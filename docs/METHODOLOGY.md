# Methodology

## Study area and coordinates

The fetch script centers a 4,000 m square on the Dallas CBD reference coordinate `(32.7767, -96.7970)`. Source coordinates are WGS 84 and metric processing uses [WGS 84 / UTM zone 14N](https://epsg.io/32614), whose horizontal unit is the metre and whose area of use includes Dallas.

The clipped footprint extent in the current snapshot is 3,620.03 m by 3,573.43 m because buildings do not touch every study-square edge.

## Geometry preparation

1. Drop null geometry.
2. Repair geometry with Shapely `make_valid`.
3. Keep polygons and multipolygons.
4. Project to EPSG:32614.
5. Compute footprint area in square metres.
6. Retain only the minimal public modeling schema.

## Height enrichment

The priority order follows common [OpenStreetMap simple 3D building](https://wiki.openstreetmap.org/wiki/Simple_3D_buildings) semantics:

1. `building:height`, then `height`, parsed as metres or explicit feet/inches. Ambiguous ranges and lists are rejected.
2. Valid whole `building:levels` multiplied by 3.0 m. If present, `roof:height` is added; otherwise whole `roof:levels` use 1.5 m per roof level.
3. A deterministic typology-and-area estimate for remaining footprints.

The final fallback is intentionally conservative and inspectable:

```text
base height = 0.65 × trusted group median + 0.35 × typology prior
area factor = clip((footprint area / trusted global median area)^0.18, 0.72, 1.65)
height = clip(base height × area factor, 3 m, typology cap)
```

“Trusted” means an explicit height or levels-derived height. A group median is used only when at least four trusted examples exist; otherwise the global trusted median is used. Typology caps prevent a large footprint alone from manufacturing a skyscraper.

### Provenance result

| Source | Confidence | Buildings | Share | Median height |
| --- | --- | ---: | ---: | ---: |
| Explicit OSM height | High | 158 | 10.17% | 24.19 m |
| OSM levels | Medium | 205 | 13.20% | 9.00 m |
| Typology + footprint area | Low | 1,190 | 76.63% | 11.79 m |

The overall median is 11.99 m and the maximum is 280.72 m. The maximum remains because it comes from an explicit OSM height, not a generated “tall tail.”

## Visibility coverage experiment

Configuration:

- 7 × 7 candidate grid before building-footprint exclusion
- 17 × 17 target grid before building-footprint exclusion
- 40 free candidate samples
- 240 free target samples
- Observer altitude: 120 m in model coordinates
- Target altitude: 2 m
- Maximum selected observers: 6

For a candidate-target pair, a 2D line segment identifies intersected footprints. At the nearest intersection with each footprint, linear interpolation gives the 3D ray altitude. The line of sight is blocked when the building's `height_m` reaches or exceeds that altitude.

Greedy selection repeatedly chooses the candidate with the largest number of newly visible targets. Six candidates cover 224 of 240 targets, or 93.33%. This is a sampled, greedy result—not continuous coverage or a proof of optimality.

## Fixed-altitude path experiment

Configuration:

- Grid cell: 50 m
- Model flight altitude: 80 m
- Vertical clearance: 15 m
- Blocking threshold: building height ≥ 65 m
- Movement: eight neighbors with Euclidean step cost
- Heuristic: Euclidean distance

In the current run, 48 buildings create 205 blocked cells. A* returns a 4,987.62 m path versus 4,914.52 m between its endpoint cell centers, for a 1.015 detour ratio.

The model does not include dynamic constraints, takeoff/landing, terrain, restricted airspace, regulations, communications, uncertainty, or collision guarantees. Its altitude values are analytical parameters, not flight recommendations.

## Reproducibility

The enrichment and experiment code has no random branch. Re-running against the same raw GeoPackage and package versions produces the same feature-level heights, sampled positions, selected observers, and path.
