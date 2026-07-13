from __future__ import annotations

import logging
import time

from .config import DEFAULT_TRACK_URI, SpotifyConfig
from .os_utils import focus_spotify_window, launch_uri, open_or_focus_spotify

logger = logging.getLogger(__name__)


class SpotifyController:
    def __init__(self, config: SpotifyConfig):
        self._config = config
        self._resolved_uri: str | None = config.track_uri

    def resolve_uri(self) -> str:
        if self._resolved_uri:
            return self._resolved_uri

        if self._config.client_id and self._config.client_secret:
            uri = self._search_uri_via_web_api()
            if uri:
                self._resolved_uri = uri
                return uri

        logger.info(
            "Usando el URI de canción por defecto (no verificado al 100%%, "
            "confírmalo o reemplázalo con SPOTIFY_TRACK_URI en tu .env): %s",
            DEFAULT_TRACK_URI,
        )
        self._resolved_uri = DEFAULT_TRACK_URI
        return DEFAULT_TRACK_URI

    def _search_uri_via_web_api(self) -> str | None:
        try:
            import spotipy
            from spotipy.oauth2 import SpotifyClientCredentials
        except ImportError:
            logger.warning("spotipy no está instalado; no se puede buscar la canción por API")
            return None

        try:
            auth_manager = SpotifyClientCredentials(
                client_id=self._config.client_id,
                client_secret=self._config.client_secret,
            )
            client = spotipy.Spotify(client_credentials_manager=auth_manager)
            results = client.search(q=self._config.track_query, type="track", limit=1)
            items = results.get("tracks", {}).get("items", [])
            if items:
                return items[0]["uri"]
        except Exception:
            logger.warning("No se pudo resolver la canción vía Spotify Web API", exc_info=True)
        return None

    def trigger(self) -> None:
        cfg = self._config
        logger.info("Aplauso detectado. Abriendo Spotify...")

        open_or_focus_spotify(dry_run=cfg.dry_run)
        time.sleep(cfg.cold_start_wait_seconds if not cfg.dry_run else 0)
        focus_spotify_window(dry_run=cfg.dry_run)
        time.sleep(cfg.focus_wait_seconds if not cfg.dry_run else 0)

        uri = self.resolve_uri()
        logger.info("Reproduciendo %s", uri)
        launch_uri(uri, dry_run=cfg.dry_run)
