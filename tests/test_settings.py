from pathlib import Path
import tempfile
import unittest

from td_scripts.settings_manager import Settings, load_settings, save_settings, settings_from_mapping


ROOT = Path(__file__).resolve().parents[1]


class SettingsTests(unittest.TestCase):
    def test_invalid_fields_use_defaults_and_valid_fields_are_sanitized(self):
        result = settings_from_mapping({
            "source_mode": ["bad"], "profile": None, "cooldown": 10**600,
            "strength": 1.7, "playlist": ["00", "06", "06", "86", 8], "low_flash": "yes",
            "transition_duration": -1, "output_monitor": True, "video_path": "invalid\0name",
            "effect_parameters": {"06": {"Palette levels": 4, "Dither": float("nan")}},
        }, ("00", "06"))
        self.assertEqual(result.source_mode, "DEMO")
        self.assertEqual(result.profile, "BALANCED")
        self.assertEqual(result.cooldown, Settings().cooldown)
        self.assertEqual(result.strength, 1.0)
        self.assertEqual(result.playlist, ("00", "06"))
        self.assertTrue(result.low_flash)
        self.assertEqual(result.output_monitor, 0)
        self.assertEqual(result.video_path, "")
        self.assertEqual(result.effect_parameters, {"06": {"Palette levels": 4.0}})

    def test_atomic_roundtrip_and_malformed_recovery(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            settings_file = Path(temporary) / "subfolder" / "settings.json"
            self.assertEqual(load_settings(settings_file), (Settings(), None))
            changed = Settings(source_mode="IMAGE", image_path="media/séquence.png", playlist=("09", "04"))
            save_settings(settings_file, changed)
            self.assertEqual(load_settings(settings_file), (changed, None))
            self.assertEqual(list(settings_file.parent.iterdir()), [settings_file])
            for bad in ("[", "[]", '{"schema_version":999}'):
                settings_file.write_text(bad, encoding="utf-8")
                recovered, message = load_settings(settings_file)
                self.assertEqual(recovered, Settings())
                self.assertTrue(message.startswith("Could not load "))
