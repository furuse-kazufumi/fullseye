# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opdocs — single-source-of-truth operator documentation (Markdown) + derived help.

The Markdown under ``docs/ops/`` is the **source of truth** for operator docs: one
note per operator (``docs/ops/<dim>/<category>/<op>.md``), a hand/agent-authored
family usage guide per op-family (``docs/ops/2d/guides/<family>.md``, math は
``docs/ops/math/guides/``), and an **auto-generated** table of contents that simply
walks the folder hierarchy. Studio's per-op HTML help (``studio_assets/op_help/``)
is produced by **bulk-converting** that Markdown — never authored twice. The same
Markdown tree is shaped as an AI-usage corpus (file-per-note) so an assistant can
grasp *how to use* each op.

Dimensions: ``2d`` (ops.REGISTRY), ``3d`` (ops3d.OPS3D), ``math`` (opsmath.OPSMATH)
and ``optics`` (opsoptics.OPSOPTICS). The two *ledger* dimensions share one code
path (:data:`LEDGER_DIMS`): notes land in ``docs/ops/<dim>/<category>/<op>.md``
and help pages in ``op_help/<dim>/``, namespaced like 3-D.

Subcommands (all idempotent; safe to re-run)::

    py -3.11 tools/opdocs.py md      # (re)write per-op Markdown notes (deterministic)
    py -3.11 tools/opdocs.py toc     # (re)write INDEX.md files by walking the tree
    py -3.11 tools/opdocs.py html    # bulk-convert 2-D Markdown -> Studio HTML help
    py -3.11 tools/opdocs.py all     # md + toc + html

Per-op notes and every INDEX.md are **generated** — do not hand-edit (a drift test
regenerates and diffs). The family guides under ``docs/ops/2d/guides/`` are authored
(grounded in the runnable examples) and are NOT overwritten by ``md``.
"""
from __future__ import annotations

import glob
import html as _html
import inspect
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "tools"))

DOCS = os.path.join(_ROOT, "docs", "ops")
HELP_ROOT = os.path.join(_ROOT, "studio_assets", "op_help")
_GEN_MARK = "<!-- opdocs:generated — do not edit; source of truth is docs/ops/*.md (tools/opdocs.py html) -->"

_AMBER = "#f5a524"
_TEAL = "#17b8a6"
_MUTE = "#8b91a0"
_CODE = "#22d3bf"

#: Ledger dimensions — registries that describe their ops with a typed catalog
#: instead of a 2-D/3-D op table. They share one notes/TOC/HTML code path; each
#: gets its own ``docs/ops/<dim>/`` tree, ``op_help/<dim>/`` help dir, anchor
#: namespace (``op<dim>:`` / ``guide<dim>:``) and one authored family guide.
LEDGER_DIMS = {
    "math": {"registry": "opsmath", "table": "OPSMATH", "module": "mathops",
             "family": "math_metrology"},
    "optics": {"registry": "opsoptics", "table": "OPSOPTICS", "module": "optics",
               "family": "optics_imaging"},
    "lightfield": {"registry": "opslightfield", "table": "OPSLIGHTFIELD",
                   "module": "lightfield", "family": "lightfield_depth"},
}

_AUTHOR = "Kazufumi Furuse"
_LICENSE = "Apache-2.0"
_COPYRIGHT = f"© 2026 {_AUTHOR} — Fullseye operator documentation. Licensed under {_LICENSE}."

# ------------------------------------------------------------------ #
# registry access
# ------------------------------------------------------------------ #

def _lib_version() -> str:
    try:
        import fullseye
        return getattr(fullseye, "__version__", "0")
    except Exception:
        return "0"


_VERSION = _lib_version()


def _registry_fingerprint(recs) -> str:
    """Deterministic sha256 over op metadata — connects docs to the exact op set."""
    import hashlib
    payload = "\n".join(
        f"{r['dim']}|{r['name']}|{r['category']}|{r['in']}|{r['out']}|{r['halcon']}"
        for r in sorted(recs, key=lambda r: (r["dim"], r["name"])))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _catslug(cat: str) -> str:
    """Filesystem-safe category folder name (categories may contain '/' or '-')."""
    return re.sub(r"[^0-9a-zA-Z]+", "_", cat).strip("_").lower() or "misc"


def _family_map():
    """2-D op -> primary family (a gallery2d_* example id), and family -> [ops].

    Families are the coverage galleries (``examples/gallery2d_*.py``); each op is
    assigned to the gallery that exercises it (deterministic tie-break: the gallery
    covering the fewest ops, i.e. the most specific, then lexicographic)."""
    from op_example_index import build_index
    _, idx2d = build_index(split=True)
    fam_ops = {}
    for op, exs in idx2d.items():
        for e in exs:
            if e.startswith("gallery2d_"):
                fam_ops.setdefault(e, set()).add(op)
    size = {f: len(o) for f, o in fam_ops.items()}
    op_fam = {}
    for op, exs in idx2d.items():
        fams = sorted((e for e in exs if e.startswith("gallery2d_")),
                      key=lambda e: (size.get(e, 1 << 30), e))
        if fams:
            op_fam[op] = fams[0]
    return op_fam, fam_ops, idx2d


def _records():
    """Uniform per-op records for both dims. Returns (list, idx2d, op_fam, fam_ops)."""
    import ops
    op_fam, fam_ops, idx2d = _family_map()
    try:
        from op_example_index import build_index
        idx3d, _ = build_index(split=True)
    except Exception:
        idx3d = {}

    recs = []
    for o in ops.REGISTRY:
        fn = o.fn
        try:
            sig = str(inspect.signature(fn))
        except (TypeError, ValueError):
            sig = "(v, a, b)"
        recs.append({
            "dim": "2d", "name": o.name, "category": o.category,
            "in": o.in_sort, "out": o.out_sort,
            "halcon": (o.halcon or "").strip(),
            "doc": (fn.__doc__ or "").strip(),
            "module": "ops", "sig": sig,
            "examples": sorted(idx2d.get(o.name, [])),
            "family": op_fam.get(o.name),
        })
    try:
        import ops3d
        for name, info in ops3d.OPS3D.items():
            fn = info.get("func")
            try:
                sig = str(inspect.signature(fn)) if fn is not None else "(...)"
            except (TypeError, ValueError):
                sig = "(...)"
            ins = info["in"]
            ins = " × ".join(ins) if isinstance(ins, (list, tuple)) else str(ins)
            recs.append({
                "dim": "3d", "name": name, "category": info["category"],
                "in": ins, "out": info["out"],
                "halcon": "", "doc": (info.get("doc") or "").strip(),
                "module": info.get("module", "ops3d"), "sig": sig,
                "examples": sorted(idx3d.get(name, [])),
                "family": None, "gpu": bool(info.get("gpu")),
            })
    except Exception as e:  # ops3d needs torch-soft deps; corpus still builds for 2-D
        print(f"  (3-D registry unavailable: {e})", file=sys.stderr)
    for _dim, _meta in LEDGER_DIMS.items():
        try:
            ledger = getattr(__import__(_meta["registry"]), _meta["table"])
            from op_example_index import _index_for
            # ledger ops are demonstrated by scripts under examples/ (same dir as
            # 2-D); index them with the same call-detection used for the other dims.
            idx = _index_for(sorted(ledger), "examples")
            for name, info in ledger.items():
                fn = info.get("func")
                try:
                    sig = str(inspect.signature(fn)) if fn is not None else "(...)"
                except (TypeError, ValueError):
                    sig = "(...)"
                ins = info["in"]
                ins = " × ".join(ins) if isinstance(ins, (list, tuple)) else str(ins)
                doc = getattr(fn, "__doc__", None) or ""
                recs.append({
                    "dim": _dim, "name": name, "category": info["category"],
                    "in": ins, "out": info["out"],
                    # cleandoc: function docstrings carry the 4-space continuation
                    # indent, which Markdown would misread as a code block.
                    "halcon": "", "doc": inspect.cleandoc(doc).strip() if doc else "",
                    "module": info.get("module", _meta["module"]), "sig": sig,
                    "examples": sorted(idx.get(name, [])),
                    # one usage guide per ledger family, named after the coverage
                    # example that exercises its ops (2-D の gallery 命名と同型)
                    "family": _meta["family"],
                })
        except Exception as e:  # corpus still builds without a ledger
            print(f"  ({_dim} registry unavailable: {e})", file=sys.stderr)
    # mark ops whose name is registered more than once in their dim: a backend override
    # (e.g. backends_auto's _safe wrapper) shadows a core fallback of the same op. The note
    # for such a name describes the winner; flag it so the override is stated, not hidden.
    from collections import Counter
    for dim in ("2d", "3d"):
        cnt = Counter(r["name"] for r in recs if r["dim"] == dim)
        for r in recs:
            if r["dim"] == dim and cnt[r["name"]] > 1:
                r["override"] = True
    return recs, idx2d, op_fam, fam_ops


# ------------------------------------------------------------------ #
# per-op Markdown notes  (deterministic; source of truth)
# ------------------------------------------------------------------ #

def _rel(from_file: str, to_file: str) -> str:
    r = os.path.relpath(to_file, os.path.dirname(from_file)).replace(os.sep, "/")
    return r


def _op_md(rec, path, by_name):
    dim, name, cat = rec["dim"], rec["name"], rec["category"]
    ins, out = rec["in"], rec["out"]
    lines = []
    # frontmatter: machine-readable, stable field order
    fm = [
        f"op: {name}", f"dim: {dim}", f"category: {cat}",
        f"in: {ins}", f"out: {out}",
    ]
    if rec["halcon"]:
        fm.append(f"halcon: {rec['halcon']}")
    if rec.get("gpu"):
        fm.append("gpu: true")
    fm.append("examples: [" + ", ".join(rec["examples"]) + "]")
    fm.append(f"author: {_AUTHOR}")
    fm.append(f"license: {_LICENSE}")
    fm.append(f"version: {_VERSION}  # fullseye lib version this note was generated for")
    lines.append("---")
    lines.extend(fm)
    lines.append("---")
    lines.append("")
    lines.append(f"# {name} — {dim.upper()} `{cat}` op")
    lines.append("")
    lines.append(f"- **データ種**: `{ins}` → `{out}`")
    if dim == "2d":
        lines.append(f'- **呼び出し**: `fullseye.apply(img, "{name}", a=0.5, b=0.5)` '
                     "(2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)")
    else:
        reg_mod = ({"3d": "ops3d"}.get(dim)
                   or (LEDGER_DIMS[dim]["registry"] if dim in LEDGER_DIMS
                       else rec["module"]))
        lines.append(f"- **呼び出し**: `import {rec['module']}; {rec['module']}.{name}{rec['sig']}` "
                     f'(または `{reg_mod}.get("{name}")`)')
    if rec["halcon"]:
        lines.append(f"- **HALCON 相当**: `{rec['halcon']}`(意味・パラメータは HALCON リファレンスが参考になる)")
    if rec.get("gpu"):
        lines.append("- **GPU**: この op は GPU 経路あり(`device=\"cuda\"`)")
    if rec.get("override"):
        lines.append(f"- **上書き登録**: この名前は 2 回登録されている(core 実装 + backend の安全ラッパ)。"
                     "`apply` が実行するのは**後勝ちの安全版**(fail-closed ラッパ)。core 版は backend "
                     "不在時のフォールバックとして残る(登録順=Wave0 stable slot は不変、`tests/test_opdocs.py` "
                     "が上書き集合を pin)。")
    lines.append("")
    # usage / behaviour — honest: docstring if present, else typed contract only
    lines.append("## 使い方")
    lines.append("")
    if rec["doc"]:
        lines.append(rec["doc"])
    else:
        lines.append(f"型契約は `{ins} → {out}`。挙動の言語説明は下記のファミリ使い方ガイドと"
                     "実行可能サンプルを参照(ここでは推測を書かない)。")
    lines.append("")
    if dim == "optics":
        # family-wide fail-closed input contract for the optics ledger (grounded in
        # optics._finite_scalar / _require_image / _require_vec / the size caps —
        # every item below is a bug the 2026-09-01 adversarial pass actually found,
        # or a trap it was written to close).
        lines.append("## ファミリ共通の入力契約(fail-closed)")
        lines.append("")
        lines.append("optics の全 op は入力を検証してから計算する(黙って通さない):")
        lines.append("")
        lines.append("- **単位は引数名に埋め込む** — `_mm` / `_um` / `_deg` / `_mrad`。"
                     "mm と µm の取り違えは crash ではなく「もっともらしく間違った答え」"
                     "なので、名前で防ぐ。大きさから単位を推測する処理は一切しない。")
        lines.append("- **文字列は `ValueError`** — `float('50')` は成功してしまうため、"
                     "未パースの設定値が長さとして通り抜ける(実測: `thin_lens('50', '200')` が"
                     "もっともらしい 66.667 mm を返していた)。bool も `True == 1` の"
                     "暗黙昇格として拒否。")
        lines.append("- **complex / masked array は `ValueError`**(実数枠のみ。虚部の"
                     "無言切り捨て・マスク剥がしを拒否)。**NaN/Inf は全入力で `ValueError`**。")
        lines.append("- **0 除算とその親戚を名指しで拒否**: 焦点距離 0・曲率半径 0・"
                     "屈折率 <= 0・不透明な開口(全 0 なので正規化が 0/0)・総和 <= 0 の PSF・"
                     "S0 = 0 の Stokes ベクトル・物体が前側焦点にある(像が無限遠)。")
        lines.append("- **非有限を返すのは 2 op だけ、しかも契約として明記**: "
                     "`depth_of_field` の過焦点距離以遠の `far_mm = inf`(それが過焦点距離の"
                     "定義)と `gaussian_beam` のウエストでの `wavefront_radius_mm = inf`"
                     "(平面波面の曲率半径)。どちらも有限の相棒(`far_is_infinite` / "
                     "`curvature_per_mm`)を併せて返す。**それ以外の無言 NaN/Inf は内部で"
                     "検出して `ValueError`** —「float64 が溢れた」と「答えが無限大」は"
                     "別の主張なので、後者の顔で前者を返さない。")
        lines.append("- **サイズ上限**: 生成格子は `optics.MAX_GRID`(4096)、供給された"
                     "場/PSF/開口は `optics.MAX_FIELD_ELEMENTS`(2^24)、ABCD 素子列は "
                     "`optics.MAX_SYSTEM_ELEMENTS`(1024)、Zernike は "
                     "`MAX_ZERNIKE_TERMS`(512)/ `MAX_ZERNIKE_ORDER`(40)/ "
                     "`MAX_ZERNIKE_BASIS`(2^25)。小さな引数から巨大な内部確保が起きる経路"
                     "(実測: n_max=40 × 4096² で 108 GB)を fail-closed で塞ぐ。")
        lines.append("- **物理的に不可能な状態も拒否**: 偏光度 > 1 の Stokes ベクトル、"
                     "負の透過率、負の強度、n-|m| が奇数などの不正な Zernike 添字。")
        lines.append("")
    if dim == "math":
        # family-wide fail-closed input contract, stated once per note (grounded in
        # mathops._as_float64 / _require_* / _check_elements — the 2026-08 adversarial
        # audits' confirmed bug families, refused explicitly instead of silently).
        lines.append("## ファミリ共通の入力契約(fail-closed)")
        lines.append("")
        lines.append("mathops の全 op は入力を検証してから計算する(黙って通さない):")
        lines.append("")
        lines.append("- **complex 入力は `ValueError`** — float64 への強制変換は虚部を黙って捨てる"
                     "(numpy は ComplexWarning だけ出して「もっともらしく間違った」実数を返す)。"
                     "`.real`/`.imag`/`abs()` を明示するか、複素対応の complexops を使う。")
        lines.append("- **masked array(masked 要素あり)は `ValueError`** — マスクを剥がして"
                     "下の生値を使う暗黙変換を拒否。埋める/落とすを明示する。")
        lines.append("- **NaN/Inf は全入力で `ValueError`**(件数を明示して拒否 — 結果全体に伝播するため)。")
        lines.append("- **形状は厳格**: 1-D と 2-D を暗黙昇格・ブロードキャストしない"
                     "(vector 枠に matrix、matrix 枠に vector は `ValueError`。reshape を明示する)。")
        lines.append("- **サイズ上限**: 行列を取る op と `stat_histogram` の bins は "
                     "`mathops.MAX_ELEMENTS`(2^26 ≈ 6700 万要素)超で `ValueError`。")
        lines.append("")
    # family guide
    if rec.get("family"):
        gp = os.path.join(DOCS, dim if dim in LEDGER_DIMS else "2d",
                          "guides", rec["family"] + ".md")
        lines.append("## 詳しい使い方ガイド")
        lines.append("")
        lines.append(f"- [{rec['family']} ファミリ ガイド]({_rel(path, gp)})")
        lines.append("")
    # sample data + references (honest pointers to the curated catalogs)
    sp = os.path.join(DOCS, "SAMPLES.md")
    rp = os.path.join(_ROOT, "docs", "REFERENCES.md")
    lines.append("## 参考(サンプルデータ・文献)")
    lines.append("")
    lines.append(f"- [サンプルデータ カタログ(DL URL / ライセンス)]({_rel(path, sp)}) "
                 "— 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。")
    lines.append(f"- [演算子の来歴・参考文献]({_rel(path, rp)}) — この op 族の元になった研究/手法の出典。")
    if rec.get("family"):
        lines.append("- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。")
    lines.append("")
    # worked examples
    lines.append("## 実行できる例(この op を実際に呼ぶ検証済みサンプル)")
    lines.append("")
    if rec["examples"]:
        exdir = "examples_3d" if dim == "3d" else "examples"
        for e in rec["examples"]:
            ep = os.path.join(_ROOT, exdir, e + ".py")
            lines.append(f"- [{e}]({_rel(path, ep)}) — `py -3.11 {exdir}/{e}.py`")
    else:
        lines.append("- (まだありません)")
    lines.append("")
    # related ops: type-compatible successors + same-category siblings
    succ, sib = [], []
    for r2 in by_name.values():
        if r2["dim"] != dim or r2["name"] == name:
            continue
        if r2["category"] == cat and len(sib) < 8:
            sib.append(r2)
        r2in = r2["in"]
        if (out in (r2in.split(" × ") if isinstance(r2in, str) else [r2in])
                or r2in == "any" or out == "any") and len(succ) < 8:
            succ.append(r2)

    def _links(rs):
        return " · ".join(f"[{r['name']}]({_rel(path, _op_path(r))})" for r in rs) or "—"

    lines.append(f"## 型が繋がる次の op(`{out}` を入力に取れる)")
    lines.append("")
    lines.append(_links(succ))
    lines.append("")
    lines.append(f"## 同カテゴリ(`{cat}`)")
    lines.append("")
    lines.append(_links(sib))
    lines.append("")
    lines.append(f"---")
    lines.append(f"*Provenance: {rec['module']}.py — {dim.upper()} operator registry. "
                 "この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*")
    lines.append("")
    lines.append(_COPYRIGHT)
    lines.append("")
    return "\n".join(lines)


def _op_path(rec) -> str:
    return os.path.join(DOCS, rec["dim"], _catslug(rec["category"]), rec["name"] + ".md")


def cmd_md():
    recs, idx2d, op_fam, fam_ops = _records()
    by_name = {(r["dim"], r["name"]): r for r in recs}
    n = 0
    for rec in recs:
        p = _op_path(rec)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(_op_md(rec, p, by_name))
        n += 1
    # ensure guides dirs exist (authored separately)
    os.makedirs(os.path.join(DOCS, "2d", "guides"), exist_ok=True)
    for _d in LEDGER_DIMS:
        os.makedirs(os.path.join(DOCS, _d, "guides"), exist_ok=True)
    print(f"opdocs md: wrote {n} per-op notes under {DOCS}")
    return recs


# ------------------------------------------------------------------ #
# sample-data catalog  (real download URLs / licences)
# ------------------------------------------------------------------ #

def cmd_samples():
    out = ["# Fullseye サンプルデータ カタログ", "",
           "op の動作確認・デバッグに使える**実在**のサンプルデータ源(DL URL / ライセンス / 取得法)。"
           "同梱はせず**ユーザー DL 方式**(`fullseye` の `sample_data` / `sample_images`)。fail-closed"
           "(未取得なら明示エラー、捏造しない)。", ""]
    # 3-D / volume: real download URLs from sample_data.MANIFEST
    try:
        import sample_data as sd
        out.append("## 3-D / ボリューム(実 DL URL)")
        out.append("")
        out.append("| id | 種別 | アクセス | 出典 / DL URL |")
        out.append("|----|------|----------|----------------|")
        for e in sd.catalog():
            url = e.get("url") or e.get("source_page") or ""
            out.append(f"| `{e.get('id','')}` | {e.get('category','')} | {e.get('access','')} "
                       f"| <{url}> |")
        out.append("")
        out.append("取得: `py -3.11 -c \"import sample_data; sample_data.download('bunny', yes=True)\"` "
                   "(`access=direct` のみ自動 DL、`gated`/`info` は出典ページから手動)。", )
        out.append("")
    except Exception as e:
        out.append(f"(sample_data 利用不可: {e})\n")
    # 2-D images: skimage.data (BSD/public) + synthetic own-work
    try:
        import sample_images as si
        entries = si.entries() if hasattr(si, "entries") else [{"name": n} for n in si.names()]
        out.append("## 2-D 画像(skimage.data(BSD/public)+ 合成)")
        out.append("")
        out.append("| name | 出典 | ライセンス |")
        out.append("|------|------|-----------|")
        for e in entries:
            out.append(f"| `{e.get('name','')}` | {e.get('source','')} | {e.get('licence', e.get('license',''))} |")
        out.append("")
        out.append("2-D は外部 DL 不要(`skimage.data` は pip 導入済、合成は自作)。"
                   "`import sample_images; sample_images.load('<name>')` で取得。", )
        out.append("")
    except Exception as e:
        out.append(f"(sample_images 利用不可: {e})\n")
    out.append("---")
    out.append(_COPYRIGHT)
    out.append("")
    os.makedirs(DOCS, exist_ok=True)
    with open(os.path.join(DOCS, "SAMPLES.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print(f"opdocs samples: wrote {os.path.join(DOCS, 'SAMPLES.md')}")


# ------------------------------------------------------------------ #
# auto TOC  (walks the folder hierarchy)
# ------------------------------------------------------------------ #

def _md_title(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("# "):
                    return line[2:].strip()
    except OSError:
        pass
    return os.path.splitext(os.path.basename(path))[0]


def _walk_ops(dim: str):
    """category -> sorted [op names] for a dimension, from the folder tree."""
    base = os.path.join(DOCS, dim)
    cats = {}
    if not os.path.isdir(base):
        return cats
    for cat in sorted(os.listdir(base)):
        cdir = os.path.join(base, cat)
        if not os.path.isdir(cdir) or cat == "guides":
            continue
        ops_ = sorted(os.path.splitext(f)[0] for f in os.listdir(cdir) if f.endswith(".md"))
        if ops_:
            cats[cat] = ops_
    return cats


def cmd_toc():
    written = 0
    dims = [d for d in ("2d", "3d", *LEDGER_DIMS)
            if os.path.isdir(os.path.join(DOCS, d))]
    # per-dimension INDEX
    dim_counts = {}
    for dim in dims:
        cats = _walk_ops(dim)
        total = sum(len(v) for v in cats.values())
        dim_counts[dim] = (len(cats), total)
        out = [f"# {dim.upper()} operator help — {total} ops in {len(cats)} categories", "",
               "自動生成(`tools/opdocs.py toc`)。フォルダ階層 `docs/ops/" + dim + "/<category>/<op>.md` を走査。", ""]
        guides = sorted(glob.glob(os.path.join(DOCS, dim, "guides", "*.md")))
        if guides:
            out.append("## ファミリ使い方ガイド(用途→op の教材)")
            out.append("")
            for g in guides:
                stem = os.path.splitext(os.path.basename(g))[0]
                out.append(f"- [{stem}](guides/{stem}.md) — {_md_title(g)}")
            out.append("")
        out.append("## カテゴリ")
        out.append("")
        for cat in sorted(cats):
            out.append(f"### {cat} ({len(cats[cat])})")
            out.append("")
            out.append(" · ".join(f"[{op}]({cat}/{op}.md)" for op in cats[cat]))
            out.append("")
        out.append("---")
        out.append(_COPYRIGHT)
        out.append("")
        with open(os.path.join(DOCS, dim, "INDEX.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(out))
        written += 1
    # top INDEX
    try:
        recs, *_ = _records()
        fp = _registry_fingerprint(recs)
    except Exception:
        fp = "?"
    top = [f"<!-- fullseye {_VERSION} · op-registry fingerprint {fp} · generated by tools/opdocs.py -->",
           "<!-- md(このコーパス)と code(op レジストリ)の版接続: この fingerprint が live レジストリと -->",
           "<!-- 一致することを CI drift テストが強制する(再生成==commit 済み)。手編集しないこと。 -->",
           "# Fullseye Operator Docs — AI 使い方コーパス", "",
           f"**fullseye {_VERSION}** の op ドキュメント。op ごとの使い方を Markdown で1件1ファイル"
           "(RAD コーパス形状)に持ち、Studio の HTML ヘルプはここから一括変換で生成する"
           "(`tools/opdocs.py html`)。この目次はフォルダ階層から自動生成。", ""]
    for dim in dims:
        nc, nt = dim_counts[dim]
        top.append(f"- [{dim.upper()} operators](./{dim}/INDEX.md) — {nt} ops / {nc} categories")
    top.append("- [サンプルデータ カタログ(DL URL / ライセンス)](./SAMPLES.md)")
    top.append("- [演算子の来歴・参考文献](../REFERENCES.md)")
    top.append("")
    top.append("## 使い方(assistant 向け)")
    top.append("")
    top.append("1. 用途(入力データ種・欲しい出力)から近い**ファミリ使い方ガイド**(`2d/guides/`)を読む。")
    top.append("2. 各 op ノートの**データ種 `in → out`** が繋がるように連鎖を組む。")
    top.append("3. 挙動が不確かなら、そのノートの**実行できる例**を走らせて GT 出力で確かめる。")
    top.append("")
    top.append("---")
    top.append(_COPYRIGHT)
    top.append("")
    with open(os.path.join(DOCS, "INDEX.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(top))
    written += 1
    print(f"opdocs toc: wrote {written} INDEX.md ({', '.join(f'{d}:{dim_counts[d][1]}ops' for d in dims)}) "
          f"fp={fp}")


# ------------------------------------------------------------------ #
# bulk Markdown -> Studio HTML  (derived; never authored twice)
# ------------------------------------------------------------------ #

_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_ICODE = re.compile(r"`([^`]+)`")
_BOLD = re.compile(r"\*\*([^*]+)\*\*")


def _rewrite_link(text: str, target: str) -> str:
    """Map a Markdown link target to a Studio QTextBrowser scheme.

    Corpus-navigation docs (SAMPLES/REFERENCES/INDEX) have no Studio handler and would
    mis-route to a bogus op card, so they render as plain text (their working relative
    links live on in the Markdown corpus for GitHub/Obsidian/RAD)."""
    t = target
    stem = os.path.splitext(os.path.basename(t))[0]
    if t.endswith(".md") and stem in ("SAMPLES", "REFERENCES", "INDEX"):
        return _html.escape(text)
    if t.endswith(".py") and "examples_3d/" in t:
        href = "example3d:" + stem
    elif t.endswith(".py") and "examples/" in t:
        href = "example2d:" + stem
    elif t.endswith(".md") and "/guides/" in t:
        href = "guide2d:" + stem
    elif t.endswith(".md"):                     # sibling op note
        href = "op:" + stem
    else:
        href = t
    return f'<a style="color:{_CODE}" href="{_html.escape(href, quote=True)}">{_html.escape(text)}</a>'


def _inline(s: str) -> str:
    # protect code spans, then escape, then re-insert styled code + bold + links
    parts = []
    idx = 0
    for m in _ICODE.finditer(s):
        parts.append(("t", s[idx:m.start()]))
        parts.append(("c", m.group(1)))
        idx = m.end()
    parts.append(("t", s[idx:]))
    out = []
    for kind, txt in parts:
        if kind == "c":
            out.append(f'<code style="color:{_CODE}">{_html.escape(txt)}</code>')
            continue
        # links first (escape handled inside), then bold, then escape remaining text
        pos = 0
        buf = []
        for m in _LINK.finditer(txt):
            buf.append(_bold_escape(txt[pos:m.start()]))
            buf.append(_rewrite_link(m.group(1), m.group(2)))
            pos = m.end()
        buf.append(_bold_escape(txt[pos:]))
        out.append("".join(buf))
    return "".join(out)


def _bold_escape(s: str) -> str:
    pos = 0
    buf = []
    for m in _BOLD.finditer(s):
        buf.append(_html.escape(s[pos:m.start()]))
        buf.append(f"<b>{_html.escape(m.group(1))}</b>")
        pos = m.end()
    buf.append(_html.escape(s[pos:]))
    return "".join(buf)


def md_to_html(md: str) -> str:
    """Convert the controlled Markdown subset we emit into Studio's inline-styled HTML."""
    lines = md.split("\n")
    # strip frontmatter -> render as a muted meta line
    meta = {}
    if lines and lines[0].strip() == "---":
        j = 1
        while j < len(lines) and lines[j].strip() != "---":
            if ":" in lines[j]:
                k, v = lines[j].split(":", 1)
                meta[k.strip()] = v.strip()
            j += 1
        lines = lines[j + 1:]
    out = []
    in_code = False
    code_lang = ""
    code_buf = []
    for line in lines:
        st = line.strip()
        if st.startswith("```"):
            if in_code:
                # mermaid / math: QTextBrowser can't render these, so we keep the source
                # in a labelled block (Markdown-native viewers — GitHub/Obsidian/RAD — do render).
                label = ""
                if code_lang in ("mermaid", "math"):
                    kind = "Mermaid 図" if code_lang == "mermaid" else "数式(LaTeX)"
                    label = (f'<p style="color:{_MUTE};font-size:11px;margin:6px 0 0 0">'
                             f'{kind}(ソース):</p>')
                out.append(label + f'<pre style="background:#12141b;border:1px solid #2c313f;'
                           f'padding:6px;color:{_CODE}">' + _html.escape("\n".join(code_buf)) + "</pre>")
                code_buf = []
                in_code = False
                code_lang = ""
            else:
                in_code = True
                code_lang = st[3:].strip().lower()
            continue
        if in_code:
            code_buf.append(line)
            continue
        if not st:
            continue
        if st == "---":
            out.append('<hr style="border:0;border-top:1px solid #2c313f">')
        elif st.startswith("#### "):
            out.append(f'<h4 style="color:{_TEAL};margin:6px 0 2px 0">{_inline(st[5:])}</h4>')
        elif st.startswith("### "):
            out.append(f'<h3 style="color:{_TEAL};margin:8px 0 2px 0">{_inline(st[4:])}</h3>')
        elif st.startswith("## "):
            out.append(f'<h3 style="color:{_TEAL};margin:10px 0 2px 0">{_inline(st[3:])}</h3>')
        elif st.startswith("# "):
            out.append(f'<h2 style="color:{_AMBER};margin:0 0 4px 0">{_inline(st[2:])}</h2>')
        elif st.startswith("- ") or st.startswith("* "):
            out.append(f'<p style="margin:2px 0 2px 12px">• {_inline(st[2:])}</p>')
        else:
            out.append(f"<p>{_inline(st)}</p>")
    if in_code and code_buf:
        out.append(f'<pre style="background:#12141b;border:1px solid #2c313f;padding:6px;color:{_CODE}">'
                   + _html.escape("\n".join(code_buf)) + "</pre>")
    return "\n".join(out) + "\n"


def _write_generated(path: str, body: str) -> bool:
    """Write a generated help page, but never clobber a hand-authored override.

    Studio's ``op_help_html`` reads ``op_help/<name>.html`` from the root, so the
    generated 2-D pages must live there too. A file counts as hand-authored (and is
    preserved) unless it carries the generated marker. This lets the 3 rich hand-written
    pages (gaussian/otsu/sobel_mag) win while every other op still gets a linked card."""
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                head = f.read(len(_GEN_MARK) + 4)
        except OSError:
            head = ""
        if _GEN_MARK not in head:
            return False  # hand-authored override — leave it
    with open(path, "w", encoding="utf-8") as f:
        f.write(_GEN_MARK + "\n" + body)
    return True


def cmd_html():
    os.makedirs(HELP_ROOT, exist_ok=True)
    n = skipped = 0
    # per-op 2-D pages from their Markdown notes -> op_help/<name>.html (Studio's lookup dir)
    for cat in sorted(os.listdir(os.path.join(DOCS, "2d"))):
        cdir = os.path.join(DOCS, "2d", cat)
        if not os.path.isdir(cdir) or cat == "guides":
            continue
        for f in sorted(os.listdir(cdir)):
            if not f.endswith(".md"):
                continue
            with open(os.path.join(cdir, f), encoding="utf-8") as fh:
                md = fh.read()
            op = f[:-3]
            if _write_generated(os.path.join(HELP_ROOT, op + ".html"), md_to_html(md)):
                n += 1
            else:
                skipped += 1
    # per-op 3-D pages from their Markdown notes -> op_help/3d/<name>.html (a namespaced
    # subdir: 2-D and 3-D op names can collide, e.g. fill_holes, so 3-D help is kept apart).
    # Same md=source-of-truth path as 2-D — this supersedes the old standalone
    # tools/gen_op_help_3d.py (retired), so 3-D help is no longer double-authored. A 3-D note's
    # sibling / next-op links target 3-D ops, so their op: anchors are rewritten to op3d: for a
    # future 3-D operator browser (2-D op: anchors are left untouched).
    n3 = 0
    d3out = os.path.join(HELP_ROOT, "3d")
    d3src = os.path.join(DOCS, "3d")
    if os.path.isdir(d3src):
        os.makedirs(d3out, exist_ok=True)
        for cat in sorted(os.listdir(d3src)):
            cdir = os.path.join(d3src, cat)
            if not os.path.isdir(cdir):
                continue
            for f in sorted(os.listdir(cdir)):
                if not f.endswith(".md"):
                    continue
                with open(os.path.join(cdir, f), encoding="utf-8") as fh:
                    md = fh.read()
                html3d = md_to_html(md).replace('href="op:', 'href="op3d:')
                if _write_generated(os.path.join(d3out, f[:-3] + ".html"), html3d):
                    n3 += 1
    # per-op ledger pages (math / optics) from their Markdown notes ->
    # op_help/<dim>/<name>.html (namespaced like 3-D; sibling/next-op anchors become
    # op<dim>:, the guide anchor guide<dim>:, for a future ledger-operator browser —
    # Studio's 2-D lookup dir stays uncluttered).
    nm = 0
    for ldim in LEDGER_DIMS:
        dmsrc = os.path.join(DOCS, ldim)
        if not os.path.isdir(dmsrc):
            continue
        dmout = os.path.join(HELP_ROOT, ldim)
        os.makedirs(dmout, exist_ok=True)
        for cat in sorted(os.listdir(dmsrc)):
            cdir = os.path.join(dmsrc, cat)
            if not os.path.isdir(cdir) or cat == "guides":
                continue
            for f in sorted(os.listdir(cdir)):
                if not f.endswith(".md"):
                    continue
                with open(os.path.join(cdir, f), encoding="utf-8") as fh:
                    md = fh.read()
                htmlm = (md_to_html(md)
                         .replace('href="op:', 'href="op%s:' % ldim)
                         .replace('href="guide2d:', 'href="guide%s:' % ldim))
                if _write_generated(os.path.join(dmout, f[:-3] + ".html"), htmlm):
                    nm += 1
    # family guides -> guide_<family>.html (always generated from guide md; the 2-D
    # gallery guides and the ledger family guides share the flat guide_ namespace —
    # stems are distinct by construction: gallery2d_* / handpose / math_metrology /
    # optics_imaging)
    g = 0
    for gdim in ("2d", *LEDGER_DIMS):
        gdir = os.path.join(DOCS, gdim, "guides")
        if not os.path.isdir(gdir):
            continue
        for f in sorted(os.listdir(gdir)):
            if not f.endswith(".md"):
                continue
            with open(os.path.join(gdir, f), encoding="utf-8") as fh:
                md = fh.read()
            _write_generated(os.path.join(HELP_ROOT, "guide_" + f[:-3] + ".html"), md_to_html(md))
            g += 1
    print(f"opdocs html: wrote {n} 2-D op pages ({skipped} hand-authored preserved) "
          f"+ {n3} 3-D op pages + {nm} ledger op pages ({'/'.join(LEDGER_DIMS)}) "
          f"+ {g} family guides to {HELP_ROOT}")


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "all"
    if cmd in ("md", "all"):
        cmd_md()
    if cmd in ("samples", "all"):
        cmd_samples()
    if cmd in ("toc", "all"):
        cmd_toc()
    if cmd in ("html", "all"):
        cmd_html()
    if cmd not in ("md", "samples", "toc", "html", "all"):
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
