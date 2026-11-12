"""Camera-independent temporal detection of thumb–middle-finger releases."""

from dataclasses import dataclass, field
from math import dist, hypot, isfinite

Point = tuple[float, float, float]


@dataclass(frozen=True)
class DetectorSettings:
    contact_distance: float = 0.24
    release_distance: float = 0.44
    contact_hold: float = 0.025
    release_window: float = 0.12
    contact_timeout: float = 1.25
    frame_gap: float = 0.13
    min_velocity: float = 3.8
    min_displacement: float = 0.28
    min_confidence: float = 0.62
    cooldown: float = 0.65

    def __post_init__(self):
        if not (0.05 <= self.contact_distance < self.release_distance <= 1.5):
            raise ValueError("Require 0.05 <= contact_distance < release_distance <= 1.5")
        if not (0 < self.contact_hold < self.contact_timeout <= 4):
            raise ValueError("Contact timing is out of range")
        if not (0 < self.release_window <= self.frame_gap <= 0.3):
            raise ValueError("Release timing is out of range")
        if not (0 < self.min_velocity <= 50 and 0 < self.min_displacement <= 2):
            raise ValueError("Motion thresholds are out of range")
        if not (0 < self.min_confidence <= 1 and 0.5 <= self.cooldown <= 1.5):
            raise ValueError("Confidence or cooldown is out of range")


@dataclass(frozen=True)
class HandSample:
    label: str
    confidence: float
    wrist: Point
    scale: float
    thumb: Point
    middle: Point
    index: Point
    ring: Point
    pinky: Point

    @property
    def separation(self) -> float:
        return dist(self.thumb, self.middle)

    def same_hand(self, previous: "HandSample") -> bool:
        unknown = {"", "Unknown"}
        return (
            (self.label == previous.label or self.label in unknown or previous.label in unknown)
            and previous.scale > 0
            and 0.65 <= self.scale / previous.scale <= 1.55
            and dist(self.wrist, previous.wrist) < min(self.scale, previous.scale) * 0.9
        )


@dataclass(frozen=True)
class SnapCandidate:
    timestamp: float
    confidence: float
    hand: str


@dataclass(frozen=True)
class Metrics:
    separation: float = -1.0
    velocity: float = 0.0
    phase: str = "NO_HAND"
    confidence: float = 0.0
    reason: str = ""


@dataclass
class SnapDetector:
    settings: DetectorSettings = field(default_factory=DetectorSettings)
    metrics: Metrics = field(init=False, default_factory=Metrics)
    _previous: HandSample | None = field(init=False, default=None)
    _contact: HandSample | None = field(init=False, default=None)
    _previous_time: float = field(init=False, default=float("-inf"))
    _last_step: float = field(init=False, default=float("-inf"))
    _last_contact: float = field(init=False, default=float("-inf"))
    _contact_start: float = field(init=False, default=float("-inf"))
    _contact_count: int = field(init=False, default=0)
    _release_speed: float = field(init=False, default=0.0)
    _missing_frames: int = field(init=False, default=0)
    _candidate_time: float = field(init=False, default=float("-inf"))
    _require_open: bool = field(init=False, default=False)

    def _clear_contact(self) -> None:
        self._contact = None
        self._contact_start = float("-inf")
        self._last_contact = float("-inf")
        self._contact_count = 0
        self._release_speed = 0.0

    def clear_tracking(self) -> None:
        """Drop incomplete evidence across camera and tracking interruptions."""
        self._clear_contact()
        self._previous = None
        self._previous_time = float("-inf")
        self._missing_frames = 0
        self._require_open = False
        self.metrics = Metrics()

    def step(self, timestamp: float, hands: list[HandSample], multiple_hands: bool = False) -> SnapCandidate | None:
        settings = self.settings
        if not isfinite(timestamp) or timestamp <= self._last_step:
            return None
        self._last_step = timestamp
        if multiple_hands or len(hands) > 1:
            self.clear_tracking()
            self.metrics = Metrics(phase="MULTIPLE_HANDS")
            return None
        if not hands or not settings.min_confidence <= hands[0].confidence <= 1.0:
            self._missing_frames += 1
            if self._contact and self._missing_frames == 1 and timestamp - self._previous_time <= settings.frame_gap:
                # Preserve one ambiguous observation, then require geometric reacquisition.
                self.metrics = Metrics(phase="TRACKING_GAP", reason="Brief hand landmark loss")
            else:
                self.clear_tracking()
                if hands:
                    self.metrics = Metrics(phase="LOW_CONFIDENCE")
            return None

        hand = hands[0]
        separation = hand.separation
        velocity = 0.0
        interval = timestamp - self._previous_time
        reason = ""
        if self._previous is not None:
            gap_limit = min(settings.frame_gap, 0.10) if self._missing_frames else settings.frame_gap
            if interval > gap_limit or not hand.same_hand(self._previous):
                self.clear_tracking()
                reason = "Hand changed or tracking gap was too long"
            else:
                velocity = (separation - self._previous.separation) / interval
        self._missing_frames = 0
        self._previous, self._previous_time = hand, timestamp

        candidate = None
        contact_limit = settings.contact_distance
        if self._contact:
            # Keep the firmly observed contact as the reference when a fingertip
            # has already started rolling away, even before it clears the arm limit.
            contact_limit = min(contact_limit, max(contact_limit * 0.80, self._contact.separation + 0.06))
        if timestamp - self._candidate_time < settings.cooldown:
            phase = "COOLDOWN"
        elif self._require_open:
            phase = "WAIT_OPEN"
            if separation >= settings.release_distance:
                self._require_open = False
        elif separation <= contact_limit and self._contact_pose(hand):
            if self._contact is None:
                self._contact_start = timestamp
            if timestamp - self._contact_start > settings.contact_timeout:
                self._clear_contact()
                self._require_open = True
                phase = "WAIT_OPEN"
            else:
                self._last_contact, self._contact = timestamp, hand
                self._contact_count += 1
                self._release_speed = 0.0
                phase = "CONTACT"
        elif self._contact is None:
            if separation <= settings.contact_distance:
                phase, reason = "CONTACT_POSE", "Show the thumb and middle-finger contact with the index clear"
            else:
                phase = "READY"
        elif timestamp - self._last_contact > settings.release_window:
            self._clear_contact()
            phase, reason = "READY", "Release took too long after contact"
        else:
            speed = (separation - self._contact.separation) / (timestamp - self._last_contact)
            self._release_speed = max(self._release_speed, velocity, speed)
            if separation < settings.release_distance:
                phase = "RELEASING"
            else:
                candidate, reason = self._validate_release(timestamp, hand)
                self._clear_contact()
                phase = "CANDIDATE" if candidate else "REJECTED"
                if candidate:
                    self._candidate_time = timestamp

        confidence = candidate.confidence if candidate else hand.confidence
        self.metrics = Metrics(separation, velocity, phase, confidence, reason)
        return candidate

    @staticmethod
    def _contact_pose(hand: HandSample) -> bool:
        # An extended or partly bent index is fine as long as it stays clear of the pinch.
        index_clearance = dist(hand.thumb, hand.index)
        return (
            hand.middle[1] >= 0.30
            and hand.index[1] >= min(0.95, hand.middle[1] - 0.12)
            and index_clearance >= max(0.16, hand.separation + 0.10)
        )

    def _validate_release(self, timestamp: float, hand: HandSample) -> tuple[SnapCandidate | None, str]:
        contact = self._contact
        settings = self.settings
        movement = dist(contact.middle, hand.middle)
        velocity = self._release_speed
        if not hand.same_hand(contact):
            return None, "Different hand at release"
        if velocity < settings.min_velocity or movement < settings.min_displacement:
            return None, "Middle finger release was too slow or small"
        release_age = timestamp - self._last_contact
        average_speed = (hand.separation - contact.separation) / release_age
        if release_age > 0.075 and average_speed < settings.min_velocity * 1.10:
            return None, "Middle finger release was too drawn out"

        elapsed = self._last_contact - self._contact_start
        # Sample quantization shortens the observed hold. A single tight observation is
        # usable if the following motion is stronger than the normal release threshold.
        timing_slack = min(release_age, settings.contact_hold * 0.5)
        sustained = self._contact_count >= 2 and elapsed + timing_slack >= settings.contact_hold
        strong_single = (
            contact.separation <= settings.contact_distance * 0.80
            and velocity >= settings.min_velocity * 1.25
            and movement >= settings.min_displacement * 1.15
        )
        if not sustained and not strong_single:
            return None, "Contact was too brief or loose"

        palmward = contact.middle[1] - hand.middle[1]
        toward_wrist = hypot(*contact.middle) - hypot(*hand.middle)
        if palmward < 0.06 and (palmward < -0.04 or toward_wrist < 0.10):
            return None, "Middle finger opened away from the palm"
        other_motion = max(dist(contact.index, hand.index), dist(contact.pinky, hand.pinky))
        ring_motion = dist(contact.ring, hand.ring)
        thumb_motion = dist(contact.thumb, hand.thumb)
        if movement < max(other_motion * 1.10, ring_motion * 0.86, thumb_motion * 0.95):
            return None, "Finger motion did not isolate the middle finger"

        velocity_score = min(velocity / (settings.min_velocity * 1.8), 1.0)
        movement_score = min(movement / (settings.min_displacement * 1.65), 1.0)
        confidence = min(contact.confidence, hand.confidence) * (
            0.65 + 0.2 * velocity_score + 0.15 * movement_score
        )
        label = contact.label if hand.label in {"", "Unknown"} else hand.label
        return SnapCandidate(timestamp, confidence, label), ""
