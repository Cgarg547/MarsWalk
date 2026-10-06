#!/usr/bin/env python3

import sys
import csv
from pathlib import Path

import numpy as np
import rasterio
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec


ROUTES = {
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
            if len(row) < 2:
                continue

            try:
                x = float(row[0])
                y = float(row[1])
            except ValueError:
                continue

            points.append((x, y))

    if not points:
        raise RuntimeError(f"No route points found: {path}")

    return np.asarray(points)


def distance(route):
    if len(route) < 2:
        return 0.0

    dx = np.diff(route[:, 0])
    dy = np.diff(route[:, 1])

    return float(np.sum(np.sqrt(dx * dx + dy * dy)))


def terrain_values(src, terrain, route):
    values = []

    for x, y in route:
        row, col = src.index(x, y)

        if (
            0 <= row < terrain.shape[0]
            and 0 <= col < terrain.shape[1]
        ):
            value = terrain[row, col]

            if np.isfinite(value) and value != src.nodata:
                values.append(float(value))

    return np.asarray(values)


def route_metrics(src, terrain, route):

    values = terrain_values(src, terrain, route)

    if len(values) == 0:
        raise RuntimeError("Route contains no valid terrain samples.")

    d = distance(route)

    mean = float(np.mean(values))
    p90 = float(np.percentile(values, 90))
    exposure = float(np.mean(values >= 0.70) * 100)

    # Conceptual risk score consistent with the mission-risk layer.
    risk = (
        0.40 * mean
        + 0.35 * p90
        + 0.25 * (exposure / 100.0)
    )

    return {
        "distance": d,
        "mean": mean,
        "p90": p90,
        "exposure": exposure,
        "risk": risk,
    }


def main():

    if len(sys.argv) != 4:
        print(
            "Usage:\n"
            "python pipelines/mission/mission_dashboard.py "
            "<terrain_cost.tif> <candidates_dir> <output.png>"
        )
        sys.exit(1)

    terrain_path = sys.argv[1]
    candidates_dir = Path(sys.argv[2])
    output_path = Path(sys.argv[3])

    print("=" * 64)
    print("MARSWALK MISSION DASHBOARD")
    print("=" * 64)

    print()
    print("INPUT")
    print("-" * 64)
    print(f"Terrain:    {terrain_path}")
    print(f"Candidates: {candidates_dir}")
    print(f"Output:     {output_path}")

    with rasterio.open(terrain_path) as src:

        terrain = src.read(1)

        valid = np.isfinite(terrain)

        if src.nodata is not None:
            valid &= terrain != src.nodata

        print()
        print("TERRAIN")
        print("-" * 64)
        print(f"Dimensions: {src.width} × {src.height}")
        print(f"Resolution: {src.res}")
        print(f"CRS:        {src.crs}")
        print(f"Valid cells: {int(valid.sum())}")

        routes = {}
        metrics = {}

        print()
        print("ROUTES")
        print("-" * 64)

        for name, filename in ROUTES.items():

            route_path = candidates_dir / filename

            if not route_path.exists():
                raise FileNotFoundError(
                    f"Missing route: {route_path}"
                )

            route = load_route(route_path)

            routes[name] = route
            metrics[name] = route_metrics(
                src,
                terrain,
                route,
            )

            m = metrics[name]

            print(
                f"{name:<12}"
                f"{m['distance']:>9.2f} m  "
                f"mean={m['mean']:.4f}  "
                f"p90={m['p90']:.4f}  "
                f"risk={m['risk']:.4f}"
            )

        recommended = "VERY_SAFE"

        # ---------------------------------------------------------
        # Figure
        # ---------------------------------------------------------

        print()
        print("BUILDING DASHBOARD")
        print("-" * 64)

        fig = plt.figure(
            figsize=(17, 11)
        )

        gs = GridSpec(
            2,
            2,
            figure=fig,
            width_ratios=[1.45, 1.0],
            height_ratios=[1.25, 1.0],
            hspace=0.30,
            wspace=0.20,
        )

        # ---------------------------------------------------------
        # TERRAIN MAP
        # ---------------------------------------------------------

        ax_map = fig.add_subplot(gs[0, 0])

        terrain_plot = terrain.astype(float).copy()
        terrain_plot[~valid] = np.nan

        left, bottom, right, top = src.bounds

        image = ax_map.imshow(
            terrain_plot,
            extent=(left, right, bottom, top),
            origin="upper",
            interpolation="nearest",
        )

        fig.colorbar(
            image,
            ax=ax_map,
            shrink=0.78,
            pad=0.02,
            label="Terrain Cost",
        )

        for name, route in routes.items():

            if name == "VERY_SAFE":
                linewidth = 3.5
                linestyle = "-"
            elif name == "SAFE":
                linewidth = 2.3
                linestyle = "-"
            elif name == "BALANCED":
                linewidth = 2.0
                linestyle = "-"
            else:
                linewidth = 1.8
                linestyle = "--"

            ax_map.plot(
                route[:, 0],
                route[:, 1],
                linewidth=linewidth,
                linestyle=linestyle,
                label=name,
                alpha=0.95,
            )

        recommended_route = routes[recommended]

        start = recommended_route[0]
        goal = recommended_route[-1]

        ax_map.scatter(
            start[0],
            start[1],
            s=160,
            marker="o",
            edgecolor="black",
            linewidth=2,
            zorder=10,
            label="START",
        )

        ax_map.scatter(
            goal[0],
            goal[1],
            s=200,
            marker="*",
            edgecolor="black",
            linewidth=2,
            zorder=10,
            label="GOAL",
        )

        ax_map.set_title(
            "Jezero Crater — Terrain & Candidate Routes",
            fontsize=14,
            fontweight="bold",
        )

        ax_map.set_xlabel("Projected X (m)")
        ax_map.set_ylabel("Projected Y (m)")

        ax_map.grid(
            True,
            alpha=0.25,
        )

        ax_map.legend(
            fontsize=8,
            loc="lower right",
            framealpha=0.9,
        )

        # ---------------------------------------------------------
        # MISSION STATUS
        # ---------------------------------------------------------

        ax_status = fig.add_subplot(gs[0, 1])

        ax_status.axis("off")

        rec = metrics[recommended]

        travel_hours = rec["distance"] / 0.05 / 3600.0

        status_text = (
            "MARSWALK\n"
            "AUTONOMOUS MARTIAN TERRAIN ROUTING\n\n"
            "MISSION: JEZERO CRATER\n\n"
            "RECOMMENDED ROUTE\n"
            f"{recommended}\n\n"
            f"Distance       {rec['distance'] / 1000:.3f} km\n"
            f"Travel time    {travel_hours:.2f} h\n"
            f"Mean cost      {rec['mean']:.3f}\n"
            f"P90 cost       {rec['p90']:.3f}\n"
            f"≥0.70 exposure {rec['exposure']:.2f}%\n"
            f"Risk score     {rec['risk']:.3f}\n\n"
            "DATA CONFIDENCE\n"
            "HIGH\n\n"
            "MODEL STATUS\n"
            "RESEARCH / DEMO"
        )

        ax_status.text(
            0.05,
            0.95,
            status_text,
            transform=ax_status.transAxes,
            verticalalignment="top",
            fontsize=13,
            fontweight="bold",
            bbox=dict(
                boxstyle="round,pad=0.8",
                alpha=0.90,
            ),
        )

        # ---------------------------------------------------------
        # ROUTE COMPARISON
        # ---------------------------------------------------------

        ax_compare = fig.add_subplot(gs[1, 0])

        names = [
            "SHORTEST",
            "BALANCED",
            "SAFE",
            "VERY_SAFE",
        ]

        distance_values = [
            metrics[n]["distance"]
            for n in names
        ]

        risk_values = [
            metrics[n]["risk"]
            for n in names
        ]

        x = np.arange(len(names))
        width = 0.36

        ax_compare.bar(
            x - width / 2,
            np.asarray(distance_values) / 1000.0,
            width,
            label="Distance (km)",
        )

        ax_compare.bar(
            x + width / 2,
            np.asarray(risk_values),
            width,
            label="Risk score",
        )

        ax_compare.set_xticks(x)
        ax_compare.set_xticklabels(
            names,
            rotation=15,
        )

        ax_compare.set_title(
            "Route Tradeoff",
            fontsize=13,
            fontweight="bold",
        )

        ax_compare.set_ylabel(
            "Distance / Risk"
        )

        ax_compare.grid(
            axis="y",
            alpha=0.25,
        )

        ax_compare.legend()

        # ---------------------------------------------------------
        # DECISION TABLE
        # ---------------------------------------------------------

        ax_table = fig.add_subplot(gs[1, 1])

        ax_table.axis("off")

        table_data = []

        for name in names:

            m = metrics[name]

            table_data.append(
                [
                    name,
                    f"{m['distance'] / 1000:.3f}",
                    f"{m['mean']:.3f}",
                    f"{m['p90']:.3f}",
                    f"{m['exposure']:.2f}%",
                ]
            )

        table = ax_table.table(
            cellText=table_data,
            colLabels=[
                "Route",
                "km",
                "Mean",
                "P90",
                "≥0.70",
            ],
            loc="center",
            cellLoc="center",
        )

        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(
            1.0,
            2.0,
        )

        ax_table.set_title(
            "Mission Decision Matrix",
            fontsize=13,
            fontweight="bold",
            pad=15,
        )

        # ---------------------------------------------------------
        # MAIN TITLE
        # ---------------------------------------------------------

        fig.suptitle(
            "MarsWalk — Autonomous Martian Mission Planning Dashboard",
            fontsize=20,
            fontweight="bold",
            y=0.98,
        )

        fig.text(
            0.5,
            0.015,
            "Research / demonstration model — "
            "not NASA-certified mobility or mission-planning software",
            ha="center",
            fontsize=9,
        )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        fig.savefig(
            output_path,
            dpi=200,
            bbox_inches="tight",
        )

        plt.close(fig)

    print()
    print(f"Output: {output_path}")

    print()
    print("=" * 64)
    print("MISSION DASHBOARD COMPLETE")
    print("=" * 64)


if __name__ == "__main__":
    main()