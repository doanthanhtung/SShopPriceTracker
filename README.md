# SShop Price Tracker

Production-grade web refactor of the original desktop price tracker.

## Backend

Run the backend stack:

```bash
docker compose up --build
```

API health check:

```bash
curl http://localhost:8000/api/v1/health
```

Run Alembic migrations from the host after installing dependencies:

```bash
alembic -c backend/alembic.ini upgrade head
```

Quality checks:

```bash
.venv\Scripts\python.exe -m pytest backend\tests
.venv\Scripts\python.exe -m ruff check backend\src backend\tests
.venv\Scripts\python.exe -m mypy backend\src backend\tests
```

## Frontend

Install dependencies and run the Next.js app:

```bash
cd frontend
npm install
npm run dev
```

The local UI runs on `http://localhost:3000` and expects the backend API at
`http://localhost:8000/api/v1` by default.

Frontend checks:

```bash
npm run typecheck
npm run build
```
