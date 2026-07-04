# Multiprocessing Acceleration

The slowest part of this simulator is raw radar signal synthesis. The simulator must repeat similar work for many chirps, virtual channels, and visible scatterers.

The multiprocessing design accelerates the chirp dimension while keeping the physical model unchanged.

## Why Split by Chirp

Each chirp can be synthesized independently once the radar configuration, target motion, and mesh are known.

For chirp `k`, the simulator:

1. computes the target position at that slow-time value
2. transforms the mesh
3. extracts visible triangles
4. builds scatterers
5. synthesizes all TX/RX channels for that chirp

That work does not require data from other chirps. This makes chirps a natural parallelization unit.

## Work Splitting

`multiprocess_engine.split_indices()` divides the chirp index range into contiguous blocks.

Example:

```text
num_chirps = 64
workers = 4

blocks:
0-16
16-32
32-48
48-64
```

Each block becomes a `_BlockTask`.

## Worker Task

Each worker runs `_simulate_block()` from `signal_synth.py`.

A block task contains:

- start chirp index
- stop chirp index
- mesh
- radar configuration
- target motion configuration

The worker returns:

```text
(start, stop, block)
```

The `block` array has shape:

```text
num_adc_samples x block_num_chirps x (num_tx * num_rx)
```

The main process writes it back into the final RDC array at `rdc[:, start:stop, :]`.

## Why Use Processes Instead of Threads

Python threads are limited by the GIL for Python-level CPU work. This simulator has Python loops around numpy operations, visibility checks, and per-channel synthesis.

Using `ProcessPoolExecutor` gives each worker a separate Python process. That avoids the GIL bottleneck for the outer task scheduling and makes CPU-heavy blocks run in parallel.

## Conservative Default Worker Count

`default_worker_count()` returns:

```text
max(1, os.cpu_count() // 2)
```

The simulator uses half of the available CPU cores by default because radar simulation can also be memory-bandwidth heavy. Using all cores is not always faster, especially on a laptop or desktop doing other work.

Users can override this with:

```bash
python -m mimo_fmcw_radar_simulator_multiprocess --workers 8
```

## What Multiprocessing Does Not Change

Multiprocessing only changes execution layout. It does not change:

- radar parameters
- target motion
- visibility logic
- scattering strength
- FMCW phase formula
- FFT processing

So the output should be conceptually the same as a serial run with the same inputs.

## Current Limitation

The current visibility stage checks ray-triangle intersections directly against the full mesh. This is easy to understand, but expensive for large meshes.

For future acceleration, the best next step is likely a spatial acceleration structure such as:

- BVH
- KD-tree
- uniform grid

That would reduce visibility cost before signal synthesis even starts.

## Serial Version vs Multiprocess Version

A serial version would look like this:

```text
for chirp in all_chirps:
    simulate this chirp
    write result into RDC
```

The multiprocess version keeps the same idea but groups chirps into blocks:

```text
worker 1: chirps 0-15
worker 2: chirps 16-31
worker 3: chirps 32-47
worker 4: chirps 48-63
```

Each worker produces a partial cube. The main process then inserts each partial cube into the correct slow-time slice of the final cube.

This works because chirp blocks do not overlap. No worker needs to write into the same output slice as another worker.

## Data Copy Cost

Multiprocessing is not free. Python must send task data to worker processes and receive result arrays back.

The task contains the mesh, radar configuration, and target configuration. For a large mesh, copying or serializing this data can be expensive. That is why multiprocessing helps most when the per-block computation is heavy enough to dominate the process overhead.

If the mesh is tiny or `num_chirps` is very small, a single worker may be just as fast or faster.

## When It Speeds Up

Multiprocessing is most useful when:

- `num_chirps` is large
- the mesh has many faces
- visibility checks are expensive
- many virtual channels are synthesized
- each worker has enough work to amortize process overhead

It may help less when:

- the input mesh is very small
- only a few chirps are simulated
- the computer is already memory-bandwidth limited
- too many workers compete for the same CPU and memory resources

## Why the Result Is Reassembled Safely

Each worker returns its own chirp range:

```text
(start, stop, block)
```

The main process writes:

```python
rdc[:, start:stop, :] = block
```

This is safe because each block corresponds to a different chirp interval. The workers never directly mutate the final `rdc` array. They only return independent results.

## Practical Tuning Advice

For a beginner, use these rules:

1. Start with the default worker count.
2. If the machine remains responsive and CPU is not saturated, try increasing `--workers`.
3. If runtime gets worse, reduce workers.
4. If the mesh is too large, try `--max-faces` first before increasing workers.

`--max-faces` often matters more than worker count because direct visibility checking can dominate runtime.

## Future Acceleration Path

The current multiprocessing approach is a coarse-grained acceleration strategy. It parallelizes independent chirp blocks but does not change the algorithmic complexity of visibility.

A future high-performance version should likely combine:

- BVH or spatial indexing for ray-triangle queries
- vectorized scatterer synthesis
- optional GPU acceleration
- caching visibility if target pose changes slowly

The current design keeps these future paths possible because multiprocessing is isolated in `multiprocess_engine.py`.
