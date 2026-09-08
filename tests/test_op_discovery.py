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


def test_the_two_namespaces_overlap_in_exactly_three_names():
    """台帳と 2-D レジストリで同名なのは ``fill_holes`` / ``lowpass`` / ``highpass``。

    ★2026-09-08 に 1 -> 3 へ増えた。``ops1d``(dsp 16 + funct1d 23)を台帳へ
    繋いだためで、**衝突そのものは前からあった** —— `fs.lowpass` は以前から
    dsp の 1-D バターワースで、`fs.op.lowpass` は 2-D 画像の周波数フィルタ。
    台帳に出したことで、この門が初めてそれを見えるようにした。

    ★★重要なのは名前の数ではなく**取り違えたときの挙動**なので、そちらを固定する:

    * `fs.ledger.lowpass`(1-D)に 2-D 画像を渡す → **ValueError**(正しく鳴る)。
    * `fs.op.lowpass`(2-D)に 1-D 信号を渡す → **鳴らない**。警告 1 本を出して
      **入力をそのまま返す**(fail-soft の恒等)。フィルタしていない信号は
      フィルタした信号に見えるので、これは黙って嘘をつく方向。
      ファサードの既定方針(`on_error`)がそうなっているためで、
      `on_error="raise"` を渡せば鳴る。ここではその**非対称**を固定して、
      方針が変わったら気づけるようにする。
    """
    both = _ledger_names() & {o.name for o in ops.REGISTRY}
    assert both == {"fill_holes", "lowpass", "highpass"}, sorted(both)
    assert fs.ledger.fill_holes is not fs.op.fill_holes
    assert fs.ledger.lowpass is not fs.op.lowpass

    img = np.zeros((32, 32))
    sig = np.sin(np.linspace(0.0, 20.0, 256))

    # 1-D の op に 2-D を渡すと鳴る
    for name in ("lowpass", "highpass"):
        with pytest.raises(ValueError):
            getattr(fs.ledger, name)(img, rate=100.0, cutoff=10.0)

    # 2-D の op に 1-D を渡しても鳴らない —— 素通しで返る(この非対称が本体)
    import warnings
    for name in ("lowpass", "highpass"):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            out = getattr(fs.op, name)(sig)
        assert np.shape(out) == sig.shape
        # ★素通しですらない: フォールバックは画像の契約 [0,1] へ**切り詰めて**返す。
        #   負の半分が 0 になった信号は「フィルタした信号」に見えるので、
        #   これは黙って嘘をつく。max|差| = 1.0、最小値 -1.0 -> 0.0。
        assert out.min() == 0.0 and sig.min() < -0.9
        assert np.max(np.abs(out - sig)) > 0.9
        assert np.allclose(out[sig > 0.0], sig[sig > 0.0])   # 正の側は素通し
        assert any("degraded to a fallback" in str(x.message) for x in w)


def test_ledger_namespace_exposes_the_raw_return_through_dot_raw():
    """adapter が捨てる 2 番目以降に ``.raw`` で届くこと(2026-09-06)。

    ``flow, info = fs.ledger.piv_cross_correlate(a, b)`` は例外を出さずに
    (2, R, C) を第 1 軸で開き、``flow`` が dy 成分だけになる。実際に PoC が
    それで踏んで、ずれ推定を 0.12 → 0.74 画素にした。
    """
    import numpy as np
    rng = np.random.default_rng(0)
    a = rng.random((96, 96))
    b = np.roll(a, 2, axis=1)
    adapted = fs.ledger.piv_cross_correlate(a, b, window=16)
    raw = fs.ledger.piv_cross_correlate.raw(a, b, window=16)
    assert isinstance(adapted, np.ndarray) and adapted.shape[0] == 2
    assert isinstance(raw, tuple) and len(raw) == 2
    assert np.array_equal(raw[0], adapted, equal_nan=True)
    assert isinstance(raw[1], dict)
    assert np.isfinite(adapted).any(), "全部 nan —— 窓か入力の選び方を見直すこと"
    # adapter が無い op でも .raw は同じものを返す(呼び分けを覚えなくてよい)
    plain = fs.ledger.dem_slope(np.zeros((8, 8)), 5.0)
    assert np.array_equal(fs.ledger.dem_slope.raw(np.zeros((8, 8)), 5.0), plain)
