# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""公開図の出典欄を監査台帳から決定的に同期する。

Synchronise every audited public-figure provenance record into its generated
``figures.json`` entry.  The ledger is the reviewable source of truth: figure
rendering can be repeated without accidentally dropping a licence, source URL,
publication, or retrieval-date notice from the public metadata.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs" / "licenses" / "public_figure_provenance.json"
FIGURES_ROOT = ROOT / "docs" / "articles" / "assets" / "poc"
REQUIRED = ("id", "figures", "source", "source_url", "publication", "license", "license_url", "retrieved", "changes")


class ProvenanceError(ValueError):
    """出典台帳の誤り。 / A public-figure provenance ledger error."""


def _read(path: Path):
    """UTF-8 JSON を fail-closed で読む。 / Read UTF-8 JSON fail-closed."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProvenanceError("cannot read %s: %s" % (path, exc)) from exc


def render_source(record: dict) -> str:
    """公開図に載せる監査可能な1行を作る。 / Render one auditable public-figure source line."""
    return ("Source: %(source)s. URL: %(source_url)s. Publication: %(publication)s. "
            "Licence: %(license)s (%(license_url)s). Retrieved: %(retrieved)s. "
            "Changes: %(changes)s" % record)


def records() -> dict[str, dict]:
    """図パスから出典レコードを作る。 / Index provenance records by figure path."""
    payload = _read(LEDGER)
    if payload.get("schema") != 1 or payload.get("audited_at") != "2026-11-24":
        raise ProvenanceError("public figure provenance ledger has an unsupported schema or audit date")
    items = payload.get("records")
    if not isinstance(items, list) or not items:
        raise ProvenanceError("public figure provenance ledger has no records")
    by_figure: dict[str, dict] = {}
    ids: set[str] = set()
    for record in items:
        if not isinstance(record, dict) or any(not str(record.get(key, "")).strip() for key in REQUIRED):
            raise ProvenanceError("public figure provenance record is incomplete")
        if record["id"] in ids:
            raise ProvenanceError("duplicate public figure provenance id: %s" % record["id"])
        ids.add(record["id"])
        if not isinstance(record["figures"], list):
            raise ProvenanceError("provenance figures must be a list: %s" % record["id"])
        for figure in record["figures"]:
            if not isinstance(figure, str) or "/" not in figure:
                raise ProvenanceError("invalid provenance figure path: %r" % (figure,))
            if figure in by_figure:
                raise ProvenanceError("duplicate public figure provenance: %s" % figure)
            by_figure[figure] = record
    return by_figure


def sync() -> int:
    """台帳を figures.json へ反映する。 / Synchronise the ledger into figures.json files."""
    by_figure = records()
    grouped: dict[str, dict[str, dict]] = {}
    for figure, record in by_figure.items():
        poc, file_name = figure.split("/", 1)
        grouped.setdefault(poc, {})[file_name] = record
    for poc, wanted in sorted(grouped.items()):
        path = FIGURES_ROOT / poc / "figures.json"
        payload = _read(path)
        if not isinstance(payload, list):
            raise ProvenanceError("figures ledger must be a list: %s" % path)
        found = set()
        for item in payload:
            if not isinstance(item, dict):
                continue
            file_name = item.get("file")
            if file_name in wanted:
                item["source"] = render_source(wanted[file_name])
                found.add(file_name)
        missing = sorted(set(wanted) - found)
        if missing:
            raise ProvenanceError("provenance figure not found in %s: %s" % (path, ", ".join(missing)))
        text = json.dumps(payload, ensure_ascii=False, indent=1) + "\n"
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            path.write_text(text, encoding="utf-8", newline="\n")
    return len(by_figure)


def main() -> int:
    """CLI entry point. / CLI entry point."""
    count = sync()
    print("synced provenance for %d public figures" % count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
