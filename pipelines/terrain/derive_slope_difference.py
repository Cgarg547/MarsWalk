from pathlib import Path
import sys

import numpy as np
import rasterio


def derive_slope_difference(
    local_path: str,
    broad_path: str,
    output_path: str,
) -> None:

    local_raster = Path(local_path)
    broad_raster = Path(broad_path)
    output_raster = Path(output_path)

    if not local_raster.exists():
        print(
            f"ERROR: Local slope does not exist: "
            f"{local_raster}"
        )
        sys.exit(1)

    if not broad_raster.exists():
        print(
            f"ERROR: Broad slope does not exist: "
            f"{broad_raster}"
        )
        sys.exit(1)

    output_raster.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("=" * 60)
    print("MARSWALK SLOPE SCALE DIFFERENCE")
    print("=" * 60)

    with rasterio.open(local_raster) as local:
        with rasterio.open(broad_raster) as broad:

            if local.width != broad.width:
                raise ValueError(
                    "Raster widths do not match."
                )

            if local.height != broad.height:
                raise ValueError(
                    "Raster heights do not match."
                )

            if local.transform != broad.transform:
                raise ValueError(
                    "Raster transforms do not match."
                )

            if local.crs != broad.crs:
                raise ValueError(
                    "Raster CRS values do not match."
                )

            profile = local.profile.copy()

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

                for _, window in local.block_windows(1):

                    local_data = local.read(
                        1,
                        window=window,
                        masked=True,
                    )

                    broad_data = broad.read(
                        1,
                        window=window,
                        masked=True,
                    )

                    local_values = (
                        local_data.filled(
                            np.nan
                        ).astype(np.float32)
                    )

                    broad_values = (
                        broad_data.filled(
                            np.nan
                        ).astype(np.float32)
                    )

                    difference = np.abs(
                        local_values
                        - broad_values
                    )

                    invalid = (
                        ~np.isfinite(local_values)
                        | ~np.isfinite(broad_values)
                    )

                    difference[invalid] = -9999.0

                    difference = difference.astype(
                        np.float32
                    )

                    dst.write(
                        difference,
                        1,
                        window=window,
                    )

    print()
    print(f"Local slope:  {local_raster}")
    print(f"Broad slope:  {broad_raster}")
    print(f"Output:       {output_raster}")
    print()
    print(
        "Slope difference derivation complete."
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
            "derive_slope_difference.py "
            "<local_slope> "
            "<broad_slope> "
            "<output>"
        )

        sys.exit(1)

    derive_slope_difference(
        sys.argv[1],
        sys.argv[2],
        sys.argv[3],
    )