"""LlmAnalyzer's draft -> self-review flow, with the model call replaced by canned answers."""
from bot.adapters.llm.letter_analyzer import LlmAnalyzer, _Analysis, _Program, _Review, _Use

DRAFT = _Analysis(coalition_funds="לא", programs=[
    _Program(code="230120", uses=[_Use(text="תפעול ואחזקת המשרד", coalition=False)])])
FIXED = _Analysis(coalition_funds="כן", programs=[
    _Program(code="230120", uses=[_Use(text="הפעלת המיזם לביטחון תזונתי", coalition=False),
                                  _Use(text="הרחבת מבחן התמיכה", coalition=True)])])


class CannedAnalyzer(LlmAnalyzer):
    """Answers each call from a list, and keeps the messages it was sent."""

    def __init__(self, answers):
        super().__init__(provider="google_genai")
        self.answers, self.sent = list(answers), []

    def _ask(self, schema, messages):
        self.sent.append(messages)
        return self.answers.pop(0), None


def test_review_replaces_a_wrong_draft_once():
    analyzer = CannedAnalyzer([DRAFT, _Review(ok=False, problems=["נלקח מתיאור התוכנית"], corrected=FIXED)])

    coalition, programs, usage = analyzer("טקסט המכתב")

    assert coalition == "כן"
    assert [u.text for u in programs[0].uses] == ["הפעלת המיזם לביטחון תזונתי", "הרחבת מבחן התמיכה"]
    assert usage["corrected"] and usage["review_problems"] == ["נלקח מתיאור התוכנית"]
    assert len(analyzer.sent) == 2   # one draft, one review: never a second correction


def test_an_ok_review_keeps_the_draft():
    analyzer = CannedAnalyzer([DRAFT, _Review(ok=True)])

    coalition, programs, usage = analyzer("טקסט המכתב")

    assert coalition == "לא" and programs[0].uses[0].text == "תפעול ואחזקת המשרד"
    assert not usage["corrected"]


def test_review_starts_with_the_drafts_prompt_so_the_cache_can_serve_it():
    analyzer = CannedAnalyzer([DRAFT, _Review(ok=True)])
    analyzer("טקסט המכתב")
    draft_call, review_call = analyzer.sent
    assert review_call[:len(draft_call)] == draft_call
