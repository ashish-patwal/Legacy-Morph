# Legacy-Morph Setup

This guide explains how to install, configure, start, and test Legacy-Morph
locally.

## 1. Clone Or Open The Project

If the project is already on your machine:

```bash
cd /Users/ks/Desktop/Corporate/Legacy-Morph
```

If cloning fresh:

```bash
git clone https://github.com/ashish-patwal/Legacy-Morph.git
cd Legacy-Morph
```

## 2. Backend Setup

Create a virtual environment from the repository root:

```bash
python -m venv .venv
```

Install backend dependencies:

```bash
.venv/bin/pip install -r backend/requirements.txt
```

## 3. Frontend Setup

Install frontend dependencies:

```bash
cd frontend
npm install
```

Return to the repository root when finished:

```bash
cd ..
```

## 4. Environment Setup

Create your local `.env`:

```bash
cp .env.example .env
```

Edit `.env` and set:

```text
OPENAI_API_KEY=your_real_openai_api_key
```

Recommended local development values:

```text
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-4.1-mini
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
VITE_BACKEND_URL=http://localhost:8000
```

Important:

- Do not commit `.env`.
- Do not put a real API key in `.env.example`.
- If `OPENAI_API_KEY` is missing, the backend may run in mock mode.

## 5. Start Backend

From the repository root:

```bash
cd backend
../.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
```

Backend URLs:

```text
http://127.0.0.1:8000
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/health
```

Health should show:

```json
{"status":"ok","service":"legacy-morph-backend","ai_mode":"openai"}
```

## 6. Start Frontend

Open another terminal:

```bash
cd /Users/ks/Desktop/Corporate/Legacy-Morph/frontend
npm run dev -- --host 127.0.0.1
```

Frontend URL:

```text
http://127.0.0.1:5173
```

## 7. Test With A Repository

Use this sample repository:

```text
https://github.com/jitesh0400/legacyBank
```

Flow:

1. Paste the repository URL.
2. Use branch `main`.
3. Click **Inspect repository**.
4. Select the files you want to migrate.
5. Choose the target language and framework.
6. Create a migration session.
7. Run analysis.
8. Create and approve the migration plan.
9. Click **Generate whole code**.
10. Review the generated batch.
11. Click **Approve full batch**.
12. Open **Package**.
13. Click **Download ZIP package**.

If download does not start in the in-app browser, use the **Direct ZIP link** on
the Package screen.

## 8. Common Commands

Run backend compile check:

```bash
.venv/bin/python -m py_compile backend/main.py backend/schemas.py
```

Build frontend:

```bash
cd frontend
npm run build
```

Check Git status:

```bash
git status --short
```

## 9. Troubleshooting

### Backend shows mock mode

Check `.env`:

```text
OPENAI_API_KEY=your_real_openai_api_key
```

Restart the backend after changing `.env`.

### CORS error

Make sure `.env` includes both local frontend origins:

```text
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Restart the backend.

### Port already in use

Find the process:

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
lsof -nP -iTCP:5173 -sTCP:LISTEN
```

Stop the process if needed:

```bash
kill <PID>
```

### ZIP package does not download

Use the **Direct ZIP link** on the Package screen. The backend package endpoint
has this shape:

```text
http://127.0.0.1:8000/migration-sessions/<session_id>/package
```

### GitHub repository inspection fails

Check:

- The repository is public.
- The URL is a valid GitHub URL.
- The branch exists.
- The repository is not too large for the MVP limits.
