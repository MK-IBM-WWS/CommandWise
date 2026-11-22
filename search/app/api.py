from contextlib import asynccontextmanager
import hashlib
import json
import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from bm25_index import BM25Index

from app.distributions import DISTRIBUTIONS
from app.corpus_store import CorpusStore, DocumentExists, InvalidDocument, MAX_UPLOAD, validate
from bm25_demo import search, tokenize

logger = logging.getLogger("uvicorn.error")


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

    distribution: str = Field(min_length=1, max_length=32)
    release: str | None = None  # Accepted for older API clients.

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


def load_index(directory=INDEX_DIR):
    pointer = json.loads(
        (directory / "current.json").read_text(
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

    folder = directory / version

    meta = json.loads(
        (folder / "meta.json").read_text(encoding="utf-8")
    )

    if version != meta["corpus_version"]:
        raise ValueError("Index version mismatch")

    def checked_json(filename, hash_key):
        data = (folder / filename).read_bytes()
        if hashlib.sha256(data).hexdigest() != meta[hash_key]:
            raise ValueError(f"Index checksum mismatch: {filename}")
        return json.loads(data)

    chunks = checked_json("chunks.json", "chunks_sha256")
    if "bm25_sha256" in meta:
        snapshot = checked_json("bm25.json", "bm25_sha256")
        bm25 = BM25Index(**snapshot, **meta["bm25"])
    else:
        # Existing installations published token rows. Rebuild their postings on load.
        tokens = checked_json("tokens.json", "tokens_sha256")
        bm25 = BM25Index.build(tokens, **meta["bm25"])

    if not chunks or len(chunks) != len(bm25.lengths) or len(chunks) != meta["count"]:
        raise ValueError("Empty or inconsistent index")

    return {
        "meta": meta,
        "chunks": chunks,
        "bm25": bm25,
        "commands": {chunk["command"] for chunk in chunks},
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.store = None
    app.state.embedder = None
    runtime = os.getenv("RUNTIME_DIR")
    if runtime:
        logger.info("Загрузка модели multilingual-e5-small.")
        from app.embedding import E5
        embedder = E5(Path(os.environ["EMBEDDING_DIR"]))
        logger.info("Подготовка поискового индекса.")
        store = CorpusStore(
            Path(runtime), Path(os.getenv("SEED_CORPUS", str(ROOT / "corpus"))),
            embedder, load_index,
        )
        app.state.index = await run_in_threadpool(store.load)
        app.state.store = store
        app.state.embedder = embedder
        logger.info("Индекс готов: %d фрагментов.", len(app.state.index["chunks"]))
    else:
        try:
            app.state.index = load_index()
        except (OSError, ValueError):
            app.state.index = None
            logger.exception("Ошибка загрузки индекса")

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
        "Проверь поля query, distribution, top_k"
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

    available = {item["distribution"] for item in index["meta"]["supported_targets"]}
    distributions = [
        {"id": key, "label": name}
        for key, name in DISTRIBUTIONS.items()
        if key in available
    ]

    return {
        "corpus_version": index["meta"]["corpus_version"],
        "distributions": distributions
    }


PACKAGE_MANAGERS = {"debian": "apt", "fedora": "dnf", "arch": "pacman"}
PACKAGE_TERMS = set(tokenize("пакет пакеты репозиторий репозитории"))
UPGRADE_TERMS = set(tokenize("обновить обновление обновлять обнови обновляется"))


def retrieve(index, query, target, embedder=None):
    ranked = search(
        query,
        index["chunks"],
        index["bm25"],
        top_k=len(index["chunks"])
    )

    # Явно указанная команда должна присутствовать в корпусе выбранной системы.
    terms = set(tokenize(query))
    named_commands = index["commands"].intersection(terms)
    distribution = target["distribution"]
    compatible = [
        item
        for item in ranked
        if any(saved["distribution"] == distribution for saved in item["applies_to"])
        and (item["command"] in named_commands if named_commands else not item.get("equivalent_only"))
    ]


    if embedder:
        compatible = embedder.rerank(query, compatible[:20], index["vectors"])

    if not named_commands and terms & PACKAGE_TERMS and terms & UPGRADE_TERMS:
        package_command = PACKAGE_MANAGERS.get(distribution)
        compatible.sort(key=lambda item: item["command"] != package_command)
    return compatible


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

    target = {"distribution": payload.distribution}
    supported = any(
        item["distribution"] == payload.distribution for item in index["meta"]["supported_targets"]
    )

    if payload.distribution not in DISTRIBUTIONS or not supported:
        return error(
            422,
            "UNSUPPORTED_TARGET",
            "Нет проверенного корпуса для выбранной системы"
        )

    compatible = retrieve(index, payload.query, target, request.app.state.embedder)

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
            "package_version": item["package_version"],
            "section": item["section"],
            "applies_to": [{"distribution": target["distribution"]} for target in item["applies_to"]],
        }

        if item["collected_at"]:
            result["collected_at"] = item["collected_at"]

        items.append(result)

    return {
        "corpus_version": index["meta"]["corpus_version"],
        "items": items
    }


@app.get("/v1/admin/documents")
def documents(request: Request):
    index = request.app.state.index
    if request.app.state.store is None or index is None:
        return error(503, "INDEX_NOT_READY", "Индекс недоступен для записи.")
    keys = ("document_id", "package", "package_version", "source_url", "collected_at", "verified_targets")
    items = [{key: item.get(key) or ([] if key == "verified_targets" else "") for key in keys} for item in index["documents"]]
    for item in items:
        item["verified_targets"] = [{"distribution": value["distribution"]} for value in item["verified_targets"]]
    return {"corpus_version": index["meta"]["corpus_version"], "items": items}


def activate_document(app, document, content):
    store = app.state.store
    with store.lock:
        previous = app.state.index
        snapshot = store.publish(previous["corpus"], previous, document, content)
        app.state.index = snapshot
        return snapshot["meta"]["corpus_version"]


@app.post("/v1/admin/documents")
async def upload_document(request: Request):
    if request.app.state.store is None or request.app.state.index is None:
        return error(503, "INDEX_NOT_READY", "Индекс недоступен для записи.")
    try:
        async with request.form(max_files=1, max_fields=7, max_part_size=8192) as form:
            uploaded = form.get("file")
            if not isinstance(uploaded, UploadFile) or not (uploaded.filename or "").lower().endswith(".md"):
                return error(400, "INVALID_FILE", "Выберите Markdown-файл с расширением .md.")
            data = await uploaded.read(MAX_UPLOAD + 1)
            if len(data) > MAX_UPLOAD:
                return error(413, "FILE_TOO_LARGE", "Размер Markdown-файла ограничен 512 КиБ.")
            document, content = validate(form, data)
        version = await run_in_threadpool(activate_document, request.app, document, content)
    except DocumentExists as exc:
        return error(409, "DOCUMENT_EXISTS", str(exc))
    except InvalidDocument as exc:
        return error(422, "INVALID_DOCUMENT", str(exc))
    except HTTPException:
        return error(400, "INVALID_FILE", "Проверьте формат формы загрузки.")
    except Exception:
        logger.exception("Ошибка публикации документа")
        return error(503, "INDEX_UPDATE_FAILED", "Не удалось опубликовать новую версию корпуса.")
    return JSONResponse(status_code=201, content={
        "document_id": document["document_id"], "corpus_version": version,
    })
