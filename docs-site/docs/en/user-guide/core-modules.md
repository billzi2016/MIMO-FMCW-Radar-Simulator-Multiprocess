# Core Modules

## `radar_model.py`

Defines radar configuration, derived physical parameters, antenna positions, virtual channels, and target motion.

## `mesh_loader.py`

Loads `OBJ`, `STL`, and `GLB` meshes and converts them into the internal triangle-mesh representation.

## `geometry.py`

Provides triangle centers, normals, areas, Euler rotation, rigid transforms, and ray-triangle intersection.

## `visibility.py`

Filters triangle faces by front-facing direction and line-of-sight occlusion.

## `scatter_model.py`

Converts visible triangle faces into simplified scattering points.

## `signal_synth.py`

Synthesizes the raw radar data cube across ADC samples, chirps, and virtual MIMO channels.

## `fft_pipeline.py`

Runs range, Doppler, and angle FFT processing, then exports maps and axes for visualization.

## `multiprocess_engine.py`

Splits chirps into work blocks and runs the expensive signal synthesis stage with multiple processes.
