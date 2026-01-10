# Dallas 3D City Model for UAV Visibility and Coverage Experiments

This repository contains a 3D geometric model of a portion of downtown Dallas, built to support research on UAV navigation, visibility, and camera placement in urban environments.

The goal of this project is to construct a simplified but realistic city model that can be used to simulate and study geometric coverage problems in 3D, inspired by city guarding and camera placement results from computational geometry.

## Project Overview

- Real-world city data sourced from OpenStreetMap (OSM)
- Buildings modeled as vertical prisms with uniform height (initially 25 meters)
- Study area focused on the Downtown Dallas Central Business District (CBD)
- Designed to be suitable for simulation, visualization, and presentation

This model serves as the first step toward experimenting with:
- Camera placement on buildings
- Coverage of free space / airspace
- Planned UAV navigation from point A to point B in urban settings

## Repository Structure

dallas-3d-city-model/
├── data/
│ ├── raw/ # Raw OSM and GIS data (not tracked if large)
│ └── processed/ # Processed / clipped building data
├── blender/ # Blender project files (.blend)
├── scripts/ # Python scripts for preprocessing and clipping
├── screenshots/ # Screenshots used for progress updates and presentations
├── README.md


Large raw GIS files are intentionally excluded from version control.  
Scripts and instructions are provided so the data can be regenerated if needed.

## Current Status

- ✔ Downtown Dallas CBD extracted (approx. 4 km × 4 km)
- ✔ Buildings extruded into a 3D model
- ✔ Uniform building height used as an initial simplification
- ⏳ Exploring use of real building heights or controlled height variation
- ⏳ Next steps: camera placement experiments and UAV path planning

## Tools Used

- OpenStreetMap (OSM)
- Python (geospatial preprocessing)
- Blender (3D modeling and visualization)

## Notes

This is an active research project under ongoing development.  
The modeling choices are intentionally simple at this stage to match the geometric assumptions in the underlying theory, with plans to gradually move toward more realistic city representations.

