from pathlib import Path
import unittest

from td_scripts.fx_registry import load_registry
from td_scripts.transition_library import ELEMENTS, load_showcase, load_transitions


ROOT = Path(__file__).resolve().parents[1]


class PresetTests(unittest.TestCase):
    def test_catalog_ids_and_shader_resources_are_complete(self):
        catalog = load_registry(ROOT)
        self.assertEqual(set(catalog), {f"{index:02}" for index in range(21)})
        self.assertEqual(len({item.shader for item in catalog.values()}), 21)
        for item in catalog.values():
            self.assertEqual(item.type, "persistent")
            self.assertEqual(len(item.parameter_vector), 4)
            self.assertTrue(item.default_preset)
            self.assertIn("DEMO", item.supported_inputs)
            source = (ROOT / item.shader).read_text(encoding="utf-8")
            self.assertIn("void main()", source)
        for resource in ("common.glsl", "transition_compositor.frag", "demo.frag"):
            self.assertTrue((ROOT / "shaders" / resource).is_file())

    def test_transition_presets_cover_the_overlay_catalog(self):
        transitions = load_transitions(ROOT)
        self.assertTrue({"SnapChain", "ComicHit", "InkPortal", "GlitchBreak", "NeonSwitch",
                         "GentleLowFlash"} <= transitions.keys())
        self.assertEqual({element.id for item in transitions.values() for element in item.elements}, ELEMENTS)
        self.assertEqual(transitions["GentleLowFlash"].flash_strength, 0.0)

    def test_showcase_length_labels_and_cues(self):
        duration, cues = load_showcase(ROOT, load_registry(ROOT), load_transitions(ROOT))
        self.assertEqual(duration, 72.0)
        self.assertEqual(len(cues), 36)
        self.assertEqual(len({cue.inspiration for cue in cues}), 36)
        self.assertTrue((ROOT / "presets" / "reference_inspired_timeline.schema.json").is_file())
