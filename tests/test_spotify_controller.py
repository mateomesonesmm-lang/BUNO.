from __future__ import annotations

from unittest.mock import MagicMock, patch

from clap_spotify.config import DEFAULT_TRACK_URI, SpotifyConfig
from clap_spotify.spotify_controller import SpotifyController


def test_resolve_uri_prefers_explicit_track_uri():
    controller = SpotifyController(SpotifyConfig(track_uri="spotify:track:explicit123"))
    assert controller.resolve_uri() == "spotify:track:explicit123"


def test_resolve_uri_falls_back_to_default_without_credentials():
    controller = SpotifyController(SpotifyConfig())
    assert controller.resolve_uri() == DEFAULT_TRACK_URI


def test_resolve_uri_uses_web_api_search_when_credentials_present():
    config = SpotifyConfig(client_id="id", client_secret="secret")
    controller = SpotifyController(config)

    fake_client = MagicMock()
    fake_client.search.return_value = {"tracks": {"items": [{"uri": "spotify:track:searched"}]}}

    with patch.object(SpotifyController, "_search_uri_via_web_api", return_value="spotify:track:searched"):
        assert controller.resolve_uri() == "spotify:track:searched"


def test_resolve_uri_falls_back_to_default_when_search_fails():
    config = SpotifyConfig(client_id="id", client_secret="secret")
    controller = SpotifyController(config)

    with patch.object(SpotifyController, "_search_uri_via_web_api", return_value=None):
        assert controller.resolve_uri() == DEFAULT_TRACK_URI


def test_trigger_dry_run_does_not_execute_real_processes():
    config = SpotifyConfig(track_uri="spotify:track:explicit123", dry_run=True)
    controller = SpotifyController(config)

    with patch("clap_spotify.spotify_controller.open_or_focus_spotify") as mock_open, patch(
        "clap_spotify.spotify_controller.focus_spotify_window"
    ) as mock_focus, patch("clap_spotify.spotify_controller.launch_uri") as mock_launch, patch(
        "subprocess.run"
    ) as mock_subprocess, patch(
        "subprocess.Popen"
    ) as mock_popen:
        controller.trigger()

    mock_open.assert_called_once_with(dry_run=True)
    mock_focus.assert_called_once_with(dry_run=True)
    mock_launch.assert_called_once_with("spotify:track:explicit123", dry_run=True)
    mock_subprocess.assert_not_called()
    mock_popen.assert_not_called()


def test_trigger_calls_actions_in_order():
    config = SpotifyConfig(track_uri="spotify:track:explicit123", dry_run=True)
    controller = SpotifyController(config)

    manager = MagicMock()
    with patch("clap_spotify.spotify_controller.open_or_focus_spotify", manager.open), patch(
        "clap_spotify.spotify_controller.focus_spotify_window", manager.focus
    ), patch("clap_spotify.spotify_controller.launch_uri", manager.launch):
        controller.trigger()

    assert [c[0] for c in manager.mock_calls] == ["open", "focus", "launch"]
