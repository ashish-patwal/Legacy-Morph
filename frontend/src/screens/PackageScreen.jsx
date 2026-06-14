import { api } from "../services/api";
import { useWorkflow } from "../state/WorkflowContext";
import "./PackageScreen.css";

function PackageScreen() {
  const workflow = useWorkflow();
  const packageFiles = workflow.generatedFiles.filter((file) =>
    ["generated", "approved"].includes(file.status),
  );
  const approvedFiles = workflow.generatedFiles.filter((file) => file.status === "approved");

  if (!workflow.session || !packageFiles.length) {
    return (
      <div className="screen">
        <div className="warning-banner">Generate code before downloading a package.</div>
      </div>
    );
  }

  return (
    <div className="screen package-screen">
      <span className="screen-kicker">Ready to ship</span>
      <h1 className="screen-title">
        Download the
        <br />
        <em>package.</em>
      </h1>
      <p className="screen-intro">
        Legacy-Morph has generated the modern code batch. Download the ZIP package,
        inspect it locally, and run it in the target stack when you are ready.
      </p>

      {workflow.error && <div className="error-banner package-screen__message">{workflow.error}</div>}

      <section className="panel package-panel">
        <div className="panel-header">
          <h2>Generated package</h2>
          <span className="panel-label">{packageFiles.length} files</span>
        </div>
        <div className="package-panel__body">
          <div>
            <span className="panel-label">Review status</span>
            <strong>
              {approvedFiles.length}/{packageFiles.length} approved
            </strong>
          </div>
          <a
            className="primary-button package-panel__download"
            href={api.packageUrl(workflow.session.id)}
          >
            Download ZIP package
          </a>
        </div>
        <div className="package-panel__files">
          {packageFiles.map((file) => (
            <div className="package-panel__file" key={file.id}>
              <span>{file.target_path}</span>
              <strong>{file.status.replaceAll("_", " ")}</strong>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

export default PackageScreen;
