from datetime import date

from common.limits import emails_per_run, list_cap, projected_monthly_emails


def test_list_cap():
    assert list_cap(95) == 93
    assert list_cap(995) == 975
    for limit in (0, 1, 50, 95, 995):
        n = list_cap(limit)
        assert emails_per_run(n) <= limit < emails_per_run(n + 1)


def test_projected_monthly_emails():
    schedule = [{"from": "2026-10-01", "to": "2026-10-31", "days": {"wed": {"enabled": True, "time": "09:00"}}}]
    assert projected_monthly_emails(93, schedule, date(2026, 10, 1)) == 4 * 95  # 4 Wednesdays
    assert projected_monthly_emails(93, schedule, date(2026, 11, 1)) == 0
