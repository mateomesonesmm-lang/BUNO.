from __future__ import annotations

import logging
import queue
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable

import numpy as np
import sounddevice as sd

from .config import ClapDetectorConfig

logger = logging.getLogger(__name__)


@dataclass
class _Candidate:
    peak_rms: float
    blocks_waited: int = 0


class ClapDetector:
    """Detecta aplausos en un stream de audio con 4 gates: amplitud, ataque
    súbito, contenido espectral en agudos y decaimiento del transitorio."""

    def __init__(self, config: ClapDetectorConfig, on_clap: Callable[[], None]):
        self._config = config
        self._on_clap = on_clap
        self._executor = ThreadPoolExecutor(max_workers=1)

        self._noise_floor = config.min_amplitude_floor
        self._recent_rms: deque[float] = deque(maxlen=config.recent_rms_window)
        self._candidate: _Candidate | None = None
        self._mute_blocks_left = 0

        block_duration = config.block_size / config.sample_rate
        mute_seconds = max(config.cooldown_seconds, config.post_trigger_mute_seconds)
        self._mute_blocks_after_trigger = max(1, round(mute_seconds / block_duration))

    @staticmethod
    def list_devices() -> str:
        return str(sd.query_devices())

    def _rms(self, block: np.ndarray) -> float:
        centered = block - np.mean(block)
        return float(np.sqrt(np.mean(np.square(centered))))

    def _high_freq_ratio(self, block: np.ndarray) -> float:
        windowed = block * np.hanning(len(block))
        spectrum = np.abs(np.fft.rfft(windowed))
        freqs = np.fft.rfftfreq(len(block), d=1.0 / self._config.sample_rate)
        total = spectrum.sum()
        if total <= 1e-9:
            return 0.0
        mask = freqs >= self._config.high_freq_cutoff_hz
        return float(spectrum[mask].sum() / total)

    def calibrate(self, stream: sd.InputStream) -> float:
        cfg = self._config
        num_blocks = max(1, round(cfg.calibration_seconds * cfg.sample_rate / cfg.block_size))
        samples = []
        for _ in range(num_blocks):
            block, _ = stream.read(cfg.block_size)
            samples.append(self._rms(block[:, 0]))

        mean = float(np.mean(samples))
        std = float(np.std(samples))
        floor = max(mean + cfg.noise_floor_std_k * std, cfg.min_amplitude_floor)

        self._noise_floor = floor
        self._recent_rms.extend(samples[-cfg.recent_rms_window :])
        return floor

    def process_block(self, block: np.ndarray) -> bool:
        """Alimenta un bloque mono de audio al detector. Retorna True el bloque
        en el que se confirma un aplauso (dispara on_clap en un hilo aparte)."""
        cfg = self._config
        rms = self._rms(block)

        if self._mute_blocks_left > 0:
            self._mute_blocks_left -= 1
            return False

        if self._candidate is not None:
            self._candidate.blocks_waited += 1
            decayed = rms < cfg.decay_ratio * self._candidate.peak_rms
            if decayed:
                self._candidate = None
                self._mute_blocks_left = self._mute_blocks_after_trigger
                self._recent_rms.clear()
                logger.info("Aplauso confirmado (RMS pico=%.5f)", rms)
                self._executor.submit(self._on_clap)
                return True
            if self._candidate.blocks_waited >= cfg.decay_check_blocks:
                logger.debug("Candidato descartado: no decayó (ruido sostenido)")
                self._candidate = None
            return False

        baseline = float(np.mean(self._recent_rms)) if self._recent_rms else self._noise_floor
        threshold = max(self._noise_floor * cfg.amplitude_multiplier, cfg.min_amplitude_floor)

        is_loud_enough = rms > threshold
        is_sudden = rms > baseline * cfg.attack_ratio

        if is_loud_enough and is_sudden and self._high_freq_ratio(block) >= cfg.min_high_freq_ratio:
            self._candidate = _Candidate(peak_rms=rms)
            return False

        self._recent_rms.append(rms)
        self._noise_floor = (
            1 - cfg.noise_floor_ema_alpha
        ) * self._noise_floor + cfg.noise_floor_ema_alpha * min(rms, threshold)
        return False

    def run_forever(self) -> None:
        cfg = self._config
        audio_queue: "queue.Queue[np.ndarray]" = queue.Queue()

        def _callback(indata, frames, time_info, status):
            if status:
                logger.warning("Estado del stream de audio: %s", status)
            audio_queue.put(indata[:, 0].copy())

        with sd.InputStream(
            samplerate=cfg.sample_rate,
            channels=1,
            blocksize=cfg.block_size,
            dtype="float32",
            device=cfg.device,
        ) as calibration_stream:
            floor = self.calibrate(calibration_stream)
            logger.info("Piso de ruido calibrado: %.5f", floor)

        logger.info("Escuchando aplausos (Ctrl+C para salir)...")
        with sd.InputStream(
            samplerate=cfg.sample_rate,
            channels=1,
            blocksize=cfg.block_size,
            dtype="float32",
            device=cfg.device,
            callback=_callback,
        ):
            while True:
                block = audio_queue.get()
                self.process_block(block)
