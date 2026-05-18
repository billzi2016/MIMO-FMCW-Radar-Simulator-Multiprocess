from __future__ import annotations

import numpy as np

from .radar_model import RadarConfig


def run_fft_pipeline(rdc: np.ndarray, radar: RadarConfig) -> dict[str, np.ndarray]:
    range_fft = np.fft.fft(rdc, axis=0)
    range_doppler_cube = np.fft.fftshift(np.fft.fft(range_fft, axis=1), axes=1)
    range_doppler_map = np.sum(np.abs(range_doppler_cube), axis=2)

    range_doppler_angle_cube = np.fft.fftshift(np.fft.fft(range_doppler_cube, axis=2), axes=2)
    range_angle_map = np.sum(np.abs(range_doppler_angle_cube), axis=1)

    return {
        "rdc": rdc,
        "range_fft": range_fft,
        "range_doppler_cube": range_doppler_cube,
        "range_doppler_map": range_doppler_map,
        "range_angle_map": range_angle_map,
        "range_doppler_angle_cube": range_doppler_angle_cube,
        "range_axis_m": range_axis_m(radar),
        "doppler_axis_m_s": doppler_axis_m_s(radar),
        "angle_axis_deg": angle_axis_deg(radar),
    }


def range_axis_m(radar: RadarConfig) -> np.ndarray:
    return np.arange(radar.num_adc_samples, dtype=np.float64) * radar.light_speed / (2.0 * radar.bandwidth_hz)


def doppler_axis_m_s(radar: RadarConfig) -> np.ndarray:
    frequencies = np.fft.fftshift(np.fft.fftfreq(radar.num_chirps, d=radar.chirp_duration_s))
    return frequencies * radar.wavelength_m / 2.0


def angle_axis_deg(radar: RadarConfig) -> np.ndarray:
    num_channels = radar.num_tx * radar.num_rx
    normalized = 2.0 * np.fft.fftshift(np.fft.fftfreq(num_channels, d=1.0))
    clipped = np.clip(normalized, -1.0, 1.0)
    return np.rad2deg(np.arcsin(clipped))
