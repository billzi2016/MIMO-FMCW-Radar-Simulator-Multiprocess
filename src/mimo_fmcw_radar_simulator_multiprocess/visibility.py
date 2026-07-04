"""三角面的雷达可见性筛选。

毫米波仿真中，并不是目标网格的所有三角面都会产生有效回波。背向雷达的面
入射角不合理，前方但被其他面遮挡的面也不应直接参与散射。这个模块做的是
一个几何级近似：先筛正面，再用射线相交做遮挡剔除。

它不是高性能渲染器里的 BVH/光线追踪实现，而是教学友好的直接算法。
因此复杂度较高，但每一步都能对应到“雷达能不能看到这个面”的物理直觉。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .geometry import ray_triangle_intersection, triangle_centers, triangle_normals


@dataclass(frozen=True)
class VisibilityResult:
    """可见性筛选结果。

    `face_indices` 保存原输入三角面中的索引，`triangles` 保存对应的三角面坐标。
    后续散射模型只处理这些可见三角面。
    """

    face_indices: np.ndarray
    triangles: np.ndarray


def extract_visible_triangles(triangles: np.ndarray, radar_origin_m: np.ndarray) -> VisibilityResult:
    """提取从雷达相位中心可见的三角面。

    步骤：
    1. 计算每个三角面的中心和法向。
    2. 用法向与雷达到面的视线方向点积，先去掉背向雷达的面。
    3. 对剩余候选面按距离从近到远排序。
    4. 从雷达向候选面中心发射射线，如果中途碰到其他三角面，则认为被遮挡。
    """

    if len(triangles) == 0:
        return VisibilityResult(face_indices=np.empty(0, dtype=np.int32), triangles=np.empty((0, 3, 3), dtype=np.float64))

    centers = triangle_centers(triangles)
    normals = triangle_normals(triangles)

    look_vectors = radar_origin_m[None, :] - centers
    distances = np.linalg.norm(look_vectors, axis=1)
    safe_distances = np.where(distances > 0.0, distances, 1.0)
    directions = look_vectors / safe_distances[:, None]

    # 点积大于 0 表示三角面法向大致朝向雷达，才可能产生有效镜面/漫反射回波。
    front_mask = np.sum(normals * directions, axis=1) > 1e-9
    candidates = np.flatnonzero(front_mask)
    # 近处遮挡远处，所以候选面按距离排序，有利于理解遮挡逻辑。
    ordered = candidates[np.argsort(distances[candidates])]

    visible: list[int] = []
    for face_index in ordered:
        direction = centers[face_index] - radar_origin_m
        distance = np.linalg.norm(direction)
        if distance <= 0.0:
            continue
        unit_direction = direction / distance
        occluded = False
        for blocker_index, blocker in enumerate(triangles):
            if blocker_index == face_index:
                continue
            # 如果雷达到该面中心的线段先击中其他三角面，则该面被遮挡。
            hit = ray_triangle_intersection(
                origin=radar_origin_m,
                direction=unit_direction,
                triangle=blocker,
                max_distance=distance,
            )
            if hit is not None:
                occluded = True
                break
        if not occluded:
            visible.append(face_index)

    visible_indices = np.asarray(visible, dtype=np.int32)
    return VisibilityResult(face_indices=visible_indices, triangles=triangles[visible_indices])
