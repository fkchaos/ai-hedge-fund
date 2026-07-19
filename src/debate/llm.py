"""MiMo LLM client — OpenAI-compatible API wrapper."""

from __future__ import annotations

import os
from openai import OpenAI


class MiMoLLM:
    """MiMo LLM client using OpenAI-compatible API."""

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        self.model = model or os.getenv("OPENAI_API_MODEL", "mimo-v2.5")
        self.temperature = temperature
        self.max_tokens = max_tokens

        api_key = api_key or os.getenv("OPENAI_API_KEY")
        base_url = base_url or os.getenv("OPENAI_API_BASE")

        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")

        self._client = OpenAI(api_key=api_key, base_url=base_url)

    def complete(self, system: str, user: str) -> str:
        """Call MiMo with system + user messages, return raw text."""
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return resp.choices[0].message.content or ""
