from __future__ import annotations

import base64
from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from bro.ai.providers.base import AIProvider
from bro.ai.providers.catalog import model_supports_vision
from bro.core.context.engine import ContextPackage


class OpenAICompatibleProvider(AIProvider):
    """Works with OpenAI, Groq, Gemini, OpenRouter, DeepSeek, xAI, NVIDIA, local, etc."""

    name = "openai"

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
        provider_label: str | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("API key is required for OpenAI-compatible provider")
        kwargs: dict = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = AsyncOpenAI(**kwargs)
        self._model = model
        self._base_url = base_url or ""
        if provider_label:
            self.name = provider_label
            self.supports_vision = model_supports_vision(provider_label, model)
        else:
            self.name = "openai" if not base_url else "openai-compatible"
            self.supports_vision = model_supports_vision(self.name, model)
        self.model = model

    async def answer_stream(self, package: ContextPackage) -> AsyncIterator[str]:
        messages: list[dict] = [{"role": "system", "content": package.system_prompt}]
        for msg in package.messages:
            role = msg.get("role", "user")
            if role not in ("user", "assistant", "system"):
                role = "user"
            messages.append({"role": role, "content": msg["content"]})
        messages.append({"role": "user", "content": package.user_content})

        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            stream=True,
            temperature=0.4,
        )
        async for event in stream:
            if not event.choices:
                continue
            delta = event.choices[0].delta
            if delta and delta.content:
                yield delta.content

    async def analyze_screen(self, image: bytes, prompt: str) -> str:
        b64 = base64.b64encode(image).decode("ascii")
        data_url = f"data:image/png;base64,{b64}"
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ]
        resp = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=0.2,
            max_tokens=1200,
        )
        choice = resp.choices[0].message
        return (choice.content or "").strip()
