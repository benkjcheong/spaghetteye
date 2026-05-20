from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from collections import deque
from dataclasses import asdict
from typing import Any

import uvicorn
from fastapi import FastAPI, File, Form, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from .events import Event
from .failure_detector import DetectionResult
from .ftps_upload import FtpsUploadError
from .printer_control import VALID_ACTIONS, PrinterControl

log = logging.getLogger(__name__)

_EVENT_BUFFER_SIZE = 200


def _safe_remote_name(name: str) -> str:
    base = name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_", ".", " ") else "_" for ch in base)
    cleaned = cleaned.strip().replace(" ", "_") or "upload.3mf"
    if not cleaned.lower().endswith(".3mf"):
        cleaned += ".3mf"
    return cleaned[:120]


class AppState:
    """Thread-safe shared state surfaced to the HTTP API."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._snapshot: dict[str, Any] = {}
        self._events: deque[dict[str, Any]] = deque(maxlen=_EVENT_BUFFER_SIZE)
        self._subscribers: list[asyncio.Queue[dict[str, Any]]] = []
        self._loop: asyncio.AbstractEventLoop | None = None
        self._frame_bytes: bytes | None = None
        self._frame_ts: float | None = None
        self._detector: dict[str, Any] = {
            "last_tick_ts": None,
            "last_confidence": None,
            "last_summary": None,
            "failure_detected": None,
            "consecutive_hits": 0,
            "alerted": False,
        }
        self._control: PrinterControl | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def update_snapshot(self, snapshot: dict[str, Any]) -> None:
        with self._lock:
            self._snapshot = dict(snapshot)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._snapshot)

    def push_event(self, event: Event) -> None:
        record = {"ts": time.time(), **asdict(event)}
        with self._lock:
            self._events.append(record)
            subs = list(self._subscribers)
            loop = self._loop
        if loop is None:
            return
        for q in subs:
            loop.call_soon_threadsafe(self._safe_put, q, record)

    @staticmethod
    def _safe_put(q: asyncio.Queue[dict[str, Any]], item: dict[str, Any]) -> None:
        try:
            q.put_nowait(item)
        except asyncio.QueueFull:
            pass

    def recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._events)[-limit:]

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=64)
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[dict[str, Any]]) -> None:
        with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def set_frame(self, jpeg: bytes | None) -> None:
        with self._lock:
            if jpeg:
                self._frame_bytes = jpeg
                self._frame_ts = time.time()

    def frame(self) -> tuple[bytes | None, float | None]:
        with self._lock:
            return self._frame_bytes, self._frame_ts

    def update_detection(self, result: DetectionResult | None, consecutive_hits: int, alerted: bool) -> None:
        with self._lock:
            self._detector["last_tick_ts"] = time.time()
            self._detector["consecutive_hits"] = consecutive_hits
            self._detector["alerted"] = alerted
            if result is not None:
                self._detector["last_confidence"] = result.confidence
                self._detector["last_summary"] = result.summary
                self._detector["failure_detected"] = result.failure_detected

    def detector(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._detector)

    def bind_control(self, ctrl: PrinterControl) -> None:
        with self._lock:
            self._control = ctrl

    def control(self) -> PrinterControl | None:
        with self._lock:
            return self._control


def build_app(state: AppState) -> FastAPI:
    app = FastAPI(title="App API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def _startup() -> None:
        state.bind_loop(asyncio.get_running_loop())

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {"ok": True, "ts": time.time()}

    @app.get("/api/snapshot")
    def snapshot() -> dict[str, Any]:
        return {"snapshot": state.snapshot()}

    @app.get("/api/events")
    def events(limit: int = 50) -> dict[str, Any]:
        limit = max(1, min(limit, _EVENT_BUFFER_SIZE))
        return {"events": state.recent_events(limit)}

    @app.get("/api/detector")
    def detector() -> dict[str, Any]:
        return state.detector()

    @app.get("/api/frame.jpg")
    def frame() -> Response:
        jpeg, ts = state.frame()
        if not jpeg:
            return Response(status_code=404, content=b"no frame yet")
        headers = {"Cache-Control": "no-store"}
        if ts is not None:
            headers["X-Frame-Timestamp"] = f"{ts:.3f}"
        return Response(content=jpeg, media_type="image/jpeg", headers=headers)

    @app.post("/api/print/{action}")
    def print_control(action: str) -> Response:
        if action not in VALID_ACTIONS:
            return JSONResponse({"ok": False, "error": "bad_action"}, status_code=400)
        ctrl = state.control()
        if ctrl is None or not ctrl.is_connected():
            return JSONResponse({"ok": False, "error": "mqtt_disconnected"}, status_code=503)
        snap = state.snapshot()
        gcode = str(snap.get("gcode_state") or "").upper()
        allowed = {"pause": {"RUNNING"}, "resume": {"PAUSE"}, "stop": {"RUNNING", "PAUSE"}}
        if gcode not in allowed[action]:
            return JSONResponse(
                {"ok": False, "error": "bad_state", "gcode_state": gcode},
                status_code=409,
            )
        ok, seq = ctrl.publish_command(action, source="api")
        return JSONResponse({"ok": ok, "sequence_id": seq}, status_code=200 if ok else 502)

    @app.post("/api/print/start")
    async def print_start(
        file: UploadFile = File(...),
        plate: int = Form(1),
        use_ams: bool = Form(False),
        bed_leveling: bool = Form(True),
        flow_cali: bool = Form(False),
        vibration_cali: bool = Form(True),
        layer_inspect: bool = Form(False),
        timelapse: bool = Form(False),
    ) -> Response:
        if not file.filename or not file.filename.lower().endswith(".3mf"):
            return JSONResponse({"ok": False, "error": "must_be_3mf"}, status_code=400)
        ctrl = state.control()
        if ctrl is None or not ctrl.is_connected():
            return JSONResponse({"ok": False, "error": "mqtt_disconnected"}, status_code=503)
        snap = state.snapshot()
        gcode = str(snap.get("gcode_state") or "").upper()
        if gcode not in {"IDLE", "FINISH", "FAILED", ""}:
            return JSONResponse(
                {"ok": False, "error": "busy", "gcode_state": gcode},
                status_code=409,
            )

        safe_name = _safe_remote_name(file.filename)
        subtask = safe_name.rsplit(".", 1)[0]
        try:
            ok, seq = ctrl.upload_and_start(
                src=file.file,
                remote_name=safe_name,
                subtask_name=subtask,
                plate=plate,
                use_ams=use_ams,
                bed_leveling=bed_leveling,
                flow_cali=flow_cali,
                vibration_cali=vibration_cali,
                layer_inspect=layer_inspect,
                timelapse=timelapse,
            )
        except FtpsUploadError as exc:
            return JSONResponse({"ok": False, "error": "ftps_failed", "detail": str(exc)}, status_code=502)
        finally:
            await file.close()
        return JSONResponse(
            {"ok": ok, "sequence_id": seq, "remote_name": safe_name},
            status_code=200 if ok else 502,
        )

    @app.get("/api/stream")
    async def stream() -> StreamingResponse:
        q = state.subscribe()

        async def gen():
            try:
                yield f": connected\n\n"
                while True:
                    try:
                        item = await asyncio.wait_for(q.get(), timeout=15.0)
                        yield f"data: {json.dumps(item)}\n\n"
                    except asyncio.TimeoutError:
                        yield ": ping\n\n"
            finally:
                state.unsubscribe(q)

        return StreamingResponse(gen(), media_type="text/event-stream")

    return app


class ApiServer:
    """Run uvicorn in a background thread."""

    def __init__(self, app: FastAPI, *, host: str = "0.0.0.0", port: int = 8000) -> None:
        config = uvicorn.Config(app, host=host, port=port, log_level="info", access_log=False)
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(target=self._server.run, name="api-server", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._server.should_exit = True
        self._thread.join(timeout=5.0)
