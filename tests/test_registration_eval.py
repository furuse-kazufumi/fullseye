"""registration_eval の GT 検証: 既知変換・既知誤差・スケール相対・fail-closed。

すべて独立 GT(閉形式/既知値)で検証する。実装の再導出はしない:
- inlier_ratio/rmse は「点ごとに既知ノルムのオフセット」を与え、GT 変換下の残差が
  そのオフセットノルムそのものになる性質(res_i = ‖gt·s − (gt·s + off_i)‖ = ‖off_i‖)で判定。
- registration_recall は並進誤差 δ を入れると RMSE=‖δ‖ になる閉形式で判定。
- rotation_translation_error は「軸まわり角 θ の回転差の測地角は θ」で判定。
"""
import numpy as np
import pytest
from scipy.spatial.transform import Rotation

import registration_eval as re


# ─────────────────────────────────────────────────────────────────────────
# ヘルパ(独立 GT の生成)
# ─────────────────────────────────────────────────────────────────────────
def _rot(axis, deg):
    """軸 axis まわり deg 度の回転行列(scipy = 独立実装)。"""
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    return Rotation.from_rotvec(np.deg2rad(deg) * a).as_matrix()


def _cloud(n=40, scale=1.0, seed=0):
    """スケール scale の一様点群 (n,3)。"""
    rng = np.random.default_rng(seed)
    return rng.uniform(-scale, scale, size=(n, 3))


def _gt():
    """代表的な GT 変換(回転+並進)。"""
    return re.make_transform(_rot([0.3, -0.7, 0.5], 37.0), [1.2, -0.4, 2.0])


# ─────────────────────────────────────────────────────────────────────────
# rotation_translation_error: 軸まわり θ / 並進ノルム(独立 GT)
# ─────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("theta", [0.5, 30.0, 90.0, 179.0])
def test_rre_equals_axis_angle(theta):
    gt = re.make_transform(np.eye(3), [0, 0, 0])
    est = re.make_transform(_rot([1, 2, 3], theta), [0, 0, 0])
    rre, rte = re.rotation_translation_error(gt, est)
    assert rre == pytest.approx(theta, abs=1e-6)
    assert rte == pytest.approx(0.0, abs=1e-9)


def test_rte_equals_translation_norm():
    R = _rot([0, 0, 1], 20.0)  # 同一回転なら RRE=0、RTE は並進差のみ
    delta = np.array([3.0, -4.0, 12.0])  # ‖δ‖ = 13
    gt = re.make_transform(R, [1.0, 1.0, 1.0])
    est = re.make_transform(R, np.array([1.0, 1.0, 1.0]) + delta)
    rre, rte = re.rotation_translation_error(gt, est)
    # arccos((tr-1)/2) は θ≈0 で条件数 ~1/θ(mantissa 半分喪失)→ 系統的に ~1e-6 deg 残る
    assert rre == pytest.approx(0.0, abs=1e-4)
    assert rte == pytest.approx(13.0, abs=1e-9)


def test_error_zero_when_identical():
    T = _gt()
    rre, rte = re.rotation_translation_error(T, T)
    assert rre == pytest.approx(0.0, abs=1e-4)  # θ≈0 の arccos 条件数(上記)
    assert rte == pytest.approx(0.0, abs=1e-12)


def test_rre_is_symmetric():
    a = re.make_transform(_rot([1, 0, 0], 40.0), [0, 0, 0])
    b = re.make_transform(_rot([1, 0, 0], 10.0), [0, 0, 0])
    r1, _ = re.rotation_translation_error(a, b)
    r2, _ = re.rotation_translation_error(b, a)
    assert r1 == pytest.approx(30.0, abs=1e-6)
    assert r1 == pytest.approx(r2, abs=1e-9)


# ─────────────────────────────────────────────────────────────────────────
# inlier_ratio: 既知オフセットノルムでの閉形式値 + thresh 単調性
# ─────────────────────────────────────────────────────────────────────────
def _offset_pair(scale=1.0, seed=1):
    """gt(source) に既知ノルムのオフセットを足した target を作る。

    res_i(transform=gt)= ‖gt·s − (gt·s + off_i)‖ = ‖off_i‖ = 既知。
    オフセットノルム = scale * [0.1,0.2,0.3,0.4,0.5]。
    """
    gt = _gt()
    S = _cloud(5, scale=scale, seed=seed)
    S_gt = re.transform_points(gt, S)
    rng = np.random.default_rng(seed + 100)
    dirs = rng.normal(size=(5, 3))
    dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    norms = scale * np.array([0.1, 0.2, 0.3, 0.4, 0.5])
    target = S_gt + dirs * norms[:, None]
    return S, target, gt, norms


def test_inlier_ratio_closed_form():
    S, target, gt, norms = _offset_pair(scale=1.0)
    # thresh=0.25 → norms<0.25 は {0.1,0.2} = 2/5
    assert re.inlier_ratio(S, target, gt, 0.25) == pytest.approx(0.4)
    # thresh=0.35 → {0.1,0.2,0.3} = 3/5
    assert re.inlier_ratio(S, target, gt, 0.35) == pytest.approx(0.6)
    # thresh=1.0 → 全部
    assert re.inlier_ratio(S, target, gt, 1.0) == pytest.approx(1.0)
    # thresh=0.05 → なし
    assert re.inlier_ratio(S, target, gt, 0.05) == pytest.approx(0.0)


def test_inlier_ratio_monotonic_in_thresh():
    S, target, gt, _ = _offset_pair()
    taus = np.linspace(0.02, 1.5, 25)
    vals = [re.inlier_ratio(S, target, gt, t) for t in taus]
    assert all(b >= a - 1e-12 for a, b in zip(vals, vals[1:]))  # 非減少


def test_inlier_ratio_one_when_est_equals_gt():
    gt = _gt()
    S = _cloud(30)
    target = re.transform_points(gt, S)  # 完全対応
    assert re.inlier_ratio(S, target, gt, 1e-6) == pytest.approx(1.0)


def test_inlier_ratio_scale_relative():
    """スケール ×1000・thresh ×1000 で inlier 率は不変(絶対 epsilon 依存でない)。"""
    for scale in (1.0, 1000.0):
        S, target, gt, _ = _offset_pair(scale=scale)
        assert re.inlier_ratio(S, target, gt, 0.35 * scale) == pytest.approx(0.6)


def test_inlier_ratio_uses_index_correspondence_not_nn():
    """判別ケース: target の並びを崩すと index 対応が壊れ inlier 率が変わる。

    NN ベース実装なら不変になってしまうため、index 対応であることを保証。
    """
    S, target, gt, _ = _offset_pair()
    perm = np.array([4, 3, 2, 1, 0])  # 非自明な並べ替え
    base = re.inlier_ratio(S, target, gt, 0.35)
    permuted = re.inlier_ratio(S, target[perm], gt, 0.35)
    assert base == pytest.approx(0.6)
    assert permuted != pytest.approx(base)  # 対応が壊れて変化


# ─────────────────────────────────────────────────────────────────────────
# rmse_inliers: inlier ノルムの二乗平均平方根(独立計算)+ 縮退
# ─────────────────────────────────────────────────────────────────────────
def test_rmse_inliers_closed_form():
    S, target, gt, norms = _offset_pair(scale=1.0)
    # thresh=0.35 → inliers {0.1,0.2,0.3}; rmse = sqrt((0.01+0.04+0.09)/3)
    rmse, n = re.rmse_inliers(S, target, gt, 0.35)
    expected = np.sqrt((0.1**2 + 0.2**2 + 0.3**2) / 3.0)
    assert n == 3
    assert rmse == pytest.approx(expected, rel=1e-9)


def test_rmse_inliers_zero_when_est_equals_gt():
    gt = _gt()
    S = _cloud(30)
    target = re.transform_points(gt, S)
    rmse, n = re.rmse_inliers(S, target, gt, 1e-6)
    assert n == 30
    assert rmse == pytest.approx(0.0, abs=1e-9)


def test_rmse_inliers_scale_relative():
    """RMSE はスケールに比例(×1000)。inlier 集合は thresh を合わせれば同一。"""
    _, _, _, _ = _offset_pair()
    r1, n1 = re.rmse_inliers(*_offset_pair(scale=1.0)[:3], 0.35)
    r1000, n1000 = re.rmse_inliers(*_offset_pair(scale=1000.0)[:3], 0.35 * 1000.0)
    assert n1 == n1000
    assert r1000 == pytest.approx(r1 * 1000.0, rel=1e-9)


def test_rmse_inliers_no_inlier_is_nan_honest():
    """inlier 0 → RMSE 未定義を nan で返す(捏造しない; fail-mode B)。"""
    S, target, gt, _ = _offset_pair()
    rmse, n = re.rmse_inliers(S, target, gt, 0.01)  # 最小ノルム 0.1 未満
    assert n == 0
    assert np.isnan(rmse)


# ─────────────────────────────────────────────────────────────────────────
# registration_recall: est=gt→1 / 並進誤差 δ で RMSE=‖δ‖ / NN 対応 / 縮退
# ─────────────────────────────────────────────────────────────────────────
def test_recall_one_when_est_equals_gt():
    gt = _gt()
    S = _cloud(50)
    target = re.transform_points(gt, S)
    assert re.registration_recall(S, target, gt, gt, thresh=0.05) == 1.0


def test_recall_threshold_on_known_translation_error():
    """est を並進 δ だけずらすと RMSE=‖δ‖。thresh をまたいで 1↔0 が切り替わる。"""
    gt = _gt()
    S = _cloud(50)
    target = re.transform_points(gt, S)
    # δ=0.3 の並進誤差 → 全点で est·s − gt·s = δ → RMSE=0.3(独立 GT)
    est = gt.copy()
    est[:3, 3] += np.array([0.3, 0.0, 0.0])
    assert re.registration_recall(S, target, gt, est, thresh=0.5) == 1.0   # 0.3<0.5
    assert re.registration_recall(S, target, gt, est, thresh=0.2) == 0.0   # 0.3>0.2


def test_recall_independent_of_target_ordering():
    """判別ケース: 対応は GT から張る → target の並べ替えに不変。"""
    gt = _gt()
    S = _cloud(50)
    target = re.transform_points(gt, S)
    rng = np.random.default_rng(7)
    perm = rng.permutation(len(target))
    r_ordered = re.registration_recall(S, target, gt, gt, thresh=0.05)
    r_perm = re.registration_recall(S, target[perm], gt, gt, thresh=0.05)
    assert r_ordered == 1.0 and r_perm == 1.0


def test_recall_scale_relative():
    gt_s = _gt()
    for scale in (1.0, 1000.0):
        S = _cloud(50, scale=scale)
        target = re.transform_points(gt_s, S)
        est = gt_s.copy()
        est[:3, 3] += np.array([0.3 * scale, 0.0, 0.0])
        assert re.registration_recall(S, target, gt_s, est, thresh=0.5 * scale) == 1.0
        assert re.registration_recall(S, target, gt_s, est, thresh=0.2 * scale) == 0.0


def test_recall_no_overlap_is_nan_honest():
    """GT 重なりが無い(対応 0)→ 成否は未定義 nan(fail-mode B)。"""
    S = _cloud(30, seed=1)
    target = _cloud(30, seed=2) + 1e6  # 遥か遠方 → gt=I で近傍なし
    gt = re.make_transform(np.eye(3), [0, 0, 0])
    assert np.isnan(re.registration_recall(S, target, gt, gt, thresh=0.05))


# ─────────────────────────────────────────────────────────────────────────
# fail-closed(形状不正・非正 thresh・非有限)
# ─────────────────────────────────────────────────────────────────────────
def test_failclosed_mismatched_correspondence_count():
    gt = _gt()
    S = _cloud(5)
    target = _cloud(4)
    with pytest.raises(ValueError):
        re.inlier_ratio(S, target, gt, 0.1)
    with pytest.raises(ValueError):
        re.rmse_inliers(S, target, gt, 0.1)


def test_failclosed_bad_point_shape():
    gt = _gt()
    bad = np.zeros((5, 2))  # (N,2)
    good = _cloud(5)
    with pytest.raises(ValueError):
        re.inlier_ratio(bad, bad, gt, 0.1)
    with pytest.raises(ValueError):
        re.transform_points(gt, bad)
    with pytest.raises(ValueError):
        re.inlier_ratio(np.zeros((0, 3)), good, gt, 0.1)  # 空


def test_failclosed_bad_transform_shape():
    S = _cloud(5)
    target = _cloud(5)
    bad = np.eye(3)  # 3×3 は不可
    with pytest.raises(ValueError):
        re.inlier_ratio(S, target, bad, 0.1)
    with pytest.raises(ValueError):
        re.rotation_translation_error(bad, np.eye(4))


def test_failclosed_nonpositive_thresh():
    gt = _gt()
    S = _cloud(5)
    target = re.transform_points(gt, S)
    for bad in (0.0, -1.0):
        with pytest.raises(ValueError):
            re.inlier_ratio(S, target, gt, bad)
        with pytest.raises(ValueError):
            re.registration_recall(S, target, gt, gt, bad)


def test_failclosed_nonfinite():
    gt = _gt()
    S = _cloud(5)
    target = re.transform_points(gt, S)
    S_bad = S.copy()
    S_bad[0, 0] = np.nan
    with pytest.raises(ValueError):
        re.inlier_ratio(S_bad, target, gt, 0.1)
    T_bad = gt.copy()
    T_bad[0, 0] = np.inf
    with pytest.raises(ValueError):
        re.rotation_translation_error(T_bad, gt)


def test_make_and_transform_roundtrip():
    R = _rot([1, 1, 0], 25.0)
    t = np.array([2.0, -3.0, 1.5])
    T = re.make_transform(R, t)
    assert T.shape == (4, 4)
    P = _cloud(10)
    got = re.transform_points(T, P)
    expected = P @ R.T + t  # 独立計算
    assert np.allclose(got, expected)


def test_validators_reject_non_numeric_inputs():
    """Regression (chain fuzz wave-4): rotation_translation_error に dict が来ると
    _as_transform 内の np.asarray が形状チェックの前に生 TypeError 化していた。
    検証層(_as_transform/_as_points/_check_thresh)で明示 ValueError に変える。"""
    bad = {"rmse": 1.0, "iters": 3}
    with pytest.raises(ValueError, match="4x4"):
        re.rotation_translation_error(bad, np.eye(4))
    with pytest.raises(ValueError, match="4x4"):
        re.rotation_translation_error(np.eye(4), bad)
    S = _cloud(5)
    with pytest.raises(ValueError, match="point cloud"):
        re.inlier_ratio(bad, S, np.eye(4), 0.1)          # points に dict
    with pytest.raises(ValueError, match="thresh"):
        re.inlier_ratio(S, S, np.eye(4), bad)            # thresh に dict
    with pytest.raises(ValueError, match="numeric"):
        re.make_transform(bad, np.zeros(3))              # 兄弟 util も同穴を一掃
