from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_SPOTIFY_PROCESS_NAME = "spotify.exe"


def duck_spotify_volume(target_percent: float) -> dict[int, float] | None:
    """Baja el volumen de la(s) sesión(es) de audio de Spotify en Windows.
    Retorna un mapa {pid: volumen_previo} para poder restaurarlo, o None si
    no se pudo (no es Windows, falta pycaw, o no se encontró la sesión)."""
    try:
        from comtypes import CoInitialize
        from pycaw.pycaw import AudioUtilities
    except ImportError:
        logger.debug("pycaw/comtypes no instalados; no se puede bajar el volumen de Spotify")
        return None

    try:
        try:
            CoInitialize()
        except OSError:
            pass  # ya inicializado en este hilo

        previous: dict[int, float] = {}
        for session in AudioUtilities.GetAllSessions():
            process = session.Process
            if not process or process.name().lower() != _SPOTIFY_PROCESS_NAME:
                continue
            volume = session.SimpleAudioVolume
            previous[process.pid] = volume.GetMasterVolume()
            volume.SetMasterVolume(target_percent / 100, None)

        return previous or None
    except Exception:
        logger.debug("No se pudo bajar el volumen de Spotify", exc_info=True)
        return None


def restore_spotify_volume(previous: dict[int, float] | None) -> None:
    if not previous:
        return

    try:
        from comtypes import CoInitialize
        from pycaw.pycaw import AudioUtilities
    except ImportError:
        return

    try:
        try:
            CoInitialize()
        except OSError:
            pass

        for session in AudioUtilities.GetAllSessions():
            process = session.Process
            if not process or process.pid not in previous:
                continue
            session.SimpleAudioVolume.SetMasterVolume(previous[process.pid], None)
    except Exception:
        logger.debug("No se pudo restaurar el volumen de Spotify", exc_info=True)
