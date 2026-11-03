# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""featmatch の門 —— 真値は合成に使った既知のホモグラフィ / 既知のカメラ、既存 op、OpenCV。

The answers come from the transform used to synthesise the pair (the estimator never sees it),
from an existing operator (``features.match_descriptors``) and, when installed, from OpenCV.
"""
import math

import numpy as np
import pytest
from scipy import ndimage

import featmatch as fm
import features
import opsmatchreg


@pytest.fixture(scope="module")
def scene():
    return fm.synthetic_scene((256, 256), seed=3)


@pytest.fixture(scope="module")
def sift_ref(scene):
    return fm.features_sift(scene)


def _corr_inliers_agree(m, H, tol=1.0):
    err = np.linalg.norm(fm._apply_h(H, m["pts1"]) - m["pts2"], axis=1)
    return err < tol


# ---- SIFT ----------------------------------------------------------------------------------

def test_sift_rot90_recovers_the_exact_permutation(scene, sift_ref):
    """90 度回転は画素の並べ替え(補間なし)。推定した H の 4 隅誤差 < 0.5 px、内れ値はほぼ全部が真の H で 1 px 以内。"""
    img2 = np.rot90(scene).copy()                      # 反時計回り: (x, y) -> (y, W-1-x)
    w = scene.shape[1]
    Ht = np.array([[0.0, 1.0, 0.0], [-1.0, 0.0, w - 1.0], [0.0, 0.0, 1.0]])
    f2 = fm.features_sift(img2)
    m = fm.features_match(sift_ref, f2)
    h = fm.ransac_homography(m)
    assert fm.corner_error(h["H"], Ht, scene.shape) < 0.5
    ok = _corr_inliers_agree(m, Ht)
    assert ok[h["inliers"]].mean() > 0.97
    assert h["n_inliers"] >= 60
    # 符号つき: 真の H[1,2] = +255 を推定も正で持つ(x と y を取り違えると負になる)
    assert h["H"][1, 2] > 250


def test_sift_half_scale_by_block_mean(scene, sift_ref):
    """2x2 の平均で半分に縮める(画素 i の中心は元の 2i+0.5 → x' = (x - 0.5)/2)。4 隅誤差 < 1.5 px。"""
    small = scene.reshape(128, 2, 128, 2).mean((1, 3))
    Ht = np.array([[0.5, 0, -0.25], [0, 0.5, -0.25], [0, 0, 1.0]])
    m = fm.features_match(sift_ref, fm.features_sift(small))
    h = fm.ransac_homography(m)
    assert fm.corner_error(h["H"], Ht, scene.shape) < 1.5


def test_sift_scale_values_follow_the_zoom(scene, sift_ref):
    """内れ値の組で、2 枚目の σ / 1 枚目の σ の中央値が拡大率 0.5 に近い(スケール不変の根拠)。"""
    small = scene.reshape(128, 2, 128, 2).mean((1, 3))
    f2 = fm.features_sift(small)
    m = fm.features_match(sift_ref, f2)
    h = fm.ransac_homography(m)
    i = m["idx"][h["inliers"]]
    ratio = np.median(f2["scale"][i[:, 1]] / sift_ref["scale"][i[:, 0]])
    assert 0.4 < ratio < 0.6


def test_sift_against_opencv(scene, sift_ref):
    """同じ対(回転 30 度・0.7 倍)で OpenCV の SIFT と点数・ホモグラフィの誤差が同じ桁。"""
    cv2 = pytest.importorskip("cv2")
    if not hasattr(cv2, "SIFT_create"):
        pytest.skip("cv2 without SIFT")
    Ht = fm.condition_homography(scene.shape, rotate_deg=30.0, scale=0.7)
    img2, _ = fm.warp_homography(scene, Ht)
    img2 = np.clip(img2, 0, 1)
    m = fm.features_match(sift_ref, fm.features_sift(img2))
    ours = fm.corner_error(fm.ransac_homography(m)["H"], Ht, scene.shape)
    s = cv2.SIFT_create()
    k1, d1 = s.detectAndCompute((scene * 255).round().astype(np.uint8), None)
    k2, d2 = s.detectAndCompute((img2 * 255).round().astype(np.uint8), None)
    good = [a for a, b in cv2.BFMatcher().knnMatch(d1, d2, k=2) if a.distance < 0.8 * b.distance]
    p1 = np.float32([k1[g.queryIdx].pt for g in good])
    p2 = np.float32([k2[g.trainIdx].pt for g in good])
    Hc, _ = cv2.findHomography(p1, p2, cv2.RANSAC, 2.0)
    theirs = fm.corner_error(Hc, Ht, scene.shape)
    assert ours < 1.0 and theirs < 1.0
    assert ours < 3.0 * theirs + 0.3
    assert 0.67 < len(sift_ref["xy"]) / len(k1) < 1.5


def test_sift_descriptor_is_unit_norm_and_clipped(sift_ref):
    d = sift_ref["descriptors"].astype(np.float64)
    assert np.allclose(np.linalg.norm(d, axis=1), 1.0, atol=1e-5)
    # 0.2 で切ってから正規化し直すので、各成分は 0.2 / (切った後のノルム) 以下。切った後のノルム <= 1。
    assert d.max() < 0.5 and d.min() >= 0.0


# ---- ORB -----------------------------------------------------------------------------------

def test_orb_rotation_45(scene):
    Ht = fm.condition_homography(scene.shape, rotate_deg=45.0)
    img2, _ = fm.warp_homography(scene, Ht)
    m = fm.features_match(fm.features_orb(scene), fm.features_orb(np.clip(img2, 0, 1)))
    h = fm.ransac_homography(m)
    assert m["metric"] == "hamming"
    assert fm.corner_error(h["H"], Ht, scene.shape) < 1.0


def test_orb_descriptor_is_256_bits(scene):
    f = fm.features_orb(scene, n_features=200)
    assert f["descriptors"].dtype == np.uint8 and f["descriptors"].shape[1] == 32
    assert 0 < len(f["xy"]) <= 200
    assert f["descriptor_kind"] == "binary"


# ---- matching ------------------------------------------------------------------------------

def test_float_matching_equals_existing_match_descriptors(scene, sift_ref):
    """実数の記述子では既存の features.match_descriptors と同じ組(一致の門)。"""
    f2 = fm.features_sift(np.rot90(scene).copy())
    for ratio, mutual in ((0.8, True), (0.9, False), (0.6, True)):
        m = fm.features_match(sift_ref, f2, ratio=ratio, mutual=mutual)
        ref = features.match_descriptors(sift_ref["descriptors"], f2["descriptors"], ratio=ratio, mutual=mutual)
        assert np.array_equal(m["idx"], ref), (ratio, mutual)


def test_hamming_distance_is_the_number_of_flipped_bits():
    """閉形式: k ビット反転した記述子との Hamming 距離はちょうど k。"""
    rng = np.random.default_rng(0)
    A = rng.integers(0, 256, (5, 32), dtype=np.uint8)
    flips = [0, 3, 17, 64, 200]
    B = A.copy()
    for i, k in enumerate(flips):
        bits = np.unpackbits(B[i])
        bits[rng.choice(256, k, replace=False)] ^= 1
        B[i] = np.packbits(bits)
    D = fm._distances(A, B, "binary")
    assert np.array_equal(np.diag(D).astype(int), flips)


def test_match_refuses_mixed_descriptor_kinds(scene, sift_ref):
    with pytest.raises(ValueError, match="descriptor kinds differ"):
        fm.features_match(sift_ref, fm.features_orb(scene))


# ---- RANSAC --------------------------------------------------------------------------------

def _synthetic_matches(H, n=200, outlier=0.4, noise=0.3, seed=0, shape=(240, 320)):
    rng = np.random.default_rng(seed)
    p1 = rng.uniform([0, 0], [shape[1], shape[0]], (n, 2))
    p2 = fm._apply_h(H, p1) + rng.normal(0, noise, (n, 2))
    bad = rng.random(n) < outlier
    p2[bad] = rng.uniform([0, 0], [shape[1], shape[0]], (int(bad.sum()), 2))
    m = {"kind": "feature_matches", "pts1": p1, "pts2": p2, "idx": np.c_[np.arange(n), np.arange(n)],
         "distance": np.zeros(n), "ratio_value": np.zeros(n), "metric": "l2", "n1": n, "n2": n,
         "image_shape1": shape, "image_shape2": shape}
    return m, ~bad


@pytest.mark.parametrize("score", ["msac", "ransac"])
def test_ransac_homography_with_40pct_outliers(score):
    H = np.array([[0.9, -0.2, 30.0], [0.15, 1.05, -12.0], [2e-4, -1e-4, 1.0]])
    m, good = _synthetic_matches(H)
    h = fm.ransac_homography(m, thresh=1.5, score=score)
    assert fm.corner_error(h["H"], H, (240, 320)) < 0.3
    tp = (h["inliers"] & good).sum()
    assert tp / good.sum() > 0.95                       # 再現率
    assert tp / h["inliers"].sum() > 0.97               # 適合率
    assert np.sign(h["H"][0, 2]) == 1 and np.sign(h["H"][1, 2]) == -1


@pytest.mark.parametrize("model, H", [
    ("translation", np.array([[1.0, 0.0, -37.5], [0.0, 1.0, 12.25], [0.0, 0.0, 1.0]])),
    ("similarity", np.array([[0.95 * math.cos(0.3), -0.95 * math.sin(0.3), 20.0],
                             [0.95 * math.sin(0.3), 0.95 * math.cos(0.3), -8.0], [0.0, 0.0, 1.0]])),
    ("affine", np.array([[1.1, 0.2, 5.0], [-0.1, 0.9, 3.0], [0.0, 0.0, 1.0]])),
])
def test_ransac_restricted_models_recover_their_own_family(model, H):
    m, good = _synthetic_matches(H, outlier=0.3, noise=0.2, seed=5)
    h = fm.ransac_homography(m, model=model, thresh=1.0)
    assert h["model"] == model and fm.corner_error(h["H"], H, (240, 320)) < 0.1
    assert np.allclose(h["H"][2], [0, 0, 1])
    assert (h["inliers"] == good).mean() > 0.97


def test_projective_extrapolates_badly_from_a_narrow_strip_but_translation_does_not():
    """正しい組が幅 20 px の帯に 10 組だけ(雑音 0.5 px): 射影は帯の外で外し、並進は外さない(貼り合わせの教訓)。

    種 0〜4 の実測で射影の 4 隅誤差 3.8〜24 px、並進 0.07〜0.23 px。ここは種 2。"""
    rng = np.random.default_rng(2)
    p1 = np.c_[rng.uniform(200, 220, 10), rng.uniform(0, 200, 10)]
    p2 = p1 + [-140.0, 0.0] + rng.normal(0, 0.5, (10, 2))
    m = {"kind": "feature_matches", "pts1": p1, "pts2": p2, "idx": np.c_[np.arange(10), np.arange(10)],
         "distance": np.zeros(10), "ratio_value": np.zeros(10), "metric": "l2", "n1": 10, "n2": 10,
         "image_shape1": (200, 220), "image_shape2": (200, 220)}
    Ht = np.array([[1, 0, -140.0], [0, 1, 0], [0, 0, 1.0]])
    e_proj = fm.corner_error(fm.ransac_homography(m, min_inliers=4, thresh=3.0)["H"], Ht, (200, 220))
    e_tr = fm.corner_error(fm.ransac_homography(m, model="translation", min_inliers=4, thresh=3.0)["H"], Ht,
                           (200, 220))
    assert e_tr < 0.3 and e_proj > 3.0 and e_proj > 10 * e_tr


def test_ransac_adaptive_iterations_stop_early_on_clean_data():
    H = np.array([[1.0, 0.0, 5.0], [0.0, 1.0, -3.0], [0.0, 0.0, 1.0]])
    m, _ = _synthetic_matches(H, outlier=0.0, noise=0.1)
    h = fm.ransac_homography(m)
    assert h["iterations"] < 50 and h["inlier_ratio"] > 0.99


def test_ransac_no_consensus_raises():
    rng = np.random.default_rng(1)
    m, _ = _synthetic_matches(np.eye(3), n=60, outlier=1.0, seed=2)
    m["pts2"] = rng.uniform(0, 300, (60, 2))
    with pytest.raises(ValueError, match="no consensus"):
        fm.ransac_homography(m, thresh=0.5, min_inliers=20)


def test_ransac_fundamental_matches_the_true_epipolar_geometry():
    """真の F = K⁻ᵀ [t]ₓ R K⁻¹(合成のカメラ)。推定の F と符号・尺度をそろえて差 < 0.05。"""
    rng = np.random.default_rng(4)
    K = np.array([[400.0, 0, 160], [0, 400.0, 120], [0, 0, 1]])
    th = math.radians(8.0)
    R = np.array([[math.cos(th), 0, math.sin(th)], [0, 1, 0], [-math.sin(th), 0, math.cos(th)]])
    t = np.array([-1.0, 0.1, 0.05])
    X = np.c_[rng.uniform(-2, 2, 300), rng.uniform(-1.5, 1.5, 300), rng.uniform(4, 9, 300)]
    x1 = (K @ X.T).T
    x1 = x1[:, :2] / x1[:, 2:]
    X2 = (R @ X.T).T + t
    x2 = (K @ X2.T).T
    x2 = x2[:, :2] / x2[:, 2:]
    x2n = x2 + rng.normal(0, 0.2, x2.shape)
    bad = rng.random(300) < 0.3
    x2n[bad] = rng.uniform(0, 320, (int(bad.sum()), 2))
    tx = np.array([[0, -t[2], t[1]], [t[2], 0, -t[0]], [-t[1], t[0], 0]])
    Ft = np.linalg.inv(K).T @ tx @ R @ np.linalg.inv(K)
    Ft /= np.linalg.norm(Ft)
    if Ft[2, 2] < 0:
        Ft = -Ft
    m = {"kind": "feature_matches", "pts1": x1, "pts2": x2n, "idx": np.c_[np.arange(300), np.arange(300)],
         "distance": np.zeros(300), "ratio_value": np.zeros(300), "metric": "l2", "n1": 300, "n2": 300,
         "image_shape1": (240, 320), "image_shape2": (240, 320)}
    f = fm.ransac_fundamental(m, thresh=1.0)
    assert np.linalg.norm(f["F"] - Ft) < 0.05
    assert f["rms_px"] < 0.5
    assert (f["inliers"] & ~bad).sum() / (~bad).sum() > 0.9


# ---- the accuracy table --------------------------------------------------------------------

def test_accuracy_table_rows_break_in_the_documented_direction(scene):
    T = fm.features_accuracy_table(scene, detector="sift",
                                   conditions=["identity", "blur_1", "blur_4", "gain_0.5", "rotate_90"])
    rows = {r["condition"]: r for r in T["rows"]}
    idt = rows["identity"]
    assert idt["precision"] == 1.0 and idt["corner_error_px"] < 1e-6 and idt["repeatability"] == 1.0
    assert idt["matching_score"] <= 1.0
    # ぼけは強いほど壊れる(符号つきの比較)
    assert rows["blur_4"]["corner_error_px"] > rows["blur_1"]["corner_error_px"]
    assert rows["blur_4"]["repeatability"] < rows["blur_1"]["repeatability"]
    # SIFT のコントラストのしきい値は絶対値なので、利得 0.5 で点が半分以下へ減る(記述子は正規化で残る)
    assert rows["gain_0.5"]["n_kp2"] < 0.6 * idt["n_kp1"]
    assert rows["gain_0.5"]["precision"] > 0.95
    assert rows["rotate_90"]["corner_error_px"] < 0.5
    assert len(T["rows"]) == 5
    for r in T["rows"]:
        assert 0.0 <= r["repeatability"] <= 1.0 and 0.0 <= r["matching_score"] <= 1.0


def test_accuracy_table_validates_conditions(scene):
    with pytest.raises(ValueError, match="unknown condition"):
        fm.features_accuracy_table(scene, conditions=["nope"])
    with pytest.raises(ValueError, match="unknown condition keys"):
        fm.features_accuracy_table(scene, conditions=[("x", {"zoom": 2})])
    with pytest.raises(ValueError, match="must be > 0"):
        fm.features_accuracy_table(scene, conditions=[("x", {"scale": 0.0})])


# ---- fail-closed ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad, msg", [
    (np.zeros((64, 64)), "constant"),
    (np.full((64, 64), np.nan), "non-finite"),
    (np.zeros((64, 64, 3)) + np.arange(3), "2-D"),
    (np.random.default_rng(0).random((8, 8)), "at least"),
])
def test_features_refuse_bad_images(bad, msg):
    for f in (fm.features_sift, fm.features_orb):
        with pytest.raises(ValueError, match=msg):
            f(bad)


def test_tables_with_the_wrong_kind_are_refused(sift_ref):
    with pytest.raises(ValueError, match="kind='feature_matches'"):
        fm.ransac_homography(sift_ref)
    with pytest.raises(ValueError, match="kind='features'"):
        fm.features_match({"kind": "homography"}, sift_ref)


def test_ledger_lists_the_twelve_ops():
    assert len(opsmatchreg.OPSMATCHREG) == 12 and not opsmatchreg.missing()
    assert set(opsmatchreg.categories()) == {"featmatch", "intensityreg"}


def test_blur_breaks_orb_more_than_mild_noise(scene):
    """ORB(FAST)はぼけに弱い: blur_4 の再現率は noise_0.02 より低い。"""
    T = fm.features_accuracy_table(scene, detector="orb", conditions=["noise_0.02", "blur_4"])
    r = {x["condition"]: x for x in T["rows"]}
    assert r["blur_4"]["repeatability"] < r["noise_0.02"]["repeatability"] - 0.3


def test_warp_homography_identity_is_exact(scene):
    out, valid = fm.warp_homography(scene, np.eye(3))
    assert valid.all() and np.max(np.abs(out - scene)) < 1e-12
    # 3 次スプラインは格子点で元の値を通る(prefilter つき)
    out2, _ = fm.warp_homography(ndimage.gaussian_filter(scene, 1.0), np.eye(3), order=3)
    assert np.max(np.abs(out2 - ndimage.gaussian_filter(scene, 1.0))) < 1e-10
