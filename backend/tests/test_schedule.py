from datetime import date

from app.schedule import next_due, following_due, SEASON_ANCHORS


def test_seasonal_fall_on_or_after():
    d = next_due(recurrence="seasonal", season="fall", month=None, day=None, from_date=date(2026, 1, 15))
    assert d == date(2026, *SEASON_ANCHORS["fall"])


def test_seasonal_wraps_year():
    d = next_due(recurrence="seasonal", season="spring", month=None, day=None, from_date=date(2026, 4, 1))
    assert d == date(2027, 3, 20)


def test_monthly_rolls_next_month():
    d = next_due(recurrence="monthly", season=None, month=None, day=1, from_date=date(2026, 9, 2))
    assert d == date(2026, 10, 1)


def test_following_due_after_completion():
    tmpl = {"recurrence": "monthly", "day": 1}
    nxt = following_due(tmpl, date(2026, 9, 1))
    assert nxt == date(2026, 10, 1)
