#!/usr/bin/env python3

from pathlib import Path
import json

import rasterio
from rasterio.windows import from_bounds


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DTM = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "jezero"
    / "jezero_hirise_dtm_2020.tif"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "derived"
    / "jezero"
    / "science"
)

OUTPUT_DTM = OUTPUT_DIR / "science_target_window.tif"
OUTPUT_METADATA = OUTPUT_DIR / "science_window_metadata.json"


TARGETS = {
    "Wildcat Ridge": {
        "x": 4591336.864,
        "y": 1091003.562,
    },
    "Skinner Ridge": {
        "x": 4591354.646,
        "y": 1091020.159,
    },
}


MARGIN_M = 1000.0


def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

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

    print("=" * 70)
    print("MARSWALK SCIENCE TERRAIN WINDOW EXTRACTION")
    print("=" * 70)

    print()
    print("Source:")
    print(RAW_DTM)

    print()
    print("Output:")
    print(OUTPUT_DTM)

    with rasterio.open(RAW_DTM) as src:

        print()
        print("SOURCE TERRAIN")
        print("-" * 70)

        print(f"CRS:         {src.crs}")
        print(f"Resolution:  {src.res}")
        print(f"Dimensions:  {src.width} × {src.height}")
        print(f"Bounds:      {src.bounds}")

        inside = (
            left >= src.bounds.left
            and right <= src.bounds.right
            and bottom >= src.bounds.bottom
            and top <= src.bounds.top
        )

        if not inside:
            raise RuntimeError(
                "Science analysis window lies outside "
                "the source DTM."
            )

        window = from_bounds(
            left,
            bottom,
            right,
            top,
            transform=src.transform,
        )

        window = window.round_offsets().round_lengths()

        data = src.read(
            1,
            window=window,
        )

        transform = src.window_transform(window)

        profile = src.profile.copy()

        profile.update(
            width=window.width,
            height=window.height,
            transform=transform,
            compress="deflate",
            predictor=2,
        )

        with rasterio.open(
            OUTPUT_DTM,
            "w",
            **profile,
        ) as dst:

            dst.write(
                data,
                1,
            )

        metadata = {
            "schema": {
                "name": "MarsWalk Science Window Metadata",
                "version": "1.0",
            },
            "source": {
                "filename": str(
                    RAW_DTM.relative_to(PROJECT_ROOT)
                ),
                "crs": str(src.crs),
                "resolution_m": list(src.res),
                "width": src.width,
                "height": src.height,
            },
            "science_window": {
                "filename": str(
                    OUTPUT_DTM.relative_to(PROJECT_ROOT)
                ),
                "bounds": {
                    "left": float(
                        transform.c
                    ),
                    "top": float(
                        transform.f
                    ),
                },
                "width": int(window.width),
                "height": int(window.height),
                "resolution_m": list(
                    transform
                    and src.res
                ),
                "margin_m": MARGIN_M,
            },
            "targets": TARGETS,
            "coverage_verified": True,
            "method": {
                "description": (
                    "Window extracted directly from the "
                    "source Jezero DTM using raster coordinates."
                ),
                "window_selection": (
                    "Bounding box of science targets plus "
                    "a 1000 m margin on every side."
                ),
            },
            "scientific_status": {
                "classification": "research_input",
                "operational_certification": False,
                "nasa_certification": False,
            },
        }

        OUTPUT_METADATA.write_text(
            json.dumps(
                metadata,
                indent=2,
            )
        )

        print()
        print("SCIENCE WINDOW")
        print("-" * 70)

        print(
            f"Dimensions: "
            f"{window.width:.0f} × "
            f"{window.height:.0f}"
        )

        print(
            f"Resolution: "
            f"{src.res}"
        )

        print(
            f"Target coverage: "
            f"{len(TARGETS)} targets"
        )

    print()
    print("OUTPUT FILES")
    print("-" * 70)
    print(OUTPUT_DTM)
    print(OUTPUT_METADATA)

    print()
    print("=" * 70)
    print("SCIENCE WINDOW EXTRACTION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
