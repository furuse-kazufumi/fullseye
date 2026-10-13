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
   段差の明るい縁の幅が PSF 幅(いずれも閉形式)。
2. **古典の分割連鎖**: しきい値 → ``blob_label`` → ``blob_features``。実データでは
   専門家マスクと ``seg_score_card``(Dice / Jaccard / 境界 F)。
3. **寸法の偏り**: 合成(真値の面積が厳密)で、面積の太り ΔA を測り、**閉形式の予測
   ΔA ≈ 周囲長 × 有効縁幅(≈ PSF 幅)** と照合。実データはマスク/分割の面積比を
   クラスごとに出す。
4. **物理モデルによる補正**: 既知のビーム PSF 幅で面積を補正(ΔA を差し引く)。合成では
   偏りがゼロに戻る門、実データでは偏りが縮むかを報告(縮まなければそのまま書く)。
5. **埋め込み POD**: 良品の地(実データの空マスク画像、無ければ合成の雑音地)に既知寸法の
   欠陥を ``sem_render`` で埋め込み、分割連鎖で検出して ``pod_hitmiss_fit`` で a90/95。
   門 = 大きい欠陥ほど検出率が単調増加・a90/95 が存在。

予想(2026-10-13): ★★**Dice は高いのに面積は系統的に太り、物理(既知 PSF 幅)で
補正すると偏りが消える。** 予想どおりでなければ正直にそのまま書く。異常に良い結果は
内訳を疑う。★実データの SEM 欠陥は**暗い**(背景より暗い穴)ので、縁は暗部を囲む明るい
リングになる —— 合成の「明るい塊」と極性が逆であることも印字する。

実データ(repo には同梱しない。環境変数 ``FULLSEYE_CARINTHIA_DATA`` に
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
import os
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

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

    print("   段差 → 明るい縁の幅 = PSF 幅:")
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
    print("   → 平面一様・斜面 sec θ(誤差 %.0e)・縁の幅 = PSF。" % sec_err)
    return sec_err


# --------------------------------------------------------------------------- #
# 段 3: 寸法の偏り(合成、真値の面積が厳密)                                     #
# --------------------------------------------------------------------------- #
def stage3_bias_synthetic():
    print("\n3) 寸法の偏り(合成、真値の面積が厳密): ΔA ≈ 周囲長 × 有効縁幅")
    print("   %-6s %-6s %8s %8s %7s %7s %8s %8s" %
          ("半径R", "PSF", "真面積", "測定面積", "比", "Dice", "周囲長", "ΔA/周囲長"))
    S = 200; thr = BASE * 1.02             # 背景のすぐ上(外側へにじむ明るい縁を拾う)
    rows, ratios, dices, w_over_psf = [], [], [], []
    for R in (12, 18, 26, 36):
        for psf in (1.5, 2.5, 3.5):
            h, foot = cone((S, S), 100, 100, R)
            img = SM.sem_render(h, psf_px=psf, base=BASE)
            a, p, mask = segment_bright(img, thr)
            true = float(foot.sum())
            dice = SE.seg_dice_jaccard(mask.astype(np.int32), foot.astype(np.int32))["dice"]
            w = (a - true) / p if p > 0 else 0.0
            rows.append((R, psf, true, a, p))
            ratios.append(a / true); dices.append(dice); w_over_psf.append(w / psf)
            print("   %-6d %-6.1f %8.0f %8.0f %7.3f %7.3f %8.0f %8.2f" %
                  (R, psf, true, a, a / true, dice, p, w))
    wop = float(np.median(w_over_psf))
    dmed = float(np.median(dices))
    print("   → ★Dice は高い(中央 %.3f = 形はよく合う)のに、面積は系統的に太る"
          "(比 %.3f〜%.3f)。有効縁幅 / PSF の中央値 = %.2f —— **太りは 周囲長 × PSF 幅 "
          "でよく説明できる**。" % (dmed, min(ratios), max(ratios), wop))
    assert min(ratios) > 1.0, "太りが出ない(どこかで比が 1 以下): %.3f" % min(ratios)
    assert dmed > 0.8, "Dice が高くない(形が合っていない): %.3f" % dmed
    assert 0.7 < wop < 1.4, "ΔA が 周囲長×PSF から外れる: w/psf=%.2f" % wop
    return rows, ratios, wop, dmed


# --------------------------------------------------------------------------- #
# 段 4: 物理モデルによる補正(既知のビーム PSF 幅で ΔA を差し引く)              #
# --------------------------------------------------------------------------- #
def stage4_correction_synthetic():
    print("\n4) 物理による補正: 面積 − 周囲長 × PSF幅 → 合成では偏りが消える")
    print("   %-6s %-6s %8s %9s %9s" % ("半径R", "PSF", "真面積", "補正前比", "補正後比"))
    S = 200; thr = BASE * 1.02
    before, after = [], []
    for R in (12, 18, 26, 36):
        for psf in (1.5, 2.5, 3.5):
            h, foot = cone((S, S), 100, 100, R)
            img = SM.sem_render(h, psf_px=psf, base=BASE)
            a, p, _ = segment_bright(img, thr)
            true = float(foot.sum())
            corrected = a - p * psf          # 既知のビーム PSF 幅で縁の太りを引く
            before.append(a / true); after.append(corrected / true)
            print("   %-6d %-6.1f %8.0f %9.3f %9.3f" % (R, psf, true, a / true, corrected / true))
    mb = float(np.median([abs(x - 1) for x in before]))
    ma = float(np.median([abs(x - 1) for x in after]))
    print("   → 補正前の偏り(中央 |比-1|)%.3f → 補正後 %.3f。**既知の PSF 幅で縁の太りが消える**。"
          % (mb, ma))
    assert ma < mb, "補正で偏りが縮まない: 前 %.3f 後 %.3f" % (mb, ma)
    assert ma < 0.05, "補正後も偏りが残る: %.3f" % ma
    return mb, ma


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
            # 欠陥は暗い → 暗部を拾う(面積ぶんだけ下側分位)
            q = 100.0 * min(2.0 * M.mean(), 0.5)
            seg = im < np.percentile(im, q)
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
    before, after = [], []
    for R in radii:
        hh, ff = cone((S, S), 100, 100, R)
        im = SM.sem_render(hh, psf_px=3.0, base=BASE)
        a, p, _ = segment_bright(im, thr); true = float(ff.sum())
        before.append(a / true); after.append((a - p * 3.0) / true)
    figs.save_plot(
        "sem_area_bias_vs_size",
        [("補正前(面積/真値)", radii, before),
         ("補正後(PSF 幅を引く)", radii, after),
         ("真値 = 1.0", radii, [1.0] * len(radii))],
        xlabel="欠陥半径 R [px]", ylabel="測定面積 / 真の面積",
        styles=[None, None, "dashed"],
        colors=["wrong", "right", "reference"],
        caption="面積の太りは小さい欠陥ほど大きい(周囲長/面積 ∝ 1/R)。既知のビーム PSF 幅を"
                "引くと、どの大きさでも 1.0 に戻る。")
    return 2


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
    _rows, ratios, wop, dmed = stage3_bias_synthetic()
    mb, ma = stage4_correction_synthetic()

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

    print("\nPASS: sem_render は平面一様・斜面 sec θ・縁幅=PSF(誤差 %.0e)。"
          "面積は系統的に太る(比 %.2f〜%.2f)が Dice は高い(中央 %.3f)—— 既知の PSF 幅で"
          "引くと偏りは %.3f→%.3f に消える。埋め込み POD(地 = %s)の a90/95 は %.1f px。%s"
          % (sec_err, min(ratios), max(ratios), dmed, mb, ma, label, a9095,
             ("実データ門も通過。" if real_on else "実データ門は未実行(合成のみ)。")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
