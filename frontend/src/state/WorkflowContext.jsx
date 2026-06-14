import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { api } from "../services/api";

const WorkflowContext = createContext(null);

const defaultTarget = {
  language: "Python",
  language_version: "3.12",
  framework: "FastAPI",
  framework_version: "",
  architecture_style: "layered",
  package_manager: "pip",
  build_tool: "",
  custom_instructions: "",
};

export function WorkflowProvider({ children }) {
  const [health, setHealth] = useState(null);
  const [repositoryUrl, setRepositoryUrl] = useState(
    "https://github.com/ashish-patwal/Legacy-Morph",
  );
  const [branch, setBranch] = useState("main");
  const [inspection, setInspection] = useState(null);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [target, setTarget] = useState(defaultTarget);
  const [session, setSession] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [plan, setPlan] = useState(null);
  const [generatedFiles, setGeneratedFiles] = useState([]);
  const [testCases, setTestCases] = useState([]);
  const [validation, setValidation] = useState(null);
  const [loading, setLoading] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth({ status: "offline" }));
  }, []);

  const run = async (label, operation) => {
    setLoading(label);
    setError("");
    try {
      return await operation();
    } catch (caught) {
      setError(caught.message || "The request could not be completed.");
      throw caught;
    } finally {
      setLoading("");
    }
  };

  const value = useMemo(
    () => ({
      health,
      repositoryUrl,
      setRepositoryUrl,
      branch,
      setBranch,
      inspection,
      setInspection,
      selectedFiles,
      setSelectedFiles,
      target,
      setTarget,
      session,
      setSession,
      analysis,
      setAnalysis,
      plan,
      setPlan,
      generatedFiles,
      setGeneratedFiles,
      testCases,
      setTestCases,
      validation,
      setValidation,
      loading,
      error,
      setError,
      run,
    }),
    [
      health,
      repositoryUrl,
      branch,
      inspection,
      selectedFiles,
      target,
      session,
      analysis,
      plan,
      generatedFiles,
      testCases,
      validation,
      loading,
      error,
    ],
  );

  return <WorkflowContext.Provider value={value}>{children}</WorkflowContext.Provider>;
}

export function useWorkflow() {
  const context = useContext(WorkflowContext);
  if (!context) {
    throw new Error("useWorkflow must be used inside WorkflowProvider");
  }
  return context;
}
