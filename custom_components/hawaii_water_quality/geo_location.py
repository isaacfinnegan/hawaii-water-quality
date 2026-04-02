"""Geo-location platform for Hawaii Water Quality."""
from __future__ import annotations

from typing import Any
import logging

from homeassistant.components.geo_location import GeolocationEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_ISLAND, NAME
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

    # Track entities by their unique ID
    current_entities: dict[str, HawaiiWaterQualityGeolocationEvent] = {}

    @callback
    def update_entities():
        """Update geo-location entities based on coordinator data."""
        if not coordinator.data:
            _LOGGER.debug("No coordinator data available for geo_location update")
            return

        if island_id == "All":
            advisories = coordinator.data.get("all_advisories", [])
        else:
            island_data = coordinator.data.get("islands", {}).get(island_id, {})
            advisories = island_data.get("advisories", [])

        _LOGGER.debug("Updating geo_location entities: %s found", len(advisories))
        
        new_advisories = []
        active_ids = set()

        for advisory in advisories:
            entity_id = f"{DOMAIN}_{advisory['id']}"
            active_ids.add(entity_id)

            if entity_id not in current_entities:
                # New advisory, create entity
                _LOGGER.debug("Adding new geo_location entity: %s", entity_id)
                entity = HawaiiWaterQualityGeolocationEvent(coordinator, advisory)
                current_entities[entity_id] = entity
                new_advisories.append(entity)
            else:
                # Existing advisory, update if needed
                _LOGGER.debug("Updating existing geo_location entity: %s", entity_id)
                current_entities[entity_id].update_advisory(advisory)

        # Remove entities that are no longer active
        to_remove = [eid for eid in current_entities if eid not in active_ids]
        for eid in to_remove:
            _LOGGER.debug("Removing geo_location entity: %s", eid)
            hass.async_create_task(current_entities[eid].async_remove())
            del current_entities[eid]

        # Also clean up the entity registry for this domain and entry
        from homeassistant.helpers import entity_registry as er
        registry = er.async_get(hass)
        
        # Find all entities for this config entry
        for entity_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
            if entity_entry.domain == "geo_location":
                if entity_entry.unique_id not in active_ids:
                    # Check if it was one of ours (prefixed with DOMAIN_)
                    if entity_entry.unique_id.startswith(f"{DOMAIN}_"):
                        _LOGGER.debug("Removing orphaned entity from registry: %s", entity_entry.entity_id)
                        registry.async_remove(entity_entry.entity_id)

        if new_advisories:
            async_add_entities(new_advisories)

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
        self._attr_latitude = float(advisory["latitude"])
        self._attr_longitude = float(advisory["longitude"])
        self._attr_unit_of_measurement = "km"
        self._attr_source = DOMAIN

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry.entry_id)},
            name="Hawaii Ocean Water Quality",
            manufacturer="Hawaii DOH",
            model="Water Quality Integration",
        )

    @callback
    def update_advisory(self, advisory: dict[str, Any]) -> None:
        """Update the advisory data."""
        self._advisory = advisory
        self._attr_latitude = float(advisory["latitude"])
        self._attr_longitude = float(advisory["longitude"])
        # No need to call async_write_ha_state here if we trust the coordinator listener to trigger it
        # or if we are already in an update loop.

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {
            "event_id": str(self._advisory["event_id"]),
            "type": self._advisory["type"],
            "status": self._advisory["status"],
            "island": self._advisory["island"],
            "posted_date": self._advisory["posted_date"],
            "geometry": self._advisory["geometry"],
            "rgb_color": [139, 69, 19], # Brown (8B 45 13)
        }
