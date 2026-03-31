"""Test the Hawaii Water Quality sensor platform."""
from unittest.mock import MagicMock
import pytest

from custom_components.hawaii_water_quality.sensor import HawaiiWaterQualitySensor
from custom_components.hawaii_water_quality.const import DOMAIN

async def test_sensor_state(hass, mock_config_entry):
    """Test sensor state and attributes."""
    coordinator = MagicMock()
    coordinator.data = {
        "all_active_areas": ["Waikiki", "Diamond Head"],
        "islands": {
            "Oahu": {
                "active_areas": ["Waikiki"],
                "events": [{"title": "Test Event", "postedDate": "2026-03-29"}],
                "geojson": {"type": "FeatureCollection", "features": []}
            }
        }
    }
    
    # Test Island-specific sensor
    sensor = HawaiiWaterQualitySensor(coordinator, "Oahu", "Oʻahu")
    assert sensor.native_value == 1
    attrs = sensor.extra_state_attributes
    assert "Waikiki" in attrs["active_areas"]
    assert len(attrs["advisories"]) == 1

    # Test "All Islands" sensor
    sensor_all = HawaiiWaterQualitySensor(coordinator, "All", "All Islands")
    assert sensor_all.native_value == 2
