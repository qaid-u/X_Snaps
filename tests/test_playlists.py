from pathlib import Path
import random
import unittest

from td_scripts.effect_controller import EffectController, load_playlists
from td_scripts.fx_registry import load_registry
from td_scripts.transition_library import load_transitions


ROOT = Path(__file__).resolve().parents[1]


class PlaylistTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = load_registry(ROOT)
        cls.transitions = load_transitions(ROOT)

    def test_manifest_references_only_installed_modes_and_presets(self):
        default, playlists = load_playlists(ROOT, self.registry, self.transitions)
        self.assertEqual(set(playlists[default][0]), set(self.registry))
        self.assertEqual(playlists["First Five"][0], ("00", "06", "03", "04", "09"))
        for effects, transition in playlists.values():
            self.assertTrue(set(effects) <= self.registry.keys())
            self.assertIn(transition, self.transitions)

    def test_wrap_order_and_manual_selection_of_a_disabled_mode(self):
        controller = EffectController(self.registry, transitions=self.transitions, default_playlist=("00", "03", "06"))
        self.assertTrue(controller.previous(0.0))
        self.assertEqual(controller.update(0.6).current_effect, "06")
        self.assertTrue(controller.next(0.7))
        self.assertEqual(controller.update(1.3).current_effect, "00")
        self.assertTrue(controller.set_effect("09", "library", 1.4))
        self.assertEqual(controller.update(2.0).current_effect, "09")
        self.assertEqual(controller.neighbor(), "00")

    def test_shuffle_always_moves_to_a_different_enabled_effect(self):
        controller = EffectController(self.registry, transitions=self.transitions, rng=random.Random(79))
        controller.configure(playlist=["06", "09", "04"], playback_mode="SHUFFLE")
        for moment in range(50):
            before = controller.state.current_effect
            self.assertTrue(controller.snap(float(moment)))
            after = controller.update(moment + 0.5).current_effect
            self.assertIn(after, controller.state.playlist)
            self.assertNotEqual(after, before)
