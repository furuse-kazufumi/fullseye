# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""fourierdesc — 閉輪郭の楕円フーリエ記述子(EFD)と複素フーリエ平滑化。

閉じた輪郭(目・部品・細胞など)を **フーリエ級数** で表す。各高調波は 1 つの
楕円軌道で、低次=大まかな形、高次=細部。使い道:

    - 形状の圧縮表現 / マッチング(正規化で回転・スケール・始点に不変)
    - 高調波を打ち切ると輪郭が平滑化される(ノイズ除去・簡約化)
    - 形状分類・検索(HALCON の shape-based と相補的な、パラメトリック記述)

楕円フーリエ記述子は Kuhl & Giardina, "Elliptic Fourier Features of a Closed
Contour" (CGIP 18, 1982) の閉形式(区分線形輪郭に対する厳密式)で実装。

輪郭の受け取り方:
    points: (N,2) 配列。順序づいた閉輪郭の頂点。座標系は問わない(EFD は 2D 形状に
    対して座標軸に依らず定義される)。既存 XLD 輪郭 dict の ``contour["cs"][i]``
    ((row,col) の Nx2)をそのまま渡せる(:func:`from_xld` を用意)。

★★ 座標順の落とし穴(2026-09-02 に明文化)★★
    ここが返す/受け取る点は XLD と同じ **(row, col) = (行, 列)**。
    いっぽう ``imagemorph``(``morph`` / ``warp_piecewise_affine`` /
    ``warp_tps_image``)の点は **(x, y) = (列, 行)** で **順序が逆**。
    どちらも (N,2) float なので取り違えても **例外は出ず**、「それらしく間違った」
    ワープになる(実測: 中間コマに二重像、affine–TPS 平均差 0.01018 →
    正しい (x,y) では 0.00802)。橋渡しは必ず列の入れ替えで::

        pts_xy = np.asarray(from_xld(contour))[:, ::-1]    # (row,col) -> (x,y)
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "elliptic_fourier",
    "reconstruct",
    "normalize",
    "invariants",
    "descriptor_distance",
    "fourier_smooth",
    "from_xld",
]


def _as_contour(points, name="points"):
    p = np.asarray(points, dtype=np.float64)
    if p.ndim != 2 or p.shape[1] != 2:
        raise ValueError(f"{name} must be a sequence of (N,2) points (received: {p.shape})")
    if p.shape[0] < 3:
        raise ValueError(f"{name} needs a closed contour with at least 3 points (received: {p.shape[0]})")
    if not np.all(np.isfinite(p)):
        raise ValueError(f"{name} contains non-finite values")
    return p


def from_xld(contour, i=0):
    """XLD 輪郭 dict(``{"shape", "cs":[Nx2,...]}``)から i 番目の輪郭を取り出す。"""
    return np.asarray(contour["cs"][i], dtype=np.float64).reshape(-1, 2)


# --------------------------------------------------------------------------- #
# 楕円フーリエ記述子(EFD)                                                     #
# --------------------------------------------------------------------------- #
def elliptic_fourier(points, n_harmonics=10):
    """閉輪郭の楕円フーリエ係数を Kuhl–Giardina 閉形式で求める。

    引数:
        points: (N,2) の閉輪郭頂点。閉じていなければ内部で先頭点を末尾に補う。
        n_harmonics: 高調波数 N(多いほど細部まで表現)。

    返り値: dict
        "coeffs": (N,4) 配列。行 n が [a_n, b_n, c_n, d_n]。
        "a0", "c0": DC 成分(輪郭の中心オフセット)。
        "n_harmonics": N。

    再構成 :func:`reconstruct` は
        x(t)=a0+Σ a_n cos(2πnt)+b_n sin(2πnt),  y(t)=c0+Σ c_n cos+d_n sin  (t∈[0,1))。
    """
    p = _as_contour(points)
    if n_harmonics < 1:
        raise ValueError(f"n_harmonics must be at least 1 (received: {n_harmonics})")
    # 閉輪郭にする(末尾==先頭)
    if not np.allclose(p[0], p[-1]):
        p = np.vstack([p, p[0]])
    d = np.diff(p, axis=0)                    # (K,2) 各セグメントの変位
    dt = np.hypot(d[:, 0], d[:, 1])           # (K,) セグメント長
    dt = np.where(dt < 1e-12, 1e-12, dt)      # 退化セグメントの 0 除算回避
    t = np.concatenate([[0.0], np.cumsum(dt)])  # (K+1,) 累積弧長
    T = t[-1]
    if T < 1e-9:
        raise ValueError("contour perimeter is 0 (all points coincide)")
    phi = 2.0 * np.pi * t / T                  # (K+1,)

    K = d.shape[0]
    coeffs = np.zeros((n_harmonics, 4), dtype=np.float64)
    for n in range(1, n_harmonics + 1):
        c = 2.0 * (n ** 2) * (np.pi ** 2)
        const = T / c
        cos_d = np.cos(n * phi[1:]) - np.cos(n * phi[:-1])   # (K,)
        sin_d = np.sin(n * phi[1:]) - np.sin(n * phi[:-1])
        coeffs[n - 1, 0] = const * np.sum(d[:, 0] / dt * cos_d)  # a_n
        coeffs[n - 1, 1] = const * np.sum(d[:, 0] / dt * sin_d)  # b_n
        coeffs[n - 1, 2] = const * np.sum(d[:, 1] / dt * cos_d)  # c_n
        coeffs[n - 1, 3] = const * np.sum(d[:, 1] / dt * sin_d)  # d_n

    # DC 成分(Kuhl–Giardina)。ξ は包含累積和 − (dx/dt)·t_end、最後に先頭点座標を加える
    # (KG の A0/C0 は先頭点を原点とした相対量なので絶対位置へ戻す)。
    xi = np.cumsum(d[:, 0]) - (d[:, 0] / dt) * t[1:]
    delta = np.cumsum(d[:, 1]) - (d[:, 1] / dt) * t[1:]
    a0 = p[0, 0] + (1.0 / T) * np.sum(d[:, 0] / (2.0 * dt) * (t[1:] ** 2 - t[:-1] ** 2) + xi * dt)
    c0 = p[0, 1] + (1.0 / T) * np.sum(d[:, 1] / (2.0 * dt) * (t[1:] ** 2 - t[:-1] ** 2) + delta * dt)
    return {"coeffs": coeffs, "a0": float(a0), "c0": float(c0), "n_harmonics": int(n_harmonics)}


def reconstruct(model, n_points=300, n_harmonics=None):
    """EFD 係数から輪郭を再構成する((M,2))。

    n_harmonics を係数数より小さくすると **高調波を打ち切って平滑化** される
    (低次だけ残すほど丸くなる)。
    """
    coeffs = np.asarray(model["coeffs"], dtype=np.float64)
    N = coeffs.shape[0] if n_harmonics is None else min(int(n_harmonics), coeffs.shape[0])
    t = np.linspace(0.0, 1.0, int(n_points), endpoint=False)
    x = np.full_like(t, model["a0"])
    y = np.full_like(t, model["c0"])
    for n in range(1, N + 1):
        a, b, c, d = coeffs[n - 1]
        ang = 2.0 * np.pi * n * t
        x += a * np.cos(ang) + b * np.sin(ang)
        y += c * np.cos(ang) + d * np.sin(ang)
    return np.column_stack([x, y])


def _amplitudes(coeffs):
    """各高調波の 2×2 係数行列の特異値 (長軸 L, 短軸 W) を返す((N,2), L≥W≥0)。

    第 n 高調波が描く楕円 (a cosφ+b sinφ, c cosφ+d sinφ) の半長軸・半短軸は行列
    [[a,b],[c,d]] の特異値に一致する。特異値は **空間回転(左からの直交変換)** と
    **始点シフト(右からの位相回転)** の両方で不変なので、KG 正規化(第1高調波の
    位相合わせ)が第1高調波が円形のとき悪条件になる問題を避けられる。
    """
    coeffs = np.asarray(coeffs, dtype=np.float64)
    out = np.empty((coeffs.shape[0], 2), dtype=np.float64)
    for n in range(coeffs.shape[0]):
        sv = np.linalg.svd(coeffs[n].reshape(2, 2), compute_uv=False)  # 降順
        out[n] = sv
    return out


def invariants(model, scale_invariant=True):
    """回転・平行移動・始点・(任意で)スケールに不変な形状記述子((N,2))。

    各高調波の楕円の (長軸, 短軸) = 特異値を並べたもの。DC を含まないので平行移動に
    不変、特異値なので空間回転と始点シフトに不変、第1高調波の長軸で割ればスケール
    不変。形状マッチング(:func:`descriptor_distance`)の土台。
    """
    amp = _amplitudes(model["coeffs"])
    if scale_invariant:
        L1 = amp[0, 0]
        if L1 > 1e-12:
            amp = amp / L1
    return amp


def normalize(model, size_invariant=True):
    """EFD 係数を「正準ポーズ」の係数へ変換する(第1高調波を基準に整列)。

    Kuhl–Giardina の正準化: (1) 第1高調波の位相で **始点** の任意性を除去、(2) 第1
    楕円の長軸を基準軸へ回して **向き** を揃え、(3) 第1高調波の長軸長で割って **大きさ**
    を揃える。複数形状を重ねる/平均する等の「正準ポーズ再構成」向け。

    注意(honest): 第1高調波がほぼ **円形**(長軸≈短軸)の形状では位相 (theta/psi) が
    悪条件で不安定になる。**不変マッチングには本関数でなく** :func:`invariants` /
    :func:`descriptor_distance`(特異値ベース)を使うこと。
    """
    coeffs = np.array(model["coeffs"], dtype=np.float64, copy=True)
    a1, b1, c1, d1 = coeffs[0]
    # (1) 始点位相 theta1
    denom = a1 ** 2 - b1 ** 2 + c1 ** 2 - d1 ** 2
    theta1 = 0.5 * np.arctan2(2.0 * (a1 * b1 + c1 * d1), denom)
    for n in range(coeffs.shape[0]):
        m = n + 1
        mat = coeffs[n].reshape(2, 2)
        rot = np.array([[np.cos(m * theta1), -np.sin(m * theta1)],
                        [np.sin(m * theta1), np.cos(m * theta1)]])
        coeffs[n] = (mat @ rot).ravel()
    # (2) 回転 psi1(更新後の第1高調波で)
    a1, c1 = coeffs[0, 0], coeffs[0, 2]
    psi1 = np.arctan2(c1, a1)
    rot_psi = np.array([[np.cos(psi1), np.sin(psi1)],
                        [-np.sin(psi1), np.cos(psi1)]])
    for n in range(coeffs.shape[0]):
        mat = coeffs[n].reshape(2, 2)
        coeffs[n] = (rot_psi @ mat).ravel()
    # (3) スケール(第1高調波の長軸長 E で割る)
    if size_invariant:
        E = np.hypot(coeffs[0, 0], coeffs[0, 2])
        if E > 1e-12:
            coeffs = coeffs / E
    return coeffs


def descriptor_distance(m1, m2, n_harmonics=None, scale_invariant=True):
    """2 つの形状間の距離(小さいほど似た形)。回転/平行移動/始点/(任意で)スケール不変。

    各高調波の楕円 (長軸, 短軸) 特異値不変量(:func:`invariants`)の L2 距離。
    m1, m2 は :func:`elliptic_fourier` の出力 dict。
    """
    a = invariants(m1, scale_invariant=scale_invariant)
    b = invariants(m2, scale_invariant=scale_invariant)
    N = min(a.shape[0], b.shape[0])
    if n_harmonics is not None:
        N = min(N, int(n_harmonics))
    if N < 1:
        raise ValueError("comparison requires at least 1 harmonic")
    return float(np.linalg.norm(a[:N] - b[:N]))


# --------------------------------------------------------------------------- #
# 複素フーリエ平滑化(輪郭の帯域制限)                                          #
# --------------------------------------------------------------------------- #
def fourier_smooth(points, keep):
    """輪郭を複素 FFT で帯域制限して平滑化する。

    輪郭を複素信号 z(t)=x(t)+i·y(t) と見て FFT し、低周波 ``keep`` 本(と対称成分)
    だけ残して逆変換する。keep が小さいほど滑らか(高周波=細部/ノイズを落とす)。
    keep が全周波数以上なら恒等。返り値は入力と同点数の (N,2)。
    """
    p = _as_contour(points)
    z = p[:, 0] + 1j * p[:, 1]
    N = z.shape[0]
    Z = np.fft.fft(z)
    k = int(keep)
    if k < 1:
        raise ValueError("keep must be at least 1")
    if k >= (N + 1) // 2:
        return p.copy()
    mask = np.zeros(N, dtype=bool)
    mask[0] = True                      # DC(重心)
    mask[1:k + 1] = True                # 低周波(正)
    mask[N - k:] = True                 # 低周波(負, 対称)
    Zf = np.where(mask, Z, 0.0)
    zf = np.fft.ifft(Zf)
    return np.column_stack([zf.real, zf.imag])
