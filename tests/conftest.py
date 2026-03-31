"""Fixtures for Hawaii Water Quality tests."""
import pytest
from unittest.mock import patch, MagicMock

from homeassistant.core import HomeAssistant
from custom_components.hawaii_water_quality.const import DOMAIN

@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(hass: HomeAssistant):
    """Enable custom integrations in Home Assistant."""
    yield

@pytest.fixture
def mock_config_entry():
    """Return a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.data = {"island": "Oahu", "recent_hours": 48}
    entry.options = {"offset_lon": 0.0, "offset_lat": 0.0}
    return entry

@pytest.fixture
def mock_api_data():
    """Return a sample API response."""
    return {
        "list": [
            {
                "id": "123",
                "title": "Wastewater Discharge at Waikiki",
                "status": "Open",
                "postedDate": "2026-03-29T08:00:00.000",
                "island": {"cleanName": "Oahu", "name": "Oahu"},
                "locations": [
                    {
                        "id": "loc1",
                        "name": "Waikiki Beach",
                        "geometry": "POINT (-157.8295 21.2765)"
                    }
                ]
            }
        ]
    }

@pytest.fixture
def mock_api_details():
    """Return sample detail response."""
    return {
        "id": "123",
        "locations": [
            {
                "id": "loc1",
                "name": "Waikiki Beach",
                "geometry": "POINT (-157.8295 21.2765)"
            }
        ]
    }
