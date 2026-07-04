# Mesh Preparation

This project needs a 3D mesh target. The mesh is the simulated object that reflects radar energy.

## Where the Mesh Comes From

The repository includes two example meshes:

- `examples/meshes/box.obj`
- `examples/meshes/Thanh.glb`

`box.obj` is a simple test object. `Thanh.glb` is a public human model from:

```text
https://github.com/hmthanh/3d-human-model
```

The human model is useful because it gives the simulator a more realistic surface than a box.

## Supported Formats

The simulator supports:

- `OBJ`
- `STL`
- `GLB`

All formats are converted into the same internal `TriangleMesh` representation.

## What the Simulator Uses

The simulator only uses geometric information:

- vertices
- triangle faces
- face centers
- face normals
- face areas

It does not use:

- texture
- material
- color
- skeleton
- animation

This matters because a visually beautiful 3D model is not automatically a good radar target. The current simulator only sees triangle surfaces.

## Recommended Mesh Properties

A good first mesh should be:

- not too dense
- mostly made of clean triangles
- scaled to a reasonable physical size
- placed in front of the radar
- free of too many tiny disconnected fragments

Large meshes can be slow because visibility checking currently uses direct ray-triangle intersection.

## Face Budget

Use `--max-faces` to reduce large meshes:

```bash
python -m mimo_fmcw_radar_simulator_multiprocess \
  --mesh examples/meshes/Thanh.glb \
  --max-faces 1200 \
  --num-chirps 16 \
  --output examples/output/thanh_run.npz
```

This keeps early experiments tractable. It randomly selects a subset of faces and remaps vertices so the mesh remains valid.

## Units and Scale

Radar simulation is sensitive to scale. If a mesh was modeled in centimeters but treated as meters, the target becomes 100 times larger than expected.

Before using a custom mesh, check:

- Is the size reasonable in meters?
- Is the target in front of the radar?
- Is the initial distance reasonable?
- Is the face count manageable?

## Practical Workflow

1. Export the object as `OBJ`, `STL`, or `GLB`.
2. Start with a simple version of the mesh.
3. Use `--max-faces` if it is dense.
4. Use fewer chirps for the first run.
5. Generate heatmaps and inspect whether range and angle look reasonable.
6. Increase mesh detail only after the simple run works.

## Common Problems

| Problem | Likely cause |
|---------|--------------|
| Simulation is too slow | too many faces |
| No obvious return | target behind radar, wrong scale, or unexpected face orientation |
| Strange range | mesh unit scale is wrong |
| Weak signal | visible area is small or reflectivity is low |
