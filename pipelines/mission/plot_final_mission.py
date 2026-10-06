#!/usr/bin/env python3

import sys
import csv
from pathlib import Path

import numpy as np
import rasterio
import matplotlib.pyplot as plt


ROUTE_FILES = {
    "SHORTEST": "route_shortest.csv",
    "BALANCED": "route_balanced.csv",
    "SAFE": "route_safe.csv",
    "VERY_SAFE": "route_very_safe.csv",
}


def load_route(path):
    points = []

    with open(path, "r", newline="") as f:
        reader = csv.reader(f)

        for row in reader:
            if not row:
                continue

            # Skip:
            # MarsWalk Route
            # x,y
            if row[0].strip().lower() in {"marswalk route", "x"}:
                continue

            if len(row) < 2:
                continue

            try:
                x = float(row[0])
                y = float(row[1])
            except ValueError:
                continue

            points.append((x, y))

    if not points:
        raise RuntimeError(f"No route points found in {path}")

    return np.asarray(points)


def route_to_pixels(src, route):
    rows = []
    cols = []

    for x, y in route:
        row, col = src.index(x, y)
        rows.append(row)
        cols.append(col)

    return np.asarray(rows), np.asarray(cols)


def main():

    if len(sys.argv) != 4:
        print(
            "Usage:\n"
            "python pipelines/mission/plot_final_mission.py "
            "<terrain_cost.tif> <candidates_dir> <output.png>"
        )
        sys.exit(1)

    terrain_path = sys.argv[1]
    candidates_dir = Path(sys.argv[2])
    output_path = sys.argv[3]

    print("=" * 64)
    print("MARSWALK FINAL MISSION VISUALIZATION")
    print("=" * 64)

    print()
    print("INPUT")
    print("-" * 64)
    print(f"Terrain:    {terrain_path}")
    print(f"Candidates: {candidates_dir}")
    print(f"Output:     {output_path}")

    with rasterio.open(terrain_path) as src:

        terrain = src.read(1)
        nodata = src.nodata

        valid = np.isfinite(terrain)

        if nodata is not None:
            valid &= terrain != nodata

        if not np.any(valid):
            raise RuntimeError("Terrain raster contains no valid cells.")

        print()
        print("TERRAIN")
        print("-" * 64)
        print(f"Width:       {src.width}")
        print(f"Height:      {src.height}")
        print(f"Resolution:  {src.res}")
        print(f"CRS:         {src.crs}")
        print(f"Valid cells: {int(valid.sum())}")

        routes = {}

        print()
        print("ROUTES")
        print("-" * 64)

        for name, filename in ROUTE_FILES.items():

            path = candidates_dir / filename

            if not path.exists():
                raise FileNotFoundError(
                    f"Missing candidate route: {path}"
                )

            route = load_route(path)
            routes[name] = route

            print(
                f"{name:<12} "
                f"{len(route):>4} points"
            )

        # ---------------------------------------------------------
        # Plot terrain
        # ---------------------------------------------------------

        print()
        print("BUILDING FIGURE")
        print("-" * 64)

        terrain_plot = terrain.astype(float).copy()
        terrain_plot[~valid] = np.nan

        left, bottom, right, top = src.bounds

        fig, ax = plt.subplots(figsize=(14, 11))

        image = ax.imshow(
            terrain_plot,
            extent=(left, right, bottom, top),
            origin="upper",
            interpolation="nearest",
        )

        colorbar = fig.colorbar(
            image,
            ax=ax,
            shrink=0.82,
            pad=0.02,
        )

        colorbar.set_label(
            "Terrain Cost",
            fontsize=12,
        )

        # ---------------------------------------------------------
        # Plot candidate routes
        # ---------------------------------------------------------

        line_styles = {
            "SHORTEST": "--",
            "BALANCED": "-",
            "SAFE": "-",
            "VERY_SAFE": "-",
        }

        line_widths = {
            "SHORTEST": 2.0,
            "BALANCED": 2.2,
            "SAFE": 2.6,
            "VERY_SAFE": 3.5,
        }

        for name, route in routes.items():

            rows, cols = route_to_pixels(src, route)

            xs = route[:, 0]
            ys = route[:, 1]

            ax.plot(
                xs,
                ys,
                linestyle=line_styles[name],
                linewidth=line_widths[name],
                label=name,
                alpha=0.95,
            )

        # ---------------------------------------------------------
        # Start / Goal
        # ---------------------------------------------------------

        recommended = routes["VERY_SAFE"]

        start_x, start_y = recommended[0]
        goal_x, goal_y = recommended[-1]

        ax.scatter(
            start_x,
            start_y,
            s=180,
            marker="o",
            edgecolor="black",
            linewidth=2,
            zorder=10,
            label="START",
        )

        ax.scatter(
            goal_x,
            goal_y,
            s=220,
            marker="*",
            edgecolor="black",
            linewidth=2,
            zorder=10,
            label="GOAL",
        )

        ax.annotate(
            "START",
            xy=(start_x, start_y),
            xytext=(12, 12),
            textcoords="offset points",
            fontsize=11,
            fontweight="bold",
            bbox=dict(
                boxstyle="round,pad=0.3",
                alpha=0.85,
            ),
        )

        ax.annotate(
            "GOAL",
            xy=(goal_x, goal_y),
            xytext=(12, 12),
            textcoords="offset points",
            fontsize=11,
            fontweight="bold",
            bbox=dict(
                boxstyle="round,pad=0.3",
                alpha=0.85,
            ),
        )

        # ---------------------------------------------------------
        # Recommended route annotation
        # ---------------------------------------------------------

        ax.text(
            0.02,
            0.98,
            "RECOMMENDED ROUTE\nVERY_SAFE\n"
            "Distance: 1.558 km\n"
            "Mean cost: 0.228\n"
            "P90 cost: 0.399\n"
            "≥0.70 exposure: 2.16%\n"
            "Risk score: 0.307",
            transform=ax.transAxes,
            verticalalignment="top",
            fontsize=11,
            fontweight="bold",
            bbox=dict(
                boxstyle="round,pad=0.6",
                alpha=0.90,
            ),
        )

        # ---------------------------------------------------------
        # Title / labels
        # ---------------------------------------------------------

        ax.set_title(
            "MarsWalk — Autonomous Terrain Route Planning\n"
            "Jezero Crater Mission Demonstration",
            fontsize=17,
            fontweight="bold",
            pad=15,
        )

        ax.set_xlabel(
            "Projected X (m)",
            fontsize=12,
        )

        ax.set_ylabel(
            "Projected Y (m)",
            fontsize=12,
        )

        ax.grid(
            True,
            alpha=0.25,
            linewidth=0.6,
        )

        ax.legend(
            loc="lower right",
            framealpha=0.92,
            fontsize=10,
        )

        # ---------------------------------------------------------
        # Save
        # ---------------------------------------------------------

        output = Path(output_path)
        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        plt.tight_layout()

        fig.savefig(
            output,
            dpi=200,
            bbox_inches="tight",
        )

        plt.close(fig)

    print()
    print(f"Output: {output}")
    print()
    print("=" * 64)
    print("FINAL MISSION VISUALIZATION COMPLETE")
    print("=" * 64)


if __name__ == "__main__":
    main()