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
    bm25, tokens = build_index(chunks)

    results = search(
        "Как изменить права доступа?",
        chunks,
        bm25,
        tokens,
    )

    assert len(results) > 0
    assert results[0]["command"] == "chmod"


def test_no_matches():
    chunks = load_chunks()
    bm25, tokens = build_index(chunks)

    results = search(
        "квантовая запутанность фотонов",
        chunks,
        bm25,
        tokens,
    )

    assert results == []

def test_mixed_language_hyphen():
    assert tokenize("Python-файлах") == tokenize("Python файлах")
    assert tokenize("Linux-команды") == tokenize("Linux команды")
