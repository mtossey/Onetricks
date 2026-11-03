"""
Champion pages: every game a main or OTP played on their champion
(sql/main_games.sql), written as one JSON file per champion for the React
site's Build, Ranking and Counters tabs. build_site.py calls write_champion_data().

    python src/champion_pages.py      # prints a short check of the data
"""

import json
from pathlib import Path

import pandas as pd

from db import connect
from ddragon import SHARD_ROWS, SHARDS, champion_icon, load_abilities, load_items, load_runes, load_summoner_spells
from settings import WINDOW_SIZE

SRC = Path(__file__).resolve().parent
SQL_DIR = SRC.parent / "sql"


def _sql(name):
    # CREATE TABLE ... AS cannot contain the query's closing semicolon
    return (SQL_DIR / name).read_text(encoding="utf-8").strip().rstrip(";")


def _create_main_games(conn):
    """Temporary tables used by the champion page queries:
    labels (player_champions.sql) and main_games (main_games.sql)."""
    conn.execute(f"CREATE TEMP TABLE labels AS {_sql('player_champions.sql')}")
    conn.execute(f"CREATE TEMP TABLE main_games AS {_sql('main_games.sql')}", {"window_size": WINDOW_SIZE})


def load_main_games():
    with connect() as conn:
        _create_main_games(conn)
        return pd.read_sql_query("SELECT * FROM main_games ORDER BY champion_id, puuid, game_creation DESC", conn)


def load_build_events(items):
    """Purchases (main_purchases.sql) and skill points (skill_order.sql) in
    mains' games, as two DataFrames. items is load_items() from ddragon.py."""
    with connect() as conn:
        _create_main_games(conn)
        conn.execute("CREATE TEMP TABLE item_kinds (item_id INTEGER PRIMARY KEY, kind TEXT)")
        conn.executemany("INSERT INTO item_kinds VALUES (?, ?)", [(i, it["kind"]) for i, it in items.items()])
        purchases = pd.read_sql_query(_sql("main_purchases.sql"), conn)
        skills = pd.read_sql_query(_sql("skill_order.sql"), conn)
    return purchases, skills


# Items bought in a game's first 60 seconds are its starting items. Players
# buy in the first 30 seconds or so, then not again until they go back to base.
START_ITEMS_MS = 60_000
SKILL_POINTS_SHOWN = 18  # one per level


def timeline_by_game(purchases, skills, items):
    """{(match_id, puuid): (starting items, completed item order, skill order)}
    from load_build_events(). The skill order is a string such as "QEWQQRQ"."""
    result = {}
    skill_text = {key: "".join("QWER"[slot - 1] for slot in rows.skill_slot[:SKILL_POINTS_SHOWN])
                  for key, rows in skills.groupby(["match_id", "puuid"])}
    for key, rows in purchases.groupby(["match_id", "puuid"]):
        start = rows[(rows.timestamp_ms < START_ITEMS_MS) & (rows.kind != "trinket")]
        # Sorted, so the same set bought in a different order counts as one option
        start_items = sorted(int(i) for i in start.item_id if i in items)
        completed = rows.dropna(subset=["completed_number"]).sort_values("completed_number")
        result[key] = (start_items, [int(i) for i in completed.item_id], skill_text.get(key, ""))
    return result


def page_payload(games, version, champion, champions, items, spells, runes, trees, timeline, abilities):
    """Everything one champion page needs, as plain lists and dicts for JSON.

    games holds one champion's rows from load_main_games(). Each game becomes
    a short list instead of a dict to keep the files small; the React site
    reads it by position (see RawGame in web/src/types.ts).
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

    used = {"items": set(), "spells": set(), "trees": set(), "champions": set()}
    game_rows = []
    for g in games.itertuples():
        # Keep only boots and completed items; components and starters are noise here
        kept = [int(i) for i in (g.item0, g.item1, g.item2, g.item3, g.item4, g.item5)
                if i and items.get(int(i), {}).get("kind") in ("boots", "completed")]
        spell_pair = sorted([int(g.summoner1_id), int(g.summoner2_id)])  # Flash+Ignite = Ignite+Flash
        rune_page = [int(x) for x in (g.primary_style, g.rune1, g.rune2, g.rune3, g.rune4,
                                      g.secondary_style, g.rune5, g.rune6)]
        opponent = None if pd.isna(g.opponent_id) else int(g.opponent_id)
        start_items, build_order, skill_order = timeline.get((g.match_id, g.puuid), ([], [], ""))
        game_rows.append([
            player_index[g.puuid],
            g.role if isinstance(g.role, str) else "",  # pandas turns a NULL role into NaN, not None
            int(g.win), int(g.kills), int(g.deaths), int(g.assists),
            kept, spell_pair, rune_page, [int(g.shard_offense), int(g.shard_flex), int(g.shard_defense)],
            opponent, start_items, build_order, skill_order,
        ])
        used["items"].update(kept, start_items, build_order)
        used["spells"].update(spell_pair)
        used["trees"].update([rune_page[0], rune_page[5]])
        if opponent is not None:
            used["champions"].add(opponent)

    def lookup(table, ids):
        return {i: [table[i]["name"], table[i]["icon"]] + ([table[i]["kind"]] if "kind" in table[i] else [])
                for i in ids if i in table}

    return {
        "champion": champion,
        "abilities": [[a["name"], a["icon"]] for a in abilities],  # Q, W, E, R
        "players": players,
        "games": game_rows,
        "lookup": {
            "items": lookup(items, used["items"]),
            "spells": lookup(spells, used["spells"]),
            # Every rune in every tree used, so the page can draw whole trees
            # with the unpicked runes greyed out
            "trees": {t: trees[t] for t in used["trees"] if t in trees},
            "runes": lookup(runes, used["trees"] | {r for t in used["trees"] for row in trees.get(t, []) for r in row}),
            "shards": lookup(SHARDS, SHARDS),
            "shard_rows": SHARD_ROWS,
            "champions": {c: [champions[c]["name"], champion_icon(version, champions[c]["icon_id"])]
                          for c in used["champions"] if c in champions},
        },
    }


def write_champion_data(json_dir, version, champions, site_name, built):
    """Write json_dir/<IconId>.json for every champion with at least one main.
    Returns {champion_id: IconId} so the champion table can link to them."""
    games = load_main_games()
    items, spells = load_items(version), load_summoner_spells(version)
    runes, trees = load_runes(version)
    timeline = timeline_by_game(*load_build_events(items), items)
    json_dir.mkdir(parents=True, exist_ok=True)

    pages = {}
    for champion_id, rows in games.groupby("champion_id"):
        info = champions.get(int(champion_id))
        if info is None:  # a champion newer than this Data Dragon version
            continue
        champion = {"name": info["name"], "icon": champion_icon(version, info["icon_id"])}
        abilities = load_abilities(version, info["icon_id"])
        payload = page_payload(rows, version, champion, champions, items, spells, runes, trees, timeline, abilities)
        payload.update({"site_name": site_name, "built": built, "window_size": WINDOW_SIZE})
        # allow_nan=False: browsers reject NaN in JSON, so fail here instead
        (json_dir / f"{info['icon_id']}.json").write_text(
            json.dumps(payload, separators=(",", ":"), allow_nan=False), encoding="utf-8")
        pages[int(champion_id)] = info["icon_id"]
    return pages


if __name__ == "__main__":
    games = load_main_games()
    pairs = games.groupby(["champion_id", "puuid"]).size()
    print(f"{len(games)} games, {len(pairs)} main/OTP player-champion pairs, "
          f"{games.champion_id.nunique()} champions")
    print(f"Games without a lane opponent: {games.opponent_id.isna().sum()}")
    print(f"Wins: {games.win.mean():.1%}")
