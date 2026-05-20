from __future__ import annotations

import logging
import signal
import sys

from .camera_stream import BambuCameraClient, CameraConfig, CameraUnavailableError
from .config import load_config, setup_logging
from .failure_detector import DetectionError, LocalFailureDetector
from .mqtt_client import build_client
from .spaghetti_monitor import SpaghettiMonitor
from .state import StateTracker
from .telegram import TelegramNotifier

log = logging.getLogger("spaghettimonster")


def run() -> int:
    cfg = load_config()
    setup_logging(cfg.log_level)
    log.info("starting spaghettimonster v1 (printer=%s)", cfg.printer_serial)

    tracker = StateTracker()
    notifier = TelegramNotifier(cfg.tg_bot_token, cfg.tg_chat_id)
    monitor = _build_spaghetti_monitor(cfg, notifier)

    def handle_payload(payload):
        events = tracker.ingest(payload)
        for ev in events:
            _deliver_monitor_event(notifier, ev, None)
        if monitor is not None:
            monitor.update_snapshot(tracker.snapshot)

    client = build_client(
        printer_ip=cfg.printer_ip,
        printer_serial=cfg.printer_serial,
        access_code=cfg.access_code,
        on_payload=handle_payload,
    )
    if monitor is not None:
        monitor.start()

    def _stop(_signum, _frame):
        log.info("shutting down")
        if monitor is not None:
            monitor.stop()
        client.disconnect()
        client.loop_stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    try:
        client.loop_forever(retry_first_connection=True)
    finally:
        if monitor is not None:
            monitor.stop()
    return 0


def _build_spaghetti_monitor(cfg, notifier: TelegramNotifier) -> SpaghettiMonitor | None:
    if not cfg.spaghetti_ai_enabled:
        return None
    try:
        camera = BambuCameraClient(
            CameraConfig(
                printer_ip=cfg.printer_ip,
                access_code=cfg.access_code,
                library_path=cfg.camera_library_path,
            )
        )
        detector = LocalFailureDetector(
            model_url=cfg.spaghetti_model_url,
            model_path=cfg.spaghetti_model_path,
            threshold=cfg.spaghetti_detection_threshold,
        )
    except CameraUnavailableError as exc:
        log.warning("AI monitoring disabled: %s", exc)
        return None
    except DetectionError as exc:
        log.warning("AI monitoring disabled: %s", exc)
        return None
    return SpaghettiMonitor(
        camera,
        detector,
        lambda event, image: _deliver_monitor_event(notifier, event, image),
        interval_sec=cfg.spaghetti_interval_sec,
        min_confidence=cfg.spaghetti_min_confidence,
        consecutive_hits=cfg.spaghetti_consecutive_hits,
    )


def _deliver_monitor_event(notifier: TelegramNotifier, event, image_bytes) -> None:
    log.info("event: %s — %s", event.kind, event.title)
    ok = notifier.send_photo(image_bytes, event.format()) if image_bytes else notifier.send(event.format())
    if not ok:
        log.error("failed to deliver event: %s", event.kind)


if __name__ == "__main__":
    raise SystemExit(run())
