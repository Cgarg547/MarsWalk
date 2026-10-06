from pathlib import Path
import sys

import numpy as np
import rasterio
from scipy.ndimage import generic_filter


def local_std(values):
    values = values[np.isfinite(values)]

    if values.size < 2:
        return np.nan

    return np.std(values)


def derive_roughness(
    input_path: str,
    output_path: str,
    window_pixels: int,
) -> None:

    input_raster = Path(input_path)
    output_raster = Path(output_path)

    if not input_raster.exists():
        print(f"ERROR: Input does not exist: {input_raster}")
        sys.exit(1)

    if window_pixels < 3:
        print("ERROR: Window must be at least 3 pixels.")
        sys.exit(1)

    if window_pixels % 2 == 0:
        print("ERROR: Window must be odd.")
        sys.exit(1)

    output_raster.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("=" * 60)
    print("MARSWALK ROBUST TERRAIN ROUGHNESS")
    print("=" * 60)

    with rasterio.open(input_raster) as src:

        print(f"Input:          {input_raster}")
        print(f"Pixel size:     {src.res}")
        print(f"Window:         {window_pixels} x {window_pixels}")

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

        half = window_pixels // 2

        with rasterio.open(
            output_raster,
            "w",
            **profile,
        ) as dst:

            # Process blocks.
            block_size = 1024

            for row in range(
                0,
                src.height,
                block_size,
            ):

                rows = min(
                    block_size,
                    src.height - row,
                )

                for col in range(
                    0,
                    src.width,
                    block_size,
                ):

                    cols = min(
                        block_size,
                        src.width - col,
                    )

                    row_start = max(
                        0,
                        row - half,
                    )

                    col_start = max(
                        0,
                        col - half,
                    )

                    row_end = min(
                        src.height,
                        row + rows + half,
                    )

                    col_end = min(
                        src.width,
                        col + cols + half,
                    )

                    window = rasterio.windows.Window(
                        col_start,
                        row_start,
                        col_end - col_start,
                        row_end - row_start,
                    )

                    masked = src.read(
                        1,
                        window=window,
                        masked=True,
                    )

                    data = masked.filled(
                        np.nan
                    ).astype(np.float32)

                    # Direct local standard deviation.
                    roughness = generic_filter(
                        data,
                        local_std,
                        size=window_pixels,
                        mode="nearest",
                    )

                    center = roughness[
                        half:half + rows,
                        half:half + cols,
                    ]

                    center = center.astype(
                        np.float32
                    )

                    center[
                        ~np.isfinite(center)
                    ] = -9999.0

                    output_window = rasterio.windows.Window(
                        col,
                        row,
                        cols,
                        rows,
                    )

                    dst.write(
                        center,
                        1,
                        window=output_window,
                    )

                completed = min(
                    row + block_size,
                    src.height,
                )

                progress = (
                    completed
                    / src.height
                    * 100
                )

                print(
                    f"Progress: {progress:6.2f}%"
                )

    print()
    print(
        f"Output: {output_raster}"
    )

    print(
        "Robust roughness derivation complete."
    )

    print("=" * 60)


if __name__ == "__main__":

    if len(sys.argv) != 4:

        print(
            "Usage:"
        )

        print(
            "python "
            "pipelines/terrain/"
            "derive_roughness_robust.py "
            "<dtm> "
            "<output> "
            "<window_pixels>"
        )

        sys.exit(1)

    derive_roughness(
        sys.argv[1],
        sys.argv[2],
        int(sys.argv[3]),
    )