# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""蛍光の共局在は漏れ込みで嘘をつく —— Pearson と Manders は別の場所で、別の向きに壊れる。

2 色の蛍光顕微鏡画像から「タンパク質 A と B は同じ場所に居るか」を数える仕事です。
現場の指標は Pearson の相関係数 r と、Manders の重なり係数 M1 / M2(A の蛍光のうち
B の領域に入っている割合、とその逆)。ところが 2 つの蛍光色素のスペクトルは裾で
重なるので、A の光の一部が B のチャネルに写る(**漏れ込み / bleed-through**)。
それだけで「共局在している」画像ができ上がります。

EXTEND: 実写に差し替えるなら :func:`make_scene` が返す辞書の ``obs_a`` / ``obs_b`` を
2 チャネルの撮影画像に、``roi`` を細胞のマスクに置き換えます。真値(``m1_true`` 等)は
実写では手に入らないので、**単染色対照(A だけ・B だけを染めた試料)を同じ露光で
撮る**こと —— それが :func:`estimate_bleed` の入力です。単染色対照を撮らずに
「r が高いから共局在」と書くのが、この PoC が測っている失敗です。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **ゼロ点(生画像に Pearson と Otsu-Manders)**: 漏れ込み α=β=10 % で真の共局在
   0 % の r が 0.202(理想 0.000)、M1 が 0.190(真値 0.000)。25 / 50 / 100 % では
   r の誤差はもっと小さく、100 % では −0.006 —— **漏れ込みは「無関係」を「少し
   関係」に見せるが、「完全に一致」は壊さない**。
2. ★**単染色対照から漏れ込み行列を推定して線形分離(``mat_lstsq`` + ``mat_solve``)
   すると戻る**: α の推定 0.0988(真値 0.10)、β 0.0989。分離後の r は 0 % で
   0.006、M1 は 0.012 —— 4 つの真値すべてで |誤差| ≤ 0.02。
3. ★★**Costes のシャッフル検定は漏れ込みを見抜けない**。真の共局在 0 %・
   α=β=15 % の画像で r=0.284、ブロック並べ替え 200 回の p 値は 0.000
   (=「有意に共局在」)。検定が答えているのは「r は偶然か」であって
   「r は共局在か」ではない。分離後は r=0.006、p=0.415。
4. ★**崖(Pearson)は幾何で先に当たる**。A, B が無相関なら対称な漏れ込み
   α=β で ``r = 2α/(1+α²)``、r=0.5 は α=2−√3=0.268。実測の交点は 0.279
   (雑音が分母を太らせるぶん少し遅い)。**片側だけ(β=0)なら
   ``r = α/√(1+α²)`` で、30 % でも 0.287 —— 0.5 には届かない**。
   同じ「漏れ込み 30 %」でも対称か片側かで r は 2 倍違う。
5. ★★**Manders の崖は Pearson とは別の場所にある**。真の共局在 50 % で
   M1 が真値から +10 pt 外れるのは α=β=0.150 から、Pearson が理想から
   0.10 外れるのは 0.100 から。**向きも違う**: 漏れ込みは Pearson を
   上へ(0 % で +0.202)、Manders も上へ押すが、**ぼけは Pearson を動かさず
   Manders だけ上へ**押す(次項)。
6. ★**ぼけの崖は Manders に来る、Pearson には来ない**。真の共局在 0 % で PSF σ を
   0.5 → 4.0 px に振ると r は −0.001 → −0.004 のまま(独立な点過程はぼかしても
   無相関)。M1 は 0.001 → 0.362 —— 「近接」が Otsu の領域の重なりに化ける。
   予想は M1 ≈ B の Otsu 領域が ROI に占める面積率(偶然の重なり)で、実測との
   相関 0.997、σ=4 px で予想 0.339 / 実測 0.362。
7. **対照群で原因を分ける**(真の共局在 0 %): 漏れ込みだけ止めると r 0.202 → −0.001、
   ぼけだけ止めると 0.202 → 0.202、背景だけ止めると 0.202 → 0.202、雑音だけ
   止めると 0.202 → 0.219。**Pearson を作っているのは漏れ込み 1 つ**。
   Manders はぼけを止めると 0.190 → 0.094 に半減 —— 2 つの原因が乗っている。
8. ★**しきい値の流儀で M1 が動く**(真の共局在 50 %、α=β=10 %): Otsu 0.632 /
   固定(背景 + 3σ)0.784 / Costes 自動 0.669、真値 0.500。分離後は
   0.510 / 0.620 / 0.523 —— **固定しきい値は分離しても +12 pt 残る**
   (低いしきい値ほど「偶然の重なり」を拾う。原因は 6 項と同じ)。

【グラウンドトゥルース】
細胞体(閉形式の輪郭)の中に小胞状の点(Gaussian σ=1.2 px、振幅は対数正規)を
2 チャネルぶん撒く。B の点のうち ``rho`` の割合を A の点と**同じ位置・同じ振幅比**に
置き、残りは無関係な位置に置く。真の M1 / M2 は「同位置の点の蛍光の総和 ÷ 全体」
で閉形式に決まり、Pearson の理想値は漏れ込み・雑音の無い点画像から計算する。
観測 = 漏れ込み行列 [[1, α], [β, 1]] × 蛍光 → 細胞質の一様蛍光と背景を足す →
PSF(Gaussian)でぼかす → 光子雑音(Poisson、``photon_sample``)。

来歴(公開文献のみ): Manders, Verbeek, Aten, *J. Microscopy* 169 (1993) 375 ——
M1/M2 / Costes et al., *Biophys. J.* 86 (2004) 3993 —— 自動しきい値と
シャッフル検定 / Bolte & Cordelières, *J. Microscopy* 224 (2006) 213 ——
共局在解析の総説 / Dunn, Kamocka, McDonald, *Am. J. Physiol. Cell Physiol.* 300
(2011) C723 —— Pearson と Manders の使い分け。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 場面の諸元 -------------------------------------------------------------- #
N_PIX = 256            # 視野 [px]
N_VES = 120            # 小胞の数(チャネルごと)
SIG_VES = 1.2          # 小胞の固有の幅 σ [px]
AMP_SIG = 0.35         # 振幅の対数正規 σ
GAIN_B = 0.8           # 同位置の点の B/A 振幅比(化学量論を固定)
CYTO = 0.08            # 細胞質の一様蛍光(小胞のピーク = 1 に対して)
BG = 0.02              # 視野全体の背景
PSF_SIG = 1.0          # 既定の PSF σ [px]
PHOTONS = 300.0        # 小胞ピーク 1.0 あたりの光子数
ALPHA = 0.10           # 既定の漏れ込み B -> A チャネル
BETA = 0.10            # 既定の漏れ込み A -> B チャネル
SEED = 7
N_SHUFFLE = 200        # Costes 検定の並べ替え回数
BLOCK = 6              # 並べ替えのブロック辺長 [px](PSF より大きく)

_LAB = fs.ledger


# --------------------------------------------------------------------------- #
# 道具 —— fullseye の op で組む                                                  #
# --------------------------------------------------------------------------- #
def blur(img: np.ndarray, sigma: float) -> np.ndarray:
    """Gaussian ぼかし。``gauss_image`` は σ=0.3+2.7a なので 3 px を超えるときは
    2 回に分けて掛ける(σ² の加法性)。σ が 0.3 未満なら掛けない。"""
    if sigma < 0.3:
        return np.asarray(img, np.float64)
    if sigma <= 3.0:
        return np.asarray(fs.apply(img, "gauss_image", a=(sigma - 0.3) / 2.7))
    s = sigma / np.sqrt(2.0)
    return blur(blur(img, s), s)


def otsu_mask(img: np.ndarray) -> tuple[np.ndarray, float]:
    """``otsu`` op の前景マスクと、その画像単位でのしきい値。"""
    v = np.asarray(img, np.float64)
    v = np.clip(v, 0.0, None)
    top = float(v.max()) or 1.0
    m = np.asarray(fs.apply(v / top, "otsu")) > 0.5
    thr = float(v[m].min()) if m.any() else float("inf")
    return m, thr


def pearson(a: np.ndarray, b: np.ndarray, roi: np.ndarray) -> float:
    """ROI 内の Pearson r(``stat_correlation``)。"""
    x = np.stack([a[roi], b[roi]], axis=1)
    return float(_LAB.stat_correlation(x)[0, 1])


def manders(a: np.ndarray, b: np.ndarray, ma: np.ndarray, mb: np.ndarray,
            roi: np.ndarray) -> tuple[float, float]:
    """M1 = B の領域に入る A の蛍光の割合、M2 = その逆。

    蛍光は ROI の中央値(細胞質 + 背景)を引いて 0 で切る —— 引かないと
    細胞質の一様蛍光が分母を太らせて、点の共局在が薄まる。
    """
    aa = np.clip(a - np.median(a[roi]), 0.0, None)
    bb = np.clip(b - np.median(b[roi]), 0.0, None)
    m1 = float(aa[mb & roi].sum() / max(aa[roi].sum(), 1e-12))
    m2 = float(bb[ma & roi].sum() / max(bb[roi].sum(), 1e-12))
    return m1, m2


def fixed_mask(img: np.ndarray, roi: np.ndarray) -> tuple[np.ndarray, float]:
    """固定しきい値: ROI の中央値 + 3σ(σ は ``noise_sigma`` の MAD 推定)。

    σ は ROI の中で測る —— 視野全体に掛けると細胞の内外の 2 山が MAD に入って
    雑音の 3 倍以上に膨らむ(ROI の外は中央値で埋めて op に渡す)。
    """
    med = float(np.median(img[roi]))
    sig = float(_LAB.noise_sigma(np.where(roi, img, med), method="mad"))
    thr = med + 3.0 * sig
    return img > thr, thr


def costes_threshold(a: np.ndarray, b: np.ndarray, roi: np.ndarray,
                     n_levels: int = 120) -> tuple[np.ndarray, np.ndarray, float, float]:
    """Costes の自動しきい値: 回帰直線 b = s·a + o に沿って T_A を下げ、
    しきい値未満の画素の r が 0 以下になった所で止める(公開経路に無いので自前)。"""
    x, y = a[roi], b[roi]
    fit = _LAB.mat_lstsq(np.stack([x, np.ones_like(x)], 1), y)
    s, o = float(fit["x"][0]), float(fit["x"][1])
    ta_best, tb_best = float(x.max()), s * float(x.max()) + o
    for ta in np.linspace(x.max(), x.min(), n_levels)[1:]:
        tb = s * ta + o
        below = (x < ta) & (y < tb)
        if below.sum() < 20:
            break
        xb, yb = x[below], y[below]
        if xb.std() < 1e-12 or yb.std() < 1e-12:
            break
        r = float(np.corrcoef(xb, yb)[0, 1])
        if r <= 0.0:
            break
        ta_best, tb_best = float(ta), float(tb)
    return a > ta_best, b > tb_best


def costes_shuffle_p(a: np.ndarray, b: np.ndarray, roi: np.ndarray, rng,
                     n: int = N_SHUFFLE, block: int = BLOCK) -> tuple[float, float]:
    """B をブロック単位で並べ替えて r の帰無分布を作る。返り = (観測 r, p 値)。"""
    r_obs = pearson(a, b, roi)
    h, w = a.shape
    hb, wb = h // block, w // block
    bb = b[:hb * block, :wb * block].reshape(hb, block, wb, block).transpose(0, 2, 1, 3)
    bb = bb.reshape(hb * wb, block, block)
    ar = a[:hb * block, :wb * block]
    rr = roi[:hb * block, :wb * block]
    count = 0
    for _ in range(n):
        perm = rng.permutation(hb * wb)
        sh = bb[perm].reshape(hb, wb, block, block).transpose(0, 2, 1, 3).reshape(hb * block, wb * block)
        if pearson(ar, sh, rr) >= r_obs:
            count += 1
    return r_obs, count / n


# --------------------------------------------------------------------------- #
# 場面を作る —— 真値は「どの点が同位置か」                                      #
# --------------------------------------------------------------------------- #
def _cell_mask(n: int) -> np.ndarray:
    """閉形式の輪郭 r(θ) = R0 (1 + 0.15 sin 3θ + 0.10 cos 5θ) の細胞体。"""
    yy, xx = np.mgrid[0:n, 0:n]
    cy, cx = n / 2.0 + 6.0, n / 2.0 - 4.0
    dy, dx = yy - cy, xx - cx
    th = np.arctan2(dy, dx)
    r0 = 0.40 * n
    rad = r0 * (1.0 + 0.15 * np.sin(3.0 * th) + 0.10 * np.cos(5.0 * th))
    return (dy ** 2 + dx ** 2) <= rad ** 2


def _render_points(n: int, pos: np.ndarray, amp: np.ndarray) -> np.ndarray:
    """整数位置に振幅を置いて小胞の幅 σ=SIG_VES でぼかす(ピークが amp になるよう正規化)。"""
    img = np.zeros((n, n), np.float64)
    if pos.size:
        np.add.at(img, (pos[:, 0], pos[:, 1]), amp)
    img = blur(img, SIG_VES)
    return img * (2.0 * np.pi * SIG_VES ** 2)   # 単位振幅の Gaussian のピーク = 1


def make_scene(rho: float, alpha: float = ALPHA, beta: float = BETA,
               psf_sigma: float = PSF_SIG, photons: float | None = PHOTONS,
               seed: int = SEED, cyto: float = CYTO, bg: float = BG,
               only: str | None = None) -> dict:
    """2 チャネル場面。``rho`` = B の点のうち A と同位置の割合(真の共局在率)。

    ``only="A"`` / ``"B"`` は単染色対照(片方の蛍光体だけ)。``photons=None`` で
    雑音なし。返り値の ``m1_true`` / ``m2_true`` は点の蛍光だけで閉形式に決まる。
    """
    rng = np.random.default_rng(seed)
    n = N_PIX
    cell = _cell_mask(n)
    inner = np.asarray(fs.apply(cell.astype(np.float64), "reg_erode", a=0.3)) > 0.5
    cand = np.argwhere(inner)
    pa = cand[rng.choice(len(cand), N_VES, replace=False)]
    amp_a = np.exp(AMP_SIG * rng.standard_normal(N_VES))
    n_co = int(round(rho * N_VES))
    pb_alone = cand[rng.choice(len(cand), N_VES - n_co, replace=False)]
    amp_b_alone = np.exp(AMP_SIG * rng.standard_normal(N_VES - n_co))

    a_co = _render_points(n, pa[:n_co], amp_a[:n_co])
    a_alone = _render_points(n, pa[n_co:], amp_a[n_co:])
    b_co = a_co * GAIN_B                          # 同位置・同じ振幅比
    b_alone = _render_points(n, pb_alone, amp_b_alone)
    fa_pts, fb_pts = a_co + a_alone, b_co + b_alone
    fa = fa_pts + cyto * cell
    fb = fb_pts + cyto * cell
    if only == "A":
        fb = np.zeros_like(fb)
    elif only == "B":
        fa = np.zeros_like(fa)

    obs_a = fa + alpha * fb + bg
    obs_b = beta * fa + fb + bg
    obs_a, obs_b = blur(obs_a, psf_sigma), blur(obs_b, psf_sigma)
    if photons is not None:
        obs_a = _LAB.photon_sample(obs_a, photons_per_unit=photons, seed=int(seed)) / photons
        obs_b = _LAB.photon_sample(obs_b, photons_per_unit=photons, seed=int(seed) + 1) / photons

    ideal_a, ideal_b = blur(fa_pts, psf_sigma), blur(fb_pts, psf_sigma)
    tot_a, tot_b = fa_pts.sum(), fb_pts.sum()
    return {"obs_a": obs_a, "obs_b": obs_b, "roi": cell,
            "ideal_a": ideal_a, "ideal_b": ideal_b,
            "m1_true": float(a_co.sum() / tot_a) if tot_a > 0 else 0.0,
            "m2_true": float(b_co.sum() / tot_b) if tot_b > 0 else 0.0,
            "r_ideal": pearson(ideal_a, ideal_b, cell) if (tot_a > 0 and tot_b > 0) else 0.0,
            "amp_a": amp_a, "rho": rho, "alpha": alpha, "beta": beta}


def measure(obs_a: np.ndarray, obs_b: np.ndarray, roi: np.ndarray) -> dict:
    """生画像に Pearson と Otsu-Manders —— この PoC の**ゼロ点の推定器**。"""
    ma, ta = otsu_mask(obs_a)
    mb, tb = otsu_mask(obs_b)
    m1, m2 = manders(obs_a, obs_b, ma, mb, roi)
    return {"r": pearson(obs_a, obs_b, roi), "m1": m1, "m2": m2,
            "mask_a": ma, "mask_b": mb, "thr_a": ta, "thr_b": tb}


# --------------------------------------------------------------------------- #
# 漏れ込みの推定と線形分離                                                     #
# --------------------------------------------------------------------------- #
def estimate_bleed(alpha: float, beta: float, psf_sigma: float = PSF_SIG,
                   photons: float | None = PHOTONS, seed: int = SEED) -> tuple[float, float]:
    """単染色対照から α(B→A)と β(A→B)を推定する。

    A だけ染めた試料では ch B ≈ β · ch A(背景を引いた後)。明るい画素
    (Otsu 前景)で原点を通る最小二乗(``mat_lstsq``)—— 暗い画素は雑音だけ。
    """
    out = []
    for only, want in (("A", "beta"), ("B", "alpha")):
        sc = make_scene(0.0, alpha, beta, psf_sigma, photons, seed + 100, only=only)
        src, dst = (sc["obs_a"], sc["obs_b"]) if only == "A" else (sc["obs_b"], sc["obs_a"])
        roi = sc["roi"]
        s = src - np.median(src[~roi])
        d = dst - np.median(dst[~roi])
        m, _ = otsu_mask(src)
        fit = _LAB.mat_lstsq(s[m][:, None], d[m])
        out.append(float(fit["x"][0]))
    beta_est, alpha_est = out
    return alpha_est, beta_est


def unmix(obs_a: np.ndarray, obs_b: np.ndarray, roi: np.ndarray,
          alpha_est: float, beta_est: float) -> tuple[np.ndarray, np.ndarray]:
    """観測 = M · 蛍光 を画素ごとに解く(``mat_solve``、M = [[1, α], [β, 1]])。"""
    off_a, off_b = np.median(obs_a[~roi]), np.median(obs_b[~roi])
    rhs = np.stack([(obs_a - off_a).ravel(), (obs_b - off_b).ravel()], 0)
    sol = np.asarray(_LAB.mat_solve(np.array([[1.0, alpha_est], [beta_est, 1.0]]), rhs))
    return sol[0].reshape(obs_a.shape) + off_a, sol[1].reshape(obs_b.shape) + off_b


# --------------------------------------------------------------------------- #
# 1-2. ゼロ点と分離                                                             #
# --------------------------------------------------------------------------- #
def section_zero_point() -> dict:
    print("\n" + "=" * 78)
    print("1-2) ゼロ点(生画像)と、単染色対照からの線形分離")
    print("=" * 78)
    a_est, b_est = estimate_bleed(ALPHA, BETA)
    print("  単染色対照から: α 推定 %.4f(真値 %.2f) / β 推定 %.4f(真値 %.2f)"
          % (a_est, ALPHA, b_est, BETA))
    print("\n  真の共局在  |  r 理想   r 生    r 分離  |  M1 真  M1 生  M1 分離 |  M2 真  M2 生  M2 分離")
    rows, res = [], {}
    keep = None
    for rho in (0.0, 0.25, 0.5, 1.0):
        sc = make_scene(rho)
        raw = measure(sc["obs_a"], sc["obs_b"], sc["roi"])
        ua, ub = unmix(sc["obs_a"], sc["obs_b"], sc["roi"], a_est, b_est)
        cor = measure(ua, ub, sc["roi"])
        res[rho] = {"raw": raw, "cor": cor, "sc": sc}
        print("     %3.0f %%     |  %+.3f  %+.3f  %+.3f  |  %.3f  %.3f  %.3f  |  %.3f  %.3f  %.3f" % (
            100 * rho, sc["r_ideal"], raw["r"], cor["r"], sc["m1_true"], raw["m1"], cor["m1"],
            sc["m2_true"], raw["m2"], cor["m2"]))
        rows.append(["%.0f %%" % (100 * rho), "%+.3f" % sc["r_ideal"], "%+.3f" % raw["r"],
                     "%+.3f" % cor["r"], "%.3f" % sc["m1_true"], "%.3f" % raw["m1"],
                     "%.3f" % cor["m1"], "%.3f" % sc["m2_true"], "%.3f" % raw["m2"],
                     "%.3f" % cor["m2"]])
        if rho == 0.5:
            keep = (sc, ua, ub, raw, cor)
        if rho == 1.0:
            # ★裾落ちの予想: しきい値 T より下の Gaussian の裾は領域に入らない。
            #   ピーク p の点のうち領域内の蛍光は 1 − (T − 台)/p(2-D Gaussian の
            #   体積の閉形式)。台 = 細胞質 + 背景(+ 漏れ込みぶん)、p は PSF で
            #   σ_ves²/(σ_ves²+σ_psf²) 倍に潰れる。
            k = SIG_VES ** 2 / (SIG_VES ** 2 + PSF_SIG ** 2)
            base = float(np.median(sc["obs_b"][sc["roi"]]))
            peak_b = (GAIN_B + BETA) * sc["amp_a"] * k
            inside = np.clip(1.0 - (raw["thr_b"] - base) / peak_b, 0.0, 1.0)
            m1_pred_tail = float((sc["amp_a"] * inside).sum() / sc["amp_a"].sum())
            print("\n  ★100 %% でも M1 生は %.3f —— Otsu(T_B=%.3f、台 %.3f)より下の裾が領域から"
                  "落ちる。\n   閉形式の予想 Σ p·(1−(T−台)/p) / Σ p = %.3f(実測との差 %+.3f)。"
                  % (raw["m1"], raw["thr_b"], base, m1_pred_tail, raw["m1"] - m1_pred_tail))
            tail = (raw["m1"], m1_pred_tail)
    sc, ua, ub, raw, cor = keep
    figs.save_grid("scene_channels",
                   [sc["obs_a"], sc["obs_b"], sc["ideal_a"], sc["ideal_b"]],
                   ["観測 ch A(漏れ込み α=%.0f %%)" % (100 * ALPHA),
                    "観測 ch B(漏れ込み β=%.0f %%)" % (100 * BETA),
                    "真の A(点だけ、PSF 込み)", "真の B(同位置は %.0f %%)" % (100 * sc["rho"])],
                   title="2 色蛍光の場面(%d px 角、小胞 %d 個 × 2 色)" % (N_PIX, N_VES))
    figs.save_grid("scene_unmixed",
                   [sc["obs_a"], np.clip(ua, 0, None), sc["obs_b"], np.clip(ub, 0, None)],
                   ["観測 A: r=%.3f M1=%.3f" % (raw["r"], raw["m1"]),
                    "分離後 A: r=%.3f M1=%.3f" % (cor["r"], cor["m1"]),
                    "観測 B: M2=%.3f" % raw["m2"], "分離後 B: M2=%.3f" % cor["m2"]],
                   title="線形分離の前後(真の共局在 %.0f %%: M1 真値 %.3f)"
                         % (100 * sc["rho"], sc["m1_true"]))
    # 散布図(cytofluorogram): 漏れ込みが「腕」を作る
    rng = np.random.default_rng(SEED)
    roi = sc["roi"]
    idx = rng.choice(int(roi.sum()), 3000, replace=False)
    xa, xb = sc["obs_a"][roi][idx], sc["obs_b"][roi][idx]
    figs.save_plot("cytofluorogram",
                   [("観測(漏れ込みあり)", xa, xb),
                    ("分離後", ua[roi][idx], ub[roi][idx])],
                   xlabel="ch A の輝度 [小胞ピーク=1]", ylabel="ch B の輝度",
                   title="画素の散布図 —— 漏れ込みは軸から浮いた 2 本の腕になる",
                   kinds=["scatter", "scatter"])
    figs.save_table("zero_point",
                    ["真の共局在", "r 理想", "r 生", "r 分離", "M1 真", "M1 生", "M1 分離",
                     "M2 真", "M2 生", "M2 分離"], rows,
                    title="ゼロ点と分離後(α=β=%.0f %%、PSF σ=%.0f px)" % (100 * ALPHA, PSF_SIG))
    return {"alpha_est": a_est, "beta_est": b_est, "res": res, "tail": tail}


# --------------------------------------------------------------------------- #
# 3. Costes のシャッフル検定                                                    #
# --------------------------------------------------------------------------- #
def section_significance(est: tuple[float, float]) -> dict:
    print("\n" + "=" * 78)
    print("3) Costes のシャッフル検定 —— 「偶然でない」と「共局在」は別")
    print("=" * 78)
    rng = np.random.default_rng(SEED + 5)
    rows, out = [], {}
    cases = [("0 %, 漏れ込みなし", 0.0, 0.0), ("0 %, α=β=15 %", 0.0, 0.15),
             ("50 %, α=β=15 %", 0.5, 0.15)]
    for name, rho, ab in cases:
        sc = make_scene(rho, ab, ab)
        r_raw, p_raw = costes_shuffle_p(sc["obs_a"], sc["obs_b"], sc["roi"], rng)
        a_est, b_est = estimate_bleed(ab, ab)
        ua, ub = unmix(sc["obs_a"], sc["obs_b"], sc["roi"], a_est, b_est)
        r_cor, p_cor = costes_shuffle_p(ua, ub, sc["roi"], rng)
        print("   %-20s 生: r=%+.3f p=%.3f   分離後: r=%+.3f p=%.3f" % (
            name, r_raw, p_raw, r_cor, p_cor))
        rows.append([name, "%+.3f" % r_raw, "%.3f" % p_raw, "%+.3f" % r_cor, "%.3f" % p_cor])
        out[name] = (r_raw, p_raw, r_cor, p_cor)
    print("\n  ★漏れ込みだけの r は「有意」と出る。検定は r が偶然かを見ているだけで、"
          "\n   r の出どころ(共局在か漏れ込みか)は区別しない。")
    figs.save_table("costes_significance", ["条件", "r 生", "p 生", "r 分離", "p 分離"], rows,
                    title="ブロック並べ替え %d 回の p 値(%d px ブロック)" % (N_SHUFFLE, BLOCK))
    return out


# --------------------------------------------------------------------------- #
# 4-5. 漏れ込みを振る —— Pearson と Manders の崖は別の場所                       #
# --------------------------------------------------------------------------- #
def section_crosstalk_sweep() -> dict:
    print("\n" + "=" * 78)
    print("4-5) 漏れ込み α を 0 → 30 % に振る(対称 α=β と片側 β=0)")
    print("=" * 78)
    alphas = np.round(np.arange(0.0, 0.301, 0.025), 3)
    seeds = (SEED, SEED + 11)
    r0_sym, r0_one, r50, m1_50, m2_50 = [], [], [], [], []
    r50_cor, m1_50_cor = [], []
    r50_ideal = m1_50_true = None
    print("    α     r(0%,対称) 予想   r(0%,片側) 予想   r(50%)  M1(50%)  M2(50%) | 分離後 r  M1")
    for al in alphas:
        acc = {k: [] for k in ("r0s", "r0o", "r50", "m1", "m2", "r50c", "m1c")}
        for sd in seeds:
            s0 = make_scene(0.0, al, al, seed=sd)
            acc["r0s"].append(measure(s0["obs_a"], s0["obs_b"], s0["roi"])["r"])
            s1 = make_scene(0.0, al, 0.0, seed=sd)
            acc["r0o"].append(measure(s1["obs_a"], s1["obs_b"], s1["roi"])["r"])
            s5 = make_scene(0.5, al, al, seed=sd)
            mm = measure(s5["obs_a"], s5["obs_b"], s5["roi"])
            acc["r50"].append(mm["r"]); acc["m1"].append(mm["m1"]); acc["m2"].append(mm["m2"])
            ae, be = estimate_bleed(al, al, seed=sd)
            ua, ub = unmix(s5["obs_a"], s5["obs_b"], s5["roi"], ae, be)
            mc = measure(ua, ub, s5["roi"])
            acc["r50c"].append(mc["r"]); acc["m1c"].append(mc["m1"])
            if r50_ideal is None:
                r50_ideal, m1_50_true = s5["r_ideal"], s5["m1_true"]
        r0_sym.append(np.mean(acc["r0s"])); r0_one.append(np.mean(acc["r0o"]))
        r50.append(np.mean(acc["r50"])); m1_50.append(np.mean(acc["m1"])); m2_50.append(np.mean(acc["m2"]))
        r50_cor.append(np.mean(acc["r50c"])); m1_50_cor.append(np.mean(acc["m1c"]))
        p_sym, p_one = 2 * al / (1 + al ** 2), al / np.sqrt(1 + al ** 2)
        print("   %.3f    %+.3f    %+.3f    %+.3f    %+.3f    %+.3f   %.3f    %.3f  |  %+.3f  %.3f" % (
            al, r0_sym[-1], p_sym, r0_one[-1], p_one, r50[-1], m1_50[-1], m2_50[-1],
            r50_cor[-1], m1_50_cor[-1]))

    def crossing(x, y, level):
        y = np.asarray(y)
        for i in range(1, len(x)):
            if (y[i - 1] - level) * (y[i] - level) <= 0 and y[i] != y[i - 1]:
                return float(x[i - 1] + (level - y[i - 1]) * (x[i] - x[i - 1]) / (y[i] - y[i - 1]))
        return float("nan")

    a_pred = 2.0 - np.sqrt(3.0)
    a_cross = crossing(alphas, r0_sym, 0.5)
    # 崖は「漏れ込みなし(α=0)の同じ推定器」からの動きで測る。真値から測ると
    # Otsu-Manders の裾落ち(1 節)が最初から −14 pt 乗っていて、途中で漏れ込みと
    # 打ち消して「真値に近い」点ができる —— それは正確ではなく相殺。
    a_m1 = crossing(alphas, np.asarray(m1_50) - m1_50[0], 0.10)
    a_r50 = crossing(alphas, np.asarray(r50) - r50[0], 0.10)
    a_cancel = crossing(alphas, np.asarray(m1_50) - m1_50_true, 0.0)
    print("\n  ★Pearson の崖: 真の共局在 0 %% の r が 0.5 を超える α(対称)= %.3f、"
          "予想 2−√3 = %.3f" % (a_cross, a_pred))
    print("   片側(β=0)は 30 %% でも r=%+.3f(予想 %.3f)—— 0.5 に届かない。"
          % (r0_one[-1], 0.3 / np.sqrt(1.09)))
    print("  ★Manders の崖: 50 %% の M1 が漏れ込みなしの値 %.3f から +10 pt 動く α = %.3f / "
          "Pearson が漏れ込みなしの値 %.3f から +0.10 動く α = %.3f"
          % (m1_50[0], a_m1, r50[0], a_r50))
    print("   (漏れ込みなしの M1 %.3f は真値 %.3f より %+.1f pt 低い —— Otsu より下の裾を"
          "落とす分。1 節の予想と同じ原因)" % (m1_50[0], m1_50_true, 100 * (m1_50[0] - m1_50_true)))
    print("  ★★打ち消し: 生の M1 が真値 %.3f を横切るのは α=%.3f —— そこで「正確」に見えるのは"
          "\n   裾落ち(−)と漏れ込み(+)が釣り合っただけ。" % (m1_50_true, a_cancel))
    print("   分離後は α=30 %% でも r=%+.3f、M1=%.3f。" % (r50_cor[-1], m1_50_cor[-1]))

    x = list(alphas * 100)
    figs.save_plot("crosstalk_sweep_pearson",
                   [("真の共局在 0 %, 対称 α=β(実測)", x, r0_sym),
                    ("予想 2α/(1+α²)", x, [2 * a / (1 + a * a) for a in alphas]),
                    ("0 %, 片側 β=0(実測)", x, r0_one),
                    ("予想 α/√(1+α²)", x, [a / np.sqrt(1 + a * a) for a in alphas]),
                    ("r = 0.5", x, [0.5] * len(x))],
                   xlabel="漏れ込み α [%]", ylabel="Pearson r",
                   title="無関係な 2 色が漏れ込みだけで「相関」する(交点 α=%.1f %%)" % (100 * a_cross),
                   kinds=["scatter", "line", "scatter", "line", "line"])
    figs.save_plot("crosstalk_sweep_manders",
                   [("M1 生(Otsu)", x, m1_50), ("M2 生(Otsu)", x, m2_50),
                    ("M1 分離後", x, m1_50_cor),
                    ("真値 M1", x, [m1_50_true] * len(x))],
                   xlabel="漏れ込み α=β [%]", ylabel="Manders 係数",
                   title="真の共局在 50 %% の Manders(崖 α=%.1f %%、真値を横切る α=%.1f %%)"
                         % (100 * a_m1, 100 * a_cancel))
    return {"a_cross": a_cross, "a_pred": a_pred, "a_m1": a_m1, "a_r50": a_r50, "a_cancel": a_cancel,
            "r0_sym": r0_sym, "r0_one": r0_one, "m1_50": m1_50, "r50": r50,
            "r50_cor": r50_cor, "m1_50_cor": m1_50_cor, "m1_true": m1_50_true,
            "r50_ideal": r50_ideal}


# --------------------------------------------------------------------------- #
# 6. ぼけを振る —— 近接が Manders に化ける                                       #
# --------------------------------------------------------------------------- #
def section_psf_sweep() -> dict:
    print("\n" + "=" * 78)
    print("6) PSF σ を 0.5 → 4 px に振る(漏れ込みなし)")
    print("=" * 78)
    sigmas = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
    r0, m1_0, m1_pred, r50, m1_50, r0_nocyto, thr_b, peak_k = [], [], [], [], [], [], [], []
    print("    σ [px]  ピーク比 k   T_B    r(0%)  M1(0%)  偶然の重なり=B領域の面積率   r(50%)  M1(50%)   r(0%, 細胞質なし)")
    flip = float("nan")
    for sg in sigmas:
        s0 = make_scene(0.0, 0.0, 0.0, psf_sigma=sg)
        m0 = measure(s0["obs_a"], s0["obs_b"], s0["roi"])
        frac_b = float((m0["mask_b"] & s0["roi"]).sum() / s0["roi"].sum())
        s5 = make_scene(0.5, 0.0, 0.0, psf_sigma=sg)
        m5 = measure(s5["obs_a"], s5["obs_b"], s5["roi"])
        sn = make_scene(0.0, 0.0, 0.0, psf_sigma=sg, cyto=0.0)
        mn = measure(sn["obs_a"], sn["obs_b"], sn["roi"])
        k = SIG_VES ** 2 / (SIG_VES ** 2 + sg ** 2)     # PSF で潰れた後の小胞ピーク
        r0.append(m0["r"]); m1_0.append(m0["m1"]); m1_pred.append(frac_b)
        r50.append(m5["r"]); m1_50.append(m5["m1"]); r0_nocyto.append(mn["r"])
        thr_b.append(m0["thr_b"]); peak_k.append(k)
        if np.isnan(flip) and m0["thr_b"] < CYTO + BG:
            flip = sg
        print("    %.1f      %.3f     %.3f   %+.3f  %.3f          %.3f                  %+.3f   %.3f      %+.3f" % (
            sg, k, m0["thr_b"], m0["r"], m0["m1"], frac_b, m5["r"], m5["m1"], mn["r"]))
    cc = float(np.corrcoef(m1_0, m1_pred)[0, 1])
    print("\n  ★r はほとんど動かない(0 %%: %+.3f → %+.3f、細胞質なしなら %+.3f → %+.3f)。"
          "\n   M1 は %.3f → %.3f —— 「近接」が Otsu の領域の重なりに化ける。"
          "偶然の重なり(B 領域の面積率)との相関 %.3f。"
          % (r0[0], r0[-1], r0_nocyto[0], r0_nocyto[-1], m1_0[0], m1_0[-1], cc))
    print("  ★★崖は σ=%.1f px: Otsu のしきい値 T_B=%.3f が細胞質の台 %.2f を割り、前景が"
          "「小胞」から「細胞体」に飛び移る。\n   小胞のピークは PSF で k=%.3f 倍(σ=%.1f)"
          "→ %.3f 倍(σ=%.1f)に潰れ、細胞と外の 2 山の方が大きくなる。"
          % (flip, thr_b[sigmas.index(flip)] if not np.isnan(flip) else float("nan"),
             CYTO + BG, peak_k[sigmas.index(flip) - 1] if not np.isnan(flip) else float("nan"),
             sigmas[sigmas.index(flip) - 1] if not np.isnan(flip) else float("nan"),
             peak_k[sigmas.index(flip)] if not np.isnan(flip) else float("nan"), flip))
    figs.save_plot("psf_sweep",
                   [("M1(真の共局在 0 %)", sigmas, m1_0),
                    ("予想: B の Otsu 領域の面積率", sigmas, m1_pred),
                    ("Pearson r(0 %)", sigmas, r0),
                    ("M1(50 %、真値 0.5 付近)", sigmas, m1_50)],
                   xlabel="PSF σ [px]", ylabel="係数",
                   title="ぼけは Manders だけを押し上げる(Pearson は動かない)",
                   kinds=["scatter", "line", "scatter", "scatter"])
    s_big = make_scene(0.0, 0.0, 0.0, psf_sigma=4.0)
    mb = measure(s_big["obs_a"], s_big["obs_b"], s_big["roi"])
    s_small = make_scene(0.0, 0.0, 0.0, psf_sigma=0.5)
    ms = measure(s_small["obs_a"], s_small["obs_b"], s_small["roi"])
    figs.save_grid("psf_masks",
                   [s_small["obs_b"], (ms["mask_a"] & ms["mask_b"]).astype(np.float64),
                    s_big["obs_b"], (mb["mask_a"] & mb["mask_b"]).astype(np.float64)],
                   ["σ=0.5 px の ch B", "A∩B の Otsu 領域(M1=%.3f)" % ms["m1"],
                    "σ=4.0 px の ch B", "A∩B の Otsu 領域(M1=%.3f)" % mb["m1"]],
                   title="真の共局在 0 % でも、ぼけると領域が重なる")
    return {"sigmas": sigmas, "r0": r0, "m1_0": m1_0, "m1_pred": m1_pred, "cc": cc,
            "r0_nocyto": r0_nocyto, "flip": flip, "thr_b": thr_b}


# --------------------------------------------------------------------------- #
# 7. 対照群 —— 要因を 1 つずつ止める                                            #
# --------------------------------------------------------------------------- #
def section_controls() -> dict:
    print("\n" + "=" * 78)
    print("7) 対照群 —— 漏れ込み / ぼけ / 背景 / 雑音を 1 つずつ止める")
    print("=" * 78)
    conds = [("全部あり", {}), ("漏れ込みなし", {"alpha": 0.0, "beta": 0.0}),
             ("ぼけなし", {"psf_sigma": 0.0}), ("背景なし", {"cyto": 0.0, "bg": 0.0}),
             ("雑音なし", {"photons": None})]
    rows, out = [], {}
    print("    条件            | 0 %: r      M1     M2   | 50 %: r     M1     M2")
    for name, kw in conds:
        vals = []
        for rho in (0.0, 0.5):
            sc = make_scene(rho, **kw)
            m = measure(sc["obs_a"], sc["obs_b"], sc["roi"])
            vals += [m["r"], m["m1"], m["m2"]]
        out[name] = vals
        print("    %-14s  | %+.3f  %.3f  %.3f  |  %+.3f  %.3f  %.3f" % (name, *vals))
        rows.append([name] + ["%+.3f" % vals[0], "%.3f" % vals[1], "%.3f" % vals[2],
                              "%+.3f" % vals[3], "%.3f" % vals[4], "%.3f" % vals[5]])
    print("\n  ★0 %% の Pearson を作っているのは漏れ込みだけ(止めると %+.3f → %+.3f)。"
          % (out["全部あり"][0], out["漏れ込みなし"][0]))
    print("   Manders(0 %%)は漏れ込みを止めて %.3f、ぼけを止めて %.3f —— 2 つの原因が乗る。"
          % (out["漏れ込みなし"][1], out["ぼけなし"][1]))
    figs.save_table("controls", ["条件", "r (0%)", "M1 (0%)", "M2 (0%)", "r (50%)", "M1 (50%)", "M2 (50%)"],
                    rows, title="対照群(真の共局在 0 % と 50 %)")
    return out


# --------------------------------------------------------------------------- #
# 8. しきい値の流儀                                                              #
# --------------------------------------------------------------------------- #
def section_thresholds(est: tuple[float, float]) -> dict:
    print("\n" + "=" * 78)
    print("8) しきい値の流儀で M1 / M2 が動く(真の共局在 50 %%、α=β=%.0f %%)" % (100 * ALPHA))
    print("=" * 78)
    sc = make_scene(0.5)
    roi = sc["roi"]
    ua, ub = unmix(sc["obs_a"], sc["obs_b"], roi, *est)
    rows, out = [], {}
    print("    流儀             | 生: M1     M2    | 分離後: M1     M2    | 真値 M1 %.3f M2 %.3f"
          % (sc["m1_true"], sc["m2_true"]))
    for name in ("Otsu", "固定(背景+3σ)", "Costes 自動"):
        vals = []
        for a, b in ((sc["obs_a"], sc["obs_b"]), (ua, ub)):
            if name == "Otsu":
                ma, mb = otsu_mask(a)[0], otsu_mask(b)[0]
            elif name.startswith("固定"):
                ma, mb = fixed_mask(a, roi), fixed_mask(b, roi)
            else:
                ma, mb = costes_threshold(a, b, roi)
            vals += list(manders(a, b, ma, mb, roi))
        out[name] = vals
        print("    %-16s | %.3f  %.3f  |  %.3f  %.3f" % (name, *vals))
        rows.append([name, "%.3f" % vals[0], "%.3f" % vals[1], "%.3f" % vals[2], "%.3f" % vals[3]])
    rows.append(["真値", "%.3f" % sc["m1_true"], "%.3f" % sc["m2_true"], "-", "-"])
    figs.save_table("threshold_table", ["しきい値", "M1 生", "M2 生", "M1 分離", "M2 分離"], rows,
                    title="しきい値の流儀と Manders(真の共局在 50 %)")
    return {"rows": out, "m1_true": sc["m1_true"]}


# --------------------------------------------------------------------------- #
# 9. 道具の穴                                                                    #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("9) 道具の穴(公開経路に無かった処理)")
    print("=" * 78)
    for name in ("manders", "costes_threshold", "colocalization", "block_shuffle", "unmix"):
        assert not fs.op_find(name), name
    print("  (a) Manders 係数 / Costes 自動しきい値 / ブロック並べ替え検定は公開経路に無い"
          "(この PoC は自前)。stat_correlation・mat_lstsq・mat_solve・otsu・gauss_image・"
          "photon_sample・noise_sigma で残りは組めた。")
    print("  (b) 線形分離(スペクトル unmixing)の専用 op も無い —— mat_solve で 2×2 は足りるが、"
          "3 色以上・非負制約(NNLS)は自前になる。")
    print("  (c) gauss_image の σ は 0.3〜3.0 px に閉じているので、4 px の PSF は 2 回掛けで作った。")


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.perf_counter()
    print("=" * 78)
    print("蛍光の共局在は漏れ込みで嘘をつく —— Pearson と Manders は別の場所で壊れる")
    print("視野 %d px 角 / 小胞 %d 個 × 2 色 / PSF σ=%.1f px / 小胞ピーク %.0f 光子" % (
        N_PIX, N_VES, PSF_SIG, PHOTONS))
    print("=" * 78)

    z = section_zero_point()
    est = (z["alpha_est"], z["beta_est"])
    sig = section_significance(est)
    sw = section_crosstalk_sweep()
    ps = section_psf_sweep()
    ct = section_controls()
    th = section_thresholds(est)
    section_tool_gaps()

    # --- 所見を固定する(壊れたら鳴る) --------------------------------------- #
    r0_raw = z["res"][0.0]["raw"]["r"]
    r0_cor = z["res"][0.0]["cor"]["r"]
    assert r0_raw > 0.15, r0_raw                       # 漏れ込みだけで r が浮く
    assert abs(r0_cor) < 0.03, r0_cor                  # 分離で戻る
    assert abs(est[0] - ALPHA) < 0.01 and abs(est[1] - BETA) < 0.01, est
    assert sig["0 %, α=β=15 %"][1] < 0.01, sig         # 漏れ込みが「有意」
    assert sig["0 %, α=β=15 %"][3] > 0.05, sig         # 分離後は有意でない
    assert abs(sw["a_cross"] - sw["a_pred"]) < 0.04, (sw["a_cross"], sw["a_pred"])
    assert sw["r0_one"][-1] < 0.5, sw["r0_one"][-1]
    assert sw["a_m1"] > sw["a_r50"], (sw["a_m1"], sw["a_r50"])   # 崖の場所が違う
    assert abs(ps["r0"][-1]) < 0.05 and ps["m1_0"][-1] > 0.25, (ps["r0"][-1], ps["m1_0"][-1])
    assert ps["cc"] > 0.95, ps["cc"]
    assert abs(ct["漏れ込みなし"][0]) < 0.03, ct["漏れ込みなし"][0]

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * 漏れ込み %.0f %% で無関係な 2 色の r が %+.3f、Otsu-Manders M1 が %.3f。"
          "単染色対照から分離すると %+.3f / %.3f。" % (
              100 * ALPHA, r0_raw, z["res"][0.0]["raw"]["m1"], r0_cor, z["res"][0.0]["cor"]["m1"]))
    print("  * Pearson の崖は α=%.3f(予想 %.3f)、Manders の崖は α=%.3f —— 別の場所。"
          % (sw["a_cross"], sw["a_pred"], sw["a_m1"]))
    print("  * Otsu-Manders は 100 %% でも %.3f(裾落ち、予想 %.3f)。真値に一致する α=%.3f は相殺。"
          % (z["tail"][0], z["tail"][1], sw["a_cancel"]))
    print("  * ぼけは Manders だけを押す(σ=4 px で M1 %.3f、r %+.3f)。" % (ps["m1_0"][-1], ps["r0"][-1]))
    print("  * シャッフル検定は漏れ込みを「有意」と言う(p=%.3f)。" % sig["0 %, α=β=15 %"][1])
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
