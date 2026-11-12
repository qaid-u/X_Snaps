"""Run the opt-in camera and microphone bridge on the local machine."""

import argparse
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path
import sys
from time import monotonic, sleep

from .audio_confirmation import AudioMatcher, Microphone
from .osc_sender import OscSender, PORT
from .settings import DEFAULT_CONFIG, DEFAULT_MODEL, GestureSettings, load
from .snap_detector import Metrics, SnapCandidate, SnapDetector
from .tracker import HandTracker

MODES = ("VISION", "AUDIO+VISION", "AUDIO_ONLY", "KEYBOARD")


@dataclass
class Update:
    status: str
    details: str
    metrics: Metrics
    audio_score: float
    events: list[SnapCandidate]
    fresh_frame: bool = False


class GestureWorker:
    def __init__(self, mode: str, settings: GestureSettings, model: Path, *, preview=False):
        self.mode = mode
        self.detector = SnapDetector(settings.detector)
        self.tracker = (
            HandTracker(model, settings.camera, width=settings.camera_width, height=settings.camera_height,
                        fps=settings.camera_fps, backend=settings.camera_backend, preview=preview)
            if mode in {"VISION", "AUDIO+VISION"} else None
        )
        self.matcher = AudioMatcher(settings.audio_window)
        self.microphone = None
        self.mic_issue = ""
        self.mic_opened = monotonic()
        if mode in {"AUDIO+VISION", "AUDIO_ONLY"}:
            try:
                self.microphone = Microphone(settings.microphone, settings.audio_threshold)
            except Exception as exc:
                self.mic_issue = str(exc)
        self.next_camera_attempt = 0.0
        self.last_audio_event = float("-inf")
        self.last_audio_pulse = float("-inf")
        self.audio_score = 0.0

    def poll(self) -> Update:
        candidate = None
        fresh_frame = False
        if self.tracker is not None:
            now = monotonic()
            if self.tracker.capture is None and now >= self.next_camera_attempt:
                self.tracker.open_camera()
                self.next_camera_attempt = now + 2.0
            observation = self.tracker.read() if self.tracker.capture is not None else None
            if observation is None and self.tracker.capture is None:
                self.detector.clear_tracking()
                self.matcher.clear()
                if self.microphone:
                    self.microphone.drain()
                return Update("CAMERA_UNAVAILABLE",
                              getattr(self.tracker, "camera_status", "Camera busy, unplugged or blocked. Retrying."),
                              Metrics(), 0.0, [])
            if observation is not None:
                fresh_frame = True
                candidate = self.detector.step(*observation)
        now = monotonic()
        if self.microphone and now - self.mic_opened > 1.5 and not self.microphone.working:
            self.microphone.close()
            self.microphone = None
            self.mic_issue = "Audio stream stopped. Restart the bridge to reconnect."
            self.matcher.clear()

        pulses = self.microphone.drain() if self.microphone else []
        if pulses:
            self.last_audio_pulse = pulses[-1].timestamp
            self.audio_score = pulses[-1].score
        audio = self.audio_score if now - self.last_audio_pulse < 0.25 else 0.0

        if self.mode == "AUDIO+VISION" and self.microphone:
            events = self.matcher.step(now, candidate, pulses)
            status, details = "AUDIO+VISION", "Camera and microphone active"
        elif self.mode == "AUDIO_ONLY":
            events = []
            for pulse in pulses:
                if pulse.timestamp - self.last_audio_event >= self.detector.settings.cooldown:
                    self.last_audio_event = pulse.timestamp
                    events.append(SnapCandidate(pulse.timestamp, pulse.score * 0.65, "AUDIO"))
            status = "AUDIO_ONLY" if self.microphone else "MIC_UNAVAILABLE"
            details = self.mic_issue or "Experimental. Other sharp sounds may trigger."
        elif self.mode == "AUDIO+VISION":
            events = [replace(candidate, confidence=candidate.confidence * 0.76)] if candidate else []
            status, details = "VISION_LOW_CONFIDENCE", f"Microphone unavailable. {self.mic_issue}"
        elif self.mode == "VISION":
            events = [replace(candidate, confidence=candidate.confidence * 0.84)] if candidate else []
            status, details = "VISION", "Vision only, lower confidence"
        else:
            events = []
            status, details = "KEYBOARD", "Use Space or N in TouchDesigner"
        metrics = self.detector.metrics
        if self.tracker is not None:
            details = f"{self.tracker.tracking_status.replace('_', ' ')} | {self.tracker.camera_status}"
            if self.mode == "AUDIO+VISION" and self.microphone is None:
                details += f" | Mic unavailable: {self.mic_issue}" if self.mic_issue else " | Mic unavailable"
            elif self.mode == "AUDIO+VISION" and self.matcher.candidates and not events:
                metrics = replace(metrics, phase="AUDIO_WAIT")
        return Update(status, details, metrics, audio, events, fresh_frame)

    def close(self):
        try:
            if self.microphone:
                self.microphone.close()
        finally:
            if self.tracker:
                self.tracker.close()


def _run(args) -> None:
    try:
        settings = load(args.config)
    except (ValueError, OSError, TypeError) as exc:
        print(f"Using defaults because {args.config.name} could not be read: {exc}", file=sys.stderr)
        settings = GestureSettings()
    overrides = {
        "camera": args.camera, "microphone": args.microphone, "camera_width": args.width,
        "camera_height": args.height, "camera_fps": args.fps, "camera_backend": args.backend,
    }
    settings = replace(settings, **{key: value for key, value in overrides.items() if value is not None})

    sender = OscSender(args.port)
    worker = None
    try:
        sender.health("STARTING", args.mode)
        worker = GestureWorker(args.mode, settings, args.model, preview=args.preview)
        deadline = monotonic() + args.seconds if args.seconds is not None else float("inf")
        frames = tracked = snaps = 0
        phases = Counter()
        last_status = ""
        last_health = last_metrics = last_control = float("-inf")
        while monotonic() < deadline:
            update = worker.poll()
            now = monotonic()
            if now - last_control >= 0.1:
                last_control = now
                if args.stop_file and args.stop_file.is_file():
                    break
            if update.fresh_frame:
                frames += 1
                tracked += update.metrics.separation >= 0
                phases[update.metrics.phase] += 1
            if update.status != last_status or (args.diagnostics and now - last_health >= 1.0):
                print(f"{update.status} | {update.details}", flush=True)
                if args.diagnostics and worker.tracker is not None:
                    print(f"  {update.metrics.phase} | separation {update.metrics.separation:.2f} | "
                          f"speed {update.metrics.velocity:.1f} | "
                          f"audio {update.audio_score:.2f} | tracked {tracked}/{frames}", flush=True)
            if update.status != last_status or now - last_health >= 1.0:
                sender.health(update.status, update.details)
                last_health, last_status = now, update.status
            if now - last_metrics >= 0.1:
                sender.metrics(update.metrics, update.audio_score)
                last_metrics = now
            for event in update.events:
                snaps += 1
                event_id = sender.event(event)
                print(f"Snap {event_id} | {event.hand} | confidence {event.confidence:.2f}", flush=True)
            if args.preview and not worker.tracker.show_preview((
                f"{update.metrics.phase}  distance {update.metrics.separation:.2f}",
                f"{snaps} snaps  |  Q / Esc to close",
            )):
                break
            if not worker.tracker or worker.tracker.capture is None:
                sleep(0.025 if worker.microphone else 0.10)
        if args.diagnostics:
            print(f"Summary | {frames} processed | {tracked} hand frames | {snaps} snaps | "
                  + ", ".join(f"{phase} {count}" for phase, count in phases.most_common()), flush=True)
        sender.health("STOPPED", "Bridge stopped")
    except KeyboardInterrupt:
        sender.health("STOPPED", "Bridge stopped")
    except (RuntimeError, OSError, ImportError, ValueError) as exc:
        sender.health("ERROR", str(exc))
        raise
    finally:
        if worker is not None:
            worker.close()
        sender.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=MODES, default="VISION")
    parser.add_argument("--camera", type=int)
    parser.add_argument("--microphone", type=int)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--width", type=int, help="Requested camera width")
    parser.add_argument("--height", type=int, help="Requested camera height")
    parser.add_argument("--fps", type=int, help="Requested camera FPS")
    parser.add_argument("--backend", choices=("auto", "dshow", "msmf", "any"))
    parser.add_argument("--preview", action="store_true", help="Show local landmarks and camera diagnostics")
    parser.add_argument("--diagnostics", action="store_true", help="Print live rates and a session summary")
    parser.add_argument("--seconds", type=float, help="Stop after this many seconds of camera testing")
    parser.add_argument("--stop-file", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.preview and args.mode not in {"VISION", "AUDIO+VISION"}:
        parser.error("--preview requires a vision mode")
    if args.seconds is not None and not 0 < args.seconds <= 3600:
        parser.error("--seconds must be greater than zero and at most 3600")
    try:
        _run(args)
    except (RuntimeError, OSError, ImportError, ValueError) as exc:
        print(f"Gesture bridge: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
