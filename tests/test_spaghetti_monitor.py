from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from spaghettimonster.spaghetti_monitor import SpaghettiMonitor  # noqa: E402


class _FakeCamera:
    def __init__(self, frames):
        self.frames = list(frames)

    def capture_frame(self, timeout_sec: float = 10.0):
        if not self.frames:
            return None
        return self.frames.pop(0)


class _Result:
    def __init__(self, failure_detected, confidence, failure_type, summary):
        self.failure_detected = failure_detected
        self.confidence = confidence
        self.failure_type = failure_type
        self.summary = summary


class _FakeDetector:
    def __init__(self, results):
        self.results = list(results)

    def detect(self, jpeg_bytes: bytes):
        return self.results.pop(0)


def test_monitor_alerts_after_consecutive_hits():
    alerts = []
    monitor = SpaghettiMonitor(
        _FakeCamera([b"\xff\xd8a", b"\xff\xd8b"]),
        _FakeDetector(
            [
                _Result(True, 0.9, "spaghetti", "first hit"),
                _Result(True, 0.95, "spaghetti", "second hit"),
            ]
        ),
        lambda event, image: alerts.append((event, image)),
        interval_sec=999,
        min_confidence=0.85,
        consecutive_hits=2,
    )
    monitor.update_snapshot({"gcode_state": "RUNNING", "subtask_name": "benchy.3mf", "mc_percent": 42})
    monitor.tick_once()
    monitor.tick_once()

    assert len(alerts) == 1
    event, image = alerts[0]
    assert event.kind == "spaghetti_detected"
    assert image == b"\xff\xd8b"
    assert "spaghetti" in event.detail


def test_monitor_resets_when_print_is_not_running():
    alerts = []
    monitor = SpaghettiMonitor(
        _FakeCamera([b"\xff\xd8a", b"\xff\xd8b"]),
        _FakeDetector(
            [
                _Result(True, 0.9, "spaghetti", "first hit"),
                _Result(True, 0.95, "spaghetti", "second hit"),
            ]
        ),
        lambda event, image: alerts.append((event, image)),
        interval_sec=999,
        min_confidence=0.85,
        consecutive_hits=2,
    )
    monitor.update_snapshot({"gcode_state": "RUNNING", "subtask_name": "benchy.3mf"})
    monitor.tick_once()
    monitor.update_snapshot({"gcode_state": "PAUSE", "subtask_name": "benchy.3mf"})
    monitor.tick_once()
    monitor.update_snapshot({"gcode_state": "RUNNING", "subtask_name": "benchy.3mf"})
    monitor.tick_once()

    assert alerts == []
