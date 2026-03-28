"""Config flow for Hawaii Water Quality integration."""
from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, NAME, CONF_ISLAND, ISLANDS, CONF_RECENT_HOURS, DEFAULT_RECENT_HOURS

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hawaii Water Quality."""

    VERSION = 1

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
