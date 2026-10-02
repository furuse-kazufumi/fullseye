# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC(セグメンテーション拡充 第 3 陣): グラフ・階層・閾値の定理 —— graph cut(最大フロー = 最小カット)、α-expansion、
統計的領域併合 SRM、成分木の属性開放、準平坦領域 = 最小全域木の切断、dynamics の階層分水嶺と ultrametric contour map、
超画素 SNIC / quick shift、閾値 4 定理(三角法・isodata・Kittler・Kapur)を、真値つきの合成世界(:mod:`segworld`)で
走らせ、物差し(:mod:`segeval`)で採点し、λ・q・閾値 θ を振ったときの分割の変化(粗 ⇄ 細)をコマ送りの動画にする。

方針: **学習器は載せない**。どの手法も定理か第 2 実装の門を持つ(:mod:`seggraph`)。この PoC はその門を小さな厳密問題と
実際の絵の上で踏み、さらに **どの世界でどれが勝つか** を門にする:

門(真値の出どころ):
  1. **最大フロー = 最小カット**: 3×4 の 40 問で graph cut のエネルギーが総当たりの最小と一致、整数のフロー = カット。
  2. **α-expansion の 2c**: 3 ラベル 3×3 の 80 問(Potts と打ち切り線形)で E ≤ 2c E*(BVZ 2001 Theorem 6.1)、
     受け入れの列は単調減少。乱数の 80 問はどれも大域解に届くので、全画素がラベル 2 の局所解から抜けられない
     3×3 の罠(E = 72 / E* = 57、比 1.26)を明示して、上界が空振りでないことも示す。
  3. **属性開放は代数的開放**: 冪等・反拡大、``skimage.morphology.area_opening`` と画素一致。
  4. **準平坦領域 = 最小全域木の切断**: 6 つの α で一致、α を増やすと入れ子。
  5. **階層分水嶺**: 盆地の全 3 つ組で ultrametric、閾値で切った UCM = 階層の段、深さが既知の 6 盆地で
     「生き残る盆地の数 = dynamics > θ の数」。
  6. **超画素**: SNIC の全ラベルが 4-連結、quick shift は τ を増やすと入れ子。
  7. **閾値**: isodata は画素の上で不動点(残差 0)、三角法 = skimage、Kittler は 2 ガウスの Bayes の閾値(2 次方程式の根)
     から 2.5 ビン以内、Kapur = 総当たりの最大エントロピー。
  8. **触れ合う粒(自明でない)**: 距離変換の地形の階層分水嶺は θ = 0 で **過分割**(粒より多い)、ある θ の区間で
     粒の数ちょうど、大きな θ で **未分割** に倒れる —— 1 本の木から両側の失敗と正解の帯を読める。切れ目はくびれに
     沿う(θ = 2 で境界 F ≥ 0.975。同じ高さの辺を最急降下の順に処理する効果、番号順だと 0.964 で格子に沿う段が出た)。
  9. **graph cut の λ(自明でない)**: 雑音の多い粒は λ を上げると Dice が上がり(≥ +0.1)、同じ λ で幅 1〜3 px の線は
     消えて下がる(≤ −0.1)。3 つの seed で同じ向き。平滑項は「細い物」と「雑音」を区別しない。
 10. **SRM の述語は平均しか見ない(自明でない)**: 結晶粒はある q で VI < 1 bit まで下がるが、平均が同じで質感だけ違う
     世界ではどの q でも「全部 1 領域」の VI より良くならない(3 つの seed)。
 11. **照明の勾配で閾値が分かれる(自明でない)**: Kittler(2 クラスの分散を別々に持つ)は 3 seed すべて Dice ≥ 0.9、
     isodata(2 平均の中点)は 3 seed すべて < 0.5。二峰のはっきりした粒では 4 法とも ≥ 0.95。
 12. **第 2 実装**: SNIC と ``skimage.segmentation.slic`` の境界の再現率が 0.05 以内、quick shift と skimage の quickshift が
     0.02 以内。
 13. 図なしで 60 秒以内。

正直に書くこと:
* ノブは世界ごとに合わせていない(graph cut の μ は isodata の 2 平均、SRM の q は 1〜1024 を 2 倍刻み)。
* SRM の述語の係数と q に対する単調性は原論文で確認できていない(seggraph の docstring)。単調性はここでは門にしない。
* 物体が暗い世界(照明の勾配・細い構造)は画像を反転して渡す(世界の宣言)。影のある部品はどの手法も Dice < 0.5
  (影と暗い面に負ける、第 1・2 陣と同じ限界)—— 表に出すだけで門にはしない。

Run: py -3.11 examples/poc_graph_hierarchy_segmentation.py   (図は FULLSEYE_FIGURE_DIR を設定したときだけ書く)
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
import seggraph as GR  # noqa: E402
import segeval as SE  # noqa: E402
import segworld as SW  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

warnings.filterwarnings("ignore")

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET", "reduced" if os.environ.get("CI") else "full") == "reduced"
T0 = time.time()
OK = []
SEEDS = (0, 1, 2)
LAMS = [0.0, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.3]
QS = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]
THS = [0.0, 0.25, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 8.0]
THRESH = [("三角法", GR.threshold_triangle), ("isodata", GR.threshold_isodata), ("Kittler", GR.threshold_kittler),
          ("Kapur", GR.threshold_kapur)]


def gate(name, cond, detail=""):
    OK.append(bool(cond))
    print("  [%s] %s %s" % ("PASS" if cond else "FAIL", name, detail))


def dice(mask, labels):
    return SE.seg_dice_jaccard(mask.astype(np.int64), (labels > 0).astype(np.int64))["dice"]


# ───────────────────────────── 1〜7. 定理の門 ─────────────────────────────
def theorems():
    print("== 1. 定理の門(小さな厳密問題)")
    rng = np.random.default_rng(11)
    n_ok = n_flow = 0
    for _ in range(40):
        im = rng.integers(0, 10, (3, 4)).astype(float)
        lam = float(rng.integers(0, 7))
        r = GR.graph_cut_binary(im, lam=lam, mu_bg=2, mu_fg=7)
        b = GR._brute_force_binary(im, lam=lam, mu_bg=2, mu_fg=7)
        n_ok += int(abs(r["energy"] - b["energy"]) < 1e-12 and abs(r["cut_value"] - r["energy"]) < 1e-12)
        n_flow += int(r["cut_value_int"] == r["flow_value_int"])
    w = SW.world_blobs_touching(10, overlap=0.2, seed=0, noise=0.15)
    big = GR.graph_cut_binary(w["image"], lam=0.05)
    gate("graph cut: 総当たりの最小と一致、最大フロー = 最小カット(整数で厳密)", n_ok == 40 and n_flow == 40
         and big["cut_value_int"] == big["flow_value_int"],
         "%d/40 一致・%d/40 フロー = カット、160×160 の世界でもフロー %d = カット %d(scale %.3g、丸めの上界 %.1e)"
         % (n_ok, n_flow, big["flow_value_int"], big["cut_value_int"], big["scale"], big["quantization_bound"]))

    rng = np.random.default_rng(7)
    worst = 0.0
    n_b = n_m = 0
    for pw in ("potts", "truncated_linear"):
        for _ in range(40):
            im = rng.integers(0, 9, (3, 3)).astype(float)
            lam = float(rng.integers(1, 30))
            r = GR.alpha_expansion(im, [1, 4, 7], lam=lam, pairwise=pw, truncation=2)
            b = GR._brute_force_multi(im, [1, 4, 7], lam=lam, pairwise=pw, truncation=2)
            n_b += int(r["energy"] <= r["bound_factor"] * b["energy"] + 1e-9)
            n_m += int(bool(np.all(np.diff(r["energies"]) < 0)) and bool(np.all(r["move_minima"][:, 0] <= r["move_minima"][:, 1] + 1e-9)))
            worst = max(worst, r["energy"] / max(b["energy"], 1e-12))
    # 罠: 全部を真ん中のラベル 2 にした解は、1 と 3 を同時に動かさないと抜けられない(1 回の expansion は 1 ラベルだけ)
    trap = np.array([[1, 6, 7], [6, 8, 8], [5, 6, 1]], float)
    rt = GR.alpha_expansion(trap, [1, 4, 7], lam=12.0)
    bt = GR._brute_force_multi(trap, [1, 4, 7], lam=12.0)
    tr_ratio = rt["energy"] / bt["energy"]
    gate("α-expansion: E ≤ 2c E*(Potts c = 1、打ち切り線形 c = 2)、受け入れは単調減少、罠の問題では局所解 > 大域解",
         n_b == 80 and n_m == 80 and 1.0 < tr_ratio <= rt["bound_factor"],
         "%d/80 が上界内、%d/80 が単調(乱数の 80 問の最悪の比 %.3f)。罠の 3×3: expansion は全画素ラベル 2 で E = %.0f、"
         "大域解 E* = %.0f(比 %.3f ≤ 2c = 2)" % (n_b, n_m, worst, rt["energy"], bt["energy"], tr_ratio))

    img = w["image"]
    a = GR.area_opening_attr(img, 40)
    a2 = GR.area_opening_attr(a["image"], 40)
    sk = None
    try:
        from skimage import morphology as M
        sk = bool(np.array_equal(a["image"], M.area_opening(img, area_threshold=40, connectivity=1)))
    except ImportError:
        print("    skimage が無い: 第 2 実装の照合は飛ばす")
    gate("属性開放: 冪等・反拡大、skimage の area_opening と画素一致", np.array_equal(a["image"], a2["image"])
         and bool(np.all(a["image"] <= img)) and sk is not False,
         "節 %d 個のうち %d を残す、下がった画素 %d、skimage と一致 %s" % (a["n_nodes"], a["n_nodes_kept"], a["removed"], sk))

    g = np.round(SW.world_grains_voronoi(36, seed=0)["image"] * 20) / 20
    al = [0.0, 0.05, 0.1, 0.15, 0.3, 1.0]
    at = GR.alpha_tree(g, al)
    eq = [bool(np.array_equal(GR.quasi_flat_zones(g, x)["labels"], at["labels"][k])) for k, x in enumerate(al)]
    gate("準平坦領域 = 最小全域木の重み ≤ α の切断(6 つの α)、α を増やすと入れ子", all(eq) and at["nested"],
         "領域数 %s" % at["n_zones"].tolist())

    sm = ndi.gaussian_filter(np.random.default_rng(3).random((80, 80)), 2.0)
    u = GR.ultrametric_contour_map(sm, distance_matrix=True)
    D = u["distance"]
    viol = int(np.count_nonzero(D[:, None, :] > np.maximum(D[:, :, None], D[None, :, :]) + 1e-12))
    h, ww = sm.shape
    idx = np.arange(h * ww).reshape(h, ww)
    th = float(np.median(u["levels"]))
    ki = np.concatenate([idx[:, :-1][u["ucm_h"] <= th], idx[:-1, :][u["ucm_v"] <= th]])
    kj = np.concatenate([idx[:, 1:][u["ucm_h"] <= th], idx[1:, :][u["ucm_v"] <= th]])
    cut = GR._components(h * ww, ki, kj).reshape(h, ww)
    hw = GR.hierarchical_watershed(sm, threshold=th)["labels"]
    same = GR._is_nested(cut, hw) and GR._is_nested(hw, cut)
    depths = (0.1, 0.25, 0.4, 0.55, 0.7, 0.9)
    terr = np.ones((60, 80))
    for d, (y, x) in zip(depths, [(10, 10), (10, 40), (10, 65), (40, 10), (40, 40), (40, 65)]):
        terr[y:y + 10, x:x + 8] = 1 - d
    cnt_ok = [GR.hierarchical_watershed(terr, threshold=t)["n_regions"] == 1 + sum(1 for d in depths[:-1] if d > t)
              for t in (0.0, 0.2, 0.3, 0.5, 0.6, 0.8)]
    gate("階層分水嶺: ultrametric(盆地の全 3 つ組)、UCM を θ で切る = 階層の段、生き残る盆地 = dynamics > θ の数",
         viol == 0 and same and all(cnt_ok),
         "盆地 %d 個 → 3 つ組 %d 個で違反 %d、θ = 中央値で一致 %s、深さ既知の 6 盆地で %s"
         % (D.shape[0], D.shape[0] ** 3, viol, same, cnt_ok))

    gw = SW.world_grains_voronoi(36, seed=0)
    con = [GR.snic_superpixels(gw["image"], n_segments=K)["all_connected"] for K in (50, 200, 400)]
    labs = [GR.quickshift(gw["image"], max_dist=t)["labels"] for t in (2.0, 4.0, 6.0, 9.0)]
    nest = [GR._is_nested(x, y) for x, y in zip(labs[:-1], labs[1:])]
    gate("超画素: SNIC の全ラベルが 4-連結(K = 50/200/400)、quick shift は τ = 2→4→6→9 で入れ子", all(con) and all(nest),
         "quick shift の領域数 %s" % [int(x.max()) for x in labs])

    thr = theorem_thresholds()
    return {"ucm": u, "smooth": sm, "terrain": terr, "thr": thr}


def theorem_thresholds():
    rng = np.random.default_rng(0)
    P1, m1, s1, m2, s2 = 0.75, 0.3, 0.05, 0.7, 0.08
    n1 = 60000
    x = rng.permutation(np.concatenate([rng.normal(m1, s1, n1), rng.normal(m2, s2, 80000 - n1)])).reshape(200, 400)
    iso = GR.threshold_isodata(x)
    tri = GR.threshold_triangle(x)
    try:
        from skimage import filters as F
        tri_sk = float(F.threshold_triangle(x))
        iso_sk = float(F.threshold_isodata(x))
    except ImportError:
        tri_sk = iso_sk = None
    a = 1 / (2 * s1 ** 2) - 1 / (2 * s2 ** 2)
    b = -m1 / s1 ** 2 + m2 / s2 ** 2
    c = m1 ** 2 / (2 * s1 ** 2) - m2 ** 2 / (2 * s2 ** 2) - math.log(P1 * s2 / ((1 - P1) * s1))
    roots = [float(np.real(r)) for r in np.roots([a, b, c]) if m1 < np.real(r) < m2]
    tb = roots[0]
    kt = GR.threshold_kittler(x)
    kp = GR.threshold_kapur(x)
    bw = (x.max() - x.min()) / 256
    cnt, _ = np.histogram(x, bins=256, range=(x.min(), x.max()))
    p = cnt / cnt.sum()
    Hs = []
    for t in range(p.size - 1):
        qa, qb = p[:t + 1], p[t + 1:]
        if qa.sum() <= 0 or qb.sum() <= 0:
            Hs.append(-np.inf)
            continue
        qa, qb = qa[qa > 0] / qa.sum(), qb[qb > 0] / qb.sum()
        Hs.append(float(-(qa * np.log(qa)).sum() - (qb * np.log(qb)).sum()))
    gate("閾値: isodata は画素の上の不動点(残差 0)、三角法 = skimage、Kittler は Bayes の閾値から 2.5 ビン以内、Kapur = 総当たり",
         iso["residual"] == 0.0 and (tri_sk is None or tri["threshold"] == tri_sk)
         and abs(kt["threshold"] - tb) <= 2.5 * bw and kp["bin"] == int(np.argmax(Hs)),
         "isodata t = %.4f(skimage %s、反復 %d)、三角法 %.4f(skimage %s)、Kittler %.4f / Bayes %.4f(ビン幅 %.4f)、Kapur ビン %d"
         % (iso["threshold"], "%.4f" % iso_sk if iso_sk is not None else "なし", iso["n_iter"], tri["threshold"],
            "%.4f" % tri_sk if tri_sk is not None else "なし", kt["threshold"], tb, bw, kp["bin"]))
    return {"x": x, "bayes": tb, "iso": iso, "tri": tri, "kit": kt, "kap": kp}


# ───────────────────────────── 8〜12. 世界 ─────────────────────────────
def touching_blobs():
    print("== 2. 触れ合う粒: 階層分水嶺の θ を振る")
    w = SW.world_blobs_touching(10, overlap=0.2, seed=0)
    m = GR.threshold_isodata(w["image"])["mask"]
    relief = -ndi.distance_transform_edt(m)
    rows = []
    labs = []
    assert len(THS) > 0
    for th in THS:
        r = GR.hierarchical_watershed(relief, threshold=th, mask=m)
        uo = SE.seg_under_over_segmentation(r["labels"], w["labels"])
        cm = SE.seg_object_counts_match(r["labels"], w["labels"])
        rows.append((th, r["n_regions"], uo["over"], uo["under"], bool(cm["counts_match"])))
        labs.append(r["labels"])
    exact = [th for th, n, o, u_, okm in rows if okm and o == 0 and u_ == 0]
    bf2 = SE.seg_boundary_f(labs[THS.index(2.0)], w["labels"], tau=2)["f"]
    print("    θ: 領域数 / 過分割 / 未分割 = %s" % ", ".join("%.2g:%d/%d/%d" % (t, n, o, u_) for t, n, o, u_, _ in rows))
    gate("触れ合う粒: θ = 0 で過分割、ある θ の帯で粒の数ちょうど(過・未分割 0)、大きな θ で未分割",
         rows[0][2] > 0 and rows[0][1] > 10 and len(exact) >= 2 and rows[-1][3] > 0 and rows[-1][1] < 10 and bf2 >= 0.975,
         "θ = 0 で %d 領域(過分割 %d)、ちょうど 10 の θ = %s、θ = %.0f で %d 領域(未分割 %d)、θ = 2 の境界 F(τ = 2)%.3f"
         % (rows[0][1], rows[0][2], exact, rows[-1][0], rows[-1][1], rows[-1][3], bf2))
    return {"world": w, "rows": rows, "labels": labs, "mask": m, "relief": relief}


def lambda_tradeoff():
    print("== 3. graph cut の λ: 雑音の粒と細い線")
    curves = {}
    ups, downs = [], []
    keep = {}
    assert len(SEEDS) > 0
    for s in SEEDS:
        wb = SW.world_blobs_touching(10, overlap=0.2, seed=s, noise=0.15)
        wt = SW.world_thin_structures(seed=s)
        xb, xt = wb["image"], 1.0 - wt["image"]
        db, dt, mb, mt = [], [], [], []
        for lam in LAMS:
            rb = GR.graph_cut_binary(xb, lam=lam)
            rt = GR.graph_cut_binary(xt, lam=lam)
            db.append(dice(rb["mask"], wb["labels"]))
            dt.append(dice(rt["mask"], wt["labels"]))
            if s == 0:
                mb.append(rb["mask"])
                mt.append(rt["mask"])
        curves[s] = (db, dt)
        k = LAMS.index(0.1)
        ups.append(db[k] - db[0])
        downs.append(dt[k] - dt[0])
        if s == 0:
            keep = {"blobs": wb, "thin": wt, "mb": mb, "mt": mt}
    print("    λ = %s" % LAMS)
    for s in SEEDS:
        print("    seed %d: 粒 Dice %s / 線 Dice %s" % (s, np.round(curves[s][0], 3).tolist(), np.round(curves[s][1], 3).tolist()))
    gate("graph cut の λ = 0.1: 雑音の粒は Dice +0.1 以上、同じ λ で細い線は −0.1 以下(3 seed で同じ向き)",
         min(ups) >= 0.1 and max(downs) <= -0.1,
         "粒 %s / 線 %s" % (np.round(ups, 3).tolist(), np.round(downs, 3).tolist()))
    keep["curves"] = curves
    return keep


def srm_worlds():
    print("== 4. SRM の q: 結晶粒と質感")
    res = {}
    gr_best, tx_ok = [], []
    for s in SEEDS:
        for name, w in (("grains", SW.world_grains_voronoi(36, seed=s)), ("texture", SW.world_texture_regions(seed=s))):
            nreg, voi, labs = [], [], []
            for q in QS:
                r = GR.statistical_region_merging(w["image"], q=q)
                nreg.append(r["n_regions"])
                voi.append(SE.seg_score_card(r["labels"], w["labels"])["voi"])
                if s == 0:
                    labs.append(r["labels"])
            trivial = SE.seg_score_card(np.ones_like(w["labels"]), w["labels"])["voi"]
            res[(name, s)] = {"n": nreg, "voi": voi, "trivial": trivial, "labels": labs, "world": w}
            if name == "grains":
                gr_best.append(min(voi))
            else:
                tx_ok.append(min(voi) >= trivial - 0.01)
    for (name, s), v in sorted(res.items()):
        print("    %s seed %d: 領域数 %s、VI 最小 %.2f(1 領域の VI %.2f)" % (name, s, v["n"], min(v["voi"]), v["trivial"]))
    gate("SRM: 結晶粒は VI < 1 bit まで下がる q がある、質感の世界はどの q でも 1 領域の VI より良くならない(3 seed)",
         max(gr_best) < 1.0 and all(tx_ok), "結晶粒の VI 最小 %s、質感 %s" % (np.round(gr_best, 2).tolist(), tx_ok))
    return res


def threshold_worlds():
    print("== 5. 閾値 4 法: 照明の勾配と二峰の粒")
    table = {}
    kit, iso = [], []
    blobs_all = []
    for s in SEEDS:
        wg = SW.world_gradient_illumination(seed=s)
        wb = SW.world_blobs_touching(10, overlap=0.2, seed=s)
        dg = {n: dice(f(1.0 - wg["image"])["mask"], wg["labels"]) for n, f in THRESH}
        db = {n: dice(f(wb["image"])["mask"], wb["labels"]) for n, f in THRESH}
        table[s] = (dg, db)
        kit.append(dg["Kittler"])
        iso.append(dg["isodata"])
        blobs_all.append(min(db.values()))
        print("    seed %d: 勾配 %s / 粒 %s" % (s, {k: round(v, 3) for k, v in dg.items()}, {k: round(v, 3) for k, v in db.items()}))
    wp = SW.world_parts_with_shadow(seed=0)
    dp = {n: dice(f(wp["image"])["mask"], wp["labels"]) for n, f in THRESH}
    print("    (参考)影のある部品: %s(どれも < 0.5 = 影と暗い面、門にしない)" % {k: round(v, 3) for k, v in dp.items()})
    gate("照明の勾配: Kittler は 3 seed すべて Dice ≥ 0.9、isodata は < 0.5。二峰の粒は 4 法とも ≥ 0.95",
         min(kit) >= 0.9 and max(iso) < 0.5 and min(blobs_all) >= 0.95,
         "Kittler %s / isodata %s / 粒の最小 %s" % (np.round(kit, 3).tolist(), np.round(iso, 3).tolist(), np.round(blobs_all, 3).tolist()))
    return {"table": table, "parts": dp, "gradient": SW.world_gradient_illumination(seed=0)}


def superpixels():
    print("== 6. 超画素: SNIC / quick shift と skimage")
    w = SW.world_grains_voronoi(36, seed=0)
    s = GR.snic_superpixels(w["image"], n_segments=200, compactness=0.1)
    q = GR.quickshift(w["image"], kernel_size=3, max_dist=6)
    qs_ = GR.superpixel_quality(s["labels"], w["labels"])
    qq = GR.superpixel_quality(q["labels"], w["labels"])
    out = {"world": w, "snic": s, "qs": q, "q_snic": qs_, "q_qs": qq}
    try:
        from skimage import segmentation as SG
        sl = SG.slic(w["image"], n_segments=200, compactness=0.1, channel_axis=None, start_label=1)
        sk = SG.quickshift(np.dstack([w["image"]] * 3), ratio=1.0 / math.sqrt(3.0), kernel_size=3, max_dist=6,
                           convert2lab=False) + 1
        q_sl = GR.superpixel_quality(sl, w["labels"])
        q_sk = GR.superpixel_quality(sk, w["labels"])
        out.update({"slic": sl, "q_slic": q_sl, "q_skqs": q_sk})
        for nm, v in (("SNIC", qs_), ("SLIC(skimage)", q_sl), ("quick shift", qq), ("quickshift(skimage)", q_sk)):
            print("    %-20s 超画素 %4d  境界再現率 %.3f  CUSE %.3f  UE %.3f" % (nm, v["n_superpixels"], v["boundary_recall"],
                                                                              v["cuse"], v["ue_np"]))
        gate("第 2 実装: SNIC と SLIC の境界再現率 0.05 以内(どちらも ≥ 0.95)、quick shift と skimage が 0.02 以内",
             qs_["boundary_recall"] >= 0.95 and q_sl["boundary_recall"] >= 0.95
             and abs(qs_["boundary_recall"] - q_sl["boundary_recall"]) <= 0.05
             and abs(qq["boundary_recall"] - q_sk["boundary_recall"]) <= 0.02,
             "SNIC %.3f / SLIC %.3f、quick shift %.3f / skimage %.3f" % (qs_["boundary_recall"], q_sl["boundary_recall"],
                                                                        qq["boundary_recall"], q_sk["boundary_recall"]))
    except ImportError as exc:
        gate("第 2 実装: skimage が要る", False, str(exc))
    return out


def main() -> int:
    print("BUDGET: %s(FULLSEYE_POC_BUDGET、CI では reduced が既定。この PoC は予算で変わらない)" % ("reduced" if REDUCED else "full"))
    th = theorems()
    tb = touching_blobs()
    lt = lambda_tradeoff()
    sr = srm_worlds()
    tw = threshold_worlds()
    sp = superpixels()
    elapsed = time.time() - T0
    gate("図なしで 60 秒以内", elapsed < 60.0, "%.1f s" % elapsed)
    if figs.enabled():
        figures(th, tb, lt, sr, tw, sp)
        if figs.errors():
            print("図の書き出しで失敗:", "; ".join(figs.errors()))
            OK.append(False)
    print("== 結果: %d / %d 門, %.1f s(CPU %.1f s)" % (sum(OK), len(OK), time.time() - T0, time.process_time()))
    print("PASS" if all(OK) else "FAIL")                    # tests/test_poc_scripts_run.py は exit 0 と PASS の両方を見る
    return 0 if all(OK) else 1


# ───────────────────────────── 図 ─────────────────────────────
UP = 3


def _palette(k):
    """ラベル 1..k の色(黄金比で色相を回す、決定的)。0 は黒。"""
    h = (np.arange(k + 1) * 0.6180339887) % 1.0
    s, v = 0.55, 0.95
    i = np.floor(h * 6).astype(int)
    f = h * 6 - i
    p, q, t = v * (1 - s), v * (1 - f * s), v * (1 - (1 - f) * s)
    tab = np.stack([np.choose(i % 6, [v, q, p, p, t, v]), np.choose(i % 6, [t, v, v, q, p, p]),
                    np.choose(i % 6, [p, p, t, v, v, q])], axis=1)
    tab[0] = 0.0
    return tab


def _labels_rgb(lab, im=None, alpha=0.55):
    pal = _palette(int(lab.max()))
    rgb = pal[lab]
    if im is not None:
        g = np.clip((im - im.min()) / max(float(np.ptp(im)), 1e-12), 0, 1)[..., None]
        rgb = alpha * rgb + (1 - alpha) * g
    b = np.zeros(lab.shape, bool)
    b[:, :-1] |= lab[:, 1:] != lab[:, :-1]
    b[:-1, :] |= lab[1:, :] != lab[:-1, :]
    rgb[b] = 1.0
    return np.repeat(np.repeat(rgb, UP, axis=0), UP, axis=1)


def _mask_rgb(mask, truth, im):
    g = np.clip((im - im.min()) / max(float(np.ptp(im)), 1e-12), 0, 1)
    rgb = np.repeat(g[..., None] * 0.6, 3, axis=2)
    rgb[mask & truth] = (0.95, 0.85, 0.2)
    rgb[mask & ~truth] = (0.95, 0.2, 0.15)
    rgb[~mask & truth] = (0.2, 0.55, 1.0)
    return np.repeat(np.repeat(rgb, UP, axis=0), UP, axis=1)


def _label(rgb, text):
    import annotate as AN
    return np.asarray(AN.text_box(rgb, text, (6, 6), anchor="lt", font_size=13, max_width=rgb.shape[1] - 12))


def _u8(rgb):
    return (np.clip(np.asarray(rgb, np.float64), 0, 1) * 255).astype(np.uint8)


def _hcat(tiles):
    assert len(tiles) > 0
    hmax = max(t.shape[0] for t in tiles)
    out = []
    for i, t in enumerate(tiles):
        if t.shape[0] < hmax:
            t = np.concatenate([t, np.ones((hmax - t.shape[0], t.shape[1], 3))], axis=0)
        out.append(t)
        if i < len(tiles) - 1:
            out.append(np.ones((hmax, 6, 3)))
    return np.concatenate(out, axis=1)


def figures(th, tb, lt, sr, tw, sp):
    print("== 7. 図")
    w = tb["world"]
    u = th["ucm"]
    gs = sr[("grains", 0)]["world"]
    tx = sr[("texture", 0)]["world"]
    panels = [w["image"], w["labels"].astype(float), tb["relief"], gs["image"], tx["image"], tw["gradient"]["image"],
              th["smooth"], np.log1p(u["ucm"] / max(float(u["ucm"].max()), 1e-12) * 50)]
    caps = ["触れ合う粒(10 個)", "真値", "地形 = −距離変換(isodata のマスク)", "結晶粒(36)", "質感だけ違う 3 領域",
            "照明の勾配の上の暗い物体", "滑らかな雑音の地形", "その UCM(log、明るい = 遅く消える境界)"]
    figs.save_grid("inputs", panels, captions=caps, title="入力: 真値つきの世界と、階層分水嶺の地形・UCM", ncols=4,
                   gray=[True, False, False, True, True, True, False, False],
                   caption="UCM は隣り合う画素が同じ領域になる最小の閾値。盆地の全 3 つ組で ultrametric(違反 0)、閾値で切ると"
                           "階層の 1 段になる(門 5)。")
    rows = tb["rows"]
    figs.save_plot("watershed_theta", [("領域数", [r[0] for r in rows], [r[1] for r in rows]),
                                       ("過分割", [r[0] for r in rows], [r[2] for r in rows]),
                                       ("未分割", [r[0] for r in rows], [r[3] for r in rows]),
                                       ("真の粒の数 10", [rows[0][0], rows[-1][0]], [10, 10])],
                   xlabel="閾値 θ(dynamics、px)", ylabel="個数", title="触れ合う粒: 階層分水嶺の閾値で過分割 → ちょうど → 未分割",
                   caption="−距離変換の地形の 1 本の最小全域森を、dynamics ≤ θ の辺で結ぶ。θ = 0 は雑音の凹みまで盆地にして"
                           "過分割、θ = 0.5〜3 px で粒の数ちょうど、くびれの深さ(重なり 20 %)を超えると隣の粒と融合する。",
                   kinds=["line", "scatter", "scatter", "line"])
    c0 = lt["curves"]
    lx = np.log10(np.maximum(np.array(LAMS), 1e-3))
    assert len(SEEDS) > 0
    mb_ = np.mean([c0[s][0] for s in SEEDS], axis=0)
    mt_ = np.mean([c0[s][1] for s in SEEDS], axis=0)
    series = [("雑音の粒(3 seed の平均)", lx, mb_), ("細い線(3 seed の平均)", lx, mt_)]
    figs.save_plot("graph_cut_lambda", series, xlabel="log10 λ(左端 −3 は λ = 0)", ylabel="Dice", size=(720, 420),
                   ylim=(0.0, 1.05),
                   title="graph cut: λ は雑音を消し、同じ強さで細い線も消す",
                   caption="エネルギーは毎回厳密に最小(最大フロー = 最小カット)。それでも正解に近づくかは別で、平滑項は"
                           "「境界の長さ」を罰するので、細長い物ほど消える。雑音の粒(σ = 0.15)は λ = 0.1 で +0.12、"
                           "幅 1〜3 px の線は同じ λ で −0.1 以上下がる(3 seed の平均。seed ごとの値は実行ログ)。",
                   kinds=["line", "line"])
    g0, t0 = sr[("grains", 0)], sr[("texture", 0)]
    lq = np.log2(np.array(QS, float))
    figs.save_plot("srm_q", [("結晶粒 VI", lq, g0["voi"]), ("質感 VI", lq, t0["voi"]),
                             ("質感: 全部 1 領域の VI", [lq[0], lq[-1]], [t0["trivial"]] * 2)],
                   xlabel="log2 q(大きいほど併合を渋る = 細かい)", size=(720, 420), ylabel="VI(bit、小さいほど良い)",
                   title="SRM: 平均の差だけを見る併合の述語",
                   caption="結晶粒は q = 256 付近で VI が 1 bit を切る。質感だけ違う世界では、q を上げると平均の揺らぎで"
                           "細切れになるだけで、どの q でも「全部 1 領域」より良くならない(q ≤ 32 では質感の VI は 1 領域の線と重なって見えない)。", kinds=["line", "line", "line"])
    tr = th["thr"]
    x = tr["x"]
    cnt, edges = np.histogram(x, bins=128, range=(x.min(), x.max()))
    ctr = 0.5 * (edges[:-1] + edges[1:])
    top = float(cnt.max())
    ser = [("ヒストグラム", ctr, cnt.astype(float))]
    for nm, t in (("Bayes(閉形式)", tr["bayes"]), ("三角法", tr["tri"]["threshold"]), ("isodata", tr["iso"]["threshold"]),
                  ("Kittler", tr["kit"]["threshold"]), ("Kapur", tr["kap"]["threshold"])):
        ser.append(("%s %.3f" % (nm, t), [t, t], [0.0, top]))
    figs.save_plot("thresholds", ser, xlabel="画素の値", ylabel="画素数", size=(720, 420), title="2 ガウスの混合(0.75·N(0.3, 0.05) + 0.25·N(0.7, 0.08))",
                   caption="Kittler は 2 クラスの分散を別々に持つので Bayes の最小誤差の閾値(2 次方程式の根)に乗る。isodata は"
                           "2 平均の中点、三角法は山頂と裾を結ぶ線から最も遠いビン、Kapur は 2 クラスのエントロピーの和の最大。",
                   kinds=["line"] * len(ser))
    header = ["世界", "手法", "Dice / 境界再現率", "備考"]
    table = []
    for s in SEEDS:
        dg, db = tw["table"][s]
        for nm, _ in THRESH:
            table.append(["勾配 seed %d" % s, nm, "%.3f" % dg[nm], ""])
    for nm, v in tw["parts"].items():
        table.append(["影の部品", nm, "%.3f" % v, "影と暗い面(限界)"])
    for nm, key in (("SNIC", "q_snic"), ("SLIC(skimage)", "q_slic"), ("quick shift", "q_qs"), ("quickshift(skimage)", "q_skqs")):
        if key in sp:
            v = sp[key]
            table.append(["結晶粒", nm, "%.3f" % v["boundary_recall"], "超画素 %d、CUSE %.3f" % (v["n_superpixels"], v["cuse"])])
    figs.save_table("scores", header, table, title="閾値 4 法と超画素の採点(segeval)",
                    caption="照明の勾配では背景の裾が長く、2 平均の中点(isodata)は背景の中に落ちる。Kittler は背景の分散を"
                            "大きく見積もって物体側へ寄る。超画素は境界の再現率(τ = 2 px)と補正つき未分割誤差 CUSE。")
    grid = [_labels_rgb(sp["snic"]["labels"], sp["world"]["image"]), _labels_rgb(sp["qs"]["labels"], sp["world"]["image"])]
    gcap = ["SNIC(K = 200、全ラベル 4-連結)", "quick shift(τ = 6)"]
    if "slic" in sp:
        grid.append(_labels_rgb(sp["slic"], sp["world"]["image"]))
        gcap.append("SLIC(skimage、第 2 実装)")
    figs.save_grid("superpixels", grid, captions=gcap, title="結晶粒の超画素", ncols=len(grid),
                   caption="白 = 超画素の境界。真の粒界は全部どれかの境界の 2 px 以内(境界再現率)。SNIC(m = 0.1)は"
                           "暗い粒界の線そのものを細い超画素として切り出す(粒界の両側に白線が 2 本並ぶ所)= 値の距離が"
                           "位置の距離より強い設定の表れ。")

    # ── 動画(既存の図の後) ──
    m = tb["mask"]
    frames = []
    order = list(range(len(THS)))[::-1]
    assert len(order) > 0
    for i in order + order[::-1]:
        t_, n_, o_, u_, _ = rows[i]
        frames.append(_u8(_label(_labels_rgb(tb["labels"][i], w["image"]),
                                 "θ = %.2g px  領域 %d(真 10)過分割 %d 未分割 %d" % (t_, n_, o_, u_))))
    figs.save_video("watershed_theta_sweep", frames, fps=2.0, gif_every=1, gif_width=480,
                    caption="触れ合う粒の階層分水嶺。θ を大 → 小 → 大に振る: 1 領域から粒の数ちょうどを経て雑音の凹みで"
                            "過分割へ、そして戻る。どのコマも同じ 1 本の木の切り方(入れ子)。")
    gl = sr[("grains", 0)]["labels"]
    frames = []
    assert len(gl) > 0
    for i, lab in enumerate(gl):
        frames.append(_u8(_label(_labels_rgb(lab, gs["image"]), "SRM q = %d  領域 %d(真 36)VI %.2f bit" % (
            QS[i], int(lab.max()), sr[("grains", 0)]["voi"][i]))))
    figs.save_video("srm_q_sweep", frames, fps=1.5, gif_every=1, gif_width=480,
                    caption="結晶粒の SRM。q = 1(全部 1 領域)から 1024(細切れ)へ。q = 256 前後で粒界に沿う。")
    blobs, thin = lt["blobs"], lt["thin"]
    frames = []
    assert len(LAMS) > 0
    for i, lam in enumerate(LAMS):
        L = _label(_mask_rgb(lt["mb"][i], blobs["labels"] > 0, blobs["image"]), "雑音の粒 λ = %g  Dice %.3f" % (lam, lt["curves"][0][0][i]))
        R = _label(_mask_rgb(lt["mt"][i], thin["labels"] > 0, 1.0 - thin["image"]), "細い線 λ = %g  Dice %.3f" % (lam, lt["curves"][0][1][i]))
        frames.append(_u8(_hcat([L, R])))
    figs.save_video("graph_cut_lambda_sweep", frames, fps=1.5, gif_every=1, gif_width=720,
                    caption="graph cut の λ を 0 → 0.3。黄 = 正解の物体、赤 = 余計、青 = 取り逃し。左の雑音の点は消え、"
                            "右の細い線も同じ λ で途切れて消える。")
    print("  図 %d 枚" % len(figs.manifest()))


if __name__ == "__main__":
    sys.exit(main())
