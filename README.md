# adrobot

FastAPI + SQLAlchemy backend with a React frontend for creating and editing Keitaro campaigns.

## Features

- create campaigns with:
  - campaign name
  - country geo code
  - offer id
- campaign editor with:
  - campaign list synced from Keitaro
  - fetch/push/cancel per flow
  - soft delete / revive offers
  - pin / unpin offers
  - offer autocomplete by id or name
  - share rebalancing
- local persistence in SQLite
- Alembic migrations

## Project structure

- `backend/` — FastAPI app, SQLAlchemy models, Alembic migrations
- `frontend/` — React app

## Requirements

- Python 3.11+
- Node.js 18+
- Keitaro API key

## Environment variables

### Backend

Required:
- `KEITARO_API_KEY`

Optional:
- `KEITARO_BASE_URL` — default `https://tlgk.host/admin_api/v1`
- `KEITARO_DOMAIN_ID`
- `KEITARO_GROUP_ID`
- `KEITARO_TRAFFIC_SOURCE_ID`
- `KEITARO_GOOGLE_URL` — default `https://www.google.com/`
- `KEITARO_GROUP_TYPE` — default `campaigns`
- `DATABASE_URL` — default `sqlite:///./data/adrobot.db`
- `CORS_ORIGIN` — default `http://localhost:5173`

### Frontend

- `VITE_API_BASE_URL` — default `http://127.0.0.1:8000`

## Setup

### Backend

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set `KEITARO_API_KEY` in `backend/.env` or export it in your shell before running.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
```

## Migrations

Run migrations from the `backend/` directory:

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
```

To create a new migration after changing models:

```bash
cd backend
source .venv/bin/activate
alembic revision --autogenerate -m "describe change"
```

## Run the app

### Backend

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm run dev
```

## Routes

- `/campaigns` — cached campaign list, auto-syncs from KT on load
- `/campaigns/:id/edit` — campaign editor
- `/create` — create campaign form

## Notes

- The campaign editor keeps its state in the local database.
- Flows are fetched from Keitaro only when you press **Fetch from KT**.
- Draft changes are saved locally until you press **Push to KT**.
- The SQLite database lives at `backend/data/adrobot.db` by default.
