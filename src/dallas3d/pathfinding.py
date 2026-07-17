"""Fixed-altitude A* experiment over a rasterized 2.5D building field."""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass

import geopandas as gpd
import numpy as np
from shapely.geometry import box


@dataclass(frozen=True)
class PathConfig:
    cell_size_m: float = 50.0
    flight_altitude_m: float = 80.0
    vertical_clearance_m: float = 15.0
    edge_padding_cells: int = 1


def _neighbors(node: tuple[int, int], shape: tuple[int, int]):
    row, column = node
    for dr, dc in [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]:
        neighbor = (row + dr, column + dc)
        if 0 <= neighbor[0] < shape[0] and 0 <= neighbor[1] < shape[1]:
            yield neighbor, math.sqrt(2.0) if dr and dc else 1.0


def _nearest_free(blocked: np.ndarray, origin: tuple[int, int]) -> tuple[int, int]:
    if not blocked[origin]:
        return origin
    rows, columns = blocked.shape
    for radius in range(1, max(rows, columns)):
        candidates = []
        for row in range(max(0, origin[0] - radius), min(rows, origin[0] + radius + 1)):
            for column in range(max(0, origin[1] - radius), min(columns, origin[1] + radius + 1)):
                if not blocked[row, column]:
                    candidates.append((row, column))
        if candidates:
            return min(candidates, key=lambda item: math.dist(item, origin))
    raise RuntimeError("No free grid cell exists")


def astar(blocked: np.ndarray, start: tuple[int, int], goal: tuple[int, int]):
    frontier: list[tuple[float, tuple[int, int]]] = [(0.0, start)]
    came_from: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
    cost_so_far = {start: 0.0}
    while frontier:
        _, current = heapq.heappop(frontier)
        if current == goal:
            break
        for neighbor, step_cost in _neighbors(current, blocked.shape):
            if blocked[neighbor]:
                continue
            new_cost = cost_so_far[current] + step_cost
            if new_cost < cost_so_far.get(neighbor, math.inf):
                cost_so_far[neighbor] = new_cost
                priority = new_cost + math.dist(neighbor, goal)
                heapq.heappush(frontier, (priority, neighbor))
                came_from[neighbor] = current
    if goal not in came_from:
        raise RuntimeError("No path exists at the configured altitude and clearance")
    path = []
    current: tuple[int, int] | None = goal
    while current is not None:
        path.append(current)
        current = came_from[current]
    return list(reversed(path))


def plan_path(
    buildings: gpd.GeoDataFrame,
    config: PathConfig | None = None,
) -> dict[str, object]:
    """Rasterize tall obstacles, then plan a deterministic diagonal A* route."""
    config = config or PathConfig()
    min_x, min_y, max_x, max_y = buildings.total_bounds
    columns = int(math.ceil((max_x - min_x) / config.cell_size_m))
    rows = int(math.ceil((max_y - min_y) / config.cell_size_m))
    blocked = np.zeros((rows, columns), dtype=bool)
    threshold = config.flight_altitude_m - config.vertical_clearance_m
    obstacles = buildings.loc[buildings["height_m"] >= threshold]

    for obstacle in obstacles.itertuples(index=False):
        bx0, by0, bx1, by1 = obstacle.geometry.bounds
        col0 = max(0, int((bx0 - min_x) // config.cell_size_m))
        col1 = min(columns - 1, int((bx1 - min_x) // config.cell_size_m))
        row0 = max(0, int((by0 - min_y) // config.cell_size_m))
        row1 = min(rows - 1, int((by1 - min_y) // config.cell_size_m))
        for row in range(row0, row1 + 1):
            for column in range(col0, col1 + 1):
                cell = box(
                    min_x + column * config.cell_size_m,
                    min_y + row * config.cell_size_m,
                    min_x + (column + 1) * config.cell_size_m,
                    min_y + (row + 1) * config.cell_size_m,
                )
                if cell.intersects(obstacle.geometry):
                    blocked[row, column] = True

    pad = min(config.edge_padding_cells, rows // 3, columns // 3)
    start = _nearest_free(blocked, (pad, pad))
    goal = _nearest_free(blocked, (rows - 1 - pad, columns - 1 - pad))
    cells = astar(blocked, start, goal)
    coordinates = [
        [
            min_x + (column + 0.5) * config.cell_size_m,
            min_y + (row + 0.5) * config.cell_size_m,
            config.flight_altitude_m,
        ]
        for row, column in cells
    ]
    distance_m = sum(
        math.dist(a[:2], b[:2]) for a, b in zip(coordinates, coordinates[1:], strict=False)
    )
    straight_m = math.dist(coordinates[0][:2], coordinates[-1][:2])
    return {
        "method": "astar_8_neighbor",
        "cell_size_m": config.cell_size_m,
        "flight_altitude_m": config.flight_altitude_m,
        "vertical_clearance_m": config.vertical_clearance_m,
        "blocking_height_threshold_m": threshold,
        "obstacle_building_count": int(len(obstacles)),
        "grid_rows": rows,
        "grid_columns": columns,
        "blocked_cell_count": int(blocked.sum()),
        "path_node_count": len(coordinates),
        "path_distance_m": round(distance_m, 2),
        "straight_line_distance_m": round(straight_m, 2),
        "detour_ratio": round(distance_m / straight_m, 3),
        "coordinates": coordinates,
    }
