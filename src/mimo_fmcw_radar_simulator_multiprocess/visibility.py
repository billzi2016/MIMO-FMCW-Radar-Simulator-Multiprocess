from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .geometry import ray_triangle_intersection, triangle_centers, triangle_normals


@dataclass(frozen=True)
class VisibilityResult:
    face_indices: np.ndarray
    triangles: np.ndarray


def extract_visible_triangles(triangles: np.ndarray, radar_origin_m: np.ndarray) -> VisibilityResult:
    if len(triangles) == 0:
        return VisibilityResult(face_indices=np.empty(0, dtype=np.int32), triangles=np.empty((0, 3, 3), dtype=np.float64))

    centers = triangle_centers(triangles)
    normals = triangle_normals(triangles)

    look_vectors = radar_origin_m[None, :] - centers
    distances = np.linalg.norm(look_vectors, axis=1)
    safe_distances = np.where(distances > 0.0, distances, 1.0)
    directions = look_vectors / safe_distances[:, None]

    front_mask = np.sum(normals * directions, axis=1) > 1e-9
    candidates = np.flatnonzero(front_mask)
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
