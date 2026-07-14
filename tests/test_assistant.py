from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from clap_spotify.assistant import HomeAssistant
from clap_spotify.config import AssistantConfig


def _make_assistant(tmp_path, dry_run=False, **overrides):
    spotify = MagicMock()
    config = AssistantConfig(
        tasks_file=str(tmp_path / "tasks.txt"),
        state_file=str(tmp_path / "state.json"),
        **overrides,
    )
    return spotify, HomeAssistant(spotify, config, dry_run=dry_run)


def test_first_clap_of_day_greets_in_order(tmp_path):
    spotify, assistant = _make_assistant(tmp_path)

    manager = MagicMock()
    manager.duck.return_value = {1: 0.5}
    with patch("clap_spotify.assistant.duck_spotify_volume", manager.duck), patch(
        "clap_spotify.assistant.restore_spotify_volume", manager.restore
    ), patch.object(HomeAssistant, "_speak", manager.speak):
        assistant.handle_clap()

    spotify.trigger.assert_called_once()
    assert [c[0] for c in manager.mock_calls] == ["duck", "speak", "restore"]
    manager.restore.assert_called_once_with({1: 0.5})


def test_second_clap_same_day_does_not_repeat_greeting(tmp_path):
    spotify, assistant = _make_assistant(tmp_path)

    with patch("clap_spotify.assistant.duck_spotify_volume", return_value=None), patch(
        "clap_spotify.assistant.restore_spotify_volume"
    ), patch.object(HomeAssistant, "_speak") as speak:
        assistant.handle_clap()
        assistant.handle_clap()

    assert spotify.trigger.call_count == 2
    speak.assert_called_once()


def test_greet_every_time_when_once_per_day_disabled(tmp_path):
    spotify, assistant = _make_assistant(tmp_path, greet_once_per_day=False)

    with patch("clap_spotify.assistant.duck_spotify_volume", return_value=None), patch(
        "clap_spotify.assistant.restore_spotify_volume"
    ), patch.object(HomeAssistant, "_speak") as speak:
        assistant.handle_clap()
        assistant.handle_clap()

    assert spotify.trigger.call_count == 2
    assert speak.call_count == 2


def test_force_greeting_ignores_state(tmp_path):
    spotify, assistant = _make_assistant(tmp_path)

    with patch("clap_spotify.assistant.duck_spotify_volume", return_value=None), patch(
        "clap_spotify.assistant.restore_spotify_volume"
    ), patch.object(HomeAssistant, "_speak") as speak:
        assistant.handle_clap()
        assistant.handle_clap(force_greeting=True)

    assert speak.call_count == 2


def test_dry_run_never_calls_duck_or_speak(tmp_path):
    spotify, assistant = _make_assistant(tmp_path, dry_run=True)

    with patch("clap_spotify.assistant.duck_spotify_volume") as duck, patch(
        "clap_spotify.assistant.restore_spotify_volume"
    ) as restore, patch.object(HomeAssistant, "_speak") as speak:
        assistant.handle_clap()

    spotify.trigger.assert_called_once()
    duck.assert_not_called()
    restore.assert_not_called()
    speak.assert_not_called()


def test_corrupt_state_file_is_treated_as_not_greeted(tmp_path):
    spotify, assistant = _make_assistant(tmp_path)
    (tmp_path / "state.json").write_text("{not valid json", encoding="utf-8")

    with patch("clap_spotify.assistant.duck_spotify_volume", return_value=None), patch(
        "clap_spotify.assistant.restore_spotify_volume"
    ), patch.object(HomeAssistant, "_speak") as speak:
        assistant.handle_clap()

    speak.assert_called_once()


def test_weather_sentence_success(tmp_path):
    _, assistant = _make_assistant(tmp_path, city="Buenos Aires,AR", weather_api_key="key123")

    response = MagicMock(status_code=200)
    response.json.return_value = {"main": {"temp": 10.0}, "weather": [{"description": "cielo claro"}]}
    with patch("clap_spotify.assistant.requests.get", return_value=response):
        sentence = assistant._get_weather_sentence()

    assert "10" in sentence
    assert "cielo claro" in sentence
    assert "abríguese" in sentence  # 10 < default cold threshold (12.0)


def test_weather_sentence_missing_config_returns_none(tmp_path):
    _, assistant = _make_assistant(tmp_path)
    assert assistant._get_weather_sentence() is None


def test_weather_sentence_401_returns_none(tmp_path):
    _, assistant = _make_assistant(tmp_path, city="Cordoba,AR", weather_api_key="bad-key")

    response = MagicMock(status_code=401)
    with patch("clap_spotify.assistant.requests.get", return_value=response):
        assert assistant._get_weather_sentence() is None


def test_weather_sentence_timeout_returns_none(tmp_path):
    _, assistant = _make_assistant(tmp_path, city="Rosario,AR", weather_api_key="key123")

    with patch("clap_spotify.assistant.requests.get", side_effect=TimeoutError):
        assert assistant._get_weather_sentence() is None


def test_tasks_sentence_missing_file_returns_none(tmp_path):
    _, assistant = _make_assistant(tmp_path)
    assert assistant._get_tasks_sentence() is None


def test_tasks_sentence_reads_and_truncates(tmp_path):
    _, assistant = _make_assistant(tmp_path, max_tasks_to_read=2)
    (tmp_path / "tasks.txt").write_text("tarea uno\n\ntarea dos\ntarea tres\n", encoding="utf-8")

    sentence = assistant._get_tasks_sentence()

    assert "tarea uno" in sentence
    assert "tarea dos" in sentence
    assert "tarea tres" not in sentence


def test_mark_and_check_greeted_today_roundtrip(tmp_path):
    _, assistant = _make_assistant(tmp_path)
    assert assistant._already_greeted_today() is False

    assistant._mark_greeted_today()

    assert assistant._already_greeted_today() is True
    saved = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert "last_greeted_date" in saved
