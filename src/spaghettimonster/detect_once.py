from __future__ import annotations

import argparse
import json
from pathlib import Path

from .camera_stream import BambuCameraClient, CameraConfig
from .config import load_config, setup_logging
from .failure_detector import LocalFailureDetector


def _cli() -> int:
    parser = argparse.ArgumentParser(
        description="Capture one A1 camera frame and run local failure detection."
    )
    parser.add_argument(
        "--save",
        help="Optional path to save the captured JPEG frame.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Seconds to wait for a camera frame before giving up.",
    )
    args = parser.parse_args()

    cfg = load_config()
    setup_logging(cfg.log_level)

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

    frame = camera.capture_frame(timeout_sec=args.timeout)
    if not frame:
        print("No frame captured.")
        return 1

    saved_to = None
    if args.save:
        output = Path(args.save).expanduser()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(frame)
        saved_to = str(output)

    result = detector.detect(frame)
    payload = {
        "failure_detected": result.failure_detected,
        "confidence": result.confidence,
        "failure_type": result.failure_type,
        "summary": result.summary,
        "saved_to": saved_to,
        "bytes_captured": len(frame),
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
