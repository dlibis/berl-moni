import base64

import pytest

from bot.adapters.llm.visual_scan import read_page
from bot.domain.errors import ExtractionError


class FakeModels:
    def __init__(self, data):
        self.data = data
        self.call = None

    def with_structured_output(self, schema):
        return self

    def invoke(self, messages):
        self.call = messages
        return self.data


def test_visual_page_uses_image_and_keeps_repeated_codes():
    row = {"code": "470102", "name": "רזרבה", "expenditure": {"before": -3, "change": 3, "after": 0}}
    models = FakeModels({"text": "", "history_present": False, "history": [], "budget_table_present": True, "rows": [row, row]})
    result = read_page(b"png-test", model="test", provider="test", api_key="test", client=models)
    assert [r.code for r in result.rows] == ["470102", "470102"]
    assert base64.b64decode(models.call[0].content[1]["image_url"]["url"].split(",", 1)[1]) == b"png-test"


def test_visual_page_rejects_missing_values_and_bad_arithmetic():
    row = {"code": "045203", "name": "שם", "expenditure": {"before": 1, "change": 2, "after": None}}
    models = FakeModels({"text": "", "history_present": False, "history": [], "budget_table_present": True, "rows": [row]})
    with pytest.raises(ExtractionError, match="blank"):
        read_page(b"png", model="test", provider="test", api_key="test", client=models)
    row["expenditure"]["after"] = 4
    with pytest.raises(ExtractionError, match="arithmetic"):
        read_page(b"png", model="test", provider="test", api_key="test", client=models)


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


def test_visibly_blank_half_is_zero_but_unknown_is_rejected():
    row = {"code": "470102", "name": "רזרבה", "expenditure":
           {"before": -3, "change": 3, "after": None, "blank_after": True}}
    models = FakeModels({"text": "", "history_present": False, "history": [],
                         "budget_table_present": True, "rows": [row]})
    page = read_page(b"png", model="test", provider="test", api_key="test", client=models)
    assert page.rows[0].expenditure.after == 0
    row["expenditure"]["blank_after"] = False
    with pytest.raises(ExtractionError, match="blank"):
        read_page(b"png", model="test", provider="test", api_key="test", client=models)


