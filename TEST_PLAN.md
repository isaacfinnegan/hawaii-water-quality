# Integration Test Plan: Hawaii Ocean Water Quality

## Automated Unit Tests
- `test_coordinator`: Verify data fetching, temporal filtering (recent hours), and area name extraction logic.
- `test_sensor`: Verify sensor state (count) and attributes (list of areas).
- `test_camera`: Verify SVG generation, OSM background inclusion, and brown highlight rendering.

## Dashboard Validation (Manual/Browser)
1.  **Card Addition**:
    -   Login to Home Assistant (`test`/`test`).
    -   Go to Overview -> Edit Dashboard.
    -   Add a 'Camera' card for `camera.hawaii_ocean_water_quality_oahu_map`.
    -   **Pass Criteria**: The card renders a map background with visible brown highlights.
2.  **Entity Favorites**:
    -   Go to Overview -> Edit.
    -   Add `camera.hawaii_ocean_water_quality_oahu_map` to the favorites section.
    -   **Pass Criteria**: Clicking the favorite icon opens a dialog showing the full-resolution map with "Oahu Water Quality" text.
3.  **Sensor Accuracy**:
    -   Go to Developer Tools -> States.
    -   Filter for `sensor.hawaii_ocean_water_quality_oahu`.
    -   **Pass Criteria**: `state` is a number (e.g., 10), and `active_areas` attribute contains a list of names like "Puha Stream".

## Temporal Filtering Test
1.  **Configuration**:
    -   Set `recent_hours` to `1` in the integration configuration.
    -   **Pass Criteria**: The area list and map should only show very recent advisories (likely 0 if none today).
2.  **Fallback**:
    -   Set `recent_hours` to `200`.
    -   **Pass Criteria**: The list should include "Puha Stream" (posted ~6 days ago).
