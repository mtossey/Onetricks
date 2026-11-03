"""
Download match timelines for the champion pages' build order, starting items
and skill order. One API call per match, only for matches where a main or OTP
played their champion (the games in sql/main_games.sql).

A timeline is about 400 KB, so only item and skill events are kept, for all
10 players (timeline_events). Resumable: matches already in the timelines
table are skipped, and each match is saved in its own transaction.

    python src/collect_timelines.py              # everything still missing
    python src/collect_timelines.py --limit 3    # quick test: 3 matches
"""

import argparse
import time

from champion_pages import load_main_games
from db import connect, init_db
from riot_client import RiotClient

REGION = "americas"
KEPT_EVENTS = {"ITEM_PURCHASED", "ITEM_SOLD", "ITEM_UNDO", "SKILL_LEVEL_UP"}


def parse_events(match_id, data):
    """timeline_events rows for one timeline response."""
    # Events name players by participantId (1 to 10); this maps them to PUUIDs.
    # participantId 0 is not a player (it appears in a few start-of-game events).
    puuid_of = {p["participantId"]: p["puuid"] for p in data["info"]["participants"]}
    rows = []
    seq = 0
    for frame in data["info"]["frames"]:
        for e in frame["events"]:
            seq += 1  # counts every event, so seq keeps the timeline's order
            if e["type"] not in KEPT_EVENTS or e.get("participantId") not in puuid_of:
                continue
            if e["type"] == "ITEM_UNDO":
                item_id, after_id = e.get("beforeId"), e.get("afterId")
            else:
                item_id, after_id = e.get("itemId"), None
            rows.append((
                match_id, puuid_of[e["participantId"]], seq, e["timestamp"], e["type"],
                item_id, after_id, e.get("skillSlot"), e.get("levelUpType"),
            ))
    return rows


def timelines_to_download():
    """Matches with a main's game, newest first, minus those already fetched."""
    games = load_main_games()
    with connect() as conn:
        done = {row[0] for row in conn.execute("SELECT match_id FROM timelines")}
    todo = sorted(set(games.match_id) - done, key=lambda m: int(m.split("_")[1]), reverse=True)
    return todo


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="only download this many timelines")
    args = parser.parse_args()

    init_db()  # creates the timeline tables if this database predates them
    todo = timelines_to_download()
    if args.limit is not None:  # "is not None", so --limit 0 means zero, not "no limit"
        todo = todo[:args.limit]
    print(f"{len(todo)} timelines to download")

    client = RiotClient()
    start_time = time.monotonic()

    for i, match_id in enumerate(todo, start=1):
        data = client.get(REGION, f"/lol/match/v5/matches/{match_id}/timeline")

        with connect() as conn:
            if data is None:
                conn.execute("INSERT INTO timelines (match_id, available) VALUES (?, 0)", (match_id,))
            else:
                conn.execute("INSERT INTO timelines (match_id, available) VALUES (?, 1)", (match_id,))
                conn.executemany("INSERT INTO timeline_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                 parse_events(match_id, data))

        if i % 50 == 0 or i == len(todo) or len(todo) <= 25:
            elapsed = time.monotonic() - start_time
            remaining = elapsed / i * (len(todo) - i)
            print(f"[{i}/{len(todo)}] {match_id}  "
                  f"(elapsed {elapsed / 60:.1f} min, about {remaining / 60:.0f} min left)")

    print("Done.")


if __name__ == "__main__":
    main()
