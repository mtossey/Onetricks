import { HashRouter, Route, Routes } from "react-router";
import { ChampionPage } from "./pages/ChampionPage";
import { ChampionTable } from "./pages/ChampionTable";

// HashRouter keeps the route after a # (#/champion/Talon), so the built site
// works on any static host without server rewrite rules.
export function App() {
  return (
    <HashRouter>
      <Routes>
        <Route path="/" element={<ChampionTable />} />
        <Route path="/champion/:slug" element={<ChampionPage />} />
        <Route path="*" element={<ChampionTable />} />
      </Routes>
    </HashRouter>
  );
}
