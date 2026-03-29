"""Switch platform for SNMP Devices."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_TYPE, CONF_OUTLET_COUNT, CONF_OUTLET_NAMES, DOMAIN
from .coordinator import SNMPDeviceCoordinator
from .devices import DEVICE_REGISTRY

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SNMP Device switches from a config entry."""
    coordinator: SNMPDeviceCoordinator = hass.data[DOMAIN][entry.entry_id]
    device_type = entry.data.get(CONF_DEVICE_TYPE, "cyberpower_pdu")
    device_def = DEVICE_REGISTRY.get(device_type)

    if not device_def or not device_def.outlets:
        return

    outlet_count = entry.data.get(CONF_OUTLET_COUNT, 0)
    outlet_names = entry.data.get(CONF_OUTLET_NAMES, {})

    entities = []
    for outlet_num in range(1, outlet_count + 1):
        name = outlet_names.get(outlet_num) or outlet_names.get(str(outlet_num), f"Outlet {outlet_num}")
        entities.append(
            SNMPDeviceSwitch(
                coordinator=coordinator,
                entry=entry,
                outlet_num=outlet_num,
                outlet_name=name,
            )
        )

    async_add_entities(entities)


class SNMPDeviceSwitch(CoordinatorEntity[SNMPDeviceCoordinator], SwitchEntity):
    """Representation of an SNMP device outlet switch."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SNMPDeviceCoordinator,
        entry: ConfigEntry,
        outlet_num: int,
        outlet_name: str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._entry = entry
        self._outlet_num = outlet_num
        self._attr_name = outlet_name
        self._attr_unique_id = f"{entry.entry_id}_outlet_{outlet_num}"

        device_type = entry.data.get(CONF_DEVICE_TYPE, "cyberpower_pdu")
        self._device_def = DEVICE_REGISTRY.get(device_type)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.data.get("name", self.coordinator.host),
            manufacturer=self._device_def.manufacturer if self._device_def else "Unknown",
            model=self._device_def.name if self._device_def else "SNMP Device",
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if the outlet is on."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.outlets.get(self._outlet_num)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the outlet on."""
        if not self._device_def or not self._device_def.outlets:
            return
        outlets = self._device_def.outlets
        oid = f"{outlets.command_oid}.{self._outlet_num}"
        success = await self.coordinator.async_snmp_set(oid, outlets.command_on)
        if success:
            if self.coordinator.data:
                self.coordinator.data.outlets[self._outlet_num] = True
            self.async_write_ha_state()
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the outlet off."""
        if not self._device_def or not self._device_def.outlets:
            return
        outlets = self._device_def.outlets
        oid = f"{outlets.command_oid}.{self._outlet_num}"
        success = await self.coordinator.async_snmp_set(oid, outlets.command_off)
        if success:
            if self.coordinator.data:
                self.coordinator.data.outlets[self._outlet_num] = False
            self.async_write_ha_state()
            await self.coordinator.async_request_refresh()
