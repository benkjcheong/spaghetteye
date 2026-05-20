from __future__ import annotations

import logging
import signal
import sys

from .config import load_config, setup_logging
from .mqtt_client import build_client
from .state import StateTracker
from .telegram import TelegramNotifier

log = logging.getLogger("spaghettimonster")


def run() -> int:
    cfg = load_config()
    setup_logging(cfg.log_level)
    log.info("starting spaghettimonster v1 (printer=%s)", cfg.printer_serial)

    tracker = StateTracker()
    notifier = TelegramNotifier(cfg.tg_bot_token, cfg.tg_chat_id)

    def handle_payload(payload):
        events = tracker.ingest(payload)
        for ev in events:
            log.info("event: %s — %s", ev.kind, ev.title)
            ok = notifier.send(ev.format())
            if not ok:
                log.error("failed to deliver event: %s", ev.kind)

    client = build_client(
        printer_ip=cfg.printer_ip,
        printer_serial=cfg.printer_serial,
        access_code=cfg.access_code,
        on_payload=handle_payload,
    )

    def _stop(_signum, _frame):
        log.info("shutting down")
        client.disconnect()
        client.loop_stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    client.loop_forever(retry_first_connection=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
