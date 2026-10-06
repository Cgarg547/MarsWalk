from pathlib import Path
import sys

import numpy as np
import rasterio


def read_sample(raster_path, row, col):
    with rasterio.open(raster_path) as src:
        value = src.read(
            1,
            window=rasterio.windows.Window(
                col,
                row,
                1,
                1,
            ),
        )[0, 0]

        x, y = rasterio.transform.xy(
            src.transform,
            row,
            col,
        )

        return float(value), float(x), float(y)


def find_representative_cells(path):
    with rasterio.open(path) as src:

        data = src.read(
            1,
            masked=True,
        )

        values = data.compressed()

        if values.size == 0:
            raise ValueError(
                "No valid cells found."
            )

        percentiles = {
            "LOW": 10,
            "MEDIAN": 50,
            "HIGH": 90,
        }

        results = {}

        for label, percentile in percentiles.items():

            target = np.percentile(
                values,
                percentile,
            )

            difference = np.abs(
                data.filled(np.nan) - target
            )

            difference[
                ~np.isfinite(
                    data.filled(np.nan)
                )
            ] = np.inf

            row, col = np.unravel_index(
                np.argmin(difference),
                difference.shape,
            )

            value = float(
                data[row, col]
            )

            x, y = rasterio.transform.xy(
                src.transform,
                row,
                col,
            )

            results[label] = {
                "percentile": percentile,
                "target": target,
                "value": value,
                "row": row,
                "col": col,
                "x": x,
                "y": y,
            }

    return results


def inspect_component(
    path,
    row,
    col,
):

    with rasterio.open(path) as src:

        value = src.read(
            1,
            window=rasterio.windows.Window(
                col,
                row,
                1,
                1,
            ),
        )[0, 0]

        if value == src.nodata:
            return None

        return float(value)


def main():

    if len(sys.argv) != 2:

        print(
            "Usage:"
        )

        print(
            "python "
            "pipelines/terrain/"
            "terrain_cost_samples.py "
            "<terrain_cost>"
        )

        sys.exit(1)

    cost_path = Path(
        sys.argv[1]
    )

    if not cost_path.exists():

        print(
            f"ERROR: File does not exist: "
            f"{cost_path}"
        )

        sys.exit(1)

    base = cost_path.parent

    local_slope = (
        base /
        "slope_degrees.tif"
    )

    broad_slope = (
        base /
        "slope_20m.tif"
    )

    roughness = (
        base /
        "roughness_std_5m.tif"
    )

    scale_difference = (
        base /
        "slope_difference.tif"
    )

    component_paths = {
        "Local slope": local_slope,
        "Broad slope": broad_slope,
        "Roughness": roughness,
        "Scale difference": scale_difference,
    }

    print("=" * 60)
    print(
        "MARSWALK TERRAIN COST "
        "SPATIAL SANITY CHECK"
    )
    print("=" * 60)

    print()

    samples = find_representative_cells(
        cost_path
    )

    for label, sample in samples.items():

        print()
        print(
            f"{label} COST LOCATION"
        )

        print("-" * 60)

        print(
            f"Reference percentile: "
            f"{sample['percentile']}%"
        )

        print(
            f"Target cost: "
            f"{sample['target']:.6f}"
        )

        print(
            f"Actual cost: "
            f"{sample['value']:.6f}"
        )

        print(
            f"Raster row: "
            f"{sample['row']}"
        )

        print(
            f"Raster column: "
            f"{sample['col']}"
        )

        print(
            f"Projected X: "
            f"{sample['x']:.3f}"
        )

        print(
            f"Projected Y: "
            f"{sample['y']:.3f}"
        )

        print()
        print(
            "UNDERLYING TERRAIN VARIABLES"
        )

        for component, path in (
            component_paths.items()
        ):

            value = inspect_component(
                path,
                sample["row"],
                sample["col"],
            )

            if value is None:

                print(
                    f"{component:<20} "
                    f"NoData"
                )

            else:

                print(
                    f"{component:<20} "
                    f"{value:.6f}"
                )

    print()
    print("=" * 60)
    print(
        "SPATIAL SANITY CHECK COMPLETE"
    )
    print("=" * 60)


if __name__ == "__main__":
    main()