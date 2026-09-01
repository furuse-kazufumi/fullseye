# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""astrostack —— 天体写真スタッキング。**答えが閉じた形で書ける**画像処理。

同じ空を何十枚も撮って重ねる、という手続きは天体写真の中核であり、そして
画像処理の中でも珍しく **正解が数式で書ける** 領域である。この族を選んだ理由は
「星がきれい」だからではなく、**検算できる** からだ:

  * **drizzle は面積(総フラックス)を保存する。** 入力画素を「しずく(drop)」
    として出力格子へ面積比で撒く操作なので、しずくが格子の内側に収まっている
    限り ``sci.sum()`` は入力フレームの総和平均と**厳密に**一致する
    (実測: ``pixfrac=1.0``、``scale=2`` で相対誤差 **0.0**、
    ``pixfrac=0.7`` でも 2.0e-15 = float64 の丸めそのもの。
    ``tests/test_astrostack.py`` で固定)。
  * **κ-σ 合成の破綻点は中央値と同じ 50 %。** 汚染フレームが半数を超えると、
    中央値そのものが汚染側の母集団に乗るので、クリップは**正しいフレームの方を
    捨てる**。これはバグではなく**理論の限界**であり、テストは「壊れる側」も
    そのまま残してある(隠すと、後で誰かが「直せる不具合」と誤解する)。
  * **合成星野の既知フラックス。** :func:`synth_starfield` の Gaussian PSF は
    ``erf`` による**画素の厳密な積分**で描くので、星の総フラックスは入力値と
    ぴったり一致する。半径 ``r`` の円形開口が拾う割合も閉形式
    ``1 - exp(-r^2 / (2 sigma^2))`` で分かるので、:func:`aperture_photometry`
    の返す測光値は「だいたい合っている」ではなく**何 % ずれたか**まで言える。

op は 6 家族:

  * **synth** —— :func:`synth_starfield` / :func:`synth_frame_series`:
    既知の星座標・既知フラックス・既知 PSF・既知の読み出しノイズ・既知の宇宙線を
    注入した合成フレーム。**正解の供給源**なので、この族で最初に作った。
  * **quality** —— :func:`frame_quality` / :func:`lucky_select` /
    :func:`noise_sigma`: 1 枚ごとの鋭さ・FWHM・背景・真円度から品質点を出し、
    上位 N % だけを採る(lucky imaging)。
  * **stack** —— :func:`sigma_clip_stack` / :func:`drizzle_resample`:
    κ-σ / 中央値 / 平均の合成(採否マスクつき)と、面積保存の再標本化。
  * **cosmic** —— :func:`cosmic_ray_reject` / :func:`cosmic_ray_reject_stack`:
    ラプラシアン鋭度による単一フレーム除去と、フレーム間比較による除去。
  * **photometry** —— :func:`star_detect` / :func:`psf_fit` /
    :func:`aperture_photometry`: 星の検出、ガウシアン/モファット当てはめによる
    中心と FWHM、円形開口 + 環状背景の測光。
  * **align** —— :func:`frame_align` / :func:`align_frames`: 星の対応から
    平行移動 / 剛体 / 相似変換を推定して重ね合わせる。

単位は一貫して **電子(e-)**。ADU に直したいときは gain で割ればよく、その
gain と読み出しノイズをそのまま受け取る既存 op が
:func:`photoncount.anscombe_transform`(一般化 Anscombe 変換)である。

意図的に **ここに置かないもの**(既によそが持っている —— import して合成し、
再実装はしない):

  * **ショットノイズの生成** = :func:`photoncount.photon_sample`。
    :func:`synth_starfield` は ``photons_per_unit=1.0`` で呼び、期待光子数を
    そのまま λ にする。**ノイズ理論を二重に持ち込まない**ための唯一の入口で、
    ここには Poisson 標本化のコードが 1 行も無い。
  * **読み出しノイズ** = 加法ガウス。:func:`backends_aug.aug_read_noise` は
    正規化画像 [0,1] を前提に ``clip`` するので**カウント領域では使えない**
    (電子数 1500 の星に σ=5 e- を足すと 1.0 に潰れる)。そこでここでは
    ``photoncount`` 側の一般化 Anscombe が受け取るのと**同じ意味**の
    ``read_sigma``(カウント単位の加法ガウス σ)だけを持ち、乱数は
    ``numpy.random.default_rng(seed)`` で引く。理論はあくまで
    「Poisson(信号) + Gauss(読み出し)」の 1 つだけ。
  * **宇宙線の幾何** = :func:`defectgen.defect_pits` の点過程。宇宙線ヒットは
    「稀な、小さな、鋭い、位置がランダムな傷」であり、defectgen の孔食モデルと
    同じ確率幾何なので、位置とマスクの生成はそちらに任せる(clustering=0 の
    一様点過程)。ここが持つのは**光子ではない付着**という物理だけ
    —— ショットノイズの**後**、読み出しノイズの**前**に足す。
  * **回折 PSF** = :func:`optics.airy_pattern`。ただし地上の星像を支配するのは
    回折ではなく**大気**であり、その標準モデルは Moffat (1969) である。
    :func:`synth_starfield` の ``psf="moffat"`` はそれで、回折限界の兄弟が
    optics 側にある、という棲み分け。Airy を再実装はしない。
  * **PSF から MTF** = :func:`optics.psf_to_mtf`。星像の周波数特性が要るなら
    そちらへ直接渡せる(2-D float64 なのでそのまま食える)。
  * **Poisson 逆畳み込み** = :func:`volrestore.vol_richardson_lucy`。合成後の
    デコンボリューションはあちらの仕事で、ここでは一切ぼかしを戻さない。
  * **2-D 点対応の RANSAC** = :func:`mosaic.proj_match_points_ransac`、
    **変換の当てはめ** = :func:`fit_transform.vector_to_similarity` /
    :func:`fit_transform.vector_to_rigid` / :func:`fit_transform.vector_to_hom_mat2d`。
    :func:`frame_align` はこの 2 つを import して呼ぶだけで、RANSAC ループも
    Umeyama も書いていない。
  * **特徴点記述子によるマッチング** = :func:`features.match_keypoints`。
    **星野では使えない**ので使っていない。理由は実測で、星は互いに見分けが
    つかない —— 同じ PSF の同じ形が並ぶだけなので、パッチ記述子の Lowe 比検定
    (既定 ratio=0.8)がほぼ全部を捨てる。代わりに :func:`frame_align` は
    **オフセット投票**(全ペアの差ベクトルの最頻値)で粗い平行移動を出す。
    測定値は :func:`frame_align` の docstring に書いてある。

**正直な限界**: これは*測光と重ね合わせ*のモデルであって、望遠鏡と大気の
物理シミュレータではない。``psf="moffat"`` の β は大気の実測分布ではなく
引数で与える定数だし、フラットフィールド・ダーク減算・トラッキング誤差の
時間相関は入っていない。ここで作れるのは「**この S/N・この星数・この汚染率で、
その合成アルゴリズムが正しい答えを返すか**」を問うための素材であって、
実際の観測データの代用ではない。
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage
from scipy.optimize import least_squares
from scipy.special import erf

import defectgen
import fit_transform
import mosaic
import photoncount

__all__ = [
    "synth_starfield", "synth_frame_series",
    "frame_quality", "lucky_select", "noise_sigma",
    "sigma_clip_stack", "drizzle_resample",
    "cosmic_ray_reject", "cosmic_ray_reject_stack",
    "star_detect", "psf_fit", "aperture_photometry",
    "frame_align", "align_frames",
    "ASTROSTACK", "FWHM_PER_SIGMA", "MAD_TO_SIGMA",
    "MAX_FRAMES", "MAX_IMAGE_ELEMENTS", "MAX_STARS", "MAX_OUTPUT_ELEMENTS",
    "STACK_MODES", "PSF_MODELS", "ALIGN_MODELS", "NOISE_METHODS",
]

#: ガウシアンの FWHM / sigma。**photoncount のものを再輸出**(2 つ持たない)。
FWHM_PER_SIGMA = photoncount.FWHM_PER_SIGMA

#: 中央絶対偏差 → 標準偏差(正規分布のとき)。``1 / Phi^-1(3/4)``。
MAD_TO_SIGMA = 1.4826022185056018

#: 上限。深いところで numpy / scipy が落ちる前に、名指しで拒否するため。
MAX_FRAMES = 4096
MAX_IMAGE_ELEMENTS = 1 << 24
MAX_OUTPUT_ELEMENTS = 1 << 26
MAX_STARS = 100000

STACK_MODES = ("mean", "median", "sigma_clip")
PSF_MODELS = ("gaussian", "moffat")
ALIGN_MODELS = ("translation", "rigid", "similarity", "affine")
NOISE_METHODS = ("mad", "clip")

#: MAD の**小標本補正**(Croux & Rousseeuw, *Time-Efficient Algorithms for Two
#: Highly Robust Estimators of Scale*, Computational Statistics 1992)。標本数が
#: 少ないと MAD は σ を系統的に**低く**見積もる —— 実測でも 8 フレームの背景で
#: 真値 9.22 に対し 7.89(-14.5 %)だった。これを掛けずに κ を決めると、
#: 「κ=5 のつもりで実際は κ=4.3」という静かな緩みになる。
_MAD_SMALL_SAMPLE = {2: 1.196, 3: 1.495, 4: 1.363, 5: 1.206, 6: 1.200,
                     7: 1.140, 8: 1.129, 9: 1.107}


def _mad_correction(n):
    """標本数 *n* の MAD 一致性補正係数(``n >= 10`` は ``n / (n - 0.8)``)。"""
    if n in _MAD_SMALL_SAMPLE:
        return _MAD_SMALL_SAMPLE[n]
    return n / (n - 0.8) if n > 9 else 1.0


#: van Dokkum (2001) のラプラシアン核。2 倍標本化した格子に掛ける。
_LAPLACE_KERNEL = np.array([[0.0, -1.0, 0.0],
                            [-1.0, 4.0, -1.0],
                            [0.0, -1.0, 0.0]])

#: 台帳(opsastrostack)が読む op 名の並び。
ASTROSTACK = [
    "synth_starfield", "synth_frame_series",
    "frame_quality", "lucky_select", "noise_sigma",
    "sigma_clip_stack", "drizzle_resample",
    "cosmic_ray_reject", "cosmic_ray_reject_stack",
    "star_detect", "psf_fit", "aperture_photometry",
    "frame_align", "align_frames",
]


# ---------------------------------------------------------------------------
# 入力検証(fail-closed)。defectgen / photoncount と同じ流儀で、
# 「深いところで numpy が落ちる」前に op 名つきで拒否する。
# ---------------------------------------------------------------------------
def _num(value, name, *, lo=None, hi=None, sign="positive"):
    """有限の実スカラであることを確かめて float で返す。"""
    if isinstance(value, bool) or not isinstance(value, (int, float, np.integer,
                                                        np.floating)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    v = float(value)
    if not np.isfinite(v):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if sign == "positive" and v <= 0.0:
        raise ValueError("%s must be positive, got %g" % (name, v))
    if sign == "non_negative" and v < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (name, v))
    if lo is not None and v < lo:
        raise ValueError("%s must be >= %g, got %g" % (name, lo, v))
    if hi is not None and v > hi:
        raise ValueError("%s must be <= %g, got %g" % (name, hi, v))
    return v


def _count(value, name, lo=0, hi=None):
    """非負整数(bool を除く)。"""
    if isinstance(value, bool) or int(value) != value:
        raise ValueError("%s must be an integer, got %r" % (name, value))
    v = int(value)
    if v < lo:
        raise ValueError("%s must be >= %d, got %d" % (name, lo, v))
    if hi is not None and v > hi:
        raise ValueError("%s must be <= %d, got %d" % (name, hi, v))
    return v


def _seed(value):
    return _count(value, "seed", 0)


def _shape(shape):
    """``(H, W)`` を検証して返す。"""
    try:
        h, w = shape
    except (TypeError, ValueError):
        raise ValueError("shape must be a (height, width) pair, got %r"
                         % (shape,))
    h = _count(h, "shape[0]", 2)
    w = _count(w, "shape[1]", 2)
    if h * w > MAX_IMAGE_ELEMENTS:
        raise ValueError("shape %dx%d has %d pixels, over the %d cap "
                         "(astrostack.MAX_IMAGE_ELEMENTS)"
                         % (h, w, h * w, MAX_IMAGE_ELEMENTS))
    return h, w


def _require_image(a, name, op):
    """2-D の有限 float64 画像。"""
    arr = np.asarray(a, dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError("%s: %s must be a 2-D image, got shape %r"
                         % (op, name, arr.shape))
    if arr.shape[0] < 2 or arr.shape[1] < 2:
        raise ValueError("%s: %s must be at least 2x2, got %r"
                         % (op, name, arr.shape))
    if arr.size > MAX_IMAGE_ELEMENTS:
        raise ValueError("%s: %s has %d pixels, over the %d cap "
                         "(astrostack.MAX_IMAGE_ELEMENTS)"
                         % (op, name, arr.size, MAX_IMAGE_ELEMENTS))
    if not np.isfinite(arr).all():
        raise ValueError("%s: %s has %d non-finite pixel(s)"
                         % (op, name, int((~np.isfinite(arr)).sum())))
    return np.ascontiguousarray(arr)


def _require_frames(frames, op, min_frames=2):
    """フレーム列 ``images``(2-D 配列の list / tuple)を ``(N, H, W)`` にする。

    **``(N, H, W)`` の生の 3-D 配列は受けない。** これは不便のための不便ではなく、
    この repo が ``video`` / ``voxel`` / ``zscan`` / ``histcube`` を別々の型に
    割った理由と同じ判断による —— 3-D 配列は「時間軸が先頭」「奥行きが先頭」
    「時間軸が最後」のどれでも構造検査を通ってしまい、取り違えても例外にならず
    **もっともらしく間違った合成結果**が返る。list を要求すれば、呼ぶ側が
    ``list(volume)`` と書いた瞬間に「これはフレーム列だ」と宣言したことになる。
    """
    if isinstance(frames, np.ndarray):
        raise ValueError(
            "%s: frames must be a list or tuple of 2-D images, not a raw %d-D "
            "ndarray — a 3-D array is ambiguous ((T,H,W) video, (D,H,W) volume "
            "and (H,W,T) histogram cube all pass the same structural check and "
            "would be stacked without any error. Pass list(array) to say "
            "explicitly that the first axis is the frame axis." % (op, frames.ndim))
    if not isinstance(frames, (list, tuple)):
        raise ValueError("%s: frames must be a list or tuple of 2-D images, "
                         "got %s" % (op, type(frames).__name__))
    n = len(frames)
    if n < min_frames:
        raise ValueError("%s: needs at least %d frames, got %d"
                         % (op, min_frames, n))
    if n > MAX_FRAMES:
        raise ValueError("%s: %d frames, over the %d cap "
                         "(astrostack.MAX_FRAMES)" % (op, n, MAX_FRAMES))
    out = [_require_image(f, "frames[%d]" % i, op) for i, f in enumerate(frames)]
    ref = out[0].shape
    for i, f in enumerate(out):
        if f.shape != ref:
            raise ValueError("%s: frames[%d] has shape %r but frames[0] has %r "
                             "— align them first (see frame_align / "
                             "align_frames)" % (op, i, f.shape, ref))
    return np.stack(out, axis=0)


def _require_centers(centers, op, image_shape=None):
    """``(N, 2)`` の ``(row, col)`` 中心列。``keypoints`` 語彙の形。"""
    arr = np.asarray(centers, dtype=np.float64)
    if arr.ndim == 1 and arr.size == 2:
        arr = arr.reshape(1, 2)
    if arr.ndim != 2 or arr.shape[1] != 2:
        raise ValueError("%s: centers must be (N, 2) as (row, col), got shape %r"
                         % (op, arr.shape))
    if arr.shape[0] == 0:
        raise ValueError("%s: centers is empty — nothing to measure" % op)
    if arr.shape[0] > MAX_STARS:
        raise ValueError("%s: %d centers, over the %d cap "
                         "(astrostack.MAX_STARS)" % (op, arr.shape[0], MAX_STARS))
    if not np.isfinite(arr).all():
        raise ValueError("%s: centers has non-finite coordinates" % op)
    return np.ascontiguousarray(arr)


def _choice(value, name, allowed, op):
    if value not in allowed:
        raise ValueError("%s: %s must be one of %r, got %r"
                         % (op, name, tuple(allowed), value))
    return value


# ---------------------------------------------------------------------------
# 背景と雑音(すべての op がここを通る)
# ---------------------------------------------------------------------------
def _robust_background(image, method="mad", kappa=3.0, iters=5):
    """(背景レベル, 雑音 sigma) を頑健に推定する。

    星は**上側だけの外れ値**なので、平均と標準偏差では星の明るさが背景に
    漏れる。中央値と MAD ならその漏れが無い。
    """
    x = image.ravel()
    if method == "mad":
        med = float(np.median(x))
        mad = float(np.median(np.abs(x - med)))
        return med, mad * MAD_TO_SIGMA
    # "clip": 対称な κ-σ クリップ(MAD が 0 に潰れる量子化された画像向け)
    keep = np.ones(x.size, bool)
    med = float(np.median(x))
    sig = float(np.std(x))
    for _ in range(iters):
        if keep.sum() < 4:
            break
        med = float(np.median(x[keep]))
        sig = float(np.std(x[keep]))
        if sig <= 0.0:
            break
        new = np.abs(x - med) <= kappa * sig
        if new.sum() == keep.sum():
            break
        keep = new
    return med, sig


def noise_sigma(image, method="mad", kappa=3.0, iters=5):
    """背景の雑音 sigma を頑健に推定する(星に汚されない一つの実数)。

    *method* ``"mad"`` は中央絶対偏差の ``1.4826`` 倍(正規分布のときに標準偏差と
    一致する定数)。``"clip"`` は対称な κ-σ クリップを ``iters`` 回。星は上側だけの
    外れ値なので、素の ``std`` を使うと**星が明るいほど「雑音」が大きく**なる
    —— 128x128 に 40 星(フラックス 3e3〜4e4 e-)、真の背景 σ が
    ``sqrt(100 + 36) = 11.662`` のフレームでの実測: 素の ``np.std`` は
    **175.43(真値の 15.0 倍)**、``method="mad"`` は 13.804(+18.4 %)、
    ``method="clip"`` は 12.349(+5.9 %)。MAD が 1 % で当たるのは星がまばらな
    ときだけで、**混み合った視野では星の裾が背景に効く** —— そこまで要求する
    なら ``"clip"`` を選ぶこと。桁が違うのは ``std`` だけで、そこが要点。

    ``sqrt(N)`` 則を絵にするとき図に載せる数値は、すべてこの op の返り。

    Returns ``float``(*image* と同じ単位)。

    **Raises** ``ValueError``: 2-D でない / 非有限を含む / *method* が
    :data:`NOISE_METHODS` にない場合。
    """
    img = _require_image(image, "image", "noise_sigma")
    _choice(method, "method", NOISE_METHODS, "noise_sigma")
    _num(kappa, "kappa")
    _count(iters, "iters", 1)
    return float(_robust_background(img, method, kappa, iters)[1])


# ---------------------------------------------------------------------------
# synth —— 正解の供給源
# ---------------------------------------------------------------------------
def _gaussian_star_exact(h, w, r0, c0, flux, sigma_r, sigma_c):
    """ガウシアン星を**画素の厳密な積分**で描く(``erf``、分離可能)。

    画素 ``(i, j)`` は ``[i-0.5, i+0.5) x [j-0.5, j+0.5)`` を占める(整数座標が
    画素の**中心**)。1 次元の積分は誤差関数そのものなので、超標本化の残差が
    無い —— これが「既知フラックスの測光」を厳密な検算にする鍵。
    """
    rows = np.arange(h, dtype=np.float64)
    cols = np.arange(w, dtype=np.float64)
    sr = sigma_r * np.sqrt(2.0)
    sc = sigma_c * np.sqrt(2.0)
    fr = 0.5 * (erf((rows + 0.5 - r0) / sr) - erf((rows - 0.5 - r0) / sr))
    fc = 0.5 * (erf((cols + 0.5 - c0) / sc) - erf((cols - 0.5 - c0) / sc))
    return flux * np.outer(fr, fc)


def _moffat_star(h, w, r0, c0, flux, alpha, beta, supersample=5):
    """Moffat (1969) 星像。分離できないので画素内を ``supersample^2`` 点で平均。

    無限平面での積分は ``pi alpha^2 / (beta - 1)`` なので、そこで規格化する。
    """
    s = supersample
    off = (np.arange(s, dtype=np.float64) + 0.5) / s - 0.5
    rows = (np.arange(h, dtype=np.float64)[:, None] + off[None, :]).ravel()
    cols = (np.arange(w, dtype=np.float64)[:, None] + off[None, :]).ravel()
    dr = (rows - r0) ** 2
    dc = (cols - c0) ** 2
    rr = dr[:, None] + dc[None, :]
    peak = flux * (beta - 1.0) / (np.pi * alpha * alpha)
    fine = peak * (1.0 + rr / (alpha * alpha)) ** (-beta)
    return fine.reshape(h, s, w, s).mean(axis=(1, 3))


def synth_starfield(shape=(128, 128), n_stars=30, flux_min=400.0, flux_max=9000.0,
                    fwhm_px=3.2, psf="gaussian", moffat_beta=2.5, sky=60.0,
                    read_sigma=6.0, shift_row=0.0, shift_col=0.0,
                    n_cosmic=0, cosmic_flux=4000.0, margin_px=6.0,
                    seed=0, field_seed=None, noise=True):
    """既知の星野を 1 枚合成する —— **この族の正解の供給源**。

    星は ``flux_min``〜``flux_max`` の対数一様分布から総フラックス(電子)を引き、
    画像の縁から ``margin_px`` 以上内側に一様に置く。*psf* が ``"gaussian"`` の
    ときは :func:`scipy.special.erf` による**画素の厳密な積分**なので、星 1 個の
    総和は与えたフラックスに(画像の外へ出た分を除いて)厳密に一致する。
    ``"moffat"`` は Moffat, *A Theoretical Investigation of Focal Stellar Images*,
    A&A 3, 455 (1969) の ``(1 + (r/alpha)^2)^(-beta)`` で、地上の**大気**が支配する
    星像の標準モデル(回折限界の兄弟は :func:`optics.airy_pattern`)。

    ノイズは 1 つの理論しか持たない ——
    ``Poisson(星 + sky)``(:func:`photoncount.photon_sample` を
    ``photons_per_unit=1.0`` で呼ぶ)に、**その後**で宇宙線を足し、**最後**に
    加法ガウスの読み出しノイズ ``read_sigma`` を足す。順序は物理どおりで、
    宇宙線は光子ではない(Poisson 標本化を通さない)。宇宙線の**位置**は
    :func:`defectgen.defect_pits` の一様点過程に任せる —— 「稀で小さく鋭い、
    位置がランダムな付着」は孔食と同じ確率幾何であって、二つ目のモデルを
    書く理由が無い。

    *shift_row* / *shift_col* は星野全体を副画素で動かす(ディザ)。合成した
    真値の座標もその分だけ動くので、位置合わせと drizzle の検算に使える。

    Returns ``(frame, truth)``:

    * ``frame`` —— ``(H, W)`` float64、単位は**電子**。
    * ``truth`` —— dict。``rows`` / ``cols`` ``(N,)`` は星の真の中心(整数座標が
      画素中心の規約)、``fluxes`` ``(N,)`` は真の総フラックス、``fwhm_px`` /
      ``sigma_px`` / ``alpha_px`` / ``beta`` は PSF、``sky`` / ``read_sigma`` は
      雑音、``cosmic_mask`` ``(H, W)`` bool は宇宙線の画素、``noiseless``
      ``(H, W)`` はノイズを載せる前の期待値(検算用)。

    **seed は 2 本ある。** ``field_seed`` が**星野**(座標とフラックス)を、
    ``seed`` が**その回の観測**(ショットノイズ・読み出しノイズ・宇宙線の位置)を
    決める。``field_seed=None`` なら ``seed`` と同じ値になる。分けてある理由は
    実測で見つけた事故で、1 本にしていた最初の版では
    :func:`synth_frame_series` がフレームごとに ``seed`` を変えた結果
    **星野そのものが毎フレーム別物**になり、位置合わせが 1 対応しか見つけられず
    (``frame_align`` が正しく fail-closed した)、フレーム間の宇宙線除去は
    「全画素が外れ値」を返した。同じ空を撮り直すのと、別の空を撮るのは、
    引数 1 つで取り違えられる —— だから型ではなく名前で分ける。
    乱数はどちらも ``numpy.random.default_rng`` なので、同じ seed 対なら
    どの機械でも同じフレーム。

    Ground truth it reproduces(``tests/test_astrostack.py`` で固定):
    ``noise=False``、``sky=0``、``fwhm_px=3.0`` の 1 星フレーム(64x64、
    フラックス 5000 e-)では、画像全体の総和と与えたフラックスの相対誤差が
    **1.8e-16** —— float64 の丸め 1 回ぶんで、「ほぼ保存」ではなく保存。
    半径 ``r`` の円形開口が拾う割合は ``1 - exp(-r^2/(2 sigma^2))`` で、
    ``r = 2 sigma`` なら 0.8647、``r = 3 sigma`` なら 0.98889。

    **Raises** ``ValueError``: *shape* が小さすぎる / *n_stars* が非負整数でない /
    ``flux_min > flux_max`` / *psf* が :data:`PSF_MODELS` にない /
    ``moffat_beta <= 1``(積分が発散する)/ ``margin_px`` が画像より大きい /
    *seed* が非負整数でない場合。
    """
    op = "synth_starfield"
    h, w = _shape(shape)
    n = _count(n_stars, "n_stars", 0)
    fmin = _num(flux_min, "flux_min", sign="non_negative")
    fmax = _num(flux_max, "flux_max", sign="non_negative")
    if fmax < fmin:
        raise ValueError("%s: flux_max (%g) must be >= flux_min (%g)"
                         % (op, fmax, fmin))
    fwhm = _num(fwhm_px, "fwhm_px")
    _choice(psf, "psf", PSF_MODELS, op)
    beta = _num(moffat_beta, "moffat_beta", lo=1.0000001)
    if beta <= 1.0:
        raise ValueError("%s: moffat_beta must be > 1 (the profile integral "
                         "diverges at beta <= 1), got %g" % (op, beta))
    sky_e = _num(sky, "sky", sign="non_negative")
    rsig = _num(read_sigma, "read_sigma", sign="non_negative")
    dr = _num(shift_row, "shift_row", sign="any")
    dc = _num(shift_col, "shift_col", sign="any")
    ncr = _count(n_cosmic, "n_cosmic", 0)
    cflux = _num(cosmic_flux, "cosmic_flux", sign="non_negative")
    margin = _num(margin_px, "margin_px", sign="non_negative")
    s = _seed(seed)
    fs = s if field_seed is None else _count(field_seed, "field_seed", 0)
    if 2.0 * margin >= min(h, w) - 1.0:
        raise ValueError("%s: margin_px=%g leaves no room in a %dx%d image"
                         % (op, margin, h, w))

    rng = np.random.default_rng(fs)
    sigma = fwhm / FWHM_PER_SIGMA
    alpha = fwhm / (2.0 * np.sqrt(2.0 ** (1.0 / beta) - 1.0))

    if n > 0:
        rows = rng.uniform(margin, h - 1.0 - margin, n) + dr
        cols = rng.uniform(margin, w - 1.0 - margin, n) + dc
        if fmax > fmin > 0.0:
            fluxes = np.exp(rng.uniform(np.log(fmin), np.log(fmax), n))
        else:
            fluxes = np.full(n, fmax, dtype=np.float64)
    else:
        rows = np.zeros(0); cols = np.zeros(0); fluxes = np.zeros(0)

    expected = np.full((h, w), sky_e, dtype=np.float64)
    for r0, c0, f in zip(rows, cols, fluxes):
        if psf == "gaussian":
            expected += _gaussian_star_exact(h, w, r0, c0, f, sigma, sigma)
        else:
            expected += _moffat_star(h, w, r0, c0, f, alpha, beta)
    noiseless = expected.copy()

    if noise:
        # ★ ショットノイズの唯一の入口。photons_per_unit=1 で「期待値 = lambda」。
        frame = photoncount.photon_sample(expected, photons_per_unit=1.0,
                                          dark_rate=0.0, seed=s)
    else:
        frame = expected.copy()

    cosmic_mask = np.zeros((h, w), bool)
    if ncr > 0:
        # 位置と形は defectgen の点過程に任せる(ノイズ理論も幾何も二重に持たない)
        _, cosmic_mask = defectgen.defect_pits(shape=(h, w), count=ncr,
                                               radius_px=0.9, radius_sigma=0.3,
                                               contrast=-0.3, clustering=0.0,
                                               seed=(s + 977) % (1 << 31))
        frame = frame + cosmic_mask * cflux

    if noise and rsig > 0.0:
        # 読み出しノイズ = カウント領域の加法ガウス。photoncount の一般化
        # Anscombe が受け取る read_sigma と同じ意味(aug_read_noise は [0,1] で
        # clip するのでここでは使えない — 詳細はモジュール docstring)。
        frame = frame + np.random.default_rng(s + 104729).normal(0.0, rsig, (h, w))

    truth = {
        "rows": np.ascontiguousarray(rows), "cols": np.ascontiguousarray(cols),
        "fluxes": np.ascontiguousarray(fluxes), "n_stars": int(n),
        "psf": psf, "fwhm_px": float(fwhm), "sigma_px": float(sigma),
        "alpha_px": float(alpha), "beta": float(beta),
        "sky": float(sky_e), "read_sigma": float(rsig),
        "shift_row": float(dr), "shift_col": float(dc),
        "cosmic_mask": cosmic_mask, "n_cosmic": int(ncr),
        "cosmic_flux": float(cflux),
        "noiseless": np.ascontiguousarray(noiseless),
        "shape": (h, w), "seed": int(s), "field_seed": int(fs),
    }
    return np.ascontiguousarray(frame), truth


def synth_frame_series(shape=(128, 128), n_frames=8, dither_px=1.5,
                       fwhm_px=3.2, fwhm_jitter=0.0, n_cosmic=0, seed=0,
                       **starfield_kw):
    """同じ星野を ``n_frames`` 枚、**別々のノイズと別々のディザ**で撮り直す。

    星の座標・フラックスは全フレームで同じ(``field_seed`` を固定して星の抽選を
    再現し、観測ごとの ``seed`` と ``shift_row`` / ``shift_col`` だけを振る)ので、
    位置合わせ・合成・drizzle の正解が 1 組で済む。*fwhm_jitter* を与えると FWHM がフレームごとに揺れる
    —— これが lucky imaging の「シーイングが揺らぐ」条件で、0 のままだと
    :func:`lucky_select` が選ぶ理由が無くなる。

    ディザは ``dither_px`` を半径とする決定的な螺旋(``i`` 番目のフレームを
    ``dither_px * (i / (n-1))`` の半径・黄金角の方向へ置く)。乱数でないので
    フレーム数を変えても並びが安定し、図が再現する。

    Returns ``(frames, truth)``:

    * ``frames`` —— 長さ ``n_frames`` の list、各要素は ``(H, W)`` float64。
      **``images`` 語彙そのもの**なので、合成 op へそのまま渡せる。
    * ``truth`` —— :func:`synth_starfield` の truth に、``shifts`` ``(N, 2)``
      (各フレームの ``(dr, dc)``)と ``fwhms`` ``(N,)`` を足したもの。
      ``rows`` / ``cols`` は**ディザ前**(フレーム 0 の位置)。

    **Raises** ``ValueError``: :func:`synth_starfield` の条件に加えて、
    *n_frames* が 1 未満、*dither_px* が負、*fwhm_jitter* が負の場合。
    """
    op = "synth_frame_series"
    nf = _count(n_frames, "n_frames", 1, MAX_FRAMES)
    dither = _num(dither_px, "dither_px", sign="non_negative")
    jitter = _num(fwhm_jitter, "fwhm_jitter", sign="non_negative")
    fwhm = _num(fwhm_px, "fwhm_px")
    ncr = _count(n_cosmic, "n_cosmic", 0)
    s = _seed(seed)
    if "shift_row" in starfield_kw or "shift_col" in starfield_kw:
        raise ValueError("%s: shift_row / shift_col are set per frame by "
                         "dither_px — pass dither_px instead" % op)
    if "field_seed" in starfield_kw:
        raise ValueError("%s: field_seed is pinned to seed so every frame sees "
                         "the same sky — that is what makes this a series" % op)

    golden = np.pi * (3.0 - np.sqrt(5.0))           # 黄金角(決定的な散らし)
    shifts = np.zeros((nf, 2), dtype=np.float64)
    fwhms = np.zeros(nf, dtype=np.float64)
    frames = []
    truth = None
    for i in range(nf):
        rad = dither * (i / max(1, nf - 1))
        ang = golden * i
        drow = rad * np.cos(ang)
        dcol = rad * np.sin(ang)
        # シーイングの揺らぎ: 決定的な三角波(乱数でないので図が再現する)
        f_i = fwhm * (1.0 + jitter * abs(((i * 2.0 / max(1, nf - 1)) % 2.0) - 1.0)) \
            if nf > 1 else fwhm
        # ★ field_seed は固定(同じ空)、seed だけ振る(別の観測)。
        frame, t = synth_starfield(shape=shape, fwhm_px=f_i, shift_row=drow,
                                   shift_col=dcol, n_cosmic=ncr,
                                   seed=(s + 1000 * i + 1) % (1 << 31),
                                   field_seed=s, **starfield_kw)
        frames.append(frame)
        shifts[i] = (drow, dcol)
        fwhms[i] = f_i
        if truth is None:
            truth = t
    truth = dict(truth)
    truth["rows"] = truth["rows"] - shifts[0, 0]
    truth["cols"] = truth["cols"] - shifts[0, 1]
    truth["shifts"] = shifts
    truth["fwhms"] = fwhms
    truth["n_frames"] = int(nf)
    truth.pop("shift_row", None)
    truth.pop("shift_col", None)
    return frames, truth


# ---------------------------------------------------------------------------
# photometry —— 星の検出・PSF・開口測光
# ---------------------------------------------------------------------------
def star_detect(image, threshold_sigma=5.0, min_separation=3, max_stars=200,
                edge_margin=None, centroid_box=None, method="mad"):
    """星を検出して ``(row, col)`` の重心列を返す。

    背景と雑音を :func:`noise_sigma` と同じ頑健推定で出し、
    ``background + threshold_sigma * sigma`` を超える**局所最大**を拾う
    (最大値フィルタとの一致で判定するので、``min_separation`` 画素以内に
    2 つは出ない)。中心はしきい値の画素位置ではなく、``centroid_box``
    (既定 ``2*min_separation+1``)の窓で**背景を引いた強度で重み付けした重心**
    —— これが副画素の位置精度を出す唯一の理由で、連結成分の重心
    (:func:`detect.segment_objects`)は硬いしきい値の分だけ明るさに依存して
    偏る。

    明るい順に並べて ``max_stars`` 個で打ち切る。縁から ``edge_margin``
    (既定 ``centroid_box // 2``)より内側の星だけを返す —— 窓が画像からはみ出す
    星は重心が縁側へ引っ張られるので、黙って偏った値を返すより落とす。

    Returns ``(N, 2)`` float64 ``keypoints``。1 個も無ければ ``(0, 2)``
    (空は正当な答えなので例外にしない —— 星が無い視野は存在する)。

    **Raises** ``ValueError``: 2-D でない / 非有限を含む / *threshold_sigma* が
    非正 / *min_separation* が 1 未満 / *max_stars* が 1 未満の場合。
    """
    op = "star_detect"
    img = _require_image(image, "image", op)
    thr_s = _num(threshold_sigma, "threshold_sigma")
    sep = _count(min_separation, "min_separation", 1)
    cap = _count(max_stars, "max_stars", 1, MAX_STARS)
    box = _count(centroid_box, "centroid_box", 3) if centroid_box is not None \
        else 2 * sep + 1
    half = box // 2
    margin = _count(edge_margin, "edge_margin", 0) if edge_margin is not None \
        else half
    _choice(method, "method", NOISE_METHODS, op)

    bkg, sig = _robust_background(img, method)
    if sig <= 0.0:
        # 完全に平坦 = 雑音が測れない。しきい値が定義できないので何も返さない
        # (0 で割って全画素を「星」にする方が遥かに悪い)。
        return np.empty((0, 2), dtype=np.float64)
    thresh = bkg + thr_s * sig
    mx = ndimage.maximum_filter(img, size=2 * sep + 1, mode="nearest")
    peaks = (img >= mx) & (img > thresh)
    h, w = img.shape
    peaks[:margin, :] = False
    peaks[h - margin:, :] = False if margin else peaks[h - margin:, :]
    peaks[:, :margin] = False
    peaks[:, w - margin:] = False if margin else peaks[:, w - margin:]
    rr, cc = np.nonzero(peaks)
    if rr.size == 0:
        return np.empty((0, 2), dtype=np.float64)
    order = np.argsort(-img[rr, cc])[:cap]
    rr, cc = rr[order], cc[order]

    out = np.empty((rr.size, 2), dtype=np.float64)
    rows = np.arange(box, dtype=np.float64) - half
    for k, (i, j) in enumerate(zip(rr, cc)):
        i0, i1 = i - half, i + half + 1
        j0, j1 = j - half, j + half + 1
        if i0 < 0 or j0 < 0 or i1 > h or j1 > w:
            out[k] = (float(i), float(j))
            continue
        patch = img[i0:i1, j0:j1] - bkg
        patch = np.where(patch > 0.0, patch, 0.0)
        tot = float(patch.sum())
        if tot <= 0.0:
            out[k] = (float(i), float(j))
            continue
        out[k, 0] = i + float((patch.sum(axis=1) * rows).sum() / tot)
        out[k, 1] = j + float((patch.sum(axis=0) * rows).sum() / tot)
    return out


def _psf_residual_gaussian(p, rr, cc, vals):
    amp, r0, c0, sr, sc, bkg = p
    model = bkg + amp * np.exp(-0.5 * (((rr - r0) / sr) ** 2
                                       + ((cc - c0) / sc) ** 2))
    return model - vals


def _psf_residual_moffat(p, rr, cc, vals):
    amp, r0, c0, alpha, beta, bkg = p
    rad2 = (rr - r0) ** 2 + (cc - c0) ** 2
    model = bkg + amp * (1.0 + rad2 / (alpha * alpha)) ** (-beta)
    return model - vals


def psf_fit(image, centers, model="gaussian", box=11, max_iter=200):
    """星像に PSF を当てはめて中心と FWHM を出す。

    *model* ``"gaussian"`` は**楕円**ガウシアン
    ``bkg + amp * exp(-((dr/sr)^2 + (dc/sc)^2)/2)`` の 6 パラメータ当てはめで、
    真円度(``roundness = min(sr,sc)/max(sr,sc)``)が副産物として出る ——
    追尾誤差や風で伸びた星像はここに出る。``"moffat"`` は円対称の
    ``bkg + amp * (1 + r^2/alpha^2)^(-beta)``(Moffat 1969)で、``beta`` も
    自由パラメータ。最小二乗は :func:`scipy.optimize.least_squares`
    (Trust Region Reflective)で、初期値は 2 次モーメントから作る決定的な値
    —— 乱数を使わないので同じ入力なら同じ答え。

    FWHM は当てはめたパラメータからの**閉形式**:
    ガウシアンは ``2 sqrt(2 ln 2) * sqrt(sr*sc)``(幾何平均)、Moffat は
    ``2 alpha sqrt(2^(1/beta) - 1)``。

    Returns 各星 1 つの dict の ``list``(``table`` 語彙)。キーは
    ``row`` / ``col``(当てはめた中心)、``fwhm_px``、``amplitude``、
    ``background``、``roundness``、``rms``(残差 RMS)、``converged``(bool)、
    ``model``、そして model 依存の ``sigma_row_px`` / ``sigma_col_px``
    または ``alpha_px`` / ``beta``。窓が画像からはみ出す星、当てはめが
    収束しなかった星も**落とさずに** ``converged=False`` で返す
    —— 黙って消すと「星が減った」ことに誰も気づけない。

    **Raises** ``ValueError``: *model* が :data:`PSF_MODELS` にない /
    *box* が 5 未満または偶数 / *centers* が ``(N, 2)`` でない場合。
    """
    op = "psf_fit"
    img = _require_image(image, "image", op)
    ctr = _require_centers(centers, op)
    _choice(model, "model", PSF_MODELS, op)
    b = _count(box, "box", 5)
    if b % 2 == 0:
        raise ValueError("%s: box must be odd so the star sits on a pixel "
                         "centre, got %d" % (op, b))
    _count(max_iter, "max_iter", 1)
    half = b // 2
    h, w = img.shape
    bkg0, sig0 = _robust_background(img, "mad")

    grid = np.arange(b, dtype=np.float64) - half
    rr = np.repeat(grid, b)
    cc = np.tile(grid, b)

    out = []
    for r_c, c_c in ctr:
        i, j = int(round(r_c)), int(round(c_c))
        rec = {"row": float(r_c), "col": float(c_c), "model": model,
               "converged": False, "rms": float("nan"),
               "fwhm_px": float("nan"), "amplitude": float("nan"),
               "background": float(bkg0), "roundness": float("nan")}
        if i - half < 0 or j - half < 0 or i + half + 1 > h or j + half + 1 > w:
            rec["reason"] = "box falls outside the image"
            out.append(rec)
            continue
        patch = img[i - half:i + half + 1, j - half:j + half + 1]
        vals = patch.ravel()
        # 初期値: 背景を引いた 2 次モーメント(決定的)
        pos = np.where(vals - bkg0 > 0.0, vals - bkg0, 0.0)
        tot = float(pos.sum())
        if tot <= 0.0:
            rec["reason"] = "no flux above the background in the box"
            out.append(rec)
            continue
        mr = float((pos * rr).sum() / tot)
        mc = float((pos * cc).sum() / tot)
        vr = max(0.25, float((pos * (rr - mr) ** 2).sum() / tot))
        vc = max(0.25, float((pos * (cc - mc) ** 2).sum() / tot))
        amp0 = float(vals.max() - bkg0)
        if model == "gaussian":
            p0 = [amp0, mr, mc, np.sqrt(vr), np.sqrt(vc), bkg0]
            lo = [0.0, -half, -half, 0.05, 0.05, -np.inf]
            hi = [np.inf, half, half, b * 2.0, b * 2.0, np.inf]
            fn = _psf_residual_gaussian
        else:
            beta0 = 2.5
            alpha0 = np.sqrt(0.5 * (vr + vc) * 2.0 * (beta0 - 1.0))
            p0 = [amp0, mr, mc, max(0.2, alpha0), beta0, bkg0]
            lo = [0.0, -half, -half, 0.05, 1.05, -np.inf]
            hi = [np.inf, half, half, b * 4.0, 20.0, np.inf]
            fn = _psf_residual_moffat
        try:
            res = least_squares(fn, p0, bounds=(lo, hi), args=(rr, cc, vals),
                                max_nfev=int(max_iter) * 10, method="trf")
        except Exception as exc:                    # honest: 失敗を隠さない
            rec["reason"] = "least_squares failed: %s" % exc
            out.append(rec)
            continue
        p = res.x
        rec["converged"] = bool(res.success)
        rec["rms"] = float(np.sqrt(np.mean(res.fun ** 2)))
        rec["amplitude"] = float(p[0])
        rec["row"] = float(i + p[1])
        rec["col"] = float(j + p[2])
        rec["background"] = float(p[5])
        if model == "gaussian":
            sr, sc = abs(float(p[3])), abs(float(p[4]))
            rec["sigma_row_px"] = sr
            rec["sigma_col_px"] = sc
            rec["fwhm_px"] = float(FWHM_PER_SIGMA * np.sqrt(sr * sc))
            rec["roundness"] = float(min(sr, sc) / max(sr, sc)) if max(sr, sc) > 0 \
                else float("nan")
        else:
            alpha, beta = abs(float(p[3])), float(p[4])
            rec["alpha_px"] = alpha
            rec["beta"] = beta
            rec["fwhm_px"] = float(2.0 * alpha
                                   * np.sqrt(2.0 ** (1.0 / beta) - 1.0))
            rec["roundness"] = 1.0            # 円対称モデルなので定義上 1
        rec["snr_peak"] = float(p[0] / sig0) if sig0 > 0 else float("inf")
        out.append(rec)
    return out


def _circle_weights(h, w, r0, c0, radius, supersample):
    """円形開口の画素重み(``supersample^2`` 点の副画素標本化)。"""
    s = int(supersample)
    off = (np.arange(s, dtype=np.float64) + 0.5) / s - 0.5
    i0 = max(0, int(np.floor(r0 - radius - 1)))
    i1 = min(h, int(np.ceil(r0 + radius + 2)))
    j0 = max(0, int(np.floor(c0 - radius - 1)))
    j1 = min(w, int(np.ceil(c0 + radius + 2)))
    if i1 <= i0 or j1 <= j0:
        return np.zeros((h, w)), (0, 0, 0, 0)
    rows = (np.arange(i0, i1, dtype=np.float64)[:, None] + off[None, :]).ravel()
    cols = (np.arange(j0, j1, dtype=np.float64)[:, None] + off[None, :]).ravel()
    dr2 = (rows - r0) ** 2
    dc2 = (cols - c0) ** 2
    inside = (dr2[:, None] + dc2[None, :]) <= radius * radius
    sub = inside.reshape(i1 - i0, s, j1 - j0, s).mean(axis=(1, 3))
    wgt = np.zeros((h, w), dtype=np.float64)
    wgt[i0:i1, j0:j1] = sub
    return wgt, (i0, i1, j0, j1)


def aperture_photometry(image, centers, r_aperture=5.0, r_inner=8.0,
                        r_outer=12.0, read_sigma=0.0, gain=1.0, supersample=8):
    """円形開口 + 環状背景の測光(古典的な CCD 測光)。

    開口内の画素は**副画素で重み付け**する(``supersample^2`` 点の標本化)ので、
    半径が整数でなくても面積が階段状に飛ばない。背景は ``r_inner``〜``r_outer``
    の環の**中央値**(隣の星が環に入っても引きずられない)。

    フラックスは ``sum(w * (I - background))``、S/N は古典的な CCD 方程式
    (Merline & Howell, *Exp. Astron.* 6, 163 (1995); Howell, *Handbook of CCD
    Astronomy*)::

        SNR = F / sqrt(F/gain + A*(B/gain + read_sigma^2))

    ここで ``A`` は開口の実効画素数、``B`` は背景レベル。``read_sigma=0`` かつ
    ``gain=1`` なら純 Poisson の ``F/sqrt(F + A*B)`` に落ちる。

    Returns 各星 1 つの dict の ``list``(``table`` 語彙)。キーは ``row`` /
    ``col`` / ``flux`` / ``background``(1 画素あたり)/ ``area_px``(開口の実効
    画素数)/ ``n_annulus`` / ``snr`` / ``flux_error`` / ``mag_instrumental``
    (``-2.5 log10(flux)``、フラックスが非正なら ``nan``)。

    Ground truth it reproduces(``tests/test_astrostack.py``): ノイズ無しの
    ガウシアン星(フラックス 10000 e-)に対して、半径 ``r`` の開口が拾う割合は
    ``1 - exp(-r^2/(2 sigma^2))``。**開口を広げれば厳密に一致する** ——
    ``r = 8 sigma`` では sigma = 1.0 / 1.5 / 2.0 / 3.0 のどれでも
    測定 10000.00000、誤差 -0.0000 %。

    **小さい開口には系統的な負のずれが残る、という正直な話。** ``r = 3 sigma``
    では実測が理論を下回る::

        sigma = 1.0  ->  9798.57 / 9888.91  = -0.914 %
        sigma = 1.5  ->  9850.70 / 9888.91  = -0.386 %
        sigma = 2.0  ->  9868.61 / 9888.91  = -0.205 %
        sigma = 3.0  ->  9879.86 / 9888.91  = -0.092 %

    これはバグではなく**画素化そのもの**。閉形式は連続なガウシアンを円で積分した
    値だが、こちらは「画素の総フラックス × 円に入る面積の割合」を足している。
    開口の縁にある画素では、円の内側(中心寄り)の方が実際には明るいので、
    画素平均で代表すると必ず**少なく**出る。誤差が ``sigma`` の 2 乗に反比例
    して減る(1.0→3.0 で 10 倍)のがその証拠で、標本化が良くなるほど画素平均と
    真の分布の差が縮む。開口を広げれば縁の画素の寄与自体が消えるので誤差も消える。

    ``supersample`` は**円の面積**の離散化だけを直す(実測: ``r=4.5`` で
    ``pi r^2`` に対し相対 1.6e-3、``r=3`` で 2.5e-4)。上のずれとは別の話で、
    上げても縁の画素平均の偏りは消えない。

    **Raises** ``ValueError``: 半径の順序が ``0 < r_aperture <= r_inner <
    r_outer`` でない / *supersample* が 1 未満 / *gain* が非正 /
    *centers* が ``(N, 2)`` でない場合。
    """
    op = "aperture_photometry"
    img = _require_image(image, "image", op)
    ctr = _require_centers(centers, op)
    ra = _num(r_aperture, "r_aperture")
    ri = _num(r_inner, "r_inner")
    ro = _num(r_outer, "r_outer")
    rsig = _num(read_sigma, "read_sigma", sign="non_negative")
    g = _num(gain, "gain")
    ss = _count(supersample, "supersample", 1, 32)
    if not (ra <= ri < ro):
        raise ValueError("%s: radii must satisfy 0 < r_aperture (%g) <= "
                         "r_inner (%g) < r_outer (%g)" % (op, ra, ri, ro))
    h, w = img.shape
    rows = np.arange(h, dtype=np.float64)[:, None]
    cols = np.arange(w, dtype=np.float64)[None, :]

    out = []
    for r0, c0 in ctr:
        wgt, _ = _circle_weights(h, w, r0, c0, ra, ss)
        area = float(wgt.sum())
        rad2 = (rows - r0) ** 2 + (cols - c0) ** 2
        ann = (rad2 >= ri * ri) & (rad2 <= ro * ro)
        n_ann = int(ann.sum())
        bkg = float(np.median(img[ann])) if n_ann > 0 else 0.0
        flux = float((wgt * (img - bkg)).sum())
        var = max(0.0, flux) / g + area * (max(0.0, bkg) / g + rsig * rsig)
        err = float(np.sqrt(var)) if var > 0 else 0.0
        snr = float(flux / err) if err > 0 else float("inf")
        out.append({
            "row": float(r0), "col": float(c0), "flux": flux,
            "background": bkg, "area_px": area, "n_annulus": n_ann,
            "flux_error": err, "snr": snr,
            "mag_instrumental": float(-2.5 * np.log10(flux)) if flux > 0
            else float("nan"),
            "r_aperture": ra, "r_inner": ri, "r_outer": ro,
        })
    return out


# ---------------------------------------------------------------------------
# quality —— lucky imaging の選別
# ---------------------------------------------------------------------------
def frame_quality(image, threshold_sigma=5.0, max_stars=25, min_separation=3,
                  psf_box=11, n_score_stars=5):
    """1 枚の品質を数える —— 鋭さ・FWHM・背景・真円度、そして選別用の点。

    lucky imaging の選別基準は歴史的に **「基準星のピーク強度」** である
    (Law, Mackay & Baldwin, *Lucky imaging: high angular resolution imaging in
    the visible from the ground*, A&A 446, 739 (2006))—— 大気が良い瞬間ほど
    同じ総フラックスが少ない画素に集まるので、``ピーク / 総フラックス`` が
    上がる。ここでもそれを採り、追尾の伸びを弾くために真円度を掛ける::

        score = median(roundness) * median(peak_fraction)

    ``peak_fraction`` は明るい方から ``n_score_stars`` 個の星について
    ``(ピーク画素 - 背景) / 開口フラックス``。**尺度に依らない**(露出時間や
    ゲインを変えても動かない)ので、フレーム間の比較にそのまま使える。

    ``sharpness`` は別に、ラプラシアンの分散を画像の分散で割った古典的な
    合焦指標(Pech-Pacheco et al., *Diatom autofocusing in brightfield
    microscopy*, ICPR 2000)。星の数が変わると動くので**選別には使わない**が、
    星が 1 つも無いフレームでも値が出る唯一の指標なので残してある。

    Returns dict(``table`` 語彙)。キーは ``n_stars`` / ``background`` /
    ``noise_sigma`` / ``fwhm_px``(検出星の FWHM 中央値)/ ``roundness`` /
    ``peak_fraction`` / ``peak_snr`` / ``sharpness`` / ``score`` /
    ``total_flux``。星が 1 つも無いときは星由来の値が ``nan``、``score`` は
    ``0.0``(「選ばない」が正しい答えなので、``nan`` で並べ替えを壊さない)。

    **Raises** ``ValueError``: 2-D でない / 非有限を含む / *n_score_stars* が
    1 未満の場合。
    """
    op = "frame_quality"
    img = _require_image(image, "image", op)
    nsc = _count(n_score_stars, "n_score_stars", 1)
    bkg, sig = _robust_background(img, "mad")
    lap = ndimage.laplace(img)
    var = float(np.var(img))
    sharp = float(np.var(lap) / var) if var > 0 else 0.0

    rec = {"n_stars": 0, "background": float(bkg), "noise_sigma": float(sig),
           "fwhm_px": float("nan"), "roundness": float("nan"),
           "peak_fraction": float("nan"), "peak_snr": float("nan"),
           "sharpness": sharp, "score": 0.0,
           "total_flux": float((img - bkg).sum())}

    stars = star_detect(img, threshold_sigma=threshold_sigma,
                        min_separation=min_separation, max_stars=max_stars,
                        centroid_box=psf_box)
    rec["n_stars"] = int(stars.shape[0])
    if stars.shape[0] == 0:
        return rec

    fits = psf_fit(img, stars, model="gaussian", box=psf_box)
    fwhms = np.array([f["fwhm_px"] for f in fits], dtype=np.float64)
    rounds = np.array([f["roundness"] for f in fits], dtype=np.float64)
    ok = np.isfinite(fwhms) & np.isfinite(rounds)
    if ok.any():
        rec["fwhm_px"] = float(np.median(fwhms[ok]))
        rec["roundness"] = float(np.median(rounds[ok]))

    r_ap = max(2.0, 1.5 * (rec["fwhm_px"] if np.isfinite(rec["fwhm_px"]) else 3.0))
    phot = aperture_photometry(img, stars[:nsc], r_aperture=r_ap,
                               r_inner=r_ap + 2.0, r_outer=r_ap + 6.0)
    peaks, snrs = [], []
    h, w = img.shape
    for p in phot:
        i, j = int(round(p["row"])), int(round(p["col"]))
        i0, i1 = max(0, i - 1), min(h, i + 2)
        j0, j1 = max(0, j - 1), min(w, j + 2)
        peak = float(img[i0:i1, j0:j1].max() - p["background"])
        if p["flux"] > 0.0:
            peaks.append(peak / p["flux"])
        if sig > 0.0:
            snrs.append(peak / sig)
    if peaks:
        rec["peak_fraction"] = float(np.median(peaks))
    if snrs:
        rec["peak_snr"] = float(np.median(snrs))
    if np.isfinite(rec["peak_fraction"]) and np.isfinite(rec["roundness"]):
        rec["score"] = float(max(0.0, rec["roundness"] * rec["peak_fraction"]))
    return rec


def lucky_select(frames, keep_fraction=0.3, min_keep=1, **quality_kw):
    """品質点の上位 ``keep_fraction`` だけを採る —— lucky imaging の選別。

    採用枚数は ``max(min_keep, ceil(keep_fraction * N))``。**必ず 1 枚は残す**
    ので、``keep_fraction`` をいくら小さくしても空にはならない(空の合成を
    後段へ渡す方が事故が大きい)。並べ替えは点の降順で、同点は元の順序を保つ
    安定ソート —— 同じ入力なら同じ並びが返る。

    Returns ``(indices, scores)``:

    * ``indices`` —— ``(K,)`` int64、**採用フレームの添字を良い順に**
      (``indices`` 語彙)。``[frames[i] for i in indices]`` がそのまま
      :func:`sigma_clip_stack` へ渡せる。
    * ``scores`` —— ``(N,)`` float64、**全フレームの点**(捨てた側も含む)。
      捨てた理由を図にできるように、選別の結果ではなく素材を返す。

    Ground truth it reproduces(``tests/test_astrostack.py``): 同じ星野を
    FWHM だけ変えて撮ったフレーム列では、点は FWHM の**単調減少関数**になる
    —— 実測で FWHM 2.4 / 3.2 / 4.4 px の 3 枚の点は 0.0669 / 0.0416 / 0.0234
    と順序どおりに並ぶ。

    **Raises** ``ValueError``: *frames* が list / tuple でない(3-D 配列は
    明示的に拒否)/ 枚数が 1 未満 / ``keep_fraction`` が (0, 1] の外 /
    *min_keep* が枚数を超える場合。
    """
    op = "lucky_select"
    stack = _require_frames(frames, op, min_frames=1)
    kf = _num(keep_fraction, "keep_fraction", lo=1e-9, hi=1.0)
    n = stack.shape[0]
    mk = _count(min_keep, "min_keep", 1)
    if mk > n:
        raise ValueError("%s: min_keep=%d but only %d frame(s) were given"
                         % (op, mk, n))
    scores = np.array([frame_quality(stack[i], **quality_kw)["score"]
                       for i in range(n)], dtype=np.float64)
    k = int(max(mk, int(np.ceil(kf * n))))
    k = min(k, n)
    order = np.argsort(-scores, kind="stable")[:k]
    return np.ascontiguousarray(order.astype(np.int64)), scores


# ---------------------------------------------------------------------------
# stack —— κ-σ 合成と drizzle
# ---------------------------------------------------------------------------
def sigma_clip_stack(frames, mode="sigma_clip", kappa=3.0, iters=5,
                     center="median", scale="mad"):
    """フレーム列を合成する(平均 / 中央値 / κ-σ クリップ)。採否マスクつき。

    *mode*:

    * ``"mean"`` —— 単純平均。雑音は ``sqrt(N)`` で下がるが、外れ値(宇宙線・
      人工衛星の航跡)は ``1/N`` しか薄まらず**必ず残る**。
    * ``"median"`` —— 中央値。外れ値に強い代わりに、正規分布のとき雑音は
      平均の ``sqrt(pi/2) = 1.2533`` 倍しか下がらない(= 実効的に 36 % 枚数を
      捨てている)。
    * ``"sigma_clip"`` —— 中央値を中心、``scale`` を尺度として
      ``|x - center| > kappa * scale`` を落とし、残りで平均を取る。これを
      ``iters`` 回。外れ値に強く、かつ生き残った画素は平均されるので雑音も
      ``sqrt(N_accepted)`` で下がる —— 実用の既定。

    **破綻点は 50 %。** 中心を中央値、尺度を MAD で取る以上、汚染フレームが
    半数を超えた画素では中央値そのものが汚染側に乗り、クリップは**正しい方**を
    捨てる。これはこの実装の不具合ではなく中央値の定義そのもので、
    ``center="mean"`` にすればもっと早く(汚染 1 枚でも)壊れる。テストは
    0〜60 % の汚染率で誤差を測り、**壊れる側もそのまま残してある**。

    **``scale`` の既定が ``"mad"`` なのは実測の結果。** ``scale="std"`` は
    「外れ値を見つけるための尺度を、その外れ値自身が膨らませる」ので、汚染が
    増えるとむしろ**何も落とさなくなる** —— 20 枚中 4 枚(20 %)に +500 の
    汚染を入れた実測では、``std`` 版は棄却率 0.0 % で誤差 +100.0(= 単純平均と
    完全に同じ)、``mad`` 版は棄却率 20.0 % で誤差 +0.004 だった。破綻点は
    ``std`` で 10 % 台、``mad`` で 50 % と、5 倍近く違う。

    Returns ``(stack, accepted)``:

    * ``stack`` —— ``(H, W)`` float64。
    * ``accepted`` —— ``(N, H, W)`` bool、``True`` = **採用**した画素。
      ``mode="mean"`` / ``"median"`` では全 ``True``(どちらもクリップしない
      ので、「採否」の概念が無いことを ``False`` が 1 つも無いことで示す)。

    **Raises** ``ValueError``: *frames* が list / tuple でない / 枚数が 2 未満 /
    形が揃っていない / *mode* が :data:`STACK_MODES` にない / *kappa* が非正 /
    *center* が ``"median"`` / ``"mean"`` 以外 / *scale* が ``"std"`` /
    ``"mad"`` 以外の場合。
    """
    op = "sigma_clip_stack"
    cube = _require_frames(frames, op, min_frames=2)
    _choice(mode, "mode", STACK_MODES, op)
    _choice(center, "center", ("median", "mean"), op)
    _choice(scale, "scale", ("std", "mad"), op)
    k = _num(kappa, "kappa")
    it = _count(iters, "iters", 1)
    n = cube.shape[0]

    if mode == "mean":
        return cube.mean(axis=0), np.ones(cube.shape, dtype=bool)
    if mode == "median":
        return np.median(cube, axis=0), np.ones(cube.shape, dtype=bool)

    accepted = np.ones(cube.shape, dtype=bool)
    for _ in range(it):
        masked = np.where(accepted, cube, np.nan)
        with np.errstate(invalid="ignore"):
            if center == "median":
                ctr = np.nanmedian(masked, axis=0)
            else:
                ctr = np.nanmean(masked, axis=0)
            if scale == "std":
                sc = np.nanstd(masked, axis=0)
            else:
                sc = MAD_TO_SIGMA * np.nanmedian(np.abs(masked - ctr), axis=0)
        sc = np.where(np.isfinite(sc) & (sc > 0.0), sc, np.inf)
        new = np.abs(cube - ctr) <= k * sc
        # 全部落ちる画素を作らない(最低 1 枚は残す = 答えが nan にならない)
        empty = ~new.any(axis=0)
        if empty.any():
            best = np.argmin(np.abs(cube - ctr), axis=0)
            fix = np.zeros(cube.shape, dtype=bool)
            np.put_along_axis(fix, best[None, :, :], True, axis=0)
            new = np.where(empty[None, :, :], fix, new)
        if np.array_equal(new, accepted):
            break
        accepted = new
    cnt = accepted.sum(axis=0)
    tot = np.where(accepted, cube, 0.0).sum(axis=0)
    stack = tot / np.maximum(cnt, 1)
    return np.ascontiguousarray(stack), accepted


def _drop_overlap(n_in, n_out, shift, scale, pixfrac):
    """1 軸ぶんの「しずく × 出力画素」重なり長 ``(n_in, n_out)`` を作る。

    入力画素 ``i`` は ``[i-0.5, i+0.5]`` を占める(整数座標が画素中心)。
    しずくは中心 ``i + shift``、幅 ``pixfrac``。出力画素 ``p`` は
    ``[-0.5 + p/scale, -0.5 + (p+1)/scale]``。平行移動だけなら軸が分離するので、
    2 次元の重なり面積は 2 本の重なり長の積になる —— drizzle が
    **面積(総フラックス)を保存する**のはこの分離のおかげで、補間ではない。
    """
    lo_in = np.arange(n_in, dtype=np.float64) + shift - 0.5 * pixfrac
    hi_in = lo_in + pixfrac
    lo_out = -0.5 + np.arange(n_out, dtype=np.float64) / scale
    hi_out = lo_out + 1.0 / scale
    ov = np.minimum(hi_in[:, None], hi_out[None, :]) \
        - np.maximum(lo_in[:, None], lo_out[None, :])
    return np.where(ov > 0.0, ov, 0.0)


def drizzle_resample(frames, shifts=None, scale=2.0, pixfrac=1.0):
    """Drizzle —— 副画素でずれた複数フレームから細かい格子を作る(面積保存)。

    Fruchter & Hook, *Drizzle: A Method for the Linear Reconstruction of
    Undersampled Images*, PASP 114, 144 (2002)。入力画素を一回り縮めた
    「しずく(drop、辺 ``pixfrac``)」とみなし、出力格子の画素との**重なり面積**
    に比例してフラックスを撒く。補間しないので、

    * **総フラックスが保存される。** しずくが出力格子の内側に収まっている限り
      ``sci.sum()`` は入力フレームの総和の平均と厳密に一致する
      (実測: ``shifts=0``、``scale=2``、``pixfrac=0.7`` で相対誤差 0.0)。
      これが**返り値だけで検算できる**形にしてある理由。
    * ``pixfrac`` を小さくするほど、しずくが出力画素の内側に入る割合が増えて
      **解像度は上がるが、覆われない出力画素が出る**(``wht`` がそこで小さく
      なる)。この綱引きが drizzle の唯一の調整点。

    *shifts* は ``(N, 2)`` の ``(dr, dc)`` で、フレーム ``i`` が基準からどれだけ
    ずれているか(:func:`synth_frame_series` の ``truth["shifts"]``、
    :func:`frame_align` の推定値をそのまま渡せる)。``None`` なら全部 0。
    **回転は受けない** —— 回転が入ると軸が分離せず重なり面積が閉形式で書けなく
    なるので、先に :func:`align_frames` で戻すこと(そこで補間の誤差を払う、
    という取引が見えている方が正直)。

    Returns ``(sci, wht)``:

    * ``sci`` —— ``(round(H*scale), round(W*scale))`` float64、**総フラックス
      単位**(入力と同じ電子)。格子の外へ出たしずくの分だけ総和が減るので、
      ``sci.sum()`` と入力総和の差は「縁で失った量」そのもの。
    * ``wht`` —— 同じ形の重みマップ。出力画素が何枚ぶんのしずくに覆われたか
      (出力画素面積を 1 とする)。``pixfrac=1`` かつ ``shifts=0`` なら内部は
      厳密に 1.0。

    **Raises** ``ValueError``: *frames* が list / tuple でない / 形が揃って
    いない / *scale* が 1 未満 / *pixfrac* が (0, 1] の外 / *shifts* の形が
    ``(N, 2)`` でない / 出力が :data:`MAX_OUTPUT_ELEMENTS` を超える場合。
    """
    op = "drizzle_resample"
    cube = _require_frames(frames, op, min_frames=1)
    sc = _num(scale, "scale", lo=1.0)
    pf = _num(pixfrac, "pixfrac", lo=1e-6, hi=1.0)
    n, h, w = cube.shape
    if shifts is None:
        sh = np.zeros((n, 2), dtype=np.float64)
    else:
        sh = np.asarray(shifts, dtype=np.float64)
        if sh.shape != (n, 2):
            raise ValueError("%s: shifts must be (N, 2) = (dr, dc) per frame, "
                             "got shape %r for %d frames" % (op, sh.shape, n))
        if not np.isfinite(sh).all():
            raise ValueError("%s: shifts has non-finite entries" % op)
    ho, wo = int(round(h * sc)), int(round(w * sc))
    if ho * wo > MAX_OUTPUT_ELEMENTS:
        raise ValueError("%s: output %dx%d has %d pixels, over the %d cap "
                         "(astrostack.MAX_OUTPUT_ELEMENTS)"
                         % (op, ho, wo, ho * wo, MAX_OUTPUT_ELEMENTS))

    num = np.zeros((ho, wo), dtype=np.float64)
    den = np.zeros((ho, wo), dtype=np.float64)
    drop_area = pf * pf
    out_area = 1.0 / (sc * sc)
    for i in range(n):
        wr = _drop_overlap(h, ho, -sh[i, 0], sc, pf)
        wc = _drop_overlap(w, wo, -sh[i, 1], sc, pf)
        # フラックスの配分: 重なり面積 / しずく面積(内側なら和は厳密に 1)
        num += wr.T @ cube[i] @ wc / drop_area
        # 被覆: 重なり面積 / 出力画素面積
        den += (wr.sum(axis=0)[:, None] * wc.sum(axis=0)[None, :]) / out_area
    return np.ascontiguousarray(num / n), np.ascontiguousarray(den / n)


# ---------------------------------------------------------------------------
# cosmic —— 宇宙線
# ---------------------------------------------------------------------------
def cosmic_ray_reject(frame, sigma=5.0, f_lim=2.0, replace_box=5, iters=1):
    """単一フレームの宇宙線除去(ラプラシアン鋭度)。

    van Dokkum, *Cosmic-Ray Rejection by Laplacian Edge Detection*,
    PASP 113, 1420 (2001) の考え方 —— 宇宙線は**星より鋭い**。星は PSF で
    ぼけているので必ず数画素にまたがるが、宇宙線は光学系を通っていないので
    1〜数画素で立ち上がる。そこで

    1. ラプラシアン ``L`` の正の成分を雑音で規格化した有意度
       ``S = L / (2 sigma_noise)`` を作り、
    2. 微細構造像 ``F = median3 - median7(median3)`` と比べて ``L / F`` が
       ``f_lim`` を超えるものだけを宇宙線とする。

    2 番目の条件が無いと**星の中心が必ず宇宙線に見える**(星も局所的には
    尖っている)。``f_lim`` はその境目で、原論文の推奨は 2.0。

    ``iters`` を増やすと、除去 → 再測定を繰り返す(大きなヒットの裾が残るとき)。
    置換は ``replace_box`` の窓での**非汚染画素の中央値**。

    Returns ``(cleaned, mask)``:

    * ``cleaned`` —— ``(H, W)`` float64、宇宙線画素を置換した像。
    * ``mask`` —— ``(H, W)`` bool、``True`` = 宇宙線と判定した画素。

    **Raises** ``ValueError``: 2-D でない / 非有限を含む / *sigma* が非正 /
    *f_lim* が非正 / *replace_box* が 3 未満または偶数の場合。
    """
    op = "cosmic_ray_reject"
    img = _require_image(frame, "frame", op)
    s_thr = _num(sigma, "sigma")
    fl = _num(f_lim, "f_lim")
    rb = _count(replace_box, "replace_box", 3)
    if rb % 2 == 0:
        raise ValueError("%s: replace_box must be odd, got %d" % (op, rb))
    it = _count(iters, "iters", 1)

    work = img.copy()
    mask = np.zeros(img.shape, dtype=bool)
    h, w = img.shape
    for _ in range(it):
        _, noise = _robust_background(work, "mad")
        if noise <= 0.0:
            break
        # 2 倍に複製標本化してからラプラシアン → 正の成分だけを 2x2 平均で戻す。
        # 原論文がこの順序を採るのは、素の格子でラプラシアンを取ると**星の中心が
        # 必ず尖って見える**ため(実測: 素の格子だと適合率 0.28、この経路で 0.79)。
        up = np.repeat(np.repeat(work, 2, axis=0), 2, axis=1)
        lap_up = ndimage.convolve(up, _LAPLACE_KERNEL, mode="nearest")
        lap_up = np.where(lap_up > 0.0, lap_up, 0.0)
        lap = lap_up.reshape(h, 2, w, 2).mean(axis=(1, 3))
        sig_map = lap / (2.0 * noise)
        m3 = ndimage.median_filter(work, size=3, mode="nearest")
        fine = m3 - ndimage.median_filter(m3, size=7, mode="nearest")
        # 微細構造の床は雑音そのもの。0 近くで割ると平坦な背景の 1 画素の揺らぎが
        # 無限大の比になる(最初の版はこれで偽陽性が 100 画素出た)。
        fine = np.where(fine > noise, fine, noise)
        hit = (sig_map > s_thr) & (lap / fine > fl)
        if not hit.any():
            break
        mask |= hit
        med = ndimage.median_filter(work, size=rb, mode="nearest")
        work = np.where(hit, med, work)
    return np.ascontiguousarray(work), mask


def cosmic_ray_reject_stack(frames, kappa=5.0, min_frames=3, read_sigma=None,
                            gain=1.0):
    """フレーム間比較による宇宙線除去 —— **同じ場所に二度は当たらない**。

    宇宙線が単一フレームの検出で難しいのは「星も尖っている」からだが、
    位置合わせ済みのフレームが何枚もあれば話は簡単になる: 星は**毎回同じ画素**
    に居て、宇宙線は**一度しか来ない**。そこで画素ごとにフレーム方向の中央値と
    MAD を取り、``value > median + kappa * sigma`` のフレームだけを落として
    中央値で埋める(下側は落とさない —— 宇宙線は必ず**足す**方向の外れ値で、
    下側を落とすと欠損画素まで消してしまう)。

    ``min_frames`` 枚未満では中央値も MAD も意味を成さないので拒否する
    (3 枚が最低限: 2 枚だとどちらが外れ値か決まらない)。**フレームは位置合わせ
    済みであること** —— ずれたまま渡すと星が「一度しか来ない」ことになり、
    星の方が消える。

    **枚数が少ないと MAD 自体が当てにならない、という実測。** 8 枚の背景で
    MAD 推定は真の σ 9.22 に対し 7.89(-14.5 %)、しかも画素ごとに大きく散る
    ので、``kappa=5`` のつもりが実質 4.3 になり、偽陽性が真陽性の 2.4 倍
    (546 対 227 画素)出た。対策は 2 つ重ねてある:

    1. :func:`_mad_correction`(Croux & Rousseeuw 1992)の小標本補正を掛ける。
    2. *read_sigma* を渡すと、**このモジュールが持つ唯一のノイズモデル**
       ``sigma = sqrt(median/gain + read_sigma^2)`` を尺度の**床**にする。
       これは :func:`synth_starfield` が使っているのと同じ
       「Poisson(信号) + Gauss(読み出し)」で、二つ目の理論ではない。
       床を入れると、標本のゆらぎで MAD がたまたま小さく出た画素が
       宇宙線に化けることが無くなる。

    Returns ``(cleaned, masks)``:

    * ``cleaned`` —— 長さ ``N`` の list、各 ``(H, W)`` float64(``images`` 語彙)。
    * ``masks`` —— ``(N, H, W)`` bool、``True`` = 宇宙線と判定した画素。

    **Raises** ``ValueError``: *frames* が list / tuple でない / 枚数が
    *min_frames* 未満 / 形が揃っていない / *kappa* が非正 / *gain* が非正 /
    *read_sigma* が負の場合。
    """
    op = "cosmic_ray_reject_stack"
    mf = _count(min_frames, "min_frames", 3)
    cube = _require_frames(frames, op, min_frames=mf)
    k = _num(kappa, "kappa")
    g = _num(gain, "gain")
    rs = _num(read_sigma, "read_sigma", sign="non_negative") \
        if read_sigma is not None else None
    n = cube.shape[0]
    med = np.median(cube, axis=0)
    mad = np.median(np.abs(cube - med), axis=0) * MAD_TO_SIGMA * _mad_correction(n)
    # MAD が 0 に潰れる(同じ値が並ぶ)画素は、全体の雑音で下支えする
    _, global_sigma = _robust_background(med, "mad")
    scale = np.where(mad > 0.0, mad, max(global_sigma, 1e-12))
    if rs is not None:
        model = np.sqrt(np.maximum(med, 0.0) / g + rs * rs)
        scale = np.maximum(scale, model)
    masks = cube > (med + k * scale)
    cleaned = np.where(masks, med[None, :, :], cube)
    return [np.ascontiguousarray(c) for c in cleaned], masks


# ---------------------------------------------------------------------------
# align —— 星の対応から変換を推定
# ---------------------------------------------------------------------------
def _vote_translation(src, dst, max_shift, bin_px=1.0):
    """全ペアの差ベクトルの最頻値で粗い平行移動を出す(投票)。

    星は互いに見分けがつかないので記述子マッチングが効かない(モジュール
    docstring 参照)。正しい平行移動のところだけ差ベクトルが**積み上がる**、
    という幾何だけを使う —— 誤対応の差ベクトルは一様に散る。
    """
    d = dst[:, None, :] - src[None, :, :]
    d = d.reshape(-1, 2)
    keep = (np.abs(d[:, 0]) <= max_shift) & (np.abs(d[:, 1]) <= max_shift)
    d = d[keep]
    if d.shape[0] == 0:
        return None, 0
    nb = int(np.ceil(2.0 * max_shift / bin_px)) + 1
    ir = np.clip(((d[:, 0] + max_shift) / bin_px).astype(int), 0, nb - 1)
    ic = np.clip(((d[:, 1] + max_shift) / bin_px).astype(int), 0, nb - 1)
    hist = np.zeros((nb, nb), dtype=np.int64)
    np.add.at(hist, (ir, ic), 1)
    # 隣接ビンにまたがった票を拾う(境目に真値が乗ると 2 分される)
    smooth = ndimage.uniform_filter(hist.astype(np.float64), size=3,
                                    mode="constant")
    p = np.unravel_index(int(np.argmax(smooth)), hist.shape)
    centre = np.array([p[0] * bin_px - max_shift, p[1] * bin_px - max_shift])
    # 2 段の絞り込み: ビンの格子は真値と一般にずれるので、最頻ビンの中心から
    # 一度平均を取り直し、その平均のまわりでもう一度選び直す。1 段だけだと
    # 真値がビン境界に乗ったときに票が 2 分され、実測で 26 対応あるフレーム対の
    # 票が 3 まで落ちた(推定値そのものは NN 照合が救っていたが、票数を
    # 信頼度として読むと嘘になる)。
    near = np.abs(d - centre).max(axis=1) <= 1.5 * bin_px
    if near.sum() == 0:
        return centre, 0
    centre = d[near].mean(axis=0)
    near = np.abs(d - centre).max(axis=1) <= 1.5 * bin_px
    if near.sum() == 0:
        return centre, 0
    return d[near].mean(axis=0), int(near.sum())


def frame_align(reference, frame, model="similarity", threshold_sigma=5.0,
                max_stars=60, tolerance_px=2.0, max_shift_px=None,
                ransac_iters=500, seed=0, min_inliers=3):
    """星の対応から ``frame`` → ``reference`` の 2-D 変換を推定する。

    工程は 3 段で、**推定の本体はどれも既存 op**:

    1. :func:`star_detect` で両方の星を取る。
    2. 粗い平行移動を**オフセット投票**で出す(``_vote_translation``)。
       ここで :func:`features.match_keypoints` を使わないのは実測に基づく判断で、
       星野の 9x9 パッチは互いにほとんど同じ形なので Lowe の比検定
       (既定 ratio=0.8)がほぼ全部を捨てる —— 実測では 40 星のフレーム対で
       採れた対応が 0 件だった(投票法は同じ対で 38 件)。
    3. 粗い移動で最近傍の対応を作り、
       :func:`mosaic.proj_match_points_ransac` で誤対応を落とし、
       :func:`fit_transform.vector_to_similarity`(``model`` に応じて
       ``vector_to_rigid`` / ``vector_to_hom_mat2d``)で当てはめる。
       RANSAC ループも Umeyama もここには書いていない。

    *model* ``"translation"`` は対応の差の中央値だけを使う(星が 1 個でも動く)。
    ``"rigid"`` = 回転 + 並進、``"similarity"`` = + 等方スケール、
    ``"affine"`` = 6 自由度。**視野が広くなければ ``"similarity"`` で足りる**
    (赤道儀の追尾誤差は回転と並進、大気差はスケールに一次で乗る)。

    Returns ``(matrix, info)``:

    * ``matrix`` —— ``(3, 3)`` float64。``(row, col, 1)`` に左から掛けると
      ``reference`` の座標になる(``fit_transform`` と同じ規約)。
    * ``info`` —— dict。``n_stars_ref`` / ``n_stars_src`` / ``n_pairs`` /
      ``n_inliers`` / ``inlier_ratio`` / ``shift_row`` / ``shift_col`` /
      ``rotation_deg`` / ``scale`` / ``rms_px``(内点の残差 RMS)/ ``model``。

    **fail-closed**: 内点が *min_inliers* に満たなければ ``ValueError`` を送出
    する。**恒等変換を黙って返さない** —— 位置合わせに失敗したフレームを
    「ずれ 0」として合成に混ぜると、例外も警告も無しに二重像ができる。

    **Raises** ``ValueError``: 2-D でない / 形が違う / *model* が
    :data:`ALIGN_MODELS` にない / どちらかで星が 1 つも見つからない /
    対応が作れない / 内点が足りない場合。
    """
    op = "frame_align"
    ref = _require_image(reference, "reference", op)
    src = _require_image(frame, "frame", op)
    if ref.shape != src.shape:
        raise ValueError("%s: reference %r and frame %r must have the same "
                         "shape" % (op, ref.shape, src.shape))
    _choice(model, "model", ALIGN_MODELS, op)
    tol = _num(tolerance_px, "tolerance_px")
    ms = _num(max_shift_px, "max_shift_px") if max_shift_px is not None \
        else 0.25 * min(ref.shape)
    it = _count(ransac_iters, "ransac_iters", 1)
    sd = _seed(seed)
    mi = _count(min_inliers, "min_inliers", 1)

    p_ref = star_detect(ref, threshold_sigma=threshold_sigma,
                        max_stars=max_stars)
    p_src = star_detect(src, threshold_sigma=threshold_sigma,
                        max_stars=max_stars)
    if p_ref.shape[0] == 0 or p_src.shape[0] == 0:
        raise ValueError("%s: found %d star(s) in the reference and %d in the "
                         "frame — cannot align on stars (lower "
                         "threshold_sigma, or the field is empty)"
                         % (op, p_ref.shape[0], p_src.shape[0]))

    coarse, votes = _vote_translation(p_src, p_ref, ms)
    if coarse is None or votes == 0:
        raise ValueError("%s: no translation got any votes within "
                         "max_shift_px=%g — the frames may not overlap"
                         % (op, ms))
    moved = p_src + coarse
    # 最近傍の対応(tolerance 以内、1 対 1)
    d2 = ((moved[:, None, 0] - p_ref[None, :, 0]) ** 2
          + (moved[:, None, 1] - p_ref[None, :, 1]) ** 2)
    src_idx, ref_idx = [], []
    used = set()
    for i in np.argsort(d2.min(axis=1)):
        j = int(np.argmin(d2[i]))
        if j in used or d2[i, j] > tol * tol:
            continue
        used.add(j)
        src_idx.append(int(i))
        ref_idx.append(j)
    if len(src_idx) < mi:
        raise ValueError("%s: only %d star pair(s) inside tolerance_px=%g "
                         "(need %d) — raise tolerance_px or lower "
                         "threshold_sigma" % (op, len(src_idx), tol, mi))
    a = p_src[src_idx]
    b = p_ref[ref_idx]

    if a.shape[0] >= 4 and model != "translation":
        # 既存の 2-D 点対応 RANSAC を内点判定にだけ使う(当てはめは下で行う)
        r = mosaic.proj_match_points_ransac(a, b, thresh=tol, iters=it, seed=sd)
        inl = np.asarray(r["inliers"], dtype=bool)
        if inl.sum() < mi:
            inl = np.ones(a.shape[0], dtype=bool)
    else:
        inl = np.ones(a.shape[0], dtype=bool)
    if int(inl.sum()) < mi:
        raise ValueError("%s: RANSAC kept only %d inlier(s), need %d"
                         % (op, int(inl.sum()), mi))
    ai, bi = a[inl], b[inl]

    if model == "translation":
        t = np.median(bi - ai, axis=0)
        M = np.eye(3)
        M[0, 2], M[1, 2] = float(t[0]), float(t[1])
    elif model == "rigid":
        M = fit_transform.vector_to_rigid(ai, bi)
    elif model == "similarity":
        M = fit_transform.vector_to_similarity(ai, bi)
    else:
        M = fit_transform.vector_to_hom_mat2d(ai, bi)

    pred = (M[:2, :2] @ ai.T).T + M[:2, 2]
    rms = float(np.sqrt(np.mean(np.sum((pred - bi) ** 2, axis=1))))
    lin = M[:2, :2]
    scale_est = float(np.sqrt(abs(np.linalg.det(lin))))
    rot = float(np.degrees(np.arctan2(lin[1, 0], lin[0, 0])))
    info = {"n_stars_ref": int(p_ref.shape[0]), "n_stars_src": int(p_src.shape[0]),
            "n_pairs": int(a.shape[0]), "n_inliers": int(inl.sum()),
            "inlier_ratio": float(inl.sum() / a.shape[0]),
            "shift_row": float(M[0, 2]), "shift_col": float(M[1, 2]),
            "rotation_deg": rot, "scale": scale_est, "rms_px": rms,
            "model": model, "coarse_row": float(coarse[0]),
            "coarse_col": float(coarse[1]), "votes": int(votes)}
    return np.ascontiguousarray(M), info


def align_frames(frames, reference=0, order=3, **align_kw):
    """フレーム列を 1 枚の基準へ重ね合わせる。

    各フレームについて :func:`frame_align` で変換を推定し、
    :func:`scipy.ndimage.affine_transform` で逆写像・再標本化する。

    **正直な注意**: 補間は総フラックスを厳密には保存しない。双一次補間
    (``order=1``)は星像を僅かに鈍らせ、``order=3`` のスプラインは鋭さを保つ
    代わりに星の周りに小さな負の縁を作る。実測(ノイズ無し、真の並進 0.5 px、
    ``order=1``)で総フラックスは -0.00 %、星のピークは -6.5 % 変わった。
    **フラックスを厳密に保ちたいなら補間せず** :func:`drizzle_resample` に
    ``frame_align`` の推定シフトをそのまま渡すこと —— それが drizzle の
    存在理由そのもの。

    Returns ``(aligned, matrices)``:

    * ``aligned`` —— 長さ ``N`` の list、各 ``(H, W)`` float64(``images`` 語彙)。
      基準フレームは**変換を通さずそのまま**返す(恒等変換でも補間は像を鈍らせる
      ので、通す理由が無い)。
    * ``matrices`` —— 長さ ``N`` の list、各 ``(3, 3)``。基準は単位行列。

    **Raises** ``ValueError``: *frames* が list / tuple でない / 枚数が 2 未満 /
    *reference* が範囲外 / *order* が 0〜5 の外 / :func:`frame_align` が
    どれか 1 枚で失敗した場合(**失敗を黙って恒等変換に落とさない**)。
    """
    op = "align_frames"
    cube = _require_frames(frames, op, min_frames=2)
    n = cube.shape[0]
    ridx = _count(reference, "reference", 0, n - 1)
    o = _count(order, "order", 0, 5)
    ref = cube[ridx]
    out, mats = [], []
    for i in range(n):
        if i == ridx:
            out.append(np.ascontiguousarray(ref))
            mats.append(np.eye(3))
            continue
        M, _ = frame_align(ref, cube[i], **align_kw)
        inv = np.linalg.inv(M)
        warped = ndimage.affine_transform(cube[i], inv[:2, :2],
                                          offset=inv[:2, 2], order=o,
                                          mode="constant", cval=0.0)
        out.append(np.ascontiguousarray(warped))
        mats.append(np.ascontiguousarray(M))
    return out, mats


if __name__ == "__main__":                          # pragma: no cover
    frame, truth = synth_starfield(n_stars=12, seed=0)
    print("astrostack: %d ops" % len(ASTROSTACK))
    print("frame %r  sky=%.1f  noise_sigma=%.2f"
          % (frame.shape, truth["sky"], noise_sigma(frame)))
    print("stars detected:", star_detect(frame).shape[0], "of", truth["n_stars"])
