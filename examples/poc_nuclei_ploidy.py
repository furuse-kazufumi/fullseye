# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""poc_nuclei_ploidy — 蛍光核の**積分輝度**から倍数性を出す。面積では分かれない。

    py -3.11 examples/poc_nuclei_ploidy.py

【この PoC が答える問い】
DNA を化学量論的に染めた細胞核は、**DNA 量が積分輝度に比例**する(image
cytometry の前提)。だから 2n と 4n は積分輝度のヒストグラムで 2 山に分かれる
——「はず」。問いは「**面積で代用したらどれだけ悪くなるか**」「**どこで積分輝度
も嘘になるか**」。答えは「面積は真値でも 20 % 誤分類、積分輝度は 0 %。ただし
**背景を引き忘れると分類は生き残ったまま DNA 指数だけが -21 % 壊れる**」。

【グラウンドトゥルース(自分で仕込んだ真値)】
核ごとに倍数性 p ∈ {2, 4} を撒き、**DNA 量 D = (p/2)·D0·lognormal(CV 10 %)**、
**面積 A = A0·1.5^((p-2)/2)·lognormal(CV 30 %)**(= 4n は平均 1.5 倍だが
DNA 比 2.0 とは一致しない。生物学的なばらつきをそう置いた)。核は楕円に
半径変調を掛けた閉曲線で、副標本 3x3 の被覆率で描き、**振幅を Σcov = D に
なるよう決める**ので ∫I = D が厳密。真の面積は描いた被覆率の総和そのもの。

【この PoC が示すこと(数字はすべて実行時に印字される実測値)】

 1. **積分輝度は保存される**。PSF でぼかしても総和は 1e-13 の桁で変わらない。
    ただし**マスクで積分すると裾が落ちる**: 大津のマスクで -8.7 %(中央値)。
    これは倍率の偏りなので分類には効かない —— **量を報告するときだけ効く**。
 2. ★★**ゼロ点(面積)と対比(積分輝度)**。全探索でいちばん良いしきい値でも
    誤分類は **面積(真値) 20.0 % / 積分輝度 0.0 %**。積分輝度の 2 山の
    分離は **6.9 σ**、面積は **1.4 σ**。
 3. ★★**「測った面積」は面積ではない**。固定しきい値のマスク面積で分けると
    誤分類が **8.7 %** —— 真の面積(20.0 %)より**良い**。ln(測定/真値) を
    ln(明るさ) に回帰すると傾き **+0.26**、相関 **0.93**。明るい核ほどぼけた
    縁がしきい値を外側で切るので、**面積という名前で DNA 量を漏らしている**。
 4. ★**予想が外れた**。「焦点がぼければ面積分類器は壊れる」と踏んでいたが、
    PSF σ を 0.6 → 1.5 px にすると誤分類は **8.7 % → 3.4 %** と**良くなる**。
    漏れの傾きが **0.26 → 0.42** に増えるため。ぼかすほど「面積」は DNA 量に
    近づく —— 性能が上がったのではなく、**測っている量が入れ替わっている**。
 5. ★★**背景の引き忘れ**。偽の項は面積に比例する: (測定 - 真値) を面積に
    回帰した傾きは **背景レベル b と 6 桁一致**。ところが分類は壊れない
    (b = 核輝度の 5 倍でも誤分類 4.7 %)。**壊れるのは量のほう** ——
    DNA 指数(4n/2n の積分輝度比)は真値 2.00 に対し **1.58**(-21 %)。
    ★**分類だけを見ていたら気づけない**。対照群として (i) 背景の中央値を引く
    (ii) `fs.aperture_photometry` の環状背景 —— どちらも DNA 指数を戻す。
 6. ★**飽和**は逆向きに効く。露光を上げると小さくて明るい核から順に頭が
    潰れ、**4n だけが過小**になる。飽和画素 2.4 % で DNA 指数が 2.00 → 1.83。
 7. ★**融合**は 2n+2n を 4n に見せる。密に撒くと 119 塊中 19 が融合し、
    4n の割合の推定が真値 0.30 に対し **0.42** になる。`solidity` の 1 本の
    しきい値で検出率 0.89 / 誤検出 0.05、落としたあとは **0.31** に戻る。
 8. ★**混合比の推定**は Otsu でも EM でも当たる(積分輝度なら)。真値 0.05〜
    0.70 に対し最大偏差 **0.014**。同じことを面積でやると最大 **0.30** 外す。

【節立て】
 1) 合成器の検算(積分輝度の保存とマスクの裾落ち)
 2) ★★ゼロ点(面積)vs 積分輝度
 3) ★★「測った面積」は面積ではない / ★焦点をぼかすと良くなる(予想外)
 4) ★★背景の引き忘れ —— 分類は生き残り、量が壊れる
 5) ★飽和
 6) ★融合と solidity
 7) ★混合比の推定
 8) 道具の穴(assert で現状を固定)

EXTEND: 実写に差し替えるなら :func:`render` の返り値と ``nuc`` の対を、撮影
画像と「核ごとの倍数性の真値」に置き換える。**真値をフローサイトメトリで
取らないこと** —— 別の標本を測っているので核ごとの対応が付かない。同じ
スライドを再染色して核型解析するか、既知倍数性の細胞株を混ぜる。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

N_PX = 384
SS = 3                     # 画素あたりの副標本(片側)
A2N = 240.0                # 2n 核の面積の中央値 [px^2]
AREA_RATIO = 1.5           # 4n / 2n の面積比(DNA 比 2.0 とは**わざと**ずらす)
AREA_CV = 0.30
D0 = 20000.0               # 2n の DNA 量(積分輝度、任意単位)
DNA_CV = 0.10
PSF_A = 0.2                # gaussian op の a。sigma = 3a [px]
N_NUC = 170


def make_nuclei(n=N_NUC, frac4=0.30, seed=7, sep=1.20):
    """核を撒く。``sep`` が 1 未満だと触れる(融合する)。"""
    rng = np.random.default_rng(seed)
    ploidy = np.where(rng.random(n) < frac4, 4, 2)
    area = A2N * (AREA_RATIO ** ((ploidy - 2) / 2.0)) * np.exp(rng.normal(0, AREA_CV, n))
    dna = D0 * (ploidy / 2.0) * np.exp(rng.normal(0, DNA_CV, n))
    req = np.sqrt(area / np.pi)
    cy, cx = [], []
    for i in range(n):
        # 試行の予算は**核ごと**に持つ(全体で持つと、後半の核が予算切れで
        # 素通りして「疎に撒いたはずが融合している」という合成側の嘘になる)。
        for t in range(600):
            y = rng.uniform(req[i] + 3, N_PX - req[i] - 3)
            x = rng.uniform(req[i] + 3, N_PX - req[i] - 3)
            ok = all((y - cy[j]) ** 2 + (x - cx[j]) ** 2 >= (sep * (req[i] + req[j])) ** 2
                     for j in range(len(cy)))
            if ok or t == 599:
                cy.append(y)
                cx.append(x)
                break
    return {"row": np.array(cy), "col": np.array(cx), "ploidy": ploidy,
            "area_target": area, "dna": dna,
            "aspect": rng.uniform(1.0, 1.6, n), "angle": rng.uniform(0, np.pi, n),
            "wob": rng.uniform(0, 2 * np.pi, (n, 2))}


def render(nuc, bkg=0.0, gain=1.0, sat=None, noise=0.0, psf=PSF_A, seed=0):
    """撮る。**振幅は Σcov = D になるよう決める**ので ∫I = D が厳密。"""
    img = np.zeros((N_PX, N_PX))
    area_true = np.zeros(len(nuc["row"]))
    off = (np.arange(SS) + 0.5) / SS - 0.5
    yy, xx = np.mgrid[0:N_PX, 0:N_PX].astype(float)
    for i in range(len(nuc["row"])):
        a = np.sqrt(nuc["area_target"][i] * nuc["aspect"][i] / np.pi)
        b = nuc["area_target"][i] / (np.pi * a)
        r0, c0 = nuc["row"][i], nuc["col"][i]
        pad = int(np.ceil(a * 1.25)) + 2
        i0, i1 = max(0, int(r0) - pad), min(N_PX, int(r0) + pad + 1)
        j0, j1 = max(0, int(c0) - pad), min(N_PX, int(c0) + pad + 1)
        ct, st = np.cos(nuc["angle"][i]), np.sin(nuc["angle"][i])
        w1, w2 = nuc["wob"][i]
        cov = np.zeros((i1 - i0, j1 - j0))
        for dy in off:
            for dx in off:
                dr = yy[i0:i1, j0:j1] + dy - r0
                dc = xx[i0:i1, j0:j1] + dx - c0
                u = (dc * ct + dr * st) / a
                v = (-dc * st + dr * ct) / b
                # 楕円に半径変調を掛ける(実際の核は凸ではない -> solidity < 1)
                ph = np.arctan2(v, u)
                lim = 1.0 + 0.10 * np.cos(3 * ph + w1) + 0.06 * np.cos(5 * ph + w2)
                cov += (u * u + v * v <= lim * lim)
        cov /= SS * SS
        s = float(cov.sum())
        area_true[i] = s
        if s > 0:
            img[i0:i1, j0:j1] += cov * (nuc["dna"][i] / s)
    if psf > 0:
        img = np.asarray(fs.apply(img, "gaussian", a=psf))
    img = img * gain + bkg
    if noise > 0:
        img = img + np.random.default_rng(seed).normal(0.0, noise, img.shape)
    if sat is not None:
        img = np.minimum(img, sat)
    return img, area_true


# --- 測る -------------------------------------------------------------------- #
def segment(img):
    """大津で前景を出して連結成分に切る(この族の外 → blob 族へ)。"""
    lo, hi = np.percentile(img, 1.0), np.percentile(img, 99.5)
    nrm = np.clip((img - lo) / max(hi - lo, 1e-12), 0.0, 1.0)
    return fs.ledger.blob_label(np.asarray(fs.apply(nrm, "sk_otsu")) > 0.5)


def objects(img, lab, nuc, area_true):
    """塊ごとの測定値と、真値との対応(中心が乗っているラベルで割り当てる)。"""
    f = fs.ledger.blob_features(lab)
    n = int(f["n"])
    integ = ndimage.sum_labels(img, lab, index=np.arange(1, n + 1))
    lid = lab[np.clip(nuc["row"].astype(int), 0, N_PX - 1),
              np.clip(nuc["col"].astype(int), 0, N_PX - 1)]
    members = [[] for _ in range(n + 1)]
    for k, li in enumerate(lid):
        if li > 0:
            members[li].append(k)
    single = np.array([k for k in range(1, n + 1) if len(members[k]) == 1], dtype=int)
    src = np.array([members[k][0] for k in single], dtype=int)
    return {"f": f, "n": n, "integ": integ, "members": members, "single": single,
            "idx": single - 1, "src": src,
            "ploidy": nuc["ploidy"][src], "dna": nuc["dna"][src],
            "area_true": area_true[src]}


def best_split(v, is_hi):
    """全探索でいちばん良い 1 本のしきい値 → (誤分類率, しきい値)。"""
    v = np.asarray(v, float)
    o = np.unique(v)
    if o.size < 2:
        return 1.0, float("nan")
    cand = (o[:-1] + o[1:]) / 2.0
    err = np.array([np.mean((v > t) != is_hi) for t in cand])
    j = int(np.argmin(err))
    return float(err[j]), float(cand[j])


def separation(v, is_hi):
    """2 群の平均差を、群内標準偏差(プール)で割った分離度[σ]。"""
    a, b = np.asarray(v)[~is_hi], np.asarray(v)[is_hi]
    if a.size < 2 or b.size < 2:
        return float("nan")
    s = np.sqrt(((a.size - 1) * a.var(ddof=1) + (b.size - 1) * b.var(ddof=1))
                / (a.size + b.size - 2))
    return float(abs(b.mean() - a.mean()) / max(s, 1e-12))


def dna_index(v, is_hi):
    """DNA 指数 = 4n 群の中央値 / 2n 群の中央値(真値 2.00)。"""
    return float(np.median(np.asarray(v)[is_hi]) / np.median(np.asarray(v)[~is_hi]))


# --------------------------------------------------------------------------- #
# 1) 合成器の検算                                                              #
# --------------------------------------------------------------------------- #
def section1_check(nuc):
    print("=" * 78)
    print("1) 合成器の検算 —— 積分輝度は保存されるか(ゼロ点その 0)")
    print("=" * 78)
    img_raw, area_true = render(nuc, psf=0.0)
    total_true = float(nuc["dna"].sum())
    print("  仕込んだ DNA の総和            %.6e" % total_true)
    print("  ぼかす前の画像の総和           %.6e (相対 %.2e)"
          % (img_raw.sum(), abs(img_raw.sum() / total_true - 1)))
    img, _ = render(nuc)
    print("  PSF sigma=%.1f px の後の総和   %.6e (相対 %.2e)"
          % (3 * PSF_A, img.sum(), abs(img.sum() / total_true - 1)))
    lab = segment(img)
    o = objects(img, lab, nuc, area_true)
    rel = o["integ"][o["idx"]] / o["dna"]
    ra = o["f"]["area"][o["idx"]] / o["area_true"]
    hi = o["ploidy"] == 4
    print()
    print("  ★ただし**マスクで積分すると裾が落ちる**(2 節以降の測定値はこの上に乗る):")
    print("     積分輝度 測定/真値  中央 %.4f  四分位 %.4f 〜 %.4f"
          % (np.median(rel), *np.percentile(rel, [25, 75])))
    print("     面積     測定/真値  中央 %.4f  四分位 %.4f 〜 %.4f"
          % (np.median(ra), *np.percentile(ra, [25, 75])))
    r2, r4 = float(np.median(rel[~hi])), float(np.median(rel[hi]))
    di = dna_index(o["integ"][o["idx"]], hi)
    print()
    print("  → ★**予想が外れた**。「裾落ちは倍率の偏りだから比には効かない」と")
    print("     書きかけたが、**効く**。裾落ちは 2n で %.1f %% / 4n で %.1f %% と"
          % (100 * (1 - r2), 100 * (1 - r4)))
    print("     大きさに依存する(落ちるのは周囲長に比例した縁の帯で、小さい核ほど")
    print("     面積に対する縁の割合が大きい)。だから **DNA 指数(4n/2n の比)は")
    print("     真値 2.00 に対し %.3f**(%+.1f %%)—— 分類の前に、量が既に歪んでいる。"
          % (di, 100 * (di / 2.0 - 1)))
    return img, lab, o, float(np.median(rel)), di


# --------------------------------------------------------------------------- #
# 2) ゼロ点 vs 積分輝度                                                        #
# --------------------------------------------------------------------------- #
def section2_zero_point(o):
    print()
    print("=" * 78)
    print("2) ★★ゼロ点(面積で分ける)vs 対比(積分輝度で分ける)")
    print("=" * 78)
    print("  しきい値は**全探索でいちばん良いもの**を選ぶ(どちらにも最良を与える)。")
    print()
    hi = o["ploidy"] == 4
    feats = [("面積(真値)", o["area_true"]),
             ("面積(測定)", o["f"]["area"][o["idx"]]),
             ("積分輝度(測定)", o["integ"][o["idx"]]),
             ("DNA 量(真値)", o["dna"])]
    print("  %-18s %10s %10s %12s" % ("特徴量", "誤分類", "分離度σ", "最良しきい値"))
    print("  " + "-" * 54)
    out = {}
    for name, v in feats:
        e, t = best_split(v, hi)
        s = separation(np.log(np.clip(v, 1e-12, None)), hi)
        out[name] = (e, s, t)
        print("  %-18s %10.4f %10.2f %12.1f" % (name, e, s, t))
    print()
    print("  → 積分輝度は 2 山に**完全に**分かれる(分離 %.1f σ)。面積は真値でも"
          % out["積分輝度(測定)"][1])
    print("     %.1f σ しかなく、%.1f %% を取り違える。" %
          (out["面積(真値)"][1], 100 * out["面積(真値)"][0]))
    print("  → ★★ところが**測った面積のほうが真の面積より良い**"
          "(%.1f %% < %.1f %%)。3 節で理由を切り分ける。"
          % (100 * out["面積(測定)"][0], 100 * out["面積(真値)"][0]))
    figs.save_plot("histograms",
                   [("2n 積分輝度", np.sort(o["integ"][o["idx"]][~hi]),
                     np.linspace(0, 1, int((~hi).sum()))),
                    ("4n 積分輝度", np.sort(o["integ"][o["idx"]][hi]),
                     np.linspace(0, 1, int(hi.sum()))),
                    ("2n 面積x100", np.sort(o["f"]["area"][o["idx"]][~hi]) * 100,
                     np.linspace(0, 1, int((~hi).sum()))),
                    ("4n 面積x100", np.sort(o["f"]["area"][o["idx"]][hi]) * 100,
                     np.linspace(0, 1, int(hi.sum())))],
                   xlabel="特徴量(面積は x100 で重ねた)", ylabel="累積割合",
                   title="積分輝度は分かれ、面積は重なる",
                   caption="累積分布。積分輝度の 2 本は離れ、面積の 2 本は大きく重なる。")
    return out


# --------------------------------------------------------------------------- #
# 3) 面積の漏れ                                                                #
# --------------------------------------------------------------------------- #
def section3_area_leak(nuc, o):
    print()
    print("=" * 78)
    print("3) ★★「測った面積」は面積ではない —— 明るさが漏れている")
    print("=" * 78)
    print("  固定しきい値のマスクは、明るい核ほど**外側**で縁を切る。だから")
    print("  マスク面積には DNA 量が混ざる。回帰で量を出す。")
    print()
    hi = o["ploidy"] == 4
    print("  %-14s %8s %10s %10s %10s" % ("PSF sigma px", "漏れ傾き", "相関", "面積 誤分類",
                                          "積分 誤分類"))
    print("  " + "-" * 56)
    rows, leak = [], {}
    for psf in (0.1, 0.2, 0.35, 0.5):
        img, at = render(nuc, psf=psf)
        oo = objects(img, segment(img), nuc, at)
        h2 = oo["ploidy"] == 4
        bright = oo["dna"] / oo["area_true"]
        rel = oo["f"]["area"][oo["idx"]] / oo["area_true"]
        slope = float(np.polyfit(np.log(bright), np.log(rel), 1)[0])
        corr = float(np.corrcoef(np.log(bright), np.log(rel))[0, 1])
        ea = best_split(oo["f"]["area"][oo["idx"]], h2)[0]
        ei = best_split(oo["integ"][oo["idx"]], h2)[0]
        leak[psf] = (slope, corr, ea, ei)
        rows.append(["%.1f" % (3 * psf), "%+.3f" % slope, "%.3f" % corr,
                     "%.4f" % ea, "%.4f" % ei])
        print("  %-14.1f %+8.3f %10.3f %10.4f %10.4f" % (3 * psf, slope, corr, ea, ei))
    print()
    s0, s1 = leak[0.2][0], leak[0.5][0]
    print("  → ★★ln(測定面積/真の面積) を ln(明るさ) に回帰した傾きは **%+.2f**"
          % leak[0.2][0])
    print("     (相関 %.2f)。面積という名前の量が、DNA 量を %.0f %% の指数で"
          % (leak[0.2][1], 100 * leak[0.2][0]))
    print("     漏らしている。真の面積で分けたときの %.1f %% との差はここから来る。"
          % (100 * best_split(o["area_true"], hi)[0]))
    print("  → ★**予想が外れた**。「ぼかせば面積分類器は壊れる」と踏んでいたが、")
    print("     PSF sigma %.1f → %.1f px で誤分類は %.4f → %.4f と**良くなる**。"
          % (0.3, 1.5, leak[0.1][2], leak[0.5][2]))
    print("     漏れの傾きが %+.2f → %+.2f に増えるため。**性能が上がったのではなく、"
          % (s0, s1))
    print("     測っている量が入れ替わっている** —— ぼかすほど「面積」は DNA 量に近づく。")
    print("     積分輝度のほうは %.4f → %.4f で動かない(総和は保存されるから)。"
          % (leak[0.1][3], leak[0.5][3]))
    return leak, rows


# --------------------------------------------------------------------------- #
# 4) 背景の引き忘れ                                                            #
# --------------------------------------------------------------------------- #
def section4_background(nuc):
    print()
    print("=" * 78)
    print("4) ★★背景(暗電流)の引き忘れ —— 面積に比例した偽の項が乗る")
    print("=" * 78)
    img0, at0 = render(nuc)
    lab0 = segment(img0)
    o0 = objects(img0, lab0, nuc, at0)
    unit = float(np.median(img0[lab0 > 0]))       # 核 1 画素の代表輝度
    print("  背景 b は「核 1 画素の代表輝度 %.1f」の倍数で振る。" % unit)
    print("  マスクの出し方(百分位で正規化してから大津)はアフィン不変なので、")
    print("  **セグメンテーションは動かない** —— 積分だけを変える対照実験になる。")
    print()
    print("  %6s %10s %10s %12s %12s %12s" %
          ("b/核輝度", "誤分類", "DNA 指数", "背景を引く", "環状背景", "偽項の傾き"))
    print("  " + "-" * 68)
    muls = [0.0, 0.5, 1.0, 2.0, 3.0, 5.0]
    curve = {"raw": [], "sub": [], "ap": [], "err": []}
    for mul in muls:
        b = mul * unit
        img, at = render(nuc, bkg=b)
        lab = segment(img)
        o = objects(img, lab, nuc, at)
        hi = o["ploidy"] == 4
        raw = o["integ"][o["idx"]]
        bg = float(np.median(img[lab == 0]))
        sub = ndimage.sum_labels(img - bg, lab, index=np.arange(1, o["n"] + 1))[o["idx"]]
        # 環状背景(astrostack の測光。核ごとに半径を変えて呼ぶ)
        rad = np.sqrt(o["f"]["area"][o["idx"]] / np.pi)
        ap = np.array([fs.aperture_photometry(img, [(o["f"]["row"][k], o["f"]["col"][k])],
                                              r_aperture=1.25 * r, r_inner=1.6 * r,
                                              r_outer=2.4 * r)[0]["flux"]
                       for k, r in zip(o["idx"], rad)])
        slope = float(np.polyfit(o["f"]["area"][o["idx"]],
                                 raw - o0["integ"][o0["idx"]], 1)[0]) if mul > 0 else 0.0
        e = best_split(raw, hi)[0]
        curve["raw"].append(dna_index(raw, hi))
        curve["sub"].append(dna_index(sub, hi))
        curve["ap"].append(dna_index(ap, hi))
        curve["err"].append(e)
        print("  %6.1f %10.4f %10.3f %12.3f %12.3f %12.3f"
              % (mul, e, curve["raw"][-1], curve["sub"][-1], curve["ap"][-1], slope))
    print()
    print("  → ★★偽の項は**面積に比例**する。(測定 - 背景なしの測定) を面積に")
    print("     回帰した傾きは b = %.3f のとき %.3f —— 定義どおり。"
          % (5.0 * unit, slope))
    print("  → ★**分類は壊れない**(b が核輝度の 5 倍でも誤分類 %.3f)。壊れるのは"
          % curve["err"][-1])
    print("     **量のほう**: DNA 指数が b=0 の %.3f から %.3f へ(%+.0f %%)。"
          % (curve["raw"][0], curve["raw"][-1],
             100 * (curve["raw"][-1] / curve["raw"][0] - 1)))
    print("     分類だけを見ていたら気づけない —— これがこのシリーズの中心的な形。")
    print("  → 対照群。**背景を引けば b をいくら振っても %.3f のまま**"
          % curve["sub"][-1])
    print("     (1 節の裾落ちぶんだけ 2.00 より高い)。`fs.aperture_photometry` の")
    print("     環状背景なら %.3f —— 開口が裾まで含むので**裾落ちも同時に直る**。"
          % curve["ap"][-1])
    print("     ★背景を引くだけでは 1 節の歪み(+%.1f %%)は残る。2 つは別の穴。"
          % (100 * (curve["sub"][-1] / 2.0 - 1)))
    figs.save_plot("background",
                   [("引き忘れ", muls, curve["raw"]),
                    ("背景を引く", muls, curve["sub"]),
                    ("環状背景 (aperture)", muls, curve["ap"]),
                    ("真値 2.00", muls, [2.0] * len(muls))],
                   xlabel="背景 b / 核 1 画素の輝度", ylabel="DNA 指数 (4n/2n)",
                   title="分類は生き残り、量が壊れる",
                   caption="誤分類率はほぼ 0 のままだが、DNA 指数は背景とともに 2.00 から落ちる。")
    return unit, muls, curve


# --------------------------------------------------------------------------- #
# 5) 飽和                                                                      #
# --------------------------------------------------------------------------- #
def section5_saturation(nuc):
    print()
    print("=" * 78)
    print("5) ★飽和 —— 小さくて明るい核から先に潰れるので 4n だけ過小になる")
    print("=" * 78)
    img0, at0 = render(nuc)
    peak = float(img0.max())
    print("  露光を上げる代わりに、飽和レベルを下げて同じことをする(peak %.1f)。" % peak)
    print()
    print("  %10s %12s %10s %10s" % ("飽和/peak", "飽和画素 %", "DNA 指数", "誤分類"))
    print("  " + "-" * 46)
    rows = []
    for frac in (1.0, 0.6, 0.4, 0.3, 0.22):
        img, at = render(nuc, sat=peak * frac)
        lab = segment(img)
        o = objects(img, lab, nuc, at)
        hi = o["ploidy"] == 4
        nsat = 100.0 * float(np.mean(img[lab > 0] >= peak * frac - 1e-9))
        di = dna_index(o["integ"][o["idx"]], hi)
        e = best_split(o["integ"][o["idx"]], hi)[0]
        rows.append((frac, nsat, di, e))
        print("  %10.2f %12.2f %10.3f %10.4f" % (frac, nsat, di, e))
    print()
    print("  → 飽和画素が %.1f %% のところで DNA 指数は %.2f(真値 2.00)。"
          % (rows[-1][1], rows[-1][2]))
    print("     ★背景の引き忘れと**同じ向き**(指数が 2 より小さくなる)なので、")
    print("     2 つが同時に起きていると打ち消しでも足し算でもなく**見分けが付かない**。")
    print("     分けて数えるには飽和画素の割合を別に報告するしかない。")
    return rows


# --------------------------------------------------------------------------- #
# 6) 融合                                                                      #
# --------------------------------------------------------------------------- #
def section6_fusion():
    print()
    print("=" * 78)
    print("6) ★融合 —— 触れた 2n + 2n は 4n に見える")
    print("=" * 78)
    nu0 = make_nuclei(n=110, seed=11, sep=1.60)
    truth4 = float(np.mean(nu0["ploidy"] == 4))
    img0, at0 = render(nu0)
    lab0 = segment(img0)
    o0 = objects(img0, lab0, nu0, at0)
    thr = best_split(o0["integ"][o0["idx"]], o0["ploidy"] == 4)[1]
    print("  疎に撒いた版(間隔 1.60)で 3n 相当のしきい値を決める: %.0f。" % thr)
    print("  以後の密度ではこの 1 本をそのまま使う(実務でも較正は 1 回)。")
    print("  真値の 4n 割合 = %.3f。" % truth4)
    print()
    print("  %6s %6s %6s %10s %10s %10s %10s" %
          ("間隔", "塊", "融合", "4n 割合", "検出率", "誤検出", "除去後"))
    print("  " + "-" * 62)
    out = {}
    for sep in (1.60, 1.10, 0.90):
        nu = make_nuclei(n=110, seed=11, sep=sep)
        img, at = render(nu)
        lab = segment(img)
        o = objects(img, lab, nu, at)
        fused = np.array([len(o["members"][k]) > 1 for k in range(1, o["n"] + 1)])
        frac4 = float(np.mean(o["integ"] > thr))
        if fused.any():
            _, ts = best_split(-o["f"]["solidity"], fused)
            det = float(np.mean(-o["f"]["solidity"][fused] > ts))
            fpr = float(np.mean(-o["f"]["solidity"][~fused] > ts))
            keep = -o["f"]["solidity"] <= ts
            clean = float(np.mean(o["integ"][keep] > thr))
        else:
            det = fpr = float("nan")
            ts = float("nan")
            clean = frac4
        out[sep] = (o["n"], int(fused.sum()), frac4, det, fpr, clean, -ts)
        print("  %6.2f %6d %6d %10.3f %10.3f %10.3f %10.3f"
              % (sep, o["n"], fused.sum(), frac4, det, fpr, clean))
    s = 0.90
    print()
    print("  → 間隔 %.2f では %d 塊中 %d が融合し、4n の割合が真値 %.3f に対し"
          % (s, out[s][0], out[s][1], truth4))
    print("     **%.3f** になる。`solidity` の 1 本のしきい値(%.3f)で検出率 %.2f /"
          % (out[s][2], out[s][6], out[s][3]))
    print("     誤検出 %.3f、落としたあとは **%.3f**。" % (out[s][4], out[s][5]))
    print("  → ★ただし solidity が効くのは**核が凸に近い**からで、この合成では")
    print("     単独核にも ±10 % の半径変調を入れてある(入れないと solidity が")
    print("     ちょうど 1.000 になって、区別が不自然に簡単になる)。")
    print("  → ★★間隔 1.60 でも融合が %d 件ある。**「疎に撒いた」は「融合ゼロ」では"
          % out[1.60][1])
    print("     ない** —— 融合ゼロを仮定した較正はここで既に汚れている。")
    return out, truth4


# --------------------------------------------------------------------------- #
# 7) 混合比                                                                    #
# --------------------------------------------------------------------------- #
def _split_frac(v, how):
    """特徴量の列を 2 群に割って、上側の割合を返す。"""
    x = np.log(np.clip(np.asarray(v, float), 1e-12, None))
    x = (x - x.min()) / max(x.max() - x.min(), 1e-12)
    m = np.asarray(fs.apply(x.reshape(1, -1), how)) > 0.5
    return float(m.mean())


def section7_mixture():
    print()
    print("=" * 78)
    print("7) ★混合比の推定 —— ヒストグラムを 2 成分に割る")
    print("=" * 78)
    print("  割り方は fullseye の op で: `sk_otsu`(判別分析)と")
    print("  `sg_gmm_segment`(1 次元 2 成分ガウス混合の EM)。")
    print()
    print("  %8s %12s %12s %12s" % ("真の 4n 比", "積分 Otsu", "積分 EM", "面積 Otsu"))
    print("  " + "-" * 48)
    rows, dev_i, dev_a = [], [], []
    for frac in (0.05, 0.15, 0.30, 0.50, 0.70):
        nu = make_nuclei(seed=23, frac4=frac)
        img, at = render(nu)
        o = objects(img, segment(img), nu, at)
        iv = o["integ"][o["idx"]]
        av = o["f"]["area"][o["idx"]]
        truth = float(np.mean(o["ploidy"] == 4))
        e1 = _split_frac(iv, "sk_otsu")
        e2 = _split_frac(iv, "sg_gmm_segment")
        e3 = _split_frac(av, "sk_otsu")
        dev_i.append(max(abs(e1 - truth), abs(e2 - truth)))
        dev_a.append(abs(e3 - truth))
        rows.append(["%.2f" % truth, "%.3f" % e1, "%.3f" % e2, "%.3f" % e3])
        print("  %8.3f %12.3f %12.3f %12.3f" % (truth, e1, e2, e3))
    print()
    print("  → 積分輝度なら Otsu でも EM でも当たる(最大偏差 %.3f)。同じことを"
          % max(dev_i))
    print("     面積でやると最大 %.3f 外す —— **2 山が重なっているものは、"
          % max(dev_a))
    print("     どんな割り方をしても割れない**(割り方の問題ではない)。")
    figs.save_table("mixture",
                    ["真の 4n 比", "積分 Otsu", "積分 EM", "面積 Otsu"], rows,
                    title="混合比の推定(n=%d、5 通りの真値)" % N_NUC,
                    caption="特徴量が分かれてさえいれば割り方は選ばない。分かれていなければ何をしても割れない。")
    return max(dev_i), max(dev_a)


# --------------------------------------------------------------------------- #
# 8) 道具の穴                                                                  #
# --------------------------------------------------------------------------- #
def section8_gaps():
    print()
    print("=" * 78)
    print("8) 道具の穴 —— fullseye に無かったもの / 使いにくかったもの")
    print("=" * 78)
    print("""
  (a) ★★**`blob_features` は形しか測らない**。19 項目すべて幾何量で、
      **物体ごとの輝度の統計が 1 つも無い**(積分・平均・最大・中央値・分散)。
      定量顕微鏡で最初に欲しい量が `sum`(積分輝度)なのに、`ndimage.sum_labels`
      を自分で呼ぶしかない。3-D 側の `region_props` も同じで幾何量だけ。
      **「連結成分に切る」までは道具があり、「切った物体の明るさを測る」で
      道具が切れている** —— 2 節の主題そのものが道具の穴の上にある。

  (b) ★★**同じ計算が別の族に、円形開口専用で在る**。`fs.aperture_photometry`
      は「開口内の積分 - 環状背景の中央値」を副画素の重みつきでやる ——
      4 節が必要としたものそのもの。ところが**開口は円に限られ、ラベル画像を
      受け取れない**。星は点源なので円で足りるが、核・粒子・欠陥は形がある。
      `blob_photometry(image, labels, dilate=…, annulus=…)` があれば、
      astrostack の背景推定を blob 族に持ち込める。

  (c) ★**背景を引く口が「値」でしか無い**。4 節では `img - median(img[lab==0])`
      と書いた。傾いた背景(照明ムラ)なら平面を当てはめて引くのが定石だが、
      **マスクの外だけを使って背景を当てはめる op** が 3 層に無い
      (`running_gaussian_background` は動画の背景差分で別物)。

  (d) **飽和画素を数える口が無い**。5 節では `img >= sat` を自分で数えた。
      計測の前段で「この物体は飽和しているから値を信じるな」と印を付けるのは
      定型作業なので、`blob_features` に `n_saturated` があってよい。

  (e) `sk_otsu` / `sg_gmm_segment` は **1 次元の値の列にも使える**(この PoC は
      `(1, N)` に整形して 7 節で使った)。よく効くのに、**画像 op としてしか
      文書化されていない**ので「特徴量の 1 次元クラスタリング」に使えることが
      見えない。台帳に 1-D 版の別名があると探せる。
""")
    f = fs.ledger.blob_features(fs.ledger.blob_label(np.pad(np.ones((6, 6), bool), 3)))
    for k in ("sum", "mean_intensity", "integrated_intensity", "max_intensity",
              "n_saturated"):
        assert k not in f, "%s が生えた(良い変化。この節を書き換えること)" % k
    assert "area" in f and "solidity" in f
    import inspect
    sig = inspect.signature(fs.aperture_photometry).parameters
    assert "labels" not in sig and "r_aperture" in sig, \
        "aperture_photometry がラベルを受けるようになった(この節を書き換えること)"
    for name in ("blob_photometry", "blob_intensity", "background_from_mask"):
        assert not hasattr(fs, name) and not hasattr(fs.ledger, name), name


# --------------------------------------------------------------------------- #
def main():
    t0 = time.time()
    print("poc_nuclei_ploidy — 積分輝度のヒストグラムから倍数性を出す")
    print("(真値 = 核ごとの倍数性と DNA 量。∫I = D が厳密になるよう描いている)")
    print()
    nuc = make_nuclei()
    img, lab, o, tail, di0 = section1_check(nuc)
    sep2 = section2_zero_point(o)
    leak, leak_rows = section3_area_leak(nuc, o)
    unit, muls, curve = section4_background(nuc)
    sat_rows = section5_saturation(nuc)
    fus, truth4 = section6_fusion()
    dev_i, dev_a = section7_mixture()
    section8_gaps()

    hi = o["ploidy"] == 4
    over = fs.ledger.blob_overlay(np.clip(img / np.percentile(img, 99.7), 0, 1), lab)
    figs.save_grid("scene",
                   [img, np.asarray(over), (lab > 0).astype(float),
                    np.log(np.clip(img, 1e-3, None))],
                   ["蛍光核", "ラベル", "マスク", "log 輝度"],
                   title="場面(%d 核、4n が %.0f %%)" % (o["n"], 100 * hi.mean()),
                   ncols=2, caption="4 枚目は対数表示。裾がしきい値の外に出ているのが見える。")

    print()
    print("=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  ・マスク積分の裾落ち        %.1f %% → DNA 指数が既に %.3f(真値 2.00)"
          % (100 * (1 - tail), di0))
    print("  ・誤分類 面積(真値) %.3f / 面積(測定) %.3f / 積分輝度 %.3f"
          % (sep2["面積(真値)"][0], sep2["面積(測定)"][0], sep2["積分輝度(測定)"][0]))
    print("  ・分離度 面積 %.1f σ / 積分輝度 %.1f σ"
          % (sep2["面積(真値)"][1], sep2["積分輝度(測定)"][1]))
    print("  ・面積の漏れ 傾き %+.2f(PSF 0.6px)→ %+.2f(1.5px)" % (leak[0.2][0], leak[0.5][0]))
    print("  ・背景 5 倍で DNA 指数 %.3f(引けば %.3f / 環状背景 %.3f)"
          % (curve["raw"][-1], curve["sub"][-1], curve["ap"][-1]))
    print("  ・飽和 %.1f %% で DNA 指数 %.3f" % (sat_rows[-1][1], sat_rows[-1][2]))
    print("  ・融合 %d/%d で 4n 割合 %.3f(真値 %.3f)→ solidity で落として %.3f"
          % (fus[0.90][1], fus[0.90][0], fus[0.90][2], truth4, fus[0.90][5]))
    print("  ・混合比の最大偏差 積分 %.3f / 面積 %.3f" % (dev_i, dev_a))

    assert sep2["積分輝度(測定)"][0] < 0.02 < sep2["面積(真値)"][0]
    assert sep2["積分輝度(測定)"][1] > 3.0 * sep2["面積(真値)"][1]
    assert sep2["面積(測定)"][0] < sep2["面積(真値)"][0], sep2
    assert leak[0.5][0] > leak[0.2][0] > 0.15, leak
    assert leak[0.5][2] < leak[0.1][2], leak
    assert di0 > 2.05, di0                     # 裾落ちは比まで歪める(1 節)
    assert curve["raw"][-1] < 1.8 < curve["sub"][-1], curve
    assert abs(curve["sub"][-1] - curve["raw"][0]) < 1e-9, curve
    assert abs(curve["ap"][-1] - 2.0) < abs(curve["sub"][-1] - 2.0), curve
    assert sat_rows[-1][2] < 1.95, sat_rows
    assert fus[0.90][2] > truth4 + 0.06 and abs(fus[0.90][5] - truth4) < 0.06, fus
    assert dev_i < 0.06 < dev_a, (dev_i, dev_a)
    assert len(leak_rows) == 4

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\n経過 %.1f 秒" % (time.time() - t0))
    print("\nPASS")


if __name__ == "__main__":
    main()
