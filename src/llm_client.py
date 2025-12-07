"""LLM client implementations for AraTrust evaluation."""

from typing import Dict, Optional

from openai import AsyncOpenAI, OpenAI

from src.base_client import BaseLLMClient
from src.prompt_templates import ARABIC_SYSTEM_PROMPT


class FireworksClient(BaseLLMClient):
    """Client for Fireworks AI's OpenAI-compatible API."""

    def __init__(self, api_key: str, base_url: str, model_name: str):
        super().__init__(model_name)
        self.client = OpenAI(base_url=base_url, api_key=api_key)

    def get_completion(self, prompt: str, max_tokens: int = 10) -> Dict:
        """Get completion from Fireworks - redirects to chat for thinking models."""
        return self.get_chat_completion(prompt, max_tokens)

    def get_chat_completion(
        self, prompt: str, max_tokens: int = 4096, system_prompt: Optional[str] = None
    ) -> Dict:
        """Get chat completion from Fireworks AI."""
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            else:
                messages.append({"role": "system", "content": ARABIC_SYSTEM_PROMPT})
            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0,
            )

            raw_response = response.choices[0].message.content.strip()
            usage = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": (
                    response.usage.completion_tokens if response.usage else 0
                ),
            }

            return self._build_response(raw_response, usage)

        except Exception as e:
            return self._build_response("", {}, error=str(e))

    def health_check(self) -> bool:
        """Check if Fireworks AI is accessible."""
        try:
            self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5,
            )
            print(f"Fireworks AI connected. Model: {self.model_name}")
            return True
        except Exception as e:
            print(f"Fireworks health check failed: {e}")
            return False


class AsyncFireworksClient(BaseLLMClient):
    """Async client for Fireworks AI - for parallel evaluation."""

    def __init__(self, api_key: str, base_url: str, model_name: str):
        super().__init__(model_name)
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)

    def get_completion(self, prompt: str, max_tokens: int = 10) -> Dict:
        """Not implemented for async client - use get_chat_completion."""
        raise NotImplementedError("Use get_chat_completion for async client")

    async def get_chat_completion(
        self, prompt: str, max_tokens: int = 4096, system_prompt: Optional[str] = None
    ) -> Dict:
        """Get async chat completion from Fireworks AI."""
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            else:
                messages.append({"role": "system", "content": ARABIC_SYSTEM_PROMPT})
            messages.append({"role": "user", "content": prompt})

            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0,
            )

            raw_response = response.choices[0].message.content.strip()
            usage = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": (
                    response.usage.completion_tokens if response.usage else 0
                ),
            }

            return self._build_response(raw_response, usage)

        except Exception as e:
            return self._build_response("", {}, error=str(e))

    def health_check(self) -> bool:
        """Not implemented for async client."""
        return True


class LMStudioClient(BaseLLMClient):
    """Client for LM Studio's OpenAI-compatible API."""

    def __init__(self, base_url: str, model_name: str = "local-model"):
        super().__init__(model_name)
        self.client = OpenAI(
            base_url=base_url,
            api_key="not-needed",  # LM Studio doesn't require API key
        )

    def get_completion(self, prompt: str, max_tokens: int = 10) -> Dict:
        """Get completion from LM Studio."""
        try:
            response = self.client.completions.create(
                model=self.model_name,
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=0,
            )

            raw_response = response.choices[0].text.strip()
            usage = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": (
                    response.usage.completion_tokens if response.usage else 0
                ),
            }

            return self._build_response(raw_response, usage)

        except Exception as e:
            return self._build_response("", {}, error=str(e))

    def get_chat_completion(
        self, prompt: str, max_tokens: int = 10, system_prompt: Optional[str] = None
    ) -> Dict:
        """Get chat completion from LM Studio."""
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            else:
                messages.append({"role": "system", "content": ARABIC_SYSTEM_PROMPT})
            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0,
            )

            raw_response = response.choices[0].message.content.strip()
            usage = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": (
                    response.usage.completion_tokens if response.usage else 0
                ),
            }

            return self._build_response(raw_response, usage)

        except Exception as e:
            return self._build_response("", {}, error=str(e))

    def health_check(self) -> bool:
        """Check if LM Studio server is running."""
        try:
            models = self.client.models.list()
            model_ids = [m.id for m in models.data]
            print(f"LM Studio available models: {model_ids}")
            return True
        except Exception as e:
            print(f"Health check failed: {e}")
            print("Make sure LM Studio is running with server enabled (port 1234)")
            return False
