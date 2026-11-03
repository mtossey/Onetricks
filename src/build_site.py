"""
Step 8: write the website's data from the database, as JSON files that the
React site in web/ loads:

    web/public/data/champions.json            the champion table (every role)
    web/public/data/champions/<IconId>.json   one champion page each
    web/public/data/tiers/<Tier>.png          ranked tier emblems (tier_emblems.py)

No API key and no live API calls. Champion names and icons come from Data
Dragon, Riot's public static data CDN, cached in data/ddragon/. Rerun this
whenever the database grows.

    python src/build_site.py
"""

import json
from datetime import date
from pathlib import Path

import pandas as pd
from champion_pages import write_champion_data
from champion_table import load_champion_table
from db import connect
from ddragon import champion_icon, load_ddragon_champions
from settings import SAMPLE_SIZE, WINDOW_SIZE
from tier_emblems import make_tier_emblems

ROOT = Path(__file__).resolve().parent.parent
# Gitignored, because the champion files contain Riot IDs
WEB_DATA_DIR = ROOT / "web" / "public" / "data"

SITE_NAME = "Mainstay"

# A win rate based on fewer games than this is shown as a dash
MIN_GAMES_SHOWN = 30


def win_rate_cell(row, group):
    """Win rate with its Wilson interval, or None when there are too few games."""
    games = int(row[f"{group}_games"])
    if games < MIN_GAMES_SHOWN:
        return {"games": games}
    return {"games": games, "wr": row[f"{group}_wr"], "low": row[f"{group}_low"], "high": row[f"{group}_high"]}


def page_summary(df):
    # Each non-remake match has 10 participants, so the all-players game
    # count divided by 10 is the number of matches in the sample's windows
    matches = int(df.all_games.sum() // 10)
    with connect() as conn:
        # Patch mix of the same matches: the sample players' window games
        patches = conn.execute("""
            SELECT m.patch, COUNT(*) * 1.0 / SUM(COUNT(*)) OVER () AS share
            FROM matches m
            WHERE m.is_remake = 0
              AND m.match_id IN (
                  SELECT match_id FROM player_matches
                  WHERE recency_rank < ?
                    AND puuid IN (SELECT puuid FROM players ORDER BY puuid LIMIT ?))
            GROUP BY m.patch ORDER BY COUNT(*) DESC LIMIT 2
        """, (WINDOW_SIZE, SAMPLE_SIZE)).fetchall()
        players = pd.read_sql_query(
            (ROOT / "sql" / "player_champions.sql").read_text(encoding="utf-8"), conn
        ).puuid.nunique()
    return {
        "matches": matches,
        "players": players,
        "top_patches": [p for p, _ in patches],
        "top_patch_share": sum(s for _, s in patches),
        "built": date.today().isoformat(),
    }


def main():
    version, ddragon = load_ddragon_champions()
    df = load_champion_table(role=None)  # every role's rows plus the 'ALL' rows
    summary = page_summary(df[df.role == "ALL"])

    # One data file per champion with at least one main (Build, Ranking, Counters)
    pages = write_champion_data(WEB_DATA_DIR / "champions", version, ddragon, SITE_NAME, summary["built"])
    make_tier_emblems(WEB_DATA_DIR / "tiers")

    # Each champion's games in all roles, to show what share a role is of them
    games_all_roles = df[df.role == "ALL"].set_index("champion_id").all_games

    champions = []
    for _, row in df.iterrows():
        # Skip roles a champion is rarely played in (Talon bot, for example)
        if row.role != "ALL" and row.all_games < MIN_GAMES_SHOWN:
            continue
        info = ddragon.get(int(row.champion_id), {"name": row.champion_name, "icon_id": row.champion_name})
        champions.append({
            "name": info["name"],
            "icon": champion_icon(version, info["icon_id"]),
            "role": row.role,
            "role_share": row.all_games / games_all_roles[row.champion_id],
            "mains": int(row.mains),
            "otps": int(row.otps),
            "main": win_rate_cell(row, "main"),
            "otp": win_rate_cell(row, "otp"),
            "all": win_rate_cell(row, "all"),
            "pick_rate": row.all_games / summary["matches"] if summary["matches"] else 0,
            "slug": pages.get(row.champion_id),  # React route /champion/<slug>, None without a page
        })

    payload = {
        "site_name": SITE_NAME,
        "summary": summary,
        "thresholds": {"min_games": MIN_GAMES_SHOWN},
        "champions": champions,
    }

    # allow_nan=False: browsers reject NaN in JSON, so fail here instead
    out = WEB_DATA_DIR / "champions.json"
    out.write_text(json.dumps(payload, allow_nan=False), encoding="utf-8")
    print(f"Wrote {out} ({len(games_all_roles)} champions, {len(champions)} champion-role rows, "
          f"{summary['players']} classified players, {summary['matches']} matches) "
          f"and {len(pages)} champion files")


if __name__ == "__main__":
    main()
