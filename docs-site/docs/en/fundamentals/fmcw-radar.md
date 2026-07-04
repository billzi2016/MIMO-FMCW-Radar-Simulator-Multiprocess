# FMCW Radar

FMCW means **frequency-modulated continuous wave**. Instead of sending a short pulse, an FMCW radar transmits a continuous signal whose frequency changes over time.

Most mmWave radars use a repeated linear frequency sweep called a **chirp**.

For beginners, the most important idea is this: FMCW radar does not measure distance by directly waiting with a stopwatch. Instead, it converts time delay into a frequency difference. Frequency difference is much easier to measure from sampled data, so FMCW radar is practical for compact mmWave sensors.

## Chirp

A chirp starts at one frequency and ramps to another frequency over a short duration.

For a linear chirp:

```text
frequency(t) = start_frequency + slope * t
```

The slope is:

```text
slope = bandwidth / chirp_duration
```

In this project, `RadarConfig.slope_hz_per_s` computes that value.

The bandwidth controls range resolution. A larger bandwidth makes it easier to separate two targets that are close together in distance. The chirp duration and number of ADC samples decide how many fast-time samples are available for each sweep.

In code, these values live in `RadarConfig`:

```python
bandwidth_hz
chirp_duration_s
num_adc_samples
```

They are not just configuration numbers. They define the physical sampling grid of the simulated radar.

## Beat Frequency

The target echo comes back delayed. Because the transmitted chirp frequency is changing, the delayed echo has a slightly different frequency than the current transmitted signal.

FMCW radar mixes the transmitted signal with the received signal. The result is a lower-frequency signal called the **beat signal**.

For a simple target, the beat frequency is approximately proportional to delay:

```text
beat_frequency = slope * round_trip_delay
```

That is the core reason FMCW radar can estimate range.

Here is the beginner intuition:

1. The radar is sweeping upward in frequency.
2. The target echo is a delayed copy of an earlier part of that sweep.
3. When the delayed echo is compared with the current transmit signal, the difference becomes a beat frequency.
4. A farther target has a larger delay.
5. A larger delay creates a larger beat frequency.

So after mixing, distance appears as frequency. Then an FFT can find that frequency.

## Fast Time and Range FFT

Within one chirp, the ADC records samples over fast time.

The range FFT is performed over fast time. Peaks in that FFT correspond to beat frequencies, and those beat frequencies correspond to target ranges.

In this simulator:

- fast-time axis: `num_adc_samples`
- range processing: FFT over axis `0`

The simulator stores this dimension as the first axis of the raw data cube:

```text
rdc[adc_sample, chirp, virtual_channel]
```

When `fft_pipeline.py` runs:

```python
range_fft = np.fft.fft(rdc, axis=0)
```

it is asking: "Which beat frequencies exist inside each chirp?" Those frequencies are then interpreted as range bins.

## Slow Time and Doppler FFT

The radar repeats many chirps. The sequence of chirps is called slow time.

If a target is moving, the phase of its return changes from chirp to chirp. The Doppler FFT is performed over slow time to estimate velocity.

In this simulator:

- slow-time axis: `num_chirps`
- Doppler processing: FFT over axis `1`

This project uses a simple constant-velocity target model. The target position changes with:

```text
position = initial_position + velocity * slow_time
```

That movement changes the distance and phase from chirp to chirp. The Doppler FFT reads those phase changes as velocity.

If there is only one chirp, there is no slow-time sequence and Doppler estimation is not meaningful. This is why `num_chirps` matters.

## MIMO Channels and Angle FFT

MIMO radar uses multiple transmit and receive antennas to create a virtual antenna array.

Different virtual channels see slightly different phases for the same target. An FFT across those channels estimates angle.

In this simulator:

- channel axis: `num_tx * num_rx`
- angle processing: FFT over axis `2`

The simulator builds a simple virtual linear array:

- RX elements are spaced by half wavelength.
- TX elements are spaced so that TX/RX combinations form a wider virtual aperture.
- Each TX/RX pair becomes one virtual channel.

This is simplified, but it is enough to show why channel phase carries angle information.

## How FMCW Appears in the Code

The FMCW equation appears most directly in `_synthesize_channel()` in `signal_synth.py`.

That function computes:

- path length from transmitter to scatterer
- path length from scatterer to receiver
- round-trip delay
- beat frequency from `slope * delay`
- static phase from carrier frequency and chirp delay terms
- fast-time complex exponential

The key line conceptually is:

```text
phase = static_phase + 2π * beat_frequency * fast_time
```

That means each scatterer contributes a complex sinusoid over ADC samples. The frequency of that sinusoid represents range, and the phase across chirps/channels later supports velocity and angle.

## What This Simulator Simplifies

The project keeps the FMCW model readable and intentionally omits many production radar details:

- no thermal noise
- no ADC quantization
- no leakage cancellation
- no CFAR detector
- no MUSIC or high-resolution angle estimator
- no multipath model
- no detailed electromagnetic material model

The purpose is to make the main FMCW chain visible: delay becomes range, phase change becomes velocity, and channel phase difference becomes angle.

## Reading Order for Beginners

If you are new to FMCW radar, read the code in this order:

1. `radar_model.py`: understand bandwidth, chirp duration, ADC samples, chirps, TX/RX count.
2. `signal_synth.py`: see how distance becomes delay and delay becomes beat frequency.
3. `fft_pipeline.py`: see how the three dimensions become range, velocity, and angle.
4. `examples/plot/plot_thanh_run.py`: see how FFT outputs become heatmaps.

This order follows the physics: configure the radar, synthesize the signal, transform the signal, then visualize the result.
