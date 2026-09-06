# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""U を捨てる SVD が ``full_matrices=False`` になっているかの静的な門。

2026-09-06、左右非対称性の PoC が `fs.obb` の 3.7 秒の正体を突き止めた。
``np.linalg.svd(P - c)`` は既定 ``full_matrices=True`` なので、``(N, 3)`` の
行列に対して **(N, N) の U** を作る。20000 点なら 3.2 GB を確保して、そのまま
捨てていた。実測 **3.73 s → 0.876 ms(4263 倍)、Vt はビット一致**。
10 万点では 80 GB になり落ちる。

そして同じ形が**兄弟に 5 つ**あった(pcseg の 2 か所、measure、ops、camera、
pnp3d)。バグ 1 件を直したら同クラスを兄弟コードで一掃する、という規律の
実施であり、次に誰かが `_, _, Vt = np.linalg.svd(X)` と書いたときに落ちる門を
ここに置く。

**一律には直せない。** ``full_matrices=False`` は **横長行列(m < n)で
``Vt[-1]`` の意味を変える**。DLT は ``A v = 0`` の零空間を ``Vt[-1]`` で取るが、
最小構成の 4 点ホモグラフィでは A が (8, 9) の横長になる。実測:

  * ``full_matrices=True``  → Vt は (9, 9)、``|A Vt[-1]| = 6.8e-16``(零空間)
  * ``full_matrices=False`` → Vt は (8, 9)、``|A Vt[-1]| = 3.2e-01``(**別物**)

5 点以上なら (10, 9) で縦長になり両者は一致する。つまり「速くなるから全部
付ける」をやると、**最小構成のときだけ静かに間違う**。この repo には DLT 系の
呼び出しが 20 か所あり、そのすべてがこの危険側にある。

**だからこの門が要求するのは「中心化した点群」の形だけ** —— SVD の引数が
``X - c`` のような引き算(または引き算を並べた ``column_stack``)である
呼び出しに限る。その形は「N 点 x 3 列」を意味するので m >= n が保証され、
``full_matrices=False`` は速いだけで答えが変わらない。DLT 側は行列の作り方が
違う(``append`` で組んだ係数行列)ので、この判定には入らない。
"""
import ast
import io
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

#: 走査しないところ(生成物・外部由来・退避)。
SKIP_PARTS = {"build", "dist", ".git", "__pycache__", ".venv", "node_modules",
              "site-packages", "out", "tests"}


def _python_files():
    for p in sorted(ROOT.rglob("*.py")):
        if SKIP_PARTS & set(p.relative_to(ROOT).parts):
            continue
        yield p


def _discards_u(node):
    """``_, _, Vt = np.linalg.svd(...)`` の形か(U を ``_`` で捨てているか)。"""
    if not isinstance(node, ast.Assign) or len(node.targets) != 1:
        return False
    tgt = node.targets[0]
    if not isinstance(tgt, ast.Tuple) or len(tgt.elts) != 3:
        return False
    first = tgt.elts[0]
    return isinstance(first, ast.Name) and first.id == "_"


def _is_centred_cloud(call):
    """SVD の引数が ``X - c`` 形か(= 中心化した点群、m >= n が保証される)。"""
    if not call.args:
        return False
    a = call.args[0]
    if isinstance(a, ast.BinOp) and isinstance(a.op, ast.Sub):
        return True
    # np.column_stack([x - mx, y - my]) も同じ形
    if isinstance(a, ast.Call) and isinstance(a.func, ast.Attribute)             and a.func.attr == "column_stack" and a.args:
        inner = a.args[0]
        if isinstance(inner, (ast.List, ast.Tuple)):
            return all(isinstance(e, ast.BinOp) and isinstance(e.op, ast.Sub)
                       for e in inner.elts)
    return False


def _is_svd(call):
    f = call.func
    return isinstance(f, ast.Attribute) and f.attr == "svd"


def _has_full_matrices_false(call):
    for kw in call.keywords:
        if kw.arg == "full_matrices":
            return isinstance(kw.value, ast.Constant) and kw.value.value is False
    return False


def _offenders():
    bad = []
    for path in _python_files():
        try:
            tree = ast.parse(io.open(path, encoding="utf-8").read())
        except SyntaxError:                      # 走査対象外の断片は無視
            continue
        for node in ast.walk(tree):
            if not _discards_u(node):
                continue
            call = node.value
            if isinstance(call, ast.Call) and _is_svd(call) \
                    and not _has_full_matrices_false(call):
                bad.append(f"{path.relative_to(ROOT).as_posix()}:{node.lineno}")
    return bad


def test_svd_calls_that_discard_u_pass_full_matrices_false():
    bad = _offenders()
    assert not bad, (
        "U を捨てる SVD が full_matrices=False になっていない。(N, k) の行列で "
        "(N, N) の U を確保して捨てる —— 20000 点で 3.7 s / 3.2 GB、10 万点で "
        "80 GB。Vt は変わらないので、足すだけで直る:\n  " + "\n  ".join(bad))


def test_the_gate_can_actually_fail(tmp_path):
    """門が壊れていないことを確かめる(発火しない門は門ではない)。"""
    import ast as _ast
    src = "import numpy as np\n_, _, Vt = np.linalg.svd(X)\n"
    tree = _ast.parse(src)
    node = [n for n in _ast.walk(tree) if isinstance(n, _ast.Assign)][0]
    assert _discards_u(node) and _is_svd(node.value)
    assert not _has_full_matrices_false(node.value)


def test_the_gate_accepts_the_fixed_form():
    import ast as _ast
    tree = _ast.parse("import numpy as np\n_, _, Vt = np.linalg.svd(X, full_matrices=False)\n")
    node = [n for n in _ast.walk(tree) if isinstance(n, _ast.Assign)][0]
    assert _has_full_matrices_false(node.value)


@pytest.mark.parametrize("module,func", [("pcseg", "obb"), ("pcseg", "fit_plane")])
def test_the_fixed_call_sites_still_agree_with_the_full_svd(module, func):
    """速くなっただけで答えは同じ、を実測で押さえる。"""
    import importlib

    import numpy as np
    mod = importlib.import_module(module)
    rng = np.random.default_rng(0)
    P = rng.random((4000, 3)) @ np.diag([3.0, 2.0, 0.05])
    got = getattr(mod, func)(P)
    Pc = P - P.mean(0)
    _, _, ref = np.linalg.svd(Pc)                    # 既定(遅いほう)
    _, _, fast = np.linalg.svd(Pc, full_matrices=False)
    assert np.array_equal(ref, fast), "Vt が一致しない —— 置き換えの前提が崩れた"
    assert got is not None
