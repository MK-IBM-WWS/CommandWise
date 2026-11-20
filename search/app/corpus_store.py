"""Stage, validate and activate a whole corpus version atomically."""

from datetime import date
import json
import logging
import os
from pathlib import Path
import re
import shutil
import tempfile
import threading
from urllib.parse import urlsplit
from uuid import uuid4

import numpy as np

from app.indexer import build, write_json
from bm25_demo import SKIP_SECTIONS, split_sections

logger = logging.getLogger(__name__)
MAX_UPLOAD = 512 * 1024
DOCUMENT_ID = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")
DISTRIBUTIONS = {"debian", "ubuntu", "fedora", "arch"}


class InvalidDocument(ValueError):
    pass


class DocumentExists(ValueError):
    pass


class CorpusStore:
    def __init__(self, directory, seed, embedder, load_index):
        self.directory = directory
        self.seed = seed
        self.embedder = embedder
        self.load_index = load_index
        self.lock = threading.Lock()
        self.releases = directory / "releases"
        self.pointer = directory / "active"
        self.releases.mkdir(parents=True, exist_ok=True)
        for path in self.releases.glob(".stage-*"):
            shutil.rmtree(path)

    def load(self):
        if not self.pointer.exists():
            return self.publish(self.seed)
        name = self.pointer.read_text(encoding="ascii").strip()
        if not re.fullmatch(r"[a-f0-9]{32}", name):
            raise ValueError("Invalid active corpus pointer")
        path = self.releases / name
        index = self.load_index(path / "index")
        return self.attach(index, path, np.load(path / "vectors.npy", allow_pickle=False))

    def publish(self, base, previous=None, document=None, content=None):
        stage = Path(tempfile.mkdtemp(prefix=".stage-", dir=self.releases))
        release = None
        ready = False
        try:
            corpus = stage / "corpus"
            shutil.copytree(base, corpus)
            if document is not None:
                manifest_path = corpus / "manifest.json"
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                if any(item["document_id"] == document["document_id"] for item in manifest["documents"]):
                    raise DocumentExists("Идентификатор документа уже занят.")
                verified = document["verified_targets"][0]
                if not any(all(item.get(key) == value for key, value in verified.items()) for item in manifest["supported_targets"]):
                    manifest["supported_targets"].append({**verified, "label": verified["release"]})
                manifest["documents"].append(document)
                write_json(manifest_path, manifest)
                (corpus / document["path"]).write_text(content, encoding="utf-8")

            build(corpus, stage / "index")
            index = self.load_index(stage / "index")
            vectors = self.embedder.index(index["chunks"], previous)
            np.save(stage / "vectors.npy", vectors, allow_pickle=False)
            release = self.releases / uuid4().hex
            os.replace(stage, release)
            snapshot = self.attach(index, release, vectors)
            pointer = self.directory / (".active-" + release.name)
            try:
                pointer.write_text(release.name + "\n", encoding="ascii")
                os.replace(pointer, self.pointer)
                ready = True
            finally:
                pointer.unlink(missing_ok=True)
            try:
                self.prune(release, previous)
            except OSError:
                logger.exception("Could not inspect corpus releases")
            return snapshot
        finally:
            if stage.exists():
                shutil.rmtree(stage)
            if release is not None and not ready and release.is_dir():
                shutil.rmtree(release)

    def attach(self, index, release, vectors):
        chunks = index["chunks"]
        if vectors.shape != (len(chunks), self.embedder.dimensions):
            raise ValueError("Embedding matrix does not match corpus")
        corpus = release / "corpus"
        manifest = json.loads((corpus / "manifest.json").read_text(encoding="utf-8"))
        index["documents"] = manifest["documents"]
        index["corpus"] = corpus
        index["vectors"] = {item["chunk_id"]: vector for item, vector in zip(chunks, vectors)}
        return index

    def prune(self, release, previous):
        retained = {release}
        if previous is not None:
            retained.add(previous["corpus"].parent)
        for path in self.releases.iterdir():
            if path not in retained and re.fullmatch(r"[a-f0-9]{32}", path.name):
                try:
                    shutil.rmtree(path)
                except OSError:
                    logger.exception("Could not remove previous corpus release")


def clean_field(form, name, maximum):
    value = form.get(name)
    if not isinstance(value, str):
        raise InvalidDocument("Заполните все метаданные документа.")
    value = value.strip()
    if not value or len(value) > maximum or not value.isprintable():
        raise InvalidDocument("Проверьте заполнение и длину метаданных документа.")
    return value


def validate(form, data):
    document_id = clean_field(form, "document_id", 64)
    if DOCUMENT_ID.fullmatch(document_id) is None:
        raise InvalidDocument("Идентификатор: строчные латинские буквы, цифры, дефис или подчёркивание.")
    distribution = clean_field(form, "distribution", 12)
    if distribution not in DISTRIBUTIONS:
        raise InvalidDocument("Выберите поддерживаемый дистрибутив.")
    release = clean_field(form, "release", 48)
    package = clean_field(form, "package", 80)
    package_version = clean_field(form, "package_version", 80)
    source_url = clean_field(form, "source_url", 2048)
    try:
        url = urlsplit(source_url)
        if url.scheme not in ("http", "https") or not url.hostname or url.username or url.password or any(c.isspace() for c in source_url) or "\\" in source_url:
            raise ValueError()
    except ValueError as exc:
        raise InvalidDocument("Укажите действительную HTTP(S)-ссылку на исходную документацию.") from exc
    collected_at = clean_field(form, "collected_at", 10)
    try:
        if date.fromisoformat(collected_at).isoformat() != collected_at:
            raise ValueError()
    except ValueError as exc:
        raise InvalidDocument("Дата проверки должна быть в формате ГГГГ-ММ-ДД.") from exc
    try:
        content = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise InvalidDocument("Сохраните Markdown в кодировке UTF-8.") from exc
    if "\0" in content:
        raise InvalidDocument("Файл содержит недопустимые символы.")
    sections = [text for heading, text in split_sections(content) if heading.lower() not in SKIP_SECTIONS and text.partition("\n")[2].strip()]
    if not sections:
        raise InvalidDocument("Добавьте раздел с заголовком ## или ### и текстом.")
    if len(sections) > 120 or any(len(text) > 4000 for text in sections):
        raise InvalidDocument("Допускается до 120 разделов, каждый до 4000 символов.")
    verified = {"distribution": distribution, "release": release}
    return {
        "document_id": document_id, "path": f"docs/{document_id}.md",
        "package": package, "package_version": package_version, "source_url": source_url,
        "collected_at": collected_at, "verified_targets": [verified],
    }, content
