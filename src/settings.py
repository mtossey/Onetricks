"""
Study settings shared by the Python scripts.

The SQL files (sql/champion_table.sql, sql/player_champions.sql) have the
same values in their settings CTE. Keep them in sync when changing these.
"""

# Analysis sample: the first SAMPLE_SIZE players ordered by PUUID. PUUIDs are
# random strings, so this is an effectively random but repeatable subset that
# mixes tiers. Growing the sample later keeps everyone already in it.
SAMPLE_SIZE = 500

# Each player's window: their newest WINDOW_SIZE ranked solo games
WINDOW_SIZE = 30
