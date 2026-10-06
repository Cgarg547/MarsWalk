from pathlib import Path

import numpy as np
import rasterio


INPUT = Path(
    "data/derived/jezero/science_routing/"
    "science_routing_terrain.tif"
)

OUTPUT = Path(
    "data/derived/jezero/science_routing/"
    "science_routing_cost.tif"
)


def normalize(values):
    finite = np.isfinite(values)

    if not finite.any():
        raise RuntimeError(
            "No finite values available for normalization."
        )

    vmin = np.nanpercentile(
        values[finite],
        2,
    )

    vmax = np.nanpercentile(
        values[finite],
        98,
    )

    if vmax <= vmin:
        return np.zeros_like(values)

    normalized = (
        (values - vmin)
        / (vmax - vmin)
    )

    return np.clip(
        normalized,
        0.0,
        1.0,
    )


def main():

    print("=" * 70)
    print("MARSWALK SCIENCE ROUTING COST BUILDER")
    print("=" * 70)

    print()
    print("INPUT")
    print("-" * 70)
    print(INPUT)

    if not INPUT.exists():
        raise FileNotFoundError(
            f"Input does not exist: {INPUT}"
        )

    with rasterio.open(INPUT) as src:

        elevation = src.read(
            1,
            masked=True,
        ).filled(np.nan).astype(
            np.float64
        )

        profile = src.profile.copy()

        transform = src.transform
        resolution = float(
            abs(transform.a)
        )

        print()
        print("TERRAIN")
        print("-" * 70)
        print("CRS:", src.crs)
        print("Width:", src.width)
        print("Height:", src.height)
        print("Resolution:", src.res)
        print("NoData:", src.nodata)

    valid = np.isfinite(elevation)

    if not valid.any():
        raise RuntimeError(
            "Terrain contains no valid cells."
        )

    # ------------------------------------------------------
    # Derive local terrain gradient
    # ------------------------------------------------------

    print()
    print("DERIVING TERRAIN GRADIENT")
    print("-" * 70)

    gy, gx = np.gradient(
        elevation,
        resolution,
        resolution,
    )

    gradient_magnitude = np.sqrt(
        gx ** 2 +
        gy ** 2
    )

    slope_degrees = np.degrees(
        np.arctan(
            gradient_magnitude
        )
    )

    slope_degrees[
        ~valid
    ] = np.nan

    # ------------------------------------------------------
    # Normalize slope
    # ------------------------------------------------------

    slope_cost = normalize(
        slope_degrees
    )

    # ------------------------------------------------------
    # Local roughness
    #
    # Approximation based on deviation from a 3x3
    # neighborhood mean.
    # ------------------------------------------------------

    print()
    print("DERIVING LOCAL ROUGHNESS")
    print("-" * 70)

    padded = np.pad(
        elevation,
        1,
        mode="edge",
    )

    neighborhood_sum = np.zeros_like(
        elevation
    )

    count = np.zeros_like(
        elevation,
        dtype=np.float64,
    )

    for dr in range(3):
        for dc in range(3):

            window = padded[
                dr:dr + elevation.shape[0],
                dc:dc + elevation.shape[1],
            ]

            finite = np.isfinite(window)

            neighborhood_sum[
                finite
            ] += window[finite]

            count[
                finite
            ] += 1.0

    neighborhood_mean = np.divide(
        neighborhood_sum,
        count,
        out=np.full_like(
            elevation,
            np.nan,
        ),
        where=count > 0,
    )

    roughness = np.abs(
        elevation -
        neighborhood_mean
    )

    roughness[
        ~valid
    ] = np.nan

    roughness_cost = normalize(
        roughness
    )

    # ------------------------------------------------------
    # Combined science-routing cost
    #
    # 70% slope
    # 30% roughness
    # ------------------------------------------------------

    cost = (
        0.70 * slope_cost
        +
        0.30 * roughness_cost
    )

    cost[
        ~valid
    ] = -9999.0

    # ------------------------------------------------------
    # Write raster
    # ------------------------------------------------------

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    profile.update(
        dtype="float32",
        count=1,
        nodata=-9999.0,
        compress="deflate",
        tiled=False,
    )

    with rasterio.open(
        OUTPUT,
        "w",
        **profile,
    ) as dst:

        dst.write(
            cost.astype(
                np.float32
            ),
            1,
        )

    valid_cost = cost[
        cost != -9999.0
    ]

    print()
    print("OUTPUT")
    print("-" * 70)
    print(OUTPUT)

    print()
    print("COST STATISTICS")
    print("-" * 70)
    print(
        f"Minimum: {np.min(valid_cost):.6f}"
    )
    print(
        f"Mean:    {np.mean(valid_cost):.6f}"
    )
    print(
        f"Median:  {np.median(valid_cost):.6f}"
    )
    print(
        f"P95:     {np.percentile(valid_cost, 95):.6f}"
    )
    print(
        f"Maximum: {np.max(valid_cost):.6f}"
    )

    print()
    print("=" * 70)
    print(
        "SCIENCE ROUTING COST BUILD COMPLETE"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()