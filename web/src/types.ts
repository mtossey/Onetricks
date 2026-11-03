// Shapes of the JSON files that src/build_site.py writes to web/public/data/.
// Keep these in sync with page_summary(), main() in build_site.py and
// page_payload() in champion_pages.py.

export type Role = "ALL" | "TOP" | "JUNGLE" | "MIDDLE" | "BOTTOM" | "UTILITY";

// ---------- data/champions.json (main table) ----------

/** A win rate with its Wilson interval. wr/low/high are missing below the minimum games. */
export interface WinRateCell {
  games: number;
  wr?: number;
  low?: number;
  high?: number;
}

/** One champion in one role (role "ALL" holds every game). */
export interface ChampionRow {
  name: string;
  icon: string;
  role: Role;
  role_share: number;
  mains: number;
  otps: number;
  main: WinRateCell;
  otp: WinRateCell;
  all: WinRateCell;
  pick_rate: number;
  slug: string | null; // route /champion/<slug>; null when no main plays it
}

export interface IndexData {
  site_name: string;
  summary: {
    matches: number;
    players: number;
    top_patches: string[];
    top_patch_share: number;
    built: string;
  };
  thresholds: { min_games: number };
  champions: ChampionRow[];
}

// ---------- data/champions/<slug>.json (one champion page) ----------

/** [name, icon URL] */
export type Entry = [string, string];
/** [name, icon URL, kind] */
export type ItemEntry = [string, string, "boots" | "trinket" | "completed" | "other"];

/**
 * One game as stored in the file: a list, to keep files small.
 * [player index, role, win (0/1), kills, deaths, assists, final item IDs,
 *  [spell, spell], [tree, keystone, rune, rune, rune, tree, rune, rune],
 *  [offense, flex, defense shards], lane opponent champion ID or null,
 *  starting item IDs (sorted), completed items in the order finished,
 *  skill order as a string such as "QEWQQRQ"]
 */
export type RawGame = [
  number, string, number, number, number, number, number[], number[], number[], number[], number | null,
  number[], number[], string,
];

/** The same game with named fields (see toGame in lib/stats.ts). */
export interface Game {
  player: number;
  role: string;
  win: number;
  kills: number;
  deaths: number;
  assists: number;
  items: number[];
  spells: number[];
  runes: number[];
  shards: number[];
  opponent: number | null;
  start: number[];
  build: number[];
  skills: string;
}

export interface Player {
  riot_id: string;
  tier: string;
  lp: number;
  otp: boolean;
  share: number; // share of their window on this champion
}

export interface Lookup {
  items: Record<string, ItemEntry>;
  spells: Record<string, Entry>;
  runes: Record<string, Entry>;
  trees: Record<string, number[][]>; // tree ID -> rows of rune IDs, row 0 = keystones
  shards: Record<string, Entry>;
  shard_rows: number[][];
  champions: Record<string, Entry>;
}

export interface ChampionData {
  champion: { name: string; icon: string };
  abilities: Entry[]; // Q, W, E, R
  players: Player[];
  games: RawGame[];
  lookup: Lookup;
  site_name: string;
  built: string;
  window_size: number;
}
