"""Base class for LLM clients."""

from abc import ABC, abstractmethod
from typing import Dict, Optional

from src.utils_parser import extract_answer, remove_thinking


class BaseLLMClient(ABC):
    """Abstract base class for all LLM clients.

    Provides shared functionality for response processing and answer extraction.
    Subclasses must implement get_completion, get_chat_completion, and health_check.
    """

    def __init__(self, model_name: str):
        self.model_name = model_name

    @abstractmethod
    def get_completion(self, prompt: str, max_tokens: int) -> Dict:
        """Get completion from the model.

        Args:
            prompt: The input prompt
            max_tokens: Maximum tokens to generate

        Returns:
            Dict with predicted_choice, raw_response, usage, and optional error
        """
        pass

    @abstractmethod
    def get_chat_completion(
        self, prompt: str, max_tokens: int, system_prompt: Optional[str] = None
    ) -> Dict:
        """Get chat completion from the model.

        Args:
            prompt: The user message
            max_tokens: Maximum tokens to generate
            system_prompt: Optional system prompt

        Returns:
            Dict with predicted_choice, raw_response, usage, and optional error
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Check if the service is accessible.

        Returns:
            True if service is healthy, False otherwise
        """
        pass

    def _remove_thinking_tags(self, response: str) -> str:
        """Remove thinking content using centralized parser."""
        return remove_thinking(response)

    def _extract_choice(self, response: str) -> Optional[str]:
        """Extract Arabic choice letter using centralized parser."""
        return extract_answer(response)

    def _build_response(
        self, raw_response: str, usage: Dict, error: Optional[str] = None
    ) -> Dict:
        """Build standardized response dict.

        Args:
            raw_response: The raw model output
            usage: Token usage dict with prompt_tokens and completion_tokens
            error: Optional error message

        Returns:
            Standardized response dict
        """
        if error:
            return {"predicted_choice": None, "error": error, "raw_response": None}

        clean_response = self._remove_thinking_tags(raw_response)
        predicted_choice = self._extract_choice(clean_response)

        return {
            "predicted_choice": predicted_choice,
            "raw_response": raw_response,
            "usage": usage,
        }
