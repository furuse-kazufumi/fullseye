# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""moments3d — 3D モーメント不変量(並進・回転・スケール不変な形状特徴)。

点群(numpy 配列 (N,3))から、剛体変換(平行移動 + 回転)と一様スケールに
**不変**なコンパクトな形状特徴を計算する。物体の姿勢・位置・撮影距離に依らず
「形そのもの」を数値化するので、Physical AI での物体同定・部品分類・把持前の
形状マッチングに使える。numpy in / numpy out・scipy(共通前提)以外に依存しない。

descriptors3d(Osada 流の統計 shape distribution)とは**別系統**:
こちらは中心モーメント(積分幾何量)から代数的に不変量を作る **Sadjadi–Hall 流**。
乱択サンプリングを一切使わないので

- 決定論的(seed 不要、同じ点群からは同じ値)、
- 少ない点数でも安定(2 次モーメントは N でならされる)、
- 閉形式で微分可能(下流の最適化に載せやすい)、

という特徴を持つ。回転不変性は共分散テンソル(= 中心 2 次モーメント)の
**固有値**が座標系の取り方に依らないことに由来し、近似ではなく厳密である。

提供する関数:
    central_moments(points, max_order)  重心中心化した中心モーメント μ_{pqr}(dict)
    inertia_tensor(points)              慣性テンソル (3,3)(中心 2 次モーメントから)
    principal_moments(points)           慣性テンソル固有値(降順、回転不変)
    moment_invariants(points)           並進+回転+スケール不変な特徴ベクトル
    shape_distance(inv_a, inv_b)        不変量ベクトル間の距離(小 = 同形状)

不変性の根拠(数学):
    並進 — すべて重心 c = mean(points) を引いてから計算するので、点群を平行移動
           しても中心化後の座標は同一。厳密に不変。
    回転 — 点群を R で回すと共分散 C は R C Rᵀ に写る。相似変換なので固有値
           (= 慣性主モーメント、特性多項式の係数 J1,J2,J3)は不変。厳密。
           高次の半径モーメント(重心距離 r のべき乗の平均)も、r が回転で
           変わらないため厳密に不変。moment_invariants はこの m4 を併用して
           2 次モーメントが等方な形状(cube vs sphere 等)も分離する。
    スケール — 点群を s 倍すると中心モーメント μ_{pqr} は s^{p+q+r} 倍される。
           moment_invariants は先に RMS 半径 R = sqrt(mean‖p-c‖²) で割って
           R→1 に正規化するため、以降の 2 次モーメントは s に依らない。厳密。

軸規約: points[:, 0], [:, 1], [:, 2] = (x, y, z)。
質量規約: 各点を等質量とみなし総質量 1 で正規化(モーメントは平均)。この規約では
    μ_000 = 1、μ_100 = μ_010 = μ_001 = 0(中心化のため)。全体の定数倍は固有値の
    比・特性多項式の正規化不変量に影響しないので、密度重み無しの点群で一貫する。
"""
from __future__ import annotations

import numpy as np

_EPS = 1e-12


# --------------------------------------------------------------------------- #
# 入力検証                                                                     #
# --------------------------------------------------------------------------- #
def _check_points(points, min_points: int, name: str = "points") -> np.ndarray:
    """(N,3) の実数点群であることを検証し、float64 の連続配列にして返す。

    点数不足・次元違い・非有限値を明示的な ValueError で弾く(黙って NaN を
    下流に流さない = fail-closed)。
    """
    arr = np.asarray(points, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] != 3:
        raise ValueError(
            f"{name} must be a point cloud of shape (N,3): shape={arr.shape}"
        )
    n = arr.shape[0]
    if n < min_points:
        raise ValueError(
            f"{name} has too few points: N={n} (this metric needs at least {min_points} points)"
        )
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} contains NaN/Inf; remove them during preprocessing")
    return np.ascontiguousarray(arr)


def _second_moment_matrix(centered: np.ndarray) -> np.ndarray:
    """中心化済み点群から中心 2 次モーメント行列(共分散、(3,3) 対称)を作る。

    C_ij = mean(x_i * x_j)。慣性テンソル・主モーメント・不変量の共通の素材。
    """
    n = centered.shape[0]
    # (centered.T @ centered) / N は各点等質量・総質量 1 の中心 2 次モーメント。
    c = (centered.T @ centered) / n
    # 対称性を数値的に厳密化(丸め誤差で非対称化するのを防ぐ)。
    return 0.5 * (c + c.T)


# --------------------------------------------------------------------------- #
# 中心モーメント                                                               #
# --------------------------------------------------------------------------- #
def central_moments(points, max_order: int = 3) -> dict:
    """重心中心化した中心モーメント μ_{pqr}(並進不変、キー=(p,q,r))を返す。

    μ_{pqr} = mean( (x-x̄)^p (y-ȳ)^q (z-z̄)^r )。p+q+r <= max_order の全次数を含む。
    重心を引いてから計算するので平行移動に厳密に不変。等質量規約なので
    μ_{000}=1、1 次モーメント μ_{100}=μ_{010}=μ_{001}=0(中心化の帰結)。

    Parameters
    ----------
    points : array_like, shape (N, 3)
        点群。
    max_order : int
        含める最大次数 p+q+r(既定 3)。0 以上。

    Returns
    -------
    dict[tuple[int, int, int], float]
        (p, q, r) -> μ_{pqr}。
    """
    if max_order < 0:
        raise ValueError(f"max_order must be at least 0: {max_order}")
    p = _check_points(points, min_points=1)
    centered = p - p.mean(axis=0, keepdims=True)
    dx, dy, dz = centered[:, 0], centered[:, 1], centered[:, 2]

    moments: dict = {}
    for i in range(max_order + 1):
        xi = dx ** i
        for j in range(max_order + 1 - i):
            xj = xi * (dy ** j)
            for k in range(max_order + 1 - i - j):
                moments[(i, j, k)] = float(np.mean(xj * (dz ** k)))
    return moments


# --------------------------------------------------------------------------- #
# 慣性テンソルと主モーメント                                                   #
# --------------------------------------------------------------------------- #
def inertia_tensor(points) -> np.ndarray:
    """点群の慣性テンソル (3,3)(中心 2 次モーメントから、等質量・総質量 1)。

    I_xx = mean(y²+z²), I_yy = mean(x²+z²), I_zz = mean(x²+y²),
    I_xy = -mean(xy), I_xz = -mean(xz), I_yz = -mean(yz)。
    共分散 C を使うと I = tr(C)·E₃ − C(E₃ は単位行列)と等価。対称・半正定値。
    重心中心化のため並進不変。

    Returns
    -------
    np.ndarray, shape (3, 3)
        対称な慣性テンソル。
    """
    p = _check_points(points, min_points=1)
    centered = p - p.mean(axis=0, keepdims=True)
    c = _second_moment_matrix(centered)
    inertia = np.trace(c) * np.eye(3) - c
    return 0.5 * (inertia + inertia.T)


def principal_moments(points) -> np.ndarray:
    """慣性テンソルの固有値(主慣性モーメント、降順ソート、回転不変)。

    慣性テンソルは対称なので固有値は実。点群を回転 R で回すと I → R I Rᵀ と
    相似変換され、固有値は不変(厳密)。返り値は降順にそろえるので座標系や
    回転に依らず一致する。

    Returns
    -------
    np.ndarray, shape (3,)
        降順の主慣性モーメント λ1 >= λ2 >= λ3 >= 0。
    """
    i_tensor = inertia_tensor(points)
    # eigvalsh は対称行列専用で昇順。降順に反転して姿勢に依らない正準順序に。
    eig = np.linalg.eigvalsh(i_tensor)
    return np.sort(eig)[::-1].copy()


# --------------------------------------------------------------------------- #
# 並進+回転+スケール不変な特徴ベクトル                                        #
# --------------------------------------------------------------------------- #
def moment_invariants(points) -> np.ndarray:
    """並進+回転+スケール不変な形状特徴ベクトル(Sadjadi–Hall 流 + 高次半径分布)。

    処方:
        1. 重心中心化(並進を除去)。
        2. RMS 半径 R = sqrt(mean‖p-c‖²) で割ってスケール正規化(R→1)。
           これで正規化後の中心 2 次モーメントは一様スケール s に依らない。
        3. 正規化共分散 C̃ の主不変量(特性多項式の係数)を並べる:
             λ̂1 >= λ̂2 >= λ̂3   … C̃ の固有値(= 正規化した主 2 次モーメント、
                                    Σλ̂ = 1、回転不変)
             J2 = λ̂1λ̂2 + λ̂1λ̂3 + λ̂2λ̂3   (Sadjadi–Hall 第 2 不変量 = 2×2 主小行列和)
             J3 = λ̂1λ̂2λ̂3               (第 3 不変量 = det C̃)
        4. 正規化 4 次半径モーメント m4 = mean(‖p̂-c‖⁴)(= mean(r⁴)/mean(r²)²)。
           r = 重心からの距離なので回転+並進不変、RMS 正規化済でスケール不変。

    返すベクトルは [λ̂1, λ̂2, λ̂3, J2, J3, m4](長さ 6)。
    第 1 不変量 J1 = Σλ̂ は正規化で常に 1 になり識別に寄与しないため省く。
    J2,J3 は固有値の対称式(冗長)だが、Sadjadi–Hall の代数不変量シグネチャとの
    互換のため併記する。

    識別性の内訳(honest):
        - λ̂1,λ̂2,λ̂3(と対称式 J2,J3)は **2 次モーメント(共分散固有値)のみ** に
          由来し、独立自由度は主軸アスペクト比の 2 つだけ。これだけでは 2 次が
          等方な形状(solid cube と solid sphere は共に λ̂≈(1/3,1/3,1/3))を区別
          できない。
        - m4 は **半径分布の 4 次モーメント** で、2 次では潰れる高次の形状差を
          捉える。一様 solid sphere は m4=75/63≈1.190、一様 solid cube は
          m4=19/15≈1.267 と異なるため、両者を分離できる。
    球なら概ね (1/3, 1/3, 1/3, 1/3, 1/27, 1.190)、
    細長い棒なら (≈1, ≈0, ≈0, ≈0, ≈0, 大) に近づく。

    Returns
    -------
    np.ndarray, shape (6,)
        並進・回転・スケール不変な特徴ベクトル。
    """
    p = _check_points(points, min_points=2)
    centered = p - p.mean(axis=0, keepdims=True)

    # スケール正規化: RMS 半径で割る。
    r2 = np.einsum("ij,ij->i", centered, centered)   # 各点の重心距離²
    rms = float(np.sqrt(np.mean(r2)))
    # 縮退判定は **スケール相対** で行う(絶対しきい値だと座標が極小 1e-13 なだけの
    # 非縮退点群を誤って弾く)。真に全点が一致 = 中心化後の広がりが 0 のときのみ拒否。
    max_abs = float(np.max(np.abs(centered))) if centered.size else 0.0
    if max_abs <= 0.0 or rms <= _EPS * max_abs:
        raise ValueError(
            "point cloud is degenerate (all points coincide, spread ≈ 0); "
            "invariants are undefined because scale normalization is not possible"
        )
    normalized = centered / rms

    c = _second_moment_matrix(normalized)          # tr(C̃) = 1(構成上)
    lam = np.sort(np.linalg.eigvalsh(c))[::-1]     # λ̂1 >= λ̂2 >= λ̂3, Σ = 1
    # 丸めで極小の負固有値が出うる(半正定値なので理論上 >= 0)。0 でクリップ。
    lam = np.clip(lam, 0.0, None)

    j2 = float(lam[0] * lam[1] + lam[0] * lam[2] + lam[1] * lam[2])
    j3 = float(lam[0] * lam[1] * lam[2])

    # 高次半径不変量: 正規化座標の 4 次半径モーメント。mean(‖normalized‖²)=1 なので
    # m4 = mean(r̂⁴) = mean(r⁴)/mean(r²)²(回転・並進・スケール不変)。等方な 2 次を
    # 持つ形状(cube vs sphere)を高次で分離する。
    rn2 = r2 / (rms * rms)                          # = ‖normalized‖²(各点)
    m4 = float(np.mean(rn2 * rn2))
    return np.array([lam[0], lam[1], lam[2], j2, j3, m4], dtype=np.float64)


# --------------------------------------------------------------------------- #
# 不変量ベクトル間の距離                                                       #
# --------------------------------------------------------------------------- #
def shape_distance(inv_a, inv_b) -> float:
    """2 つの不変量ベクトル間の L2 距離(小さいほど同形状)。

    moment_invariants() が返す同じ長さのベクトルどうしを比較する。すべての成分が
    無次元・剛体変換とスケールに不変なので、距離もこれらに不変。

    Returns
    -------
    float
        非負のユークリッド距離。
    """
    a = np.asarray(inv_a, dtype=np.float64).ravel()
    b = np.asarray(inv_b, dtype=np.float64).ravel()
    if a.shape != b.shape:
        raise ValueError(f"invariant vector lengths do not match: {a.shape} vs {b.shape}")
    if a.size == 0:
        raise ValueError("invariant vector is empty")
    if not (np.all(np.isfinite(a)) and np.all(np.isfinite(b))):
        raise ValueError("invariant vector contains NaN/Inf")
    return float(np.linalg.norm(a - b))
