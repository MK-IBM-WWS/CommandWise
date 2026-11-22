import json
from pathlib import Path
import shutil

import numpy as np
import pytest

from app.api import load_index, retrieve
from app.corpus_store import CorpusStore


class TestEmbeddings:
    __test__ = False
    dimensions = 1

    def index(self, chunks, previous):
        return np.zeros((len(chunks), self.dimensions), dtype=np.float32)


def test_seed_update_keeps_uploaded_docs_and_renames_collisions(tmp_path):
    source = Path(__file__).resolve().parents[2] / "corpus"
    old = tmp_path / "old-seed"
    (old / "docs").mkdir(parents=True)
    shutil.copyfile(source / "docs" / "cat.md", old / "docs" / "cat.md")
    manifest = {
        "supported_targets": [{"distribution": "debian", "release": "13", "label": "Debian 13"}],
        "documents": [{
            "document_id": "cat", "path": "docs/cat.md", "verified_targets": [{"distribution": "debian", "release": "13"}],
            "source_url": "https://example.org/cat",
        }],
    }
    (old / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    runtime = tmp_path / "runtime"
    embedder = TestEmbeddings()
    older = CorpusStore(runtime, old, embedder, load_index)
    uploaded = {
        "document_id": "ping", "path": "docs/ping.md",
        "verified_targets": [{"distribution": "fedora", "release": "44"}],
        "source_url": "https://example.org/ping",
    }
    initial = older.load()
    older.publish(initial["corpus"], initial, uploaded, "# ping\n\n## Локальная заметка\n\nПроверка учебного стенда.\n")

    new = tmp_path / "new-seed"
    shutil.copytree(source, new)
    (new / "docs" / "nano.md").write_text("# Устаревшая инструкция\n", encoding="utf-8")
    latest = CorpusStore(runtime, new, embedder, load_index)
    upgraded = latest.load()
    assert len(upgraded["documents"]) == 51
    assert not (upgraded["corpus"] / "docs" / "nano.md").exists()
    assert len(upgraded["meta"]["supported_targets"]) == 3
    assert latest.load()["corpus"] == upgraded["corpus"]
    renamed = next(item for item in upgraded["documents"] if item["document_id"] == "ping-uploaded-1")
    assert renamed["verified_targets"] == [{"distribution": "fedora"}]
    matches = retrieve(upgraded, "ping учебного стенда", {"distribution": "fedora"})
    assert matches[0]["document_id"] == "ping-uploaded-1"


def test_startup_skips_markdown_left_from_an_older_checkout(tmp_path, caplog):
    seed = tmp_path / "seed"
    shutil.copytree(Path(__file__).resolve().parents[2] / "corpus", seed)
    leftovers = {"tee", "cd", "nano", "pwd", "ln", "stat", "sed", "touch", "echo", "less"}
    for name in leftovers:
        (seed / "docs" / f"{name}.md").write_text("# Старая инструкция\n", encoding="utf-8")

    store = CorpusStore(tmp_path / "runtime", seed, TestEmbeddings(), load_index)
    snapshot = store.load()

    assert len(snapshot["documents"]) == 50
    saved_ids = {path.stem for path in (snapshot["corpus"] / "docs").glob("*.md")}
    assert saved_ids == {entry["document_id"] for entry in snapshot["documents"]}
    assert all((seed / "docs" / f"{name}.md").is_file() for name in leftovers)
    assert all(f"{name}.md" in caplog.text for name in leftovers)


def test_startup_reports_a_missing_manifest_file(tmp_path):
    seed = tmp_path / "seed"
    shutil.copytree(Path(__file__).resolve().parents[2] / "corpus", seed)
    (seed / "docs" / "cat.md").unlink()
    store = CorpusStore(tmp_path / "runtime", seed, TestEmbeddings(), load_index)

    with pytest.raises(ValueError, match=r"Отсутствуют файлы встроенного корпуса: cat\.md"):
        store.load()
    assert not store.pointer.exists()


@pytest.mark.parametrize("damaged_file", ["index/current.json", "vectors.npy"])
def test_damaged_index_is_rebuilt_from_the_published_corpus(tmp_path, damaged_file):
    seed = Path(__file__).resolve().parents[2] / "corpus"
    store = CorpusStore(tmp_path, seed, TestEmbeddings(), load_index)
    initial = store.load()
    document = {
        "document_id": "example-tool",
        "path": "docs/example-tool.md",
        "verified_targets": [{"distribution": "fedora"}],
        "source_url": "https://example.org/example-tool",
    }
    published = store.publish(
        initial["corpus"], initial, document,
        "# example-tool\n\n## Пример\n\nПоказывает зелёные яблоки.\n",
    )
    damaged = published["corpus"].parent
    (damaged / damaged_file).write_bytes(b"damaged")

    restored = store.load()
    assert restored["corpus"].parent != damaged
    assert restored["meta"]["corpus_version"] == published["meta"]["corpus_version"]
    assert damaged.is_dir()
    assert store.load()["corpus"] == restored["corpus"]
    results = retrieve(restored, "пример example-tool", {"distribution": "fedora"})
    assert results[0]["document_id"] == "example-tool"
