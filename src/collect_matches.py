"""
Step 6: download match details for the match IDs in player_matches and save
them to matches, participants and raw_matches.

One API call per match. A match shared by several sampled players is only
downloaded once. Resumable: matches already stored (or recorded as
unavailable) are skipped, and each match is saved in its own transaction.

    python src/collect_matches.py                          # the study sample (see settings.py)
    python src/collect_matches.py --players 1500 --max-rank 50   # grow the sample later
    python src/collect_matches.py --players 50 --limit 3   # quick test: 3 matches
"""

import argparse
import json
import time
import zlib

from db import connect, init_db
from riot_client import RiotClient
from settings import SAMPLE_SIZE, WINDOW_SIZE

REGION = "americas"


def parse_match(data):
    """Turn one match-v5 response into a matches row and 10 participants rows."""
    info = data["info"]
    participants = info["participants"]

    match_row = (
        data["metadata"]["matchId"],
        info["gameVersion"],
        ".".join(info["gameVersion"].split(".")[:2]),  # '16.21.829.8620' -> '16.21'
        info["queueId"],
        info["gameCreation"],
        info["gameDuration"],
        int(any(p["gameEndedInEarlySurrender"] for p in participants)),
    )

    participant_rows = []
    for p in participants:
        # perks["styles"] holds two rune trees: primaryStyle and subStyle.
        # The first selection in the primary tree is the keystone.
        styles = {s["description"]: s for s in p["perks"]["styles"]}
        primary = styles["primaryStyle"]
        secondary = styles["subStyle"]

        participant_rows.append((
            data["metadata"]["matchId"],
            p["puuid"],
            p["teamId"],
            p["championId"],
            p["championName"],
            p["teamPosition"] or None,  # empty string in some games, store as NULL
            int(p["win"]),
            p["kills"], p["deaths"], p["assists"],
            p["totalMinionsKilled"], p["neutralMinionsKilled"],
            p["goldEarned"],
            p["totalDamageDealtToChampions"],
            p["visionScore"],
            p["item0"], p["item1"], p["item2"], p["item3"], p["item4"], p["item5"], p["item6"],
            p["summoner1Id"], p["summoner2Id"],
            primary["style"], primary["selections"][0]["perk"], secondary["style"],
        ))

    return match_row, participant_rows


def save_match(conn, data):
    """Insert one match into all three tables. Caller handles the transaction."""
    match_row, participant_rows = parse_match(data)
    conn.execute("INSERT INTO matches VALUES (?, ?, ?, ?, ?, ?, ?)", match_row)
    conn.executemany(
        "INSERT INTO participants VALUES (" + ", ".join("?" * 27) + ")",
        participant_rows,
    )
    compressed = zlib.compress(json.dumps(data, separators=(",", ":")).encode("utf-8"), 9)
    conn.execute("INSERT INTO raw_matches VALUES (?, ?)", (match_row[0], compressed))


def matches_to_download(max_rank, num_players):
    """
    Match IDs still needed: in the chosen players' newest max_rank games,
    and not already stored or marked unavailable.
    """
    # Ordering players by PUUID gives an effectively random but repeatable
    # subset, because PUUIDs are random strings. This keeps a small test
    # batch from being only Challenger players.
    query = """
        WITH chosen_players AS (
            SELECT puuid FROM players ORDER BY puuid LIMIT ?
        )
        SELECT DISTINCT pm.match_id
        FROM player_matches pm
        JOIN chosen_players cp ON cp.puuid = pm.puuid
        WHERE pm.recency_rank < ?
          AND pm.match_id NOT IN (SELECT match_id FROM matches)
          AND pm.match_id NOT IN (SELECT match_id FROM unavailable_matches)
        -- Match IDs increase over time, so this downloads the newest games
        -- first. If a run is stopped early, what we have is the most recent data.
        ORDER BY CAST(SUBSTR(pm.match_id, 5) AS INTEGER) DESC
    """
    with connect() as conn:
        # LIMIT -1 means no limit in SQLite
        return [row[0] for row in conn.execute(query, (num_players or -1, max_rank))]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-rank", type=int, default=WINDOW_SIZE,
                        help=f"download each player's newest N games (default {WINDOW_SIZE})")
    parser.add_argument("--players", type=int, default=SAMPLE_SIZE,
                        help=f"only use this many players (default {SAMPLE_SIZE})")
    parser.add_argument("--limit", type=int, help="only download this many matches")
    args = parser.parse_args()

    init_db()  # adds any new tables from schema.sql, keeps existing data
    todo = matches_to_download(args.max_rank, args.players)
    if args.limit:
        todo = todo[:args.limit]
    print(f"{len(todo)} matches to download")

    client = RiotClient()
    start_time = time.monotonic()

    for i, match_id in enumerate(todo, start=1):
        data = client.get(REGION, f"/lol/match/v5/matches/{match_id}")

        with connect() as conn:
            if data is None:
                conn.execute("INSERT OR IGNORE INTO unavailable_matches (match_id) VALUES (?)", (match_id,))
            else:
                save_match(conn, data)

        if i % 50 == 0 or i == len(todo) or len(todo) <= 25:
            elapsed = time.monotonic() - start_time
            remaining = elapsed / i * (len(todo) - i)
            print(f"[{i}/{len(todo)}] {match_id}  "
                  f"(elapsed {elapsed / 60:.1f} min, about {remaining / 60:.0f} min left)")

    print("Done.")


if __name__ == "__main__":
    main()
