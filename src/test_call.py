"""
Test call to verify the Riot API key, request header, and regional routing.

Calls account-v1 by-riot-id, which uses a regional host (americas),
and prints only the HTTP status code and the PUUID. The API key is never printed.
"""

import os
from urllib.parse import quote

import requests
from dotenv import load_dotenv

# Riot ID to look up (gameName#tagLine)
GAME_NAME = "Scissorsbox"
TAG_LINE = "NA1"
REGION_HOST = "https://americas.api.riotgames.com"

load_dotenv()
api_key = os.getenv("RIOT_API_KEY")
if not api_key:
    raise SystemExit("RIOT_API_KEY not found. Check that .env contains RIOT_API_KEY=...")

# quote() encodes spaces and special characters that can appear in Riot IDs
url = (
    f"{REGION_HOST}/riot/account/v1/accounts/by-riot-id/"
    f"{quote(GAME_NAME)}/{quote(TAG_LINE)}"
)

response = requests.get(url, headers={"X-Riot-Token": api_key}, timeout=10)

print("Status code:", response.status_code)
if response.status_code == 200:
    print("PUUID:", response.json()["puuid"])
