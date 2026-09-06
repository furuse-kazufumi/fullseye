# -*- coding: utf-8 -*-
"""blob2d(2-D の連結成分解析)の門。

真値が閉形式で書ける図形だけで測る —— 円板の面積と周長、楕円の慣性主軸、
凸な図形の充填率、穴の数。**推定器の偏りは隠さずここに数値で固定する**
(周長の Crofton は円板で +0.6 %、軸に平行な正方形で -6.6 %)。値が動いたら
それは実装が変わった合図で、テストの側を緩めて通すものではない。
"""
from __future__ import annotations

import io
import math
import re
from pathlib import Path

import numpy as np
import pytest

import blob2d as B

ROOT = Path(__file__).resolve().parents[1]


def _disc(radius: int, half: int = 60) -> np.ndarray:
    yy, xx = np.mgrid[-half:half + 1, -half:half + 1]
    return (yy * yy + xx * xx) <= radius * radius


def _square(side: int = 20, pad: int = 10) -> np.ndarray:
    m = np.zeros((side + 2 * pad, side + 2 * pad), bool)
    m[pad:pad + side, pad:pad + side] = True
    return m


# --------------------------------------------------------------------------- #
# 1. 切る —— 連結の定義                                                        #
# --------------------------------------------------------------------------- #
def test_four_and_eight_connectivity_split_on_a_diagonal_touch():
    """斜めに触れる 2 個は 8 連結で 1 個、4 連結で 2 個。"""
    m = np.zeros((10, 10), bool)
    m[3:5, 3:5] = True
    m[5:7, 5:7] = True
    assert int(B.blob_label(m, 8).max()) == 1
    assert int(B.blob_label(m, 4).max()) == 2


def test_labels_are_contiguous_and_background_is_zero():
    m = np.zeros((20, 40), bool)
    m[2:8, 2:8] = True
    m[2:8, 12:18] = True
    m[12:18, 22:38] = True
    lab = B.blob_label(m)
    assert lab.dtype == np.int32
    assert sorted(np.unique(lab).tolist()) == [0, 1, 2, 3]
    assert not lab[~m].any(), "背景に番号が付いた"


def test_a_bad_connectivity_is_refused():
    with pytest.raises(ValueError, match="connectivity must be 4 or 8"):
        B.blob_label(np.zeros((4, 4), bool), 6)


# --------------------------------------------------------------------------- #
# 2. 測る —— 真値が閉形式で書ける図形                                          #
# --------------------------------------------------------------------------- #
def test_rectangle_area_bbox_and_extent_are_exact():
    m = np.zeros((30, 30), bool)
    m[5:25, 8:16] = True                       # 20 x 8
    f = B.blob_features(B.blob_label(m))
    assert f["n"] == 1
    assert float(f["area"][0]) == 160.0
    assert [int(f[k][0]) for k in ("bbox_r0", "bbox_c0", "bbox_r1", "bbox_c1")] \
        == [5, 8, 25, 16]
    assert float(f["extent"][0]) == 1.0        # 外接箱ぴったり
    assert float(f["row"][0]) == pytest.approx(14.5)
    assert float(f["col"][0]) == pytest.approx(11.5)


@pytest.mark.parametrize("r", [10, 20, 40])
def test_the_disc_perimeter_estimator_stays_within_four_percent(r):
    """★推定器の偏りを数字で固定する。

    素朴に境界画素を数えると +21〜26 %、Serra の重みは大きさによらず
    +4.95 %、Crofton の 4 方向は大きさとともに真値へ寄る(実測
    +3.77 / +1.63 / +0.56 %)。ここが緩むと円形度が意味を失う。
    """
    d = _disc(r)
    est = B._perimeter(d)
    true = 2.0 * math.pi * r
    rel = (est - true) / true
    assert 0.0 < rel < 0.04, "r=%d: %.2f vs %.2f (%+.2f %%)" % (r, est, true, 100 * rel)


def test_the_disc_is_round_and_convex():
    f = B.blob_features(B.blob_label(_disc(40)))
    assert float(f["circularity"][0]) > 0.98
    assert float(f["eccentricity"][0]) < 0.01
    assert float(f["solidity"][0]) == 1.0
    assert int(f["holes"][0]) == 0
    # 等価直径は面積から出るので、真の直径 80 に 1 % 以内で一致する
    assert float(f["equiv_diameter"][0]) == pytest.approx(80.0, rel=0.01)


def test_the_axis_aligned_square_is_the_documented_weak_case():
    """★Crofton は軸に平行な多角形を**小さく**見る。隠さず固定する。

    真値 80 に対して 74.7(-6.6 %)、円形度は pi/4 = 0.785 のところ 0.90。
    「角ばった物体の円形度を絶対値で語らない」という注意書きの根拠。
    """
    f = B.blob_features(B.blob_label(_square()))
    assert float(f["perimeter"][0]) == pytest.approx(74.73, abs=0.05)
    assert float(f["circularity"][0]) == pytest.approx(0.900, abs=0.005)
    assert float(f["circularity"][0]) > math.pi / 4, "偏りの向きが変わった"


def test_the_ellipse_axes_and_angle_match_the_analytic_values():
    """長半径 40・短半径 15 の楕円を 30 度に置く。4 つとも真値と突き合わせる。"""
    yy, xx = np.mgrid[-60:61, -60:61]
    th = math.radians(30.0)
    u = xx * math.cos(th) + yy * math.sin(th)      # 長軸方向
    v = -xx * math.sin(th) + yy * math.cos(th)
    ell = (u / 40.0) ** 2 + (v / 15.0) ** 2 <= 1.0
    f = B.blob_features(B.blob_label(ell))
    assert float(f["area"][0]) == pytest.approx(math.pi * 40 * 15, rel=0.01)
    assert float(f["major"][0]) == pytest.approx(80.0, rel=0.01)
    assert float(f["minor"][0]) == pytest.approx(30.0, rel=0.01)
    assert math.degrees(float(f["angle"][0])) == pytest.approx(30.0, abs=0.5)
    assert float(f["eccentricity"][0]) == pytest.approx(
        math.sqrt(1 - (15 / 40) ** 2), abs=0.005)


def test_the_angle_sign_is_plus_col_towards_plus_row():
    """★向きの規約。**画面では時計回りが正**(数学の慣習と逆)。

    行が増える向き(下)へ傾いた棒は正の角、上へ傾いた棒は負の角。
    ここが逆になると、図に重ねた軸だけが鏡像になって静かに間違う。
    """
    n = 61
    rr, cc = np.mgrid[0:n, 0:n]
    down = np.abs((rr - 30) - 0.5 * (cc - 30)) <= 1.5      # 右へ行くほど下がる
    up = np.abs((rr - 30) + 0.5 * (cc - 30)) <= 1.5        # 右へ行くほど上がる
    a_down = float(B.blob_features(B.blob_label(down))["angle"][0])
    a_up = float(B.blob_features(B.blob_label(up))["angle"][0])
    assert a_down > 0.2, a_down
    assert a_up < -0.2, a_up
    assert a_down == pytest.approx(-a_up, abs=1e-9)


def test_a_one_pixel_wide_line_does_not_collapse_to_eccentricity_one():
    """2 次モーメントの 1/12 補正が入っていること。

    補正が無いと ``minor`` が厳密に 0 になり、``eccentricity`` が 1 に
    張り付いて「細長さ」の指標として使えなくなる。
    """
    m = np.zeros((10, 10), bool)
    m[3, 2:8] = True
    f = B.blob_features(B.blob_label(m))
    assert float(f["minor"][0]) == pytest.approx(4.0 / math.sqrt(12.0), rel=0.01)
    assert 0.9 < float(f["eccentricity"][0]) < 1.0
    assert float(f["solidity"][0]) == 1.0      # 線分は凸


@pytest.mark.parametrize("name", ["disc", "square", "triangle", "pixel", "line"])
def test_every_convex_shape_has_solidity_exactly_one(name):
    """★凸な物体の充填率は 1.0 ちょうど。

    凸包を多角形の面積として出すと、画素を点と見るか正方形と見るかで
    0.977 か 1.025 にずれる。塗り直して数えるのはこれを 1.0 にするため。
    """
    if name == "disc":
        m = _disc(40)
    elif name == "square":
        m = _square()
    elif name == "triangle":
        m = np.zeros((30, 30), bool)
        for r in range(20):
            m[5 + r, 5:6 + r] = True
    elif name == "pixel":
        m = np.zeros((5, 5), bool)
        m[2, 2] = True
    else:
        m = np.zeros((10, 10), bool)
        m[2:8, 3] = True
    assert float(B.blob_features(B.blob_label(m))["solidity"][0]) == 1.0


def test_a_crescent_is_not_solid():
    yy, xx = np.mgrid[-60:61, -60:61]
    cres = _disc(40) & ~(((yy + 20) ** 2 + xx ** 2) <= 35 * 35)
    f = B.blob_features(B.blob_label(cres))
    assert 0.4 < float(f["solidity"][0]) < 0.7


def test_holes_are_counted():
    yy, xx = np.mgrid[-60:61, -60:61]
    donut = _disc(40) & ~(yy * yy + xx * xx <= 15 * 15)
    two = _disc(40).copy()
    two[-10:10, -25:-15] = False              # 何も抜けない添字(下で明示的に開ける)
    two = _disc(40).copy()
    two[50:56, 45:51] = False
    two[70:76, 68:74] = False
    assert int(B.blob_features(B.blob_label(donut))["holes"][0]) == 1
    assert int(B.blob_features(B.blob_label(two))["holes"][0]) == 2
    assert int(B.blob_features(B.blob_label(_disc(40)))["holes"][0]) == 0


def test_touches_border_is_flagged():
    m = np.zeros((20, 20), bool)
    m[0:5, 0:5] = True                        # 左上の角に接する
    m[10:15, 10:15] = True                    # 内側
    f = B.blob_features(B.blob_label(m))
    assert f["touches_border"].tolist() == [True, False]


def test_spacing_scales_lengths_once_and_areas_twice_but_not_indices():
    m = np.zeros((30, 30), bool)
    m[5:25, 8:16] = True
    a = B.blob_features(B.blob_label(m), spacing=1.0)
    b = B.blob_features(B.blob_label(m), spacing=0.05)
    assert float(b["area"][0]) == pytest.approx(float(a["area"][0]) * 0.05 ** 2)
    assert float(b["perimeter"][0]) == pytest.approx(float(a["perimeter"][0]) * 0.05)
    assert float(b["major"][0]) == pytest.approx(float(a["major"][0]) * 0.05)
    # 添字と無次元量は動かない
    assert int(b["bbox_r0"][0]) == int(a["bbox_r0"][0])
    assert float(b["row"][0]) == float(a["row"][0])
    assert float(b["circularity"][0]) == pytest.approx(float(a["circularity"][0]))
    assert float(b["solidity"][0]) == float(a["solidity"][0])


def test_units_names_every_feature():
    """``units`` に載っていない項目があると、表を読む側が単位を推測してしまう。"""
    f = B.blob_features(B.blob_label(_square()))
    assert set(f["units"]) == set(B.FEATURE_KEYS)


def test_an_empty_image_still_returns_every_key():
    f = B.blob_features(np.zeros((8, 8), np.int32))
    assert f["n"] == 0
    for k in B.FEATURE_KEYS:
        assert k in f and len(f[k]) == 0, k


# --------------------------------------------------------------------------- #
# 3. 選ぶ                                                                      #
# --------------------------------------------------------------------------- #
def _three_sizes():
    m = np.zeros((40, 60), bool)
    m[2:6, 2:6] = True                        # 16 px
    m[10:20, 10:20] = True                    # 100 px
    m[24:38, 30:56] = True                    # 364 px
    return B.blob_label(m)


def test_select_keeps_the_range_and_renumbers_from_one():
    lab = _three_sizes()
    sel = B.blob_select(lab, "area", vmin=50, vmax=200)
    assert sorted(np.unique(sel).tolist()) == [0, 1]
    assert float(B.blob_features(sel)["area"][0]) == 100.0


def test_select_uses_spacing_for_physical_thresholds():
    lab = _three_sizes()
    # 100 px は 0.1 単位/px なら 1.0 unit^2。1.5 で切れば落ちる。
    assert int(B.blob_select(lab, "area", vmin=0.9, spacing=0.1).max()) == 2
    assert int(B.blob_select(lab, "area", vmin=1.5, spacing=0.1).max()) == 1


def test_select_refuses_an_unknown_feature_and_names_the_alternatives():
    with pytest.raises(ValueError, match="unknown feature"):
        B.blob_select(_three_sizes(), "roundness", vmin=0.0)


def test_select_refuses_to_be_a_no_op():
    """両端とも None は「選んでいない」—— 黙って素通しさせない。"""
    with pytest.raises(ValueError, match="at least one of vmin"):
        B.blob_select(_three_sizes(), "area")


def test_select_largest_orders_by_area_and_tolerates_asking_for_too_many():
    lab = _three_sizes()
    top = B.blob_select_largest(lab, 2)
    f = B.blob_features(top)
    assert f["n"] == 2
    assert f["area"].tolist() == [364.0, 100.0]      # 番号 1 が最大
    assert B.blob_features(B.blob_select_largest(lab, 99))["n"] == 3


def test_select_largest_breaks_ties_by_the_original_number():
    m = np.zeros((20, 40), bool)
    m[2:6, 2:6] = True
    m[2:6, 12:16] = True
    m[2:6, 22:26] = True                       # 3 個とも同じ面積
    lab = B.blob_label(m)
    keep = B.blob_select_largest(lab, 2)
    # 元の 1 番と 2 番が残る(3 番の場所は消える)
    assert not keep[2:6, 22:26].any()
    assert keep[2:6, 2:6].any() and keep[2:6, 12:16].any()


def test_selecting_from_an_empty_label_image_is_empty_not_an_error():
    empty = np.zeros((8, 8), np.int32)
    assert not B.blob_select(empty, "area", vmin=1).any()
    assert not B.blob_select_largest(empty, 3).any()


# --------------------------------------------------------------------------- #
# 4. 取り出す・見る                                                            #
# --------------------------------------------------------------------------- #
def test_region_extracts_one_object_with_a_one_origin_index():
    lab = _three_sizes()
    assert int(B.blob_region(lab, 2).sum()) == 100
    with pytest.raises(ValueError, match="1-origin"):
        B.blob_region(lab, 0)
    with pytest.raises(ValueError, match="1-origin"):
        B.blob_region(lab, 4)


def test_boundaries_lie_inside_the_objects_and_separate_neighbours():
    """接している 2 物体でも、輪郭は自分の内側に出る。"""
    m = np.zeros((20, 20), bool)
    m[5:15, 4:10] = True
    lab = B.blob_label(m)
    lab[5:15, 10:16] = 2                       # 1 と 2 が列 9/10 で接する
    bnd = B.blob_boundaries(lab)
    assert bnd[lab == 0].sum() == 0, "背景に輪郭が出た"
    assert bnd[5:15, 9].all() and bnd[5:15, 10].all(), "接する境目が消えた"
    assert not bnd[9, 6], "内部まで輪郭になっている"


def test_overlay_keeps_the_background_and_colours_the_objects():
    lab = _three_sizes()
    img = np.linspace(0.0, 1.0, lab.size).reshape(lab.shape)
    out = B.blob_overlay(img, lab, alpha=1.0)
    assert out.shape == lab.shape + (3,)
    bg = lab == 0
    grey = np.repeat(img[:, :, None], 3, axis=2)
    assert np.allclose(out[bg], grey[bg]), "背景が塗り替えられた"
    assert not np.allclose(out[lab == 1], grey[lab == 1]), "物体が塗られていない"


def test_overlay_refuses_a_mismatched_image():
    with pytest.raises(ValueError, match="differ"):
        B.blob_overlay(np.zeros((10, 10)), _three_sizes())


def test_overlay_takes_colour_images_too():
    lab = _three_sizes()
    rgb = np.zeros(lab.shape + (3,))
    out = B.blob_overlay(rgb, lab, alpha=0.5)
    assert out.shape == lab.shape + (3,)


# --------------------------------------------------------------------------- #
# 5. fail closed —— 混ぜたら静かに嘘をつく入口を塞ぐ                            #
# --------------------------------------------------------------------------- #
def test_a_boolean_mask_is_refused_with_the_fix_in_the_message():
    """★これがこの族で型を分けた理由そのもの。

    マスクをそのまま測ると、離れた 2 個の物体が 1 個として測られ
    **2 つの中心のあいだに重心が出る**。例外にならない = 静かに嘘をつく。
    """
    m = np.zeros((40, 40), bool)
    m[5:15, 5:15] = True
    m[25:35, 25:35] = True
    with pytest.raises(ValueError) as exc:
        B.blob_features(m)
    assert "blob_label" in str(exc.value), "直し方が書かれていない"
    # 嘘の中身も押さえておく: マスクを 1 物体として測ると重心は真ん中に来る
    f = B.blob_features(B.blob_label(m).clip(0, 1).astype(np.int32))
    assert float(f["row"][0]) == pytest.approx(19.5, abs=0.6)


def test_a_float_label_image_is_refused():
    with pytest.raises(ValueError, match="integer dtype"):
        B.blob_features(np.zeros((8, 8), np.float64))


def test_a_three_dimensional_input_is_refused_by_both_entry_points():
    with pytest.raises(ValueError, match="2-D"):
        B.blob_label(np.zeros((4, 4, 4), bool))
    with pytest.raises(ValueError, match="2-D"):
        B.blob_features(np.zeros((4, 4, 4), np.int32))


def test_negative_labels_are_refused():
    lab = np.zeros((8, 8), np.int32)
    lab[2, 2] = -1
    with pytest.raises(ValueError, match="negative labels"):
        B.blob_features(lab)


def test_a_non_positive_spacing_is_refused():
    with pytest.raises(ValueError, match="spacing"):
        B.blob_features(np.zeros((8, 8), np.int32), spacing=0.0)


def test_nan_pixels_are_background_not_foreground():
    x = np.zeros((10, 10), np.float64)
    x[2:5, 2:5] = np.nan
    x[6:9, 6:9] = 1.0
    assert int(B.blob_label(x).max()) == 1


# --------------------------------------------------------------------------- #
# 6. 台帳と公開経路                                                            #
# --------------------------------------------------------------------------- #
def test_the_ledger_lists_every_op_and_nothing_is_missing():
    import opsblob

    assert opsblob.missing() == []
    assert set(opsblob.OPSBLOB) == set(B.__all__) - {"FEATURE_KEYS", "CONNECTIVITIES"}


def test_every_op_is_reachable_from_the_public_tier():
    """``fullseye.ledger.<名前>`` から呼べること(登録面を 1 つ落とすと静かに消える)。"""
    import fullseye as fs
    import opsblob

    for name in opsblob.OPSBLOB:
        assert hasattr(fs.ledger, name), name


def test_the_typed_catalog_declares_the_family():
    import typed_catalog as tc

    rows = [r for r in tc.catalog() if r[1] == "blob"]
    assert len(rows) == 10
    assert {r[3] for r in rows} == {"labels2d", "table", "mask", "rgb", "image2d"}


def test_the_fuzzer_knows_the_new_type_and_can_seed_it():
    """新しい型に種と述語が無いと、その型を要る op は**永久に走らない**。"""
    import sys

    sys.path.insert(0, str(ROOT / "tools"))
    import chain_fuzz as cf

    assert "labels2d" in cf.TYPE_CHECKS
    seed = cf.make_generators()["labels2d"](np.random.default_rng(0))
    assert cf.TYPE_CHECKS["labels2d"](seed)
    assert int(seed.max()) >= 3, "種の物体が 3 個未満(形の違いを測れない)"
    # ★物体が 3 つとも別の形であること。同じ形を並べた種だと circularity も
    #   holes も全部同じ値になり、「どのノブでも同じ数を返す op」を見逃す。
    f = B.blob_features(seed)
    assert len(set(np.round(f["circularity"], 2).tolist())) == 3, f["circularity"]
    assert int(f["holes"].max()) >= 1, "穴のある物体が種に無い"
    assert float(f["eccentricity"].max()) > 0.9, "細長い物体が種に無い"


def test_the_predicate_does_not_accept_a_boolean_mask():
    """``mask`` の述語には当たる型なので、ここを緩めると検査面が死ぬ。"""
    import sys

    sys.path.insert(0, str(ROOT / "tools"))
    import chain_fuzz as cf

    assert not cf.TYPE_CHECKS["labels2d"](np.zeros((8, 8), bool))
    assert cf.TYPE_CHECKS["labels2d"](np.zeros((8, 8), np.int32))


# --------------------------------------------------------------------------- #
# 7. ガイドの手順が実際に走る                                                  #
# --------------------------------------------------------------------------- #
def test_the_family_guide_python_snippets_actually_run():
    """書いてあるとおりに打って動くこと(綴り検査ではなく実行で確かめる)。"""
    guide = ROOT / "docs" / "ops" / "blob" / "guides" / "blob_analysis.md"
    src = io.open(guide, encoding="utf-8").read()
    blocks = re.findall(r"```python\n(.*?)```", src, re.S)
    assert len(blocks) >= 4, "ガイドから実行できる例が減った"
    for i, block in enumerate(blocks, 1):
        exec(compile(block, "%s[%d]" % (guide.name, i), "exec"),
             {"__name__": "__guide__"})


# --------------------------------------------------------------------------- #
# 8. 割る —— 触れ合って 1 個になった塊を戻す                                    #
# --------------------------------------------------------------------------- #
def _two_touching_discs():
    """半径 20 と 14 の円板を重ねて置く。**真値は重ねる前の面積**。"""
    yy, xx = np.mgrid[0:100, 0:100]
    a = (yy - 50) ** 2 + (xx - 36) ** 2 <= 20 * 20
    b = (yy - 50) ** 2 + (xx - 66) ** 2 <= 14 * 14
    return a | b, int(a.sum()), int(b.sum())


def test_the_distance_transform_is_in_pixels_not_normalised():
    """★進化 op の `distance_transform` は最大値で割る。こちらは割らない。"""
    m = np.zeros((21, 21), bool)
    m[5:16, 5:16] = True                       # 11x11 の正方形
    d = B.blob_distance(m)
    assert float(d.max()) == pytest.approx(6.0), float(d.max())
    assert float(B.blob_distance(m, spacing=0.5).max()) == pytest.approx(3.0)


def test_seeds_take_an_absolute_h_and_do_not_clip_the_input():
    """★`xsk2_h_maxima` は入力を [0,1] に切り詰めるので生の距離では壊れる。

    ここは切り詰めない —— 距離 20 px の山と 2 px の山が区別できること。
    """
    m, _, _ = _two_touching_discs()
    d = B.blob_distance(m)
    assert float(d.max()) > 19.0, "距離が [0,1] へ潰れている"
    assert int(B.blob_seeds(d, 1.0).max()) == 2, "2 つの山が見つからない"
    # h を山の高さより大きくすると、種は 1 つに融ける
    assert int(B.blob_seeds(d, 30.0).max()) == 1


def test_seeds_reject_a_non_positive_h():
    d = B.blob_distance(_two_touching_discs()[0])
    with pytest.raises(ValueError, match="h"):
        B.blob_seeds(d, 0.0)


def test_split_separates_two_touching_discs():
    """★融合した塊が 2 つに戻ること。**面積の偏りも数字で押さえる**。

    分水嶺は重なりの部分を距離で分けるので、大きいほうが損をして小さい
    ほうが得をする。実測 1149 / 680(真値 1257 / 613)—— これは算法の
    定義どおりで、誤差ではない。
    """
    m, area_a, area_b = _two_touching_discs()
    lab = B.blob_label(m)
    assert int(lab.max()) == 1, "そもそも融合していない試験になっている"

    d = B.blob_distance(m)
    parts = B.blob_split(lab, B.blob_seeds(d, 1.0), d)
    f = B.blob_features(parts)
    assert f["n"] == 2
    got = np.sort(np.asarray(f["area"]))[::-1]
    assert got[0] == pytest.approx(1149, abs=30), got
    assert got[1] == pytest.approx(680, abs=30), got
    # 総面積は保存する(割っただけで画素を捨てていない)
    assert float(got.sum()) == float(m.sum())
    # 大きい側が損をして小さい側が得をする向き
    assert got[0] < area_a and got[1] > area_b


def test_split_leaves_alone_a_blob_with_no_seed():
    """種を持たない塊は**そのまま残す**(割る材料が無いのに消すのは嘘)。"""
    m, _, _ = _two_touching_discs()
    m2 = m.copy()
    m2[5:9, 5:9] = True                        # 遠くに小さい塊を 1 つ
    lab = B.blob_label(m2)
    d = B.blob_distance(m2)
    seeds = B.blob_seeds(d, 1.0)
    parts = B.blob_split(lab, seeds, d)
    f = B.blob_features(parts)
    assert f["n"] >= 3, f["n"]
    assert float(np.asarray(f["area"]).sum()) == float(m2.sum()), "画素が消えた"


def test_split_ignores_seeds_that_fall_outside_the_region():
    m, _, _ = _two_touching_discs()
    lab = B.blob_label(m)
    d = B.blob_distance(m)
    seeds = B.blob_seeds(d, 1.0).copy()
    seeds[2, 2] = int(seeds.max()) + 1         # 背景に置いた偽の種
    parts = B.blob_split(lab, seeds, d)
    assert not parts[2, 2], "領域の外の種が拾われた"
    assert int(parts.max()) == 2


def test_split_refuses_mismatched_shapes():
    m, _, _ = _two_touching_discs()
    lab = B.blob_label(m)
    with pytest.raises(ValueError, match="same shape"):
        B.blob_split(lab, B.blob_label(np.zeros((10, 10), bool) | True),
                     B.blob_distance(m))


def test_the_per_component_reconstruction_matches_the_global_one():
    """★速さのために成分ごとに回している。**答えが変わっていないこと**。

    512x512 に 200 個の円で 237.7 ms → 15.3 ms(15.5 倍)。速くするために
    別の答えを返していたら意味が無いので、素朴な全体版と全画素で比べる。
    """
    rng = np.random.default_rng(3)
    h, w = 160, 160
    img = np.zeros((h, w), bool)
    yy, xx = np.mgrid[0:h, 0:w]
    for _ in range(40):
        r0, c0 = rng.integers(8, h - 8), rng.integers(8, w - 8)
        img |= (yy - r0) ** 2 + (xx - c0) ** 2 <= rng.integers(4, 9) ** 2
    d = B.blob_distance(img)
    mine = B.blob_seeds(d, 2.0) > 0
    naive = (d - B._reconstruct_by_dilation(d - 2.0, d)) > 0
    assert np.array_equal(mine, naive), int((mine != naive).sum())
