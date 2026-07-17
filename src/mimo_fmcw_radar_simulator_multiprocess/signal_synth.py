"""RDC 原始雷达数据合成。

RDC 指 range-Doppler cube 前的原始复数采样数据，形状为：
`num_adc_samples x num_chirps x num_channels`。

整体流程：
1. 按 chirp 把目标网格移动到当前时刻位置。
2. 取出雷达可见三角面。
3. 把可见面转换为散射点。
4. 对每个 Tx/Rx 虚拟通道合成 FMCW beat signal。
5. 多进程按 chirp 区间并行，最后拼回完整 RDC。

这是项目里最核心的文件：它把网格几何、目标运动、雷达参数、散射模型和
多进程执行串成一个完整的原始雷达数据生成流程。读代码时建议先看
`simulate_rdc`，再看 `_simulate_block`，最后看 `_synthesize_channel`。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .geometry import TriangleMesh, euler_rotation_matrix, transform_vertices
from .multiprocess_engine import default_worker_count, parallel_map, split_indices
from .radar_model import RadarConfig, TargetMotion
from .scatter_model import build_scatter_set
from .visibility import extract_visible_triangles


@dataclass(frozen=True)
class _BlockTask:
    """一个进程要处理的 chirp 区间任务。"""

    start: int
    stop: int
    mesh: TriangleMesh
    radar: RadarConfig
    target: TargetMotion


def simulate_rdc(
    mesh: TriangleMesh,
    radar: RadarConfig,
    target: TargetMotion,
    workers: int | None = None,
) -> np.ndarray:
    """生成 MIMO FMCW 雷达原始复数采样数据。

    返回数组维度为：
    `(num_adc_samples, num_chirps, num_channels)`。
    第 0 维是 fast-time，第 1 维是 slow-time，第 2 维是虚拟阵列通道。
    """

    worker_count = default_worker_count() if workers is None else max(1, workers)
    tasks = [
        _BlockTask(start=start, stop=stop, mesh=mesh, radar=radar, target=target)
        for start, stop in split_indices(radar.num_chirps, worker_count)
    ]
    blocks = parallel_map(_simulate_block, tasks, worker_count)

    channel_count = radar.num_channels
    rdc = np.zeros((radar.num_adc_samples, radar.num_chirps, channel_count), dtype=np.complex128)
    for start, stop, block in blocks:
        # 每个 worker 返回一个连续 chirp 片段，直接写回 slow-time 维度。
        rdc[:, start:stop, :] = block
    return rdc


def _simulate_block(task: _BlockTask) -> tuple[int, int, np.ndarray]:
    """合成一个 chirp 区间内的 RDC 子块。

    这个函数会被多进程调用，因此参数集中在 `_BlockTask` 中，返回值带上
    `start/stop`，方便主进程把结果拼回原始时间顺序。
    """

    radar = task.radar
    target = task.target
    mesh = task.mesh

    rotation = euler_rotation_matrix(*target.euler_deg)
    base_vertices = mesh.vertices
    # 每个有效 Tx/Rx 位置对形成一个虚拟通道；通道间相位差用于后续角度 FFT。
    channel_tx_positions, channel_rx_positions = radar.channel_pair_positions_m
    channel_pairs = zip(channel_tx_positions, channel_rx_positions)
    channel_pairs = tuple(channel_pairs)
    fast_time = radar.fast_time_s

    block = np.zeros(
        (radar.num_adc_samples, task.stop - task.start, radar.num_channels),
        dtype=np.complex128,
    )

    for chirp_index in range(task.start, task.stop):
        slow_time = radar.slow_time_s[chirp_index]
        # 目标作为刚体运动：当前平移 = 初始位置 + 速度 * slow-time。
        translation = target.initial_position_array + target.velocity_array * slow_time
        transformed_vertices = transform_vertices(base_vertices, rotation=rotation, translation=translation)
        triangles = transformed_vertices[mesh.faces]

        # 先做几何可见性筛选，减少后续散射点数量，也避免背面/遮挡面贡献回波。
        visibility = extract_visible_triangles(triangles, radar.radar_phase_center_m)
        if len(visibility.face_indices) == 0:
            continue

        # 可见三角面被近似为散射点，强度由面积、入射角和整体反射率决定。
        scatter = build_scatter_set(
            triangles=visibility.triangles,
            radar_origin_m=radar.radar_phase_center_m,
            reflectivity=target.reflectivity,
        )
        if len(scatter.strengths) == 0:
            continue

        local_chirp = chirp_index - task.start
        for channel_index, (tx_position, rx_position) in enumerate(channel_pairs):
            # 同一组散射点在不同 Tx/Rx 通道下的路径长度不同，因此相位也不同。
            block[:, local_chirp, channel_index] = _synthesize_channel(
                centers_m=scatter.centers_m,
                strengths=scatter.strengths,
                tx_position_m=tx_position,
                rx_position_m=rx_position,
                radar=radar,
                fast_time_s=fast_time,
            )

    return task.start, task.stop, block


def _synthesize_channel(
    centers_m: np.ndarray,
    strengths: np.ndarray,
    tx_position_m: np.ndarray,
    rx_position_m: np.ndarray,
    radar: RadarConfig,
    fast_time_s: np.ndarray,
) -> np.ndarray:
    """合成单个 Tx/Rx 通道的 FMCW beat signal。

    对每个散射点：
    - 先计算 Tx->散射点->Rx 的双程距离和传播时延。
    - 由 FMCW 斜率得到 beat frequency。
    - 由载频和调频项得到静态相位。
    - 对 fast-time 采样点生成复指数并按散射强度叠加。
    """

    light_speed = radar.light_speed
    tx_distances = np.linalg.norm(centers_m - tx_position_m[None, :], axis=1)
    rx_distances = np.linalg.norm(centers_m - rx_position_m[None, :], axis=1)
    round_trip_delay = (tx_distances + rx_distances) / light_speed

    # 简化距离衰减：Tx 距离和 Rx 距离越远，振幅越弱；下限避免除 0。
    amplitudes = strengths / np.maximum(tx_distances * rx_distances, 1e-12)
    beat_frequency = radar.slope_hz_per_s * round_trip_delay
    # 解调后的 FMCW 相位：载频传播相位减去 chirp 延迟产生的二次项。
    static_phase = 2.0 * np.pi * (
        radar.carrier_hz * round_trip_delay
        - 0.5 * radar.slope_hz_per_s * round_trip_delay * round_trip_delay
    )

    # phase 形状为 `散射点数 x ADC采样点数`，最后沿散射点维度求和。
    phase = static_phase[:, None] + 2.0 * np.pi * beat_frequency[:, None] * fast_time_s[None, :]
    return np.sum(amplitudes[:, None] * np.exp(1j * phase), axis=0)
