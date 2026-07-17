import math

import geopandas as gpd
from shapely.geometry import box

from dallas3d.heights import enrich_buildings, parse_height_m, parse_levels


def test_parse_height_supports_metric_and_imperial_values():
    assert parse_height_m("12.5") == 12.5
    assert parse_height_m("12.5 m") == 12.5
    assert math.isclose(parse_height_m("100 ft"), 30.48)
    assert math.isclose(parse_height_m("10' 6\""), 3.2004)


def test_parse_height_rejects_ranges_and_non_positive_values():
    assert math.isnan(parse_height_m("10-12"))
    assert math.isnan(parse_height_m("12;14"))
    assert math.isnan(parse_height_m(0))


def test_parse_levels_requires_positive_whole_storeys():
    assert parse_levels("4") == 4
    assert math.isnan(parse_levels("4.5"))
    assert math.isnan(parse_levels("2;3"))
    assert math.isnan(parse_levels(0))


def test_enrichment_is_deterministic_and_tracks_provenance():
    raw = gpd.GeoDataFrame(
        {
            "id": [1, 2, 3, 4, 5, 6],
            "building": ["office", "apartments", "office", "office", "office", "warehouse"],
            "height": ["30 m", None, None, "20", "40", None],
            "building:levels": [None, "5", None, None, None, None],
            "geometry": [
                box(-96.80, 32.77, -96.799, 32.771),
                box(-96.79, 32.77, -96.789, 32.771),
                box(-96.78, 32.77, -96.779, 32.772),
                box(-96.77, 32.77, -96.769, 32.771),
                box(-96.76, 32.77, -96.759, 32.771),
                box(-96.75, 32.77, -96.748, 32.772),
            ],
        },
        crs="EPSG:4326",
    )

    first = enrich_buildings(raw)
    second = enrich_buildings(raw)

    assert first.crs.to_epsg() == 32614
    assert first["height_m"].tolist() == second["height_m"].tolist()
    assert first["height_source"].tolist() == [
        "osm_height",
        "osm_levels",
        "typology_area",
        "osm_height",
        "osm_height",
        "typology_area",
    ]
    assert first.loc[1, "height_m"] == 15.0
    assert first.loc[2, "height_confidence"] == "low"
    assert set(first.columns) == {
        "osm_id",
        "building_type",
        "building_group",
        "levels",
        "footprint_m2",
        "height_m",
        "height_source",
        "height_confidence",
        "geometry",
    }
