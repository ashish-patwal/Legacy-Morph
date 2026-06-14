import { useState } from "react";

import "./MigrationPanel.css";

function MigrationPanel({ file, onReview, loading }) {
  const [comments, setComments] = useState("");

  if (!file) {
    return <div className="empty-state">Generate the next planned file to review it here.</div>;
  }

  return (
    <div className="migration-panel">
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
            disabled={loading}
            onClick={() => onReview("approved", comments)}
            type="button"
          >
            Approve file
          </button>
          <button
            className="secondary-button"
            disabled={loading || !comments.trim()}
            onClick={() => onReview("needs_changes", comments)}
            type="button"
          >
            Request changes
          </button>
          <button
            className="danger-button"
            disabled={loading}
            onClick={() => onReview("rejected", comments)}
            type="button"
          >
            Reject
          </button>
        </div>
      </div>
    </div>
  );
}

export default MigrationPanel;
