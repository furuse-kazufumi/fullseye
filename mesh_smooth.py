# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""mesh_smooth — 三角形メッシュの平滑化(Laplacian / Taubin).

marching cubes やスキャン由来の三角形メッシュは、頂点位置に高周波ノイズ(ボクセル階段・
計測揺らぎ)が乗る。ここでは **接続(faces)から頂点隣接を作り、隣接頂点の平均へ寄せる
umbrella(uniform)Laplacian** で高周波成分だけを落とす。

差別化点(honest, 既存 op との違い):
  - ``pointcloud.mls_smooth`` … *点群* を局所多項式(MLS)で当て直す平滑化。接続(faces)を持たず、
    面のトポロジーは使わない。
  - ``curvature3d`` 系 / ``smooth_flow`` … スカラー/ベクトル場の平滑化であってメッシュ幾何ではない。
  - ``sdf_smooth_union`` … SDF(符号付き距離場)の soft union であって既存メッシュの平滑化ではない。
  - **本モジュール** … 既存の *三角形メッシュ*(verts+faces)の頂点を、faces から張った隣接
    グラフ上で平滑化する。faces は不変で verts だけが動く。

2 つの op:
  * :func:`laplacian_smooth` — 各頂点を隣接平均へ ``lam`` だけ寄せる素朴な Laplacian。ノイズは
    確実に減るが、閉曲面では平均曲率流と同じく **内側へ収縮(shrinkage)** する(球は縮む)。
  * :func:`taubin_smooth` — Taubin (SIGGRAPH 1995) の λ|μ フィルタ。正の ``lam`` で寄せた直後に
    負の ``mu``(``|mu| > lam``)で押し戻す 2 段を交互に掛け、**低周波(全体形状)を保ったまま**
    高周波ノイズだけを落とす。これにより **収縮しない**(球の平均半径がほぼ保たれる)。

メッシュ表現は recon3d / match3d.voxel_to_mesh に合わせ ``verts (N,3) float`` + ``faces (M,3) int``。
入力は 2 要素以上のシーケンス(verts, faces, ...)を受け、先頭 2 つを使う(voxel_to_mesh の
3-tuple もそのまま渡せる)。返り値は常に ``(verts, faces)`` の 2-tuple(faces は入力を保持)。

numpy + scipy(sparse)のみ。重い依存なし。入力は fail-closed に検証する。

Reference (public): G. Taubin, "A Signal Processing Approach to Fair Surface Design",
SIGGRAPH 1995.
"""
from __future__ import annotations

from typing import Sequence, Tuple

import numpy as np
from scipy.sparse import coo_matrix, diags

__all__ = ["laplacian_smooth", "taubin_smooth"]

Mesh = Tuple[np.ndarray, np.ndarray]


def _as_mesh(mesh: Sequence) -> Mesh:
    """入力メッシュを (verts (N,3) float64, faces (M,3) int64) へ検証。fail-closed。

    2 要素以上のシーケンス(verts, faces[, normals, ...])を受け、先頭 2 つを使う。
    形状不正・非有限・面インデックスの範囲外は ValueError(退化を捏造せず拒否)。
    """
    if not isinstance(mesh, (tuple, list)) or len(mesh) < 2:
        raise ValueError(
            "mesh は (verts, faces) を含む長さ>=2 のシーケンスが必要です"
            f"(受領: {type(mesh).__name__})")
    V = np.asarray(mesh[0], dtype=np.float64)
    F = np.asarray(mesh[1], dtype=np.int64)
    if V.ndim != 2 or V.shape[1] != 3:
        raise ValueError(f"verts は (N,3) が必要です(受領 shape={V.shape})")
    if F.ndim != 2 or F.shape[1] != 3:
        raise ValueError(f"faces は (M,3) が必要です(受領 shape={F.shape})")
    if len(V) < 3:
        raise ValueError(f"頂点が少なすぎます(>=3、受領 {len(V)})")
    if not np.isfinite(V).all():
        raise ValueError("verts に NaN/Inf が含まれています")
    if len(F) == 0:
        raise ValueError("faces が空です(隣接を張れません)")
    if F.min() < 0 or F.max() >= len(V):
        raise ValueError(
            f"faces のインデックスが範囲外です([0,{len(V)}) 必要、"
            f"実測 [{int(F.min())},{int(F.max())}])")
    return V, F


def _umbrella_operator(faces: np.ndarray, n: int):
    """faces から umbrella(行正規化)隣接作用素を構築。→ (W(csr), has_neighbor(bool,(N,))).

    各三角形の 3 辺を無向エッジとして数え上げ、二値隣接 A(重複辺は 1)を作り、次数で
    行正規化した ``W = D^-1 A`` を返す。``W @ V`` は各頂点の**隣接頂点の重心**になる。
    孤立頂点(次数 0、faces に現れない頂点)は ``has_neighbor=False`` として呼び出し側で
    据え置く(原点へ吸い込ませない)。
    """
    e = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]], axis=0)
    i = np.concatenate([e[:, 0], e[:, 1]])          # 無向化: 両向きを入れる
    j = np.concatenate([e[:, 1], e[:, 0]])
    A = coo_matrix((np.ones(len(i), dtype=np.float64), (i, j)), shape=(n, n)).tocsr()
    A.data[:] = 1.0                                  # 重複辺(tocsr で合算済)を二値化
    deg = np.asarray(A.sum(axis=1)).ravel()
    has_nb = deg > 0
    inv = np.zeros(n, dtype=np.float64)
    inv[has_nb] = 1.0 / deg[has_nb]
    W = diags(inv) @ A                               # 行正規化 = 隣接平均作用素
    return W.tocsr(), has_nb


def _smooth_pass(V: np.ndarray, W, has_nb: np.ndarray, factor: float) -> np.ndarray:
    """1 段の umbrella Laplacian 更新: V += factor * (隣接平均 - V)。孤立頂点は据え置き。"""
    delta = W @ V - V                                # 各頂点の umbrella Laplacian
    delta[~has_nb] = 0.0                             # 孤立頂点は動かさない(fail-safe)
    return V + factor * delta


def laplacian_smooth(mesh: Sequence, iters: int = 10, lam: float = 0.5) -> Mesh:
    """umbrella Laplacian による三角形メッシュ平滑化。→ (verts, faces)。

    各反復で全頂点を ``v_i += lam * (mean(隣接 v_j) - v_i)`` と更新する。高周波ノイズを
    確実に減らす一方、閉曲面では平均曲率流と同様に **内側へ収縮(shrinkage)** する
    (球は反復とともに縮む)。収縮を避けたい場合は :func:`taubin_smooth` を使う。

    Args:
        mesh: (verts (N,3), faces (M,3)[, ...]) のシーケンス。faces は不変。
        iters: 反復回数(正の整数)。
        lam: 各段の寄せ率、``0 < lam <= 1``(1 で隣接平均へ全寄せ)。

    Returns:
        (verts (N,3) float64, faces (M,3) int64)。faces は入力を保持。

    Raises:
        ValueError: メッシュ形状不正・面範囲外・iters/lam が不正(fail-closed)。
    """
    V, F = _as_mesh(mesh)
    if not isinstance(iters, (int, np.integer)) or iters < 1:
        raise ValueError(f"iters は正の整数が必要です(受領 {iters!r})")
    if not np.isfinite(lam) or not (0.0 < lam <= 1.0):
        raise ValueError(f"lam は 0 < lam <= 1 が必要です(受領 {lam!r})")

    W, has_nb = _umbrella_operator(F, len(V))
    out = V.copy()
    for _ in range(int(iters)):
        out = _smooth_pass(out, W, has_nb, float(lam))
    return out.astype(np.float64), F


def taubin_smooth(mesh: Sequence, iters: int = 10, lam: float = 0.33,
                  mu: float = -0.34) -> Mesh:
    """Taubin λ|μ フィルタによる **非収縮** 平滑化。→ (verts, faces)。

    各反復で「正の ``lam`` で寄せる段」→「負の ``mu`` で押し戻す段」を続けて掛ける。
    ``|mu| > lam`` とすることで低周波(全体形状)を通し高周波(ノイズ)だけを減衰させる
    帯域通過フィルタになり、Laplacian の収縮アーティファクトを打ち消す(球の平均半径が
    ほぼ保たれる)。既定 ``lam=0.33, mu=-0.34`` は Taubin (1995) の推奨に近い。

    Args:
        mesh: (verts (N,3), faces (M,3)[, ...]) のシーケンス。faces は不変。
        iters: λ|μ ペアの反復回数(正の整数)。
        lam: 寄せ段の係数、``0 < lam < 1``。
        mu: 押し戻し段の係数、``mu < 0`` かつ ``|mu| > lam``(収縮を打ち消す条件)。

    Returns:
        (verts (N,3) float64, faces (M,3) int64)。faces は入力を保持。

    Raises:
        ValueError: メッシュ形状不正・面範囲外・iters/lam/mu が不正(fail-closed)。
    """
    V, F = _as_mesh(mesh)
    if not isinstance(iters, (int, np.integer)) or iters < 1:
        raise ValueError(f"iters は正の整数が必要です(受領 {iters!r})")
    if not np.isfinite(lam) or not (0.0 < lam < 1.0):
        raise ValueError(f"lam は 0 < lam < 1 が必要です(受領 {lam!r})")
    if not np.isfinite(mu) or mu >= 0.0:
        raise ValueError(f"mu は負である必要があります(受領 {mu!r})")
    if abs(mu) <= lam:
        raise ValueError(
            f"|mu| > lam が必要です(非収縮の条件)。受領 lam={lam!r}, mu={mu!r}")

    W, has_nb = _umbrella_operator(F, len(V))
    out = V.copy()
    for _ in range(int(iters)):
        out = _smooth_pass(out, W, has_nb, float(lam))   # 寄せる(平滑)
        out = _smooth_pass(out, W, has_nb, float(mu))    # 押し戻す(収縮打消)
    return out.astype(np.float64), F
