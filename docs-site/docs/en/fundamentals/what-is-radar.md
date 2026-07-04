# What Is Radar

Radar means **radio detection and ranging**. A radar system transmits electromagnetic waves, waits for echoes reflected by objects, and estimates information about those objects from the returned signal.

If you have never studied radar before, think of it as an active sensing system. A camera waits for light from the environment. A radar creates its own signal, sends it out, and studies what comes back. That is why radar can work in darkness, fog, smoke, or other conditions where visible-light cameras may struggle.

At the simplest level, a radar answers three questions:

1. Is there an object in front of the radar?
2. How far away is it?
3. Is it moving, and in which direction?

More advanced radar systems can also estimate angle, shape, micro-motion, and rough surface structure.

## A Simple Analogy

Imagine shouting in a canyon and listening for the echo.

- If the echo comes back late, the wall is far away.
- If the echo is loud, the reflecting surface may be large or close.
- If the echo changes pitch, the reflector may be moving.

Radar is not sound, but the logic is similar. It sends a wave, receives an echo, and measures how the echo changed. The main difference is that radar uses electromagnetic waves instead of acoustic waves, and it can measure phase and frequency with very high precision.

## Basic Radar Idea

A radar transmitter emits a known waveform. When that wave reaches an object, part of the energy is reflected back. The receiver records the returned signal.

The returned signal is useful because it is changed by the propagation path:

- A farther object produces a longer round-trip delay.
- A moving object shifts the signal frequency through the Doppler effect.
- An object at a different angle produces different phases across antenna elements.
- A larger or more reflective surface produces a stronger return.

This project simulates those ideas in a simplified way: it builds a virtual radar, puts a 3D mesh target in front of it, finds which triangle faces are visible, and synthesizes the complex radar samples that those faces would roughly produce.

## What a Radar Return Contains

A radar return is not just a single number. In modern digital radar, the receiver records complex samples. A complex sample contains two parts:

- amplitude: how strong the received signal is
- phase: where the signal is inside its wave cycle

Amplitude helps describe reflection strength. Phase is extremely important because small phase changes can reveal distance, velocity, and angle.

This project stores raw radar data as a complex-valued cube. That cube is later processed with FFTs to reveal range, velocity, and angle structure.

## Range

Radar range comes from round-trip travel time.

If a signal takes time `tau` to go from radar to target and back, the distance is approximately:

```text
range = c * tau / 2
```

The division by 2 appears because the wave travels the distance twice: radar to target, then target back to radar.

In a real radar, directly measuring tiny time delays can be hard. FMCW radar solves this by turning delay into a frequency difference. That is why the FMCW page is important.

## Velocity

Velocity comes from phase change across multiple repeated measurements.

If the target moves between chirps, the return phase changes over slow time. A Doppler FFT turns that slow-time phase change into a velocity estimate.

In this simulator, `num_chirps` controls how many repeated measurements are available for Doppler processing.

For beginners, the key point is this: one chirp can tell you range, but repeated chirps are needed to estimate motion. If a target changes position between chirps, its phase changes in a structured way. The Doppler FFT reads that structure.

## Angle

Angle comes from phase differences across antenna elements.

If a target is not directly in front of the radar, the echo reaches different antennas with slightly different path lengths. Those path differences appear as phase differences. An angle FFT across virtual MIMO channels gives a coarse angle estimate.

In this project, `num_tx * num_rx` forms the virtual channel dimension.

This is why MIMO matters. More virtual channels give the simulator more spatial samples across the antenna array. Those spatial samples are what make angle estimation possible.

## Radar Data Cube

The project uses a three-dimensional raw data cube:

```text
ADC samples x chirps x virtual channels
```

Each dimension has a physical meaning:

| Dimension | Meaning | Used for |
|-----------|---------|----------|
| ADC samples | samples inside one chirp | range |
| chirps | repeated sweeps over time | velocity |
| virtual channels | MIMO antenna combinations | angle |

This is the core mental model for the whole repository. Most code either creates this cube or transforms it.

## Why Radar Simulation Is Useful

Radar simulation is useful because real radar experiments are expensive and hard to debug. A simulator lets you inspect each stage:

- target geometry
- visible surfaces
- scattering strength
- raw radar data cube
- range-Doppler map
- range-angle map
- range-Doppler-angle cube

This repository is intentionally educational: it does not try to be a full electromagnetic solver, but it exposes the main structure of a MIMO FMCW radar processing chain.

## What This Project Does Not Try to Do

It is also important to understand the boundary. This project does not simulate every physical effect in a real radar sensor. It does not model hardware noise, antenna patterns, multipath, material-dependent electromagnetic scattering, or calibration errors.

Instead, it teaches the main chain:

```text
geometry -> visible surfaces -> scattering points -> radar samples -> FFT maps
```

Once that chain is clear, more advanced radar effects can be added later in a controlled way.
