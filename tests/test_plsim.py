# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""plsim(PL 像のキャリア拡散 PSF)の門。

採点は「絵がそれらしいか」ではなく、**閉形式の真値に合うか**: 拡散 PSF の総和が 1
(= G·τ)で半質量半径が L に比例、一様励起で厳密に一様、影の溝は格子の閉形式
``1 − 2ρ^{m+1}/(1+ρ)`` に 1e-9 で一致、1 画素の沈みは ``k/(k + L²(1−ρ²)/ρ)`` に一致。
どれも画像を見ないで数で通せる(「走った」≠「意味のある出力」を避けるため、構造の有無も見る)。
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import plsim as P                                                 # noqa: E402


# --------------------------------------------------------------------------- #
# 1. 拡散 PSF(グリーン関数)                                                    #
# --------------------------------------------------------------------------- #
def test_the_diffusion_psf_sums_to_one_and_peaks_at_the_centre():
    """総和 = G·τ(= 1)。8L で切った欠けは 8·K₁(8) ≈ 1.2e-3 以下、中心が最大、対称。"""
    for L in (3.0, 6.0, 12.0):
        k = P.pl_diffusion_psf(L)
        c = k.shape[0] // 2
        assert k.shape[0] == 2 * int(np.ceil(8 * L)) + 1
        assert 0.99 < float(k.sum()) <= 1.0 + 1e-9, "L=%g: sum %.5f" % (L, k.sum())
        assert float(k[c, c]) == float(k.max())
        assert (k > 0).all()
        assert np.allclose(k, k.T) and np.allclose(k, k[::-1, ::-1])


def test_the_half_mass_radius_scales_with_L():
    """半分の質量が入る半径 r½ = 1.2572·L(1 − x·K₁(x) = 1/2 の根)。L を 2 倍で 2 倍。"""
    from scipy import optimize, special

    root = optimize.brentq(lambda x: 1.0 - x * special.k1(x) - 0.5, 0.1, 5.0)
    assert root == pytest.approx(P.HALF_MASS_RADIUS_OVER_L, abs=1e-9)
    got = []
    for L in (10.0, 20.0):
        k = P.pl_diffusion_psf(L)
        c = k.shape[0] // 2
        y, x = np.mgrid[-c:c + 1, -c:c + 1]
        r = np.hypot(x, y)
        rh = optimize.brentq(lambda R: k[r <= R].sum() - 0.5, 0.5, 8 * L)
        got.append(rh)
        assert rh / L == pytest.approx(P.HALF_MASS_RADIUS_OVER_L, abs=0.03), \
            "L=%g: r_half/L = %.4f" % (L, rh / L)
    assert got[1] / got[0] == pytest.approx(2.0, abs=0.05)


# --------------------------------------------------------------------------- #
# 2. PL 像の合成(定常拡散方程式の厳密解)                                        #
# --------------------------------------------------------------------------- #
def test_uniform_excitation_renders_uniform():
    """一様励起・欠陥なし → 厳密に 1(Neumann 境界なので端も暗くならない)。"""
    u = P.pl_image_simulate(np.ones((12, 17)), diffusion_length_px=5.0)
    assert u.shape == (12, 17) and u.dtype == np.float64
    assert float(np.ptp(u)) < 1e-10
    assert float(u.mean()) == pytest.approx(1.0, abs=1e-10)


def test_a_shadow_groove_matches_the_grid_closed_form_and_the_continuum():
    """幅 w = 2m+1 の影の溝: 中心のコントラストは格子で厳密に 1 − 2ρ^{m+1}/(1+ρ)、
    連続の 1 − e^{−w/2L} には L ≥ 10 で 3 % 以内。w ≪ L で ≈ w/2L と消える。"""
    for L in (3.0, 10.0, 40.0):
        for w in (1, 3, 9):
            W = max(401, int(20 * L) | 1)
            g = np.ones((1, W)); c = W // 2; m = (w - 1) // 2
            g[0, c - m:c + m + 1] = 0.0
            u = P.pl_image_simulate(g, diffusion_length_px=L)
            t = P.pl_groove_visibility(w, L)
            sim = 1.0 - float(u[0, c])
            assert sim == pytest.approx(t["contrast_shadow_grid"], abs=1e-9), (L, w)
            if L >= 10:
                assert sim == pytest.approx(t["contrast_shadow"], rel=0.03), (L, w)
    # 消え方: 同じ w=1 で L を 4 倍にすると中心のコントラストは約 1/4
    c10 = P.pl_groove_visibility(1.0, 10.0)["contrast_shadow"]
    c40 = P.pl_groove_visibility(1.0, 40.0)["contrast_shadow"]
    assert c10 / c40 == pytest.approx(4.0, rel=0.03)


def test_a_one_pixel_sink_matches_the_grid_closed_form_and_donolato():
    """1 画素の沈み(再結合率 k): 格子で厳密に k/(k + L²(1−ρ²)/ρ)、連続では SL/(SL+2D)。
    L が長いほど**深く**見える(影と逆向き)。"""
    prev = -1.0
    for L in (3.0, 10.0, 40.0):
        k0 = 5.0
        W = int(20 * L) | 1
        g = np.ones((1, W)); k = np.zeros((1, W)); c = W // 2
        k[0, c] = k0
        u = P.pl_image_simulate(g, k, diffusion_length_px=L)
        rho = P._grid_rho(L)
        exact = k0 / (k0 + L * L * (1 - rho * rho) / rho)
        sim = 1.0 - float(u[0, c])
        assert sim == pytest.approx(exact, abs=1e-9), L
        s = k0 / (L * L)                                   # s = k·w/L²(w = 1)
        cont = P.pl_groove_visibility(1.0, L, sink_velocity=s)["contrast_sink"]
        assert sim == pytest.approx(cont, rel=0.02), L
    # 物理の再結合速度 s を固定して L を伸ばすと、沈みは深くなる
    for L in (5.0, 10.0, 20.0, 40.0):
        c = P.pl_groove_visibility(1.0, L, sink_velocity=0.2)["contrast_sink"]
        assert c > prev
        prev = c


def test_superposition_and_the_optical_psf_and_noise_knobs():
    """線形なので励起の重ね合わせは像の重ね合わせ。光学 PSF は総量を保ち、雑音は種で再現。"""
    L = 6.0
    g1 = np.ones((1, 101)); g1[0, 30] = 0.0
    g2 = np.ones((1, 101)); g2[0, 70] = 0.0
    u1 = P.pl_image_simulate(g1, diffusion_length_px=L)
    u2 = P.pl_image_simulate(g2, diffusion_length_px=L)
    u12 = P.pl_image_simulate(g1 + g2 - 1.0, diffusion_length_px=L)
    assert np.allclose(u1 + u2 - 1.0, u12, atol=1e-9)
    g = np.ones((24, 24)); g[10:14, 10:14] = 0.0
    sharp = P.pl_image_simulate(g, diffusion_length_px=3.0)
    blur = P.pl_image_simulate(g, diffusion_length_px=3.0, optical_psf_px=1.5)
    assert float(blur.sum()) == pytest.approx(float(sharp.sum()), rel=1e-3)
    assert float(np.ptp(blur)) < float(np.ptp(sharp))
    n1 = P.pl_image_simulate(np.ones((16, 16)), noise_rel=0.02, seed=3)
    n2 = P.pl_image_simulate(np.ones((16, 16)), noise_rel=0.02, seed=3)
    assert np.array_equal(n1, n2) and float(n1.std()) == pytest.approx(0.02, rel=0.4)


def test_visibility_table_closed_forms_and_boundaries():
    """表の閉形式: 影 1 − e^{−w/2L}、沈み sL/(sL+2)、FWHM、CNR、L* の両向き。"""
    t = P.pl_groove_visibility(2.0, 20.0, sink_velocity=0.5, noise_rel=0.02, cnr_min=1.0)
    assert t["contrast_shadow"] == pytest.approx(1 - np.exp(-2 / 40))
    assert t["contrast_sink"] == pytest.approx(10 / 12)
    assert t["fwhm_sink_px"] == pytest.approx(2 * 20 * np.log(2))
    assert t["contrast_shadow_grid"] is None                         # 偶数幅は格子式なし
    assert t["cnr_shadow"] == pytest.approx(t["contrast_shadow"] / 0.02)
    # L*: 影は L > L* で消え、沈みは L < L* で消える(定義どおりに CNR = cnr_min)
    Ls = t["L_star_shadow_px"]
    assert P.pl_groove_visibility(2.0, Ls, noise_rel=0.02)["cnr_shadow"] == pytest.approx(1.0)
    Lk = t["L_star_sink_px"]
    assert P.pl_groove_visibility(2.0, Lk, sink_velocity=0.5, noise_rel=0.02)["cnr_sink"] \
        == pytest.approx(1.0)
    assert P.pl_groove_visibility(2.0, 2 * Ls, noise_rel=0.02)["visible_shadow"] is False
    assert P.pl_groove_visibility(2.0, 0.5 * Lk, sink_velocity=0.5,
                                  noise_rel=0.02)["visible_sink"] is False
    # 沈みの速度 0 には境界が無い: inf でなく None(探針の nonfinite 契約、2026-10-13)
    t0 = P.pl_groove_visibility(2.0, 20.0, noise_rel=0.02)
    assert t0["L_star_sink_px"] is None and t0["contrast_sink"] == 0.0 and t0["visible_sink"] is False
    assert all(np.isfinite(v) for v in t0.values() if isinstance(v, float))
    # 影の FWHM は w ≪ L で 2L·ln2 に近づく
    f = P.pl_groove_visibility(1.0, 50.0)["fwhm_shadow_px"]
    assert f == pytest.approx(2 * 50 * np.log(2), rel=0.02)


def test_fail_closed_on_bad_input():
    """不正入力は黙って通さず明示拒否(fail-closed)。"""
    with pytest.raises(ValueError):
        P.pl_diffusion_psf(0.0)
    with pytest.raises(ValueError):
        P.pl_diffusion_psf(4.0, size=10)                       # 偶数
    with pytest.raises(ValueError):
        P.pl_image_simulate(np.ones((4, 4, 3)))                # 3-D
    with pytest.raises(ValueError):
        P.pl_image_simulate(np.full((4, 4), np.nan))           # 非有限
    with pytest.raises(ValueError):
        P.pl_image_simulate(np.ones((4, 4)), np.ones((5, 4)))  # 形が違う
    with pytest.raises(ValueError):
        P.pl_image_simulate(-np.ones((4, 4)))                  # 負の励起
    with pytest.raises(ValueError):
        P.pl_image_simulate(np.ones((4, 4)), diffusion_length_px=-1.0)
    with pytest.raises(ValueError):
        P.pl_groove_visibility(0.0, 5.0)
    with pytest.raises(ValueError):
        P.pl_groove_visibility(1.0, 5.0, noise_rel=0.0)
    with pytest.raises(ValueError):
        P.pl_image_simulate(np.zeros((0, 4)))                  # 空


# --------------------------------------------------------------------------- #
# 3. 台帳と公開経路(登録面を 1 つ落とすと静かに消える)                        #
# --------------------------------------------------------------------------- #
def test_the_ledger_lists_the_ops_and_nothing_is_missing():
    import opsgenerative as og

    assert set(og.list_ops("pl")) == set(P.__all__)
    assert og.missing() == []
    assert "pl" in og.categories()


def test_the_ops_are_reachable_from_the_public_tier():
    import fullseye as fs

    for name in P.__all__:
        assert hasattr(fs.ledger, name), name
    assert fs.ledger.pl_image_simulate(np.ones((8, 8))).shape == (8, 8)
    assert fs.ledger.pl_diffusion_psf(2.0).shape == (33, 33)
    assert "contrast_shadow" in fs.ledger.pl_groove_visibility()


def test_the_typed_catalog_declares_the_ops():
    import typed_catalog as tc

    rows = {r[0]: r for r in tc.catalog() if r[0] in P.__all__}
    assert set(rows) == set(P.__all__)
    assert rows["pl_image_simulate"][2:4] == (["image2d"], "image2d")
    assert rows["pl_diffusion_psf"][2:4] == ([], "image2d")
    assert rows["pl_groove_visibility"][2:4] == ([], "table")
    assert all(rows[n][1] == "generative" for n in P.__all__)


def test_the_fuzzer_can_actually_run_the_ops():
    """★「登録したのに一度も計算しない」を避ける。image2d の種で実際に走ること。"""
    sys.path.insert(0, str(ROOT / "tools"))
    import chain_fuzz as cf

    seed = cf.make_generators()["image2d"](np.random.default_rng(0))
    assert cf.TYPE_CHECKS["image2d"](P.pl_image_simulate(seed))
    assert cf.TYPE_CHECKS["image2d"](P.pl_diffusion_psf())
    assert cf.TYPE_CHECKS["table"](P.pl_groove_visibility())


def test_the_op_summaries_have_matching_fingerprints():
    """op_summary.json の指紋が docstring の 1 行目と一致する(古い訳が出ないため)。"""
    sys.path.insert(0, str(ROOT / "tools"))
    import json
    import opdocs

    d = json.loads((ROOT / "docs" / "i18n" / "op_summary.json").read_text(encoding="utf-8"))
    for name in P.__all__:
        line = getattr(P, name).__doc__.strip().splitlines()[0]
        e = d["summaries"]["generative/" + name]
        assert e["fp"] == opdocs.fingerprint(line), name
        for lang in ("en", "zh", "tw", "ko", "de", "hi"):
            assert e[lang].strip(), (name, lang)
