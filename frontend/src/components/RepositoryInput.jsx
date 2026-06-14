import "./RepositoryInput.css";

function RepositoryInput({
  repositoryUrl,
  branch,
  onRepositoryUrlChange,
  onBranchChange,
  onInspect,
  loading,
}) {
  return (
    <section className="repository-input panel">
      <div className="panel-header">
        <h2>Repository coordinates</h2>
        <span className="panel-label">Temporary shallow clone</span>
      </div>
      <div className="repository-input__body">
        <div className="field repository-input__url">
          <label htmlFor="repository-url">Repository URL</label>
          <input
            id="repository-url"
            onChange={(event) => onRepositoryUrlChange(event.target.value)}
            placeholder="https://github.com/owner/repository"
            type="url"
            value={repositoryUrl}
          />
        </div>
        <div className="field">
          <label htmlFor="branch">Branch</label>
          <input
            id="branch"
            onChange={(event) => onBranchChange(event.target.value)}
            placeholder="main"
            value={branch}
          />
        </div>
        <button
          className="primary-button repository-input__button"
          disabled={!repositoryUrl || loading}
          onClick={onInspect}
          type="button"
        >
          {loading ? "Inspecting..." : "Inspect repository"}
        </button>
      </div>
      <p className="repository-input__note">
        Read-only public repository access. Cloned code is treated as untrusted input
        and never executed.
      </p>
    </section>
  );
}

export default RepositoryInput;
