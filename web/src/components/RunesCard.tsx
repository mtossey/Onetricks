import { useState, type ReactNode } from "react";
import { pct } from "../lib/format";
import { tally, winRate, type Tally } from "../lib/stats";
import type { Entry, Game, Lookup } from "../types";
import { Icon } from "./Icon";

/**
 * Win rate, pick rate and games under a rune, like the stats grid on lolalytics.
 * The win rate is green or red when it is 1.5+ points above or below the average.
 */
function RuneStats({ c, total, average }: { c?: Tally<number>; total: number; average: number }) {
  if (!c) {
    return (
      <div className="rs"><span className="dash">-</span><span className="dash">0%</span><span className="dash">0</span></div>
    );
  }
  const wr = c.wins / c.games;
  const cls = wr - average >= 0.015 ? "good" : average - wr >= 0.015 ? "bad" : "";
  return (
    <div className="rs">
      <span className={`rwr ${cls}`}>{pct(wr)}</span>
      <span className="rpick">{pct(c.games / total)}</span>
      <span>{c.games}</span>
    </div>
  );
}

interface RuneProps {
  entry?: Entry;
  on: boolean;
  size?: "" | "small" | "tiny";
  stats: Tally<number> | undefined;
  total: number;
  average: number;
}

/** One rune icon (lit when part of the most common rune page) with its stats underneath. */
function Rune({ entry, on, size = "", stats, total, average }: RuneProps) {
  return (
    <div className={["rune", size, on ? "on" : ""].filter(Boolean).join(" ")} title={entry?.[0]}>
      {entry && <img src={entry[1]} alt={entry[0]} loading="lazy" />}
      <RuneStats c={stats} total={total} average={average} />
    </div>
  );
}

const byKey = (rows: Tally<number>[]) => new Map(rows.map((c) => [c.key, c]));

interface RunesCardProps {
  games: Game[];
  lookup: Lookup;
  /** The keystone the reader clicked, or null to show the most common one */
  chosen: number | null;
  onChoose: (keystone: number | null) => void;
  /** Shown when the games are filtered by a choice in another card */
  filter?: ReactNode;
}

export function RunesCard({ games, lookup, chosen, onChoose, filter }: RunesCardProps) {
  // The secondary tree the reader clicked, remembered with its keystone so it
  // resets to the most common tree when the keystone changes
  const [treeChoice, setTreeChoice] = useState<{ keystone: number; tree: number } | null>(null);
  const runes = lookup.runes;

  // 1. Keystones used in these games, most common first. g.runes is
  //    [primary tree, keystone, rune, rune, rune, secondary tree, rune, rune].
  const keystones = tally(games, (g) => [g.runes[1]]);
  // With "All" (nothing chosen) the trees show the most common keystone, since
  // only one tree can be drawn; the build path then counts every game
  const picked = keystones.some((k) => k.key === chosen) ? chosen : null;
  const keystone = picked ?? keystones[0].key;
  const kGames = games.filter((g) => g.runes[1] === keystone);
  const n = kGames.length;
  const average = winRate(kGames); // everything below the keystone row compares with this

  // 2. The most common full rune page with this keystone. Its runes are lit.
  const topPage = tally(kGames, (g) => [g.runes.join(",")])[0].key;
  const page = topPage.split(",").map(Number);
  const pageGames = kGames.filter((g) => g.runes.join(",") === topPage);

  // 3. Primary tree, drawn whole. Keystone row stats are across all games in
  //    view; the rows below are within games with the chosen keystone.
  const keystoneStats = byKey(keystones);
  const primaryStats = byKey(tally(kGames, (g) => g.runes.slice(2, 5)));
  const allAverage = winRate(games);

  // 4. Secondary tree: the reader can switch between the trees used
  const secondaryTrees = tally(kGames, (g) => [g.runes[5]]);
  const pickedTree = treeChoice?.keystone === keystone ? treeChoice.tree : null;
  const secondary = secondaryTrees.some((t) => t.key === pickedTree) ? pickedTree! : page[5];
  const secondaryStats = byKey(tally(kGames.filter((g) => g.runes[5] === secondary), (g) => g.runes.slice(6, 8)));

  return (
    <section className="card">
      <h2>Runes<small>click a keystone to see the items built with it</small></h2>
      {filter}

      <div className="pills">
        <button type="button" className={`pill all-pill${picked === null ? " on" : ""}`} onClick={() => onChoose(null)}>
          All
        </button>
        {keystones.map((k) => (
          <button key={k.key} type="button" className={`pill big${k.key === picked ? " on" : ""}`}
                  onClick={() => onChoose(k.key === chosen ? null : k.key)}>
            <Icon entry={runes[k.key]} className="round" />
            <span>{pct(k.games / games.length, 0)}</span>
          </button>
        ))}
      </div>

      {picked === null && keystones.length > 1 && (
        <p className="tree-note">Trees below: {runes[keystone]?.[0] ?? "the most common keystone"}, the most common keystone. Click a keystone to see another.</p>
      )}

      <div className="rune-layout">
        <div className="rune-tree">
          {(lookup.trees[page[0]] ?? []).map((row, i) => (
            <div key={i} className={`rune-row${i === 0 ? " keystone-row" : ""}`}>
              {row.map((id) => i === 0
                ? <Rune key={id} entry={runes[id]} on={page.includes(id)} stats={keystoneStats.get(id)} total={games.length} average={allAverage} />
                : <Rune key={id} entry={runes[id]} on={page.includes(id)} stats={primaryStats.get(id)} total={n} average={average} />)}
            </div>
          ))}
        </div>

        <div className="rune-tree">
          <div className="pills">
            {secondaryTrees.map((t) => (
              <button key={t.key} type="button" className={`pill${t.key === secondary ? " on" : ""}`}
                      onClick={() => setTreeChoice({ keystone, tree: t.key })}>
                <Icon entry={runes[t.key]} className="round" />
                <span>{pct(t.games / n, 0)}</span>
              </button>
            ))}
          </div>
          {(lookup.trees[secondary] ?? []).slice(1).map((row, i) => (
            <div key={i} className="rune-row">
              {row.map((id) => (
                <Rune key={id} entry={runes[id]} size="small" on={secondary === page[5] && page.slice(6).includes(id)}
                      stats={secondaryStats.get(id)} total={n} average={average} />
              ))}
            </div>
          ))}

          {/* Stat shards: the top page's most common shard in each row is lit */}
          <div className="shard-grid">
            {lookup.shard_rows.map((row, i) => {
              const stats = byKey(tally(kGames, (g) => [g.shards[i]]));
              const top = tally(pageGames, (g) => [g.shards[i]])[0];
              return (
                <div key={i} className="rune-row">
                  {row.map((id) => (
                    <Rune key={id} entry={lookup.shards[id]} size="tiny" on={top?.key === id}
                          stats={stats.get(id)} total={n} average={average} />
                  ))}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <p className="note">
        Lit runes are the most common rune page with this keystone. Under each rune: win rate (green or red when 1.5+
        points from the average), pick rate in blue, and games. Keystones are counted across all games shown; every
        other rune and shard within games with the keystone shown. All keeps the build path on every game.
      </p>
    </section>
  );
}
