from __future__ import annotations

import logging
from typing import Protocol, TypeVar

from django.conf import settings
from openai import OpenAI, OpenAIError
from pydantic import BaseModel, Field, ValidationError

from advisor.context_builder import build_spell_table, build_system_prompt, build_user_context
from advisor.packages import (
    build_advisor_packages,
    build_package_table,
    force_org_summary,
    package_lookup,
    prompt_packages,
    spell_role_tags,
)
from army_books.models import Faction, FactionSpell

ADVISOR_MAX_OUTPUT_TOKENS = 8192
ADVISOR_RETRY_MAX_OUTPUT_TOKENS = 8192
ADVISOR_PARSE_RETRY_INSTRUCTION = (
    "Return complete valid JSON that exactly matches the requested schema. "
    "Keep justifications concise so the response is not truncated."
)

logger = logging.getLogger(__name__)


class AdvisorLLMError(Exception):
    """Raised when the advisor LLM provider cannot satisfy a request."""


class SelectedUpgradeSelection(BaseModel):
    option: int = Field(gt=0, description="Local database id of the selected native upgrade option.")
    quantity: int = Field(default=1, ge=1, description="Number of times this option is selected.")


class SuggestedUnit(BaseModel):
    unit_id: int = Field(gt=0, description="Database id of the selected unit.")
    unit_name: str = Field(description="Human-readable unit name.")
    model_count: int = Field(gt=0, description="Number of models to include.")
    combined_from_count: int = Field(
        default=1,
        ge=1,
        description="Number of same-unit copies combined into this effective unit.",
    )
    selected_upgrade_ids: list[int] = Field(
        default_factory=list,
        description="Local database ids of selected native upgrade options.",
    )
    selected_upgrade_selections: list[SelectedUpgradeSelection] = Field(
        default_factory=list,
        description="Selected native upgrade options with quantities for variable replacement upgrades.",
    )
    parent_unit_index: int | None = Field(
        default=None,
        ge=0,
        description="Zero-based index of the suggested host unit this hero should embed into.",
    )
    justification: str = Field(description="One sentence explaining the selection.")


class ListSuggestion(BaseModel):
    units: list[SuggestedUnit]
    total_points: int = Field(ge=0)
    archetype: str
    playstyle: str
    activation_count: int = Field(ge=0)
    strategy_summary: str
    warnings: list[str]


class PackageSuggestedUnit(BaseModel):
    package_id: str = Field(description="Package id from the supplied legal package table.")
    join_to_unit_index: int | None = Field(
        default=None,
        ge=0,
        description="Zero-based index of the returned package selection this hero should embed into.",
    )
    justification: str = Field(description="One sentence explaining the selection.")


class PackageListSuggestion(BaseModel):
    units: list[PackageSuggestedUnit]
    total_points: int = Field(ge=0)
    archetype: str
    playstyle: str
    activation_count: int = Field(ge=0)
    strategy_summary: str
    warnings: list[str]


SuggestionModel = TypeVar("SuggestionModel", bound=BaseModel)


class AdvisorProvider(Protocol):
    def suggest(
        self,
        *,
        system_prompt: str,
        user_context: str,
        text_format: type[SuggestionModel] = ListSuggestion,
    ) -> SuggestionModel:
        """Return a validated army list suggestion."""


class OpenAIAdvisorProvider:
    def __init__(self, client: OpenAI | None = None):
        self.client = client or OpenAI(api_key=settings.OPENAI_API_KEY or None)

    def suggest(
        self,
        *,
        system_prompt: str,
        user_context: str,
        text_format: type[SuggestionModel] = ListSuggestion,
    ) -> SuggestionModel:
        response = self._parse_response(
            system_prompt=system_prompt,
            user_context=user_context,
            text_format=text_format,
            max_output_tokens=ADVISOR_MAX_OUTPUT_TOKENS,
        )
        parsed = self._parsed_output(response, text_format)
        if parsed is not None:
            return parsed

        logger.warning(
            "Advisor provider returned no parsed output; retrying with stricter structured-output instructions. %s",
            _response_debug_summary(response),
        )
        retry_response = self._parse_response(
            system_prompt=f"{system_prompt}\n\n{ADVISOR_PARSE_RETRY_INSTRUCTION}",
            user_context=user_context,
            text_format=text_format,
            max_output_tokens=ADVISOR_RETRY_MAX_OUTPUT_TOKENS,
        )
        parsed = self._parsed_output(retry_response, text_format)
        if parsed is not None:
            return parsed
        raise AdvisorLLMError("LLM response did not include a structured suggestion.")

    def _parsed_output(
        self,
        response,
        text_format: type[SuggestionModel],
    ) -> SuggestionModel | None:
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            return None
        if isinstance(parsed, text_format):
            return parsed
        try:
            return text_format.model_validate(parsed)
        except ValidationError as exc:
            raise AdvisorLLMError("LLM response did not match the suggestion schema.") from exc

    def _parse_response(
        self,
        *,
        system_prompt: str,
        user_context: str,
        text_format: type[SuggestionModel],
        max_output_tokens: int,
    ):
        try:
            return self.client.responses.parse(
                model=settings.OPENAI_MODEL,
                instructions=system_prompt,
                input=user_context,
                text_format=text_format,
                max_output_tokens=max_output_tokens,
            )
        except OpenAIError as exc:
            raise AdvisorLLMError("OpenAI provider request failed.") from exc
        except ValidationError as exc:
            try:
                return self.client.responses.parse(
                    model=settings.OPENAI_MODEL,
                    instructions=f"{system_prompt}\n\n{ADVISOR_PARSE_RETRY_INSTRUCTION}",
                    input=user_context,
                    text_format=text_format,
                    max_output_tokens=ADVISOR_RETRY_MAX_OUTPUT_TOKENS,
                )
            except OpenAIError as retry_exc:
                raise AdvisorLLMError("OpenAI provider request failed.") from retry_exc
            except ValidationError as retry_exc:
                raise AdvisorLLMError("LLM response did not match the structured suggestion schema.") from retry_exc


def _response_debug_summary(response) -> str:
    parts: list[str] = []
    for name in ("id", "status", "finish_reason"):
        value = getattr(response, name, None)
        if value:
            parts.append(f"{name}={value}")
    incomplete_details = getattr(response, "incomplete_details", None)
    if incomplete_details:
        parts.append(f"incomplete_details={incomplete_details}")
    refusal = getattr(response, "refusal", None)
    if refusal:
        parts.append("refusal=true")
    return " ".join(parts) if parts else "response had no diagnostic fields"


def get_default_provider() -> str:
    return settings.LLM_PROVIDER


def get_default_model() -> str:
    return settings.OPENAI_MODEL


def get_advisor_provider() -> AdvisorProvider:
    if settings.LLM_PROVIDER == "openai":
        return OpenAIAdvisorProvider()
    raise AdvisorLLMError(f"Unsupported LLM provider: {settings.LLM_PROVIDER}")


def suggest_list(
    faction_id: int,
    point_limit: int,
    user_prompt: str,
    *,
    correction_feedback: str = "",
) -> ListSuggestion:
    faction = Faction.objects.get(id=faction_id)
    packages = build_advisor_packages(faction_id, point_limit)
    visible_packages = prompt_packages(
        packages,
        point_limit=point_limit,
        max_rows=int(getattr(settings, "ADVISOR_PACKAGE_TABLE_MAX_ROWS", 60)),
    )
    package_table = build_package_table(visible_packages)
    spell_table = build_spell_table(_faction_spells(faction_id))
    system_prompt = build_system_prompt(game="AoF")
    user_context = build_user_context(
        faction_name=faction.name,
        point_limit=point_limit,
        package_table=package_table,
        spell_table=spell_table,
        force_org=force_org_summary(point_limit),
        user_prompt=user_prompt,
        correction_feedback=correction_feedback,
    )
    package_suggestion = get_advisor_provider().suggest(
        system_prompt=system_prompt,
        user_context=user_context,
        text_format=PackageListSuggestion,
    )
    return package_suggestion_to_list_suggestion(
        package_suggestion,
        package_lookup(visible_packages),
    )


def _faction_spells(faction_id: int) -> list[dict]:
    return [
        {
            "name": spell.name,
            "threshold": spell.threshold,
            "effect": spell.effect,
            "role_tags": spell_role_tags(spell.effect),
        }
        for spell in FactionSpell.objects.filter(faction_id=faction_id).order_by(
            "threshold",
            "name",
            "id",
        )
    ]


def package_suggestion_to_list_suggestion(
    suggestion: PackageListSuggestion,
    packages: dict[str, dict],
) -> ListSuggestion:
    units: list[SuggestedUnit] = []
    warnings = list(suggestion.warnings)
    valid_selections: list[tuple[int, PackageSuggestedUnit, dict]] = []
    original_index_to_output_index: dict[int, int] = {}
    for original_index, selected in enumerate(suggestion.units):
        package = packages.get(selected.package_id)
        if package is None:
            warnings.append(f"Unknown package id {selected.package_id} was skipped.")
            continue
        original_index_to_output_index[original_index] = len(valid_selections)
        valid_selections.append((original_index, selected, package))

    for _original_index, selected, package in valid_selections:
        parent_unit_index = None
        if selected.join_to_unit_index is not None:
            parent_unit_index = original_index_to_output_index.get(selected.join_to_unit_index)
        units.append(
            SuggestedUnit(
                unit_id=int(package["unit_id"]),
                unit_name=str(package["unit_name"]),
                model_count=int(package["model_count"]),
                combined_from_count=int(package.get("combined_from_count", 1)),
                selected_upgrade_ids=list(package["selected_upgrade_ids"]),
                selected_upgrade_selections=list(package.get("selected_upgrade_selections", [])),
                parent_unit_index=parent_unit_index,
                justification=selected.justification,
            )
        )
    return ListSuggestion(
        units=units,
        total_points=suggestion.total_points,
        archetype=suggestion.archetype,
        playstyle=suggestion.playstyle,
        activation_count=len(units),
        strategy_summary=suggestion.strategy_summary,
        warnings=warnings,
    )
