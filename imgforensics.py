# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""imgforensics — 画像フォレンジック(image forensics)の **証拠量** を出す op 族。

この族が答えるのは「この画像は加工されているか」ではない。**それには答えない。**
返すのは「どんな証拠が、どれだけの量あるか」と「その証拠が **何を意味しないか**」で、
判定は人間が下す。理由は 2 つある。

1. フォレンジックの各手法は **前提が崩れると黙って数字を出す**。ELA は「元が
   JPEG である」、PRNU は「同一センサ・同一解像度・強い再圧縮なし」、コピー&ムーブは
   「平坦でない領域」を前提にする。前提が崩れたときに例外を出す手法は 1 つも無く、
   代わりに **もっともらしい有限値**が出る。だから「しきい値を超えたので改竄」と
   書ける op を用意すること自体が、この repo が潰そうとしている失敗そのものになる。
2. どの量も **単調ではない**。PCE 40 は「同じセンサ」を意味しないし、PCE 5 は
   「違うセンサ」を意味しない(枚数・解像度・圧縮率に依存する)。だから
   :func:`fingerprint_correlate` は ``"tampered": True`` を返さず、``pce`` と
   ``caveats`` を返す。

## この族が fullseye にある理由 —— **正解が手元にある**

改竄側を作る手段が既にこの repo にある(:mod:`defectgen` の欠陥合成、
``backends_aug`` の JPEG ブロック/固定パターンノイズ/動きぼけ、:mod:`imagemorph`
の warp)。つまり **「どこを、どうコピーしたか」を知っている状態で検出器を測れる**。
``tests/test_imgforensics.py`` はその形で書いてあり、「例外が出ない」ではなく
**既知の座標を当てられるか / 当てられない条件はどれか**を数で固定している。

## 既存資産との棲み分け(**再実装せず import して合成**)

  * **キーポイント検出と記述**は :func:`features.harris_corners` /
    :func:`features.describe_patches`。:func:`copy_move_regions` は 1 度も
    コーナー検出を書いていない。
  * **RANSAC** は :func:`mosaic.proj_match_points_ransac`(射影変換、(row, col) 規約)。
    コピー&ムーブの幾何整合はこれに委ねる。
  * **相似変換の当てはめ**は :func:`fit_transform.vector_to_similarity`(Umeyama)。
  * **JPEG 標準輝度量子化表**は ``backends_aug._JPEG_LUMA_Q`` を **参照**する
    (複製しない)。2 つの表が別々に育つと、:func:`jpeg_quality_estimate` が
    ``aug_jpeg_blocks`` の作った画像の品質を外す —— 同じ repo の中で
    **答え合わせに使う表が食い違う**という最悪の形になる。
    ``tests/test_imgforensics.py::test_luma_table_is_the_shared_one`` が同一性を固定。
  * **記述子マッチ** :func:`features.match_descriptors` は **使えない**。実測:
    同じ記述子集合を 2 引数に渡すと 100% 自分自身との対応(``[[i, i]]``)を返し、
    Lowe の比率検定は自分自身を最近傍として通す。コピー&ムーブは
    **自己マッチから自己を除いた最近傍**が要るので、そこだけは新しく書いた
    (:func:`_self_match`)。除外の距離条件が本質で、それは 2 集合マッチには無い。

## 依存(すべて optional、不在なら **その op だけ**が明示的な例外)

  * **numpy + scipy のみ**で動く: :func:`perceptual_hash` :func:`hash_distance`
    :func:`sensor_fingerprint` :func:`fingerprint_correlate`
    :func:`fingerprint_strength_map` :func:`copy_move_regions`
    :func:`jpeg_quality_estimate` :func:`noise_inconsistency_map`
    :func:`jpeg_ghost_quality`
  * **Pillow 必須**: :func:`error_level_map` :func:`jpeg_ghost_map`
    (本物の JPEG 符号化器が要る。無い環境で「DCT 量子化で近似」に黙って落ちると、
    **符号化器の丸め・色空間変換・チャネル間引きが消えた別物**を ELA と名乗ることに
    なる。よって :class:`ImportError` を送出する。)
  * **PyWavelets 必須**: :func:`watermark_embed` :func:`watermark_extract`
    :func:`watermark_capacity` :func:`sensor_fingerprint` の ``denoiser="wavelet"``
  import 自体は上記が 1 つも無くても通る(遅延 import)。

## 来歴(公開文献・公開実装のみ。製品名は名前にも動機にも使わない)

  * 知覚ハッシュ(平均・DCT・差分)= C. Zauner, *Implementation and Benchmarking of
    Perceptual Image Hash Functions*, MSc thesis, Upper Austria Univ. of Applied
    Sciences, 2010。DCT 版の原型は J. Fridrich & M. Goljan, *Robust Hash Functions
    for Digital Watermarking*, ITCC 2000。
  * PRNU センサ指紋 = J. Lukáš, J. Fridrich, M. Goljan, *Digital Camera
    Identification from Sensor Pattern Noise*, IEEE TIFS 1(2), 2006。
    最尤推定 K = Σ W_i I_i / Σ I_i² と ZM 前処理 = M. Chen, J. Fridrich,
    M. Goljan, J. Lukáš, *Determining Image Origin and Integrity Using Sensor
    Noise*, IEEE TIFS 3(1), 2008。
  * PCE(peak-to-correlation energy)= M. Goljan, J. Fridrich, T. Filler,
    *Large Scale Test of Sensor Fingerprint Camera Identification*,
    SPIE Media Forensics and Security, 2009。
  * 局所 Wiener によるノイズ抽出 = M. K. Mihcak, I. Kozintsev, K. Ramchandran,
    *Spatially Adaptive Statistical Modeling of Wavelet Image Coefficients*,
    ICASSP 1999。
  * ELA(誤差レベル解析)= N. Krawetz, *A Picture's Worth: Digital Image Analysis
    and Forensics*, Black Hat Briefings 2007。
  * コピー&ムーブ(ブロック法)= J. Fridrich, D. Soukal, J. Lukáš, *Detection of
    Copy-Move Forgery in Digital Images*, DFRWS 2003。
  * 量子化表のブラインド推定 = Z. Fan & R. L. de Queiroz, *Identification of
    Bitmap Compression History: JPEG Detection and Quantizer Estimation*,
    IEEE TIP 12(2), 2003。品質係数 ↔ 表の換算は Independent JPEG Group の
    公開スケーリング規則(``S = 5000/Q`` (Q<50) / ``S = 200-2Q``)。
  * JPEG ゴースト = H. Farid, *Exposing Digital Forgeries from JPEG Ghosts*,
    IEEE TIFS 4(1), 2009。
  * 高速ノイズ分散推定 = J. Immerkær, *Fast Noise Variance Estimation*,
    CVIU 64(2), 1996(3x3 ラプラシアン風マスク、係数 √(π/2)/(6(W-2)(H-2)))。
  * DWT-DCT 電子透かし(係数対の大小関係で 1 ビット)= C.-T. Hsu & J.-L. Wu,
    *Hidden Digital Watermarks in Images*, IEEE TIP 8(1), 1999 の中帯域係数対法を
    DWT の LL 副帯域に適用したもの。ブラインド抽出(原画像不要)。

## fail-closed

2-D でない / 非有限 / 空 / 画素数上限超 / 範囲外の ``quality`` ``strength``
``hash_size`` ``block`` / dtype 違いのハッシュ / 長さの違うハッシュ ——
すべて文書化された :class:`ValueError` を送出する。黙って clip も wrap もしない。
"""
from __future__ import annotations

import numpy as np
from scipy import fft as sfft
from scipy import ndimage

import backends_aug
import features
import fit_transform
import mosaic

__all__ = [
    "perceptual_hash", "hash_distance",
    "sensor_fingerprint", "fingerprint_correlate", "fingerprint_strength_map",
    "error_level_map", "jpeg_quality_estimate", "jpeg_ghost_map",
    "jpeg_ghost_quality", "noise_inconsistency_map", "copy_move_regions",
    "watermark_embed", "watermark_extract", "watermark_capacity",
    "IMGFORENSICS", "MAX_PIXELS", "MAX_HASH_SIZE", "JPEG_LUMA_Q",
]

#: 公開 op(introspection / facade 配線用)。順序はカテゴリ順。
IMGFORENSICS = [
    "perceptual_hash", "hash_distance",
    "sensor_fingerprint", "fingerprint_correlate", "fingerprint_strength_map",
    "error_level_map", "jpeg_quality_estimate", "jpeg_ghost_map",
    "jpeg_ghost_quality", "noise_inconsistency_map", "copy_move_regions",
    "watermark_embed", "watermark_extract", "watermark_capacity",
]

#: 画素数の上限。PRNU は画像 1 枚あたり float64 の一時配列を 5〜6 本作り、
#: :func:`jpeg_ghost_map` は品質の数だけ (H, W) を保持する。``2**24`` (16.8 Mpx)
#: で float64 1 本が 134 MB。これを超えるものは ROI へ切ってから渡す。
MAX_PIXELS = 1 << 24

#: :func:`perceptual_hash` の 1 辺の上限。``hash_size**2`` ビットを返すので
#: 64 で 4096 ビット。これ以上は「ハッシュ」ではなく縮小画像そのものである。
MAX_HASH_SIZE = 64

#: JPEG Annex-K 標準輝度量子化表(品質 50)。**複製ではなく参照**である ——
#: ``backends_aug`` の ``aug_jpeg_blocks`` が作った劣化画像の品質を
#: :func:`jpeg_quality_estimate` が推定するので、2 つの表が食い違うと
#: 「同じ repo の中で答え合わせが狂う」。
JPEG_LUMA_Q = backends_aug._JPEG_LUMA_Q

#: Immerkær (1996) の 3x3 マスク。係数の二乗和は 36 なので、|畳み込み| の平均に
#: ``sqrt(pi/2) / 6`` を掛けるとガウス雑音の σ の不偏推定になる。
_IMMERKAER = np.array([[1.0, -2.0, 1.0],
                       [-2.0, 4.0, -2.0],
                       [1.0, -2.0, 1.0]], np.float64)

#: :func:`perceptual_hash` の DCT 版で使う低周波の切り出し倍率(Zauner 2010 と同じ 4)。
_DCT_HIGHFREQ_FACTOR = 4

#: 透かしを入れる 8x8 DCT の中帯域係数の対((row, col))。低すぎると目に見え、
#: 高すぎると JPEG の量子化で最初に消える。Hsu & Wu 1999 の中帯域の考え方どおり
#: ジグザグ順でほぼ同順位(どちらも 5 番目相当)の 2 つを選んでいるので、
#: **交換しても画質への影響がほぼ等しい** = 埋め込みの偏りが出ない。
_WM_COEFF_A = (3, 1)
_WM_COEFF_B = (1, 3)


# --------------------------------------------------------------------------- #
# fail-closed 入力ヘルパ                                                        #
# --------------------------------------------------------------------------- #
def _require(module: str, op: str):
    """optional 依存を遅延 import。不在なら **何が要るかを言う** ImportError。"""
    try:
        return __import__(module)
    except ImportError as exc:                          # pragma: no cover - 環境依存
        raise ImportError(
            f"{op} は {module} を必要とする(近似には落ちない)。"
            f"`py -3.11 -m pip install {module}` で入れること。元の例外: {exc}"
        ) from exc


def _as_image(image, name: str = "image", *, allow_color: bool = True) -> np.ndarray:
    """(H, W) の有限 float64 へ。カラー (H, W, 3|4) は ITU-R BT.601 の輝度へ落とす。

    **輝度へ落とすことは情報の破棄**である。PRNU はチャネルごとに指紋が違う
    (CFA 補間で緑の画素密度が倍)ので、本気の識別ではチャネルを分けて呼ぶこと。
    ここで落とすのは「1 枚のグレー地図を返す」という族の約束を守るためで、
    黙ってやらないよう docstring に書いてある。
    """
    a = np.asarray(image)
    if a.dtype == object:
        raise ValueError(f"{name}: object dtype は受け取らない")
    a = a.astype(np.float64, copy=False)
    if a.ndim == 3:
        if not allow_color:
            raise ValueError(f"{name}: 2-D のみ。カラー (H, W, C) は受け取らない")
        if a.shape[2] not in (3, 4):
            raise ValueError(f"{name}: 3-D の最終軸は 3 か 4 のみ、{a.shape[2]} が来た")
        a = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    if a.ndim != 2:
        raise ValueError(f"{name}: (H, W) か (H, W, 3|4) が要る、shape={np.shape(image)}")
    if a.size == 0:
        raise ValueError(f"{name}: 空の配列")
    if a.size > MAX_PIXELS:
        raise ValueError(f"{name}: 画素数 {a.size} が上限 {MAX_PIXELS} を超える。"
                         "ROI に切ってから渡すこと")
    if not np.all(np.isfinite(a)):
        raise ValueError(f"{name}: 非有限(NaN / Inf)を含む。上流が壊れている印なので"
                         "黙って 0 で埋めない")
    return a


def _as_images(images, name: str = "images", *, min_n: int = 1) -> list:
    """同じ shape の 2-D 画像の列へ。shape が揃わなければ fail-closed。"""
    if isinstance(images, np.ndarray) and images.ndim == 3 and images.shape[2] not in (3, 4):
        seq = [images[i] for i in range(images.shape[0])]      # (N, H, W) スタック
    elif isinstance(images, np.ndarray) and images.ndim == 3:
        raise ValueError(
            f"{name}: (N, H, W) のスタックのつもりでも最終軸が 3 か 4 だと "
            "カラー 1 枚と区別できない。list か tuple で渡すこと")
    elif isinstance(images, (list, tuple)):
        seq = list(images)
    else:
        raise ValueError(f"{name}: list / tuple / (N, H, W) の ndarray が要る")
    if len(seq) < min_n:
        raise ValueError(f"{name}: 少なくとも {min_n} 枚が要る、{len(seq)} 枚が来た")
    out = [_as_image(x, f"{name}[{i}]") for i, x in enumerate(seq)]
    shp = out[0].shape
    for i, x in enumerate(out):
        if x.shape != shp:
            raise ValueError(f"{name}[{i}]: shape {x.shape} が {name}[0] の {shp} と違う。"
                             "PRNU は画素の位置がそのまま指紋なので、"
                             "リサイズして揃えると指紋そのものが壊れる")
    return out


def _as_hash(h, name: str = "hash") -> np.ndarray:
    """bool の 1-D ビット列へ。**float を黙って 0/1 に丸めない**。"""
    a = np.asarray(h)
    if a.ndim != 1:
        raise ValueError(f"{name}: 1-D のビット列が要る、ndim={a.ndim}")
    if a.size == 0:
        raise ValueError(f"{name}: 空")
    if a.dtype != np.bool_:
        raise ValueError(
            f"{name}: dtype は bool でなければならない、{a.dtype} が来た。"
            "float の 1-D は `signal` / `descriptor` 語彙の値であって"
            "ハッシュではない —— != で数えれば有限の距離が出てしまうので"
            "ここで止める(silently-plausible を作らない)")
    return a


def _pos_int(v, name, lo=1, hi=None):
    if isinstance(v, bool) or not isinstance(v, (int, np.integer)):
        raise ValueError(f"{name}: 整数が要る、{v!r} が来た")
    v = int(v)
    if v < lo or (hi is not None and v > hi):
        raise ValueError(f"{name}: {lo}..{hi if hi is not None else '∞'} の範囲外: {v}")
    return v


def _unit_float(v, name, lo=0.0, hi=1.0, *, inclusive_lo=True):
    if isinstance(v, bool) or not isinstance(v, (int, float, np.floating, np.integer)):
        raise ValueError(f"{name}: 実数が要る、{v!r} が来た")
    v = float(v)
    if not np.isfinite(v):
        raise ValueError(f"{name}: 非有限")
    if (v < lo if inclusive_lo else v <= lo) or v > hi:
        raise ValueError(f"{name}: {lo}..{hi} の範囲外: {v}")
    return v


def _to_uint8(x) -> np.ndarray:
    """[0, 1] を想定した float を 8 bit へ。**範囲外は例外**(clip で隠さない)。"""
    a = np.asarray(x, np.float64)
    lo, hi = float(a.min()), float(a.max())
    if lo < -1e-9 or hi > 1.0 + 1e-9:
        raise ValueError(
            f"画素値が [0, 1] の外(min={lo:.4g}, max={hi:.4g})。JPEG 符号化は"
            "8 bit 前提なので、どう正規化するかを呼び出し側が決めること —— "
            "ここで勝手に clip すると飽和した画素が『元から白飛び』に見える")
    return np.round(np.clip(a, 0.0, 1.0) * 255.0).astype(np.uint8)


# --------------------------------------------------------------------------- #
# 面積平均リサンプル(知覚ハッシュの土台)                                        #
# --------------------------------------------------------------------------- #
def _area_resize_axis(a: np.ndarray, m: int, axis: int) -> np.ndarray:
    """1 軸だけ **面積平均**で ``m`` 標本へ。累積和の線形補間で厳密に出す。"""
    a = np.moveaxis(a, axis, -1)
    n = a.shape[-1]
    if n == m:
        return np.moveaxis(a, -1, axis)
    c = np.concatenate([np.zeros(a.shape[:-1] + (1,), np.float64),
                        np.cumsum(a, axis=-1)], axis=-1)
    edges = np.linspace(0.0, float(n), m + 1)
    lo = np.clip(np.floor(edges).astype(int), 0, n)
    hi = np.clip(lo + 1, 0, n)
    frac = edges - lo
    ce = c[..., lo] * (1.0 - frac) + c[..., hi] * frac
    seg = np.diff(ce, axis=-1) / np.diff(edges)
    return np.moveaxis(seg, -1, axis)


def _area_resize(img: np.ndarray, out_shape) -> np.ndarray:
    """(H, W) を面積平均で ``out_shape`` へ。

    最近傍や単純な間引きでリサイズすると **縮小時に高周波が折り返して**、
    元は同じ画像なのにハッシュが変わる。面積平均は箱フィルタ + 標本化と等価で、
    「同じ画像をリサイズしても距離が小さい」というハッシュの前提を守る側にある。
    """
    a = _area_resize_axis(np.asarray(img, np.float64), int(out_shape[0]), 0)
    return _area_resize_axis(a, int(out_shape[1]), 1)


# =========================================================================== #
# (1) 知覚ハッシュ                                                             #
# =========================================================================== #
def perceptual_hash(image, mode: str = "dct", hash_size: int = 8) -> np.ndarray:
    """知覚ハッシュ(perceptual hash)。**bool の 1-D ビット列**を返す。

    ``mode``:

    ``"dct"``   縮小 ``(hash_size * 4)`` 角 → 2-D DCT-II(直交)→ 左上
                ``hash_size x hash_size`` を取り、**DC を除いた中央値**と比較。
                Zauner 2010 の pHash と同じ手順。長さ ``hash_size**2`` ビット。
    ``"average"`` 縮小 ``hash_size`` 角 → 平均と比較(aHash)。同じ長さ。
    ``"difference"`` 縮小 ``(hash_size, hash_size + 1)`` → **横に隣り合う画素の
                大小**を比較(dHash)。同じ長さで、平均輝度の変化に強い。

    **この op が言えないこと**(``tests/test_imgforensics.py`` が数で固定):

    * 距離が小さい = 同じ画像、ではない。8x8 の粗い縮小に落としているので、
      **細部の改竄は距離 0 のまま通る**。実測:512x512 の画像に 24x24 の
      コピー&ムーブを入れても dct/average/difference の距離は 0 / 0 / 0。
    * 距離が大きい = 別画像、でもない。**左右反転で 32 / 30 / 32 ビット**、
      **90 度回転で 34 / 26 / 32 ビット**(ランダムな 2 枚の期待値 32 と同程度)。
      幾何変換に対する不変性は一切無い。
    * 返り値は **``phash`` 語彙**であって ``signal`` ではない。bool の 1-D は
      既存の ``signal`` / ``indices`` / ``descriptor`` の述語をすべて満たすので、
      取り違えると ``signal1d.lowpass`` などが **有限でもっともらしい値**を返す
      (実測 5 op)。だから :func:`hash_distance` は dtype を検査する。
    """
    x = _as_image(image)
    n = _pos_int(hash_size, "hash_size", 2, MAX_HASH_SIZE)
    if mode == "average":
        small = _area_resize(x, (n, n))
        return (small > small.mean()).ravel()
    if mode == "difference":
        small = _area_resize(x, (n, n + 1))
        return (small[:, 1:] > small[:, :-1]).ravel()
    if mode == "dct":
        big = _DCT_HIGHFREQ_FACTOR * n
        small = _area_resize(x, (big, big))
        d = sfft.dctn(small, norm="ortho")[:n, :n]
        flat = d.ravel()
        # DC(平均輝度)は画像の内容ではなく露出なので、比較の基準からも外す。
        med = float(np.median(flat[1:]))
        bits = flat > med
        bits[0] = flat[0] > med          # DC ビット自体は残す(長さを n**2 に保つ)
        return bits
    raise ValueError(f"mode は 'dct' / 'average' / 'difference' のいずれか、{mode!r} が来た")


def hash_distance(hash1, hash2) -> int:
    """2 つの知覚ハッシュのハミング距離(異なるビット数)。

    **dtype と長さを検査して fail-closed** する。float の 1-D を受け取って
    ``!=`` で数えると、ほぼ確実に「全ビット違う」= 最大距離という
    *もっともらしい* 値が出る —— それは型の取り違えであって画像の違いではない。

    返りは Python の ``int``(``measurement`` 語彙)。ビット長で割った
    正規化距離が欲しければ ``hash_distance(a, b) / a.size``。
    """
    a = _as_hash(hash1, "hash1")
    b = _as_hash(hash2, "hash2")
    if a.size != b.size:
        raise ValueError(f"ハッシュ長が違う: {a.size} vs {b.size}。"
                         "hash_size か mode が食い違っている(距離は定義できない)")
    return int(np.count_nonzero(a != b))


# =========================================================================== #
# (2) PRNU センサ指紋                                                          #
# =========================================================================== #
def _wiener_denoise(x: np.ndarray, sigma: float, windows=(3, 5, 7, 9)) -> np.ndarray:
    """局所適応 Wiener(Mihcak et al. 1999)。複数窓の局所分散の **最小**を使う。

    最小を取るのが要点で、これは「一番平坦に見える見方を採用する」= 信号分散を
    小さめに見積もる = **雑音を残しすぎない**側に倒す選択である。エッジの上では
    どの窓でも分散が大きいので、エッジの信号はきちんと残る。
    """
    s2 = float(sigma) ** 2
    est = None
    for w in windows:
        mu = ndimage.uniform_filter(x, w, mode="reflect")
        m2 = ndimage.uniform_filter(x * x, w, mode="reflect")
        v = np.maximum(m2 - mu * mu - s2, 0.0)
        est = v if est is None else np.minimum(est, v)
    return x * (est / (est + s2))


def _wavelet_denoise(x: np.ndarray, sigma: float, wavelet: str = "db4",
                     level: int = 4) -> np.ndarray:
    """波数域の局所 Wiener(PRNU の古典的な取り出し方)。PyWavelets 必須。"""
    pywt = _require("pywt", "sensor_fingerprint(denoiser='wavelet')")
    lv = min(int(level), int(pywt.dwtn_max_level(x.shape, wavelet)))
    if lv < 1:
        return _wiener_denoise(x, sigma)
    coeffs = pywt.wavedec2(x, wavelet, level=lv, mode="symmetric")
    out = [coeffs[0]]
    for det in coeffs[1:]:
        out.append(tuple(_wiener_denoise(np.asarray(c, np.float64), sigma) for c in det))
    rec = pywt.waverec2(out, wavelet, mode="symmetric")
    return np.asarray(rec, np.float64)[:x.shape[0], :x.shape[1]]


def _noise_residual(x: np.ndarray, sigma: float, denoiser: str) -> np.ndarray:
    """雑音残差 W = I - denoise(I)。"""
    if denoiser == "wiener":
        return x - _wiener_denoise(x, sigma)
    if denoiser == "wavelet":
        return x - _wavelet_denoise(x, sigma)
    raise ValueError(f"denoiser は 'wiener' / 'wavelet'、{denoiser!r} が来た")


def _zero_mean(k: np.ndarray) -> np.ndarray:
    """ZM 前処理(Chen et al. 2008):行平均と列平均を抜く。

    JPEG のブロック格子・CFA 補間・行/列アンプの固定パターンは行方向・列方向に
    **共通**の成分として乗るので、これを抜かないと *別のカメラ同士でも* 相関が出る。
    抜かずに測った偽陽性は :func:`fingerprint_correlate` の docstring に実測値がある。
    """
    k = k - k.mean(axis=0, keepdims=True)
    return k - k.mean(axis=1, keepdims=True)


def sensor_fingerprint(images, denoiser: str = "wiener", sigma: float = 0.02,
                       zero_mean: bool = True) -> np.ndarray:
    """複数枚から **PRNU センサ指紋** K を最尤推定する(Chen et al. 2008)。

    ``K = Σ_i W_i I_i / Σ_i I_i²``(``W_i = I_i - denoise(I_i)``)。撮像モデル
    ``I = I⁰ + I⁰·K + Θ`` の下で、これが K の最尤推定量になる —— 明るい画素ほど
    PRNU が強く出る(乗法的な欠陥だから)ので、**明るさで重み付けした平均**である。

    返りは ``(H, W)`` の float64 で、``zero_mean=True``(既定)なら行・列平均を
    抜いたうえで **標準偏差 1 に正規化**してある。正規化は :func:`fingerprint_correlate`
    の PCE をスケール不変にするためで、指紋の絶対的な強さは
    :func:`fingerprint_strength_map` が別に返す。

    ``images`` は同じ shape の 2 枚以上。**リサイズして揃えてはいけない** ——
    PRNU は画素の物理位置そのものなので、内挿した瞬間に指紋は消える(shape 不一致は
    :class:`ValueError`)。

    枚数と分離度の実測(``tests/test_imgforensics.py::test_prnu_separates_two_sensors``、
    128x128・PRNU 強度 3%・読み出し雑音 σ=0.01):

    ========= ================= =================
    枚数      同一センサの PCE  別センサの PCE
    ========= ================= =================
    2         1.09e+03          1.03e-01
    4         2.44e+03          8.11e-02
    8         4.79e+03          2.79e-01
    16        8.19e+03          1.72e-01
    ========= ================= =================

    **これは合成雑音での上限**であり、実カメラでは 4 桁小さい値が普通である
    (被写体の内容が残差に漏れるため)。この表は「実装が正しく動いている」ことの
    固定であって、実運用のしきい値ではない。
    """
    imgs = _as_images(images, "images", min_n=2)
    sig = _unit_float(sigma, "sigma", 1e-6, 1.0, inclusive_lo=False)
    num = np.zeros_like(imgs[0])
    den = np.zeros_like(imgs[0])
    for im in imgs:
        w = _noise_residual(im, sig, denoiser)
        num += w * im
        den += im * im
    k = num / np.maximum(den, 1e-12)
    if zero_mean:
        k = _zero_mean(k)
    sd = float(k.std())
    if sd < 1e-15:
        raise ValueError("推定された指紋が定数(標準偏差 ~0)。入力が同一画像の"
                         "複製か、雑音がまったく無い合成画像である可能性が高い")
    return k / sd


def _pce(corr: np.ndarray, exclude: int = 11) -> tuple:
    """相関面 → (PCE, ピーク位置, ピーク値)。Goljan et al. 2009。

    PCE = sign(peak)·peak² / (ピーク近傍 ``exclude`` 角を除いた相関面の二乗平均)。
    「相関の最大値」ではなく「**まわりに比べてどれだけ尖っているか**」を測るので、
    画像全体が似ている(=相関面全体が持ち上がる)場合に騙されにくい。
    """
    idx = int(np.argmax(np.abs(corr)))
    py, px = np.unravel_index(idx, corr.shape)
    peak = float(corr[py, px])
    h = max(1, int(exclude) // 2)
    mask = np.ones(corr.shape, bool)
    ys = (np.arange(py - h, py + h + 1)) % corr.shape[0]
    xs = (np.arange(px - h, px + h + 1)) % corr.shape[1]
    mask[np.ix_(ys, xs)] = False
    energy = float(np.mean(corr[mask] ** 2)) if mask.any() else 0.0
    if energy <= 0.0:
        raise ValueError("相関面のピーク近傍を除いたエネルギーが 0。"
                         "画像が定数か、指紋が画像そのものである(自己相関)")
    return (np.sign(peak) * peak * peak / energy, (int(py), int(px)), peak)


def fingerprint_correlate(image, fingerprint, denoiser: str = "wiener",
                          sigma: float = 0.02, exclude: int = 11) -> dict:
    """1 枚の画像を指紋に照合する。**判定は返さない** —— 証拠量と注意書きを返す。

    残差 ``W = I - denoise(I)`` と参照信号 ``I·K`` の巡回相互相関を FFT で取り、
    正規化相互相関のピークと **PCE**(peak-to-correlation energy)を返す。

    返り(``table`` 語彙の dict):

    ``pce``          PCE。**しきい値は同梱しない**(下の caveats 参照)
    ``ncc_peak``     正規化相互相関のピーク値([-1, 1])
    ``peak_shift``   ピークの位置 ``(dy, dx)``。**(0, 0) でなければ位置がずれている**
                     = 切り出し / 手ぶれ補正 / リサイズを疑う手がかり
    ``n_pixels``     使った画素数
    ``caveats``      この数値が言えないことの列(文字列)

    ``peak_shift`` を返すのは重要で、``(0, 0)`` 以外のピークは「同じセンサだが
    切り出されている」か「**たまたまの相関**」のどちらかである。どちらかは
    この op には決められない。

    **黙って間違う経路(実測)**: ``fingerprint`` に指紋ではなく普通の画像を渡すと、
    shape は合っているので例外は出ず、PCE も有限値が返る。指紋は ``(H, W)`` の
    float64 なので既存の ``image2d`` 述語を完全に満たし、**実行時には区別できない**。
    そこで入口で「ゼロ平均でない / 標準偏差に比べて平均が大きい」ものを
    :class:`ValueError` で弾く(``|mean| > 0.05 * std``)。実測では
    :func:`sensor_fingerprint` の返りの ``|mean|/std`` は 1e-17 桁、
    自然画像は 0.4〜6 桁で、**暗い画像(平均 0.02)でも 0.36** と分離する
    (``tests/test_imgforensics.py::test_fingerprint_gate_rejects_plain_images``)。
    それでも完全ではないので、``image2d`` に相乗りさせず語彙を分ける判断は
    ``opsimgforensics`` の docstring に書いてある。
    """
    x = _as_image(image)
    k = _as_image(fingerprint, "fingerprint")
    if k.shape != x.shape:
        raise ValueError(f"fingerprint の shape {k.shape} が image の {x.shape} と違う。"
                         "PRNU は画素位置そのものなので、リサイズでは合わせられない")
    ksd = float(k.std())
    if ksd < 1e-15:
        raise ValueError("fingerprint が定数(標準偏差 ~0)")
    if abs(float(k.mean())) > 0.05 * ksd:
        raise ValueError(
            f"fingerprint がゼロ平均でない(|mean|/std = {abs(k.mean()) / ksd:.3g} > 0.05)。"
            "sensor_fingerprint の返りは行・列平均を抜いてあるのでこの比は 1e-15 桁になる。"
            "普通の画像を指紋として渡していないか確認すること —— "
            "shape は合ってしまうので、これを通すと有限でもっともらしい PCE が出る")
    sig = _unit_float(sigma, "sigma", 1e-6, 1.0, inclusive_lo=False)
    w = _noise_residual(x, sig, denoiser)
    ref = x * k
    w = w - w.mean()
    ref = ref - ref.mean()
    nw, nr = float(np.linalg.norm(w)), float(np.linalg.norm(ref))
    if nw < 1e-12 or nr < 1e-12:
        raise ValueError("残差または参照信号のノルムが 0(定数画像)")
    corr = np.real(sfft.ifft2(sfft.fft2(w) * np.conj(sfft.fft2(ref)))) / (nw * nr)
    pce, shift, peak = _pce(corr, exclude)
    dy = shift[0] if shift[0] <= x.shape[0] // 2 else shift[0] - x.shape[0]
    dx = shift[1] if shift[1] <= x.shape[1] // 2 else shift[1] - x.shape[1]
    return {
        "pce": float(pce),
        "ncc_peak": float(peak),
        "peak_shift": (int(dy), int(dx)),
        "n_pixels": int(x.size),
        "denoiser": denoiser,
        "caveats": [
            "PCE にしきい値は同梱しない。分離点は枚数・解像度・圧縮率・被写体で動く",
            "peak_shift != (0, 0) は『切り出し』か『偶然の相関』のどちらか。区別はできない",
            "強い再圧縮は PRNU を消す。低 PCE は『別のカメラ』ではなく『情報が残っていない』かもしれない",
            "リサイズされた画像は原理的に照合できない(画素位置が指紋そのもの)",
            "カラー画像は輝度に落としてある。チャネルごとの指紋の違いは見ていない",
        ],
    }


def fingerprint_strength_map(fingerprint, block: int = 16) -> np.ndarray:
    """指紋の **ブロックごとの実効強度**(標準偏差)を並べた地図。``image2d``。

    PRNU は飽和した画素と真っ暗な画素では出ない(乗法的な欠陥なので信号が要る)。
    この地図は「**指紋がどこで何も言えないか**」を見るためのもので、値が低い領域の
    照合結果は弱い。``block`` 角の非重複ブロックごとの標準偏差を、元の ``(H, W)`` へ
    ブロック定数で戻して返す(端は端のブロックの値で埋める)。

    これは ``fingerprint`` 語彙の **出口** でもある(袋小路を作らないため)。
    """
    k = _as_image(fingerprint, "fingerprint")
    b = _pos_int(block, "block", 2, max(2, min(k.shape)))
    H, W = k.shape
    nh, nw = max(1, H // b), max(1, W // b)
    crop = k[:nh * b, :nw * b].reshape(nh, b, nw, b)
    sd = crop.std(axis=(1, 3))
    out = np.repeat(np.repeat(sd, b, axis=0), b, axis=1)
    full = np.empty((H, W), np.float64)
    full[:out.shape[0], :out.shape[1]] = out
    if out.shape[0] < H:
        full[out.shape[0]:, :out.shape[1]] = out[-1:, :]
    if out.shape[1] < W:
        full[:, out.shape[1]:] = full[:, out.shape[1] - 1:out.shape[1]]
    return full


# =========================================================================== #
# (3) JPEG 系(ELA / 品質推定 / ゴースト)                                       #
# =========================================================================== #
def _jpeg_roundtrip(u8: np.ndarray, quality: int) -> np.ndarray:
    """Pillow で **本物の JPEG** を通して戻す。近似には落ちない。"""
    import io

    _require("PIL", "JPEG 再圧縮")
    from PIL import Image

    buf = io.BytesIO()
    Image.fromarray(u8, mode="L").save(buf, format="JPEG", quality=int(quality),
                                       subsampling=0, optimize=False)
    buf.seek(0)
    return np.asarray(Image.open(buf).convert("L"), np.float64)


def error_level_map(image, quality: int = 90, normalize: bool = True) -> np.ndarray:
    """ELA(誤差レベル解析)。指定品質で **再圧縮した差分**の地図を返す。``image2d``。

    Krawetz 2007。JPEG は 8x8 ブロックごとに量子化するので、**一度圧縮された領域**は
    同じ品質で再圧縮しても誤差が小さく、**後から貼られた / 描かれた領域**は誤差が
    大きく残る、という考え方に基づく。

    ``normalize=True``(既定)なら最大値で割って [0, 1] にする(見るため)。
    ``False`` なら 8 bit 階調そのままの絶対誤差(数えるため)。

    **Pillow が無ければ :class:`ImportError`。近似には落ちない。** DCT の量子化だけを
    numpy で真似ると、符号化器の丸め・色空間変換・チャネル間引きが消えた *別物* に
    なる。それを ELA と名乗ると、この族が潰そうとしている「もっともらしく間違う」を
    自分でやることになる。

    **この地図が言えないこと**(``tests/test_imgforensics.py`` が数で固定):

    * **無圧縮 PNG(一度も JPEG を通っていない画像)では何も言えない**。そのとき
      ELA が明るくなるのは「改竄された場所」ではなく **単に高周波が多い場所**で、
      実測で ELA と Sobel 勾配強度の相関は **0.744**(合成テクスチャ画像)。
      貼り付けた領域とそれ以外で ELA の平均を比べても分離しない(実測 1.03 倍)。
    * 一度 JPEG を通した画像に貼り付けた場合は分離する(同じ実測で **4.28 倍**)。
      つまり **ELA が意味を持つのは「元が JPEG」のときだけ**である。
    * 平坦な領域は圧縮しても誤差が出ないので、**改竄されていても暗いまま**になる。
    """
    _require("PIL", "error_level_map")
    x = _as_image(image)
    q = _pos_int(quality, "quality", 1, 100)
    u8 = _to_uint8(x)
    rec = _jpeg_roundtrip(u8, q)
    diff = np.abs(u8.astype(np.float64) - rec)
    if not normalize:
        return diff
    m = float(diff.max())
    return diff / m if m > 0 else diff


def _zigzag_order(n: int = 8) -> np.ndarray:
    """n x n のジグザグ走査順(index の 1-D 配列)。"""
    idx = [(i, j) for i in range(n) for j in range(n)]
    idx.sort(key=lambda p: (p[0] + p[1], p[1] if (p[0] + p[1]) % 2 == 0 else -p[1]))
    return np.array([i * n + j for i, j in idx], int)


def _blocks_dct(x: np.ndarray, block: int = 8, offset=(0, 0)) -> np.ndarray:
    """(H, W) [0,1] → 8x8 ブロック DCT-II(直交、0..255 スケール)。(nb, b, b)。"""
    oy, ox = int(offset[0]) % block, int(offset[1]) % block
    a = x[oy:, ox:]
    nh, nw = a.shape[0] // block, a.shape[1] // block
    if nh < 1 or nw < 1:
        raise ValueError(f"画像が {block}x{block} ブロックより小さい: shape={x.shape}")
    a = a[:nh * block, :nw * block] * 255.0
    blk = a.reshape(nh, block, nw, block).transpose(0, 2, 1, 3).reshape(-1, block, block)
    return sfft.dctn(blk, axes=(1, 2), norm="ortho")


def _estimate_step(vals: np.ndarray, max_step: int = 64, *,
                   min_levels: int = 5, min_n: int = 32, min_r: float = 0.5) -> float:
    """1 つの DCT 係数の列 → 量子化ステップの推定(Fan & de Queiroz 2003)。

    量子化された係数は ``q`` の倍数に集まる(櫛状)。候補 ``q`` ごとに円周統計の
    合成長 ``r(q) = |mean(exp(2πi·v/q))|`` を測る(ヒストグラムの箱の切り方に
    依存しない集中度)。

    **どの ``q`` を選ぶかが要点**で、ここは実測で 2 度直した箇所である。

    * 真のステップ ``q*`` では ``v/q*`` が整数になるので ``r ≈ 1``。
    * ``q*`` の **約数** でも ``v/q`` は整数なので ``r ≈ 1``(``2q*`` のような倍数では
      半整数になり ``r ≈ 0``)。よって条件を満たす ``q`` の中で **最大**を採る。
    * **失敗 1**: ``q`` が係数の値域より大きいと全部が 1 周期の一部に収まるので
      ``r ≈ 1`` が無条件に立つ。最初の実装はこれを踏み、**無圧縮 PNG に
      「品質 17」を返していた**(実測)。
    * **失敗 2**: 高周波係数は大半が 0 に量子化され、復号後は **0 のまわりの
      小さな塊**として戻ってくる。この塊は候補 ``q`` が何であれ位相 0 に集まるので、
      値域で切っても大きい ``q`` が勝ち続け、低品質側で推定が上振れした
      (実測: 真 Q=50 に対し推定 Q=74)。

    両方を潰す条件が、候補ごとに **``|v| >= q`` の係数だけを使う**(0 の塊を外す)+
    **丸めた水準が ``min_levels`` 段以上**(1 周期に収まる域を外す)+ 標本 ``min_n``
    以上、である。どれも満たさなければ「櫛が無い」= 量子化されていないとして
    ``0.0`` を返す(「品質 100」とは答えない —— 無圧縮とほぼ無劣化を同じ答えに
    しないため)。
    """
    v = np.asarray(vals, np.float64)
    for q in range(int(max_step), 0, -1):
        w = v[np.abs(v) >= q]
        if w.size < min_n:
            continue
        if np.unique(np.round(w / q)).size < min_levels:
            continue
        if float(np.abs(np.mean(np.exp(2j * np.pi * w / q)))) > min_r:
            return float(q)
    return 0.0


def _ijg_table(quality: int) -> np.ndarray:
    """IJG の公開スケーリング規則で品質 → 輝度量子化表。"""
    q = int(np.clip(quality, 1, 100))
    s = 5000.0 / q if q < 50 else 200.0 - 2.0 * q
    t = np.floor((JPEG_LUMA_Q * s + 50.0) / 100.0)
    return np.clip(t, 1, 255)


def jpeg_quality_estimate(image, max_step: int = 64, n_coeff: int = 21) -> dict:
    """デコード済み画像から **量子化表と JPEG 品質をブラインド推定**する。``table``。

    ファイルの DQT を読むのではなく、**画素だけ**から推定する(そこが要点で、
    PNG に保存し直された / 貼り付けられた画像でも「元は JPEG 品質 N だった」が
    見える)。8x8 ブロック DCT を取り、係数ごとに櫛の間隔を推定して
    (Fan & de Queiroz 2003)、IJG の公開スケーリング規則で作った標準表の族から
    最も合う品質を選ぶ。

    返り(dict):

    ``jpeg_compressed`` 櫛が立った係数が ``n_coeff`` 個中いくつあったかで判断した
                        bool。**「JPEG である」証明ではない**(下記 caveats)
    ``quality``         推定品質 1..100(櫛が無ければ ``None``)
    ``table``           推定した ``(8, 8)`` の量子化ステップ(0 = 推定できず)
    ``n_quantized``     櫛が立った係数の数 / ``n_coeff``
    ``fit_error``       選ばれた品質の標準表との平均絶対差
    ``caveats``         この数値が言えないこと

    実測(``tests/test_imgforensics.py::test_jpeg_quality_estimate_recovers_quality``、
    256x256 の合成テクスチャを Pillow で符号化 → 復号して推定):

    ======= ========= ============
    真の Q  推定 Q    fit_error
    ======= ========= ============
    95      95        0.000
    90      90        0.000
    80      80        0.000
    70      70        0.000
    60      60        0.000
    50      50        0.000
    ======= ========= ============

    そして **無圧縮 PNG では ``jpeg_compressed=False`` / ``quality=None``**
    (同テストで固定)。ここで黙って「品質 100」と答えないことが肝で、
    そうすると「無圧縮」と「ほぼ無劣化の JPEG」が同じ答えになる。
    """
    x = _as_image(image)
    n = _pos_int(n_coeff, "n_coeff", 2, 64)
    ms = _pos_int(max_step, "max_step", 2, 255)
    d = _blocks_dct(x)
    zz = _zigzag_order(8)
    flat = d.reshape(d.shape[0], 64)
    table = np.zeros(64, np.float64)
    hits = 0
    for k in zz[1:n]:                     # DC は露出で動くので使わない
        q = _estimate_step(flat[:, k], ms)
        table[k] = q
        if q > 0:
            hits += 1
    table = table.reshape(8, 8)
    quantized = hits >= max(3, (n - 1) // 3)
    quality, fit = None, float("nan")
    if quantized:
        mask = table > 0
        best = None
        for cand in range(1, 101):
            ref = _ijg_table(cand)
            err = float(np.mean(np.abs(ref[mask] - table[mask])))
            if best is None or err < best[1]:
                best = (cand, err)
        quality, fit = int(best[0]), float(best[1])
    return {
        "jpeg_compressed": bool(quantized),
        "quality": quality,
        "table": table,
        "n_quantized": int(hits),
        "n_tested": int(n - 1),
        "fit_error": fit,
        "caveats": [
            "櫛が無い = 無圧縮とは限らない。品質 100 に近い JPEG は櫛がほぼ立たない",
            "櫛がある = JPEG とも限らない。ブロック状の量子化を伴う処理はどれも櫛を立てる",
            "8x8 の格子が (0,0) からずれている(切り出し)と推定は崩れる",
            "推定表は IJG 標準表の族に当てはめたもの。独自表の符号化器には合わない",
            "二重圧縮では最後の圧縮の品質しか見えない",
        ],
    }


def jpeg_ghost_map(image, qualities=None, block: int = 16) -> list:
    """JPEG ゴースト(Farid 2009)。品質を掃引した **再圧縮残差の地図の列**。``images``。

    ある領域が品質 ``q0`` で一度圧縮されていると、``q = q0`` で再圧縮したときに
    その領域の差分が **谷** になる。画像全体が同じ ``q0`` なら谷は全面に出るが、
    別の品質で圧縮された部分が貼られていると、**その領域だけ別の ``q`` で谷になる**。

    返りは ``len(qualities)`` 本の ``(H, W)`` 地図(``block`` 角の箱平均で平滑化した
    二乗差)。谷の位置を画素ごとに読むのは :func:`jpeg_ghost_quality`。

    **Pillow 必須**(:class:`ImportError`)。理由は :func:`error_level_map` と同じ。

    実測(``tests/test_imgforensics.py::test_jpeg_ghost_finds_the_pasted_quality``、
    品質 92 の背景に品質 60 で圧縮した 64x64 を貼った 192x192):
    貼った領域の谷は **品質 60**、背景の谷は **品質 92**(掃引 40..95 step 5)。
    """
    _require("PIL", "jpeg_ghost_map")
    x = _as_image(image)
    b = _pos_int(block, "block", 1, max(1, min(x.shape)))
    qs = list(range(40, 100, 5)) if qualities is None else [int(q) for q in qualities]
    if not qs:
        raise ValueError("qualities が空")
    for q in qs:
        _pos_int(q, "qualities の要素", 1, 100)
    u8 = _to_uint8(x).astype(np.float64)
    out = []
    for q in qs:
        rec = _jpeg_roundtrip(_to_uint8(x), q)
        d = (u8 - rec) ** 2
        out.append(ndimage.uniform_filter(d, b, mode="reflect"))
    return out


def jpeg_ghost_quality(ghosts, qualities=None) -> np.ndarray:
    """ゴースト地図の列 → 画素ごとに **残差が最小になる品質** の地図。``image2d``。

    ``qualities`` を省くと :func:`jpeg_ghost_map` の既定(40..95 step 5)を仮定する
    —— **枚数が合わなければ :class:`ValueError`**(添字と品質がずれた地図を返さない)。

    返りは品質そのものを画素値に持つ ``(H, W)`` なので、値域は [0, 1] ではない。
    表示するときは正規化すること(この op は数値を返すのであって絵を返さない)。
    """
    if not isinstance(ghosts, (list, tuple)) or len(ghosts) < 2:
        raise ValueError("ghosts は 2 本以上の (H, W) 地図の list/tuple")
    maps = [_as_image(g, f"ghosts[{i}]", allow_color=False) for i, g in enumerate(ghosts)]
    shp = maps[0].shape
    for i, m in enumerate(maps):
        if m.shape != shp:
            raise ValueError(f"ghosts[{i}] の shape {m.shape} が ghosts[0] の {shp} と違う")
    qs = list(range(40, 100, 5)) if qualities is None else [float(q) for q in qualities]
    if len(qs) != len(maps):
        raise ValueError(f"qualities の数 {len(qs)} が ghosts の数 {len(maps)} と違う。"
                         "省略時の既定は 40..95 step 5 の 12 本")
    stack = np.stack(maps, 0)
    return np.asarray(qs, np.float64)[np.argmin(stack, axis=0)]


# =========================================================================== #
# (4) ノイズ整合性                                                             #
# =========================================================================== #
def noise_inconsistency_map(image, block: int = 16) -> np.ndarray:
    """ブロックごとの **雑音標準偏差** を並べた地図。``image2d``。

    Immerkær 1996 の 3x3 マスクで高周波成分を取り、``block`` 角の非重複ブロックごとに
    ``sigma = sqrt(pi/2) / 6 * mean(|conv|)`` を出してブロック定数で戻す。
    貼り付けた領域が別の露出・別の圧縮率・別のカメラから来ていれば、この値が
    まわりと **段差**になる。

    **この地図が言えないこと**(``tests/test_imgforensics.py`` が数で固定):

    * **テクスチャは雑音として数えられる**。Immerkær のマスクはラプラシアン風なので、
      細かい模様の領域は σ が高く出る。実測:雑音を一切足していない合成画像で、
      チェッカー領域の推定 σ は平坦領域の **17.9 倍**。段差があっても「改竄」では
      なく「模様」かもしれない。
    * 逆に **平滑化された改竄は σ が下がる**ので見えるが、平坦な背景に平坦な物を
      貼った場合は差が出ない。
    * JPEG は雑音をブロックごとに削るので、圧縮済みの画像では ``block`` を 8 の倍数に
      しないとブロック格子と干渉して縞が出る(既定 16 は 8 の倍数)。
    """
    x = _as_image(image)
    b = _pos_int(block, "block", 3, max(3, min(x.shape)))
    conv = ndimage.convolve(x * 255.0, _IMMERKAER, mode="reflect")
    H, W = x.shape
    nh, nw = max(1, H // b), max(1, W // b)
    crop = np.abs(conv[:nh * b, :nw * b]).reshape(nh, b, nw, b)
    sigma = np.sqrt(np.pi / 2.0) / 6.0 * crop.mean(axis=(1, 3))
    out = np.repeat(np.repeat(sigma, b, axis=0), b, axis=1)
    full = np.empty((H, W), np.float64)
    full[:out.shape[0], :out.shape[1]] = out
    if out.shape[0] < H:
        full[out.shape[0]:, :out.shape[1]] = out[-1:, :]
    if out.shape[1] < W:
        full[:, out.shape[1]:] = full[:, out.shape[1] - 1:out.shape[1]]
    return full


# =========================================================================== #
# (5) コピー&ムーブ検出                                                        #
# =========================================================================== #
def _self_match(desc: np.ndarray, kp: np.ndarray, min_offset: float,
                ratio: float) -> np.ndarray:
    """**自己を除いた**最近傍マッチ。:func:`features.match_descriptors` では書けない。

    実測(``tests/test_imgforensics.py::test_match_descriptors_cannot_self_match``):
    ``features.match_descriptors(d, d)`` は 100% ``[[i, i]]`` を返す —— 自分自身が
    距離 0 の最近傍なので Lowe の比率検定も素通しする。コピー&ムーブに要るのは
    「自分から ``min_offset`` px 以上離れた中での最近傍」で、その除外条件は
    2 集合マッチの API に存在しない。だからここだけ新しく書いている。

    返りは ``(M, 2)`` の添字対(i < j に正規化し、重複を除く)。
    """
    n = desc.shape[0]
    if n < 2:
        return np.empty((0, 2), int)
    d2 = (desc ** 2).sum(1)[:, None] + (desc ** 2).sum(1)[None, :] - 2.0 * desc @ desc.T
    np.maximum(d2, 0.0, out=d2)
    dy = kp[:, 0][:, None] - kp[:, 0][None, :]
    dx = kp[:, 1][:, None] - kp[:, 1][None, :]
    far = (dy * dy + dx * dx) >= float(min_offset) ** 2
    d2 = np.where(far, d2, np.inf)
    order = np.argsort(d2, axis=1)
    pairs = set()
    r2 = float(ratio) ** 2
    for i in range(n):
        j, j2 = int(order[i, 0]), int(order[i, 1]) if n > 1 else None
        if not np.isfinite(d2[i, j]):
            continue
        second = d2[i, j2] if j2 is not None else np.inf
        if np.isfinite(second) and not (d2[i, j] < r2 * second):
            continue
        pairs.add((min(i, j), max(i, j)))
    return np.asarray(sorted(pairs), int).reshape(-1, 2)


def _orient(src: np.ndarray, dst: np.ndarray):
    """対応の向きを **位置で** 正規化する(シフトが辞書順で正になるよう入れ替える)。

    向きを添字(記述子の並び順)で決めていた最初の実装では、同じ複製に対して
    ``(110, 128)`` と ``(-110, -128)`` が画像サイズによって入れ替わった(実測)。
    シフトは**画像の中の位置の差**なので、添字ではなく位置で決めるのが正しい。
    """
    off = dst - src
    flip = (off[:, 0] < 0) | ((off[:, 0] == 0) & (off[:, 1] < 0))
    s = np.where(flip[:, None], dst, src)
    d = np.where(flip[:, None], src, dst)
    return s, d


def _cluster_by_offset(src: np.ndarray, dst: np.ndarray, tol: float):
    """対応をシフトベクトルで束ねる。``tol`` px の格子に丸めて同じ箱を 1 群にする。"""
    off = dst - src
    key = np.round(off / max(tol, 1e-9)).astype(int)
    groups = {}
    for i in range(off.shape[0]):
        groups.setdefault((int(key[i, 0]), int(key[i, 1])), []).append(i)
    return sorted(groups.values(), key=len, reverse=True)


#: :func:`copy_move_regions` の ``method="block"`` が一度に扱えるブロック数。
#: ``step=1`` だと画素数ぶんのブロックが出るので、``(block, block)`` の DCT を
#: まとめて取る配列が ``n_blocks * block**2 * 8`` バイトになる。``300_000`` は
#: 8x8 ブロックで 154 MB、16x16 で 614 MB。超えたら ``step`` を上げるか ROI へ切る。
MAX_BLOCKS = 300_000


def _block_features(x: np.ndarray, block: int, step: int, n_dct: int,
                    min_variance: float):
    """重なりブロックの **DCT 低周波特徴** と位置。``sliding_window_view`` で一括。

    Python ループでブロックごとに DCT を取ると ``step=1`` は現実的な時間で
    終わらない(256x256 で 6 万ブロック)。ここは配列 1 本にまとめて
    ``scipy.fft.dctn`` を 1 回だけ呼ぶ。
    """
    from numpy.lib.stride_tricks import sliding_window_view

    win = sliding_window_view(x, (block, block))[::step, ::step]
    nh, nw = win.shape[0], win.shape[1]
    n = nh * nw
    if n > MAX_BLOCKS:
        raise ValueError(
            f"ブロック数 {n} が上限 {MAX_BLOCKS} を超える(block={block}, step={step}, "
            f"shape={x.shape})。step を上げるか ROI に切ること")
    blk = np.ascontiguousarray(win.reshape(n, block, block))
    keep = blk.var(axis=(1, 2)) >= float(min_variance)
    if not keep.any():
        return np.empty((0, n_dct)), np.empty((0, 2))
    zz = _zigzag_order(block)[:n_dct]
    d = sfft.dctn(blk[keep], axes=(1, 2), norm="ortho").reshape(-1, block * block)
    rr, cc = np.meshgrid(np.arange(nh) * step, np.arange(nw) * step, indexing="ij")
    pos = np.stack([rr.ravel(), cc.ravel()], 1).astype(np.float64)[keep]
    return d[:, zz], pos


def _bbox(pts: np.ndarray):
    return (int(pts[:, 0].min()), int(pts[:, 1].min()),
            int(pts[:, 0].max()), int(pts[:, 1].max()))


def copy_move_regions(image, method: str = "keypoint", min_matches: int = 4,
                      min_offset: float = 16.0, offset_tol: float = 2.0,
                      ratio: float = 0.6, patch: int = 11,
                      block: int = 8, step: int = 1, n_dct: int = 10,
                      min_variance: float = 1e-4, max_feature_dist: float = 0.02,
                      neighbours: int = 2, ransac_thresh: float = 3.0,
                      ransac_iters: int = 300, seed: int = 0) -> list:
    """1 枚の画像の中の **コピー&ムーブ**(自己複製)領域の対を返す。``table``。

    ``method="keypoint"``(既定)
        :func:`features.harris_corners` でコーナーを取り、
        :func:`features.describe_patches` で正規化パッチ記述子を作り、
        **自分から ``min_offset`` px 以上離れた**最近傍と Lowe の比率検定で対応を作る
        (:func:`_self_match`)。対応をシフトベクトルで束ね、群ごとに
        :func:`mosaic.proj_match_points_ransac` で幾何整合を確認する。
        相似変換は :func:`fit_transform.vector_to_similarity`(Umeyama)で当てて
        ``similarity`` に入れる。

    ``method="block"``
        Fridrich, Soukal & Lukáš 2003。``block`` 角の重なりブロックを ``step`` px
        刻みで取り(既定 ``step=1`` —— **これは飾りではない**。下の「歩幅」参照)、
        各ブロックの DCT 低周波 ``n_dct`` 係数を特徴にして辞書順に並べ、
        辞書順で近い ``neighbours`` 件までを候補にし、特徴距離が
        ``max_feature_dist`` 以下のものだけをシフトベクトルで数える。
        回転・拡大には効かないが、角の少ない画像で keypoint 法より拾える。
        分散が ``min_variance`` 未満のブロックは捨てる(**一様な空を空にコピーしても
        同じ特徴になる** = 検出器が必ず作る偽陽性の主因)。

    **歩幅 (``step``) を 1 にしてある理由(実測で決めた)**: ブロック法が「同じ特徴」を
    見つけられるのは、複製元と複製先が **同じ格子に乗ったとき**だけである。
    ``step=4`` にすると、シフトが 4 の倍数でない複製(たとえば ``(110, 128)``)は
    **原理的に一度も一致しない**。実測で ``step=4`` は真のシフトを 1 件も返さず、
    代わりに偽の群を 60 件返した。``step=1`` なら真のシフトが第 1 群に来る。
    大きい画像で重いときは ``step`` を上げてよいが、**上げた歩幅の倍数のシフト
    しか見つからなくなる**ことを承知の上で上げること。

    返りは領域対の list(対応数の多い順)。各要素:

    ``offset``       シフト ``(dy, dx)``(row, col)。向きは **位置で正規化**してある
                     (辞書順で正になる向き)—— 添字で決めると同じ複製が
                     ``(110, 128)`` にも ``(-110, -128)`` にもなる(実測して直した)
    ``n_matches``    その群の対応数
    ``n_inliers``    RANSAC の内点数(``method="block"`` では ``n_matches`` と同じ)
    ``inlier_ratio`` 内点率
    ``src_bbox`` / ``dst_bbox``  ``(r0, c0, r1, c1)``
    ``src_points`` / ``dst_points``  ``(N, 2)`` の (row, col)
    ``similarity``   Umeyama で当てた ``3x3``(``method="keypoint"`` のみ、なければ ``None``)
    ``method``       使った方法
    ``caveats``      この結果が言えないこと

    **正解が手元にあるので当てられることを数で固定してある**
    (``tests/test_imgforensics.py::test_copy_move_finds_the_known_offset``、
    256x256 のテクスチャ画像の ``(40, 32)`` にある 64x64 を ``(150, 160)`` へ複製 =
    真のシフト ``(110, 128)``):

    ============ ================ ============ ==============
    method       第 1 群の offset  n_matches    誤差
    ============ ================ ============ ==============
    keypoint     (110.0, 128.0)   9            0 px
    block        (110.0, 128.0)   1225         0 px
    ============ ================ ============ ==============

    **言えないこと**(すべて同じテストで測ってある):

    * 一様な領域(空・壁)は複製しなくても同じ特徴になる。``min_variance=0`` に
      すると、同じ画像で block 法の群が 1 → 42 件に増える。
    * ``method="keypoint"`` は正規化パッチ記述子なので **回転に効かない**。
      複製を回して貼ると第 1 群の対応数は 0 度 9 件 → 5 度 4 件 → 15 度 0 件
      → 30 度 0 件。``similarity`` に回転が入って返ることは実質ない。
    * ``method="block"`` は **回転にまったく効かない**(5 度でも 0 件)。
    * 検出ゼロ = 複製が無い、ではない。平滑化・ノイズ付与・再圧縮を挟んだ複製は
      特徴距離が伸びて ``max_feature_dist`` を超える。実測:同じ複製を品質 75 の
      JPEG に通すと block 法は 1225 → 0 件、keypoint 法は 9 → 6 件。
    """
    x = _as_image(image)
    mo = _unit_float(min_offset, "min_offset", 0.0, float(max(x.shape)))
    tol = _unit_float(offset_tol, "offset_tol", 1e-3, float(max(x.shape)))
    rt = _unit_float(ratio, "ratio", 1e-3, 1.0)
    mm = _pos_int(min_matches, "min_matches", 2)
    caveats = [
        "一様な領域は複製しなくても一致する。min_variance を下げると偽陽性が増える",
        "keypoint 法は正規化パッチ記述子なので回転・拡大した複製は取れない",
        "block 法は step の倍数のシフトしか見つけられない(既定 step=1)",
        "検出ゼロ = 複製が無い、ではない(平滑化・再圧縮された複製は距離が伸びる)",
        "シフトが同じ群は 1 件にまとまる。同じシフトの別々の複製は区別できない",
    ]
    if method == "keypoint":
        kp = features.harris_corners(x)
        if kp.shape[0] < 2:
            return []
        desc, kp = features.describe_patches(x, kp, patch)
        pairs = _self_match(desc, kp.astype(np.float64), mo, rt)
        if pairs.shape[0] == 0:
            return []
        src, dst = _orient(kp[pairs[:, 0]].astype(np.float64),
                           kp[pairs[:, 1]].astype(np.float64))
        out = []
        for g in _cluster_by_offset(src, dst, tol):
            if len(g) < mm:
                continue
            s, d = src[g], dst[g]
            res = mosaic.proj_match_points_ransac(s, d, thresh=float(ransac_thresh),
                                                  iters=int(ransac_iters), seed=int(seed))
            inl = np.asarray(res["inliers"], bool)
            if int(inl.sum()) < mm:            # RANSAC が 4 点未満で諦めた場合も含む
                inl = np.ones(len(g), bool)
                n_in = len(g)
            else:
                n_in = int(inl.sum())
            si, di = s[inl], d[inl]
            sim = None
            if n_in >= 2:
                try:
                    sim = fit_transform.vector_to_similarity(si, di)
                except Exception:                        # 退化した配置(全点同一など)
                    sim = None
            out.append({
                "offset": (float(np.median(di[:, 0] - si[:, 0])),
                           float(np.median(di[:, 1] - si[:, 1]))),
                "n_matches": int(len(g)), "n_inliers": n_in,
                "inlier_ratio": float(n_in / len(g)),
                "src_bbox": _bbox(si), "dst_bbox": _bbox(di),
                "src_points": si, "dst_points": di,
                "similarity": sim, "method": "keypoint", "caveats": caveats,
            })
        return sorted(out, key=lambda r: (-r["n_matches"], r["offset"]))
    if method == "block":
        b = _pos_int(block, "block", 4, max(4, min(x.shape)))
        st = _pos_int(step, "step", 1, b)
        nd = _pos_int(n_dct, "n_dct", 1, b * b)
        nb = _pos_int(neighbours, "neighbours", 1, 64)
        mfd = _unit_float(max_feature_dist, "max_feature_dist", 0.0, 1e6)
        if min(x.shape) < b:
            raise ValueError(f"block={b} が画像 {x.shape} より大きい")
        feat, pos = _block_features(x, b, st, nd, min_variance)
        if feat.shape[0] < 2:
            return []
        order = np.lexsort(tuple(feat[:, k] for k in range(feat.shape[1] - 1, -1, -1)))
        groups = {}
        for w in range(1, min(nb, feat.shape[0] - 1) + 1):
            a_idx, b_idx = order[:-w], order[w:]
            off = pos[b_idx] - pos[a_idx]
            far = (off[:, 0] ** 2 + off[:, 1] ** 2) >= mo * mo
            close = np.linalg.norm(feat[a_idx] - feat[b_idx], axis=1) <= mfd
            sel = np.flatnonzero(far & close)
            if sel.size == 0:
                continue
            s, d = _orient(pos[a_idx[sel]], pos[b_idx[sel]])
            key = np.round((d - s) / tol).astype(int)
            for i in range(sel.size):
                groups.setdefault((int(key[i, 0]), int(key[i, 1])), []).append((s[i], d[i]))
        out = []
        for _, items in sorted(groups.items(), key=lambda kv: -len(kv[1])):
            if len(items) < mm:
                continue
            s = np.asarray([p for p, _ in items], np.float64)
            d = np.asarray([q for _, q in items], np.float64)
            out.append({
                "offset": (float(np.median(d[:, 0] - s[:, 0])),
                           float(np.median(d[:, 1] - s[:, 1]))),
                "n_matches": int(len(items)), "n_inliers": int(len(items)),
                "inlier_ratio": 1.0,
                "src_bbox": _bbox(s), "dst_bbox": _bbox(d),
                "src_points": s, "dst_points": d,
                "similarity": None, "method": "block", "caveats": caveats,
            })
        return out
    raise ValueError(f"method は 'keypoint' / 'block'、{method!r} が来た")



# =========================================================================== #
# (6) DWT-DCT 電子透かし                                                       #
# =========================================================================== #
def _wm_blocks(image, wavelet: str, level: int):
    """DWT → LL 副帯域 → 8x8 ブロックの格子。(pywt, coeffs, LL, nh, nw)。"""
    pywt = _require("pywt", "watermark")
    x = _as_image(image)
    lv = _pos_int(level, "level", 1, 4)
    maxlv = int(pywt.dwtn_max_level(x.shape, wavelet))
    if maxlv < lv:
        raise ValueError(f"画像 {x.shape} には level={lv} の {wavelet} 分解ができない"
                         f"(最大 {maxlv})")
    coeffs = pywt.wavedec2(x, wavelet, level=lv, mode="periodization")
    ll = np.asarray(coeffs[0], np.float64)
    nh, nw = ll.shape[0] // 8, ll.shape[1] // 8
    if nh < 1 or nw < 1:
        raise ValueError(f"LL 副帯域 {ll.shape} が 8x8 ブロックに満たない。"
                         "画像を大きくするか level を下げること")
    return pywt, coeffs, ll, nh, nw


def watermark_embed(image, bits, strength: float = 0.1, wavelet: str = "haar",
                    level: int = 1) -> np.ndarray:
    """DWT-DCT **電子透かし**の埋め込み。透かし入り画像 ``(H, W)`` を返す。``image2d``。

    1 段 DWT(既定 haar)の LL 副帯域を 8x8 に切り、各ブロックの直交 DCT-II の
    **中帯域係数の対** ``(3,1)`` と ``(1,3)`` の大小関係で 1 ビットを表す
    (Hsu & Wu 1999 の中帯域係数対法)。差が ``strength`` 未満なら差が
    ``strength`` になるまで **対称に**動かす(片方だけ動かすとブロックの
    エネルギーが偏る)。抽出に原画像は要らない(ブラインド)。

    容量は ``(LL の高さ // 8) * (LL の幅 // 8)`` ビット。``bits`` がそれより短ければ
    先頭から埋め、残りのブロックは触らない。長ければ :class:`ValueError`。

    ``bits`` は bool の 1-D(``phash`` 語彙)。0/1 の int 配列も受けるが、
    **float は受けない**(丸めの向きを黙って決めない)。

    強度と画質のトレードオフは :func:`watermark_capacity` が掃引して表で返す。
    実測(256x256 の合成画像・128 ビット、``tests/test_imgforensics.py``):

    ========= ========== ======
    strength  PSNR (dB)  BER
    ========= ========== ======
    0.02      68.42      0.000
    0.05      60.71      0.000
    0.10      54.79      0.000
    0.20      48.85      0.000
    0.40      42.94      0.000
    ========= ========== ======

    **PyWavelets 必須**(:class:`ImportError`)。
    """
    st = _unit_float(strength, "strength", 0.0, 10.0, inclusive_lo=False)
    b = np.asarray(bits)
    if b.ndim != 1 or b.size == 0:
        raise ValueError("bits は空でない 1-D")
    if b.dtype.kind == "f":
        raise ValueError("bits に float は受け取らない(0.5 をどちらに丸めるかを"
                         "黙って決めない)。bool か整数の 0/1 で渡すこと")
    if b.dtype != np.bool_:
        if not np.all((b == 0) | (b == 1)):
            raise ValueError("整数の bits は 0 と 1 のみ")
        b = b.astype(bool)
    pywt, coeffs, ll, nh, nw = _wm_blocks(image, wavelet, level)
    cap = nh * nw
    if b.size > cap:
        raise ValueError(f"bits が {b.size} 個あるが容量は {cap} ビット"
                         f"(LL {ll.shape} → {nh}x{nw} ブロック)")
    ua, va = _WM_COEFF_A
    ub, vb = _WM_COEFF_B
    out = ll.copy()
    for i in range(b.size):
        r, c = (i // nw) * 8, (i % nw) * 8
        blk = out[r:r + 8, c:c + 8]
        D = sfft.dctn(blk, norm="ortho")
        d = D[ua, va] - D[ub, vb]
        want = st if b[i] else -st
        if (want > 0 and d < st) or (want < 0 and d > -st):
            adj = (want - d) / 2.0
            D[ua, va] += adj
            D[ub, vb] -= adj
            out[r:r + 8, c:c + 8] = sfft.idctn(D, norm="ortho")
    new = [out] + list(coeffs[1:])
    rec = np.asarray(pywt.waverec2(new, wavelet, mode="periodization"), np.float64)
    x = _as_image(image)
    return rec[:x.shape[0], :x.shape[1]]


def watermark_extract(image, n_bits: int, wavelet: str = "haar",
                      level: int = 1) -> np.ndarray:
    """透かしの **ブラインド抽出**。bool の 1-D(``phash`` 語彙)を返す。

    同じ DWT / ブロック分割で中帯域係数の対の大小を読むだけ。原画像も鍵も要らない
    —— これは **秘匿ではなく完全性の印**であり、鍵が無いので **誰でも消せるし
    誰でも書ける**。所有権の主張には使えない。

    返りが ``phash`` 語彙なので、埋めたビット列との一致は :func:`hash_distance` で
    そのまま数えられる(BER = ``hash_distance(sent, got) / n_bits``)。
    語彙を合わせてあるのはそのため。

    **PyWavelets 必須**(:class:`ImportError`)。
    """
    n = _pos_int(n_bits, "n_bits", 1)
    _pywt, _coeffs, ll, nh, nw = _wm_blocks(image, wavelet, level)
    cap = nh * nw
    if n > cap:
        raise ValueError(f"n_bits={n} が容量 {cap} を超える(LL {ll.shape})")
    ua, va = _WM_COEFF_A
    ub, vb = _WM_COEFF_B
    bits = np.zeros(n, bool)
    for i in range(n):
        r, c = (i // nw) * 8, (i % nw) * 8
        D = sfft.dctn(ll[r:r + 8, c:c + 8], norm="ortho")
        bits[i] = D[ua, va] > D[ub, vb]
    return bits


def watermark_capacity(image, bits, strengths=(0.02, 0.05, 0.1, 0.2, 0.4),
                       wavelet: str = "haar", level: int = 1,
                       jpeg_quality=None) -> dict:
    """埋め込み強度と **PSNR / BER** のトレードオフを掃引して返す。``table``。

    各 ``strength`` について埋め込み → 抽出を実際に走らせ、

    ``psnr_db``  原画像と透かし入り画像の PSNR(値域 [0, 1] 基準、``MAX=1``)
    ``ber``      抽出のビット誤り率(:func:`hash_distance` で数える)
    ``clipped``  透かし入り画像が [0, 1] からはみ出した画素の割合。
                 **はみ出しは保存時に必ず失われる**ので、PSNR だけ見て強度を
                 上げると「測っていない劣化」が増える

    ``jpeg_quality`` に品質を渡すと、透かし入り画像を **本物の JPEG** に通してから
    抽出した ``ber_jpeg`` も入る(Pillow 必須。省略時は列ごと入らない ——
    環境によって返る列が変わらないようにするため、既定では走らせない)。

    返りは ``{"capacity_bits": int, "n_bits": int, "rows": [...], "caveats": [...]}``。
    """
    rows = []
    for s in strengths:
        wm = watermark_embed(image, bits, strength=float(s), wavelet=wavelet, level=level)
        x = _as_image(image)
        mse = float(np.mean((np.clip(wm, 0.0, 1.0) - x) ** 2))
        psnr = float("inf") if mse <= 0 else float(10.0 * np.log10(1.0 / mse))
        n = int(np.asarray(bits).size)
        got = watermark_extract(wm, n, wavelet=wavelet, level=level)
        sent = np.asarray(bits).astype(bool)
        row = {
            "strength": float(s),
            "psnr_db": psnr,
            "ber": hash_distance(sent, got) / n,
            "clipped": float(np.mean((wm < 0.0) | (wm > 1.0))),
        }
        if jpeg_quality is not None:
            _require("PIL", "watermark_capacity(jpeg_quality=...)")
            rec = _jpeg_roundtrip(_to_uint8(np.clip(wm, 0.0, 1.0)),
                                  _pos_int(jpeg_quality, "jpeg_quality", 1, 100)) / 255.0
            row["ber_jpeg"] = hash_distance(sent, watermark_extract(
                rec, n, wavelet=wavelet, level=level)) / n
        rows.append(row)
    _p, _c, ll, nh, nw = _wm_blocks(image, wavelet, level)
    return {
        "capacity_bits": int(nh * nw),
        "n_bits": int(np.asarray(bits).size),
        "ll_shape": tuple(int(v) for v in ll.shape),
        "rows": rows,
        "caveats": [
            "鍵が無いので秘匿性は無い。誰でも読めて、誰でも消せて、誰でも書ける",
            "PSNR は [0,1] クリップ後で測っている。clipped が大きい行は"
            "『測っていない劣化』を含む",
            "BER 0 は『この処理では消えない』であって『どんな処理でも消えない』ではない",
            "回転・切り出し・リサイズには一切耐えない(ブロックの位置がずれるため)",
        ],
    }


if __name__ == "__main__":                              # pragma: no cover
    print(f"imgforensics: {len(IMGFORENSICS)} ops")
    for name in IMGFORENSICS:
        fn = globals()[name]
        head = (fn.__doc__ or "").strip().splitlines()[0]
        print(f"  {name:26s} {head}")
