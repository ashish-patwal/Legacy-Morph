import "./ValidationPanel.css";

function ValidationPanel({ validation }) {
  if (!validation) {
    return <div className="empty-state">Run validation to see the migration verdict.</div>;
  }

  return (
    <div className="validation-panel">
      <div className={`validation-score validation-score--${validation.status.toLowerCase()}`}>
        <span>Migration verdict</span>
        <strong>{validation.status}</strong>
      </div>
      <div className="validation-metrics">
        <div>
          <span>Deterministic</span>
          <strong>{validation.deterministic_status}</strong>
        </div>
        <div>
          <span>LLM review</span>
          <strong>{validation.llm_review_status}</strong>
        </div>
        <div>
          <span>Tests</span>
          <strong>
            {validation.passed}/{validation.total_tests}
          </strong>
        </div>
      </div>
      <div className="validation-findings">
        <h3>Findings</h3>
        {validation.findings.length ? (
          validation.findings.map((finding, index) => (
            <div
              className={`validation-finding validation-finding--${finding.severity}`}
              key={`${finding.message}-${index}`}
            >
              <span>{finding.severity}</span>
              <p>{finding.message}</p>
            </div>
          ))
        ) : (
          <p className="validation-findings__empty">No findings reported.</p>
        )}
      </div>
    </div>
  );
}

export default ValidationPanel;
