"""imgevolve — MULTI-SORT typed image-op registry (toward HALCON-scale).

The key upgrade for HALCON coverage: operators are typed by SORT, mirroring
HALCON's data model:

  image   : gray raster, float64 in [0,1]
  region  : a binary mask (float 0/1) — HALCON's Region
  feature : a scalar/tuple measurement (float) — HALCON's control tuple

Pipelines follow the canonical machine-vision shape
  image --(segment)--> region --(region morph / select)--> region --(measure)--> feature
and the type-aware decoder guarantees each stage is sort-compatible (an op only
runs on a value of its `in_sort`). Adding operators — in any sort — makes the
evolutionary search and codegen pick them up automatically.

Genome = [0,1]^GENOME_LEN: N_SLOTS stages x (op-select t, a, b). At each slot the
candidate set is the ops whose in_sort matches the running sort (+ the sort-neutral
identity), so t indexes into that filtered set. Deterministic decode.

stdlib + numpy + scipy.ndimage only. C support is a growing image-sort subset.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
from scipy import ndimage

IMAGE, REGION, FEATURE, ANY = "image", "region", "feature", "any"
CONTOUR, MATCH = "contour", "match"   # XLD subpixel contours / template-match result
VOLUME = "volume"                     # 3D voxel array (CT/MRI/depth stacks)
COLOR = "color"                       # multichannel H x W x 3 (RGB); reached via cfa_to_rgb
# Sorts opened by the typed bridge (backends_typed): the evolution vocabulary and
# the typed op catalogs (ops3d / ops1d / opsmath / opsoptics) were two disjoint
# universes — 742 ops vs 382 ops overlapping in only 3 names (measured
# 2026-09-01), so evolution could never combine a point-cloud or 1-D operator.
# These sorts are BRAND NEW, which is what makes the bridge safe: `_candidates`
# filters on `in_sort`, so adding ops under a sort nothing used before cannot
# change the candidate list length of any existing sort — and it is that length
# that decides which op a genome decodes to (see docs/WAVE0_STABLE_SLOTS.md).
POINTS = "points"                     # (N,3) point cloud
SIGNAL = "signal"                     # 1-D array (profiles, spectra, sensor series)
MATRIX = "matrix"                     # general 2-D numeric matrix (linear algebra)
CIMAGE = "cimage"                     # 2-D complex image (HALCON complex format)
# 以下 3 つは 2026-09-01 の光子計数 / ライトフィールド族と一緒に入った。
# **新設の sort なので既存 sort の候補リストは 1 つも動かない**(= ゲノム →
# op の写像は不変。docs/WAVE0_STABLE_SLOTS.md の安全規約)。入口 op は
# image を入力に取るため既存 sort の候補を変えてしまう — したがって
# この 3 sort は入口ごと wide 語彙(IMGEVOLVE_WIDE_VOCAB=1)側に置く。
LIGHTFIELD = "lightfield"             # 4-D (V,U,H,W) light field
COUNTS = "counts"                     # 非負の 1-D 光子カウント/レート
HISTCUBE = "histcube"                 # (H,W,T) 到達時刻ヒストグラム立方体
# keypoints = 像面上の (N,2) 点。**points((N,3) の点群)とは別の sort**。
# 2026-09-02 まで両者は同じ 'points' sort に写されており、``_sort_ok`` は
# points に ``shape[1] == 3`` を要求するので、(N,2) を返す/取る橋渡し op は
# 全部 fail-soft に落ちていた —— tb_project_points / tb_points_zyx_to_keypoints_uv /
# tb_keypoints_uv_to_points / tb_keypoints_to_image2d の 4 件が、あらゆる入力で
# 「定数ゼロ」か「入力の素通し」を返していた(実測)。つまり進化は
# **「3 次元を撮る」という基本的な写像を一度も使えていなかった**。
# 型を分ける基準(混ぜると例外でなく黙って別物になるか)にも合致する。
KEYPOINTS = "keypoints"               # (N,2) 像面上の点


# Matching context: the locate problem sets a reference template here before scoring
# (matching needs a model + a search image; the pipeline threads the image, the model
# comes from context). Honest coupling — documented.
class _MatchCtx:
    """Dict-like matching context whose store is THREAD-LOCAL.

    Two evaluators scoring different models in parallel (evolution sweeps run the
    scorers on a thread pool) used to share one module-level dict: B's template
    overwrote A's and A then returned a plausible-but-wrong ``[corr, y, x]`` with no
    exception. Each thread now sees the template IT set, which removes that race for
    the reachable pattern. Dict-like on purpose: callers save/restore via
    ``ctx["template"]`` / ``ctx.get("template")``.

    Precondition (honest disclosure — this is a per-call global, not a per-call
    argument, because a registry op's signature is fixed at ``(v, a, b)``):
    ``set_match_template`` must be called on the SAME thread immediately before the
    matching op that consumes it. Given that, this is race-free. Two known limits
    it does NOT solve, neither reachable in-repo (evolution builds the dataset and
    sets the template on the main thread; the only thread pool, ``scale.py``, has
    workers that merely READ via ``fn`` and never set a template):
      * a thread pool reused across tasks reads its OWN last-set template, so a
        worker must re-set per task rather than rely on a later main-thread set;
      * a thread that never set one inherits the last template set anywhere (a
        best-effort seed for the build-on-main / score-on-fresh-worker flow), which
        is not a guarantee under two threads scoring DIFFERENT templates at once.
    When no template was ever set, the matching ops return a zero (no-match) vector
    rather than a wrong match, so the failure mode is fail-closed, not silent-wrong.
    """

    def __init__(self) -> None:
        self._tl = threading.local()
        self._shared: dict = {"template": None}   # fallback for threads that never set one

    def __getitem__(self, key: str):
        try:
            return getattr(self._tl, key)
        except AttributeError:
            return self._shared[key]

    def __setitem__(self, key: str, value) -> None:
        setattr(self._tl, key, value)
        self._shared[key] = value

    def get(self, key: str, default=None):
        return getattr(self._tl, key, self._shared.get(key, default))


_MATCH_CTX = _MatchCtx()


def set_match_template(t) -> None:
    _MATCH_CTX["template"] = None if t is None else np.asarray(t, np.float64)


def _k(a: float) -> int:
    return (3, 5, 7, 9)[min(3, int(a * 4))]


def _it(a: float) -> int:
    return 1 + int(a * 3)  # morphology iterations 1..4


def _norm(x):
    mx = float(np.max(np.abs(x)))
    return x / mx if mx > 1e-8 else x


def _shift_edge(x, dy, dx):
    """Shift like ``np.roll`` but REPLICATE the border instead of wrapping around.

    ``np.roll`` is circular, so a neighbourhood built from it makes the first
    column/row see the LAST column/row of the image. Every local neighbourhood
    here must stay inside the image, so out-of-image taps are clamped to the
    nearest in-image pixel (``mode="edge"``). Interior values are bit-identical
    to ``np.roll``; only the border ring changes.
    """
    x = np.asarray(x, np.float64)
    H, W = x.shape[0], x.shape[1]
    py0, py1, px0, px1 = max(dy, 0), max(-dy, 0), max(dx, 0), max(-dx, 0)
    p = np.pad(x, ((py0, py1), (px0, px1)), mode="edge")
    return p[py1:py1 + H, px1:px1 + W]


def _signed01(x):
    """Map a signed response to [0,1] with the zero-crossing at 0.5 (preserves the
    negative half that a plain _norm→[-1,1] would lose to the pipeline's clip)."""
    x = np.asarray(x, np.float64)
    m = float(np.max(np.abs(x))) if x.size else 0.0
    return np.clip(x / (2 * m) + 0.5, 0, 1) if m > 1e-8 else np.full_like(x, 0.5)


def _bin(v):
    return (np.asarray(v) > 0.5)


# --- image -> image ---------------------------------------------------------- #
def _identity(v, a, b):
    """恒等写像。HALCON の ``copy_image``（Copy an image and allocate new memory for it.）に対応付けられているが、実装は新しいメモリを確保して複製する ``copy_image`` とは異なり、入力の配列をそのまま返すだけ（複製しない）。

``a``, ``b`` は未使用。sort が ``ANY``（image/region/feature いずれの入力にも一致）なのはこの op だけの特別扱いで、パイプラインの型を変えずに「何もしない」スロットを置くために使う（進化がスロット数を埋めたいだけのとき等）。値を作り直さず入力をそのまま返すため、呼び出し側で戻り値を書き換えると入力の配列も一緒に変わる点に注意。"""
    return v
def _gaussian(v, a, b):
    """等方ガウシアン平滑化。HALCON の ``gauss_filter``（Smooth using discrete Gauss functions.）に相当。

``a`` が標準偏差 σ を ``0.3〜3.0`` に線形に振る（``σ = 0.3 + 2.7a``）。``b`` は未使用。実装は ``scipy.ndimage.gaussian_filter`` をそのまま呼ぶ（境界は scipy 既定の ``reflect``）。ノイズ除去や後段のエッジ検出前のぼかしに使う。σ が大きいほど細部が失われる。"""
    return ndimage.gaussian_filter(v, sigma=0.3 + 2.7 * a)
def _mean_box(v, a, b):
    """矩形窓の単純平均（box）フィルタ。HALCON の ``mean_image``（Smooth by averaging.）に相当。

``a`` が窓の一辺を ``3,5,7,9`` の4段階（``_k(a)``、``a`` を4分割して丸める）に切り替える。``b`` は未使用。ガウシアンより計算は軽いがリンギングが出やすく、エッジがぼやける。"""
    return ndimage.uniform_filter(v, size=_k(a))
def _median(v, a, b):
    """メディアン（中央値）フィルタ。HALCON の ``median_image``（Compute a median filter with various masks.）に相当。

``a`` が窓サイズを ``3,5,7,9``（``_k(a)``）に振る。``b`` は未使用。塩胡椒ノイズなど外れ値に強く、ガウシアン平滑よりエッジを保ちやすい。"""
    return ndimage.median_filter(v, size=_k(a))
def _min_filter(v, a, b):
    """矩形窓内の最小値フィルタ（グレースケール侵食に相当）。HALCON の ``gray_erosion_rect``（Determine the minimum gray value within a rectangle.）に相当。

``a`` が窓サイズを ``3,5,7,9``（``_k(a)``）に振る。``b`` は未使用。明るい小さな構造（点状の輝点等）を消し、暗い領域を広げる。"""
    return ndimage.minimum_filter(v, size=_k(a))
def _max_filter(v, a, b):
    """矩形窓内の最大値フィルタ（グレースケール膨張に相当）。HALCON の ``gray_dilation_rect``（Determine the maximum gray value within a rectangle.）に相当。

``a`` が窓サイズを ``3,5,7,9``（``_k(a)``）に振る。``b`` は未使用。暗い小さな欠陥（ピンホール等）を消し、明るい領域を広げる。"""
    return ndimage.maximum_filter(v, size=_k(a))
def _percentile(v, a, b):
    """任意パーセンタイルのランクフィルタ。HALCON の ``rank_image``（Compute a rank filter with arbitrary masks.）に相当。

``a`` が窓サイズを ``3,5,7,9``（``_k(a)``）に、``b`` が抽出するパーセンタイルを ``5〜95%``（``int(5+90b)``）に振る。``b`` が 0 に近いほど ``_min_filter``、1 に近いほど ``_max_filter``、中間で ``_median`` に近づく——3 op を 1 つに統合した一般形。"""
    return ndimage.percentile_filter(v, percentile=int(5 + 90 * b), size=_k(a))
def _erode_g(v, a, b):
    """グレースケール侵食（暗い側に広げる）。HALCON の ``gray_erosion``（Perform a gray value erosion on an image.）に相当。

``a`` が構造要素（正方形）の一辺を ``3,5,7,9``（``_k(a)``）に振る。``b`` は未使用。実装は矩形窓の最小値フィルタと同じ（``_min_filter`` と等価）で、HALCON の任意形状構造要素とは異なり常に正方形。"""
    return ndimage.grey_erosion(v, size=_k(a))
def _dilate_g(v, a, b):
    """グレースケール膨張（明るい側に広げる）。HALCON の ``gray_dilation``（Perform a gray value dilation on an image.）に相当。

``a`` が構造要素（正方形）の一辺を ``3,5,7,9``（``_k(a)``）に振る。``b`` は未使用。実装は矩形窓の最大値フィルタと同じ（``_max_filter`` と等価）。"""
    return ndimage.grey_dilation(v, size=_k(a))
def _open_g(v, a, b):
    """グレースケールオープニング（侵食してから膨張）。HALCON の ``gray_opening``（Perform a gray value opening on an image.）に相当。

``a`` が構造要素の一辺を ``3,5,7,9``（``_k(a)``）に振る。``b`` は未使用。明るい小さな突起（ノイズ状の輝点）を除去しつつ、大きな明域の形はほぼ保つ。"""
    return ndimage.grey_opening(v, size=_k(a))
def _close_g(v, a, b):
    """グレースケールクロージング（膨張してから侵食）。HALCON の ``gray_closing``（Perform a gray value closing on an image.）に相当。

``a`` が構造要素の一辺を ``3,5,7,9``（``_k(a)``）に振る。``b`` は未使用。暗い小さな欠け（ノイズ状の暗点）を埋めつつ、大きな暗域の形はほぼ保つ。"""
    return ndimage.grey_closing(v, size=_k(a))
def _tophat(v, a, b):
    """ホワイトトップハット（原画像 − オープニング）。HALCON の ``gray_tophat``（Perform a gray value top hat transformation on an image.）に相当。

``a`` が構造要素の一辺を ``3,5,7,9``（``_k(a)``）に振る。``b`` は未使用。背景より明るく、構造要素より小さい局所的な輝点だけを浮き上がらせる（照明ムラを消して欠陥だけ残す用途）。結果は ``_norm`` で最大絶対値 1 に正規化される。"""
    return _norm(ndimage.white_tophat(v, size=_k(a)))
def _bothat(v, a, b):
    """ブラックトップハット（クロージング − 原画像）。HALCON の ``gray_bothat``（Perform a gray value bottom hat transformation on an image.）に相当。

``a`` が構造要素の一辺を ``3,5,7,9``（``_k(a)``）に振る。``b`` は未使用。背景より暗く、構造要素より小さい局所的な暗点だけを浮き上がらせる。結果は ``_norm`` で正規化される。"""
    return _norm(ndimage.black_tophat(v, size=_k(a)))
def _morph_grad(v, a, b):
    """モルフォロジー勾配（膨張 − 侵食）。HALCON の ``gray_range_rect``（Determine the gray value range within a rectangle.）に相当。

``a`` が構造要素の一辺を ``3,5,7,9``（``_k(a)``）に振る。``b`` は未使用。窓内の最大値と最小値の差を返すため、エッジ検出フィルタ（Sobel 等）に似た働きをするが方向を持たない。結果は ``_norm`` で正規化される。"""
    return _norm(ndimage.morphological_gradient(v, size=_k(a)))
def _sobel_mag(v, a, b):
    """Sobel フィルタによる勾配強度（エッジ検出）。HALCON の ``sobel_amp``（Detect edges (amplitude) using the Sobel operator.）に相当。

縦横それぞれの Sobel 応答のユークリッドノルム ``hypot(Gx, Gy)`` を取り、``_norm`` で正規化する。``a``, ``b`` は未使用（カーネルサイズ・向きとも固定）。"""
    return _norm(np.hypot(ndimage.sobel(v, 1), ndimage.sobel(v, 0)))
def _laplace(v, a, b): return _norm(np.abs(ndimage.laplace(v)))
def _prewitt_mag(v, a, b):
    """Prewitt フィルタによる勾配強度（エッジ検出）。HALCON の ``prewitt_amp``（Detect edges (amplitude) using the Prewitt operator.）に相当。

縦横それぞれの Prewitt 応答のユークリッドノルムを取り、``_norm`` で正規化する。``a``, ``b`` は未使用。Sobel と同系統だが平均カーネル（重み無し）を使うぶんノイズにはやや弱い。"""
    return _norm(np.hypot(ndimage.prewitt(v, 1), ndimage.prewitt(v, 0)))


def _roberts_mag(v, a, b):
    """Roberts クロス勾配による勾配強度（エッジ検出）。HALCON の ``roberts``（Detect edges using the Roberts filter.）に相当。

2×2 の対角差分（``v - shift(-1,-1)`` と ``shift(0,-1) - shift(-1,0)``）のユークリッドノルムを ``_norm`` で正規化する。``a``, ``b`` は未使用。カーネルが小さい（2×2）ためノイズに敏感だが応答の局在性は高い。境界は ``_shift_edge`` によりレプリケート（折り返しなし）。"""
    return _norm(np.hypot(v - _shift_edge(v, -1, -1), _shift_edge(v, 0, -1) - _shift_edge(v, -1, 0)))


def _dog(v, a, b):
    """差分ガウシアン（Difference of Gaussians, DoG）。HALCON の ``diff_of_gauss``（Approximate the LoG operator (Laplace of Gaussian).）に相当。

``a`` が細かい方のぼかし σ₁ を ``0.5〜2.5`` に、``b`` が粗い方のぼかし σ₂ を ``1.0〜5.0`` に振る（``|gauss(σ₁) - gauss(σ₂)|`` を ``_norm`` で正規化）。2 つのスケールの中間の大きさを持つ斑点・エッジを強調する、LoG の近似。σ₁ と σ₂ が近いほど応答は弱くなる。"""
    return _norm(np.abs(ndimage.gaussian_filter(v, 0.5 + 2.0 * a) - ndimage.gaussian_filter(v, 1.0 + 4.0 * b)))


def _gamma(v, a, b):
    """ガンマ補正（べき乗変換）。HALCON の ``pow_image``（Raise an image to a power.）に相当。

``a`` が指数 γ を ``0.5〜2.0`` に振る（``v**γ``、入力は先に ``[0,1]`` へ clip）。``b`` は未使用。γ<1 で暗部を持ち上げ（明るくする）、γ>1 で暗部をさらに沈める（コントラストを付ける）。"""
    return np.clip(v, 0, 1) ** (0.5 + 1.5 * a)
def _invert(v, a, b):
    """階調反転（ネガポジ反転）。HALCON の ``invert_image``（Invert an image.）に相当。

``1 - clip(v,0,1)`` を返すだけ。``a``, ``b`` は未使用。"""
    return 1.0 - np.clip(v, 0, 1)
def _scale_clip(v, a, b):
    """ゲインとオフセットによる線形階調変換。HALCON の ``scale_image``（Scale the gray values of an image.）に相当。

``a`` がゲイン（コントラスト）を ``0.5〜2.0`` 倍に、``b`` がオフセット（明るさ）を ``-0.5〜+0.5`` に振る（``clip(gain*v + offset, 0, 1)``）。``b=0.5`` がオフセット 0（変化なし）に対応する点に注意。"""
    return np.clip((0.5 + 1.5 * a) * v + (b - 0.5), 0, 1)


def _equalize(v, a, b):
    """ヒストグラム均等化（線形化）。HALCON の ``equ_histo_image``（Histogram linearization of images）に相当。

``a``, ``b`` は未使用。``[0,1]`` を 256 ビンに分けたヒストグラムの累積分布関数（CDF）を求め、各画素値をその CDF で置き換えることで、出力のヒストグラムがほぼ一様になるよう引き伸ばす。コントラストが低い（値域が狭い）画像を見やすくするのに使う。全画素が同一値だと CDF が定義できず ``cdf[-1]`` が 0 になり、変換は事実上恒等（変化なし）になる。"""
    x = np.clip(v, 0, 1); hist, edges = np.histogram(x, 256, (0, 1))
    cdf = np.cumsum(hist).astype(np.float64); cdf = cdf / cdf[-1] if cdf[-1] > 0 else cdf
    return np.interp(x.ravel(), (edges[:-1] + edges[1:]) / 2, cdf).reshape(x.shape)


def _sigmoid(v, a, b):
    """ロジスティック関数（シグモイド）による S 字型のコントラスト強調。HALCON の ``scale_image_max``（Maximum gray value spreading in the value range 0 to 255.）に対応付けられているが、ダイナミックレンジを最大まで引き伸ばす ``scale_image_max`` とは処理内容が異なる（近似というより別物に近い）。

``a`` が S字の傾き ``k = 4 + 12a``（``4〜16``）を、``b`` が中心（変曲点）の位置 ``x0 = 0.2 + 0.6b``（``0.2〜0.8``）を振る（``1/(1+exp(-k*(v-x0)))``）。``x0`` 付近の階調差を強調し、両端の階調差は圧縮する。"""
    return 1.0 / (1.0 + np.exp(-(4.0 + 12.0 * a) * (np.clip(v, 0, 1) - (0.2 + 0.6 * b))))


def _bilateral(v, a, b):
    """エッジ保存平滑化（bilateral filter）。HALCON の ``bilateral_filter``（bilateral filtering of an image.）に相当。

``a`` が空間方向の広がり ``σ_s = 1.0 + 3.0a`` を、``b`` が明るさ方向の許容差 ``σ_r = 0.05 + 0.4b`` を振る。近傍窓は半径 ``r=2``（5×5）固定で ``a`` では変わらない。近傍の重みは ``exp(-距離²/2σ_s²) × exp(-明度差²/2σ_r²)`` の積で、明度差が大きい（=エッジをまたぐ）画素は重みが小さくなるため、平滑化しつつ輪郭を保てる。窓内を Python の二重ループで回すため他の平滑化 op より遅い。"""
    ss, sr, r = 1.0 + 3.0 * a, 0.05 + 0.4 * b, 2
    out = np.zeros_like(v, np.float64); wsum = np.zeros_like(v, np.float64)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            sh = _shift_edge(v, dy, dx)   # edge-clamped: never wraps to the opposite border
            w = np.exp(-(dx * dx + dy * dy) / (2 * ss * ss)) * np.exp(-((sh - v) ** 2) / (2 * sr * sr))
            out += w * sh; wsum += w
    return out / np.maximum(wsum, 1e-8)


def _std_filter(v, a, b):
    """局所窓内の標準偏差（テクスチャの粗さの指標）。HALCON の ``deviation_image``（Calculate the standard deviation of gray values within rectangular windows.）に相当。

``a`` が窓サイズを ``3,5,7,9``（``_k(a)``）に振る。``b`` は未使用。``E[v²]-E[v]²`` を窓ごとに求めて平方根を取り（負の丸め誤差は 0 にクランプ）、``_norm`` で正規化する。値が大きいほどその窓内の階調が激しく変化している（テクスチャがある/エッジが多い）ことを示す。"""
    k = _k(a); m = ndimage.uniform_filter(v, k); m2 = ndimage.uniform_filter(v * v, k)
    return _norm(np.sqrt(np.maximum(m2 - m * m, 0.0)))


def _fft_mask(v, cutoff, high):
    H, W = v.shape
    rad = np.sqrt(np.fft.fftfreq(H)[:, None] ** 2 + np.fft.fftfreq(W)[None, :] ** 2)
    mask = (rad > cutoff) if high else (rad <= cutoff)
    return np.real(np.fft.ifft2(np.fft.fft2(v) * mask))


def _lowpass(v, a, b):
    """FFT による低域通過フィルタ（ぼかし）。HALCON に対応する単体 op は指定されていない。

``a`` が遮断周波数 ``cutoff = 0.05 + 0.4a``（正規化周波数、0〜0.5 がナイキストまでの範囲）を振る。``b`` は未使用。2-D FFT で ``rad <= cutoff`` の低周波成分だけを残し、逆 FFT の実部を ``[0,1]`` に clip する。``a`` が小さいほど強くぼける。境界は周期的（FFT の性質上、画像端は反対側と隣接するとみなされる）に扱われ、``ndimage`` 系フィルタの ``reflect``/``edge`` とは境界処理が異なる点に注意。"""
    return np.clip(_fft_mask(v, 0.05 + 0.4 * a, False), 0, 1)
def _highpass(v, a, b):
    """FFT による高域通過フィルタ（輪郭・高周波成分の抽出）。HALCON の ``highpass_image``（Extract high frequency components from an image.）に相当。

``a`` が遮断周波数 ``cutoff = 0.02 + 0.3a`` を振る。``b`` は未使用。2-D FFT で ``rad > cutoff`` の高周波成分だけを残し、逆 FFT の実部を ``_signed01`` で ``[0,1]`` へ写す（0.5 が「変化なし」、それより明暗が高周波成分の符号を表す）。低域フィルタ同様、境界は周期的（FFT）に扱われる。"""
    return _signed01(_fft_mask(v, 0.02 + 0.3 * a, True))
def _unsharp(v, a, b):
    """Unsharp mask. ★出口で [0,1] に clip する(2026-09-02)。

    ``v + k*(v - blur)`` は定義上オーバーシュートする(実測 min=-0.1499 /
    max=+1.1499)。`_apply` は段間で同じ clip を掛けるので **パイプライン結果は
    ビット不変**だが、`fullseye.apply` を単発で呼ぶ経路だけは生値が出ていて、
    `image` の [0,1] 契約を破ったまま保存すると黒/白に潰れていた。GPU 側
    (`accel._unsharp`)も同じ clip を持つ。"""
    return np.clip(v + (1.5 * a) * (v - ndimage.gaussian_filter(v, 0.5 + 1.5 * b)), 0, 1)


# --- image -> region (segmentation) ------------------------------------------ #
def _threshold(v, a, b):
    """大域しきい値処理（グローバルスレッショルド）。HALCON の ``threshold``（Segment an image using global threshold.）に相当。

``a`` がしきい値そのもの（``0〜1``）で、``v > a`` を満たす画素を前景（1）とする region を返す。``b`` は未使用。HALCON の ``threshold`` は下限・上限の 2 値を取れる帯域しきい値だが、この実装は下限のみの片側しきい値。"""
    return (v > a).astype(np.float64)


def _otsu(v, a, b):
    """大津の判別分析法（Otsu's method）による自動しきい値処理。HALCON の ``binary_threshold``（Segment an image using binary thresholding.）に相当。

``a``, ``b`` は未使用（しきい値は入力から自動で決まる）。``[0,1]`` を 256 ビンのヒストグラムに分け、クラス間分散 ``ω(1-ω)`` を最大化するしきい値を全探索して選び、それより大きい画素を前景とする。前景・背景 2 クラスの分離を仮定するため、ヒストグラムが単峰（1 山）の画像では意図しない位置で切れることがある。"""
    x = np.clip(v, 0, 1); hist, edges = np.histogram(x, 256, (0, 1))
    p = hist.astype(np.float64) / max(1, hist.sum()); omega = np.cumsum(p)
    mids = (edges[:-1] + edges[1:]) / 2; mu = np.cumsum(p * mids); mu_t = mu[-1]
    den = omega * (1 - omega); sb = np.where(den > 1e-12, (mu_t * omega - mu) ** 2 / np.maximum(den, 1e-12), 0.0)
    return (x > mids[int(np.argmax(sb))]).astype(np.float64)


def _dyn_threshold(v, a, b):
    return (v > ndimage.uniform_filter(v, size=_k(a)) + (b - 0.5) * 0.4).astype(np.float64)


# --- region -> region -------------------------------------------------------- #
def _reg_erode(v, a, b):
    """領域（region）の二値侵食。HALCON の ``erosion_circle``（Erode a region with a circular structuring element.）に相当。

``a`` が反復回数を ``1〜4``（``_it(a)``）に振る。``b`` は未使用。構造要素は ``scipy.ndimage.binary_erosion`` の既定（十字形、4近傍相当）で、HALCON の円形構造要素とは形が異なる（近似）。入力は ``v > 0.5`` で二値化してから処理する。"""
    return ndimage.binary_erosion(_bin(v), iterations=_it(a)).astype(np.float64)
def _reg_dilate(v, a, b):
    """領域（region）の二値膨張。HALCON の ``dilation_circle``（Dilate a region with a circular structuring element.）に相当。

``a`` が反復回数を ``1〜4``（``_it(a)``）に振る。``b`` は未使用。構造要素は scipy 既定の十字形（円形ではない、近似）。"""
    return ndimage.binary_dilation(_bin(v), iterations=_it(a)).astype(np.float64)
def _reg_open(v, a, b):
    """領域（region）の二値オープニング（侵食してから膨張）。HALCON の ``opening_circle``（Open a region with a circular structuring element.）に相当。

``a`` が反復回数を ``1〜4``（``_it(a)``）に振る。``b`` は未使用。細い突起や小さな孤立領域を除去する。構造要素は scipy 既定の十字形。"""
    return ndimage.binary_opening(_bin(v), iterations=_it(a)).astype(np.float64)
def _reg_close(v, a, b):
    """領域（region）の二値クロージング（膨張してから侵食）。HALCON の ``closing_circle``（Close a region with a circular structuring element.）に相当。

``a`` が反復回数を ``1〜4``（``_it(a)``）に振る。``b`` は未使用。細い切れ込みや小さな穴を埋める。``border_value=1`` を指定しているため画像端は前景として扱われる。"""
    return ndimage.binary_closing(_bin(v), iterations=_it(a), border_value=1).astype(np.float64)
def _fill_holes(v, a, b):
    """領域内の穴埋め。HALCON の ``fill_up``（Fill up holes in regions.）に相当。

``a``, ``b`` は未使用。前景に完全に囲まれた背景画素（穴）をすべて前景に変える（``scipy.ndimage.binary_fill_holes``）。画像端に接する背景は穴とみなされないため埋まらない。"""
    return ndimage.binary_fill_holes(_bin(v)).astype(np.float64)


def _select_largest(v, a, b):
    """最大面積の連結領域だけを残す。HALCON の ``select_shape_std``（Select regions of a given shape.）に相当。

``a``, ``b`` は未使用（常に「最大」を選ぶ）。連結成分ラベリング後、画素数が最大の 1 成分だけを 1、それ以外を 0 にする。入力に前景が無ければ全 0 を返す。HALCON の ``select_shape_std`` は面積以外の形状基準（円形度等）や複数選択にも対応するが、この実装は面積最大の単一選択のみ。"""
    lab, n = ndimage.label(_bin(v))
    if n == 0:
        return np.zeros_like(v, np.float64)
    sizes = ndimage.sum(np.ones_like(lab), lab, index=range(1, n + 1))
    return (lab == (int(np.argmax(sizes)) + 1)).astype(np.float64)


def _remove_small(v, a, b):
    """小さい連結領域を面積で除去する。HALCON の ``select_shape``（Choose regions with the aid of shape features.）に相当。

``a`` が除去のしきい値（画素数）を、画像全体の画素数に対する割合 ``0.01〜0.16``（``(0.01+0.15a) * 画素数``）として振る。``b`` は未使用。しきい値以上の面積を持つ連結成分だけを残す。連結性は scipy ``label`` の既定（4連結）。"""
    lab, n = ndimage.label(_bin(v))
    if n == 0:
        return np.zeros_like(v, np.float64)
    sizes = ndimage.sum(np.ones_like(lab), lab, index=range(1, n + 1))
    thr = (0.01 + 0.15 * a) * v.size
    keep = np.zeros_like(v, np.float64)
    for i, s in enumerate(sizes, 1):
        if s >= thr:
            keep[lab == i] = 1.0
    return keep


def _invert_region(v, a, b):
    """領域の補集合（前景/背景の反転）。HALCON の ``complement``（Return the complement of a region.）に相当。

``a``, ``b`` は未使用。``v > 0.5`` で二値化してから 1 から引くだけ（前景と背景を入れ替える）。"""
    return 1.0 - _bin(v).astype(np.float64)


# --- region -> feature (measurement) ----------------------------------------- #
def _blob_count(v, a, b, connectivity=8):
    """Number of connected components in the region (HALCON `count_obj`).

    2026-08-30: 8 連結既定に修正(HALCON パリティ — `connection`/計数の既定は
    8 連結。従来は scipy.ndimage.label の既定 = 4 連結で、対角接触した 2 画素を
    2 個と数えていた: KNOWN_ISSUES #1)。旧 4 連結は connectivity=4 で。
    """
    st = ndimage.generate_binary_structure(2, 2 if int(connectivity) == 8 else 1)
    _, n = ndimage.label(_bin(v), structure=st)
    return np.float64(n)


def _area_frac(v, a, b):
    """領域が占める画素の割合（面積率）を返す特徴量。HALCON の ``area_center``（Area and center of regions.）とは異なり、面積のみを返し重心は計算しない（機能の一部だけの対応）。

``a``, ``b`` は未使用。``v > 0.5`` で二値化した画素の平均値（= 前景画素数 / 全画素数）をスカラーで返す。値域は ``[0,1]``。"""
    return np.float64(np.mean(_bin(v)))


# --- more image -> image ----------------------------------------------------- #
def _grad_dir(v, a, b):
    """勾配方向（エッジの向き）を画像として返す。対応する HALCON op は指定されていない（fullseye 独自）。

``a``, ``b`` は未使用。Sobel 応答から ``atan2(Gy, Gx)`` で角度（``-π〜π``）を求め、``[0,1]`` へ線形に写す。``0`` と ``1`` はどちらも同じ角度（``-π``≡``π``）に対応する周期量である点に注意——連続的に変化する向きでも出力が 0 と 1 の間で不連続にジャンプし得る。平坦な領域では勾配がほぼ 0 で方向が不定になり、ノイズの影響を受けやすい。"""
    return (np.arctan2(ndimage.sobel(v, 0), ndimage.sobel(v, 1)) + np.pi) / (2 * np.pi)


def _log(v, a, b):
    """ラプラシアン・オブ・ガウシアン（LoG）フィルタ。HALCON の ``laplace_of_gauss``（LoG-Operator (Laplace of Gaussian).）に相当。

``a`` がガウシアンの標準偏差 σ を ``0.5〜3.0`` に振る。``b`` は未使用。``scipy.ndimage.gaussian_laplace`` の絶対値を ``_norm`` で正規化する（符号を捨てているため、暗背景上の明斑点と明背景上の暗斑点を区別できない）。ブロブ（斑点状構造）検出やエッジ検出に使う。"""
    return _norm(np.abs(ndimage.gaussian_laplace(v, sigma=0.5 + 2.5 * a)))


# --- more image -> region ---------------------------------------------------- #
def _canny(v, a, b):
    """簡易 Canny 風エッジ検出（region を返す）。HALCON の ``edges_image``（Extract edges using Deriche, Lanser, Shen, or Canny filters.）に対応付けられているが、非極大抑制やヒステリシスしきい値処理は行わない簡略版（近似）。

``a`` が事前平滑化のガウシアン σ を ``0.5〜2.0`` に、``b`` がしきい値を ``0.1〜0.6`` に振る。ガウシアンでぼかした画像に Sobel 勾配強度を掛け、正規化した値を ``b`` で二値化するだけ——本家 Canny の細線化（1画素幅への収束）は無いため、エッジは本来の Canny より太く、複数画素にまたがって残る。"""
    g = ndimage.gaussian_filter(v, 0.5 + 1.5 * a)
    m = _norm(np.hypot(ndimage.sobel(g, 1), ndimage.sobel(g, 0)))
    return (m > (0.1 + 0.5 * b)).astype(np.float64)


def _local_max(v, a, b):
    return ((v >= ndimage.maximum_filter(v, size=_k(a))) & (v > (0.3 + 0.4 * b))).astype(np.float64)


# --- more region ops --------------------------------------------------------- #
def _dist_transform(v, a, b):
    """ユークリッド距離変換。HALCON の ``distance_transform``（Compute the distance transformation of a region.）に相当。

``a``, ``b`` は未使用。各前景画素について最も近い背景画素までのユークリッド距離を求め（``scipy.ndimage.distance_transform_edt``）、``_norm`` でその画像内の最大値を 1 に正規化する（画像間で絶対距離の比較はできない）。骨格化・粒の中心検出等の前処理に使う。"""
    return _norm(ndimage.distance_transform_edt(_bin(v)))


def _region_boundary(v, a, b):
    """領域の輪郭（境界リング）を抽出する。HALCON の ``boundary``（Reduce a region to its boundary.）に相当。

``a``, ``b`` は未使用。二値化した領域から、1 回侵食した領域を差し引くことで、幅 1 画素の外周だけを残す。出力は region（0/1）のまま。"""
    return (_bin(v).astype(np.float64) - ndimage.binary_erosion(_bin(v)).astype(np.float64)).clip(0, 1)


def _convex_fill(v, a, b):
    """凸包に近い形へ穴・くびれを埋める（クロージングによる近似）。HALCON の ``shape_trans``（Transform the shape of a region.）の凸包変換に相当することを意図しているが、実装は反復回数の多いクロージングであり、厳密な凸包計算ではない（近似）。

``a`` が反復回数を ``3〜6``（``_it(a)+2``）に振る。``b`` は未使用。``border_value=1`` の二値クロージングを掛けるだけなので、反復回数を超える大きさのくびれ・穴は埋まらない（真の凸包なら必ず埋まる）。"""
    return ndimage.binary_closing(_bin(v), iterations=_it(a) + 2, border_value=1).astype(np.float64)


# --- image -> contour (XLD) -------------------------------------------------- #
def _edges_sub_pix(v, a, b):
    """Gradient-band edge contours, refined to **sub-pixel** accuracy along the normal.

    ``a`` = 勾配強度のしきい値 ``0.15 + 0.5a``。返すのは XLD 輪郭 dict
    ``{"shape", "cs": [(N,2) の (row, col), ...]}``。

    ★2026-09-02: それまで返していたのは ``np.where`` が出す **整数の画素座標**
    そのもので、``sub_pix`` を名乗りながらサブピクセル精度が無かった
    (KNOWN_ISSUES #3 / docs/FULLSEYE_OP_ARTICLE_SPEC.md に「ピクセル精度実装」と
    明記されていた)。放物線当てはめによる法線方向の精密化を追加して、名前と
    実態を合わせた。**点の個数・連結成分の分け方は変えていない**(座標が 1 px
    未満動くだけ)ので、下流の輪郭選別・計数はそのまま。

    実測(真の位置が列 20.37 の合成ステップエッジ、a=0.2): 旧実装が返す列は
    {20.0, 21.0} のみで平均絶対誤差 **0.500 px**、精密化後は {20.324, 20.370} で
    平均絶対誤差 **0.0228 px**(約 22 倍改善)。

    正直な限界: 抽出母集団は「しきい値を超えた勾配帯」全体(非極大抑制は
    していない)なので、太いエッジでは帯の全画素が稜線へ寄せられて **重なった
    点**になる。1 画素幅の連鎖が要るなら `canny` を、より高精度な等値線が要るなら
    `threshold_sub_pix`(実測 0.001 px)を使うこと。
    """
    from backend_safe import gradient_normals, subpixel_refine_edges

    g, ny, nx = gradient_normals(v)
    m = _norm(g)
    lab, n = ndimage.label(m > (0.15 + 0.5 * a), structure=np.ones((3, 3)))
    cs = []
    for i in range(1, n + 1):
        ys, xs = np.where(lab == i)
        if len(ys) >= 3:
            pts = np.stack([ys, xs], 1).astype(np.float64)
            cs.append(subpixel_refine_edges(pts, m, ny, nx))
    return {"shape": v.shape, "cs": cs}


# --- contour -> contour ------------------------------------------------------ #
def _select_contours(cv, a, b):
    """点数（長さ）でフィルタして XLD 輪郭を選別する。HALCON の ``select_contours_xld``（Select XLD contours according to several features.）に相当。

``a`` が残す最小点数のしきい値を ``3〜43``（``3 + int(40a)``）に振る。``b`` は未使用。輪郭を構成する点の数（≒長さ）がしきい値未満のものを丸ごと捨てる。HALCON 版は点数以外にも円形度・凸性などの特徴で選べるが、この実装は点数のみ。"""
    thr = 3 + int(a * 40)
    return {"shape": cv["shape"], "cs": [c for c in cv["cs"] if len(c) >= thr]}


def _smooth_contours(cv, a, b):
    """移動平均による XLD 輪郭の平滑化。HALCON の ``smooth_contours_xld``（Smooth an XLD contour.）に相当。

``a`` が平滑化窓の半幅を ``1〜4``（窓長 ``2w+1 = 3,5,7,9``）に振る。``b`` は未使用。各輪郭の ``(row, col)`` 列を独立に等重み移動平均（``np.convolve`` の ``"same"`` モード）で均す。点数が窓長の 2 倍以下の短い輪郭はそのまま素通しする（平滑化されない）。"""
    w = 1 + int(a * 3); out = []
    for c in cv["cs"]:
        if len(c) > 2 * w + 1:
            k = np.ones(2 * w + 1) / (2 * w + 1)
            out.append(np.stack([np.convolve(c[:, 0], k, "same"), np.convolve(c[:, 1], k, "same")], 1))
        else:
            out.append(c)
    return {"shape": cv["shape"], "cs": out}


def _fit_line_contours(cv, a, b):
    """各 XLD 輪郭を 1 本の直線で近似する。HALCON の ``fit_line_contour_xld``（Approximate XLD contours by line segments.）に相当。

``a``, ``b`` は未使用。輪郭点群の重心を通り、SVD（特異値分解）で求めた第一主成分方向を直線の向きとして採用し（全点との距離二乗和を最小化する直線）、元の点群の射影範囲に等間隔に打ち直した点列に置き換える。HALCON 版は折れ線（複数線分）に分割できるが、この実装は輪郭全体を 1 本の直線にする点が異なる。点が 2 点未満の輪郭はそのまま返す。"""
    out = []
    for c in cv["cs"]:
        if len(c) >= 2:
            mean = c.mean(0); _, _, vt = np.linalg.svd(c - mean); d = vt[0]
            t = (c - mean) @ d
            out.append(mean + np.outer(np.linspace(t.min(), t.max(), max(2, len(c))), d))
        else:
            out.append(c)
    return {"shape": cv["shape"], "cs": out}


# --- contour -> region ------------------------------------------------------- #
def _contours_to_region(cv, a, b):
    """XLD 輪郭をラスタ化して region に変換する。HALCON の ``gen_region_contour_xld``（Create a region from an XLD contour.）に相当。

``a`` が仕上げに掛ける膨張の反復回数を ``1〜3``（``1 + int(2a)``）に振る。``b`` は未使用。輪郭点の実数座標を最近傍の画素へ丸めてマスクを立て、点間が疎で線がつながらないぶんを膨張で補う（サブピクセル精度は失われる）。"""
    H, W = cv["shape"]; mask = np.zeros((H, W), np.float64)
    for c in cv["cs"]:
        idx = np.clip(np.round(c).astype(int), [0, 0], [H - 1, W - 1])
        mask[idx[:, 0], idx[:, 1]] = 1.0
    return ndimage.binary_dilation(mask > 0.5, iterations=1 + int(a * 2)).astype(np.float64)


# --- contour -> feature ------------------------------------------------------ #
def _count_contours(cv, a, b):
    """輪郭（オブジェクト）の本数を返す特徴量。HALCON の ``count_obj``（Number of objects in a tuple.）に相当。

``a``, ``b`` は未使用。輪郭リストの長さをそのまま返すだけ。"""
    return np.float64(len(cv["cs"]))


def _total_length(cv, a, b):
    """全 XLD 輪郭の合計弧長を返す特徴量。HALCON の ``length_xld``（Length of contours or polygons.）に相当。

``a``, ``b`` は未使用。各輪郭について隣接点間のユークリッド距離を足し合わせたもの（折れ線の全長）を、全輪郭ぶん合算する。点が 2 点未満の輪郭は長さ 0 として扱われる。"""
    tot = 0.0
    for c in cv["cs"]:
        if len(c) >= 2:
            tot += float(np.sum(np.hypot(np.diff(c[:, 0]), np.diff(c[:, 1]))))
    return np.float64(tot)


# --- image -> match (template matching) -------------------------------------- #
def _ncc_map(v, T):
    """Normalized cross-correlation of template `T` over image `v` (Lewis 1995).

    Value at (y,x) is Pearson's correlation between `T` and the T-sized window
    centred there::

        sum_w (I_w - mean_w)(T - mean_T) / (||I_w - mean_w|| * ||T - mean_T||)

    so it is bounded to [-1,1], invariant to the window's brightness/contrast,
    and 1.0 exactly for a match up to a positive affine map. Raw correlation
    (no local normalization) instead peaks on whatever is brightest/largest.
    Positions where the template does not fully overlap the image, flat windows
    and a zero-energy template all score 0 (no match).
    """
    v = np.asarray(v, np.float64)
    T = np.asarray(T, np.float64)
    if T.ndim != v.ndim:
        return np.zeros_like(v)
    Tz = T - float(T.mean())
    tnorm = float(np.sqrt(np.sum(Tz * Tz)))
    if tnorm < 1e-12:
        return np.zeros_like(v)
    num = ndimage.correlate(v, Tz, mode="constant")          # sum(Tz) == 0 -> mean-free
    m1 = ndimage.uniform_filter(v, size=T.shape, mode="constant")
    m2 = ndimage.uniform_filter(v * v, size=T.shape, mode="constant")
    den = np.sqrt(np.maximum(m2 - m1 * m1, 0.0) * float(T.size)) * tnorm
    ok = np.zeros(v.shape, bool)                             # full-overlap positions only
    lo = tuple(s // 2 for s in T.shape)
    hi = tuple(n - (s - 1 - s // 2) for n, s in zip(v.shape, T.shape))
    if all(h > l for l, h in zip(lo, hi)):
        ok[tuple(slice(l, h) for l, h in zip(lo, hi))] = True
    out = np.zeros_like(v)
    np.divide(num, den, out=out, where=ok & (den > 1e-12))
    return np.clip(out, -1.0, 1.0)


def _ncc_locate(v, a, b):
    """正規化相互相関（NCC）によるテンプレートマッチングで最良位置を探す。HALCON の ``find_ncc_model``（Find the best matches of an NCC model in an image.）に相当。

``a``, ``b`` は未使用——テンプレートは引数ではなく ``set_match_template`` でスレッドローカルな ``_MATCH_CTX`` に事前登録しておく（マッチング系 op 共通の作法、``_MatchCtx`` の docstring 参照）。``_ncc_map``（NCC 相関マップ、Lewis 1995 の定義で ``[-1,1]``）を計算し、その最大値の位置を ``[相関値, y, x]`` で返す。テンプレート未設定、または入力が 2 次元画像でない場合は ``[0,0,0]``（no-match）を返す——fail-closed。回転・スケール変化には非対応（``_shape_locate`` は回転を扱う）。"""
    T = _MATCH_CTX.get("template")
    if T is None or not (isinstance(v, np.ndarray) and v.ndim == 2):
        return np.array([0.0, 0.0, 0.0])
    corr = _ncc_map(v, T)
    idx = np.unravel_index(int(np.argmax(corr)), corr.shape)
    return np.array([float(corr[idx]), float(idx[0]), float(idx[1])])


# --- geometry (image -> image; calibration/rectification building blocks) ----- #
def _rotate_img(v, a, b):
    """Rotate about the image centre by ``-45° + 90°·a`` (a=0.5 → 0°). ``b`` unused.

    ★呼び出し規約(2026-09-02 に明文化。実装は変えていない):

    * **キャンバスを変えない** (``reshape=False``)。出力の shape は入力と同じで、
      回転で枠外へ出た画素は捨てられる。
    * **枠外は鏡映で埋める** (``mode="reflect"``)。つまり回すと **四隅に元画像が
      折り返して写り込む**(帳票を回すと隅に鏡文字が出る)。

    どちらが正典かは用途で割れる。**この op の正典は「連鎖しても常に同じ形・
    同じ値域の画像が出ること」** — 進化パイプラインは image を段間で無条件に
    繋ぐので、shape が変わる/枠外に定数が入ると後段の統計(平均・分散・
    ヒストグラム)が回転量に依存して動いてしまう。鏡映は「無から作った定数」で
    はなく画像自身の統計を保つので、この用途ではこちらを採る。

    **deskew(帳票の傾き補正)には向かない**: 折り返した鏡文字が OCR / 二値化に
    そのまま乗る。背景色で埋めたい場合はこの op を使わず、
    ``scipy.ndimage.rotate(v, ang, reshape=True, mode="constant", cval=bg)`` を
    直接呼ぶこと(``fullseye.apply`` の 2 つまみ界面では背景色を渡せない)。
    同じ規約が backends_auto の ``rotate_image`` (``_sh_geom`` kind="rotate")にも
    そのまま当てはまる。
    """
    return np.clip(ndimage.rotate(v, angle=-45 + 90 * a, reshape=False, mode="reflect"), 0, 1)


def _rescale_img(v, a, b):
    """Isotropic centre-preserving rescale by ``s = 0.7 + 0.6·a``, canvas kept.

    ``b`` = **補間の次数** — ``(0, 1, 3, 3)[min(3, int(4b))]``(0 = 最近傍、
    1 = 双一次、3 = 三次スプライン)。``b=0.5`` は 3 次で、``b`` が死んでいた頃の
    既定(``ndimage`` の order=3)と **ビット一致**する。

    ★2026-09-02: それまで ``rescale_img`` / ``zoom_image_factor`` /
    ``zoom_image_size`` は **3 つとも同じ実装**(実測: 相互の最大差 0.0 と
    4.9e-14)で、3 つとも ``b`` を使っていなかった。3 つの役割を分けた:

    * ``rescale_img``      — 等方倍率 1 つ + **補間次数**(この関数)
    * ``zoom_image_factor``— 縦横 **2 つの倍率**(HALCON の ScaleHeight/ScaleWidth)
    * ``zoom_image_size``  — **目標サイズ**指定(出力 shape が変わる)

    HALCON 名も実態に合わせて ``zoom_image_size`` → ``zoom_image_factor`` へ
    付け替えた(この op はサイズではなく倍率で駆動するため)。
    """
    s = 0.7 + 0.6 * a
    order = (0, 1, 3, 3)[min(3, int(np.clip(b, 0.0, 1.0) * 4))]
    off = (v.shape[0] * (1 - 1 / s) / 2, v.shape[1] * (1 - 1 / s) / 2)
    return np.clip(ndimage.affine_transform(v, np.array([1 / s, 1 / s]), offset=off,
                                            order=order, mode="reflect"), 0, 1)


def _affine_warp(v, a, b):
    """任意のアフィン変換（回転+せん断）を画像に適用する。HALCON の ``affine_trans_image``（Apply an arbitrary affine 2D transformation to images.）に相当。

``a`` が回転角を ``-20°〜+20°`` に、``b`` がせん断量を ``-0.2〜+0.2`` に振る。回転中心は画像の中心、境界は ``reflect``（鏡映）で埋め、結果を ``[0,1]`` に clip する。平行移動・拡大縮小は含まない（``_rescale_img``/``_rotate_img`` が別 op として存在）。"""
    ang = np.deg2rad(-20 + 40 * a); sh = (b - 0.5) * 0.4
    M = np.array([[np.cos(ang), -np.sin(ang) + sh], [np.sin(ang), np.cos(ang)]])
    c = np.array(v.shape) / 2
    return np.clip(ndimage.affine_transform(v, M, offset=c - M @ c, mode="reflect"), 0, 1)


# --- more filters (OpenCV/skimage families) ---------------------------------- #
def _gabor(v, a, b):
    """Gabor energy |v * g| — an oriented band-pass texture response.

    - ``a`` — **向き** ``θ = π·a`` [rad]。カーネルの余弦は回転後の x 方向に走るので、
      ``a=0`` (θ=0) は **縦縞**(列方向に明暗が変わる模様)に最も強く応答し、
      ``a=0.5`` (θ=90°) は **横縞**に応答する。``a=1`` は θ=180° で a=0 と同じ向き。
    - ``b`` — 空間周波数 ``0.1 + 0.3·b`` [cycles/px]。

    ★正規化(2026-09-02 の修正): **カーネルの L1 ノルムで割る固定スケール**。
    以前は ``_norm`` = その画像での最大絶対値で割っていたため、**応答の大小そのもの
    が消えていた**。実測(96×96 の横縞、周波数 0.25): 生の畳み込みの平均振幅は
    θ=0° が 0.0165、θ=90° が 0.9077 で **54.9 倍**の差があるのに、``_norm`` を通すと
    平均は 0.3554 対 0.4790 = **1.35 倍**まで潰れていた —— 向きを見分けるための
    特徴量なのに識別力が消えていた(向きごとに別の除数で割っていたのだから当然)。
    ``|v| <= 1`` なら ``|v * g| <= sum|g|`` なので L1 で割れば値域 [0,1] を保ったまま
    **op を跨いで比較できる絶対スケール**になる。
    """
    theta = np.pi * a; freq = 0.1 + 0.3 * b; k = 7
    yy, xx = np.mgrid[-k:k + 1, -k:k + 1]
    xr = xx * np.cos(theta) + yy * np.sin(theta)
    g = np.exp(-(xx * xx + yy * yy) / 8.0) * np.cos(2 * np.pi * freq * xr)
    g = g - g.mean()   # DC-free (zero-mean) kernel: a Gabor is band-pass, not a brightness detector
    l1 = float(np.abs(g).sum())
    resp = np.abs(ndimage.convolve(np.clip(v, 0, 1), g, mode="reflect"))
    return np.clip(resp / l1, 0, 1) if l1 > 1e-12 else np.zeros_like(resp)


def _clip_limit_cdf(hist, climit_counts):
    """Contrast-limited CDF: clip the histogram, redistribute the excess, normalise.

    Zuiderveld (1994) の CLAHE の "CL"。各ビンを ``climit_counts`` で切り、
    切り落とした総量を全ビンへ均等に配り直してから累積して [0,1] に正規化する。
    再配分するので **CDF の終端は常に 1.0**(= 画像の最大値は 1.0 に写る)。

    ``climit_counts`` はビンの **平均カウント** を単位にした倍率で与えるのが CLAHE の
    習わし(OpenCV の ``clipLimit`` と同じ意味)。1.0 倍 = 全ビンを平均に均す =
    トーンマップが直線 = コントラスト強調ゼロ、256 倍(= ビン数)= 1 ビンが取り得る
    最大カウントなので **切り取りが一度も効かない = 素の AHE**。
    """
    h = np.asarray(hist, np.float64)
    total = float(h.sum())
    if total <= 0:
        return h
    excess = float(np.sum(np.maximum(h - climit_counts, 0.0)))
    if excess > 0:
        h = np.minimum(h, climit_counts) + excess / h.size
    cdf = np.cumsum(h)
    return cdf / cdf[-1] if cdf[-1] > 0 else cdf


def _clahe(v, a, b):
    """Contrast-Limited Adaptive Histogram Equalization (tiled, bilinearly blended).

    - ``a`` — タイル数 ``nb = 2 + int(3a)`` (画像を nb×nb に分割)
    - ``b`` — **clip limit**。ビン平均カウントに対する倍率 ``256**b`` で与える
      (``b=0`` → 1 倍 = 完全に平坦化されたヒストグラム = トーンマップ直線 =
      強調ゼロ、``b=1`` → 256 倍 = 1 ビンが取り得る最大値なので切り取りが
      効かない = 素の AHE、``b=0.5`` → 16 倍。OpenCV の既定 ``clipLimit=40`` は
      おおよそ ``b=0.665``)。

    ★2026-09-02(この修正): それまで ``b`` は **完全に死んでいた**(実測:
    ``max|clahe(x,0.5,0.0) - clahe(x,0.5,1.0)| == 0.0`` きっかり)。CLAHE の
    "C" は contrast **limited** の C であり、clip limit こそが AHE と CLAHE を
    分ける当のものなので、**実装は AHE であって CLAHE ではなかった** ——
    名前が嘘をついていた。ここで clip limit を実装して ``b`` に割り当て、
    ``b=1`` が旧実装とビット一致する端になるよう倍率を選んである
    (切り取りが起きない上限 = ビン数 256 倍)。

    Tiles PARTITION the image (linspace boundaries, so the last tile absorbs the
    H % nb / W % nb remainder), each tile's clip-limited CDF is its local tone map,
    and every pixel blends the maps of its (up to) 4 nearest tile centres with
    bilinear weights — the standard CLAHE interpolation (Zuiderveld 1994).

    2026-08-30: 補間を追加(KNOWN_ISSUES #4 — 旧実装はタイルごとに独立に平坦化
    しており、タイル境界に不連続(肉眼で見える格子)が出ていた)。タイル中心の
    近傍領域ではそのタイルの CDF がそのまま支配的なので、旧実装と同じ写像族の
    連続版になっている。
    """
    nb = 2 + int(a * 3)
    H, W = v.shape
    x = np.clip(np.asarray(v, np.float64), 0, 1)
    # clip limit を「その領域の全画素数に対する割合」で持つ。
    #   b=1 -> 256**0 = 1.0 (きっかり) -> climit = n -> どのビンも超えられない = 素の AHE
    #   b=0 -> 256**-1 = 1/256        -> climit = 平均カウント -> 完全平坦 = 強調ゼロ
    # b=1 で climit が n と **厳密に**一致するようこの形で書く(倍率を掛けてから
    # 256 で割ると丸めで n をわずかに下回り、定数タイルで余計な再配分が起きる)。
    clip_frac = 256.0 ** (float(np.clip(b, 0.0, 1.0)) - 1.0)
    ys = np.linspace(0, H, nb + 1).astype(int)
    xs = np.linspace(0, W, nb + 1).astype(int)
    cy = (ys[:-1] + ys[1:]) / 2.0                       # tile centres (pixel coords)
    cx = (xs[:-1] + xs[1:]) / 2.0
    edges = np.linspace(0.0, 1.0, 257)
    mids = (edges[:-1] + edges[1:]) / 2.0

    # Global CDF: the fallback map for degenerate (empty) tiles, which linspace
    # can produce when nb exceeds the image side.
    ghist, _ = np.histogram(x, 256, (0, 1))
    gcdf = _clip_limit_cdf(ghist, clip_frac * float(x.size))

    cdfs = np.empty((nb, nb, 256), np.float64)          # per-tile tone maps at bin mids
    for i in range(nb):
        for j in range(nb):
            blk = x[ys[i]:ys[i + 1], xs[j]:xs[j + 1]]
            if blk.size:
                hist, _ = np.histogram(blk, 256, (0, 1))
                # clip limit はタイルの画素数に対する割合(b=1 で blk.size = 切り取り無効)
                cdfs[i, j] = _clip_limit_cdf(hist, clip_frac * float(blk.size))
            else:
                cdfs[i, j] = gcdf

    def _tent(centers, n):
        """Clamped bilinear (tent) weights, one (n,) vector per tile; sums to 1."""
        pos = np.arange(n, dtype=np.float64)
        ws = []
        for i in range(len(centers)):
            w = np.zeros(n)
            if i > 0:
                gap = max(centers[i] - centers[i - 1], 1e-12)
                m = (pos >= centers[i - 1]) & (pos < centers[i])
                w[m] = (pos[m] - centers[i - 1]) / gap
            if i < len(centers) - 1:
                gap = max(centers[i + 1] - centers[i], 1e-12)
                m = (pos >= centers[i]) & (pos <= centers[i + 1])
                w[m] = np.minimum(1.0, (centers[i + 1] - pos[m]) / gap)
            else:
                w[pos >= centers[i]] = 1.0
            if i == 0:
                w[pos <= centers[0]] = 1.0
            ws.append(w)
        return ws

    wy, wx = _tent(cy, H), _tent(cx, W)
    out = np.zeros_like(x)
    for i in range(nb):
        ri = np.nonzero(wy[i] > 0)[0]
        if ri.size == 0:
            continue
        r0, r1 = int(ri[0]), int(ri[-1]) + 1            # tent support is contiguous
        for j in range(nb):
            ci = np.nonzero(wx[j] > 0)[0]
            if ci.size == 0:
                continue
            c0, c1 = int(ci[0]), int(ci[-1]) + 1
            sub = x[r0:r1, c0:c1]
            mapped = np.interp(sub.ravel(), mids, cdfs[i, j]).reshape(sub.shape)
            out[r0:r1, c0:c1] += (wy[i][r0:r1, None] * wx[j][None, c0:c1]) * mapped
    return np.clip(out, 0.0, 1.0)


def _corner_response(v, a, b):
    """Harris コーナー検出の応答値（コーナーらしさ）を画像として返す。HALCON の ``points_harris``（Detect points of interest using the Harris operator.）に相当。

``a`` が構造テンソルを平滑化するガウシアンの σ を ``0.5〜2.5`` に振る。``b`` は未使用（Harris の経験定数 ``k=0.04`` は固定）。Sobel 勾配 ``Gx, Gy`` から構造テンソル成分 ``Gx², Gy², Gx*Gy`` をガウシアンで平滑化し、``det - k*trace²`` を ``_signed01`` で ``[0,1]`` に写す（0.5 が応答ゼロ、大きいほどコーナーらしく、小さいほどエッジらしい）。座標リストではなく応答マップを返す点が HALCON の ``points_harris``（座標を返す）と異なる——極大点抽出は別途 ``_local_max`` 等と組み合わせる必要がある。"""
    gx = ndimage.sobel(v, 1); gy = ndimage.sobel(v, 0); s = 0.5 + 2.0 * a
    axx = ndimage.gaussian_filter(gx * gx, s); ayy = ndimage.gaussian_filter(gy * gy, s)
    axy = ndimage.gaussian_filter(gx * gy, s)
    return _signed01(axx * ayy - axy * axy - 0.04 * (axx + ayy) ** 2)


def _adaptive_gauss_thresh(v, a, b):
    """ガウシアン平滑化した局所平均を基準にした適応的しきい値処理。HALCON の ``local_threshold``（Segment an image using local thresholding.）に相当。

``a`` が基準を作るガウシアンの σ を ``1.0〜4.0`` に、``b`` がオフセットを ``-0.15〜+0.15``（``(b-0.5)*0.3``）に振る。``v > gaussian_filter(v, σ) + offset`` を満たす画素を前景にする。照明ムラがある画像で大域しきい値（``_threshold``/``_otsu``）より安定する。近い op に ``_dyn_threshold`` があるが、そちらは箱型平均（``uniform_filter``）を基準にし、オフセット幅も異なる（``±0.2``）——同じ「適応的しきい値」でも基準の平滑化方式とパラメータ範囲が違う別実装。"""
    return (v > ndimage.gaussian_filter(v, 1.0 + 3.0 * a) + (b - 0.5) * 0.3).astype(np.float64)


# --- shape-based matching (rotation invariant; image -> match) --------------- #
def _shape_locate(v, a, b):
    """回転を考慮したテンプレートマッチング（shape-based matching）。HALCON の ``find_shape_model``（Find the best matches of a shape model in an image.）に相当。

``a``, ``b`` は未使用——テンプレートは ``_ncc_locate`` と同じく ``set_match_template`` で事前登録する。テンプレートを ``0°〜330°`` まで ``30°`` 刻みで回転させながらそれぞれ ``_ncc_map``（NCC）を計算し、全位置・全角度を通じて最良の相関を ``[相関値, y, x, 角度]`` で返す。角度の刻みが粗い（30°）ぶん、HALCON の ``find_shape_model`` のような連続的な角度精度は出ない——大まかな向き検出用。テンプレート未設定時は ``[0,0,0,0]``。"""
    T = _MATCH_CTX.get("template")
    if T is None or not (isinstance(v, np.ndarray) and v.ndim == 2):
        return np.array([0.0, 0.0, 0.0, 0.0])
    best = [-1e18, 0.0, 0.0, 0.0]
    for ang in range(0, 360, 30):
        corr = _ncc_map(v, ndimage.rotate(T, ang, reshape=False))   # NCC per rotation
        idx = np.unravel_index(int(np.argmax(corr)), corr.shape)
        m = float(corr[idx])
        if m > best[0]:
            best = [m, float(idx[0]), float(idx[1]), float(ang)]
    return np.array(best)


# --- classification (region -> feature; OCR/decision basis) ------------------ #
def _classify_shape(v, a, b):
    """最大の連結領域について円形度（circularity）を計算する形状分類の基礎特徴量。対応する単体の HALCON op は指定されていない。

``a``, ``b`` は未使用。最大面積の連結成分について ``4π×面積 / 周長²`` を計算し、理想円で 1 になるよう ``min(1.0, ...)`` で頭打ちにする（数値誤差で 1 をわずかに超えるのを防ぐ）。周長は領域からその侵食を引いた境界画素数（``_region_boundary`` と同じ考え方）で近似するため、輪郭ベースの周長より粗い。前景が無ければ 0 を返す。コード中のコメントの通り、OCR・良否判定など「形状で分類する」処理の土台として使うことを想定している。"""
    lab, n = ndimage.label(_bin(v))
    if n == 0:
        return np.float64(0.0)
    sizes = ndimage.sum(np.ones_like(lab), lab, index=range(1, n + 1))
    mask = lab == (int(np.argmax(sizes)) + 1)
    area = float(mask.sum())
    per = float((mask.astype(np.float64) - ndimage.binary_erosion(mask).astype(np.float64)).sum())
    return np.float64(min(1.0, 4 * np.pi * area / (per * per)) if per > 0 else 0.0)  # ~1 circle


# --- barcode-lite (image -> feature; count dark bars on the mid scanline) ---- #
def _decode_barcode(v, a, b):
    """中央走査線上の明暗の切り替わり回数を数える簡易バーコード風特徴量。HALCON の ``find_bar_code``（Detect and read bar code symbols in an image.）とは似て非なるもので、シンボル体系の判定やデータのデコードは一切行わない（バー「数」を数えるだけ）。

``a`` が「暗い」とみなすしきい値を ``0.3〜0.7`` に振る。``b`` は未使用。画像中央の行（``v.shape[0]//2``）だけを見て、``v < しきい値`` の画素を 1 とした列に対し、0→1 に立ち上がる回数（暗いバーの本数）を数える。実際のバーコードのデータ（数字・文字列）は得られない。"""
    row = (v[v.shape[0] // 2] < (0.3 + 0.4 * a)).astype(int)
    return np.float64(int((np.diff(np.concatenate([[0], row, [0]])) == 1).sum()))


# --- 3D volume ops (scipy.ndimage is N-D; CT/MRI/depth stacks) --------------- #
def _vol_gaussian(v, a, b):
    """3D ボリュームの等方ガウシアン平滑化。対応する HALCON op は指定されていない。

``a`` が標準偏差 σ を ``0.3〜3.0``（``0.3+2.7a``）に振る。``b`` は未使用。``scipy.ndimage`` は次元非依存（N-D）なので、2-D の ``_gaussian`` と全く同じ式をそのまま 3 軸（CT/MRI/深度スタック等）に適用する。"""
    return ndimage.gaussian_filter(v, sigma=0.3 + 2.7 * a)


def _vol_median(v, a, b):
    """3D ボリュームのメディアンフィルタ。対応する HALCON op は指定されていない。

窓サイズは ``3``（3×3×3）に固定——``a``, ``b`` はどちらも未使用（2-D 版 ``_median`` と異なり ``_k(a)`` を使っていないため、進化パラメータで強さを変えられない）。"""
    return ndimage.median_filter(v, size=3)


def _vol_erode(v, a, b):
    """3D ボリュームのグレースケール侵食。対応する HALCON op は指定されていない。

構造要素の一辺は ``size = 1 + 2*(1 + int(a))``。``a`` は ``[0,1)`` の範囲では ``int(a)`` が常に 0 になるため実質サイズ ``3`` 固定で、``a`` が ``1.0``（``decode`` の ``np.clip`` で上限に張り付いたとき）になったときだけ ``5`` に切り替わる、実質 2 値スイッチにしかなっていない（``_vol_dilate`` も同じ式で同じ性質）。``b`` も未使用。"""
    return ndimage.grey_erosion(v, size=1 + 2 * (1 + int(a)))


def _vol_dilate(v, a, b):
    """3D ボリュームのグレースケール膨張。対応する HALCON op は指定されていない。

``_vol_erode`` と同じ式 ``size = 1 + 2*(1 + int(a))`` を使うため、``a`` はほぼ効かない（``a`` が ``[0,1)`` の間は ``int(a)`` が常に 0 で実質サイズ ``3`` 固定、``a=1.0`` のときだけ ``5``）。``b`` も未使用。半径を連続的に振りたい場合は球形構造要素版（``_vol_dilation_ball`` 等、``int(a*3)`` を使い ``a`` が実際に効く）を使うこと。"""
    return ndimage.grey_dilation(v, size=1 + 2 * (1 + int(a)))


def _vol_threshold(v, a, b):
    """3D ボリュームの大域しきい値処理（2-D の ``_threshold`` の 3D 版）。対応する HALCON op は指定されていない。

``a`` がしきい値そのもの（``0〜1``）で、``v > a`` を満たすボクセルを 1 にする。``b`` は未使用。出力は二値ボリューム（0/1 の float64）。"""
    return (v > a).astype(np.float64)                    # volume -> binary volume


# 3D 二値(領域)モルフォロジ(2026-08-31)。accel_vol に GPU kernel が先に実装
# 済みで core 名が無く bridge から永久に到達不能だった層 — ここが SoT になる。
# cross = 6 近傍(generate_binary_structure(3,1))、ball = x²+y²+z²<=r²
# (skimage.morphology.ball と同式)。境界は scipy 既定 border_value=0(背景)。
def _vol_ball_fp(r):
    if r <= 0:
        return np.ones((1, 1, 1), bool)
    zz, yy, xx = np.mgrid[-r:r + 1, -r:r + 1, -r:r + 1]
    return (xx * xx + yy * yy + zz * zz) <= r * r


def _vol_reg_dilate(v, a, b):
    """3D 二値領域の膨張（region ボリュームの膨張）。対応する HALCON op は指定されていない。

``a`` が反復回数を ``1〜4``（``max(1, 1+int(3a))``）に振る。``b`` は未使用。構造要素は 6 近傍（``generate_binary_structure(3,1)``、十字形）。反復回数を明示的に ``1`` 以上へクランプしているのは、scipy が ``iterations<1`` を「収束するまで反復」と解釈し、``a`` が小さい側で全充填・全消去に発散するのを防ぐため（敵対的レビューで見つかった不具合の修正、D3）。"""
    # iterations は 1 以上へクランプ。scipy は iterations<1 を「収束まで反復」と
    # 解釈するため、a<0 を渡すと全充填/全消去に発散する(敵対レビュー D3)
    st = ndimage.generate_binary_structure(3, 1)
    return ndimage.binary_dilation(_bin(v), st, iterations=max(1, 1 + int(a * 3))).astype(np.float64)


def _vol_reg_erode(v, a, b):
    """3D 二値領域の侵食（region ボリュームの侵食）。対応する HALCON op は指定されていない。

``a`` が反復回数を ``1〜4``（``max(1, 1+int(3a))``）に振る。``b`` は未使用。構造要素は 6 近傍（十字形）。``_vol_reg_dilate`` と同じ理由で反復回数を ``1`` 以上にクランプしている。"""
    st = ndimage.generate_binary_structure(3, 1)
    return ndimage.binary_erosion(_bin(v), st, iterations=max(1, 1 + int(a * 3))).astype(np.float64)


def _vol_dilation_ball(v, a, b):
    """球形構造要素による 3D 二値膨張。対応する HALCON op は指定されていない。

``a`` が球の半径を ``1〜4``（``1+int(3a)``）に振る。``b`` は未使用。球は ``x²+y²+z² <= r²`` で作る（``skimage.morphology.ball`` と同じ定義）。``_vol_reg_dilate``（6近傍固定）より広い近傍を扱え、``a`` で半径そのものを直接変えられる。"""
    return ndimage.binary_dilation(_bin(v), _vol_ball_fp(1 + int(a * 3))).astype(np.float64)


def _vol_erosion_ball(v, a, b):
    """球形構造要素による 3D 二値侵食。対応する HALCON op は指定されていない。

``a`` が球の半径を ``1〜4``（``1+int(3a)``）に振る。``b`` は未使用。球の定義は ``_vol_dilation_ball`` と同じ。"""
    return ndimage.binary_erosion(_bin(v), _vol_ball_fp(1 + int(a * 3))).astype(np.float64)


def _vol_opening_ball(v, a, b):
    """球形構造要素による 3D 二値オープニング（侵食してから同じ球で膨張）。対応する HALCON op は指定されていない。

``a`` が球の半径を ``1〜4``（``1+int(3a)``）に振る。``b`` は未使用。侵食と膨張に同じ半径の球を使うため、球より小さい突起・細い連結だけを選択的に除去する。"""
    fp = _vol_ball_fp(1 + int(a * 3))
    return ndimage.binary_dilation(
        ndimage.binary_erosion(_bin(v), fp), fp).astype(np.float64)


def _vol_mip(v, a, b):
    """最大値投影（Maximum Intensity Projection, MIP）で 3D ボリュームを 2D 画像に潰す。対応する HALCON op は指定されていない。

``a``, ``b`` は未使用。先頭軸（``axis=0``、スライス/深さ方向）に沿った最大値を取り、``_norm`` でそのスライスの最大絶対値を 1 に正規化する。CT/MRI の読影でよく使う投影法。"""
    return _norm(np.max(v, axis=0))                      # volume -> image (max-intensity projection)


def _vol_slice(v, a, b):
    """3D ボリュームから 1 枚の 2D スライスを取り出す。対応する HALCON op は指定されていない。

``a`` が取り出すスライス番号を先頭軸（``axis=0``）に沿って ``0`` から ``shape[0]-1`` まで線形に振る（``int(a * shape[0])`` を範囲内にクランプ）。``b`` は未使用。値は ``[0,1]`` に clip して返す（3D フィルタ後に生じ得るオーバーシュートの後始末）。"""
    return np.clip(v[min(v.shape[0] - 1, int(a * v.shape[0]))], 0, 1)  # volume -> image


def _vol_count(v, a, b):
    """3D ボリューム中の連結成分（ブロブ）の個数を返す特徴量。対応する HALCON op は指定されていない。

``a``, ``b`` は未使用。しきい値は ``0.5`` に固定（``v > 0.5`` で二値化してから ``scipy.ndimage.label``）。連結性は scipy の既定構造要素（面で接する 6 近傍相当）で、稜・頂点だけで接する（26 近傍でしか繋がらない）ボクセルは別ブロブとして数えられる——2-D の ``_blob_count`` が HALCON パリティのため 8 連結を明示指定しているのとは対照的に、こちらは既定のまま連結性を明示していない。"""
    return np.float64(ndimage.label(np.asarray(v) > 0.5)[1])          # volume -> feature (3D blobs)


@dataclass
class Op:
    name: str
    category: str
    halcon: str
    in_sort: str
    out_sort: str
    fn: Callable
    c_stmt: Optional[Callable[[float, float], str]] = None
    #: op の説明。**関数の docstring が第一の置き場**で、これはその代わりが要る
    #: ときの受け皿 —— backend の op 表は lambda で書かれているものが多く、
    #: lambda に docstring は書けない。各 backend が module-level ``DOCS``
    #: (op 名 -> 説明)を出すと、下の登録ループがここへ入れる。
    #: 読む側(``tools/opdocs.py`` / Studio ヘルプ)は ``fn.__doc__ or op.doc``。
    doc: str = ""


def _c(name):
    return {
        "gaussian": lambda a, b: f"gaussian(buf, w, h, {0.3 + 2.7 * a:.6f}f);",
        "mean_box": lambda a, b: f"box(buf, w, h, {_k(a)});",
        "gamma": lambda a, b: f"gamma_op(buf, w, h, {0.5 + 1.5 * a:.6f}f);",
        "invert": lambda a, b: "invert(buf, w, h);",
        "scale_clip": lambda a, b: f"scale_clip(buf, w, h, {0.5 + 1.5 * a:.6f}f, {b - 0.5:.6f}f);",
        "threshold": lambda a, b: f"threshold(buf, w, h, {a:.6f}f);",
        "unsharp": lambda a, b: f"sharpen(buf, w, h, {1.5 * a:.6f}f, {0.5 + 1.5 * b:.6f}f);",
        "sobel_mag": lambda a, b: "sobel_mag(buf, w, h);",
    }.get(name)


_DEFS = [
    ("identity", "misc", "copy_image", ANY, ANY, _identity),
    # image -> image
    ("gaussian", "smoothing", "gauss_filter", IMAGE, IMAGE, _gaussian),
    ("mean_box", "smoothing", "mean_image", IMAGE, IMAGE, _mean_box),
    ("bilateral", "smoothing", "bilateral_filter", IMAGE, IMAGE, _bilateral),
    ("unsharp", "smoothing", "emphasize", IMAGE, IMAGE, _unsharp),
    ("median", "rank", "median_image", IMAGE, IMAGE, _median),
    ("min_filter", "rank", "gray_erosion_rect", IMAGE, IMAGE, _min_filter),
    ("max_filter", "rank", "gray_dilation_rect", IMAGE, IMAGE, _max_filter),
    ("percentile", "rank", "rank_image", IMAGE, IMAGE, _percentile),
    ("gerode", "morphology", "gray_erosion", IMAGE, IMAGE, _erode_g),
    ("gdilate", "morphology", "gray_dilation", IMAGE, IMAGE, _dilate_g),
    ("gopen", "morphology", "gray_opening", IMAGE, IMAGE, _open_g),
    ("gclose", "morphology", "gray_closing", IMAGE, IMAGE, _close_g),
    ("tophat", "morphology", "gray_tophat", IMAGE, IMAGE, _tophat),
    ("bothat", "morphology", "gray_bothat", IMAGE, IMAGE, _bothat),
    ("morph_grad", "morphology", "gray_range_rect", IMAGE, IMAGE, _morph_grad),
    ("sobel_mag", "edges", "sobel_amp", IMAGE, IMAGE, _sobel_mag),
    ("laplace", "edges", "laplace", IMAGE, IMAGE, _laplace),
    ("prewitt_mag", "edges", "prewitt_amp", IMAGE, IMAGE, _prewitt_mag),
    ("roberts_mag", "edges", "roberts", IMAGE, IMAGE, _roberts_mag),
    ("dog", "edges", "diff_of_gauss", IMAGE, IMAGE, _dog),
    ("gamma", "gray", "pow_image", IMAGE, IMAGE, _gamma),
    ("invert", "gray", "invert_image", IMAGE, IMAGE, _invert),
    ("scale_clip", "gray", "scale_image", IMAGE, IMAGE, _scale_clip),
    ("equalize", "gray", "equ_histo_image", IMAGE, IMAGE, _equalize),
    ("sigmoid", "gray", "scale_image_max", IMAGE, IMAGE, _sigmoid),
    ("lowpass", "frequency", "", IMAGE, IMAGE, _lowpass),
    ("highpass", "frequency", "highpass_image", IMAGE, IMAGE, _highpass),
    ("std_filter", "texture", "deviation_image", IMAGE, IMAGE, _std_filter),
    # image -> region (segmentation)
    ("threshold", "segmentation", "threshold", IMAGE, REGION, _threshold),
    ("otsu", "segmentation", "binary_threshold", IMAGE, REGION, _otsu),
    ("dyn_threshold", "segmentation", "dyn_threshold", IMAGE, REGION, _dyn_threshold),
    # region -> region
    ("reg_erode", "region", "erosion_circle", REGION, REGION, _reg_erode),
    ("reg_dilate", "region", "dilation_circle", REGION, REGION, _reg_dilate),
    ("reg_open", "region", "opening_circle", REGION, REGION, _reg_open),
    ("reg_close", "region", "closing_circle", REGION, REGION, _reg_close),
    ("fill_holes", "region", "fill_up", REGION, REGION, _fill_holes),
    ("select_largest", "region", "select_shape_std", REGION, REGION, _select_largest),
    ("remove_small", "region", "select_shape", REGION, REGION, _remove_small),
    ("invert_region", "region", "complement", REGION, REGION, _invert_region),
    # region -> feature (measurement)
    ("blob_count", "features", "count_obj", REGION, FEATURE, _blob_count),
    ("area_frac", "features", "area_center", REGION, FEATURE, _area_frac),
    # extra image ops
    ("grad_dir", "edges", "", IMAGE, IMAGE, _grad_dir),
    ("log", "edges", "laplace_of_gauss", IMAGE, IMAGE, _log),
    # extra segmentation (image -> region)
    ("canny", "segmentation", "edges_image", IMAGE, REGION, _canny),
    ("local_max", "segmentation", "local_max_sub_pix", IMAGE, REGION, _local_max),
    # extra region ops
    ("dist_transform", "region", "distance_transform", REGION, IMAGE, _dist_transform),
    ("region_boundary", "region", "boundary", REGION, REGION, _region_boundary),
    ("convex_fill", "region", "shape_trans", REGION, REGION, _convex_fill),
    # image -> contour (XLD)
    ("edges_sub_pix", "contour", "edges_sub_pix", IMAGE, CONTOUR, _edges_sub_pix),
    # contour -> contour
    ("select_contours", "contour", "select_contours_xld", CONTOUR, CONTOUR, _select_contours),
    ("smooth_contours", "contour", "smooth_contours_xld", CONTOUR, CONTOUR, _smooth_contours),
    ("fit_line_contours", "contour", "fit_line_contour_xld", CONTOUR, CONTOUR, _fit_line_contours),
    # contour -> region / feature
    ("contours_to_region", "contour", "gen_region_contour_xld", CONTOUR, REGION, _contours_to_region),
    ("count_contours", "features", "count_obj", CONTOUR, FEATURE, _count_contours),
    ("total_length", "features", "length_xld", CONTOUR, FEATURE, _total_length),
    # image -> match (template matching)
    ("ncc_locate", "matching", "find_ncc_model", IMAGE, MATCH, _ncc_locate),
    # geometry (calibration/rectification basis)
    ("rotate_img", "geometry", "rotate_image", IMAGE, IMAGE, _rotate_img),
    # halcon 名は zoom_image_size → zoom_image_factor へ訂正(2026-09-02): この op は
    # 目標サイズではなく **倍率** で駆動する。目標サイズ版は backends_auto の
    # `zoom_image_size` が本当に実装している。
    ("rescale_img", "geometry", "zoom_image_factor", IMAGE, IMAGE, _rescale_img),
    ("affine_warp", "geometry", "affine_trans_image", IMAGE, IMAGE, _affine_warp),
    # extra filters
    ("gabor", "texture", "gen_gabor", IMAGE, IMAGE, _gabor),
    ("clahe", "gray", "", IMAGE, IMAGE, _clahe),
    ("corner_response", "edges", "points_harris", IMAGE, IMAGE, _corner_response),
    ("adaptive_gauss_thresh", "segmentation", "local_threshold", IMAGE, REGION, _adaptive_gauss_thresh),
    # shape-based matching (rotation invariant)
    ("shape_locate", "matching", "find_shape_model", IMAGE, MATCH, _shape_locate),
    # classification (OCR/decision basis)
    ("classify_shape", "classification", "", REGION, FEATURE, _classify_shape),
    # barcode
    ("decode_barcode", "barcode", "find_bar_code", IMAGE, FEATURE, _decode_barcode),
    # 3D volume (CT/MRI/depth stacks)
    ("vol_gaussian", "3d", "", VOLUME, VOLUME, _vol_gaussian),
    ("vol_median", "3d", "", VOLUME, VOLUME, _vol_median),
    ("vol_erode", "3d", "", VOLUME, VOLUME, _vol_erode),
    ("vol_dilate", "3d", "", VOLUME, VOLUME, _vol_dilate),
    ("vol_threshold", "3d", "", VOLUME, VOLUME, _vol_threshold),
    ("vol_reg_dilate", "3d", "", VOLUME, VOLUME, _vol_reg_dilate),
    ("vol_reg_erode", "3d", "", VOLUME, VOLUME, _vol_reg_erode),
    ("vol_dilation_ball", "3d", "", VOLUME, VOLUME, _vol_dilation_ball),
    ("vol_erosion_ball", "3d", "", VOLUME, VOLUME, _vol_erosion_ball),
    ("vol_opening_ball", "3d", "", VOLUME, VOLUME, _vol_opening_ball),
    ("vol_mip", "3d", "", VOLUME, IMAGE, _vol_mip),
    ("vol_slice", "3d", "", VOLUME, IMAGE, _vol_slice),
    ("vol_count", "features", "", VOLUME, FEATURE, _vol_count),
]

REGISTRY: list[Op] = [Op(n, c, h, i, o, f, _c(n)) for (n, c, h, i, o, f) in _DEFS]
RT: dict[str, Callable] = {op.name: op.fn for op in REGISTRY}
_BY_NAME: dict[str, Op] = {op.name: op for op in REGISTRY}
OPS = tuple((op.name, op.fn) for op in REGISTRY)  # back-compat
N_OPS = len(REGISTRY)
N_SLOTS = 6
GENOME_LEN = N_SLOTS * 3

# Optional library backends (scikit-image / OpenCV): wrap the ecosystem so op count
# scales without reimplementing. Disable with IMGEVOLVE_NO_BACKENDS=1 for the pure,
# always-deterministic numpy/scipy core. Adding backends only widens per-sort
# candidate sets — GENOME_LEN is unchanged.
import os as _os  # noqa: E402

if _os.environ.get("IMGEVOLVE_NO_BACKENDS", "") != "1":
    _extra = []
    FAILED_BACKENDS: list = []   # (module, error) for backends whose build() raised

    for _mod in ("backends", "backends_dl", "backends_auto", "backends_color",
                 "backends_extra", "backends_pil", "backends_scipy",
                 "backends_ski2", "backends_cv2b", "backends_r3", "backends_kornia",
                 "backends_filters2", "backends_regions2", "backends_subpix", "backends_xldgeom",
                 "backends_regions3", "backends_imgtools", "backends_measure1d",
                 "backends_physics", "backends_decomp",
                 "backends_inverse", "backends_transform2", "backends_segment2", "backends_tomo",
                 # Physical-AI / evolution op wave (all halcon="", new capabilities):
                 # sim2real sensor corruption (aug_), artificial-life / cellular automata
                 # (alife_), and tactile / contact-from-shading (tac_).
                 "backends_aug", "backends_alife", "backends_tactile",
                 # more cellular-automata / artificial-life (Langton / Wolfram-1D /
                 # Lenia / Abelian sandpile) and control-point deformable warps
                 # (thin-plate spline / B-spline FFD / moving least squares). All
                 # halcon="" new capabilities; numpy/scipy-native, deterministic.
                 "backends_alife2", "backends_deform",
                 # HALCON coverage 拡充: 未カバーの実 operator を genuine numpy 実装
                 # (gen_circle/ellipse/rectangle2/checker/grid, convol_gabor,
                 #  fit_surface_first/second_order, cooc_feature_image, full_domain)。
                 "backends_halcon_ext",
                 # self-expanding registry: macro ("DNA") ops condensed from evolved
                 # champions (backends_macro.py). LAST, so it can reference any backend
                 # op and minimally perturbs existing registration indices.
                 "backends_macro",
                 # typed bridge: the ops3d / ops1d / opsmath / opsoptics catalogs
                 # exposed to evolution. AFTER macro so every existing SLOTS index
                 # (macro ops included) is preserved. Registers only NEW in_sorts by
                 # default, which is what keeps decode byte-identical — see
                 # backends_typed's docstring and docs/WAVE0_STABLE_SLOTS.md.
                 "backends_typed"):
        try:
            _b = __import__(_mod)
            _new = _b.build(Op, IMAGE, REGION, FEATURE, CONTOUR, _norm, _bin)
            # backend が module-level DOCS を出していれば、docstring を持てない
            # op(= lambda で書かれた表の行)の説明をここで積む。docstring が
            # あるものは触らない —— 実装のそばに書いてある方が正しい。
            _docs = getattr(_b, "DOCS", None) or {}
            for _op in _new:
                if not _op.doc and not (getattr(_op.fn, "__doc__", None) or "").strip():
                    _op.doc = (_docs.get(_op.name) or "").strip()
            _extra += _new
        except Exception as _e:  # noqa: BLE001 - optional backend; recorded, never silent
            # A backend that fails to import used to VANISH: every op it defines
            # silently missing from the registry, evolution / coverage none the
            # wiser. Keep the registry importable, but leave a trace.
            FAILED_BACKENDS.append((_mod, "%s: %s" % (type(_e).__name__, _e)))
            try:
                import backend_safe as _bs
                _bs.record(_mod, _e, None, source="import")
            except Exception:  # pragma: no cover - the ledger itself must never break import
                pass
    # 名前の衝突を弾く。**op 名は addressing の鍵**で、``RT`` / ``_BY_NAME`` /
    # ``SLOTS`` はどれも後勝ちの dict なので、同名を 2 つ登録すると先に入った方が
    # 名前では二度と引けなくなる(``decode_by_names`` が再現できない)。一方
    # ``_candidates`` はリストを走査するので**両方が抽選に入り、その op だけ
    # 当たる確率が 2 倍**になる。
    #
    # 2026-09-02 実測: laplace / dyn_threshold / local_max / edges_sub_pix の 4 件が
    # ``ops.py`` のコア定義(index 17/31/45/49)と ``backends_auto`` の再定義
    # (210/236/244/276)で衝突していた。9 通りの入力で両者の出力は完全一致
    # (= 純粋な重複)。``backends_auto.build`` は自分の spec 内だけ HALCON 名で
    # de-dup しており、コアが既に登録した名前を知らない。
    #
    # 残すのは**最後に登録された方**。``RT`` / ``_BY_NAME`` は元々「後勝ち」の
    # dict なので、こうすると**名前で引ける実装は 1 ビットも変わらない** ――
    # 4 件はいずれも「コアの fallback + backends_auto の fail-closed ``_safe``
    # ラッパが勝つ」という意図的な上書きで(tests/test_opdocs.py に pin されて
    # いた)、勝者を入れ替えてはいけない。消えるのは抽選の二重取りだけ。
    # backend が不在の環境ではコア定義しか登録されないので、fallback も保たれる。
    #
    # 捨てた分は ``DROPPED_DUPLICATES`` に残す —— 黙って消すと「登録したのに
    # 使えない」になるので、テストが「ちょうどこの集合だけ」を検査できるようにする。
    DROPPED_DUPLICATES = []
    if _extra:
        _all = REGISTRY + _extra
        _last = {}
        for _i, _op in enumerate(_all):
            _last[_op.name] = _i
        REGISTRY = [_op for _i, _op in enumerate(_all) if _last[_op.name] == _i]
        DROPPED_DUPLICATES = [_op.name for _i, _op in enumerate(_all)
                              if _last[_op.name] != _i]
        RT = {op.name: op.fn for op in REGISTRY}
        _BY_NAME = {op.name: op for op in REGISTRY}
        OPS = tuple((op.name, op.fn) for op in REGISTRY)
        N_OPS = len(REGISTRY)


def categories() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for op in REGISTRY:
        out.setdefault(op.category, []).append(op.name)
    return out


def _candidates(sort: str) -> list[Op]:
    return [op for op in REGISTRY if op.in_sort == sort or op.in_sort == ANY]


@dataclass
class Stage:
    op: str
    a: float
    b: float
    sort: str  # the sort this stage operates on (for readability/codegen)


def decode(genome, start: str = IMAGE) -> list[Stage]:
    """Type-aware decode: each slot picks a sort-compatible op; sort threads through."""
    g = np.clip(np.asarray(genome, np.float64), 0.0, 1.0)
    sort = start
    out: list[Stage] = []
    for i in range(N_SLOTS):
        t, a, b = g[3 * i], g[3 * i + 1], g[3 * i + 2]
        cands = _candidates(sort)
        op = cands[min(len(cands) - 1, int(t * len(cands)))]
        out.append(Stage(op.name, float(a), float(b), sort))
        if op.name != "identity":
            sort = op.out_sort
    return out


#: 値域が [0,1] と決まっている sort。``_apply`` の段間クリップはこの規約のもの。
#: 座標や振幅を運ぶ新 sort(points/signal/matrix/cimage)に同じクリップを掛けると
#: **データを破壊する** — 実測 2026-09-01: 点群 (N,3) は 2-D ndarray なので
#: クリップ対象になり、[0,10] の座標が [0,1] に潰れて hand baseline が trivial を
#: 下回った(0.194 vs 0.684)。既存 sort の挙動は 1 ビットも変えないため、
#: 「新 sort だけを除外する」形で書く(既存 champion のスコアは不変)。
_UNCLIPPED_SORTS = frozenset({POINTS, SIGNAL, MATRIX, CIMAGE,
                              LIGHTFIELD, COUNTS, HISTCUBE, KEYPOINTS})


def _effective_out_sort(st):
    """その stage を出た値の sort。

    ``identity`` のように ``out_sort == ANY`` の op は「入ってきた sort を保つ」
    という意味なので、宣言をそのまま読むと sort を見失う。実測 2026-09-01:
    ANY を素直に読んだせいで、**何もしない 6 段が点群を [0,1] にクリップして
    いた** — 同じ「何もしないパイプライン」がゲノム経路 0.2016 / 名前経路
    0.6616 と食い違い、進化が trivial baseline に到達できない真因だった。
    """
    op = _BY_NAME.get(st.op)
    if op is None:
        return None
    return st.sort if op.out_sort == ANY else op.out_sort


def _apply(stages, img):
    v = np.asarray(img, np.float64)
    for st in stages:
        v = RT[st.op](v, st.a, st.b)
        if isinstance(v, np.ndarray) and v.ndim in (2, 3):
            if _effective_out_sort(st) not in _UNCLIPPED_SORTS:
                v = np.clip(v, 0.0, 1.0)
    return v


def run_genome(genome, img, start: str = IMAGE):
    """Run the decoded pipeline; returns an image/region (2-D), volume (3-D), or feature."""
    return _apply(decode(genome, start), img)


def run_stages(stages: list, img):
    return _apply(stages, img)


def apply_genome(genome, img):
    """Back-compat: coerce the final value to a 2-D array (feature -> constant image)."""
    v = run_genome(genome, img)
    if isinstance(v, np.ndarray) and v.ndim == 2:
        return v
    if isinstance(v, dict):                       # contour -> use the contour count
        v = float(len(v.get("cs", [])))
    try:
        m = float(np.clip(np.mean(np.asarray(v, np.float64)), 0, 1))
    except Exception:
        m = 0.0
    return np.full(img.shape, m, np.float64)


def stage(op: str, a: float, b: float) -> Stage:
    """Build one typed stage (for hand-written baseline pipelines)."""
    return Stage(op, a, b, _BY_NAME[op].in_sort)


def pipeline_str(genome, start: str = IMAGE) -> str:
    parts = [f"{s.op}(a={s.a:.2f},b={s.b:.2f})" for s in decode(genome, start) if s.op != "identity"]
    return " -> ".join(parts) if parts else "identity"


# --------------------------------------------------------------------------- #
# Wave-0: stable op slots + name-pinned (cross-install) champion records.       #
# --------------------------------------------------------------------------- #
# SLOTS freezes each op's registration-order index the moment REGISTRY is fully
# built (core _DEFS first, then any optional backends in import order). decode()
# indexes _candidates(sort) in exactly this order, so within a given install the
# genome->op mapping is deterministic and documented by SLOTS.
#
# CROSS-INSTALL CAVEAT (honest): the index a genome resolves to depends on how
# many candidates a sort has, which grows with the optional backends present in
# THIS install. Re-sorting _candidates to a globally stable order WOULD change
# that mapping and therefore change every existing champion — so decode() is
# deliberately left byte-identical (proven in tests/test_wave0.py). Reproducing a
# champion across installs is done by op NAME instead of index: pipeline_stages()
# records the champion as (name, a, b) and decode_by_names() rebuilds the exact
# pipeline from those names, independent of the index layout. See docs/WAVE0_STABLE_SLOTS.md.
#
# A few names occur twice (a backend overrides a core op, e.g. "laplace"). Like RT
# and _BY_NAME, SLOTS resolves a name to its LAST (canonical) occurrence — the op
# that actually executes (decode() stores a name; _apply runs RT[name]). Name-pinned
# reload is therefore consistent with execution on both sides.
SLOTS: dict[str, int] = {op.name: i for i, op in enumerate(REGISTRY)}


def op_slot(name: str) -> int:
    """Stable registration-order slot of an op (frozen when REGISTRY was built)."""
    return SLOTS[name]


def stages_str(stages) -> str:
    """Render a decoded pipeline (list[Stage]) to the same string form as
    pipeline_str, but from stages rather than a genome (drops identity)."""
    parts = [f"{s.op}(a={s.a:.2f},b={s.b:.2f})" for s in stages if s.op != "identity"]
    return " -> ".join(parts) if parts else "identity"


def pipeline_stages(genome, start: str = IMAGE) -> list[dict]:
    """Name-pinned champion record: the decoded pipeline as a list of
    ``{"op", "a", "b", "sort"}`` dicts (identity dropped). Index-independent, so
    it reloads to the SAME pipeline on any install that has the named ops, via
    :func:`decode_by_names`. This is the cross-install-reproducible counterpart
    to the index-based :func:`decode`."""
    return [{"op": s.op, "a": float(s.a), "b": float(s.b), "sort": s.sort}
            for s in decode(genome, start) if s.op != "identity"]


def genome_for_names(stage_specs, start: str = IMAGE):
    """名前で書いたパイプライン → それを decode するゲノム(不可能なら ``None``)。

    :func:`decode` の逆写像。``decode`` は各スロットで
    ``cands[int(t*len(cands))]`` を引くので、目的の op が候補リストの何番目かが
    分かれば ``t`` を作れる(区間の中央を取る)。埋まらないスロットは
    ``identity`` で詰める。

    **何のためか**: 進化を **既知の baseline から始められる**ようにするため。
    候補が狭い sort では、ランダム初期化で「何もしない」パイプラインに当たる
    確率が ``(1/候補数)**スロット数`` になり事実上ゼロで、進化が trivial にすら
    到達できない(実測 2026-09-01: 点群 25 候補 × 6 スロットで 4e-9。3200 評価の
    探索でも locked 0.436 と、何もしない 0.675 を下回った)。そのままでは
    「進化は baseline を超えたか」の比較が空虚になる。

    ``None`` を返すのは、その op がそのスロットの sort の候補に居ないとき
    (= そのパイプラインはこの encoding では表現できない)。**近い op で
    代用しない** — 別物を種にしたら実験の意味が変わる。
    """
    slots = list(stage_specs)
    if len(slots) > N_SLOTS:
        return None
    g = np.zeros(GENOME_LEN, np.float64)
    sort = start
    for i in range(N_SLOTS):
        if i < len(slots):
            spec = slots[i]
            name = spec[0] if isinstance(spec, tuple) else spec["op"]
            a = float(spec[1] if isinstance(spec, tuple) else spec.get("a", 0.5))
            b = float(spec[2] if isinstance(spec, tuple) else spec.get("b", 0.5))
        else:
            name, a, b = "identity", 0.5, 0.5
        cands = _candidates(sort)
        idx = next((j for j, o in enumerate(cands) if o.name == name), None)
        if idx is None:
            return None                       # この encoding では表現できない
        g[3 * i] = (idx + 0.5) / len(cands)   # その区間の中央 = 端の丸めに強い
        g[3 * i + 1], g[3 * i + 2] = a, b
        if name != "identity":
            sort = _BY_NAME[name].out_sort
    return g


def decode_by_names(stage_specs) -> list[Stage]:
    """Reconstruct a pipeline from op NAMES (independent of registry index order).

    ``stage_specs`` is an iterable of either ``(name, a, b)`` tuples or dicts with
    keys ``op``/``a``/``b``. Each op's ``in_sort`` is resolved from ``_BY_NAME``,
    so a champion saved by name (see :func:`pipeline_stages`) rebuilds to the same
    pipeline regardless of which optional backends shifted the index layout. Raises
    ``KeyError`` (fail-closed) if a named op is absent in this install."""
    out: list[Stage] = []
    for spec in stage_specs:
        if isinstance(spec, dict):
            name = spec["op"]
            a = float(spec.get("a", 0.0))
            b = float(spec.get("b", 0.0))
        else:
            name, a, b = spec[0], float(spec[1]), float(spec[2])
        out.append(Stage(name, a, b, _BY_NAME[name].in_sort))
    return out


def psnr(a, b) -> float:
    mse = float(np.mean((np.asarray(a, np.float64) - np.asarray(b, np.float64)) ** 2))
    return 99.0 if mse <= 1e-12 else float(10.0 * np.log10(1.0 / mse))
