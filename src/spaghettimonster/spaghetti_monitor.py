from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Any, Protocol

from .events import Event

log = logging.getLogger(__name__)


class CameraClient(Protocol):
    def capture_frame(self, timeout_sec: float = 10.0) -> bytes | None: ...


class Detector(Protocol):
    def detect(self, jpeg_bytes: bytes): ...


AlertCallback = Callable[[Event, bytes | None], None]


class SpaghettiMonitor:
    def __init__(
        self,
        camera: CameraClient,
        detector: Detector,
        on_alert: AlertCallback,
        *,
        interval_sec: float = 30.0,
        min_confidence: float = 0.85,
        consecutive_hits: int = 2,
    ) -> None:
        self._camera = camera
        self._detector = detector
        self._on_alert = on_alert
        self._interval_sec = interval_sec
        self._min_confidence = min_confidence
        self._consecutive_hits_required = consecutive_hits
        self._lock = threading.Lock()
        self._snapshot: dict[str, Any] = {}
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._active = False
        self._consecutive_hits = 0
        self._alerted = False

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="spaghetti-monitor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)

    def update_snapshot(self, snapshot: dict[str, Any]) -> None:
        with self._lock:
            self._snapshot = dict(snapshot)

    def tick_once(self) -> None:
        with self._lock:
            snapshot = dict(self._snapshot)

        now_active = snapshot.get("gcode_state") == "RUNNING"
        if not now_active:
            self._reset_state(now_active=False)
            return

        if not self._active:
            self._reset_state(now_active=True)

        try:
            frame = self._camera.capture_frame()
        except Exception as exc:
            log.warning("camera capture failed: %s", exc)
            return
        if not frame:
            return

        try:
            result = self._detector.detect(frame)
        except Exception as exc:
            log.warning("spaghetti detection failed: %s", exc)
            return

        if not result.failure_detected or result.confidence < self._min_confidence:
            self._consecutive_hits = 0
            return

        self._consecutive_hits += 1
        if self._alerted or self._consecutive_hits < self._consecutive_hits_required:
            return

        detail = f"{result.failure_type} ({result.confidence:.2f}) — {result.summary}"
        event = Event(
            kind="spaghetti_detected",
            title="Possible spaghetti / blob failure detected",
            detail=detail,
            file=snapshot.get("subtask_name"),
            layer=self._maybe_int(snapshot.get("layer_num")),
            layer_total=self._maybe_int(snapshot.get("total_layer_num")),
            percent=self._maybe_int(snapshot.get("mc_percent")),
        )
        self._on_alert(event, frame)
        self._alerted = True

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self.tick_once()
            self._stop_event.wait(self._interval_sec)

    def _reset_state(self, *, now_active: bool) -> None:
        self._active = now_active
        self._consecutive_hits = 0
        self._alerted = False

    @staticmethod
    def _maybe_int(value: Any) -> int | None:
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None
