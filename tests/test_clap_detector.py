from __future__ import annotations

import numpy as np
import pytest

from clap_spotify.audio_listener import ClapDetector
from clap_spotify.config import ClapDetectorConfig

SAMPLE_RATE = 44100
BLOCK_SIZE = 1024


def _make_detector(on_clap, **overrides) -> ClapDetector:
    config = ClapDetectorConfig(sample_rate=SAMPLE_RATE, block_size=BLOCK_SIZE, **overrides)
    return ClapDetector(config, on_clap=on_clap)


def _silence(n=BLOCK_SIZE, amplitude=0.002, rng=None) -> np.ndarray:
    rng = rng or np.random.default_rng(0)
    return (rng.standard_normal(n) * amplitude).astype(np.float32)


def _clap_burst(n=BLOCK_SIZE, amplitude=0.5, rng=None) -> np.ndarray:
    # Ruido blanco de banda ancha (rico en agudos) y amplitud alta: emula un aplauso.
    rng = rng or np.random.default_rng(1)
    return (rng.standard_normal(n) * amplitude).astype(np.float32)


def _low_freq_thump(n=BLOCK_SIZE, amplitude=0.5, freq=80.0) -> np.ndarray:
    t = np.arange(n) / SAMPLE_RATE
    return (amplitude * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def _feed(detector: ClapDetector, blocks: list[np.ndarray]) -> list[bool]:
    return [detector.process_block(block) for block in blocks]


def _seed_calibrated(detector: ClapDetector, floor: float = 0.01) -> None:
    detector._noise_floor = floor
    detector._recent_rms.extend([floor] * detector._config.recent_rms_window)


class _Counter:
    def __init__(self):
        self.calls = 0

    def __call__(self):
        self.calls += 1


def test_clap_burst_triggers_exactly_one_event():
    counter = _Counter()
    detector = _make_detector(counter, decay_check_blocks=2, decay_ratio=0.6)
    _seed_calibrated(detector)

    rng = np.random.default_rng(42)
    blocks = [_silence(rng=rng) for _ in range(3)]
    blocks.append(_clap_burst(rng=rng))
    blocks.append(_silence(rng=rng))
    blocks.append(_silence(rng=rng))

    results = _feed(detector, blocks)

    assert results.count(True) == 1
    detector._executor.shutdown(wait=True)
    assert counter.calls == 1


def test_low_freq_thump_does_not_trigger():
    counter = _Counter()
    detector = _make_detector(counter)
    _seed_calibrated(detector)

    blocks = [_silence(), _low_freq_thump(), _silence()]
    results = _feed(detector, blocks)

    assert True not in results
    detector._executor.shutdown(wait=True)
    assert counter.calls == 0


def test_sustained_loud_noise_does_not_trigger():
    counter = _Counter()
    detector = _make_detector(counter, decay_check_blocks=2, decay_ratio=0.6)
    _seed_calibrated(detector)

    rng = np.random.default_rng(7)
    loud = _clap_burst(rng=rng)
    blocks = [_silence(rng=rng), loud, loud, loud, loud]

    results = _feed(detector, blocks)

    assert True not in results
    detector._executor.shutdown(wait=True)
    assert counter.calls == 0


def test_two_claps_within_cooldown_count_once():
    counter = _Counter()
    detector = _make_detector(
        counter, decay_check_blocks=2, decay_ratio=0.6, cooldown_seconds=5.0, post_trigger_mute_seconds=5.0
    )
    _seed_calibrated(detector)

    rng = np.random.default_rng(99)
    blocks = [_silence(rng=rng)]
    blocks.append(_clap_burst(rng=rng))
    blocks.append(_silence(rng=rng))
    blocks.append(_clap_burst(rng=rng))
    blocks.append(_silence(rng=rng))

    results = _feed(detector, blocks)

    assert results.count(True) == 1
    detector._executor.shutdown(wait=True)
    assert counter.calls == 1


def test_calibrate_sets_reasonable_noise_floor(monkeypatch):
    counter = _Counter()
    detector = _make_detector(counter, calibration_seconds=0.1, min_amplitude_floor=0.001)

    rng = np.random.default_rng(3)
    fed_blocks = []

    class FakeStream:
        def read(self, block_size):
            block = _silence(block_size, amplitude=0.01, rng=rng)
            fed_blocks.append(block)
            return block.reshape(-1, 1), False

    floor = detector.calibrate(FakeStream())

    assert floor > 0
    assert floor < 0.05
    detector._executor.shutdown(wait=True)
