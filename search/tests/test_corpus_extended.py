import json
from collections import Counter
from pathlib import Path

from app.api import load_index
from app.distributions import DISTRIBUTIONS
from bm25_demo import split_sections


ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "corpus"


def test_fifty_documents_each_have_three_instruction_sections():
    manifest = json.loads((CORPUS / "manifest.json").read_text(encoding="utf-8"))
    ids = {item["document_id"] for item in manifest["documents"]}

    assert ids == {path.stem for path in (CORPUS / "docs").glob("*.md")}
    assert len(ids) == 50
    assert Counter(item["category"] for item in manifest["documents"]) == {
        "base": 21, "network": 18, "packages": 11,
    }

    for document in manifest["documents"]:
        sections = dict(split_sections((CORPUS / document["path"]).read_text(encoding="utf-8")))
        for distro, label in DISTRIBUTIONS.items():
            assert document["distro_sections"][label] == distro
            assert "bash" in sections[label], (document["document_id"], label)


def test_index_contains_fifty_commands_for_each_distro():
    index = load_index()
    for distro in DISTRIBUTIONS:
        specific = [item for item in index["chunks"] if item["distribution"] == distro]
        assert len({item["command"] for item in specific}) == 50
        assert all(item["applies_to"] == [{"distribution": distro}] for item in specific)
