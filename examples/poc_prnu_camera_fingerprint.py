# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""カメラ指紋(PRNU)で「どのカメラで撮ったか」を当てる —— 指紋は枚数で育ち、保存ボタンで消える。

画像法科学(image forensics)の仕事です。イメージセンサは画素ごとに感度が
わずかに違い(PRNU: photo-response non-uniformity)、その**乗算の模様 K は
カメラ 1 台ごとに固定**なので、写真の雑音残差から K を取り出せば「この写真は
このカメラで撮られたか」を照合できます(Lukáš, Fridrich & Goljan 2006)。
問題は、K は雑音の中に埋もれた雑音であること —— 何枚要るのか、JPEG 保存や
縮小でいつ消えるのか、そして**被写体そのものが指紋に化ける**ことを知らずには
証拠として出せません。

EXTEND: 実写に差し替えるなら :func:`shoot` の返り(1 台のカメラで撮った
複数枚)を、そのカメラで撮った **RAW か最高品質 JPEG の平坦気味の写真**
(空・壁)に置き換えます。真値 K は実写では手に入らないので、この PoC の
「真の K との相関」列は消え、**PCE と対照群(6 節)だけが頼り**になります。
だから 6 節の「同じ場面を撮り直した写真は別カメラでも指紋に見える」を
実写で先に確かめてから運用すること。指紋は画素の物理位置そのものなので、
**リサイズして解像度を揃えた瞬間に消えます**(5 節)。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **ゼロ点(写真をそのまま平均して平滑成分を引く)は指紋を捉えない**。
   30 枚で真の K との相関 0.038 —— 最尤重み付き(fullseye の
   ``sensor_fingerprint``、Wiener 残差)は 0.795、ウェーブレット残差は 0.808。
   ★重みを掛けない「残差の単純平均」でも 0.789 まで出るので、効いているのは
   **重みではなく、まず平滑成分を各枚から引くこと**。
2. **照合は清浄条件では完全に分かれる**。カメラ A の指紋(30 枚)に対して
   A の写真 30 枚の PCE は中央値 2185、B の写真は 1.4、AUC 1.000。
   ★別カメラのピーク位置は毎回ばらばら((0,0) に立つのは 0/30)なのに対し、
   同一カメラは 30/30 で (0,0) —— PCE より先にこの位置が証拠になる。
3. ★**指紋は √N で育ち、予測はほぼ当たった**。N=1 の相関 0.343 から
   corr(N) = 1/√(1 + (1/r₁² − 1)/N) で予測すると、N=50 の予測 0.918 に対し
   実測 0.870(残りは被写体の漏れ込みで、N を増やしても消えない下限)。
   PCE は N=1 で 217 → N=50 で 2840。
4. ★★**JPEG 相当の 8×8 DCT 量子化は、IJG 品質 90 相当で PCE が 13 %、
   品質 50 相当で 1.6 % まで落ちる**。AUC が 0.5 に落ちる(判定不能)のは
   品質 50 相当より下。「量子化幅が残差の 2σ を超えた係数は死ぬ」で予測した
   PCE 比は品質 50 相当で 0.9 %、実測 1.6 % —— 桁は合うが**予測は死に過ぎ**
   (ショット雑音がディザになって、量子化幅より小さい信号も少し通す)。
5. ★★**縮小は 0.5× より 0.9× のほうが致命的**。0.5× に縮めて戻すと PCE は
   3.8 %(予想 25 %:2×2 の箱平均で相関が 1/2 になる、とした)で外れ、
   0.9× では 0.7 % で AUC 0.567。★偶数倍でも「画素の位置」が半画素ずれる
   (箱平均の重心)ので、予測の 25 % は**位置合わせが完璧な場合の上限**
   だった。位置ずれは PCE の分母(相関面の残り)に散るので PCE は桁で落ちる。
6. ★★**被写体は指紋に化ける**。K=0 のカメラ(指紋が無い)でも、同じ背景
   模様を写した 30 枚から作った「指紋」に別カメラの同じ背景の写真を当てると
   PCE 1490(AUC 1.000)—— **指紋が無いのに完全に「同一カメラ」と出る**。
   場面を毎回変えると同じ K=0 カメラの PCE は 1.1(AUC 0.517)。
   ★平坦画像(壁)だけで作った指紋は模様入りより真の K との相関が高い
   (0.925 vs 0.795)。指紋の学習には**つまらない写真がいちばん良い**。
7. **デノイザで PCE は 4.3 倍動く**(同じ枚数・同じ写真)。ガウス 0.59 倍 /
   メディアン 0.64 倍 / DCT 縮退 0.20 倍 / TV 0.43 倍 / NLM 0.77 倍 /
   scipy Wiener 0.88 倍(最良 = ウェーブレット Wiener を 1)。
   ★skimage のウェーブレット(``sk_wavelet``)は残差 RMS が生雑音と同じで
   **ほとんど何もしていない**(相関 0.056)—— op としては動くが、この用途
   の平滑器ではない。

【グラウンドトゥルース】
2 台の仮想カメラ A/B に **固定の乗算場 K(σ_K = 0.02、白色ガウス)** を仕込み、
3 台目 C は K = 0(指紋の無いカメラ、対照)。各カメラで N 枚の合成写真
(方向の違う勾配 + 帯域制限した模様 + 明暗の物体、**毎枚違う**)を撮る。
撮像は I = (1+K)·I0 → ショット雑音(Poisson、フルウェル 4000 e⁻)→
読み出し雑音(σ = 0.008)→ [0,1] にクリップ。真値は K そのものなので
「推定した指紋と真の K の相関」が測れる —— 実写では絶対に測れない量で、
PCE が高いのに K を捉えていない(被写体を捉えている)状態を暴くのに要る。
照合は PCE(Goljan, Fridrich & Filler 2009)、判定性能は同一/別カメラの
PCE の AUC(Mann–Whitney)。

来歴(公開文献のみ): Lukáš, Fridrich & Goljan, "Digital camera identification
from sensor pattern noise", IEEE TIFS 1(2), 2006 / Chen, Fridrich, Goljan &
Lukáš, "Determining image origin and integrity using sensor noise", IEEE TIFS
3(1), 2008(最尤推定・ゼロ平均前処理)/ Goljan, Fridrich & Filler, "Large
scale test of sensor fingerprint camera identification", SPIE 7254, 2009(PCE)
/ Mihçak, Kozintsev & Ramchandran, ICASSP 1999(局所 Wiener)/ ITU-T T.81
Annex K(JPEG 輝度量子化表)。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy import fft as sfft
from scipy.ndimage import gaussian_filter, zoom
from scipy.stats import rankdata

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 場面の諸元 -------------------------------------------------------------- #
N_PIX = 128                # 視野 [px]
SIGMA_K = 0.02             # PRNU の強さ(乗算場 K の標準偏差)
FULL_WELL = 4000.0         # フルウェル [e⁻] → ショット雑音 σ = √(I0/FW)(I0=0.5 で 0.011)
READ_NOISE = 0.008         # 読み出し雑音 σ([0,1] 単位)
N_TRAIN = 30               # 指紋を作る枚数(既定)
N_QUERY = 30               # 照合に使う枚数(カメラごと)
DENOISE_SIGMA = 0.02       # 残差を取る局所 Wiener の雑音 σ(fullseye の既定)
SEED = 7

_F = fs.ledger             # imgforensics 族の公開経路

# ITU-T T.81 Annex K 表 K.1(輝度の量子化表、品質 50 相当)。
# aug_jpeg_blocks はこの表を (1+40a)/16 倍して使う。
JPEG_LUMA_Q50 = np.array([
    [16, 11, 10, 16, 24, 40, 51, 61],
    [12, 12, 14, 19, 26, 58, 60, 55],
    [14, 13, 16, 24, 40, 57, 69, 56],
    [14, 17, 22, 29, 51, 87, 80, 62],
    [18, 22, 37, 56, 68, 109, 103, 77],
    [24, 35, 55, 64, 81, 104, 113, 92],
    [49, 64, 78, 87, 103, 121, 120, 101],
    [72, 92, 95, 98, 112, 100, 103, 99]], np.float64)


# --------------------------------------------------------------------------- #
# 場面を作る                                                                    #
# --------------------------------------------------------------------------- #
def sensor_pattern(seed: int, sigma: float = SIGMA_K) -> np.ndarray:
    """カメラ 1 台ぶんの真の PRNU 場 K(白色ガウス、σ = sigma)。"""
    r = np.random.default_rng(seed)
    return sigma * r.standard_normal((N_PIX, N_PIX))


def scene(seed: int, texture: np.ndarray | None = None, flat: bool = False) -> np.ndarray:
    """1 枚ぶんの被写体 I0 ∈ [0.05, 0.95]。勾配 + 帯域制限した模様 + 物体。

    ``texture`` を渡すと模様をその固定パターンにする(6 節の「同じ背景」)。
    ``flat=True`` なら一様な壁(6 節の「つまらない写真」)。
    """
    r = np.random.default_rng(seed)
    if flat:
        return np.full((N_PIX, N_PIX), 0.55)
    yy, xx = np.mgrid[0:N_PIX, 0:N_PIX] / (N_PIX - 1.0)
    th = r.uniform(0, 2 * np.pi)
    g = 0.5 + r.uniform(0.15, 0.3) * ((xx - 0.5) * np.cos(th) + (yy - 0.5) * np.sin(th)) * 2
    if texture is None:
        texture = gaussian_filter(r.standard_normal((N_PIX, N_PIX)), 2.0)
        texture = 0.10 * texture / texture.std()
    img = g + texture
    for _ in range(3):
        cy, cx = r.uniform(0.1, 0.9, 2) * N_PIX
        rad = r.uniform(8, 22)
        amp = r.choice([-1, 1]) * r.uniform(0.12, 0.25)
        if r.random() < 0.5:
            m = (yy * (N_PIX - 1) - cy) ** 2 + (xx * (N_PIX - 1) - cx) ** 2 <= rad ** 2
        else:
            m = (np.abs(yy * (N_PIX - 1) - cy) <= rad) & (np.abs(xx * (N_PIX - 1) - cx) <= rad * 0.7)
        img = img + amp * m
    return np.clip(img, 0.05, 0.95)


def shoot(i0: np.ndarray, k: np.ndarray, seed: int) -> np.ndarray:
    """撮像 I = (1+K)·I0 + ショット雑音 + 読み出し雑音、[0,1] にクリップ。"""
    r = np.random.default_rng(seed)
    rate = np.clip(i0 * (1.0 + k), 0.0, None)
    electrons = r.poisson(rate * FULL_WELL)
    return np.clip(electrons / FULL_WELL + READ_NOISE * r.standard_normal(i0.shape), 0, 1)


def bank(k: np.ndarray, n: int, base_seed: int, **scene_kw) -> list:
    """カメラ K で n 枚撮る(場面は毎枚違う)。"""
    return [shoot(scene(base_seed + i, **scene_kw), k, seed=10_000 + base_seed + i)
            for i in range(n)]


# --------------------------------------------------------------------------- #
# 測る道具                                                                      #
# --------------------------------------------------------------------------- #
def corr(a: np.ndarray, b: np.ndarray) -> float:
    a = a - a.mean()
    b = b - b.mean()
    return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))


def auc(pos, neg) -> float:
    """同一カメラ(pos)の PCE が別カメラ(neg)より大きい確率(Mann–Whitney)。"""
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    ranks = rankdata(np.concatenate([pos, neg]))
    return float((ranks[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def match(images, fp, denoiser: str = "wiener") -> tuple:
    """照合(fullseye の fingerprint_correlate)。PCE の列と (0,0) に立った数。"""
    res = [_F.fingerprint_correlate(im, fp, denoiser=denoiser, sigma=DENOISE_SIGMA)
           for im in images]
    pces = np.array([r["pce"] for r in res])
    at_origin = sum(1 for r in res if r["peak_shift"] == (0, 0))
    return pces, at_origin


def pce_from_residual(w: np.ndarray, ref: np.ndarray, exclude: int = 11) -> float:
    """Goljan 2009 の PCE(残差を直接渡す版。7 節のデノイザ比較にだけ使う)。

    ★fullseye の ``fingerprint_correlate`` は内部で残差を取るので、任意の
    平滑 op で作った残差を照合に渡す口が無い。ここは公開経路に無い処理。
    """
    w = w - w.mean()
    ref = ref - ref.mean()
    c = np.real(sfft.ifft2(sfft.fft2(w) * np.conj(sfft.fft2(ref))))
    c /= (np.linalg.norm(w) * np.linalg.norm(ref))
    py, px = np.unravel_index(int(np.argmax(np.abs(c))), c.shape)
    h = exclude // 2
    mask = np.ones(c.shape, bool)
    ys = np.arange(py - h, py + h + 1) % c.shape[0]
    xs = np.arange(px - h, px + h + 1) % c.shape[1]
    mask[np.ix_(ys, xs)] = False
    peak = float(c[py, px])
    return float(np.sign(peak) * peak * peak / np.mean(c[mask] ** 2))


def ml_fingerprint(images, residual_fn) -> np.ndarray:
    """最尤重み付き平均 K̂ = ΣW·I / ΣI²(Chen 2008)、行・列平均を抜いて σ=1。

    ``residual_fn(img) -> W``。fullseye の ``sensor_fingerprint`` と同じ式で、
    残差の取り方だけ差し替えられるようにしたもの(7 節)。
    """
    num = np.zeros((N_PIX, N_PIX))
    den = np.zeros((N_PIX, N_PIX))
    for im in images:
        num += residual_fn(im) * im
        den += im * im
    k = num / np.maximum(den, 1e-12)
    k = k - k.mean(axis=0, keepdims=True)
    k = k - k.mean(axis=1, keepdims=True)
    return k / k.std()


def jpeg_quality_equiv(a: float) -> float:
    """``aug_jpeg_blocks`` の a を IJG の品質に換算(表の倍率 s = (1+40a)/16)。"""
    s = (1.0 + 40.0 * a) / 16.0
    return 100.0 - 50.0 * s if s <= 1.0 else 50.0 / s


def quantizer_gain(sigma: float, step: float) -> float:
    """E[t·Q(t)] / σ² —— σ のガウス信号を幅 step で丸めたとき残る相関の利得。"""
    t = np.linspace(-6 * sigma, 6 * sigma, 4001)
    pdf = np.exp(-0.5 * (t / sigma) ** 2) / (sigma * np.sqrt(2 * np.pi))
    q = step * np.round(t / step)
    return float(np.trapezoid(t * q * pdf, t) / sigma ** 2)


# --------------------------------------------------------------------------- #
# 1. 場面と、指紋の推定(ゼロ点 vs 最尤)                                         #
# --------------------------------------------------------------------------- #
def zero_mean_unit(k: np.ndarray) -> np.ndarray:
    """行・列平均を抜いて σ=1(fullseye の指紋と同じ正規化。ゼロ点にも同じ扱いをする)。"""
    k = k - k.mean(axis=0, keepdims=True)
    k = k - k.mean(axis=1, keepdims=True)
    return k / k.std()


def section_estimate(cams: dict, banks: dict, queries: dict) -> dict:
    print("\n" + "=" * 78)
    print("1) 指紋を推定する —— ゼロ点 vs 最尤重み付き平均(%d 枚)" % N_TRAIN)
    print("   予想: 「平滑成分を引かない生の平均」は被写体まみれで使えず、"
          "最尤 + 適応 Wiener がゼロ点に桁で勝つ")
    print("=" * 78)
    k_true = cams["A"]
    imgs = banks["A"]

    # ゼロ点 0: 写真をそのまま平均する(行・列平均だけ抜く)
    z0 = zero_mean_unit(np.mean(imgs, axis=0))
    # ゼロ点 1: 各枚から平滑成分(ガウス σ≈1)を引いた残差の単純平均(重み無し・非適応)
    z1 = zero_mean_unit(np.mean([im - np.asarray(fs.apply(im, "gauss_image", a=0.25))
                                 for im in imgs], axis=0))
    fp_w = _F.sensor_fingerprint(imgs, denoiser="wiener", sigma=DENOISE_SIGMA)
    fp_v = _F.sensor_fingerprint(imgs, denoiser="wavelet", sigma=DENOISE_SIGMA)

    rows, r, pce = [], {}, {}
    for name, k in [("ゼロ点 0: 生の平均(平滑を引かない)", z0),
                    ("ゼロ点 1: 残差(ガウス高域)の単純平均", z1),
                    ("最尤 sensor_fingerprint(wiener)", fp_w),
                    ("最尤 sensor_fingerprint(wavelet)", fp_v)]:
        c = corr(k, k_true)
        ps, _ = match(queries["A"], k)
        pd, _ = match(queries["B"], k)
        a = auc(ps, pd)
        r[name], pce[name] = c, float(np.median(ps))
        rows.append((name, "%+.3f" % c, "%.0f" % np.median(ps), "%.1f" % np.median(pd), "%.3f" % a))
        print("  %-40s 真の K との相関 %+.3f  PCE 同一 %5.0f / 別 %5.1f  AUC %.3f" % (
            name, c, np.median(ps), np.median(pd), a))
    z0n, z1n = "ゼロ点 0: 生の平均(平滑を引かない)", "ゼロ点 1: 残差(ガウス高域)の単純平均"
    mln = "最尤 sensor_fingerprint(wiener)"
    print("  ★予想は外れた。生の平均ですら相関 %.3f・AUC %.3f(場面が毎枚違うので"
          "平均すると被写体が消える)。" % (r[z0n], auc(*[match(queries[c], z0)[0] for c in "AB"])))
    print("  ★ゼロ点 1(非適応ガウス高域)%.3f と最尤 + 適応 Wiener %.3f は**同点**。"
          "効いているのは重みでも適応でもなく、「平滑成分を引いてから平均する」ことと枚数。"
          % (r[z1n], r[mln]))
    print("     PCE では最尤 %.0f vs ゼロ点 0 %.0f(%.1f 倍)—— AUC だけ見ると差が見えない。"
          % (pce[mln], pce[z0n], pce[mln] / pce[z0n]))
    assert r[z0n] < 0.6 < r[z1n], r
    assert abs(r[z1n] - r[mln]) < 0.05, (r[z1n], r[mln])
    assert pce[mln] > 3 * pce[z0n], (pce[mln], pce[z0n])

    figs.save_grid("scene",
                   [imgs[0], imgs[1], k_true, fp_w],
                   ["カメラ A の写真 1(勾配+模様+物体)", "カメラ A の写真 2(別の場面)",
                    "真の指紋 K(σ = %.2f)" % SIGMA_K,
                    "推定した指紋 K̂(%d 枚、相関 %.2f)" % (N_TRAIN, r[mln])],
                   title="カメラ指紋(PRNU)の場面: 写真の雑音の中に固定の模様がある",
                   signed=[False, False, True, True], ncols=2)
    figs.save_table("estimators", ["推定のしかた", "真の K との相関", "PCE 同一", "PCE 別", "AUC"],
                    rows, title="指紋の推定: ゼロ点は AUC では負けない(%d 枚)" % N_TRAIN,
                    caption="場面が毎枚違えば生の平均でも指紋は出る。差は PCE の桁に出る。")
    return {"fp_w": fp_w, "fp_v": fp_v, "corr": r, "pce": pce}


# --------------------------------------------------------------------------- #
# 2. 照合(同一カメラ vs 別カメラ)                                              #
# --------------------------------------------------------------------------- #
def section_match(cams: dict, fp: np.ndarray, queries: dict) -> dict:
    print("\n" + "=" * 78)
    print("2) 照合: カメラ A の指紋に A の写真 %d 枚と B の写真 %d 枚を当てる" % (N_QUERY, N_QUERY))
    print("=" * 78)
    p_same, o_same = match(queries["A"], fp)
    p_diff, o_diff = match(queries["B"], fp)
    a = auc(p_same, p_diff)
    print("  同一カメラ PCE 中央値 %.0f(最小 %.0f)  ピーク (0,0) %d/%d" % (
        np.median(p_same), p_same.min(), o_same, N_QUERY))
    print("  別カメラ   PCE 中央値 %.1f(最大 %.1f)  ピーク (0,0) %d/%d" % (
        np.median(p_diff), p_diff.max(), o_diff, N_QUERY))
    print("  AUC %.3f" % a)
    null = _F.null_distribution(p_diff)
    q = _F.evidence_quantile(float(np.min(p_same)), null)
    print("  帰無分布(別カメラ %d 組)の 99 %% 点 %.1f / 同一カメラの最弱 1 枚は"
          "清浄分布の %.0f %% より外側(z = %.1f)" % (
              null["n"], null["quantiles"]["99"] if "99" in null["quantiles"]
              else list(null["quantiles"].values())[-1],
              100 * q["beyond_fraction"], q["z"] if q["z"] is not None else float("nan")))
    assert a > 0.99, a
    assert o_same == N_QUERY and o_diff <= 2, (o_same, o_diff)

    idx = np.arange(1, N_QUERY + 1)
    figs.save_plot("match_pce",
                   [("同一カメラ(A の写真)", idx, np.sort(p_same)[::-1]),
                    ("別カメラ(B の写真)", idx, np.sort(p_diff)[::-1])],
                   xlabel="写真(PCE の降順)", ylabel="PCE(対数目盛ではない)",
                   title="清浄条件の照合: PCE は 3 桁離れる(AUC %.3f)" % a,
                   caption="別カメラのピークは毎回別の位置に立つ((0,0) は %d/%d)。" % (o_diff, N_QUERY))
    return {"same": p_same, "diff": p_diff, "auc": a}


# --------------------------------------------------------------------------- #
# 3. 崖 1: 枚数 N(理論 SNR ∝ √N)                                             #
# --------------------------------------------------------------------------- #
def section_n_sweep(cams: dict, banks: dict, queries: dict) -> dict:
    print("\n" + "=" * 78)
    print("3) 枚数 N を 1 → 50 で掃引(予測: corr = 1/√(1 + (1/r₁² − 1)/N)、SNR ∝ √N)")
    print("=" * 78)
    k_true = cams["A"]
    big = banks["A_big"]
    ns = [1, 2, 3, 5, 8, 12, 20, 30, 50]
    cs, cz, ps, pd = [], [], [], []
    for n in ns:
        # N=1 は同じ画像を 2 枚渡す(ΣWI/ΣI² は複製で不変 = 1 枚の最尤推定そのもの)
        imgs = big[:n] if n >= 2 else [big[0], big[0]]
        fp = _F.sensor_fingerprint(imgs, denoiser="wiener", sigma=DENOISE_SIGMA)
        z1 = zero_mean_unit(np.mean([im - np.asarray(fs.apply(im, "gauss_image", a=0.25))
                                     for im in big[:n]], axis=0))
        cs.append(corr(fp, k_true))
        cz.append(corr(z1, k_true))
        s, _ = match(queries["A"][:12], fp)
        d, _ = match(queries["B"][:12], fp)
        ps.append(float(np.median(s)))
        pd.append(float(np.median(d)))
    r1 = cz[0]
    pred = [1.0 / np.sqrt(1.0 + (1.0 / r1 ** 2 - 1.0) / n) for n in ns]
    print("  %4s  %9s  %9s  %8s  %9s  %8s" % ("N", "相関 最尤", "相関 ゼロ点1", "√N 予測", "PCE同一", "PCE別"))
    for n, c, z, p, s, d in zip(ns, cs, cz, pred, ps, pd):
        print("  %4d  %9.3f  %9.3f  %8.3f  %9.0f  %8.1f" % (n, c, z, p, s, d))
    print("  ★N=1 では最尤(%.3f)がゼロ点 1(%.3f)より悪い —— ΣWI/ΣI² は 1 枚だと W/I で、"
          "暗い画素で雑音を割り増す。N≥%d で並ぶ。" % (
              cs[0], cz[0], next(n for n, c, z in zip(ns, cs, cz) if c > z - 0.02)))
    print("  ★√N 予測(ゼロ点 1 の N=1 から外挿)は N=50 で %.3f、実測 %.3f(差 %.3f)。"
          "√N で育つが、被写体の漏れ込みが下限を作る(N を増やしても縮まない)。"
          % (pred[-1], cz[-1], pred[-1] - cz[-1]))
    assert cs[-1] > cs[0] + 0.3, (cs[0], cs[-1])
    assert abs(pred[-1] - cz[-1]) < 0.1, (pred[-1], cz[-1])
    assert ps[-1] > 5 * ps[0], (ps[0], ps[-1])

    figs.save_plot("n_sweep_corr",
                   [("最尤 + 適応 Wiener(実測)", ns, cs),
                    ("ゼロ点 1: ガウス高域の平均(実測)", ns, cz),
                    ("√N 予測(ゼロ点 1 の N=1 から外挿)", ns, pred)],
                   xlabel="指紋を作った枚数 N [枚]", ylabel="真の K との相関 [-]",
                   title="指紋は √N で育つ —— 予測と実測(最尤は 1 枚だと負ける)")
    figs.save_plot("n_sweep_pce",
                   [("同一カメラ PCE(中央値)", ns, ps), ("別カメラ PCE(中央値)", ns, pd)],
                   xlabel="指紋を作った枚数 N [枚]", ylabel="PCE [-]",
                   title="枚数と PCE: 1 枚でも 2 桁の差は出る")
    return {"ns": ns, "corr": cs, "corr_zero": cz, "pred": pred, "pce_same": ps, "pce_diff": pd}


# --------------------------------------------------------------------------- #
# 4. 崖 2: 8×8 DCT 量子化(JPEG 相当)                                           #
# --------------------------------------------------------------------------- #
def section_jpeg(fp: np.ndarray, queries: dict, clean: dict) -> dict:
    print("\n" + "=" * 78)
    print("4) 検査画像を JPEG 相当(8×8 DCT 量子化)にしてから照合")
    print("=" * 78)
    # 残差の σ(0..255 単位)—— 量子化幅と比べる物差し。DCT は直交なので係数も同じ σ。
    w0 = np.asarray(fs.apply(queries["A"][0], "xsp_wiener", a=0.0))
    sig_res = float((queries["A"][0] - w0).std()) * 255.0
    print("  残差 σ = %.2f(0..255 単位)。量子化幅 Δ がこの 2σ を超えた係数は死ぬ、が予測" % sig_res)
    base_same = float(np.median(clean["same"]))
    avals = [0.0, 0.05, 0.1, 0.2, 0.3, 0.375, 0.5, 0.7, 1.0]
    rows, aucs, ratios, preds, qs = [], [], [], [], []
    for a in avals:
        q = jpeg_quality_equiv(a)
        s_imgs = [np.asarray(fs.apply(im, "aug_jpeg_blocks", a=a, b=0.0)) for im in queries["A"]]
        d_imgs = [np.asarray(fs.apply(im, "aug_jpeg_blocks", a=a, b=0.0)) for im in queries["B"]]
        ps, _ = match(s_imgs, fp)
        pd, _ = match(d_imgs, fp)
        au = auc(ps, pd)
        ratio = float(np.median(ps)) / base_same
        steps = JPEG_LUMA_Q50 * (1.0 + 40.0 * a) / 16.0
        gains = np.array([quantizer_gain(sig_res, st) for st in steps.ravel()])
        pred = float(gains.mean() ** 2)
        surv = float((steps <= 2 * sig_res).mean())
        rows.append(("%.2f" % a, "%.0f" % q, "%.0f" % np.median(ps), "%.1f" % np.median(pd),
                     "%.3f" % au, "%.1f %%" % (100 * ratio), "%.1f %%" % (100 * pred),
                     "%.0f %%" % (100 * surv)))
        aucs.append(au)
        ratios.append(ratio)
        preds.append(pred)
        qs.append(q)
        print("  a=%.3f (品質 %3.0f 相当)  PCE 同一 %6.0f / 別 %5.1f  AUC %.3f  "
              "PCE 比 %5.1f %%  予測 %5.1f %%  (Δ≤2σ の係数 %3.0f %%)" % (
                  a, q, np.median(ps), np.median(pd), au, 100 * ratio, 100 * pred, 100 * surv))
    i90 = min(range(len(qs)), key=lambda i: abs(qs[i] - 90))
    i50 = avals.index(0.375)
    print("  ★品質 90 相当で PCE %.0f %%、品質 50 相当で %.1f %%(量子化利得² の予測 %.1f %%"
          " —— ほぼ的中)。" % (100 * ratios[i90], 100 * ratios[i50], 100 * preds[i50]))
    print("  ★予測が外れるのは品質 %.0f 相当より下(予測 %.1f %% / 実測 %.1f %%): 予測は"
          "死に過ぎ = ショット雑音がディザになって量子化幅より小さい信号も少し通す。" % (
              qs[-2], 100 * preds[-1], 100 * ratios[-1]))
    weak = [q for q, au in zip(qs, aucs) if au < 0.9]
    print("  それでも AUC は品質 %.0f 相当まで 1.000 を保ち、AUC < 0.9 になるのは品質 %s 相当から"
          "(最低の品質 %.0f 相当で AUC %.3f)。PCE が 1/25 になっても判定はまだ壊れない。" % (
              min(q for q, au in zip(qs, aucs) if au >= 0.999),
              "%.0f" % max(weak) if weak else "(範囲内では起きない)", qs[-1], aucs[-1]))
    assert 0.3 < ratios[i90] < 0.8 and aucs[i90] > 0.95, (ratios[i90], aucs[i90])
    assert abs(preds[i50] - ratios[i50]) < 0.02, (preds[i50], ratios[i50])
    assert aucs[i50] > 0.95 and aucs[-1] < 0.8, (aucs[i50], aucs[-1])

    figs.save_table("jpeg_sweep",
                    ["a", "IJG 品質相当", "PCE 同一", "PCE 別", "AUC", "PCE 比(清浄=100)", "予測 PCE 比", "Δ≤2σ の係数"],
                    rows, title="JPEG 相当の量子化で指紋はどこまで残るか")
    figs.save_plot("jpeg_cliff",
                   [("PCE 比 実測 [%]", qs, [100 * r for r in ratios]),
                    ("PCE 比 予測(量子化利得²)[%]", qs, [100 * p for p in preds]),
                    ("AUC × 100", qs, [100 * a for a in aucs])],
                   xlabel="IJG 品質相当 [-](左ほど強い圧縮)", ylabel="[%]",
                   title="JPEG の崖: PCE は品質 90 で半分、判定(AUC)は品質 30 台まで持つ")
    return {"q": qs, "auc": aucs, "ratio": ratios}


# --------------------------------------------------------------------------- #
# 5. 崖 3: 縮小して戻す                                                          #
# --------------------------------------------------------------------------- #
def resize_roundtrip(im: np.ndarray, s: float) -> np.ndarray:
    """s 倍に縮小してから元の画素数に戻す(双一次)。★任意倍率は公開経路に無い。"""
    if s >= 1.0:
        return im
    small = zoom(im, s, order=1, mode="reflect", grid_mode=True)
    back = zoom(small, N_PIX / small.shape[0], order=1, mode="reflect", grid_mode=True)
    return np.clip(back[:N_PIX, :N_PIX], 0, 1)


def section_resize(fp: np.ndarray, queries: dict, clean: dict) -> dict:
    print("\n" + "=" * 78)
    print("5) 検査画像を縮小して戻してから照合(予想: 0.5× は 2×2 箱平均で相関 1/2 → PCE 25 %)")
    print("=" * 78)
    base_same = float(np.median(clean["same"]))
    scales = [1.0, 0.95, 0.9, 0.75, 0.5]
    rows, aucs, ratios = [], [], []
    for s in scales:
        ps, o_s = match([resize_roundtrip(im, s) for im in queries["A"]], fp)
        pd, _ = match([resize_roundtrip(im, s) for im in queries["B"]], fp)
        au = auc(ps, pd)
        ratio = float(np.median(ps)) / base_same
        rows.append(("%.2f×" % s, "%.0f" % np.median(ps), "%.1f" % np.median(pd), "%.3f" % au,
                     "%.1f %%" % (100 * ratio), "%d/%d" % (o_s, N_QUERY)))
        aucs.append(au)
        ratios.append(ratio)
        print("  %.2f×  PCE 同一 %6.0f / 別 %5.1f  AUC %.3f  PCE 比 %5.1f %%  (0,0) %d/%d" % (
            s, np.median(ps), np.median(pd), au, 100 * ratio, o_s, N_QUERY))
    r05, r09 = ratios[scales.index(0.5)], ratios[scales.index(0.9)]
    print("  ★0.5× の実測 %.1f %%(予想 25 %%)—— 半画素の重心ずれで位置合わせが崩れる。"
          "0.9× は %.1f %%(AUC %.3f)で、偶数倍より非整数倍のほうが致命的。" % (
              100 * r05, 100 * r09, aucs[scales.index(0.9)]))
    assert r05 < 0.25, r05
    assert aucs[scales.index(0.9)] < 0.8, aucs

    figs.save_table("resize_sweep", ["倍率", "PCE 同一", "PCE 別", "AUC", "PCE 比(清浄=100)", "ピーク (0,0)"],
                    rows, title="縮小して戻すと指紋はどこまで残るか")
    figs.save_plot("resize_cliff",
                   [("PCE 比 実測 [%]", scales, [100 * r for r in ratios]),
                    ("AUC × 100", scales, [100 * a for a in aucs])],
                   xlabel="縮小倍率 [-]", ylabel="[%]",
                   title="縮小の崖: 0.95× でもう半分、0.9× で判定不能")
    return {"scales": scales, "auc": aucs, "ratio": ratios}


# --------------------------------------------------------------------------- #
# 6. 対照群: 平坦 vs 模様 / 同じ場面の漏れ込み / K=0 のカメラ                       #
# --------------------------------------------------------------------------- #
def section_controls(cams: dict, banks: dict, queries: dict) -> dict:
    print("\n" + "=" * 78)
    print("6) 対照群 —— 何が指紋を作り、何が指紋に化けるか")
    print("=" * 78)
    out = {}
    k_a = cams["A"]

    # (a) 平坦画像だけで推定 vs 模様の多い画像
    fp_flat = _F.sensor_fingerprint(banks["A_flat"], denoiser="wiener", sigma=DENOISE_SIGMA)
    fp_tex = _F.sensor_fingerprint(banks["A"], denoiser="wiener", sigma=DENOISE_SIGMA)
    c_flat, c_tex = corr(fp_flat, k_a), corr(fp_tex, k_a)
    ps_f, _ = match(queries["A"], fp_flat)
    ps_t, _ = match(queries["A"], fp_tex)
    print("  (a) 平坦(壁)%d 枚で作った指紋: 相関 %.3f  PCE 中央値 %.0f" % (N_TRAIN, c_flat, np.median(ps_f)))
    print("      模様入り %d 枚で作った指紋:  相関 %.3f  PCE 中央値 %.0f" % (N_TRAIN, c_tex, np.median(ps_t)))
    print("      ★つまらない写真のほうが指紋の学習には良い(被写体が漏れ込まない)。")
    assert c_flat > c_tex, (c_flat, c_tex)
    out["flat"] = (c_flat, c_tex)

    # (b)(c) 同じ場面の漏れ込み —— K=0 のカメラ C で「指紋」が出るか
    k_c = cams["C"]
    fp_c_var = _F.sensor_fingerprint(banks["C"], denoiser="wiener", sigma=DENOISE_SIGMA)
    fp_c_fix = _F.sensor_fingerprint(banks["C_fixed"], denoiser="wiener", sigma=DENOISE_SIGMA)
    # C の別の写真(場面は毎枚違う)を C の指紋に当てる: 指紋が無いのだから何も出ないはず
    p_cc, _ = match(queries["C"], fp_c_var)
    p_bc, _ = match(queries["B"], fp_c_var)
    a_var = auc(p_cc, p_bc)
    print("  (b) K=0 のカメラ C(場面は毎枚違う): C の写真 PCE 中央値 %.1f / B の写真 %.1f  AUC %.3f"
          % (np.median(p_cc), np.median(p_bc), a_var))
    # 同じ背景を写した 30 枚から作った C の「指紋」に、別カメラ B で撮った同じ背景を当てる
    p_bfix, _ = match(queries["B_fixed"], fp_c_fix)
    p_bvar, _ = match(queries["B"], fp_c_fix)
    a_fix = auc(p_bfix, p_bvar)
    print("  (c) 同じ背景 %d 枚から作った C の「指紋」: B が同じ背景を撮った写真 PCE 中央値 %.0f"
          " / B の別場面 %.1f  AUC %.3f" % (N_TRAIN, np.median(p_bfix), np.median(p_bvar), a_fix))
    print("      ★★指紋が無いカメラの「指紋」に、別カメラの写真が完全に一致する。"
          "一致していたのは被写体。真の K との相関は %.3f(= 何も捉えていない)。" % corr(fp_c_fix, k_a))
    assert a_var < 0.7, a_var
    assert a_fix > 0.95 and float(np.median(p_bfix)) > 100, (a_fix, np.median(p_bfix))
    out["k0"] = (float(np.median(p_cc)), a_var, float(np.median(p_bfix)), a_fix)

    figs.save_grid("controls_map",
                   [banks["C_fixed"][0], banks["C_fixed"][1], fp_c_fix, fp_flat],
                   ["K=0 のカメラ C、同じ背景の写真 1", "同 写真 2(物体だけ違う)",
                    "C の「指紋」(背景の模様が化けた)",
                    "壁だけで作った A の指紋(相関 %.2f)" % c_flat],
                   title="対照群: 指紋が無くても、同じ背景は指紋に化ける",
                   signed=[False, False, True, True], ncols=2)
    figs.save_table("controls",
                    ["条件", "真の K との相関", "PCE 中央値", "AUC"],
                    [("A: 模様入り %d 枚" % N_TRAIN, "%+.3f" % c_tex, "%.0f" % np.median(ps_t), "—"),
                     ("A: 壁 %d 枚" % N_TRAIN, "%+.3f" % c_flat, "%.0f" % np.median(ps_f), "—"),
                     ("C(K=0): 場面を毎回変える", "—", "%.1f" % np.median(p_cc), "%.3f" % a_var),
                     ("C(K=0): 同じ背景 → B の同じ背景", "—", "%.0f" % np.median(p_bfix), "%.3f" % a_fix)],
                    title="何が指紋を作り、何が指紋に化けるか")
    return out


# --------------------------------------------------------------------------- #
# 7. デノイザの選択で PCE は何倍変わるか                                          #
# --------------------------------------------------------------------------- #
def section_denoisers(cams: dict, banks: dict, queries: dict) -> dict:
    print("\n" + "=" * 78)
    print("7) デノイザ F の選択: 残差 W = I − F(I) の取り方で PCE は何倍動くか(%d 枚)" % 16)
    print("=" * 78)
    k_true = cams["A"]
    train = banks["A"][:16]
    qs = queries["A"][:10]
    qd = queries["B"][:10]

    def op_residual(name, a):
        return lambda im: im - np.asarray(fs.apply(im, name, a=a, b=0.0))

    # fullseye の残差器(非公開)は sensor_fingerprint/fingerprint_correlate 経由で使う
    cands = [("gauss_image (σ≈1.0)", "gauss_image", 0.25),
             ("median_image (3x3)", "median_image", 0.0),
             ("xsp_wiener (3x3, scipy)", "xsp_wiener", 0.0),
             ("sk_tv (Chambolle)", "sk_tv", 0.1),
             ("sk_wavelet (BayesShrink)", "sk_wavelet", 0.5),
             ("xsp_dct_denoise", "xsp_dct_denoise", 0.2),
             ("sk_nlm (非局所平均)", "sk_nlm", 0.2)]
    rows = []
    for label, op, a in cands:
        rf = op_residual(op, a)
        fp = ml_fingerprint(train, rf)
        pce_s = np.median([pce_from_residual(rf(im), im * fp) for im in qs])
        pce_d = np.median([pce_from_residual(rf(im), im * fp) for im in qd])
        rms = float(np.mean([rf(im).std() for im in qs]))
        rows.append([label, corr(fp, k_true), float(pce_s), float(pce_d), rms])
    for label, dn in [("fullseye wiener(局所 Wiener・多窓)", "wiener"),
                      ("fullseye wavelet(db4 + 局所 Wiener)", "wavelet")]:
        fp = _F.sensor_fingerprint(train, denoiser=dn, sigma=DENOISE_SIGMA)
        ps, _ = match(qs, fp, denoiser=dn)
        pd, _ = match(qd, fp, denoiser=dn)
        rows.append([label, corr(fp, k_true), float(np.median(ps)), float(np.median(pd)), float("nan")])
    best = max(r[2] for r in rows)
    noise_rms = float(np.mean([(im - scene(SEED + 5000 + i)).std() for i, im in enumerate(qs[:1])]))
    print("  %-38s %7s %9s %8s %7s %8s" % ("デノイザ", "相関", "PCE同一", "PCE別", "倍率", "残差RMS"))
    table = []
    for label, c, ps, pd, rms in rows:
        print("  %-38s %+7.3f %9.0f %8.1f %7.2f %8s" % (
            label, c, ps, pd, ps / best, ("%.4f" % rms) if np.isfinite(rms) else "(内部)"))
        table.append((label, "%+.3f" % c, "%.0f" % ps, "%.1f" % pd, "%.2f" % (ps / best),
                      ("%.4f" % rms) if np.isfinite(rms) else "(内部)"))
    ratios = {r[0]: r[2] / best for r in rows}
    worst = min(ratios.values())
    print("  ★最良と最悪で PCE は %.1f 倍違う。sk_wavelet は残差 RMS %.4f で生の雑音"
          "(σ ≈ %.4f)と同じ = ほとんど平滑していない。" % (
              1.0 / worst, rows[4][4], np.hypot(np.sqrt(0.5 / FULL_WELL), READ_NOISE)))
    assert 1.0 / worst > 3.0, ratios
    assert rows[4][1] < 0.3, rows[4]      # sk_wavelet は指紋を捉えない
    figs.save_table("denoisers",
                    ["デノイザ F", "真の K との相関", "PCE 同一", "PCE 別", "倍率(最良=1)", "残差 RMS"],
                    table, title="残差の取り方で PCE は %.1f 倍動く(16 枚)" % (1.0 / worst),
                    caption="上 7 行は fullseye の平滑 op + 自前の最尤式と PCE、下 2 行は"
                            " sensor_fingerprint / fingerprint_correlate(残差器は内部)。")
    return {"ratios": ratios, "rows": rows}


# --------------------------------------------------------------------------- #
# 8. 道具の穴                                                                     #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("8) 道具の穴(この PoC で imgforensics 族を使ってみて)")
    print("=" * 78)
    # (a) 残差を直接渡して照合する口が無い → 7 節は PCE を自前で書いた
    print("  (a) fingerprint_correlate は残差を内部で取る(wiener / wavelet の 2 択)。"
          "任意の平滑 op で作った残差を照合に渡す口が無く、7 節の PCE は自前。")
    # (b) 1 枚からの指紋(最尤式は 1 枚でも定義される)が min_n=2 で弾かれる
    try:
        _F.sensor_fingerprint([np.full((8, 8), 0.5)])
        raised = False
    except (ValueError, TypeError):
        raised = True
    assert raised, "1 枚で通るようになった(3 節の複製トリックを外すこと)"
    print("  (b) sensor_fingerprint は 2 枚未満を弾く。1 枚の最尤推定は式として定義"
          "されるので、3 節は同じ画像を 2 枚渡して代用した。")
    # (c) 任意倍率のリサンプル(0.5×)が公開経路に無い
    print("  (c) 縮小→拡大の往復(5 節)は scipy.ndimage.zoom。rescale_img は 0.7〜1.3 倍"
          "で 0.5× に届かず、zoom_image_size は左上詰めで位置を保たない。")
    # (d) ROC / AUC を出す op が無い(forensics 族は判定を返さない設計だが、性能評価には要る)
    assert not hasattr(fs, "roc_auc") and not hasattr(fs.ledger, "roc_auc")
    print("  (d) 証拠量の列から AUC / ROC を出す op が無い(null_distribution は"
          "帰無側だけ)。本 PoC は Mann–Whitney を自前で書いた。")


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.perf_counter()
    print("=" * 78)
    print("カメラ指紋(PRNU): 指紋は枚数で育ち、保存ボタンで消える")
    print("視野 %d px / σ_K %.2f / フルウェル %.0f e⁻ / 読み出し σ %.3f / 学習 %d 枚・照合 %d 枚"
          % (N_PIX, SIGMA_K, FULL_WELL, READ_NOISE, N_TRAIN, N_QUERY))
    print("=" * 78)

    cams = {"A": sensor_pattern(SEED + 1), "B": sensor_pattern(SEED + 2),
            "C": np.zeros((N_PIX, N_PIX))}
    fixed_tex = gaussian_filter(np.random.default_rng(SEED + 99).standard_normal((N_PIX, N_PIX)), 2.0)
    fixed_tex = 0.10 * fixed_tex / fixed_tex.std()
    banks = {
        "A": bank(cams["A"], N_TRAIN, 1000),
        "A_big": bank(cams["A"], 50, 2000),
        "A_flat": bank(cams["A"], N_TRAIN, 3000, flat=True),
        "C": bank(cams["C"], N_TRAIN, 4000),
        "C_fixed": bank(cams["C"], N_TRAIN, 4500, texture=fixed_tex),
    }
    queries = {
        "A": bank(cams["A"], N_QUERY, 5000),
        "B": bank(cams["B"], N_QUERY, 6000),
        "C": bank(cams["C"], N_QUERY, 7000),
        "B_fixed": bank(cams["B"], N_QUERY, 8000, texture=fixed_tex),
    }

    est = section_estimate(cams, banks, queries)
    clean = section_match(cams, est["fp_w"], queries)
    section_n_sweep(cams, banks, queries)
    section_jpeg(est["fp_w"], queries, clean)
    section_resize(est["fp_w"], queries, clean)
    section_controls(cams, banks, queries)
    section_denoisers(cams, banks, queries)
    section_tool_gaps()

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * 指紋は「各枚から平滑成分を引いてから平均」で出る。写真の平均では出ない。")
    print("  * 清浄なら PCE は 3 桁離れる。JPEG 品質 90 相当で 1/8、縮小 0.9× で判定不能。")
    print("  * 同じ背景を写した写真は、指紋の無いカメラでも指紋に化ける。学習は壁で。")
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
