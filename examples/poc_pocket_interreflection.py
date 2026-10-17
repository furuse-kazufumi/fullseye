# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 加工ポケットの相互反射を収束まで数える —— 直接光だけのモデルは「あり得ない反射率」で合い、収束解は真値に戻る。

【問い】凹んだ部品(加工ポケット・内角・V 溝)の画像に、直接光だけの物理モデルを合わせると何が起きるか。
向かいの壁で反射した光が底を照らす分(相互反射)はモデルに無いので、その明るさは**反射率や照明の強さに
吸収されて、もっともらしく合ってしまう**。新 op 7 本(``radiosity3d``、``opsoptics`` の族 ``radiosity``)の
検査用の多重反射描画 ``render_optscene_gi`` で、同じシーン・同じ照明のまま「直接光だけ / 1 回反射 / 収束解」の
3 つのモデルを作り、sim-to-real 較正の族 ``simcal``(``simcal_fit`` / ``simcal_validate`` /
``simcal_discrepancy``)で反射率と照明の強さを合わせる。収蔵番号は仮(統合で振る)。6 章:

  1. **形態係数の門**: Howell のカタログの表の値(C-11 の 0.199825、C-14 の 0.200044)を閉形式の op が 6 桁で再現し、
     数値の ``form_factor_polygons`` が閉形式と一致する。閉じた立方体の行和 = 1。
  2. **漸進ラジオシティの門**: Cohen ら 1988 の shooting(式 7・8)が逆行列の解と一致し、残エネルギーが減るだけ。
     止める閾値は Cohen が数で決めていないので、残エネルギー Σ ΔB·A ≤ tol × 初期のエネルギー、が**こちらの判断**。
  3. **描画の門**: 反射 0 回の ``render_optscene_gi`` が ``render_optscene``(直接光だけの検査用描画)と一致する
     —— 測光の真値を 1 桁も変えずに反射を足している。パッチの細かさ(1.5 / 1.0 / 0.7 mm)を振り、細かい真値との
     差が雑音の何割かを数える(反射の回数だけでなく、メッシュも収束させる)。
  4. **何回数えれば足りるか**: 反射 0〜12 回の像の増分、隣り合う増分の比(観測収束比 —— 等比級数なので Roache の
     観測収束次数 p の代わり)、GCI 型の残りの見積もり 1.25·Δ_k g/(1 − g) と、収束解との実際の誤差。雑音の大きさを
     許容値にして、必要な反射の回数を返す。見積もりを信じるのは漸近域(観測収束比が 2 回続けて 5 % 以内でしか
     動かない回)だけ —— その前の k = 3 では見積もりが実際の差を下回った(楽観した)ので、それも印字する。
  5. **較正**: 白っぽい部品(反射率 0.7)のポケットを、ドーム照明・EMVA 1288 の線形カメラ(ポアソンの電子 + 読み出し
     雑音 + 丸め、物理の経路)で撮った合成の観測と、反射率の分かった灰色の板(0.5)の観測に、3 つのモデルを合わせる。
     見せ場: 直接光だけのモデルは**反射率 > 1(エネルギー保存に反する)**で合い、残差は雑音の数十倍・残差 PCA は
     凹みの構造を検出 → 不合格。1 回反射は中間。収束解は反射率・照明の強さが真値に戻り、残差は白色で全部の門を通る。
  6. **実データとの照合(数値の引用)**: Bulczak, Lambers, Kolb 2018 の表 2(実測の凹んだ 3 形状 x 2 材料で、
     直接光だけのシミュレーションと 1 回反射込みの MAE)。1 回反射を足すと誤差が 0.20〜0.47 倍になる —— 本 PoC の
     強度画像の同じ比と並べる(向こうは ToF の距離、こちらは強度なので、比べるのは「直接光だけでは足りない量」の比)。

【外部真値】Howell のカタログの表の値、逆行列の解、``render_optscene``(別の op)、細かいメッシュの収束解、
合成の観測の真値(作った反射率・照明の強さ)、Bulczak ら 2018 の表 2(実測)。【学習】0。【較正】反射率と照明の強さ。

【来歴】M. F. Cohen, S. E. Chen, J. R. Wallace, D. P. Greenberg, "A Progressive Refinement Approach to Fast Radiosity
Image Generation", SIGGRAPH '88 / J. R. Howell, "A Catalog of Radiation Heat Transfer Configuration Factors"(C-11, C-14)
/ P. J. Roache, J. Fluids Eng. 116 (1994)(安全係数 1.25)/ D. Bulczak, M. Lambers, A. Kolb, "Quantified, Interactive
Simulation of AMCW ToF Camera Including Multipath Effects", Sensors 18(1):13, 2018, https://doi.org/10.3390/s18010013 ,
© 2017 by the authors, CC BY 4.0(https://creativecommons.org/licenses/by/4.0/)。表 2 の MAE の値を改変せずに数値として
引用し、比は本 PoC が計算した。論文の生データ(ToF の距離画像)は使っていない —— 今回は強度画像だけを扱う。

EXTEND: 鏡面の相互反射(``gi_render``、optional)、ToF の位相への影響(iToF の PoC で別に)、V 溝(傾いた面は optscene の
シーンに無い。押し出し形状なら ``lighttransport`` の 2-D と、多角形を直接渡す ``radiosity_patches(polygons=...)``)。

使い方:
    py -3.11 examples/poc_pocket_interreflection.py
    FULLSEYE_FIGURE_DIR=out/poc_pocket_interreflection py -3.11 examples/poc_pocket_interreflection.py   # 図も
"""
from __future__ import annotations

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import illumdesign as ID  # noqa: E402
import optscene as OS  # noqa: E402
import radiosity3d as R  # noqa: E402
import simcal  # noqa: E402
import simcalcheck  # noqa: E402
from metriccontract import MetricContractError  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"

FAILS: list[str] = []
GATES: list[str] = []

#: Howell のカタログの表の値(C-11: X = Y = 1、C-14: H = W = 1)。
HOWELL_C11, HOWELL_C14 = 0.199825, 0.200044
#: 合成の観測の真値。部品は白っぽい樹脂(反射率 0.7)、基準の板は反射率 0.5 の灰色。
RHO_TRUE, I_TRUE, RHO_REF = 0.7, 1.0, 0.5
#: EMVA 1288 の線形カメラ: 0.5 DN/電子、暗雑音 6 電子、黒レベル 64 DN。
K, SIGMA_D, DARK = 0.5, 6.0, 64.0
NOISE = {"kind": "emva", "K": K, "sigma_d": SIGMA_D, "dark": DARK}
#: 観測の乱数の種は先に決めておく(simcal の例と同じ日付の種、holdout は robust.py の流儀で + 10000)。
SEED = 20261015
#: パッチの大きさ [mm]。ポケットの内側だけ細かく、外側(何とも光を交わさない)は 3 mm。
PM_MODEL, PM_TRUTH, OUTER = 1.0, (0.7 if REDUCED else 0.5), 3.0
MESH_STUDY = (1.5, 1.0) if REDUCED else (1.5, 1.0, 0.7)
#: 所要の上限(この PoC 自身の CPU 時間)。
BUDGET_S = 240.0 if REDUCED else 420.0

#: Bulczak, Lambers, Kolb 2018, Sensors 18(1):13, 表 2 の MAE(CC BY 4.0、数値は改変なし)。
#: 列 = (形状, 材料)。材料 #1 は光沢のある白いアクリル板、#5 は拡散的な白い PVC 発泡板(論文の表 1)。
BULCZAK_COLS = (("Corner", "#1"), ("Corner", "#5"), ("CornerCube", "#1"), ("CornerCube", "#5"),
                ("CornerCubeShifted", "#1"), ("CornerCubeShifted", "#5"))
BULCZAK_DIRECT = (0.0885, 0.0884, 0.0728, 0.0688, 0.0846, 0.0777)
BULCZAK_SINGLE = (0.0238, 0.0200, 0.0194, 0.0138, 0.0396, 0.0342)
BULCZAK_SOURCE = ("D. Bulczak, M. Lambers, A. Kolb, Quantified, Interactive Simulation of AMCW ToF Camera Including "
                  "Multipath Effects, Sensors 18(1):13 (2018), doi:10.3390/s18010013, (c) 2017 the authors, CC BY 4.0 "
                  "(creativecommons.org/licenses/by/4.0) - Table 2 MAE values quoted unchanged; ratios computed here")

CAM = OS.optical_camera(focal_mm=12.0, pixel_um=27.6, resolution=(96, 96), working_distance_mm=200.0,
                        image_distance_mm=12.0 * 200.0 / 188.0)      # 3.45 µm の 8x8 ビニング、作動距離に合焦


def gate(name: str, ok: bool, detail: str = "") -> None:
    print("   [%s] %s%s" % ("ok" if ok else "NG", name, (" — " + detail) if detail else ""))
    GATES.append(name)
    if not ok:
        FAILS.append(name)


def part(rho):
    """反射率 rho の部品: 28 x 22 x 14 mm のブロックに 20 x 14 mm・深さ 10 mm のポケット。黒い台の上。"""
    m = OS.scene_material("lambert", albedo=rho)
    return [OS.scene_difference(OS.scene_box((0, 0, 7), (14, 11, 7), m), OS.scene_box((0, 0, 12), (10, 7, 8))),
            OS.scene_plane(0.0, OS.scene_material("lambert", albedo=0.0))]


def tile():
    """反射率の分かった基準の板(同じ外形のブロック、ポケットなし)。"""
    return [OS.scene_box((0, 0, 7), (14, 11, 7), OS.scene_material("lambert", albedo=RHO_REF)),
            OS.scene_plane(0.0, OS.scene_material("lambert", albedo=0.0))]


def light(intensity=1.0):
    return ID.light_source(kind="dome", radius_mm=60.0, n=160, intensity=intensity)


def render(intensity, rho, target, bounces, pm, study=0, tol=1e-6):
    sc = part(rho) if target == "part" else tile()
    return R.render_optscene_gi(sc, CAM, light(intensity), bounces=bounces, patch_mm=pm, outer_mm=OUTER,
                                study_bounces=study, tol=tol)


def emva_var(mu):
    return K * K * SIGMA_D ** 2 + 1.0 / 12.0 + K * np.maximum(mu - DARK, 0.0)


def capture(mus, seed):
    """物理の経路で撮る: 電子はポアソン、読み出し雑音、K 倍して黒レベルを足し、整数に丸める。"""
    rng = np.random.default_rng(seed)
    out = []
    for mu in mus:
        e = rng.poisson(np.maximum(mu - DARK, 0.0) / K)
        out.append(np.round(K * (e + SIGMA_D * rng.standard_normal(mu.shape)) + DARK))
    return out


# --------------------------------------------------------------------------- #
# 1-2. 形態係数と漸進ラジオシティ
# --------------------------------------------------------------------------- #
def chapter_form_factors():
    print("\n1. 形態係数(Howell の表)")
    c11, c14 = R.form_factor_parallel_rects(), R.form_factor_perpendicular_rects()
    sq0 = [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]]
    sq1 = [[0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]]
    wall = [[0, 0, 0], [0, 1, 0], [0, 1, 1], [0, 0, 1]]
    n11 = R.form_factor_polygons(sq0, sq1, n_quad=16)
    n14 = R.form_factor_polygons(sq0, wall, n_quad=16)
    print("   C-11: 閉形式 %.7f / 数値 %.7f / 表 %.6f" % (c11, n11, HOWELL_C11))
    print("   C-14: 閉形式 %.7f / 数値 %.7f / 表 %.6f" % (c14, n14, HOWELL_C14))
    gate("閉形式が Howell の表の 6 桁を再現", round(c11, 6) == HOWELL_C11 and round(c14, 6) == HOWELL_C14)
    gate("数値の形態係数が閉形式と一致", abs(n11 - c11) < 1e-6 and abs(n14 - c14) < 1e-6,
         "差 %.1e / %.1e" % (abs(n11 - c11), abs(n14 - c14)))


def chapter_progressive():
    print("\n2. 漸進ラジオシティ(Cohen ら 1988)")
    pt = R.radiosity_patches(scene=part(RHO_TRUE), patch_mm=PM_MODEL, outer_mm=OUTER)
    F = R.form_factor_matrix(pt)
    A = pt["areas"]
    E = np.where(pt["regions"] == "cavity", 1.0, 0.0) * (np.abs(pt["normals"][:, 2] - 1.0) < 1e-9)  # 底だけ光る
    sol = R.radiosity_progressive_3d(pt, E, form_factors=F, albedo=np.full(len(A), RHO_TRUE), tol=1e-10)
    Bx = np.linalg.solve(np.eye(len(A)) - RHO_TRUE * (F.T * A[None, :]) / A[:, None], E)
    err = float(np.abs(sol["radiosity"][:, 0] - Bx).max() / Bx.max())
    h = sol["unshot_history"]
    print("   パッチ %d 枚(ポケットの内側 %d)、%d 回撃って残エネルギー %.1e(収束 %s)"
          % (len(A), int((pt["regions"] == "cavity").sum()), sol["n_shots"], sol["residual_energy"], sol["converged"]))
    gate("漸進法 = 逆行列の解", sol["converged"] and err < 1e-8, "最大の相対差 %.1e" % err)
    gate("残エネルギーは減るだけ", bool((np.diff(h) <= 1e-15 * h[0]).all()))
    return pt


# --------------------------------------------------------------------------- #
# 3-4. 描画・メッシュ・反射の回数
# --------------------------------------------------------------------------- #
def roi_crop():
    hit = OS.trace_rays(part(RHO_TRUE), *OS.camera_rays(CAM))
    z = hit["point"][:, 2].reshape(CAM["height"], CAM["width"])
    roi = (z < 13.9) & (z > 3.9) & (hit["index"].reshape(z.shape) == 0)       # ポケットの底と壁
    rr, cc = np.nonzero(roi)
    return roi, (rr.min(), rr.max() + 1, cc.min(), cc.max() + 1)


def chapter_render(crop):
    print("\n3. 検査用の多重反射描画")
    r0 = render(I_TRUE, RHO_TRUE, "part", 0, PM_MODEL)
    ref = OS.render_optscene(part(RHO_TRUE), CAM, [light()])
    d0 = float(np.abs(r0["image"] - ref).max() / ref.max())
    gate("反射 0 回 = render_optscene(測光の真値をそのまま)", d0 <= 1e-12, "最大差 / 最大値 %.1e" % d0)
    t0 = time.process_time()
    truth = render(I_TRUE, RHO_TRUE, "part", None, PM_TRUTH)
    tt = render(I_TRUE, RHO_TRUE, "tile", None, PM_TRUTH)
    print("   真値の収束解(パッチ %.1f mm、%d 枚、%d 回撃って収束 %s)%.1f s"
          % (PM_TRUTH, truth["n_patches"], truth["n_shots"], truth["converged"], time.process_time() - t0))
    r0_, r1_, c0, c1 = crop
    kappa = 1500.0 / float(truth["image"][r0_:r1_, c0:c1, 1][ROI_C].mean())    # ポケットの平均が 1500 DN
    mu_truth = DARK + kappa * truth["image"][r0_:r1_, c0:c1, 1]
    share = truth["indirect_share"][r0_:r1_, c0:c1][ROI_C]
    print("   ポケットの中の相互反射の割合: 平均 %.0f %%、最大 %.0f %%" % (100 * share.mean(), 100 * share.max()))
    # メッシュの収束: モデルの細かさを振り、細かい真値との差を雑音の σ で数える
    sig = np.sqrt(emva_var(mu_truth))[ROI_C]
    mesh = []
    for pm in MESH_STUDY:
        m = DARK + kappa * render(I_TRUE, RHO_TRUE, "part", None, pm)["image"][r0_:r1_, c0:c1, 1]
        z = (m[ROI_C] - mu_truth[ROI_C]) / sig
        mesh.append((pm, float(np.sqrt((z ** 2).mean())), float(np.abs(z).max())))
        print("   パッチ %.1f mm: 真値(%.1f mm)との差 RMS %.3f σ・最大 %.2f σ" % (pm, PM_TRUTH, mesh[-1][1], mesh[-1][2]))
    gate("メッシュを細かくすると真値との差が減る", all(a[1] > b[1] for a, b in zip(mesh, mesh[1:])))
    rm = dict((p, r) for p, r, _ in mesh)[PM_MODEL]
    gate("較正に使うメッシュ(%.1f mm)の差は雑音の 1/4 未満" % PM_MODEL, rm < 0.25, "RMS %.3f σ" % rm)
    return truth, tt, kappa, mesh


def chapter_bounces(kappa):
    print("\n4. 反射を何回数えれば足りるか")
    r = render(I_TRUE, RHO_TRUE, "part", None, PM_MODEL, study=12, tol=1e-10)
    peak_dn = kappa * float(r["image"].max())
    noise_rel = math.sqrt(float(emva_var(DARK + peak_dn))) / peak_dn          # 最も明るい画素での雑音の σ / 信号
    rows = r["bounce_study"]
    need = next((x["bounces"] for x in rows if x["asymptotic"] and x["gci"] <= noise_rel), None)
    print("   k  増分     観測収束比  漸近域  GCI 型の見積もり  収束解との実際の差(像の最大値に対する比)")
    for x in rows:
        f = lambda v, fmt: "-" if v is None else fmt % v                     # noqa: E731
        print("   %2d  %-8s %-11s %-7s %-17s %.4f" % (x["bounces"], f(x["increment"], "%.4f"),
                                                    f(x["observed_ratio"], "%.3f"), "yes" if x["asymptotic"] else "",
                                                    f(x["gci"], "%.4f"), x["error_vs_converged"]))
    pre = [x for x in rows if x["gci"] is not None and not x["asymptotic"] and x["gci"] < x["error_vs_converged"]]
    if pre:
        print("   (漸近域の前では見積もりが楽観した: " + "、".join("k = %d で %.4f < %.4f" % (
            x["bounces"], x["gci"], x["error_vs_converged"]) for x in pre) + ")")
    gci_ok = all(x["gci"] >= x["error_vs_converged"] for x in rows if x["asymptotic"])
    gate("漸近域(観測収束比が 2 回続けて 5 % 以内)の GCI 型の見積もりは実際の差を下回らない",
         gci_ok and sum(x["asymptotic"] for x in rows) >= 4)
    gate("雑音(%.2f %%)に埋もれる反射の回数が決まる" % (100 * noise_rel), need is not None,
         "%s 回(そのときの実際の差 %.4f)" % (need, rows[need]["error_vs_converged"] if need is not None else float("nan")))
    return rows, need, noise_rel


# --------------------------------------------------------------------------- #
# 5. 較正
# --------------------------------------------------------------------------- #
def make_forward(kappa, crop):
    r0_, r1_, c0, c1 = crop

    def forward(intensity=1.0, rho=0.5, target="part", model="converged"):
        """模型: 照明の強さと反射率 → DN の画像(ポケットの切り出し)。基準の板の反射率は既知。"""
        if model == "direct" and target == "part":
            # 直接光だけのモデルでは反射率は単なる倍率: rho = 1 で描いて掛ける(1 を超えても止める式が無い)
            img = rho * render(intensity, 1.0, target, 0, PM_MODEL)["image"]
        else:
            img = render(intensity, rho, target, {"direct": 0, "one": 1, "converged": None}[model], PM_MODEL)["image"]
        return DARK + kappa * img[r0_:r1_, c0:c1, 1]
    return forward


def chapter_calibrate(forward, train, hold):
    print("\n5. 較正: 反射率と照明の強さを 3 つのモデルで合わせる(真値 %.2f / %.2f)" % (RHO_TRUE, I_TRUE))
    res = {}
    for name in ("direct", "one", "converged"):
        t0 = time.process_time()
        # 反射を数えるモデルは式の中にエネルギー保存(ρ <= 1、それより大きい反射率は描画が拒む)がある。
        # 直接光だけのモデルでは ρ は単なる倍率で、範囲を物理で縛る式が無い —— そこが「あり得ない値で合う」穴。
        model = simcal.simcal_model(
            chain=[{"op": forward, "args": {"model": name}}],
            knobs=[{"name": "intensity", "step": 0, "arg": "intensity", "lo": 0.25, "hi": 4.0, "scale": "log",
                    "unit": "1", "init": 1.0},
                   {"name": "rho", "step": 0, "arg": "rho", "lo": 0.05, "hi": 2.0 if name == "direct" else 1.0,
                    "unit": "1", "init": 0.5}],
            conditions=[{0: {"target": "part"}}, {0: {"target": "tile"}}], noise=NOISE, label=name)
        model = simcal.simcal_observe(model, train, roi=None)
        try:
            fit = simcal.simcal_fit(model)
        except MetricContractError as e:
            print("   %s: 拒否 %s" % (name, str(e)[:200]))
            res[name] = None
            continue
        val = simcalcheck.simcal_validate(fit, holdout=hold)
        dis = simcalcheck.simcal_discrepancy(fit)
        th = fit["theta_hat"]
        g = val["validation"]["gates"]
        fc = g["fit_consistent_with_noise"]
        sims = simcal.simcal_simulate(model, th)
        part_fit, part_obs = sims[0], train[0]
        rel_rms = float(np.sqrt(((part_fit - part_obs)[ROI_C] ** 2).mean()) / (part_obs[ROI_C] - DARK).mean())
        corr = float(np.corrcoef(part_fit[ROI_C], part_obs[ROI_C])[0, 1])
        res[name] = {"fit": fit, "val": val, "dis": dis, "rho": th["rho"], "intensity": th["intensity"],
                     "chi2_train": fc["train"]["chi2_per_nu"], "chi2_hold": fc["holdout"]["chi2_per_nu"],
                     "p": fc["value"], "failed": val["validation"]["failed"],
                     "n_struct": dis["discrepancy"]["n_structural"], "verdict": dis["discrepancy"]["verdict"],
                     "resid": (part_obs - part_fit) / np.sqrt(emva_var(part_fit)), "image": part_fit,
                     "loading": dis["discrepancy"]["loading_maps"], "rel_rms": rel_rms, "corr": corr}
        print("   %-9s ρ = %.4f  照明 = %.4f  χ²/ν 訓練 %.2f・holdout %.2f  p %.2g  残差 PCA %s(%d 成分)"
              "  RMS 残差 / 信号 %.1f %%  相関 %.4f  落ちた門 %s  %.1f s"
              % (name, th["rho"], th["intensity"], res[name]["chi2_train"], res[name]["chi2_hold"], fc["value"],
                 res[name]["verdict"], res[name]["n_struct"], 100 * rel_rms, corr, res[name]["failed"] or "なし",
                 time.process_time() - t0))
    d, o, c = res["direct"], res["one"], res["converged"]
    gate("直接光だけ: 反射率が 1 を超えて合う(エネルギー保存に反する)", d is not None and d["rho"] > 1.0,
         "ρ = %.3f" % d["rho"] if d else "拒否")
    gate("直接光だけ: 絶対 χ² の門と残差 PCA で不合格",
         d is not None and "fit_consistent_with_noise" in d["failed"] and d["verdict"] == "structure",
         "χ²/ν %.1f・構造 %d 成分" % (d["chi2_train"], d["n_struct"]) if d else "")
    gate("1 回反射: まだ不合格(反射率は真値より %.0f %% 高い)" % (100 * (o["rho"] / RHO_TRUE - 1)) if o else "1 回反射",
         o is not None and "fit_consistent_with_noise" in o["failed"] and o["rho"] > RHO_TRUE + 0.05)
    gate("収束解: 反射率と照明の強さが真値に戻る",
         c is not None and abs(c["rho"] - RHO_TRUE) < 0.005 and abs(c["intensity"] - I_TRUE) < 0.005,
         "ρ %.4f(真値 %.2f)・照明 %.4f(真値 %.2f)" % (c["rho"], RHO_TRUE, c["intensity"], I_TRUE) if c else "")
    gate("収束解: 過適合の 6 門をすべて通り、残差は白色",
         c is not None and not c["failed"] and c["verdict"] == "white",
         "χ²/ν %.3f・p %.3f" % (c["chi2_train"], c["p"]) if c else "")
    gate("χ² は 直接光 > 1 回反射 > 収束解", d is not None and o is not None and c is not None
         and d["chi2_train"] > o["chi2_train"] > c["chi2_train"])
    return res


# --------------------------------------------------------------------------- #
# 6. Bulczak ら 2018 の表 2
# --------------------------------------------------------------------------- #
def chapter_bulczak(forward, train):
    print("\n6. 実測との照合: Bulczak, Lambers, Kolb 2018(Sensors 18(1):13、CC BY 4.0)の表 2")
    ratios = [s / d for s, d in zip(BULCZAK_SINGLE, BULCZAK_DIRECT)]
    for (shape, mat), d, s, q in zip(BULCZAK_COLS, BULCZAK_DIRECT, BULCZAK_SINGLE, ratios):
        print("   %-18s 材料 %s  直接光だけ %.4f  1 回反射込み %.4f  比 %.2f" % (shape, mat, d, s, q))
    gate("引用した表で 1 回反射込みの MAE < 直接光だけ(6 列すべて)", all(q < 1.0 for q in ratios))
    obs = train[0][ROI_C]
    mae = {m: float(np.abs(forward(I_TRUE, RHO_TRUE, "part", m)[ROI_C] - obs).mean())
           for m in ("direct", "one", "converged")}
    ours = mae["one"] / mae["direct"]
    print("   本 PoC(強度、真値の係数で描いて観測と比べる): MAE 直接光だけ %.1f DN・1 回反射 %.1f DN・収束解 %.1f DN"
          "(雑音だけの MAE の目安 %.1f DN)、比 %.2f(論文 %.2f〜%.2f)"
          % (mae["direct"], mae["one"], mae["converged"], float(np.sqrt(2 / np.pi) * np.sqrt(emva_var(obs)).mean()),
             ours, min(ratios), max(ratios)))
    gate("本 PoC でも 直接光だけ > 1 回反射 > 収束解", mae["direct"] > mae["one"] > mae["converged"])
    return ratios, mae


# --------------------------------------------------------------------------- #
# 図
# --------------------------------------------------------------------------- #
def figures(truth, crop, res, rows, need, noise_rel, mesh, ratios, mae, kappa):
    if figs.target_dir() is None:
        return
    r0_, r1_, c0, c1 = crop
    img = truth["image"][..., 1]
    dir_ = truth["direct"][..., 1]
    hi = float(img.max())
    figs.save_grid("renders", [dir_, img, truth["difference"][..., 1], truth["indirect_share"]],
                   captions=["直接光だけ(render_optscene と同じ)", "収束解(render_optscene_gi)",
                             "差 = 相互反射の地図", "相互反射の割合"],
                   gray=[True, True, False, False], vrange=[(0, hi), (0, hi), None, (0.0, 1.0)],
                   caption="同じシーン・同じドーム照明・同じカメラで、直接光だけの検査用描画(左上)と、反射を収束まで数えた描画"
                           "(右上)。ポケットの底は相互反射で平均 %.0f %% 明るく、角ほど強い(右下は像に占める相互反射の割合)。"
                           "反射 0 回の render_optscene_gi は render_optscene と 1e-12 以内で一致する。"
                           % (100 * float(truth["indirect_share"][r0_:r1_, c0:c1][ROI_C].mean())))
    names = ("direct", "one", "converged")
    labels = {"direct": "直接光だけ", "one": "1 回反射", "converged": "収束解"}
    panels = [res[n]["resid"] for n in names if res[n] is not None]
    figs.save_grid("residuals", panels, captions=["%s: ρ = %.3f、χ²/ν %.1f" % (labels[n], res[n]["rho"], res[n]["chi2_train"])
                                                  for n in names if res[n] is not None],
                   signed=True, ncols=3, vrange=(-8.0, 8.0),
                   caption="合わせた後の残差(雑音の σ で割った値、±8 σ で塗った)。直接光だけのモデルは反射率 %.2f(1 を超える = "
                           "当てた光より多く返す面)で合い、中央は足りず壁際は出すぎる山形が残る。1 回反射は %.2f で、山は低いが"
                           "まだ残る。"
                           "収束解は %.3f(真値 %.2f)で、残差は雑音と区別できない。"
                           % (res["direct"]["rho"], res["one"]["rho"], res["converged"]["rho"], RHO_TRUE))
    if res["direct"]["loading"]:
        up = [np.kron(m, np.ones((6, 6))) for m in res["direct"]["loading"][:2]]       # 34 x 50 画素を 6 倍に(最近傍)
        figs.save_grid("discrepancy", up, signed=True, ncols=2,
                       captions=["残差 PCA 第 %d 成分" % (i + 1) for i in range(min(2, len(res["direct"]["loading"])))],
                       caption="直接光だけのモデルの残差の主成分(simcal_discrepancy)。雑音の Tracy-Widom 99 %% の線を超える "
                               "成分が %d 本あり、第 1 成分は左右の壁と中央の差、第 2 成分は上下の壁と中央の差 —— 壁からの距離で"
                               "変わる明るさ、つまりモデルに足りない相互反射の形を指す(画素は 6 倍に拡大)。"
                               % res["direct"]["n_struct"])
    ks = [x["bounces"] for x in rows if x["bounces"] >= 1]
    inc = [x["increment"] for x in rows if x["bounces"] >= 1]
    err = [max(x["error_vs_converged"], 1e-12) for x in rows if x["bounces"] >= 1]
    gk = [x["bounces"] for x in rows if x["gci"] is not None]
    gv = [x["gci"] for x in rows if x["gci"] is not None]
    figs.save_plot("bounces", [("増分", ks, np.log10(inc)), ("GCI 型の見積もり", gk, np.log10(gv)),
                               ("収束解との実際の差", ks, np.log10(err)),
                               ("雑音の σ", [ks[0], ks[-1]], [math.log10(noise_rel)] * 2)],
                   xlabel="数えた反射の回数 k", ylabel="log10(像の最大値に対する比)", title="反射の回数と残りの誤差",
                   styles=[None, None, None, "dashed"], colors=["neutral", "emphasis", "right", "reference"],
                   caption="反射を k 回まで数えた像の誤差。等比級数なので直線に乗り、隣り合う増分の比(観測収束比)は %.2f。"
                           "GCI 型の見積もり 1.25·Δg/(1 − g) は実際の差のすぐ上にあり、雑音の線(%.2f %%)を下回るのは "
                           "%s 回目から。" % (rows[-1]["observed_ratio"], 100 * noise_rel, need))
    figs.save_plot("mesh", [("真値との差 RMS", [m[0] for m in mesh], [m[1] for m in mesh]),
                            ("雑音の 1/4", [mesh[-1][0], mesh[0][0]], [0.25, 0.25])],
                   xlabel="パッチの大きさ [mm]", ylabel="差の RMS [σ]", styles=[None, "dashed"], title="メッシュの収束",
                   colors=["emphasis", "reference"], kinds=["line", "line"],
                   caption="反射の回数だけでなく、パッチの細かさも収束させる。ポケットの内側のパッチを細かくすると、"
                           "細かい真値(%.1f mm)との差が減る。較正には %.1f mm を使った。" % (PM_TRUTH, PM_MODEL))
    rows_t = [[labels[n], "%.4f" % res[n]["rho"], "%.4f" % res[n]["intensity"], "%.2f" % res[n]["chi2_train"],
               "%.2g" % res[n]["p"], "%d" % res[n]["n_struct"], "%.1f" % (100 * res[n]["rel_rms"]),
               "不合格" if res[n]["failed"] else "合格"] for n in names]
    figs.save_table("calibration", ["モデル", "反射率", "照明の強さ", "χ²/ν", "p", "残差 PCA", "RMS 残差 %", "判定"],
                    rows_t, title="真値: 反射率 %.2f・照明の強さ %.2f" % (RHO_TRUE, I_TRUE),
                    caption="3 つのモデルを同じ観測(ポケット + 反射率 0.5 の基準の板)に合わせた結果。")
    rows_b = [[s, m, "%.4f" % d, "%.4f" % q, "%.2f" % (q / d)] for (s, m), d, q in
              zip(BULCZAK_COLS, BULCZAK_DIRECT, BULCZAK_SINGLE)]
    rows_b.append(["本 PoC(強度)", "反射率 0.7", "%.1f DN" % mae["direct"], "%.1f DN" % mae["one"],
                   "%.2f" % (mae["one"] / mae["direct"])])
    figs.save_table("bulczak", ["形状", "材料", "直接光だけ MAE", "1 回反射込み MAE", "比"], rows_b,
                    title="Bulczak ら 2018 の表 2(実測、CC BY 4.0)と本 PoC",
                    caption="実測の凹形状 3 種 x 材料 2 種で、1 回反射を足すと距離の誤差が %.2f〜%.2f 倍になる(論文の表 2、"
                            "数値は改変なし)。本 PoC の強度画像では %.2f 倍。出典: " % (min(ratios), max(ratios),
                                                                                 mae["one"] / mae["direct"])
                            + BULCZAK_SOURCE)


ROI_C = None


def main():
    global ROI_C
    t0 = time.process_time()
    print("PoC 加工ポケットの相互反射を収束まで数える(予算 %s)" % ("reduced" if REDUCED else "full"))
    chapter_form_factors()
    chapter_progressive()
    roi, crop = roi_crop()
    r0_, r1_, c0, c1 = crop
    ROI_C = roi[r0_:r1_, c0:c1]
    print("   ポケットの切り出し %d x %d 画素(関心領域 %d 画素)" % (r1_ - r0_, c1 - c0, int(ROI_C.sum())))
    truth, tt, kappa, mesh = chapter_render(crop)
    rows, need, noise_rel = chapter_bounces(kappa)
    mus = [DARK + kappa * truth["image"][r0_:r1_, c0:c1, 1], DARK + kappa * tt["image"][r0_:r1_, c0:c1, 1]]
    train, hold = capture(mus, SEED), capture(mus, SEED + 10000)
    nchi = [float((((a - b) ** 2) / emva_var(b)).mean()) for a, b in zip(train, mus)]
    print("   観測(訓練)の雑音だけの χ²/画素: ポケット %.3f・基準の板 %.3f(雑音の模型の確かめ)" % tuple(nchi))
    forward = make_forward(kappa, crop)
    res = chapter_calibrate(forward, train, hold)
    ratios, mae = chapter_bulczak(forward, train)
    if all(res[n] is not None for n in res):
        figures(truth, crop, res, rows, need, noise_rel, mesh, ratios, mae, kappa)
    used = time.process_time() - t0
    gate("所要(この PoC の CPU 時間)%.0f s 以内" % BUDGET_S, used <= BUDGET_S, "%.1f s" % used)
    print("\n門 %d 件中 NG %d 件" % (len(GATES), len(FAILS)))
    if FAILS:
        print("FAIL: " + ", ".join(FAILS))
        sys.exit(1)
    assert not figs.errors(), figs.errors()
    print("PASS")


if __name__ == "__main__":
    main()
