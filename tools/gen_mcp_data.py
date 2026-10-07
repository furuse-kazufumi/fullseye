# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""MCP サーバが wheel から読む package-data を ``fullseye/data/`` に書く。

    py -3.11 tools/gen_mcp_data.py            # 書く
    py -3.11 tools/gen_mcp_data.py --check    # 書かずに、コミット済みと一致するか(exit 1 で不一致)

書くもの(2 つ、どちらも ``pyproject.toml`` の package-data に載っている):

* ``fullseye/data/OP_INDEX.json`` —— ``docs/OP_INDEX.json`` の**同一内容の複製**
  (正本は docs 側。``imgevolve.py index`` の後にこれを回す。順序は ``tools/regen_all.py``)。
* ``fullseye/data/OP_NOTES.json`` —— ``docs/ops/**/*.md`` の frontmatter のうち MCP が
* ``fullseye/data/op_knob.json`` —— ``docs/op_knob.json``(実測したつまみの表)の同一内容の複製。
  ``api.knob_summary`` / ``list_ops`` の ``knobs`` 欄が wheel から読む(2026-09-20)
  読む項目(``fullseye.mcp.catalog.NOTE_KEYS``: op / dim / category / in / out / halcon)
  + ノートの相対パス。**本文は入れない**(140 MB。本文は同梱の Studio help HTML が代わる)。
* ``fullseye/data/OP_SEARCH.json`` —— 意味で op を引く検索(``fullseye.opsearch``)の索引: op ごとに名前・族・分類・
  入出力の型・HALCON 名・ノートの相対パスと、要約の 6 言語(ja 原文 = ``tools/opdocs.py`` の要約、5 訳 =
  ``docs/i18n/op_summary.json`` のうち原文の指紋が今の要約と一致するもの)。古い訳は入れない(2026-10-07)。

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

from fullseye.mcp.catalog import NOTE_KEYS, OP_INDEX, OP_KNOB, OPS_DOCS, PKG_INDEX, PKG_KNOBS, PKG_NOTES, scan_notes  # noqa: E402
from fullseye.opsearch import PKG_SEARCH  # noqa: E402

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


def build_knobs() -> list:
    """``docs/op_knob.json``(tools/impl2/knob_probe.py の実測)の同一内容の複製。空なら複製しない。"""
    if not os.path.exists(OP_KNOB):
        raise SystemExit("docs/op_knob.json が無い(tools/impl2/knob_probe.py の実測が正本)")
    with open(OP_KNOB, encoding="utf-8") as f:
        rows = json.load(f)
    if not isinstance(rows, list) or not rows:
        raise SystemExit("docs/op_knob.json が空 —— 複製しない")
    return rows


def build_search() -> dict:
    """``fullseye.opsearch`` の索引。要約は opdocs と同じ切り方(``summary_and_rest``)、訳は指紋が合うものだけ。"""
    tools_dir = os.path.join(_ROOT, "tools")
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    import opdocs as OD
    from fullseye.opsearch import LANGS
    recs = OD._records()[0]
    si = OD.summary_i18n()
    notes = scan_notes(OPS_DOCS)
    rows, n_tr = [], {lang: 0 for lang in LANGS}
    for r in recs:
        src = (OD.summary_and_rest(r.get("doc"))[0] or "").strip()
        summ = {}
        if src:
            summ["ja"] = src
            e = si.get("%s/%s" % (r["dim"], r["name"])) or {}
            if e.get("fp") == OD.fingerprint(src):
                for lang in LANGS[1:]:
                    if e.get(lang):
                        summ[lang] = e[lang]
        for lang in summ:
            n_tr[lang] += 1
        path = None
        for fm in notes.get(r["name"]) or ():
            if fm.get("dim") == r["dim"]:
                path = fm["path"]
                break
        row = {"n": r["name"], "d": r["dim"], "c": r.get("category"), "i": r.get("in"), "o": r.get("out"),
               "h": r.get("halcon") or None, "p": path, "s": summ}
        rows.append({k: v for k, v in row.items() if v not in (None, "", {})})
    if not rows:
        raise SystemExit("opdocs の記録が 0 件 —— 検索索引を書かない")
    rows.sort(key=lambda x: (x["d"], x["n"]))
    return {"generated_by": "tools/gen_mcp_data.py", "languages": list(LANGS), "n_ops": len(rows),
            "summaries_per_language": n_tr, "ops": rows}


def _dump_compact(obj) -> str:
    # 1 op 1 行(差分が読める)で、行の中は詰める —— indent=1 だと 6 言語ぶんで wheel が太る
    head = {k: v for k, v in obj.items() if k != "ops"}
    lines = [json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in obj["ops"]]
    return json.dumps(head, ensure_ascii=False)[:-1] + ', "ops": [\n' + ",\n".join(lines) + "\n]}\n"


def _dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="書かずに一致を確かめる(不一致で exit 1)")
    a = ap.parse_args(argv)
    targets = {PKG_INDEX: _dump(build_index()), PKG_NOTES: _dump(build_notes()),
               PKG_KNOBS: _dump(build_knobs()), PKG_SEARCH: _dump_compact(build_search())}
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
        knobs = json.loads(targets[PKG_KNOBS])
        print("[gen_mcp_data] index %d op / notes %d op (%d 枚) / knobs %d op"
              % (idx["n_ops"], notes["n_ops"], notes["n_notes"], len(knobs)))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
