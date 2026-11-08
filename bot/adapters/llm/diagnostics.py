"""Log model-call metadata on success and failure, never prompts or response contents."""
import logging
from contextlib import contextmanager
from time import monotonic

from pydantic_ai import ModelResponse, capture_run_messages
from pydantic_ai.messages import ModelRequest, RetryFeedbackPart, ToolReturnPart

logger = logging.getLogger(__name__)


@contextmanager
def model_diagnostics(stage, model, settings, history_count=0):
    started = monotonic()
    logger.info("llm stage=%s started model=%s settings=%s", stage,
                getattr(model, "model_name", model), settings)
    outcome = "success"
    with capture_run_messages() as messages:
        try:
            yield
        except Exception as error:
            outcome = type(error).__name__
            raise
        finally:
            messages = messages[history_count:]
            responses = [message for message in messages if isinstance(message, ModelResponse)]
            for message in messages:
                if isinstance(message, ModelRequest):
                    for part in message.parts:
                        if (isinstance(part, (RetryFeedbackPart, ToolReturnPart))
                                and isinstance(part.content, list)):
                            logger.warning("llm stage=%s schema_validation_errors=%s", stage,
                                           [{"type": error["type"], "loc": error["loc"]}
                                            for error in part.content if isinstance(error, dict)
                                            and "type" in error and "loc" in error])
            for attempt, response in enumerate(responses, 1):
                usage = response.usage
                logger.info(
                    "llm stage=%s response=%d model=%s response_id=%s finish_reason=%s "
                    "provider_finish_reason=%s input_tokens=%s output_tokens=%s "
                    "thinking_tokens=%s answer_tokens=%s total_tokens=%s cached_tokens=%s "
                    "unmeasured_requests=%s",
                    stage, attempt, response.model_name, response.provider_response_id,
                    response.finish_reason, (response.provider_details or {}).get("finish_reason"),
                    usage.input_tokens, usage.output_tokens, usage.output_reasoning_tokens,
                    usage.output_tokens - usage.output_reasoning_tokens, usage.total_tokens,
                    usage.cache_read_tokens, usage.unmeasured_requests,
                )
            logger.info("llm stage=%s finished outcome=%s duration_seconds=%.2f responses=%d",
                        stage, outcome, monotonic() - started, len(responses))
