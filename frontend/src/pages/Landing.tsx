import { Link } from "react-router-dom";

const FEATURES = [
  {
    icon: "📊",
    title: "Forecast vs actual",
    body: "See the wind forecast you had at the day-ahead cutoff, next to what actually happened.",
  },
  {
    icon: "🎯",
    title: "Know the miss",
    body: "MAE, bias and percentiles quantify how wrong the forecast usually is — in megawatts.",
  },
  {
    icon: "🛡️",
    title: "Size your margin",
    body: "The P90 shortfall tells you how far wind fell below forecast 9 times out of 10.",
  },
  {
    icon: "🔍",
    title: "Break it down",
    body: "Error by horizon, by hour of day and by wind level — find where the forecast drifts.",
  },
];

export function Landing() {
  return (
    <div className="fade">
      <header className="landing-nav">
        <div className="brand">
          <span className="dot" />
          Wind Forecast Monitor
        </div>
        <Link to="/overview" className="btn-sm">
          Open dashboard →
        </Link>
      </header>

      <section className="hero">
        <span className="eyebrow rise">GB national wind · January 2026</span>
        <h1 className="rise" style={{ animationDelay: "0.05s" }}>
          See the forecast you had. Measure how wrong it was.
        </h1>
        <p className="rise" style={{ animationDelay: "0.12s" }}>
          A day-ahead trading view for UK wind: the forecast at decision time, the actual
          generation beside it, and the error metrics you need to set a safe buying margin.
        </p>
        <div className="cta rise" style={{ animationDelay: "0.18s" }}>
          <Link to="/overview" className="btn">
            Launch dashboard
          </Link>
          <Link to="/methodology" className="btn ghost">
            How it works
          </Link>
        </div>
      </section>

      <section className="features">
        {FEATURES.map((f, i) => (
          <div className="feature rise" key={f.title} style={{ animationDelay: `${0.1 + i * 0.07}s` }}>
            <div className="ic">{f.icon}</div>
            <h3>{f.title}</h3>
            <p>{f.body}</p>
          </div>
        ))}
      </section>

      <footer className="landing-foot">
        Built on Elexon BMRS open data (FUELHH actuals, WINDFOR forecasts). No look-ahead.
      </footer>
    </div>
  );
}
