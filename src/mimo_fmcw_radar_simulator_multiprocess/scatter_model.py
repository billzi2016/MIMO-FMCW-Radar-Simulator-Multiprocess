"""从可见三角面构造简化散射点。

本项目没有做全电磁仿真，而是采用几何光学风格的近似：每个可见三角面用
中心点表示散射位置，面积和入射角决定散射强度。这种模型足够支撑教学和
流水线验证，也能保持计算量可控。

这个抽象是连接“几何世界”和“雷达信号世界”的桥：
- 输入是三角面坐标。
- 输出是散射点位置和实数强度。
- 相位、距离衰减和 beat frequency 交给 `signal_synth.py` 处理。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .geometry import triangle_areas, triangle_centers, triangle_normals


@dataclass(frozen=True)
class ScatterSet:
    """散射点集合。

    `centers_m` 是散射点三维位置，`strengths` 是对应复信号幅度前的实数权重。
    真正的距离衰减、相位和 beat frequency 在信号合成阶段处理。
    """

    centers_m: np.ndarray
    strengths: np.ndarray


def build_scatter_set(triangles: np.ndarray, radar_origin_m: np.ndarray, reflectivity: float = 1.0) -> ScatterSet:
    """把三角面转换为散射点。

    强度近似为：
    `reflectivity * triangle_area * max(dot(normal, line_of_sight), 0)`。
    这样面积越大、越正对雷达的面越强；背向雷达的面会被压到 0。
    """

    centers = triangle_centers(triangles)
    normals = triangle_normals(triangles)
    areas = triangle_areas(triangles)

    # 视线方向从三角面中心指向雷达，用于计算入射角余弦。
    los_vectors = radar_origin_m[None, :] - centers
    los_norms = np.linalg.norm(los_vectors, axis=1, keepdims=True)
    safe_norms = np.where(los_norms > 0.0, los_norms, 1.0)
    los_directions = los_vectors / safe_norms
    # incidence 小于 0 表示背向雷达，clip 到 0 后不再贡献散射。
    incidence = np.clip(np.sum(normals * los_directions, axis=1), 0.0, None)

    strengths = reflectivity * areas * incidence
    keep = strengths > 0.0
    return ScatterSet(centers_m=centers[keep], strengths=strengths[keep])
