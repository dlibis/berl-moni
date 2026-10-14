"""Resend sending limits (plan: Locked, Limits). One function for the route, the screen, and the job."""
import calendar
import math
from datetime import date

from common.schedule_due import day_time

CHUNK = 49  # bcc per message; +1 for the `to` address


def emails_per_run(count: int) -> int:
    """Emails for one attachment batch sent to `count` recipients."""
    return count + math.ceil(count / CHUNK)


def list_cap(daily_limit: int) -> int:
    """Largest n with n + ceil(n/49) <= daily_limit. Pass resend_daily_limit - resend_reserve."""
    n = max(daily_limit, 0)
    while n and emails_per_run(n) > daily_limit:
        n -= 1
    return n


def projected_monthly_emails(count: int, schedule: list, month: date) -> int:
    """Emails if `count` recipients get one batch on every scheduled send day of `month`'s month."""
    days = calendar.monthrange(month.year, month.month)[1]
    send_days = sum(day_time(schedule, date(month.year, month.month, d)) is not None
                    for d in range(1, days + 1))
    return send_days * emails_per_run(count)
