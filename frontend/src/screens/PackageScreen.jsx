import { useEffect, useRef, useState } from "react";

import { api } from "../services/api";
import { useWorkflow } from "../state/WorkflowContext";
import "./PackageScreen.css";

function PackageScreen() {
  const workflow = useWorkflow();
  const hasWorkflowPackage = workflow.session && workflow.generatedFiles.length > 0;
  const attemptedRecovery = useRef(false);
  const [recoveryLoading, setRecoveryLoading] = useState(false);
  const [downloadMessage, setDownloadMessage] = useState("");

  useEffect(() => {
    if (hasWorkflowPackage || attemptedRecovery.current) return;

    attemptedRecovery.current = true;
    setRecoveryLoading(true);
    workflow.setError("");
    api
      .latestPackage()
      .then((result) => {
        workflow.setSession(result.session);
        workflow.setGeneratedFiles(result.files);
      })
      .catch((caught) => {
        workflow.setError(caught.message || "The latest package could not be loaded.");
      })
      .finally(() => {
        setRecoveryLoading(false);
      });
  }, [hasWorkflowPackage, workflow]);

  const packageFiles = workflow.generatedFiles.filter((file) =>
    ["generated", "approved"].includes(file.status),
  );
  const approvedFiles = workflow.generatedFiles.filter((file) => file.status === "approved");
  const packageUrl = workflow.session ? api.packageUrl(workflow.session.id) : "";

  const downloadPackage = async () => {
    try {
      setDownloadMessage("");
      const { blob, filename } = await workflow.run("package", () =>
        api.downloadPackage(workflow.session.id),
      );
      const downloadUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(downloadUrl);
      setDownloadMessage(
        "ZIP package is ready. If your browser did not start the download, use the direct ZIP link below.",
      );
    } catch {
      // The shared workflow already exposes the request error.
    }
  };

  if (recoveryLoading) {
    return (
      <div className="screen">
        <div className="warning-banner">Loading the latest generated package...</div>
      </div>
    );
  }

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
          <button
            className="primary-button package-panel__download"
            disabled={workflow.loading === "package"}
            onClick={downloadPackage}
            type="button"
          >
            {workflow.loading === "package" ? "Preparing ZIP..." : "Download ZIP package"}
          </button>
        </div>
        {downloadMessage && <p className="package-panel__message">{downloadMessage}</p>}
        <div className="package-panel__direct-link">
          <span className="panel-label">Direct ZIP link</span>
          <a download href={packageUrl}>
            {packageUrl}
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
