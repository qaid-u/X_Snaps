"""Data-driven definitions for GPU wipes, overlays and showcase cues."""

from dataclasses import dataclass
import json
from pathlib import Path


WIPE_IDS = {"CROSSFADE": 0, "RADIAL": 1, "INK_WIPE": 2, "DIGITAL": 3, "DIAGONAL": 4}
OVERLAY_IDS = {
    "NEON_BEAMS": 1, "EXPLOSION_BURST": 2, "GOLDEN_SIGIL": 3, "SHARD_PORTAL": 4,
    "PASTEL_POLYGONS": 5, "PERSPECTIVE_TUNNEL": 6, "DIGITAL_FRAGMENT": 7, "INK_WIPE": 8,
}
TYPE_TEXT = {"TYPE_SNAP": "SNAP!", "TYPE_POP": "POP!"}
ELEMENTS = set(OVERLAY_IDS) | set(TYPE_TEXT) | {"IMPACT_FRAME"}


@dataclass(frozen=True)
class TimelineElement:
    id: str
    start: float
    end: float

    def progress(self, progress):
        if self.start < progress < self.end:
            return (progress - self.start) / (self.end - self.start)
        return None


@dataclass(frozen=True)
class TransitionDefinition:
    id: str
    duration: float
    center: tuple[float, float]
    impact_duration: float
    flash_strength: float
    wipe: str
    audio_cue: str | None
    elements: tuple[TimelineElement, ...]


@dataclass(frozen=True)
class ShowcaseCue:
    at: float
    effect_id: str
    transition_id: str
    inspiration: str


def load_transitions(root_path) -> dict[str, TransitionDefinition]:
    path = Path(root_path) / "presets" / "transitions.json"
    presets = json.loads(path.read_text(encoding="utf-8-sig"))
    transitions = {}
    for entry in presets["transitions"]:
        preset = TransitionDefinition(
            id=entry["id"], duration=float(entry["duration"]), center=tuple(entry["center"]),
            impact_duration=float(entry["impact_duration"]), flash_strength=float(entry["flash_strength"]),
            wipe=entry["wipe"], audio_cue=entry.get("audio_cue"),
            elements=tuple(TimelineElement(**item) for item in entry["elements"]),
        )
        if preset.id in transitions or preset.wipe not in WIPE_IDS:
            raise ValueError(f"Duplicate preset or unknown wipe: {preset.id}")
        if not 0.10 <= preset.duration <= 3.0 or not 0.01 <= preset.impact_duration < preset.duration * 0.4:
            raise ValueError(f"Invalid transition timing: {preset.id}")
        if len(preset.center) != 2 or not all(0.0 <= value <= 1.0 for value in preset.center):
            raise ValueError(f"Invalid center: {preset.id}")
        if not 0.0 <= preset.flash_strength <= 0.30:
            raise ValueError(f"Flash strength exceeds GPU compositor limits: {preset.id}")
        if any(element.id not in ELEMENTS or not 0.0 <= element.start < element.end <= 1.0
               for element in preset.elements):
            raise ValueError(f"Invalid overlay element: {preset.id}")
        sample_times = sorted({value for element in preset.elements for value in (element.start, element.end)})
        for start, end in zip(sample_times, sample_times[1:]):
            active = [element.id for element in preset.elements if element.progress((start + end) / 2) is not None]
            if sum(item in OVERLAY_IDS for item in active) > 2 or sum(item in TYPE_TEXT for item in active) > 1:
                raise ValueError(f"Overlay capacity exceeded: {preset.id}")
        transitions[preset.id] = preset
    if "GentleLowFlash" not in transitions:
        raise ValueError("A low-flash default is required")
    return transitions


def load_showcase(root_path, registry, transitions) -> tuple[float, tuple[ShowcaseCue, ...]]:
    path = Path(root_path) / "presets" / "reference_inspired_timeline.json"
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    duration = float(data["showcase"]["duration"])
    cues = tuple(ShowcaseCue(**entry) for entry in data["showcase"]["cues"])
    labels = {entry["label"] for entry in data["inspirations"]}
    if not 60.0 <= duration <= 75.0:
        raise ValueError("Showcase length must be 60–75 seconds")
    previous = -1.0
    for cue in cues:
        if not previous < cue.at < duration:
            raise ValueError(f"Showcase cues must be chronological: {cue}")
        if cue.effect_id not in registry or cue.transition_id not in transitions or cue.inspiration not in labels:
            raise ValueError(f"Unknown effect, transition or inspiration: {cue}")
        previous = cue.at
    return duration, cues
