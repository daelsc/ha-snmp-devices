# SNMP Devices Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

A Home Assistant integration for managing SNMP-enabled power devices including CyberPower PDUs and APC UPS units.

## Supported Devices

### CyberPower PDU

Tested and confirmed working:
- **PDU41001** - Switched ATS PDU

Other CyberPower Switched ePDU models using the standard CyberPower MIB (OID base 1.3.6.1.4.1.3808.1.1.3) may also work but are untested.

### APC UPS

Tested and confirmed working:
- **Smart-UPS 3000-X** (SMX3000RMHV2UNC)

Other APC UPS models with Network Management Cards and switchable outlet groups may also work but are untested.

**Requirements**:
- SNMP must be enabled with read-write access
- Device must have switchable outlets/outlet groups for switch control

## Features

### CyberPower PDU
- **Switches**: Control individual outlets (on/off)
- **Sensors**:
  - Total Power (W)
  - Total Energy (kWh)

### APC UPS
- **Switches**: Control outlet groups (on/off)
- **Sensors**:
  - Output Power (W)
  - Load (%)
  - Battery Capacity (%)
  - Runtime Remaining (minutes)
  - Input Voltage (V)

### Key Features
- UI-based configuration (no YAML required)
- Auto-discovery of outlets/outlet groups
- Custom naming for each outlet
- Reconfigure outlet names anytime via integration options
- Efficient polling with shared data coordinator

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots menu → "Custom repositories"
3. Add this repository URL and select "Integration" as the category
4. Click "Install"
5. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/snmp_devices` folder to your Home Assistant's `custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "SNMP Devices"
4. Select your device type (CyberPower PDU or APC UPS)
5. Enter the device IP address and SNMP community string (usually `private`)
6. Configure outlet names as desired

## SNMP Requirements

Your device must have SNMP enabled with read-write access:
- **Community string**: Usually `private` for read-write, `public` for read-only
- **SNMP version**: v1 or v2c
- **Port**: 161 (UDP)

### Enabling SNMP on CyberPower PDU
1. Access the PDU web interface
2. Navigate to Network → SNMP Settings
3. Enable SNMP v1/v2c
4. Set the read-write community string

### Enabling SNMP on APC Network Management Card
1. Access the NMC web interface
2. Navigate to Configuration → Network → SNMPv1 → Access Control
3. Enable SNMPv1
4. Configure a community with read-write access

## Supported OIDs

### CyberPower PDU
| Function | OID |
|----------|-----|
| Outlet State | 1.3.6.1.4.1.3808.1.1.3.3.3.1.1.4.X |
| Outlet Name | 1.3.6.1.4.1.3808.1.1.3.3.2.1.1.2.X |
| Total Power | 1.3.6.1.4.1.3808.1.1.3.2.3.1.1.8.1 |
| Total Energy | 1.3.6.1.4.1.3808.1.1.3.2.3.1.1.10.1 |

### APC UPS
| Function | OID |
|----------|-----|
| Outlet Group State | 1.3.6.1.4.1.318.1.1.1.12.3.2.1.3.X |
| Output Power | 1.3.6.1.4.1.318.1.1.1.4.2.8.0 |
| Output Load | 1.3.6.1.4.1.318.1.1.1.4.2.3.0 |
| Battery Capacity | 1.3.6.1.4.1.318.1.1.1.2.2.1.0 |
| Battery Runtime | 1.3.6.1.4.1.318.1.1.1.2.2.3.0 |
| Input Voltage | 1.3.6.1.4.1.318.1.1.1.3.2.1.0 |

## Troubleshooting

### Cannot connect to device
- Verify the IP address is correct and device is reachable (`ping <ip>`)
- Check SNMP is enabled on the device
- Verify the community string (try `public` for read-only test)
- Ensure UDP port 161 is not blocked by firewall

### Outlets not discovered
- Some devices may have fewer outlets than expected
- Check device documentation for SNMP support
- Verify your device model has switchable outlets

### Enable debug logging
Add to `configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.snmp_devices: debug
```

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

If you have a different CyberPower or APC model and confirm it works, please open an issue to add it to the tested devices list.

## License

MIT License - see LICENSE file for details.
