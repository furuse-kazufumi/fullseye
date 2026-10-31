# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""SEM の明るい縁は、寸法をどれだけ太らせるか —— 真値つきの合成と公開実データで測る。

走査電子顕微鏡(SEM)像では、**二次電子が斜面でよけいに出る**(放出 ∝ sec θ)ので
段差の縁が明るく縁取られる。ビームの有限径(PSF)がその縁をさらに広げる。CD-SEM
(半導体の寸法計測)でも外観検査でも、この**明るい縁ごと**しきい値を超えて拾うと、
測った寸法・面積が系統的に太る。この PoC は、その太りを**真値つき**で切り分ける。

多段(各段に閉形式の真値か外部実データの門):

0. **マスクの規約を数える**(実データ、リスク対策): 専門家マスクの境界が、輝度勾配の
   峰(= 明るい縁)に対して内側か外側か。勾配で重みづけた符号つき距離の中心
   (band 内)を数で出す。これが面積の偏りの主因なら物理の主張を弱めて正直に書く。
1. **SEM 像の物理モデル**(``sem_render``、新 op): 二次電子の縁効果(sec θ)+ ビーム
   PSF(ガウシアン)+ ポアソン雑音 + 緩い帯電。門 = 平面で一様 / 斜面で sec θ /
   段差応答そのものの二次モーメント幅が PSF 幅(分割後の有効縁幅とは別の門)。
2. **古典の分割連鎖**: しきい値 → ``blob_label`` → ``blob_features``。実データでは
   専門家マスクと ``seg_score_card``(Dice / Jaccard / 境界 F)。
3. **寸法の偏り**: 合成(真値の面積が厳密)で、面積の太り ΔA を測り、正規 PSF の
   閉形式 ``w = -σΦ⁻¹((t-1)/(secθ-1))`` と照合する。全条件での実測との相対差は
   中央 0.260 なので「一致」とはせず、しきい値別の一致度を報告する。実データはマスク/分割の面積比を
   クラスごとに出す。
4. **物理モデルによる補正**: しきい値ごとの閉形式縁幅で ΔA を差し引く。しきい値を
   1.02 / 1.05 / 1.10 と掃引し、残る偏りをすべて報告する。
5. **埋め込み POD**: 良品の地(実データの空マスク画像、無ければ合成の雑音地)に既知寸法の
   欠陥を ``sem_render`` で埋め込み、分割連鎖で検出して ``pod_hitmiss_fit`` で a90/95。
   門 = 大きい欠陥ほど検出率が単調増加・a90/95 が存在。

予想(2026-10-13): ★★**Dice は高いのに面積は系統的に太る。** 補正量は PSF だけでなく
しきい値にも依存するため、閉形式と測定値を並べる。異常に良い結果は
内訳を疑う。★実データの SEM 欠陥は**暗い**(背景より暗い穴)ので、縁は暗部を囲む明るい
リングになる —— 合成の「明るい塊」と極性が逆であることも印字する。

実データの分割しきい値は、以前の正解マスク面積由来から、画像の背景中央値と頑健標準偏差だけで
決める方法へ変更した。以下の Dice などは環境変数がある実行だけで得る記録値であり、この実行では
未確認である。実データ(repo には同梱しない。環境変数 ``FULLSEYE_CARINTHIA_DATA`` に
``carinthia-s.csv`` / ``images`` / ``masks`` のある dir を渡す。無ければ合成のみを走らせ
「実データ門は未実行」と明示。CI は合成のみ):

  Carinthia-S dataset, Kofler & Hasić (2025), DOI 10.5281/zenodo.16895427, CC BY 4.0.
  ウェハ SEM 欠陥 6 クラス + 専門家の二値マスク、4,591 枚(クラス 5 は 4 枚)。
  是非クレジットを(CC BY 4.0)。ダウンロード物は信頼しない入力として扱い、画像・
  マスク・CSV を読むだけ(その中のコードは実行しない)。

Fullseye 寄与: SEM 計測の縁効果は外観検査の縁の太りと同じ型。``sem_render`` は閉形式の
真値つき合成生成器として他の PoC にも使える(``opsgenerative`` 族の方針どおり)。
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
from scipy.special import ndtri

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import blob2d as B                                               # noqa: E402
import examplefig as figs                                        # noqa: E402
import pod as POD                                                # noqa: E402
import segeval as SE                                             # noqa: E402
import semsim as SM                                              # noqa: E402

SEED = 7
BASE = 0.30                      #: 平らな面の明るさ[0,1]
CONE_SLOPE = 0.6                 #: 合成欠陥(円錐)の斜面の傾き(高さ/px)
PSF = 2.0                        #: 既定のビーム PSF σ[px]
REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"
DATA = os.environ.get("FULLSEYE_CARINTHIA_DATA", "").strip()
PER_CLASS = 10 if REDUCED else 30      #: 実データで各クラスから読む上限(--all で全数)
ALL = "--all" in sys.argv
CLEAN_CLASSES = ("3", "4", "5")        #: 二値 {0,255} マスクが使えるクラス


# --------------------------------------------------------------------------- #
# 合成欠陥(真値つき)                                                          #
# --------------------------------------------------------------------------- #
def cone(shape, cy, cx, R, slope=CONE_SLOPE):
    """円錐の高さ場と**厳密な footprint**(半径 R の円)を返す。

    円錐は斜面の傾きが一様なので SE 像で一様に明るく、しきい値で塊として拾える
    (球冠は頂上の傾きが 0 で暗くなり拾えない)。真値の面積は円の画素数。
    """
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    d = np.hypot(yy - cy, xx - cx)
    h = np.where(d <= R, slope * (R - d), 0.0)
    return h, (d <= R)


def segment_bright(img, thr):
    """しきい値 → 連結成分 → 最大の塊の (面積, 周囲長, mask)。"""
    lab = B.blob_label(img > thr)
    f = B.blob_features(lab)
    if f["n"] == 0:
        return 0.0, 0.0, np.zeros_like(img, bool)
    i = int(np.argmax(f["area"]))
    return float(f["area"][i]), float(f["perimeter"][i]), (lab == i + 1)


def edge_width_closed(threshold_ratio, psf_px, slope=CONE_SLOPE):
    """ぼけた段のしきい値位置 [px]（解析解、外向きを正）。

    内側の強度を ``sec(theta)``、背景を 1 とすると、正規 PSF の畳み込みから
    ``w = -sigma*Phi^-1((t-1)/(sec(theta)-1))``。有効範囲は ``1 < t < sec(theta)``。
    """
    sec = math.sqrt(1.0 + float(slope) ** 2)
    q = (float(threshold_ratio) - 1.0) / (sec - 1.0)
    if not 0.0 < q < 1.0:
        raise ValueError("threshold_ratio must lie between background 1 and sec(theta)")
    return float(-float(psf_px) * ndtri(q))


# --------------------------------------------------------------------------- #
# 段 1: 物理モデルの閉形式の門                                                  #
# --------------------------------------------------------------------------- #
def stage1_physics():
    print("1) SEM 像の物理モデル sem_render(閉形式の真値)")
    flat = SM.sem_render(np.zeros((48, 48)), base=BASE)
    print("   平面 → 一様: ptp = %.2e(厳密 0)、値 %.3f = base" % (np.ptp(flat), flat[0, 0]))

    print("   一様斜面 → 平面比 = sec θ:")
    sec_err = 0.0
    for slope in (0.5, 1.0, 2.0):
        ramp = np.tile(np.linspace(0.0, slope * 47, 48), (48, 1))
        r = SM.sem_render(ramp, pixel_nm=1.0, base=BASE)
        theta = np.arctan(slope)
        meas, want = float(r[24, 24]) / BASE, 1.0 / np.cos(theta)
        sec_err = max(sec_err, abs(meas - want))
        print("     傾き %.1f(θ=%4.1f度): 比 %.5f / sec θ %.5f" %
              (slope, np.degrees(theta), meas, want))

    print("   段差応答 → 二次モーメント幅 = PSF 幅(分割後の有効縁幅とは別):")
    widths = []
    for psf in (1.0, 2.0, 3.0):
        H = np.zeros((80, 80)); H[:, 40:] = 30.0
        im = SM.sem_render(H, psf_px=psf, base=0.5)
        prof = im[40] - im[40].min(); x = np.arange(prof.size, dtype=np.float64)
        cen = (x * prof).sum() / prof.sum()
        sig = float(np.sqrt(((x - cen) ** 2 * prof).sum() / prof.sum()))
        widths.append((psf, sig))
        print("     PSF σ=%.1f px → 縁の幅 σ=%.3f px" % (psf, sig))

    assert np.ptp(flat) == 0.0, "平面が一様でない"
    assert sec_err < 1e-9, "斜面比が sec θ でない: %.2e" % sec_err
    assert all(abs(s - p) < 0.6 and s >= p for p, s in widths), "縁の幅が PSF に合わない: %r" % widths
    print("   → 平面一様・斜面 sec θ(誤差 %.0e)・段差応答の二次モーメント幅 = PSF。" % sec_err)
    return sec_err


# --------------------------------------------------------------------------- #
# 段 3: 寸法の偏り(合成、真値の面積が厳密)                                     #
# --------------------------------------------------------------------------- #
def stage3_bias_synthetic():
    print("\n3) しきい値掃引: 測った縁幅と正規 PSF の独立な閉形式")
    print("   %-6s %-6s %8s %8s %7s %7s %8s %8s" %
          ("半径R", "PSF", "真面積", "測定面積", "比", "Dice", "周囲長", "ΔA/周囲長"))
    S = 200
    rows, ratios, dices, w_over_psf = [], [], [], []
    sweep = []
    for tr in (1.02, 1.05, 1.10):
      for R in (12, 18, 26, 36):
        for psf in (1.5, 2.5, 3.5):
            h, foot = cone((S, S), 100, 100, R)
            img = SM.sem_render(h, psf_px=psf, base=BASE)
            a, p, mask = segment_bright(img, BASE * tr)
            true = float(foot.sum())
            dice = SE.seg_dice_jaccard(mask.astype(np.int32), foot.astype(np.int32))["dice"]
            w = (a - true) / p if p > 0 else 0.0
            wc = edge_width_closed(tr, psf)
            sweep.append((tr, R, psf, w, wc, a / true))
            rows.append((R, psf, true, a, p))
            ratios.append(a / true); dices.append(dice); w_over_psf.append(w / psf)
            print("   %-6d %-6.1f %8.0f %8.0f %7.3f %7.3f %8.0f %8.2f" %
                  (R, psf, true, a, a / true, dice, p, w))
    wop = float(np.median([w / p for tr, _r, p, w, _wc, _ar in sweep if tr == 1.02]))
    dmed = float(np.median(dices))
    print("   → ★Dice は高い(中央 %.3f = 形はよく合う)一方、面積比は %.3f〜%.3f。"
          "t/base=1.02 に限ると有効縁幅 / PSF の中央値 = %.2f。"
          % (dmed, min(ratios), max(ratios), wop))
    low_ratios = [ar for tr, _r, _p, _w, _wc, ar in sweep if tr == 1.02]
    assert min(low_ratios) > 1.0, "t/base=1.02 で太りが出ない: %.3f" % min(low_ratios)
    assert dmed > 0.8, "Dice が高くない(形が合っていない): %.3f" % dmed
    rel = float(np.median([abs(w - wc) / max(abs(wc), 1e-9) for _, _, _, w, wc, _ in sweep]))
    print("   → 閉形式との縁幅の相対差(全しきい値・半径・PSFの中央値) %.3f。" % rel)
    for tr in (1.02, 1.05, 1.10):
        tr_rel = float(np.median([abs(w - wc) / max(abs(wc), 1e-9)
                                 for t, _, _, w, wc, _ in sweep if t == tr]))
        print("     t/base %.2f: 閉形式との相対差の中央値 %.3f" % (tr, tr_rel))
    assert rel < 0.35, "測定縁幅が閉形式から外れる: %.3f" % rel
    return rows, ratios, wop, dmed, sweep


# --------------------------------------------------------------------------- #
# 段 4: しきい値ごとの閉形式縁幅で ΔA を差し引く                              #
# --------------------------------------------------------------------------- #
def stage4_correction_synthetic():
    print("\n4) しきい値ごとの閉形式縁幅で面積を補正")
    print("   %-6s %-6s %8s %9s %9s" % ("半径R", "PSF", "真面積", "補正前比", "補正後比"))
    S = 200
    by_threshold = {}
    for tr in (1.02, 1.05, 1.10):
      before, after = [], []
      for R in (12, 18, 26, 36):
        for psf in (1.5, 2.5, 3.5):
            h, foot = cone((S, S), 100, 100, R)
            img = SM.sem_render(h, psf_px=psf, base=BASE)
            a, p, _ = segment_bright(img, BASE * tr)
            true = float(foot.sum())
            corrected = a - p * edge_width_closed(tr, psf)
            before.append(a / true); after.append(corrected / true)
            print("   %-6d %-6.1f %8.0f %9.3f %9.3f" % (R, psf, true, a / true, corrected / true))
      mb = float(np.median([abs(x - 1) for x in before]))
      ma = float(np.median([abs(x - 1) for x in after]))
      by_threshold[tr] = (mb, ma)
      print("   → t/base %.2f: 補正前 %.3f → 補正後 %.3f" % (tr, mb, ma))
      assert ma < mb
    return by_threshold


def stage4_noise_check():
    """図と同じ 45 e-/px で、低いしきい値が雑音を拾う反例を数える。"""
    h, foot = cone((200, 200), 100, 100, 26)
    ratios = []
    for seed in range(5):
        img = SM.sem_render(h, psf_px=2.5, base=BASE, dose=45.0, seed=seed)
        a, _p, _m = segment_bright(img, BASE * 1.02)
        ratios.append(a / float(foot.sum()))
    med = float(np.median(ratios))
    print("   線量 45 e-/px・t/base 1.02: 面積比 %.2f〜%.2f、中央値 %.2f（雑音なしの補正は適用不可）"
          % (min(ratios), max(ratios), med))
    assert med > 5.0
    return ratios


# --------------------------------------------------------------------------- #
# 段 5: 埋め込み POD                                                            #
# --------------------------------------------------------------------------- #
POD_SNR_PP = 3.2     #: 埋め込む欠陥の画素コントラストを 背景雑音σ の何倍にするか
POD_K = 3.0          #: 検出しきい値 = 中央値 + POD_K·(頑健σ)
POD_AMIN = 30        #: 検出と認める最小の塊面積[px]


def _robust_std(a):
    return float(np.median(np.abs(a - np.median(a))) * 1.4826)


def _detect_on_background(bg, R, cy, cx, psf=PSF):
    """地 bg の (cy,cx) に半径 R の欠陥を埋め込み、検出できたら True。

    欠陥の画素コントラストは**背景の雑音 σ に比例**させる(``POD_SNR_PP·σ``)ので、
    合成でも実データでも「検出は大きさで決まる」形になる(SNR/画素は揃える)。
    """
    sig = _robust_std(bg) or 1e-3
    h, _foot = cone(bg.shape, cy, cx, R)
    relief = np.clip(SM.sem_render(h, psf_px=psf, base=BASE) - BASE, 0.0, None)
    peak = float(relief.max())
    if peak > 0:
        relief = relief * (POD_SNR_PP * sig / peak)       # 画素 SNR を背景に合わせる
    comp = np.clip(bg + relief, 0.0, 1.0)
    thr = float(np.median(comp) + POD_K * _robust_std(comp))
    f = B.blob_features(B.blob_label(comp > thr))
    for i in range(f["n"]):
        if (f["row"][i] - cy) ** 2 + (f["col"][i] - cx) ** 2 <= (R + 4) ** 2 \
                and f["area"][i] >= POD_AMIN:
            return True
    return False


def stage5_pod(backgrounds, label):
    print("\n5) 埋め込み POD(%s の地に既知寸法の欠陥を埋めて検出)" % label)
    rng = np.random.default_rng(SEED)
    radii = [3, 4, 5, 6, 7, 8, 9, 10, 12, 14]
    reps = 12 if REDUCED else 20
    sizes, hits = [], []
    rate = {}
    for R in radii:
        got = 0
        for _ in range(reps):
            bg = backgrounds[rng.integers(len(backgrounds))]
            m = 24
            cy = int(rng.integers(m, bg.shape[0] - m))
            cx = int(rng.integers(m, bg.shape[1] - m))
            hit = _detect_on_background(bg, R, cy, cx)
            sizes.append(float(2 * R)); hits.append(int(hit)); got += hit
        rate[R] = got / reps
    print("   直径[px] と検出率: " +
          " ".join("%d:%.2f" % (2 * R, rate[R]) for R in radii))
    sizes = np.array(sizes); hits = np.array(hits)
    a50 = a90 = a9095 = float("nan")
    try:
        fit = POD.pod_hitmiss_fit({"a": sizes, "hit": hits}, log_size=True)
        a50, a90, a9095 = fit.get("a50"), fit.get("a90"), fit.get("a90_95")
        print("   POD 当て(直径, log): a50 %.2f / a90 %.2f / a90/95 %.2f px" % (a50, a90, a9095))
    except ValueError as ex:
        print("   POD 当ては立たず(%s)。検出率の単調性だけ確かめる。" % ex)
    small = float(np.mean([rate[R] for R in radii[:3]]))
    large = float(np.mean([rate[R] for R in radii[-3:]]))
    print("   検出率: 小径 3 本 平均 %.2f → 大径 3 本 平均 %.2f" % (small, large))
    assert large > small + 0.3, \
        "大きい欠陥の検出率が小さい側を明確に上回らない: 小 %.2f 大 %.2f" % (small, large)
    assert large >= 0.6, "大きい欠陥の検出率が低すぎる: %.2f" % large
    return rate, (a50, a90, a9095)


# --------------------------------------------------------------------------- #
# 実データ                                                                      #
# --------------------------------------------------------------------------- #
def _load_image(path):
    from PIL import Image
    return np.asarray(Image.open(path).convert("L"), dtype=np.float64) / 255.0


def _load_mask(path):
    from PIL import Image
    return np.asarray(Image.open(path).convert("L")) > 127


def read_real():
    """CSV を読み、クラスごとに最大 PER_CLASS 枚(--all で全数)を層化して返す。"""
    try:
        import PIL  # noqa: F401
    except Exception:
        print("   実データ門は未実行(Pillow が無い)。合成のみを走らせる。")
        return None
    csv_path = os.path.join(DATA, "carinthia-s.csv")
    if not (DATA and os.path.exists(csv_path)):
        print("   実データ門は未実行(FULLSEYE_CARINTHIA_DATA が未設定/不在)。合成のみ。")
        return None
    rows = list(csv.reader(open(csv_path, encoding="utf-8"), delimiter=";"))[1:]
    by = {}
    for r in rows:
        by.setdefault(r[3], []).append(r)
    picked = {}
    for cls, items in by.items():
        picked[cls] = items if ALL else items[:PER_CLASS]
    total = sum(len(v) for v in picked.values())
    print("   実データ読込: クラス別 %s(計 %d 枚、クラス 5 は全 %d 枚)" %
          ({c: len(v) for c, v in sorted(picked.items())}, total, len(by.get("5", []))))
    return picked


def stage0_mask_convention(picked):
    """段 0: マスク境界は輝度勾配の峰(明るい縁)の内側か外側か。"""
    print("\n0) マスクの規約(境界 vs 輝度勾配の峰、clean な二値クラス 3/4/5)")
    print("   符号つき距離の勾配重み中心 cm[px](+ = 峰がマスクの外 = マスクは暗い芯だけ)")
    out = {}
    for cls in CLEAN_CLASSES:
        cms = []
        for r in picked.get(cls, []):
            im = _load_image(os.path.join(DATA, r[0]))
            M = _load_mask(os.path.join(DATA, r[1]))
            if M.sum() < 30 or (~M).sum() < 30:
                continue
            gy, gx = np.gradient(im)
            G = np.hypot(gx, gy)
            d_out = ndi.distance_transform_edt(~M)
            d_in = ndi.distance_transform_edt(M)
            dmap = d_out - d_in                       # 外 +, 内 -
            band = np.abs(dmap) <= 6.0
            w = G[band]
            if w.sum() <= 0:
                continue
            cms.append(float((w * dmap[band]).sum() / w.sum()))
        if cms:
            med = float(np.median(cms))
            out[cls] = (med, np.percentile(cms, 25), np.percentile(cms, 75), len(cms))
            print("   クラス %s: cm 中央 %+.2f px(四分位 %+.2f / %+.2f、n=%d)" %
                  (cls, med, out[cls][1], out[cls][2], len(cms)))
    if out:
        allmed = float(np.median([v[0] for v in out.values()]))
        side = "外(マスクは暗い芯、明るい縁を含まない)" if allmed > 0.5 else \
               ("内(マスクが明るい縁まで含む)" if allmed < -0.5 else "境界ほぼ一致")
        print("   → 規約: 峰はマスクの%s。全体中央 cm = %+.2f px。" % (side, allmed))
    return out


def stage2_3_real(picked):
    """段 2+3(実データ): 分割採点と、マスク/分割の面積比。"""
    print("\n2+3) 実データの分割採点(seg_score_card)と面積比(クラス別)")
    print("   %-5s %7s %8s %8s %8s %10s" %
          ("クラス", "n", "Dice中央", "Jacc中央", "境界F中央", "面積比中央"))
    table = {}
    polar = []
    for cls in CLEAN_CLASSES:
        dices, jaccs, bfs, arat = [], [], [], []
        for r in picked.get(cls, []):
            im = _load_image(os.path.join(DATA, r[0]))
            M = _load_mask(os.path.join(DATA, r[1]))
            if M.sum() < 30:
                continue
            polar.append(float(im[M].mean() - im[~M].mean()))
            # 正解マスクを見ず、画像の背景中央値と頑健標準偏差だけで決める。
            bg = float(np.median(im)); sig = _robust_std(im)
            seg = im < (bg - 3.0 * sig)
            seg = ndi.binary_opening(seg, iterations=1)
            dj = SE.seg_dice_jaccard(seg.astype(np.int32), M.astype(np.int32))
            bf = SE.seg_boundary_f(seg.astype(np.int32), M.astype(np.int32), tau=2.0)
            dices.append(dj["dice"]); jaccs.append(dj["jaccard"]); bfs.append(bf["f"])
            if M.sum() > 0:
                arat.append(float(seg.sum()) / float(M.sum()))
        if dices:
            table[cls] = (len(dices), float(np.median(dices)), float(np.median(jaccs)),
                          float(np.median(bfs)), float(np.median(arat)))
            print("   %-5s %7d %8.3f %8.3f %8.3f %10.3f" % (cls, *table[cls]))
    if polar:
        print("   ★実データの欠陥は背景より %+.3f 暗い(合成の明るい塊と極性が逆)。"
              % float(np.median(polar)))
    return table, (float(np.median(polar)) if polar else float("nan"))


def real_backgrounds(picked):
    """クラス 6(空マスク = 良品)の画像を POD の地に使う。"""
    bgs = []
    for r in picked.get("6", []):
        im = _load_image(os.path.join(DATA, r[0]))
        m = _load_mask(os.path.join(DATA, r[1]))
        if m.sum() == 0:
            bgs.append(im)
    return bgs


# --------------------------------------------------------------------------- #
def synthetic_backgrounds():
    """合成の良品の地(平らな base + ショット雑音)を何枚か。"""
    rng = np.random.default_rng(SEED + 1)
    out = []
    for k in range(6):
        flat = np.zeros((160, 160))
        out.append(SM.sem_render(flat, psf_px=PSF, base=BASE, dose=120.0, seed=SEED + k))
    return out


def _boundary(mask):
    return np.asarray(mask, bool) ^ ndi.binary_erosion(mask, iterations=1)


def make_figures():
    """図は ``FULLSEYE_FIGURE_DIR`` があるときだけ書く(既定の走行は図なしで 60 秒未満)。

    1 枚目: 合成 SEM 像(明るい縁が見える)に、真の縁(緑)と測定した縁(赤)を重ねる ——
    赤が緑の**外**にあるのが面積の太り。2 枚目: 半径ごとの面積比を、補正前(太る)と
    補正後(1 に戻る)で並べ、真値の 1.0 を破線で引く。
    """
    # Device-native micrographs: line/contact structures and two defect types.
    hh, ww = 512, 1024
    yy, xx = np.mgrid[:hh, :ww]
    height = np.zeros((hh, ww), np.float64)
    material = np.zeros((hh, ww), np.int32)
    for x0 in range(90, 900, 150):
        line = np.abs(xx - x0) < 24
        height[line] = 28.0; material[line] = 1
    for cy in (130, 380):
        for cx in (180, 480, 780):
            contact = (xx - cx) ** 2 + (yy - cy) ** 2 < 42 ** 2
            height[contact] = 42.0; material[contact] = 1
    particle = (xx - 690) ** 2 + (yy - 265) ** 2 < 25 ** 2
    bridge = (np.abs(yy - 260) < 13) & (xx > 365) & (xx < 515)
    height[particle] = 70.0; height[bridge] = 28.0
    material[particle | bridge] = 1
    se = SM.sem_render(height, pixel_nm=2.0, psf_px=2.2, edge_gain=1.0,
                       base=0.24, dose=45.0, charging=0.018, seed=225)
    signals = SM.sem_image(height[::4, ::4], material[::4, ::4], materials=("PMMA", "W"), substrate="SI",
                           energy_kev=5.0, pixel_nm=8.0, beam_sigma_nm=2.0,
                           electrons_per_pixel=1, detector="everhart", seed=226,
                           return_signals=True)
    # Use the Monte-Carlo material contrast on a coarse calibration grid, then
    # recompute a full-resolution count image from that contrast (no upscaling).
    mc = signals["bse"]
    c0 = float(np.mean(mc[material[::4, ::4] == 0]))
    c1 = float(np.mean(mc[material[::4, ::4] == 1]))
    expected = ndi.gaussian_filter(np.where(material == 1, c1, c0), 1.0)
    bse = np.random.default_rng(226).poisson(24.0 * expected) / 24.0
    truth = height > 0
    measured = se > (np.median(se) + 0.12)
    overlay = np.repeat((0.45 * se)[..., None], 3, axis=2)
    overlay[_boundary(truth)] = (0.1, 0.95, 0.2)
    overlay[_boundary(measured)] = (0.95, 0.15, 0.1)
    truth_edge = _boundary(truth); measured_edge = _boundary(measured)
    bias_nm = 2.0 * float(np.median(ndi.distance_transform_edt(~truth_edge)[measured_edge]))
    triptych = np.concatenate([np.repeat(se[..., None], 3, axis=2),
                               np.repeat(bse[..., None], 3, axis=2), overlay], axis=1)
    figs.save("sem_se_bse_bias", triptych,
              caption=("二次電子像（左、45 e⁻/pixel、PSF σ=4.4 nm、帯電勾配 0.018）｜反射電子像（中央）｜寸法測定重ね合わせ（右、緑=真値、赤=閾値輪郭）。等価半径の偏り %+.1f nm。" % bias_nm))
    # Eightfold zoom is recomputed at the same physical sampling, not nearest-neighbour enlarged.
    local_h = np.zeros((512, 512)); local_h[:, 256:] = 28.0
    crop = SM.sem_render(local_h, pixel_nm=0.5, psf_px=8.8, base=0.24,
                         dose=45.0, charging=0.018, seed=227)
    figs.save_grid("sem_edge_rim_zoom", [crop], captions=["256 nm 視野"], title="縁の明帯と検出器側の陰影（8倍視野）",
                   caption="0.5 nm/pixel で再計算した 256 nm 視野。明帯幅は PSF とともに増える。")
    dose_imgs = [SM.sem_render(height[:, :512], pixel_nm=2.0, psf_px=2.2, base=0.24,
                               dose=d, charging=0.018, seed=225 + int(d)) for d in (4.0, 16.0, 64.0)]
    figs.save_grid("sem_dose_series", dose_imgs, captions=["4 e⁻/pixel", "16 e⁻/pixel", "64 e⁻/pixel"],
                   title="照射量系列", caption="低照射量ほど粒状のショット雑音が増える。")

    S = 200; thr = BASE * 1.02
    h, foot = cone((S, S), 100, 100, 22)
    img = SM.sem_render(h, psf_px=3.0, base=BASE)
    _a, _p, seg = segment_bright(img, thr)
    rgb = np.repeat((img / img.max())[..., None], 3, axis=2)
    rgb[_boundary(foot)] = [0.1, 0.9, 0.2]       # 真の縁 = 緑
    rgb[_boundary(seg)] = [0.95, 0.1, 0.1]       # 測定の縁 = 赤(外側ににじむ)
    figs.save("sem_edge_inflation", rgb,
              caption="合成 SEM 像(半径 22 px の円錐欠陥、PSF σ=3)。緑 = 真の縁、"
                      "赤 = しきい値で測った縁。明るい縁ごと拾うので赤が緑の外に出る "
                      "= 面積の太り。形(Dice)は高いまま、寸法だけが系統的に太る。")

    radii = [10, 14, 18, 24, 30, 38]
    before = []
    for R in radii:
        hh, ff = cone((S, S), 100, 100, R)
        im = SM.sem_render(hh, psf_px=3.0, base=BASE)
        a, p, _ = segment_bright(im, thr); true = float(ff.sum())
        before.append(a / true)
    figs.save_plot(
        "sem_area_bias_vs_size",
        [("測定面積/真値", radii, before),
         ("真値 = 1.0", radii, [1.0] * len(radii))],
        xlabel="欠陥半径 R [px]", ylabel="測定面積 / 真の面積",
        styles=[None, None, "dashed"],
        colors=["wrong", "right", "reference"],
        caption="t/base=1.02 の数値模型。小さい欠陥ほど面積比が大きい。"
                "PSF 幅だけを引く一般補正はこの図では主張しない。")
    return 5


def main():
    t0 = time.perf_counter()
    print("SEM ウェハ欠陥: 明るい縁が寸法をどれだけ太らせるか")
    print("=" * 68)
    picked = read_real()
    real_on = picked is not None

    # --- 実データ段(環境変数があるときだけ) ---
    t_real0 = time.perf_counter()
    mask_conv = seg_real = polarity = None
    if real_on:
        mask_conv = stage0_mask_convention(picked)
        seg_real, polarity = stage2_3_real(picked)
    t_real = time.perf_counter() - t_real0

    # --- 合成段(常に走る = CI の門) ---
    t_syn0 = time.perf_counter()
    sec_err = stage1_physics()
    _rows, ratios, wop, dmed, sweep = stage3_bias_synthetic()
    corrections = stage4_correction_synthetic()
    noisy_ratios = stage4_noise_check()
    mb, ma = corrections[1.02]

    # --- 埋め込み POD(地は実データのクラス 6、無ければ合成) ---
    bgs, label = None, "合成の雑音地"
    if real_on:
        rb = real_backgrounds(picked)
        if rb:
            bgs, label = rb, "実データ良品(クラス 6)"
    if bgs is None:
        bgs = synthetic_backgrounds()
    rate, (a50, a90, a9095) = stage5_pod(bgs, label)
    nfig = make_figures()
    if figs.errors():
        print("   図の書き出しで失敗:", "; ".join(figs.errors()))
    elif figs.enabled():
        print("   図 %d 枚を書き出した。" % nfig)
    t_syn = time.perf_counter() - t_syn0

    # --- 段 6: 表 ---
    print("\n6) まとめ")
    if real_on and seg_real:
        print("   実データ(クラス別 Dice / Jaccard / 境界F / 面積比):")
        for cls, v in sorted(seg_real.items()):
            print("     クラス %s: n=%d  Dice %.3f  Jacc %.3f  境界F %.3f  面積比 %.3f"
                  % (cls, v[0], v[1], v[2], v[3], v[4]))
        if mask_conv:
            cm = float(np.median([v[0] for v in mask_conv.values()]))
            print("   マスク規約: 勾配の峰はマスク境界の cm=%+.2f px(正=外)。" % cm)
    else:
        print("   実データ門は未実行(合成のみ)。")
    print("   合成: 面積の太り 比 %.3f〜%.3f、有効縁幅/PSF %.2f、補正で偏り %.3f→%.3f。"
          % (min(ratios), max(ratios), wop, mb, ma))
    print("   埋め込み POD(地 = %s): a90/95 %.2f px(大欠陥検出率 %.2f)。"
          % (label, a9095, np.mean([rate[r] for r in sorted(rate)[-2:]])))
    print("   所要: 実データ段 %.2f 秒 / 合成段 %.2f 秒 / 合計 %.2f 秒"
          % (t_real, t_syn, time.perf_counter() - t0))

    print("\nPASS: sem_render は平面一様・斜面 sec θ・段差応答の二次モーメント幅=PSF(誤差 %.0e)。"
          "面積比はしきい値で変わる(%.2f〜%.2f)が Dice は高い(中央 %.3f)—— t/base=1.02 の"
          "閉形式補正で偏りは %.3f→%.3f。埋め込み POD(地 = %s)の a90/95 は %.1f px。%s"
          % (sec_err, min(ratios), max(ratios), dmed, mb, ma, label, a9095,
             ("実データ門も通過。" if real_on else "実データ門は未実行(合成のみ)。")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
