"""Read and atomically store the gesture worker's calibration."""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from tempfile import NamedTemporaryFile

from .snap_detector import DetectorSettings

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "gesture_settings.json"
DEFAULT_MODEL = ROOT / "assets" / "models" / "hand_landmarker.task"


@dataclass(frozen=True)
class GestureSettings:
    camera: int = 0
    microphone: int | None = None
    audio_threshold: float = 0.035
    audio_window: float = 0.10
    detector: DetectorSettings = field(default_factory=DetectorSettings)
    camera_width: int = 640
    camera_height: int = 480
    camera_fps: int = 60
    camera_backend: str = "auto"

    def __post_init__(self):
        if type(self.camera) is not int or self.camera < 0:
            raise ValueError("Camera index must be a nonnegative integer")
        if self.microphone is not None and (type(self.microphone) is not int or self.microphone < 0):
            raise ValueError("Microphone index must be null or a nonnegative integer")
        if not 0.003 <= self.audio_threshold <= 0.95:
            raise ValueError("Invalid audio threshold")
        if not 0.02 <= self.audio_window <= 0.35:
            raise ValueError("Invalid audio sync window")
        for value, minimum, maximum, label in (
            (self.camera_width, 160, 1920, "width"),
            (self.camera_height, 120, 1080, "height"),
            (self.camera_fps, 15, 120, "FPS"),
        ):
            if type(value) is not int or not minimum <= value <= maximum:
                raise ValueError(f"Camera {label} must be between {minimum} and {maximum}")
        if self.camera_backend not in ("auto", "dshow", "msmf", "any"):
            raise ValueError("Camera backend must be auto, dshow, msmf or any")


def load(path: Path) -> GestureSettings:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return GestureSettings()
    if not isinstance(data, dict) or data.pop("schema_version", None) != 1:
        raise ValueError("Gesture settings require schema_version 1")
    return GestureSettings(detector=DetectorSettings(**data.pop("detector", {})), **data)


def save(path: Path, settings: GestureSettings) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=path.name, suffix=".tmp", delete=False,
    )
    temporary_path = Path(temporary.name)
    try:
        with temporary:
            json.dump({"schema_version": 1, **asdict(settings)}, temporary, indent=2)
            temporary.write("\n")
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)
