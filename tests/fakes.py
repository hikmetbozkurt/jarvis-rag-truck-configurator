import hashlib
import json
import math
from typing import Any

from jarvis.generation.llm_clients import ChatMessage, LanguageModelUnavailableError
from jarvis.retrieval.keyword_index import tokenize_for_keyword_search

HASHED_VECTOR_SIZE = 512


class HashedBagOfWordsEmbeddingModel:
    """Deterministic stand-in for a sentence embedding model so tests never download weights."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_text(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed_text(text)

    @staticmethod
    def _embed_text(text: str) -> list[float]:
        vector = [0.0] * HASHED_VECTOR_SIZE
        for token in tokenize_for_keyword_search(text):
            bucket = int(hashlib.md5(token.encode()).hexdigest(), 16) % HASHED_VECTOR_SIZE
            vector[bucket] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


class ScriptedChatClient:
    provider_name = "scripted"
    model_name = "scripted-model"

    def __init__(self, scripted_reply: dict[str, Any] | str, is_reachable: bool = True) -> None:
        self._scripted_reply = scripted_reply
        self._is_reachable = is_reachable
        self.received_messages: list[list[ChatMessage]] = []

    def generate_structured_reply(self, messages: list[ChatMessage], response_schema: dict[str, Any]) -> str:
        self.received_messages.append(messages)
        if isinstance(self._scripted_reply, str):
            return self._scripted_reply
        return json.dumps(self._scripted_reply)

    def is_model_reachable(self) -> bool:
        return self._is_reachable


class UnavailableChatClient(ScriptedChatClient):
    def __init__(self) -> None:
        super().__init__(scripted_reply="", is_reachable=False)

    def generate_structured_reply(self, messages: list[ChatMessage], response_schema: dict[str, Any]) -> str:
        raise LanguageModelUnavailableError("Connection refused")
