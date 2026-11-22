import json
from pathlib import Path
import shutil

import numpy as np

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

    latest = CorpusStore(runtime, source, embedder, load_index)
    upgraded = latest.load()
    assert len(upgraded["documents"]) == 51
    assert len(upgraded["meta"]["supported_targets"]) == 3
    assert latest.load()["corpus"] == upgraded["corpus"]
    renamed = next(item for item in upgraded["documents"] if item["document_id"] == "ping-uploaded-1")
    assert renamed["verified_targets"] == [{"distribution": "fedora"}]
    matches = retrieve(upgraded, "ping учебного стенда", {"distribution": "fedora"})
    assert matches[0]["document_id"] == "ping-uploaded-1"
