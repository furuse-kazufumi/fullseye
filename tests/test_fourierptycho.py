# -*- coding: utf-8 -*-
"""fourierptycho(フーリエ・タイコグラフィ)の門: 閉形式・真値のチャート・収束と拒否の契約。"""
from __future__ import annotations

import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import coherent  # noqa: E402
import fourierptycho as FP  # noqa: E402
import opsoptics  # noqa: E402
from metriccontract import MetricContractError  # noqa: E402


def _small_stack(**kw):
    t = FP.fp_usaf_target(groups=(8, 9), elements=(1, 2, 3), shape=(128, 128))
    args = dict(n_side=5)
    args.update(kw)
    return t, FP.fp_capture(t["amplitude"], 0.5 * t["coverage"], **args)


# --------------------------------------------------------------------------- 閉形式
def test_overlap_ratio_matches_counted_circle_intersection():
    for a in (0.05, 0.2, 0.315, 0.5, 0.8):
        r = 1.0
        d = 2 * a * r
        g = np.linspace(-1.2, 1.2 + d, 1801)
        X, Y = np.meshgrid(g, np.linspace(-1.2, 1.2, 1501))
        inside = (X ** 2 + Y ** 2) <= 1
        both = inside & (((X - d) ** 2 + Y ** 2) <= 1)
        assert abs(FP._circle_overlap_fraction(d, r) - both.sum() / inside.sum()) < 3e-3
    assert FP._circle_overlap_fraction(0.0, 1.0) == 1.0
    assert FP._circle_overlap_fraction(2.0, 1.0) == 0.0


def test_design_closed_forms():
    d = FP.fp_design(na_obj=0.1, wavelength_um=0.532, led_pitch_mm=4.0, led_distance_mm=70.0, n_side=13,
                     magnification=4.0, camera_pixel_um=5.2, target_na=0.40)
    e = 6 * 4.0
    assert d["na_illumination_max_axis"] == pytest.approx(e / math.hypot(e, 70.0), rel=1e-12)
    assert d["na_synthetic"] == pytest.approx(0.1 + e / math.hypot(e, 70.0), rel=1e-12)
    assert d["coherent_cutoff_period_um"] == pytest.approx(0.532 / d["na_synthetic"], rel=1e-12)
    assert d["r_cam"] == pytest.approx(0.532 * 4.0 / (2 * 0.1 * 5.2), rel=1e-12)
    assert d["pixel_sampling_ok"] and d["overlap_ok"] and d["boundary_ok"]
    assert d["n_side_needed"] == 13 and d["n_brightfield"] == 9
    # 重なりは中心で最小、端で大きい(sinθ の刻みは外ほど狭い)
    assert d["overlap_ratio_edge"] > d["overlap_ratio_centre"]
    # 明視野と暗視野の境の LED を数える
    b = FP.fp_design(led_pitch_mm=7.0, led_distance_mm=70.0, n_side=7)
    assert b["boundary_leds"] == 4 and not b["boundary_ok"]
    with pytest.raises(ValueError):
        FP.fp_design(na_obj=1.2)


def test_usaf_target_periods_and_coverage():
    t = FP.fp_usaf_target(groups=(8, 9), elements=(1, 4), shape=(128, 128), supersample=8)
    assert [(e["group"], e["element"]) for e in t["elements"]] == [(8, 1), (8, 4), (9, 1), (9, 4)]
    fine = 0.325 / 8
    assert len(t["elements"]) == 4
    for e in t["elements"]:
        assert e["period_nominal_um"] == pytest.approx(1000.0 / 2 ** (e["group"] + (e["element"] - 1) / 6), rel=1e-12)
        assert abs(e["period_um"] - e["period_nominal_um"]) <= fine + 1e-12
    # 被覆率の総和 = 棒の面積(1 要素 = 2 向き × 3 本 × 幅 × 5 幅)
    area = sum(2 * 3 * (e["period_um"] / 2) * (5 * e["period_um"] / 2) for e in t["elements"]) / 0.325 ** 2
    assert t["coverage"].sum() == pytest.approx(area, rel=1e-9)
    p = FP.fp_usaf_target(groups=(9,), elements=(1,), shape=(64, 64), kind="phase", phase_rad=0.7)
    assert np.allclose(p["amplitude"], 1.0) and p["phase"].max() == pytest.approx(0.7)
    # kind="both": 振幅は amplitude と、位相は phase と同じ(棒が暗く、位相も進む)
    a = FP.fp_usaf_target(groups=(9,), elements=(1,), shape=(64, 64), kind="amplitude", bar_value=0.3)
    b = FP.fp_usaf_target(groups=(9,), elements=(1,), shape=(64, 64), kind="both", bar_value=0.3, phase_rad=0.7)
    assert np.array_equal(b["amplitude"], a["amplitude"]) and np.array_equal(b["phase"], p["phase"])
    with pytest.raises(ValueError):
        FP.fp_usaf_target(groups=(9,), elements=(1,), shape=(64, 64), kind="mixed")


# --------------------------------------------------------------------------- 撮像
def test_capture_centre_led_is_the_coherent_image():
    """中心の LED(垂直入射)・収差なし・雑音なし の像は coherent.coherent_image と一致する(端を除く)。"""
    t = FP.fp_usaf_target(groups=(8,), elements=(1, 2), shape=(128, 128))
    st = FP.fp_capture(t["amplitude"], None, n_side=1, photons=1e12, read_noise_e=0.0, downsample=1,
                       pixel_um=1.0, pad_px=0)
    ref = coherent.coherent_image(t["amplitude"], None, cutoff=0.1 * 1.0 / 0.532)
    got = st["images"][0] / st["photons"]
    m = slice(8, -8)
    assert np.abs(got[m, m] - ref[m, m]).max() < 2e-3


def test_capture_metadata_and_refusals():
    t, st = _small_stack()
    assert st["kind"] == "fp_stack" and st["images"].shape == (25, 32, 32)
    assert np.all(np.diff(st["na_illumination"]) >= -1e-12)          # 照明の NA の小さい順
    assert st["led_brightness"][0] == pytest.approx(1.0)
    assert set(np.unique(st["exposure"])) == {1.0, 8.0}
    with pytest.raises(ValueError, match="sampling"):
        FP.fp_capture(t["amplitude"], None, pixel_um=1.0, downsample=4)     # 4 µm > λ/(2 NA) = 2.66 µm
    with pytest.raises(ValueError, match="unknown aberration"):
        FP.fp_capture(t["amplitude"], None, pupil_aberration={"trefoil": 0.1})
    with pytest.raises(ValueError):
        FP.fp_capture(t["amplitude"][:, :100], None)


def test_reflection_height_is_round_trip_phase():
    h = np.zeros((64, 64))
    h[20:40, 20:40] = 0.05
    a = FP.fp_capture(np.ones((64, 64)), 4 * np.pi * h / 0.532, n_side=3, photons=1e12, read_noise_e=0.0)
    b = FP.fp_capture(np.ones((64, 64)), None, height_um=h, n_side=3, photons=1e12, read_noise_e=0.0)
    assert np.allclose(a["images"], b["images"], rtol=1e-6, atol=1e-3)


# --------------------------------------------------------------------------- 復元と収束の契約
def test_reconstruct_converges_and_returns_the_contract():
    _, st = _small_stack()
    r = FP.fp_reconstruct(st)
    for k in ("converged", "reason", "n_iter", "residual", "residual_history", "na_synthetic", "start_disagreement"):
        assert k in r
    assert r["converged"] and r["reason"].startswith("stalled")
    assert r["n_iter"] == len(r["residual_history"]) and r["residual"] == r["residual_history"][-1]
    assert r["na_synthetic"] == pytest.approx(0.1 + float(st["na_illumination"].max()), rel=1e-12)
    up = r["upsample"]
    # 自動の上げ倍率: 照明の NA が入り、画素が λ/(2 NA_syn) 以下になる最小の整数
    assert r["pixel_um"] == pytest.approx(1.3 / up) and r["pixel_um"] <= 0.532 / (2 * r["na_synthetic"])
    assert r["amplitude"].shape == (32 * up, 32 * up)


def test_reconstruct_refuses_with_the_record_attached():
    _, st = _small_stack()
    with pytest.raises(FP.FPNotConvergedError) as ei:
        FP.fp_reconstruct(st, n_iter=2)
    assert isinstance(ei.value, MetricContractError) and isinstance(ei.value, ValueError)
    rec = ei.value.record
    assert rec["converged"] is False and rec["reason"].startswith("max_iterations") and len(rec["residual_history"]) == 2
    rec2 = FP.fp_reconstruct(st, n_iter=2, on_fail="record")
    assert rec2["converged"] is False


def test_too_little_overlap_is_refused():
    """重なり 7 % の LED のピッチでは、2 本の初期値が別の答えに着くか回数が尽きて拒否される。"""
    t = FP.fp_usaf_target(groups=(8, 9), elements=(1, 2, 3), shape=(128, 128))
    st = FP.fp_capture(t["amplitude"], 0.5 * t["coverage"], n_side=5, led_pitch_mm=12.0)
    assert FP.fp_design(led_pitch_mm=12.0, n_side=5)["overlap_ratio_centre"] < 0.1
    rec = FP.fp_reconstruct(st, pupil_update=False, on_fail="record")
    assert not rec["converged"]
    assert rec["reason"].startswith(("non-unique", "max_iterations"))


def test_flipped_k_gives_the_conjugate():
    """照明の k の符号の反転は、強度だけでは区別できない(位相の符号が反転した像に着き、残差は同じ)。"""
    _, st = _small_stack()
    a = FP.fp_reconstruct(st, pupil_update=False, starts=1)
    b = FP.fp_reconstruct(dict(st, kx=-st["kx"], ky=-st["ky"]), pupil_update=False, starts=1)
    inner = slice(a["margin_px"], 128 - a["margin_px"])
    d, _ = FP._disagreement(np.conj(a["field"]), b["field"], inner)
    assert d < 1e-6
    assert b["residual"] == pytest.approx(a["residual"], rel=1e-9)


def test_reconstruction_is_closer_to_the_truth_than_the_bright_field_image():
    """復元を真値と比べる: 振幅のチャートで、真値との相対誤差が明視野の 1 枚の拡大より 3 割以上小さい。
    像と LED の対応をずらした組(区別できる設定)は真値から離れ、拒否される。"""
    t = FP.fp_usaf_target(groups=(8, 9), elements=(1, 2, 3), shape=(128, 128))
    st = FP.fp_capture(t["amplitude"], None, n_side=5)
    r = FP.fp_reconstruct(st, upsample=4)                   # 高解像の格子 = 真値の格子(0.325 µm)
    m = r["margin_px"]
    s = slice(m, 128 - m)

    def err(X):
        X = X / np.mean(X[s, s])
        T = t["amplitude"] / np.mean(t["amplitude"][s, s])
        return float(np.linalg.norm(X[s, s] - T[s, s]) / np.linalg.norm(T[s, s]))

    bf = np.kron(np.sqrt(np.clip(st["images"][0], 0, None)), np.ones((4, 4)))
    assert r["converged"] and err(r["amplitude"]) < 0.25 and err(r["amplitude"]) < 0.7 * err(bf), (err(r["amplitude"]), err(bf))
    perm = np.arange(25)
    perm[9:] = np.roll(perm[9:], 1)
    bad = FP.fp_reconstruct(dict(st, images=st["images"][perm]), upsample=4, on_fail="record")
    assert not bad["converged"] and err(bad["amplitude"]) > err(r["amplitude"]) + 0.1


def test_known_phase_sample_fixes_the_k_sign_that_the_residual_cannot():
    """符号の取り違えは残差では見抜けない(両軸の反転は同じ残差で共役像に着く)。位相の符号が分かっている試料なら
    復元の位相と真値の相関の符号で分かる —— 実機の校正の手順をそのまま門にしたもの。"""
    t = FP.fp_usaf_target(groups=(8, 9), elements=(1, 2, 3), shape=(128, 128))
    ph = 0.8 * t["coverage"]                                  # 棒の位相は +0.8 rad(符号が既知)
    st = FP.fp_capture(np.ones((128, 128)), ph, n_side=5)

    def corr(r):
        m = r["margin_px"]
        s = slice(m, 128 - m)
        f = r["field"] * np.conj(np.mean(r["field"][s, s]))    # 大域の位相をそろえる
        return float(np.corrcoef(np.angle(f)[s, s].ravel(), ph[s, s].ravel())[0, 1])

    a = FP.fp_reconstruct(st, pupil_update=False, starts=1, upsample=4)
    b = FP.fp_reconstruct(dict(st, kx=-st["kx"], ky=-st["ky"]), pupil_update=False, starts=1, upsample=4)
    assert b["residual"] == pytest.approx(a["residual"], rel=1e-9)   # 残差は区別しない
    assert corr(a) > 0.5 and corr(b) < -0.5                           # 既知の位相は区別する
    # 片軸の反転も、残差が少し大きいだけで「収束」しうる(残差では検出できないことの裏づけ)
    c = FP.fp_reconstruct(dict(st, kx=-st["kx"]), pupil_update=False, starts=1, upsample=4, on_fail="record")
    assert corr(c) < 0.5


def test_zero_energy_images_are_refused():
    """全部 0 の像は残差 0 の自明な不動点に着く —— 収束と呼ばず ValueError。"""
    _, st = _small_stack()
    z = FP.fp_stack_from_images(np.zeros((25, 32, 32)), st["kx"] * 0.532, st["ky"] * 0.532, 0.532, 0.1, 1.3)
    for starts in (1, 2):
        with pytest.raises(ValueError, match="energy"):
            FP.fp_reconstruct(z, starts=starts, on_fail="record")


def test_single_start_is_marked_unchecked_and_a_large_residual_warns():
    _, st = _small_stack()
    one = FP.fp_reconstruct(st, starts=1)
    assert one["converged"] and one["uniqueness_checked"] is False and "uniqueness not checked" in one["reason"]
    two = FP.fp_reconstruct(st)
    assert two["uniqueness_checked"] is True and "uniqueness not checked" not in two["reason"]
    assert two["residual_warning"] is False and two["residual_ceiling"] == FP.RESIDUAL_WARN
    # 照明の k と無関係な乱数の像: 初期値 1 本なら停留して「収束」するが、残差が上限を超えて警告が出る
    rng = np.random.default_rng(1)
    g = FP.fp_stack_from_images(rng.random((25, 32, 32)) * 100 + 1, st["kx"] * 0.532, st["ky"] * 0.532, 0.532, 0.1, 1.3)
    rg = FP.fp_reconstruct(g, starts=1, on_fail="record")
    assert rg["residual"] > FP.RESIDUAL_WARN and rg["residual_warning"] is True and "warning" in rg["reason"]


def test_led_fit_outside_the_grid_is_a_named_error():
    """LED の幾何の当てはめが瞳の中心を高解像の格子の外へ置いたら、名前つきの ValueError(TypeError で落ちない)。"""
    _, st = _small_stack()
    xyz = st["led_xyz_mm"].copy()
    xyz[-1] = (50.0, 0.0, 0.01)                               # 1 個だけ横 90° 近くに置いた、当てはまらない LED
    with pytest.raises(ValueError, match="outside the high-resolution grid"):
        FP.fp_reconstruct(dict(st, led_xyz_mm=xyz), led_correction=True, on_fail="record", n_iter=8, starts=1)


def test_reconstruct_rejects_foreign_tables():
    with pytest.raises(ValueError, match="fp_stack"):
        FP.fp_reconstruct({"kind": "oct_ascan"})
    _, st = _small_stack()
    with pytest.raises(ValueError):
        FP.fp_reconstruct(dict(st, kx=st["kx"][:3]))
    with pytest.raises(ValueError, match="led_xyz_mm"):
        FP.fp_reconstruct({k: v for k, v in st.items() if k != "led_xyz_mm"}, led_correction=True)


def test_stack_from_images_orders_and_squares():
    _, st = _small_stack()
    perm = np.arange(25)[::-1]
    s2 = FP.fp_stack_from_images(np.sqrt(np.clip(st["images"][perm], 0, None)), st["kx"][perm] * 0.532,
                                 st["ky"][perm] * 0.532, 0.532, 0.1, 1.3, values="amplitude")
    assert np.allclose(s2["na_illumination"], np.sort(s2["na_illumination"]))
    assert np.allclose(s2["images"][0], np.clip(st["images"][0], 0, None))
    with pytest.raises(ValueError, match="sampling"):
        FP.fp_stack_from_images(st["images"], st["kx"] * 0.532, st["ky"] * 0.532, 0.532, 0.1, 3.0)
    with pytest.raises(ValueError):
        FP.fp_stack_from_images(st["images"], st["kx"][:4], st["ky"], 0.532, 0.1, 1.3)


# --------------------------------------------------------------------------- 要素の読み取り
def test_element_contrast_reads_truth_and_refuses_blur():
    from scipy import ndimage as ndi
    t = FP.fp_usaf_target(groups=(8, 9), elements=(1, 2, 3), shape=(128, 128))
    c = FP.fp_element_contrast(t["amplitude"], t)
    assert c["n_resolved"] == len(t["elements"]) and c["last_resolved"]["group"] == 9
    blur = FP.fp_element_contrast(ndi.gaussian_filter(t["amplitude"], 5.0), t)
    assert blur["n_resolved"] == 0
    bad = [dict(t["elements"][0], vertical_bars_box=(0, 10, 120, 140))]
    with pytest.raises(ValueError, match="outside"):
        FP.fp_element_contrast(t["amplitude"], bad)


def test_registered_in_opsoptics():
    want = {"fp_design", "fp_usaf_target", "fp_capture", "fp_stack_from_images", "fp_reconstruct", "fp_element_contrast"}
    got = list(opsoptics.list_ops("fpm"))
    assert set(got) == want and len(got) == len(want) and set(FP.__all__) == want
