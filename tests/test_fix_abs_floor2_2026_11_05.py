"""1.0 前の修正 2026-11-05(abs-floor2): 単位のある量の絶対の床の第 2 便。

前の便(tests/test_fix_abs_floor_2026_11_05.py)と同じ形の門: 入力の尺度を変えても
(1e-15 倍・1e-6 倍・1e6 倍・1e9 倍)結果が尺度 1 の結果と一致するか、尺度どおりに
伸び縮みすることを確かめる。各テストは、比べる前に尺度 1 で意味のある値が出ている
ことを表明する(空の比較で通らないように)。
"""
from __future__ import annotations

import math

import numpy as np
import pytest

import backends_bridge
import dsp
import fourierdesc
import mathnumerics
import specularity
import visualhull


# --------------------------------------------------------------------------- #
# dsp.signal_features: スペクトル重心・帯域・波高率・rms・peak                  #
# --------------------------------------------------------------------------- #
def _two_tone(n=1000, rate=1000.0):
    t = np.arange(n) / rate
    return 0.8 * np.cos(2 * np.pi * 50 * t) + 0.4 * np.cos(2 * np.pi * 200 * t)


@pytest.mark.parametrize("s", [1e-15, 1e-9, 1e-6, 1e6])
def test_signal_features_scale_free_entries_do_not_depend_on_amplitude(s):
    x = _two_tone()
    ref = dsp.signal_features(x, 1000.0)
    # 尺度 1 で意味のある値(重心は 50 と 200 の間、帯域 > 0、波高率 > 1)
    assert 50.0 < ref["spectral_centroid"] < 200.0
    assert ref["bandwidth"] > 10.0
    assert ref["crest_factor"] > 1.0
    got = dsp.signal_features(x * s, 1000.0)
    for key in ("spectral_centroid", "bandwidth", "peak_freq", "crest_factor", "zcr"):
        assert got[key] == pytest.approx(ref[key], rel=1e-6, abs=0.0), key


@pytest.mark.parametrize("s", [1e-15, 1e-9, 1e6])
def test_signal_features_rms_and_peak_scale_with_amplitude(s):
    x = _two_tone()
    ref = dsp.signal_features(x, 1000.0)
    assert ref["rms"] > 0.5 and ref["peak"] > 1.0
    got = dsp.signal_features(x * s, 1000.0)
    # 丸めで 0 に潰れず、尺度どおり(有効数字 6 桁)
    assert got["rms"] == pytest.approx(ref["rms"] * s, rel=1e-5, abs=0.0)
    assert got["peak"] == pytest.approx(ref["peak"] * s, rel=1e-5, abs=0.0)


def test_signal_features_unit_scale_values_are_unchanged():
    # 尺度 1 の値は修正前と同じ丸め(rms・peak は小数 6 桁、周波数は小数 3 桁)
    f = dsp.signal_features(_two_tone(), 1000.0)
    assert f["rms"] == round(math.sqrt(0.8 ** 2 + 0.4 ** 2) / math.sqrt(2), 6)
    assert f["peak_freq"] == 50.0
    assert f["spectral_centroid"] == round(f["spectral_centroid"], 3)


def test_signal_features_zero_signal_is_finite():
    f = dsp.signal_features(np.zeros(64), 1000.0)
    assert len(f) == 7
    assert all(np.isfinite(v) for v in f.values())
    assert f["rms"] == 0.0 and f["crest_factor"] == 0.0


# --------------------------------------------------------------------------- #
# backends_bridge.matrix_to_img: 小さい値の行列を一様 0.5 にしない               #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("b", [0.0, 0.7])
@pytest.mark.parametrize("s", [1e-14, 1e-9, 1e6])
def test_matrix_to_img_linear_is_scale_free(s, b):
    M = np.array([[1.0, -2.0, 0.25], [3.0, 0.5, -1.0]])
    ref = backends_bridge.matrix_to_img(M, 0.0, b)
    assert float(np.ptp(ref)) > 0.5                     # 尺度 1 で濃淡がある
    got = backends_bridge.matrix_to_img(M * s, 0.0, b)
    np.testing.assert_allclose(got, ref, rtol=0, atol=1e-12)


def test_matrix_to_img_constant_matrix_is_neutral_at_any_scale():
    for s in (1e-14, 1.0, 1e6):
        for b in (0.0, 0.7):
            out = backends_bridge.matrix_to_img(np.full((2, 3), 3.0 * s), 0.0, b)
            if b < 0.5:
                assert np.all(out == 0.5)
            else:
                assert np.all(out == 1.0)                # 全部正 → 最大で割って 1
    assert np.all(backends_bridge.matrix_to_img(np.zeros((2, 2)), 0.0, 0.7) == 0.5)


# --------------------------------------------------------------------------- #
# mathnumerics.interp_barycentric(nodes="chebyshev2"): 点の照合は区間の尺度で  #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("s", [1.0, 1e6, 1e9])
def test_interp_barycentric_accepts_chebyshev_nodes_on_a_large_interval(s):
    k = np.arange(17)
    # 同じ点を別の式で作る(丸めの順が違うので、大きい区間では 1e-12 を超えて食い違う)
    xk = np.sort(s * (1.5 + 0.5 * np.cos(k * math.pi / 16)))
    yk = np.sin(xk / s)
    x = np.array([1.3 * s, 1.77 * s])
    got = mathnumerics.interp_barycentric(xk, yk, x, nodes="chebyshev2")
    ref = mathnumerics.interp_barycentric(xk, yk, x)     # 重みを点から計算する経路
    assert got.shape == (2,)
    np.testing.assert_allclose(got, np.sin(x / s), rtol=0, atol=1e-9)
    np.testing.assert_allclose(got, ref, rtol=0, atol=1e-9)


@pytest.mark.parametrize("s", [1.0, 1e-15])
def test_interp_barycentric_rejects_equispaced_nodes_on_a_tiny_interval(s):
    xk = np.linspace(0.0, s, 9)
    expected = mathnumerics.chebyshev_nodes(9, 0.0, s, kind=2)
    assert float(np.abs(xk - expected).max()) > 0.01 * s   # 本当に別の点
    with pytest.raises(ValueError):
        mathnumerics.interp_barycentric(xk, xk, np.array([0.5 * s]), nodes="chebyshev2")


# --------------------------------------------------------------------------- #
# fourierdesc: 周長・第 1 高調波の床                                            #
# --------------------------------------------------------------------------- #
def _contour():
    th = np.linspace(0, 2 * np.pi, 64, endpoint=False)
    r = 1.0 + 0.2 * np.cos(3 * th)
    return np.c_[3.0 * r * np.cos(th), r * np.sin(th) + 0.3 * np.sin(2 * th)]


@pytest.mark.parametrize("s", [1e-13, 1e-9, 1e-6, 1e6])
def test_fourier_invariants_and_normalize_are_scale_free(s):
    P = _contour()
    m1 = fourierdesc.elliptic_fourier(P, 8)
    inv1 = fourierdesc.invariants(m1, scale_invariant=True)
    nrm1 = fourierdesc.normalize(m1, size_invariant=True)
    assert inv1.shape == (8, 2) and inv1[0, 0] == pytest.approx(1.0)
    assert float(np.abs(inv1[1:]).max()) > 0.01               # 形の情報がある
    ms = fourierdesc.elliptic_fourier(P * s, 8)
    np.testing.assert_allclose(ms["coeffs"], m1["coeffs"] * s, rtol=0,
                               atol=1e-9 * s * float(np.abs(m1["coeffs"]).max()))
    np.testing.assert_allclose(fourierdesc.invariants(ms, scale_invariant=True), inv1,
                               rtol=0, atol=1e-9)
    np.testing.assert_allclose(fourierdesc.normalize(ms, size_invariant=True), nrm1,
                               rtol=0, atol=1e-9)


def test_fourier_duplicate_points_do_not_change_the_descriptor():
    P = _contour() * 1e-6                                     # 線分 ~1e-7: 床 1e-12 が効く桁
    Pd = np.repeat(P, 2, axis=0)                              # 各点が 2 回
    a = fourierdesc.elliptic_fourier(P, 6)["coeffs"]
    b = fourierdesc.elliptic_fourier(Pd, 6)["coeffs"]
    assert float(np.abs(a).max()) > 1e-7
    np.testing.assert_allclose(b, a, rtol=0, atol=1e-9 * float(np.abs(a).max()))


def test_fourier_all_coincident_points_are_refused_even_when_many():
    # 床 1e-12 × 点数 >= 1e-9 で、以前は 1000 点以上の一点輪郭が通った
    with pytest.raises(ValueError):
        fourierdesc.elliptic_fourier(np.ones((2000, 2)), 4)
    with pytest.raises(ValueError):
        fourierdesc.elliptic_fourier(np.ones((5, 2)), 4)


# --------------------------------------------------------------------------- #
# visualhull.look_at: eye と target の一致判定は座標の尺度で                      #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("s", [1e-13, 1e-6, 1e6])
def test_look_at_is_scale_free(s):
    eye = np.array([2.0, -1.0, 1.5])
    R1, t1 = visualhull.look_at(eye, (0.0, 0.0, 0.0))
    assert abs(np.linalg.det(R1) - 1.0) < 1e-12
    Rs, ts = visualhull.look_at(eye * s, (0.0, 0.0, 0.0))
    np.testing.assert_allclose(Rs, R1, rtol=0, atol=1e-12)
    np.testing.assert_allclose(ts, t1 * s, rtol=0, atol=1e-12 * s * float(np.abs(t1).max()))


def test_look_at_still_refuses_coincident_eye_and_target():
    for s in (1e-13, 1.0, 1e6):
        with pytest.raises(ValueError):
            visualhull.look_at(np.array([1.0, 2.0, 3.0]) * s, np.array([1.0, 2.0, 3.0]) * s)


# --------------------------------------------------------------------------- #
# specularity.photometric_stereo_robust(normalize=False): 光の強さの尺度          #
# --------------------------------------------------------------------------- #
def _ps_scene():
    rng = np.random.default_rng(3)
    H, W = 6, 7
    nz = np.ones((H, W))
    nx = 0.3 * np.sin(np.arange(W))[None, :] * np.ones((H, 1))
    ny = 0.2 * np.cos(np.arange(H))[:, None] * np.ones((1, W))
    n = np.stack([nx, ny, nz], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    L = np.array([[0.3, 0.2, 1.0], [-0.4, 0.1, 1.0], [0.1, -0.5, 1.0],
                  [0.5, 0.5, 1.0], [-0.3, -0.3, 1.0]])
    L = L / np.linalg.norm(L, axis=1, keepdims=True)
    alb = 0.5 + 0.3 * rng.random((H, W))
    I = np.maximum(np.einsum("li,hwi->lhw", L, n), 0.0) * alb[None]
    return I, L


@pytest.mark.parametrize("s", [1e-5, 1e3])
def test_photometric_stereo_robust_unnormalised_lights_scale_free(s):
    I, L = _ps_scene()
    n1, a1, _ = specularity.photometric_stereo_robust(I, L, normalize=False)
    assert np.isfinite(n1).all() and float(np.nanmin(a1)) > 0.4
    ns, as_, _ = specularity.photometric_stereo_robust(I * s, L * s, normalize=False)
    assert np.isfinite(ns).all()
    np.testing.assert_allclose(ns, n1, rtol=0, atol=1e-5)
    np.testing.assert_allclose(as_, a1, rtol=1e-5, atol=0)


@pytest.mark.parametrize("closed", [False, True])
@pytest.mark.parametrize("s", [1e-10, 1e-6, 1e6])
def test_contour_fourier_complex_is_scale_free(s, closed):
    # 兄弟: 閉じ点の判定 np.allclose(atol=1e-8)が、広がり 1e-8 以下の輪郭で本物の点を落とした
    P = _contour()
    if closed:
        P = np.vstack([P, P[0]])
    for par in ("index", "arclength"):
        r = fourierdesc.contour_fourier_complex(P, parametrisation=par)
        assert r.shape == (64, 3) and float(np.abs(r[:, 1:]).max()) > 1.0
        q = fourierdesc.contour_fourier_complex(P * s, parametrisation=par)
        assert q.shape == r.shape
        np.testing.assert_array_equal(q[:, 0], r[:, 0])
        np.testing.assert_allclose(q[:, 1:], r[:, 1:] * s, rtol=0,
                                   atol=1e-12 * s * float(np.abs(r[:, 1:]).max()))
