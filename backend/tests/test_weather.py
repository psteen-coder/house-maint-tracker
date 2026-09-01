from datetime import date, timedelta

from app.weather import apply_reschedule, choose_favorable_date, day_is_favorable


DRY = {"outdoor": True, "require_dry": True, "max_precip_mm": 0.8, "min_temp_c": 4}
INDOOR = {"outdoor": False}


def _wx(precip, temp=18, wind=10):
    return {"precip_mm": precip, "temp_max_c": temp, "wind_kmh": wind}


def test_indoor_always_favorable():
    assert day_is_favorable(_wx(20), INDOOR)
    assert day_is_favorable(None, INDOOR)


def test_dry_only_skips_rain():
    assert day_is_favorable(_wx(0.0), DRY)
    assert not day_is_favorable(_wx(5.0), DRY)


def test_reschedule_skips_rainy_due_and_picks_nearest():
    due = date(2026, 9, 10)
    forecast = {
        due - timedelta(days=1): _wx(0.0),
        due: _wx(12.0),
        due + timedelta(days=1): _wx(0.0),
        due + timedelta(days=2): _wx(0.0),
    }
    chosen, reason = choose_favorable_date(due, forecast, DRY, window=3)
    assert reason == "moved"
    assert chosen == due - timedelta(days=1)  # tie at 1 day: prefer earlier


def test_reschedule_stays_in_window():
    due = date(2026, 9, 10)
    forecast = {
        due: _wx(20),
        due + timedelta(days=4): _wx(0),
        due - timedelta(days=4): _wx(0),
    }
    chosen, reason = choose_favorable_date(due, forecast, DRY, window=3)
    assert chosen == due
    assert reason == "no_favorable_in_window"


def test_indoor_not_shifted():
    due = date(2026, 9, 10)
    rows = apply_reschedule(
        [{"id": 1, "due_date": due, "status": "todo", "weather_prefs": INDOOR}],
        {due: _wx(40)},
    )
    assert rows[0]["due_date"] == due
    assert rows[0]["weather_reason"] == "indoor"
    assert rows[0]["weather_adjusted"] is False


def test_kept_when_due_is_dry():
    due = date(2026, 9, 10)
    chosen, reason = choose_favorable_date(due, {due: _wx(0.1)}, DRY)
    assert chosen == due
    assert reason == "kept"
