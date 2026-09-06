# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""op に**たどり着けるか**の門。

2026-09-06 に PoC が出した穴が発端。fullseye には入口が 2 系統ある:

  * **台帳の op**  —— `fullseye.<名前>(...)` / `op_run` / `op_assist` / `op_find`。
  * **2-D レジストリの 882 op** —— `fullseye.apply(image, 名前)` だけ。

このとき実測で判ったこと: `dir(fullseye)` の 1092 名前と 882 op は **3 つしか
重ならず**、しかもその 3 つは別物だった。つまり補完でも `op_find` でも
「erosion」に一件も当たらず、**動くのに一生見つからない op** が 882 個あった。
「発見ゼロ」が頑健さではなく未実行だった 2026-09-02 の件と同じ形である。

ここで守るのは 3 つ:

1. 新しい族を足したら **opassist の台帳表にも載る**(登録面がまた 1 つ増えた
   ことを門で固定する。載せ忘れると `op_run` からだけ消える)。
2. `fullseye.op.<名前>` で 882 op すべてに届き、`apply` と**同じ値**を返す。
3. `op_find` は台帳と 2-D レジストリの**両方**を返し、呼び方の違いを `call` で
   明かす(検索に出るのに `run` で動かない、を隠さない)。
"""
import importlib
import sys
from pathlib import Path

import numpy as np
import pytest

import fullseye as fs
import opassist as A
import ops

_TOOLS = str(Path(__file__).resolve().parents[1] / "tools")


def _ledger_dims():
    if _TOOLS not in sys.path:
        sys.path.insert(0, _TOOLS)
    return importlib.import_module("opdocs").LEDGER_DIMS


# --------------------------------------------------------------------------- #
# 1. 登録面: 台帳を足したら opassist にも載っているか
# --------------------------------------------------------------------------- #
def test_every_documented_ledger_is_reachable_from_opassist():
    """docs を出す台帳は、入力補助(op_run/op_assist)からも引けなければならない。

    2026-09-06 の実測: dem / piv / profile の 3 族 54 op が opassist にだけ
    無く、`op_run("dem_slope", ...)` が "not in any ledger" で落ちていた。
    登録面は 台帳 / opdocs / typed_catalog / PARAM_HINTS / TYPE_CHECKS に
    加えて **opassist._LEDGERS** の 6 つある。
    """
    declared = {m for m, _ in A._LEDGERS}
    for key, info in _ledger_dims().items():
        assert info["registry"] in declared, (
            "台帳 %r (%s) が opassist._LEDGERS に無い —— docs には出るが "
            "op_run / op_assist / op_find から引けない" % (key, info["registry"]))


def test_new_families_are_actually_answerable_by_the_assist_layer():
    for name in ("dem_slope", "piv_cross_correlate", "profile_thickness"):
        assert A._ledger_entry(name)[0] is not None, name
        spec = A.assist(name, measure=False)
        assert spec["op"] == name and spec["ledger"]


# --------------------------------------------------------------------------- #
# 2. fullseye.op —— 882 op への属性アクセス
# --------------------------------------------------------------------------- #
def test_op_namespace_covers_the_whole_registry():
    names = dir(fs.op)
    assert len(names) == len(ops.REGISTRY) == len(fs.op)
    assert names == sorted(names)
    assert "gray_erosion" in fs.op and "no_such_op_xyz" not in fs.op


def test_op_namespace_matches_apply_exactly():
    img = np.zeros((16, 16))
    img[5:11, 5:11] = 1.0
    for name in ("gray_erosion", "gray_dilation", "sobel_amp", "gauss_filter"):
        for a in (0.0, 0.3, 0.9):
            got = fs.op[name](img, a=a)
            want = fs.apply(img, name, a=a)
            assert np.array_equal(got, want), (name, a)


def test_op_namespace_carries_the_ops_own_doc():
    doc = fs.op.gray_erosion.__doc__
    assert "収縮" in doc and "morphology" in doc and "gray_erosion" in doc
    assert fs.op.gray_erosion.__name__ == "gray_erosion"


def test_op_namespace_is_fail_closed_on_unknown_names():
    with pytest.raises(AttributeError, match="op_find"):
        _ = fs.op.definitely_not_an_op


def test_the_three_colliding_names_are_different_things():
    """``lowpass`` / ``highpass`` / ``fill_holes`` は両側にあるが**別物**。

    882 名前を 1092 名前へ混ぜなかった理由そのもの。混ぜていれば、どちらかが
    もう一方を静かに上書きし、例外ではなく違う答えが返っていた。
    """
    both = [o.name for o in ops.REGISTRY if hasattr(fs, o.name)]
    assert sorted(both) == ["fill_holes", "highpass", "lowpass"]
    for name in both:
        assert fs.op[name] is not getattr(fs, name)
    # fs.fill_holes は網(mesh)の穴埋め、fs.op.fill_holes は 2-D 領域の穴埋め。
    mask = np.zeros((32, 32))
    mask[8:24, 8:24] = 1.0
    mask[14:18, 14:18] = 0.0
    filled = fs.op.fill_holes(mask)
    assert filled.sum() > mask.sum(), "2-D 側の fill_holes が穴を埋めていない"
    mesh_doc = (fs.fill_holes.__doc__ or "").lower()
    assert "boundary loop" in mesh_doc and "(v, f)" in mesh_doc, \
        "fs.fill_holes は網の境界ループを閉じる op のはず(2-D の穴埋めではない)"


# --------------------------------------------------------------------------- #
# 3. op_find —— 両方の系統が出て、呼び方が判る
# --------------------------------------------------------------------------- #
def test_find_reaches_the_2d_registry():
    hits = fs.op_find("erosion", limit=10)
    assert hits, "erosion で 1 件も出ない(882 op が検索から消えている)"
    assert any(h["op"] == "gray_erosion" for h in hits)
    assert all(h["call"] in ("run", "apply") for h in hits)


def test_find_still_reaches_the_ledgers_and_marks_the_call_style():
    hits = fs.op_find("dem_slope", limit=5)
    top = hits[0]
    assert top["op"] == "dem_slope" and top["call"] == "run"
    reg = [h for h in fs.op_find("gray_erosion", limit=5) if h["op"] == "gray_erosion"]
    assert reg and reg[0]["call"] == "apply" and reg[0]["ledger"] == "ops"


def test_find_prefers_the_ledger_when_a_name_exists_on_both_sides():
    hits = fs.op_find("fill_holes", limit=10)
    names = [h["op"] for h in hits]
    assert names[0] == "fill_holes"
    # 同名は 1 件だけ(台帳側)。二重に出すと利用者はどちらを呼ぶか決められない。
    assert names.count("fill_holes") == 1


# --------------------------------------------------------------------------- #
# 4. fullseye.ledger —— 型つき台帳 894 op への属性アクセス
# --------------------------------------------------------------------------- #
def _ledger_names():
    names = set()
    for mod_name, table in A._LEDGERS:
        mod = importlib.import_module(mod_name)
        names.update(getattr(mod, table, {}))
    return names


def test_ledger_namespace_covers_every_ledger_op():
    """台帳に載っている op は 1 つ残らず ``fs.ledger`` から呼べること。

    2026-09-06 実測: 894 op のうち ``fullseye`` 直下に名前が出ているのは
    **499 個だけ**で、残り 395 個は ``op_run`` からしか届かなかった。左右
    非対称性の PoC が ``fs.reflect_points`` で AttributeError を踏んで露見。
    """
    names = _ledger_names()
    assert len(names) > 800, len(names)
    assert set(dir(fs.ledger)) == names
    for probe in ("reflect_points", "reflection_symmetry_score", "chamfer_distance",
                  "hausdorff_distance", "dem_slope", "piv_cross_correlate"):
        assert probe in fs.ledger, probe


def test_ledger_namespace_applies_the_result_adapters():
    """宣言 out 型どおりの値が返ること(素の返りではなく ``call`` を通す)。"""
    import numpy as np
    import opspiv
    adapted = [n for n in opspiv.RESULT_ADAPTERS if n in fs.ledger]
    assert adapted, "adapter つきの op が無い —— 前提が変わった"
    a = np.zeros((64, 64))
    a[24:40, 24:40] = 1.0
    b = np.roll(a, 2, axis=1)
    got = fs.ledger.piv_cross_correlate(a, b, window=16)
    raw = opspiv.get("piv_cross_correlate")(a, b, window=16)
    assert isinstance(raw, tuple) and len(raw) == 2, type(raw)
    assert isinstance(got, np.ndarray) and got.shape[0] == 2, (type(got), got.shape)


def test_ledger_namespace_is_fail_closed_and_points_at_the_other_tier():
    with pytest.raises(AttributeError, match="fullseye.op"):
        _ = fs.ledger.definitely_not_a_ledger_op


def test_the_two_namespaces_overlap_in_exactly_one_name():
    """台帳 894 と 2-D レジストリ 882 で同名は ``fill_holes`` の **1 つだけ**。

    そしてそれは別物である(``fs.ledger.fill_holes`` は網の境界ループを閉じ、
    ``fs.op.fill_holes`` は 2-D 領域の穴を埋める)。1 つに増減したら、名前空間を
    分けている前提が変わったということなので、ここで気づく。
    """
    both = _ledger_names() & {o.name for o in ops.REGISTRY}
    assert both == {"fill_holes"}, sorted(both)
    assert fs.ledger.fill_holes is not fs.op.fill_holes
