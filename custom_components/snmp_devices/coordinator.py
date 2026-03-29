"""DataUpdateCoordinator for SNMP Devices."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_DEVICE_TYPE,
    CONF_OUTLET_COUNT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .devices import DEVICE_REGISTRY
from .snmp_client import snmp_get, snmp_set

_LOGGER = logging.getLogger(__name__)


@dataclass
class SNMPDeviceData:
    """Generic container for SNMP device data."""

    outlets: dict[int, bool] = field(default_factory=dict)
    sensors: dict[str, float | None] = field(default_factory=dict)


class SNMPDeviceCoordinator(DataUpdateCoordinator[SNMPDeviceData]):
    """Coordinator for SNMP device data updates."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.host = entry.data[CONF_HOST]
        self.community = entry.data.get("community", "private")
        self.device_type = entry.data.get(CONF_DEVICE_TYPE, "cyberpower_pdu")
        self.outlet_count = entry.data.get(CONF_OUTLET_COUNT, 8)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
            config_entry=entry,
        )

    async def async_config_entry_first_refresh_lenient(self) -> None:
        """First refresh that doesn't fail setup on error."""
        try:
            await self.async_config_entry_first_refresh()
        except Exception as err:
            _LOGGER.warning(
                "First data refresh failed for %s (%s), will retry: %s",
                self.host, self.device_type, err,
            )
            self.data = SNMPDeviceData()

    async def _async_snmp_get(self, oid: str) -> Any:
        """Perform async SNMP GET."""
        try:
            resp = await snmp_get(self.host, self.community, oid)
            if resp.error:
                _LOGGER.debug("SNMP error for %s: %s", oid, resp.error)
                return None
            if resp.no_such:
                return None
            return resp.value
        except Exception as err:
            _LOGGER.debug("SNMP GET error for %s: %s", oid, err)
            return None

    async def async_snmp_set(self, oid: str, value: int) -> bool:
        """Perform an SNMP SET request."""
        try:
            resp = await snmp_set(self.host, self.community, oid, value)
            if resp.error:
                _LOGGER.error("SNMP SET error: %s", resp.error)
                return False
            return True
        except Exception as err:
            _LOGGER.error("SNMP SET error: %s", err)
            return False

    async def _async_update_data(self) -> SNMPDeviceData:
        """Fetch data from device."""
        device_def = DEVICE_REGISTRY.get(self.device_type)
        if device_def is None:
            _LOGGER.error("Unknown device type: %s", self.device_type)
            return SNMPDeviceData()

        data = SNMPDeviceData()

        try:
            # Fetch outlet states
            if device_def.outlets:
                for num in range(1, self.outlet_count + 1):
                    oid = f"{device_def.outlets.state_oid}.{num}"
                    result = await self._async_snmp_get(oid)
                    if result is not None:
                        try:
                            data.outlets[num] = int(result) == device_def.outlets.state_on
                        except (ValueError, TypeError):
                            _LOGGER.debug("Invalid outlet state for %d: %s", num, result)

            # Fetch sensors
            for sensor_def in device_def.sensors:
                result = await self._async_snmp_get(sensor_def.oid)
                if result is not None:
                    try:
                        data.sensors[sensor_def.key] = float(int(result)) * sensor_def.scale
                    except (ValueError, TypeError):
                        _LOGGER.debug("Invalid sensor value for %s: %s", sensor_def.key, result)

        except Exception as err:
            _LOGGER.warning("Error communicating with %s at %s: %s", device_def.name, self.host, err)

        return data
