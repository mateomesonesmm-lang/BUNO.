from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

from clap_spotify import audio_mixer


def test_duck_and_restore_without_pycaw_do_not_raise():
    # pycaw no está instalado en este entorno (Linux) -> debe hacer fallback silencioso.
    assert audio_mixer.duck_spotify_volume(15.0) is False
    audio_mixer.restore_spotify_volume()  # no debe lanzar


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


def test_duck_lowers_all_spotify_sessions(monkeypatch):
    session_a, volume_a = _make_fake_session(1234, "Spotify.exe", 0.8)
    session_b, volume_b = _make_fake_session(5678, "Spotify.exe", 0.8)
    other_session, other_volume = _make_fake_session(999, "chrome.exe", 0.5)
    _install_fake_pycaw(monkeypatch, [session_a, session_b, other_session])

    found = audio_mixer.duck_spotify_volume(15.0)

    assert found is True
    volume_a.SetMasterVolume.assert_called_once_with(0.15, None)
    volume_b.SetMasterVolume.assert_called_once_with(0.15, None)
    other_volume.SetMasterVolume.assert_not_called()


def test_restore_sets_all_spotify_sessions_to_target(monkeypatch):
    session_a, volume_a = _make_fake_session(1234, "spotify.exe", 0.15)
    session_b, volume_b = _make_fake_session(5678, "spotify.exe", 0.15)
    _install_fake_pycaw(monkeypatch, [session_a, session_b])

    audio_mixer.restore_spotify_volume(100.0)

    volume_a.SetMasterVolume.assert_called_once_with(1.0, None)
    volume_b.SetMasterVolume.assert_called_once_with(1.0, None)


def test_duck_returns_false_when_no_spotify_session(monkeypatch):
    session, _ = _make_fake_session(999, "chrome.exe", 0.5)
    _install_fake_pycaw(monkeypatch, [session])

    assert audio_mixer.duck_spotify_volume(15.0) is False


def test_restore_without_pycaw_does_not_raise(monkeypatch):
    monkeypatch.delitem(sys.modules, "comtypes", raising=False)
    monkeypatch.delitem(sys.modules, "pycaw", raising=False)
    monkeypatch.delitem(sys.modules, "pycaw.pycaw", raising=False)
    audio_mixer.restore_spotify_volume()
