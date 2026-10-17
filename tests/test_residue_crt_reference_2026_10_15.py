# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""residue_crt の錨(reference remainder)と Wang–Xia の保証 —— 2026-10-15 の欠陥の回帰テスト。

欠陥: ``residue_crt`` は**最も長い周期**の剰余を錨にして候補 ``v = r_ref + k p_ref`` を並べていた。位相雑音が
帯ごとに同じ問題(間接 ToF の多周波)では、最も長い周期の剰余が距離の誤差が最も大きい —— 錨の誤差がそのまま
全候補にのるので、低い周波数の位相誤差が Wang–Xia の保証(剰余の誤差 < Γ/4)を越えた所から、仮説を全部試す
最尤より大きく崩れた(σ_φ 0.33 rad で次数の誤り 0.53 対 0.07)。保証の外でも黙って値を返していた。

一次資料: W. Wang & X.-G. Xia, "A closed-form robust Chinese remainder theorem and its performance analysis",
IEEE TSP 58(11):5655–5666, 2010(doi:10.1109/TSP.2010.2066974)。周期 ``Γ M_i`` で、全剰余の誤差が ``Γ/4`` 未満なら
次数(folding integer)は必ず正しい(式 (47))。錨は任意の剰余でよく、**雑音の分散が最も小さい剰余**を錨に選ぶと
性能が上がる(IV-A 節。分散が等しいときは剰余 mod Γ が共通の剰余の推定に最も近いもの、式 (55)(58))。

門:
  1. 保証の範囲(全帯の誤差 < Γ/4、符号の全組合せ・互いに素でない M・重み 0 の帯)で次数の誤りが 0。
  2. 位相雑音が帯ごとに同じとき、誤り率が最尤(各帯を錨にした仮説を全部試す)と同程度(以前は 8 倍)。
  3. 保証の外では警告(既定)/ 拒否(``on_outside="raise"``)/ NaN(``"nan"``)。保証の内では警告しない。
"""
from __future__ import annotations

import itertools
import warnings
from math import lcm

import numpy as np
import pytest

import residue as R


def _circ_err(est, truth, U):
    return np.abs((est - truth + U / 2.0) % U - U / 2.0)


def _ml_all_hypotheses(r, p, w, hi):
    """最尤の参照: 各帯を錨にした候補 ``r_j + k p_j`` を全部フェーザの一致で採点し、全体の最良を取る。"""
    best_val = None
    best_sc = None
    for j in range(p.size):
        ks = np.arange(-1, int(np.ceil(hi / p[j])) + 1)[:, None]
        cand = r[j][None] + ks * p[j]
        inside = (cand >= 0.0) & (cand < hi)
        sc = (w[:, None] * np.cos(2 * np.pi * (cand[None] - r[:, None]) / p[:, None, None])).sum(0)
        sc = np.where(inside, sc, -np.inf)
        k = np.argmax(sc, 0)
        v = np.take_along_axis(cand, k[None], 0)[0]
        s = np.take_along_axis(sc, k[None], 0)[0]
        if best_val is None:
            best_val, best_sc = v, s
        else:
            upd = s > best_sc
            best_val = np.where(upd, v, best_val)
            best_sc = np.where(upd, s, best_sc)
    return best_val


# ---- 1. 保証の範囲では次数を誤らない -------------------------------------------------------
@pytest.mark.parametrize("M", [(15, 3, 2), (3, 5, 7), (2, 3), (20, 15, 12), (7, 9, 11, 13)])
def test_no_folding_error_anywhere_inside_the_wang_xia_bound(M):
    G = 0.7
    M = np.array(M)
    p = G * M
    U = G * lcm(*M.tolist())
    v = np.linspace(0.013 * G, U - 0.013 * G, 1501)
    bad = 0
    with warnings.catch_warnings():
        warnings.simplefilter("error")                 # 保証の内側では警告も出さない
        for signs in itertools.product((-1, 0, 1), repeat=M.size):
            e = 0.999 * G / 4 * np.array(signs, float)
            out = R.residue_crt((v[None] + e[:, None]) % p[:, None], p, lo=0.0, hi=U)
            assert out["within_bound"].all()
            bad += int((_circ_err(out["value"], v, U) > G / 2).sum())
            assert _circ_err(out["value"], v, U).max() < G / 4      # 式 (52): 推定の誤差 <= τ < Γ/4
    assert bad == 0


def test_bound_and_its_phase_form_are_reported():
    # 間接 ToF 16/80/120 MHz: 周期 = U/(2, 10, 15)、Γ = U/30、M = (15, 3, 2)
    p = 30.0 / np.array([2.0, 10.0, 15.0])
    out = R.residue_crt(np.zeros((3, 1)), p)
    assert out["gamma"] == pytest.approx(1.0) and out["error_bound"] == pytest.approx(0.25)
    # 最も長い周期(16 MHz)の位相で 2π(Γ/4)/p = π/30 = 0.1047 rad —— PoC の「保証 0.105 rad」
    assert out["phase_bound_rad"][0] == pytest.approx(np.pi / 30)
    assert np.argmin(out["phase_bound_rad"]) == 0


def test_a_zero_weight_band_is_never_the_reference():
    # 以前は重みに関係なく最も長い周期が錨 —— 重み 0(コントラストなし)のごみの剰余が全候補にのった
    p = np.array([7.0, 9.0, 11.0, 13.0])
    v = np.array([123.4, 5.5, 600.25])
    r = (v[None] % p[:, None]).copy()
    r[3] = (r[3] + 6.0) % 13.0                     # 最も長い周期の帯がごみ ...
    w = np.array([1.0, 1.0, 1.0, 0.0])             # ... ただしコントラストが無い
    out = R.residue_crt(r, p, w, lo=0, hi=693)
    assert np.allclose(out["value"], v, atol=1e-9)
    assert not np.any(out["reference"] == 3)


def test_equal_variance_reference_follows_wang_xia_rule_58():
    # 分散が等しい(重み ∝ p²)とき、錨は「剰余 mod Γ が共通の剰余の推定に最も近い」帯(式 (58))
    # Γ = 1、剰余 mod Γ = (0.20, 0.95, 0.15)。円の上の最小二乗の平均は 0.10 で、距離は (0.10, 0.15, 0.05)
    # —— 錨は帯 2(最も長い周期でも最も短い周期でもない)。
    p = np.array([3.0, 5.0, 7.0])
    e = np.array([0.2, -0.05, 0.15])
    out = R.residue_crt(((50.0 + e) % p)[:, None], p, weights=(p ** 2)[:, None])
    assert int(out["reference"][0]) == 2
    assert abs(float(out["value"][0]) - 50.0) < 0.25


# ---- 2. 位相雑音が帯ごとに同じ: 最尤と比べる ------------------------------------------------
def test_equal_phase_noise_error_rate_is_close_to_maximum_likelihood():
    C = 299792458.0
    f = np.array([16e6, 80e6, 120e6])
    p = C / (2 * f) / (C / (2 * 16e6))             # 最長の周期で割った単位(itof と同じ)
    U = 2.0                                        # = 18.737 m / 9.369 m
    rng = np.random.default_rng(20261015)
    n = 20000
    v = rng.uniform(0.02, U - 0.02, n)
    rows = []
    for sig in (0.105, 0.24, 0.33):
        e = rng.normal(0.0, sig, (3, n)) * p[:, None] / (2 * np.pi)
        r = (v[None] + e) % p[:, None]
        w = np.ones_like(r)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", R.ResidueBoundWarning)
            crt = R.residue_crt(r, p, w)["value"]
        ml = _ml_all_hypotheses(r, p, w, U)
        thr = 0.25 * p.min()
        rate_crt = float((_circ_err(crt, v, U) > thr).mean())
        rate_ml = float((_circ_err(ml, v, U) > thr).mean())
        rows.append((sig, rate_crt, rate_ml))
    for sig, rc_, rm in rows:
        # 以前: 0.105 → 0.05 / 0.24 → 0.39 / 0.33 → 0.53(最尤の 8 倍)
        assert rc_ <= 1.1 * rm + 2e-3, rows


# ---- 3. 保証の外では黙らない ----------------------------------------------------------------
def _beyond(n=400, seed=3):
    p = 30.0 / np.array([2.0, 10.0, 15.0])
    rng = np.random.default_rng(seed)
    v = rng.uniform(0.1, 29.9, n)
    e = rng.normal(0.0, 0.33, (3, n)) * p[:, None] / (2 * np.pi)
    return (v[None] + e) % p[:, None], p


def test_outside_the_bound_warns_by_default():
    r, p = _beyond()
    with pytest.warns(R.ResidueBoundWarning, match="Wang"):
        out = R.residue_crt(r, p)
    assert (~out["within_bound"]).any() and out["within_bound"].any()


def test_outside_the_bound_can_be_refused_or_blanked():
    r, p = _beyond()
    with pytest.raises(ValueError, match="Wang"):
        R.residue_crt(r, p, on_outside="raise")
    out = R.residue_crt(r, p, on_outside="nan")
    out_bad = ~out["within_bound"]
    assert np.isnan(out["value"][out_bad]).all() and np.isfinite(out["value"][~out_bad]).all()
    assert (out["margin"][out_bad] == 0.0).all()
    with pytest.raises(ValueError):
        R.residue_crt(r, p, on_outside="quietly")


def test_incommensurate_periods_have_no_guarantee_and_say_so():
    with pytest.warns(R.ResidueBoundWarning, match="no common"):
        out = R.residue_crt([1.0, 2.0], [7.0, np.pi], lo=0, hi=20)
    assert np.isnan(out["gamma"]) and not np.any(out["within_bound"])


def test_values_at_the_edge_of_a_narrow_range_keep_the_guarantee():
    # 錨の候補は錨の誤差(< Γ/4)ぶん [lo, hi) の外へ出うる。以前は外に出た候補を捨て、範囲の端の値で次数を誤った
    # (poc_residue_crt の RRNS で、-40 の際の 2 件が別の帯を犯人にした)。
    p = np.array([7.0, 9.0, 11.0, 13.0])
    v = np.array([-39.999, -39.9, -39.76, 39.76, 39.9, 39.999])
    for signs in itertools.product((-1, 1), repeat=4):
        e = 0.249 * np.array(signs, float)[:, None]
        out = R.residue_crt((v[None] + e) % p[:, None], p, lo=-40, hi=40)
        assert np.abs(out["value"] - v).max() < 0.25, (signs, out["value"])
