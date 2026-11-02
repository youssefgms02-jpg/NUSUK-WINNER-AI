# NUSUK WINNER AI

Responsive Arabic-first PWA starter for lawful public information discovery, code/key organization, and AI-assisted question analysis.

## Stack
- Backend: Python 3.11+, FastAPI, SQLAlchemy, SQLite
- Frontend: React, TypeScript, Vite
- OCR: Tesseract (optional system dependency)
- AI: OpenAI-compatible API integration
- PWA: installable manifest and service worker

## Safety and source policy
- Scanner accepts explicitly configured public RSS/Atom feeds only.
- No login automation, private-group collection, access-control bypass, or unauthorized scraping.
- Discovered codes remain `unverified` until an official validation method confirms them.

## Development
See `backend/` and `frontend/` for the application. Configure secrets in `backend/.env`; never expose provider API keys in frontend code.
