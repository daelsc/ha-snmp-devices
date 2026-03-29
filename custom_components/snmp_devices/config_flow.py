"""Config flow for SNMP Devices integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant

from .const import CONF_DEVICE_TYPE, CONF_OUTLET_COUNT, CONF_OUTLET_NAMES, DEFAULT_COMMUNITY, DOMAIN
from .devices import DEVICE_REGISTRY, DEVICE_TYPES, DeviceDef
from .snmp_client import snmp_get

_LOGGER = logging.getLogger(__name__)


async def _snmp_get_value(host: str, community: str, oid: str) -> Any:
    """Perform SNMP GET and return the value, or raise on failure."""
    resp = await snmp_get(host, community, oid)
    if resp.error:
        raise Exception(resp.error)
    if resp.no_such:
        return None
    return resp.value


async def validate_device(
    hass: HomeAssistant, host: str, community: str, device_def: DeviceDef
) -> dict[str, Any]:
    """Validate connection and discover outlets for any device type."""
    _LOGGER.info("Validating %s connection to %s", device_def.name, host)

    # Test connectivity
    try:
        result = await _snmp_get_value(host, community, device_def.validation_oid)
        if result is None:
            raise ValueError(f"Could not read from {device_def.name}")
    except Exception as err:
        raise ValueError(f"Could not connect to {device_def.name}: {err}") from err

    outlet_count = 0
    outlet_names: dict[int, str] = {}

    if device_def.outlets:
        outlets = device_def.outlets

        # Discover outlets
        for num in range(1, outlets.max_outlets + 1):
            oid = f"{outlets.state_oid}.{num}"
            try:
                result = await _snmp_get_value(host, community, oid)
                if result is None:
                    break
                state = int(result)
                if state in (outlets.state_on, outlets.state_off):
                    outlet_count = num
                    outlet_names[num] = f"{outlets.label} {num}"
                else:
                    break
            except Exception as err:
                _LOGGER.debug("Error checking %s %d: %s", outlets.label.lower(), num, err)
                if num == 1:
                    raise ValueError(f"Could not connect: {err}") from err
                break

        # Try to read outlet names from device
        if outlets.name_oid:
            for num in range(1, outlet_count + 1):
                oid = f"{outlets.name_oid}.{num}"
                try:
                    result = await _snmp_get_value(host, community, oid)
                    if result:
                        name = str(result)
                        if name:
                            outlet_names[num] = name
                except Exception:
                    pass

    _LOGGER.info("Discovered %d outlets on %s", outlet_count, device_def.name)
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

            await self.async_set_unique_id(f"{self._device_type}_{self._host}")
            self._abort_if_unique_id_configured()

            device_def = DEVICE_REGISTRY.get(self._device_type)
            if not device_def:
                errors["base"] = "unknown"
            else:
                try:
                    result = await validate_device(self.hass, self._host, self._community, device_def)
                    self._outlet_count = result["outlet_count"]
                    self._discovered_names = result["outlet_names"]

                    if self._outlet_count > 0:
                        return await self.async_step_outlets()
                    else:
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
