from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from spaghettimonster import detect_once  # noqa: E402


class _FakeCamera:
    def capture_frame(self, timeout_sec: float = 10.0):
        return b"\xff\xd8jpeg-bytes"


class _FakeResult:
    failure_detected = True
    confidence = 0.73
    failure_type = "failure"
    summary = "test summary"


class _FakeDetector:
    def detect(self, frame: bytes):
        assert frame == b"\xff\xd8jpeg-bytes"
        return _FakeResult()


def test_detect_once_saves_frame_and_prints_json(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(detect_once, "load_config", lambda: type("Cfg", (), {
        "printer_ip": "192.168.1.33",
        "access_code": "12345678",
        "camera_library_path": None,
        "spaghetti_model_url": "https://example.com/model.onnx",
        "spaghetti_model_path": None,
        "spaghetti_detection_threshold": 0.08,
        "log_level": "INFO",
    })())
    monkeypatch.setattr(detect_once, "setup_logging", lambda level: None)
    monkeypatch.setattr(detect_once, "BambuCameraClient", lambda cfg: _FakeCamera())
    monkeypatch.setattr(detect_once, "LocalFailureDetector", lambda **kwargs: _FakeDetector())
    output = tmp_path / "frame.jpg"
    monkeypatch.setattr(sys, "argv", ["detect_once", "--save", str(output)])

    rc = detect_once._cli()

    assert rc == 0
    assert output.read_bytes() == b"\xff\xd8jpeg-bytes"
    payload = json.loads(capsys.readouterr().out)
    assert payload["failure_detected"] is True
    assert payload["saved_to"] == str(output)


def test_detect_once_returns_error_when_no_frame(monkeypatch, capsys):
    monkeypatch.setattr(detect_once, "load_config", lambda: type("Cfg", (), {
        "printer_ip": "192.168.1.33",
        "access_code": "12345678",
        "camera_library_path": None,
        "spaghetti_model_url": "https://example.com/model.onnx",
        "spaghetti_model_path": None,
        "spaghetti_detection_threshold": 0.08,
        "log_level": "INFO",
    })())
    monkeypatch.setattr(detect_once, "setup_logging", lambda level: None)
    monkeypatch.setattr(detect_once, "BambuCameraClient", lambda cfg: type("Cam", (), {"capture_frame": lambda self, timeout_sec=10.0: None})())
    monkeypatch.setattr(detect_once, "LocalFailureDetector", lambda **kwargs: _FakeDetector())
    monkeypatch.setattr(sys, "argv", ["detect_once"])

    rc = detect_once._cli()

    assert rc == 1
    assert "No frame captured." in capsys.readouterr().out
