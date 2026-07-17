"""命令行入口。

这个文件把项目的几个核心模块串起来：
加载网格 -> 构造雷达参数和目标运动 -> 合成 RDC -> 跑 FFT 流水线 -> 保存 NPZ。
它不直接实现物理模型，主要负责参数解析和流程编排。

换句话说，这里是“应用层入口”，不是算法层。参数越集中，后续做实验时
越不需要改源代码，只需要改命令行参数即可。
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from .fft_pipeline import run_fft_pipeline
from .mesh_loader import load_mesh
from .multiprocess_engine import default_worker_count
from .profile_loader import load_radar_profile
from .radar_model import RadarConfig, TargetMotion
from .signal_synth import simulate_rdc


def main() -> None:
    """执行一次完整仿真并保存结果。"""

    arguments = _build_parser().parse_args()

    radar, profile_name = _build_radar_config(arguments)
    # 目标模型是刚体运动：初始位置、速度、姿态角和整体反射率。
    target = TargetMotion(
        initial_position_m=(arguments.x0_m, arguments.y0_m, arguments.z0_m),
        velocity_m_s=(arguments.vx_m_s, arguments.vy_m_s, arguments.vz_m_s),
        euler_deg=(arguments.roll_deg, arguments.pitch_deg, arguments.yaw_deg),
        reflectivity=arguments.reflectivity,
    )

    mesh = load_mesh(arguments.mesh)
    workers = arguments.workers if arguments.workers is not None else default_worker_count()
    # 大模型可通过 max_faces 下采样，先保证教学流程能跑通，再逐步提高精度。
    mesh = mesh.with_face_budget(arguments.max_faces)
    rdc = simulate_rdc(mesh=mesh, radar=radar, target=target, workers=workers)
    outputs = run_fft_pipeline(rdc, radar)

    output_path = Path(arguments.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output_path, **outputs)

    print(f"Saved simulation output to: {output_path}")
    print(f"RDC shape: {outputs['rdc'].shape}")
    print(f"Range-Doppler-Angle cube shape: {outputs['range_doppler_angle_cube'].shape}")
    print(f"Faces used: {mesh.faces.shape[0]}")
    print(f"Workers used: {workers}")
    if profile_name is not None:
        print(f"Radar profile: {profile_name}")


def _build_radar_config(arguments: argparse.Namespace) -> tuple[RadarConfig, str | None]:
    """合并内置默认值、TOML profile 和显式命令行覆盖参数。"""

    overrides = {
        "carrier_hz": arguments.carrier_hz,
        "bandwidth_hz": arguments.bandwidth_hz,
        "chirp_duration_s": arguments.chirp_duration_s,
        "num_adc_samples": arguments.num_adc_samples,
        "num_chirps": arguments.num_chirps,
        "num_tx": arguments.num_tx,
        "num_rx": arguments.num_rx,
        "azimuth_virtual_channels": arguments.azimuth_virtual_channels,
    }
    if arguments.profile is None:
        defaults = RadarConfig()
        values = {
            key: value if value is not None else getattr(defaults, key)
            for key, value in overrides.items()
        }
        return RadarConfig(**values), None

    project_root = Path(__file__).resolve().parents[2]
    profile = load_radar_profile(arguments.profile, project_root / "profiles")
    return profile.to_radar_config(**overrides), profile.name


def _build_parser() -> argparse.ArgumentParser:
    """构造 CLI 参数解析器。

    参数分为四组：输入输出、多进程/网格规模、雷达配置、目标运动配置。
    这样可以在不改代码的情况下快速测试不同雷达参数和目标运动。
    """

    project_root = Path(__file__).resolve().parents[2]
    default_mesh = project_root / "examples" / "meshes" / "box.obj"
    default_output = project_root / "examples" / "output" / "box_run.npz"

    parser = argparse.ArgumentParser(description="Mesh-based MIMO FMCW radar simulator.")
    parser.add_argument("--mesh", type=Path, default=default_mesh, help="Path to OBJ or STL mesh.")
    parser.add_argument("--output", type=Path, default=default_output, help="Path to NPZ output file.")
    parser.add_argument("--workers", type=int, default=None, help="Multiprocess worker count. Default: cpu_count() // 2.")
    parser.add_argument("--max-faces", type=int, default=None, help="Optional face-budget downsampling before simulation.")

    # 雷达波形和阵列规模参数。
    parser.add_argument("--profile", type=str, default=None, help="Radar profile name or TOML path.")
    parser.add_argument("--carrier-hz", type=float, default=None)
    parser.add_argument("--bandwidth-hz", type=float, default=None)
    parser.add_argument("--chirp-duration-s", type=float, default=None)
    parser.add_argument("--num-adc-samples", type=int, default=None)
    parser.add_argument("--num-chirps", type=int, default=None)
    parser.add_argument("--num-tx", type=int, default=None)
    parser.add_argument("--num-rx", type=int, default=None)
    parser.add_argument("--azimuth-virtual-channels", type=int, default=None)

    # 目标初始位置、速度、姿态和反射率参数。
    parser.add_argument("--x0-m", type=float, default=0.0)
    parser.add_argument("--y0-m", type=float, default=10.0)
    parser.add_argument("--z0-m", type=float, default=0.0)
    parser.add_argument("--vx-m-s", type=float, default=0.0)
    parser.add_argument("--vy-m-s", type=float, default=-1.0)
    parser.add_argument("--vz-m-s", type=float, default=0.0)
    parser.add_argument("--roll-deg", type=float, default=0.0)
    parser.add_argument("--pitch-deg", type=float, default=0.0)
    parser.add_argument("--yaw-deg", type=float, default=0.0)
    parser.add_argument("--reflectivity", type=float, default=1.0)
    return parser
