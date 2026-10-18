"""LLM letter analyzer: LlmAnalyzer judges coalition funds and says, per program, what the request's
money is for — a draft, then one self-review that may correct it once (at most two model calls).

The Extractor depends on a plain callable `analyze(region) -> (coalition, programs, usage)`
(Cosmic Python ch. 3), so tests pass a lambda instead.

    analyze = LlmAnalyzer(model="gpt-4o", provider="openai", api_key="sk-...")
    coalition, programs, usage = analyze(region)
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from bot.domain.request_fields import ProgramUses, Use

DEFAULT_MODELS = {
    "openai": "gpt-4o",
    "google_genai": "gemini-3.6-flash",
}
DEFAULT_MODEL = DEFAULT_MODELS["openai"]

# The report's reader wants, at a glance, what this request's money is for. Two lessons from real
# letters shape the rules: 'תיאור התוכנית' is the budget line's standing description and often has
# nothing to do with this request (central office services funding a food-security project), and
# decision numbers mean nothing to a reader while their topics do.
SYSTEM_PROMPT = """\
לפניך הטקסט הנרטיבי של פנייה להעברה תקציבית (מהכותרת 'עיקרי הפנייה'). הקורא של הדוח רוצה להבין \
במבט אחד למה מיועד הכסף. בצע שתי משימות.

1) coalition_funds — אחד מ: 'כן', 'לא', 'אולי'.
- 'כן': הפנייה מקצה או מעבירה בפועל כספים קואליציוניים (למשל 'הקצאת תקציב קואליציוני', \
'יישום הסכמים קואליציוניים/פוליטיים'), או מבקשת מהוועדה להמשיך לעקוב אחריהם.
- 'אולי': כספים קואליציוניים מוזכרים, אך לא ברור אם הפנייה הזו מקצה אותם.
- 'לא': אין אזכור, או נכתב במפורש שהפנייה אינה כוללת כספים קואליציוניים. השאלה הכללית \
'האם יש התייחסות לכספים קואליציונים' לבדה אינה אזכור.

2) programs — רשומה אחת לכל תכנית שמופיעה בכותרת 'NNNNNN: <שם> – <סכום>' (או 'NNNNNN - <שם>'), \
לפי סדר הופעתן. \
אל תוסיף תכניות שאין להן כותרת כזו (למשל מקטע 'יישום הסכמים פוליטיים').
- code: שש הספרות מהכותרת.
- uses: למה מיועד הכסף של התכנית בפנייה הזו — רשומה אחת לכל שימוש נפרד.

כללים ל-uses:
- קח רק מ'מטרת השינוי'. לעולם אל תשתמש ב'תיאור התוכנית': זה תיאור כללי של סעיף התקציב, \
ולעתים קרובות הוא כלל לא קשור לכסף בפנייה.
- שימוש נפרד לכל מטרה: פצל במקומות כמו 'והקצאת', 'בנוסף', 'וכן'.
- כל שימוש הוא ביטוי קצר בסגנון כותרת, עד 15 מילים, במונחי המכתב. השמט פתיחים כמו \
'הקצאת תקציב ל', 'תקצוב', 'הסטת תקציב למימון'.
- החלטות ממשלה: כתוב את נושא ההחלטה ב-2 עד 4 מילים (למשל 'הבדואים בנגב', 'שיקום אשקלון'), \
בלי מספר, בלי תאריך ובלי שמה המלא. החלטה אחת: הוסף \
'(החלטת ממשלה)'. כמה החלטות לאותה מטרה: '<המטרה> ליישום N החלטות ממשלה: <נושא> · <נושא> · ...'.
- coalition: true רק אם המכתב אומר שהשימוש הזה ממומן מתקציב קואליציוני. אל תכתוב את המילה \
'קואליציוני' בתוך text.
- אל תוסיף מידע, אל תפרש ואל תעריך סכומים.

דוגמה (מכתב מומצא):
'240310: שירותי מטה – 5,000 אלפי ש"ח. תיאור התוכנית: תכנית זו משמשת למימון שכר דירה, רכב ותחזוקה. \
מטרת השינוי: הקצאת תקציב להפעלת קו סיוע לנפגעות אלימות, ויישום החלטת ממשלה מספר 1234 מיום \
01.01.2024 בנושא תוכנית לאומית למניעת אלימות במשפחה, והקצאת תקציב קואליציוני להרחבת מלגות \
לסטודנטים במקצועות הטיפול.'
uses:
- {"text": "הפעלת קו סיוע לנפגעות אלימות", "coalition": false}
- {"text": "תוכנית לאומית למניעת אלימות במשפחה (החלטת ממשלה)", "coalition": false}
- {"text": "הרחבת מלגות לסטודנטים במקצועות הטיפול", "coalition": true}
(שכר דירה, רכב ותחזוקה מופיעים רק בתיאור התוכנית — ולכן אינם שימוש.)
"""

# Sent after the draft, in the same conversation: the system prompt and the letter come first in both
# calls, so the review re-reads them from Gemini's implicit cache instead of paying for them again.
REVIEW_PROMPT = """בדוק את התשובה שלך מול הטקסט ומול הכללים, תכנית אחר תכנית:
1. כל תכנית שיש לה כותרת 'NNNNNN:' מופיעה בדיוק פעם אחת, ואין תכניות שאין להן כותרת.
2. כל שימוש לקוח מ'מטרת השינוי' של אותה תכנית — לא מ'תיאור התוכנית' ולא מתכנית אחרת.
3. כל מטרה שב'מטרת השינוי' מכוסה, ואין שתי מטרות שהתמזגו לשימוש אחד.
4. אין מספרי החלטות ואין תאריכים; כל החלטה מופיעה לפי הנושא שלה, ב-2 עד 4 מילים.
5. כל שימוש קצר (עד 15 מילים, לא כולל רשימת נושאי ההחלטות) ובסגנון כותרת.
6. coalition: true רק כשהמכתב אומר שהשימוש ממומן מתקציב קואליציוני; coalition_funds תואם לכלל המכתב.
7. אין מידע שאינו בטקסט.
אם הכול תקין: ok=true, problems ריק, ובלי corrected.
אחרת: ok=false, problems — משפט קצר לכל בעיה, ו-corrected — התשובה המלאה המתוקנת (כל התכניות).
"""


class _Use(BaseModel):
    text: str = Field(description="One use of the money, from 'מטרת השינוי' only: a short Hebrew "
                                  "headline, up to 15 words; decisions named by topic, not number.")
    coalition: bool = Field(description="True only if the letter says this use is coalition-funded.")


class _Program(BaseModel):
    code: str = Field(description="The 6-digit program code from its 'NNNNNN:' heading.")
    uses: list[_Use]


class _Analysis(BaseModel):
    """The one LLM call's output: the coalition judgment + what each program's money is for."""
    coalition_funds: str = Field(description="'כן', 'לא' or 'אולי'.")
    programs: list[_Program]


class _Review(BaseModel):
    """The self-review: whether the draft follows the rules, and if not, the corrected answer."""
    ok: bool
    problems: list[str] = Field(default_factory=list, description="One short Hebrew sentence per problem.")
    corrected: _Analysis | None = Field(default=None, description="The full corrected answer when ok is false.")


class LlmAnalyzer:
    """Coalition judgment + each program's uses: a draft, then one self-review that may replace it —
    never a second correction. NO fallback: if the model is unavailable the error surfaces, it is
    not masked by a deterministic answer."""

    def __init__(self, *, model=None, provider=None, api_key=None):
        self.provider = provider
        self.api_key = api_key
        self.model = model or DEFAULT_MODELS.get(provider or "openai", DEFAULT_MODEL)

    def __call__(self, region: str) -> tuple[str, list[ProgramUses], dict]:
        conversation = [("system", SYSTEM_PROMPT), ("user", region)]
        draft, draft_raw = self._ask(_Analysis, conversation)
        review, review_raw = self._ask(_Review, conversation + [
            ("ai", draft.model_dump_json()), ("user", REVIEW_PROMPT)])
        final = draft if review.ok or review.corrected is None else review.corrected
        usage = self._usage(draft_raw, review_raw)
        usage |= {"review_ok": review.ok, "review_problems": review.problems, "corrected": final is not draft}
        return self._coalition(final.coalition_funds), self._programs(final), usage

    def _ask(self, schema: type[BaseModel], messages: list) -> tuple[BaseModel, object]:
        """One structured-output model call: (the parsed answer, the raw AIMessage)."""
        from langchain.chat_models import init_chat_model

        params: dict = {"temperature": 0, "max_retries": 3}
        if self.api_key:
            params["api_key"] = self.api_key
        if self.provider:
            params["model_provider"] = self.provider
        llm = init_chat_model(self.model, **params).with_structured_output(schema, include_raw=True)
        result = llm.invoke(messages)
        return result["parsed"], result.get("raw")

    @staticmethod
    def _coalition(answer: str | None) -> str:
        return next((v for v in ("כן", "אולי") if v in (answer or "")), "לא")

    @staticmethod
    def _programs(analysis: _Analysis) -> list[ProgramUses]:
        return [ProgramUses(code=p.code.strip(),
                            uses=[Use(text=u.text.strip(), coalition=u.coalition) for u in p.uses if u.text.strip()])
                for p in analysis.programs]

    def _usage(self, *raws) -> dict:
        """The model and its token counts over all calls, from the raw AIMessages (logged by the job,
        not printed). `cached_tokens` are input tokens served from the provider's prompt cache."""
        metas = [getattr(raw, "usage_metadata", None) or {} for raw in raws]
        return {"model": self.model, "calls": len(raws),
                "input_tokens": sum(m.get("input_tokens", 0) for m in metas),
                "output_tokens": sum(m.get("output_tokens", 0) for m in metas),
                "cached_tokens": sum((m.get("input_token_details") or {}).get("cache_read", 0) for m in metas)}
