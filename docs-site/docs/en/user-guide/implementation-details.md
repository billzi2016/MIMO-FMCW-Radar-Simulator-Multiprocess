# Implementation Details

This project is built as a small, inspectable radar simulation pipeline rather than a black-box simulator. Each module owns one stage of the pipeline, and the output of one stage becomes the input of the next stage.

## Overall Design

The main data path is:

```text
mesh file
-> TriangleMesh
-> per-chirp transformed triangles
-> visible triangles
-> ScatterSet
-> raw radar data cube
-> FFT outputs
-> plots
```

The important design choice is that the simulator does not jump directly from a mesh to a heatmap. It keeps intermediate concepts explicit:

- mesh loading
- geometric visibility
- scattering approximation
- channel-level signal synthesis
- range/Doppler/angle FFT

That makes the project easier to debug and easier to teach.

## 1. Mesh Loading

`mesh_loader.py` reads `OBJ`, `STL`, and `GLB` files and converts them into `TriangleMesh`.

`TriangleMesh` only stores:

- `vertices`: point coordinates
- `faces`: triangle vertex indices

Rendering information such as textures, materials, and animation is ignored. The radar simulator only needs geometry.

## 2. Per-Chirp Target Transformation

For each chirp, the target is transformed as a rigid body.

The target position is:

```text
position(t) = initial_position + velocity * slow_time
```

Then a fixed Euler rotation is applied. This creates a simple moving target model that is enough for early range and Doppler experiments.

## 3. Visibility Filtering

`visibility.py` removes triangles that should not contribute to the radar echo.

It uses two checks:

1. Front-facing check: keep triangles whose normals point toward the radar.
2. Occlusion check: cast a ray from the radar phase center to the triangle center and discard the triangle if another face blocks the ray.

This is intentionally direct and readable. It is not yet accelerated by BVH or spatial indexing.

## 4. Scatter Model

`scatter_model.py` converts each visible triangle into one scattering point.

The scattering point is placed at the triangle center. Its strength is computed from:

- triangle area
- incidence angle
- global target reflectivity

This approximation is not a full electromagnetic model. It is a teaching-oriented model that makes the relationship between geometry and radar signal visible.

## 5. Signal Synthesis

`signal_synth.py` generates the raw radar data cube.

For each chirp, each virtual channel, and each scatterer, it computes:

- TX-to-scatterer distance
- scatterer-to-RX distance
- round-trip delay
- distance attenuation
- beat frequency
- complex phase over fast time

All scatterer returns are summed into one complex signal per channel.

The output shape is:

```text
num_adc_samples x num_chirps x (num_tx * num_rx)
```

## 6. FFT Pipeline

`fft_pipeline.py` performs three FFT stages:

1. Range FFT over ADC samples.
2. Doppler FFT over chirps.
3. Angle FFT over virtual MIMO channels.

The outputs include both full cubes and projected maps for visualization.

## Why This Structure Works

The implementation is deliberately modular:

- geometry code does not know radar parameters
- radar configuration does not synthesize signals
- visibility does not compute FFT
- multiprocessing only splits work; it does not change the physical model

This separation makes the simulator easier to extend. For example, a future version can replace the visibility stage with BVH acceleration or replace the scatter model with a more detailed material model without rewriting the whole project.

## Beginner Reading Path

If you are new to the project, read it from the outside in:

1. Start with `main.py`. It shows the full command-line flow: parse arguments, create configuration objects, load the mesh, run simulation, run FFT, and save output.
2. Move to `radar_model.py`. It explains what the radar needs to know: carrier frequency, bandwidth, chirp duration, ADC samples, chirp count, and antenna count.
3. Read `mesh_loader.py` and `geometry.py`. These files explain how a 3D model becomes triangles and how those triangles are measured.
4. Read `visibility.py`. This is where the simulator decides which surfaces the radar can actually see.
5. Read `scatter_model.py`. This turns visible surfaces into point-like radar scatterers.
6. Read `signal_synth.py`. This is the core file where distances become delays, delays become beat frequencies, and scatterers become complex radar samples.
7. Read `fft_pipeline.py`. This is where the raw cube becomes range, velocity, and angle maps.

This order is easier than reading alphabetically because it follows the actual execution path.

## Stage-by-Stage Inputs and Outputs

The project is easier to understand if every stage is viewed as a transformation:

| Stage | Input | Output |
|-------|-------|--------|
| Mesh loading | `OBJ` / `STL` / `GLB` file | `TriangleMesh` |
| Geometry transform | mesh + target motion | per-chirp triangle positions |
| Visibility | transformed triangles + radar origin | visible triangles |
| Scatter model | visible triangles | scatterer centers and strengths |
| Signal synthesis | scatterers + radar config | raw complex RDC |
| FFT pipeline | raw complex RDC | range/Doppler/angle outputs |
| Plotting | FFT maps | PNG heatmaps |

This table is also a debugging guide. If a result looks wrong, find the earliest stage where the intermediate output becomes unreasonable.

## Why Keep the Model Simple

The simulator intentionally omits many advanced radar effects. That is not a bug; it is a design choice. The first goal is to make the main signal path visible.

For example, a production radar system may include antenna radiation patterns, receiver noise, calibration errors, leakage, multipath, clutter suppression, CFAR detection, and tracking. Adding all of those at once would make the code harder to learn from.

This project starts with a smaller model:

```text
surface geometry -> simple scattering -> complex samples -> FFT maps
```

Once this path is understood, advanced effects can be added one at a time.

## How Code Maps to Radar Concepts

The code is intentionally named after radar concepts:

- `RadarConfig` is the radar hardware and waveform description.
- `TargetMotion` is the moving object description.
- `TriangleMesh` is the target geometry.
- `VisibilityResult` is the set of surfaces that can reflect directly to the radar.
- `ScatterSet` is the simplified scattering model.
- `rdc` is the raw radar data cube before FFT interpretation.

The most important variable is `rdc`. It is the bridge between simulation and radar signal processing. Everything before `rdc` creates the signal. Everything after `rdc` interprets the signal.

## What to Change First When Extending

Different research directions map to different modules:

| Goal | First module to modify |
|------|------------------------|
| Better mesh loading | `mesh_loader.py` |
| Faster visibility | `visibility.py` |
| More realistic scattering | `scatter_model.py` |
| Noise or hardware effects | `signal_synth.py` |
| Different radar axes | `fft_pipeline.py` |
| More CLI options | `main.py` |

This is why the project is split into small files. The boundaries are meant to make future experiments local rather than global rewrites.
