from __future__ import annotations

import argparse
import logging

from .audio_listener import ClapDetector
from .config import load_config
from .spotify_controller import SpotifyController


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Escucha el micrófono y reproduce una canción en Spotify al detectar un aplauso."
    )
    parser.add_argument(
        "--simulate-clap",
        action="store_true",
        help="Dispara la acción de Spotify una vez sin usar el micrófono (para probar el flujo).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="No ejecuta comandos reales del sistema operativo, solo los loggea.",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="Lista los dispositivos de audio disponibles y sale.",
    )
    parser.add_argument("--device", type=str, default=None, help="Índice o nombre del micrófono a usar.")
    parser.add_argument("--calibration-seconds", type=float, default=None)
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(message)s")

    if args.list_devices:
        print(ClapDetector.list_devices())
        return

    config = load_config()
    config.spotify.dry_run = args.dry_run
    if args.device is not None:
        config.clap.device = int(args.device) if args.device.isdigit() else args.device
    if args.calibration_seconds is not None:
        config.clap.calibration_seconds = args.calibration_seconds

    controller = SpotifyController(config.spotify)

    if args.simulate_clap:
        controller.trigger()
        return

    detector = ClapDetector(config.clap, on_clap=controller.trigger)
    try:
        detector.run_forever()
    except KeyboardInterrupt:
        print("\nDeteniendo el detector de aplausos.")


if __name__ == "__main__":
    main()
