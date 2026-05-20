"""One-shot helper: DM your bot `/chatid` and it prints + replies with chat ID.

Usage:
    python -m spaghettimonster.get_chatid

Then in Telegram, open your bot and send: /chatid
"""

from __future__ import annotations

import sys
import time

import requests

from .config import load_config, setup_logging

_API = "https://api.telegram.org"


def run() -> int:
    cfg = load_config()
    setup_logging(cfg.log_level)
    token = cfg.tg_bot_token
    base = f"{_API}/bot{token}"

    # Clear any backlog so we only react to fresh /chatid.
    r = requests.get(f"{base}/getUpdates", params={"timeout": 0}, timeout=10)
    r.raise_for_status()
    last = r.json().get("result", [])
    offset = (last[-1]["update_id"] + 1) if last else 0

    print("Bot listening. In Telegram, DM your bot:  /chatid", flush=True)
    print("(Ctrl-C to abort)", flush=True)

    while True:
        try:
            r = requests.get(
                f"{base}/getUpdates",
                params={"timeout": 30, "offset": offset},
                timeout=40,
            )
            r.raise_for_status()
            for upd in r.json().get("result", []):
                offset = upd["update_id"] + 1
                msg = upd.get("message") or upd.get("channel_post") or {}
                text = (msg.get("text") or "").strip()
                chat = msg.get("chat", {})
                chat_id = chat.get("id")
                if text.lower().startswith("/chatid") and chat_id is not None:
                    print(f"\nTG_CHAT_ID={chat_id}", flush=True)
                    requests.post(
                        f"{base}/sendMessage",
                        json={
                            "chat_id": chat_id,
                            "text": f"chat_id = `{chat_id}`\nPaste into .env as TG_CHAT_ID.",
                            "parse_mode": "Markdown",
                        },
                        timeout=10,
                    )
                    return 0
        except requests.RequestException as e:
            print(f"network error: {e}; retrying in 3s", file=sys.stderr, flush=True)
            time.sleep(3)


if __name__ == "__main__":
    raise SystemExit(run())
