"""Deterministic 2.5D line-of-sight coverage experiment."""

from __future__ import annotations

from dataclasses import dataclass

import geopandas as gpd
import numpy as np
from shapely.geometry import LineString, Point
from shapely.ops import nearest_points


@dataclass(frozen=True)
class VisibilityConfig:
    candidate_grid: int = 7
    target_grid: int = 17
    observer_altitude_m: float = 120.0
    target_altitude_m: float = 2.0
    max_observers: int = 6
    edge_inset_m: float = 80.0


def _free_grid(buildings: gpd.GeoDataFrame, count: int, inset_m: float) -> list[Point]:
    min_x, min_y, max_x, max_y = buildings.total_bounds
    xs = np.linspace(min_x + inset_m, max_x - inset_m, count)
    ys = np.linspace(min_y + inset_m, max_y - inset_m, count)
    union = buildings.geometry.union_all()
    return [Point(float(x), float(y)) for y in ys for x in xs if not union.covers(Point(x, y))]


def line_of_sight(
    observer: Point,
    target: Point,
    observer_altitude_m: float,
    target_altitude_m: float,
    buildings: gpd.GeoDataFrame,
) -> bool:
    """Return whether a descending 3D ray clears all flat-roof building prisms."""
    ray = LineString([observer, target])
    length = ray.length
    if length <= 1e-9:
        return True
    for index in buildings.sindex.query(ray, predicate="intersects"):
        row = buildings.iloc[int(index)]
        intersection = ray.intersection(row.geometry)
        if intersection.is_empty:
            continue
        nearest = nearest_points(observer, intersection)[1]
        distance = ray.project(nearest)
        if distance <= 0.5 or distance >= length - 0.5:
            continue
        fraction = distance / length
        ray_height = observer_altitude_m + fraction * (
            target_altitude_m - observer_altitude_m
        )
        if float(row.height_m) >= ray_height:
            return False
    return True


def greedy_coverage(
    buildings: gpd.GeoDataFrame,
    config: VisibilityConfig | None = None,
) -> dict[str, object]:
    """Select aerial observer samples with a transparent greedy set-cover heuristic."""
    config = config or VisibilityConfig()
    candidates = _free_grid(buildings, config.candidate_grid, config.edge_inset_m)
    targets = _free_grid(buildings, config.target_grid, config.edge_inset_m)
    if not candidates or not targets:
        raise RuntimeError("Study area did not produce free candidate and target samples")

    visibility: list[set[int]] = []
    for candidate in candidates:
        visible = {
            index
            for index, target in enumerate(targets)
            if line_of_sight(
                candidate,
                target,
                config.observer_altitude_m,
                config.target_altitude_m,
                buildings,
            )
        }
        visibility.append(visible)

    selected: list[int] = []
    covered: set[int] = set()
    remaining = set(range(len(candidates)))
    progress: list[dict[str, float | int]] = []
    for _ in range(config.max_observers):
        if not remaining:
            break
        choice = max(remaining, key=lambda index: (len(visibility[index] - covered), -index))
        gain = len(visibility[choice] - covered)
        if gain == 0:
            break
        selected.append(choice)
        covered |= visibility[choice]
        remaining.remove(choice)
        progress.append(
            {
                "observer_count": len(selected),
                "new_targets": gain,
                "covered_targets": len(covered),
                "coverage_pct": round(100 * len(covered) / len(targets), 2),
            }
        )

    return {
        "method": "greedy_set_cover",
        "candidate_count": len(candidates),
        "target_count": len(targets),
        "observer_altitude_m": config.observer_altitude_m,
        "target_altitude_m": config.target_altitude_m,
        "selected_candidate_indices": selected,
        "selected_observers": [[candidates[i].x, candidates[i].y] for i in selected],
        "covered_target_indices": sorted(covered),
        "coverage_pct": round(100 * len(covered) / len(targets), 2),
        "progress": progress,
        "candidates": [[point.x, point.y] for point in candidates],
        "targets": [[point.x, point.y] for point in targets],
    }
