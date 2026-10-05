# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""ドーム状の柔らかい指先センサを平らな物に押す —— 大変形のスケーリング則を門に、Hertz がどの押し込みで何 % 外れるかを数で出す(2026-10-05)。

物理シミュ × Fullseye 系列(視触覚 (b))。tacsim(Hertz の膜、小変形)の先。指先のドーム(半球、高さ L = 半径 R)を平らな物に δ 押すと、
δ/L が 0.3 を超えたあたりから小変形の Hertz が外れる。外から来るもの:
  * **論文のスケーリング則**(T. Mu ほか, arXiv:2509.18581, 2025): F = κₙ(δ/L)·F_L(式 2)、接触半径の式 (4)(不完全ベータ)、普遍形
    κ = (1 − 10/9·δ/L)⁻¹(式 6)、検証範囲 δ/L ≤ 0.5。**式 (3) の 1 次の係数は原文の活字 (4+2n)/(1+n) では円柱で力が負になる** ——
    本文の模型(1D の非線形ばね、各ばねは同じ材料の円柱)を組み直して積分した 2n/(1+n) を使い、活字・以前のメモ 2/(1+n) との 3 つの読みを
    門で比べる。
  * **連続体の厳密解**: 非圧縮 neo-Hookean の円柱の一軸圧縮 P = μ(λ⁻² − λ)、半径 λ^{−1/2}(n = 1 と p = ∞ の厳密な真値)。
  * **Hertz の小変形極限**(tacsim の hertz_force / hertz_sphere = 被験者)。
  * **MuJoCo の柔体(--full)**: 線形弾性の立方体を摩擦なしの平板で圧縮 —— 小ひずみの剛性 E·A·ε だけを門にし、大ひずみで neo-Hookean と
    どう違うかを数で出す(第 2 実装としては使えない理由を見せる)。
自分で作ったのは式 (3)(4) の導出、ばね列の数値積分(閉形式の第 2 実装)、内側カメラの接触像と面積法の半径、半径 → 力の逆算。

門(既定 13 本、numpy): 3 つの読みの判定(連続体の厳密解)、式 (4) の 3 経路の一致、ばね列 = 閉形式と 2 次の係数 n/(2+n)(活字と一致)、
定理 κₙ ≤ κ₁(挿入図の並び)、Hertz の極限と d → 0 の傾き、普遍形 = 円柱の κ₁ の最小二乗(k = 10/9)、論文の「0.3 を超えると外れる」、半径から読む Hertz は球で
6 % 以内・円錐で外れる、像から半径(面積法と縁の円の当てはめ)、半径 → 力の逆算、雑音、往復、fail-closed。
--full(+2 本): 512 px の像で 20 点の掃引、MuJoCo の柔体の小ひずみ剛性。

図(既定 6 枚 + --full 1 枚): 押し込みの GIF(内側カメラの像・ばね列・F–δ/L の曲線に点が増える)、3 形状の F–δ/L(Hertz 破線)、κ⁻¹ の帯と
3 つの読み、a/a_L と円柱の厳密解、Hertz の誤差 vs δ/L(観測量 3 つ)、接触像の等倍切り出しと読んだ円。

正直に: 半球は放物線で近似(論文と同じ)、摩擦なし・準静的・非圧縮、寸法と弾性率(R = L = 8 mm、μ = 0.1 MPa)は設計の仮定(論文のセンサの
寸法は付録で未読)。論文の図 5C(半球 1 個の半径 vs 力)は Hertz の半径が 1 割以上大きく描かれているが、導出した模型では 2 % 以内で、
この図は再現できない。実験値は論文の図の中だけ(数値化しない)。
Run: py -3.11 examples/poc_tacdome_large_deformation.py [--full]        (--full の門 15 は mujoco)
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import measure as FM  # noqa: E402
import tacdome as TD  # noqa: E402
import tacsim as TS  # noqa: E402

FULL = "--full" in sys.argv
_GATES = []
_NUM = {}
R_DOME = L_DOME = 8.0e-3            # 半球の指先: 半径 = 高さ = 8 mm(設計の仮定)
MU = 0.1e6                          # 柔らかいシリコンの剪断弾性率 0.1 MPa(仮定)、非圧縮 → E* = 4μ
ES = 4.0 * MU
CONE_SLOPE = 1.0                    # 円錐: 高さ = 底の半径(論文の有限要素と同じ比)
N_IMG, FOV = 192, 2.8 * R_DOME      # 内側カメラ 192 px、視野 22.4 mm(0.117 mm/px)
FOOT = 1.3 * R_DOME                 # ドームの底のフランジの円(見た目と背景の輪)
D_IMG = (0.05, 0.1, 0.2, 0.3, 0.4, 0.5)


def gate(name, ok, detail=""):
    _GATES.append((name, bool(ok)))
    print("  [%s] %s %s" % ("ok" if ok else "NG", name, detail))


def _raises(fn):
    try:
        fn()
    except ValueError:
        return True
    return False


def _lins():
    return {"sphere": TD.powerlaw_linear_contact("sphere", R_DOME, ES),
            "cone": TD.powerlaw_linear_contact("cone", CONE_SLOPE, ES),
            "punch": TD.powerlaw_linear_contact("punch", R_DOME, ES)}


def _read_image(d, lin, noise=0.0, seed=0, n=N_IMG, fov=FOV):
    """d の押し込みの接触像を作り、面積法・しきい値・縁の円の 3 通りで半径を読み、半径から力を逆算する。"""
    pitch = fov / n
    fw = TD.large_deformation_contact(d * L_DOME, L_DOME, lin)
    img = TD.dome_contact_image(fw["a"], pitch, n, footprint=FOOT, noise=noise, seed=seed)
    rd = TD.contact_patch_radius(img, pitch)
    circ = FM.fit_circle(rd["edge_points"])
    inv = TD.large_deformation_inverse(rd["a"], L_DOME, lin)
    return {"d": d, "a": fw["a"], "F": fw["F"], "img": img, "pitch": pitch, "rd": rd, "a_circle": circ["r"] * pitch, "circ": circ,
            "inv": inv, "F_hertz_tacsim": TS.hertz_force(R_DOME, ES, a=rd["a"]),
            "err_a_pct": 100 * (rd["a"] / fw["a"] - 1), "err_thr_pct": 100 * (rd["a_threshold"] / fw["a"] - 1),
            "err_circ_pct": 100 * (circ["r"] * pitch / fw["a"] - 1), "err_F_pct": 100 * (inv["F"] / fw["F"] - 1),
            "err_hertz_pct": 100 * (TS.hertz_force(R_DOME, ES, a=rd["a"]) / fw["F"] - 1)}


def numpy_part():
    print("== 門(読みの判定・閉形式・第 2 実装・被験者・センサの読み出し)")
    t0 = time.time()
    lins = _lins()
    dd = np.linspace(0.01, 0.9, 90)
    exact = TD.neohookean_cylinder_exact(dd)
    k_der = TD.largedef_correction(dd, 1.0)
    k_prn = TD.largedef_correction(dd, 1.0, "printed")
    e_der = float(np.max(np.abs(k_der / exact["kappa"] - 1)))
    e_rr = float(np.max(np.abs(TD.largedef_radius_ratio(dd, math.inf) / exact["radius_ratio"] - 1)))
    k_n15 = {r: TD.largedef_correction(dd, 1.5, r) for r in TD.C1_READINGS}
    memo_bad = bool(np.any(k_n15["memo"] > TD.largedef_correction(dd, 1.0, "memo") + 1e-12))
    _NUM["printed_k1_05"] = float(TD.largedef_correction(0.5, 1.0, "printed"))
    gate("門 1 式 (3) の読み: 導出 c₁ = 2n/(1+n) は n = 1 で非圧縮 neo-Hookean の円柱の厳密解 [(1−d)⁻² − (1−d)]/(3d) と 1e-12、"
         "p = ∞ の式 (4) は半径の伸び λ^{−1/2} と 1e-12。活字 (4+2n)/(1+n) は d = 0.5 で κ₁ = %.3f(力が負)、メモ 2/(1+n) は n = 1.5 で "
         "κ₁.₅ > κ₁(定理を破る)で棄却" % _NUM["printed_k1_05"],
         e_der < 1e-12 and e_rr < 1e-12 and _NUM["printed_k1_05"] < 0 and float(np.min(k_prn)) < 0 and memo_bad,
         "max |κ/厳密 − 1| = %.1e、半径 %.1e" % (e_der, e_rr))
    d6 = np.array([0.02, 0.1, 0.3, 0.5, 0.7, 0.9])
    p1 = (2 / (3 * d6)) * (1 - (1 - d6) ** 1.5) / np.sqrt(1 - d6)
    p2 = (np.sqrt(1 - d6) / 2 + np.arctan2(np.sqrt(d6), np.sqrt(1 - d6)) / (2 * np.sqrt(d6))) / np.sqrt(1 - d6)
    e_cf = max(float(np.max(np.abs(TD.largedef_radius_ratio(d6, 1.0) - p1))), float(np.max(np.abs(TD.largedef_radius_ratio(d6, 2.0) - p2))))
    e_bt = max(float(np.max(np.abs(TD.largedef_radius_ratio(d6, p) - TD.largedef_radius_ratio(d6, p, "beta")))) for p in (1.5, 3.0, 8.0, 50.0))
    gate("門 2 式 (4) の 3 経路: 積分 ∫₀¹√((1 − d uᵖ)/(1 − d))du(複合 Gauss–Legendre)= p = 1・2 の閉形式(1e-12)= 原文の形 "
         "(1/p)B_d(1/p, 3/2)d^{−1/p}/√(1−d)(不完全ベータの連分数、p = 1.5/3/8/50 で 1e-12)",
         e_cf < 1e-12 and e_bt < 1e-12, "閉形式 %.1e、ベータ %.1e" % (e_cf, e_bt))
    errs, coefs = [], {}
    for sh, lin in lins.items():
        for d in (0.05, 0.2, 0.35, 0.5):
            sb = TD.mdr_spring_bed(d * L_DOME, L_DOME, lin)
            fw = TD.large_deformation_contact(d * L_DOME, L_DOME, lin)
            errs.append(max(abs(sb["kappa"] / fw["kappa"] - 1), abs(sb["radius_ratio"] / fw["radius_ratio"] - 1)))
        if sh != "punch":
            ds = np.linspace(0.02, 0.6, 12)
            kk = np.array([TD.mdr_spring_bed(x * L_DOME, L_DOME, lin, 20000)["kappa"] for x in ds])
            c = np.polyfit(ds, kk * (1 - ds) ** 2, 2)          # c[0] d² + c[1] d + c[2]
            coefs[sh] = (-c[1], c[0], lin["n"])
    e_sb = max(errs)
    ok_c = all(abs(c1 - 2 * n / (1 + n)) < 1e-4 and abs(c2 - n / (2 + n)) < 1e-4 for c1, c2, n in coefs.values())
    _NUM["coef"] = {k: (round(float(v[0]), 5), round(float(v[1]), 5)) for k, v in coefs.items()}
    gate("門 3 ばね列(第 2 実装: 長さ L − g(x) の neo-Hookean 円柱ばねを中点則で直接積分)= 閉形式の κₙ と a/a_L(球・円錐・平頭 × "
         "d 4 点で 1e-7)、数値から当てた係数は 1 次 2n/(1+n)・2 次 n/(2+n)(活字の 2 次と一致、1e-4)",
         e_sb < 1e-7 and ok_c, "max %.1e、球 (c₁, c₂) = %s(導出 1.2, 0.4286)、円錐 %s(1.3333, 0.5)" % (e_sb, _NUM["coef"]["sphere"], _NUM["coef"]["cone"]))
    kb = {n: TD.largedef_correction(dd, n) for n in (1.0, 1.25, 1.5, 2.0)}
    order_ok = bool(np.all(kb[2.0] <= kb[1.5] + 1e-15) and np.all(kb[1.5] <= kb[1.25] + 1e-15) and np.all(kb[1.25] <= kb[1.0] + 1e-15))
    i05 = int(np.argmin(np.abs(dd - 0.5)))
    _NUM["kinv05"] = {n: round(1 / float(kb[n][i05]), 3) for n in (1.0, 1.5, 2.0)}
    gate("門 4 定理 κₙ ≤ κ₁(局所ひずみ ≤ d の重みつき平均): n = 2 ≤ 1.5 ≤ 1.25 ≤ 1 が d ∈ (0, 0.9] の全点で成り立つ = 論文の図 4B の挿入図の並び "
         "(κ⁻¹ で n = 2 が上・n = 1 が下、図から読んだ定性値)", order_ok,
         "κ⁻¹(0.5) = %s(n = 1 / 1.5 / 2)" % list(_NUM["kinv05"].values()))
    sph = lins["sphere"]
    dl = 1e-4 * L_DOME
    FL_ts = TS.hertz_force(R_DOME, ES, delta=dl)
    hz = TS.hertz_sphere(FL_ts, R_DOME, ES)
    fw0 = TD.large_deformation_contact(dl, L_DOME, sph)
    eps = 1e-6
    sl_k = (TD.largedef_correction(eps, 1.5) - 1) / eps
    sl_a = (TD.largedef_radius_ratio(eps, 2.0) - 1) / eps
    gate("門 5 Hertz の小変形極限(被験者 tacsim): 線形解 = tacsim.hertz_force(δ) と hertz_sphere の a(1e-12)、d → 0 の傾き "
         "(κ − 1)/d → 2/(1+n) = 0.8、(a/a_L − 1)/d → p/(2(p+1)) = 1/3(1e-5)",
         abs(fw0["F_L"] / FL_ts - 1) < 1e-12 and abs(fw0["a_L"] / hz["a"] - 1) < 1e-12 and abs(sl_k - 0.8) < 1e-5 and abs(sl_a - 1 / 3) < 1e-5,
         "傾き %.6f / %.6f" % (sl_k, sl_a))
    du = np.linspace(0.005, 0.5, 100)
    uni = TD.largedef_universal_correction(du)
    dev = {n: float(np.max(np.abs(uni / TD.largedef_correction(du, n) - 1))) * 100 for n in (1.0, 1.5, 2.0)}
    dk = np.linspace(1e-3, 0.999, 999)
    kfit = {n: float(np.sum((1 - 1 / TD.largedef_correction(dk, n)) * dk) / np.sum(dk * dk)) for n in (1.0, 1.5, 2.0)}
    _NUM["kfit"] = {n: round(v, 4) for n, v in kfit.items()}
    _NUM["universal_dev"] = {n: round(v, 2) for n, v in dev.items()}
    stiffer = du[uni > TD.largedef_correction(du, 1.0)]
    _NUM["universal_stiffer_below"] = round(float(stiffer.max()), 3) if stiffer.size else 0.0
    gate("門 6 普遍形 (1 − 10/9·d)⁻¹(式 6)と導出した κₙ: 円柱 κ₁ とは d ≤ 0.5 で %.2f %% 以内、κ₁⁻¹ ≈ 1 − k d の最小二乗(d ∈ [0, 1])は "
         "k = %.4f(公表値 10/9 = 1.1111 と 0.5 %% 以内)。球 %.1f %%・円錐 %.1f %% は普遍形が高い(「狭い帯」は再現しない、正直に)"
         % (dev[1.0], kfit[1.0], dev[1.5], dev[2.0]),
         dev[1.0] < 4.0 and abs(kfit[1.0] / TD.UNIVERSAL_K - 1) < 0.005,
         "d < %.3f では普遍形が円柱より硬い(帯の外)、k(n = 1 / 1.5 / 2) = %s" % (_NUM["universal_stiffer_below"], list(_NUM["kfit"].values())))
    hs = TD.hertz_small_strain_error(np.array([0.05, 0.3, 0.5]), 2.0)
    _NUM["hertz_sphere"] = {k: [round(float(x), 2) for x in v] for k, v in hs.items() if k != "d"}
    gate("門 7 論文の記述「δ/L が 0.3 を超えると Hertz は力も半径も大きく過小評価」: 球で押し込みから読む力 %.1f %%・半径 %.1f %%(d = 0.3)、"
         "d = 0.05 では力 %.1f %%(5 %% 以内)" % (hs["force_from_delta"][1], hs["radius_from_delta"][1], hs["force_from_delta"][0]),
         hs["force_from_delta"][1] < -20 and hs["radius_from_delta"][1] < -10 and hs["force_from_delta"][0] > -5)
    dr = np.linspace(0.005, 0.5, 100)
    fr_s = TD.hertz_small_strain_error(dr, 2.0)["force_from_radius"]
    fr_c = TD.hertz_small_strain_error(0.5, 1.0)["force_from_radius"]
    _NUM["hertz_from_radius"] = {"sphere_max": round(float(np.max(np.abs(fr_s))), 2), "sphere_argmax": round(float(dr[np.argmax(np.abs(fr_s))]), 3),
                                 "cone_05": round(float(fr_c), 2)}
    gate("門 8 観測量で外れ方が変わる: 接触半径から Hertz で力を読むと(センサの読み方)球は d ≤ 0.5 で max %.2f %%(κ と半径の伸びが打ち消す)、"
         "円錐は d = 0.5 で %.1f %%" % (_NUM["hertz_from_radius"]["sphere_max"], fr_c),
         _NUM["hertz_from_radius"]["sphere_max"] <= 6.0 and fr_c < -15.0)
    rows = [_read_image(d, sph) for d in D_IMG]
    _NUM["img"] = [{k: round(r[k], 3) for k in ("d", "err_a_pct", "err_thr_pct", "err_circ_pct", "err_F_pct", "err_hertz_pct")} for r in rows]
    ea = max(abs(r["err_a_pct"]) for r in rows)
    ec = max(abs(r["err_circ_pct"]) for r in rows)
    gate("門 9 内側カメラの像から接触半径(192 px、0.117 mm/px、a = %.1f〜%.1f px): 面積法 max %.3f %%、縁の画素に measure.fit_circle "
         "(被験者)max %.2f %%(縁の画素は内側に寄る)" % (rows[0]["rd"]["a_px"], rows[-1]["rd"]["a_px"], ea, ec),
         ea < 0.2 and ec < 5.0, "しきい値の画素数 %s %%" % [round(r["err_thr_pct"], 2) for r in rows])
    eF = max(abs(r["err_F_pct"]) for r in rows)
    gate("門 10 半径 → 力の逆算(式 4 を二分法、式 2): 6 押し込みで max %.3f %%、同じ半径を tacsim.hertz_force(a) で読むと %s %%"
         % (eF, [round(r["err_hertz_pct"], 2) for r in rows]), eF < 0.5)
    noisy = [_read_image(d, sph, noise=0.03, seed=7 + i) for i, d in enumerate(D_IMG)]
    eFn = max(abs(r["err_F_pct"]) for r in noisy)
    _NUM["noise_F"] = round(eFn, 3)
    gate("門 11 雑音 σ = 0.03(コントラスト 0.88 に対し)でも半径の線形和は偏らない: 力の誤差 max %.3f %%" % eFn, eFn < 1.0)
    rt = []
    for sh, lin in lins.items():
        for d in (0.03, 0.25, 0.5, 0.7):
            fw = TD.large_deformation_contact(d * L_DOME, L_DOME, lin)
            inv = TD.large_deformation_inverse(fw["a"], L_DOME, lin)
            rt.append(abs(inv["d"] / d - 1))
    gate("門 12 往復: δ → (F, a) → δ が球・円錐・平頭 × 4 点で 1e-9(平頭は閉形式 d = 1 − (a0/a)²)", max(rt) < 1e-9, "max %.1e" % max(rt))
    fc = [_raises(lambda: TD.largedef_correction(1.0, 1.5)), _raises(lambda: TD.largedef_correction(0.3, 1.5, "derivd")),
          _raises(lambda: TD.powerlaw_linear_contact("sphre", R_DOME, ES)), _raises(lambda: TD.powerlaw_linear_contact("power", 1.0, ES)),
          _raises(lambda: TD.large_deformation_contact(L_DOME, L_DOME, sph)), _raises(lambda: TD.large_deformation_inverse(R_DOME * 0.5, L_DOME, lins["punch"])),
          _raises(lambda: TD.contact_patch_radius(np.full((64, 64), 0.3), 1e-4)), _raises(lambda: TD.largedef_universal_correction(0.95)),
          _raises(lambda: TD.dome_contact_image(5e-3, 1e-4, 64)),
          bool(np.isnan(TD.large_deformation_contact(0.3 * L_DOME, L_DOME, lins["punch"])["F_hertz_from_radius"]))]
    gate("門 13 fail-closed: d ≥ 1・読みの綴り違い・形の綴り違い・power で p 無し・δ = L・平頭で a ≤ a0・平らな像・k d ≥ 1・窓に入らない円盤は "
         "ValueError、平頭の「半径から Hertz」は nan(半径が δ を決めない)", all(fc), "%d / %d" % (sum(fc), len(fc)))
    print("  既定の門 %.2f s" % (time.time() - t0))
    return {"lins": lins, "rows": rows, "noisy": noisy}


def full_part(ctx):
    print("== --full")
    t0 = time.time()
    sph = ctx["lins"]["sphere"]
    ds = np.linspace(0.03, 0.55, 20)
    rows = [_read_image(float(d), sph, n=512) for d in ds]
    ea = max(abs(r["err_a_pct"]) for r in rows)
    eF = max(abs(r["err_F_pct"]) for r in rows)
    _NUM["full_img"] = (round(ea, 4), round(eF, 4))
    gate("門 14 512 px(0.044 mm/px)の像で d = 0.03〜0.55 の 20 点: 半径 max %.4f %%、力 max %.4f %%(d > 0.5 は検証範囲の外と印)" % (ea, eF),
         ea < 0.05 and eF < 0.2, "%.1f s" % (time.time() - t0))
    ctx["full_rows"] = rows
    try:
        import mujoco  # noqa: F401
    except Exception:  # noqa: BLE001
        print("  [skip] 門 15 MuJoCo の柔体(mujoco が無い)")
        return
    t1 = time.time()
    res = flex_cube()
    ctx["flex"] = res
    small = [r for e, r, _ in res if e <= 0.03]
    assert len(small) >= 2
    big = [(e, r, k) for e, r, k in res if e > 0.03]
    _NUM["flex"] = [(round(e, 4), round(r, 3), round(k, 3)) for e, r, k in res]
    gate("門 15 MuJoCo の柔体(線形弾性・ν 0.3 の立方体 20 mm、摩擦なしの平板 2 枚)の小ひずみ剛性 F/(E·A·ε) = %s(ε ≤ 3 %%、0.9〜1.1 = 両模型の線形極限)"
         % [round(r, 3) for r in small], all(0.9 <= r <= 1.1 for r in small),
         "大ひずみ: %s(ε, 柔体, neo-Hookean)—— 柔体は硬くならない、%.1f s" % ([(round(e, 3), round(r, 3), round(k, 3)) for e, r, k in big], time.time() - t1))


def _flex_xml(E, H, cnt):
    sp = H / (cnt - 1)
    return f"""<mujoco>
 <option timestep="0.0002" gravity="0 0 0" solver="Newton" integrator="implicitfast" iterations="50"/>
 <worldbody>
  <geom name="floor" type="plane" size="0.1 0.1 0.01" pos="0 0 0" condim="1"/>
  <body name="platen" pos="0 0 {H + 0.0015}"><joint name="kz" type="slide" axis="0 0 1" damping="5"/>
   <geom type="box" size="0.05 0.05 0.001" mass="0.1" condim="1"/></body>
  <flexcomp name="blk" type="grid" count="{cnt} {cnt} {cnt}" spacing="{sp} {sp} {sp}" pos="0 0 {H / 2 + 0.0005}" dim="3" radius="0.0005" mass="0.02">
   <elasticity young="{E}" poisson="0.3" damping="0.0005"/>
   <contact condim="1" solref="0.003 1" selfcollide="none"/>
   <edge equality="false"/>
  </flexcomp>
 </worldbody>
 <actuator><position joint="kz" kp="5e4" kv="0"/></actuator>
</mujoco>"""


def flex_cube():
    """立方体(20 mm、7³ 頂点、E 20 kPa)を摩擦なしの床と平板で挟んで押す。ひずみは上下の面の頂点の平均高さの差(接触の食い込みを含まない)。"""
    import mujoco
    E, H, cnt = 2e4, 0.02, 7
    m = mujoco.MjModel.from_xml_string(_flex_xml(E, H, cnt))
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    v0 = d.flexvert_xpos.copy()
    top = v0[:, 2] > v0[:, 2].max() - 1e-6
    bot = v0[:, 2] < v0[:, 2].min() + 1e-6
    A, Hh = float(np.ptp(v0[:, 0]) * np.ptp(v0[:, 1])), float(np.ptp(v0[:, 2]))
    out, prev = [], 0.0
    for tgt in (0.0002 + 0.0005, 0.0004 + 0.0005, 0.0012 + 0.0005, 0.0030 + 0.0005, 0.0045 + 0.0005):    # 0.0005 = 平板と頂点の隙間
        fs_, es_ = [], []
        for i in range(8000):
            d.ctrl[0] = -(prev + (tgt - prev) * min(1.0, (i + 1) / 4000))
            mujoco.mj_step(m, d)
            if i >= 5000 and i % 300 == 0:
                f6, s = np.zeros(6), 0.0
                for c in range(d.ncon):
                    if d.contact[c].pos[2] > Hh / 2:
                        mujoco.mj_contactForce(m, d, c, f6)
                        s += f6[0]
                fs_.append(s)
                es_.append(-(d.flexvert_xpos[top, 2].mean() - d.flexvert_xpos[bot, 2].mean() - Hh) / Hh)
        assert len(fs_) >= 5
        prev = tgt
        e = float(np.mean(es_))
        out.append((e, float(np.mean(fs_)) / (E * A * e), float(TD.neohookean_cylinder_exact(e)["kappa"])))
    return out


# ----------------------------------------------------------------------------------------------------------------------
# 図
def _up(img, k):
    return np.kron(img, np.ones((k, k) + (1,) * (img.ndim - 2)))


def _gray_rgb(img, lo=0.0, hi=1.05):
    g = np.clip((img - lo) / (hi - lo), 0, 1)
    return np.stack([g, g, g], -1)


def _draw_circle(rgb, cy, cx, r, color, up=1):
    t = np.linspace(0, 2 * np.pi, int(max(64, 8 * r * up)))
    yy = np.round((cy + 0.5) * up - 0.5 + r * up * np.sin(t)).astype(int)
    xx = np.round((cx + 0.5) * up - 0.5 + r * up * np.cos(t)).astype(int)
    ok = (yy >= 0) & (yy < rgb.shape[0]) & (xx >= 0) & (xx < rgb.shape[1])
    rgb[yy[ok], xx[ok]] = color


def _spring_bed_canvas(d, lin, H=300, W=420, dmax=0.55):
    """1D のばね列の絵: 上の板から吊ったばね(長さ L − g)が平らな物(下の線)で L − δ まで縮み、幅が λ^{−1/2} 倍に広がる。色 = ひずみ。"""
    img = np.ones((H, W, 3))
    s = (H - 60) / L_DOME
    y_top, y_plane = 20, int(20 + (L_DOME - d * L_DOME) * s)
    xmax = math.sqrt(lin["g_coef"] ** -1 * L_DOME) if lin["p"] == 2 else R_DOME
    xmax = min(xmax, 1.6 * R_DOME)
    xs = W / (2.3 * xmax)
    img[y_top - 4:y_top, 10:W - 10] = (0.35, 0.35, 0.35)
    img[y_plane:y_plane + 3, 10:W - 10] = (0.15, 0.35, 0.75)
    n_sp = 15
    dx = xmax / n_sp
    sb = TD.mdr_spring_bed(max(d, 1e-4) * L_DOME, L_DOME, lin, 4000)
    aL, a = sb["a_L"], sb["a"]
    for i in range(-n_sp, n_sp + 1):
        x0 = i * dx
        g = lin["g_coef"] * abs(x0) ** lin["p"]
        if g >= L_DOME:
            continue
        ell = L_DOME - g
        if abs(x0) <= aL and d > 0:
            lam = (L_DOME - d * L_DOME) / ell
            w = lam ** -0.5
            xd = np.interp(abs(x0), sb["x"], sb["x_deformed"]) * np.sign(x0)
            strain = 1 - lam
            length = L_DOME - d * L_DOME
        else:
            w, strain, length = 1.0, 0.0, ell
            xd = x0 + np.sign(x0) * (a - aL) if d > 0 else x0
        cx = W / 2 + xd * xs
        half = max(1.0, 0.30 * dx * w * xs)
        c = min(1.0, strain / dmax)
        col = (0.2 + 0.75 * c, 0.55 - 0.35 * c, 0.85 - 0.7 * c)
        y1 = int(y_top + length * s)
        img[y_top:y1, int(cx - half):int(cx + half) + 1] = col
    return img


def figures(ctx):
    print("== 図")
    lins = ctx["lins"]
    sph = lins["sphere"]
    pitch = FOV / N_IMG
    # 1. 押し込みの GIF
    dg = np.linspace(0.0, 0.55, 23)
    dc = np.linspace(0.002, 0.6, 120)
    fwc = TD.large_deformation_contact(dc * L_DOME, L_DOME, sph)
    frames, seen_d, seen_F = [], [], []
    for d in dg:
        if d > 0:
            r = _read_image(float(d), sph)
            left = _gray_rgb(r["img"])
            _draw_circle(left, *r["rd"]["centre"], r["rd"]["a_px"], (1.0, 0.25, 0.1))
            seen_d.append(float(d))
            seen_F.append(r["inv"]["F"])
        else:
            left = _gray_rgb(TD.dome_contact_image(1e-9 + 0.3 * pitch, pitch, N_IMG, footprint=FOOT))
        left = _up(left, 2)
        mid = _spring_bed_canvas(float(d), sph, H=left.shape[0], W=360)
        series = [("Hertz F_L (small strain)", dc, fwc["F_L"]), ("large deformation F = κ F_L", dc, fwc["F"])]
        kinds, styles, colors = ["line", "line"], ["dashed", None], ["reference", "right"]
        if seen_d:
            series.append(("read from the image (radius → F)", np.array(seen_d), np.array(seen_F)))
            kinds.append("scatter")
            styles.append(None)
            colors.append("emphasis")
        right = figs.render_plot(series, xlabel="δ/L", ylabel="force F [N]", title="δ/L = %.3f%s" % (d, "  (beyond 0.5: not validated)" if d > 0.5 else ""),
                                 size=(440, left.shape[0]), xlim=(0, 0.6), ylim=(0, float(fwc["F"][-1]) * 1.05),
                                 kinds=kinds, styles=styles, colors=colors)
        frames.append(np.hstack([left, mid, np.asarray(right, np.float64)]))
    figs.save_gif("tacdome_press_sweep", frames, fps=3.0,
                  caption="半球の指先(R = L = 8 mm、μ = 0.1 MPa、仮定)を平らな物に δ/L = 0 → 0.55 押す(23 コマ)。左 = 内側カメラの接触像(192 px、"
                          "%.3f mm/px を 2 倍、赤 = 面積法で読んだ円)、中 = 1D のばね列(各ばね = 長さ L − g(x) の neo-Hookean 円柱、平らな物の線まで縮み"
                          "幅が λ^{−1/2} 倍、色 = ひずみ)、右 = 力の曲線(破線 = Hertz、実線 = 大変形、点 = 像の半径から逆算した力)。" % (pitch * 1e3))
    # 2. 3 形状の F–δ/L
    d2 = np.linspace(0.01, 0.6, 120)
    series, styles, colors = [], [], []
    for sh, col in (("sphere", "right"), ("cone", "emphasis"), ("punch", "neutral")):
        fw = TD.large_deformation_contact(d2 * L_DOME, L_DOME, lins[sh])
        series += [("%s: large deformation" % sh, d2, np.log10(fw["F"] / (MU * L_DOME ** 2))),
                   ("%s: Hertz / linear" % sh, d2, np.log10(fw["F_L"] / (MU * L_DOME ** 2)))]
        styles += [None, "dashed"]
        colors += [col, col]
    figs.save_plot("tacdome_force_three_shapes", series, xlabel="δ/L", ylabel="log10 F/(μL²)", title="Force vs compression: three profiles",
                   styles=styles, colors=colors, size=(680, 420),
                   caption="球(p = 2、n = 1.5)・円錐(p = 1、n = 2、傾き 1)・平頭の円柱(p = ∞、n = 1、半径 = L)の力(無次元、縦軸は対数)。破線 = 線形解"
                           "(球は Hertz)、実線 = 大変形 F = κₙ F_L。δ/L = 0.3 を超えると開き、平頭が最も大きく外れる(全ばねが最大ひずみ)。")
    # 3. κ⁻¹ の帯と 3 つの読み
    d3 = np.linspace(0.0, 0.95, 160)
    s3 = [("n = %g (derived)" % n, d3, 1 / TD.largedef_correction(d3, n)) for n in (1.0, 1.5, 2.0)]
    s3 += [("universal (1 − 10/9 d)", d3[d3 < 0.9], 1 - TD.UNIVERSAL_K * d3[d3 < 0.9]),
           ("memo reading 2/(1+n), n = 2", d3, 1 / TD.largedef_correction(d3, 2.0, "memo")),
           ]
    kp = 1 / TD.largedef_correction(d3, 1.5, "printed")
    keep = (kp > -0.15) & (kp < 1.35) & (d3 < 0.45)              # 活字の読みは d ≈ 0.4 で κ が 0 を横切り κ⁻¹ が発散する —— 枠の中だけ描く
    assert int(keep.sum()) >= 10
    s3.append(("printed reading, n = 1.5", d3[keep], kp[keep]))
    figs.save_plot("tacdome_kappa_band_readings", s3, xlabel="δ/L", ylabel="κ⁻¹ = F_L / F", title="Correction band and three readings of Eq. (3)",
                   styles=[None, None, None, "dashed", "dotted", "dotted"], colors=["right", "emphasis", "neutral", "reference", "wrong", "wrong"],
                   size=(680, 420), ylim=(-0.2, 1.4),
                   caption="導出した κₙ⁻¹(実線、n = 1 / 1.5 / 2)は n = 2 が上 = 論文の図 4B の挿入図と同じ並び。普遍形(破線)は n = 1 の線に沿い(d ≤ 0.5 で %.1f %% 以内)、d < %.2f では帯の少し下。点線 = 棄却した読み: "
                           "メモ 2/(1+n) は並びが逆(κ₂ > κ₁ = 定理違反)、活字 (4+2n)/(1+n) は 1 を超えて増え d ≈ 0.4 で発散(力が負へ)。"
                           % (_NUM["universal_dev"][1.0], _NUM["universal_stiffer_below"]))
    # 4. a/a_L と円柱の厳密解
    d4 = np.linspace(0.0, 0.8, 120)
    ex = TD.neohookean_cylinder_exact(np.linspace(0.05, 0.8, 12))
    figs.save_plot("tacdome_radius_ratio",
                   [("cone p = 1", d4, TD.largedef_radius_ratio(d4, 1.0)), ("sphere p = 2", d4, TD.largedef_radius_ratio(d4, 2.0)),
                    ("punch p = ∞", d4, TD.largedef_radius_ratio(d4, math.inf)),
                    ("neo-Hookean cylinder exact λ^{-1/2}", np.linspace(0.05, 0.8, 12), ex["radius_ratio"])],
                   xlabel="δ/L", ylabel="a / a_L", title="Contact radius beyond the linear solution (Eq. 4)",
                   kinds=["line", "line", "line", "scatter"], colors=["emphasis", "right", "neutral", "reference"], size=(640, 400),
                   caption="式 (4) の a/a_L(積分の形で計算、不完全ベータの形と 1e-12 で一致)。平頭は非圧縮の円柱の半径の伸び λ^{−1/2}(点 = 連続体の厳密解)に"
                           "重なる。Hertz は a/a_L = 1 の水平線で、球なら d = 0.3 で %.1f %% 小さい。" % -_NUM["hertz_sphere"]["radius_from_delta"][1])
    # 5. Hertz の誤差
    d5 = np.linspace(0.005, 0.6, 120)
    hs, hc = TD.hertz_small_strain_error(d5, 2.0), TD.hertz_small_strain_error(d5, 1.0)
    figs.save_plot("tacdome_hertz_error",
                   [("sphere: F from δ", d5, hs["force_from_delta"]), ("sphere: a from δ", d5, hs["radius_from_delta"]),
                    ("sphere: F from measured a", d5, hs["force_from_radius"]), ("cone: F from measured a", d5, hc["force_from_radius"]),
                    ("", [0.5, 0.5], [-60, 10])],
                   xlabel="δ/L", ylabel="Hertz error [%]", title="Where the small-strain Hertz fails, by observable",
                   styles=[None, None, None, "dashed", "dotted"], colors=["wrong", "neutral", "right", "emphasis", "reference"], size=(680, 420),
                   caption="小変形の Hertz を大変形に当てた誤差(寸法・弾性率に依らない)。押し込みから読む力は d = 0.3 で %.1f %%、半径は %.1f %%。"
                           "接触半径から力を読む(視触覚センサの読み方)と球は max +%.1f %%(κ と半径の伸びがほぼ打ち消す)、円錐は d = 0.5 で %.1f %%。"
                           "点線 = 論文の検証範囲の端 0.5。" % (_NUM["hertz_sphere"]["force_from_delta"][1], _NUM["hertz_sphere"]["radius_from_delta"][1],
                                                 _NUM["hertz_from_radius"]["sphere_max"], _NUM["hertz_from_radius"]["cone_05"]))
    # 6. 接触像: 全体(等倍)+ 上の縁の 12 倍(真の円・面積法・縁の画素の円の当てはめ)
    r = ctx["rows"][3]
    rd = r["rd"]
    cy, cx = rd["centre"]
    full = _gray_rgb(r["img"])
    _draw_circle(full, cy, cx, rd["a_px"], (1.0, 0.2, 0.1))
    zh, up = 8, 12
    y0, x0 = int(round(cy - rd["a_px"])) - zh, int(round(cx)) - zh
    full[y0:y0 + 2 * zh, x0] = full[y0:y0 + 2 * zh, x0 + 2 * zh - 1] = (1.0, 0.85, 0.0)      # 拡大する範囲の枠
    full[y0, x0:x0 + 2 * zh] = full[y0 + 2 * zh - 1, x0:x0 + 2 * zh] = (1.0, 0.85, 0.0)
    zoom = _up(_gray_rgb(r["img"][y0:y0 + 2 * zh, x0:x0 + 2 * zh]), up)
    ccy, ccx = r["circ"]["cy"], r["circ"]["cx"]
    _draw_circle(zoom, cy - y0, cx - x0, r["a"] / r["pitch"], (0.1, 0.8, 0.2), up)
    _draw_circle(zoom, ccy - y0, ccx - x0, r["circ"]["r"], (0.2, 0.4, 1.0), up)
    _draw_circle(zoom, cy - y0, cx - x0, rd["a_px"], (1.0, 0.2, 0.1), up)
    assert zoom.shape[0] == full.shape[0]
    figs.save("tacdome_contact_edge_crop", _up(np.hstack([full, zoom]), 2),          # 全体を最近傍で 2 倍(画素はそのまま)
              caption="左 = d = 0.3 の内側カメラの接触像(192 px、%.3f mm/px、画素を 2 倍、赤 = 面積法で読んだ円、黄 = 右の範囲)。右 = 上の縁 16 × 16 px を 24 倍"
                      "(最近傍)。緑 = 真の接触円(a = %.2f px)、赤 = 面積法(%+.3f %%、緑と重なる)、青 = 縁の画素に measure.fit_circle(%+.2f %%、"
                      "縁の画素は円の内側に乗るので約 0.5 px 小さい)。縁の灰色の画素が被覆率で、面積法はこれを線形に足す。"
                      % (r["pitch"] * 1e3, r["a"] / r["pitch"], r["err_a_pct"], r["err_circ_pct"]))
    if FULL and "flex" in ctx:
        e = np.array([x[0] for x in ctx["flex"]])
        eps = np.linspace(0.0, max(0.12, float(e.max()) * 1.1), 60)
        figs.save_plot("tacdome_flex_vs_neohookean",
                       [("neo-Hookean cylinder exact", eps, TD.neohookean_cylinder_exact(eps)["kappa"]), ("linear (Hertz-like)", eps, np.ones_like(eps)),
                        ("MuJoCo flex cube", e, np.array([x[1] for x in ctx["flex"]]))],
                       xlabel="strain ε", ylabel="F / (E A ε)", title="A linear-elastic soft body does not stiffen",
                       kinds=["line", "line", "scatter"], styles=[None, "dashed", None], colors=["right", "reference", "wrong"], size=(640, 400),
                       caption="MuJoCo の柔体(線形弾性、ν 0.3)の立方体を摩擦なしで圧縮した剛性比。小ひずみは 1(両模型の線形極限)だが、ひずみが増えても"
                               " neo-Hookean のように硬くならず、最後の押し込み(ε = %.2f)では %.2f まで落ちる(要素がつぶれる)—— 大変形の真値には使えない(門 15 は小ひずみだけ)。"
                               % (ctx["flex"][-1][0], ctx["flex"][-1][1]))
    print("  figures:", figs.errors() or "ok")


def main() -> int:
    t_all = time.time()
    ctx = numpy_part()
    t_def = time.time() - t_all
    if FULL:
        full_part(ctx)
    if figs.enabled():
        figures(ctx)
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    n_ng = sum(1 for _, ok in _GATES if not ok)
    print("numbers:", _NUM)
    print("gates: %d / %d ok  (既定の門 %.1f s、全体 %.1f s)" % (len(_GATES) - n_ng, len(_GATES), t_def, time.time() - t_all))
    if n_ng or figs.errors():
        print("FAIL")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
