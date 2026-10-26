"""Versions of the saved extraction shape and the LLM prompt that produced it."""
import re


PROMPT_VERSION = 1
SCHEMA_VERSION = 2


def analysis_version(model: str) -> str:
    return f"{model}|prompt:{PROMPT_VERSION}|schema:{SCHEMA_VERSION}"


def is_outdated(stored: str | None) -> bool:
    """Whether the saved prompt or schema differs; the worker model is informational."""
    if stored is None:
        return True
    match = re.fullmatch(r".*\|prompt:([^|]+)\|schema:([^|]+)", stored)
    return match is None or match.groups() != (str(PROMPT_VERSION), str(SCHEMA_VERSION))
