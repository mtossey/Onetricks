"""
Run sql/champion_table.sql and add win rates with Wilson 95% confidence
intervals. Prints the table and a short summary.

    python src/champion_table.py
"""

import math
from pathlib import Path

import pandas as pd

from db import connect

SQL_PATH = Path(__file__).resolve().parent.parent / "sql" / "champion_table.sql"


def wilson_interval(wins, games, z=1.96):
    """
    95% Wilson score interval for a win rate. Unlike the simple
    p +/- 1.96 * sqrt(p(1-p)/n), it stays between 0 and 1 and behaves
    sensibly for small samples, which we will have for many champions.
    """
    if games == 0:
        return (math.nan, math.nan)
    p = wins / games
    denominator = 1 + z**2 / games
    center = (p + z**2 / (2 * games)) / denominator
    half_width = z * math.sqrt(p * (1 - p) / games + z**2 / (4 * games**2)) / denominator
    return (center - half_width, center + half_width)


def add_win_rate(df, group):
    """Add <group>_wr, <group>_low, <group>_high columns from <group>_wins and <group>_games."""
    games, wins = df[f"{group}_games"], df[f"{group}_wins"]
    df[f"{group}_wr"] = (wins / games).where(games > 0)
    intervals = [wilson_interval(w, g) for w, g in zip(wins, games)]
    df[f"{group}_low"] = [low for low, _ in intervals]
    df[f"{group}_high"] = [high for _, high in intervals]


ROLES = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]


def load_champion_table(role="ALL"):
    """
    One row per champion for the given role ('ALL' for every game, or one of
    ROLES). role=None returns every row, with a role column to tell them apart.
    """
    with connect() as conn:
        df = pd.read_sql_query(SQL_PATH.read_text(encoding="utf-8"), conn)
    if role is not None:
        df = df[df.role == role].reset_index(drop=True)
    for group in ("main", "otp", "other", "all"):
        add_win_rate(df, group)
    return df


if __name__ == "__main__":
    df = load_champion_table()

    with connect() as conn:
        player_rows = pd.read_sql_query(
            (SQL_PATH.parent / "player_champions.sql").read_text(encoding="utf-8"), conn)
    print(f"Classified players (complete window, at least 15 games): {player_rows.puuid.nunique()}")
    print(f"Champions in data: {len(df)}, with at least one main: {(df.mains > 0).sum()}, "
          f"with at least one OTP: {(df.otps > 0).sum()}")
    print(f"Total main rows: {df.mains.sum()}, total OTP rows: {df.otps.sum()}\n")

    def fmt(wr, low, high):
        return "" if pd.isna(wr) else f"{wr:.0%} ({low:.0%}-{high:.0%})"

    # Pooled across all champions: a first look at the overall answer
    print("All champions combined:")
    for group, label in [("main", "Mains (incl. OTPs)"), ("otp", "OTPs"),
                         ("other", "Other sampled players"), ("all", "All players (context)")]:
        games, wins = df[f"{group}_games"].sum(), df[f"{group}_wins"].sum()
        low, high = wilson_interval(wins, games)
        print(f"  {label:<24} {games:>7} games  {fmt(wins / games if games else math.nan, low, high)}")
    print()

    view = pd.DataFrame({
        "champion": df.champion_name,
        "mains": df.mains,
        "otps": df.otps,
        "main_games": df.main_games,
        "main_wr (95% CI)": [fmt(*r) for r in zip(df.main_wr, df.main_low, df.main_high)],
        "otp_games": df.otp_games,
        "otp_wr (95% CI)": [fmt(*r) for r in zip(df.otp_wr, df.otp_low, df.otp_high)],
        "other_games": df.other_games,
        "other_wr (95% CI)": [fmt(*r) for r in zip(df.other_wr, df.other_low, df.other_high)],
        "all_wr": df.all_wr.map(lambda x: f"{x:.0%}"),
    })
    print(view[view.mains > 0].to_string(index=False))
