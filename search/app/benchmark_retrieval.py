"""Промежуточный benchmark по командам, без проверки target и LLM."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time

from app.api import load_index
from bm25_demo import search


ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--questions",
        type=Path,
        default=ROOT / "benchmark" / "questions_dev.jsonl",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "benchmark" / "results" / "retrieval-dev.json",
    )

    args = parser.parse_args()

    index = load_index()
    rows = []

    for line in args.questions.read_text(
        encoding="utf-8"
    ).splitlines():

        if not line.strip():
            continue

        question = json.loads(line)
        expected = question["expected_command"]

        start = time.perf_counter()

        matches = search(
            question["query"],
            index["chunks"],
            index["bm25"],
            index["tokens"],
            top_k=5,
        )

        elapsed_ms = round(
            (time.perf_counter() - start) * 1000,
            2,
        )

        returned = [
            item["document_id"]
            for item in matches
        ]

        rank = (
            returned.index(expected) + 1
            if expected in returned
            else None
        )

        rows.append({
            "id": question["id"],
            "query": question["query"],
            "expected_command": expected,
            "returned_commands": returned,
            "returned_chunk_ids": [
                item["chunk_id"] for item in matches
            ],
            "first_correct_rank": rank,
            "latency_ms": elapsed_ms,
            "correct_empty": (
                expected is None and not matches
            ),
        })

    positive = [
        row for row in rows
        if row["expected_command"] is not None
    ]

    negative = [
        row for row in rows
        if row["expected_command"] is None
    ]

    if not positive:
        raise ValueError("Нет вопросов с ожидаемой командой")

    hit_at_1 = sum(
        row["first_correct_rank"] == 1
        for row in positive
    ) / len(positive)

    hit_at_5 = sum(
        row["first_correct_rank"] is not None
        for row in positive
    ) / len(positive)

    mrr_at_5 = sum(
        1 / row["first_correct_rank"]
        if row["first_correct_rank"]
        else 0
        for row in positive
    ) / len(positive)

    report = {
        "note": (
            "Черновой benchmark: проверяется команда, "
            "не gold chunk/section и не совместимость Linux."
        ),
        "corpus_version": index["meta"]["corpus_version"],
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "questions": len(rows),
        "answerable": len(positive),
        "unanswerable": len(negative),
        "hit_at_1_by_command": round(hit_at_1, 3),
        "hit_at_5_by_command": round(hit_at_5, 3),
        "mrr_at_5_by_command": round(mrr_at_5, 3),
        "correct_empty_count": sum(
            row["correct_empty"] for row in negative
        ),
        "rows": rows,
    }

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.output.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    print(f"Вопросов: {len(rows)}")
    print(f"Hit@1: {hit_at_1:.1%}")
    print(f"Hit@5: {hit_at_5:.1%}")
    print(f"MRR@5: {mrr_at_5:.3f}")

    print(
        "Без ответа, корректно пусто: "
        f"{report['correct_empty_count']}/{len(negative)}"
    )

    print(f"Отчёт: {args.output}")
    print("Неудачные вопросы:")

    for row in positive:
        if (
            row["first_correct_rank"] is None
            or row["first_correct_rank"] > 1
        ):
            print(
                f"  {row['id']}: {row['query']} "
                f"(место {row['first_correct_rank']})"
            )


if __name__ == "__main__":
    main()
