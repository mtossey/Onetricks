import { pct } from "../lib/format";
import { ROLES } from "../lib/roles";
import type { Role } from "../types";
import { RoleIcon } from "./RoleIcon";

interface Props {
  role: Role;
  onChange: (role: Role) => void;
  /** Games per role. When given, each button shows its share and empty roles are disabled. */
  counts?: Record<Role, number>;
}

export function RoleButtons({ role, onChange, counts }: Props) {
  return (
    <div className="roles" role="group" aria-label="Role">
      {ROLES.map(({ key, label, short }) => (
        <button
          key={key}
          type="button"
          // The full name goes in the tooltip and for screen readers
          title={label}
          aria-label={label}
          aria-pressed={key === role}
          disabled={counts !== undefined && counts[key] === 0}
          onClick={() => onChange(key)}
        >
          <RoleIcon role={key} />
          <span className="role-short">{short}</span>
          {counts && key !== "ALL" && <small>{pct(counts[key] / counts.ALL, 0)}</small>}
        </button>
      ))}
    </div>
  );
}
