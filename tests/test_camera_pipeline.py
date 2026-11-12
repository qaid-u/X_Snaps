from collections import deque
from pathlib import Path
import sys
from threading import Event, get_ident
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from gesture_service.tracker import HandTracker, _CameraStream, _rate, sample_from_landmarks


class FakeCamera:
    def __init__(self, frames=(), opened=True):
        self.frames = deque(frames)
        self.opened = opened
        self.settings = []
        self.waiting = Event()
        self.disconnect = Event()
        self.open_thread = None
        self.close_thread = None

    def isOpened(self):
        self.open_thread = get_ident()
        return self.opened

    def set(self, key, value):
        self.settings.append((key, value))
        return True

    def get(self, key):
        return 59.94

    def getBackendName(self):
        return "DSHOW"

    def read(self):
        if self.frames:
            return True, self.frames.popleft()
        self.waiting.set()
        self.disconnect.wait(0.7)
        return False, None

    def release(self):
        self.close_thread = get_ident()


def fake_frame(index=0, width=640, height=480):
    return SimpleNamespace(index=index, shape=(height, width, 3), size=width * height * 3)


def fake_cv2(*cameras):
    return SimpleNamespace(
        CAP_DSHOW=700, CAP_MSMF=1400, CAP_ANY=0,
        CAP_PROP_FPS=5, CAP_PROP_FRAME_WIDTH=3, CAP_PROP_FRAME_HEIGHT=4,
        CAP_PROP_FOURCC=6, CAP_PROP_BUFFERSIZE=38, COLOR_BGR2RGB=4, INTER_AREA=3,
        VideoWriter_fourcc=Mock(return_value=1196444237),
        VideoCapture=Mock(side_effect=cameras),
        cvtColor=Mock(side_effect=lambda frame, code: frame),
        resize=Mock(side_effect=lambda frame, size, interpolation: fake_frame(width=size[0], height=size[1])),
        error=RuntimeError,
    )


def fake_landmarks():
    points = [SimpleNamespace(x=0.5, y=0.5, z=0.0) for _ in range(21)]
    points[0].y = 0.7
    points[5].x = 0.58
    points[17].x = 0.42
    return points


class CameraPipelineTests(unittest.TestCase):
    def test_capture_negotiation_and_bounded_queue(self):
        camera = FakeCamera([fake_frame(index) for index in range(7)])
        cv2 = fake_cv2(camera)
        with patch("gesture_service.tracker._MAX_FRAME_AGE", 5):
            stream = _CameraStream(cv2, 0, (640, 480), 60, "dshow")
            try:
                self.assertTrue(camera.waiting.wait(1))
                items = [stream.read(0) for _ in range(3)]
                self.assertEqual([frame.index for _, frame in items], [4, 5, 6])
                self.assertEqual(sorted(stamp for stamp, _ in items), [stamp for stamp, _ in items])
                self.assertEqual(stream.metrics(None, None).dropped_frames, 4)
                self.assertEqual(stream.metrics(None, None).reported_fps, 59.94)
                self.assertEqual(camera.settings, [(5, 60), (3, 640), (4, 480), (6, 1196444237), (38, 1)])
            finally:
                camera.disconnect.set()
                self.assertTrue(stream.close())
        self.assertEqual(camera.open_thread, camera.close_thread)
        self.assertNotEqual(camera.close_thread, get_ident())

    def test_windows_auto_falls_back_to_another_backend(self):
        unopened = FakeCamera(opened=False)
        camera = FakeCamera([fake_frame()])
        cv2 = fake_cv2(unopened, camera)
        with patch("gesture_service.tracker.sys.platform", "win32"):
            stream = _CameraStream(cv2, 1, (640, 480), 60, "auto")
            try:
                self.assertIsNotNone(stream.read(timeout=1))
                self.assertIsNotNone(unopened.close_thread)
                self.assertEqual([call.args for call in cv2.VideoCapture.call_args_list], [(1, 700), (1, 1400)])
            finally:
                camera.disconnect.set()
                self.assertTrue(stream.close())

    def test_reported_fps_uses_recent_capture_time_window(self):
        samples = deque([1.0, 3.00, 3.10, 3.20, 3.30, 3.40])
        self.assertAlmostEqual(_rate(samples, 3.40), 10)
        self.assertIsNone(_rate(samples, 5.0))

    def test_capture_timestamp_is_forwarded_and_large_frames_are_downscaled(self):
        cv2 = fake_cv2()
        landmarker = Mock()
        landmarker.detect_for_video.return_value = SimpleNamespace(hand_landmarks=[fake_landmarks()], handedness=[])
        options = Mock()
        mp = SimpleNamespace(
            tasks=SimpleNamespace(
                BaseOptions=Mock(),
                vision=SimpleNamespace(
                    HandLandmarkerOptions=options,
                    HandLandmarker=SimpleNamespace(create_from_options=Mock(return_value=landmarker)),
                    RunningMode=SimpleNamespace(VIDEO="VIDEO"),
                ),
            ),
            Image=Mock(),
            ImageFormat=SimpleNamespace(SRGB="SRGB"),
        )
        with patch.dict(sys.modules, {"cv2": cv2, "mediapipe": mp}):
            tracker = HandTracker(Path(__file__), 0)
        tracker.capture = Mock()
        tracker.capture.read.return_value = (10.020, fake_frame(width=1920, height=1080))
        tracker.capture.close.return_value = True
        with patch("gesture_service.tracker.monotonic", return_value=10.045):
            timestamp, samples, ambiguous = tracker.read()
        self.assertEqual(timestamp, 10.020)
        self.assertEqual(options.call_args.kwargs["num_hands"], 1)
        self.assertEqual(landmarker.detect_for_video.call_args.args[1], 10020)
        self.assertEqual(cv2.resize.call_args.args[1], (640, 360))
        self.assertEqual(samples[0].label, "Unknown")
        self.assertFalse(ambiguous)
        self.assertEqual(tracker.tracking_status, "HAND_TRACKED")
        self.assertAlmostEqual(tracker._latency_ms, 25)
        tracker.close()

    def test_handedness_score_does_not_gate_detected_landmarks(self):
        low_handedness = SimpleNamespace(category_name="Left", score=0.52)
        sample = sample_from_landmarks(fake_landmarks(), low_handedness, 4 / 3)
        self.assertEqual(sample.confidence, 1.0)
        self.assertEqual(sample.label, "Left")


if __name__ == "__main__":
    unittest.main()
