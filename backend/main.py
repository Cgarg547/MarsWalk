from pathlib import Path
import csv
import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware


PROJECT_ROOT = Path(__file__).resolve().parent.parent

SCIENCE_DIR = (
    PROJECT_ROOT
    / "data"
    / "derived"
    / "jezero"
    / "science_routing"
)

ROUTES_DIR = SCIENCE_DIR / "routes"


app = FastAPI(
    title="MarsWalk API",
    description=(
        "Research/demo API for Mars terrain-aware "
        "science mission planning."
    ),
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_json(path: Path):
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {path}",
        )

    with open(path, "r") as f:
        return json.load(f)


def load_csv(path: Path):
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {path}",
        )

    with open(path, newline="") as f:
        return list(csv.DictReader(f))

def load_route(path: Path):
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Route not found: {path}",
        )

    with open(path, newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if len(rows) < 2:
        return []

    # Find the row containing x/y columns.
    header_index = None
    header = None

    for i, row in enumerate(rows):
        normalized = [
            value.strip().lower()
            for value in row
        ]

        if "x" in normalized and "y" in normalized:
            header_index = i
            header = normalized
            break

    if header_index is None:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Could not find x/y columns in "
                f"{path.name}."
            ),
        )

    x_index = header.index("x")
    y_index = header.index("y")

    sequence_index = (
        header.index("sequence")
        if "sequence" in header
        else None
    )

    points = []

    for i, row in enumerate(
        rows[header_index + 1:],
        start=0,
    ):
        if len(row) <= max(x_index, y_index):
            continue

        try:
            x = float(row[x_index])
            y = float(row[y_index])
        except (ValueError, TypeError):
            continue

        if sequence_index is not None:
            try:
                sequence = int(
                    float(row[sequence_index])
                )
            except (ValueError, TypeError):
                sequence = i
        else:
            sequence = i

        points.append(
            {
                "sequence": sequence,
                "x": x,
                "y": y,
            }
        )

    return points

@app.get("/")
def root():
    return {
        "name": "MarsWalk API",
        "version": "1.0.0",
        "status": "online",
        "purpose": (
            "Research/demo terrain-aware "
            "planetary mobility planning."
        ),
    }


@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "project": "MarsWalk",
    }


@app.get("/api/mission")
def mission():
    path = (
        SCIENCE_DIR
        / "complete_science_mission.json"
    )

    return load_json(path)


@app.get("/api/science-targets")
def science_targets():
    path = (
        ROUTES_DIR
        / "science_target_routes.csv"
    )

    return {
        "targets": load_csv(path)
    }


@app.get("/api/routes")
def routes():
    return {
        "wildcat": load_route(
            ROUTES_DIR
            / "route_to_wildcat_ridge.csv"
        ),
        "skinner": load_route(
            ROUTES_DIR
            / "route_to_skinner_ridge.csv"
        ),
        "wildcat_to_skinner": load_route(
            ROUTES_DIR
            / "route_wildcat_ridge_to_skinner_ridge.csv"
        ),
    }


@app.get("/api/complete-route")
def complete_route():
    path = (
        ROUTES_DIR
        / "complete_science_mission.csv"
    )

    return {
        "route": load_route(path)
    }


@app.get("/api/metadata")
def metadata():
    path = (
        SCIENCE_DIR
        / "science_routing_metadata.json"
    )

    return load_json(path)