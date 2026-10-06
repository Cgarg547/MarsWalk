from pathlib import Path
import sys

import numpy as np
import rasterio


def calculate_statistics(input_path: str) -> None:

    input_raster = Path(input_path)

    if not input_raster.exists():
        print(f"ERROR: File does not exist: {input_raster}")
        sys.exit(1)

    print("=" * 60)
    print("MARSWALK MULTI-SCALE SLOPE STATISTICS")
    print("=" * 60)

    with rasterio.open(input_raster) as src:

        print(f"Raster:       {input_raster}")
        print(f"Width:        {src.width}")
        print(f"Height:       {src.height}")
        print(f"Resolution:   {src.res}")
        print(f"CRS:          {src.crs}")
        print(f"NoData:       {src.nodata}")

        valid_values = []

        valid_cells = 0
        nodata_cells = 0

        # Process the raster block-by-block.
        for _, window in src.block_windows(1):

            data = src.read(
                1,
                window=window,
                masked=True,
            )

            values = data.compressed()

            if values.size == 0:
                continue

            values = values[
                np.isfinite(values)
            ]

            if values.size == 0:
                continue

            valid_cells += values.size

            valid_values.append(
                values.astype(np.float32)
            )

        total_cells = src.width * src.height

        nodata_cells = (
            total_cells - valid_cells
        )

        if not valid_values:
            print("ERROR: No valid raster values found.")
            sys.exit(1)

        values = np.concatenate(
            valid_values
        )

    print()
    print(f"Valid cells:  {valid_cells:,}")
    print(f"NoData cells: {nodata_cells:,}")

    print()
    print("SLOPE STATISTICS")
    print("-" * 60)

    print(
        f"Minimum:      {np.min(values):.4f}°"
    )

    print(
        f"Maximum:      {np.max(values):.4f}°"
    )

    print(
        f"Mean:         {np.mean(values):.4f}°"
    )

    print(
        f"Median:       {np.median(values):.4f}°"
    )

    print(
        f"Std deviation:{np.std(values):.4f}°"
    )

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

    print()
    print("SLOPE PERCENTILES")
    print("-" * 60)

    for percentile in percentiles:

        value = np.percentile(
            values,
            percentile,
        )

        print(
            f"{percentile:>3}%:         "
            f"{value:.4f}°"
        )

    print()
    print("=" * 60)
    print("SLOPE STATISTICS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":

    if len(sys.argv) != 2:

        print(
            "Usage:"
        )

        print(
            "python "
            "pipelines/terrain/"
            "slope_statistics.py "
            "<slope_raster>"
        )

        sys.exit(1)

    calculate_statistics(
        sys.argv[1]
    )