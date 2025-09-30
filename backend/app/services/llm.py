"""Service for interacting with LLM API with streaming responses."""

from __future__ import annotations

import json
import logging
from typing import AsyncIterator

import httpx

from ..config import get_settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for streaming chat completions from LLM or OpenAI-compatible endpoints."""

    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.LLM.host.rstrip("/")
        self._model = settings.LLM.model
        self._system_prompt = settings.LLM.system_prompt
        self._client = httpx.AsyncClient(timeout=120.0, follow_redirects=True)

    async def close(self) -> None:
        await self._client.aclose()

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        stream: bool = True,
    ) -> AsyncIterator[dict[str, str]]:
        logger.debug("LLM request payload: %s", messages)
        payload_messages = [{"role": "system", "content": self._system_prompt}] + messages
        openai_payload = {
            "model": self._model,
            "messages": payload_messages,
            "stream": stream,
        }

        try:
            async for chunk in self._stream_openai(openai_payload):
                yield chunk
            return
        except Exception as exc:  # noqa: BLE001
            logger.warning("OpenAI compatible streaming failed, falling back to LLM API: %s", exc)

        async for chunk in self._stream_llm(payload_messages):
            yield chunk

    async def _stream_openai(self, payload: dict) -> AsyncIterator[dict[str, str]]:
        url = f"{self._base_url}/v1/chat/completions"
        async with self._client.stream("POST", url, json=payload) as response:
            response.raise_for_status()
            async for raw_line in response.aiter_lines():
                if not raw_line:
                    continue
                if raw_line.startswith("data:"):
                    data = raw_line[len("data:") :].strip()
                    if data == "[DONE]":
                        yield {"done": True}
                        break
                    try:
                        message_json = json.loads(data)
                    except json.JSONDecodeError as exc:  # noqa: BLE001
                        logger.debug("Failed to decode OpenAI chunk: %s", exc)
                        continue
                    choices = message_json.get("choices", [])
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {})
                    content_piece = delta.get("content", "")
                    if content_piece:
                        yield {"message": {"content": content_piece}}

    async def _stream_llm(self, messages: list[dict[str, str]]) -> AsyncIterator[dict[str, str]]:
        formatted_prompt = "\n".join(f"{message['role']}: {message['content']}" for message in messages)
        payload = {
            "model": self._model,
            "prompt": formatted_prompt,
            "stream": True,
        }
        url = f"{self._base_url}/api/generate"
        async with self._client.stream("POST", url, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                chunk = json.loads(line)
                if "response" in chunk:
                    yield {"message": {"content": chunk["response"]}}
                if chunk.get("done"):
                    yield {"done": True}
                    break


_llm_client: LLMClient | None = None


async def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client

