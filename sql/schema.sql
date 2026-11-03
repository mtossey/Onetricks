-- Schema for the one-trick analysis database (data/onetricks.db).
-- Every table uses CREATE TABLE IF NOT EXISTS, so running this again is safe
-- and never deletes collected data.
--
-- Columns are based on real API responses inspected on Oct 31, 2026 (patch 16.21).
--
-- Mains and one-tricks are not stored here. They are calculated in SQL from
-- each player's share of games on a champion, so the thresholds can be
-- changed without calling the API again.

-- One row per sampled player, from the league-v4 Challenger, Grandmaster and
-- Master lists (platform host, for example na1). Tier is recorded at the time
-- the list was pulled. Players can move between tiers after that.
-- match_ids_fetched_at makes collection resumable: NULL means we have not
-- pulled this player's match ID list yet.
CREATE TABLE IF NOT EXISTS players (
    puuid                TEXT PRIMARY KEY,
    tier                 TEXT NOT NULL,      -- 'CHALLENGER', 'GRANDMASTER' or 'MASTER'
    league_points        INTEGER,
    wins                 INTEGER,            -- season ranked wins at collection time
    losses               INTEGER,
    added_at             TEXT NOT NULL DEFAULT (datetime('now')),
    match_ids_fetched_at TEXT
);

-- Each sampled player's recent ranked solo match IDs, newest first.
-- recency_rank 0 is the player's most recent game, 1 the one before, and so on.
-- This lets us download the newest 50 games first and extend to 100 later.
-- A match ID listed here but missing from the matches table still needs its
-- details downloaded.
CREATE TABLE IF NOT EXISTS player_matches (
    puuid        TEXT NOT NULL REFERENCES players(puuid),
    match_id     TEXT NOT NULL,
    recency_rank INTEGER NOT NULL,
    PRIMARY KEY (puuid, match_id)
);

-- One row per downloaded match, from match-v5 (regional host, for example americas).
CREATE TABLE IF NOT EXISTS matches (
    match_id              TEXT PRIMARY KEY,  -- for example 'NA1_5669273171'
    game_version          TEXT NOT NULL,     -- for example '16.21.829.8620'
    patch                 TEXT NOT NULL,     -- first two parts of game_version, for example '16.21'
    queue_id              INTEGER NOT NULL,  -- 420 is ranked solo queue
    game_creation         INTEGER NOT NULL,  -- Unix time in milliseconds
    game_duration_seconds INTEGER NOT NULL,
    is_remake             INTEGER NOT NULL   -- 1 if the game ended in an early surrender (remake)
);

-- All 10 players in each match, not only the sampled one. Rows for players who
-- are not in the players table have no one-trick flag, but they cost no extra
-- API calls and may be useful later.
CREATE TABLE IF NOT EXISTS participants (
    match_id              TEXT NOT NULL REFERENCES matches(match_id),
    puuid                 TEXT NOT NULL,
    team_id               INTEGER NOT NULL,  -- 100 (blue) or 200 (red)
    champion_id           INTEGER NOT NULL,
    champion_name         TEXT NOT NULL,     -- internal name, for example 'MonkeyKing' for Wukong
    team_position         TEXT,              -- TOP, JUNGLE, MIDDLE, BOTTOM, UTILITY (can be empty)
    win                   INTEGER NOT NULL,  -- 1 for a win, 0 for a loss
    kills                 INTEGER,
    deaths                INTEGER,
    assists               INTEGER,
    lane_minions          INTEGER,           -- totalMinionsKilled
    jungle_minions        INTEGER,           -- neutralMinionsKilled
    gold_earned           INTEGER,
    damage_to_champions   INTEGER,
    vision_score          INTEGER,
    item0 INTEGER, item1 INTEGER, item2 INTEGER,
    item3 INTEGER, item4 INTEGER, item5 INTEGER,
    item6 INTEGER,                           -- item6 is the trinket slot
    summoner1_id          INTEGER,
    summoner2_id          INTEGER,
    primary_style         INTEGER,           -- rune tree, for example 8000 (Precision)
    keystone              INTEGER,           -- first rune in the primary tree
    secondary_style       INTEGER,
    PRIMARY KEY (match_id, puuid)
);

-- Full match JSON, compressed with zlib. Lets us extract new fields later
-- without spending hours calling the API again. About 11 KB per match.
CREATE TABLE IF NOT EXISTS raw_matches (
    match_id  TEXT PRIMARY KEY REFERENCES matches(match_id),
    json_zlib BLOB NOT NULL
);

-- Match IDs the API could not return (for example 404). Recorded so the
-- downloader does not retry them on every run.
CREATE TABLE IF NOT EXISTS unavailable_matches (
    match_id   TEXT PRIMARY KEY,
    checked_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Speeds up the main analysis join: same champion, compare players.
CREATE INDEX IF NOT EXISTS idx_participants_champion ON participants(champion_id);
CREATE INDEX IF NOT EXISTS idx_participants_puuid ON participants(puuid);

-- Fields extracted later from raw_matches by src/extract_details.py, so no
-- extra API calls were needed. Used by the champion pages.
--   Runes: the primary tree has 4 runes (rune1 is the keystone), the
--   secondary tree has 2, and the 3 stat shards are small bonuses.
--   Riot ID: the player's name and tag at the time of that match.
CREATE TABLE IF NOT EXISTS participant_details (
    match_id        TEXT NOT NULL,
    puuid           TEXT NOT NULL,
    riot_id_name    TEXT,
    riot_id_tag     TEXT,
    primary_style   INTEGER,
    rune1 INTEGER, rune2 INTEGER, rune3 INTEGER, rune4 INTEGER,
    secondary_style INTEGER,
    rune5 INTEGER, rune6 INTEGER,
    shard_offense INTEGER, shard_flex INTEGER, shard_defense INTEGER,
    PRIMARY KEY (match_id, puuid),
    FOREIGN KEY (match_id, puuid) REFERENCES participants(match_id, puuid)
);

-- Match timelines (match-v5 timeline endpoint), downloaded by
-- src/collect_timelines.py for matches where a main or OTP played their
-- champion. One row per match, so the download can stop and resume.
--   available = 0 when the API had no timeline (404).
CREATE TABLE IF NOT EXISTS timelines (
    match_id   TEXT PRIMARY KEY REFERENCES matches(match_id),
    available  INTEGER NOT NULL,
    fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- The item and skill events from those timelines, for all 10 players.
-- Everything else in a timeline (about 400 KB per match) is thrown away.
--   event_type: ITEM_PURCHASED, ITEM_SOLD, ITEM_UNDO or SKILL_LEVEL_UP
--   item_id:    the item bought or sold. For ITEM_UNDO, the item the undo
--               removed (Riot's beforeId); after_id is what it restored.
--   skill_slot: 1 = Q, 2 = W, 3 = E, 4 = R
--   seq:        the event's position in the timeline, to keep the order of
--               events that share a timestamp
CREATE TABLE IF NOT EXISTS timeline_events (
    match_id      TEXT NOT NULL REFERENCES timelines(match_id),
    puuid         TEXT NOT NULL,
    seq           INTEGER NOT NULL,
    timestamp_ms  INTEGER NOT NULL,
    event_type    TEXT NOT NULL,
    item_id       INTEGER,
    after_id      INTEGER,
    skill_slot    INTEGER,
    level_up_type TEXT,
    PRIMARY KEY (match_id, seq)
);
CREATE INDEX IF NOT EXISTS idx_timeline_events_player ON timeline_events(match_id, puuid);
