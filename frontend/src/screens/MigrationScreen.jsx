import { useNavigate } from "react-router-dom";

import MigrationPanel from "../components/MigrationPanel";
import { api } from "../services/api";
import { useWorkflow } from "../state/WorkflowContext";
import "./MigrationScreen.css";

function MigrationScreen() {
  const navigate = useNavigate();
  const workflow = useWorkflow();
  const currentFile = workflow.generatedFiles.at(-1);

  const generate = async () => {
    try {
      const result = await workflow.run("migrate", () => api.migrate(workflow.session.id));
      workflow.setGeneratedFiles([...workflow.generatedFiles, result]);
    } catch {
      // The shared workflow already exposes the request error.
    }
  };

  const review = async (decision, comments) => {
    if (!currentFile) return;
    try {
      const result = await workflow.run("review", () =>
        api.reviewFile(currentFile.id, {
          decision,
          comments: comments.trim() || null,
        }),
      );
      workflow.setGeneratedFiles(
        workflow.generatedFiles.map((file) => (file.id === result.id ? result : file)),
      );
      if (decision === "approved") {
        navigate("/validation");
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
        One file.
        <br />
        One <em>decision.</em>
      </h1>
      <p className="screen-intro">
        Each file is generated from approved source evidence, checked independently,
        and held for your review before the migration moves forward.
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
          disabled={Boolean(workflow.loading) || (currentFile && currentFile.status === "generated")}
          onClick={generate}
          type="button"
        >
          {workflow.loading === "migrate" ? "Generating..." : currentFile ? "Generate next file" : "Generate first file"}
        </button>
      </section>

      <section className="panel migration-screen__panel">
        <div className="panel-header">
          <h2>Generated file review</h2>
          <span className="panel-label">Human checkpoint</span>
        </div>
        <MigrationPanel
          file={currentFile}
          loading={workflow.loading === "review"}
          onReview={review}
        />
      </section>
    </div>
  );
}

export default MigrationScreen;
