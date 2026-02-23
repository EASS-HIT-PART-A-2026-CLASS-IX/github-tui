# OctoLens Web UI

Vite + React dashboard for the OctoLens backend API.

Root documentation is the source of truth for full setup and demo flow:
- `../README.md`

## Local Development

1. Configure root `.env` in repo root (see `../README.md`), then start backend:

```bash
docker compose up --build
```

2. Start frontend:

```bash
npm install
VITE_DEV_PROXY_TARGET=http://localhost:8000 npm run dev
```

3. Open:

- `http://127.0.0.1:5173`

## Environment

- `VITE_DEV_PROXY_TARGET` sets Vite `/api` proxy target (default: `http://localhost:8000`).
- `VITE_API_BASE_URL` is optional and bypasses proxy for direct API calls.

You can copy `frontend/.env.example` if needed.

## Scripts

- `npm run dev`: local development server
- `npm run build`: production build
- `npm run preview`: local preview of production build
- `npm run lint`: ESLint checks
