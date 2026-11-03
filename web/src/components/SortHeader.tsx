import type { ReactNode } from "react";
import type { Sort } from "../lib/useSort";

interface Props<K extends string> {
  column: K;
  sort: Sort<K>;
  className?: string;
  children: ReactNode;
}

/** A column header that sorts the table when clicked, with an arrow on the sorted column. */
export function SortHeader<K extends string>({ column, sort, className, children }: Props<K>) {
  const on = sort.key === column;
  const classes = [className, on ? "sorted" : "", on && sort.asc ? "asc" : ""].filter(Boolean).join(" ");
  return (
    <th className={classes} onClick={() => sort.sortBy(column)}
        aria-sort={on ? (sort.asc ? "ascending" : "descending") : "none"}>
      {children}
    </th>
  );
}
