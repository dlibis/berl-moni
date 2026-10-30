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


@dataclass(frozen=True)
class Approval:
    request_numbers: tuple[str, ...]
    approved_date: date | None


def request_key(numbers) -> tuple[str, ...]:
    """The complete request set, independent of feed grouping and ordering."""
    return tuple(sorted({n.strip() for value in numbers for n in value.split(",") if n.strip()}))
