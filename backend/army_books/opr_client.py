"""Thin HTTP client for public OPR Army Forge endpoints."""

from __future__ import annotations

from typing import Any

import requests


BASE_URL = "https://army-forge.onepagerules.com/api"
DEFAULT_TIMEOUT_SECONDS = 20
GAME_SYSTEM_IDS = {
    "age-of-fantasy": "4",
}


class OprClientError(RuntimeError):
    """Raised when Army Forge cannot return a usable payload."""


def fetch_army_book_list(game_system_slug: str = "age-of-fantasy") -> list[dict[str, Any]]:
    payload = _get_json(
        f"{BASE_URL}/army-books",
        params={
            "filters": "official",
            "gameSystemSlug": game_system_slug,
            "searchText": "",
            "page": "1",
            "unitCount": "0",
            "balanceValid": "false",
            "customRules": "true",
            "fans": "false",
            "sortBy": "",
        },
    )
    if not isinstance(payload, list):
        raise OprClientError("Army book list payload was not a list")
    return payload


def fetch_army_book(uid: str, game_system_slug: str = "age-of-fantasy") -> dict[str, Any]:
    game_system_id = _game_system_id(game_system_slug)
    payload = _get_json(
        f"{BASE_URL}/army-books/{uid}",
        params={
            "gameSystem": game_system_id,
            "simpleMode": "false",
            "includeVehicles": "false",
        },
    )
    if not isinstance(payload, dict):
        raise OprClientError("Army book payload was not an object")
    return payload


def _game_system_id(game_system_slug: str) -> str:
    game_system_id = GAME_SYSTEM_IDS.get(game_system_slug)
    if game_system_id is None:
        raise OprClientError(f"Unsupported game system: {game_system_slug}")
    return game_system_id


def _get_json(url: str, params: dict[str, str]) -> Any:
    try:
        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        raise OprClientError(f"Army Forge request failed: {exc}") from exc

    if response.status_code != 200:
        raise OprClientError(f"Army Forge returned HTTP {response.status_code}")

    try:
        return response.json()
    except ValueError as exc:
        raise OprClientError("Army Forge returned invalid JSON") from exc
