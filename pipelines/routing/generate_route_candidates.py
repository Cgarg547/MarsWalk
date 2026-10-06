import csv
import heapq
import math
import os
import sys

import numpy as np
import rasterio


MOVES = [
    (-1, 0, 1.0),
    (1, 0, 1.0),
    (0, -1, 1.0),
    (0, 1, 1.0),
    (-1, -1, math.sqrt(2)),
    (-1, 1, math.sqrt(2)),
    (1, -1, math.sqrt(2)),
    (1, 1, math.sqrt(2)),
]


def load_surface(path):
    with rasterio.open(path) as src:
        data = src.read(1).astype(np.float64)
        transform = src.transform
        nodata = src.nodata
        resolution = float(abs(transform.a))

    valid = np.isfinite(data)

    if nodata is not None:
        valid &= data != nodata

    return data, valid, transform, resolution


def nearest_valid(valid, row, col, max_radius=20):
    if (
        0 <= row < valid.shape[0]
        and 0 <= col < valid.shape[1]
        and valid[row, col]
    ):
        return row, col

    for radius in range(1, max_radius + 1):
        r0 = max(0, row - radius)
        r1 = min(valid.shape[0], row + radius + 1)
        c0 = max(0, col - radius)
        c1 = min(valid.shape[1], col + radius + 1)

        candidates = []

        for r in range(r0, r1):
            for c in range(c0, c1):
                if valid[r, c]:
                    distance = math.hypot(r - row, c - col)
                    candidates.append((distance, r, c))

        if candidates:
            candidates.sort()
            return candidates[0][1], candidates[0][2]

    return None


def heuristic(node, goal, resolution):
    r, c = node
    gr, gc = goal

    return math.hypot(gr - r, gc - c) * resolution


def astar(cost, valid, start, goal, terrain_weight):
    height, width = cost.shape

    start = nearest_valid(valid, *start)
    goal = nearest_valid(valid, *goal)

    if start is None:
        raise RuntimeError("Unable to find valid start location.")

    if goal is None:
        raise RuntimeError("Unable to find valid goal location.")

    open_set = []

    g_score = {
        start: 0.0
    }

    came_from = {}

    heapq.heappush(
        open_set,
        (
            heuristic(start, goal, 1.0),
            0.0,
            start,
        ),
    )

    closed = set()

    while open_set:
        _, current_g, current = heapq.heappop(open_set)

        if current in closed:
            continue

        closed.add(current)

        if current == goal:
            path = [current]

            while current in came_from:
                current = came_from[current]
                path.append(current)

            path.reverse()
            return path

        r, c = current

        for dr, dc, movement_factor in MOVES:
            nr = r + dr
            nc = c + dc

            if nr < 0 or nr >= height or nc < 0 or nc >= width:
                continue

            if not valid[nr, nc]:
                continue

            movement_distance = movement_factor

            terrain_penalty = 1.0 + terrain_weight * max(
                0.0,
                float(cost[nr, nc])
            )

            step_cost = movement_distance * terrain_penalty

            tentative_g = current_g + step_cost

            neighbor = (nr, nc)

            if tentative_g < g_score.get(neighbor, float("inf")):
                g_score[neighbor] = tentative_g
                came_from[neighbor] = current

                f_score = (
                    tentative_g
                    + heuristic(neighbor, goal, 1.0)
                )

                heapq.heappush(
                    open_set,
                    (
                        f_score,
                        tentative_g,
                        neighbor,
                    ),
                )

    return None


def write_route(path, transform, output_csv):
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)

    with open(output_csv, "w", newline="") as f:
        writer = csv.writer(f)

        writer.writerow(["MarsWalk Route"])
        writer.writerow(["x", "y"])

        for row, col in path:
            x, y = rasterio.transform.xy(
                transform,
                row,
                col,
                offset="center",
            )

            writer.writerow(
                [
                    f"{x:.3f}",
                    f"{y:.3f}",
                ]
            )


def route_distance(path, resolution):
    distance = 0.0

    for (r1, c1), (r2, c2) in zip(path[:-1], path[1:]):
        distance += math.hypot(
            r2 - r1,
            c2 - c1,
        ) * resolution

    return distance


def summarize_route(path, cost, resolution):
    values = np.array(
        [cost[r, c] for r, c in path],
        dtype=float,
    )

    distance = route_distance(path, resolution)

    return {
        "nodes": len(path),
        "distance_m": distance,
        "mean_cost": float(np.mean(values)),
        "median_cost": float(np.median(values)),
        "max_cost": float(np.max(values)),
        "p90_cost": float(np.percentile(values, 90)),
        "p95_cost": float(np.percentile(values, 95)),
        "high_cost_70_pct": float(
            np.mean(values >= 0.70) * 100.0
        ),
        "high_cost_80_pct": float(
            np.mean(values >= 0.80) * 100.0
        ),
    }


def main():
    if len(sys.argv) != 7:
        print(
            "Usage:\n"
            "python pipelines/routing/generate_route_candidates.py "
            "<cost.tif> <start_row> <start_col> "
            "<goal_row> <goal_col> <output_dir>"
        )
        sys.exit(1)

    raster_path = sys.argv[1]

    start = (
        int(sys.argv[2]),
        int(sys.argv[3]),
    )

    goal = (
        int(sys.argv[4]),
        int(sys.argv[5]),
    )

    output_dir = sys.argv[6]

    print("=" * 60)
    print("MARSWALK CANDIDATE ROUTE GENERATOR")
    print("=" * 60)

    print()
    print("INPUT")
    print("-" * 60)
    print("Raster:", raster_path)
    print("Start:", start)
    print("Goal: ", goal)
    print("Output:", output_dir)

    cost, valid, transform, resolution = load_surface(
        raster_path
    )

    print()
    print("SURFACE")
    print("-" * 60)
    print("Width:      ", cost.shape[1])
    print("Height:     ", cost.shape[0])
    print("Resolution: ", resolution, "m")
    print("Valid nodes:", int(valid.sum()))

    start_valid = nearest_valid(valid, *start)

    goal_valid = nearest_valid(valid, *goal)

    if start_valid != start:
        print(
            f"\nStart adjusted: {start} -> {start_valid}"
        )

    if goal_valid != goal:
        print(
            f"Goal adjusted:  {goal} -> {goal_valid}"
        )

    candidates = [
        ("shortest", 0.0),
        ("balanced", 2.0),
        ("safe", 6.0),
        ("very_safe", 12.0),
    ]

    os.makedirs(output_dir, exist_ok=True)

    summary_path = os.path.join(
        output_dir,
        "candidate_routes.csv",
    )

    results = []

    print()
    print("GENERATING CANDIDATES")
    print("-" * 60)

    for name, weight in candidates:
        print(
            f"\n{name.upper()} "
            f"(terrain weight={weight})"
        )

        path = astar(
            cost,
            valid,
            start,
            goal,
            weight,
        )

        if path is None:
            print("  FAILED: no route found.")
            continue

        output_csv = os.path.join(
            output_dir,
            f"route_{name}.csv",
        )

        write_route(
            path,
            transform,
            output_csv,
        )

        metrics = summarize_route(
            path,
            cost,
            resolution,
        )

        metrics["route"] = name
        metrics["terrain_weight"] = weight
        metrics["output"] = output_csv

        results.append(metrics)

        print("  Nodes:             ", metrics["nodes"])
        print(
            "  Distance:          "
            f"{metrics['distance_m']:.3f} m"
        )
        print(
            "  Mean cost:         "
            f"{metrics['mean_cost']:.6f}"
        )
        print(
            "  Maximum cost:      "
            f"{metrics['max_cost']:.6f}"
        )
        print(
            "  P90 cost:          "
            f"{metrics['p90_cost']:.6f}"
        )
        print(
            "  Cost >= 0.70:      "
            f"{metrics['high_cost_70_pct']:.2f}%"
        )
        print("  Output:", output_csv)

    with open(summary_path, "w", newline="") as f:
        fieldnames = [
            "route",
            "terrain_weight",
            "nodes",
            "distance_m",
            "mean_cost",
            "median_cost",
            "max_cost",
            "p90_cost",
            "p95_cost",
            "high_cost_70_pct",
            "high_cost_80_pct",
            "output",
        ]

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for result in results:
            writer.writerow(result)

    print()
    print("=" * 60)
    print("CANDIDATE ROUTE GENERATION COMPLETE")
    print("=" * 60)
    print()
    print("Summary:", summary_path)


if __name__ == "__main__":
    main()
