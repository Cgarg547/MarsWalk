from pathlib import Path
import sys

import numpy as np
import rasterio
from rasterio.windows import Window


def derive_baseline_slope(
    input_path: str,
    output_path: str,
    baseline_meters: int,
) -> None:

    input_raster = Path(input_path)
    output_raster = Path(output_path)

    if not input_raster.exists():
        print(f"ERROR: Input file does not exist: {input_raster}")
        sys.exit(1)

    if baseline_meters <= 0:
        print("ERROR: Baseline must be greater than zero.")
        sys.exit(1)

    output_raster.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("=" * 60)
    print("MARSWALK MULTI-SCALE TERRAIN SLOPE")
    print("=" * 60)

    with rasterio.open(input_raster) as src:

        pixel_x = float(src.res[0])
        pixel_y = float(src.res[1])

        if not np.isclose(pixel_x, pixel_y):
            print(
                "ERROR: This implementation requires square pixels."
            )
            sys.exit(1)

        baseline_pixels = int(
            round(baseline_meters / pixel_x)
        )

        if baseline_pixels < 1:
            baseline_pixels = 1

        # For an even baseline, use symmetric endpoints.
        # For an odd baseline, use interpolation between
        # neighboring raster samples.
        half_distance = baseline_pixels / 2.0

        print(f"Requested baseline: {baseline_meters} m")
        print(f"Pixel size:         {pixel_x:.3f} m")
        print(f"Baseline pixels:    {baseline_pixels}")

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

            # We need enough padding to support the requested
            # baseline around every output pixel.
            padding = int(
                np.ceil(half_distance)
            ) + 1

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

                    # -------------------------------------------------
                    # Desired padded extent.
                    # -------------------------------------------------

                    desired_row_start = row - padding
                    desired_col_start = col - padding

                    desired_row_end = (
                        row + rows + padding
                    )

                    desired_col_end = (
                        col + cols + padding
                    )

                    # -------------------------------------------------
                    # Actual raster intersection.
                    # -------------------------------------------------

                    actual_row_start = max(
                        0,
                        desired_row_start,
                    )

                    actual_col_start = max(
                        0,
                        desired_col_start,
                    )

                    actual_row_end = min(
                        src.height,
                        desired_row_end,
                    )

                    actual_col_end = min(
                        src.width,
                        desired_col_end,
                    )

                    actual_window = Window(
                        actual_col_start,
                        actual_row_start,
                        actual_col_end
                        - actual_col_start,
                        actual_row_end
                        - actual_row_start,
                    )

                    data = src.read(
                        1,
                        window=actual_window,
                        masked=True,
                    )

                    values = data.filled(
                        np.nan
                    ).astype(np.float32)

                    # -------------------------------------------------
                    # Explicitly pad at raster boundaries.
                    # -------------------------------------------------

                    pad_top = (
                        actual_row_start
                        - desired_row_start
                    )

                    pad_bottom = (
                        desired_row_end
                        - actual_row_end
                    )

                    pad_left = (
                        actual_col_start
                        - desired_col_start
                    )

                    pad_right = (
                        desired_col_end
                        - actual_col_end
                    )

                    values = np.pad(
                        values,
                        (
                            (pad_top, pad_bottom),
                            (pad_left, pad_right),
                        ),
                        mode="constant",
                        constant_values=np.nan,
                    )

                    # -------------------------------------------------
                    # Position of the output block inside padded data.
                    # -------------------------------------------------

                    center_row = padding
                    center_col = padding

                    center = values[
                        center_row:center_row + rows,
                        center_col:center_col + cols,
                    ]

                    # -------------------------------------------------
                    # Calculate slopes using endpoints separated by
                    # the requested horizontal baseline.
                    #
                    # For even baselines this is symmetric.
                    # For odd baselines we use the nearest raster
                    # samples on either side and document the actual
                    # discrete baseline.
                    # -------------------------------------------------

                    if baseline_pixels % 2 == 0:

                        half = baseline_pixels // 2

                        north = values[
                            center_row - half:
                            center_row - half + rows,
                            center_col:
                            center_col + cols,
                        ]

                        south = values[
                            center_row + half:
                            center_row + half + rows,
                            center_col:
                            center_col + cols,
                        ]

                        west = values[
                            center_row:
                            center_row + rows,
                            center_col - half:
                            center_col - half + cols,
                        ]

                        east = values[
                            center_row:
                            center_row + rows,
                            center_col + half:
                            center_col + half + cols,
                        ]

                        actual_distance = (
                            baseline_pixels
                            * pixel_x
                        )

                    else:

                        # Odd baselines cannot be represented by
                        # perfectly symmetric integer-pixel endpoints.
                        #
                        # We therefore use the nearest symmetric
                        # integer-pixel baseline and explicitly report
                        # the discrete distance.

                        half = baseline_pixels // 2

                        north = values[
                            center_row - half:
                            center_row - half + rows,
                            center_col:
                            center_col + cols,
                        ]

                        south = values[
                            center_row + half:
                            center_row + half + rows,
                            center_col:
                            center_col + cols,
                        ]

                        west = values[
                            center_row:
                            center_row + rows,
                            center_col - half:
                            center_col - half + cols,
                        ]

                        east = values[
                            center_row:
                            center_row + rows,
                            center_col + half:
                            center_col + half + cols,
                        ]

                        actual_distance = (
                            2
                            * half
                            * pixel_x
                        )

                    # -------------------------------------------------
                    # Verify dimensions.
                    # -------------------------------------------------

                    expected_shape = (
                        rows,
                        cols,
                    )

                    if not (
                        center.shape
                        == north.shape
                        == south.shape
                        == west.shape
                        == east.shape
                        == expected_shape
                    ):

                        raise RuntimeError(
                            "Internal window-shape error: "
                            f"expected {expected_shape}, "
                            f"got center={center.shape}, "
                            f"north={north.shape}, "
                            f"south={south.shape}, "
                            f"west={west.shape}, "
                            f"east={east.shape}"
                        )

                    # -------------------------------------------------
                    # Central-difference terrain gradient.
                    # -------------------------------------------------

                    dz_dx = (
                        east - west
                    ) / actual_distance

                    dz_dy = (
                        south - north
                    ) / actual_distance

                    slope = np.degrees(
                        np.arctan(
                            np.sqrt(
                                dz_dx ** 2
                                + dz_dy ** 2
                            )
                        )
                    )

                    # -------------------------------------------------
                    # Propagate NoData.
                    # -------------------------------------------------

                    invalid = (
                        ~np.isfinite(center)
                        | ~np.isfinite(north)
                        | ~np.isfinite(south)
                        | ~np.isfinite(west)
                        | ~np.isfinite(east)
                    )

                    slope[invalid] = -9999.0

                    slope = slope.astype(
                        np.float32
                    )

                    # -------------------------------------------------
                    # Write output block.
                    # -------------------------------------------------

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
    print(f"Output: {output_raster}")
    print("Multi-scale slope derivation complete.")
    print("=" * 60)


if __name__ == "__main__":

    if len(sys.argv) != 4:

        print(
            "Usage:"
        )

        print(
            "python "
            "pipelines/terrain/"
            "derive_multiscale_slope.py "
            "<input_dtm> "
            "<output_slope> "
            "<baseline_meters>"
        )

        sys.exit(1)

    derive_baseline_slope(
        sys.argv[1],
        sys.argv[2],
        int(sys.argv[3]),
    )