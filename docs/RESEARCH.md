# Research notes

## Why an LOD1-style model

[OGC CityGML 3.0](https://www.ogc.org/standards/citygml/) provides a standard conceptual vocabulary for 3D city objects and levels of detail. A footprint extruded to one flat height is useful for broad urban morphology and obstruction experiments, but it should not be presented as a photorealistic digital twin. This repository therefore uses “LOD1-style” and does not claim CityGML schema conformance.

OpenStreetMap's [Simple 3D Buildings](https://wiki.openstreetmap.org/wiki/Simple_3D_buildings) model distinguishes building outlines from building parts and documents the relationship among `height`, `building:levels`, and roof attributes. This project currently models one flat prism per footprint or multipolygon part. Supporting detailed `building:part` volumes is a clear next step.

## Coordinate-system choice

The prototype used EPSG:3857 for metric-looking values. Web Mercator is convenient for web maps, but it is not the right basis for local area and distance analysis. [EPSG:32614](https://epsg.io/32614) is a metre-based UTM projected CRS covering longitudes 102°W to 96°W, which includes Dallas.

## Line of sight in urban geometry

Saboor et al., [“Probability of Line of Sight Evaluation in Urban Environments using 3D Simulator”](https://arxiv.org/abs/2303.03197), show why city geometry, relative positions, and elevation/azimuth matter when evaluating UAV-to-ground line of sight. Their work is broader and more physically motivated than this repository's binary prism test; it supports the decision to expose the actual geometry and sampling assumptions instead of reporting a generic probability.

Zheng and Chen, [“Geography-aware Optimal UAV 3D Placement for LOS Relaying: A Geometry Approach”](https://arxiv.org/abs/2209.15161), study placement in actual dense-city geometry rather than relying only on stochastic line-of-sight models. This project does not reproduce their optimization guarantees; it implements a small, transparent greedy coverage baseline suitable for inspecting the Dallas model.

## Path planning

The route experiment uses the classic A* formulation introduced by Hart, Nilsson, and Raphael, [“A Formal Basis for the Heuristic Determination of Minimum Cost Paths”](https://doi.org/10.1109/TSSC.1968.300136). Euclidean distance is admissible for the eight-neighbor grid with Euclidean step costs.

The current route is deliberately a 2D slice through a 2.5D obstacle field. A more serious research extension would use 3D motion primitives, uncertainty-aware clearance, terrain, and regulatory/airspace constraints.

## Data-quality direction

The dominant uncertainty is building height: 76.63% of current footprints lack an explicit height or usable levels tag. The deterministic fallback makes this uncertainty visible rather than disguising it with random variation.

Future validation could use public elevation sources such as the [USGS 3D Elevation Program](https://www.usgs.gov/3d-elevation-program), subject to acquisition, classification, and roof-height extraction work. That would support measured roof elevations, terrain, and error analysis rather than stronger-looking inference.

## Research boundaries

This repository demonstrates software engineering and computational-geometry methods. It is not evidence of:

- complete Dallas building coverage;
- survey-grade or cadastral geometry;
- measured height accuracy for inferred buildings;
- continuous or optimal visibility coverage;
- communications performance;
- safe, legal, or flyable UAV routes.
