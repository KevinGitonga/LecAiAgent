import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    scores254_base_url: str = os.getenv(
        "SCORES254_BASE_URL", "https://adminpanel.254scores.com/api"
    )
    scores254_api_key: str = os.getenv("SCORES254_API_KEY", "")
    api_football_base_url: str = os.getenv(
        "API_FOOTBALL_BASE_URL", "https://v3.football.api-sports.io"
    )
    api_football_key: str = os.getenv("API_FOOTBALL_KEY", "")
    api_football_bet_id: int = int(os.getenv("API_FOOTBALL_BET_ID", "12"))
    request_timeout_seconds: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "15"))
    max_retries: int = int(os.getenv("MAX_RETRIES", "2"))
    state_path: str = os.getenv("STATE_PATH", "output/state.json")
    audit_path: str = os.getenv("AUDIT_PATH", "output/audit.json")
    ranking_path: str = os.getenv("RANKING_PATH", "output/reconciled_ranking.json")
