"""Command-line entrypoint for reproducible research artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd

from dallas3d.heights import enrich_buildings, summarize_heights
from dallas3d.mesh import build_city_mesh
from dallas3d.pathfinding import PathConfig, plan_path
from dallas3d.reporting import (
    plot_experiments,
    plot_height_quality,
    write_json,
    write_source_summary,
)
from dallas3d.visibility import VisibilityConfig, greedy_coverage


def build_data(input_path: Path, output_dir: Path) -> gpd.GeoDataFrame:
    raw = gpd.read_file(input_path)
    buildings = enrich_buildings(raw)
    output_dir.mkdir(parents=True, exist_ok=True)
    buildings.to_file(output_dir / "dallas_buildings_lod1.gpkg", layer="buildings", driver="GPKG")
    buildings.to_file(output_dir / "dallas_buildings_lod1.geojson", driver="GeoJSON")
    write_json(summarize_heights(buildings), output_dir / "height_quality.json")
    write_source_summary(buildings, output_dir / "height_provenance.csv")
    plot_height_quality(buildings, output_dir / "height_quality.png")
    return buildings


def run_experiments(buildings: gpd.GeoDataFrame, output_dir: Path) -> None:
    visibility = greedy_coverage(buildings, VisibilityConfig())
    path = plan_path(buildings, PathConfig())
    write_json(visibility, output_dir / "visibility_experiment.json")
    write_json(path, output_dir / "path_experiment.json")
    plot_experiments(buildings, visibility, path, output_dir / "geometry_experiments.png")


def build_all(input_path: Path, output_dir: Path, mesh_dir: Path) -> None:
    buildings = build_data(input_path, output_dir)
    run_experiments(buildings, output_dir)
    build_city_mesh(
        buildings,
        mesh_dir / "dallas_buildings_lod1.glb",
        output_dir / "model_origin.json",
    )


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    command.add_argument(
        "--input",
        type=Path,
        default=Path("data/raw/dallas_cbd_osm_buildings.gpkg"),
        help="Raw OSM building GeoPackage",
    )
    command.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/processed"),
    )
    command.add_argument(
        "--mesh-dir",
        type=Path,
        default=Path("data/meshes"),
    )
    command.add_argument(
        "action",
        choices=["build-data", "run-experiments", "build-mesh", "build-all"],
        nargs="?",
        default="build-all",
    )
    return command


def main() -> None:
    args = parser().parse_args()
    if args.action in {"build-data", "build-all"}:
        if args.action == "build-all":
            build_all(args.input, args.output_dir, args.mesh_dir)
        else:
            build_data(args.input, args.output_dir)
        return

    buildings = gpd.read_file(args.output_dir / "dallas_buildings_lod1.gpkg")
    if args.action == "run-experiments":
        run_experiments(buildings, args.output_dir)
    elif args.action == "build-mesh":
        build_city_mesh(
            buildings,
            args.mesh_dir / "dallas_buildings_lod1.glb",
            args.output_dir / "model_origin.json",
        )


if __name__ == "__main__":
    main()
