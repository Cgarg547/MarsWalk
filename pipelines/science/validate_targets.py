#!/usr/bin/env python3

from pathlib import Path
import sys

import yaml


REQUIRED_FIELDS = {
    "id",
    "name",
    "target_type",
    "description",
    "source",
    "coordinates",
}


def validate_target(target):
    errors = []

    missing = REQUIRED_FIELDS - set(target.keys())

    if missing:
        errors.append(
            f"missing fields: {', '.join(sorted(missing))}"
        )

    coordinates = target.get("coordinates")

    if coordinates is not None:

        if "x" not in coordinates or "y" not in coordinates:
            errors.append(
                "coordinates must contain x and y"
            )

        else:

            try:
                float(coordinates["x"])
                float(coordinates["y"])
            except (TypeError, ValueError):
                errors.append(
                    "coordinates x/y must be numeric"
                )

    source = target.get("source")

    if source is not None:

        if not isinstance(source, dict):
            errors.append(
                "source must be an object"
            )

        else:

            if not source.get("dataset"):
                errors.append(
                    "source.dataset is required"
                )

            if not source.get("reference"):
                errors.append(
                    "source.reference is required"
                )

    return errors


def main():

    if len(sys.argv) != 2:

        print(
            "Usage:\n"
            "python pipelines/science/validate_targets.py "
            "<targets.yaml>"
        )

        sys.exit(1)

    path = Path(sys.argv[1])

    if not path.exists():
        raise RuntimeError(
            f"Target registry not found: {path}"
        )

    with open(path, "r") as f:
        registry = yaml.safe_load(f)

    targets = registry.get("targets", [])

    print("=" * 64)
    print("MARSWALK SCIENCE TARGET VALIDATOR")
    print("=" * 64)

    print()
    print(f"Registry: {path}")
    print(f"Targets:  {len(targets)}")

    errors_found = False

    for target in targets:

        target_id = target.get(
            "id",
            "<unknown>"
        )

        errors = validate_target(target)

        if errors:

            errors_found = True

            print()
            print(f"FAIL: {target_id}")

            for error in errors:
                print(f"  - {error}")

        else:

            print(
                f"PASS: {target_id} "
                f"({target.get('name', 'Unnamed')})"
            )

    print()

    if errors_found:

        print("VALIDATION FAILED")
        sys.exit(1)

    print("VALIDATION PASSED")


if __name__ == "__main__":
    main()
