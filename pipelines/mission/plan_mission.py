#!/usr/bin/env python3

"""
MarsWalk Mission Planner

Mission-level orchestration for the terrain-aware rover route planner.

This first version:
    1. Validates the routing surface.
    2. Validates start / goal nodes.
    3. Runs the existing candidate-route generator.
    4. Compares candidate routes.
    5. Selects the recommended route.
    6. Produces a mission report.

Important:
    Rover performance parameters in this file are configurable assumptions.
    They are NOT NASA-certified engineering values.
"""

from __future__ import annotations

import csv
import math
import os
import sys
from pathlib import Path

import numpy as np
import rasterio


# ============================================================
# CONFIGURATION
# ============================================================

ROVER_SPEED_MPS = 0.05

MAX_ACCEPTABLE_COST = 0.80
HIGH_COST_THRESHOLD = 0.70

# These are intentionally configurable assumptions.
# They should not be presented as validated rover specifications.
MAX_MISSION_DISTANCE_M = 5000.0


# ============================================================
# OUTPUT
# ============================================================

def print_header(title: str) -> None:
    print("=" * 60)
    print(title)
    print("=" * 60)


def print_section(title: str) -> None:
    print()
    print(title)
    print("-" * 60)


# ============================================================
# RASTER VALIDATION
# ============================================================

def load_routing_surface(path: str):
    with rasterio.open(path) as src:
        data = src.read(1)
        profile = src.profile.copy()
        transform = src.transform
        crs = src.crs
        nodata = src.nodata

    valid = np.isfinite(data)

    if nodata is not None:
        valid &= data != nodata

    return data, valid, profile, transform, crs, nodata


def validate_node(
    data: np.ndarray,
    valid: np.ndarray,
    row: int,
    col: int,
    name: str,
) -> None:

    height, width = data.shape

    if not (0 <= row < height and 0 <= col < width):
        raise RuntimeError(
            f"{name} node ({row}, {col}) is outside the routing raster."
        )

    if not valid[row, col]:
        raise RuntimeError(
            f"{name} node ({row}, {col}) is invalid / NoData."
        )


# ============================================================
# ROUTE LOADING
# ============================================================

def load_route(route_csv: str):
    points = []

    with open(route_csv, "r", newline="") as f:
        reader = csv.reader(f)

        for row in reader:
            if not row:
                continue

            # Skip metadata/header lines.
            if row[0].strip().lower() in {
                "marswalk route",
                "x",
            }:
                continue

            if len(row) < 2:
                continue

            try:
                x = float(row[0])
                y = float(row[1])
            except ValueError:
                continue

            points.append((x, y))

    if len(points) < 2:
        raise RuntimeError(
            f"Unable to load a valid route from {route_csv}"
        )

    return points


# ============================================================
# ROUTE METRICS
# ============================================================

def route_distance(points):
    total = 0.0

    for i in range(1, len(points)):
        x1, y1 = points[i - 1]
        x2, y2 = points[i]

        total += math.hypot(
            x2 - x1,
            y2 - y1,
        )

    return total


def coordinate_to_row_col(transform, x, y):
    col, row = ~transform * (x, y)

    return int(round(row)), int(round(col))


def route_costs(points, data, transform, valid):
    costs = []

    for x, y in points:

        row, col = coordinate_to_row_col(
            transform,
            x,
            y,
        )

        if (
            row < 0
            or row >= data.shape[0]
            or col < 0
            or col >= data.shape[1]
        ):
            continue

        if not valid[row, col]:
            continue

        costs.append(float(data[row, col]))

    return np.asarray(costs, dtype=np.float64)


# ============================================================
# MISSION ANALYSIS
# ============================================================

def calculate_mission_metrics(
    route_points,
    data,
    transform,
    valid,
):
    distance_m = route_distance(route_points)

    costs = route_costs(
        route_points,
        data,
        transform,
        valid,
    )

    if len(costs) == 0:
        raise RuntimeError(
            "No valid terrain-cost values were found along the route."
        )

    mean_cost = float(np.mean(costs))
    median_cost = float(np.median(costs))
    p90_cost = float(np.percentile(costs, 90))
    maximum_cost = float(np.max(costs))

    high_cost_fraction = float(
        np.mean(costs >= HIGH_COST_THRESHOLD)
    )

    critical_cost_fraction = float(
        np.mean(costs > MAX_ACCEPTABLE_COST)
    )

    estimated_time_seconds = distance_m / ROVER_SPEED_MPS

    estimated_time_hours = estimated_time_seconds / 3600.0

    return {
        "distance_m": distance_m,
        "distance_km": distance_m / 1000.0,
        "mean_cost": mean_cost,
        "median_cost": median_cost,
        "p90_cost": p90_cost,
        "maximum_cost": maximum_cost,
        "high_cost_fraction": high_cost_fraction,
        "critical_cost_fraction": critical_cost_fraction,
        "estimated_time_seconds": estimated_time_seconds,
        "estimated_time_hours": estimated_time_hours,
        "route_points": len(route_points),
    }


# ============================================================
# ROUTE DISCOVERY
# ============================================================

def find_candidate_routes(candidate_directory):
    candidate_directory = Path(candidate_directory)

    routes = {}

    for path in candidate_directory.glob("route_*.csv"):

        name = path.stem.replace("route_", "")

        routes[name] = path

    if not routes:
        raise RuntimeError(
            f"No candidate routes found in {candidate_directory}"
        )

    return routes


# ============================================================
# ROUTE SCORING
# ============================================================

def mission_score(metrics):
    """
    Simple mission-level score.

    Lower is better.

    This is deliberately transparent rather than pretending to be
    a scientifically validated rover utility function.
    """

    distance_component = (
        metrics["distance_m"] / MAX_MISSION_DISTANCE_M
    )

    terrain_component = metrics["mean_cost"]

    exposure_component = metrics["high_cost_fraction"]

    critical_component = metrics["critical_cost_fraction"]

    return (
        0.35 * distance_component
        + 0.35 * terrain_component
        + 0.20 * exposure_component
        + 0.10 * critical_component
    )


# ============================================================
# REPORT
# ============================================================

def write_report(
    output_path,
    routing_surface,
    start,
    goal,
    routes,
    recommended,
):

    with open(output_path, "w") as f:

        f.write(
            "MARSWALK MISSION PLANNING REPORT\n"
        )

        f.write("=" * 70 + "\n\n")

        f.write("MISSION\n")
        f.write("-" * 70 + "\n")

        f.write(
            f"Routing surface: {routing_surface}\n"
        )

        f.write(
            f"Start node:      {start[0]}, {start[1]}\n"
        )

        f.write(
            f"Goal node:       {goal[0]}, {goal[1]}\n"
        )

        f.write(
            f"Rover speed assumption: {ROVER_SPEED_MPS:.3f} m/s\n"
        )

        f.write(
            f"High-cost threshold: {HIGH_COST_THRESHOLD:.2f}\n"
        )

        f.write(
            f"Maximum accepted cost: {MAX_ACCEPTABLE_COST:.2f}\n"
        )

        f.write("\n")

        f.write("ROUTE OPTIONS\n")
        f.write("-" * 70 + "\n")

        for name, metrics in routes.items():

            f.write(
                f"{name.upper()}\n"
            )

            f.write(
                f"  Distance:             "
                f"{metrics['distance_m']:.2f} m\n"
            )

            f.write(
                f"  Mean terrain cost:    "
                f"{metrics['mean_cost']:.4f}\n"
            )

            f.write(
                f"  P90 terrain cost:     "
                f"{metrics['p90_cost']:.4f}\n"
            )

            f.write(
                f"  Maximum terrain cost: "
                f"{metrics['maximum_cost']:.4f}\n"
            )

            f.write(
                f"  High-cost exposure:   "
                f"{metrics['high_cost_fraction'] * 100:.2f}%\n"
            )

            f.write(
                f"  Critical exposure:    "
                f"{metrics['critical_cost_fraction'] * 100:.2f}%\n"
            )

            f.write(
                f"  Estimated travel:     "
                f"{metrics['estimated_time_hours']:.2f} h\n"
            )

            f.write(
                f"  Mission score:        "
                f"{metrics['mission_score']:.4f}\n"
            )

            f.write("\n")

        f.write("RECOMMENDATION\n")
        f.write("-" * 70 + "\n")

        f.write(
            f"Recommended strategy: {recommended}\n"
        )

        m = routes[recommended]

        f.write(
            f"Distance:              "
            f"{m['distance_m']:.2f} m\n"
        )

        f.write(
            f"Mean terrain cost:     "
            f"{m['mean_cost']:.4f}\n"
        )

        f.write(
            f"P90 terrain cost:      "
            f"{m['p90_cost']:.4f}\n"
        )

        f.write(
            f"High-cost exposure:    "
            f"{m['high_cost_fraction'] * 100:.2f}%\n"
        )

        f.write(
            f"Estimated travel time: "
            f"{m['estimated_time_hours']:.2f} h\n"
        )

        f.write("\n")

        f.write(
            "NOTE: Rover speed and mission scoring are configurable "
            "engineering assumptions for this prototype and are not "
            "NASA-certified operational parameters.\n"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    if len(sys.argv) != 7:

        print(
            "\nUsage:\n"
            "\n"
            "python pipelines/mission/plan_mission.py "
            "<terrain_cost> "
            "<start_row> "
            "<start_col> "
            "<goal_row> "
            "<goal_col> "
            "<output_directory>\n"
        )

        sys.exit(1)

    terrain_cost = sys.argv[1]

    start_row = int(sys.argv[2])
    start_col = int(sys.argv[3])

    goal_row = int(sys.argv[4])
    goal_col = int(sys.argv[5])

    output_directory = Path(sys.argv[6])

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    print_header(
        "MARSWALK MISSION PLANNER"
    )

    print_section("MISSION INPUT")

    print(
        f"Terrain cost: {terrain_cost}"
    )

    print(
        f"Start:         ({start_row}, {start_col})"
    )

    print(
        f"Goal:          ({goal_row}, {goal_col})"
    )

    print(
        f"Output:        {output_directory}"
    )

    # --------------------------------------------------------
    # Load raster
    # --------------------------------------------------------

    data, valid, profile, transform, crs, nodata = (
        load_routing_surface(terrain_cost)
    )

    print_section("ROUTING SURFACE")

    print(
        f"Dimensions:    {data.shape[1]} × {data.shape[0]}"
    )

    print(
        f"Resolution:    "
        f"{profile['transform'].a:.1f} × "
        f"{abs(profile['transform'].e):.1f} m"
    )

    print(
        f"CRS:           {crs}"
    )

    print(
        f"Valid nodes:   {int(valid.sum())}"
    )

    # --------------------------------------------------------
    # Validate mission nodes
    # --------------------------------------------------------

    print_section("NODE VALIDATION")

    validate_node(
        data,
        valid,
        start_row,
        start_col,
        "START",
    )

    validate_node(
        data,
        valid,
        goal_row,
        goal_col,
        "GOAL",
    )

    print(
        f"START valid:   cost={data[start_row, start_col]:.6f}"
    )

    print(
        f"GOAL valid:     cost={data[goal_row, goal_col]:.6f}"
    )

    # --------------------------------------------------------
    # Candidate routes
    # --------------------------------------------------------

    candidate_directory = (
        output_directory / "candidates"
    )

    # The candidate generator is expected to be run before this
    # planner in this first version.
    candidate_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    print_section("CANDIDATE ROUTES")

    candidate_routes = find_candidate_routes(
        candidate_directory
    )

    print(
        f"Routes discovered: {len(candidate_routes)}"
    )

    route_metrics = {}

    for name, path in sorted(candidate_routes.items()):

        points = load_route(str(path))

        metrics = calculate_mission_metrics(
            points,
            data,
            transform,
            valid,
        )

        metrics["mission_score"] = mission_score(
            metrics
        )

        route_metrics[name] = metrics

        print(
            f"{name.upper():12s} "
            f"{metrics['distance_m']:.2f} m  "
            f"mean={metrics['mean_cost']:.4f}  "
            f"p90={metrics['p90_cost']:.4f}  "
            f"exposure="
            f"{metrics['high_cost_fraction'] * 100:.2f}%  "
            f"score="
            f"{metrics['mission_score']:.4f}"
        )

    # --------------------------------------------------------
    # Select route
    # --------------------------------------------------------

    recommended = min(
        route_metrics,
        key=lambda name: route_metrics[name]["mission_score"],
    )

    print_section("MISSION RECOMMENDATION")

    print(
        f"Recommended route: {recommended.upper()}"
    )

    m = route_metrics[recommended]

    print(
        f"Distance:          {m['distance_m']:.2f} m"
    )

    print(
        f"Mean terrain cost:  {m['mean_cost']:.4f}"
    )

    print(
        f"P90 terrain cost:   {m['p90_cost']:.4f}"
    )

    print(
        f"High-cost exposure: "
        f"{m['high_cost_fraction'] * 100:.2f}%"
    )

    print(
        f"Estimated travel:   "
        f"{m['estimated_time_hours']:.2f} h"
    )

    print(
        f"Mission score:      "
        f"{m['mission_score']:.4f}"
    )

    # --------------------------------------------------------
    # Report
    # --------------------------------------------------------

    report_path = (
        output_directory / "mission_report.txt"
    )

    write_report(
        report_path,
        terrain_cost,
        (start_row, start_col),
        (goal_row, goal_col),
        route_metrics,
        recommended,
    )

    print_section("MISSION OUTPUT")

    print(
        f"Report: {report_path}"
    )

    print()

    print_header(
        "MARSWALK MISSION PLANNING COMPLETE"
    )


if __name__ == "__main__":
    main()