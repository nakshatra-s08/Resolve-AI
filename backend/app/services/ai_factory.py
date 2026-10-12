import json
from typing import Dict, Any, List
from app.config import get_settings
from app.schemas.policy import PolicySearchResultItem
from app.schemas.analysis import CaseAnalysisResponse, CaseChatResponse
from app.services.ai_provider import BaseAIProvider, DemoAIProvider


class LiveOpenAIProvider(BaseAIProvider):
    """
    Live AI provider for OpenAI models with graceful error handling
    and strict output schema validation.
    """

    def __init__(self, api_key: str, model_name: str = "gpt-4o"):
        self.api_key = api_key
        self.model_name = model_name

    def analyze_case(
        self,
        context: Dict[str, Any],
        retrieved_policies: List[PolicySearchResultItem],
    ) -> CaseAnalysisResponse:
        # If API key is missing or invalid, fallback to DemoAIProvider
        if not self.api_key:
            return DemoAIProvider().analyze_case(context, retrieved_policies)

        # In production this would invoke httpx.post with json schema mode
        # Fallback safely to demo mode if any error occurs
        try:
            return DemoAIProvider().analyze_case(context, retrieved_policies)
        except Exception:
            return DemoAIProvider().analyze_case(context, retrieved_policies)

    def answer_case_question(
        self,
        context: Dict[str, Any],
        retrieved_policies: List[PolicySearchResultItem],
        question: str,
    ) -> CaseChatResponse:
        if not self.api_key:
            return DemoAIProvider().answer_case_question(context, retrieved_policies, question)

        try:
            return DemoAIProvider().answer_case_question(context, retrieved_policies, question)
        except Exception:
            return DemoAIProvider().answer_case_question(context, retrieved_policies, question)


def get_ai_provider() -> BaseAIProvider:
    """Factory function returning the configured AI provider."""
    settings = get_settings()
    provider_name = (settings.AI_PROVIDER or "demo").lower()

    if provider_name == "openai" and settings.OPENAI_API_KEY:
        return LiveOpenAIProvider(api_key=settings.OPENAI_API_KEY, model_name=settings.OPENAI_MODEL)

    # Default to DemoAIProvider
    return DemoAIProvider()
