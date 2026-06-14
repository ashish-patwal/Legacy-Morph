import TestPanel from "../components/TestPanel";
import ValidationPanel from "../components/ValidationPanel";
import { api } from "../services/api";
import { useWorkflow } from "../state/WorkflowContext";
import "./ValidationScreen.css";

function ValidationScreen() {
  const workflow = useWorkflow();
  const approvedFiles = workflow.generatedFiles.filter((file) => file.status === "approved");

  const generateTests = async () => {
    try {
      const result = await workflow.run("tests", () =>
        api.generateTests(
          workflow.session.id,
          approvedFiles.map((file) => file.id),
        ),
      );
      workflow.setTestCases(result.test_cases);
    } catch {
      // The shared workflow already exposes the request error.
    }
  };

  const validate = async () => {
    try {
      const result = await workflow.run("validate", () =>
        api.validate(
          workflow.session.id,
          approvedFiles.map((file) => file.id),
          workflow.testCases,
        ),
      );
      workflow.setValidation(result);
    } catch {
      // The shared workflow already exposes the request error.
    }
  };

  if (!workflow.session || !approvedFiles.length) {
    return (
      <div className="screen">
        <div className="warning-banner">Approve at least one generated file before validation.</div>
      </div>
    );
  }

  return (
    <div className="screen validation-screen">
      <span className="screen-kicker">Evidence over confidence</span>
      <h1 className="screen-title">
        Verify the
        <br />
        <em>behavior.</em>
      </h1>
      <p className="screen-intro">
        Static checks, trusted behavioral tests, and an independent AI review combine
        into one migration verdict. No generated code is executed unrestricted.
      </p>

      {workflow.error && <div className="error-banner validation-screen__message">{workflow.error}</div>}

      <div className="validation-screen__actions">
        <button
          className="secondary-button"
          disabled={Boolean(workflow.loading)}
          onClick={generateTests}
          type="button"
        >
          {workflow.loading === "tests" ? "Generating tests..." : "Generate tests"}
        </button>
        <button
          className="primary-button"
          disabled={!workflow.testCases.length || Boolean(workflow.loading)}
          onClick={validate}
          type="button"
        >
          {workflow.loading === "validate" ? "Validating..." : "Validate migration"}
        </button>
      </div>

      <div className="validation-screen__grid">
        <section className="panel">
          <div className="panel-header">
            <h2>Behavioral tests</h2>
            <span className="panel-label">{workflow.testCases.length} cases</span>
          </div>
          <TestPanel testCases={workflow.testCases} />
        </section>
        <section className="panel">
          <div className="panel-header">
            <h2>Validation report</h2>
            <span className="panel-label">Combined verdict</span>
          </div>
          <ValidationPanel validation={workflow.validation} />
        </section>
      </div>
    </div>
  );
}

export default ValidationScreen;
