"""Test the Hawaii Water Quality config flow."""
from unittest.mock import patch, MagicMock, AsyncMock
import pytest

from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant
from custom_components.hawaii_water_quality.const import DOMAIN
from custom_components.hawaii_water_quality.config_flow import ConfigFlow

async def test_user_step(hass: HomeAssistant) -> None:
    """Test the user step works."""
    mock_integration = MagicMock(domain=DOMAIN)
    mock_component = MagicMock()
    mock_integration.async_get_component = AsyncMock(return_value=mock_component)
    mock_integration.async_get_platform = AsyncMock()
    
    with patch("homeassistant.config_entries._async_get_flow_handler", return_value=ConfigFlow), \
         patch("homeassistant.loader.async_get_integration", return_value=mock_integration):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "user"

        with patch(
            "custom_components.hawaii_water_quality.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry:
            mock_component.async_setup_entry = mock_setup_entry
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {"island": "Oahu", "recent_hours": 48},
            )
            await hass.async_block_till_done()

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "Hawaii Ocean Water Quality (O\u2018ahu)"
    assert result["data"] == {"island": "Oahu", "recent_hours": 48}
    assert len(mock_setup_entry.mock_calls) == 1

async def test_options_flow(hass: HomeAssistant) -> None:
    """Test the options flow."""
    entry = config_entries.ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Hawaii Water Quality",
        data={"island": "Oahu", "recent_hours": 48},
        source="user",
        options={},
        entry_id="test",
        discovery_keys={},
        unique_id=None,
        subentries_data=[],
    )
    # entry.add_to_hass(hass) is deprecated/removed in newer HA
    hass.config_entries._entries[entry.entry_id] = entry

    mock_integration = MagicMock(domain=DOMAIN)
    mock_integration.async_get_component = AsyncMock()
    mock_integration.async_get_platform = AsyncMock()
    with patch("homeassistant.config_entries._async_get_flow_handler", return_value=ConfigFlow), \
         patch("homeassistant.loader.async_get_integration", return_value=mock_integration):
        result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"offset_lon": -0.029, "offset_lat": 0.097},
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert entry.options == {"offset_lon": -0.029, "offset_lat": 0.097}
