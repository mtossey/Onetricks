import { useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { Footer } from "../components/Footer";
import { RoleButtons } from "../components/RoleButtons";
import { SortHeader } from "../components/SortHeader";
import { fmtInt, pct } from "../lib/format";
import { roleFromSlug, slugFromRole } from "../lib/roles";
import { useJson } from "../lib/useJson";
import { useSort } from "../lib/useSort";
import type { ChampionRow, IndexData, Role, WinRateCell } from "../types";

type SortKey = "rank" | "name" | "mains" | "otps" | "main" | "otp" | "all" | "pick_rate";

const COLUMNS: { key: SortKey; label: string; sub?: string }[] = [
  { key: "rank", label: "#" },
  { key: "name", label: "Champion" },
  { key: "mains", label: "Mains", sub: "30%+ of games" },
  { key: "otps", label: "OTPs", sub: "70%+ of games" },
  { key: "main", label: "Mains WR" },
  { key: "otp", label: "OTPs WR" },
  { key: "all", label: "All players WR", sub: "everyone on the champion" },
  { key: "pick_rate", label: "Pick rate" },
];

/** The value a column sorts by. null (no win rate) always sorts last. */
function sortValue(c: ChampionRow, key: SortKey): string | number | null {
  if (key === "main" || key === "otp" || key === "all") return c[key].wr ?? null;
  if (key === "rank") return null;
  return c[key];
}

function WinRate({ cell }: { cell: WinRateCell }) {
  if (cell.wr === undefined) {
    return (
      <td className="wr">
        <span className="dash" title={`${fmtInt(cell.games)} games, too few to show`}>-</span>
        <small>{fmtInt(cell.games)} g</small>
      </td>
    );
  }
  const title = `${pct(cell.wr)} (95% interval ${pct(cell.low!)} to ${pct(cell.high!)}), ${fmtInt(cell.games)} games`;
  return (
    <td className="wr" title={title}>
      {pct(cell.wr)}
      <small>{fmtInt(cell.games)} g</small>
    </td>
  );
}

export function ChampionTable() {
  const state = useJson<IndexData>("data/champions.json");
  if (state.status === "loading") return <div className="wrap">Loading…</div>;
  if (state.status === "error") return <div className="wrap">Could not load data: {state.message}</div>;
  return <TableView data={state.data} />;
}

function TableView({ data }: { data: IndexData }) {
  const navigate = useNavigate();
  // The role lives in the URL (#/?role=jungle) so a filtered view can be linked
  const [params, setParams] = useSearchParams();
  const role: Role = roleFromSlug(params.get("role")) ?? "ALL";
  const setRole = (r: Role) => setParams(r === "ALL" ? {} : { role: slugFromRole(r) }, { replace: true });

  const [query, setQuery] = useState("");
  const [onlyMains, setOnlyMains] = useState(true);
  const [onlyOtps, setOnlyOtps] = useState(false);
  const sort = useSort<SortKey>("mains", ["name"]); // names A to Z first, numbers high to low first

  const inRole = useMemo(() => data.champions.filter((c) => c.role === role), [data, role]);
  const shown = useMemo(() => {
    const q = query.trim().toLowerCase();
    const rows = inRole
      .filter((c) => c.name.toLowerCase().includes(q))
      .filter((c) => !onlyMains || c.mains > 0)
      .filter((c) => !onlyOtps || c.otps > 0);
    return sort.sorted(rows, sortValue);
  }, [inRole, query, onlyMains, onlyOtps, sort.key, sort.asc]); // sort.sorted only depends on these two

  // Champion pages open on the role chosen here (All roles opens their main role)
  const championLink = (slug: string) => `/champion/${slug}${role === "ALL" ? "" : `?role=${slugFromRole(role)}`}`;
  const s = data.summary;

  return (
    <div className="wrap">
      <header>
        <h1>
          NA Master+ mains and one-tricks
        </h1>
        <p>
          Which champions do NA Master+ players main and one-trick most, and how do those players do on them? Hover a
          win rate for its 95% interval.
        </p>
      </header>

      <div className="chips">
        <div className="chip"><b>{fmtInt(s.players)}</b>players</div>
        <div className="chip"><b>{fmtInt(s.matches)}</b>ranked solo matches</div>
        <div className="chip">
          <b>{s.top_patches.join(" and ")}</b>patches with {pct(s.top_patch_share, 0)} of games
        </div>
        <div className="chip"><b>NA</b>Challenger, Grandmaster, Master</div>
      </div>

      <div className="controls">
        <RoleButtons role={role} onChange={setRole} />
        <input type="search" placeholder="Search champion" aria-label="Search champion"
               value={query} onChange={(e) => setQuery(e.target.value)} />
        <label>
          <input type="checkbox" checked={onlyMains} onChange={(e) => setOnlyMains(e.target.checked)} /> Only
          champions with mains
        </label>
        <label>
          <input type="checkbox" checked={onlyOtps} onChange={(e) => setOnlyOtps(e.target.checked)} /> Only
          champions with OTPs
        </label>
        <span className="count">{shown.length} of {inRole.length} champions</span>
      </div>

      <div className="table-box">
        <table>
          <thead>
            <tr>
              {/* "#" is the row's position, so it is the one column that does not sort */}
              {COLUMNS.map((col) => col.key === "rank" ? <th key={col.key}>{col.label}</th> : (
                <SortHeader key={col.key} column={col.key} sort={sort}>
                  {col.label}
                  {col.sub && <span className="sub">{col.sub}</span>}
                </SortHeader>
              ))}
            </tr>
          </thead>
          <tbody>
            {shown.map((c, i) => (
              <tr key={c.name} className={c.slug ? "linked" : ""}
                  onClick={() => c.slug && navigate(championLink(c.slug))}>
                <td className="rank">{i + 1}</td>
                <td>
                  <div className="champ">
                    <img src={c.icon} alt="" loading="lazy" />
                    <div>
                      {c.slug ? <Link to={championLink(c.slug)} onClick={(e) => e.stopPropagation()}>{c.name}</Link> : c.name}
                      {role !== "ALL" && <small>{pct(c.role_share, 0)} of its games</small>}
                    </div>
                  </div>
                </td>
                <td className="num">{c.mains ? <span className="tag main">{c.mains}</span> : <span className="dash">0</span>}</td>
                <td className="num">{c.otps ? <span className="tag otp">{c.otps}</span> : <span className="dash">0</span>}</td>
                <WinRate cell={c.main} />
                <WinRate cell={c.otp} />
                <WinRate cell={c.all} />
                <td className="num">{pct(c.pick_rate)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="notes">
        <section>
          <h2>Definitions</h2>
          <ul>
            <li>Each sampled player's window is their newest 30 ranked solo games, remakes removed. Players need at least 15 games to be classified.</li>
            <li><b>Main:</b> 30% or more of the window on the champion. Includes OTPs.</li>
            <li><b>OTP (one-trick):</b> 70% or more of the window on one champion.</li>
            <li><b>Roles:</b> a main counts in their most-played role on the champion, using only those games. Their off-role games (mostly autofill) count in "All roles". A role is listed for a champion once it has {data.thresholds.min_games} games.</li>
          </ul>
        </section>
        <section>
          <h2>Why are mains' win rates above 50%?</h2>
          <p>Players were taken from the current Master+ ladder, so they recently won more than average, mostly on their mains. A high mains win rate shows how these players do, not that the champion is strong.</p>
          <p>"All players WR" is every player on the champion in the same matches, so it shows how the champion itself is doing.</p>
        </section>
        <section>
          <h2>Reading the numbers</h2>
          <p>A dash means fewer than {data.thresholds.min_games} games. The small number under each win rate is its game count.</p>
          <p>Intervals are Wilson 95% intervals on games. Games from the same player are related, so the real uncertainty is somewhat larger, especially for champions with few mains.</p>
        </section>
      </div>

      <Footer siteName={data.site_name} built={s.built} />
    </div>
  );
}
