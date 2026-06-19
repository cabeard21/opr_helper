from __future__ import annotations

from typing import Protocol

from django.conf import settings
from openai import OpenAI, OpenAIError
from pydantic import BaseModel, Field, ValidationError

from advisor.context_builder import build_system_prompt, build_unit_table, build_user_context
from advisor.unit_scorer import score_faction_units
from army_books.models import Faction


class AdvisorLLMError(Exception):
    """Raised when the advisor LLM provider cannot satisfy a request."""


class SuggestedUnit(BaseModel):
    unit_id: int = Field(gt=0, description="Database id of the selected unit.")
    unit_name: str = Field(description="Human-readable unit name.")
    model_count: int = Field(gt=0, description="Number of models to include.")
    justification: str = Field(description="One sentence explaining the selection.")


class ListSuggestion(BaseModel):
    units: list[SuggestedUnit]
    total_points: int = Field(ge=0)
    archetype: str
    playstyle: str
    activation_count: int = Field(ge=0)
    strategy_summary: str
    warnings: list[str]


class AdvisorProvider(Protocol):
    def suggest(self, *, system_prompt: str, user_context: str) -> ListSuggestion:
        """Return a validated army list suggestion."""


class OpenAIAdvisorProvider:
    def __init__(self, client: OpenAI | None = None):
        self.client = client or OpenAI(api_key=settings.OPENAI_API_KEY or None)

    def suggest(self, *, system_prompt: str, user_context: str) -> ListSuggestion:
        try:
            response = self.client.responses.parse(
                model=settings.OPENAI_MODEL,
                instructions=system_prompt,
                input=user_context,
                text_format=ListSuggestion,
                max_output_tokens=2048,
            )
        except OpenAIError as exc:
            raise AdvisorLLMError("OpenAI provider request failed.") from exc

        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise AdvisorLLMError("LLM response did not include a structured suggestion.")
        if isinstance(parsed, ListSuggestion):
            return parsed
        try:
            return ListSuggestion.model_validate(parsed)
        except ValidationError as exc:
            raise AdvisorLLMError("LLM response did not match the suggestion schema.") from exc


def get_default_provider() -> str:
    return settings.LLM_PROVIDER


def get_default_model() -> str:
    return settings.OPENAI_MODEL


def get_advisor_provider() -> AdvisorProvider:
    if settings.LLM_PROVIDER == "openai":
        return OpenAIAdvisorProvider()
    raise AdvisorLLMError(f"Unsupported LLM provider: {settings.LLM_PROVIDER}")


def suggest_list(faction_id: int, point_limit: int, user_prompt: str) -> ListSuggestion:
    faction = Faction.objects.get(id=faction_id)
    profiles = score_faction_units(faction_id)
    unit_table = build_unit_table(profiles)
    system_prompt = build_system_prompt(game="AoF")
    user_context = build_user_context(
        faction_name=faction.name,
        point_limit=point_limit,
        unit_table=unit_table,
        user_prompt=user_prompt,
    )
    return get_advisor_provider().suggest(
        system_prompt=system_prompt,
        user_context=user_context,
    )
