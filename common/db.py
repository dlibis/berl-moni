"""Neon access shared by web, check, and send. No pandas. Route-specific SQL lives in the routes."""
import os

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


def connect(url: str | None = None) -> psycopg.Connection:
    """Connection to DATABASE_URL (or `url`), rows as dicts. Use as `with connect() as conn:`."""
    return psycopg.connect(url or os.environ["DATABASE_URL"], row_factory=dict_row)


def load_programs(conn=None) -> dict[str, str]:
    """{six-digit code: program name}. Writes nothing."""
    if conn is None:
        with connect() as conn:
            return load_programs(conn)
    return {r["code"]: r["name"] for r in conn.execute("SELECT code, name FROM programs ORDER BY code")}


def get_setting(conn, key: str, default=None):
    row = conn.execute("SELECT value FROM settings WHERE key = %s", (key,)).fetchone()
    return default if row is None else row["value"]


def set_setting(conn, key: str, value) -> None:
    conn.execute("INSERT INTO settings (key, value) VALUES (%s, %s) "
                 "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (key, Jsonb(value)))


def list_subscribers(conn) -> list[dict]:
    return list(conn.execute("SELECT email, name FROM mailing_list ORDER BY email"))


def list_emails(conn) -> list[str]:
    return [r["email"] for r in conn.execute("SELECT email FROM mailing_list ORDER BY email")]


def add_subscriber(conn, email: str, name: str) -> None:
    """Insert one subscriber. Raises UniqueViolation on duplicates."""
    conn.execute("INSERT INTO mailing_list (email, name) VALUES (%s, %s)", (email, name))


def update_subscriber_name(conn, email: str, name: str) -> bool:
    """True if the address was on the list."""
    return conn.execute(
        "UPDATE mailing_list SET name = %s WHERE email = %s", (name, email)
    ).rowcount > 0


def remove_email(conn, email: str) -> bool:
    """True if the address was on the list."""
    return conn.execute("DELETE FROM mailing_list WHERE email = %s", (email,)).rowcount > 0
