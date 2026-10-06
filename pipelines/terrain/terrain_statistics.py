from pathlib import Path
import sys

import numpy as np
import rasterio


def calculate_statistics(path: str) -> None:
    raster_path = Path(path)

    if not raster_path.exists():
        print(f"ERROR: File does not exist: {raster_path}")
        sys.exit(1)

    print("=" * 60)
    print("MARSWALK TERRAIN STATISTICS")
    print("=" * 60)

    with rasterio.open(raster_path) as src:
        print(f"Raster:       {raster_path}")
        print(f"Width:        {src.width}")
        print(f"Height:       {src.height}")
        print(f"Resolution:   {src.res}")
        print(f"CRS:          {src.crs}")
        print()

        # Read the raster as a masked array.
        # Rasterio automatically masks the declared NoData value.
        data = src.read(1, masked=True)

        valid = data.compressed()

        if valid.size == 0:
            print("ERROR: No valid elevation values found.")
            sys.exit(1)

        print(f"Valid cells:  {valid.size:,}")
        print(f"NoData cells: {data.mask.sum():,}")
        print()

        print("ELEVATION STATISTICS")
        print("-" * 60)
        print(f"Minimum:      {np.min(valid):.3f} m")
        print(f"Maximum:      {np.max(valid):.3f} m")
        print(f"Mean:         {np.mean(valid):.3f} m")
        print(f"Median:       {np.median(valid):.3f} m")
        print(f"Std deviation:{np.std(valid):.3f} m")
        print()

        percentiles = np.percentile(
            valid,
            [1, 5, 25, 50, 75, 95, 99]
        )

        print("ELEVATION PERCENTILES")
        print("-" * 60)

        labels = ["1%", "5%", "25%", "50%", "75%", "95%", "99%"]

        for label, value in zip(labels, percentiles):
            print(f"{label:>4}:         {value:.3f} m")

    print()
    print("=" * 60)
    print("TERRAIN STATISTICS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(
            "Usage:\n"
            "python pipelines/terrain/terrain_statistics.py "
            "<raster_file>"
        )
        sys.exit(1)

    calculate_statistics(sys.argv[1])