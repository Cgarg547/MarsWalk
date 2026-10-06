#!/usr/bin/env python3

from pathlib import Path
import sys

import yaml


def load_targets(path):

    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"Target registry not found: {path}"
        )

    with open(path, "r") as f:
        registry = yaml.safe_load(f) or {}

    return registry


def main():

    if len(sys.argv) != 2:

        print(
            "Usage:\n"
            "python pipelines/science/load_targets.py "
            "<targets.yaml>"
        )

        sys.exit(1)

    registry = load_targets(sys.argv[1])

    targets = registry.get(
        "targets",
        []
    )

    print("=" * 64)
    print("MARSWALK SCIENCE TARGET REGISTRY")
    print("=" * 64)

    print()
    print(
        f"Study area: "
        f"{registry.get('study_area', {}).get('name', 'Unknown')}"
    )

    print(
        f"Targets: {len(targets)}"
    )

    for target in targets:

        print()
        print(
            f"{target.get('id')}: "
            f"{target.get('name')}"
        )

        print(
            f"Type: "
            f"{target.get('target_type')}"
        )

        coordinates = target.get(
            "coordinates",
            {}
        )

        print(
            f"Coordinates: "
            f"{coordinates.get('x')}, "
            f"{coordinates.get('y')}"
        )


if __name__ == "__main__":
    main()
