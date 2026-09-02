"""fast.py — CPU の高速 twin テーブル(cv2/IPP)。**同じ答えを速く出す**経路。

``accel.py`` が GPU(torch)で core op を再現する表なら、この module は **CPU の
cv2(IPP + SIMD + マルチスレッド)で core op を再現する表**である。狙いは
``docs/design/PERF_MEMORY_VIDEO_SURVEY.md`` §0-1 の実測:

    遅さの正体は「Python」ではなく「scipy.ndimage を float64 で単スレッド実行して
    いること」。同じ処理を cv2 で走らせると 2048² で gaussian 58 → 8.6 ms、
    gray opening 154 → 17 ms、median(k=5) 数百 → 数 ms。

設計原則(``docs/GPU_ACCEL_PLAN.md`` の accel と同一):

* **faithful なものだけ載せる。「速いが違う」は作らない。** 登録候補は
  :func:`parity` のゲート(5 つの (a,b) × 6 枚の画像、interior max-abs < 5e-3、
  **二値出力 op は不一致率 0 が必須**)を通ったものだけ。落ちたものは
  ``docs/design/FAST_TWINS.md`` の「載せなかった」表に **実測誤差つきで**残す。
* **境界規約は推測しない。** scipy.ndimage の既定 ``mode="reflect"`` は numpy の
  ``"symmetric"``(端を複製する鏡映)であり、cv2 の既定
  ``BORDER_REFLECT_101``(端を複製しない鏡映)とは **別物**。accel は
  2026-08-31 にこの罠を踏んで sobel/dog/unsharp の端がずれていた。ここでは
  **``cv2.BORDER_REFLECT``**(= symmetric)を明示し、実測で確かめてある
  (BORDER_REFLECT_101 を使うと gaussian の max 差は 2.2e-3〜8.9e-2 まで跳ねる)。
* **契約は float64 [0,1] のまま。** twin は core と同じ dtype・shape・値域を返す。
  uint8 の整数カーネルは :func:`apply_uint8` に **別口**で置く(facade は通さない)。
* **失敗は隠さない。** 例外は呼び出し側(``api._try_fast``)が ledger に
  ``source="fast"`` で記録して core に落ちる。``on_error="raise"`` では再送出。

使い方::

    import fast
    fast.FAST["gaussian"].note                 # なぜ載っているか
    y = fast.apply_fast("gaussian", x, 0.5, 0.5)   # float64 [0,1] -> float64 [0,1]
    u = fast.apply_uint8("median", x_u8, 0.5, 0.5) # uint8 -> uint8(整数カーネル)
    rows = fast.parity()                       # ゲートを回す(tests/test_fast_parity.py)

    py -3.11 fast.py                           # 表とゲートの結果を印字
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Callable

import numpy as np

try:
    import cv2
    _HAS_CV2 = True
except Exception:                                # pragma: no cover - optional dependency
    cv2 = None
    _HAS_CV2 = False


class FastUnsupported(Exception):
    """この入力(shape / dtype / パラメータ)には faithful な twin が無い。

    「壊れた」ではなく「**無い**」を表す。``api._try_fast`` はこれを ledger に
    記録せず、黙って core に落ちる(``accel`` の "その op に mapping が無い" と
    同じ扱い)。実際に壊れた場合は普通の例外が飛び、そちらは記録される。
    """


@dataclass(frozen=True)
class FastTwin:
    """1 つの core op に対する CPU 高速 twin。

    fn            -- ``fn(v, a, b)``。**float64 [0,1] の契約入力**を受け取り、
                     core op と同じ dtype / shape / 値域を返す。
    dtype_policy  -- ``"f64"``  = float64 経路のみ、
                     ``"f64+u8"`` = :func:`apply_uint8` に uint8 の整数カーネルも
                     あり(1/255 の量子化まで core と一致)。
    note          -- 何で速いのか / どこが core と厳密に一致するのか。
    """

    fn: Callable
    dtype_policy: str
    note: str


# ── core と同じ引数写像 ───────────────────────────────────────────────────────
def _k(a: float) -> int:
    """``ops._k`` と同一。a -> 奇数のカーネル辺長 3/5/7/9。"""
    return (3, 5, 7, 9)[min(3, int(a * 4))]


def _sigma(a: float) -> float:
    """``ops._gaussian`` の sigma。"""
    return 0.3 + 2.7 * a


def _gauss_ksize(sigma: float) -> int:
    """scipy の ``gaussian_filter`` が使う離散カーネル辺長。

    scipy は ``truncate=4.0`` から ``radius = int(4*sigma + 0.5)`` を作る。cv2 に
    ``ksize=(0,0)`` を渡すと cv2 自身の式(``round(sigma*4)*2+1``)になり、丸めが
    一致しない sigma が出うるので **scipy の半径を明示的に渡す**。
    """
    return 2 * max(1, int(4.0 * sigma + 0.5)) + 1


def _norm(x):
    """``ops._norm`` と同一(画像全体の最大絶対値で割る)。"""
    mx = float(np.max(np.abs(x)))
    return x / mx if mx > 1e-8 else x


_BORDER = None if cv2 is None else cv2.BORDER_REFLECT   # = scipy mode="reflect" (symmetric)


def _rect(k: int):
    return np.ones((k, k), np.uint8)


def _f64(v):
    """cv2 に渡せる形へ。契約外(非 float64 / 非 2-D)なら twin は「無い」。"""
    a = np.asarray(v)
    if a.dtype != np.float64 or a.ndim != 2 or a.size == 0:
        raise FastUnsupported("fast twins take a non-empty 2-D float64 image, got "
                              "dtype=%s ndim=%d size=%d" % (a.dtype, a.ndim, a.size))
    return np.ascontiguousarray(a)


# ── float64 カーネル ──────────────────────────────────────────────────────────
def _blur_g(v, sigma):
    kz = _gauss_ksize(sigma)
    return cv2.GaussianBlur(v, (kz, kz), sigma, borderType=_BORDER)


def _box(v, k):
    return cv2.blur(v, (k, k), borderType=_BORDER)


def t_gaussian(v, a, b):
    return _blur_g(_f64(v), _sigma(a))


def t_mean_box(v, a, b):
    return _box(_f64(v), _k(a))


def t_median(v, a, b):
    """``ndimage.median_filter(size=k)`` の twin。

    ★honest: ``cv2.medianBlur`` は **float では ksize 3 と 5 しか受け付けない**
    (それ以上は uint8 専用)。``a >= 0.5`` は k=7/9 になるので **core の
    scipy をそのまま呼ぶ**(= 速くならないが、答えは 1 ビットも変わらない)。
    uint8 なら全 k で cv2 が使えるので :func:`apply_uint8` 側は全域を覆う。

    ``medianBlur`` の境界規約は BORDER_REPLICATE で scipy の reflect と違うため、
    **入力を symmetric で k//2 だけ pad してから掛けて切り戻す**。これで端まで
    一致する(pad 無しだと端 3px で max 0.155 ずれる ―― 実測)。
    """
    x = _f64(v)
    k = _k(a)
    if k > 5:
        from scipy import ndimage          # 遅い方(= core と同一実装)に素直に落ちる
        return ndimage.median_filter(x, size=k)
    p = k // 2
    pad = np.pad(x, p, mode="symmetric").astype(np.float32)
    return cv2.medianBlur(pad, k).astype(np.float64)[p:-p, p:-p]


def t_min_filter(v, a, b):
    return cv2.erode(_f64(v), _rect(_k(a)), borderType=_BORDER)


def t_max_filter(v, a, b):
    return cv2.dilate(_f64(v), _rect(_k(a)), borderType=_BORDER)


def t_gopen(v, a, b):
    return cv2.morphologyEx(_f64(v), cv2.MORPH_OPEN, _rect(_k(a)), borderType=_BORDER)


def t_gclose(v, a, b):
    return cv2.morphologyEx(_f64(v), cv2.MORPH_CLOSE, _rect(_k(a)), borderType=_BORDER)


def t_tophat(v, a, b):
    return _norm(cv2.morphologyEx(_f64(v), cv2.MORPH_TOPHAT, _rect(_k(a)), borderType=_BORDER))


def t_bothat(v, a, b):
    return _norm(cv2.morphologyEx(_f64(v), cv2.MORPH_BLACKHAT, _rect(_k(a)), borderType=_BORDER))


def t_morph_grad(v, a, b):
    return _norm(cv2.morphologyEx(_f64(v), cv2.MORPH_GRADIENT, _rect(_k(a)), borderType=_BORDER))


def _sobel_xy(x):
    return (cv2.Sobel(x, cv2.CV_64F, 1, 0, ksize=3, borderType=_BORDER),
            cv2.Sobel(x, cv2.CV_64F, 0, 1, ksize=3, borderType=_BORDER))


def t_sobel_mag(v, a, b):
    gx, gy = _sobel_xy(_f64(v))
    return _norm(np.hypot(gx, gy))


def t_laplace(v, a, b):
    return _norm(np.abs(cv2.Laplacian(_f64(v), cv2.CV_64F, ksize=1, borderType=_BORDER)))


_PREWITT_D = np.array([-1.0, 0.0, 1.0])
_PREWITT_S = np.array([1.0, 1.0, 1.0])


def t_prewitt_mag(v, a, b):
    x = _f64(v)
    px = cv2.sepFilter2D(x, cv2.CV_64F, _PREWITT_D, _PREWITT_S, borderType=_BORDER)
    py = cv2.sepFilter2D(x, cv2.CV_64F, _PREWITT_S, _PREWITT_D, borderType=_BORDER)
    return _norm(np.hypot(px, py))


def t_dog(v, a, b):
    x = _f64(v)
    return _norm(np.abs(_blur_g(x, 0.5 + 2.0 * a) - _blur_g(x, 1.0 + 4.0 * b)))


def t_unsharp(v, a, b):
    x = _f64(v)
    return np.clip(x + (1.5 * a) * (x - _blur_g(x, 0.5 + 1.5 * b)), 0, 1)


def t_std_filter(v, a, b):
    x = _f64(v)
    k = _k(a)
    m = _box(x, k)
    m2 = _box(x * x, k)
    return _norm(np.sqrt(np.maximum(m2 - m * m, 0.0)))


def t_canny(v, a, b):
    """core の ``_canny`` は **hysteresis を持たない**(gaussian → sobel 振幅 →
    しきい値)。``cv2.Canny`` は別のアルゴリズムなので使えず、**cv2 のプリミティブ
    で core の式をそのまま組む**。これで二値の不一致率 0(実測)。
    """
    x = _f64(v)
    g = _blur_g(x, 0.5 + 1.5 * a)
    gx, gy = _sobel_xy(g)
    return (_norm(np.hypot(gx, gy)) > (0.1 + 0.5 * b)).astype(np.float64)


# ── uint8 の整数カーネル(facade は通さない・:func:`apply_uint8` 専用)──────────
def _u8in(v):
    a = np.asarray(v)
    if a.dtype != np.uint8 or a.ndim != 2 or a.size == 0:
        raise FastUnsupported("apply_uint8 takes a non-empty 2-D uint8 image, got "
                              "dtype=%s ndim=%d size=%d" % (a.dtype, a.ndim, a.size))
    return np.ascontiguousarray(a)


def u8_gaussian(v, a, b):
    x = _u8in(v)
    s = _sigma(a)
    kz = _gauss_ksize(s)
    return cv2.GaussianBlur(x, (kz, kz), s, borderType=_BORDER)


def u8_mean_box(v, a, b):
    return cv2.blur(_u8in(v), (_k(a),) * 2, borderType=_BORDER)


def u8_median(v, a, b):
    """uint8 は **全 k**(3/5/7/9)で cv2 が使えて、しかも順序統計なので
    量子化後の入力に対しては **厳密**(丸め誤差ゼロ)。"""
    x = _u8in(v)
    k = _k(a)
    p = k // 2
    return cv2.medianBlur(np.pad(x, p, mode="symmetric"), k)[p:-p, p:-p]


def u8_min_filter(v, a, b):
    return cv2.erode(_u8in(v), _rect(_k(a)), borderType=_BORDER)


def u8_max_filter(v, a, b):
    return cv2.dilate(_u8in(v), _rect(_k(a)), borderType=_BORDER)


def u8_gopen(v, a, b):
    return cv2.morphologyEx(_u8in(v), cv2.MORPH_OPEN, _rect(_k(a)), borderType=_BORDER)


def u8_gclose(v, a, b):
    return cv2.morphologyEx(_u8in(v), cv2.MORPH_CLOSE, _rect(_k(a)), borderType=_BORDER)


_F64 = "f64"
_F64U8 = "f64+u8"

# core registry 名 -> (twin, dtype_policy, note)。
# ★ここに載っているのは全て :func:`parity` のゲートを通ったものだけ。
#   追加するときは「実装 → ゲートを回す → 通ったら載せる」の順を必ず守る。
_SPEC: tuple = (
    # (registry name, twin fn, dtype_policy, note)
    ("gaussian", t_gaussian, _F64U8,
     "cv2.GaussianBlur、scipy の半径 int(4σ+0.5) を明示 + BORDER_REFLECT。full-image bit 一致(2e-16)。2048² 58→8.6 ms"),
    ("mean_box", t_mean_box, _F64U8,
     "cv2.blur + BORDER_REFLECT。full-image 一致(1e-15)。2048² 54→10 ms"),
    ("median", t_median, _F64U8,
     "cv2.medianBlur(float32、symmetric pad で端も一致)。★float は k<=5 のみ = a<0.5。k=7/9 は core の scipy に落ちる(答えは不変・速度は不変)"),
    ("min_filter", t_min_filter, _F64U8, "cv2.erode(矩形 k×k)。bit 一致(0.0)"),
    ("max_filter", t_max_filter, _F64U8, "cv2.dilate(矩形 k×k)。bit 一致(0.0)"),
    ("gerode", t_min_filter, _F64U8, "grey_erosion(size=k) = cv2.erode。bit 一致(0.0)"),
    ("gdilate", t_max_filter, _F64U8, "grey_dilation(size=k) = cv2.dilate。bit 一致(0.0)"),
    ("gopen", t_gopen, _F64U8, "cv2.morphologyEx OPEN。bit 一致(0.0)。2048² 154→17 ms"),
    ("gclose", t_gclose, _F64U8, "cv2.morphologyEx CLOSE。bit 一致(0.0)"),
    ("tophat", t_tophat, _F64, "cv2 TOPHAT + ops._norm。bit 一致(0.0)"),
    ("bothat", t_bothat, _F64, "cv2 BLACKHAT + ops._norm。bit 一致(0.0)"),
    ("morph_grad", t_morph_grad, _F64, "cv2 GRADIENT + ops._norm。bit 一致(0.0)"),
    ("sobel_mag", t_sobel_mag, _F64, "cv2.Sobel(ksize=3)×2 + hypot + _norm。一致 4e-16"),
    ("laplace", t_laplace, _F64, "cv2.Laplacian(ksize=1 = [[0,1,0],[1,-4,1],[0,1,0]])+ _norm。一致 4e-16"),
    ("prewitt_mag", t_prewitt_mag, _F64, "cv2.sepFilter2D([-1,0,1]/[1,1,1])×2 + _norm。一致 3e-16"),
    ("dog", t_dog, _F64, "GaussianBlur 2 本の差 + _norm。一致 4e-14"),
    ("unsharp", t_unsharp, _F64, "v + k(v - GaussianBlur)。一致 6e-16"),
    ("std_filter", t_std_filter, _F64, "box(v²) - box(v)² の sqrt + _norm。一致 2e-14"),
    ("canny", t_canny, _F64, "core は hysteresis 無し(gauss→sobel→閾値)なので cv2 プリミティブで同式を組む。二値不一致率 0"),
    # ★``edges_image``(HALCON 名としては canny と同じ)は載せない。registry の
    #   その名前は backends_auto の **skimage canny**(本物の hysteresis つき)で、
    #   core の ``canny`` とは別のアルゴリズム。不一致率 1.0(実測)。
    # ── HALCON 名の twin(registry に同一実装で別名登録されている op)──────────
    # accel._TWIN_ALIASES と同じ発想。ゲートは registry の**その名前の実装**に
    # 対して回すので、実装がずれていれば落ちて載らない。
    ("gauss_filter", t_gaussian, _F64U8, "gaussian の HALCON twin"),
    ("gauss_image", t_gaussian, _F64U8, "gaussian の HALCON twin"),
    ("mean_image", t_mean_box, _F64U8, "mean_box の HALCON twin"),
    ("median_image", t_median, _F64U8, "median の HALCON twin"),
    ("median_separate", t_median, _F64U8, "median の HALCON twin"),
    ("median_weighted", t_median, _F64U8, "median の HALCON twin"),
    ("eliminate_min_max", t_median, _F64U8, "median の HALCON twin"),
    ("gray_erosion", t_min_filter, _F64U8, "gerode の HALCON twin"),
    ("gray_erosion_rect", t_min_filter, _F64U8, "min_filter の HALCON twin"),
    ("gray_dilation", t_max_filter, _F64U8, "gdilate の HALCON twin"),
    ("gray_dilation_rect", t_max_filter, _F64U8, "max_filter の HALCON twin"),
    ("gray_opening", t_gopen, _F64U8, "gopen の HALCON twin"),
    ("gray_opening_rect", t_gopen, _F64U8, "gopen の HALCON twin"),
    ("gray_closing", t_gclose, _F64U8, "gclose の HALCON twin"),
    ("gray_closing_rect", t_gclose, _F64U8, "gclose の HALCON twin"),
    ("gray_tophat", t_tophat, _F64, "tophat の HALCON twin"),
    ("gray_bothat", t_bothat, _F64, "bothat の HALCON twin"),
    ("gray_range_rect", t_morph_grad, _F64, "morph_grad の HALCON twin"),
    ("sobel_amp", t_sobel_mag, _F64, "sobel_mag の HALCON twin"),
    ("prewitt_amp", t_prewitt_mag, _F64, "prewitt_mag の HALCON twin"),
    ("deviation_image", t_std_filter, _F64, "std_filter の HALCON twin"),
    ("diff_of_gauss", t_dog, _F64, "dog の HALCON twin"),
)

FAST: dict = {}
if _HAS_CV2:
    FAST = {n: FastTwin(f, p, note) for (n, f, p, note) in _SPEC}

# uint8 の整数カーネル。``dtype_policy == "f64+u8"`` の op だけがここに居る。
_U8_KERNELS: dict = {} if not _HAS_CV2 else {
    "gaussian": u8_gaussian, "mean_box": u8_mean_box, "median": u8_median,
    "min_filter": u8_min_filter, "max_filter": u8_max_filter,
    "gerode": u8_min_filter, "gdilate": u8_max_filter,
    "gopen": u8_gopen, "gclose": u8_gclose,
    # HALCON twin 別名
    "gauss_filter": u8_gaussian, "gauss_image": u8_gaussian, "mean_image": u8_mean_box,
    "median_image": u8_median, "median_separate": u8_median, "median_weighted": u8_median,
    "eliminate_min_max": u8_median,
    "gray_erosion": u8_min_filter, "gray_erosion_rect": u8_min_filter,
    "gray_dilation": u8_max_filter, "gray_dilation_rect": u8_max_filter,
    "gray_opening": u8_gopen, "gray_opening_rect": u8_gopen,
    "gray_closing": u8_gclose, "gray_closing_rect": u8_gclose,
}

# 二値(region)を返す twin。ゲートは **不一致率 0** を要求する(連続 op の
# 5e-3 より厳しい。二値は 1 画素の食い違いが目に見える差だから)。
# ★「観測した出力が {0,1} だったか」で判定してはいけない —— 連続 op でも定数画像
#   では出力が全 0 になり、二値と誤判定して基準が勝手に厳しくなる(実装中に踏んだ)。
#   判定は registry の **宣言された out_sort** で行う。
_BINARY_OUT = frozenset({"canny"})

# 載せなかった候補と、その実測誤差(docs/design/FAST_TWINS.md の表の出典)。
# 「速いが違う」を作らないための、**捨てた記録**。
NOT_LISTED: dict = {
    "clahe": "cv2.createCLAHE は clip limit の定義もタイル補間も core と別物 — interior 0.135",
    "bilateral": "cv2.bilateralFilter は空間近傍が半径 2 の円(角 4 画素を落とす)で core の 5x5 全画素と別物 — interior 0.121",
    "rotate_img": "cv2.warpAffine INTER_CUBIC は Catmull-Rom、core は order=3 B-spline(prefilter あり) — interior 0.870",
    "rescale_img": "同上(order=3 spline)。b<0.25 の最近傍 / b<0.5 の双一次だけ一致しても部分的なので載せない",
    "affine_warp": "同上(order=3 spline)",
    "equalize": "cv2.equalizeHist は uint8 の 256 段、core は float の 256 bin + np.interp — interior 0.580",
    "otsu": "cv2 の Otsu は uint8 ヒストグラム、core は float 256 bin。interior 0.0042 でゲートは通るが**二値 op なので不一致率 0 を要求**して不採用",
    "dyn_threshold": "cv2.blur と ndimage.uniform_filter の最終 ulp 差で閾値上の画素が反転 — 二値不一致率 2.97e-4(> 0)なので不採用",
    "edges_image": "registry のこの名前は backends_auto の skimage canny(本物の hysteresis つき)で core の canny とは別アルゴリズム — 二値不一致率 1.00",
    "percentile": "cv2 に任意パーセンタイルの rank filter が無い",
    "lowpass/highpass": "cv2.dft は np.fft.fft2 とレイアウト規約が違い、調査でも cv2 の利得は測れていない",
    "gamma/invert/scale_clip/threshold": "既に numpy の要素演算で 100〜450 Mpx/s。cv2 化の利得が無い(uint8 LUT は契約外)",
}


# ── 公開 API ──────────────────────────────────────────────────────────────────
def has(name: str) -> bool:
    """*name* に faithful な CPU 高速 twin があるか。"""
    return name in FAST


def apply_fast(name: str, v, a: float = 0.5, b: float = 0.5):
    """twin を 1 つ走らせる。契約は core と同じ float64 [0,1] -> float64。

    twin が無い名前は :class:`KeyError`、この入力に twin が使えない場合は
    :class:`FastUnsupported`(呼び出し側は core に落ちる)。
    """
    twin = FAST.get(name)
    if twin is None:
        raise KeyError("no CPU fast twin for %r (fast.FAST has %d)" % (name, len(FAST)))
    return twin.fn(v, a, b)


def apply_uint8(name: str, img_u8, a: float = 0.5, b: float = 0.5):
    """uint8 の整数カーネル(**facade は通さない** — 呼び出し側が明示的に使う)。

    入力・出力とも uint8。core を float64 で走らせた結果と **1/255 まで**一致する
    (median / モルフォロジは順序統計なので量子化後の入力に対しては厳密、
    gaussian / box は整数丸めで最大 0.5/255)。
    """
    fn = _U8_KERNELS.get(name)
    if fn is None:
        raise KeyError("no uint8 integer kernel for %r — the float64 twin is %s"
                       % (name, "present" if name in FAST else "absent"))
    return fn(img_u8, a, b)


# ── parity ゲート(accel.parity と同一の方法)─────────────────────────────────
# accel.PARITY_AB と同じ 5 点。a は _k(a) の 4 段(3/5/7/9)を全部踏む。
PARITY_AB = ((0.5, 0.4), (0.25, 0.75), (0.8, 0.2), (0.0, 0.5), (1.0, 0.9))
PARITY_TOL = 5e-3


def parity_images() -> list:
    """ゲートの 6 枚。自然画 / 純ノイズ / 定数 / 量子化 / 勾配 / 小さい 64²。

    accel.parity の 6 枚(乱数 4 + 定数 + uint8 量子化)と同じ趣旨だが、
    「平坦入力での _norm の雑音増幅」「量子化入力での閾値の刃」「小さい画像で
    カーネルが画像より大きい場合」の 3 つを名前つきで持たせてある。
    """
    n = 128
    rng = np.random.default_rng(7)
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    grad = xx / (n - 1)
    disk = ((yy - n * 0.35) ** 2 + (xx - n * 0.4) ** 2) < (n * 0.18) ** 2
    natural = np.clip(0.35 * grad + 0.45 * disk + 0.03 * rng.standard_normal((n, n)), 0, 1)
    noise = rng.random((n, n))
    const = np.full((n, n), 0.42)
    quant = np.round(natural * 255.0) / 255.0
    small = np.clip(rng.random((64, 64)) * 0.6 + 0.2 * (np.mgrid[0:64, 0:64][1] / 64), 0, 1)
    return [natural, noise, const, quant, grad.copy(), small]


def _margin(a: float) -> int:
    """accel.parity と同じ: カーネル半径 +1(最低 3px)を端から除く。"""
    return max(3, _k(a) // 2 + 1)


def parity(name: str | None = None, images=None, params=None, tol: float = PARITY_TOL) -> list:
    """全 twin(or *name* 1 つ)を registry の core op と difftest する。

    accel.parity と同じ方法: **5 つの (a,b) × 6 枚の画像**、端から
    ``max(3, k//2+1)`` px を除いた **interior の max-abs**。二値出力 op だけは
    max-abs だと「刃の上の 1 画素」で即 1.0 になるので **不一致率**で測る
    (accel と同じ計量。ただし採否の閾値はこちらの方が厳しく **0 を要求**する)。

    返り値: ``[{"name", "full", "interior", "binary", "tol", "ok"}, ...]``
    """
    import ops                                   # 遅延: registry の import は重い
    imgs = parity_images() if images is None else list(images)
    abs_ = PARITY_AB if params is None else tuple(params)
    names = sorted(FAST) if name is None else [name]
    rows = []
    for nm in names:
        core = ops.RT.get(nm)
        if core is None:
            rows.append({"name": nm, "full": float("nan"), "interior": float("nan"),
                         "binary": False, "tol": tol, "ok": False,
                         "error": "no registry op named %r" % nm})
            continue
        full = inter = 0.0
        # 二値かどうかは **宣言された out_sort** で決める(観測値で決めると定数画像で
        # 全 0 になった連続 op を二値と誤判定する)。
        op = ops._BY_NAME.get(nm)
        binary = (nm in _BINARY_OUT) or (op is not None and op.out_sort == "region")
        err = None
        for a, b in abs_:
            m = _margin(a)
            for im in imgs:
                try:
                    ref = np.clip(np.asarray(core(im.copy(), a, b), np.float64), 0, 1)
                    got = np.clip(np.asarray(apply_fast(nm, im.copy(), a, b), np.float64), 0, 1)
                except Exception as e:            # noqa: BLE001 - report, never hide
                    err = "%s: %s" % (type(e).__name__, e)
                    break
                if ref.shape != got.shape:
                    err = "shape %s vs %s" % (ref.shape, got.shape)
                    break
                d = np.abs(ref - got)
                inside = d[m:-m, m:-m] if (d.shape[0] > 2 * m and d.shape[1] > 2 * m) else d
                if binary:
                    # 「刃の上の 1 画素」で max-diff が即 1.0 になるので不一致率で測る
                    # (accel.parity と同じ計量。ただし採否は 0 を要求する)。
                    full = max(full, float(d.mean()))
                    inter = max(inter, float(inside.mean()))
                else:
                    full = max(full, float(d.max()))
                    inter = max(inter, float(inside.max()))
            if err:
                break
        lim = 0.0 if binary else tol
        row = {"name": nm, "full": full, "interior": inter, "binary": binary,
               "tol": lim, "ok": err is None and inter <= lim}
        if err:
            row["error"] = err
        rows.append(row)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="CPU fast twins (cv2) — table + parity gate")
    ap.add_argument("--name", default=None, help="check one twin only")
    args = ap.parse_args()
    if not _HAS_CV2:
        print("OpenCV not available — fast twins disabled (FAST is empty)")
        return 1
    rows = parity(args.name)
    ok = sum(1 for r in rows if r["ok"])
    print("fast twins: %d | uint8 kernels: %d | cv2 %s" % (len(FAST), len(_U8_KERNELS), cv2.__version__))
    print("parity vs the registry op (interior = %s-px inset, binary ops = mismatch RATE):"
          % "/".join(str(_margin(a)) for a, _ in PARITY_AB))
    for r in sorted(rows, key=lambda r: -r["interior"]):
        print("  %-22s full=%.3e interior=%.3e  tol=%.0e  %s%s"
              % (r["name"], r["full"], r["interior"], r["tol"],
                 "pass" if r["ok"] else "FAIL", "  " + r.get("error", "")))
    print("faithful: %d / %d" % (ok, len(rows)))
    return 0 if ok == len(rows) else 2


if __name__ == "__main__":
    raise SystemExit(main())
