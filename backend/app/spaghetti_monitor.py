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
TickCallback = Callable[[bytes | None, Any, int, bool], None]
AutoPauseCallback = Callable[[], None]


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
        on_tick: TickCallback | None = None,
        auto_pause: AutoPauseCallback | None = None,
        auto_pause_enabled: bool = False,
    ) -> None:
        self._camera = camera
        self._detector = detector
        self._on_alert = on_alert
        self._on_tick = on_tick
        self._auto_pause = auto_pause
        self._auto_pause_enabled = auto_pause_enabled
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
        self._auto_paused = False

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

        try:
            frame = self._camera.capture_frame()
        except Exception as exc:
            log.warning("camera capture failed: %s", exc)
            frame = None
        if not frame:
            diag = getattr(self._camera, "last_capture_diagnostic", None)
            log.warning("camera capture returned no frame%s", f": {diag}" if diag else "")

        now_active = snapshot.get("gcode_state") == "RUNNING"
        if not now_active:
            self._reset_state(now_active=False)
            self._emit_tick(frame, None)
            return

        if not self._active:
            self._reset_state(now_active=True)

        if not frame:
            self._emit_tick(None, None)
            return

        try:
            result = self._detector.detect(frame)
        except Exception as exc:
            log.warning("spaghetti detection failed: %s", exc)
            self._emit_tick(frame, None)
            return

        if not result.failure_detected or result.confidence < self._min_confidence:
            self._consecutive_hits = 0
            self._emit_tick(frame, result)
            return

        self._consecutive_hits += 1
        self._emit_tick(frame, result)
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
        if self._auto_pause_enabled and self._auto_pause is not None and not self._auto_paused:
            try:
                self._auto_pause()
                self._auto_paused = True
            except Exception as exc:
                log.warning("auto-pause failed: %s", exc)

    def _emit_tick(self, frame: bytes | None, result: Any) -> None:
        if self._on_tick is None:
            return
        try:
            self._on_tick(frame, result, self._consecutive_hits, self._alerted)
        except Exception as exc:
            log.debug("on_tick callback failed: %s", exc)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self.tick_once()
            self._stop_event.wait(self._interval_sec)

    def _reset_state(self, *, now_active: bool) -> None:
        self._active = now_active
        self._consecutive_hits = 0
        self._alerted = False
        self._auto_paused = False

    @staticmethod
    def _maybe_int(value: Any) -> int | None:
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None
