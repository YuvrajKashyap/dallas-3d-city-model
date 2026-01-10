import geopandas as gpd
from shapely.geometry import box

IN_SHP = "dallas_buildings.shp"

CBD_LAT = 32.7767
CBD_LON = -96.7970

SIZES_M = [2000, 4000, 6000]  # square sizes in meters

print("Loading buildings...")
gdf = gpd.read_file(IN_SHP)
print("Input CRS:", gdf.crs)

if gdf.crs is None:
    raise ValueError("Input shapefile has no CRS. We must fix CRS before continuing.")

# Reproject buildings to meters
gdf_m = gdf.to_crs(3857)

# CBD center point -> EPSG:3857
cbd_pt = gpd.GeoSeries.from_xy([CBD_LON], [CBD_LAT], crs=4326).to_crs(3857).iloc[0]
cx, cy = cbd_pt.x, cbd_pt.y

for size in SIZES_M:
    half = size / 2
    clip_poly = box(cx - half, cy - half, cx + half, cy + half)

    sub = gdf_m[gdf_m.intersects(clip_poly)].copy()
    out = f"dallas_cbd_{size}m_box_buildings.shp"

    print(f"Size {size}m: buildings =", len(sub))
    sub.to_file(out)
    print("  saved:", out)

print("DONE")
