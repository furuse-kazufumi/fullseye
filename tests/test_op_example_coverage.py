# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Every operator must have a worked example — and the coverage galleries must run.

This is the invariant that keeps op coverage at 100% as the library grows: the moment
a new op is added to ``ops.REGISTRY`` or ``ops3d`` without any example calling it, this
test fails, so op help / OP_CATALOG never advertises "· 例: なし". The 2-D category
gallery examples (``examples/gallery2d_*.py``) are also executed end-to-end so their
per-op behavior checks stay honest.
"""
import glob
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import op_example_index as OEI  # noqa: E402

from conftest import requires_full_registry


def test_no_3d_op_lacks_an_example():
    idx3d, _ = OEI.build_index(split=True)
    uncovered = sorted(n for n, ex in idx3d.items() if not ex)
    assert not uncovered, f"{len(uncovered)} ops3d op(s) have no worked example: {uncovered}"


def test_no_2d_op_lacks_an_example():
    _, idx2d = OEI.build_index(split=True)
    uncovered = sorted(n for n, ex in idx2d.items() if not ex)
    assert not uncovered, f"{len(uncovered)} 2-D registry op(s) have no worked example: {uncovered}"


_GALLERIES = sorted(
    os.path.basename(p)[:-3]
    for p in glob.glob(os.path.join(ROOT, "examples", "gallery2d_*.py"))
)


@pytest.mark.parametrize("gallery", _GALLERIES)
def test_coverage_gallery_runs(gallery):
    """Each 2-D category gallery runs to a passing self-check (exit 0, PASS line)."""
    # ギャラリーは op 名を文字列で直書きするので、optional backend が欠けると
    # 「OPS に余分」で落ちる。op 集合が環境で変わる以上、満杯でないと意味が無い。
    requires_full_registry()
    env = dict(os.environ, PYTHONPATH=ROOT, PYTHONUTF8="1")
    r = subprocess.run(
        [sys.executable, os.path.join(ROOT, "examples", f"{gallery}.py")],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=300,
    )
    assert r.returncode == 0, f"{gallery} exited {r.returncode}\nstderr tail:\n{r.stderr[-1500:]}"
    assert "PASS" in r.stdout, f"{gallery} produced no PASS line\nstdout tail:\n{r.stdout[-800:]}"


# --------------------------------------------------------------------------- #
# ★母集団を「配布物の側」から数える ratchet(2026-09-06)                        #
# --------------------------------------------------------------------------- #
#: 2026-09-06 の実測。**この数より悪くしない**ための歯止めで、目標値ではない。
#: 台帳 op 1,002 本のうち例索引に入っているのは 349 本しかなく、上の 2 本の
#: 「100 %」は母集団が 3 層のうち 2 層しか無いために成り立っていた。
#: 経緯と族別の内訳 = docs/KNOWN_ISSUES.md §38。
_LEDGER_COVERED_FLOOR = 349
_REGISTRY_COVERED_FLOOR = 749


def _covered_names():
    idx3d, idx2d = OEI.build_index(split=True)
    return {n for n, ex in idx3d.items() if ex} | {n for n, ex in idx2d.items() if ex}


def test_ledger_example_coverage_does_not_regress():
    """台帳 op のうち例を持つ本数が、記録した床を下回らないこと。

    **緑でも「足りている」意味ではない** —— いま 349/1002。族を足したときに
    ここが下がらない(= 新しい族が例ゼロのまま増え続けない)ことだけを守る。
    増えたら床を上げること。
    """
    import typed_catalog as tc

    led = {r[0] for r in tc.catalog()}
    got = len(led & _covered_names())
    assert got >= _LEDGER_COVERED_FLOOR, (
        "台帳 op の例が %d → %d に減った。床を下げて通すのではなく、"
        "例を足すか、なぜ減ったかを docs/KNOWN_ISSUES.md §38 に書くこと。"
        % (_LEDGER_COVERED_FLOOR, got))


def test_the_two_dimensional_gate_knows_how_much_it_is_not_counting():
    """★「100 %」の分母が `ops.REGISTRY` より小さいことを**明示的に**固定する。

    黙って分母が縮むと「100 %」だけが生き残る。ここが落ちたら、
    増えたのか減ったのかを数字で見てから判断する。
    """
    import ops

    _, idx2d = OEI.build_index(split=True)
    outside = len(ops.REGISTRY) - len(idx2d)
    assert outside >= 0
    assert outside <= 148 + 20, (
        "例索引の母集団に入らない 2-D op が %d 本に増えた(2026-09-06 は 148 本)。"
        "新しい op を索引に載せるか、載せない理由を残すこと。" % outside)
