"""LLM Integration via Ollama API."""
import os
import json
import httpx
from typing import AsyncGenerator, Optional
from api.core.config import OLLAMA_HOST, DEFAULT_MODEL


class OllamaClient:
    """Client for Ollama LLM API with streaming support."""

    def __init__(self, host: str = None, model: str = None):
        self.host = host or OLLAMA_HOST
        self.model = model or DEFAULT_MODEL
        self.client = httpx.AsyncClient(timeout=120.0)

    async def generate(self, prompt: str, system: str = None,
                       temperature: float = 0.7, max_tokens: int = 2048,
                       stream: bool = False) -> str:
        """Generate a response from the LLM."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }
        if system:
            payload["system"] = system

        try:
            response = await self.client.post(
                f"{self.host}/api/generate",
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
        except Exception as e:
            return f"[Fejl i LLM-kommunikation: {str(e)}. Sørg for at Ollama kører på {self.host}]"

    async def generate_stream(self, prompt: str, system: str = None,
                              temperature: float = 0.7,
                              max_tokens: int = 2048) -> AsyncGenerator[str, None]:
        """Stream response from the LLM."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }
        if system:
            payload["system"] = system

        try:
            async with self.client.stream(
                "POST",
                f"{self.host}/api/generate",
                json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            data = json.loads(line)
                            if "response" in data:
                                yield data["response"]
                            if data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            yield f"[Fejl: {str(e)}. Sørg for at Ollama kører.]"

    async def chat(self, messages: list, temperature: float = 0.7,
                   max_tokens: int = 2048) -> str:
        """Chat completion with message history."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }
        try:
            response = await self.client.post(
                f"{self.host}/api/chat",
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "")
        except Exception as e:
            return f"[Fejl i chat-kommunikation: {str(e)}]"

    async def chat_stream(self, messages: list, temperature: float = 0.7,
                          max_tokens: int = 2048) -> AsyncGenerator[str, None]:
        """Stream chat completion."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }
        try:
            async with self.client.stream(
                "POST",
                f"{self.host}/api/chat",
                json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                yield data["message"]["content"]
                            if data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            yield f"[Fejl: {str(e)}]"

    async def check_connection(self) -> bool:
        """Check if Ollama is reachable."""
        try:
            response = await self.client.get(f"{self.host}/api/tags", timeout=5.0)
            return response.status_code == 200
        except:
            return False

    async def list_models(self) -> list:
        """List available models."""
        try:
            response = await self.client.get(f"{self.host}/api/tags")
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
        except:
            return []
