# MIMO FMCW Radar Simulator

This documentation site explains the mesh-based MIMO FMCW radar simulator, its processing pipeline, and the project structure.

The simulator loads a triangle-surface 3D mesh, keeps radar-facing visible faces, approximates each visible face as a scattering unit, synthesizes raw radar data, and produces range, Doppler, and angle FFT outputs.

## What This Site Covers

- How to install and run the simulator.
- How the mesh-to-radar processing chain is organized.
- What each core module is responsible for.
- How the bilingual MkDocs documentation site is structured.

## Language Structure

This site is organized as two parallel documentation trees:

- English content: `docs/en/`
- Chinese content: `docs/zh/`

The two trees should keep matching page topics and navigation levels whenever possible.
