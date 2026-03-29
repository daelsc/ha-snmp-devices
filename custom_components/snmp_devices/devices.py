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
    state_on: int                  # SNMP value meaning "on" when reading state
    state_off: int                 # SNMP value meaning "off" when reading state
    max_outlets: int               # max outlets to probe during discovery
    label: str = "Outlet"          # display label ("Outlet", "Outlet Group")
    command_on: int | None = None  # value to SET for "on" (defaults to state_on)
    command_off: int | None = None # value to SET for "off" (defaults to state_off)

    def __post_init__(self) -> None:
        if self.command_on is None:
            self.command_on = self.state_on
        if self.command_off is None:
            self.command_off = self.state_off


@dataclass
class DeviceDef:
    """Full definition of an SNMP device type."""

    key: str                       # matches config entry device_type value
    name: str                      # display name for UI
    manufacturer: str
    validation_oid: str            # OID to test connectivity during setup
    sensors: list[SensorDef] = field(default_factory=list)
    outlets: OutletDef | None = None


# =============================================================================
# OID base prefixes
# =============================================================================

_CYBERPOWER_BASE = "1.3.6.1.4.1.3808.1.1.3"

# APC UPS (PowerNet-MIB upsObjects)
_APC_UPS = "1.3.6.1.4.1.318.1.1.1"
# APC Rack PDU (rPDU — older switched models: AP79xx, AP78xx)
_APC_RPDU = "1.3.6.1.4.1.318.1.1.12"
# APC Rack PDU2 (rPDU2 — newer models: AP86xx, AP88xx, AP89xx)
_APC_RPDU2 = "1.3.6.1.4.1.318.1.1.26"
# APC In-Row Cooling (airIRSC)
_APC_COOL = "1.3.6.1.4.1.318.1.1.13"
# APC Environmental Monitor (iemStatusProbes)
_APC_ENV = "1.3.6.1.4.1.318.1.1.10"

# RFC 1628 standard UPS-MIB (used by many vendors)
_UPS_MIB = "1.3.6.1.2.1.33.1"

# Eaton XUPS-MIB
_EATON_XUPS = "1.3.6.1.4.1.534.1"
# Eaton ePDU (EATON-EPDU-MIB)
_EATON_EPDU = "1.3.6.1.4.1.534.6.6.7"

# Raritan PDU2-MIB
_RARITAN = "1.3.6.1.4.1.13742.6"

# Liebert/Vertiv (LIEBERT-GP-ENVIRONMENTAL-MIB)
_LIEBERT = "1.3.6.1.4.1.476.1.42"


# =============================================================================
# Device registry
# =============================================================================

DEVICE_REGISTRY: dict[str, DeviceDef] = {

    # -----------------------------------------------------------------
    # CyberPower PDU
    # -----------------------------------------------------------------
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

    # -----------------------------------------------------------------
    # APC UPS (Smart-UPS, Back-UPS with NMC, Symmetra)
    # PowerNet-MIB upsObjects (.1.3.6.1.4.1.318.1.1.1)
    # -----------------------------------------------------------------
    "apc_ups": DeviceDef(
        key="apc_ups",
        name="APC UPS",
        manufacturer="APC",
        validation_oid=f"{_APC_UPS}.4.2.3.0",
        outlets=OutletDef(
            state_oid=f"{_APC_UPS}.12.3.2.1.3",
            command_oid=f"{_APC_UPS}.12.3.2.1.3",
            name_oid=f"{_APC_UPS}.12.3.2.1.2",
            state_on=1,
            state_off=2,
            max_outlets=9,
            label="Outlet Group",
        ),
        sensors=[
            # --- Output ---
            SensorDef(key="power", name="Output Power",
                      oid=f"{_APC_UPS}.4.2.8.0",
                      device_class="power", unit="W", state_class="measurement"),
            SensorDef(key="load", name="Output Load",
                      oid=f"{_APC_UPS}.4.2.3.0",
                      device_class=None, unit="%", state_class="measurement",
                      icon="mdi:gauge"),
            SensorDef(key="output_voltage", name="Output Voltage",
                      oid=f"{_APC_UPS}.4.2.1.0",
                      device_class="voltage", unit="V", state_class="measurement"),
            SensorDef(key="output_current", name="Output Current",
                      oid=f"{_APC_UPS}.4.2.4.0",        # upsAdvOutputCurrent (A)
                      device_class="current", unit="A", state_class="measurement",
                      precision=1),
            SensorDef(key="output_frequency", name="Output Frequency",
                      oid=f"{_APC_UPS}.4.2.2.0",        # upsAdvOutputFrequency (Hz)
                      device_class="frequency", unit="Hz", state_class="measurement",
                      precision=1),
            # --- Input ---
            SensorDef(key="input_voltage", name="Input Voltage",
                      oid=f"{_APC_UPS}.3.2.1.0",
                      device_class="voltage", unit="V", state_class="measurement"),
            SensorDef(key="input_frequency", name="Input Frequency",
                      oid=f"{_APC_UPS}.3.2.4.0",        # upsAdvInputFrequency (Hz)
                      device_class="frequency", unit="Hz", state_class="measurement",
                      precision=1),
            # --- Battery ---
            SensorDef(key="battery_capacity", name="Battery Capacity",
                      oid=f"{_APC_UPS}.2.2.1.0",
                      device_class="battery", unit="%", state_class="measurement"),
            SensorDef(key="battery_runtime", name="Runtime Remaining",
                      oid=f"{_APC_UPS}.2.2.3.0",
                      device_class="duration", unit="min", state_class="measurement",
                      scale=1 / 6000, precision=0),
            SensorDef(key="battery_temperature", name="Battery Temperature",
                      oid=f"{_APC_UPS}.2.2.2.0",
                      device_class="temperature", unit="°C", state_class="measurement"),
            SensorDef(key="battery_voltage", name="Battery Voltage",
                      oid=f"{_APC_UPS}.2.2.8.0",
                      device_class="voltage", unit="V", state_class="measurement"),
            SensorDef(key="battery_current", name="Battery Current",
                      oid=f"{_APC_UPS}.2.2.9.0",
                      device_class="current", unit="A", state_class="measurement"),
        ],
    ),

    # -----------------------------------------------------------------
    # APC Rack PDU — older switched models (AP79xx, AP78xx)
    # PowerNet-MIB rPDU (.1.3.6.1.4.1.318.1.1.12)
    # -----------------------------------------------------------------
    "apc_rpdu": DeviceDef(
        key="apc_rpdu",
        name="APC Rack PDU",
        manufacturer="APC",
        validation_oid=f"{_APC_RPDU}.1.16.0",
        outlets=OutletDef(
            state_oid=f"{_APC_RPDU}.3.5.1.1.4",
            command_oid=f"{_APC_RPDU}.3.3.1.1.4",
            name_oid=f"{_APC_RPDU}.3.3.1.1.2",
            state_on=1,
            state_off=2,
            max_outlets=48,
            command_on=1,   # immediateOn
            command_off=2,  # immediateOff
            label="Outlet",
        ),
        sensors=[
            SensorDef(key="power", name="Power",
                      oid=f"{_APC_RPDU}.1.16.0",
                      device_class="power", unit="W", state_class="measurement"),
            SensorDef(key="bank1_current", name="Bank 1 Current",
                      oid=f"{_APC_RPDU}.2.3.1.1.2.1",
                      device_class="current", unit="A", state_class="measurement",
                      scale=0.1, precision=1),
            SensorDef(key="bank2_current", name="Bank 2 Current",
                      oid=f"{_APC_RPDU}.2.3.1.1.2.2",
                      device_class="current", unit="A", state_class="measurement",
                      scale=0.1, precision=1),
        ],
    ),

    # -----------------------------------------------------------------
    # APC Rack PDU2 — newer models (AP86xx, AP88xx, AP89xx)
    # PowerNet-MIB rPDU2 (.1.3.6.1.4.1.318.1.1.26)
    # -----------------------------------------------------------------
    "apc_rpdu2": DeviceDef(
        key="apc_rpdu2",
        name="APC Rack PDU2",
        manufacturer="APC",
        validation_oid=f"{_APC_RPDU2}.4.3.1.5.1.1",
        outlets=OutletDef(
            state_oid=f"{_APC_RPDU2}.9.2.1.5.1",
            command_oid=f"{_APC_RPDU2}.9.2.2.1.3.1",
            name_oid=f"{_APC_RPDU2}.9.2.1.3.1",
            state_on=1,
            state_off=2,
            max_outlets=48,
            command_on=1,   # immediateOn
            command_off=2,  # immediateOff
            label="Outlet",
        ),
        sensors=[
            SensorDef(key="power", name="Power",
                      oid=f"{_APC_RPDU2}.4.3.1.5.1.1",
                      device_class="power", unit="W", state_class="measurement"),
            SensorDef(key="energy", name="Energy",
                      oid=f"{_APC_RPDU2}.4.3.1.6.1.1",
                      device_class="energy", unit="kWh", state_class="total_increasing",
                      scale=0.1, precision=1),
            SensorDef(key="phase_voltage", name="Voltage",
                      oid=f"{_APC_RPDU2}.6.3.1.6.1.1",
                      device_class="voltage", unit="V", state_class="measurement",
                      scale=0.1, precision=1),
            SensorDef(key="phase_current", name="Current",
                      oid=f"{_APC_RPDU2}.6.3.1.5.1.1",
                      device_class="current", unit="A", state_class="measurement",
                      scale=0.1, precision=1),
            SensorDef(key="phase_power", name="Phase Power",
                      oid=f"{_APC_RPDU2}.6.3.1.7.1.1",
                      device_class="power", unit="W", state_class="measurement"),
        ],
    ),

    # -----------------------------------------------------------------
    # APC In-Row Cooling Unit (InRow RC/SC/RD)
    # PowerNet-MIB airIRSC (.1.3.6.1.4.1.318.1.1.13)
    # -----------------------------------------------------------------
    "apc_inrow": DeviceDef(
        key="apc_inrow",
        name="APC In-Row Cooling",
        manufacturer="APC",
        validation_oid=f"{_APC_COOL}.3.2.2.2.1.0",
        sensors=[
            SensorDef(key="cool_output", name="Cooling Output",
                      oid=f"{_APC_COOL}.3.2.2.2.1.0",
                      device_class="power", unit="kW", state_class="measurement",
                      scale=0.1, precision=1),
            SensorDef(key="rack_inlet_temp", name="Rack Inlet Temperature",
                      oid=f"{_APC_COOL}.3.2.2.2.6.0",
                      device_class="temperature", unit="°C", state_class="measurement",
                      scale=0.1, precision=1),
            SensorDef(key="supply_air_temp", name="Supply Air Temperature",
                      oid=f"{_APC_COOL}.3.2.2.2.8.0",
                      device_class="temperature", unit="°C", state_class="measurement",
                      scale=0.1, precision=1),
            SensorDef(key="return_air_temp", name="Return Air Temperature",
                      oid=f"{_APC_COOL}.3.2.2.2.10.0",
                      device_class="temperature", unit="°C", state_class="measurement",
                      scale=0.1, precision=1),
            SensorDef(key="air_flow", name="Air Flow",
                      oid=f"{_APC_COOL}.3.2.2.2.4.0",
                      device_class=None, unit="L/s", state_class="measurement",
                      icon="mdi:fan"),
            SensorDef(key="fan_speed", name="Fan Speed",
                      oid=f"{_APC_COOL}.3.2.2.2.16.0",
                      device_class=None, unit="%", state_class="measurement",
                      icon="mdi:fan"),
        ],
    ),

    # -----------------------------------------------------------------
    # APC Environmental Monitor (NetBotz, AP9340, etc.)
    # PowerNet-MIB iemStatusProbes (.1.3.6.1.4.1.318.1.1.10)
    # Probe index 1
    # -----------------------------------------------------------------
    "apc_env": DeviceDef(
        key="apc_env",
        name="APC Environmental Monitor",
        manufacturer="APC",
        validation_oid=f"{_APC_ENV}.2.3.2.1.4.1",
        sensors=[
            SensorDef(key="temperature", name="Temperature",
                      oid=f"{_APC_ENV}.2.3.2.1.4.1",
                      device_class="temperature", unit="°C", state_class="measurement"),
            SensorDef(key="humidity", name="Humidity",
                      oid=f"{_APC_ENV}.2.3.2.1.6.1",
                      device_class="humidity", unit="%", state_class="measurement"),
        ],
    ),

    # =================================================================
    # RFC 1628 UPS-MIB (generic standard)
    # Works with: Tripp Lite, Eaton (some), Liebert (some), many others
    # =================================================================
    "ups_rfc1628": DeviceDef(
        key="ups_rfc1628",
        name="UPS (RFC 1628 standard)",
        manufacturer="Generic",
        validation_oid=f"{_UPS_MIB}.4.4.1.5.1",  # upsOutputPercentLoad line 1
        sensors=[
            # --- Output ---
            SensorDef(key="power", name="Output Power",
                      oid=f"{_UPS_MIB}.4.4.1.4.1",        # upsOutputPower line 1 (W)
                      device_class="power", unit="W", state_class="measurement"),
            SensorDef(key="load", name="Output Load",
                      oid=f"{_UPS_MIB}.4.4.1.5.1",        # upsOutputPercentLoad line 1 (%)
                      device_class=None, unit="%", state_class="measurement",
                      icon="mdi:gauge"),
            SensorDef(key="output_voltage", name="Output Voltage",
                      oid=f"{_UPS_MIB}.4.4.1.2.1",        # upsOutputVoltage line 1 (V)
                      device_class="voltage", unit="V", state_class="measurement"),
            SensorDef(key="output_current", name="Output Current",
                      oid=f"{_UPS_MIB}.4.4.1.3.1",        # upsOutputCurrent line 1 (0.1 A)
                      device_class="current", unit="A", state_class="measurement",
                      scale=0.1, precision=1),
            SensorDef(key="output_frequency", name="Output Frequency",
                      oid=f"{_UPS_MIB}.4.2.0",            # upsOutputFrequency (0.1 Hz)
                      device_class="frequency", unit="Hz", state_class="measurement",
                      scale=0.1, precision=1),
            # --- Input ---
            SensorDef(key="input_voltage", name="Input Voltage",
                      oid=f"{_UPS_MIB}.3.3.1.3.1",        # upsInputVoltage line 1 (V)
                      device_class="voltage", unit="V", state_class="measurement"),
            SensorDef(key="input_frequency", name="Input Frequency",
                      oid=f"{_UPS_MIB}.3.3.1.2.1",        # upsInputFrequency line 1 (0.1 Hz)
                      device_class="frequency", unit="Hz", state_class="measurement",
                      scale=0.1, precision=1),
            # --- Battery ---
            SensorDef(key="battery_capacity", name="Battery Capacity",
                      oid=f"{_UPS_MIB}.2.4.0",            # upsEstimatedChargeRemaining (%)
                      device_class="battery", unit="%", state_class="measurement"),
            SensorDef(key="battery_runtime", name="Runtime Remaining",
                      oid=f"{_UPS_MIB}.2.3.0",            # upsEstimatedMinutesRemaining (min)
                      device_class="duration", unit="min", state_class="measurement",
                      precision=0),
            SensorDef(key="battery_voltage", name="Battery Voltage",
                      oid=f"{_UPS_MIB}.2.5.0",            # upsBatteryVoltage (0.1 V)
                      device_class="voltage", unit="V", state_class="measurement",
                      scale=0.1, precision=1),
            SensorDef(key="battery_current", name="Battery Current",
                      oid=f"{_UPS_MIB}.2.6.0",            # upsBatteryCurrent (0.1 A)
                      device_class="current", unit="A", state_class="measurement",
                      scale=0.1, precision=1),
            SensorDef(key="battery_temperature", name="Battery Temperature",
                      oid=f"{_UPS_MIB}.2.7.0",            # upsBatteryTemperature (°C)
                      device_class="temperature", unit="°C", state_class="measurement"),
        ],
    ),

    # =================================================================
    # Eaton UPS (XUPS-MIB)
    # Eaton 5P, 5PX, 9PX, 9SX, 93PM, etc.
    # =================================================================
    "eaton_ups": DeviceDef(
        key="eaton_ups",
        name="Eaton UPS",
        manufacturer="Eaton",
        validation_oid=f"{_EATON_XUPS}.4.1.0",  # xupsOutputLoad
        sensors=[
            # --- Output ---
            SensorDef(key="power", name="Output Power",
                      oid=f"{_EATON_XUPS}.4.4.1.4.1",     # xupsOutputWatts phase 1 (W)
                      device_class="power", unit="W", state_class="measurement"),
            SensorDef(key="load", name="Output Load",
                      oid=f"{_EATON_XUPS}.4.1.0",         # xupsOutputLoad (%)
                      device_class=None, unit="%", state_class="measurement",
                      icon="mdi:gauge"),
            SensorDef(key="output_voltage", name="Output Voltage",
                      oid=f"{_EATON_XUPS}.4.4.1.2.1",     # xupsOutputVoltage phase 1 (V)
                      device_class="voltage", unit="V", state_class="measurement"),
            SensorDef(key="output_current", name="Output Current",
                      oid=f"{_EATON_XUPS}.4.4.1.3.1",     # xupsOutputCurrent phase 1 (0.1 A)
                      device_class="current", unit="A", state_class="measurement",
                      scale=0.1, precision=1),
            SensorDef(key="output_frequency", name="Output Frequency",
                      oid=f"{_EATON_XUPS}.4.2.0",         # xupsOutputFrequency (0.1 Hz)
                      device_class="frequency", unit="Hz", state_class="measurement",
                      scale=0.1, precision=1),
            # --- Input ---
            SensorDef(key="input_voltage", name="Input Voltage",
                      oid=f"{_EATON_XUPS}.3.4.1.2.1",     # xupsInputVoltage phase 1 (V)
                      device_class="voltage", unit="V", state_class="measurement"),
            SensorDef(key="input_frequency", name="Input Frequency",
                      oid=f"{_EATON_XUPS}.3.1.0",         # xupsInputFrequency (0.1 Hz)
                      device_class="frequency", unit="Hz", state_class="measurement",
                      scale=0.1, precision=1),
            # --- Battery ---
            SensorDef(key="battery_capacity", name="Battery Capacity",
                      oid=f"{_EATON_XUPS}.2.4.0",         # xupsBatCapacity (%)
                      device_class="battery", unit="%", state_class="measurement"),
            SensorDef(key="battery_runtime", name="Runtime Remaining",
                      oid=f"{_EATON_XUPS}.2.1.0",         # xupsBatTimeRemaining (seconds)
                      device_class="duration", unit="min", state_class="measurement",
                      scale=1 / 60, precision=0),
            SensorDef(key="battery_voltage", name="Battery Voltage",
                      oid=f"{_EATON_XUPS}.2.2.0",         # xupsBatVoltage (V)
                      device_class="voltage", unit="V", state_class="measurement"),
            SensorDef(key="battery_current", name="Battery Current",
                      oid=f"{_EATON_XUPS}.2.3.0",         # xupsBatCurrent (A)
                      device_class="current", unit="A", state_class="measurement"),
            # --- Environment ---
            SensorDef(key="ambient_temperature", name="Ambient Temperature",
                      oid=f"{_EATON_XUPS}.6.1.0",         # xupsEnvAmbientTemp (°C)
                      device_class="temperature", unit="°C", state_class="measurement"),
        ],
    ),

    # =================================================================
    # Eaton ePDU (managed/switched rack PDU)
    # Eaton ePDU G3, eAA, eMA series
    # EATON-EPDU-MIB — indexes: strappingIndex=0, inputIndex=1, phaseIndex=1
    # =================================================================
    "eaton_epdu": DeviceDef(
        key="eaton_epdu",
        name="Eaton ePDU",
        manufacturer="Eaton",
        validation_oid=f"{_EATON_EPDU}.3.1.1.4.0.1",  # inputPower unit 0 input 1
        outlets=OutletDef(
            state_oid=f"{_EATON_EPDU}.6.6.1.2.0",         # outletControlStatus .0.N
            command_oid=f"{_EATON_EPDU}.6.6.1.3.0",        # outletControlSwitchCommand .0.N
            name_oid=f"{_EATON_EPDU}.6.1.1.3.0",           # outletName .0.N
            state_on=1,     # on
            state_off=0,    # off
            max_outlets=48,
            command_on=1,   # immediateOn
            command_off=0,  # immediateOff
            label="Outlet",
        ),
        sensors=[
            SensorDef(key="power", name="Power",
                      oid=f"{_EATON_EPDU}.3.1.1.4.0.1",   # inputPower (W)
                      device_class="power", unit="W", state_class="measurement"),
            SensorDef(key="voltage", name="Voltage",
                      oid=f"{_EATON_EPDU}.3.2.1.3.0.1.1",  # inputVoltage (mV)
                      device_class="voltage", unit="V", state_class="measurement",
                      scale=0.001, precision=1),
            SensorDef(key="current", name="Current",
                      oid=f"{_EATON_EPDU}.3.3.1.4.0.1.1",  # inputCurrentValue (mA)
                      device_class="current", unit="A", state_class="measurement",
                      scale=0.001, precision=2),
        ],
    ),

    # =================================================================
    # Raritan PDU (PX2, PX3 series)
    # PDU2-MIB — indexes: pduId=1
    # Note: read state uses 7=on/8=off, write command uses 1=on/2=off
    # =================================================================
    "raritan_pdu": DeviceDef(
        key="raritan_pdu",
        name="Raritan PDU",
        manufacturer="Raritan",
        validation_oid=f"{_RARITAN}.3.5.3.1.3.1.1",  # outletName pdu 1 outlet 1
        outlets=OutletDef(
            state_oid=f"{_RARITAN}.4.1.2.1.3.1",          # switchingState .1.N
            command_oid=f"{_RARITAN}.4.1.2.1.2.1",         # switchingOperation .1.N
            name_oid=f"{_RARITAN}.3.5.3.1.3.1",            # outletName .1.N
            state_on=7,     # on (read)
            state_off=8,    # off (read)
            max_outlets=48,
            command_on=1,   # on (write)
            command_off=2,  # off (write)
            label="Outlet",
        ),
        sensors=[
            SensorDef(key="power", name="Active Power",
                      oid=f"{_RARITAN}.5.2.3.1.4.1.1.5",  # inletSensorValue pdu 1 inlet 1 activePower (W)
                      device_class="power", unit="W", state_class="measurement"),
            SensorDef(key="current", name="RMS Current",
                      oid=f"{_RARITAN}.5.2.3.1.4.1.1.1",  # inletSensorValue pdu 1 inlet 1 rmsCurrent (mA)
                      device_class="current", unit="A", state_class="measurement",
                      scale=0.001, precision=2),
            SensorDef(key="voltage", name="RMS Voltage",
                      oid=f"{_RARITAN}.5.2.3.1.4.1.1.4",  # inletSensorValue pdu 1 inlet 1 rmsVoltage (mV)
                      device_class="voltage", unit="V", state_class="measurement",
                      scale=0.001, precision=1),
            SensorDef(key="apparent_power", name="Apparent Power",
                      oid=f"{_RARITAN}.5.2.3.1.4.1.1.6",  # inletSensorValue pdu 1 inlet 1 apparentPower (VA)
                      device_class="apparent_power", unit="VA", state_class="measurement"),
            SensorDef(key="energy", name="Energy",
                      oid=f"{_RARITAN}.5.2.3.1.4.1.1.7",  # inletSensorValue pdu 1 inlet 1 activeEnergy (Wh)
                      device_class="energy", unit="Wh", state_class="total_increasing"),
        ],
    ),

    # =================================================================
    # Liebert/Vertiv UPS (GXT5, PSI5, EXM, APM)
    # LIEBERT-GP-POWER-MIB (.1.3.6.1.4.1.476.1.42.3.9)
    # =================================================================
    "liebert_ups": DeviceDef(
        key="liebert_ups",
        name="Liebert/Vertiv UPS",
        manufacturer="Vertiv",
        validation_oid=f"{_LIEBERT}.3.9.20.1.0",  # lgpPwrMeasurementPhaseBOutputLoad phase 1
        sensors=[
            SensorDef(key="load", name="Output Load",
                      oid=f"{_LIEBERT}.3.9.20.1.0",       # lgpPwrMeasurementPhaseBOutputLoad (%)
                      device_class=None, unit="%", state_class="measurement",
                      icon="mdi:gauge"),
            SensorDef(key="output_voltage", name="Output Voltage",
                      oid=f"{_LIEBERT}.3.9.30.5.1.60.1",  # lgpPwrMeasurementPointOutputPhaseVoltage phase 1 (0.1 V)
                      device_class="voltage", unit="V", state_class="measurement",
                      scale=0.1, precision=1),
            SensorDef(key="output_current", name="Output Current",
                      oid=f"{_LIEBERT}.3.9.30.5.1.70.1",  # lgpPwrMeasurementPointOutputPhaseCurrent phase 1 (0.1 A)
                      device_class="current", unit="A", state_class="measurement",
                      scale=0.1, precision=1),
            SensorDef(key="power", name="Output Power",
                      oid=f"{_LIEBERT}.3.9.30.5.1.80.1",  # lgpPwrMeasurementPointOutputPhaseApparentPower (VA)
                      device_class="apparent_power", unit="VA", state_class="measurement"),
            SensorDef(key="input_voltage", name="Input Voltage",
                      oid=f"{_LIEBERT}.3.9.30.5.1.10.1",  # lgpPwrMeasurementPointInputPhaseVoltage phase 1 (0.1 V)
                      device_class="voltage", unit="V", state_class="measurement",
                      scale=0.1, precision=1),
            SensorDef(key="battery_capacity", name="Battery Capacity",
                      oid=f"{_LIEBERT}.3.9.20.2.0",       # lgpPwrBatteryCapacityPercent (%)
                      device_class="battery", unit="%", state_class="measurement"),
            SensorDef(key="battery_runtime", name="Runtime Remaining",
                      oid=f"{_LIEBERT}.3.9.20.3.0",       # lgpPwrBatteryTimeRemaining (seconds)
                      device_class="duration", unit="min", state_class="measurement",
                      scale=1 / 60, precision=0),
            SensorDef(key="battery_temperature", name="Battery Temperature",
                      oid=f"{_LIEBERT}.3.9.20.4.0",       # lgpPwrBatteryTemperature (°C)
                      device_class="temperature", unit="°C", state_class="measurement"),
        ],
    ),
}

# Derived lookup for config flow dropdown
DEVICE_TYPES: dict[str, str] = {k: v.name for k, v in DEVICE_REGISTRY.items()}
