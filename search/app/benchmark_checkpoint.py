"""Reproducible 30-document RAG evaluation for the course checkpoint."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from statistics import mean
from time import perf_counter
from urllib.request import Request, urlopen

from bm25_demo import build_index
from app.api import retrieve


ROOT = Path(__file__).resolve().parents[2]
BENCHMARK = ROOT / "benchmark"
TARGET = {"distribution": "debian", "release": "13"}


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def file_hash(path):
    return sha256(path.read_bytes()).hexdigest()


def answer_hash(answer):
    return sha256(answer.encode("utf-8")).hexdigest()


def dataset():
    docs = read_jsonl(BENCHMARK / "corpus.jsonl")
    questions = read_jsonl(BENCHMARK / "questions.jsonl")
    ids = {doc["id"] for doc in docs}
    if len(docs) != 30 or ids != {f"D{i:02}" for i in range(1, 31)}:
        raise ValueError("Corpus must contain exactly D01–D30")
    if len({doc["chunk_id"] for doc in docs}) != 30 or any(TARGET not in doc["applies_to"] for doc in docs):
        raise ValueError("Corpus must contain unique verified chunks for Debian 13")
    if {q["id"] for q in questions} != {f"Q{i:02}" for i in range(1, 16)} or len(questions) != 15:
        raise ValueError("Questions must contain exactly Q01–Q15")
    if sum(q["answerable"] for q in questions) != 10:
        raise ValueError("Expected ten answerable and five unanswerable questions")
    for question in questions:
        gold = question["gold_document_ids"]
        if len(set(gold)) != len(gold) or not set(gold) <= ids or not question["reference_answer"].strip():
            raise ValueError(f"Invalid gold for {question['id']}")
        if (question["answerable"] and len(gold) < 3) or (not question["answerable"] and gold):
            raise ValueError(f"Invalid number of relevant documents for {question['id']}")
    return docs, questions


def fingerprints():
    source_files = {
        "corpus": BENCHMARK / "corpus.jsonl",
        "questions": BENCHMARK / "questions.jsonl",
        "prompt": ROOT / "backend" / "rag_system.txt",
        "bm25": ROOT / "search" / "bm25_index.py",
        "lexical_rules": ROOT / "search" / "bm25_demo.py",
        "retrieval": ROOT / "search" / "app" / "api.py",
        "embedding": ROOT / "search" / "app" / "embedding.py",
    }
    return {name: file_hash(path) for name, path in source_files.items()}


def retrieval_metrics(rows, method):
    recalls = []
    reciprocal_ranks = []
    for row in rows:
        gold = set(row["gold_document_ids"])
        if not gold:
            continue
        returned = [hit["id"] for hit in row[method]["hits"]]
        recalls.append(len(gold.intersection(returned)) / len(gold))
        reciprocal_ranks.append(next((1 / rank for rank, doc_id in enumerate(returned, 1) if doc_id in gold), 0))
    return {"recall": round(mean(recalls), 6), "mrr": round(mean(reciprocal_ranks), 6)}


def retrieve_hits(index, query, k, embedder=None):
    start = perf_counter()
    hits = retrieve(index, query, TARGET, embedder)[:k]
    elapsed = round((perf_counter() - start) * 1000, 2)
    return {
        "hits": [{"id": hit["id"], "chunk_id": hit["chunk_id"], "score": round(hit["final_score"], 6)} for hit in hits],
        "elapsed_ms": elapsed,
    }


def prepare(args):
    from app.embedding import E5

    docs, questions = dataset()
    bm25, _ = build_index(docs)
    embedder = E5(args.embedding_dir)
    vectors = embedder.index(docs)
    index = {
        "chunks": docs, "bm25": bm25, "commands": {doc["command"] for doc in docs},
        "vectors": {doc["chunk_id"]: vector for doc, vector in zip(docs, vectors)},
    }
    rows = []
    for question in questions:
        query = question["query"]
        rows.append({
            **question,
            "bm25": retrieve_hits(index, query, args.k),
            "hybrid": retrieve_hits(index, query, args.k, embedder),
        })
    save_json(args.output, {
        "target": TARGET,
        "k": args.k,
        "fingerprints": fingerprints(),
        "embedder": "intfloat/multilingual-e5-small ONNX",
        "retrieval_metrics": {mode: retrieval_metrics(rows, mode) for mode in ("bm25", "hybrid")},
        "rows": rows,
    })
    print(f"Search ran on 30 indexed documents and 15 questions. Saved {args.output}", flush=True)


def request_json(base, path, payload=None):
    request = Request(
        base.rstrip("/") + path,
        data=None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=240) as response:
        return json.load(response)


def generate(args):
    docs, _ = dataset()
    docs = {doc["id"]: doc for doc in docs}
    report = read_json(args.retrieval)
    if report["fingerprints"] != fingerprints():
        raise ValueError("Benchmark inputs changed. Run prepare again.")
    models = request_json(args.llm_url, "/v1/models")
    if args.model not in {model["id"] for model in models["data"]}:
        raise ValueError(f"Server does not advertise model {args.model}")

    template = (ROOT / "backend" / "rag_system.txt").read_text(encoding="utf-8") % TARGET["distribution"]
    report["model"] = args.model
    report["generation"] = {"temperature": 0, "seed": 42, "max_tokens": args.max_tokens, "reasoning": "off", "jobs": args.jobs}
    report["started_at"] = datetime.now(timezone.utc).isoformat()
    report["model_report"] = models["data"]

    def generate_row(row):
        start = perf_counter()
        hits = row[args.method]["hits"]
        row["model_input_documents"] = [hit["id"] for hit in hits]
        row["generation_method"] = args.method
        if hits:
            sources = [docs[hit["id"]] for hit in hits]
            excerpts = "".join(
                f"\n[{ref}] {doc['title']} — {doc['section']}\n{doc['text']}\n"
                for ref, doc in enumerate(sources, 1)
            )
            messages = [
                {"role": "system", "content": template + excerpts + "\nОтветь по возможности кратко."},
                {"role": "user", "content": row["query"]},
            ]
            result = request_json(args.llm_url, "/v1/chat/completions", {
                "model": args.model,
                "messages": messages,
                "temperature": 0,
                "seed": 42,
                "max_tokens": args.max_tokens,
                "chat_template_kwargs": {"enable_thinking": False},
            })
            choice = result["choices"][0]
            answer = (choice["message"]["content"] or "").strip()
            finish = choice["finish_reason"]
            row["usage"] = result.get("usage")
        else:
            answer = "В проверенной документации для этой системы подходящих сведений не найдено. Уточните команду или задачу."
            finish = "no_context"
        row["answer"] = answer
        row["finish_reason"] = finish
        row["answer_sha256"] = answer_hash(answer)
        row["generation_ms"] = round((perf_counter() - start) * 1000, 2)
        return row

    indexed_rows = report["rows"]
    report["rows"] = []
    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        for row in executor.map(generate_row, indexed_rows):
            report["rows"].append(row)
            save_json(args.output, report)
            print(f"{row['id']} {row['finish_reason']} {row['generation_ms']:.0f} ms | {row['answer'][:160]}", flush=True)
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    save_json(args.output, report)


def score(args):
    report = read_json(args.answers)
    if "finished_at" not in report:
        raise ValueError("The generation run is incomplete")
    if any(report["fingerprints"].get(key) != fingerprints()[key] for key in ("corpus", "questions")):
        raise ValueError("Benchmark dataset does not match the generation run")
    rows = report["rows"]
    reviews = read_jsonl(args.review)
    verified = {item["id"]: item for item in reviews}
    if len(reviews) != len(rows) or set(verified) != {row["id"] for row in rows}:
        raise ValueError("Provide one manual review for each answer")
    for row in rows:
        review = verified[row["id"]]
        if review["answer_sha256"] != answer_hash(row["answer"]) or type(review["correct"]) is not bool:
            raise ValueError(f"Review does not match the answer for {row['id']}")
        row["review"] = review
    positive = [row for row in rows if row["answerable"]]
    traps = [row for row in rows if not row["answerable"]]
    report["retrieval_metrics"] = {mode: retrieval_metrics(rows, mode) for mode in ("bm25", "hybrid")}
    report["answer_metrics"] = {
        "accuracy": mean(row["review"]["correct"] for row in positive),
        "correct_rejection_rate": mean(row["review"]["correct"] for row in traps),
    }
    save_json(args.output, report)
    print(json.dumps({
        "k": report["k"], "retrieval": report["retrieval_metrics"],
        "answers": report["answer_metrics"],
    }, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    stages = parser.add_subparsers(dest="stage", required=True)
    retrieval = stages.add_parser("prepare", help="run BM25 and BM25 + E5")
    retrieval.add_argument("--embedding-dir", type=Path, required=True)
    retrieval.add_argument("--k", type=int, choices=range(1, 11), default=5)
    retrieval.add_argument("--output", type=Path, required=True)
    generation = stages.add_parser("generate", help="send the retrieved contexts to llama.cpp")
    generation.add_argument("--retrieval", type=Path, required=True)
    generation.add_argument("--llm-url", required=True)
    generation.add_argument("--model", default="qwen3-14b")
    generation.add_argument("--method", choices=("bm25", "hybrid"), default="hybrid")
    generation.add_argument("--max-tokens", type=int, default=144)
    generation.add_argument("--jobs", type=int, choices=range(1, 9), default=1)
    generation.add_argument("--output", type=Path, required=True)
    review = stages.add_parser("score", help="calculate final metrics from manual reviews")
    review.add_argument("--answers", type=Path, required=True)
    review.add_argument("--review", type=Path, required=True)
    review.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    {"prepare": prepare, "generate": generate, "score": score}[args.stage](args)


if __name__ == "__main__":
    main()
