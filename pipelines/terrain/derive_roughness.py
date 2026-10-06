from pathlib import Path
import sys

import numpy as np
import rasterio
from scipy.ndimage import uniform_filter


def derive_roughness(
    input_path: str,
    output_path: str,
    window_meters: int,
) -> None:

    input_raster = Path(input_path)
    output_raster = Path(output_path)

    if not input_raster.exists():
        print(
            f"ERROR: Input file does not exist: "
            f"{input_raster}"
        )
        sys.exit(1)

    if window_meters <= 0:
        print(
            "ERROR: Window size must be greater than zero."
        )
        sys.exit(1)

    output_raster.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("=" * 60)
    print("MARSWALK TERRAIN ROUGHNESS")
    print("=" * 60)

    with rasterio.open(input_raster) as src:

        pixel_size = float(src.res[0])

        if not np.isclose(
            src.res[0],
            src.res[1],
        ):
            print(
                "ERROR: Raster must have square pixels."
            )
            sys.exit(1)

        window_pixels = int(
            round(
                window_meters
                / pixel_size
            )
        )

        if window_pixels < 3:
            window_pixels = 3

        # Use an odd window so there is a clear center.
        if window_pixels % 2 == 0:
            window_pixels += 1

        print(
            f"Input:          {input_raster}"
        )

        print(
            f"Pixel size:     {pixel_size:.3f} m"
        )

        print(
            f"Requested size: {window_meters} m"
        )

        print(
            f"Window:         "
            f"{window_pixels} x "
            f"{window_pixels} pixels"
        )

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

        with rasterio.open(
            output_raster,
            "w",
            **profile,
        ) as dst:

            block_size = 1024

            half = window_pixels // 2

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

                    # Read padded block.
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

                    data = src.read(
                        1,
                        window=window,
                        masked=True,
                    )

                    elevation = data.filled(
                        np.nan
                    ).astype(np.float32)

                    # -------------------------------------------------
                    # NaN-aware local mean and variance.
                    # -------------------------------------------------

                    valid = np.isfinite(
                        elevation
                    ).astype(np.float32)

                    safe_elevation = np.where(
                        np.isfinite(elevation),
                        elevation,
                        0.0,
                    )

                    local_sum = uniform_filter(
                        safe_elevation,
                        size=window_pixels,
                        mode="nearest",
                    )

                    local_count = uniform_filter(
                        valid,
                        size=window_pixels,
                        mode="nearest",
                    )

                    local_sum_sq = uniform_filter(
                        safe_elevation ** 2,
                        size=window_pixels,
                        mode="nearest",
                    )

                    mean = np.divide(
                        local_sum,
                        local_count,
                        out=np.full_like(
                            local_sum,
                            np.nan,
                        ),
                        where=local_count > 0,
                    )

                    mean_sq = np.divide(
                        local_sum_sq,
                        local_count,
                        out=np.full_like(
                            local_sum_sq,
                            np.nan,
                        ),
                        where=local_count > 0,
                    )

                    variance = (
                        mean_sq
                        - mean ** 2
                    )

                    variance = np.maximum(
                        variance,
                        0.0,
                    )

                    roughness = np.sqrt(
                        variance
                    )

                    # Extract center block.
                    center = roughness[
                        half:half + rows,
                        half:half + cols,
                    ]

                    center_count = local_count[
                        half:half + rows,
                        half:half + cols,
                    ]

                    center = center.astype(
                        np.float32
                    )

                    invalid = (
                        ~np.isfinite(center)
                        | (center_count <= 0)
                    )

                    center[invalid] = -9999.0

                    output_window = (
                        rasterio.windows.Window(
                            col,
                            row,
                            cols,
                            rows,
                        )
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

                percent = (
                    completed
                    / src.height
                ) * 100.0

                print(
                    f"Progress: {percent:6.2f}%"
                )

    print()
    print(
        f"Output: {output_raster}"
    )

    print(
        "Terrain roughness derivation complete."
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
            "derive_roughness.py "
            "<input_dtm> "
            "<output_roughness> "
            "<window_meters>"
        )

        sys.exit(1)

    derive_roughness(
        sys.argv[1],
        sys.argv[2],
        int(sys.argv[3]),
    )