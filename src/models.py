from dataclasses import asdict, dataclass
from typing import Any

@dataclass(frozen=True)
class FixtureSignal:
    fixture_id: int
    league_id: int
    season: int
    home_team: str
    away_team: str
    prediction_choice: str
    prediction_description: str
    predicted_double_chance: str
    model_probability: float
    prediction_odds: float
    opening_odds: float

@dataclass(frozen=True)
class LatestMarket:
    fixture_id: int
    double_chance: str
    decimal_odds: float
    implied_probability: float
    bookmaker_id: int | None
    bookmaker_name: str
    updated_at: str | None

@dataclass(frozen=True)
class Decision:
    fixture_id: int
    selected_source: str
    selected_double_chance: str
    final_probability: float
    opening_probability: float
    latest_market_probability: float
    probability_change: float
    signed_probability_change: float
    material_conflict: bool
    model_probability: float
    rule: str
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
