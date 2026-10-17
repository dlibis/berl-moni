"""LLM letter analyzer: LlmAnalyzer makes the one model call per letter — the coalition-funds judgment
and the request text, verbatim.

The Extractor depends on a plain callable `analyze(region) -> (coalition, request_summary, usage)`
(Cosmic Python ch. 3), so tests pass a lambda instead.

    analyze = LlmAnalyzer(model="gpt-4o", provider="openai", api_key="sk-...")
    coalition, summary, usage = analyze(region)
"""
from __future__ import annotations

from pydantic import BaseModel, Field

DEFAULT_MODELS = {
    "openai": "gpt-4o",
    "google_genai": "gemini-3.6-flash",
}
DEFAULT_MODEL = DEFAULT_MODELS["openai"]

SYSTEM_PROMPT = (
    "לפניך הטקסט הנרטיבי של פנייה תקציבית (מהכותרת 'עיקרי הפנייה'). בצע שתי משימות:\n"
    "1) coalition_funds: קבע 'כן' אם הפנייה עושה שימוש בפועל בכספים קואליציוניים, "
    "או מבקשת מהוועדה להמשיך ולעקוב אחריהם; אחרת 'לא'. רק אזכור של קואליציה, או "
    "'אינה כוללת כספים קואליציוניים', הם 'לא'. המשפט הכללי 'האם יש התייחסות לכספים "
    "קואליציונים' לבדו אינו מספיק.\n"
    "2) request_summary: החזר את הנרטיב של הפנייה כטקסט עברי רציף ונקי — פסקת הפתיחה, "
    "ולכל תכנית את שורת 'NNNNNN: <שם> – <סכום>', 'תיאור התוכנית' ו'מטרת השינוי'. "
    "העתק את הניסוח בנאמנות; אל תמציא, אל תקצר ואל תנסח מחדש. אל תכלול טבלאות ורשימות "
    "מספרים (למשל טבלת סיכום קואליציונית המסתיימת ב'סה\"כ'), את מקטע הקישורים ואת החתימה."
)


class _Analysis(BaseModel):
    """The one LLM call's output: the coalition judgment + the whole request text verbatim."""
    coalition_funds: str = Field(
        description="'כן' if the letter actually USES/allocates coalition funds, or asks "
                    "the committee to keep monitoring them going forward; else 'לא'. "
                    "Merely mentioning coalition is not enough.")
    request_summary: str = Field(
        description="Return the COMPLETE request text VERBATIM — this is NOT a summary. "
                    "Include the opening paragraph and, for EACH program, its "
                    "'NNNNNN: <שם> – <סכום>' line with its full 'תיאור התוכנית' and "
                    "'מטרת השינוי'. Copy every word exactly; do NOT summarize, shorten, "
                    "rephrase or omit any narrative sentence. The ONLY things to leave out "
                    "are non-prose artifacts: tables / number lists (e.g. the coalition "
                    "totals table ending in 'סה\"כ'), the links section, and the sign-off.")


class LlmAnalyzer:
    """Coalition judgment + the full request text in one structured-output call — NO fallback:
    if the model is unavailable the error surfaces, it is not masked by a deterministic answer."""

    def __init__(self, *, model=None, provider=None, api_key=None):
        self.provider = provider
        self.api_key = api_key
        self.model = model or DEFAULT_MODELS.get(provider or "openai", DEFAULT_MODEL)

    def __call__(self, region: str) -> tuple[str, str, dict]:
        from langchain.chat_models import init_chat_model

        params: dict = {"temperature": 0, "max_retries": 3}
        if self.api_key:
            params["api_key"] = self.api_key
        if self.provider:
            params["model_provider"] = self.provider
        llm = init_chat_model(self.model, **params).with_structured_output(
            _Analysis, include_raw=True)
        result = llm.invoke([("system", SYSTEM_PROMPT), ("user", region)])
        parsed = result["parsed"]
        coalition = "כן" if "כן" in (parsed.coalition_funds or "").strip() else "לא"
        return coalition, (parsed.request_summary or "").strip(), self._usage(result.get("raw"))

    def _usage(self, raw) -> dict:
        """The model and its token counts, from the raw AIMessage (logged by the job, not printed)."""
        meta = getattr(raw, "usage_metadata", None) or {}
        return {"model": self.model, "input_tokens": meta.get("input_tokens", 0),
                "output_tokens": meta.get("output_tokens", 0)}
