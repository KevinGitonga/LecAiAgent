import json
from pathlib import Path

import pytest

from src.agent import ReconciliationAgent, write_outputs
from src.models import Decision, FixtureSignal, LatestMarket


# =========================================================
# Fake dependencies
# =========================================================

class FakeScoresClient:
    def fetch_fixture(self, fixture_id):
        return {
            "data": [
                {
                    "fixture_id": str(fixture_id),
                    "home_team_name": "Sevilla",
                    "away_team_name": "Rayo Vallecano",
                    "prediction": {
                        "prediction_choice": "home_draw",
                        "prediction_description": "Sevilla or draw",
                        "prediction_odd": "1.30",
                        "probability_home_win": "50",
                        "probability_fixture_draw": "50",
                        "probability_away_win": "0",
                    },
                    "league": {
                        "league_id": "140",
                        "league_season": "2026",
                    },
                    "odd": {
                        "double_chance": {
                            "home_draw": "1.30",
                            "home_away": "1.30",
                            "away_draw": "1.62",
                        }
                    },
                }
            ]
        }


class FakeFootballClient:
    def __init__(self):
        self.last_call = None

    def fetch_latest_double_chance(
        self,
        fixture_id,
        season,
        league_id,
    ):
        self.last_call = {
            "fixture_id": fixture_id,
            "season": season,
            "league_id": league_id,
        }

        return {
            "response": [
                {
                    "fixture": {
                        "id": fixture_id
                    },
                    "update": "2026-08-15T10:37:21+00:00",
                    "bookmakers": [
                        {
                            "id": 1,
                            "name": "10Bet",
                            "bets": [
                                {
                                    "id": 12,
                                    "name": "Double Chance",
                                    "values": [
                                        {
                                            "value": "Home/Draw",
                                            "odd": "1.33"
                                        },
                                        {
                                            "value": "Home/Away",
                                            "odd": "1.30"
                                        },
                                        {
                                            "value": "Draw/Away",
                                            "odd": "1.62"
                                        },
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ]
        }


class FakeStateStore:
    def __init__(self):
        self.data = {}
        self.saved = False

    def get(self, fixture_id):
        return self.data.get(fixture_id)

    def put(self, fixture_id, value):
        self.data[fixture_id] = value

    def save(self):
        self.saved = True


# =========================================================
# Fixture reconciliation
# =========================================================

def test_reconcile_fixture_returns_ranking_item_and_audit():
    scores_client = FakeScoresClient()
    football_client = FakeFootballClient()
    state_store = FakeStateStore()

    agent = ReconciliationAgent(
        scores_client,
        football_client,
        state_store,
    )

    item, audit = agent.reconcile_fixture(1570341)

    assert item["fixture_id"] == 1570341
    assert item["event"] == "Sevilla vs Rayo Vallecano"
    assert item["prediction"] == "Sevilla or draw"
    assert item["double_chance"] == "home_draw"

    assert "final_probability" in item
    assert "rule" in item

    assert audit["fixture_id"] == 1570341
    assert audit["event"] == "Sevilla vs Rayo Vallecano"

    assert audit["league_id"] == 140
    assert audit["season"] == 2026


def test_reconcile_fixture_calls_football_api_with_correct_values():
    football_client = FakeFootballClient()

    agent = ReconciliationAgent(
        FakeScoresClient(),
        football_client,
        FakeStateStore(),
    )

    agent.reconcile_fixture(1570341)

    assert football_client.last_call == {
        "fixture_id": 1570341,
        "season": 2026,
        "league_id": 140,
    }




def test_reconcile_fixture_uses_league_and_season_overrides():
    football_client = FakeFootballClient()

    agent = ReconciliationAgent(
        FakeScoresClient(),
        football_client,
        FakeStateStore(),
    )

    agent.reconcile_fixture(
        1570341,
        league_override=999,
        season_override=2030,
    )

    assert football_client.last_call == {
        "fixture_id": 1570341,
        "season": 2030,
        "league_id": 999,
    }


def test_reconcile_fixture_updates_state_store():
    state_store = FakeStateStore()

    agent = ReconciliationAgent(
        FakeScoresClient(),
        FakeFootballClient(),
        state_store,
    )

    _, audit = agent.reconcile_fixture(1570341)

    assert 1570341 in state_store.data

    assert (
        state_store.data[1570341]["fixture_id"]
        == 1570341
    )

    assert state_store.data[1570341] == audit


def test_reconcile_fixture_audit_contains_market_data():
    agent = ReconciliationAgent(
        FakeScoresClient(),
        FakeFootballClient(),
        FakeStateStore(),
    )

    _, audit = agent.reconcile_fixture(1570341)

    latest = audit["latest_market"]

    assert latest["bookmaker_id"] == 1
    assert latest["bookmaker_name"] == "10Bet"
    assert latest["decimal_odds"] == pytest.approx(1.33)

    assert latest["implied_probability"] == pytest.approx(
        1 / 1.33
    )

    assert (
        latest["updated_at"]
        == "2026-08-15T10:37:21+00:00"
    )


def test_audit_does_not_contain_model_reliability():
    agent = ReconciliationAgent(
        FakeScoresClient(),
        FakeFootballClient(),
        FakeStateStore(),
    )

    _, audit = agent.reconcile_fixture(1570341)

    assert "model_reliability" not in audit
    assert "adjusted_model_score" not in audit

    assert (
        "model_reliability"
        not in audit["prediction"]
    )


def test_reconcile_batch_ranks_by_final_probability(monkeypatch):
    agent = ReconciliationAgent(
        FakeScoresClient(),
        FakeFootballClient(),
        FakeStateStore(),
    )

    results = {
        1: (
            {
                "fixture_id": 1,
                "event": "A vs B",
                "prediction": "A or draw",
                "double_chance": "home_draw",
                "source": "model",
                "final_probability": 0.70,
                "rule": "TEST",
            },
            {"fixture_id": 1},
        ),
        2: (
            {
                "fixture_id": 2,
                "event": "C vs D",
                "prediction": "C or draw",
                "double_chance": "home_draw",
                "source": "model",
                "final_probability": 0.90,
                "rule": "TEST",
            },
            {"fixture_id": 2},
        ),
        3: (
            {
                "fixture_id": 3,
                "event": "E vs F",
                "prediction": "E or draw",
                "double_chance": "home_draw",
                "source": "model",
                "final_probability": 0.80,
                "rule": "TEST",
            },
            {"fixture_id": 3},
        ),
    }

    monkeypatch.setattr(
        agent,
        "reconcile_fixture",
        lambda fixture_id, league_override=None, season_override=None:
            results[fixture_id],
    )

    ranking, audit, errors = agent.reconcile_batch(
        [1, 2, 3]
    )

    assert errors == []

    assert ranking[0]["fixture_id"] == 2
    assert ranking[1]["fixture_id"] == 3
    assert ranking[2]["fixture_id"] == 1

    assert ranking[0]["rank"] == 1
    assert ranking[1]["rank"] == 2
    assert ranking[2]["rank"] == 3

def test_reconcile_batch_collects_errors(monkeypatch):
    state_store = FakeStateStore()

    agent = ReconciliationAgent(
        FakeScoresClient(),
        FakeFootballClient(),
        state_store,
    )

    def fake_reconcile(
        fixture_id,
        league_override=None,
        season_override=None,
    ):
        if fixture_id == 2:
            raise ValueError("Something went wrong")

        return (
            {
                "fixture_id": fixture_id,
                "event": "Test",
                "prediction": "Test",
                "double_chance": "home_draw",
                "source": "model",
                "final_probability": 0.80,
                "rule": "TEST",
            },
            {
                "fixture_id": fixture_id
            },
        )

    monkeypatch.setattr(
        agent,
        "reconcile_fixture",
        fake_reconcile,
    )

    ranking, audit, errors = agent.reconcile_batch(
        [1, 2, 3]
    )

    assert len(ranking) == 2
    assert len(audit) == 2
    assert len(errors) == 1

    assert errors[0]["fixture_id"] == 2

    assert (
        errors[0]["error"]
        == "Something went wrong"
    )


def test_reconcile_batch_saves_state(monkeypatch):
    state_store = FakeStateStore()

    agent = ReconciliationAgent(
        FakeScoresClient(),
        FakeFootballClient(),
        state_store,
    )

    monkeypatch.setattr(
        agent,
        "reconcile_fixture",
        lambda fixture_id, league_override=None, season_override=None: (
            {
                "fixture_id": fixture_id,
                "event": "Test",
                "prediction": "Test",
                "double_chance": "home_draw",
                "source": "model",
                "final_probability": 0.80,
                "rule": "TEST",
            },
            {
                "fixture_id": fixture_id
            },
        ),
    )

    agent.reconcile_batch([1])

    assert state_store.saved is True


def test_write_outputs_creates_files(tmp_path):
    ranking_path = tmp_path / "reconciled_ranking.json"
    audit_path = tmp_path / "audit.json"

    ranking = [
        {
            "rank": 1,
            "fixture_id": 1570341,
            "final_probability": 0.80,
        }
    ]

    audit = [
        {
            "fixture_id": 1570341,
            "event": "Sevilla vs Rayo Vallecano",
        }
    ]

    write_outputs(
        ranking,
        audit,
        ranking_path,
        audit_path,
    )

    assert ranking_path.exists()
    assert audit_path.exists()


def test_write_outputs_appends_previous_runs(tmp_path):
    ranking_path = tmp_path / "reconciled_ranking.json"
    audit_path = tmp_path / "audit.json"

    write_outputs(
        [{"fixture_id": 1}],
        [{"fixture_id": 1}],
        ranking_path,
        audit_path,
    )

    write_outputs(
        [{"fixture_id": 2}],
        [{"fixture_id": 2}],
        ranking_path,
        audit_path,
    )

    ranking_history = json.loads(
        ranking_path.read_text(
            encoding="utf-8"
        )
    )

    audit_history = json.loads(
        audit_path.read_text(
            encoding="utf-8"
        )
    )

    assert len(ranking_history) == 2
    assert len(audit_history) == 2

    assert (
        ranking_history[0]["ranking"][0]["fixture_id"]
        == 1
    )

    assert (
        ranking_history[1]["ranking"][0]["fixture_id"]
        == 2
    )

    assert (
        audit_history[0]["records"][0]["fixture_id"]
        == 1
    )

    assert (
        audit_history[1]["records"][0]["fixture_id"]
        == 2
    )


def test_write_outputs_adds_timestamp(tmp_path):
    ranking_path = tmp_path / "reconciled_ranking.json"
    audit_path = tmp_path / "audit.json"

    write_outputs(
        [{"fixture_id": 1}],
        [{"fixture_id": 1}],
        ranking_path,
        audit_path,
    )

    ranking_history = json.loads(
        ranking_path.read_text()
    )

    audit_history = json.loads(
        audit_path.read_text()
    )

    assert "timestamp" in ranking_history[0]
    assert "timestamp" in audit_history[0]                        