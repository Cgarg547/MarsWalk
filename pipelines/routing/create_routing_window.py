from pathlib import Path
import sys

import rasterio
from rasterio.windows import Window


def create_window(
    input_raster,
    output_raster,
    row,
    col,
    height,
    width,
):

    with rasterio.open(input_raster) as src:

        window = Window(
            col_off=col,
            row_off=row,
            width=width,
            height=height,
        )

        # Make sure the requested window
        # stays inside the source raster.

        window = window.intersection(
            Window(
                0,
                0,
                src.width,
                src.height,
            )
        )

        data = src.read(
            1,
            window=window,
        )

        transform = src.window_transform(
            window
        )

        profile = src.profile.copy()

        profile.update(
            height=data.shape[0],
            width=data.shape[1],
            transform=transform,
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
                data,
                1,
            )

    print("=" * 60)
    print("MARSWALK ROUTING WINDOW")
    print("=" * 60)

    print()
    print(f"Input:  {input_raster}")
    print(f"Output: {output_raster}")

    print()
    print("WINDOW")
    print("-" * 60)

    print(f"Row:    {row}")
    print(f"Column: {col}")
    print(f"Height: {height}")
    print(f"Width:  {width}")

    print()
    print("Actual output dimensions")
    print(
        f"{data.shape[1]} × {data.shape[0]}"
    )

    print()
    print("=" * 60)
    print(
        "ROUTING WINDOW CREATED"
    )
    print("=" * 60)


def main():

    if len(sys.argv) != 7:

        print(
            "Usage:"
        )

        print(
            "python "
            "pipelines/routing/"
            "create_routing_window.py "
            "<input> <output> "
            "<row> <col> "
            "<height> <width>"
        )

        sys.exit(1)

    create_window(
        sys.argv[1],
        sys.argv[2],
        int(sys.argv[3]),
        int(sys.argv[4]),
        int(sys.argv[5]),
        int(sys.argv[6]),
    )


if __name__ == "__main__":
    main()