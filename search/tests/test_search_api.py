import pytest
from fastapi.testclient import TestClient

from app.api import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_corpus_contains_debian(client):
    response = client.get("/v1/corpus")

    assert response.status_code == 200

    distributions = response.json()["distributions"]

    assert any(
        d["id"] == "debian"
        and any(
            r["id"] == "13"
            for r in d["releases"]
        )
        for d in distributions
    )


def test_real_search_finds_find(client):
    response = client.post(
        "/v1/search",
        json={
            "query": "Как найти файлы больше 100 МБ?",
            "distribution": "debian",
            "release": "13",
            "top_k": 5
        }
    )

    assert response.status_code == 200

    items = response.json()["items"]

    assert len(items) > 0
    assert items[0]["command"] == "find"

    assert all(
        item["source_url"]
        for item in items
    )


def test_unknown_target_rejected(client):
    response = client.post(
        "/v1/search",
        json={
            "query": "find",
            "distribution": "ubuntu",
            "release": "24.04",
            "top_k": 5
        }
    )

    assert response.status_code == 422
    assert (
        response.json()["error"]["code"]
        == "UNSUPPORTED_TARGET"
    )


def test_invalid_top_k_rejected(client):
    response = client.post(
        "/v1/search",
        json={
            "query": "find",
            "distribution": "debian",
            "release": "13",
            "top_k": 11
        }
    )

    assert response.status_code == 422


def test_unrelated_query_returns_no_sources(client):
    response = client.post(
        "/v1/search",
        json={
            "query": "квантовая запутанность фотонов",
            "distribution": "debian",
            "release": "13",
            "top_k": 5
        }
    )

    assert response.status_code == 200
    assert response.json()["items"] == []

def test_unverified_commands_not_returned_for_debian(client):
    draft_commands = {"cp", "mv", "mkdir", "rm", "cat"}

    for command in sorted(draft_commands):
        response = client.post(
            "/v1/search",
            json={
                "query": f"Как использовать {command}?",
                "distribution": "debian",
                "release": "13",
                "top_k": 10,
            },
        )

        assert response.status_code == 200

        returned = {
            item["command"]
            for item in response.json()["items"]
        }

        assert returned.isdisjoint(draft_commands)
