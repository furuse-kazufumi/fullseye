# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""granular の門(粉体の山を画像で測る: 安息角・体積・質量・流動性・排出率を規則だけで、真値は閉形式・公表値・MuJoCo)。

numpy だけの門(常に走る):
 1. 円錐の閉形式(V = πR²H/3、H = R tan φ)の往復 1e-9、質量 m = ρ_b V、3 つ全部 / 1 つだけ渡すと ValueError
 2. 高さ図の体積 vs 閉形式(6 角度、400 px の山)1e-4
 3. 側面像 → φ の往復(雑音なし)0.01 度 —— 合成と計測の縁の模型が同じなので配管の検査(docstring に明記)
 4. 被覆率に一様雑音 ±0.1: edge 法 0.02 度、列和法は切り捨ての偏りで −0.4 度より低い(罠を数で残す)
 5. 高さ図の勾配ヒストグラムの最頻 vs 側面(σ 0.05 px)0.5 度
 6. Beverloo: 合成排出の高さ図列から指数 n = 2.5 ± 1 %、C = 0.58 ± 3 %、雑音なしは 1e-6; 値の手計算一致、D₀ ≤ k d は ValueError
 7. 裾の丸み / 頂の鈍り: 除外なしで偏り、15 % 除外で 0.02 度以内
 8. 分解能: 山 50 px で側面 0.3 度・25 px で 1 度、高さ図(σ 0.1 px)50 px で 1.5 度
 9. 傾いた基準面 β = 5 度: 左右の斜面 = 閉形式 atan(tan φ ± tan β)、左右差 ≈ 2β の警報(datum_tilt_check)、tan 補正で 30.00、
    高さ図の最頻は地面そのもの(5 度)で datum を渡せば 30.00
10. 流動性区分(USP <1174> 表 1)の 16 境界値、25 度未満は tabulated=False、0 / 90 は ValueError
11. 綴り壊し(method / cone / solver)と山が写っていない・切れている → ValueError
12. スプーンの規則 θ_c = φ − atan(2h₀/L)(厳密な tan(φ − θ)、2026-10-05 まで小角の近似 atan(tan φ − 2h₀/L))、h₀ → 0 で φ、単調、
    壁の高さは θ_c 以下で効かない; 回帰: 厳密解の値、小角で旧式と一致、口に壁の無い器は θ = 0⁺ からこぼれる
13. 容器の充填率(0.63、面の傾き 3 度)0.002 / 0.05 度
14. 動画からの質量(雑音なしの往復)1e-4、排出率の帯当て(3 コマ未満は ValueError)
15. MJCF 文字列(mujoco 不要): 球の数・板 28 枚・contact_tc < 2 timestep は ValueError、孔がビンより大きいと ValueError
16. 入口: __all__ の全部が実在、docstring に ']( ' のリンク無し
mujoco が要る門(無ければ skip、module fixture で 1 回だけ):
17. 山ができる(逃げ < 5 %、速度 < 0.3 m/s、高さ > 6R)、側面の φ が公表値 25.2 ± 0.8 度(1 mm ガラス球)の −7〜+1 度、高さ図との差 4 度、
    排出率 vs Beverloo(等価直径)が桁で合う
"""
from __future__ import annotations

import math

import numpy as np
import pytest

import granular as G

PHIS = (20.0, 25.0, 30.0, 35.0, 40.0, 45.0)


def _raises(fn, *a, **k):
    try:
        fn(*a, **k)
    except ValueError:
        return True
    return False


# ── 1. 円錐の閉形式 ─────────────────────────────────────────────────────────
def test_cone_closed_form_round_trips():
    c = G.heap_volume_cone(R=0.3, H=0.2)
    assert c["V"] == pytest.approx(math.pi / 3 * 0.09 * 0.2, rel=1e-12)
    c2 = G.heap_volume_cone(R=0.3, phi_deg=c["phi_deg"])
    c3 = G.heap_volume_cone(H=c2["H"], phi_deg=c["phi_deg"])
    assert c2["H"] == pytest.approx(0.2, rel=1e-9) and c3["R"] == pytest.approx(0.3, rel=1e-9)
    assert G.heap_mass(c["V"], 1500.0) == pytest.approx(1500.0 * c["V"], rel=1e-12)
    assert _raises(G.heap_volume_cone, R=1.0, H=1.0, phi_deg=45.0) and _raises(G.heap_volume_cone, R=1.0)
    assert _raises(G.heap_mass, -1.0, 1500.0) and _raises(G.heap_mass, 1.0, 0.0)


# ── 2. 高さ図の体積 ────────────────────────────────────────────────────────
def test_heightmap_volume_matches_closed_form():
    errs = []
    for phi in PHIS:
        w = G.heap_synth_cone(phi, 200)
        errs.append(abs(G.heap_volume_heightmap(w["heightmap"], w["pitch"]) / w["truth"]["V_cone"] - 1))
    assert len(errs) == len(PHIS)
    assert max(errs) < 1e-4


# ── 3〜5. 側面像と高さ図 ────────────────────────────────────────────────────
def test_silhouette_round_trip_and_heightmap_mode():
    e_sil, e_cmp = [], []
    for phi in PHIS:
        w = G.heap_synth_cone(phi, 200)
        s = G.repose_angle_silhouette(w["side"])
        hm = w["heightmap"] + np.random.default_rng(int(phi)).normal(0.0, 0.05 * w["pitch"], w["heightmap"].shape)
        h = G.repose_angle_heightmap(hm, w["pitch"])
        e_sil.append(abs(s["phi_deg"] - phi))
        e_cmp.append(abs(h["phi_deg"] - s["phi_deg"]))
        assert s["n_left"] >= 8 and s["n_right"] >= 8 and abs(s["asymmetry_deg"]) < 0.05
    assert len(e_sil) == len(PHIS)
    assert max(e_sil) < 0.01                      # 合成と計測の縁の模型が同じ → 配管の検査(独立な被験者は雑音と MuJoCo)
    assert max(e_cmp) < 0.5                       # 高さ雑音 σ 0.05 px は最頻を +0.12 度動かす(実測)


def test_silhouette_under_noise_edge_method_vs_column_sum_bias():
    errs = []
    for seed in range(5):
        for phi in (25.0, 35.0):
            w = G.heap_synth_cone(phi, 200, noise=0.1, seed=seed)
            errs.append(G.repose_angle_silhouette(w["side"])["phi_deg"] - phi)
    assert len(errs) == 10
    assert max(abs(e) for e in errs) < 0.02
    w = G.heap_synth_cone(30.0, 200, noise=0.1, seed=0)
    bias = G.repose_angle_silhouette(w["side"], method="column_sum")["phi_deg"] - 30.0
    assert bias < -0.4                            # [0, 1] に切った雑音で粉の平均値が 0.975 → tan φ がその比で縮む(−0.62 度、実測)


# ── 6. Beverloo ────────────────────────────────────────────────────────────
def test_beverloo_exponent_from_synthetic_video_and_value():
    D0s = np.array([0.02, 0.025, 0.03, 0.035, 0.04, 0.05])
    Ws, Wt = [], []
    for D0 in D0s:
        ds = G.discharge_synth(D0, 0.001, 1500.0, 30.0, 1.5e-3, 2.0, n_frames=6, grid=256, noise=0.5e-3, seed=3)
        Ws.append(G.dispense_mass_from_video(ds["frames"], 1.5e-3, 1500.0, ds["times"])["rate"])
        Wt.append(ds["W"])
    f = G.beverloo_fit(D0s, Ws, 0.001, 1500.0)
    f0 = G.beverloo_fit(D0s, Wt, 0.001, 1500.0)
    assert f["n"] == pytest.approx(2.5, rel=0.01) and f["C"] == pytest.approx(0.58, rel=0.03)
    assert f0["n"] == pytest.approx(2.5, abs=1e-6)
    Wh = 0.58 * 1500.0 * math.sqrt(9.80665) * (0.03 - 1.4 * 0.001) ** 2.5
    assert G.beverloo_rate(0.03, 0.001, 1500.0) == pytest.approx(Wh, abs=1e-12)
    assert _raises(G.beverloo_rate, 0.0014, 0.001, 1500.0) and _raises(G.beverloo_rate, 0.03, 0.001, -5.0)
    assert _raises(G.beverloo_fit, [0.02, 0.03], [1.0, 2.0], 0.001, 1500.0)


# ── 7. 裾と頂 ──────────────────────────────────────────────────────────────
@pytest.mark.parametrize("kw,limit", [({"toe_round_px": 60}, -0.1), ({"apex_blunt_px": 60}, -0.3)])
def test_toe_rounding_and_apex_blunting_bias_and_exclusion(kw, limit):
    w = G.heap_synth_cone(30.0, 200, noise=0.1, seed=0, **kw)
    b_no = G.repose_angle_silhouette(w["side"], toe_frac=0.0, apex_frac=0.0)["phi_deg"] - 30.0
    b_ex = G.repose_angle_silhouette(w["side"])["phi_deg"] - 30.0
    assert b_no < limit
    assert abs(b_ex) < 0.02


# ── 8. 分解能 ──────────────────────────────────────────────────────────────
def test_resolution_small_heaps():
    res = {}
    for W in (25, 50):
        es, eh = [], []
        for seed in range(3):
            for phi in (25.0, 35.0):
                w = G.heap_synth_cone(phi, W / 2, noise=0.1, seed=seed)
                es.append(abs(G.repose_angle_silhouette(w["side"])["phi_deg"] - phi))
                hm = w["heightmap"] + np.random.default_rng(seed).normal(0.0, 0.1 * w["pitch"], w["heightmap"].shape)
                eh.append(abs(G.repose_angle_heightmap(hm, w["pitch"])["phi_deg"] - phi))
        assert len(es) == 6
        res[W] = (max(es), max(eh))
    assert res[50][0] < 0.3 and res[25][0] < 1.0 and res[50][1] < 1.5


# ── 9. 傾いた基準面 ────────────────────────────────────────────────────────
def test_tilted_datum_adds_angles_and_the_check_alarms():
    beta = 5.0
    w = G.heap_synth_cone(30.0, 200, ground_tilt_deg=beta)
    s = G.repose_angle_silhouette(w["side"])
    exp_l = math.degrees(math.atan(math.tan(math.radians(30.0)) + math.tan(math.radians(beta))))
    exp_r = math.degrees(math.atan(math.tan(math.radians(30.0)) - math.tan(math.radians(beta))))
    assert s["phi_left_deg"] == pytest.approx(exp_l, abs=0.05) and s["phi_right_deg"] == pytest.approx(exp_r, abs=0.05)
    assert s["ground_deg"] == pytest.approx(beta, abs=0.05)
    assert G.repose_angle_silhouette(w["side"], correct_ground=True)["phi_deg"] == pytest.approx(30.0, abs=0.02)
    d = G.datum_tilt_check(s)
    assert d["alarm"] and d["asymmetry_deg"] > 7.0
    assert d["phi_shear_deg"] == pytest.approx(30.0, abs=0.02) and d["beta_shear_deg"] == pytest.approx(beta, abs=0.05)
    assert abs(d["phi_roll_deg"] - d["phi_shear_deg"]) > 0.1          # 回転型とせん断型は 1 次で違う
    flat = G.repose_angle_silhouette(G.heap_synth_cone(30.0, 200)["side"])
    assert not G.datum_tilt_check(flat)["alarm"]
    h_raw = G.repose_angle_heightmap(w["heightmap"], w["pitch"])
    h_cor = G.repose_angle_heightmap(w["heightmap"], w["pitch"], ground=w["ground"])
    assert h_raw["phi_deg"] == pytest.approx(beta, abs=0.5)            # 地面のセルがヒストグラムを乗っ取る
    assert h_cor["phi_deg"] == pytest.approx(30.0, abs=0.02)
    assert _raises(G.datum_tilt_check, {"phi_left_deg": 30.0}) and _raises(G.datum_tilt_check, s, warn_deg=0.0)


# ── 10. 流動性区分 ─────────────────────────────────────────────────────────
@pytest.mark.parametrize("phi,cls", [(25.0, "excellent"), (30.4, "excellent"), (30.5, "good"), (35.0, "good"), (36.0, "fair"), (40.0, "fair"),
                                     (41.0, "passable"), (45.0, "passable"), (46.0, "poor"), (55.0, "poor"), (56.0, "very poor"),
                                     (65.0, "very poor"), (66.0, "very, very poor"), (80.0, "very, very poor")])
def test_flowability_classes(phi, cls):
    assert G.powder_flowability_class(phi)["cls"] == cls


def test_flowability_table_bounds():
    assert G.powder_flowability_class(24.0)["tabulated"] is False and G.powder_flowability_class(25.0)["tabulated"] is True
    assert _raises(G.powder_flowability_class, 0.0) and _raises(G.powder_flowability_class, 90.0)
    assert G.powder_flowability_class(80.0)["band_upper_deg"] is None          # inf を返さない(chain_fuzz の NONFINITE、2026-10-05)
    assert G.powder_flowability_class(33.0)["band_upper_deg"] == 35.0


# ── 11. fail-closed ────────────────────────────────────────────────────────
def test_spelling_breaks_and_no_heap_fail_closed():
    w0 = G.heap_synth_cone(30.0, 200)
    assert _raises(G.repose_angle_heightmap, w0["heightmap"], w0["pitch"], method="Horn")
    assert _raises(G.repose_angle_silhouette, w0["side"], method="edges")
    assert _raises(G.heap_synth_cone, 30.0, 200, ground_tilt_deg=60.0)
    assert _raises(G.cone_profile_px, [0.0], 10.0, 30.0, toe_round_px=50.0, apex_blunt_px=50.0)
    assert _raises(G.heap_scene_mjcf, 10, 0.004, solver="newton") and _raises(G.heap_scene_mjcf, 10, 0.004, cone="Elliptic")
    blank = np.zeros((64, 96))
    cut = w0["side"][int(w0["side"].shape[0] * 0.5):, :]
    edge = w0["side"][:, int(w0["truth"]["apex_col"]):]
    assert _raises(G.repose_angle_silhouette, blank) and _raises(G.repose_angle_silhouette, cut) and _raises(G.repose_angle_silhouette, edge)
    assert _raises(G.repose_angle_heightmap, np.zeros((64, 64)), 1e-3) and _raises(G.container_fill_level, blank)
    assert _raises(G.repose_angle_silhouette, w0["side"] * 2.0)


# ── 12. スプーン ───────────────────────────────────────────────────────────
def test_spoon_tilt_rule():
    assert G.spoon_tilt_critical(30.0, 0.05, 1e-7) == pytest.approx(30.0, abs=1e-3)
    thc = G.spoon_tilt_critical(30.0, 0.05, 0.005)
    assert thc == pytest.approx(30.0 - math.degrees(math.atan(0.2)), abs=1e-9)        # 18.690(旧式は 20.674)
    fr = [G.spoon_tilt_dispense(th, 30.0, 0.05, 0.005)["fraction"] for th in np.linspace(0.0, 45.0, 91)]
    assert len(fr) == 91
    assert all(b >= a - 1e-12 for a, b in zip(fr[:-1], fr[1:]))
    assert G.spoon_tilt_dispense(thc - 0.5, 30.0, 0.05, 0.005)["fraction"] == 0.0
    assert G.spoon_tilt_dispense(30.0, 30.0, 0.05, 0.005)["fraction"] == 1.0
    assert G.spoon_tilt_dispense(15.0, 30.0, 0.05, 0.005, h_wall=10.0)["fraction"] == pytest.approx(G.spoon_tilt_dispense(15.0, 30.0, 0.05, 0.005)["fraction"], abs=1e-12)
    assert _raises(G.spoon_tilt_dispense, 95.0, 30.0, 0.05, 0.005)
    assert _raises(G.spoon_tilt_dispense, 5.0, 30.0, 0.05, 0.005, lip="none") and _raises(G.spoon_tilt_critical, 30.0, 0.05, 0.005, lip=1)
    assert _raises(G.spoon_tilt_dispense, 5.0, 30.0, 0.05, 0.005, h_wall=0.004, lip="open")


def _old_small_angle_fraction(theta, phi, L, h0):
    """2026-10-05 までの式(楔の傾き tan φ − tan θ)。回帰の比較にだけ使う。"""
    s = math.tan(math.radians(phi)) - math.tan(math.radians(theta))
    A = 0.5 * L * L * s if s > 0.0 else 0.0
    return 1.0 - min(A, L * h0) / (L * h0)


def test_spoon_tilt_exact_wedge_regression():
    """厳密な楔 tan(φ − θ) の値そのもの、小角で旧式(tan φ − tan θ)と一致すること、口に壁の無い器(2026-10-05)。"""
    L, h0 = 0.05, 0.005
    # 厳密解: 保持断面 = ½ L² tan(φ − θ)(θ_c より先)。θ = 25°・φ = 30° で tan 5°
    r = G.spoon_tilt_dispense(25.0, 30.0, L, h0)
    assert r["retained_area"] == pytest.approx(0.5 * L * L * math.tan(math.radians(5.0)), rel=1e-12)
    assert r["fraction"] == pytest.approx(1.0 - 0.5 * L * math.tan(math.radians(5.0)) / h0, rel=1e-12)
    # 差の例: θ = 10°、φ = 30° で旧式の楔の傾きは厳密の 1.102 倍(約 10 %)
    old = math.tan(math.radians(30.0)) - math.tan(math.radians(10.0))
    assert old / math.tan(math.radians(20.0)) == pytest.approx(1.1018, abs=1e-4)
    # 小角では旧式と一致する(φ = 2°: θ_c の差 < 0.1 %、割合の差 < 1e-3)
    phi, hh = 2.0, 0.0002
    old_thc = math.degrees(math.atan(math.tan(math.radians(phi)) - 2.0 * hh / L))
    assert G.spoon_tilt_critical(phi, L, hh) == pytest.approx(old_thc, rel=1e-3)
    ths = np.linspace(0.0, phi, 41)
    assert len(ths) == 41
    assert max(abs(G.spoon_tilt_dispense(t, phi, L, hh)["fraction"] - _old_small_angle_fraction(t, phi, L, hh)) for t in ths) < 1e-3
    # 大きい角では違う(φ = 30°、h0 5 mm で θ_c 18.69° と 20.67°)
    assert G.spoon_tilt_critical(30.0, L, h0) < math.degrees(math.atan(math.tan(math.radians(30.0)) - 0.2)) - 1.9
    # 口に壁の無い器: θ = 0⁺ からこぼれ、θ_c = 0、θ ≥ φ で 1、単調、A(0) = L h0 − h0²/(2 tan φ)
    o = [G.spoon_tilt_dispense(t, 30.0, L, h0, lip="open")["fraction"] for t in np.linspace(0.0, 30.0, 61)]
    assert len(o) == 61
    assert o[0] == 0.0 and o[1] > 0.0 and o[-1] == 1.0 and all(b >= a - 1e-15 for a, b in zip(o, o[1:]))
    assert G.spoon_tilt_critical(30.0, L, h0, lip="open") == 0.0
    assert G.spoon_tilt_dispense(0.0, 30.0, L, h0, lip="open")["initial_area"] == pytest.approx(
        L * h0 - h0 * h0 / (2.0 * math.tan(math.radians(30.0))), rel=1e-12)


# ── 13. 容器 ───────────────────────────────────────────────────────────────
def test_container_fill_level():
    cs = G.container_synth(0.63, 3.0)
    cf = G.container_fill_level(cs["side"])
    assert cf["fill_frac"] == pytest.approx(0.63, abs=0.002) and cf["surface_tilt_deg"] == pytest.approx(3.0, abs=0.05)
    assert _raises(G.container_synth, 1.2) and _raises(G.container_synth, 0.99, 20.0)


# ── 14. 動画からの質量と排出率の帯当て ─────────────────────────────────────
def test_mass_from_video_and_discharge_band_fit():
    ds = G.discharge_synth(0.03, 0.001, 1500.0, 30.0, 1.5e-3, 2.0, n_frames=6, grid=256)
    m = G.dispense_mass_from_video(ds["frames"], 1.5e-3, 1500.0, ds["times"])
    assert m["rate"] == pytest.approx(ds["W"], rel=1e-4) and m["masses"][-1] == pytest.approx(ds["masses"][-1], rel=1e-4)
    assert _raises(G.dispense_mass_from_video, ds["frames"][:1], 1.5e-3, 1500.0, ds["times"][:1])
    t = np.linspace(0.0, 2.0, 11)
    r = G.hopper_discharge_rate(0.5 * t, t, 1.0)
    assert r["rate"] == pytest.approx(0.5, abs=1e-12) and r["n_frames"] == 5
    assert _raises(G.hopper_discharge_rate, np.array([0.0, 0.5, 1.0]), np.array([0.0, 1.0, 2.0]), 1.0)     # 帯に 1 コマ
    assert _raises(G.hopper_discharge_rate, 0.5 * t, t[::-1], 1.0)
    assert _raises(G.discharge_synth, 0.3, 0.001, 1500.0, 30.0, 1.5e-3, 20.0, n_frames=3, grid=64)        # 山が格子からはみ出す


# ── 15. MJCF 文字列 ────────────────────────────────────────────────────────
def test_scene_mjcf_string_without_mujoco():
    sc = G.heap_scene_mjcf(60, 0.004, seed=1)
    assert sc["xml"].count("<freejoint/>") == 60 and sc["positions"].shape == (60, 3)
    assert sc["xml"].count('type="box"') == 24 + 4 and sc["xml"].count('type="plane"') == 1
    assert sc["info"]["mass_total"] == pytest.approx(60 * 2500.0 * 4 / 3 * math.pi * 0.004 ** 3, rel=1e-12)
    assert sc["info"]["bulk_density_bin"] > 0.0
    assert _raises(G.heap_scene_mjcf, 60, 0.004, contact_tc=0.002, timestep=0.0015)
    assert _raises(G.heap_scene_mjcf, 60, 0.004, orifice_d=0.2)
    assert _raises(G.heap_scene_mjcf, 0, 0.004)


# ── 16. 入口 ───────────────────────────────────────────────────────────────
def test_entry_points_exist_and_docstrings_have_no_markdown_links():
    assert len(G.__all__) >= 29
    for name in G.__all__:
        obj = getattr(G, name)
        if callable(obj):
            assert (obj.__doc__ or "").strip(), name
            assert "](" not in obj.__doc__, name


# ── 17. MuJoCo(第 2 実装) ────────────────────────────────────────────────
@pytest.fixture(scope="module")
def mj_heap():
    pytest.importorskip("mujoco")
    r = G.heap_mujoco_pour()
    return r


def test_mujoco_heap_forms_and_repose_matches_published(mj_heap):
    r = mj_heap
    info = r["model_info"]
    sel = G.heap_spheres_select(r["pos"], r["radius"], info["orifice_height"], info["bin_radius"])
    heap = sel["pos"]
    assert sel["n_runaway"] < 0.05 * info["n"] and info["max_speed_end"] < 0.3 and heap[:, 2].max() > 6 * r["radius"]
    pitch, extent, height = 0.0015, 0.16, 0.07
    phis = []
    for az in (0.0, 45.0, 90.0, 135.0):
        a = math.radians(az)
        R = np.array([[math.cos(a), -math.sin(a), 0.0], [math.sin(a), math.cos(a), 0.0], [0.0, 0.0, 1.0]])
        sil = G.spheres_to_silhouette(heap @ R.T, r["radius"], pitch, extent, height)
        phis.append(G.repose_angle_silhouette(sil, toe_frac=0.2, apex_frac=0.2)["phi_deg"])
    assert len(phis) == 4
    phi_s = float(np.mean(phis))
    pub = G.GLASS_BEADS_REPOSE_PUBLISHED["phi_deg"]
    assert -7.0 < phi_s - pub < 1.0                 # 初回実測 −3.6〜−5.5 度、組込み時 −3.0(剛体球・MuJoCo の転がり模型・山が 5 粒径)
    hm = G.spheres_to_heightmap(heap, r["radius"], pitch, extent)
    k = 2 * int(round(2 * r["radius"] / pitch)) + 1
    h = G.repose_angle_heightmap(hm, pitch, bin_deg=1.0, min_rel_height=0.2, max_rel_height=0.8, smooth_cells=k)
    assert abs(h["phi_median_deg"] - phi_s) < 4.0


def test_mujoco_discharge_rate_vs_beverloo_order_of_magnitude(mj_heap):
    r = mj_heap
    info = r["model_info"]
    dr = G.hopper_discharge_rate(r["mass_below"], r["times"], info["mass_total"])
    Deq = math.sqrt(4.0 / math.pi) * info["orifice_d"]
    Wb = G.beverloo_rate(Deq, 2 * r["radius"], info["bulk_density_bin"])
    assert 0.5 < dr["rate"] / Wb < 2.0                # 桁だけ(正方孔・D₀/d = 6.8・コマ数が少ない —— 一致が良すぎるので信用しない)
    img = G.spheres_render_shaded(r["pos"], r["radius"], 0.002, 0.16, 0.26)
    assert img.shape[2] == 3 and 0.0 <= img.min() and img.max() <= 1.0
