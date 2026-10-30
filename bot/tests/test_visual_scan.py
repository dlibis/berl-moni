import base64

import pytest

from bot.adapters.llm.visual_scan import ScanDocument, read_document
from bot.domain.errors import ExtractionError


class FakeModels:
    def __init__(self, data):
        self.data = data
        self.call = None
        self.calls = 0

    def with_structured_output(self, schema):
        assert schema is ScanDocument
        return self

    def invoke(self, messages):
        self.call = messages
        self.calls += 1
        return self.data


@pytest.fixture
def pdf_path(tmp_path):
    import pymupdf
    path = tmp_path / "letter.pdf"
    with pymupdf.open() as pdf:
        pdf.new_page()
        pdf.new_page()
        pdf.save(path)
    return path


def page(number, rows=(), history=(), text=""):
    return {"page_number": number, "text": text, "history_present": bool(history),
            "history": list(history), "budget_table_present": bool(rows), "rows": list(rows)}


def read(pdf_path, models):
    return read_document(str(pdf_path), model="test", provider="test", api_key="test", client=models)


def test_visual_document_sends_whole_pdf_once_and_keeps_repeated_codes(pdf_path):
    row = {"code": "470102", "name": "רזרבה", "expenditure": {"before": -3, "change": 3, "after": 0}}
    history = {"label": "עבר", "columns": ["שנה", "סכום"], "rows": [["2025", "100"]]}
    models = FakeModels({"pages": [page(1, [row], text="ראשון"), page(2, [row], [history], "שני")]})
    result = read(pdf_path, models)
    assert [r[0] for r in result.table.rows] == ["470102", "470102"]
    assert result.text == "ראשון\nשני"
    assert result.history[0][0] == "עבר"
    assert result.history[0][1].rows == (("2025", "100"),)
    assert models.calls == 1
    block = models.call[0].content[1]
    assert block["type"] == "file" and block["mime_type"] == "application/pdf"
    assert base64.b64decode(block["data"]) == pdf_path.read_bytes()


def test_visual_document_rejects_missing_values_and_bad_arithmetic(pdf_path):
    row = {"code": "045203", "name": "שם", "expenditure": {"before": 1, "change": 2, "after": None}}
    models = FakeModels({"pages": [page(1), page(2, [row])]})
    with pytest.raises(ExtractionError, match="Page 2:.*blank"):
        read(pdf_path, models)
    row["expenditure"]["after"] = 4
    with pytest.raises(ExtractionError, match="Page 2:.*arithmetic"):
        read(pdf_path, models)


def test_extractor_uses_visual_data_without_tesseract():
    from types import SimpleNamespace
    from bot.domain.extraction import Extractor
    from bot.domain.request_fields import ProgramUses, Use
    from bot.domain.table import Table

    class Doc:
        scanned = True
        path = "scan.pdf"

        @property
        def text(self):
            raise AssertionError("Tesseract must not run")

    letter = SimpleNamespace(doc=Doc(), source_sha256="hash", source_size=1,
                             decision_links=lambda: [], extract_letterhead=lambda: ["מדינת ישראל"])
    table = Table(("number", "name", "הוצאה from", "הוצאה to"), (("045203", "משרד", 1, 3),))
    visual = SimpleNamespace(text="עיקרי הפנייה: 045203: משרד מטרת השינוי: מימון\nתאריך הבקשה 01/01/2026",
                             table=table, history=[])
    extractor = Extractor({"045203"}, lambda _: ("לא", [ProgramUses(code="045203", uses=[Use(text="מימון")])], None),
                          lambda _: letter, visual_scan=lambda _: visual)
    result = extractor.extract("source")
    assert result.scanned and result.visual_scan and result.table == table
    assert result.to_json()["visual_scan"] is True


def test_visibly_blank_half_is_zero_but_unknown_is_rejected(pdf_path):
    row = {"code": "470102", "name": "רזרבה", "expenditure":
           {"before": -3, "change": 3, "after": None, "blank_after": True}}
    models = FakeModels({"pages": [page(1, [row]), page(2)]})
    result = read(pdf_path, models)
    assert result.table.rows[0][-1] == 0
    row["expenditure"]["blank_after"] = False
    with pytest.raises(ExtractionError, match="blank"):
        read(pdf_path, models)


def test_blank_change_is_zero_only_when_row_is_unchanged(pdf_path):
    row = {"code": "194101", "name": "שכר", "expenditure": {"before": 92868, "change": None, "after": 92868}}
    models = FakeModels({"pages": [page(1, [row]), page(2)]})
    assert read(pdf_path, models).table.rows[0][2:] == (92868, 92868)
    row["expenditure"]["after"] = 92000
    with pytest.raises(ExtractionError, match="blank"):
        read(pdf_path, models)


@pytest.mark.parametrize("numbers", [[1], [1, 1], [2, 1], [1, 2, 3]])
def test_all_pages_must_be_returned_once_in_order(pdf_path, numbers):
    models = FakeModels({"pages": [page(n) for n in numbers]})
    with pytest.raises(ExtractionError, match="omitted, duplicated, or reordered"):
        read(pdf_path, models)


@pytest.mark.parametrize("data,error", [
    ({}, "invalid scan document"),
    ({"pages": [page(1), page(2)]}, "No budget program rows"),
    ({"pages": [{**page(1), "rows": [{}]}, page(2)]}, "invalid scan document"),
    ({"pages": [{**page(1), "history_present": True}, page(2)]}, "detected history table"),
    ({"pages": [{**page(1), "budget_table_present": True}, page(2)]}, "detected budget table"),
    ({"pages": [page(1, history=[{"label": "", "columns": ["a"], "rows": [["x", "y"]]}]), page(2)]}, "incomplete history table"),
])
def test_invalid_document_and_history_fail_closed(pdf_path, data, error):
    with pytest.raises(ExtractionError, match=error):
        read(pdf_path, FakeModels(data))


def test_missing_key_does_not_call_model(pdf_path):
    models = FakeModels({})
    with pytest.raises(ExtractionError, match="API key"):
        read_document(str(pdf_path), model="test", provider="test", api_key="", client=models)
    assert models.calls == 0


def test_document_reader_uses_configured_model_and_provider(pdf_path, monkeypatch):
    row = {"code": "45203", "name": "שם", "expenditure": {"before": 1, "change": 2, "after": 3}}
    models = FakeModels({"pages": [page(1, [row]), page(2)]})
    settings = []

    def init(model, **kwargs):
        settings.append((model, kwargs))
        return models

    monkeypatch.setattr("langchain.chat_models.init_chat_model", init)
    result = read_document(str(pdf_path), model="configured-model", provider="configured-provider", api_key="test")
    assert settings == [("configured-model", {"model_provider": "configured-provider", "api_key": "test", "max_retries": 0})]
    assert models.calls == 1
    assert result.table.rows[0][0] == "045203"


