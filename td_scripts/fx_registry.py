"""Load and validate the effect manifest and its local shader resources."""

from dataclasses import dataclass
import json
import math
from pathlib import Path


@dataclass(frozen=True)
class EffectParameter:
    name: str
    default: float
    minimum: float
    maximum: float


@dataclass(frozen=True)
class EffectDefinition:
    id: str
    name: str
    group: str
    type: str
    supported_inputs: tuple[str, ...]
    parameters: tuple[EffectParameter, ...]
    gpu_cost: str
    dependencies: tuple[str, ...]
    default_preset: str
    shader: str

    @property
    def parameter_vector(self):
        values = tuple(parameter.default for parameter in self.parameters)
        return values + (0.0,) * (4 - len(values))


def load_registry(root_path) -> dict[str, EffectDefinition]:
    root = Path(root_path).resolve()
    manifest = json.loads((root / "presets" / "effects.json").read_text(encoding="utf-8-sig"))
    entries = manifest["effects"] if isinstance(manifest, dict) else manifest
    registry = {}
    for entry in entries:
        effect_id = entry["id"]
        if not isinstance(effect_id, str) or len(effect_id) != 2 or not effect_id.isascii() or not effect_id.isdigit():
            raise ValueError(f"Invalid effect ID: {effect_id!r}")
        if effect_id in registry:
            raise ValueError(f"Duplicate effect ID: {effect_id}")
        shader = (root / entry["shader"]).resolve()
        if not shader.is_relative_to(root / "shaders") or not shader.is_file():
            raise ValueError(f"Missing or invalid shader path for {effect_id}: {entry['shader']}")
        parameters = []
        for item in entry.get("parameters", []):
            default = float(item["default"])
            minimum = float(item.get("min", min(0.0, default)))
            maximum = float(item.get("max", max(1.0, default)))
            if not all(map(math.isfinite, (default, minimum, maximum))) or not minimum <= default <= maximum:
                raise ValueError(f"Invalid parameter bounds in {effect_id}: {item['name']}")
            parameters.append(EffectParameter(item["name"], default, minimum, maximum))
        if len(parameters) > 4 or len({item.name for item in parameters}) != len(parameters):
            raise ValueError(f"Invalid parameter count or duplicate parameter name in {effect_id}")
        registry[effect_id] = EffectDefinition(
            id=effect_id,
            name=entry["name"],
            group=entry["group"],
            type=entry["type"],
            supported_inputs=tuple(entry["supported_inputs"]),
            parameters=tuple(parameters),
            gpu_cost=entry["gpu_cost"],
            dependencies=tuple(entry.get("dependencies", [])),
            default_preset=entry.get("default_preset", "Default"),
            shader=entry["shader"],
        )
    if "00" not in registry:
        raise ValueError("Effect manifest needs the original source mode (00)")
    return registry
