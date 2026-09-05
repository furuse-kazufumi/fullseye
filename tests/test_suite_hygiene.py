# -*- coding: utf-8 -*-
"""テスト群そのものの衛生。**収集が中断する形**を静的に止める。

pytest は 1 つのテストモジュールが import に失敗すると
``Interrupted: N errors during collection`` で**残り全部を走らせずに終わる**。
つまりテスト 1 本の import ミスが、11,000 件の検査をまるごと消す。

2026-09-05 に**同じ日に 2 回**踏んだ:
  1. `tests/test_op_contract_property.py` が `hypothesis` を素で import し、
     CI の install 行に無かったため 0.1.8 の CI が 2 分で全滅した(テスト 0 件)。
  2. その修正の直後、`tests/test_no_local_paths_in_shipped_code.py` が
     `tomllib` を素で import し、**Python 3.10 に無い**ため py3.10 が全滅した。

どちらも「実行したら分かる」ものだが、手元に該当の版が無ければ実行できない。
だからここで**静的に**見る。判定は AST で、`try` の中や関数の中の import は対象外。
"""
from __future__ import annotations

import ast
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

#: 素の top-level import を禁じるモジュールと、その理由。
#:
#: * 標準ライブラリだが**古い Python に無い**もの
#: * CI の最小構成に**入っていない**第三者ライブラリ
#:
#: 使いたいときは ``pytest.importorskip`` か ``try/except ImportError`` で包む。
#: 直ったら**この台帳から消す**(両方向の規律)。
NEEDS_GUARD = {
    "tomllib": "Python 3.11 から。3.10 では ModuleNotFoundError で収集が止まる",
    "hypothesis": "dev extra。CI の test ジョブの install 行に入るまで素で import しない",
    "torch": "optional backend(gpu extra)。conftest の requires_backend を使う",
    "kornia": "optional backend(gpu extra)",
    "mahotas": "optional backend(extra extra)",
    "mitsuba": "optional backend(gi extra)",
    "SimpleITK": "optional backend(extra / volume extra)",
    "mediapipe": "optional backend(handpose extra)",
    "laspy": "optional backend(lidar extra)",
    "pypcd4": "optional backend(pcd extra)",
    "pygltflib": "optional backend(gltf extra)",
    "matplotlib": "polygon extra。CI は明示 install するが最小構成には無い",
    "imageio": "optional backend(video / raster extra)",
    "tifffile": "optional backend(volume / raster extra)",
    "sympy": "algo-difftest 用。CI は明示 install するが最小構成には無い",
}


def _toplevel_imports(tree):
    """モジュール直下(``try`` の中でも関数の中でもない)の import 名を返す。"""
    out = []
    for node in tree.body:                                   # body だけ = top-level
        if isinstance(node, ast.Import):
            out += [(a.name.split(".")[0], node.lineno) for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            out.append((node.module.split(".")[0], node.lineno))
    return out


def _guarded_before(tree):
    """``pytest.importorskip("X")`` が top-level に現れた行 -> {X: 行}。

    素の import でも、**それより前に** importorskip があれば安全
    (importorskip が Skipped を投げるので、後ろの import には到達しない)。
    この区別を入れないと、正しく書かれている側を誤検出する
    —— 実際、最初の版が `test_op_contract_property.py` を誤検出した。
    """
    seen = {}
    for node in tree.body:
        expr = node.value if isinstance(node, ast.Expr) else None
        if isinstance(node, ast.Assign):
            expr = node.value
        if not isinstance(expr, ast.Call):
            continue
        fn = expr.func
        nm = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
        if nm != "importorskip" or not expr.args:
            continue
        arg = expr.args[0]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            seen.setdefault(arg.value.split(".")[0], node.lineno)
    return seen


def test_no_test_module_imports_a_guarded_dependency_at_top_level():
    """収集を止めうる import が、素のまま書かれていないこと。"""
    offenders = []
    scanned = 0
    for name in sorted(os.listdir(HERE)):
        if not (name.startswith("test_") and name.endswith(".py")):
            continue
        path = os.path.join(HERE, name)
        with open(path, encoding="utf-8", errors="ignore") as f:
            try:
                tree = ast.parse(f.read(), filename=path)
            except SyntaxError as exc:                        # pragma: no cover
                offenders.append("%s: 構文エラー %s" % (name, exc))
                continue
        scanned += 1
        guarded = _guarded_before(tree)
        for mod, lineno in _toplevel_imports(tree):
            if mod not in NEEDS_GUARD:
                continue
            g = guarded.get(mod)
            if g is not None and g < lineno:
                continue                                      # 先に importorskip がある
            offenders.append("%s:%d  import %s  (%s)" % (name, lineno, mod,
                                                         NEEDS_GUARD[mod]))
    assert scanned > 50, "テストファイルの列挙に失敗している(母数 %d)" % scanned
    assert not offenders, (
        "収集を中断させうる top-level import がある(%d 件)。"
        "pytest.importorskip か try/except で包むこと:\n  " % len(offenders)
        + "\n  ".join(offenders))


def test_the_guard_ledger_only_names_things_that_are_actually_risky():
    """台帳の陳腐化。**標準ライブラリに昇格した**ものが残っていないか。

    `tomllib` は 3.11 から標準。プロジェクトが 3.11 を最小にしたら、
    この台帳から外して素の import に戻してよい —— そのとき気づけるように。
    """
    import importlib.util
    stale = []
    min_py = (3, 10)                                          # pyproject の requires-python
    if sys.version_info[:2] == min_py:
        for mod in ("tomllib",):
            if importlib.util.find_spec(mod) is not None:
                stale.append(mod)
    assert not stale, (
        "最小サポート版に標準で入るようになったので台帳から外せる: %s" % stale)
