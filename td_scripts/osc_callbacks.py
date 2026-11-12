"""Parse localhost OSC messages and deliver fresh snap events to the controller."""

from dataclasses import dataclass
import math
import time


@dataclass(frozen=True)
class SnapEvent:
    event_id: int
    timestamp: float
    confidence: float
    hand: str = ""
    session: str = ""


@dataclass(frozen=True)
class TrackerHealth:
    status: str
    detail: str = ""
    session: str = ""


@dataclass(frozen=True)
class TrackerMetrics:
    separation: float
    velocity: float
    phase: str
    audio_transient: float
    confidence: float


def _number(value, *, numeric_string=False):
    if type(value) not in (int, float) and not (numeric_string and isinstance(value, str) and len(value) <= 32):
        raise ValueError("Expected OSC number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Expected finite OSC number")
    return number


def _text(value, limit=80):
    if not isinstance(value, str) or len(value) > limit or not value.isprintable() and value != "":
        raise ValueError("Invalid OSC text field")
    return value


def _unit(value):
    value = _number(value)
    if not 0.0 <= value <= 1.0:
        raise ValueError("Expected normalized OSC number")
    return value


def parse_message(address, args):
    if not isinstance(args, (list, tuple)):
        raise ValueError("Expected OSC argument list")
    if address == "/snap/event" and 3 <= len(args) <= 5:
        event_id = args[0]
        if type(event_id) is not int or not 1 <= event_id <= 9_223_372_036_854_775_807:
            raise ValueError("Invalid OSC event ID")
        timestamp = _number(args[1], numeric_string=True)
        if timestamp < 0.0:
            raise ValueError("Invalid monotonic timestamp")
        hand = _text(args[3], 32) if len(args) >= 4 else ""
        session = _text(args[4], 64) if len(args) >= 5 else ""
        return SnapEvent(event_id, timestamp, _unit(args[2]), hand, session)
    if address == "/snap/health" and 1 <= len(args) <= 3:
        status = _text(args[0], 32)
        if not status:
            raise ValueError("Missing OSC tracker status")
        detail = _text(args[1], 120) if len(args) >= 2 else ""
        session = _text(args[2], 64) if len(args) >= 3 else ""
        return TrackerHealth(status, detail, session)
    if address == "/snap/metrics" and len(args) == 5:
        separation, velocity = map(_number, args[:2])
        transient = _unit(args[3])
        if separation < 0.0 and separation != -1.0:
            raise ValueError("Invalid negative separation")
        return TrackerMetrics(separation, velocity, _text(args[2], 24), transient, _unit(args[4]))
    raise ValueError(f"Unexpected OSC address or field count: {address!r}")


class OscReceiver:
    def __init__(self, controller, *, heartbeat_timeout=3.0, min_confidence=0.20, max_event_age=None, clock=time.monotonic):
        self.controller = controller
        self.heartbeat_timeout = heartbeat_timeout
        self.min_confidence = min_confidence
        self.max_event_age = max_event_age
        self.clock = clock
        self.last_health = None
        self.last_metrics = None
        self.last_seen = None
        self.last_event = None
        self.last_error = ""
        self._session = ""
        self._retired_sessions = []
        self._last_event_id = 0
        self._last_timestamp = float("-inf")

    def _set_session(self, session):
        if not session or session == self._session:
            return True
        if session in self._retired_sessions:
            return False
        if self._session:
            self._retired_sessions.append(self._session)
            self._retired_sessions = self._retired_sessions[-16:]
        self._session = session
        self._last_event_id = 0
        self._last_timestamp = float("-inf")
        return True

    def handle(self, address, args, now=None):
        """Return True when a validated event was accepted by the controller."""
        now = self.clock() if now is None else now
        try:
            message = parse_message(address, args)
        except (ValueError, OverflowError) as exc:
            self.last_error = str(exc)
            return False
        if isinstance(message, TrackerHealth):
            if self._set_session(message.session):
                self.last_health = message
                self.last_seen = now
                self.update(now)
            return False
        if isinstance(message, TrackerMetrics):
            self.last_metrics = message
            return False
        if self.max_event_age is not None and not -0.5 <= now - message.timestamp <= self.max_event_age:
            return False
        if not self._set_session(message.session):
            return False
        if message.event_id <= self._last_event_id or message.timestamp < self._last_timestamp:
            return False
        self._last_event_id = message.event_id
        self._last_timestamp = message.timestamp
        self.last_event = message
        if message.confidence < self.min_confidence:
            return False
        return self.controller.snap(now)

    def update(self, now=None):
        now = self.clock() if now is None else now
        if self.last_seen is None or now - self.last_seen > self.heartbeat_timeout:
            self.controller.state.tracker_health = "KEYBOARD"
            self.last_metrics = None
        else:
            self.controller.state.tracker_health = self.last_health.status
        return self.controller.state.tracker_health
