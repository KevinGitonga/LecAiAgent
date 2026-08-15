import argparse
import json

from src.agent import ReconciliationAgent, write_outputs
from src.clients.api_football import ApiFootballClient
from src.clients.scores254 import Scores254Client
from src.config import Settings
from src.state_store import StateStore


def build_agent(settings: Settings) -> ReconciliationAgent:
    return ReconciliationAgent(
        Scores254Client(
            settings.scores254_base_url,
            settings.scores254_api_key,
            settings.request_timeout_seconds,
            settings.max_retries,
        ),
        ApiFootballClient(
            settings.api_football_base_url,
            settings.api_football_key,
            settings.api_football_bet_id,
            settings.request_timeout_seconds,
            settings.max_retries,
        ),
        StateStore(settings.state_path),
    )


def main():
    parser = argparse.ArgumentParser(description="Reconcile 254Scores AI double-chance predictions with API-Football odds.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--fixture", type=int)
    group.add_argument("--fixtures", type=int, nargs="+")
    parser.add_argument("--league", type=int, help="Optional league override")
    parser.add_argument("--season", type=int, help="Optional season override")
    args = parser.parse_args()

    fixture_ids = [args.fixture] if args.fixture else args.fixtures
    settings = Settings()
    ranking, audit, errors = build_agent(settings).reconcile_batch(
        fixture_ids,
        league_override=args.league,
        season_override=args.season,
    )
    write_outputs(ranking, audit, settings.ranking_path, settings.audit_path)

    print(json.dumps({"ranking": ranking, "errors": errors}, indent=2))
    if not ranking:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
