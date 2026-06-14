# Legacy-Morph Backend

The backend is a FastAPI service that coordinates repository inspection,
deterministic AST and dependency extraction, AI-assisted migration, file review,
and validation.

## Stack

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- SQLite
- OpenAI Responses API
- GitHub MCP

## Setup

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

Copy the environment template:

```bash
cp .env.example .env
```

Set `OPENAI_API_KEY` in `.env` to enable real AI analysis and code generation.
When the key is absent or still contains the placeholder value, the backend
runs in deterministic mock mode.

Never commit `.env`.

## Run

Run the service from the `backend` directory:

```bash
cd backend
../.venv/bin/uvicorn main:app --reload --port 8000
```

Available local URLs:

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- OpenAPI document: `http://localhost:8000/openapi.json`

## Environment Variables

### AI

```text
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4.1-mini
```

### Backend

```text
DATABASE_URL=sqlite:///./legacy_morph.db
ARTIFACT_ROOT=./artifacts
CORS_ORIGINS=http://localhost:5173
```

### GitHub MCP

```text
GITHUB_MCP_SERVER_URL=http://localhost:9000
GITHUB_MCP_SERVER_NAME=github
GITHUB_MCP_AUTH_TOKEN=your_mcp_auth_token_here
GITHUB_MAX_FILES=100
GITHUB_MAX_FILE_SIZE_BYTES=200000
```

The configured MCP server must provide read-only repository metadata and file
content tools. Tool names can be overridden with:

```text
GITHUB_MCP_REPOSITORY_TOOL=get_repository
GITHUB_MCP_CONTENTS_TOOL=get_file_contents
```

## API Workflow

The workflow is stateful and should be followed in this order.

### 1. Health

```http
GET /health
```

The response reports whether the AI service is running in `mock` or `openai`
mode.

### 2. Inspect Repository

```http
POST /repositories/inspect
```

```json
{
  "repository_url": "https://github.com/example/legacy-app",
  "branch": "main"
}
```

The MCP service returns the repository tree, supported files, detected source
technologies, and warnings.

### 3. Create Migration Session

```http
POST /migration-sessions
```

```json
{
  "repository_url": "https://github.com/example/legacy-app",
  "branch": "main",
  "commit_sha": null,
  "selected_files": [
    "src/legacy/app.js"
  ],
  "target": {
    "language": "Python",
    "language_version": "3.12",
    "framework": "FastAPI",
    "architecture_style": "layered",
    "package_manager": "pip",
    "custom_instructions": ""
  }
}
```

Retrieve the session later with:

```http
GET /migration-sessions/{session_id}
```

### 4. Analyze

```http
POST /analyze
```

```json
{
  "migration_session_id": "session UUID"
}
```

Analysis creates:

- A normalized AST artifact
- A dependency schema artifact
- An AI or mock repository analysis

### 5. Create and Approve Plan

```http
POST /migration-sessions/{session_id}/plan
POST /migration-sessions/{session_id}/plan/approve
```

Code generation is blocked until the migration plan is approved.

### 6. Generate One File

```http
POST /migrate
```

```json
{
  "migration_session_id": "session UUID"
}
```

Each call generates only the next eligible file in dependency order.

### 7. Review Generated File

```http
POST /generated-files/{file_id}/review
```

Approve:

```json
{
  "decision": "approved",
  "comments": null
}
```

Request changes:

```json
{
  "decision": "needs_changes",
  "comments": "Preserve the original date validation rule."
}
```

Comments are required when requesting changes.

### 8. Generate Tests

```http
POST /generate-tests
```

```json
{
  "migration_session_id": "session UUID",
  "generated_file_ids": [
    "generated file UUID"
  ]
}
```

### 9. Validate

```http
POST /validate
```

```json
{
  "migration_session_id": "session UUID",
  "generated_file_ids": [
    "generated file UUID"
  ],
  "test_cases": [
    {
      "name": "example",
      "input": {
        "principal": 10000,
        "rate": 5,
        "years": 2
      },
      "expected_output": {
        "interest": 1000,
        "total_amount": 11000
      }
    }
  ]
}
```

Validation combines deterministic file checks, an independent LLM review, and
trusted behavioral comparison.

## Artifacts

Generated artifacts are stored under:

```text
backend/artifacts/{migration_session_id}/
├── analysis/
├── ast/
├── generated/
├── plan/
├── schema/
└── validation/
```

Artifacts are ignored by Git.

## SQLite

The MVP creates three tables automatically at startup:

- `migration_sessions`
- `generated_files`
- `validation_results`

The database is intentionally simple for the MVP.

## Supported Deterministic Parsing

Current parser adapters cover:

- Java
- JavaScript
- TypeScript

Other source languages are recorded as unsupported until a deterministic parser
adapter is added. The LLM is not allowed to invent an AST for unsupported code.

The JavaScript adapter detects framework hints such as Dojo, AMD, AngularJS, and
Backbone.js. The Java adapter detects Spring, Java EE, Servlet, and Struts hints.

## Validation Safety

The backend does not execute generated code.

Current deterministic validation includes:

- Target path safety
- File size
- Placeholder and conflict-marker scans
- Target language and extension matching
- Python syntax parsing
- Delimiter checks for selected non-Python languages
- Migration-plan traceability

Behavioral validation uses trusted internal executors. The current demo executor
supports the loan calculator example. Production support requires a restricted
sandbox and language-specific test runners.

## Tests

Run backend tests once test files are added:

```bash
PYTHONPATH=backend .venv/bin/pytest
```
