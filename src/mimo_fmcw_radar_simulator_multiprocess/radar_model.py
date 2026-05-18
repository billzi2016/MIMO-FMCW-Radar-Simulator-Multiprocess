from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class RadarConfig:
    carrier_hz: float = 77e9
    bandwidth_hz: float = 150e6
    chirp_duration_s: float = 40e-6
    num_adc_samples: int = 256
    num_chirps: int = 64
    num_tx: int = 2
    num_rx: int = 4

    @property
    def light_speed(self) -> float:
        return 299792458.0

    @property
    def wavelength_m(self) -> float:
        return self.light_speed / self.carrier_hz

    @property
    def slope_hz_per_s(self) -> float:
        return self.bandwidth_hz / self.chirp_duration_s

    @property
    def sample_rate_hz(self) -> float:
        return self.num_adc_samples / self.chirp_duration_s

    @property
    def fast_time_s(self) -> np.ndarray:
        return np.arange(self.num_adc_samples, dtype=np.float64) / self.sample_rate_hz

    @property
    def slow_time_s(self) -> np.ndarray:
        return np.arange(self.num_chirps, dtype=np.float64) * self.chirp_duration_s

    @property
    def element_spacing_m(self) -> float:
        return self.wavelength_m / 2.0

    @property
    def tx_positions_m(self) -> np.ndarray:
        spacing = self.num_rx * self.element_spacing_m
        positions = np.zeros((self.num_tx, 3), dtype=np.float64)
        positions[:, 0] = np.arange(self.num_tx, dtype=np.float64) * spacing
        return positions

    @property
    def rx_positions_m(self) -> np.ndarray:
        positions = np.zeros((self.num_rx, 3), dtype=np.float64)
        positions[:, 0] = np.arange(self.num_rx, dtype=np.float64) * self.element_spacing_m
        return positions

    @property
    def virtual_channel_positions_m(self) -> np.ndarray:
        channels = []
        for tx in self.tx_positions_m:
            for rx in self.rx_positions_m:
                channels.append(tx + rx)
        return np.asarray(channels, dtype=np.float64)

    @property
    def radar_phase_center_m(self) -> np.ndarray:
        all_positions = np.vstack([self.tx_positions_m, self.rx_positions_m])
        return np.mean(all_positions, axis=0)


@dataclass(frozen=True)
class TargetMotion:
    initial_position_m: tuple[float, float, float] = (0.0, 10.0, 0.0)
    velocity_m_s: tuple[float, float, float] = (0.0, -1.0, 0.0)
    euler_deg: tuple[float, float, float] = (0.0, 0.0, 0.0)
    reflectivity: float = 1.0

    @property
    def initial_position_array(self) -> np.ndarray:
        return np.asarray(self.initial_position_m, dtype=np.float64)

    @property
    def velocity_array(self) -> np.ndarray:
        return np.asarray(self.velocity_m_s, dtype=np.float64)
