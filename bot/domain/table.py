"""A plain table: column names and rows of str / float / None. The domain's tables (the budget table,
the budget history) are this, not DataFrames, so the domain and the web bundle stay free of pandas."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

Cell = str | float | None


@dataclass(frozen=True)
class Table:
    columns: tuple[str, ...]
    rows: tuple[tuple[Cell, ...], ...]

    @classmethod
    def from_records(cls, columns: Sequence[str], records: Iterable[Mapping]) -> Table:
        """A table of `columns` from dicts; a key a record lacks becomes None."""
        return cls(tuple(columns), tuple(tuple(r.get(c) for c in columns) for r in records))

    @property
    def empty(self) -> bool:
        return not self.rows

    def column(self, name: str) -> list:
        i = self.columns.index(name)
        return [row[i] for row in self.rows]

    def records(self) -> list[dict]:
        return [dict(zip(self.columns, row)) for row in self.rows]
