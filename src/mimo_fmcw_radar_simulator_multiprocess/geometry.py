from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class TriangleMesh:
    vertices: np.ndarray
    faces: np.ndarray

    def triangles(self) -> np.ndarray:
        return self.vertices[self.faces]

    def with_face_budget(self, max_faces: int | None, seed: int = 0) -> "TriangleMesh":
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
    return np.asarray(values, dtype=np.float64)


def triangle_centers(triangles: np.ndarray) -> np.ndarray:
    return np.mean(triangles, axis=1)


def triangle_normals(triangles: np.ndarray) -> np.ndarray:
    edge_1 = triangles[:, 1, :] - triangles[:, 0, :]
    edge_2 = triangles[:, 2, :] - triangles[:, 0, :]
    normals = np.cross(edge_1, edge_2)
    norms = np.linalg.norm(normals, axis=1, keepdims=True)
    safe_norms = np.where(norms > 0.0, norms, 1.0)
    return normals / safe_norms


def triangle_areas(triangles: np.ndarray) -> np.ndarray:
    edge_1 = triangles[:, 1, :] - triangles[:, 0, :]
    edge_2 = triangles[:, 2, :] - triangles[:, 0, :]
    return 0.5 * np.linalg.norm(np.cross(edge_1, edge_2), axis=1)


def euler_rotation_matrix(roll_deg: float, pitch_deg: float, yaw_deg: float) -> np.ndarray:
    roll, pitch, yaw = np.deg2rad([roll_deg, pitch_deg, yaw_deg])
    cx, cy, cz = np.cos([roll, pitch, yaw])
    sx, sy, sz = np.sin([roll, pitch, yaw])

    rx = np.array([[1.0, 0.0, 0.0], [0.0, cx, -sx], [0.0, sx, cx]])
    ry = np.array([[cy, 0.0, sy], [0.0, 1.0, 0.0], [-sy, 0.0, cy]])
    rz = np.array([[cz, -sz, 0.0], [sz, cz, 0.0], [0.0, 0.0, 1.0]])
    return rz @ ry @ rx


def transform_vertices(vertices: np.ndarray, rotation: np.ndarray, translation: np.ndarray) -> np.ndarray:
    return vertices @ rotation.T + translation


def ray_triangle_intersection(
    origin: np.ndarray,
    direction: np.ndarray,
    triangle: np.ndarray,
    max_distance: float,
    epsilon: float = 1e-9,
) -> float | None:
    vertex_0, vertex_1, vertex_2 = triangle
    edge_1 = vertex_1 - vertex_0
    edge_2 = vertex_2 - vertex_0
    p_vec = np.cross(direction, edge_2)
    det = np.dot(edge_1, p_vec)
    if abs(det) < epsilon:
        return None

    inv_det = 1.0 / det
    t_vec = origin - vertex_0
    u = np.dot(t_vec, p_vec) * inv_det
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
