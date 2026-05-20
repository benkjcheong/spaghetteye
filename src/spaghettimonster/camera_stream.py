from __future__ import annotations

import ctypes as c
import logging
import time
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

_BAMBU_SUCCESS = 0
_BAMBU_STREAM_END = 1
_BAMBU_WOULD_BLOCK = 2


class CameraUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class CameraConfig:
    printer_ip: str
    access_code: str
    user: str = "bblp"
    port: int = 6000
    library_path: str | None = None


class _Sample(c.Structure):
    _fields_ = [
        ("itrack", c.c_int),
        ("size", c.c_int),
        ("flags", c.c_int),
        ("buffer", c.POINTER(c.c_ubyte)),
        ("decode_time", c.c_ulonglong),
    ]


class BambuCameraClient:
    def __init__(self, config: CameraConfig) -> None:
        self._config = config
        self._lib = self._load_library(config.library_path)
        self._configure_api()

    @staticmethod
    def default_library_path() -> str:
        return str(Path.home() / "Library/Application Support/BambuStudio/plugins/libBambuSource.dylib")

    def _load_library(self, override: str | None):
        path = Path(override or self.default_library_path())
        if not path.exists():
            raise CameraUnavailableError(
                f"Bambu camera library not found at {path}. Install Bambu Studio or set CAMERA_LIBRARY_PATH."
            )
        try:
            return c.CDLL(str(path))
        except OSError as exc:
            raise CameraUnavailableError(f"Failed to load camera library at {path}: {exc}") from exc

    def _configure_api(self) -> None:
        self._lib.Bambu_Init.restype = c.c_int
        self._lib.Bambu_Deinit.restype = None
        self._lib.Bambu_Create.argtypes = [c.POINTER(c.c_void_p), c.c_char_p]
        self._lib.Bambu_Create.restype = c.c_int
        self._lib.Bambu_Open.argtypes = [c.c_void_p]
        self._lib.Bambu_Open.restype = c.c_int
        self._lib.Bambu_StartStream.argtypes = [c.c_void_p, c.c_bool]
        self._lib.Bambu_StartStream.restype = c.c_int
        self._lib.Bambu_ReadSample.argtypes = [c.c_void_p, c.POINTER(_Sample)]
        self._lib.Bambu_ReadSample.restype = c.c_int
        self._lib.Bambu_Close.argtypes = [c.c_void_p]
        self._lib.Bambu_Close.restype = None
        self._lib.Bambu_Destroy.argtypes = [c.c_void_p]
        self._lib.Bambu_Destroy.restype = None
        self._lib.Bambu_GetLastErrorMsg.restype = c.c_char_p

    def capture_frame(self, timeout_sec: float = 10.0) -> bytes | None:
        handle = c.c_void_p()
        url = (
            f"bambu:///local/{self._config.printer_ip}"
            f"?port={self._config.port}&user={self._config.user}&passwd={self._config.access_code}"
        ).encode("utf-8")
        rc = self._lib.Bambu_Init()
        if rc != _BAMBU_SUCCESS:
            raise CameraUnavailableError(f"Bambu_Init failed with rc={rc}")
        try:
            self._require_ok(self._lib.Bambu_Create(c.byref(handle), url), "Bambu_Create")
            self._require_ok(self._lib.Bambu_Open(handle), "Bambu_Open")
            start_rc = self._lib.Bambu_StartStream(handle, True)
            if start_rc not in {_BAMBU_SUCCESS, _BAMBU_WOULD_BLOCK}:
                self._raise_last_error("Bambu_StartStream", start_rc)

            deadline = time.monotonic() + timeout_sec
            while time.monotonic() < deadline:
                sample = _Sample()
                sample_rc = self._lib.Bambu_ReadSample(handle, c.byref(sample))
                if sample_rc == _BAMBU_SUCCESS and sample.size > 0:
                    frame = c.string_at(sample.buffer, sample.size)
                    if frame[:2] == b"\xff\xd8":
                        return frame
                    log.debug("camera sample was not a jpeg frame (%r)", frame[:8])
                elif sample_rc == _BAMBU_STREAM_END:
                    return None
                time.sleep(0.1)
            return None
        finally:
            if handle.value:
                self._lib.Bambu_Close(handle)
                self._lib.Bambu_Destroy(handle)
            self._lib.Bambu_Deinit()

    def _require_ok(self, rc: int, call_name: str) -> None:
        if rc != _BAMBU_SUCCESS:
            self._raise_last_error(call_name, rc)

    def _raise_last_error(self, call_name: str, rc: int) -> None:
        msg = self._lib.Bambu_GetLastErrorMsg()
        detail = msg.decode("utf-8", errors="ignore") if msg else "unknown error"
        raise CameraUnavailableError(f"{call_name} failed with rc={rc}: {detail}")
