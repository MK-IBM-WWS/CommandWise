import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import app


def test_publish_reload_and_search(tmp_path, monkeypatch):
    assets = os.getenv("COMMANDWISE_TEST_EMBEDDING_DIR")
    if not assets:
        pytest.skip("set COMMANDWISE_TEST_EMBEDDING_DIR to the E5 assets")
    monkeypatch.setenv("RUNTIME_DIR", str(tmp_path))
    monkeypatch.setenv("EMBEDDING_DIR", str(Path(assets).resolve()))
    fields = {
        "document_id": "example-tool",
        "package": "test-package",
        "package_version": "1.0",
        "source_url": "https://example.org/man/example-tool",
        "collected_at": "2026-01-10",
        "distribution": "fedora",
        "release": "44",
    }
    path = "/v1/admin/documents"
    file = ("test.md", "# example-tool\n\n## Пример\n\nКоманда example-tool показывает зелёные яблоки.\n".encode())
    query = {"query": "Как вызвать example-tool для зелёных яблок?", "distribution": "fedora", "release": "44", "top_k": 5}
    with TestClient(app) as client:
        initial = client.get(path).json()
        assert client.post("/v1/search", json=query).status_code == 422
        invalid = client.post(path, data={**fields, "document_id": "../bad"}, files={"file": file})
        assert invalid.status_code == 422
        assert client.get(path).json() == initial

        result = client.post(path, data=fields, files={"file": file})
        assert result.status_code == 201, result.text
        published = result.json()["corpus_version"]
        assert published != initial["corpus_version"]
        after = client.post("/v1/search", json=query).json()
        assert after["corpus_version"] == published
        assert [item["document_id"] for item in after["items"]] == ["example-tool"]
        assert client.post(path, data=fields, files={"file": file}).status_code == 409
        assert client.post("/v1/search", json={**query, "distribution": "debian", "release": "13"}).json()["items"] == []

    with TestClient(app) as client:
        assert client.get(path).json()["corpus_version"] == published
        assert client.post("/v1/search", json=query).json()["items"][0]["document_id"] == "example-tool"
