# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""varmodel — 良品統計の変動モデル(位置合わせした良品群の画素ごとの中心とばらつき → 許容帯 → 欠陥図)。

外観検査の古典「良品を何枚も撮って、画素ごとに"いつもの値"と"いつものばらつき"を覚え、
そこから外れた画素を欠陥とする」を、**誤検出率を宣言して**使える形にした op 族。
既存の ``inspection.create_variation_model``(平均 ± k·std、k は手で決める)と
``fullseye.compare_to_golden``(基準 1 枚との差、閾値は手で決める)に欠けていた 4 つを足す:

1. **閾値を分布から決める**: 画素あたりの両側誤検出率 ``far`` を宣言すると、帯の幅 ``k`` は
   予測区間の分布から閉形式で出る(検査対象の欠陥で調整しない)。正規の良品なら
   ``(x − x̄) / (s·√(1+1/n)) ~ t_{n−1}`` なので ``k = t⁻¹_{n−1}(1 − far/2)·√(1+1/n)``。
2. **良品が少ないとき**: 画素ごとの分散は n が小さいと大きく揺れる。``pooled``(全画素で 1 つの分散)と
   ``moderated``(経験ベイズの縮小、Smyth 2004 の moderated t)を用意した。moderated は
   画素の分散が尺度つき逆カイ二乗の事前分布に従うとき ``t_{d+d0}`` が**厳密に**成り立つ。
3. **汚れた良品群に強く**: ``mad``(中央値と MAD)。正規の下で ``(x − med)/MAD`` は
   位置と尺度によらない量(ピボット)なので、``k`` は n と far だけで決まり、乱数の
   モンテカルロで 1 回求めて使い回す(種は固定、乱数の誤差は返り値に書く)。
4. **位置合わせを確かめる**: 良品群がずれていると帯は**太り**(縁で分散が膨らむ)、欠陥を見逃す。
   ``align="check"`` は各良品の並進(位相相関 + 放物線のサブピクセル)を測り、
   ``max_misalign_px`` を超える群は**拒否**する。``align="translate"`` は並進を測って
   Fourier シフトで合わせる(Fourier シフトは全域通過なので白色雑音の分散を変えない ——
   双線形補間は雑音を均して帯を細らせ、誤検出率を宣言より上げる)。

op(並びは使う順):

  * :func:`varmodel_alignment` — 良品群の並進のずれと、許容までの余裕。
  * :func:`varmodel_band_k` — n・far・ばらつきの種類から帯の幅 k(閉形式 / ピボット)。
  * :func:`varmodel_fit` — 良品群 → 中心・ばらつき・k・有効画素。
  * :func:`varmodel_calibrate` — 当てはめに使わなかった良品で k を測り直す(分布の仮定が外れる実画像用)。
  * :func:`varmodel_score` — 1 枚を当てて z 図(何 σ ずれたか)・はみ出し図・領域ごとの説明。

評価指標(画素 AUROC・PRO)は方法に依存しない別の族 ``anomeval`` にある。

★仮定(明示): 良品の画素値は画素ごとに独立な正規(moderated は分散に事前分布)。
実画像は空間相関・量子化・照明の揺れで外れる —— 実データの誤検出率は宣言と一致しない
ことがあり、それは良品だけの持ち出し(hold-out)で**測って**報告する(``examples/poc_good_sample_variation_model.py``)。
そのときの逃げ道が :func:`varmodel_calibrate`(k を良品の持ち出しの |z| の分位で決め直す。欠陥は見ない)。

出典(公開文献のみ): G. K. Smyth, *Stat. Appl. Genet. Mol. Biol.* 3(1):3, 2004(moderated t、
trigamma の逆関数)/ P. J. Rousseeuw & C. Croux, *JASA* 88:1273, 1993(MAD の 1.4826)/
M. Guizar-Sicairos, S. T. Thurman, J. R. Fienup, *Opt. Lett.* 33:156, 2008(upsampled DFT)。
"""
from __future__ import annotations

import functools
import math

import numpy as np

__all__ = ["varmodel_alignment", "varmodel_band_k", "varmodel_fit", "varmodel_calibrate",
           "varmodel_score", "SPREADS"]

#: ばらつきの種類。std = 画素ごとの標本標準偏差 / pooled = 全画素で 1 つ /
#: moderated = 経験ベイズの縮小 / mad = 中央値と MAD(頑健)。
SPREADS = ("std", "pooled", "moderated", "mad")

_MAD_TO_SIGMA = 1.482602218505602          # 1 / Φ⁻¹(3/4)
_MAD_MIN_N = 5
_MAD_MIN_FAR = 1e-3                        # これより小さい far はモンテカルロが重すぎる
_MIN_FAR = 1e-9
_MAX_PIXELS = 1 << 26                      # 1 回の呼び出しで受け付ける画素の上限(メモリの防壁)
_MIN_PRIOR_PIXELS = 50                     # moderated の事前分布を推定するのに要る画素数


def _stats():
    from scipy import stats as _st          # noqa: PLC0415 — 遅延 import(numpy だけの環境で落ちない)
    return _st


def _special():
    from scipy import special as _sp        # noqa: PLC0415
    return _sp


# --------------------------------------------------------------------------- #
# 入力の検査                                                                    #
# --------------------------------------------------------------------------- #
def _stack(x, name, op, min_n=1, min_side=4):
    """(n, H, W) の有限な float64 に揃える。空・形違い・非有限は ValueError。"""
    if isinstance(x, (list, tuple)):
        if len(x) == 0:
            raise ValueError("%s: %s is empty (0 images)" % (op, name))
        arrs = [np.asarray(a, dtype=np.float64) for a in x]
        if any(a.ndim != 2 for a in arrs):
            raise ValueError("%s: every image in %s must be 2-D" % (op, name))
        if len({a.shape for a in arrs}) != 1:
            raise ValueError("%s: images in %s differ in shape: %s"
                             % (op, name, sorted({a.shape for a in arrs})))
        a = np.stack(arrs, axis=0)
    else:
        a = np.asarray(x, dtype=np.float64)
    if a.size == 0:
        raise ValueError("%s: %s is empty" % (op, name))
    if a.ndim == 2:
        a = a[None]
    if a.ndim != 3:
        raise ValueError("%s: %s must be (n, H, W) or a list of 2-D images, got shape %s"
                         % (op, name, a.shape))
    if a.size > _MAX_PIXELS:
        raise ValueError("%s: %s has %d values (> %d); downsample first" % (op, name, a.size, _MAX_PIXELS))
    if a.shape[0] < min_n:
        raise ValueError("%s: %s needs at least %d images, got %d" % (op, name, min_n, a.shape[0]))
    if min(a.shape[1:]) < min_side:
        raise ValueError("%s: images in %s must be at least %d x %d, got %s"
                         % (op, name, min_side, min_side, a.shape[1:]))
    if not np.isfinite(a).all():
        raise ValueError("%s: %s contains non-finite values" % (op, name))
    return a


def _image(x, name, op):
    a = np.asarray(x, dtype=np.float64)
    if a.size == 0:
        raise ValueError("%s: %s is empty" % (op, name))
    if a.ndim != 2:
        raise ValueError("%s: %s must be a 2-D image, got shape %s" % (op, name, a.shape))
    if not np.isfinite(a).all():
        raise ValueError("%s: %s contains non-finite values" % (op, name))
    return a


def _far(far, op, spread):
    try:
        f = float(far)
    except (TypeError, ValueError):
        raise ValueError("%s: far must be a number, got %r" % (op, far)) from None
    if isinstance(far, bool) or not (_MIN_FAR <= f < 0.5):
        raise ValueError("%s: far (two-sided false-alarm rate per pixel) must be in [%g, 0.5), got %r"
                         % (op, _MIN_FAR, far))
    if spread == "mad" and f < _MAD_MIN_FAR:
        raise ValueError("%s: spread='mad' takes its k from a Monte-Carlo pivot and supports far >= %g "
                         "(got %g); use spread='std'/'moderated' for smaller rates" % (op, _MAD_MIN_FAR, f))
    return f


def _spread_kind(spread, op):
    if spread not in SPREADS:
        raise ValueError("%s: spread must be one of %s, got %r" % (op, SPREADS, spread))
    return spread


# --------------------------------------------------------------------------- #
# 1. 位置合わせ                                                                 #
# --------------------------------------------------------------------------- #
_UPSAMPLE = 20                             # サブピクセルの刻み = 1/20 px


_WHITEN = 0.5                              # = filters_freq.phase_correlation_fft の既定


def _ref_spec(ref):
    h, w = ref.shape
    win = np.outer(np.hanning(h), np.hanning(w))
    return win, np.fft.fft2((ref - ref.mean()) * win)


def _offset(ref, img, spec=None):
    """``img`` が ``ref`` に対して (行, 列) にどれだけずれているか(サブピクセル)と PSR。

    粗い整数の山は ``filters_freq.phase_correlation_fft`` と**同じ式**(Hann 窓 + 半白色化、
    その既定。``tests/test_varmodel.py`` が整数の山の一致を固定)で取り、基準のスペクトルは
    群の中で使い回す。山の周り ±0.75 px を行列 DFT で 1/20 px 刻みに上げて探す
    (Guizar-Sicairos ら 2008 の upsampled DFT)。放物線の当てはめは、半白色化の山が広いと
    0.3 px 以上ずれた(実測)ので使わない。細かい探索は**白色化しない**相互相関で行う(半白色化は
    雑音の多い高い周波数を持ち上げ、雑音 1 % の像で 0.18 px 外れた、実測)。

    ★窓は動かないので、並進の推定は 0 の側へ偏る(整数 3 px の巡回シフトで 2.95、実測)。
    偏りはずれの大きさに比例するから、推定した分だけ Fourier シフトで戻して残りをもう一度測り、
    足し合わせる(最大 3 回、残りが刻み 1/20 px 未満で止める)。
    """
    win, fa = spec if spec is not None else _ref_spec(ref)
    tr = tc = 0.0
    psr = 0.0
    work = img
    for it in range(3):
        r, c, p = _offset_once(win, fa, work)
        if it == 0:
            psr = p
        tr += r
        tc += c
        if max(abs(r), abs(c)) < 1.0 / _UPSAMPLE:
            break
        work = _fourier_shift(img, -tr, -tc)
    return tr, tc, psr


def _offset_once(win, fa, img):
    h, w = img.shape
    fb = np.fft.fft2((img - img.mean()) * win)
    R0 = fa * np.conj(fb)
    R = R0 / (np.abs(R0) ** _WHITEN + 1e-12)
    c = np.fft.ifft2(R).real
    pk = np.unravel_index(int(np.argmax(c)), c.shape)
    dr0 = pk[0] - (h if pk[0] > h // 2 else 0)
    dc0 = pk[1] - (w if pk[1] > w // 2 else 0)
    sd = float(c.std())
    psr = float((c[pk] - c.mean()) / sd) if sd > 0 else 0.0
    span = int(math.ceil(0.75 * _UPSAMPLE))
    steps = np.arange(-span, span + 1) / _UPSAMPLE
    rs = dr0 + steps
    cs = dc0 + steps
    er = np.exp(2j * np.pi * np.outer(rs, np.fft.fftfreq(h)))
    ec = np.exp(2j * np.pi * np.outer(np.fft.fftfreq(w), cs))
    cc = (er @ R0 @ ec).real                # 細かい山は白色化しない相互相関(白色雑音で最尤)
    i, j = np.unravel_index(int(np.argmax(cc)), cc.shape)
    # phase_correlation_fft の符号: image2 = roll(image1, d) のとき −d を返す。
    return -float(rs[i]), -float(cs[j]), psr


def _fourier_shift(img, dr, dc):
    """``img`` を (dr, dc) だけ動かす(Fourier シフト、全域通過 = 白色雑音の分散を保つ)。

    ★そのまま FFT で動かすと、像の上下・左右の端の不連続が巡回で繋がって**輪状の波紋**
    (Gibbs)が像の内側まで入る —— 2 px 動かした合成の像どうしの推定が 0.2 px 外れた(実測)。
    そこで鏡映しで縁を延ばしてから動かし、切り戻す(延ばした像は端で値が連続する)。
    双線形やスプラインの補間は雑音を均して帯を細らせるので使わない。
    """
    h, w = img.shape
    p = int(math.ceil(max(abs(dr), abs(dc)))) + 16
    big = np.pad(img, p, mode="symmetric")
    H, W = big.shape
    fr = np.fft.fftfreq(H)[:, None]
    fc = np.fft.fftfreq(W)[None, :]
    ph = np.exp(-2j * np.pi * (fr * dr + fc * dc))
    return np.fft.ifft2(np.fft.fft2(big) * ph).real[p:p + h, p:p + w]


def _offsets_against(ref, a):
    offs = np.zeros((a.shape[0], 2))
    psr = np.zeros(a.shape[0])
    spec = _ref_spec(ref)
    for i in range(a.shape[0]):
        r, c, p = _offset(ref, a[i], spec)
        offs[i] = (r, c)
        psr[i] = p
    return offs, psr


def _alignment(a, max_misalign_px):
    """各良品の並進を、群の「典型の位置」(並進の中央値)に対して測る。

    画素ごとの中央値の像は、ずれた群では**ずれの混ざった像**になり、それとの相関は
    0.8 px も外れた(実測)。そこで 3 段で測る: (1) 中央値像に対して粗く測り、
    (2) 並進が中央値に最も近い**実在の 1 枚**を基準に測り直し、(3) その結果で全員を
    合わせた平均像(雑音が 1/√n に下がる)に対してもう一度測る。並進は最後に中央値を
    引いて「群の典型からのずれ」にする。
    """
    n = a.shape[0]
    o1, _ = _offsets_against(np.median(a, axis=0), a)
    i0 = int(np.argmin(np.abs(o1 - np.median(o1, axis=0)).max(axis=1)))
    o2, _ = _offsets_against(a[i0], a)
    o2 -= np.median(o2, axis=0)
    reg = np.stack([_fourier_shift(a[i], -o2[i, 0], -o2[i, 1]) for i in range(n)])
    ref = reg.mean(axis=0)
    offs, psr = _offsets_against(ref, a)
    offs -= np.median(offs, axis=0)
    sd = _shift_sd(reg, ref)
    observable = bool(sd <= max_misalign_px / 4.0)
    if not observable:                     # 像に構造が無い: ずれは測れず、帯を太らせることもない
        offs = np.zeros_like(offs)
    mag = np.abs(offs).max(axis=1)
    return offs, mag, psr, sd, observable


def _shift_sd(reg, ref):
    """並進の推定のばらつき(Cramér–Rao の近似)。``σ_shift² ≈ σ²(1 + 1/n) / Σ(∂ref)²``。

    σ² は合わせた群の画素ごとの分散の平均、``Σ(∂ref)²`` は基準の差分の二乗和から雑音の寄与
    (差分 1 つあたり 2σ²/n)を引いた**構造の**勾配エネルギー。構造が無い(平らな良品・純粋な
    雑音)と分母が 0 に近づき、ばらつきは無限大 —— その群の並進は測れない。けれど構造が無ければ
    ずれは帯を太らせもしない(帯の太りは |∇μ|·ずれ に比例する)ので、拒否ではなく「測れない」と報告する。
    """
    n = reg.shape[0]
    s2 = float(reg.var(axis=0, ddof=1).mean()) if n > 1 else 0.0
    worst = 0.0
    for ax in (0, 1):
        dif = np.diff(ref, axis=ax)
        g = float(np.sum(dif * dif)) - dif.size * 2.0 * s2 / n
        if g <= 0.0:
            return float(max(ref.shape))   # 構造なし: 像の大きさ以下には言えない(inf を返さない)
        worst = max(worst, math.sqrt(s2 * (1.0 + 1.0 / n) / g))
    return worst


def varmodel_alignment(stack, max_misalign_px=0.5):
    """Translation offset of every good sample against the typical position of the stack, and the margin to the tolerance (``table``).

    Each image of ``stack`` (n, H, W) is phase-correlated (``filters_freq.phase_correlation_fft``)
    against a reference built from the stack itself (the most typical sample, then the
    registered mean); the integer peak is refined to 1/20 px by an upsampled DFT
    (Guizar-Sicairos et al. 2008). Offsets are relative to the median offset, so a common
    shift of every sample is not a misalignment. Returns ``offset`` (n, 2) = (row, col) in px
    (positive = the sample sits further down / right than the typical one), ``abs_offset`` (n,) = the larger of the two, ``margin_px``
    = ``max_misalign_px - abs_offset`` (negative = this sample breaks the tolerance), ``ok``
    (all margins >= 0), ``worst`` (index of the most shifted sample) and ``psr`` (peak-to-
    sidelobe ratio of the correlation), ``shift_sd_px`` (Cramér–Rao lower bound of the offset's
    spread: noise variance over the structural gradient energy of the registered mean; the
    window makes the real spread a few times larger) and
    ``observable``. A featureless or pure-noise stack has no structure, so its offsets cannot be
    measured (``observable=False``, offsets reported as 0, ``shift_sd_px`` capped at the image
    size) — and for the
    same reason a shift cannot fatten its band, so such a stack is not refused.

    Why it matters: a per-pixel spread learned from a misaligned stack is inflated wherever the
    image has gradient (edges), so the tolerance band gets fatter and real defects there are missed.

    Raises ``ValueError`` on an empty stack, a stack that is not (n, H, W) / a list of equal
    2-D images, non-finite values, or ``max_misalign_px`` <= 0.
    """
    op = "varmodel_alignment"
    a = _stack(stack, "stack", op, min_n=1)
    tol = float(max_misalign_px)
    if not (tol > 0 and math.isfinite(tol)):
        raise ValueError("%s: max_misalign_px must be > 0, got %r" % (op, max_misalign_px))
    offs, mag, psr, sd, obs = _alignment(a, tol)
    margin = tol - mag
    return {"offset": offs, "abs_offset": mag, "margin_px": margin,
            "ok": bool((margin >= 0).all()), "worst": int(np.argmax(mag)),
            "max_misalign_px": tol, "psr": psr, "shift_sd_px": sd, "observable": obs, "reference": "registered mean of the stack (offsets relative to the median offset)",
            "n": int(a.shape[0])}


# --------------------------------------------------------------------------- #
# 2. 帯の幅 k                                                                   #
# --------------------------------------------------------------------------- #
@functools.lru_cache(maxsize=64)
def _mad_k(n, far):
    """正規の下の ``|x − med_n| / (1.4826·MAD_n)`` の上側 far 分位(モンテカルロ、固定の種)。

    ピボットなので位置と尺度によらない。標本数 M は far に合わせ、はみ出しが約 400 回になるようにする。
    """
    m_total = int(min(4_000_000, max(200_000, math.ceil(400.0 / far))))
    rng = np.random.default_rng(np.random.SeedSequence([20261018, int(n)]))
    out = np.empty(m_total)
    done = 0
    chunk = max(1, 4_000_000 // (n + 1))
    while done < m_total:
        m = min(chunk, m_total - done)
        x = rng.standard_normal((m, n + 1))
        tr = x[:, :n]
        med = np.median(tr, axis=1)
        mad = np.median(np.abs(tr - med[:, None]), axis=1) * _MAD_TO_SIGMA
        out[done:done + m] = np.abs(x[:, n] - med) / mad
        done += m
    k = float(np.quantile(out, 1.0 - far))
    rel_se = math.sqrt((1.0 - far) / (m_total * far))
    return k, m_total, rel_se


def _band_k(n, far, spread, df_prior):
    st = _stats()
    infl = math.sqrt(1.0 + 1.0 / n)
    if spread == "mad":
        k, m, rel = _mad_k(int(n), float(far))
        return {"k": k, "df": 0.0, "source": "Monte-Carlo pivot of |x - median|/(1.4826 MAD), "
                "normal good samples, %d draws" % m, "mc_far_rel_se": rel}
    if spread == "std":
        df = float(n - 1)
    elif spread == "pooled":
        df = float("inf") if df_prior is None else float(df_prior)
    else:                                   # moderated
        d0 = float("inf") if df_prior is None else float(df_prior)
        df = (n - 1) + d0
    q = float(st.norm.isf(far / 2.0)) if math.isinf(df) else float(st.t.isf(far / 2.0, df))
    return {"k": q * infl, "df": df, "source": "closed form: t quantile x sqrt(1 + 1/n) (prediction interval)",
            "mc_far_rel_se": 0.0}


def varmodel_band_k(n=20, far=1e-3, spread="std", df_prior=None):
    """Half-width ``k`` (in spread units) of the tolerance band for a declared two-sided per-pixel false-alarm rate (``table``).

    A new good pixel ``x`` is flagged when ``|x - center| > k * spread``. Under per-pixel
    independent normal good samples:

      * ``std``: ``(x - mean)/(s * sqrt(1+1/n)) ~ t_{n-1}`` so ``k = t_{n-1}^-1(1 - far/2) * sqrt(1+1/n)``.
      * ``pooled``: one variance pooled over many pixels (degrees of freedom ``df_prior``; ``None``
        = infinite) → normal quantile.
      * ``moderated``: empirical-Bayes shrunk variance with ``df_prior`` = d0 prior degrees of
        freedom (Smyth 2004) → ``t_{n-1+d0}``.
      * ``mad``: median / MAD centre and spread → no closed form, but the ratio is a pivot, so k
        is a Monte-Carlo quantile that depends on (n, far) only (fixed seed; ``mc_far_rel_se`` is
        the relative standard error of the achieved rate). Needs ``n >= 5`` and ``far >= 1e-3``.

    The threshold comes from the distribution, never from test defects. Returns ``k``, ``df``
    (0 for ``mad``: no t quantile is involved),
    ``far``, ``n``, ``spread``, ``source``, ``mc_far_rel_se``.

    Raises ``ValueError`` for ``n < 2`` (``mad``: ``n < 5``), ``far`` outside [1e-9, 0.5),
    an unknown ``spread`` or a non-positive ``df_prior``.
    """
    op = "varmodel_band_k"
    sp = _spread_kind(spread, op)
    try:
        nn = int(n)
    except (TypeError, ValueError):
        raise ValueError("%s: n must be an integer, got %r" % (op, n)) from None
    if isinstance(n, bool) or nn != n:
        raise ValueError("%s: n must be an integer, got %r" % (op, n))
    if nn < (_MAD_MIN_N if sp == "mad" else 2):
        raise ValueError("%s: n=%d is too few for spread=%r" % (op, nn, sp))
    f = _far(far, op, sp)
    if df_prior is not None and not (float(df_prior) > 0):
        raise ValueError("%s: df_prior must be > 0 or None, got %r" % (op, df_prior))
    r = _band_k(nn, f, sp, df_prior)
    r.update({"far": f, "n": nn, "spread": sp})
    return r


# --------------------------------------------------------------------------- #
# 3. 当てはめ                                                                   #
# --------------------------------------------------------------------------- #
def _trigamma_inverse(x):
    """ψ'(y) = x を y について解く(Smyth 2004 の Newton 法)。"""
    sp = _special()
    if x > 1e7:
        return 1.0 / math.sqrt(x)
    if x < 1e-6:
        return 1.0 / x
    y = 0.5 + 1.0 / x
    for _ in range(50):
        tri = float(sp.polygamma(1, y))
        dif = tri * (1.0 - tri / x) / float(sp.polygamma(2, y))
        y += dif
        if -dif / y < 1e-8:
            break
    return y


def _moderate(s2, d, use):
    """画素の標本分散 s2(自由度 d)から事前分布 (d0, s0²) を推定し、縮小した分散を返す。"""
    sp = _special()
    v = s2[use & (s2 > 0)]
    if v.size < _MIN_PRIOR_PIXELS:
        raise ValueError("varmodel_fit: spread='moderated' needs >= %d pixels with non-zero variance "
                         "to estimate the prior, got %d" % (_MIN_PRIOR_PIXELS, v.size))
    e = np.log(v) - float(sp.digamma(d / 2.0)) + math.log(d / 2.0)
    emean = float(e.mean())
    evar = float(e.var(ddof=1)) - float(sp.polygamma(1, d / 2.0))
    if evar > 0:
        d0 = 2.0 * _trigamma_inverse(evar)
        s02 = math.exp(emean + float(sp.digamma(d0 / 2.0)) - math.log(d0 / 2.0))
        post = (d0 * s02 + d * s2) / (d0 + d)
    else:                                   # 画素間の分散の違いが標本の揺れ以下 → 完全に共通
        d0 = float("inf")
        s02 = math.exp(emean)
        post = np.full_like(s2, s02)
    return post, d0, s02


def varmodel_fit(stack, spread="moderated", far=1e-3, align="check", max_misalign_px=0.5,
                 spread_floor=0.0, mask=None):
    """Learn a per-pixel variation model (centre, spread, band half-width k) from a stack of good samples (``table``).

    ``stack`` is (n, H, W) or a list of equal 2-D images, all good. ``spread`` chooses the
    estimator (``SPREADS``): ``std`` (mean / per-pixel sample std, needs n >= 3), ``pooled``
    (mean / one std for all valid pixels — few samples, homoscedastic noise), ``moderated``
    (mean / empirical-Bayes shrinkage of every pixel's variance toward a prior estimated from
    all pixels, Smyth 2004 — few samples, heteroscedastic noise; the default) or ``mad``
    (median / 1.4826 MAD — robust to a few defective images hidden in the "good" set, needs
    n >= 5). ``far`` is the declared two-sided per-pixel false-alarm rate; ``k`` follows from it
    (see ``varmodel_band_k``) and is never tuned on defects.

    Alignment: ``align="check"`` measures every sample's translation (``varmodel_alignment``)
    and REFUSES the stack if any exceeds ``max_misalign_px``; ``align="translate"`` registers the
    samples to the median by a Fourier shift (all-pass, so white noise keeps its variance),
    re-checks the residual against ``max_misalign_px`` and marks the wrapped border invalid.
    A stack without structure (``alignment["observable"]`` False) is neither refused nor shifted;
    its band is then only an intensity threshold on the overall variation. Stochastic textures,
    whose every sample shows a different pattern, are therefore not a variation-model problem
    (on DAGM 2007 Class1 it scores at chance — see the PoC).

    ``spread_floor`` (>= 0, image units) lower-bounds the spread (8-bit data has pixels whose
    good samples are all equal); any remaining zero spread is refused. ``mask`` (H, W) bool
    limits the inspected area. Returns ``center``, ``spread``, ``k``, ``far``, ``n``, ``df``,
    ``spread_kind``, ``lower`` / ``upper`` (the band), ``valid`` (bool), ``n_floored``,
    ``d0`` / ``s0`` (the prior's degrees of freedom and scale: 0 for std / mad; for pooled and a
    fully pooled moderated prior d0 = valid pixels x (n - 1)), ``k_source``,
    ``mc_far_rel_se`` and ``alignment`` (the offset report, after registration if any).

    Raises ``ValueError`` on an empty / malformed / non-finite stack, too few samples, an
    unknown ``spread`` / ``align``, ``far`` outside its range, a misaligned stack, a mask of the
    wrong shape, or zero spread left after the floor.
    """
    op = "varmodel_fit"
    sp = _spread_kind(spread, op)
    a = _stack(stack, "stack", op, min_n=_MAD_MIN_N if sp == "mad" else 3)
    n, h, w = a.shape
    f = _far(far, op, sp)
    if align not in ("check", "translate"):
        raise ValueError("%s: align must be 'check' or 'translate', got %r" % (op, align))
    tol = float(max_misalign_px)
    if not (tol > 0 and math.isfinite(tol)):
        raise ValueError("%s: max_misalign_px must be > 0, got %r" % (op, max_misalign_px))
    floor = float(spread_floor)
    if not (floor >= 0 and math.isfinite(floor)):
        raise ValueError("%s: spread_floor must be >= 0, got %r" % (op, spread_floor))
    if mask is None:
        m = np.ones((h, w), dtype=bool)
    else:
        m = np.asarray(mask)
        if m.shape != (h, w):
            raise ValueError("%s: mask %s must match the images %s" % (op, m.shape, (h, w)))
        m = m.astype(bool)
    valid = np.ones((h, w), dtype=bool)

    offs, mag, psr, sd, obs = _alignment(a, tol)
    registered = None
    if align == "check":
        if (mag > tol).any():
            bad = np.nonzero(mag > tol)[0]
            raise ValueError(
                "%s: the good samples are not aligned — %d of %d exceed max_misalign_px=%g "
                "(worst: sample %d at (%.2f, %.2f) px). A per-pixel band learned from this stack "
                "would be inflated at every edge. Register them first (align='translate') or "
                "fix the fixture." % (op, bad.size, n, tol, int(bad[np.argmax(mag[bad])]),
                                      offs[bad[np.argmax(mag[bad])], 0], offs[bad[np.argmax(mag[bad])], 1]))
    else:
        lim = min(h, w) / 4.0
        if (mag > lim).any():
            raise ValueError("%s: a sample is shifted by %.1f px (> a quarter of the image, %.1f); "
                             "translation registration is not trustworthy that far" % (op, mag.max(), lim))
        a = np.stack([_fourier_shift(a[i], -offs[i, 0], -offs[i, 1]) for i in range(n)])
        registered = offs.copy()
        offs, mag, psr, sd, obs = _alignment(a, tol)
        if (mag > tol).any():
            raise ValueError("%s: residual misalignment after registration is %.2f px (> %g); the "
                             "samples differ by more than a translation" % (op, mag.max(), tol))
        b = int(math.ceil(np.abs(registered).max())) + 1
        if np.abs(registered).max() > 0:
            valid[:b, :] = False
            valid[-b:, :] = False
            valid[:, :b] = False
            valid[:, -b:] = False
    use = valid & m
    if not use.any():
        raise ValueError("%s: no valid pixel left (mask / registered border)" % op)

    d0 = s02 = 0.0                          # std / mad: 事前分布なし(自由度 0)
    df_prior = None
    if sp == "mad":
        center = np.median(a, axis=0)
        spread_map = np.median(np.abs(a - center[None]), axis=0) * _MAD_TO_SIGMA
    else:
        center = a.mean(axis=0)
        s2 = a.var(axis=0, ddof=1)
        if sp == "std":
            spread_map = np.sqrt(s2)
        elif sp == "pooled":
            s02 = float(s2[use].mean())
            d0 = float(use.sum() * (n - 1))
            df_prior = d0
            spread_map = np.full((h, w), math.sqrt(s02))
        else:
            post, d0, s02 = _moderate(s2, n - 1, use)
            if math.isinf(d0):              # 完全に共通 = pooled と同じ: 自由度は有効画素 × (n − 1)
                d0 = float(use.sum() * (n - 1))
            df_prior = d0
            spread_map = np.sqrt(post)
    floored = use & (spread_map < floor)
    spread_map = np.maximum(spread_map, floor)
    zero = use & ~(spread_map > 0)
    if zero.any():
        raise ValueError("%s: %d valid pixels have zero spread (all good samples equal there); set "
                         "spread_floor (e.g. the quantisation step / sqrt(12)) or use spread='moderated'"
                         % (op, int(zero.sum())))
    kk = _band_k(n, f, sp, df_prior)
    k = kk["k"]
    spread_out = np.where(use, spread_map, 0.0)
    return {
        "center": center, "spread": spread_out, "k": float(k), "far": f, "n": int(n),
        "df": float(kk["df"]), "spread_kind": sp,
        "lower": np.where(use, center - k * spread_map, 0.0),
        "upper": np.where(use, center + k * spread_map, 0.0),
        "valid": use, "n_valid": int(use.sum()), "n_floored": int(floored.sum()),
        "spread_floor": floor, "d0": float(d0), "s0": float(math.sqrt(s02)),
        "k_source": kk["source"], "mc_far_rel_se": float(kk["mc_far_rel_se"]),
        "alignment": {"mode": align, "registered_offset": registered, "offset": offs,
                      "abs_offset": mag, "margin_px": tol - mag, "max_misalign_px": tol, "psr": psr,
                      "shift_sd_px": sd, "observable": obs},
    }


# --------------------------------------------------------------------------- #
# 4. 当てる・説明する                                                           #
# --------------------------------------------------------------------------- #
_MODEL_KEYS = ("center", "spread", "k", "far", "valid", "spread_kind", "n")


def varmodel_score(image, model, mask=None, align="check"):
    """Score one image against a ``varmodel_fit`` model: z map in sigmas, out-of-band map and a per-region explanation (``table``).

    ``z = (image - center) / spread`` on valid pixels (0 elsewhere); a pixel is out of band
    when ``|z| > k``. Out-of-band pixels are grouped into 8-connected regions; each region
    reports ``area``, ``peak_z`` (signed, the largest |z|), ``mean_abs_z``, ``polarity``
    (``bright`` / ``dark`` / ``mixed``), ``centroid`` (row, col), ``bbox`` (r0, c0, r1, c1,
    exclusive end) and ``peak_pos``; regions are sorted by |peak_z| (rounded to 1e-9, ties by
    label order). Also returns ``z``, ``exceed``, ``valid`` (scored pixels, image grid), ``n_exceed``, ``n_valid``, ``k``, ``far``,
    ``expected_false`` = far * n_valid and ``count_pvalue`` = P(Binomial(n_valid, far) >=
    n_exceed) — that p-value assumes independent pixels and is optimistic for spatially
    correlated noise (reported, not used to decide).

    Alignment: the image's translation against the model centre is measured as in
    ``varmodel_alignment`` and returned as ``offset``. ``align="check"`` REFUSES an image
    displaced by more than the model's ``max_misalign_px``; ``align="translate"`` registers it
    to the model by a Fourier shift, computes z in model coordinates and maps ``z`` /
    ``exceed`` back onto the image grid by the rounded offset (the wrapped border is invalid),
    so the maps line up with masks drawn on the original image. ``mask`` is on the image grid.

    Raises ``ValueError`` when ``image`` is empty / not 2-D / non-finite, its shape differs
    from the model, ``model`` lacks the fitted keys, ``mask`` has the wrong shape, ``align`` is
    unknown, or the image is misaligned (``check``) / displaced by more than a quarter of the
    image (``translate``).
    """
    op = "varmodel_score"
    img = _image(image, "image", op)
    if not isinstance(model, dict) or any(k not in model for k in _MODEL_KEYS):
        raise ValueError("%s: model must be the table returned by varmodel_fit (keys %s)" % (op, _MODEL_KEYS))
    center = np.asarray(model["center"], dtype=np.float64)
    spread = np.asarray(model["spread"], dtype=np.float64)
    valid = np.asarray(model["valid"], dtype=bool)
    if img.shape != center.shape:
        raise ValueError("%s: image %s and model %s differ in shape" % (op, img.shape, center.shape))
    k = float(model["k"])
    if not (k > 0 and math.isfinite(k)):
        raise ValueError("%s: model k must be a positive finite number, got %r" % (op, model["k"]))
    if align not in ("check", "translate"):
        raise ValueError("%s: align must be 'check' or 'translate', got %r" % (op, align))
    tol = float((model.get("alignment") or {}).get("max_misalign_px", 0.5))
    al = model.get("alignment") or {}
    if al.get("observable", True):
        rr0, cc0, _psr = _offset(center, img)
    else:                                                 # 構造の無い模型: 並進は測れず、効きもしない
        rr0 = cc0 = 0.0
    off = (rr0, cc0)
    mag = max(abs(rr0), abs(cc0))
    use = valid & (spread > 0)
    h, w = img.shape
    if align == "check":
        if mag > tol:
            raise ValueError("%s: the image is displaced by (%.2f, %.2f) px against the model "
                             "(> max_misalign_px=%g); register it (align='translate')"
                             % (op, rr0, cc0, tol))
        work = img
        ir = ic = 0
    else:
        if mag > min(h, w) / 4.0:
            raise ValueError("%s: the image is displaced by %.1f px (> a quarter of the image)" % (op, mag))
        work = _fourier_shift(img, -rr0, -cc0)
        ir, ic = int(round(rr0)), int(round(cc0))
        b = int(math.ceil(mag)) + 1
        if mag > 0:
            use = use.copy()
            use[:b, :] = False
            use[-b:, :] = False
            use[:, :b] = False
            use[:, -b:] = False
    z = np.zeros_like(img)
    z[use] = (work[use] - center[use]) / spread[use]
    if ir or ic:                                          # 模型の座標 → 画像の座標(整数の並進)
        z = np.roll(z, (ir, ic), axis=(0, 1))
        use = np.roll(use, (ir, ic), axis=(0, 1))
        if ir > 0:
            use[:ir, :] = False
        elif ir < 0:
            use[h + ir:, :] = False
        if ic > 0:
            use[:, :ic] = False
        elif ic < 0:
            use[:, w + ic:] = False
        z = np.where(use, z, 0.0)
    if mask is not None:
        mm = np.asarray(mask)
        if mm.shape != img.shape:
            raise ValueError("%s: mask %s must match the image %s" % (op, mm.shape, img.shape))
        use = use & mm.astype(bool)
        z = np.where(use, z, 0.0)
    exceed = use & (np.abs(z) > k)
    from scipy import ndimage as ndi                       # noqa: PLC0415
    lab, nreg = ndi.label(exceed, structure=np.ones((3, 3), dtype=int))
    regions = []
    if nreg:
        objs = ndi.find_objects(lab)
        for i, sl in enumerate(objs, start=1):
            sub = lab[sl] == i
            zz = z[sl][sub]
            rr, cc = np.nonzero(sub)
            j = int(np.argmax(np.abs(zz)))
            pos = int((zz > 0).sum())
            neg = int((zz < 0).sum())
            regions.append({
                "label": i, "area": int(sub.sum()), "peak_z": float(zz[j]),
                "mean_abs_z": float(np.abs(zz).mean()),
                "polarity": "bright" if neg == 0 else ("dark" if pos == 0 else "mixed"),
                "centroid": (float(rr.mean() + sl[0].start), float(cc.mean() + sl[1].start)),
                "bbox": (int(sl[0].start), int(sl[1].start), int(sl[0].stop), int(sl[1].stop)),
                "peak_pos": (int(rr[j] + sl[0].start), int(cc[j] + sl[1].start)),
            })
        regions.sort(key=lambda r: (-round(abs(r["peak_z"]), 9), r["label"]))
    nv = int(use.sum())
    ne = int(exceed.sum())
    far = float(model["far"])
    pval = float(_stats().binom.sf(ne - 1, nv, far)) if nv else 1.0
    return {"z": z, "exceed": exceed, "regions": regions, "n_regions": int(nreg),
            "n_exceed": ne, "n_valid": nv, "k": k, "far": far,
            "expected_false": far * nv, "count_pvalue": pval, "offset": off, "align": align, "valid": use,
            "max_abs_z": float(np.abs(z).max()) if nv else 0.0}


def _calibration_z_valid(image, model):
    """Return the translate-mode z map and validity mask without explanations."""
    img = _image(image, "image", "varmodel_calibrate")
    center = np.asarray(model["center"], dtype=np.float64)
    spread = np.asarray(model["spread"], dtype=np.float64)
    use = np.asarray(model["valid"], dtype=bool) & (spread > 0)
    al = model.get("alignment") or {}
    if al.get("observable", True):
        rr0, cc0, _psr = _offset(center, img)
    else:
        rr0 = cc0 = 0.0
    mag = max(abs(rr0), abs(cc0))
    h, w = img.shape
    if mag > min(h, w) / 4.0:
        raise ValueError("varmodel_score: the image is displaced by %.1f px (> a quarter of the image)" % mag)
    work = _fourier_shift(img, -rr0, -cc0)
    ir, ic = int(round(rr0)), int(round(cc0))
    b = int(math.ceil(mag)) + 1
    if mag > 0:
        use = use.copy()
        use[:b, :] = False
        use[-b:, :] = False
        use[:, :b] = False
        use[:, -b:] = False
    z = np.zeros_like(img)
    z[use] = (work[use] - center[use]) / spread[use]
    if ir or ic:
        z = np.roll(z, (ir, ic), axis=(0, 1))
        use = np.roll(use, (ir, ic), axis=(0, 1))
        if ir > 0:
            use[:ir, :] = False
        elif ir < 0:
            use[h + ir:, :] = False
        if ic > 0:
            use[:, :ic] = False
        elif ic < 0:
            use[:, w + ic:] = False
        z = np.where(use, z, 0.0)
    return z, use


def varmodel_calibrate(model, good_images, far=None):
    """Re-derive the band half-width ``k`` from held-out good images, for data that break the normal assumption (``table``).

    ``model`` is a ``varmodel_fit`` table; ``good_images`` (m, H, W) are good samples that were
    NOT used to fit it. Each is scored (``varmodel_score``, ``align="translate"``) and the
    pooled |z| of all valid pixels gives the empirical (1 - far) quantile, which replaces ``k``
    (``far`` defaults to the model's declared rate). Defects are never looked at: the threshold
    still comes from the good distribution, only measured instead of assumed. Real images break
    the per-pixel independent-normal model (residual misregistration, compression, lighting
    drift); the closed-form k then under-states the false alarms and this is the honest fix.

    Returns a copy of the model with ``k`` / ``lower`` / ``upper`` replaced and
    ``k_declared`` (the closed-form k), ``k_source`` = ``held-out quantile``,
    ``calibration_n_images``, ``calibration_n_pixels`` and ``calibration_far_declared_k``
    (the false-alarm rate the closed-form k actually had on these good images).

    Raises ``ValueError`` on an empty / malformed / non-finite set, a shape mismatch, a model
    without the fitted keys, ``far`` outside its range, or fewer than 10/far calibration pixels
    (the quantile would rest on fewer than 10 exceedances).
    """
    op = "varmodel_calibrate"
    if not isinstance(model, dict) or any(k not in model for k in _MODEL_KEYS):
        raise ValueError("%s: model must be the table returned by varmodel_fit (keys %s)" % (op, _MODEL_KEYS))
    g = _stack(good_images, "good_images", op, min_n=1)
    if g.shape[1:] != np.asarray(model["center"]).shape:
        raise ValueError("%s: good_images %s and model %s differ in shape"
                         % (op, g.shape[1:], np.asarray(model["center"]).shape))
    f = _far(model["far"] if far is None else far, op, "std")
    zs = []
    for i in range(g.shape[0]):
        z_map, valid_map = _calibration_z_valid(g[i], model)
        zs.append(np.abs(z_map[valid_map]))
    z = np.concatenate(zs) if zs else np.zeros(0)
    if z.size < 10.0 / f:
        raise ValueError("%s: %d calibration pixels are too few for far=%g (need >= %d)"
                         % (op, z.size, f, int(math.ceil(10.0 / f))))
    k_new = float(np.quantile(z, 1.0 - f))
    k_old = float(model["k"])
    out = dict(model)
    sp = np.asarray(model["spread"], dtype=np.float64)
    c = np.asarray(model["center"], dtype=np.float64)
    use = np.asarray(model["valid"], dtype=bool)
    out.update({"k": k_new, "far": f, "k_declared": k_old, "k_source": "held-out quantile of |z| on %d good images" % g.shape[0],
                "lower": np.where(use, c - k_new * sp, 0.0), "upper": np.where(use, c + k_new * sp, 0.0),
                "calibration_n_images": int(g.shape[0]), "calibration_n_pixels": int(z.size),
                "calibration_far_declared_k": float((z > k_old).mean())})
    return out
