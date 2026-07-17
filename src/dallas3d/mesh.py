"""Convert processed building footprints into a centered 3D mesh."""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import trimesh
from shapely import affinity
from shapely.geometry import MultiPolygon, Polygon


def iter_polygons(geometry: object):
    if isinstance(geometry, Polygon):
        yield geometry
    elif isinstance(geometry, MultiPolygon):
        yield from geometry.geoms


def build_city_mesh(
    buildings: gpd.GeoDataFrame,
    output_path: Path,
    origin_path: Path,
) -> dict[str, float | int]:
    """Extrude each footprint and export a centered GLB mesh."""
    if "height_m" not in buildings:
        raise ValueError("Processed buildings must include height_m")
    center = buildings.geometry.union_all().centroid
    meshes: list[trimesh.Trimesh] = []
    skipped = 0

    for row in buildings.itertuples(index=False):
        height = float(row.height_m)
        for polygon in iter_polygons(row.geometry):
            shifted = affinity.translate(polygon, xoff=-center.x, yoff=-center.y)
            try:
                meshes.append(trimesh.creation.extrude_polygon(shifted, height=height))
            except (ValueError, TypeError):
                skipped += 1

    if not meshes:
        raise RuntimeError("No valid building meshes were created")
    city = trimesh.util.concatenate(meshes)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    city.export(output_path)

    origin = {
        "crs": str(buildings.crs),
        "origin_easting_m": round(float(center.x), 3),
        "origin_northing_m": round(float(center.y), 3),
        "mesh_count": len(meshes),
        "skipped_polygon_count": skipped,
        "vertex_count": int(len(city.vertices)),
        "face_count": int(len(city.faces)),
    }
    origin_path.parent.mkdir(parents=True, exist_ok=True)
    origin_path.write_text(json.dumps(origin, indent=2) + "\n", encoding="utf-8")
    return origin
