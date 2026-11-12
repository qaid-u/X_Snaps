import importlib.util
import socket
import struct
from time import monotonic
import unittest
from unittest.mock import Mock, patch

from gesture_service.osc_sender import HOST, OscSender, _pack_message
from gesture_service.snap_detector import Metrics, SnapCandidate


class GestureOscWireTests(unittest.TestCase):
    def test_wire_messages(self):
        transport = Mock()
        with patch("gesture_service.osc_sender.socket.socket", return_value=transport):
            sender = OscSender(7400)
        try:
            timestamp = monotonic()
            event_id = sender.event(SnapCandidate(timestamp, 0.8, "Right"))
            payload, destination = transport.sendto.call_args.args
            self.assertEqual(destination, (HOST, 7400))
            self.assertEqual(payload[:20], b"/snap/event\0,hdfs\0\0\0")
            decoded_id, decoded_time, confidence = struct.unpack_from(">qdf", payload, 20)
            self.assertEqual(decoded_id, event_id)
            self.assertEqual(decoded_time, timestamp)
            self.assertAlmostEqual(confidence, 0.8)
            self.assertEqual(payload[40:], b"Right\0\0\0")
            self.assertGreater(sender.event(SnapCandidate(timestamp, 0.8, "Right")), event_id)

            sender.health("VISION_LOW_CONFIDENCE", "Microphone unavailable")
            payload, _ = transport.sendto.call_args.args
            self.assertEqual(
                payload,
                b"/snap/health\0\0\0\0,ss\0VISION_LOW_CONFIDENCE\0\0\0Microphone unavailable\0\0",
            )
            sender.metrics(Metrics(0.25, -0.5, "CONTACT", 0.75), 0.5)
            payload, _ = transport.sendto.call_args.args
            self.assertEqual(payload[:24], b"/snap/metrics\0\0\0,ffsff\0\0")
            self.assertEqual(struct.unpack_from(">ff", payload, 24), (0.25, -0.5))
            self.assertEqual(payload[32:40], b"CONTACT\0")
            self.assertEqual(struct.unpack_from(">ff", payload, 40), (0.5, 0.75))
        finally:
            sender.close()
        transport.close.assert_called_once()

    def test_loopback_transport(self):
        with (
            socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as listener,
            socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe,
        ):
            try:
                listener.bind((HOST, 0))
                listener.settimeout(0.4)
                probe.sendto(b"probe", listener.getsockname())
                self.assertEqual(listener.recvfrom(16)[0], b"probe")
            except (TimeoutError, PermissionError):
                self.skipTest("Execution environment did not deliver a raw UDP loopback probe")
            sender = OscSender(listener.getsockname()[1])
            try:
                sender.event(SnapCandidate(monotonic(), 0.8, "Right"))
                payload, source = listener.recvfrom(256)
                self.assertEqual(source[0], HOST)
                self.assertTrue(payload.startswith(b"/snap/event\0,hdfs\0\0\0"))
            finally:
                sender.close()

    @unittest.skipUnless(importlib.util.find_spec("pythonosc"), "Install python-osc for library parity")
    def test_preinstall_encoder_matches_python_osc(self):
        from pythonosc.osc_message_builder import OscMessageBuilder

        typed = ((45676117778778, "h"), (456761.17778778, "d"), (0.6, "f"), ("Right", "s"))
        builder = OscMessageBuilder("/snap/event")
        for value, tag in typed:
            builder.add_arg(value, tag)
        self.assertEqual(builder.build().dgram, _pack_message("/snap/event", typed))


if __name__ == "__main__":
    unittest.main()
