import { NavLink, Navigate, Route, Routes } from "react-router-dom";

import AnalysisScreen from "./screens/AnalysisScreen";
import MigrationScreen from "./screens/MigrationScreen";
import RepositoryScreen from "./screens/RepositoryScreen";
import ValidationScreen from "./screens/ValidationScreen";
import { useWorkflow } from "./state/WorkflowContext";
import "./App.css";

const steps = [
  { path: "/", label: "01", title: "Source" },
  { path: "/analysis", label: "02", title: "Analyze" },
  { path: "/migration", label: "03", title: "Migrate" },
  { path: "/validation", label: "04", title: "Validate" },
];

function App() {
  const { health, session } = useWorkflow();

  return (
    <div className="app-shell">
      <header className="app-header">
        <NavLink className="brand" to="/">
          <span className="brand-mark">LM</span>
          <span>
            <strong>Legacy-Morph</strong>
            <small>Modernization control room</small>
          </span>
        </NavLink>

        <nav className="step-nav" aria-label="Migration workflow">
          {steps.map((step) => (
            <NavLink
              className={({ isActive }) =>
                `step-link ${isActive ? "step-link--active" : ""}`
              }
              key={step.path}
              to={step.path}
            >
              <span>{step.label}</span>
              {step.title}
            </NavLink>
          ))}
        </nav>

        <div className="runtime-status">
          <span
            className={`status-dot ${
              health?.status === "ok" ? "status-dot--online" : ""
            }`}
          />
          <span>
            <strong>{health?.status === "ok" ? "Backend ready" : "Connecting"}</strong>
            <small>{health?.ai_mode ? `${health.ai_mode} mode` : "checking mode"}</small>
          </span>
        </div>
      </header>

      <main className="app-main">
        {session && (
          <div className="session-strip">
            <span>Active migration</span>
            <strong>{session.id.slice(0, 8)}</strong>
            <span className="session-state">{session.status.replaceAll("_", " ")}</span>
          </div>
        )}

        <Routes>
          <Route path="/" element={<RepositoryScreen />} />
          <Route path="/analysis" element={<AnalysisScreen />} />
          <Route path="/migration" element={<MigrationScreen />} />
          <Route path="/validation" element={<ValidationScreen />} />
          <Route path="*" element={<Navigate replace to="/" />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
