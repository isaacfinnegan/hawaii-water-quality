"""Test the Hawaii Water Quality initialization."""
from unittest.mock import MagicMock, patch, AsyncMock
import pytest

from homeassistant.core import HomeAssistant
from custom_components.hawaii_water_quality import async_setup, async_setup_entry
from custom_components.hawaii_water_quality.const import DOMAIN

async def test_setup_registers_resource(hass: HomeAssistant):
    """Test that async_setup registers the Lovelace resource and static path."""
    # Mock Lovelace resources and HTTP
    hass.data["lovelace"] = {"resources": MagicMock()}
    hass.http = MagicMock()
    hass.http.async_register_static_paths = AsyncMock()
    
    with patch("custom_components.hawaii_water_quality.async_register_resource") as mock_resource:
        assert await async_setup(hass, {}) is True
        
        # Verify static path registration attempt
        assert hass.http.async_register_static_paths.called or hass.http.register_static_path.called

async def test_setup_entry(hass: HomeAssistant, mock_config_entry):
    """Test setting up an entry."""
    coordinator = MagicMock()
    coordinator.async_config_entry_first_refresh = AsyncMock(return_value=None)
    
    with patch("custom_components.hawaii_water_quality.HawaiiWaterQualityDataUpdateCoordinator", return_value=coordinator), \
         patch("homeassistant.config_entries.ConfigEntries.async_forward_entry_setups", return_value=None) as mock_forward:
        
        assert await async_setup_entry(hass, mock_config_entry) is True
        assert mock_forward.called
        assert hass.data[DOMAIN][mock_config_entry.entry_id] == coordinator
