"""Thin Google Gemini wrapper (google-genai SDK).

System instructions stay separate from user data: callers pass `system`
(role/task/rules) and `contents` (user/model turns) apart.

Two robustness features matter on the free tier:
  * transient 503 "high demand" / read-timeout -> retry with backoff
  * every response is cached on disk (outputs/llm_cache/) keyed by the full
    request, so re-runs and report edits never re-spend the daily quota.
"""

from __future__ import annotations

import base64
import hashlib
import json
import time
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

from .config import LLMConfig

ToolSpec = dict[str, Any]  # {"name", "description", "parameters": <JSON schema>}

_CACHE_DIR = Path(__file__).resolve().parent.parent / "outputs" / "llm_cache"


class _Cand:
    def __init__(self, content: types.Content) -> None:
        self.content = content


class _Resp:
    """Minimal stand-in for a google-genai response (text + one candidate)."""

    def __init__(self, text: str | None, content: types.Content) -> None:
        self.text = text
        self.candidates = [_Cand(content)]


def _content_to_jsonable(content: types.Content) -> dict:
    parts = []
    for p in content.parts or []:
        sig = getattr(p, "thought_signature", None)
        entry: dict[str, Any] = {}
        if sig:
            entry["thought_signature"] = base64.b64encode(sig).decode()
        if getattr(p, "function_call", None):
            entry["function_call"] = {
                "name": p.function_call.name,
                "args": dict(p.function_call.args or {}),
            }
        elif getattr(p, "function_response", None):
            entry["function_response"] = {
                "name": p.function_response.name,
                "response": dict(p.function_response.response or {}),
            }
        elif getattr(p, "text", None) is not None:
            entry["text"] = p.text
        else:
            continue
        parts.append(entry)
    return {"role": content.role or "model", "parts": parts}


def _content_from_jsonable(d: dict) -> types.Content:
    parts = []
    for p in d["parts"]:
        kw: dict[str, Any] = {}
        if p.get("thought_signature"):
            kw["thought_signature"] = base64.b64decode(p["thought_signature"])
        if "function_call" in p:
            kw["function_call"] = types.FunctionCall(
                name=p["function_call"]["name"], args=p["function_call"]["args"]
            )
        elif "function_response" in p:
            kw["function_response"] = types.FunctionResponse(
                name=p["function_response"]["name"],
                response=p["function_response"]["response"],
            )
        else:
            kw["text"] = p["text"]
        parts.append(types.Part(**kw))
    return types.Content(role=d.get("role", "model"), parts=parts)


class LLM:
    def __init__(self, cfg: LLMConfig, use_cache: bool = True) -> None:
        self.cfg = cfg
        self.use_cache = use_cache
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        key = cfg.resolved_key()
        http = types.HttpOptions(timeout=90_000)  # ms; fail fast instead of hanging
        self._client = (
            genai.Client(api_key=key, http_options=http)
            if key
            else genai.Client(http_options=http)
        )

    # -- caching -----------------------------------------------------------

    def _cache_path(self, payload: dict) -> Path:
        blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        return _CACHE_DIR / (hashlib.sha256(blob.encode()).hexdigest()[:32] + ".json")

    # -- low level -------------------------------------------------------

    def _generate_content(self, model: str, contents: Any, config: Any):
        last: Exception | None = None
        for attempt in range(5):
            try:
                return self._client.models.generate_content(
                    model=model, contents=contents, config=config
                )
            except genai.errors.ServerError as e:  # 5xx incl. 503 high demand
                last = e
            except genai.errors.ClientError as e:
                if e.code != 429:
                    raise
                last = e
            except Exception as e:  # connection reset / read timeout
                if not any(
                    w in str(e).lower() for w in ("timeout", "deadline", "connection")
                ):
                    raise
                last = e
            time.sleep(2 * (attempt + 1))
        raise RuntimeError(f"Gemini unavailable after retries: {last}")

    @staticmethod
    def _tools(specs: list[ToolSpec] | None):
        if not specs:
            return None
        return [
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name=s["name"],
                        description=s.get("description", ""),
                        parameters=s["parameters"],
                    )
                    for s in specs
                ]
            )
        ]

    # -- public -------------------------------------------------------

    def generate(
        self,
        system: str,
        contents: Any,
        tools: list[ToolSpec] | None = None,
        response_schema: dict | None = None,
        max_tokens: int | None = None,
    ) -> _Resp:
        # serialise contents (str or list[types.Content]) for the cache key
        if isinstance(contents, str):
            contents_key: Any = contents
            contents_arg: Any = contents
        else:
            contents_key = [_content_to_jsonable(c) for c in contents]
            contents_arg = contents

        payload = {
            "model": self.cfg.model,
            "system": system,
            "contents": contents_key,
            "tools": tools,
            "schema": response_schema,
            "max_tokens": max_tokens or self.cfg.max_tokens,
            "thinking_budget": self.cfg.thinking_budget,
        }
        cache_file = self._cache_path(payload)
        if self.use_cache and cache_file.exists():
            d = json.loads(cache_file.read_text())
            return _Resp(d["text"], _content_from_jsonable(d["content"]))

        cfg = types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_tokens or self.cfg.max_tokens,
            tools=self._tools(tools),
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        tb = self.cfg.thinking_budget
        if tb is not None and "lite" not in self.cfg.model:
            cfg.thinking_config = types.ThinkingConfig(thinking_budget=tb)
        if response_schema is not None:
            cfg.response_mime_type = "application/json"
            cfg.response_schema = response_schema

        raw = self._generate_content(self.cfg.model, contents_arg, cfg)
        content = raw.candidates[0].content
        text = "".join(
            p.text for p in (content.parts or []) if getattr(p, "text", None)
        )
        cache_file.write_text(
            json.dumps({"text": text, "content": _content_to_jsonable(content)},
                       ensure_ascii=False, indent=2)
        )
        # return the ORIGINAL content object so thought_signature bytes survive
        return _Resp(text, content)

    def json_object(
        self,
        system: str,
        user: str,
        schema: dict | None = None,
        max_tokens: int | None = None,
    ) -> dict:
        resp = self.generate(system, user, response_schema=schema, max_tokens=max_tokens)
        text = (resp.text or "").strip()
        if text.startswith("```"):
            text = text.split("```", 2)[1].lstrip("json").strip()
        return json.loads(text)
