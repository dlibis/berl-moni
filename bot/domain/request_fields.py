"""RequestFields — the typed result of extracting a budget letter's summary fields.

The Extractor returns this model from its deterministic rules and one LLM call, so callers know
exactly what comes back. Attribute names are English (valid Python identifiers, nice
in code and IDEs); the Hebrew labels the summary PDF prints are kept as aliases.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# A program's heading in the narrative: 'NNNNNN:' (5-6 digits, not part of a longer number). Not
# anchored to a line start: a heading may share its line with the text before it. A dash heading
# ('206101 - ...', 21656) is not matched: in the narrative a dash also follows table rows.
PROGRAM_HEADING = r"(?<![\d.,])(\d{5,6})\s*:"


class Use(BaseModel):
    """One thing a program's money is for, as the model writes it from 'מטרת השינוי'."""
    text: str
    coalition: bool = False   # the letter says this use is funded by coalition money


class ProgramUses(BaseModel):
    """What one program's money in this request is for."""
    code: str
    uses: list[Use] = Field(default_factory=list)


class RequestFields(BaseModel):
    """A budget-transfer request letter's summary fields."""

    model_config = ConfigDict(populate_by_name=True)

    date: str = Field(default="", alias="תאריך")
    request_number: str = Field(default="", alias="מס' פנייה")
    program_number: str = Field(default="", alias="מס' תוכנית")
    total_amount: str = Field(default="", alias="סך הפנייה")   # thousands of ₪, as printed: '190,709'
    programs: list[ProgramUses] = Field(default_factory=list)
    decision_links: str = Field(default="", alias="קישורים להחלטות ממשלה")
    coalition_funds: str = Field(default="", alias="כספים קואליציוניים")   # כן / לא / אולי
    staffing_changes: str = Field(default="", alias="שינויים בכוח אדם")

    def uses(self, code: str) -> list[Use]:
        """What a program's money is for; [] when the letter does not say (e.g. a source)."""
        return next((p.uses for p in self.programs if p.code == code), [])
