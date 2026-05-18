from __future__ import annotations

import struct
from pathlib import Path

import numpy as np

from .geometry import TriangleMesh


def load_mesh(path: str | Path) -> TriangleMesh:
    mesh_path = Path(path)
    suffix = mesh_path.suffix.lower()
    if suffix == ".obj":
        return _load_obj(mesh_path)
    if suffix == ".stl":
        return _load_stl(mesh_path)
    if suffix == ".glb":
        return _load_glb(mesh_path)
    raise ValueError(f"Unsupported mesh format: {mesh_path.suffix}")


def _load_obj(path: Path) -> TriangleMesh:
    vertices: list[list[float]] = []
    faces: list[list[int]] = []

    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("v "):
                _, x, y, z = line.split()[:4]
                vertices.append([float(x), float(y), float(z)])
                continue
            if line.startswith("f "):
                parts = line.split()[1:]
                indices = [int(part.split("/")[0]) - 1 for part in parts]
                faces.extend(_triangulate_face(indices))

    if not vertices or not faces:
        raise ValueError(f"Mesh file contains no usable geometry: {path}")
    return TriangleMesh(vertices=np.asarray(vertices, dtype=np.float64), faces=np.asarray(faces, dtype=np.int32))


def _load_stl(path: Path) -> TriangleMesh:
    file_size = path.stat().st_size
    with path.open("rb") as handle:
        header = handle.read(80)
        count_bytes = handle.read(4)
        if len(count_bytes) != 4:
            raise ValueError(f"Invalid STL file: {path}")
        triangle_count = struct.unpack("<I", count_bytes)[0]
        is_binary = file_size == 84 + triangle_count * 50 and not header[:5].lower() == b"solid"

    if is_binary:
        return _load_binary_stl(path)
    return _load_ascii_stl(path)


def _load_ascii_stl(path: Path) -> TriangleMesh:
    vertices: list[list[float]] = []
    faces: list[list[int]] = []
    current: list[list[float]] = []

    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if line.startswith("vertex"):
                _, x, y, z = line.split()
                current.append([float(x), float(y), float(z)])
                if len(current) == 3:
                    start = len(vertices)
                    vertices.extend(current)
                    faces.append([start, start + 1, start + 2])
                    current = []

    if not vertices or not faces:
        raise ValueError(f"Mesh file contains no usable geometry: {path}")
    return TriangleMesh(vertices=np.asarray(vertices, dtype=np.float64), faces=np.asarray(faces, dtype=np.int32))


def _load_binary_stl(path: Path) -> TriangleMesh:
    vertices: list[list[float]] = []
    faces: list[list[int]] = []

    with path.open("rb") as handle:
        handle.read(80)
        triangle_count = struct.unpack("<I", handle.read(4))[0]
        for _ in range(triangle_count):
            handle.read(12)
            triangle = []
            for _ in range(3):
                x, y, z = struct.unpack("<fff", handle.read(12))
                triangle.append([float(x), float(y), float(z)])
            handle.read(2)
            start = len(vertices)
            vertices.extend(triangle)
            faces.append([start, start + 1, start + 2])

    return TriangleMesh(vertices=np.asarray(vertices, dtype=np.float64), faces=np.asarray(faces, dtype=np.int32))


def _load_glb(path: Path) -> TriangleMesh:
    import trimesh

    loaded = trimesh.load(path, force="mesh", process=False)
    vertices = np.asarray(loaded.vertices, dtype=np.float64)
    faces = np.asarray(loaded.faces, dtype=np.int32)
    if vertices.size == 0 or faces.size == 0:
        raise ValueError(f"Mesh file contains no usable geometry: {path}")
    return TriangleMesh(vertices=vertices, faces=faces)


def _triangulate_face(indices: list[int]) -> list[list[int]]:
    if len(indices) < 3:
        return []
    if len(indices) == 3:
        return [indices]
    triangles: list[list[int]] = []
    for index in range(1, len(indices) - 1):
        triangles.append([indices[0], indices[index], indices[index + 1]])
    return triangles
