# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""examples/poc_photoelasticity.py を光弾性の族の op で書き直した回の門(2026-11-04)。

初版(2026-09-06)は応力場の閉形式・主応力差・画素ごとの位相子の 4x4・平面偏光の強度式を
PoC の中に手書きしていた。書き直した版は ``photoelastic.py`` の op を呼ぶ。この試験は
**初版の手書きの計算をそのまま参照として持ち**、op を使う新版の値と突き合わせる。

参照は新版の関数を 1 つも呼ばない(``fs.mueller_element`` / ``fs.mueller_apply`` と numpy だけ)。
新版は ``photoelastic.py`` の op を呼ぶ。両辺は別の実装で、同じ関数を 2 回呼んで一致させる門ではない。

許容差の根拠(どれも「同じ式を違う順・違う単位で計算した丸め」の幅):

* 応力・位相差: 参照は mm・N・MPa、op は m・N・Pa で計算する。1e3 の係数が式の中で
  何度も掛かる(r1⁴ に 1e-12、k に 1e3)ので、相対で数 ulp(1e-15 台)ずれる。主応力差は
  √((σx-σy)² + 4τ²) の差の取り方が両者で違い(op は hypot)、場の最大値に対して
  1e-12 を許す(実測 1e-15 台)。
* 等傾角: atan2 の引数が上と同じ桁でずれる。主応力差が小さい点ほど角度は敏感だが、
  評価域(半径 0.9R)の主応力差の最小は最大の 1.1 %(0.25 / 22.0 MPa)あるので 1e-10 rad で
  足りる(実測 8.9e-16)。
* 強度・Stokes: 値は 0〜1 で、op の閉形式と 4x4 の積の丸めの差。1e-12(実測 1e-16 台)。
* 各節の数値: 上の入力の差がそのまま伝わる。比較に使う閾値(0.05 rad、π/2、四捨五入)を
  またぐ画素が出ない限り一致する。割合は**一致する画素数**で比べる(差 0 画素)。
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

import fullseye as fs

ROOT = Path(__file__).resolve().parents[1]


def _load():
    path = ROOT / "examples" / "poc_photoelasticity.py"
    spec = importlib.util.spec_from_file_location("poc_photoelasticity_ops_gate", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def P():
    with pytest.MonkeyPatch.context() as mp:
        mp.delenv("FULLSEYE_FIGURE_DIR", raising=False)
        mp.setenv("FULLSEYE_FIGURES", "off")
        mod = _load()
        mod.run_out = mod.run()
        yield mod


# =========================================================================== #
# 初版(2026-09-06)の手書きの計算。式は初版のまま(コメントだけ短くした)。               #
# =========================================================================== #
R_MM, H_MM, P_N, F_SIGMA, NPIX = 25.0, 6.0, 500.0, 10.7, 257
PX_MM = 2.0 * R_MM / (NPIX - 1)
_YY, _XX = np.mgrid[0:NPIX, 0:NPIX].astype(np.float64)
X_MM = (_XX - (NPIX - 1) / 2.0) * PX_MM
Y_MM = ((NPIX - 1) / 2.0 - _YY) * PX_MM
IN_DISC = X_MM ** 2 + Y_MM ** 2 <= (R_MM * 0.90) ** 2


def legacy_disc_stress(x, y, p=P_N, r=R_MM, h=H_MM):
    """直径圧縮された円板の平面応力(閉形式)[MPa]。"""
    r1sq = np.maximum(x ** 2 + (r - y) ** 2, 1e-9)
    r2sq = np.maximum(x ** 2 + (r + y) ** 2, 1e-9)
    k = 2.0 * p / (np.pi * h)
    sxx = -k * (x ** 2 * (r - y) / r1sq ** 2 + x ** 2 * (r + y) / r2sq ** 2 - 1.0 / (2 * r))
    syy = -k * ((r - y) ** 3 / r1sq ** 2 + (r + y) ** 3 / r2sq ** 2 - 1.0 / (2 * r))
    txy = k * (x * (r - y) ** 2 / r1sq ** 2 - x * (r + y) ** 2 / r2sq ** 2)
    return sxx, syy, txy


def legacy_principal_difference(sxx, syy, txy):
    d = sxx - syy
    return np.sqrt(d * d + 4.0 * txy * txy), 0.5 * np.arctan2(2.0 * txy, d)


def legacy_build_fields():
    dsig, theta = legacy_principal_difference(*legacy_disc_stress(X_MM, Y_MM))
    return dsig, theta, 2.0 * np.pi * H_MM * dsig / F_SIGMA


def legacy_retarder_stack(delta, theta):
    """画素ごとの位相子 Mueller (H, W, 4, 4)。``theta`` は進相軸 [rad]。"""
    c2, s2 = np.cos(2 * theta), np.sin(2 * theta)
    cd, sd = np.cos(delta), np.sin(delta)
    m = np.zeros(delta.shape + (4, 4))
    m[..., 0, 0] = 1.0
    m[..., 1, 1] = c2 * c2 + s2 * s2 * cd
    m[..., 1, 2] = c2 * s2 * (1.0 - cd)
    m[..., 1, 3] = -s2 * sd
    m[..., 2, 1] = m[..., 1, 2]
    m[..., 2, 2] = s2 * s2 + c2 * c2 * cd
    m[..., 2, 3] = c2 * sd
    m[..., 3, 1] = s2 * sd
    m[..., 3, 2] = -c2 * sd
    m[..., 3, 3] = cd
    return m


def legacy_polariscope_image(delta, fast, analyser_deg=90.0):
    q1 = np.asarray(fs.mueller_element("quarter_wave", 45.0))
    q2 = np.asarray(fs.mueller_element("quarter_wave", -45.0))
    an = np.asarray(fs.mueller_element("polarizer", analyser_deg))
    s_in = np.asarray(fs.mueller_apply(q1, np.array([1.0, 1.0, 0.0, 0.0])))
    s = fs.mueller_apply(legacy_retarder_stack(delta, fast), s_in)
    return np.asarray(fs.mueller_apply(an @ q2, s))[..., 0]


def legacy_plane_polariscope(delta, theta, pol_deg=0.0):
    b = np.deg2rad(pol_deg)
    return np.sin(2.0 * (theta - b)) ** 2 * np.sin(delta / 2.0) ** 2


def legacy_emerging_stokes(delta, fast):
    return np.asarray(fs.mueller_apply(legacy_retarder_stack(delta, fast), np.array([1.0, 0.0, 0.0, 1.0])))


def legacy_sections():
    """初版の 2〜6 節が門で見ていた数値を、初版の手順のまま計算する。

    位相子の進相軸は**新版と同じ規約**(σ1 + 90°、C > 0)で渡す。初版は σ1 を進相軸に
    渡していた(所見 (b))。4 節の符号つき推定はその分だけ読み方を合わせる。
    """
    dsig, theta, delta = legacy_build_fields()
    fast = theta + np.pi / 2
    naive = P_N / (2 * R_MM * H_MM)
    m = IN_DISC & (np.abs(delta) < np.pi)
    err0 = float(np.mean(np.abs(naive - dsig[m])))
    # 3 節
    n_int = np.round(delta / (2 * np.pi))
    e3 = float(np.mean(np.abs(F_SIGMA * n_int / H_MM - dsig)[m]))
    # 4 節
    s_out = legacy_emerging_stokes(delta, fast)
    s1, s2, s3 = s_out[..., 1], s_out[..., 2], s_out[..., 3]
    i0, i1, i2, i3 = (legacy_plane_polariscope(delta, theta, b) for b in (0.0, 22.5, 45.0, 67.5))
    th_hat = 0.25 * np.arctan2(i3 - i1, i2 - i0)
    f_hat = th_hat + np.pi / 2
    d_hat = np.arctan2(s2 * np.cos(2 * f_hat) - s1 * np.sin(2 * f_hat), s3)
    # 初版そのまま(σ1 を進相軸に渡し、θ で読む)の符号つき推定。規約を変えても同じ δ になる。
    s_old = legacy_emerging_stokes(delta, theta)
    d_hat_orig = np.arctan2(s_old[..., 2] * np.cos(2 * th_hat) - s_old[..., 1] * np.sin(2 * th_hat),
                            s_old[..., 3])
    wrapped_true = np.mod(delta + np.pi, 2 * np.pi) - np.pi
    good = np.abs(np.mod(d_hat - wrapped_true + np.pi, 2 * np.pi) - np.pi) < 0.05
    abs_err = float(np.mean(np.abs(F_SIGMA * (np.abs(d_hat) / (2 * np.pi)) / H_MM - dsig)[m]))
    # 5 節
    n_true = delta / (2 * np.pi)
    gy, gx = np.gradient(n_true)
    aliased = IN_DISC & (1.0 / np.maximum(np.hypot(gx, gy), 1e-12) < 2.0)
    lowmod = IN_DISC & (np.hypot(s1, s2) < 0.05)
    wrapped = np.mod(d_hat + np.pi, 2 * np.pi) - np.pi
    ok_counts = {}
    for label, mask in [("そのまま(マスク無し)", None), ("標本化不足を外す", ~aliased),
                        ("標本化不足 + 低変調を外す", ~aliased & ~lowmod)]:
        kw = {} if mask is None else {"mask": mask}
        un = np.asarray(fs.ledger.unwrap_phase_2d(wrapped, **kw))
        valid = IN_DISC & np.isfinite(un)
        off = float(np.median((un - delta)[valid]))
        ok = (np.abs(un - off - delta) < 0.5 * np.pi) & valid
        ok_counts[label] = (int(ok.sum()), int(valid.sum()))
    # 6 節
    rng = np.random.default_rng(5)
    rows = {}
    for sig, bits in [(0.0, 0), (0.002, 0), (0.01, 0), (0.0, 8), (0.002, 8)]:
        dark = legacy_polariscope_image(delta, fast, 90.0)
        bright = legacy_polariscope_image(delta, fast, 0.0)
        if sig > 0:
            dark = dark + rng.normal(0, sig, dark.shape)
            bright = bright + rng.normal(0, sig, bright.shape)
        if bits:
            q = 2 ** bits - 1
            dark = np.round(np.clip(dark, 0, 1) * q) / q
            bright = np.round(np.clip(bright, 0, 1) * q) / q
        dh = 2.0 * np.arctan2(np.sqrt(np.maximum(dark, 0)), np.sqrt(np.maximum(bright, 0)))
        e = np.abs(np.mod(dh - delta + np.pi, 2 * np.pi) - np.pi)
        rows[(sig, bits)] = (float(np.median(e[m])),
                             float(np.mean(np.abs(F_SIGMA * (dh / (2 * np.pi)) / H_MM - dsig)[m])))
    return {"err0": err0, "e3": e3, "good": good, "abs_err": abs_err, "d_hat": d_hat, "d_hat_orig": d_hat_orig,
            "ok_counts": ok_counts, "rows": rows, "m": m}


@pytest.fixture(scope="module")
def L():
    return legacy_sections()


# =========================================================================== #
def test_grid_and_disc_mask_match_the_legacy_grid(P):
    """op の格子(m)と初版の格子(mm)が同じ点で、評価域(半径 0.9R)も同じ画素。"""
    disc = P.fields()["disc"]
    assert disc["x"].shape == (NPIX, NPIX)
    assert np.max(np.abs(disc["x"] * 1e3 - X_MM)) < 1e-12
    assert np.max(np.abs(disc["y"] * 1e3 - Y_MM)) < 1e-12
    assert np.array_equal(P.IN_DISC, IN_DISC)
    # 評価域が空や定数でないこと(空を通す門にしない)
    assert 40000 < int(IN_DISC.sum()) < NPIX * NPIX


def test_stress_fields_match_the_legacy_closed_form(P):
    """主応力差・等傾角・位相差・縞次数: op(SI)と初版(mm・MPa)の閉形式が一致する。"""
    dsig_l, theta_l, delta_l = legacy_build_fields()
    dsig, theta, delta = P.build_fields()
    m = IN_DISC
    scale = float(np.max(dsig_l[m]))
    assert scale > 5.0                                   # 場は空でも定数でもない(最大 22 MPa 台)
    assert np.max(np.abs(dsig - dsig_l)[m]) <= 1e-12 * scale
    ang = np.abs(np.mod(theta - theta_l + np.pi / 2, np.pi) - np.pi / 2)
    assert np.max(ang[m]) < 1e-10
    assert np.max(np.abs(delta - delta_l)[m]) <= 1e-12 * float(np.max(delta_l[m]))
    order = P.fields()["order"]
    assert np.max(np.abs(order - delta_l / (2 * np.pi))[m]) < 1e-12


def test_polariscope_images_match_the_legacy_mueller_chain(P):
    """暗視野・明視野(初版は Mueller の鎖)と平面偏光(初版は強度式)が op と一致する。"""
    _, theta, delta = legacy_build_fields()
    fast = theta + np.pi / 2
    ang = np.rad2deg(theta)
    m = IN_DISC
    dark = P.pe.polariscope_intensity(delta, ang, "circular_dark")
    bright = P.pe.polariscope_intensity(delta, ang, "circular_bright")
    assert np.max(np.abs(dark - legacy_polariscope_image(delta, fast, 90.0))[m]) < 1e-12
    assert np.max(np.abs(bright - legacy_polariscope_image(delta, fast, 0.0))[m]) < 1e-12
    for b in (0.0, 22.5, 45.0, 67.5):
        plane = P.pe.polariscope_intensity(delta, ang, "plane_dark", polarizer_deg=b)
        assert np.max(np.abs(plane - legacy_plane_polariscope(delta, theta, b))[m]) < 1e-12
    # 中身のある像であること(暗線と明線の両方が出ている)
    assert dark[m].min() < 1e-3 and dark[m].max() > 1 - 1e-3


def test_specimen_stokes_match_the_legacy_retarder_and_document_the_sign(P):
    """試料を出た Stokes: 進相軸 = σ1 + 90° の初版の位相子と一致。σ1 を進相軸にした初版
    (2026-09-06 の規約)とは S1・S2 の符号だけが逆で、S0・S3 は同じ。"""
    _, theta, delta = legacy_build_fields()
    m = IN_DISC
    s = np.stack(P.stokes_from_frames(P.specimen_frames(delta, theta)), axis=-1)
    ref = legacy_emerging_stokes(delta, theta + np.pi / 2)
    assert np.max(np.abs(s - ref)[m]) < 1e-12
    old = legacy_emerging_stokes(delta, theta)
    assert np.max(np.abs(s[..., 1:3] + old[..., 1:3])[m]) < 1e-12
    assert np.max(np.abs(s[..., [0, 3]] - old[..., [0, 3]])[m]) < 1e-12
    # 符号の差は画像で見えるだけの大きさがある(0 同士の一致ではない)
    assert np.max(np.abs(old[..., 1])[m]) > 0.99


@pytest.mark.parametrize("analyser", [0.0, 22.5, 45.0, 90.0, 135.0])
def test_general_analyser_image_matches_the_legacy_chain(P, analyser):
    """ViEW2026 の掃引が呼ぶ ``polariscope_image``(検光子を回す)も初版の鎖と一致。
    0°/90° は進相軸の取り方に依らず、それ以外は σ1 + 90° の規約で一致する。"""
    _, theta, delta = legacy_build_fields()
    m = IN_DISC
    got = P.polariscope_image(delta, theta, analyser)
    assert np.max(np.abs(got - legacy_polariscope_image(delta, theta + np.pi / 2, analyser))[m]) < 1e-12
    if analyser in (0.0, 90.0):
        assert np.max(np.abs(got - legacy_polariscope_image(delta, theta, analyser))[m]) < 1e-12


def test_section_numbers_match_the_legacy_procedure(P, L):
    """2〜6 節が門で見る数値: op を使う新版 = 初版の手順。"""
    out = P.run_out
    assert out["err0"] == pytest.approx(L["err0"], rel=1e-12)
    assert out["e3"] == pytest.approx(L["e3"], rel=1e-12)
    # 4 節: 符号の一致率は画素単位で同じ集合
    _, _, delta = P.build_fields()
    wrapped_true = np.mod(delta + np.pi, 2 * np.pi) - np.pi
    good_new = np.abs(np.mod(out["d_hat"] - wrapped_true + np.pi, 2 * np.pi) - np.pi) < 0.05
    assert np.array_equal(good_new[IN_DISC], L["good"][IN_DISC])
    assert out["agree"] == pytest.approx(100 * float(np.mean(L["good"][IN_DISC])), abs=1e-12)
    assert np.max(np.abs(out["d_hat"] - L["d_hat"])[IN_DISC]) < 1e-12
    assert np.max(np.abs(out["d_hat"] - L["d_hat_orig"])[IN_DISC]) < 1e-12
    # |δ| の誤差は両方とも機械精度(値そのものは丸めの屑なので桁だけ比べる)
    assert out["abs_err"] < 1e-12 and L["abs_err"] < 1e-12
    # 5 節: 一致率は一致した画素数で比べる(差 0 画素)
    for label, (n_ok, n_valid) in L["ok_counts"].items():
        assert out["rates"][label] == pytest.approx(100.0 * n_ok / n_valid, abs=1e-12), label
    # 6 節: 同じ乱数列・同じ量子化
    for key, (e_l, s_l) in L["rows"].items():
        e_n, s_n = out["rows"][key]
        assert e_n == pytest.approx(e_l, rel=1e-9, abs=1e-15), key
        assert s_n == pytest.approx(s_l, rel=1e-9, abs=1e-15), key


def test_legacy_reference_keeps_its_own_physics(L):
    """参照の側も中身のある値であること(参照が壊れて 0 同士で一致する門にしない)。"""
    assert 1.0 < L["err0"] < 1.2
    assert 0.3 < L["e3"] < 1.0
    assert 95.0 < 100 * float(np.mean(L["good"][IN_DISC])) < 99.5
    noise = L["rows"][(0.002, 0)][0]
    assert 1e-3 < noise < 1e-2 and np.isfinite(noise)
    rates = {k: 100.0 * a / b for k, (a, b) in L["ok_counts"].items()}
    assert rates["そのまま(マスク無し)"] > 90.0 > rates["標本化不足 + 低変調を外す"]


def test_unwrap_misses_are_mostly_the_sign_ambiguity(P):
    """5 節の所見をテスト本体で数え直す(fixture の run() の assert に頼らない)。"""
    import fullseye as fs
    _, _, delta = P.build_fields()
    m = IN_DISC
    out = P.run_out
    w = lambda a: np.mod(a + np.pi, 2 * np.pi) - np.pi
    un = np.asarray(fs.ledger.unwrap_phase_2d(w(out["d_hat"])))
    bad = m & ~(np.abs(un - np.median((un - delta)[m]) - delta) < 0.5 * np.pi)
    flipped = out["flipped"]
    assert bad.sum() > 0 and (bad & flipped).sum() / bad.sum() > 0.9
    ut = np.asarray(fs.ledger.unwrap_phase_2d(w(delta)))
    bad_t = m & ~(np.abs(ut - np.median((ut - delta)[m]) - delta) < 0.5 * np.pi)
    assert bad_t.sum() / m.sum() < 0.005
    n = np.asarray(P.pe.retardation_convert(delta, "rad", "waves"))
    assert n[m].min() > 0.1                      # 評価域に等方点は無い
    low = m & (np.hypot(*P.stokes_from_frames(P.specimen_frames(delta, P.build_fields()[1]))[1:3]) < 0.05)
    assert np.max(np.abs(2 * n[low] - np.round(2 * n[low]))) / 2 < 0.01   # N が 0.5 の倍数の帯
