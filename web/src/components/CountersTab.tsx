import { pct } from "../lib/format";
import { tally } from "../lib/stats";
import { useSort } from "../lib/useSort";
import type { Game, Lookup } from "../types";
import { Icon } from "./Icon";
import { SortHeader } from "./SortHeader";

type Column = "opponent" | "games" | "winrate";

export function CountersTab({ games, lookup, championName }: { games: Game[]; lookup: Lookup; championName: string }) {
  const sort = useSort<Column>("games", ["opponent"]);
  // tally lists the most played opponents first; other columns sort from that order
  const all = tally(games.filter((g) => g.opponent !== null), (g) => [g.opponent!]);
  const rows = sort.sorted(all, (c, key) => {
    if (key === "opponent") return lookup.champions[c.key]?.[0] ?? String(c.key);
    if (key === "winrate") return c.wins / c.games;
    return c.games;
  });
  if (rows.length === 0) return <div className="empty">No lane opponents recorded.</div>;

  return (
    <>
      <div className="table-box boxed">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <SortHeader column="opponent" sort={sort} className="left">Lane opponent</SortHeader>
              <SortHeader column="games" sort={sort}>Games</SortHeader>
              <SortHeader column="winrate" sort={sort}>Win rate<span className="sub">of {championName} mains</span></SortHeader>
            </tr>
          </thead>
          <tbody>
            {rows.map((c, i) => {
              const champ = lookup.champions[c.key];
              return (
                <tr key={c.key}>
                  <td className="rank">{i + 1}</td>
                  <td className="left">
                    <div className="champ"><Icon entry={champ} />{champ ? champ[0] : c.key}</div>
                  </td>
                  <td className="num">{c.games}</td>
                  <td className="wr">{pct(c.wins / c.games)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="note">
        Each row is {championName} mains' record against that champion in the same role. Most rows have only a few
        games, so treat them as rough. Click a column header to sort.
      </p>
    </>
  );
}
