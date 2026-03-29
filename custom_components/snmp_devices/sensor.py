"""Sensor platform for SNMP Devices."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_DEVICE_TYPE,
    DEVICE_TYPE_APC_UPS,
    DEVICE_TYPE_CYBERPOWER_PDU,
    DEVICE_TYPES,
    DOMAIN,
)
from .coordinator import SNMPDeviceCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SNMP Device sensors from a config entry."""
    coordinator: SNMPDeviceCoordinator = hass.data[DOMAIN][entry.entry_id]
    device_type = entry.data.get(CONF_DEVICE_TYPE, DEVICE_TYPE_CYBERPOWER_PDU)

    entities: list[SensorEntity] = []

    if device_type == DEVICE_TYPE_CYBERPOWER_PDU:
        entities.extend([
            SNMPDevicePowerSensor(coordinator, entry),
            SNMPDeviceEnergySensor(coordinator, entry),
        ])
    elif device_type == DEVICE_TYPE_APC_UPS:
        entities.extend([
            SNMPDevicePowerSensor(coordinator, entry),
            SNMPDeviceLoadSensor(coordinator, entry),
            SNMPDeviceBatteryCapacitySensor(coordinator, entry),
            SNMPDeviceBatteryRuntimeSensor(coordinator, entry),
            SNMPDeviceInputVoltageSensor(coordinator, entry),
        ])

    async_add_entities(entities)


class SNMPDeviceBaseSensor(CoordinatorEntity[SNMPDeviceCoordinator], SensorEntity):
    """Base class for SNMP device sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SNMPDeviceCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._device_type = entry.data.get(CONF_DEVICE_TYPE, DEVICE_TYPE_CYBERPOWER_PDU)

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


class SNMPDevicePowerSensor(SNMPDeviceBaseSensor):
    """Sensor for device power consumption."""

    _attr_name = "Power"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: SNMPDeviceCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_power"

    @property
    def native_value(self) -> float | None:
        """Return the current power."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.power


class SNMPDeviceEnergySensor(SNMPDeviceBaseSensor):
    """Sensor for device energy consumption (CyberPower PDU)."""

    _attr_name = "Energy"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_suggested_display_precision = 0

    def __init__(self, coordinator: SNMPDeviceCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_energy"

    @property
    def native_value(self) -> float | None:
        """Return the total energy."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.energy


class SNMPDeviceLoadSensor(SNMPDeviceBaseSensor):
    """Sensor for UPS output load (APC UPS)."""

    _attr_name = "Load"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:gauge"

    def __init__(self, coordinator: SNMPDeviceCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_load"

    @property
    def native_value(self) -> float | None:
        """Return the current load percentage."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.load_percent


class SNMPDeviceBatteryCapacitySensor(SNMPDeviceBaseSensor):
    """Sensor for UPS battery capacity (APC UPS)."""

    _attr_name = "Battery"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: SNMPDeviceCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_battery_capacity"

    @property
    def native_value(self) -> float | None:
        """Return the battery capacity percentage."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.battery_capacity


class SNMPDeviceBatteryRuntimeSensor(SNMPDeviceBaseSensor):
    """Sensor for UPS battery runtime remaining (APC UPS)."""

    _attr_name = "Runtime Remaining"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 0

    def __init__(self, coordinator: SNMPDeviceCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_battery_runtime"

    @property
    def native_value(self) -> float | None:
        """Return the battery runtime remaining in minutes."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.battery_runtime


class SNMPDeviceInputVoltageSensor(SNMPDeviceBaseSensor):
    """Sensor for UPS input voltage (APC UPS)."""

    _attr_name = "Input Voltage"
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: SNMPDeviceCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_input_voltage"

    @property
    def native_value(self) -> float | None:
        """Return the input voltage."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.input_voltage
