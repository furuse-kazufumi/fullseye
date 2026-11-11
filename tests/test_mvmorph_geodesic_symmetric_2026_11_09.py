"""opening_seg を測地的に、morph_skiz を対称に(2026-11-09 点検 g4_2d_stats の med)。

1. opening_seg は最近傍の種の番号を背景を跨いで配った: 大物体から 3 px 離れた 3x3 の塊
   (5x5 の収縮で種が消える)が大物体の番号 1 をもらった(測地的な参照では 0)。
2. morph_skiz は「右か下の隣と違う画素」だけに印を付けたので境界が片側へ寄った:
   像を 180° 回して戻すと 147 px が不一致(境界 105 px)、偶数幅の隙間で列 19 対 20。
"""
import numpy as np
import pytest
from scipy import ndimage

import mvmorph as M


def _old_opening_seg(a, s):
    seeds, n = ndimage.label(ndimage.binary_erosion(a, structure=s))
    if n == 0:
        return np.zeros(a.shape, np.int32)
    idx = ndimage.distance_transform_edt(seeds == 0, return_distances=False, return_indices=True)
    return np.where(a, seeds[idx[0], idx[1]], 0).astype(np.int32)


def _exact_skiz(a):
    """成分ごとに距離変換を取る厳密な参照(最近傍の集合が正確に分かる)。"""
    lab, n = ndimage.label(a, structure=np.ones((3, 3), bool))
    D = np.stack([ndimage.distance_transform_edt(lab != k) for k in range(1, n + 1)])
    d = D.min(0)
    S = D == d[None]
    edge = S.sum(0) >= 2
    dj = ~(S[:, :-1, :] & S[:, 1:, :]).any(0)
    edge[:-1] |= dj & (d[:-1] >= d[1:])
    edge[1:] |= dj & (d[1:] >= d[:-1])
    dj = ~(S[:, :, :-1] & S[:, :, 1:]).any(0)
    edge[:, :-1] |= dj & (d[:, :-1] >= d[:, 1:])
    edge[:, 1:] |= dj & (d[:, 1:] >= d[:, :-1])
    return edge & ~a


# ---- opening_seg ---------------------------------------------------------- #
def _two_objects():
    reg = np.zeros((40, 60), bool)
    reg[5:35, 5:30] = True        # 大物体
    reg[18:21, 33:36] = True      # 3 px 離れた 3x3 の塊(5x5 の収縮で消える)
    return reg


def test_seedless_blob_does_not_borrow_the_neighbours_label():
    lab = M.opening_seg(_two_objects(), np.ones((5, 5), bool))
    assert set(np.unique(lab[18:21, 33:36]).tolist()) == {0}
    assert set(np.unique(lab[5:35, 5:30]).tolist()) == {1}


def test_matches_skimage_geodesic_reference_on_the_probe():
    sks = pytest.importorskip("skimage.segmentation")
    reg = _two_objects()
    seeds, _ = ndimage.label(ndimage.binary_erosion(reg, np.ones((5, 5), bool)))
    ref = sks.watershed(-ndimage.distance_transform_edt(reg), seeds, mask=reg)
    lab = M.opening_seg(reg, np.ones((5, 5), bool))
    assert np.array_equal(lab, ref)


def test_single_convex_objects_unchanged():
    yy, xx = np.mgrid[0:60, 0:80]
    reg = (((yy - 30) / 20.0) ** 2 + ((xx - 25) / 18.0) ** 2 <= 1) | (((yy - 30) / 20.0) ** 2 + ((xx - 50) / 18.0) ** 2 <= 1)
    for se in (np.ones((3, 3), bool), np.ones((7, 7), bool)):
        assert np.array_equal(M.opening_seg(reg, se), _old_opening_seg(reg, se))


def test_every_label_region_is_connected_to_its_seed():
    rng = np.random.default_rng(3)
    for k in range(10):
        reg = ndimage.gaussian_filter(rng.random((70, 70)), 2.5) > 0.5
        lab = M.opening_seg(reg, np.ones((3, 3), bool))
        assert not lab[~reg].any()
        labels = np.unique(lab[lab > 0])
        assert labels.size > 0                     # 空の像では何も確かめないので、空でないことも表明する
        for v in labels:
            comp, nc = ndimage.label(lab == v, structure=np.ones((3, 3), bool))
            assert nc == 1, "label %d split into %d pieces" % (v, nc)


# ---- morph_skiz ----------------------------------------------------------- #
def _three_squares():
    reg = np.zeros((61, 61), bool)
    reg[10:20, 10:20] = True
    reg[40:50, 12:22] = True
    reg[25:35, 45:55] = True
    return reg


def test_skiz_is_invariant_under_flips_and_transpose():
    reg = _three_squares()
    s = M.morph_skiz(reg)
    assert int((s != M.morph_skiz(reg[::-1, ::-1])[::-1, ::-1]).sum()) == 0
    assert int((s != M.morph_skiz(reg[:, ::-1])[:, ::-1]).sum()) == 0
    assert int((s != M.morph_skiz(reg.T).T).sum()) == 0
    rng = np.random.default_rng(0)
    for k in range(8):
        m = ndimage.gaussian_filter(rng.random((90, 90)), 2) > 0.62
        sm = M.morph_skiz(m)
        assert np.array_equal(sm, M.morph_skiz(m[::-1, ::-1])[::-1, ::-1])
        assert np.array_equal(sm, M.morph_skiz(m.T).T)


def test_gap_midline():
    odd = np.zeros((21, 41), bool)
    odd[:, :5] = True
    odd[:, 36:] = True
    assert np.unique(np.nonzero(M.morph_skiz(odd))[1]).tolist() == [20]
    even = np.zeros((21, 40), bool)
    even[:, :5] = True
    even[:, 35:] = True
    assert np.unique(np.nonzero(M.morph_skiz(even))[1]).tolist() == [19, 20]


def test_matches_exact_per_component_reference():
    assert np.array_equal(M.morph_skiz(_three_squares()), _exact_skiz(_three_squares()))
    rng = np.random.default_rng(1)
    for k in range(10):
        m = ndimage.gaussian_filter(rng.random((100, 100)), 2) > 0.62
        assert np.array_equal(M.morph_skiz(m), _exact_skiz(m))


def test_skiz_contains_the_skimage_watershed_line():
    sks = pytest.importorskip("skimage.segmentation")
    reg = _three_squares()
    lab, _ = ndimage.label(reg, np.ones((3, 3)))
    ws = sks.watershed(ndimage.distance_transform_edt(~reg), lab, watershed_line=True)
    line = ws == 0
    assert (M.morph_skiz(reg) & line).sum() == line.sum()


def test_one_component_has_no_boundary():
    reg = np.zeros((20, 20), bool)
    reg[5:10, 5:10] = True
    assert not M.morph_skiz(reg).any()


# ---- opening_seg の速さ(2026-11-09 独立レビュー R3) ------------------------- #
def _layered_reference(a, s):
    """層ごとに全画面の距離変換を回す、速さを直す前の測地的な広げ方(答えの参照)。"""
    seeds, n = ndimage.label(ndimage.binary_erosion(a, structure=s))
    if n == 0:
        return np.zeros(a.shape, np.int32)
    idx = ndimage.distance_transform_edt(seeds == 0, return_distances=False, return_indices=True)
    lab = np.where(a, seeds[idx[0], idx[1]], 0)
    comp = M._same_value_components(lab, a)
    seeded = np.zeros(int(comp.max()) + 1, bool)
    seeded[comp[seeds > 0]] = True
    ok = a & seeded[comp]
    out = np.where(ok, lab, 0)
    todo = a & ~ok
    while todo.any():
        grown = ndimage.binary_dilation(ok, structure=np.ones((3, 3), bool)) & todo
        if not grown.any():
            break
        jdx = ndimage.distance_transform_edt(~ok, return_distances=False, return_indices=True)
        out[grown] = out[jdx[0][grown], jdx[1][grown]]
        ok |= grown
        todo &= ~grown
    return out.astype(np.int32)


def test_windowed_growth_gives_the_same_answer_as_the_full_frame_reference():
    rng = np.random.default_rng(0)
    changed = 0
    for k in range(120):
        a = ndimage.gaussian_filter(rng.random((80, 80)), rng.uniform(1.5, 3)) > rng.uniform(0.45, 0.6)
        for s in (np.ones((3, 3), bool), np.ones((5, 5), bool)):
            got = M.opening_seg(a, s)
            want = _layered_reference(a, s)
            assert np.array_equal(got, want)
            changed += int((got != _old_opening_seg(a, s)).sum())
    assert changed > 0                      # 広げ直しの経路を実際に通っている


def test_long_snake_next_to_another_seed_is_fast():
    import time
    N = 1024
    a = np.zeros((N, N), bool)
    a[N // 2 - 20:N // 2 + 20, 5:45] = True
    a[N // 2 - 20:N // 2 + 20, N - 45:N - 5] = True
    r = N // 2 + 25
    a[N // 2 + 19:r + 2, 20:22] = True
    a[r:r + 2, 20:N - 3] = True
    t0 = time.perf_counter()
    lab = M.opening_seg(a, np.ones((5, 5), bool))
    dt = time.perf_counter() - t0
    assert set(np.unique(lab[r:r + 2, 20:N - 3]).tolist()) == {1}
    assert dt < 2.0, dt                     # 直す前は 21.4 s(1 画素ずつ全画面の距離変換)


def test_two_far_apart_snakes_are_fast():
    """前線全体を 1 つの窓で囲むと、左上と右下に 1 本ずつあるだけで 1024² で 5.24 s に戻った(2 回目の確認)。"""
    import time
    N = 1024
    a = np.zeros((N, N), bool)
    a[5:45, 5:45] = True
    a[N - 45:N - 5, N - 45:N - 5] = True
    a[N // 2 - 20:N // 2 + 20, N // 2 - 20:N // 2 + 20] = True
    a[5:45, N - 45:N - 5] = True
    a[45:49, 22:24] = True
    a[47:49, 22:N - 3] = True
    a[N - 45:N - 5, 5:45] = True
    a[N - 50:N - 45, N - 24:N - 22] = True
    a[N - 50:N - 48, 3:N - 22] = True
    t0 = time.perf_counter()
    lab = M.opening_seg(a, np.ones((5, 5), bool))
    dt = time.perf_counter() - t0
    assert lab.shape == a.shape and not lab[~a].any()
    assert dt < 2.0, dt
