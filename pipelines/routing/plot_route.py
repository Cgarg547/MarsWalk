import sys
import csv

import numpy as np
import rasterio
import matplotlib.pyplot as plt


def load_route(route_csv):
    route = []

    with open(route_csv, "r") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            if line == "MarsWalk Route":
                continue

            if line.lower() == "x,y":
                continue

            parts = line.split(",")

            if len(parts) < 2:
                continue

            try:
                x = float(parts[0])
                y = float(parts[1])
            except ValueError:
                continue

            route.append((x, y))

    if not route:
        raise RuntimeError("No valid route coordinates found.")

    return np.array(route)


def plot_route(raster_path, route_csv, output_png):

    print("=" * 60)
    print("MARSWALK ROUTE VISUALIZATION")
    print("=" * 60)

    print()
    print("INPUT")
    print("-" * 60)
    print("Raster:", raster_path)
    print("Route: ", route_csv)
    print("Output:", output_png)

    route = load_route(route_csv)

    with rasterio.open(raster_path) as src:

        cost = src.read(1)
        transform = src.transform
        nodata = src.nodata

        valid = np.isfinite(cost)

        if nodata is not None:
            valid &= cost != nodata

        if not np.any(valid):
            raise RuntimeError("Raster contains no valid cells.")

        display_cost = np.where(valid, cost, np.nan)

        # Convert route coordinates to raster row/column positions
        rows = []
        cols = []

        for x, y in route:
            row, col = rasterio.transform.rowcol(
                transform,
                x,
                y
            )

            rows.append(row)
            cols.append(col)

        rows = np.asarray(rows)
        cols = np.asarray(cols)

        # Verify route points are inside raster
        inside = (
            (rows >= 0)
            & (rows < cost.shape[0])
            & (cols >= 0)
            & (cols < cost.shape[1])
        )

        if not np.all(inside):
            raise RuntimeError(
                "One or more route points fall outside the raster."
            )

        route_costs = cost[rows, cols]

        valid_route = np.isfinite(route_costs)

        if nodata is not None:
            valid_route &= route_costs != nodata

        if not np.all(valid_route):
            raise RuntimeError(
                "One or more route points intersect NoData."
            )

        # Raster extent
        left = transform.c
        top = transform.f
        right = left + transform.a * cost.shape[1]
        bottom = top + transform.e * cost.shape[0]

        print()
        print("ROUTE")
        print("-" * 60)
        print("Route points:", len(route))

        print()
        print("COST")
        print("-" * 60)
        print(f"Mean:       {np.mean(route_costs):.6f}")
        print(f"Median:     {np.median(route_costs):.6f}")
        print(f"Maximum:    {np.max(route_costs):.6f}")
        print(
            f"90th pct:   {np.percentile(route_costs, 90):.6f}"
        )

        print()
        print("BUILDING FIGURE")
        print("-" * 60)

        fig, ax = plt.subplots(figsize=(12, 10))

        image = ax.imshow(
            display_cost,
            extent=[left, right, bottom, top],
            origin="upper",
            cmap="terrain",
            vmin=0,
            vmax=1
        )

        # Route
        ax.plot(
            route[:, 0],
            route[:, 1],
            linewidth=2.5,
            label="A* route"
        )

        # Start
        ax.scatter(
            route[0, 0],
            route[0, 1],
            s=100,
            marker="o",
            edgecolors="black",
            linewidths=1.5,
            label="Start",
            zorder=5
        )

        # Goal
        ax.scatter(
            route[-1, 0],
            route[-1, 1],
            s=120,
            marker="*",
            edgecolors="black",
            linewidths=1.5,
            label="Goal",
            zorder=5
        )

        ax.set_title(
            "MarsWalk — A* Terrain-Cost Route",
            fontsize=16,
            fontweight="bold"
        )

        ax.set_xlabel("Projected X (m)")
        ax.set_ylabel("Projected Y (m)")

        ax.legend(loc="best")

        cbar = fig.colorbar(image, ax=ax)
        cbar.set_label("Terrain Cost (0 = lower, 1 = higher)")

        ax.grid(
            True,
            alpha=0.2,
            linewidth=0.5
        )

        fig.tight_layout()

        fig.savefig(
            output_png,
            dpi=200,
            bbox_inches="tight"
        )

        plt.close(fig)

    print()
    print("Output:", output_png)
    print()
    print("ROUTE VISUALIZATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":

    if len(sys.argv) != 4:
        print(
            "Usage:\n"
            "python pipelines/routing/plot_route.py "
            "<terrain_cost.tif> <route.csv> <output.png>"
        )
        sys.exit(1)

    plot_route(
        sys.argv[1],
        sys.argv[2],
        sys.argv[3]
    )