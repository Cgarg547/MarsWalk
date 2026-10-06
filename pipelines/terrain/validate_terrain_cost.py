from pathlib import Path
import sys

import numpy as np
import rasterio


def collect_samples(path, max_samples=2_000_000):

    values = []

    with rasterio.open(path) as src:

        for _, window in src.block_windows(1):

            data = src.read(
                1,
                window=window,
                masked=True,
            )

            block = data.compressed()

            if block.size == 0:
                continue

            block = block[
                np.isfinite(block)
            ]

            if block.size:
                values.append(
                    block.astype(np.float32)
                )

    if not values:
        raise ValueError(
            f"No valid values in {path}"
        )

    values = np.concatenate(values)

    if values.size > max_samples:

        rng = np.random.default_rng(
            42
        )

        indices = rng.choice(
            values.size,
            size=max_samples,
            replace=False,
        )

        values = values[indices]

    return values


def percentile_report(values):

    percentiles = [
        1,
        5,
        10,
        25,
        50,
        75,
        90,
        95,
        99,
    ]

    for p in percentiles:

        value = np.percentile(
            values,
            p,
        )

        print(
            f"{p:>3}%: {value:.6f}"
        )


def main():

    if len(sys.argv) != 2:

        print(
            "Usage:"
        )

        print(
            "python "
            "pipelines/terrain/"
            "validate_terrain_cost.py "
            "<terrain_cost>"
        )

        sys.exit(1)

    path = Path(sys.argv[1])

    if not path.exists():

        print(
            f"ERROR: File does not exist: "
            f"{path}"
        )

        sys.exit(1)

    print("=" * 60)
    print("MARSWALK TERRAIN COST VALIDATION")
    print("=" * 60)

    print()
    print(f"Raster: {path}")

    values = collect_samples(path)

    print()
    print("VALID VALUES")
    print("-" * 60)

    print(
        f"Sample size: {values.size:,}"
    )

    print(
        f"Minimum:     {values.min():.6f}"
    )

    print(
        f"Maximum:     {values.max():.6f}"
    )

    print(
        f"Mean:        {values.mean():.6f}"
    )

    print(
        f"Median:      {np.median(values):.6f}"
    )

    print(
        f"Std dev:     {values.std():.6f}"
    )

    print()
    print("PERCENTILES")
    print("-" * 60)

    percentile_report(values)

    print()
    print("BOUND CHECK")
    print("-" * 60)

    below_zero = np.count_nonzero(
        values < 0
    )

    above_one = np.count_nonzero(
        values > 1
    )

    exactly_zero = np.count_nonzero(
        values == 0
    )

    exactly_one = np.count_nonzero(
        values == 1
    )

    print(
        f"Values < 0:       {below_zero:,}"
    )

    print(
        f"Values > 1:       {above_one:,}"
    )

    print(
        f"Exactly 0:        {exactly_zero:,}"
    )

    print(
        f"Exactly 1:        {exactly_one:,}"
    )

    print()
    print("EXPECTED")
    print("-" * 60)

    if below_zero == 0:

        print(
            "PASS: No values below 0."
        )

    else:

        print(
            "FAIL: Values below 0 detected."
        )

    if above_one == 0:

        print(
            "PASS: No values above 1."
        )

    else:

        print(
            "FAIL: Values above 1 detected."
        )

    print()
    print("=" * 60)
    print("TERRAIN COST VALIDATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":

    main()