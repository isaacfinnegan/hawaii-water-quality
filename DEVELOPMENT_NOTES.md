# Development Notes: Hawaii Ocean Water Quality

## Project Status
The integration has been refined with improved data presentation and high-resolution mapping.

### Achievements
- **Refined Data Presentation**: Replaced the simple advisory count with a per-island "Active Areas" sensor.
  - **State**: Count of distinct areas under advisory.
  - **Attribute (`active_areas`)**: A list of specific beach/area names, ideal for Markdown cards.
- **High-Resolution Mapping**:
  - Replaced crude SVG drawings with a high-resolution OpenStreetMap background.
  - Implemented precise bounding boxes and a projection system for accurate alignment of DOH API coordinates.
  - Highlights are now **Brown** (`#8B4513`) as requested, improving visibility against the map.
- **Modern Integration Pattern**: Robust `config_flow`, `DataUpdateCoordinator`, and `async_setup_entry` implementation.
- **Networking Fix**: Resolved macOS/Docker "Network unreachable" issues by forcing IPv4 in the `aiohttp` coordinator.

### Testing Environment
- **URL**: `http://localhost:8123`
- **Username**: `test`
- **Password**: `test`
- **Integration**: Hawaii Ocean Water Quality

### Next Steps
1. **User Verification**: Allow manual testing of the new high-res maps and list sensors.
2. **Refine Bounding Boxes**: Further tune island bounds if the map centering needs adjustment.
