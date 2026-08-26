"""fringe(構造化光・位相シフト・プロファイロメトリ)の単体テスト。

契約(ground-truth 検証):
  * 既知の滑らかな height map → synthesize_fringes で縞生成 → decode_fringe で復元し、
    復元高さが元の height map と(較正 k・参照位相 ref で吸収した上で)一致する。
  * wrapped_phase が 4-step で理論位相と一致する。
  * graycode_decode が既知の Gray code パターンを正しく整数次数へ戻す。
  * modulation / unwrap の NaN・マスク挙動 / 各種エラー処理。

skimage が無い環境では skip する。
"""
import numpy as np
import pytest

pytest.importorskip("skimage")

import fringe


# --------------------------------------------------------------------------- #
# ヘルパ                                                                        #
# --------------------------------------------------------------------------- #
def _smooth_height(rows=64, cols=96):
    """滑らかな高さ場: ガウス突起 + 緩い傾斜(アンラップ可能な連続場)。"""
    yy, xx = np.mgrid[0:rows, 0:cols].astype(np.float64)
    cy, cx = rows * 0.5, cols * 0.5
    bump = np.exp(-(((yy - cy) / (rows * 0.28)) ** 2 + ((xx - cx) / (cols * 0.28)) ** 2))
    tilt = 0.15 * (xx / cols) + 0.1 * (yy / rows)
    return bump + tilt  # 高さ範囲 ~[0.1, 1.25]


def _corr(a, b):
    a = a.ravel()
    b = b.ravel()
    return float(np.corrcoef(a, b)[0, 1])


# --------------------------------------------------------------------------- #
# ground-truth: height → fringe → 復元高さ                                      #
# --------------------------------------------------------------------------- #
def test_roundtrip_height_recovery_noise_free():
    """既知高さ → 縞 → 復元。ノイズ無しなら定数オフセットを除きほぼ完全一致。"""
    height = _smooth_height()
    freq, gain = 6.0, 2.0

    obj = fringe.synthesize_fringes(height, n_steps=4, freq=freq, phase_gain=gain)
    ref_frames = fringe.synthesize_fringes(np.zeros_like(height), n_steps=4,
                                           freq=freq, phase_gain=gain)
    ref_phase = fringe.unwrap_phase_2d(fringe.wrapped_phase(ref_frames))

    recovered = fringe.decode_fringe(obj, ref_phase=ref_phase, k=1.0 / gain)

    # k=1/gain なのでスケールは既知。定数オフセット(unwrap の大域不定性)だけ除いて比較。
    r0 = recovered - recovered.mean()
    h0 = height - height.mean()
    rms = float(np.sqrt(np.mean((r0 - h0) ** 2)))
    assert np.all(np.isfinite(recovered))
    assert _corr(recovered, height) > 0.9999
    assert rms < 1e-6, f"noise-free RMS が大きすぎます: {rms}"


def test_roundtrip_affine_fit_reports_accuracy():
    """位相のスケール/オフセットは較正で吸収してよい前提で、affine fit 後の残差 RMS を検証。"""
    height = _smooth_height()
    freq, gain = 8.0, 1.5
    obj = fringe.synthesize_fringes(height, n_steps=5, freq=freq, phase_gain=gain)
    flat = fringe.synthesize_fringes(np.zeros_like(height), n_steps=5,
                                     freq=freq, phase_gain=gain)
    ref_phase = fringe.unwrap_phase_2d(fringe.wrapped_phase(flat))
    diff = fringe.decode_fringe(obj, ref_phase=ref_phase, k=1.0)  # = gain*height + const

    # height ≈ slope*diff + intercept を最小二乗で当てる(k と ref で吸収する部分)。
    slope, intercept = np.polyfit(diff.ravel(), height.ravel(), 1)
    fitted = slope * diff + intercept
    rms = float(np.sqrt(np.mean((fitted - height) ** 2)))
    span = float(height.max() - height.min())
    assert rms / span < 1e-4, f"affine fit 後の相対 RMS が大きすぎます: {rms / span}"


def test_roundtrip_robust_to_moderate_noise():
    """中程度のカメラノイズ下でも相関が高いこと(honest な劣化許容)。"""
    height = _smooth_height()
    freq, gain = 5.0, 2.0
    obj = fringe.synthesize_fringes(height, n_steps=8, freq=freq, phase_gain=gain,
                                    noise=0.02, seed=7)
    flat = fringe.synthesize_fringes(np.zeros_like(height), n_steps=8, freq=freq,
                                     phase_gain=gain, noise=0.02, seed=8)
    ref_phase = fringe.unwrap_phase_2d(fringe.wrapped_phase(flat))
    recovered = fringe.decode_fringe(obj, ref_phase=ref_phase, k=1.0 / gain)
    assert _corr(recovered, height) > 0.99


# --------------------------------------------------------------------------- #
# wrapped_phase: 4-step 理論一致                                                #
# --------------------------------------------------------------------------- #
def test_wrapped_phase_4step_matches_theory():
    """I_n = 0.5 + 0.5 cos(φ - δ_n) を 4-step 復号すると φ をそのまま返す。"""
    rows, cols = 8, 40
    phi0 = np.broadcast_to(np.linspace(-3.0, 3.0, cols)[None, :], (rows, cols))
    frames = np.stack([0.5 + 0.5 * np.cos(phi0 - 2 * np.pi * n / 4) for n in range(4)])
    w = fringe.wrapped_phase(frames)
    assert np.allclose(w, phi0, atol=1e-9)


def test_wrapped_phase_range_and_wrap():
    """出力は (-π, π] に収まり、位相が 2π を超える場でも wrap すること。"""
    height = _smooth_height(48, 64)
    frames = fringe.synthesize_fringes(height, n_steps=4, freq=10.0, phase_gain=3.0)
    w = fringe.wrapped_phase(frames)
    assert w.min() >= -np.pi - 1e-9
    assert w.max() <= np.pi + 1e-9
    # 10 周期の搬送波があるので、隣接列で -π/π を跨ぐ wrap が必ず起きる。
    assert (np.abs(np.diff(w, axis=1)) > np.pi).any()


def test_wrapped_phase_nstep_variants_agree():
    """N=3,4,6 いずれでも同じ位相を復元する(N 非依存)。"""
    phi0 = np.linspace(-2.5, 2.5, 30)[None, :] * np.ones((5, 1))
    results = []
    for n in (3, 4, 6):
        frames = np.stack([0.5 + 0.5 * np.cos(phi0 - 2 * np.pi * i / n) for i in range(n)])
        results.append(fringe.wrapped_phase(frames))
    assert np.allclose(results[0], results[1], atol=1e-9)
    assert np.allclose(results[1], results[2], atol=1e-9)


# --------------------------------------------------------------------------- #
# modulation                                                                   #
# --------------------------------------------------------------------------- #
def test_modulation_full_contrast_is_one():
    """bias=amplitude=0.5 の理想縞では変調度 γ = b/a = 1。"""
    height = _smooth_height(32, 48)
    frames = fringe.synthesize_fringes(height, n_steps=4, bias=0.5, amplitude=0.5, freq=4.0)
    g = fringe.modulation(frames)
    assert np.allclose(g, 1.0, atol=1e-6)


def test_modulation_low_contrast_region():
    """振幅の小さい(低反射)縞は変調度が低く出る。"""
    height = _smooth_height(32, 48)
    hi = fringe.synthesize_fringes(height, n_steps=4, bias=0.5, amplitude=0.5, freq=4.0)
    lo = fringe.synthesize_fringes(height, n_steps=4, bias=0.5, amplitude=0.05, freq=4.0)
    assert fringe.modulation(lo).mean() < fringe.modulation(hi).mean()
    assert fringe.modulation(lo).mean() < 0.2


# --------------------------------------------------------------------------- #
# graycode_decode                                                              #
# --------------------------------------------------------------------------- #
def test_graycode_decode_known_pattern():
    """0..2**K-1 の絶対次数を Gray code 化 → decode で厳密に戻る。"""
    rows, k = 5, 4
    n_codes = 2 ** k
    order = np.broadcast_to(np.arange(n_codes)[None, :], (rows, n_codes)).astype(np.int64)
    gray = order ^ (order >> 1)
    # MSB first のビット面(明=1/暗=0)
    bit_images = np.stack([((gray >> (k - 1 - i)) & 1).astype(np.float64) for i in range(k)])
    decoded = fringe.graycode_decode(bit_images, thresh=0.5)
    assert np.array_equal(decoded, order)


def test_graycode_decode_binarization():
    """明暗が 0.9/0.1 のように非二値でも thresh で正しく二値化される。"""
    rows, k = 3, 3
    n_codes = 2 ** k
    order = np.broadcast_to(np.arange(n_codes)[None, :], (rows, n_codes)).astype(np.int64)
    gray = order ^ (order >> 1)
    bits = np.stack([((gray >> (k - 1 - i)) & 1) for i in range(k)]).astype(np.float64)
    noisy = np.where(bits > 0.5, 0.85, 0.12)  # 明=0.85 / 暗=0.12
    decoded = fringe.graycode_decode(noisy, thresh=0.5)
    assert np.array_equal(decoded, order)


# --------------------------------------------------------------------------- #
# phase_to_height                                                              #
# --------------------------------------------------------------------------- #
def test_phase_to_height_linear():
    phase = np.array([[1.0, 2.0], [3.0, 4.0]])
    ref = 1.0
    out = fringe.phase_to_height(phase, ref, k=0.5)
    assert np.allclose(out, 0.5 * (phase - 1.0))


def test_phase_to_height_array_ref_and_nan_propagation():
    phase = np.array([[1.0, np.nan], [3.0, 4.0]])
    ref = np.array([[0.0, 0.0], [1.0, 2.0]])
    out = fringe.phase_to_height(phase, ref, k=2.0)
    assert np.isnan(out[0, 1])
    assert np.allclose(out[[0, 1, 1], [0, 0, 1]], [2.0, 4.0, 4.0])


# --------------------------------------------------------------------------- #
# unwrap_phase_2d: NaN / マスク / エラー                                         #
# --------------------------------------------------------------------------- #
def test_unwrap_basic_ramp():
    """線形位相ランプを wrap → unwrap で連続位相に復元(定数差のみ)。"""
    x = np.linspace(0, 8 * np.pi, 80)
    ramp = np.broadcast_to(x[None, :], (10, 80)).astype(np.float64)
    wrapped = np.angle(np.exp(1j * ramp))
    un = fringe.unwrap_phase_2d(wrapped)
    d = un - ramp
    assert np.allclose(d - d.mean(), 0.0, atol=1e-6)


def test_unwrap_nan_masked_out():
    """NaN 画素はアンラップから除外され、出力でも NaN。"""
    x = np.linspace(0, 6 * np.pi, 60)
    wrapped = np.angle(np.exp(1j * np.broadcast_to(x[None, :], (8, 60)))).astype(np.float64)
    wrapped[3, 30] = np.nan
    un = fringe.unwrap_phase_2d(wrapped)
    assert np.isnan(un[3, 30])
    assert np.isfinite(un[0, 0])
    assert np.isfinite(np.nansum(un))


def test_unwrap_mask_argument():
    """mask=True を有効画素として扱う(False 画素は NaN)。"""
    x = np.linspace(0, 4 * np.pi, 40)
    wrapped = np.angle(np.exp(1j * np.broadcast_to(x[None, :], (6, 40)))).astype(np.float64)
    mask = np.ones_like(wrapped, dtype=bool)
    mask[2, 20] = False
    un = fringe.unwrap_phase_2d(wrapped, mask=mask)
    assert np.isnan(un[2, 20])


def test_unwrap_all_invalid_raises():
    with pytest.raises(ValueError):
        fringe.unwrap_phase_2d(np.full((4, 4), np.nan))


# --------------------------------------------------------------------------- #
# decode_fringe: マスク・低変調                                                  #
# --------------------------------------------------------------------------- #
def test_decode_fringe_min_modulation_masks():
    """低変調領域を min_modulation でマスクすると、その画素は NaN になる。"""
    height = _smooth_height(32, 48)
    frames = fringe.synthesize_fringes(height, n_steps=4, freq=4.0, phase_gain=2.0)
    # 一部フレームを平坦化して局所的に低変調域を作る
    frames[:, 5:10, 5:10] = 0.5
    out = fringe.decode_fringe(frames, k=1.0, min_modulation=0.5)
    assert np.isnan(out[7, 7])
    assert np.isfinite(out[0, 0])


# --------------------------------------------------------------------------- #
# エラー処理                                                                     #
# --------------------------------------------------------------------------- #
def test_wrapped_phase_requires_min_3_steps():
    with pytest.raises(ValueError):
        fringe.wrapped_phase(np.zeros((2, 8, 8)))


def test_wrapped_phase_requires_3d():
    with pytest.raises(ValueError):
        fringe.wrapped_phase(np.zeros((8, 8)))


def test_synthesize_requires_2d_height():
    with pytest.raises(ValueError):
        fringe.synthesize_fringes(np.zeros((4, 4, 4)))


def test_graycode_requires_3d():
    with pytest.raises(ValueError):
        fringe.graycode_decode(np.zeros((8, 8)))


def test_synthesize_output_domain():
    """合成縞は [0,1] に収まり、shape=(N,H,W)。"""
    height = _smooth_height(20, 30)
    frames = fringe.synthesize_fringes(height, n_steps=6, freq=3.0)
    assert frames.shape == (6, 20, 30)
    assert frames.min() >= 0.0 and frames.max() <= 1.0
