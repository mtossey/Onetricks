-- Per-champion table: number of mains and one-tricks (OTPs), their win rates
-- on that champion, and two comparison groups.
--
-- Definitions (change them in the settings CTE, and keep src/settings.py in sync):
--   Sample: the first sample_size players ordered by PUUID (a repeatable random subset).
--   Window: a sampled player's newest window_size ranked solo games, remakes removed.
--   Main:   30% or more of the window on one champion. Includes OTPs.
--   OTP:    70% or more of the window on one champion.
--   A player needs at least min_games non-remake games in the window to be classified.
--
-- Comparison groups:
--   other: sampled players who played the champion but are not mains of it.
--          This is the main comparison. Sampled players were chosen from the
--          current Master+ ladder, which means they recently won more than
--          average (54% vs 50% in the trial batch). Comparing mains with other
--          sampled players cancels out that selection effect.
--   all:   every participant on the champion in the sample's window matches,
--          sampled or not. Shown for context only, because it does not share
--          the selection effect.
--
-- Roles: the output has one row per champion per role (TOP, JUNGLE, MIDDLE,
-- BOTTOM, UTILITY) plus a role = 'ALL' row with every game. Labels come from a
-- player's share of the champion across all roles. Each main and OTP is then
-- placed in their most-played role on that champion, and only those games
-- count in the role rows. Their off-role games (mostly one or two autofill
-- games) still count in 'ALL'. Other sampled players and all players count in
-- whichever role each game was played.
--
-- Output is raw counts (games and wins). Win rates and Wilson confidence
-- intervals are calculated in Python, because SQLite has no built-in SQRT
-- in every Python build.

WITH settings AS (
    SELECT 500  AS sample_size,
           30   AS window_size,
           15   AS min_games,
           0.30 AS main_share,
           0.70 AS otp_share
),

-- 0. The analysis sample. Same order as collect_matches.py --players, so the
--    players analyzed are exactly the players whose matches were downloaded.
sample_players AS (
    SELECT puuid
    FROM players
    ORDER BY puuid
    LIMIT (SELECT sample_size FROM settings)
),

-- 1. Each sampled player's window of match IDs.
window_games AS (
    SELECT pm.puuid, pm.match_id
    FROM player_matches pm
    JOIN sample_players sp ON sp.puuid = pm.puuid
    CROSS JOIN settings s
    WHERE pm.recency_rank < s.window_size
      AND pm.match_id NOT IN (SELECT match_id FROM unavailable_matches)
),

-- 2. Players whose whole window has been downloaded. While collection is
--    still running, a player can appear in a few downloaded matches without
--    the rest of their window, and their shares would be wrong.
--    COUNT(m.match_id) skips NULLs from the LEFT JOIN, so it only equals
--    COUNT(*) when every match in the window is in the matches table.
complete_players AS (
    SELECT w.puuid
    FROM window_games w
    LEFT JOIN matches m ON m.match_id = w.match_id
    GROUP BY w.puuid
    HAVING COUNT(m.match_id) = COUNT(*)
),

-- 3. The champion played, the role and the result for each game in a
--    complete window. team_position is the role Riot assigned in that game.
player_games AS (
    SELECT w.puuid, p.champion_id, p.team_position AS role, p.win
    FROM window_games w
    JOIN complete_players cp ON cp.puuid = w.puuid
    JOIN matches m           ON m.match_id = w.match_id AND m.is_remake = 0
    JOIN participants p      ON p.match_id = w.match_id AND p.puuid = w.puuid
),

-- 4. Games and wins per player per champion, and that champion's share of
--    the player's window.
--    SUM(COUNT(*)) OVER (PARTITION BY puuid) is a window function on top of
--    the GROUP BY: COUNT(*) is games on this champion, and the window sum
--    adds those counts across all of the player's champions, which gives the
--    player's total games without a separate subquery.
player_champions AS (
    SELECT puuid,
           champion_id,
           COUNT(*) AS games,
           SUM(win) AS wins,
           SUM(COUNT(*)) OVER (PARTITION BY puuid) AS player_total_games,
           COUNT(*) * 1.0 / SUM(COUNT(*)) OVER (PARTITION BY puuid) AS share
    FROM player_games
    GROUP BY puuid, champion_id
),

-- 5. Label every player-champion row of classified players:
--    'otp' (70%+), 'main' (30% to 69%), or 'other' (under 30%).
labeled AS (
    SELECT pc.puuid,
           pc.champion_id,
           CASE
               WHEN pc.share >= s.otp_share  THEN 'otp'
               WHEN pc.share >= s.main_share THEN 'main'
               ELSE 'other'
           END AS label
    FROM player_champions pc
    CROSS JOIN settings s
    WHERE pc.player_total_games >= s.min_games
),

-- 6. Each player's roles on each champion, ranked by games played.
--    ROW_NUMBER() numbers the rows 1, 2, 3, ... separately inside each
--    PARTITION (one player on one champion), in the ORDER BY order: most games
--    first, and alphabetical role to break ties. role_rank = 1 is the
--    player's main role on that champion.
player_roles AS (
    SELECT puuid,
           champion_id,
           role,
           ROW_NUMBER() OVER (PARTITION BY puuid, champion_id
                              ORDER BY COUNT(*) DESC, role) AS role_rank
    FROM player_games
    WHERE role IN ('TOP', 'JUNGLE', 'MIDDLE', 'BOTTOM', 'UTILITY')
    GROUP BY puuid, champion_id, role
),

-- 7. Every labeled game, listed twice: once under its own role and once
--    under 'ALL'. UNION ALL stacks the two lists (it keeps duplicates, unlike
--    UNION), which lets one GROUP BY produce the per-role and all-role rows.
--    In the role list, mains and OTPs keep only games in their main role.
--    The few games with no role recorded only count toward 'ALL'.
labeled_games AS (
    SELECT g.puuid, g.champion_id, g.role, g.win, l.label
    FROM player_games g
    JOIN labeled l       ON l.puuid = g.puuid AND l.champion_id = g.champion_id
    JOIN player_roles pr ON pr.puuid = g.puuid AND pr.champion_id = g.champion_id
                        AND pr.role = g.role
    WHERE l.label = 'other' OR pr.role_rank = 1
    UNION ALL
    SELECT g.puuid, g.champion_id, 'ALL', g.win, l.label
    FROM player_games g
    JOIN labeled l ON l.puuid = g.puuid AND l.champion_id = g.champion_id
),

-- 8. Sampled players' counts per champion and role. The "mains" columns
--    include OTPs, so they use label IN ('main', 'otp'). Rows here are games,
--    so player counts need COUNT(DISTINCT puuid). CASE with no ELSE gives
--    NULL for rows that do not match, and COUNT and SUM skip NULLs.
sampled AS (
    SELECT champion_id,
           role,
           COUNT(DISTINCT CASE WHEN label IN ('main', 'otp') THEN puuid END) AS mains,
           COUNT(DISTINCT CASE WHEN label = 'otp' THEN puuid END)            AS otps,
           COUNT(CASE WHEN label IN ('main', 'otp') THEN 1 END)              AS main_games,
           SUM(CASE WHEN label IN ('main', 'otp') THEN win END)              AS main_wins,
           COUNT(CASE WHEN label = 'otp' THEN 1 END)                         AS otp_games,
           SUM(CASE WHEN label = 'otp' THEN win END)                         AS otp_wins,
           COUNT(DISTINCT CASE WHEN label = 'other' THEN puuid END)          AS other_players,
           COUNT(CASE WHEN label = 'other' THEN 1 END)                       AS other_games,
           SUM(CASE WHEN label = 'other' THEN win END)                       AS other_wins
    FROM labeled_games
    GROUP BY champion_id, role
),

-- 9. Every participant on each champion in the sample's non-remake window
--    matches, sampled or not. Context only (see the comparison groups above).
--    Limiting to window matches leaves out matches downloaded for earlier,
--    larger sample plans. Listed per role and under 'ALL', as in step 7.
all_participants AS (
    SELECT p.champion_id, p.champion_name, p.team_position AS role, p.win
    FROM participants p
    JOIN matches m ON m.match_id = p.match_id
    WHERE m.is_remake = 0
      AND p.match_id IN (SELECT match_id FROM window_games)
),
all_players AS (
    SELECT champion_id, MAX(champion_name) AS champion_name, role,
           COUNT(*) AS games, SUM(win) AS wins
    FROM all_participants
    WHERE role IN ('TOP', 'JUNGLE', 'MIDDLE', 'BOTTOM', 'UTILITY')
    GROUP BY champion_id, role
    UNION ALL
    SELECT champion_id, MAX(champion_name), 'ALL',
           COUNT(*), SUM(win)
    FROM all_participants
    GROUP BY champion_id
)

-- 10. One row per champion per role. LEFT JOIN keeps rows with no sampled
--     players, and COALESCE turns their missing counts (NULL) into 0.
SELECT a.champion_id,
       a.champion_name,
       a.role,
       COALESCE(s.mains, 0)         AS mains,
       COALESCE(s.otps, 0)          AS otps,
       COALESCE(s.main_games, 0)    AS main_games,
       COALESCE(s.main_wins, 0)     AS main_wins,
       COALESCE(s.otp_games, 0)     AS otp_games,
       COALESCE(s.otp_wins, 0)      AS otp_wins,
       COALESCE(s.other_players, 0) AS other_players,
       COALESCE(s.other_games, 0)   AS other_games,
       COALESCE(s.other_wins, 0)    AS other_wins,
       a.games                      AS all_games,
       a.wins                       AS all_wins
FROM all_players a
LEFT JOIN sampled s ON s.champion_id = a.champion_id AND s.role = a.role
ORDER BY a.role, mains DESC, all_games DESC;
