from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_SPOTIFY_PROCESS_NAME = "spotify.exe"


def _spotify_sessions():
    from comtypes import CoInitialize
    from pycaw.pycaw import AudioUtilities

    try:
        CoInitialize()
    except OSError:
        pass  # ya inicializado en este hilo

    for session in AudioUtilities.GetAllSessions():
        process = session.Process
        if process and process.name().lower() == _SPOTIFY_PROCESS_NAME:
            yield session


def duck_spotify_volume(target_percent: float) -> bool:
    """Baja el volumen de todas las sesiones de audio de Spotify en Windows.
    Retorna True si bajó al menos una, False si no se pudo (no es Windows,
    falta pycaw, o no se encontró ninguna sesión de Spotify)."""
    try:
        found = False
        for session in _spotify_sessions():
            session.SimpleAudioVolume.SetMasterVolume(target_percent / 100, None)
            found = True
        return found
    except ImportError:
        logger.debug("pycaw/comtypes no instalados; no se puede bajar el volumen de Spotify")
        return False
    except Exception:
        logger.debug("No se pudo bajar el volumen de Spotify", exc_info=True)
        return False


def restore_spotify_volume(target_percent: float = 100.0) -> None:
    """Vuelve a subir todas las sesiones de audio de Spotify a un volumen fijo
    (100% por defecto), en vez de intentar recordar el valor previo exacto:
    Spotify puede tener varios procesos de audio y el que se ducken no
    siempre es el mismo que sigue vivo un rato después, así que "recordar y
    restaurar" es poco confiable. Simplemente la dejamos al máximo."""
    try:
        for session in _spotify_sessions():
            session.SimpleAudioVolume.SetMasterVolume(target_percent / 100, None)
    except ImportError:
        pass
    except Exception:
        logger.debug("No se pudo restaurar el volumen de Spotify", exc_info=True)
