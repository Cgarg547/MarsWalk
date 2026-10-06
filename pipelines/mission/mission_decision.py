#!/usr/bin/env python3

import csv
import math
import sys
from pathlib import Path

import numpy as np
import rasterio


# ============================================================
# MARSWALK FINAL MISSION DECISION ENGINE
# ============================================================

ROUTES = {
    "shortest": {
        "file": "route_shortest.csv",
        "strategy": "SHORTEST",
    },
    "balanced": {
        "file": "route_balanced.csv",
        "strategy": "BALANCED",
    },
    "safe": {
        "file": "route_safe.csv",
        "strategy": "SAFE",
    },
    "very_safe": {
        "file": "route_very_safe.csv",
        "strategy": "VERY_SAFE",
    },
}


def load_route(path):
    points = []

    with open(path, "r", newline="") as f:
        reader = csv.reader(f)

        for row in reader:
            if not row:
                continue

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

    if len(points) < 2:
        raise RuntimeError(f"Invalid route: {path}")

    return points


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


def sample_route(points, src, raster):
    costs = []
    invalid = 0

    for x, y in points:

        row, col = rasterio.transform.rowcol(
            src.transform,
            x,
            y,
        )

        row = int(row)
        col = int(col)

        if (
            row < 0
            or row >= src.height
            or col < 0
            or col >= src.width
        ):
            invalid += 1
            continue

        value = float(raster[row, col])

        if not np.isfinite(value):
            invalid += 1
            continue

        if src.nodata is not None and value == src.nodata:
            invalid += 1
            continue

        costs.append(value)

    return np.asarray(costs), invalid


def calculate_metrics(points, costs):

    distance = route_distance(points)

    mean_cost = float(np.mean(costs))
    median_cost = float(np.median(costs))
    p90 = float(np.percentile(costs, 90))
    p95 = float(np.percentile(costs, 95))
    maximum = float(np.max(costs))

    exposure_50 = float(
        np.mean(costs >= 0.50) * 100.0
    )

    exposure_70 = float(
        np.mean(costs >= 0.70) * 100.0
    )

    exposure_85 = float(
        np.mean(costs >= 0.85) * 100.0
    )

    # Conceptual travel-time estimate.
    # This is a demonstration assumption, not a
    # flight-qualified rover mobility model.
    speed_mps = 0.05

    travel_hours = (
        distance / speed_mps / 3600.0
    )

    # Mission risk score.
    risk_score = (
        0.40 * mean_cost
        + 0.30 * p90
        + 0.20 * (exposure_50 / 100.0)
        + 0.10 * maximum
    )

    risk_score = max(
        0.0,
        min(1.0, risk_score),
    )

    return {
        "distance": distance,
        "mean": mean_cost,
        "median": median_cost,
        "p90": p90,
        "p95": p95,
        "maximum": maximum,
        "exposure_50": exposure_50,
        "exposure_70": exposure_70,
        "exposure_85": exposure_85,
        "travel_hours": travel_hours,
        "risk_score": risk_score,
    }


def decision_score(metrics):

    """
    Final mission-decision score.

    Lower is better.

    The score balances:
        - terrain risk
        - high-cost exposure
        - travel distance

    The distance term is deliberately limited so that
    a very short but dangerous route does not automatically win.
    """

    distance_km = metrics["distance"] / 1000.0

    distance_penalty = min(
        distance_km / 2.0,
        1.0,
    )

    score = (
        0.70 * metrics["risk_score"]
        + 0.20 * (metrics["exposure_70"] / 100.0)
        + 0.10 * distance_penalty
    )

    return score


def main():

    if len(sys.argv) != 3:

        print(
            "Usage:\n"
            "python pipelines/mission/mission_decision.py "
            "<routing_directory> <output_report>"
        )

        sys.exit(1)

    routing_dir = Path(sys.argv[1])
    output_report = Path(sys.argv[2])

    terrain_raster = (
        routing_dir / "terrain_cost_10m.tif"
    )

    candidates_dir = (
        routing_dir / "candidates"
    )

    print("=" * 60)
    print("MARSWALK FINAL MISSION DECISION")
    print("=" * 60)

    print()
    print("INPUT")
    print("-" * 60)
    print(f"Terrain cost: {terrain_raster}")
    print(f"Candidates:   {candidates_dir}")
    print(f"Output:       {output_report}")

    if not terrain_raster.exists():
        raise RuntimeError(
            f"Terrain raster not found: {terrain_raster}"
        )

    if not candidates_dir.exists():
        raise RuntimeError(
            f"Candidate directory not found: {candidates_dir}"
        )

    results = {}

    with rasterio.open(terrain_raster) as src:

        raster = src.read(1)

        print()
        print("TERRAIN SURFACE")
        print("-" * 60)
        print(
            f"Dimensions:  {src.width} × {src.height}"
        )
        print(
            f"Resolution:  {src.res}"
        )
        print(
            f"CRS:         {src.crs}"
        )

        for key, config in ROUTES.items():

            route_path = (
                candidates_dir
                / config["file"]
            )

            if not route_path.exists():
                print(
                    f"WARNING: Missing {route_path}"
                )
                continue

            points = load_route(route_path)

            costs, invalid = sample_route(
                points,
                src,
                raster,
            )

            if len(costs) == 0:
                print(
                    f"WARNING: No valid terrain data "
                    f"for {config['strategy']}"
                )
                continue

            metrics = calculate_metrics(
                points,
                costs,
            )

            metrics["invalid"] = invalid
            metrics["decision_score"] = (
                decision_score(metrics)
            )
            metrics["points"] = len(points)

            results[key] = {
                "strategy": config["strategy"],
                "path": route_path,
                **metrics,
            }

    if len(results) == 0:
        raise RuntimeError(
            "No candidate routes could be evaluated."
        )

    # --------------------------------------------------------
    # SORT
    # --------------------------------------------------------

    ranked = sorted(
        results.values(),
        key=lambda r: r["decision_score"],
    )

    recommended = ranked[0]

    # --------------------------------------------------------
    # PRINT COMPARISON
    # --------------------------------------------------------

    print()
    print("ROUTE DECISION MATRIX")
    print("-" * 60)

    print(
        f"{'ROUTE':<12}"
        f"{'DISTANCE':>12}"
        f"{'MEAN':>10}"
        f"{'P90':>10}"
        f"{'≥0.70':>10}"
        f"{'RISK':>10}"
        f"{'SCORE':>10}"
    )

    for result in ranked:

        print(
            f"{result['strategy']:<12}"
            f"{result['distance']:>12.1f}"
            f"{result['mean']:>10.4f}"
            f"{result['p90']:>10.4f}"
            f"{result['exposure_70']:>9.2f}%"
            f"{result['risk_score']:>10.4f}"
            f"{result['decision_score']:>10.4f}"
        )

    # --------------------------------------------------------
    # TRADEOFFS
    # --------------------------------------------------------

    shortest_distance = min(
        r["distance"]
        for r in results.values()
    )

    extra_distance = (
        recommended["distance"]
        - shortest_distance
    )

    extra_time = (
        recommended["travel_hours"]
        - min(
            r["travel_hours"]
            for r in results.values()
        )
    )

    # --------------------------------------------------------
    # DECISION
    # --------------------------------------------------------

    print()
    print("FINAL MISSION RECOMMENDATION")
    print("-" * 60)

    print(
        f"Recommended route: {recommended['strategy']}"
    )

    print(
        f"Distance:           "
        f"{recommended['distance']:.2f} m"
    )

    print(
        f"Mean terrain cost:  "
        f"{recommended['mean']:.4f}"
    )

    print(
        f"P90 terrain cost:   "
        f"{recommended['p90']:.4f}"
    )

    print(
        f"≥0.70 exposure:     "
        f"{recommended['exposure_70']:.2f}%"
    )

    print(
        f"Risk score:         "
        f"{recommended['risk_score']:.4f}"
    )

    print(
        f"Decision score:     "
        f"{recommended['decision_score']:.4f}"
    )

    print(
        f"Travel estimate:    "
        f"{recommended['travel_hours']:.2f} h"
    )

    # --------------------------------------------------------
    # REASONING
    # --------------------------------------------------------

    reasons = []

    reasons.append(
        "Lowest combined mission-decision score "
        "among the evaluated candidate routes."
    )

    if recommended["mean"] < 0.30:
        reasons.append(
            "Mean terrain cost remains below 0.30."
        )

    if recommended["exposure_70"] < 5.0:
        reasons.append(
            "Very-high-cost terrain exposure remains "
            "below 5%."
        )

    if recommended["invalid"] == 0:
        reasons.append(
            "Every route point intersects valid terrain data."
        )

    print()
    print("DECISION RATIONALE")
    print("-" * 60)

    for reason in reasons:
        print(f"- {reason}")

    # --------------------------------------------------------
    # REPORT
    # --------------------------------------------------------

    output_report.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(output_report, "w") as f:

        f.write(
            "MARSWALK FINAL MISSION DECISION REPORT\n"
        )
        f.write("=" * 70 + "\n\n")

        f.write("RECOMMENDED ROUTE\n")
        f.write("-" * 70 + "\n")

        f.write(
            f"Strategy: {recommended['strategy']}\n"
        )
        f.write(
            f"Distance: "
            f"{recommended['distance']:.3f} m\n"
        )
        f.write(
            f"Mean terrain cost: "
            f"{recommended['mean']:.6f}\n"
        )
        f.write(
            f"P90 terrain cost: "
            f"{recommended['p90']:.6f}\n"
        )
        f.write(
            f"P95 terrain cost: "
            f"{recommended['p95']:.6f}\n"
        )
        f.write(
            f"Maximum terrain cost: "
            f"{recommended['maximum']:.6f}\n"
        )
        f.write(
            f"Cost >= 0.70 exposure: "
            f"{recommended['exposure_70']:.2f}%\n"
        )
        f.write(
            f"Risk score: "
            f"{recommended['risk_score']:.6f}\n"
        )
        f.write(
            f"Decision score: "
            f"{recommended['decision_score']:.6f}\n"
        )
        f.write(
            f"Estimated travel time: "
            f"{recommended['travel_hours']:.2f} h\n\n"
        )

        f.write("ROUTE COMPARISON\n")
        f.write("-" * 70 + "\n")

        for result in ranked:

            f.write(
                f"{result['strategy']:<12} "
                f"distance={result['distance']:.3f} m "
                f"mean={result['mean']:.4f} "
                f"p90={result['p90']:.4f} "
                f"exposure70={result['exposure_70']:.2f}% "
                f"risk={result['risk_score']:.4f} "
                f"score={result['decision_score']:.4f}\n"
            )

        f.write("\n")

        f.write("DECISION RATIONALE\n")
        f.write("-" * 70 + "\n")

        for reason in reasons:
            f.write(f"- {reason}\n")

        f.write("\n")

        f.write("TRADEOFF\n")
        f.write("-" * 70 + "\n")
        f.write(
            f"Additional distance over shortest: "
            f"{extra_distance:.3f} m\n"
        )
        f.write(
            f"Additional estimated travel time: "
            f"{extra_time:.2f} h\n"
        )

        f.write("\n")

        f.write("MODEL LIMITATION\n")
        f.write("-" * 70 + "\n")
        f.write(
            "MarsWalk is a research/demo terrain-routing "
            "system. The decision score, terrain thresholds, "
            "and travel-speed assumption are conceptual and "
            "are not NASA-certified mobility, safety, or "
            "mission-planning models.\n"
        )

    print()
    print("=" * 60)
    print("FINAL MISSION DECISION COMPLETE")
    print("=" * 60)

    print()
    print(f"Report: {output_report}")


if __name__ == "__main__":
    main()