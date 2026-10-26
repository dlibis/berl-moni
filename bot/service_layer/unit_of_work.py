"""Unit of Work (Cosmic Python ch. 6): one Postgres connection, and the only place that commits.

    with UnitOfWork() as uow:
        uow.letters.upsert_feed(letters, auto=False)
        uow.commit()            # anything not committed is rolled back on exit

The services see one repository per table (uow.letters, .send_runs, .email_log, .scans) and a few
reads of settings; never a connection.
"""
from bot.adapters.postgres.email_log import EmailLogRepository
from bot.adapters.postgres.letters import LettersRepository
from bot.adapters.postgres.scans import ScansRepository
from bot.adapters.postgres.send_runs import SendRunsRepository
from common.db import connect, get_setting, list_emails, load_programs, set_setting
from common.always_send_due import due_always_send
from common.schedule_due import due_day


class UnitOfWork:
    def __init__(self, url: str | None = None):
        self.url = url  # None -> DATABASE_URL

    def __enter__(self) -> "UnitOfWork":
        self.conn = connect(self.url)
        self.letters = LettersRepository(self.conn)
        self.send_runs = SendRunsRepository(self.conn)
        self.email_log = EmailLogRepository(self.conn)
        self.scans = ScansRepository(self.conn)
        return self

    def __exit__(self, *exc) -> None:
        self.conn.rollback()
        self.conn.close()

    def commit(self) -> None:
        self.conn.commit()

    def rollback(self) -> None:
        self.conn.rollback()

    def setting(self, key: str, default=None):
        return get_setting(self.conn, key, default)

    def set_setting(self, key: str, value) -> None:
        set_setting(self.conn, key, value)

    def db_now(self) -> str:
        """Postgres' clock (ISO): what first_seen_at is stamped with, so comparisons with it are exact."""
        return self.conn.execute("SELECT now() AS now").fetchone()["now"].isoformat()

    def mailing_list(self) -> list[str]:
        return list_emails(self.conn)

    def programs(self) -> dict[str, str]:
        return load_programs(self.conn)

    def due_day(self, now_utc):
        """Today's Israel date if custom schedule or Always Send says a send is due now."""
        day = due_day(now_utc, self.setting("schedule", []), self.conn)
        if day is not None:
            return day
        return due_always_send(now_utc, bool(self.setting("always_send", False)), self.conn)
