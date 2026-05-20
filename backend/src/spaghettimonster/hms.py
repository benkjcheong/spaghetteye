from __future__ import annotations

# Subset of common Bambu HMS codes. Full list: https://e.bambulab.com/query.php?lang=en
# Codes are normalized to 4-block uppercase form: AAAA_BBBB_CCCC_DDDD.
_HMS_DESCRIPTIONS: dict[str, str] = {
    "0300_0E00_0002_0001": "Filament runout",
    "0300_0F00_0003_0001": "Filament tangle / extruder clog",
    "0500_0100_0001_0001": "Bed leveling failed",
    "0700_8003_0001_0001": "Nozzle temperature abnormal",
    "0C00_0100_0001_0001": "Door open",
    "1200_0100_0001_0001": "AMS filament runout",
}


def format_hms_code(raw: dict | str) -> str:
    """Normalize an HMS entry to 'AAAA_BBBB_CCCC_DDDD' uppercase hex string.

    Bambu reports HMS as {'attr': int, 'code': int} or sometimes pre-formatted strings.
    The 4 blocks are derived from upper/lower halves of attr and code.
    """
    if isinstance(raw, str):
        return raw.upper()
    attr = int(raw.get("attr", 0))
    code = int(raw.get("code", 0))
    a = (attr >> 16) & 0xFFFF
    b = attr & 0xFFFF
    c = (code >> 16) & 0xFFFF
    d = code & 0xFFFF
    return f"{a:04X}_{b:04X}_{c:04X}_{d:04X}"


def describe(code: str) -> str:
    return _HMS_DESCRIPTIONS.get(code, "Unknown HMS code — see e.bambulab.com/query.php")
