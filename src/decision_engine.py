from src.models import Decision, FixtureSignal, LatestMarket

MATERIAL_THRESHOLD = 0.10


def reconcile(signal: FixtureSignal, market: LatestMarket) -> Decision:
    if signal.fixture_id != market.fixture_id:
        raise ValueError("Fixture IDs do not match")
    if signal.predicted_double_chance != market.double_chance:
        raise ValueError("Double-chance selections do not match")
    if signal.opening_odds <= 1:
        raise ValueError("Opening decimal odds must be greater than 1")

    opening_probability = 1.0 / signal.opening_odds
    latest_probability = market.implied_probability
    signed_change = latest_probability - opening_probability
    probability_change = abs(signed_change)
    material = probability_change >= MATERIAL_THRESHOLD

    if not material:
            source = "model"
            final_probability = signal.model_probability
            rule = "NON_MATERIAL_RETAIN_MODEL"

            rationale = (
                f"Market implied probability moved {signed_change:+.1%} "
                f"({probability_change:.1%} absolute), below the "
                f"{MATERIAL_THRESHOLD:.0%} threshold; "
                f"retain the initial AI signal."
            )

    elif signal.model_probability >= latest_probability:
            source = "model"
            final_probability = signal.model_probability
            rule = "MATERIAL_MODEL"

            rationale = (
                f"Model probability {signal.model_probability:.1%} "
                f"is at least the latest market probability "
                f"{latest_probability:.1%}; model signal retained."
            )

    else:
            source = "market"
            final_probability = latest_probability
            rule = "MATERIAL_MARKET"

            rationale = (
                f"Latest market probability {latest_probability:.1%} "
                f"exceeds model probability "
                f"{signal.model_probability:.1%}; market signal selected."
            )

    return Decision(
            fixture_id=signal.fixture_id,
            selected_source=source,
            selected_double_chance=signal.predicted_double_chance,
            final_probability=final_probability,
            opening_probability=opening_probability,
            latest_market_probability=latest_probability,
            probability_change=probability_change,
            signed_probability_change=signed_change,
            material_conflict=material,
            model_probability=signal.model_probability,
            rule=rule,
            rationale=rationale,
        )
