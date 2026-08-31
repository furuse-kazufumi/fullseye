# -*- coding: utf-8 -*-
"""op -> worked-example index.

Parses the runnable examples (``examples/`` for 2-D, ``examples_3d/`` for 3-D) and
maps every operator name to the example scripts that actually call it, so op help /
the op catalog can link each operator to a sample that demonstrates it (HDevelop
style) and so coverage gaps are measurable per op.

An op counts as demonstrated by an example when the example source *calls* it —
``op(`` / ``.op(`` for the direct-call 3-D ops, or the op name as a quoted string
(``apply(img, "op", ...)`` / pipeline specs) for the 2-D registry ops. Comments and
substrings of longer identifiers are excluded by the word-boundary match.

Usage::

    from tools.op_example_index import build_index
    idx = build_index()                 # {"gaussian": ["signal_filter", ...], ...}
    idx3d, idx2d = build_index(split=True)
"""
from __future__ import annotations

import glob
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def _sources(subdir: str) -> dict:
    """example id (file stem) -> source text, for a directory of scripts."""
    out = {}
    for f in sorted(glob.glob(os.path.join(ROOT, subdir, "*.py"))):
        stem = os.path.splitext(os.path.basename(f))[0]
        if stem.startswith("_") or stem == "__init__":
            continue
        with open(f, encoding="utf-8") as fh:
            out[stem] = fh.read()
    return out


def _op_names_3d() -> list:
    import ops3d
    names = []
    for cat in ops3d.categories():
        for t in ops3d._CATALOG[cat]:
            names.append(t[0])
    return names


def _op_names_2d() -> list:
    """例が要る 2-D op の名前。

    除外するもの:
      * ``identity`` — 何もしない op に例は書けない。
      * **橋渡し op(``category == "typed"``、``tb_`` 接頭辞)** — これは新しい
        能力ではなく、型付きカタログ側の既存 op を進化語彙から引くための
        **別名**である。実体の例・ドキュメント・テストは ``docs/ops`` 配下に
        カタログ名で既にあり、例は実 op 名で書かれるので ``tb_`` 名が一致する
        ことは原理的に無い。ここで数えると「例の無い op が 59 個ある」という
        **誤った赤**になり、本当に例が欠けている op を隠してしまう
        (実測 2026-09-01: 橋渡し導入直後にこの不変条件が赤くなった)。
        橋渡し op の品質は ``tests/test_backends_typed.py`` が別途固定する。
    """
    import ops
    return [o.name for o in ops.REGISTRY
            if o.name != "identity" and o.category != "typed"]


def _called(name: str, src: str) -> bool:
    """True if `src` calls the op (direct call or via a quoted-name dispatch)."""
    esc = re.escape(name)
    if re.search(r"(?<![\w.])" + esc + r"\s*\(", src):      # name(
        return True
    if re.search(r"\." + esc + r"\s*\(", src):              # .name(
        return True
    if re.search(r"""['"]""" + esc + r"""['"]""", src):     # "name" / 'name' (apply/pipeline)
        return True
    return False


def _index_for(names: list, subdir: str) -> dict:
    srcs = _sources(subdir)
    idx = {}
    for n in names:
        idx[n] = [ex for ex, s in srcs.items() if _called(n, s)]
    return idx


def build_index(split: bool = False):
    """op name -> [example ids]. ``split=True`` returns ``(idx3d, idx2d)``."""
    idx3d = _index_for(_op_names_3d(), "examples_3d")
    idx2d = _index_for(_op_names_2d(), "examples")
    if split:
        return idx3d, idx2d
    merged = dict(idx2d)
    merged.update(idx3d)                                   # 3-D names win on the rare clash
    return merged


def coverage_report():
    """Print a per-dimension coverage summary and the uncovered op lists."""
    idx3d, idx2d = build_index(split=True)
    for label, idx in (("3-D (ops3d)", idx3d), ("2-D (ops.REGISTRY)", idx2d)):
        cov = [n for n, ex in idx.items() if ex]
        unc = sorted(n for n, ex in idx.items() if not ex)
        print(f"{label}: {len(cov)}/{len(idx)} covered "
              f"({100 * len(cov) / max(len(idx), 1):.1f}%), {len(unc)} uncovered")
    return idx3d, idx2d


if __name__ == "__main__":
    coverage_report()
