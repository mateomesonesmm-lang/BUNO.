from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

# URI encontrado por búsqueda pública para "Should I Stay or Should I Go" (The Clash,
# remasterizado, álbum Combat Rock). No está verificado al 100%: confírmalo o
# reemplázalo vía SPOTIFY_TRACK_URI en tu .env (ver README).
DEFAULT_TRACK_URI = "spotify:track:02DZxszCWyn3UivsWTblnq"
DEFAULT_TRACK_QUERY = "The Clash Should I Stay or Should I Go"


@dataclass
class ClapDetectorConfig:
    sample_rate: int = 44100
    block_size: int = 1024
    calibration_seconds: float = 2.0
    amplitude_multiplier: float = 3.0
    min_amplitude_floor: float = 0.01
    noise_floor_std_k: float = 1.5
    high_freq_cutoff_hz: float = 2000.0
    min_high_freq_ratio: float = 0.35
    attack_ratio: float = 2.5
    recent_rms_window: int = 5
    decay_check_blocks: int = 2
    decay_ratio: float = 0.6
    cooldown_seconds: float = 1.5
    post_trigger_mute_seconds: float = 5.0
    noise_floor_ema_alpha: float = 0.05
    device: int | str | None = None

    def __post_init__(self) -> None:
        if self.high_freq_cutoff_hz >= self.sample_rate / 2:
            raise ValueError(
                "high_freq_cutoff_hz debe ser menor que sample_rate/2 "
                f"(recibido {self.high_freq_cutoff_hz} >= {self.sample_rate / 2})"
            )


@dataclass
class SpotifyConfig:
    track_query: str = DEFAULT_TRACK_QUERY
    track_uri: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    dry_run: bool = False
    cold_start_wait_seconds: float = 3.0
    focus_wait_seconds: float = 1.0


@dataclass
class AppConfig:
    clap: ClapDetectorConfig = field(default_factory=ClapDetectorConfig)
    spotify: SpotifyConfig = field(default_factory=SpotifyConfig)


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value else default


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value else default


def load_config() -> AppConfig:
    load_dotenv()

    clap = ClapDetectorConfig(
        amplitude_multiplier=_float_env("CLAP_AMPLITUDE_MULTIPLIER", 3.0),
        min_amplitude_floor=_float_env("CLAP_MIN_AMPLITUDE_FLOOR", 0.01),
        noise_floor_std_k=_float_env("CLAP_NOISE_FLOOR_STD_K", 1.5),
        high_freq_cutoff_hz=_float_env("CLAP_HIGH_FREQ_CUTOFF_HZ", 2000.0),
        min_high_freq_ratio=_float_env("CLAP_MIN_HIGH_FREQ_RATIO", 0.35),
        attack_ratio=_float_env("CLAP_ATTACK_RATIO", 2.5),
        cooldown_seconds=_float_env("CLAP_COOLDOWN_SECONDS", 1.5),
        post_trigger_mute_seconds=_float_env("CLAP_POST_TRIGGER_MUTE_SECONDS", 5.0),
        calibration_seconds=_float_env("CLAP_CALIBRATION_SECONDS", 2.0),
    )

    spotify = SpotifyConfig(
        track_query=os.getenv("SPOTIFY_TRACK_QUERY") or DEFAULT_TRACK_QUERY,
        track_uri=os.getenv("SPOTIFY_TRACK_URI") or None,
        client_id=os.getenv("SPOTIFY_CLIENT_ID") or None,
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET") or None,
    )

    return AppConfig(clap=clap, spotify=spotify)
