from io import BytesIO

import pytest
from flask import Flask
from openpyxl import Workbook

from tests.test_letters_api import SessionResponse
from web.csrf import register_csrf
from web.master_xlsx import SHEET, CODE_COL, NAME_COL, programs_to_xlsx, xlsx_to_programs
from web.routes.master import master_bp


def _sample_xlsx(rows: list[tuple[str, str]]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = SHEET
    ws.append([CODE_COL, NAME_COL])
    for code, name in rows:
        ws.append([code, name])
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_round_trip_and_normalize():
    data = _sample_xlsx([("42", "foo"), ("200102", "bar")])
    programs = xlsx_to_programs(data)
    assert programs == [("000042", "foo"), ("200102", "bar")]
    out = programs_to_xlsx([{"code": c, "name": n} for c, n in programs])
    assert xlsx_to_programs(out) == programs


def test_invalid_file_raises():
    with pytest.raises(ValueError):
        xlsx_to_programs(b"not xlsx")


@pytest.fixture
def master_client(test_db_url, monkeypatch):
    import psycopg
    from psycopg.rows import dict_row

    monkeypatch.setenv("SITE_ORIGIN", "https://berl.site")
    monkeypatch.setenv("NEON_AUTH_BASE_URL", "https://auth.example")
    monkeypatch.setattr("web.auth.requests.get", lambda *args, **kwargs: SessionResponse())
    monkeypatch.setattr(
        "web.routes.master.connect",
        lambda: psycopg.connect(test_db_url, row_factory=dict_row),
    )
    app = Flask(__name__)
    register_csrf(app)
    app.register_blueprint(master_bp)
    return app.test_client()


def test_upload_download_api(master_client, test_db_url):
    import psycopg
    from psycopg.rows import dict_row

    headers = {"Origin": "https://berl.site"}
    data = _sample_xlsx([("100001", "א"), ("100002", "ב")])
    bad = master_client.post(
        "/api/v1/master/upload",
        data={"file": (BytesIO(b"x"), "bad.xlsx")},
        headers=headers,
        content_type="multipart/form-data",
    )
    assert bad.status_code == 400
    ok = master_client.post(
        "/api/v1/master/upload",
        data={"file": (BytesIO(data), "master.xlsx")},
        headers=headers,
        content_type="multipart/form-data",
    )
    assert ok.status_code == 200
    with psycopg.connect(test_db_url, row_factory=dict_row) as conn:
        rows = list(conn.execute("SELECT code, name FROM programs ORDER BY code"))
    assert rows == [{"code": "100001", "name": "א"}, {"code": "100002", "name": "ב"}]
    down = master_client.get("/api/v1/master/download", headers=headers)
    assert down.status_code == 200
    assert xlsx_to_programs(down.data) == [("100001", "א"), ("100002", "ב")]
