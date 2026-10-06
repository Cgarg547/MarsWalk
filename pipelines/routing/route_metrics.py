import sys
import csv
import math

import numpy as np
import rasterio


def load_route(route_csv):
    route = []

    with open(route_csv, "r") as f:
        for line in f:
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Skip MarsWalk title/header
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

    return route


def route_metrics(route_csv, terrain_raster):

    print("=" * 60)
    print("MARSWALK ROUTE METRICS")
    print("=" * 60)

    print()
    print("INPUT")
    print("-" * 60)
    print(f"Route:   {route_csv}")
    print(f"Raster:  {terrain_raster}")

    route = load_route(route_csv)

    print()
    print("ROUTE")
    print("-" * 60)
    print(f"Route points: {len(route)}")

    with rasterio.open(terrain_raster) as src:

        print(f"CRS:         {src.crs}")
        print(f"Resolution:  {src.res}")

        costs = []

        valid_points = 0
        invalid_points = 0

        for x, y in route:

            try:
                row, col = src.index(x, y)

                value = src.read(
                    1,
                    window=((row, row + 1), (col, col + 1))
                )[0, 0]

                if (
                    np.isfinite(value)
                    and value != src.nodata
                ):
                    costs.append(float(value))
                    valid_points += 1
                else:
                    invalid_points += 1

            except Exception:
                invalid_points += 1

    # ---------------------------------------------------------
    # DISTANCE
    # ---------------------------------------------------------

    distances = []

    total_distance = 0.0

    for i in range(1, len(route)):

        x1, y1 = route[i - 1]
        x2, y2 = route[i]

        dx = x2 - x1
        dy = y2 - y1

        distance = math.sqrt(
            dx * dx +
            dy * dy
        )

        distances.append(distance)
        total_distance += distance

    # ---------------------------------------------------------
    # COST STATISTICS
    # ---------------------------------------------------------

    costs_array = np.asarray(costs, dtype=float)

    mean_cost = float(np.mean(costs_array))
    median_cost = float(np.median(costs_array))
    max_cost = float(np.max(costs_array))

    p90_cost = float(np.percentile(costs_array, 90))
    p95_cost = float(np.percentile(costs_array, 95))

    # ---------------------------------------------------------
    # HIGH COST EXPOSURE
    # ---------------------------------------------------------

    high_cost_70 = int(np.sum(costs_array >= 0.70))
    high_cost_80 = int(np.sum(costs_array >= 0.80))
    high_cost_90 = int(np.sum(costs_array >= 0.90))

    high_cost_70_pct = (
        high_cost_70 / len(costs_array) * 100
    )

    high_cost_80_pct = (
        high_cost_80 / len(costs_array) * 100
    )

    high_cost_90_pct = (
        high_cost_90 / len(costs_array) * 100
    )

    # ---------------------------------------------------------
    # RESULTS
    # ---------------------------------------------------------

    print()
    print("DISTANCE")
    print("-" * 60)

    print(f"Total distance:       {total_distance:.3f} m")
    print(f"Total distance:       {total_distance / 1000:.3f} km")

    print()
    print("TERRAIN COST")
    print("-" * 60)

    print(f"Mean:                 {mean_cost:.6f}")
    print(f"Median:               {median_cost:.6f}")
    print(f"Maximum:              {max_cost:.6f}")
    print(f"90th percentile:      {p90_cost:.6f}")
    print(f"95th percentile:      {p95_cost:.6f}")

    print()
    print("HIGH-COST EXPOSURE")
    print("-" * 60)

    print(
        f"Cost >= 0.70:         "
        f"{high_cost_70} points "
        f"({high_cost_70_pct:.2f}%)"
    )

    print(
        f"Cost >= 0.80:         "
        f"{high_cost_80} points "
        f"({high_cost_80_pct:.2f}%)"
    )

    print(
        f"Cost >= 0.90:         "
        f"{high_cost_90} points "
        f"({high_cost_90_pct:.2f}%)"
    )

    print()
    print("DATA VALIDITY")
    print("-" * 60)

    print(f"Valid route points:   {valid_points}")
    print(f"Invalid route points: {invalid_points}")

    if invalid_points == 0:
        print("PASS: Every route point intersects valid terrain data.")
    else:
        print("WARNING: Some route points intersect invalid terrain.")

    print()
    print("MARSWALK ROUTE METRICS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":

    if len(sys.argv) != 3:

        print(
            "Usage:\n"
            "python pipelines/routing/route_metrics.py "
            "<route.csv> <terrain_cost.tif>"
        )

        sys.exit(1)

    route_metrics(
        sys.argv[1],
        sys.argv[2]
    )