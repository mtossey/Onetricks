import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router";
import { BuildTab } from "../components/BuildTab";
import { CountersTab } from "../components/CountersTab";
import { Footer } from "../components/Footer";
import { PlayersTab } from "../components/PlayersTab";
import { RoleButtons } from "../components/RoleButtons";
import { pct } from "../lib/format";
import { ROLES, roleFromSlug, slugFromRole } from "../lib/roles";
import { toGame, winRate } from "../lib/stats";
import { useJson } from "../lib/useJson";
import type { ChampionData, Role } from "../types";

const TABS = [
  { key: "build", label: "Build" },
  { key: "players", label: "Players" },
  { key: "counters", label: "Counters" },
] as const;
type Tab = (typeof TABS)[number]["key"];

export function ChampionPage() {
  const { slug = "" } = useParams();
  // Slugs are Data Dragon IDs like "Talon" or "MonkeyKing". Checking the
  // format keeps anything else in the URL out of the file path we fetch.
  const valid = /^[A-Za-z0-9]+$/.test(slug);
  const state = useJson<ChampionData>(valid ? `data/champions/${slug}.json` : null);

  // Braces matter: an effect may only return a cleanup function, and newer
  // browsers return a Promise from scrollTo, which crashed the page on leaving
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [slug]);

  if (!valid || state.status === "error") {
    return (
      <div className="wrap">
        <Link className="back" to="/">← All champions</Link>
        <p>No page for this champion. Only champions with at least one main have a page.</p>
      </div>
    );
  }
  if (state.status === "loading") return <div className="wrap">Loading…</div>;
  // key={slug} gives each champion fresh state (role, player, rune choices)
  return <ChampionView key={slug} data={state.data} />;
}

function ChampionView({ data }: { data: ChampionData }) {
  const games = useMemo(() => data.games.map(toGame), [data]);
  const [params, setParams] = useSearchParams();
  const [player, setPlayer] = useState<number | null>(null);

  // Games per role, and the champion's most-played role among mains
  const counts = useMemo(() => {
    const c = Object.fromEntries(ROLES.map((r) => [r.key, 0])) as Record<Role, number>;
    for (const g of games) {
      c.ALL += 1;
      if (g.role in c) c[g.role as Role] += 1;
    }
    return c;
  }, [games]);
  const mainRole = ROLES.slice(1).reduce((best, r) => (counts[r.key] > counts[best] ? r.key : best), "TOP" as Role);

  // Role and tab live in the URL (#/champion/Talon?role=jungle&tab=players).
  // "ranking" was the Players tab's old name, so old links still open it.
  const urlRole = roleFromSlug(params.get("role"));
  const role: Role = urlRole && counts[urlRole] > 0 ? urlRole : mainRole;
  const tabParam = params.get("tab") === "ranking" ? "players" : params.get("tab");
  const tab: Tab = TABS.find((t) => t.key === tabParam)?.key ?? "build";
  function update(next: { role?: Role; tab?: Tab }) {
    const r = next.role ?? role, t = next.tab ?? tab;
    setParams({ role: slugFromRole(r), ...(t === "build" ? {} : { tab: t }) }, { replace: true });
  }

  useEffect(() => {
    document.title = `${data.champion.name} mains · NA Master+`;
  }, [data]);

  const inRole = games.filter((g) => role === "ALL" || g.role === role);
  const shown = inRole.filter((g) => player === null || g.player === player);
  const otps = data.players.filter((p) => p.otp).length;
  const mains = data.players.length;

  return (
    <div className="wrap">
      <Link className="back" to="/">← All champions</Link>
      <div className="champ-head">
        <img src={data.champion.icon} alt="" />
        <div>
          <h1>{data.champion.name}</h1>
          <p>
            {mains} {mains === 1 ? "main" : "mains"} ({otps} {otps === 1 ? "OTP" : "OTPs"}) · {games.length} games ·{" "}
            {pct(winRate(games))} win rate on {data.champion.name}
          </p>
        </div>
      </div>

      <div className="bar">
        <RoleButtons role={role} counts={counts} onChange={(r) => update({ role: r })} />
      </div>

      <div className="tabs" role="tablist">
        {TABS.map((t) => (
          <button key={t.key} type="button" role="tab" aria-selected={t.key === tab} onClick={() => update({ tab: t.key })}>
            {t.label}
          </button>
        ))}
      </div>

      {player !== null && (
        <div className="filter-note">
          Showing <b>{data.players[player].riot_id}</b> only ({shown.length} games)
          <button type="button" onClick={() => setPlayer(null)}>Show all mains</button>
        </div>
      )}

      {tab === "players" ? (
        <PlayersTab
          games={inRole}
          players={data.players}
          windowSize={data.window_size}
          onSelect={(p) => {
            setPlayer(p);
            update({ tab: "build" });
            window.scrollTo({ top: 0, behavior: "smooth" });
          }}
        />
      ) : shown.length === 0 ? (
        <div className="empty">No games for this selection.</div>
      ) : tab === "build" ? (
        <BuildTab games={shown} lookup={data.lookup} abilities={data.abilities} />
      ) : (
        <CountersTab games={shown} lookup={data.lookup} championName={data.champion.name} />
      )}

      <Footer siteName={data.site_name} built={data.built}
              extra="Builds come from mains' and OTPs' games only." />
    </div>
  );
}
