from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from .fft_pipeline import run_fft_pipeline
from .mesh_loader import load_mesh
from .multiprocess_engine import default_worker_count
from .radar_model import RadarConfig, TargetMotion
from .signal_synth import simulate_rdc


def main() -> None:
    arguments = _build_parser().parse_args()

    radar = RadarConfig(
        carrier_hz=arguments.carrier_hz,
        bandwidth_hz=arguments.bandwidth_hz,
        chirp_duration_s=arguments.chirp_duration_s,
        num_adc_samples=arguments.num_adc_samples,
        num_chirps=arguments.num_chirps,
        num_tx=arguments.num_tx,
        num_rx=arguments.num_rx,
    )
    target = TargetMotion(
        initial_position_m=(arguments.x0_m, arguments.y0_m, arguments.z0_m),
        velocity_m_s=(arguments.vx_m_s, arguments.vy_m_s, arguments.vz_m_s),
        euler_deg=(arguments.roll_deg, arguments.pitch_deg, arguments.yaw_deg),
        reflectivity=arguments.reflectivity,
    )

    mesh = load_mesh(arguments.mesh)
    workers = arguments.workers if arguments.workers is not None else default_worker_count()
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


def _build_parser() -> argparse.ArgumentParser:
    project_root = Path(__file__).resolve().parents[2]
    default_mesh = project_root / "examples" / "meshes" / "box.obj"
    default_output = project_root / "examples" / "output" / "box_run.npz"

    parser = argparse.ArgumentParser(description="Mesh-based MIMO FMCW radar simulator.")
    parser.add_argument("--mesh", type=Path, default=default_mesh, help="Path to OBJ or STL mesh.")
    parser.add_argument("--output", type=Path, default=default_output, help="Path to NPZ output file.")
    parser.add_argument("--workers", type=int, default=None, help="Multiprocess worker count. Default: cpu_count() // 2.")
    parser.add_argument("--max-faces", type=int, default=None, help="Optional face-budget downsampling before simulation.")

    parser.add_argument("--carrier-hz", type=float, default=77e9)
    parser.add_argument("--bandwidth-hz", type=float, default=150e6)
    parser.add_argument("--chirp-duration-s", type=float, default=40e-6)
    parser.add_argument("--num-adc-samples", type=int, default=256)
    parser.add_argument("--num-chirps", type=int, default=64)
    parser.add_argument("--num-tx", type=int, default=2)
    parser.add_argument("--num-rx", type=int, default=4)

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
