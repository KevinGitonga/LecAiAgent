from src.double_chance import canonicalise
from src.models import LatestMarket


def parse_latest_market(payload: dict, fixture_id: int, selection: str) -> LatestMarket:
    responses = payload.get("response", [])
    if not responses:
        raise ValueError("API-Football returned no odds response")

    event = responses[0]
    if int(event.get("fixture", {}).get("id", fixture_id)) != int(fixture_id):
        raise ValueError("API-Football fixture ID does not match")

    bookmakers = event.get("bookmakers", [])
    if not bookmakers:
        raise ValueError("API-Football returned no bookmakers")

    # Project requirement: the first bookmaker is the latest odds source.
    bookmaker = bookmakers[0]
    for bet in bookmaker.get("bets", []):
        if bet.get("id") not in (12, "12") and str(bet.get("name", "")).lower() != "double chance":
            continue
        for value in bet.get("values", []):
            try:
                label = canonicalise(value.get("value"))
            except ValueError:
                continue
            if label == selection:
                decimal_odds = round(float(value["odd"]),2)
                if decimal_odds <= 1:
                    raise ValueError("Latest decimal odds must be greater than 1")
                return LatestMarket(
                    fixture_id=int(fixture_id),
                    double_chance=selection,
                    decimal_odds=decimal_odds,
                    implied_probability=1.0 / decimal_odds,
                    bookmaker_id=int(bookmaker["id"]) if bookmaker.get("id") is not None else None,
                    bookmaker_name=str(bookmaker.get("name", "Unknown")),
                    updated_at=event.get("update"),
                )

    raise ValueError(f"First bookmaker has no double-chance odds for {selection}")
