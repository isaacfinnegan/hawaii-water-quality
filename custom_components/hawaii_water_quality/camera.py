"""Camera platform for Hawaii Water Quality."""
from __future__ import annotations

import base64
import logging
import math
import os
import re
from typing import Any

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME, CONF_ISLAND
from .coordinator import HawaiiWaterQualityDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Precise Bounding Boxes for OSM (min_lon, min_lat, max_lon, max_lat)
# These MUST match the bbox used in the curl download commands.
OSM_BOUNDS = {
    "All": (-160.5, 18.8, -154.5, 22.5),
    "Oahu": (-158.35, 21.2, -157.6, 21.75),
    "Maui": (-156.75, 20.5, -155.9, 21.1),
    "Hawaii": (-156.2, 18.8, -154.7, 20.3),
    "Kauai": (-159.9, 21.7, -159.2, 22.3),
    "Molokai": (-157.5, 21.0, -156.6, 21.3),
    "Lanai": (-157.2, 20.6, -156.7, 21.1),
}

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Hawaii Water Quality camera platform."""
    coordinator: HawaiiWaterQualityDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    island_id = entry.data.get(CONF_ISLAND, "All")
    
    async_add_entities([HawaiiWaterQualityCamera(coordinator, island_id)])


class HawaiiWaterQualityCamera(CoordinatorEntity, Camera):
    """Camera that shows a graphic of water quality advisories."""

    def __init__(self, coordinator: HawaiiWaterQualityDataUpdateCoordinator, island_id: str) -> None:
        """Initialize the camera."""
        super().__init__(coordinator)
        Camera.__init__(self)
        self.island_id = island_id
        self._attr_name = f"{NAME} {island_id} Map"
        self._attr_unique_id = f"{DOMAIN}_{island_id.lower()}_map"
        self.content_type = "image/svg+xml"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry.entry_id)},
            name=NAME,
            manufacturer="Hawaii DOH",
            model="Water Quality Integration",
        )

    def camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return a byte representation of the SVG image."""
        svg = self._generate_svg()
        return svg.encode("utf-8")

    def _generate_svg(self) -> str:
        """Generate an SVG image with an embedded high-res background and highlights."""
        bounds = OSM_BOUNDS.get(self.island_id, OSM_BOUNDS["All"])
        min_lon, min_lat, max_lon, max_lat = bounds
        view_w, view_h = 600, 450
        
        # 1. Background Map (Embedded as Base64)
        map_filename = f"osm_{self.island_id.lower()}.png"
        map_path = os.path.join(os.path.dirname(__file__), "maps", map_filename)
        
        encoded_image = ""
        if os.path.exists(map_path):
            try:
                with open(map_path, "rb") as image_file:
                    encoded_image = base64.b64encode(image_file.read()).decode("utf-8")
            except Exception as e:
                _LOGGER.error("Error reading map file %s: %s", map_path, e)

        map_url = f"data:image/png;base64,{encoded_image}" if encoded_image else ""

        # 2. Get GeoJSON Features
        if self.island_id == "All":
            features = self.coordinator.data.get("all_geojson", {}).get("features", [])
        else:
            island_data = self.coordinator.data.get("islands", {}).get(self.island_id, {})
            features = island_data.get("geojson", {}).get("features", [])

        # Start SVG
        svg = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {view_w} {view_h}" width="100%" height="100%">',
            '<!-- Solid White Background -->',
            f'<rect x="0" y="0" width="{view_w}" height="{view_h}" fill="white" />',
            '<!-- Base Map Background -->',
            f'<image href="{map_url}" x="0" y="0" width="{view_w}" height="{view_h}" preserveAspectRatio="none" />',
            # Slight darkening overlay
            f'<rect x="0" y="0" width="{view_w}" height="{view_h}" fill="black" fill-opacity="0.03" />',
            f'<text x="10" y="25" font-family="Arial" font-size="16" fill="white" font-weight="bold" stroke="black" stroke-width="0.5">{self.island_id} Water Quality</text>'
        ]

        def lat_to_y(lat):
            """Convert latitude to Y coordinate using Mercator projection."""
            lat_rad = math.radians(lat)
            return math.log(math.tan(math.pi / 4 + lat_rad / 2))

        merc_min_y = lat_to_y(min_lat)
        merc_max_y = lat_to_y(max_lat)

        def project(lon, lat):
            """Project lon/lat to SVG coordinates."""
            x = (lon - min_lon) / (max_lon - min_lon) * view_w
            merc_y = lat_to_y(lat)
            y = (1 - (merc_y - merc_min_y) / (merc_max_y - merc_min_y)) * view_h
            return x, y

        # Colors
        highlight_fill = "#D2B48C" # Tan
        highlight_stroke = "#CD853F" # Peru

        # Draw geometries from GeoJSON
        for feature in features:
            geom = feature.get("geometry", {})
            props = feature.get("properties", {})
            geom_type = geom.get("type")
            coords = geom.get("coordinates", [])
            title = props.get("name", "Advisory")

            if geom_type == "Polygon":
                # GeoJSON Polygon coords are list of lists of [lon, lat]
                points = []
                # Assuming simple polygon with one outer ring
                if coords and len(coords) > 0:
                    for lon, lat in coords[0]:
                        x, y = project(lon, lat)
                        points.append(f"{x},{y}")
                    poly_points = " ".join(points)
                    svg.append(f'<polygon points="{poly_points}" fill="{highlight_fill}" fill-opacity="0.5" stroke="{highlight_stroke}" stroke-width="3">')
                    svg.append(f'<title>{title}</title></polygon>')
                
            elif geom_type == "LineString":
                points = []
                for lon, lat in coords:
                    x, y = project(lon, lat)
                    points.append(f"{x},{y}")
                poly_points = " ".join(points)
                svg.append(f'<polyline points="{poly_points}" fill="none" stroke="{highlight_stroke}" stroke-width="6" stroke-linecap="round">')
                svg.append(f'<title>{title}</title></polyline>')
                
            elif geom_type == "Point":
                if len(coords) >= 2:
                    lon, lat = coords[0], coords[1]
                    x, y = project(lon, lat)
                    # Draw a pulse or large circle for points to make them visible
                    svg.append(f'<circle cx="{x}" cy="{y}" r="9" fill="{highlight_stroke}" fill-opacity="0.8">')
                    svg.append(f'<title>{title}</title></circle>')
                    svg.append(f'<circle cx="{x}" cy="{y}" r="18" fill="{highlight_fill}" fill-opacity="0.3" stroke="{highlight_stroke}" stroke-width="1" />')

        svg.append('</svg>')
        return "".join(svg)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        if self.island_id == "All":
            island_data = self.coordinator.data
            active_areas = island_data.get("all_active_areas", [])
            events = island_data.get("all_active", [])
        else:
            island_data = self.coordinator.data.get("islands", {}).get(self.island_id, {})
            active_areas = island_data.get("active_areas", [])
            events = island_data.get("events", [])

        # Include geometries in attributes for debugging
        geometries = []
        for event in events:
            for loc in event.get("locations", []):
                if loc.get("geometry"):
                    geometries.append({
                        "area": loc.get("name") or event.get("locationName"),
                        "wkt": loc.get("geometry")
                    })

        return {
            "island": self.island_id,
            "active_areas": active_areas,
            "debug_geometries": geometries[:10] # Cap for context size
        }
