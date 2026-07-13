from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

from clap_spotify import audio_mixer


def test_duck_and_restore_without_pycaw_returns_none():
    # pycaw no está instalado en este entorno (Linux) -> debe hacer fallback silencioso.
    assert audio_mixer.duck_spotify_volume(15.0) is None
    audio_mixer.restore_spotify_volume({1234: 1.0})  # no debe lanzar


def _install_fake_pycaw(monkeypatch, sessions):
    comtypes_module = types.ModuleType("comtypes")
    comtypes_module.CoInitialize = MagicMock()
    monkeypatch.setitem(sys.modules, "comtypes", comtypes_module)

    pycaw_pkg = types.ModuleType("pycaw")
    pycaw_module = types.ModuleType("pycaw.pycaw")
    audio_utilities = MagicMock()
    audio_utilities.GetAllSessions.return_value = sessions
    pycaw_module.AudioUtilities = audio_utilities
    monkeypatch.setitem(sys.modules, "pycaw", pycaw_pkg)
    monkeypatch.setitem(sys.modules, "pycaw.pycaw", pycaw_module)


def _make_fake_session(pid, name, current_volume):
    process = MagicMock()
    process.pid = pid
    process.name.return_value = name
    volume = MagicMock()
    volume.GetMasterVolume.return_value = current_volume
    session = MagicMock()
    session.Process = process
    session.SimpleAudioVolume = volume
    return session, volume


def test_duck_lowers_spotify_session_volume(monkeypatch):
    spotify_session, spotify_volume = _make_fake_session(1234, "Spotify.exe", 0.8)
    other_session, other_volume = _make_fake_session(999, "chrome.exe", 0.5)
    _install_fake_pycaw(monkeypatch, [spotify_session, other_session])

    previous = audio_mixer.duck_spotify_volume(15.0)

    assert previous == {1234: 0.8}
    spotify_volume.SetMasterVolume.assert_called_once_with(0.15, None)
    other_volume.SetMasterVolume.assert_not_called()


def test_restore_sets_back_previous_volume(monkeypatch):
    session, volume = _make_fake_session(1234, "spotify.exe", 0.15)
    _install_fake_pycaw(monkeypatch, [session])

    audio_mixer.restore_spotify_volume({1234: 0.8})

    volume.SetMasterVolume.assert_called_once_with(0.8, None)


def test_duck_returns_none_when_no_spotify_session(monkeypatch):
    session, _ = _make_fake_session(999, "chrome.exe", 0.5)
    _install_fake_pycaw(monkeypatch, [session])

    assert audio_mixer.duck_spotify_volume(15.0) is None


def test_restore_with_none_does_not_touch_pycaw(monkeypatch):
    calls = MagicMock()
    monkeypatch.setitem(sys.modules, "comtypes", calls)
    audio_mixer.restore_spotify_volume(None)
    calls.CoInitialize.assert_not_called()
