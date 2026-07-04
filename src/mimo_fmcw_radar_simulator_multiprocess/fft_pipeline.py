"""RDC 后处理 FFT 流水线。

输入是 `signal_synth.simulate_rdc` 生成的原始复数采样：
`range samples x chirps x virtual channels`。
本模块按毫米波雷达常见处理链路依次做距离 FFT、多普勒 FFT、角度 FFT，
并同时输出便于画图的坐标轴。

三个 FFT 维度的含义固定为：
- axis 0：fast-time / ADC 采样点，对应距离。
- axis 1：slow-time / chirp 序列，对应速度。
- axis 2：虚拟阵列通道，对应角度。
"""

from __future__ import annotations

import numpy as np

from .radar_model import RadarConfig


def run_fft_pipeline(rdc: np.ndarray, radar: RadarConfig) -> dict[str, np.ndarray]:
    """执行 Range / Doppler / Angle 三级 FFT。

    返回字典既包含中间 cube，也包含压缩后的 2D map：
    - `range_fft`：距离维 FFT 后结果。
    - `range_doppler_cube`：距离-速度-通道 cube。
    - `range_doppler_angle_cube`：距离-速度-角度 cube。
    - `range_doppler_map` / `range_angle_map`：常用可视化投影。
    """

    # axis=0 是 fast-time，对应距离维；FMCW beat frequency 在这一维分离。
    range_fft = np.fft.fft(rdc, axis=0)
    # axis=1 是 slow-time，对 chirp 序列做 FFT 得到多普勒；fftshift 把 0 速度移到中心。
    range_doppler_cube = np.fft.fftshift(np.fft.fft(range_fft, axis=1), axes=1)
    # 对虚拟通道求幅值和，得到更容易观察的 Range-Doppler 热力图。
    range_doppler_map = np.sum(np.abs(range_doppler_cube), axis=2)

    # axis=2 是 MIMO 虚拟阵列通道，对通道相位做 FFT 得到角度维。
    range_doppler_angle_cube = np.fft.fftshift(np.fft.fft(range_doppler_cube, axis=2), axes=2)
    # 对速度维求和，得到 Range-Angle 投影。
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
    """距离轴。

    对线性 FMCW，距离分辨率约为 `c / (2B)`，这里用 bin index 乘该分辨率
    得到每个 range bin 的距离刻度。
    """

    return np.arange(radar.num_adc_samples, dtype=np.float64) * radar.light_speed / (2.0 * radar.bandwidth_hz)


def doppler_axis_m_s(radar: RadarConfig) -> np.ndarray:
    """多普勒速度轴。

    slow-time FFT 的频率单位是 Hz，对单站近似雷达速度换算为
    `v = f_d * lambda / 2`。`fftshift` 与 cube 的多普勒维保持一致。
    """

    frequencies = np.fft.fftshift(np.fft.fftfreq(radar.num_chirps, d=radar.chirp_duration_s))
    return frequencies * radar.wavelength_m / 2.0


def angle_axis_deg(radar: RadarConfig) -> np.ndarray:
    """角度轴的简化估计。

    半波长均匀线阵中，空间频率近似对应 `sin(theta)`。这里把虚拟通道 FFT
    频率映射到 `[-1, 1]` 后用 arcsin 得到角度刻度。
    """

    num_channels = radar.num_tx * radar.num_rx
    normalized = 2.0 * np.fft.fftshift(np.fft.fftfreq(num_channels, d=1.0))
    clipped = np.clip(normalized, -1.0, 1.0)
    return np.rad2deg(np.arcsin(clipped))
