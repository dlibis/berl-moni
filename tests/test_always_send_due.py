from datetime import date, datetime, timezone

from common.always_send_due import ALWAYS_SEND_WEEKDAY, due_always_send
from common.schedule_due import ISRAEL
from tests.test_schedule_due import FakeConn


def at(y, m, d, hh, mm=0):
    return datetime(y, m, d, hh, mm, tzinfo=ISRAEL).astimezone(timezone.utc)


def test_disabled_is_never_due():
    sunday = date(2026, 10, 25)  # Sunday
    assert sunday.weekday() == ALWAYS_SEND_WEEKDAY
    assert due_always_send(at(2026, 10, 25, 10), False, FakeConn()) is None


def test_sunday_after_nine_when_enabled():
    assert due_always_send(at(2026, 10, 25, 8, 59), True, FakeConn()) is None
    assert due_always_send(at(2026, 10, 25, 9), True, FakeConn()) == date(2026, 10, 25)


def test_monday_not_due():
    assert due_always_send(at(2026, 10, 26, 12), True, FakeConn()) is None
