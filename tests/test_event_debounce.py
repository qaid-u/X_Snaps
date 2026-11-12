from pathlib import Path
import unittest

from td_scripts.effect_controller import EffectController
from td_scripts.fx_registry import load_registry
from td_scripts.osc_callbacks import OscReceiver, parse_message
from td_scripts.transition_library import load_transitions


ROOT = Path(__file__).resolve().parents[1]


class EventTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = load_registry(ROOT)
        cls.transitions = load_transitions(ROOT)

    def setUp(self):
        self.controller = EffectController(self.registry, transitions=self.transitions)
        self.receiver = OscReceiver(self.controller, max_event_age=1.5)

    def test_one_valid_event_advances_once_and_cooldown_consumes_id(self):
        first = 9_123_456_789
        self.assertTrue(self.receiver.handle("/snap/event", [first, 10.0, 0.92, "Right"], 10.01))
        self.assertEqual(self.controller.state.current_effect, "01")
        self.assertFalse(self.receiver.handle("/snap/event", [first + 1, 10.1, 0.92], 10.11))
        self.assertFalse(self.receiver.handle("/snap/event", [first, 10.0, 0.92], 10.72))
        self.assertFalse(self.receiver.handle("/snap/event", [first + 1, 10.1, 0.92], 10.72))
        self.assertTrue(self.receiver.handle("/snap/event", [first + 2, 10.71, 0.92], 10.73))
        self.assertEqual(self.controller.state.current_effect, "02")
        self.assertEqual(self.controller.state.snap_count, 2)

    def test_rejects_bad_confidence_stale_time_and_malformed_types(self):
        for arguments in ([True, 10.0, 0.9], [1, "NaN", 0.9], [1, 10.0, 1.2], [1, 10.0, 0.9, []],
                          [1, 10.0, 0.1], [2, 6.0, 0.9], [3, 12.0, 0.9], None):
            with self.subTest(arguments=arguments):
                self.assertFalse(self.receiver.handle("/snap/event", arguments, 10.0))
        self.assertEqual(self.controller.state.snap_count, 0)

    def test_heartbeat_expiration_and_no_hand_metrics(self):
        self.assertEqual(self.receiver.update(0.0), "KEYBOARD")
        self.assertFalse(self.receiver.handle("/snap/health", ["CAMERA_UNAVAILABLE", "device lost"], 0.0))
        self.assertFalse(self.receiver.handle("/snap/metrics", [-1.0, 0.0, "NO_HAND", 0.0, 0.0], 0.1))
        self.assertEqual(self.receiver.last_metrics.separation, -1.0)
        self.assertEqual(self.receiver.update(2.9), "CAMERA_UNAVAILABLE")
        self.assertEqual(self.receiver.update(3.1), "KEYBOARD")
        self.assertIsNone(self.receiver.last_metrics)
        self.assertTrue(self.controller.next(3.1))

    def test_disarmed_or_manual_only_accepts_explicit_selection(self):
        self.controller.configure(armed=False)
        self.assertFalse(self.receiver.handle("/snap/event", [1, 10.0, 0.9], 10.0))
        self.controller.configure(armed=True, playback_mode="MANUAL")
        self.assertFalse(self.receiver.handle("/snap/event", [2, 11.0, 0.9], 11.0))
        self.assertTrue(self.controller.next(11.0))

    def test_event_parser_supports_osc_int64_and_float64(self):
        event = parse_message("/snap/event", [921234567890, 32346.9353178186, 0.9, "Left"])
        self.assertEqual(event.event_id, 921234567890)
        self.assertEqual(event.timestamp, 32346.9353178186)
        self.assertEqual(event.hand, "Left")
