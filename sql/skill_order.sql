-- Champion pages: the order in which a main or OTP put skill points into
-- abilities in their games on their champion.
--
-- Needs the temporary table main_games (see main_purchases.sql).
--
-- skill_point is 1 for the first point (usually level 1), 2 for the second,
-- and so on. ROW_NUMBER restarts for each player in each game because of
-- PARTITION BY. skill_slot: 1 = Q, 2 = W, 3 = E, 4 = R.
-- EVOLVE events (Kha'Zix and similar ability upgrades) are not skill points.

SELECT e.match_id,
       e.puuid,
       ROW_NUMBER() OVER (PARTITION BY e.match_id, e.puuid ORDER BY e.seq) AS skill_point,
       e.skill_slot
FROM timeline_events e
JOIN main_games g ON g.match_id = e.match_id AND g.puuid = e.puuid
WHERE e.event_type = 'SKILL_LEVEL_UP'
  AND e.level_up_type = 'NORMAL'
ORDER BY e.match_id, e.puuid, skill_point;
