import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone

import rasterio


# ============================================================
# MARSWALK DATA PROVENANCE GENERATOR
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

ROUTING_DIR = (
    PROJECT_ROOT
    / "data"
    / "derived"
    / "jezero"
    / "routing"
)

TERRAIN_FILE = ROUTING_DIR / "terrain_cost_10m.tif"
CANDIDATE_DIR = ROUTING_DIR / "candidates"

OUTPUT_FILE = ROUTING_DIR / "provenance.json"


# ============================================================
# HELPERS
# ============================================================

def sha256_file(path):
    """Calculate SHA-256 checksum for reproducibility."""

    sha256 = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            sha256.update(chunk)

    return sha256.hexdigest()


def file_info(path):
    """Return basic metadata about a file."""

    if not path.exists():
        return None

    return {
        "filename": path.name,
        "relative_path": str(path.relative_to(PROJECT_ROOT)),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


# ============================================================
# TERRAIN METADATA
# ============================================================

def inspect_terrain():

    if not TERRAIN_FILE.exists():
        raise FileNotFoundError(
            f"Terrain raster not found: {TERRAIN_FILE}"
        )

    with rasterio.open(TERRAIN_FILE) as src:

        return {
            "filename": TERRAIN_FILE.name,
            "relative_path": str(
                TERRAIN_FILE.relative_to(PROJECT_ROOT)
            ),
            "width": src.width,
            "height": src.height,
            "resolution_m": [
                float(src.res[0]),
                float(src.res[1]),
            ],
            "crs": str(src.crs),
            "nodata": (
                float(src.nodata)
                if src.nodata is not None
                else None
            ),
            "bounds": {
                "left": float(src.bounds.left),
                "bottom": float(src.bounds.bottom),
                "right": float(src.bounds.right),
                "top": float(src.bounds.top),
            },
            "sha256": sha256_file(TERRAIN_FILE),
            "size_bytes": TERRAIN_FILE.stat().st_size,
        }


# ============================================================
# CANDIDATE ROUTES
# ============================================================

def inspect_candidate_routes():

    routes = {}

    route_files = {
        "SHORTEST": "route_shortest.csv",
        "BALANCED": "route_balanced.csv",
        "SAFE": "route_safe.csv",
        "VERY_SAFE": "route_very_safe.csv",
    }

    for strategy, filename in route_files.items():

        path = CANDIDATE_DIR / filename

        if path.exists():
            routes[strategy] = file_info(path)

    return routes


# ============================================================
# PROJECT METHODOLOGY
# ============================================================

def build_methodology():

    return {
        "study_area": "Jezero study area",
        "terrain_surface": {
            "type": "Derived terrain-cost raster",
            "filename": TERRAIN_FILE.name,
            "resolution": "10 m",
        },

        "routing": {
            "algorithm": "A*",
            "purpose": (
                "Terrain-aware path planning between a "
                "user-defined start and goal."
            ),
        },

        "candidate_strategies": {
            "SHORTEST": (
                "Minimum-distance route with terrain "
                "cost largely ignored."
            ),
            "BALANCED": (
                "Balances travel distance against "
                "terrain difficulty."
            ),
            "SAFE": (
                "Prioritizes lower terrain risk while "
                "limiting distance increase."
            ),
            "VERY_SAFE": (
                "Strongest terrain-risk avoidance "
                "among the evaluated routes."
            ),
        },

        "risk_analysis": {
            "terrain_statistics": [
                "mean",
                "median",
                "P90",
                "P95",
                "maximum",
            ],
            "exposure_thresholds": [
                0.50,
                0.70,
                0.85,
            ],
        },

        "mission_decision": {
            "description": (
                "Candidate routes are compared using "
                "distance and terrain-risk characteristics."
            ),
        },

        "travel_time": {
            "nominal_speed_m_per_s": 0.050,
            "note": (
                "Conceptual planning assumption used "
                "by the current MarsWalk prototype."
            ),
        },
    }


# ============================================================
# LIMITATIONS
# ============================================================

def build_limitations():

    return [
        (
            "MarsWalk is a research/demo terrain-routing "
            "system."
        ),
        (
            "The current decision score and terrain "
            "thresholds are conceptual."
        ),
        (
            "The nominal travel speed is a planning "
            "assumption rather than a validated rover "
            "mobility model."
        ),
        (
            "The current system does not constitute "
            "NASA-certified mobility, safety, or mission "
            "planning software."
        ),
        (
            "Additional validation against independent "
            "datasets and physical mobility constraints "
            "would be required for operational use."
        ),
    ]


# ============================================================
# BUILD PROVENANCE DOCUMENT
# ============================================================

def generate_provenance():

    print("=" * 64)
    print("MARSWALK DATA PROVENANCE GENERATOR")
    print("=" * 64)

    print()
    print("PROJECT")
    print("-" * 64)

    print(f"Project root: {PROJECT_ROOT}")
    print(f"Routing directory: {ROUTING_DIR}")

    print()
    print("TERRAIN")
    print("-" * 64)

    terrain = inspect_terrain()

    print(f"Raster:       {terrain['filename']}")
    print(
        f"Dimensions:   "
        f"{terrain['width']} × {terrain['height']}"
    )
    print(
        f"Resolution:   "
        f"{terrain['resolution_m'][0]} × "
        f"{terrain['resolution_m'][1]} m"
    )
    print(f"CRS:          {terrain['crs']}")
    print(f"NoData:       {terrain['nodata']}")

    print()
    print("CANDIDATE ROUTES")
    print("-" * 64)

    candidates = inspect_candidate_routes()

    for strategy, metadata in candidates.items():

        print(
            f"{strategy:<12} "
            f"{metadata['size_bytes']:,} bytes"
        )

    print()
    print("BUILDING PROVENANCE RECORD")
    print("-" * 64)

    provenance = {
        "schema": {
            "name": "MarsWalk Provenance Record",
            "version": "1.0",
        },

        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),

        "project": {
            "name": "MarsWalk",
            "purpose": (
                "Research/demo platform for terrain-aware "
                "planetary mobility planning."
            ),
            "study_area": "Jezero study area",
        },

        "terrain": terrain,

        "candidate_routes": candidates,

        "methodology": build_methodology(),

        "reproducibility": {
            "terrain_checksum": terrain["sha256"],
            "candidate_route_files": {
                strategy: metadata["sha256"]
                for strategy, metadata in candidates.items()
            },
            "checksum_algorithm": "SHA-256",
        },

        "limitations": build_limitations(),

        "scientific_status": {
            "classification": "Research/demo prototype",
            "operational_certification": False,
            "nasa_certification": False,
        },
    }

    OUTPUT_FILE.write_text(
        json.dumps(
            provenance,
            indent=2,
        )
    )

    print()
    print("OUTPUT")
    print("-" * 64)

    print(f"Provenance: {OUTPUT_FILE}")

    print()
    print("=" * 64)
    print("MARSWALK PROVENANCE GENERATION COMPLETE")
    print("=" * 64)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    generate_provenance()