from pathlib import Path
import csv
import math
import json

ROUTES_DIR = Path(
    "data/derived/jezero/science_routing/routes"
)

OUTPUT_ROUTE = ROUTES_DIR / "complete_science_mission.csv"
OUTPUT_REPORT = ROUTES_DIR / "complete_science_mission.txt"
OUTPUT_JSON = ROUTES_DIR / "complete_science_mission.json"

SEGMENTS = [
    (
        "START_TO_WILDCAT",
        ROUTES_DIR / "route_to_wildcat_ridge.csv",
    ),
    (
        "WILDCAT_TO_SKINNER",
        ROUTES_DIR / "route_wildcat_ridge_to_skinner_ridge.csv",
    ),
]


def read_route(path):
    rows = []

    with open(path, newline="") as f:
        reader = csv.reader(f)

        # First line is the title.
        next(reader)

        # Second line is x,y.
        header = next(reader)

        if [h.strip().lower() for h in header] != ["x", "y"]:
            raise RuntimeError(
                f"Unexpected route header in {path}: {header}"
            )

        for row in reader:
            if len(row) < 2:
                continue

            rows.append(
                (float(row[0]), float(row[1]))
            )

    if len(rows) < 2:
        raise RuntimeError(
            f"Route contains fewer than two points: {path}"
        )

    return rows


def distance(route):
    total = 0.0

    for a, b in zip(route[:-1], route[1:]):
        total += math.hypot(
            b[0] - a[0],
            b[1] - a[1],
        )

    return total


def main():

    print("=" * 70)
    print("MARSWALK COMPLETE SCIENCE MISSION BUILDER")
    print("=" * 70)

    segments = {}

    for name, path in SEGMENTS:

        print()
        print(name)
        print("-" * 70)
        print("Input:", path)

        route = read_route(path)

        print("Points:", len(route))
        print("Start:", route[0])
        print("End:", route[-1])

        d = distance(route)

        print(f"Distance: {d:.3f} m")
        print(f"Distance: {d / 1000:.3f} km")

        segments[name] = {
            "route": route,
            "distance_m": d,
        }

    # ---------------------------------------------------------
    # Join routes.
    #
    # The last point of START_TO_WILDCAT is the first point
    # of WILDCAT_TO_SKINNER, so avoid duplicating it.
    # ---------------------------------------------------------

    first = segments["START_TO_WILDCAT"]["route"]
    second = segments["WILDCAT_TO_SKINNER"]["route"]

    if first[-1] != second[0]:
        raise RuntimeError(
            "Route segments do not connect exactly."
        )

    complete = first + second[1:]

    complete_distance = distance(complete)

    print()
    print("=" * 70)
    print("COMPLETE MISSION")
    print("=" * 70)

    print("Route points:", len(complete))
    print("Mission start:", complete[0])
    print("Wildcat Ridge:", first[-1])
    print("Skinner Ridge:", second[-1])

    print(
        f"Total distance: "
        f"{complete_distance:.3f} m"
    )

    print(
        f"Total distance: "
        f"{complete_distance / 1000:.3f} km"
    )

    # Current MarsWalk conceptual speed.
    speed_mps = 0.05

    travel_hours = (
        complete_distance / speed_mps / 3600
    )

    print(
        f"Conceptual travel time: "
        f"{travel_hours:.2f} h"
    )

    # ---------------------------------------------------------
    # Write complete route
    # ---------------------------------------------------------

    OUTPUT_ROUTE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        OUTPUT_ROUTE,
        "w",
        newline="",
    ) as f:

        writer = csv.writer(f)

        writer.writerow(
            ["MarsWalk Complete Science Mission"]
        )

        writer.writerow(
            ["sequence", "x", "y"]
        )

        for i, (x, y) in enumerate(complete):

            writer.writerow(
                [
                    i,
                    f"{x:.3f}",
                    f"{y:.3f}",
                ]
            )

    # ---------------------------------------------------------
    # JSON
    # ---------------------------------------------------------

    mission = {
        "mission": "MarsWalk Complete Science Mission",
        "sequence": [
            "START",
            "WILDCAT_RIDGE",
            "SKINNER_RIDGE",
        ],
        "segments": {
            "START_TO_WILDCAT": {
                "distance_m": segments[
                    "START_TO_WILDCAT"
                ]["distance_m"],
                "route_file": str(
                    SEGMENTS[0][1]
                ),
            },
            "WILDCAT_TO_SKINNER": {
                "distance_m": segments[
                    "WILDCAT_TO_SKINNER"
                ]["distance_m"],
                "route_file": str(
                    SEGMENTS[1][1]
                ),
            },
        },
        "total_distance_m": complete_distance,
        "total_distance_km": (
            complete_distance / 1000
        ),
        "nominal_speed_m_per_s": speed_mps,
        "conceptual_travel_hours": travel_hours,
        "status": "research_demo",
        "operational_certification": False,
        "nasa_certification": False,
    }

    OUTPUT_JSON.write_text(
        json.dumps(
            mission,
            indent=2,
        )
    )

    # ---------------------------------------------------------
    # Human-readable report
    # ---------------------------------------------------------

    with open(
        OUTPUT_REPORT,
        "w",
    ) as f:

        f.write(
            "MARSWALK COMPLETE SCIENCE MISSION REPORT\n"
        )
        f.write("=" * 70 + "\n\n")

        f.write("MISSION SEQUENCE\n")
        f.write("-" * 70 + "\n")
        f.write(
            "START -> WILDCAT RIDGE -> SKINNER RIDGE\n\n"
        )

        f.write("SEGMENTS\n")
        f.write("-" * 70 + "\n")

        f.write(
            f"Start -> Wildcat Ridge: "
            f"{segments['START_TO_WILDCAT']['distance_m']:.3f} m\n"
        )

        f.write(
            f"Wildcat Ridge -> Skinner Ridge: "
            f"{segments['WILDCAT_TO_SKINNER']['distance_m']:.3f} m\n\n"
        )

        f.write("TOTAL MISSION\n")
        f.write("-" * 70 + "\n")

        f.write(
            f"Distance: "
            f"{complete_distance:.3f} m\n"
        )

        f.write(
            f"Distance: "
            f"{complete_distance / 1000:.3f} km\n"
        )

        f.write(
            f"Conceptual travel time: "
            f"{travel_hours:.2f} h\n\n"
        )

        f.write("MODEL STATUS\n")
        f.write("-" * 70 + "\n")

        f.write(
            "MarsWalk is a research/demo terrain-routing "
            "system. Travel speed, terrain costs, risk "
            "weights, and mission decision parameters "
            "are conceptual engineering assumptions and "
            "are not NASA-certified operational parameters.\n"
        )

    print()
    print("OUTPUT")
    print("-" * 70)
    print("Complete route:", OUTPUT_ROUTE)
    print("JSON:", OUTPUT_JSON)
    print("Report:", OUTPUT_REPORT)

    print()
    print("=" * 70)
    print("COMPLETE SCIENCE MISSION BUILD COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
