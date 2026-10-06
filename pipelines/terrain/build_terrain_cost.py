from pathlib import Path
import sys

import numpy as np
import rasterio


def collect_values(path: Path) -> np.ndarray:
    """Collect finite valid raster values."""

    values = []

    with rasterio.open(path) as src:

        for _, window in src.block_windows(1):

            data = src.read(
                1,
                window=window,
                masked=True,
            )

            block = data.compressed()

            if block.size == 0:
                continue

            block = block[
                np.isfinite(block)
            ]

            if block.size:
                values.append(
                    block.astype(np.float32)
                )

    if not values:
        raise ValueError(
            f"No valid values found in {path}"
        )

    return np.concatenate(values)


def percentile_range(
    values: np.ndarray,
    lower: float = 5.0,
    upper: float = 95.0,
):
    """Calculate robust percentile bounds."""

    p_low = float(
        np.percentile(values, lower)
    )

    p_high = float(
        np.percentile(values, upper)
    )

    if p_high <= p_low:
        raise ValueError(
            f"Invalid percentile range: "
            f"{p_low} -> {p_high}"
        )

    return p_low, p_high


def normalize(
    data: np.ndarray,
    p_low: float,
    p_high: float,
):
    """Robust percentile normalization to [0,1]."""

    normalized = (
        (data - p_low)
        / (p_high - p_low)
    )

    normalized = np.clip(
        normalized,
        0.0,
        1.0,
    )

    return normalized


def build_cost_surface(
    local_slope_path: str,
    broad_slope_path: str,
    roughness_path: str,
    difference_path: str,
    output_path: str,
) -> None:

    local_path = Path(local_slope_path)
    broad_path = Path(broad_slope_path)
    roughness_path = Path(roughness_path)
    difference_path = Path(difference_path)
    output = Path(output_path)

    inputs = [
        local_path,
        broad_path,
        roughness_path,
        difference_path,
    ]

    for path in inputs:

        if not path.exists():

            print(
                f"ERROR: Missing input: {path}"
            )

            sys.exit(1)

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("=" * 60)
    print("MARSWALK TERRAIN COST MODEL")
    print("=" * 60)

    print()
    print("INPUTS")
    print("-" * 60)

    print(
        f"Local slope:       {local_path}"
    )

    print(
        f"Broad slope:       {broad_path}"
    )

    print(
        f"Roughness:         {roughness_path}"
    )

    print(
        f"Scale difference:  {difference_path}"
    )

    print()
    print("MODEL")
    print("-" * 60)

    print(
        "Local slope:       0.35"
    )

    print(
        "Broad slope:       0.25"
    )

    print(
        "Roughness:         0.25"
    )

    print(
        "Scale difference:  0.15"
    )

    print()
    print(
        "Normalization: "
        "5th-95th percentile"
    )

    # ------------------------------------------------------------
    # Calculate normalization statistics
    # ------------------------------------------------------------

    print()
    print("CALCULATING NORMALIZATION RANGES")
    print("-" * 60)

    datasets = {
        "local_slope": local_path,
        "broad_slope": broad_path,
        "roughness": roughness_path,
        "scale_difference": difference_path,
    }

    ranges = {}

    for name, path in datasets.items():

        print(
            f"Reading {name}..."
        )

        values = collect_values(path)

        p5, p95 = percentile_range(
            values
        )

        ranges[name] = (
            p5,
            p95,
        )

        print(
            f"  P05: {p5:.6f}"
        )

        print(
            f"  P95: {p95:.6f}"
        )

    # ------------------------------------------------------------
    # Confirm spatial compatibility
    # ------------------------------------------------------------

    print()
    print("CHECKING RASTER ALIGNMENT")
    print("-" * 60)

    with rasterio.open(
        local_path
    ) as reference:

        reference_profile = (
            reference.profile.copy()
        )

        reference_shape = (
            reference.height,
            reference.width,
        )

        reference_transform = (
            reference.transform
        )

        reference_crs = reference.crs

    for name, path in datasets.items():

        with rasterio.open(path) as src:

            shape = (
                src.height,
                src.width,
            )

            if shape != reference_shape:

                raise ValueError(
                    f"{name} shape mismatch: "
                    f"{shape} != "
                    f"{reference_shape}"
                )

            if src.transform != reference_transform:

                raise ValueError(
                    f"{name} transform mismatch."
                )

            if src.crs != reference_crs:

                raise ValueError(
                    f"{name} CRS mismatch: "
                    f"{src.crs} != "
                    f"{reference_crs}"
                )

            print(
                f"{name:<20} OK"
            )

    # ------------------------------------------------------------
    # Output profile
    # ------------------------------------------------------------

    profile = reference_profile

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

    # ------------------------------------------------------------
    # Process block by block
    # ------------------------------------------------------------

    print()
    print("BUILDING COST SURFACE")
    print("-" * 60)

    with rasterio.open(
        local_path
    ) as local_src, \
        rasterio.open(
            broad_path
        ) as broad_src, \
        rasterio.open(
            roughness_path
        ) as roughness_src, \
        rasterio.open(
            difference_path
        ) as difference_src, \
        rasterio.open(
            output,
            "w",
            **profile,
        ) as dst:

        total_blocks = 0

        for _, _ in local_src.block_windows(1):
            total_blocks += 1

        processed = 0

        for _, window in local_src.block_windows(1):

            local = local_src.read(
                1,
                window=window,
                masked=True,
            )

            broad = broad_src.read(
                1,
                window=window,
                masked=True,
            )

            roughness = roughness_src.read(
                1,
                window=window,
                masked=True,
            )

            difference = difference_src.read(
                1,
                window=window,
                masked=True,
            )

            # ------------------------------------------------
            # Combined validity mask
            # ------------------------------------------------

            valid = (
                ~local.mask
                & ~broad.mask
                & ~roughness.mask
                & ~difference.mask
            )

            # Convert to arrays.
            local_data = local.filled(
                np.nan
            ).astype(np.float32)

            broad_data = broad.filled(
                np.nan
            ).astype(np.float32)

            roughness_data = roughness.filled(
                np.nan
            ).astype(np.float32)

            difference_data = difference.filled(
                np.nan
            ).astype(np.float32)

            # ------------------------------------------------
            # Normalize each feature
            # ------------------------------------------------

            local_norm = normalize(
                local_data,
                *ranges["local_slope"],
            )

            broad_norm = normalize(
                broad_data,
                *ranges["broad_slope"],
            )

            roughness_norm = normalize(
                roughness_data,
                *ranges["roughness"],
            )

            difference_norm = normalize(
                difference_data,
                *ranges["scale_difference"],
            )

            # ------------------------------------------------
            # Weighted terrain cost
            # ------------------------------------------------

            cost = (
                0.35 * local_norm
                + 0.25 * broad_norm
                + 0.25 * roughness_norm
                + 0.15 * difference_norm
            )

            cost = cost.astype(
                np.float32
            )

            cost[~valid] = -9999.0

            dst.write(
                cost,
                1,
                window=window,
            )

            processed += 1

            progress = (
                processed
                / total_blocks
                * 100
            )

            if (
                processed == 1
                or processed == total_blocks
                or processed % 20 == 0
            ):

                print(
                    f"Progress: {progress:6.2f}%"
                )

    print()
    print(
        f"Output: {output}"
    )

    print()
    print("TERRAIN COST MODEL COMPLETE")
    print("=" * 60)


if __name__ == "__main__":

    if len(sys.argv) != 6:

        print(
            "Usage:"
        )

        print(
            "python "
            "pipelines/terrain/"
            "build_terrain_cost.py "
            "<local_slope> "
            "<broad_slope> "
            "<roughness> "
            "<slope_difference> "
            "<output>"
        )

        sys.exit(1)

    build_cost_surface(
        sys.argv[1],
        sys.argv[2],
        sys.argv[3],
        sys.argv[4],
        sys.argv[5],
    )