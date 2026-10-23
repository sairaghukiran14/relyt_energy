import { useState } from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import type { Range } from "./api";
import { TopBar } from "./TopBar";
import { Accuracy } from "./pages/Accuracy";
import { DayAhead } from "./pages/DayAhead";
import { Methodology } from "./pages/Methodology";
import { Overview } from "./pages/Overview";

export default function App() {
  const [range, setRange] = useState<Range>({
    start: "2026-01-02",
    end: "2026-02-01",
    mode: "dayahead",
    horizonH: 24,
  });

  return (
    <>
      <nav className="nav">
        <strong style={{ marginRight: 16 }}>Wind Forecast Monitor</strong>
        <NavLink to="/" end>
          Overview
        </NavLink>
        <NavLink to="/day-ahead">Day-ahead</NavLink>
        <NavLink to="/accuracy">Accuracy</NavLink>
        <NavLink to="/methodology">Methodology</NavLink>
      </nav>

      <Routes>
        <Route
          path="/"
          element={
            <>
              <TopBar range={range} onChange={setRange} />
              <Overview range={range} />
            </>
          }
        />
        <Route path="/day-ahead" element={<DayAhead />} />
        <Route
          path="/accuracy"
          element={
            <>
              <TopBar range={range} onChange={setRange} />
              <Accuracy range={range} />
            </>
          }
        />
        <Route path="/methodology" element={<Methodology />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}
