from __future__ import annotations

from unittest.mock import patch

from clap_spotify import os_utils


def test_open_or_focus_spotify_windows_uses_startfile():
    with patch("os.startfile", create=True) as mock_startfile:
        os_utils.open_or_focus_spotify(system="Windows")
    mock_startfile.assert_called_once_with("spotify:")


def test_open_or_focus_spotify_macos_uses_open_dash_a():
    with patch("subprocess.run") as mock_run:
        os_utils.open_or_focus_spotify(system="Darwin")
    mock_run.assert_called_once_with(["open", "-a", "Spotify"], check=False)


def test_open_or_focus_spotify_linux_prefers_installed_binary():
    with patch("shutil.which", return_value="/usr/bin/spotify"), patch(
        "subprocess.Popen"
    ) as mock_popen:
        os_utils.open_or_focus_spotify(system="Linux")
    mock_popen.assert_called_once_with(["/usr/bin/spotify"])


def test_open_or_focus_spotify_linux_falls_back_to_xdg_open():
    with patch("shutil.which", return_value=None), patch("subprocess.run") as mock_run:
        os_utils.open_or_focus_spotify(system="Linux")
    mock_run.assert_called_once_with(["xdg-open", "spotify:"], check=False)


def test_dry_run_never_touches_subprocess_or_os():
    with patch("subprocess.run") as mock_run, patch("subprocess.Popen") as mock_popen, patch(
        "os.startfile", create=True
    ) as mock_startfile:
        os_utils.open_or_focus_spotify(dry_run=True, system="Windows")
        os_utils.focus_spotify_window(dry_run=True, system="Windows")
        os_utils.launch_uri("spotify:track:x", dry_run=True, system="Windows")

    mock_run.assert_not_called()
    mock_popen.assert_not_called()
    mock_startfile.assert_not_called()


def test_launch_uri_windows_uses_startfile():
    with patch("os.startfile", create=True) as mock_startfile:
        os_utils.launch_uri("spotify:track:abc", system="Windows")
    mock_startfile.assert_called_once_with("spotify:track:abc")
