# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""semsim(SEM 像の物理モデル)の門。

採点は「絵がそれらしいか」ではなく、**縁の明るさが閉形式の真値に合うか**:
平らな面で一様、斜面で sec θ、段差の明るい縁の幅が PSF 幅。どれも画像を
見ないで数で通せる(「走った」≠「意味のある出力」を避けるため、構造の有無も見る)。
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import semsim as SM                                               # noqa: E402


# --------------------------------------------------------------------------- #
# 1. 物理の閉形式(真値つき)                                                   #
# --------------------------------------------------------------------------- #
def test_a_flat_surface_renders_uniform():
    """平らな高さ場 → 一様(雑音を切れば ptp は厳密に 0)。"""
    img = SM.sem_render(np.zeros((48, 48)), base=0.3)
    assert img.shape == (48, 48)
    assert img.dtype == np.float64
    assert float(np.ptp(img)) == 0.0
    assert float(img[0, 0]) == pytest.approx(0.3)


def test_a_uniform_slope_is_exactly_sec_theta_brighter():
    """傾き θ の一様斜面 → 平面に対する輝度比はちょうど sec θ(閉形式)。"""
    base = 0.2
    for slope in (0.25, 0.5, 1.0, 2.0):
        ramp = np.tile(np.linspace(0.0, slope * 47, 48), (48, 1))
        r = SM.sem_render(ramp, pixel_nm=1.0, base=base)
        theta = np.arctan(slope)
        measured = float(r[24, 24]) / base
        assert measured == pytest.approx(1.0 / np.cos(theta), abs=1e-9), \
            "slope %g: %.6f vs sec %.6f" % (slope, measured, 1.0 / np.cos(theta))


def test_the_bright_edge_width_matches_the_psf():
    """段差の明るい縁の幅(2 次モーメント σ)は PSF 幅に合う。

    段差の勾配は np.gradient で ~1 px に広がるので、測った σ は PSF 幅より
    わずかに広い(閉形式: σ_meas² ≈ psf_px² + w_step², w_step ≈ 1 px)。縁の幅は
    PSF と共に単調に増え、PSF 幅に 0.6 px 以内で一致する。
    """
    prev = -1.0
    for psf in (1.0, 2.0, 3.0, 4.0):
        H = np.zeros((80, 80))
        H[:, 40:] = 30.0
        im = SM.sem_render(H, psf_px=psf, base=0.5)
        prof = im[40] - im[40].min()
        x = np.arange(prof.size, dtype=np.float64)
        m = prof.sum()
        cen = (x * prof).sum() / m
        sig = float(np.sqrt(((x - cen) ** 2 * prof).sum() / m))
        assert sig > prev, "縁の幅が PSF と共に増えない: psf=%g sigma=%.3f" % (psf, sig)
        assert sig >= psf, "縁の幅が PSF より狭い: psf=%g sigma=%.3f" % (psf, sig)
        prev = sig
        assert abs(sig - psf) < 0.6, \
            "psf=%g: 縁の幅 σ=%.3f が PSF から 0.6 px 以上ずれた" % (psf, sig)


def test_shot_noise_falls_with_dose():
    """ショット雑音は dose（画素あたり電子数）で決まる: dose が増えると平坦面の σ が減る。"""
    flat = np.zeros((64, 64))
    s_lo = float(np.std(SM.sem_render(flat, dose=20.0, seed=1, base=0.5)))
    s_hi = float(np.std(SM.sem_render(flat, dose=500.0, seed=1, base=0.5)))
    assert s_lo > s_hi > 0.0, "雑音が dose で下がらない: lo=%.4f hi=%.4f" % (s_lo, s_hi)


def test_charging_adds_a_monotone_horizontal_gradient():
    """帯電は横方向の緩い輝度勾配を足す(収差でなく系統的な明暗)。"""
    flat = np.zeros((32, 48))
    img = SM.sem_render(flat, charging=0.6, base=0.4)
    col_mean = img.mean(axis=0)
    assert col_mean[-1] > col_mean[0], "帯電の勾配が横に出ていない"
    assert float(np.ptp(img)) > 0.0


def test_fail_closed_on_bad_input():
    """不正入力は黙って通さず明示拒否(fail-closed)。"""
    with pytest.raises(ValueError):
        SM.sem_render(np.zeros((4, 4, 3)))          # 3-D
    with pytest.raises(ValueError):
        SM.sem_render(np.full((4, 4), np.nan))      # 非有限
    with pytest.raises(ValueError):
        SM.sem_render(np.zeros((4, 4)), psf_px=0.0)  # 非正
    with pytest.raises(ValueError):
        SM.sem_render(np.zeros((4, 4)), base=0.0)    # 範囲外


# --------------------------------------------------------------------------- #
# 2. 台帳と公開経路(登録面を 1 つ落とすと静かに消える)                        #
# --------------------------------------------------------------------------- #
def test_the_ledger_lists_the_op_and_nothing_is_missing():
    import opsgenerative as og

    assert "sem_render" in og.list_ops("sem")
    assert og.missing() == []
    assert "sem" in og.categories()


def test_the_op_is_reachable_from_the_public_tier():
    import fullseye as fs

    assert hasattr(fs.ledger, "sem_render")
    out = fs.ledger.sem_render(np.zeros((16, 16)))
    assert out.shape == (16, 16)


def test_the_typed_catalog_declares_the_op():
    import typed_catalog as tc

    rows = [r for r in tc.catalog() if r[0] == "sem_render"]
    assert len(rows) == 1
    name, dim, ins, out, fn = rows[0]
    assert dim == "generative" and ins == ["image2d"] and out == "image2d"


def test_the_fuzzer_can_actually_run_the_op():
    """★「登録したのに一度も計算しない」を避ける。image2d の種で実際に走ること。"""
    sys.path.insert(0, str(ROOT / "tools"))
    import chain_fuzz as cf

    assert "image2d" in cf.TYPE_CHECKS
    seed = cf.make_generators()["image2d"](np.random.default_rng(0))
    out = SM.sem_render(seed)
    assert cf.TYPE_CHECKS["image2d"](out), "出力が image2d 契約を満たさない"


def test_the_op_summary_has_a_matching_japanese_fingerprint():
    """op_summary.json の指紋が docstring の 1 行目と一致する(古い訳が出ないため)。"""
    sys.path.insert(0, str(ROOT / "tools"))
    import json
    import opdocs

    line = SM.sem_render.__doc__.strip().splitlines()[0]
    d = json.loads((ROOT / "docs" / "i18n" / "op_summary.json").read_text(encoding="utf-8"))
    e = d["summaries"]["generative/sem_render"]
    assert e["fp"] == opdocs.fingerprint(line), "指紋が docstring 1 行目と合わない"
    for lang in ("en", "zh", "tw", "ko", "de", "hi"):
        assert e[lang].strip(), "翻訳 %s が空" % lang
