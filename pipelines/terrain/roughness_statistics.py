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
    print("MARSWALK TERRAIN ROUGHNESS STATISTICS")
    print("=" * 60)

    with rasterio.open(input_raster) as src:

        print(f"Raster:       {input_raster}")
        print(f"Width:        {src.width}")
        print(f"Height:       {src.height}")
        print(f"Resolution:   {src.res}")
        print(f"CRS:          {src.crs}")
        print(f"NoData:       {src.nodata}")

        chunks = []
        valid_cells = 0

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

            if values.size == 0:
                continue

            valid_cells += values.size
            chunks.append(values.astype(np.float32))

        total_cells = src.width * src.height
        nodata_cells = total_cells - valid_cells

    if not chunks:
        print("ERROR: No valid values found.")
        sys.exit(1)

    values = np.concatenate(chunks)

    print()
    print(f"Valid cells:  {valid_cells:,}")
    print(f"NoData cells: {nodata_cells:,}")

    print()
    print("ROUGHNESS STATISTICS")
    print("-" * 60)

    print(f"Minimum:      {np.min(values):.4f} m")
    print(f"Maximum:      {np.max(values):.4f} m")
    print(f"Mean:         {np.mean(values):.4f} m")
    print(f"Median:       {np.median(values):.4f} m")
    print(f"Std deviation:{np.std(values):.4f} m")

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
    print("ROUGHNESS PERCENTILES")
    print("-" * 60)

    for percentile in percentiles:

        value = np.percentile(
            values,
            percentile,
        )

        print(
            f"{percentile:>3}%:         {value:.4f} m"
        )

    print()
    print("=" * 60)
    print("ROUGHNESS STATISTICS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":

    if len(sys.argv) != 2:

        print(
            "Usage:"
        )

        print(
            "python "
            "pipelines/terrain/"
            "roughness_statistics.py "
            "<roughness_raster>"
        )

        sys.exit(1)

    calculate_statistics(sys.argv[1])