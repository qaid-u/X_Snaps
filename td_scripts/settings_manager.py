"""Versioned user settings and atomic, local JSON persistence."""

from dataclasses import asdict, dataclass, fields
import json
import math
from pathlib import Path
import tempfile


SOURCE_MODES = ("DEMO", "SCREEN", "VIDEO", "IMAGE", "CAMERA")
PLAYBACK_MODES = ("SEQUENTIAL", "SHUFFLE", "MANUAL", "PERFORMANCE")
TRANSITION_POLICIES = ("ignore", "queue-one", "interrupt")
QUALITY_PROFILES = {"LOW": (640, 360, 30, 0), "BALANCED": (960, 540, 60, 1), "HIGH": (1280, 720, 60, 2)}


@dataclass(frozen=True)
class Settings:
    schema_version: int = 1
    source_mode: str = "DEMO"
    playback_mode: str = "SEQUENTIAL"
    transition_policy: str = "queue-one"
    transition_preset: str = "SnapChain"
    transition_duration: float = 0.0
    cooldown: float = 0.65
    strength: float = 1.0
    center_x: float = 0.5
    center_y: float = 0.5
    profile: str = "BALANCED"
    low_flash: bool = True
    armed: bool = True
    playlist: tuple[str, ...] = ()
    effect_parameters: dict | None = None
    video_path: str = ""
    image_path: str = ""
    output_monitor: int = 0
    camera_flip: bool = False
    crop: bool = False
    camera_independent: bool = False
    video_play: bool = True
    video_loop: bool = True


def _number(value, fallback, minimum, maximum):
    if not _finite_number(value):
        return fallback
    return max(minimum, min(maximum, float(value)))


def _finite_number(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _enum(value, choices, fallback):
    return value if isinstance(value, str) and value in choices else fallback


def _boolean(value, fallback):
    return value if isinstance(value, bool) else fallback


def _path(value):
    return value if isinstance(value, str) and "\0" not in value else ""


def settings_from_mapping(raw, effect_ids=(), transition_ids=()):
    baseline = Settings()
    if not isinstance(raw, dict):
        return baseline
    version = raw.get("schema_version", 1)
    if type(version) is not int or version != 1:
        raise ValueError(f"Unsupported settings schema version: {version!r}")
    raw_playlist = raw.get("playlist")
    playlist = tuple(dict.fromkeys(effect for effect in raw_playlist if isinstance(effect, str)
                                   and (effect in effect_ids or not effect_ids))) if isinstance(raw_playlist, (list, tuple)) else ()
    raw_parameters = raw.get("effect_parameters")
    parameters = {}
    if isinstance(raw_parameters, dict):
        for effect, values in raw_parameters.items():
            if (effect_ids and effect not in effect_ids) or not isinstance(values, dict):
                continue
            parameters[effect] = {
                name: float(value) for name, value in values.items()
                if isinstance(name, str) and _finite_number(value)
            }
    raw_duration = raw.get("transition_duration", 0.0)
    duration = 0.0 if raw_duration == 0 else _number(raw_duration, 0.0, 0.10, 3.0)
    return Settings(
        source_mode=_enum(raw.get("source_mode"), SOURCE_MODES, baseline.source_mode),
        playback_mode=_enum(raw.get("playback_mode"), PLAYBACK_MODES, baseline.playback_mode),
        transition_policy=_enum(raw.get("transition_policy"), TRANSITION_POLICIES, baseline.transition_policy),
        transition_preset=_enum(raw.get("transition_preset"), transition_ids or ("SnapChain", "GentleLowFlash"),
                                baseline.transition_preset),
        transition_duration=duration,
        cooldown=_number(raw.get("cooldown"), baseline.cooldown, 0.0, 5.0),
        strength=_number(raw.get("strength"), baseline.strength, 0.0, 1.0),
        center_x=_number(raw.get("center_x"), baseline.center_x, 0.0, 1.0),
        center_y=_number(raw.get("center_y"), baseline.center_y, 0.0, 1.0),
        profile=_enum(raw.get("profile"), QUALITY_PROFILES, baseline.profile),
        low_flash=_boolean(raw.get("low_flash"), baseline.low_flash),
        armed=_boolean(raw.get("armed"), baseline.armed),
        playlist=playlist,
        effect_parameters=parameters or None,
        video_path=_path(raw.get("video_path")),
        image_path=_path(raw.get("image_path")),
        output_monitor=int(_number(raw.get("output_monitor"), baseline.output_monitor, 0, 31)),
        camera_flip=_boolean(raw.get("camera_flip"), baseline.camera_flip),
        crop=_boolean(raw.get("crop"), baseline.crop),
        camera_independent=_boolean(raw.get("camera_independent"), baseline.camera_independent),
        video_play=_boolean(raw.get("video_play"), baseline.video_play),
        video_loop=_boolean(raw.get("video_loop"), baseline.video_loop),
    )


def load_settings(path, effect_ids=(), transition_ids=()) -> tuple[Settings, str | None]:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        if not isinstance(raw, dict):
            raise ValueError("Expected a JSON settings object")
        return settings_from_mapping(raw, effect_ids, transition_ids), None
    except FileNotFoundError:
        return Settings(), None
    except (OSError, UnicodeError, ValueError) as exc:
        return Settings(), f"Could not load {path}: {exc}"


def save_settings(path, settings):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=target.parent,
                                         prefix=f".{target.name}.", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(asdict(settings), stream, indent=2, allow_nan=False)
            stream.write("\n")
        temporary.replace(target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def update_settings(settings, *, effect_ids=(), transition_ids=(), **changes):
    known = {item.name for item in fields(Settings)}
    if unknown := changes.keys() - known:
        raise ValueError(f"Unknown settings: {', '.join(sorted(unknown))}")
    return settings_from_mapping(asdict(settings) | changes, effect_ids, transition_ids)
