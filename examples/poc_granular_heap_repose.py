# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""粉体の山を画像で測る —— 安息角・体積・質量・流動性・排出率を規則だけで、真値は閉形式・公表値・MuJoCo(2026-10-05)。

物理シミュ × Fullseye 系列(pegsim / tacsim / tacslip / tactorque / puck / pegfail に続く)。先行研究の粉体計量
(Kadokawa, Hamaya, Tanaka, IROS 2023, doi 10.1109/iros55552.2023.10342463)は秤の質量だけを観測に使い、視覚は無い。
ここは **山の形(側面像・高さ図)から安息角・質量・流動性を読む**側を、新モジュール granular(23 op + mujoco の facade 2)で
学習なしに組む。外から来る真値:
  * **閉形式**: 円錐 V = (π/3) R² H、H = R tan φ、m = ρ_b V; Beverloo, Leniger, van de Velde 1961 の排出則
    W = C ρ_b √g (D₀ − k d)^{5/2}(C ≈ 0.58、k ≈ 1.4、Nedderman 1992 の整理)。
  * **公表の表**: USP 一般章 <1174> Powder Flow の Table 1(安息角 → 流動性区分、原典 Carr 1965)。表は整数の度。
  * **公表値**: 1 mm ガラス球の安息角 25.2 ± 0.8 度(Sunday, Murdoch, Tardivel, Schwartz, Michel, MNRAS 2020、arXiv 2009.10448 §5.4)。
    測り方(側面像の上縁に左右別々に直線、裾と頂を除く)も同論文 §5.3 —— op の作法の出典。
  * **第 2 実装(--full)**: MuJoCo の剛体球 1,200 個を平底ホッパの正方孔から流して山を作る。

門(既定 20 本 + --full 5 本): 円錐の閉形式、高さ図の体積、側面像の往復、被覆率の雑音(edge 法 vs 列和法の罠)、高さ図の最頻、
Beverloo の指数(合成排出の高さ図列)と値、裾の丸みと頂の鈍り、分解能(山の幅 25 / 50 / 400 px)、傾いた基準面(左右差 ≈ 2β の警報)、
流動性区分の境界、綴り壊し、山が写っていない、スプーンの規則、容器の充填率、動画からの質量と排出率の帯当て、MJCF 文字列、入口の棚卸し、
所要; --full: 山ができたか、φ vs 公表値、高さ図 vs 側面、排出率 vs Beverloo、所要。
図(既定の出力先は out/figures/<PoC 名>/、FULLSEYE_FIGURE_DIR で変更): 側面像に当てた 2 直線と真値、勾配ヒストグラム、分解能で壊れる場所、
裾・頂・基準面・小さな山の 4 枚、Beverloo の W(D₀)、流動性の帯、スプーンの傾け、**基準面の傾きを振る GIF**; --full: 球の山ができる GIF、
側面に当てた直線と公表値の線、高さ図、排出の質量の列、MuJoCo と公表値・Beverloo の表。
正直に: 合成の側面像は縁の模型が計測と同じなので雑音なしの往復は配管の検査。独立な被験者は雑音と MuJoCo の球だけ。MuJoCo の山は
公表値より約 3 度低く出る(剛体・付着なし・転がり摩擦の模型が DEM と違う・山が 5 粒径しか無い・正方孔の異方性 —— 切り分けていない)。
Beverloo との比は桁の照合だけ(正方孔を等価直径に、D₀/d ≈ 6.8 は詰まりの限界付近)。mg 級の計量は画像では無理(g 級で成立)。
Run: py -3.11 examples/poc_granular_heap_repose.py [--full]        (--full は mujoco)
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import annotate as AN  # noqa: E402
import examplefig as figs  # noqa: E402
import granular as G  # noqa: E402

FULL = "--full" in sys.argv
PHIS = (20.0, 25.0, 30.0, 35.0, 40.0, 45.0)
_GATES: list[tuple[str, bool]] = []


def gate(name, ok, detail=""):
    _GATES.append((name, bool(ok)))
    print("  [%s] %s %s" % ("ok" if ok else "NG", name, detail))


def skip(name, why):
    print("  [skip] %s —— %s" % (name, why))


def _raises(fn, *a, **k):
    try:
        fn(*a, **k)
    except ValueError:
        return True
    except Exception as exc:  # noqa: BLE001  別の例外は fail-closed ではない
        print("    (wrong exception %s: %s)" % (type(exc).__name__, exc))
        return False
    return False


# ======================================================================================================================
# 図の道具(numpy だけ)
# ======================================================================================================================
def _rgb(cov):
    g = np.clip(np.asarray(cov, float), 0, 1)
    return np.stack([0.10 + 0.78 * g, 0.10 + 0.70 * g, 0.12 + 0.52 * g], axis=-1)


def _line(img, p0, p1, color, width=1.5, dash=0):
    """(row, col) の 2 点を結ぶ太線。``dash`` > 0 なら dash 画素ごとに描く / 抜くを繰り返す。"""
    (r0, c0), (r1, c1) = p0, p1
    n = int(max(abs(r1 - r0), abs(c1 - c0)) * 2) + 2
    rr, cc = np.linspace(r0, r1, n), np.linspace(c0, c1, n)
    h, w = img.shape[:2]
    k = int(math.ceil(width))
    for t, (r, c) in enumerate(zip(rr, cc)):
        if dash and (t // (2 * dash)) % 2 == 1:
            continue
        for dr in range(-k, k + 1):
            for dc in range(-k, k + 1):
                if dr * dr + dc * dc <= width * width:
                    i, j = int(round(r)) + dr, int(round(c)) + dc
                    if 0 <= i < h and 0 <= j < w:
                        img[i, j] = color
    return img


def _text(img, s, xy, fs=18, anchor="lt"):
    try:
        return np.asarray(AN.text_box(img, s, xy, anchor=anchor, font_size=fs), dtype=np.float64)
    except Exception as exc:  # noqa: BLE001  文字が収まらない等は図を落とさず素の絵(理由は errors に残る)
        figs._errors.append("text_box: %r" % (exc,))
        return img


def _draw_fit(cov, res, truth_phi=None, title=None, scale=1, background=None, ref_phi=None, ref_label="ref"):
    """側面像に左右の当てた直線(当てた範囲 = 太い黄、その延長 = 細い橙)と地面線(青)を描く。

    ``scale`` = 最近傍で拡大(小さな山は画素を見せる)。``background`` = 被覆率の代わりに敷く RGB(陰影つき描画、座標は実寸比)。
    ``ref_phi`` = 頂から引く参照の斜面(公表値など、水色の破線)。"""
    if background is None:
        img = _rgb(cov)
        if scale > 1:
            img = np.kron(img, np.ones((scale, scale, 1)))
    else:
        img = np.asarray(background, float).copy()
        scale = img.shape[1] / cov.shape[1]
    rows = img.shape[0]
    top, g, xs = res["profile_top"] * scale, res["profile_ground"] * scale, res["profile_cols"] * scale
    _line(img, (rows - g[0], xs[0]), (rows - g[-1], xs[-1]), (0.35, 0.65, 1.0), 1.2)
    if ref_phi is not None:
        ia = int(np.argmax(top))
        ax, ay, gy = xs[ia] + 0.5 * scale, top[ia], float(np.median(g))
        dx = (ay - gy) / math.tan(math.radians(ref_phi))
        for sgn in (-1, 1):
            _line(img, (rows - ay, ax), (rows - gy, ax + sgn * dx), (0.3, 0.95, 0.95), 1.0, dash=6)
    for side_cols, th, sign in ((res["left_cols"], res["phi_left_deg"], +1), (res["right_cols"], res["phi_right_deg"], -1)):
        c0, c1 = side_cols[0] * scale, side_cols[1] * scale
        i0, i1 = int(np.searchsorted(xs, c0)), min(int(np.searchsorted(xs, c1)), len(xs) - 1)
        t = math.tan(math.radians(th)) * sign
        cm, ym = 0.5 * (c0 + c1), 0.5 * (top[i0] + top[i1])
        ext = 0.45 * res["base_px"] * scale
        for (a, b), col, w in (((cm - ext, cm + ext), (1.0, 0.55, 0.15), 0.8), ((c0, c1), (1.0, 0.85, 0.2), 2.0)):
            _line(img, (rows - (ym + t * (a - cm)), a + 0.5 * scale), (rows - (ym + t * (b - cm)), b + 0.5 * scale), col, w)
    label = "measured phi = %.2f deg (left %.2f / right %.2f)" % (res["phi_deg"], res["phi_left_deg"], res["phi_right_deg"])
    if truth_phi is not None:
        label += "   %s %.2f" % (ref_label, truth_phi)
    y = 8
    if title:
        img = _text(img, title, (8, y))
        y += 30
    return _text(img, label, (8, y))


def _pad_top(frames, h=None):
    """高さ・幅の違うコマを、上と左右に背景を足して揃える(GIF は全コマ同じ大きさ)。"""
    h = h or max(f.shape[0] for f in frames)
    w = max(f.shape[1] for f in frames)
    out = []
    for f in frames:
        pad = np.empty((h, w, 3))
        pad[:] = (0.10, 0.10, 0.12)
        c0 = (w - f.shape[1]) // 2
        pad[h - f.shape[0]:, c0:c0 + f.shape[1]] = f
        out.append(pad)
    return out


# ======================================================================================================================
def numpy_part() -> dict:
    print("== 1. numpy の門(閉形式・側面像・高さ図・Beverloo・基準面・流動性・スプーン・容器・MJCF)")
    t0 = time.perf_counter()
    out = {}

    # ── 門 1 円錐の閉形式
    c = G.heap_volume_cone(R=0.3, H=0.2)
    e1 = abs(c["V"] - math.pi / 3 * 0.09 * 0.2) / c["V"]
    c2 = G.heap_volume_cone(R=0.3, phi_deg=c["phi_deg"])
    c3 = G.heap_volume_cone(H=c2["H"], phi_deg=c["phi_deg"])
    e2 = max(abs(c2["H"] - 0.2) / 0.2, abs(c3["R"] - 0.3) / 0.3, abs(c3["V"] - c["V"]) / c["V"])
    e3 = abs(G.heap_mass(c["V"], 1500.0) - 1500.0 * c["V"]) / (1500.0 * c["V"])
    gate("門 1 円錐の閉形式 V = πR²H/3、H = R tan φ、m = ρ_b V", e1 < 1e-12 and e2 < 1e-9 and e3 < 1e-12
         and _raises(G.heap_volume_cone, R=1.0, H=1.0, phi_deg=45.0) and _raises(G.heap_volume_cone, R=1.0),
         "体積 %.1e、往復 %.1e、質量 %.1e(門 1e-9)、3 つ全部 / 1 つだけ → ValueError" % (e1, e2, e3))

    # ── 門 2 高さ図の体積
    vols = []
    for phi in PHIS:
        w = G.heap_synth_cone(phi, 200)
        vols.append(abs(G.heap_volume_heightmap(w["heightmap"], w["pitch"]) / w["truth"]["V_cone"] - 1))
    assert len(vols) == len(PHIS)
    gate("門 2 高さ図の体積 vs 閉形式(6 角度、幅 400 px の山)", max(vols) < 1e-4, "max |ΔV|/V = %.1e(門 1e-4)" % max(vols))

    # ── 門 3 側面像の往復 / 門 5 高さ図の最頻
    e_sil, e_cmp, e_hm = [], [], []
    for phi in PHIS:
        w = G.heap_synth_cone(phi, 200)
        s = G.repose_angle_silhouette(w["side"])
        hm = w["heightmap"] + np.random.default_rng(int(phi)).normal(0.0, 0.05 * w["pitch"], w["heightmap"].shape)
        h = G.repose_angle_heightmap(hm, w["pitch"])
        e_sil.append(abs(s["phi_deg"] - phi))
        e_cmp.append(abs(h["phi_deg"] - s["phi_deg"]))
        e_hm.append(abs(h["phi_deg"] - phi))
    assert len(e_sil) == len(PHIS)
    gate("門 3 側面像 → φ の往復(雑音なし、6 角度)", max(e_sil) < 0.01,
         "max |Δφ| = %.4f 度(門 0.01)—— 合成と計測の縁の模型が同じなので配管の検査" % max(e_sil))
    # ── 門 4 被覆率の雑音 ±0.1: edge 法 vs 列和法
    errs = []
    for seed in range(5):
        for phi in (25.0, 35.0):
            w = G.heap_synth_cone(phi, 200, noise=0.1, seed=seed)
            errs.append(G.repose_angle_silhouette(w["side"])["phi_deg"] - phi)
    assert len(errs) == 10
    e4 = float(np.max(np.abs(errs)))
    w = G.heap_synth_cone(30.0, 200, noise=0.1, seed=0)
    bias_cs = G.repose_angle_silhouette(w["side"], method="column_sum")["phi_deg"] - 30.0
    gate("門 4 被覆率に一様雑音 ±0.1: edge 法と列和法", e4 < 0.02 and bias_cs < -0.4,
         "edge 法 max |Δφ| %.4f 度(門 0.02); 列和法は [0, 1] に切った雑音で粉の平均値が 0.975 → tan φ がその比で縮み %.3f 度(罠を数で残す)"
         % (e4, bias_cs))
    gate("門 5 高さ図の勾配ヒストグラムの最頻 vs 側面(高さ雑音 σ 0.05 px)", max(e_cmp) < 0.5 and max(e_hm) < 0.5,
         "側面との差 max %.3f 度、真値との差 max %.3f 度(門 0.5; 雑音は勾配を上にしか動かさない)" % (max(e_cmp), max(e_hm)))

    # ── 門 6 Beverloo の指数(合成排出の高さ図列、σ 0.5 mm)
    D0s = np.array([0.02, 0.025, 0.03, 0.035, 0.04, 0.05])
    Ws, Wt = [], []
    for D0 in D0s:
        ds = G.discharge_synth(D0, 0.001, 1500.0, 30.0, 1.5e-3, 2.0, n_frames=6, grid=256, noise=0.5e-3, seed=3)
        Ws.append(G.dispense_mass_from_video(ds["frames"], 1.5e-3, 1500.0, ds["times"])["rate"])
        Wt.append(ds["W"])
    f = G.beverloo_fit(D0s, Ws, 0.001, 1500.0)
    f0 = G.beverloo_fit(D0s, Wt, 0.001, 1500.0)
    gate("門 6 Beverloo の指数 2.5(高さ図の列 6 本 × 6 コマ、σ 0.5 mm)",
         abs(f["n"] / 2.5 - 1) < 0.01 and abs(f["C"] / 0.58 - 1) < 0.03 and abs(f0["n"] - 2.5) < 1e-6,
         "n = %.4f(±1 %%)、C = %.4f(±3 %%; 雑音の地面を 0 で切る偏り)、雑音なし n = %.7f" % (f["n"], f["C"], f0["n"]))
    out.update(g06=f, g06_D0=D0s, g06_W=np.array(Ws))
    # ── 門 7 Beverloo の値と fail-closed
    Wh = 0.58 * 1500.0 * math.sqrt(9.80665) * (0.03 - 1.4 * 0.001) ** 2.5
    gate("門 7 Beverloo の値 / D₀ ≤ k d は拒否", abs(G.beverloo_rate(0.03, 0.001, 1500.0) - Wh) < 1e-12
         and _raises(G.beverloo_rate, 0.0014, 0.001, 1500.0) and _raises(G.beverloo_rate, 0.03, 0.001, -5.0)
         and _raises(G.beverloo_fit, [0.02, 0.03], [1.0, 2.0], 0.001, 1500.0),
         "W(30 mm, 1 mm, 1500 kg/m³) = %.4f kg/s = 手計算; 有効開口なし・負の密度・2 点の当てはめ → ValueError" % Wh)

    # ── 門 8 裾の丸み / 門 9 頂の鈍り
    w = G.heap_synth_cone(30.0, 200, toe_round_px=60, noise=0.1, seed=0)
    b_no = G.repose_angle_silhouette(w["side"], toe_frac=0.0, apex_frac=0.0)["phi_deg"] - 30.0
    b_ex = G.repose_angle_silhouette(w["side"])["phi_deg"] - 30.0
    gate("門 8 裾の丸み(円弧 r = 60 px、裾の幅 30 px / 底 400 px)", b_no < -0.1 and abs(b_ex) < 0.02,
         "裾ごと当てると %.3f 度、裾 15 %% を外すと %.3f 度(門 < −0.1 / 0.02)" % (b_no, b_ex))
    w = G.heap_synth_cone(30.0, 200, apex_blunt_px=60, noise=0.1, seed=0)
    a_no = G.repose_angle_silhouette(w["side"], toe_frac=0.0, apex_frac=0.0)["phi_deg"] - 30.0
    a_ex = G.repose_angle_silhouette(w["side"])["phi_deg"] - 30.0
    gate("門 9 頂の鈍り(円弧 r = 60 px)", a_no < -0.3 and abs(a_ex) < 0.02,
         "頂ごと当てると %.3f 度、頂 15 %% を外すと %.3f 度(門 < −0.3 / 0.02)" % (a_no, a_ex))

    # ── 門 10 分解能
    res = {}
    for W in (25, 50, 400):
        es, eh = [], []
        for seed in range(6):
            for phi in (25.0, 30.0, 35.0, 40.0):
                w = G.heap_synth_cone(phi, W / 2, noise=0.1, seed=seed)
                es.append(G.repose_angle_silhouette(w["side"])["phi_deg"] - phi)
                hm = w["heightmap"] + np.random.default_rng(seed).normal(0.0, 0.1 * w["pitch"], w["heightmap"].shape)
                eh.append(G.repose_angle_heightmap(hm, w["pitch"])["phi_deg"] - phi)
        assert len(es) == 24
        res[W] = (float(np.max(np.abs(es))), float(np.max(np.abs(eh))))
    gate("門 10 分解能: 山の幅 50 px で φ の誤差は何度か", res[50][0] < 0.3 and res[25][0] < 1.0 and res[50][1] < 1.5,
         "側面(雑音 ±0.1): 25 px %.3f、50 px %.3f、400 px %.3f 度(門 1.0 / 0.3); 高さ図(σ 0.1 px): 50 px %.3f、400 px %.3f 度(門 1.5)"
         % (res[25][0], res[50][0], res[400][0], res[50][1], res[400][1]))

    # ── 門 11 傾いた基準面(せん断型 datum、β = 5 度)
    beta = 5.0
    w = G.heap_synth_cone(30.0, 200, ground_tilt_deg=beta)
    s = G.repose_angle_silhouette(w["side"])
    sc = G.repose_angle_silhouette(w["side"], correct_ground=True)
    d = G.datum_tilt_check(s)
    flat = G.datum_tilt_check(G.repose_angle_silhouette(G.heap_synth_cone(30.0, 200)["side"]))
    exp_l = math.degrees(math.atan(math.tan(math.radians(30.0)) + math.tan(math.radians(beta))))
    exp_r = math.degrees(math.atan(math.tan(math.radians(30.0)) - math.tan(math.radians(beta))))
    h_raw = G.repose_angle_heightmap(w["heightmap"], w["pitch"])
    h_cor = G.repose_angle_heightmap(w["heightmap"], w["pitch"], ground=w["ground"])
    ok11 = (abs(s["phi_left_deg"] - exp_l) < 0.05 and abs(s["phi_right_deg"] - exp_r) < 0.05 and abs(s["ground_deg"] - beta) < 0.05
            and abs(sc["phi_deg"] - 30.0) < 0.02 and d["alarm"] and not flat["alarm"] and abs(d["phi_shear_deg"] - 30.0) < 0.02
            and abs(d["beta_shear_deg"] - beta) < 0.05 and abs(h_raw["phi_deg"] - beta) < 0.5 and abs(h_cor["phi_deg"] - 30.0) < 0.02)
    gate("門 11 傾いた基準面 β = 5 度は安息角に足し算される", ok11,
         "左右の斜面 %.2f / %.2f(閉形式 atan(tan φ ± tan β) = %.2f / %.2f)、左右差 %.2f → 警報(平らなら %.3f で警報なし)、"
         "tan の引き算で %.4f、回転型の読み(角の平均)%.2f —— 片側の斜面では 1 次で違う(33.62 対 35.00); 高さ図の最頻は %.2f 度 = 地面そのもの、datum を渡せば %.4f"
         % (s["phi_left_deg"], s["phi_right_deg"], exp_l, exp_r, d["asymmetry_deg"], flat["asymmetry_deg"], d["phi_shear_deg"],
            d["phi_roll_deg"], h_raw["phi_deg"], h_cor["phi_deg"]))

    # ── 門 12 流動性区分(USP <1174> Table 1)
    exp = [(25.0, "excellent"), (30.0, "excellent"), (30.4, "excellent"), (30.5, "good"), (31.0, "good"), (35.0, "good"), (36.0, "fair"),
           (40.0, "fair"), (41.0, "passable"), (45.0, "passable"), (46.0, "poor"), (55.0, "poor"), (56.0, "very poor"),
           (65.0, "very poor"), (66.0, "very, very poor"), (80.0, "very, very poor")]
    assert len(exp) == 16
    bad = [(a, G.powder_flowability_class(a)["cls"], cl) for a, cl in exp if G.powder_flowability_class(a)["cls"] != cl]
    gate("門 12 流動性区分の境界 16 点(表は整数の度: 30.4 → excellent、30.5 → good)",
         not bad and G.powder_flowability_class(24.0)["tabulated"] is False and G.powder_flowability_class(25.0)["tabulated"] is True
         and _raises(G.powder_flowability_class, 0.0) and _raises(G.powder_flowability_class, 90.0),
         "24 度は表の外(tabulated=False)、0 / 90 → ValueError%s" % ("" if not bad else "; 違う: %r" % bad))

    # ── 門 13 綴り壊し
    w0 = G.heap_synth_cone(30.0, 200)
    gate("門 13 綴り壊しは ValueError", _raises(G.repose_angle_heightmap, w0["heightmap"], w0["pitch"], method="Horn")
         and _raises(G.repose_angle_silhouette, w0["side"], method="edges") and _raises(G.heap_synth_cone, 30.0, 200, ground_tilt_deg=60.0)
         and _raises(G.cone_profile_px, [0.0], 10.0, 30.0, toe_round_px=50.0, apex_blunt_px=50.0)
         and _raises(G.heap_scene_mjcf, 10, 0.004, solver="newton") and _raises(G.heap_scene_mjcf, 10, 0.004, cone="Elliptic"),
         "method='Horn' / 'edges'、基準面 60 度、円弧の重なり、solver='newton'、cone='Elliptic'")
    # ── 門 14 山が写っていない / 切れている
    blank = np.zeros((64, 96))
    cut = w0["side"][int(w0["side"].shape[0] * 0.5):, :]
    edge = w0["side"][:, int(w0["truth"]["apex_col"]):]
    gate("門 14 山が写っていない・切れている → ValueError(黙って測らない)",
         _raises(G.repose_angle_silhouette, blank) and _raises(G.repose_angle_silhouette, cut) and _raises(G.repose_angle_silhouette, edge)
         and _raises(G.repose_angle_heightmap, np.zeros((64, 64)), 1e-3) and _raises(G.container_fill_level, blank)
         and _raises(G.repose_angle_silhouette, w0["side"] * 2.0),
         "空 / 頂が上縁で切れる / 左縁で切れる / 平らな高さ図 / 空の容器 / 被覆率 > 1")

    # ── 門 15 スプーン
    thc0 = G.spoon_tilt_critical(30.0, 0.05, 1e-7)
    thc = G.spoon_tilt_critical(30.0, 0.05, 0.005)
    fr = [G.spoon_tilt_dispense(th, 30.0, 0.05, 0.005)["fraction"] for th in np.linspace(0.0, 45.0, 91)]
    assert len(fr) == 91
    mono = all(b >= a - 1e-12 for a, b in zip(fr[:-1], fr[1:]))
    fo = [G.spoon_tilt_dispense(th, 30.0, 0.05, 0.005, lip="open")["fraction"] for th in np.linspace(0.0, 45.0, 91)]
    assert len(fo) == 91
    old = math.degrees(math.atan(math.tan(math.radians(30.0)) - 0.2))     # 2026-10-05 までの小角の近似
    gate("門 15 スプーンの規則 θ_c = φ − atan(2h₀/L)(楔の傾きは厳密な tan(φ − θ))、口に壁の無い器は θ = 0⁺ からこぼれる",
         abs(thc0 - 30.0) < 1e-3 and mono
         and abs(thc - (30.0 - math.degrees(math.atan(0.2)))) < 1e-9
         and G.spoon_tilt_dispense(thc - 0.5, 30.0, 0.05, 0.005)["fraction"] == 0.0
         and G.spoon_tilt_dispense(30.0, 30.0, 0.05, 0.005)["fraction"] == 1.0
         and fo[0] == 0.0 and fo[1] > 0.0 and fo[60] == 1.0 and all(b >= a - 1e-12 for a, b in zip(fo[:-1], fo[1:])),
         "h₀ → 0 で θ_c = %.4f(= φ)、L 50 mm・h₀ 5 mm で %.2f 度(2026-10-05 までの小角の近似 tan φ − tan θ では %.2f 度)、θ_c の手前で 0・φ で 1・単調 %s; "
         "口に壁の無い器は 0.5 度で %.3f 出る" % (thc0, thc, old, mono, fo[1]))
    out["thc"] = thc

    # ── 門 16 容器の充填率
    cs = G.container_synth(0.63, 3.0)
    cf = G.container_fill_level(cs["side"])
    gate("門 16 容器の充填率(0.63、粉面の傾き 3 度)", abs(cf["fill_frac"] - 0.63) < 0.002 and abs(cf["surface_tilt_deg"] - 3.0) < 0.05,
         "充填率 %.4f(門 0.002)、傾き %.3f 度(門 0.05)" % (cf["fill_frac"], cf["surface_tilt_deg"]))

    # ── 門 17 動画からの質量と排出率の帯当て
    ds = G.discharge_synth(0.03, 0.001, 1500.0, 30.0, 1.5e-3, 2.0, n_frames=6, grid=256)
    m = G.dispense_mass_from_video(ds["frames"], 1.5e-3, 1500.0, ds["times"])
    e17 = max(abs(m["rate"] / ds["W"] - 1), abs(m["masses"][-1] / ds["masses"][-1] - 1))
    t = np.linspace(0.0, 2.0, 11)
    band = G.hopper_discharge_rate(0.5 * t, t, 1.0)
    gate("門 17 動画からの質量(雑音なし)と排出率の帯当て", e17 < 1e-4 and abs(band["rate"] - 0.5) < 1e-12 and band["n_frames"] == 5
         and _raises(G.hopper_discharge_rate, np.array([0.0, 0.5, 1.0]), np.array([0.0, 1.0, 2.0]), 1.0),
         "率と最終質量の相対誤差 %.1e(門 1e-4; 同じ円錐を両辺に入れるので配管の検査だけ)、20〜80 %% の帯 %d コマで 0.5 kg/s、帯に 1 コマ → ValueError"
         % (e17, band["n_frames"]))

    # ── 門 18 MJCF 文字列(mujoco 不要)
    sc_ = G.heap_scene_mjcf(60, 0.004, seed=1)
    gate("門 18 MJCF 文字列(mujoco 不要): 球 60・壁 24 + 底板 4・平面 1", sc_["xml"].count("<freejoint/>") == 60
         and sc_["xml"].count('type="box"') == 28 and sc_["xml"].count('type="plane"') == 1
         and _raises(G.heap_scene_mjcf, 60, 0.004, contact_tc=0.002, timestep=0.0015) and _raises(G.heap_scene_mjcf, 60, 0.004, orifice_d=0.2),
         "軟接触の時定数 < 2·timestep(発散した実測)と孔がビンに収まらない → ValueError")

    # ── 門 19 入口の棚卸し
    missing = [n for n in G.__all__ if not hasattr(G, n)]
    bad_doc = [n for n in G.__all__ if callable(getattr(G, n, None))
               and ("](" in (getattr(G, n).__doc__ or "") or not (getattr(G, n).__doc__ or "").strip())]
    gate("門 19 入口: __all__ が実在し、docstring があり Markdown のリンク記法を含まない", not missing and not bad_doc,
         "%d 名%s" % (len(G.__all__), "" if not (missing or bad_doc) else "; %r %r" % (missing, bad_doc)))
    dt = time.perf_counter() - t0
    # 単独 1.3 s、全体スイートの 8 並列の中では 3.3 s(実測、3 s の門が負荷で鳴った)。共有ランナーの遅さも見込んで 15 s。
    gate("門 20 既定の門の所要 ≤ 15 s", dt <= 15.0, "%.2f s(単独の実測 1.3 s)" % dt)
    return out


# ======================================================================================================================
def full_part(out: dict) -> dict:
    print("== 2. MuJoCo の門(剛体球 1,200 個の山 = 第 2 実装)")
    t0 = time.perf_counter()
    r = G.heap_mujoco_pour()
    info = r["model_info"]
    pitch, extent, height = 0.0015, 0.16, 0.07
    sel = G.heap_spheres_select(r["pos"], r["radius"], info["orifice_height"], info["bin_radius"])
    heap = sel["pos"]
    gate("門 21 山ができた(逃げ < 5 %、最終速度 < 0.3 m/s、高さ > 6 R)",
         sel["n_runaway"] < 0.05 * info["n"] and info["max_speed_end"] < 0.3 and heap[:, 2].max() > 6 * r["radius"],
         "%d 球(r %.0f mm): ビンに残り %d(平底の滞留層)、逃げ %d、最終速度 %.3f m/s、高さ %.1f mm = %.1f 粒径、半径 95 %% %.0f mm"
         % (info["n"], r["radius"] * 1e3, sel["n_in_bin"], sel["n_runaway"], info["max_speed_end"], heap[:, 2].max() * 1e3,
            heap[:, 2].max() / (2 * r["radius"]), sel["radius_95"] * 1e3))
    phis, sils = [], []
    for az in (0.0, 45.0, 90.0, 135.0):
        a = math.radians(az)
        R = np.array([[math.cos(a), -math.sin(a), 0.0], [math.sin(a), math.cos(a), 0.0], [0.0, 0.0, 1.0]])
        sil = G.spheres_to_silhouette(heap @ R.T, r["radius"], pitch, extent, height)
        s = G.repose_angle_silhouette(sil, toe_frac=0.2, apex_frac=0.2)
        phis.append(s["phi_deg"])
        sils.append((sil, s))
    assert len(phis) == 4
    phi_s = float(np.mean(phis))
    pub = G.GLASS_BEADS_REPOSE_PUBLISHED
    gate("門 22 MuJoCo の φ vs 公表値 25.2 ± 0.8 度(1 mm ガラス球)", -7.0 < phi_s - pub["phi_deg"] < 1.0,
         "側面 4 方位 %s の平均 %.2f 度、差 %+.2f 度(門 −7〜+1; 剛体球・転がりの模型・山が 5 粒径 —— 低い側に出るのは既知、高く出たら別の異常)"
         % ([round(v, 1) for v in phis], phi_s, phi_s - pub["phi_deg"]))
    hm = G.spheres_to_heightmap(heap, r["radius"], pitch, extent)
    k = 2 * int(round(2 * r["radius"] / pitch)) + 1
    h = G.repose_angle_heightmap(hm, pitch, bin_deg=1.0, min_rel_height=0.2, max_rel_height=0.8, smooth_cells=k)
    h_raw = G.repose_angle_heightmap(hm, pitch, bin_deg=1.0, min_rel_height=0.2, max_rel_height=0.8)
    gate("門 23 高さ図(2 粒径で平滑、中央値)vs 側面", abs(h["phi_median_deg"] - phi_s) < 4.0,
         "高さ図 %.2f 度(最頻 %.1f、平滑なしの最頻 %.1f = 球の縁)vs 側面 %.2f: 差 %+.2f(門 4)"
         % (h["phi_median_deg"], h["phi_deg"], h_raw["phi_deg"], phi_s, h["phi_median_deg"] - phi_s))
    dr = G.hopper_discharge_rate(r["mass_below"], r["times"], info["mass_total"])
    Deq = math.sqrt(4.0 / math.pi) * info["orifice_d"]
    Wb = G.beverloo_rate(Deq, 2 * r["radius"], info["bulk_density_bin"])
    gate("門 24 排出率 vs Beverloo(正方孔は等価直径)", 0.5 < dr["rate"] / Wb < 2.0,
         "%.3f kg/s vs %.3f kg/s(D_eq %.1f mm、d %.0f mm、ρ_b %.0f kg/m³ はビンの実測)= 比 %.2f(門 0.5〜2 = 桁だけ; D₀/d = %.1f は詰まりの限界付近、"
         "帯のコマ %d)" % (dr["rate"], Wb, Deq * 1e3, 2 * r["radius"] * 1e3, info["bulk_density_bin"], dr["rate"] / Wb, Deq / (2 * r["radius"]), dr["n_frames"]))
    dt = time.perf_counter() - t0
    gate("門 25 --full の所要 ≤ 60 s", dt <= 60.0, "%.1f s(シミュ %.1f s、%d 歩 × %.1f ms)" % (dt, r["elapsed_s"], info["steps"], info["timestep"] * 1e3))
    out.update(mj=r, mj_heap=heap, mj_sils=sils, mj_phi=phi_s, mj_phis=phis, mj_hm=hm, mj_h=h, mj_h_raw=h_raw, mj_rate=dr, mj_Wb=Wb, mj_Deq=Deq,
               mj_extent=extent, mj_height=height, mj_pitch=pitch)
    return out


# ======================================================================================================================
def _figures_numpy(out: dict) -> None:
    # 01 側面像に 2 直線(主図、等倍、幅 ≈ 880 px)
    w = G.heap_synth_cone(32.0, 420, noise=0.05, seed=4, margin_px=80)
    s = G.repose_angle_silhouette(w["side"])
    figs.save("granular_heap_side_view_two_lines", _draw_fit(w["side"], s, 32.0, "synthetic heap, coverage noise +-0.05, 1:1", ref_label="truth"),
              caption="合成の側面像(粉の被覆率、雑音 ±0.05、等倍)。黄 = 当てた範囲(裾 15 %%・頂 15 %% を外す)、橙 = その延長、青 = 地面。"
                      "φ = %.3f 度(真値 32)。縁の画素の被覆率をそのまま副画素の位置に読む。" % s["phi_deg"])
    # 02 勾配ヒストグラム
    w0 = G.heap_synth_cone(30.0, 200)
    h0 = G.repose_angle_heightmap(w0["heightmap"], w0["pitch"])
    hm = w0["heightmap"] + np.random.default_rng(7).normal(0.0, 0.1 * w0["pitch"], w0["heightmap"].shape)
    h1 = G.repose_angle_heightmap(hm, w0["pitch"])
    sl = (h0["hist_centers"] > 22) & (h0["hist_centers"] < 40)
    figs.save_plot("granular_slope_histogram",
                   [("noiseless heightmap (mode %.2f)" % h0["phi_deg"], h0["hist_centers"][sl], h0["hist_counts"][sl] / h0["hist_counts"].max()),
                    ("height noise 0.1 px (mode %.2f)" % h1["phi_deg"], h1["hist_centers"][sl], h1["hist_counts"][sl] / h1["hist_counts"].max()),
                    ("truth 30 deg", np.array([30.0, 30.0]), np.array([0.0, 1.0]))],
                   xlabel="slope [deg]", ylabel="count (normalised)", title="dem_slope histogram of the 10-90 % height band", size=(760, 440),
                   styles=[None, None, "dashed"], colors=["emphasis", "neutral", "reference"],
                   caption="高さ図の勾配ヒストグラム(demops.dem_slope)。雑音なしは 1 ビンに立つ。σ = 0.1 px の雑音で最頻が %+.2f 度ずれる"
                           "(|∇| は雑音で増えるだけ)—— 同じ大きさの雑音で側面像は 0.01 度も動かない。" % (h1["phi_deg"] - 30.0))
    # 03 分解能で壊れる場所
    widths = np.array([25, 35, 50, 70, 100, 200, 400])
    es_m, eh_m = [], []
    for wd_ in widths:
        es, eh = [], []
        for seed in range(8):
            for phi in (25.0, 35.0):
                ww = G.heap_synth_cone(phi, wd_ / 2, noise=0.1, seed=seed)
                es.append(abs(G.repose_angle_silhouette(ww["side"])["phi_deg"] - phi))
                hh = ww["heightmap"] + np.random.default_rng(seed).normal(0.0, 0.1 * ww["pitch"], ww["heightmap"].shape)
                eh.append(abs(G.repose_angle_heightmap(hh, ww["pitch"])["phi_deg"] - phi))
        assert len(es) == 16
        es_m.append(max(es))
        eh_m.append(max(eh))
    lx = np.log2(widths)
    figs.save_plot("granular_where_it_breaks_resolution",
                   [("side view, coverage noise +-0.1", lx, np.array(es_m)), ("heightmap, height noise 0.1 px", lx, np.array(eh_m)),
                    ("gate at 50 px (side view 0.3 deg)", np.array([lx[0], lx[-1]]), np.array([0.3, 0.3]))],
                   xlabel="log2 of the heap width in px (25 ... 400)", ylabel="max |phi error| [deg]", title="Where it breaks: resolution",
                   size=(760, 440), styles=[None, None, "dashed"], colors=["emphasis", "neutral", "reference"],
                   caption="山の幅(画素)と φ の最大誤差(2 角度 × 8 seed)。側面像は 50 px で %.2f 度、25 px で %.2f 度。高さ図は雑音で上にずれるので"
                           " 400 px でも %.2f 度残る。台帳の問い「山が 50 px のとき何度」の答え。" % (es_m[2], es_m[0], eh_m[-1]))
    # 04〜07 壊れ方 4 枚(等倍、幅 ≈ 880 px)
    wt = G.heap_synth_cone(30.0, 400, toe_round_px=120, noise=0.1, seed=0, margin_px=80)
    st = G.repose_angle_silhouette(wt["side"], toe_frac=0.0, apex_frac=0.0)
    st2 = G.repose_angle_silhouette(wt["side"])
    figs.save("granular_breaks_toe_rounding_view", _draw_fit(wt["side"], st, 30.0, "toe filled by a 120 px arc, fitted without exclusion", ref_label="truth"),
              caption="裾を円弧(r = 120 px、底 800 px)で埋めた山を裾ごと当てると %+.3f 度。裾 15 %% を外せば %+.3f 度。"
                      % (st["phi_deg"] - 30.0, st2["phi_deg"] - 30.0))
    wa = G.heap_synth_cone(30.0, 400, apex_blunt_px=120, noise=0.1, seed=0, margin_px=80)
    sa = G.repose_angle_silhouette(wa["side"], toe_frac=0.0, apex_frac=0.0)
    sa2 = G.repose_angle_silhouette(wa["side"])
    figs.save("granular_breaks_apex_blunting_view", _draw_fit(wa["side"], sa, 30.0, "apex blunted by a 120 px arc, fitted without exclusion", ref_label="truth"),
              caption="頂を円弧(r = 120 px)で削った山を頂ごと当てると %+.3f 度。頂 15 %% を外せば %+.3f 度。" % (sa["phi_deg"] - 30.0, sa2["phi_deg"] - 30.0))
    wd = G.heap_synth_cone(30.0, 400, ground_tilt_deg=5.0, margin_px=80)
    sd = G.repose_angle_silhouette(wd["side"])
    dd = G.datum_tilt_check(sd)
    figs.save("granular_breaks_tilted_datum_view", _draw_fit(wd["side"], sd, 30.0, "datum tilted by 5 deg (shear)", ref_label="truth"),
              caption="基準面が 5 度傾くと左右が %.2f / %.2f 度に割れる(atan(tan φ ± tan β))。左右差 %.2f 度が警報、tan の引き算で %.3f 度に戻る。"
                      % (sd["phi_left_deg"], sd["phi_right_deg"], dd["asymmetry_deg"], dd["phi_shear_deg"]))
    ws = G.heap_synth_cone(30.0, 25, noise=0.1, seed=1)
    ss = G.repose_angle_silhouette(ws["side"])
    figs.save("granular_breaks_small_heap_view", _draw_fit(ws["side"], ss, 30.0, "50 px heap, x10 nearest (pixels visible)", scale=10, ref_label="truth"),
              caption="幅 50 px の山(10 倍の最近傍拡大で画素が見える)。雑音 ±0.1 で φ = %.2f 度(真値 30)。" % ss["phi_deg"])
    # 08 Beverloo
    D0, Wm, fb = out["g06_D0"], out["g06_W"], out["g06"]
    Dc = np.linspace(0.016, 0.055, 80)
    figs.save_plot("granular_beverloo_W_vs_D0",
                   [("Beverloo 1961, C 0.58, k 1.4", Dc * 1e3, np.array([G.beverloo_rate(x, 0.001, 1500.0) for x in Dc])),
                    ("read from synthetic heightmap video (noise 0.5 mm)", D0 * 1e3, Wm)],
                   xlabel="orifice D0 [mm]", ylabel="W [kg/s]", title="W = C rho_b sqrt(g) (D0 - k d)^2.5", size=(760, 440),
                   kinds=["line", "scatter"], styles=["dashed", None], colors=["reference", "emphasis"],
                   caption="合成排出の高さ図の列(6 コマ)から体積の傾きで読んだ率(点)と閉形式(破線)。対数当ての指数 n = %.4f、C = %.4f。" % (fb["n"], fb["C"]))
    # 09 流動性の帯
    img = np.full((330, 1000, 3), 0.97)

    def x_of(a):
        return int(50 + (a - 18) * 900 / 54)
    img = _text(img, "USP <1174> Table 1 (Carr 1965): flow property vs angle of repose [deg]", (50, 10), fs=18)
    bands = [(25, 30, (0.55, 0.85, 0.55)), (30, 35, (0.70, 0.88, 0.55)), (35, 40, (0.90, 0.90, 0.55)), (40, 45, (0.95, 0.80, 0.50)),
             (45, 55, (0.95, 0.65, 0.45)), (55, 65, (0.90, 0.50, 0.45)), (65, 72, (0.75, 0.40, 0.45))]
    names = ["excellent", "good", "fair", "passable", "poor", "very poor", "v.v. poor"]
    for (lo, hi, col), nm in zip(bands, names):
        img[150:225, x_of(lo):x_of(hi)] = col
        img = _text(img, nm, (x_of(lo) + 4, 175), fs=14)
    for a in range(20, 73, 5):
        img[225:233, x_of(a):x_of(a) + 2] = 0.2
        img = _text(img, str(a), (x_of(a) - 10, 238), fs=14)
    marks = [("glass beads 25.2 +- 0.8 (arXiv:2009.10448, 1 mm, published)", 25.2, (0.1, 0.3, 0.9))]
    if out.get("mj_phi") is not None:
        marks.append(("MuJoCo rigid spheres %.1f (this run)" % out["mj_phi"], out["mj_phi"], (0.85, 0.2, 0.2)))
    for i, (lab, a, col) in enumerate(marks):
        x = x_of(a)
        img[78 + 32 * i:228, x - 1:x + 2] = col
        img = _text(img, lab, (x + 8, 50 + 32 * i), fs=15)
    img = _text(img, "below 25 deg: outside the table (returned with tabulated=False)", (50, 285), fs=15)
    figs.save("granular_flowability_bands", img,
              caption="安息角 → 流動性区分(USP <1174> 表 1、原典 Carr 1965)。表は整数の度なので四捨五入して引く。25 度未満は表の外。")
    # 10 スプーンの傾け
    th = np.linspace(0.0, 34.0, 171)
    ser, sty, col = [], [], []
    for h0_ in (0.002, 0.005, 0.010):
        ser.append(("h0 = %.0f mm (theta_c %.1f deg)" % (h0_ * 1e3, G.spoon_tilt_critical(30.0, 0.05, h0_)), th,
                    np.array([G.spoon_tilt_dispense(t_, 30.0, 0.05, h0_)["fraction"] for t_ in th])))
        sty.append(None)
        col.append(None)
    ser.append(("h0 = 5 mm, no lip wall (spills from 0)", th,
                np.array([G.spoon_tilt_dispense(t_, 30.0, 0.05, 0.005, lip="open")["fraction"] for t_ in th])))
    sty.append("dotted")
    col.append(None)
    ser.append(("phi = 30 deg (all out)", np.array([30.0, 30.0]), np.array([0.0, 1.0])))
    sty.append("dashed")
    col.append("reference")
    figs.save_plot("granular_spoon_tilt_dispense", ser, xlabel="spoon tilt [deg]", ylabel="fraction dispensed", size=(760, 440),
                   title="Spoon rule: theta_c = phi - atan(2 h0 / L), L = 50 mm", styles=sty, colors=col,
                   caption="スプーンを傾けたときに出る割合(2 次元断面・準静的・自分の導出、楔の傾きは厳密な tan(φ − θ))。盛りが多いほど早くこぼれ始め、"
                           "θ = φ で全部出る。L 50 mm・h₀ 5 mm で θ_c = %.2f 度(2026-10-05 までの小角の近似では 20.67 度)。点線 = 口に壁の無い器"
                           "(前面が初めから安息角の斜面)は θ = 0⁺ からこぼれる。" % out["thc"])
    # 11 GIF: 基準面の傾きを振る
    frames = []
    betas = [float(b) for b in np.arange(-8.0, 8.01, 1.0)]
    betas = betas + betas[-2:0:-1]
    for b in betas:
        wb = G.heap_synth_cone(30.0, 300, ground_tilt_deg=b, margin_px=110)
        sb = G.repose_angle_silhouette(wb["side"])
        db = G.datum_tilt_check(sb)
        state = ("ALARM: left - right = %.1f deg" % db["asymmetry_deg"]) if db["alarm"] else "no alarm"
        im = _draw_fit(wb["side"], sb, None, "datum tilt beta = %+.0f deg   %s" % (b, state))
        im = _text(im, "tan-corrected phi = %.2f deg   (truth 30)" % db["phi_shear_deg"], (8, 68))
        frames.append(im)
    assert len(frames) >= 30
    frames = _pad_top(frames)
    figs.save_gif("granular_datum_tilt_sweep", [(np.clip(f, 0, 1) * 255).astype(np.uint8) for f in frames], fps=4.0,
                  caption="基準面の傾き β を −8〜+8 度で振る(%d コマ)。左右の斜面が atan(tan φ ± tan β) で割れ、左右差 ≈ 2β が 1 度を超えると警報。"
                          "tan の引き算で 30 度に戻る。" % len(frames))


def _flow_label(phi):
    """流動性区分の表示。25 度未満は表の外なので区分名を出さない(excellent と書くと嘘になる)。"""
    c = G.powder_flowability_class(phi)
    return c["cls"] if c["tabulated"] else "below the table (< 25 deg)"


def _bin_outline(img, info, extent, height, p):
    """GIF のコマにビンの壁と底板(正方孔の切れ目つき)を描く(球だけだと浮いて見える)。"""
    def rc(x, z):
        return ((height - z) / p, (x + extent) / p)
    Rb, zf, D0, top = info["bin_radius"], info["orifice_height"], info["orifice_d"], info["column_top"]
    zc = zf - info["plate_thickness"]
    col = (0.45, 0.55, 0.70)
    for x0, x1 in ((-Rb, -0.5 * D0), (0.5 * D0, Rb)):
        _line(img, rc(x0, zc), rc(x1, zc), col, 1.5)
    for x in (-Rb, Rb):
        _line(img, rc(x, zc), rc(x, top), col, 1.5)
    return img


def _figures_mujoco(out: dict) -> None:
    # 12 GIF: 球の山ができる
    r, info = out["mj"], out["mj"]["model_info"]
    extent = out["mj_extent"]
    fr_all = r["frames"]
    step = max(1, len(fr_all) // 40)
    gif = []
    for i in range(0, len(fr_all), step):
        im = _bin_outline(G.spheres_render_shaded(fr_all[i], r["radius"], 0.0005, extent, 0.26), info, extent, 0.26, 0.0005)
        im = _text(im, "t = %.2f s   discharged %.0f g of %.0f g" % (r["times"][i], r["mass_below"][i] * 1e3, info["mass_total"] * 1e3), (8, 8), fs=16)
        gif.append((np.clip(im, 0, 1) * 255).astype(np.uint8))
    assert len(gif) >= 10
    figs.save_gif("granular_mujoco_heap_render_settling", gif, fps=10.0,
                  caption="剛体球 %d 個(r %.0f mm、滑り摩擦 0.16、転がり 0.09·R、粗い台)が平底ホッパ(青灰の線 = 壁と底板)の正方孔(48 mm)から流れて山になる"
                          "(0.5 mm/px、%d コマ)。φ = %.2f 度(4 方位の平均)。" % (info["n"], r["radius"] * 1e3, len(gif), out["mj_phi"]))
    # 13 側面の当てはめ + 公表値の線
    sil, s0 = out["mj_sils"][0]
    pub = G.GLASS_BEADS_REPOSE_PUBLISHED
    shaded = G.spheres_render_shaded(out["mj_heap"], r["radius"], out["mj_pitch"] / 6.0, extent, out["mj_height"])
    figs.save("granular_mujoco_side_fit_view",
              _draw_fit(sil, s0, pub["phi_deg"], "MuJoCo rigid spheres, azimuth 0 (cyan dashed = published 25.2 deg)",
                        background=shaded, ref_phi=pub["phi_deg"], ref_label="published"),
              caption="球の山の側面(陰影つき正射影、0.25 mm/px)に、被覆率の側面像で当てた 2 直線(黄)と公表値 25.2 度の斜面(水色の破線)を重ねる。"
                      "この方位で φ = %.2f 度。4 方位 %s。" % (s0["phi_deg"], ", ".join("%.1f" % v for v in out["mj_phis"])))
    # 14 高さ図
    figs.save("granular_mujoco_heightmap", np.kron(out["mj_hm"] * 1e3, np.ones((3, 3))),
              caption="同じ山の高さ図(単位 mm、球面の最大高さ、1.5 mm/セルを 3 倍の最近傍で表示)。2 粒径で平滑してから dem_slope: 中央値 %.2f 度"
                      "(平滑なしの最頻 %.1f 度 = 球の縁)。" % (out["mj_h"]["phi_median_deg"], out["mj_h_raw"]["phi_deg"]))
    # 15 排出の質量の列
    dr, Wb = out["mj_rate"], out["mj_Wb"]
    tt, mb = r["times"], r["mass_below"]
    t0_, t1_ = dr["t_range"]
    selb = (tt >= t0_) & (tt <= t1_)
    figs.save_plot("granular_mujoco_discharge",
                   [("mass below the floor (MuJoCo)", tt, mb * 1e3),
                    ("fitted 20-80 %% band: %.3f kg/s" % dr["rate"], tt[selb], (mb[selb][0] + dr["rate"] * (tt[selb] - tt[selb][0])) * 1e3),
                    ("Beverloo (D_eq %.1f mm): %.3f kg/s" % (out["mj_Deq"] * 1e3, Wb), tt[selb], (mb[selb][0] + Wb * (tt[selb] - tt[selb][0])) * 1e3)],
                   xlabel="t [s]", ylabel="mass [g]", title="Hopper discharge: MuJoCo vs Beverloo", size=(760, 440),
                   styles=[None, None, "dashed"], colors=["neutral", "emphasis", "reference"],
                   caption="底板より下の質量。中央 20〜80 %% の帯(%d コマ)の傾き %.3f kg/s、Beverloo(正方孔を等価直径に)%.3f kg/s、比 %.2f —— 桁の照合だけ。"
                           % (dr["n_frames"], dr["rate"], Wb, dr["rate"] / Wb))
    # 16 表: MuJoCo と外の真値
    hdr = ["quantity", "this run (MuJoCo)", "outside reference", "difference", "gate"]
    rows = [["angle of repose, side view [deg]", "%.2f" % out["mj_phi"], "25.2 +- 0.8 (1 mm glass, arXiv:2009.10448)",
             "%+.2f" % (out["mj_phi"] - 25.2), "-7 .. +1"],
            ["angle of repose, heightmap median [deg]", "%.2f" % out["mj_h"]["phi_median_deg"], "side view %.2f" % out["mj_phi"],
             "%+.2f" % (out["mj_h"]["phi_median_deg"] - out["mj_phi"]), "|d| < 4"],
            ["discharge rate [kg/s]", "%.3f" % dr["rate"], "Beverloo %.3f (D_eq %.1f mm)" % (Wb, out["mj_Deq"] * 1e3), "ratio %.2f" % (dr["rate"] / Wb), "0.5 .. 2"],
            ["flowability class (USP <1174>)", _flow_label(out["mj_phi"]), _flow_label(25.2) + " (published)", "-", "-"]]
    figs.save_table("granular_mujoco_vs_references", hdr, rows, title="MuJoCo rigid-sphere heap vs the outside references",
                    caption="第 2 実装(MuJoCo の剛体球)と外の真値。安息角は公表値より %.1f 度低い(剛体・付着なし・転がりの模型・山が 5 粒径 —— 切り分けていない)。"
                            % (25.2 - out["mj_phi"]))


def figures(out: dict) -> None:
    print("== 図")
    _figures_numpy(out)
    if "mj" in out:
        _figures_mujoco(out)
    else:
        print("  図 12〜16 は --full(MuJoCo)のときだけ")
    print("  figures:", figs.errors() or "ok")


# ======================================================================================================================
def main() -> int:
    t_all = time.time()
    out = numpy_part()
    if FULL:
        out = full_part(out)
    else:
        skip("門 21〜25(MuJoCo)", "--full のときだけ(mujoco)")
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
