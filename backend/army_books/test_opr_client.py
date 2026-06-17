from unittest.mock import Mock, patch

import pytest
import requests

from army_books.opr_client import OprClientError, fetch_army_book, fetch_army_book_list


def make_response(status_code=200, payload=None, json_error=None):
    response = Mock()
    response.status_code = status_code
    response.text = "response body"
    if json_error is not None:
        response.json.side_effect = json_error
    else:
        response.json.return_value = payload
    return response


@patch("army_books.opr_client.requests.get")
def test_fetch_army_book_list_returns_list_payload(mock_get):
    mock_get.return_value = make_response(payload=[{"uid": "book-1"}])

    assert fetch_army_book_list() == [{"uid": "book-1"}]
    _url, kwargs = mock_get.call_args
    assert kwargs["params"] == {
        "filters": "official",
        "gameSystemSlug": "age-of-fantasy",
        "searchText": "",
        "page": "1",
        "unitCount": "0",
        "balanceValid": "false",
        "customRules": "true",
        "fans": "false",
        "sortBy": "",
    }


@patch("army_books.opr_client.requests.get")
def test_fetch_army_book_uses_current_army_forge_detail_params(mock_get):
    mock_get.return_value = make_response(payload={"uid": "TciwNI3AOMXAM-dr"})

    assert fetch_army_book("TciwNI3AOMXAM-dr") == {"uid": "TciwNI3AOMXAM-dr"}
    args, kwargs = mock_get.call_args
    assert args[0].endswith("/army-books/TciwNI3AOMXAM-dr")
    assert kwargs["params"] == {
        "gameSystem": "4",
        "simpleMode": "false",
        "includeVehicles": "false",
    }


def test_fetch_army_book_raises_for_unsupported_game_system():
    with pytest.raises(OprClientError, match="Unsupported game system"):
        fetch_army_book("book-1", game_system_slug="unknown-system")


@patch("army_books.opr_client.requests.get")
def test_fetch_army_book_list_allows_empty_list(mock_get):
    mock_get.return_value = make_response(payload=[])

    assert fetch_army_book_list() == []


@patch("army_books.opr_client.requests.get")
def test_fetch_army_book_list_raises_for_non_200(mock_get):
    mock_get.return_value = make_response(status_code=503, payload={"error": "down"})

    with pytest.raises(OprClientError, match="503"):
        fetch_army_book_list()


@patch("army_books.opr_client.requests.get")
def test_fetch_army_book_list_raises_for_invalid_json(mock_get):
    mock_get.return_value = make_response(json_error=ValueError("invalid"))

    with pytest.raises(OprClientError, match="invalid JSON"):
        fetch_army_book_list()


@patch("army_books.opr_client.requests.get")
def test_fetch_army_book_list_raises_for_timeout(mock_get):
    mock_get.side_effect = requests.Timeout("too slow")

    with pytest.raises(OprClientError, match="request failed"):
        fetch_army_book_list()
