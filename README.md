# NUSUK WINNER AI

Arabic-first responsive PWA for organizing challenge codes, reviewing configured public RSS/Atom sources, extracting text from question images, and optional AI-assisted question analysis.

## Architecture
- Frontend: React, TypeScript, Vite, deployed on Vercel from `frontend/`.
- API: FastAPI + SQLAlchemy, deployed as a Docker service from `backend/`.
- Database: PostgreSQL for persistent hosted data; SQLite is for local development only.
- OCR: Tesseract with Arabic and English language packs, installed in the backend Docker image.
- PWA: web manifest and service worker.

## Deploy

### 1. Backend and database
1. Open Render and choose **New → Blueprint**.
2. Connect `youssefgms02-jpg/NUSUK-WINNER-AI`.
3. Render detects the root `render.yaml`; review the web service and PostgreSQL database before creating them.
4. Wait for the service named `nusuk-winner-ai-api` to become healthy at `/api/health`.
5. If you use a different frontend domain, update `CORS_ORIGINS` on the API service to that exact HTTPS origin.

The free PostgreSQL tier, where offered, is temporary and is not suitable for permanent production data. Use a paid persistent database plan before storing important information.

### 2. Frontend
The Vercel project is configured with root directory `frontend`, build command `npm run build`, and output directory `dist`. Set `VITE_API_URL` to the actual HTTPS URL assigned to the backend service, then redeploy the frontend.

### 3. Optional AI
Set `AI_API_KEY` in the backend service environment to a key from an OpenAI-compatible provider. Never put this secret in Vercel or frontend code. `AI_BASE_URL` and `AI_MODEL` are optional provider settings.

## Local development

Backend:
```bash
cd backend
python -m venv .venv
# Activate the environment, then:
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:
```bash
cd frontend
npm install
npm run dev
```

Set `VITE_API_URL=http://127.0.0.1:8000` in `frontend/.env.local` for local development. For OCR locally, install Tesseract and the Arabic and English language data.

## Source and safety notes
- The scanner accepts only explicitly configured HTTPS RSS/Atom sources, rejects non-public DNS destinations and does not follow redirects.
- Source feeds are size-limited; only public feed content is read.
- Discovered codes remain `unverified` until confirmed through an official method.
- AI answers are suggestions and do not verify code validity.
- Do not store secrets in the frontend or commit `.env` files.

## CI
GitHub Actions runs backend tests and a TypeScript/Vite production build on pushes and pull requests.
