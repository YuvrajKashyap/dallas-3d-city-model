import geopandas as gpd
from shapely.geometry import Point, box

from dallas3d.visibility import line_of_sight


def _buildings(height: float):
    return gpd.GeoDataFrame(
        {"height_m": [height], "geometry": [box(4, -1, 6, 1)]},
        crs="EPSG:32614",
    )


def test_tall_building_blocks_descending_ray():
    assert not line_of_sight(Point(0, 0), Point(10, 0), 100, 0, _buildings(70))


def test_short_building_clears_descending_ray():
    assert line_of_sight(Point(0, 0), Point(10, 0), 100, 0, _buildings(20))
