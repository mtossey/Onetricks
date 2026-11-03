import type { Entry, ItemEntry } from "../types";

/** A Data Dragon icon with its name as alt text and tooltip. Renders nothing for an unknown ID. */
export function Icon({ entry, className }: { entry?: Entry | ItemEntry; className?: string }) {
  if (!entry) return null;
  return <img className={className} src={entry[1]} alt={entry[0]} title={entry[0]} loading="lazy" />;
}
