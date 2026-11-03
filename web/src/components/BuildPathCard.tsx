import type { ReactNode } from "react";
import { pct } from "../lib/format";
import { tally } from "../lib/stats";
import type { Game, Lookup } from "../types";
import { Icon } from "./Icon";

// Each column lists items finished in these positions of the build (0 = 1st item).
// Few games reach a 5th or 6th item, so everything from the 4th on is one column.
const SLOTS = [
  { label: "2nd item", from: 1, to: 2 },
  { label: "3rd item", from: 2, to: 3 },
  { label: "4th+ items", from: 3, to: Infinity },
];
const OPTIONS_PER_SLOT = 4;

interface BuildPathCardProps {
  games: Game[];
  lookup: Lookup;
  /** The first item the reader clicked, or null to show the most common one */
  chosen: number | null;
  onChoose: (item: number | null) => void;
  /** Shown when the games are filtered by a choice in another card */
  filter?: ReactNode;
}

/**
 * Build path: completed items in the order they were finished (boots not
 * included). Choosing a first item shows what was built after it, so the
 * later columns only count games that started with that item.
 */
export function BuildPathCard({ games, lookup, chosen, onChoose, filter }: BuildPathCardProps) {
  const withBuild = games.filter((g) => g.build.length > 0);
  if (withBuild.length === 0) {
    return (
      <section className="card">
        <h2>Build path</h2>
        {filter}
        <div className="empty">No completed items in these games</div>
      </section>
    );
  }
  const firstItems = tally(withBuild, (g) => [g.build[0]]);
  // null means "All": the later columns then count every game with a build
  const first = firstItems.some((c) => c.key === chosen) ? chosen : null;
  const after = first === null ? withBuild : withBuild.filter((g) => g.build[0] === first);

  return (
    <section className="card">
      <h2>Build path<small>click a first item to see the runes used with it</small></h2>
      {filter}

      <div className="path-first">
        <span className="path-label">1st item</span>
        <div className="pills">
          <button type="button" className={`pill all-pill${first === null ? " on" : ""}`} onClick={() => onChoose(null)}>
            All
          </button>
          {firstItems.slice(0, 6).map((c) => (
            <button key={c.key} type="button" className={`pill item-pill${c.key === first ? " on" : ""}`}
                    onClick={() => onChoose(c.key === chosen ? null : c.key)}>
              <Icon entry={lookup.items[c.key]} />
              <span className="pill-stats">
                <b>{pct(c.games / withBuild.length, 0)}</b>
                <small>{pct(c.wins / c.games, 0)} WR · {c.games} g</small>
              </span>
            </button>
          ))}
        </div>
      </div>

      <div className="path-slots">
        {SLOTS.map((slot) => {
          // Items in these positions, in games that started with the chosen first item
          // (or in every game with All).
          // An item counts once per game, so the 4th+ pick rate is the share of
          // games that finished it anywhere from 4th on.
          const options = tally(after, (g) => g.build.slice(slot.from, slot.to));
          return (
            <div key={slot.label} className="path-slot">
              <div className="path-label">{slot.label}</div>
              {options.length === 0 && <div className="empty">-</div>}
              {options.slice(0, OPTIONS_PER_SLOT).map((c) => (
                <div key={c.key} className="opt">
                  <div className="icons"><Icon entry={lookup.items[c.key]} /></div>
                  <div className="stats">
                    <b>{pct(c.games / after.length, 0)}</b>
                    <small>{pct(c.wins / c.games, 0)} WR · {c.games} g</small>
                  </div>
                </div>
              ))}
            </div>
          );
        })}
      </div>
      <p className="note">
        {first === null
          ? `Percentages are out of all ${after.length} games with a completed item. Choose a first item to see what followed it.`
          : `Percentages in the later columns are out of the ${after.length} games that started with ${lookup.items[first]?.[0] ?? "this item"}.`}
      </p>
    </section>
  );
}
