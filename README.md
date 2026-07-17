# MIMO-FMCW-Radar-Simulator-Multiprocess

`MIMO-FMCW-Radar-Simulator-Multiprocess` is a Python simulator for mesh-based MIMO FMCW radar scenes. The input target is a triangle-surface 3D model, and the simulator keeps only radar-facing visible faces before generating baseband radar data and three-stage FFT outputs.

Documentation site: https://billzi2016.github.io/MIMO-FMCW-Radar-Simulator-Multiprocess/

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
├── README_CN.md
├── fmcw-2243-cascade.png
├── pyproject.toml
├── profiles/
│   ├── awr1642.toml
│   ├── awr2243.toml
│   ├── awr2243_cascade.toml
│   └── iwr6843.toml
├── examples/
│   ├── meshes/
│   │   ├── box.obj
│   │   └── Thanh.glb
│   ├── output/
│   └── plot/
│       ├── output/
│       └── plot_thanh_run.py
└── src/
    └── mimo_fmcw_radar_simulator_multiprocess/
        ├── __init__.py
        ├── __main__.py
        ├── fft_pipeline.py
        ├── geometry.py
        ├── main.py
        ├── mesh_loader.py
        ├── multiprocess_engine.py
        ├── profile_loader.py
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

Load a radar profile by name:

```bash
python -m mimo_fmcw_radar_simulator_multiprocess \
  --profile awr2243 \
  --mesh examples/meshes/box.obj \
  --output examples/output/awr2243_run.npz
```

Use the four-chip AWR2243 Cascade profile with 86 effective azimuth virtual channels:

```bash
python -m mimo_fmcw_radar_simulator_multiprocess \
  --profile awr2243_cascade \
  --mesh examples/meshes/box.obj \
  --output examples/output/awr2243_cascade_run.npz
```

Available profiles:

| Profile | Frequency range | Physical array | Effective azimuth channels |
| --- | --- | --- | ---: |
| `awr1642` | 76-81 GHz | 2 TX x 4 RX | 8 |
| `awr2243` | 76-81 GHz | 3 TX x 4 RX | 12 |
| `iwr6843` | 60-64 GHz | 3 TX x 4 RX | 12 |
| `awr2243_cascade` | 76-81 GHz | 12 TX x 16 RX | 86 |

Explicit radar CLI options override values loaded from a profile.

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

## Visualization

The image below shows the real-world target object corresponding to the simulated scene used in this repository.

![Simulated target object](fmcw-2243-cascade.png)

The following PNG results are generated from `examples/output/thanh_run.npz` by the standalone plotting script in `examples/plot/`.

### Summary Heatmaps

![Summary heatmaps](examples/plot/output/summary_heatmaps.png)

### Range-Doppler Heatmap

![Range-Doppler heatmap](examples/plot/output/range_doppler_heatmap.png)

### Range-Angle Heatmap

![Range-Angle heatmap](examples/plot/output/range_angle_heatmap.png)

### Doppler-Angle Heatmap

![Doppler-Angle heatmap](examples/plot/output/doppler_angle_heatmap.png)

### Range-Chirp Heatmap

![Range-Chirp heatmap](examples/plot/output/range_chirp_heatmap.png)

## Disclaimer

Texas Instruments, TI, AWR1642, AWR2243, and IWR6843 are trademarks or product names of Texas Instruments Incorporated. This project is an independent, unofficial simulation tool intended solely for educational and research purposes. It is not affiliated with, endorsed by, sponsored by, or otherwise associated with Texas Instruments Incorporated.

The simulator is independently implemented using general FMCW and MIMO radar principles. It does not incorporate TI source code, firmware, SDK components, proprietary algorithms, confidential information, or copied technical documentation. References to TI device names and publicly available specifications are used solely to identify example hardware profiles and factual operating parameters. The simulation models, profile format, and software implementation in this repository were developed independently.

This project uses publicly available files and parameters to support academic reproducibility consistent with practices commonly encouraged in ACM and IEEE publications, including reproduction of documented data-processing workflows and experimental results.

## License

This repository currently does not include a separate license file.
