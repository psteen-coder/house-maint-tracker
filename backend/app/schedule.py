"""Seasonal / calendar recurrence helpers."""

from __future__ import annotations

from datetime import date
from calendar import monthrange

SEASON_ANCHORS = {
    "spring": (3, 20),
    "summer": (6, 21),
    "fall": (9, 22),
    "winter": (12, 21),
}


def _clamp_day(year: int, month: int, day: int) -> date:
    last = monthrange(year, month)[1]
    return date(year, month, min(day, last))


def next_due(
    *,
    recurrence: str,
    season: str | None,
    month: int | None,
    day: int | None,
    from_date: date,
) -> date:
    """First due date on or after from_date for the given schedule."""
    rec = (recurrence or "once").lower()
    if rec == "seasonal":
        key = (season or "spring").lower()
        m, d = SEASON_ANCHORS.get(key, SEASON_ANCHORS["spring"])
        candidate = date(from_date.year, m, d)
        if candidate < from_date:
            candidate = date(from_date.year + 1, m, d)
        return candidate
    if rec == "monthly":
        d = day or 1
        candidate = _clamp_day(from_date.year, from_date.month, d)
        if candidate < from_date:
            y, m = from_date.year, from_date.month + 1
            if m > 12:
                y, m = y + 1, 1
            candidate = _clamp_day(y, m, d)
        return candidate
    if rec == "quarterly":
        d = day or 1
        months = [1, 4, 7, 10]
        for y in (from_date.year, from_date.year + 1):
            for m in months:
                candidate = _clamp_day(y, m, d)
                if candidate >= from_date:
                    return candidate
        return _clamp_day(from_date.year + 1, 1, d)
    if rec == "yearly":
        m = month or (SEASON_ANCHORS.get((season or "spring").lower(), (1, 1))[0])
        d = day or 1
        candidate = _clamp_day(from_date.year, m, d)
        if candidate < from_date:
            candidate = _clamp_day(from_date.year + 1, m, d)
        return candidate
    # once
    m = month or from_date.month
    d = day or from_date.day
    candidate = _clamp_day(from_date.year, m, d)
    if candidate < from_date:
        candidate = _clamp_day(from_date.year + 1, m, d)
    return candidate


def following_due(template: dict, after: date) -> date:
    """Due date strictly after `after` (used when rolling a completed occurrence)."""
    from datetime import timedelta

    return next_due(
        recurrence=template.get("recurrence") or "once",
        season=template.get("season"),
        month=template.get("month"),
        day=template.get("day"),
        from_date=after + timedelta(days=1),
    )
