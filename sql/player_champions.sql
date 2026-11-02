-- One row per classified sampled player per champion they played in their
-- window, labeled 'otp', 'main' or 'other'. The notebook uses these rows for
-- player-level statistics (bootstrap) and breakdowns by tier.
--
-- Steps 0 to 4 are the same as in champion_table.sql (see the comments
-- there). Keep the settings in both files and src/settings.py in sync.

WITH settings AS (
    SELECT 500  AS sample_size,
           30   AS window_size,
           15   AS min_games,
           0.30 AS main_share,
           0.70 AS otp_share
),

sample_players AS (
    SELECT puuid
    FROM players
    ORDER BY puuid
    LIMIT (SELECT sample_size FROM settings)
),

window_games AS (
    SELECT pm.puuid, pm.match_id
    FROM player_matches pm
    JOIN sample_players sp ON sp.puuid = pm.puuid
    CROSS JOIN settings s
    WHERE pm.recency_rank < s.window_size
      AND pm.match_id NOT IN (SELECT match_id FROM unavailable_matches)
),

complete_players AS (
    SELECT w.puuid
    FROM window_games w
    LEFT JOIN matches m ON m.match_id = w.match_id
    GROUP BY w.puuid
    HAVING COUNT(m.match_id) = COUNT(*)
),

player_games AS (
    SELECT w.puuid, p.champion_id, p.win
    FROM window_games w
    JOIN complete_players cp ON cp.puuid = w.puuid
    JOIN matches m           ON m.match_id = w.match_id AND m.is_remake = 0
    JOIN participants p      ON p.match_id = w.match_id AND p.puuid = w.puuid
),

player_champions AS (
    SELECT puuid,
           champion_id,
           COUNT(*) AS games,
           SUM(win) AS wins,
           SUM(COUNT(*)) OVER (PARTITION BY puuid) AS player_total_games,
           COUNT(*) * 1.0 / SUM(COUNT(*)) OVER (PARTITION BY puuid) AS share
    FROM player_games
    GROUP BY puuid, champion_id
)

SELECT pc.puuid,
       pl.tier,
       pc.champion_id,
       pc.games,
       pc.wins,
       pc.player_total_games,
       pc.share,
       CASE
           WHEN pc.share >= s.otp_share  THEN 'otp'
           WHEN pc.share >= s.main_share THEN 'main'
           ELSE 'other'
       END AS label
FROM player_champions pc
JOIN players pl ON pl.puuid = pc.puuid
CROSS JOIN settings s
WHERE pc.player_total_games >= s.min_games
ORDER BY pc.puuid, pc.games DESC;
