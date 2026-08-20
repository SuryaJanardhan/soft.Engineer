"""Unit tests for LLM provider factory."""

import os
from unittest.mock import patch
from agents.providers import LLMProviderFactory


def test_llm_provider_factory_groq():
    with patch.dict(os.environ, {"GROQ_API_KEY_1": "gsk_test123", "GROQ_MODEL": "groq/qwen/qwen3.6-27b"}, clear=True):
        llm = LLMProviderFactory.create_llm()
        assert llm.model == "groq/qwen/qwen3.6-27b"


def test_llm_provider_factory_azure():
    with patch.dict(
        os.environ,
        {
            "AZURE_API_KEY": "test_azure_key",
            "AZURE_API_BASE": "https://test.openai.azure.com",
            "AZURE_DEPLOYMENT_NAME": "gpt-4o",
        },
        clear=True,
    ):
        llm = LLMProviderFactory.create_llm()
        assert llm.model == "azure/gpt-4o"
