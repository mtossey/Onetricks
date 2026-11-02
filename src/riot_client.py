"""
Small client for the Riot API. Every collection script should make its
requests through this so rate limiting and retries happen in one place.

What it does:
- Adds the X-Riot-Token header to every request.
- Waits at least 1.3 seconds between requests. The personal key limit is
  100 requests per 2 minutes, and 1.3 seconds works out to about 92.
- On 429 (rate limited), waits for the number of seconds in the
  Retry-After header, then tries again.
- On 5xx (Riot server errors) or network errors, waits and retries a few times.
- Returns None on 404 so callers can skip data that does not exist.
- Logs problems to the console and to data/riot_client.log.
  The API key is sent in a header and is never logged.
"""

import logging
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

MIN_SECONDS_BETWEEN_CALLS = 1.3
MAX_ATTEMPTS = 5
LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "riot_client.log"

logger = logging.getLogger("riot_client")


def _setup_logging():
    # Only add handlers once, even if several clients are created
    if logger.handlers:
        return
    LOG_PATH.parent.mkdir(exist_ok=True)
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    for handler in (logging.StreamHandler(), logging.FileHandler(LOG_PATH, encoding="utf-8")):
        handler.setFormatter(formatter)
        logger.addHandler(handler)


class RiotClient:
    def __init__(self):
        load_dotenv()
        api_key = os.getenv("RIOT_API_KEY")
        if not api_key:
            raise RuntimeError("RIOT_API_KEY not found. Check that .env contains RIOT_API_KEY=...")

        # A Session reuses the connection and sends the header on every request
        self.session = requests.Session()
        self.session.headers["X-Riot-Token"] = api_key
        self._last_call_time = 0.0
        _setup_logging()

    def _wait_for_rate_limit(self):
        elapsed = time.monotonic() - self._last_call_time
        if elapsed < MIN_SECONDS_BETWEEN_CALLS:
            time.sleep(MIN_SECONDS_BETWEEN_CALLS - elapsed)
        self._last_call_time = time.monotonic()

    def get(self, host, path, params=None):
        """
        Make a GET request and return the parsed JSON, or None on 404.

        host: "americas" for account-v1 and match-v5 (regional routing),
              "na1" for league-v4 and champion-mastery-v4 (platform routing).
        path: the endpoint path, for example "/riot/account/v1/accounts/by-riot-id/Name/TAG".
        """
        url = f"https://{host}.api.riotgames.com{path}"

        for attempt in range(1, MAX_ATTEMPTS + 1):
            self._wait_for_rate_limit()

            try:
                response = self.session.get(url, params=params, timeout=10)
            except requests.RequestException as error:
                wait = 2 ** attempt
                logger.warning("Network error on %s (attempt %d/%d): %s. Waiting %ds.",
                               url, attempt, MAX_ATTEMPTS, error, wait)
                time.sleep(wait)
                continue

            status = response.status_code

            if status == 200:
                return response.json()

            if status == 404:
                logger.info("404 not found: %s", url)
                return None

            if status == 429:
                wait = int(response.headers.get("Retry-After", 10))
                logger.warning("429 rate limited on %s (attempt %d/%d). Waiting %ds.",
                               url, attempt, MAX_ATTEMPTS, wait)
                time.sleep(wait)
                continue

            if status >= 500:
                wait = 2 ** attempt
                logger.warning("%d server error on %s (attempt %d/%d). Waiting %ds.",
                               status, url, attempt, MAX_ATTEMPTS, wait)
                time.sleep(wait)
                continue

            # 400, 401, 403 and similar: retrying will not help, so stop here.
            # Riot's error body is a short status message and does not contain the key.
            logger.error("%d on %s: %s", status, url, response.text[:200])
            response.raise_for_status()

        raise RuntimeError(f"Gave up on {url} after {MAX_ATTEMPTS} attempts")


if __name__ == "__main__":
    # Self-test: one lookup that should succeed and one that should return 404
    from urllib.parse import quote

    client = RiotClient()

    account = client.get("americas", f"/riot/account/v1/accounts/by-riot-id/{quote('Scissorsbox')}/{quote('NA1')}")
    print("Real account found:", account is not None)
    if account:
        print("PUUID:", account["puuid"])

    missing = client.get("americas", "/riot/account/v1/accounts/by-riot-id/ThisNameShouldNotExist12345/ZZZZZ")
    print("Fake account returned None:", missing is None)
