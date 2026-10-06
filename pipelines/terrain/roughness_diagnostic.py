from pathlib import Path
import sys

import numpy as np
import rasterio


def diagnose(
    dtm_path: str,
    roughness_path: str,
) -> None:

    dtm = Path(dtm_path)
    roughness = Path(roughness_path)

    if not dtm.exists():
        print(f"ERROR: DTM does not exist: {dtm}")
        sys.exit(1)

    if not roughness.exists():
        print(
            f"ERROR: Roughness raster does not exist: "
            f"{roughness}"
        )
        sys.exit(1)

    print("=" * 60)
    print("MARSWALK ROUGHNESS DIAGNOSTIC")
    print("=" * 60)

    with rasterio.open(dtm) as src:

        print()
        print("DTM")
        print("-" * 60)
        print(f"Size:        {src.width} x {src.height}")
        print(f"Resolution:  {src.res}")
        print(f"CRS:         {src.crs}")
        print(f"NoData:      {src.nodata}")

        zero_count = 0
        valid_count = 0
        flat_window_count = 0

        # Examine a representative set of blocks rather than
        # loading the entire 21k x 21k raster into memory.
        max_blocks = 100
        blocks_examined = 0

        for _, window in src.block_windows(1):

            if blocks_examined >= max_blocks:
                break

            data = src.read(
                1,
                window=window,
                masked=True,
            )

            values = data.compressed()

            if values.size:
                valid_count += values.size

            # Count exact repeated values within each block.
            if data.shape[0] >= 2 and data.shape[1] >= 2:

                a = data[:-1, :-1]
                b = data[:-1, 1:]
                c = data[1:, :-1]
                d = data[1:, 1:]

                valid = (
                    ~a.mask
                    & ~b.mask
                    & ~c.mask
                    & ~d.mask
                )

                if np.any(valid):

                    same = (
                        (a.data == b.data)
                        & (a.data == c.data)
                        & (a.data == d.data)
                        & valid
                    )

                    flat_window_count += np.count_nonzero(
                        same
                    )

            blocks_examined += 1

    print()
    print(
        f"Blocks examined: {blocks_examined}"
    )

    print(
        f"Valid DTM cells examined: "
        f"{valid_count:,}"
    )

    print(
        f"Exact locally-identical "
        f"2x2 neighborhoods: "
        f"{flat_window_count:,}"
    )

    # ------------------------------------------------------------
    # Roughness zero analysis
    # ------------------------------------------------------------

    with rasterio.open(roughness) as src:

        zero_cells = 0
        valid_roughness = 0

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

            valid_roughness += values.size

            zero_cells += np.count_nonzero(
                values == 0
            )

    zero_percentage = (
        zero_cells
        / valid_roughness
        * 100
    )

    print()
    print("ROUGHNESS ZERO CHECK")
    print("-" * 60)

    print(
        f"Valid roughness cells: "
        f"{valid_roughness:,}"
    )

    print(
        f"Zero roughness cells:   "
        f"{zero_cells:,}"
    )

    print(
        f"Zero percentage:        "
        f"{zero_percentage:.4f}%"
    )

    print()
    print("=" * 60)
    print("ROUGHNESS DIAGNOSTIC COMPLETE")
    print("=" * 60)


if __name__ == "__main__":

    if len(sys.argv) != 3:

        print(
            "Usage:"
        )

        print(
            "python "
            "pipelines/terrain/"
            "roughness_diagnostic.py "
            "<dtm> "
            "<roughness>"
        )

        sys.exit(1)

    diagnose(
        sys.argv[1],
        sys.argv[2],
    )