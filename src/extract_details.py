"""
Fill participant_details (full rune pages and Riot IDs) from the compressed
match JSON in raw_matches. No API calls.

Safe to rerun: matches that already have details are skipped, so after
downloading more matches this only processes the new ones.

    python src/extract_details.py
"""

import json
import zlib

from db import connect, init_db


def parse_details(data):
    """One participant_details row per player in a match-v5 response."""
    rows = []
    for p in data["info"]["participants"]:
        styles = {s["description"]: s for s in p["perks"]["styles"]}
        primary = [s["perk"] for s in styles["primaryStyle"]["selections"]]
        secondary = [s["perk"] for s in styles["subStyle"]["selections"]]
        shards = p["perks"]["statPerks"]
        rows.append((
            data["metadata"]["matchId"],
            p["puuid"],
            p.get("riotIdGameName"),
            p.get("riotIdTagline"),
            styles["primaryStyle"]["style"],
            *primary,                      # 4 runes, the first is the keystone
            styles["subStyle"]["style"],
            *secondary,                    # 2 runes
            shards["offense"], shards["flex"], shards["defense"],
        ))
    return rows


def main():
    init_db()  # creates participant_details if this database predates it
    with connect() as conn:
        todo = conn.execute("""
            SELECT r.match_id, r.json_zlib
            FROM raw_matches r
            WHERE r.match_id NOT IN (SELECT match_id FROM participant_details)
        """).fetchall()
        print(f"{len(todo)} matches to extract")

        for i, (match_id, blob) in enumerate(todo, start=1):
            data = json.loads(zlib.decompress(blob))
            conn.executemany(
                "INSERT OR IGNORE INTO participant_details VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                parse_details(data))
            if i % 2000 == 0:
                print(f"  {i} done")
        conn.commit()

        count = conn.execute("SELECT COUNT(*) FROM participant_details").fetchone()[0]
        print(f"participant_details now has {count} rows")


if __name__ == "__main__":
    main()
