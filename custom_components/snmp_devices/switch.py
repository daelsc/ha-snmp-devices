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

from .const import (
    APC_OID_OUTLET_GROUP_STATE,
    APC_STATE_OFF,
    APC_STATE_ON,
    CONF_DEVICE_TYPE,
    CONF_OUTLET_COUNT,
    CONF_OUTLET_NAMES,
    CYBERPOWER_OID_OUTLET_COMMAND,
    CYBERPOWER_STATE_OFF,
    CYBERPOWER_STATE_ON,
    DEVICE_TYPE_APC_UPS,
    DEVICE_TYPE_CYBERPOWER_PDU,
    DEVICE_TYPES,
    DOMAIN,
)
from .coordinator import SNMPDeviceCoordinator, SNMPDeviceData

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SNMP Device switches from a config entry."""
    coordinator: SNMPDeviceCoordinator = hass.data[DOMAIN][entry.entry_id]

    outlet_count = entry.data.get(CONF_OUTLET_COUNT, 0)
    outlet_names = entry.data.get(CONF_OUTLET_NAMES, {})
    device_type = entry.data.get(CONF_DEVICE_TYPE, DEVICE_TYPE_CYBERPOWER_PDU)

    entities = []
    for outlet_num in range(1, outlet_count + 1):
        name = outlet_names.get(outlet_num) or outlet_names.get(str(outlet_num), f"Outlet {outlet_num}")
        entities.append(
            SNMPDeviceSwitch(
                coordinator=coordinator,
                entry=entry,
                outlet_num=outlet_num,
                outlet_name=name,
                device_type=device_type,
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
        device_type: str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._entry = entry
        self._outlet_num = outlet_num
        self._device_type = device_type
        self._attr_name = outlet_name
        self._attr_unique_id = f"{entry.entry_id}_outlet_{outlet_num}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        device_type_name = DEVICE_TYPES.get(self._device_type, "SNMP Device")
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.data.get("name", self.coordinator.host),
            manufacturer="CyberPower" if self._device_type == DEVICE_TYPE_CYBERPOWER_PDU else "APC",
            model=device_type_name,
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if the outlet is on."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.outlets.get(self._outlet_num)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the outlet on."""
        if self._device_type == DEVICE_TYPE_CYBERPOWER_PDU:
            oid = f"{CYBERPOWER_OID_OUTLET_COMMAND}.{self._outlet_num}"
            value = CYBERPOWER_STATE_ON
        else:  # APC UPS
            oid = f"{APC_OID_OUTLET_GROUP_STATE}.{self._outlet_num}"
            value = APC_STATE_ON

        success = await self.coordinator.snmp_set(oid, value)
        if success:
            if self.coordinator.data:
                self.coordinator.data.outlets[self._outlet_num] = True
            self.async_write_ha_state()
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the outlet off."""
        if self._device_type == DEVICE_TYPE_CYBERPOWER_PDU:
            oid = f"{CYBERPOWER_OID_OUTLET_COMMAND}.{self._outlet_num}"
            value = CYBERPOWER_STATE_OFF
        else:  # APC UPS
            oid = f"{APC_OID_OUTLET_GROUP_STATE}.{self._outlet_num}"
            value = APC_STATE_OFF

        success = await self.coordinator.snmp_set(oid, value)
        if success:
            if self.coordinator.data:
                self.coordinator.data.outlets[self._outlet_num] = False
            self.async_write_ha_state()
            await self.coordinator.async_request_refresh()
