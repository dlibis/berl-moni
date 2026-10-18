"""A pending letter as the Knesset feed describes it; rows sharing one PDF are one letter."""
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class FeedLetter:
    url: str
    letter_date: date | None
    ministry: str
    request_numbers: tuple[str, ...]
    rows: tuple[dict, ...]
