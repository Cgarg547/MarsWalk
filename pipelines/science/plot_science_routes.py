from pathlib import Path

import csv
import numpy as np
import matplotlib.pyplot as plt
import rasterio
from rasterio.plot import plotting_extent


# ============================================================
# PATHS
# ============================================================

COST_RASTER = Path(
    "data/derived/jezero/science_routing/"
    "science_routing_cost.tif"
)

ROUTE_DIR = Path(
    "data/derived/jezero/science_routing/routes"
)

OUTPUT = ROUTE_DIR / "science_target_routes.png"


# ============================================================
# TARGETS
# ============================================================

TARGETS = {
    "Wildcat Ridge": (
        4591336.864,
        1091003.562,
    ),
    "Skinner Ridge": (
        4591354.646,
        1091020.159,
    ),
}


START = (
    4588522.364,
    1093977.659,
)


# ============================================================
# ROUTE LOADER
# ============================================================

def load_route(path):

    coordinates = []

    with open(path, newline="") as f:

        reader = csv.reader(f)
        rows = list(reader)

    for row in rows[2:]:

        if len(row) < 2:
            continue

        try:
            x = float(row[0])
            y = float(row[1])
        except ValueError:
            continue

        coordinates.append((x, y))

    if not coordinates:
        raise RuntimeError(
            f"No coordinates found in {path}"
        )

    return np.asarray(
        coordinates,
        dtype=float,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("MARSWALK SCIENCE ROUTE VISUALIZATION")
    print("=" * 70)

    wildcat_file = (
        ROUTE_DIR /
        "route_to_wildcat_ridge.csv"
    )

    skinner_file = (
        ROUTE_DIR /
        "route_to_skinner_ridge.csv"
    )

    print()
    print("INPUT")
    print("-" * 70)

    print("Cost raster:", COST_RASTER)
    print("Wildcat route:", wildcat_file)
    print("Skinner route:", skinner_file)

    wildcat = load_route(wildcat_file)
    skinner = load_route(skinner_file)

    print()
    print("ROUTES")
    print("-" * 70)

    print(
        "Wildcat points:",
        len(wildcat),
    )

    print(
        "Skinner points:",
        len(skinner),
    )

    with rasterio.open(COST_RASTER) as src:

        cost = src.read(1)

        nodata = src.nodata

        if nodata is not None:

            valid = (
                np.isfinite(cost)
                & (cost != nodata)
            )

        else:

            valid = np.isfinite(cost)

        extent = plotting_extent(
            src
        )

        print()
        print("RASTER")
        print("-" * 70)

        print("CRS:", src.crs)
        print("Resolution:", src.res)
        print("Dimensions:", src.width, "×", src.height)
        print("Bounds:", src.bounds)

    # --------------------------------------------------------
    # Mask invalid values
    # --------------------------------------------------------

    display_cost = np.where(
        valid,
        cost,
        np.nan,
    )

    # --------------------------------------------------------
    # Figure
    # --------------------------------------------------------

    fig, ax = plt.subplots(
        figsize=(13, 10)
    )

    image = ax.imshow(
        display_cost,
        extent=extent,
        origin="upper",
        cmap="terrain",
        vmin=0.0,
        vmax=1.0,
    )

    colorbar = fig.colorbar(
        image,
        ax=ax,
        shrink=0.82,
    )

    colorbar.set_label(
        "Terrain Routing Cost"
    )

    # --------------------------------------------------------
    # Plot routes
    # --------------------------------------------------------

    ax.plot(
        wildcat[:, 0],
        wildcat[:, 1],
        linewidth=2.2,
        label="Route → Wildcat Ridge",
    )

    ax.plot(
        skinner[:, 0],
        skinner[:, 1],
        linewidth=2.2,
        label="Route → Skinner Ridge",
    )

    # --------------------------------------------------------
    # Start point
    # --------------------------------------------------------

    ax.scatter(
        START[0],
        START[1],
        s=100,
        marker="o",
        edgecolor="black",
        linewidth=1.2,
        zorder=5,
        label="Mission Start",
    )

    ax.annotate(
        "Mission Start",
        xy=START,
        xytext=(10, 10),
        textcoords="offset points",
        fontsize=10,
        fontweight="bold",
    )

    # --------------------------------------------------------
    # Science targets
    # --------------------------------------------------------

    for name, (x, y) in TARGETS.items():

        ax.scatter(
            x,
            y,
            s=130,
            marker="*",
            edgecolor="black",
            linewidth=1.2,
            zorder=6,
        )

        ax.annotate(
            name,
            xy=(x, y),
            xytext=(10, -15),
            textcoords="offset points",
            fontsize=10,
            fontweight="bold",
        )

    # --------------------------------------------------------
    # Labels
    # --------------------------------------------------------

    ax.set_title(
        "MarsWalk Science-Target Routing\n"
        "Jezero Crater",
        fontsize=16,
        fontweight="bold",
        pad=15,
    )

    ax.set_xlabel(
        "Projected X (m)"
    )

    ax.set_ylabel(
        "Projected Y (m)"
    )

    ax.legend(
        loc="best",
        frameon=True,
    )

    ax.grid(
        alpha=0.25
    )

    # --------------------------------------------------------
    # Equal spatial scale
    # --------------------------------------------------------

    ax.set_aspect(
        "equal",
        adjustable="box",
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    plt.tight_layout()

    plt.savefig(
        OUTPUT,
        dpi=220,
        bbox_inches="tight",
    )

    plt.close()

    print()
    print("OUTPUT")
    print("-" * 70)

    print(
        "Visualization:",
        OUTPUT,
    )

    print()
    print("=" * 70)
    print("SCIENCE ROUTE VISUALIZATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
