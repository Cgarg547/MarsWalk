from pathlib import Path
import json

import rasterio
from rasterio.windows import from_bounds


RAW = Path(
    "data/raw/jezero/jezero_hirise_dtm_2020.tif"
)

OUTPUT = Path(
    "data/derived/jezero/science_routing/"
    "science_routing_terrain.tif"
)

METADATA = Path(
    "data/derived/jezero/science_routing/"
    "science_routing_metadata.json"
)


TARGETS = {
    "wildcat_ridge": {
        "name": "Wildcat Ridge",
        "x": 4591336.864,
        "y": 1091003.562,
    },
    "skinner_ridge": {
        "name": "Skinner Ridge",
        "x": 4591354.646,
        "y": 1091020.159,
    },
}


MARGIN_M = 3000.0


def main():

    print("=" * 70)
    print("MARSWALK SCIENCE ROUTING WINDOW")
    print("=" * 70)

    xs = [
        target["x"]
        for target in TARGETS.values()
    ]

    ys = [
        target["y"]
        for target in TARGETS.values()
    ]

    left = min(xs) - MARGIN_M
    right = max(xs) + MARGIN_M
    bottom = min(ys) - MARGIN_M
    top = max(ys) + MARGIN_M

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with rasterio.open(RAW) as src:

        print()
        print("SOURCE")
        print("-" * 70)
        print("File:", RAW)
        print("CRS:", src.crs)
        print("Resolution:", src.res)
        print("Bounds:", src.bounds)

        inside = (
            left >= src.bounds.left
            and right <= src.bounds.right
            and bottom >= src.bounds.bottom
            and top <= src.bounds.top
        )

        if not inside:
            raise RuntimeError(
                "Science routing window extends outside "
                "the source DTM."
            )

        window = from_bounds(
            left,
            bottom,
            right,
            top,
            transform=src.transform,
        )

        data = src.read(
            1,
            window=window,
        )

        transform = src.window_transform(window)

        profile = src.profile.copy()

        profile.update(
            height=data.shape[0],
            width=data.shape[1],
            transform=transform,
            compress="deflate",
            tiled=False,
        )

        with rasterio.open(
            OUTPUT,
            "w",
            **profile,
        ) as dst:

            dst.write(data, 1)

        actual_bounds = rasterio.windows.bounds(
            window,
            src.transform,
        )

        actual_left, actual_bottom, actual_right, actual_top = actual_bounds

        metadata = {
            "schema": {
                "name": "MarsWalk Science Routing Window",
                "version": "1.0",
            },
            "source": {
                "filename": str(RAW),
                "crs": str(src.crs),
                "resolution_m": list(src.res),
            },
            "routing_window": {
                "filename": str(OUTPUT),
                "margin_m": MARGIN_M,
                "width": int(data.shape[1]),
                "height": int(data.shape[0]),
                "resolution_m": list(src.res),
                "bounds": {
                    "left": actual_left,
                    "bottom": actual_bottom,
                    "right": actual_right,
                    "top": actual_top,
                },
            },
            "targets": TARGETS,
            "purpose": (
                "Terrain-routing surface centered on "
                "registered MarsWalk candidate science targets."
            ),
            "scientific_status": {
                "classification": "research_demo",
                "operational_certification": False,
                "nasa_certification": False,
            },
        }

    METADATA.write_text(
        json.dumps(
            metadata,
            indent=2,
        )
    )

    print()
    print("ROUTING WINDOW")
    print("-" * 70)
    print("Output:", OUTPUT)
    print("Width:", data.shape[1])
    print("Height:", data.shape[0])
    print("Resolution:", src.res)
    print("Margin:", MARGIN_M, "m")

    print()
    print("TARGETS")
    print("-" * 70)

    for target in TARGETS.values():
        print(
            f"{target['name']}: "
            f"({target['x']:.3f}, {target['y']:.3f})"
        )

    print()
    print("METADATA:", METADATA)

    print()
    print("=" * 70)
    print("SCIENCE ROUTING WINDOW COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
