# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""印字品質の等級(symgrade)の門 —— 閉形式で答えが決まる合成シンボルだけで確かめる。

  * 理想のシンボル → どの体系でも最高等級(4 = A)
  * 反射率を指定した描画 → SC = light − dark、Rmin ≤ Rmax/2 の規則(閉形式)
  * 既知の深さの汚れ → defects = 深さ / SC
  * 平面のあおり(遠い視点)→ 軸の不均一 AN = 2(1 − cos t)/(1 + cos t)(t = 傾き)、
    平面内の回転 r と組むと AN = |Lx − Ly| / ((Lx + Ly)/2)、Lx = √(cos²r + sin²r cos²t) など
  * k 語を壊した記号 → UEC = 1 − 2k/(n_ec − p)(誤り訂正の閉形式)
  * 灰色に塗ったモジュール → 変調の等級が誤り訂正の規則どおりに落ちる
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import barcode1d as B  # noqa: E402
import symgrade as G  # noqa: E402
import symrender as SR  # noqa: E402


# --------------------------------------------------------------------------- #
# 1-D
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("sym,txt", [("ean13", "400638133393"), ("code128", "FULLSEYE-2026"),
                                     ("code39", "LOT 42A"), ("itf", "12345678901231"),
                                     ("upca", "03600029145")])
def test_ideal_1d_symbol_is_grade_a(sym, txt):
    g = G.grade_barcode1d(SR.render_symbol(B.encode_barcode1d(txt, sym), 6.0))
    assert g["symbol_grade"] == 4.0 and g["letter"] == "A", g["limiting"]
    assert np.allclose(g["parameters"]["symbol_contrast"], 0.80, atol=1e-9)
    assert np.allclose(g["parameters"]["modulation"], 1.0, atol=1e-6)
    assert max(g["parameters"]["defects"]) < 1e-9


@pytest.mark.parametrize("light,dark,grade", [(0.85, 0.05, 4), (0.75, 0.15, 3), (0.70, 0.25, 2),
                                              (0.50, 0.20, 1), (0.40, 0.25, 0)])
def test_symbol_contrast_closed_form(light, dark, grade):
    """SC = light − dark。0.60 → B、0.45 → C、0.30 → D、0.15 → F(境界の外側だけを選ぶ)。"""
    g = G.grade_barcode1d(SR.render_symbol(B.encode_barcode1d("LOT42", "code128"), 6.0,
                                           light=light, dark=dark))
    assert np.allclose(g["parameters"]["symbol_contrast"], light - dark, atol=1e-9)
    assert g["parameter_grade_mean"]["symbol_contrast"] == grade


def test_rmin_rule():
    """Rmin > Rmax/2 は SC が C でも全体を F にする(0.44 > 0.43)。"""
    g = G.grade_barcode1d(SR.render_symbol(B.encode_barcode1d("LOT42", "code128"), 6.0,
                                           light=0.86, dark=0.44))
    assert g["symbol_grade"] == 0.0 and g["limiting"][0] == "r_min"
    assert g["parameter_grade_mean"]["symbol_contrast"] == 2


def test_defect_depth_closed_form():
    """太いバーの中の明るい汚れ(反射率 v)→ ERN = v − dark、defects = (v − 0.05)/0.80。

    開口 0(素の画素)にして汚れの値がそのまま走査線に出るようにする。0.226 は
    defects = 0.22 → 等級 C(上限 0.20 < 0.22 ≤ 0.25)。"""
    enc = B.encode_barcode1d("400638133393", "ean13")
    geo = SR.render_symbol(enc, 8.0, return_geometry=True)
    img = geo["image"].copy()
    w = enc["widths"]
    k = int(np.argmax(np.where(np.arange(w.size) % 2 == 0, w, 0)))   # 最も太いバー
    u0 = enc["edges"][k] + 0.5 * w[k]
    H = geo["homography"]
    c0 = (H @ np.array([u0, 0.0, 1.0]))[0]
    img[:, int(round(c0)) - 3:int(round(c0)) + 3] = 0.226
    g = G.grade_barcode1d(img, aperture_x=0.0)
    assert np.allclose(g["parameters"]["defects"], (0.226 - 0.05) / 0.80, atol=1e-9)
    assert g["parameter_grade_mean"]["defects"] == 2 and g["symbol_grade"] == 2.0


def test_modulation_falls_with_blur_and_matches_the_erf_model():
    """ガウスぼけ σ の下の走査線は Σ ±Φ((x − e_k)/σ) の重ね合わせ(独立に計算した閉形式)。
    その要素の極値から作った ECmin / SC と、画像から測った変調が一致し、σ とともに単調に下がる。"""
    from scipy.special import ndtr
    enc = B.encode_barcode1d("400638133393", "ean13")
    mpx = 8.0
    mods = []
    for sig in (1.0, 3.0, 5.0):
        img = SR.capture_degrade(SR.render_symbol(enc, mpx, supersample=8), gauss_px=sig)
        g = G.grade_barcode1d(img, aperture_x=0.0, angle_deg=0.0)
        m = float(np.median(g["parameters"]["modulation"]))
        mods.append(m)
        # 閉形式: 反射率 = light − (light−dark)·Σ_bars [Φ((x−a)/σ) − Φ((x−b)/σ)]
        # 画素の面積積分(幅 1 の箱、分散 1/12)をガウスに足して近似する
        s_eff = np.sqrt(sig ** 2 + 1.0 / 12.0)
        x = np.arange(0.0, (enc["edges"][-1] + enc["quiet"][1]) * mpx, 0.05)
        cov = np.zeros_like(x)
        for a, b in zip(enc["edges"][0:-1:2], enc["edges"][1::2]):
            cov += ndtr((x - a * mpx) / s_eff) - ndtr((x - b * mpx) / s_eff)
        prof = 0.85 - 0.80 * cov
        gp = G.grade_barcode_profile(prof)
        assert abs(m - gp["modulation"]) < 0.015, (sig, m, gp["modulation"])
    assert mods[0] > mods[1] > mods[2]


def test_quiet_zone_violation_is_graded_f():
    """左の静寂域(EAN は 11 X)の 8 X の位置に暗い線 → 復号は通る(読み取りは 5 X で探す)が
    静寂域の等級が F。"""
    enc = B.encode_barcode1d("400638133393", "ean13")
    geo = SR.render_symbol(enc, 4.0, return_geometry=True)
    img = geo["image"].copy()
    c = (geo["homography"] @ np.array([enc["edges"][0] - 8.0, 0.0, 1.0]))[0]
    img[:, int(round(c)) - 2:int(round(c)) + 2] = 0.05
    g = G.grade_barcode1d(img)
    assert g["symbol_grade"] == 0.0 and "quiet_zone" in g["limiting"]


def test_letter_mapping_and_fail_closed():
    assert [G.grade_letter(v) for v in (4, 3.5, 3.49, 2.5, 1.5, 0.5, 0.49, 0)] == \
        ["A", "A", "B", "B", "C", "D", "F", "F"]
    with pytest.raises(ValueError):
        G.grade_letter(4.5)
    with pytest.raises(ValueError):
        G.grade_barcode1d(np.ones((30, 30)), n_scans=0)
    with pytest.raises(ValueError):
        G.grade_barcode1d(np.ones((30, 30)), aperture_x=3.0)
    with pytest.raises(ValueError):
        G.grade_barcode_profile(np.full(40, np.nan))
    flat = G.grade_barcode_profile(np.full(64, 0.5))
    assert flat["profile_grade"] == 0 and flat["decode"] is False


# --------------------------------------------------------------------------- #
# 2-D
# --------------------------------------------------------------------------- #
qrsym = pytest.importorskip("qrsym")
dmsym = pytest.importorskip("dmsym")


def _qr():
    return qrsym.qr_encode("LOT-2026-1103", ec_level="M")          # 1-M: (16, 10), p = 2


def _dm():
    return dmsym.dm_encode("LOT-2026-1103")                         # 16x16: (12, 12)


@pytest.mark.parametrize("make", [_qr, _dm])
def test_ideal_2d_symbol_is_grade_a(make):
    g = G.grade_datacode2d(SR.render_symbol(make(), 6.0, rotate_deg=23.0))
    assert g["overall_grade"] == 4 and g["letter"] == "A", g["limiting"]
    assert abs(g["symbol_contrast"] - 0.80) < 0.01
    assert g["axial_nonuniformity"] < 0.01 and g["grid_nonuniformity"] < 0.1
    assert g["unused_error_correction"] == 1.0 and g["wrong_modules"] == 0


@pytest.mark.parametrize("make", [_qr, _dm])
@pytest.mark.parametrize("rot,tilt", [(0.0, 15.0), (0.0, 24.0), (20.0, 20.0)])
def test_axial_nonuniformity_closed_form(make, rot, tilt):
    """遠い視点(distance_ratio 300)で縦軸まわりに t 傾けると、x の刻みが cos t 倍。"""
    r, t = np.deg2rad(rot), np.deg2rad(tilt)
    lx = np.sqrt(np.cos(r) ** 2 + np.sin(r) ** 2 * np.cos(t) ** 2)
    ly = np.sqrt(np.sin(r) ** 2 + np.cos(r) ** 2 * np.cos(t) ** 2)
    an_closed = abs(lx - ly) / (0.5 * (lx + ly))
    img = SR.render_symbol(make(), 6.0, rotate_deg=rot, tilt_deg=tilt, tilt_axis_deg=90.0,
                           distance_ratio=300.0)
    g = G.grade_datacode2d(img)
    assert abs(g["axial_nonuniformity"] - an_closed) < 0.006, (g["axial_nonuniformity"], an_closed)


@pytest.mark.parametrize("make,nec_p", [(_qr, 8), (_dm, 12)])
@pytest.mark.parametrize("k", [1, 2, 3])
def test_unused_error_correction_closed_form(make, nec_p, k):
    """k 語のモジュールを全部反転 → 復号器が k 語を直し、UEC = 1 − 2k/(n_ec − p)。"""
    e = make()
    m = np.asarray(e["modules"]).astype(bool).copy()
    ci = np.asarray(e["codeword_index"])
    for c in range(k):
        m ^= ci == c
    tbl = dict(e)
    tbl["modules"] = m.astype(np.uint8)
    g = G.grade_datacode2d(SR.render_symbol(tbl, 6.0))
    want = 1.0 - 2.0 * k / nec_p
    assert g["decode"] and g["text"] == e["text"]
    assert g["block_corrected"] == [k]
    assert abs(g["unused_error_correction"] - want) < 1e-12
    assert g["grades"]["unused_error_correction"] == G._grade(want, "unused_error_correction",
                                                              G.GRADE_TABLE_2D)
    # 壊したモジュールは「理想と逆の側」= 変調 0 の符号語になり、変調の等級も UEC で決まる
    assert g["grades"]["modulation"] == g["grades"]["unused_error_correction"]


@pytest.mark.parametrize("c,expect", [(1, 4), (2, 3), (3, 2)])
def test_grey_modules_lower_modulation_by_the_error_correction_rule(c, expect):
    """QR 1-M の c 語の暗いモジュールを反射率 0.31 に(正しい側、変調 = 2·0.14/0.80 = 0.35 → C)。

    規則: 等級 L 未満の語を誤りと数えて UEC_L、変調の等級 = max_L min(L, 等級(UEC_L))。
    c = 1 → UEC 0.75 で A のまま、c = 2 → 0.50 = B → 3、c = 3 → 0.25 = D → C 段の 2。"""
    e = _qr()
    geo = SR.render_symbol(e, 8.0, return_geometry=True)
    img = geo["image"].copy()
    H = geo["homography"]
    Hinv = np.linalg.inv(H)
    yy, xx = np.mgrid[0:img.shape[0], 0:img.shape[1]].astype(float)
    w = Hinv[2, 0] * xx + Hinv[2, 1] * yy + Hinv[2, 2]
    u = (Hinv[0, 0] * xx + Hinv[0, 1] * yy + Hinv[0, 2]) / w - 4.0      # 静寂域 4
    v = (Hinv[1, 0] * xx + Hinv[1, 1] * yy + Hinv[1, 2]) / w - 4.0
    ci = np.asarray(e["codeword_index"])
    mods = np.asarray(e["modules"]).astype(bool)
    N = mods.shape[0]
    jj, ii = np.floor(u).astype(int), np.floor(v).astype(int)
    inside = (ii >= 0) & (ii < N) & (jj >= 0) & (jj < N)
    sel = np.zeros_like(inside)
    for cw in range(c):
        mask = (ci == cw) & mods
        sel |= inside & mask[np.clip(ii, 0, N - 1), np.clip(jj, 0, N - 1)]
    img[sel] = 0.31
    g = G.grade_datacode2d(img)
    assert g["decode"] and g["block_corrected"] == [0]
    assert g["grades"]["modulation"] == expect, (g["grades"], g["codeword_grades"][:6])


def test_unreadable_2d_is_f_not_an_exception():
    g = G.grade_datacode2d(np.full((80, 80), 0.8))
    assert g["overall_grade"] == 0 and g["decode"] is False and g["letter"] == "F"
    with pytest.raises(ValueError):
        G.grade_datacode2d(np.full((80, 80), 0.8), symbology="pdf417")
    with pytest.raises(ValueError):
        G.grade_datacode2d(np.full((8, 8, 3), 0.8))
