#!/usr/bin/env python3

import csv
import math
import sys
from pathlib import Path

import numpy as np
import rasterio


# ============================================================
# MARSWALK MISSION RISK ENGINE
# ============================================================

RISK_CLASSES = [
    ("LOW", 0.00, 0.25),
    ("MODERATE", 0.25, 0.50),
    ("HIGH", 0.50, 0.70),
    ("VERY_HIGH", 0.70, 0.85),
    ("EXTREME", 0.85, float("inf")),
]


def load_route(route_csv):
    """
    Load a MarsWalk route CSV.

    Expected format:

        MarsWalk Route
        x,y
        4581077.000,1103835.000
        ...
    """

    points = []

    with open(route_csv, "r", newline="") as f:
        reader = csv.reader(f)

        for row in reader:
            if not row:
                continue

            # Skip title/header rows.
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
            "Route does not contain at least two valid coordinate points."
        )

    return points


def classify_cost(cost):
    """Return risk class for a terrain-cost value."""

    if cost < 0.25:
        return "LOW"

    if cost < 0.50:
        return "MODERATE"

    if cost < 0.70:
        return "HIGH"

    if cost < 0.85:
        return "VERY_HIGH"

    return "EXTREME"


def calculate_distance(points):
    """Calculate total route distance in projected coordinate units."""

    total = 0.0
    distances = []

    for i in range(1, len(points)):
        x1, y1 = points[i - 1]
        x2, y2 = points[i]

        distance = math.hypot(x2 - x1, y2 - y1)

        distances.append(distance)
        total += distance

    return total, distances


def percentile(values, p):
    """Safe percentile helper."""

    if len(values) == 0:
        return float("nan")

    return float(np.percentile(values, p))


def mission_risk(route_csv, raster_path, output_report):
    print("=" * 60)
    print("MARSWALK MISSION RISK ENGINE")
    print("=" * 60)

    print()
    print("INPUT")
    print("-" * 60)
    print(f"Route:   {route_csv}")
    print(f"Raster:  {raster_path}")
    print(f"Report:  {output_report}")

    # --------------------------------------------------------
    # LOAD ROUTE
    # --------------------------------------------------------

    route = load_route(route_csv)

    print()
    print("ROUTE")
    print("-" * 60)
    print(f"Route points: {len(route)}")

    # --------------------------------------------------------
    # OPEN TERRAIN COST RASTER
    # --------------------------------------------------------

    with rasterio.open(raster_path) as src:

        raster = src.read(1)
        transform = src.transform
        nodata = src.nodata

        print()
        print("TERRAIN COST RASTER")
        print("-" * 60)
        print(f"Dimensions:  {src.width} × {src.height}")
        print(f"Resolution: {src.res}")
        print(f"CRS:        {src.crs}")
        print(f"NoData:     {nodata}")

        # ----------------------------------------------------
        # SAMPLE ROUTE
        # ----------------------------------------------------

        costs = []
        valid_points = []
        invalid_points = []

        for x, y in route:

            row, col = rasterio.transform.rowcol(
                transform,
                x,
                y
            )

            row = int(row)
            col = int(col)

            if (
                row < 0
                or row >= src.height
                or col < 0
                or col >= src.width
            ):
                invalid_points.append((x, y))
                continue

            value = float(raster[row, col])

            if not np.isfinite(value):
                invalid_points.append((x, y))
                continue

            if nodata is not None and value == nodata:
                invalid_points.append((x, y))
                continue

            costs.append(value)
            valid_points.append((x, y))

    if len(costs) == 0:
        raise RuntimeError(
            "No valid terrain-cost values intersect the route."
        )

    costs = np.asarray(costs, dtype=np.float64)

    # --------------------------------------------------------
    # DISTANCE
    # --------------------------------------------------------

    total_distance, segment_distances = calculate_distance(route)

    # --------------------------------------------------------
    # TERRAIN STATISTICS
    # --------------------------------------------------------

    mean_cost = float(np.mean(costs))
    median_cost = float(np.median(costs))
    p90 = percentile(costs, 90)
    p95 = percentile(costs, 95)
    maximum = float(np.max(costs))

    # --------------------------------------------------------
    # RISK CLASSIFICATION
    # --------------------------------------------------------

    class_counts = {
        "LOW": 0,
        "MODERATE": 0,
        "HIGH": 0,
        "VERY_HIGH": 0,
        "EXTREME": 0,
    }

    classifications = []

    for cost in costs:
        risk_class = classify_cost(cost)
        classifications.append(risk_class)
        class_counts[risk_class] += 1

    total_valid = len(costs)

    class_percentages = {}

    for name, count in class_counts.items():
        class_percentages[name] = (
            100.0 * count / total_valid
        )

    # --------------------------------------------------------
    # HIGH-RISK EXPOSURE
    # --------------------------------------------------------

    high_risk_mask = costs >= 0.50

    very_high_mask = costs >= 0.70
    extreme_mask = costs >= 0.85

    high_count = int(np.sum(high_risk_mask))
    very_high_count = int(np.sum(very_high_mask))
    extreme_count = int(np.sum(extreme_mask))

    high_exposure_percent = (
        100.0 * high_count / total_valid
    )

    very_high_exposure_percent = (
        100.0 * very_high_count / total_valid
    )

    extreme_exposure_percent = (
        100.0 * extreme_count / total_valid
    )

    # --------------------------------------------------------
    # CONTINUOUS HIGH-RISK SEGMENTS
    # --------------------------------------------------------

    exposure_segments = []

    current_start = None
    current_distance = 0.0

    for i, is_high in enumerate(high_risk_mask):

        if is_high:

            if current_start is None:
                current_start = i
                current_distance = 0.0

            if i > 0:
                current_distance += segment_distances[i - 1]

        else:

            if current_start is not None:

                exposure_segments.append(
                    (
                        current_start,
                        i - 1,
                        current_distance,
                    )
                )

                current_start = None
                current_distance = 0.0

    # Handle exposure extending to route end.
    if current_start is not None:

        exposure_segments.append(
            (
                current_start,
                len(high_risk_mask) - 1,
                current_distance,
            )
        )

    number_of_exposure_zones = len(exposure_segments)

    if exposure_segments:
        longest_exposure = max(
            segment[2]
            for segment in exposure_segments
        )
    else:
        longest_exposure = 0.0

    # --------------------------------------------------------
    # ESTIMATED TRAVEL TIME
    # --------------------------------------------------------

    # Conservative conceptual rover/crew planning assumption.
    #
    # This is NOT a NASA-certified mobility model.
    #
    # 0.05 m/s ≈ 180 m/hour.

    nominal_speed_mps = 0.05

    travel_seconds = total_distance / nominal_speed_mps
    travel_hours = travel_seconds / 3600.0

    # --------------------------------------------------------
    # MISSION RISK SCORE
    # --------------------------------------------------------

    # Weighted conceptual score:
    #
    # Mean terrain burden
    # P90 terrain burden
    # High-risk exposure
    #
    # The result remains 0-1 for easier interpretation.

    risk_score = (
        0.40 * mean_cost
        + 0.30 * p90
        + 0.20 * (high_exposure_percent / 100.0)
        + 0.10 * (maximum)
    )

    risk_score = max(
        0.0,
        min(1.0, risk_score)
    )

    # --------------------------------------------------------
    # CONFIDENCE
    # --------------------------------------------------------

    if len(invalid_points) == 0:

        data_confidence = "HIGH"

    elif len(invalid_points) <= max(1, int(0.01 * len(route))):

        data_confidence = "MEDIUM"

    else:

        data_confidence = "LOW"

    # --------------------------------------------------------
    # WARNINGS
    # --------------------------------------------------------

    warnings = []

    if high_exposure_percent > 10:
        warnings.append(
            "Significant exposure to high-cost terrain."
        )

    if very_high_exposure_percent > 5:
        warnings.append(
            "Route contains substantial very-high-risk terrain."
        )

    if extreme_exposure_percent > 1:
        warnings.append(
            "Extreme terrain exposure exceeds 1% of sampled route points."
        )

    if longest_exposure > 100:
        warnings.append(
            "Longest continuous high-risk segment exceeds 100 m."
        )

    if maximum >= 0.90:
        warnings.append(
            "Route contains terrain-cost values >= 0.90."
        )

    if invalid_points:
        warnings.append(
            f"{len(invalid_points)} route points "
            "do not intersect valid terrain data."
        )

    if not warnings:
        warnings.append(
            "No major terrain-risk warning thresholds exceeded."
        )

    # --------------------------------------------------------
    # PRINT RESULTS
    # --------------------------------------------------------

    print()
    print("DISTANCE")
    print("-" * 60)
    print(f"Total distance:          {total_distance:.3f} m")
    print(f"Total distance:          {total_distance / 1000:.3f} km")
    print(f"Estimated travel time:   {travel_hours:.2f} h")

    print()
    print("TERRAIN RISK")
    print("-" * 60)
    print(f"Mean cost:               {mean_cost:.6f}")
    print(f"Median cost:             {median_cost:.6f}")
    print(f"P90 cost:                {p90:.6f}")
    print(f"P95 cost:                {p95:.6f}")
    print(f"Maximum cost:            {maximum:.6f}")

    print()
    print("RISK DISTRIBUTION")
    print("-" * 60)

    for name in [
        "LOW",
        "MODERATE",
        "HIGH",
        "VERY_HIGH",
        "EXTREME",
    ]:
        print(
            f"{name:<12} "
            f"{class_counts[name]:>8} points "
            f"{class_percentages[name]:>7.2f}%"
        )

    print()
    print("HIGH-RISK EXPOSURE")
    print("-" * 60)
    print(
        f"Cost >= 0.50:             "
        f"{high_count} points "
        f"({high_exposure_percent:.2f}%)"
    )

    print(
        f"Cost >= 0.70:             "
        f"{very_high_count} points "
        f"({very_high_exposure_percent:.2f}%)"
    )

    print(
        f"Cost >= 0.85:             "
        f"{extreme_count} points "
        f"({extreme_exposure_percent:.2f}%)"
    )

    print(
        f"Exposure zones:           "
        f"{number_of_exposure_zones}"
    )

    print(
        f"Longest high-risk zone:   "
        f"{longest_exposure:.2f} m"
    )

    print()
    print("MISSION SCORE")
    print("-" * 60)
    print(f"Risk score:               {risk_score:.4f}")
    print(f"Data confidence:          {data_confidence}")

    print()
    print("WARNINGS")
    print("-" * 60)

    for warning in warnings:
        print(f"- {warning}")

    # --------------------------------------------------------
    # WRITE REPORT
    # --------------------------------------------------------

    output_path = Path(output_report)
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(output_path, "w") as f:

        f.write(
            "MARSWALK MISSION RISK REPORT\n"
        )
        f.write("=" * 70 + "\n\n")

        f.write("INPUT\n")
        f.write("-" * 70 + "\n")
        f.write(f"Route: {route_csv}\n")
        f.write(f"Terrain raster: {raster_path}\n")
        f.write(f"Route points: {len(route)}\n\n")

        f.write("MISSION\n")
        f.write("-" * 70 + "\n")
        f.write(
            f"Distance: {total_distance:.3f} m\n"
        )
        f.write(
            f"Distance: {total_distance / 1000:.3f} km\n"
        )
        f.write(
            f"Estimated travel time: {travel_hours:.2f} h\n"
        )
        f.write(
            f"Nominal speed assumption: "
            f"{nominal_speed_mps:.3f} m/s\n\n"
        )

        f.write("TERRAIN STATISTICS\n")
        f.write("-" * 70 + "\n")
        f.write(f"Mean: {mean_cost:.6f}\n")
        f.write(f"Median: {median_cost:.6f}\n")
        f.write(f"P90: {p90:.6f}\n")
        f.write(f"P95: {p95:.6f}\n")
        f.write(f"Maximum: {maximum:.6f}\n\n")

        f.write("RISK DISTRIBUTION\n")
        f.write("-" * 70 + "\n")

        for name in [
            "LOW",
            "MODERATE",
            "HIGH",
            "VERY_HIGH",
            "EXTREME",
        ]:
            f.write(
                f"{name}: "
                f"{class_counts[name]} points "
                f"({class_percentages[name]:.2f}%)\n"
            )

        f.write("\n")

        f.write("HIGH-RISK EXPOSURE\n")
        f.write("-" * 70 + "\n")
        f.write(
            f"Cost >= 0.50: "
            f"{high_exposure_percent:.2f}%\n"
        )
        f.write(
            f"Cost >= 0.70: "
            f"{very_high_exposure_percent:.2f}%\n"
        )
        f.write(
            f"Cost >= 0.85: "
            f"{extreme_exposure_percent:.2f}%\n"
        )
        f.write(
            f"Exposure zones: "
            f"{number_of_exposure_zones}\n"
        )
        f.write(
            f"Longest continuous high-risk zone: "
            f"{longest_exposure:.2f} m\n\n"
        )

        f.write("MISSION ASSESSMENT\n")
        f.write("-" * 70 + "\n")
        f.write(
            f"Risk score: {risk_score:.4f}\n"
        )
        f.write(
            f"Data confidence: {data_confidence}\n\n"
        )

        f.write("WARNINGS\n")
        f.write("-" * 70 + "\n")

        for warning in warnings:
            f.write(f"- {warning}\n")

        f.write("\n")

        f.write(
            "IMPORTANT NOTE\n"
        )
        f.write("-" * 70 + "\n")
        f.write(
            "This mission-risk assessment is a MarsWalk "
            "research/demo model based on the supplied terrain-cost "
            "surface. It is not a NASA-certified mobility, safety, "
            "or mission-planning model.\n"
        )

    print()
    print("=" * 60)
    print("MISSION RISK ANALYSIS COMPLETE")
    print("=" * 60)
    print()
    print(f"Report: {output_report}")


# ============================================================
# COMMAND LINE
# ============================================================

if __name__ == "__main__":

    if len(sys.argv) != 4:

        print(
            "Usage:\n"
            "python pipelines/mission/mission_risk.py "
            "<route.csv> <terrain_cost.tif> <report.txt>"
        )

        sys.exit(1)

    mission_risk(
        sys.argv[1],
        sys.argv[2],
        sys.argv[3],
    )