from src.double_chance import canonicalise, SCORES254_ODD_KEY
from src.models import FixtureSignal


def _probability(value) -> float:
    n = float(str(value).replace("%", "").strip())
    if n > 1:
        n /= 100.0
    if not 0 <= n <= 1:
        raise ValueError(f"Probability outside [0,1]: {value}")
    return n


def parse_fixture(payload: dict) -> FixtureSignal:
    rows = payload.get("data", [])
    if not rows:
        raise ValueError("254Scores returned no fixture")
    fixture = rows[0]

    prediction = fixture.get("prediction")
    league = fixture.get("league")
    odd = fixture.get("odd")
    if not isinstance(prediction, dict):
        raise ValueError("254Scores prediction relation is missing")
    if not isinstance(league, dict):
        raise ValueError("254Scores league relation is missing")
    if not isinstance(odd, dict) or not isinstance(odd.get("double_chance"), dict):
        raise ValueError("254Scores double-chance opening odds are missing")

    if prediction.get("prediction_type") != "double_chance":
        raise ValueError("Only double_chance predictions are supported")

    prediction_choice = prediction.get("prediction_choice")
    selection = canonicalise(prediction_choice)
    opening_key = SCORES254_ODD_KEY[selection]
    opening_odds = round(float(fixture["odd"]["double_chance"][prediction_choice]),2)
    prediction_odds = round(float(prediction["prediction_odd"]),2)

    # Model probability for the selected double-chance signal is the sum of its
    # component outcome probabilities from the stored AI analysis.
    home = _probability(prediction.get("probability_home_win", 0))
    draw = _probability(prediction.get("probability_fixture_draw", 0))
    away = _probability(prediction.get("probability_away_win", 0))
    component_probability = {
        "1X": home + draw,
        "12": home + away,
        "X2": draw + away,
    }[selection]
    model_probability = min(component_probability, 1.0)

    return FixtureSignal(
        fixture_id=int(fixture["fixture_id"]),
        league_id=int(league["league_id"]),
        season=int(league["league_season"]),
        home_team=str(fixture["home_team_name"]),
        away_team=str(fixture["away_team_name"]),
        prediction_choice=str(prediction_choice),
        prediction_description=str(prediction.get("prediction_description", prediction_choice)),
        predicted_double_chance=selection,
        model_probability=model_probability,
        prediction_odds=prediction_odds,
        opening_odds=opening_odds,
    )
