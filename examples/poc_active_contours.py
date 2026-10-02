# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC(セグメンテーション拡充 第 2 陣): 変分・動的輪郭 —— snake / GVF snake / Chan–Vese / 形態学的 Chan–Vese /
形態学的測地的 active contour / DRLSE を、真値つきの合成世界(:mod:`segworld`)と Xu–Prince の U 字で走らせ、
物差し(:mod:`segeval`)で採点し、輪郭が動いていく様子をコマ送りの動画にする。

方針: **学習器は載せない**。どの手法も定理か第 2 実装の門を持つ(:mod:`segcontour`)。この PoC はその門を
「実際の絵の上で」もう一度踏み、さらに **手法どうしの差** を門にする:

門(真値の出どころ、自明でない):
  1. **snake の閉形式**: 外力 0 の円は 1 反復ごとに半径 γ/(γ + 4α sin²(π/N) + 16β sin⁴(π/N)) 倍(巡回行列の固有値、厳密)。
  2. **平均曲率流**: 囲む面積の減りは dA/dt = −2π(円でも、凹んだ星形でも = 回転数 1 の Gauss–Bonnet)。
  3. **再初期化**: Sussman の PDE で |∇φ| の 10〜90 % 点が 1 ± 5 %、零等高線は動かない(Hausdorff ≤ 1 px)、
     距離変換の符号付き距離(第 2 実装)と帯の中で 0.75 px 以内。
  4. **U 字の凹部**(Xu–Prince 1998 の図): 古典の snake(エッジの勾配)は凹部の 90 % 超を覆ったまま入れない、GVF snake は
     凹部の 5 % 未満しか覆わず Dice ≥ 0.98。同じ α・β・γ・反復で、違うのは外力だけ。
  5. **エネルギーの単調性**: 古典の snake(γ ≥ L の近接勾配)のエネルギーは 1 度も増えない、Chan–Vese(凸緩和の交互最小化)の
     鋭いエネルギーは 4 世界すべてで単調非増加、形態学的 Chan–Vese のデータ段は 4 世界すべてで当てはめを上げない。
  6. **触れ合う粒**: Chan–Vese と形態学的 Chan–Vese のマスクは Dice ≥ 0.95(ただし融合した粒は分けない = 未分割を表で示す)。
  7. **照明の勾配**: Chan–Vese(大域の 2 平均)は Jaccard < 0.5、エッジで止まる局所の手法(形態学的測地的 AC・DRLSE)は ≥ 0.9。
  8. **影のある部品**: どの輪郭法も Jaccard < 0.7(閾値と同じく、影と暗い面に負ける = 限界の記録)。
  9. **DRLSE**: 真円の縁(半径 20)で 1 px 以内に止まり、零等高線の近くの |∇φ| の中央値が 0.85〜1.1(2 値の段差から始めて
     再初期化なしで距離の形になる = Li 2010 の主張を測った)。
 10. **既存 op との照合**: 2 値 + 雑音の楕円で、Chan–Vese(凸)と既存の ``sk_chan_vese`` の Dice ≥ 0.97。
 11. 図なしで 60 秒以内。

正直に書くこと:
* ノブは世界ごとに合わせていない(μ = 0.2、GAC の k = 0.02、DRLSE は Li の例の λ = 5・α = 1.5)。
* Chan–Vese の「レベルセットの勾配流」版(``method="level_set"``)は局所解で止まるので、ここでは凸緩和の版を使う
  (segcontour の docstring に実測)。DRLSE のエネルギーは陽的な刻みのため反復で増えることがある(数を表示、門ではない)。
* 物体が暗い世界(照明の勾配・細い構造)は画像を反転して渡す(世界の宣言、画素ごとの真値ではない)。

Run: py -3.11 examples/poc_active_contours.py   (図は FULLSEYE_FIGURE_DIR を設定したときだけ書く)
"""
from __future__ import annotations

import math
import os
import sys
import time
import warnings
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import segcontour as SC  # noqa: E402
import segeval as SE  # noqa: E402
import segworld as SW  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

warnings.filterwarnings("ignore")

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET", "reduced" if os.environ.get("CI") else "full") == "reduced"
T0 = time.time()
OK = []
MU = 0.2
K_GAC = 0.02


def gate(name, cond, detail=""):
    OK.append(bool(cond))
    print("  [%s] %s %s" % ("PASS" if cond else "FAIL", name, detail))


def grid(h, w):
    return np.mgrid[0:h, 0:w].astype(np.float64)


def circle_points(cy, cx, r, n):
    th = np.linspace(0.0, 2.0 * math.pi, n, endpoint=False)
    return np.stack([cy + r * np.sin(th), cx + r * np.cos(th)], axis=1)


def jac(mask, body):
    return SE.seg_dice_jaccard(mask, body)["jaccard"]


# ───────────────────────────── 1〜3. 定理の門 ─────────────────────────────
def theorems():
    print("== 1. 定理の門(snake の閉形式・曲率流・再初期化)")
    n, r0, al, be, ga, it = 60, 20.0, 0.5, 0.2, 2.0, 50
    r = SC.snake_evolve(np.zeros((81, 83)), circle_points(40, 41, r0, n), alpha=al, beta=be, gamma=ga,
                        external="none", n_iter=it)
    rad = np.hypot(r["points"][:, 0] - 40, r["points"][:, 1] - 41)
    want = r0 * (ga / (ga + 4 * al * math.sin(math.pi / n) ** 2 + 16 * be * math.sin(math.pi / n) ** 4)) ** it
    err = float(np.abs(rad - want).max() / want)
    gate("snake: 外力 0 の円は巡回行列の閉形式どおり縮む(相対誤差 < 1e-10)", err < 1e-10,
         "r_%d = %.6f(閉形式 %.6f、誤差 %.1e)" % (it, rad.mean(), want, err))

    yy, xx = grid(80, 80)
    cf = SC.curvature_flow(np.hypot(yy - 39.6, xx - 40.3) - 30.0, t_end=300.0, dt=0.2, record_every=25)
    yy2, xx2 = grid(96, 96)
    th = np.arctan2(yy2 - 47.6, xx2 - 48.2)
    star = np.hypot(yy2 - 47.6, xx2 - 48.2) < 28 * (1 + 0.3 * np.cos(3 * th))
    cs = SC.curvature_flow(star, t_end=150.0, dt=0.2, record_every=10)
    rc = cf["area_rate"] / (-2 * math.pi) - 1
    rs = cs["area_rate"] / (-2 * math.pi) - 1
    r2_end = cf["areas"][-1] / math.pi
    gate("曲率流: dA/dt = −2π(円は ±0.5 %、凹んだ星形も ±1 %)、円は r² = r0² − 2t", abs(rc) < 0.005 and abs(rs) < 0.01
         and abs(r2_end - (900 - 600)) < 3.0,
         "円 %.4f / 星 %.4f(−2π = %.4f)、t=300 で r² = %.1f(閉形式 300)" % (cf["area_rate"], cs["area_rate"], -2 * math.pi, r2_end))

    yy3, xx3 = grid(96, 96)
    true = np.hypot(yy3 - 47.6, xx3 - 48.2) - 25.3
    phi0 = 0.005 * (np.hypot(yy3 - 47.6, xx3 - 48.2) ** 2 - 25.3 ** 2)
    ri = SC.level_set_reinit(phi0, n_iter=200)
    re = SC.level_set_reinit(phi0, method="edt")
    band = np.abs(true) <= 3
    g = ri["grad"]
    gate("再初期化: |∇φ| の 10〜90 % 点が 1 ± 5 %、零等高線 Hausdorff ≤ 1、距離変換と帯の中で ≤ 0.75 px",
         0.95 < g["q10"] and g["q90"] < 1.05 and ri["zero_hausdorff"] <= 1.0
         and float(np.abs(ri["phi"] - re["phi"])[band].max()) <= 0.75,
         "前 q50=%.2f → 後 q10/q50/q90 = %.3f/%.3f/%.3f、Hausdorff %.1f、解析解との差 最大 %.3f px、EDT との差 最大 %.2f px"
         % (ri["grad_before"]["q50"], g["q10"], g["q50"], g["q90"], ri["zero_hausdorff"],
            float(np.abs(ri["phi"] - true)[band].max()), float(np.abs(ri["phi"] - re["phi"])[band].max())))
    return {"curv_circle": cf, "curv_star": cs, "star0": star}


# ───────────────────────────── 4. U 字 ─────────────────────────────
def u_shape():
    print("== 2. U 字の凹部(Xu–Prince 1998): 古典の snake vs GVF snake")
    U = np.zeros((128, 128), bool)
    U[30:100, 30:98] = True
    U[30:82, 52:76] = False
    slot = np.zeros(U.shape, bool)
    slot[30:82, 52:76] = True
    img = ndi.gaussian_filter(U.astype(float), 1.0)
    init = circle_points(65, 64, 52, 120)
    common = dict(alpha=0.01, beta=0.01, gamma=1.0, n_iter=1000, record_every=20)
    a = SC.snake_evolve(img, init, external="edge", sigma=1.5, kappa=20.0, **common)
    g = SC.gvf_field(img, mu=0.2, sigma=1.0)
    b = SC.snake_evolve(img, init, external="gvf", gvf=g, kappa=5.0, resample_every=5, **common)
    ca = np.count_nonzero(a["mask"] & slot) / slot.sum()
    cb = np.count_nonzero(b["mask"] & slot) / slot.sum()
    da, db = SE.seg_dice_jaccard(a["mask"], U)["dice"], SE.seg_dice_jaccard(b["mask"], U)["dice"]
    print("  古典: 凹部の被覆 %.2f、Dice %.3f / GVF: 被覆 %.3f、Dice %.3f(GVF の Euler 方程式の残差 %.1e)"
          % (ca, da, cb, db, g["residual_rel"]))
    gate("U 字: 古典の snake は凹部の 90 % 超を覆ったまま、GVF snake は 5 % 未満で Dice ≥ 0.98", ca > 0.9 and cb < 0.05 and db >= 0.98,
         "被覆 %.2f vs %.3f、Dice %.3f vs %.3f" % (ca, cb, da, db))
    gate("古典の snake のエネルギーは 1 度も増えない(γ ≥ L なら降下補題で保証)", a["n_increase"] == 0,
         "増加 %d 回、γ = 1 ≥ L = %.3f: %s、E %.2f → %.2f" % (a["n_increase"], a["lipschitz"], a["gamma_ge_lipschitz"],
                                                            a["energy"][0], a["energy"][-1]))
    return {"U": U, "img": img, "classic": a, "gvf": b, "field": g}


# ───────────────────────────── 5〜8. 世界 ─────────────────────────────
WORLDS = [
    ("blobs", "触れ合う粒", lambda: SW.world_blobs_touching(10, 0.2, 0), True),
    ("parts", "影のある部品", lambda: SW.world_parts_with_shadow(0), True),
    ("gradient", "照明の勾配", lambda: SW.world_gradient_illumination(0), False),
    ("thin", "細い構造", lambda: SW.world_thin_structures(0), False),
]


def worlds():
    print("== 3. 真値つきの世界(segworld)で 4 手法 + DRLSE")
    rows = {}
    keep = {}
    assert len(WORLDS) > 0
    for key, title, make, bright in WORLDS:
        w = make()
        im = w["image"] if bright else 1.0 - w["image"]
        body = w["labels"] > 0
        init = np.zeros(im.shape, bool)
        init[3:-3, 3:-3] = True
        t = time.time()
        cv = SC.chan_vese_evolve(im, init, mu=MU, n_iter=30, record_every=1)
        mc = SC.morph_chan_vese(im, init, n_iter=150, smoothing=1, record_every=5)
        g = SC.edge_stop_g(im, sigma=1.0, k=K_GAC)["g"]
        ga = SC.morph_geodesic_ac(g, init, n_iter=250, smoothing=1, balloon=-1, record_every=8)
        res = {"chan_vese": cv, "morph_chan_vese": mc, "morph_gac": ga}
        if key == "gradient":
            res["drlse"] = SC.drle_evolve(im, init, k=K_GAC, n_iter=800, dt=5.0, record_every=25)
        cards = {}
        assert len(res) > 0
        for name, r in res.items():
            m = r["mask"]
            # 2 相の手法は「どちらが物体か」を持たないので、極性は真値に近い側(宣言として表に出す)
            flip = name in ("chan_vese", "morph_chan_vese") and jac(~m, body) > jac(m, body)
            if flip:
                m = ~m
            lab = ndi.label(m)[0].astype(np.int64)
            c = SE.seg_score_card(lab, w["labels"], tau=2.0)
            c["flipped"] = flip
            cards[name] = c
        rows[key] = cards
        keep[key] = (title, w, im, res)
        print("  --- %s(%.1f s)" % (title, time.time() - t))
        assert len(cards) > 0
        for name, c in cards.items():
            print("    %-16s J=%.3f Dice=%.3f BF=%.2f under=%3d over=%3d n=%3d/%2d%s" % (
                name, c["jaccard"], c["dice"], c["boundary_f"], c["under"], c["over"], c["n_pred"], c["n_true"],
                " (反転)" if c["flipped"] else ""))
    return rows, keep


def main() -> int:
    print("BUDGET: %s(FULLSEYE_POC_BUDGET、CI では reduced が既定。この PoC は予算で変わらない)" % ("reduced" if REDUCED else "full"))
    th = theorems()
    us = u_shape()
    rows, keep = worlds()

    print("== 4. 単調性・手法の差(門)")
    cv_mono = [bool(np.all(np.diff(keep[k][3]["chan_vese"]["energy"]) <= 0)) and keep[k][3]["chan_vese"]["n_guard"] == 0
               for k in rows]
    mc_mono = [keep[k][3]["morph_chan_vese"]["n_data_increase"] == 0 for k in rows]
    gate("Chan–Vese(凸)の鋭いエネルギーは 4 世界すべてで単調非増加、形態学的 CV のデータ段は当てはめを上げない",
         len(cv_mono) == 4 and all(cv_mono) and all(mc_mono),
         "CV %s / mCV %s" % (cv_mono, mc_mono))
    smooth_up = {k: int(np.count_nonzero(np.diff(np.concatenate([[keep[k][3]["morph_chan_vese"]["fit_before_data"][0]],
                                                                  keep[k][3]["morph_chan_vese"]["fit_after_smooth"]])) > 0))
                 for k in rows}
    print("    (参考)形態学的 CV の 1 反復全体で当てはめが増えた回数(平滑段のせい): %s" % smooth_up)
    b = rows["blobs"]
    gate("触れ合う粒: Chan–Vese と形態学的 CV のマスクは Dice ≥ 0.95(粒は分けない = 未分割)",
         b["chan_vese"]["dice"] >= 0.95 and b["morph_chan_vese"]["dice"] >= 0.95,
         "Dice %.3f / %.3f、未分割 %d / %d" % (b["chan_vese"]["dice"], b["morph_chan_vese"]["dice"],
                                            b["chan_vese"]["under"], b["morph_chan_vese"]["under"]))
    gr = rows["gradient"]
    gate("照明の勾配: Chan–Vese(大域の 2 平均)は Jaccard < 0.5、局所の手法(形態学的測地的 AC・DRLSE)は ≥ 0.9",
         gr["chan_vese"]["jaccard"] < 0.5 and gr["morph_gac"]["jaccard"] >= 0.9 and gr["drlse"]["jaccard"] >= 0.9,
         "CV %.3f / mCV %.3f / GAC %.3f / DRLSE %.3f" % (gr["chan_vese"]["jaccard"], gr["morph_chan_vese"]["jaccard"],
                                                        gr["morph_gac"]["jaccard"], gr["drlse"]["jaccard"]))
    pj = [c["jaccard"] for c in rows["parts"].values()]
    gate("影のある部品: どの輪郭法も Jaccard < 0.7(影と暗い面に負ける = 限界)", max(pj) < 0.7, "max J = %.3f" % max(pj))
    dr = keep["gradient"][3]["drlse"]
    print("    (参考)DRLSE(照明の勾配)の |∇φ| 中央値の推移 %s、エネルギーの増加 %d 回(陽的な刻み)"
          % (np.round(dr["grad_trace"], 2).tolist(), dr["n_increase"]))

    yy, xx = grid(96, 96)
    d = np.hypot(yy - 47.6, xx - 48.2)
    disk = SC.drle_evolve(0.2 + 0.6 * (d < 20), d < 32, n_iter=400, record_every=50)
    rad = math.sqrt(np.count_nonzero(disk["mask"]) / math.pi)
    gate("DRLSE: 真円(半径 20)の縁で 1 px 以内に止まり、零等高線の近くの |∇φ| 中央値が 0.85〜1.1",
         abs(rad - 20) < 1.0 and 0.85 < disk["grad"]["q50"] < 1.1,
         "半径 %.2f、|∇φ| q10/q50/q90 = %.2f/%.2f/%.2f(初期は 2 値の段差)" % (rad, disk["grad"]["q10"], disk["grad"]["q50"], disk["grad"]["q90"]))

    sk_dice = None
    try:
        import fullseye as fs
        yy4, xx4 = grid(100, 100)
        truth = (yy4 - 50) ** 2 / 30 ** 2 + (xx4 - 48) ** 2 / 22 ** 2 < 1
        im = truth + 0.15 * np.random.default_rng(3).standard_normal(truth.shape)
        im = (im - im.min()) / (im.max() - im.min())
        sq = np.zeros(im.shape, bool)
        sq[20:80, 20:80] = True
        mine = SC.chan_vese_evolve(im, sq, mu=MU, n_iter=50)["mask"]
        sk = fs.apply(im, "sk_chan_vese", 0.5, 0.5) > 0.5
        sk_dice = max(SE.seg_dice_jaccard(sk, mine)["dice"], SE.seg_dice_jaccard(~sk, mine)["dice"])
    except ImportError as exc:
        print("    sk_chan_vese を呼べない: %s" % exc)
    gate("既存 op との照合: Chan–Vese(凸)と sk_chan_vese の Dice ≥ 0.97", sk_dice is not None and sk_dice >= 0.97,
         "Dice %.4f" % (sk_dice if sk_dice is not None else float("nan")))
    elapsed = time.time() - T0
    gate("図なしで 60 秒以内", elapsed < 60.0, "%.1f s" % elapsed)

    if figs.enabled():
        figures(th, us, rows, keep, disk)
        if figs.errors():
            print("図の書き出しで失敗:", "; ".join(figs.errors()))
            OK.append(False)
    print("== 結果: %d / %d 門, %.1f s(CPU %.1f s)" % (sum(OK), len(OK), time.time() - T0, time.process_time()))
    print("PASS" if all(OK) else "FAIL")                    # tests/test_poc_scripts_run.py は exit 0 と PASS の両方を見る
    return 0 if all(OK) else 1


# ───────────────────────────── 図 ─────────────────────────────
UP = 3
COL = {"truth": (0.15, 0.85, 0.25), "a": (0.95, 0.2, 0.15), "b": (0.2, 0.55, 1.0), "c": (1.0, 0.85, 0.1)}


def _boundary(m):
    b = np.zeros(m.shape, bool)
    b[:, :-1] |= m[:, 1:] != m[:, :-1]
    b[:-1, :] |= m[1:, :] != m[:-1, :]
    return b


def _base(im):
    x = np.clip((im - im.min()) / max(float(np.ptp(im)), 1e-12), 0, 1) * 0.8
    rgb = np.repeat(x[:, :, None], 3, axis=2)
    return np.repeat(np.repeat(rgb, UP, axis=0), UP, axis=1)


def _draw_mask(rgb, m, col, thick=1):
    b = _boundary(m)
    if thick > 1:
        b = ndi.binary_dilation(b, iterations=thick - 1)
    bu = np.repeat(np.repeat(b, UP, axis=0), UP, axis=1)
    rgb[bu] = col
    return rgb


def _draw_poly(rgb, pts, col):
    p = np.vstack([pts, pts[:1]]) * UP + UP / 2.0
    h, w = rgb.shape[:2]
    for k in range(len(p) - 1):
        n = int(max(abs(p[k + 1, 0] - p[k, 0]), abs(p[k + 1, 1] - p[k, 1]))) + 2
        rr = np.clip(np.round(np.linspace(p[k, 0], p[k + 1, 0], n)).astype(int), 0, h - 1)
        cc = np.clip(np.round(np.linspace(p[k, 1], p[k + 1, 1], n)).astype(int), 0, w - 1)
        for dr in (-1, 0, 1):
            rgb[np.clip(rr + dr, 0, h - 1), cc] = col
    return rgb


def _label(rgb, text):
    import annotate as AN
    return np.asarray(AN.text_box(rgb, text, (6, 6), anchor="lt", font_size=13, max_width=rgb.shape[1] - 12))


def _u8(rgb):
    return (np.clip(np.asarray(rgb, np.float64), 0, 1) * 255).astype(np.uint8)


def _pick(seq, k):
    """長さの違う履歴を k コマに揃える(比例で間引き、最後のコマは必ず入る)。"""
    idx = np.round(np.linspace(0, len(seq) - 1, k)).astype(int)
    return [seq[i] for i in idx]


def figures(th, us, rows, keep, disk):
    print("== 5. 図")
    U, img = us["U"], us["img"]
    panels = [img, us["field"]["edge_map"], np.hypot(us["field"]["u"], us["field"]["v"])]
    caps = ["U 字(Xu–Prince の凹部)", "辺の地図 f = |∇G_σ*I|(正規化)", "GVF の大きさ |(u, v)|(凹部の奥まで届く)"]
    assert len(keep) > 0
    for key, (title, w, im, res) in keep.items():
        panels += [w["image"], w["labels"].astype(float)]
        caps += ["%s: 画像" % title, "%s: 真値" % title]
    figs.save_grid("inputs", panels, captions=caps, title="入力: U 字と GVF、真値つきの 4 世界", ncols=3,
                   gray=[True, False, False] + [True, False] * len(keep),
                   caption="GVF は辺の勾配を μ∇² で辺から離れた所まで拡散した場(Euler 方程式の残差 %.1e)。古典の snake の力は"
                           "辺の近くにしか無いので U 字の凹部の中は力 0。" % us["field"]["residual_rel"])
    series = []
    assert len(keep) > 0
    for key, (title, w, im, res) in keep.items():
        e = res["chan_vese"]["energy"]
        series.append(("%s(%d 反復)" % (title, len(e) - 1), np.arange(len(e)), e / e[0]))
    figs.save_plot("cv_energy", series, xlabel="外側の反復", ylabel="鋭いエネルギー / 初期", title="Chan–Vese(凸緩和): 単調に下がって止まる",
                   caption="c の更新(内外の平均)と、c を固定した凸緩和(Chan–Esedoglu–Nikolova)の交互最小化。どの世界でも"
                           "1 度も増えず、分割が変わらなくなった所で止まる(門 5)。止まった所が真値に近いかは別(表を見る)。",
                   kinds=["scatter"] * len(series))
    a_ = us["classic"]
    it = np.arange(len(a_["energy"]))
    figs.save_plot("snake_energy", [("全体", it, a_["energy"]), ("内部(½ x·Ax)", it, a_["energy_internal"]),
                                    ("外力(−κP)", it, a_["energy_external"])],
                   xlabel="反復", ylabel="エネルギー", title="古典の snake(U 字): 近接勾配の降下",
                   caption="γ = 1 ≥ L = %.3f(外力の勾配の Lipschitz 定数)なので降下補題により全体は増えない(実測 増加 %d 回)。"
                           "内部(張力と曲げ)は角に巻き付くぶん少し上がり、外力が縁に乗るぶん大きく下がる。1000 反復でも"
                           "まだ下がり続ける(遅い)が、凹部の口に架かった橋の下には力が無いので、何反復回しても凹部には入らない。"
                   % (a_["lipschitz"], a_["n_increase"]))
    cf, cs = th["curv_circle"], th["curv_star"]
    figs.save_plot("curvature_area", [("円 r0 = 30", cf["times"], cf["areas"][0] - cf["areas"]),
                                      ("凹んだ星形", cs["times"], cs["areas"][0] - cs["areas"]),
                                      ("6.283 t(定理 dA/dt = −2π)", cf["times"], 2 * math.pi * cf["times"])],
                   xlabel="時間 t", ylabel="減った面積 A(0) − A(t)", title="平均曲率流: 囲む面積は 2π t ずつ減る",
                   caption="dA/dt = −∮κ ds = −2π。円(傾き %.3f)も凹んだ星形(%.3f)も同じ速さ —— 凹部は外へ膨らみ、"
                           "凸部は縮み、総和は回転数だけで決まる。" % (cf["area_rate"], cs["area_rate"]),
                   kinds=["line", "scatter", "line"])
    header = ["世界", "手法", "Jaccard", "Dice", "境界F", "未分割", "過分割", "予測/真"]
    table = []
    assert len(rows) > 0
    for key, cards in rows.items():
        assert len(cards) > 0
        for name, c in cards.items():
            table.append([keep[key][0], name + (" (反転)" if c["flipped"] else ""), "%.3f" % c["jaccard"], "%.3f" % c["dice"],
                          "%.3f" % c["boundary_f"], str(c["under"]), str(c["over"]), "%d/%d" % (c["n_pred"], c["n_true"])])
    figs.save_table("scores", header, table, title="輪郭法の採点(segeval、ノブは既定)",
                    caption="Jaccard/Dice は物体マスク、境界 F は τ = 2 px。2 相の手法(CV・形態学的 CV)は物体の側を真値に"
                            "近い方に取る(反転と書いた行)。照明の勾配では大域の 2 平均が壊れ、エッジで止まる局所の手法が通る。")

    # ── 動画(既存の図の後) ──
    a, b = us["classic"], us["gvf"]
    frames = []
    assert len(a["history"]) > 0
    for pa, pb in zip(a["history"], b["history"]):
        L = _draw_mask(_base(img), U, COL["truth"])
        L = _draw_poly(L, pa, COL["a"])
        R = _draw_mask(_base(img), U, COL["truth"])
        R = _draw_poly(R, pb, COL["b"])
        frames.append(_u8(np.concatenate([_label(L, "古典の snake(エッジの勾配)"), np.ones((L.shape[0], 6, 3)),
                                          _label(R, "GVF snake")], axis=1)))
    figs.save_video("u_shape_snakes", frames, fps=8.0, gif_every=1, gif_width=640,
                    caption="U 字の凹部: 同じ α・β・γ で外力だけ違う。古典(赤)は凹部の口に橋を架けて止まり、辺の途中も外に浮いたまま(エッジの勾配の力は辺の近くにしか届かない)、GVF(青)は奥まで入る。"
                            "緑 = 真の縁。1 コマ = 20 反復。")
    title, w, im, res = keep["gradient"]
    order = [("chan_vese", "Chan–Vese(大域 2 平均)"), ("morph_chan_vese", "形態学的 CV"),
             ("morph_gac", "形態学的測地的 AC"), ("drlse", "DRLSE")]
    K = 40
    seqs = {n: _pick(res[n]["history"], K) for n, _ in order}
    body = w["labels"] > 0
    frames = []
    for i in range(K):
        tiles = []
        assert len(order) > 0
        for n, lab in order:
            m = seqs[n][i]
            if rows["gradient"][n]["flipped"]:
                m = ~m
            t = _draw_mask(_base(im), body, COL["truth"])
            t = _draw_mask(t, m, COL["c"] if n != "chan_vese" else COL["a"])
            tiles.append(_label(t, "%s  J=%.2f" % (lab, rows["gradient"][n]["jaccard"])))
        top = np.concatenate([tiles[0], np.ones((tiles[0].shape[0], 6, 3)), tiles[1]], axis=1)
        bot = np.concatenate([tiles[2], np.ones((tiles[2].shape[0], 6, 3)), tiles[3]], axis=1)
        frames.append(_u8(np.concatenate([top, np.ones((6, top.shape[1], 3)), bot], axis=0)))
    figs.save_video("gradient_world_contours", frames, fps=6.0, gif_every=2, gif_width=560,
                    caption="照明の勾配の上の暗い物体(反転して渡す)。全画面の矩形から 4 手法の輪郭が動く。大域の 2 平均"
                            "(Chan–Vese・形態学的 CV)は明るい側の背景ごと切り、エッジで止まる GAC・DRLSE は物体に貼り付く"
                            "(GAC は雑音の粒を数十個残す = 表の予測の個数)。"
                            "緑 = 真の縁、各手法のコマは反復数に比例して間引いて 40 コマに揃えた。")
    frames = []
    star0 = th["star0"]
    hist = th["curv_star"]["history"]
    tt = th["curv_star"]["times"]
    assert len(hist) > 0
    for i, m in enumerate(hist):
        t = _draw_mask(_base(star0.astype(float) * 0.4 + 0.3), star0, COL["truth"])
        t = _draw_mask(t, m, COL["c"], thick=1)
        ti = tt[min(i * 10, len(tt) - 1)]
        frames.append(_u8(_label(t, "t = %.0f  減った面積 %.0f(6.283 t = %.0f)" % (
            ti, th["curv_star"]["areas"][0] - th["curv_star"]["areas"][min(i * 10, len(tt) - 1)], 2 * math.pi * ti))))
    figs.save_video("curvature_flow_star", frames, fps=10.0, gif_every=1, gif_width=480,
                    caption="凹んだ星形の平均曲率流。凹部は外へ、凸部は内へ動き、丸くなりながら面積は毎時間 2π ずつ減る。")
    print("  図 %d 枚" % len(figs.manifest()))


if __name__ == "__main__":
    sys.exit(main())
