"""DataUpdateCoordinator for Hawaii Water Quality."""
from __future__ import annotations

import asyncio
import json
import logging
import re
import socket
import urllib.request
from datetime import datetime, timedelta

import aiohttp
import async_timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN, 
    CONF_RECENT_HOURS, 
    DEFAULT_RECENT_HOURS, 
    CONF_OFFSET_LON, 
    CONF_OFFSET_LAT,
    DEFAULT_OFFSET_LON,
    DEFAULT_OFFSET_LAT
)

_LOGGER = logging.getLogger(__name__)

API_URL_EVENTS = "https://eha-cloud.doh.hawaii.gov/cwb/api/json/reply/GetEvents"
API_URL_EVENT_DETAILS = "https://eha-cloud.doh.hawaii.gov/cwb/api/json/reply/GetEvent?id="
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

class HawaiiWaterQualityDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Hawaii Water Quality data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=15),
        )
        self.entry = entry

    async def _async_update_data(self):
        """Fetch data from API with resilient fallback."""
        recent_hours = self.entry.data.get(CONF_RECENT_HOURS, DEFAULT_RECENT_HOURS)
        cutoff_time = datetime.now() - timedelta(hours=recent_hours)
        
        try:
            # Try aiohttp first (standard way)
            return await self._fetch_via_aiohttp(cutoff_time)
        except Exception as err:
            _LOGGER.warning("aiohttp fetch failed, trying synchronous fallback: %s", err)
            try:
                # Fallback to synchronous urllib in an executor (resilient to container network bugs)
                return await self.hass.async_add_executor_job(self._fetch_via_urllib, cutoff_time)
            except Exception as fallback_err:
                _LOGGER.error("All fetch attempts failed: %s", fallback_err)
                raise UpdateFailed(f"Error communicating with API: {fallback_err}") from fallback_err

    async def _fetch_via_aiohttp(self, cutoff_time: datetime):
        """Fetch using aiohttp."""
        async with async_timeout.timeout(30):
            headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
            # Force IPv4 to fix macOS Docker routing issues
            connector = aiohttp.TCPConnector(family=socket.AF_INET)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(API_URL_EVENTS, headers=headers) as response:
                    if response.status != 200:
                        raise Exception(f"API List Status: {response.status}")
                    data = await response.json()
                
                events = data.get("list", [])
                _LOGGER.debug("Fetched %s events from API", len(events))
                active_events = self._filter_recent_events(events, cutoff_time)
                _LOGGER.debug("Found %s active/recent events", len(active_events))

                sem = asyncio.Semaphore(1) # Fetch one-by-one

                async def fetch_details(event):
                    event_id = event.get("id")
                    async with sem:
                        try:
                            # Cooldown between requests to avoid rate limiting
                            await asyncio.sleep(0.5)
                            async with session.get(f"{API_URL_EVENT_DETAILS}{event_id}", headers=headers, timeout=25) as resp:
                                if resp.status == 200:
                                    res_data = await resp.json()
                                    _LOGGER.debug("Fetched details for event %s: %s locations", event_id, len(res_data.get("locations", [])))
                                    return res_data
                                _LOGGER.warning("Failed to fetch details for event %s: Status %s", event_id, resp.status)
                        except Exception as e:
                            _LOGGER.warning("Error fetching details for event %s: %s", event_id, e)
                    return event

                detailed_events = await asyncio.gather(*[fetch_details(e) for e in active_events])
                return self._process_data(detailed_events)

    def _fetch_via_urllib(self, cutoff_time: datetime):
        """Fetch using synchronous urllib (resilient to async network bugs)."""
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        
        # 1. Get List
        req = urllib.request.Request(API_URL_EVENTS, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as response:
            data = json.loads(response.read().decode())
        
        events = data.get("list", [])
        active_events = self._filter_recent_events(events, cutoff_time)

        # 2. Get Details
        detailed_events = []
        for event in active_events:
            event_id = event.get("id")
            try:
                detail_req = urllib.request.Request(f"{API_URL_EVENT_DETAILS}{event_id}", headers=headers)
                with urllib.request.urlopen(detail_req, timeout=10) as resp:
                    detailed_events.append(json.loads(resp.read().decode()))
            except Exception:
                detailed_events.append(event)
        
        return self._process_data(detailed_events)

    def _filter_recent_events(self, events: list, cutoff_time: datetime):
        """Filter events by Open status or Recency."""
        active = []
        for e in events:
            p_str = e.get("postedDate")
            if not p_str:
                continue
            try:
                # API format: 2026-03-27T01:11:12.9400000
                p_date = datetime.fromisoformat(p_str.split(".")[0])
                if e.get("status") == "Open" or p_date > cutoff_time:
                    active.append(e)
            except Exception:
                if e.get("status") == "Open":
                    active.append(e)
        return active

    def _wkt_to_geojson(self, wkt: str, offset_lon: float, offset_lat: float) -> dict[str, Any] | None:
        """Convert a WKT-like string to GeoJSON geometry."""
        coords = re.findall(r"(-?\d+\.\d+)\s+(-?\d+\.\d+)", wkt)
        if not coords:
            return None
        
        # Apply configurable offset
        points = [[float(c[0]) + offset_lon, float(c[1]) + offset_lat] for c in coords]
        
        if "POLYGON" in wkt.upper():
            return {"type": "Polygon", "coordinates": [points]}
        if "LINESTRING" in wkt.upper():
            return {"type": "LineString", "coordinates": points}
        if "POINT" in wkt.upper():
            return {"type": "Point", "coordinates": points[0]}
        
        return None

    def _process_data(self, events):
        """Process the raw API data."""
        islands = {}
        all_features = []
        all_advisories = []
        
        offset_lon = self.entry.options.get(CONF_OFFSET_LON, self.entry.data.get(CONF_OFFSET_LON, DEFAULT_OFFSET_LON))
        offset_lat = self.entry.options.get(CONF_OFFSET_LAT, self.entry.data.get(CONF_OFFSET_LAT, DEFAULT_OFFSET_LAT))

        # Island Centers for Fallback Markers
        island_centers = {
            "Oahu": (-158.0001, 21.4389),
            "Maui": (-156.3319, 20.7984),
            "Hawaii": (-155.5230, 19.5667),
            "Kauai": (-159.5261, 22.0964),
            "Molokai": (-157.0226, 21.1344),
            "Lanai": (-156.9273, 20.8166),
        }

        for event in events:
            island_name = event.get("island", {}).get("cleanName", "Unknown")
            if island_name not in islands:
                islands[island_name] = {
                    "events": [],
                    "active_areas": set(),
                    "advisories": [],
                    "features": []
                }
            
            islands[island_name]["events"].append(event)
            
            # 1. Extract unique area names
            area_names = set()
            locations = event.get("locations", [])
            for location in locations:
                name = location.get("name") or location.get("cleanName")
                if name:
                    area_names.add(name)
            
            if not area_names:
                fallback_name = event.get("locationName")
                if not fallback_name:
                    title = event.get("title", "")
                    fallback_name = title.split(" at ")[-1].split(",")[0].strip() if " at " in title else title
                if fallback_name:
                    area_names.add(fallback_name)
            
            for name in area_names:
                islands[island_name]["active_areas"].add(name)

            # 2. Extract Geometries and generate GeoJSON
            has_geometry = False
            for loc in locations:
                geom_wkt = loc.get("geometry", "")
                if not geom_wkt:
                    continue
                
                geojson_geom = self._wkt_to_geojson(geom_wkt, offset_lon, offset_lat)
                if not geojson_geom:
                    continue
                
                has_geometry = True
                # Calculate centroid for legacy geo_location support
                coords = geojson_geom["coordinates"]
                if geojson_geom["type"] == "Polygon":
                    raw_coords = coords[0]
                elif geojson_geom["type"] == "LineString":
                    raw_coords = coords
                else: # Point
                    raw_coords = [coords]
                
                avg_lon = sum(c[0] for c in raw_coords) / len(raw_coords)
                avg_lat = sum(c[1] for c in raw_coords) / len(raw_coords)

                properties = {
                    "name": loc.get("name") or (list(area_names)[0] if area_names else "Unknown"),
                    "type": event.get("type"),
                    "status": event.get("status"),
                    "island": island_name,
                    "posted_date": event.get("postedDate"),
                    "event_id": event.get("id"),
                    "color": "#CD853F" # Peru
                }

                feature = {
                    "type": "Feature",
                    "geometry": geojson_geom,
                    "properties": properties
                }

                advisory_obj = {
                    "id": f"{event.get('id')}_{loc.get('id') or 0}",
                    "latitude": avg_lat,
                    "longitude": avg_lon,
                    "geometry": geojson_geom,
                    **properties
                }

                islands[island_name]["features"].append(feature)
                islands[island_name]["advisories"].append(advisory_obj)
                all_features.append(feature)
                all_advisories.append(advisory_obj)

            # Fallback point for events with no geometry (e.g. general island-wide Brown Water Advisories)
            if not has_geometry and island_name in island_centers:
                lon, lat = island_centers[island_name]
                # Apply configurable offset even to fallback points for consistency
                lon += offset_lon
                lat += offset_lat
                
                geojson_geom = {"type": "Point", "coordinates": [lon, lat]}
                properties = {
                    "name": list(area_names)[0] if area_names else event.get("title"),
                    "type": event.get("type"),
                    "status": event.get("status"),
                    "island": island_name,
                    "posted_date": event.get("postedDate"),
                    "event_id": event.get("id"),
                    "color": "#CD853F",
                    "fallback": True
                }
                feature = {"type": "Feature", "geometry": geojson_geom, "properties": properties}
                advisory_obj = {"id": f"{event.get('id')}_fallback", "latitude": lat, "longitude": lon, "geometry": geojson_geom, **properties}
                
                islands[island_name]["features"].append(feature)
                islands[island_name]["advisories"].append(advisory_obj)
                all_features.append(feature)
                all_advisories.append(advisory_obj)

        processed_islands = {}
        all_active_areas = set()
        for island_name, data in islands.items():
            processed_islands[island_name] = {
                "events": data["events"],
                "active_areas": sorted(list(data["active_areas"])),
                "advisories": data["advisories"],
                "geojson": {"type": "FeatureCollection", "features": data["features"]}
            }
            all_active_areas.update(data["active_areas"])

        return {
            "all_active": events,
            "all_active_areas": sorted(list(all_active_areas)),
            "all_geojson": {"type": "FeatureCollection", "features": all_features},
            "all_advisories": all_advisories,
            "islands": processed_islands,
        }
