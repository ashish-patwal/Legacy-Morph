import { useNavigate } from "react-router-dom";

import RepositoryInput from "../components/RepositoryInput";
import RepositoryTree from "../components/RepositoryTree";
import TargetSelector from "../components/TargetSelector";
import { api } from "../services/api";
import { useWorkflow } from "../state/WorkflowContext";
import "./RepositoryScreen.css";

function RepositoryScreen() {
  const navigate = useNavigate();
  const workflow = useWorkflow();

  const inspect = async () => {
    try {
      const result = await workflow.run("inspect", () =>
        api.inspectRepository({
          repository_url: workflow.repositoryUrl,
          branch: workflow.branch || null,
        }),
      );
      workflow.setInspection(result);
      workflow.setSelectedFiles(
        result.files.filter((file) => file.supported).map((file) => file.path),
      );
    } catch {
      // The shared workflow already exposes the request error.
    }
  };

  const createSession = async () => {
    try {
      const result = await workflow.run("session", () =>
        api.createSession({
          repository_url: workflow.repositoryUrl,
          branch: workflow.inspection?.branch || workflow.branch || null,
          commit_sha: workflow.inspection?.commit_sha || null,
          selected_files: workflow.selectedFiles,
          target: workflow.target,
        }),
      );
      workflow.setSession(result);
      navigate("/analysis");
    } catch {
      // The shared workflow already exposes the request error.
    }
  };

  return (
    <div className="screen repository-screen">
      <span className="screen-kicker">Repository intelligence</span>
      <h1 className="screen-title">
        Understand the old.
        <br />
        Build the <em>next.</em>
      </h1>
      <p className="screen-intro">
        Point Legacy-Morph at a repository, choose the destination stack, and create
        a traceable migration from source structure to reviewed modern code.
      </p>

      <RepositoryInput
        branch={workflow.branch}
        loading={workflow.loading === "inspect"}
        onBranchChange={workflow.setBranch}
        onInspect={inspect}
        onRepositoryUrlChange={workflow.setRepositoryUrl}
        repositoryUrl={workflow.repositoryUrl}
      />

      {workflow.error && <div className="error-banner repository-screen__message">{workflow.error}</div>}

      {workflow.inspection && (
        <>
          <div className="repository-screen__technology">
            <span>Detected source</span>
            <div className="tag-list">
              {workflow.inspection.source_technologies.map((item, index) => (
                <span className="tag" key={`${item.language}-${item.framework}-${index}`}>
                  {item.language}
                  {item.framework ? ` / ${item.framework}` : ""}
                </span>
              ))}
            </div>
          </div>

          <div className="repository-screen__workspace">
            <RepositoryTree
              files={workflow.inspection.files}
              onChange={workflow.setSelectedFiles}
              selectedFiles={workflow.selectedFiles}
            />
            <TargetSelector onChange={workflow.setTarget} target={workflow.target} />
          </div>

          <div className="repository-screen__continue">
            <div>
              <span className="panel-label">Ready to analyze</span>
              <strong>{workflow.selectedFiles.length} source files selected</strong>
            </div>
            <button
              className="primary-button"
              disabled={!workflow.selectedFiles.length || workflow.loading === "session"}
              onClick={createSession}
              type="button"
            >
              {workflow.loading === "session" ? "Creating session..." : "Create migration session"}
            </button>
          </div>
        </>
      )}
    </div>
  );
}

export default RepositoryScreen;
