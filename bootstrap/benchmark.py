"""Measure the live SNAP//REALITY TouchDesigner process without pixel readback."""

from collections import Counter
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import platform
from statistics import fmean
from time import perf_counter
import traceback

import td


APP_PATH = "/project1/SNAP_REALITY"
WARMUP_SECONDS = 2.0
_active = None
last_error = ""


def _stats(values):
    ordered = sorted(values)
    return {
        "mean": round(fmean(ordered), 3),
        "min": round(ordered[0], 3),
        "p95": round(ordered[math.ceil(0.95 * len(ordered)) - 1], 3),
        "max": round(ordered[-1], 3),
    }


class _Benchmark:
    def __init__(self, app, output_path, seconds):
        self.final = app.op("OUT_FINAL")
        self.timing = app.op("DIAGNOSTICS/TIMING")
        self.dropped_channel = "dropped_frames" if self.timing["dropped_frames"] is not None else "droppedframes"
        self.controller = app.op("CONTROL_ENGINE/runtime").module.controller
        self.output_path = output_path
        self.seconds = seconds
        self.warmup_ends = perf_counter() + WARMUP_SECONDS
        self.started = None
        self.last_frame = None
        self.fps = []
        self.cook_ms = []
        self.dropped = 0
        self.timeline_gaps = 0
        self.effects = Counter()
        self.phases = Counter()
        self.conditions = []
        self.trace = []
        self.next_trace_second = 1
        self.start_cooks = 0

    def schedule(self):
        td.run(self.sample, delayFrames=1, delayRef=td.op("/"), group="SNAP_REALITY_BENCHMARK")

    def _conditions(self):
        state = self.controller.state
        return {
            "source": state.source_mode,
            "profile": state.profile,
            "resolution": [self.final.width, self.final.height],
            "target_fps": td.project.cookRate,
            "perform_mode": bool(td.ui.performMode),
        }

    def sample(self):
        global _active, last_error
        if _active is not self:
            return
        try:
            now = perf_counter()
            if now < self.warmup_ends:
                self.schedule()
                return
            if self.started is None:
                self.started = now
                self.start_cooks = self.final.totalCooks
            elapsed = now - self.started
            frame = td.absTime.frame
            if frame == self.last_frame:
                self.schedule()
                return
            if self.last_frame is not None:
                self.timeline_gaps += max(0, round(frame - self.last_frame) - 1)
            self.last_frame = frame
            fps = float(self.timing["fps"].eval())
            cook_ms = float(self.timing["msec"].eval())
            dropped = max(0, round(self.timing[self.dropped_channel].eval()))
            self.fps.append(fps)
            self.cook_ms.append(cook_ms)
            if len(self.fps) > 1:
                self.dropped += dropped
            state = self.controller.state
            self.effects[state.current_effect] += 1
            self.phases[state.phase] += 1
            if not self.conditions or elapsed >= self.next_trace_second:
                conditions = self._conditions()
                if not self.conditions or self.conditions[-1]["conditions"] != conditions:
                    self.conditions.append({"at_seconds": round(elapsed, 3), "conditions": conditions})
            if elapsed >= self.next_trace_second:
                self.trace.append({
                    "elapsed_seconds": round(elapsed, 3),
                    "fps": fps,
                    "cook_ms": cook_ms,
                    "dropped_since_start": self.dropped,
                    "absolute_frame_gaps_since_start": self.timeline_gaps,
                    "effect": state.current_effect,
                    "phase": state.phase,
                })
                self.next_trace_second = int(elapsed) + 1
            if elapsed >= self.seconds:
                self.finish(elapsed)
                _active = None
            else:
                self.schedule()
        except Exception:
            last_error = traceback.format_exc()
            _active = None
            try:
                error_path = self.output_path.with_suffix(".error.txt")
                error_path.parent.mkdir(parents=True, exist_ok=True)
                error_path.write_text(f"Benchmark stopped after {len(self.fps)} samples.\n{last_error}", encoding="utf-8")
            except OSError as exc:
                print(f"Could not write the benchmark failure report: {exc}")
            raise

    def finish(self, elapsed):
        report = {
            "schema_version": 1,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "touchdesigner_build": str(td.app.build),
            "project": str(td.project.name),
            "platform": platform.platform(),
            "cpu": platform.processor(),
            "gpu": str(getattr(td.sysinfo, "GPUName", "unavailable")),
            "requested_seconds": self.seconds,
            "measured_seconds": round(elapsed, 3),
            "sampled_frames": len(self.fps),
            "fps": _stats(self.fps),
            "frame_cook_ms": _stats(self.cook_ms),
            "dropped_frames": self.dropped,
            "absolute_timeline_frame_gaps": self.timeline_gaps,
            "final_top_cooks": self.final.totalCooks - self.start_cooks,
            "effect_samples": dict(self.effects),
            "phase_samples": dict(self.phases),
            "conditions": self.conditions,
            "trace": self.trace,
            "measurement": {
                "warmup_seconds": WARMUP_SECONDS,
                "source": "TouchDesigner Perform CHOP, sampled once per scheduled frame",
                "fps": "Rolling rendered-frame count for the last second, reported by TouchDesigner",
                "dropped_frames": "Sum of Perform CHOP drops since the preceding sample, excluding the first sample",
                "absolute_timeline_frame_gaps": "Independent count of gaps between scheduled absolute frames",
                "scope": "TouchDesigner process and current project load. Display refresh and physical presentation are outside this measurement.",
            },
        }
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.output_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        temporary.replace(self.output_path)
        print(f"SNAP//REALITY benchmark saved: {self.output_path}")


def start(root, seconds=60):
    """Start a wall-clock benchmark. Keep the timeline and live preview running."""
    global _active, last_error
    if _active is not None:
        raise RuntimeError("A SNAP//REALITY benchmark is already running")
    seconds = float(seconds)
    if not math.isfinite(seconds) or seconds < 1.0:
        raise ValueError("Benchmark duration must be at least one second")
    app = td.op(APP_PATH)
    if app is None or app.op("DIAGNOSTICS/TIMING") is None:
        raise RuntimeError("Open the full SNAP//REALITY project before benchmarking")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output_path = Path(root).resolve() / "reports" / f"benchmark-{stamp}.json"
    session = _Benchmark(app, output_path, seconds)
    last_error = ""
    session.schedule()
    _active = session
    print(f"SNAP//REALITY benchmark started ({seconds:g}s, after {WARMUP_SECONDS:g}s warm-up)")
    return output_path
