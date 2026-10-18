# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""水田の雑草はどれだけあるか —— 色と肌理だけで雑草の画素を分け、被度を 4 段階で答える(学習器なし)。

問いの型: 圃場の RGB 画像から作物(水稲)の画素と雑草の画素を分け、雑草の程度を
4 段階(0 少ない / 1 中程度 / 2 多い / 3 甚大)で判定する。外観検査のアルゴリズムコンテストの
2026 年の課題(水田の水稲と雑草の割合)と同じ型の問いだが、**そのコンテストの画像は参加者限定で
使っていない**し、ここの数字はコンテストの得点と比べられるものではない(画像も採点も違う)。

道具は全部 Fullseye の op(``cropweed`` 族、台帳 ``opssegmentation`` の ``plant`` / ``classify``):

* ``plant_color_index`` —— ExG・ExR・ExGR・CIVE・NGRDI・VEG(可視 3 バンドの植物の色指標)。
* ``superpixel_color_texture_features`` —— 領域(格子か超画素)ごとの色と肌理の 10 特徴。
* ``fisher_lda_fit`` / ``fisher_lda_score`` —— 2 クラスの Fisher 線形判別(閉形式)。
* ``cover_ratio_grade`` —— 被度を **宣言した境** で段階に分ける。

## 段階の境は評価の前に宣言した(注釈から決めていない)

境は 5 % / 25 % / 50 %(植生調査の被度階級 Braun-Blanquet の区切りを借りた)。実データの注釈を
見る前にこの値に決め、``GRADE_EDGES`` に書いた。注釈から境を合わせれば一致率はいくらでも上がる
—— それは判定の腕前ではなく、境の当てはめの腕前になる。

## 章立て

1. 色指標の閉形式(純緑・灰色・ExGR = ExG − ExR の恒等式)。
2. 真値つきの合成の水田(作物 = 細く濃い葉・雑草 = 広く明るい葉の群落、雑草の割合を 0〜80 % で振る)。
   門: 段階の一致の Cohen のカッパ(自前と ``msa_attribute_agreement`` の 2 実装が一致)・カッパの下限
   (評価前に 0.6 と宣言、Landis–Koch の「かなりの一致」)・**壊す探針**(作物と雑草の色を入れ替えると
   予測した被度の順位が反転する / R と G を入れ替えると植物の画素が消える)。
3. 実データ(``FULLSEYE_WEEDYRICE_DATA`` があるときだけ): WeedyRice-RGBMS(UAV の RGB と
   雑草イネの注釈マスク 734 組、CC BY 4.0)。train で判別を学び、val で特徴の組と領域の作り方を
   1 つ選び、test で **1 回だけ** 採点する。門は全部、統計で決めた形(並べ替え検定の p、
   ブートストラップの 95 % 区間の下限)。データが無いとき(CI)は記録した値を印字して飛ばす。

## 主な実測(2026-10-18)

合成(学習 24 枚・試験 24 枚): 段階の一致 22/24、κ = 0.876、被度の相関 0.999、IoU 0.820。
色を入れ替える探針で予測した被度の順位相関は −0.999(判定は色で決まっている)。

実データ(データ付属の分割、test 148 枚、学習器なし・判別は 10 特徴の 1 次式):

  ===================================== =================================
  段階の一致                            0.574(多数派の段階だけ答えると 0.345)
  Cohen の κ [95 % 区間]                0.424 [0.313, 0.520]、並べ替え p = 0.0005
  被度の相関 r [95 % 区間]              0.826 [0.758, 0.883]、誤差の平均 −7.2 pt
  IoU(ばらまき / 全部雑草と答える)     0.397(0.189 / 0.336)
  R と G を入れ替えた κ                 −0.023(偶然と同じ)
  撮影日を丸ごと外した κ                0.464(日ごとの r: 0.46 / 0.87 / 0.49 / 0.14)
  ===================================== =================================

★正直に書いておくこと:

* val で選んだのは格子(16 px 角)で、SNIC の超画素は格子より悪かった(val の κ 0.443 対 0.499)。
  画像ごとに中央値を引いた特徴を足すと、train の Fisher 比は上がるのに val は下がった(過適合)。
* 判定は少ない側へ寄る(誤差の平均 −7.2 pt)。外れの大きい 9 枚(注釈 7〜9 割を 2〜5 割と言う)は
  **全部 2025-01-15 の飛行**で、その日を丸ごと外して学ぶと日の中の相関は r = 0.14 しかない。
  データ付属の分割は同じ飛行の隣り合うコマ(重なる)を train と test に分けるので、test の数字は
  「見た飛行の別のコマ」の成績で、季節が変わった飛行への汎化はずっと弱い。
* 撮影日を外した κ 0.464 は日をまとめた値で、日ごとの被度の違い(2024-06 は 1〜2 割、2025-01 は 6 割)
  も一致に数えている。日の中で被度の順位を当てる力は上の r の方が正直。

## 実データの出典(CC BY 4.0)

Nguyen V. H., Le C.-D., Truong M.-T., Bui M.-P., Le T.-P. (2025) "A Dataset of Aligned RGB and
Multispectral UAV Imagery for Semantic Segmentation of Weedy Rice", Mendeley Data, V1,
doi:10.17632/vt4s83pxx6.1 —— CC BY 4.0(https://creativecommons.org/licenses/by/4.0/)。
図に載せた実画像は 1/4 に縮小し一部を切り出したもので、注釈と判定を重ねてある(改変あり)。
データの作者がこの PoC を推奨・承認しているわけではない。

★ここの「雑草」は **雑草イネ**(栽培イネと同じ種の雑草化した系統)。広葉の雑草よりずっと
見分けにくい —— 色も葉の形もほぼ同じで、群落の明るさと肌理のわずかな差しかない。
コンテストの課題の雑草(ノビエ・広葉など)とは難しさが違う。

Run::

    py -3.11 examples/poc_weed_rice_ratio.py
    set FULLSEYE_WEEDYRICE_DATA=<展開先>\\WeedyRice-RGBMS-DB & py -3.11 examples/poc_weed_rice_ratio.py
"""
from __future__ import annotations

import os
import time

import numpy as np
from scipy import ndimage

import fullseye as fs

import examplefig as figs      # ★fullseye の後(パスフックがリポジトリ直下を通す)

L = fs.ledger

#: 段階の境(評価の前に宣言。Braun-Blanquet の被度階級 5 % / 25 % / 50 % から借りた)。
GRADE_EDGES = (0.05, 0.25, 0.50)
GRADE_NAMES = ("0 少ない", "1 中程度", "2 多い", "3 甚大")
#: 合成の章のカッパの下限(評価の前に宣言。Landis–Koch 1977 の「かなりの一致」の下端)。
SYN_KAPPA_FLOOR = 0.6
#: 実データの章の有意水準(並べ替え検定)とブートストラップの回数。
ALPHA = 0.01
N_PERM = 2000
N_BOOT = 2000
#: 実データを縮める倍率と、格子の 1 区画の一辺 [縮めた画素]。
REAL_SCALE = 4
BLOCK = 16
DATA_ENV = "FULLSEYE_WEEDYRICE_DATA"
SOURCE = ("Nguyen et al. (2025) WeedyRice-RGBMS, Mendeley Data V1, doi:10.17632/vt4s83pxx6.1, "
          "CC BY 4.0; resized 1/4, cropped, annotation and prediction overlaid")

#: 実データの章を手元で走らせた記録(CI ではデータが無いのでこれを印字する)。2026-10-18、
#: ``FULLSEYE_WEEDYRICE_DATA`` を指定して走らせた出力からそのまま写した。
RECORDED = {
    "選んだ組(val)": "格子",
    "test 枚数": 148,
    "段階の一致": "0.574(多数派だけ 0.345)",
    "κ [95 % 区間]": "0.424 [0.313, 0.520]",
    "並べ替え p": "0.0005",
    "被度の相関 r [95 % 区間]": "0.826 [0.758, 0.883]",
    "IoU / ばらまき / 全部雑草": "0.397 / 0.189 / 0.336",
    "R↔G 入れ替えの κ": "-0.023",
    "撮影日ごとに外した κ(pooled)": "0.464(p = 0.0005)",
    "撮影日ごとに外した r(日ごと)": {"2024_06_02": "n=115 r=0.46 誤差 -0.06",
                                   "2024_06_04": "n=331 r=0.87 誤差 -0.02",
                                   "2024_09_30": "n=41 r=0.49 誤差 -0.02",
                                   "2025_01_15": "n=247 r=0.14 誤差 -0.09"},
    "所要(CPU / 壁)": "384 s / 774 s",
}

_GATES = []


def gate(name, ok, detail):
    """門を 1 つ記録して印字する。最後にまとめて合否を出す。"""
    _GATES.append((name, bool(ok), detail))
    print("  [%s] %s —— %s" % ("PASS" if ok else "FAIL", name, detail))


# --------------------------------------------------------------------------- #
# 採点の道具(自前。カッパは 2 実装で突き合わせる)                              #
# --------------------------------------------------------------------------- #
def confusion(t, p, k=4):
    m = np.zeros((k, k), np.int64)
    np.add.at(m, (np.asarray(t), np.asarray(p)), 1)
    return m


def cohen_kappa(t, p, k=4):
    """Cohen のカッパ κ = (p_o − p_e)/(1 − p_e)(重みなし)。"""
    m = confusion(t, p, k).astype(np.float64)
    n = m.sum()
    po = np.trace(m) / n
    pe = float((m.sum(0) * m.sum(1)).sum()) / (n * n)
    return (po - pe) / (1.0 - pe) if pe < 1.0 else float("nan")


def kappa_by_msa(t, p):
    """同じカッパを ``msa_attribute_agreement``(2 人の検査員の一致)で数える —— 第 2 実装。"""
    n = len(t)
    tab = {"appraiser": np.array(["truth"] * n + ["method"] * n, dtype=object),
           "part": np.r_[np.arange(n), np.arange(n)],
           "rating": np.r_[np.asarray(t), np.asarray(p)].astype(np.int64)}
    return float(np.asarray(L.msa_attribute_agreement(tab)["kappa"])[0])


def perm_p(t, p, seed):
    """予測の段階を並べ替えたときにカッパが観測値以上になる割合(片側、+1 補正)。"""
    g = np.random.default_rng(seed)
    k0 = cohen_kappa(t, p)
    p = np.asarray(p)
    hit = sum(cohen_kappa(t, g.permutation(p)) >= k0 for _ in range(N_PERM))
    return (hit + 1) / (N_PERM + 1)


def boot_ci(stat, n, seed):
    """画像を単位にしたブートストラップの 95 % 区間(パーセンタイル法)。"""
    g = np.random.default_rng(seed)
    vals = np.array([stat(g.integers(0, n, n)) for _ in range(N_BOOT)])
    return float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))


def iou(a, b):
    u = np.count_nonzero(a | b)
    return np.count_nonzero(a & b) / u if u else 1.0


# --------------------------------------------------------------------------- #
# 領域 → 特徴 → 判別 → 画素の判定                                              #
# --------------------------------------------------------------------------- #
def grid_labels(h, w, s=BLOCK):
    nx = (w + s - 1) // s
    return (np.arange(h)[:, None] // s) * nx + np.arange(w)[None, :] // s + 1


def snic_labels(rgb):
    br = rgb.mean(axis=2)
    if br.max() > 1.0:
        br = br / 255.0
    return np.asarray(L.snic_superpixels(br, n_segments=int(br.size / (BLOCK * BLOCK)),
                                         compactness=0.1)["labels"])


def region_features(rgb, lab, centred):
    f = L.superpixel_color_texture_features(rgb, lab)
    X = f["X"]
    if centred:                     # 画像ごとの中央値を引いた列を足す(照明・生育の差を打ち消す)
        X = np.c_[X, X - np.median(X, axis=0)]
    return f, X


def region_truth(lab, f, mask):
    frac = np.bincount(lab.ravel(), weights=mask.ravel().astype(np.float64),
                       minlength=int(lab.max()) + 1)[f["ids"]] / f["sizes"]
    return frac


def predict_mask(model, rgb, lab, centred):
    f, X = region_features(rgb, lab, centred)
    s = L.fisher_lda_score(model, X)
    pm = np.zeros(int(lab.max()) + 1, bool)
    pm[f["ids"]] = s["label"] == 1
    return pm[lab]


def fit_on(samples, labeller, centred):
    """``samples`` = [(rgb, mask)]。注釈が 2 割未満 / 8 割超の領域だけで学ぶ(境の混ざった領域は除く)。"""
    Xs, ys = [], []
    for rgb, mask in samples:
        lab = labeller(rgb)
        f, X = region_features(rgb, lab, centred)
        fr = region_truth(lab, f, mask)
        keep = (fr < 0.2) | (fr > 0.8)
        Xs.append(X[keep])
        ys.append((fr[keep] > 0.5).astype(np.int64))
    return L.fisher_lda_fit(np.vstack(Xs), np.concatenate(ys))


def evaluate(model, samples, labeller, centred):
    ft, fp, ious, ious_rand = [], [], [], []
    preds = []
    for rgb, mask in samples:
        pred = predict_mask(model, rgb, labeller(rgb), centred)
        t, p = float(mask.mean()), float(pred.mean())
        ft.append(t)
        fp.append(p)
        ious.append(iou(pred, mask))
        # 同じ割合でばらまいた予測の IoU の期待値(位置の腕前が無いときの基準線)
        inter = p * t
        ious_rand.append(inter / (p + t - inter) if (p + t - inter) > 0 else 1.0)
        preds.append(pred)
    ft, fp = np.array(ft), np.array(fp)
    gt = L.cover_ratio_grade(ft, edges=GRADE_EDGES)["grade"]
    gp = L.cover_ratio_grade(fp, edges=GRADE_EDGES)["grade"]
    return {"ft": ft, "fp": fp, "gt": gt, "gp": gp, "iou": np.array(ious),
            "iou_rand": np.array(ious_rand), "preds": preds}


def overlay(rgb, mask, color):
    a = np.asarray(rgb, np.float64)
    if a.max() > 1.0:
        a = a / 255.0
    out = a.copy()
    out[mask] = 0.5 * out[mask] + 0.5 * np.asarray(color)
    edge = mask ^ ndimage.binary_erosion(mask, iterations=1)
    out[edge] = color
    return out


# --------------------------------------------------------------------------- #
# 1. 色指標の閉形式                                                             #
# --------------------------------------------------------------------------- #
def section_closed_form():
    print("\n== 1. 色指標の閉形式")
    px = np.array([[[0.0, 1.0, 0.0], [0.5, 0.5, 0.5], [0.3, 0.6, 0.1]]])
    exg = L.plant_color_index(px, index="exg")["index"][0]
    exr = L.plant_color_index(px, index="exr")["index"][0]
    exgr = L.plant_color_index(px, index="exgr")["index"][0]
    cive = L.plant_color_index(px, index="cive")
    gate("純緑の ExG = 2、灰色の ExG = 0", abs(exg[0] - 2.0) < 1e-15 and abs(exg[1]) < 1e-15,
         "ExG = %r" % (exg[:2].round(15).tolist(),))
    gate("ExGR = ExG − ExR(Meyer–Camargo Neto の定義)", np.allclose(exgr, exg - exr, atol=1e-15, rtol=0),
         "最大の差 %.1e" % np.max(np.abs(exgr - (exg - exr))))
    gate("灰色の CIVE = 0.015/3 + 18.78745、植物で小さい(符号 −1)",
         abs(cive["index"][0, 1] - (0.015 / 3 + 18.78745)) < 1e-12 and cive["vegetation_sign"] == -1
         and cive["index"][0, 0] < cive["index"][0, 1],
         "CIVE(灰) = %.5f" % cive["index"][0, 1])
    try:
        L.plant_color_index(np.zeros((4, 4, 3)))
        gate("真っ黒な画像は色度が決まらないので拒否", False, "値を返した")
    except ValueError as exc:
        gate("真っ黒な画像は色度が決まらないので拒否", True, str(exc)[:70])


# --------------------------------------------------------------------------- #
# 2. 合成の水田                                                                 #
# --------------------------------------------------------------------------- #
SYN_H, SYN_W = 192, 256
#: 色(0..1)。作物 = 濃い緑、雑草 = 明るい黄緑、水 = 暗い灰緑、葉の間の陰 = さらに暗い緑。
C_CROP = np.array([0.17, 0.34, 0.12])
C_WEED = np.array([0.36, 0.50, 0.20])
C_WATER = np.array([0.22, 0.25, 0.23])
C_SHADE = np.array([0.08, 0.16, 0.06])


def _leaf(img, cy, cx, length, width, theta, color):
    a, b = 0.5 * length, 0.5 * width
    r = int(np.ceil(a)) + 1
    h, w = img.shape[:2]
    y0, y1 = max(0, int(cy) - r), min(h, int(cy) + r + 1)
    x0, x1 = max(0, int(cx) - r), min(w, int(cx) + r + 1)
    if y1 <= y0 or x1 <= x0:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    u = (xx - cx) * np.cos(theta) + (yy - cy) * np.sin(theta)
    v = -(xx - cx) * np.sin(theta) + (yy - cy) * np.cos(theta)
    t = np.clip(1.0 - (u / a) ** 2, 0.0, None)
    inside = np.abs(v) <= b * np.sqrt(t)
    shade = 0.85 + 0.3 * (u + a) / (2 * a)            # 葉の付け根は暗く、先は明るい
    sub = img[y0:y1, x0:x1]
    sub[inside] = (color[None, :] * shade[inside][:, None])


def synthetic_paddy(seed, weed_fraction, swap_colors=False):
    """真値つきの水田 1 枚: (rgb, 雑草の真値マスク)。雑草の割合は滑らかな乱数場の分位点で **厳密に** 決める。"""
    g = np.random.default_rng(seed)
    field = ndimage.gaussian_filter(g.normal(size=(SYN_H, SYN_W)), 22.0, mode="wrap")
    if weed_fraction <= 0.0:
        weed = np.zeros((SYN_H, SYN_W), bool)
    else:
        thr = np.quantile(field, 1.0 - weed_fraction)
        weed = field > thr
    crop_c, weed_c = (C_WEED, C_CROP) if swap_colors else (C_CROP, C_WEED)
    img = np.empty((SYN_H, SYN_W, 3))
    img[:] = C_SHADE
    water = ndimage.gaussian_filter(g.normal(size=(SYN_H, SYN_W)), 3.0) > 1.0
    img[water & ~weed] = C_WATER
    row_dir = g.uniform(0, np.pi)
    for _ in range(int(SYN_H * SYN_W / 38)):            # 作物: 細く長く、向きが畝に揃う
        cy, cx = g.uniform(0, SYN_H), g.uniform(0, SYN_W)
        if weed[int(cy), int(cx)] and g.random() < 0.85:
            continue
        _leaf(img, cy, cx, g.uniform(16, 26), g.uniform(1.6, 2.4), row_dir + g.normal(0, 0.25),
              crop_c * g.uniform(0.85, 1.15))
    ys, xs = np.nonzero(weed)
    if ys.size:
        for _ in range(int(ys.size / 30)):              # 雑草: 広く短く、向きはばらばら
            k = g.integers(ys.size)
            _leaf(img, ys[k] + g.uniform(-0.5, 0.5), xs[k] + g.uniform(-0.5, 0.5), g.uniform(10, 16),
                  g.uniform(3.5, 5.5), g.uniform(0, np.pi), weed_c * g.uniform(0.85, 1.15))
    yy, xx = np.mgrid[0:SYN_H, 0:SYN_W]
    illum = 0.9 + 0.2 * (xx / SYN_W) * np.cos(row_dir) ** 2      # 日の当たりのむら
    img = img * illum[..., None] + g.normal(0.0, 0.01, img.shape)
    return np.clip(img, 0.0, 1.0), weed


def section_synthetic():
    print("\n== 2. 合成の水田(作物 = 細く濃い葉、雑草 = 広く明るい葉。雑草の割合は厳密に置く)")
    n = 24
    f_train = 0.01 + 0.79 * np.arange(n) / (n - 1)
    f_test = f_train + 0.79 / (2 * (n - 1))
    train = [synthetic_paddy(1000 + i, f) for i, f in enumerate(f_train)]
    test = [synthetic_paddy(2000 + i, f) for i, f in enumerate(f_test)]
    lab = grid_labels(SYN_H, SYN_W)

    def labeller(_):
        return lab
    model = fit_on(train, labeller, centred=False)
    ev = evaluate(model, test, labeller, centred=False)
    k_own = cohen_kappa(ev["gt"], ev["gp"])
    k_msa = kappa_by_msa(ev["gt"], ev["gp"])
    print("  学習 %d 枚 / 試験 %d 枚、区画 %d px 角、Fisher 比 J = %.2f"
          % (n, n, BLOCK, model["fisher_ratio"]))
    print("  被度の誤差の平均 %+.3f、相関 r = %.3f、段階の一致 %d/%d、IoU の平均 %.3f"
          % (np.mean(ev["fp"] - ev["ft"]), np.corrcoef(ev["ft"], ev["fp"])[0, 1],
             int((ev["gt"] == ev["gp"]).sum()), n, ev["iou"].mean()))
    gate("カッパの 2 実装が一致(自前 / msa_attribute_agreement)", abs(k_own - k_msa) < 1e-12,
         "κ = %.6f / %.6f" % (k_own, k_msa))
    gate("合成の段階の一致 κ > %.1f(評価前に宣言)" % SYN_KAPPA_FLOOR, k_own > SYN_KAPPA_FLOOR, "κ = %.3f" % k_own)
    gate("位置の腕前: IoU が同じ割合でばらまいた予測より大きい(全枚)",
         bool(np.all(ev["iou"] > ev["iou_rand"])),
         "IoU %.3f > ばらまき %.3f(平均)" % (ev["iou"].mean(), ev["iou_rand"].mean()))

    # 壊す探針 1: 作物と雑草の色を入れ替える(形と配置は同じ種で同じ)
    swapped = [synthetic_paddy(2000 + i, f, swap_colors=True) for i, f in enumerate(f_test)]
    ev_s = evaluate(model, swapped, labeller, centred=False)
    rho = np.corrcoef(np.argsort(np.argsort(ev["fp"])), np.argsort(np.argsort(ev_s["fp"])))[0, 1]
    lo = ev["gt"] == 0
    hi = ev["gt"] == 3
    print("  探針(色の入れ替え): 予測した被度の順位相関 %.3f、真の段階 0 → 入替後の段階 %s、真の段階 3 → %s"
          % (rho, np.bincount(ev_s["gp"][lo], minlength=4).tolist(), np.bincount(ev_s["gp"][hi], minlength=4).tolist()))
    gate("探針: 作物と雑草の色を入れ替えると被度の順位が反転(順位相関 < 0)", rho < 0.0, "ρ = %.3f" % rho)
    gate("探針: 真の段階 0(雑草 5 % 未満)の画像は入れ替えると段階 2 以上",
         bool(np.all(ev_s["gp"][lo] >= 2)), "入替後 %s" % ev_s["gp"][lo].tolist())

    # 壊す探針 2: R と G を入れ替える —— 植物の色指標 ExGR > 0 の画素がほぼ消える
    img0 = test[len(test) // 2][0]
    v0 = np.nanmean(L.plant_color_index(img0, index="exgr")["index"] > 0)
    v1 = np.nanmean(L.plant_color_index(img0[..., [1, 0, 2]], index="exgr")["index"] > 0)
    gate("探針: R と G を入れ替えると ExGR > 0(植物)の画素が消える", v0 > 0.5 and v1 < 0.05,
         "植物の画素 %.1f %% → %.1f %%" % (100 * v0, 100 * v1))

    # 図
    picks = [int(np.argmin(np.abs(f_test - q))) for q in (0.03, 0.18, 0.40, 0.70)]
    panels, caps = [], []
    for i in picks:
        rgb, m = test[i]
        panels += [rgb, overlay(rgb, m, (1.0, 0.0, 1.0)), overlay(rgb, ev["preds"][i], (1.0, 0.85, 0.0))]
        caps += ["合成 %d: 雑草 %.0f %%" % (i, 100 * ev["ft"][i]),
                 "真値(段階 %d)" % ev["gt"][i],
                 "判定 %.0f %%(段階 %d)" % (100 * ev["fp"][i], ev["gp"][i])]
    figs.save_grid("synthetic_paddy", panels, caps, ncols=3,
                   title="合成の水田: 原画・真値(紫)・判定(黄)",
                   caption="作物は細く濃い葉が畝の向きに揃い、雑草は広く明るい葉がばらばらの向き。雑草の割合は乱数場の"
                           "分位点で厳密に置いた。判定は %d px 角の区画ごとの Fisher 判別。" % BLOCK)
    i = picks[0]
    figs.save_grid("synthetic_color_swap",
                   [test[i][0], overlay(test[i][0], ev["preds"][i], (1.0, 0.85, 0.0)),
                    swapped[i][0], overlay(swapped[i][0], ev_s["preds"][i], (1.0, 0.85, 0.0))],
                   ["原画(雑草 %.0f %%)" % (100 * ev["ft"][i]), "判定 %.0f %%" % (100 * ev["fp"][i]),
                    "作物と雑草の色だけ入れ替え", "判定 %.0f %%(段階 %d → %d)" % (100 * ev_s["fp"][i], ev["gp"][i], ev_s["gp"][i])],
                   ncols=2, title="壊す探針: 色を入れ替えると判定が反転する",
                   caption="葉の形と配置は同じ乱数で同じ。色だけ入れ替えると、判別は作物を雑草と読み、被度の段階が反転する"
                           " —— 判定を支えているのが色だという証拠。")
    return ev


# --------------------------------------------------------------------------- #
# 3. 実データ(WeedyRice-RGBMS、CC BY 4.0)                                    #
# --------------------------------------------------------------------------- #
def _read_list(root, name):
    out = []
    with open(os.path.join(root, name), encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(os.path.splitext(os.path.basename(line.split()[0].replace("\\", "/")))[0])
    return out


def _load(root, base):
    from PIL import Image
    im = Image.open(os.path.join(root, "RGB", base + ".JPG")).convert("RGB")
    w, h = im.size
    size = (w // REAL_SCALE, h // REAL_SCALE)
    rgb = np.asarray(im.resize(size, Image.BILINEAR))
    m = np.asarray(Image.open(os.path.join(root, "Masks", base + ".png")).resize(size, Image.NEAREST)) > 127
    return rgb, m


def section_real():
    root = os.environ.get(DATA_ENV, "").strip()
    print("\n== 3. 実データ(WeedyRice-RGBMS、UAV の RGB と雑草イネの注釈、CC BY 4.0)")
    if not root or not os.path.isdir(os.path.join(root, "RGB")):
        print("  [skip] %s が無い(画像は repo に入れない)。手元で走らせた記録:" % DATA_ENV)
        for k, v in RECORDED.items():
            print("    %-38s %s" % (k, v))
        return None
    t0, w0 = time.process_time(), time.time()
    sets = {k: [b for b in _read_list(root, k + "_list.txt")
                if os.path.exists(os.path.join(root, "RGB", b + ".JPG"))] for k in ("train", "val", "test")}
    print("  train %d / val %d / test %d 枚(データ付属の分割)、1/%d に縮小、区画 %d px 角"
          % (len(sets["train"]), len(sets["val"]), len(sets["test"]), REAL_SCALE, BLOCK))
    data = {k: [_load(root, b) for b in v] for k, v in sets.items()}

    # val で 1 つ選ぶ(宣言順で同点は先): 領域の作り方 2 通り x 特徴の組 2 通り
    cands = [("格子", "grid", False), ("格子 + 画像内の中央値を引いた列", "grid", True),
             ("SNIC 超画素", "snic", False), ("SNIC + 画像内の中央値を引いた列", "snic", True)]
    best = None
    rows = []
    for title, kind, centred in cands:
        lab_of = (lambda rgb: grid_labels(*rgb.shape[:2])) if kind == "grid" else snic_labels
        model = fit_on(data["train"], lab_of, centred)
        ev = evaluate(model, data["val"], lab_of, centred)
        kv = round(cohen_kappa(ev["gt"], ev["gp"]), 6)
        rows.append([title, "%.2f" % model["fisher_ratio"], "%.3f" % kv, "%.3f" % ev["iou"].mean(),
                     "%.3f" % np.corrcoef(ev["ft"], ev["fp"])[0, 1]])
        print("  val: %-34s J = %.2f  κ = %.3f  IoU = %.3f" % (title, model["fisher_ratio"], kv, ev["iou"].mean()))
        if best is None or kv > best[0]:
            best = (kv, title, lab_of, centred, model)
    _, title, lab_of, centred, model = best
    print("  → val で選んだ: %s(test はこの 1 つだけで 1 回採点する)" % title)
    figs.save_table("validation_choice", ["領域 / 特徴", "Fisher 比 J", "val の κ", "val の IoU", "val の r"], rows,
                    title="val で 1 つ選ぶ(test は見ない)",
                    caption="train で判別を学び、val の段階の一致 κ がいちばん高い組を選んだ。同点は表の順で先。")

    ev = evaluate(model, data["test"], lab_of, centred)
    n = len(ev["ft"])
    k_own = cohen_kappa(ev["gt"], ev["gp"])
    k_msa = kappa_by_msa(ev["gt"], ev["gp"])
    p = perm_p(ev["gt"], ev["gp"], seed=20261018)
    r = float(np.corrcoef(ev["ft"], ev["fp"])[0, 1])
    r_lo, r_hi = boot_ci(lambda ix: np.corrcoef(ev["ft"][ix], ev["fp"][ix])[0, 1], n, seed=20261019)
    d = ev["iou"] - ev["iou_rand"]
    d_lo, d_hi = boot_ci(lambda ix: d[ix].mean(), n, seed=20261020)
    k_lo, k_hi = boot_ci(lambda ix: cohen_kappa(ev["gt"][ix], ev["gp"][ix]), n, seed=20261021)
    agree = float((ev["gt"] == ev["gp"]).mean())
    maj = float(np.max(np.bincount(ev["gt"], minlength=4)) / n)
    iou_all = float(np.mean(ev["ft"]))       # 全部を雑草と言ったときの IoU = 真の割合
    print("  test %d 枚: 段階の一致 %.3f(多数派の段階だけ答えると %.3f)、κ = %.3f [%.3f, %.3f]、並べ替え p = %.4f"
          % (n, agree, maj, k_own, k_lo, k_hi, p))
    print("  被度の相関 r = %.3f [%.3f, %.3f]、誤差の平均 %+.3f、IoU %.3f(ばらまき %.3f・全部雑草 %.3f)"
          % (r, r_lo, r_hi, np.mean(ev["fp"] - ev["ft"]), ev["iou"].mean(), ev["iou_rand"].mean(), iou_all))
    gate("実データ: カッパの 2 実装が一致", abs(k_own - k_msa) < 1e-12, "κ = %.6f / %.6f" % (k_own, k_msa))
    gate("実データ: 段階の一致は偶然より上(並べ替え検定 p < %.2f)" % ALPHA, p < ALPHA, "p = %.4f" % p)
    gate("実データ: 被度の相関の 95 % 区間の下限 > 0", r_lo > 0.0, "r = %.3f [%.3f, %.3f]" % (r, r_lo, r_hi))
    gate("実データ: IoU − ばらまきの IoU の 95 % 区間の下限 > 0(位置の腕前)", d_lo > 0.0,
         "差 %.3f [%.3f, %.3f]" % (d.mean(), d_lo, d_hi))

    # 壊す探針: R と G を入れ替えた test 画像
    swapped = [(rgb[..., [1, 0, 2]], m) for rgb, m in data["test"]]
    ev_s = evaluate(model, swapped, lab_of, centred)
    k_s = cohen_kappa(ev_s["gt"], ev_s["gp"])
    gate("探針(実データ): R と G を入れ替えると κ が元の 95 % 区間の下限を割る", k_s < k_lo,
         "κ %.3f → %.3f(段階の分布 %s)" % (k_own, k_s, np.bincount(ev_s["gp"], minlength=4).tolist()))

    lodo = leave_one_date_out(root, sets)

    cpu, wall = time.process_time() - t0, time.time() - w0
    rec = {"選んだ組(val)": title, "test 枚数": n, "段階の一致": "%.3f(多数派だけ %.3f)" % (agree, maj),
           "κ [95 % 区間]": "%.3f [%.3f, %.3f]" % (k_own, k_lo, k_hi), "並べ替え p": "%.4f" % p,
           "被度の相関 r [95 % 区間]": "%.3f [%.3f, %.3f]" % (r, r_lo, r_hi),
           "IoU / ばらまき / 全部雑草": "%.3f / %.3f / %.3f" % (ev["iou"].mean(), ev["iou_rand"].mean(), iou_all),
           "R↔G 入れ替えの κ": "%.3f" % k_s,
           "撮影日ごとに外した κ(pooled)": "%.3f(p = %.4f)" % (lodo["kappa"], lodo["p"]),
           "撮影日ごとに外した r(日ごと)": lodo["per_date"],
           "所要(CPU / 壁)": "%.0f s / %.0f s" % (cpu, wall)}
    print("  記録(RECORDED に写す):")
    for k, v in rec.items():
        print("    %r: %r," % (k, v))

    # 図
    order = np.argsort(ev["ft"])
    picks = [order[int(q * (n - 1))] for q in (0.15, 0.5, 0.85)]
    panels, caps = [], []
    for i in picks:
        rgb, m = data["test"][i]
        pr = ev["preds"][i]
        panels += [rgb / 255.0, overlay(rgb, m, (1.0, 0.0, 1.0)), overlay(rgb, pr, (1.0, 0.85, 0.0))]
        caps += ["test: 雑草イネ %.0f %%" % (100 * ev["ft"][i]), "注釈(段階 %d)" % ev["gt"][i],
                 "判定 %.0f %%(段階 %d、IoU %.2f)" % (100 * ev["fp"][i], ev["gp"][i], ev["iou"][i])]
    figs.save_grid("real_examples", panels, caps, ncols=3,
                   title="実データ: 原画・注釈(紫)・判定(黄)",
                   caption="UAV の水田の RGB(1/4 に縮小)。紫が注釈の雑草イネ、黄が区画ごとの判別。出典: " + SOURCE)
    figs.save_plot("fraction_scatter",
                   [("test の 1 枚", ev["ft"], ev["fp"]), ("y = x", np.array([0, 1.0]), np.array([0, 1.0]))]
                   + [("" if j else "段階の境(宣言)", np.array([e, e]), np.array([0, 1.0])) for j, e in enumerate(GRADE_EDGES)],
                   xlabel="注釈の雑草イネの割合", ylabel="判定の割合", title="被度: 注釈と判定",
                   kinds=["scatter", "line"] + ["line"] * len(GRADE_EDGES),
                   styles=[None, "dashed"] + ["dotted"] * len(GRADE_EDGES),
                   colors=["emphasis", "reference"] + ["neutral"] * len(GRADE_EDGES), xlim=(0, 1), ylim=(0, 1),
                   caption="点 1 つが test の 1 枚。破線が y = x、点線が評価前に宣言した段階の境(5 / 25 / 50 %%)。"
                           "r = %.3f [%.3f, %.3f]。" % (r, r_lo, r_hi), source=SOURCE)
    cm = confusion(ev["gt"], ev["gp"])
    figs.save_table("grade_confusion", ["注釈 \\ 判定"] + list(GRADE_NAMES),
                    [[GRADE_NAMES[i]] + ["%d" % c for c in cm[i]] for i in range(4)],
                    title="段階の混同行列(test %d 枚)" % n,
                    caption="対角が一致。κ = %.3f、並べ替え検定 p = %.4f。境は評価前に宣言した 5 / 25 / 50 %%。" % (k_own, p))
    bins = np.linspace(0, 1, 21)
    ht = np.histogram(ev["ft"], bins)[0]
    hp = np.histogram(ev["fp"], bins)[0]
    xc = 0.5 * (bins[1:] + bins[:-1])
    figs.save_plot("fraction_histogram",
                   [("注釈", xc, ht), ("判定", xc, hp)]
                   + [("" if j else "段階の境(宣言)", np.array([e, e]), np.array([0, max(ht.max(), hp.max())]))
                      for j, e in enumerate(GRADE_EDGES)],
                   xlabel="雑草イネの割合", ylabel="枚数", title="被度の分布(test)",
                   styles=[None, None] + ["dotted"] * len(GRADE_EDGES),
                   colors=["reference", "emphasis"] + ["neutral"] * len(GRADE_EDGES), xlim=(0, 1),
                   caption="判定は少ない側へ寄る(誤差の平均 %+.0f pt)。0〜5 %% の枚数が注釈より多く、注釈で 8 割を超える"
                           "画像の一部を 2〜5 割と言う。" % (100 * np.mean(ev["fp"] - ev["ft"])), source=SOURCE)
    rgb0 = data["test"][0][0]
    names = list(L.superpixel_color_texture_features(rgb0, grid_labels(*rgb0.shape[:2]))["names"])
    if centred:
        names = names + [nm + "(画像内で中心化)" for nm in names]
    w = np.asarray(model["w"])
    top = np.argsort(-np.abs(w))[:8]
    figs.save_table("lda_weights", ["特徴", "重み(標準化後)"],
                    [[names[j], "%+.3f" % w[j]] for j in top], col_w=240,
                    title="判別を支える特徴(重みの大きい順)",
                    caption="正の重みは雑草イネの側。Fisher 比 J = %.2f。" % model["fisher_ratio"])
    i = picks[1]
    rgb, m = swapped[i]
    figs.save_grid("real_channel_swap",
                   [data["test"][i][0] / 255.0, overlay(data["test"][i][0], ev["preds"][i], (1.0, 0.85, 0.0)),
                    rgb / 255.0, overlay(rgb, ev_s["preds"][i], (1.0, 0.85, 0.0))],
                   ["原画", "判定 %.0f %%" % (100 * ev["fp"][i]), "R と G を入れ替え",
                    "判定 %.0f %%" % (100 * ev_s["fp"][i])], ncols=2,
                   title="壊す探針(実データ): R と G を入れ替える",
                   caption="色を入れ替えると判別の入力の分布から外れ、判定が崩れる。出典: " + SOURCE)
    return ev


def leave_one_date_out(root, sets):
    """撮影日(=飛行)を丸ごと外して学び、外した日で採点する。データ付属の分割は同じ飛行の隣り合う
    コマが train と test に分かれる(コマは重なる)ので、それより厳しい問いになる。"""
    names = sets["train"] + sets["val"] + sets["test"]
    dates = np.array([b[13:23] for b in names])
    cache = []
    for b in names:
        rgb, m = _load(root, b)
        lab = grid_labels(*rgb.shape[:2])
        f, X = region_features(rgb, lab, False)
        fr = region_truth(lab, f, m)
        cache.append((X, fr, f["sizes"], float(m.mean())))
    ft_all, fp_all, rows, per = [], [], [], {}
    for d in sorted(set(dates.tolist())):
        tr = [c for c, dd in zip(cache, dates) if dd != d]
        X = np.vstack([c[0][(c[1] < 0.2) | (c[1] > 0.8)] for c in tr])
        y = np.concatenate([(c[1][(c[1] < 0.2) | (c[1] > 0.8)] > 0.5).astype(np.int64) for c in tr])
        model = L.fisher_lda_fit(X, y)
        ft, fp = [], []
        for c, dd in zip(cache, dates):
            if dd != d:
                continue
            lab1 = L.fisher_lda_score(model, c[0])["label"]
            fp.append(float((lab1 * c[2]).sum() / c[2].sum()))
            ft.append(c[3])
        ft, fp = np.array(ft), np.array(fp)
        gt = L.cover_ratio_grade(ft, edges=GRADE_EDGES)["grade"]
        gp = L.cover_ratio_grade(fp, edges=GRADE_EDGES)["grade"]
        r = float(np.corrcoef(ft, fp)[0, 1]) if ft.size > 2 and ft.std() > 0 else float("nan")
        per[d] = "n=%d r=%.2f 誤差 %+.2f" % (ft.size, r, float(np.mean(fp - ft)))
        rows.append([d.replace("_", "-"), "%d" % ft.size, "%.2f" % ft.mean(), "%.2f" % fp.mean(),
                     "%+.3f" % float(np.mean(fp - ft)), "%.3f" % r, "%d/%d" % (int((gt == gp).sum()), ft.size)])
        ft_all.append(ft)
        fp_all.append(fp)
        print("  撮影日 %s を外す: %3d 枚 注釈 %.2f 判定 %.2f 誤差 %+.3f r = %.3f 段階の一致 %d/%d"
              % (d, ft.size, ft.mean(), fp.mean(), np.mean(fp - ft), r, int((gt == gp).sum()), ft.size))
    ft, fp = np.concatenate(ft_all), np.concatenate(fp_all)
    gt = L.cover_ratio_grade(ft, edges=GRADE_EDGES)["grade"]
    gp = L.cover_ratio_grade(fp, edges=GRADE_EDGES)["grade"]
    k = cohen_kappa(gt, gp)
    p = perm_p(gt, gp, seed=20261022)
    print("  撮影日を外した判定をまとめると: 段階の一致 %.3f、κ = %.3f(並べ替え p = %.4f)" % (float((gt == gp).mean()), k, p))
    gate("実データ(撮影日を丸ごと外す): 段階の一致は偶然より上(並べ替え検定 p < %.2f)" % ALPHA, p < ALPHA,
         "κ = %.3f、p = %.4f" % (k, p))
    figs.save_table("leave_one_date_out", ["外した撮影日", "枚数", "注釈の平均", "判定の平均", "誤差", "r", "段階の一致"],
                    rows, title="撮影日を丸ごと外して学ぶ",
                    caption="データ付属の分割は同じ飛行の隣り合うコマを train と test に分ける(コマは重なる)。"
                            "撮影日ごとに外すと、季節・生育・日の当たりが学習に無い日を当てることになる。")
    return {"kappa": k, "p": p, "per_date": per}


def main():
    t0, w0 = time.process_time(), time.time()
    section_closed_form()
    section_synthetic()
    section_real()
    n_fail = sum(1 for _, ok, _ in _GATES if not ok)
    print("\n== まとめ: 門 %d 本、FAIL %d(CPU %.1f s / 壁 %.1f s)"
          % (len(_GATES), n_fail, time.process_time() - t0, time.time() - w0))
    if figs.errors():                    # 図が書けなかったら黙らない(数値は正しくても展示から図が消える)
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
        raise SystemExit(1)
    if n_fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
