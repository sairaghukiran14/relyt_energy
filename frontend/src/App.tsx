import { useState } from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import type { Range } from "./api";
import { TopBar } from "./TopBar";
import { Accuracy } from "./pages/Accuracy";
import { DayAhead } from "./pages/DayAhead";
import { Landing } from "./pages/Landing";
import { Methodology } from "./pages/Methodology";
import { Overview } from "./pages/Overview";

function DashboardNav() {
  return (
    <nav className="nav">
      <NavLink to="/overview" className="brand">
        <span className="dot" />
        Wind Forecast Monitor
      </NavLink>
      <div className="nav-links">
        <NavLink to="/overview">Overview</NavLink>
        <NavLink to="/day-ahead">Day-ahead</NavLink>
        <NavLink to="/accuracy">Accuracy</NavLink>
        <NavLink to="/methodology">Methodology</NavLink>
      </div>
    </nav>
  );
}

export default function App() {
  const [range, setRange] = useState<Range>({
    start: "2026-01-02",
    end: "2026-02-01",
    mode: "dayahead",
    horizonH: 24,
  });

  return (
    <Routes>
      <Route path="/" element={<Landing />} />

      <Route
        path="/overview"
        element={
          <>
            <DashboardNav />
            <TopBar range={range} onChange={setRange} />
            <Overview range={range} />
          </>
        }
      />
      <Route
        path="/day-ahead"
        element={
          <>
            <DashboardNav />
            <DayAhead />
          </>
        }
      />
      <Route
        path="/accuracy"
        element={
          <>
            <DashboardNav />
            <TopBar range={range} onChange={setRange} />
            <Accuracy range={range} />
          </>
        }
      />
      <Route
        path="/methodology"
        element={
          <>
            <DashboardNav />
            <Methodology />
          </>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
