"""Load named radar profiles from TOML files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib

from .radar_model import RadarConfig


@dataclass(frozen=True)
class RadarProfile:
    """Hardware metadata and simulation defaults loaded from one profile."""

    name: str
    frequency_min_hz: float
    frequency_max_hz: float
    max_bandwidth_hz: float
    max_adc_sample_rate_hz: float
    num_chips: int
    num_tx: int
    num_rx: int
    raw_virtual_channels: int
    azimuth_virtual_channels: int
    documentation_url: str
    carrier_hz: float
    bandwidth_hz: float
    chirp_duration_s: float
    num_adc_samples: int
    num_chirps: int

    def to_radar_config(self, **overrides: float | int | None) -> RadarConfig:
        """Build a simulator config, applying non-None CLI overrides."""

        values: dict[str, float | int | None] = {
            "carrier_hz": self.carrier_hz,
            "bandwidth_hz": self.bandwidth_hz,
            "chirp_duration_s": self.chirp_duration_s,
            "num_adc_samples": self.num_adc_samples,
            "num_chirps": self.num_chirps,
            "num_tx": self.num_tx,
            "num_rx": self.num_rx,
            "azimuth_virtual_channels": self.azimuth_virtual_channels,
        }
        values.update({key: value for key, value in overrides.items() if value is not None})
        return RadarConfig(**values)


def load_radar_profile(profile: str | Path, profiles_dir: Path) -> RadarProfile:
    """Load a profile by short name or explicit TOML path."""

    profile_path = _resolve_profile_path(profile, profiles_dir)
    with profile_path.open("rb") as profile_file:
        data = tomllib.load(profile_file)

    try:
        device = data["device"]
        simulation = data["simulation"]
        loaded = RadarProfile(
            name=str(device["name"]),
            frequency_min_hz=float(device["frequency_min_hz"]),
            frequency_max_hz=float(device["frequency_max_hz"]),
            max_bandwidth_hz=float(device["max_bandwidth_hz"]),
            max_adc_sample_rate_hz=float(device["max_adc_sample_rate_hz"]),
            num_chips=int(device["num_chips"]),
            num_tx=int(device["num_tx"]),
            num_rx=int(device["num_rx"]),
            raw_virtual_channels=int(device["raw_virtual_channels"]),
            azimuth_virtual_channels=int(device["azimuth_virtual_channels"]),
            documentation_url=str(device["documentation_url"]),
            carrier_hz=float(simulation["carrier_hz"]),
            bandwidth_hz=float(simulation["bandwidth_hz"]),
            chirp_duration_s=float(simulation["chirp_duration_s"]),
            num_adc_samples=int(simulation["num_adc_samples"]),
            num_chirps=int(simulation["num_chirps"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"Invalid radar profile: {profile_path}") from error

    _validate_profile(loaded, profile_path)
    return loaded


def _resolve_profile_path(profile: str | Path, profiles_dir: Path) -> Path:
    requested = Path(profile)
    if requested.parent != Path(".") or requested.suffix:
        path = requested if requested.is_absolute() else Path.cwd() / requested
    else:
        path = profiles_dir / f"{requested.name}.toml"

    if not path.is_file():
        raise FileNotFoundError(f"Radar profile not found: {path}")
    return path


def _validate_profile(profile: RadarProfile, profile_path: Path) -> None:
    if not profile.frequency_min_hz <= profile.carrier_hz <= profile.frequency_max_hz:
        raise ValueError(f"carrier_hz is outside the device frequency range: {profile_path}")
    if profile.bandwidth_hz <= 0.0 or profile.bandwidth_hz > profile.max_bandwidth_hz:
        raise ValueError(f"bandwidth_hz exceeds the device capability: {profile_path}")
    sample_rate_hz = profile.num_adc_samples / profile.chirp_duration_s
    if sample_rate_hz > profile.max_adc_sample_rate_hz:
        raise ValueError(f"simulation ADC sample rate exceeds the device capability: {profile_path}")
    if profile.raw_virtual_channels != profile.num_tx * profile.num_rx:
        raise ValueError(f"raw_virtual_channels must equal num_tx * num_rx: {profile_path}")
    if not 1 <= profile.azimuth_virtual_channels <= profile.raw_virtual_channels:
        raise ValueError(f"invalid azimuth_virtual_channels: {profile_path}")
