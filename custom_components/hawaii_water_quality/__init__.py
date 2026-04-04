"""The Hawaii Water Quality integration."""
from __future__ import annotations

import logging
import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.components.http import StaticPathConfig

from .const import DOMAIN, CARD_VERSION
from .coordinator import HawaiiWaterQualityDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["sensor", "camera", "geo_location"]

_RESOURCE_LOCK: asyncio.Lock | None = None

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Hawaii Water Quality component."""
    hass.data.setdefault(DOMAIN, {})
    
    # Register static path and resource globally
    await _async_setup_shared_resources(hass)
    
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Hawaii Water Quality from a config entry."""
    _LOGGER.info("Initializing Hawaii Water Quality integration")
    
    # Ensure resources are registered (handles UI-only installs)
    await _async_setup_shared_resources(hass)
    
    coordinator = HawaiiWaterQualityDataUpdateCoordinator(hass, entry)
    
    _LOGGER.info("Starting initial Hawaii Water Quality data fetch")
    await coordinator.async_config_entry_first_refresh()
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True

async def _async_setup_shared_resources(hass: HomeAssistant) -> None:
    """Setup shared HTTP paths and Lovelace resources."""
    global _RESOURCE_LOCK
    if _RESOURCE_LOCK is None:
        _RESOURCE_LOCK = asyncio.Lock()

    async with _RESOURCE_LOCK:
        # Ensure we only register resources once per Home Assistant session
        if hass.data[DOMAIN].get("shared_resources_setup"):
            return

        # Register static path for the dashboard card
        card_path = hass.config.path("custom_components/hawaii_water_quality/dashboard/hawaii-water-quality-card.js")
        url_path = "/hawaii_water_quality/hawaii-water-quality-card.js"
        
        # Check if already registered in aiohttp to be extra safe
        already_registered = False
        if hasattr(hass.http, "app") and hasattr(hass.http.app, "router"):
            for route in hass.http.app.router.routes():
                if route.resource and hasattr(route.resource, "get_info"):
                    info = route.resource.get_info()
                    if info.get("path") == url_path or info.get("prefix") == url_path:
                        _LOGGER.debug("Static path %s already registered in HTTP server", url_path)
                        already_registered = True
                        break

        if not already_registered:
            _LOGGER.info("Registering static path for Hawaii Water Quality card")
            if hasattr(hass.http, "async_register_static_paths"):
                await hass.http.async_register_static_paths([
                    StaticPathConfig(url_path, card_path, True)
                ])
            else:
                # Fallback for older HA versions
                hass.http.register_static_path(url_path, card_path, True)

        hass.data[DOMAIN]["shared_resources_setup"] = True

        # Automatically register the card as a Lovelace resource after a short delay
        if "hawaii_resource_task" not in hass.data[DOMAIN]:
            hass.data[DOMAIN]["hawaii_resource_task"] = hass.async_create_task(
                async_delayed_resource_registration(hass)
            )

async def async_delayed_resource_registration(hass: HomeAssistant) -> None:
    """Register resource after a short delay."""
    await asyncio.sleep(5)
    await async_register_resource(hass)
    if "hawaii_resource_task" in hass.data.get(DOMAIN, {}):
        del hass.data[DOMAIN]["hawaii_resource_task"]

async def async_register_resource(hass: HomeAssistant) -> None:
    """Register the Lovelace resource."""
    url = f"/hawaii_water_quality/hawaii-water-quality-card.js?v={CARD_VERSION}"
    
    if "lovelace" not in hass.data:
        return
        
    lovelace = hass.data["lovelace"]
    resources = getattr(lovelace, "resources", None)
    if not resources and isinstance(lovelace, dict):
        resources = lovelace.get("resources")
        
    if not resources:
        return

    # Check if resource already exists
    current_resources = []
    if hasattr(resources, "async_items"):
        current_resources = resources.async_items()
    elif isinstance(resources, list):
        current_resources = resources
    
    for resource in current_resources:
        res_url = resource.get("url", "") if isinstance(resource, dict) else getattr(resource, "url", "")
        if "/hawaii-water-quality-card.js" in res_url:
            if res_url != url:
                _LOGGER.debug("Updating Hawaii Water Quality card resource from %s to %s", res_url, url)
                if hasattr(resources, "async_update_item"):
                    res_id = resource.get("id") if isinstance(resource, dict) else getattr(resource, "id")
                    await resources.async_update_item(res_id, {"url": url})
            return

    _LOGGER.info("Registering Hawaii Water Quality card resource: %s", url)
    if hasattr(resources, "async_create_item"):
        await resources.async_create_item({"res_type": "module", "url": url})

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
