"""Constants for the SNMP Devices integration."""

DOMAIN = "snmp_devices"

# Default values
DEFAULT_PORT = 161
DEFAULT_COMMUNITY = "private"
DEFAULT_SCAN_INTERVAL = 30

# Config keys
CONF_DEVICE_TYPE = "device_type"
CONF_OUTLET_NAMES = "outlet_names"
CONF_OUTLET_COUNT = "outlet_count"

# Device types
DEVICE_TYPE_CYBERPOWER_PDU = "cyberpower_pdu"
DEVICE_TYPE_APC_UPS = "apc_ups"

DEVICE_TYPES = {
    DEVICE_TYPE_CYBERPOWER_PDU: "CyberPower PDU",
    DEVICE_TYPE_APC_UPS: "APC UPS",
}

# =============================================================================
# CyberPower PDU OIDs
# =============================================================================
CYBERPOWER_BASE_OID = "1.3.6.1.4.1.3808.1.1.3"

# Outlet OIDs (append .X for outlet number)
CYBERPOWER_OID_OUTLET_STATE = f"{CYBERPOWER_BASE_OID}.3.3.1.1.4"
CYBERPOWER_OID_OUTLET_NAME = f"{CYBERPOWER_BASE_OID}.3.2.1.1.2"
CYBERPOWER_OID_OUTLET_COMMAND = f"{CYBERPOWER_BASE_OID}.3.3.1.1.4"

# PDU-level sensors
CYBERPOWER_OID_POWER = f"{CYBERPOWER_BASE_OID}.2.3.1.1.8.1"
CYBERPOWER_OID_ENERGY = f"{CYBERPOWER_BASE_OID}.2.3.1.1.10.1"

# Outlet state values
CYBERPOWER_STATE_ON = 1
CYBERPOWER_STATE_OFF = 2

# =============================================================================
# APC UPS OIDs
# =============================================================================
APC_BASE_OID = "1.3.6.1.4.1.318.1.1.1"

# Outlet group OIDs (append .X for group number)
APC_OID_OUTLET_GROUP_STATE = f"{APC_BASE_OID}.12.3.2.1.3"
APC_OID_OUTLET_GROUP_NAME = f"{APC_BASE_OID}.12.3.2.1.2"

# UPS sensors
APC_OID_OUTPUT_LOAD = f"{APC_BASE_OID}.4.2.3.0"        # Output load in percent
APC_OID_OUTPUT_POWER = f"{APC_BASE_OID}.4.2.8.0"       # Output power in watts
APC_OID_OUTPUT_CURRENT = f"{APC_BASE_OID}.4.2.4.0"    # Output current in 0.1A
APC_OID_BATTERY_CAPACITY = f"{APC_BASE_OID}.2.2.1.0"  # Battery capacity percent
APC_OID_BATTERY_RUNTIME = f"{APC_BASE_OID}.2.2.3.0"   # Runtime remaining in ticks (1/100 sec)
APC_OID_BATTERY_STATUS = f"{APC_BASE_OID}.2.1.1.0"    # Battery status
APC_OID_INPUT_VOLTAGE = f"{APC_BASE_OID}.3.2.1.0"     # Input voltage
APC_OID_OUTPUT_VOLTAGE = f"{APC_BASE_OID}.4.2.1.0"    # Output voltage

# Outlet group state values
APC_STATE_ON = 1
APC_STATE_OFF = 2
