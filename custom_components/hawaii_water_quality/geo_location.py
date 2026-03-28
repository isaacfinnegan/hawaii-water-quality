"""Geo-location platform for Hawaii Water Quality."""
from __future__ import annotations

from typing import Any
import logging

from homeassistant.components.geo_location import GeolocationEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_ISLAND
from .coordinator import HawaiiWaterQualityDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Hawaii Water Quality geo-location platform."""
    coordinator: HawaiiWaterQualityDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    island_id = entry.data.get(CONF_ISLAND, "All")

    @callback
    def update_entities():
        """Update geo-location entities based on coordinator data."""
        if island_id == "All":
            advisories = coordinator.data.get("all_advisories", [])
        else:
            island_data = coordinator.data.get("islands", {}).get(island_id, {})
            advisories = island_data.get("advisories", [])

        _LOGGER.debug("Updating geo_location entities: %s found", len(advisories))
        
        new_entities = []
        for advisory in advisories:
            # For now, we'll just create them on every refresh to be simple
            # Home Assistant handles duplicate unique_ids by ignoring them
            new_entities.append(HawaiiWaterQualityGeolocationEvent(coordinator, advisory))

        if new_entities:
            async_add_entities(new_entities)

    # Register listener
    entry.async_on_unload(coordinator.async_add_listener(update_entities))
    
    # Initial trigger
    update_entities()


class HawaiiWaterQualityGeolocationEvent(CoordinatorEntity, GeolocationEvent):
    """Represent a water quality advisory as a geo-location event."""

    _attr_should_poll = False
    _attr_icon = "mdi:waves"

    def __init__(
        self, 
        coordinator: HawaiiWaterQualityDataUpdateCoordinator, 
        advisory: dict[str, Any]
    ) -> None:
        """Initialize the event."""
        super().__init__(coordinator)
        self._advisory = advisory
        self._attr_name = advisory["name"]
        self._attr_unique_id = f"{DOMAIN}_{advisory['id']}"
        self._attr_latitude = advisory["latitude"]
        self._attr_longitude = advisory["longitude"]
        self._attr_unit_of_measurement = "km"
        self._attr_source = DOMAIN

    @property
    def source(self) -> str:
        """Return the source of the event."""
        return DOMAIN

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {
            "event_id": self._advisory["event_id"],
            "type": self._advisory["type"],
            "status": self._advisory["status"],
            "island": self._advisory["island"],
            "posted_date": self._advisory["posted_date"],
            "geometry": self._advisory["geometry"],
            "rgb_color": [139, 69, 19], # SaddleBrown
        }
