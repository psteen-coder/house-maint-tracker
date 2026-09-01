from __future__ import annotations

import json
import os
import secrets
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Annotated, Any

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .models import Base, Occurrence, SessionToken, Setting, Task, User, make_engine
from .schedule import following_due, next_due
from .seed import get_setting, hash_password, seed_if_empty, verify_password
from .weather import apply_reschedule, choose_favorable_date, day_is_favorable

DATABASE_URL = os.environ.get("HOUSE_MAINT_DB", "sqlite:///./house_maint.db")
engine, SessionLocal = make_engine(DATABASE_URL)

app = FastAPI(title="House Maint Tracker", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


Db = Annotated[Session, Depends(get_db)]


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()


def current_user(
    db: Db,
    authorization: Annotated[str | None, Header()] = None,
    x_token: Annotated[str | None, Header()] = None,
) -> User:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if not token:
        token = x_token
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in required")
    row = db.get(SessionToken, token)
    if not row:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid session")
    user = db.get(User, row.user_id)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown user")
    return user


UserDep = Annotated[User, Depends(current_user)]


def require_roles(*roles: str):
    def inner(user: UserDep) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
        return user

    return inner


class LoginIn(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    theme: str


class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: str = "member"


class ThemeIn(BaseModel):
    theme: str


class TaskIn(BaseModel):
    title: str
    description: str = ""
    estimated_minutes: int = 30
    recurrence: str = "once"
    season: str | None = None
    month: int | None = None
    day: int | None = None
    conditions: list[str] = Field(default_factory=list)
    weather_prefs: dict[str, Any] = Field(default_factory=dict)
    default_assignee_id: int | None = None
    depends_on_id: int | None = None


class OccurrencePatch(BaseModel):
    status: str | None = None
    due_date: date | None = None
    assignee_id: int | None = None
    notes: str | None = None


def user_out(u: User) -> dict:
    return {"id": u.id, "name": u.name, "email": u.email, "role": u.role, "theme": u.theme}


def _dependency_blocked(db: Session, o: Occurrence) -> tuple[bool, str | None]:
    t = o.task
    if not t or not t.depends_on_id:
        return False, None
    parent_open = (
        db.query(Occurrence)
        .filter(
            Occurrence.task_id == t.depends_on_id,
            Occurrence.status != "done",
            Occurrence.due_date <= o.due_date,
        )
        .first()
    )
    if parent_open:
        parent = db.get(Task, t.depends_on_id)
        return True, f"Waiting on: {parent.title if parent else 'prior task'}"
    return False, None


def _occ_out(db: Session, o: Occurrence) -> dict:
    blocked, reason = _dependency_blocked(db, o)
    assignee = o.assignee
    t = o.task
    return {
        "id": o.id,
        "task_id": o.task_id,
        "title": t.title if t else "",
        "description": t.description if t else "",
        "estimated_minutes": t.estimated_minutes if t else 0,
        "recurrence": t.recurrence if t else "once",
        "season": t.season if t else None,
        "conditions": t.condition_list() if t else [],
        "weather_prefs": t.prefs() if t else {},
        "depends_on_id": t.depends_on_id if t else None,
        "due_date": o.due_date.isoformat(),
        "original_due_date": o.original_due_date.isoformat(),
        "status": o.status,
        "assignee_id": o.assignee_id,
        "assignee_name": assignee.name if assignee else None,
        "completed_at": o.completed_at.isoformat() if o.completed_at else None,
        "weather_adjusted": o.weather_adjusted,
        "weather_reason": o.weather_reason,
        "notes": o.notes,
        "blocked": blocked,
        "block_reason": reason,
    }


def task_out(t: Task) -> dict:
    return {
        "id": t.id,
        "title": t.title,
        "description": t.description,
        "estimated_minutes": t.estimated_minutes,
        "recurrence": t.recurrence,
        "season": t.season,
        "month": t.month,
        "day": t.day,
        "conditions": t.condition_list(),
        "weather_prefs": t.prefs(),
        "default_assignee_id": t.default_assignee_id,
        "depends_on_id": t.depends_on_id,
        "active": t.active,
    }


@app.get("/api/health")
def health():
    return {"ok": True, "service": "house-maint-tracker"}


@app.post("/api/auth/login")
def login(body: LoginIn, db: Db):
    user = db.query(User).filter(User.email == body.email.lower().strip()).first()
    if not user or not verify_password(body.password, user.password_hash):
        # also try original case emails from seed
        user = db.query(User).filter(User.email == body.email.strip()).first()
        if not user or not verify_password(body.password, user.password_hash):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Bad email or password")
    token = secrets.token_urlsafe(32)
    db.add(SessionToken(token=token, user_id=user.id))
    db.commit()
    return {"token": token, "user": user_out(user)}


@app.post("/api/auth/logout")
def logout(user: UserDep, db: Db, authorization: Annotated[str | None, Header()] = None):
    token = (authorization or "").split(" ", 1)[-1].strip()
    row = db.get(SessionToken, token)
    if row:
        db.delete(row)
        db.commit()
    return {"ok": True}


@app.get("/api/me")
def me(user: UserDep, db: Db):
    return {
        "user": user_out(user),
        "house": {
            "name": get_setting(db, "name", "1944 Dinius"),
            "address": get_setting(db, "address", ""),
            "lat": float(get_setting(db, "lat", "0") or 0),
            "lon": float(get_setting(db, "lon", "0") or 0),
        },
    }


@app.patch("/api/me/theme")
def set_theme(body: ThemeIn, user: UserDep, db: Db):
    allowed = {"light", "dark", "forest", "terracotta", "slate"}
    if body.theme not in allowed:
        raise HTTPException(400, "Unknown theme")
    user.theme = body.theme
    db.commit()
    return user_out(user)


@app.get("/api/users")
def list_users(user: UserDep, db: Db):
    return [user_out(u) for u in db.query(User).order_by(User.id).all()]


@app.post("/api/users")
def create_user(body: UserCreate, user: UserDep, db: Db):
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin only")
    if body.role not in {"admin", "member", "viewer"}:
        raise HTTPException(400, "Invalid role")
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(409, "Email already exists")
    u = User(
        name=body.name,
        email=body.email.strip(),
        password_hash=hash_password(body.password),
        role=body.role,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return user_out(u)


@app.delete("/api/users/{user_id}")
def delete_user(user_id: int, user: UserDep, db: Db):
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin only")
    if user_id == user.id:
        raise HTTPException(400, "Cannot delete yourself")
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "Not found")
    db.delete(target)
    db.commit()
    return {"ok": True}


@app.get("/api/tasks")
def list_tasks(user: UserDep, db: Db):
    return [task_out(t) for t in db.query(Task).order_by(Task.id).all()]


@app.post("/api/tasks")
def create_task(body: TaskIn, user: UserDep, db: Db):
    if user.role == "viewer":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Viewers cannot mutate tasks")
    t = Task(
        title=body.title,
        description=body.description,
        estimated_minutes=body.estimated_minutes,
        recurrence=body.recurrence,
        season=body.season,
        month=body.month,
        day=body.day,
        conditions=json.dumps(body.conditions),
        weather_prefs=json.dumps(body.weather_prefs),
        default_assignee_id=body.default_assignee_id,
        depends_on_id=body.depends_on_id,
    )
    db.add(t)
    db.flush()
    due = next_due(
        recurrence=t.recurrence,
        season=t.season,
        month=t.month,
        day=t.day,
        from_date=date.today(),
    )
    db.add(
        Occurrence(
            task_id=t.id,
            due_date=due,
            original_due_date=due,
            status="todo",
            assignee_id=t.default_assignee_id,
        )
    )
    db.commit()
    db.refresh(t)
    return task_out(t)


@app.get("/api/occurrences")
def list_occurrences(user: UserDep, db: Db):
    rows = db.query(Occurrence).order_by(Occurrence.due_date).all()
    return [_occ_out(db, o) for o in rows]


@app.patch("/api/occurrences/{occ_id}")
def patch_occurrence(occ_id: int, body: OccurrencePatch, user: UserDep, db: Db):
    if user.role == "viewer":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Viewers cannot mutate tasks")
    o = db.get(Occurrence, occ_id)
    if not o:
        raise HTTPException(404, "Not found")
    if body.status:
        if body.status not in {"todo", "in_progress", "done"}:
            raise HTTPException(400, "Bad status")
        blocked, reason = _dependency_blocked(db, o)
        if blocked and body.status in {"in_progress", "done"}:
            raise HTTPException(409, reason or "Blocked by dependency")
        o.status = body.status
        if body.status == "done":
            o.completed_at = datetime.utcnow()
            t = o.task
            if t and t.recurrence != "once":
                nxt = following_due(task_out(t), o.due_date)
                exists = (
                    db.query(Occurrence)
                    .filter(Occurrence.task_id == t.id, Occurrence.due_date == nxt)
                    .first()
                )
                if not exists:
                    db.add(
                        Occurrence(
                            task_id=t.id,
                            due_date=nxt,
                            original_due_date=nxt,
                            status="todo",
                            assignee_id=t.default_assignee_id,
                        )
                    )
        elif body.status != "done":
            o.completed_at = None
    if body.due_date:
        o.due_date = body.due_date
    if body.assignee_id is not None:
        o.assignee_id = body.assignee_id
    if body.notes is not None:
        o.notes = body.notes
    db.commit()
    db.refresh(o)
    return _occ_out(db, o)


@app.get("/api/kanban")
def kanban(user: UserDep, db: Db):
    today = date.today()
    week = today + timedelta(days=7)
    due, progress, done = [], [], []
    for o in db.query(Occurrence).all():
        row = _occ_out(db, o)
        if o.status == "in_progress":
            progress.append(row)
        elif o.status == "done":
            if o.completed_at and o.completed_at.date() >= today - timedelta(days=7):
                done.append(row)
        else:
            if today <= o.due_date <= week:
                due.append(row)
    due.sort(key=lambda r: r["due_date"])
    progress.sort(key=lambda r: r["due_date"])
    done.sort(key=lambda r: r["completed_at"] or "", reverse=True)
    return {"due": due, "in_progress": progress, "completed": done}


@app.get("/api/calendar")
def calendar(user: UserDep, db: Db, year: int | None = None, month: int | None = None):
    today = date.today()
    year = year or today.year
    month = month or today.month
    rows = (
        db.query(Occurrence)
        .filter(
            Occurrence.due_date >= date(year, month, 1),
            Occurrence.due_date < (date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)),
        )
        .all()
    )
    by_day: dict[str, list] = {}
    for o in rows:
        by_day.setdefault(o.due_date.isoformat(), []).append(_occ_out(db, o))
    return {"year": year, "month": month, "days": by_day}


def _forecast_from_open_meteo(lat: float, lon: float) -> dict[date, dict]:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "precipitation_sum,temperature_2m_max,windspeed_10m_max",
        "timezone": "America/Detroit",
        "forecast_days": 16,
    }
    with httpx.Client(timeout=20) as client:
        r = client.get(url, params=params)
        r.raise_for_status()
        data = r.json()
    daily = data.get("daily") or {}
    out: dict[date, dict] = {}
    times = daily.get("time") or []
    for i, raw in enumerate(times):
        d = date.fromisoformat(raw)
        out[d] = {
            "precip_mm": (daily.get("precipitation_sum") or [None])[i],
            "temp_max_c": (daily.get("temperature_2m_max") or [None])[i],
            "wind_kmh": (daily.get("windspeed_10m_max") or [None])[i],
        }
    return out


@app.get("/api/weather/forecast")
def forecast(user: UserDep, db: Db):
    lat = float(get_setting(db, "lat", "41.9849515"))
    lon = float(get_setting(db, "lon", "-83.9916572"))
    try:
        days = _forecast_from_open_meteo(lat, lon)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Weather feed unavailable: {exc}") from exc
    return {
        "lat": lat,
        "lon": lon,
        "days": [
            {
                "date": d.isoformat(),
                **wx,
                "favorable_sample": day_is_favorable(
                    wx, {"outdoor": True, "require_dry": True, "max_precip_mm": 0.8}
                ),
            }
            for d, wx in sorted(days.items())
        ],
    }


@app.post("/api/weather/reschedule")
def reschedule(user: UserDep, db: Db, window: int = 3):
    if user.role == "viewer":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Viewers cannot mutate tasks")
    lat = float(get_setting(db, "lat", "41.9849515"))
    lon = float(get_setting(db, "lon", "-83.9916572"))
    try:
        forecast_map = _forecast_from_open_meteo(lat, lon)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Weather feed unavailable: {exc}") from exc
    moved = []
    occs = db.query(Occurrence).filter(Occurrence.status != "done").all()
    payload = []
    for o in occs:
        payload.append(
            {
                "id": o.id,
                "due_date": o.due_date,
                "original_due_date": o.original_due_date,
                "status": o.status,
                "weather_prefs": o.task.prefs() if o.task else {},
            }
        )
    updated = apply_reschedule(payload, forecast_map, window=window)
    by_id = {row["id"]: row for row in updated}
    for o in occs:
        row = by_id[o.id]
        if row["due_date"] != o.due_date:
            o.due_date = row["due_date"]
            o.weather_adjusted = True
            o.weather_reason = row["weather_reason"]
            moved.append(_occ_out(db, o))
        else:
            o.weather_reason = row["weather_reason"]
            o.weather_adjusted = False
    db.commit()
    return {"moved": moved, "checked": len(occs)}


STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
