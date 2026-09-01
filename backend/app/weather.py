"""Weather preference matching and bounded reschedule."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any


DEFAULT_WINDOW = 3


def day_is_favorable(day_wx: dict[str, Any] | None, prefs: dict[str, Any] | None) -> bool:
    if not prefs or not prefs.get("outdoor"):
        return True
    if not day_wx:
        return False
    precip = float(day_wx.get("precip_mm") or 0)
    temp = day_wx.get("temp_max_c")
    wind = float(day_wx.get("wind_kmh") or 0)
    max_precip = prefs.get("max_precip_mm")
    if prefs.get("require_dry"):
        threshold = 0.5 if max_precip is None else float(max_precip)
        if precip > threshold:
            return False
    elif max_precip is not None and precip > float(max_precip):
        return False
    if prefs.get("min_temp_c") is not None and temp is not None and float(temp) < float(prefs["min_temp_c"]):
        return False
    if prefs.get("max_temp_c") is not None and temp is not None and float(temp) > float(prefs["max_temp_c"]):
        return False
    if prefs.get("max_wind_kmh") is not None and wind > float(prefs["max_wind_kmh"]):
        return False
    return True


def choose_favorable_date(
    due: date,
    forecast: dict[date, dict[str, Any]],
    prefs: dict[str, Any] | None,
    window: int = DEFAULT_WINDOW,
) -> tuple[date, str]:
    """Keep due if favorable; otherwise pick the closest day in ±window.

    On a distance tie, prefer the earlier day (move backward).
    Indoor / empty prefs never move.
    """
    if not prefs or not prefs.get("outdoor"):
        return due, "indoor"
    due_wx = forecast.get(due)
    if day_is_favorable(due_wx, prefs):
        return due, "kept"
    candidates: list[tuple[int, int, date]] = []
    for delta in range(-window, window + 1):
        if delta == 0:
            continue
        d = due + timedelta(days=delta)
        wx = forecast.get(d)
        if day_is_favorable(wx, prefs):
            candidates.append((abs(delta), delta, d))
    if not candidates:
        return due, "no_favorable_in_window"
    candidates.sort(key=lambda item: (item[0], item[1]))
    return candidates[0][2], "moved"


def apply_reschedule(
    occurrences: list[dict[str, Any]],
    forecast: dict[date, dict[str, Any]],
    window: int = DEFAULT_WINDOW,
) -> list[dict[str, Any]]:
    """Return copies of occurrence dicts with due_date possibly shifted.

    Skips indoor tasks and already-completed work.
    """
    out: list[dict[str, Any]] = []
    for occ in occurrences:
        row = dict(occ)
        if row.get("status") == "done":
            row["weather_reason"] = row.get("weather_reason") or "completed"
            out.append(row)
            continue
        prefs = row.get("weather_prefs") or {}
        due = row["due_date"]
        if isinstance(due, str):
            due = date.fromisoformat(due)
        new_due, reason = choose_favorable_date(due, forecast, prefs, window=window)
        row["original_due_date"] = row.get("original_due_date") or due
        if isinstance(row["original_due_date"], str):
            row["original_due_date"] = date.fromisoformat(row["original_due_date"])
        row["due_date"] = new_due
        row["weather_adjusted"] = new_due != due
        row["weather_reason"] = reason
        out.append(row)
    return out
