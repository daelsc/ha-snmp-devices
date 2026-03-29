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
    APC_OID_BATTERY_CAPACITY,
    APC_OID_BATTERY_RUNTIME,
    APC_OID_INPUT_VOLTAGE,
    APC_OID_OUTLET_GROUP_STATE,
    APC_OID_OUTPUT_LOAD,
    APC_OID_OUTPUT_POWER,
    APC_STATE_ON,
    CONF_DEVICE_TYPE,
    CONF_OUTLET_COUNT,
    CYBERPOWER_OID_ENERGY,
    CYBERPOWER_OID_OUTLET_STATE,
    CYBERPOWER_OID_POWER,
    CYBERPOWER_STATE_ON,
    DEFAULT_SCAN_INTERVAL,
    DEVICE_TYPE_APC_UPS,
    DEVICE_TYPE_CYBERPOWER_PDU,
    DOMAIN,
)
from .snmp_client import snmp_get, snmp_set

_LOGGER = logging.getLogger(__name__)


@dataclass
class SNMPDeviceData:
    """Class to hold SNMP device data."""

    outlets: dict[int, bool] = field(default_factory=dict)  # outlet_num -> is_on
    power: float | None = None  # Watts
    energy: float | None = None  # kWh
    load_percent: float | None = None  # Percent (APC)
    battery_capacity: float | None = None  # Percent (APC)
    battery_runtime: float | None = None  # Minutes (APC)
    input_voltage: float | None = None  # Volts (APC)


class SNMPDeviceCoordinator(DataUpdateCoordinator[SNMPDeviceData]):
    """Coordinator for SNMP device data updates."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        self.host = entry.data[CONF_HOST]
        self.community = entry.data.get("community", "private")
        self.device_type = entry.data.get(CONF_DEVICE_TYPE, DEVICE_TYPE_CYBERPOWER_PDU)
        self.outlet_count = entry.data.get(CONF_OUTLET_COUNT, 8)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
            config_entry=entry,
        )

    async def async_config_entry_first_refresh_lenient(self) -> None:
        """First refresh that doesn't fail setup on error.

        Entities show as unavailable and the coordinator retries on its
        normal interval.
        """
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

    async def _async_snmp_set(self, oid: str, value: int) -> bool:
        """Perform async SNMP SET."""
        try:
            resp = await snmp_set(self.host, self.community, oid, value)
            if resp.error:
                _LOGGER.error("SNMP SET error: %s", resp.error)
                return False
            return True
        except Exception as err:
            _LOGGER.error("SNMP SET error: %s", err)
            return False

    async def async_snmp_set(self, oid: str, value: int) -> bool:
        """Perform an SNMP SET request."""
        return await self._async_snmp_set(oid, value)

    async def _async_update_data(self) -> SNMPDeviceData:
        """Fetch data from device.

        Returns empty data on failure so entities go unavailable instead
        of the integration failing entirely.
        """
        if self.device_type == DEVICE_TYPE_CYBERPOWER_PDU:
            return await self._fetch_cyberpower_data()
        elif self.device_type == DEVICE_TYPE_APC_UPS:
            return await self._fetch_apc_data()
        else:
            _LOGGER.error("Unknown device type: %s", self.device_type)
            return SNMPDeviceData()

    async def _fetch_cyberpower_data(self) -> SNMPDeviceData:
        """Fetch data from CyberPower PDU."""
        data = SNMPDeviceData()

        try:
            for outlet_num in range(1, self.outlet_count + 1):
                oid = f"{CYBERPOWER_OID_OUTLET_STATE}.{outlet_num}"
                result = await self._async_snmp_get(oid)
                if result is not None:
                    try:
                        state_value = int(result)
                        data.outlets[outlet_num] = state_value == CYBERPOWER_STATE_ON
                    except (ValueError, TypeError):
                        _LOGGER.debug("Invalid outlet state for outlet %d: %s", outlet_num, result)

            power_result = await self._async_snmp_get(CYBERPOWER_OID_POWER)
            if power_result is not None:
                try:
                    data.power = float(int(power_result))
                except (ValueError, TypeError):
                    pass

            energy_result = await self._async_snmp_get(CYBERPOWER_OID_ENERGY)
            if energy_result is not None:
                try:
                    data.energy = int(energy_result) / 10.0
                except (ValueError, TypeError):
                    pass

        except Exception as err:
            _LOGGER.warning("Error communicating with CyberPower PDU at %s: %s", self.host, err)

        return data

    async def _fetch_apc_data(self) -> SNMPDeviceData:
        """Fetch data from APC UPS."""
        data = SNMPDeviceData()

        try:
            for group_num in range(1, self.outlet_count + 1):
                oid = f"{APC_OID_OUTLET_GROUP_STATE}.{group_num}"
                result = await self._async_snmp_get(oid)
                if result is not None:
                    try:
                        state_value = int(result)
                        data.outlets[group_num] = state_value == APC_STATE_ON
                    except (ValueError, TypeError):
                        _LOGGER.debug("Invalid outlet group state for group %d: %s", group_num, result)

            power_result = await self._async_snmp_get(APC_OID_OUTPUT_POWER)
            if power_result is not None:
                try:
                    data.power = float(int(power_result))
                except (ValueError, TypeError):
                    pass

            load_result = await self._async_snmp_get(APC_OID_OUTPUT_LOAD)
            if load_result is not None:
                try:
                    data.load_percent = float(int(load_result))
                except (ValueError, TypeError):
                    pass

            battery_result = await self._async_snmp_get(APC_OID_BATTERY_CAPACITY)
            if battery_result is not None:
                try:
                    data.battery_capacity = float(int(battery_result))
                except (ValueError, TypeError):
                    pass

            runtime_result = await self._async_snmp_get(APC_OID_BATTERY_RUNTIME)
            if runtime_result is not None:
                try:
                    ticks = int(runtime_result)
                    data.battery_runtime = ticks / 6000.0
                except (ValueError, TypeError):
                    pass

            voltage_result = await self._async_snmp_get(APC_OID_INPUT_VOLTAGE)
            if voltage_result is not None:
                try:
                    data.input_voltage = float(int(voltage_result))
                except (ValueError, TypeError):
                    pass

        except Exception as err:
            _LOGGER.warning("Error communicating with APC UPS at %s: %s", self.host, err)

        return data
