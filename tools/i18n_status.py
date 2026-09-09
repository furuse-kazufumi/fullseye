# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""多言語化の現在地を**数え直す**(`docs/I18N_PLAN.md` の数字はここから)。

手で書いた進捗は必ず古びる。だから毎回ディレクトリとファイルの側から数える:

* `docs/` の文書が何本あり、そのうち何本に他言語版があるか
* 非日本語版の中に**かな**が何行残っているか(= 日本語が混ざっている行)。
  `(ja)` の印が付いているものは「未訳と分かる形で出している」ので分けて数える ——
  **黙って混ざっている行がゼロ**であることがこの道具の主目的。
* `DESIGN_NOTES`(★ コメント集)の訳の本数

漢字ではなく**かな**で判定する。漢字は中国語版と共有するので、漢字で数えると
中国語の訳を「日本語が残っている」と誤判定する(実際に最初そうなった)。

    py -3.11 tools/i18n_status.py
    py -3.11 tools/i18n_status.py --strict   # 印の無い日本語が 1 行でもあれば exit 1
"""
from __future__ import annotations

import argparse
import json
import os
import re

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DOCS = os.path.join(_ROOT, "docs")

#: かな = 日本語であることの確実な印(漢字は中国語と共有するので使えない)。
_KANA = re.compile(r"[぀-ヿ]")

#: 未訳であることを示す印。これが付いていれば「隠していない」。
_MARK = "_(ja)_"


def _docs_by_stem() -> dict:
    out: dict[str, set] = {}
    for name in sorted(os.listdir(_DOCS)):
        if not name.endswith(".md"):
            continue
        parts = name[:-3].split(".")
        out.setdefault(parts[0], set()).add(parts[1] if len(parts) > 1 else "ja")
    return out


def _kana_lines(path: str):
    """(印つき, 印なし) の行数。"""
    marked = bare = 0
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.lstrip().startswith("<!--"):
                    continue          # 保守者向けのコメントは読み手に出ない
                if _KANA.search(line):
                    if _MARK in line:
                        marked += 1
                    else:
                        bare += 1
    except OSError:
        pass
    return marked, bare


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--strict", action="store_true",
                    help="印の無い日本語が非日本語版に 1 行でもあれば exit 1")
    a = ap.parse_args(argv)

    by = _docs_by_stem()
    multi = {k: v for k, v in by.items() if len(v) > 1}
    ja_only = [k for k, v in by.items() if v == {"ja"}]
    ja_lines = 0
    for k in ja_only:
        p = os.path.join(_DOCS, k + ".md")
        if os.path.isfile(p):
            with open(p, encoding="utf-8", errors="replace") as f:
                ja_lines += sum(1 for _ in f)

    print("docs/ の文書: %d 本 —— 多言語版あり %d 本 / 日本語のみ %d 本(%d 行)"
          % (len(by), len(multi), len(ja_only), ja_lines))

    total_bare = 0
    print("\n非日本語版に残る日本語(かなで判定、HTML コメントは除く):")
    for name in sorted(os.listdir(_DOCS)):
        if not name.endswith(".md") or name.count(".") < 2:
            continue
        marked, bare = _kana_lines(os.path.join(_DOCS, name))
        if marked or bare:
            total_bare += bare
            flag = "  ★印なし" if bare else ""
            print("  %-26s 印つき %3d / 印なし %3d%s" % (name, marked, bare, flag))

    meta_path = os.path.join(_DOCS, "design_notes.json")
    if os.path.isfile(meta_path):
        with open(meta_path, encoding="utf-8") as f:
            m = json.load(f)
        print("\nDESIGN_NOTES(★ コメント集): %d 件 / %d ファイル、訳 %s"
              % (m["total"], m["files"],
                 ", ".join("%s=%d" % (k, v) for k, v in sorted(m["translated"].items()))))

    if a.strict and total_bare:
        print("\n★印の無い日本語が %d 行ある —— 未訳は隠さず `%s` を付けること"
              % (total_bare, _MARK))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
