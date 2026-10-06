#!/usr/bin/env python3

from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT = (
    PROJECT_ROOT
    / "data"
    / "derived"
    / "jezero"
    / "science"
    / "science_target_window.tif"
)

OUTPUT = (
    PROJECT_ROOT
    / "data"
    / "derived"
    / "jezero"
    / "science"
    / "science_slope_degrees.tif"
)


def main():

    print("=" * 70)
    print("MARSWALK SCIENCE SLOPE DERIVATION")
    print("=" * 70)

    with rasterio.open(INPUT) as src:

        elevation = src.read(1).astype(np.float64)

        nodata = src.nodata

        valid = np.isfinite(elevation)

        if nodata is not None:
            valid &= elevation != nodata

        dx = float(src.res[0])
        dy = float(src.res[1])

        print()
        print("INPUT")
        print("-" * 70)
        print(f"File:        {INPUT}")
        print(f"CRS:         {src.crs}")
        print(f"Resolution:  {src.res}")
        print(f"Dimensions:  {src.width} × {src.height}")

        # Replace invalid values temporarily so numerical
        # gradient calculations remain stable.
        working = elevation.copy()

        if not np.all(valid):
            median = np.nanmedian(
                np.where(valid, working, np.nan)
            )

            working[~valid] = median

        dz_dy, dz_dx = np.gradient(
            working,
            dy,
            dx,
        )

        slope_radians = np.arctan(
            np.sqrt(
                dz_dx ** 2
                + dz_dy ** 2
            )
        )

        slope_degrees = np.degrees(
            slope_radians
        )

        slope_degrees[~valid] = np.nan

        profile = src.profile.copy()

        profile.update(
            dtype="float32",
            count=1,
            nodata=-9999.0,
            compress="deflate",
            predictor=3,
        )

        with rasterio.open(
            OUTPUT,
            "w",
            **profile,
        ) as dst:

            output = slope_degrees.astype(
                np.float32
            )

            output[~np.isfinite(output)] = -9999.0

            dst.write(
                output,
                1,
            )

    print()
    print("OUTPUT")
    print("-" * 70)
    print(OUTPUT)

    valid_slope = slope_degrees[
        np.isfinite(slope_degrees)
    ]

    print()
    print("SLOPE STATISTICS")
    print("-" * 70)
    print(
        f"Minimum: {np.min(valid_slope):.3f}°"
    )
    print(
        f"Mean:    {np.mean(valid_slope):.3f}°"
    )
    print(
        f"Median:  {np.median(valid_slope):.3f}°"
    )
    print(
        f"P95:     {np.percentile(valid_slope, 95):.3f}°"
    )
    print(
        f"Maximum: {np.max(valid_slope):.3f}°"
    )

    print()
    print("=" * 70)
    print("SCIENCE SLOPE DERIVATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
