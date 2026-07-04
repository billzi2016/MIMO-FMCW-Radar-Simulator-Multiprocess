# Getting Started

## Install

From the repository root:

```bash
pip install -e .
```

## Run the Box Example

```bash
python -m mimo_fmcw_radar_simulator_multiprocess \
  --mesh examples/meshes/box.obj \
  --output examples/output/box_run.npz
```

## Run the Human Mesh Example

```bash
python -m mimo_fmcw_radar_simulator_multiprocess \
  --mesh examples/meshes/Thanh.glb \
  --max-faces 1200 \
  --num-chirps 16 \
  --output examples/output/thanh_run.npz
```

## Plot the Output

```bash
python examples/plot/plot_thanh_run.py \
  --input examples/output/thanh_run.npz
```

The plotting script generates range-Doppler, range-angle, Doppler-angle, range-chirp, and summary heatmaps.
