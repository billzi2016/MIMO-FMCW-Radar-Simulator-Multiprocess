from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def main() -> None:
    arguments = build_parser().parse_args()
    data = np.load(arguments.input, allow_pickle=True)

    output_dir = arguments.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    range_axis_m = data["range_axis_m"]
    doppler_axis_m_s = data["doppler_axis_m_s"]
    angle_axis_deg = data["angle_axis_deg"]

    range_doppler_map = data["range_doppler_map"]
    range_angle_map = data["range_angle_map"]
    range_doppler_angle_cube = data["range_doppler_angle_cube"]
    range_fft = data["range_fft"]

    doppler_angle_map = np.sum(np.abs(range_doppler_angle_cube), axis=0)
    range_chirp_map = np.sum(np.abs(range_fft), axis=2)
    chirp_axis = np.arange(range_fft.shape[1], dtype=np.int64)

    save_heatmap(
        matrix=range_doppler_map,
        x_axis=doppler_axis_m_s,
        y_axis=range_axis_m,
        title="Range-Doppler Heatmap",
        x_label="Speed (m/s)",
        y_label="Range (m)",
        output_path=output_dir / "range_doppler_heatmap.png",
    )
    save_heatmap(
        matrix=range_angle_map,
        x_axis=angle_axis_deg,
        y_axis=range_axis_m,
        title="Range-Angle Heatmap",
        x_label="Angle (deg)",
        y_label="Range (m)",
        output_path=output_dir / "range_angle_heatmap.png",
    )
    save_heatmap(
        matrix=doppler_angle_map,
        x_axis=angle_axis_deg,
        y_axis=doppler_axis_m_s,
        title="Doppler-Angle Heatmap",
        x_label="Angle (deg)",
        y_label="Speed (m/s)",
        output_path=output_dir / "doppler_angle_heatmap.png",
    )
    save_heatmap(
        matrix=range_chirp_map,
        x_axis=chirp_axis,
        y_axis=range_axis_m,
        title="Range-Chirp Heatmap",
        x_label="Chirp Index",
        y_label="Range (m)",
        output_path=output_dir / "range_chirp_heatmap.png",
    )
    save_summary(
        range_doppler_map=range_doppler_map,
        range_angle_map=range_angle_map,
        doppler_angle_map=doppler_angle_map,
        range_chirp_map=range_chirp_map,
        range_axis_m=range_axis_m,
        doppler_axis_m_s=doppler_axis_m_s,
        angle_axis_deg=angle_axis_deg,
        chirp_axis=chirp_axis,
        output_path=output_dir / "summary_heatmaps.png",
    )

    print(f"Saved plots to: {output_dir}")


def build_parser() -> argparse.ArgumentParser:
    script_dir = Path(__file__).resolve().parent
    default_input = script_dir.parent / "output" / "thanh_run.npz"
    default_output_dir = script_dir / "output"

    parser = argparse.ArgumentParser(description="Plot heatmaps from thanh_run.npz.")
    parser.add_argument("--input", type=Path, default=default_input, help="Path to the NPZ result file.")
    parser.add_argument("--output-dir", type=Path, default=default_output_dir, help="Directory for generated plot images.")
    return parser


def save_heatmap(
    matrix: np.ndarray,
    x_axis: np.ndarray,
    y_axis: np.ndarray,
    title: str,
    x_label: str,
    y_label: str,
    output_path: Path,
) -> None:
    figure, axis = plt.subplots(figsize=(8, 6))
    image = axis.imshow(
        to_db(matrix),
        origin="lower",
        aspect="auto",
        extent=build_extent(x_axis, y_axis),
        cmap="viridis",
    )
    axis.set_title(title)
    axis.set_xlabel(x_label)
    axis.set_ylabel(y_label)
    colorbar = figure.colorbar(image, ax=axis)
    colorbar.set_label("Magnitude (dB)")
    figure.tight_layout()
    figure.savefig(output_path, dpi=200)
    plt.close(figure)


def save_summary(
    range_doppler_map: np.ndarray,
    range_angle_map: np.ndarray,
    doppler_angle_map: np.ndarray,
    range_chirp_map: np.ndarray,
    range_axis_m: np.ndarray,
    doppler_axis_m_s: np.ndarray,
    angle_axis_deg: np.ndarray,
    chirp_axis: np.ndarray,
    output_path: Path,
) -> None:
    figure, axes = plt.subplots(2, 2, figsize=(14, 10))

    plot_on_axis(
        axis=axes[0, 0],
        matrix=range_doppler_map,
        x_axis=doppler_axis_m_s,
        y_axis=range_axis_m,
        title="Range-Doppler",
        x_label="Speed (m/s)",
        y_label="Range (m)",
    )
    plot_on_axis(
        axis=axes[0, 1],
        matrix=range_angle_map,
        x_axis=angle_axis_deg,
        y_axis=range_axis_m,
        title="Range-Angle",
        x_label="Angle (deg)",
        y_label="Range (m)",
    )
    plot_on_axis(
        axis=axes[1, 0],
        matrix=doppler_angle_map,
        x_axis=angle_axis_deg,
        y_axis=doppler_axis_m_s,
        title="Doppler-Angle",
        x_label="Angle (deg)",
        y_label="Speed (m/s)",
    )
    plot_on_axis(
        axis=axes[1, 1],
        matrix=range_chirp_map,
        x_axis=chirp_axis,
        y_axis=range_axis_m,
        title="Range-Chirp",
        x_label="Chirp Index",
        y_label="Range (m)",
    )

    figure.tight_layout()
    figure.savefig(output_path, dpi=200)
    plt.close(figure)


def plot_on_axis(
    axis: plt.Axes,
    matrix: np.ndarray,
    x_axis: np.ndarray,
    y_axis: np.ndarray,
    title: str,
    x_label: str,
    y_label: str,
) -> None:
    image = axis.imshow(
        to_db(matrix),
        origin="lower",
        aspect="auto",
        extent=build_extent(x_axis, y_axis),
        cmap="viridis",
    )
    axis.set_title(title)
    axis.set_xlabel(x_label)
    axis.set_ylabel(y_label)
    colorbar = axis.figure.colorbar(image, ax=axis)
    colorbar.set_label("Magnitude (dB)")


def to_db(matrix: np.ndarray) -> np.ndarray:
    magnitude = np.abs(matrix)
    return 20.0 * np.log10(np.maximum(magnitude, 1e-12))


def build_extent(x_axis: np.ndarray, y_axis: np.ndarray) -> list[float]:
    x_min, x_max = axis_edges(x_axis)
    y_min, y_max = axis_edges(y_axis)
    return [x_min, x_max, y_min, y_max]


def axis_edges(axis_values: np.ndarray) -> tuple[float, float]:
    values = np.asarray(axis_values, dtype=np.float64)
    if values.size == 1:
        delta = 0.5
        return float(values[0] - delta), float(values[0] + delta)

    step = values[1] - values[0]
    return float(values[0] - step / 2.0), float(values[-1] + step / 2.0)


if __name__ == "__main__":
    main()
