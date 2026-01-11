import geopandas as gpd
import osmnx as ox
from shapely.geometry import box

CBD_LAT = 32.7767
CBD_LON = -96.7970
SIZE_M = 4000  # 4km box

OUT_GPKG = "data/processed/dallas_cbd_4000m_osm_buildings_raw.gpkg"
OUT_SHP  = "data/processed/dallas_cbd_4000m_osm_buildings_raw.shp"

def main():
    # Build the same 4km square in EPSG:3857 (meters), then convert to WGS84 for OSM query.
    cbd_pt_3857 = gpd.GeoSeries.from_xy([CBD_LON], [CBD_LAT], crs=4326).to_crs(3857).iloc[0]
    cx, cy = cbd_pt_3857.x, cbd_pt_3857.y
    half = SIZE_M / 2
    clip_3857 = box(cx - half, cy - half, cx + half, cy + half)
    clip_wgs84 = gpd.GeoSeries([clip_3857], crs=3857).to_crs(4326).iloc[0]

    # Ask OSM for anything tagged building=*
    tags = {"building": True}

    # Configure OSMnx to keep useful tags. (It keeps all OSM tags it receives as columns.)
    ox.settings.use_cache = True
    ox.settings.log_console = True

    print("Querying OSM for buildings in 4km CBD box...")
    gdf = ox.features_from_polygon(clip_wgs84, tags)

    # OSMnx returns points/lines/polygons depending on data; keep only polygons for building footprints
    gdf = gdf[gdf.geometry.type.isin(["Polygon", "MultiPolygon"])].copy()

    # For consistent downstream geometry units
    gdf = gdf.set_crs(4326, allow_override=True).to_crs(3857)

    print("Buildings fetched:", len(gdf))
    print("Columns:", list(gdf.columns))

    # Save
    print("Writing:", OUT_GPKG)
    gdf.to_file(OUT_GPKG, layer="buildings", driver="GPKG")

    print("Writing:", OUT_SHP)
    gdf.to_file(OUT_SHP)

    print("DONE")

if __name__ == "__main__":
    main()
