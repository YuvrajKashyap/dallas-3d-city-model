"""Fetch the Dallas CBD study square from OpenStreetMap with OSMnx.

Run after installing the optional fetch dependency:
    python -m pip install -e ".[fetch]"
    python scripts/fetch_osm_buildings.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd
import osmnx as ox
from shapely.geometry import box

DALLAS_CBD_LAT = 32.7767
DALLAS_CBD_LON = -96.7970
SOURCE_CRS = "EPSG:4326"
METRIC_CRS = "EPSG:32614"


def study_area(side_m: float):
    center = gpd.GeoSeries.from_xy([DALLAS_CBD_LON], [DALLAS_CBD_LAT], crs=SOURCE_CRS)
    projected = center.to_crs(METRIC_CRS).iloc[0]
    half = side_m / 2
    return gpd.GeoSeries(
        [box(projected.x - half, projected.y - half, projected.x + half, projected.y + half)],
        crs=METRIC_CRS,
    ).to_crs(SOURCE_CRS).iloc[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--side-m", type=float, default=4_000)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/raw/dallas_cbd_osm_buildings.gpkg"),
    )
    args = parser.parse_args()

    boundary = study_area(args.side_m)
    raw = ox.features.features_from_polygon(boundary, tags={"building": True})
    buildings = raw.loc[raw.geom_type.isin(["Polygon", "MultiPolygon"])].reset_index()
    buildings = buildings.to_crs(METRIC_CRS)
    buildings = gpd.clip(buildings, gpd.GeoSeries([boundary], crs=SOURCE_CRS).to_crs(METRIC_CRS))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    buildings.to_file(args.output, layer="buildings", driver="GPKG")
    print(f"Wrote {len(buildings):,} building footprints to {args.output}")


if __name__ == "__main__":
    main()
