"""Helper utilities for deriving conversation titles via the LLM."""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

import httpx

from ..config import get_settings

logger = logging.getLogger(__name__)

_TITLE_INSTRUCTION = (
    "Return only a short conversation title in 2 to 5 plain words. "
    "Do not include explanations, punctuation, quotes, lists, JSON, or reasoning."
)


async def _make_title_request(url: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    """Generic helper to make a POST request and handle common errors."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPStatusError, httpx.RequestError, ValueError) as exc:
            logger.debug("Title generation request to %s failed: %s", url, exc)
            return None


async def get_conversation_title(user_message: str, assistant_message: str) -> Optional[str]:
    """Request a concise conversation title from the LLM.

    Returns ``None`` if a title could not be generated.
    """
    user_message = (user_message or "").strip()
    assistant_message = (assistant_message or "").strip()
    if not user_message or not assistant_message:
        return None

    settings = get_settings()
    base_url = settings.LLM.host.rstrip("/")
    messages = [
        {"role": "system", "content": _TITLE_INSTRUCTION},
        {
            "role": "user",
            "content": (
                f"The user asked: {user_message}\n"
                f"You answered: {assistant_message}\n"
                "Give only a brief descriptive title (2-5 words)."
            ),
        },
    ]

    title = await _request_openai_style_title(base_url, settings.LLM.model, messages)
    if title is None:
        title = await _request_LLM_title(base_url, settings.LLM.model, messages)
    if title is None:
        title = await _request_LLM_chat_title(base_url, settings.LLM.model, messages)
    if title is None:
        return None
    return _sanitize_title(title)


async def _request_openai_style_title(
    base_url: str, model: str, messages: list[dict[str, str]]
) -> Optional[str]:
    url = f"{base_url}/v1/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "max_tokens": 50,
        "temperature": 0.5,
        "n": 1,
    }
    data = await _make_title_request(url, payload)
    if not isinstance(data, dict):
        return None

    choices = data.get("choices", [])
    if not choices:
        return None
    message = choices[0].get("message", {})
    return _extract_message_text(message)


async def _request_LLM_title(base_url: str, model: str, messages: list[dict[str, str]]) -> Optional[str]:
    prompt = "\n".join(f"{m['role']}: {m['content']}" for m in messages) + "\nassistant:"
    payload = {"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.0}}
    url = f"{base_url}/api/generate"
    data = await _make_title_request(url, payload)
    if not isinstance(data, dict):
        return None

    return data.get("response") or data.get("message")


async def _request_LLM_chat_title(
    base_url: str, model: str, messages: list[dict[str, str]]
) -> Optional[str]:
    payload = {"model": model, "messages": messages, "stream": False, "options": {"temperature": 0.0}}
    url = f"{base_url}/api/chat"
    data = await _make_title_request(url, payload)
    if not isinstance(data, dict):
        return None

    message = data.get("message") or data.get("response")
    if isinstance(message, dict):
        return _extract_message_text(message)
    if isinstance(message, str):
        return message
    return None


def _extract_message_text(message: dict) -> Optional[str]:
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    return None


def _sanitize_title(raw_title: Optional[str]) -> Optional[str]:
    if not raw_title:
        return None

    title = raw_title.strip()
    if not title:
        return None

    # Drop leading labels like "Title:" if present.
    parts = title.split(":", maxsplit=1)
    if len(parts) == 2 and parts[0].strip().lower() in {"title", "conversation"}:
        title = parts[1]

    title = title.strip().strip("\"'`“”„‘’")
    title = re.sub(r"[\r\n]+", " ", title)
    title = re.sub(r"\s+", " ", title)
    title = title.strip().strip("-–—:;,.!?")

    if not title:
        return None

    words = title.split()
    if len(words) < 2:
        return None
    if len(words) > 5:
        title = " ".join(words[:5])

    return title


__all__ = ["get_conversation_title"]