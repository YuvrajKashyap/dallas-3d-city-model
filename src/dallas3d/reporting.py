"""Research artifact writers and plots."""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

COLORS = {
    "background": "#07111f",
    "panel": "#101e31",
    "building": "#8ea7bd",
    "cyan": "#56d8e4",
    "orange": "#ff8b5c",
    "muted": "#61758b",
    "text": "#edf7ff",
}


def _style(axis):
    axis.set_facecolor(COLORS["background"])
    axis.tick_params(colors=COLORS["text"])
    for spine in axis.spines.values():
        spine.set_color(COLORS["muted"])
    axis.xaxis.label.set_color(COLORS["text"])
    axis.yaxis.label.set_color(COLORS["text"])
    axis.title.set_color(COLORS["text"])


def write_json(payload: object, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def plot_height_quality(buildings: gpd.GeoDataFrame, output_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), facecolor=COLORS["background"])
    source_order = ["osm_height", "osm_levels", "typology_area"]
    source_labels = ["OSM height", "OSM levels", "Typology + area"]
    counts = buildings["height_source"].value_counts().reindex(source_order, fill_value=0)
    axes[0].bar(source_labels, counts, color=[COLORS["cyan"], "#9de27a", COLORS["orange"]])
    axes[0].set_title("Height provenance")
    axes[0].set_ylabel("Buildings")
    axes[0].tick_params(axis="x", rotation=15)
    _style(axes[0])

    for source, color, label in zip(
        source_order,
        [COLORS["cyan"], "#9de27a", COLORS["orange"]],
        source_labels,
        strict=True,
    ):
        values = buildings.loc[buildings["height_source"] == source, "height_m"]
        axes[1].hist(values, bins=36, alpha=0.72, color=color, label=label)
    axes[1].set_xlim(0, min(310, max(100, float(buildings["height_m"].max()) + 10)))
    axes[1].set_title("Height distribution by source")
    axes[1].set_xlabel("Height (m)")
    axes[1].set_ylabel("Buildings")
    legend = axes[1].legend(facecolor=COLORS["panel"], edgecolor=COLORS["muted"])
    for text in legend.get_texts():
        text.set_color(COLORS["text"])
    _style(axes[1])
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, facecolor=fig.get_facecolor())
    plt.close(fig)


def plot_experiments(
    buildings: gpd.GeoDataFrame,
    visibility: dict[str, object],
    path: dict[str, object],
    output_path: Path,
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(15, 7), facecolor=COLORS["background"])
    buildings.plot(ax=axes[0], color=COLORS["building"], linewidth=0)
    targets = visibility["targets"]
    covered = set(visibility["covered_target_indices"])
    axes[0].scatter(
        [point[0] for index, point in enumerate(targets) if index not in covered],
        [point[1] for index, point in enumerate(targets) if index not in covered],
        s=7,
        color=COLORS["muted"],
        alpha=0.65,
    )
    axes[0].scatter(
        [point[0] for index, point in enumerate(targets) if index in covered],
        [point[1] for index, point in enumerate(targets) if index in covered],
        s=9,
        color=COLORS["cyan"],
        alpha=0.85,
    )
    observers = visibility["selected_observers"]
    axes[0].scatter(
        [point[0] for point in observers],
        [point[1] for point in observers],
        s=75,
        marker="^",
        color=COLORS["orange"],
        edgecolor=COLORS["text"],
        linewidth=0.7,
    )
    axes[0].set_title(
        f"Greedy visibility coverage · {visibility['coverage_pct']}% of sampled targets"
    )
    axes[0].legend(
        handles=[
            Line2D(
                [0],
                [0],
                marker="o",
                color="none",
                markerfacecolor=COLORS["cyan"],
                label="Visible sample",
            ),
            Line2D(
                [0],
                [0],
                marker="^",
                color="none",
                markerfacecolor=COLORS["orange"],
                label="Selected observer",
            ),
        ],
        facecolor=COLORS["panel"],
        labelcolor=COLORS["text"],
        loc="lower right",
    )

    buildings.plot(ax=axes[1], color=COLORS["building"], linewidth=0)
    coordinates = path["coordinates"]
    axes[1].plot(
        [point[0] for point in coordinates],
        [point[1] for point in coordinates],
        color=COLORS["orange"],
        linewidth=3.0,
    )
    axes[1].scatter(
        [coordinates[0][0], coordinates[-1][0]],
        [coordinates[0][1], coordinates[-1][1]],
        s=55,
        color=[COLORS["cyan"], COLORS["orange"]],
        edgecolor=COLORS["text"],
    )
    axes[1].set_title(
        "Fixed-altitude A* path · "
        f"{path['path_distance_m'] / 1000:.2f} km · {path['detour_ratio']}×"
    )

    for axis in axes:
        axis.set_aspect("equal")
        axis.set_xticks([])
        axis.set_yticks([])
        _style(axis)
    fig.suptitle(
        "Dallas 3D urban geometry experiments",
        color=COLORS["text"],
        fontsize=17,
        fontweight="bold",
    )
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)


def write_source_summary(buildings: gpd.GeoDataFrame, output_path: Path) -> None:
    summary = (
        buildings.groupby(["height_source", "height_confidence"], dropna=False)
        .agg(buildings=("osm_id", "count"), median_height_m=("height_m", "median"))
        .reset_index()
    )
    summary["share_pct"] = (100 * summary["buildings"] / len(buildings)).round(2)
    summary["median_height_m"] = summary["median_height_m"].round(2)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(output_path, index=False)
