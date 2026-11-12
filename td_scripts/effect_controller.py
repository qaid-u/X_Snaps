"""Single source of truth for persistent modes, transitions and snap routing."""

from dataclasses import dataclass
import json
from pathlib import Path
import random
import time

from .settings_manager import QUALITY_PROFILES, Settings, update_settings
from .transition_library import OVERLAY_IDS, TYPE_TEXT, WIPE_IDS


@dataclass
class AppState:
    current_effect: str = "00"
    previous_effect: str = "00"
    pending_effect: str | None = None
    phase: str = "IDLE"
    time_in_state: float = 0.0
    snap_count: int = 0
    cooldown_remaining: float = 0.0
    source_mode: str = "DEMO"
    playlist: tuple[str, ...] = ()
    profile: str = "BALANCED"
    recording: bool = False
    tracker_health: str = "KEYBOARD"
    feedback_reset: int = 0
    last_reason: str = "startup"


@dataclass(frozen=True)
class TransitionFrame:
    previous_effect: str
    current_effect: str
    transition: tuple[float, float, float, float]
    layers: tuple[float, float, float, float]
    timing: tuple[float, float, float, float]
    typography: str
    phase: str


@dataclass(frozen=True)
class _Change:
    effect_id: str
    reason: str
    transition_id: str | None


def load_playlists(root_path, registry, transitions):
    path = Path(root_path) / "presets" / "playlist.json"
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    playlists = {}
    for name, entry in data["playlists"].items():
        effects = tuple(entry["effects"])
        if not effects or len(set(effects)) != len(effects) or any(item not in registry for item in effects):
            raise ValueError(f"Invalid effects in playlist {name}")
        if entry["transition"] not in transitions:
            raise ValueError(f"Unknown transition for playlist {name}")
        playlists[name] = (effects, entry["transition"])
    if data["default_playlist"] not in playlists:
        raise ValueError("Default playlist is missing")
    return data["default_playlist"], playlists


def load_accessibility(root_path):
    path = Path(root_path) / "presets" / "accessibility.json"
    return json.loads(path.read_text(encoding="utf-8-sig"))["presets"]


class EffectController:
    def __init__(self, registry, settings=None, transitions=None, *, default_playlist=None,
                 accessibility=None, performance_cues=(), rng=None, clock=time.monotonic):
        self.registry = registry
        self.settings = settings or Settings()
        self.transitions = transitions or {}
        self.state = AppState()
        self._default_playlist = tuple(default_playlist or sorted(registry))
        self._accessibility = accessibility or load_accessibility(Path(__file__).resolve().parents[1])
        self._rng = rng or random.Random()
        self._clock = clock
        self._epoch = None
        self._started = None
        self._effect_started = {}
        self._preset = None
        self._duration = 0.0
        self._impact = 0.0
        self._last_snap = float("-inf")
        self._pending = None
        self._phase_started = None
        self._showcase = None
        self._showcase_position = 0
        self._performance_cues = tuple(performance_cues)
        self._performance_position = 0
        self._apply_settings()

    def _apply_settings(self):
        state = self.state
        if state.source_mode != self.settings.source_mode or state.profile != self.settings.profile:
            state.feedback_reset += 1
        state.source_mode = self.settings.source_mode
        state.profile = self.settings.profile
        state.playlist = tuple(effect for effect in self.settings.playlist if effect in self.registry) or self._default_playlist

    def configure(self, **changes):
        self.settings = update_settings(self.settings, effect_ids=self.registry,
                                        transition_ids=self.transitions, **changes)
        self._apply_settings()
        return self.settings

    def set_source(self, mode):
        self.configure(source_mode=mode)

    def invalidate_feedback(self):
        self.state.feedback_reset += 1

    def _moment(self, now):
        return self._clock() if now is None else float(now)

    def _set_phase(self, phase, now):
        if self.state.phase != phase or self._phase_started is None:
            self.state.phase = phase
            self._phase_started = now
        self.state.time_in_state = max(0.0, now - self._phase_started)

    def _cancel_pending(self):
        self._pending = None
        self.state.pending_effect = None

    def _begin(self, change, now):
        state = self.state
        state.previous_effect = state.current_effect
        state.current_effect = change.effect_id
        state.last_reason = change.reason
        self._effect_started[change.effect_id] = now
        state.feedback_reset += 1
        self._cancel_pending()
        preset_id = change.transition_id or self.settings.transition_preset
        self._preset = self.transitions.get(preset_id)
        if self._preset is None:
            self._started = None
            state.previous_effect = state.current_effect
            self._set_phase("IDLE", now)
            return
        self._started = now
        self._duration = self.settings.transition_duration or self._preset.duration
        self._impact = min(self._preset.impact_duration, self._duration * 0.3)
        self._set_phase("PRE_IMPACT", now)

    def set_effect(self, effect_id, reason, now=None, *, transition_id=None, immediate=False):
        """Select a registered effect and apply the configured collision policy."""
        if effect_id not in self.registry:
            return False
        now = self._moment(now)
        self._advance(now)
        change = _Change(effect_id, reason, transition_id)
        if immediate:
            self._cancel_pending()
            self._started = None
            self._preset = None
            self.state.current_effect = effect_id
            self.state.previous_effect = effect_id
            self.state.last_reason = reason
            self._effect_started[effect_id] = now
            self.invalidate_feedback()
            self._set_phase("IDLE", now)
            return True
        if effect_id == self.state.current_effect or effect_id == self.state.pending_effect:
            return False
        if self._started is not None:
            policy = self.settings.transition_policy
            if policy == "ignore" or (policy == "queue-one" and self._pending is not None):
                return False
            if policy == "queue-one":
                self._pending = change
                self.state.pending_effect = effect_id
                return True
        self._begin(change, now)
        return True

    def neighbor(self, step=1):
        playlist = self.state.playlist
        if not playlist:
            return "00"
        try:
            index = playlist.index(self.state.current_effect)
        except ValueError:
            return playlist[0] if step >= 0 else playlist[-1]
        return playlist[(index + step) % len(playlist)]

    def next(self, now=None):
        return self.set_effect(self.neighbor(), "next", now)

    def previous(self, now=None):
        return self.set_effect(self.neighbor(-1), "previous", now)

    def _random_effect(self):
        alternatives = [effect for effect in self.state.playlist if effect != self.state.current_effect]
        return self._rng.choice(alternatives) if alternatives else self.state.current_effect

    def random(self, now=None):
        return self.set_effect(self._random_effect(), "random", now)

    def reset(self, now=None):
        self._showcase = None
        self._performance_position = 0
        self._last_snap = float("-inf")
        self.state.snap_count = 0
        self.state.cooldown_remaining = 0.0
        return self.set_effect("00", "reset", now, immediate=True)

    def snap(self, now=None):
        now = self._moment(now)
        self._advance(now)
        if not self.settings.armed or self.settings.playback_mode == "MANUAL":
            return False
        if now - self._last_snap < self.settings.cooldown:
            return False
        mode = self.settings.playback_mode
        if mode == "SHUFFLE":
            effect_id = self._random_effect()
        else:
            effect_id = self.neighbor()
        transition_id = None
        performance_next = self._performance_position
        if mode == "PERFORMANCE" and self._performance_cues:
            for _ in self._performance_cues:
                cue = self._performance_cues[performance_next]
                performance_next = (performance_next + 1) % len(self._performance_cues)
                if cue.effect_id not in (self.state.current_effect, self.state.pending_effect):
                    effect_id, transition_id = cue.effect_id, cue.transition_id
                    break
        accepted = self.set_effect(effect_id, "snap", now, transition_id=transition_id)
        if accepted:
            self._performance_position = performance_next
            self._last_snap = now
            self.state.snap_count += 1
            self.state.cooldown_remaining = self.settings.cooldown
        return accepted

    def start_showcase(self, duration, cues, now=None):
        if not cues:
            raise ValueError("Showcase requires at least one cue")
        now = self._moment(now)
        self.set_effect("00", "showcase", now, immediate=True)
        self.set_source("DEMO")
        self._showcase = (now, duration, tuple(cues))
        self._showcase_position = 0

    def stop_showcase(self):
        self._showcase = None

    @property
    def showcase_playing(self):
        return self._showcase is not None

    def _advance_showcase(self, now):
        if self._showcase is None:
            return
        started, duration, cues = self._showcase
        elapsed = now - started
        if elapsed >= duration:
            self.stop_showcase()
            return
        index = self._showcase_position
        while index < len(cues) and cues[index].at <= elapsed:
            index += 1
        if index != self._showcase_position:
            self._showcase_position = index
            cue = cues[index - 1]
            self.set_effect(cue.effect_id, "showcase", now, transition_id=cue.transition_id)

    def _advance(self, now):
        self.state.cooldown_remaining = max(0.0, self.settings.cooldown - (now - self._last_snap))
        if self._started is None:
            self._set_phase("IDLE", now)
            return
        elapsed = max(0.0, now - self._started)
        impact_start = self._duration * 0.12
        if elapsed >= self._duration:
            self._started = None
            self.state.previous_effect = self.state.current_effect
            pending = self._pending
            self._cancel_pending()
            if pending is None:
                self._set_phase("IDLE", now)
            else:
                self._begin(pending, now)
        elif elapsed >= self._duration * 0.80:
            self._set_phase("SETTLE", now)
        elif elapsed >= impact_start + self._impact:
            self._set_phase("MORPH", now)
        elif elapsed >= impact_start:
            self._set_phase("SNAP_IMPACT", now)
        else:
            self._set_phase("PRE_IMPACT", now)

    def update(self, now=None) -> TransitionFrame:
        now = self._moment(now)
        self._advance(now)
        self._advance_showcase(now)
        state = self.state
        frame = (state.previous_effect, state.current_effect)
        center = (self.settings.center_x, self.settings.center_y)
        if self._started is None:
            return TransitionFrame(*frame, (1.0, 1.0, *center), (0.0, 0.0, 0.0, 0.0),
                                   (0.0, 0.0, 0.0, -1.0), "", state.phase)

        preset = self._preset
        elapsed = max(0.0, now - self._started)
        progress = elapsed / self._duration
        impact_start = self._duration * 0.12
        wipe_start = impact_start + self._impact * 0.3
        blend = max(0.0, min(1.0, (elapsed - wipe_start) / (self._duration * 0.83 - wipe_start)))
        safety = self._accessibility["LOW_FLASH" if self.settings.low_flash else "STANDARD"]
        flash_duration = min(self._impact, float(safety["max_flash_seconds"]))
        flash = 0.0
        overlays = []
        typography = ""
        type_progress = -1.0
        for element in preset.elements:
            local = element.progress(progress)
            if local is None:
                continue
            if element.id in OVERLAY_IDS:
                overlays.append((OVERLAY_IDS[element.id], local))
            elif element.id in TYPE_TEXT:
                typography, type_progress = TYPE_TEXT[element.id], local
            elif element.id == "IMPACT_FRAME" and impact_start <= elapsed < impact_start + flash_duration:
                flash = min(preset.flash_strength, float(safety["max_flash_strength"]))
                flash *= 1.0 - 0.6 * (elapsed - impact_start) / flash_duration
        overlays += [(0, 0.0)] * (2 - len(overlays))
        center = tuple(max(0.0, min(1.0, a + b - 0.5)) for a, b in zip(preset.center, center))
        return TransitionFrame(
            *frame, (blend, float(safety["layer_strength"]), *center),
            (WIPE_IDS[preset.wipe], flash, overlays[0][0], overlays[1][0]),
            (overlays[0][1], overlays[1][1], elapsed, type_progress), typography, state.phase,
        )

    def effect_uniforms(self, effect_id, now=None):
        now = self._moment(now)
        if self._epoch is None:
            self._epoch = now
        settings = self.settings
        effect = self.registry[effect_id]
        frame = (max(0.0, now - self._epoch), settings.strength, settings.center_x, settings.center_y)
        overrides = (settings.effect_parameters or {}).get(effect_id, {})
        palette = max(0.0, min(3.0, overrides.get("palette", 0.0)))
        options = (max(0.0, now - self._effect_started.setdefault(effect_id, now)),
                   float(int(effect_id)), palette, QUALITY_PROFILES[settings.profile][3])
        parameters = tuple(max(parameter.minimum, min(parameter.maximum, overrides.get(parameter.name, parameter.default)))
                           for parameter in effect.parameters)
        return {"uFrame": frame, "uOptions": options, "uParams": parameters + (0.0,) * (4 - len(parameters))}
