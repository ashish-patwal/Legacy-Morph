# Deployment

This repository is configured to deploy the React frontend and FastAPI backend
as one Docker web service on Render.

## Render

1. Push this repository to GitHub.
2. Open the Render dashboard and choose **New > Blueprint**.
3. Connect the repository and select the root `render.yaml`.
4. When Render asks for `OPENAI_API_KEY`, paste your OpenAI API key.
5. Create the Blueprint and wait for the first deploy to finish.

The public app URL will be the service's `onrender.com` URL. The frontend and
backend share that one origin:

- App: `https://your-service.onrender.com`
- Health check: `https://your-service.onrender.com/health`
- API docs: `https://your-service.onrender.com/docs`

## Important Free-Tier Note

Render Free web services use an ephemeral filesystem. This app currently uses
SQLite and local artifact files, so migration sessions can be lost when the
service restarts, redeploys, or spins down after being idle. This setup is good
for demos and testing. For durable production use, move persistence to a hosted
database and object storage.
