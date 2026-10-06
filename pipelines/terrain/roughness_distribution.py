from pathlib import Path
import sys

import numpy as np
import rasterio


def analyze_distribution(input_path: str) -> None:

    input_raster = Path(input_path)

    if not input_raster.exists():
        print(f"ERROR: File does not exist: {input_raster}")
        sys.exit(1)

    print("=" * 60)
    print("MARSWALK ROUGHNESS DISTRIBUTION")
    print("=" * 60)

    chunks = []

    with rasterio.open(input_raster) as src:

        print(f"Raster:       {input_raster}")
        print(f"CRS:          {src.crs}")
        print(f"Resolution:   {src.res}")

        for _, window in src.block_windows(1):

            data = src.read(
                1,
                window=window,
                masked=True,
            )

            values = data.compressed()

            if values.size == 0:
                continue

            values = values[np.isfinite(values)]

            if values.size:
                chunks.append(
                    values.astype(np.float32)
                )

    if not chunks:
        print("ERROR: No valid values.")
        sys.exit(1)

    values = np.concatenate(chunks)

    print()
    print(f"Valid cells: {len(values):,}")

    # ------------------------------------------------------------
    # Exact zero
    # ------------------------------------------------------------

    zero_count = np.count_nonzero(
        values == 0
    )

    zero_percent = (
        zero_count / len(values)
    ) * 100

    print()
    print("EXACT ZERO")
    print("-" * 60)
    print(
        f"Count:       {zero_count:,}"
    )
    print(
        f"Percentage:  {zero_percent:.4f}%"
    )

    # ------------------------------------------------------------
    # Distribution bins
    # ------------------------------------------------------------

    bins = [
        (0.0, 0.1),
        (0.1, 0.25),
        (0.25, 0.5),
        (0.5, 0.75),
        (0.75, 1.0),
        (1.0, 1.5),
        (1.5, 2.0),
        (2.0, 3.0),
        (3.0, 5.0),
        (5.0, np.inf),
    ]

    print()
    print("ROUGHNESS DISTRIBUTION")
    print("-" * 60)

    for lower, upper in bins:

        if np.isinf(upper):

            mask = values >= lower

            label = f">={lower:.2f} m"

        else:

            mask = (
                (values >= lower)
                & (values < upper)
            )

            label = (
                f"{lower:.2f}–{upper:.2f} m"
            )

        count = np.count_nonzero(mask)

        percentage = (
            count / len(values)
        ) * 100

        print(
            f"{label:<15}"
            f"{count:>14,}"
            f"   {percentage:>8.4f}%"
        )

    # ------------------------------------------------------------
    # Unique values
    # ------------------------------------------------------------

    unique_values = np.unique(values)

    print()
    print("UNIQUE VALUE SUMMARY")
    print("-" * 60)

    print(
        f"Unique values: {len(unique_values):,}"
    )

    print()
    print(
        "First values:"
    )

    for value in unique_values[:20]:

        print(
            f"  {value:.6f} m"
        )

    print()
    print("=" * 60)
    print("ROUGHNESS DISTRIBUTION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":

    if len(sys.argv) != 2:

        print(
            "Usage:"
        )

        print(
            "python "
            "pipelines/terrain/"
            "roughness_distribution.py "
            "<roughness_raster>"
        )

        sys.exit(1)

    analyze_distribution(
        sys.argv[1]
    )