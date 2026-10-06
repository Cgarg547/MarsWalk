from pathlib import Path
import sys

import numpy as np
import rasterio
from rasterio.enums import Resampling


def build_routing_grid(
    input_raster,
    output_raster,
    scale_factor,
):

    with rasterio.open(input_raster) as src:

        new_height = src.height // scale_factor
        new_width = src.width // scale_factor

        data = src.read(
            1,
            out_shape=(
                new_height,
                new_width,
            ),
            resampling=Resampling.average,
        )

        new_transform = src.transform * src.transform.scale(
            src.width / new_width,
            src.height / new_height,
        )

        profile = src.profile.copy()

        profile.update(
            height=new_height,
            width=new_width,
            transform=new_transform,
            compress="deflate",
            tiled=True,
            blockxsize=256,
            blockysize=256,
        )

        with rasterio.open(
            output_raster,
            "w",
            **profile,
        ) as dst:

            dst.write(
                data.astype(np.float32),
                1,
            )

        print("=" * 60)
        print("MARSWALK ROUTING GRID")
        print("=" * 60)

        print()
        print(f"Input:  {input_raster}")
        print(f"Output: {output_raster}")

        print()
        print("SOURCE")
        print("-" * 60)

        print(
            f"Width:       {src.width}"
        )

        print(
            f"Height:      {src.height}"
        )

        print(
            f"Resolution:  "
            f"{src.res[0]} × {src.res[1]} m"
        )

        print()
        print("ROUTING GRID")
        print("-" * 60)

        print(
            f"Width:       {new_width}"
        )

        print(
            f"Height:      {new_height}"
        )

        print(
            f"Resolution:  "
            f"{src.res[0] * scale_factor:.1f} × "
            f"{src.res[1] * scale_factor:.1f} m"
        )

        print(
            f"Nodes:       "
            f"{new_width * new_height:,}"
        )

        print()
        print("=" * 60)
        print(
            "ROUTING GRID COMPLETE"
        )
        print("=" * 60)


def main():

    if len(sys.argv) != 4:

        print(
            "Usage:"
        )

        print(
            "python "
            "pipelines/routing/"
            "build_routing_grid.py "
            "<input> <output> <scale_factor>"
        )

        sys.exit(1)

    input_raster = Path(
        sys.argv[1]
    )

    output_raster = Path(
        sys.argv[2]
    )

    scale_factor = int(
        sys.argv[3]
    )

    if not input_raster.exists():

        print(
            f"ERROR: Input does not exist: "
            f"{input_raster}"
        )

        sys.exit(1)

    output_raster.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    build_routing_grid(
        input_raster,
        output_raster,
        scale_factor,
    )


if __name__ == "__main__":
    main()