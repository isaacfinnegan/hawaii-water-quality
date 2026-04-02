"""Sensor platform for Hawaii Water Quality."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME, CONF_ISLAND, ISLANDS
from .coordinator import HawaiiWaterQualityDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Hawaii Water Quality sensor platform (legacy)."""
    pass

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Hawaii Water Quality sensor platform."""
    coordinator: HawaiiWaterQualityDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    island_id = entry.data.get(CONF_ISLAND, "All")
    island_name = ISLANDS.get(island_id, "All Islands")
    
    entities = [
        HawaiiWaterQualitySensor(coordinator, island_id, island_name),
    ]
        
    async_add_entities(entities)


class HawaiiWaterQualitySensor(CoordinatorEntity, SensorEntity):
    """Representation of a Hawaii Water Quality sensor."""

    def __init__(
        self, 
        coordinator: HawaiiWaterQualityDataUpdateCoordinator, 
        island_id: str,
        island_name: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.island_id = island_id
        self.island_name = island_name
        self._attr_name = f"{NAME} {island_name}"
        self._attr_unique_id = f"{DOMAIN}_{island_id.lower()}_status"
        self._attr_icon = "mdi:waves"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry.entry_id)},
            name=NAME,
            manufacturer="Hawaii DOH",
            model="Water Quality Integration",
        )

    @property
    def native_value(self) -> int | None:
        """Return the state of the sensor (count of active areas)."""
        if not self.coordinator.data:
            return None
            
        if self.island_id == "All":
            return len(self.coordinator.data.get("all_active_areas", []))
        
        island_data = self.coordinator.data.get("islands", {}).get(self.island_id, {})
        return len(island_data.get("active_areas", []))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        if not self.coordinator.data:
            return {}

        if self.island_id == "All":
            events = self.coordinator.data.get("all_active", [])
            active_areas = self.coordinator.data.get("all_active_areas", [])
            geojson = self.coordinator.data.get("all_geojson", {"type": "FeatureCollection", "features": []})
        else:
            island_data = self.coordinator.data.get("islands", {}).get(self.island_id, {})
            events = island_data.get("events", [])
            active_areas = island_data.get("active_areas", [])
            geojson = island_data.get("geojson", {"type": "FeatureCollection", "features": []})

        res = {
            "island": self.island_id,
            "active_areas": active_areas,
            "advisories": [
                {
                    "title": event.get("title"),
                    "type": event.get("type"),
                    "island": event.get("island", {}).get("name"),
                    "date": event.get("postedDate"),
                }
                for event in events
            ]
        }

        # Only include geojson if it fits (roughly under 15KB)
        import json
        try:
            geojson_str = json.dumps(geojson, separators=(',', ':'))
            if len(geojson_str) < 15500:
                res["geojson"] = geojson
            else:
                # Provide fallback points if full geojson is too large
                if self.island_id == "All":
                    advisories = self.coordinator.data.get("all_advisories", [])
                else:
                    advisories = island_data.get("advisories", [])
                
                res["geojson"] = {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "geometry": {"type": "Point", "coordinates": [a["longitude"], a["latitude"]]},
                            "properties": {
                                "name": a["name"],
                                "type": a["type"],
                                "posted_date": a["posted_date"],
                                "event_id": str(a.get("event_id")),
                                "fallback": True
                            }
                        } for a in advisories
                    ]
                }
        except Exception as e:
            _LOGGER.error("Error processing GeoJSON for sensor: %s", e)

        return res
