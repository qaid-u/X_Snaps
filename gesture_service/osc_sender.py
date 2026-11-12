"""Send small typed OSC messages to TouchDesigner on the loopback interface."""

import socket
import struct
from time import monotonic_ns

from .snap_detector import Metrics, SnapCandidate

HOST = "127.0.0.1"
PORT = 7400
_NUMERIC_TAGS = {"h": ">q", "d": ">d", "f": ">f"}


def _osc_string(value: str) -> bytes:
    data = value.encode("utf-8")
    return data + b"\0" * (4 - len(data) % 4)


def _pack_message(address, typed_values) -> bytes:
    # Keep the keyboard and loopback tester available before the camera dependencies are installed.
    arguments = (
        _osc_string(value) if tag == "s" else struct.pack(_NUMERIC_TAGS[tag], value)
        for value, tag in typed_values
    )
    type_tags = "," + "".join(tag for _, tag in typed_values)
    return _osc_string(address) + _osc_string(type_tags) + b"".join(arguments)


class OscSender:
    def __init__(self, port: int = PORT):
        if not 1 <= port <= 65535:
            raise ValueError("OSC port must be between 1 and 65535")
        try:
            from pythonosc.osc_message_builder import OscMessageBuilder
        except ModuleNotFoundError as exc:
            if exc.name != "pythonosc":
                raise
            OscMessageBuilder = None
        self.builder = OscMessageBuilder
        self.client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.address = (HOST, port)
        self.last_id = -1

    def _send(self, address: str, *typed_values) -> None:
        if self.builder is None:
            payload = _pack_message(address, typed_values)
        else:
            message = self.builder(address=address)
            for value, tag in typed_values:
                message.add_arg(value, tag)
            payload = message.build().dgram
        self.client.sendto(payload, self.address)

    def event(self, candidate: SnapCandidate) -> int:
        self.last_id = max(monotonic_ns(), self.last_id + 1)
        self._send(
            "/snap/event", (self.last_id, "h"), (candidate.timestamp, "d"),
            (candidate.confidence, "f"), (candidate.hand, "s"),
        )
        return self.last_id

    def health(self, status: str, details: str = "") -> None:
        detail = "".join(char if char.isprintable() else " " for char in details)[:120]
        self._send("/snap/health", (status, "s"), (detail, "s"))

    def metrics(self, metrics: Metrics, audio: float) -> None:
        self._send(
            "/snap/metrics", (metrics.separation, "f"), (metrics.velocity, "f"),
            (metrics.phase, "s"), (audio, "f"), (metrics.confidence, "f"),
        )

    def close(self):
        self.client.close()
