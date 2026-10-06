# 🚀 MarsWalk

### Interplanetary Science Mission Planning & Terrain-Aware Rover Routing

MarsWalk is a research and demonstration platform for planning rover missions across the Martian surface using terrain-aware routing, science-target analysis, risk scoring, and geospatial data.

The current project focuses on the **Jezero study area** and demonstrates how terrain information and science objectives can be combined to generate and evaluate a conceptual rover mission route.

> **Project status:** Core science-routing and mission-planning pipeline implemented. Frontend restoration and final integration are currently in progress.

---

## 🎯 Project Goal

The goal of MarsWalk is to create a system that can answer questions such as:

- Where should a rover travel?
- Which science targets should it visit?
- What route minimizes terrain-related cost?
- How difficult or risky is a proposed route?
- How can multiple science targets be connected into one mission?
- How can the resulting mission be presented through an interactive planning interface?

The system is designed as a **research/demo platform**, not as flight-certified rover navigation software.

---

# 🛰️ Current Mission Concept

The current science mission focuses on the **Jezero study area** and includes a conceptual sequence:

```text
Mission Start
     ↓
Wildcat Ridge
     ↓
Skinner Ridge
```

The routing system uses derived terrain/science cost information to evaluate the mission route.

---

# 🧠 What Has Been Implemented

## 1. Project Architecture

The repository has been organized into separate components for:

```text
MarsWalk/
│
├── api/
├── app/
├── backend/
├── challenges/
├── data/
├── docs/
├── pipelines/
│   ├── metadata/
│   ├── mission/
│   ├── routing/
│   ├── science/
│   ├── terrain/
│   └── validate/
├── scripts/
├── requirements.txt
└── README.md
```

This separates application code, scientific processing, routing, terrain analysis, documentation, and validation.

---

# 🗺️ Terrain Processing

MarsWalk contains a terrain-processing pipeline designed to derive information needed for rover routing.

Implemented components include:

- Terrain slope derivation
- Multiscale slope analysis
- Roughness derivation
- Robust roughness analysis
- Slope-difference analysis
- Terrain statistics
- Roughness statistics
- Slope statistics
- Terrain-cost sampling
- Terrain-cost validation
- Raster validation

The resulting terrain information can be incorporated into routing-cost calculations.

---

# 🧭 Routing System

A terrain-aware routing pipeline has been implemented.

Current routing components include:

- Routing-window creation
- Routing-grid construction
- Graph generation
- A* route calculation
- Route candidate generation
- Route comparison
- Route metrics
- Route plotting
- Route-comparison plotting

The routing architecture is intended to allow routes to be evaluated using terrain-related costs rather than simply using straight-line distance.

---

# 🔬 Science Target Routing

MarsWalk includes a dedicated science-routing pipeline.

Implemented components include:

- Science target loading
- Target validation
- Science routing-window creation
- Science slope derivation
- Science routing-cost generation
- Routing between science targets
- Individual science-target route generation
- Science-target analysis
- Target scoring
- Science-route plotting
- Complete science-mission construction

The current mission products include routes toward:

- **Wildcat Ridge**
- **Skinner Ridge**

and a combined mission route connecting the science targets.

---

# 📊 Mission Analysis

Mission-level analysis has also been implemented.

The project contains modules for:

- Mission planning
- Mission risk analysis
- Mission decision-making
- Mission dashboard generation
- Final mission plotting

The mission planner currently calculates metrics such as:

- Total route distance
- Conceptual travel time
- Route-point count
- Terrain cost
- Mean terrain cost
- Median terrain cost
- P90 terrain cost
- P95 terrain cost
- Maximum terrain cost
- High-cost terrain exposure
- Overall conceptual mission risk score

---

# 🖥️ Mission Planner Frontend

MarsWalk includes a Streamlit-based mission-planning interface:

```text
app/mission_planner.py
```

The intended interface contains:

- MarsWalk mission header
- Mission status
- Mission overview
- Mission metrics
- Mission sequence
- Interactive mission route visualization
- Science target analysis
- Terrain-risk profile
- Terrain-cost profile
- Mission recommendation
- Model-status/scientific disclaimer
- Sidebar/navigation functionality from the original interface

### Current frontend status

The frontend has undergone several iterations and the current version does **not yet fully reproduce the original working interface**.

A previously created **legacy version** of the mission planner is available and serves as the known-good UI/reference implementation.

Therefore, the next frontend task is **restoration rather than redesign from scratch**.

The legacy implementation should be treated as the baseline for:

- Sidebar
- Navigation
- Layout
- Existing controls
- Visual styling
- Interactive features
- Existing mission-planning functionality

---

# 📁 Data & Scientific Products

The repository currently tracks project metadata and scientific configuration files, including:

```text
data/
└── metadata/
    ├── data_registry.yaml
    ├── jezero_hirise_dtm.yaml
    └── science/
        └── targets.yaml
```

Large raw/generated datasets are intentionally excluded from Git where appropriate through `.gitignore`.

This prevents the repository from becoming unnecessarily large while keeping the source code and project metadata version-controlled.

---

# 📚 Documentation

Current documentation includes:

```text
docs/
├── architecture.md
├── data-provenance.md
├── scientific-limitations.md
└── scoring-methodology.md
```

These documents describe the project's:

- Architecture
- Data sources/provenance
- Scientific limitations
- Routing/scoring methodology

---

# 🧪 Validation

A validation structure is already present in the repository.

Current validation-related components include:

```text
scripts/test_environment.py
```

and:

```text
pipelines/validate/
└── validate_raster.py
```

The project environment has also been successfully configured with a Python virtual environment.

The current Streamlit environment has been verified to run with:

```text
Streamlit 1.65.0
```

---

# 🐙 GitHub Repository

The project is now version-controlled with Git and has been pushed to GitHub.

Repository:

**MarsWalk**

https://github.com/Cgarg547/MarsWalk

Current branch:

```text
main
```

The initial project checkpoint has been committed and pushed successfully.

This provides a stable baseline before continuing frontend development.

---

# 🔄 Current Development Status

## ✅ Completed

- [x] MarsWalk project structure
- [x] Git repository initialization
- [x] GitHub repository connection
- [x] Initial Git commit
- [x] Initial GitHub push
- [x] Python environment
- [x] Project requirements
- [x] Terrain-processing pipeline
- [x] Terrain-cost generation
- [x] Terrain validation tools
- [x] Routing grid
- [x] Graph construction
- [x] A* routing
- [x] Route candidate generation
- [x] Route comparison
- [x] Route metrics
- [x] Science target loading
- [x] Science target validation
- [x] Science-target routing
- [x] Wildcat Ridge route
- [x] Skinner Ridge route
- [x] Complete science mission route
- [x] Science target analysis
- [x] Mission risk calculations
- [x] Mission decision logic
- [x] Mission plotting
- [x] Streamlit mission-planner foundation
- [x] Scientific limitations/disclaimer
- [x] Project documentation foundation
- [x] Known-good legacy frontend identified
- [x] Working GitHub checkpoint created

---

# 🚧 Remaining Work

## 1. Restore the Original Frontend

This is currently the highest priority.

The current `mission_planner.py` interface needs to be brought back to the functionality and appearance of the legacy version.

### Requirements

- [ ] Restore original sidebar
- [ ] Restore original navigation
- [ ] Restore all previous frontend controls
- [ ] Restore original layout
- [ ] Restore original interactive features
- [ ] Restore route visualization
- [ ] Restore target-selection functionality
- [ ] Restore original styling
- [ ] Verify Streamlit renders HTML correctly
- [ ] Remove any raw HTML appearing as text
- [ ] Ensure all components render properly

**Important:** The legacy file should be used as the reference implementation rather than continuing to make blind changes to the current frontend.

---

# 🔧 Frontend Integration

After restoring the legacy interface:

- [ ] Connect the restored UI to the current science-routing products
- [ ] Verify all file paths
- [ ] Verify route loading
- [ ] Verify raster loading
- [ ] Verify target loading
- [ ] Verify risk calculations
- [ ] Verify interactive maps
- [ ] Verify mission metrics
- [ ] Verify sidebar controls
- [ ] Verify error handling

---

# 🧪 End-to-End Testing

The complete workflow needs to be tested from the scientific data through to the user interface.

Target workflow:

```text
Terrain Data
     ↓
Terrain Processing
     ↓
Terrain Cost
     ↓
Routing Grid
     ↓
A* Routing
     ↓
Science Target Routing
     ↓
Complete Mission
     ↓
Risk Analysis
     ↓
Mission Decision
     ↓
Interactive Frontend
```

Testing should confirm that each stage produces the expected output for the next stage.

---

# 📈 Final Mission Dashboard

The final dashboard should provide a clear mission-planning experience showing:

### Mission Overview

- Mission distance
- Estimated travel time
- Number of route points
- Terrain/risk score
- Terrain resolution

### Mission Route

Interactive visualization showing:

```text
START
  ↓
WILDCAT RIDGE
  ↓
SKINNER RIDGE
```

### Science Targets

For each target:

- Distance
- Travel time
- Mean terrain cost
- P90 terrain cost
- Maximum terrain cost
- High-cost exposure

### Terrain Risk

Display:

- Mean
- Median
- P90
- P95
- Maximum
- High-cost exposure

### Mission Recommendation

Present the final conceptual route and explain the terrain/risk characteristics that influenced the decision.

---

# 🔬 Scientific Improvements

Future versions can improve the scientific realism of the model.

Potential improvements include:

- More physically meaningful rover mobility constraints
- Better terrain-cost calibration
- Improved slope/roughness modeling
- Rover-specific traversability models
- Energy consumption modeling
- Solar/communication constraints
- Science-priority optimization
- Time-window constraints
- Multi-objective route optimization
- Uncertainty analysis
- Alternative route generation
- Sensitivity analysis of risk weights

These improvements should be clearly separated from the current research/demo assumptions.

---

# ⚠️ Scientific Disclaimer

MarsWalk is currently a **research and demonstration system**.

Its:

- terrain costs,
- rover-speed assumptions,
- risk weights,
- thresholds,
- route decisions,
- mission metrics

are conceptual engineering assumptions.

They are **not NASA-certified operational parameters** and should not be interpreted as flight-qualified rover navigation data.

The purpose of the system is to demonstrate a reproducible approach to terrain-aware science mission planning.

---

# 🏗️ Planned Development Roadmap

## Phase 1 — Baseline
**Status: Completed**

- Establish project structure
- Implement terrain processing
- Implement routing
- Implement science-target routing
- Generate mission products
- Create documentation
- Establish GitHub repository

## Phase 2 — Frontend Restoration
**Status: In Progress**

- Restore legacy UI
- Restore sidebar
- Restore navigation
- Restore interactive functionality
- Fix rendering
- Connect current science products

## Phase 3 — Integration
**Planned**

- End-to-end pipeline testing
- UI/data integration
- Error handling
- Performance improvements
- Reproducibility testing

## Phase 4 — Scientific Enhancement
**Planned**

- Improved rover model
- Better terrain modeling
- Energy constraints
- Communication constraints
- Science-priority optimization
- Uncertainty analysis

## Phase 5 — Hackathon Demo
**Planned**

- Finalize UI
- Prepare mission story
- Create demo workflow
- Prepare architecture diagram
- Prepare technical explanation
- Prepare scientific limitations
- Prepare live demonstration
- Prepare presentation/demo video

---

# 🚀 Vision

MarsWalk aims to demonstrate how planetary terrain data, science objectives, and algorithmic route planning can be combined into an interactive mission-planning system.

The long-term vision is a platform where a user can select:

```text
Science Objectives
        +
Rover Constraints
        +
Terrain Data
        +
Mission Constraints
        ↓
MarsWalk
        ↓
Candidate Mission Plans
        ↓
Risk / Cost / Science Analysis
        ↓
Recommended Mission Route
```

The current implementation establishes the core foundation for this workflow.

---

## Repository

**GitHub:**  
https://github.com/Cgarg547/MarsWalk

**Current branch:** `main`

**Current milestone:**  
Core science-routing pipeline completed → frontend restoration in progress.