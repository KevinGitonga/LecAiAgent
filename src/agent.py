from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from src.decision_engine import reconcile
from src.parsers.api_football import parse_latest_market
from src.parsers.scores254 import parse_fixture

class ReconciliationAgent:
    def __init__(self, scores_client, football_client, state_store):
        self.scores_client = scores_client
        self.football_client = football_client
        self.state_store = state_store

    def reconcile_fixture(self, fixture_id: int, league_override=None, season_override=None):
        signal = parse_fixture(self.scores_client.fetch_fixture(fixture_id))
        league_id = int(league_override or signal.league_id)
        season = int(season_override or signal.season)
        latest_payload = self.football_client.fetch_latest_double_chance(signal.fixture_id, season, league_id)
        market = parse_latest_market(latest_payload, signal.fixture_id, signal.predicted_double_chance)
        decision = reconcile(signal, market)
        previous_state = self.state_store.get(signal.fixture_id)
        audit = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "fixture_id": signal.fixture_id,
            "event": f"{signal.home_team} vs {signal.away_team}",
            "league_id": league_id,
            "season": season,
            "prediction": {
                "choice": signal.prediction_choice,
                "canonical_double_chance": signal.predicted_double_chance,
                "description": signal.prediction_description,
                "prediction_odd": signal.prediction_odds,
                "model_probability": signal.model_probability
            },
            "opening_market": {"decimal_odds": signal.opening_odds, "implied_probability": decision.opening_probability},
            "latest_market": {
                "bookmaker_id": market.bookmaker_id,
                "bookmaker_name": market.bookmaker_name,
                "updated_at": market.updated_at,
                "decimal_odds": market.decimal_odds,
                "implied_probability": market.implied_probability,
            },
            "previous_state": previous_state,
            "decision": decision.to_dict(),
        }
        self.state_store.put(signal.fixture_id, audit)
        return {
            "fixture_id": signal.fixture_id,
            "event": audit["event"],
            "prediction": signal.prediction_description,
            "double_chance": decision.selected_double_chance,
            "source": decision.selected_source,
            "final_probability": decision.final_probability,
            "rule": decision.rule,
        }, audit

    def reconcile_batch(self, fixture_ids, league_override=None, season_override=None):
        ranking, audit, errors = [], [], []
        for fixture_id in fixture_ids:
            try:
                item, record = self.reconcile_fixture(fixture_id, league_override, season_override)
                ranking.append(item); audit.append(record)
            except Exception as exc:
                errors.append({"fixture_id": fixture_id, "error": str(exc)})
        ranking.sort(key=lambda row: row["final_probability"], reverse=True)
        for index, row in enumerate(ranking, 1): row["rank"] = index
        self.state_store.save()
        return ranking, audit, errors

def write_outputs(ranking, audit, ranking_path, audit_path):
    for path, value in ((ranking_path, ranking), (audit_path, audit)):
        output = Path(path); output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
