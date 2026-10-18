from typing import Any, Protocol, TypedDict

import httpx


class ChatMessage(TypedDict):
    role: str
    content: str


class LanguageModelUnavailableError(RuntimeError):
    pass


class ChatCompletionClient(Protocol):
    provider_name: str
    model_name: str

    def generate_structured_reply(
        self, messages: list[ChatMessage], response_schema: dict[str, Any]
    ) -> str: ...

    def is_model_reachable(self) -> bool: ...


class OllamaChatClient:
    provider_name = "ollama"

    def __init__(
        self,
        base_url: str,
        model_name: str,
        temperature: float,
        context_window_tokens: int,
        timeout_seconds: float,
    ) -> None:
        self.model_name = model_name
        self._temperature = temperature
        self._context_window_tokens = context_window_tokens
        self._http_client = httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout_seconds)

    def generate_structured_reply(self, messages: list[ChatMessage], response_schema: dict[str, Any]) -> str:
        request_body = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "format": response_schema,
            "options": {"temperature": self._temperature, "num_ctx": self._context_window_tokens},
        }
        try:
            response = self._http_client.post("/api/chat", json=request_body)
            response.raise_for_status()
        except httpx.HTTPError as http_error:
            raise LanguageModelUnavailableError(
                f"Ollama request failed for model '{self.model_name}': {http_error}"
            ) from http_error
        return str(response.json()["message"]["content"])

    def is_model_reachable(self) -> bool:
        try:
            response = self._http_client.get("/api/tags", timeout=3.0)
            response.raise_for_status()
        except httpx.HTTPError:
            return False
        installed_model_names = {model["name"] for model in response.json().get("models", [])}
        return any(name.split(":")[0] == self.model_name.split(":")[0] for name in installed_model_names)


class OpenAICompatibleChatClient:
    """Works with any server exposing the OpenAI chat completions API (LM Studio, vLLM, llama.cpp, OpenAI)."""

    provider_name = "openai_compatible"

    def __init__(
        self,
        base_url: str,
        model_name: str,
        temperature: float,
        timeout_seconds: float,
        api_key: str | None = None,
    ) -> None:
        self.model_name = model_name
        self._temperature = temperature
        authorization_headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._http_client = httpx.Client(
            base_url=base_url.rstrip("/"), timeout=timeout_seconds, headers=authorization_headers
        )

    def generate_structured_reply(self, messages: list[ChatMessage], response_schema: dict[str, Any]) -> str:
        request_body = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self._temperature,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "assistant_reply", "schema": response_schema},
            },
        }
        try:
            response = self._http_client.post("/chat/completions", json=request_body)
            response.raise_for_status()
        except httpx.HTTPError as http_error:
            raise LanguageModelUnavailableError(
                f"Chat completion request failed for model '{self.model_name}': {http_error}"
            ) from http_error
        return str(response.json()["choices"][0]["message"]["content"])

    def is_model_reachable(self) -> bool:
        try:
            self._http_client.get("/models", timeout=3.0).raise_for_status()
        except httpx.HTTPError:
            return False
        return True
