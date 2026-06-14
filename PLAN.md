# Legacy-Morph Development Plan

The approved development plan is maintained in:

`/Users/ks/Desktop/Corporate/LEGACY_MORPH_PLAN.md`

This repository will be implemented one file at a time. Each file must be
reviewed and approved before development continues to the next file.

## Product Summary

Legacy-Morph is an AI-powered legacy application migration assistant. It:

1. Reads a GitHub repository through an MCP integration.
2. Detects source languages, frameworks, toolkits, and runtimes.
3. Generates normalized AST and dependency schema artifacts.
4. Finds repeated structural patterns across the legacy application.
5. Builds a migration plan for a user-selected modern language and framework.
6. Uses an LLM to generate one modern file at a time.
7. Runs deterministic validation and an independent LLM review.
8. Requires human approval for every generated file.

## MVP Stack

### Frontend

- React
- JavaScript and JSX
- Vite
- React Router
- One CSS file per screen and component

### Backend

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- SQLite
- OpenAI API

### Persistence

The MVP uses three SQLite tables:

- `migration_sessions`
- `generated_files`
- `validation_results`

AST and dependency schemas are stored as JSON artifacts referenced by the
migration session.

## Development Rules

- Implement one file at a time.
- Explain the file before creating or modifying it.
- Run relevant checks after each file.
- Stop for user review after each file.
- Never commit API keys.
- Load `OPENAI_API_KEY` from the environment.
- Use mock AI responses when no key is configured.
- Treat repository content and generated code as untrusted input.
- Do not execute arbitrary generated code without a restricted sandbox.

## Source Support

The architecture is language-extensible and must not assume Java or COBOL.
Examples include older JavaScript, Dojo applications, Java, COBOL, C, C++, C#,
PHP, Visual Basic, Perl, and mixed-language repositories.

Dojo is treated as a JavaScript toolkit/framework. Source language, framework,
runtime, and version are detected and recorded separately.

## Migration Pipeline

```text
GitHub Repository
        |
        v
GitHub MCP Repository Agent
        |
        v
Language and Framework Detection
        |
        v
Normalized AST Generation
        |
        v
Dependency and Domain Schemas
        |
        v
Similarity and Pattern Clustering
        |
        v
Human-Approved Migration Plan
        |
        v
One-File-at-a-Time LLM Generation
        |
        v
Deterministic Validation
        |
        v
Independent LLM Review
        |
        v
Human File Approval
```

## Target Selection

The user can choose a suggested target or enter a custom target:

- Language and version
- Framework and version
- Architecture style
- Package manager
- Build tool
- Custom migration instructions

Unsupported custom targets are marked experimental and cannot claim complete
validation coverage.

## Repository Structure

```text
Legacy-Morph/
├── PLAN.md
├── README.md
├── .gitignore
├── .env.example
├── backend/
│   ├── artifacts/
│   ├── agents/
│   │   ├── ast_agent.py
│   │   ├── dependency_agent.py
│   │   ├── migration_agent.py
│   │   └── validation_agent.py
│   ├── main.py
│   ├── ai_service.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── github_mcp_service.py
│   ├── prompts.py
│   ├── validator.py
│   └── requirements.txt
└── frontend/
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── App.css
        ├── styles/
        │   └── global.css
        ├── screens/
        └── components/
```

## Build Order

1. Repository documentation and environment templates.
2. Backend Pydantic schemas.
3. Simple SQLite models and database setup.
4. GitHub MCP repository service.
5. AST and dependency schema agents.
6. OpenAI service and prompts.
7. Migration and validation agents.
8. FastAPI routes.
9. React JSX frontend with paired CSS files.
10. End-to-end validation and demo polish.
