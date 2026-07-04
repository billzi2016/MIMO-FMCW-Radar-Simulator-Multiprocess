# Simulator Principle

This simulator turns a 3D mesh into synthetic MIMO FMCW radar data.

The high-level idea is:

```text
3D mesh -> visible triangle faces -> scattering points -> raw radar data cube -> FFT maps
```

It is not a full electromagnetic solver. It is a transparent geometric radar simulator designed for learning, debugging, and early experiments.

For a beginner, the key is to separate three layers:

1. Geometry layer: what surfaces exist, where they are, and which ones face the radar.
2. Radar signal layer: how visible surfaces create delayed complex returns.
3. FFT interpretation layer: how raw samples become range, velocity, and angle maps.

The simulator is built around those layers.

## 1. Mesh as Target Geometry

The target is represented as a triangle mesh.

Each face has:

- three vertices
- a center point
- a normal direction
- an area

The simulator only keeps geometry. It does not use texture, material, animation, or rendering information.

This is why a visual 3D model can become a radar target. The radar does not need the color of a shirt or the texture of an object. In this simplified simulator, it only needs surfaces that can reflect energy.

The mesh is reduced to triangles because triangles are easy to process:

- a triangle has a well-defined center
- a triangle has a well-defined normal direction
- a triangle has a measurable area
- ray-triangle intersection is a standard geometric test

## 2. Target Motion

For each chirp, the target mesh is transformed as a rigid body.

The transformation has two parts:

- fixed Euler rotation
- translation from initial position plus velocity multiplied by slow time

This means the target moves as one object. The current version does not model articulated motion, walking limbs, vibration, or micro-Doppler body-part motion.

This is a deliberate simplification. It makes the connection between target velocity and Doppler easier to understand. If the whole mesh moves toward the radar, the phase changes consistently across chirps. Later, articulated motion could be added by moving different mesh parts differently.

## 3. Visible Face Selection

Not every triangle face should contribute to the radar return.

The simulator first removes faces whose normals point away from the radar. Then it checks line-of-sight occlusion: if another triangle blocks the ray from the radar to the candidate face center, that face is discarded.

This is a simple but important step. Without it, back faces and hidden faces would generate unrealistic echoes.

The visibility step answers a physical question: "Can the radar see this surface directly?"

The simulator uses the radar phase center as the viewpoint. For each candidate face, it checks whether a straight line from the radar to the face center is blocked. This is similar to a very simple ray tracer, but the goal is not rendering an image. The goal is deciding which surfaces are allowed to scatter.

This step is expensive for large meshes because every candidate face may be tested against many other faces. That is why the command line provides `--max-faces` for early experiments.

## 4. Face-Level Scattering Approximation

Each visible triangle is converted into one scattering point at its center.

The scattering strength is based on:

- triangle area
- incidence angle
- target reflectivity

Larger faces contribute more. Faces pointing more directly toward the radar contribute more. Back-facing faces contribute nothing.

This is a coarse approximation, but it keeps the simulator explainable and computationally manageable.

The approximation is useful because it turns a surface problem into a point-scatterer problem. Once every visible face becomes a point with a strength, the signal synthesis stage can compute distances and phases in a straightforward way.

The strength formula is intentionally simple:

```text
strength ≈ reflectivity * area * incidence
```

This means:

- larger faces have stronger echoes
- faces pointing toward the radar have stronger echoes
- faces pointing away from the radar are ignored

## 5. Channel Signal Synthesis

For every scatterer and every TX/RX pair, the simulator computes:

- distance from TX to scatterer
- distance from scatterer to RX
- round-trip delay
- distance attenuation
- beat frequency
- complex phase

The returned samples are complex exponentials summed across all scatterers.

The result is the raw radar data cube:

```text
num_adc_samples x num_chirps x (num_tx * num_rx)
```

This cube is the central data object of the project.

Each axis answers one question:

- ADC samples: what beat frequencies exist inside one chirp?
- chirps: how does phase change over repeated chirps?
- virtual channels: how does phase change across antenna positions?

The simulator does not store a separate object for "range" or "speed" at this stage. Those meanings appear after FFT processing.

## 6. FFT Processing

The raw cube is processed in three FFT stages:

1. Range FFT over ADC samples.
2. Doppler FFT over chirps.
3. Angle FFT over virtual MIMO channels.

The pipeline outputs:

- raw data cube
- range FFT cube
- range-Doppler cube
- range-Doppler map
- range-angle map
- range-Doppler-angle cube
- range, velocity, and angle axes

The FFT stages are not arbitrary. They match the physical dimensions of the radar measurement:

| FFT | Input dimension | Physical meaning |
|-----|-----------------|------------------|
| Range FFT | ADC samples | delay / distance |
| Doppler FFT | chirps | phase change / velocity |
| Angle FFT | virtual channels | spatial phase / angle |

This table is the best shortcut for understanding the code.

## 7. Multiprocessing

The expensive part is signal synthesis across many chirps and many faces.

The simulator splits the chirp dimension into contiguous blocks. Each worker process computes one block, and the main process writes the blocks back into the final cube.

This keeps the algorithm simple while making larger examples more practical.

The important design point is that multiprocessing does not change the math. It only changes how the chirp loop is executed. A serial run and a multiprocess run follow the same physical model.

## Current Boundary

This simulator is best understood as a first-principles educational pipeline. It explains how a mesh target can become synthetic radar data, but it does not yet replace professional radar simulation or real sensor validation.

## End-to-End Mental Model

If you remember only one thing, remember this:

```text
visible geometry creates delayed complex sinusoids;
FFTs interpret those sinusoids as range, velocity, and angle.
```

The rest of the project is implementation detail around that sentence.
