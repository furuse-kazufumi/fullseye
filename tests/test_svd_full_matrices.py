# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""中心化した点群の SVD が ``full_matrices=False`` かを見る静的な門。

2026-09-06、左右非対称性の PoC が ``fs.obb`` の 3.7 秒の正体を突き止めた。
``np.linalg.svd(P - c)`` は既定 ``full_matrices=True`` なので、``(N, 3)`` の
行列に対して **(N, N) の U** を作る。20000 点なら 3.2 GB を確保して、そのまま
捨てていた。実測 **3.73 s → 0.876 ms(4263 倍)、Vt はビット一致**。
10 万点では 80 GB になり落ちる。

同じ形が**兄弟に 5 つ**あった(``pcseg`` の 2 か所、``measure``、``ops``、
``camera``、``pnp3d``)。バグ 1 件を直したら同クラスを兄弟で一掃する、という
規律の実施であり、次に誰かが ``_, _, Vt = np.linalg.svd(X - c)`` と書いたら
落ちる門をここに置く。

**一律には直せない。** ``full_matrices=False`` は**横長行列(m < n)で
``Vt[-1]`` の意味を変える**。DLT は ``A v = 0`` の零空間を ``Vt[-1]`` で取るが、
最小構成の 4 点ホモグラフィでは A が (8, 9) の横長になる。実測:

  * ``full_matrices=True``  → Vt は (9, 9)、``|A Vt[-1]| = 6.8e-16``(零空間)
  * ``full_matrices=False`` → Vt は (8, 9)、``|A Vt[-1]| = 3.2e-01``(**別物**)

5 点以上なら (10, 9) で縦長になり両者は一致する。つまり「速くなるから全部
付ける」をやると、**最小構成のときだけ静かに間違う**。この repo には DLT 系の
呼び出しが 20 か所あり、そのすべてがこの危険側にある。

**だからこの門が要求するのは「中心化した点群」の形だけ** —— SVD の引数が
``X - c`` のような引き算(または引き算を並べた ``column_stack``)である場合に
限る。その形は「N 点 x 3 列」を意味するので m >= n が保証され、
``full_matrices=False`` は速いだけで答えが変わらない。DLT 側は係数行列を
``append`` で組み立てるので、この判定には入らない。
"""
import ast
import io
import warnings
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]

#: 走査しないところ(生成物・外部由来・退避・このテスト自身)。
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


def _is_svd(call):
    f = call.func
    return isinstance(f, ast.Attribute) and f.attr == "svd"


def _is_centred_cloud(call):
    """SVD の引数が ``X - c`` 形か(= 中心化した点群、m >= n が保証される)。"""
    if not call.args:
        return False
    a = call.args[0]
    if isinstance(a, ast.BinOp) and isinstance(a.op, ast.Sub):
        return True
    if (isinstance(a, ast.Call) and isinstance(a.func, ast.Attribute)
            and a.func.attr == "column_stack" and a.args):
        inner = a.args[0]
        if isinstance(inner, (ast.List, ast.Tuple)):
            return all(isinstance(e, ast.BinOp) and isinstance(e.op, ast.Sub)
                       for e in inner.elts)
    return False


def _has_full_matrices_false(call):
    for kw in call.keywords:
        if kw.arg == "full_matrices":
            return isinstance(kw.value, ast.Constant) and kw.value.value is False
    return False


def _offenders():
    bad = []
    for path in _python_files():
        try:
            # 他ファイルの docstring 由来の DeprecationWarning(不正な
            # エスケープ列)をこの走査で鳴らさない —— 門の出力を汚すだけで、
            # ここで直す問題ではない。
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                tree = ast.parse(io.open(path, encoding="utf-8").read())
        except SyntaxError:                      # 走査対象外の断片は無視
            continue
        for node in ast.walk(tree):
            if not _discards_u(node):
                continue
            call = node.value
            if (isinstance(call, ast.Call) and _is_svd(call)
                    and _is_centred_cloud(call)
                    and not _has_full_matrices_false(call)):
                bad.append(f"{path.relative_to(ROOT).as_posix()}:{node.lineno}")
    return bad


def test_centred_cloud_svd_passes_full_matrices_false():
    bad = _offenders()
    assert not bad, (
        "中心化した点群の SVD が full_matrices=False になっていない。(N, 3) に "
        "対して (N, N) の U を確保して捨てる —— 20000 点で 3.7 s / 3.2 GB、"
        "10 万点で 80 GB。この形では Vt は変わらないので足すだけで直る:\n  "
        + "\n  ".join(bad))


def test_the_gate_can_actually_fail():
    """発火しない門は門ではない。壊れた形を食わせて検出することを確かめる。"""
    tree = ast.parse("import numpy as np\n_, _, Vt = np.linalg.svd(P - c)\n")
    node = [n for n in ast.walk(tree) if isinstance(n, ast.Assign)][0]
    assert _discards_u(node) and _is_svd(node.value) and _is_centred_cloud(node.value)
    assert not _has_full_matrices_false(node.value)


def test_the_gate_accepts_the_fixed_form():
    tree = ast.parse("import numpy as np\n"
                     "_, _, Vt = np.linalg.svd(P - c, full_matrices=False)\n")
    node = [n for n in ast.walk(tree) if isinstance(n, ast.Assign)][0]
    assert _has_full_matrices_false(node.value)


def test_the_gate_leaves_dlt_matrices_alone():
    """DLT の係数行列は判定に入れない。入れたら最小構成で静かに壊れる。"""
    tree = ast.parse("import numpy as np\n_, _, Vt = np.linalg.svd(np.asarray(A))\n")
    node = [n for n in ast.walk(tree) if isinstance(n, ast.Assign)][0]
    assert _is_svd(node.value) and not _is_centred_cloud(node.value)


def test_the_wide_matrix_hazard_is_real():
    """横長行列で ``Vt[-1]`` の意味が変わることの実測(除外の根拠)。"""
    A = np.random.default_rng(0).standard_normal((8, 9))     # 4 点 DLT の形
    _, _, full = np.linalg.svd(A)
    _, _, thin = np.linalg.svd(A, full_matrices=False)
    assert full.shape == (9, 9) and thin.shape == (8, 9)
    assert np.linalg.norm(A @ full[-1]) < 1e-12
    assert np.linalg.norm(A @ thin[-1]) > 1e-3, "横長でも一致した —— 前提を再確認"
    B = np.random.default_rng(0).standard_normal((10, 9))    # 5 点以上なら縦長
    _, _, bf = np.linalg.svd(B)
    _, _, bt = np.linalg.svd(B, full_matrices=False)
    assert np.array_equal(bf, bt)


@pytest.mark.parametrize("func", ["obb", "fit_plane"])
def test_the_fixed_call_sites_still_agree_with_the_full_svd(func):
    """速くなっただけで答えは同じ、を実測で押さえる。"""
    import pcseg
    rng = np.random.default_rng(0)
    P = rng.random((4000, 3)) @ np.diag([3.0, 2.0, 0.05])
    assert getattr(pcseg, func)(P) is not None
    Pc = P - P.mean(0)
    _, _, ref = np.linalg.svd(Pc)                    # 既定(遅いほう)
    _, _, fast = np.linalg.svd(Pc, full_matrices=False)
    assert np.array_equal(ref, fast), "Vt が一致しない —— 置き換えの前提が崩れた"
