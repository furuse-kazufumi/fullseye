"""Generate per-operator help pages for the 3-D operator registry (dev tool).

Every op in ``ops3d`` gets a small self-contained HTML help card in
``studio_assets/op_help/3d/<name>.html`` — the same visual style as the 2-D
op-help cards Studio shows, but sourced from the typed 3-D registry (category,
input/output kinds, one-line doc, call signature, and type-compatible neighbours
found via ``ops3d.compatible``). These feed the docs gallery and a future Studio
3-D operator browser so the 230 ops are **discoverable**, not just importable.

    py -3.11 tools/gen_op_help_3d.py

Re-run whenever the registry changes. Not shipped as code (a dev tool); the
generated HTML under ``studio_assets/op_help/3d`` DOES ship via package-data.
"""
from __future__ import annotations

import html
import inspect
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
_OUT = os.path.join(_ROOT, "studio_assets", "op_help", "3d")

_AMBER = "#f5a524"
_TEAL = "#17b8a6"
_MUTE = "#8b91a0"


def _signature(fn) -> str:
    try:
        return str(inspect.signature(fn))
    except (TypeError, ValueError):
        return "(...)"


def _card(name, info, reg) -> str:
    cat = info["category"]
    ins = " × ".join(info["in"]) if isinstance(info["in"], (list, tuple)) else str(info["in"])
    out = info["out"]
    doc = info.get("doc") or ""
    module = info.get("module", "")
    fn = info.get("func")
    sig = _signature(fn) if fn is not None else "(...)"

    # type-compatible successors (ops whose input accepts this op's output) — the
    # "what can follow this" neighbourhood the typed grammar makes explicit.
    try:
        nxt = [n for n in reg if out in (reg[n]["in"] if isinstance(reg[n]["in"], (list, tuple)) else [reg[n]["in"]])]
    except Exception:
        nxt = []
    nxt = [n for n in nxt if n != name][:6]
    # same-category siblings
    sib = [n for n in reg if reg[n]["category"] == cat and n != name][:6]

    def _oplinks(names):
        return " · ".join(
            f'<a style="color:#22d3bf" href="op3d:{html.escape(n)}">{html.escape(n)}</a>' for n in names
        ) or '<span style="color:%s">—</span>' % _MUTE

    return f"""<h2 style="color:{_AMBER};margin:0 0 4px 0">{html.escape(name)} <span style="color:{_MUTE};font-size:11px">· {html.escape(cat)} · 3D</span></h2>
<p style="color:{_MUTE};margin:2px 0"><b>{html.escape(ins)} → {html.escape(out)}</b></p>
<p>{html.escape(doc)}</p>

<h3 style="color:{_TEAL};margin:8px 0 2px 0">Call signature</h3>
<pre style="background:#12141b;border:1px solid #2c313f;padding:6px;color:#22d3bf">{html.escape(module)}.{html.escape(name)}{html.escape(sig)}</pre>

<h3 style="color:{_TEAL};margin:8px 0 2px 0">Type-compatible next ops (out = {html.escape(out)})</h3>
<p>{_oplinks(nxt)}</p>

<h3 style="color:{_TEAL};margin:8px 0 2px 0">Same category ({html.escape(cat)})</h3>
<p>{_oplinks(sib)}</p>

<p style="color:{_MUTE};font-size:11px">Provenance: {html.escape(module)}.py (3-D operator registry ops3d). See docs/EXAMPLES_3D.md for worked examples.</p>
"""


def main():
    import ops3d
    os.makedirs(_OUT, exist_ok=True)
    reg = ops3d.OPS3D
    n = 0
    for name, info in sorted(reg.items()):
        with open(os.path.join(_OUT, name + ".html"), "w", encoding="utf-8") as f:
            f.write(_card(name, info, reg))
        n += 1
    # a small index the docs / Studio can enumerate
    cats = {}
    for name, info in reg.items():
        cats.setdefault(info["category"], []).append(name)
    with open(os.path.join(_OUT, "INDEX.html"), "w", encoding="utf-8") as f:
        f.write(f'<h2 style="color:{_AMBER}">3-D operator help — {n} ops in {len(cats)} categories</h2>\n')
        for cat in sorted(cats):
            names = " · ".join(
                f'<a style="color:#22d3bf" href="op3d:{html.escape(x)}">{html.escape(x)}</a>'
                for x in sorted(cats[cat]))
            f.write(f'<p><b style="color:{_TEAL}">{html.escape(cat)}</b><br>{names}</p>\n')
    print(f"wrote {n} op-help cards + INDEX.html to {_OUT} ({len(cats)} categories)")


if __name__ == "__main__":
    main()
