# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""MCP サーバが wheel から読む package-data を ``fullseye/data/`` に書く。

    py -3.11 tools/gen_mcp_data.py            # 書く
    py -3.11 tools/gen_mcp_data.py --check    # 書かずに、コミット済みと一致するか(exit 1 で不一致)

書くもの(2 つ、どちらも ``pyproject.toml`` の package-data に載っている):

* ``fullseye/data/OP_INDEX.json`` —— ``docs/OP_INDEX.json`` の**同一内容の複製**
  (正本は docs 側。``imgevolve.py index`` の後にこれを回す。順序は ``tools/regen_all.py``)。
* ``fullseye/data/OP_NOTES.json`` —— ``docs/ops/**/*.md`` の frontmatter のうち MCP が
  読む項目(``fullseye.mcp.catalog.NOTE_KEYS``: op / dim / category / in / out / halcon)
  + ノートの相対パス。**本文は入れない**(140 MB。本文は同梱の Studio help HTML が代わる)。

なぜ複製か: ``docs/`` はパッケージの外にあり、flat layout の wheel には乗らない。
0.1.11 の MCP は ``docs/OP_INDEX.json`` をリポジトリ相対で読んでいたので
``pip install fullseye`` した環境では ``CatalogError`` で止まった(2026-09-15 実測)。
生成物を 2 か所に持つ代わりに、``--check`` と ``tests/test_mcp_server.py`` が
「複製が正本と一致する」ことを数える(``regen_all --check`` が CI で回す)。
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from fullseye.mcp.catalog import NOTE_KEYS, OP_INDEX, OPS_DOCS, PKG_INDEX, PKG_NOTES, scan_notes  # noqa: E402

DATA_DIR = os.path.join(_ROOT, "fullseye", "data")


def build_notes() -> dict:
    notes = scan_notes(OPS_DOCS)
    if not notes:
        raise SystemExit("docs/ops にノートが 1 枚も無い(%s)。先に `py -3.11 tools/opdocs.py all`" % OPS_DOCS)
    n_files = sum(len(v) for v in notes.values())
    return {"generated_by": "tools/gen_mcp_data.py", "source": "docs/ops/**/*.md",
            "keys": list(NOTE_KEYS) + ["path"],
            "n_ops": len(notes), "n_notes": n_files, "notes": notes}


def build_index() -> dict:
    if not os.path.exists(OP_INDEX):
        raise SystemExit("docs/OP_INDEX.json が無い。先に `py -3.11 imgevolve.py index`")
    with open(OP_INDEX, encoding="utf-8") as f:
        idx = json.load(f)
    if not idx.get("ops"):
        raise SystemExit("docs/OP_INDEX.json の ops が空 —— 複製しない")
    return idx


def _dump(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="書かずに一致を確かめる(不一致で exit 1)")
    a = ap.parse_args(argv)
    targets = {PKG_INDEX: _dump(build_index()), PKG_NOTES: _dump(build_notes())}
    os.makedirs(DATA_DIR, exist_ok=True)
    rc = 0
    for name, text in targets.items():
        path = os.path.join(DATA_DIR, name)
        if a.check:
            cur = open(path, encoding="utf-8").read() if os.path.exists(path) else None
            if cur != text:
                print("★%s が古い(`py -3.11 tools/gen_mcp_data.py` で書き直す)" % os.path.relpath(path, _ROOT))
                rc = 1
            continue
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print("[gen_mcp_data] %s (%.0f KB)" % (os.path.relpath(path, _ROOT), len(text.encode("utf-8")) / 1024))
    if not a.check:
        idx, notes = json.loads(targets[PKG_INDEX]), json.loads(targets[PKG_NOTES])
        print("[gen_mcp_data] index %d op / notes %d op (%d 枚)" % (idx["n_ops"], notes["n_ops"], notes["n_notes"]))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
