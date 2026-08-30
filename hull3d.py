# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""hull3d — 最小包含球(minimum enclosing sphere)。

点群 (N,3) を「囲む」プリミティブのうち、**fullseye にまだ存在しなかった 1 つ**だけを足す
モジュール。検査・衝突判定・把持計画・粗い占有見積りで最初に欲しくなる「その物体はどこに・
どれだけの大きさで存在するか」のうち、他の外接プリミティブは既に公開 API で揃っているため、
ここではそれらを**再実装せず**、欠けていた最小包含球のみを提供する。

正直な新規性の開示(既存公開 API との関係)
--------------------------------------------------
点群の外接プリミティブは、その多くが既に fullseye の公開 API として存在する。本モジュールは
それらを置き換えず、**唯一 repo に無かった最小包含球だけ**を追加する:

- **凸包**       — 既存: ``fs.convex_hull``(実体 ``meshrepair.convex_hull``)。同じ
  ``scipy.spatial.ConvexHull``(Qhull)ラッパで、さらに各三角面を重心から外向きに巻き直す
  **上位互換**(inertia_tensor / MuJoCo convex collider にそのまま渡せる)。→ そちらを使う。
- **AABB**       — 既存: ``fs.aabb``(実体 ``pcseg.aabb``)。軸整列の min/max。→ そちらを使う。
- **OBB**        — 既存: ``fs.obb``(実体 ``pcseg.obb``)。共分散 PCA による向き付き箱
  (``axes`` は列ベクトル・``extents`` は半幅の規約)。→ そちらを使う。
- **球フィット** — 既存だが**別問題**: ``match3d.fit_sphere_3d``(点が球**面上**にある前提の
  最小二乗代数フィット)/ ``ransac_sphere`` / ``match3d.hough_sphere_3d``(球の検出)。
  いずれも「全点を内包する最小の球」ではない。

したがって本モジュールが実際に足す新規 op は ``min_enclosing_sphere`` の 1 本のみ。
「全点を含む最小の球」は最小二乗フィットや検出とは異なる最適化問題(最小包含球, MEB)で、
把持前のクリアランス確保・衝突球・視錐台カリング等で「取りこぼしゼロで最小の余白」を欲しい
場面に対応する。凸包 / AABB / OBB が要るときは上記の既存公開 API を呼ぶこと。

- ``min_enclosing_sphere`` — 全点を含む(近似)最小包含球(Ritter 初期化 + Bădoiu–Clarkson
  精緻化)。重心中心の素朴球より中心を寄せて半径を詰める。全点内包を保証(構成上、各点を
  含むよう最後に半径を確定する安全側)。

numpy in / numpy(+dict) out、numpy だけで動く(scipy 不要)。入力検証は fail-closed
(形状不正・非有限・点数不足は例外)。

Reference (public): J. Ritter, "An efficient bounding sphere", Graphics Gems (1990);
M. Bădoiu, K. L. Clarkson, "Smaller core-sets for balls", SODA (2003)。
"""
from __future__ import annotations

from typing import Dict

import numpy as np

__all__ = [
    "min_enclosing_sphere",
]


def _as_points(points, min_n: int = 1) -> np.ndarray:
    """入力を (N,3) float64 に検証・正規化。fail-closed(形状不正/非有限/点数不足は ValueError)。"""
    P = np.asarray(points, dtype=np.float64)
    if P.ndim != 2 or P.shape[1] != 3:
        raise ValueError(f"points must be an (N,3) point cloud (got shape={P.shape})")
    if len(P) < min_n:
        raise ValueError(f"not enough points (need >= {min_n}, got {len(P)})")
    if not np.isfinite(P).all():
        raise ValueError("points contains NaN/Inf")
    return P


# ═══════════════════════════════════════════════════════════════════════════
# min_enclosing_sphere: 全点を含む(近似)最小包含球(Ritter + Bădoiu–Clarkson)
#
# 新規性: 「全点を内包する最小の球」= 最小包含球(MEB)。既存の fit_sphere_3d(点が球面上に
# ある前提の最小二乗フィット)/ ransac_sphere / hough_sphere_3d(球の検出)とは別の最適化問題で、
# repo に不在だった。凸包/AABB/OBB は既存の fs.convex_hull / fs.aabb / fs.obb を使うこと。
# ═══════════════════════════════════════════════════════════════════════════
def min_enclosing_sphere(points, refine_iters: int = 1000) -> Dict[str, object]:
    """点群 (N,3) → 全点を含む(近似)最小包含球 {center(3), radius}。

    ``fit_sphere_3d``(球面フィット)や ``ransac_sphere`` / ``hough_sphere_3d``(球検出)とは
    異なり、**全点を内包する最小の球**(minimum enclosing ball, MEB)を解く。2 段構成で
    「全点内包」を厳守しつつ半径を詰める:

    1. **Ritter (1990) 初期化** — 最遠の点対を粗く取り初期球にし、各点を走査して球外の点が
       あれば「その点と既存球の両方を含む」最小の球へ 1 回膨らませる(膨張式
       ``new_r=(r+d)/2`` / 中心を点方向へ ``(d-r)/(2d)`` 進める)。新球が旧球を完全に含むため、
       1 パスで全点内包を保証する。
    2. **Bădoiu–Clarkson (2003) core-set 反復による精緻化** — 反復 ``i`` で最遠点 ``q`` へ
       中心を ``1/(i+2)`` だけ寄せる。真の最小包含球へ単調収束する(半径過大な Ritter の
       ドリフトを詰める)。最後に半径を「中心からの最大距離」で確定するので、精緻化後も
       **必ず全点を内包**(近似ゆえ半径が過小になり点が漏れることはない、安全側)。

    精緻化した中心が Ritter より外接半径を縮められたときのみ採用する(常に Ritter 以下)。
    真の最小球(厳密解は Welzl の乱択線形時間法)ではなく高速な (1+ε) 近似。

    Parameters
    ----------
    points : array_like (N,3)
        入力点群(>= 1 点)。
    refine_iters : int
        Bădoiu–Clarkson 精緻化の反復数(既定 1000)。0 で Ritter のみ。

    Returns
    -------
    dict
        - ``center``: (3,) float64 — 球中心(世界座標)。
        - ``radius``: float — 半径(全点を内包)。

    Raises
    ------
    ValueError
        形状不正・非有限・点数 0、または ``refine_iters`` が負のとき(fail-closed)。
    """
    P = _as_points(points, min_n=1)
    if refine_iters < 0:
        raise ValueError("refine_iters must be non-negative")
    if len(P) == 1:
        return {"center": P[0].astype(np.float64), "radius": 0.0}

    # --- 1) Ritter 初期化: 最遠点対 → 中心/半径、球外の点ごとに最小膨張 ---
    x = P[0]
    y = P[int(np.argmax(np.linalg.norm(P - x, axis=1)))]
    z = P[int(np.argmax(np.linalg.norm(P - y, axis=1)))]
    c = (y + z) / 2.0
    r = float(np.linalg.norm(y - z) / 2.0)
    for p in P:
        diff = p - c
        d = float(np.linalg.norm(diff))
        if d > r:
            r_new = (r + d) / 2.0
            c = c + ((d - r_new) / d) * diff   # (d - r_new)/d == (d - r)/(2d)
            r = r_new
    c_ritter, r_ritter = c.copy(), r

    # --- 2) Bădoiu–Clarkson 精緻化: 最遠点へ 1/(i+2) だけ中心を寄せる ---
    c_bc = c_ritter.copy()
    for it in range(refine_iters):
        d = np.linalg.norm(P - c_bc, axis=1)
        j = int(np.argmax(d))
        c_bc = c_bc + (P[j] - c_bc) / (it + 2)
    # 半径は「中心からの最大距離」で確定 → 全点内包を厳守(過小にならない安全側)
    r_bc = float(np.linalg.norm(P - c_bc, axis=1).max())

    # Ritter を上回る(半径を縮める)ときのみ採用 → 常に Ritter 以下を保証
    if r_bc < r_ritter:
        return {"center": c_bc.astype(np.float64), "radius": r_bc}
    return {"center": c_ritter.astype(np.float64), "radius": float(r_ritter)}
