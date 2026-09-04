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

# repo をそのまま clone した状態(pip install -e . を打っていない / install の
# マッピングが古い)でも動くように、リポジトリ直下を import パスへ入れる。
# 2026-09-02 実測: これが無い 29 本は editable install に寄生しており、
# finder の MAPPING から torch_lazy が抜けた瞬間に 6 本が ModuleNotFoundError
# で全滅した(docs/OP_CATALOG.md は裸の起動コマンドを載せている)。
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))


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


def _strip_prose(src: str) -> str:
    """コメントと docstring を空白へ潰したソースを返す(誤リンク防止)。

    2026-09-04 の実バグ: docstring の散文 "boundary (printed)" が `boundary\s*\(`
    に当たり、**呼んでいない op を呼んだことにして**偽リンクを生んだ。「<op 名> (」という
    散文はどの example にも起こりうる ―― 言い換えで避けるのは対症療法なので、走査の前に
    コメントと docstring を落とす。

    docstring 以外の文字列リテラルは**残す**: 2-D の op 名は `apply(img, "gaussian")`
    のように文字列で渡すのが正規の呼び方で、ここを落とすと本物のリンクが消える。

    ★ `ast` の `col_offset` は **UTF-8 バイト**基準である。日本語コメントだらけのこの
    リポジトリで文字数として扱うと位置が右へずれ、**docstring の代わりに直後の実コードを
    消す**(実測: `X.match_sh_descriptor(a, b)` が消えてカバレッジが偽の未到達になった)。
    行ごとにバイト列へ直してから文字位置へ戻す。

    パースに失敗したソースは原文をそのまま返す(この索引のために example を落とさない)。
    """
    import ast
    import io
    import tokenize

    try:
        tree = ast.parse(src)
    except SyntaxError:
        return src

    lines = src.splitlines(keepends=True)

    def _char_col(row: int, byte_col: int) -> int:
        """1-based 行 `row` の UTF-8 バイト列位置 → 文字位置。"""
        if not (1 <= row <= len(lines)):
            return byte_col
        return len(lines[row - 1].encode("utf-8")[:byte_col].decode("utf-8", "ignore"))

    def _blank(node):
        r0, r1 = node.lineno, node.end_lineno
        c0, c1 = _char_col(r0, node.col_offset), _char_col(r1, node.end_col_offset)
        for r in range(r0, r1 + 1):
            ln = lines[r - 1]
            lo = c0 if r == r0 else 0
            hi = c1 if r == r1 else len(ln)
            keep = "".join(c if c == chr(10) else " " for c in ln[lo:hi])
            lines[r - 1] = ln[:lo] + keep + ln[hi:]

    for parent in ast.walk(tree):
        if not isinstance(parent, (ast.Module, ast.ClassDef, ast.FunctionDef,
                                   ast.AsyncFunctionDef)):
            continue
        body = getattr(parent, "body", None)
        if not body:
            continue
        first = body[0]
        if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)):
            _blank(first.value)
    stripped = "".join(lines)

    # コメント(# 以降)も落とす。tokenize は str 上で動くので列は**文字**位置。
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(stripped).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return stripped
    out = stripped.splitlines(keepends=True)
    for tok in toks:
        if tok.type != tokenize.COMMENT:
            continue
        r = tok.start[0]
        if not (1 <= r <= len(out)):
            continue
        ln = out[r - 1]
        lo, hi = tok.start[1], tok.end[1]
        out[r - 1] = ln[:lo] + " " * max(hi - lo, 0) + ln[hi:]
    return "".join(out)


def _called(name: str, src: str) -> bool:
    """True if `src` calls the op (direct call or via a quoted-name dispatch)."""
    src = _strip_prose(src)
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
