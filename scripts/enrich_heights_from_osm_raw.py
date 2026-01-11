import re
import numpy as np
import pandas as pd
import geopandas as gpd

IN_GPKG = "data/processed/dallas_cbd_4000m_osm_buildings_raw.gpkg"
IN_LAYER = "buildings"

OUT_GPKG = "data/processed/dallas_cbd_4000m_osm_buildings_height.gpkg"
OUT_SHP  = "data/processed/dallas_cbd_4000m_osm_buildings_height.shp"
REPORT_CSV = "data/processed/dallas_cbd_4000m_osm_buildings_height_quality.csv"
HIST_PNG = "data/processed/dallas_cbd_4000m_osm_buildings_height_hist.png"

# Use 3.2m per floor as a reasonable downtown average (residential+office mix).
LEVEL_M = 3.2
RNG_SEED = 42

def parse_height_to_m(val):
    if val is None:
        return np.nan
    if isinstance(val, (int, float)) and np.isfinite(val):
        return float(val) if val > 0 else np.nan
    s = str(val).strip().lower()
    if s in ("", "nan", "none", "null"):
        return np.nan
    m = re.search(r"(-?\d+(\.\d+)?)", s)
    if not m:
        return np.nan
    num = float(m.group(1))
    if num <= 0:
        return np.nan
    if "ft" in s or "feet" in s or "'" in s:
        return num * 0.3048
    return num

def parse_levels(val):
    if val is None:
        return np.nan
    if isinstance(val, (int, float)) and np.isfinite(val):
        return float(val) if val > 0 else np.nan
    s = str(val).strip().lower()
    if s in ("", "nan", "none", "null"):
        return np.nan
    m = re.search(r"(\d+(\.\d+)?)", s)
    if not m:
        return np.nan
    num = float(m.group(1))
    return num if num > 0 else np.nan

def sample_random_height(area):
    # Same piecewise distribution you already used, based on footprint size.
    if not np.isfinite(area) or area <= 0:
        area = 300.0
    if area < 200:
        return np.random.uniform(3.0, 12.0)
    elif area < 1000:
        h = np.random.lognormal(mean=np.log(20.0), sigma=0.5)
        return float(np.clip(h, 6.0, 60.0))
    elif area < 5000:
        h = np.random.lognormal(mean=np.log(45.0), sigma=0.6)
        return float(np.clip(h, 12.0, 180.0))
    else:
        h = np.random.lognormal(mean=np.log(80.0), sigma=0.7)
        return float(np.clip(h, 15.0, 300.0))

def main():
    np.random.seed(RNG_SEED)

    print("Loading:", IN_GPKG)
    gdf = gpd.read_file(IN_GPKG, layer=IN_LAYER)
    if gdf.crs is None:
        raise ValueError("Missing CRS in input.")

    # Ensure meters
    gdf_m = gdf.to_crs(3857).copy()
    gdf_m["area_m2"] = gdf_m.geometry.area

    # 1) OSM height (height or building:height)
    h1 = gdf_m["height"].apply(parse_height_to_m) if "height" in gdf_m.columns else np.nan
    h2 = gdf_m["building:height"].apply(parse_height_to_m) if "building:height" in gdf_m.columns else np.nan
    # combine: prefer building:height then height
    if isinstance(h1, float) and np.isnan(h1):
        gdf_m["height_osm_m"] = np.nan
    else:
        gdf_m["height_osm_m"] = pd.concat(
            [h2 if not isinstance(h2, float) else pd.Series(np.nan, index=gdf_m.index),
             h1 if not isinstance(h1, float) else pd.Series(np.nan, index=gdf_m.index)],
            axis=1
        ).bfill(axis=1).iloc[:, 0]

    # 2) levels fallback
    lv = gdf_m["building:levels"].apply(parse_levels) if "building:levels" in gdf_m.columns else np.nan
    if isinstance(lv, float) and np.isnan(lv):
        gdf_m["levels"] = np.nan
    else:
        gdf_m["levels"] = lv
    gdf_m["height_levels_m"] = gdf_m["levels"] * LEVEL_M

    # 3) final height_m
    gdf_m["height_m"] = gdf_m["height_osm_m"]

    use_levels = gdf_m["height_m"].isna() & gdf_m["height_levels_m"].notna() & (gdf_m["height_levels_m"] > 0)
    gdf_m.loc[use_levels, "height_m"] = gdf_m.loc[use_levels, "height_levels_m"]

    missing = gdf_m["height_m"].isna() | (gdf_m["height_m"] <= 0)
    gdf_m.loc[missing, "height_m"] = gdf_m.loc[missing, "area_m2"].apply(sample_random_height)

    # Add tall tail among randomized
    missing_idx = gdf_m.index[missing]
    if len(missing_idx) > 0:
        k = max(1, int(0.005 * len(missing_idx)))
        cand = gdf_m.loc[missing_idx].sort_values("area_m2", ascending=False).head(max(k * 10, k))
        chosen = cand.sample(n=k, random_state=RNG_SEED).index
        gdf_m.loc[chosen, "height_m"] = np.random.uniform(120.0, 300.0, size=len(chosen))

    gdf_m["height_src"] = "random"
    gdf_m.loc[use_levels, "height_src"] = "levels"
    gdf_m.loc[gdf_m["height_osm_m"].notna() & (gdf_m["height_osm_m"] > 0), "height_src"] = "osm_height"

    gdf_m["height_m"] = gdf_m["height_m"].clip(lower=2.5, upper=350.0)

    # Quality report
    n = len(gdf_m)
    pct_osm = gdf_m["height_src"].eq("osm_height").mean() * 100.0 if n else 0
    pct_lvl = gdf_m["height_src"].eq("levels").mean() * 100.0 if n else 0
    pct_rnd = gdf_m["height_src"].eq("random").mean() * 100.0 if n else 0

    stats = gdf_m["height_m"].describe(percentiles=[0.1, 0.25, 0.5, 0.75, 0.9]).to_dict()
    summary = {
        "n_buildings": n,
        "pct_osm_height": pct_osm,
        "pct_levels": pct_lvl,
        "pct_random": pct_rnd,
        "min_m": float(stats["min"]),
        "p10_m": float(stats["10%"]),
        "p25_m": float(stats["25%"]),
        "median_m": float(stats["50%"]),
        "p75_m": float(stats["75%"]),
        "p90_m": float(stats["90%"]),
        "max_m": float(stats["max"]),
        "mean_m": float(stats["mean"]),
    }

    pd.DataFrame([summary]).to_csv(REPORT_CSV, index=False)
    print("\nQUALITY REPORT (also saved to CSV):")
    for k, v in summary.items():
        print(f"  {k}: {v}")

    # Histogram
    import matplotlib.pyplot as plt
    plt.figure()
    plt.hist(gdf_m["height_m"].values, bins=50)
    plt.xlabel("Building height (m)")
    plt.ylabel("Count")
    plt.title("Dallas CBD 4km OSM Buildings: height_m distribution")
    plt.tight_layout()
    plt.savefig(HIST_PNG, dpi=200)
    plt.close()
    print("Histogram saved:", HIST_PNG)

    # Save outputs
    print("\nWriting:", OUT_GPKG)
    gdf_m.to_file(OUT_GPKG, layer="buildings", driver="GPKG")

    print("Writing:", OUT_SHP)
    gdf_m.to_file(OUT_SHP)

    print("\nDONE.")

if __name__ == "__main__":
    main()
