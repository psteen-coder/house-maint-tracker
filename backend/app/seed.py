from __future__ import annotations

import hashlib
import json
import secrets
from datetime import date, timedelta

from sqlalchemy.orm import Session

from .models import Occurrence, Setting, Task, User
from .schedule import next_due


HOUSE = {
    "name": "1944 Dinius",
    "address": "1944 Dinius Road, Raisin Township, Lenawee County, Michigan 49286",
    "lat": "41.9849515",
    "lon": "-83.9916572",
    "timezone": "America/Detroit",
}


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000)
    return f"{salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, _ = stored.split("$", 1)
    except ValueError:
        return False
    return secrets.compare_digest(hash_password(password, salt), stored)


def seed_if_empty(db: Session) -> None:
    if db.query(User).first():
        return

    admin = User(
        name="Patrick",
        email="patrick@1944dinius.local",
        password_hash=hash_password("adminpass"),
        role="admin",
        theme="forest",
    )
    member = User(
        name="Alex",
        email="alex@1944dinius.local",
        password_hash=hash_password("memberpass"),
        role="member",
        theme="light",
    )
    viewer = User(
        name="Jamie",
        email="jamie@1944dinius.local",
        password_hash=hash_password("viewerpass"),
        role="viewer",
        theme="dark",
    )
    db.add_all([admin, member, viewer])
    db.flush()

    for k, v in HOUSE.items():
        db.add(Setting(key=k, value=v))

    outdoor_dry = json.dumps(
        {"outdoor": True, "require_dry": True, "max_precip_mm": 0.8, "min_temp_c": 4, "max_wind_kmh": 40}
    )
    indoor = json.dumps({"outdoor": False})

    gutters = Task(
        title="Clean gutters",
        description="Clear leaves and check downspouts. Spring and fall.",
        estimated_minutes=90,
        recurrence="seasonal",
        season="fall",
        conditions=json.dumps(["ladder", "dry weather", "two people preferred"]),
        weather_prefs=outdoor_dry,
        default_assignee_id=member.id,
    )
    gutters_spring = Task(
        title="Clean gutters (spring)",
        description="Spring gutter pass after seed drop.",
        estimated_minutes=90,
        recurrence="seasonal",
        season="spring",
        conditions=json.dumps(["ladder", "dry weather"]),
        weather_prefs=outdoor_dry,
        default_assignee_id=member.id,
    )
    filter_task = Task(
        title="Change furnace air filter",
        description="Swap 16x25x1 filter. Indoor, monthly.",
        estimated_minutes=15,
        recurrence="monthly",
        day=1,
        conditions=json.dumps(["spare filter on hand"]),
        weather_prefs=indoor,
        default_assignee_id=admin.id,
    )
    hvac = Task(
        title="HVAC seasonal service",
        description="Pre-cooling inspection. Depends on filter change being current.",
        estimated_minutes=60,
        recurrence="seasonal",
        season="spring",
        conditions=json.dumps(["tech appointment"]),
        weather_prefs=indoor,
        default_assignee_id=admin.id,
        depends_on_id=None,  # set after flush
    )
    mow = Task(
        title="Mow and edge lawn",
        description="Keep under 4 inches during growing season.",
        estimated_minutes=75,
        recurrence="monthly",
        day=15,
        season="summer",
        conditions=json.dumps(["dry grass", "daylight"]),
        weather_prefs=outdoor_dry,
        default_assignee_id=member.id,
    )
    smoke = Task(
        title="Test smoke and CO detectors",
        description="Press test on every unit; replace batteries if chirping.",
        estimated_minutes=20,
        recurrence="quarterly",
        day=1,
        conditions=json.dumps(["9V batteries in drawer"]),
        weather_prefs=indoor,
        default_assignee_id=admin.id,
    )
    windows = Task(
        title="Wash exterior windows",
        description="South and west faces first.",
        estimated_minutes=120,
        recurrence="seasonal",
        season="summer",
        conditions=json.dumps(["no rain next 24h"]),
        weather_prefs=outdoor_dry,
        default_assignee_id=member.id,
    )
    db.add_all([gutters, gutters_spring, filter_task, hvac, mow, smoke, windows])
    db.flush()
    hvac.depends_on_id = filter_task.id

    today = date.today()
    templates = [gutters, gutters_spring, filter_task, hvac, mow, smoke, windows]
    for t in templates:
        due = next_due(
            recurrence=t.recurrence,
            season=t.season,
            month=t.month,
            day=t.day,
            from_date=today - timedelta(days=3),
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

    # One in-progress and one recently completed so the board is not empty.
    extra_done = Occurrence(
        task_id=filter_task.id,
        due_date=today - timedelta(days=2),
        original_due_date=today - timedelta(days=2),
        status="done",
        assignee_id=admin.id,
        completed_at=__import__("datetime").datetime.utcnow(),
        weather_reason="indoor",
        notes="Seeded completion for board demo",
    )
    db.add(extra_done)
    db.commit()


def get_setting(db: Session, key: str, default: str = "") -> str:
    row = db.get(Setting, key)
    return row.value if row else default
