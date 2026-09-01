# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""defectgen の契約テスト。

この生成器の価値は「欠陥画像」ではなく「**欠陥画像と、定義から作った画素完全な
マスクの対**」にある。だから固定すべき契約は、絵の見た目ではなく次の 4 つ:

  1. **マスクが画像と一致する** — マスクの内側だけが背景から変わっていること。
     ここがずれると、学習にも評価にも使えない注釈になる。
  2. **注文どおりの寸法になる** — 幅・長さ・向きを指定したのだから、測り返して
     一致すること(意図と実測の乖離は掃引データセットで致命的)。
  3. **決定的** — 同じ seed は同じ欠陥。再現できない素材では実験にならない。
  4. **fail-closed** — 退化した注文は黙って変な絵を返さず、明示的に拒否する。
"""
import numpy as np
import pytest

pytest.importorskip("scipy")

import defectgen as dg

GENERATORS = [
    ("scratch", dg.defect_scratch, {}),
    ("pits", dg.defect_pits, {"count": 12}),
    ("crack", dg.defect_crack, {}),
    ("blob", dg.defect_blob, {}),
]


# --------------------------------------------------------------------------- #
# 1. マスクと画像の一致(注釈としての正しさ)                                    #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("name,fn,kw", GENERATORS)
def test_mask_marks_exactly_what_changed(name, fn, kw):
    """マスクの内側だけが背景 0.5 から変わっていること。"""
    img, mask = fn(shape=(96, 96), seed=0, **kw)
    assert img.shape == mask.shape == (96, 96)
    assert img.dtype == np.float64 and mask.dtype == bool
    assert mask.any(), f"{name}: 欠陥が 1 画素も描かれていない"
    assert np.allclose(img[~mask], 0.5), f"{name}: マスクの外が変化している"
    assert not np.allclose(img[mask], 0.5), f"{name}: マスクの内が変化していない"


@pytest.mark.parametrize("name,fn,kw", GENERATORS)
def test_contrast_sign_selects_dark_or_bright_defects(name, fn, kw):
    """負なら暗く、正なら明るく。鏡面部品では傷が明るく出るので符号が要る。"""
    dark, dm = fn(shape=(96, 96), seed=1, contrast=-0.3, **kw)
    bright, bm = fn(shape=(96, 96), seed=1, contrast=+0.3, **kw)
    assert dark[dm].mean() < 0.5 < bright[bm].mean()
    assert np.array_equal(dm, bm), f"{name}: コントラストで形が変わっている"


@pytest.mark.parametrize("name,fn,kw", GENERATORS)
def test_output_stays_in_range(name, fn, kw):
    """飽和するコントラストでも [0,1] を出ない。"""
    img, _ = fn(shape=(64, 64), seed=2, contrast=-1.0, **kw)
    assert 0.0 <= img.min() and img.max() <= 1.0


# --------------------------------------------------------------------------- #
# 2. 注文どおりの寸法か(意図 vs 実測)                                          #
# --------------------------------------------------------------------------- #
def test_straight_scratch_matches_its_ordered_geometry():
    """wander=0 なら厳密な直線。長さ・幅・向きが測り返して一致すること。"""
    length, width = 60.0, 5.0
    img, mask = dg.defect_scratch(shape=(160, 160), length_px=length,
                                  width_px=width, angle_deg=0.0, wander=0.0,
                                  seed=0)
    st = dg.defect_stats(mask)
    # 水平の傷なので外接箱の高さ = 幅、横 = 長さ(円盤スタンプなので直径ぶん伸びる)
    assert st["bbox_h_px"] == pytest.approx(width, abs=2.0)
    assert st["bbox_w_px"] == pytest.approx(length + width, abs=3.0)
    # 面積 ≈ 長さ×幅(端の丸みぶん少し増える)
    assert st["area_px"] == pytest.approx(length * width, rel=0.35)
    assert st["major_axis_px"] > st["minor_axis_px"], "線状なのに等方に見える"


def test_scratch_angle_is_honoured():
    """45° を頼んだら 45° に伸びること(向きの取り違えは符号バグの温床)。"""
    kw = dict(shape=(200, 200), length_px=80.0, width_px=3.0, wander=0.0, seed=0)
    horiz = dg.defect_stats(dg.defect_scratch(angle_deg=0.0, **kw)[1])
    diag = dg.defect_stats(dg.defect_scratch(angle_deg=45.0, **kw)[1])
    vert = dg.defect_stats(dg.defect_scratch(angle_deg=90.0, **kw)[1])
    assert horiz["bbox_w_px"] > horiz["bbox_h_px"]
    assert vert["bbox_h_px"] > vert["bbox_w_px"]
    # 45° は外接箱がほぼ正方
    assert diag["bbox_w_px"] == pytest.approx(diag["bbox_h_px"], rel=0.15)


def test_bigger_orders_make_bigger_defects():
    """大きさの注文が単調に効くこと(掃引の前提)。"""
    areas = [dg.defect_stats(dg.defect_blob(shape=(128, 128), radius_px=r,
                                            roughness=0.0, seed=0)[1])["area_px"]
             for r in (5.0, 10.0, 20.0)]
    assert areas == sorted(areas) and areas[0] < areas[-1]
    # 真円(roughness=0)の面積は πr² に一致するはず
    exact = dg.defect_stats(dg.defect_blob(shape=(256, 256), radius_px=30.0,
                                           roughness=0.0, seed=0)[1])["area_px"]
    assert exact == pytest.approx(np.pi * 30.0 ** 2, rel=0.03)


def test_crack_branches_and_scratch_does_not():
    """割れは分岐する — それが傷との違い。分岐で充填率が下がる。"""
    _, crack = dg.defect_crack(shape=(200, 200), length_px=100.0, width_px=2.0,
                               branch_prob=0.5, max_branches=8, seed=3)
    _, plain = dg.defect_crack(shape=(200, 200), length_px=100.0, width_px=2.0,
                               branch_prob=0.0, seed=3)
    assert dg.defect_stats(crack)["area_px"] > dg.defect_stats(plain)["area_px"]


def test_pit_clustering_concentrates_them():
    """clustering を上げると孔が寄る = 外接箱が小さくなる。"""
    kw = dict(shape=(200, 200), count=30, radius_px=3.0, radius_sigma=0.0, seed=5)
    spread = dg.defect_stats(dg.defect_pits(clustering=0.0, **kw)[1])
    tight = dg.defect_stats(dg.defect_pits(clustering=1.0, **kw)[1])
    assert tight["bbox_w_px"] * tight["bbox_h_px"] < \
        spread["bbox_w_px"] * spread["bbox_h_px"]


# --------------------------------------------------------------------------- #
# 3. 決定性                                                                     #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("name,fn,kw", GENERATORS)
def test_same_seed_gives_the_same_defect(name, fn, kw):
    a_img, a_mask = fn(shape=(80, 80), seed=11, **kw)
    b_img, b_mask = fn(shape=(80, 80), seed=11, **kw)
    assert np.array_equal(a_img, b_img) and np.array_equal(a_mask, b_mask)
    c_img, _ = fn(shape=(80, 80), seed=12, **kw)
    assert not np.array_equal(a_img, c_img), f"{name}: seed を変えても同じ"


def test_surface_texture_is_deterministic_and_zero_mean_ish():
    for kind in ("orange_peel", "brushed", "grain"):
        a = dg.surface_texture((64, 64), kind, strength=0.1, seed=3)
        assert np.array_equal(a, dg.surface_texture((64, 64), kind,
                                                    strength=0.1, seed=3))
        assert 0.0 <= a.min() and a.max() <= 1.0
        assert a.mean() == pytest.approx(0.5, abs=0.05), kind
    # strength=0 は完全な平坦面
    flat = dg.surface_texture((32, 32), "grain", strength=0.0, seed=0)
    assert np.allclose(flat, 0.5)


def test_brushed_texture_is_directional():
    """ヘアライン仕上げは一方向に相関する — 等方ノイズと区別できること。"""
    t = dg.surface_texture((128, 128), "brushed", strength=0.2, scale_px=6.0, seed=0)
    along = float(np.abs(np.diff(t, axis=1)).mean())     # 横方向の変化
    across = float(np.abs(np.diff(t, axis=0)).mean())    # 縦方向の変化
    assert along > across * 2.0, "方向性が出ていない"


# --------------------------------------------------------------------------- #
# 4. 合成と計測                                                                 #
# --------------------------------------------------------------------------- #
def test_composite_keeps_the_texture_outside_the_mask():
    bg = dg.surface_texture((96, 96), "orange_peel", strength=0.08, seed=1)
    img, mask = dg.defect_scratch((96, 96), contrast=-0.2, seed=0)
    out = dg.composite_defect(bg, img, mask)
    assert np.array_equal(out[~mask], bg[~mask]), "正常面の質感が失われている"
    assert (out[mask] < bg[mask] + 1e-12).all(), "暗い傷が明るくなっている"


def test_composite_fails_closed_on_mismatch():
    bg = np.full((8, 8), 0.5)
    img, mask = dg.defect_blob((8, 8), radius_px=2.0, seed=0)
    with pytest.raises(ValueError, match="share"):
        dg.composite_defect(np.full((9, 9), 0.5), img, mask)
    with pytest.raises(ValueError, match="boolean"):
        dg.composite_defect(bg, img, mask.astype(np.float64))
    with pytest.raises(ValueError, match="non-finite"):
        dg.composite_defect(np.full((8, 8), np.nan), img, mask)


def test_defect_stats_reports_empty_rather_than_dividing_by_zero():
    st = dg.defect_stats(np.zeros((16, 16), bool))
    assert st["empty"] is True and st["area_px"] == 0
    st2 = dg.defect_stats(dg.defect_blob((64, 64), radius_px=8.0, seed=0)[1],
                          um_per_pixel=10.0)
    assert st2["major_axis_um"] == pytest.approx(st2["major_axis_px"] * 10.0)
    assert st2["area_um2"] == pytest.approx(st2["area_px"] * 100.0)


# --------------------------------------------------------------------------- #
# 5. fail-closed                                                                #
# --------------------------------------------------------------------------- #
def test_degenerate_orders_are_refused():
    with pytest.raises(ValueError, match="2x2"):
        dg.defect_scratch(shape=(1, 50))
    with pytest.raises(ValueError, match="MAX_DEFECT_PIXELS"):
        dg.defect_scratch(shape=(1 << 13, 1 << 13))
    with pytest.raises(ValueError, match="must be positive"):
        dg.defect_scratch(length_px=0.0)
    with pytest.raises(ValueError, match="must be a number"):
        dg.defect_scratch(width_px="3")           # float("3") が通ってしまう罠
    with pytest.raises(ValueError, match="must be >= 0"):
        dg.defect_scratch(wander=-0.1)
    with pytest.raises(ValueError, match="contrast"):
        dg.defect_scratch(contrast=2.0)
    with pytest.raises(ValueError, match="seed"):
        dg.defect_scratch(seed=1.5)
    with pytest.raises(ValueError, match="non-negative integer"):
        dg.defect_pits(count=-1)
    with pytest.raises(ValueError, match="kind"):
        dg.surface_texture(kind="marble")


def test_zero_count_pits_is_a_clean_empty_result_not_a_crash():
    """0 個の注文は「欠陥なし」であってエラーではない(掃引の端点で必ず来る)。"""
    img, mask = dg.defect_pits(shape=(32, 32), count=0, seed=0)
    assert not mask.any() and np.allclose(img, 0.5)
    assert dg.defect_stats(mask)["empty"] is True
