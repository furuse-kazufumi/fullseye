# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""llmcore —— 大規模言語モデルに至る系譜の芯を、**恒等式が立つものだけ**アルゴリズムとして持つ。

系譜(状態機械 → RNN → Attention → Transformer)に出てくる仕組みのうち、この族に入れたのは
**厳密な等式・保存量・整数不変量が立つもの**に限る。「それらしく動く」は入れていない ——
蒸留も Sampler も Perplexity も、真値が無いのでこの箱の外。

なぜ画像の箱に入っているか: **注意はパッチ列の上の演算**で、画像を格子に切れば
そのまま ViT の入口になる。この族の op は ``tokens``(T, d)を受けて ``tokens`` か
``attnmap``(T, T)を返すだけなので、トークンが単語だろうが画素パッチだろうが同じ式で動く。

立つ恒等式(すべて実測。単位は相対差):

* ``attention_weights`` の**行和は 1**(2.2e-16)、mask 位置は**厳密に 0**(0.0e+00)。
* ``attention_tiled``(FlashAttention の芯)は**近似ではない** —— タイル + online softmax は
  一括と一致する(タイル 128 枚でも 1.2e-15)。速いのは計算を変えたからでなく、
  (T, T) の行列を**作らない**から。
* ``attention_linear`` は**結合則そのもの** —— (QKᵀ)V == Q(KᵀV)(7.1e-16)。
  O(T²d) と O(Td²) は同じ数の別の括り方で、交差点は **T == d**。
* ``rope_rotate`` は**回転なのでノルムを保ち**(8.9e-16)、内積は**相対位置だけ**で決まる
  (絶対位置を 40 通り動かして幅 8.9e-15)。
* 因果マスクの下では、**未来のトークンを書き換えても前の出力が 1 ビットも動かない**
  (0.0e+00)—— KV Cache が成り立つ理由そのもの。
* ``attention_grouped`` は ``n_kv_heads == n_heads`` で MHA と、``== 1`` で MQA と
  **厳密に一致**する(どちらも 0.0e+00)。
* ``rms_norm`` の出力の **RMS は厳密に 1**(2.2e-16)。
* 位置符号が無ければ注意は**置換同変** —— パッチを並べ替えて戻すと元に戻る(4.4e-16)。
  RoPE を入れると壊れる(3.4e-02)。**それが位置符号の仕事**。

型は 2 つだけ足した。``tokens`` =(T, d)の実数列(**軸の順が意味を持つ** —— 転置しても
形が通ってしまい、例外ではなくもっともらしく間違った数が出る)、``attnmap`` =(T, T)の
注意行列(生のスコアと softmax 後の重みの両方)。numpy だけで動く ——
**torch は使わない**(任意依存を要る op は CI の一部の Python にしか入らない)。
"""
from __future__ import annotations

from typing import Any

import numpy as np

__all__ = [
    "rms_norm", "rope_rotate",
    "attention_scores", "attention_weights", "attention_apply",
    "attention_softmax", "attention_tiled", "attention_linear", "attention_grouped",
    "kv_cache_decode",
    "MAX_TOKENS", "MASK_KINDS", "ROPE_BASE",
]

#: 1 回で扱う列の長さの上限。(T, T) を作る op があるので T² が効く(4096² = 1.6 千万)。
MAX_TOKENS = 4096
#: ``mask`` に渡せる語。``None`` = 全対、``"causal"`` = 下三角、``"window"`` = 幅 ``window`` の因果窓。
MASK_KINDS = ("causal", "window")
#: RoPE の既定の底(Su ら 2021 の 10000)。
ROPE_BASE = 10000.0


# --------------------------------------------------------------------------- #
# 入口の検査 —— どの例外も op 名を名乗る                                         #
# --------------------------------------------------------------------------- #
def _tokens(x: Any, op: str, name: str, width: int | None = None) -> np.ndarray:
    a = np.asarray(x, dtype=np.float64)
    if a.ndim != 2 or a.size == 0:
        raise ValueError("%s: %s must be a non-empty 2-D token array (T, d), got shape %r"
                         % (op, name, a.shape))
    if a.shape[0] > MAX_TOKENS:
        raise ValueError("%s: %s has T=%d > MAX_TOKENS=%d; split the sequence"
                         % (op, name, a.shape[0], MAX_TOKENS))
    if not np.isfinite(a).all():
        raise ValueError("%s: %s must be finite (NaN/Inf would spread through the softmax)"
                         % (op, name))
    if width is not None and a.shape[1] != width:
        raise ValueError("%s: %s has width %d but %d was expected"
                         % (op, name, a.shape[1], width))
    return a


def _square(x: Any, op: str, name: str) -> np.ndarray:
    a = np.asarray(x, dtype=np.float64)
    if a.ndim != 2 or a.shape[0] != a.shape[1] or a.size == 0:
        raise ValueError("%s: %s must be a non-empty square (T, T) attention matrix, got shape %r"
                         % (op, name, a.shape))
    if not np.isfinite(a).all():
        raise ValueError("%s: %s must be finite" % (op, name))
    return a


def _positive_int(v: Any, op: str, name: str, lo: int = 1) -> int:
    try:
        n = int(v)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be an integer, got %r" % (op, name, v)) from None
    if n != v or n < lo:
        raise ValueError("%s: %s must be an integer >= %d, got %r" % (op, name, lo, v))
    return n


def _finite(v: Any, op: str, name: str, lo=None) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a real number, got %r" % (op, name, v)) from None
    if not np.isfinite(f):
        raise ValueError("%s: %s must be finite, got %r" % (op, name, v))
    if lo is not None and f < lo:
        raise ValueError("%s: %s must be >= %g, got %g" % (op, name, lo, f))
    return f


def _mask_array(kind, t: int, window, op: str):
    """``mask`` の語 → (T, T) の bool。``None`` なら ``None`` を返す(全対)。"""
    if kind is None:
        return None
    if isinstance(kind, str):
        if kind not in MASK_KINDS:
            raise ValueError("%s: mask must be None or one of %s, got %r"
                             % (op, ", ".join(repr(k) for k in MASK_KINDS), kind))
        if kind == "causal":
            return np.tril(np.ones((t, t), dtype=bool))
        w = _positive_int(window, op, "window")
        i = np.arange(t)[:, None]
        j = np.arange(t)[None, :]
        return (j <= i) & (j > i - w)
    m = np.asarray(kind)
    if m.dtype != bool or m.shape != (t, t):
        raise ValueError("%s: an explicit mask must be a bool array of shape (%d, %d), got %r %s"
                         % (op, t, t, m.shape, m.dtype))
    if not m.any(axis=1).all():
        raise ValueError("%s: every row of the mask must keep at least one column "
                         "(a fully masked row has no softmax)" % op)
    return m


# --------------------------------------------------------------------------- #
# 前処理 —— 正規化と位置符号                                                     #
# --------------------------------------------------------------------------- #
def rms_norm(tokens, eps: float = 0.0, weight=None) -> np.ndarray:
    """RMS 正規化 → tokens。**既定(eps=0, weight なし)では出力の RMS が厳密に 1**。

    Zhang・Sennrich 2019。LayerNorm から平均を引く段を落としたもので、残るのは
    「行のノルムを揃える」だけ —— だから **RMS が 1 になることが検算になる**
    (実測 2.2e-16)。``eps`` を入れると 1 からずれる。それが ``eps`` の値段。

    Args:
        tokens: (T, d) float。1 行が 1 トークン。
        eps: 平方根の中に足す下駄。0 なら RMS は厳密に 1、正なら 1 未満に縮む。
        weight: (d,) float か None。学習で付く軸ごとの倍率(掛けるだけなので RMS は動く)。
    Returns:
        tokens (T, d) float: 各行を自分の RMS で割ったもの(``weight`` があれば掛けたもの)。
        **全成分が 0 の行**は割れないので ValueError(黙って 0/0 の NaN を返さない)。
    """
    op = "rms_norm"
    a = _tokens(tokens, op, "tokens")
    e = _finite(eps, op, "eps", lo=0.0)
    r = np.sqrt(np.mean(a * a, axis=-1, keepdims=True) + e)
    if not (r > 0).all():
        raise ValueError("%s: %d row(s) are all-zero and have no RMS; pass eps > 0 to allow them"
                         % (op, int((r <= 0).sum())))
    y = a / r
    if weight is None:
        return y
    w = np.asarray(weight, dtype=np.float64)
    if w.shape != (a.shape[1],) or not np.isfinite(w).all():
        raise ValueError("%s: weight must be a finite array of shape (%d,), got %r"
                         % (op, a.shape[1], w.shape))
    return y * w


def rope_rotate(tokens, positions=None, base: float = ROPE_BASE) -> np.ndarray:
    """回転による位置符号(RoPE)→ tokens。**回転なのでノルムを保つ**。

    Su ら 2021。偶奇の対 (x₂ᵢ, x₂ᵢ₊₁) を角度 ``pos · base**(−2i/d)`` だけ回す。
    平面回転の直和なので ``‖RoPE(x)‖ == ‖x‖`` が**厳密に**成り立ち(実測 8.9e-16)、
    しかも回した 2 本の内積は**位置の差だけ**で決まる(絶対位置を 40 通り動かして幅 8.9e-15)
    —— 「相対位置を内積に埋める」という主張が、そのまま検算になる。

    Args:
        tokens: (T, d) float。**d は偶数**(対にして回すため)。
        positions: (T,) の位置。None なら 0..T−1。飛び飛びの位置(切り出した窓)も渡せる。
        base: 角度の底。大きいほど低い軸がゆっくり回る(長い文脈向け)。
    Returns:
        tokens (T, d) float: 対ごとに回したもの。行ごとのノルムは入力と同じ。
    """
    op = "rope_rotate"
    a = _tokens(tokens, op, "tokens")
    t, d = a.shape
    if d % 2:
        raise ValueError("%s: d must be even to rotate pairs, got d=%d" % (op, d))
    b = _finite(base, op, "base", lo=1.0 + 1e-12)
    if positions is None:
        pos = np.arange(t, dtype=np.float64)
    else:
        pos = np.asarray(positions, dtype=np.float64)
        if pos.shape != (t,) or not np.isfinite(pos).all():
            raise ValueError("%s: positions must be a finite array of shape (%d,), got %r"
                             % (op, t, pos.shape))
    i = np.arange(d // 2, dtype=np.float64)[None, :]
    theta = pos[:, None] * (b ** (-2.0 * i / d))
    c, s = np.cos(theta), np.sin(theta)
    xe, xo = a[:, 0::2], a[:, 1::2]
    out = np.empty_like(a)
    out[:, 0::2] = xe * c - xo * s
    out[:, 1::2] = xe * s + xo * c
    return out


# --------------------------------------------------------------------------- #
# 注意 —— 3 段に分けたもの                                                       #
# --------------------------------------------------------------------------- #
def attention_scores(query, key, scale=None) -> np.ndarray:
    """生の注意スコア QKᵀ/√d → attnmap (T, S)。

    Args:
        query: (T, d) float。問い合わせる側。
        key: (S, d) float。引かれる側。d は query と同じ。
        scale: スコアの倍率。None なら 1/√d(Vaswani ら 2017 —— 内積が d に比例して
            育ち softmax が尖るのを打ち消す)。
    Returns:
        attnmap (T, S) float: softmax にかける前の生のスコア。
    """
    op = "attention_scores"
    q = _tokens(query, op, "query")
    k = _tokens(key, op, "key", width=q.shape[1])
    sc = 1.0 / np.sqrt(q.shape[1]) if scale is None else _finite(scale, op, "scale")
    return (q @ k.T) * sc


def attention_weights(scores, mask=None, window=None) -> np.ndarray:
    """行ごとの softmax(マスクつき)→ attnmap。**行和は 1、mask 位置は厳密に 0**。

    行ごとに最大値を引いてから指数を取る。これは飾りではない —— 引かずに ``exp`` すると
    スコアが大きいとき**全行が inf/NaN になる**(実測: 96 行中 96 行)。引けば 0 行。

    Args:
        scores: (T, T) float の生スコア(``attention_scores`` の出力)。
        mask: None(全対)/ ``"causal"``(下三角)/ ``"window"``(幅 ``window`` の因果窓)/
            (T, T) の bool 配列。True が「見てよい」。
        window: ``mask="window"`` のときの窓幅(自分を含む個数)。
    Returns:
        attnmap (T, T) float: 各行が確率分布(和 1)。mask が False の位置は厳密に 0。
    """
    op = "attention_weights"
    s = _square(scores, op, "scores")
    m = _mask_array(mask, s.shape[0], window, op)
    if m is not None:
        s = np.where(m, s, -np.inf)
    mx = np.max(s, axis=-1, keepdims=True)
    mx = np.where(np.isfinite(mx), mx, 0.0)
    e = np.exp(s - mx)
    return e / np.sum(e, axis=-1, keepdims=True)


def attention_apply(weights, value) -> np.ndarray:
    """注意の重みで値を混ぜる → tokens。**行和 1 なので出力は入力の凸結合**。

    Args:
        weights: (T, S) float。行和が 1 であること(``attention_weights`` の出力)。
        value: (S, dv) float。混ぜられる側。
    Returns:
        tokens (T, dv) float: 各行が value の行の凸結合。**値域は value を出ない**
        (同時に幅は縮む —— 平均は対比を潰す)。
    """
    op = "attention_apply"
    w = np.asarray(weights, dtype=np.float64)
    if w.ndim != 2 or w.size == 0 or not np.isfinite(w).all():
        raise ValueError("%s: weights must be a finite non-empty 2-D array, got shape %r"
                         % (op, w.shape))
    if w.min() < 0.0:
        raise ValueError("%s: weights must be non-negative (row %d has %g)"
                         % (op, int(np.argmin(w.min(axis=1))), float(w.min())))
    bad = float(np.max(np.abs(w.sum(axis=1) - 1.0)))
    if bad > 1e-9:
        raise ValueError("%s: every row of weights must sum to 1 (worst row is off by %.3g); "
                         "pass the output of attention_weights" % (op, bad))
    v = _tokens(value, op, "value")
    if v.shape[0] != w.shape[1]:
        raise ValueError("%s: weights has %d columns but value has %d rows"
                         % (op, w.shape[1], v.shape[0]))
    return w @ v


def attention_softmax(query, key, value, mask=None, window=None, scale=None) -> np.ndarray:
    """一括の注意(参照実装)→ tokens。**この族の答え合わせの基準**。

    (T, T) のスコア行列を実際に作ってから softmax する、いちばん素直な書き方。
    ``attention_tiled`` / ``attention_linear`` / ``attention_grouped`` はこれと
    一致することで正しさを示す。

    Args:
        query: (T, d) float。
        key: (S, d) float。
        value: (S, dv) float。
        mask: None / ``"causal"`` / ``"window"`` / (T, S) の bool 配列。
        window: ``mask="window"`` のときの窓幅。
        scale: スコアの倍率。None なら 1/√d。
    Returns:
        tokens (T, dv) float: 注意で混ぜた列。
    """
    op = "attention_softmax"
    q = _tokens(query, op, "query")
    k = _tokens(key, op, "key", width=q.shape[1])
    v = _tokens(value, op, "value")
    if v.shape[0] != k.shape[0]:
        raise ValueError("%s: key has %d rows but value has %d" % (op, k.shape[0], v.shape[0]))
    sc = 1.0 / np.sqrt(q.shape[1]) if scale is None else _finite(scale, op, "scale")
    s = (q @ k.T) * sc
    m = _mask_rect(mask, q.shape[0], k.shape[0], window, op)
    if m is not None:
        s = np.where(m, s, -np.inf)
    mx = np.max(s, axis=-1, keepdims=True)
    mx = np.where(np.isfinite(mx), mx, 0.0)
    e = np.exp(s - mx)
    return (e / np.sum(e, axis=-1, keepdims=True)) @ v


def _mask_rect(kind, t: int, s: int, window, op: str):
    """(T, S) の mask。T == S のときだけ語("causal" / "window")を許す。"""
    if kind is None:
        return None
    if isinstance(kind, str):
        if t != s:
            raise ValueError("%s: mask=%r needs a square problem (T=%d, S=%d); "
                             "pass an explicit bool array instead" % (op, kind, t, s))
        return _mask_array(kind, t, window, op)
    m = np.asarray(kind)
    if m.dtype != bool or m.shape != (t, s):
        raise ValueError("%s: an explicit mask must be a bool array of shape (%d, %d), got %r %s"
                         % (op, t, s, m.shape, m.dtype))
    if not m.any(axis=1).all():
        raise ValueError("%s: every row of the mask must keep at least one column" % op)
    return m


def attention_tiled(query, key, value, tile: int = 64, mask=None, window=None,
                    scale=None) -> np.ndarray:
    """タイル + online softmax の注意(FlashAttention の芯)→ tokens。**近似ではない**。

    Dao ら 2022。key/value を ``tile`` 行ずつ読み、走っている最大値と分母をその場で
    補正しながら足す。作る中間行列は (T, ``tile``) だけで、**(T, T) を一度も作らない** ——
    速さの出どころは近似ではなく、置き場所。``attention_softmax`` との相対差は
    タイル 128 枚でも **1.2e-15**(タイル 1 枚で 8.2e-16 なので、枚数を 128 倍しても 1.5 倍)。

    Args:
        query: (T, d) float。
        key: (S, d) float。
        value: (S, dv) float。
        tile: 一度に読む key/value の行数。小さいほど中間行列が小さく、枚数が増える。
        mask: None / ``"causal"`` / ``"window"`` / (T, S) の bool 配列。
        window: ``mask="window"`` のときの窓幅。
        scale: スコアの倍率。None なら 1/√d。
    Returns:
        tokens (T, dv) float: ``attention_softmax`` と機械精度で一致する。
    """
    op = "attention_tiled"
    q = _tokens(query, op, "query")
    k = _tokens(key, op, "key", width=q.shape[1])
    v = _tokens(value, op, "value")
    if v.shape[0] != k.shape[0]:
        raise ValueError("%s: key has %d rows but value has %d" % (op, k.shape[0], v.shape[0]))
    tl = _positive_int(tile, op, "tile")
    sc = 1.0 / np.sqrt(q.shape[1]) if scale is None else _finite(scale, op, "scale")
    m = _mask_rect(mask, q.shape[0], k.shape[0], window, op)
    t = q.shape[0]
    run_max = np.full(t, -np.inf)
    run_sum = np.zeros(t)
    acc = np.zeros((t, v.shape[1]))
    for j0 in range(0, k.shape[0], tl):
        j1 = min(j0 + tl, k.shape[0])
        s = (q @ k[j0:j1].T) * sc
        if m is not None:
            s = np.where(m[:, j0:j1], s, -np.inf)
        blk = np.max(s, axis=1)
        new_max = np.maximum(run_max, blk)
        safe = np.where(np.isfinite(new_max), new_max, 0.0)
        corr = np.where(np.isfinite(run_max), np.exp(np.where(np.isfinite(run_max), run_max, 0.0) - safe), 0.0)
        e = np.where(np.isfinite(s), np.exp(s - safe[:, None]), 0.0)
        acc = acc * corr[:, None] + e @ v[j0:j1]
        run_sum = run_sum * corr + np.sum(e, axis=1)
        run_max = new_max
    if not (run_sum > 0).all():
        raise ValueError("%s: %d row(s) had every column masked" % (op, int((run_sum <= 0).sum())))
    return acc / run_sum[:, None]


def attention_linear(query, key, value, causal: bool = False) -> np.ndarray:
    """softmax を外した注意 → tokens。**(QKᵀ)V == Q(KᵀV) —— 結合則そのもの**。

    Katharopoulos ら 2020。softmax を外すと行列積の結合則が使え、(T, T) を作らずに
    (d, dv) の状態だけで足りる。**同じ数の別の括り方**なので答えは一致し(相対差 7.1e-16)、
    計算量は O(T²d) から O(Td²) に移る —— 交差点は **T == d**(実測: T=d=64 で比 0.9、
    T=1024 で 14.6 倍)。★T を 2048 にしても比は 14.4 で頭打ちになる。式が言う 32 倍には
    届かない —— 二次の側が帯域律速に入るから。

    Args:
        query: (T, d) float。
        key: (S, d) float。
        value: (S, dv) float。``causal=True`` では S == T。
        causal: True なら「自分より前だけ」を累積状態で足す(逐次 1 回で線形時間)。
    Returns:
        tokens (T, dv) float: **softmax を通していない**ので行和 1 の凸結合ではない。
        ``attention_softmax`` の代わりではなく、**別の注意**。
    """
    op = "attention_linear"
    q = _tokens(query, op, "query")
    k = _tokens(key, op, "key", width=q.shape[1])
    v = _tokens(value, op, "value")
    if v.shape[0] != k.shape[0]:
        raise ValueError("%s: key has %d rows but value has %d" % (op, k.shape[0], v.shape[0]))
    if not isinstance(causal, (bool, np.bool_)):
        raise ValueError("%s: causal must be a bool, got %r" % (op, causal))
    if not causal:
        return q @ (k.T @ v)
    if k.shape[0] != q.shape[0]:
        raise ValueError("%s: causal=True needs key/value as long as query (%d vs %d)"
                         % (op, k.shape[0], q.shape[0]))
    out = np.zeros((q.shape[0], v.shape[1]))
    state = np.zeros((k.shape[1], v.shape[1]))
    for i in range(q.shape[0]):
        state = state + np.outer(k[i], v[i])
        out[i] = q[i] @ state
    return out


def attention_grouped(query, key, value, n_heads: int, n_kv_heads: int,
                      mask=None, window=None) -> np.ndarray:
    """頭を束ねる注意(GQA)→ tokens。**n_kv_heads == n_heads で MHA、== 1 で MQA に厳密一致**。

    Ainslie ら 2023。query は ``n_heads`` 本に割り、key/value は ``n_kv_heads`` 本しか
    持たずに使い回す。両端が既存の 2 つ(MHA / MQA)に**厳密に**落ちる(どちらも 0.0e+00)
    ので、「中間を取る」という主張が端で検算できる。

    Args:
        query: (T, n_heads·dh) float。頭ごとに幅 dh で並んでいる。
        key: (S, n_kv_heads·dh) float。
        value: (S, n_kv_heads·dh) float。
        n_heads: query の頭の数。``n_kv_heads`` の倍数であること。
        n_kv_heads: key/value の頭の数。1 なら MQA、``n_heads`` なら MHA。
        mask: None / ``"causal"`` / ``"window"`` / (T, S) の bool 配列。
        window: ``mask="window"`` のときの窓幅。
    Returns:
        tokens (T, n_heads·dh) float: 頭ごとの出力を横に連結したもの。
    """
    op = "attention_grouped"
    q = _tokens(query, op, "query")
    k = _tokens(key, op, "key")
    v = _tokens(value, op, "value")
    nh = _positive_int(n_heads, op, "n_heads")
    nkv = _positive_int(n_kv_heads, op, "n_kv_heads")
    if nh % nkv:
        raise ValueError("%s: n_heads=%d must be a multiple of n_kv_heads=%d" % (op, nh, nkv))
    if q.shape[1] % nh:
        raise ValueError("%s: query width %d is not divisible by n_heads=%d" % (op, q.shape[1], nh))
    dh = q.shape[1] // nh
    if k.shape[1] != nkv * dh or v.shape[1] != nkv * dh:
        raise ValueError("%s: key/value width must be n_kv_heads*dh = %d, got %d / %d"
                         % (op, nkv * dh, k.shape[1], v.shape[1]))
    if k.shape[0] != v.shape[0]:
        raise ValueError("%s: key has %d rows but value has %d" % (op, k.shape[0], v.shape[0]))
    rep = nh // nkv
    outs = []
    for h in range(nh):
        g = h // rep
        outs.append(attention_softmax(q[:, h * dh:(h + 1) * dh],
                                      k[:, g * dh:(g + 1) * dh],
                                      v[:, g * dh:(g + 1) * dh], mask, window))
    return np.concatenate(outs, axis=1)


def kv_cache_decode(query_step, key_cache, value_cache, scale=None) -> np.ndarray:
    """1 トークン分だけ進める推論(KV Cache)→ tokens (1, dv)。

    因果マスクの下では**未来を書き換えても前の出力が 1 ビットも動かない**(実測 0.0e+00)
    ので、済んだ key/value を取っておいて 1 行だけ計算すればよい —— 逐次に 1 行ずつ
    進めた結果は、全系列を一括で通した結果と一致する(相対差 1.6e-16)。
    計算量は 1 歩あたり O(T d) で、一括の O(T² d) を T 歩に割ったものに等しい。

    Args:
        query_step: (1, d) float。いま生成しようとしている 1 トークン。
        key_cache: (T, d) float。ここまでに見た key(自分を含む)。
        value_cache: (T, dv) float。同じ長さの value。
        scale: スコアの倍率。None なら 1/√d。
    Returns:
        tokens (1, dv) float: 一括で通した最終行と一致する。
    """
    op = "kv_cache_decode"
    q = _tokens(query_step, op, "query_step")
    if q.shape[0] != 1:
        raise ValueError("%s: query_step must be exactly one token, got %d rows" % (op, q.shape[0]))
    k = _tokens(key_cache, op, "key_cache", width=q.shape[1])
    v = _tokens(value_cache, op, "value_cache")
    if v.shape[0] != k.shape[0]:
        raise ValueError("%s: key_cache has %d rows but value_cache has %d"
                         % (op, k.shape[0], v.shape[0]))
    return attention_softmax(q, k, v, scale=scale)
