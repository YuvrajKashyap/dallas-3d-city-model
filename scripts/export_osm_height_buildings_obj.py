import geopandas as gpd
import trimesh
from shapely.geometry import Polygon, MultiPolygon

IN_GPKG = "data/processed/dallas_cbd_4000m_osm_buildings_height.gpkg"
IN_LAYER = "buildings"

OUT_OBJ = "data/processed/dallas_cbd_4000m_osm_buildings_extruded.obj"
OUT_GLB = "data/processed/dallas_cbd_4000m_osm_buildings_extruded.glb"

def iter_polygons(geom):
    if geom is None:
        return
    if isinstance(geom, Polygon):
        yield geom
    elif isinstance(geom, MultiPolygon):
        for p in geom.geoms:
            yield p

def main():
    print("Loading:", IN_GPKG)
    gdf = gpd.read_file(IN_GPKG, layer=IN_LAYER)
    if gdf.crs is None:
        raise ValueError("Missing CRS in input.")
    gdf = gdf.to_crs(3857)

    if "height_m" not in gdf.columns:
        raise ValueError("height_m column missing. Did you run enrichment?")

    # Shift origin near centroid so Blender doesn't get huge coordinates
    center = gdf.unary_union.centroid
    cx, cy = center.x, center.y

    meshes = []
    total = len(gdf)
    print("Buildings:", total)

    for i, row in gdf.iterrows():
        h = float(row["height_m"])
        geom = row.geometry
        if geom is None:
            continue

        for poly in iter_polygons(geom):
            try:
                # translate polygon near origin
                poly2 = Polygon(
                    [(x - cx, y - cy) for (x, y) in poly.exterior.coords],
                    holes=[[(x - cx, y - cy) for (x, y) in ring.coords] for ring in poly.interiors]
                )
                m = trimesh.creation.extrude_polygon(poly2, height=h)
                meshes.append(m)
            except Exception:
                continue

        if (i % 500) == 0:
            print(f"  processed {i}/{total}")

    if not meshes:
        raise RuntimeError("No meshes created.")

    city = trimesh.util.concatenate(meshes)

    print("Exporting OBJ:", OUT_OBJ)
    city.export(OUT_OBJ)

    print("Exporting GLB:", OUT_GLB)
    city.export(OUT_GLB)

    print("DONE.")

if __name__ == "__main__":
    main()
