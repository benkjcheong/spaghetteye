from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    printer_ip: str
    printer_serial: str
    access_code: str
    tg_bot_token: str
    tg_chat_id: str
    log_level: str = "INFO"


def _require(key: str) -> str:
    val = os.environ.get(key, "").strip()
    if not val:
        raise RuntimeError(f"Missing required env var: {key}")
    return val


def load_config(env_file: str | Path | None = None) -> Config:
    if env_file is None:
        env_file = Path.cwd() / ".env"
    load_dotenv(env_file, override=False)
    return Config(
        printer_ip=_require("PRINTER_IP"),
        printer_serial=_require("PRINTER_SERIAL"),
        access_code=_require("ACCESS_CODE"),
        tg_bot_token=_require("TG_BOT_TOKEN"),
        tg_chat_id=_require("TG_CHAT_ID"),
        log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    )


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
