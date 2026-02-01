"""Config flow for SNMP Devices integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant

from .const import (
    APC_OID_OUTLET_GROUP_STATE,
    APC_OID_OUTPUT_POWER,
    APC_STATE_ON,
    APC_STATE_OFF,
    CONF_DEVICE_TYPE,
    CONF_OUTLET_COUNT,
    CONF_OUTLET_NAMES,
    CYBERPOWER_OID_OUTLET_NAME,
    CYBERPOWER_OID_OUTLET_STATE,
    CYBERPOWER_STATE_ON,
    CYBERPOWER_STATE_OFF,
    DEFAULT_COMMUNITY,
    DEVICE_TYPE_APC_UPS,
    DEVICE_TYPE_CYBERPOWER_PDU,
    DEVICE_TYPES,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def _async_snmp_get(host: str, community: str, oid: str) -> Any:
    """Perform async SNMP GET."""
    from pysnmp.hlapi.v1arch.asyncio import (
        CommunityData,
        ObjectIdentity,
        ObjectType,
        SnmpDispatcher,
        UdpTransportTarget,
        get_cmd,
    )

    dispatcher = SnmpDispatcher()

    try:
        transport = await UdpTransportTarget.create((host, 161), timeout=2, retries=1)

        error_indication, error_status, error_index, var_binds = await get_cmd(
            dispatcher,
            CommunityData(community, mpModel=1),
            transport,
            ObjectType(ObjectIdentity(oid)),
        )

        if error_indication:
            raise Exception(f"SNMP error: {error_indication}")
        if error_status:
            raise Exception(f"SNMP error: {error_status.prettyPrint()}")

        if var_binds:
            return var_binds[0][1]
        return None
    finally:
        dispatcher.transport_dispatcher.close_dispatcher()


async def validate_cyberpower(hass: HomeAssistant, host: str, community: str) -> dict[str, Any]:
    """Validate CyberPower PDU connection and discover outlets."""
    outlet_names: dict[int, str] = {}
    outlet_count = 0

    _LOGGER.info("Validating CyberPower PDU connection to %s", host)

    # Discover outlets
    for outlet_num in range(1, 25):
        oid = f"{CYBERPOWER_OID_OUTLET_STATE}.{outlet_num}"
        try:
            result = await _async_snmp_get(host, community, oid)

            if result is None:
                break

            result_str = str(result)
            if 'NoSuchInstance' in result_str or 'NoSuchObject' in result_str:
                break

            state = int(result)
            if state in (CYBERPOWER_STATE_ON, CYBERPOWER_STATE_OFF):
                outlet_count = outlet_num
            else:
                break
        except Exception as err:
            _LOGGER.debug("Error checking outlet %d: %s", outlet_num, err)
            if outlet_num == 1:
                raise ValueError(f"Could not connect: {err}") from err
            break

    if outlet_count == 0:
        raise ValueError("Could not discover any outlets.")

    # Get outlet names
    for outlet_num in range(1, outlet_count + 1):
        oid = f"{CYBERPOWER_OID_OUTLET_NAME}.{outlet_num}"
        try:
            result = await _async_snmp_get(host, community, oid)
            if result:
                name = str(result)
                if name and 'NoSuchInstance' not in name and 'NoSuchObject' not in name:
                    outlet_names[outlet_num] = name
                else:
                    outlet_names[outlet_num] = f"Outlet {outlet_num}"
            else:
                outlet_names[outlet_num] = f"Outlet {outlet_num}"
        except Exception:
            outlet_names[outlet_num] = f"Outlet {outlet_num}"

    return {"outlet_count": outlet_count, "outlet_names": outlet_names}


async def validate_apc(hass: HomeAssistant, host: str, community: str) -> dict[str, Any]:
    """Validate APC UPS connection and discover outlet groups."""
    outlet_names: dict[int, str] = {}
    outlet_count = 0

    _LOGGER.info("Validating APC UPS connection to %s", host)

    # First check if we can connect by reading output power
    try:
        result = await _async_snmp_get(host, community, APC_OID_OUTPUT_POWER)
        if result is None:
            raise ValueError("Could not read UPS power data")
    except Exception as err:
        raise ValueError(f"Could not connect to APC UPS: {err}") from err

    # Discover outlet groups
    for group_num in range(1, 10):
        oid = f"{APC_OID_OUTLET_GROUP_STATE}.{group_num}"
        try:
            result = await _async_snmp_get(host, community, oid)

            if result is None:
                break

            result_str = str(result)
            if 'NoSuchInstance' in result_str or 'NoSuchObject' in result_str:
                break

            state = int(result)
            if state in (APC_STATE_ON, APC_STATE_OFF):
                outlet_count = group_num
                outlet_names[group_num] = f"Outlet Group {group_num}"
            else:
                break
        except Exception as err:
            _LOGGER.debug("Error checking outlet group %d: %s", group_num, err)
            break

    _LOGGER.info("Discovered %d outlet groups on APC UPS", outlet_count)

    return {"outlet_count": outlet_count, "outlet_names": outlet_names}


class SNMPDevicesConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SNMP Devices."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._device_type: str | None = None
        self._host: str | None = None
        self._community: str | None = None
        self._name: str | None = None
        self._outlet_count: int = 0
        self._discovered_names: dict[int, str] = {}

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return SNMPDevicesOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle device type selection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._device_type = user_input[CONF_DEVICE_TYPE]
            return await self.async_step_connection()

        schema = vol.Schema({
            vol.Required(CONF_DEVICE_TYPE): vol.In(DEVICE_TYPES),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_connection(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle connection details."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._host = user_input[CONF_HOST]
            self._community = user_input["community"]
            self._name = user_input.get(CONF_NAME, self._host)

            # Check if already configured
            await self.async_set_unique_id(f"{self._device_type}_{self._host}")
            self._abort_if_unique_id_configured()

            try:
                if self._device_type == DEVICE_TYPE_CYBERPOWER_PDU:
                    result = await validate_cyberpower(self.hass, self._host, self._community)
                elif self._device_type == DEVICE_TYPE_APC_UPS:
                    result = await validate_apc(self.hass, self._host, self._community)
                else:
                    raise ValueError(f"Unknown device type: {self._device_type}")

                self._outlet_count = result["outlet_count"]
                self._discovered_names = result["outlet_names"]

                if self._outlet_count > 0:
                    return await self.async_step_outlets()
                else:
                    # No outlets, create entry directly
                    return self._create_entry()

            except ValueError as err:
                _LOGGER.error("Validation error: %s", err)
                errors["base"] = "cannot_connect"
            except Exception as err:
                _LOGGER.exception("Unexpected exception: %s", err)
                errors["base"] = "unknown"

        schema = vol.Schema({
            vol.Required(CONF_HOST): str,
            vol.Required("community", default=DEFAULT_COMMUNITY): str,
            vol.Optional(CONF_NAME): str,
        })

        return self.async_show_form(
            step_id="connection",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "device_type": DEVICE_TYPES.get(self._device_type, self._device_type),
            },
        )

    async def async_step_outlets(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle outlet naming step."""
        if user_input is not None:
            outlet_names = {}
            for outlet_num in range(1, self._outlet_count + 1):
                key = f"outlet_{outlet_num}"
                outlet_names[outlet_num] = user_input.get(key, f"Outlet {outlet_num}")

            return self._create_entry(outlet_names)

        schema_dict = {}
        for outlet_num in range(1, self._outlet_count + 1):
            default_name = self._discovered_names.get(outlet_num, f"Outlet {outlet_num}")
            schema_dict[vol.Required(f"outlet_{outlet_num}", default=default_name)] = str

        return self.async_show_form(
            step_id="outlets",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={
                "outlet_count": str(self._outlet_count),
            },
        )

    def _create_entry(self, outlet_names: dict[int, str] | None = None) -> ConfigFlowResult:
        """Create the config entry."""
        return self.async_create_entry(
            title=self._name or self._host,
            data={
                CONF_HOST: self._host,
                "community": self._community,
                CONF_NAME: self._name or self._host,
                CONF_DEVICE_TYPE: self._device_type,
                CONF_OUTLET_COUNT: self._outlet_count,
                CONF_OUTLET_NAMES: outlet_names or {},
            },
        )


class SNMPDevicesOptionsFlow(OptionsFlow):
    """Handle options flow for SNMP Devices."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            outlet_count = self._config_entry.data.get(CONF_OUTLET_COUNT, 0)
            outlet_names = {}
            for outlet_num in range(1, outlet_count + 1):
                key = f"outlet_{outlet_num}"
                outlet_names[outlet_num] = user_input.get(key, f"Outlet {outlet_num}")

            new_data = {**self._config_entry.data, CONF_OUTLET_NAMES: outlet_names}
            self.hass.config_entries.async_update_entry(self._config_entry, data=new_data)
            await self.hass.config_entries.async_reload(self._config_entry.entry_id)

            return self.async_create_entry(title="", data={})

        outlet_count = self._config_entry.data.get(CONF_OUTLET_COUNT, 0)
        current_names = self._config_entry.data.get(CONF_OUTLET_NAMES, {})

        if outlet_count == 0:
            return self.async_abort(reason="no_outlets")

        schema_dict = {}
        for outlet_num in range(1, outlet_count + 1):
            current_name = current_names.get(outlet_num) or current_names.get(
                str(outlet_num), f"Outlet {outlet_num}"
            )
            schema_dict[vol.Required(f"outlet_{outlet_num}", default=current_name)] = str

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_dict),
        )
