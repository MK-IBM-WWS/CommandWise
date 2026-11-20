from bm25_demo import (
    tokenize,
    load_chunks,
    build_index,
    search,
)


def test_russian_stemming():
    assert tokenize("файлы") == tokenize("файлов")


def test_flags_case():
    tokens = tokenize("grep -r -R --exclude-dir")

    assert "-r" in tokens
    assert "-R" in tokens
    assert "--exclude-dir" in tokens


def test_documents_loaded():
    chunks = load_chunks()
    commands = {chunk["command"] for chunk in chunks}

    assert {
        "ls", "find", "grep", "chmod", "tar"
    } <= commands


def test_chmod_search():
    chunks = load_chunks()
    bm25, _ = build_index(chunks)

    results = search(
        "Как изменить права доступа?",
        chunks,
        bm25,
    )

    assert len(results) > 0
    assert results[0]["command"] == "chmod"


def test_no_matches():
    chunks = load_chunks()
    bm25, _ = build_index(chunks)

    results = search(
        "квантовая запутанность фотонов",
        chunks,
        bm25,
    )

    assert results == []

def test_mixed_language_hyphen():
    assert tokenize("Python-файлах") == tokenize("Python файлах")
    assert tokenize("Linux-команды") == tokenize("Linux команды")


def test_bm25_matches_hand_calculation_and_snapshot(tmp_path):
    from json import dumps, loads
    from math import log1p

    import pytest

    from bm25_index import BM25Index

    docs = [
        ["возврат", "оплаты", "на", "карту"],
        ["статус", "оплаты", "в", "приложении"],
        ["возврат", "билета", "по", "правилам"],
    ]
    index = BM25Index.build(docs, k1=1.2)
    snapshot = tmp_path / "bm25.json"
    snapshot.write_text(dumps(index.snapshot()), encoding="utf-8")
    restored = BM25Index(**loads(snapshot.read_text(encoding="utf-8")), k1=1.2)

    common_idf = log1p((3 - 2 + 0.5) / (2 + 0.5))
    expected = {0: 2 * common_idf, 1: common_idf, 2: common_idf}
    assert index.score(["возврат", "оплаты"]) == pytest.approx(expected)
    assert restored.score(["возврат", "возврат", "оплаты"]) == pytest.approx(expected)
    assert restored.matching_documents(["оплаты"]) == {0, 1}
    assert restored.score(["неизвестный"]) == {}


def test_bm25_normalizes_length_and_saturates_frequency():
    from math import log1p

    import pytest

    from bm25_index import BM25Index

    index = BM25Index.build([["term", "term"], ["term", "padding", "padding", "padding"]], k1=1.2, b=0.75)
    common_idf = log1p(0.5 / 2.5)
    assert index.score(["term"]) == pytest.approx({0: common_idf * 4.4 / 2.9, 1: common_idf * 2.2 / 2.5})
