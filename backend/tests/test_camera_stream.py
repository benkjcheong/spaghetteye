from __future__ import annotations

import ctypes as c
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from spaghettimonster.camera_stream import BambuCameraClient, CameraConfig  # noqa: E402


class _FakeLib:
    def __init__(self, samples):
        self._samples = list(samples)
        self._buffers = []

    def Bambu_Init(self):
        return 0

    def Bambu_Create(self, handle_ptr, url):
        handle_ptr._obj.value = 1
        return 0

    def Bambu_Open(self, handle):
        return 0

    def Bambu_StartStream(self, handle, video):
        return 0

    def Bambu_GetStreamCount(self, handle):
        return 0

    def Bambu_GetStreamInfo(self, handle, index, info_ptr):
        return -1

    def Bambu_ReadSample(self, handle, sample_ptr):
        if not self._samples:
            return 2

        data, flags = self._samples.pop(0)
        buf = c.create_string_buffer(data)
        self._buffers.append(buf)
        sample = sample_ptr._obj
        sample.itrack = 0
        sample.size = len(data)
        sample.flags = flags
        sample.buffer = c.cast(buf, c.POINTER(c.c_ubyte))
        sample.decode_time = 0
        return 0

    def Bambu_Close(self, handle):
        return None

    def Bambu_Destroy(self, handle):
        return None

    def Bambu_Deinit(self):
        return None

    def Bambu_GetLastErrorMsg(self):
        return b"fake error"


def _make_client(lib: _FakeLib) -> BambuCameraClient:
    client = BambuCameraClient.__new__(BambuCameraClient)
    client._config = CameraConfig(printer_ip="192.168.1.33", access_code="12345678")
    client._lib = lib
    client.last_capture_diagnostic = None
    return client


def test_capture_frame_returns_jpeg_sample():
    client = _make_client(_FakeLib([(b"\xff\xd8jpeg-bytes", 0)]))

    frame = client.capture_frame(timeout_sec=0.2)

    assert frame == b"\xff\xd8jpeg-bytes"


def test_capture_frame_decodes_h264_sample(monkeypatch):
    raw_h264 = b"\x00\x00\x00\x01\x67\x64\x00\x1f\xac\xd9\x40"
    client = _make_client(_FakeLib([(raw_h264, 1)]))

    seen = {}

    def _fake_decode(video_bytes: bytes) -> bytes | None:
        seen["video_bytes"] = video_bytes
        return b"\xff\xd8decoded-jpeg"

    monkeypatch.setattr(client, "_decode_h264_to_jpeg", _fake_decode)

    frame = client.capture_frame(timeout_sec=0.2)

    assert frame == b"\xff\xd8decoded-jpeg"
    assert seen["video_bytes"] == raw_h264
