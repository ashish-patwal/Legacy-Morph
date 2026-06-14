import { useState } from "react";

import "./MigrationPanel.css";

function MigrationPanel({ files, onReview, loading }) {
  const [comments, setComments] = useState("");
  const generatedFiles = files.filter((file) => file.status === "generated");
  const canReview = generatedFiles.length > 0;

  if (!files.length) {
    return <div className="empty-state">Generate the planned code batch to review it here.</div>;
  }

  return (
    <div className="migration-panel">
      <div className="migration-panel__batch-summary">
        <span className="panel-label">Generated batch</span>
        <strong>{files.length} files ready for review</strong>
      </div>
      <div className="migration-panel__files">
        {files.map((file) => (
          <article className="migration-panel__file" key={file.id}>
            <div className="migration-panel__meta">
              <div>
                <span className="panel-label">Target path</span>
                <strong>{file.target_path}</strong>
              </div>
              <span className={`migration-panel__status migration-panel__status--${file.status}`}>
                {file.status.replaceAll("_", " ")}
              </span>
            </div>
            <pre className="code-block">{file.content}</pre>
          </article>
        ))}
      </div>
      <div className="migration-panel__review">
        <div className="field">
          <label htmlFor="review-comments">Review comments</label>
          <textarea
            id="review-comments"
            onChange={(event) => setComments(event.target.value)}
            placeholder="Required when requesting changes"
            rows="3"
            value={comments}
          />
        </div>
        <div className="button-row">
          <button
            className="primary-button"
            disabled={loading || !canReview}
            onClick={() => onReview("approved", comments)}
            type="button"
          >
            Approve full batch
          </button>
          <button
            className="secondary-button"
            disabled={loading || !canReview || !comments.trim()}
            onClick={() => onReview("needs_changes", comments)}
            type="button"
          >
            Request batch changes
          </button>
          <button
            className="danger-button"
            disabled={loading || !canReview}
            onClick={() => onReview("rejected", comments)}
            type="button"
          >
            Reject batch
          </button>
        </div>
      </div>
    </div>
  );
}

export default MigrationPanel;
