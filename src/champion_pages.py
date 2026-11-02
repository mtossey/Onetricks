"""
Champion pages: every game a main or OTP played on their champion
(sql/main_games.sql), written into one page per champion with its Build,
Ranking and Counters tabs. build_site.py calls write_champion_pages().

    python src/champion_pages.py      # prints a short check of the data
"""

import json
from pathlib import Path

import pandas as pd

from db import connect
from ddragon import SHARDS, champion_icon, load_items, load_runes, load_summoner_spells
from settings import WINDOW_SIZE

SRC = Path(__file__).resolve().parent
SQL_DIR = SRC.parent / "sql"
TEMPLATE_PATH = SRC / "champion_template.html"


def load_main_games():
    with connect() as conn:
        # player_champions.sql ends with a semicolon, which CREATE ... AS cannot contain
        labels_query = (SQL_DIR / "player_champions.sql").read_text(encoding="utf-8").strip().rstrip(";")
        conn.execute(f"CREATE TEMP TABLE labels AS {labels_query}")
        return pd.read_sql_query((SQL_DIR / "main_games.sql").read_text(encoding="utf-8"), conn,
                                 params={"window_size": WINDOW_SIZE})


def page_payload(games, version, champion, champions, items, spells, runes):
    """Everything one champion page needs, as plain lists and dicts for JSON.

    games holds one champion's rows from load_main_games(). Each game becomes
    a short list instead of a dict to keep the page small; the template reads
    it by position (see the GAME FIELDS comment there).
    """
    # One entry per player. Rows are newest first within each player, so the
    # first row has their current Riot ID.
    players, player_index = [], {}
    for puuid, rows in games.groupby("puuid", sort=False):
        first = rows.iloc[0]
        player_index[puuid] = len(players)
        players.append({
            "riot_id": f"{first.riot_id_name}#{first.riot_id_tag}",
            "tier": first.tier.title(),
            "lp": int(first.league_points),
            "otp": first.label == "otp",
            "share": round(float(first.share), 3),  # share of their window on this champion
        })

    used = {"items": set(), "spells": set(), "runes": set(), "champions": set()}
    game_rows = []
    for g in games.itertuples():
        # Keep only boots and completed items; components and starters are noise here
        kept = [int(i) for i in (g.item0, g.item1, g.item2, g.item3, g.item4, g.item5)
                if i and items.get(int(i), {}).get("kind") in ("boots", "completed")]
        spell_pair = sorted([int(g.summoner1_id), int(g.summoner2_id)])  # Flash+Ignite = Ignite+Flash
        rune_page = [int(x) for x in (g.primary_style, g.rune1, g.rune2, g.rune3, g.rune4,
                                      g.secondary_style, g.rune5, g.rune6)]
        opponent = None if pd.isna(g.opponent_id) else int(g.opponent_id)
        game_rows.append([
            player_index[g.puuid], g.role or "", int(g.win), int(g.kills), int(g.deaths), int(g.assists),
            kept, spell_pair, rune_page, [int(g.shard_offense), int(g.shard_flex), int(g.shard_defense)],
            opponent,
        ])
        used["items"].update(kept)
        used["spells"].update(spell_pair)
        used["runes"].update(rune_page)
        if opponent is not None:
            used["champions"].add(opponent)

    def lookup(table, ids):
        return {i: [table[i]["name"], table[i]["icon"]] + ([table[i]["kind"]] if "kind" in table[i] else [])
                for i in ids if i in table}

    return {
        "champion": champion,
        "players": players,
        "games": game_rows,
        "lookup": {
            "items": lookup(items, used["items"]),
            "spells": lookup(spells, used["spells"]),
            "runes": lookup(runes, used["runes"]),
            "shards": SHARDS,
            "champions": {c: [champions[c]["name"], champion_icon(version, champions[c]["icon_id"])]
                          for c in used["champions"] if c in champions},
        },
    }


def write_champion_pages(out_dir, version, champions, site_name, built):
    """Write out_dir/<IconId>.html for every champion with at least one main.
    Returns {champion_id: file name} so the main table can link to them."""
    games = load_main_games()
    items, spells, runes = load_items(version), load_summoner_spells(version), load_runes(version)
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    out_dir.mkdir(parents=True, exist_ok=True)

    pages = {}
    for champion_id, rows in games.groupby("champion_id"):
        info = champions.get(int(champion_id))
        if info is None:  # a champion newer than this Data Dragon version
            continue
        champion = {"name": info["name"], "icon": champion_icon(version, info["icon_id"])}
        payload = page_payload(rows, version, champion, champions, items, spells, runes)
        payload.update({"site_name": site_name, "built": built, "window_size": WINDOW_SIZE})
        # "</" inside the JSON could end the <script> tag early, so escape it
        data_json = json.dumps(payload, separators=(",", ":")).replace("</", "<\\/")
        html = (template.replace("__SITE_NAME__", site_name)
                        .replace("__CHAMPION__", info["name"])
                        .replace("__DATA__", data_json))
        file_name = f"{info['icon_id']}.html"
        (out_dir / file_name).write_text(html, encoding="utf-8")
        pages[int(champion_id)] = file_name
    return pages


if __name__ == "__main__":
    games = load_main_games()
    pairs = games.groupby(["champion_id", "puuid"]).size()
    print(f"{len(games)} games, {len(pairs)} main/OTP player-champion pairs, "
          f"{games.champion_id.nunique()} champions")
    print(f"Games without a lane opponent: {games.opponent_id.isna().sum()}")
    print(f"Wins: {games.win.mean():.1%}")
