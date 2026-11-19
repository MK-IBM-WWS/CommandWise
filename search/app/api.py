from contextlib import asynccontextmanager
import hashlib
import json
import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from rank_bm25 import BM25Okapi

from bm25_demo import search


ROOT = Path(__file__).resolve().parents[2]

INDEX_DIR = Path(
    os.getenv(
        "INDEX_DIR",
        str(ROOT / ".local-index")
    )
)


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=4000)

    distribution: Literal[
        "debian",
        "ubuntu",
        "fedora",
        "arch"
    ]

    release: str = Field(min_length=1)

    top_k: int = Field(ge=1, le=10)


def error(status, code, message):
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code,
                "message": message
            }
        }
    )


def load_index():
    pointer = json.loads(
        (INDEX_DIR / "current.json").read_text(
            encoding="utf-8"
        )
    )

    version = pointer["corpus_version"]

    if (
        not isinstance(version, str)
        or not version
        or not all(
            char in "0123456789abcdef"
            for char in version
        )
    ):
        raise ValueError("Invalid corpus version")

    folder = INDEX_DIR / version

    meta = json.loads(
        (folder / "meta.json").read_text(encoding="utf-8")
    )

    if version != meta["corpus_version"]:
        raise ValueError("Index version mismatch")

    for filename, hash_key in [
        ("chunks.json", "chunks_sha256"),
        ("tokens.json", "tokens_sha256"),
    ]:
        digest = hashlib.sha256(
            (folder / filename).read_bytes()
        ).hexdigest()

        if digest != meta[hash_key]:
            raise ValueError(
                f"Index checksum mismatch: {filename}"
            )

    chunks = json.loads(
        (folder / "chunks.json").read_text(
            encoding="utf-8"
        )
    )

    tokens = json.loads(
        (folder / "tokens.json").read_text(
            encoding="utf-8"
        )
    )

    if (
        not chunks
        or len(chunks) != len(tokens)
        or len(chunks) != meta["count"]
    ):
        raise ValueError("Empty or inconsistent index")

    bm25 = BM25Okapi(
        tokens,
        **meta["bm25"]
    )

    return {
        "meta": meta,
        "chunks": chunks,
        "tokens": tokens,
        "bm25": bm25,
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        app.state.index = load_index()
    except Exception as exc:
        app.state.index = None
        print(f"Ошибка загрузки индекса: {exc}")

    yield


app = FastAPI(
    title="CommandWise Search API",
    description="Поисковый сервис BM25",
    lifespan=lifespan
)


@app.exception_handler(RequestValidationError)
def validation_error(request: Request, exc: RequestValidationError):
    return error(
        422,
        "INVALID_REQUEST",
        "Проверь поля query, distribution, release, top_k"
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready(request: Request):
    index = request.app.state.index

    if index is None:
        return error(
            503,
            "INDEX_NOT_READY",
            "Поисковый индекс не загружен"
        )

    return {
        "status": "ready",
        "corpus_version": index["meta"]["corpus_version"]
    }


@app.get("/v1/corpus")
def corpus(request: Request):
    index = request.app.state.index

    if index is None:
        return error(
            503,
            "INDEX_NOT_READY",
            "Поисковый индекс не загружен"
        )

    groups = {}

    for target in index["meta"]["supported_targets"]:
        distribution = target["distribution"]

        groups.setdefault(distribution, []).append({
            "id": target["release"],
            "label": target.get(
                "label",
                target["release"]
            )
        })

    distributions = [
        {
            "id": distribution,
            "label": distribution.capitalize(),
            "releases": releases
        }
        for distribution, releases in sorted(groups.items())
    ]

    return {
        "corpus_version": index["meta"]["corpus_version"],
        "distributions": distributions
    }


@app.post("/v1/search")
def search_endpoint(payload: SearchRequest, request: Request):
    index = request.app.state.index

    if index is None:
        return error(
            503,
            "INDEX_NOT_READY",
            "Поисковый индекс не загружен"
        )

    if not payload.query.strip():
        return error(
            422,
            "INVALID_REQUEST",
            "Вопрос не должен быть пустым"
        )

    target = {
        "distribution": payload.distribution,
        "release": payload.release
    }

    supported = any(
        all(
            saved.get(key) == value
            for key, value in target.items()
        )
        for saved in index["meta"]["supported_targets"]
    )

    if not supported:
        return error(
            422,
            "UNSUPPORTED_TARGET",
            "Нет проверенного корпуса для выбранной системы"
        )

    ranked = search(
        payload.query,
        index["chunks"],
        index["bm25"],
        index["tokens"],
        top_k=len(index["chunks"])
    )

    # Фильтруем совместимые результаты до выбора top_k.
    compatible = [
        item
        for item in ranked
        if target in item["applies_to"]
    ]

    items = []

    for item in compatible[:payload.top_k]:
        result = {
            "chunk_id": item["chunk_id"],
            "document_id": item["document_id"],
            "command": item["command"],
            "title": item["title"],
            "text": item["text"],
            "source_url": item["source_url"],
            "score": item["final_score"],
            "distribution": item["distribution"],
            "release": item["release"],
            "package_version": item["package_version"],
            "section": item["section"],
            "applies_to": item["applies_to"],
        }

        if item["collected_at"]:
            result["collected_at"] = item["collected_at"]

        items.append(result)

    return {
        "corpus_version": index["meta"]["corpus_version"],
        "items": items
    }
