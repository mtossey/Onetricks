import { pct } from "../lib/format";
import { tally, type Tally } from "../lib/stats";
import type { Entry, Game } from "../types";

const KEYS = ["Q", "W", "E", "R"];
const GRID_LEVELS = 15;

/**
 * Max priority: the order in which Q, W and E reach their 5th (last) point,
 * written like "QEW". Abilities that never reach 5 points in a short game
 * come last, more points first.
 */
function maxOrder(skills: string): string {
  const fifthPoint = (key: string) => {
    let count = 0;
    for (let i = 0; i < skills.length; i++) {
      if (skills[i] === key && ++count === 5) return i;
    }
    return Infinity;
  };
  const points = (key: string) => skills.split(key).length - 1;
  return ["Q", "W", "E"].sort((a, b) => fifthPoint(a) - fifthPoint(b) || points(b) - points(a)).join("");
}

function AbilityIcon({ ability, letter }: { ability?: Entry; letter: string }) {
  return (
    <span className="ability" title={ability ? `${letter}: ${ability[0]}` : letter}>
      {ability && <img src={ability[1]} alt={ability[0]} loading="lazy" />}
      <b>{letter}</b>
    </span>
  );
}

function Stats({ c, total }: { c: Tally<string>; total: number }) {
  return (
    <div className="stats">
      <b>{pct(c.games / total)}</b>
      <small>{pct(c.wins / c.games)} WR · {c.games} g</small>
    </div>
  );
}

export function SkillOrderCard({ games, abilities }: { games: Game[]; abilities: Entry[] }) {
  const ability = (letter: string) => abilities[KEYS.indexOf(letter)];
  const withSkills = games.filter((g) => g.skills.length >= 3);
  if (withSkills.length === 0) return null;
  const n = withSkills.length;

  const priorities = tally(withSkills, (g) => [maxOrder(g.skills)]);
  const firstThree = tally(withSkills, (g) => [g.skills.slice(0, 3)]);
  // The grid: the most common exact order of the first 15 points, among games
  // that reached level 15
  const long = withSkills.filter((g) => g.skills.length >= GRID_LEVELS);
  const sequences = tally(long, (g) => [g.skills.slice(0, GRID_LEVELS)]);
  const top = sequences[0];

  return (
    <section className="card full">
      <h2>Skill order</h2>
      <div className="skill-layout">
        <div>
          <div className="path-label">Max priority</div>
          {priorities.slice(0, 3).map((c) => (
            <div key={c.key} className="opt">
              <div className="icons skill-chain">
                {c.key.split("").map((k, i) => (
                  <span key={k} className="chain-step">
                    {i > 0 && <span className="chain-arrow">›</span>}
                    <AbilityIcon ability={ability(k)} letter={k} />
                  </span>
                ))}
              </div>
              <Stats c={c} total={n} />
            </div>
          ))}
        </div>
        <div>
          <div className="path-label">Levels 1 to 3</div>
          {firstThree.slice(0, 3).map((c) => (
            <div key={c.key} className="opt">
              <div className="icons skill-chain">
                {c.key.split("").map((k, i) => <AbilityIcon key={i} ability={ability(k)} letter={k} />)}
              </div>
              <Stats c={c} total={n} />
            </div>
          ))}
        </div>
      </div>

      {top && (
        <>
          <div className="path-label" style={{ marginTop: 14 }}>
            Most common order to level {GRID_LEVELS}: {pct(top.games / long.length)} of {long.length} games ·{" "}
            {pct(top.wins / top.games)} WR
          </div>
          <div className="skill-grid-box">
            <table className="skill-grid">
              <tbody>
                {KEYS.map((k) => (
                  <tr key={k}>
                    <th><AbilityIcon ability={ability(k)} letter={k} /></th>
                    {top.key.split("").map((taken, level) => (
                      <td key={level} className={taken === k ? `on skill-${k}` : ""}>{taken === k ? level + 1 : ""}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      <p className="note">
        Max priority is the order in which Q, W and E reach their last point. Percentages are out of the {n} games
        with a recorded skill order.
      </p>
    </section>
  );
}
