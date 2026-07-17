# Architecture

## Design goal

The repository separates source acquisition, data modeling, geometry experiments, and presentation so each result can be inspected or regenerated independently.

## Components

### `scripts/fetch_osm_buildings.py`

Builds a 4 km square around the Dallas CBD reference point, queries `building=*` features through OSMnx, keeps polygonal footprints, clips them in the local metric CRS, and writes a raw GeoPackage under `data/raw/`.

The raw snapshot is intentionally ignored by Git. It contains the complete upstream attribute surface and is not necessary for understanding the published result.

### `src/dallas3d/heights.py`

Validates geometry, projects it to EPSG:32614, parses explicit height and levels tags, applies deterministic fallback inference, assigns provenance/confidence, and reduces the public schema to the fields needed by the model.

### `src/dallas3d/mesh.py`

Extrudes every valid polygon into a flat-roof prism with Trimesh. Coordinates are shifted around the study-area centroid before GLB export so Blender and other 3D tools do not need to operate on large projected coordinates. `model_origin.json` preserves the inverse mapping.

### `src/dallas3d/visibility.py`

Samples free-space observer and target positions. For each pair it intersects the 2D ray with candidate building footprints, evaluates the ray altitude at the nearest intersection, and marks the ray blocked when a flat-roof prism reaches that altitude. A deterministic greedy set-cover heuristic selects observer samples by marginal target gain.

### `src/dallas3d/pathfinding.py`

Converts the city to a fixed-resolution grid. A building blocks a cell when its height reaches the configured flight altitude minus vertical clearance. Eight-neighbor A* then minimizes planar grid distance between free cells near opposite study-area corners.

### `src/dallas3d/reporting.py`

Writes machine-readable JSON/CSV and creates consistent research plots. It contains no experiment logic.

### `scripts/render_scene.py`

Loads the regenerated mesh and experiment JSON into Blender, restores Z-up coordinates, applies a single visual system, adds the selected observers and path, saves the canonical scene, and renders the portfolio images.

## Dependency direction

```text
fetch script
    ↓
height/data model
    ├── mesh export ──→ Blender renderer
    ├── visibility ───→ report + Blender renderer
    └── pathfinding ──→ report + Blender renderer
```

The experiments depend on the processed data contract, not on Blender. That keeps the results testable in CI and the presentation layer replaceable.

## Public data contract

The canonical GeoPackage uses one `buildings` layer with:

| Field | Meaning |
| --- | --- |
| `osm_id` | Upstream OSM feature identifier represented as text |
| `building_type` | Original normalized `building=*` value |
| `building_group` | Coarse typology used by fallback inference |
| `levels` | Parsed whole above-ground storeys when valid |
| `footprint_m2` | Projected polygon area |
| `height_m` | Final extrusion height |
| `height_source` | `osm_height`, `osm_levels`, or `typology_area` |
| `height_confidence` | `high`, `medium`, or `low` |
| `geometry` | Polygon or multipolygon in EPSG:32614 |
