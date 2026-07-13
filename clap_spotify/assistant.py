from __future__ import annotations

import json
import logging
from datetime import date, datetime
from pathlib import Path

import requests

from .audio_mixer import duck_spotify_volume, restore_spotify_volume
from .config import AssistantConfig
from .spotify_controller import SpotifyController

logger = logging.getLogger(__name__)

_DAY_NAMES_ES = [
    "lunes",
    "martes",
    "miércoles",
    "jueves",
    "viernes",
    "sábado",
    "domingo",
]

_MONTH_NAMES_ES = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]

_SPANISH_VOICE_HINTS = [
    "spanish",
    "español",
    "espanol",
    "es-",
    "es_",
    "sabina",
    "helena",
    "pablo",
    "raul",
    "raúl",
    "laura",
    "elvira",
]


class HomeAssistant:
    def __init__(self, spotify: SpotifyController, config: AssistantConfig, dry_run: bool = False):
        self._spotify = spotify
        self._config = config
        self._dry_run = dry_run

    def handle_clap(self, force_greeting: bool = False) -> None:
        self._spotify.trigger()

        if not self._config.enabled:
            return

        try:
            if force_greeting or not self._already_greeted_today():
                self._greet()
                self._mark_greeted_today()
        except Exception:
            logger.warning("Falló el saludo del asistente (la música sigue igual)", exc_info=True)

    def _greet(self) -> None:
        text = self._build_greeting()

        if self._dry_run:
            logger.info("[dry-run] el asistente diría: %s", text)
            return

        previous_volume = duck_spotify_volume(self._config.duck_volume_percent)
        try:
            self._speak(text)
        finally:
            restore_spotify_volume(previous_volume)

    def _already_greeted_today(self) -> bool:
        try:
            data = json.loads(Path(self._config.state_file).read_text(encoding="utf-8"))
            return data.get("last_greeted_date") == date.today().isoformat()
        except (OSError, ValueError, json.JSONDecodeError):
            return False

    def _mark_greeted_today(self) -> None:
        try:
            path = Path(self._config.state_file)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"last_greeted_date": date.today().isoformat()}), encoding="utf-8")
        except OSError:
            logger.debug("No se pudo guardar el estado del asistente", exc_info=True)

    def _build_greeting(self) -> str:
        parts = []

        greeting = "Bienvenido a casa"
        if self._config.greeting_title:
            greeting += f", {self._config.greeting_title}"
        parts.append(greeting + ".")

        now = datetime.now()
        day_name = _DAY_NAMES_ES[now.weekday()]
        month_name = _MONTH_NAMES_ES[now.month - 1]
        parts.append(f"Hoy es {day_name} {now.day} de {month_name}, son las {now.hour:02d}:{now.minute:02d}.")

        weather_sentence = self._get_weather_sentence()
        if weather_sentence:
            parts.append(weather_sentence)

        tasks_sentence = self._get_tasks_sentence()
        if tasks_sentence:
            parts.append(tasks_sentence)

        return " ".join(parts)

    def _get_weather_sentence(self) -> str | None:
        cfg = self._config
        if not cfg.city or not cfg.weather_api_key:
            return None

        try:
            response = requests.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"q": cfg.city, "appid": cfg.weather_api_key, "units": "metric", "lang": "es"},
                timeout=5,
            )
            if response.status_code == 401:
                logger.warning(
                    "OpenWeatherMap devolvió 401: la API key puede ser incorrecta o "
                    "todavía no estar activada (puede tardar hasta 2 horas)."
                )
                return None
            response.raise_for_status()
            data = response.json()
            temp = data["main"]["temp"]
            description = data["weather"][0]["description"]
        except Exception:
            logger.debug("No se pudo obtener el clima", exc_info=True)
            return None

        sentence = f"Afuera hay {temp:.0f} grados con {description}."
        if temp < cfg.cold_temperature_threshold_c:
            sentence += " Está fresco, abrigate."
        return sentence

    def _get_tasks_sentence(self) -> str | None:
        try:
            lines = Path(self._config.tasks_file).read_text(encoding="utf-8").splitlines()
        except OSError:
            return None

        tasks = [line.strip() for line in lines if line.strip()]
        if not tasks:
            return None

        tasks = tasks[: self._config.max_tasks_to_read]
        if len(tasks) == 1:
            return f"Tenés una tarea pendiente: {tasks[0]}."
        return "Tenés estas tareas pendientes: " + "; ".join(tasks) + "."

    def _pick_spanish_voice_id(self, voices) -> str | None:
        for voice in voices:
            languages = getattr(voice, "languages", None) or []
            for lang in languages:
                lang_str = lang.decode("utf-8", "ignore") if isinstance(lang, bytes) else str(lang)
                if "es" in lang_str.lower():
                    return voice.id

        for voice in voices:
            haystack = f"{voice.name} {voice.id}".lower()
            if any(hint in haystack for hint in _SPANISH_VOICE_HINTS):
                return voice.id

        return None

    def _speak(self, text: str) -> None:
        try:
            import pyttsx3
        except ImportError:
            logger.warning("pyttsx3 no está instalado; no se puede hablar")
            return

        engine = None
        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", self._config.speech_rate)
            engine.setProperty("volume", self._config.speech_volume)

            voice_id = self._config.voice_id or self._pick_spanish_voice_id(engine.getProperty("voices"))
            if voice_id:
                engine.setProperty("voice", voice_id)
            else:
                logger.info(
                    "No se encontró una voz en español instalada; usando la voz por "
                    "defecto (podés instalar una desde Configuración > Hora e idioma > Voz)."
                )

            engine.say(text)
            engine.runAndWait()
        except Exception:
            logger.warning("Falló la síntesis de voz", exc_info=True)
        finally:
            if engine is not None:
                try:
                    engine.stop()
                except Exception:
                    pass

    @staticmethod
    def list_voices() -> list[tuple[str, str]]:
        import pyttsx3

        engine = pyttsx3.init()
        try:
            return [(voice.id, voice.name) for voice in engine.getProperty("voices")]
        finally:
            engine.stop()
