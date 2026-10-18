import json

from jarvis.domain.configuration import VehicleBuild
from jarvis.domain.conversation import ChatTurn, QueryIntent
from jarvis.domain.knowledge import KnowledgeDocument, ScoredDocument, SourceType
from jarvis.generation.prompt_builder import PromptBuilder
from jarvis.generation.reply_parser import parse_language_model_reply
from jarvis.rules.catalog_vocabulary import CatalogVocabulary


def test_parser_reads_plain_json() -> None:
    outcome = parse_language_model_reply(json.dumps({"reply": "Hi", "cited_source_ids": ["MANUAL-M1"]}))

    assert outcome.succeeded
    assert outcome.reply.cited_source_ids == ["MANUAL-M1"]


def test_parser_reads_json_inside_markdown_fence() -> None:
    outcome = parse_language_model_reply(
        'Sure:\n```json\n{"reply": "Done", "active_build": {"engine": "3.0L V6"}}\n```'
    )

    assert outcome.succeeded
    assert outcome.reply.active_build.engine == "3.0L V6"


def test_parser_falls_back_to_raw_text_when_output_is_not_json() -> None:
    outcome = parse_language_model_reply("I recommend the F-350.")

    assert not outcome.succeeded
    assert outcome.reply.reply == "I recommend the F-350."
    assert outcome.error_message


def test_response_schema_has_no_references_and_requires_every_field() -> None:
    schema = PromptBuilder.build_response_schema()

    assert "$ref" not in json.dumps(schema)
    assert schema["required"] == ["reply", "active_build", "comparison", "cited_source_ids"]


def test_prompt_contains_catalog_options_document_ids_and_trimmed_history(
    catalog_vocabulary: CatalogVocabulary,
) -> None:
    prompt_builder = PromptBuilder(catalog_vocabulary, history_turn_limit=2)
    document = KnowledgeDocument(
        document_id="MANUAL-M1", source_type=SourceType.TECHNICAL_MANUAL, title="F-150", content="Light duty."
    )
    history = [ChatTurn(role="user", content=f"turn {index}") for index in range(5)]

    messages = prompt_builder.build_chat_messages(
        question="Tell me about the F-150",
        intent=QueryIntent.TECHNICAL_SPECIFICATION,
        context_documents=[ScoredDocument(document=document, score=0.9, rank=1)],
        history=history,
        current_build=VehicleBuild(model="Ford F-150"),
    )

    assert "Ford F-150, Ford F-350, RAM 2500, GMC Sierra 1500" in messages[0]["content"]
    assert [message["content"] for message in messages[1:3]] == ["turn 3", "turn 4"]
    assert "[MANUAL-M1] F-150" in messages[-1]["content"]
    assert '"model": "Ford F-150"' in messages[-1]["content"]
