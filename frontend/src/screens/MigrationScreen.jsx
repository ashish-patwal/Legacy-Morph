import { useNavigate } from "react-router-dom";

import MigrationPanel from "../components/MigrationPanel";
import { api } from "../services/api";
import { useWorkflow } from "../state/WorkflowContext";
import "./MigrationScreen.css";

function MigrationScreen() {
  const navigate = useNavigate();
  const workflow = useWorkflow();
  const generatedBatch = workflow.generatedFiles;
  const hasPendingReview = generatedBatch.some((file) => file.status === "generated");

  const generate = async () => {
    try {
      const result = await workflow.run("migrate", () => api.migrate(workflow.session.id));
      workflow.setGeneratedFiles([...workflow.generatedFiles, ...result]);
    } catch {
      // The shared workflow already exposes the request error.
    }
  };

  const review = async (decision, comments) => {
    const reviewableFiles = generatedBatch.filter((file) => file.status === "generated");
    if (!reviewableFiles.length) return;
    try {
      const results = await workflow.run("review", () =>
        Promise.all(
          reviewableFiles.map((file) =>
            api.reviewFile(file.id, {
              decision,
              comments: comments.trim() || null,
            }),
          ),
        ),
      );
      const updatedById = new Map(results.map((file) => [file.id, file]));
      workflow.setGeneratedFiles(
        workflow.generatedFiles.map((file) => updatedById.get(file.id) || file),
      );
      if (decision === "approved") {
        navigate("/package");
      }
    } catch {
      // The shared workflow already exposes the request error.
    }
  };

  if (!workflow.session || workflow.plan?.status !== "approved") {
    return (
      <div className="screen">
        <div className="warning-banner">Approve a migration plan before generating code.</div>
      </div>
    );
  }

  return (
    <div className="screen migration-screen">
      <span className="screen-kicker">Controlled generation</span>
      <h1 className="screen-title">
        Whole code.
        <br />
        One <em>review.</em>
      </h1>
      <p className="screen-intro">
        Generate the complete planned code batch from approved source evidence,
        then review and approve the full migration before packaging.
      </p>

      {workflow.error && <div className="error-banner migration-screen__message">{workflow.error}</div>}

      <section className="migration-screen__status">
        <div>
          <span className="panel-label">Progress</span>
          <strong>
            {workflow.generatedFiles.filter((file) => file.status === "approved").length}
            /{workflow.plan.plan.files.length} approved
          </strong>
        </div>
        <button
          className="primary-button"
          disabled={Boolean(workflow.loading) || hasPendingReview || workflow.generatedFiles.length > 0}
          onClick={generate}
          type="button"
        >
          {workflow.loading === "migrate" ? "Generating code..." : "Generate whole code"}
        </button>
      </section>

      <section className="panel migration-screen__panel">
        <div className="panel-header">
          <h2>Generated file review</h2>
          <span className="panel-label">Human checkpoint</span>
        </div>
        <MigrationPanel
          files={generatedBatch}
          loading={workflow.loading === "review"}
          onReview={review}
        />
      </section>
    </div>
  );
}

export default MigrationScreen;
