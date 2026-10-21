# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""手書き文書に埋め込んだ、実装から決まる件数だけを更新する。

文章そのものは手書きのまま保ち、件数の表記だけを狭い正規表現で置換する。
README の op 数は registry、AI_RAG_GUIDE のノート数は docs 索引と同じ
``gen_docs_index_ops._records()`` を唯一の数え方とする。
"""
from __future__ import annotations

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


def _replace_one(path: Path, pattern: str, replacement: str) -> None:
    body = path.read_text(encoding="utf-8")
    changed, n = re.subn(pattern, replacement, body, count=1)
    if n != 1:
        raise RuntimeError("%s: 件数の置換箇所が %d 件(pattern=%r)" % (path, n, pattern))
    path.write_text(changed, encoding="utf-8", newline="\n")


def generate() -> None:
    nops, nnotes = counts()

    # 冒頭だけ。後段の生成ブロックにある網羅率の分母などは、その生成器の責務。
    for path in sorted(DOCS.glob("README*.md")):
        body = path.read_text(encoding="utf-8")
        head, sep, tail = body.partition("\n---\n")
        changed, n = re.subn(r"\*\*\d+\*\*", "**%d**" % nops, head, count=1)
        if n != 1:
            raise RuntimeError("%s: 冒頭の op 件数が %d 件" % (path, n))
        path.write_text(changed + sep + tail, encoding="utf-8", newline="\n")

    for path in sorted(DOCS.glob("AI_RAG_GUIDE*.md")):
        lang = path.name.split(".")[1] if path.name.count(".") > 1 else "ja"
        rendered = format(nnotes, ",").replace(",", "." if lang == "de" else ",")
        _replace_one(path, r"(\*\*)\d{1,3}(?:[,.]\d{3})+(\s*)(?=(?:枚|notes|Notizen|개|篇|条))",
                     r"\g<1>%s\g<2>" % rendered)

    # 上の変更は各言語とも数値だけ。この条件を Git の直前版と照合できたときだけ
    # 翻訳を fresh として扱う。文章まで変わっていれば例外になり、手訳を要求する。
    for path in sorted(DOCS.glob("AI_RAG_GUIDE.*.md")):
        i18n_docs.stamp_if_numeric_only(str(path))


def main() -> int:
    generate()
    print("updated README op count and AI_RAG_GUIDE note count")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
