from __future__ import annotations
import time
import requests


class Scores254Client:
    def __init__(self, base_url: str, api_key: str, timeout: int = 15, max_retries: int = 2):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})
        self.session.headers.update({"Accept": "application/json"})

    def fetch_fixture(self, fixture_id: int) -> dict:
        params = [
            ("filters[fixture_id]", str(fixture_id)),
            ("populate", "odd.double_chance"),
            ("populate[1]", "prediction"),
            ("populate[2]", "league"),
        ]
        return self._get("/fixtures", params)

    def _get(self, path: str, params) -> dict:
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.get(
                    f"{self.base_url}{path}", params=params, timeout=self.timeout
                )
                response.raise_for_status()
                return response.json()
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(2 ** attempt)
        raise RuntimeError(f"254Scores request failed: {last_error}")
