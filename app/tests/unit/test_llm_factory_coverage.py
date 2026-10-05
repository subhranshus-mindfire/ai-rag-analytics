"""
Unit tests covering LLM Factory providers and fallback behavior.
"""
import unittest
from unittest.mock import patch
from app.llms.llm_factory import get_llm, _create_dummy_llm
from app.config.env_config import settings


class TestLLMFactoryCoverage(unittest.TestCase):

    def _get_resp_text(self, resp) -> str:
        if hasattr(resp, "content"):
            return resp.content
        return str(resp)

    def test_dummy_llm_execution(self):
        dummy = _create_dummy_llm("Testing fallback")
        resp = dummy.invoke("Hello")
        self.assertIn("Testing fallback", self._get_resp_text(resp))

    def test_unknown_provider_fallback(self):
        with patch.object(settings, "LLM_PROVIDER", "unsupported_provider"):
            llm = get_llm()
            resp = llm.invoke("Hi")
            self.assertIn("Unknown provider", self._get_resp_text(resp))

    def test_groq_missing_key_fallback(self):
        with patch.object(settings, "LLM_PROVIDER", "groq"):
            with patch.object(settings, "GROQ_API_KEY", ""):
                llm = get_llm()
                resp = llm.invoke("Test query")
                self.assertIn("Groq API key not set", self._get_resp_text(resp))

    def test_gemini_missing_key_fallback(self):
        with patch.object(settings, "LLM_PROVIDER", "gemini"):
            with patch.object(settings, "GOOGLE_API_KEY", ""):
                llm = get_llm()
                resp = llm.invoke("Test query")
                self.assertIn("Google API key not set", self._get_resp_text(resp))

    def test_ollama_provider_creation(self):
        with patch.object(settings, "LLM_PROVIDER", "ollama"):
            try:
                llm = get_llm()
                self.assertIsNotNone(llm)
            except ImportError:
                pass


if __name__ == "__main__":
    unittest.main()
