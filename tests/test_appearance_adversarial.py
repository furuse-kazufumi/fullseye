"""外観 op 族(matappear / glassmirror / metalfinish / surfacelib / opassist)の敵対的検証。

**この回で新しく作った層に対して、まだ一度も掛けていない検査**だけを集めた。
既存のテストは「自分が期待した振る舞い」を固定しているので、ここでは逆に
**自分が確かめていない不変量**を突く:

  A. 相反性(Helmholtz)  — 光源と視線を入れ替えても BRDF は変わらないはず
  B. 極限での一致       — 金属 Fresnel は k→0 で誘電体 Fresnel に一致するはず
  C. エネルギー         — 無損失界面は R + T = 1 のはず
  D. 線形性             — 分光反射率を 2 倍したら RGB も 2 倍のはず
  E. 敵対入力           — NaN / Inf / 空 / 変な dtype で**素の例外を漏らさない**はず
  F. 決定性             — 乱数を使う op は seed が同じなら同じ結果のはず
  G. 補助層の正直さ     — `accepted_sorts` の "works" が中身のない通過を隠していないか
  H. 導線の実行可能性   — `op_path` が返す連鎖が本当に繋がるか

落ちたものは「実装が間違っている」か「不変量の理解が間違っている」かのどちらかで、
どちらでも収穫がある。
"""
import numpy as np
import pytest

import glassmirror as G
import matappear as M
import metalfinish as MF
import opassist as A
import surfacelib as S


def _hemi(n=48):
    y, x = np.mgrid[-1:1:n * 1j, -1:1:n * 1j]
    r2 = x * x + y * y
    m = r2 < 1.0
    z = np.sqrt(np.maximum(1.0 - r2, 0.0))
    return np.stack([x, y, z], -1) * m[..., None], m


_L = np.array([0.31, 0.44, 0.84]) / np.linalg.norm([0.31, 0.44, 0.84])
_V = np.array([-0.22, 0.18, 0.96]) / np.linalg.norm([-0.22, 0.18, 0.96])


# --------------------------------------------------------------------------- #
# A. 相反性(Helmholtz reciprocity)                                             #
# --------------------------------------------------------------------------- #
def test_ward_lobe_is_reciprocal():
    """光源と視線を入れ替えても分布関数は同じ(微小面モデルの基本性質)。"""
    N, m = _hemi()
    a = MF.matappear.ward_anisotropic(N, light=_L, view=_V, alpha_x=0.3, alpha_y=0.05)
    b = MF.matappear.ward_anisotropic(N, light=_V, view=_L, alpha_x=0.3, alpha_y=0.05)
    both = m & (a > 0) & (b > 0)
    assert both.any()
    rel = np.abs(a[both] - b[both]) / np.maximum(np.abs(a[both]), 1e-12)
    assert float(rel.max()) < 1e-9, float(rel.max())


def test_oren_nayar_is_reciprocal():
    """粗い拡散も相反(A + B·cosΔφ·sinα·tanβ は α, β の入れ替えに対して対称)。"""
    N, m = _hemi()
    a = S.oren_nayar(N, light=_L, view=_V, roughness_deg=30.0)
    b = S.oren_nayar(N, light=_V, view=_L, roughness_deg=30.0)
    # 拡散項は cosθi が掛かるので、その分を割って比べる(BRDF そのものを比べる)
    unit = N / np.maximum(np.linalg.norm(N, axis=-1, keepdims=True), 1e-12)
    ndl = np.clip(np.einsum("ijk,k->ij", unit, _L), 0, None)
    ndv = np.clip(np.einsum("ijk,k->ij", unit, _V), 0, None)
    ok = m & (ndl > 0.05) & (ndv > 0.05)
    fa = a[ok] / ndl[ok]
    fb = b[ok] / ndv[ok]
    rel = np.abs(fa - fb) / np.maximum(np.abs(fa), 1e-12)
    assert float(np.max(rel)) < 1e-9, float(np.max(rel))


# --------------------------------------------------------------------------- #
# B. 極限での一致(別々に実装した式が同じ物理に収束するか)                        #
# --------------------------------------------------------------------------- #
def test_conductor_fresnel_reduces_to_the_dielectric_one_as_k_goes_to_zero():
    """★ 独立に書いた 2 つの式が同じ物理に落ちるか ―― 片方だけ間違っていたら気づけない。"""
    ci = np.cos(np.radians(np.linspace(0.0, 85.0, 40)))
    for n in (1.33, 1.5168, 2.4):
        for pol in ("unpolarized", "s", "p"):
            a = G.fresnel_conductor(ci, np.full_like(ci, n), np.zeros_like(ci), pol)
            b = G.fresnel_dielectric(ci, 1.0, n, pol)
            assert np.allclose(a, b, atol=1e-9), (n, pol, float(np.abs(a - b).max()))


def test_thin_film_at_zero_thickness_equals_the_interface_formula():
    """膜厚 0 の薄膜は「界面 1 枚」に一致する(斜入射でも)。"""
    ang = np.radians(np.linspace(0.0, 80.0, 25))
    ci = np.cos(ang)
    a = M.thin_film_reflectance(np.full_like(ci, 550.0), 0.0, n_film=1.33,
                                n_sub=1.5, cos_theta=ci)
    b = G.fresnel_dielectric(ci, 1.0, 1.5)
    assert np.allclose(a, b, atol=1e-12), float(np.abs(a - b).max())


# --------------------------------------------------------------------------- #
# C. エネルギー保存                                                             #
# --------------------------------------------------------------------------- #
def test_single_interface_conserves_energy():
    """無損失界面は R + T = 1。T は面積と立体角の比を含むので、素朴に (1−R) と
    比べるのではなく、フレネルの透過係数から作った T を使って確かめる。"""
    ang = np.radians(np.linspace(0.0, 80.0, 30))
    n1, n2 = 1.0, 1.5168
    ci = np.cos(ang)
    st = n1 / n2 * np.sin(ang)
    ct = np.sqrt(np.maximum(1.0 - st ** 2, 0.0))
    for pol in ("s", "p"):
        R = G.fresnel_dielectric(ci, n1, n2, pol)
        if pol == "s":
            t = 2 * n1 * ci / (n1 * ci + n2 * ct)
        else:
            t = 2 * n1 * ci / (n2 * ci + n1 * ct)
        T = (n2 * ct) / (n1 * ci) * t ** 2
        assert np.allclose(R + T, 1.0, atol=1e-12), (pol, float(np.abs(R + T - 1).max()))


def test_metal_reflectance_never_exceeds_one():
    """金属でも R > 1 にならない(複素平方根の枝を取り違えると簡単に破れる)。"""
    ang = np.cos(np.radians(np.linspace(0.0, 89.9, 60)))
    w = np.linspace(380.0, 780.0, 41)
    for metal in G.METALS:
        n, k = G.metal_optical_constants(metal, w)
        R = G.fresnel_conductor(ang[:, None], n[None, :], k[None, :])
        assert np.all(R >= 0.0) and np.all(R <= 1.0 + 1e-12), (metal, float(R.max()))


# --------------------------------------------------------------------------- #
# D. 線形性                                                                     #
# --------------------------------------------------------------------------- #
def test_spectrum_to_srgb_is_linear_in_reflectance():
    w = np.linspace(380.0, 780.0, 81)
    r = 0.2 + 0.6 * np.sin(np.linspace(0, 3, 81)) ** 2
    a = M.spectrum_to_srgb(w, r)
    b = M.spectrum_to_srgb(w, 2.0 * r)
    c = M.spectrum_to_srgb(w, r * 0.0)
    assert np.allclose(b, 2.0 * a, rtol=1e-12)
    assert np.allclose(c, 0.0, atol=1e-12)
    # 加法性: 2 つの分光の和 → RGB の和
    r2 = np.linspace(0.1, 0.9, 81)
    assert np.allclose(M.spectrum_to_srgb(w, r + r2),
                       a + M.spectrum_to_srgb(w, r2), rtol=1e-12)


# --------------------------------------------------------------------------- #
# E. 敵対入力(素の例外を漏らさない / 黙って NaN を返さない)                      #
# --------------------------------------------------------------------------- #
_HOSTILE = {
    "nan": lambda shape: np.full(shape, np.nan),
    "inf": lambda shape: np.full(shape, np.inf),
    "empty": lambda shape: np.zeros((0,) + tuple(shape[1:])),
    "int": lambda shape: np.ones(shape, dtype=np.int32),
    "f32": lambda shape: np.ones(shape, dtype=np.float32),
}


@pytest.mark.parametrize("bad", sorted(_HOSTILE))
def test_normalmap_ops_are_fail_closed_on_hostile_input(bad):
    """NaN / Inf / 空 / 整数 / float32 を法線マップとして渡す。

    許されるのは (1) ValueError で断る (2) 有限の値を返す のどちらか。
    **素の TypeError/IndexError を漏らす**か **黙って NaN を返す**のは不合格。
    """
    data = _HOSTILE[bad]((16, 16, 3))
    ops = [lambda d: M.ward_anisotropic(d), lambda d: M.grating_rgb(d),
           lambda d: M.thin_film_rgb(d), lambda d: S.oren_nayar(d),
           lambda d: S.sheen_shade(d), lambda d: S.subsurface_approx(d),
           lambda d: MF.micro_normals(d), lambda d: MF.blast_normals(d),
           lambda d: MF.finish_shade(d)]
    for fn in ops:
        try:
            out = fn(data)
        except ValueError:
            continue                                    # 明示拒否 = 合格
        except Exception as exc:                        # noqa: BLE001
            pytest.fail("%s で素の %s が漏れた: %s" % (bad, type(exc).__name__, exc))
        arr = np.asarray(out, dtype=np.float64)
        assert arr.size == 0 or np.isfinite(arr).all(), (bad, fn, "NaN/Inf を返した")


def test_scalar_ops_reject_nonsense_numbers():
    for fn, args in ((G.fresnel_dielectric, (np.nan, 1.0, 1.5)),
                     (G.beer_lambert_transmittance, (np.nan, 0.1)),
                     (M.thin_film_reflectance, (np.array([np.nan]),)),
                     (M.cie_xyz_from_wavelength, (np.array([np.inf]),))):
        with pytest.raises(ValueError):
            fn(*args)


# --------------------------------------------------------------------------- #
# F. 決定性                                                                     #
# --------------------------------------------------------------------------- #
def test_random_based_ops_are_deterministic_per_seed():
    N, _ = _hemi(32)
    pairs = [
        (lambda: MF.blast_normals(N, grain=0.05, seed=7)),
        (lambda: S.corrosion_mask((64, 64), coverage=0.3, seed=7)),
        (lambda: S.metallic_flake_normals((64, 64), density=0.1, seed=7)),
        (lambda: S.wood_grain((64, 64), seed=7)[0]),
        (lambda: MF.roughness_field((64, 64), "linear", patchiness=0.5, seed=7)),
    ]
    for make in pairs:
        assert np.array_equal(make(), make())
    # seed を変えたら変わる(固定値を返しているだけではない)
    assert not np.array_equal(S.corrosion_mask((64, 64), coverage=0.3, seed=1),
                              S.corrosion_mask((64, 64), coverage=0.3, seed=2))


# --------------------------------------------------------------------------- #
# G. 補助層の正直さ                                                             #
# --------------------------------------------------------------------------- #
def test_accepted_sorts_works_verdict_is_not_empty_success():
    """★ "works" が「例外が出なかっただけ」を隠していないか。

    通ったと言うからには、返りが**入力の大きさに応じた中身**を持つべき。
    要素数 0 や、入力を無視した固定サイズを返しているなら "works" は嘘になる。
    """
    for op in ("fresnel_dielectric", "beer_lambert_transmittance", "thin_film_reflectance"):
        verdicts = A.accepted_sorts(op)
        seeds = A._probe_seeds()
        args, kwargs = A.sample_input(op)
        for sort, verdict in verdicts.items():
            if verdict != "works":
                continue
            call = list(args)
            call[0] = seeds[sort]
            out = np.asarray(A._ledger_entry(op)[1]["func"](*call, **kwargs))
            assert out.size > 0, (op, sort)
            assert out.size == np.asarray(seeds[sort]).size or out.shape[:1] == np.shape(seeds[sort])[:1], \
                (op, sort, out.shape, np.shape(seeds[sort]))


def test_preflight_does_not_fire_on_the_documented_good_setup():
    """警告が出っぱなしだと誰も読まなくなる。正しい配置では黙ること。"""
    good = A.preflight("grating_rgb", {"tangent": (1, 0, 0), "light": (0.0, 0.55, 0.83),
                                       "view": (0, 0, 1)})
    assert good == []
    for op in ("thin_film_reflectance", "slab_transmittance", "corrosion_mask"):
        assert A.preflight(op) == [], op        # 既定値は「まともな設定」であるべき


# --------------------------------------------------------------------------- #
# H. 導線の実行可能性                                                           #
# --------------------------------------------------------------------------- #
def test_op_path_chains_are_type_consistent():
    """`op_path` が出した連鎖が、台帳の型の上で本当に繋がっているか。"""
    for src, dst in (("normalmap", "rgbimage"), ("image2d", "depth"), ("points", "mesh")):
        for chain in A.path(src, dst)[:3]:
            cur = src
            for name in chain:
                _mod, entry = A._ledger_entry(name)
                assert cur in (entry.get("in") or []), (src, dst, chain, name, cur)
                cur = entry.get("out")
            assert cur == dst, (src, dst, chain, cur)
