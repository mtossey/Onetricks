import { pct } from "../lib/format";
import { useSort } from "../lib/useSort";
import type { Game, Player } from "../types";
import { SortHeader } from "./SortHeader";

type Column = "player" | "rank" | "games" | "share" | "winrate" | "kda";

// Official ladder order. Rank sorts by tier, then LP within the tier.
const TIER_ORDER: Record<string, number> = { Master: 1, Grandmaster: 2, Challenger: 3 };

interface Props {
  games: Game[]; // role-filtered, but not player-filtered, so every main stays listed
  players: Player[];
  windowSize: number;
  onSelect: (player: number) => void;
}

export function PlayersTab({ games, players, windowSize, onSelect }: Props) {
  const sort = useSort<Column>("games", ["player"]);
  const all = players
    .map((p, index) => {
      const mine = games.filter((g) => g.player === index);
      const sum = (f: "win" | "kills" | "deaths" | "assists") => mine.reduce((s, g) => s + g[f], 0);
      return { ...p, index, games: mine.length, wins: sum("win"),
               kda: (sum("kills") + sum("assists")) / Math.max(sum("deaths"), 1) };
    })
    .filter((r) => r.games > 0)
    // Default order: games played, never a made-up skill score (Riot policy).
    // Other columns sort from this order, so ties stay ordered by games.
    .sort((a, b) => b.games - a.games || b.wins / b.games - a.wins / a.games);
  const rows = sort.sorted(all, (r, key) => {
    if (key === "player") return r.riot_id.toLowerCase();
    if (key === "rank") return (TIER_ORDER[r.tier] ?? 0) * 100_000 + r.lp;
    if (key === "share") return r.share;
    if (key === "winrate") return r.wins / r.games;
    return r[key];
  });

  if (rows.length === 0) return <div className="empty">No mains in this role.</div>;

  return (
    <>
      <div className="table-box boxed">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <SortHeader column="player" sort={sort} className="left">Player</SortHeader>
              <SortHeader column="rank" sort={sort} className="left">Rank</SortHeader>
              <SortHeader column="games" sort={sort}>Games</SortHeader>
              <SortHeader column="share" sort={sort}>Play rate<span className="sub">share of their games</span></SortHeader>
              <SortHeader column="winrate" sort={sort}>Win rate</SortHeader>
              <SortHeader column="kda" sort={sort}>KDA</SortHeader>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={r.index} className="linked" title="Show this player's build" onClick={() => onSelect(r.index)}>
                <td className="rank">{i + 1}</td>
                {/* React escapes text, so player-chosen Riot IDs are safe to show */}
                <td className="left">
                  <span className="player">{r.riot_id}</span> {r.otp && <span className="tag otp">OTP</span>}
                </td>
                {/* Riot's emblem instead of the tier name; the name stays as alt text and tooltip */}
                <td className="left">
                  <span className="tier">
                    <img src={`data/tiers/${r.tier}.png`} alt={r.tier} title={r.tier} />
                    <small className="dash">{r.lp} LP</small>
                  </span>
                </td>
                <td className="num">{r.games}</td>
                <td className="num">{pct(r.share, 0)}</td>
                <td className="wr">{pct(r.wins / r.games)}</td>
                <td className="num">{r.kda.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="note">
        Games are on this champion in each player's newest {windowSize} ranked games. Click a column header to sort,
        and a player to see their build.
      </p>
    </>
  );
}
