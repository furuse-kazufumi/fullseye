# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""volcolor — 3-D ラベルの色分けの検証。

この族の主張は 1 つ ―― **「切ってから色を付ける」と「色を付けてから切る」は違う**。
主張であるからには数で示す必要があるので、このファイルは「例外が出ないこと」ではなく

  * 閉形式の真値(既知半径の球 N 個)に対する成分数・体積・重心の**誤差**、
  * ちらつきの**本数**、
  * connectivity 6/18/26 で成分数が**どう変わるか**、
  * 異方 spacing を無視したときの**狂い幅**、
  * 病的入力(1 ボクセル 1 ラベル)での**時間**、

を測って固定する。加えて「例外が出る」ではなく「**黙って間違った数字や絵を返す**」
種類の失敗を敵対的に叩く ―― 軸の入れ替わり、背景 0 を成分と数える、色の衝突、
uint8 飽和、spacing の適用先違い、``labels.max()`` を成分数と誤ること。
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import imgio                                            # noqa: E402
import volcolor                                         # noqa: E402
import volops                                           # noqa: E402


# --------------------------------------------------------------------------- #
# 参照ファントム(決定的)                                                       #
# --------------------------------------------------------------------------- #
def phantom(shape=(24, 48, 48)):
    """16 個の球を格子状に置いた決定的なファントム。

    3-D では 16 成分。断面では層ごとに現れる球の数と並びが変わるので、
    「スライスごとに色を付け直す」と番号が振り直されて色が動く。
    """
    D, H, W = shape
    z, y, x = np.indices(shape).astype(np.float64)
    vol = np.zeros(shape)
    for gy in range(4):
        for gx in range(4):
            k = gy * 4 + gx
            cy, cx = 6.0 + gy * 12.0, 6.0 + gx * 12.0
            cz = 5.0 + (k % 4) * 4.5
            r = 2.0 + (k % 5) * 0.7
            vol[((z - cz) ** 2 + (y - cy) ** 2 + (x - cx) ** 2) <= r * r] = 1.0
    return vol


def labelled_phantom():
    return volops.vol_label(phantom(), connectivity=26)


def slab_stack(shape=(16, 16, 16)):
    """z 方向にずらして重なる 3 枚の板。投影の合成モードを試すための体。"""
    v = np.zeros(shape)
    v[0:6, 2:12, 2:12] = 1.0
    v[7:11, 4:14, 4:14] = 1.0
    v[12:16, 1:11, 6:16] = 1.0
    return v


def checkerboard(side):
    """1 ボクセル 1 ラベルの病的入力(成分数 = (side/2)**3)。"""
    v = np.zeros((side, side, side))
    v[::2, ::2, ::2] = 1.0
    return v


# --------------------------------------------------------------------------- #
# (1) パレット規約 —— 2-D と 3-D で色が一致することの固定                        #
# --------------------------------------------------------------------------- #
def test_palette_prefix_is_stable():
    """``n`` を増やしても先頭行は変わらない。これが 2-D / 3-D 一致の土台。"""
    small = volcolor.vol_label_palette(5, seed=0)
    big = volcolor.vol_label_palette(500, seed=0)
    assert np.array_equal(small, big[:6])
    assert big.shape == (501, 3)


def test_palette_row_zero_is_the_background():
    pal = volcolor.vol_label_palette(4, seed=0)
    assert np.array_equal(pal[0], np.zeros(3))          # 2-D と同じ既定 = 黒
    pal2 = volcolor.vol_label_palette(4, seed=0, background=(0.1, 0.2, 0.3))
    assert np.allclose(pal2[0], (0.1, 0.2, 0.3))
    assert np.array_equal(pal[1:], pal2[1:])            # 前景色は背景で変わらない


@pytest.mark.parametrize("seed", [0, 1, 7, 12345])
def test_matches_imgio_colorize_labels_exactly(seed):
    """**2-D の配色規約との一致を ``np.array_equal`` で固定する。**

    ``imgio.colorize_labels`` は 3-D 配列にもそのまま適用できる(値を引くだけ)ので、
    ボリューム全体で完全一致を要求できる。片側だけ配色を変える改変はここで落ちる。
    """
    L, n = labelled_phantom()
    assert n == 16
    assert np.array_equal(volcolor.vol_colorize_labels(L, seed=seed),
                          imgio.colorize_labels(L, seed=seed))


@pytest.mark.parametrize("seed", [0, 3])
def test_same_label_same_colour_in_2d_and_3d(seed):
    """**同じラベル番号なら 2-D の 1 枚でも 3-D でも同じ色**(番号に欠番があっても)。"""
    L, _ = labelled_phantom()
    rgb = volcolor.vol_colorize_labels(L, seed=seed)
    for z in (0, 5, 11, 23):
        # 断面を 2-D として `imgio` に渡す = その断面の max しか知らない状態
        assert np.array_equal(imgio.colorize_labels(L[z], seed=seed), rgb[z])

    # 欠番のあるラベル(3 と 9 だけ)でも同じ色が出る
    gap = np.zeros((8, 8, 8), np.int64)
    gap[1:3, 1:3, 1:3] = 3
    gap[5:7, 5:7, 5:7] = 9
    img2d = np.zeros((8, 8), np.int64)
    img2d[1:3, 1:3] = 3
    assert np.array_equal(imgio.colorize_labels(img2d, seed=seed)[1, 1],
                          volcolor.vol_colorize_labels(gap, seed=seed)[1, 1, 1])


def test_colorize_output_contract():
    L, _ = labelled_phantom()
    rgb = volcolor.vol_colorize_labels(L)
    assert rgb.shape == L.shape + (3,)
    assert rgb.dtype == np.float64
    assert rgb.min() >= 0.0 and rgb.max() <= 1.0
    assert np.array_equal(rgb[L == 0], np.zeros((int((L == 0).sum()), 3)))


def test_colour_collisions_are_disclosed_not_denied():
    """パレットは一様乱数なので**色は衝突しうる**。distinct を主張しない。"""
    measured = {}
    for nc in (16, 64, 256):
        pal = volcolor.vol_label_palette(nc, seed=0)[1:]
        d = np.linalg.norm(pal[:, None, :] - pal[None, :, :], axis=2)
        np.fill_diagonal(d, np.inf)
        measured[nc] = float(d.min())
    assert measured[16] == pytest.approx(0.1439, abs=1e-3)
    assert measured[64] == pytest.approx(0.0385, abs=1e-3)
    assert measured[256] == pytest.approx(0.0274, abs=1e-3)
    # 色数が増えるほど最近接は詰まる(= 色は識別子ではない)
    assert measured[16] > measured[64] > measured[256]


# --------------------------------------------------------------------------- #
# (2) 色の安定性 —— この族の存在理由                                            #
# --------------------------------------------------------------------------- #
def test_color_flicker_counts_the_difference():
    """**スライスごとに色を付けると 24 中 20 スライスで色が動き、ボリュームでは 0。**"""
    f = volcolor.vol_label_color_flicker(phantom(), axis="z", seed=0)
    assert f["n_components"] == 16
    assert f["n_slices"] == 24
    assert f["pairs_checked"] == 108
    assert f["slices_with_change"] == 20
    assert f["changed_pairs"] == 62
    assert f["changed_components"] == 16
    assert f["flicker_rate"] == pytest.approx(62 / 108, abs=1e-9)
    # ボリュームで色を付けた側は構造上ゼロ
    assert f["volume_slices_with_change"] == 0
    assert f["volume_changed_pairs"] == 0
    assert f["volume_changed_components"] == 0


def test_volume_colour_is_constant_along_a_component():
    """1 つの成分のボクセルは、どの断面でも**すべて同じ色**である。"""
    L, n = labelled_phantom()
    rgb = volcolor.vol_colorize_labels(L, seed=0)
    for i in range(1, n + 1):
        cols = np.unique(rgb[L == i], axis=0)
        assert cols.shape == (1, 3), "component %d has %d colours" % (i, cols.shape[0])


def test_flicker_is_deterministic():
    a = volcolor.vol_label_color_flicker(phantom(), seed=0)
    b = volcolor.vol_label_color_flicker(phantom(), seed=0)
    assert a == b


# --------------------------------------------------------------------------- #
# (3) connectivity の効き                                                       #
# --------------------------------------------------------------------------- #
def test_connectivity_6_18_26_on_corner_and_edge_contact():
    """斜めに接する 2 塊が 26 連結で 1 つに融合する、を数で。"""
    corner = np.zeros((9, 9, 9))
    corner[2:5, 2:5, 2:5] = 1.0
    corner[5:8, 5:8, 5:8] = 1.0                 # 角 1 点だけで接する
    edge = np.zeros((9, 9, 9))
    edge[2:5, 2:5, 2:5] = 1.0
    edge[5:8, 5:8, 2:5] = 1.0                   # 稜線で接する

    got_corner = {c: volops.vol_label(corner, connectivity=c)[1] for c in (6, 18, 26)}
    got_edge = {c: volops.vol_label(edge, connectivity=c)[1] for c in (6, 18, 26)}
    assert got_corner == {6: 2, 18: 2, 26: 1}   # 角接触は 26 だけが繋ぐ
    assert got_edge == {6: 2, 18: 1, 26: 1}     # 稜線接触は 18 から繋がる

    # 色数もそのまま連動する(成分が融合すれば色は 1 つ減る)
    for vol, expect in ((corner, got_corner), (edge, got_edge)):
        for c, n in expect.items():
            lab, _ = volops.vol_label(vol, connectivity=c)
            rgb = volcolor.vol_colorize_labels(lab, seed=0)
            fg = np.unique(rgb[lab > 0], axis=0)
            assert fg.shape[0] == n


def test_connectivity_does_not_change_the_separated_phantom():
    """離れている 16 球は 6/18/26 のどれでも 16 —— 効くのは接触があるときだけ。"""
    m = phantom()
    assert {c: volops.vol_label(m, connectivity=c)[1] for c in (6, 18, 26)} == \
        {6: 16, 18: 16, 26: 16}


# --------------------------------------------------------------------------- #
# (4) 閉形式の真値との突き合わせ                                                 #
# --------------------------------------------------------------------------- #
def test_stats_against_closed_form_spheres():
    """既知の球 N 個 —— 成分数は厳密、体積と重心は**誤差を数字で**出す。"""
    shape = (40, 40, 40)
    centres = [(10.0, 10.0, 10.0), (10.0, 10.0, 30.0), (30.0, 22.0, 12.0),
               (28.0, 30.0, 31.0)]
    radii = [4.0, 5.0, 6.0, 7.0]
    z, y, x = np.indices(shape).astype(np.float64)
    vol = np.zeros(shape)
    for (cz, cy, cx), r in zip(centres, radii):
        vol[((z - cz) ** 2 + (y - cy) ** 2 + (x - cx) ** 2) <= r * r] = 1.0
    L, n = volops.vol_label(vol, connectivity=26)
    assert n == len(radii)                              # 成分数は厳密に一致

    st = volcolor.vol_label_shape_stats(L)
    # ラベル番号は z, y, x の走査順に振られる。重心で対応づける
    vol_err, cen_err = [], []
    for rec in st:
        cz, cy, cx = rec["centroid"]
        j = int(np.argmin([abs(cz - a) + abs(cy - b) + abs(cx - c)
                           for a, b, c in centres]))
        true_v = 4.0 / 3.0 * np.pi * radii[j] ** 3
        vol_err.append(abs(rec["volume"] - true_v) / true_v)
        cen_err.append(max(abs(u - v) for u, v in zip(rec["centroid"], centres[j])))
        assert rec["isotropy"] > 0.93                   # 球なので等方
        assert rec["equivalent_diameter"] == pytest.approx(
            2.0 * radii[j], rel=0.02)
    # 実測(2026-09-02、半径 4 / 5 / 6 / 7 に対応する成分):体積の相対誤差は
    # 1.64 % / 4.13 % / 1.24 % / 2.23 % ―― これは**ボクセル化そのものの誤差**
    # (球面を格子で刻む誤差)であって統計側の誤差ではない。重心は真値と完全一致
    # (最大差 0.0)。
    assert max(vol_err) < 0.05, vol_err
    assert max(cen_err) < 1e-9, cen_err


def test_stats_agree_with_vol_region_props_exactly():
    """共通の 5 キーは :func:`volops.vol_region_props` と**厳密一致**。"""
    L, _ = labelled_phantom()
    props = volops.vol_region_props(L)
    stats = volcolor.vol_label_shape_stats(L)
    assert len(props) == len(stats) == 16
    for a, b in zip(props, stats):
        assert a["label"] == b["label"]
        assert a["voxel_count"] == b["voxel_count"]
        assert a["volume"] == pytest.approx(b["volume"], abs=1e-12)
        assert tuple(a["bbox"]) == tuple(b["bbox"])
        for u, v in zip(a["centroid"], b["centroid"]):
            assert u == pytest.approx(v, abs=1e-12)


def test_stats_do_not_invent_the_component_count_from_max():
    """``labels.max()`` を成分数と誤らない(欠番があると狂う典型)。"""
    gap = np.zeros((8, 8, 8), np.int64)
    gap[1:3, 1:3, 1:3] = 3
    gap[5:7, 5:7, 5:7] = 9
    st = volcolor.vol_label_shape_stats(gap)
    assert [r["label"] for r in st] == [3, 9]           # max は 9 でも成分は 2
    assert len(st) == 2
    leg = volcolor.vol_label_legend(gap)
    assert [r["label"] for r in leg] == [3, 9]
    assert [r["rank"] for r in leg] == [1, 2]


def test_background_is_never_counted_as_a_component():
    L, n = labelled_phantom()
    assert all(r["label"] > 0 for r in volcolor.vol_label_shape_stats(L))
    assert len(volcolor.vol_label_legend(L)) == n
    empty = np.zeros((6, 6, 6), np.int64)
    assert volcolor.vol_label_shape_stats(empty) == []
    assert volcolor.vol_label_legend(empty) == []
    assert volcolor.vol_labels_to_meshes(empty) == []


def test_elongation_is_infinite_by_contract():
    """厚み 1 の直線は ``elongation = inf``。0 除算の事故ではなく契約。"""
    line = np.zeros((12, 12, 12), np.int64)
    line[5, 5, 2:10] = 1
    line[2, 2, 2] = 2
    st = {r["label"]: r for r in volcolor.vol_label_shape_stats(line)}
    assert np.isinf(st[1]["elongation"])
    assert st[1]["linearity"] == pytest.approx(1.0)
    assert st[2]["elongation"] == 1.0                   # 単一ボクセル = 等方な点
    assert st[2]["isotropy"] == 1.0


# --------------------------------------------------------------------------- #
# (5) 異方 spacing                                                              #
# --------------------------------------------------------------------------- #
def test_anisotropic_spacing_changes_the_answer():
    """z だけ 3 倍粗い格子で、spacing を無視すると**球が板に見える**。"""
    sp = (3.0, 1.0, 1.0)
    S = np.zeros((17, 33, 33))
    z, y, x = np.indices(S.shape).astype(np.float64)
    S[(((z - 8) * sp[0]) ** 2 + ((y - 16) * sp[1]) ** 2
       + ((x - 16) * sp[2]) ** 2) <= 6.0 ** 2] = 1.0
    L, n = volops.vol_label(S, connectivity=26)
    assert n == 1
    no_sp = volcolor.vol_label_shape_stats(L)[0]
    with_sp = volcolor.vol_label_shape_stats(L, spacing=sp)[0]

    true_mm3 = 4.0 / 3.0 * np.pi * 6.0 ** 3             # 904.78 mm**3
    assert no_sp["voxel_count"] == 293
    assert with_sp["volume"] == pytest.approx(879.0, abs=1e-9)
    assert with_sp["volume"] / no_sp["volume"] == pytest.approx(3.0, abs=1e-12)
    # spacing あり: -2.85 % / なしを mm**3 と読むと -67.6 %
    assert abs(with_sp["volume"] - true_mm3) / true_mm3 == pytest.approx(0.0285, abs=2e-3)
    assert abs(no_sp["volume"] - true_mm3) / true_mm3 == pytest.approx(0.6762, abs=2e-3)
    # 形状指標も逆の結論になる: 0.0817(板)vs 0.7349(ほぼ等方 = 正しい)
    assert no_sp["isotropy"] == pytest.approx(0.0817, abs=2e-3)
    assert with_sp["isotropy"] == pytest.approx(0.7349, abs=2e-3)
    # 重心は voxel 添字のまま、centroid_mm だけが物理座標(適用先の取り違え検出)
    assert no_sp["centroid"] == pytest.approx(with_sp["centroid"], abs=1e-12)
    assert with_sp["centroid_mm"][0] == pytest.approx(with_sp["centroid"][0] * 3.0)
    assert with_sp["centroid_mm"][1] == pytest.approx(with_sp["centroid"][1])


def test_spacing_accepts_a_volume_meta_like_object():
    class Meta:
        spacing_mm = (2.0, 0.5, 0.5)

    L, _ = labelled_phantom()
    a = volcolor.vol_label_shape_stats(L, spacing=Meta())[0]
    b = volcolor.vol_label_shape_stats(L, spacing=(2.0, 0.5, 0.5))[0]
    assert a["volume"] == b["volume"]


@pytest.mark.parametrize("bad", [(0.0, 1.0, 1.0), (1.0, -1.0, 1.0), (1.0, 1.0),
                                 (np.nan, 1.0, 1.0)])
def test_spacing_is_fail_closed(bad):
    L, _ = labelled_phantom()
    with pytest.raises(ValueError):
        volcolor.vol_label_shape_stats(L, spacing=bad)


# --------------------------------------------------------------------------- #
# (6) 性能 —— 病的入力で二次爆発しないこと                                       #
# --------------------------------------------------------------------------- #
def _best_of(fn, repeats: int = 3) -> float:
    """3 回のうち最小 —— 時間の測定は上振れしかしないので min が最も安定。"""
    fn()                                                # warm-up(import / 初回確保)
    return min(_timed(fn) for _ in range(repeats))


def _timed(fn) -> float:
    t = time.perf_counter()
    fn()
    return time.perf_counter() - t


def test_shape_stats_does_not_blow_up_quadratically():
    """1 ボクセル 1 ラベルでボクセル数を **64 倍**にし、時間の伸びを測る。

    16**3 (512 成分) -> 64**3 (32768 成分) はボクセルも成分も 64 倍。
    線形なら約 64 倍、二次なら約 4096 倍になる。実測(2026-09-02、best-of-3):
    0.0037 s -> 0.2556 s = **69 倍**。ここでは環境差を吸収して
    **400 倍未満**(= 二次の 1/10 以下)を要求する。
    """
    small, n_s = volops.vol_label(checkerboard(16), connectivity=26)
    big, n_b = volops.vol_label(checkerboard(64), connectivity=26)
    assert (n_s, n_b) == (512, 32768)                   # 本当に 1 ボクセル 1 ラベル
    assert big.size / small.size == 64.0
    t_s = _best_of(lambda: volcolor.vol_label_shape_stats(small))
    t_b = _best_of(lambda: volcolor.vol_label_shape_stats(big))
    ratio = t_b / max(t_s, 1e-6)
    assert len(volcolor.vol_label_shape_stats(big)) == n_b
    assert ratio < 400.0, (t_s, t_b, ratio)


def test_colorize_does_not_blow_up_quadratically():
    small, _ = volops.vol_label(checkerboard(16), connectivity=26)
    big, _ = volops.vol_label(checkerboard(64), connectivity=26)
    t_s = _best_of(lambda: volcolor.vol_colorize_labels(small))
    t_b = _best_of(lambda: volcolor.vol_colorize_labels(big))
    assert t_b / max(t_s, 1e-6) < 400.0, (t_s, t_b)


def test_label_value_explosion_is_refused_before_allocating():
    """実在する成分が 2 つでも、番号が 10**9 ならパレットで死ぬ。**値**で切る。"""
    tiny = np.zeros((2, 2, 2), np.int64)
    tiny[0, 0, 0] = 1
    tiny[1, 1, 1] = 10 ** 9
    with pytest.raises(ValueError, match="MAX_LABELS"):
        volcolor.vol_colorize_labels(tiny)
    with pytest.raises(ValueError, match="MAX_LABELS"):
        volcolor.vol_label_palette(volcolor.MAX_LABELS + 1)


def test_mesh_count_is_capped():
    lab, n = volops.vol_label(checkerboard(32), connectivity=26)
    assert n == 4096 > volcolor.MAX_MESHES // 2
    lab2, n2 = volops.vol_label(checkerboard(40), connectivity=26)
    assert n2 == 8000 > volcolor.MAX_MESHES
    with pytest.raises(ValueError, match="MAX_MESHES"):
        volcolor.vol_labels_to_meshes(lab2)


# --------------------------------------------------------------------------- #
# (7) 断面 —— 軸の入れ替わりを黙って通さない                                      #
# --------------------------------------------------------------------------- #
def test_slice_axes_shapes_and_content():
    L, _ = labelled_phantom()
    rgb = volcolor.vol_colorize_labels(L, seed=0)
    D, H, W = L.shape
    ax = volcolor.vol_label_slice_rgb(rgb, 7, "z")
    co = volcolor.vol_label_slice_rgb(rgb, 7, "y")
    sa = volcolor.vol_label_slice_rgb(rgb, 7, "x")
    assert ax.shape == (H, W, 3)
    assert co.shape == (D, W, 3)
    assert sa.shape == (D, H, 3)
    assert np.array_equal(ax, rgb[7])
    assert np.array_equal(co, rgb[:, 7])
    assert np.array_equal(sa, rgb[:, :, 7])
    # 別名も同じ結果(axial / coronal / sagittal / 0 / 1 / 2)
    assert np.array_equal(ax, volcolor.vol_label_slice_rgb(rgb, 7, "axial"))
    assert np.array_equal(co, volcolor.vol_label_slice_rgb(rgb, 7, 1))
    assert np.array_equal(sa, volcolor.vol_label_slice_rgb(rgb, 7, "sagittal"))


def test_slice_refuses_negative_and_out_of_range_index():
    rgb = np.zeros((4, 5, 6, 3))
    with pytest.raises(ValueError, match="Negative indices"):
        volcolor.vol_label_slice_rgb(rgb, -1, "z")
    with pytest.raises(ValueError, match="out of range"):
        volcolor.vol_label_slice_rgb(rgb, 4, "z")
    with pytest.raises(ValueError, match="out of range"):
        volcolor.vol_label_slice_rgb(rgb, 6, "x")       # x は 6 なので 0..5
    assert volcolor.vol_label_slice_rgb(rgb, 5, "x").shape == (4, 5, 3)


def test_slice_refuses_a_0_255_volume():
    """``[0, 255]`` のまま渡すと uint8 で飽和して真っ白になる。手前で止める。"""
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        volcolor.vol_label_slice_rgb(np.full((3, 3, 3, 3), 200.0), 0)


def test_mpr_contains_the_three_planes():
    L, _ = labelled_phantom()
    rgb = volcolor.vol_colorize_labels(L, seed=0)
    D, H, W = L.shape
    m = volcolor.vol_label_mpr_rgb(rgb, gap=4)
    assert m.shape == (max(H, D), W + 4 + W + 4 + H, 3)
    assert np.array_equal(m[:H, :W], rgb[D // 2])
    with pytest.raises(ValueError, match="outside the volume"):
        volcolor.vol_label_mpr_rgb(rgb, center=(D, 0, 0))


def test_mpr_shows_the_same_component_in_the_same_colour():
    """3 面で同じ部品が同じ色 = 3 面が同じラベリングから来ている証拠。"""
    L, _ = labelled_phantom()
    rgb = volcolor.vol_colorize_labels(L, seed=0)
    st = {r["label"]: r for r in volcolor.vol_label_shape_stats(L)}
    pal = volcolor.vol_label_palette(int(L.max()), seed=0)
    lab = max(st, key=lambda i: st[i]["voxel_count"])
    cz, cy, cx = (int(round(v)) for v in st[lab]["centroid"])
    for axis, idx in (("z", cz), ("y", cy), ("x", cx)):
        sl = volcolor.vol_label_slice_rgb(rgb, idx, axis)
        assert np.any(np.all(np.isclose(sl, pal[lab]), axis=-1))


# --------------------------------------------------------------------------- #
# (8) 選別                                                                      #
# --------------------------------------------------------------------------- #
def test_select_by_volume_keeps_the_right_components():
    L, _ = labelled_phantom()
    st = volcolor.vol_label_shape_stats(L)
    counts = sorted(r["voxel_count"] for r in st)
    thr = counts[len(counts) // 2]
    out, kept = volcolor.vol_select_labels(L, st, min_voxels=thr)
    expect = sorted(r["label"] for r in st if r["voxel_count"] >= thr)
    assert sorted(int(i) for i in kept) == expect
    assert set(np.unique(out)) - {0} == set(expect)
    # 落ちた成分のボクセルは背景になる
    dropped = [r["label"] for r in st if r["voxel_count"] < thr]
    for i in dropped:
        assert not (out == i).any()


def test_select_exclude_border():
    """視野で切れている成分を落とす(CT の計測で使う標準手順)。"""
    v = np.zeros((10, 10, 10))
    v[0:3, 0:3, 0:3] = 1.0                              # 端に接する
    v[4:7, 4:7, 4:7] = 1.0                              # 内部
    L, n = volops.vol_label(v, connectivity=26)
    assert n == 2
    st = volcolor.vol_label_shape_stats(L)
    assert [r["touches_border"] for r in st] == [True, False]
    out, kept = volcolor.vol_select_labels(L, st, exclude_border=True)
    assert list(kept) == [2]
    assert set(np.unique(out)) == {0, 2}


def test_select_preserves_colours_unless_you_ask_for_relabelling():
    """**relabel=False は色を保ち、relabel=True は総取り替えになる。**"""
    L, _ = labelled_phantom()
    st = volcolor.vol_label_shape_stats(L)
    counts = sorted(r["voxel_count"] for r in st)
    thr = counts[4]
    keep, ids_k = volcolor.vol_select_labels(L, st, min_voxels=thr)
    rel, ids_r = volcolor.vol_select_labels(L, st, min_voxels=thr, relabel=True)
    assert list(ids_r) == list(range(1, len(ids_k) + 1))
    assert ids_k[0] != 1 or len(ids_k) != len(st)       # 実際に番号が動く状況

    before = volcolor.vol_colorize_labels(L, seed=0)
    after_keep = volcolor.vol_colorize_labels(keep, seed=0)
    after_rel = volcolor.vol_colorize_labels(rel, seed=0)
    m = keep > 0
    assert np.array_equal(before[m], after_keep[m])     # 色は 1 ボクセルも動かない
    assert not np.array_equal(before[m], after_rel[m])  # 振り直すと動く


def test_select_rejects_a_criterion_it_cannot_evaluate():
    """欠けたキーを既定値で埋めない —— 一件も落ちないフィルタを黙って作らない。"""
    L, _ = labelled_phantom()
    st = volcolor.vol_label_shape_stats(L)              # sphericity を持たない
    with pytest.raises(ValueError, match="sphericity"):
        volcolor.vol_select_labels(L, st, min_sphericity=0.5)
    with pytest.raises(ValueError, match="unknown selection criterion"):
        volcolor.vol_select_labels(L, st, min_roundness=0.5)
    # volops の props を渡せば通る(そちらが sphericity を出すので)
    props = volops.vol_region_props(L, surface="faces")
    out, kept = volcolor.vol_select_labels(L, props, min_sphericity=0.5)
    assert kept.size >= 1


def test_select_rejects_props_from_another_volume():
    L, _ = labelled_phantom()
    other = np.zeros((6, 6, 6), np.int64)
    other[1:3, 1:3, 1:3] = 1
    with pytest.raises(ValueError, match="does not cover"):
        volcolor.vol_select_labels(L, volcolor.vol_label_shape_stats(other))


def test_select_by_shape_separates_a_rod_from_a_ball():
    """伸長度で棒と球を分ける(2-D のブロブ選別の 3-D 版であることの確認)。"""
    v = np.zeros((20, 20, 20))
    z, y, x = np.indices(v.shape).astype(np.float64)
    v[((z - 5) ** 2 + (y - 5) ** 2 + (x - 5) ** 2) <= 16.0] = 1.0   # 球
    v[13:16, 12:15, 2:18] = 1.0                                     # 棒
    L, n = volops.vol_label(v, connectivity=26)
    assert n == 2
    st = {r["label"]: r for r in volcolor.vol_label_shape_stats(L)}
    ball = min(st, key=lambda i: st[i]["elongation"])
    rod = max(st, key=lambda i: st[i]["elongation"])
    assert st[ball]["elongation"] < 1.1
    assert st[rod]["elongation"] > 3.0
    _out, kept = volcolor.vol_select_labels(L, list(st.values()), max_elongation=2.0)
    assert list(kept) == [ball]


# --------------------------------------------------------------------------- #
# (9) 重ね合わせ                                                                #
# --------------------------------------------------------------------------- #
def test_overlay_alpha_is_linear_and_background_is_untouched():
    L, _ = labelled_phantom()
    rng = np.random.default_rng(3)
    grey = np.clip(0.25 + 0.15 * rng.standard_normal(L.shape) + 0.35 * (L > 0), 0, 1)
    base = np.repeat(((grey - grey.min()) / (grey.max() - grey.min()))[..., None], 3, 3)
    fg = L > 0
    got = []
    for a in (0.0, 0.25, 0.5, 0.75, 1.0):
        o = volcolor.vol_label_overlay(grey, L, seed=0, alpha=a)
        assert o.shape == L.shape + (3,)
        assert np.abs(o[~fg] - base[~fg]).max() == 0.0          # 背景は無傷
        got.append(float(np.abs(o[fg] - base[fg]).mean()))
    assert got[0] == 0.0
    assert got == pytest.approx([0.0, 0.0679, 0.1359, 0.2038, 0.2718], abs=2e-3)
    diffs = np.diff(got)
    assert np.allclose(diffs, diffs[0], atol=1e-9)              # alpha に対して直線


def test_overlay_alpha_1_paints_the_palette_colour():
    L, _ = labelled_phantom()
    grey = np.zeros(L.shape)
    o = volcolor.vol_label_overlay(grey, L, seed=0, alpha=1.0)
    assert np.array_equal(o[L > 0], volcolor.vol_colorize_labels(L, seed=0)[L > 0])


def test_overlay_boundary_mode_paints_only_the_shell():
    L, _ = labelled_phantom()
    grey = np.zeros(L.shape)
    fill = volcolor.vol_label_overlay(grey, L, alpha=1.0, mode="fill")
    edge = volcolor.vol_label_overlay(grey, L, alpha=1.0, mode="boundary")
    n_fill = int((fill.sum(axis=3) > 0).sum())
    n_edge = int((edge.sum(axis=3) > 0).sum())
    assert 0 < n_edge < n_fill                          # 殻だけ = 中身が見える
    # 実測(2026-09-02): 3128 前景ボクセルのうち殻は 1648(52.7 %)
    assert n_fill == 3128 and n_edge == 1648


def test_overlay_window_is_explicit():
    L, _ = labelled_phantom()
    grey = np.linspace(-1000.0, 3000.0, L.size).reshape(L.shape)
    wide = volcolor.vol_label_overlay(grey, L, alpha=0.0)
    narrow = volcolor.vol_label_overlay(grey, L, alpha=0.0, vmin=0.0, vmax=100.0)
    assert not np.allclose(wide, narrow)                # 窓が違えば絵が違う
    with pytest.raises(ValueError, match="greater than"):
        volcolor.vol_label_overlay(grey, L, vmin=100.0, vmax=100.0)


def test_overlay_on_a_constant_volume_does_not_divide_by_zero():
    L, _ = labelled_phantom()
    o = volcolor.vol_label_overlay(np.full(L.shape, 0.5), L, alpha=0.5)
    assert np.isfinite(o).all()


# --------------------------------------------------------------------------- #
# (10) 凡例                                                                     #
# --------------------------------------------------------------------------- #
def test_legend_is_sorted_deterministic_and_matches_the_palette():
    L, n = labelled_phantom()
    leg = volcolor.vol_label_legend(L, seed=0, measure="volume")
    assert len(leg) == n
    assert [r["rank"] for r in leg] == list(range(1, n + 1))
    assert [r["value"] for r in leg] == sorted((r["value"] for r in leg), reverse=True)
    assert sum(r["share"] for r in leg) == pytest.approx(1.0)
    assert leg == volcolor.vol_label_legend(L, seed=0, measure="volume")

    pal = volcolor.vol_label_palette(n, seed=0)
    rgbvol = volcolor.vol_colorize_labels(L, seed=0)
    for r in leg:
        assert np.allclose(r["rgb"], pal[r["label"]])
        # 凡例の色が本当にその成分の色である(図と表が食い違わない)
        assert np.allclose(np.unique(rgbvol[L == r["label"]], axis=0)[0], r["rgb"])
        assert r["hex"] == "#%02x%02x%02x" % tuple(
            int(round(v * 255.0)) for v in r["rgb"])


def test_legend_top_and_physical_units():
    L, _ = labelled_phantom()
    sp = (2.0, 0.5, 0.5)
    leg = volcolor.vol_label_legend(L, seed=0, spacing=sp, top=3)
    assert len(leg) == 3
    assert leg[0]["volume"] == pytest.approx(leg[0]["voxel_count"] * 0.5, abs=1e-9)
    with pytest.raises(ValueError, match="not a key of props"):
        volcolor.vol_label_legend(L, measure="roundness")
    with pytest.raises(ValueError, match="positive integer"):
        volcolor.vol_label_legend(L, top=0)


def test_legend_refuses_props_without_a_volume_column():
    """``volume`` が無い props を voxel_count で埋めない。

    埋めると「mm**3」の見出しの下にボクセル数が並ぶ表ができ、単位だけが黙って
    嘘になる(数字自体は妥当な大きさなので、誰も気づかない)。
    """
    L, _ = labelled_phantom()
    stripped = [{k: v for k, v in r.items() if k != "volume"}
                for r in volcolor.vol_label_shape_stats(L)]
    with pytest.raises(ValueError, match="no 'volume' key"):
        volcolor.vol_label_legend(L, stripped, measure="voxel_count")


def test_dead_parameters_were_removed_not_ignored():
    """色を置かない op に ``background`` を残さない(効かない引数は静かな嘘)。"""
    L, _ = labelled_phantom()
    for fn, args in ((volcolor.vol_label_overlay, (np.zeros(L.shape), L)),
                     (volcolor.vol_label_legend, (L,)),
                     (volcolor.vol_labels_to_meshes, (L,))):
        with pytest.raises(TypeError):
            fn(*args, background=(1.0, 0.0, 0.0))
    # 逆に、本当に背景を塗る 3 op では効く
    assert np.allclose(volcolor.vol_label_palette(2, background=(1, 0, 0))[0], (1, 0, 0))
    empty = np.zeros((4, 4, 4), np.int64)
    assert np.allclose(volcolor.vol_colorize_labels(empty, background=(1, 0, 0)),
                       np.tile((1.0, 0.0, 0.0), (4, 4, 4, 1)))
    assert np.allclose(volcolor.vol_label_volume_render(empty, background=(0, 1, 0)),
                       np.tile((0.0, 1.0, 0.0), (4, 4, 1)))


def test_select_refuses_shape_criteria_on_stats_without_shape():
    L, _ = labelled_phantom()
    lean = volcolor.vol_label_shape_stats(L, shape=False)
    assert "elongation" not in lean[0]
    with pytest.raises(ValueError, match="elongation"):
        volcolor.vol_select_labels(L, lean, max_elongation=2.0)
    out, kept = volcolor.vol_select_labels(L, lean, min_voxels=1)    # 体積なら通る
    assert kept.size == 16


def test_legend_accepts_vol_region_props_measures():
    L, _ = labelled_phantom()
    props = volops.vol_region_props(L, surface="faces")
    leg = volcolor.vol_label_legend(L, props, measure="sphericity")
    assert leg[0]["measure"] == "sphericity"
    assert leg[0]["value"] >= leg[-1]["value"]


# --------------------------------------------------------------------------- #
# (11) メッシュ                                                                 #
# --------------------------------------------------------------------------- #
def _mesh_volume(V, F):
    """符号付き体積(発散定理)。marching cubes の閉曲面に対して使う。"""
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    return float(abs(np.einsum("ij,ij->i", a, np.cross(b, c)).sum()) / 6.0)


def test_meshes_carry_the_same_colours_as_the_slices():
    L, n = labelled_phantom()
    meshes = volcolor.vol_labels_to_meshes(L, seed=0)
    assert len(meshes) == n
    pal = volcolor.vol_label_palette(int(L.max()), seed=0)
    rgbvol = volcolor.vol_colorize_labels(L, seed=0)
    for md in meshes:
        assert md["vertices"].ndim == 2 and md["vertices"].shape[1] == 3
        assert md["faces"].ndim == 2 and md["faces"].shape[1] == 3
        assert md["faces"].max() < md["vertices"].shape[0]
        assert np.allclose(md["color"], pal[md["label"]])
        assert np.allclose(np.unique(rgbvol[L == md["label"]], axis=0)[0], md["color"])


def test_mesh_axes_order_is_explicit():
    """``axes`` を取り違えると例外なく上下と前後が入れ替わる —— 両方を固定する。"""
    L, _ = labelled_phantom()
    st = {r["label"]: r for r in volcolor.vol_label_shape_stats(L)}
    xyz = volcolor.vol_labels_to_meshes(L, seed=0, axes="xyz")
    zyx = volcolor.vol_labels_to_meshes(L, seed=0, axes="zyx")
    for a, b in zip(xyz, zyx):
        assert np.allclose(a["vertices"], b["vertices"][:, ::-1])
        cz, cy, cx = st[a["label"]]["centroid"]
        # zyx の重心は stats の (z, y, x) に一致し、xyz はその逆順
        assert np.allclose(b["vertices"].mean(axis=0), (cz, cy, cx), atol=0.6)
        assert np.allclose(a["vertices"].mean(axis=0), (cx, cy, cz), atol=0.6)


def test_mesh_volume_tracks_the_voxel_count():
    L, _ = labelled_phantom()
    st = {r["label"]: r for r in volcolor.vol_label_shape_stats(L)}
    for md in volcolor.vol_labels_to_meshes(L, seed=0, axes="zyx"):
        v_mesh = _mesh_volume(md["vertices"], md["faces"])
        v_vox = st[md["label"]]["voxel_count"]
        # marching cubes は角を落とすので voxel 数より小さく出る(既知・実測)
        assert 0.55 * v_vox < v_mesh < 1.05 * v_vox, (md["label"], v_mesh, v_vox)


def test_mesh_of_a_border_touching_component_is_closed():
    """端に接する成分もパディングして閉じる(穴の開いたメッシュを出さない)。"""
    v = np.zeros((8, 8, 8))
    v[0:3, 0:3, 0:3] = 1.0
    L, _ = volops.vol_label(v, connectivity=26)
    md = volcolor.vol_labels_to_meshes(L, seed=0, axes="zyx")[0]
    assert _mesh_volume(md["vertices"], md["faces"]) > 10.0
    # 閉曲面なら全ての辺がちょうど 2 回現れる
    F = md["faces"]
    edges = np.sort(np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), axis=1)
    _u, cnt = np.unique(edges, axis=0, return_counts=True)
    assert set(np.unique(cnt)) == {2}


def test_mesh_spacing_scales_the_vertices():
    L, _ = labelled_phantom()
    a = volcolor.vol_labels_to_meshes(L, ids=[1], seed=0, axes="zyx")[0]
    b = volcolor.vol_labels_to_meshes(L, ids=[1], seed=0, axes="zyx",
                                      spacing=(2.0, 0.5, 0.5))[0]
    assert np.allclose(b["vertices"], a["vertices"] * np.array([2.0, 0.5, 0.5]))


# --------------------------------------------------------------------------- #
# (12) 投影 —— チャネル別 max が色を捏造することの実証                            #
# --------------------------------------------------------------------------- #
def test_channelwise_max_would_invent_colours():
    """**この op が MIP を提供しない理由**を数で示す。"""
    L, n = volops.vol_label(slab_stack(), connectivity=26)
    assert n == 3
    pal = volcolor.vol_label_palette(int(L.max()), seed=0)
    rgb = volcolor.vol_colorize_labels(L, seed=0)
    mip = rgb.max(axis=0)                               # チャネル別 max(禁じ手)
    front = volcolor.vol_label_volume_render(L, axis="z", mode="front", seed=0)
    fg = (L > 0).any(axis=0)

    def not_in_palette(img, mask):
        flat = img[mask].reshape(-1, 3)
        ok = np.zeros(len(flat), bool)
        for c in pal:
            ok |= np.all(np.isclose(flat, c), axis=1)
        return int(len(flat)), int((~ok).sum())

    n_fg, bad_mip = not_in_palette(mip, fg)
    n_all, bad_front = not_in_palette(front, np.ones_like(fg))
    assert (n_fg, bad_mip) == (168, 90)                 # 前景 168 のうち 90 が捏造色
    assert (n_all, bad_front) == (256, 0)               # front は 1 画素も捏造しない

    with pytest.raises(ValueError, match="refused on purpose"):
        volcolor.vol_label_volume_render(L, mode="max")
    with pytest.raises(ValueError, match="refused on purpose"):
        volcolor.vol_label_volume_render(L, mode="mip")


def test_volume_render_front_back_and_alpha():
    L, _ = volops.vol_label(slab_stack(), connectivity=26)
    pal = volcolor.vol_label_palette(int(L.max()), seed=0)
    front = volcolor.vol_label_volume_render(L, "z", "front", seed=0)
    back = volcolor.vol_label_volume_render(L, "z", "back", seed=0)
    alpha = volcolor.vol_label_volume_render(L, "z", "alpha", seed=0, alpha=0.35)
    assert front.shape == back.shape == alpha.shape == (16, 16, 3)
    assert not np.array_equal(front, back)              # 表と裏は違う絵

    # front は「最初に当たる非背景ボクセルの色」そのもの(閉形式で照合)
    nz = L > 0
    has = nz.any(axis=0)
    first = np.argmax(nz, axis=0)
    rr, cc = np.indices(first.shape)
    expect = pal[np.where(has, L[first, rr, cc], 0)]
    expect[~has] = 0.0
    assert np.array_equal(front, expect)

    # alpha 合成は Porter & Duff の over: 全部背景なら背景色、重なるほど濃い
    assert np.allclose(alpha[~has], 0.0)
    assert alpha[has].sum() > 0.0
    assert alpha.min() >= 0.0 and alpha.max() <= 1.0
    # alpha=1 なら front と一致する(手前で完全に不透明になる)
    assert np.allclose(volcolor.vol_label_volume_render(L, "z", "alpha", seed=0,
                                                        alpha=1.0), front)


def test_volume_render_axes():
    L, _ = volops.vol_label(slab_stack((10, 12, 14)), connectivity=26)
    assert volcolor.vol_label_volume_render(L, "z").shape == (12, 14, 3)
    assert volcolor.vol_label_volume_render(L, "y").shape == (10, 14, 3)
    assert volcolor.vol_label_volume_render(L, "x").shape == (10, 12, 3)


# --------------------------------------------------------------------------- #
# (13) fail-closed 一覧                                                         #
# --------------------------------------------------------------------------- #
def _labels3():
    return np.zeros((4, 4, 4), np.int64)


@pytest.mark.parametrize("call, match", [
    (lambda: volcolor.vol_colorize_labels(np.zeros((4, 4), np.int64)), "3-D"),
    (lambda: volcolor.vol_colorize_labels(np.zeros((4, 4, 4, 4), np.int64)), "3-D"),
    (lambda: volcolor.vol_colorize_labels(np.zeros((4, 4, 4))), "must be integers"),
    (lambda: volcolor.vol_colorize_labels(-np.ones((4, 4, 4), np.int64)), "negative"),
    (lambda: volcolor.vol_colorize_labels(np.zeros((0, 4, 4), np.int64)), "empty"),
    (lambda: volcolor.vol_colorize_labels(_labels3(), seed=-1), "non-negative"),
    (lambda: volcolor.vol_colorize_labels(_labels3(), background=(0, 0)), "RGB"),
    (lambda: volcolor.vol_colorize_labels(_labels3(), background=(0, 0, 2.0)), "RGB"),
    (lambda: volcolor.vol_label_palette(-1), "non-negative"),
    (lambda: volcolor.vol_label_palette(2.5), "non-negative"),
    (lambda: volcolor.vol_label_slice_rgb(np.zeros((4, 4, 4)), 0), "D, H, W, 3"),
    (lambda: volcolor.vol_label_slice_rgb(np.full((3, 3, 3, 3), np.nan), 0), "non-finite"),
    (lambda: volcolor.vol_label_slice_rgb(np.zeros((3, 3, 3, 3)), 0, "t"), "axis must"),
    (lambda: volcolor.vol_label_overlay(np.full((4, 4, 4), np.inf), _labels3()), "non-finite"),
    (lambda: volcolor.vol_label_overlay(np.zeros((4, 4, 5)), _labels3()), "same shape"),
    (lambda: volcolor.vol_label_overlay(np.zeros((4, 4, 4)), _labels3(), alpha=-0.1), "alpha"),
    (lambda: volcolor.vol_label_overlay(np.zeros((4, 4, 4)), _labels3(), mode="x"), "mode must"),
    (lambda: volcolor.vol_label_volume_render(_labels3(), mode="pretty"), "mode must"),
    (lambda: volcolor.vol_labels_to_meshes(_labels3(), axes="yxz"), "axes must"),
    (lambda: volcolor.vol_labels_to_meshes(_labels3(), level=0.0), "level"),
    (lambda: volcolor.vol_labels_to_meshes(_labels3(), ids=[7]), "not present"),
    (lambda: volcolor.vol_select_labels(_labels3(), keep=[3]), "not present"),
    (lambda: volcolor.vol_select_labels(_labels3(), props="nope"), "list of per-label"),
])
def test_fail_closed(call, match):
    with pytest.raises(ValueError, match=match):
        call()


def test_voxel_cap_is_enforced_before_allocating():
    """巨大 shape は**確保する前に**断る(0-stride で実メモリを使わずに試す)。"""
    huge = np.lib.stride_tricks.as_strided(np.zeros(1, np.int64),
                                           (300, 300, 300), (0, 0, 0))
    assert huge.size > volcolor.MAX_COLOR_VOXELS
    with pytest.raises(ValueError, match="MAX_COLOR_VOXELS"):
        volcolor.vol_colorize_labels(huge)


def test_bool_labels_are_accepted_as_a_single_component():
    m = np.zeros((5, 5, 5), bool)
    m[1:3, 1:3, 1:3] = True
    rgb = volcolor.vol_colorize_labels(m, seed=0)
    assert rgb.shape == (5, 5, 5, 3)
    assert np.allclose(np.unique(rgb[m], axis=0)[0],
                       volcolor.vol_label_palette(1, seed=0)[1])


# --------------------------------------------------------------------------- #
# (14) 台帳                                                                     #
# --------------------------------------------------------------------------- #
def test_docstrings_only_cite_tests_that_exist():
    """docstring が名指しするテストが実在することを機械で確かめる。

    「テストで固定してある」と書いてある docstring は、その名前のテストが消えた
    瞬間から**嘘になる**。しかも読む側からは検証できない(名前があるだけで
    通ったように見える)ので、参照の実在をここで強制する。
    """
    import re

    here = os.path.dirname(os.path.abspath(__file__))
    src = open(os.path.join(os.path.dirname(here), "volcolor.py"),
               encoding="utf-8").read()
    mine = open(os.path.join(here, "test_volcolor.py"), encoding="utf-8").read()
    have = set(re.findall(r"^def (test_\w+)", mine, re.M))
    cited = set(re.findall(r"test_volcolor\.py::(\w+)", src))
    assert cited, "volcolor.py should cite the tests that fix its claims"
    assert not (cited - have), sorted(cited - have)


def test_ledger_is_complete_and_consistent():
    import opsvolcolor

    assert opsvolcolor.missing() == []
    assert sorted(opsvolcolor.list_ops()) == sorted(volcolor.VOLCOLOR)
    assert len(volcolor.VOLCOLOR) == len(volcolor.__all__) - 4   # 定数 4 つを除く
    for name in volcolor.VOLCOLOR:
        assert hasattr(volcolor, name)
        assert getattr(volcolor, name).__doc__, name


def test_ledger_call_returns_the_declared_type():
    import opsvolcolor

    L, _ = labelled_phantom()
    raw = opsvolcolor.get("vol_select_labels")(L, min_voxels=1)
    assert isinstance(raw, tuple) and len(raw) == 2      # 素の返りは情報を削らない
    typed = opsvolcolor.call("vol_select_labels", L, min_voxels=1)
    assert isinstance(typed, np.ndarray) and typed.ndim == 3

    # 他の 10 op は宣言型を素で返す
    checks = {
        "vol_label_palette": (lambda: opsvolcolor.call("vol_label_palette", 4),
                              lambda v: isinstance(v, np.ndarray) and v.ndim == 2),
        "vol_colorize_labels": (lambda: opsvolcolor.call("vol_colorize_labels", L),
                                lambda v: isinstance(v, np.ndarray) and v.ndim == 4
                                and v.shape[3] == 3),
        "vol_label_shape_stats": (lambda: opsvolcolor.call("vol_label_shape_stats", L),
                                  lambda v: isinstance(v, list)),
        "vol_label_volume_render": (
            lambda: opsvolcolor.call("vol_label_volume_render", L),
            lambda v: isinstance(v, np.ndarray) and v.ndim == 3 and v.shape[2] == 3),
        "vol_label_color_flicker": (
            lambda: opsvolcolor.call("vol_label_color_flicker", phantom((8, 16, 16))),
            lambda v: isinstance(v, dict)),
    }
    for name, (run, ok) in checks.items():
        assert ok(run()), name


def test_rgbvolume_is_not_a_lightfield():
    """新語彙 `rgbvolume` を分けた理由の再現 —— 既存 lightfield が黙って食う。"""
    import lightfield

    rgbvol = volcolor.vol_colorize_labels(labelled_phantom()[0], seed=0)[:8, :16, :16]
    assert rgbvol.ndim == 4                             # lightfield の述語を満たす
    silent = []
    for fn_name in ("lf_refocus", "lf_subaperture", "lf_epi", "lf_depth_from_focus"):
        fn = getattr(lightfield, fn_name, None)
        if fn is None:
            continue
        try:
            r = fn(rgbvol)
        except Exception:
            continue
        arr = np.asarray(r[0] if isinstance(r, tuple) else r)
        if np.isfinite(arr).all():
            silent.append(fn_name)
    assert len(silent) >= 3, silent                     # 実測は 4 op すべて
    # 逆向きは fail-closed(安全なのは片側だけ = 実行時チェックに頼れない)
    with pytest.raises(ValueError):
        volcolor.vol_label_slice_rgb(np.zeros((4, 4, 8, 8)), 0)
