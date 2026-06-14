import "./RepositoryTree.css";

function RepositoryTree({ files, selectedFiles, onChange }) {
  const supportedFiles = files.filter((file) => file.supported);
  const allSelected =
    supportedFiles.length > 0 && supportedFiles.every((file) => selectedFiles.includes(file.path));

  const toggleAll = () => {
    onChange(allSelected ? [] : supportedFiles.map((file) => file.path));
  };

  const toggleFile = (path) => {
    onChange(
      selectedFiles.includes(path)
        ? selectedFiles.filter((item) => item !== path)
        : [...selectedFiles, path],
    );
  };

  return (
    <section className="repository-tree panel">
      <div className="panel-header">
        <h2>Source inventory</h2>
        <button className="repository-tree__select" onClick={toggleAll} type="button">
          {allSelected ? "Clear all" : "Select supported"}
        </button>
      </div>
      <div className="repository-tree__stats">
        <span>{files.length} discovered</span>
        <span>{supportedFiles.length} supported</span>
        <strong>{selectedFiles.length} selected</strong>
      </div>
      <div className="repository-tree__list">
        {files.map((file) => (
          <label
            className={`repository-file ${!file.supported ? "repository-file--disabled" : ""}`}
            key={file.path}
          >
            <input
              checked={selectedFiles.includes(file.path)}
              disabled={!file.supported}
              onChange={() => toggleFile(file.path)}
              type="checkbox"
            />
            <span className="repository-file__path">{file.path}</span>
            <span className="repository-file__language">{file.language || "other"}</span>
            <span className="repository-file__size">
              {(file.size_bytes / 1024).toFixed(1)} KB
            </span>
          </label>
        ))}
      </div>
    </section>
  );
}

export default RepositoryTree;
