"""SNMP device definitions.

To add a new device type, add an entry to DEVICE_REGISTRY below.
No other files need editing.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SensorDef:
    """Definition of a sensor to read from the device."""

    key: str                       # unique key, also the unique_id suffix
    name: str                      # HA entity display name
    oid: str                       # OID to SNMP GET
    device_class: str | None       # HA SensorDeviceClass value or None
    unit: str | None               # HA unit constant string or None
    state_class: str | None        # HA SensorStateClass value or None
    scale: float = 1.0             # raw_value * scale = reported value
    icon: str | None = None        # optional mdi icon override
    precision: int | None = None   # suggested_display_precision


@dataclass
class OutletDef:
    """Definition of switchable outlets on the device."""

    state_oid: str                 # OID prefix for reading outlet state (append .N)
    command_oid: str               # OID prefix for setting outlet state (append .N)
    name_oid: str | None           # OID prefix for outlet names (append .N), None if unsupported
    state_on: int                  # SNMP value meaning "on"
    state_off: int                 # SNMP value meaning "off"
    max_outlets: int               # max outlets to probe during discovery
    label: str = "Outlet"          # display label ("Outlet", "Outlet Group")


@dataclass
class DeviceDef:
    """Full definition of an SNMP device type."""

    key: str                       # matches config entry device_type value
    name: str                      # display name for UI
    manufacturer: str
    validation_oid: str            # OID to test connectivity during setup
    sensors: list[SensorDef] = field(default_factory=list)
    outlets: OutletDef | None = None


# ---------------------------------------------------------------------------
# Device registry — add new devices here
# ---------------------------------------------------------------------------

_CYBERPOWER_BASE = "1.3.6.1.4.1.3808.1.1.3"
_APC_BASE = "1.3.6.1.4.1.318.1.1.1"

DEVICE_REGISTRY: dict[str, DeviceDef] = {
    "cyberpower_pdu": DeviceDef(
        key="cyberpower_pdu",
        name="CyberPower PDU",
        manufacturer="CyberPower",
        validation_oid=f"{_CYBERPOWER_BASE}.3.3.1.1.4.1",
        outlets=OutletDef(
            state_oid=f"{_CYBERPOWER_BASE}.3.3.1.1.4",
            command_oid=f"{_CYBERPOWER_BASE}.3.3.1.1.4",
            name_oid=f"{_CYBERPOWER_BASE}.3.2.1.1.2",
            state_on=1,
            state_off=2,
            max_outlets=24,
            label="Outlet",
        ),
        sensors=[
            SensorDef(
                key="power",
                name="Power",
                oid=f"{_CYBERPOWER_BASE}.2.3.1.1.8.1",
                device_class="power",
                unit="W",
                state_class="measurement",
            ),
            SensorDef(
                key="energy",
                name="Energy",
                oid=f"{_CYBERPOWER_BASE}.2.3.1.1.10.1",
                device_class="energy",
                unit="kWh",
                state_class="total_increasing",
                scale=0.1,
                precision=0,
            ),
        ],
    ),
    "apc_ups": DeviceDef(
        key="apc_ups",
        name="APC UPS",
        manufacturer="APC",
        validation_oid=f"{_APC_BASE}.4.2.8.0",
        outlets=OutletDef(
            state_oid=f"{_APC_BASE}.12.3.2.1.3",
            command_oid=f"{_APC_BASE}.12.3.2.1.3",
            name_oid=None,
            state_on=1,
            state_off=2,
            max_outlets=9,
            label="Outlet Group",
        ),
        sensors=[
            SensorDef(
                key="power",
                name="Power",
                oid=f"{_APC_BASE}.4.2.8.0",
                device_class="power",
                unit="W",
                state_class="measurement",
            ),
            SensorDef(
                key="load",
                name="Load",
                oid=f"{_APC_BASE}.4.2.3.0",
                device_class=None,
                unit="%",
                state_class="measurement",
                icon="mdi:gauge",
            ),
            SensorDef(
                key="battery_capacity",
                name="Battery",
                oid=f"{_APC_BASE}.2.2.1.0",
                device_class="battery",
                unit="%",
                state_class="measurement",
            ),
            SensorDef(
                key="battery_runtime",
                name="Runtime Remaining",
                oid=f"{_APC_BASE}.2.2.3.0",
                device_class="duration",
                unit="min",
                state_class="measurement",
                scale=1 / 6000,  # ticks (1/100 sec) to minutes
                precision=0,
            ),
            SensorDef(
                key="input_voltage",
                name="Input Voltage",
                oid=f"{_APC_BASE}.3.2.1.0",
                device_class="voltage",
                unit="V",
                state_class="measurement",
            ),
        ],
    ),
}

# Derived lookup for config flow dropdown: {"cyberpower_pdu": "CyberPower PDU", ...}
DEVICE_TYPES: dict[str, str] = {k: v.name for k, v in DEVICE_REGISTRY.items()}
