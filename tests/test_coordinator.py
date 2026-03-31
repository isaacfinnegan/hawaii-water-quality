"""Test the Hawaii Water Quality coordinator."""
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import pytest

from custom_components.hawaii_water_quality.coordinator import HawaiiWaterQualityDataUpdateCoordinator
from custom_components.hawaii_water_quality.const import DOMAIN

async def test_coordinator_parsing(hass, mock_config_entry, mock_api_data):
    """Test that the coordinator parses API data correctly."""
    coordinator = HawaiiWaterQualityDataUpdateCoordinator(hass, mock_config_entry)
    
    # Test WKT to GeoJSON conversion with offsets
    wkt = "POINT (-157.8295 21.2765)"
    geojson = coordinator._wkt_to_geojson(wkt, -0.029, 0.097)
    
    assert geojson["type"] == "Point"
    assert round(geojson["coordinates"][0], 4) == round(-157.8295 - 0.029, 4)
    assert round(geojson["coordinates"][1], 4) == round(21.2765 + 0.097, 4)

async def test_fallback_marker(hass, mock_config_entry):
    """Test that fallback markers are created for events without geometry."""
    coordinator = HawaiiWaterQualityDataUpdateCoordinator(hass, mock_config_entry)
    
    # Event with NO locations/geometries
    events = [{
        "id": "bw1",
        "title": "General Brown Water Advisory",
        "status": "Open",
        "postedDate": "2026-03-29T08:00:00.000",
        "island": {"cleanName": "Oahu", "name": "Oahu"},
        "locations": []
    }]
    
    data = coordinator._process_data(events)
    oahu_data = data["islands"].get("Oahu")
    
    assert oahu_data is not None
    assert len(oahu_data["advisories"]) == 1
    assert oahu_data["advisories"][0]["id"] == "bw1_fallback"
    assert oahu_data["advisories"][0]["fallback"] is True
    # Island center for Oahu is approx (-158.0001, 21.4389)
    assert oahu_data["advisories"][0]["longitude"] < -157.9

async def test_filter_recent_events(hass, mock_config_entry):
    """Test the recency filtering logic."""
    coordinator = HawaiiWaterQualityDataUpdateCoordinator(hass, mock_config_entry)
    
    now = datetime.now()
    cutoff = now - timedelta(hours=48)
    
    events = [
        {"status": "Open", "postedDate": now.isoformat()}, # Should keep
        {"status": "Closed", "postedDate": (now - timedelta(hours=10)).isoformat()}, # Should keep (recent)
        {"status": "Closed", "postedDate": (now - timedelta(hours=100)).isoformat()}, # Should drop
    ]
    
    filtered = coordinator._filter_recent_events(events, cutoff)
    assert len(filtered) == 2
