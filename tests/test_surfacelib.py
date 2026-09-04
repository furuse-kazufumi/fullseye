"""surfacelib(金属・ガラス以外の素材と表面処理)の単体テスト。

契約(退化ケースと保存則で固定):
  * Oren–Nayar は σ=0 で **Lambert に厳密一致**し、σ>0 では端(terminator)が明るくなる。
  * 上塗りは**エネルギーを作らない**: 上塗りを強くすると下地の寄与が単調に減る。
  * 布の縁光沢は鏡面と**逆**に、正面で 0・縁で最大。
  * 濡れは拡散を暗くする(乾き < 濡れ ではなく 濡れ < 乾き)。
  * 腐食マスクの面積率は指定した coverage に一致する(分位点で決めているため)。
  * すりガラスの直進 + 拡散 = 透明板の透過率(エネルギー保存)。
  * 法線を作る op はすべて単位ベクトルを返す。
"""
import numpy as np
import pytest

import glassmirror
import surfacelib as S


def _hemisphere(n=96):
    y, x = np.mgrid[-1:1:n * 1j, -1:1:n * 1j]
    r2 = x * x + y * y
    m = r2 < 1.0
    z = np.sqrt(np.maximum(1.0 - r2, 0.0))
    N = np.stack([x, y, z], -1) * m[..., None]
    return N, m


_L = np.array([0.3, 0.4, 0.87]) / np.linalg.norm([0.3, 0.4, 0.87])


# --------------------------------------------------------------------------- #
# 粗い拡散                                                                      #
# --------------------------------------------------------------------------- #
def test_oren_nayar_reduces_to_lambert_at_zero_roughness():
    N, m = _hemisphere()
    got = S.oren_nayar(N, _L, roughness_deg=0.0)
    unit = N / np.maximum(np.linalg.norm(N, axis=-1, keepdims=True), 1e-12)
    lam = np.clip(np.einsum("ijk,k->ij", unit, _L), 0.0, None) * m
    assert np.abs(got - lam).max() < 1e-12


def test_oren_nayar_flattens_the_terminator():
    """粗い面は端が平らに明るい(満月が円盤に見える理由)。"""
    N, m = _hemisphere()
    a = S.oren_nayar(N, _L, roughness_deg=0.0)
    b = S.oren_nayar(N, _L, roughness_deg=30.0)
    edge = m & (a > 0.01) & (a < 0.15)
    assert float(np.median((b / np.maximum(a, 1e-9))[edge])) > 1.2
    # 正面付近では差が小さい(粗さが効くのは端)
    front = m & (a > 0.9)
    assert float(np.median((b / np.maximum(a, 1e-9))[front])) < 1.1


def test_oren_nayar_validation():
    N, _ = _hemisphere(16)
    with pytest.raises(ValueError):
        S.oren_nayar(N, _L, roughness_deg=120.0)
    with pytest.raises(ValueError):
        S.oren_nayar(N, (0.0, 0.0, 0.0))


# --------------------------------------------------------------------------- #
# 上塗り                                                                        #
# --------------------------------------------------------------------------- #
def test_clearcoat_attenuates_the_base_monotonically():
    """★ 上塗りで反射した分だけ下地に届く光が減る。掛けないと足すほど明るくなる。"""
    N, m = _hemisphere()
    base = np.array([0.6, 0.2, 0.2])
    prev = None
    for coat in (0.0, 0.25, 0.5, 1.0):
        # 鏡面項は下地の色に依らないので、下地 0 の画像を引けば**下地の寄与だけ**が残る
        # (領域で切り分けようとすると、粗い上塗りのローブが全面に届いていて分離できない
        #  —— 最初はそれで落ちた)。
        img = S.clearcoat_shade(base, N, _L, coat=coat, coat_roughness=0.6)
        spec = S.clearcoat_shade(np.zeros(3), N, _L, coat=coat, coat_roughness=0.6)
        contribution = float((img - spec)[m].sum())
        if prev is not None:
            assert contribution < prev, (coat, contribution, prev)
        prev = contribution


def test_clearcoat_shape_and_validation():
    N, m = _hemisphere(32)
    img = S.clearcoat_shade(np.array([0.5, 0.5, 0.5]), N, _L)
    assert img.shape == N.shape and np.all(img >= 0.0)
    assert np.allclose(img[~m], 0.0)
    with pytest.raises(ValueError):
        S.clearcoat_shade(np.zeros((8, 8, 3)), N, _L)     # 形が合わない
    with pytest.raises(ValueError):
        S.clearcoat_shade(np.array([0.5, 0.5, 0.5]), N, _L, coat=2.0)


def test_metallic_flakes_scale_with_density():
    lo = S.metallic_flake_normals((128, 128), density=0.02, seed=1)
    hi = S.metallic_flake_normals((128, 128), density=0.20, seed=1)
    tilted_lo = float((np.abs(lo[..., 2]) < 0.999).mean())
    tilted_hi = float((np.abs(hi[..., 2]) < 0.999).mean())
    assert tilted_hi > 3.0 * tilted_lo
    for f in (lo, hi):
        assert np.allclose(np.linalg.norm(f, axis=-1), 1.0, atol=1e-12)


# --------------------------------------------------------------------------- #
# 布                                                                           #
# --------------------------------------------------------------------------- #
def test_sheen_peaks_at_the_rim_not_the_centre():
    """★ 鏡面とは逆。Phong では出せない布の見え方。"""
    N, m = _hemisphere()
    sh = S.sheen_shade(N, _L)
    ndv = np.abs(N[..., 2])
    centre = float(sh[m & (ndv > 0.95)].mean())
    rim = float(sh[m & (ndv < 0.35)].mean())
    assert rim > 100.0 * max(centre, 1e-9), (centre, rim)


def test_weave_has_two_orthogonal_periods():
    w = S.weave_normals((128, 128), warp_px=8.0, weft_px=16.0, depth=0.3)
    assert np.allclose(np.linalg.norm(w, axis=-1), 1.0, atol=1e-12)
    fx = np.abs(np.fft.rfft(w[64, :, 0] - w[64, :, 0].mean()))
    fy = np.abs(np.fft.rfft(w[:, 64, 1] - w[:, 64, 1].mean()))
    kx = int(fx.argmax())
    ky = int(fy.argmax())
    assert kx == pytest.approx(128 / 8.0, abs=1)          # 経糸の周期
    assert ky == pytest.approx(128 / 16.0, abs=1)         # 緯糸の周期
    with pytest.raises(ValueError):
        S.weave_normals((16, 16), warp_px=0.0)


# --------------------------------------------------------------------------- #
# 木                                                                           #
# --------------------------------------------------------------------------- #
def test_wood_grain_modulates_and_gives_a_fibre_direction():
    mod, t = S.wood_grain((96, 96), ring_px=12.0, angle_deg=20.0)
    assert mod.shape == (96, 96) and 0.0 <= mod.min() and mod.max() <= 1.0
    assert float(mod.std()) > 0.1                          # 木目がある
    assert np.allclose(np.linalg.norm(t, axis=-1), 1.0, atol=1e-12)
    flat, _ = S.wood_grain((96, 96), ring_px=12.0, wobble=0.0)
    assert float(flat.std()) > 0.1                         # うねり 0 でも年輪は出る
    with pytest.raises(ValueError):
        S.wood_grain((16, 16), ring_px=0.0)


# --------------------------------------------------------------------------- #
# 状態                                                                          #
# --------------------------------------------------------------------------- #
def test_wet_surfaces_get_darker():
    dry = np.array([0.5, 0.4, 0.3])
    wet = S.wetness(dry, 1.0)
    assert np.all(wet < dry), (dry, wet)
    assert np.allclose(S.wetness(dry, 0.0), dry)           # 乾きは恒等
    mid = S.wetness(dry, 0.5)
    assert np.all(mid < dry) and np.all(mid > wet)         # 単調
    with pytest.raises(ValueError):
        S.wetness(dry, 1.0, ior=0.9)


def test_corrosion_coverage_matches_the_request():
    for cov in (0.1, 0.3, 0.6):
        m = S.corrosion_mask((160, 160), coverage=cov, seed=2)
        assert float((m > 0.5).mean()) == pytest.approx(cov, abs=0.02), cov
    assert np.allclose(S.corrosion_mask((32, 32), coverage=0.0), 0.0)


def test_subsurface_keeps_light_where_lambert_is_zero():
    N, m = _hemisphere()
    ndl = np.einsum("ijk,k->ij", N / np.maximum(np.linalg.norm(N, axis=-1, keepdims=True), 1e-12), _L)
    shadow = m & (ndl < -0.1)
    ss = S.subsurface_approx(N, _L, thickness=0.8)
    assert float(ss[shadow].mean()) > 0.05                 # 影側にも光が回る
    thin = S.subsurface_approx(N, _L, thickness=0.0)
    assert float(ss[shadow].mean()) > float(thin[shadow].mean())


# --------------------------------------------------------------------------- #
# すりガラス                                                                    #
# --------------------------------------------------------------------------- #
def test_frosted_glass_conserves_energy():
    for r in (0.0, 0.3, 0.8):
        spec, diff = S.rough_transmission(1.0, r)
        total = float(spec) + float(diff)
        assert total == pytest.approx(float(glassmirror.slab_transmittance(1.0, 1.0, 1.5, 0.0, 0.0)),
                                      rel=1e-12), r
    s0, d0 = S.rough_transmission(1.0, 0.0)
    assert float(d0) == pytest.approx(0.0, abs=1e-12)      # 粗さ 0 は完全に直進
    s1, d1 = S.rough_transmission(1.0, 1.0)
    assert float(s1) < float(s0)                           # 粗いほど直進が減る
    with pytest.raises(ValueError):
        S.rough_transmission(1.0, 1.5)


def test_material_catalog_orders_the_coats():
    cat = S.material_catalog()
    assert set(cat) == set(S.MATERIALS)
    assert cat["paper"]["coat"] < cat["plastic"]["coat"] < cat["car_paint"]["coat"]
    assert cat["concrete"]["roughness_deg"] > cat["paper"]["roughness_deg"] > cat["plastic"]["roughness_deg"]
    assert cat["velvet"]["sheen"] > cat["fabric"]["sheen"] > cat["plastic"]["sheen"]
    cat["paper"]["coat"] = 9.0
    assert S.material_catalog()["paper"]["coat"] != 9.0    # 返りは複製
