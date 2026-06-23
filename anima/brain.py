"""
The Brain — abstraction over intelligence backends.

Three tiers:
1. LOCAL (Ollama) — free, always available, runs on device. Used for:
   - Deep thoughts (inner monologue)
   - Casual conversation
   - Reflection / pattern extraction
   - Chat absorption
   Good enough for 90% of cognitive activity.

2. CLOUD (Anthropic API) — paid, higher quality. Used for:
   - Important conversations (when local isn't cutting it)
   - Birth from personality documents
   - Complex reasoning moments
   Used sparingly. The "phone a friend" of cognition.

3. MECHANICAL (no model) — instant, free. Used for:
   - Shallow thoughts (template recombination)
   - Emotion math, memory decay, salience
   - All state management
   Already running locally in the other modules.

The agent defaults to LOCAL. Cloud is a conscious escalation.
"""

import json
import asyncio
from typing import Optional
from dataclasses import dataclass
from enum import Enum

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


class Tier(Enum):
    LOCAL = "local"
    CLOUD = "cloud"


@dataclass
class BrainResponse:
    text: str
    tier: Tier
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""


class Brain:
    """Unified interface to local and cloud intelligence."""

    # default local models — small, fast, good enough for inner monologue
    DEFAULT_LOCAL_MODELS = [
        "gemma3:4b",
        "llama3.2:3b",
        "phi4-mini",
        "qwen2.5:3b",
        "gemma2:2b",
    ]

    def __init__(self, api_key: str | None = None,
                 ollama_url: str = "http://localhost:11434",
                 local_model: str | None = None,
                 cloud_model: str = "claude-sonnet-4-20250514",
                 cloud_model_cheap: str = "claude-haiku-4-5-20251001"):
        self.api_key = api_key
        self.ollama_url = ollama_url.rstrip("/")
        self.cloud_model = cloud_model
        self.cloud_model_cheap = cloud_model_cheap
        self._local_model = local_model
        self._local_available: Optional[bool] = None
        self._cloud_client = None

        if api_key and HAS_ANTHROPIC:
            self._cloud_client = anthropic.Anthropic(api_key=api_key)

    async def _check_local(self) -> bool:
        """Check if Ollama is running and has a model available."""
        if self._local_available is not None:
            return self._local_available

        if not HAS_HTTPX:
            # fall back to urllib
            import urllib.request
            try:
                req = urllib.request.Request(f"{self.ollama_url}/api/tags")
                with urllib.request.urlopen(req, timeout=3) as resp:
                    data = json.loads(resp.read())
                    models = [m["name"].split(":")[0] for m in data.get("models", [])]
                    if self._local_model and any(self._local_model.split(":")[0] in m for m in models):
                        self._local_available = True
                    else:
                        # find any suitable model
                        for candidate in self.DEFAULT_LOCAL_MODELS:
                            base = candidate.split(":")[0]
                            if any(base in m for m in models):
                                self._local_model = candidate
                                self._local_available = True
                                break
                    if not self._local_available:
                        if models:
                            self._local_model = data["models"][0]["name"]
                            self._local_available = True
                        else:
                            self._local_available = False
            except Exception:
                self._local_available = False
        else:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(f"{self.ollama_url}/api/tags", timeout=3)
                    data = resp.json()
                    models = [m["name"].split(":")[0] for m in data.get("models", [])]
                    if self._local_model and any(self._local_model.split(":")[0] in m for m in models):
                        self._local_available = True
                    else:
                        for candidate in self.DEFAULT_LOCAL_MODELS:
                            base = candidate.split(":")[0]
                            if any(base in m for m in models):
                                self._local_model = candidate
                                self._local_available = True
                                break
                    if not self._local_available:
                        if models:
                            self._local_model = data["models"][0]["name"]
                            self._local_available = True
                        else:
                            self._local_available = False
            except Exception:
                self._local_available = False

        return self._local_available

    async def think(self, system: str, prompt: str, max_tokens: int = 200,
                    temperature: float = 0.8) -> BrainResponse:
        """Generate a thought — prefers local, falls back to cloud cheap."""
        if await self._check_local():
            return await self._local_generate(system, prompt, max_tokens, temperature)
        if self._cloud_client:
            return await self._cloud_generate(system, prompt, max_tokens, temperature, cheap=True)
        return BrainResponse(text="", tier=Tier.LOCAL, model="none")

    async def speak(self, system: str, messages: list[dict], max_tokens: int = 400,
                    temperature: float = 0.7, important: bool = False) -> BrainResponse:
        """Generate a conversation response.
        important=True forces cloud for quality-critical moments."""
        if important and self._cloud_client:
            return await self._cloud_chat(system, messages, max_tokens, temperature, cheap=False)
        if await self._check_local():
            return await self._local_chat(system, messages, max_tokens, temperature)
        if self._cloud_client:
            return await self._cloud_chat(system, messages, max_tokens, temperature, cheap=True)
        # nothing available — retry local detection once
        self._local_available = None
        if await self._check_local():
            return await self._local_chat(system, messages, max_tokens, temperature)
        return BrainResponse(text="(no brain available — is Ollama running?)", tier=Tier.LOCAL, model="none")

    async def analyze(self, system: str, text: str, max_tokens: int = 600) -> BrainResponse:
        """Analyze text (for reflection, absorption). Prefers local."""
        if await self._check_local():
            return await self._local_generate(system, text, max_tokens, 0.3)
        if self._cloud_client:
            return await self._cloud_generate(system, text, max_tokens, 0.3, cheap=True)
        return BrainResponse(text="", tier=Tier.LOCAL, model="none")

    # --- Local (Ollama) ---

    async def _local_generate(self, system: str, prompt: str, max_tokens: int,
                              temperature: float) -> BrainResponse:
        payload = {
            "model": self._local_model,
            "system": system,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }

        try:
            if HAS_HTTPX:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        f"{self.ollama_url}/api/generate",
                        json=payload, timeout=30
                    )
                    data = resp.json()
            else:
                data = await asyncio.to_thread(self._urllib_post,
                    f"{self.ollama_url}/api/generate", payload)

            return BrainResponse(
                text=data.get("response", ""),
                tier=Tier.LOCAL,
                model=self._local_model or "unknown",
            )
        except Exception as e:
            # local failed — fall back to cloud
            if self._cloud_client:
                return await self._cloud_generate(system, prompt, max_tokens, temperature, cheap=True)
            return BrainResponse(text="", tier=Tier.LOCAL, model="failed")

    async def _local_chat(self, system: str, messages: list[dict], max_tokens: int,
                          temperature: float) -> BrainResponse:
        ollama_messages = [{"role": "system", "content": system}]
        for m in messages:
            ollama_messages.append({"role": m["role"], "content": m["content"]})

        payload = {
            "model": self._local_model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }

        try:
            if HAS_HTTPX:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        f"{self.ollama_url}/api/chat",
                        json=payload, timeout=30
                    )
                    data = resp.json()
            else:
                data = await asyncio.to_thread(self._urllib_post,
                    f"{self.ollama_url}/api/chat", payload)

            return BrainResponse(
                text=data.get("message", {}).get("content", ""),
                tier=Tier.LOCAL,
                model=self._local_model or "unknown",
            )
        except Exception:
            if self._cloud_client:
                return await self._cloud_chat(system, messages, max_tokens, temperature, cheap=True)
            return BrainResponse(text="", tier=Tier.LOCAL, model="failed")

    # --- Cloud (Anthropic) ---

    async def _cloud_generate(self, system: str, prompt: str, max_tokens: int,
                              temperature: float, cheap: bool = True) -> BrainResponse:
        if not self._cloud_client:
            return BrainResponse(text="", tier=Tier.CLOUD, model="no-key")

        model = self.cloud_model_cheap if cheap else self.cloud_model

        response = self._cloud_client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )

        return BrainResponse(
            text=response.content[0].text.strip(),
            tier=Tier.CLOUD,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=model,
        )

    async def _cloud_chat(self, system: str, messages: list[dict], max_tokens: int,
                          temperature: float, cheap: bool = True) -> BrainResponse:
        if not self._cloud_client:
            return BrainResponse(text="", tier=Tier.CLOUD, model="no-key")

        model = self.cloud_model_cheap if cheap else self.cloud_model

        response = self._cloud_client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=messages,
        )

        return BrainResponse(
            text=response.content[0].text.strip(),
            tier=Tier.CLOUD,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=model,
        )

    @staticmethod
    def _urllib_post(url: str, payload: dict) -> dict:
        import urllib.request
        data = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=data,
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())

    @property
    def status(self) -> dict:
        return {
            "local_available": self._local_available or False,
            "local_model": self._local_model,
            "cloud_available": self._cloud_client is not None,
            "cloud_model": self.cloud_model,
        }
