from __future__ import annotations

import logging
import os
import platform
import shutil
import subprocess

logger = logging.getLogger(__name__)


def current_platform() -> str:
    return platform.system()


def open_or_focus_spotify(dry_run: bool = False, system: str | None = None) -> None:
    system = system or current_platform()

    if dry_run:
        logger.info("[dry-run] abriría/enfocaría Spotify en %s", system)
        return

    if system == "Windows":
        os.startfile("spotify:")  # type: ignore[attr-defined]
    elif system == "Darwin":
        subprocess.run(["open", "-a", "Spotify"], check=False)
    else:
        spotify_bin = shutil.which("spotify")
        if spotify_bin:
            subprocess.Popen([spotify_bin])
        else:
            subprocess.run(["xdg-open", "spotify:"], check=False)


def focus_spotify_window(dry_run: bool = False, system: str | None = None) -> None:
    system = system or current_platform()

    if dry_run:
        logger.info("[dry-run] enfocaría la ventana de Spotify en %s", system)
        return

    try:
        if system == "Windows":
            try:
                import pygetwindow as gw

                windows = gw.getWindowsWithTitle("Spotify")
                if windows:
                    windows[0].activate()
            except ImportError:
                logger.debug("pygetwindow no instalado; se omite el enfoque de ventana")
        elif system == "Darwin":
            subprocess.run(
                ["osascript", "-e", 'tell application "Spotify" to activate'],
                check=False,
            )
        else:
            if shutil.which("wmctrl"):
                subprocess.run(["wmctrl", "-a", "Spotify"], check=False)
    except Exception:
        logger.debug("No se pudo enfocar la ventana de Spotify", exc_info=True)


def launch_uri(uri: str, dry_run: bool = False, system: str | None = None) -> None:
    system = system or current_platform()

    if dry_run:
        logger.info("[dry-run] lanzaría el URI: %s", uri)
        return

    if system == "Windows":
        os.startfile(uri)  # type: ignore[attr-defined]
    elif system == "Darwin":
        subprocess.run(["open", uri], check=False)
    else:
        spotify_bin = shutil.which("spotify")
        if spotify_bin:
            subprocess.Popen([spotify_bin, uri])
        else:
            subprocess.run(["xdg-open", uri], check=False)
