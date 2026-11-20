"""Локальный просмотр чернового корпуса. Не подключать к production/Go."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.api import load_index
from bm25_demo import search


class PreviewRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=5, ge=1, le=10)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        app.state.index = load_index()
    except (OSError, ValueError, KeyError) as exc:
        print(f"Не удалось загрузить индекс: {exc}")
        app.state.index = None
    yield


app = FastAPI(
    title="CommandWise — черновой поиск (только локально)",
    lifespan=lifespan,
)


@app.get("/ready")
def ready(request: Request):
    if request.app.state.index is None:
        return JSONResponse(
            status_code=503,
            content={"status": "index_not_ready"},
        )

    return {"status": "ready"}


@app.post("/dev/search")
def preview(payload: PreviewRequest, request: Request):
    index = request.app.state.index

    if index is None:
        return JSONResponse(
            status_code=503,
            content={"error": "index_not_ready"},
        )

    if not payload.query.strip():
        return JSONResponse(
            status_code=422,
            content={"error": "empty_query"},
        )

    ranked = search(
        payload.query,
        index["chunks"],
        index["bm25"],
        top_k=payload.top_k,
    )

    items = [
        {
            "chunk_id": item["chunk_id"],
            "document_id": item["document_id"],
            "section": item["section"],
            "text": item["text"],
            "source_url": item["source_url"],
            "bm25_score": item["bm25_score"],
            "rank_score": item["final_score"],
        }
        for item in ranked
    ]

    return {
        "status": "draft_unverified",
        "warning": "Демонстрационный поиск: версии Linux ещё не подтверждены.",
        "corpus_version": index["meta"]["corpus_version"],
        "items": items,
    }
