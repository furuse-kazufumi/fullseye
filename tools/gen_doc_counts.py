# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""手書き文書に埋め込んだ、実装から決まる件数だけを更新する。

文章そのものは手書きのまま保ち、件数の表記だけを狭い正規表現で置換する。
README の op 数は registry、AI_RAG_GUIDE のノート数は docs 索引と同じ
``gen_docs_index_ops._records()`` を唯一の数え方とする。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import i18n_docs

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def counts() -> tuple[int, int]:
    import gen_docs_index_ops

    # 先に opdocs と同じ台帳を確定する。ops の import は利用可能な任意 backend を
    # 登録し、一部の台帳モジュールも import するため、順序を逆にするとノート数へ
    # 混ざる(実測 3,496 -> 3,501)ことがある。
    nnotes = len(gen_docs_index_ops._records())
    import ops

    return len(ops.REGISTRY), nnotes


def _index_counts() -> tuple[int, int]:
    """Read shipped total and ledger counts / 出荷索引から総数・台帳数を読む。"""
    index = json.loads((DOCS / "OP_INDEX.json").read_text(encoding="utf-8"))
    return int(index["n_ops"]), int(index["tiers"]["ledger"])


def _replace_one(path: Path, pattern: str, replacement: str) -> None:
    body = path.read_text(encoding="utf-8")
    changed, n = re.subn(pattern, replacement, body, count=1)
    if n != 1:
        raise RuntimeError("%s: 件数の置換箇所が %d 件(pattern=%r)" % (path, n, pattern))
    path.write_text(changed, encoding="utf-8", newline="\n")


def _replace_public_count_forms(path: Path, total: int, ledger: int) -> None:
    """Update only current-count prose forms / 現在数を述べる定型だけを索引値へそろえる。"""
    body = path.read_text(encoding="utf-8")
    total_text, ledger_text = format(total, ","), format(ledger, ",")
    total_patterns = (
        r"\b\d{1,3}(?:,\d{3})*(?= typed ops\b)",
        r"\b\d{1,3}(?:,\d{3})*(?= typed operators\b)",
        r"\b\d{1,3}(?:,\d{3})*(?=\s+operators in the machine-readable\s+index)",
        r"(?<=the )\d{1,3}(?:,\d{3})*(?= operators are not all reachable)",
        r"(?<=of the )\d{1,3}(?:,\d{3})*(?= \(\d+ ledger \+ \d+ registry\))",
        r"(?<=the full )\d{1,3}(?:,\d{3})*(?=\.)",
    )
    ledger_patterns = (
        r"\b\d{1,3}(?:,\d{3})*(?= in the typed ledgers)",
        r"\b\d{1,3}(?:,\d{3})*(?= typed-ledger ops)",
        r"(?<=typed ledgers \()\d{1,3}(?:,\d{3})*(?= operators)",
        r"(?<=ledgers \()\d{1,3}(?:,\d{3})*(?= operators whose inputs)",
    )
    for pattern in total_patterns:
        body = re.sub(pattern, total_text, body)
    for pattern in ledger_patterns:
        body = re.sub(pattern, ledger_text, body)
    path.write_text(body, encoding="utf-8", newline="\n")


def generate() -> None:
    nops, nnotes = counts()
    total, ledger = _index_counts()

    # 冒頭だけ。後段の生成ブロックにある網羅率の分母などは、その生成器の責務。
    for path in sorted(DOCS.glob("README*.md")):
        body = path.read_text(encoding="utf-8")
        intro_start = 0
        if body.startswith("---\n"):
            frontmatter_end = body.find("\n---\n", 4)
            if frontmatter_end < 0:
                raise RuntimeError("%s: front matter が閉じていない" % path)
            intro_start = frontmatter_end + len("\n---\n")
        prefix = body[:intro_start]
        head, sep, tail = body[intro_start:].partition("\n---\n")
        changed, n = re.subn(r"\*\*\d+\*\*", "**%d**" % nops, head, count=1)
        if n != 1:
            raise RuntimeError("%s: 冒頭の op 件数が %d 件" % (path, n))
        path.write_text(prefix + changed + sep + tail, encoding="utf-8", newline="\n")

    for path in sorted(DOCS.glob("AI_RAG_GUIDE*.md")):
        lang = path.name.split(".")[1] if path.name.count(".") > 1 else "ja"
        rendered = format(nnotes, ",").replace(",", "." if lang == "de" else ",")
        _replace_one(path, r"(\*\*)\d{1,3}(?:[,.]\d{3})+(\s*)(?=(?:枚|notes|Notizen|개|篇|条))",
                     r"\g<1>%s\g<2>" % rendered)

    # 上の変更は各言語とも数値だけ。この条件を Git の直前版と照合できたときだけ
    # 翻訳を fresh として扱う。文章まで変わっていれば例外になり、手訳を要求する。
    for path in sorted(DOCS.glob("AI_RAG_GUIDE.*.md")):
        i18n_docs.stamp_if_numeric_only(str(path))

    # These files are prose, but their present-tense operator counts are derived
    # facts. Keep the narrow count forms in one generator rather than hand-editing.
    public_root = DOCS.parent
    for rel in ("pyproject.toml", "CITATION.cff", "README.md", "docs/INTEGRATION.md"):
        path = public_root / rel
        if path.exists():
            _replace_public_count_forms(path, total, ledger)


def main() -> int:
    generate()
    print("updated README op count and AI_RAG_GUIDE note count")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
