import csv
import heapq
import math
import os
from pathlib import Path

import numpy as np
import rasterio


COST_RASTER = Path(
    "data/derived/jezero/science_routing/"
    "science_routing_cost.tif"
)

OUTPUT_DIR = Path(
    "data/derived/jezero/science_routing/"
    "routes"
)

TARGETS = {
    "wildcat_ridge": (3016, 3000),
    "skinner_ridge": (3000, 3017),
}

ROVER_SPEED_MPS = 0.05


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


def load_cost_surface():

    with rasterio.open(COST_RASTER) as src:

        cost = src.read(1).astype(np.float64)

        nodata = src.nodata
        transform = src.transform
        resolution = float(abs(transform.a))

    valid = np.isfinite(cost)

    if nodata is not None:
        valid &= cost != nodata

    return cost, valid, transform, resolution


def heuristic(a, b, resolution):

    r, c = a
    gr, gc = b

    return (
        math.hypot(
            gr - r,
            gc - c,
        )
        * resolution
    )


def astar(
    cost,
    valid,
    start,
    goal,
    resolution,
):

    height, width = cost.shape

    if not valid[start]:
        raise RuntimeError(
            f"Start cell is invalid: {start}"
        )

    if not valid[goal]:
        raise RuntimeError(
            f"Goal cell is invalid: {goal}"
        )

    open_set = []

    heapq.heappush(
        open_set,
        (
            heuristic(
                start,
                goal,
                resolution,
            ),
            0.0,
            start,
        ),
    )

    came_from = {}

    g_score = {
        start: 0.0
    }

    closed = set()

    expansions = 0

    while open_set:

        _, current_g, current = (
            heapq.heappop(open_set)
        )

        if current in closed:
            continue

        closed.add(current)

        expansions += 1

        if current == goal:

            path = [current]

            while current in came_from:

                current = came_from[current]

                path.append(current)

            path.reverse()

            return path, expansions

        r, c = current

        for dr, dc, movement_factor in MOVES:

            nr = r + dr
            nc = c + dc

            if (
                nr < 0
                or nr >= height
                or nc < 0
                or nc >= width
            ):
                continue

            if not valid[nr, nc]:
                continue

            neighbour = (nr, nc)

            # Average terrain cost between cells.
            terrain_factor = (
                1.0
                +
                (
                    float(cost[r, c])
                    +
                    float(cost[nr, nc])
                )
                / 2.0
            )

            step_cost = (
                movement_factor
                * resolution
                * terrain_factor
            )

            tentative_g = (
                current_g
                + step_cost
            )

            if tentative_g < g_score.get(
                neighbour,
                float("inf"),
            ):

                came_from[neighbour] = current

                g_score[neighbour] = tentative_g

                f_score = (
                    tentative_g
                    +
                    heuristic(
                        neighbour,
                        goal,
                        resolution,
                    )
                )

                heapq.heappush(
                    open_set,
                    (
                        f_score,
                        tentative_g,
                        neighbour,
                    ),
                )

    return None, expansions


def route_distance(path, resolution):

    distance = 0.0

    for a, b in zip(
        path[:-1],
        path[1:],
    ):

        distance += (
            math.hypot(
                b[0] - a[0],
                b[1] - a[1],
            )
            * resolution
        )

    return distance


def route_statistics(
    path,
    cost,
    resolution,
):

    values = np.asarray(
        [
            cost[r, c]
            for r, c in path
        ],
        dtype=float,
    )

    distance = route_distance(
        path,
        resolution,
    )

    return {
        "nodes": len(path),
        "distance_m": distance,
        "mean_cost": float(
            np.mean(values)
        ),
        "median_cost": float(
            np.median(values)
        ),
        "p90_cost": float(
            np.percentile(values, 90)
        ),
        "p95_cost": float(
            np.percentile(values, 95)
        ),
        "maximum_cost": float(
            np.max(values)
        ),
        "cost_ge_070_pct": float(
            np.mean(values >= 0.70)
            * 100.0
        ),
        "cost_ge_080_pct": float(
            np.mean(values >= 0.80)
            * 100.0
        ),
        "cost_ge_090_pct": float(
            np.mean(values >= 0.90)
            * 100.0
        ),
        "travel_hours": (
            distance
            / ROVER_SPEED_MPS
            / 3600.0
        ),
    }


def write_route(
    path,
    transform,
    output,
):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        output,
        "w",
        newline="",
    ) as f:

        writer = csv.writer(f)

        writer.writerow(
            ["MarsWalk Science Route"]
        )

        writer.writerow(
            ["x", "y"]
        )

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


def main():

    print("=" * 70)
    print(
        "MARSWALK SCIENCE TARGET-TO-TARGET ROUTING"
    )
    print("=" * 70)

    print()
    print("INPUT")
    print("-" * 70)

    print(
        "Cost raster:",
        COST_RASTER,
    )

    cost, valid, transform, resolution = (
        load_cost_surface()
    )

    print()
    print("ROUTING SURFACE")
    print("-" * 70)

    print(
        "Dimensions:",
        cost.shape[1],
        "×",
        cost.shape[0],
    )

    print(
        "Resolution:",
        resolution,
        "m",
    )

    print(
        "Valid cells:",
        int(valid.sum()),
    )

    wildcat = TARGETS["wildcat_ridge"]
    skinner = TARGETS["skinner_ridge"]

    pairs = [
        (
            "wildcat_ridge_to_skinner_ridge",
            wildcat,
            skinner,
        ),
        (
            "skinner_ridge_to_wildcat_ridge",
            skinner,
            wildcat,
        ),
    ]

    summary = []

    for name, start, goal in pairs:

        print()
        print("=" * 70)
        print(name.upper())
        print("=" * 70)

        print(
            "Start:",
            start,
        )

        print(
            "Goal:",
            goal,
        )

        path, expansions = astar(
            cost,
            valid,
            start,
            goal,
            resolution,
        )

        if path is None:

            print()
            print(
                "FAILED: No route found."
            )

            continue

        metrics = route_statistics(
            path,
            cost,
            resolution,
        )

        output = (
            OUTPUT_DIR
            /
            f"route_{name}.csv"
        )

        write_route(
            path,
            transform,
            output,
        )

        print()
        print("ROUTE RESULT")
        print("-" * 70)

        print(
            "Nodes:",
            metrics["nodes"],
        )

        print(
            "A* expansions:",
            expansions,
        )

        print(
            f"Distance: "
            f"{metrics['distance_m']:.3f} m"
        )

        print(
            f"Distance: "
            f"{metrics['distance_m'] / 1000:.3f} km"
        )

        print(
            f"Mean cost: "
            f"{metrics['mean_cost']:.6f}"
        )

        print(
            f"Median cost: "
            f"{metrics['median_cost']:.6f}"
        )

        print(
            f"P90 cost: "
            f"{metrics['p90_cost']:.6f}"
        )

        print(
            f"P95 cost: "
            f"{metrics['p95_cost']:.6f}"
        )

        print(
            f"Maximum cost: "
            f"{metrics['maximum_cost']:.6f}"
        )

        print(
            f"Cost >= 0.70: "
            f"{metrics['cost_ge_070_pct']:.3f}%"
        )

        print(
            f"Cost >= 0.80: "
            f"{metrics['cost_ge_080_pct']:.3f}%"
        )

        print(
            f"Cost >= 0.90: "
            f"{metrics['cost_ge_090_pct']:.3f}%"
        )

        print(
            f"Conceptual travel time: "
            f"{metrics['travel_hours']:.2f} h"
        )

        print(
            "Output:",
            output,
        )

        summary.append(
            {
                "route": name,
                **metrics,
                "output": str(output),
            }
        )

    summary_file = (
        OUTPUT_DIR
        /
        "target_to_target_routes.csv"
    )

    with open(
        summary_file,
        "w",
        newline="",
    ) as f:

        if summary:

            writer = csv.DictWriter(
                f,
                fieldnames=summary[0].keys(),
            )

            writer.writeheader()
            writer.writerows(summary)

    print()
    print("=" * 70)
    print(
        "TARGET-TO-TARGET ROUTING COMPLETE"
    )
    print("=" * 70)

    print()
    print(
        "Summary:",
        summary_file,
    )


if __name__ == "__main__":
    main()
