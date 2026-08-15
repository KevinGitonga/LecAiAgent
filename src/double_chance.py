import re

CANONICAL = ("1X", "12", "X2")

_ALIAS_MAP = {
    "1x": "1X", "home/draw": "1X", "home draw": "1X", "home or draw": "1X",
    "home_draw": "1X", "home_or_draw": "1X", "home-draw": "1X", "1/x": "1X",
    "12": "12", "1/2": "12", "home/away": "12", "home away": "12",
    "home or away": "12", "home_away": "12", "home_or_away": "12", "home-away": "12",
    "x2": "X2", "x/2": "X2", "draw/away": "X2", "draw away": "X2",
    "draw or away": "X2", "away_draw": "X2", "draw_or_away": "X2", "draw-away": "X2",
}

API_FOOTBALL_LABEL = {"1X": "Home/Draw", "12": "Home/Away", "X2": "Draw/Away"}
SCORES254_ODD_KEY = {"1X": "home_draw", "12": "home_away", "X2": "away_draw"}


def canonicalise(value: str) -> str:
    if value is None:
        raise ValueError("Double chance value is missing")
    raw = str(value).strip()
    direct = _ALIAS_MAP.get(raw.lower())
    if direct:
        return direct
    compact = re.sub(r"[^0-9xX]", "", raw).upper()
    if compact in CANONICAL:
        return compact
    raise ValueError(f"Unsupported double chance label: {value!r}")
