"""LLM Provider abstraction layer for soft.Engineer and OpenHands SDK."""

import logging
import os
from pydantic import SecretStr
from openhands.sdk import LLM

LOGGER = logging.getLogger(__name__)


class LLMProviderFactory:
    """Factory for instantiating OpenHands SDK LLM instances based on environment configuration."""

    @staticmethod
    def create_llm() -> LLM:
        azure_key = os.getenv("AZURE_API_KEY")
        azure_endpoint = os.getenv("AZURE_API_BASE") or os.getenv("AZURE_ENDPOINT")
        azure_version = os.getenv("AZURE_API_VERSION", "2024-08-01-preview")
        azure_deployment = os.getenv("AZURE_DEPLOYMENT_NAME") or os.getenv("AZURE_MODEL", "gpt-4o")

        if azure_key and azure_endpoint:
            model_name = f"azure/{azure_deployment}"
            LOGGER.info("Configuring Azure OpenAI LLM provider model=%s endpoint=%s", model_name, azure_endpoint)
            return LLM(
                model=model_name,
                api_key=SecretStr(azure_key),
                base_url=azure_endpoint.rstrip("/"),
                api_version=azure_version,
            )

        api_key = (
            os.getenv("OPENAI_API_KEY")
            or os.getenv("GROQ_API_KEY_1")
            or os.getenv("GROQ_API_KEY_2")
            or os.getenv("GROQ_API_KEY")
        )
        if not api_key:
            raise ValueError(
                "No valid LLM credentials configured. Please set AZURE_API_KEY, OPENAI_API_KEY, or GROQ_API_KEY_1 in .env."
            )

        model_name = os.getenv("OPENAI_MODEL") or os.getenv("GROQ_MODEL", "groq/qwen/qwen3.6-27b")
        if not model_name.startswith("groq/") and os.getenv("GROQ_API_KEY_1") and not os.getenv("OPENAI_API_KEY"):
            model_name = f"groq/{model_name}"

        LOGGER.info("Configuring LLM provider model=%s", model_name)
        return LLM(model=model_name, api_key=SecretStr(api_key))
