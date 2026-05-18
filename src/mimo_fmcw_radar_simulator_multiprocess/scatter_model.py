from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .geometry import triangle_areas, triangle_centers, triangle_normals


@dataclass(frozen=True)
class ScatterSet:
    centers_m: np.ndarray
    strengths: np.ndarray


def build_scatter_set(triangles: np.ndarray, radar_origin_m: np.ndarray, reflectivity: float = 1.0) -> ScatterSet:
    centers = triangle_centers(triangles)
    normals = triangle_normals(triangles)
    areas = triangle_areas(triangles)

    los_vectors = radar_origin_m[None, :] - centers
    los_norms = np.linalg.norm(los_vectors, axis=1, keepdims=True)
    safe_norms = np.where(los_norms > 0.0, los_norms, 1.0)
    los_directions = los_vectors / safe_norms
    incidence = np.clip(np.sum(normals * los_directions, axis=1), 0.0, None)

    strengths = reflectivity * areas * incidence
    keep = strengths > 0.0
    return ScatterSet(centers_m=centers[keep], strengths=strengths[keep])
