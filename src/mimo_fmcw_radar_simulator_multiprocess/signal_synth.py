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
    worker_count = default_worker_count() if workers is None else max(1, workers)
    tasks = [
        _BlockTask(start=start, stop=stop, mesh=mesh, radar=radar, target=target)
        for start, stop in split_indices(radar.num_chirps, worker_count)
    ]
    blocks = parallel_map(_simulate_block, tasks, worker_count)

    channel_count = radar.num_tx * radar.num_rx
    rdc = np.zeros((radar.num_adc_samples, radar.num_chirps, channel_count), dtype=np.complex128)
    for start, stop, block in blocks:
        rdc[:, start:stop, :] = block
    return rdc


def _simulate_block(task: _BlockTask) -> tuple[int, int, np.ndarray]:
    radar = task.radar
    target = task.target
    mesh = task.mesh

    rotation = euler_rotation_matrix(*target.euler_deg)
    base_vertices = mesh.vertices
    channel_pairs = [(tx, rx) for tx in radar.tx_positions_m for rx in radar.rx_positions_m]
    fast_time = radar.fast_time_s

    block = np.zeros(
        (radar.num_adc_samples, task.stop - task.start, radar.num_tx * radar.num_rx),
        dtype=np.complex128,
    )

    for chirp_index in range(task.start, task.stop):
        slow_time = radar.slow_time_s[chirp_index]
        translation = target.initial_position_array + target.velocity_array * slow_time
        transformed_vertices = transform_vertices(base_vertices, rotation=rotation, translation=translation)
        triangles = transformed_vertices[mesh.faces]

        visibility = extract_visible_triangles(triangles, radar.radar_phase_center_m)
        if len(visibility.face_indices) == 0:
            continue

        scatter = build_scatter_set(
            triangles=visibility.triangles,
            radar_origin_m=radar.radar_phase_center_m,
            reflectivity=target.reflectivity,
        )
        if len(scatter.strengths) == 0:
            continue

        local_chirp = chirp_index - task.start
        for channel_index, (tx_position, rx_position) in enumerate(channel_pairs):
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
    light_speed = radar.light_speed
    tx_distances = np.linalg.norm(centers_m - tx_position_m[None, :], axis=1)
    rx_distances = np.linalg.norm(centers_m - rx_position_m[None, :], axis=1)
    round_trip_delay = (tx_distances + rx_distances) / light_speed

    amplitudes = strengths / np.maximum(tx_distances * rx_distances, 1e-12)
    beat_frequency = radar.slope_hz_per_s * round_trip_delay
    static_phase = 2.0 * np.pi * (
        radar.carrier_hz * round_trip_delay
        - 0.5 * radar.slope_hz_per_s * round_trip_delay * round_trip_delay
    )

    phase = static_phase[:, None] + 2.0 * np.pi * beat_frequency[:, None] * fast_time_s[None, :]
    return np.sum(amplitudes[:, None] * np.exp(1j * phase), axis=0)
