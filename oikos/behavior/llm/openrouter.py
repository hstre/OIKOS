"""Minimal OpenRouter chat-completions client (standard library only).

The API key is read from the environment variable OPENROUTER_API_KEY and
never written to any output. Every call returns the content together with
the model that actually answered and the reported token usage and cost.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

API_URL = "https://openrouter.ai/api/v1/chat/completions"


class LLMError(RuntimeError):
    pass


@dataclass
class Completion:
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float


class OpenRouterClient:
    def __init__(self, api_key: str | None = None, timeout: float = 60.0, retries: int = 4):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            raise LLMError("OPENROUTER_API_KEY is not set")
        self.timeout = timeout
        self.retries = retries

    def complete(self, model: str, messages: list[dict], *, temperature: float, seed: int,
                 max_tokens: int, json_schema: dict | None = None) -> Completion:
        body = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "seed": seed,
            "max_tokens": max_tokens,
            "usage": {"include": True},
            # route only to providers that honour all parameters (schema, seed)
            "provider": {"require_parameters": True},
        }
        if json_schema is not None:
            body["response_format"] = {"type": "json_schema", "json_schema": json_schema}
        data = json.dumps(body).encode()
        req = urllib.request.Request(API_URL, data=data, method="POST", headers={
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Title": "OIKOS",
        })
        last = None
        for attempt in range(self.retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    out = json.loads(resp.read())
                if "error" in out:
                    raise LLMError(str(out["error"])[:300])
                usage = out.get("usage") or {}
                return Completion(
                    content=out["choices"][0]["message"]["content"] or "",
                    model=out.get("model", model),
                    prompt_tokens=int(usage.get("prompt_tokens", 0)),
                    completion_tokens=int(usage.get("completion_tokens", 0)),
                    cost_usd=float(usage.get("cost", 0.0) or 0.0),
                )
            except (urllib.error.URLError, TimeoutError, LLMError, KeyError, json.JSONDecodeError) as e:
                last = e
                if isinstance(e, urllib.error.HTTPError) and e.code in (400, 401, 402, 403):
                    raise LLMError(f"HTTP {e.code}: {e.read()[:300]!r}") from e
                time.sleep(2 ** attempt)
        raise LLMError(f"request failed after {self.retries + 1} attempts: {last}")
