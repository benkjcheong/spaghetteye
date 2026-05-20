# Spaghetti Monster

Self-hosted Bambu A1 / A1 mini print monitor. Connects to your printer over the LAN MQTT
interface, watches state + HMS error codes, and pushes notifications to a Telegram bot.
No cloud, no Pi, no OctoEverywhere — runs as a plain Python process on your iMac.

## v1 features

- Connects to Bambu A1 / A1 mini over local MQTT (TLS, port 8883).
- Notifies on Telegram when:
  - print starts / pauses / resumes / finishes / fails
  - HMS warnings appear (filament runout, AMS error, door open, etc.)
  - non-zero `print_error` raised
- Auto-reconnects on disconnect.
- Initial state sync is silent (no spurious "started" event on cold start).

Out of scope in v1: camera/AI failure detection, web UI, pause/resume control. See the plan
in `/Users/benkjcheong/.claude/plans/the-project-is-a-peppy-lecun.md` for the roadmap.

## Prerequisites

- Bambu A1 / A1 mini on your LAN, with **LAN-only mode** enabled (Settings → General → LAN-only
  mode). Cloud mode also works as long as the printer is on the same network — but LAN-only
  is what this project is designed for.
- LAN Access Code: printer screen → Settings → WLAN → Access Code (8 digits).
- Printer serial number: printer screen → Settings → Device → SN (or sticker on back).
- Printer LAN IP: your router admin page, or printer screen → Settings → WLAN.
- A Telegram bot token + your chat ID.

### Creating the Telegram bot

1. In Telegram, message [@BotFather](https://t.me/BotFather) and send `/newbot`. Follow the
   prompts to get a bot token like `123456:ABCdef...`.
2. Start a chat with your new bot and send any message (e.g. `/start`) so it can find you.
3. Visit `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser. Find the `chat.id`
   field in the response — that's your `TG_CHAT_ID`.

## Setup

```bash
cd /Users/benkjcheong/spaghettimonster
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .   # so `python -m spaghettimonster` resolves

cp .env.example .env
# edit .env with your printer IP, serial, access code, telegram token + chat id
```

## Smoke test the Telegram side

```bash
python -m spaghettimonster.telegram --test
# expect: "sent"  and a "hello from spaghetti monster" message in Telegram
```

## Run

```bash
python -m spaghettimonster
```

Expected first log lines:

```
... INFO spaghettimonster: starting spaghettimonster v1 (printer=<SN>)
... INFO spaghettimonster.mqtt_client: connecting to <IP>:8883 as bblp
... INFO spaghettimonster.mqtt_client: connected, subscribing device/<SN>/report
```

Start a print on the printer → expect a Telegram message within a few seconds.

## Run tests

```bash
pip install pytest
python -m pytest tests/ -q
```

## Layout

```
spaghettimonster/
├── src/spaghettimonster/
│   ├── __main__.py       # python -m spaghettimonster
│   ├── config.py         # .env loader
│   ├── events.py         # Event dataclass + formatter
│   ├── hms.py            # HMS code lookup
│   ├── mqtt_client.py    # paho-mqtt TLS connection
│   ├── state.py          # snapshot + diff → events
│   ├── telegram.py       # bot API client
│   └── main.py           # wiring
└── tests/test_state.py
```

## Troubleshooting

- **`connect failed: Not authorised`**: wrong `ACCESS_CODE`. Re-check the printer screen.
  Note the access code can rotate if you toggle LAN-only mode.
- **No messages arriving in Telegram**: run the `--test` smoke test. If that works but live
  events don't, check that the printer is publishing — `python -m spaghettimonster` logs
  every received payload at DEBUG level (set `LOG_LEVEL=DEBUG` in `.env`).
- **TLS errors**: the printer uses a self-signed cert; this project disables verification
  with `tls_insecure_set(True)`. If your Python build complains, ensure
  `paho-mqtt>=2.0`.

## Privacy

The printer talks only to your iMac on the LAN. No data leaves your network except the
outbound HTTPS POSTs to `api.telegram.org`. Putting the iMac behind Tailscale doesn't change
this — Tailscale is only relevant when you later add a dashboard (v2.1).
