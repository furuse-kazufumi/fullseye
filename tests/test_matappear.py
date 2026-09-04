"""matappear(構造色・異方性反射)の単体テスト。

契約(ground-truth 検証):
  * CIE 1931 等色関数の近似は ȳ のピークが 555 nm 近傍、可視域外で 0 に落ちる。
  * 分光 → sRGB は、反射率 1 の面を **sRGB の基準白 (1,1,1)** に、0.5 を 0.5 に写す。
  * 薄膜の反射率は膜厚 0 で **基板単体のフレネル反射に厳密一致**し、λ/4 で解析的な
    極大値に一致する(閉じた式との突き合わせ)。
  * 回折格子は格子の式 d(sinθo − sinθi) = mλ をそのまま満たす。
  * Ward 異方性はハイライトの**伸びの向きと比**が αx/αy に従う(等方なら円)。
  * 引数検査は fail-closed(形・符号・ゼロ長方向で ValueError)。
"""
import numpy as np
import pytest

import matappear as M


# --------------------------------------------------------------------------- #
# 等色関数と分光 → sRGB                                                         #
# --------------------------------------------------------------------------- #
def test_cmf_peak_and_tails():
    w = np.linspace(360.0, 830.0, 471)
    xyz = M.cie_xyz_from_wavelength(w)
    assert xyz.shape == (471, 3)
    assert abs(w[int(xyz[:, 1].argmax())] - 555.0) <= 3.0     # ȳ のピーク
    assert xyz[0, 1] < 1e-3 and xyz[-1, 1] < 1e-3             # 可視域外は 0 へ
    assert xyz[:, 1].max() == pytest.approx(1.0, abs=0.05)    # ȳ の最大は 1


def test_white_maps_to_srgb_white():
    w = np.linspace(360.0, 830.0, 471)
    white = M.spectrum_to_srgb(w, np.ones_like(w))
    assert np.allclose(white, 1.0, atol=1e-3), white
    half = M.spectrum_to_srgb(w, np.full_like(w, 0.5))
    assert np.allclose(half, 0.5, atol=1e-3), half


def test_narrow_band_is_out_of_gamut_and_not_silently_clipped():
    """単色光は sRGB の色域外 → 負の成分が**そのまま**返る(黙って丸めない)。"""
    w = np.linspace(360.0, 830.0, 471)
    band = np.exp(-0.5 * ((w - 540.0) / 12.0) ** 2)
    rgb = M.spectrum_to_srgb(w, band / band.max())
    assert rgb[1] > 0.2 and rgb.min() < 0.0                   # 緑が強く、色域外で負


def test_spectrum_errors():
    w = np.linspace(400.0, 700.0, 16)
    with pytest.raises(ValueError):
        M.spectrum_to_srgb(w[::-1], np.ones(16))              # 単調でない
    with pytest.raises(ValueError):
        M.spectrum_to_srgb(w, np.ones(15))                    # 長さ不一致
    with pytest.raises(ValueError):
        M.cie_xyz_from_wavelength([-1.0])                     # 負の波長


# --------------------------------------------------------------------------- #
# 薄膜干渉                                                                      #
# --------------------------------------------------------------------------- #
def test_zero_thickness_equals_bare_substrate():
    """膜厚 0 → 基板単体のフレネル反射(垂直入射)に厳密一致。"""
    for n_sub in (1.5, 2.0, 3.5):
        got = float(M.thin_film_reflectance([550.0], 0.0, n_film=1.33, n_sub=n_sub)[0])
        want = ((1.0 - n_sub) / (1.0 + n_sub)) ** 2
        assert got == pytest.approx(want, rel=1e-12), (n_sub, got, want)


def test_quarter_wave_matches_closed_form():
    """λ/4 膜(n0=n2=1、n1=1.33)の反射率は ((n1²−n0n2)/(n1²+n0n2))² に一致。"""
    lam, n1 = 550.0, 1.33
    got = float(M.thin_film_reflectance([lam], lam / (4.0 * n1), n_film=n1, n_sub=1.0)[0])
    want = ((n1 ** 2 - 1.0) / (n1 ** 2 + 1.0)) ** 2
    assert got == pytest.approx(want, rel=1e-9), (got, want)


def test_half_wave_is_absentee_layer():
    """λ/2 膜は「無い」のと同じ(absentee layer)。基板のフレネル反射へ戻る。"""
    lam, n1, n2 = 550.0, 1.33, 1.5
    got = float(M.thin_film_reflectance([lam], lam / (2.0 * n1), n_film=n1, n_sub=n2)[0])
    want = ((1.0 - n2) / (1.0 + n2)) ** 2
    assert got == pytest.approx(want, rel=1e-9), (got, want)


def test_thin_film_range_and_errors():
    w = np.linspace(400.0, 700.0, 32)
    R = M.thin_film_reflectance(w, 350.0, 1.33, 1.0)
    assert R.shape == (32,) and R.min() >= 0.0 and R.max() <= 1.0
    with pytest.raises(ValueError):
        M.thin_film_reflectance(w, -1.0)
    with pytest.raises(ValueError):
        M.thin_film_reflectance(w, 100.0, n_film=0.0)


# --------------------------------------------------------------------------- #
# 回折格子                                                                      #
# --------------------------------------------------------------------------- #
def test_grating_equation_holds():
    """返した λ を格子の式に戻すと sinθo − sinθi が再現する(定義そのものの検算)。"""
    d, si, so, orders = 1.6, -0.10, 0.35, (1, 2, -1)
    lam = M.grating_wavelengths(d, si, so, orders=orders)
    for k, m in enumerate(orders):
        assert (m * lam[k] / (1000.0 * d)) == pytest.approx(so - si, rel=1e-12)


def test_cd_first_order_is_visible_green():
    """CD(1.6 µm)の 1 次は sinθ 差 0.35 で 560 nm — 可視の緑。"""
    lam = M.grating_wavelengths(1.6, 0.0, 0.35, orders=(1,))
    assert float(lam[0]) == pytest.approx(560.0, rel=1e-12)


def test_grating_errors():
    with pytest.raises(ValueError):
        M.grating_wavelengths(1.6, 0.0, 0.3, orders=(0,))     # 0 次に解は無い
    with pytest.raises(ValueError):
        M.grating_wavelengths(-1.0, 0.0, 0.3)


# --------------------------------------------------------------------------- #
# 法線マップを食う 3 op                                                          #
# --------------------------------------------------------------------------- #
def _hemisphere(n=96):
    y, x = np.mgrid[-1:1:n * 1j, -1:1:n * 1j]
    r2 = x * x + y * y
    m = r2 < 1.0
    z = np.sqrt(np.maximum(1.0 - r2, 0.0))
    return np.stack([x, y, z], -1) * m[..., None], m


def _extent(a):
    m = a > 0.1 * a.max()
    ys, xs = np.nonzero(m)
    return int(np.ptp(xs)) + 1, int(np.ptp(ys)) + 1


def test_ward_elongates_along_the_groove_axis():
    """αx > αy ならハイライトは x 方向に伸び、入れ替えると y 方向に伸びる。等方なら円。"""
    n, _ = _hemisphere()
    L = np.array([0.4, 0.5, 0.77]); L /= np.linalg.norm(L)
    wide = M.ward_anisotropic(n, light=L, view=(0, 0, 1), alpha_x=0.30, alpha_y=0.03)
    tall = M.ward_anisotropic(n, light=L, view=(0, 0, 1), alpha_x=0.03, alpha_y=0.30)
    iso = M.ward_anisotropic(n, light=L, view=(0, 0, 1), alpha_x=0.15, alpha_y=0.15)
    ex_w, ey_w = _extent(wide)
    ex_t, ey_t = _extent(tall)
    ex_i, ey_i = _extent(iso)
    assert ex_w > 3 * ey_w, (ex_w, ey_w)
    assert ey_t > 3 * ex_t, (ex_t, ey_t)
    assert 0.7 < ex_i / ey_i < 1.4, (ex_i, ey_i)              # 等方はほぼ円
    assert wide.min() >= 0.0 and np.isfinite(wide).all()


def test_grating_dispersion_needs_the_light_across_the_grooves():
    """★幾何の要件: 分散は**溝に直交する向き**にしか起きない。溝と同じ向きに光源を
    ずらしても λ = d·Δsin は 0 付近のまま = 色は出ない。実測(溝 x、光源も x 方向へ
    20°): Δsin は ±0.063 しかなく λ は ±100 nm(不可視)。溝に直交(y)へ振ると
    Δsin が桁で増える。「色が出ない」の大半はバグではなくこの配置ミスである。"""
    n, m = _hemisphere(64)
    along = np.array([0.35, 0.0, 0.94]); along /= np.linalg.norm(along)
    across = np.array([0.0, 0.55, 0.83]); across /= np.linalg.norm(across)
    a = M.grating_rgb(n, light=along, view=(0, 0, 1), tangent=(1, 0, 0), pitch_um=1.6)
    b = M.grating_rgb(n, light=across, view=(0, 0, 1), tangent=(1, 0, 0), pitch_um=1.6)
    assert np.abs(b[m]).sum() > 100.0 * np.abs(a[m]).sum()


def test_grating_rgb_changes_with_pitch_and_is_zero_on_background():
    n, m = _hemisphere(64)
    L = np.array([0.0, 0.55, 0.83]); L /= np.linalg.norm(L)   # 溝(x)に直交して照らす
    cd = M.grating_rgb(n, light=L, view=(0, 0, 1), pitch_um=1.6)
    bd = M.grating_rgb(n, light=L, view=(0, 0, 1), pitch_um=0.32)
    assert cd.shape == (64, 64, 3)
    assert np.allclose(cd[~m], 0.0) and np.allclose(bd[~m], 0.0)   # 背景は 0
    # ピッチが 1/5 になると同じ幾何で選ばれる波長も 1/5 → 可視域から外れて暗くなる
    assert np.abs(cd[m]).sum() > 3.0 * np.abs(bd[m]).sum()
    # 色が付いている(グレースケールではない)
    assert float(np.abs(cd[..., 0] - cd[..., 2]).max()) > 0.05


def test_thin_film_rgb_moves_with_thickness():
    n, m = _hemisphere(48)
    a = M.thin_film_rgb(n, thickness_nm=250.0)
    b = M.thin_film_rgb(n, thickness_nm=520.0)
    assert a.shape == (48, 48, 3) and np.allclose(a[~m], 0.0)
    assert float(np.abs(a[m] - b[m]).mean()) > 0.01           # 厚みで色が動く


def test_normalmap_shape_is_fail_closed():
    """点群の (N,3) 法線を渡したら通してはいけない(normalmap と normals は別の型)。"""
    pts = np.random.default_rng(0).normal(size=(64, 3))
    for fn in (M.grating_rgb, M.thin_film_rgb, M.ward_anisotropic):
        with pytest.raises(ValueError):
            fn(pts)


def test_zero_direction_is_rejected():
    n, _ = _hemisphere(16)
    with pytest.raises(ValueError):
        M.ward_anisotropic(n, light=(0.0, 0.0, 0.0))
    with pytest.raises(ValueError):
        M.ward_anisotropic(n, alpha_x=0.0)
