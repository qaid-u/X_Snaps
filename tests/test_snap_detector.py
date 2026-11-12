import importlib.util
from dataclasses import replace
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from gesture_service.audio_confirmation import AudioMatcher, AudioPulse, TransientDetector
from gesture_service.main import GestureWorker
from gesture_service.settings import GestureSettings
from gesture_service.snap_detector import HandSample, SnapCandidate, SnapDetector
from gesture_service.tracker import sample_from_landmarks


CONTACT = HandSample(
    "Right", 0.94, (0.5, 0.5, 0), 0.2,
    (0.3, 0.83, 0), (0.28, 0.83, 0), (0.3, 1.3, 0),
    (-0.1, 0.8, 0), (-0.3, 0.67, 0),
)
RELEASE = replace(CONTACT, middle=(0.0, 0.35, 0))


class SnapDetectorTests(unittest.TestCase):
    def setUp(self):
        self.detector = SnapDetector()

    def _contact(self, start=1.0):
        self.assertIsNone(self.detector.step(start, [CONTACT]))
        self.assertIsNone(self.detector.step(start + 0.034, [CONTACT]))
        self.assertEqual(self.detector.metrics.phase, "CONTACT")

    def test_emits_once_and_accepts_again_after_cooldown(self):
        self._contact()
        event = self.detector.step(1.067, [RELEASE])
        self.assertEqual(event.hand, "Right")
        self.assertGreater(event.confidence, 0.8)
        self.assertIsNone(self.detector.step(1.1, [RELEASE]))
        self.assertIsNone(self.detector.step(1.12, [CONTACT]))
        self.assertIsNone(self.detector.step(1.16, [RELEASE]))
        self._contact(2.0)
        self.assertIsNotNone(self.detector.step(2.067, [RELEASE]))

    def test_new_hand_cannot_complete_contact(self):
        self._contact()
        different = replace(RELEASE, label="Left")
        self.assertIsNone(self.detector.step(1.067, [different]))

    def test_same_handedness_but_different_wrist_cannot_complete_contact(self):
        self._contact()
        different = replace(RELEASE, wrist=(0.9, 0.7, 0))
        self.assertIsNone(self.detector.step(1.067, [different]))

    def test_single_missed_landmark_frame_can_reacquire_the_same_hand(self):
        self._contact()
        self.assertIsNone(self.detector.step(1.067, []))
        self.assertEqual(self.detector.metrics.phase, "TRACKING_GAP")
        self.assertIsNotNone(self.detector.step(1.100, [RELEASE]))

    def test_low_confidence_frame_can_reacquire_without_trusting_the_bad_sample(self):
        self._contact()
        low_confidence_release = replace(RELEASE, confidence=0.2)
        self.assertIsNone(self.detector.step(1.067, [low_confidence_release]))
        self.assertIsNotNone(self.detector.step(1.100, [RELEASE]))

    def test_reacquiring_a_different_hand_cannot_complete_contact(self):
        self._contact()
        self.assertIsNone(self.detector.step(1.067, []))
        self.assertIsNone(self.detector.step(1.100, [replace(RELEASE, wrist=(0.9, 0.5, 0))]))

    def test_long_gap_and_multiple_hands_invalidate_contact(self):
        interruptions = (([], []), ([CONTACT, replace(CONTACT, label="Left")],), ([],))
        for sequence, reacquire_at in zip(interruptions, (1.110, 1.085, 1.145)):
            with self.subTest(sequence=sequence, reacquire_at=reacquire_at):
                self.detector = SnapDetector()
                self._contact()
                for index, hands in enumerate(sequence):
                    self.assertIsNone(self.detector.step(1.061 + index * 0.025, hands))
                self.assertIsNone(self.detector.step(reacquire_at, [RELEASE]))

    def test_one_tight_contact_frame_and_palmward_release_at_30_fps(self):
        self.assertIsNone(self.detector.step(1.0, [CONTACT]))
        self.assertIsNotNone(self.detector.step(1.033, [RELEASE]))

    def test_one_loose_contact_frame_does_not_arm(self):
        loose = replace(CONTACT, middle=(0.08, 0.83, 0))
        self.assertIsNone(self.detector.step(1.0, [loose]))
        self.assertIsNone(self.detector.step(1.033, [RELEASE]))
        self.assertIn("Contact", self.detector.metrics.reason)

    def test_partly_bent_index_and_ring_comotion_are_supported(self):
        contact = replace(CONTACT, index=(0.55, 0.85, 0))
        release = replace(contact, middle=RELEASE.middle, ring=(-0.12, 0.32, 0))
        self.assertIsNone(self.detector.step(1.0, [contact]))
        self.assertIsNone(self.detector.step(1.017, [contact]))
        self.assertEqual(self.detector.metrics.phase, "CONTACT")
        self.assertIsNotNone(self.detector.step(1.034, [release]))

    def test_peak_release_speed_survives_a_slower_last_segment(self):
        self._contact()
        roll = replace(CONTACT, middle=(0.19, 0.49, 0))
        settle = replace(CONTACT, middle=(0.11, 0.42, 0))
        self.assertIsNone(self.detector.step(1.067, [roll]))
        self.assertEqual(self.detector.metrics.phase, "RELEASING")
        self.assertIsNotNone(self.detector.step(1.100, [settle]))

    def test_partial_roll_inside_contact_distance_preserves_pinch_reference(self):
        self._contact()
        roll = replace(CONTACT, middle=(0.23, 0.62, 0))
        release = replace(CONTACT, middle=(0.21, 0.37, 0))
        self.assertIsNone(self.detector.step(1.050, [roll]))
        self.assertEqual(self.detector.metrics.phase, "RELEASING")
        self.assertIsNotNone(self.detector.step(1.067, [release]))

    def test_unknown_handedness_can_keep_continuity_but_not_bridge_opposite_labels(self):
        self._contact()
        unknown_release = replace(RELEASE, label="Unknown")
        self.assertEqual(self.detector.step(1.067, [unknown_release]).hand, "Right")
        self.detector = SnapDetector()
        self._contact()
        roll = replace(CONTACT, label="Unknown", middle=(0.19, 0.49, 0))
        self.assertIsNone(self.detector.step(1.067, [roll]))
        self.assertIsNone(self.detector.step(1.100, [replace(RELEASE, label="Left")]))

    def test_delayed_or_nonmonotonic_frames_do_not_emit(self):
        self._contact()
        self.assertIsNone(self.detector.step(1.030, [RELEASE]))
        self.assertIsNone(self.detector.step(1.220, [RELEASE]))

    def test_waving_with_contact_does_not_emit(self):
        for frame in range(12):
            wrist = (0.5 + 0.11 * (-1) ** frame, 0.5, 0)
            self.assertIsNone(self.detector.step(1 + frame / 30, [replace(CONTACT, wrist=wrist)]))

    def test_closed_fist_and_hand_opening_do_not_emit(self):
        fist = replace(CONTACT, index=(0.2, 0.6, 0))
        for time, hand in [(1.0, fist), (1.034, fist), (1.067, RELEASE)]:
            self.assertIsNone(self.detector.step(time, [hand]))
        self._contact(2.0)
        opened = replace(RELEASE, middle=(0, 1.5, 0), ring=(0, 1.4, 0), pinky=(-0.3, 1.35, 0))
        self.assertIsNone(self.detector.step(2.067, [opened]))

    def test_slow_release_does_not_emit(self):
        self._contact()
        for time, mid in [(1.070, (0.25, 0.61, 0)), (1.108, (0.21, 0.51, 0)), (1.146, (0.17, 0.40, 0))]:
            self.assertIsNone(self.detector.step(time, [replace(CONTACT, middle=mid)]))

    def test_expired_contact_needs_open_pose_to_rearm(self):
        self._contact()
        for index in range(50):
            self.assertIsNone(self.detector.step(1.068 + index / 30, [CONTACT]))
        self.assertEqual(self.detector.metrics.phase, "WAIT_OPEN")
        self.assertIsNone(self.detector.step(2.75, [RELEASE]))
        self._contact(2.8)
        self.assertIsNotNone(self.detector.step(2.87, [RELEASE]))

    def test_unavailable_camera_keeps_worker_idle(self):
        tracker = Mock(capture=None)
        with patch("gesture_service.main.HandTracker", return_value=tracker):
            worker = GestureWorker("VISION", GestureSettings(), Path("unused"))
        try:
            first, second = worker.poll(), worker.poll()
            self.assertEqual(first.status, "CAMERA_UNAVAILABLE")
            self.assertEqual(second.events, [])
            tracker.open_camera.assert_called_once()
            tracker.read.assert_not_called()
        finally:
            worker.close()

    def test_microphone_permission_failure_falls_back_to_vision(self):
        tracker = Mock(capture=object())
        tracker.read.side_effect = [(1.0, [CONTACT]), (1.034, [CONTACT]), (1.067, [RELEASE])]
        with patch("gesture_service.main.HandTracker", return_value=tracker):
            with patch("gesture_service.main.Microphone", side_effect=OSError("permission denied")):
                worker = GestureWorker("AUDIO+VISION", GestureSettings(), Path("unused"))
        try:
            worker.poll()
            worker.poll()
            update = worker.poll()
            self.assertEqual(update.status, "VISION_LOW_CONFIDENCE")
            self.assertIn("permission denied", update.details)
            self.assertEqual(len(update.events), 1)
            self.assertLess(update.events[0].confidence, 0.8)
        finally:
            worker.close()

    def test_landmarks_use_palm_local_coordinates_and_visibility(self):
        points = [SimpleNamespace(x=0.5, y=0.5, z=0.0) for _ in range(21)]
        points[0].y = 0.7
        points[5].x = 0.58
        points[17].x = 0.42
        points[8].y = 0.4
        points[12].x = 0.51
        points[12].visibility = 0.8
        category = SimpleNamespace(category_name="Right", score=0.92)
        sample = sample_from_landmarks(points, category, 1.33)
        self.assertEqual(sample.confidence, 0.8)
        self.assertGreater(sample.index[1], 1)
        self.assertLess(sample.separation, 0.12)
        points[12].x = 1.1
        self.assertIsNone(sample_from_landmarks(points, category, 1.33))


class AudioTests(unittest.TestCase):
    def test_audio_alone_and_distant_audio_cannot_confirm(self):
        matcher = AudioMatcher(0.1)
        self.assertEqual(matcher.step(1.0, None, [AudioPulse(1.0, 1.0)]), [])
        candidate = SnapCandidate(1.25, 0.8, "Right")
        self.assertEqual(matcher.step(1.25, candidate, []), [])
        self.assertEqual(matcher.step(1.50, None, [AudioPulse(1.50, 0.9)]), [])

    def test_delayed_pulse_matches_only_one_candidate(self):
        matcher = AudioMatcher(0.1)
        candidate = SnapCandidate(2.0, 0.8, "Right")
        self.assertEqual(matcher.step(2.0, candidate, []), [])
        events = matcher.step(2.06, None, [AudioPulse(2.02, 1.0)])
        self.assertEqual(len(events), 1)
        self.assertGreater(events[0].confidence, candidate.confidence)
        self.assertEqual(matcher.step(2.08, replace(candidate, timestamp=2.04), []), [])

    @unittest.skipUnless(importlib.util.find_spec("numpy"), "NumPy is required for waveform fixtures")
    def test_transient_is_distinguished_from_sustained_loud_audio(self):
        import numpy as np

        detector = TransientDetector(0.035)
        rate = 48000
        silence = np.zeros(480)
        sustained = np.full(480, 0.4)
        self.assertIsNone(detector.step(silence, 1.0, rate))
        for index in range(10):
            self.assertIsNone(detector.step(sustained, 1.01 + index * 0.01, rate))
        self.assertIsNone(detector.step(silence, 1.20, rate))
        impulse = np.zeros(480)
        impulse[220:228] = [0.03, -0.25, 0.65, -0.51, 0.32, -0.25, 0.12, -0.06]
        self.assertIsNone(detector.step(impulse, 1.21, rate))
        pulse = detector.step(silence, 1.22, rate)
        self.assertAlmostEqual(pulse.timestamp, 1.21 + 222 / rate)


if __name__ == "__main__":
    unittest.main()
