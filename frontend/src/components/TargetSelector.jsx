import "./TargetSelector.css";

const frameworks = {
  Python: ["FastAPI", "Django", "Flask"],
  Java: ["Spring Boot", "Quarkus"],
  JavaScript: ["Express", "React", "Node.js"],
  TypeScript: ["NestJS", "Express", "React"],
  "C#": ["ASP.NET Core"],
  Go: ["Gin", "Fiber"],
  Kotlin: ["Ktor", "Spring Boot"],
};

function TargetSelector({ target, onChange }) {
  const update = (field, value) => {
    const next = { ...target, [field]: value };
    if (field === "language") {
      next.framework = frameworks[value]?.[0] || "";
    }
    onChange(next);
  };

  return (
    <section className="target-selector panel">
      <div className="panel-header">
        <h2>Modern target</h2>
        <span className="panel-label">User controlled</span>
      </div>
      <div className="target-selector__grid">
        <div className="field">
          <label htmlFor="target-language">Language</label>
          <input
            id="target-language"
            list="target-languages"
            onChange={(event) => update("language", event.target.value)}
            value={target.language}
          />
          <datalist id="target-languages">
            {Object.keys(frameworks).map((language) => (
              <option key={language} value={language} />
            ))}
          </datalist>
        </div>
        <div className="field">
          <label htmlFor="target-version">Version</label>
          <input
            id="target-version"
            onChange={(event) => update("language_version", event.target.value)}
            placeholder="Latest stable"
            value={target.language_version}
          />
        </div>
        <div className="field">
          <label htmlFor="target-framework">Framework</label>
          <input
            id="target-framework"
            list="target-frameworks"
            onChange={(event) => update("framework", event.target.value)}
            value={target.framework}
          />
          <datalist id="target-frameworks">
            {(frameworks[target.language] || []).map((framework) => (
              <option key={framework} value={framework} />
            ))}
          </datalist>
        </div>
        <div className="field">
          <label htmlFor="architecture-style">Architecture</label>
          <select
            id="architecture-style"
            onChange={(event) => update("architecture_style", event.target.value)}
            value={target.architecture_style}
          >
            <option value="layered">Layered</option>
            <option value="clean">Clean architecture</option>
            <option value="hexagonal">Hexagonal</option>
            <option value="modular-monolith">Modular monolith</option>
          </select>
        </div>
        <div className="field">
          <label htmlFor="package-manager">Package manager</label>
          <input
            id="package-manager"
            onChange={(event) => update("package_manager", event.target.value)}
            placeholder="pip, npm, Maven..."
            value={target.package_manager}
          />
        </div>
        <div className="field">
          <label htmlFor="build-tool">Build tool</label>
          <input
            id="build-tool"
            onChange={(event) => update("build_tool", event.target.value)}
            placeholder="Optional"
            value={target.build_tool}
          />
        </div>
        <div className="field target-selector__instructions">
          <label htmlFor="custom-instructions">Migration instructions</label>
          <textarea
            id="custom-instructions"
            onChange={(event) => update("custom_instructions", event.target.value)}
            placeholder="Preserve public APIs, prefer async I/O, avoid vendor lock-in..."
            rows="3"
            value={target.custom_instructions}
          />
        </div>
      </div>
    </section>
  );
}

export default TargetSelector;
