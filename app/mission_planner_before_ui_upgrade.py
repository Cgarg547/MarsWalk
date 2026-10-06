from pathlib import Path
import csv
import re
import math
import json

import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import xy
import streamlit as st
import plotly.graph_objects as go


# ============================================================
# MARSWALK INTERACTIVE MISSION PLANNER
# ============================================================

st.set_page_config(
    page_title="MarsWalk Mission Planner",
    page_icon="🚀",
    layout="wide",
)


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

ROUTING_DIR = (
    PROJECT_ROOT
    / "data"
    / "derived"
    / "jezero"
    / "routing"
)

TERRAIN_FILE = ROUTING_DIR / "terrain_cost_10m.tif"
CANDIDATE_DIR = ROUTING_DIR / "candidates"
DECISION_FILE = ROUTING_DIR / "final_mission_decision.txt"


# ============================================================
# ROUTE CONFIGURATION
# ============================================================

ROUTES = {
    "SHORTEST": {
        "file": "route_shortest.csv",
        "description": (
            "Minimum-distance route with terrain cost largely ignored."
        ),
    },
    "BALANCED": {
        "file": "route_balanced.csv",
        "description": (
            "Balances travel distance against terrain difficulty."
        ),
    },
    "SAFE": {
        "file": "route_safe.csv",
        "description": (
            "Prioritizes lower terrain risk while limiting "
            "distance increase."
        ),
    },
    "VERY_SAFE": {
        "file": "route_very_safe.csv",
        "description": (
            "Strongest terrain-risk avoidance among the "
            "evaluated routes."
        ),
    },
}


# ============================================================
# PAGE HEADER
# ============================================================

st.title("🚀 MarsWalk Mission Planner")

st.caption(
    "Terrain-aware route planning and mission decision support "
    "for the Jezero study area"
)

st.divider()


# ============================================================
# LOAD TERRAIN
# ============================================================

@st.cache_data
def load_terrain(path):

    with rasterio.open(path) as src:

        raster = src.read(1)

        transform = src.transform
        crs = src.crs
        nodata = src.nodata

        width = src.width
        height = src.height

        resolution = src.res

        bounds = src.bounds

    valid = np.isfinite(raster)

    if nodata is not None:
        valid &= raster != nodata

    return (
        raster,
        transform,
        crs,
        nodata,
        width,
        height,
        resolution,
        valid,
        bounds,
    )


# ============================================================
# LOAD ROUTE
# ============================================================

@st.cache_data
def load_route(path):

    points = []

    with open(path, "r", newline="") as f:

        reader = csv.reader(f)

        for row in reader:

            if not row:
                continue

            first = row[0].strip().lower()

            if first in {
                "marswalk route",
                "x",
                "x coordinate",
                "longitude",
            }:
                continue

            if len(row) < 2:
                continue

            try:

                x = float(row[0])
                y = float(row[1])

            except (ValueError, TypeError):
                continue

            points.append((x, y))

    return np.asarray(points, dtype=float)


# ============================================================
# DECISION FILE
# ============================================================

def parse_decision_file(path):

    result = {}

    if not path.exists():
        return result

    try:
        text = path.read_text()
    except Exception:
        return result

    patterns = {

        "recommended":
            r"Strategy:\s*([A-Z_]+)",

        "distance":
            r"Distance:\s*([0-9.]+)\s*m",

        "mean_cost":
            r"Mean terrain cost:\s*([0-9.]+)",

        "p90":
            r"P90 terrain cost:\s*([0-9.]+)",

        "exposure":
            r"Cost\s*>=\s*0\.70 exposure:\s*([0-9.]+)%",

        "risk":
            r"Risk score:\s*([0-9.]+)",

        "decision_score":
            r"Decision score:\s*([0-9.]+)",

        "travel_time":
            r"Estimated travel time:\s*([0-9.]+)\s*h",
    }

    for key, pattern in patterns.items():

        match = re.search(pattern, text)

        if not match:
            continue

        value = match.group(1)

        if key == "recommended":

            result[key] = value

        else:

            try:
                result[key] = float(value)
            except ValueError:
                pass

    return result


# ============================================================
# TERRAIN LOOKUP
# ============================================================

def terrain_value_at_xy(
    x,
    y,
    raster,
    transform,
    valid,
):

    try:

        row, col = rasterio.transform.rowcol(
            transform,
            x,
            y,
        )

        row = int(row)
        col = int(col)

        if (
            row < 0
            or row >= raster.shape[0]
            or col < 0
            or col >= raster.shape[1]
        ):
            return np.nan

        if not valid[row, col]:
            return np.nan

        return float(raster[row, col])

    except Exception:

        return np.nan


# ============================================================
# DENSIFY ROUTE
# ============================================================

def densify_route(route, spacing=5.0):

    """
    Creates additional points between route vertices.

    This prevents the terrain analysis from looking only at
    the original route vertices.
    """

    if len(route) < 2:
        return route.copy()

    dense_points = [route[0]]

    for i in range(len(route) - 1):

        start = route[i]
        end = route[i + 1]

        dx = end[0] - start[0]
        dy = end[1] - start[1]

        distance = math.sqrt(
            dx * dx + dy * dy
        )

        if distance <= 0:
            continue

        segments = max(
            1,
            int(math.ceil(distance / spacing)),
        )

        for j in range(1, segments + 1):

            t = j / segments

            point = (
                start
                + t * (end - start)
            )

            dense_points.append(point)

    return np.asarray(dense_points)


# ============================================================
# ROUTE METRICS
# ============================================================

def route_metrics(
    route,
    raster,
    transform,
    valid,
    sample_spacing=5.0,
):

    if len(route) < 2:

        return {
            "points": len(route),
            "sample_points": 0,
            "distance": 0.0,
            "mean": np.nan,
            "median": np.nan,
            "p90": np.nan,
            "p95": np.nan,
            "maximum": np.nan,
            "exposure70": np.nan,
            "exposure85": np.nan,
            "valid": 0,
        }

    # --------------------------------------------------------
    # ORIGINAL ROUTE DISTANCE
    # --------------------------------------------------------

    differences = np.diff(
        route,
        axis=0,
    )

    distances = np.sqrt(
        differences[:, 0] ** 2
        + differences[:, 1] ** 2
    )

    total_distance = float(
        distances.sum()
    )

    # --------------------------------------------------------
    # DENSIFIED ROUTE
    # --------------------------------------------------------

    dense_route = densify_route(
        route,
        spacing=sample_spacing,
    )

    terrain_values = []

    for x, y in dense_route:

        value = terrain_value_at_xy(
            x,
            y,
            raster,
            transform,
            valid,
        )

        if np.isfinite(value):

            terrain_values.append(value)

    terrain_values = np.asarray(
        terrain_values,
        dtype=float,
    )

    # --------------------------------------------------------
    # NO VALID TERRAIN
    # --------------------------------------------------------

    if len(terrain_values) == 0:

        return {
            "points": len(route),
            "sample_points": len(dense_route),
            "distance": total_distance,
            "mean": np.nan,
            "median": np.nan,
            "p90": np.nan,
            "p95": np.nan,
            "maximum": np.nan,
            "exposure70": np.nan,
            "exposure85": np.nan,
            "valid": 0,
        }

    # --------------------------------------------------------
    # TERRAIN STATISTICS
    # --------------------------------------------------------

    mean_cost = float(
        np.mean(terrain_values)
    )

    median_cost = float(
        np.median(terrain_values)
    )

    p90_cost = float(
        np.percentile(
            terrain_values,
            90,
        )
    )

    p95_cost = float(
        np.percentile(
            terrain_values,
            95,
        )
    )

    maximum_cost = float(
        np.max(terrain_values)
    )

    exposure70 = float(
        np.mean(
            terrain_values >= 0.70
        ) * 100
    )

    exposure85 = float(
        np.mean(
            terrain_values >= 0.85
        ) * 100
    )

    return {

        "points": len(route),

        "sample_points":
            len(dense_route),

        "distance":
            total_distance,

        "mean":
            mean_cost,

        "median":
            median_cost,

        "p90":
            p90_cost,

        "p95":
            p95_cost,

        "maximum":
            maximum_cost,

        "exposure70":
            exposure70,

        "exposure85":
            exposure85,

        "valid":
            len(terrain_values),
    }


# ============================================================
# RISK CLASSIFICATION
# ============================================================

def classify_risk(
    mean_cost,
    p90_cost,
    exposure70,
):

    if not np.isfinite(mean_cost):

        return "UNKNOWN"

    # Conservative interpretation:
    # multiple indicators are considered together.

    if (
        mean_cost >= 0.70
        or p90_cost >= 0.90
        or exposure70 >= 40
    ):

        return "CRITICAL"

    if (
        mean_cost >= 0.55
        or p90_cost >= 0.80
        or exposure70 >= 25
    ):

        return "HIGH"

    if (
        mean_cost >= 0.35
        or p90_cost >= 0.65
        or exposure70 >= 10
    ):

        return "MODERATE"

    return "LOW"


# ============================================================
# RISK DESCRIPTION
# ============================================================

def risk_description(risk):

    descriptions = {

        "LOW":
            "Low terrain-cost exposure along the evaluated route.",

        "MODERATE":
            "Moderate terrain difficulty; route remains operationally plausible.",

        "HIGH":
            "Elevated terrain-cost exposure; additional mission constraints should be considered.",

        "CRITICAL":
            "High terrain-cost exposure; route should be treated as a significant mobility-risk candidate.",

        "UNKNOWN":
            "Terrain risk could not be determined from the available raster data.",
    }

    return descriptions.get(
        risk,
        descriptions["UNKNOWN"],
    )


# ============================================================
# CHECK TERRAIN FILE
# ============================================================

if not TERRAIN_FILE.exists():

    st.error(
        "Terrain raster not found:\n\n"
        f"{TERRAIN_FILE}"
    )

    st.stop()


# ============================================================
# LOAD TERRAIN
# ============================================================

(
    raster,
    transform,
    crs,
    nodata,
    width,
    height,
    resolution,
    valid,
    bounds,
) = load_terrain(
    TERRAIN_FILE
)


# ============================================================
# LOAD DECISION
# ============================================================

decision = parse_decision_file(
    DECISION_FILE
)


# ============================================================
# LOAD ROUTES
# ============================================================

route_data = {}

for name, config in ROUTES.items():

    route_file = (
        CANDIDATE_DIR
        / config["file"]
    )

    if not route_file.exists():
        continue

    route = load_route(
        route_file
    )

    if len(route) < 2:
        continue

    metrics = route_metrics(
        route,
        raster,
        transform,
        valid,
        sample_spacing=max(
            2.0,
            min(
                float(resolution[0]),
                float(resolution[1]),
            ) / 2.0,
        ),
    )

    route_data[name] = {

        "route": route,

        "metrics": metrics,

        "description":
            config["description"],
    }


if not route_data:

    st.error(
        "No valid candidate route files were found."
    )

    st.stop()


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header(
    "🎛️ Mission Controls"
)


default_route = decision.get(
    "recommended",
    "VERY_SAFE",
)


if default_route not in route_data:

    default_route = list(
        route_data.keys()
    )[0]


selected_route = st.sidebar.selectbox(

    "Route strategy",

    list(
        route_data.keys()
    ),

    index=list(
        route_data.keys()
    ).index(
        default_route
    ),
)


show_all_routes = st.sidebar.checkbox(

    "Show all candidate routes",

    value=True,
)


show_terrain = st.sidebar.checkbox(

    "Show terrain cost",

    value=True,
)


st.sidebar.divider()


st.sidebar.subheader(
    "🛰️ Terrain Dataset"
)


st.sidebar.write(
    f"Raster: `{TERRAIN_FILE.name}`"
)


st.sidebar.write(
    "Resolution: "
    f"`{resolution[0]:.1f} × "
    f"{resolution[1]:.1f} m`"
)


st.sidebar.write(
    f"Raster size: `{width:,} × {height:,}`"
)


st.sidebar.write(
    f"Valid cells: `{int(valid.sum()):,}`"
)


st.sidebar.write(
    f"CRS: `{crs}`"
)


st.sidebar.divider()


st.sidebar.subheader(
    "⚙️ Mission Assumption"
)


TRAVEL_SPEED = 0.050


st.sidebar.write(
    f"Assumed travel speed: "
    f"`{TRAVEL_SPEED:.3f} m/s`"
)


st.sidebar.caption(
    "Travel-speed value is a conceptual demonstration "
    "assumption and is not a flight-qualified rover "
    "mobility model."
)


# ============================================================
# SELECTED ROUTE
# ============================================================

selected = route_data[
    selected_route
]

selected_route_points = selected[
    "route"
]

selected_metrics = selected[
    "metrics"
]


# ============================================================
# RECOMMENDED ROUTE
# ============================================================

recommended = decision.get(
    "recommended",
    selected_route,
)


if recommended not in route_data:

    recommended = selected_route


# ============================================================
# MISSION RECOMMENDATION
# ============================================================

if recommended == selected_route:

    st.success(
        f"🏆 **MarsWalk Recommendation: "
        f"{recommended}**"
    )

else:

    st.info(
        f"🏆 **MarsWalk Recommendation: "
        f"{recommended}**  \n"
        f"Currently viewing: **{selected_route}**"
    )


# ============================================================
# KPI ROW
# ============================================================

col1, col2, col3, col4, col5 = st.columns(5)


col1.metric(

    "Distance",

    f"{selected_metrics['distance'] / 1000:.3f} km",
)


col2.metric(

    "Mean Terrain Cost",

    (
        f"{selected_metrics['mean']:.3f}"
        if np.isfinite(
            selected_metrics["mean"]
        )
        else "N/A"
    ),
)


col3.metric(

    "P90 Cost",

    (
        f"{selected_metrics['p90']:.3f}"
        if np.isfinite(
            selected_metrics["p90"]
        )
        else "N/A"
    ),
)


col4.metric(

    "≥ 0.70 Exposure",

    (
        f"{selected_metrics['exposure70']:.2f}%"
        if np.isfinite(
            selected_metrics["exposure70"]
        )
        else "N/A"
    ),
)


col5.metric(

    "Terrain Risk",

    classify_risk(

        selected_metrics["mean"],

        selected_metrics["p90"],

        selected_metrics["exposure70"],
    ),
)


st.divider()


# ============================================================
# ROUTE MAP
# ============================================================

st.subheader(
    "🗺️ Mission Route Map"
)


fig = go.Figure()


# ============================================================
# TERRAIN MAP
# ============================================================

if show_terrain:

    terrain_display = (
        raster
        .astype(float)
        .copy()
    )

    terrain_display[
        ~valid
    ] = np.nan

    rows, cols = (
        terrain_display.shape
    )

    # Actual projected coordinates
    # corresponding to raster pixel centers.

    x_coords = np.asarray(
        [
            xy(
                transform,
                0,
                col,
                offset="center",
            )[0]

            for col in range(cols)
        ]
    )

    y_coords = np.asarray(
        [
            xy(
                transform,
                row,
                0,
                offset="center",
            )[1]

            for row in range(rows)
        ]
    )

    fig.add_trace(

        go.Heatmap(

            x=x_coords,

            y=y_coords,

            z=terrain_display,

            colorscale="Turbo",

            zmin=0,

            zmax=1,

            colorbar=dict(

                title="Terrain Cost",

                thickness=18,

            ),

            hovertemplate=(

                "Projected X: %{x:.1f}<br>"

                "Projected Y: %{y:.1f}<br>"

                "Terrain Cost: %{z:.3f}"

                "<extra></extra>"
            ),

            showscale=True,

            name="Terrain",
        )
    )


# ============================================================
# ROUTE STYLES
# ============================================================

route_styles = {

    "SHORTEST": {
        "width": 2,
        "dash": "dot",
    },

    "BALANCED": {
        "width": 2,
        "dash": "dash",
    },

    "SAFE": {
        "width": 3,
        "dash": "dashdot",
    },

    "VERY_SAFE": {
        "width": 4,
        "dash": "solid",
    },
}


# ============================================================
# ALL ROUTES
# ============================================================

if show_all_routes:

    for name, data in route_data.items():

        route = data["route"]

        style = route_styles.get(

            name,

            {
                "width": 2,
                "dash": "solid",
            },
        )

        is_selected = (
            name == selected_route
        )

        width_value = (
            7
            if is_selected
            else style["width"]
        )

        opacity_value = (
            1.0
            if is_selected
            else 0.45
        )

        fig.add_trace(

            go.Scatter(

                x=route[:, 0],

                y=route[:, 1],

                mode="lines",

                name=name,

                line=dict(

                    width=width_value,

                    dash=style["dash"],
                ),

                opacity=opacity_value,

                hovertemplate=(

                    f"<b>{name}</b><br>"

                    "X: %{x:.1f}<br>"

                    "Y: %{y:.1f}"

                    "<extra></extra>"
                ),
            )
        )


else:

    route = selected_route_points

    fig.add_trace(

        go.Scatter(

            x=route[:, 0],

            y=route[:, 1],

            mode="lines",

            name=selected_route,

            line=dict(
                width=7,
            ),

            hovertemplate=(

                f"<b>{selected_route}</b><br>"

                "X: %{x:.1f}<br>"

                "Y: %{y:.1f}"

                "<extra></extra>"
            ),
        )
    )


# ============================================================
# START / GOAL
# ============================================================

if len(selected_route_points) > 0:

    start = (
        selected_route_points[0]
    )

    goal = (
        selected_route_points[-1]
    )


    fig.add_trace(

        go.Scatter(

            x=[start[0]],

            y=[start[1]],

            mode="markers+text",

            name="START",

            marker=dict(

                size=15,

                symbol="circle",
            ),

            text=["START"],

            textposition="top center",

            hovertemplate=(

                "<b>MISSION START</b><br>"

                "X: %{x:.1f}<br>"

                "Y: %{y:.1f}"

                "<extra></extra>"
            ),
        )
    )


    fig.add_trace(

        go.Scatter(

            x=[goal[0]],

            y=[goal[1]],

            mode="markers+text",

            name="GOAL",

            marker=dict(

                size=17,

                symbol="diamond",
            ),

            text=["GOAL"],

            textposition="bottom center",

            hovertemplate=(

                "<b>MISSION GOAL</b><br>"

                "X: %{x:.1f}<br>"

                "Y: %{y:.1f}"

                "<extra></extra>"
            ),
        )
    )


# ============================================================
# MAP LAYOUT
# ============================================================

fig.update_layout(

    height=700,

    xaxis_title="Projected X",

    yaxis_title="Projected Y",

    xaxis=dict(
        showgrid=True,
    ),

    yaxis=dict(

        showgrid=True,

        scaleanchor="x",

        scaleratio=1,
    ),

    legend=dict(

        orientation="h",

        yanchor="bottom",

        y=1.02,

        xanchor="left",

        x=0,
    ),

    margin=dict(

        l=20,

        r=20,

        t=70,

        b=20,
    ),

    hovermode="closest",

)


st.plotly_chart(

    fig,

    use_container_width=True,
)


# ============================================================
# ROUTE COMPARISON
# ============================================================

st.subheader(
    "📊 Route Comparison"
)


comparison_rows = []


for name, data in route_data.items():

    metrics = data["metrics"]

    risk = classify_risk(

        metrics["mean"],

        metrics["p90"],

        metrics["exposure70"],
    )

    comparison_rows.append(

        {

            "Strategy":
                name,

            "Risk":
                risk,

            "Distance (km)":
                metrics["distance"] / 1000,

            "Mean Cost":
                metrics["mean"],

            "P90 Cost":
                metrics["p90"],

            "P95 Cost":
                metrics["p95"],

            "≥0.70 Exposure (%)":
                metrics["exposure70"],

            "≥0.85 Exposure (%)":
                metrics["exposure85"],

            "Route Points":
                metrics["points"],

            "Terrain Samples":
                metrics["sample_points"],
        }
    )


comparison_df = pd.DataFrame(
    comparison_rows
)


st.dataframe(

    comparison_df,

    use_container_width=True,

    hide_index=True,

    column_config={

        "Distance (km)":
            st.column_config.NumberColumn(
                format="%.3f"
            ),

        "Mean Cost":
            st.column_config.NumberColumn(
                format="%.3f"
            ),

        "P90 Cost":
            st.column_config.NumberColumn(
                format="%.3f"
            ),

        "P95 Cost":
            st.column_config.NumberColumn(
                format="%.3f"
            ),

        "≥0.70 Exposure (%)":
            st.column_config.NumberColumn(
                format="%.2f"
            ),

        "≥0.85 Exposure (%)":
            st.column_config.NumberColumn(
                format="%.2f"
            ),
    },
)


# ============================================================
# SELECTED ROUTE ASSESSMENT
# ============================================================

st.subheader(
    f"🔎 {selected_route} Route Assessment"
)


risk = classify_risk(

    selected_metrics["mean"],

    selected_metrics["p90"],

    selected_metrics["exposure70"],
)


st.info(
    f"**Terrain Risk Classification: {risk}** — "
    f"{risk_description(risk)}"
)


detail1, detail2 = st.columns(2)


# ============================================================
# TERRAIN DETAILS
# ============================================================

with detail1:

    st.markdown(
        "### 🏔️ Terrain"
    )

    st.write(
        f"**Mean cost:** "
        f"{selected_metrics['mean']:.4f}"
    )

    st.write(
        f"**Median cost:** "
        f"{selected_metrics['median']:.4f}"
    )

    st.write(
        f"**90th percentile:** "
        f"{selected_metrics['p90']:.4f}"
    )

    st.write(
        f"**95th percentile:** "
        f"{selected_metrics['p95']:.4f}"
    )

    st.write(
        f"**Maximum:** "
        f"{selected_metrics['maximum']:.4f}"
    )


# ============================================================
# EXPOSURE DETAILS
# ============================================================

with detail2:

    st.markdown(
        "### ⚠️ Exposure"
    )

    st.write(
        f"**Cost ≥ 0.70:** "
        f"{selected_metrics['exposure70']:.2f}%"
    )

    st.write(
        f"**Cost ≥ 0.85:** "
        f"{selected_metrics['exposure85']:.2f}%"
    )

    st.write(
        f"**Valid terrain samples:** "
        f"{selected_metrics['valid']:,}"
    )

    st.write(
        f"**Original route points:** "
        f"{selected_metrics['points']:,}"
    )

    st.write(
        f"**Densified terrain samples:** "
        f"{selected_metrics['sample_points']:,}"
    )


# ============================================================
# TRAVEL ESTIMATE
# ============================================================

estimated_hours = (

    selected_metrics["distance"]

    / TRAVEL_SPEED

    / 3600
)


st.metric(

    "Estimated Travel Time",

    f"{estimated_hours:.2f} h",
)


# ============================================================
# STRATEGY EXPLANATION
# ============================================================

st.info(

    f"**{selected_route}:** "
    f"{selected['description']}"
)


# ============================================================
# MISSION DECISION
# ============================================================

st.divider()


st.subheader(
    "🧠 MarsWalk Mission Decision"
)


decision_col1, decision_col2 = (
    st.columns(2)
)


# ============================================================
# DECISION SUMMARY
# ============================================================

with decision_col1:

    st.markdown(
        f"### 🏆 Recommended Strategy: "
        f"**{recommended}**"
    )

    if recommended in route_data:

        recommended_metrics = (
            route_data[
                recommended
            ]["metrics"]
        )

        recommended_risk = (
            classify_risk(

                recommended_metrics[
                    "mean"
                ],

                recommended_metrics[
                    "p90"
                ],

                recommended_metrics[
                    "exposure70"
                ],
            )
        )

        st.write(
            f"**Risk classification:** "
            f"{recommended_risk}"
        )

        st.write(
            f"**Distance:** "
            f"{recommended_metrics['distance'] / 1000:.3f} km"
        )

        st.write(
            f"**Mean terrain cost:** "
            f"{recommended_metrics['mean']:.3f}"
        )

        st.write(
            f"**P90 terrain cost:** "
            f"{recommended_metrics['p90']:.3f}"
        )

        st.write(
            f"**High-cost exposure:** "
            f"{recommended_metrics['exposure70']:.2f}%"
        )

    if decision:

        if "decision_score" in decision:

            st.write(
                f"**Decision score:** "
                f"{decision['decision_score']:.3f}"
            )

        if "risk" in decision:

            st.write(
                f"**Model risk score:** "
                f"{decision['risk']:.3f}"
            )

        if "travel_time" in decision:

            st.write(
                f"**Decision-file travel estimate:** "
                f"{decision['travel_time']:.2f} h"
            )


# ============================================================
# MISSION INTERPRETATION
# ============================================================

with decision_col2:

    st.markdown(
        "### 🛰️ Mission Interpretation"
    )

    if recommended == "VERY_SAFE":

        st.write(
            "MarsWalk prioritizes terrain-risk reduction "
            "over minimum travel distance. This strategy "
            "is appropriate when mobility reliability is "
            "more important than minimizing traverse length."
        )

    elif recommended == "SAFE":

        st.write(
            "MarsWalk identifies a strong compromise "
            "between terrain safety and travel distance."
        )

    elif recommended == "BALANCED":

        st.write(
            "MarsWalk selects a balanced tradeoff "
            "between route efficiency and terrain risk."
        )

    else:

        st.write(
            "The shortest route minimizes distance but "
            "accepts greater terrain exposure."
        )


# ============================================================
# DECISION LOGIC EXPLANATION
# ============================================================

st.markdown(
    "### 📐 Decision-Support Logic"
)

st.write(
    """
MarsWalk evaluates candidate routes using multiple
terrain-aware indicators rather than distance alone:

1. **Travel distance** — total route length.
2. **Mean terrain cost** — average terrain difficulty.
3. **P90 terrain cost** — conditions encountered in the
   more difficult portion of the route.
4. **P95 terrain cost** — near-worst-case terrain exposure.
5. **High-cost exposure** — percentage of sampled route
   points with terrain cost ≥ 0.70.
6. **Very-high-cost exposure** — percentage of sampled
   route points with terrain cost ≥ 0.85.

The resulting indicators support comparison between
SHORTEST, BALANCED, SAFE and VERY_SAFE strategies.
"""
)


# ============================================================
# DATA QUALITY
# ============================================================

st.divider()

st.subheader(
    "🔬 Data & Model Transparency"
)


quality_col1, quality_col2, quality_col3 = (
    st.columns(3)
)


with quality_col1:

    st.metric(
        "Terrain Resolution",
        f"{resolution[0]:.1f} m",
    )


with quality_col2:

    st.metric(
        "Valid Raster Cells",
        f"{int(valid.sum()):,}",
    )


with quality_col3:

    st.metric(
        "Coordinate System",
        str(crs),
    )

# ============================================================
# DATA & METHODOLOGY
# ============================================================

st.divider()

st.subheader("🔬 Data & Methodology")

st.markdown(
    """
MarsWalk uses a documented terrain-cost surface and a
terrain-aware routing pipeline to evaluate candidate
mobility paths within the Jezero study area.
"""
)

method_col1, method_col2, method_col3 = st.columns(3)


with method_col1:

    st.markdown("### 🗺️ Study Area")

    st.write("**Region:** Jezero study area")

    st.write(
        f"**Terrain raster:** "
        f"`{TERRAIN_FILE.name}`"
    )

    st.write(
        f"**Resolution:** "
        f"{resolution[0]:.1f} × "
        f"{resolution[1]:.1f} m"
    )

    st.write(
        f"**Dimensions:** "
        f"{width} × {height}"
    )


with method_col2:

    st.markdown("### 🧭 Routing")

    st.write("**Algorithm:** A*")

    st.write(
        "**Purpose:** Terrain-aware path planning "
        "between a defined start and goal."
    )

    st.write(
        "**Candidate strategies:** "
        "Shortest, Balanced, Safe, Very Safe"
    )


with method_col3:

    st.markdown("### 📊 Risk Model")

    st.write("**Statistics:** Mean, Median, P90, P95, Maximum")

    st.write(
        "**Exposure thresholds:** "
        "0.50, 0.70, 0.85"
    )

    st.write(
        "**Travel speed assumption:** "
        "0.050 m/s"
    )


# ============================================================
# DATA INTEGRITY
# ============================================================

st.subheader("🔐 Data Integrity & Reproducibility")

provenance_file = ROUTING_DIR / "provenance.json"


if provenance_file.exists():

    try:

        with open(provenance_file, "r") as f:
            provenance = json.load(f)

        terrain_provenance = provenance.get(
            "terrain",
            {}
        )

        candidate_provenance = provenance.get(
            "candidate_routes",
            {}
        )

        integrity_col1, integrity_col2 = st.columns(2)


        with integrity_col1:

            st.markdown("### Terrain Dataset")

            st.write(
                f"**File:** "
                f"`{terrain_provenance.get('filename', 'N/A')}`"
            )

            st.write(
                f"**SHA-256:** "
                f"`{terrain_provenance.get('sha256', 'N/A')}`"
            )

            st.write(
                f"**Size:** "
                f"{terrain_provenance.get('size_bytes', 0):,} bytes"
            )


        with integrity_col2:

            st.markdown("### Candidate Routes")

            for strategy, metadata in candidate_provenance.items():

                st.write(
                    f"**{strategy}:** "
                    f"`{metadata.get('sha256', 'N/A')}`"
                )


        with st.expander(
            "View complete provenance record"
        ):

            st.json(provenance)


    except Exception as exc:

        st.warning(
            f"Unable to read provenance record: {exc}"
        )

else:

    st.warning(
        "Provenance record not found. "
        "Run `generate_provenance.py` to create it."
    )


# ============================================================
# SCIENTIFIC STATUS
# ============================================================

st.subheader("🧪 Scientific Status")

status_col1, status_col2 = st.columns(2)


with status_col1:

    st.info(
        """
**Classification**

Research/demo prototype

MarsWalk is designed as a terrain-routing and
mission decision-support research platform.
"""
    )


with status_col2:

    st.warning(
        """
**Certification Status**

MarsWalk does **not** claim NASA certification,
operational certification, or flight/rover qualification.

The current model uses conceptual terrain thresholds,
decision scores, and travel-speed assumptions.
"""
    )


# ============================================================
# LIMITATIONS
# ============================================================

st.subheader("⚠️ Current Limitations")

limitations = [
    "Terrain thresholds are conceptual.",
    "The travel-speed assumption is not a validated rover mobility model.",
    "The current decision model is a research/demo implementation.",
    "Operational use would require independent validation.",
    "Additional physical mobility constraints would be required for a flight-qualified system.",
]

for limitation in limitations:

    st.write(f"• {limitation}")

# ============================================================
# LIMITATION
# ============================================================

st.divider()

st.caption(
    "MarsWalk is a research/demo terrain-routing and "
    "mission-decision-support system. Terrain thresholds, "
    "decision scores, route classifications and travel-speed "
    "assumptions are conceptual and are not NASA-certified "
    "mobility, safety, navigation or mission-planning models."
)