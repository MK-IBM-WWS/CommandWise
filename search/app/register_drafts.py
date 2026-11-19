import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "corpus"
MANIFEST_PATH = CORPUS / "manifest.json"

COREUTILS = (
    "https://www.gnu.org/software/coreutils/"
    "manual/html_node/"
)

SOURCES = {
    "head": ("coreutils", COREUTILS + "head-invocation.html"),
    "tail": ("coreutils", COREUTILS + "tail-invocation.html"),
    "sort": ("coreutils", COREUTILS + "sort-invocation.html"),
    "uniq": ("coreutils", COREUTILS + "uniq-invocation.html"),
    "wc": ("coreutils", COREUTILS + "wc-invocation.html"),
    "du": ("coreutils", COREUTILS + "du-invocation.html"),
    "df": ("coreutils", COREUTILS + "df-invocation.html"),
    "ps": (
        "procps",
        "https://man7.org/linux/man-pages/man1/ps.1.html",
    ),
    "kill": (
        "",
        "https://man7.org/linux/man-pages/man1/kill.1.html",
    ),
    "ssh": (
        "openssh-client",
        "https://man.openbsd.org/ssh",
    ),
}


def main():
    manifest = json.loads(
        MANIFEST_PATH.read_text(encoding="utf-8")
    )

    existing = {
        doc["document_id"]
        for doc in manifest["documents"]
    }

    # Сначала проверяем наличие всех файлов.
    missing = [
        command
        for command in SOURCES
        if not (CORPUS / "docs" / f"{command}.md").is_file()
    ]

    if missing:
        raise FileNotFoundError(
            "Не найдены файлы: " + ", ".join(missing)
        )

    added = 0

    for command, (package, source_url) in SOURCES.items():
        if command in existing:
            continue

        manifest["documents"].append({
            "document_id": command,
            "path": f"docs/{command}.md",
            "package": package,
            "source_url": source_url,
            "package_version": "",
            "collected_at": None,
            "verified_targets": [],
        })

        added += 1

    manifest["documents"].sort(
        key=lambda doc: doc["document_id"]
    )

    if added:
        manifest["corpus_version"] = ""

        MANIFEST_PATH.write_text(
            json.dumps(
                manifest,
                ensure_ascii=False,
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )

    print(f"Добавлено новых команд: {added}")
    print(f"Всего команд: {len(manifest['documents'])}")


if __name__ == "__main__":
    main()
