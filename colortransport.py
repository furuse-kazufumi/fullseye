# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""colortransport —— **分布を運ぶ** op 族(最適輸送・色移し・勾配合成)。

動機は :mod:`imgmetrics` と同じく実測の空白(2026-09-02)。op カタログ全文で
``histogram_match`` / ``color_transfer`` / ``poisson_blend`` / ``sinkhorn`` /
``wasserstein`` / ``optimal_transport`` が **一件もヒットしない**
(``tonemap_reinhard`` はトーンマッピングで別物)。

:mod:`imgmetrics` が「2 枚がどれだけ違うか**を測る**」側なら、こちらは
「片方の分布を相手に**合わせる**」側 ―― 測る op と直す op が対になる。
``rgb_to_lab`` はあちらの実体をそのまま使う(色空間を 2 つ持たない)。

## この族も検算できる

* **1 次元の最適輸送には厳密解がある。** 並べ替えて累積分布を突き合わせるだけ
  ―― 総当たりの割当問題(``scipy.optimize.linear_sum_assignment``)と
  **厳密に一致する**ことをテストで固定してある。
* **ガウス分布どうしの 2-Wasserstein 距離には閉じた式がある。**
  1 次元なら ``W2^2 = (m1-m2)^2 + (s1-s2)^2``。
* **Poisson 合成には構成上の不変量がある。** 解いた結果の**内部のラプラシアン
  は元の勾配場と一致**し、**境界は貼り先と厳密に一致**する。解が正しいことを
  出力だけから確かめられる珍しい処理。
* **Sinkhorn は正則化を弱めると厳密解へ収束する。** 収束の様子そのものを
  テストにしてある(``reg`` を下げると厳密解との差が単調に縮む)。

## 黙って間違う場所(この族の危ないところ)

* **Reinhard 流の色移しは「各チャネルが単峰の正規分布」を仮定している。**
  二峰の絵(前景と背景がはっきり分かれた絵)に掛けると、平均と分散だけ
  合って**どちらの峰にも当たらない色**になる。例外は出ない。
  この仮定の破れ方は ``color_transfer`` の docstring に実測つきで書いてある。
* **チャネルごとのヒストグラム整合は、チャネル間の相関を壊す。** 各軸の周辺
  分布は完璧に一致するのに、**同時分布は似ても似つかない**ことがありうる。
  相関まで合わせたいなら ``method="gaussian"``(共分散ごと運ぶ Monge 写像)。
* **Sinkhorn の距離は正則化のぶん偏る。** ``reg`` が大きいほど輸送計画がぼけ、
  距離は真値から**系統的にずれる**(0 に近づくのではなく、自分自身との距離が
  0 でなくなる)。よって ``sinkhorn_distance`` は「厳密な距離」ではないことを
  名前と docstring の両方に書き、厳密が要る 1 次元では
  :func:`wasserstein_1d` を使わせる。
* **Poisson 合成は貼った物の色を変える。** それが目的の処理だが、
  「貼った物体の色を測る」用途にそのまま流すと**測っているのは貼り先の色**に
  なる。返り値と一緒に、内部で何画素動かしたかを出す。

使い方::

    import colortransport as CT

    CT.wasserstein_1d(a.ravel(), b.ravel())          # 厳密(1 次元)
    CT.histogram_match(src, ref)                     # 周辺分布を合わせる
    CT.color_transfer(src, ref, method="gaussian")   # 相関ごと運ぶ
    CT.poisson_blend(src, dst, mask, offset=(20, 30))
"""
from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse import linalg as sparse_linalg

import imgmetrics as _M
from metriccontract import MetricContractError

__all__ = [
    "wasserstein_1d", "transport_plan_1d",
    "histogram_match", "color_transfer", "COLOR_TRANSFER_METHODS",
    "sinkhorn", "sinkhorn_distance", "sinkhorn_divergence",
    "transport_cost", "apply_transport",
    "gaussian_transport_map", "poisson_blend",
]


# =========================================================================
# 1 次元の最適輸送 —— 厳密解
# =========================================================================

def _weighted_quantile_grid(values, weights):
    order = np.argsort(values, kind="mergesort")
    v = np.asarray(values, dtype=np.float64)[order]
    if weights is None:
        w = np.full(v.size, 1.0 / v.size)
    else:
        w = np.asarray(weights, dtype=np.float64)[order]
        total = w.sum()
        if total <= 0:
            raise MetricContractError("weights must sum to a positive number")
        w = w / total
    return v, np.cumsum(w)


def wasserstein_1d(u_values, v_values, p=1, u_weights=None, v_weights=None):
    """1 次元の p-Wasserstein 距離。**厳密解**。

    1 次元では最適輸送に閉じた形があり、累積分布の逆関数どうしの
    ``L^p`` 距離になる ―― 反復も近似も要らない。総当たりの割当問題
    (``scipy.optimize.linear_sum_assignment``)と厳密に一致することを
    テストで固定してある。

    Parameters
    ----------
    u_values, v_values : array_like
        標本(1 次元に潰される)。長さは違ってよい。
    p : float
        次数。``p=1`` が Earth Mover 距離、``p=2`` が 2-Wasserstein。
    u_weights, v_weights : array_like, optional
        標本ごとの重み(和は内部で 1 に正規化する)。

    Returns
    -------
    float
    """
    u = np.asarray(u_values, dtype=np.float64).ravel()
    v = np.asarray(v_values, dtype=np.float64).ravel()
    if u.size == 0 or v.size == 0:
        raise MetricContractError("both samples must be non-empty")
    if not (np.all(np.isfinite(u)) and np.all(np.isfinite(v))):
        raise MetricContractError("samples must be finite")
    if not np.isfinite(p) or p < 1:
        raise MetricContractError(f"p must be a finite number >= 1, got {p!r}")

    us, ucdf = _weighted_quantile_grid(u, u_weights)
    vs, vcdf = _weighted_quantile_grid(v, v_weights)

    # 2 つの累積分布の段の位置をすべて集め、各区間の幅 x |逆関数の差|^p を積む
    edges = np.unique(np.concatenate([ucdf, vcdf]))
    widths = np.diff(np.concatenate([[0.0], edges]))
    ui = np.searchsorted(ucdf, edges - 1e-15, side="left").clip(0, us.size - 1)
    vi = np.searchsorted(vcdf, edges - 1e-15, side="left").clip(0, vs.size - 1)
    gaps = np.abs(us[ui] - vs[vi])
    if p == 1:
        return float(np.sum(widths * gaps))
    return float(np.sum(widths * gaps ** p) ** (1.0 / p))


def transport_plan_1d(u_values, v_values):
    """1 次元の厳密な輸送計画(北西隅則)。``(n, m)`` の質量行列を返す。

    行和が ``1/n``、列和が ``1/m`` になる ―― これは**構成上厳密**で、
    数値誤差以外でずれることはない(テストで固定)。
    """
    u = np.asarray(u_values, dtype=np.float64).ravel()
    v = np.asarray(v_values, dtype=np.float64).ravel()
    if u.size == 0 or v.size == 0:
        raise MetricContractError("both samples must be non-empty")
    n, m = u.size, v.size
    ui = np.argsort(u, kind="mergesort")
    vi = np.argsort(v, kind="mergesort")
    plan = np.zeros((n, m))
    i = j = 0
    ru, rv = 1.0 / n, 1.0 / m
    while i < n and j < m:
        take = min(ru, rv)
        plan[ui[i], vi[j]] += take
        ru -= take
        rv -= take
        if ru <= 1e-15:
            i += 1
            ru = 1.0 / n
        if rv <= 1e-15:
            j += 1
            rv = 1.0 / m
    return plan


# =========================================================================
# ヒストグラム整合
# =========================================================================

def histogram_match(src, ref, bins=None, ties="average"):
    """``src`` の値分布を ``ref`` に合わせる(1 次元の厳密な最適輸送)。

    順位を保ったまま参照の分位点に置き換える。``bins`` を指定すると、その段数の
    累積分布で近似する ―― 速いが**厳密ではなくなる**ので、既定は ``None``
    (厳密)にしてある。

    **同じ値の画素をどう扱うかで、絵の意味が変わる。** 単調写像なら「等しい入力
    は等しい出力に写る」はずだが、素朴に順位で置き換えると**同値が引き裂かれる**。
    実測(値 2 が 4 画素ある整数画像):出力は ``0.2222 / 0.3333 / 0.4444 /
    0.5556`` の 4 つに分かれた。つまり**平坦だった領域に、元の絵に無い濃淡が
    生える**。整数画像は同値だらけなので、これは例外ではなく常態。

    * ``ties="average"``(既定)—— 同値の画素には、そこに割り当たった参照値の
      **平均**を与える。等しい入力は等しい出力に写り、単調性が保たれる。
      その代わり**出力の分布は参照と厳密には一致しなくなる**(同値の塊のぶん、
      分布が階段状に丸まる)。連続な入力(同値が無い)なら厳密一致のまま。
    * ``ties="break"`` —— 順位そのままで引き裂く。**出力の分布は参照と厳密に
      一致する**が、平坦部に偽の濃淡が出る。分布を厳密に合わせることが目的で、
      絵として見ないと分かっているときだけ。

    どちらを選んでも失うものがある(分布の厳密さ か 平坦部の平坦さ)ので、
    **黙って片方に決めず引数にした**。

    多チャネルの絵に**そのまま掛けるとチャネル間の相関を壊す**。
    各軸の周辺分布は合うのに、色の組合せが元に無かったものになりうる。
    相関ごと運びたいときは :func:`color_transfer` の ``method="gaussian"``。
    """
    if ties not in ("average", "break"):
        raise MetricContractError(f"ties must be 'average' or 'break', got {ties!r}")
    s = np.asarray(src, dtype=np.float64)
    r = np.asarray(ref, dtype=np.float64).ravel()
    if s.size == 0 or r.size == 0:
        raise MetricContractError("both images must be non-empty")
    if not (np.all(np.isfinite(s)) and np.all(np.isfinite(r))):
        raise MetricContractError("images must be finite")

    flat = s.ravel()
    order = np.argsort(flat, kind="mergesort")
    ranks = np.empty(flat.size, dtype=np.float64)
    ranks[order] = (np.arange(flat.size) + 0.5) / flat.size

    if bins is None:
        rs = np.sort(r)
        idx = np.clip((ranks * rs.size).astype(np.int64), 0, rs.size - 1)
        out = rs[idx]
    else:
        if not isinstance(bins, (int, np.integer)) or bins < 2:
            raise MetricContractError(f"bins must be None (exact) or an integer >= 2, got {bins!r}")
        hist, edges = np.histogram(r, bins=int(bins))
        cdf = np.cumsum(hist).astype(np.float64)
        cdf /= cdf[-1]
        centres = 0.5 * (edges[:-1] + edges[1:])
        out = np.interp(ranks, cdf, centres)

    if ties == "break":
        import fssystem
        uniq_n = np.unique(flat).size
        if uniq_n < flat.size and fssystem.get_system("extra_checks") == "on":
            raise MetricContractError(
                f"ties='break' splits {flat.size - uniq_n} tied pixel(s) into different output "
                "values, so flat regions gain shading that was never in the source "
                "(measured: one value held by 4 pixels came out as 4 distinct levels). "
                "extra_checks='on' refuses it; use ties='average' or drop that system setting"
            )
    if ties == "average":
        # 同値の塊ごとに、割り当たった参照値の平均へ潰す(単調性の回復)
        uniq, inv = np.unique(flat, return_inverse=True)
        if uniq.size < flat.size:                       # 同値があるときだけ働く
            sums = np.bincount(inv, weights=out, minlength=uniq.size)
            counts = np.bincount(inv, minlength=uniq.size)
            out = (sums / counts)[inv]
    return out.reshape(s.shape)


# =========================================================================
# 色移し
# =========================================================================

COLOR_TRANSFER_METHODS = ("reinhard", "gaussian", "histogram")


def gaussian_transport_map(src_samples, ref_samples):
    """2 つの点群を正規分布とみなしたときの Monge 写像 ``(A, b)``。

    ``x -> A (x - m1) + m2`` で、``A`` は
    ``S1^-1/2 (S1^1/2 S2 S1^1/2)^1/2 S1^-1/2``(Bures 幾何の閉じた形)。
    **共分散ごと運ぶ**ので、チャネル間の相関が保たれる。

    退化(片方の共分散が特異)では逆平方根が作れない ―― 疑似逆で誤魔化すと
    「運べていないのに運んだ顔をした」写像になるので ``ValueError``。
    """
    a = np.asarray(src_samples, dtype=np.float64)
    b = np.asarray(ref_samples, dtype=np.float64)
    if a.ndim != 2 or b.ndim != 2 or a.shape[1] != b.shape[1]:
        raise MetricContractError(f"samples must be (N, D) with matching D, got {a.shape} and {b.shape}")
    if a.shape[0] < a.shape[1] + 1 or b.shape[0] < b.shape[1] + 1:
        raise MetricContractError("need more samples than dimensions to estimate a covariance")

    m1, m2 = a.mean(axis=0), b.mean(axis=0)
    s1 = np.cov(a, rowvar=False)
    s2 = np.cov(b, rowvar=False)
    s1 = np.atleast_2d(s1)
    s2 = np.atleast_2d(s2)

    def _sqrtm_psd(m, name):
        w, v = np.linalg.eigh(0.5 * (m + m.T))
        if np.min(w) < -1e-9 * max(1.0, float(np.max(np.abs(w)))):
            raise MetricContractError(f"{name} is not positive semi-definite (min eigenvalue {np.min(w):.3e})")
        return v @ np.diag(np.sqrt(np.clip(w, 0.0, None))) @ v.T, w

    r1, w1 = _sqrtm_psd(s1, "source covariance")
    if np.min(w1) <= 1e-12 * max(1.0, float(np.max(w1))):
        raise MetricContractError(
            f"source covariance is singular (min eigenvalue {np.min(w1):.3e}); the Monge map is "
            "undefined. A pseudo-inverse here would return a map that moves nothing along the "
            "degenerate direction while looking like a valid transport"
        )
    r1_inv = np.linalg.inv(r1)
    mid, _ = _sqrtm_psd(r1 @ s2 @ r1, "intermediate")
    A = r1_inv @ mid @ r1_inv
    return A, m1, m2


def color_transfer(src, ref, method="reinhard", space="lab"):
    """``src`` の色味を ``ref`` に寄せる。

    Parameters
    ----------
    src, ref : array_like
        ``(..., 3)`` の sRGB(``[0, 1]`` の float、または整数 dtype)。
        大きさは違ってよい(統計だけを使う)。
    method : {"reinhard", "gaussian", "histogram"}
        * ``"reinhard"`` —— 各チャネルの平均と標準偏差だけ合わせる
          (Reinhard, Ashikhmin, Gooch & Shirley, IEEE CG&A 21(5), 2001)。
          **各チャネルが単峰の正規分布**という仮定が効いている。
          前景と背景がはっきり分かれた 二峰の絵では、平均と分散は合うのに
          **どちらの峰にも当たらない色**になる(例外は出ない)。
        * ``"gaussian"`` —— 共分散ごと運ぶ Monge 写像。**相関が保たれる**。
        * ``"histogram"`` —— チャネルごとに厳密なヒストグラム整合。
          周辺分布は完全に一致するが、**チャネル間の相関は壊れる**。
    space : {"lab", "rgb"}
        統計を取る空間。既定の ``lab`` は :mod:`imgmetrics` の実体を使う。

    Returns
    -------
    ndarray
        ``src`` と同じ形の sRGB ``[0, 1]``(色域外は切り詰められる)。
    """
    if method not in COLOR_TRANSFER_METHODS:
        raise MetricContractError(f"method must be one of {COLOR_TRANSFER_METHODS}, got {method!r}")
    if space not in ("lab", "rgb"):
        raise MetricContractError(f"space must be 'lab' or 'rgb', got {space!r}")

    s = _M._to_unit_float(src)
    r = _M._to_unit_float(ref)
    for arr, nm in ((s, "src"), (r, "ref")):
        if arr.ndim < 2 or arr.shape[-1] != 3:
            raise MetricContractError(f"{nm} must be an RGB image with 3 channels last, got {arr.shape}")

    sv = (_M.rgb_to_lab(s) if space == "lab" else s).reshape(-1, 3)
    rv = (_M.rgb_to_lab(r) if space == "lab" else r).reshape(-1, 3)

    if method == "reinhard":
        ss, rs = sv.std(axis=0), rv.std(axis=0)
        if np.any(ss <= 1e-12):
            raise MetricContractError(
                "a source channel is constant, so it has no spread to rescale; "
                "Reinhard transfer is undefined here (scaling by 0 would silently flatten it)"
            )
        out = (sv - sv.mean(axis=0)) * (rs / ss) + rv.mean(axis=0)
    elif method == "gaussian":
        A, m1, m2 = gaussian_transport_map(sv, rv)
        out = (sv - m1) @ A.T + m2
    else:
        out = np.stack([histogram_match(sv[:, c], rv[:, c]) for c in range(3)], axis=1)

    out = out.reshape(s.shape)
    return np.clip(_M.lab_to_rgb(out) if space == "lab" else out, 0.0, 1.0)


# =========================================================================
# Sinkhorn —— 正則化つき最適輸送
# =========================================================================

def sinkhorn(a, b, cost, reg=0.05, n_iter=2000, tol=1e-9):
    """エントロピー正則化つき最適輸送の計画(Cuturi, NIPS 2013)。

    **厳密解ではない。** ``reg`` を小さくすると厳密解に近づくが、同時に
    数値的に不安定になる(指数がアンダーフローする)。``reg`` を下げると
    厳密解との差が縮むこと自体をテストで固定してある。

    Returns
    -------
    ndarray
        ``(n, m)`` の輸送計画。行和・列和は ``a`` / ``b`` に一致する
        (``tol`` まで)。収束しなければ ``RuntimeError`` ―― 収束しないまま
        最後の反復を返すと、行和が合っていない計画が黙って下流へ流れる。
    """
    a = np.asarray(a, dtype=np.float64).ravel()
    b = np.asarray(b, dtype=np.float64).ravel()
    cost = np.asarray(cost, dtype=np.float64)
    if cost.shape != (a.size, b.size):
        raise MetricContractError(f"cost must be ({a.size}, {b.size}), got {cost.shape}")
    if np.any(a < 0) or np.any(b < 0):
        raise MetricContractError("marginals must be non-negative")
    if not np.isclose(a.sum(), b.sum(), rtol=1e-9, atol=1e-12):
        raise MetricContractError(f"marginals must have equal mass, got {a.sum()!r} and {b.sum()!r}")
    if not np.isfinite(reg) or reg <= 0:
        raise MetricContractError(f"reg must be a positive finite number, got {reg!r}")

    K = np.exp(-cost / reg)
    # 「全体が 0」だけを見るのは弱い。質量のある行/列が 1 つでも全滅すると、
    # その行の質量を運ぶ先が無くなり、割り算の下駄(1e-300)で**でたらめな計画が
    # 黙って返る**。行・列ごとに見るのが正しい検査(2026-09-02 の実測で判明)。
    live_rows = (K > 0).any(axis=1) | (a <= 0)
    live_cols = (K > 0).any(axis=0) | (b <= 0)
    if not (live_rows.all() and live_cols.all()):
        dead = int((~live_rows).sum()) + int((~live_cols).sum())
        raise MetricContractError(
            f"reg={reg!r} is too small for this cost matrix: exp(-cost/reg) underflowed to zero "
            f"for {dead} row(s)/column(s) that still carry mass "
            f"(cost range [{cost.min():.3g}, {cost.max():.3g}]). Their mass has nowhere to go, "
            "so the iteration would return a plan whose marginals are meaningless. "
            "Use a larger reg, or wasserstein_1d for an exact 1-D answer"
        )
    u = np.ones_like(a)
    v = np.ones_like(b)
    for _ in range(int(n_iter)):
        u_prev = u
        v = b / np.maximum(K.T @ u, 1e-300)
        u = a / np.maximum(K @ v, 1e-300)
        if np.max(np.abs(u - u_prev)) < tol:
            break
    else:
        raise MetricContractError(
            f"sinkhorn did not converge in {n_iter} iterations at reg={reg!r} "
            f"(last change {float(np.max(np.abs(u - u_prev))):.3e} > tol={tol!r}); "
            "returning the last iterate would hand on a plan whose marginals do not match"
        )

    plan = u[:, None] * K * v[None, :]
    # **収束したことと、正しい答えに収束したことは別**。reg が小さいと K の大半が
    # アンダーフローし、生き残った少数の要素だけで反復が止まる ―― u は動かなく
    # なるのに、行和・列和は要求した周辺分布から外れたままになる。入力側の検査
    # (行・列に非零があるか)ではここを取りこぼすことを実測で確認したので、
    # 出したものを測ってから返す(2026-09-02)。
    err = max(float(np.max(np.abs(plan.sum(axis=1) - a))),
              float(np.max(np.abs(plan.sum(axis=0) - b))))
    if err > max(1e-6, 1e3 * tol):
        raise MetricContractError(
            f"sinkhorn converged at reg={reg!r} but to a plan whose marginals are off by "
            f"{err:.3e}: exp(-cost/reg) has underflowed for most of the matrix, so the mass "
            "cannot be routed as requested. Use a larger reg, or wasserstein_1d for an exact "
            "1-D answer"
        )
    return plan


def sinkhorn_divergence(a, b, cost, cost_aa=None, cost_bb=None, reg=0.05, **kw):
    """**偏りを打ち消した** Sinkhorn 距離(Genevay, Peyré & Cuturi, AISTATS 2018)。

    ``S(a,b) - (S(a,a) + S(b,b)) / 2``。:func:`sinkhorn_distance` は正則化のぶん
    系統的に上振れし、**自分自身との「距離」が 0 にならない**(実測 reg=0.2 で
    0.05 超)。同じ偏りを自分自身との距離から引くと相殺され、**自分自身との値が
    0 に戻る** ―― TRIZ でいう釣り合い(反作用で打ち消す)そのもの。

    ``cost_aa`` / ``cost_bb`` は ``a`` 同士・``b`` 同士の費用行列。1 点集合を
    自分自身と比べる意味なので、**省略すると ``cost`` が正方のときだけ**
    それを流用する(非正方で省略したら例外 ―― 適当な行列で埋めると、
    引き算する量が別物になり、打ち消したつもりで別の偏りが載る)。
    """
    cost = np.asarray(cost, dtype=np.float64)
    if cost_aa is None or cost_bb is None:
        if cost.shape[0] != cost.shape[1]:
            raise MetricContractError(
                f"cost is {cost.shape}, so cost_aa/cost_bb cannot be inferred from it; "
                "pass them explicitly (reusing a rectangular cost would subtract a quantity "
                "that is not the self-transport bias)"
            )
        # 正方なだけでは自己費用にならない。台が別なら c(x_i, x_i) は 0 でなく、
        # sab と saa/sbb が同じ量になって打ち消しが効き、遠い分布にも 0.0 を
        # 例外なしで返す(実測: 台 [0,1,2] vs [10,11,12] で真値 100 に対し 0.0)。
        # 自己費用の定義的な性質「対角=0」で門を締める。
        d = np.diag(cost)
        if not np.allclose(d, 0.0, atol=1e-12):
            raise MetricContractError(
                f"cost is square but its diagonal is not zero (max |diag| = {np.abs(d).max():g}), "
                "so it is a cost between two different supports and cannot double as the "
                "self-transport cost; reusing it would subtract sab from itself and report ~0 "
                "for distributions that are far apart. Pass cost_aa/cost_bb explicitly"
            )
        cost_aa = cost if cost_aa is None else cost_aa
        cost_bb = cost if cost_bb is None else cost_bb
    sab = sinkhorn_distance(a, b, cost, reg=reg, **kw)
    saa = sinkhorn_distance(a, a, cost_aa, reg=reg, **kw)
    sbb = sinkhorn_distance(b, b, cost_bb, reg=reg, **kw)
    return float(sab - 0.5 * (saa + sbb))


def transport_cost(plan, cost):
    """輸送計画の総費用 ``<plan, cost>``。**計画を消費する**側の op。

    計画は「行和・列和が周辺分布に一致する」という意味を持つ行列で、普通の
    ``matrix`` として扱うと質量保存が黙って壊れる。ここは計画としての検査
    (非負・和が 1 前後)を通してから費用を出す。
    """
    p = np.asarray(plan, dtype=np.float64)
    c = np.asarray(cost, dtype=np.float64)
    if p.shape != c.shape:
        raise MetricContractError(f"plan {p.shape} and cost {c.shape} must have the same shape")
    if np.any(p < -1e-12):
        raise MetricContractError("a transport plan cannot carry negative mass")
    if not np.isfinite(p).all() or not np.isfinite(c).all():
        raise MetricContractError("plan and cost must be finite")
    return float(np.sum(p * c))


def apply_transport(plan, target_values):
    """輸送計画で ``target_values`` を元の点へ引き戻す(重心写像)。

    各行(送り元)について、運んだ質量で重み付けした行き先の値の平均を返す。
    これが「計画を**使って絵を直す**」入口 ―― 計画を作るだけで使い道が無いと、
    :func:`sinkhorn` の出力は台帳の袋小路になる(この repo が繰り返し踏んできた
    「入口はあるが消費 op が無い型」の形)。

    質量ゼロの行は行き先が無い ―― 0 で埋めると「黒い画素」が黙って混ざるので
    ``ValueError``。
    """
    p = np.asarray(plan, dtype=np.float64)
    t = np.asarray(target_values, dtype=np.float64)
    if p.ndim != 2:
        raise MetricContractError(f"plan must be 2-D, got {p.shape}")
    if t.shape[0] != p.shape[1]:
        raise MetricContractError(
            f"target_values must have {p.shape[1]} rows to match the plan's columns, got {t.shape}"
        )
    if np.any(p < -1e-12):
        raise MetricContractError("a transport plan cannot carry negative mass")
    row = p.sum(axis=1)
    dead = int(np.count_nonzero(row <= 1e-15))
    if dead:
        raise MetricContractError(
            f"{dead} row(s) of the plan carry no mass, so those sources have nowhere to map from; "
            "filling them with zeros would quietly blend black into the result"
        )
    weighted = p @ (t if t.ndim > 1 else t[:, None])
    out = weighted / row[:, None]
    return out if t.ndim > 1 else out[:, 0]


def sinkhorn_distance(a, b, cost, reg=0.05, **kw):
    """正則化つき輸送費 ``<plan, cost>``。**厳密な距離ではない**。

    正則化のぶん系統的に偏るので、自分自身との「距離」も 0 にならない
    (そのずれ幅はテストに実測で残してある)。1 次元で厳密が要るときは
    :func:`wasserstein_1d`。
    """
    return float(np.sum(sinkhorn(a, b, cost, reg=reg, **kw) * np.asarray(cost, dtype=np.float64)))


# =========================================================================
# Poisson 合成 —— 出力だけから正しさを確かめられる処理
# =========================================================================

def poisson_blend(src, dst, mask, offset=(0, 0)):
    """勾配場を運ぶ継ぎ目なし合成(Pérez, Gangnet & Blake, SIGGRAPH 2003)。

    ``mask`` の内部で **``src`` の勾配**を保ちつつ、**境界で ``dst`` の値**に
    一致する像を解く。よって出力は次の 2 つを**構成上**満たし、
    それが正しさの検算になる:

    * 内部のラプラシアンが ``src`` のラプラシアンと一致(解の残差ぶんまで)
    * マスクの外は ``dst`` と**厳密に一致**(1 画素も触らない)

    **貼った物の色は変わる。** それが目的の処理だが、「貼った物体の色を測る」
    用途にそのまま流すと**測っているのは貼り先の色**になる。返り値は
    ``(blended, info)`` で、``info["changed_pixels"]`` と
    ``info["max_shift"]`` が実際にどれだけ動いたかを言う。

    Parameters
    ----------
    src : array_like
        貼る絵。``(H, W)`` または ``(H, W, C)``。
    dst : array_like
        貼り先。``src`` 以上の大きさ。
    mask : array_like
        ``src`` と同じ ``(H, W)`` の真偽値。**縁に接していてはいけない**
        (境界条件が取れないため明示的に拒否する)。
    offset : (int, int)
        ``dst`` の中で ``src`` の左上を置く ``(row, col)``。

    Returns
    -------
    (ndarray, dict)
    """
    s = np.asarray(src, dtype=np.float64)
    d = np.asarray(dst, dtype=np.float64)
    m = np.asarray(mask)
    if m.dtype != bool:
        m = m > 0.5
    if s.ndim not in (2, 3) or d.ndim != s.ndim:
        raise MetricContractError(f"src and dst must both be 2-D or both 3-D, got {s.shape} and {d.shape}")
    if m.shape != s.shape[:2]:
        raise MetricContractError(f"mask must be {s.shape[:2]}, got {m.shape}")
    if not m.any():
        raise MetricContractError("mask selects no pixels; there is nothing to blend")
    if m[0, :].any() or m[-1, :].any() or m[:, 0].any() or m[:, -1].any():
        raise MetricContractError(
            "mask touches the edge of src, so the Dirichlet boundary has no ring of dst pixels "
            "to sit on; erode the mask or pad src (silently clamping would solve a different "
            "problem than the one asked for)"
        )
    r0, c0 = (int(offset[0]), int(offset[1]))
    h, w = s.shape[:2]
    if r0 < 0 or c0 < 0 or r0 + h > d.shape[0] or c0 + w > d.shape[1]:
        raise MetricContractError(
            f"src at offset {(r0, c0)} with shape {(h, w)} does not fit inside dst {d.shape[:2]}"
        )
    if not (np.all(np.isfinite(s)) and np.all(np.isfinite(d))):
        raise MetricContractError("src and dst must be finite")

    idx = -np.ones((h, w), dtype=np.int64)
    ys, xs = np.nonzero(m)
    idx[ys, xs] = np.arange(ys.size)
    n = ys.size

    rows, cols, vals = [], [], []
    rows.append(np.arange(n)); cols.append(np.arange(n)); vals.append(np.full(n, 4.0))
    neighbours = []
    for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        ny, nx = ys + dy, xs + dx
        nid = idx[ny, nx]
        inside = nid >= 0
        rows.append(np.arange(n)[inside]); cols.append(nid[inside]); vals.append(np.full(inside.sum(), -1.0))
        neighbours.append((ny, nx, inside))
    A = sparse.csr_matrix(
        (np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n))
    lu = sparse_linalg.splu(A.tocsc())

    out = d.copy()
    planes = [(s, d, out)] if s.ndim == 2 else [
        (s[..., c], d[..., c], out[..., c]) for c in range(s.shape[2])]
    residual = 0.0
    for sp, dp, op in planes:
        lap = 4.0 * sp[ys, xs] - sum(sp[ny, nx] for ny, nx, _ in neighbours)
        rhs = lap.copy()
        for (ny, nx, inside) in neighbours:                 # 境界は dst の値を右辺へ
            outside = ~inside
            rhs[outside] += dp[r0 + ny[outside], c0 + nx[outside]]
        x = lu.solve(rhs)
        # 解いた線形系の残差を実際に測る(解けたつもりの値を返さないため)
        residual = max(residual, float(np.max(np.abs(A @ x - rhs))))
        op[r0 + ys, c0 + xs] = x

    before = d[r0:r0 + h, c0:c0 + w]
    after = out[r0:r0 + h, c0:c0 + w]
    diff = np.abs(after - before)
    return out, {
        "changed_pixels": int(np.count_nonzero(diff > 1e-12)),
        "max_shift": float(diff.max()),
        "solved_pixels": n,
        "residual": residual,
    }


if __name__ == "__main__":     # pragma: no cover - 手元確認用
    rng = np.random.default_rng(0)
    a = rng.normal(0.0, 1.0, 400)
    b = rng.normal(2.0, 3.0, 400)
    w2 = wasserstein_1d(a, b, p=2)
    closed = np.hypot(a.mean() - b.mean(), a.std() - b.std())
    print(f"W2 実測 {w2:.6f} / ガウスの閉形式 {closed:.6f} / 差 {abs(w2 - closed):.3e}")
