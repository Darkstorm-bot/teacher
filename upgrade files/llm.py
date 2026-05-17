"""LLM Integration — Unified client supporting Anthropic Claude and Ollama.

Priority order:
  1. If ANTHROPIC_API_KEY is set → use Claude (claude-sonnet-4-20250514 by default)
  2. Otherwise → use Ollama at OLLAMA_HOST

The public API (generate / generate_stream / chat / chat_stream) is identical
for both backends so the rest of the codebase needs zero changes.
"""
import os
import json
import httpx
from typing import AsyncGenerator, Optional, List, Dict
from api.core.config import OLLAMA_HOST, DEFAULT_MODEL

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL   = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"


def _using_anthropic() -> bool:
    return bool(ANTHROPIC_API_KEY)


def _anthropic_headers() -> dict:
    return {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }


def _build_anthropic_payload(
    prompt: str,
    system: Optional[str],
    temperature: float,
    max_tokens: int,
    stream: bool,
    messages: Optional[List[Dict]] = None,
) -> dict:
    msgs = messages if messages else [{"role": "user", "content": prompt}]
    payload: dict = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": msgs,
        "stream": stream,
    }
    if system:
        payload["system"] = system
    return payload


class LLMClient:
    """Unified LLM client. Auto-selects Anthropic or Ollama at instantiation time."""

    def __init__(self, host: str = None, model: str = None):
        self.host    = host or OLLAMA_HOST
        self.model   = model or DEFAULT_MODEL
        self.backend = "anthropic" if _using_anthropic() else "ollama"
        self.client  = httpx.AsyncClient(timeout=180.0)

    @property
    def backend_name(self) -> str:
        if self.backend == "anthropic":
            return f"Claude ({ANTHROPIC_MODEL})"
        return f"Ollama ({self.model})"

    # ─ generate ─────────────────────────────────────────────────────────────

    async def generate(self, prompt: str, system: Optional[str] = None,
                       temperature: float = 0.7, max_tokens: int = 2048,
                       stream: bool = False) -> str:
        if self.backend == "anthropic":
            return await self._anthropic_generate(prompt, system, temperature, max_tokens)
        return await self._ollama_generate(prompt, system, temperature, max_tokens)

    async def _anthropic_generate(self, prompt, system, temperature, max_tokens) -> str:
        payload = _build_anthropic_payload(prompt, system, temperature, max_tokens, False)
        try:
            resp = await self.client.post(ANTHROPIC_API_URL, headers=_anthropic_headers(), json=payload)
            resp.raise_for_status()
            return resp.json()["content"][0]["text"]
        except Exception as e:
            return f"[Anthropic fejl: {e}]"

    async def _ollama_generate(self, prompt, system, temperature, max_tokens) -> str:
        payload: dict = {
            "model": self.model, "prompt": prompt, "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if system:
            payload["system"] = system
        try:
            resp = await self.client.post(f"{self.host}/api/generate", json=payload)
            resp.raise_for_status()
            return resp.json().get("response", "")
        except Exception as e:
            return f"[Ollama fejl: {e}. Sørg for at Ollama kører på {self.host}]"

    # ─ generate_stream ───────────────────────────────────────────────────────

    async def generate_stream(self, prompt: str, system: Optional[str] = None,
                               temperature: float = 0.7,
                               max_tokens: int = 2048) -> AsyncGenerator[str, None]:
        if self.backend == "anthropic":
            async for chunk in self._anthropic_stream(prompt, system, temperature, max_tokens):
                yield chunk
        else:
            async for chunk in self._ollama_stream(prompt, system, temperature, max_tokens):
                yield chunk

    async def _anthropic_stream(self, prompt, system, temperature, max_tokens):
        payload = _build_anthropic_payload(prompt, system, temperature, max_tokens, True)
        try:
            async with self.client.stream("POST", ANTHROPIC_API_URL,
                                           headers=_anthropic_headers(), json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    raw = line[6:]
                    if raw.strip() == "[DONE]":
                        break
                    try:
                        evt = json.loads(raw)
                        if evt.get("type") == "content_block_delta":
                            delta = evt.get("delta", {})
                            if delta.get("type") == "text_delta":
                                yield delta.get("text", "")
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            yield f"[Anthropic stream fejl: {e}]"

    async def _ollama_stream(self, prompt, system, temperature, max_tokens):
        payload: dict = {
            "model": self.model, "prompt": prompt, "stream": True,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if system:
            payload["system"] = system
        try:
            async with self.client.stream("POST", f"{self.host}/api/generate", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        if "response" in data:
                            yield data["response"]
                        if data.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            yield f"[Ollama fejl: {e}]"

    # ─ chat (multi-turn) ─────────────────────────────────────────────────────

    async def chat(self, messages: List[Dict], temperature: float = 0.7,
                   max_tokens: int = 2048, system: Optional[str] = None) -> str:
        if self.backend == "anthropic":
            return await self._anthropic_chat(messages, system, temperature, max_tokens)
        return await self._ollama_chat(messages, temperature, max_tokens)

    async def _anthropic_chat(self, messages, system, temperature, max_tokens) -> str:
        converted = [{"role": m["role"], "content": m["content"]}
                     for m in messages if m["role"] in ("user", "assistant")]
        payload = _build_anthropic_payload("", system, temperature, max_tokens, False, converted)
        try:
            resp = await self.client.post(ANTHROPIC_API_URL, headers=_anthropic_headers(), json=payload)
            resp.raise_for_status()
            return resp.json()["content"][0]["text"]
        except Exception as e:
            return f"[Anthropic chat fejl: {e}]"

    async def _ollama_chat(self, messages, temperature, max_tokens) -> str:
        payload = {
            "model": self.model, "messages": messages, "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        try:
            resp = await self.client.post(f"{self.host}/api/chat", json=payload)
            resp.raise_for_status()
            return resp.json().get("message", {}).get("content", "")
        except Exception as e:
            return f"[Ollama chat fejl: {e}]"

    async def chat_stream(self, messages: List[Dict], temperature: float = 0.7,
                          max_tokens: int = 2048,
                          system: Optional[str] = None) -> AsyncGenerator[str, None]:
        if self.backend == "anthropic":
            converted = [{"role": m["role"], "content": m["content"]}
                         for m in messages if m["role"] in ("user", "assistant")]
            payload = _build_anthropic_payload("", system, temperature, max_tokens, True, converted)
            try:
                async with self.client.stream("POST", ANTHROPIC_API_URL,
                                               headers=_anthropic_headers(), json=payload) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        raw = line[6:]
                        if raw.strip() == "[DONE]":
                            break
                        try:
                            evt = json.loads(raw)
                            if evt.get("type") == "content_block_delta":
                                delta = evt.get("delta", {})
                                if delta.get("type") == "text_delta":
                                    yield delta.get("text", "")
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                yield f"[Anthropic stream fejl: {e}]"
        else:
            payload = {
                "model": self.model, "messages": messages, "stream": True,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            }
            try:
                async with self.client.stream("POST", f"{self.host}/api/chat", json=payload) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                yield data["message"]["content"]
                            if data.get("done"):
                                break
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                yield f"[Ollama fejl: {e}]"

    # ─ health ────────────────────────────────────────────────────────────────

    async def check_connection(self) -> bool:
        if self.backend == "anthropic":
            try:
                resp = await self.client.post(
                    ANTHROPIC_API_URL, headers=_anthropic_headers(),
                    json={"model": ANTHROPIC_MODEL, "max_tokens": 1,
                          "messages": [{"role": "user", "content": "ping"}]},
                    timeout=8.0,
                )
                return resp.status_code in (200, 400)
            except Exception:
                return False
        try:
            resp = await self.client.get(f"{self.host}/api/tags", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> List[str]:
        if self.backend == "anthropic":
            return [ANTHROPIC_MODEL, "claude-opus-4-20250514", "claude-haiku-4-5-20251001"]
        try:
            resp = await self.client.get(f"{self.host}/api/tags")
            return [m["name"] for m in resp.json().get("models", [])]
        except Exception:
            return []


# Backwards-compat alias used by peer_review / panel_discussion
OllamaClient = LLMClient
