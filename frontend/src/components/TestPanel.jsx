import "./TestPanel.css";

function TestPanel({ testCases }) {
  if (!testCases.length) {
    return <div className="empty-state">No generated tests yet.</div>;
  }

  return (
    <div className="test-panel">
      {testCases.map((testCase, index) => (
        <article className="test-card" key={`${testCase.name}-${index}`}>
          <div className="test-card__number">{String(index + 1).padStart(2, "0")}</div>
          <div>
            <strong>{testCase.name}</strong>
            <div className="test-card__data">
              <span>Input</span>
              <code>{JSON.stringify(testCase.input)}</code>
              <span>Expected</span>
              <code>{JSON.stringify(testCase.expected_output)}</code>
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}

export default TestPanel;
