# Setup procedure — desktop

This is the first-time install for running House Maint Tracker on a local machine (Patrick’s desktop or any household computer). For an always-on box, use [SERVER.md](SERVER.md) after this works.

## 1. Prerequisites

- **Git**
- **Python 3.12+** (`python3 --version`)
- Optional, only if you will change the UI: **Node.js 20+** and npm

Confirm:

```bash
git --version
python3 --version
```

On Debian/Ubuntu if Python is missing:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
```

On Windows, install Python from python.org and tick “Add python.exe to PATH”.

## 2. Clone

```bash
git clone https://github.com/psteen-coder/house-maint-tracker.git
cd house-maint-tracker
```

## 3. Backend (required)

From the repo root:

```bash
cd backend
python3 -m venv .venv
```

Activate the venv:

- Linux / macOS: `source .venv/bin/activate`
- Windows cmd: `.venv\Scripts\activate.bat`
- Windows PowerShell: `.venv\Scripts\Activate.ps1`

Install:

```bash
pip install -r requirements.txt
```

Start:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

First start creates `backend/house_maint.db` and seeds the 1944 Dinius household (users + sample tasks).

Open http://127.0.0.1:8000 — you should see **House Maint Tracker**, not a Vite “Get started” page.

Sign in as `patrick@1944dinius.local` / `adminpass`.

Leave this terminal open while you use the app. Ctrl+C stops it.

## 4. Optional: live frontend (UI development)

Only needed if you are editing React files. The committed `backend/app/static/` already contains a built UI.

Terminal A (API):

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal B (Vite, proxies `/api` to port 8000):

```bash
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173

After UI changes, publish them into the Python app:

```bash
cd frontend
npm run build
```

That writes `backend/app/static/`. Restart uvicorn if it is already serving the old files without `--reload` on static.

## 5. Tests

```bash
cd backend
source .venv/bin/activate
pytest -q
```

Expect 17 passing tests (auth, roles, kanban, calendar, weather reschedule kernel, seasonal dates).

## 6. Sanity checks

| Check | How |
|-------|-----|
| API up | `curl http://127.0.0.1:8000/api/health` → `{"ok":true,...}` |
| Real UI | View source of `/` — `<title>House Maint Tracker</title>` |
| Database | `ls backend/house_maint.db` after first start |
| Board | Sign in → Board shows Due / In progress / Completed columns |

## 7. Data location

| Thing | Default |
|-------|---------|
| SQLite | `backend/house_maint.db` (cwd when you start uvicorn) |
| Override | `HOUSE_MAINT_DB=sqlite:////absolute/path/house_maint.db` |
| Built UI | `backend/app/static/` |

Back up the `.db` file. That is the whole household dataset.

## 8. Stop / restart

Stop: Ctrl+C in the uvicorn terminal.

Restart: same `uvicorn` command from `backend/` with the venv active. Existing users and tasks persist in SQLite.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `python3: command not found` | Install Python 3.12+ |
| `externally-managed-environment` | You skipped the venv — create `.venv` and activate it |
| Port 8000 in use | `--port 8001` and use that URL |
| Blank page / old Vite starter | You are not serving `backend/app/static`; run `npm run build` in `frontend/` then restart uvicorn |
| Login fails | Use the seeded emails exactly, including `@1944dinius.local` |
| Weather button errors | Machine needs outbound HTTPS to `api.open-meteo.com` |
