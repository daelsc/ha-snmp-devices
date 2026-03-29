# SNMP Devices Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

A Home Assistant custom integration for monitoring and controlling SNMP-enabled infrastructure devices. Zero external dependencies — uses a built-in SNMPv2c client, so it won't break on Home Assistant upgrades.

## Supported Devices

### Power (PDUs & UPS)

| Type | Manufacturer | Outlets | Sensors |
|------|-------------|---------|---------|
| CyberPower PDU | CyberPower | Yes | Power, energy |
| APC UPS | APC/Schneider | Yes | Power, load, voltage, current, frequency, battery (capacity, runtime, temp, voltage, current) |
| APC Rack PDU | APC/Schneider | Yes | Power, bank current |
| APC Rack PDU2 | APC/Schneider | Yes | Power, energy, phase voltage/current/power |
| Eaton UPS | Eaton | No | Power, load, voltage, current, frequency, battery, ambient temp |
| Eaton ePDU | Eaton | Yes | Power, voltage, current |
| Tripp Lite UPS | Tripp Lite | No | Power, load, voltage, current, frequency, battery |
| Tripp Lite PDU | Tripp Lite | Yes | Power, current, voltage |
| Raritan PDU | Raritan | Yes | Power, current, voltage, apparent power, energy |
| ServerTech Sentry3 | Legrand | Yes | Current, voltage, power, apparent power, energy, power factor |
| ServerTech Sentry4 | Legrand | Yes | Current, voltage, power, energy, power factor |
| Liebert/Vertiv UPS | Vertiv | No | Power, load, voltage, current, battery |
| UPS (RFC 1628) | Generic | No | Power, load, voltage, current, frequency, battery |

### Environmental

| Type | Manufacturer | Sensors |
|------|-------------|---------|
| APC In-Row Cooling | APC/Schneider | Cooling output, rack inlet/supply/return temps, air flow, fan speed |
| APC Environmental Monitor | APC/Schneider | Temperature, humidity |
| Liebert/Vertiv Environmental | Vertiv | Temperature, humidity |

### Networking & Compute

| Type | Manufacturer | Sensors |
|------|-------------|---------|
| Mikrotik RouterOS | Mikrotik | Board/CPU temp, voltage, power, current, fan speed |
| Palo Alto Firewall | Palo Alto | Active sessions, session utilization, GP tunnels |
| Ubiquiti UniFi AP | Ubiquiti | Connected clients |
| Synology NAS | Synology | System temp, disk 1-4 temps |
| Linux / Net-SNMP Host | Generic | CPU user/system/idle %, memory, swap |
| Network Printer | Generic | Page count, supply levels (RFC 3805) |

OIDs that don't exist on a particular model simply show as unavailable — no errors.

## Features

- **Zero dependencies** — built-in SNMPv2c client using only Python stdlib. Nothing to break on HA upgrades.
- **22 device types** covering PDUs, UPSes, cooling, environmental, networking, and compute
- **UI-based configuration** — no YAML required
- **Auto-discovery** of outlets and outlet groups
- **Custom outlet naming** via config flow and options
- **Resilient startup** — integration loads even if first poll fails; entities go unavailable and recover automatically

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots menu > **Custom repositories**
3. Add `daelsc/ha-snmp-devices` and select **Integration**
4. Click **Install**
5. Restart Home Assistant

### Manual

Copy `custom_components/snmp_devices/` to your Home Assistant `custom_components/` directory and restart.

## Configuration

1. **Settings** > **Devices & Services** > **+ Add Integration**
2. Search for **SNMP Devices**
3. Select your device type
4. Enter IP address and SNMP community string (usually `private` for read-write, `public` for read-only)
5. Name outlets if applicable

### SNMP Requirements

- **SNMP v1 or v2c** enabled on the device
- **Community string** with read access (read-write for outlet control)
- **UDP port 161** reachable from Home Assistant

## Adding New Device Types

Device types are defined declaratively in `devices.py`. To add a new device, add one entry to `DEVICE_REGISTRY` — no other files need editing:

```python
"my_device": DeviceDef(
    key="my_device",
    name="My Device",
    manufacturer="Acme",
    validation_oid="1.3.6.1.4.1.XXXX.1.0",  # OID to test connectivity
    outlets=OutletDef(                         # omit if no switchable outlets
        state_oid="1.3.6.1.4.1.XXXX.2",       # append .N for outlet N
        command_oid="1.3.6.1.4.1.XXXX.3",
        name_oid="1.3.6.1.4.1.XXXX.4",
        state_on=1, state_off=2,
        max_outlets=24,
    ),
    sensors=[
        SensorDef(
            key="power", name="Power",
            oid="1.3.6.1.4.1.XXXX.5.0",
            device_class="power", unit="W", state_class="measurement",
        ),
    ],
),
```

## Troubleshooting

### Cannot connect
- Verify IP is reachable: `ping <ip>`
- Check SNMP is enabled on the device
- Test with: `snmpget -v2c -c public <ip> 1.3.6.1.2.1.1.1.0`
- Ensure UDP 161 is not blocked

### Debug logging
```yaml
logger:
  logs:
    custom_components.snmp_devices: debug
```

## License

MIT
