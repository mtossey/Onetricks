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
    """{item_id: {name, icon, kind}} where kind is 'boots', 'trinket', 'completed' or 'other'.

    'completed' means a finished item: it does not build into anything, is not
    a starter item (Doran's items and support items carry the 'Lane' tag), a
    consumable or a trinket, and costs at least 1,000 gold.
    """
    data = ddragon_json(version, "item.json")["data"]
    # Boots are items tagged "Boots", plus upgrades built from them: Gunmetal
    # Greaves builds from Berserker's Greaves but is missing the tag
    tagged_boots = {key for key, it in data.items() if "Boots" in it.get("tags", [])}
    items = {}
    for key, it in data.items():
        tags = it.get("tags", [])
        if key in tagged_boots or tagged_boots & set(it.get("from", [])):
            kind = "boots"
        elif "Trinket" in tags:
            kind = "trinket"  # wards and lenses, left out of starting items
        elif (not it.get("into") and it["gold"]["total"] >= 1000
              and not {"Lane", "Consumable", "Trinket"} & set(tags)):
            kind = "completed"
        else:
            kind = "other"
        items[int(key)] = {"name": it["name"], "icon": f"{DDRAGON}/cdn/{version}/img/item/{key}.png", "kind": kind}
    return items


def load_abilities(version, icon_id):
    """A champion's Q, W, E and R as [{name, icon}], from its own Data Dragon file."""
    spells = ddragon_json(version, f"champion/{icon_id}.json")["data"][icon_id]["spells"]
    return [{"name": s["name"], "icon": f"{DDRAGON}/cdn/{version}/img/spell/{s['image']['full']}"} for s in spells]


def load_summoner_spells(version):
    """{spell_id: {name, icon}}. summoner.json is keyed by internal name; "key" is the numeric ID."""
    spells = ddragon_json(version, "summoner.json")["data"].values()
    return {int(s["key"]): {"name": s["name"], "icon": f"{DDRAGON}/cdn/{version}/img/spell/{s['image']['full']}"}
            for s in spells}


def load_runes(version):
    """Return ({rune_or_tree_id: {name, icon}}, {tree_id: slots}).

    slots is the tree's layout as lists of rune IDs: slots[0] is the keystone
    row and slots[1] to slots[3] are the three rows below it.
    """
    runes, trees = {}, {}
    for tree in ddragon_json(version, "runesReforged.json"):
        runes[tree["id"]] = {"name": tree["name"], "icon": f"{DDRAGON}/cdn/img/{tree['icon']}"}
        trees[tree["id"]] = [[r["id"] for r in slot["runes"]] for slot in tree["slots"]]
        for slot in tree["slots"]:
            for r in slot["runes"]:
                runes[r["id"]] = {"name": r["name"], "icon": f"{DDRAGON}/cdn/img/{r['icon']}"}
    return runes, trees


# Stat shards are not in runesReforged.json, so their names and icons are listed here
_STAT_MODS = f"{DDRAGON}/cdn/img/perk-images/StatMods"
SHARDS = {
    5001: {"name": "Health scaling", "icon": f"{_STAT_MODS}/StatModsHealthScalingIcon.png"},
    5005: {"name": "Attack speed", "icon": f"{_STAT_MODS}/StatModsAttackSpeedIcon.png"},
    5007: {"name": "Ability haste", "icon": f"{_STAT_MODS}/StatModsCDRScalingIcon.png"},
    5008: {"name": "Adaptive force", "icon": f"{_STAT_MODS}/StatModsAdaptiveForceIcon.png"},
    5010: {"name": "Move speed", "icon": f"{_STAT_MODS}/StatModsMovementSpeedIcon.png"},
    5011: {"name": "Health", "icon": f"{_STAT_MODS}/StatModsHealthPlusIcon.png"},
    5013: {"name": "Tenacity and slow resist", "icon": f"{_STAT_MODS}/StatModsTenacityIcon.png"},
}
# The three shard rows (offense, flex, defense) and their options, as seen in our data
SHARD_ROWS = [[5008, 5005, 5007], [5008, 5010, 5001], [5011, 5013, 5001]]
