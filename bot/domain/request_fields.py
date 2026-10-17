"""RequestFields — the typed result of extracting a budget letter's summary fields.

The Extractor returns this model from its deterministic rules and one LLM call, so callers know
exactly what comes back. Attribute names are English (valid Python identifiers, nice
in code and IDEs); the Hebrew labels used by the reports and existing outputs are kept
as aliases. `model_dump(by_alias=True)` yields the Hebrew-keyed dict the reports expect.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RequestFields(BaseModel):
    """A budget-transfer request letter's summary fields."""

    model_config = ConfigDict(populate_by_name=True)

    date: str = Field(
        default="", alias="תאריך",
        description="תאריך הבקשה מדפי הטבלה, בפורמט DD/MM/YYYY. אם אינו מופיע, החזר מחרוזת ריקה.")
    request_number: str = Field(
        default="", alias="מס' פנייה",
        description=("רק מספרי הבקשה עצמם בפורמט NN-NNN בדיוק כפי שהם מופיעים בטקסט, "
                     "מופרדים בפסיק, ללא המילים 'בקשה מספר'. לאחר מכן הוסף 'מספר פנייה לועדה: X'."))
    program_number: str = Field(
        default="", alias="מס' תוכנית",
        description=("רק קודי התוכניות המופיעים ככותרת 'תכנית NNNNNN:' בתוך מקטע 'עיקרי הפנייה "
                     "בחלוקה לתוכניות'. אל תיקח קודים מטבלאות התקציב. אם יש כמה, החזר מופרדים בפסיק."))
    request_summary: str = Field(
        default="", alias="עיקרי הפנייה",
        description=("העתק מילה במילה את כל הנרטיב שאחרי הכותרת 'עיקרי הפנייה:' — הפסקה "
                     "הפותחת, כל בלוק 'NNNNNN: ... תיאור התוכנית: ...' וכל בלוק 'מטרת השינוי:'. "
                     "אל תסכם ואל תנסח מחדש."))
    decision_links: str = Field(
        default="", alias="קישורים להחלטות ממשלה",
        description="קישורים להחלטות ממשלה אם מופיעים בטקסט. אם אין, החזר מחרוזת ריקה.")
    coalition_funds: str = Field(
        default="", alias="האם יש התייחסות לכספים קואליציונים",
        description=("'כן' או 'לא' בלבד לפי ההצהרה המפורשת במכתב. "
                     "אם נכתב 'אינה כוללת כספים קואליציוניים' החזר 'לא'."))
    staffing_changes: str = Field(
        default="", alias="שינויים בכוח אדם",
        description="'כן' או 'לא' בלבד, לפי האם המכתב מציין שינויים בכוח אדם.")

    @classmethod
    def field_labels(cls) -> list[str]:
        """The Hebrew field labels, in declaration order (replaces the old REQUEST_FIELDS)."""
        return [info.alias for info in cls.model_fields.values()]
