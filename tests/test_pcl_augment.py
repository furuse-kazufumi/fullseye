"""Ground-truth correctness for pcl_augment (3D point-cloud augmentation).

すべて閉形式/既知不変量に対する数値検証で、実装の再導出ではない(note_15 Class C):
    - random_rotation: RᵀR=I・det=+1、距離保存(等長)、Rᵀ逆変換で厳密復元。
    - random_scale: bbox 対角長がちょうど s 倍・全ペア距離が s 倍。
    - random_dropout: kept 数 = round((1-ratio)N)・kept==points[idx]・idx 昇順一意。
    - jitter: 大 N でノイズ平均≈0・標準偏差≈sigma、clip で変位が上限内。
    - elastic_deform: RMS 変位 = alpha(正規化の閉形式)、σ→∞ で定数場(剛体並進)。
    - cutout: 除去点は辺長 extent の軸平行ボックスに収まる(空間局所=dropout と判別)。
    - fail-closed: 縮退/不正入力は ValueError(note_15 Class B、詐称値を返さない)。
    - スケール相対性: 座標スケール 1 と 1000 の両方で性質が成立(note_15 Class A)。
"""
from __future__ import annotations

import numpy as np
import pytest

import pcl_augment as A


# --------------------------------------------------------------------------- #
# fixtures / helpers                                                          #
# --------------------------------------------------------------------------- #
def _cloud(n=500, scale=1.0, seed=12345):
    """テスト用のランダム点群(モジュールの rng とは独立)。"""
    rng = np.random.default_rng(seed)
    return rng.standard_normal((n, 3)) * scale + np.array([2.0, -1.0, 0.5]) * scale


def _pairwise(P):
    d = P[:, None, :] - P[None, :, :]
    return np.sqrt(np.sum(d * d, axis=2))


def _bbox_diag(P):
    return float(np.linalg.norm(P.max(0) - P.min(0)))


def _rot_angle(R):
    return float(np.arccos(np.clip((np.trace(R) - 1.0) / 2.0, -1.0, 1.0)))


# --------------------------------------------------------------------------- #
# random_rotation                                                             #
# --------------------------------------------------------------------------- #
def test_rotation_is_orthonormal_det_plus_one():
    P = _cloud(50)
    for seed in range(6):
        _, R = A.random_rotation(P, seed=seed)
        assert np.allclose(R.T @ R, np.eye(3), atol=1e-12)
        assert np.isclose(np.linalg.det(R), 1.0, atol=1e-12)


def test_rotation_inverse_recovers_exactly():
    P = _cloud(200)
    rotated, R = A.random_rotation(P, seed=7)
    # 逆変換 = Rᵀ を各点に作用 = rotated @ R。
    recovered = rotated @ R
    assert np.allclose(recovered, P, atol=1e-10)


def test_rotation_is_isometry():
    # 独立 GT: 回転は全ペア距離とノルムを保存する。
    P = _cloud(80)
    rotated, _ = A.random_rotation(P, seed=3)
    assert np.allclose(_pairwise(rotated), _pairwise(P), atol=1e-9)


def test_rotation_max_angle_constrains_angle():
    P = _cloud(10)
    for ma in (0.05, 0.2, 0.5, 1.0):
        for seed in range(15):
            _, R = A.random_rotation(P, seed=seed, max_angle=ma)
            assert _rot_angle(R) <= ma + 1e-9
            assert np.allclose(R.T @ R, np.eye(3), atol=1e-12)
            assert np.isclose(np.linalg.det(R), 1.0, atol=1e-12)


def test_rotation_determinism_and_seed_variation():
    P = _cloud(30)
    r0, R0 = A.random_rotation(P, seed=42)
    r0b, R0b = A.random_rotation(P, seed=42)
    r1, R1 = A.random_rotation(P, seed=43)
    assert np.array_equal(r0, r0b) and np.array_equal(R0, R0b)
    assert not np.allclose(R0, R1)


# --------------------------------------------------------------------------- #
# random_scale                                                                #
# --------------------------------------------------------------------------- #
def test_scale_bbox_diagonal_scales_by_s():
    P = _cloud(300)
    d0 = _bbox_diag(P)
    for seed in range(8):
        scaled, s = A.random_scale(P, 0.5, 2.0, seed=seed)
        assert 0.5 <= s <= 2.0
        assert np.isclose(_bbox_diag(scaled), s * d0, rtol=1e-12)


def test_scale_all_pairwise_distances_scale():
    P = _cloud(60)
    scaled, s = A.random_scale(P, 0.8, 1.5, seed=1)
    assert np.allclose(_pairwise(scaled), s * _pairwise(P), rtol=1e-12)


def test_scale_relative_at_two_magnitudes():
    # note_15 Class A: 座標スケールが 1 と 1000 の両方で対角×s が成立。
    for coord_scale in (1.0, 1000.0):
        P = _cloud(200, scale=coord_scale)
        d0 = _bbox_diag(P)
        scaled, s = A.random_scale(P, 0.9, 1.1, seed=5)
        assert np.isclose(_bbox_diag(scaled), s * d0, rtol=1e-12)


# --------------------------------------------------------------------------- #
# random_dropout                                                              #
# --------------------------------------------------------------------------- #
def test_dropout_keeps_exact_count():
    P = _cloud(1000)
    for ratio in (0.0, 0.1, 0.25, 0.3, 0.5, 0.9, 1.0):
        kept, idx = A.random_dropout(P, ratio, seed=2)
        expected = int(round((1.0 - ratio) * 1000))
        assert kept.shape[0] == expected
        assert idx.shape[0] == expected


def test_dropout_index_consistency():
    P = _cloud(400)
    kept, idx = A.random_dropout(P, 0.37, seed=9)
    # kept == points[idx] を厳密に。
    assert np.array_equal(kept, P[idx])
    # idx は昇順・一意・範囲内。
    assert np.all(np.diff(idx) > 0)
    assert idx.min() >= 0 and idx.max() < 400
    assert len(np.unique(idx)) == len(idx)


def test_dropout_determinism_and_seed_variation():
    P = _cloud(300)
    _, i0 = A.random_dropout(P, 0.5, seed=11)
    _, i0b = A.random_dropout(P, 0.5, seed=11)
    _, i1 = A.random_dropout(P, 0.5, seed=12)
    assert np.array_equal(i0, i0b)
    assert not np.array_equal(i0, i1)


# --------------------------------------------------------------------------- #
# jitter                                                                       #
# --------------------------------------------------------------------------- #
def test_jitter_noise_statistics():
    # 大 N: ノイズの平均≈0・標準偏差≈sigma。
    P = np.zeros((20000, 3))
    sigma = 0.037
    out = A.jitter(P, sigma=sigma, seed=4)
    noise = out - P
    assert abs(noise.mean()) < 1e-3
    assert np.isclose(noise.std(), sigma, rtol=0.03)


def test_jitter_clip_bounds_displacement():
    P = _cloud(2000)
    sigma, clip = 1.0, 0.4
    out = A.jitter(P, sigma=sigma, clip=clip, seed=6)
    disp = out - P
    assert np.max(np.abs(disp)) <= clip + 1e-12


def test_jitter_determinism_and_seed_variation():
    P = _cloud(100)
    a0 = A.jitter(P, 0.01, seed=1)
    a0b = A.jitter(P, 0.01, seed=1)
    a1 = A.jitter(P, 0.01, seed=2)
    assert np.array_equal(a0, a0b)
    assert not np.allclose(a0, a1)


def test_jitter_zero_sigma_is_identity():
    P = _cloud(50)
    assert np.array_equal(A.jitter(P, 0.0, seed=0), P)


# --------------------------------------------------------------------------- #
# elastic_deform                                                              #
# --------------------------------------------------------------------------- #
def test_elastic_rms_displacement_equals_alpha():
    # 閉形式: 変位場を RMS=1 に正規化 → alpha 倍なので RMS ノルム = alpha。
    P = _cloud(500)
    for alpha in (0.02, 0.1, 0.5):
        out = A.elastic_deform(P, sigma=0.5, alpha=alpha, seed=3)
        rms = np.sqrt(np.mean(np.sum((out - P) ** 2, axis=1)))
        assert np.isclose(rms, alpha, rtol=1e-9)


def test_elastic_large_sigma_is_rigid_translation():
    # σ≫直径 → 重み≈一様 → 変位場は定数(全点が同一ベクトルで並進)。
    P = _cloud(200, scale=1.0)
    out = A.elastic_deform(P, sigma=1e4, alpha=0.05, seed=8)
    disp = out - P
    # 全点の変位が一致 = 点間の std がほぼ 0。
    assert np.all(disp.std(axis=0) < 1e-3 * 0.05)


def test_elastic_small_sigma_is_incoherent():
    # σ→0 → 各点独立 → 変位場の点間 std は振幅オーダー(定数場と判別)。
    P = _cloud(200)
    out = A.elastic_deform(P, sigma=1e-9, alpha=0.05, seed=8)
    disp = out - P
    assert np.mean(disp.std(axis=0)) > 0.1 * 0.05


def test_elastic_determinism_and_seed_variation():
    P = _cloud(150)
    a0 = A.elastic_deform(P, 0.3, 0.05, seed=1)
    a0b = A.elastic_deform(P, 0.3, 0.05, seed=1)
    a1 = A.elastic_deform(P, 0.3, 0.05, seed=2)
    assert np.array_equal(a0, a0b)
    assert not np.allclose(a0, a1)


# --------------------------------------------------------------------------- #
# cutout                                                                       #
# --------------------------------------------------------------------------- #
def _grid(nside=12, spacing=1.0):
    g = np.arange(nside) * spacing
    X, Y, Z = np.meshgrid(g, g, g, indexing="ij")
    return np.stack([X.ravel(), Y.ravel(), Z.ravel()], axis=1).astype(np.float64)


def test_cutout_removed_points_fit_in_extent_box():
    # 独立 GT: 除去点は必ず辺長 extent の軸平行ボックスに収まる(空間的に局所)。
    P = _grid(12, spacing=1.0)
    extent = 3.0
    kept, idx = A.cutout(P, extent, seed=7)
    removed_mask = np.ones(P.shape[0], bool)
    removed_mask[idx] = False
    removed = P[removed_mask]
    assert removed.shape[0] >= 1                       # 中心点は必ず除去
    span = removed.max(0) - removed.min(0)
    assert np.all(span <= extent + 1e-9)


def test_cutout_partition_complete_and_consistent():
    P = _grid(10)
    kept, idx = A.cutout(P, 2.5, seed=4)
    assert np.array_equal(kept, P[idx])                 # kept==points[idx]
    removed_mask = np.ones(P.shape[0], bool)
    removed_mask[idx] = False
    # kept と removed が互いに素・全体を被覆。
    assert kept.shape[0] + int(removed_mask.sum()) == P.shape[0]
    assert len(np.unique(idx)) == len(idx)


def test_cutout_is_spatially_local_unlike_dropout():
    # cutout の除去は 1 ボックス内に凝集、同数を dropout した場合は散布。
    P = _grid(12, spacing=1.0)
    _, cidx = A.cutout(P, 4.0, seed=2)
    removed_mask = np.ones(P.shape[0], bool)
    removed_mask[cidx] = False
    cut_span = float(np.max(P[removed_mask].max(0) - P[removed_mask].min(0)))
    assert cut_span <= 4.0 + 1e-9
    # 同数をランダム dropout → 除去集合はボックスより遥かに広く散らばる。
    n_removed = int(removed_mask.sum())
    ratio = n_removed / P.shape[0]
    _, kidx = A.random_dropout(P, ratio, seed=2)
    drop_removed = np.ones(P.shape[0], bool)
    drop_removed[kidx] = False
    drop_span = float(np.max(P[drop_removed].max(0) - P[drop_removed].min(0)))
    assert drop_span > cut_span


def test_cutout_scale_relative(at_scales=(1.0, 1000.0)):
    # note_15 Class A: 座標スケール 1 と 1000 の両方で局所性が成立。
    for cs in at_scales:
        P = _grid(12, spacing=cs)
        extent = 3.0 * cs
        _, idx = A.cutout(P, extent, seed=1)
        removed_mask = np.ones(P.shape[0], bool)
        removed_mask[idx] = False
        span = P[removed_mask].max(0) - P[removed_mask].min(0)
        assert np.all(span <= extent + 1e-6 * cs)


def test_cutout_vector_extent():
    P = _grid(12)
    ext = np.array([2.0, 5.0, 3.0])
    _, idx = A.cutout(P, ext, seed=0)
    removed_mask = np.ones(P.shape[0], bool)
    removed_mask[idx] = False
    span = P[removed_mask].max(0) - P[removed_mask].min(0)
    assert np.all(span <= ext + 1e-9)


# --------------------------------------------------------------------------- #
# augment (合成)                                                             #
# --------------------------------------------------------------------------- #
def test_augment_composition_determinism():
    P = _cloud(400)
    cfg = {
        "rotation": {"max_angle": 0.3},
        "scale": {"lo": 0.9, "hi": 1.1},
        "elastic": {"sigma": 0.4, "alpha": 0.02},
        "jitter": {"sigma": 0.01, "clip": 0.05},
        "dropout": {"ratio": 0.1},
        "cutout": {"extent": 0.5},
    }
    o0 = A.augment(P, cfg, seed=5)
    o0b = A.augment(P, cfg, seed=5)
    o1 = A.augment(P, cfg, seed=6)
    assert np.array_equal(o0, o0b)
    assert o0.shape[1] == 3
    # dropout があるので点数は減る。
    assert o0.shape[0] < P.shape[0]
    assert not np.array_equal(o0, o1)


def test_augment_empty_config_is_identity():
    P = _cloud(50)
    assert np.array_equal(A.augment(P, {}, seed=0), P)


def test_augment_rotation_only_preserves_count_and_isometry():
    P = _cloud(120)
    out = A.augment(P, {"rotation": {}}, seed=2)
    assert out.shape == P.shape
    assert np.allclose(_pairwise(out), _pairwise(P), atol=1e-9)


# --------------------------------------------------------------------------- #
# fail-closed (note_15 Class B)                                               #
# --------------------------------------------------------------------------- #
def test_bad_shape_raises():
    with pytest.raises(ValueError):
        A.jitter(np.zeros((10, 2)), 0.1)
    with pytest.raises(ValueError):
        A.random_rotation(np.zeros((5, 4)))
    with pytest.raises(ValueError):
        A.random_scale(np.zeros((3, 3, 3)), 0.5, 1.0)


def test_nonfinite_input_raises():
    P = _cloud(10)
    P[0, 0] = np.nan
    with pytest.raises(ValueError):
        A.jitter(P, 0.1)


def test_invalid_params_raise():
    P = _cloud(20)
    with pytest.raises(ValueError):
        A.random_dropout(P, 1.5)
    with pytest.raises(ValueError):
        A.random_dropout(P, -0.1)
    with pytest.raises(ValueError):
        A.random_scale(P, 0.0, 1.0)          # lo must be > 0
    with pytest.raises(ValueError):
        A.random_scale(P, 1.0, 0.5)          # hi < lo
    with pytest.raises(ValueError):
        A.cutout(P, 0.0)                     # extent must be > 0
    with pytest.raises(ValueError):
        A.cutout(P, np.array([1.0, 2.0]))    # wrong extent shape
    with pytest.raises(ValueError):
        A.jitter(P, -1.0)                    # sigma < 0
    with pytest.raises(ValueError):
        A.jitter(P, 0.1, clip=0.0)           # clip <= 0
    with pytest.raises(ValueError):
        A.elastic_deform(P, -0.1, 0.05)      # sigma < 0
    with pytest.raises(ValueError):
        A.augment(P, {"bogus": {}})          # unknown stage


def test_single_point_promotion():
    out = A.jitter([1.0, 2.0, 3.0], 0.0)
    assert out.shape == (1, 3)
