"""ScansRepository: the `scans` table — one row per job run saying what happened (sent, nothing new,
failed and why) with counts only, never an address. The status screen reads it."""
from bot.domain.statuses import ScanReason, ScanStatus


class ScansRepository:
    def __init__(self, conn):
        self.conn = conn

    def add(self, day, status: ScanStatus, reason: ScanReason | None = None, letters_in_feed: int | None = None,
            new_letters: int = 0, relevant: int = 0, failed: int = 0, emails_sent: int = 0) -> None:
        self.conn.execute("INSERT INTO scans (day, status, reason, letters_in_feed, new_letters, relevant, failed, emails_sent) "
                          "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                          (day, status, reason, letters_in_feed, new_letters, relevant, failed, emails_sent))
