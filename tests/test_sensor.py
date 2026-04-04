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

async def test_sensor_geojson_limit(hass, mock_config_entry):
    """Test that geojson is simplified if it exceeds the size limit."""
    coordinator = MagicMock()
    # Create a large geojson
    large_features = []
    # 300 features with polygons should definitely exceed 15500 bytes
    for i in range(300):
        large_features.append({
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [[[i, i], [i+1, i], [i+1, i+1], [i, i+1], [i, i]]]},
            "properties": {"name": f"Area {i}", "event_id": str(i)}
        })
    
    coordinator.data = {
        "all_active_areas": [],
        "all_active": [],
        "all_advisories": [{"latitude": 0, "longitude": 0, "name": "Fallback", "type": "T", "posted_date": "D", "event_id": "1"}],
        "all_geojson": {"type": "FeatureCollection", "features": large_features},
        "islands": {}
    }
    
    sensor = HawaiiWaterQualitySensor(coordinator, "All", "All Islands")
    attrs = sensor.extra_state_attributes
    
    # It should have fallback points instead of the large polygons
    assert "geojson" in attrs
    assert len(attrs["geojson"]["features"]) > 0
    assert attrs["geojson"]["features"][0]["geometry"]["type"] == "Point"
    assert attrs["geojson"]["features"][0]["properties"]["fallback"] is True
