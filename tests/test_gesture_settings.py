from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from gesture_service.settings import GestureSettings, load, save

ROOT = Path(__file__).resolve().parents[1]


class GestureSettingsTests(unittest.TestCase):
    def test_roundtrip_and_replace(self):
        with TemporaryDirectory(dir=ROOT) as temporary:
            path = Path(temporary) / "config" / "gesture_settings.json"
            self.assertEqual(load(path), GestureSettings())
            selected = GestureSettings(camera=1, microphone=0, audio_window=0.12)
            save(path, selected)
            self.assertEqual(load(path), selected)
            replacement = replace(selected, microphone=None)
            save(path, replacement)
            self.assertEqual(load(path), replacement)
            self.assertEqual(list(path.parent.iterdir()), [path])

    def test_invalid_threshold_and_schema(self):
        with TemporaryDirectory(dir=ROOT) as temporary:
            path = Path(temporary) / "gesture_settings.json"
            path.write_text('{"schema_version": 2}', encoding="utf-8")
            with self.assertRaises(ValueError):
                load(path)
            path.write_text('{"schema_version": 1, "detector": {"contact_distance": 1.8}}', encoding="utf-8")
            with self.assertRaises(ValueError):
                load(path)


if __name__ == "__main__":
    unittest.main()
