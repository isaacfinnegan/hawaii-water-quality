"""Config flow for Hawaii Water Quality integration."""
from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN, 
    NAME, 
    CONF_ISLAND, 
    ISLANDS, 
    CONF_RECENT_HOURS, 
    DEFAULT_RECENT_HOURS,
    CONF_OFFSET_LON,
    CONF_OFFSET_LAT,
    DEFAULT_OFFSET_LON,
    DEFAULT_OFFSET_LAT
)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hawaii Water Quality."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return HawaiiWaterQualityOptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({
                    vol.Required(CONF_ISLAND, default="All"): vol.In(ISLANDS),
                    vol.Required(CONF_RECENT_HOURS, default=DEFAULT_RECENT_HOURS): vol.Coerce(int),
                })
            )

        island_name = ISLANDS[user_input[CONF_ISLAND]]
        return self.async_create_entry(title=f"{NAME} ({island_name})", data=user_input)

class HawaiiWaterQualityOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        # Use the built-in property initialized by the caller in modern HA,
        # but save it explicitly with a different name just in case.
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = {
            vol.Optional(
                CONF_OFFSET_LON,
                default=self._config_entry.options.get(CONF_OFFSET_LON, DEFAULT_OFFSET_LON),
            ): vol.Coerce(float),
            vol.Optional(
                CONF_OFFSET_LAT,
                default=self._config_entry.options.get(CONF_OFFSET_LAT, DEFAULT_OFFSET_LAT),
            ): vol.Coerce(float),
        }

        # Use the description to guide the user to the map click debugger
        return self.async_show_form(
            step_id="init", 
            data_schema=vol.Schema(options),
            description_placeholders={
                "instructions": "Click on the actual location on the map card to see required Lon/Lat deltas to add."
            }
        )
