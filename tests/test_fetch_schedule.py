from datetime import datetime, timedelta, timezone

import pytest

from common.schedule_due import (
    ISRAEL, DAY_KEYS, legacy_fetch_schedule, read_fetch_schedule,
    scheduled_fetch_due, valid_fetch_schedule,
)


def at(day=14, hour=9, month=10):
    return datetime(2026, month, day, hour, tzinfo=ISRAEL).astimezone(timezone.utc)


def test_legacy_and_explicit_off():
    settings = {"fetch_every_hours": 6}
    assert read_fetch_schedule(settings.get) == legacy_fetch_schedule(6)
    settings["fetch_schedule"] = None
    assert read_fetch_schedule(settings.get) is None


@pytest.mark.parametrize("config", [
    {}, {"days": [], "mode": "interval", "interval_hours": 1},
    {"days": ["bad"], "mode": "interval", "interval_hours": 1},
    {"days": ["wed", "wed"], "mode": "interval", "interval_hours": 1},
    *[{"days": ["wed"], "mode": "interval", "interval_hours": n} for n in [True, 0, 25, 1.5, "2"]],
    *[{"days": ["wed"], "mode": "specific", "time": t} for t in ["09:30", "24:00", "9:00", 9]],
    {"days": ["wed"], "mode": "specific", "time": "09:00", "extra": 1},
])
def test_invalid_config(config):
    assert not valid_fetch_schedule(config)


def test_interval_day_gating_and_boundary():
    config = {"days": ["wed"], "mode": "interval", "interval_hours": 2}
    now = at()
    assert scheduled_fetch_due(now, config, None)
    assert not scheduled_fetch_due(now, config, (now - timedelta(hours=1, minutes=59)).isoformat())
    assert scheduled_fetch_due(now, config, (now - timedelta(hours=2)).isoformat())
    assert not scheduled_fetch_due(at(day=15), config, None)
    assert not scheduled_fetch_due(now, None, None)


def test_specific_retry_success_and_midnight():
    config = {"days": DAY_KEYS, "mode": "specific", "time": "09:00"}
    assert not scheduled_fetch_due(at(hour=8), config, None)
    assert scheduled_fetch_due(at(), config, None)
    assert scheduled_fetch_due(at(hour=23), config, None)  # failure leaves timestamp unchanged
    assert scheduled_fetch_due(at(), config, at(hour=8).isoformat())
    assert not scheduled_fetch_due(at(hour=23), config, at().isoformat())
    assert not scheduled_fetch_due(at(day=15, hour=0), config, None)
    assert scheduled_fetch_due(at(day=15), config, at().isoformat())


@pytest.mark.parametrize("month,day", [(3, 26), (3, 27), (10, 24), (10, 25)])
def test_specific_uses_israel_clock_across_dst(month, day):
    config = {"days": DAY_KEYS, "mode": "specific", "time": "09:00"}
    assert not scheduled_fetch_due(at(day, 8, month), config, None)
    assert scheduled_fetch_due(at(day, 9, month), config, None)
