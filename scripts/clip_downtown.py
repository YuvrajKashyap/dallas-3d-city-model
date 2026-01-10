import geopandas as gpd
from shapely.geometry import box

# INPUT
DALLAS_BUILDINGS = r"dallas_buildings.shp"

# OUTPUT
DOWNTOWN_OUT = r"downtown_dallas_buildings.shp"

print("Loading Dallas buildings...")
gdf = gpd.read_file(DALLAS_BUILDINGS)

print("Ensuring CRS is EPSG:3857...")
gdf = gdf.to_crs(3857)

# Downtown Dallas bounding box (meters, EPSG:3857)
# Approx area: CBD + surrounding core
xmin, ymin = -10718000, 3843000
xmax, ymax = -10714000, 3846500

print("Creating downtown bounding box...")
downtown_box = box(xmin, ymin, xmax, ymax)

print("Clipping to downtown...")
downtown = gdf[gdf.intersects(downtown_box)]

print("Buildings in downtown:", len(downtown))

print("Saving output...")
downtown.to_file(DOWNTOWN_OUT)

print("DONE")
