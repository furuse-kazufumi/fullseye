# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""視触覚センサのマーカー配列からせん断場・固着/滑り・接線力を読む —— Cattaneo–Mindlin の閉形式と有限要素の節点変位を門に(2026-10-04)。

物理シミュ × Fullseye 系列の第 2 弾の第 2 本(第 1 本 = poc_tacsim_elastic_membrane、法線荷重)。外から来るものは 2 系統:
  * **閉形式**(Johnson, *Contact Mechanics*, CUP 1985): Cattaneo–Mindlin の部分滑り(§7.2: c/a = (1 − Q/μP)^{1/3}、q = q′ − q″、
    δx = 3μP(2−ν)/(16Ga)[1 − (1−Q/μP)^{2/3}]、kt = 8Ga/(2−ν)、固着円内の表面変位は一様)、Hertz 形接線トラクションの円内解(式 3.91)、
    法線荷重の半径変位(式 3.41b)、接線点荷重の半空間解 = Cerruti(式 3.22)。
  * **有限要素の節点変位**(Robo-Touch/Taxim リポジトリ同梱、MIT ライセンス、環境変数 FULLSEYE_TAXIM_DATA の下、無ければ [skip]): 有限厚の
    ドーム状ゲルで半空間がどこで外れるかを数に。
  公表の定性値(Yuan, Dong, Adelson, Sensors 2017): 滑りは周縁から、変位ヒストグラムのエントロピーは部分滑りで増える。
自分で作ったのは 3 つ: 接触円の外側と滑り環の接線変位(閉形式が無い)を Cerruti 核の画素平均核で FFT 畳み込み、任意の固着半径の場を
相似則 g(x) − (c/a)²g(x·a/c) で出す逆算模型(畳み込み 1 回)、マーカー像の合成(変位で中心を移してから描く、補間しない)。
被験者 = 既存 op: blob2d.blob_label / blob_features(重心)、pivops.piv_cross_correlate(窓相関、第 2 実装)、backends_subpix の副画素極値、
backends_tactile.tac_shear_field(別被験者)、measure.fit_circle、tacsim の Hertz と膜の合成。新モジュール tacslip 20 op。

門(numpy、18 本は常に、FEM の 2 本はデータがあるとき): 閉形式の自己検算(∫q dA = Q、c/a、kt、計画書の錨 70.5 µm)、ūr の最大は 0.93a、
Cerruti 畳み込み vs 式 3.91(0.02 %)、固着円の一様性(0.006 %)、遠方 1/r、マーカー重心の往復(重み 0.003 px・二値 0.16 px・副画素極値)、
法線荷重だけでは 0.19 px、追跡 RMS 0.01 px(Q/μP 0.25〜0.9、961/961)、PIV の格子エイリアス(5 → −3 px)と探索を絞った一致、逆算 Q/μP 0.03・
c/a 0.02・μ と Q の分離(低 Q で μ は 2c/(1−c²) 倍に増幅)、模型なしの固着半径はピッチの分解能、全滑りで核が消える、指数 1/3、エントロピー
の単調性、tac_shear_field は固着/滑りを分けない、壊れる場所(密度・雑音)、FEM の r½ = 2.3 mm と Cerruti の角度依存(ν 0.49〜0.51)。
図(FULLSEYE_FIGURE_DIR があるとき 7 枚): 基準/荷重後/追跡ベクトル、固着円が縮む GIF、q(r)、δx–Q、エントロピー、FEM vs 半空間、壊れる場所。
正直に: 半空間・小変形・剛体球・Coulomb・準静的、μ は低 Q で決まりにくい、FEM は点荷重状で荷重不明(形の比較だけ)、相関と最近傍は
|u| ≥ ピッチ/2 を測れない(対応は視野の縁が遠方場という前提に依る)。
Run: py -3.11 examples/poc_tacsim_marker_shear.py           (FULLSEYE_TAXIM_DATA=<FEM 節点ファイルの親> で FEM の 2 門も)
"""
from __future__ import annotations

import math
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import blob2d  # noqa: E402,F401  (被験者: tacslip.marker_detect の中で使う)
import examplefig as figs  # noqa: E402
import imagedraw  # noqa: E402
import measure as FM  # noqa: E402
import pivops  # noqa: E402
import tacsim as T  # noqa: E402
import tacslip as S  # noqa: E402

try:
    import backends_subpix as SP  # noqa: E402
except Exception:  # noqa: BLE001
    SP = None
try:
    import backends_tactile as TAC  # noqa: E402
except Exception:  # noqa: BLE001
    TAC = None

# 寸法(分解能の罠を先に潰す): a = 2.05 mm = 32.9 px、接触円内にマーカー 53 個、全滑り δx = 8.2 px ≈ ピッチ(最悪の組、正直に)
E_GEL, NU, R_BALL, P_LOAD, MU = 0.2e6, 0.48, 6.0e-3, 0.5, 0.5       # μ 0.5 は仮定(計画書の錨 R 3 mm・0.08 N・Q/μP 0.5 → δx 70.5 µm を再現する値)
N_PX, FOV = 256, 16.0e-3
PITCH = FOV / N_PX
G_GEL = E_GEL / (2.0 * (1.0 + NU))
MARK_PITCH_M, MARK_R_PX, MARK_DARK = 0.5e-3, 2.5, 0.85             # 半径は測って決めた(pixel-locking: 2.0 px で ±0.030、2.5 px で ±0.018 → ガウス重みで 0.006)
AMB, ELEV = 0.03, 55.0
_GATES: list[tuple[str, bool]] = []
_trapz = getattr(np, "trapezoid", None) or np.trapz


def gate(name, ok, detail=""):
    _GATES.append((name, bool(ok)))
    print("  [%s] %s %s" % ("ok" if ok else "NG", name, detail))


def skip(name, why):
    print("  [skip] %s —— %s" % (name, why))


def _raises(fn):
    try:
        fn()
    except ValueError:
        return True
    return False


def centre_px():
    return (N_PX - 1) / 2.0


def match_to_truth(det, truth, tol=1.5):
    from scipy.spatial import cKDTree
    d, i = cKDTree(det).query(truth, distance_upper_bound=tol)
    ok = np.isfinite(d)
    return det[i[ok]] - truth[ok], ok


class Scene:
    """P 固定・Q 可変の 1 場面: 基準像(P のみ)と荷重後(P + Q)。"""

    def __init__(self, ctx, Q, pitch_px=None, noise=0.0, seed=0, offset=(0.3, 0.6)):
        hz, X, Y, kern = ctx["hz"], ctx["X"], ctx["Y"], ctx["kern"]
        self.mp = S.mindlin_partial_slip(Q, hz, MU, G_GEL, NU)
        self.field = S.membrane_shear_field(hz, self.mp, X, Y, kern)
        self.pitch_px = pitch_px if pitch_px is not None else MARK_PITCH_M / PITCH
        pts = S.membrane_markers(N_PX, self.pitch_px, offset[0], offset[1])
        self.pts_flat = pts
        self.pts_ref = S.displace_markers(pts, self.field["urx"], self.field["ury"], PITCH)
        self.pts_cur = S.displace_markers(pts, self.field["urx"] + self.field["ux"], self.field["ury"] + self.field["uy"], PITCH)
        bg = ctx["bg_rgb"]
        self.rgb_ref = S.membrane_render_markers(bg, self.pts_ref, MARK_R_PX, MARK_DARK)
        self.rgb_cur = S.membrane_render_markers(bg, self.pts_cur, MARK_R_PX, MARK_DARK)
        if noise > 0:
            rng = np.random.default_rng(seed)
            self.rgb_ref = self.rgb_ref + rng.normal(0, noise, self.rgb_ref.shape)
            self.rgb_cur = self.rgb_cur + rng.normal(0, noise, self.rgb_cur.shape)
        self.m_ref = S.marker_image(self.rgb_ref, bg)
        self.m_cur = S.marker_image(self.rgb_cur, bg)

    def track(self, piv=False):
        return S.marker_track(self.m_ref, self.m_cur, MARK_DARK, self.pitch_px, MARK_R_PX, piv=piv)

    def true_u_px(self, p0):
        return np.column_stack([S._sample(self.field["ux"], p0), S._sample(self.field["uy"], p0)]) / PITCH


def numpy_part():
    t0 = time.time()
    print("既存 op の再利用: blob2d.blob_label / blob_features、pivops.piv_cross_correlate、backends_subpix.sp_local_max_sub_pix、"
          "backends_tactile.tac_shear_field、measure.fit_circle、tacsim.hertz_sphere / membrane_indent_sphere / membrane_lights / membrane_render_rgb")
    print("== 門(閉形式・畳み込み・合成・被験者・破れ)")
    Es = T.combined_modulus(E_GEL, NU)
    hz = T.hertz_sphere(P_LOAD, R_BALL, Es)
    a, p0 = hz["a"], hz["p0"]
    muP = MU * P_LOAD
    mps = {q: S.mindlin_partial_slip(q * muP, hz, MU, G_GEL, NU) for q in (0.25, 0.5, 0.75, 1.0)}
    rr = np.linspace(0, a, 40001)
    ints = {q: 2 * math.pi * _trapz(S.mindlin_traction(rr, mp) * rr, rr) for q, mp in mps.items()}
    err_int = max(abs(ints[q] - q * muP) / (q * muP) for q in ints)
    mp5 = mps[0.5]
    r_slip = np.linspace(mp5["c"] * 1.001, a * 0.999, 500)
    r_stick = np.linspace(0, mp5["c"] * 0.999, 500)
    coulomb = np.max(np.abs(S.mindlin_traction(r_slip, mp5) - MU * T.hertz_pressure(r_slip, a, p0))) / (MU * p0)
    below = np.all(S.mindlin_traction(r_stick, mp5) < MU * T.hertz_pressure(r_stick, a, p0))
    gate("門 1 トラクションの面積分 ∫q dA = Q(Q/μP = 0.25/0.5/0.75/1、< 0.1 %)、滑り環 c < r < a で q = μp(r)(Coulomb の限界、1e-9)、固着円内で q < μp",
         err_int < 1e-3 and coulomb < 1e-9 and below,
         "最大 %.2e、環の差 %.1e; a = %.3f mm = %.1f px、p0 = %.1f kPa、G = %.1f kPa" % (err_int, coulomb, a * 1e3, a / PITCH, p0 * 1e-3, G_GEL * 1e-3))
    qs = np.linspace(0, 1, 101)
    cas = np.array([S.mindlin_partial_slip(q * muP, hz, MU, G_GEL, NU)["c_over_a"] for q in qs])
    full = mps[1.0]
    over = S.mindlin_partial_slip(1.2 * muP, hz, MU, G_GEL, NU)
    gate("門 2 固着円 c/a = (1 − Q/μP)^{1/3}: Q で単調減少、Q/μP = 0.5 で 0.7937、Q = μP で c = 0(全滑り、slipping=True)、Q > μP も例外でなく "
         "slipping 印(fail-closed は Q < 0 と μ ≤ 0 だけ ValueError)",
         np.all(np.diff(cas) < 0) and abs(mps[0.5]["c_over_a"] - 0.5 ** (1 / 3)) < 1e-12 and full["c"] == 0.0 and full["slipping"]
         and over["slipping"] and over["c"] == 0.0 and _raises(lambda: S.mindlin_partial_slip(-0.1, hz, MU, G_GEL, NU))
         and _raises(lambda: S.mindlin_partial_slip(0.1, hz, 0.0, G_GEL, NU)), "c/a(0.5) = %.4f" % mps[0.5]["c_over_a"])
    hq = 1e-7 * muP
    slope0 = S.mindlin_partial_slip(hq, hz, MU, G_GEL, NU)["delta_x"] / hq
    dx_full = full["delta_x"]
    dx3 = S.mindlin_partial_slip(0.5 * 0.5 * 0.08, T.hertz_sphere(0.08, 3.0e-3, Es), 0.5, G_GEL, NU)["delta_x"]
    gate("門 3 接線変位 δx = 3μP(2−ν)/(16Ga)[1 − (1−Q/μP)^{2/3}]: Q → 0 の傾き = 1/kt = (2−ν)/(8Ga)(1e-6)、Q = μP で δx = 3μP(2−ν)/(16Ga)、"
         "計画書の錨(R 3 mm・0.08 N・μ 0.5・Q/μP 0.5)で 70.5 µm",
         abs(slope0 * full["k_t"] - 1.0) < 1e-6 and abs(dx_full - 3 * muP * (2 - NU) / (16 * G_GEL * a)) < 1e-15 and abs(dx3 * 1e6 - 70.5) < 0.1,
         "kt = %.1f N/m、全滑り δx = %.1f µm = %.2f px、錨 %.1f µm" % (full["k_t"], dx_full * 1e6, dx_full / PITCH, dx3 * 1e6))
    ratio_f = lambda nu: 2 * (1 - 2 * nu) / (3 * math.pi * (1 - nu))      # noqa: E731  ūr(a)/δ の閉形式(導出)
    ur_a = S.hertz_surface_ur(np.array([a]), a, p0, G_GEL, NU)[0]
    ur_out = S.hertz_surface_ur(np.array([3 * a]), a, p0, G_GEL, NU)[0]
    point = -(1 - 2 * NU) * P_LOAD / (4 * math.pi * G_GEL * 3 * a)
    gate("門 4 法線荷重の半径変位(Johnson 3.41b): ūr(a)/δ = 2(1−2ν)/(3π(1−ν)) = %.2f %% (ν 0.48)、ν 0.3 なら %.1f %%、外側は点荷重 "
         "−(1−2ν)P/(4πGr) に一致(1e-12)、中心向き(負)" % (100 * ratio_f(NU), 100 * ratio_f(0.3)),
         abs(abs(ur_a) / hz["delta"] - ratio_f(NU)) < 1e-12 and abs(ur_out - point) < 1e-12 * abs(point) and ur_a < 0,
         "ūr(a) = %.1f µm = %.2f px(δ = %.0f µm、全滑り δx の %.1f %%)" % (ur_a * 1e6, ur_a / PITCH, hz["delta"] * 1e6, 100 * abs(ur_a) / dx_full))
    X, Y, r, _ = T._grid(N_PX, FOV)
    kern = S.cerruti_kernel(N_PX, PITCH, G_GEL, NU)
    q0 = MU * p0
    uH = S.cerruti_surface_displacement(np.where(r < a, q0 * np.sqrt(np.maximum(0, 1 - (r / a) ** 2)), 0.0), kern)
    cf = S.hertzian_tangential_inner(X, Y, q0, a, G_GEL, NU)
    inner = r < 0.9 * a
    ux0 = math.pi * q0 / (32.0 * G_GEL * a) * 4.0 * (2.0 - NU) * a * a
    e_x = float(np.sqrt(np.mean((uH["ux"] - cf["ux"])[inner] ** 2)) / ux0)
    e_y = float(np.sqrt(np.mean((uH["uy"] - cf["uy"])[inner] ** 2)) / np.abs(cf["uy"][inner]).max())
    gate("門 5 Cerruti 核の FFT 畳み込み(画素平均核、中心は解析積分)vs Johnson 3.91 の閉形式: Hertz 形トラクション 1 個の円内 r < 0.9a で ūx の RMS "
         "< 1 %%、ūy(2νxy 項)の RMS < 2 %%(ūx は円内で %.0f %% 変わる非一様な場なので核の形まで試している)" % (100 * np.ptp(cf["ux"][inner]) / ux0),
         e_x < 0.01 and e_y < 0.02, "ūx %.3f %%, ūy %.2f %%、%.1f s" % (100 * e_x, 100 * e_y, time.time() - t0))
    fld = S.membrane_shear_field(hz, mp5, X, Y, kern)
    core = r <= 0.9 * mp5["c"]
    uni = float(fld["ux"][core].std() / mp5["delta_x"]); bias = float(fld["ux"][core].mean() / mp5["delta_x"] - 1)
    uy_core = float(np.abs(fld["uy"][core]).max() / mp5["delta_x"])
    gate("門 6 Mindlin の一様性(2 つの Hertz 形トラクションの x², y² 項が打ち消す): 畳み込んだ場は固着円 r ≤ 0.9c で std/δx < 1 %、平均が閉形式 δx と "
         "1 % 以内、ūy は δx の 1 % 未満", uni < 0.01 and abs(bias) < 0.01 and uy_core < 0.01,
         "std %.3f %%, 平均 %+.3f %%, |ūy| %.3f %%" % (100 * uni, 100 * bias, 100 * uy_core))
    far = {}
    for k in (3.0, 3.5):
        band = np.abs(r - k * a) < 0.5 * PITCH
        far[k] = float((fld["ux"][band] * r[band]).mean() / (mp5["Q"] * (2 - NU) / (4 * math.pi * G_GEL)))
    gate("門 7 遠方場: 方位平均の ūx·r が点荷重の Q(2−ν)/(4πG) に r = 3a・3.5a で 5 % 以内(有限分布の補正 O((a/r)²) 込み)、3.5a の方が 3a より点荷重に近い",
         all(abs(v - 1) < 0.05 for v in far.values()) and abs(far[3.5] - 1) < abs(far[3.0] - 1),
         "3a: %.3f、3.5a: %.3f(視野 = %.1f a、零詰め 2n で巻き込みなし)" % (far[3.0], far[3.5], FOV / a))
    # --- 合成と被験者 ---
    lights = T.membrane_lights(ELEV)
    gh = T.membrane_indent_sphere(hz, N_PX, FOV)
    bg_rgb = T.membrane_render_rgb(gh["normals"], lights, ambient=AMB)
    ctx = {"hz": hz, "X": X, "Y": Y, "kern": kern, "bg_rgb": bg_rgb, "lights": lights, "gh": gh, "Es": Es}
    model = S.mindlin_model(hz, X, Y, kern, G_GEL, NU)
    ctx["model"] = model
    pitch_px = MARK_PITCH_M / PITCH
    sc0 = Scene(ctx, 0.0)
    m_flat = S.marker_image(S.membrane_render_markers(bg_rgb, sc0.pts_flat, MARK_R_PX, MARK_DARK), bg_rgb)
    det = S.marker_detect(m_flat, MARK_DARK, MARK_R_PX, binary=True)
    inside_img = (sc0.pts_flat[:, 0] > 4) & (sc0.pts_flat[:, 0] < N_PX - 5) & (sc0.pts_flat[:, 1] > 4) & (sc0.pts_flat[:, 1] < N_PX - 5)
    truth = sc0.pts_flat[inside_img]
    d_bin, okb = match_to_truth(det["binary"], truth)
    d_w, okw = match_to_truth(det["weighted"], truth)
    d_wp, _ = match_to_truth(det["weighted_plain"], truth)
    rms_b = float(np.sqrt(np.mean(d_bin ** 2))); rms_w = float(np.sqrt(np.mean(d_w ** 2))); rms_wp = float(np.sqrt(np.mean(d_wp ** 2)))
    bias_w = float(np.hypot(*d_w.mean(0))); bias_wp = float(np.hypot(*d_wp.mean(0)))
    n_in_a = int((np.hypot(truth[:, 0] - centre_px(), truth[:, 1] - centre_px()) * PITCH < a).sum())
    sp_txt, sp_ok = "backends_subpix なし", True
    if SP is not None:
        pts_sp = SP.sp_local_max_sub_pix(m_flat, 0.3, 0.0)
        c_sp = np.array([[c[0, 1], c[0, 0]] for c in pts_sp["cs"]], np.float64).reshape(-1, 2)
        d_sp, oks = match_to_truth(c_sp, truth)
        rms_sp = float(np.sqrt(np.mean(d_sp ** 2))) if len(d_sp) else float("nan")
        sp_ok = oks.mean() > 0.95 and rms_sp < 0.5
        sp_txt = "副画素極値(backends_subpix、平らな頂の 2 次曲面当て)%.3f px・検出率 %.2f" % (rms_sp, oks.mean())
    gate("門 8 マーカー重心の往復(無荷重、真値中心 vs 検出): blob2d.blob_features の二値重心は RMS < 0.2 px(実測 0.16)、m を重みにした重心は < 0.03 px、"
         "反復ガウス重み(σ = 半径)で精密化すると格子共通の系統バイアス(pixel-locking)が半分以下、backends_subpix の副画素極値は平らな頂で "
         "< 0.5 px(第 3 の被験者、頂が平らな円盤には向かない)、全マーカー検出(欠け・偽なし)",
         rms_b < 0.2 and rms_w < 0.03 and bias_w < 0.5 * max(bias_wp, 1e-9) and okb.all() and okw.all() and len(det["weighted"]) == len(truth) and sp_ok,
         "二値 %.3f px、重み %.4f px(素 %.4f)、共通バイアス %.4f px(素 %.4f)、%s、%d 個(接触円内 %d 個、ピッチ %.0f px、半径 %.1f px)"
         % (rms_b, rms_w, rms_wp, bias_w, bias_wp, sp_txt, len(truth), n_in_a, pitch_px, MARK_R_PX))
    mv = np.hypot(*(sc0.pts_ref - sc0.pts_flat).T)
    rf = np.linspace(0.5 * a, 1.5 * a, 20001)
    urf = np.abs(S.hertz_surface_ur(rf, a, p0, G_GEL, NU))
    ur_max, r_at_max = float(urf.max()), float(rf[np.argmax(urf)])
    gate("門 9 法線荷重だけ(P = 0.5 N、ν 0.48)のマーカー移動は最大 %.3f px で閉形式 |ūr| の最大(r = %.3fa、ūr(a) の %.3f 倍 —— 最大は縁でなく少し内側、"
         "試作で思い込みを 1 つ直した)を超えず(0.1 %% 以内)、全滑り δx の 3 %% 未満 —— 「マーカーの動き ≈ せん断」の根拠(ν 0.3 なら %.0f %% で成り立たない)"
         % (mv.max(), r_at_max / a, ur_max / abs(ur_a), 100 * ratio_f(0.3) * hz["delta"] / dx_full),
         mv.max() * PITCH <= ur_max * (1 + 1e-3) and mv.max() * PITCH > 0.95 * ur_max and mv.max() * PITCH < 0.03 * dx_full,
         "最大 %.4f px vs 閉形式 %.4f px" % (mv.max(), ur_max / PITCH))
    rows = []
    for qr in (0.25, 0.5, 0.75, 0.9):
        sc = Scene(ctx, qr * muP)
        tr = sc.track(piv=True)
        ut = sc.true_u_px(tr["p0"])
        err = tr["u"] - ut
        p0c = tr["p0"] - centre_px()
        rpx = np.hypot(p0c[:, 0], p0c[:, 1])
        core_m = rpx * PITCH < 0.8 * sc.mp["c"]
        piv_at = tr["piv_at"]
        piv_u = piv_at(tr["p0"])
        fit = S.mindlin_fit(model, tr["p0"], tr["u"] * PITCH)
        mf = S.stick_radius_modelfree(p0c, tr["u"])
        rows.append({"qr": qr, "sc": sc, "tr": tr, "rms": float(np.sqrt(np.mean(err ** 2))), "max": float(np.abs(err).max()),
                     "piv_core": float(np.sqrt(np.mean((piv_u - tr["u"])[core_m] ** 2))) if core_m.any() else float("nan"),
                     "fit": fit, "c_mf_px": mf["c_px"], "core_u": mf["core_px"], "matched": tr["matched"], "n0": tr["n0"], "n1": tr["n1"]})
    gate("門 10 マーカー追跡(重み重心 + 縁から伸ばす連続性の対応)vs 真値の変位: Q/μP = 0.25〜0.9 で RMS < 0.05 px、最大 < 0.15 px、対応は全マーカー"
         "(欠け 0、ピッチ 1 つ飛びなし)",
         all(r_["rms"] < 0.05 and r_["max"] < 0.15 and r_["matched"] == min(r_["n0"], r_["n1"]) for r_ in rows),
         "RMS %s px、最大 %s px、対応 %s" % ([round(r_["rms"], 4) for r_ in rows], [round(r_["max"], 3) for r_ in rows], [r_["matched"] for r_ in rows]))
    pts_l = sc0.pts_flat
    m_a = S.marker_image(S.membrane_render_markers(bg_rgb, pts_l, MARK_R_PX, MARK_DARK), bg_rgb)
    alias = {}
    for dxs in (3.0, 5.0):
        m_b = S.marker_image(S.membrane_render_markers(bg_rgb, pts_l + np.array([dxs, 0.0]), MARK_R_PX, MARK_DARK), bg_rgb)
        fl_, _ = pivops.piv_cross_correlate(m_a, m_b, window=32, overlap=0.5)
        alias[dxs] = float(np.nanmedian(np.asarray(fl_)[1]))
    pts_j = pts_l + np.random.default_rng(0).uniform(-1.5, 1.5, pts_l.shape)
    m_ja = S.marker_image(S.membrane_render_markers(bg_rgb, pts_j, MARK_R_PX, MARK_DARK), bg_rgb)
    m_jb = S.marker_image(S.membrane_render_markers(bg_rgb, pts_j + np.array([5.0, 0.0]), MARK_R_PX, MARK_DARK), bg_rgb)
    fl_, _ = pivops.piv_cross_correlate(m_ja, m_jb, window=32, overlap=0.5)
    alias["jitter5"] = float(np.nanmedian(np.asarray(fl_)[1]))
    gate("門 11 第 2 実装 pivops.piv_cross_correlate(単段 32 px 窓)と規則格子の罠: 8 px 格子を 3 px ずらすと 3.000、5 px ずらすと −3.000(= 5 − 8、格子周期の"
         "エイリアス)、±1.5 px のジッタ格子なら 5.000 —— |u| がピッチ/2 を超えると相関も最近傍も隣のマーカーに飛ぶ。探索を ±3.8 px(0.12 窓 < ピッチ/2)に絞った "
         "PIV は固着円 r < 0.8c で Q/μP ≤ 0.5(|u| ≤ 3.0 px)ならマーカー追跡と 0.1 px 以内、0.75 以上(|u| ≥ 5 px)は探索の外で u − 8 に飛ぶ(> 4 px)",
         abs(alias[3.0] - 3.0) < 0.01 and abs(alias[5.0] + 3.0) < 0.01 and abs(alias["jitter5"] - 5.0) < 0.01
         and all(r_["piv_core"] < 0.1 for r_ in rows[:2]) and all(r_["piv_core"] > 4.0 for r_ in rows[2:]),
         "平行移動 3→%.3f、5→%.3f、ジッタ 5→%.3f; 固着円の差 %s px" % (alias[3.0], alias[5.0], alias["jitter5"], [round(r_["piv_core"], 3) for r_ in rows]))
    e_q = [abs(r_["fit"]["q_ratio"] - r_["qr"]) for r_ in rows]
    e_c = [abs(r_["fit"]["c_over_a"] - r_["sc"].mp["c_over_a"]) for r_ in rows]
    e_mu = [abs(r_["fit"]["mu"] / MU - 1) for r_ in rows]
    e_Q = [abs(r_["fit"]["Q"] / r_["sc"].mp["Q"] - 1) for r_ in rows]
    amp = [2 * r_["sc"].mp["c_over_a"] / (1 - r_["sc"].mp["c_over_a"] ** 2) for r_ in rows]
    gate("門 12 逆算(c/a を走査し μP を線形最小二乗、全マーカー、相似則の模型): Q/μP = 0.25〜0.9 で Q/μP の誤差 < 0.03、c/a < 0.02、Q < 5 %%; G・ν・a が既知なら"
         "振幅から μP も決まり **μ と Q が別々に**出る —— ただし μ は c/a の誤差が 2c/(1−c²) 倍(%s 倍)に増幅されるので低 Q ほど悪く、Q/μP で単調に改善して "
         "0.75 以上で 3 %% 以内(c は Q/μP だけで、δx = 3μP(2−ν)(1−c²/a²)/(16Ga) が μP を与える; 滑り環が狭いと μ は決まりにくい)" % [round(v, 1) for v in amp],
         max(e_q) < 0.03 and max(e_c) < 0.02 and max(e_Q) < 0.05 and all(e_mu[i] >= e_mu[i + 1] for i in range(len(e_mu) - 1)) and max(e_mu[2:]) < 0.03,
         "Q/μP 誤差 %s、c/a 誤差 %s、μ 誤差 %s %%、Q 誤差 %s %%" % ([round(v, 4) for v in e_q], [round(v, 4) for v in e_c],
                                                                [round(100 * v, 2) for v in e_mu], [round(100 * v, 2) for v in e_Q]))
    e_mf = [abs(r_["c_mf_px"] * PITCH - r_["sc"].mp["c"]) / PITCH for r_ in rows[:3]]
    gate("門 13 模型なしの固着半径(内側 6 点の中央値から |ux − δ̂| が 8 %% + 0.05 px を超える最初の半径)は閉形式 c とマーカー 1 ピッチ(%.0f px)以内 —— "
         "分解能はマーカー間隔で決まる(模型を使う経路は c/a 0.02 = %.1f px)" % (pitch_px, 0.02 * a / PITCH),
         max(e_mf) < pitch_px, "誤差 %s px、δ̂ %s px(閉形式 %s px)" % ([round(v, 2) for v in e_mf], [round(r_["core_u"], 3) for r_ in rows[:3]],
                                                                  [round(r_["sc"].mp["delta_x"] / PITCH, 3) for r_ in rows[:3]]))
    scF = Scene(ctx, muP)
    trF = scF.track()
    rpxF = np.hypot(*(trF["p0"] - centre_px()).T) * PITCH
    fitF = S.mindlin_fit(model, trF["p0"], trF["u"] * PITCH)
    inner_u = trF["u"][rpxF < 0.8 * a, 0]
    spread = float(np.ptp(inner_u) / np.median(inner_u))
    gate("門 14 Q = μP(全滑り): 逆算は c/a < 0.05・Q/μP > 0.99 を返し、接触円内の変位は一様でなく Johnson 3.91 の二次曲面(r < 0.8a で最大−最小が中央値の "
         "20 % 超)—— 一様な核が消えた瞬間が全滑りの印", fitF["c_over_a"] < 0.05 and fitF["q_ratio"] > 0.99 and spread > 0.2,
         "c/a %.3f、Q/μP %.4f、ばらつき %.0f %%" % (fitF["c_over_a"], fitF["q_ratio"], 100 * spread))
    sweep = []
    for qr in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95):
        sc = Scene(ctx, qr * muP)
        tr = sc.track()
        rpx = np.hypot(*(tr["p0"] - centre_px()).T) * PITCH
        fit = S.mindlin_fit(model, tr["p0"], tr["u"] * PITCH)
        mag = np.hypot(*tr["u"].T)[rpx <= a]
        core_sel = rpx < 0.3 * sc.mp["c"]
        sweep.append({"qr": qr, "fit": fit, "ent_abs": S.slip_entropy(mag, vmax=dx_full / PITCH), "ent_rel": S.slip_entropy(mag), "sc": sc, "tr": tr,
                      "dx_meas": float(np.median(tr["u"][core_sel, 0])) if core_sel.any() else float("nan")})
    one_minus = np.array([1 - s["qr"] for s in sweep]); ca_fit = np.array([s["fit"]["c_over_a"] for s in sweep])
    expo = float(np.polyfit(np.log(one_minus), np.log(ca_fit), 1)[0])
    gate("門 15 固着円の縮み: 画像から当てた c/a の log-log 傾き(vs 1 − Q/μP、10 点 0.1〜0.95)が閉形式の指数 1/3 と 0.02 以内(c/a → 1 の端で log が誤差を"
         "増幅するので 0.01 は無理、実測 0.34)", abs(expo - 1 / 3) < 0.02, "指数 %.4f" % expo)
    ea = np.array([s["ent_abs"] for s in sweep]); er = np.array([s["ent_rel"] for s in sweep])
    gate("門 16 滑りの指標(Yuan 2017): 接触円内の |u| ヒストグラムのエントロピー(16 ビン、全滑り δx を上限に固定)が Q/μP で単調非減少(53 個のマーカーでは"
         "同値の段がつく)、0.95 で 0.1 の 5 倍超; ビン幅を場ごとの最大に合わせた「形だけ」のエントロピーは 0.5 以降は単調増加(固着核が縮み滑り環の勾配に乗る"
         "マーカーが増える; 小さい Q では外側の尾の相対分布が支配)",
         np.all(np.diff(ea) >= 0) and ea[-1] > 5 * ea[0] and np.all(np.diff(er[4:]) > 0),
         "絶対 %s、形 %s" % ([round(float(v), 3) for v in ea], [round(float(v), 3) for v in er]))
    tac_row = None
    if TAC is not None:
        sc = rows[1]["sc"]
        gray = sc.rgb_cur.mean(-1); gray = (gray - gray.min()) / (np.ptp(gray) + 1e-12)
        coh = TAC.tac_shear_field(gray, 0.5, 0.5)
        fl_m = sc.field
        c_stick = float(coh[fl_m["mask_stick"]].mean()); c_slip = float(coh[fl_m["mask_slip"]].mean()); c_out = float(coh[r > 1.5 * a].mean())
        gray0 = sc.rgb_ref.mean(-1); gray0 = (gray0 - gray0.min()) / (np.ptp(gray0) + 1e-12)
        coh0 = TAC.tac_shear_field(gray0, 0.5, 0.5)
        d_slip = float(abs(coh[fl_m["mask_slip"]].mean() - coh0[fl_m["mask_slip"]].mean()))
        tac_row = {"stick": c_stick, "slip": c_slip, "out": c_out, "d_slip": d_slip}
        gate("門 17 別被験者 tac_shear_field(単画像の構造テンソルのコヒーレンス)は滑り環と固着円を分けない: 環と核の平均の差が 0.05 未満、せん断なしの基準像との差も "
             "0.05 未満(1 枚の像の向きの揃い方は、2 枚の差 = 変位を見ないと滑りに結びつかない)",
             abs(c_slip - c_stick) < 0.05 and d_slip < 0.05, "核 %.3f、環 %.3f、外 %.3f、基準像との差 %.3f" % (c_stick, c_slip, c_out, d_slip))
    else:
        skip("門 17 tac_shear_field", "backends_tactile が import できない")
    breaks = []
    for pp, nz in ((8.0, 0.0), (12.0, 0.0), (16.0, 0.0), (8.0, 0.02), (8.0, 0.05)):
        sc = Scene(ctx, 0.5 * muP, pitch_px=pp, noise=nz, seed=3)
        tr = sc.track()
        p0c = tr["p0"] - centre_px()
        fit = S.mindlin_fit(model, tr["p0"], tr["u"] * PITCH)
        ut = sc.true_u_px(tr["p0"])
        breaks.append({"pitch": pp, "noise": nz, "n_in": int((np.hypot(p0c[:, 0], p0c[:, 1]) * PITCH < a).sum()), "e_q": abs(fit["q_ratio"] - 0.5),
                       "e_c": abs(fit["c_over_a"] - mps[0.5]["c_over_a"]), "rms": float(np.sqrt(np.mean((tr["u"] - ut) ** 2))), "matched": tr["matched"]})
    gate("門 18 壊れる場所: マーカー間隔 8 → 12 → 16 px(接触円内 %s 個)でも Q/μP の誤差は 0.05 以内だが単調ではない(効くのはマーカーの数でなく固着縁 c に対する"
         "マーカーの位置、量子化)、画素雑音 σ 0.02 / 0.05 で追跡 RMS は単調に増える(ガウス重みの重心は素の重心の 0.54 px より 17 倍雑音に強い)が Q/μP は "
         "0.05 以内(全マーカーで当てる)" % ([b["n_in"] for b in breaks[:3]]),
         all(b["e_q"] < 0.05 for b in breaks) and breaks[0]["rms"] < breaks[3]["rms"] < breaks[4]["rms"],
         "c/a 誤差 %s、Q/μP 誤差 %s、RMS %s px" % ([round(b["e_c"], 4) for b in breaks], [round(b["e_q"], 4) for b in breaks], [round(b["rms"], 3) for b in breaks]))
    print("  (numpy 部 %.1f s)" % (time.time() - t0))
    ctx.update({"rows": rows, "sweep": sweep, "breaks": breaks, "tac": tac_row, "mps": mps, "full": full, "dx_full": dx_full, "pts_flat": sc0.pts_flat})
    return ctx


def fem_part(ctx):
    print("== 有限要素の節点変位(第 2 真値、FULLSEYE_TAXIM_DATA)")
    root = os.environ.get("FULLSEYE_TAXIM_DATA", "").strip()
    ctx["fem"] = None
    if not root:
        skip("門 19/20 FEM", "FULLSEYE_TAXIM_DATA が未設定(配布物同梱の FEM 節点ファイルを取得し、その親ディレクトリを指す。手順はモジュールの docstring)")
        return ctx
    try:
        t0 = time.time()
        fz = S.fem_nodes_load(os.path.join(root, "calibs", "0705_dome_node_dz_0.3"), "0705_dome_node_dz_0.3")
        fxz = S.fem_nodes_load(os.path.join(root, "calibs", "0705_dome_node_dxdz_0.3"), "0705_dome_node_dxdz_0.3")
    except (FileNotFoundError, ValueError, OSError) as exc:
        skip("門 19/20 FEM", "節点ファイルが読めない: %s" % exc)
        return ctx
    cmp = S.fem_vs_halfspace(fz, fxz)
    ctx["fem"] = cmp
    ctx["fem_fxz"] = fxz
    at = lambda rmm: float(np.interp(rmm * 1e-3, cmp["mids"], cmp["rdz_n"]))      # noqa: E731
    gate("門 19 FEM の法線荷重(ドーム R %.1f mm、節点 %d、最小間隔 %.2f mm): r·dz を 0.5〜0.8 mm で 1 に正規化すると半空間 Boussinesq はどこでも 1 のところ、"
         "FEM は 1 mm で %.2f、2 mm で %.2f、3 mm で %.2f と落ち、1/r から 2 倍外れる半径 r½ = %.2f mm —— 有限厚ゲルの効き(接触は節点間隔より小さい点荷重状。"
         "半空間 1 mm 以内 0.8〜1.0、r½ は 1.5〜4 mm)" % (cmp["R_dome"] * 1e3, fz["n"], cmp["dx_min_spacing"] * 1e3, at(1.0), at(2.0), at(3.0), (cmp["r_half"] or 0) * 1e3),
         0.8 <= at(1.0) <= 1.0 and cmp["r_half"] is not None and 1.5e-3 < cmp["r_half"] < 4e-3 and at(3.0) < 0.5,
         "dz(0) = %.1f µm、法線だけの FEM でも中心に dy/dz = %.2f の接線成分(対称でない、%.1f s)" % (cmp["dz0"] * 1e6, cmp["dy_over_dz0"], time.time() - t0))
    ang = cmp["ang"]
    mid = [d for d in ang if 1.4e-3 <= d["r"] <= 2.1e-3]
    far_ = [d for d in ang if d["r"] >= 2.9e-3]
    gate("門 20 FEM の斜め荷重の接線変位 dx(θ) は r = 1.5〜2 mm(r½ の内側)で Cerruti の形 A + B cos²θ に乗り(R² > 0.7)、異方性 (A+B)/A = 1/(1−ν) から読む ν が "
         "0.45〜0.52(ほぼ非圧縮)、dy は sin2θ(R² > 0.5); r = 3 mm(r½ の外)では比が半空間の上限 2(ν = 0.5)を超える —— 有限厚は半径減衰だけでなく r½ の外で"
         "角度依存も歪める(1 mm は節点が粗く R² 0.5)",
         all(d["R2"] > 0.7 and 0.45 <= d["nu"] <= 0.52 for d in mid) and cmp["dy_fit"]["R2"] > 0.5 and all(d["ratio"] > 2.0 for d in far_),
         "r %s mm: 比 %s、ν %s、R² %s、dy R² %.2f" % ([round(d["r"] * 1e3, 1) for d in ang], [round(d["ratio"], 2) for d in ang],
                                                      [round(d["nu"], 3) for d in ang], [round(d["R2"], 2) for d in ang], cmp["dy_fit"]["R2"]))
    return ctx


# ----------------------------------------------------------------------------------------------------------------------
# 図
def _crop_up(img, cy, cx, half, up):
    y0, x0 = int(round(cy)) - half, int(round(cx)) - half
    c = img[y0:y0 + 2 * half, x0:x0 + 2 * half]
    return np.kron(c, np.ones((up, up) + (1,) * (c.ndim - 2)))


def _circle(img, cxy, r, color, width=1):
    return np.asarray(imagedraw.draw_circle(img, cxy, r, color=color, width=width, fill=False))


def _draw_segments(img, p0s, p1s, color, width: int = 1):
    """多数の線分を一度に描く(numpy、アンチエイリアスなし)。imagedraw.draw_line は 1 本 1.4 ms で 6,000 本だと 8 s かかる(実測)。"""
    out = np.asarray(img, np.float64).copy()
    H, W = out.shape[:2]
    p0s = np.asarray(p0s, np.float64); p1s = np.asarray(p1s, np.float64)
    if len(p0s) == 0:
        return out
    n = int(np.ceil(np.hypot(*(p1s - p0s).T).max())) * 2 + 2
    t = np.linspace(0.0, 1.0, n)
    xs = p0s[:, 0, None] + (p1s[:, 0] - p0s[:, 0])[:, None] * t
    ys = p0s[:, 1, None] + (p1s[:, 1] - p0s[:, 1])[:, None] * t
    xi = np.rint(xs).astype(int).ravel(); yi = np.rint(ys).astype(int).ravel()
    for dy in range(-(width // 2), width - width // 2):
        for dx in range(-(width // 2), width - width // 2):
            xx, yy = xi + dx, yi + dy
            ok = (xx >= 0) & (xx < W) & (yy >= 0) & (yy < H)
            out[yy[ok], xx[ok]] = color
    return out


def _vectors(img, p0, u, cpx, half, up, scale=4.0):
    inside = (np.abs(p0[:, 0] - cpx) < half - 2) & (np.abs(p0[:, 1] - cpx) < half - 2)
    o = round(cpx) - half
    return _draw_segments(img, (p0[inside] - o) * up, (p0[inside] + scale * u[inside] - o) * up, (1.0, 0.2, 0.1))


def figures(ctx):
    print("== 図")
    hz, a = ctx["hz"], ctx["hz"]["a"]
    muP = MU * P_LOAD
    cpx = centre_px()
    half = int(round(2.3 * a / PITCH)); up = 2
    sc = ctx["rows"][1]["sc"]; tr = ctx["rows"][1]["tr"]
    ref = np.clip(_crop_up(sc.rgb_ref, cpx, cpx, half, up), 0, 1)
    cur = np.clip(_crop_up(sc.rgb_cur, cpx, cpx, half, up), 0, 1)
    vec = _vectors(cur, tr["p0"], tr["u"], cpx, half, up)
    cc = (half * up, half * up)
    vec = _circle(vec, cc, a / PITCH * up, (1.0, 1.0, 1.0)); vec = _circle(vec, cc, sc.mp["c"] / PITCH * up, (0.1, 0.9, 0.2), 2)
    figs.save_grid("tacslip_marker_frames", [ref, cur, vec], ncols=3,
                   captions=["reference (P only)", "P + Q, Q/muP = 0.5", "tracked displacement x4, c (green), a (white)"],
                   caption="球(R = 6 mm)を 0.5 N で押した膜のマーカー配列(ピッチ 0.5 mm = 8 px、半径 %.1f px)、圧痕まわり ±%.1f mm を 2 倍。左 = 法線荷重だけの基準像、"
                           "中 = 接線 Q = 0.5 μP を掛けた像、右 = マーカー追跡の変位ベクトル(4 倍)。固着円(緑、c/a = %.3f)の中は一様に動き、滑り環で遅れ、"
                           "外側は 1/r で尾を引く。" % (MARK_R_PX, half * PITCH * 1e3, sc.mp["c_over_a"]))
    frames, seen_q, seen_c = [], [], []
    qs = np.linspace(0.0, 1.0, 1001)
    curve = (1 - qs) ** (1 / 3)
    for qr in np.linspace(0.02, 1.0, 12):
        s = Scene(ctx, qr * muP)
        t_ = s.track()
        fit = S.mindlin_fit(ctx["model"], t_["p0"], t_["u"] * PITCH)
        seen_q.append(qr); seen_c.append(fit["c_over_a"])
        left = _vectors(np.clip(_crop_up(s.rgb_cur, cpx, cpx, half, up), 0, 1), t_["p0"], t_["u"], cpx, half, up)
        left = _circle(left, cc, a / PITCH * up, (1.0, 1.0, 1.0))
        if s.mp["c"] > 0:
            left = _circle(left, cc, s.mp["c"] / PITCH * up, (0.1, 0.9, 0.2), 2)
        if fit["c_over_a"] > 0.02:
            left = _circle(left, cc, fit["c_over_a"] * a / PITCH * up, (1.0, 0.1, 0.1), 1)
        right = figs.render_plot([("closed form (1 - Q/muP)^(1/3)", qs, curve), ("from markers", np.array(seen_q), np.array(seen_c))],
                                 xlabel="Q / muP", ylabel="stick radius c / a", title="Q/muP = %.2f" % qr, size=(420, left.shape[0]),
                                 xlim=(0, 1.02), ylim=(0, 1.05), kinds=["line", "scatter"], styles=["dashed", None], colors=["reference", "emphasis"])
        frames.append(np.hstack([left, np.asarray(right, np.float64)]))
    figs.save_gif("tacslip_stick_circle_shrinks", frames, fps=2.5,
                  caption="接線力を 0 → μP に上げる(12 コマ)。左 = マーカー像 + 追跡ベクトル(4 倍)、緑 = 閉形式の固着円 c = a(1 − Q/μP)^{1/3}、赤 = 画像から当てた c、"
                          "白 = 接触円 a。右 = c/a の閉形式(破線)に各コマの推定点が増える。Q = μP で核が消え全滑り。")
    rr = np.linspace(0, a, 400)
    series = [("Q/muP = %.2f (c/a = %.3f)" % (qr, ctx["mps"][qr]["c_over_a"]), rr * 1e3, S.mindlin_traction(rr, ctx["mps"][qr]) * 1e-3) for qr in (0.25, 0.5, 0.75)]
    series.append(("mu p(r) (Coulomb limit)", rr * 1e3, MU * T.hertz_pressure(rr, a, hz["p0"]) * 1e-3))
    figs.save_plot("tacslip_traction_q_r", series, xlabel="r [mm]", ylabel="q(r) [kPa]", title="Cattaneo-Mindlin shear traction",
                   kinds=["line"] * 4, styles=[None, None, None, "dashed"], colors=["emphasis", "right", "wrong", "reference"], size=(640, 400),
                   caption="接線トラクション q(r) = μp0[√(1−r²/a²) − (c/a)√(1−r²/c²)]。固着円 r < c では Coulomb の限界 μp(r)(破線)の下、滑り環 c < r < a では "
                           "限界に張り付く。Q が増えると c が縮み、張り付く環が内へ広がる。")
    qq = np.linspace(0, 1, 200)
    dcf = np.array([S.mindlin_partial_slip(q * muP, hz, MU, G_GEL, NU)["delta_x"] for q in qq]) / PITCH
    sw = ctx["sweep"]
    figs.save_plot("tacslip_delta_x_vs_Q", [("closed form delta_x(Q)", qq, dcf), ("initial stiffness Q/k_t", qq, qq * muP / ctx["full"]["k_t"] / PITCH),
                                            ("stick-core median from markers", [s["qr"] for s in sw], [s["dx_meas"] for s in sw])],
                   xlabel="Q / muP", ylabel="tangential displacement [px] (62.5 um/px)", title="delta_x vs Q: closed form and markers",
                   kinds=["line", "line", "scatter"], styles=["dashed", "dotted", None], colors=["reference", "neutral", "emphasis"], size=(640, 400),
                   caption="剛体球の接線変位 δx = 3μP(2−ν)/(16Ga)[1 − (1−Q/μP)^{2/3}] (破線)と初期剛性 kt = 8Ga/(2−ν) の直線(点線)。点 = 固着核(r < 0.3c)の"
                           "マーカー変位の中央値。全滑りで %.2f px。" % (ctx["dx_full"] / PITCH))
    figs.save_plot("tacslip_entropy_vs_Q", [("entropy, bins fixed to full-slip delta_x", [s["qr"] for s in sw], [s["ent_abs"] for s in sw]),
                                            ("entropy of the shape only (bins = per-field max)", [s["qr"] for s in sw], [s["ent_rel"] for s in sw])],
                   xlabel="Q / muP", ylabel="normalised Shannon entropy", title="Slip indicator (Yuan 2017) vs Q/muP",
                   kinds=["scatter", "scatter"], colors=["emphasis", "right"], size=(640, 400),
                   caption="接触円内のマーカー変位の大きさのヒストグラム(16 ビン)のエントロピー。ビンを全滑り δx に固定した版は単調非減少(Yuan 2017 の定性値)。"
                           "ビンを場ごとの最大に合わせた「形だけ」の版は固着核が縮むほど滑り環の勾配に乗るマーカーが増えて上がる。")
    fem = ctx.get("fem")
    if fem is not None:
        p1 = figs.render_plot([("half-space (Boussinesq): r*uz = const", np.array([0.4, 6.0]), np.array([1.0, 1.0])),
                               ("FEM dome, dz load (r*dz)", fem["mids"] * 1e3, fem["rdz_n"]), ("FEM dome, dx+dz load (r*dx)", fem["mids_dx"] * 1e3, fem["rdx_n"])],
                              xlabel="r [mm]", ylabel="r * u / (r * u at 0.5-0.8 mm)", title="Finite gel vs half-space: radial decay",
                              size=(520, 380), kinds=["line", "scatter", "scatter"], styles=["dashed", None, None], colors=["reference", "emphasis", "right"])
        d = fem["ang"][2]
        m = np.abs(fem["r"] - 2.0e-3) < 0.3e-3
        th = np.degrees(fem["th"][m]); o = np.argsort(th)
        thd = np.linspace(-180, 180, 361)
        rn = fem["r"][m] / 2.0e-3
        p2 = figs.render_plot([("Cerruti A + B cos^2(theta), nu = %.2f" % d["nu"], thd, (d["A"] + d["B"] * np.cos(np.radians(thd)) ** 2) * 1e6),
                               ("FEM dx * (r / 2 mm), nodes at r = 1.7-2.3 mm", th[o], (ctx["fem_fxz"]["dx"][m] * rn)[o] * 1e6)],
                              xlabel="theta [deg]", ylabel="dx [um] (scaled to r = 2 mm)", title="Angular form of the tangential field",
                              size=(520, 380), kinds=["line", "scatter"], styles=["dashed", None], colors=["reference", "emphasis"])
        figs.save_grid("tacslip_fem_vs_halfspace", [p1, p2], ncols=2, captions=["radial decay", "angular dependence (dx+dz case)"],
                       caption="第 2 真値: 有限要素の節点変位(ドーム状の有限厚ゲル、Robo-Touch/Taxim リポジトリ同梱、MIT)と半空間解。左 = r·u を 0.5〜0.8 mm で 1 に正規化。"
                               "半空間なら 1 のまま、FEM は r½ = %.1f mm で半分 —— 有限厚の効き(接線の r·dx は法線より緩やかに落ちる)。右 = 斜め荷重の dx(θ) を "
                               "r = 2 mm に換算。Cerruti の A + B cos²θ に乗り、異方性から読む ν = %.2f。ただし FEM の山は半空間の当てはめより尖る"
                               "(r½ の外で比が 2 を超える前兆)。角度依存はほぼ残り、半径減衰が先に外れる。" % (fem["r_half"] * 1e3, d["nu"]))
    else:
        print("  (FEM の図は FULLSEYE_TAXIM_DATA があるときだけ)")
    br = ctx["breaks"]
    pts_l = ctx["pts_flat"]; bg_rgb = ctx["bg_rgb"]
    m_a = S.marker_image(S.membrane_render_markers(bg_rgb, pts_l, MARK_R_PX, MARK_DARK), bg_rgb)
    pts_j = pts_l + np.random.default_rng(0).uniform(-1.5, 1.5, pts_l.shape)
    m_ja = S.marker_image(S.membrane_render_markers(bg_rgb, pts_j, MARK_R_PX, MARK_DARK), bg_rgb)
    shifts = np.arange(1, 8, dtype=float)
    read_l, read_j = [], []
    for dxs in shifts:
        m_b = S.marker_image(S.membrane_render_markers(bg_rgb, pts_l + np.array([dxs, 0.0]), MARK_R_PX, MARK_DARK), bg_rgb)
        read_l.append(float(np.nanmedian(np.asarray(pivops.piv_cross_correlate(m_a, m_b, window=32, overlap=0.5)[0])[1])))
        m_jb = S.marker_image(S.membrane_render_markers(bg_rgb, pts_j + np.array([dxs, 0.0]), MARK_R_PX, MARK_DARK), bg_rgb)
        read_j.append(float(np.nanmedian(np.asarray(pivops.piv_cross_correlate(m_ja, m_jb, window=32, overlap=0.5)[0])[1])))
    pa = figs.render_plot([("truth", shifts, shifts), ("regular 8 px lattice: PIV reads", shifts, np.array(read_l)),
                           ("lattice with +-1.5 px jitter: PIV reads", shifts, np.array(read_j))],
                          xlabel="true shift [px]", ylabel="PIV reading [px] (32 px window, 1/4 rule)", title="(a) lattice aliasing",
                          size=(520, 380), kinds=["line", "scatter", "scatter"], styles=["dashed", None, None], colors=["reference", "wrong", "right"])
    pb = figs.render_plot([("|Q/muP error| at Q/muP = 0.5", [b["pitch"] for b in br[:3]], [b["e_q"] for b in br[:3]]),
                           ("markers inside the contact circle / 100", [b["pitch"] for b in br[:3]], [b["n_in"] / 100 for b in br[:3]])],
                          xlabel="marker pitch [px]", ylabel="error  |  count / 100", title="(b) marker density", size=(520, 380),
                          kinds=["scatter", "scatter"], colors=["emphasis", "neutral"], ylim=(0, 0.6))
    nz = br[:1] + br[3:]
    pc = figs.render_plot([("tracking RMS [px]", [b["noise"] for b in nz], [b["rms"] for b in nz]), ("|Q/muP error|", [b["noise"] for b in nz], [b["e_q"] for b in nz])],
                          xlabel="pixel noise sigma", ylabel="px  |  error", title="(c) pixel noise", size=(520, 380),
                          kinds=["scatter", "scatter"], colors=["emphasis", "wrong"], ylim=(0, 0.06))
    figs.save_grid("tacslip_failure_modes", [pa, pb, pc], ncols=3, captions=["lattice aliasing", "marker density", "pixel noise"],
                   caption="壊れる場所。(a) 規則格子(8 px)に窓相関を当てると、ずれが 4 px を超えた所で読みが u − 8 に飛ぶ(5 → −3)。±1.5 px のジッタ格子なら飛ばない。"
                           "対応を「視野の縁から連続性で伸ばす」のはこのため。(b) マーカー間隔 8 → 16 px で接触円内が %d → %d 個に減っても Q/μP の誤差は 0.05 以内 "
                           "—— 効くのは数より固着縁に対するマーカーの位置。(c) 画素雑音 σ = 0.05 で追跡 RMS は 0.03 px に増えるが Q/μP は 0.05 以内(全マーカーで当てる)。"
                           % (br[0]["n_in"], br[2]["n_in"]))
    print("  figures:", figs.errors() or "ok")


def main() -> int:
    t_all = time.time()
    ctx = numpy_part()
    ctx = fem_part(ctx)
    if figs.enabled():
        figures(ctx)
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
    # measure.fit_circle は図の円の検算用に import 済み(被験者の一覧に載せるため)。
    _ = FM.fit_circle
    sys.exit(main())
