# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""ペグ挿入の失敗を規則の表で見つけて回復する —— VLM の代わりに Whitney の接触状態、真値は MuJoCo(2026-10-04)。

物理シミュ × Fullseye 系列、pegsim(柔らかい手首のペグ挿入、2026.195)の集大成。先行研究(Shirasaka, Beltran-Hernandez, Hamaya, Ushiku,
arXiv:2509.17666、ICRA 2026 予定、コード未公開)は挿入の失敗を **VLM** が判定して回復スキルを選ぶ。ここでは VLM を **規則の表**(12 行・
8 クラス)に置き換える: 観測(接触の種別・深さの帯・停滞・くさびの境目・かじりの図の内外・穴中心からのずれ)を離散の署名にし、
表の 1 行だけが当たれば失敗クラスと回復プリミティブが決まる。当たらなければ ``unknown`` で止まる(fail-closed、推測しない)。
外から来るものは 2 つ:
  * **定理**: Whitney 1982(原著は有料で未読、式は著者本人の MIT OCW 2.875 Class 3 スライド本文)—— くさび θ > c/μ(p.28)、かじりの
    平行四辺形 λ = l/(2rμ)(p.34)。平行四辺形の頂点は **二点接触の平面静力学**から導き直して pegsim(OCW の値)と 1e-9 で一致させ、
    力の比の符号の規約をその導出で固定する。
  * **物理エンジン(--full)**: MuJoCo の接触点・法線力・手首の力センサが真値。失敗を**わざと注入**し(面取りに乗れないずれ、
    μ 0.8 で θ₀ > c/μ、傾きの側へ横目標をずらす、穴の栓、囮の穴)、停滞 → 署名 → 表 → 回復 の鎖を回す。

門(12 + --full 8): 表の完全性と排他(語彙 576 署名のうち 362 を決める)、平行四辺形の頂点(1e-9)、くさびの境目(∓1e-9 rad)、
停滞の検出(誤報 0・遅れ ≤ 窓 + 1)、全行の全署名 362 個の分類、unknown と綴り壊し、手首ばね → 荷重の閉形式、視覚の境目の反転 = Φ(−|z|)、
合成 RGB-D(mujoco 不要)のずれ → 欄 → 分類、離散化の境目、要約と混同行列、MJCF 文字列; --full: 力の閉じ(ばねの推定 + 重力 = −Σ接触力)、
注入格子 6 クラス × {回復なし, あり}(真値署名でも視覚の署名でも 6 / 6、回復 0/5 → 5/5)、検出の遅れ、**力を抜く探針でくさびと詰まりを
物理的に区別**、かじりの図の余裕(停滞は外・滑りは内)、くさびは境目の上だけ、視覚の錨(囮があると当てはめが乱れる)、記録つき走行。
図(FULLSEYE_FIGURE_DIR があるとき、--full で 6 枚): 境目の反転確率、混同行列(表)、かじりの図に実測の軌跡と 2 つの深さの平行四辺形、
深さ vs 刻(停滞 → 検出 → 回復)、手首カメラの GIF(detected: wedging が出て退避 → 再降下 → 成功)、力を抜く探針の表。
正直に: VLM との比較は作らない(無いものを並べない)。5/5 は各クラス 1 条件ずつで論文の実機の成功率とは並べない。視覚の署名は構えた時の
RGB-D の錨 + エンコーダ積分(穴に入った先端は写らない)。かじりの判定は停滞中・F_z ≥ 1 N でだけ。回復プリミティブは脚本。
Run: py -3.11 examples/poc_peg_failure_recovery.py [--full]        (--full は mujoco)
"""
from __future__ import annotations

import itertools
import math
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import annotate as AN  # noqa: E402
import examplefig as figs  # noqa: E402
import pegfail as F  # noqa: E402
import pegsim as P  # noqa: E402

KP = P.peg_params()
DEG = math.pi / 180.0
FULL = "--full" in sys.argv
_GATES: list[tuple[str, bool]] = []
_NUM: dict = {}


def gate(name, ok, detail=""):
    _GATES.append((name, bool(ok)))
    print("  [%s] %s %s" % ("ok" if ok else "NG", name, detail))


def skip(name, why):
    print("  [skip] %s —— %s" % (name, why))


def _raises(fn, exc=ValueError):
    try:
        fn()
    except exc:
        return True
    return False


# ======================================================================================================================
def numpy_part() -> dict:
    print("== 1. numpy の門(表・Whitney・停滞・手首荷重・視覚の境目・合成 RGB-D・MJCF)")
    t0 = time.time()
    out = {}
    # ── 1. 表の完全性と排他
    v = F.insertion_failure_validate()
    T = F.insertion_failure_table()
    dup = T + [dict(T[5], cls="jamming")]
    bad_cls = T[:-1] + [dict(T[-1], cls="nomnial")]
    gate("門 1 表: %d 行、unknown 以外の %d クラス全部に行があり、同じ署名を 2 行が取る組 = 0、語彙 %d 署名のうち %d (%.0f %%) を表が決め"
         "残りは unknown。行を複製 / クラスの綴りを壊すと ValueError"
         % (v["n_rows"], len(v["classes_covered"]), v["n_signatures"], v["n_covered"], 100 * v["coverage"]),
         v["n_rows"] == 12 and len(v["classes_covered"]) == 8 and not v["overlaps"] and not v["classes_missing"]
         and _raises(lambda: F.insertion_failure_validate(dup)) and _raises(lambda: F.insertion_failure_validate(bad_cls)))
    _NUM["table"] = {k: v[k] for k in ("n_rows", "n_covered", "n_signatures", "coverage")}
    # ── 2. 平行四辺形: 平面静力学 vs pegsim(OCW の頂点)
    worst = 0.0
    for mu in (0.3, 0.8):
        k = P.peg_params(mu=mu)
        for ell in (2e-3, 5e-3, 12e-3):
            worst = max(worst, float(np.abs(F.jamming_parallelogram_planar(k, ell)["vertices"] - P.jamming_diagram(k, ell)["vertices"]).max()))
    ell, mu, r = 5e-3, KP["mu"], KP["r"]
    f1, f2 = 2.0, 3.0
    Fx, Fz, M = f2 - f1, mu * (f1 + f2), mu * r * f1 - (mu * r + ell) * f2
    on_line = abs(F.jamming_force_check(KP, ell, Fx / Fz, M / (r * Fz))["margins"]["line_minus"]) < 1e-12
    vert = abs((f2 - 0.0) / (mu * (0.0 + f2)) - 1.0 / mu) < 1e-12
    gate("門 2 かじりの平行四辺形: 二点接触の平面静力学(F_x = f₂ − f₁、F_z = μ(f₁ + f₂)、M = μrf₁ − (μr + l)f₂)から導いた 4 頂点が OCW p.34 の頂点"
         "(pegsim)と 1e-9 で一致(μ 0.3 / 0.8 × l 2 / 5 / 12 mm)、構成した滑りの荷重は切片 −λ の斜辺の上(1e-12)、f₁ = 0 で縦の辺 F_x/F_z = 1/μ",
         worst < 1e-9 and on_line and vert, "max |Δ頂点| = %.1e" % worst)
    _NUM["vertices_max_diff"] = worst
    # ── 3. くさびの境目
    lim3, lim8 = P.whitney_clearance(KP)["theta_wedge"], P.whitney_clearance(P.peg_params(mu=0.8))["theta_wedge"]
    ok = (F.wedging_risk(KP, lim3 - 1e-9)["level"] != "over" and F.wedging_risk(KP, lim3 + 1e-9)["level"] == "over"
          and F.wedging_risk(KP, lim3 - 0.3 * DEG)["level"] == "near" and F.wedging_risk(KP, 3 * DEG)["level"] == "safe"
          and abs(math.degrees(lim3) - 7.353) < 0.01 and abs(math.degrees(lim8) - 2.755) < 0.01
          and F.wedging_risk(P.peg_params(mu=0.8), 4.5 * DEG)["level"] == "over")
    gate("門 3 くさびの境目 θ = c/μ(OCW p.28): c/μ ∓ 1e-9 rad で below / over が切り替わる、μ = 0.3 → %.3f°、μ = 0.8 → %.3f°(θ₀ = 4.5° は over、"
         "3° は safe、境目 − 0.3° は near)" % (math.degrees(lim3), math.degrees(lim8)), ok)
    _NUM["theta_wedge_deg"] = {"mu0.3": math.degrees(lim3), "mu0.8": math.degrees(lim8)}
    # ── 4. 停滞の検出
    rng = np.random.default_rng(1)
    alarms = 0
    for v_mm_s in (12.0, 3.0, 1.7):
        alarms += F.insertion_stall_detect(np.arange(400) * v_mm_s * 1e-3 * 0.01 + rng.normal(0, 5e-6, 400))["n_stalled"]
    alarms += F.insertion_stall_detect(np.concatenate([np.zeros(80), np.arange(300) * 3e-5]) + rng.normal(0, 5e-6, 380))["n_stalled"]
    sd = F.insertion_stall_detect(np.concatenate([np.arange(200) * 3e-5, np.full(150, 199 * 3e-5)]) + rng.normal(0, 5e-6, 350))
    lat = sd["onset"] - 200
    gate("門 4 停滞の検出(窓 30 刻、進み < 0.05 mm): 単調降下 3 速度 + 構える平面 → 誤報 0、降下 → 停止では真の停止から %d 刻以内(窓 + 1)で onset、"
         "武装は 0.5 mm 進んでから(刻 %d)" % (sd["window"] + 1, sd["armed_at"]),
         alarms == 0 and 0 <= lat <= sd["window"] + 1 and sd["armed_at"] == 17, "onset − 真 = %d 刻、誤報 %d" % (lat, alarms))
    _NUM["stall"] = {"false_alarms": int(alarms), "onset_lag_ticks": int(lat)}
    # ── 5. 真値署名の分類(全列挙)
    n_sig, bad = 0, 0
    fields = list(F.SIGNATURE_FIELDS)
    for row in T:
        for combo in itertools.product(*[F._row_values(row["when"][f], f) for f in fields]):
            c = F.insertion_failure_classify(dict(zip(fields, combo)))
            n_sig += 1
            bad += int(c["cls"] != row["cls"] or c["n_match"] != 1 or c["recovery"] != row["recovery"])
    gate("門 5 真値の署名から注入クラスへ: 表の全行の全署名 %d 個を分類すると 100 %% が行のクラス(n_match = 1、回復名も一致)" % n_sig,
         bad == 0 and n_sig == v["n_covered"], "外れ %d" % bad)
    # ── 6. fail-closed
    unk = [{"contact": "plate", "zone": "mouth", "progress": "stalled", "wedge": "below", "jam": "na", "offset": "small"},
           {"contact": "two_point", "zone": "hole", "progress": "stalled", "wedge": "below", "jam": "inside", "offset": "small"},
           {"contact": "none", "zone": "mouth", "progress": "stalled", "wedge": "below", "jam": "na", "offset": "small"}]
    ok = (all(F.insertion_failure_classify(s)["cls"] == "unknown" for s in unk)
          and _raises(lambda: F.insertion_failure_classify(dict(unk[0], contact="two_pint")))
          and _raises(lambda: F.insertion_recovery_primitive("lift_recenter"))
          and _raises(lambda: F.failure_confusion(["wedging"], ["wedgin"]))
          and _raises(lambda: F.insertion_signature({"contact_kind": "two_pint", "depth": 0.0, "stalled": True}, KP))
          and _raises(lambda: F.jamming_force_check(KP, 5e-3, float("nan"), 0.0)))
    gate("門 6 fail-closed: 表に無い 3 署名(板の上で止まって小ずれ / 二点・停滞・内側 / 無接触で停滞)は推測せず unknown、綴り壊し"
         "(two_pint、lift_recenter、wedgin、nan の力の比)は全部 ValueError", ok)
    # ── 7. 手首荷重の閉形式
    L = KP["peg_length"]
    a = np.array([0.0, 0.0, 1.0])
    w1 = F.wrist_load_from_deflection(KP, (0, 0, 2e-3), (0, 0, 0), (0, 0, 0), (0, 0, 0), a)
    w2 = F.wrist_load_from_deflection(KP, (1e-3, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), a, lg=L, peg_mass=0.0)
    rr = F.tip_force_ratios(KP, [1.5, 0.0, -3.0], [0.0, -0.006, 0.0], [1.0, 0.0, 0.0])
    ok = (np.allclose(w1["F"], [0, 0, -KP["k_trans"] * 2e-3 - 0.04 * 9.81], atol=1e-12)
          and np.allclose(w2["M_tip"], [0, -L * KP["k_trans"] * 1e-3, 0], atol=1e-12)
          and abs(rr["fx_over_fz"] - 0.5) < 1e-12 and abs(rr["m_over_rfz"] - 0.006 / (KP["r"] * 3.0)) < 1e-12
          and F.tip_force_ratios(KP, [0.0, 0.0, 0.5], [0, 0, 0], [1, 0, 0])["fx_over_fz"] is None)
    gate("門 7 手首ばね → 先端の荷重(閉形式): z 圧縮 2 mm → F = (0, 0, −k_t·2 mm − mg)、横たわみ 1 mm・L_g = L → M_tip = −L k_t q_x ŷ(1e-12)、"
         "比の規約 x = F·e_x/F_z、y = M·(e_x × ẑ)/(rF_z)、引いているとき(F_z ≤ 0)は None", ok)
    # ── 8. 視覚の境目
    sig_v = 0.05e-3
    emax = P.chamfer_capture(KP, 0.0)["eps_max"]
    vb = F.vision_boundary_flip(KP, [emax - 4 * sig_v, emax - sig_v, emax, emax + sig_v, emax + 4 * sig_v], sig_v, n=4000)
    fr = vb["flip_rate"]
    gate("門 8 どこで壊れるか(視覚のずれに σ = 0.05 mm の雑音): 境目 W + c_r = %.1f mm ちょうどで offset の欄が 50 %% 反転(%.3f)、±1σ で Φ(−1) = 0.159 "
         "と 0.03 以内(%.3f / %.3f)、±4σ で < 0.5 %%" % (emax * 1e3, fr[2], fr[1], fr[3]),
         abs(fr[2] - 0.5) < 0.03 and abs(fr[1] - 0.1587) < 0.03 and abs(fr[3] - 0.1587) < 0.03 and fr[0] < 0.005 and fr[4] < 0.005)
    _NUM["flip"] = {"at_boundary": float(fr[2]), "minus_1sigma": float(fr[1]), "plus_1sigma": float(fr[3])}
    # ── 9. 合成 RGB-D → 視覚のずれ → offset の欄 → 分類
    t1 = time.time()
    errs, agree, cls_ok = [], True, True
    for eps_mm, ck, zone_depth, expect in ((0.5, "chamfer", 0.5e-3, "chamfer_sliding"), (1.0, "chamfer", 0.5e-3, "chamfer_sliding"),
                                           (1.4, "plate", 0.0, "missed_hole"), (2.5, "plate", 0.0, "missed_hole")):
        tip = np.array([eps_mm * 1e-3 * math.cos(0.6), eps_mm * 1e-3 * math.sin(0.6), 0.008])
        syn = P.peg_synthetic_rgbd(KP, tip, (0.0, 0.0, 1.0), supersample=2)
        res = P.peg_offset_from_rgbd(syn["rgb"], syn["depth"], syn["K"], syn["R_cam_to_world"], r_peg=KP["r"], hole_radius=KP["R"] + KP["chamfer"])
        est = math.hypot(res["dx"], res["dy"])
        errs.append(abs(est - eps_mm * 1e-3) * 1e3)
        agree &= P.chamfer_capture(KP, est)["captured"] == P.chamfer_capture(KP, eps_mm * 1e-3)["captured"]
        cls_ok &= F.insertion_failure_classify(F.insertion_signature({"contact_kind": ck, "depth": zone_depth, "stalled": True, "offset": est}, KP))["cls"] == expect
    gate("門 9 合成 RGB-D(解析的レイキャスト、mujoco 不要)4 姿勢 ε = 0.5 / 1.0 / 1.4 / 2.5 mm: 手首カメラのずれの誤差 max %.3f mm(境目 1.2 mm から "
         "≥ 0.2 mm 離れていれば欄は反転しない)、視覚のずれで作った署名の分類 = 真値(chamfer_sliding ×2、missed_hole ×2)、%.1f s"
         % (max(errs), time.time() - t1), max(errs) < 0.05 and agree and cls_ok)
    _NUM["synthetic_vision_err_mm"] = max(errs)
    # ── 10. 離散化の境目
    W, Hd = KP["chamfer"], KP["hole_depth"]
    base = {"contact_kind": "none", "stalled": False}
    zones = [F.insertion_signature(dict(base, depth=dz), KP)["zone"] for dz in (-1e-6, 0.0, W - 1e-9, W, Hd - 1e-3 - 1e-9, Hd - 1e-3)]
    o1 = {"contact_kind": "two_point", "depth": 6e-3, "stalled": True, "fx_over_fz": 0.0, "m_over_rfz": 0.0}
    o3 = {"contact_kind": "one_point", "depth": 6e-3, "stalled": True, "fx_over_fz": 1 / KP["mu"] + 1e-6}
    off = [F.insertion_signature(dict(base, depth=0.0, offset=e), KP)["offset"] for e in (emax - 1e-9, emax + 1e-9)]
    gate("門 10 離散化の境目: zone は depth −1e-6 → above、0 → mouth、W⁻ → mouth、W → hole、(H − 1 mm)⁻ → hole、H − 1 mm → bottom; jam は原点 → inside、"
         "M/(rF_z) = 10 → outside、一点で F_x/F_z = 1/μ + 1e-6 → outside; offset は W + c_r ∓ 1e-9 で small / large",
         zones == ["above", "mouth", "mouth", "hole", "hole", "bottom"] and F.insertion_signature(o1, KP)["jam"] == "inside"
         and F.insertion_signature(dict(o1, m_over_rfz=10.0), KP)["jam"] == "outside" and F.insertion_signature(o3, KP)["jam"] == "outside"
         and off == ["small", "large"])
    # ── 11. 要約と混同行列(合成の走行)
    n = 80
    ep = {"injected": "wedging", "rec": {"depth": np.linspace(0, 6e-3, n), "cls_truth": ["nominal"] * 40 + ["wedging"] * 40,
                                        "detected": [False] * 40 + [True] * 40, "force": [1.0] * n},
          "failing_onset_tick": 10, "recoveries": [{"cls": "wedging"}], "success": True, "status": "success"}
    sm = F.insertion_episode_summary(ep)
    cf = F.failure_confusion(["wedging", "jamming", "jamming", "missed_hole"], ["wedging", "jamming", "unknown", "missed_hole"])
    gate("門 11 要約: 検出の刻 40 − 真の始まり 10 = 遅れ 30 刻、first_cls = wedging; 混同行列 4 件(jamming の 1 件が unknown)→ 正答率 0.75、"
         "jamming の再現率 0.5、wedging 1.0",
         sm["latency_ticks"] == 30 and sm["first_cls"] == "wedging" and abs(cf["accuracy"] - 0.75) < 1e-12
         and abs(cf["per_class_recall"][cf["classes"].index("jamming")] - 0.5) < 1e-12 and cf["matrix"].sum() == 4)
    # ── 12. MJCF(mujoco 不要)
    x0 = ET.fromstring(F.pegfail_scene_mjcf(KP))
    xb = ET.fromstring(F.pegfail_scene_mjcf(KP, blocked_depth=6e-3))
    xd = ET.fromstring(F.pegfail_scene_mjcf(KP, decoy_xy=(26e-3, 0.0)))
    plug = next(g for g in xb.iter("geom") if g.get("name") == "plug")
    half = (Hd - 6e-3) / 2
    n_decoy = sum(1 for g in xd.iter("geom") if (g.get("name") or "").startswith("decoy_"))
    n_frame = sum(1 for g in next(b for b in xd.iter("body") if b.get("name") == "plate") if g.tag == "geom" and g.get("name") is None)
    gate("門 12 MJCF(文字列、mujoco 不要): 力・トルクセンサ 2 個、栓は深さ 6 mm を上面にする円柱(中心 z = −%.1f mm)、囮は壁・面取り・襟 3 × %d + 床 = "
         "%d 個の複製と 2 穴を囲む枠 4 個、栓が穴の外 / 囮が目標穴と重なる → ValueError" % ((6e-3 + half) * 1e3, KP["n_seg"], 3 * KP["n_seg"] + 1),
         len(list(x0.iter("force"))) == 1 and len(list(x0.iter("torque"))) == 1 and abs(float(plug.get("pos").split()[2]) + 6e-3 + half) < 1e-9
         and n_decoy == 3 * KP["n_seg"] + 1 and n_frame == 4 and _raises(lambda: F.pegfail_scene_mjcf(KP, blocked_depth=0.5e-3))
         and _raises(lambda: F.pegfail_scene_mjcf(KP, decoy_xy=(5e-3, 0.0))))
    out["flip"] = vb
    print("  numpy の門: %.2f s" % (time.time() - t0))
    return out


# ======================================================================================================================
def full_part(out: dict) -> dict:
    print("== 2. --full: MuJoCo の門(力の閉じ・注入格子・遅れ・くさびと詰まりの区別・境目・視覚の錨・記録つき走行)")
    try:
        import mujoco  # noqa: F401
    except ImportError:
        skip("門 13〜20", "mujoco が無い")
        return out
    t0 = time.time()
    g = F.pegfail_failure_grid(KP, log=lambda s: print("     " + s), keep_episodes=True)
    out["grid"] = g
    # ── 13. 力の閉じ
    worst_eq, worst_sens, n_pts, worst_dyn = 0.0, 0.0, 0, 0.0
    for ep in g["episodes"]:
        r = ep["rec"]
        for Fe, Fc, Fs, frc, st in zip(r["F_est"], r["f_contact"], r["sensor_force"], r["force"], r["stalled"]):
            if frc > 0.5:
                e = float(np.linalg.norm(np.asarray(Fe) + np.asarray(Fc)))
                worst_dyn = max(worst_dyn, e)
                if st:
                    worst_eq = max(worst_eq, e)
                    worst_sens = max(worst_sens, float(np.linalg.norm(np.asarray(Fs) - (np.asarray(Fe) - [0, 0, -0.04 * 9.81]))))
                    n_pts += 1
    gate("門 13 力の閉じ(格子 12 走行、停滞中 = 準静的な %d 刻): 手首ばねのたわみから推定した荷重 + 重力と MuJoCo の接触力の和が釣り合う |ΣF| ≤ 0.5 N、"
         "手首の力センサ(site 系 → 世界)とばねの推定の差 ≤ 0.1 N —— 外部の F/T センサ無しでも剛性で荷重が読める根拠(動いている刻を含めると衝突の過渡で %.1f N)"
         % (n_pts, worst_dyn), worst_eq < 0.5 and worst_sens < 0.1,
         "max |F_est + ΣF_c| = %.3f N、max |F_sensor − F_spring| = %.3f N" % (worst_eq, worst_sens))
    _NUM["force_closure_N"] = {"eq_stalled": worst_eq, "sensor_stalled": worst_sens, "eq_all_ticks": worst_dyn}
    # ── 14. 分類と回復
    ct, cv, sr = g["confusion_truth"], g["confusion_vision"], g["success"]
    gate("門 14 注入格子 6 クラス × {回復なし, あり}: 真値署名の分類 = 注入クラス %d / %d、視覚のずれ(構え時の RGB-D + エンコーダ積分)で作った署名でも %d / %d、"
         "回復なしの成功 %d / %d(基準)、回復ありの成功 %d / %d(blocked は正しく中止 = 成功)、%.1f s"
         % (int(np.trace(ct["matrix"])), ct["n"], int(np.trace(cv["matrix"])), cv["n"], *sr[False], *sr[True], time.time() - t0),
         ct["accuracy"] == 1.0 and cv["accuracy"] == 1.0 and sr[False][0] == 0 and sr[True][0] >= 4)
    _NUM["grid_success"] = {"no_recovery": list(sr[False]), "recovery": list(sr[True])}
    # ── 15. 遅れ
    lat = {row["injected"]: row["latency_ticks"] for row in g["rows"] if not row["recover"]}
    stall_lat = [lat[c] for c in ("missed_hole", "wedging", "jamming")]
    gate("門 15 検出の遅れ(刻 = 10 ms): 停滞で見つける 3 クラス(missed / wedging / jamming)は %s 刻 = 窓 30 + 確認 ≤ 10、栓は接触から %d 刻、囮は接触から %d 刻"
         % ([int(x) for x in stall_lat], lat["blocked_hole"], lat["wrong_hole"]),
         all(30 <= x <= 40 for x in stall_lat) and lat["blocked_hole"] <= 15 and lat["wrong_hole"] <= 25)
    _NUM["latency_ticks"] = {k: (None if (isinstance(v, float) and math.isnan(v)) else float(v)) for k, v in lat.items()}
    # ── 16. くさびと詰まりの区別(力を抜く探針)
    pre = F.insertion_failure_presets(KP)
    t1 = time.time()
    rw = F.pegfail_episode_run(KP, injected="wedging", recover=False, release_probe=True, **pre["wedging"])["release"]
    rj = F.pegfail_episode_run(KP, injected="jamming", recover=False, release_probe=True, **pre["jamming"])["release"]
    out["release"] = (rw, rj)
    gate("門 16 Whitney の区別を物理で: くさび(μ 0.8、θ %.1f°)は押す力を抜き(F_z %.2f → %.2f N)さらに 2 mm 引いても(F_z %.2f N)深さ %.2f → %.2f mm で動かない = "
         "内部に圧縮が溜まっている; 詰まり(μ 0.3、θ %.1f°、F_x %.1f N)は横の力も抜くと自重で %.2f → %.2f mm 進み、引くと %.2f mm まで戻る = 力の向きの問題、%.1f s"
         % (rw["tilt_before_deg"], rw["F_z_before_N"], rw["F_z_unloaded_N"], rw["F_z_pulled_N"], rw["depth_before_mm"], rw["depth_pulled_mm"],
            rj["tilt_before_deg"], rj["F_x_before_N"], rj["depth_before_mm"], rj["depth_unloaded_mm"], rj["depth_pulled_mm"], time.time() - t1),
         rw["stuck"] and rw["F_z_pulled_N"] < 0 and abs(rw["depth_before_mm"] - rw["depth_pulled_mm"]) < 0.5 and not rj["stuck"]
         and rj["depth_before_mm"] - rj["depth_pulled_mm"] > 0.5)
    _NUM["release"] = {"wedging": rw, "jamming": rj}
    # ── 17. かじりの余裕: 停滞の点は外、滑りは内
    ep_j = next(e for e in g["episodes"] if e["injected"] == "jamming" and not e["recover"])
    r = ep_j["rec"]
    i_det = [k for k, dd in enumerate(r["detected"]) if dd][0]
    m_det = r["jam_margin"][i_det]
    ep_n = F.pegfail_episode_run(KP, injected="nominal", recover=False, eps_mm=(0.3, 0.0), tilt_deg=3.0)
    rn = ep_n["rec"]
    slide = np.array([m for m, c, fz in zip(rn["jam_margin"], rn["contact"], rn["F_z"]) if c == "two_point" and np.isfinite(m) and fz is not None and fz > 1.0])
    out["jam_episode"], out["nominal3"] = ep_j, ep_n
    gate("門 17 かじりの図の余裕(4 辺の最小、負 = 外): 詰まりの停滞を検出した刻は %.2f(外、F_x/F_z = %.2f、M/(rF_z) = %.2f)、μ 0.3・θ 3° の正常な二点滑り %d 刻は"
         " min %.2f / 中央値 %.2f(内)—— 「内側」の閾値 0.15 はこの間に置いた(MuJoCo の滑りの境目は Whitney の線より ≈ 0.15 内側: 36 角形の壁・柔らかい接触)"
         % (m_det, r["fx_over_fz"][i_det], r["m_over_rfz"][i_det], len(slide), slide.min(), np.median(slide)),
         m_det < -0.3 and slide.min() >= 0.15 and ep_n["success"])
    _NUM["jam_margin"] = {"at_detection": float(m_det), "sliding_min": float(slide.min()), "sliding_median": float(np.median(slide)), "sliding_n": int(len(slide))}
    # ── 18. くさびは境目の上だけ
    t1 = time.time()
    e_lo = F.pegfail_episode_run(KP, injected="wedging_below", recover=False, eps_mm=(0.3, 0.0), tilt_deg=2.0, mu=0.8)
    e_mu3 = F.pegfail_episode_run(KP, injected="wedging_mu03", recover=False, eps_mm=(0.3, 0.0), tilt_deg=4.5)
    gate("門 18 くさびは境目の上だけ: μ 0.8 で θ₀ = 2.0°(< c/μ = 2.76°)は wedging を出さず入る(深さ %.1f mm、%s)、μ 0.3 で θ₀ = 4.5°(< 7.35°)も wedging を出さない"
         "(%s、深さ %.1f mm)、μ 0.8・θ₀ 4.5° は出す(格子)、%.1f s"
         % (e_lo["rec"]["depth"][-1] * 1e3, e_lo["status"], e_mu3["status"], e_mu3["rec"]["depth"][-1] * 1e3, time.time() - t1),
         "wedging" not in set(e_lo["rec"]["cls_truth"]) and e_lo["success"] and "wedging" not in set(e_mu3["rec"]["cls_truth"]))
    # ── 19. 視覚の錨
    single = [e["vision_anchor"]["hole_err_mm"] for e in g["episodes"] if e["injected"] != "wrong_hole" and e["vision_anchor"]["ok"]]
    decoy = [e["vision_anchor"]["hole_err_mm"] for e in g["episodes"] if e["injected"] == "wrong_hole" and e["vision_anchor"]["ok"]]
    gate("門 19 視覚の錨(構え時の手首 RGB-D、穴の円は治具の半径 R + W で当てる): 穴 1 つの場面では穴中心の誤差 max %.3f mm(%d 走行)、囮の穴がある場面では %.2f mm "
         "—— 目標の穴は見つけるが囮が当てはめを乱す(正直に)" % (max(single), len(single), max(decoy)), max(single) < 0.05 and max(decoy) < 0.6)
    _NUM["vision_anchor_mm"] = {"single_max": max(single), "decoy_max": max(decoy)}
    # ── 20. 記録つきの走行(GIF 用)
    t1 = time.time()
    rec_ep = F.pegfail_episode_run(KP, injected="wedging", recover=True, record=True, frame_every=0.1, **pre["wedging"])
    labels = [f["label"] for f in rec_ep["frames"]]
    out["gif_episode"] = rec_ep
    gate("門 20 手首カメラの記録つき走行(くさび → 検出 → 退避して傾きを戻す → 成功): コマ %d 枚、ラベルに detected: wedging と retract_reduce_tilt が現れ、成功、%.1f s"
         % (len(rec_ep["frames"]), time.time() - t1),
         len(rec_ep["frames"]) >= 20 and any("detected: wedging" in s for s in labels) and any("retract_reduce_tilt" in s for s in labels) and rec_ep["success"])
    print("  mujoco の門: %.1f s" % (time.time() - t0))
    return out


# ======================================================================================================================
def figures(out: dict) -> None:
    print("== 図")
    vb = F.vision_boundary_flip(KP, np.linspace(0.9e-3, 1.5e-3, 61), 0.05e-3, n=3000)
    figs.save_plot("pegfail_where_it_breaks_offset_flip",
                   [("measured flip rate (σ = 0.05 mm)", vb["eps"] * 1e3, vb["flip_rate"]), ("Φ(−|ε − 1.2| / σ)", vb["eps"] * 1e3, vb["flip_theory"])],
                   xlabel="true offset ε [mm]", ylabel="P(offset field flips)", title="Where it breaks: the W + c_r boundary", styles=[None, "dashed"],
                   caption="視覚のずれに σ = 0.05 mm の雑音を足すと、境目 W + c_r = 1.2 mm の ±0.1 mm では missed_hole と chamfer_sliding の欄が反転する"
                           "(境目ちょうどで %.3f、±1σ で %.3f / %.3f)。破線は正規雑音の理論値 Φ(−|z|)。" % (_NUM["flip"]["at_boundary"], _NUM["flip"]["minus_1sigma"], _NUM["flip"]["plus_1sigma"]))
    if "grid" not in out:
        print("  図 2〜6 は --full(MuJoCo)のときだけ")
        return
    g = out["grid"]
    ct, cv = g["confusion_truth"], g["confusion_vision"]
    used = [c for c in ct["classes"] if ct["matrix"][ct["classes"].index(c)].sum() or ct["matrix"][:, ct["classes"].index(c)].sum()]
    hdr = ["injected \\ classified"] + used + ["(vision)"]
    rows = []
    for c in used:
        i = ct["classes"].index(c)
        rows.append([c] + [str(int(ct["matrix"][i, ct["classes"].index(k)])) for k in used] + ["%d/%d" % (cv["matrix"][i, i], cv["matrix"][i].sum())])
    figs.save_table("pegfail_failure_confusion", hdr, rows, title="Confusion: injected failure vs rule-table class (truth signatures; last column = from vision)",
                    caption="注入した失敗 6 クラスと表の分類(真値署名): 対角 %d / %d。右列は視覚のずれ(構え時の RGB-D + エンコーダ積分)で作った署名の正答 %d / %d。"
                            % (int(np.trace(ct["matrix"])), ct["n"], int(np.trace(cv["matrix"])), cv["n"]))
    # かじりの図 + 軌跡
    ep = out["jam_episode"]
    r = ep["rec"]
    i_det = [k for k, dd in enumerate(r["detected"]) if dd][0]
    ell = max(r["depth"][i_det] - KP["chamfer"], 0.0)
    pg = F.jamming_parallelogram_planar(KP, ell)
    V = np.vstack([pg["vertices"], pg["vertices"][:1]])
    pts = [(x, y) for x, y, c, fz in zip(r["fx_over_fz"], r["m_over_rfz"], r["contact"], r["F_z"]) if c == "two_point" and x is not None and fz > 1.0]
    xs, ys = (np.array([p[0] for p in pts]), np.array([p[1] for p in pts])) if pts else (np.zeros(1), np.zeros(1))
    rn = out["nominal3"]["rec"]
    pn = [(x, y, dz) for x, y, c, fz, dz in zip(rn["fx_over_fz"], rn["m_over_rfz"], rn["contact"], rn["F_z"], rn["depth"]) if c == "two_point" and x is not None and fz > 1.0]
    xn, yn = np.array([p[0] for p in pn]), np.array([p[1] for p in pn])
    ell_n = float(np.median([p[2] for p in pn])) - KP["chamfer"] if pn else 10e-3
    pgn = F.jamming_parallelogram_planar(KP, ell_n)
    Vn = np.vstack([pgn["vertices"], pgn["vertices"][:1]])
    figs.save_plot("pegfail_jamming_diagram_measured",
                   [("Whitney p.34 at the jam, l = %.1f mm" % (ell * 1e3), V[:, 0], V[:, 1]), ("same at l = %.1f mm (nominal)" % (ell_n * 1e3), Vn[:, 0], Vn[:, 1]),
                    ("jam: two-point, F_z > 1 N", xs, ys), ("detected stall", np.array([r["fx_over_fz"][i_det]]), np.array([r["m_over_rfz"][i_det]])),
                    ("nominal θ₀ = 3° sliding", xn, yn)],
                   xlabel="F_x / F_z", ylabel="M / (r F_z)", title="Jamming diagram with measured wrist loads (μ = 0.3)", size=(760, 440),
                   kinds=["line", "line", "scatter", "scatter", "scatter"], styles=["dashed", "dotted", None, None, None], xlim=(-4, 4), ylim=(-8, 8),
                   caption="手首ばねのたわみから推定した先端の力の比。停滞を検出した点は自分の深さの平行四辺形の外(余裕 %.2f)、正常な二点滑りは自分の深さ"
                           "(より深い = 広い)の内側(min %.2f)。深さで平行四辺形が広がるので 1 枚に 2 つ描く。" % (r["jam_margin"][i_det], _NUM["jam_margin"]["sliding_min"]))
    # 深さ vs 刻(くさび、回復あり)
    ge = out["gif_episode"]
    rg = ge["rec"]
    t = np.arange(len(rg["depth"]))
    z = np.array(rg["depth"]) * 1e3
    st = np.array(rg["stalled"], bool)
    det = np.array(rg["detected"], bool)
    series = [("tip depth [mm]", t, z), ("stalled (detector)", t[st], z[st])]
    if det.any():
        series.append(("detected: " + rg["cls_truth"][int(np.argmax(det))], t[det], z[det]))
    for rc in ge["recoveries"]:
        series.append(("recovery: %s" % rc["primitive"], np.array([rc["tick"]]), np.array([z[rc["tick"]]])))
    figs.save_plot("pegfail_depth_vs_tick_stall_detection", series, xlabel="control tick (10 ms)", ylabel="tip depth [mm]",
                   title="Wedging episode: stall → class → recovery", kinds=["line"] + ["scatter"] * (len(series) - 1),
                   caption="μ = 0.8・θ₀ = 4.5° のくさび。深さが止まってから窓 30 刻で停滞、同じ刻に表が wedging を出し、退避 + 傾き戻しで再降下して成功"
                           "(回復 %d 回、最終深さ %.1f mm)。" % (len(ge["recoveries"]), z[-1]))
    # 手首カメラの GIF(ラベル入り)
    frames = []
    for fr in ge["frames"]:
        img = fr["rgb"].astype(np.float64) / 255.0
        txt = "t = %.2f s   %s" % (fr["t"], fr["label"])
        try:
            img = np.asarray(AN.text_box(img, txt, (10, 10), anchor="lt", font_size=18))
        except Exception as exc:  # noqa: BLE001  文字が収まらない等は図を落とさず素のコマ
            figs._errors.append("text_box: %r" % (exc,))
        frames.append((np.clip(img, 0, 1) * 255).astype(np.uint8))
    figs.save_gif("pegfail_wrist_camera_wedging_detect_recover", frames, fps=8.0,
                  caption="手首カメラ(640×480、0.1 s ごと、%d コマ): 降下 → くさびで止まる → 'detected: wedging' → 退避して傾きを戻す → 再降下で成功。" % len(frames))
    # 力を抜く探針の表
    rw, rj = out["release"]
    hdr = ["probe", "class", "θ [deg]", "depth before [mm]", "F_z before [N]", "F_z unloaded [N]", "depth unloaded [mm]", "F_z pulled [N]", "depth pulled [mm]", "stuck"]
    rows = [[nm, rr["cls"], "%.2f" % rr["tilt_before_deg"], "%.2f" % rr["depth_before_mm"], "%.2f" % rr["F_z_before_N"], "%.2f" % rr["F_z_unloaded_N"],
             "%.2f" % rr["depth_unloaded_mm"], "%.2f" % rr["F_z_pulled_N"], "%.2f" % rr["depth_pulled_mm"], str(rr["stuck"])]
            for nm, rr in (("wedging (μ 0.8)", rw), ("jamming (μ 0.3)", rj))]
    figs.save_table("pegfail_release_probe_wedge_vs_jam", hdr, rows, title="Release probe: remove all applied forces, then pull 2 mm",
                    caption="くさびは力を抜いても引いても動かない(深さ %.2f → %.2f mm、内部圧縮)、詰まりは横の力を抜くと自重で進み(%.2f → %.2f mm)引けば戻る"
                            "(%.2f mm、力の向きの問題)—— Whitney の区別を MuJoCo で。" % (rw["depth_before_mm"], rw["depth_pulled_mm"], rj["depth_before_mm"],
                                                                         rj["depth_unloaded_mm"], rj["depth_pulled_mm"]))
    print("  figures:", figs.errors() or "ok")


# ======================================================================================================================
def main() -> int:
    t_all = time.time()
    out = numpy_part()
    if FULL:
        out = full_part(out)
    else:
        skip("門 13〜20(MuJoCo)", "--full のときだけ(mujoco)")
    if figs.enabled():
        figures(out)
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    n_ng = sum(1 for _, ok in _GATES if not ok)
    print("gates: %d / %d ok  (%.1f s)" % (len(_GATES) - n_ng, len(_GATES), time.time() - t_all))
    if n_ng or figs.errors():
        print("FAIL")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
