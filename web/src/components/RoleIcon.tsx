import type { Role } from "../types";

// Lane icons are Riot's in-game position icons (game art, which Riot's
// developer policies allow), in web/public/roles/. There is no in-game icon for
// "all roles", so that one is our own SVG, drawn in the same gold.
const IMAGES: Partial<Record<Role, string>> = {
  TOP: "roles/top.png",
  JUNGLE: "roles/jungle.png",
  MIDDLE: "roles/mid.png",
  BOTTOM: "roles/bot.png",
  UTILITY: "roles/support.png",
};

// A square inside a square, the same shape language as the lane icons
const ALL_ICON = (
  <>
    <path d="M3 3h18v18H3z M5.5 5.5v13h13v-13z" fill="currentColor" fillRule="evenodd" opacity={0.75} />
    <path d="M9 9h6v6H9z" fill="currentColor" />
  </>
);

export function RoleIcon({ role }: { role: Role }) {
  const src = IMAGES[role];
  if (src) return <img className="role-icon" src={src} width="22" height="22" alt="" />;
  return (
    <svg className="role-icon" viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
      {ALL_ICON}
    </svg>
  );
}
