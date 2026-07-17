"""Traceable building-height enrichment for an LOD1-style city model."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

import geopandas as gpd
import numpy as np
import pandas as pd

DALLAS_UTM = "EPSG:32614"
METERS_PER_LEVEL = 3.0
METERS_PER_ROOF_LEVEL = 1.5

_NUMBER = re.compile(r"[-+]?\d+(?:\.\d+)?")
_FEET_INCHES = re.compile(
    r"^\s*(?P<feet>\d+(?:\.\d+)?)\s*(?:ft|feet|foot|')"
    r"(?:\s*(?P<inches>\d+(?:\.\d+)?)\s*(?:in|inch|inches|\"))?\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class HeightResult:
    height_m: float
    source: str
    confidence: str


def _missing(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return str(value).strip().lower() in {"", "nan", "none", "null", "unknown"}


def parse_height_m(value: object) -> float:
    """Parse a positive OSM height value into metres; return NaN if ambiguous."""
    if _missing(value):
        return np.nan
    if isinstance(value, (int, float, np.number)):
        number = float(value)
        return number if 0 < number <= 500 else np.nan

    text = str(value).strip().lower().replace(",", ".")
    if ";" in text or "-" in text[1:]:
        return np.nan
    match = _FEET_INCHES.match(text)
    if match:
        feet = float(match.group("feet"))
        inches = float(match.group("inches") or 0.0)
        metres = feet * 0.3048 + inches * 0.0254
        return metres if 0 < metres <= 500 else np.nan

    number_match = _NUMBER.fullmatch(text.removesuffix("m").strip())
    if not number_match:
        return np.nan
    number = float(number_match.group())
    return number if 0 < number <= 500 else np.nan


def parse_levels(value: object) -> float:
    """Parse positive, whole above-ground storeys from an OSM levels tag."""
    if _missing(value):
        return np.nan
    text = str(value).strip()
    if not re.fullmatch(r"\d+", text):
        return np.nan
    levels = int(text)
    return float(levels) if 0 < levels <= 120 else np.nan


def normalize_building_type(value: object) -> str:
    """Collapse the long OSM building vocabulary into useful inference groups."""
    kind = "yes" if _missing(value) else str(value).strip().lower()
    groups = {
        "residential": {
            "apartments",
            "detached",
            "house",
            "residential",
            "semidetached_house",
            "terrace",
        },
        "commercial": {"commercial", "hotel", "office", "retail", "supermarket"},
        "institutional": {
            "civic",
            "church",
            "college",
            "government",
            "hospital",
            "public",
            "school",
            "university",
        },
        "industrial": {"industrial", "service", "warehouse"},
        "parking": {"carport", "garage", "garages", "parking"},
        "roof": {"roof"},
    }
    for group, values in groups.items():
        if kind in values:
            return group
    return "other"


def _series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column in frame.columns:
        return frame[column]
    return pd.Series(np.nan, index=frame.index, dtype=float)


def _robust_group_statistics(frame: gpd.GeoDataFrame) -> tuple[dict[str, float], float, float]:
    trusted = frame.loc[frame["height_source"].isin(["osm_height", "osm_levels"])].copy()
    global_height = float(trusted["height_m"].median()) if len(trusted) else 12.0
    global_area = float(trusted["footprint_m2"].median()) if len(trusted) else 400.0
    medians: dict[str, float] = {}
    for group, rows in trusted.groupby("building_group"):
        if len(rows) >= 4:
            medians[str(group)] = float(rows["height_m"].median())
    return medians, global_height, global_area


def _infer_height(
    group: str,
    footprint_m2: float,
    medians: dict[str, float],
    global_height: float,
    global_area: float,
) -> float:
    priors = {
        "residential": 9.0,
        "commercial": 15.0,
        "institutional": 12.0,
        "industrial": 9.0,
        "parking": 9.0,
        "roof": 4.0,
        "other": 10.0,
    }
    caps = {
        "residential": 30.0,
        "commercial": 75.0,
        "institutional": 36.0,
        "industrial": 24.0,
        "parking": 30.0,
        "roof": 8.0,
        "other": 42.0,
    }
    empirical = medians.get(group, global_height)
    base = 0.65 * empirical + 0.35 * priors[group]
    safe_area = footprint_m2 if np.isfinite(footprint_m2) and footprint_m2 > 0 else global_area
    area_factor = float(np.clip((safe_area / global_area) ** 0.18, 0.72, 1.65))
    return float(np.clip(base * area_factor, 3.0, caps[group]))


def enrich_buildings(raw: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Return a minimal, projected dataset with explicit height provenance."""
    if raw.crs is None:
        raise ValueError("Input buildings must declare a CRS")
    if "geometry" not in raw:
        raise ValueError("Input buildings must contain geometry")

    frame = raw.loc[raw.geometry.notna()].copy()
    frame.geometry = frame.geometry.make_valid()
    frame = frame.loc[~frame.geometry.is_empty & frame.geom_type.isin(["Polygon", "MultiPolygon"])]
    frame = frame.to_crs(DALLAS_UTM).reset_index(drop=True)
    frame["footprint_m2"] = frame.geometry.area.round(2)
    frame["building_type"] = _series(frame, "building").fillna("yes").astype(str)
    frame["building_group"] = frame["building_type"].map(normalize_building_type)

    explicit = _series(frame, "building:height").map(parse_height_m)
    explicit = explicit.fillna(_series(frame, "height").map(parse_height_m))
    levels = _series(frame, "building:levels").map(parse_levels)
    roof_height = _series(frame, "roof:height").map(parse_height_m)
    roof_levels = _series(frame, "roof:levels").map(parse_levels)
    roof_component = roof_height.fillna(roof_levels * METERS_PER_ROOF_LEVEL).fillna(0.0)

    frame["height_m"] = explicit
    frame["height_source"] = np.where(explicit.notna(), "osm_height", "unassigned")
    frame["height_confidence"] = np.where(explicit.notna(), "high", "unassigned")

    use_levels = frame["height_m"].isna() & levels.notna()
    frame.loc[use_levels, "height_m"] = (
        levels[use_levels] * METERS_PER_LEVEL + roof_component[use_levels]
    )
    frame.loc[use_levels, "height_source"] = "osm_levels"
    frame.loc[use_levels, "height_confidence"] = "medium"

    medians, global_height, global_area = _robust_group_statistics(frame)
    missing = frame["height_m"].isna()
    frame.loc[missing, "height_m"] = [
        _infer_height(group, area, medians, global_height, global_area)
        for group, area in zip(
            frame.loc[missing, "building_group"],
            frame.loc[missing, "footprint_m2"],
            strict=True,
        )
    ]
    frame.loc[missing, "height_source"] = "typology_area"
    frame.loc[missing, "height_confidence"] = "low"
    frame["height_m"] = frame["height_m"].clip(lower=2.5, upper=350.0).round(2)

    osm_id = _series(frame, "id")
    if osm_id.isna().all():
        osm_id = pd.Series(range(1, len(frame) + 1), index=frame.index)
    frame["osm_id"] = osm_id.astype(str)
    frame["levels"] = levels

    columns = [
        "osm_id",
        "building_type",
        "building_group",
        "levels",
        "footprint_m2",
        "height_m",
        "height_source",
        "height_confidence",
        "geometry",
    ]
    return gpd.GeoDataFrame(frame[columns], geometry="geometry", crs=DALLAS_UTM)


def summarize_heights(buildings: gpd.GeoDataFrame) -> dict[str, object]:
    """Produce JSON-serializable quality metrics for a processed dataset."""
    source_counts = buildings["height_source"].value_counts().to_dict()
    confidence_counts = buildings["height_confidence"].value_counts().to_dict()
    heights = buildings["height_m"]
    return {
        "building_count": int(len(buildings)),
        "crs": str(buildings.crs),
        "study_width_m": round(float(buildings.total_bounds[2] - buildings.total_bounds[0]), 2),
        "study_height_m": round(float(buildings.total_bounds[3] - buildings.total_bounds[1]), 2),
        "height_source_counts": {str(k): int(v) for k, v in source_counts.items()},
        "height_confidence_counts": {str(k): int(v) for k, v in confidence_counts.items()},
        "height_min_m": round(float(heights.min()), 2),
        "height_median_m": round(float(heights.median()), 2),
        "height_p90_m": round(float(heights.quantile(0.9)), 2),
        "height_max_m": round(float(heights.max()), 2),
        "observed_or_levels_pct": round(
            float(buildings["height_source"].isin(["osm_height", "osm_levels"]).mean() * 100), 2
        ),
    }
