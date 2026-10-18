from bot.domain.table import Table
from bot.domain import money_flow

T = Table.from_records(["number", "name", "net from", "net to"], [
    {"number": "200101", "name": "a", "net from": 100.0, "net to": 40.0},
    {"number": "200102", "name": "b", "net from": 0.0, "net to": 60.0},
    {"number": "200102", "name": "b", "net from": None, "net to": None},
])


def test_table_columns_and_records():
    assert T.column("number") == ["200101", "200102", "200102"]
    assert T.records()[0]["name"] == "a" and not T.empty and Table((), ()).empty


def test_transfer_summary_without_pandas():
    sources, destinations, metric = money_flow.transfer_summary(T)
    assert metric == "net"
    assert sources == [("200101", "a", 60.0)] and destinations == [("200102", "b", 60.0)]


def test_domain_has_no_pandas():
    import bot.domain.extraction, bot.domain.money_flow
    assert "pd" not in vars(bot.domain.extraction) and "pd" not in vars(bot.domain.money_flow)
