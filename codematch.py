# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""codematch —— 符号系の頑健照合(方向符号・増分符号・選択的相関・放射リーチ)。

明るさの値そのものではなく、**明るさの変化の向き**を符号にして比べる照合の族。
照明が変わっても、局所的に光っても、物の一部が隠れても、符号は値ほどは崩れない。
学習した特徴は使わない(式と閾値だけで、壊れる所を自分で言える)。

文献(式から再実装した。文章・図・数値表は写していない):

* F. Ullah, S. Kaneko, S. Igarashi, "Orientation Code Matching for Robust Object
  Search", IEICE Trans. Inf. & Syst. E84-D(8), 2001(方向符号照合 OCM)。符号化と
  相違度の表は、T. Honda, H. Takauji, S. Kaneko, 「照明スペクトル変動に対して
  ロバストな重み付きカラー方向符号照合法」, 精密工学会誌 75(2), 2009 の再掲
  (式 (1)〜(5))で確かめた。
* S. Kaneko, I. Murase, S. Igarashi, "Robust image registration by increment sign
  correlation", Pattern Recognition 35(10), 2002(和文: 村瀬・金子・五十嵐,
  精密工学会誌 66(2), 2000)。増分符号相関 ISC。
* S. Kaneko, Y. Satoh, S. Igarashi, "Using selective correlation coefficient for
  robust image registration", Pattern Recognition 36(5), 2003(和文: 佐藤・金子・
  五十嵐, 電気学会論文誌 C 121(4), 2001)。選択的相関係数 SCC。
* Y. Satoh, S. Kaneko, Y. Niwa, K. Yamamoto, "Robust object detection using a Radial
  Reach Filter (RRF)", Systems and Computers in Japan 35(10), 2004。式は和島ほか,
  電気学会論文誌 C 129(10), 2009 の再掲(式 (1)〜(5))で確かめた。

ここに書いた再実装は著者の承認を受けたものではない。

## 6 つの op

``orientation_code``
    Sobel 勾配の向き θ を N 段に量子化した符号 ``floor(θ / (2π/N))``。
    ``|∇x| + |∇y| <= grad_thresh`` の画素は無効符号 N。
``increment_sign``
    隣の画素との増分の符号 ``b = [I(x+1) >= I(x)]``(行方向、または列方向)。
``ocm_match``
    符号の巡回差 ``min(|a-b|, N-|a-b|)`` の平均で照合する。テンプレート側が無効なら 0、
    対象側だけ無効なら N/4(一様に乱れた符号の巡回差の期待値と同じ)。相違度
    ``h = mean / (N/2)`` を 0〜1 にし、類似度 ``1 - h`` を ``score`` で返す。
``isc_match``
    増分符号の一致率。**狭義単調増加の明るさの変換では値が 1 ビットも変わらない**
    (増分の符号は保たれ、等しい画素は等しいまま)。
``scc_match``
    隣り合う 2 画素の組ごとに増分符号の一致を見て、一致した組だけで正規化相関を取る。
    平均はテンプレート・窓の**全画素**の平均(論文の式 (2))。
``radial_reach_filter``
    背景の各画素から 8 方向へ、明るさの差が ``t_p`` 以上になる最初の画素(reach)を
    探し、その差の符号が現在の画像でも保たれているかを数える。保たれた方向の割合が
    ``agree_thresh`` 未満の画素を前景とする。

## 黙って間違わない(fail-closed)

* テンプレートに有効な符号が足りない(平坦・低コントラスト)ときは、照合の値を
  返さずに ``ValueError``。NCC はこの場合もどこかに最大値を作って返す。
* SCC は一致した組が少なすぎる位置、窓の分散が 0 の位置を採点から外す
  (``valid_map``)。全位置が外れたら ``ValueError``。
* RRF は reach が見つかった方向が ``min_dirs`` 未満の画素を「判定しない」
  (``decided`` が False)。判定できた画素が ``min_decided_fraction`` 未満なら
  ``ValueError``。
* NaN / inf、2 次元でない入力、テンプレートが画像より大きいときも ``ValueError``。

照合の返り値の座標は ``find_ncc_model`` と同じ**テンプレート中心**
(``row = row_tl + h // 2``)。左上は ``row_tl`` / ``col_tl``。
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage
from scipy.signal import fftconvolve

__all__ = [
    "orientation_code", "increment_sign",
    "ocm_match", "isc_match", "scc_match",
    "radial_reach_filter",
]

#: 量子化の境界ちょうどの角度(|gx| = |gy| や gy = 0)を上の段へ寄せる余裕(符号の単位)。
#: 浮動小数点で π/2 が 3.9999999 段に化けて 1 段ずれるのを止める。rot90 の同変性の門が
#: これに依存する(境界ちょうどの画素は自然画像でも 0 ではない)。
_EDGE_TOL = 1e-9

#: 8 方向(行, 列)。RRF の reach を探す向き。
_DIRS8 = ((0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1))


# --------------------------------------------------------------------------- #
# 入力の検査                                                                    #
# --------------------------------------------------------------------------- #
def _image(a, name: str, op: str) -> np.ndarray:
    """2 次元・有限・各辺 2 以上の float64 画像に直す。だめなら ValueError。"""
    try:
        arr = np.asarray(a, dtype=np.float64)
    except (TypeError, ValueError) as e:
        raise ValueError("%s: %s is not numeric (%s)" % (op, name, e)) from None
    if arr.ndim != 2:
        raise ValueError("%s: %s must be a 2-D grey image, got shape %s"
                         % (op, name, arr.shape))
    if arr.shape[0] < 2 or arr.shape[1] < 2:
        raise ValueError("%s: %s is too small (%s); need at least 2x2"
                         % (op, name, arr.shape))
    if not np.all(np.isfinite(arr)):
        raise ValueError("%s: %s contains NaN or inf" % (op, name))
    return arr


def _pair(image, template, op: str):
    img = _image(image, "image", op)
    tpl = _image(template, "template", op)
    if tpl.shape[0] > img.shape[0] or tpl.shape[1] > img.shape[1]:
        raise ValueError("%s: template %s is larger than image %s"
                         % (op, tpl.shape, img.shape))
    return img, tpl


def _n_codes(n, op: str) -> int:
    try:
        n_i = int(n)
    except (TypeError, ValueError):
        raise ValueError("%s: n_codes must be an integer, got %r" % (op, n)) from None
    if n_i != n or n_i < 4 or n_i > 256 or n_i % 4:
        raise ValueError("%s: n_codes must be a multiple of 4 in [4, 256], got %r" % (op, n))
    return n_i


def _nonneg(x, name: str, op: str) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a number, got %r" % (op, name, x)) from None
    if not math.isfinite(v) or v < 0:
        raise ValueError("%s: %s must be finite and >= 0, got %r" % (op, name, x))
    return v


def _fraction(x, name: str, op: str) -> float:
    v = _nonneg(x, name, op)
    if v > 1:
        raise ValueError("%s: %s must be in [0, 1], got %r" % (op, name, x))
    return v


def _count(x, name: str, op: str, lo: int = 1) -> int:
    try:
        v = int(x)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be an integer, got %r" % (op, name, x)) from None
    if v != x or v < lo:
        raise ValueError("%s: %s must be an integer >= %d, got %r" % (op, name, lo, x))
    return v


# --------------------------------------------------------------------------- #
# 共通の部品                                                                    #
# --------------------------------------------------------------------------- #
def _corr_valid(field, kernel):
    """``out[y, x] = sum_u field[y + u] * kernel[u]``(全面が重なる位置だけ)を FFT で。"""
    return fftconvolve(field, kernel[::-1, ::-1], mode="valid")


def _match_result(score, higher_better: bool, tshape, valid=None, **extra) -> dict:
    """照合の最良位置・次点・余裕を、find_ncc_model と同じ中心規約で返す。

    同点は **raster 順で先の位置**(score を 12 桁に丸めてから比べる。argmax の屑で
    OS ごとに答えが変わらないように)。次点は最良位置から ``max(h, w) // 2`` 画素より
    離れた位置の最良(近傍の裾を次点と数えない)。
    """
    s = np.asarray(score, dtype=np.float64)
    ok = np.ones(s.shape, bool) if valid is None else np.asarray(valid, bool)
    key = np.round(s if higher_better else -s, 12)
    key = np.where(ok, key, -np.inf)
    flat = int(np.argmax(key))
    r0, c0 = np.unravel_index(flat, s.shape)
    th, tw = tshape
    rad = max(th, tw) // 2
    yy, xx = np.ogrid[:s.shape[0], :s.shape[1]]
    far = ok & ((np.abs(yy - r0) > rad) | (np.abs(xx - c0) > rad))
    if far.any():
        k2 = np.where(far, key, -np.inf)
        f2 = int(np.argmax(k2))
        r1, c1 = np.unravel_index(f2, s.shape)
        second = float(s[r1, c1])
        second_rc = (int(r1) + th // 2, int(c1) + tw // 2)
    else:
        second = float("nan")
        second_rc = (-1, -1)
    best = float(s[r0, c0])
    if math.isnan(second):
        margin = float("inf")
    else:
        margin = (best - second) if higher_better else (second - best)
    out = {
        "row": int(r0) + th // 2, "col": int(c0) + tw // 2, "column": int(c0) + tw // 2,
        "row_tl": int(r0), "col_tl": int(c0),
        "score": best, "second_score": second if not math.isnan(second) else best,
        "second_row": second_rc[0], "second_col": second_rc[1],
        "margin": margin if math.isfinite(margin) else 0.0,
        "has_second": bool(far.any()),
        "score_map": s,
    }
    out.update(extra)
    return out


# --------------------------------------------------------------------------- #
# 方向符号                                                                      #
# --------------------------------------------------------------------------- #
def _codes(img: np.ndarray, n: int, gthr: float) -> np.ndarray:
    gx = ndimage.sobel(img, axis=1, mode="nearest")
    gy = ndimage.sobel(img, axis=0, mode="nearest")
    theta = np.mod(np.arctan2(gy, gx), 2.0 * np.pi)
    code = np.floor(theta / (2.0 * np.pi / n) + _EDGE_TOL).astype(np.int64) % n
    code[(np.abs(gx) + np.abs(gy)) <= gthr] = n
    return code.astype(np.int16)


def orientation_code(image, n_codes=16, grad_thresh=0.05):
    """勾配の向きを ``n_codes`` 段に量子化した方向符号の画像(OCM の符号化)。

    ``θ = atan2(∂I/∂行, ∂I/∂列)`` を [0, 2π) に取り(Sobel、縁は最近傍で延長)、
    ``floor(θ / (2π/N))`` を符号 0..N-1 にする。``|∂I/∂列| + |∂I/∂行| <= grad_thresh``
    の画素は無効符号 ``N``(雑音しか無い所の向きは信用しない)。

    ``grad_thresh`` は [0, 1] の明るさで測った Sobel の和の閾値。既定 0.05 は、
    8 ビットの量子化雑音(σ = 1/255)が作る和の平均(約 0.022)の 2 倍強。
    ``n_codes`` は 4 の倍数(既定 16 = 22.5° 刻み)。返りは int16 の 2 次元配列。

    明るさに定数を足しても符号は 1 つも変わらない。明るさを g 倍したときは
    ``grad_thresh`` も g 倍すれば同じ符号になる。画像を 90° 回すと、符号は
    ``N/4`` だけ巡回してずれる(``np.rot90`` で反時計回りなら ``-N/4``)。
    """
    op = "orientation_code"
    img = _image(image, "image", op)
    n = _n_codes(n_codes, op)
    g = _nonneg(grad_thresh, "grad_thresh", op)
    return _codes(img, n, g)


def _code_distance(a, b, n: int):
    """巡回差 ``min(|a-b|, N-|a-b|)``。方向は 0 と N-1 が隣どうし。"""
    d = np.abs(np.asarray(a, np.int64) - np.asarray(b, np.int64))
    return np.minimum(d, n - d)


def ocm_match(image, template, n_codes=16, grad_thresh=0.05, min_valid=32,
              min_valid_fraction=0.05) -> dict:
    """方向符号照合(OCM)。符号の巡回差の平均が最小の位置を返す。

    相違度は画素ごとに ``D(m, n)``(m = テンプレート側、n = 画像側の符号):
    両方有効なら巡回差 ``min(|m-n|, N-|m-n|)``、テンプレート側が無効なら 0、
    画像側だけ無効なら ``N/4``。全画素の平均を ``N/2`` で割った相違度 ``h`` を
    ``dissimilarity_map`` に、``score = 1 - h``(1 が完全一致)を ``score_map`` に返す。
    和は 4 倍して整数で数える(FFT の丸めを ``rint`` で消す)ので、同じ入力の答えは
    環境によらず同じ。

    **テンプレートの有効な符号が** ``max(min_valid, min_valid_fraction × 画素数)``
    **に満たなければ ValueError**(平坦なテンプレートは位置を決めない)。

    返り: ``row`` / ``col``(テンプレート中心)、``score``、``dissimilarity``、
    ``second_score``・``margin``(最良から離れた次点との差)、``valid_fraction``
    (テンプレートの有効符号の割合)、``valid_required``・``refusal_margin``(拒否まで
    あと何画素の余裕があるか)、``score_map``、``dissimilarity_map``。
    """
    op = "ocm_match"
    img, tpl = _pair(image, template, op)
    n = _n_codes(n_codes, op)
    g = _nonneg(grad_thresh, "grad_thresh", op)
    mv = _count(min_valid, "min_valid", op)
    mf = _fraction(min_valid_fraction, "min_valid_fraction", op)
    ci = _codes(img, n, g)
    ct = _codes(tpl, n, g)
    vt = ct < n
    nv = int(vt.sum())
    need = max(mv, int(math.ceil(mf * tpl.size)))
    if nv < need:
        raise ValueError(
            "%s: template undetermined: only %d of %d pixels carry a valid orientation code "
            "(|gx|+|gy| > grad_thresh=%g); need %d. A flat or low-contrast template does not "
            "fix a position." % (op, nv, tpl.size, g, need))
    codes = np.arange(n + 1)
    total = np.zeros((img.shape[0] - tpl.shape[0] + 1, img.shape[1] - tpl.shape[1] + 1))
    for k in np.unique(ct[vt]):
        lut4 = 4 * _code_distance(k, codes, n)
        lut4[n] = n                       # 4 × N/4: 画像側だけ無効
        total += _corr_valid(lut4[ci].astype(np.float64), (ct == k).astype(np.float64))
    total = np.rint(total)
    dis = total / 4.0 / tpl.size / (n / 2.0)
    res = _match_result(1.0 - dis, True, tpl.shape, valid_fraction=nv / tpl.size,
                        n_codes=n, grad_thresh=g, dissimilarity_map=dis,
                        valid_required=need, refusal_margin=nv - need)
    res["dissimilarity"] = 1.0 - res["score"]
    return res


# --------------------------------------------------------------------------- #
# 増分符号                                                                      #
# --------------------------------------------------------------------------- #
def _axis(axis, op: str) -> int:
    if axis in (1, "h", "row", "x"):
        return 1
    if axis in (0, "v", "col", "y"):
        return 0
    raise ValueError("%s: axis must be 1 / 'h' (along rows) or 0 / 'v' (along columns), got %r"
                     % (op, axis))


def _sign(img: np.ndarray, ax: int) -> np.ndarray:
    if ax == 1:
        return (img[:, 1:] >= img[:, :-1]).astype(np.uint8)
    return (img[1:, :] >= img[:-1, :]).astype(np.uint8)


def increment_sign(image, axis="h"):
    """隣の画素との増分の符号 ``b = [I(次) >= I(今)]``(1 / 0 の uint8)。

    ``axis="h"``(既定)は行に沿って右隣と比べ、形は ``(H, W-1)``。``axis="v"`` は
    下隣と比べ、形は ``(H-1, W)``。等しい画素の組は 1(論文の ``>=`` の規約)。
    狭義単調増加の明るさの変換 ``g`` では ``increment_sign(g(I)) == increment_sign(I)``
    が厳密に成り立つ(ISC の不変性の芯)。
    """
    op = "increment_sign"
    img = _image(image, "image", op)
    return _sign(img, _axis(axis, op))


def _directions(direction, op: str):
    table = {"h": (1,), "v": (0,), "hv": (1, 0)}
    if direction not in table:
        raise ValueError("%s: direction must be 'h', 'v' or 'hv', got %r" % (op, direction))
    return table[direction]


def _informative(tpl: np.ndarray, axes, flat: float) -> int:
    n = 0
    for ax in axes:
        d = np.diff(tpl, axis=ax)
        n += int((np.abs(d) > flat).sum())
    return n


def isc_match(image, template, direction="h", flat_thresh=0.01, min_valid=32) -> dict:
    """増分符号相関(ISC)。増分符号が一致する割合が最大の位置を返す。

    ``r = (1/n) Σ [b_image == b_template]``(``n`` は増分の数)。乱れた位置での期待値は
    0.5、同じものなら 1 に近い。``direction="h"`` は論文どおり行に沿った増分、
    ``"hv"`` は縦の増分も足す 2 次元の拡張。

    **狭義単調増加の明るさの変換(ガンマ・ゲイン・オフセット・任意の単調な表)で
    ``score_map`` は 1 ビットも変わらない。**

    テンプレートの増分のうち ``|Δ| > flat_thresh`` のものが ``min_valid`` に満たなければ
    ValueError(平坦なテンプレートは符号が雑音で決まり、位置を決めない)。既定の 0.01 は
    [0, 1] の明るさで 8 ビットの約 2.5 階調 —— これより小さい増分の符号は撮像の雑音と同じ桁で
    決まる。この判定は
    テンプレートだけを見るので、上の不変性を壊さない。拒否までの余裕は ``refusal_margin``。
    """
    op = "isc_match"
    img, tpl = _pair(image, template, op)
    axes = _directions(direction, op)
    flat = _nonneg(flat_thresh, "flat_thresh", op)
    mv = _count(min_valid, "min_valid", op)
    info = _informative(tpl, axes, flat)
    if info < mv:
        raise ValueError(
            "%s: template undetermined: only %d increments exceed flat_thresh=%g; need %d. "
            "A flat template codes every pair as 1 and does not fix a position."
            % (op, info, flat, mv))
    agree = 0.0
    n = 0
    for ax in axes:
        bi = _sign(img, ax).astype(np.float64)
        bt = _sign(tpl, ax).astype(np.float64)
        agree = agree + _corr_valid(bi, bt) + _corr_valid(1.0 - bi, 1.0 - bt)
        n += bt.size
    agree = np.rint(agree)
    return _match_result(agree / n, True, tpl.shape, n_increments=n,
                         informative_increments=info, direction=direction,
                         valid_required=mv, refusal_margin=info - mv)


# --------------------------------------------------------------------------- #
# 選択的相関係数                                                                #
# --------------------------------------------------------------------------- #
def _scc_groups(th: int, K: int, extend: bool):
    """拡張マスクの組分け。要素 = (行 i, 組 k)。拡張なら 2 行 × 2 組(画素で 2 × 4)を 1 群に。

    端で 4 要素に満たない要素(行数・組数が奇数のときの余り)は 1 要素の群として基本マスクのまま。
    """
    if not extend:
        return [[(i, k)] for i in range(th) for k in range(K)]
    groups = []
    for a in range(0, th - th % 2, 2):
        for b in range(0, K - K % 2, 2):
            groups.append([(a, b), (a, b + 1), (a + 1, b), (a + 1, b + 1)])
    for i in range(th):
        for k in range(K):
            if (i >= th - th % 2) or (k >= K - K % 2):
                groups.append([(i, k)])
    return groups


def scc_match(image, template, flat_thresh=0.01, min_valid=32, min_mask_fraction=None,
              mask_extension=True, z_mask=4.0) -> dict:
    """選択的相関係数(SCC)。増分符号の一致する画素だけで正規化相関を取る。

    テンプレートの列を (0,1), (2,3), … の組にし、組ごとに右の画素が左以上かの符号
    ``b`` を作る。画像の窓の同じ組の符号 ``b'`` と一致すれば、その組の 2 画素の
    基本マスク ``c = 1``、違えば 0。
    ``r = Σ c (f - f̄)(g - ḡ) / sqrt(Σ c (f - f̄)² · Σ c (g - ḡ)²)``、
    ``f̄`` と ``ḡ`` は窓とテンプレートの**全画素**の平均。マスクが全部 1 なら NCC と
    厳密に一致する(列数が奇数なら最後の列は組を作らず、マスク 0)。

    ``mask_extension=True``(既定、論文の 3 章の拡張マスク)は、基本マスクの要素を
    2 行 × 2 組(画素で 2 × 4)ずつ束ね、4 つのうち 2 つ以上が不一致なら 4 つとも外し、
    そうでなければ 4 つとも使う。不一致の起こる確率が ``p`` の所で、外される確率は
    ``1 - (1-p)^4 - 4 p (1-p)^3``(p = 0.5 の遮蔽部で 0.6875)。端の余りの要素は基本マスクのまま。
    ``False`` は基本マスク(全位置を FFT で数えるので速い)。

    fail-closed:
    * テンプレートの組の増分のうち ``|Δ| > flat_thresh`` のものが ``min_valid`` 未満 → ValueError。
    * 使った画素が窓の ``min_mask_fraction`` 未満の位置、窓の選ばれた画素の
      分散が 0 の位置は採点しない(``valid_map`` が False、``score_map`` は -1)。
    * 採点できる位置が 1 つも無ければ ValueError。

    ``min_mask_fraction=None``(既定)は、**無相関の位置で期待される使用率**に
    ``z_mask`` 標準偏差を足した値を床にする。無相関なら増分符号は半々で一致するので、
    基本マスクの使用率の期待値は 1/2、拡張マスクは 4 要素の群で
    ``(1/2)^4 + 4 (1/2)^4 = 5/16``。標準偏差は群を独立な試行とみた 2 項分布の値。
    ★この床が無いと、SCC は「たまたま符号の合った画素だけ」を選んだ偽の位置で
    相関が 1 近くまで上がり、NCC より先に壊れる(選択の偏り。PoC で実測)。
    この床は論文の式には無く、論文の統計モデル(無相関で 0.5)から足した fail-closed。

    返り: ``row`` / ``col``、``score``、``mask_fraction``(最良位置で使った画素の割合)、
    ``mask``(最良位置のマスク、テンプレートと同じ形)、``score_map``、``valid_map``、
    ``mask_fraction_map``、``refusal_margin``(テンプレートの組の余裕)。
    """
    op = "scc_match"
    img, tpl = _pair(image, template, op)
    flat = _nonneg(flat_thresh, "flat_thresh", op)
    mv = _count(min_valid, "min_valid", op)
    zm = _nonneg(z_mask, "z_mask", op)
    if mask_extension not in (True, False, 0, 1):
        raise ValueError("%s: mask_extension must be True or False, got %r" % (op, mask_extension))
    ext = bool(mask_extension)
    th, tw = tpl.shape
    K = tw // 2
    if K < 1:
        raise ValueError("%s: template needs at least 2 columns to form a pair" % op)
    t0 = tpl[:, 0:2 * K:2]
    t1 = tpl[:, 1:2 * K:2]
    info = int((np.abs(t1 - t0) > flat).sum())
    if info < mv:
        raise ValueError(
            "%s: template undetermined: only %d pixel pairs differ by more than flat_thresh=%g; "
            "need %d." % (op, info, flat, mv))
    if min_mask_fraction is None:
        q = []
        for grp in _scc_groups(th, K, ext):
            q.append((len(grp), 5.0 / 16.0 if len(grp) == 4 else 0.5))
        n_el = float(th * K)
        mean_q = sum(n * qq for n, qq in q) / n_el
        sd_q = math.sqrt(sum(n * n * qq * (1.0 - qq) for n, qq in q)) / n_el
        # 使用率は画素で数える(組の 2 画素)。テンプレート全体に対する割合に直す
        mmf = min(1.0, (mean_q + zm * sd_q) * (2.0 * K) / tw)
    else:
        mmf = _fraction(min_mask_fraction, "min_mask_fraction", op)
    bt = (t1 >= t0)                                      # (th, K)
    tm = tpl.mean()
    u0, u1 = t0 - tm, t1 - tm
    oh, ow = img.shape[0] - th + 1, img.shape[1] - tw + 1
    bi = (img[:, 1:] >= img[:, :-1])                     # (H, W-1)、組の左の位置で引く

    if not ext:
        bif = bi.astype(np.float64)
        btf = bt.astype(np.float64)
        J = img[:, :-1]
        J1 = img[:, 1:]

        def kern(gk):
            k = np.zeros((th, 2 * K - 1))
            k[:, 0::2] = gk
            return k

        def msum(field, gk):
            """Σ_組 [b' == b] · field(画像側、組の左の位置) · gk(テンプレート側)。"""
            a = _corr_valid(bif * field, kern(btf * gk))
            b = _corr_valid((1.0 - bif) * field, kern((1.0 - btf) * gk))
            return (a + b)[:oh, :ow]

        one_i = np.ones_like(J)
        one_t = np.ones_like(btf)
        m_pix = 2.0 * np.rint(msum(one_i, one_t))
        s_it = msum(J, u0) + msum(J1, u1)
        s_t = msum(one_i, u0 + u1)
        s_i = msum(J + J1, one_t)
        s_ii = msum(J * J + J1 * J1, one_t)
        s_tt = msum(one_i, u0 * u0 + u1 * u1)
    else:
        m_pix = np.zeros((oh, ow))
        s_it = np.zeros((oh, ow))
        s_t = np.zeros((oh, ow))
        s_i = np.zeros((oh, ow))
        s_ii = np.zeros((oh, ow))
        s_tt = np.zeros((oh, ow))
        img2 = img * img
        for grp in _scc_groups(th, K, True):
            agree = np.zeros((oh, ow), np.int8)
            for (i, k) in grp:
                v = bi[i:i + oh, 2 * k:2 * k + ow]
                agree += v if bt[i, k] else ~v
            keep = (agree >= (3 if len(grp) == 4 else 1)).astype(np.float64)
            for (i, k) in grp:
                I0 = img[i:i + oh, 2 * k:2 * k + ow]
                I1 = img[i:i + oh, 2 * k + 1:2 * k + 1 + ow]
                m_pix += 2.0 * keep
                s_it += keep * (I0 * u0[i, k] + I1 * u1[i, k])
                s_t += keep * (u0[i, k] + u1[i, k])
                s_i += keep * (I0 + I1)
                s_ii += keep * (img2[i:i + oh, 2 * k:2 * k + ow] + img2[i:i + oh, 2 * k + 1:2 * k + 1 + ow])
                s_tt += keep * (u0[i, k] ** 2 + u1[i, k] ** 2)
    wsum = _corr_valid(img, np.ones((th, tw)))[:oh, :ow]
    mean_i = wsum / tpl.size
    num = s_it - mean_i * s_t
    var_i = s_ii - 2.0 * mean_i * s_i + mean_i * mean_i * m_pix
    var_t = s_tt
    # 分散の床は「丸めの屑」と区別できる大きさに: 明るさの尺度の 2 乗 × 画素数 × 1e-12
    scale = max(float(np.abs(img).max()), float(np.abs(tpl).max()), 1e-300) ** 2
    floor = 1e-12 * scale * tpl.size
    mask_frac = m_pix / tpl.size
    valid = (mask_frac >= mmf) & (var_i > floor) & (var_t > floor)
    if not valid.any():
        raise ValueError(
            "%s: no position has enough agreeing pairs (min_mask_fraction=%g) and a non-zero "
            "selected variance; the template is not located." % (op, mmf))
    den = np.sqrt(np.where(valid, var_i * var_t, 1.0))
    score = np.where(valid, np.clip(num / den, -1.0, 1.0), -1.0)
    res = _match_result(score, True, tpl.shape, valid=valid, valid_map=valid,
                        mask_fraction_map=mask_frac, mask_extension=ext,
                        min_mask_fraction=mmf)
    r0, c0 = res["row_tl"], res["col_tl"]
    mask = np.zeros(tpl.shape, bool)
    for grp in _scc_groups(th, K, ext):
        ag = [bool(bi[r0 + i, c0 + 2 * k]) == bool(bt[i, k]) for (i, k) in grp]
        kp = (sum(ag) >= 3) if len(grp) == 4 else ag[0]
        for (i, k) in grp:
            mask[i, 2 * k] = kp
            mask[i, 2 * k + 1] = kp
    res["mask"] = mask
    res["mask_fraction"] = float(mask_frac[r0, c0])
    res["valid_positions"] = int(valid.sum())
    res["valid_required"] = mv
    res["refusal_margin"] = info - mv
    return res


# --------------------------------------------------------------------------- #
# 放射リーチ                                                                    #
# --------------------------------------------------------------------------- #
def radial_reach_filter(background, image, t_p=0.08, agree_thresh=0.625, max_reach=32,
                        min_dirs=4, min_decided_fraction=0.01) -> dict:
    """Radial Reach Filter(RRF)。背景と現在の画像を、8 方向の reach の符号で比べる。

    背景 ``B`` の画素 ``p`` から方向 ``d_k`` へ 1, 2, … と進み、``|B(p + r d_k) - B(p)| >= t_p``
    になる最初の ``r`` を reach ``r_k``(``max_reach`` まで。画像の外に出たらその方向は
    無効)。符号 ``b_k = [B(p + r_k d_k) >= B(p)]``、現在の画像でも同じ位置の組で
    ``b'_k = [I(p + r_k d_k) >= I(p)]`` を作り、一致した方向の数を RRC とする。
    有効な方向のうち一致した割合が ``agree_thresh`` 未満の画素を前景にする
    (8 方向が全部有効なら、既定 0.625 は「一致 5 未満」)。

    現在の画像に狭義単調増加の明るさの変換を掛けても、結果は 1 ビットも変わらない。
    影(局所の掛け算)の内側も同じ理由で前景にならない。

    fail-closed: 有効な方向が ``min_dirs`` 未満の画素は判定しない(``decided`` が False、
    ``rrc`` が -1、前景にもしない)。判定できた画素が ``min_decided_fraction`` 未満なら
    ValueError(背景が平坦すぎて、変化を言えない)。

    返り: ``foreground``(bool)、``decided``(bool)、``rrc``(一致した方向の数、
    判定しない画素は -1)、``valid_dirs``、``agree_fraction``(判定しない画素は 1.0)、
    ``reach``((8, H, W)、無効は 0)、``decided_fraction``、``foreground_fraction``、
    ``refusal_margin``(判定できた割合 − ``min_decided_fraction``)。
    """
    op = "radial_reach_filter"
    B = _image(background, "background", op)
    I = _image(image, "image", op)
    if B.shape != I.shape:
        raise ValueError("%s: background %s and image %s differ in shape" % (op, B.shape, I.shape))
    tp = _nonneg(t_p, "t_p", op)
    if tp <= 0:
        raise ValueError("%s: t_p must be > 0 (the reach sign is undefined at equal brightness)" % op)
    at = _fraction(agree_thresh, "agree_thresh", op)
    L = _count(max_reach, "max_reach", op)
    md = _count(min_dirs, "min_dirs", op)
    if md > 8:
        raise ValueError("%s: min_dirs must be <= 8, got %r" % (op, min_dirs))
    mdf = _fraction(min_decided_fraction, "min_decided_fraction", op)
    H, W = B.shape
    Bp = np.pad(B, L, mode="constant", constant_values=np.nan)
    Ip = np.pad(I, L, mode="constant", constant_values=0.0)
    reach = np.zeros((8, H, W), np.int32)
    agree = np.zeros((H, W), np.int32)
    with np.errstate(invalid="ignore"):
        for k, (dy, dx) in enumerate(_DIRS8):
            found = np.zeros((H, W), bool)
            for r in range(1, L + 1):
                ys, xs = L + r * dy, L + r * dx
                Bs = Bp[ys:ys + H, xs:xs + W]
                hit = (~found) & (np.abs(Bs - B) >= tp)      # NaN(画像の外)は当たらない
                if hit.any():
                    Is = Ip[ys:ys + H, xs:xs + W]
                    b = Bs[hit] >= B[hit]
                    bp = Is[hit] >= I[hit]
                    agree[hit] += (b == bp)
                    reach[k][hit] = r
                    found |= hit
                if found.all():
                    break
    nvalid = (reach > 0).sum(axis=0).astype(np.int32)
    decided = nvalid >= md
    dfrac = float(decided.mean())
    if dfrac < mdf:
        raise ValueError(
            "%s: only %.4f of the pixels have >= %d directions with a reach (t_p=%g, max_reach=%d); "
            "the background is too flat to tell a change." % (op, dfrac, md, tp, L))
    frac = np.where(decided, agree / np.maximum(nvalid, 1), 1.0)
    fg = decided & (frac < at)
    return {
        "foreground": fg, "decided": decided,
        "rrc": np.where(decided, agree, -1).astype(np.int32),
        "valid_dirs": nvalid, "agree_fraction": frac, "reach": reach,
        "decided_fraction": dfrac, "foreground_fraction": float(fg.mean()),
        "t_p": tp, "agree_thresh": at,
        "decided_required": mdf, "refusal_margin": dfrac - mdf,
    }
