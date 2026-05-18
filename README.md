# MIMO-FMCW-Radar-Simulator-Multiprocess

`MIMO-FMCW-Radar-Simulator-Multiprocess` is a Python simulator for mesh-based MIMO FMCW radar scenes. The input target is a triangle-surface 3D model, and the simulator keeps only radar-facing visible faces before generating baseband radar data and three-stage FFT outputs.

## Project Goal

This project focuses on a minimal and transparent simulation chain:

- triangle mesh input
- front-facing face extraction
- line-of-sight occlusion filtering
- face-level scattering approximation
- range FFT, Doppler FFT, and angle FFT
- multiprocess execution with `cpu_count() // 2`

The current implementation intentionally keeps the signal model simple:

- no additive noise
- no filtering
- no CFAR
- no MUSIC
- no micro-Doppler specific post-processing

For large meshes, the command line supports a face-budget downsampling option so the naive visibility stage remains tractable during early experiments.

## Core Workflow

1. Load an `OBJ`, `STL`, or `GLB` mesh and convert it into triangles.
2. Apply rigid-body translation and fixed Euler rotation for each chirp.
3. Keep only faces whose normals point toward the radar phase center.
4. Cast a ray from the radar to each candidate face center and discard occluded faces.
5. Treat each visible face as one scattering unit with amplitude driven by face area and incidence angle.
6. Synthesize the dechirped radar data cube for all TX/RX channels.
7. Compute range, Doppler, and angle FFT outputs.

## Repository Layout

```text
MIMO-FMCW-Radar-Simulator-Multiprocess/
├── README.md
├── pyproject.toml
├── examples/
│   └── meshes/
│       └── box.obj
└── src/
    └── mimo_fmcw_radar_simulator_multiprocess/
        ├── __init__.py
        ├── __main__.py
        ├── fft_pipeline.py
        ├── geometry.py
        ├── main.py
        ├── mesh_loader.py
        ├── multiprocess_engine.py
        ├── radar_model.py
        ├── scatter_model.py
        ├── signal_synth.py
        └── visibility.py
```

## Installation

```bash
pip install -e .
```

## Usage

Run the built-in example:

```bash
python -m mimo_fmcw_radar_simulator_multiprocess \
  --mesh examples/meshes/box.obj \
  --output examples/output/box_run.npz
```

Run the downloaded human mesh with a face budget:

```bash
python -m mimo_fmcw_radar_simulator_multiprocess \
  --mesh examples/meshes/Thanh.glb \
  --max-faces 1200 \
  --num-chirps 16 \
  --output examples/output/thanh_run.npz
```

The output file stores:

- `rdc`: raw radar data cube
- `range_fft`: range FFT cube
- `range_doppler_cube`: range-Doppler cube
- `range_doppler_map`: non-coherent range-Doppler map
- `range_angle_map`: non-coherent range-angle map
- `range_doppler_angle_cube`: full 3D FFT result
- `range_axis_m`, `doppler_axis_m_s`, `angle_axis_deg`

## Model Assumptions

- The radar uses a simple TDM-style virtual array layout.
- The target is a rigid mesh with constant velocity.
- Occlusion is determined by ray-triangle intersection against the full mesh.
- Each visible triangle is approximated by a single scattering center at its centroid.

## Example Parameters

Default runtime parameters are chosen to keep the first version easy to inspect:

- carrier frequency: `77 GHz`
- bandwidth: `150 MHz`
- chirp duration: `40 us`
- ADC samples per chirp: `256`
- chirps per frame: `64`
- array layout: `2 TX x 4 RX`

## Model Source

The example human mesh `examples/meshes/Thanh.glb` is a public model file obtained from the GitHub repository `hmthanh/3d-human-model`:

- Source repository: `https://github.com/hmthanh/3d-human-model`
- Direct file URL: `https://raw.githubusercontent.com/hmthanh/3d-human-model/main/Thanh.glb`

## License

This repository currently does not include a separate license file.
