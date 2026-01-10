import geopandas as gpd

# paths (adjust if your folder names differ)
BUILDINGS_SHP = r"texas-260103-free.shp/gis_osm_buildings_a_free_1.shp"
PLACES_SHP = r"tl_2025_48_place/tl_2025_48_place.shp"


print("Loading buildings...")
buildings = gpd.read_file(BUILDINGS_SHP)

print("Loading Texas places...")
places = gpd.read_file(PLACES_SHP)

print("Selecting Dallas boundary...")
dallas = places[(places["NAME"] == "Dallas") & (places["STATEFP"] == "48")]

print("Reprojecting to meters (EPSG:3857)...")
buildings = buildings.to_crs(3857)
dallas = dallas.to_crs(3857)

print("Clipping buildings to Dallas...")
clipped = gpd.clip(buildings, dallas)

print("Buildings in Dallas:", len(clipped))

print("Saving output...")
clipped.to_file("dallas_buildings.shp")

print("DONE")
