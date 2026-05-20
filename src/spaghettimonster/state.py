from __future__ import annotations

from typing import Any

from .events import Event
from .hms import describe, format_hms_code

# gcode_state values seen in the wild: IDLE, PREPARE, RUNNING, PAUSE, FINISH, FAILED
_ACTIVE_STATES = {"RUNNING", "PAUSE", "PREPARE"}


def _deep_merge(dst: dict[str, Any], src: dict[str, Any]) -> dict[str, Any]:
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_merge(dst[k], v)
        else:
            dst[k] = v
    return dst


class StateTracker:
    """Merge partial MQTT updates into a running snapshot, emit diff events."""

    def __init__(self) -> None:
        self.snapshot: dict[str, Any] = {}
        self.active_hms: set[str] = set()
        self.primed: bool = False  # silence first-message events (cold start)

    def ingest(self, payload: dict[str, Any]) -> list[Event]:
        """payload is the full MQTT message body. Returns events triggered by the diff."""
        print_section = payload.get("print")
        if not isinstance(print_section, dict):
            return []

        prev = dict(self.snapshot)  # shallow copy is enough for top-level reads
        # Track prev gcode_state explicitly before merge.
        prev_gcode = prev.get("gcode_state")
        prev_print_error = prev.get("print_error", 0)

        _deep_merge(self.snapshot, print_section)
        events: list[Event] = []

        if not self.primed:
            self.primed = True
            # seed active_hms from initial snapshot without firing
            self.active_hms = self._current_hms_codes()
            return events

        # gcode_state transitions
        new_gcode = self.snapshot.get("gcode_state")
        if new_gcode != prev_gcode and new_gcode is not None:
            ev = self._state_change_event(new_gcode, prev_gcode)
            if ev is not None:
                events.append(ev)

        # print_error (non-zero, newly set)
        new_err = self.snapshot.get("print_error", 0)
        if new_err and new_err != prev_print_error:
            events.append(
                Event(
                    kind="print_error",
                    title="Print error code raised",
                    detail=f"print_error={new_err}",
                    file=self.snapshot.get("subtask_name"),
                    layer=self._maybe_int("layer_num"),
                    layer_total=self._maybe_int("total_layer_num"),
                    percent=self._maybe_int("mc_percent"),
                )
            )

        # HMS diff
        current = self._current_hms_codes()
        new_codes = current - self.active_hms
        for code in sorted(new_codes):
            events.append(
                Event(
                    kind="hms",
                    title="HMS alert",
                    detail=describe(code),
                    hms_code=code,
                    file=self.snapshot.get("subtask_name"),
                    layer=self._maybe_int("layer_num"),
                    layer_total=self._maybe_int("total_layer_num"),
                    percent=self._maybe_int("mc_percent"),
                )
            )
        self.active_hms = current

        return events

    def _current_hms_codes(self) -> set[str]:
        hms = self.snapshot.get("hms")
        if not isinstance(hms, list):
            return set()
        return {format_hms_code(item) for item in hms if isinstance(item, (dict, str))}

    def _maybe_int(self, key: str) -> int | None:
        v = self.snapshot.get(key)
        try:
            return int(v) if v is not None else None
        except (TypeError, ValueError):
            return None

    def _state_change_event(self, new: str, prev: str | None) -> Event | None:
        titles = {
            "RUNNING": ("print_start", "Print started")
            if prev in (None, "IDLE", "FINISH", "FAILED", "PREPARE")
            else ("print_resume", "Print resumed"),
            "PAUSE": ("print_pause", "Print paused"),
            "FINISH": ("print_finish", "Print finished"),
            "FAILED": ("print_fail", "Print failed"),
        }
        entry = titles.get(new)
        if entry is None:
            return None
        kind, title = entry
        return Event(
            kind=kind,
            title=title,
            file=self.snapshot.get("subtask_name"),
            layer=self._maybe_int("layer_num"),
            layer_total=self._maybe_int("total_layer_num"),
            percent=self._maybe_int("mc_percent"),
        )
