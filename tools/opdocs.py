# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opdocs — single-source-of-truth operator documentation (Markdown) + derived help.

The Markdown under ``docs/ops/`` is the **source of truth** for operator docs: one
note per operator (``docs/ops/<dim>/<category>/<op>.md``), a hand/agent-authored
family usage guide per op-family (``docs/ops/2d/guides/<family>.md``), and an
**auto-generated** table of contents that simply walks the folder hierarchy. Studio's
per-op HTML help (``studio_assets/op_help/2d/*.html``) is produced by **bulk-converting**
that Markdown — never authored twice. The same Markdown tree is shaped as an AI-usage
corpus (file-per-note) so an assistant can grasp *how to use* each op.

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
HELP2D = os.path.join(_ROOT, "studio_assets", "op_help", "2d")

_AMBER = "#f5a524"
_TEAL = "#17b8a6"
_MUTE = "#8b91a0"
_CODE = "#22d3bf"

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
        lines.append(f"- **呼び出し**: `import {rec['module']}; {rec['module']}.{name}{rec['sig']}` "
                     f'(または `ops3d.get("{name}")`)')
    if rec["halcon"]:
        lines.append(f"- **HALCON 相当**: `{rec['halcon']}`(意味・パラメータは HALCON リファレンスが参考になる)")
    if rec.get("gpu"):
        lines.append("- **GPU**: この op は GPU 経路あり(`device=\"cuda\"`)")
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
    # family guide
    if rec.get("family"):
        gp = os.path.join(DOCS, "2d", "guides", rec["family"] + ".md")
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
    # ensure guides dir exists (authored separately)
    os.makedirs(os.path.join(DOCS, "2d", "guides"), exist_ok=True)
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
    dims = [d for d in ("2d", "3d") if os.path.isdir(os.path.join(DOCS, d))]
    # per-dimension INDEX
    dim_counts = {}
    for dim in dims:
        cats = _walk_ops(dim)
        total = sum(len(v) for v in cats.values())
        dim_counts[dim] = (len(cats), total)
        out = [f"# {dim.upper()} operator help — {total} ops in {len(cats)} categories", "",
               "自動生成(`tools/opdocs.py toc`)。フォルダ階層 `docs/ops/" + dim + "/<category>/<op>.md` を走査。", ""]
        if dim == "2d":
            guides = sorted(glob.glob(os.path.join(DOCS, "2d", "guides", "*.md")))
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
    """Map a Markdown link target to a Studio QTextBrowser scheme."""
    t = target
    stem = os.path.splitext(os.path.basename(t))[0]
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


def cmd_html():
    os.makedirs(HELP2D, exist_ok=True)
    n = 0
    # per-op 2-D pages from their Markdown notes
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
            with open(os.path.join(HELP2D, op + ".html"), "w", encoding="utf-8") as fh:
                fh.write(md_to_html(md))
            n += 1
    # family guides -> guide_<family>.html
    g = 0
    gdir = os.path.join(DOCS, "2d", "guides")
    if os.path.isdir(gdir):
        for f in sorted(os.listdir(gdir)):
            if not f.endswith(".md"):
                continue
            with open(os.path.join(gdir, f), encoding="utf-8") as fh:
                md = fh.read()
            with open(os.path.join(HELP2D, "guide_" + f[:-3] + ".html"), "w", encoding="utf-8") as fh:
                fh.write(md_to_html(md))
            g += 1
    print(f"opdocs html: wrote {n} op pages + {g} family guides to {HELP2D}")


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
