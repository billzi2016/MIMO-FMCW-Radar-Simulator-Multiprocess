"""网格文件加载器。

仿真只需要三角面几何，因此这里把 OBJ/STL/GLB 都统一加载为
`TriangleMesh(vertices, faces)`。材质、纹理、骨骼动画等信息不会进入
雷达散射模型，避免把渲染语义和雷达几何语义混在一起。

本文件的目标不是做完整 3D 资产导入器，而是把常见 mesh 文件压缩成
雷达仿真真正需要的最小数据结构：顶点坐标和三角面索引。
"""

from __future__ import annotations

import struct
from pathlib import Path

import numpy as np

from .geometry import TriangleMesh


def load_mesh(path: str | Path) -> TriangleMesh:
    """按文件扩展名选择网格解析器。

    支持：
    - `.obj`：手写解析，只读取顶点和面。
    - `.stl`：自动区分 ASCII / binary STL。
    - `.glb`：交给 trimesh 读取，因为 GLB 二进制结构更复杂。
    """

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
    """读取 OBJ 网格。

    OBJ 的 face 可能是三角形，也可能是四边形或多边形；本项目统一把它们
    扇形剖分成三角面，后续可见性和散射计算只处理三角面。
    """

    vertices: list[list[float]] = []
    faces: list[list[int]] = []

    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("v "):
                # 这里只读取几何顶点 `v x y z`，忽略纹理坐标和法线。
                _, x, y, z = line.split()[:4]
                vertices.append([float(x), float(y), float(z)])
                continue
            if line.startswith("f "):
                parts = line.split()[1:]
                # OBJ 索引从 1 开始，且可能写成 v/vt/vn；雷达仿真只需要顶点索引。
                indices = [int(part.split("/")[0]) - 1 for part in parts]
                faces.extend(_triangulate_face(indices))

    if not vertices or not faces:
        raise ValueError(f"Mesh file contains no usable geometry: {path}")
    return TriangleMesh(vertices=np.asarray(vertices, dtype=np.float64), faces=np.asarray(faces, dtype=np.int32))


def _load_stl(path: Path) -> TriangleMesh:
    """读取 STL，并根据文件大小判断二进制还是 ASCII。

    二进制 STL 的大小满足 `84 + triangle_count * 50`。有些 ASCII STL 也以
    `solid` 开头，所以这里同时用文件大小和 header 做保守判断。
    """

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
    """读取 ASCII STL。

    ASCII STL 中每个三角面由三个 `vertex x y z` 行组成。这里直接把每个
    三角面的三个顶点追加到顶点表，不做顶点去重，逻辑更简单稳定。
    """

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
    """读取 binary STL。

    每个三角形记录包含：法向量 12 字节、三个顶点各 12 字节、属性 2 字节。
    文件里的法向量不一定可信，后续统一由几何模块重新计算。
    """

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
    """读取 GLB 网格。

    GLB 结构复杂，手写解析成本高且容易出错，所以这里使用 trimesh。
    `process=False` 避免自动修复/合并改变原始几何。
    """

    import trimesh

    loaded = trimesh.load(path, force="mesh", process=False)
    vertices = np.asarray(loaded.vertices, dtype=np.float64)
    faces = np.asarray(loaded.faces, dtype=np.int32)
    if vertices.size == 0 or faces.size == 0:
        raise ValueError(f"Mesh file contains no usable geometry: {path}")
    return TriangleMesh(vertices=vertices, faces=faces)


def _triangulate_face(indices: list[int]) -> list[list[int]]:
    """把一个多边形面扇形剖分成多个三角形。

    例如 `[0, 1, 2, 3]` 会变成 `[0,1,2]` 和 `[0,2,3]`。这种方式对凸多边形
    最直接；作为教学级仿真输入，足够处理常见 OBJ 网格。
    """

    if len(indices) < 3:
        return []
    if len(indices) == 3:
        return [indices]
    triangles: list[list[int]] = []
    for index in range(1, len(indices) - 1):
        triangles.append([indices[0], indices[index], indices[index + 1]])
    return triangles
