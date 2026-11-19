import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

from app.api import load_index
from bm25_demo import search


ROOT = Path(__file__).resolve().parents[2]

QUESTIONS = (
    ROOT / "benchmark" / "questions_sections_dev.jsonl"
)

OUTPUT = (
    ROOT / "benchmark" / "results" / "sections-dev.json"
)


def get_key(item):
    return (
        item["command"],
        item["section"].strip().casefold(),
    )


def main():
    index = load_index()

    available = {
        get_key(item)
        for item in index["chunks"]
    }

    questions = [
        json.loads(line)
        for line in QUESTIONS.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]

    results = []
    durations = []

    for question in questions:
        gold = {
            get_key(item)
            for item in question["gold"]
        }

        # Проверяем правильность ручной разметки.
        missing = gold - available

        if missing:
            raise ValueError(
                f"{question['id']}: в корпусе "
                f"нет разделов {missing}"
            )

        start = time.perf_counter()

        found = search(
            question["query"],
            index["chunks"],
            index["bm25"],
            index["tokens"],
            top_k=5,
        )

        elapsed = (
            time.perf_counter() - start
        ) * 1000

        durations.append(elapsed)

        returned = [
            get_key(item)
            for item in found
        ]

        matched = gold.intersection(returned)

        ranks = [
            returned.index(key) + 1
            for key in matched
        ]

        first_rank = min(ranks) if ranks else None

        recall = (
            len(matched) / len(gold)
            if gold else None
        )

        results.append({
            "id": question["id"],
            "query": question["query"],
            "answerable": bool(gold),
            "gold": question["gold"],
            "first_gold_rank": first_rank,
            "recall_at_5": recall,
            "correct_empty": not gold and not found,
            "latency_ms": round(elapsed, 2),
            "returned": [
                {
                    "command": item["command"],
                    "section": item["section"],
                    "chunk_id": item["chunk_id"],
                    "score": round(
                        item["final_score"], 4
                    ),
                }
                for item in found
            ],
        })

    positive = [
        item for item in results
        if item["answerable"]
    ]

    negative = [
        item for item in results
        if not item["answerable"]
    ]

    recall5 = statistics.mean(
        item["recall_at_5"]
        for item in positive
    )

    hit5 = statistics.mean(
        item["first_gold_rank"] is not None
        for item in positive
    )

    mrr5 = statistics.mean(
        1 / item["first_gold_rank"]
        if item["first_gold_rank"] else 0
        for item in positive
    )

    times = sorted(durations)
    p95 = times[
        max(0, (95 * len(times) + 99) // 100 - 1)
    ]

    metrics = {
        "recall_at_5": round(recall5, 4),
        "hit_at_5": round(hit5, 4),
        "mrr_at_5": round(mrr5, 4),
        "correct_empty": sum(
            item["correct_empty"]
            for item in negative
        ),
        "negative_count": len(negative),
        "latency_median_ms": round(
            statistics.median(times), 2
        ),
        "latency_p95_ms": round(p95, 2),
    }

    report = {
        "corpus_version": (
            index["meta"]["corpus_version"]
        ),
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "mode": "draft_all_commands_no_target_filter",
        "question_count": len(results),
        "metrics": metrics,
        "results": results,
    }

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    OUTPUT.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    print(f"Вопросов: {len(results)}")
    print(f"Recall@5: {recall5:.1%}")
    print(f"Hit@5: {hit5:.1%}")
    print(f"MRR@5: {mrr5:.3f}")

    print(
        "Корректно пустых ответов: "
        f"{metrics['correct_empty']}/"
        f"{len(negative)}"
    )

    print(
        f"Latency median: "
        f"{metrics['latency_median_ms']} ms"
    )
    print(
        f"Latency p95: "
        f"{metrics['latency_p95_ms']} ms"
    )

    print("\nВопросы с проблемами:")

    problems = 0

    for item in results:
        bad = (
            item["recall_at_5"] is not None
            and item["recall_at_5"] < 1
        ) or (
            not item["answerable"]
            and not item["correct_empty"]
        )

        if not bad:
            continue

        problems += 1

        print(
            f"\n{item['id']}: {item['query']}"
        )

        print("Найденные разделы:")

        for found in item["returned"]:
            print(
                f"  {found['command']}: "
                f"{found['section']}"
            )

    if problems == 0:
        print("Проблем в этом наборе не обнаружено.")

    print(f"\nОтчёт: {OUTPUT}")


if __name__ == "__main__":
    main()
