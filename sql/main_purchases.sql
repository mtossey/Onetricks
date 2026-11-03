-- Champion pages: every item a main or OTP bought in their games on their
-- champion, in order, with undone purchases removed. Used for starting items
-- and build order.
--
-- Needs two temporary tables that src/champion_pages.py creates:
--   main_games:  the output of main_games.sql (one row per main's game)
--   item_kinds:  item_id and kind ('boots', 'trinket', 'completed', 'other')
--                from Data Dragon

WITH
-- 1. Purchases and purchase undos in mains' games. For an undo, item_id is
--    the item it took back (undos of a sale have item_id 0 and are skipped).
purchases AS (
    SELECT e.match_id, e.puuid, e.seq, e.timestamp_ms, e.item_id
    FROM timeline_events e
    JOIN main_games g ON g.match_id = e.match_id AND g.puuid = e.puuid
    WHERE e.event_type = 'ITEM_PURCHASED'
),
undos AS (
    SELECT e.match_id, e.puuid, e.seq, e.item_id
    FROM timeline_events e
    JOIN main_games g ON g.match_id = e.match_id AND g.puuid = e.puuid
    WHERE e.event_type = 'ITEM_UNDO' AND e.item_id > 0
),

-- 2. Remove undone purchases. An undo takes back the most recent purchase of
--    that item, so a purchase is undone when an undo of the same item comes
--    after it with no other purchase of that item in between. (Two undos in
--    a row of the same item only remove one purchase here, which is rare.)
kept AS (
    SELECT p.*
    FROM purchases p
    WHERE NOT EXISTS (
        SELECT 1
        FROM undos u
        WHERE u.match_id = p.match_id AND u.puuid = p.puuid
          AND u.item_id = p.item_id AND u.seq > p.seq
          AND NOT EXISTS (
              SELECT 1
              FROM purchases p2
              WHERE p2.match_id = p.match_id AND p2.puuid = p.puuid
                AND p2.item_id = p.item_id AND p2.seq > p.seq AND p2.seq < u.seq
          )
    )
),

-- 3. Each purchase's item kind, and which copy of that item it is in the game
--    (1 for the first time the player bought it, 2 if they bought it again).
numbered AS (
    SELECT k.*,
           COALESCE(ik.kind, 'other') AS kind,
           ROW_NUMBER() OVER (PARTITION BY k.match_id, k.puuid, k.item_id ORDER BY k.seq) AS copy_number
    FROM kept k
    LEFT JOIN item_kinds ik ON ik.item_id = k.item_id
)

-- 4. completed_number: 1 for the first completed item the player finished,
--    2 for the second, and so on (boots have their own kind and are not
--    counted). The window is PARTITIONed by player and by whether the row is a
--    first-copy completed item, so other purchases do not use up numbers;
--    the CASE then blanks the number on every row that is not one.
SELECT match_id, puuid, seq, timestamp_ms, item_id, kind,
       CASE WHEN kind = 'completed' AND copy_number = 1 THEN
           ROW_NUMBER() OVER (PARTITION BY match_id, puuid, (kind = 'completed' AND copy_number = 1)
                              ORDER BY seq)
       END AS completed_number
FROM numbered
ORDER BY match_id, puuid, seq;
