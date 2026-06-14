import "./AnalysisPanel.css";

function AnalysisPanel({ analysis }) {
  if (!analysis) {
    return <div className="empty-state">Run analysis to reveal business logic and risks.</div>;
  }

  return (
    <div className="analysis-panel">
      <p className="analysis-panel__summary">{analysis.summary}</p>
      <div className="analysis-panel__columns">
        <section>
          <h3>Business rules</h3>
          <ol>
            {analysis.business_rules.length ? (
              analysis.business_rules.map((rule) => <li key={rule}>{rule}</li>)
            ) : (
              <li>No business rules extracted in the current mode.</li>
            )}
          </ol>
        </section>
        <section>
          <h3>Migration risks</h3>
          <ol>
            {analysis.risks.length ? (
              analysis.risks.map((risk) => <li key={risk}>{risk}</li>)
            ) : (
              <li>No explicit risks reported.</li>
            )}
          </ol>
        </section>
      </div>
      <section className="analysis-panel__functions">
        <h3>Discovered functions</h3>
        <div className="tag-list">
          {analysis.functions.length ? (
            analysis.functions.map((item) => (
              <span className="tag" key={`${item.source_path}-${item.name}`}>
                {item.name}
              </span>
            ))
          ) : (
            <span className="tag">Awaiting semantic analysis</span>
          )}
        </div>
      </section>
    </div>
  );
}

export default AnalysisPanel;
