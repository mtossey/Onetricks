"""
Data Dragon: Riot's public CDN of static game data (champion, item, spell and
rune names and icons). No API key needed. Files are cached in data/ddragon/
so pages can be rebuilt without downloading them again.
"""

import json
from pathlib import Path

import requests

DDRAGON = "https://ddragon.leagueoflegends.com"
CACHE = Path(__file__).resolve().parent.parent / "data" / "ddragon"


def latest_version():
    return requests.get(f"{DDRAGON}/api/versions.json", timeout=10).json()[0]


def ddragon_json(version, filename):
    """A data file such as champion.json for the given version, cached."""
    cache = CACHE / f"{Path(filename).stem}_{version}.json"
    if not cache.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        data = requests.get(f"{DDRAGON}/cdn/{version}/data/en_US/{filename}", timeout=10).json()
        cache.write_text(json.dumps(data), encoding="utf-8")
    return json.loads(cache.read_text(encoding="utf-8"))


def load_ddragon_champions():
    """Return the latest Data Dragon version and {champion_id: {name, icon_id}}."""
    version = latest_version()
    champions = ddragon_json(version, "champion.json")["data"]
    # champion.json is keyed by internal name ('MonkeyKing'); "key" holds the
    # numeric champion ID as a string, and "name" is the display name ('Wukong')
    return version, {int(c["key"]): {"name": c["name"], "icon_id": c["id"]} for c in champions.values()}


def champion_icon(version, icon_id):
    return f"{DDRAGON}/cdn/{version}/img/champion/{icon_id}.png"


def load_items(version):
    """{item_id: {name, icon, kind}} where kind is 'boots', 'completed' or 'other'.

    'completed' means a finished item: it does not build into anything, is not
    a starter item (Doran's items and support items carry the 'Lane' tag), a
    consumable or a trinket, and costs at least 1,000 gold.
    """
    items = {}
    for key, it in ddragon_json(version, "item.json")["data"].items():
        tags = it.get("tags", [])
        if "Boots" in tags:
            kind = "boots"
        elif (not it.get("into") and it["gold"]["total"] >= 1000
              and not {"Lane", "Consumable", "Trinket"} & set(tags)):
            kind = "completed"
        else:
            kind = "other"
        items[int(key)] = {"name": it["name"], "icon": f"{DDRAGON}/cdn/{version}/img/item/{key}.png", "kind": kind}
    return items


def load_summoner_spells(version):
    """{spell_id: {name, icon}}. summoner.json is keyed by internal name; "key" is the numeric ID."""
    spells = ddragon_json(version, "summoner.json")["data"].values()
    return {int(s["key"]): {"name": s["name"], "icon": f"{DDRAGON}/cdn/{version}/img/spell/{s['image']['full']}"}
            for s in spells}


def load_runes(version):
    """{rune_or_tree_id: {name, icon}} for every rune tree and every rune in it."""
    runes = {}
    for tree in ddragon_json(version, "runesReforged.json"):
        runes[tree["id"]] = {"name": tree["name"], "icon": f"{DDRAGON}/cdn/img/{tree['icon']}"}
        for slot in tree["slots"]:
            for r in slot["runes"]:
                runes[r["id"]] = {"name": r["name"], "icon": f"{DDRAGON}/cdn/img/{r['icon']}"}
    return runes


# Stat shards are not in Data Dragon, so their names are listed here
SHARDS = {
    5001: "Health scaling", 5002: "Armor", 5003: "Magic resist", 5005: "Attack speed",
    5007: "Ability haste", 5008: "Adaptive force", 5010: "Move speed", 5011: "Health",
    5013: "Tenacity and slow resist",
}
