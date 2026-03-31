"""Test the Hawaii Water Quality camera platform."""
from unittest.mock import MagicMock, patch
import pytest

from custom_components.hawaii_water_quality.camera import HawaiiWaterQualityCamera
from custom_components.hawaii_water_quality.const import DOMAIN

async def test_camera_svg_generation(hass, mock_config_entry):
    """Test that the camera generates a valid responsive SVG."""
    coordinator = MagicMock()
    coordinator.data = {
        "all_geojson": {"type": "FeatureCollection", "features": []},
        "islands": {
            "Oahu": {
                "geojson": {
                    "type": "FeatureCollection", 
                    "features": [
                        {
                            "type": "Feature",
                            "geometry": {"type": "Point", "coordinates": [-157.8, 21.3]},
                            "properties": {"name": "Test Point"}
                        }
                    ]
                }
            }
        }
    }
    
    camera = HawaiiWaterQualityCamera(coordinator, "Oahu")
    
    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", MagicMock()):
        svg = camera._generate_svg()
        
    assert 'width="100%"' in svg
    assert 'height="100%"' in svg
    assert 'viewBox="0 0 600 450"' in svg
    assert 'Oahu Water Quality' in svg
    # Point markers: circle with radius 9 and 18
    assert 'r="9"' in svg
    assert 'r="18"' in svg
