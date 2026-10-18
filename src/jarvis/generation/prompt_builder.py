import json
from typing import Any

from jarvis.domain.configuration import VehicleBuild
from jarvis.domain.conversation import ChatTurn, LanguageModelReply, QueryIntent
from jarvis.domain.knowledge import ScoredDocument
from jarvis.generation.llm_clients import ChatMessage
from jarvis.rules.catalog_vocabulary import CatalogVocabulary

ASSISTANT_PERSONA = """You are Jarvis, a truck configuration consultant at a commercial truck dealership.
You help customers choose a pickup configuration (model, engine, transmission, trim) for their use case,
and you compare real-world EPA fuel economy data for pickups.
Tone: confident, clear and friendly. Explain technical terms briefly. Keep answers under 150 words unless the
customer asks for more detail."""

GROUNDING_RULES = """Rules you must follow:
1. Use only facts from the KNOWLEDGE section. If the answer is not there, say that the knowledge base
   does not cover it.
2. Never invent prices, towing figures, ratings or fuel economy numbers. Quote numbers exactly as written.
3. Put the id of every knowledge document you used in "cited_source_ids" (for example "MANUAL-M1").
4. Engineering constraints in the knowledge are mandatory. If the customer asks for a forbidden combination,
   explain the conflict and suggest the allowed alternative.
5. Keep every field of CURRENT BUILD unless the customer changes it. Use null for fields that are still open.
6. Fill "comparison" only when the customer compares two vehicles, otherwise set it to null.
7. Interpret informal wishes: "something tough" or "a beast" means a high-torque heavy-duty setup,
   "a green option" means the EV Dual Motor or the 2.0L I4 Turbo, "for driving kids around" means safety first
   with the Premium trim."""


def inline_schema_references(json_schema: dict[str, Any]) -> dict[str, Any]:
    """Replaces "$ref" pointers with their definitions, because some local runtimes ignore "$defs"."""
    definitions = json_schema.get("$defs", {})

    def resolve(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                return resolve(definitions[node["$ref"].split("/")[-1]])
            return {key: resolve(value) for key, value in node.items() if key != "$defs"}
        if isinstance(node, list):
            return [resolve(item) for item in node]
        return node

    resolved_schema: dict[str, Any] = resolve(json_schema)
    return resolved_schema


class PromptBuilder:
    def __init__(self, catalog_vocabulary: CatalogVocabulary, history_turn_limit: int) -> None:
        self._catalog_vocabulary = catalog_vocabulary
        self._history_turn_limit = history_turn_limit
        self._system_prompt = self._compose_system_prompt()

    @staticmethod
    def build_response_schema() -> dict[str, Any]:
        response_schema = inline_schema_references(LanguageModelReply.model_json_schema())
        response_schema["required"] = list(response_schema["properties"])
        return response_schema

    def build_chat_messages(
        self,
        question: str,
        intent: QueryIntent,
        context_documents: list[ScoredDocument],
        history: list[ChatTurn],
        current_build: VehicleBuild,
    ) -> list[ChatMessage]:
        messages: list[ChatMessage] = [{"role": "system", "content": self._system_prompt}]
        recent_history = history[-self._history_turn_limit :] if self._history_turn_limit else []
        messages.extend({"role": turn.role, "content": turn.content} for turn in recent_history)
        messages.append(
            {
                "role": "user",
                "content": self._compose_user_message(question, intent, context_documents, current_build),
            }
        )
        return messages

    def _compose_system_prompt(self) -> str:
        catalog_lines = "\n".join(
            f"- {build_field}: {', '.join(self._catalog_vocabulary.list_option_names(build_field))}"
            for build_field in ("model", "engine", "transmission", "trim", "application")
        )
        return (
            f"{ASSISTANT_PERSONA}\n\n{GROUNDING_RULES}\n\n"
            f"Catalog options (use these exact names in active_build):\n{catalog_lines}\n\n"
            "Answer with a JSON object containing: reply, active_build, comparison, cited_source_ids."
        )

    @staticmethod
    def _compose_user_message(
        question: str,
        intent: QueryIntent,
        context_documents: list[ScoredDocument],
        current_build: VehicleBuild,
    ) -> str:
        knowledge_section = "\n\n".join(
            f"[{scored.document.document_id}] {scored.document.title}\n{scored.document.content}"
            for scored in context_documents
        )
        return (
            f"CURRENT BUILD:\n{json.dumps(current_build.model_dump(), indent=2)}\n\n"
            f"KNOWLEDGE:\n{knowledge_section or 'No documents were retrieved.'}\n\n"
            f"DETECTED INTENT: {intent.value}\n\n"
            f"QUESTION:\n{question}"
        )
