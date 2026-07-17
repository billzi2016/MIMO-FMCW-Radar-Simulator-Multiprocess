"""雷达与目标运动的基础参数模型。

这个文件只负责描述“仿真需要哪些物理参数”，不直接生成信号。
后续的信号合成、FFT 处理、可视化都会依赖这里给出的采样时间轴、
天线阵列位置、波长、调频斜率等派生量。

阅读本文件时可以把它理解成“物理配置层”：
- `RadarConfig` 描述雷达硬件、波形和虚拟阵列。
- `TargetMotion` 描述目标刚体运动和整体反射强度。
- 所有复杂信号都不会在这里生成，只提供后续模块需要的可复用物理量。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class RadarConfig:
    """MIMO FMCW 雷达配置。

    这里的默认值对应一个简化的 77GHz 毫米波雷达设置：
    - fast-time 维度由 `num_adc_samples` 和 chirp 时长决定，用于距离 FFT。
    - slow-time 维度由 `num_chirps` 决定，用于多普勒 FFT。
    - `num_tx * num_rx` 形成原始虚拟阵列通道，用于角度 FFT。
    - `azimuth_virtual_channels` 可选取水平方位向的有效虚拟阵元数。
    """

    carrier_hz: float = 77e9
    bandwidth_hz: float = 150e6
    chirp_duration_s: float = 40e-6
    num_adc_samples: int = 256
    num_chirps: int = 64
    num_tx: int = 2
    num_rx: int = 4
    azimuth_virtual_channels: int | None = None

    def __post_init__(self) -> None:
        if self.num_tx <= 0 or self.num_rx <= 0:
            raise ValueError("num_tx and num_rx must be positive")
        if self.azimuth_virtual_channels is not None:
            if not 1 <= self.azimuth_virtual_channels <= self.num_tx * self.num_rx:
                raise ValueError("azimuth_virtual_channels must be within the raw virtual channel count")

    @property
    def num_channels(self) -> int:
        """用于当前水平角度处理的有效虚拟通道数。"""

        return self.azimuth_virtual_channels or self.num_tx * self.num_rx

    @property
    def light_speed(self) -> float:
        """光速，FMCW 往返传播时延计算的基础常量。"""

        return 299792458.0

    @property
    def wavelength_m(self) -> float:
        """载频对应波长，后续用于阵元间距和多普勒速度轴。"""

        return self.light_speed / self.carrier_hz

    @property
    def slope_hz_per_s(self) -> float:
        """FMCW 调频斜率，决定距离时延映射到 beat frequency 的比例。"""

        return self.bandwidth_hz / self.chirp_duration_s

    @property
    def sample_rate_hz(self) -> float:
        """ADC 采样率，由单个 chirp 内的采样点数和 chirp 时长决定。"""

        return self.num_adc_samples / self.chirp_duration_s

    @property
    def fast_time_s(self) -> np.ndarray:
        """单个 chirp 内的采样时间轴，也就是距离向 FFT 的原始时间维。"""

        return np.arange(self.num_adc_samples, dtype=np.float64) / self.sample_rate_hz

    @property
    def slow_time_s(self) -> np.ndarray:
        """chirp 序列的慢时间轴，用于描述目标运动和多普勒处理。"""

        return np.arange(self.num_chirps, dtype=np.float64) * self.chirp_duration_s

    @property
    def element_spacing_m(self) -> float:
        """阵元间距设为半波长，避免角度估计时出现明显栅瓣。"""

        return self.wavelength_m / 2.0

    @property
    def tx_positions_m(self) -> np.ndarray:
        """发射天线位置。

        Tx 间距按 `num_rx * 半波长` 拉开，使 Tx-Rx 组合后形成近似均匀的
        虚拟线阵。这里只建模 x 方向线阵，y/z 坐标保持 0。
        """

        spacing = self.num_rx * self.element_spacing_m
        positions = np.zeros((self.num_tx, 3), dtype=np.float64)
        positions[:, 0] = np.arange(self.num_tx, dtype=np.float64) * spacing
        return positions

    @property
    def rx_positions_m(self) -> np.ndarray:
        """接收天线位置，按半波长沿 x 方向排列。"""

        positions = np.zeros((self.num_rx, 3), dtype=np.float64)
        positions[:, 0] = np.arange(self.num_rx, dtype=np.float64) * self.element_spacing_m
        return positions

    @property
    def virtual_channel_positions_m(self) -> np.ndarray:
        """MIMO 虚拟阵列通道位置。

        每个虚拟通道由一个 Tx 和一个 Rx 组合得到，位置用 `tx + rx`
        近似表示。后续角度 FFT 实际处理的是这些虚拟通道上的相位差。
        """

        tx_positions, rx_positions = self.channel_pair_positions_m
        return tx_positions + rx_positions

    @property
    def channel_pair_positions_m(self) -> tuple[np.ndarray, np.ndarray]:
        """返回当前有效虚拟通道对应的 Tx/Rx 位置。

        普通单芯片配置保留实际的 Tx/Rx 笛卡尔积。Cascade profile 从 192 个
        原始组合中抽象出 86 个水平有效阵元，并用等间距等效相位中心建模。
        """

        raw_count = self.num_tx * self.num_rx
        if self.num_channels == raw_count:
            tx_positions = np.repeat(self.tx_positions_m, self.num_rx, axis=0)
            rx_positions = np.tile(self.rx_positions_m, (self.num_tx, 1))
            return tx_positions, rx_positions

        virtual_positions = np.zeros((self.num_channels, 3), dtype=np.float64)
        virtual_positions[:, 0] = np.arange(self.num_channels, dtype=np.float64) * self.element_spacing_m
        return virtual_positions / 2.0, virtual_positions / 2.0

    @property
    def radar_phase_center_m(self) -> np.ndarray:
        """雷达相位中心。

        可见性判断和散射点入射方向需要一个统一的雷达参考点。
        这里用所有 Tx/Rx 阵元位置的平均值作为近似相位中心。
        """

        tx_positions, rx_positions = self.channel_pair_positions_m
        all_positions = np.vstack([tx_positions, rx_positions])
        return np.mean(all_positions, axis=0)


@dataclass(frozen=True)
class TargetMotion:
    """目标整体运动与姿态参数。

    当前模型把网格目标看作一个刚体：先按欧拉角旋转，再按初始位置和速度
    做平移。散射强度通过 `reflectivity` 做整体缩放。
    """

    initial_position_m: tuple[float, float, float] = (0.0, 10.0, 0.0)
    velocity_m_s: tuple[float, float, float] = (0.0, -1.0, 0.0)
    euler_deg: tuple[float, float, float] = (0.0, 0.0, 0.0)
    reflectivity: float = 1.0

    @property
    def initial_position_array(self) -> np.ndarray:
        """把元组形式的初始位置转成 numpy 数组，方便向量运算。"""

        return np.asarray(self.initial_position_m, dtype=np.float64)

    @property
    def velocity_array(self) -> np.ndarray:
        """把元组形式的速度转成 numpy 数组，方便按 slow-time 更新位置。"""

        return np.asarray(self.velocity_m_s, dtype=np.float64)
