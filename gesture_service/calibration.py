"""Run a terminal calibration without sending OSC events."""

import argparse
from dataclasses import replace
from pathlib import Path
import sys
from time import monotonic, sleep

from .main import GestureWorker
from .settings import DEFAULT_CONFIG, DEFAULT_MODEL, GestureSettings, load, save


def _collect(worker, seconds: float, status: bool = False):
    started = monotonic()
    events = []
    audio_peak = 0.0
    hands = 0
    previous = None
    while monotonic() - started < seconds:
        update = worker.poll()
        events.extend(update.events)
        audio_peak = max(audio_peak, update.audio_score)
        hands += update.metrics.separation >= 0
        current = (update.status, update.metrics.phase)
        if status and current != previous:
            previous = current
            print(f"{update.status} | {update.metrics.phase} | separation {update.metrics.separation:.2f}", flush=True)
        if update.status == "CAMERA_UNAVAILABLE":
            sleep(0.08)
    return events, hands, audio_peak


def _prompt(question: str, default):
    answer = input(f"{question} [{default}] ").strip()
    return type(default)(answer) if answer else default


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    args = parser.parse_args()
    try:
        try:
            settings = load(args.config)
        except (ValueError, TypeError):
            settings = GestureSettings()
        camera = _prompt("Camera index (start with 0)", settings.camera)
        mic = _prompt("Use microphone (y/n)", "n").lower() == "y"
        default_mic = -1 if settings.microphone is None else settings.microphone
        microphone = _prompt("Microphone index (-1 for system default)", default_mic) if mic else -1
        level = _prompt("Sensitivity from 1 (strict) to 5 (sensitive)", 3)
        if not 1 <= level <= 5:
            raise ValueError("Sensitivity must be between 1 and 5")
        scale = 1.0 - (level - 3) * 0.115
        detector = replace(settings.detector, min_velocity=3.8 * scale, min_displacement=0.28 * scale)
        threshold = _prompt("Microphone peak threshold", settings.audio_threshold) if mic else settings.audio_threshold
        settings = replace(
            settings, camera=camera, microphone=microphone if microphone >= 0 else None,
            detector=detector, audio_threshold=threshold,
        )
        mode = "AUDIO+VISION" if mic else "VISION"
        worker = GestureWorker(mode, settings, args.model)
        try:
            input("Frame one hand with its wrist and fingers visible, then press Enter. ")
            print("Show one hand, press the thumb against the middle fingertip, then snap.")
            _, hands, audio = _collect(worker, 6.0, status=True)
            print(f"Hand frames: {hands}. Microphone transient score: {audio:.2f}.")
            if hands == 0:
                print("No usable hand landmarks. Check the camera index, permissions, lighting and framing.")
                return 1

            single = misses = excess = 0
            for index in range(1, 11):
                input(f"Trial {index}/10. Press Enter, then snap once during the next three seconds. ")
                events, _, _ = _collect(worker, 3.0)
                count = len(events)
                print(f"{count} detection(s)", flush=True)
                single += count == 1
                misses += count == 0
                excess += max(0, count - 1)
            input("Press Enter and move your hand normally for five seconds without snapping. ")
            false_events, _, _ = _collect(worker, 5.0)
            print(
                f"Single detections: {single}/10 | misses: {misses} | extra detections: {excess} | "
                f"control false triggers: {len(false_events)}"
            )
            if _prompt("Save these thresholds (y/n)", "y").lower() == "y":
                save(args.config, settings)
                print(f"Saved {args.config}")
        finally:
            worker.close()
    except (KeyboardInterrupt, EOFError):
        return 130
    except (OSError, RuntimeError, ImportError, ValueError) as exc:
        print(f"Calibration: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
