import json
from dataclasses import dataclass

from pydantic import ValidationError

from jarvis.domain.conversation import LanguageModelReply


@dataclass(frozen=True)
class ReplyParsingOutcome:
    reply: LanguageModelReply
    succeeded: bool
    error_message: str | None = None


def _extract_json_object(raw_output: str) -> str:
    cleaned_output = raw_output.replace("```json", "").replace("```", "").strip()
    first_brace = cleaned_output.find("{")
    last_brace = cleaned_output.rfind("}")
    if first_brace == -1 or last_brace <= first_brace:
        raise ValueError("No JSON object found in model output.")
    return cleaned_output[first_brace : last_brace + 1]


def parse_language_model_reply(raw_output: str) -> ReplyParsingOutcome:
    try:
        reply = LanguageModelReply.model_validate(json.loads(_extract_json_object(raw_output)))
    except (ValueError, ValidationError) as parsing_error:
        fallback_reply = LanguageModelReply(reply=raw_output.strip() or "I could not generate an answer.")
        return ReplyParsingOutcome(
            reply=fallback_reply, succeeded=False, error_message=str(parsing_error)[:500]
        )
    return ReplyParsingOutcome(reply=reply, succeeded=True)
