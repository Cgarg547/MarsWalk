from pathlib import Path
import csv
import heapq
import math
import sys

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

# Existing MarsWalk mission start used by the routing workflow.
START = (42, 185)

TARGETS = {
    "wildcat_ridge": (
        3016,
        3000,
    ),
    "skinner_ridge": (
        3000,
        3017,
    ),
}


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


def load_cost_surface(path):

    with rasterio.open(path) as src:

        cost = src.read(
            1
        ).astype(
            np.float64
        )

        transform = src.transform
        nodata = src.nodata
        resolution = float(
            abs(transform.a)
        )

        profile = src.profile.copy()

    valid = np.isfinite(cost)

    if nodata is not None:
        valid &= cost != nodata

    return (
        cost,
        valid,
        transform,
        resolution,
        profile,
    )


def nearest_valid(
    valid,
    row,
    col,
    max_radius=100,
):

    height, width = valid.shape

    if (
        0 <= row < height
        and 0 <= col < width
        and valid[row, col]
    ):
        return row, col

    for radius in range(
        1,
        max_radius + 1,
    ):

        r0 = max(
            0,
            row - radius,
        )

        r1 = min(
            height,
            row + radius + 1,
        )

        c0 = max(
            0,
            col - radius,
        )

        c1 = min(
            width,
            col + radius + 1,
        )

        candidates = []

        for r in range(r0, r1):

            for c in range(c0, c1):

                if not valid[r, c]:
                    continue

                distance = math.hypot(
                    r - row,
                    c - col,
                )

                candidates.append(
                    (
                        distance,
                        r,
                        c,
                    )
                )

        if candidates:

            candidates.sort()

            return (
                candidates[0][1],
                candidates[0][2],
            )

    return None


def heuristic(
    node,
    goal,
    resolution,
):

    r, c = node
    gr, gc = goal

    return (
        math.hypot(
            gr - r,
            gc - c,
        )
        * resolution
    )


def run_astar(
    cost,
    valid,
    start,
    goal,
    resolution,
):

    start = nearest_valid(
        valid,
        *start,
    )

    goal = nearest_valid(
        valid,
        *goal,
    )

    if start is None:
        raise RuntimeError(
            "Unable to find valid start."
        )

    if goal is None:
        raise RuntimeError(
            "Unable to find valid goal."
        )

    open_set = []

    g_score = {
        start: 0.0
    }

    came_from = {}

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

    closed = set()

    expansions = 0

    while open_set:

        (
            _,
            current_g,
            current,
        ) = heapq.heappop(
            open_set
        )

        if current in closed:
            continue

        closed.add(current)

        expansions += 1

        if current == goal:

            path = [
                current
            ]

            while current in came_from:

                current = came_from[
                    current
                ]

                path.append(
                    current
                )

            path.reverse()

            return (
                path,
                expansions,
                start,
                goal,
            )

        r, c = current

        for dr, dc, movement_factor in MOVES:

            nr = r + dr
            nc = c + dc

            if (
                nr < 0
                or nr >= cost.shape[0]
                or nc < 0
                or nc >= cost.shape[1]
            ):
                continue

            if not valid[nr, nc]:
                continue

            neighbour = (
                nr,
                nc,
            )

            terrain_factor = (
                1.0
                +
                2.0
                *
                (
                    float(
                        cost[r, c]
                    )
                    +
                    float(
                        cost[nr, nc]
                    )
                )
                /
                2.0
            )

            movement_cost = (
                movement_factor
                *
                resolution
                *
                terrain_factor
            )

            tentative_g = (
                current_g
                +
                movement_cost
            )

            if (
                tentative_g
                <
                g_score.get(
                    neighbour,
                    float("inf"),
                )
            ):

                came_from[
                    neighbour
                ] = current

                g_score[
                    neighbour
                ] = tentative_g

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

    return (
        None,
        expansions,
        start,
        goal,
    )


def route_distance(
    path,
    resolution,
):

    distance = 0.0

    for (
        r1,
        c1,
    ), (
        r2,
        c2,
    ) in zip(
        path[:-1],
        path[1:],
    ):

        distance += (
            math.hypot(
                r2 - r1,
                c2 - c1,
            )
            * resolution
        )

    return distance


def route_statistics(
    path,
    cost,
):

    values = np.asarray(
        [
            cost[r, c]
            for r, c in path
        ],
        dtype=float,
    )

    return {
        "nodes": len(path),

        "mean_cost": float(
            np.mean(values)
        ),

        "median_cost": float(
            np.median(values)
        ),

        "p90_cost": float(
            np.percentile(
                values,
                90,
            )
        ),

        "p95_cost": float(
            np.percentile(
                values,
                95,
            )
        ),

        "maximum_cost": float(
            np.max(values)
        ),

        "cost_ge_070_pct": float(
            np.mean(
                values >= 0.70
            )
            * 100.0
        ),

        "cost_ge_080_pct": float(
            np.mean(
                values >= 0.80
            )
            * 100.0
        ),

        "cost_ge_090_pct": float(
            np.mean(
                values >= 0.90
            )
            * 100.0
        ),
    }


def write_route(
    path,
    transform,
    output,
):

    output.parent.mkdir(
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
            [
                "MarsWalk Science Route"
            ]
        )

        writer.writerow(
            [
                "x",
                "y",
            ]
        )

        for row, col in path:

            x, y = (
                rasterio.transform.xy(
                    transform,
                    row,
                    col,
                    offset="center",
                )
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
        "MARSWALK SCIENCE TARGET A* ROUTING"
    )
    print("=" * 70)

    print()
    print("INPUT")
    print("-" * 70)
    print(
        "Cost raster:",
        COST_RASTER,
    )

    if not COST_RASTER.exists():

        raise FileNotFoundError(
            f"Missing cost raster: "
            f"{COST_RASTER}"
        )

    cost, valid, transform, resolution, profile = (
        load_cost_surface(
            COST_RASTER
        )
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

    start_valid = nearest_valid(
        valid,
        *START,
    )

    if start_valid != START:

        print(
            "Start adjusted:",
            START,
            "->",
            start_valid,
        )

    print()
    print("START")
    print("-" * 70)
    print(
        "Raster cell:",
        start_valid,
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    summary = []

    for target_id, target in TARGETS.items():

        print()
        print("=" * 70)
        print(
            f"TARGET: {target_id.upper()}"
        )
        print("=" * 70)

        print(
            "Requested target:",
            target,
        )

        result = run_astar(
            cost,
            valid,
            START,
            target,
            resolution,
        )

        (
            path,
            expansions,
            actual_start,
            actual_goal,
        ) = result

        if path is None:

            print(
                "NO ROUTE FOUND"
            )

            continue

        distance = route_distance(
            path,
            resolution,
        )

        stats = route_statistics(
            path,
            cost,
        )

        output = (
            OUTPUT_DIR
            /
            f"route_to_{target_id}.csv"
        )

        write_route(
            path,
            transform,
            output,
        )

        estimated_hours = (
            distance
            /
            0.05
            /
            3600.0
        )

        print()
        print("ROUTE RESULT")
        print("-" * 70)

        print(
            "Actual start:",
            actual_start,
        )

        print(
            "Actual target:",
            actual_goal,
        )

        print(
            "Nodes:",
            stats["nodes"],
        )

        print(
            "A* expansions:",
            expansions,
        )

        print(
            f"Distance: "
            f"{distance:.3f} m"
        )

        print(
            f"Distance: "
            f"{distance / 1000:.3f} km"
        )

        print(
            f"Mean cost: "
            f"{stats['mean_cost']:.6f}"
        )

        print(
            f"Median cost: "
            f"{stats['median_cost']:.6f}"
        )

        print(
            f"P90 cost: "
            f"{stats['p90_cost']:.6f}"
        )

        print(
            f"P95 cost: "
            f"{stats['p95_cost']:.6f}"
        )

        print(
            f"Maximum cost: "
            f"{stats['maximum_cost']:.6f}"
        )

        print(
            f"Cost >= 0.70: "
            f"{stats['cost_ge_070_pct']:.2f}%"
        )

        print(
            f"Cost >= 0.80: "
            f"{stats['cost_ge_080_pct']:.2f}%"
        )

        print(
            f"Cost >= 0.90: "
            f"{stats['cost_ge_090_pct']:.2f}%"
        )

        print(
            f"Conceptual travel time: "
            f"{estimated_hours:.2f} h"
        )

        print(
            "Output:",
            output,
        )

        summary.append(
            {
                "target": target_id,
                "distance_m": distance,
                "nodes": stats["nodes"],
                "mean_cost": stats["mean_cost"],
                "median_cost": stats["median_cost"],
                "p90_cost": stats["p90_cost"],
                "p95_cost": stats["p95_cost"],
                "maximum_cost": stats["maximum_cost"],
                "cost_ge_070_pct": stats[
                    "cost_ge_070_pct"
                ],
                "cost_ge_080_pct": stats[
                    "cost_ge_080_pct"
                ],
                "cost_ge_090_pct": stats[
                    "cost_ge_090_pct"
                ],
                "estimated_travel_hours": estimated_hours,
                "route_file": str(output),
            }
        )

    summary_file = (
        OUTPUT_DIR
        /
        "science_target_routes.csv"
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

            writer.writerows(
                summary
            )

    print()
    print("=" * 70)
    print(
        "SCIENCE TARGET ROUTING COMPLETE"
    )
    print("=" * 70)

    print()
    print(
        "Summary:",
        summary_file,
    )


if __name__ == "__main__":
    main()
