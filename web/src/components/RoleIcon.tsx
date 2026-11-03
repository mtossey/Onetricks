import type { Role } from "../types";

// Our own role icons in the style of the in-game position icons (24x24 SVG,
// drawn in the text color so they follow hover and selected colors). Lane
// icons show the map: the lane itself bright, the rest of the map faint.
const FAINT = 0.3;

const PATHS: Record<Role, JSX.Element> = {
  // A square inside a square
  ALL: (
    <>
      <path d="M3 3h18v18H3z M5.5 5.5v13h13v-13z" fill="currentColor" fillRule="evenodd" opacity={0.75} />
      <path d="M9 9h6v6H9z" fill="currentColor" />
    </>
  ),
  // Top lane: the top-left edge of the map
  TOP: (
    <>
      <path d="M21 7v14H7l4-4h6V11z" fill="currentColor" opacity={FAINT} />
      <path d="M10 10h4v4h-4z" fill="currentColor" opacity={FAINT} />
      <path d="M3 3h18l-4 4H7v10l-4 4z" fill="currentColor" />
    </>
  ),
  // Four grass blades growing from one point
  JUNGLE: (
    <>
      <path d="M10.5 22C8.5 18 6 13.5 2.5 10.5c4 1.5 7 4.5 8.8 8.5z" fill="currentColor" />
      <path d="M10.5 22C7.5 16 6.5 8.5 8.5 1.5c1.8 6.5 3.5 13 3.3 20.5z" fill="currentColor" />
      <path d="M11.8 22c.2-6 1.4-12 4-17 .6 6-.8 12-2.6 17z" fill="currentColor" />
      <path d="M13.2 22c1.5-4.5 4.5-8.5 8.3-11-1.8 4-4.3 8-7 11z" fill="currentColor" />
    </>
  ),
  // Mid lane: the diagonal, with the two bases faint
  MIDDLE: (
    <>
      <path d="M3 3h11l-4 4H7v3l-4 4z" fill="currentColor" opacity={FAINT} />
      <path d="M21 21H10l4-4h3v-3l4-4z" fill="currentColor" opacity={FAINT} />
      <path d="M17 3h4v4L7 21H3v-4z" fill="currentColor" />
    </>
  ),
  // Bot lane: the bottom-right edge of the map
  BOTTOM: (
    <>
      <path d="M3 17V3h14l-4 4H7v6z" fill="currentColor" opacity={FAINT} />
      <path d="M10 10h4v4h-4z" fill="currentColor" opacity={FAINT} />
      <path d="M21 21H3l4-4h10V7l4-4z" fill="currentColor" />
    </>
  ),
  // A gem on top, angular wings, and a long blade down the middle
  UTILITY: (
    <>
      <path d="M8.5 2h7l2 3L12 9.8 6.5 5z" fill="currentColor" />
      <path d="M10.6 8.8L.8 6.8l2.6 4.4 2.3-.6 1 3.4 4.4-2.6z" fill="currentColor" />
      <path d="M13.4 8.8l9.8-2-2.6 4.4-2.3-.6-1 3.4-4.4-2.6z" fill="currentColor" />
      <path d="M10.4 11h3.2l1 2.7L12 22.5l-2.6-8.8z" fill="currentColor" />
    </>
  ),
};

export function RoleIcon({ role }: { role: Role }) {
  return (
    <svg className="role-icon" viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
      {PATHS[role]}
    </svg>
  );
}
