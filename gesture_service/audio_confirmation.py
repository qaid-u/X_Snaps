"""Transient detection and one-to-one matching with landmark candidates."""

from collections import deque
from dataclasses import dataclass
from time import monotonic

from .snap_detector import SnapCandidate


@dataclass(frozen=True)
class AudioPulse:
    timestamp: float
    score: float


class TransientDetector:
    def __init__(self, threshold: float):
        if not 0.003 <= threshold <= 0.95:
            raise ValueError("Microphone threshold must be between 0.003 and 0.95")
        self.threshold = threshold
        self.floor = 0.003
        self.previous_rms = 0.003
        self.previous_sample = 0.0
        self.pending = None
        self.last_pulse = float("-inf")

    def step(self, samples, timestamp: float, rate: float) -> AudioPulse | None:
        import numpy as np

        peak_index = int(np.argmax(np.abs(samples)))
        peak = float(abs(samples[peak_index]))
        rms = float(np.sqrt(np.mean(samples * samples)))
        diff = np.diff(samples, prepend=self.previous_sample)
        high_ratio = float(np.sqrt(np.mean(diff * diff))) / max(rms, 1e-6)
        crest = peak / max(rms, 1e-6)
        pulse = None
        if self.pending is not None:
            onset, onset_rms = self.pending
            elapsed = timestamp - onset.timestamp
            if elapsed <= 0.065 and rms < onset_rms * 0.46:
                pulse, self.pending, self.last_pulse = onset, None, onset.timestamp
            elif elapsed > 0.065:
                self.pending = None
        if (
            pulse is None and self.pending is None and timestamp - self.last_pulse > 0.14
            and peak >= self.threshold and rms >= max(self.floor * 3.2, self.previous_rms * 2.2)
            and crest >= 2.3 and high_ratio >= 0.68
        ):
            score = min(1.0, 0.42 + crest * 0.055 + high_ratio * 0.12)
            self.pending = (AudioPulse(timestamp + peak_index / rate, score), rms)
        self.floor = self.floor * 0.985 + min(rms, self.floor * 2.0) * 0.015
        self.previous_rms = rms
        self.previous_sample = float(samples[-1])
        return pulse


class Microphone:
    def __init__(self, device: int | None, threshold: float):
        import sounddevice as sd

        self.detector = TransientDetector(threshold)
        self.pulses = deque(maxlen=32)
        self.last_callback = monotonic()
        self.callback_seen = False
        device_info = sd.query_devices(device, "input")
        self.rate = float(device_info["default_samplerate"])
        self.stream = sd.InputStream(
            device=device, channels=1, samplerate=self.rate, blocksize=round(self.rate * 0.01),
            dtype="float32", callback=self._callback,
        )
        try:
            self.stream.start()
        except Exception:
            self.stream.close()
            raise

    def _callback(self, audio, _frames, clock, status):
        self.last_callback = now = monotonic()
        self.callback_seen = True
        if status.input_overflow:
            self.detector.pending = None
            return
        timestamp = now - max(0.0, clock.currentTime - clock.inputBufferAdcTime)
        pulse = self.detector.step(audio[:, 0], timestamp, self.rate)
        if pulse is not None:
            self.pulses.append(pulse)

    @property
    def working(self) -> bool:
        return self.callback_seen and monotonic() - self.last_callback < 1.5

    def drain(self) -> list[AudioPulse]:
        pulses = []
        while self.pulses:
            pulses.append(self.pulses.popleft())
        return pulses

    def close(self) -> None:
        self.stream.close()


class AudioMatcher:
    def __init__(self, window: float):
        if not 0.02 <= window <= 0.35:
            raise ValueError("Audio sync window must be between 20 and 350 ms")
        self.window = window
        self.candidates: list[SnapCandidate] = []
        self.pulses: list[AudioPulse] = []

    def clear(self):
        self.candidates.clear()
        self.pulses.clear()

    def step(self, now: float, candidate: SnapCandidate | None, pulses: list[AudioPulse]) -> list[SnapCandidate]:
        self.pulses.extend(pulses)
        if candidate is not None:
            self.candidates.append(candidate)
        results = []
        waiting = []
        for item in self.candidates:
            nearby = [pulse for pulse in self.pulses if abs(pulse.timestamp - item.timestamp) <= self.window]
            if nearby:
                match = min(nearby, key=lambda pulse: abs(pulse.timestamp - item.timestamp))
                self.pulses.remove(match)
                results.append(SnapCandidate(item.timestamp, item.confidence * 0.8 + match.score * 0.2, item.hand))
            elif now - item.timestamp <= self.window + 0.07:
                waiting.append(item)
        self.candidates = waiting
        self.pulses = [pulse for pulse in self.pulses if now - pulse.timestamp <= self.window + 0.12]
        return results
