from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

import ollama

from src.core.config import settings
from src.core.logging_config import get_logger
from src.domain.exceptions import AIProviderException

logger = get_logger(__name__)


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    async def generate(
        self,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
        temperature: float | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        """Generate text completion."""
        pass

    @abstractmethod
    async def stream(
        self,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> AsyncIterator[str]:
        """Stream text completion."""
        pass

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for texts."""
        pass


class OpenAIProvider(AIProvider):
    """OpenAI provider implementation."""

    def __init__(self, api_key: str | None = None):
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key or settings.openai_api_key)
        self._model = settings.openai_model
        self._embedding_model = settings.openai_embedding_model

    async def generate(
        self,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
        temperature: float | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        try:
            params: dict[str, Any] = {
                "model": self._model,
                "messages": messages,
                "max_tokens": max_tokens or settings.openai_max_tokens,
                "temperature": temperature or settings.openai_temperature,
            }
            if response_format:
                params["response_format"] = response_format

            response = await self._client.chat.completions.create(**params)
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error("OpenAI generation failed", error=str(e))
            raise AIProviderException(str(e), provider="openai")

    async def stream(
        self,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> AsyncIterator[str]:
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=max_tokens or settings.openai_max_tokens,
                temperature=temperature or settings.openai_temperature,
                stream=True,
            )
            async for chunk in response:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        except Exception as e:
            logger.error("OpenAI streaming failed", error=str(e))
            raise AIProviderException(str(e), provider="openai")

    async def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            response = await self._client.embeddings.create(
                model=self._embedding_model,
                input=texts,
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error("OpenAI embedding failed", error=str(e))
            raise AIProviderException(str(e), provider="openai")


class AnthropicProvider(AIProvider):
    """Anthropic provider implementation (for future use)."""

    def __init__(self, api_key: str | None = None):
        from anthropic import AsyncAnthropic

        self._client = AsyncAnthropic(api_key=api_key or settings.anthropic_api_key)
        self._model = settings.anthropic_model

    async def generate(
        self,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
        temperature: float | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        try:
            # Anthropic uses different message format
            system_msg = None
            user_messages = []
            for msg in messages:
                if msg.get("role") == "system":
                    system_msg = msg.get("content")
                else:
                    user_messages.append(msg)

            params: dict[str, Any] = {
                "model": self._model,
                "messages": user_messages,
                "max_tokens": max_tokens or settings.openai_max_tokens,
                "temperature": temperature or settings.openai_temperature,
            }
            if system_msg:
                params["system"] = system_msg

            response = await self._client.messages.create(**params)
            return response.content[0].text if response.content else ""
        except Exception as e:
            logger.error("Anthropic generation failed", error=str(e))
            raise AIProviderException(str(e), provider="anthropic")

    async def stream(
        self,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> AsyncIterator[str]:
        try:
            system_msg = None
            user_messages = []
            for msg in messages:
                if msg.get("role") == "system":
                    system_msg = msg.get("content")
                else:
                    user_messages.append(msg)

            params: dict[str, Any] = {
                "model": self._model,
                "messages": user_messages,
                "max_tokens": max_tokens or settings.openai_max_tokens,
                "temperature": temperature or settings.openai_temperature,
                "stream": True,
            }
            if system_msg:
                params["system"] = system_msg

            async with self._client.messages.stream(**params) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            logger.error("Anthropic streaming failed", error=str(e))
            raise AIProviderException(str(e), provider="anthropic")

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Anthropic doesn't have embeddings - fallback to OpenAI."""
        raise AIProviderException(
            "Anthropic doesn't support embeddings. Use OpenAI for embeddings.",
            provider="anthropic"
        )


class GroqProvider(AIProvider):
    """Groq provider implementation - fast inference with open-source models."""

    def __init__(self, api_key: str | None = None):
        # Groq uses OpenAI-compatible API
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(
            api_key=api_key or settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
        )
        self._model = settings.groq_model

    async def generate(
        self,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
        temperature: float | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        try:
            params: dict[str, Any] = {
                "model": self._model,
                "messages": messages,
                "max_tokens": max_tokens or settings.openai_max_tokens,
                "temperature": temperature or settings.openai_temperature,
            }
            if response_format:
                # Groq doesn't support response_format yet, add system prompt instead
                params["messages"].insert(0, {
                    "role": "system",
                    "content": "You must respond with valid JSON only. No markdown, no code blocks, just raw JSON."
                })

            response = await self._client.chat.completions.create(**params)
            content = response.choices[0].message.content or ""

            # Try to extract JSON if response_format was requested
            if response_format and content:
                import json
                import re
                # Try to find JSON in the content
                try:
                    # Look for JSON block
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        # Validate it's proper JSON
                        json.loads(json_match.group())
                        return json_match.group()
                except json.JSONDecodeError:
                    pass
                # If no JSON found, wrap in a simple structure
                return json.dumps({"answer": content})

            return content
        except Exception as e:
            logger.error("Groq generation failed", error=str(e))
            raise AIProviderException(str(e), provider="groq")

    async def stream(
        self,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> AsyncIterator[str]:
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=max_tokens or settings.openai_max_tokens,
                temperature=temperature or settings.openai_temperature,
                stream=True,
            )
            async for chunk in response:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        except Exception as e:
            logger.error("Groq streaming failed", error=str(e))
            raise AIProviderException(str(e), provider="groq")

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Groq doesn't have embeddings - fallback to OpenAI."""
        raise AIProviderException(
            "Groq doesn't support embeddings. Configure OPENAI_API_KEY for embeddings.",
            provider="groq"
        )


class OllamaProvider(AIProvider):
    """Ollama provider - local LLM inference, completely free."""

    def __init__(self, base_url: str | None = None, model: str | None = None):
        self._base_url = base_url or settings.ollama_base_url
        self._model = model or settings.ollama_model
        self._embedding_model = settings.ollama_embedding_model
        import httpx
        # Shorter timeout to fail fast when Ollama is not available
        self._client = httpx.AsyncClient(timeout=10.0)

    async def generate(
        self,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
        temperature: float | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        try:
            # DEBUG: Log dos messages recebidos
            logger.info("[DEBUG] Ollama generate chamado", messages_count=len(messages))
            for i, msg in enumerate(messages):
                content_preview = msg.get("content", "")[:200]
                logger.info(f"[DEBUG] Message {i}: role={msg.get('role')}, content_len={len(msg.get('content', ''))}, preview={content_preview}")

            # Extrair system message e user message corretamente
            system_content = None
            user_content = None

            for msg in messages:
                if msg.get("role") == "system":
                    system_content = msg.get("content", "")
                elif msg.get("role") == "user":
                    user_content = msg.get("content", "")

            # DEBUG: Verificar conteúdo extraído
            logger.info(f"[DEBUG] System content length: {len(system_content) if system_content else 0}")
            logger.info(f"[DEBUG] User content length: {len(user_content) if user_content else 0}")

            if user_content:
                logger.info(f"[DEBUG] Primeiros 300 chars do user content: {user_content[:300]}")

            # Montar mensagens no formato correto para ollama.chat()
            ollama_messages = []
            if system_content:
                ollama_messages.append({
                    "role": "system",
                    "content": system_content
                })
            if user_content:
                ollama_messages.append({
                    "role": "user",
                    "content": user_content
                })

            # Se não tem user_content, usar o último message como fallback
            if not user_content and messages:
                last_msg = messages[-1]
                if last_msg.get("role") in ["user", "assistant"]:
                    ollama_messages.append({
                        "role": "user",
                        "content": last_msg.get("content", "")
                    })

            # DEBUG: Log das mensagens formatadas
            logger.info(f"[DEBUG] Enviando {len(ollama_messages)} mensagens para Ollama")

            # Chamar Ollama usando a biblioteca correta
            # A biblioteca ollama é síncrona, então rodamos em thread
            import asyncio
            def _call_ollama():
                return ollama.chat(
                    model=self._model,
                    messages=ollama_messages,
                    options={
                        "temperature": temperature or settings.ollama_temperature,
                        "num_predict": max_tokens or settings.ollama_max_tokens,
                    }
                )

            response = await asyncio.get_event_loop().run_in_executor(None, _call_ollama)
            content = response["message"]["content"]

            logger.info(f"[DEBUG] Resposta recebida do Ollama: {len(content)} caracteres")

            # Try to extract JSON if response_format was requested
            if response_format and content:
                import json
                import re
                try:
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        json.loads(json_match.group())  # Validate
                        return json_match.group()
                except json.JSONDecodeError:
                    pass
                # Wrap in simple structure if no valid JSON found
                return json.dumps({"answer": content})

            return content
        except Exception as e:
            logger.error("Ollama generation failed", error=str(e))
            raise AIProviderException(
                f"Ollama error: {str(e)}. Make sure Ollama is running (ollama serve)",
                provider="ollama"
            )

    async def stream(
        self,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> AsyncIterator[str]:
        try:
            system_msg = ""
            user_messages = []
            for msg in messages:
                if msg.get("role") == "system":
                    system_msg = msg.get("content", "")
                else:
                    user_messages.append(msg)

            prompt = ""
            if system_msg:
                prompt += f"System: {system_msg}\n\n"
            for msg in user_messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    prompt += f"User: {content}\n"
                elif role == "assistant":
                    prompt += f"Assistant: {content}\n"
            prompt += "Assistant: "

            payload = {
                "model": self._model,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": temperature or settings.ollama_temperature,
                    "num_predict": max_tokens or settings.ollama_max_tokens,
                },
            }

            async with self._client.stream(
                "POST",
                f"{self._base_url}/api/generate",
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        import json
                        try:
                            data = json.loads(line)
                            if "response" in data:
                                yield data["response"]
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error("Ollama streaming failed", error=str(e))
            raise AIProviderException(
                f"Ollama error: {str(e)}. Make sure Ollama is running (ollama serve)",
                provider="ollama"
            )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using Ollama's embedding endpoint."""
        try:
            embeddings = []
            for text in texts:
                payload = {
                    "model": self._embedding_model,
                    "prompt": text,
                }
                response = await self._client.post(
                    f"{self._base_url}/api/embeddings",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                embedding = data.get("embedding", [])
                embeddings.append(embedding)
            return embeddings
        except Exception as e:
            logger.error("Ollama embedding failed", error=str(e))
            raise AIProviderException(
                f"Ollama embedding error: {str(e)}. Make sure Ollama is running.",
                provider="ollama"
            )


class AIProviderFactory:
    """Factory for creating AI providers."""

    _providers: dict[str, AIProvider] = {}

    @classmethod
    def get_provider(cls, name: str | None = None) -> AIProvider:
        provider_name = name or settings.default_ai_provider

        if provider_name not in cls._providers:
            if provider_name == "openai":
                cls._providers[provider_name] = OpenAIProvider()
            elif provider_name == "anthropic":
                cls._providers[provider_name] = AnthropicProvider()
            elif provider_name == "groq":
                cls._providers[provider_name] = GroqProvider()
            elif provider_name == "ollama":
                cls._providers[provider_name] = OllamaProvider()
            else:
                raise AIProviderException(f"Unknown provider: {provider_name}")

        return cls._providers[provider_name]

    @classmethod
    def reset(cls) -> None:
        cls._providers.clear()


# Convenience function
def get_ai_provider(name: str | None = None) -> AIProvider:
    return AIProviderFactory.get_provider(name)
