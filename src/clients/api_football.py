from __future__ import annotations
import time
import requests


class ApiFootballClient:
    def __init__(self, base_url: str, api_key: str, bet_id: int = 12, timeout: int = 15, max_retries: int = 2):
        self.base_url = base_url.rstrip("/")
        self.bet_id = bet_id
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"x-apisports-key": api_key})
        self.session.headers.update({"Accept": "application/json"})

    def fetch_latest_double_chance(self, fixture_id: int, season: int, league_id: int) -> dict:
        params = {
            "fixture": fixture_id,
            "season": season,
            "league": league_id,
            "bet": self.bet_id,
        }
        return self._get("/odds", params)

    def _get(self, path: str, params: dict) -> dict:
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.get(
                    f"{self.base_url}{path}", params=params, timeout=self.timeout
                )
                if response.status_code == 429 and attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                    continue
                response.raise_for_status()
                payload = response.json()
                if payload.get("errors"):
                    raise RuntimeError(str(payload["errors"]))
                return payload
            except (requests.RequestException, RuntimeError, ValueError) as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(2 ** attempt)
        raise RuntimeError(f"API-Football request failed: {last_error}")
