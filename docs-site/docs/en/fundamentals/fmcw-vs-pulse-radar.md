# FMCW vs Pulse Radar

Many beginners imagine radar as a system that sends a short pulse, waits for the echo, and measures how long the echo takes to return. That is a real radar category, usually called pulse radar. FMCW radar is different.

This page explains the difference in beginner-friendly terms.

## Pulse Radar

A pulse radar transmits a short burst of energy and then listens for echoes.

The simple model is:

```text
send pulse -> wait -> receive echo -> measure delay
```

If the echo returns after time `tau`, the range is:

```text
range = c * tau / 2
```

The idea is direct: measure time, convert time to distance. The challenge is that the time delay can be extremely small, especially for short-range targets.

## FMCW Radar

FMCW radar transmits a continuous chirp. The chirp frequency changes over time.

The simple model is:

```text
send frequency sweep -> receive delayed sweep -> mix signals -> measure beat frequency
```

The delayed echo is compared with the current transmit signal. Because the transmit frequency is sweeping, delay becomes a frequency difference.

```text
beat_frequency = chirp_slope * round_trip_delay
```

So FMCW radar estimates range by measuring frequency, not by directly measuring a tiny time interval.

## Key Differences

| Topic | Pulse radar | FMCW radar |
|-------|-------------|------------|
| Transmit signal | short pulse | continuous chirp |
| Range measurement | direct time delay | beat frequency |
| Typical signal after receiving | echo pulse | low-frequency beat signal |
| Common use | long-range and high-power systems | compact mmWave sensing |
| Hardware style | often high peak power | lower peak power, easier for small sensors |

## Why This Matters for This Simulator

This project is an FMCW simulator. That means the code focuses on:

1. chirp slope
2. round-trip delay
3. beat frequency
4. complex fast-time samples
5. FFT over ADC samples

The most important equation in the simulator is:

```text
beat_frequency = radar.slope_hz_per_s * round_trip_delay
```

That equation is why the simulator can turn target distance into a frequency component inside the raw data cube.

## What "Ordinary Radar" Means

There is no single "ordinary radar." Radar can use many waveforms: pulse, FMCW, continuous-wave Doppler, stepped frequency, phase-coded waveforms, and more.

When this documentation compares FMCW with "ordinary radar," it means the common beginner model: pulse radar that measures echo time delay directly.
