"""
Step 5: get each player's most recent ranked solo match IDs and store them
in player_matches, newest first (recency_rank 0 = most recent game).

One API call per player (up to 100 IDs per call). Resumable: players with a
match_ids_fetched_at value are skipped, and each player is saved in its own
transaction, so stopping the script (Ctrl+C) never leaves a half-saved player.

    python src/collect_match_ids.py            # all remaining players
    python src/collect_match_ids.py --limit 5  # only the next 5, for testing
"""

import argparse
import time

from db import connect
from riot_client import RiotClient

REGION = "americas"
MATCHES_PER_PLAYER = 100  # the API maximum for one call
RANKED_SOLO_QUEUE = 420


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="only process this many players")
    args = parser.parse_args()

    with connect() as conn:
        todo = [row[0] for row in conn.execute(
            "SELECT puuid FROM players WHERE match_ids_fetched_at IS NULL ORDER BY rowid"
        )]
    if args.limit:
        todo = todo[:args.limit]
    print(f"{len(todo)} players to process")

    client = RiotClient()
    start_time = time.monotonic()

    for i, puuid in enumerate(todo, start=1):
        match_ids = client.get(
            REGION,
            f"/lol/match/v5/matches/by-puuid/{puuid}/ids",
            {"queue": RANKED_SOLO_QUEUE, "start": 0, "count": MATCHES_PER_PLAYER},
        )
        # None means 404 (player not found). Mark them as done with no matches
        # so we do not retry them forever.
        match_ids = match_ids or []

        # "with conn" commits both statements together, or neither if something fails
        with connect() as conn:
            conn.executemany(
                "INSERT OR IGNORE INTO player_matches (puuid, match_id, recency_rank) VALUES (?, ?, ?)",
                [(puuid, match_id, rank) for rank, match_id in enumerate(match_ids)],
            )
            conn.execute(
                "UPDATE players SET match_ids_fetched_at = datetime('now') WHERE puuid = ?",
                (puuid,),
            )

        if i % 25 == 0 or i == len(todo) or len(todo) <= 25:
            elapsed = time.monotonic() - start_time
            remaining = elapsed / i * (len(todo) - i)
            print(f"[{i}/{len(todo)}] {len(match_ids)} match IDs  "
                  f"(elapsed {elapsed / 60:.1f} min, about {remaining / 60:.0f} min left)")

    print("Done.")


if __name__ == "__main__":
    main()
