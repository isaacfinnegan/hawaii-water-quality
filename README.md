# Hawaii Ocean Water Quality

A Home Assistant custom component that tracks water quality advisories from the Hawaii Department of Health (DOH), provides high-resolution OpenStreetMap (OSM) maps, and lists active advisory areas per island.

## Features
- **Active Areas Tracking**: Replaces simple advisory counts with a per-island "Active Areas" sensor, showing distinct areas under advisory.
- **Detailed Attributes**: Provides a list of specific beach/area names (`active_areas`) for each island.
- **High-Resolution Mapping**: Utilizes high-resolution OpenStreetMap backgrounds with precise bounding boxes and a projection system for accurate alignment of DOH API coordinates.
- **Robust Integration**: Built with `config_flow`, `DataUpdateCoordinator`, and `async_setup_entry` for a modern, reliable integration pattern.

## Installation

### Via HACS (Recommended)
1. Ensure [HACS](https://hacs.xyz/) is installed.
2. Go to HACS -> Integrations -> 3 dots (top right) -> **Custom repositories**.
3. Paste this repository URL: `https://github.com/YOUR_USERNAME/hawaii-water-quality`
4. Select **Integration** as the category and click **Add**.
5. Find "Hawaii Ocean Water Quality" in HACS and click **Download**.
6. Restart Home Assistant.

### Manual Installation
1. Copy the `custom_components/hawaii_water_quality` folder to your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.

## Custom Card Installation
The integration includes a high-performance map card. 
1. Copy `hawaii-water-quality-card.js` from the root of this repo to your `www` folder.
2. Add it as a resource in Settings -> Dashboards -> Resources:
   - URL: `/local/hawaii-water-quality-card.js`
   - Type: `JavaScript Module`


### Prerequisites
- Docker and Docker Compose installed.

### Starting the Environment
Run the following command in the root of the repository to start the development container in the background:

```bash
docker-compose up -d
```

### Testing the Integration
Once the container is running, access the Home Assistant testing instance:

- **URL**: `http://localhost:8123`
- **Username**: `test`
- **Password**: `test`

You can manually test the high-res maps, list sensors, and verify the integration's behavior.

### Coordinate Offset Adjustment
If the advisory highlights appear offset from the map tiles:
1. Open the **Hawaii Ocean Water Quality Map** card on your dashboard.
2. Click on the **correct physical location** of a beach where you expect a highlight to be.
3. A popup will appear showing the required **Lon/Lat deltas**.
4. Go to **Settings -> Devices & Services -> Hawaii Ocean Water Quality -> Configure**.
5. Add the reported deltas to the existing offset values and click **Submit**.
6. The highlights will instantly realign.

## Next Steps
- **User Verification**: Allow manual testing of the new high-res maps and list sensors.
- **Refine Bounding Boxes**: Further tune island bounds if the map centering needs adjustment.
