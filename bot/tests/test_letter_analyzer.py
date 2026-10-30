"""LlmAnalyzer's draft -> self-review flow, with the model replaced by a FunctionModel giving canned answers."""
from pydantic_ai import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from bot.adapters.llm.letter_analyzer import SYSTEM_PROMPT, LlmAnalyzer, _Analysis, _Program, _Review, _Use

DRAFT = _Analysis(coalition_funds="לא", programs=[
    _Program(code="230120", uses=[_Use(text="תפעול ואחזקת המשרד", coalition=False)])])
FIXED = _Analysis(coalition_funds="כן", programs=[
    _Program(code="230120", uses=[_Use(text="הפעלת המיזם לביטחון תזונתי", coalition=False),
                                  _Use(text="הרחבת מבחן התמיכה", coalition=True)])])


def canned(answers):
    """A model that answers each request with the next canned output, and keeps the messages it was sent."""
    answers, sent = list(answers), []

    def respond(messages, info):
        sent.append((list(messages), info.instructions))
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, answers.pop(0).model_dump())])

    return LlmAnalyzer(FunctionModel(respond)), sent


def test_review_replaces_a_wrong_draft_once():
    analyzer, sent = canned([DRAFT, _Review(ok=False, problems=["נלקח מתיאור התוכנית"], corrected=FIXED)])

    coalition, programs, usage = analyzer("טקסט המכתב")

    assert coalition == "כן"
    assert [u.text for u in programs[0].uses] == ["הפעלת המיזם לביטחון תזונתי", "הרחבת מבחן התמיכה"]
    assert usage["corrected"] and usage["review_problems"] == ["נלקח מתיאור התוכנית"]
    assert len(sent) == 2 and usage["calls"] == 2   # one draft, one review: never a second correction


def test_an_ok_review_keeps_the_draft():
    analyzer, _ = canned([DRAFT, _Review(ok=True)])

    coalition, programs, usage = analyzer("טקסט המכתב")

    assert coalition == "לא" and programs[0].uses[0].text == "תפעול ואחזקת המשרד"
    assert not usage["corrected"]


def test_review_starts_with_the_drafts_prompt_so_the_cache_can_serve_it():
    analyzer, sent = canned([DRAFT, _Review(ok=True)])
    analyzer("טקסט המכתב")
    (draft_messages, draft_instructions), (review_messages, review_instructions) = sent
    assert draft_instructions == review_instructions == SYSTEM_PROMPT.strip()
    assert review_messages[0].parts[0].content == draft_messages[0].parts[0].content == "טקסט המכתב"
