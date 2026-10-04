# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""pegfail の門(ペグ挿入の失敗検出と回復を、学習なしの「失敗分類表 × 接触計測」で: Whitney 1982 と MuJoCo を真値に)。

numpy だけの門(常に走る):
 1. 表: 12 行・8 クラス全部に行・同じ署名を 2 行が取らない・語彙 576 署名のうち 362 を決める、行の複製と綴り壊しは ValueError
 2. 表の全行の全署名 362 個を分類すると 100 % が行のクラス(n_match = 1)、表に無い署名は推測せず unknown
 3. 綴り壊し(two_pint / lift_recenter / wedgin / nan の力の比 / str でない名 / 列でない混同行列の入力)は全部 ValueError
 4. かじりの平行四辺形: 二点接触の平面静力学から導いた 4 頂点 = pegsim(OCW p.34)の頂点 1e-9、滑りの荷重は斜辺の上、f₁ = 0 は縦の辺
 5. jamming_force_check の辺・余裕・側(side)、くさびの境目 θ = c/μ ∓ 1e-9 で below / over
 6. 停滞の検出: 単調降下 3 速度 + 構える平面で誤報 0、真の停止から窓 + 1 刻以内で onset、0.5 mm 進んでから武装
 7. 手首ばね → 先端の荷重の閉形式(1e-12)、力の比の規約と F_z ≤ 0 で None
 8. 視覚の境目の反転確率 = Φ(−|z|)(0.03 以内)、合成 RGB-D(mujoco 不要)のずれ → offset の欄 → 分類 = 真値
 9. 離散化の境目(zone / jam / offset)、要約の遅れ、混同行列、回復プリミティブの表、既定の注入が Whitney の境目の正しい側
10. MJCF 文字列(力・トルクセンサ、栓、囮 109 個 + 枠 4 個)、栓が穴の外 / 囮が重なる → ValueError
mujoco が要る門(無ければ skip):
11. 注入格子 6 クラス × {回復なし, あり}: 真値署名でも視覚の署名でも 6 / 6、回復なし 0 / 5 → 回復あり 5 / 5、遅れは窓 30 + 確認 ≤ 10
12. 力の閉じ: 手首ばねのたわみからの荷重 + 重力 = −Σ接触力(停滞中 ≤ 0.5 N)、力センサとばねの推定の差 ≤ 0.1 N
13. 力を抜く探針: くさび(μ 0.8)は抜いても引いても動かない、詰まり(μ 0.3)は抜くと進み引くと戻る —— Whitney の区別を物理で
14. くさびは境目 c/μ の上だけ(μ 0.8・θ₀ 2.0° は入る、μ 0.3・θ₀ 4.5° は詰まりで wedging を出さない)
"""
from __future__ import annotations

import itertools
import math
import xml.etree.ElementTree as ET

import numpy as np
import pytest

import pegfail as F
import pegsim as P

KP = P.peg_params()
DEG = math.pi / 180.0


def _raises(fn, exc=ValueError):
    try:
        fn()
    except exc:
        return True
    return False


# ── 1〜3. 表 ───────────────────────────────────────────────────────────────────
def test_the_table_is_complete_exclusive_and_fail_closed():
    v = F.insertion_failure_validate()
    T = F.insertion_failure_table()
    assert v["n_rows"] == 12 and len(v["classes_covered"]) == 8 and not v["overlaps"] and not v["classes_missing"]
    assert v["n_signatures"] == 576 and v["n_covered"] == 362
    assert _raises(lambda: F.insertion_failure_validate(T + [dict(T[5], cls="jamming")]))      # 同じ署名を 2 行が取る
    assert _raises(lambda: F.insertion_failure_validate(T[:-1] + [dict(T[-1], cls="nomnial")]))
    assert _raises(lambda: F.insertion_failure_validate([r for r in T if r["cls"] != "seated"]))   # seated の行が無くなれば届かないクラス
    assert _raises(lambda: F.insertion_failure_validate([]))
    assert _raises(lambda: F.insertion_failure_validate([1, 2]))


def test_every_row_signature_classifies_to_its_row():
    T = F.insertion_failure_table()
    fields = list(F.SIGNATURE_FIELDS)
    n_sig, bad = 0, 0
    assert len(T) == 12
    for row in T:
        sets = [F._row_values(row["when"][f], f) for f in fields]
        combos = list(itertools.product(*sets))
        assert len(combos) >= 1
        for combo in combos:
            c = F.insertion_failure_classify(dict(zip(fields, combo)))
            n_sig += 1
            bad += int(c["cls"] != row["cls"] or c["n_match"] != 1 or c["recovery"] != row["recovery"])
    assert n_sig == 362 and bad == 0


def test_unknown_signatures_are_not_guessed():
    unk = [{"contact": "plate", "zone": "mouth", "progress": "stalled", "wedge": "below", "jam": "na", "offset": "small"},
           {"contact": "two_point", "zone": "hole", "progress": "stalled", "wedge": "below", "jam": "inside", "offset": "small"},
           {"contact": "none", "zone": "mouth", "progress": "stalled", "wedge": "below", "jam": "na", "offset": "small"}]
    assert len(unk) == 3
    for s in unk:
        c = F.insertion_failure_classify(s)
        assert c["cls"] == "unknown" and c["recovery"] is None and c["n_match"] == 0 and c["row"] == -1


def test_spelling_breaks_fail_closed():
    sig = {"contact": "two_pint", "zone": "mouth", "progress": "stalled", "wedge": "below", "jam": "na", "offset": "small"}
    assert _raises(lambda: F.insertion_failure_classify(sig))
    assert _raises(lambda: F.insertion_failure_classify({"contact": "none"}))
    assert _raises(lambda: F.insertion_failure_classify("none"))
    assert _raises(lambda: F.insertion_recovery_primitive("lift_recenter"))
    assert _raises(lambda: F.insertion_recovery_primitive(["lift_recentre"]))
    assert _raises(lambda: F.failure_confusion(["wedging"], ["wedgin"]))
    assert _raises(lambda: F.failure_confusion(1.0, 2.0))
    assert _raises(lambda: F.failure_confusion(["wedging"], ["wedging", "jamming"]))
    assert _raises(lambda: F.insertion_signature({"contact_kind": "two_pint", "depth": 0.0, "stalled": True}, KP))
    assert _raises(lambda: F.insertion_signature({"contact_kind": "none", "stalled": True}, KP))
    assert _raises(lambda: F.insertion_signature("none", KP))
    assert _raises(lambda: F.jamming_force_check(KP, 5e-3, float("nan"), 0.0))
    assert _raises(lambda: F.jamming_force_check(KP, 5e-3, 0.0, 0.0, side=2))
    assert _raises(lambda: F.jamming_parallelogram_planar(KP, -1e-3))
    assert _raises(lambda: F.jamming_parallelogram_planar(P.peg_params(mu=0.0), 5e-3))
    assert _raises(lambda: F.wedging_risk(KP, -0.1))
    assert _raises(lambda: F.insertion_stall_detect([]))
    assert _raises(lambda: F.insertion_stall_detect([0.0, 1e-3], window=0))
    assert _raises(lambda: F.vision_boundary_flip(KP, [1e-3], 0.0))
    assert _raises(lambda: F.insertion_episode_summary({"rec": 3}))
    assert _raises(lambda: F.wrist_load_from_deflection(KP, (0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 1)))
    assert _raises(lambda: F.wrist_load_from_deflection(KP, (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0)))
    assert _raises(lambda: F.tip_force_ratios(KP, [0, 0, -1], [0, 0, 0], [0, 0, 1]))


# ── 4〜5. Whitney の量 ─────────────────────────────────────────────────────────
def test_planar_statics_parallelogram_matches_pegsim_vertices():
    worst = 0.0
    cases = [(mu, ell) for mu in (0.3, 0.8) for ell in (2e-3, 5e-3, 12e-3)]
    assert len(cases) == 6
    for mu, ell in cases:
        k = P.peg_params(mu=mu)
        pg = F.jamming_parallelogram_planar(k, ell)
        worst = max(worst, float(np.abs(pg["vertices"] - P.jamming_diagram(k, ell)["vertices"]).max()))
        assert abs(pg["lambda"] - ell / (2 * k["r"] * mu)) < 1e-15
    assert worst < 1e-9


def test_sliding_load_lies_on_the_minus_line_and_f1_zero_is_the_vertical_edge():
    ell, mu, r = 5e-3, KP["mu"], KP["r"]
    f1, f2 = 2.0, 3.0                                              # 両点が下へ滑る釣り合いの荷重
    Fx, Fz, M = f2 - f1, mu * (f1 + f2), mu * r * f1 - (mu * r + ell) * f2
    jc = F.jamming_force_check(KP, ell, Fx / Fz, M / (r * Fz))
    assert abs(jc["margins"]["line_minus"]) < 1e-12
    assert jc["pegsim_inside"] == jc["inside"]
    f1 = 0.0
    Fx, Fz = f2 - f1, mu * (f1 + f2)
    assert abs(Fx / Fz - 1.0 / mu) < 1e-12


def test_jamming_force_check_edges_margins_and_sides():
    inside = F.jamming_force_check(KP, 5e-3, 0.0, 0.0)
    assert inside["inside"] and inside["margin"] > 0 and inside["active_line"] == "line_minus"
    far = F.jamming_force_check(KP, 5e-3, 0.0, 10.0)
    assert not far["inside"] and far["edge"] == "line_plus"
    assert F.jamming_force_check(KP, 5e-3, 0.0, 10.0, side=-1)["inside"]                # 鏡像の斜辺を外せば内側
    assert not F.jamming_force_check(KP, 5e-3, 0.0, -10.0, side=-1)["inside"]
    pg = F.jamming_parallelogram_planar(KP, 5e-3)
    x_out = 1.0 / KP["mu"] + 0.05                                                         # 縦の辺の 0.05 外、斜辺の真ん中の高さ
    assert F.jamming_force_check(KP, 5e-3, x_out, pg["slope"] * x_out, tol=0.1)["inside"]
    assert not F.jamming_force_check(KP, 5e-3, x_out, pg["slope"] * x_out)["inside"]
    assert F.jamming_force_check(KP, 5e-3, x_out, pg["slope"] * x_out)["edge"] == "fx_plus"
    assert set(F.jamming_force_check(KP, 5e-3, 0.0, 0.0, side=1)["margins"]) == {"fx_plus", "fx_minus", "line_plus"}


def test_wedging_boundary_flips_at_c_over_mu():
    lim3 = P.whitney_clearance(KP)["theta_wedge"]
    lim8 = P.whitney_clearance(P.peg_params(mu=0.8))["theta_wedge"]
    assert abs(math.degrees(lim3) - 7.353) < 0.01 and abs(math.degrees(lim8) - 2.755) < 0.01
    assert F.wedging_risk(KP, lim3 - 1e-9)["level"] != "over" and F.wedging_risk(KP, lim3 + 1e-9)["level"] == "over"
    assert F.wedging_risk(KP, lim3 - 0.3 * DEG)["level"] == "near" and F.wedging_risk(KP, 3 * DEG)["level"] == "safe"
    assert F.wedging_risk(P.peg_params(mu=0.8), 4.5 * DEG)["level"] == "over"
    assert F.wedging_risk(P.peg_params(mu=0.0), 10 * DEG)["level"] == "safe"           # μ = 0 なら境目は inf


# ── 6. 停滞 ────────────────────────────────────────────────────────────────────
def test_stall_detector_has_no_false_alarms_on_monotone_descent():
    rng = np.random.default_rng(1)
    speeds = (12.0, 3.0, 1.7)
    assert len(speeds) == 3
    for v_mm_s in speeds:
        z = np.arange(400) * v_mm_s * 1e-3 * 0.01 + rng.normal(0, 5e-6, 400)
        assert F.insertion_stall_detect(z)["n_stalled"] == 0
    hover = np.concatenate([np.zeros(80), np.arange(300) * 3e-5]) + rng.normal(0, 5e-6, 380)
    assert F.insertion_stall_detect(hover)["n_stalled"] == 0                             # 構える平面では鳴らない(武装前)


def test_stall_detector_onset_after_the_true_stop_and_arming():
    rng = np.random.default_rng(2)
    desc = np.concatenate([np.arange(200) * 3e-5, np.full(150, 199 * 3e-5)]) + rng.normal(0, 5e-6, 350)
    sd = F.insertion_stall_detect(desc)
    lat = sd["onset"] - 200
    assert 0 <= lat <= sd["window"] + 1 and sd["armed_at"] == 17 and sd["stalled"].shape == (350,)
    assert F.insertion_stall_detect(np.zeros(100))["armed_at"] == -1                     # 一度も進まなければ武装せず


# ── 7. 手首の荷重 ──────────────────────────────────────────────────────────────
def test_wrist_load_closed_form_and_tip_force_ratio_convention():
    L = KP["peg_length"]
    a = np.array([0.0, 0.0, 1.0])
    w1 = F.wrist_load_from_deflection(KP, (0, 0, 2e-3), (0, 0, 0), (0, 0, 0), (0, 0, 0), a)
    assert np.allclose(w1["F"], [0, 0, -KP["k_trans"] * 2e-3 - 0.04 * 9.81], atol=1e-12)
    w2 = F.wrist_load_from_deflection(KP, (1e-3, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), a, lg=L, peg_mass=0.0)
    assert np.allclose(w2["M_tip"], [0, -L * KP["k_trans"] * 1e-3, 0], atol=1e-12)
    w3 = F.wrist_load_from_deflection(KP, (0, 0, 0), (0, 0.01, 0), (0, 0, 0), (0, 0, 0), a, peg_mass=0.0)
    assert np.allclose(w3["M_tip"], [0, -KP["k_rot"] * 0.01, 0], atol=1e-12)
    rr = F.tip_force_ratios(KP, [1.5, 0.0, -3.0], [0.0, -0.006, 0.0], [1.0, 0.0, 0.0])
    assert abs(rr["fx_over_fz"] - 0.5) < 1e-12 and abs(rr["m_over_rfz"] - 0.006 / (KP["r"] * 3.0)) < 1e-12
    assert F.tip_force_ratios(KP, [0.0, 0.0, 0.5], [0, 0, 0], [1, 0, 0])["fx_over_fz"] is None


# ── 8. 視覚 ────────────────────────────────────────────────────────────────────
def test_vision_boundary_flip_matches_the_gaussian_theory():
    sig = 0.05e-3
    emax = P.chamfer_capture(KP, 0.0)["eps_max"]
    vb = F.vision_boundary_flip(KP, [emax - 4 * sig, emax - sig, emax, emax + sig, emax + 4 * sig], sig, n=4000)
    fr = vb["flip_rate"]
    assert abs(vb["eps_max"] - 1.2e-3) < 1e-12
    assert abs(fr[2] - 0.5) < 0.03 and abs(fr[1] - 0.1587) < 0.03 and abs(fr[3] - 0.1587) < 0.03
    assert fr[0] < 0.005 and fr[4] < 0.005
    assert np.allclose(vb["flip_theory"][[1, 3]], 0.5 * math.erfc(1 / math.sqrt(2)), atol=1e-12)


def test_synthetic_rgbd_offset_feeds_the_offset_field_and_the_class():
    cases = ((0.5, "chamfer", 0.5e-3, "chamfer_sliding"), (1.0, "chamfer", 0.5e-3, "chamfer_sliding"),
             (1.4, "plate", 0.0, "missed_hole"), (2.5, "plate", 0.0, "missed_hole"))
    assert len(cases) == 4
    for eps_mm, ck, zone_depth, expect in cases:
        tip = np.array([eps_mm * 1e-3 * math.cos(0.6), eps_mm * 1e-3 * math.sin(0.6), 0.008])
        syn = P.peg_synthetic_rgbd(KP, tip, (0.0, 0.0, 1.0), supersample=2)
        res = P.peg_offset_from_rgbd(syn["rgb"], syn["depth"], syn["K"], syn["R_cam_to_world"], r_peg=KP["r"], hole_radius=KP["R"] + KP["chamfer"])
        est = math.hypot(res["dx"], res["dy"])
        assert abs(est - eps_mm * 1e-3) < 0.05e-3
        sig = F.insertion_signature({"contact_kind": ck, "depth": zone_depth, "stalled": True, "offset": est}, KP)
        assert F.insertion_failure_classify(sig)["cls"] == expect


# ── 9. 離散化・要約・既定 ───────────────────────────────────────────────────────
def test_signature_discretisation_boundaries():
    W, Hd = KP["chamfer"], KP["hole_depth"]
    emax = P.chamfer_capture(KP, 0.0)["eps_max"]
    base = {"contact_kind": "none", "stalled": False}
    zones = [F.insertion_signature(dict(base, depth=dz), KP)["zone"] for dz in (-1e-6, 0.0, W - 1e-9, W, Hd - 1e-3 - 1e-9, Hd - 1e-3)]
    assert zones == ["above", "mouth", "mouth", "hole", "hole", "bottom"]
    o1 = {"contact_kind": "two_point", "depth": 6e-3, "stalled": True, "fx_over_fz": 0.0, "m_over_rfz": 0.0}
    assert F.insertion_signature(o1, KP)["jam"] == "inside"
    assert F.insertion_signature(dict(o1, m_over_rfz=10.0), KP)["jam"] == "outside"
    o3 = {"contact_kind": "one_point", "depth": 6e-3, "stalled": True, "fx_over_fz": 1 / KP["mu"] + 1e-6}
    assert F.insertion_signature(o3, KP)["jam"] == "outside"
    assert F.insertion_signature(dict(o3, fx_over_fz=None), KP)["jam"] == "na"
    off = [F.insertion_signature(dict(base, depth=0.0, offset=e), KP)["offset"] for e in (emax - 1e-9, emax + 1e-9)]
    assert off == ["small", "large"]
    lim = P.whitney_clearance(KP)["theta_wedge"]
    assert F.insertion_signature(dict(base, depth=0.0, theta_onset=lim + 1e-9), KP)["wedge"] == "over"
    assert F.insertion_signature(dict(base, depth=0.0, tilt=lim - 1e-9), KP)["wedge"] == "below"


def test_episode_summary_latency_and_the_confusion_matrix():
    n = 80
    cls = ["nominal"] * 40 + ["wedging"] * 40
    det = [False] * 40 + [True] * 40
    ep = {"injected": "wedging", "rec": {"depth": np.linspace(0, 6e-3, n), "cls_truth": cls, "detected": det, "force": [1.0] * n},
          "failing_onset_tick": 10, "recoveries": [{"cls": "wedging"}], "success": True, "status": "success"}
    sm = F.insertion_episode_summary(ep)
    assert sm["latency_ticks"] == 30 and sm["first_cls"] == "wedging" and sm["recoveries"] == 1 and abs(sm["final_depth_mm"] - 6.0) < 1e-9
    none = F.insertion_episode_summary({"injected": "nominal", "rec": {"depth": [0.0], "cls_truth": ["nominal"], "force": [0.0]}})
    assert none["first_cls"] == "none" and math.isnan(none["latency_ticks"])
    cf = F.failure_confusion(["wedging", "jamming", "jamming", "missed_hole"], ["wedging", "jamming", "unknown", "missed_hole"])
    assert abs(cf["accuracy"] - 0.75) < 1e-12 and cf["matrix"].sum() == 4
    assert abs(cf["per_class_recall"][cf["classes"].index("jamming")] - 0.5) < 1e-12
    assert abs(cf["per_class_recall"][cf["classes"].index("wedging")] - 1.0) < 1e-12


def test_recovery_primitives_and_presets_sit_on_the_right_side_of_whitney():
    T = F.insertion_failure_table()
    names = sorted({r["recovery"] for r in T})
    assert len(names) == 7
    for nm in names:
        pr = F.insertion_recovery_primitive(nm)
        assert pr["name"] == nm and isinstance(pr["resume"], bool)
    assert F.insertion_recovery_primitive("lift_abort")["terminal"] == "aborted"
    pre = F.insertion_failure_presets(KP)
    emax = P.chamfer_capture(KP, 0.0)["eps_max"]
    assert set(pre) == {"nominal", "missed_hole", "wedging", "jamming", "blocked_hole", "wrong_hole"}
    assert math.hypot(*pre["missed_hole"]["eps_mm"]) * 1e-3 > emax                       # 面取りに乗れないずれ
    assert math.hypot(*pre["nominal"]["eps_mm"]) * 1e-3 < emax
    assert pre["wedging"]["tilt_deg"] * DEG > P.whitney_clearance(P.peg_params(mu=pre["wedging"]["mu"]))["theta_wedge"]
    assert pre["jamming"]["tilt_deg"] * DEG < P.whitney_clearance(KP)["theta_wedge"]      # 詰まりはくさびでない傾き
    assert KP["chamfer"] < pre["blocked_hole"]["blocked_depth"] < KP["hole_depth"]
    assert math.hypot(*pre["wrong_hole"]["decoy_xy"]) >= 2 * (KP["R"] + KP["chamfer"]) + 1e-3


# ── 10. MJCF ───────────────────────────────────────────────────────────────────
def test_scene_mjcf_parts_and_fail_closed():
    Hd = KP["hole_depth"]
    x0 = ET.fromstring(F.pegfail_scene_mjcf(KP))
    xb = ET.fromstring(F.pegfail_scene_mjcf(KP, blocked_depth=6e-3))
    xd = ET.fromstring(F.pegfail_scene_mjcf(KP, decoy_xy=(26e-3, 0.0)))
    assert len(list(x0.iter("force"))) == 1 and len(list(x0.iter("torque"))) == 1
    plug = next(g for g in xb.iter("geom") if g.get("name") == "plug")
    half = (Hd - 6e-3) / 2
    assert abs(float(plug.get("pos").split()[2]) + 6e-3 + half) < 1e-9
    n_decoy = sum(1 for g in xd.iter("geom") if (g.get("name") or "").startswith("decoy_"))
    plate = next(b for b in xd.iter("body") if b.get("name") == "plate")
    n_frame = sum(1 for g in plate if g.tag == "geom" and g.get("name") is None)
    assert n_decoy == 3 * KP["n_seg"] + 1 and n_frame == 4
    assert _raises(lambda: F.pegfail_scene_mjcf(KP, blocked_depth=0.5e-3))
    assert _raises(lambda: F.pegfail_scene_mjcf(KP, blocked_depth=Hd))
    assert _raises(lambda: F.pegfail_scene_mjcf(KP, decoy_xy=(5e-3, 0.0)))


# ── 11〜14. mujoco ─────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def grid():
    pytest.importorskip("mujoco")
    return F.pegfail_failure_grid(KP, keep_episodes=True)


def test_mujoco_grid_classifies_and_recovers(grid):
    ct, cv, sr = grid["confusion_truth"], grid["confusion_vision"], grid["success"]
    assert ct["n"] == 6 and ct["accuracy"] == 1.0 and cv["accuracy"] == 1.0
    assert sr[False] == (0, 5) and sr[True][0] >= 4 and sr[True][1] == 5
    lat = {row["injected"]: row["latency_ticks"] for row in grid["rows"] if not row["recover"]}
    stall_lat = [lat[c] for c in ("missed_hole", "wedging", "jamming")]
    assert len(stall_lat) == 3
    assert all(30 <= x <= 40 for x in stall_lat)                                          # 窓 30 + 確認 ≤ 10
    assert lat["blocked_hole"] <= 15 and lat["wrong_hole"] <= 25
    assert len(grid["rows"]) == 12
    assert all(isinstance(r["success"], bool) for r in grid["rows"])


def test_mujoco_force_closure_from_wrist_stiffness(grid):
    worst_eq, worst_sens, n_pts = 0.0, 0.0, 0
    assert len(grid["episodes"]) == 12
    for ep in grid["episodes"]:
        r = ep["rec"]
        rows = list(zip(r["F_est"], r["f_contact"], r["sensor_force"], r["force"], r["stalled"]))
        assert len(rows) >= 1
        for Fe, Fc, Fs, frc, st in rows:
            if frc > 0.5 and st:                                                           # 準静的(停滞中)の刻だけ
                worst_eq = max(worst_eq, float(np.linalg.norm(np.asarray(Fe) + np.asarray(Fc))))
                worst_sens = max(worst_sens, float(np.linalg.norm(np.asarray(Fs) - (np.asarray(Fe) - [0, 0, -0.04 * 9.81]))))
                n_pts += 1
    assert n_pts > 1000
    assert worst_eq < 0.5 and worst_sens < 0.1                                             # 実測 0.35 / 0.026 N


def test_mujoco_release_probe_distinguishes_wedge_from_jam():
    pytest.importorskip("mujoco")
    pre = F.insertion_failure_presets(KP)
    rw = F.pegfail_episode_run(KP, injected="wedging", recover=False, release_probe=True, **pre["wedging"])["release"]
    rj = F.pegfail_episode_run(KP, injected="jamming", recover=False, release_probe=True, **pre["jamming"])["release"]
    assert rw["cls"] == "wedging" and rw["stuck"] and rw["F_z_pulled_N"] < 0 and abs(rw["depth_before_mm"] - rw["depth_pulled_mm"]) < 0.5
    assert rj["cls"] == "jamming" and not rj["stuck"] and rj["depth_before_mm"] - rj["depth_pulled_mm"] > 0.5
    assert rj["depth_unloaded_mm"] > rj["depth_before_mm"]                                 # 横の力を抜くと自重で進む


def test_mujoco_wedging_only_above_the_boundary():
    pytest.importorskip("mujoco")
    e_lo = F.pegfail_episode_run(KP, injected="wedging_below", recover=False, eps_mm=(0.3, 0.0), tilt_deg=2.0, mu=0.8)
    e_mu3 = F.pegfail_episode_run(KP, injected="wedging_mu03", recover=False, eps_mm=(0.3, 0.0), tilt_deg=4.5)
    assert e_lo["success"] and "wedging" not in set(e_lo["rec"]["cls_truth"])
    assert "wedging" not in set(e_mu3["rec"]["cls_truth"]) and e_mu3["status"] == "failed:jamming"
