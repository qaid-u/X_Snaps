from pathlib import Path
import unittest

from td_scripts.effect_controller import EffectController
from td_scripts.fx_registry import load_registry
from td_scripts.transition_library import load_showcase, load_transitions


ROOT = Path(__file__).resolve().parents[1]


class TransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = load_registry(ROOT)
        cls.transitions = load_transitions(ROOT)

    def controller(self, **settings):
        controller = EffectController(self.registry, transitions=self.transitions)
        controller.configure(**settings)
        return controller

    def test_transition_visits_each_phase_in_order(self):
        controller = self.controller()
        self.assertEqual(controller.update(0.0).phase, "IDLE")
        self.assertTrue(controller.set_effect("03", "test", 1.0))
        before = controller.update(1.01)
        impact = controller.update(1.07)
        morph = controller.update(1.18)
        settle = controller.update(1.41)
        finished = controller.update(1.5)
        self.assertEqual([before.phase, impact.phase, morph.phase, settle.phase, finished.phase],
                         ["PRE_IMPACT", "SNAP_IMPACT", "MORPH", "SETTLE", "IDLE"])
        self.assertEqual(before.transition[0], 0.0)
        self.assertGreater(impact.layers[1], 0.0)
        self.assertLessEqual(impact.layers[1], 0.075)
        self.assertEqual(morph.typography, "SNAP!")
        self.assertEqual(finished.previous_effect, "03")
        self.assertEqual(finished.current_effect, "03")
        self.assertEqual(finished.transition[0], 1.0)

    def test_queue_one_releases_after_first_transition(self):
        controller = self.controller(transition_policy="queue-one", cooldown=0.0)
        self.assertTrue(controller.snap(0.0))
        self.assertTrue(controller.snap(0.1))
        self.assertFalse(controller.set_effect("06", "test", 0.2))
        self.assertEqual(controller.state.current_effect, "01")
        self.assertEqual(controller.state.pending_effect, "02")
        self.assertEqual(controller.update(0.49).current_effect, "02")
        self.assertEqual(controller.state.phase, "PRE_IMPACT")
        self.assertEqual(controller.state.snap_count, 2)
        self.assertIsNone(controller.state.pending_effect)

    def test_ignore_and_interrupt(self):
        controller = self.controller(transition_policy="ignore", cooldown=0.0)
        self.assertTrue(controller.snap(0.0))
        self.assertFalse(controller.snap(0.1))
        self.assertEqual(controller.state.current_effect, "01")
        controller.configure(transition_policy="interrupt")
        self.assertTrue(controller.snap(0.2))
        self.assertEqual(controller.update(0.2).current_effect, "02")
        self.assertEqual(controller.update(0.2).previous_effect, "01")
        self.assertEqual(controller.state.phase, "PRE_IMPACT")

    def test_configurable_duration_and_feedback_invalidation(self):
        controller = self.controller(transition_duration=1.1)
        generation = controller.state.feedback_reset
        self.assertTrue(controller.set_effect("10", "test", 0.0))
        self.assertGreater(controller.state.feedback_reset, generation)
        self.assertNotEqual(controller.update(0.7).phase, "IDLE")
        self.assertEqual(controller.update(1.11).phase, "IDLE")
        generation = controller.state.feedback_reset
        controller.set_source("VIDEO")
        self.assertGreater(controller.state.feedback_reset, generation)
        generation = controller.state.feedback_reset
        controller.reset(1.2)
        self.assertGreater(controller.state.feedback_reset, generation)
        self.assertEqual(controller.update(1.2).current_effect, "00")

    def test_showcase_uses_demo_and_runs_independently(self):
        controller = self.controller(source_mode="VIDEO")
        duration, cues = load_showcase(ROOT, self.registry, self.transitions)
        controller.start_showcase(duration, cues, 0.0)
        self.assertEqual(controller.state.source_mode, "DEMO")
        self.assertTrue(controller.showcase_playing)
        self.assertEqual(controller.update(2.6).current_effect, cues[0].effect_id)
        self.assertEqual(controller.update(70.0).current_effect, cues[-1].effect_id)
        controller.update(duration + 0.01)
        self.assertFalse(controller.showcase_playing)

    def test_performance_snaps_follow_cue_bundles(self):
        _, cues = load_showcase(ROOT, self.registry, self.transitions)
        controller = EffectController(self.registry, transitions=self.transitions, performance_cues=cues)
        controller.configure(playback_mode="PERFORMANCE")
        self.assertTrue(controller.snap(0.0))
        self.assertEqual(controller.update(0.17).typography, "POP!")
        self.assertTrue(controller.snap(0.7))
        self.assertEqual(controller.state.current_effect, "03")
