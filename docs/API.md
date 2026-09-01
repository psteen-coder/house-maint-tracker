# HTTP API

Base URL: `http://127.0.0.1:8000`

All routes except `/api/health` and `/api/auth/login` need:

```
Authorization: Bearer <token>
```

Token comes from login. JSON request/response.

## Auth

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/health` | `{ "ok": true, "service": "house-maint-tracker" }` |
| POST | `/api/auth/login` | body `{ "email", "password" }` → `{ token, user }` |
| POST | `/api/auth/logout` | invalidates this token |
| GET | `/api/me` | `{ user, house }` (name, address, lat, lon) |
| PATCH | `/api/me/theme` | `{ "theme": "light\|dark\|forest\|terracotta\|slate" }` |

## Users

| Method | Path | Who |
|--------|------|-----|
| GET | `/api/users` | any signed-in role |
| POST | `/api/users` | admin; body `{ name, email, password, role }` |
| DELETE | `/api/users/{id}` | admin; cannot delete self |

Roles: `admin`, `member`, `viewer`.

## Tasks (catalog)

| Method | Path | Who |
|--------|------|-----|
| GET | `/api/tasks` | any |
| POST | `/api/tasks` | admin/member; viewer → 403 |

Create body (all optional except `title`):

```json
{
  "title": "Clean gutters",
  "description": "",
  "estimated_minutes": 90,
  "recurrence": "seasonal",
  "season": "fall",
  "month": null,
  "day": null,
  "conditions": ["ladder", "dry weather"],
  "weather_prefs": {
    "outdoor": true,
    "require_dry": true,
    "max_precip_mm": 0.8,
    "min_temp_c": 4,
    "max_wind_kmh": 40
  },
  "default_assignee_id": 2,
  "depends_on_id": null
}
```

Creating a task also inserts the next `Occurrence`.

## Occurrences (work items)

| Method | Path | Who |
|--------|------|-----|
| GET | `/api/occurrences` | any |
| PATCH | `/api/occurrences/{id}` | admin/member |

Patch body (any subset): `{ "status", "due_date", "assignee_id", "notes" }`

`status`: `todo` | `in_progress` | `done`

Completing a recurring task schedules the following due date. Blocked dependencies return **409**.

## Board and calendar

| Method | Path |
|--------|------|
| GET | `/api/kanban` |
| GET | `/api/calendar?year=2026&month=9` |

Kanban JSON:

```json
{ "due": [], "in_progress": [], "completed": [] }
```

- `due` — status not done/in_progress, due date in today … today+7
- `in_progress` — status `in_progress`
- `completed` — status `done` and `completed_at` within the last 7 days

Calendar: `{ year, month, days: { "YYYY-MM-DD": [occurrence, ...] } }`

## Weather

| Method | Path | Who |
|--------|------|-----|
| GET | `/api/weather/forecast` | any |
| POST | `/api/weather/reschedule?window=3` | admin/member |

Forecast is Open-Meteo. Reschedule returns `{ checked, moved }`.

Feed down → **502**.

## Interactive docs

With uvicorn running: http://127.0.0.1:8000/docs (FastAPI Swagger UI) and `/redoc`.
The SPA is mounted at `/`; `/docs` remains on the API app.
