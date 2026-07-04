"""几何基础工具。

这个文件放置与雷达无关的三维几何操作：网格三角面表示、三角面中心/法向/
面积计算、欧拉角旋转、刚体变换，以及射线和三角面的相交测试。它们被
可见性判断、散射点建模和信号合成共同复用。

这里的函数故意保持“纯几何”：
- 不知道雷达频率、chirp 或 MIMO 通道。
- 只处理点、向量、三角面和射线。
- 这样后续可见性、散射和信号模块可以共享同一套几何语义。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class TriangleMesh:
    """三角网格的最小表示。

    `vertices` 是 N x 3 顶点坐标，`faces` 是 M x 3 顶点索引。
    这里不保存材质、纹理、法线等渲染信息，因为雷达仿真只需要几何形状。
    """

    vertices: np.ndarray
    faces: np.ndarray

    def triangles(self) -> np.ndarray:
        """把面索引展开成 M x 3 x 3 的三角面坐标数组。"""

        return self.vertices[self.faces]

    def with_face_budget(self, max_faces: int | None, seed: int = 0) -> "TriangleMesh":
        """按面数量预算随机下采样网格。

        复杂模型可能有成千上万个三角面，逐面做遮挡检测和散射合成会很慢。
        这里随机保留一部分 face，并重新映射顶点索引，使输出仍是一个自洽网格。
        """

        if max_faces is None or max_faces <= 0 or len(self.faces) <= max_faces:
            return self

        rng = np.random.default_rng(seed)
        chosen_faces = np.sort(rng.choice(len(self.faces), size=max_faces, replace=False))
        faces = self.faces[chosen_faces]
        used_vertices, inverse = np.unique(faces.reshape(-1), return_inverse=True)
        vertices = self.vertices[used_vertices]
        remapped_faces = inverse.reshape(-1, 3)
        return TriangleMesh(vertices=vertices, faces=remapped_faces.astype(np.int32))


def ensure_float_array(values: np.ndarray | list[float] | tuple[float, ...]) -> np.ndarray:
    """统一把输入转成 float64 数组，避免整数数组参与几何计算。"""

    return np.asarray(values, dtype=np.float64)


def triangle_centers(triangles: np.ndarray) -> np.ndarray:
    """计算每个三角面的几何中心，用作简化散射点位置。"""

    return np.mean(triangles, axis=1)


def triangle_normals(triangles: np.ndarray) -> np.ndarray:
    """计算单位法向量。

    法向由两个边向量叉乘得到。退化三角形面积为 0 时，norm 会变成 0；
    这里用 1 替代 0 做安全除法，避免产生 NaN。
    """

    edge_1 = triangles[:, 1, :] - triangles[:, 0, :]
    edge_2 = triangles[:, 2, :] - triangles[:, 0, :]
    normals = np.cross(edge_1, edge_2)
    norms = np.linalg.norm(normals, axis=1, keepdims=True)
    safe_norms = np.where(norms > 0.0, norms, 1.0)
    return normals / safe_norms


def triangle_areas(triangles: np.ndarray) -> np.ndarray:
    """计算三角面面积，散射强度会按面积放大或缩小。"""

    edge_1 = triangles[:, 1, :] - triangles[:, 0, :]
    edge_2 = triangles[:, 2, :] - triangles[:, 0, :]
    return 0.5 * np.linalg.norm(np.cross(edge_1, edge_2), axis=1)


def euler_rotation_matrix(roll_deg: float, pitch_deg: float, yaw_deg: float) -> np.ndarray:
    """由 roll/pitch/yaw 生成旋转矩阵。

    旋转顺序为 `Rz @ Ry @ Rx`，也就是先绕 x 轴 roll，再绕 y 轴 pitch，
    最后绕 z 轴 yaw。这个约定会影响目标姿态，调用方需要保持一致。
    """

    roll, pitch, yaw = np.deg2rad([roll_deg, pitch_deg, yaw_deg])
    cx, cy, cz = np.cos([roll, pitch, yaw])
    sx, sy, sz = np.sin([roll, pitch, yaw])

    rx = np.array([[1.0, 0.0, 0.0], [0.0, cx, -sx], [0.0, sx, cx]])
    ry = np.array([[cy, 0.0, sy], [0.0, 1.0, 0.0], [-sy, 0.0, cy]])
    rz = np.array([[cz, -sz, 0.0], [sz, cz, 0.0], [0.0, 0.0, 1.0]])
    return rz @ ry @ rx


def transform_vertices(vertices: np.ndarray, rotation: np.ndarray, translation: np.ndarray) -> np.ndarray:
    """对网格顶点做刚体变换：先旋转，再平移。"""

    return vertices @ rotation.T + translation


def ray_triangle_intersection(
    origin: np.ndarray,
    direction: np.ndarray,
    triangle: np.ndarray,
    max_distance: float,
    epsilon: float = 1e-9,
) -> float | None:
    """Moller-Trumbore 射线三角形相交测试。

    返回从 `origin` 沿 `direction` 打到三角面的距离；如果没有相交，或交点
    不在 `max_distance` 之前，则返回 None。可见性模块用它判断某个三角面
    是否被其他三角面挡住。
    """

    vertex_0, vertex_1, vertex_2 = triangle
    edge_1 = vertex_1 - vertex_0
    edge_2 = vertex_2 - vertex_0
    p_vec = np.cross(direction, edge_2)
    det = np.dot(edge_1, p_vec)
    # det 接近 0 表示射线与三角面近似平行，无法得到稳定交点。
    if abs(det) < epsilon:
        return None

    inv_det = 1.0 / det
    t_vec = origin - vertex_0
    u = np.dot(t_vec, p_vec) * inv_det
    # u/v 是三角形内部的重心坐标约束，超出范围说明交点落在三角形外。
    if u < 0.0 or u > 1.0:
        return None

    q_vec = np.cross(t_vec, edge_1)
    v = np.dot(direction, q_vec) * inv_det
    if v < 0.0 or u + v > 1.0:
        return None

    distance = np.dot(edge_2, q_vec) * inv_det
    if distance <= epsilon or distance >= max_distance - epsilon:
        return None
    return distance
