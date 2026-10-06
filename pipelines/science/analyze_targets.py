#!/usr/bin/env python3

from pathlib import Path
import json
import math
import sys

import numpy as np
import rasterio


# ============================================================
# MARSWALK SCIENCE TARGET ANALYSIS ENGINE
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

TARGET_REGISTRY = (
    PROJECT_ROOT
    / "data"
    / "metadata"
    / "science"
    / "targets.yaml"
)

SCIENCE_WINDOW = (
    PROJECT_ROOT
    / "data"
    / "derived"
    / "jezero"
    / "science"
    / "science_target_window.tif"
)

SCIENCE_SLOPE = (
    PROJECT_ROOT
    / "data"
    / "derived"
    / "jezero"
    / "science"
    / "science_slope_degrees.tif"
)

OUTPUT = (
    PROJECT_ROOT
    / "data"
    / "derived"
    / "jezero"
    / "science"
    / "target_analysis.json"
)

# Radius used to characterize terrain immediately
# surrounding each science target.
ANALYSIS_RADIUS_M = 100.0

# These are terrain-characterization thresholds,
# NOT rover certification limits.
SLOPE_THRESHOLDS = [5.0, 10.0, 15.0, 20.0]


# ============================================================
# TARGET REGISTRY
# ============================================================

def load_targets():

    import yaml

    if not TARGET_REGISTRY.exists():
        raise RuntimeError(
            f"Target registry not found: {TARGET_REGISTRY}"
        )

    with open(TARGET_REGISTRY, "r") as f:
        registry = yaml.safe_load(f) or {}

    targets = registry.get("targets", [])

    if not targets:
        raise RuntimeError(
            "Science target registry contains zero targets."
        )

    return registry, targets


# ============================================================
# TARGET WINDOW EXTRACTION
# ============================================================

def extract_target_values(
    src,
    raster,
    x,
    y,
    radius_m,
):

    pixel_x = abs(src.transform.a)
    pixel_y = abs(src.transform.e)

    radius_pixels_x = int(
        math.ceil(radius_m / pixel_x)
    )

    radius_pixels_y = int(
        math.ceil(radius_m / pixel_y)
    )

    row, col = src.index(x, y)

    row_start = max(
        0,
        row - radius_pixels_y,
    )

    row_end = min(
        src.height,
        row + radius_pixels_y + 1,
    )

    col_start = max(
        0,
        col - radius_pixels_x,
    )

    col_end = min(
        src.width,
        col + radius_pixels_x + 1,
    )

    subset = raster[
        row_start:row_end,
        col_start:col_end,
    ].astype(float)

    valid = np.isfinite(subset)

    if src.nodata is not None:
        valid &= subset != src.nodata

    values = subset[valid]

    return (
        values,
        row,
        col,
        (
            row_start,
            row_end,
            col_start,
            col_end,
        ),
    )


# ============================================================
# STATISTICS
# ============================================================

def calculate_statistics(values):

    if len(values) == 0:
        raise RuntimeError(
            "No valid terrain values found."
        )

    statistics = {
        "sample_count": int(len(values)),
        "minimum": float(np.min(values)),
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
        "p90": float(np.percentile(values, 90)),
        "p95": float(np.percentile(values, 95)),
        "maximum": float(np.max(values)),
    }

    threshold_exposure = {}

    for threshold in SLOPE_THRESHOLDS:

        percentage = (
            np.mean(values >= threshold)
            * 100.0
        )

        threshold_exposure[
            f"greater_equal_{threshold:g}_degrees"
        ] = float(percentage)

    statistics["threshold_exposure_percent"] = (
        threshold_exposure
    )

    return statistics


# ============================================================
# TARGET ANALYSIS
# ============================================================

def analyze_target(
    target,
    slope_src,
    slope_raster,
    window_src,
):

    target_id = target.get("id")
    name = target.get("name")

    coordinates = target.get(
        "coordinates",
        {},
    )

    x = float(coordinates["x"])
    y = float(coordinates["y"])

    # Verify target lies inside the science window.
    inside_window = (
        window_src.bounds.left <= x <= window_src.bounds.right
        and
        window_src.bounds.bottom <= y <= window_src.bounds.top
    )

    if not inside_window:
        raise RuntimeError(
            f"{target_id} ({name}) lies outside "
            "the science analysis window."
        )

    values, row, col, pixel_window = (
        extract_target_values(
            slope_src,
            slope_raster,
            x,
            y,
            ANALYSIS_RADIUS_M,
        )
    )

    statistics = calculate_statistics(
        values
    )

    return {
        "id": target_id,
        "name": name,
        "target_type": target.get(
            "target_type"
        ),
        "coordinates": {
            "x_m": x,
            "y_m": y,
            "crs": str(slope_src.crs),
        },
        "spatial_verification": {
            "inside_science_window": True,
            "raster_row": int(row),
            "raster_column": int(col),
            "analysis_radius_m": ANALYSIS_RADIUS_M,
            "analysis_pixels": {
                "row_start": int(pixel_window[0]),
                "row_end": int(pixel_window[1]),
                "column_start": int(pixel_window[2]),
                "column_end": int(pixel_window[3]),
            },
        },
        "slope_statistics_degrees": statistics,
        "source": target.get(
            "source",
            {},
        ),
        "description": target.get(
            "description"
        ),
        "confidence": target.get(
            "confidence"
        ),
        "status": target.get(
            "status"
        ),
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("MARSWALK SCIENCE TARGET ANALYSIS ENGINE")
    print("=" * 70)

    registry, targets = load_targets()

    print()
    print("INPUTS")
    print("-" * 70)
    print(
        f"Target registry: {TARGET_REGISTRY}"
    )
    print(
        f"Science terrain: {SCIENCE_WINDOW}"
    )
    print(
        f"Science slope:   {SCIENCE_SLOPE}"
    )

    if not SCIENCE_WINDOW.exists():
        raise RuntimeError(
            f"Science window not found: {SCIENCE_WINDOW}"
        )

    if not SCIENCE_SLOPE.exists():
        raise RuntimeError(
            f"Science slope raster not found: {SCIENCE_SLOPE}"
        )

    print()
    print("TARGETS")
    print("-" * 70)
    print(
        f"Study area: "
        f"{registry.get('study_area', {}).get('name')}"
    )
    print(
        f"Target count: {len(targets)}"
    )

    with rasterio.open(
        SCIENCE_WINDOW
    ) as window_src:

        with rasterio.open(
            SCIENCE_SLOPE
        ) as slope_src:

            slope_raster = slope_src.read(1)

            print()
            print("SCIENCE TERRAIN")
            print("-" * 70)
            print(
                f"CRS:         {slope_src.crs}"
            )
            print(
                f"Resolution:  {slope_src.res}"
            )
            print(
                f"Dimensions:  "
                f"{slope_src.width} × "
                f"{slope_src.height}"
            )

            analyses = []

            for target in targets:

                print()
                print(
                    f"Analyzing: "
                    f"{target.get('name')}"
                )

                result = analyze_target(
                    target,
                    slope_src,
                    slope_raster,
                    window_src,
                )

                analyses.append(result)

                stats = result[
                    "slope_statistics_degrees"
                ]

                print(
                    f"Mean slope:   "
                    f"{stats['mean']:.3f}°"
                )

                print(
                    f"Median slope: "
                    f"{stats['median']:.3f}°"
                )

                print(
                    f"P95 slope:    "
                    f"{stats['p95']:.3f}°"
                )

                print(
                    f"Maximum:      "
                    f"{stats['maximum']:.3f}°"
                )

    # ========================================================
    # OUTPUT
    # ========================================================

    output = {
        "schema": {
            "name": (
                "MarsWalk Science Target Analysis"
            ),
            "version": "1.0",
        },

        "project": {
            "name": "MarsWalk",
            "study_area": registry.get(
                "study_area",
                {},
            ),
        },

        "analysis": {
            "purpose": (
                "Terrain characterization around "
                "registered science targets."
            ),
            "terrain_source": (
                "science_target_window.tif"
            ),
            "slope_source": (
                "science_slope_degrees.tif"
            ),
            "analysis_radius_m": (
                ANALYSIS_RADIUS_M
            ),
            "slope_thresholds_degrees": (
                SLOPE_THRESHOLDS
            ),
        },

        "targets": analyses,

        "scientific_status": {
            "classification": (
                "research_analysis"
            ),
            "operational_certification": False,
            "nasa_certification": False,
        },

        "limitations": [
            (
                "Slope statistics describe terrain "
                "geometry and do not establish rover "
                "mobility capability."
            ),
            (
                "Slope thresholds are analytical "
                "characterization thresholds, not "
                "vehicle-certified limits."
            ),
            (
                "Science-target selection requires "
                "independent scientific evidence and "
                "mission-specific validation."
            ),
            (
                "Operational mission use would require "
                "validated vehicle, terrain, hazard, "
                "communications, power, and navigation "
                "constraints."
            ),
        ],
    }

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT.write_text(
        json.dumps(
            output,
            indent=2,
        )
    )

    print()
    print("OUTPUT")
    print("-" * 70)
    print(OUTPUT)

    print()
    print(
        f"Analyzed targets: {len(analyses)}"
    )

    print()
    print("=" * 70)
    print(
        "SCIENCE TARGET ANALYSIS COMPLETE"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()
