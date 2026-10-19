# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""良品だけから学ぶパッチ特徴の異常検知 ―― 深層特徴を使わず、古典特徴で「分布」と「記憶」を比べる。

外観検査の研究で最も厚いのは「良品の特徴量を覚え、外れたパッチを欠陥とする」型の異常検知で、その中身は
(a) パッチ特徴の**位置ごとの正規分布**(マハラノビス距離)と、(b) パッチ特徴の**記憶バンク**(k 近傍、記憶は貪欲被覆で間引く)
の 2 つに大別できる。特徴は普通は事前学習した深層網の中間層だが、この PoC は**古典特徴**(多重解像度の勾配・Gabor・
LBP・周波数帯・色)だけで同じ骨格を組み、**1 つの採点台**(``anomeval``: 画素 AUROC・AUPRO・画像 AUROC・F1 最大)で変種を比べる。
新 op 8 本: ``patch_features`` / ``patchdist_fit`` / ``patchdist_score`` / ``patchbank_fit`` / ``patchbank_score``(``anomaly_patch``)と、
採点の追加 ``anomaly_pixel_f1_max`` / ``anomaly_image_f1_max`` / ``anomaly_operating_point``(``anomeval``)。

変種として再現する構成(ViEW の題目のみ。本文・図は写さず、式から自前で実装):
  * 位置ごとの正規分布(特徴の次元を絞る / 縮小推定を宣言する): ViEW2022『Fourier-Convolutional PaDiMによる異常検知』
    (周波数帯の特徴を足す変種)、ViEW2023『Scale-Invariantな欠陥検出のための多重解像度PaDiMの提案』(多重解像度の変種)、
    ViEW2025『異常検知モデルにおけるプリミティブ特徴量の検討』(勾配だけ・1 解像度の変種)。
  * 記憶バンクと近傍: ViEW2024『事前学習済みDNN中間特徴量の位置を考慮した近傍法による異常検知』(位置を足す変種)、
    ViEW2025『高速検査のための統計的近傍予測に基づく改良型PatchCoreの提案』と ViEW2021『高解像度画像からの特徴量抽出による
    鍛造部品の異常検知と計算量抑制』(記憶の間引き: 精度と時間の交換)。
  * 運用: ViEW2024『半教師あり異常検知技術を用いた画像外観検査の高速化の取り組み』の問い「見逃しを許さない閾値はどこか」に、
    再現率を信頼水準つきで保証する運用点(``anomaly_operating_point``)で答える。

多段(各段に op の外の真値か実データの門):

1. **特徴の閉形式**: 傾き a の斜面の勾配の大きさは a。
2. **合成の 3 つの世界**(確率場・向きの揃わない織り・位置の決まった部品)に、点と細い傷(真の欠陥マスクつき)を植えて 8 変種 + 既存の
   変動モデル(``varmodel``)+ 無作為の対照を同じ採点台で比べる。
3. **良品の枚数 5・20・80** で順位が変わらないか。
4. **論理的な異常**(正しい模様が違う場所にある): 位置を見ない記憶は見逃し、位置を見る記憶は見つける。
5. **記憶の間引き**: 記憶 2〜100 % で精度・被覆半径・所要時間(CPU 時間)。
6. **縮小推定の宣言**: 良品 5 枚で特異な共分散を、宣言(``auto``)で通し、宣言なし(``none``)は拒否する。
7. **再現率を保証する運用点**: 保証を 300 回の繰り返しで確かめ、保証なしの分位点と比べる。
8. **公開実データ**(あるときだけ): DAGM 2007 Class1(確率的なテクスチャ)と VisA pcb1・candle。

予想(2026-10-19、着手前): ★「深層特徴の代わりの古典特徴でも、記憶バンクは位置ごとの正規分布より良品の枚数に強い」。
合成の確率場では**当たった**(3.: 位置ごとの正規分布は良品 5・20・80 枚のどれでも最下位)。実データでも当たり(VisA pcb1 で
記憶バンク 10 % の画素 AUROC 0.990 対 位置ごとの正規分布 0.847)、さらに**予想外**が 2 つ: (1) 位置の重みは合成の論理的な異常には
効いたが、実データでは pcb1 の画素 AUROC を下げ(0.990 → 0.969)、candle ではほぼ変わらない(0.895 → 0.901)。(2) 特徴を増やすと
悪くなる場合がある ―― DAGM の欠陥は「細かい模様が消えた滑らかな斑」で、勾配だけ・1 解像度の記憶(AUROC 0.768)が
51 次元の特徴の記憶(0.623)を上回る。DAGM の画像ごとの判定(画像 AUROC 0.50〜0.61)は偶然並みで、画素の地図の AUROC だけでは
合否に使えない。実データの全数は 8. と ``RECORDED``。

実データ(repo には同梱しない。環境変数で渡す。無ければ合成の章だけを走らせ、実データの章は記録値を印字する。CI は合成のみ):

  Wieler, M., Hahn, T., Hamprecht, F. A. Weakly Supervised Learning for Industrial Optical Inspection (DAGM 2007).
  Zenodo 12750201、CC BY 4.0(Zenodo の記録の license 欄 cc-by-4.0 を取得時に確認)。環境変数 ``FULLSEYE_DAGM_DATA`` に
  ``Class1/`` を展開した dir の親を渡す。改変: 2×2 の平均で縮小。注釈は楕円の弱い注釈。

  Zou, Y., Jeong, J., Pemula, L., Zhang, D., Dabeer, O. (2022). SPot-the-Difference Self-Supervised Pre-training for Anomaly
  Detection and Segmentation. ECCV 2022. データセット VisA: https://github.com/amazon-science/spot-diff、
  "The data is released under the CC BY 4.0 license." 環境変数 ``FULLSEYE_VISA_DATA`` に VisA を展開した dir
  (``split_csv/1cls.csv`` と ``pcb1/`` がある所)を渡す。改変: 灰色化と平均による縮小。ダウンロード物は信頼しない入力として扱い、
  画像と CSV を読むだけ。

Fullseye 寄与: パッチ特徴の「分布」と「記憶」を、縮小推定の宣言・被覆半径・位置の重み・再現率の保証つきの op 族にした。
採点台 ``anomeval`` は方法に依存しないので、変動モデル・RPCA・ゴールデン比較とも同じ物差しで比べられる。
"""
from __future__ import annotations

import csv
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402  公開経路 fs.ledger.<名前>

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"
DAGM = os.environ.get("FULLSEYE_DAGM_DATA", "").strip()         # Class1 を展開した dir の親
VISA = os.environ.get("FULLSEYE_VISA_DATA", "").strip()
S = 64
DAGM_SOURCE = ("DAGM 2007 Class1 (Wieler, Hahn, Hamprecht), Zenodo 12750201, CC BY 4.0; 2x2 mean downsampling")
VISA_SOURCE = ("VisA (Zou et al., ECCV 2022), github.com/amazon-science/spot-diff, CC BY 4.0; "
               "gray + mean downsampling")

#: 実データの章の記録値(2026-10-19、FULLSEYE_DAGM_DATA / FULLSEYE_VISA_DATA ありで実行)。CI ではこれを印字する。
RECORDED = {"lines": [
    'DAGM 2007 Class1(確率的なテクスチャ、(256, 256) px): 良品 40 枚で学び、試験 100 枚(不良 50・良品 50、楕円の弱い注釈)',
    '変動モデル(既存)                          AUROC 0.436  AUPRO 0.088  画像AU 0.484  F1max 0.036',
    'プリミティブ(勾配のみ・1 解像度)                 AUROC 0.665  AUPRO 0.185  画像AU 0.505  F1max 0.061',
    '多重解像度(勾配・Gabor・LBP)                AUROC 0.532  AUPRO 0.129  画像AU 0.610  F1max 0.039',
    '全位置まとめた正規分布                        AUROC 0.606  AUPRO 0.160  画像AU 0.546  F1max 0.051',
    '記憶バンク(10 %)                        AUROC 0.623  AUPRO 0.188  画像AU 0.562  F1max 0.053',
    '位置つき記憶バンク(10 %)                    AUROC 0.591  AUPRO 0.169  画像AU 0.558  F1max 0.049',
    'プリミティブ + 記憶バンク(10 %)               AUROC 0.768  AUPRO 0.474  画像AU 0.532  F1max 0.105',
    'VisA pcb1(1/6、(178, 234) px): 良品 20 枚で学び、試験 200 枚(不良 100・良品 100)',
    '多重解像度(勾配・Gabor・LBP)                AUROC 0.847  AUPRO 0.694  画像AU 0.805  F1max 0.042',
    '全位置まとめた正規分布                        AUROC 0.938  AUPRO 0.607  画像AU 0.515  F1max 0.439',
    '記憶バンク(10 %)                        AUROC 0.990  AUPRO 0.875  画像AU 0.935  F1max 0.720',
    '位置つき記憶バンク(10 %)                    AUROC 0.969  AUPRO 0.790  画像AU 0.782  F1max 0.410',
    'プリミティブ + 記憶バンク(10 %)               AUROC 0.783  AUPRO 0.648  画像AU 0.707  F1max 0.273',
    'VisA candle(1/6、(194, 214) px): 良品 20 枚で学び、試験 200 枚(不良 100・良品 100)',
    '多重解像度(勾配・Gabor・LBP)                AUROC 0.790  AUPRO 0.399  画像AU 0.576  F1max 0.032',
    '全位置まとめた正規分布                        AUROC 0.886  AUPRO 0.644  画像AU 0.662  F1max 0.189',
    '記憶バンク(10 %)                        AUROC 0.895  AUPRO 0.734  画像AU 0.712  F1max 0.313',
    '位置つき記憶バンク(10 %)                    AUROC 0.901  AUPRO 0.716  画像AU 0.776  F1max 0.291',
    'プリミティブ + 記憶バンク(10 %)               AUROC 0.896  AUPRO 0.666  画像AU 0.739  F1max 0.279',
]}

ok_all = []
DAGM_DOWN = 2                                                    # 欠陥は「テクスチャが消えた滑らかな斑」なので、細かい模様が残る 1/2 縮小


def check(name, cond, detail=""):
    ok_all.append(bool(cond))
    print("   [%s] %s%s" % ("OK" if cond else "NG", name, (" —— " + detail) if detail else ""))
    return bool(cond)


# --------------------------------------------------------------------------- #
# 合成の世界(真の欠陥マスクつき)                                                  #
# --------------------------------------------------------------------------- #
def w_stoch(rng):
    """確率場: 1 枚ごとに模様が違う(位置の決まらない、滑らかなテクスチャ)。"""
    return ndi.gaussian_filter(rng.standard_normal((S, S)), 2.0) * 4.0 + 0.5 + 0.02 * rng.standard_normal((S, S))


def w_weave(rng):
    """織り: 周期 6 px の格子で、位相が 1 枚ごとにランダム(位置合わせしても模様が揃わない)。"""
    yy, xx = np.mgrid[0:S, 0:S].astype(float)
    ph = rng.uniform(0, 2 * np.pi, 2)
    return (0.5 + 0.2 * np.sin(2 * np.pi * xx / 6 + ph[0]) * np.sin(2 * np.pi * yy / 6 + ph[1])
            + 0.03 * rng.standard_normal((S, S)))


def w_bar(rng, col=20):
    """縦の棒が 1 本(位置の決まった部品。棒が動くと論理的な異常)。"""
    yy, xx = np.mgrid[0:S, 0:S].astype(float)
    return ndi.gaussian_filter(0.5 + 0.3 * (np.abs(xx - col) < 3), 1.0) + 0.01 * rng.standard_normal((S, S))


def w_part(rng, bar=20):
    """位置の決まった部品: 縦の棒と横の棒。"""
    yy, xx = np.mgrid[0:S, 0:S].astype(float)
    base = 0.5 + 0.25 * (np.abs(xx - bar) < 3) + 0.25 * (np.abs(yy - 44) < 4) * (xx > 30)
    return ndi.gaussian_filter(base, 1.0) + 0.03 * rng.standard_normal((S, S))


#: 世界ごとの欠陥の強さ(植える量。小さいほど難しい)
WORLDS = {"stoch": (w_stoch, 1.0), "weave": (w_weave, 0.10), "part": (w_part, 0.09)}


def plant(img, rng, kind, amp):
    """点(硬い縁の円)か細い傷を 1 つ植えて、真のマスクを返す。"""
    m = np.zeros(img.shape, bool)
    r, c = rng.integers(14, S - 14, 2)
    if kind == "spot":
        yy, xx = np.mgrid[0:S, 0:S]
        m = (yy - r) ** 2 + (xx - c) ** 2 <= 9
        return img + amp * ndi.gaussian_filter(m.astype(float), 0.5), m
    ang = rng.uniform(0, np.pi)
    t = np.arange(-10, 11)
    m[np.clip(np.round(r + t * np.sin(ang)).astype(int), 0, S - 1),
      np.clip(np.round(c + t * np.cos(ang)).astype(int), 0, S - 1)] = True
    m = ndi.binary_dilation(m, iterations=1)
    return img - amp * ndi.gaussian_filter(m.astype(float), 0.5), m


def make_world(name, n_train, n_test, seed):
    """良品 n_train 枚と試験 n_test 枚(半分が不良: 点と細い傷が交互)。"""
    gen, amp = WORLDS[name]
    rng = np.random.default_rng([2026, 10, 19, seed, len(name)])
    train = np.stack([gen(rng) for _ in range(n_train)])
    te, ms, lab = [], [], []
    for i in range(n_test):
        im = gen(rng)
        m = np.zeros(im.shape, bool)
        if i % 2:
            im, m = plant(im, rng, "spot" if (i // 2) % 2 else "scratch", amp)
        te.append(im)
        ms.append(m)
        lab.append(bool(i % 2))
    return train, np.stack(te), np.stack(ms), np.array(lab)


# --------------------------------------------------------------------------- #
# 変種と採点台                                                                   #
# --------------------------------------------------------------------------- #
def _L():
    return fs.ledger


def variants(**kw):
    """(名前, 方式, 当てはめ)の一覧。方式 "dist" = 位置ごと/まとめた正規分布、"bank" = 記憶バンク。kw は全変種に渡す特徴の設定。"""
    return [
        ("プリミティブ(勾配のみ・1 解像度)", "dist",
         lambda s: _L().patchdist_fit(s, groups=("gradient",), scales=(1.0,), **kw)),
        ("多重解像度(勾配・Gabor・LBP)", "dist", lambda s: _L().patchdist_fit(s, **kw)),
        ("多重解像度 + 周波数帯", "dist",
         lambda s: _L().patchdist_fit(s, groups=("gradient", "gabor", "lbp", "fourier"), **kw)),
        ("全位置まとめた正規分布", "dist", lambda s: _L().patchdist_fit(s, pool="global", **kw)),
        ("記憶バンク(全部)", "bank", lambda s: _L().patchbank_fit(s, coreset=1.0, proj_dim=None, **kw)),
        ("記憶バンク(10 %)", "bank", lambda s: _L().patchbank_fit(s, coreset=0.1, **kw)),
        ("位置つき記憶バンク(10 %)", "bank",
         lambda s: _L().patchbank_fit(s, coreset=0.1, position_weight=4.0, **kw)),
        ("プリミティブ + 記憶バンク(10 %)", "bank",
         lambda s: _L().patchbank_fit(s, groups=("gradient",), scales=(1.0,), coreset=0.1, **kw)),
    ]


VARIANTS = variants()


def score_maps(kind, model, tests, smooth=4.0):
    fn = _L().patchdist_score if kind == "dist" else _L().patchbank_score
    return np.stack([fn(x, model, smooth=smooth)["map"] for x in tests])


def varmodel_maps(train, tests):
    """既存の変動モデル(位置を合わせた良品の画素ごとの帯)。拒否されたら None。"""
    try:
        m = _L().varmodel_fit(train, spread="moderated", far=1e-3)
    except ValueError as exc:
        return None, str(exc)[:90]
    return np.stack([np.abs(_L().varmodel_score(x, m)["z"]) for x in tests]), ""


def metrics(maps, masks, labels):
    return {"auroc": _L().anomaly_pixel_auroc(maps, masks)["auroc"],
            "aupro": _L().anomaly_pro(maps, masks, fpr_max=0.3)["aupro"],
            "image_auroc": _L().anomaly_image_auroc(maps.reshape(len(maps), -1).max(axis=1), labels)["auroc"],
            "f1": _L().anomaly_pixel_f1_max(maps, masks)["f1"]}


def fmt(v):
    return "AUROC %.3f  AUPRO %.3f  画像AU %.3f  F1max %.3f" % (v["auroc"], v["aupro"], v["image_auroc"], v["f1"])


# --------------------------------------------------------------------------- #
# 1. 特徴の閉形式                                                                #
# --------------------------------------------------------------------------- #
def stage1_features():
    print("\n1) 特徴の閉形式(傾き a = 0.02 の斜面の勾配チャネル)")
    a = 0.02
    xx = np.arange(S, dtype=float)[None, :] * np.ones((S, 1))
    r = _L().patch_features(a * xx, scales=(2.0,), groups=("gradient",))
    mid = r["features"][4:11, 4:11, 0]
    err = float(np.abs(mid / a - 1.0).max())
    print("   勾配の大きさ %.6f(閉形式 %.6f)、相対誤差 %.1e、特徴 %d 次元 × 格子 %s"
          % (float(mid.mean()), a, err, r["dim"], r["grid"]))
    check("斜面の勾配の大きさが a に一致(ガウス核の打ち切りの 1e-3 以内)", err < 1e-3)
    d = _L().patch_features(a * xx)["dim"]
    check("既定の特徴は 51 次元(3 解像度 x(勾配 3 + Gabor 4 + LBP 10))", d == 51, str(d))


# --------------------------------------------------------------------------- #
# 2. 合成の 3 つの世界で 8 変種                                                   #
# --------------------------------------------------------------------------- #
def stage2_worlds():
    print("\n2) 合成の 3 つの世界(良品 20 枚、試験 %d 枚の半分に点と細い傷)で 8 変種 + 変動モデル + 無作為" % (24 if REDUCED else 40))
    n_te = 24 if REDUCED else 40
    res, keep = {}, {}
    for wname in WORLDS:
        train, tests, ms, labs = make_world(wname, 20, n_te, 1)
        print("   --- %s(欠陥の領域 %d 個)" % (wname, _L().anomaly_region_overlap(ms, ms)["n_regions"]))
        rng = np.random.default_rng(7)
        rnd = [metrics(rng.random(ms.shape), ms, labs)["auroc"] for _ in range(3)]
        res[(wname, "無作為")] = {"auroc": float(np.mean(rnd))}
        print("   %-34s 画素 AUROC %.3f(3 回の平均、0.5 のまわり)" % ("無作為", float(np.mean(rnd))))
        vm, why = varmodel_maps(train, tests)
        if vm is None:
            print("   %-34s 拒否: %s" % ("変動モデル(既存)", why))
            res[(wname, "変動モデル")] = None
        else:
            res[(wname, "変動モデル")] = metrics(vm, ms, labs)
            print("   %-34s %s" % ("変動モデル(既存)", fmt(res[(wname, "変動モデル")])))
        for name, kind, fit in VARIANTS:
            model = fit(train)
            maps = score_maps(kind, model, tests)
            res[(wname, name)] = metrics(maps, ms, labs)
            if wname == "stoch":
                keep[name] = maps
            print("   %-34s %s" % (name, fmt(res[(wname, name)])))
        keep[(wname, "data")] = (train, tests, ms, labs)
    st = {n: res[("stoch", n)]["aupro"] for n, _, _ in VARIANTS}
    gap = max(abs(res[(w, "無作為")]["auroc"] - 0.5) for w in WORLDS)
    check("良品だけで学んだ検出器は無作為より桁で良い(確率場: 最良の AUROC - 0.5 が無作為のずれの 10 倍超)",
          max(res[("stoch", n)]["auroc"] for n, _, _ in VARIANTS) - 0.5 > 10 * gap,
          "%.3f vs %.4f" % (max(res[("stoch", n)]["auroc"] for n, _, _ in VARIANTS) - 0.5, gap))
    check("確率場: 位置ごとの正規分布(AUPRO %.3f)は、全位置まとめた分布・記憶バンクのどちらにも負ける" % st["多重解像度(勾配・Gabor・LBP)"],
          st["多重解像度(勾配・Gabor・LBP)"] + 0.05 < min(st["全位置まとめた正規分布"], st["記憶バンク(10 %)"]))
    check("確率場: 変動モデル(位置ごとの画素の帯)は、記憶バンクに画素 AUROC で負ける",
          res[("stoch", "変動モデル")] is None or res[("stoch", "変動モデル")]["auroc"] < res[("stoch", "記憶バンク(10 %)")]["auroc"],
          "%s" % ("拒否" if res[("stoch", "変動モデル")] is None else "%.3f" % res[("stoch", "変動モデル")]["auroc"]))
    # 図: 異常地図の重ね描き(確率場の欠陥を含む 3 枚)
    train, tests, ms, labs = keep[("stoch", "data")]
    pick = [int(np.nonzero(labs)[0][j]) for j in (0, 1, 2)]
    panels, caps = [], []
    shown = ("多重解像度(勾配・Gabor・LBP)", "全位置まとめた正規分布", "記憶バンク(10 %)")
    rng_of = {n: (float(np.percentile(keep[n][pick], 1)), float(np.percentile(keep[n][pick], 99.8))) for n in shown}
    for i in pick:
        base = (tests[i] - tests[i].min()) / (np.ptp(tests[i]) + 1e-9)
        edge = ms[i] & ~ndi.binary_erosion(ms[i])
        rgb = np.repeat(base[..., None], 3, axis=2)
        rgb[edge] = (1.0, 0.85, 0.0)
        panels.append(rgb)
        caps.append("試験(黄=欠陥)")
        for name in shown:
            panels.append(keep[name][i])
            caps.append({"多重解像度(勾配・Gabor・LBP)": "位置ごとの分布", "全位置まとめた正規分布": "まとめた分布",
                         "記憶バンク(10 %)": "記憶バンク"}[name])
    figs.save_grid("anomaly_maps", panels, captions=caps, ncols=4,
                   signed=False, vrange=[None, rng_of[shown[0]], rng_of[shown[1]], rng_of[shown[2]]] * 3,
                   title="確率場の欠陥 3 つ: 位置ごとの分布・まとめた分布・記憶バンクの異常地図",
                   caption="確率場(1 枚ごとに模様が違う)の試験 3 枚。左端: 試験画像と真の欠陥の輪郭(黄)。右へ、位置ごとの正規分布・"
                           "全位置まとめた正規分布・記憶バンク(10 %)の異常地図。色の幅は方法ごとに、3 枚で共通(1〜99.8 パーセンタイル)。"
                           "位置ごとの分布は良品 20 枚では標本が足りず、欠陥でない所の自然な模様の変動も同じくらい明るくなる。")
    # 図: PRO 曲線(変種ごと)
    series = []
    for name in ("プリミティブ(勾配のみ・1 解像度)", "多重解像度(勾配・Gabor・LBP)", "全位置まとめた正規分布",
                 "記憶バンク(10 %)", "位置つき記憶バンク(10 %)"):
        c = _L().anomaly_pro(keep[name], ms, fpr_max=0.3)
        series.append((name, list(c["fpr"]), list(c["pro"])))
    figs.save_plot("pro_curves", series, xlabel="偽陽性率(良品の画素)", ylabel="PRO(欠陥の領域ごとの重なり)",
                   title="確率場の PRO 曲線(FPR ≤ 0.3): 変種ごと", size=(760, 400),
                   colors=["neutral", "wrong", "right", "emphasis", "reference"],
                   caption="確率場・良品 20 枚の PRO 曲線。曲線の下の面積(0.3 で割る)が AUPRO。位置ごとの正規分布(赤)は"
                           "偽陽性が増えても欠陥の領域をなかなか覆えず、記憶バンクとまとめた分布は早く立ち上がる。")
    return res, keep


# --------------------------------------------------------------------------- #
# 3. 良品の枚数                                                                  #
# --------------------------------------------------------------------------- #
def stage3_counts():
    ns = (5, 20) if REDUCED else (5, 20, 80)
    print("\n3) 良品の枚数 %s(確率場、試験 %d 枚)" % (ns, 20 if REDUCED else 30))
    out = {}
    for n in ns:
        train, tests, ms, labs = make_world("stoch", n, 20 if REDUCED else 30, 3)
        for name, kind, fit in VARIANTS:
            out[(n, name)] = metrics(score_maps(kind, fit(train), tests), ms, labs)
        row = "  ".join("%s %.3f" % (nm.split("(")[0][:8], out[(n, nm)]["aupro"]) for nm, _, _ in VARIANTS)
        print("   n=%-3d AUPRO: %s" % (n, row), flush=True)
    for n in ns:
        a = out[(n, "多重解像度(勾配・Gabor・LBP)")]["aupro"]
        b = out[(n, "全位置まとめた正規分布")]["aupro"]
        c = out[(n, "記憶バンク(10 %)")]["aupro"]
        check("n=%d: 位置ごとの正規分布(%.3f)は、まとめた分布(%.3f)にも記憶バンク(%.3f)にも負ける" % (n, a, b, c),
              a + 0.05 < min(b, c))
    shown = ("プリミティブ(勾配のみ・1 解像度)", "多重解像度(勾配・Gabor・LBP)", "全位置まとめた正規分布",
             "記憶バンク(10 %)", "位置つき記憶バンク(10 %)")
    series = [(nm, list(ns), [out[(n, nm)]["aupro"] for n in ns]) for nm in shown]
    figs.save_plot("sample_count_curve", series, xlabel="良品の枚数 n", ylabel="AUPRO(FPR ≤ 0.3)",
                   title="確率場: 良品の枚数と AUPRO(変種ごと)", size=(760, 420), xlim=(0, max(ns) * 1.05),
                   colors=["neutral", "wrong", "right", "emphasis", "reference"],
                   caption="確率場の試験画像での AUPRO。良品 %s 枚のどれでも、位置ごとの正規分布(赤)は"
                           "全位置まとめた分布・記憶バンクより下にある。順位は枚数で入れ替わらない。" % ("・".join(map(str, ns))))
    return out


# --------------------------------------------------------------------------- #
# 4. 論理的な異常                                                                #
# --------------------------------------------------------------------------- #
def stage4_logical():
    print("\n4) 論理的な異常: 正しい模様が違う場所にある(縦の棒が 24 px 動いた。特徴 = 勾配 + 強度、2 解像度、位置の重み 4)")
    rng = np.random.default_rng(41)
    train = np.stack([w_bar(rng) for _ in range(8)])
    goods = [w_bar(rng) for _ in range(8)]
    moved = [w_bar(rng, col=44) for _ in range(8)]
    out = {}
    for tag, pw in (("位置を見ない", 0.0), ("位置を見る", 4.0)):
        m = _L().patchbank_fit(train, coreset=1.0, position_weight=pw, groups=("gradient", "intensity"),
                               scales=(1.0, 2.0))
        g = [_L().patchbank_score(x, m)["image_score"] for x in goods]
        b = [_L().patchbank_score(x, m)["image_score"] for x in moved]
        out[tag] = (float(np.median(g)), float(np.median(b)),
                    _L().anomaly_image_auroc(np.r_[g, b], np.r_[np.zeros(8), np.ones(8)].astype(bool))["auroc"],
                    _L().patchbank_score(moved[0], m)["map"])
        print("   %-8s 良品の中央値 %.2f  棒が動いた画像の中央値 %.2f(比 %.1f 倍)  画像 AUROC %.3f"
              % (tag, out[tag][0], out[tag][1], out[tag][1] / out[tag][0], out[tag][2]))
    check("位置を見ない記憶は、動いた棒をほとんど指さない(動いた画像の中央値 < 良品の 2 倍)",
          out["位置を見ない"][1] < 2.0 * out["位置を見ない"][0])
    check("位置を見る記憶は、動いた棒を指す(動いた画像の中央値 > 良品の 3 倍)",
          out["位置を見る"][1] > 3.0 * out["位置を見る"][0])
    figs.save_grid("logical_anomaly", [moved[0], out["位置を見ない"][3], out["位置を見る"][3]],
                   captions=["棒が動いた画像", "位置を見ない", "位置を見る"], ncols=3,
                   signed=False, vrange=[None, (0, 6), (0, 6)],
                   title="論理的な異常: 縦の棒が 24 px 右に動いた",
                   caption="良品では縦の棒は左(x = 20)にある。試験画像では右(x = 44)にある。棒の欠片そのものは記憶に在るので、"
                           "位置を見ない記憶バンクの異常地図(中)はほぼ平ら。位置を足した記憶バンク(右)は、あるべき場所から棒が消えた"
                           "所と、無いはずの場所に棒が現れた所を指す。")
    return out


# --------------------------------------------------------------------------- #
# 5. 記憶の間引き                                                                #
# --------------------------------------------------------------------------- #
def stage5_coreset():
    print("\n5) 記憶の間引き(確率場、良品 %d 枚、記憶 2〜100 %%)" % (20 if REDUCED else 40))
    train, tests, ms, labs = make_world("stoch", 20 if REDUCED else 40, 20 if REDUCED else 30, 5)
    rows = []
    for frac in (0.02, 0.05, 0.1, 0.25, 1.0):
        m = _L().patchbank_fit(train, coreset=frac, proj_dim=None if frac == 1.0 else 32)
        t0, w0 = time.process_time(), time.perf_counter()
        maps = score_maps("bank", m, tests)
        cpu, wall = time.process_time() - t0, time.perf_counter() - w0
        v = metrics(maps, ms, labs)
        rows.append((frac, m["n_memory"], m["covering_radius"], v["aupro"], v["auroc"], cpu, wall))
        print("   記憶 %5.0f %%  %6d 個  被覆半径 %6.3f  AUPRO %.3f  AUROC %.3f  採点 CPU %.2f 秒(壁時計 %.2f 秒)"
              % (100 * frac, m["n_memory"], m["covering_radius"], v["aupro"], v["auroc"], cpu, wall))
    r = [x[2] for x in rows]
    check("被覆半径は記憶が増えるほど単調に縮み、100 % で 0", r[0] > r[1] > r[2] > r[3] > r[4] == 0.0,
          " > ".join("%.2f" % x for x in r))
    check("採点の CPU 時間は記憶 10 % で、全部の半分以下(記憶の数にほぼ比例)", rows[2][5] < 0.5 * rows[4][5],
          "%.2f 秒 対 %.2f 秒" % (rows[2][5], rows[4][5]))
    check("10 % に間引いても AUPRO は全部の記憶から 0.1 以上は落ちない", rows[2][3] > rows[4][3] - 0.1,
          "%.3f 対 %.3f" % (rows[2][3], rows[4][3]))
    return rows


# --------------------------------------------------------------------------- #
# 6. 縮小推定の宣言                                                              #
# --------------------------------------------------------------------------- #
def stage6_shrinkage():
    print("\n6) 特異な共分散: 良品 5 枚で特徴 51 次元(位置ごとの共分散は階数 4)")
    train = make_world("stoch", 5, 2, 6)[0]
    try:
        _L().patchdist_fit(train, shrinkage="none")
        refused = False
    except ValueError as exc:
        refused = True
        print("   shrinkage='none' の拒否: " + str(exc)[:150])
    check("宣言なし(none)は拒否される", refused)
    lam = {}
    for n in (5, 10, 20, 40, 80):
        m = _L().patchdist_fit(make_world("stoch", n, 2, 6)[0], shrinkage="auto")
        lam[n] = m["shrinkage_mean"]
    print("   auto の縮小の強さ(位置の平均): " + "  ".join("n=%d: %.3f" % (n, v) for n, v in lam.items()))
    vals = list(lam.values())
    check("auto は良品が増えるほど縮小を弱める(5 > 20 > 80 枚)", lam[5] > lam[20] > lam[80], " > ".join("%.3f" % x for x in vals))
    return lam


# --------------------------------------------------------------------------- #
# 7. 再現率を保証する運用点                                                       #
# --------------------------------------------------------------------------- #
def stage7_operating_point():
    n_def, n_nor, trials = (150, 100, 150) if REDUCED else (400, 250, 300)
    recall, conf, ncal = 0.8, 0.9, 30
    print("\n7) 再現率を保証する運用点(確率場・記憶バンク 10 %%): 欠陥 %d・良品 %d 枚のプールから、較正 %d+%d 枚を %d 回引く"
          % (n_def, n_nor, ncal, ncal, trials))
    train = make_world("stoch", 20, 2, 7)[0]
    m = _L().patchbank_fit(train, coreset=0.1)
    gen, amp = WORLDS["stoch"][0], 2.0                             # 運用点の章は、欠陥の見えやすい確率場(強さ 2.0)
    rng = np.random.default_rng([2026, 10, 19, 77])
    sc_d, sc_n = [], []
    for i in range(n_def):
        im, _ = plant(gen(rng), rng, "spot" if i % 2 else "scratch", amp)
        sc_d.append(_L().patchbank_score(im, m)["image_score"])
    for _ in range(n_nor):
        sc_n.append(_L().patchbank_score(gen(rng), m)["image_score"])
    sc_d, sc_n = np.array(sc_d), np.array(sc_n)
    print("   プールの画像 AUROC %.3f(欠陥の再現率は閾値で決まる)"
          % _L().anomaly_image_auroc(np.r_[sc_d, sc_n], np.r_[np.ones(n_def), np.zeros(n_nor)].astype(bool))["auroc"])
    ok_g, ok_n, fpr_g, fpr_n, rec_g, rec_n = [], [], [], [], [], []
    for t in range(trials):
        r2 = np.random.default_rng([2026, 10, 19, 78, t])
        idd = r2.permutation(n_def)
        idn = r2.permutation(n_nor)
        cd, rd = sc_d[idd[:ncal]], sc_d[idd[ncal:]]
        cn, rn = sc_n[idn[:ncal]], sc_n[idn[ncal:]]
        op = _L().anomaly_operating_point(np.r_[cd, cn], np.r_[np.ones(ncal), np.zeros(ncal)].astype(bool),
                                          recall=recall, confidence=conf)
        thr_g = op["threshold"]
        thr_n = float(np.quantile(cd, 1.0 - recall, method="lower"))   # 保証なし: 較正の欠陥の 80 % が超える点
        for thr, ok, fp, rc in ((thr_g, ok_g, fpr_g, rec_g), (thr_n, ok_n, fpr_n, rec_n)):
            true_rec = float((rd >= thr).mean())
            rc.append(true_rec)
            ok.append(true_rec >= recall)
            fp.append(float((rn >= thr).mean()))
    cov_g, cov_n = float(np.mean(ok_g)), float(np.mean(ok_n))
    se = math.sqrt(conf * (1 - conf) / trials)
    print("   保証つき: 真の再現率 >= %.1f になった割合 %.3f(宣言 %.1f)  平均の再現率 %.3f  平均の誤検出 %.3f"
          % (recall, cov_g, conf, float(np.mean(rec_g)), float(np.mean(fpr_g))))
    print("   保証なし(較正の欠陥の %.0f %% 点): 同じ割合 %.3f  平均の再現率 %.3f  平均の誤検出 %.3f"
          % (100 * recall, cov_n, float(np.mean(rec_n)), float(np.mean(fpr_n))))
    check("保証つきの運用点は、宣言した信頼水準を(二項の 4σ を許して)守る", cov_g > conf - 4 * se, "%.3f > %.3f" % (cov_g, conf - 4 * se))
    check("保証なしの分位点は、守れない(同じ割合が信頼水準の 4σ 下を割る)", cov_n < conf - 4 * se, "%.3f < %.3f" % (cov_n, conf - 4 * se))
    check("保証の代償は誤検出(保証つきの平均の誤検出 > 保証なし)", float(np.mean(fpr_g)) > float(np.mean(fpr_n)),
          "%.3f > %.3f" % (float(np.mean(fpr_g)), float(np.mean(fpr_n))))
    try:
        _L().anomaly_operating_point(np.r_[sc_d[:10], sc_n[:10]], np.r_[np.ones(10), np.zeros(10)].astype(bool),
                                     recall=0.95, confidence=0.95)
        refused = False
    except ValueError as exc:
        refused = True
        print("   欠陥 10 枚で 0.95 / 0.95 を求めると拒否: " + str(exc)[:120])
    check("欠陥が少なすぎて保証できないときは閾値を返さず拒否する", refused)
    order = np.argsort(rec_g)
    figs.save_plot("recall_guarantee",
                   [("保証つき(信頼 %.1f)" % conf, list(range(trials)), list(np.array(rec_g)[order])),
                    ("保証なし(較正の %.0f %% 点)" % (100 * recall), list(range(trials)), list(np.sort(rec_n))),
                    ("目標 %.1f" % recall, [0, trials - 1], [recall, recall])],
                   xlabel="繰り返し(真の再現率の小さい順)", ylabel="残りの欠陥での真の再現率",
                   title="再現率 %.1f の運用点: 保証つきと保証なし(%d 回)" % (recall, trials), size=(760, 400),
                   kinds=["line", "line", "line"], styles=[None, None, "dashed"], colors=["right", "wrong", "reference"],
                   caption="欠陥 %d 枚のプールから較正に欠陥 %d 枚を引いて閾値を決め、残りの欠陥で真の再現率を測った %d 回を小さい順に並べた。"
                           "保証なし(較正の欠陥の %.0f %% が超える点)は約半数が目標を割る。保証つき(Clopper–Pearson の下限)は"
                           "目標を割った回が %.1f %% で、宣言した信頼水準 %.1f を守る。" % (
                               n_def, ncal, trials, 100 * recall, 100 * (1 - cov_g), conf))
    return cov_g, cov_n


# --------------------------------------------------------------------------- #
# 8. 公開実データ                                                                #
# --------------------------------------------------------------------------- #
def _gray_down(path, down, mask=False):
    from PIL import Image                                         # noqa: PLC0415
    im = np.asarray(Image.open(path).convert("L"), dtype=np.float64)
    im = (im > 0).astype(np.float64) if mask else im / 255.0
    h, w = im.shape
    h -= h % down
    w -= w % down
    r = im[:h, :w].reshape(h // down, down, w // down, down).mean(axis=(1, 3))
    return r >= 0.25 if mask else r


def _real_row(name, kind, model, tests, ms, labs, smooth=4.0):
    t0 = time.process_time()
    maps = score_maps(kind, model, tests, smooth=smooth)
    cpu = time.process_time() - t0
    v = metrics(maps, ms, labs)
    print("   %-34s %s  採点 CPU %.1f 秒" % (name, fmt(v), cpu), flush=True)
    return maps, v, cpu


def stage8_real():
    print("\n8) 公開実データ(CC BY 4.0)")
    lines = []
    out = {}
    root = os.path.join(DAGM, "Class1") if DAGM else ""
    if root and os.path.isfile(os.path.join(root, "Train", "Label", "Labels.txt")):
        def rows(split):
            with open(os.path.join(root, split, "Label", "Labels.txt"), encoding="utf-8") as fh:
                return [ln.split("\t") for ln in fh.read().splitlines()[1:] if ln.strip()]
        good = [r[2] for r in rows("Train") if r[1] == "0"][:(30 if REDUCED else 40)]
        train = np.stack([_gray_down(os.path.join(root, "Train", p), DAGM_DOWN) for p in good])
        te_rows = rows("Test")
        bad = [r for r in te_rows if r[1] == "1"][:50]
        nor = [r for r in te_rows if r[1] == "0"][:len(bad)]
        sel = bad + nor
        tests = np.stack([_gray_down(os.path.join(root, "Test", r[2]), DAGM_DOWN) for r in sel])
        ms = np.stack([_gray_down(os.path.join(root, "Test", "Label", r[4].strip()), DAGM_DOWN, True) if r[1] == "1"
                       else np.zeros(train.shape[1:], bool) for r in sel])
        labs = np.array([r[1] == "1" for r in sel])
        print("   DAGM 2007 Class1(確率的なテクスチャ、%s px): 良品 %d 枚で学び、試験 %d 枚(不良 %d・良品 %d、楕円の弱い注釈)"
              % (train.shape[1:], len(train), len(tests), labs.sum(), (~labs).sum()))
        res = {}
        vm, why = varmodel_maps(train, tests)
        if vm is not None:
            res["変動モデル(既存)"] = metrics(vm, ms, labs)
            print("   %-34s %s" % ("変動モデル(既存)", fmt(res["変動モデル(既存)"])))
        keepmaps = {}
        for name, kind, fit in variants(patch=16, stride=8):
            if name in ("多重解像度 + 周波数帯", "記憶バンク(全部)"):
                continue
            maps, v, _ = _real_row(name, kind, fit(train), tests, ms, labs, smooth=8.0)
            res[name] = v
            keepmaps[name] = maps
        out["dagm"] = res
        lines += ["DAGM 2007 Class1: " + ", ".join("%s AUROC %.3f AUPRO %.3f" % (k, v["auroc"], v["aupro"]) for k, v in res.items())]
        best = max((k for k in keepmaps), key=lambda k: res[k]["aupro"])
        show = [int(np.nonzero(labs)[0][j]) for j in (0, 5, 10)]
        panels, caps = [], []
        shown = ("プリミティブ + 記憶バンク(10 %)", "記憶バンク(10 %)")
        rng_of = {n: (float(np.percentile(keepmaps[n][show], 1)), float(np.percentile(keepmaps[n][show], 99.8)))
                  for n in shown}
        for i in show:
            base = (tests[i] - tests[i].min()) / (np.ptp(tests[i]) + 1e-9)
            edge = ms[i] & ~ndi.binary_erosion(ms[i])
            rgb = np.repeat(base[..., None], 3, axis=2)
            rgb[edge] = (1.0, 0.85, 0.0)
            panels += [rgb, keepmaps["プリミティブ + 記憶バンク(10 %)"][i], keepmaps["記憶バンク(10 %)"][i]]
            caps += ["試験(黄=注釈)", "勾配のみの記憶", "多重解像度の記憶"]
        figs.save_grid("dagm_maps", panels, captions=caps, ncols=3, signed=False,
                       vrange=[None, rng_of[shown[0]], rng_of[shown[1]]] * 3,
                       title="DAGM 2007 Class1 の不良 3 枚: 異常地図",
                       caption="DAGM 2007 Class1(CC BY 4.0、2×2 の平均で縮小)。黄の輪郭は楕円の弱い注釈。欠陥は「細かい模様が消えた"
                               "滑らかな斑」。勾配だけの記憶バンクと多重解像度の記憶バンクの異常地図(色の幅は方法ごとに、3 枚で共通)。"
                               "欠陥の場所は周りよりわずかに明るい程度で、縁や角にも同じくらいの山があり、図の上では欠陥を指し切れていない"
                               "(勾配だけの記憶バンクは画素 AUROC 0.768・AUPRO 0.474、画像ごとの AUROC は 0.53)。")
        check("DAGM: 古典特徴の最良は、画素ごとの帯の変動モデルより画素 AUROC が高い",
              "変動モデル(既存)" not in res or max(res[k]["auroc"] for k in keepmaps) > res["変動モデル(既存)"]["auroc"] + 0.05,
              "%.3f vs %s" % (max(res[k]["auroc"] for k in keepmaps),
                              ("%.3f" % res["変動モデル(既存)"]["auroc"]) if "変動モデル(既存)" in res else "拒否"))
    else:
        print("   FULLSEYE_DAGM_DATA が無いので DAGM の章は走らせない。")
    if VISA and os.path.isfile(os.path.join(VISA, "split_csv", "1cls.csv")):
        rows_ = list(csv.DictReader(open(os.path.join(VISA, "split_csv", "1cls.csv"), encoding="utf-8")))
        for obj, down in (("pcb1", 6), ("candle", 6)):
            tr = sorted(r["image"] for r in rows_ if r["object"] == obj and r["split"] == "train")[:(10 if REDUCED else 20)]
            te = sorted((r for r in rows_ if r["object"] == obj and r["split"] == "test"), key=lambda r: r["image"])
            train = np.stack([_gray_down(os.path.join(VISA, p), down) for p in tr])
            tests = np.stack([_gray_down(os.path.join(VISA, r["image"]), down) for r in te])
            ms = np.stack([_gray_down(os.path.join(VISA, r["mask"]), down, True) if r["mask"]
                           else np.zeros(train.shape[1:], bool) for r in te])
            labs = np.array([r["label"] == "anomaly" for r in te])
            print("   VisA %s(1/%d、%s px): 良品 %d 枚で学び、試験 %d 枚(不良 %d・良品 %d)"
                  % (obj, down, train.shape[1:], len(train), len(tests), labs.sum(), (~labs).sum()))
            res = {}
            for name, kind, fit in VARIANTS:
                if name in ("プリミティブ(勾配のみ・1 解像度)", "多重解像度 + 周波数帯", "記憶バンク(全部)"):
                    continue
                maps, v, _ = _real_row(name, kind, fit(train), tests, ms, labs)
                res[name] = v
            out[obj] = res
            lines += ["VisA %s: " % obj + ", ".join("%s AUROC %.3f AUPRO %.3f" % (k, v["auroc"], v["aupro"]) for k, v in res.items())]
    else:
        print("   FULLSEYE_VISA_DATA が無いので VisA の章は走らせない。")
    if not out:
        if RECORDED["lines"]:
            print("   記録値(2026-10-19):")
            for ln in RECORDED["lines"]:
                print("     " + ln)
        return None
    return out, lines


# --------------------------------------------------------------------------- #
def main():
    t0 = time.perf_counter()
    c0 = time.process_time()
    print("良品だけから学ぶパッチ特徴の異常検知: 古典特徴で『分布』と『記憶』を比べる")
    print("=" * 68)
    stage1_features()
    res, keep = stage2_worlds()
    stage3_counts()
    stage4_logical()
    stage5_coreset()
    stage6_shrinkage()
    cov = stage7_operating_point()
    real = stage8_real()
    print("\n9) まとめ")
    print("   確率場(AUPRO、良品 20 枚): 位置ごとの正規分布 %.3f / まとめた正規分布 %.3f / 記憶バンク(10 %%) %.3f / 位置つき記憶 %.3f。"
          % (res[("stoch", "多重解像度(勾配・Gabor・LBP)")]["aupro"], res[("stoch", "全位置まとめた正規分布")]["aupro"],
             res[("stoch", "記憶バンク(10 %)")]["aupro"], res[("stoch", "位置つき記憶バンク(10 %)")]["aupro"]))
    print("   運用点: 保証つき %.3f、保証なし %.3f(目標 0.8 を守った割合、宣言 0.9)。" % cov)
    if real is None and not RECORDED["lines"]:
        print("   実データの章は未実行(記録値なし)。")
    if figs.errors():
        print("   図の書き出しで失敗:", "; ".join(figs.errors()))
    print("   所要: CPU %.1f 秒(壁時計 %.1f 秒)" % (time.process_time() - c0, time.perf_counter() - t0))
    if not all(ok_all):
        print("NG が残っている(%d 件)" % ok_all.count(False))
        raise SystemExit(1)
    print("PASS")


if __name__ == "__main__":
    main()
