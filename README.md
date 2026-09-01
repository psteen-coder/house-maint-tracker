# House Maint Tracker

Household maintenance tracker for **1944 Dinius Road, Raisin Township, MI**.

Web app + SQLite backend. Run it on a desktop or a small always-on box. The same UI installs as an Android PWA; `android/` is a WebView wrapper for a dedicated app.

## Features

- Household users with roles: `admin`, `member`, `viewer`
- Recurring tasks (monthly / quarterly / seasonal / yearly) with conditions, estimates, assignees, and optional dependencies
- Kanban: due within a week · in progress · completed in the past week
- Month calendar forecast
- Light, dark, forest, terracotta, and slate themes
- Open-Meteo weather feed; outdoor tasks shift ±3 days when the scheduled day fails dry/temp/wind prefs

## Docs

| Doc | What it covers |
|-----|----------------|
| [docs/SETUP.md](docs/SETUP.md) | First-time install on a desktop (Linux / macOS / Windows) |
| [docs/SERVER.md](docs/SERVER.md) | Run as a LAN/server service (systemd, bind address, backup) |
| [docs/ANDROID.md](docs/ANDROID.md) | PWA install + Android Studio WebView |
| [docs/OPERATIONS.md](docs/OPERATIONS.md) | Roles, weather reschedule, house location, passwords |
| [docs/API.md](docs/API.md) | HTTP API reference |

## Quick start (built UI, one process)

Needs Python 3.12+ only. A production frontend is already in `backend/app/static/`.

```bash
git clone https://github.com/psteen-coder/house-maint-tracker.git
cd house-maint-tracker/backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Or: `bash scripts/run-local.sh`

Open http://127.0.0.1:8000

| Person  | Email                    | Password   | Role   |
|---------|--------------------------|------------|--------|
| Patrick | patrick@1944dinius.local | adminpass  | admin  |
| Alex    | alex@1944dinius.local    | memberpass | member |
| Jamie   | jamie@1944dinius.local   | viewerpass | viewer |

Change these before exposing the app on a network. See [docs/OPERATIONS.md](docs/OPERATIONS.md).

SQLite file: `backend/house_maint.db` (override with `HOUSE_MAINT_DB`).
House coordinates: 41.9849515, -83.9916572 (OSM: 1944 Dinius Road).

## Tests

```bash
cd backend
.venv/bin/pytest -q
```

## Repo

https://github.com/psteen-coder/house-maint-tracker
