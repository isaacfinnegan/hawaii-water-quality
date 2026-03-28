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

from .const import DOMAIN, CONF_RECENT_HOURS, DEFAULT_RECENT_HOURS

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
                active_events = self._filter_recent_events(events, cutoff_time)

                async def fetch_details(event):
                    event_id = event.get("id")
                    try:
                        async with session.get(f"{API_URL_EVENT_DETAILS}{event_id}", headers=headers, timeout=10) as resp:
                            if resp.status == 200:
                                return await resp.json()
                    except Exception:
                        pass
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

    def _process_data(self, events):
        """Process the raw API data."""
        islands = {}
        all_advisories = []

        for event in events:
            island_name = event.get("island", {}).get("cleanName", "Unknown")
            if island_name not in islands:
                islands[island_name] = {
                    "events": [],
                    "active_areas": set(),
                    "advisories": []
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

            # 2. Extract Geometries and calculate centroids for Geo-Location
            for loc in locations:
                geom = loc.get("geometry", "")
                if not geom:
                    continue
                
                coords = re.findall(r"(-?\d+\.\d+)\s+(-?\d+\.\d+)", geom)
                if not coords:
                    continue
                
                # Calculate centroid (average)
                lons = [float(c[0]) for c in coords]
                lats = [float(c[1]) for c in coords]
                avg_lon = sum(lons) / len(lons)
                avg_lat = sum(lats) / len(lats)

                advisory_obj = {
                    "id": f"{event.get('id')}_{loc.get('id') or 0}",
                    "event_id": event.get("id"),
                    "name": loc.get("name") or (list(area_names)[0] if area_names else "Unknown"),
                    "latitude": avg_lat,
                    "longitude": avg_lon,
                    "geometry": geom,
                    "type": event.get("type"),
                    "status": event.get("status"),
                    "island": island_name,
                    "posted_date": event.get("postedDate")
                }
                islands[island_name]["advisories"].append(advisory_obj)
                all_advisories.append(advisory_obj)

        processed_islands = {}
        all_active_areas = set()
        for island_name, data in islands.items():
            processed_islands[island_name] = {
                "events": data["events"],
                "active_areas": sorted(list(data["active_areas"])),
                "advisories": data["advisories"]
            }
            all_active_areas.update(data["active_areas"])

        return {
            "all_active": events,
            "all_active_areas": sorted(list(all_active_areas)),
            "all_advisories": all_advisories,
            "islands": processed_islands,
        }
