"""The boundary between the parser's DataFrames and the domain's plain Table."""
from numbers import Real

import pandas as pd

from bot.domain.table import Table


def to_table(df: pd.DataFrame) -> Table:
    """`df` as a Table: NaN / NA become None, numbers Python floats, everything else str."""
    def cell(value):
        if pd.isna(value):
            return None
        return float(value) if isinstance(value, Real) and not isinstance(value, bool) else str(value)
    return Table(tuple(str(c) for c in df.columns), tuple(tuple(map(cell, row)) for row in df.itertuples(index=False)))
