# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""グラフ・階層・閾値の定理でつくる分割: 2 値の graph cut(Boykov–Jolly 2001、最大フロー = 最小カット)、多ラベルの
α-expansion(Boykov–Veksler–Zabih 2001)、統計的領域併合 SRM(Nock–Nielsen 2004)、成分木(max-tree、Salembier 1998)と
属性開放、準平坦領域と α-tree(Soille 2008)、dynamics による階層分水嶺と ultrametric contour map、超画素 SNIC
(Achanta–Süsstrunk 2017)と quick shift(Vedaldi–Soatto 2008)と超画素の採点、閾値の 4 定理(Zack 1977 の三角法・
Ridler–Calvard 1978 の不動点・Kittler–Illingworth 1986 の最小誤差・Kapur 1985 の最大エントロピー)。

## 何を作るか

セグメンテーション拡充 第 3 陣「グラフ・階層・閾値」。**学習器は載せない**(numpy + scipy のルールベース)。どの op も
**定理か第 2 実装の門** を持つ:

1. ``graph_cut_binary`` —— E(x) = Σ_p D_p(x_p) + λ Σ_(p,q) w_pq [x_p ≠ x_q] (2 値、w ≥ 0 = submodular)を、s-t グラフの
   最小カットで **厳密に** 最小化する(Boykov–Jolly 2001 の Theorem 1 の構成。最小カットは ``scipy.sparse.csgraph.maximum_flow``
   の最大フローの残余グラフから取る)。門: (a) 最大フロー = 最小カット(Ford–Fulkerson の定理、整数の容量で厳密に一致)、
   (b) カットの値 + 定数 = エネルギー(構成の恒等式)、(c) 12 画素以下で総当たりの最小と一致、(d) λ = 0 で画素ごとの判定と一致。
2. ``alpha_expansion`` —— 多ラベル E(f) = Σ D_p(f_p) + λ Σ w_pq V(f_p, f_q)、V は計量(Potts か打ち切り線形)。各 α について
   「今のラベルのまま / α に替える」の 2 値の移動を graph cut で厳密に解き、**厳密に下がる時だけ** 受け入れる(論文の Fig. 3 と
   同じ)。門: (a) 受け入れの列でエネルギーは単調に下がる、(b) 移動の 2 値問題の最小 ≤ 今の値(今のラベルは移動の 1 つ)、
   (c) 小問題で総当たりの最小 E* に対し E ≤ 2c E*(BVZ 2001 の Theorem 6.1、c = V の最大 / 0 でない最小)。
3. ``statistical_region_merging`` —— 4 近傍の画素の組を |I_p − I_q| の昇順に並べ、併合の述語を満たす組だけを Union-Find で
   併合する(Nock–Nielsen 2004)。門: 2 値 + 雑音の世界で真の領域数、q を振った時の領域数の推移(**実測**、定理ではない)。
4. ``max_tree`` / ``area_opening_attr`` —— 成分木を Union-Find で作り(Najman–Couprie 2006 / Berger ら 2007 の型)、
   面積(または外接矩形の径)の属性で節を間引く(Salembier–Oliveras–Garrido 1998)。門: 開放は **冪等・反拡大・増加**(束論の定理:
   増加する属性の連結開放は代数的開放)、第 2 実装 = ``skimage.morphology.area_opening`` / ``diameter_opening`` と画素一致・``max_tree`` と節の数一致。
5. ``quasi_flat_zones`` / ``alpha_tree`` —— α-連結成分(隣の差が α 以下の経路で結べる画素の同値類)を、(a) 閾値を超える辺を
   落とした 4 近傍グラフの連結成分、(b) 最小全域木(Kruskal、scipy)の重み ≤ α の辺だけの連結成分、の 2 通りで出す。
   門: (a) = (b)(最小全域木の切断性質)、α を増やすと入れ子。
6. ``hierarchical_watershed`` / ``ultrametric_contour_map`` —— 地形 f の 4 近傍グラフに w_pq = max(f_p, f_q) を張り、Kruskal で
   最小全域森を作る(分水嶺カット = 極小を根とする最小全域森、Cousty–Bertrand–Najman–Couprie 2009)。2 つの盆地が峠 w で
   出会う時、浅い方の盆地の **dynamics**(= w − その盆地の底)を辺の重要度(saliency)にする(Najman–Schmitt 1996)。
   重要度 ≤ θ の辺で結んだ連結成分が階層の 1 段。門: 盆地の間の距離 d(x, y) = 「同じ領域になる最小の θ」は ultrametric
   (d(x, z) ≤ max(d(x, y), d(y, z)))、θ を上げると入れ子、θ の段で生き残る盆地の数 = dynamics > θ の極小の数(閉形式)。
7. ``snic_superpixels`` / ``quickshift`` / ``superpixel_quality`` —— SNIC = 格子の種から優先度つき待ち行列で 4 近傍に育て、
   重心をその場で更新(Achanta–Süsstrunk 2017 の Algorithm 1)。quick shift = Parzen 密度を見積もり、各点を「密度が上の最も
   近い点」に繋ぎ、長さ τ を超える枝を切る(Vedaldi–Soatto 2008 の式 (8))。門: SNIC の全ラベルが 4-連結(構成上の保証を
   数えて確かめる)、quick shift は τ を増やすと入れ子(同じ木から枝を切るだけ)、第 2 実装 = ``skimage.segmentation`` の
   ``slic`` / ``quickshift`` と境界の再現率・未分割誤差が近い。``superpixel_quality`` は境界の再現率(segeval の境界 F の
   recall)・補正つき未分割誤差 CUSE(Neubert–Protzel 2012、SNIC 論文の式 (2))・達成可能な分割精度 ASA を返す。
8. ``threshold_triangle`` / ``threshold_isodata`` / ``threshold_kittler`` / ``threshold_kapur`` —— 1 次元の閾値。門: isodata は
   不動点 t = (μ_low + μ_high)/2 を **画素の上で厳密に** 満たす(分割が変わらなくなるまで反復)、三角法と isodata は
   ``skimage.filters`` と 1 ビン以内、Kittler は 2 ガウスの混合で Bayes の最小誤差の閾値(2 次方程式の根)に近い、
   Kapur は総当たりの最大エントロピーと一致、Kittler / Kapur は SimpleITK と 1〜2 ビン以内(在れば)。

## 規約

* 画素の添字 (row, col) = (y, x)。4 近傍の辺は「右」(H, W − 1)と「下」(H − 1, W)の 2 枚に分けて持つ(segeval の境界と同じ)。
* ラベル画像は int64、**1 から** 振る(0 = マスクの外 / 背景)。2 値の結果は bool の ``mask``。
* 返り値はどれも dict。入力が不正なら ValueError(黙って直さない)。乱数は使わない(quick shift の同点は画素番号で決める)。
* graph cut の容量は scipy の最大フローが整数しか受けないので、実数のエネルギーを ``scale`` 倍して丸めた **整数の
  エネルギー** を厳密に最小化する。入力が整数なら scale = 1 で実数の最小そのもの。そうでなければ実数の最小との差は
  丸めの上界 ``quantization_bound`` 以下(返す)。

## 原論文で確認したこと / 要確認(self_reported)

* 確認(版面のテキストで): BVZ 2001 —— 計量の定義 (2)〜(4)、c = 最大 / 最小(0 でない V)、Theorem 6.1「expansion の局所解
  f̂ と大域解 f* について E(f̂) ≤ 2c E(f*)」、反復は「厳密に良いラベルが見つかれば成功、成功しない周回で止まる」。
  Boykov–Jolly 2001(ICCV)—— E(A) = λ R(A) + B(A)、B_pq ≥ 0、t-link と n-link の重みの表、K = 1 + max_p Σ_q B_pq、
  Theorem 1(最小カットが硬い制約の下で (1) を最小化)、B_pq ∝ exp(−(I_p − I_q)²/2σ²)/dist(p, q)。
  **注意**: 論文の λ は **領域項** に掛かる。ここでは平滑項に λ を掛ける(BVZ の形、λ = 1/λ_BJ と同値)。
  SNIC 2017 —— Algorithm 1(待ち行列・ラベル 0 の画素だけ受け入れ・重心のその場更新・4 / 8 近傍)、s = √(N/K)、
  CUSE の式 (2)。quick shift 2008 —— 「各点を密度が増える最も近い点へ」、木の枝を τ で切る、全ての τ の解を 1 度に得る。
* 要確認: SNIC の式 (1) は版面の抽出では d = √(|Δx|²/s + |Δc|²/m) と読めたが、SLIC(Achanta 2012)の距離は
  √((d_c/m)² + (d_s/S)²)。ここは **SLIC の 2 乗の形** を使う(抽出の崩れか原典の表記かは未確認)。
* 要確認(原論文を入手できず、記憶と広く使われる実装の式): SRM の述語 |R̄ − R̄'| ≤ √(b²(R) + b²(R'))、
  b(R) = g √(ln(|R_|R||/δ) / (2Q|R|))、|R_l| ≤ (l + 1)^min(l, g)、δ = 1/(6|I|²)。論文の確率的な誤差上界の定理の文言も未確認
  なので **門にしない**(q に対する領域数の推移は実測として返す)。
* 要確認(教科書の記憶): Kittler–Illingworth の基準 J(t) = 1 + 2(P1 ln σ1 + P2 ln σ2) − 2(P1 ln P1 + P2 ln P2)、
  Kapur の H(t) = H_低 + H_高(各クラスで正規化した確率のエントロピー)、Zack 1977 の三角法の作図(山頂と裾の端を結ぶ線から
  最も遠いビン)。三角法の端点の高さ 0・符号つき距離・裾の長い側を選ぶ規約は skimage / ImageJ と同じにした(原典未確認)。
* 要確認: 分水嶺カット = 最小全域森(Cousty ら 2009)・dynamics の階層 = ultrametric(Najman 2011)の定理の文言。ここでは
  門を **数えて** 確かめる(ultrametric の三角不等式を盆地の全 3 つ組で、生き残る盆地の数を閉形式の地形で)。
* 冪等・反拡大・増加は「増加する基準の連結な属性開放は代数的開放」(Breen–Jones 1996 / Salembier ら 1998)に依る(記憶)。
"""
from __future__ import annotations

import heapq
import math
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy import ndimage as ndi
from scipy import sparse
from scipy.sparse import csgraph

import segeval

__all__ = [
    "MAX_PIXELS", "MAX_BRUTE_PIXELS",
    "graph_cut_binary", "alpha_expansion", "statistical_region_merging", "max_tree", "area_opening_attr",
    "quasi_flat_zones", "alpha_tree", "hierarchical_watershed", "ultrametric_contour_map",
    "snic_superpixels", "quickshift", "superpixel_quality",
    "threshold_triangle", "threshold_isodata", "threshold_kittler", "threshold_kapur",
]

#: 1 枚の画像の画素数の上限(Python の Union-Find / 優先度つき待ち行列を回すので、大き過ぎる入力は先に断る)。
MAX_PIXELS = 1_000_000
#: 総当たりの検算を許す画素数の上限(テスト用の道具 ``_brute_force_*`` が使う)。
MAX_BRUTE_PIXELS = 14
#: scipy の最大フローは int32 の容量を取る。容量の総和をこれ以下に抑えて桁あふれを防ぐ。
_CAP_LIMIT = 2 ** 30


# ───────────────────────────── 入力の検査 ─────────────────────────────
def _image(x, name: str, op: str, min_side: int = 1) -> np.ndarray:
    """2-D の有限な実数画像に揃える(bool / 整数は float64 に)。"""
    if isinstance(x, (str, bytes, dict)) or np.ma.is_masked(x):
        raise ValueError("%s: %s must be a 2-D real image" % (op, name))
    a = np.asarray(x)
    if a.dtype.kind not in "biuf":
        raise ValueError("%s: %s has dtype %s — must be real" % (op, name, a.dtype))
    a = a.astype(np.float64)
    if a.ndim != 2 or a.shape[0] < min_side or a.shape[1] < min_side:
        raise ValueError("%s: %s must be a 2-D image of at least %d x %d, got shape %r" % (op, name, min_side, min_side, a.shape))
    if a.size > MAX_PIXELS:
        raise ValueError("%s: %s has %d pixels > MAX_PIXELS=%d" % (op, name, a.size, MAX_PIXELS))
    if not np.isfinite(a).all():
        raise ValueError("%s: %s has non-finite values" % (op, name))
    return a


def _num(v, name: str, op: str, lo: float = -math.inf, hi: float = math.inf, lo_open: bool = False) -> float:
    if isinstance(v, bool):
        raise ValueError("%s: %s must be a number (got bool)" % (op, name))
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a number (got %r)" % (op, name, v)) from None
    if not math.isfinite(f) or f < lo or f > hi or (lo_open and f == lo):
        raise ValueError("%s: %s must be finite and in %s%g, %g] (got %r)" % (op, name, "(" if lo_open else "[", lo, hi, v))
    return f


def _int(v, name: str, op: str, lo: int = 1, hi: int = 10 ** 9) -> int:
    if isinstance(v, bool) or not isinstance(v, (int, np.integer)):
        raise ValueError("%s: %s must be an integer (got %r)" % (op, name, v))
    k = int(v)
    if k < lo or k > hi:
        raise ValueError("%s: %s must be in [%d, %d] (got %d)" % (op, name, lo, hi, k))
    return k


def _conn(c, op: str) -> int:
    if isinstance(c, bool) or c not in (4, 8):
        raise ValueError("%s: connectivity must be 4 or 8 (got %r)" % (op, c))
    return int(c)


def _mask_opt(m, shape, op: str, name: str = "mask") -> Optional[np.ndarray]:
    if m is None:
        return None
    a = np.asarray(m)
    if a.dtype.kind not in "biuf" or a.shape != tuple(shape):
        raise ValueError("%s: %s must be a 2-D 0/1 array of shape %r" % (op, name, tuple(shape)))
    if np.count_nonzero((a != 0) & (a != 1)) > 0:
        raise ValueError("%s: %s must hold only 0 and 1" % (op, name))
    a = a != 0
    if np.count_nonzero(a) == 0:
        raise ValueError("%s: %s is empty" % (op, name))
    return a


def _labels_in(x, name: str, op: str, shape=None) -> np.ndarray:
    a = np.asarray(x)
    if a.dtype.kind == "b":
        a = a.astype(np.int64)
    if a.dtype.kind == "f":
        if not np.isfinite(a).all() or np.count_nonzero(a != np.round(a)) > 0:
            raise ValueError("%s: %s must hold integers" % (op, name))
        a = a.astype(np.int64)
    if a.dtype.kind not in "iu" or a.ndim != 2:
        raise ValueError("%s: %s must be a 2-D integer label image" % (op, name))
    if a.size > 0 and int(a.min()) < 0:
        raise ValueError("%s: %s has negative labels" % (op, name))
    if shape is not None and a.shape != tuple(shape):
        raise ValueError("%s: %s must have shape %r, got %r" % (op, name, tuple(shape), a.shape))
    return a.astype(np.int64)


# ───────────────────────────── 格子の辺 ─────────────────────────────
def _grid_edges(h: int, w: int, conn: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """格子の無向の辺 (i, j, 距離)。4 近傍 = 右・下、8 近傍 = さらに右下・左下(距離 √2)。i < j の順。"""
    idx = np.arange(h * w).reshape(h, w)
    ii = [idx[:, :-1].ravel(), idx[:-1, :].ravel()]
    jj = [idx[:, 1:].ravel(), idx[1:, :].ravel()]
    dd = [np.ones(h * (w - 1)), np.ones((h - 1) * w)]
    if conn == 8:
        ii += [idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel()]
        jj += [idx[1:, 1:].ravel(), idx[1:, :-1].ravel()]
        dd += [np.full((h - 1) * (w - 1), math.sqrt(2.0))] * 2
    return (np.concatenate(ii).astype(np.int64), np.concatenate(jj).astype(np.int64), np.concatenate(dd))


def _relabel(lab: np.ndarray, keep_zero: bool = False) -> np.ndarray:
    """ラベルを **ラスタ順の初出** で 1..k に振り直す(同じ分割なら同じ配列になる = 正準形)。keep_zero なら 0 は 0 のまま。"""
    flat = lab.ravel()
    u, first, inv = np.unique(flat, return_index=True, return_inverse=True)
    rank = np.empty(u.size, np.int64)
    if keep_zero and u.size > 0 and u[0] == 0:
        rank[0] = 0
        order = np.argsort(first[1:], kind="stable")
        rank[1:][order] = np.arange(1, u.size)
    else:
        order = np.argsort(first, kind="stable")
        rank[order] = np.arange(1, u.size + 1)
    return rank[inv].reshape(lab.shape)


def _components(n: int, i: np.ndarray, j: np.ndarray) -> np.ndarray:
    """n 頂点の無向グラフ(辺 i–j)の連結成分の番号(0..k−1)。"""
    g = sparse.coo_matrix((np.ones(i.size, np.int8), (i, j)), shape=(n, n)).tocsr()
    return csgraph.connected_components(g, directed=False)[1].astype(np.int64)


def _is_nested(fine: np.ndarray, coarse: np.ndarray) -> bool:
    """細かい分割の各領域が粗い分割のちょうど 1 領域に入るか(入れ子)。"""
    f = fine.ravel()
    c = coarse.ravel()
    pairs = np.unique(np.stack([f, c], axis=1), axis=0)
    return int(np.unique(pairs[:, 0]).size) == int(pairs.shape[0])


# ───────────────────────────── 1. 最小カット(共通の芯) ─────────────────────────────
def _mincut(u0: np.ndarray, u1: np.ndarray, pa: np.ndarray, pb: np.ndarray, pw: np.ndarray, op: str) -> Dict[str, object]:
    """Σ_p (y_p = 0 なら u0_p、1 なら u1_p) + Σ_k pw_k [y_(pa_k) = 1 かつ y_(pb_k) = 0] を最小化する(pw ≥ 0)。

    y = 1 ⇔ 頂点が源 S の側。S→p の容量 u0_p(p が T 側 = y_p = 0 で切れる)、p→T の容量 u1_p、pa→pb の容量 pw。
    単項は画素ごとに min(u0, u1) を定数へ移して非負にする。容量は整数(scale 倍して丸め、整数ならそのまま)。
    返す: y(bool)・整数のカットの値・最大フローの値・定数・scale・整数か。
    """
    n = int(u0.size)
    if np.count_nonzero(pw < 0) > 0:
        raise ValueError("%s: pairwise weights must be non-negative (submodular)" % op)
    c = np.minimum(u0, u1)
    a0 = u0 - c
    a1 = u1 - c
    const = float(c.sum())
    total = float(a0.sum() + a1.sum() + pw.sum())
    is_int = bool(np.all(a0 == np.round(a0)) and np.all(a1 == np.round(a1)) and np.all(pw == np.round(pw)))
    if is_int and total <= _CAP_LIMIT:
        scale = 1.0
    else:
        scale = (_CAP_LIMIT / total) if total > 0 else 1.0
        is_int = False
    q0 = np.round(a0 * scale).astype(np.int64)
    q1 = np.round(a1 * scale).astype(np.int64)
    qw = np.round(pw * scale).astype(np.int64)
    S, T = n, n + 1
    pix = np.arange(n, dtype=np.int64)
    s0 = q0 > 0
    s1 = q1 > 0
    sw = qw > 0
    rows = np.concatenate([np.full(int(s0.sum()), S), pix[s1], pa[sw]])
    cols = np.concatenate([pix[s0], np.full(int(s1.sum()), T), pb[sw]])
    caps = np.concatenate([q0[s0], q1[s1], qw[sw]])
    C = sparse.coo_matrix((caps, (rows, cols)), shape=(n + 2, n + 2)).tocsr()
    C.sum_duplicates()
    if C.nnz > 0 and int(C.data.max()) >= 2 ** 31 - 1:
        raise ValueError("%s: a capacity overflows int32 after scaling" % op)
    C = C.astype(np.int32)
    res = csgraph.maximum_flow(C, S, T, method="dinic")
    F = res.flow.tocsr().astype(np.int64)
    R = (C.astype(np.int64) - F).tocsr()
    R.eliminate_zeros()
    R.data = (R.data > 0).astype(np.int8)
    R.eliminate_zeros()
    reach = csgraph.breadth_first_order(R, S, directed=True, return_predecessors=False)
    side = np.zeros(n + 2, bool)
    side[reach] = True
    if side[T]:
        raise ValueError("%s: internal error — sink reachable after max-flow" % op)
    y = side[:n]
    Ccoo = C.tocoo()
    cut_mask = side[Ccoo.row] & ~side[Ccoo.col]
    cut_int = int(Ccoo.data[cut_mask].astype(np.int64).sum())
    return {"y": y, "cut_int": cut_int, "flow_int": int(res.flow_value), "const": const, "scale": float(scale),
            "integer": is_int, "n_terms": int(n + pa.size)}


def _energy_binary(u0, u1, pa, pb, pw, y) -> float:
    return float(np.where(y, u1, u0).sum() + pw[y[pa] & ~y[pb]].sum())


def _two_means(a: np.ndarray) -> Tuple[float, float]:
    """isodata の不動点で 2 群に割ったときの低い群・高い群の平均(どちらかが空なら最小・最大)。"""
    if float(a.max()) <= float(a.min()):
        return float(a.min()), float(a.max())
    t = threshold_isodata(a.reshape(1, -1))["threshold"]
    lo = a[a <= t]
    hi = a[a > t]
    return (float(lo.mean()) if lo.size else float(a.min()), float(hi.mean()) if hi.size else float(a.max()))


def graph_cut_binary(image, *, lam: float = 1.0, mu_bg: Optional[float] = None, mu_fg: Optional[float] = None,
                     contrast_sigma: Optional[float] = None, seeds=None, connectivity: int = 4) -> Dict[str, object]:
    """2 値の graph cut(Boykov–Jolly 2001): E = Σ_p D_p(x_p) + λ Σ w_pq [x_p ≠ x_q] を最大フロー / 最小カットで厳密に最小化。

    データ項は D_p(0) = (I_p − μ_bg)²、D_p(1) = (I_p − μ_fg)²(μ を省くと isodata の 2 群の平均)。辺の重みは
    w_pq = exp(−(I_p − I_q)²/(2σ²)) / dist(p, q)(``contrast_sigma`` = σ、省くと 1/dist = Potts)。``seeds`` は labels2d で
    1 = 背景の種、2 = 物体の種(Boykov–Jolly の K = 1 + max_p Σ_q λ w_pq で硬く縛る、エネルギーには数えない)。
    返す: ``mask``(物体 = True)、``energy`` = data + smooth、``cut_value`` / ``flow_value``(実数に戻した値 = 整数の値 / scale +
    定数)と ``cut_value_int`` / ``flow_value_int``(最大フロー = 最小カットの門)、``quantization_bound``(整数化による実数の
    最小との差の上界、整数の入力なら 0)。
    """
    op = "graph_cut_binary"
    img = _image(image, "image", op)
    lam = _num(lam, "lam", op, 0.0)
    conn = _conn(connectivity, op)
    h, w = img.shape
    a = img.ravel()
    if mu_bg is None or mu_fg is None:
        m0, m1 = _two_means(a)
        mu_bg = m0 if mu_bg is None else mu_bg
        mu_fg = m1 if mu_fg is None else mu_fg
    mu_bg = _num(mu_bg, "mu_bg", op)
    mu_fg = _num(mu_fg, "mu_fg", op)
    u0 = (a - mu_bg) ** 2
    u1 = (a - mu_fg) ** 2
    ei, ej, ed = _grid_edges(h, w, conn)
    if contrast_sigma is None:
        wt = 1.0 / ed
    else:
        sg = _num(contrast_sigma, "contrast_sigma", op, 0.0, lo_open=True)
        wt = np.exp(-(a[ei] - a[ej]) ** 2 / (2.0 * sg * sg)) / ed
    pw = lam * wt
    data_u0, data_u1 = u0.copy(), u1.copy()
    n_seed = 0
    if seeds is not None:
        sd = _labels_in(seeds, "seeds", op, img.shape).ravel()
        if int(sd.max()) > 2:
            raise ValueError("%s: seeds must hold 0 (free), 1 (background) or 2 (object)" % op)
        deg = np.bincount(ei, weights=pw, minlength=a.size) + np.bincount(ej, weights=pw, minlength=a.size)
        K = 1.0 + float(deg.max()) + float(np.max(np.abs(u0 - u1)))
        u0 = u0 + np.where(sd == 2, K, 0.0)
        u1 = u1 + np.where(sd == 1, K, 0.0)
        n_seed = int(np.count_nonzero(sd))
    pa = np.concatenate([ei, ej])
    pb = np.concatenate([ej, ei])
    pww = np.concatenate([pw, pw])
    r = _mincut(u0, u1, pa, pb, pww, op)
    y = r["y"]
    data_e = float(np.where(y, data_u1, data_u0).sum())
    smooth_e = float(pw[y[ei] != y[ej]].sum())
    qb = 0.0 if r["integer"] else float(r["n_terms"]) / r["scale"]
    return {"mask": y.reshape(h, w), "energy": data_e + smooth_e, "data_energy": data_e, "smooth_energy": smooth_e,
            "cut_value": r["cut_int"] / r["scale"] + r["const"], "flow_value": r["flow_int"] / r["scale"] + r["const"],
            "cut_value_int": r["cut_int"], "flow_value_int": r["flow_int"], "constant": r["const"], "scale": r["scale"],
            "integer_exact": r["integer"], "quantization_bound": qb, "mu_bg": mu_bg, "mu_fg": mu_fg, "lam": lam,
            "n_seeds": n_seed, "n_edges": int(ei.size), "connectivity": conn}


def _brute_force_binary(image, *, lam, mu_bg, mu_fg, connectivity=4, contrast_sigma=None) -> Dict[str, object]:
    """総当たりの最小(テストの検算用、画素数 ≤ MAX_BRUTE_PIXELS)。graph_cut_binary と同じエネルギー。"""
    img = _image(image, "image", "_brute_force_binary")
    if img.size > MAX_BRUTE_PIXELS:
        raise ValueError("_brute_force_binary: too many pixels")
    a = img.ravel()
    ei, ej, ed = _grid_edges(*img.shape, connectivity)
    wt = 1.0 / ed if contrast_sigma is None else np.exp(-(a[ei] - a[ej]) ** 2 / (2.0 * contrast_sigma ** 2)) / ed
    n = a.size
    codes = np.arange(2 ** n)
    Y = ((codes[:, None] >> np.arange(n)[None, :]) & 1).astype(bool)
    E = np.where(Y, (a - mu_fg) ** 2, (a - mu_bg) ** 2).sum(axis=1) + lam * ((Y[:, ei] != Y[:, ej]) * wt).sum(axis=1)
    k = int(np.argmin(E))
    return {"energy": float(E[k]), "mask": Y[k].reshape(img.shape), "n_min": int(np.count_nonzero(E <= E[k] + 1e-12))}


# ───────────────────────────── 2. α-expansion ─────────────────────────────
def _vmat(L: int, kind: str, trunc: float, op: str) -> np.ndarray:
    lv = np.arange(L, dtype=np.float64)
    if kind == "potts":
        V = (lv[:, None] != lv[None, :]).astype(np.float64)
    elif kind == "truncated_linear":
        V = np.minimum(np.abs(lv[:, None] - lv[None, :]), trunc)
    else:
        raise ValueError("%s: pairwise must be 'potts' or 'truncated_linear' (got %r)" % (op, kind))
    return V


def _multi_energy(D: np.ndarray, V: np.ndarray, ei, ej, wt, lam, f) -> float:
    n = f.size
    return float(D[np.arange(n), f].sum() + lam * (wt * V[f[ei], f[ej]]).sum())


def alpha_expansion(image, means: Optional[Sequence[float]] = None, *, lam: float = 1.0, pairwise: str = "potts", truncation: float = 2.0,
                    connectivity: int = 4, max_cycles: int = 10, init=None) -> Dict[str, object]:
    """多ラベルの α-expansion(Boykov–Veksler–Zabih 2001): E(f) = Σ (I_p − μ_(f_p))² + λ Σ w_pq V(f_p, f_q)、V は計量。

    ``means`` = 各ラベルの平均 μ_1..μ_L(L ≥ 2。省くと画素の値の 1/6・1/2・5/6 分位の 3 ラベル)。V は ``"potts"``([α ≠ β]、c = 1)か ``"truncated_linear"``
    (min(|α − β|, T)、T ≥ 1 なら計量、c = min(L − 1, T))。1 周 = α = 1..L の expansion を順に。各移動は 2 値の graph cut で
    厳密に解き、**エネルギーが厳密に下がる時だけ** 受け入れる。1 周で 1 度も受け入れなければ止まる(論文と同じ)。
    返す: ``labels``(1..L)、``energy``、``energies``(受け入れの列、単調減少)、``move_minima``(各移動の 2 値問題の最小、
    今の値以下 = 門)、``c``、``bound_factor`` = 2c(Theorem 6.1: E(f̂) ≤ 2c E(f*))。
    """
    op = "alpha_expansion"
    img = _image(image, "image", op)
    if means is None:
        means = np.quantile(img, [1.0 / 6.0, 0.5, 5.0 / 6.0])
    mu = np.asarray(means, dtype=np.float64).ravel()
    if mu.size < 2 or not np.isfinite(mu).all():
        raise ValueError("%s: means must hold at least 2 finite values" % op)
    L = int(mu.size)
    lam = _num(lam, "lam", op, 0.0)
    conn = _conn(connectivity, op)
    mc = _int(max_cycles, "max_cycles", op, 1, 1000)
    if pairwise == "truncated_linear":
        T = _num(truncation, "truncation", op, 1.0)
    else:
        T = 1.0
    V = _vmat(L, pairwise, T, op)
    nz = V[V > 0]
    c = float(nz.max() / nz.min())
    h, w = img.shape
    a = img.ravel()
    n = a.size
    D = (a[:, None] - mu[None, :]) ** 2
    ei, ej, ed = _grid_edges(h, w, conn)
    wt = 1.0 / ed
    if init is None:
        f = np.argmin(D, axis=1).astype(np.int64)
    else:
        f = _labels_in(init, "init", op, img.shape).ravel() - 1
        if int(f.min()) < 0 or int(f.max()) >= L:
            raise ValueError("%s: init must hold labels 1..%d" % (op, L))
    E = _multi_energy(D, V, ei, ej, wt, lam, f)
    energies = [E]
    move_min: List[Tuple[float, float]] = []
    n_moves = 0
    n_acc = 0
    cycles = 0
    pix = np.arange(n)
    for cyc in range(mc):
        cycles += 1
        changed = False
        for al in range(L):
            n_moves += 1
            u0 = D[pix, f].copy()
            u1 = D[:, al].copy()
            A = lam * wt * V[f[ei], f[ej]]
            B = lam * wt * V[f[ei], al]          # y_i = 0(据え置き)、y_j = 1(α)
            Cc = lam * wt * V[al, f[ej]]         # y_i = 1、y_j = 0
            # E_ij = A + (C − A) y_i + (0 − C) y_j + (B + C − A)(1 − y_i) y_j
            const = float(A.sum())
            np.add.at(u1, ei, Cc - A)
            np.add.at(u1, ej, -Cc)
            pwt = B + Cc - A                     # ≥ 0 は V の三角不等式(計量)
            if np.count_nonzero(pwt < -1e-9 * max(1.0, lam)) > 0:
                raise ValueError("%s: pairwise term is not a metric (expansion move not submodular)" % op)
            pwt = np.maximum(pwt, 0.0)
            r = _mincut(u0, u1, ej, ei, pwt, op)
            y = r["y"]
            cand = np.where(y, al, f)
            Ec = _multi_energy(D, V, ei, ej, wt, lam, cand)
            mmin = _energy_binary(u0, u1, ej, ei, pwt, y) + const
            move_min.append((mmin, E))
            if Ec < E - 1e-12 * max(1.0, abs(E)):
                f = cand
                E = Ec
                energies.append(E)
                n_acc += 1
                changed = True
        if not changed:
            break
    return {"labels": (f + 1).reshape(h, w), "energy": E, "energies": np.array(energies),
            "move_minima": np.array(move_min), "n_moves": n_moves, "n_accepted": n_acc, "n_cycles": cycles,
            "c": c, "bound_factor": 2.0 * c, "pairwise": pairwise, "lam": lam, "means": mu}


def _brute_force_multi(image, means, *, lam, pairwise="potts", truncation=2.0, connectivity=4) -> Dict[str, object]:
    """多ラベルの総当たり(検算用、L^n ≤ 2e6)。alpha_expansion と同じエネルギー。"""
    img = _image(image, "image", "_brute_force_multi")
    mu = np.asarray(means, np.float64)
    L, n = mu.size, img.size
    if L ** n > 2_000_000:
        raise ValueError("_brute_force_multi: too large")
    V = _vmat(L, pairwise, truncation, "_brute_force_multi")
    a = img.ravel()
    D = (a[:, None] - mu[None, :]) ** 2
    ei, ej, ed = _grid_edges(*img.shape, connectivity)
    wt = 1.0 / ed
    codes = np.arange(L ** n)
    Fm = (codes[:, None] // (L ** np.arange(n))[None, :]) % L
    E = D[np.arange(n)[None, :], Fm].sum(axis=1) + lam * (wt[None, :] * V[Fm[:, ei], Fm[:, ej]]).sum(axis=1)
    k = int(np.argmin(E))
    return {"energy": float(E[k]), "labels": (Fm[k] + 1).reshape(img.shape)}


# ───────────────────────────── 3. SRM ─────────────────────────────
class _UF:
    """Union-Find(経路圧縮 + 大きさ合わせ)。"""

    def __init__(self, n: int):
        self.p = list(range(n))
        self.sz = [1] * n

    def find(self, x: int) -> int:
        p = self.p
        r = x
        while p[r] != r:
            r = p[r]
        while p[x] != r:
            p[x], x = r, p[x]
        return r


def statistical_region_merging(image, *, q: float = 32.0, g: int = 256, value_range=(0.0, 1.0),
                               connectivity: int = 4) -> Dict[str, object]:
    """統計的領域併合 SRM(Nock–Nielsen 2004): 隣の画素の組を |I_p − I_q| の昇順に処理し、述語 P(R, R') が真なら併合。

    画素の値は ``value_range`` を [0, g − 1] に線形に写して使う(範囲の外の値は ValueError)。
    P(R, R') ⇔ |R̄ − R̄'| ≤ √(b²(R) + b²(R'))、b(R) = g √(ln(|R_|R||/δ) / (2Q|R|))、ln|R_l| = min(l, g) ln(l + 1)、
    δ = 1/(6|I|²)(述語の係数は **要確認**、モジュールの説明参照)。Q(``q``)が大きいほど b が小さく、併合を渋る(細かい)。
    返す: ``labels``(1..k)、``n_regions``、``means``(領域ごとの平均、元の値の尺度)、``n_merges``、``q``。
    """
    op = "statistical_region_merging"
    img = _image(image, "image", op)
    Q = _num(q, "q", op, 0.0, lo_open=True)
    g_ = _int(g, "g", op, 2, 65536)
    conn = _conn(connectivity, op)
    try:
        lo, hi = float(value_range[0]), float(value_range[1])
    except (TypeError, IndexError, ValueError):
        raise ValueError("%s: value_range must be (lo, hi)" % op) from None
    if not (math.isfinite(lo) and math.isfinite(hi) and hi > lo):
        raise ValueError("%s: value_range must satisfy lo < hi" % op)
    if float(img.min()) < lo or float(img.max()) > hi:
        raise ValueError("%s: image values must lie in value_range %r" % (op, (lo, hi)))
    h, w = img.shape
    v = (img.ravel() - lo) / (hi - lo) * (g_ - 1)
    n = v.size
    ei, ej, _ = _grid_edges(h, w, conn)
    order = np.argsort(np.abs(v[ei] - v[ej]), kind="stable")
    logdelta = math.log(6.0 * n * n)
    uf = _UF(n)
    ssum = v.tolist()
    cnt = [1] * n
    n_merge = 0
    I = ei[order].tolist()
    J = ej[order].tolist()
    assert len(I) > 0
    for p, qq in zip(I, J):
        rp = uf.find(p)
        rq = uf.find(qq)
        if rp == rq:
            continue
        a_, b_ = cnt[rp], cnt[rq]
        ba2 = g_ * g_ * (min(a_, g_) * math.log(1.0 + a_) + logdelta) / (2.0 * Q * a_)
        bb2 = g_ * g_ * (min(b_, g_) * math.log(1.0 + b_) + logdelta) / (2.0 * Q * b_)
        d = ssum[rp] / a_ - ssum[rq] / b_
        if d * d <= ba2 + bb2:
            if a_ < b_:
                rp, rq = rq, rp
            uf.p[rq] = rp
            cnt[rp] += cnt[rq]
            ssum[rp] += ssum[rq]
            n_merge += 1
    roots = np.array([uf.find(i) for i in range(n)], dtype=np.int64)
    lab = _relabel(roots.reshape(h, w))
    k = int(lab.max())
    means = ndi.mean(img, lab, index=np.arange(1, k + 1))
    return {"labels": lab, "n_regions": k, "means": np.asarray(means, np.float64), "n_merges": n_merge, "q": Q, "g": g_}


# ───────────────────────────── 4. 成分木と属性開放 ─────────────────────────────
def max_tree(image, *, connectivity: int = 4) -> Dict[str, object]:
    """成分木(max-tree): 上位集合 {f ≥ h} の連結成分の木を Union-Find で作る(画素を値の降順に処理)。

    返す: ``parent``(H, W の平らな添字。根は自分自身)、``order``(値の昇順、親は子より前)、``canonical``(節の代表画素の印 =
    根か、親と値が違う画素)、``area``(代表画素での成分の画素数)、``diameter``(成分の外接矩形の長い辺 = skimage の diameter と同じ)、
    ``height``(成分の中の最大値 − 成分の値、参考)、``n_nodes``。
    """
    op = "max_tree"
    img = _image(image, "image", op)
    conn = _conn(connectivity, op)
    h, w = img.shape
    f = img.ravel()
    n = f.size
    order = np.argsort(f, kind="stable")
    ei, ej, _ = _grid_edges(h, w, conn)
    nbr: List[List[int]] = [[] for _ in range(n)]
    for a_, b_ in zip(ei.tolist(), ej.tolist()):
        nbr[a_].append(b_)
        nbr[b_].append(a_)
    parent = list(range(n))
    zpar = [-1] * n
    ordl = order.tolist()
    assert len(ordl) > 0
    for p in reversed(ordl):
        parent[p] = p
        zpar[p] = p
        for q in nbr[p]:
            if zpar[q] < 0:
                continue
            r = q
            while zpar[r] != r:
                r = zpar[r]
            x = q
            while zpar[x] != r:
                zpar[x], x = r, zpar[x]
            if r != p:
                parent[r] = p
                zpar[r] = p
    fl = f.tolist()
    for p in ordl:
        qq = parent[p]
        if fl[parent[qq]] == fl[qq]:
            parent[p] = parent[qq]
    par = np.array(parent, dtype=np.int64)
    root = ordl[0]
    canon = (f[par] != f) | (np.arange(n) == root)
    area = np.ones(n, np.int64)
    hmax = f.copy()
    rr, cc = np.divmod(np.arange(n), w)
    r0, r1, c0, c1 = rr.copy(), rr.copy(), cc.copy(), cc.copy()
    for p in reversed(ordl):
        if p == root:
            continue
        qq = parent[p]
        area[qq] += area[p]
        if hmax[p] > hmax[qq]:
            hmax[qq] = hmax[p]
        if r0[p] < r0[qq]:
            r0[qq] = r0[p]
        if r1[p] > r1[qq]:
            r1[qq] = r1[p]
        if c0[p] < c0[qq]:
            c0[qq] = c0[p]
        if c1[p] > c1[qq]:
            c1[qq] = c1[p]
    diam = np.maximum(r1 - r0 + 1, c1 - c0 + 1)
    return {"parent": par.reshape(h, w), "order": order, "canonical": canon.reshape(h, w), "area": area.reshape(h, w),
            "height": (hmax - f).reshape(h, w), "diameter": diam.reshape(h, w), "n_nodes": int(np.count_nonzero(canon)), "root": int(root),
            "connectivity": conn}


def area_opening_attr(image, threshold: float = 16.0, *, attribute: str = "area", connectivity: int = 4) -> Dict[str, object]:
    """属性開放(Salembier ら 1998): 成分木の節のうち属性 < ``threshold`` を消し、各画素を「属性 ≥ 閾値の最も近い祖先」の値にする。

    ``attribute`` = ``"area"``(画素数、skimage の area_opening と同じ「面積が閾値未満の明るい構造を消す」)か ``"diameter"``
    (外接矩形の長い辺、skimage の diameter_opening)。どちらも **2 値の集合の** 増加する属性なので、結果は代数的開放 =
    冪等・反拡大・増加。成分の中の最大値に依る「高さ」は集合の属性でなく(h-maxima と同じく)冪等にならないので載せない
    (実測で 2 回目に値が変わった)。
    返す: ``image``(開放の結果)、``n_nodes_kept`` / ``n_nodes``、``removed``(値が下がった画素の数)。
    """
    op = "area_opening_attr"
    img = _image(image, "image", op)
    thr = _num(threshold, "threshold", op, 0.0)
    if attribute not in ("area", "diameter"):
        raise ValueError("%s: attribute must be 'area' or 'diameter' (got %r)" % (op, attribute))
    t = max_tree(img, connectivity=connectivity)
    par = t["parent"].ravel()
    canon = t["canonical"].ravel()
    attr = t[attribute].ravel().astype(np.float64)
    f = img.ravel()
    out = np.empty_like(f)
    root = t["root"]
    ordl = t["order"].tolist()
    assert len(ordl) > 0
    for p in ordl:
        if p == root:
            out[p] = f[p]
        elif canon[p]:
            out[p] = f[p] if attr[p] >= thr else out[par[p]]
        else:
            out[p] = out[par[p]]
    kept = int(np.count_nonzero(canon & (attr >= thr))) + (0 if attr[root] >= thr else 1)
    return {"image": out.reshape(img.shape), "n_nodes": t["n_nodes"], "n_nodes_kept": kept,
            "removed": int(np.count_nonzero(out < f)), "attribute": attribute, "threshold": thr}


# ───────────────────────────── 5. 準平坦領域と α-tree ─────────────────────────────
def quasi_flat_zones(image, alpha: float = 0.05, *, connectivity: int = 4) -> Dict[str, object]:
    """α-準平坦領域(Soille 2008): |f_p − f_q| ≤ α の隣接辺だけで結んだ連結成分。返す: ``labels``(1..k)、``n_zones``。"""
    op = "quasi_flat_zones"
    img = _image(image, "image", op)
    al = _num(alpha, "alpha", op, 0.0)
    conn = _conn(connectivity, op)
    h, w = img.shape
    f = img.ravel()
    ei, ej, _ = _grid_edges(h, w, conn)
    keep = np.abs(f[ei] - f[ej]) <= al
    lab = _components(f.size, ei[keep], ej[keep])
    lab = _relabel(lab.reshape(h, w))
    return {"labels": lab, "n_zones": int(lab.max()), "alpha": al}


def alpha_tree(image, alphas: Sequence[float] = (0.0,), *, connectivity: int = 4) -> Dict[str, object]:
    """α-tree: 隣の差を重みにした格子の最小全域木(scipy の Kruskal)を作り、重み ≤ α の木の辺だけで α ごとの分割を出す。

    scipy は重み 0 の辺を「辺が無い」と読むので、重み 0 の辺だけを「正の重みの最小の半分」に置き換えてから木を作る
    (辺の順序は変わらない = 最小全域木は同じ)。**全辺に 1 を足す手は使わない**: 0.3 の差が浮動小数で 0.29999999999999993 と
    0.30000000000000004 に割れている時、+1 の丸めで 2 つが同点になり、木が重い方を選んで α = 0.3 の切断がずれた(実測、
    テスト test_quasi_flat_zones_equal_mst_cut)。木の辺の重みは添字から |f_p − f_q| を計算し直す。
    返す: ``labels``(α ごとの (H, W) を積んだ (A, H, W))、``n_zones``、``mst_i`` / ``mst_j`` / ``mst_w``、``merge_levels``
    (木の辺の重みの昇順 = 併合の高さ)、``nested``(α の昇順で入れ子か)。
    """
    op = "alpha_tree"
    img = _image(image, "image", op)
    conn = _conn(connectivity, op)
    al = np.asarray(alphas, dtype=np.float64).ravel()
    if al.size == 0 or not np.isfinite(al).all() or np.count_nonzero(al < 0) > 0:
        raise ValueError("%s: alphas must be non-empty, finite and >= 0" % op)
    h, w = img.shape
    f = img.ravel()
    n = f.size
    ei, ej, _ = _grid_edges(h, w, conn)
    wt = np.abs(f[ei] - f[ej])
    if n == 1:
        mi = mj = np.zeros(0, np.int64)
    else:
        posw = wt[wt > 0]
        eps = 0.5 * float(posw.min()) if posw.size else 1.0
        G = sparse.coo_matrix((np.where(wt > 0, wt, eps), (ei, ej)), shape=(n, n)).tocsr()
        Tm = csgraph.minimum_spanning_tree(G).tocoo()
        mi, mj = Tm.row.astype(np.int64), Tm.col.astype(np.int64)
    mw = np.abs(f[mi] - f[mj])
    labs = []
    nz = []
    assert al.size > 0
    for a_ in al.tolist():
        k = mw <= a_
        lab = _relabel(_components(n, mi[k], mj[k]).reshape(h, w))
        labs.append(lab)
        nz.append(int(lab.max()))
    srt = np.argsort(al, kind="stable")
    nested = True
    for x, y in zip(srt[:-1].tolist(), srt[1:].tolist()):
        nested = nested and _is_nested(labs[x], labs[y])
    return {"labels": np.stack(labs), "n_zones": np.array(nz), "alphas": al, "mst_i": mi, "mst_j": mj, "mst_w": mw,
            "merge_levels": np.sort(mw), "n_mst_edges": int(mi.size), "nested": bool(nested)}


# ───────────────────────────── 6. 階層分水嶺と ultrametric contour map ─────────────────────────────
def _watershed_core(img: np.ndarray, mask: Optional[np.ndarray], conn: int) -> Dict[str, object]:
    """Kruskal で最小全域森を作り、各木の辺に dynamics の saliency を付ける。盆地(saliency 0 の辺の成分)まで出す。"""
    h, w = img.shape
    f = img.ravel()
    n = f.size
    ei, ej, _ = _grid_edges(h, w, conn)
    if mask is not None:
        mk = mask.ravel()
        keep = mk[ei] & mk[ej]
        ei, ej = ei[keep], ej[keep]
    else:
        mk = np.ones(n, bool)
    ew = np.maximum(f[ei], f[ej])
    # 同じ高さの辺の順: 低い端点が低い辺を先に(= 画素は最も低い隣の盆地へ、最急降下)、最後に辺の番号。
    # どの順でも最小全域森(分水嶺カット)だが、番号だけで決めると峠の帯の中で切れ目が格子に沿った直線と
    # L 字の段になった(実測: 触れ合う粒の −距離変換、PoC の動画のコマ)。
    order = np.lexsort((np.arange(ei.size), np.minimum(f[ei], f[ej]), ew))
    uf = _UF(n)
    cmin = f.tolist()
    cpix = list(range(n))                     # 成分の底の画素
    dpix: List[int] = []                      # saliency > 0 の辺で死ぬ盆地の底の画素
    ti: List[int] = []
    tj: List[int] = []
    ts: List[float] = []
    tw: List[float] = []
    E_i = ei[order].tolist()
    E_j = ej[order].tolist()
    E_w = ew[order].tolist()
    if len(E_i) > 0:
        for p, q, wv in zip(E_i, E_j, E_w):
            rp = uf.find(p)
            rq = uf.find(q)
            if rp == rq:
                continue
            sal = wv - max(cmin[rp], cmin[rq])
            # 浅い方(底が高い方)が死ぬ。同じ高さなら画素番号の大きい底の方
            if (cmin[rp], cpix[rp]) > (cmin[rq], cpix[rq]):
                dying, surv = cpix[rp], cpix[rq]
            else:
                dying, surv = cpix[rq], cpix[rp]
            dpix.append(dying)
            ti.append(p)
            tj.append(q)
            ts.append(sal)
            tw.append(wv)
            if uf.sz[rp] < uf.sz[rq]:
                rp, rq = rq, rp
            uf.p[rq] = rp
            uf.sz[rp] += uf.sz[rq]
            cmin[rp] = min(cmin[rp], cmin[rq])
            cpix[rp] = surv
    ti_a = np.array(ti, np.int64)
    tj_a = np.array(tj, np.int64)
    ts_a = np.array(ts, np.float64)
    zero = ts_a <= 0.0
    basin = _components(n, ti_a[zero], tj_a[zero])
    basin = np.where(mk, basin, -1)
    u, inv = np.unique(basin[mk], return_inverse=True)
    bl = np.zeros(n, np.int64)
    bl[mk] = inv + 1
    dyn = np.full(int(u.size), np.inf)
    dp = np.array(dpix, np.int64)
    pos = ts_a > 0.0
    if np.count_nonzero(pos) > 0:
        dyn[bl[dp[pos]] - 1] = ts_a[pos]
    return {"ti": ti_a, "tj": tj_a, "ts": ts_a, "tw": np.array(tw), "basin": bl, "n_basins": int(u.size),
            "mask": mk, "ei": ei, "ej": ej, "dynamics": dyn}


def _basin_hierarchy(core: Dict[str, object], f: np.ndarray, want_matrix: bool, max_matrix: int = 2500) -> Dict[str, object]:
    """盆地の間の木の辺(saliency > 0)で第 2 の Kruskal を回し、盆地ごとの dynamics・隣り合う盆地の ultrametric 距離・
    (盆地が max_matrix 以下なら)全盆地の ultrametric 距離の行列を作る。"""
    bl = core["basin"]
    k = core["n_basins"]
    ti, tj, ts = core["ti"], core["tj"], core["ts"]
    pos = ts > 0.0
    bi, bj, bs = bl[ti[pos]] - 1, bl[tj[pos]] - 1, ts[pos]
    order = np.lexsort((np.arange(bs.size), bs))
    # 盆地の底
    mk = core["mask"]
    bmin = np.full(k, np.inf)
    np.minimum.at(bmin, bl[mk] - 1, f[mk])
    # 隣り合う盆地の組(画素の辺から)
    ei, ej = core["ei"], core["ej"]
    li, lj = bl[ei] - 1, bl[ej] - 1
    cross = li != lj
    pa = np.minimum(li[cross], lj[cross])
    pb = np.maximum(li[cross], lj[cross])
    pairs = np.unique(np.stack([pa, pb], axis=1), axis=0) if pa.size else np.zeros((0, 2), np.int64)
    pd = np.full(pairs.shape[0], np.inf)
    adj: List[Dict[int, List[int]]] = [dict() for _ in range(k)]
    for idx, (x, y) in enumerate(pairs.tolist()):
        adj[x].setdefault(y, []).append(idx)
        adj[y].setdefault(x, []).append(idx)
    members: List[List[int]] = [[i] for i in range(k)]
    cid = list(range(k))
    cmin = bmin.tolist()
    D = np.zeros((k, k)) if (want_matrix and k <= max_matrix) else None
    levels: List[float] = []
    BI, BJ, BS = bi[order].tolist(), bj[order].tolist(), bs[order].tolist()
    if len(BI) > 0:
        for x, y, s in zip(BI, BJ, BS):
            cx, cy = cid[x], cid[y]
            if cx == cy:
                continue
            levels.append(s)
            for pidx in adj[cx].get(cy, []):
                pd[pidx] = s
            if D is not None:
                mx, my = np.array(members[cx]), np.array(members[cy])
                D[np.ix_(mx, my)] = s
                D[np.ix_(my, mx)] = s
            big, small = (cx, cy) if len(members[cx]) >= len(members[cy]) else (cy, cx)
            for m in members[small]:
                cid[m] = big
            members[big].extend(members[small])
            members[small] = []
            cmin[big] = min(cmin[big], cmin[small])
            # 隣接の付け替え(小さい方の隣を大きい方へ)
            for nb, lst in adj[small].items():
                if nb == big:
                    continue
                adj[big].setdefault(nb, []).extend(lst)
                d_nb = adj[nb]
                moved = d_nb.pop(small, [])
                d_nb.setdefault(big, []).extend(moved)
            adj[big].pop(small, None)
            adj[small] = {}
    if D is not None:
        # 違う木(マスクの別の連結成分)の盆地は無限遠
        roots = np.array(cid)
        D[roots[:, None] != roots[None, :]] = np.inf
        np.fill_diagonal(D, 0.0)
    return {"dynamics": core["dynamics"], "pairs": pairs, "pair_d": pd, "distance": D, "levels": np.sort(np.array(levels)),
            "basin_min": bmin}


def hierarchical_watershed(image, *, threshold: float = 0.0, n_regions: Optional[int] = None, mask=None,
                           connectivity: int = 4) -> Dict[str, object]:
    """dynamics による階層分水嶺: 地形 ``image``(低い所が盆地)の最小全域森の辺に dynamics の saliency を付け、
    saliency ≤ ``threshold`` の辺で結んだ成分を返す(``n_regions`` を与えたら、その数になる最小の閾値を使う)。

    ``mask`` を与えるとその中だけで(外は 0)。返す: ``labels``(1..k)、``n_regions``、``basins``(閾値 0 の分割 = 分水嶺の
    盆地)、``n_basins``、``dynamics``(盆地ごと、各連結成分で最も深い盆地は inf)、``levels``(盆地が消える高さの昇順)、
    ``threshold``(実際に使った値)。盆地の数 = dynamics > 閾値 の盆地の数(この関数が数えて返す ``n_expected``)。
    """
    op = "hierarchical_watershed"
    img = _image(image, "image", op)
    conn = _conn(connectivity, op)
    mk = _mask_opt(mask, img.shape, op)
    core = _watershed_core(img, mk, conn)
    hb = _basin_hierarchy(core, img.ravel(), want_matrix=False)
    dyn = hb["dynamics"]
    if n_regions is not None:
        k = _int(n_regions, "n_regions", op, 1, core["n_basins"])
        srt = np.sort(dyn)[::-1]
        thr = 0.0 if k >= srt.size else float(srt[k])          # k 番目に大きい dynamics より上は残す
        thr = max(thr, 0.0)
    else:
        thr = _num(threshold, "threshold", op, 0.0)
    keep = core["ts"] <= thr
    n = img.size
    lab = _components(n, core["ti"][keep], core["tj"][keep])
    out = _relabel(np.where(core["mask"], lab + 1, 0).reshape(img.shape), keep_zero=True)
    return {"labels": out, "n_regions": int(out.max()), "basins": core["basin"].reshape(img.shape),
            "n_basins": core["n_basins"], "dynamics": dyn, "levels": hb["levels"], "threshold": thr,
            "n_expected": int(np.count_nonzero(dyn > thr))}


def ultrametric_contour_map(image, *, mask=None, connectivity: int = 4, distance_matrix: bool = False) -> Dict[str, object]:
    """dynamics の階層の ultrametric contour map(UCM): 隣り合う画素 p, q の値 = 「p と q が同じ領域になる最小の閾値」。

    盆地の中の辺は 0、盆地の境の辺は第 2 の Kruskal(盆地の木を saliency の昇順に併合)で 2 つの盆地が出会う高さ。
    返す: ``ucm_h``(H, W − 1:画素とその右)、``ucm_v``(H − 1, W:画素とその下)、``ucm``(画素ごとに右と下の大きい方 =
    境界を左上の画素で代表、segeval と同じ)、``basins``、``levels``、``distance``(``distance_matrix=True`` かつ盆地が
    2500 以下なら盆地の全組の ultrametric 距離の行列)。閾値 θ で ucm > θ の辺を切った成分 = hierarchical_watershed(θ)。
    """
    op = "ultrametric_contour_map"
    img = _image(image, "image", op)
    conn = _conn(connectivity, op)
    mk = _mask_opt(mask, img.shape, op)
    core = _watershed_core(img, mk, conn)
    hb = _basin_hierarchy(core, img.ravel(), want_matrix=bool(distance_matrix))
    h, w = img.shape
    bl = core["basin"].reshape(h, w)
    k = core["n_basins"]
    pairs, pd = hb["pairs"], hb["pair_d"]

    def edge_vals(A: np.ndarray, B: np.ndarray) -> np.ndarray:
        out = np.zeros(A.shape)
        a_ = A.ravel() - 1
        b_ = B.ravel() - 1
        o = out.ravel()
        diff = np.flatnonzero((a_ != b_) & (a_ >= 0) & (b_ >= 0))
        if diff.size:
            lo = np.minimum(a_[diff], b_[diff])
            hi = np.maximum(a_[diff], b_[diff])
            if pairs.shape[0] > 0:
                key = lo * max(k, 1) + hi
                pk = pairs[:, 0] * max(k, 1) + pairs[:, 1]
                pos = np.searchsorted(pk, key)
                pos = np.clip(pos, 0, pk.size - 1)
                o[diff] = np.where(pk[pos] == key, pd[pos], np.inf)
        return o.reshape(A.shape)

    uh = edge_vals(bl[:, :-1], bl[:, 1:])
    uv = edge_vals(bl[:-1, :], bl[1:, :])
    ucm = np.zeros((h, w))
    ucm[:, :-1] = np.maximum(ucm[:, :-1], uh)
    ucm[:-1, :] = np.maximum(ucm[:-1, :], uv)
    return {"ucm_h": uh, "ucm_v": uv, "ucm": ucm, "basins": bl, "n_basins": k, "levels": hb["levels"],
            "dynamics": hb["dynamics"], "distance": hb["distance"]}


# ───────────────────────────── 7. 超画素 ─────────────────────────────
def _connected_per_label(lab: np.ndarray) -> Tuple[bool, int]:
    """各ラベルが 4-連結か(ラベルごとの 4-連結成分の数 = 1)。返す: (全部 1 か, 連結でないラベルの数)。"""
    h, w = lab.shape
    ei, ej, _ = _grid_edges(h, w, 4)
    l = lab.ravel()
    same = l[ei] == l[ej]
    comp = _components(l.size, ei[same], ej[same])
    pairs = np.unique(np.stack([l, comp], axis=1), axis=0)
    counts = np.bincount(pairs[:, 0])
    bad = int(np.count_nonzero(counts[np.unique(l)] != 1))
    return bad == 0, bad


def snic_superpixels(image, *, n_segments: int = 100, compactness: float = 0.1, connectivity: int = 4) -> Dict[str, object]:
    """SNIC(Achanta–Süsstrunk 2017 の Algorithm 1): 格子の種から優先度つき待ち行列で育てる非反復の超画素。

    距離 d² = |Δx|²/s² + |Δc|²/m²(s = √(N/K)、m = ``compactness``、c は画素の値。SLIC の正規化の形、式 (1) の表記は要確認)。
    待ち行列から最小の d を取り出し、未ラベルならラベルを付け、重心(位置と値)をその場で更新し、未ラベルの近傍を今の重心との
    距離で積む。同点は (距離, 積んだ順) で決める(決定的)。
    返す: ``labels``(1..K)、``n_segments``、``all_connected``(全ラベルが 4-連結 = 構成上の保証を数えて確かめた印)、
    ``n_disconnected``、``sizes``、``seeds``((K, 2) の [row, col])、``s``。
    """
    op = "snic_superpixels"
    img = _image(image, "image", op, min_side=2)
    K = _int(n_segments, "n_segments", op, 1, img.size)
    m = _num(compactness, "compactness", op, 0.0, lo_open=True)
    conn = _conn(connectivity, op)
    h, w = img.shape
    N = img.size
    s = math.sqrt(N / K)
    ny = max(1, int(round(h / s)))
    nx = max(1, int(round(w / s)))
    ys = ((np.arange(ny) + 0.5) * h / ny).astype(int)
    xs = ((np.arange(nx) + 0.5) * w / nx).astype(int)
    seeds = np.array([(y, x) for y in ys.tolist() for x in xs.tolist()], dtype=np.int64)
    f = img.ravel().tolist()
    lab = [0] * N
    if conn == 4:
        offs = ((-1, 0), (1, 0), (0, -1), (0, 1))
    else:
        offs = ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1))
    k_n = seeds.shape[0]
    sy = [0.0] * (k_n + 1)
    sx = [0.0] * (k_n + 1)
    sc = [0.0] * (k_n + 1)
    cnt = [0] * (k_n + 1)
    heap: List[Tuple[float, int, int, int]] = []
    tick = 0
    inv_s2 = 1.0 / (s * s)
    inv_m2 = 1.0 / (m * m)
    assert k_n > 0
    for k, (y, x) in enumerate(seeds.tolist(), start=1):
        heapq.heappush(heap, (0.0, tick, y * w + x, k))
        tick += 1
    while heap:
        d, _, p, k = heapq.heappop(heap)
        if lab[p] != 0:
            continue
        lab[p] = k
        y, x = divmod(p, w)
        sy[k] += y
        sx[k] += x
        sc[k] += f[p]
        cnt[k] += 1
        cy, cx, cc = sy[k] / cnt[k], sx[k] / cnt[k], sc[k] / cnt[k]
        for dy, dx in offs:
            yy, xx = y + dy, x + dx
            if 0 <= yy < h and 0 <= xx < w:
                qn = yy * w + xx
                if lab[qn] == 0:
                    dd = ((yy - cy) ** 2 + (xx - cx) ** 2) * inv_s2 + (f[qn] - cc) ** 2 * inv_m2
                    heapq.heappush(heap, (dd, tick, qn, k))
                    tick += 1
    L = np.array(lab, np.int64).reshape(h, w)
    ok, bad = _connected_per_label(L)
    return {"labels": L, "n_segments": int(np.unique(L).size), "all_connected": ok, "n_disconnected": bad,
            "sizes": np.bincount(L.ravel())[1:], "seeds": seeds, "s": s, "compactness": m}


def quickshift(image, *, kernel_size: float = 3.0, max_dist: float = 6.0, ratio: float = 1.0,
               search_radius: int = 10) -> Dict[str, object]:
    """quick shift(Vedaldi–Soatto 2008): 特徴 (y, x, ratio · I) で Parzen 密度 P_i = Σ_j exp(−D_ij²/(2σ²))(窓 3σ、σ =
    ``kernel_size``)を見積もり、各画素を「密度が上の点のうち最も近い点」(半径 ``search_radius`` の窓の中)に繋ぎ、
    長さ > ``max_dist`` の枝を切った木の成分を領域にする。

    密度の同点は画素番号で決める(乱数なし)。木は ``max_dist`` に依らない(search_radius を固定すれば)ので、
    max_dist を増やした分割は入れ子になる(切る枝が減るだけ)。返す: ``labels``(1..k)、``n_segments``、``parent``
    (平らな添字、根は自分)、``link``(親までの距離、根は inf)、``density``。
    """
    op = "quickshift"
    img = _image(image, "image", op, min_side=2)
    sg = _num(kernel_size, "kernel_size", op, 0.0, lo_open=True)
    tau = _num(max_dist, "max_dist", op, 0.0)
    rt = _num(ratio, "ratio", op, 0.0)
    R = _int(search_radius, "search_radius", op, 1, 200)
    h, w = img.shape
    c = img * rt
    W = int(math.ceil(3.0 * sg))
    dens = np.zeros((h, w))
    pad = np.pad(c, W, mode="constant", constant_values=np.nan)
    rng_w = range(-W, W + 1)
    assert len(rng_w) > 0
    for dy in rng_w:
        for dx in rng_w:
            sh = pad[W + dy:W + dy + h, W + dx:W + dx + w]
            d2 = dy * dy + dx * dx + (sh - c) ** 2
            v = np.exp(-d2 / (2.0 * sg * sg))
            dens += np.where(np.isnan(v), 0.0, v)
    idx = np.arange(h * w).reshape(h, w)
    best = np.full((h, w), np.inf)
    par = idx.copy()
    padc = np.pad(c, R, mode="constant", constant_values=np.nan)
    padd = np.pad(dens, R, mode="constant", constant_values=-np.inf)
    padi = np.pad(idx, R, mode="constant", constant_values=-1)
    rng_r = range(-R, R + 1)
    assert len(rng_r) > 0
    for dy in rng_r:
        for dx in rng_r:
            if dy * dy + dx * dx > R * R or (dy == 0 and dx == 0):
                continue
            sd = padd[R + dy:R + dy + h, R + dx:R + dx + w]
            si = padi[R + dy:R + dy + h, R + dx:R + dx + w]
            sc_ = padc[R + dy:R + dy + h, R + dx:R + dx + w]
            higher = (sd > dens) | ((sd == dens) & (si > idx))
            d2 = dy * dy + dx * dx + (sc_ - c) ** 2
            better = higher & (si >= 0) & ((d2 < best) | ((d2 == best) & (si < par)))
            best = np.where(better, d2, best)
            par = np.where(better, si, par)
    link = np.sqrt(best)
    cut = link > tau
    p = par.ravel().copy()
    p[cut.ravel()] = idx.ravel()[cut.ravel()]
    nodes = np.arange(h * w)
    keep = p != nodes
    lab = _relabel(_components(h * w, nodes[keep], p[keep]).reshape(h, w))
    return {"labels": lab, "n_segments": int(lab.max()), "parent": par, "link": link, "density": dens,
            "max_dist": tau, "kernel_size": sg, "ratio": rt, "search_radius": R}


def superpixel_quality(labels_sp, labels_true, *, tau: float = 2.0) -> Dict[str, object]:
    """超画素の採点: 境界の再現率(``segeval.seg_boundary_f`` の recall、許容 τ)、補正つき未分割誤差 CUSE =
    (1/N) Σ_k |S_k − G_max(S_k)|(Neubert–Protzel 2012、SNIC 論文の式 (2))、ASA = 1 − CUSE、Neubert–Protzel の未分割誤差
    UE = (1/N) Σ_G Σ_(S∩G≠∅) min(|S∩G|, |S − G|)、超画素の数。真値の 0 も 1 つの領域として数える(背景も被覆の対象)。"""
    op = "superpixel_quality"
    s = _labels_in(labels_sp, "labels_sp", op)
    t = _labels_in(labels_true, "labels_true", op, s.shape)
    N = s.size
    if N == 0:
        raise ValueError("%s: empty labels" % op)
    su, si = np.unique(s.ravel(), return_inverse=True)
    tu, tinv = np.unique(t.ravel(), return_inverse=True)
    M = sparse.coo_matrix((np.ones(N), (si, tinv)), shape=(su.size, tu.size)).toarray()
    ssize = M.sum(axis=1)
    cuse = float((ssize - M.max(axis=1)).sum() / N)
    ue = float(np.minimum(M, ssize[:, None] - M)[M > 0].sum() / N)
    bf = segeval.seg_boundary_f(s, t, tau=tau)
    return {"boundary_recall": float(bf["recall"]), "boundary_precision": float(bf["precision"]), "cuse": cuse,
            "asa": 1.0 - cuse, "ue_np": ue, "n_superpixels": int(su.size), "n_true": int(tu.size), "tau": float(tau)}


# ───────────────────────────── 8. 閾値 ─────────────────────────────
def _hist(image, nbins, op: str):
    a = _image(image, "image", op).ravel()
    nb = _int(nbins, "nbins", op, 2, 1 << 16)
    lo, hi = float(a.min()), float(a.max())
    if hi <= lo:
        raise ValueError("%s: image is flat (min == max) — no threshold separates it" % op)
    counts, edges = np.histogram(a, bins=nb, range=(lo, hi))
    centers = 0.5 * (edges[:-1] + edges[1:])
    return a, counts.astype(np.float64), edges, centers


def _bin_index(a: np.ndarray, edges: np.ndarray) -> np.ndarray:
    nb = edges.size - 1
    return np.clip(np.searchsorted(edges, a, side="right") - 1, 0, nb - 1)


def threshold_triangle(image, *, nbins: int = 256) -> Dict[str, object]:
    """三角法(Zack–Rogers–Latt 1977): 山頂 (b_p, h_p) と、裾の長い側の端のビン (b_e, 0) を結ぶ線から、間のビンの
    (b, h_b) までの符号つき垂直距離が最大のビンを閾値にする(線の下側を正)。返す: ``threshold``(そのビンの中心)、
    ``mask`` = image > threshold、``bin``、``distance``(各ビンの距離、範囲外は nan)。端点の高さ 0・裾の側の選び方は
    skimage / ImageJ と同じ規約(原典は要確認)。"""
    op = "threshold_triangle"
    a, cnt, edges, centers = _hist(image, nbins, op)
    nb = cnt.size
    nzb = np.flatnonzero(cnt)
    lo_b, hi_b = int(nzb[0]), int(nzb[-1])
    pk = int(np.argmax(cnt))
    hp = cnt[pk]
    if pk - lo_b < hi_b - pk:                      # 右の裾が長い → 端点は右
        end = hi_b
    else:
        end = lo_b
    dist = np.full(nb, np.nan)
    lo_r, hi_r = (end, pk) if end < pk else (pk + 1, end + 1)
    b = np.arange(lo_r, hi_r)
    # 直線 (end, 0)–(pk, hp) からの符号つき距離(線より下 = ヒストグラムが谷 = 正)
    dx, dy = pk - end, hp
    nrm = math.hypot(dx, dy)
    sgn = 1.0 if end < pk else -1.0
    dist[b] = sgn * (dy * (b - end) - dx * cnt[b]) / nrm
    k = int(np.nanargmax(dist))
    t = float(centers[k])
    return {"threshold": t, "mask": (a > t).reshape(np.shape(image)), "bin": k, "distance": dist, "peak_bin": pk,
            "end_bin": end, "centers": centers, "counts": cnt}


def threshold_isodata(image, *, nbins: int = 256, max_iter: int = 1000) -> Dict[str, object]:
    """isodata(Ridler–Calvard 1978): t ← (μ_≤t + μ_>t)/2 を **画素の値の上で** 分割が変わらなくなるまで反復(初期値 = 平均)。

    分割が止まれば t は μ を計算し直しても動かない = 不動点 t = (μ_low + μ_high)/2 が厳密に成り立つ(``residual`` = 0)。
    ヒストグラムの上の不動点(skimage と同じ「ビンの中心 c で 0 ≤ (μ_≤c + μ_>c)/2 − c < ビン幅」)も ``fixed_points`` で返す。
    返す: ``threshold``、``mask`` = image > t、``mu_low`` / ``mu_high``、``residual``、``n_iter``、``fixed_points``。
    """
    op = "threshold_isodata"
    a, cnt, edges, centers = _hist(image, nbins, op)
    mi = _int(max_iter, "max_iter", op, 1, 10 ** 6)
    t = float(a.mean())
    prev = None
    it = 0
    lo_m = hi_m = t
    for it in range(1, mi + 1):
        low = a <= t
        n_low = int(np.count_nonzero(low))
        if n_low == 0 or n_low == a.size:
            raise ValueError("%s: iteration left one class empty" % op)
        lo_m = float(a[low].mean())
        hi_m = float(a[~low].mean())
        t_new = 0.5 * (lo_m + hi_m)
        key = n_low
        if prev is not None and key == prev:
            t = t_new
            break
        prev = key
        t = t_new
    low = a <= t
    lo_m, hi_m = float(a[low].mean()), float(a[~low].mean())
    res = abs(t - 0.5 * (lo_m + hi_m))
    csl = np.cumsum(cnt)
    csh = csl[-1] - csl
    ci = np.cumsum(cnt * centers)
    with np.errstate(divide="ignore", invalid="ignore"):
        lower = ci[:-1] / csl[:-1]
        higher = (ci[-1] - ci[:-1]) / csh[:-1]
    allm = 0.5 * (lower + higher)
    bw = centers[1] - centers[0]
    dd = allm - centers[:-1]
    fp = centers[:-1][(dd >= 0) & (dd < bw)]
    return {"threshold": float(t), "mask": (a > t).reshape(np.shape(image)), "mu_low": lo_m, "mu_high": hi_m,
            "residual": float(res), "n_iter": it, "fixed_points": fp, "bin_width": float(bw)}


def threshold_kittler(image, *, nbins: int = 256) -> Dict[str, object]:
    """最小誤差閾値(Kittler–Illingworth 1986): 各ビン t で低い側(ビン ≤ t)と高い側に分け、
    J(t) = 1 + 2(P1 ln σ1 + P2 ln σ2) − 2(P1 ln P1 + P2 ln P2) を最小にする(σ は各側のビンの中心の標準偏差。どちらかの側の
    σ が 0 のビンは除く)。返す: ``threshold`` = そのビンの上端(mask はビンの番号 > t で決める = 端の値も矛盾なし)、
    ``mask``、``bin``、``criterion``(J、除いたビンは nan)。"""
    op = "threshold_kittler"
    a, cnt, edges, centers = _hist(image, nbins, op)
    p = cnt / cnt.sum()
    P1 = np.cumsum(p)
    m1 = np.cumsum(p * centers)
    s1 = np.cumsum(p * centers * centers)
    P2 = 1.0 - P1
    with np.errstate(divide="ignore", invalid="ignore"):
        mu1 = m1 / P1
        mu2 = (m1[-1] - m1) / P2
        v1 = s1 / P1 - mu1 ** 2
        v2 = (s1[-1] - s1) / P2 - mu2 ** 2
        ok = (P1 > 0) & (P2 > 1e-15) & (v1 > 1e-15 * (centers[-1] - centers[0]) ** 2) & (v2 > 1e-15 * (centers[-1] - centers[0]) ** 2)
        J = 1.0 + 2.0 * (P1 * np.log(np.sqrt(np.abs(v1))) + P2 * np.log(np.sqrt(np.abs(v2)))) \
            - 2.0 * (P1 * np.log(P1) + P2 * np.log(np.where(P2 > 0, P2, 1.0)))
    J = np.where(ok, J, np.nan)
    if np.count_nonzero(ok) == 0:
        raise ValueError("%s: no threshold leaves both classes with positive variance" % op)
    k = int(np.nanargmin(J))
    bi = _bin_index(a, edges)
    return {"threshold": float(edges[k + 1]), "mask": (bi > k).reshape(np.shape(image)), "bin": k, "criterion": J,
            "centers": centers}


def threshold_kapur(image, *, nbins: int = 256) -> Dict[str, object]:
    """最大エントロピー閾値(Kapur–Sahoo–Wong 1985): H(t) = −Σ_(i ≤ t) (p_i/P1) ln(p_i/P1) − Σ_(i > t) (p_i/P2) ln(p_i/P2)
    を最大にするビン t(両側とも確率が正のビンだけ)。返す: ``threshold`` = そのビンの上端、``mask``(ビンの番号 > t)、
    ``bin``、``entropy``(H、除いたビンは nan)。"""
    op = "threshold_kapur"
    a, cnt, edges, centers = _hist(image, nbins, op)
    p = cnt / cnt.sum()
    with np.errstate(divide="ignore", invalid="ignore"):
        plogp = np.where(p > 0, p * np.log(np.where(p > 0, p, 1.0)), 0.0)
        P1 = np.cumsum(p)
        A1 = np.cumsum(plogp)
        P2 = 1.0 - P1
        A2 = A1[-1] - A1
        # −Σ (p/P) ln(p/P) = ln P − (Σ p ln p)/P
        H1 = np.log(np.where(P1 > 0, P1, 1.0)) - A1 / P1
        H2 = np.log(np.where(P2 > 0, P2, 1.0)) - A2 / P2
    ok = (P1 > 0) & (P2 > 1e-15)
    H = np.where(ok, H1 + H2, np.nan)
    if np.count_nonzero(ok) == 0:
        raise ValueError("%s: no valid split" % op)
    k = int(np.nanargmax(H))
    bi = _bin_index(a, edges)
    return {"threshold": float(edges[k + 1]), "mask": (bi > k).reshape(np.shape(image)), "bin": k, "entropy": H,
            "centers": centers}
