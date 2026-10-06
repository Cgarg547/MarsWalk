import sys
import csv
from pathlib import Path

import numpy as np
import rasterio
import matplotlib.pyplot as plt


ROUTE_FILES = {
    "shortest": "route_shortest.csv",
    "balanced": "route_balanced.csv",
    "safe": "route_safe.csv",
    "very_safe": "route_very_safe.csv",
}


def load_route(path):
    points = []

    with open(path, "r", newline="") as f:
        reader = csv.reader(f)

        for row in reader:
            if not row:
                continue

            # Skip header/title rows
            if row[0] in ("MarsWalk Route", "x"):
                continue

            try:
                x = float(row[0])
                y = float(row[1])
                points.append((x, y))
            except (ValueError, IndexError):
                continue

    return np.array(points)


def plot_route_comparison(raster_path, candidates_dir, output_path):

    print("=" * 60)
    print("MARSWALK ROUTE COMPARISON VISUALIZATION")
    print("=" * 60)

    print("\nINPUT")
    print("-" * 60)
    print(f"Raster:     {raster_path}")
    print(f"Candidates: {candidates_dir}")
    print(f"Output:     {output_path}")

    with rasterio.open(raster_path) as src:
        terrain = src.read(1)
        transform = src.transform
        nodata = src.nodata

        valid = np.isfinite(terrain)

        if nodata is not None:
            valid &= terrain != nodata

        terrain_plot = np.where(valid, terrain, np.nan)

        left = src.bounds.left
        right = src.bounds.right
        bottom = src.bounds.bottom
        top = src.bounds.top

        extent = [left, right, bottom, top]

        print("\nTERRAIN")
        print("-" * 60)
        print(f"Width:      {src.width}")
        print(f"Height:     {src.height}")
        print(f"Resolution: {src.res}")
        print(f"CRS:        {src.crs}")

    routes = {}

    print("\nROUTES")
    print("-" * 60)

    for name, filename in ROUTE_FILES.items():

        path = Path(candidates_dir) / filename

        if not path.exists():
            raise FileNotFoundError(
                f"Missing route file: {path}"
            )

        route = load_route(path)

        if len(route) == 0:
            raise RuntimeError(
                f"No route points found in {path}"
            )

        routes[name] = route

        print(
            f"{name.upper():12s} "
            f"{len(route):4d} points"
        )

    print("\nBUILDING FIGURE")
    print("-" * 60)

    fig, ax = plt.subplots(figsize=(12, 10))

    image = ax.imshow(
        terrain_plot,
        extent=extent,
        origin="upper",
        interpolation="nearest"
    )

    cbar = fig.colorbar(
        image,
        ax=ax,
        shrink=0.82
    )

    cbar.set_label(
        "Terrain Cost (0 = easier, 1 = harder)"
    )

    styles = {
        "shortest": {
            "linewidth": 1.8,
            "label": "Shortest"
        },
        "balanced": {
            "linewidth": 2.0,
            "label": "Balanced"
        },
        "safe": {
            "linewidth": 2.8,
            "label": "Safe — Recommended"
        },
        "very_safe": {
            "linewidth": 2.0,
            "label": "Very Safe"
        },
    }

    for name in ["shortest", "balanced", "safe", "very_safe"]:

        route = routes[name]

        ax.plot(
            route[:, 0],
            route[:, 1],
            linewidth=styles[name]["linewidth"],
            label=styles[name]["label"]
        )

    # Start and goal from SAFE route
    safe_route = routes["safe"]

    start = safe_route[0]
    goal = safe_route[-1]

    ax.scatter(
        start[0],
        start[1],
        s=120,
        marker="o",
        edgecolor="black",
        linewidth=1.5,
        label="Start",
        zorder=10
    )

    ax.scatter(
        goal[0],
        goal[1],
        s=150,
        marker="*",
        edgecolor="black",
        linewidth=1.5,
        label="Goal",
        zorder=10
    )

    ax.annotate(
        "START",
        xy=start,
        xytext=(10, 10),
        textcoords="offset points",
        fontsize=10,
        fontweight="bold"
    )

    ax.annotate(
        "GOAL",
        xy=goal,
        xytext=(10, 10),
        textcoords="offset points",
        fontsize=10,
        fontweight="bold"
    )

    ax.set_title(
        "MarsWalk — Candidate Route Comparison\n"
        "Jezero Crater Terrain-Cost Routing",
        fontsize=15,
        fontweight="bold"
    )

    ax.set_xlabel("Projected X")
    ax.set_ylabel("Projected Y")

    ax.legend(
        loc="best",
        frameon=True
    )

    ax.set_aspect("equal")

    ax.grid(
        True,
        alpha=0.25,
        linewidth=0.5
    )

    plt.tight_layout()

    output_path = Path(output_path)
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    plt.savefig(
        output_path,
        dpi=200,
        bbox_inches="tight"
    )

    plt.close()

    print(f"\nOutput: {output_path}")

    print("\nROUTE COMPARISON VISUALIZATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":

    if len(sys.argv) != 4:
        print(
            "Usage:\n"
            "python pipelines/routing/plot_route_comparison.py "
            "<terrain_cost.tif> "
            "<candidates_dir> "
            "<output.png>"
        )
        sys.exit(1)

    plot_route_comparison(
        sys.argv[1],
        sys.argv[2],
        sys.argv[3]
    )