# Legacy-Morph Instructions

Legacy-Morph is an AI-assisted migration tool. It inspects a public GitHub
repository, analyzes legacy source code, generates a modern code batch using
OpenAI, lets you review the generated files, and provides a downloadable ZIP
package.

## What You Need

- Python 3.12 or newer
- Node.js 20 or newer
- npm
- Git
- OpenAI API key

## One-Time Setup

Follow the setup guide:

```text
setup.md
```

Short version:

```bash
cd /Users/ks/Desktop/Corporate/Legacy-Morph
python -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cd frontend
npm install
```

Create `.env` from the template:

```bash
cd /Users/ks/Desktop/Corporate/Legacy-Morph
cp .env.example .env
```

Add your real OpenAI key in `.env`:

```text
OPENAI_API_KEY=your_real_openai_api_key
```

Do not put the real key in `.env.example`.

## Start The App

Open two terminals.

Terminal 1, backend:

```bash
cd /Users/ks/Desktop/Corporate/Legacy-Morph/backend
../.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
```

Terminal 2, frontend:

```bash
cd /Users/ks/Desktop/Corporate/Legacy-Morph/frontend
npm run dev -- --host 127.0.0.1
```

Open:

```text
http://127.0.0.1:5173
```

Check backend:

```text
http://127.0.0.1:8000/health
```

Expected OpenAI mode:

```json
{"status":"ok","service":"legacy-morph-backend","ai_mode":"openai"}
```

## How To Use The App

1. Open `http://127.0.0.1:5173`.
2. Paste a public GitHub repository URL.
3. Enter a branch, usually `main`.
4. Click **Inspect repository**.
5. Review supported files and detected technologies.
6. Choose the target stack, for example `Python` and `FastAPI`.
7. Create the migration session.
8. Run analysis.
9. Generate the migration plan.
10. Approve the plan.
11. Click **Generate whole code**.
12. Review the generated batch.
13. Click **Approve full batch**.
14. Go to **Package**.
15. Click **Download ZIP package**.

If the in-app browser does not save the file, use the **Direct ZIP link** shown
on the Package screen.

## Example Test Repository

```text
https://github.com/jitesh0400/legacyBank
```

## Current Flow

```text
GitHub repo
  -> inspect source
  -> create migration session
  -> analyze AST/dependencies
  -> create migration plan
  -> approve plan
  -> generate whole modern code batch
  -> approve generated batch
  -> download ZIP package
```

## Notes

- The app only supports public GitHub repositories in this MVP.
- Cloned repository code is treated as untrusted input.
- Generated code is packaged for review; it is not executed by the backend.
- `.env`, SQLite DB files, artifacts, virtualenvs, and node modules should stay
  out of Git.
