import { useNavigate } from "react-router-dom";

import AnalysisPanel from "../components/AnalysisPanel";
import { api } from "../services/api";
import { useWorkflow } from "../state/WorkflowContext";
import "./AnalysisScreen.css";

function AnalysisScreen() {
  const navigate = useNavigate();
  const workflow = useWorkflow();

  const analyze = async () => {
    if (!workflow.session) return;
    try {
      const result = await workflow.run("analyze", () => api.analyze(workflow.session.id));
      workflow.setAnalysis(result);
    } catch {
      // The shared workflow already exposes the request error.
    }
  };

  const createPlan = async () => {
    try {
      const result = await workflow.run("plan", () => api.createPlan(workflow.session.id));
      workflow.setPlan(result);
    } catch {
      // The shared workflow already exposes the request error.
    }
  };

  const approvePlan = async () => {
    try {
      const result = await workflow.run("approve-plan", () =>
        api.approvePlan(workflow.session.id),
      );
      workflow.setPlan(result);
      navigate("/migration");
    } catch {
      // The shared workflow already exposes the request error.
    }
  };

  if (!workflow.session) {
    return (
      <div className="screen">
        <div className="warning-banner">Create a migration session before analysis.</div>
      </div>
    );
  }

  return (
    <div className="screen analysis-screen">
      <span className="screen-kicker">Structural intelligence</span>
      <h1 className="screen-title">
        Turn code into
        <br />
        <em>evidence.</em>
      </h1>
      <p className="screen-intro">
        Deterministic parsers build the AST and dependency graph first. The AI layer
        then explains business behavior and proposes a migration sequence.
      </p>

      {workflow.error && <div className="error-banner analysis-screen__message">{workflow.error}</div>}

      <section className="panel analysis-screen__panel">
        <div className="panel-header">
          <h2>Repository analysis</h2>
          <button
            className="primary-button"
            disabled={Boolean(workflow.loading)}
            onClick={analyze}
            type="button"
          >
            {workflow.loading === "analyze" ? "Analyzing..." : workflow.analysis ? "Run again" : "Analyze source"}
          </button>
        </div>
        <AnalysisPanel analysis={workflow.analysis} />
      </section>

      {workflow.analysis && (
        <section className="analysis-screen__plan panel">
          <div className="panel-header">
            <h2>Migration plan</h2>
            {!workflow.plan && (
              <button
                className="secondary-button"
                disabled={workflow.loading === "plan"}
                onClick={createPlan}
                type="button"
              >
                {workflow.loading === "plan" ? "Planning..." : "Create plan"}
              </button>
            )}
          </div>
          {workflow.plan ? (
            <div className="analysis-screen__plan-body">
              <div className="analysis-screen__plan-heading">
                <div>
                  <span className="panel-label">Target summary</span>
                  <strong>{workflow.plan.plan.target_summary}</strong>
                </div>
                <span className="tag">{workflow.plan.plan.support_level}</span>
              </div>
              <div className="analysis-screen__file-plan">
                {workflow.plan.plan.files.map((file) => (
                  <article key={file.target_path}>
                    <span>{String(file.order).padStart(2, "0")}</span>
                    <div>
                      <strong>{file.target_path}</strong>
                      <p>{file.purpose}</p>
                    </div>
                  </article>
                ))}
              </div>
              <button
                className="primary-button"
                disabled={workflow.plan.status === "approved" || Boolean(workflow.loading)}
                onClick={approvePlan}
                type="button"
              >
                {workflow.plan.status === "approved" ? "Plan approved" : "Approve plan and continue"}
              </button>
            </div>
          ) : (
            <div className="empty-state">Create a plan after analysis.</div>
          )}
        </section>
      )}
    </div>
  );
}

export default AnalysisScreen;
