# Simulation Workflow

The simulator follows a deliberately transparent radar-processing chain.

1. Load an `OBJ`, `STL`, or `GLB` mesh.
2. Convert the mesh into triangle faces.
3. Apply target translation and fixed Euler rotation for each chirp.
4. Keep faces whose normals point toward the radar phase center.
5. Remove faces occluded by other triangles.
6. Convert visible faces into simplified scattering units.
7. Synthesize the raw radar data cube for every TX/RX channel.
8. Run range FFT, Doppler FFT, and angle FFT.

## Current Modeling Scope

The first version keeps the signal model intentionally simple:

- no additive noise
- no filtering
- no CFAR
- no MUSIC
- no dedicated micro-Doppler post-processing

This keeps the code easy to inspect while preserving the main MIMO FMCW radar pipeline.
