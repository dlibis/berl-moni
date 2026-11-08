import logging

import pytest
from pydantic_ai import Agent, ModelResponse, TextPart, ToolCallPart, UnexpectedModelBehavior
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RequestUsage

from bot.adapters.llm.diagnostics import model_diagnostics


@pytest.mark.parametrize("finish_reason", ["stop", "length"])
def test_response_usage_is_logged_even_when_generation_hits_limit(caplog, finish_reason):
    def respond(messages, info):
        return ModelResponse(
            parts=[TextPart("private answer")] if finish_reason == "stop" else [],
            model_name="test-model", finish_reason=finish_reason,
            provider_details={"finish_reason": "STOP" if finish_reason == "stop" else "MAX_TOKENS",
                              "private": "private metadata"},
            usage=RequestUsage(input_tokens=2918, output_tokens=946, output_reasoning_tokens=825),
        )

    model = FunctionModel(respond)
    with caplog.at_level(logging.INFO):
        if finish_reason == "length":
            with pytest.raises(UnexpectedModelBehavior):
                with model_diagnostics("visual_scan", model, {}):
                    Agent(model).run_sync("private prompt")
        else:
            with model_diagnostics("visual_scan", model, {}):
                Agent(model).run_sync("private prompt")
    assert "input_tokens=2918 output_tokens=946 thinking_tokens=825 answer_tokens=121 total_tokens=3864" in caplog.text
    assert f"finish_reason={finish_reason}" in caplog.text
    assert "responses=1" in caplog.text
    assert "private" not in caplog.text
    assert f"outcome={'success' if finish_reason == 'stop' else 'UnexpectedModelBehavior'}" in caplog.text


def test_schema_errors_log_fields_without_invalid_input(caplog):
    from pydantic import BaseModel

    class Answer(BaseModel):
        amount: int

    def respond(messages, info):
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {"amount": "private invalid value"})])

    model = FunctionModel(respond)
    with caplog.at_level(logging.INFO), pytest.raises(UnexpectedModelBehavior):
        with model_diagnostics("visual_scan", model, {}):
            Agent(model, output_type=Answer, retries=1).run_sync("private prompt")
    assert "schema_validation_errors=" in caplog.text
    assert "int_parsing" in caplog.text
    assert "amount" in caplog.text
    assert "responses=2" in caplog.text
    assert "private" not in caplog.text
    assert "outcome=UnexpectedModelBehavior" in caplog.text


def test_failure_without_response_does_not_invent_usage(caplog):
    error = UnexpectedModelBehavior("failure", body="private response body")

    def respond(messages, info):
        raise error

    model = FunctionModel(respond)
    with caplog.at_level(logging.INFO), pytest.raises(UnexpectedModelBehavior) as caught:
        with model_diagnostics("narrative_review", model, {}):
            Agent(model).run_sync("private prompt")
    assert caught.value is error
    assert "outcome=UnexpectedModelBehavior" in caplog.text
    assert "responses=0" in caplog.text
    assert "input_tokens=" not in caplog.text
    assert "private" not in caplog.text
