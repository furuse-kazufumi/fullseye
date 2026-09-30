# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""edgesfr の門: 閉形式(ガウスのエッジの SFR と MTF50)・角度・向きと回転の不変・光幕の約分・VGI = g・fail-closed。"""
import math

import numpy as np
import pytest

import edgesfr as E


def _edge(angle_deg, sigma, n=128, c=64.3):
    """ガウスでぼかしたエッジを画素の中心で点標本(真値 = 閉形式の MTF exp(−2π²σ²f²))。"""
    from math import erf
    y, x = np.mgrid[0:n, 0:n].astype(np.float64)
    t = math.radians(angle_deg)
    d = ((x - c) - (y - n / 2) * math.tan(t)) * math.cos(t)
    v = np.vectorize(erf)(d / (math.sqrt(2.0) * sigma))
    return 0.5 * (1.0 + v)


ROI = (8, 120, 24, 104)


def _sfr(img, roi=ROI, window=12):
    return E.sfr_from_edge(E.edge_spread(img, roi, oversample=4), window, correction="derivative+bin")


@pytest.mark.parametrize("angle", [2.0, 5.0, 8.0, -6.0])
@pytest.mark.parametrize("sigma", [0.6, 1.0, 2.0])
def test_sfr_matches_the_gaussian_closed_form(angle, sigma):
    es = E.edge_spread(_edge(angle, sigma), ROI, oversample=4)
    assert abs(es["angle_deg"] - angle) < 1e-3
    s = E.sfr_from_edge(es, 12, correction="derivative+bin")
    f = s[:, 0]
    m = f <= 0.5
    assert m.sum() >= 10
    truth = np.exp(-2.0 * math.pi ** 2 * sigma ** 2 * f[m] ** 2)
    assert np.abs(s[m, 1] - truth).max() < 1e-2
    f50 = math.sqrt(math.log(2.0) / (2.0 * math.pi ** 2 * sigma ** 2))
    assert abs(E.mtf50(s) / f50 - 1.0) < 0.015


def test_without_the_sinc_correction_the_sfr_sags():
    """補正を外すと sinc(fΔ)² だけ下がる —— 補正は飾りではない(Δ = 1/4 px、f = 0.5 で 5 %)。"""
    es = E.edge_spread(_edge(5.0, 0.6), ROI, oversample=4)
    a = E.sfr_from_edge(es, 12, correction="derivative+bin")
    b = E.sfr_from_edge(es, 12, correction="none")
    i = int(np.argmin(np.abs(a[:, 0] - 0.5)))
    assert b[i, 1] / a[i, 1] == pytest.approx(np.sinc(a[i, 0] / 4) ** 2, rel=1e-9)
    assert b[i, 1] / a[i, 1] < 0.96


def test_polarity_rotation_and_a_uniform_veil_leave_the_sfr_unchanged():
    im = _edge(5.0, 1.0)
    a = _sfr(im)
    assert np.abs(a - _sfr(1.0 - im)).max() < 1e-12                        # 暗→明 と 明→暗
    assert np.abs(a - _sfr(im.T, roi=(24, 104, 8, 120))).max() < 1e-12      # 90° 回した像(横に走るエッジ)
    g = 0.2
    assert np.abs(a - _sfr((1.0 - g) * im + g)).max() < 1e-12              # ★光幕は窓の両端の正規化で約分される


def test_veiling_glare_index_of_a_uniform_veil_is_exactly_g():
    s = np.ones((128, 128))
    s[48:80, 48:80] = 0.0
    dm = np.zeros_like(s, bool)
    dm[60:68, 60:68] = True
    bm = np.zeros_like(s, bool)
    bm[:16, :16] = True
    for g in (0.0, 0.03, 0.2):
        r = E.veiling_glare_index((1.0 - g) * s + g, dm, bm)
        assert r["vgi"] == pytest.approx(g, abs=1e-15)
        assert (r["n_dark"], r["n_bright"]) == (64, 256)


def test_the_glare_index_depends_on_the_spot_size_for_a_heavy_tail():
    """裾の重い PSF では黒点が大きいほど指数が下がる(測る範囲を宣言しない限り数字に意味が無い)。"""
    n = 256
    y, x = np.mgrid[0:n, 0:n] - n // 2
    tail = 1.0 / (1.0 + (np.hypot(x, y) / 20.0) ** 2)
    core = np.zeros((n, n))
    core[n // 2, n // 2] = 1.0
    psf = 0.85 * core + 0.15 * tail / tail.sum()
    K = np.fft.rfft2(np.fft.ifftshift(psf))
    vg = []
    for side in (16, 64, 160):
        s = np.ones((n, n))
        h = side // 2
        s[n // 2 - h:n // 2 + h, n // 2 - h:n // 2 + h] = 0.0
        out = np.fft.irfft2(np.fft.rfft2(s) * K, s=s.shape)
        dm = np.zeros((n, n), bool)
        dm[n // 2 - 2:n // 2 + 2, n // 2 - 2:n // 2 + 2] = True
        bm = np.zeros((n, n), bool)
        bm[:4, :4] = True
        vg.append(E.veiling_glare_index(out, dm, bm)["vgi"])
    assert len(vg) == 3
    assert vg[0] > vg[1] > vg[2] > 0


def test_fail_closed():
    with pytest.raises(ValueError, match="empty bins"):
        E.edge_spread(_edge(0.0, 1.0), ROI, oversample=4)               # 傾きが無いと位相が升を埋めない
    with pytest.raises(ValueError, match="orientation"):
        E.edge_spread(_edge(5.0, 1.0), ROI, orientation="diagonal")
    with pytest.raises(ValueError, match="oversample"):
        E.edge_spread(_edge(5.0, 1.0), ROI, oversample=0)
    with pytest.raises(ValueError, match="no edge"):
        E.edge_spread(np.ones((64, 64)), (0, 64, 0, 64))
    with pytest.raises(ValueError, match="NaN"):
        E.edge_spread(np.full((64, 64), np.nan), (0, 64, 0, 64))
    es = E.edge_spread(_edge(5.0, 1.0), ROI, oversample=4)
    with pytest.raises(ValueError, match="correction"):
        E.sfr_from_edge(es, 12, correction="auto")
    with pytest.raises(ValueError, match="runs past"):
        E.sfr_from_edge(es, 500, correction="none")
    with pytest.raises(ValueError, match="ends"):
        E.sfr_from_edge(es, 12, correction="none", ends=12)
    with pytest.raises(ValueError, match="beyond the measured range"):
        E.mtf50(np.array([[0.0, 1.0], [0.5, 0.9]]))
    s = np.ones((32, 32))
    m = np.zeros((32, 32), bool)
    m[0, 0] = True
    with pytest.raises(ValueError, match="boolean"):
        E.veiling_glare_index(s, m.astype(int), m)
    with pytest.raises(ValueError, match="overlap"):
        E.veiling_glare_index(s, m, m)
    with pytest.raises(ValueError, match="no pixels"):
        E.veiling_glare_index(s, np.zeros((32, 32), bool), m)


def test_a_bare_1d_esf_matches_the_column_mean_route():
    """1-D の ESF(1 px 刻み)を渡す経路: 離散の段差を 3 画素の箱で畳んだ像の列平均 → 前進差分が離散 LSF そのもの
    なので、SFR は箱の周波数応答 |1 + 2cos 2πf| / 3 と一致する(correction="none" が正しい場合)。"""
    step = np.zeros(64)
    step[32:] = 1.0
    row = np.convolve(step, np.ones(3) / 3.0, mode="valid")         # 端を巻き戻さない(np.roll は偽のエッジを作る)
    im = np.tile(row, (32, 1))
    a = E.sfr_from_edge(im.mean(axis=0), 10, correction="none")
    assert a.shape[1] == 2
    assert a[0, 1] == pytest.approx(1.0)
    assert np.all(np.diff(a[:, 0]) > 0)
    truth = np.abs(1.0 + 2.0 * np.cos(2.0 * np.pi * a[:, 0])) / 3.0
    assert np.abs(a[:, 1] - truth).max() < 1e-12
