from datetime import date, datetime, timezone

from common.schedule_due import ISRAEL, due_day, fetch_due, resume_requested, schedule_configured

SCHEDULE = [{"from": "2026-10-01", "to": "2026-10-31", "days": {
    "wed": {"enabled": True, "time": "09:00"},
    "thu": {"enabled": True, "time": "23:00"},
    "fri": {"enabled": False, "time": "09:00"},
}}]

EVERY_DAY = [{"from": "2000-01-01", "to": "2999-12-31", "days": {
    key: {"enabled": True, "time": "09:00"} for key in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]}}]


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


def test_always_send_skips_custom_slots():
    assert due_day(at(2026, 10, 14, 12), SCHEDULE, FakeConn(), always_send=True) is None
    assert due_day(at(2026, 10, 14, 12), SCHEDULE, FakeConn(), always_send=False) == date(2026, 10, 14)


def test_resume_requested_needs_a_sending_row():
    assert resume_requested(FakeConn(row={"?column?": 1})) is True
    assert resume_requested(FakeConn()) is False


def test_occurrence_count_stops_auto_send(test_db_url):
    import psycopg
    from psycopg.rows import dict_row
    sched = [{**SCHEDULE[0], "count": 1, "from": "2026-10-01"}]
    with psycopg.connect(test_db_url, row_factory=dict_row) as conn:
        conn.execute("TRUNCATE send_runs RESTART IDENTITY CASCADE")
        conn.execute("TRUNCATE scans")
        assert due_day(at(2026, 10, 14, 12), sched, conn) == date(2026, 10, 14)
        conn.execute("INSERT INTO send_runs (day, status, kind, from_address, reply_to_address, batches) "
                     "VALUES ('2026-10-14', 'sent', 'auto', 'a@berl.site', 'r@x', '[]')")
        assert due_day(at(2026, 10, 14, 12), sched, conn) is None


def test_schedule_configured():
    assert not schedule_configured([]) and schedule_configured(EVERY_DAY)
    assert not schedule_configured([{**EVERY_DAY[0], "to": "2000-01-02"}])
    assert not schedule_configured([{**EVERY_DAY[0], "days": {"mon": {"enabled": False, "time": "09:00"}}}])


def test_fetch_due_every_hours():
    now = at(2026, 10, 14, 12)
    assert fetch_due(now, None, None) is False
    assert fetch_due(now, 2, None) is False
    assert fetch_due(now, 1, None) is True
    assert fetch_due(now, 1, at(2026, 10, 14, 11).isoformat()) is True
    assert fetch_due(now, 1, at(2026, 10, 14, 11, 30).isoformat()) is False
    assert fetch_due(now, 6, at(2026, 10, 14, 7).isoformat()) is False
    assert fetch_due(now, 6, at(2026, 10, 14, 6).isoformat()) is True
    assert fetch_due(now, 24, at(2026, 10, 13, 13).isoformat()) is False
    assert fetch_due(now, 24, at(2026, 10, 13, 12).isoformat()) is True


def test_main_due_when_only_fetch_cadence_is_due(test_db_url, monkeypatch, capsys):
    import psycopg
    from psycopg.rows import dict_row

    import common.schedule_due as sd
    from common.db import set_setting

    with psycopg.connect(test_db_url, row_factory=dict_row) as conn:
        conn.execute("DELETE FROM settings WHERE key IN ('schedule', 'always_send', 'fetch_every_hours', 'last_feed_refresh_at')")
        set_setting(conn, "schedule", [])
        set_setting(conn, "always_send", False)
        set_setting(conn, "fetch_every_hours", 1)
        conn.commit()
    monkeypatch.setenv("DATABASE_URL", test_db_url)
    frozen = at(2026, 10, 14, 12)

    class Frozen(datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen if tz is None else frozen.astimezone(tz)

    monkeypatch.setattr(sd, "datetime", Frozen)
    sd.main()
    assert "due=true" in capsys.readouterr().out


def test_manual_send_today_does_not_cancel_the_auto_send(test_db_url):
    import psycopg
    from psycopg.rows import dict_row
    with psycopg.connect(test_db_url, row_factory=dict_row) as conn:
        conn.execute("TRUNCATE send_runs RESTART IDENTITY CASCADE")
        conn.execute("TRUNCATE scans")
        conn.execute("INSERT INTO send_runs (day, status, kind, from_address, reply_to_address, batches) "
                     "VALUES ('2026-10-14', 'sent', 'manual', 'a@berl.site', 'r@x', '[]')")
        assert due_day(at(2026, 10, 14, 12), SCHEDULE, conn) == date(2026, 10, 14)
        conn.execute("INSERT INTO send_runs (day, status, kind, from_address, reply_to_address, batches) "
                     "VALUES ('2026-10-14', 'sent', 'auto', 'a@berl.site', 'r@x', '[]')")
        assert due_day(at(2026, 10, 14, 12), SCHEDULE, conn) is None
