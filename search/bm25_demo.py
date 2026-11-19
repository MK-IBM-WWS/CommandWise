
from pathlib import Path
import re

from nltk.stem.snowball import SnowballStemmer
from rank_bm25 import BM25Okapi


DOCS_DIR = Path(__file__).resolve().parents[1] / "corpus" / "docs"

stemmer = SnowballStemmer("russian")

TITLE_WEIGHT = 4.0
SECTION_WEIGHT = 3.0

SKIP_SECTIONS = {
    "источники",
    "применимость",
    "проверка применимости",
}

STOPWORDS = {
    "как", "что", "можно", "нужно", "мне",
    "в", "на", "по", "и", "для", "с",
    "пожалуйста",
}

TOKEN_PATTERN = re.compile(
    r"--[A-Za-z][A-Za-z0-9-]*(?:=[^\s]+)?"
    r"|(?<!\w)-[A-Za-z][A-Za-z0-9]*"
    r"|(?:~/|/)[^\s`\"'<>|;()]+"
    r"|[А-Яа-яЁё]+"
    r"|[A-Za-z][A-Za-z0-9_]*(?:-[A-Za-z0-9_]+)*"
    r"|[+-]?\d+[KMG]?"
)


def tokenize(text):
    """Обработка текста для поиска."""
    result = []

    for token in TOKEN_PATTERN.findall(text):
        if re.fullmatch(r"[А-Яа-яЁё]+", token):
            token = stemmer.stem(
                token.lower().replace("ё", "е")
            )
        elif not token.startswith(("-", "/", "~/")):
            token = token.lower()

        result.append(token)

    return result


STOP_TOKENS = set(tokenize(" ".join(STOPWORDS)))
# Небольшой словарь проверяемых смысловых соответствий.
# Он помогает находить похожие по смыслу формулировки.

SYNONYM_GROUPS = [
    ("посчитать", "подсчитать", "подсчёт"),
    ("повторяющиеся", "повторения", "дубликаты", "одинаковые"),
    ("объединить", "объединение", "соединить"),
    ("папка", "каталог", "директория"),
    ("исполняемый", "выполнение", "запустить"),
]

SYNONYM_TOKENS = [
    set(tokenize(" ".join(group)))
    for group in SYNONYM_GROUPS
]


def expand_query(tokens):
    """Добавляет близкие поисковые формулировки."""
    expanded = set(tokens)

    for group in SYNONYM_TOKENS:
        if tokens & group:
            expanded.update(group)

    return expanded


def split_sections(content):
    """Деление Markdown по заголовкам без разрыва блоков кода."""
    heading = None
    lines = []
    fence = None

    for line in content.splitlines():
        stripped = line.lstrip()

        is_fence = stripped.startswith(("```", "~~~"))

        if fence is None and not is_fence:
            if re.match(r"^#{2,3} ", line):
                if heading is not None:
                    yield heading, "\n".join(lines).strip()

                heading = line.lstrip("# ").strip()
                lines = [line]
                continue

        if heading is not None:
            lines.append(line)

        if is_fence:
            marker = stripped[:3]

            if fence is None:
                fence = marker
            elif fence == marker:
                fence = None

    if heading is not None:
        yield heading, "\n".join(lines).strip()


def load_chunks():
    """Загрузка документации из отдельных файлов."""
    chunks = []

    for file in sorted(DOCS_DIR.glob("*.md")):
        content = file.read_text(encoding="utf-8")

        title = next(
            (
                line[2:].strip()
                for line in content.splitlines()
                if line.startswith("# ")
            ),
            file.stem,
        )

        for heading, text in split_sections(content):
            if heading.lower() in SKIP_SECTIONS:
                continue

            if not text.strip():
                continue

            chunks.append({
                "command": file.stem,
                "title": title,
                "section": heading,
                "text": text,
                "search_text": (
                    f"{file.stem} {heading} {text}"
                ),
            })

    return chunks


def build_index(chunks):
    """Создание BM25-индекса."""
    tokens = [
        tokenize(chunk["search_text"])
        for chunk in chunks
    ]

    bm25 = BM25Okapi(
        tokens,
        k1=1.5,
        b=0.75,
    )

    return bm25, tokens


def search(query, chunks, bm25, tokens, top_k=5):
    """BM25 с расширением запроса и учётом заголовков."""

    original_tokens = (
        set(tokenize(query)) - STOP_TOKENS
    )

    if not original_tokens:
        return []

    query_tokens = expand_query(original_tokens)

    scores = bm25.get_scores(
        sorted(query_tokens)
    )

    results = []

    for i, chunk in enumerate(chunks):
        chunk_tokens = set(tokens[i])

        # Нужны хотя бы какие-то совпадения
        # с исходным вопросом.
        if not (original_tokens & chunk_tokens):
            continue

        # Учитываем заголовок всего документа.
        title_tokens = set(
            tokenize(chunk["title"])
        )

        title_matches = (
            query_tokens & title_tokens
        )

        title_bonus = (
            TITLE_WEIGHT * len(title_matches)
        )

        # Дополнительно учитываем название
        # конкретного раздела документа.
        section_tokens = set(
            tokenize(chunk["section"])
        )

        section_matches = (
            query_tokens & section_tokens
        )

        section_bonus = (
            SECTION_WEIGHT * len(section_matches)
        )

        final_score = (
            float(scores[i])
            + title_bonus
            + section_bonus
        )

        results.append({
            **chunk,
            "bm25_score": float(scores[i]),
            "title_bonus": title_bonus,
            "section_bonus": section_bonus,
            "final_score": final_score,
        })

    results.sort(
        key=lambda item: (
            -item["final_score"],
            item["command"],
            item["section"],
        )
    )

    return results[:top_k]


def main():
    chunks = load_chunks()

    if not chunks:
        print("Документация не найдена.")
        return

    bm25, tokens = build_index(chunks)

    print(f"Загружено документов: {len(list(DOCS_DIR.glob('*.md')))}")
    print(f"Создано фрагментов: {len(chunks)}")
    print("Поиск готов. Для выхода введи exit.")

    while True:
        query = input("\nВопрос: ").strip()

        if query.lower() == "exit":
            break

        if not query:
            continue

        results = search(query, chunks, bm25, tokens)

        if not results:
            print("Подходящих фрагментов не найдено.")
            continue

        print("\nЛучшие результаты:")

        for rank, item in enumerate(results, start=1):
            print(f"\n--- Результат {rank} ---")
            print(f"Команда: {item['command']}")
            print(f"Раздел: {item['section']}")
            print(f"BM25: {item['bm25_score']:.3f}")
            print(f"Бонус заголовка: {item['title_bonus']:.3f}")
            print(f"Итоговый балл: {item['final_score']:.3f}")
            print(item["text"][:400])


if __name__ == "__main__":
    main()
