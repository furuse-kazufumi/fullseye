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
  さらに op ごとの**文脈**(``t``): 文献層のテーマ → op の対応表(``tools/gen_literature_notes.py`` の ``THEME_TABLES``)と
  厳選の層の軸(``docs/literature/curated/*.json``)で、人がその op に書いた「テーマ: なぜ使うか」(2026-10-15)と、
  その英訳(``te``)。英訳は対訳表 ``docs/i18n/op_context.json``(原文の句 → en)から組み、欠けた句があれば止まる。

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
from fullseye.opsearch import PKG_CARDS, PKG_PROBE, PKG_SEARCH  # noqa: E402

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


#: 文脈の句(テーマ名・「なぜ使うか」)の対訳表。キーは原文(日本語)の句そのもの —— 原文を書き換えれば
#: キーが外れて「訳なし」になり、:func:`op_contexts_en` が止まる(古い訳を黙って出さない)。
CONTEXT_I18N = os.path.join(_ROOT, "docs", "i18n", "op_context.json")


def _context_pairs() -> list:
    """``[(op, テーマ, なぜ), …]`` —— 文献層のテーマ表と厳選の層の軸を、書かれた順に。"""
    tools_dir = os.path.join(_ROOT, "tools")
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    import gen_literature_notes as GL
    out = []
    for table in GL.THEME_TABLES.values():
        for th in table:
            for op, why in th["ops"]:
                out.append((op, th["theme"], why))
    for name, rel in sorted(GL.CURATED.items()):
        with open(os.path.join(_ROOT, rel), encoding="utf-8") as f:
            cur = json.load(f)
        for ax in cur.get("axes") or ():
            for op, why in ax.get("ops") or ():
                out.append((op, ax["name"], why))
    return out


def context_phrases() -> list:
    """訳が要る原文の句(テーマ名と「なぜ使うか」)の一覧(重複なし、出てきた順)。"""
    seen = []
    for _op, theme, why in _context_pairs():
        for s in (theme, why):
            if s not in seen:
                seen.append(s)
    return seen


def load_context_i18n() -> dict:
    """``{原文の句: {"en": 訳}}``。"""
    with open(CONTEXT_I18N, encoding="utf-8") as f:
        return json.load(f)["phrases"]


def op_contexts_en() -> dict:
    """:func:`op_contexts` の英語版(同じ op・同じ並び)。訳の無い句があれば止まる(fail-closed)。

    ★2026-10-15: 文脈が日本語だけだったので、英語の問い合わせ(評価問題集の外れ 12 問のうち 8 問)は伸びなかった。
    """
    tr = load_context_i18n()
    missing = [s for s in context_phrases() if not (tr.get(s) or {}).get("en")]
    if missing:
        raise SystemExit("文脈の句に英訳が無い(docs/i18n/op_context.json に足す): %d 句、例 %s" % (len(missing), missing[:3]))
    ctx: dict = {}
    for op, theme, why in _context_pairs():
        line = "%s: %s" % (tr[theme]["en"], tr[why]["en"])
        lst = ctx.setdefault(op, [])
        if line not in lst:
            lst.append(line)
    return ctx


def op_contexts() -> dict:
    """op 名 → 人が書いた文脈の行 ``["テーマ: なぜ使うか", …]``(文献層のテーマ表 + 厳選の層の軸)。

    ★2026-10-15: 「溶接ビードの高さ」「研磨でどれだけ削れるか」「X 線回折で相の割合」のような**現場の言い方**は
    op の要約(1 段落の docstring)に出てこないので、検索が 0 件か無関係の op を返していた(評価問題集で hit@5 0.52)。
    その言い方と op の対応は文献層のテーマ表が**人の手で**既に持っている —— ただし文献層はファイルとして読む層で、
    この検索(MCP / fullseye-rag)からは引けなかった(同じ問いに答える入口が 2 つあり、片方にだけ知識が在った)。
    語の一致で op を引くのではない: どの op に付けるかは表が決め、検索はその文を op の索引語に足すだけ。
    """
    tools_dir = os.path.join(_ROOT, "tools")
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    import gen_literature_notes as GL
    ctx: dict = {}

    def add(op, line):
        lst = ctx.setdefault(op, [])
        if line not in lst:
            lst.append(line)

    for table in GL.THEME_TABLES.values():
        for th in table:
            for op, why in th["ops"]:
                add(op, "%s: %s" % (th["theme"], why))
    for name, rel in sorted(GL.CURATED.items()):
        with open(os.path.join(_ROOT, rel), encoding="utf-8") as f:
            cur = json.load(f)
        for ax in cur.get("axes") or ():
            for op, why in ax.get("ops") or ():
                add(op, "%s: %s" % (ax["name"], why))
    if not ctx:
        raise SystemExit("文献層のテーマ表から op の文脈が 0 件 —— 検索索引を書かない")
    return ctx


def build_search() -> dict:
    """``fullseye.opsearch`` の索引。要約は opdocs と同じ切り方(``summary_and_rest``)、訳は指紋が合うものだけ。"""
    tools_dir = os.path.join(_ROOT, "tools")
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    import opdocs as OD
    ctx = op_contexts()
    ctx_en = op_contexts_en()
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
               "h": r.get("halcon") or None, "p": path, "s": summ, "t": ctx.get(r["name"]) or None,
               "te": ctx_en.get(r["name"]) or None}
        rows.append({k: v for k, v in row.items() if v not in (None, "", {})})
    if not rows:
        raise SystemExit("opdocs の記録が 0 件 —— 検索索引を書かない")
    rows.sort(key=lambda x: (x["d"], x["n"]))
    unknown = sorted(set(ctx) - {r["n"] for r in rows})
    if unknown:                                        # 表が名指しする op は実在する(gen_literature_notes と同じ規約)
        raise SystemExit("文献層の表に実在しない op: %s" % ", ".join(unknown))
    return {"generated_by": "tools/gen_mcp_data.py", "languages": list(LANGS), "n_ops": len(rows),
            "summaries_per_language": n_tr, "ops_with_context": sum(1 for r in rows if r.get("t")),
            "ops": rows}


def build_cards(search: dict, knobs: list) -> dict:
    """Build compact, stable cards for small-context models."""
    kt = {r.get("op"): r for r in knobs}
    rows = []
    for r in search["ops"]:
        name, kr = r["n"], kt.get(r["n"]) or {}
        card = {"name": name, "in_sort": r.get("i"), "out_sort": r.get("o"),
                "summary": ((r.get("s") or {}).get("en") or (r.get("s") or {}).get("ja") or "")[:220],
                "knobs": {"a": kr.get("a_kind") or "unspecified",
                            "b": "unused" if kr.get("b_used") is False else "unspecified"},
                "cautions": (["type metadata is incomplete"] if not r.get("i") or not r.get("o") else []) +
                             (["knob probe: %s" % kr["status"]] if kr.get("status") not in (None, "determined") else []),
                "call": "fullseye.apply(value, %r, 0.5, 0.5)" % name}
        card["tokens"] = max(1, (len(json.dumps(card, ensure_ascii=False)) + 3) // 4)
        rows.append(card)
    return {"generated_by": "tools/gen_mcp_data.py", "n_ops": len(rows), "ops": rows}


def build_probe(search: dict) -> dict:
    """Publish a CPU-only one-shot probe; a failure describes this input, not the op."""
    import warnings
    import numpy as np
    import op_probe
    import ops
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
    registry = {o.name: o for o in ops.REGISTRY}
    out = []
    for name in sorted(r["n"] for r in search["ops"]):
        op = registry.get(name)
        if op is None:
            out.append({"name": name, "status": "not_in_registry", "reason": "not executable by fullseye.apply"})
            continue
        input_error = None
        try:
            value = op_probe.sample_input(op.in_sort, np.random.default_rng(20261028), structured=True)
        except Exception as exc:
            value, input_error = None, "%s: %s" % (type(exc).__name__, str(exc)[:160])
        if value is None:
            out.append({"name": name, "status": "input_unavailable", "in_sort": op.in_sort,
                        "reason": input_error or "no representative input for this sort"})
            continue
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                result = op.fn(value, 0.5, 0.5)
            arrays = ([result] if isinstance(result, np.ndarray) else
                      [v for v in result.values() if isinstance(v, np.ndarray)] if isinstance(result, dict) else [])
            bad = any(a.dtype.kind in "fc" and not np.isfinite(a).all() for a in arrays)
            status, reason = (("nonfinite", "representative input produced NaN or infinity") if bad else
                              ("shape_mismatch", "representative input produced no value") if result is None else ("ok", None))
        except Exception as exc:
            status, reason = "exception", "%s: %s" % (type(exc).__name__, str(exc)[:240])
        row = {"name": name, "status": status, "in_sort": op.in_sort, "out_sort": op.out_sort,
               "probe_input": "op_probe.sample_input(%r, structured=True)" % op.in_sort}
        if reason:
            row["reason"] = reason
        out.append(row)
    return {"generated_by": "tools/gen_mcp_data.py", "probe": "CPU, a=b=0.5, representative input",
            "n_ops": len(out), "ops": out}


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
    search, knobs = build_search(), build_knobs()
    targets = {PKG_INDEX: _dump(build_index()), PKG_NOTES: _dump(build_notes()),
               PKG_KNOBS: _dump(knobs), PKG_SEARCH: _dump_compact(search),
               PKG_CARDS: _dump_compact(build_cards(search, knobs)),
               PKG_PROBE: _dump_compact(build_probe(search))}
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
