import csv
import math
from pathlib import Path


BASE = Path("data/derived/jezero/science_routing")

ROUTE_SUMMARY = (
    BASE / "routes" / "science_target_routes.csv"
)

OUTPUT = (
    BASE / "science_mission_plan.txt"
)

ROVER_SPEED_MPS = 0.05

# Prototype science priorities.
# These are engineering/demo assumptions, not NASA values.
SCIENCE_PRIORITY = {
    "wildcat_ridge": 1.0,
    "skinner_ridge": 0.9,
}


def load_routes():

    routes = {}

    with open(ROUTE_SUMMARY, newline="") as f:

        reader = csv.DictReader(f)

        for row in reader:

            target = row["target"]

            routes[target] = {
                "distance_m": float(
                    row["distance_m"]
                ),
                "mean_cost": float(
                    row["mean_cost"]
                ),
                "p90_cost": float(
                    row["p90_cost"]
                ),
                "p95_cost": float(
                    row["p95_cost"]
                ),
                "maximum_cost": float(
                    row["maximum_cost"]
                ),
                "cost_ge_070_pct": float(
                    row["cost_ge_070_pct"]
                ),
                "cost_ge_080_pct": float(
                    row["cost_ge_080_pct"]
                ),
                "cost_ge_090_pct": float(
                    row["cost_ge_090_pct"]
                ),
                "route_file": row["route_file"],
            }

    return routes


def travel_hours(distance_m):

    return distance_m / ROVER_SPEED_MPS / 3600.0


def route_risk(metrics):

    """
    Prototype terrain-risk score.

    Higher values indicate greater terrain exposure.
    """

    return (
        0.40 * metrics["mean_cost"]
        + 0.25 * metrics["p90_cost"]
        + 0.20 * (
            metrics["cost_ge_070_pct"] / 100.0
        )
        + 0.15 * (
            metrics["maximum_cost"]
        )
    )


def target_score(metrics, target):

    """
    Lower is better.

    Combines:
      - normalized distance
      - terrain risk
      - high-cost exposure
      - science priority

    This is a prototype decision model.
    """

    distance_component = (
        metrics["distance_m"] / 5000.0
    )

    risk_component = route_risk(metrics)

    exposure_component = (
        metrics["cost_ge_070_pct"] / 100.0
    )

    science_priority = SCIENCE_PRIORITY.get(
        target,
        0.5,
    )

    science_bonus = 1.0 - science_priority

    return (
        0.35 * distance_component
        + 0.45 * risk_component
        + 0.10 * exposure_component
        + 0.10 * science_bonus
    )


def evaluate_sequence(routes, first, second):

    first_metrics = routes[first]
    second_metrics = routes[second]

    total_distance = (
        first_metrics["distance_m"]
        + second_metrics["distance_m"]
    )

    total_hours = (
        travel_hours(
            first_metrics["distance_m"]
        )
        +
        travel_hours(
            second_metrics["distance_m"]
        )
    )

    average_mean_cost = (
        first_metrics["mean_cost"]
        +
        second_metrics["mean_cost"]
    ) / 2.0

    average_p90 = (
        first_metrics["p90_cost"]
        +
        second_metrics["p90_cost"]
    ) / 2.0

    average_risk = (
        route_risk(first_metrics)
        +
        route_risk(second_metrics)
    ) / 2.0

    science_value = (
        SCIENCE_PRIORITY[first]
        +
        SCIENCE_PRIORITY[second]
    )

    sequence_score = (
        0.35 * (total_distance / 10000.0)
        + 0.45 * average_risk
        + 0.10 * average_p90
        + 0.10 * (2.0 - science_value)
    )

    return {
        "first": first,
        "second": second,
        "distance_m": total_distance,
        "travel_hours": total_hours,
        "mean_cost": average_mean_cost,
        "p90_cost": average_p90,
        "risk": average_risk,
        "science_value": science_value,
        "score": sequence_score,
    }


def main():

    print("=" * 70)
    print("MARSWALK SCIENCE MISSION PLANNER")
    print("=" * 70)

    routes = load_routes()

    if len(routes) < 2:
        raise RuntimeError(
            "At least two science targets are required."
        )

    print()
    print("SCIENCE TARGETS")
    print("-" * 70)

    for target, metrics in routes.items():

        print()
        print(target.upper())

        print(
            f"Distance:       "
            f"{metrics['distance_m']:.3f} m"
        )

        print(
            f"Mean cost:      "
            f"{metrics['mean_cost']:.6f}"
        )

        print(
            f"P90 cost:       "
            f"{metrics['p90_cost']:.6f}"
        )

        print(
            f"≥0.70 exposure: "
            f"{metrics['cost_ge_070_pct']:.3f}%"
        )

        print(
            f"Risk score:     "
            f"{route_risk(metrics):.6f}"
        )

        print(
            f"Science value:  "
            f"{SCIENCE_PRIORITY.get(target, 0.5):.2f}"
        )

    targets = list(routes.keys())

    first = targets[0]
    second = targets[1]

    sequence_a = evaluate_sequence(
        routes,
        first,
        second,
    )

    sequence_b = evaluate_sequence(
        routes,
        second,
        first,
    )

    sequences = [
        sequence_a,
        sequence_b,
    ]

    recommended = min(
        sequences,
        key=lambda x: x["score"],
    )

    print()
    print("MISSION SEQUENCES")
    print("-" * 70)

    for i, sequence in enumerate(
        sequences,
        start=1,
    ):

        print()
        print(
            f"{i}. "
            f"{sequence['first']} "
            f"→ "
            f"{sequence['second']}"
        )

        print(
            f"   Distance:    "
            f"{sequence['distance_m']:.3f} m"
        )

        print(
            f"   Travel time: "
            f"{sequence['travel_hours']:.2f} h"
        )

        print(
            f"   Mean cost:   "
            f"{sequence['mean_cost']:.6f}"
        )

        print(
            f"   P90 cost:    "
            f"{sequence['p90_cost']:.6f}"
        )

        print(
            f"   Risk:        "
            f"{sequence['risk']:.6f}"
        )

        print(
            f"   Score:       "
            f"{sequence['score']:.6f}"
        )

    print()
    print("RECOMMENDED MISSION")
    print("-" * 70)

    print(
        f"Sequence: "
        f"{recommended['first']} "
        f"→ "
        f"{recommended['second']}"
    )

    print(
        f"Distance: "
        f"{recommended['distance_m']:.3f} m"
    )

    print(
        f"Travel time: "
        f"{recommended['travel_hours']:.2f} h"
    )

    print(
        f"Mean terrain cost: "
        f"{recommended['mean_cost']:.6f}"
    )

    print(
        f"P90 terrain cost: "
        f"{recommended['p90_cost']:.6f}"
    )

    print(
        f"Risk score: "
        f"{recommended['risk']:.6f}"
    )

    print(
        f"Decision score: "
        f"{recommended['score']:.6f}"
    )

    # ---------------------------------------------------------
    # REPORT
    # ---------------------------------------------------------

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(OUTPUT, "w") as f:

        f.write(
            "MARSWALK SCIENCE MISSION PLAN\n"
        )

        f.write("=" * 70 + "\n\n")

        f.write("MISSION OBJECTIVE\n")
        f.write("-" * 70 + "\n")

        f.write(
            "Navigate from the rover starting location "
            "to registered science targets using "
            "terrain-aware routing.\n\n"
        )

        f.write(
            "ROVER SPEED ASSUMPTION\n"
        )

        f.write("-" * 70 + "\n")

        f.write(
            f"{ROVER_SPEED_MPS:.3f} m/s\n\n"
        )

        f.write("TARGETS\n")
        f.write("-" * 70 + "\n")

        for target, metrics in routes.items():

            f.write(
                f"{target}\n"
            )

            f.write(
                f"  Distance: "
                f"{metrics['distance_m']:.3f} m\n"
            )

            f.write(
                f"  Mean cost: "
                f"{metrics['mean_cost']:.6f}\n"
            )

            f.write(
                f"  P90 cost: "
                f"{metrics['p90_cost']:.6f}\n"
            )

            f.write(
                f"  ≥0.70 exposure: "
                f"{metrics['cost_ge_070_pct']:.3f}%\n"
            )

            f.write(
                f"  Risk score: "
                f"{route_risk(metrics):.6f}\n\n"
            )

        f.write("SEQUENCE COMPARISON\n")
        f.write("-" * 70 + "\n")

        for sequence in sequences:

            f.write(
                f"{sequence['first']} "
                f"-> "
                f"{sequence['second']}\n"
            )

            f.write(
                f"  Distance: "
                f"{sequence['distance_m']:.3f} m\n"
            )

            f.write(
                f"  Travel time: "
                f"{sequence['travel_hours']:.2f} h\n"
            )

            f.write(
                f"  Mean cost: "
                f"{sequence['mean_cost']:.6f}\n"
            )

            f.write(
                f"  P90 cost: "
                f"{sequence['p90_cost']:.6f}\n"
            )

            f.write(
                f"  Risk score: "
                f"{sequence['risk']:.6f}\n"
            )

            f.write(
                f"  Decision score: "
                f"{sequence['score']:.6f}\n\n"
            )

        f.write("RECOMMENDATION\n")
        f.write("-" * 70 + "\n")

        f.write(
            f"Recommended sequence: "
            f"{recommended['first']} "
            f"-> "
            f"{recommended['second']}\n"
        )

        f.write(
            f"Distance: "
            f"{recommended['distance_m']:.3f} m\n"
        )

        f.write(
            f"Travel time: "
            f"{recommended['travel_hours']:.2f} h\n"
        )

        f.write(
            f"Mission score: "
            f"{recommended['score']:.6f}\n\n"
        )

        f.write("MODEL STATUS\n")
        f.write("-" * 70 + "\n")

        f.write(
            "This is a research/demo mission-planning "
            "model. Science priorities, rover speed, "
            "risk weights, and decision thresholds are "
            "prototype assumptions and are not "
            "NASA-certified operational parameters.\n"
        )

    print()
    print("REPORT")
    print("-" * 70)
    print("Output:", OUTPUT)

    print()
    print("=" * 70)
    print("SCIENCE MISSION PLANNER COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
