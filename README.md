# House Maint Tracker

Household maintenance tracker for **1944 Dinius Road, Raisin Township, MI**.

Web app + SQLite backend you can run on a desktop or a small server. Same UI installs as an Android PWA, and an Android WebView project wraps it.

## Features

- Household users with roles: `admin`, `member`, `viewer`
- Recurring tasks (monthly / quarterly / seasonal / yearly) with conditions, estimates, assignees, and optional dependencies
- Kanban: due within a week · in progress · completed in the past week
- Month calendar forecast
- Light, dark, forest, terracotta, and slate themes
- Open-Meteo weather feed; outdoor tasks shift ±3 days when the scheduled day is a bad weather match

## Run locally

```bash
# backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# frontend (dev, proxies /api → :8000)
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173

Production-style (API serves the built UI):

```bash
cd frontend && npm install && npm run build
cd ../backend && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then open http://127.0.0.1:8000

## Seeded logins

| Person  | Email                       | Password    | Role   |
|---------|-----------------------------|-------------|--------|
| Patrick | patrick@1944dinius.local    | adminpass   | admin  |
| Alex    | alex@1944dinius.local       | memberpass  | member |
| Jamie   | jamie@1944dinius.local      | viewerpass  | viewer |

Change these after first login if you put the box on a network.

SQLite file: `backend/house_maint.db` (override with `HOUSE_MAINT_DB`).

House lat/lon is seeded from OSM for 1944 Dinius Road (41.9849515, -83.9916572).

## Tests

```bash
cd backend
.venv/bin/pytest -q
```

## Android

- **PWA:** in Chrome on Android, open the site → Add to Home screen (`manifest.webmanifest` + service worker).
- **WebView project:** `android/` — open in Android Studio. Default URL is `http://10.0.2.2:8000` (emulator → host). Change `MainActivity.APP_URL` for a LAN/server deploy.

## GitHub

https://github.com/psteen-coder/house-maint-tracker
