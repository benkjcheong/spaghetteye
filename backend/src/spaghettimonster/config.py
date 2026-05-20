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
    spaghetti_ai_enabled: bool = False
    spaghetti_interval_sec: float = 30.0
    spaghetti_consecutive_hits: int = 2
    spaghetti_min_confidence: float = 0.85
    camera_library_path: str | None = None
    spaghetti_model_path: str | None = None
    spaghetti_model_url: str = "https://tsd-pub-static.s3.amazonaws.com/ml-models/model-weights-5a6b1be1fa.onnx"
    spaghetti_detection_threshold: float = 0.08


def _get_bool(key: str, default: bool = False) -> bool:
    val = os.environ.get(key)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(key: str, default: int) -> int:
    val = os.environ.get(key)
    if val is None or not val.strip():
        return default
    return int(val)


def _get_float(key: str, default: float) -> float:
    val = os.environ.get(key)
    if val is None or not val.strip():
        return default
    return float(val)


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
        spaghetti_ai_enabled=_get_bool("SPAGHETTI_AI_ENABLED", False),
        spaghetti_interval_sec=_get_float("SPAGHETTI_INTERVAL_SEC", 30.0),
        spaghetti_consecutive_hits=_get_int("SPAGHETTI_CONSECUTIVE_HITS", 2),
        spaghetti_min_confidence=_get_float("SPAGHETTI_MIN_CONFIDENCE", 0.85),
        camera_library_path=os.environ.get("CAMERA_LIBRARY_PATH", "").strip() or None,
        spaghetti_model_path=os.environ.get("SPAGHETTI_MODEL_PATH", "").strip() or None,
        spaghetti_model_url=(
            os.environ.get("SPAGHETTI_MODEL_URL", "").strip()
            or "https://tsd-pub-static.s3.amazonaws.com/ml-models/model-weights-5a6b1be1fa.onnx"
        ),
        spaghetti_detection_threshold=_get_float("SPAGHETTI_DETECTION_THRESHOLD", 0.08),
    )


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
