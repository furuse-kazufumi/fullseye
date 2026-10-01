# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""HALCON "Segmentation" 章の 9 op(``segmentation.py``)の契約と第 2 実装の門。

1. 契約: 形・dtype・有限・決定的(同じ入力で 2 回呼んで一致)。
2. 第 2 実装 / 定理: それぞれの op に、絵を見ずに答えが決まる門を 1 つ以上置く。
   * ``watersheds_marker`` = 自前の優先度つき洪水(heapq)と画素単位で一致 + 尾根で割れる
   * ``expand_gray``       = 「候補画素 ∪ 種」の中で種を含む 4 連結成分(反復膨張の不動点)
   * ``regiongrowing_n``   = 階段状の特徴画像では連結成分ラベリングと一致(番号の付け替えに不変)
   * ``class_2dim_sup``    = 2 次元特徴空間の既知の箱
   * ``class_2dim_unsup``  = よく離れた 3 クラスタの分割と一致(番号の付け替えに不変)
   * ``learn_ndim_norm`` → ``class_ndim_norm`` の往復 = 既知の超楕円体(マハラノビス距離)
   * ``classify_image_class_lut`` = 画素ごとの総当たり
   * ``check_difference``  = 画素ごとの総当たり
3. 台帳と公開経路: ``opssegmentation`` が 9 本すべてを持ち ``fullseye.ledger`` から届く。

★死んでいたコードなので、見つけた欠陥は直さずに ``xfail(strict=True)`` で**記録**する
(直ったら strict が落として知らせる)。中身は scratchpad の NOTES.md と同じ。
"""
from __future__ import annotations

import heapq
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import segmentation as S  # noqa: E402

OPS9 = (
    "check_difference", "class_2dim_sup", "learn_ndim_norm", "class_ndim_norm",
    "class_2dim_unsup", "classify_image_class_lut", "expand_gray", "regiongrowing_n",
    "watersheds_marker",
)


# --------------------------------------------------------------------------- #
# helpers                                                                      #
# --------------------------------------------------------------------------- #
def _same_partition(a, b) -> bool:
    """2 枚のラベル画像が**番号の付け替えを除いて**同じ分割か(全単射の検査)。"""
    a = np.asarray(a).ravel()
    b = np.asarray(b).ravel()
    assert a.shape == b.shape
    fwd, bwd = {}, {}
    for x, y in zip(a.tolist(), b.tolist()):
        if fwd.setdefault(x, y) != y:
            return False
        if bwd.setdefault(y, x) != x:
            return False
    return True


def _priority_flood(image, markers):
    """マーカー制御分水嶺の第 2 実装(優先度つき洪水、4 連結、先に押した側が勝つ)。

    skimage の ``watershed`` と同じ規則: 画素値の小さい順に取り出し、取り出した画素の
    ラベルを未割当の隣接画素に与えて待ち行列へ押す。既に待ち行列にある画素は押し直さない。
    画素値がすべて相異なるときは順序が一意に決まるので、画素単位で一致するはず。
    """
    im = np.asarray(image, float)
    lab = np.asarray(markers, int).copy()
    H, W = im.shape
    heap = []
    order = 0
    queued = lab != 0
    for r in range(H):
        for c in range(W):
            if lab[r, c]:
                heapq.heappush(heap, (im[r, c], order, r, c))
                order += 1
    while heap:
        _v, _o, r, c = heapq.heappop(heap)
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            rr, cc = r + dr, c + dc
            if 0 <= rr < H and 0 <= cc < W and not queued[rr, cc]:
                lab[rr, cc] = lab[r, c]
                queued[rr, cc] = True
                heapq.heappush(heap, (im[rr, cc], order, rr, cc))
                order += 1
    return lab


def _rng():
    return np.random.default_rng(20261002)


# --------------------------------------------------------------------------- #
# 1. check_difference                                                          #
# --------------------------------------------------------------------------- #
def test_check_difference_contract_and_brute_force():
    rng = _rng()
    a = rng.random((12, 15))
    b = a + rng.normal(0.0, 0.08, a.shape)
    out = S.check_difference(a, b, tol=0.1)
    assert out.shape == a.shape and out.dtype == bool
    want = np.zeros(a.shape, bool)
    cells = [(r, c) for r in range(12) for c in range(15)]
    assert len(cells) > 0
    for r, c in cells:
        want[r, c] = abs(a[r, c] - b[r, c]) > 0.1
    assert np.array_equal(out, want)
    assert np.array_equal(out, S.check_difference(a, b, tol=0.1))       # 決定的
    assert not S.check_difference(a, a, tol=0.0).any()                  # 差 0 は tol=0 でも「超えない」


def test_check_difference_is_symmetric_and_threshold_is_strict():
    a = np.zeros((3, 3))
    b = np.full((3, 3), 0.1)
    assert not S.check_difference(a, b, tol=0.1).any()                   # ちょうど tol は「超えない」
    assert S.check_difference(a, b, tol=0.0999).all()
    assert np.array_equal(S.check_difference(a, b, 0.05), S.check_difference(b, a, 0.05))


# --------------------------------------------------------------------------- #
# 2. class_2dim_sup                                                            #
# --------------------------------------------------------------------------- #
def test_class_2dim_sup_is_the_feature_space_box_of_the_reference_region():
    """参照領域の 2 特徴の [min, max] × [min, max] に入る画素が選ばれる(箱の定理)。"""
    y, x = np.mgrid[0:20, 0:30]
    f1 = x / 29.0
    f2 = y / 19.0
    ref = np.zeros((20, 30), bool)
    ref[5:10, 10:20] = True                   # f1 ∈ [10/29, 19/29], f2 ∈ [5/19, 9/19]
    out = S.class_2dim_sup(f1, f2, ref)
    assert out.shape == ref.shape and out.dtype == bool
    want = (x >= 10) & (x <= 19) & (y >= 5) & (y <= 9)
    assert np.array_equal(out, want)
    assert out[ref].all()                      # 参照領域は必ず自分の箱に入る
    assert np.array_equal(out, S.class_2dim_sup(f1, f2, ref))


def test_class_2dim_sup_non_convex_reference_becomes_its_bounding_box():
    """★実測の記録: 特徴空間で L 字の参照は**外接箱に膨らむ**(HALCON は特徴空間の領域そのもの)。"""
    y, x = np.mgrid[0:10, 0:10]
    f1 = x / 9.0
    f2 = y / 9.0
    ref = np.zeros((10, 10), bool)
    ref[0:2, 0:10] = True                      # 横棒
    ref[0:10, 0:2] = True                      # 縦棒 → L 字
    out = S.class_2dim_sup(f1, f2, ref)
    assert out.all(), "L 字の外接箱は全域 —— 箱で近似していることの記録"


@pytest.mark.xfail(strict=True, reason="NOTES.md B2: 空の参照領域で zero-size reduction の ValueError(fail-closed だが理由の無い例外)")
def test_class_2dim_sup_empty_reference_gives_a_reasoned_error():
    with pytest.raises(ValueError, match="ref_region"):
        S.class_2dim_sup(np.zeros((4, 4)), np.zeros((4, 4)), np.zeros((4, 4), bool))


# --------------------------------------------------------------------------- #
# 3. learn_ndim_norm → class_ndim_norm(往復)                                  #
# --------------------------------------------------------------------------- #
def test_learn_ndim_norm_model_contract():
    rng = _rng()
    X = rng.normal(size=(400, 3)) @ np.array([[2.0, 0.3, 0.0], [0.0, 1.0, 0.0], [0.5, 0.0, 0.5]])
    X += np.array([1.0, -2.0, 0.5])
    m = S.learn_ndim_norm(X)
    assert set(m) == {"mean", "cov", "inv"}
    assert m["mean"].shape == (3,) and m["cov"].shape == (3, 3) and m["inv"].shape == (3, 3)
    assert np.isfinite(m["cov"]).all() and np.isfinite(m["inv"]).all()
    assert np.allclose(m["mean"], X.mean(0))
    assert np.allclose(m["cov"], np.cov(X.T) + 1e-6 * np.eye(3))
    assert np.allclose(m["inv"] @ m["cov"], np.eye(3), atol=1e-8)
    assert np.allclose(m["cov"], m["cov"].T)
    m2 = S.learn_ndim_norm(X, features_bg=rng.normal(size=(50, 3)))
    assert "bg_mean" in m2 and m2["bg_mean"].shape == (3,)
    assert np.allclose(m2["mean"], m["mean"])                              # 背景は前景の推定を変えない


def test_class_ndim_norm_roundtrip_is_the_mahalanobis_ellipsoid():
    """学習した正規分布の等高線(マハラノビス距離 = thresh)で内外が決まる(定理の門)。"""
    rng = _rng()
    X = rng.normal(size=(600, 2)) * np.array([3.0, 0.5]) + np.array([0.4, 0.6])
    m = S.learn_ndim_norm(X)
    y, x = np.mgrid[-5:5:41j, -5:5:41j]
    fa = x + 0.4
    fb = y * 0.25 + 0.6
    out = S.class_ndim_norm([fa, fb], m, thresh=2.0)
    assert out.shape == fa.shape and out.dtype == bool
    # 第 2 実装: 画素ごとに (f - mu)^T inv (f - mu) を素直に計算
    want = np.zeros(fa.shape, bool)
    cells = [(r, c) for r in range(41) for c in range(41)]
    assert len(cells) > 0
    for r, c in cells:
        d = np.array([fa[r, c], fb[r, c]]) - m["mean"]
        want[r, c] = float(d @ m["inv"] @ d) < 4.0
    assert np.array_equal(out, want)
    assert out[20, 20]                                                     # 平均の画素は必ず内側
    assert not out[0, 0] and not out[-1, -1]
    assert np.array_equal(out, S.class_ndim_norm(np.stack([fa, fb], -1), m, thresh=2.0))   # (H,W,D) と list が同じ
    # 一様な分布の標本の 2σ 内側の割合 ≈ 1 - exp(-2)(カイ二乗 2 自由度)
    inside = S.class_ndim_norm([X[:, 0].reshape(20, 30), X[:, 1].reshape(20, 30)], m, thresh=2.0)
    frac = inside.mean()
    assert abs(frac - (1.0 - np.exp(-2.0))) < 0.05, frac


@pytest.mark.xfail(strict=True, reason="NOTES.md B3: 1 枚の 2-D 特徴画像を渡すと (H,W,D) の unpack で ValueError(regiongrowing_n は受ける)")
def test_class_ndim_norm_accepts_a_single_2d_feature_image():
    m = S.learn_ndim_norm(_rng().normal(size=(50, 1)))
    out = S.class_ndim_norm(np.zeros((4, 4)), m)
    assert out.shape == (4, 4)


# --------------------------------------------------------------------------- #
# 4. class_2dim_unsup                                                          #
# --------------------------------------------------------------------------- #
def _three_clusters():
    rng = _rng()
    H, W = 24, 24
    gt = np.zeros((H, W), int)
    gt[:, 8:16] = 1
    gt[:, 16:] = 2
    centers = np.array([[0.1, 0.1], [0.5, 0.9], [0.9, 0.3]])
    f1 = centers[gt, 0] + rng.normal(0, 0.02, (H, W))
    f2 = centers[gt, 1] + rng.normal(0, 0.02, (H, W))
    return f1, f2, gt


def test_class_2dim_unsup_contract_and_lloyd_fixed_point():
    """返りは Lloyd 反復の不動点: 各画素は**自分のクラスタ平均**に最も近い(停留条件の第 2 実装)。"""
    f1, f2, _gt = _three_clusters()
    lab = S.class_2dim_unsup(f1, f2, n_clusters=3)
    assert lab.shape == (24, 24) and np.issubdtype(lab.dtype, np.integer)
    assert int(lab.min()) >= 0 and int(lab.max()) <= 2
    assert len(np.unique(lab)) == 3
    X = np.column_stack([f1.ravel(), f2.ravel()])
    C = np.array([X[lab.ravel() == k].mean(0) for k in range(3)])
    d = ((X[:, None, :] - C[None, :, :]) ** 2).sum(2)
    assert np.array_equal(d.argmin(1), lab.ravel())
    assert np.array_equal(lab, S.class_2dim_unsup(f1, f2, n_clusters=3))   # 決定的(seed 固定)


def test_class_2dim_unsup_two_far_clusters():
    rng = _rng()
    gt = np.zeros((16, 16), int)
    gt[:, 8:] = 1
    f1 = np.where(gt == 1, 0.9, 0.1) + rng.normal(0, 0.02, (16, 16))
    f2 = np.where(gt == 1, 0.2, 0.8) + rng.normal(0, 0.02, (16, 16))
    lab = S.class_2dim_unsup(f1, f2, n_clusters=2)
    assert _same_partition(lab, gt)


@pytest.mark.xfail(strict=True, reason="NOTES.md B5: 初期中心を一様に引く(k-means++ 無し・再試行無し)ので、よく離れた 3 クラスタでも 1 つを割り 2 つを併せる局所解に落ちる")
def test_class_2dim_unsup_recovers_well_separated_clusters():
    f1, f2, gt = _three_clusters()
    lab = S.class_2dim_unsup(f1, f2, n_clusters=3)
    assert _same_partition(lab, gt)


def test_class_2dim_unsup_single_cluster_is_all_zero():
    f = np.full((5, 5), 0.3)
    lab = S.class_2dim_unsup(f, f, n_clusters=1)
    assert lab.shape == (5, 5) and not lab.any()


@pytest.mark.xfail(strict=True, reason="NOTES.md B4: n_clusters > 画素数で rng.choice の ValueError(理由の無い例外)")
def test_class_2dim_unsup_more_clusters_than_pixels_is_a_reasoned_error():
    with pytest.raises(ValueError, match="n_clusters"):
        S.class_2dim_unsup(np.zeros((2, 2)), np.zeros((2, 2)), n_clusters=5)


# --------------------------------------------------------------------------- #
# 5. classify_image_class_lut                                                  #
# --------------------------------------------------------------------------- #
def test_classify_image_class_lut_brute_force():
    rng = _rng()
    im = rng.random((9, 11))
    lut = np.array([0, 0, 1, 1, 2, 3, 3, 3])
    out = S.classify_image_class_lut(im, lut)
    assert out.shape == im.shape and np.issubdtype(out.dtype, np.integer)
    cells = [(r, c) for r in range(9) for c in range(11)]
    assert len(cells) > 0
    for r, c in cells:
        idx = int(np.clip(round(im[r, c] * 7), 0, 7))
        assert out[r, c] == lut[idx], (r, c)
    assert np.array_equal(out, S.classify_image_class_lut(im, lut))


def test_classify_image_class_lut_clips_out_of_range_values():
    lut = [5, 6, 7]
    out = S.classify_image_class_lut(np.array([[-1.0, 0.0, 0.5, 1.0, 2.0]]), lut)
    assert out.tolist() == [[5, 5, 6, 7, 7]]


# --------------------------------------------------------------------------- #
# 6. expand_gray                                                               #
# --------------------------------------------------------------------------- #
def test_expand_gray_equals_the_connected_component_of_the_candidate_set():
    """反復膨張の不動点 = 「候補(|im - ref| < tol)∪ 種」の中で種に触れる 4 連結成分(定理)。"""
    rng = _rng()
    im = rng.random((30, 40))
    im[10:20, 10:30] = 0.5 + rng.normal(0, 0.01, (10, 20))          # 平坦な島
    im[14:16, 20:22] = 0.9                                            # 島の中の穴(候補外)
    seed = np.zeros((30, 40), bool)
    seed[12:14, 12:14] = True
    out = S.expand_gray(im, seed, tol=0.05)
    assert out.shape == im.shape and out.dtype == bool
    ref = im[seed].mean()
    cand = (np.abs(im - ref) < 0.05) | seed
    lab, n = ndimage.label(cand)                                      # 既定 = 4 連結(膨張の十字と同じ)
    assert n >= 1
    keep = np.unique(lab[seed])
    assert len(keep) > 0
    want = np.isin(lab, keep) & (lab > 0)
    assert np.array_equal(out, want)
    assert out[seed].all()                                            # 種は必ず残る
    assert not out[14:16, 20:22].any()                                # 穴は入らない
    assert np.array_equal(out, S.expand_gray(im, seed, tol=0.05))


def test_expand_gray_compares_with_the_seed_mean_not_the_neighbour():
    """★記録: 参照は**種の平均**(HALCON expand_gray_ref の形)。隣接画素との差ではない。"""
    im = np.tile(np.linspace(0.0, 0.4, 11), (3, 1))                   # 隣との差 0.04、端と端で 0.4
    seed = np.zeros((3, 11), bool)
    seed[:, 0] = True
    out = S.expand_gray(im, seed, tol=0.05)
    assert out[:, :2].all() and not out[:, 2:].any(), "隣接比較なら全列に広がるはず"


def test_expand_gray_empty_seed_stays_empty():
    assert not S.expand_gray(np.zeros((4, 4)), np.zeros((4, 4), bool)).any()


# --------------------------------------------------------------------------- #
# 7. regiongrowing_n                                                           #
# --------------------------------------------------------------------------- #
def test_regiongrowing_n_on_piecewise_constant_features_is_connected_components():
    """段差 > tol の階段状画像では、領域 = 同じ値の 4 連結成分(番号の付け替えに不変)。"""
    f1 = np.zeros((20, 20))
    f1[0:10, 0:10] = 0.2
    f1[10:20, 10:20] = 0.2                                            # 同じ値だが角で接するだけ(4 連結では別)
    f1[0:10, 10:20] = 0.6
    f2 = np.zeros((20, 20))
    f2[5:8, 5:8] = 0.9                                                # f1 と同じ値の中に f2 だけ違う島
    lab = S.regiongrowing_n([f1, f2], tol=0.05)
    assert lab.shape == (20, 20) and np.issubdtype(lab.dtype, np.integer)
    assert int(lab.min()) == 1 and int(lab.max()) == len(np.unique(lab))   # 1..n で歯抜け無し
    # 第 2 実装: 値の組ごとに連結成分ラベリング
    key = (np.round(f1 * 100).astype(int) * 1000 + np.round(f2 * 100).astype(int))
    want = np.zeros((20, 20), int)
    nxt = 0
    vals = np.unique(key)
    assert len(vals) > 0
    for v in vals:
        cc, n = ndimage.label(key == v)
        want[cc > 0] = cc[cc > 0] + nxt
        nxt += n
    assert _same_partition(lab, want)
    assert len(np.unique(lab)) == 5                                   # 0.2 ×2(角接触)、0.6、島、残りの 0
    assert np.array_equal(lab, S.regiongrowing_n([f1, f2], tol=0.05))


def test_regiongrowing_n_compares_with_the_seed_pixel_not_the_neighbour():
    """★記録: 判定は**走査で最初に当たった種画素との差**(HALCON は隣接画素どうしの差)。"""
    im = np.tile(np.linspace(0.0, 0.4, 11), (2, 1))                   # 隣との差 0.04 < tol、端と端で 0.4
    lab = S.regiongrowing_n(im, tol=0.05)
    assert len(np.unique(lab)) == 6, "隣接比較なら 1 領域になるはず(2 列ずつ 6 領域が実測)"


def test_regiongrowing_n_accepts_a_single_2d_image_and_hwd():
    im = np.zeros((6, 6))
    im[:, 3:] = 1.0
    a = S.regiongrowing_n(im)
    b = S.regiongrowing_n(im[..., None])
    c = S.regiongrowing_n([im])
    assert np.array_equal(a, b) and np.array_equal(a, c)
    assert len(np.unique(a)) == 2


@pytest.mark.xfail(strict=True, reason="NOTES.md B1: min_size は受け取るが一度も使われない(HALCON は min_size 未満の領域を捨てる)")
def test_regiongrowing_n_min_size_drops_small_regions():
    im = np.zeros((8, 8))
    im[3, 3] = 1.0                                                    # 1 画素の島
    lab = S.regiongrowing_n(im, tol=0.05, min_size=2)
    assert lab[3, 3] == 0, "min_size=2 なら 1 画素の島は捨てられるはず"


# --------------------------------------------------------------------------- #
# 8. watersheds_marker                                                         #
# --------------------------------------------------------------------------- #
def test_watersheds_marker_splits_at_the_ridge():
    """尾根(高い列)の左右にマーカーを置くと、尾根で割れる(定理)。"""
    y, x = np.mgrid[0:16, 0:31]
    im = -np.abs(x - 15).astype(float)                                 # 列 15 が尾根(最大)、両側が谷
    mk = np.zeros((16, 31), int)
    mk[8, 3] = 1
    mk[8, 27] = 2
    lab = S.watersheds_marker(im, mk)
    assert lab.shape == im.shape and np.issubdtype(lab.dtype, np.integer)
    assert set(np.unique(lab).tolist()) == {1, 2}
    assert (lab[:, :15] == 1).all() and (lab[:, 16:] == 2).all()
    assert np.array_equal(lab, S.watersheds_marker(im, mk))


def test_watersheds_marker_matches_a_priority_flood_second_implementation():
    """画素値がすべて異なる画像では、優先度つき洪水の自前実装と**画素単位で一致**する。"""
    pytest.importorskip("skimage")
    rng = _rng()
    base = ndimage.gaussian_filter(rng.random((24, 28)), 2.0)
    im = base + rng.permutation(24 * 28).reshape(24, 28) * 1e-9        # 同値を無くす
    assert len(np.unique(im)) == im.size
    mk = np.zeros((24, 28), int)
    for k, (r, c) in enumerate(((3, 4), (20, 24), (12, 14), (2, 25)), start=1):
        mk[r, c] = k
    lab = S.watersheds_marker(im, mk)
    want = _priority_flood(im, mk)
    assert (lab > 0).all()                                            # 全画素がどれかの盆地
    assert set(np.unique(lab).tolist()) == {1, 2, 3, 4}
    assert np.array_equal(lab, want)


def test_watersheds_marker_keeps_marker_labels_and_fallback_is_nearest_marker():
    """marker の番号は保存される。skimage 不在時の代替(最近傍)の形も固定しておく。"""
    rng = _rng()
    im = rng.random((10, 10))
    mk = np.zeros((10, 10), int)
    mk[1, 1] = 7
    mk[8, 8] = 3
    lab = S.watersheds_marker(im, mk)
    assert lab[1, 1] == 7 and lab[8, 8] == 3 and set(np.unique(lab).tolist()) == {3, 7}
    # 代替経路(距離変換の最近傍)を直接なぞる: 各画素は近いマーカーの番号
    idx = ndimage.distance_transform_edt(mk == 0, return_distances=False, return_indices=True)
    near = mk[tuple(idx)]
    assert near[0, 0] == 7 and near[9, 9] == 3 and (near > 0).all()


# --------------------------------------------------------------------------- #
# 9. 契約の横断(9 本すべて)                                                    #
# --------------------------------------------------------------------------- #
def _calls():
    rng = _rng()
    im = rng.random((12, 12))
    im2 = rng.random((12, 12))
    seed = np.zeros((12, 12), bool)
    seed[4:6, 4:6] = True
    mk = np.zeros((12, 12), int)
    mk[1, 1] = 1
    mk[10, 10] = 2
    model = S.learn_ndim_norm(rng.normal(size=(40, 2)))
    return [
        ("check_difference", (im, im2), {}),
        ("class_2dim_sup", (im, im2, seed), {}),
        ("learn_ndim_norm", (rng.normal(size=(40, 2)),), {}),
        ("class_ndim_norm", ([im, im2], model), {}),
        ("class_2dim_unsup", (im, im2), {"n_clusters": 3}),
        ("classify_image_class_lut", (im, [0, 1, 2]), {}),
        ("expand_gray", (im, seed), {}),
        ("regiongrowing_n", ([im, im2],), {"tol": 0.3}),
        ("watersheds_marker", (im, mk), {}),
    ]


@pytest.mark.parametrize("name,args,kw", _calls(), ids=[c[0] for c in _calls()])
def test_every_op_is_finite_deterministic_and_does_not_touch_its_inputs(name, args, kw):
    fn = getattr(S, name)
    snap = [np.array(a, copy=True) if isinstance(a, np.ndarray) else a for a in args]
    out1 = fn(*args, **kw)
    out2 = fn(*args, **kw)
    if isinstance(out1, dict):
        assert set(out1) == set(out2)
        assert len(out1) > 0                               # 空の dict なら下のループは何も確かめない
        for k in out1:
            assert np.isfinite(out1[k]).all() and np.array_equal(out1[k], out2[k]), k
    else:
        out1 = np.asarray(out1)
        assert out1.shape == (12, 12), out1.shape
        assert out1.dtype == bool or np.issubdtype(out1.dtype, np.integer)
        assert np.array_equal(out1, np.asarray(out2))
    for a, s in zip(args, snap):
        if isinstance(a, np.ndarray):
            assert np.array_equal(a, s), "%s が入力を書き換えた" % name


def test_module_exports_exactly_the_nine_halcon_operators():
    assert tuple(S.__all__) == OPS9
    for name in OPS9:
        assert callable(getattr(S, name)), name
    for name in OPS9:
        doc = getattr(S, name).__doc__ or ""
        assert doc.strip(), name
        assert "](" not in doc and "{{" not in doc and "{%" not in doc, name


# --------------------------------------------------------------------------- #
# 10. 台帳と公開経路                                                           #
# --------------------------------------------------------------------------- #
def test_the_ledger_lists_every_op_and_nothing_is_missing():
    import opssegmentation

    assert opssegmentation.missing() == []
    # ★2026-10-02: 同じ台帳に score(segeval)/world(segworld)のカテゴリが足された。HALCON の 9 本は
    #   4 カテゴリの中にちょうど 9 本、他のカテゴリの op は segmentation.py の物ではない。
    halcon_cats = ["compare", "classify", "grow", "watershed"]
    in_halcon = {n for c in halcon_cats for n in opssegmentation.list_ops(c)}
    assert in_halcon == set(S.__all__) == set(OPS9)
    assert len(opssegmentation.OPSSEGMENTATION) >= 9
    assert opssegmentation.categories()[:4] == halcon_cats
    rows = [(n, m) for n, m in opssegmentation.OPSSEGMENTATION.items() if n in in_halcon]
    assert len(rows) == 9
    for name, m in rows:
        assert m["func"] is getattr(S, name)
        assert m["doc"], name


def test_every_op_is_reachable_from_the_public_tier():
    """``fullseye.ledger.<名前>`` から呼べること(登録面を 1 つ落とすと静かに消える)。"""
    import fullseye as fs
    import opssegmentation

    for name in opssegmentation.OPSSEGMENTATION:
        assert hasattr(fs.ledger, name), name
    mk = np.zeros((6, 6), int)
    mk[0, 0] = 1
    mk[5, 5] = 2
    lab = fs.ledger.watersheds_marker(np.arange(36, dtype=float).reshape(6, 6), mk)
    assert set(np.unique(np.asarray(lab)).tolist()) == {1, 2}


def test_the_typed_catalog_declares_the_family():
    import typed_catalog as tc

    rows = [r for r in tc.catalog() if r[1] == "segmentation" and r[0] in OPS9]
    assert {r[0] for r in rows} == set(OPS9)
    assert {r[3] for r in rows} == {"mask", "labels2d", "table"}
    ins = {t for r in rows for t in r[2]}
    assert ins == {"image2d", "images", "mask", "labels2d", "matrix", "table", "signal"}


def test_the_fuzzer_can_seed_every_declared_input_and_has_builders():
    """種と述語が無い型を要る op は**永久に走らない**。9 本すべてに専用の種(builder)がある。"""
    sys.path.insert(0, str(ROOT / "tools"))
    import chain_fuzz as cf

    gens = cf.make_generators()
    for sort in ("image2d", "images", "mask", "labels2d", "matrix", "table", "signal"):
        assert sort in gens and sort in cf.TYPE_CHECKS, sort
        assert cf.TYPE_CHECKS[sort](gens[sort](np.random.default_rng(0))), sort
    for name in OPS9:
        assert name in cf.OP_ARG_BUILDERS, name
    # builder の出力で op が実際に走り、宣言 out 型の述語を通る
    import opssegmentation
    rng = np.random.default_rng(1)
    pool = {}
    for name in OPS9:
        args, kw = cf.OP_ARG_BUILDERS[name](pool, rng)
        out = opssegmentation.call(name, *args, **kw)
        want = opssegmentation.info(name)["out"]
        assert cf.TYPE_CHECKS[want](out), (name, want, type(out))


def test_no_typed_bridge_is_built_for_this_family():
    """単入力は learn_ndim_norm(matrix → table)と regiongrowing_n(images → labels2d)だけで、
    どちらも out / in が ``TYPE_TO_SORT`` に無い → tb_* の橋は架からない(2-D の件数は動かない)。"""
    import ops

    names = {o.name for o in ops.REGISTRY}
    for name in OPS9:
        assert "tb_" + name not in names, name
        assert name not in names, name                               # 2-D レジストリと同名衝突も無い
