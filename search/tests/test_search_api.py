import pytest
from fastapi.testclient import TestClient

from app.api import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_corpus_returns_distributions_without_releases(client):
    response = client.get("/v1/corpus")
    assert response.status_code == 200
    assert response.json()["distributions"] == [
        {"id": "debian", "label": "Debian"},
        {"id": "fedora", "label": "Fedora"},
        {"id": "arch", "label": "Arch Linux"},
    ]


def test_real_search_finds_find(client):
    response = client.post(
        "/v1/search",
        json={
            "query": "Как найти файлы больше 100 МБ?",
            "distribution": "debian",
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
            "top_k": 5
        }
    )

    assert response.status_code == 200
    assert response.json()["items"] == []

@pytest.mark.parametrize(("distribution", "manager", "install"), [
    ("debian", "apt", "sudo apt install dnsutils"),
    ("fedora", "dnf", "sudo dnf install bind-utils"),
    ("arch", "pacman", "sudo pacman -Syu bind"),
])
def test_distro_specific_packages_and_native_manager(client, distribution, manager, install):
    def ask(query):
        response = client.post("/v1/search", json={
            "query": query, "distribution": distribution, "top_k": 5,
        })
        assert response.status_code == 200
        return response.json()["items"]

    items = ask("Как установить dig?")
    assert any(install in row["text"] for row in items)
    assert all(row["distribution"] in {distribution, "common"} for row in items)
    assert ask("Как обновить пакеты системы?")[0]["command"] == manager

    if distribution == "fedora":
        equivalents = ask("Что можно использовать вместо apt?")
        assert any("sudo dnf install curl" in row["text"] for row in equivalents)


def test_legacy_release_is_ignored(client):
    data = {"query": "ss", "distribution": "fedora", "top_k": 4}
    expected = client.post("/v1/search", json=data).json()
    assert client.post("/v1/search", json={**data, "release": "invalid"}).json() == expected
