"""
Step 4: build the player pool and save it to the players table.

Pool: every NA Challenger and Grandmaster player in ranked solo queue,
plus a random sample of Master players. Three API calls in total, because
each apex league endpoint returns the whole tier at once.

The pool is only drawn once. If the players table already has rows, the
script stops without changing anything, so a rerun on a later day cannot
mix two different snapshots of the ladder.

    python src/collect_players.py
"""

import random

from db import connect, init_db
from riot_client import RiotClient

PLATFORM = "na1"
QUEUE = "RANKED_SOLO_5x5"
MASTER_SAMPLE_SIZE = 1000
RANDOM_SEED = 42  # fixed so the Master sample can be reproduced from the same list

LEAGUE_ENDPOINTS = {
    "CHALLENGER": "challengerleagues",
    "GRANDMASTER": "grandmasterleagues",
    "MASTER": "masterleagues",
}


def fetch_tier(client, tier):
    data = client.get(PLATFORM, f"/lol/league/v4/{LEAGUE_ENDPOINTS[tier]}/by-queue/{QUEUE}")
    return data["entries"]


def main():
    init_db()

    with connect() as conn:
        existing = conn.execute("SELECT COUNT(*) FROM players").fetchone()[0]
    if existing:
        print(f"players table already has {existing} rows. Pool is already drawn, nothing to do.")
        return

    client = RiotClient()
    entries_by_tier = {tier: fetch_tier(client, tier) for tier in LEAGUE_ENDPOINTS}
    for tier, entries in entries_by_tier.items():
        print(f"{tier}: {len(entries)} players on the ladder")

    # Sort before sampling so the same ladder and seed always give the same sample
    masters = sorted(entries_by_tier["MASTER"], key=lambda e: e["puuid"])
    entries_by_tier["MASTER"] = random.Random(RANDOM_SEED).sample(masters, MASTER_SAMPLE_SIZE)

    rows = [
        (e["puuid"], tier, e["leaguePoints"], e["wins"], e["losses"])
        for tier, entries in entries_by_tier.items()
        for e in entries
    ]

    with connect() as conn:
        # OR IGNORE skips a duplicate PUUID if a player appears in two lists
        # (possible if they were promoted while we were pulling the lists)
        conn.executemany(
            "INSERT OR IGNORE INTO players (puuid, tier, league_points, wins, losses) "
            "VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        print("\nSaved to players table:")
        for tier, count in conn.execute(
            "SELECT tier, COUNT(*) FROM players GROUP BY tier ORDER BY MIN(league_points) DESC"
        ):
            print(f"  {tier}: {count}")


if __name__ == "__main__":
    main()
