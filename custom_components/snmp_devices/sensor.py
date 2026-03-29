"""Sensor platform for SNMP Devices."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_TYPE, DOMAIN
from .coordinator import SNMPDeviceCoordinator
from .devices import DEVICE_REGISTRY, SensorDef

_LOGGER = logging.getLogger(__name__)

# Map string values in SensorDef to HA constants
_DEVICE_CLASS_MAP: dict[str, SensorDeviceClass] = {dc.value: dc for dc in SensorDeviceClass}
_STATE_CLASS_MAP: dict[str, SensorStateClass] = {sc.value: sc for sc in SensorStateClass}

# Map unit strings to HA unit constants
_UNIT_MAP: dict[str, str] = {
    "W": "W",
    "kWh": "kWh",
    "%": "%",
    "V": "V",
    "A": "A",
    "min": "min",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SNMP Device sensors from a config entry."""
    coordinator: SNMPDeviceCoordinator = hass.data[DOMAIN][entry.entry_id]
    device_type = entry.data.get(CONF_DEVICE_TYPE, "cyberpower_pdu")
    device_def = DEVICE_REGISTRY.get(device_type)

    if not device_def or not device_def.sensors:
        return

    async_add_entities(
        SNMPDeviceSensor(coordinator, entry, sensor_def)
        for sensor_def in device_def.sensors
    )


class SNMPDeviceSensor(CoordinatorEntity[SNMPDeviceCoordinator], SensorEntity):
    """Generic SNMP device sensor driven by a SensorDef."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SNMPDeviceCoordinator,
        entry: ConfigEntry,
        sensor_def: SensorDef,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._sensor_def = sensor_def

        device_type = entry.data.get(CONF_DEVICE_TYPE, "cyberpower_pdu")
        self._device_def = DEVICE_REGISTRY.get(device_type)

        self._attr_name = sensor_def.name
        self._attr_unique_id = f"{entry.entry_id}_{sensor_def.key}"

        if sensor_def.device_class and sensor_def.device_class in _DEVICE_CLASS_MAP:
            self._attr_device_class = _DEVICE_CLASS_MAP[sensor_def.device_class]
        if sensor_def.unit:
            self._attr_native_unit_of_measurement = _UNIT_MAP.get(sensor_def.unit, sensor_def.unit)
        if sensor_def.state_class and sensor_def.state_class in _STATE_CLASS_MAP:
            self._attr_state_class = _STATE_CLASS_MAP[sensor_def.state_class]
        if sensor_def.icon:
            self._attr_icon = sensor_def.icon
        if sensor_def.precision is not None:
            self._attr_suggested_display_precision = sensor_def.precision

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
    def native_value(self) -> float | None:
        """Return the sensor value."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.sensors.get(self._sensor_def.key)
