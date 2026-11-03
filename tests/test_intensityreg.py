# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""intensityreg の門 —— 真値は合成に使った既知の変換・既知の変形場(推定側は知らない)、
既存 op(demons・位相相関・imgmetrics の MI)、OpenCV の findTransformECC。

Synthesis uses cubic splines; the registration samples bilinearly, so the two never share an
interpolation kernel. Pairs are cut from a larger scene so that no black border enters the
comparison (a black border is a strong fake edge that biases every intensity method).
"""
import math

import numpy as np
import pytest
from scipy import ndimage

import featmatch as fm
import imgmetrics
import intensityreg as ir


def _pair(W, n=128, o=32, seed=1):
    """大きな場面から切り出した対(縁に黒い帯が入らない)。moving(W p) = fixed(p)。"""
    S = fm.synthetic_scene((n + 2 * o, n + 2 * o), seed=seed)
    T = np.array([[1, 0, o], [0, 1, o], [0, 0, 1.0]])
    Mb = ir.warp_parametric(S, T @ W @ np.linalg.inv(T))
    return S[o:o + n, o:o + n], Mb[o:o + n, o:o + n]


W_AFF = np.array([[1.02, 0.03, 2.5], [-0.02, 0.99, -1.5], [0, 0, 1.0]])


# ---- ECC -----------------------------------------------------------------------------------

@pytest.mark.parametrize("tx, ty", [(0.25, -1.5), (1.0, 0.0), (2.5, -1.5), (-3.0, 2.0)])
def test_ecc_translation_is_unbiased(tx, ty):
    F, M = _pair(np.array([[1, 0, tx], [0, 1, ty], [0, 0, 1.0]]))
    r = ir.register_ecc(F, M, motion="translation")
    assert abs(r["warp"][0, 2] - tx) < 0.02 and abs(r["warp"][1, 2] - ty) < 0.02
    assert r["converged"] and r["metric"] > 0.99


@pytest.mark.parametrize("motion, W, tol", [
    ("euclidean", np.array([[math.cos(0.05), -math.sin(0.05), 1.5], [math.sin(0.05), math.cos(0.05), -2.0],
                            [0, 0, 1.0]]), 0.05),
    ("affine", W_AFF, 0.05),
    ("homography", np.array([[1.01, 0.02, 1.5], [-0.01, 0.99, -1.0], [1e-4, -5e-5, 1.0]]), 0.05),
])
def test_ecc_parametric_corner_error(motion, W, tol):
    F, M = _pair(W)
    r = ir.register_ecc(F, M, motion=motion, levels=2)
    assert fm.corner_error(r["warp"], W, F.shape) < tol


def test_ecc_flow_matches_the_warp_convention():
    """flow(p) = p - W p、warp_by_field(moving, dx, dy) が fixed に重なる(demons と同じ向き)。"""
    import deformreg
    F, M = _pair(W_AFF)
    r = ir.register_ecc(F, M, motion="affine")
    yy, xx = np.mgrid[0:128, 0:128].astype(float)
    X = r["warp"][0, 0] * xx + r["warp"][0, 1] * yy + r["warp"][0, 2]
    assert np.allclose(r["flow2d"][1], xx - X)
    back = deformreg.warp_by_field(M, r["flow2d"][1], r["flow2d"][0])
    inner = (slice(10, -10), slice(10, -10))
    assert np.sqrt(np.mean((back - F)[inner] ** 2)) < 0.01


def test_ecc_against_opencv_and_the_border_band():
    """OpenCV 5.0 の findTransformECC と同じ対。どちらも収束し、こちらの誤差は OpenCV 以下。

    OpenCV は平滑化の縁(折り返しの値)も照合に入れるので並進でも偏る。ここは 3σ の帯を外す。
    """
    cv2 = pytest.importorskip("cv2")
    F, M = _pair(W_AFF)
    ours = fm.corner_error(ir.register_ecc(F, M, motion="affine")["warp"], W_AFF, F.shape)
    w = np.eye(2, 3, dtype=np.float32)
    _, w = cv2.findTransformECC(F.astype(np.float32), M.astype(np.float32), w, cv2.MOTION_AFFINE,
                                (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6), None, 5)
    theirs = fm.corner_error(np.vstack([w, [0, 0, 1]]), W_AFF, F.shape)
    assert ours < 0.05
    assert theirs < 1.0
    assert ours <= theirs + 0.01


def test_ecc_refuses_anticorrelated_pairs():
    F, M = _pair(W_AFF)
    with pytest.raises(ValueError, match="would not converge"):
        ir.register_ecc(F, 1.0 - M, motion="affine")


def test_ecc_step_option_widens_the_capture_range_and_min_rho_guards_it():
    """初期のずれ 32 px(1 段): 分母が負で止まる既定(OpenCV と同じ)より ``nonpositive="step"`` の成功率が高い。

    ★ピラミッド(levels=3)はこの場面では範囲を**広げなかった**(粗い段は 32 px でぼけて相関が落ちる)——
    その事実も固定する。``"step"`` は白黒反転の組でも「相関 0.35」へ進んでしまうので、``min_rho`` が床。
    """
    F = fm.synthetic_scene((128, 128), seed=2)
    rate = {}
    for lv, npv in ((1, "raise"), (1, "step"), (3, "raise")):
        C = ir.register_capture_range(F, method="ecc", offsets_px=(32,), n_directions=8,
                                      method_kwargs={"motion": "translation", "levels": lv, "nonpositive": npv})
        rate[(lv, npv)] = C["rows"][0]["success_rate"]
    assert rate[(1, "step")] >= rate[(1, "raise")] + 0.25
    assert rate[(3, "raise")] <= rate[(1, "raise")]
    Fp, Mp = _pair(W_AFF)
    with pytest.raises(ValueError, match="min_rho"):
        ir.register_ecc(Fp, 1.0 - Mp, motion="affine", nonpositive="step", min_rho=0.8)


# ---- MI ------------------------------------------------------------------------------------

@pytest.mark.parametrize("modality", ["inverted", "folded"])
def test_mi_recovers_affine_across_modalities(modality):
    F, M = _pair(W_AFF)
    M2 = ir._modality(M, modality)
    r = ir.register_mi(F, M2, model="affine")
    assert fm.corner_error(r["warp"], W_AFF, F.shape) < 0.15
    assert 1.0 < r["nmi"] <= 2.0


def test_ecc_fails_where_mi_works_on_a_folded_mapping():
    """sin(πx) は単調でない(0.3 と 0.7 が同じ明るさ)。ECC は誤差 > 0.5 px か拒否、MI は < 0.15 px。"""
    F, M = _pair(W_AFF)
    M2 = ir._modality(M, "folded")
    try:
        e_ecc = fm.corner_error(ir.register_ecc(F, M2, motion="affine")["warp"], W_AFF, F.shape)
    except ValueError:
        e_ecc = np.inf
    e_mi = fm.corner_error(ir.register_mi(F, M2)["warp"], W_AFF, F.shape)
    assert e_ecc > 0.5 and e_mi < 0.15


def test_mi_result_raises_the_existing_mi_metric():
    """既存の指標 imgmetrics.mutual_information が、合わせる前より合わせた後で大きい。"""
    F, M = _pair(W_AFF)
    M2 = 1.0 - M
    r = ir.register_mi(F, M2)
    v = r["valid"] & np.pad(np.ones((108, 108), bool), 10)
    before = imgmetrics.mutual_information(F[v], M2[v], bins=32)
    after = imgmetrics.mutual_information(F[v], r["warped"][v], bins=32)
    assert after > before + 0.3


@pytest.mark.parametrize("model", ["rigid", "similarity"])
def test_mi_restricted_models(model):
    th = math.radians(3.0)
    s = 1.0 if model == "rigid" else 1.03
    W = np.array([[s * math.cos(th), -s * math.sin(th), 2.0], [s * math.sin(th), s * math.cos(th), 1.0],
                  [0, 0, 1.0]])
    c = np.array([63.5, 63.5])
    W[:2, 2] = c + np.array([2.0, 1.0]) - W[:2, :2] @ c
    F, M = _pair(W)
    r = ir.register_mi(F, ir._modality(M, "gamma"), model=model)
    assert fm.corner_error(r["warp"], W, F.shape) < 0.2


# ---- FFD -----------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def sheet():
    F = fm.synthetic_scene((128, 128), seed=2)
    g = ir.smooth_test_field(F.shape, amplitude=3.0, wavelength=64, seed=0)
    return F, g


def test_ffd_recovers_a_smooth_field(sheet):
    F, g = sheet
    A = ir.register_accuracy_map(F, g, method="ffd")
    assert A["epe_mean"] < 0.2 and A["epe_p95"] < 0.5
    # 符号: |真の成分| > 1 px の画素で、推定の成分は真と同じ符号(取り違えると逆になる)
    for k in (0, 1):
        big = A["mask"] & (np.abs(g[k]) > 1.0)
        assert big.sum() > 500
        assert (np.sign(A["est_flow2d"][k][big]) == np.sign(g[k][big])).mean() > 0.99


def test_ffd_and_demons_share_the_field_convention(sheet):
    """同じ真値で demons(既存 op)も小さな誤差 = 2 つの場の向きが揃っている(逆なら EPE は ~2|g|)。"""
    F, g = sheet
    A = ir.register_accuracy_map(F, g, method="demons", method_kwargs={"iters": 200, "sigma": 2.0})
    assert A["epe_mean"] < 0.3
    assert A["epe_mean"] < 0.25 * np.hypot(g[0], g[1])[A["mask"]].mean() * 2


def test_ffd_membrane_tames_blank_regions_at_a_cost_on_large_smooth_fields(sheet):
    """膜の罰: 模様の無い右半分での推定の暴れを抑える。滑らかな大きな場(模様あり)では誤差を増やす。"""
    F = fm.synthetic_scene((128, 128), seed=4)
    F[:, 64:] = 0.5 + 0.004 * np.random.default_rng(1).normal(size=(128, 64))
    g = ir.smooth_test_field(F.shape, amplitude=1.5, wavelength=24, seed=1)
    kw0 = {"grid_spacing": 12}
    kw1 = {"grid_spacing": 12, "membrane_weight": 1.0}
    a0 = ir.register_accuracy_map(F, g, method="ffd", method_kwargs=kw0)
    a1 = ir.register_accuracy_map(F, g, method="ffd", method_kwargs=kw1)
    right = a0["mask"].copy()
    right[:, :72] = False
    mx0 = np.hypot(*a0["est_flow2d"])[right].max()
    mx1 = np.hypot(*a1["est_flow2d"])[right].max()
    assert mx1 < mx0
    Fs, gs = sheet
    b0 = ir.register_accuracy_map(Fs, gs, method="ffd")["epe_mean"]
    b1 = ir.register_accuracy_map(Fs, gs, method="ffd", method_kwargs={"membrane_weight": 1.0})["epe_mean"]
    assert b1 > b0


def test_ffd_zero_field_is_exactly_zero(sheet):
    F, _ = sheet
    A = ir.register_accuracy_map(F, np.zeros((2,) + F.shape), method="ffd")
    assert A["epe_max"] < 1e-9


def test_ffd_cannot_represent_waves_shorter_than_its_grid():
    """波長 24 px の場は格子 16 px では表せず(EPE 大)、格子 8 px では表せる —— 分解能の限界を数で。"""
    F = fm.synthetic_scene((128, 128), seed=5)
    g = ir.smooth_test_field(F.shape, amplitude=1.5, wavelength=24, seed=1)
    e16 = ir.register_accuracy_map(F, g, method="ffd", method_kwargs={"grid_spacing": 16})["epe_mean"]
    e8 = ir.register_accuracy_map(F, g, method="ffd", method_kwargs={"grid_spacing": 8})["epe_mean"]
    assert e16 > 1.5 * e8


def test_ffd_regulariser_gradient_is_exact_and_data_gradient_matches_inside():
    F = ndimage.gaussian_filter(fm.synthetic_scene((64, 64), seed=2), 3.0)
    g = ir.smooth_test_field(F.shape, 1.5, 30, 0)
    M, _ = ir.synthesize_moving(F, g)
    rng = np.random.default_rng(0)
    f0, By, Bx = ir._ffd_objective(F, M, 8.0, 0.0)
    f1, _, _ = ir._ffd_objective(F, M, 8.0, 5.0)
    ny, nx = By.shape[1], Bx.shape[1]
    c = rng.normal(0, 0.3, 2 * ny * nx)
    h = 1e-5

    def num(fun, i):
        e = np.zeros_like(c)
        e[i] = h
        return (fun(c + e)[0] - fun(c - e)[0]) / (2 * h)

    reg = lambda x: (f1(x)[0] - f0(x)[0], f1(x)[1] - f0(x)[1])   # noqa: E731
    gr = reg(c)[1]
    for i in (5, 40, 77, ny * nx + 33):
        assert abs(num(reg, i) - gr[i]) <= 1e-6 * max(1.0, abs(gr[i]))
    # データ項: 解析勾配は中心差分の勾配画像を使う近似(双線形の傾きは区分的に一定)なので完全一致は
    # しない。内側の係数全部で、数値微分との向きの一致(余弦 > 0.99)と相対ノルム誤差 < 0.2 を門にする。
    gd = f0(c)[1]
    ids = [comp * ny * nx + a * nx + b for comp in (0, 1) for a in range(2, ny - 2) for b in range(2, nx - 2)]
    nm = np.array([num(f0, i) for i in ids])
    an = gd[ids]
    assert nm @ an / (np.linalg.norm(nm) * np.linalg.norm(an)) > 0.99
    assert np.linalg.norm(nm - an) / np.linalg.norm(nm) < 0.2


def test_flat_regions_have_larger_error_than_textured_ones():
    """左半分に模様・右半分が平ら: 平らな側の EPE の中央値が模様の側より大きい(場が決まらない)。"""
    F = fm.synthetic_scene((128, 128), seed=4)
    F[:, 64:] = ndimage.gaussian_filter(F[:, 64:], 12.0).mean()
    F[:, 64:] += np.linspace(0, 0.02, 64)[None, :]
    g = ir.smooth_test_field(F.shape, amplitude=2.0, wavelength=64, seed=2)
    A = ir.register_accuracy_map(F, g, method="demons", method_kwargs={"iters": 200, "sigma": 2.0})
    m = A["mask"]
    el = np.median(A["error_map"][:, 8:56][m[:, 8:56]])
    er = np.median(A["error_map"][:, 72:120][m[:, 72:120]])
    assert er > 2.0 * el
    assert A["by_texture"][0]["epe_median"] > A["by_texture"][-1]["epe_median"]


# ---- accuracy map / capture range ----------------------------------------------------------

def test_synthesize_moving_round_trip_and_invertibility():
    import deformreg
    F = fm.synthetic_scene((96, 96), seed=1)
    g = ir.smooth_test_field(F.shape, amplitude=2.0, wavelength=48, seed=3)
    M, valid = ir.synthesize_moving(F, g, order=3)
    back = deformreg.warp_by_field(M, g[1], g[0])
    inner = (slice(6, -6), slice(6, -6))
    assert np.sqrt(np.mean((back - F)[inner] ** 2)) < 0.02
    yy, xx = np.mgrid[0:96, 0:96].astype(float)
    with pytest.raises(ValueError, match="not invertible"):
        ir.synthesize_moving(F, np.stack([np.zeros_like(xx), 8.0 * np.sin(xx / 3.0)]))


def test_capture_range_orders_phase_ecc_and_ffd():
    """並進の収束の範囲: 位相相関(大域)>= ECC(局所)> FFD(制御格子の局所)。"""
    F = fm.synthetic_scene((128, 128), seed=2)
    caps = {}
    for meth, kw in (("phase", {}), ("ecc", {"motion": "translation"}), ("ffd", {})):
        C = ir.register_capture_range(F, method=meth, method_kwargs=kw, offsets_px=(1, 2, 4, 8, 16, 32),
                                      n_directions=4)
        caps[meth] = C["capture_range_px"]
    assert caps["phase"] >= 16 and caps["phase"] >= caps["ecc"] > caps["ffd"] >= 1


def test_rotation_breaks_phase_correlation_but_not_euclidean_ecc():
    F = fm.synthetic_scene((128, 128), seed=2)
    ph = ir.register_capture_range(F, method="phase", offsets_px=(2,), n_directions=4, rotation_deg=6.0)
    ec = ir.register_capture_range(F, method="ecc", offsets_px=(2,), n_directions=4, rotation_deg=6.0,
                                   method_kwargs={"motion": "euclidean", "levels": 2})
    assert ph["rows"][0]["success_rate"] == 0.0
    assert ec["rows"][0]["success_rate"] == 1.0


def test_registration_to_flow2d_and_kind_checks():
    F, M = _pair(W_AFF)
    r = ir.register_ecc(F, M, motion="affine")
    f = ir.registration_to_flow2d(r)
    assert f.shape == (2, 128, 128) and np.array_equal(f, r["flow2d"]) and f is not r["flow2d"]
    with pytest.raises(ValueError, match="kind='registration'"):
        ir.registration_to_flow2d({"kind": "homography"})


@pytest.mark.parametrize("call, msg", [
    (lambda F: ir.register_ecc(F, F, motion="similarity"), "motion must be"),
    (lambda F: ir.register_mi(F, F, model="projective"), "model must be"),
    (lambda F: ir.register_ffd(F, F[:-1]), "same shape"),
    (lambda F: ir.register_ffd(F, F, grid_spacing=2), "grid_spacing"),
    (lambda F: ir.register_ecc(F, F, levels=5), "coarsest level"),
    (lambda F: ir.register_accuracy_map(F, np.zeros((2, 3, 3))), "true_flow2d"),
    (lambda F: ir.register_capture_range(F, method="sift"), "method must be"),
    (lambda F: ir.register_ecc(F, np.zeros_like(F)), "constant"),
])
def test_fail_closed(call, msg):
    F = fm.synthetic_scene((64, 64), seed=0)
    with pytest.raises(ValueError, match=msg):
        call(F)
