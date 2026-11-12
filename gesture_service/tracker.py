"""Camera frames and MediaPipe landmark conversion, isolated from TouchDesigner."""

from collections import deque
from dataclasses import dataclass
from math import dist, hypot, isfinite
from pathlib import Path
import sys
from threading import Condition, Event, Thread
from time import monotonic

from .snap_detector import HandSample, Point


CAMERA_BACKENDS = ("auto", "dshow", "msmf", "any")
_CAMERA_QUEUE_SIZE = 3
_MAX_FRAME_AGE = 0.075
_FPS_WINDOW = 1.5
_PREVIEW_TITLE = "SNAP//REALITY Hand Tracking"
_FINGER_CHAINS = (
    (0, 1, 2, 3, 4), (0, 5, 6, 7, 8), (5, 9, 10, 11, 12),
    (9, 13, 14, 15, 16), (13, 17, 18, 19, 20), (17, 0),
)


def _subtract(a: Point, b: Point) -> Point:
    return tuple(x - y for x, y in zip(a, b))


def _dot(a: Point, b: Point) -> float:
    return sum(x * y for x, y in zip(a, b))


def _unit(point: Point) -> Point:
    length = hypot(*point)
    if length < 1e-6:
        raise ValueError("Degenerate palm axes")
    return tuple(value / length for value in point)


def _cross(a: Point, b: Point) -> Point:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def sample_from_landmarks(landmarks, category, aspect: float) -> HandSample | None:
    if len(landmarks) != 21:
        return None
    label = getattr(category, "category_name", None)
    if label not in {"Left", "Right"}:
        label = "Unknown"
    indices = (0, 4, 5, 8, 9, 12, 16, 17, 20)
    # Handedness is a separate classifier. The landmarker gates hand presence upstream.
    confidence = 1.0
    for index in indices:
        landmark = landmarks[index]
        if not all(value is not None and isfinite(value) for value in (landmark.x, landmark.y, landmark.z)):
            return None
        if not (0.015 <= landmark.x <= 0.985 and 0.015 <= landmark.y <= 0.985):
            return None
        for score in (getattr(landmark, "visibility", None), getattr(landmark, "presence", None)):
            if score is not None:
                confidence = min(confidence, score) if isfinite(score) else 0.0

    points = {
        index: (landmarks[index].x * aspect, landmarks[index].y, landmarks[index].z * aspect)
        for index in indices
    }
    wrist = points[0]
    palm_width = dist(points[5], points[17])
    palm_length = dist(wrist, points[9])
    scale = (palm_width + palm_length) / 2
    if not 0.035 <= scale <= 0.55:
        return None
    try:
        y_axis = _unit(_subtract(points[9], wrist))
        across = _subtract(points[5], points[17])
        x_axis = _unit(_subtract(across, tuple(_dot(across, y_axis) * value for value in y_axis)))
        z_axis = _cross(x_axis, y_axis)
    except ValueError:
        return None

    def palm_local(index):
        offset = _subtract(points[index], wrist)
        return tuple(_dot(offset, axis) / scale for axis in (x_axis, y_axis, z_axis))

    return HandSample(
        label, confidence, wrist, scale,
        *(palm_local(index) for index in (4, 12, 8, 16, 20)),
    )


@dataclass(frozen=True)
class CameraMetrics:
    backend: str
    width: int
    height: int
    reported_fps: float | None
    capture_fps: float | None
    tracking_fps: float | None
    latency_ms: float | None
    dropped_frames: int


def _rate(timestamps: deque, now: float) -> float | None:
    while timestamps and now - timestamps[0] > _FPS_WINDOW:
        timestamps.popleft()
    if len(timestamps) < 2 or timestamps[-1] - timestamps[0] < 0.25:
        return None
    return (len(timestamps) - 1) / (timestamps[-1] - timestamps[0])


def _backends(cv2, backend):
    if backend == "auto":
        names = ("dshow", "msmf", "any") if sys.platform == "win32" else ("any",)
    else:
        names = (backend,)
    for name in names:
        yield getattr(cv2, "CAP_" + name.upper())


class _CameraStream:
    """Own a single capture handle on its producer thread and bound inference lag."""

    def __init__(self, cv2, camera, size, fps, backend):
        self.cv2, self.camera, self.size, self.fps, self.backend = cv2, camera, size, fps, backend
        self._changed = Condition()
        self._stop = Event()
        self._frames = deque(maxlen=_CAMERA_QUEUE_SIZE)
        self._received = deque(maxlen=512)
        self._dropped = 0
        self._geometry = 0, 0
        self._reported_fps = None
        self._backend_name = ""
        self._error = ""
        self._done = False
        self._thread = Thread(target=self._produce, name="snap-camera", daemon=True)
        self._thread.start()

    def _configure(self, capture):
        cv2 = self.cv2
        # DirectShow restarts its capture graph on FPS changes. Request FourCC last.
        capture.set(cv2.CAP_PROP_FPS, self.fps)
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.size[0])
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.size[1])
        capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    def _connect(self):
        for backend in _backends(self.cv2, self.backend):
            for configure in (True, False):
                if self._stop.is_set():
                    return None
                capture = self.cv2.VideoCapture(self.camera, backend)
                connected = False
                try:
                    if not capture.isOpened():
                        break
                    if configure:
                        self._configure(capture)
                    ok, frame = capture.read()
                    timestamp = monotonic()
                    if ok and frame is not None and frame.size:
                        backend_name = capture.getBackendName()
                        reported = capture.get(self.cv2.CAP_PROP_FPS)
                        with self._changed:
                            self._backend_name = backend_name
                            self._reported_fps = reported if isfinite(reported) and reported > 0 else None
                        connected = True
                        return capture, timestamp, frame
                except self.cv2.error:
                    # Some drivers cannot apply a requested format. Try the native mode.
                    pass
                finally:
                    if not connected:
                        capture.release()
        return None

    def _publish(self, timestamp, frame):
        with self._changed:
            self._geometry = frame.shape[1], frame.shape[0]
            self._received.append(timestamp)
            if len(self._frames) == self._frames.maxlen:
                self._dropped += 1
            self._frames.append((timestamp, frame))
            self._changed.notify()

    def _produce(self):
        capture = None
        try:
            connection = self._connect()
            if connection is None:
                self._error = f"Camera {self.camera} busy, blocked or unavailable"
                return
            capture, timestamp, frame = connection
            self._publish(timestamp, frame)
            failures = 0
            while not self._stop.is_set():
                ok, frame = capture.read()
                timestamp = monotonic()
                if ok and frame is not None and frame.size:
                    self._publish(timestamp, frame)
                    failures = 0
                else:
                    failures += 1
                    if failures >= 3:
                        self._error = f"Camera {self.camera} stopped delivering frames"
                        break
                    self._stop.wait(0.025)
        except (self.cv2.error, OSError) as exc:
            self._error = f"Camera {self.camera}: {exc}"
        finally:
            if capture is not None:
                capture.release()
            with self._changed:
                self._done = True
                self._changed.notify_all()

    def read(self, timeout=0.4):
        deadline = monotonic() + timeout
        with self._changed:
            while not self._stop.is_set():
                now = monotonic()
                while self._frames and now - self._frames[0][0] > _MAX_FRAME_AGE:
                    self._frames.popleft()
                    self._dropped += 1
                if self._frames:
                    return self._frames.popleft()
                if self._done or now >= deadline:
                    break
                self._changed.wait(deadline - now)
        return None

    @property
    def finished(self):
        with self._changed:
            return self._done

    @property
    def status(self):
        with self._changed:
            if self._done:
                return self._error or f"Camera {self.camera} closed"
            if not self._backend_name:
                return f"Opening camera {self.camera}"
            return f"Waiting for camera {self.camera} frames"

    def metrics(self, tracking_fps, latency_ms):
        with self._changed:
            return CameraMetrics(
                self._backend_name, *self._geometry, self._reported_fps,
                _rate(self._received, monotonic()), tracking_fps, latency_ms, self._dropped,
            )

    def close(self):
        self._stop.set()
        with self._changed:
            self._changed.notify_all()
        # The producer releases the handle itself, even when an in-flight native read
        # runs longer than this wait. The caller must not open another owner meanwhile.
        self._thread.join(0.8)
        return not self._thread.is_alive()


class HandTracker:
    def __init__(
        self, model: Path, camera: int, width: int = 640, height: int = 480, fps: int = 60,
        *, backend: str = "auto", preview: bool = False, max_hands: int = 1,
    ):
        if backend not in CAMERA_BACKENDS:
            raise ValueError(f"Unsupported camera backend: {backend}")
        if min(width, height, fps) <= 0:
            raise ValueError("Camera width, height and FPS must be positive")
        if max_hands not in (1, 2):
            raise ValueError("Track one hand for speed or two hands for ambiguity rejection")
        if not model.is_file():
            raise FileNotFoundError(f"Hand Landmarker model missing: {model}. Run scripts/setup_windows.ps1.")
        import cv2
        import mediapipe as mp

        self.cv2 = cv2
        self.mp = mp
        self.camera_index = camera
        self.camera_size = (width, height)
        self.fps = fps
        self.backend = backend
        self.capture = None
        self.last_frame_ms = -1
        self.tracking_status = "CAMERA_UNAVAILABLE"
        self._camera_message = f"Camera {camera} closed"
        self._processed = deque(maxlen=512)
        self._latency_ms = None
        self._preview = preview
        self._preview_image = None
        self._preview_hands = ()
        self._preview_open = False
        options = mp.tasks.vision.HandLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(model)),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            # MediaPipe can skip full palm detection once it tracks all configured hands.
            num_hands=max_hands,
            min_hand_detection_confidence=0.55,
            min_hand_presence_confidence=0.55,
            min_tracking_confidence=0.55,
        )
        self.landmarker = mp.tasks.vision.HandLandmarker.create_from_options(options)

    def open_camera(self) -> bool:
        self.release_camera()
        if self.capture is not None:
            return False
        self._processed.clear()
        self._latency_ms = None
        self.tracking_status = "CAMERA_OPENING"
        self.capture = _CameraStream(self.cv2, self.camera_index, self.camera_size, self.fps, self.backend)
        return True

    @property
    def camera_metrics(self) -> CameraMetrics:
        if self.capture is None:
            return CameraMetrics("", 0, 0, None, None, None, None, 0)
        return self.capture.metrics(_rate(self._processed, monotonic()), self._latency_ms)

    @property
    def camera_status(self) -> str:
        if self.capture is None:
            return self._camera_message
        if self.tracking_status in {"CAMERA_OPENING", "CAMERA_WAITING"}:
            return self.capture.status
        metrics = self.camera_metrics
        speed = f"{metrics.capture_fps:.1f}" if metrics.capture_fps is not None else "--"
        tracking = f"{metrics.tracking_fps:.1f}" if metrics.tracking_fps is not None else "--"
        latency = f" {metrics.latency_ms:.0f}ms" if metrics.latency_ms is not None else ""
        return f"{metrics.backend} {metrics.width}x{metrics.height} {speed} cam/{tracking} tracking FPS{latency}"

    def read(self) -> tuple[float, list[HandSample], bool] | None:
        capture = self.capture
        packet = capture.read() if capture is not None else None
        if packet is None:
            self._preview_image = None
            self._preview_hands = ()
            if capture is None or capture.finished:
                if capture is not None:
                    self._camera_message = capture.status
                    self.release_camera()
                self.tracking_status = "CAMERA_UNAVAILABLE"
            else:
                self.tracking_status = "CAMERA_WAITING"
            return None
        timestamp, frame = packet
        frame_ms = max(int(timestamp * 1000), self.last_frame_ms + 1)
        self.last_frame_ms = frame_ms
        limit = max(self.camera_size)
        largest = max(frame.shape[:2])
        if largest > limit:
            scale = limit / largest
            width, height = frame.shape[1], frame.shape[0]
            frame = self.cv2.resize(
                frame, (max(1, round(width * scale)), max(1, round(height * scale))),
                interpolation=self.cv2.INTER_AREA,
            )
        rgb = self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2RGB)
        image = self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=rgb)
        result = self.landmarker.detect_for_video(image, frame_ms)
        finished = monotonic()
        self._processed.append(finished)
        self._latency_ms = (finished - timestamp) * 1000
        if self._preview:
            self._preview_image = frame
            self._preview_hands = result.hand_landmarks
        # Two hands are ambiguous for a single snap detector, even if one fails quality checks.
        if len(result.hand_landmarks) != 1:
            multiple = len(result.hand_landmarks) > 1
            self.tracking_status = "TWO_HANDS" if multiple else "NO_HAND"
            return timestamp, [], multiple
        category = result.handedness[0][0] if result.handedness and result.handedness[0] else None
        sample = sample_from_landmarks(
            result.hand_landmarks[0], category, frame.shape[1] / frame.shape[0],
        )
        self.tracking_status = "HAND_TRACKED" if sample is not None else "UNUSABLE_LANDMARKS"
        return timestamp, [sample] if sample is not None else [], False

    def show_preview(self, lines=()) -> bool:
        if not self._preview:
            return True
        cv2 = self.cv2
        try:
            if self._preview_open and cv2.getWindowProperty(_PREVIEW_TITLE, cv2.WND_PROP_VISIBLE) < 1:
                self._preview_open = False
                return False
            if self._preview_image is None:
                from numpy import zeros
                image = zeros((320, 640, 3), dtype="uint8")
            else:
                image = self._preview_image.copy()
            height, width = image.shape[:2]
            for hand in self._preview_hands:
                points = [
                    (round(landmark.x * (width - 1)), round(landmark.y * (height - 1)))
                    if landmark.x is not None and landmark.y is not None
                    and isfinite(landmark.x) and isfinite(landmark.y)
                    and 0 <= landmark.x <= 1 and 0 <= landmark.y <= 1 else None
                    for landmark in hand
                ]
                if len(points) != 21:
                    continue
                for chain in _FINGER_CHAINS:
                    for start, end in zip(chain, chain[1:]):
                        if points[start] is not None and points[end] is not None:
                            cv2.line(image, points[start], points[end], (80, 240, 140), 2, cv2.LINE_AA)
                for index, color in ((4, (255, 215, 55)), (12, (220, 50, 255))):
                    if points[index] is not None:
                        cv2.circle(image, points[index], 5, color, -1, cv2.LINE_AA)
            text = (self.camera_status, self.tracking_status.replace("_", " "), *lines, "Esc or Q to close")
            for row, value in enumerate(text, 1):
                location = (9, 19 * row)
                cv2.putText(image, str(value), location, cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 0, 0), 3, cv2.LINE_AA)
                cv2.putText(image, str(value), location, cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.imshow(_PREVIEW_TITLE, image)
            self._preview_open = True
            return cv2.pollKey() & 0xFF not in (27, ord("q"), ord("Q"))
        except cv2.error as exc:
            if self._preview_open:
                self._preview_open = False
                return False
            raise RuntimeError(f"Camera preview could not open: {exc}") from exc

    def release_camera(self):
        if self.capture is not None and self.capture.close():
            self.capture = None

    def close(self):
        try:
            self.release_camera()
            if self._preview_open:
                self.cv2.destroyWindow(_PREVIEW_TITLE)
        finally:
            self.landmarker.close()
