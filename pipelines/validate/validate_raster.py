from pathlib import Path
import sys

import rasterio


def validate_raster(path: str) -> None:
    raster_path = Path(path)

    if not raster_path.exists():
        print(f"ERROR: File does not exist: {raster_path}")
        sys.exit(1)

    print("=" * 60)
    print("MARSWALK RASTER VALIDATION")
    print("=" * 60)

    with rasterio.open(raster_path) as src:
        print(f"File:              {raster_path}")
        print(f"Driver:            {src.driver}")
        print(f"Width:             {src.width}")
        print(f"Height:            {src.height}")
        print(f"Bands:             {src.count}")
        print(f"Data type:         {src.dtypes}")
        print(f"CRS:               {src.crs}")
        print(f"Resolution:        {src.res}")
        print(f"Bounds:            {src.bounds}")
        print(f"NoData:            {src.nodata}")
        print(f"Transform:         {src.transform}")

        print()
        print("MARSWALK VALIDATION COMPLETE")
        print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage:")
        print("python pipelines/validate/validate_raster.py <raster_file>")
        sys.exit(1)

    validate_raster(sys.argv[1])