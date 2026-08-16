import pytest

from src.decision_engine import reconcile, MATERIAL_THRESHOLD
from src.models import FixtureSignal, LatestMarket


# =========================================================
# Test helpers
# =========================================================

def create_signal(
    fixture_id=1570341,
    league_id=140,
    season=2026,
    home_team="Sevilla",
    away_team="Rayo Vallecano",
    prediction_choice="home_draw",
    prediction_description="Sevilla or draw",
    predicted_double_chance="home_draw",
    model_probability=0.80,
    prediction_odds=1.30,
    opening_odds=1.30,
):
    """
    Creates a FixtureSignal with sensible default values.

    Tests can override only the fields relevant to the
    scenario being tested.
    """
    return FixtureSignal(
        fixture_id=fixture_id,
        league_id=league_id,
        season=season,
        home_team=home_team,
        away_team=away_team,
        prediction_choice=prediction_choice,
        prediction_description=prediction_description,
        predicted_double_chance=predicted_double_chance,
        model_probability=model_probability,
        prediction_odds=prediction_odds,
        opening_odds=opening_odds,
    )


def create_market(
    fixture_id=1570341,
    double_chance="home_draw",
    decimal_odds=1.33,
    implied_probability=None,
    bookmaker_id=1,
    bookmaker_name="10Bet",
    updated_at="2026-08-15T10:37:21+00:00",
):
    """
    Creates a LatestMarket with sensible default values.

    If implied_probability is not supplied, calculate it
    directly from the decimal odds.
    """
    if implied_probability is None:
        implied_probability = 1.0 / decimal_odds

    return LatestMarket(
        fixture_id=fixture_id,
        double_chance=double_chance,
        decimal_odds=decimal_odds,
        implied_probability=implied_probability,
        bookmaker_id=bookmaker_id,
        bookmaker_name=bookmaker_name,
        updated_at=updated_at,
    )


# =========================================================
# Non-material movement
# =========================================================

def test_non_material_change_retains_model():
    """
    Opening:
        1 / 1.30 = 76.92%

    Latest:
        1 / 1.33 = 75.19%

    Movement:
        -1.73 percentage points

    This is below the 10% material threshold.
    """

    signal = create_signal(
        opening_odds=1.30,
        model_probability=0.80,
    )

    market = create_market(
        decimal_odds=1.33,
    )

    result = reconcile(signal, market)

    assert result.fixture_id == 1570341

    assert result.selected_source == "model"

    assert (
        result.selected_double_chance
        == "home_draw"
    )

    assert result.material_conflict is False

    assert (
        result.rule
        == "NON_MATERIAL_RETAIN_MODEL"
    )

    assert result.opening_probability == pytest.approx(
        1 / 1.30
    )

    assert result.latest_market_probability == pytest.approx(
        1 / 1.33
    )

    assert result.final_probability == pytest.approx(
        0.80
    )


# =========================================================
# Material conflict - model wins
# =========================================================

def test_material_conflict_model_wins():
    """
    Opening probability:
        1 / 1.40 = 71%

    Latest probability:
        1/ 1.20 = 83%

    Movement:
        -12 percentage points

    Model probability:
        75%

    Model 75% > Market 60%
    Therefore model wins.
    """

    signal = create_signal(
        opening_odds=1.25,
        model_probability=0.75,
    )

    market = create_market(
        decimal_odds=1 / 0.60,
        implied_probability=0.60,
    )

    result = reconcile(signal, market)

    assert result.material_conflict is True

    assert result.selected_source == "model"

    assert result.rule == "MATERIAL_MODEL"

    assert result.final_probability == pytest.approx(
        0.75
    )

    assert result.opening_probability == pytest.approx(
        0.80
    )

    assert result.latest_market_probability == pytest.approx(
        0.60
    )

    assert result.probability_change == pytest.approx(
        0.20
    )

    assert result.signed_probability_change == pytest.approx(
        -0.20
    )


# =========================================================
# Material conflict - market wins
# =========================================================

def test_material_conflict_market_wins():
    """
    Opening probability:
        1 / 2.00 = 50%

    Latest probability:
        75%

    Movement:
        +25 percentage points

    Model:
        60%

    Market 75% > Model 60%
    Therefore market wins.
    """

    signal = create_signal(
        opening_odds=2.00,
        model_probability=0.60,
    )

    market = create_market(
        decimal_odds=1 / 0.75,
        implied_probability=0.75,
    )

    result = reconcile(signal, market)

    assert result.material_conflict is True

    assert result.selected_source == "market"

    assert result.rule == "MATERIAL_MARKET"

    assert result.final_probability == pytest.approx(
        0.75
    )

    assert result.opening_probability == pytest.approx(
        0.50
    )

    assert result.latest_market_probability == pytest.approx(
        0.75
    )

    assert result.probability_change == pytest.approx(
        0.25
    )

    assert result.signed_probability_change == pytest.approx(
        0.25
    )


# =========================================================
# Exact 10% material threshold
# =========================================================

def test_exact_material_threshold_is_material():
    """
    Opening probability = 80%
    Latest probability = 70%

    Difference = exactly 10 percentage points.

    Your decision engine treats >= 10% as material.
    """

    signal = create_signal(
        opening_odds=1.25,
        model_probability=0.85,
    )

    market = create_market(
        decimal_odds=1 / 0.70,
        implied_probability=0.70,
    )

    result = reconcile(signal, market)

    assert result.probability_change == pytest.approx(
        MATERIAL_THRESHOLD
    )

    assert result.material_conflict is True


# =========================================================
# Below 10% threshold
# =========================================================

def test_change_below_material_threshold():
    """
    Opening probability = 80%
    Latest probability = 71%

    Movement = 9 percentage points.

    This should NOT be material.
    """

    signal = create_signal(
        opening_odds=1.25,
        model_probability=0.85,
    )

    market = create_market(
        decimal_odds=1 / 0.71,
        implied_probability=0.71,
    )

    result = reconcile(signal, market)

    assert result.probability_change == pytest.approx(
        0.09
    )

    assert result.material_conflict is False

    assert result.selected_source == "model"

    assert (
        result.rule
        == "NON_MATERIAL_RETAIN_MODEL"
    )


# =========================================================
# Positive market movement
# =========================================================

def test_positive_signed_probability_change():
    """
    Opening probability = 50%
    Latest probability = 70%

    Signed movement should be +20%.
    """

    signal = create_signal(
        opening_odds=2.00,
        model_probability=0.80,
    )

    market = create_market(
        decimal_odds=1 / 0.70,
        implied_probability=0.70,
    )

    result = reconcile(signal, market)

    assert result.signed_probability_change == pytest.approx(
        0.20
    )

    assert result.signed_probability_change > 0


# =========================================================
# Negative market movement
# =========================================================

def test_negative_signed_probability_change():
    """
    Opening probability = 80%
    Latest probability = 60%

    Signed movement should be -20%.
    """

    signal = create_signal(
        opening_odds=1.25,
        model_probability=0.80,
    )

    market = create_market(
        decimal_odds=1 / 0.60,
        implied_probability=0.60,
    )

    result = reconcile(signal, market)

    assert result.signed_probability_change == pytest.approx(
        -0.20
    )

    assert result.signed_probability_change < 0


# =========================================================
# Absolute probability movement
# =========================================================

def test_probability_change_is_absolute():
    """
    probability_change should always be positive even
    when signed_probability_change is negative.
    """

    signal = create_signal(
        opening_odds=1.25,       # 80%
        model_probability=0.80,
    )

    market = create_market(
        decimal_odds=1 / 0.60,
        implied_probability=0.60,
    )

    result = reconcile(signal, market)

    assert result.signed_probability_change == pytest.approx(
        -0.20
    )

    assert result.probability_change == pytest.approx(
        0.20
    )

    assert result.probability_change >= 0


# =========================================================
# Model equals market
# =========================================================

def test_model_wins_when_model_probability_equals_market():
    """
    The decision engine uses:

        model_probability >= latest_probability

    Therefore equality should select the model.
    """

    signal = create_signal(
        opening_odds=2.00,       # 50%
        model_probability=0.70,
    )

    market = create_market(
        decimal_odds=1 / 0.70,
        implied_probability=0.70,
    )

    result = reconcile(signal, market)

    # 50% -> 70% = 20pp, therefore material
    assert result.material_conflict is True

    assert result.selected_source == "model"

    assert result.rule == "MATERIAL_MODEL"

    assert result.final_probability == pytest.approx(
        0.70
    )


# =========================================================
# Fixture ID mismatch
# =========================================================

def test_fixture_id_mismatch_raises_error():
    signal = create_signal(
        fixture_id=1570341
    )

    market = create_market(
        fixture_id=999999
    )

    with pytest.raises(
        ValueError,
        match="Fixture IDs do not match"
    ):
        reconcile(signal, market)


# =========================================================
# Double chance mismatch
# =========================================================

def test_double_chance_mismatch_raises_error():
    signal = create_signal(
        predicted_double_chance="home_draw"
    )

    market = create_market(
        double_chance="away_draw"
    )

    with pytest.raises(
        ValueError,
        match="Double-chance selections do not match"
    ):
        reconcile(signal, market)


# =========================================================
# Invalid opening odds = 1
# =========================================================

def test_opening_odds_equal_one_raises_error():
    signal = create_signal(
        opening_odds=1.00
    )

    market = create_market()

    with pytest.raises(
        ValueError,
        match="Opening decimal odds must be greater than 1"
    ):
        reconcile(signal, market)


# =========================================================
# Invalid opening odds below 1
# =========================================================

def test_opening_odds_below_one_raises_error():
    signal = create_signal(
        opening_odds=0.90
    )

    market = create_market()

    with pytest.raises(
        ValueError,
        match="Opening decimal odds must be greater than 1"
    ):
        reconcile(signal, market)


# =========================================================
# Latest market bookmaker metadata
# =========================================================

def test_latest_market_contains_bookmaker_information():
    market = create_market(
        bookmaker_id=1,
        bookmaker_name="10Bet",
    )

    assert market.bookmaker_id == 1
    assert market.bookmaker_name == "10Bet"

    assert (
        market.updated_at
        == "2026-08-15T10:37:21+00:00"
    )


# =========================================================
# Latest implied probability from decimal odds
# =========================================================

def test_market_helper_calculates_implied_probability():
    market = create_market(
        decimal_odds=1.33
    )

    assert market.implied_probability == pytest.approx(
        1 / 1.33
    )