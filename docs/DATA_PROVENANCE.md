# Data provenance

## Source

Building footprints and building tags come from [OpenStreetMap](https://www.openstreetmap.org/). The reproducible fetch entrypoint uses OSMnx `features_from_polygon` with `{"building": true}` over the Dallas CBD study square.

The upstream snapshot is stored locally under `data/raw/` and is ignored by Git. This avoids publishing the entire upstream attribute surface and keeps repository history focused on the processed research contract.

## Published derivative

`data/processed/dallas_buildings_lod1.gpkg` and `.geojson` are OSM-derived databases. They retain only:

- OSM feature identifier;
- building type and coarse modeling group;
- parsed levels when available;
- footprint area;
- final height, provenance, and confidence;
- polygon geometry in EPSG:32614.

Names, addresses, phone numbers, emails, websites, and unrelated OSM tags are intentionally excluded from the published schema.

## Attribution and license

© OpenStreetMap contributors. OpenStreetMap data is available under the Open Data Commons Open Database License (ODbL). See [OpenStreetMap copyright and licensing](https://www.openstreetmap.org/copyright) and this repository's [data license notice](../DATA_LICENSE.md).

## Regeneration caveat

OpenStreetMap changes continuously. Fetching a new snapshot may change feature counts, tags, geometry, enrichment statistics, experiment results, and rendered appearance. Exact reproduction requires the same local source snapshot; current-state regeneration requires a network fetch and should be treated as a new data release.
