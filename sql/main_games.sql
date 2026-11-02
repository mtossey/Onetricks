-- Champion pages: one row per game a main or OTP played on their champion
-- within their window, with everything the Build, Ranking and Counters tabs
-- need. The pages aggregate these rows in the browser, so they can filter by
-- role or by a single player without another query.
--
-- Needs a temporary table named labels holding the output of
-- player_champions.sql (src/champion_pages.py creates it), so the main and
-- OTP definitions live in one place. :window_size comes from src/settings.py.

SELECT l.champion_id,
       l.puuid,
       l.label,
       l.share,
       pl.tier,
       pl.league_points,
       m.match_id,
       m.game_creation,
       p.team_position AS role,
       p.win,
       p.kills, p.deaths, p.assists,
       p.item0, p.item1, p.item2, p.item3, p.item4, p.item5,
       p.summoner1_id, p.summoner2_id,
       d.riot_id_name, d.riot_id_tag,
       d.primary_style, d.rune1, d.rune2, d.rune3, d.rune4,
       d.secondary_style, d.rune5, d.rune6,
       d.shard_offense, d.shard_flex, d.shard_defense,
       opp.champion_id AS opponent_id
FROM labels l
JOIN players pl              ON pl.puuid = l.puuid
JOIN player_matches pm       ON pm.puuid = l.puuid AND pm.recency_rank < :window_size
JOIN matches m               ON m.match_id = pm.match_id AND m.is_remake = 0
JOIN participants p          ON p.match_id = pm.match_id
                            AND p.puuid = l.puuid
                            AND p.champion_id = l.champion_id
JOIN participant_details d   ON d.match_id = p.match_id AND d.puuid = p.puuid
-- Lane opponent: the player on the other team in the same role. This is a
-- self-join (participants joined to itself). LEFT JOIN keeps the few games
-- with no role recorded; their opponent_id is NULL.
LEFT JOIN participants opp   ON opp.match_id = p.match_id
                            AND opp.team_id <> p.team_id
                            AND opp.team_position = p.team_position
WHERE l.label IN ('main', 'otp')
ORDER BY l.champion_id, l.puuid, m.game_creation DESC;
