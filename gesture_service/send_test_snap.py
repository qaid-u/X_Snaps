"""Send a single synthetic snap over OSC without camera or microphone access."""

import argparse
from time import monotonic

from .osc_sender import OscSender
from .snap_detector import SnapCandidate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=7400)
    args = parser.parse_args()
    sender = OscSender(args.port)
    try:
        event_id = sender.event(SnapCandidate(monotonic(), 1.0, "TEST"))
        print(f"Sent /snap/event {event_id} to 127.0.0.1:{args.port}")
    finally:
        sender.close()


if __name__ == "__main__":
    main()
