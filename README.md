# Legacy-Morph

Legacy-Morph is an AI-assisted platform for analyzing and modernizing legacy
applications. It reads a GitHub repository through an MCP integration, builds
structural and dependency artifacts, and generates modern code in a language
and framework selected by the user.

The project is currently under active MVP development. See [PLAN.md](PLAN.md)
for the approved architecture and build order.

## Goals

- Support legacy applications across different languages and frameworks.
- Detect source languages, frameworks, toolkits, runtimes, and versions.
- Generate normalized AST and dependency schema artifacts.
- Identify repeated structures to reduce duplicate migration work.
- Let users select or describe the desired modern target stack.
- Generate and review one modern file at a time.
- Combine deterministic checks with an independent LLM review.
- Require human approval before a generated file is accepted.

Dojo applications are treated as JavaScript applications with Dojo recorded as
the legacy toolkit. The architecture is not limited to Java or COBOL.

## Planned Stack

### Frontend

- React
- JavaScript and JSX
- Vite
- React Router
- Plain CSS with one stylesheet per screen and component

### Backend

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- SQLite
- OpenAI API

### Repository Access

Legacy repositories are accessed through a GitHub-capable MCP server. The
application should not require direct repository cloning during normal use.

## Migration Flow

```text
GitHub repository URL
        |
        v
Repository inspection through GitHub MCP
        |
        v
Language and legacy-framework detection
        |
        v
Normalized AST and dependency schemas
        |
        v
Similarity clustering and migration planning
        |
        v
User-selected modern target
        |
        v
One-file-at-a-time LLM generation
        |
        v
Deterministic validation and independent LLM review
        |
        v
Human approval
```

## Configuration

Copy `.env.example` to `.env` and replace placeholder values locally:

```bash
cp .env.example .env
```

Set an OpenAI API key to enable real AI analysis and migration:

```text
OPENAI_API_KEY=your_real_key
```

Never commit `.env` or paste API keys into source files. The application will
support deterministic mock responses when an API key is unavailable.

GitHub repository inspection also requires access to a configured GitHub MCP
server. Its URL, server name, and authentication token are read from environment
variables.

## Planned Local Development

The commands below will become available as the backend and frontend are added.

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The planned local URLs are:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- API documentation: `http://localhost:8000/docs`

## MVP Persistence

SQLite uses three tables:

- `migration_sessions`
- `generated_files`
- `validation_results`

AST and dependency schemas are stored as JSON artifacts referenced by the
migration session.

## Security Boundaries

- Repository content is untrusted input.
- MCP and OpenAI credentials remain backend-only.
- Generated code must not run through unrestricted `exec`.
- Behavioral validation must use trusted functions or a restricted sandbox.
- LLM review supplements static analysis and tests; it does not replace them.

## Development Process

This project is developed one file at a time:

1. Explain the next file and its purpose.
2. Create or update only that file.
3. Run relevant checks.
4. Stop for review and approval.
5. Continue only after approval.

This keeps architectural and implementation decisions visible throughout the
MVP build.
