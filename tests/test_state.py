from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from spaghettimonster.state import StateTracker  # noqa: E402


def _wrap(print_section: dict) -> dict:
    return {"print": print_section}


def test_initial_message_is_silent():
    t = StateTracker()
    out = t.ingest(_wrap({"gcode_state": "RUNNING", "subtask_name": "x.3mf"}))
    assert out == []
    assert t.snapshot["gcode_state"] == "RUNNING"


def test_print_start_after_idle():
    t = StateTracker()
    t.ingest(_wrap({"gcode_state": "IDLE"}))
    out = t.ingest(_wrap({"gcode_state": "RUNNING", "subtask_name": "benchy.3mf"}))
    assert len(out) == 1
    assert out[0].kind == "print_start"
    assert out[0].file == "benchy.3mf"


def test_pause_resume_finish_sequence():
    t = StateTracker()
    t.ingest(_wrap({"gcode_state": "IDLE"}))
    s1 = t.ingest(_wrap({"gcode_state": "RUNNING"}))
    s2 = t.ingest(_wrap({"gcode_state": "PAUSE"}))
    s3 = t.ingest(_wrap({"gcode_state": "RUNNING"}))
    s4 = t.ingest(_wrap({"gcode_state": "FINISH"}))
    kinds = [e.kind for e in s1 + s2 + s3 + s4]
    assert kinds == ["print_start", "print_pause", "print_resume", "print_finish"]


def test_failure_emits_print_fail():
    t = StateTracker()
    t.ingest(_wrap({"gcode_state": "RUNNING"}))
    out = t.ingest(_wrap({"gcode_state": "FAILED"}))
    assert [e.kind for e in out] == ["print_fail"]


def test_hms_new_code_emits_event():
    t = StateTracker()
    t.ingest(_wrap({"gcode_state": "RUNNING", "hms": []}))
    out = t.ingest(
        _wrap(
            {
                "hms": [{"attr": 0x03000E00, "code": 0x00020001}],
                "subtask_name": "x.3mf",
                "layer_num": 12,
                "total_layer_num": 100,
                "mc_percent": 12,
            }
        )
    )
    hms_events = [e for e in out if e.kind == "hms"]
    assert len(hms_events) == 1
    ev = hms_events[0]
    assert ev.hms_code == "0300_0E00_0002_0001"
    assert "Filament runout" in ev.detail
    assert ev.layer == 12
    assert ev.layer_total == 100


def test_hms_persistent_code_not_repeated():
    t = StateTracker()
    t.ingest(_wrap({"gcode_state": "RUNNING", "hms": [{"attr": 0x03000E00, "code": 0x00020001}]}))
    out = t.ingest(_wrap({"hms": [{"attr": 0x03000E00, "code": 0x00020001}]}))
    assert [e for e in out if e.kind == "hms"] == []


def test_print_error_nonzero_emits_event():
    t = StateTracker()
    t.ingest(_wrap({"gcode_state": "RUNNING", "print_error": 0}))
    out = t.ingest(_wrap({"print_error": 117440513}))
    err_events = [e for e in out if e.kind == "print_error"]
    assert len(err_events) == 1


def test_non_print_payload_ignored():
    t = StateTracker()
    out = t.ingest({"info": {"command": "get_version"}})
    assert out == []
    assert t.snapshot == {}


def test_partial_update_merges():
    t = StateTracker()
    t.ingest(_wrap({"gcode_state": "RUNNING", "subtask_name": "a.3mf", "mc_percent": 10}))
    t.ingest(_wrap({"mc_percent": 25}))  # partial update
    assert t.snapshot["subtask_name"] == "a.3mf"
    assert t.snapshot["mc_percent"] == 25
