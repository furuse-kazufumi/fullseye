# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""順序に依らない FP64 の行列積(Ozaki スキーム)—— 点の順・BLAS のスレッド数に依らずビット単位で同じ答え、誤差は上界つき(2026-10-05)。

点群の相互共分散 ``H = Pᵀ Q``、正規方程式の ``JᵀJ`` のように、内側の次元(点の数)が長く出力が 3×3 / 6×6 と小さい縮約は、
普通の FP64 の行列積(DGEMM)だと **足す順で下位ビットが動く**。点の順を入れ替える・BLAS のスレッド数を変える・別の BLAS に
替えるだけで、Kabsch の回転が 1e-15 級で別の値になる。この module はその縮約を **正確な整数の部分積** に分けて計算し、
順序の入る余地をなくす。

方式(読んだ文献は RAD の Ozaki スキームのコーパス。式の出典は各関数の docstring):

- **Ozaki-I**(Ozaki, Ogita, Oishi, Rump 2012 の誤差なし変換を行列積に使う系統。ここでは ozIMMU 型の固定小数点の切り出し、
  Uchino, Ozaki, Imamura 2023 = arXiv 2306.11975): A の行・B の列ごとに 2 の冪の指数を 1 つ共有させ、7 ビットずつの整数の
  切れ端に分ける。切れ端どうしの積は float32 の BLAS で計算しても **整数として正確**(1 ブロック 1040 項までの和が 2²⁴ 未満)。
  ブロックの和は float64 で 2⁵³ 未満の整数なので、これも正確。最後の組み立てだけが丸めで、その順序は固定。
- **Ozaki-II**(Ozaki, Uchino, Imamura 2025 = arXiv 2504.08009): 整数に拡大して法 m ≤ 256 の剰余で掛け、中国剰余定理で戻す。
  拡大の指数は行・列の 2-ノルムから決める(Cauchy–Schwarz)ので、**入力を定数倍しても壊れない** —— Kawakami, Takahashi 2026
  (arXiv 2606.29129)が報告した fast mode の欠陥(定数倍 c ≤ 2⁻² で相対誤差 約 1)はこの式では起きない(門がある)。

使い分け(手元の実測。数字は RAD コーパスのベンダー資料のノート末尾の自前の測定表と、この module の PoC の記録):

- **CPU で速くはならない**。Ozaki-I は DGEMM の 15〜83 倍遅い(正方行列 n = 256〜2048、OpenBLAS 0.3.31、24 スレッド)。
  点群の 3×3 の縮約(20 万点)では 1 ms 未満が 100〜300 ms になる。効くのは **ビット単位の再現性と精度の保証** だけ。
- **GPU で FP64 を速くしたいなら、自前の実装より cuBLAS 13.4 の FP64 エミュレーション**(opt-in: math mode
  ``CUBLAS_FP64_EMULATED_FIXEDPOINT_MATH``、またはコードを変えずに環境変数 ``CUBLAS_EMULATE_DOUBLE_PRECISION=1``)。
  手元の GPU(RTX 5090)の n = 8192 で 17.8〜23.8 TFLOPS、ネイティブの FP64 は 1.67。cuBLAS 13.3 は指数の幅が広い入力
  (φ ≥ 2)でネイティブへ戻った。:func:`fp64_emulation_probe` で使えるかを確かめられる。
- ただし cuBLAS の文書(Results Reproducibility の節)は、エミュレーションを使うと「同じ版・同じ GPU ならビット単位で同じ」
  の保証が **外れる** と書く。**速さは cuBLAS、ビット単位の再現はこの module**、と分ける。
- **距離行列には使わない**。原点から遠い点群の float32 の距離の取り違えは、重心を引くだけで消える(PoC の記録)。

再現性の約束(門がある): 同じ入力なら、内側の添字の並べ替え(点の順)・BLAS のスレッド数・内部のブロック幅に依らず
**同じビット**。分割数を自動で選ぶ :func:`matmul_reproducible` は、選択に使う量(行・列の最大の指数、並べ替えた和、
|A||B| の下界)も全部この約束を満たすように作ってある(float32 の BLAS で |A||B| を見積もると、境目で分割数が入れ替わる)。
出力の行を分けて呼ぶと、分けた側ごとに分割数が選び直されるので、行を分けるなら ``n_slices`` を固定して :func:`matmul_ozaki` を使う。
特異値分解など、この後に続く LAPACK の計算は同じ計算機の上でだけ同じビット(:func:`kabsch_reproducible`)。

ICP の家族(registration.icp / registration.point_to_plane_icp / match3d.icp_point2point_3d / match3d.icp_point2plane /
gicp.gicp)は引数 ``reproducible=True`` でこの module の縮約を使う(既定は従来の経路のまま。2 万点の ICP 全体で 2〜5 倍遅い)。

限界: Inf / NaN は扱わない(``ValueError``)。符号付きのゼロは保たない。指数の幅が広い入力(φ = 4)は FP64 並みの精度に
12〜13 枚(78〜91 回の積)が要る。出力が溢れたら ``ValueError``。
"""
from __future__ import annotations

import ctypes
import glob
import math
import os
import re
import sys

import numpy as np

__all__ = [
    "matmul_ozaki", "matmul_reproducible", "ozaki_error_bound",
    "cross_covariance_reproducible", "kabsch_reproducible", "fp64_emulation_probe",
]

#: Ozaki-II の法(int8 の剰余で掛けられる、互いに素な m ≤ 256。Ozaki, Uchino, Imamura 2025 の式 (19))。
_INT8_MODULI = (256, 255, 253, 251, 247, 239, 233, 229, 227, 223,
                217, 211, 199, 197, 193, 191, 181, 179, 173, 167)
_BITS = 7                       # 切れ端 1 枚のビット数(int8 に入る)
_FP32_EXACT = 2 ** 24           # float32 で正確に足せる整数の上限
_KB = (_FP32_EXACT - 1) // (2 ** _BITS - 1) ** 2      # 1040: |切れ端| ≤ 127 のブロック内の和が 2²⁴ 未満
_KB2 = (_FP32_EXACT - 1) // 128 ** 2                 # 1023: Ozaki-II の対称な剰余は -128..127
_MAX_SLICES = 16
_STACK_LIMIT = 512             # 切れ端を積んで 1 回で掛ける出力の大きさの上限(行 × 枚数、列 × 枚数)
_SCHEMES = ("ozaki1", "ozaki2")


# ----------------------------------------------------------------------------------------------
# 検査(fail-closed)
# ----------------------------------------------------------------------------------------------
def _check_pair(A, B, who):
    try:
        A = np.asarray(A, dtype=np.float64)
        B = np.asarray(B, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError("%s: A and B must be numeric 2-D arrays" % who) from exc
    if A.ndim != 2 or B.ndim != 2:
        raise ValueError("%s: need 2-D operands, got %d-D and %d-D" % (who, A.ndim, B.ndim))
    if A.shape[1] != B.shape[0]:
        raise ValueError("%s: inner dimensions differ: %r @ %r" % (who, A.shape, B.shape))
    if A.size == 0 or B.size == 0:
        raise ValueError("%s: empty operand %r @ %r" % (who, A.shape, B.shape))
    if not (np.isfinite(A).all() and np.isfinite(B).all()):
        raise ValueError("%s: non-finite input (the emulation does not carry Inf / NaN)" % who)
    return A, B


def _count(v, name, lo, hi):
    if isinstance(v, bool) or not isinstance(v, (int, np.integer)) or not lo <= int(v) <= hi:
        raise ValueError("%s must be an int in %d..%d, got %r" % (name, lo, hi, v))
    return int(v)


def _tol(tol):
    if isinstance(tol, bool):
        raise ValueError("tol must be a number in (0, 1), got %r" % (tol,))
    try:
        t = float(tol)
    except (TypeError, ValueError) as exc:
        raise ValueError("tol must be a number in (0, 1), got %r" % (tol,)) from exc
    if not (0.0 < t < 1.0):
        raise ValueError("tol must be a number in (0, 1), got %r" % (tol,))
    return t


def _finite_out(C, who):
    if not np.isfinite(C).all():
        raise ValueError("%s: the product overflows float64" % who)
    return C


# ----------------------------------------------------------------------------------------------
# 正確な整数の積(float32 の BLAS を整数の計算機として使う)
# ----------------------------------------------------------------------------------------------
def _exact_int_product(X, Y, kb=_KB):
    """整数値の X (m, k)・Y (k, n)(|要素| ≤ 127、``kb=_KB2`` なら ≤ 128)の積を **正確に** 返す(float64)。

    内側を ``kb`` 項(既定 1040)ずつのブロックに切り、ブロックごとに float32 の BLAS で掛ける。ブロック内の部分和はどの順で足しても
    2²⁴ 未満の整数なので正確。ブロックの結果(整数)を float64 で足すのも 2⁵³ 未満なので正確 —— だから **ブロックの順も、
    BLAS が内部でどう足すかも結果に入らない**。ブロックはまとめて batched matmul に渡す(Python の繰り返しを避ける)。
    """
    m, k = X.shape
    n = Y.shape[1]
    X32 = X if X.dtype == np.float32 else X.astype(np.float32)     # 切れ端は最初から float32 で持つ
    Y32 = Y if Y.dtype == np.float32 else Y.astype(np.float32)
    if k <= kb:
        return (X32 @ Y32).astype(np.float64)
    nb, rem = divmod(k, kb)
    full = nb * kb
    Xb = X32[:, :full].reshape(m, nb, kb).transpose(1, 0, 2)       # (nb, m, kb)
    Yb = Y32[:full].reshape(nb, kb, n)                              # (nb, kb, n)
    out = np.matmul(Xb, Yb).astype(np.float64).sum(axis=0)          # 整数の和: 正確
    if rem:
        out += (X32[:, full:] @ Y32[full:]).astype(np.float64)
    return out


# ----------------------------------------------------------------------------------------------
# Ozaki-I
# ----------------------------------------------------------------------------------------------
def _shared_exponent(M, axis):
    """``|M| < 2**e`` となる行(列)ごとの e(全部 0 の行は 0)。最大値なので並べ替えに依らない。"""
    _, e = np.frexp(np.max(np.abs(M), axis=axis))
    return e.astype(np.int32)       # Windows の numpy 1.x の ldexp は C の int の指数を要る


def _slicer(M, e, axis):
    """M を共有指数 e の固定小数点で 7 ビットずつ切る(切り捨て)生成器。

    ``M ≈ Σ_t S_t · 2^(e − 7(t+1))``、各 ``S_t`` は |S_t| ≤ 127 の整数。誤差は最後の切れ端の後の残りだけで、要素ごとに
    ``2^(e − 7s)`` 未満。前から順に切るので、s 枚目までは全体を何枚に切るかに依らない(だから分割数を 1 枚ずつ増やせる)。
    """
    R = np.ldexp(M, -np.expand_dims(e, axis))       # |R| < 1(最大の要素から遠い要素は非正規数に丸まる: FP64 の積と同じ)
    step = float(2 ** _BITS)
    while True:
        R *= step                                    # 2 の冪の掛け算: 正確(ldexp より速い)
        S = np.trunc(R)
        R -= S                                       # 正確、|R| < 1
        yield S.astype(np.float32)                   # |S| ≤ 127 の整数: float32 で正確(積のたびに変換しない)


def _combine(G, e_rows, e_cols):
    """反対角ごとの整数の和 ``G[p] = Σ_{i+j=p} S_i T_j`` を 2 の冪で組み立てる(小さい桁から、順序は固定)。

    溢れは黙らせ、呼び手が有限かを確かめて ``ValueError`` にする。
    """
    C = np.zeros_like(G[0])
    for p in sorted(G, reverse=True):
        C += np.ldexp(G[p], -_BITS * (p + 2))
    with np.errstate(over="ignore", invalid="ignore"):
        return np.ldexp(C, e_rows[:, None] + e_cols[None, :])


def _sorted_abs_sum(M, axis):
    """|M| の行(列)の和を、並べ替えてから取る(内側の順に依らない)。上界の計算にだけ使う。"""
    return np.sort(np.abs(M), axis=axis).sum(axis=axis)


def _bound_from_stats(ea, eb, a1, b1, k, s):
    """Ozaki-I を s 枚で打ち切ったときの要素ごとの保証上界(打ち切りの分。最後の float64 の組み立ての丸めは含めない)。

    切り捨ての残り ``|a − Σ 切れ端| < 2^(e_i − 7s)``(B の列も同様)と、捨てた組 ``i + j > s + 1`` の積
    ``< k · 2^(e_i + e_j − 7(p − 2))``(p ≥ s + 2)を足す。
    """
    ea = ea.astype(np.float64)
    eb = eb.astype(np.float64)
    with np.errstate(over="ignore", invalid="ignore"):
        return _bound_terms(ea, eb, a1, b1, k, s)


def _bound_terms(ea, eb, a1, b1, k, s):
    tail = sum((p - 1) * 2.0 ** (-_BITS * (p - 2)) for p in range(s + 2, 2 * s + 1))
    scale = np.exp2(ea[:, None] + eb[None, :])
    res = 2.0 ** (-_BITS * s) * (np.exp2(ea)[:, None] * b1[None, :] + np.exp2(eb)[None, :] * a1[:, None]
                                 + k * scale * 2.0 ** (-_BITS * s))
    return res + k * scale * tail


def _pair_products(SA, SB, pairs):
    """切れ端の組 (i, j) ごとの正確な積 ``SA[i] @ SB[j]``。

    出力が小さい(行 × 枚数と列 × 枚数がどちらも 512 以下)ときは、切れ端を縦と横に積んで **1 回の積** で全部の組を
    出す —— 点群の 3×N @ N×3 では積の回数より内側を読む回数が効くので、組ごとに掛けるより 1 桁速い。要らない組も
    計算するが、どの要素も正確な整数なので、組ごとに掛けた結果とビット単位で同じ。
    """
    na = 1 + max(i for i, _ in pairs)
    nb = 1 + max(j for _, j in pairs)
    m, n = SA[0].shape[0], SB[0].shape[1]
    if na * m <= _STACK_LIMIT and nb * n <= _STACK_LIMIT:
        big = _exact_int_product(np.vstack(SA[:na]), np.hstack(SB[:nb]))
        return {(i, j): big[i * m:(i + 1) * m, j * n:(j + 1) * n] for i, j in pairs}
    return {(i, j): _exact_int_product(SA[i], SB[j]) for i, j in pairs}


def _antidiagonal_sums(prods, s):
    """``G[p] = Σ_{i+j=p} prods[(i, j)]``(p < s)。整数の和なので正確。"""
    G = {}
    for i in range(s):
        for j in range(s - i):
            G[i + j] = G[i + j] + prods[(i, j)] if (i + j) in G else prods[(i, j)].copy()
    return G


def _check_inner(k, s):
    if k * (2 ** _BITS - 1) ** 2 * s >= 2 ** 53:
        raise ValueError("matmul_ozaki: inner dimension %d is too long for exact float64 sums" % k)


def _ozaki1_fixed(A, B, s):
    """Ozaki-I を s 枚で。積の回数は s(s+1)/2(小さい出力は 1 回の積にまとめる)。"""
    _check_inner(A.shape[1], s)
    ea = _shared_exponent(A, 1)
    eb = _shared_exponent(B, 0)
    ga, gb = _slicer(A, ea, 1), _slicer(B, eb, 0)
    SA = [next(ga) for _ in range(s)]
    SB = [next(gb) for _ in range(s)]
    prods = _pair_products(SA, SB, [(i, j) for i in range(s) for j in range(s - i)])
    return _combine(_antidiagonal_sums(prods, s), ea, eb), {
        "n_slices": s, "n_products": s * (s + 1) // 2, "scheme": "ozaki1", "fallback": False}


def _ozaki1_auto(A, B, tol, max_slices, on_insufficient):
    """上界が ``tol · (|A||B|)_ij`` 以下になる最少の枚数を選び、その枚数の積を返す。

    **選ばれる枚数を決める量はどれも内側の順と BLAS のスレッド数に依らない**: 指数(最大値)、並べ替えた |A|・|B| の和、
    支え(0 でない項が重なるか)の正確な個数、|A||B| の下界 = |切れ端| どうしの正確な積(切り捨ては非負の値を小さくし、
    捨てた組も非負なので、組み立ての丸めの分だけ縮めれば厳密に下界)。

    何枚まで切っておくかの見当だけは float32 の |A||B| から付ける(見当が外れても、足りなければ切り足すだけで、
    選ばれる枚数 = 結果のビットには入らない)。|切れ端| の積を別に取るので、積の回数は固定の枚数の約 2 倍。
    """
    k = A.shape[1]
    _check_inner(k, max_slices)
    ea = _shared_exponent(A, 1)
    eb = _shared_exponent(B, 0)
    a1 = _sorted_abs_sum(A, 1)
    b1 = _sorted_abs_sum(B, 0)
    live = _exact_int_product((A != 0).astype(np.float32), (B != 0).astype(np.float32)) > 0
    if not np.all(np.isfinite(_bound_from_stats(ea, eb, a1, b1, k, 1)[live])):
        raise ValueError("matmul_ozaki: the scale of the product overflows float64 (rows x columns exponents)")
    # 見当(結果に入らない): float32 の |A||B| の半分を相手に上界が届く枚数 + 1
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        ref = (np.abs(A).astype(np.float32) @ np.abs(B).astype(np.float32)).astype(np.float64) * 0.5
    guess = max_slices
    for s in range(1, max_slices + 1):
        if np.all(_bound_from_stats(ea, eb, a1, b1, k, s)[live] <= tol * ref[live]):
            guess = s
            break
    cap = min(max_slices, guess + 1)
    ga, gb = _slicer(A, ea, 1), _slicer(B, eb, 0)
    SA, SB = [], []
    shrink = 1.0 - 2.0 ** -45           # 組み立ての丸め(≤ 2s 回 × 2⁻⁵³)より十分大きい余裕
    lo = 1
    while True:
        while len(SA) < cap:
            SA.append(next(ga))
            SB.append(next(gb))
        pairs = [(i, j) for i in range(cap) for j in range(cap - i)]
        prods_abs = _pair_products([np.abs(x) for x in SA], [np.abs(x) for x in SB], pairs)
        for s in range(lo, cap + 1):
            lower = _combine(_antidiagonal_sums(prods_abs, s), ea, eb) * shrink
            if np.all(_bound_from_stats(ea, eb, a1, b1, k, s)[live] <= tol * lower[live]):
                prods = _pair_products(SA, SB, [(i, j) for i in range(s) for j in range(s - i)])
                return _combine(_antidiagonal_sums(prods, s), ea, eb), {
                    "n_slices": s, "n_products": s * (s + 1) // 2, "scheme": "ozaki1", "fallback": False}
        if cap >= max_slices:
            break
        lo, cap = cap + 1, min(max_slices, cap + 3)
    if on_insufficient == "max":            # 内部用(ICP): 決定的に最大の枚数で。精度は行・列の尺度に対し 2⁻¹¹² 級
        C, info = _ozaki1_fixed(A, B, max_slices)
        info["capped"] = True
        return C, info
    if on_insufficient == "raise":
        raise ValueError("matmul_ozaki: tol=%g needs more than %d slices (the exponent span is too wide); "
                         "use float64, or on_insufficient='fallback'" % (tol, max_slices))
    return A @ B, {"n_slices": None, "n_products": None, "scheme": "float64", "fallback": True}


# ----------------------------------------------------------------------------------------------
# Ozaki-II
# ----------------------------------------------------------------------------------------------
def _garner(residues, moduli):
    """平衡した混合基数の中国剰余定理(Garner)。対称な代表値を float64 で返す。"""
    digits = []
    for t, m in enumerate(moduli):
        acc = np.zeros_like(residues[t])
        w = 1
        for j in range(t):
            acc = (acc + digits[j] * w) % m
            w = (w * moduli[j]) % m
        inv = pow(w, -1, m) if t else 1
        v = ((residues[t] - acc) * inv) % m
        digits.append(np.where(v > m // 2, v - m, v))
    X = np.zeros(residues[0].shape)
    for t in range(len(moduli) - 1, -1, -1):        # 上の桁から Horner
        X = X * moduli[t] + digits[t]
    return X


def _sym_mod(X, m):
    R = np.fmod(X, m)
    R = np.where(R >= (m + 1) // 2, R - m, R)
    return np.where(R < -(m // 2), R + m, R)


def _ozaki2_fixed(A, B, n_moduli):
    """Ozaki-II(中国剰余定理)を n_moduli 個の法で。積の回数は n_moduli。

    拡大の指数は行・列の 2-ノルム(並べ替えた二乗和)から ``||a'_i|| < 2^K`` となるように決める。Cauchy–Schwarz で
    ``|a'_i · b'_j| < 2^(2K) < M/2``(CRT の一意性の条件)が **入力の定数倍に依らず** 成り立つ(arXiv 2606.29129 が指摘した
    fast mode の欠陥の直し方と同じ考え)。
    """
    if A.shape[1] * 128 ** 2 >= 2 ** 53:
        raise ValueError("matmul_ozaki: inner dimension %d is too long for exact float64 sums" % A.shape[1])
    moduli = _INT8_MODULI[:n_moduli]
    log2M = sum(math.log2(m) for m in moduli)
    K = int(math.floor((log2M - 2) / 2))
    # ★2026-10-07: 行・列の最大値で 2 の冪に先に正規化してからノルムを取る(1e-200 × 1e200 で
    # 二乗がアンダー/オーバーフローし 0 を返していた)。2 の冪の倍率は正確なので通常域の結果はビット同一。
    _, sa = np.frexp(np.abs(A).max(axis=1))
    _, sb = np.frexp(np.abs(B).max(axis=0))
    sa = sa.astype(np.int32)
    sb = sb.astype(np.int32)
    As = np.ldexp(A, -sa[:, None])
    Bs = np.ldexp(B, -sb[None, :])
    na = np.sqrt(np.sort(As * As, axis=1).sum(axis=1))
    nb = np.sqrt(np.sort(Bs * Bs, axis=0).sum(axis=0))
    _, ea = np.frexp(na)
    _, eb = np.frexp(nb)
    ea = ea.astype(np.int32) + sa
    eb = eb.astype(np.int32) + sb
    Ai = np.trunc(np.ldexp(A, (K - ea)[:, None]))
    Bi = np.trunc(np.ldexp(B, (K - eb)[None, :]))
    res = []
    for m in moduli:
        Ct = _exact_int_product(_sym_mod(Ai, m), _sym_mod(Bi, m), _KB2)   # |剰余| ≤ 128: 1023 項の和は 2²⁴ 未満
        res.append(np.fmod(Ct, m).astype(np.int64))
    X = _garner(res, moduli)
    C = np.ldexp(X, -(K - ea)[:, None] - (K - eb)[None, :])
    return C, {"n_slices": n_moduli, "n_products": n_moduli, "scheme": "ozaki2", "fallback": False}


# ----------------------------------------------------------------------------------------------
# 公開の op
# ----------------------------------------------------------------------------------------------
def matmul_ozaki(A, B, n_slices=None, scheme: str = "ozaki1", tol: float = 2.0 ** -53,
                 on_insufficient: str = "raise", return_info: bool = False):
    """FP64 の精度の行列積 ``A @ B`` を、正確な低精度の部分積から組む(Ozaki-I / Ozaki-II)。

    ``scheme="ozaki1"``: ``n_slices`` 枚に切る(積 ``n(n+1)/2`` 回)。``n_slices=None`` なら、誤差の保証上界が
    ``tol · (|A||B|)_ij`` 以下になる最少の枚数を自動で選ぶ(1〜16 枚)。届かなければ ``on_insufficient="raise"`` で
    ``ValueError``、``"fallback"`` で普通の float64 の積を返す(この場合だけ再現性の約束は外れる。``return_info=True``
    の ``fallback`` で分かる)。
    ``scheme="ozaki2"``: 法の数を ``n_slices``(2〜20)で必ず指定する(積 ``n`` 回)。自動の選択は無い。
    ``return_info=True`` で ``(C, info)``(``n_slices``・``n_products``・``scheme``・``fallback``)。

    どちらの方式も、同じ入力なら内側の並べ替え・BLAS のスレッド数に依らず同じビット。CPU では DGEMM より 1〜2 桁遅い
    (module の docstring の使い分けを参照)。
    """
    A, B = _check_pair(A, B, "matmul_ozaki")
    if not isinstance(scheme, str) or scheme not in _SCHEMES:
        raise ValueError("matmul_ozaki: scheme must be one of %r, got %r" % (_SCHEMES, scheme))
    if not isinstance(on_insufficient, str) or on_insufficient not in ("raise", "fallback"):
        raise ValueError("matmul_ozaki: on_insufficient must be 'raise' or 'fallback', got %r" % (on_insufficient,))
    if n_slices is None:
        if scheme != "ozaki1":
            raise ValueError("matmul_ozaki: the automatic count is only available for scheme='ozaki1'; "
                             "give n_slices (2..20 moduli) for 'ozaki2'")
        C, info = _ozaki1_auto(A, B, _tol(tol), _MAX_SLICES, on_insufficient)
    elif scheme == "ozaki1":
        C, info = _ozaki1_fixed(A, B, _count(n_slices, "n_slices", 1, _MAX_SLICES))
    else:
        C, info = _ozaki2_fixed(A, B, _count(n_slices, "n_slices", 2, len(_INT8_MODULI)))
    C = _finite_out(C, "matmul_ozaki")
    return (C, info) if return_info else C


def matmul_reproducible(A, B, tol: float = 2.0 ** -53):
    """ビット単位で再現する FP64 の精度の ``A @ B``(保証できなければ ``ValueError`` = fail-closed)。

    :func:`matmul_ozaki` の Ozaki-I の自動選択に ``on_insufficient="raise"`` を固定したもの。誤差は要素ごとに
    ``tol · (|A||B|)_ij`` + 最後の組み立ての丸め(数 ulp)以下。内側の添字の順(点の順)・BLAS のスレッド数に依らず
    同じビットを返す。点群の 3×N @ N×3 や 6×N @ N×6 の縮約向け(出力が大きい積では DGEMM の 15〜83 倍遅い)。
    """
    return matmul_ozaki(A, B, None, "ozaki1", tol, "raise")


def ozaki_error_bound(A, B, n_slices: int):
    """``matmul_ozaki(A, B, n_slices)``(Ozaki-I)の打ち切り誤差の要素ごとの保証上界(行列)。

    切り捨ての残りと捨てた切れ端の組の和の上界で、最後の float64 の組み立ての丸め(``(s+1) u |A||B|`` 程度)は含めない。
    門では 26 万点余りの要素で破れ 0(PoC と tests)。並べ替えた和で計算するので、上界そのものも内側の順に依らない。
    """
    A, B = _check_pair(A, B, "ozaki_error_bound")
    s = _count(n_slices, "n_slices", 1, _MAX_SLICES)
    return _bound_from_stats(_shared_exponent(A, 1), _shared_exponent(B, 0),
                             _sorted_abs_sum(A, 1), _sorted_abs_sum(B, 0), A.shape[1], s)


def _points(X, name, who):
    try:
        X = np.asarray(X, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError("%s: %s must be a numeric (N, 3) array" % (who, name)) from exc
    if X.ndim != 2 or X.shape[1] != 3 or len(X) < 3:
        raise ValueError("%s: %s must be (N, 3) with N >= 3, got shape %r" % (who, name, X.shape))
    if not np.isfinite(X).all():
        raise ValueError("%s: %s has non-finite values" % (who, name))
    return X


def _fsum_mean(X):
    """列の正確に丸めた和を N で割る(``math.fsum`` は足す順に依らない)。"""
    return np.array([math.fsum(X[:, j].tolist()) / len(X) for j in range(X.shape[1])])


def cross_covariance_reproducible(P, Q, tol: float = 2.0 ** -53):
    """Kabsch / ICP の相互共分散 ``H = (P − P̄)ᵀ (Q − Q̄)``(3×3)を、点の順に依らないビットで返す。

    平均は ``math.fsum``(正確に丸めた和)、中心化は要素ごと、縮約は :func:`matmul_reproducible`。P と Q は行ごとに
    対応する (N, 3)(N ≥ 3)。精度は FP64 の積と同じ水準(要素ごとに ``tol · (|P−P̄|ᵀ|Q−Q̄|)_ij`` + 数 ulp)。
    """
    P = _points(P, "P", "cross_covariance_reproducible")
    Q = _points(Q, "Q", "cross_covariance_reproducible")
    if len(P) != len(Q):
        raise ValueError("cross_covariance_reproducible: P and Q must pair up, got %d and %d points" % (len(P), len(Q)))
    return matmul_reproducible((P - _fsum_mean(P)).T, Q - _fsum_mean(Q), tol)


def kabsch_reproducible(P, Q):
    """``|R p + t − q|`` を最小にする剛体の ``R``・``t``(Kabsch 1976)を、点の順に依らないビットで返す。

    返り: ``{"R": (3, 3), "t": (3,), "H": (3, 3)}``。``H`` は :func:`cross_covariance_reproducible`(どの計算機でも同じ
    ビット)、``R`` は ``H`` の特異値分解から(反射は det で直す)。特異値分解は LAPACK なので、``R``・``t`` が同じビットに
    なるのは同じ計算機・同じ LAPACK の上(3×3 なのでスレッド数には依らない)。
    """
    P = _points(P, "P", "kabsch_reproducible")
    Q = _points(Q, "Q", "kabsch_reproducible")
    if len(P) != len(Q):
        raise ValueError("kabsch_reproducible: P and Q must pair up, got %d and %d points" % (len(P), len(Q)))
    cp, cq = _fsum_mean(P), _fsum_mean(Q)
    H = matmul_reproducible((P - cp).T, Q - cq)
    U, _, Vt = np.linalg.svd(H)
    d = 1.0 if np.linalg.det(Vt.T @ U.T) >= 0 else -1.0
    R = Vt.T @ np.diag([1.0, 1.0, d]) @ U.T
    return {"R": R, "t": cq - R @ cp, "H": H}


# ----------------------------------------------------------------------------------------------
# GPU の FP64 エミュレーションの有無(重い依存なし。ctypes だけ、例外を出さない)
# ----------------------------------------------------------------------------------------------
def _cublas_candidates():
    """cuBLAS 13 の共有ライブラリの候補(CUDA_PATH 系の環境変数と既定の置き場の bin を新しい版から、最後に名前だけの探索)。"""
    if sys.platform.startswith("win"):
        names = ["cublas64_13.dll"]
        dirs = []
        for key, val in sorted(os.environ.items()):
            if key.upper().startswith("CUDA_PATH") and val:
                dirs += [os.path.join(val, "bin", "x64"), os.path.join(val, "bin")]
        # 環境変数を立てない版の入れ方もあるので、既定の置き場の v13.* も見る
        root = os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "NVIDIA GPU Computing Toolkit", "CUDA")
        for d in glob.glob(os.path.join(root, "v13.*")):
            dirs += [os.path.join(d, "bin", "x64"), os.path.join(d, "bin")]
        out = []
        for d in dirs:
            out += glob.glob(os.path.join(d, "cublas64_13.dll"))

        def ver(path):          # 新しい版を先に(…/v13.4/… は v13.3 より前)
            m = re.search(r"v(\d+)\.(\d+)", path)
            return (int(m.group(1)), int(m.group(2))) if m else (0, 0)
        return list(dict.fromkeys(sorted(set(out), key=ver, reverse=True) + names))
    return ["libcublas.so.13"]


def fp64_emulation_probe():
    """cuBLAS の FP64 エミュレーション(CUDA 13.0 Update 2 以降)が、この計算機で使えるかを表で返す。

    **例外を出さない**: GPU・CUDA・cuBLAS 13 が無ければ ``available=False`` と理由を返す(重い依存は持たない。ctypes で
    ライブラリを開いて版を読むだけ)。返り: ``available``(bool)、``rows``(候補ごとの ``library``・``path``・``loaded``・
    ``cublas_version``・``emulation_api``(``cublasSetEmulationStrategy`` があるか)・``gpu``(ハンドルを作れたか)・
    ``reason``)、``how``(有効にする方法)、``note``。

    有効にする方法は opt-in: math mode ``CUBLAS_FP64_EMULATED_FIXEDPOINT_MATH``、またはコードを変えずに
    ``CUBLAS_EMULATE_DOUBLE_PRECISION=1``。cuBLAS の文書はエミュレーション中はビット単位の再現の保証が外れると書く
    —— 再現が要るなら :func:`matmul_reproducible`。
    """
    rows = []
    available = False
    for cand in _cublas_candidates():
        row = {"library": os.path.basename(cand), "path": cand, "loaded": False, "cublas_version": None,
               "emulation_api": False, "gpu": False, "reason": ""}
        try:
            if os.path.isabs(cand) and hasattr(os, "add_dll_directory"):
                try:
                    os.add_dll_directory(os.path.dirname(cand))
                except OSError:
                    pass
            lib = ctypes.CDLL(cand)
        except OSError as exc:
            row["reason"] = "not loadable (%s)" % (str(exc).splitlines()[0][:80] if str(exc) else "not found")
            rows.append(row)
            continue
        row["loaded"] = True
        try:
            row["emulation_api"] = hasattr(lib, "cublasSetEmulationStrategy")
            h = ctypes.c_void_p()
            ver = ctypes.c_int()
            if lib.cublasCreate_v2(ctypes.byref(h)) != 0:
                row["reason"] = "cublasCreate failed (no usable GPU or driver)"
            else:
                row["gpu"] = True
                if lib.cublasGetVersion_v2(h, ctypes.byref(ver)) == 0:
                    row["cublas_version"] = int(ver.value)
                lib.cublasDestroy_v2(h)
                row["reason"] = "ok" if row["emulation_api"] else "this cuBLAS has no emulation API"
        except Exception as exc:                          # noqa: BLE001  探針は落ちない約束
            row["reason"] = "probe failed: %s" % type(exc).__name__
        available = available or (row["gpu"] and row["emulation_api"])
        rows.append(row)
        if row["gpu"]:
            break
    if not rows:
        rows.append({"library": "", "path": "", "loaded": False, "cublas_version": None, "emulation_api": False,
                     "gpu": False, "reason": "no candidate library name for this platform"})
    return {"available": bool(available), "rows": rows,
            "how": "math mode CUBLAS_FP64_EMULATED_FIXEDPOINT_MATH (cublasSetMathMode), "
                   "or env CUBLAS_EMULATE_DOUBLE_PRECISION=1 without code changes",
            "note": "fast, but cuBLAS documents that bitwise reproducibility is not guaranteed while emulation is used; "
                    "use matmul_reproducible when the bits must not move"}


# ----------------------------------------------------------------------------------------------
# 門と PoC のための正確な参照(遅い。公開しない)
# ----------------------------------------------------------------------------------------------
def _exact_matmul(A, B):
    """Python の整数で計算した、正確に丸めた ``A @ B``(門の真値。小さい行列にだけ使う)。"""
    from fractions import Fraction
    A, B = _check_pair(A, B, "_exact_matmul")

    def to_int(M):
        nz = M[M != 0]
        lo = (int(np.frexp(np.abs(nz))[1].min()) - 53) if nz.size else 0
        ints = np.empty(M.shape, dtype=object)
        for idx in np.ndindex(M.shape):
            ints[idx] = int(math.ldexp(float(M[idx]), -lo))      # 正確: 2 の冪を掛けて整数に
        return ints, lo

    IA, la = to_int(A)
    IB, lb = to_int(B)
    P = IA.dot(IB)
    scale = Fraction(2) ** (la + lb)
    out = np.empty(P.shape)
    for idx in np.ndindex(P.shape):
        out[idx] = float(Fraction(P[idx]) * scale)              # Fraction → float は正確に丸める
    return out


def _test_matrix(m, k, phi, rng):
    """論文の試験入力 ``(rand − 0.5) · exp(φ · randn)``。φ が指数の幅。"""
    return (rng.random((m, k)) - 0.5) * np.exp(phi * rng.standard_normal((m, k)))


# ----------------------------------------------------------------------------------------------
# ICP の reproducible=True の経路が使う内部の道具(registration / match3d / gicp から呼ぶ。公開しない)
# ----------------------------------------------------------------------------------------------
def _matmul_repro_any(A, B):
    """順序に依らない ``A @ B``。上界で ``tol = u`` に届けばその枚数、届かなければ 16 枚に固定(どちらも決定的)。

    ICP の ``JᵀJ`` は、ある列が大きい点と別の列が大きい点が分かれていると、成分ごとの保証に 16 枚では足りないことがある。
    ICP を ValueError で止める代わりに、行・列の尺度に対して 2⁻¹¹² 級の精度の 16 枚で返す(選ぶ規則は順序に依らない)。
    """
    A, B = _check_pair(A, B, "_matmul_repro_any")
    C, _ = _ozaki1_auto(A, B, 2.0 ** -53, _MAX_SLICES, "max")
    return _finite_out(C, "_matmul_repro_any")


def _sum_rows(M):
    """``M`` (N, d) の列ごとの和(行の順に依らない)。``ones(1, N) @ M`` を Ozaki で。"""
    M = np.asarray(M, dtype=np.float64)
    return _matmul_repro_any(np.ones((1, M.shape[0])), M)[0]


def _apply_rigid(P, R, t):
    """``P @ R.T + t`` を要素ごとの演算だけで(BLAS の核の選び方・FMA で行ごとの丸めが動かない)。"""
    P = np.asarray(P, dtype=np.float64)
    R = np.asarray(R, dtype=np.float64)
    t = np.asarray(t, dtype=np.float64)
    out = np.empty_like(P)
    for i in range(3):
        out[:, i] = ((P[:, 0] * R[i, 0] + P[:, 1] * R[i, 1]) + P[:, 2] * R[i, 2]) + t[i]
    return out


def _rowdot(a, b):
    """行ごとの内積(3 列、足す順を固定)。"""
    return (a[:, 0] * b[:, 0] + a[:, 1] * b[:, 1]) + a[:, 2] * b[:, 2]


def _rms(x):
    """``sqrt(mean(x²))``、和は ``math.fsum``(順序に依らない)。"""
    x = np.asarray(x, dtype=np.float64).ravel()
    return math.sqrt(math.fsum((x * x).tolist()) / max(1, x.size))


def _kabsch_rt(P, Q):
    """対応する点の Kabsch(順序に依らない)。返り ``(R, t)``。N ≥ 3 でなければ ValueError。"""
    r = kabsch_reproducible(P, Q)
    return r["R"], r["t"]
