# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""良品統計の変動モデル(varmodel、5 op)の門。

★真値は op の外から取る:

1. **閉形式の誤検出率**: 画素ごとに独立な正規の良品を合成し、宣言した ``far`` と、当てはめに
   使っていない良品で**数えた**誤検出率を突き合わせる。画素ごとの「学習 + 1 枚の試験」は
   互いに独立なので、全画素のはみ出し数は Binomial(画素数, far) —— その 4σ の帯に入ること。
   (std = t 分布の予測区間 / pooled = 正規 / moderated = 分散が逆カイ二乗の事前分布に従う
   ときの t_{d+d0} / mad = ピボットのモンテカルロ。乱数の誤差 ``mc_far_rel_se`` も帯に足す)
2. **教科書の数表**: t_{0.975, 4} = 2.776445(どの統計の教科書の付表にもある値)。
3. **第 2 実装**: 整数の山は ``filters_freq.phase_correlation_fft`` と一致。
4. **作り手が知る真値**: Fourier シフトで動かした量、描き込んだ欠陥の位置・符号・振幅。

壊す探針: ずれた良品群は**拒否**され、許容を緩めて通すと帯が縁で太る(2 倍以上)/
汚れた良品群(3 枚に同じ場所の傷)で std は傷を見逃し、mad は見つける /
裾の重い雑音では閉形式の k が誤検出を過小に言い、``varmodel_calibrate`` が直す。
"""
from __future__ import annotations

import functools
import math
import os
import sys

import numpy as np
import pytest
from scipy import ndimage as ndi
from scipy import special, stats

import opsspc
import varmodel as VM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = W = 160


@functools.lru_cache(maxsize=None)
def _measured_far(spread, n, far, sigma_kind, reps=6, seed=0):
    """当てはめに使っていない良品 1 枚 × reps 回のはみ出し率と、閉形式の帯の半幅(4σ)。"""
    tot = nv = 0
    rel = 0.0
    for rep in range(reps):
        rng = np.random.default_rng([seed, rep, n, len(spread)])
        if sigma_kind == "invchi2":                       # σ² ~ d0·s0²/χ²_{d0}, d0 = 6
            sig = np.sqrt(6.0 / rng.chisquare(6.0, (H, W))) * 0.1
        elif sigma_kind == "const":
            sig = 0.1
        else:
            sig = rng.uniform(0.05, 0.2, (H, W))
        mu = rng.uniform(0.0, 1.0, (H, W))
        m = VM.varmodel_fit(mu + sig * rng.standard_normal((n, H, W)), spread=spread, far=far)
        r = VM.varmodel_score(mu + sig * rng.standard_normal((H, W)), m)
        tot += r["n_exceed"]
        nv += r["n_valid"]
        rel = m["mc_far_rel_se"]
    p = tot / nv
    band = 4.0 * math.sqrt(far * (1 - far) / nv + (rel * far) ** 2)
    return p, band, m


@pytest.mark.parametrize("spread,n,far,kind", [
    ("std", 5, 1e-2, "uniform"),
    ("std", 20, 1e-3, "uniform"),
    ("std", 40, 1e-2, "uniform"),
    ("pooled", 5, 1e-2, "const"),
    ("moderated", 5, 1e-2, "invchi2"),
    ("moderated", 20, 1e-3, "invchi2"),
    ("mad", 5, 1e-2, "uniform"),
    ("mad", 20, 1e-2, "uniform"),
])
def test_measured_false_alarm_rate_matches_the_declared_rate(spread, n, far, kind):
    p, band, _m = _measured_far(spread, n, far, kind)
    assert abs(p - far) < band, (spread, n, far, p, band)


def test_pooled_variance_breaks_when_the_noise_is_heteroscedastic():
    """探針: 画素ごとに雑音が違うのに 1 つの分散で帯を作ると、宣言の誤検出率は守れない。"""
    p, band, _m = _measured_far("pooled", 5, 1e-2, "uniform")
    assert p > 1e-2 + 3 * band, (p, band)


def test_moderated_recovers_the_prior_degrees_of_freedom():
    _p, _b, m = _measured_far("moderated", 5, 1e-2, "invchi2")
    assert 5.0 < m["d0"] < 7.2, m["d0"]                   # 真値 6(25,600 画素の推定)
    assert abs(m["s0"] - 0.1) < 0.01, m["s0"]


def test_few_samples_moderation_narrows_the_band_at_the_same_rate():
    """n = 5 で std の k は t_4 の裾で 5.0 —— 縮小した分散は自由度 4 + d0 で k ≈ 3.5。"""
    _p, _b, ms = _measured_far("std", 5, 1e-2, "invchi2")
    _p, _b, mm = _measured_far("moderated", 5, 1e-2, "invchi2")
    assert ms["k"] > 4.9 and mm["k"] < 3.7, (ms["k"], mm["k"])


def test_band_k_matches_the_t_table():
    r = VM.varmodel_band_k(5, 0.05, spread="std")
    assert abs(r["k"] - 2.776445105 * math.sqrt(1.2)) < 1e-6      # t_{0.975,4} の付表値
    assert r["df"] == 4
    big = VM.varmodel_band_k(10_000, 0.05, spread="pooled")
    assert abs(big["k"] - 1.959964 * math.sqrt(1.0001)) < 1e-5
    mad = VM.varmodel_band_k(20, 1e-2, spread="mad")
    assert mad["k"] > VM.varmodel_band_k(20, 1e-2, spread="std")["k"], "MAD は std より揺れる"
    assert mad["mc_far_rel_se"] < 0.05


def test_trigamma_inverse_inverts_trigamma():
    for x in (1e-3, 0.05, 0.7, 3.0, 50.0):
        y = VM._trigamma_inverse(x)
        assert abs(float(special.polygamma(1, y)) - x) / x < 1e-7, (x, y)


# --------------------------------------------------------------------------- #
# 位置合わせ                                                                    #
# --------------------------------------------------------------------------- #
def _pattern(seed=3, h=128, w=128):
    rng = np.random.default_rng(seed)
    b = ndi.gaussian_filter(rng.random((h, w)), 3)
    return (b - b.min()) / np.ptp(b)


def test_alignment_recovers_known_subpixel_shifts():
    base = _pattern()
    rng = np.random.default_rng(4)
    offs = rng.uniform(-2.0, 2.0, (12, 2))
    st = np.stack([VM._fourier_shift(base, r, c) + 0.01 * rng.standard_normal(base.shape) for r, c in offs])
    a = VM.varmodel_alignment(st)
    d = a["offset"] - offs
    d -= np.median(d, axis=0)                             # 共通の並進は「ずれ」ではない
    assert np.abs(d).max() < 0.2, np.abs(d).max()
    assert not a["ok"] and a["margin_px"].min() < 0


def test_integer_peak_agrees_with_phase_correlation_fft():
    from filters_freq import phase_correlation_fft

    base = _pattern(seed=8)
    for d in ((3, -5), (-7, 2), (0, 9)):
        img = np.roll(base, d, axis=(0, 1))
        pc = phase_correlation_fft(base, img)
        r, c, _ = VM._offset(base, img)
        assert (round(-r), round(-c)) == (int(pc["row_shift"]), int(pc["col_shift"]))
        assert abs(r - d[0]) < 1e-9 and abs(c - d[1]) < 1e-9


def test_misaligned_stack_is_refused_and_inflates_the_band_when_forced():
    base = _pattern()
    rng = np.random.default_rng(5)
    offs = rng.uniform(-2.0, 2.0, (16, 2))
    shifted = np.stack([VM._fourier_shift(base, r, c) + 0.01 * rng.standard_normal(base.shape) for r, c in offs])
    aligned = np.stack([base + 0.01 * rng.standard_normal(base.shape) for _ in range(16)])
    with pytest.raises(ValueError, match="not aligned"):
        VM.varmodel_fit(shifted, spread="std")
    forced = VM.varmodel_fit(shifted, spread="std", max_misalign_px=5.0)
    good = VM.varmodel_fit(aligned, spread="std")
    reg = VM.varmodel_fit(shifted, spread="std", align="translate")
    v = reg["valid"]
    grad = np.hypot(*np.gradient(base))
    edge = v & (grad > np.percentile(grad[v], 75))
    infl_forced = np.median(forced["spread"][edge]) / np.median(good["spread"][edge])
    infl_reg = np.median(reg["spread"][edge]) / np.median(good["spread"][edge])
    assert infl_forced > 2.0, infl_forced                 # ずれは帯を太らせる
    assert infl_reg < 1.3, infl_reg                       # 合わせれば戻る
    assert reg["alignment"]["abs_offset"].max() <= 0.5


def test_score_registers_a_displaced_image_and_reports_on_its_own_grid():
    base = _pattern()
    rng = np.random.default_rng(6)
    m = VM.varmodel_fit(np.stack([base + 0.01 * rng.standard_normal(base.shape) for _ in range(20)]),
                        spread="std", far=1e-3)
    img = base + 0.01 * rng.standard_normal(base.shape)
    img[60:66, 40:46] += 0.2
    moved = VM._fourier_shift(img, 3.3, -2.6)
    with pytest.raises(ValueError, match="displaced"):
        VM.varmodel_score(moved, m)
    r = VM.varmodel_score(moved, m, align="translate")
    top = r["regions"][0]
    assert abs(top["centroid"][0] - 65.8) < 1.5 and abs(top["centroid"][1] - 40.0) < 1.5, top
    assert top["polarity"] == "bright" and top["peak_z"] > 10


# --------------------------------------------------------------------------- #
# 説明・汚れ・較正                                                             #
# --------------------------------------------------------------------------- #
def test_explanation_names_the_defects_with_sign_and_sigmas():
    rng = np.random.default_rng(9)
    mu = np.full((64, 64), 0.5)
    m = VM.varmodel_fit(mu + 0.02 * rng.standard_normal((40, 64, 64)), spread="std", far=1e-4)
    img = mu + 0.02 * rng.standard_normal((64, 64))
    img[10:13, 10:13] += 0.2                              # +10σ
    img[40:44, 50:52] -= 0.3                              # -15σ
    r = VM.varmodel_score(img, m)
    assert [g["polarity"] for g in r["regions"][:2]] == ["dark", "bright"]
    dark, bright = r["regions"][:2]
    assert dark["bbox"] == (40, 50, 44, 52) and dark["area"] == 8
    assert bright["bbox"] == (10, 10, 13, 13) and bright["area"] == 9
    assert -21 < dark["peak_z"] < -11 and 8 < bright["peak_z"] < 16   # 9 画素の最大なので上振れ
    assert r["n_regions"] == len(r["regions"])


def test_robust_spread_survives_a_contaminated_good_set():
    """3/20 の「良品」に同じ場所の傷。std はそこの帯が太り、同じ場所の本物の傷を見逃す。"""
    rng = np.random.default_rng(10)
    mu = np.full((64, 64), 0.5)
    st = mu + 0.02 * rng.standard_normal((20, 64, 64))
    st[:3, 20:26, 20:26] += 0.3
    test = mu + 0.02 * rng.standard_normal((64, 64))
    test[20:26, 20:26] += 0.2
    hit = {}
    for sp in ("std", "mad"):
        m = VM.varmodel_fit(st, spread=sp, far=1e-3)
        r = VM.varmodel_score(test, m)
        hit[sp] = r["exceed"][20:26, 20:26].mean()
    assert hit["std"] < 0.1 and hit["mad"] > 0.9, hit


def test_calibrate_fixes_the_rate_on_heavy_tailed_noise():
    rng = np.random.default_rng(12)
    mu = rng.uniform(0, 1, (128, 128))

    def draw(k):
        return mu + 0.02 * rng.standard_t(3, (k, 128, 128))

    m = VM.varmodel_fit(draw(20), spread="std", far=1e-3)
    c = VM.varmodel_calibrate(m, draw(20))
    assert c["calibration_far_declared_k"] > 3e-3          # 閉形式の k は正規の裾を仮定
    assert c["k"] > c["k_declared"]
    tot = nv = 0
    for _ in range(10):
        r = VM.varmodel_score(draw(1)[0], c)
        tot += r["n_exceed"]
        nv += r["n_valid"]
    assert abs(tot / nv - 1e-3) < 4 * math.sqrt(1e-3 / nv) + 3e-4, tot / nv


# --------------------------------------------------------------------------- #
# 拒否                                                                         #
# --------------------------------------------------------------------------- #
def test_refusals():
    rng = np.random.default_rng(0)
    st = 0.5 + 0.02 * rng.standard_normal((6, 16, 16))
    with pytest.raises(ValueError, match="empty"):
        VM.varmodel_fit([])
    with pytest.raises(ValueError, match="empty"):
        VM.varmodel_fit(np.zeros((0, 16, 16)))
    with pytest.raises(ValueError):
        VM.varmodel_fit(st[:2], spread="std")             # 少なすぎ
    with pytest.raises(ValueError):
        VM.varmodel_fit(st[:4], spread="mad")
    bad = st.copy()
    bad[0, 0, 0] = np.inf
    with pytest.raises(ValueError):
        VM.varmodel_fit(bad)
    with pytest.raises(ValueError):
        VM.varmodel_fit(st, far=0.6)
    with pytest.raises(ValueError):
        VM.varmodel_fit(st, spread="mad", far=1e-4)
    with pytest.raises(ValueError):
        VM.varmodel_fit(st, spread="rms")
    with pytest.raises(ValueError):
        VM.varmodel_fit(st, align="none")
    flat = np.full((6, 16, 16), 0.5)
    with pytest.raises(ValueError, match="zero spread"):
        VM.varmodel_fit(flat + rng.standard_normal((6, 16, 16)) * (np.arange(16) > 7), spread="std")
    with pytest.raises(ValueError):
        VM.varmodel_fit(st, mask=np.ones((3, 3), bool))
    m = VM.varmodel_fit(st, spread="std")
    with pytest.raises(ValueError):
        VM.varmodel_score(st[0, :8], m)
    with pytest.raises(ValueError):
        VM.varmodel_score(st[0], {"center": 0})
    with pytest.raises(ValueError):
        VM.varmodel_band_k(1, 0.01)
    with pytest.raises(ValueError):
        VM.varmodel_calibrate(m, st[:1])                  # 画素が 10/far に届かない


# --------------------------------------------------------------------------- #
# 台帳と公開経路                                                                #
# --------------------------------------------------------------------------- #
_OPS = [n for n in VM.__all__ if n != "SPREADS"]


def test_the_ledger_lists_every_op_and_nothing_is_missing():
    listed = set(opsspc.list_ops("variation"))
    assert listed == set(_OPS), (listed, _OPS)
    for name in listed:
        assert opsspc.info(name)["module"] == "varmodel"
        assert opsspc.info(name)["out"] == "table"
        assert len(opsspc.info(name)["doc"]) >= 20


def test_every_op_is_reachable_from_the_public_tier():
    import fullseye as fs

    for name in _OPS:
        assert hasattr(fs.ledger, name), name


def test_the_typed_catalog_declares_the_family():
    import typed_catalog as tc

    rows = {r[0]: r for r in tc.catalog() if r[0].startswith("varmodel_")}
    assert set(rows) == set(_OPS)
    assert rows["varmodel_fit"][2] == ["video"]
    assert rows["varmodel_score"][2] == ["image2d", "table"]


def test_the_fuzzer_builds_arguments_that_actually_compute():
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import chain_fuzz as cf

    for name in _OPS:
        assert name in cf.OP_ARG_BUILDERS, name
        args, kw = cf.OP_ARG_BUILDERS[name](None, np.random.default_rng(0))
        out = getattr(VM, name)(*args, **kw)
        assert cf.TYPE_CHECKS["table"](out)
    a, k = cf.OP_ARG_BUILDERS["varmodel_score"](None, np.random.default_rng(0))
    assert VM.varmodel_score(*a, **k)["n_regions"] >= 1, "探針の画像に欠陥が無い"
