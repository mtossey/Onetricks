import { useState, type ReactNode } from "react";
import { pct } from "../lib/format";
import { tally, type Tally } from "../lib/stats";
import type { Entry, Game, ItemEntry, Lookup } from "../types";
import { BuildPathCard } from "./BuildPathCard";
import { Icon } from "./Icon";
import { RunesCard } from "./RunesCard";
import { SkillOrderCard } from "./SkillOrderCard";

interface OptionCardProps<K> {
  title: string;
  subtitle?: string;
  options: Tally<K>[];
  total: number;
  limit: number;
  /** "wide" spans two grid columns, "full" the whole row; both list options in columns */
  size?: "normal" | "wide" | "full";
  render: (option: Tally<K>) => ReactNode;
}

/** A card listing options (spells, boots, items) with pick rate, win rate and games. */
function OptionCard<K extends string | number>({ title, subtitle, options, total, limit, size = "normal", render }: OptionCardProps<K>) {
  const rows = options.slice(0, limit).map((c) => (
    <div className="opt" key={c.key}>
      {render(c)}
      <div className="stats">
        <b>{pct(c.games / total)}</b>
        <small>{pct(c.wins / c.games)} WR · {c.games} g</small>
      </div>
    </div>
  ));
  return (
    <section className={`card${size === "normal" ? "" : ` ${size}`}`}>
      <h2>{title}{subtitle && <small>{subtitle}</small>}</h2>
      {rows.length === 0 ? <div className="empty">No games</div> : size === "normal" ? rows : <div className="opt-columns">{rows}</div>}
    </section>
  );
}

function Named({ entry }: { entry?: Entry | ItemEntry }) {
  return (
    <>
      <div className="icons"><Icon entry={entry} /></div>
      <div className="label">{entry ? entry[0] : "Unknown"}</div>
    </>
  );
}

/** "Games with X" line at the top of a card filtered by the other card, with a clear button. */
function CrossFilter({ entry, round, text, onClear }: { entry?: Entry | ItemEntry; round?: boolean; text: string; onClear: () => void }) {
  return (
    <div className="cross-filter">
      <Icon entry={entry} className={round ? "round" : undefined} />
      <span>{text}</span>
      <button type="button" onClick={onClear}>Clear</button>
    </div>
  );
}

export function BuildTab({ games, lookup, abilities }: { games: Game[]; lookup: Lookup; abilities: Entry[] }) {
  // Runes and build path filter each other: a clicked keystone limits the build
  // path to games with it, and a clicked first item limits the runes.
  const [keystone, setKeystone] = useState<number | null>(null);
  const [firstItem, setFirstItem] = useState<number | null>(null);
  // A choice only counts if some game in view has it (the role or player may have changed)
  const ks = games.some((g) => g.runes[1] === keystone) ? keystone : null;
  let item = games.some((g) => g.build[0] === firstItem) ? firstItem : null;
  if (ks !== null && item !== null && !games.some((g) => g.runes[1] === ks && g.build[0] === item)) item = null;
  const runeGames = item === null ? games : games.filter((g) => g.build[0] === item);
  const itemGames = ks === null ? games : games.filter((g) => g.runes[1] === ks);

  const n = games.length;
  const itemsOfKind = (g: Game, kind: string) => g.items.filter((i) => lookup.items[i]?.[2] === kind);
  // Spell pairs are stored sorted, so Flash + Ignite and Ignite + Flash count together
  const spells = tally(games, (g) => [g.spells.join(",")]);
  const boots = tally(games, (g) => itemsOfKind(g, "boots"));
  const items = tally(games, (g) => itemsOfKind(g, "completed"));
  // Starting items are stored sorted, so the same set bought in any order counts once
  const starts = tally(games.filter((g) => g.start.length > 0), (g) => [g.start.join(",")]);

  return (
    <>
      <div className="cards">
        <div className="pair">
          <RunesCard games={runeGames} lookup={lookup} chosen={ks} onChoose={setKeystone}
                     filter={item !== null && <CrossFilter entry={lookup.items[item]}
                       text={`${runeGames.length} games with ${lookup.items[item]?.[0] ?? "this item"} first`}
                       onClear={() => setFirstItem(null)} />} />
          <BuildPathCard games={itemGames} lookup={lookup} chosen={item} onChoose={setFirstItem}
                         filter={ks !== null && <CrossFilter entry={lookup.runes[ks]} round
                           text={`${itemGames.length} games with ${lookup.runes[ks]?.[0] ?? "this keystone"}`}
                           onClear={() => setKeystone(null)} />} />
        </div>
        <OptionCard title="Starting items" subtitle="bought in the first minute" options={starts} total={n} limit={4}
                    render={(c) => {
          const ids = c.key.split(",");
          return (
            <>
              <div className="icons">{ids.map((id, i) => <Icon key={i} entry={lookup.items[id]} />)}</div>
              <div className="label">{[...new Set(ids)].map((id) => lookup.items[id]?.[0] ?? "?").join(" + ")}</div>
            </>
          );
        }} />
        <OptionCard title="Summoner spells" options={spells} total={n} limit={4} render={(c) => {
          const pair = c.key.split(",").map((id) => lookup.spells[id]);
          return (
            <>
              <div className="icons">{pair.map((s, i) => <Icon key={i} entry={s} />)}</div>
              <div className="label">{pair.map((s) => (s ? s[0] : "?")).join(" + ")}</div>
            </>
          );
        }} />
        <OptionCard title="Boots" subtitle="share of games ending with them" options={boots} total={n} limit={4}
                    render={(c) => <Named entry={lookup.items[c.key]} />} />
        <SkillOrderCard games={games} abilities={abilities} />
        <OptionCard title="Completed items" subtitle="share of games ending with each item" options={items} total={n}
                    limit={12} size="full" render={(c) => <Named entry={lookup.items[c.key]} />} />
      </div>
      <p className="note">
        Pick rate is the share of these games that used the option; WR is the win rate in those games. Boots and
        completed items are the final inventory at the end of each game; starting items, build path and skill order
        come from each game's timeline.
      </p>
    </>
  );
}
