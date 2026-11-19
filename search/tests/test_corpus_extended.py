import json
from pathlib import Path

from app.api import load_index


ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "corpus"

NEW_COMMANDS = {
    "head", "tail", "sort", "uniq", "wc",
    "du", "df", "ps", "kill", "ssh",
}


def test_twenty_documents_registered():
    manifest = json.loads(
        (CORPUS / "manifest.json").read_text(
            encoding="utf-8"
        )
    )

    commands = {
        item["document_id"]
        for item in manifest["documents"]
    }

    assert len(commands) == 20
    assert NEW_COMMANDS <= commands


def test_new_documents_are_not_verified():
    manifest = json.loads(
        (CORPUS / "manifest.json").read_text(
            encoding="utf-8"
        )
    )

    for item in manifest["documents"]:
        if item["document_id"] in NEW_COMMANDS:
            assert item["verified_targets"] == []


def test_index_contains_twenty_commands():
    index = load_index()

    commands = {
        item["command"]
        for item in index["chunks"]
    }

    assert len(commands) == 20
    assert NEW_COMMANDS <= commands
