from datetime import date, datetime, timezone

from common.schedule_due import ISRAEL, due_day, resume_requested

SCHEDULE = [{"from": "2026-10-01", "to": "2026-10-31", "days": {
    "wed": {"enabled": True, "time": "09:00"},
    "thu": {"enabled": True, "time": "23:00"},
    "fri": {"enabled": False, "time": "09:00"},
}}]


class FakeConn:
    """Answers every query with `row` (None = no send_runs / scans row blocks the day)."""

    def __init__(self, row=None):
        self.row = row

    def execute(self, sql, params=None):
        return self

    def fetchone(self):
        return self.row


def at(y, m, d, hh, mm=0):
    return datetime(y, m, d, hh, mm, tzinfo=ISRAEL).astimezone(timezone.utc)


def test_missing_weekday_key_is_disabled():
    assert due_day(at(2026, 10, 12, 12), SCHEDULE, FakeConn()) is None  # Monday: no key
    assert due_day(at(2026, 10, 16, 12), SCHEDULE, FakeConn()) is None  # Friday: disabled


def test_exactly_on_the_hour():
    assert due_day(at(2026, 10, 14, 8, 59), SCHEDULE, FakeConn()) is None
    assert due_day(at(2026, 10, 14, 9), SCHEDULE, FakeConn()) == date(2026, 10, 14)
    assert due_day(at(2026, 10, 14, 23, 59), SCHEDULE, FakeConn()) == date(2026, 10, 14)


def test_23_00_until_israel_midnight():
    assert due_day(at(2026, 10, 15, 22, 59), SCHEDULE, FakeConn()) is None
    assert due_day(at(2026, 10, 15, 23), SCHEDULE, FakeConn()) == date(2026, 10, 15)
    assert due_day(at(2026, 10, 16, 0, 30), SCHEDULE, FakeConn()) is None  # next day is Friday


def test_outside_range_or_blocked_by_db():
    assert due_day(at(2026, 11, 4, 12), SCHEDULE, FakeConn()) is None
    assert due_day(at(2026, 10, 14, 12), SCHEDULE, FakeConn(row={"?column?": 1})) is None


def test_resume_requested_needs_a_sending_row():
    assert resume_requested(FakeConn(row={"?column?": 1})) is True
    assert resume_requested(FakeConn()) is False
