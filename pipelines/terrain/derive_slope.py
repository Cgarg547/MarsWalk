from pathlib import Path
import sys

import numpy as np
import rasterio
from rasterio.windows import Window


def derive_slope(input_path: str, output_path: str) -> None:
    input_raster = Path(input_path)
    output_raster = Path(output_path)

    if not input_raster.exists():
        print(f"ERROR: Input file does not exist: {input_raster}")
        sys.exit(1)

    output_raster.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("MARSWALK SLOPE DERIVATION")
    print("=" * 60)

    with rasterio.open(input_raster) as src:

        print(f"Input:       {input_raster}")
        print(f"Resolution:  {src.res}")
        print(f"CRS:         {src.crs}")
        print(f"Size:        {src.width} x {src.height}")

        profile = src.profile.copy()

        profile.update(
            dtype="float32",
            count=1,
            nodata=-9999.0,
            compress="deflate",
            predictor=2,
            tiled=True,
            blockxsize=1024,
            blockysize=1024,
        )

        with rasterio.open(output_raster, "w", **profile) as dst:

            # Process in manageable blocks instead of loading
            # the entire 460-million-cell raster into memory.
            block_size = 1024

            for row in range(0, src.height, block_size):

                rows = min(block_size, src.height - row)

                for col in range(0, src.width, block_size):

                    cols = min(block_size, src.width - col)

                    # Read one-cell padding around the block.
                    row_start = max(0, row - 1)
                    col_start = max(0, col - 1)

                    row_end = min(src.height, row + rows + 1)
                    col_end = min(src.width, col + cols + 1)

                    window = Window(
                        col_start,
                        row_start,
                        col_end - col_start,
                        row_end - row_start,
                    )

                    elevation = src.read(
                        1,
                        window=window,
                        masked=True,
                    )

                    # Convert masked values to NaN.
                    values = elevation.filled(np.nan).astype(
                        np.float32
                    )

                    # Calculate gradients.
                    dy, dx = np.gradient(
                        values,
                        src.res[1],
                        src.res[0],
                    )

                    slope_radians = np.arctan(
                        np.sqrt(dx**2 + dy**2)
                    )

                    slope_degrees = np.degrees(
                        slope_radians
                    )

                    # Remove one-cell padding.
                    top = row - row_start
                    left = col - col_start

                    slope = slope_degrees[
                        top:top + rows,
                        left:left + cols,
                    ]

                    # Convert NaN to output NoData.
                    slope = np.where(
                        np.isfinite(slope),
                        slope,
                        -9999.0,
                    ).astype(np.float32)

                    output_window = Window(
                        col,
                        row,
                        cols,
                        rows,
                    )

                    dst.write(
                        slope,
                        1,
                        window=output_window,
                    )

                completed = min(
                    row + block_size,
                    src.height
                )

                percent = (
                    completed / src.height
                ) * 100

                print(
                    f"Progress: {percent:6.2f}%"
                )

    print()
    print(f"Output: {output_raster}")
    print("Slope derivation complete.")
    print("=" * 60)


if __name__ == "__main__":

    if len(sys.argv) != 3:
        print(
            "Usage:\n"
            "python pipelines/terrain/derive_slope.py "
            "<input_dtm> <output_slope>"
        )
        sys.exit(1)

    derive_slope(
        sys.argv[1],
        sys.argv[2],
    )