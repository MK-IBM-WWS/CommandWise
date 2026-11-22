import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import uuid

from app.distributions import DISTRIBUTIONS
from bm25_index import BM25Index
from bm25_demo import SKIP_SECTIONS, split_sections, tokenize


ROOT = Path(__file__).resolve().parents[2]


def as_bytes(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def write_json(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def build(corpus: Path, output: Path):
    manifest_path = corpus / "manifest.json"
    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )

    documents = {
        doc["document_id"]: doc
        for doc in manifest["documents"]
    }

    actual_files = {
        path.stem
        for path in (corpus / "docs").glob("*.md")
    }

    if not actual_files or actual_files != set(documents):
        raise ValueError(
            "Файлы docs и manifest не совпадают: "
            f"{actual_files ^ set(documents)}"
        )

    checksum = hashlib.sha256()

    manifest_for_hash = {
        key: value
        for key, value in manifest.items()
        if key != "corpus_version"
    }

    checksum.update(as_bytes(manifest_for_hash))

    for doc_id in sorted(documents):
        doc = documents[doc_id]
        path = corpus / doc["path"]

        expected_path = corpus / "docs" / f"{doc_id}.md"

        if path.resolve() != expected_path.resolve():
            raise ValueError(
                f"Неверный путь документа: {doc_id}"
            )

        checksum.update(doc_id.encode("utf-8"))
        checksum.update(path.read_bytes())

    checksum.update(
        (ROOT / "search" / "bm25_demo.py").read_bytes()
    )

    checksum.update((ROOT / "search" / "bm25_index.py").read_bytes())
    checksum.update(Path(__file__).read_bytes())
    version = checksum.hexdigest()[:16]

    chunks = []

    for doc_id in sorted(documents):
        doc = documents[doc_id]

        content = (
            corpus / "docs" / f"{doc_id}.md"
        ).read_text(encoding="utf-8")

        title = next(
            (
                line[2:].strip()
                for line in content.splitlines()
                if line.startswith("# ")
            ),
            doc_id,
        )

        distro_sections = doc.get("distro_sections", {})
        section_distribution = None
        command = doc.get("command", doc_id)
        for heading, section_text in split_sections(content):
            if heading in DISTRIBUTIONS.values() and heading in distro_sections:
                section_distribution = distro_sections[heading]
            if heading.casefold() in SKIP_SECTIONS or not section_text.partition("\n")[2].strip():
                continue

            target_list = doc.get("verified_targets", [])
            if section_distribution:
                target_list = [item for item in target_list if item["distribution"] == section_distribution]
                if not target_list:
                    raise ValueError(f"Unexpected distribution for {doc_id}: {section_distribution}")

            search_text = f"{command} {heading} {section_text}"
            identity = [doc_id, heading, section_text, target_list]
            chunk_id = hashlib.sha256(as_bytes(identity)).hexdigest()[:24]
            chunks.append({
                "chunk_id": chunk_id,
                "document_id": doc_id,
                "command": command,
                "title": title,
                "section": heading,
                "text": section_text,
                "search_text": search_text,
                "source_url": doc.get("distro_sources", {}).get(section_distribution, doc["source_url"]),
                "distribution": section_distribution or (
                    target_list[0]["distribution"] if len(target_list) == 1 else "common"
                ),
                "equivalent_only": bool(doc.get("native_for") and section_distribution not in doc["native_for"]),
                "package_version": doc.get("package_version", ""),
                "collected_at": doc.get("collected_at"),
                "applies_to": target_list,
            })

    if not chunks:
        raise ValueError("Нет фрагментов для индекса")

    tokens = [
        tokenize(chunk["search_text"])
        for chunk in chunks
    ]

    if not any(tokens):
        raise ValueError("Все поисковые токены пусты")

    output.mkdir(parents=True, exist_ok=True)

    stage = output / (
        ".building-" + uuid.uuid4().hex
    )

    stage.mkdir()

    try:
        write_json(stage / "chunks.json", chunks)
        write_json(stage / "bm25.json", BM25Index.build(tokens).snapshot())

        chunks_hash = hashlib.sha256(
            (stage / "chunks.json").read_bytes()
        ).hexdigest()

        bm25_hash = hashlib.sha256(
            (stage / "bm25.json").read_bytes()
        ).hexdigest()

        write_json(stage / "meta.json", {
            "corpus_version": version,
            "count": len(chunks),
            "supported_targets": manifest["supported_targets"],
            "tokenizer": "bm25_demo-v1",
            "chunker": "markdown-headings-v1",
            "bm25": {
                "k1": 1.5,
                "b": 0.75
            },
            "chunks_sha256": chunks_hash,
            "bm25_sha256": bm25_hash,
        })

        release_dir = output / version

        if release_dir.exists():
            shutil.rmtree(stage)
        else:
            os.replace(stage, release_dir)

        pointer = output / (
            ".current-" + uuid.uuid4().hex + ".json"
        )

        write_json(pointer, {
            "corpus_version": version
        })

        os.replace(pointer, output / "current.json")

        manifest["corpus_version"] = version
        write_json(manifest_path, manifest)

        print(f"Индекс готов: {len(chunks)} фрагментов")
        print(f"Версия корпуса: {version}")
        print(f"Папка индекса: {release_dir}")
        print(
            "Проверенных систем: "
            f"{len(manifest['supported_targets'])}"
        )

    finally:
        if stage.exists():
            shutil.rmtree(stage)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--corpus",
        type=Path,
        default=ROOT / "corpus"
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / ".local-index"
    )

    args = parser.parse_args()

    build(
        args.corpus.resolve(),
        args.output.resolve()
    )
