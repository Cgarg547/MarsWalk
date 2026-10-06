import csv
import os
import sys


def load_routes(path):
    routes = []

    with open(path, newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            routes.append({
                "route": row["route"],
                "terrain_weight": float(row["terrain_weight"]),
                "nodes": int(row["nodes"]),
                "distance_m": float(row["distance_m"]),
                "mean_cost": float(row["mean_cost"]),
                "median_cost": float(row["median_cost"]),
                "max_cost": float(row["max_cost"]),
                "p90_cost": float(row["p90_cost"]),
                "p95_cost": float(row["p95_cost"]),
                "high_cost_70_pct": float(row["high_cost_70_pct"]),
                "high_cost_80_pct": float(row["high_cost_80_pct"]),
                "output": row["output"],
            })

    return routes


def normalize(value, minimum, maximum):
    if maximum == minimum:
        return 0.0

    return (value - minimum) / (maximum - minimum)


def calculate_scores(routes):
    distances = [r["distance_m"] for r in routes]
    mean_costs = [r["mean_cost"] for r in routes]
    p90_costs = [r["p90_cost"] for r in routes]
    exposure = [r["high_cost_70_pct"] for r in routes]

    d_min, d_max = min(distances), max(distances)
    c_min, c_max = min(mean_costs), max(mean_costs)
    p_min, p_max = min(p90_costs), max(p90_costs)
    e_min, e_max = min(exposure), max(exposure)

    for route in routes:
        distance_score = normalize(
            route["distance_m"],
            d_min,
            d_max,
        )

        mean_cost_score = normalize(
            route["mean_cost"],
            c_min,
            c_max,
        )

        p90_score = normalize(
            route["p90_cost"],
            p_min,
            p_max,
        )

        exposure_score = normalize(
            route["high_cost_70_pct"],
            e_min,
            e_max,
        )

        # Lower is better.
        route["overall_score"] = (
            0.30 * distance_score
            + 0.30 * mean_cost_score
            + 0.20 * p90_score
            + 0.20 * exposure_score
        )

        route["distance_vs_shortest_pct"] = (
            (
                route["distance_m"] / d_min
            ) - 1.0
        ) * 100.0


def find_dominated_routes(routes):
    dominated = []

    for candidate in routes:
        for other in routes:
            if candidate is other:
                continue

            no_worse = (
                other["distance_m"] <= candidate["distance_m"]
                and other["mean_cost"] <= candidate["mean_cost"]
                and other["p90_cost"] <= candidate["p90_cost"]
                and other["high_cost_70_pct"]
                <= candidate["high_cost_70_pct"]
            )

            strictly_better = (
                other["distance_m"] < candidate["distance_m"]
                or other["mean_cost"] < candidate["mean_cost"]
                or other["p90_cost"] < candidate["p90_cost"]
                or other["high_cost_70_pct"]
                < candidate["high_cost_70_pct"]
            )

            if no_worse and strictly_better:
                dominated.append(
                    (
                        candidate["route"],
                        other["route"],
                    )
                )
                break

    return dominated


def write_report(routes, dominated, output_path):
    recommended = min(
        routes,
        key=lambda r: r["overall_score"],
    )

    shortest = min(
        routes,
        key=lambda r: r["distance_m"],
    )

    safest = min(
        routes,
        key=lambda r: (
            r["high_cost_70_pct"],
            r["mean_cost"],
            r["distance_m"],
        ),
    )

    with open(output_path, "w") as f:
        f.write("MARSWALK ROUTE COMPARISON REPORT\n")
        f.write("=" * 70 + "\n\n")

        f.write("RECOMMENDED ROUTE\n")
        f.write("-" * 70 + "\n")
        f.write(
            f"Strategy: {recommended['route'].upper()}\n"
        )
        f.write(
            f"Distance: {recommended['distance_m']:.3f} m\n"
        )
        f.write(
            f"Mean terrain cost: "
            f"{recommended['mean_cost']:.6f}\n"
        )
        f.write(
            f"P90 terrain cost: "
            f"{recommended['p90_cost']:.6f}\n"
        )
        f.write(
            f"High-cost exposure: "
            f"{recommended['high_cost_70_pct']:.2f}%\n"
        )
        f.write(
            f"Overall score: "
            f"{recommended['overall_score']:.6f}\n\n"
        )

        f.write("SHORTEST ROUTE\n")
        f.write("-" * 70 + "\n")
        f.write(
            f"{shortest['route'].upper()} — "
            f"{shortest['distance_m']:.3f} m\n\n"
        )

        f.write("LOWEST HIGH-COST EXPOSURE\n")
        f.write("-" * 70 + "\n")
        f.write(
            f"{safest['route'].upper()} — "
            f"{safest['high_cost_70_pct']:.2f}%\n\n"
        )

        f.write("ROUTE COMPARISON\n")
        f.write("-" * 70 + "\n")

        for route in sorted(
            routes,
            key=lambda r: r["overall_score"],
        ):
            f.write(
                f"{route['route'].upper():12s} "
                f"distance={route['distance_m']:8.3f} m "
                f"mean={route['mean_cost']:.4f} "
                f"p90={route['p90_cost']:.4f} "
                f"exposure={route['high_cost_70_pct']:6.2f}% "
                f"score={route['overall_score']:.4f}\n"
            )

        f.write("\nDOMINATED ROUTES\n")
        f.write("-" * 70 + "\n")

        if dominated:
            for candidate, dominator in dominated:
                f.write(
                    f"{candidate.upper()} is dominated by "
                    f"{dominator.upper()}\n"
                )
        else:
            f.write("None\n")


def main():
    if len(sys.argv) != 3:
        print(
            "Usage:\n"
            "python pipelines/routing/compare_routes.py "
            "<candidate_routes.csv> <output_report.txt>"
        )
        sys.exit(1)

    input_csv = sys.argv[1]
    output_report = sys.argv[2]

    print("=" * 60)
    print("MARSWALK ROUTE COMPARISON")
    print("=" * 60)

    print()
    print("INPUT")
    print("-" * 60)
    print("Candidate routes:", input_csv)

    routes = load_routes(input_csv)

    if not routes:
        raise RuntimeError("No candidate routes found.")

    print("Routes loaded:", len(routes))

    calculate_scores(routes)

    dominated = find_dominated_routes(routes)

    recommended = min(
        routes,
        key=lambda r: r["overall_score"],
    )

    print()
    print("ROUTE COMPARISON")
    print("-" * 60)

    print(
        f"{'ROUTE':<12}"
        f"{'DISTANCE':>12}"
        f"{'MEAN COST':>12}"
        f"{'P90':>10}"
        f"{'EXPOSURE':>12}"
        f"{'SCORE':>10}"
    )

    for route in sorted(
        routes,
        key=lambda r: r["overall_score"],
    ):
        print(
            f"{route['route']:<12}"
            f"{route['distance_m']:>12.2f}"
            f"{route['mean_cost']:>12.4f}"
            f"{route['p90_cost']:>10.4f}"
            f"{route['high_cost_70_pct']:>11.2f}%"
            f"{route['overall_score']:>10.4f}"
        )

    print()
    print("DOMINANCE ANALYSIS")
    print("-" * 60)

    if dominated:
        for candidate, dominator in dominated:
            print(
                f"{candidate.upper()} is dominated by "
                f"{dominator.upper()}"
            )
    else:
        print("No route is completely dominated.")

    print()
    print("RECOMMENDATION")
    print("-" * 60)
    print(
        f"Recommended route: "
        f"{recommended['route'].upper()}"
    )
    print(
        f"Distance: "
        f"{recommended['distance_m']:.2f} m"
    )
    print(
        f"Mean terrain cost: "
        f"{recommended['mean_cost']:.4f}"
    )
    print(
        f"P90 terrain cost: "
        f"{recommended['p90_cost']:.4f}"
    )
    print(
        f"High-cost exposure: "
        f"{recommended['high_cost_70_pct']:.2f}%"
    )
    print(
        f"Overall score: "
        f"{recommended['overall_score']:.4f}"
    )

    output_dir = os.path.dirname(output_report)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    write_report(
        routes,
        dominated,
        output_report,
    )

    print()
    print("Report:", output_report)

    print()
    print("=" * 60)
    print("ROUTE COMPARISON COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
