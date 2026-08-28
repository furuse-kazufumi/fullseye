# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""hull3d — 凸包(convex hull)とバウンディングボリューム(bounding volumes)。

点群 (N,3) を「囲む」最小限のプリミティブを起こす基本メトロロジー群。検査・衝突判定・
把持計画・粗い占有見積りで最初に欲しくなる「その物体はどこに・どれだけの向きと大きさで
存在するか」を、テンプレート不要・データ駆動で返す。

- ``convex_hull_3d`` — Qhull(scipy.spatial.ConvexHull)で凸包メッシュ (verts, faces) を張る。
  凸包は「その点群を含む最小の凸多面体」で、体積/表面積/凸性の基準になる。
- ``oriented_bounding_box`` — 共分散 PCA で主軸を取り、点を主軸系へ回して各軸の幅を測る
  向き付きバウンディングボックス(OBB)。回転した物体でも密着する(軸整列の AABB より小さい)。
- ``aabb`` — 軸整列バウンディングボックス(axis-aligned bounding box)。座標軸に沿った最小箱。
  計算は最速だが、物体が座標軸に対し傾いていると過大になる。
- ``min_enclosing_sphere`` — 全点を含む(近似)最小包含球(Ritter 法)。重心中心の素朴球より
  中心を寄せて半径を詰める。全点内包を保証(構成上、各点を含むよう膨らませる)。

すべて numpy in / numpy(+dict) out。凸包のみ scipy.spatial.ConvexHull(Qhull)に依存し、
他は numpy だけで動く。入力検証は fail-closed(形状不正・非有限・点数不足・縮退は例外)。

Reference (public): J. Ritter, "An efficient bounding sphere", Graphics Gems (1990);
C. B. Barber, D. P. Dobkin, H. Huhdanpaa, "The Quickhull Algorithm for Convex Hulls",
ACM TOMS 22(4) 1996 (Qhull)。
"""
from __future__ import annotations

from typing import Dict

import numpy as np

__all__ = [
    "convex_hull_3d",
    "oriented_bounding_box",
    "aabb",
    "min_enclosing_sphere",
]


def _as_points(points, min_n: int = 1) -> np.ndarray:
    """入力を (N,3) float64 に検証・正規化。fail-closed(形状不正/非有限/点数不足は ValueError)。"""
    P = np.asarray(points, dtype=np.float64)
    if P.ndim != 2 or P.shape[1] != 3:
        raise ValueError(f"points は (N,3) の点群が必要です(受領: shape={P.shape})")
    if len(P) < min_n:
        raise ValueError(f"点数が不足しています(>= {min_n} 必要、受領 {len(P)})")
    if not np.isfinite(P).all():
        raise ValueError("points に NaN/Inf が含まれています")
    return P


# ═══════════════════════════════════════════════════════════════════════════
# 1. convex_hull_3d: 点群 → 凸包メッシュ(verts, faces)
# ═══════════════════════════════════════════════════════════════════════════
def convex_hull_3d(points):
    """点群 (N,3) → 凸包の三角形メッシュ (vertices(V,3), faces(F,3))。

    scipy.spatial.ConvexHull(Qhull)で凸包を計算し、hull を構成する頂点だけに詰め直した
    三角形メッシュとして返す。頂点は入力点の部分集合(凸包上の点)、面は三角形へ分割済み
    (Qhull の Qt トライアンギュレーション)で、``faces`` は ``vertices`` を参照する 0 始まり
    インデックス。表現は recon3d / match3d のメッシュ規約(verts float, faces int)を踏襲する。

    Parameters
    ----------
    points : array_like (N,3)
        入力点群(>= 4 点かつ非共面)。

    Returns
    -------
    vertices : numpy.ndarray (V,3) float64
        凸包を構成する頂点(入力点の部分集合、詰め直し済み)。
    faces : numpy.ndarray (F,3) int64
        vertices を参照する三角形インデックス。

    Raises
    ------
    ValueError
        点数不足(<4)、非有限、または共面/共線などで 3D 凸包が退化して張れないとき
        (fail-closed。Qhull の失敗を握りつぶさず明示エラーにする)。
    """
    P = _as_points(points, min_n=4)
    try:
        from scipy.spatial import ConvexHull
        from scipy.spatial.qhull import QhullError  # type: ignore
    except ImportError:  # pragma: no cover - scipy レイアウト差異のフォールバック
        from scipy.spatial import ConvexHull
        try:
            from scipy.spatial import QhullError  # type: ignore
        except ImportError:  # 最終手段: 汎用例外で捕捉
            QhullError = Exception  # type: ignore

    try:
        hull = ConvexHull(P)
    except QhullError as e:  # 共面/共線/重複などで 3D 包が張れない
        raise ValueError(
            f"凸包を張れませんでした(共面/共線/退化した点群?): {e}"
        )

    used = np.unique(hull.simplices)          # 凸包に実際に使われた頂点 index
    remap = -np.ones(len(P), dtype=np.int64)
    remap[used] = np.arange(len(used))
    vertices = P[used]
    faces = remap[hull.simplices].astype(np.int64)
    return vertices.astype(np.float64), faces


# ═══════════════════════════════════════════════════════════════════════════
# 2. oriented_bounding_box: 共分散 PCA による向き付きバウンディングボックス
# ═══════════════════════════════════════════════════════════════════════════
def oriented_bounding_box(points) -> Dict[str, np.ndarray]:
    """点群 (N,3) → 向き付きバウンディングボックス(OBB)。

    重心を引いた点群の共分散行列を固有分解して主軸(principal axes)を得(``eigh``、
    分散の大きい順)、点を主軸系へ回して各軸方向の最小/最大から幅(extent)と中心を測る。
    軸整列の AABB と違い物体の向きに追従するため、傾いた/回転した物体に密着する。

    Parameters
    ----------
    points : array_like (N,3)
        入力点群(>= 2 点)。

    Returns
    -------
    dict
        - ``center`` : (3,) float64 — OBB 中心(世界座標)。
        - ``axes``   : (3,3) float64 — 各行が主軸の単位ベクトル(分散降順、右手系に整える)。
        - ``extents``: (3,) float64 — 各主軸方向の**全幅**(= max − min、辺の長さ)。
        - ``corners``: (8,3) float64 — 8 頂点(世界座標)。

    Raises
    ------
    ValueError
        点数不足(<2)、非有限、または全点が一致してスプレッドが無い(向きが定義不能)とき。
    """
    P = _as_points(points, min_n=2)
    c0 = P.mean(axis=0)
    X = P - c0
    if not np.any(np.abs(X) > 1e-12):
        raise ValueError("全点が一致しています(OBB の向きが定義できません)")

    cov = (X.T @ X) / len(P)                   # 共分散(スケール因子は固有ベクトルに不変)
    _, V = np.linalg.eigh(cov)                 # 昇順固有値、列が固有ベクトル
    axes = V.T[::-1].copy()                    # 各行=主軸、分散降順に並べ替え
    # 右手系(det=+1)に整える(反転しても extents/corners は不変だが向きを決定的に)
    if np.linalg.det(axes) < 0:
        axes[2] = -axes[2]

    proj = X @ axes.T                          # 主軸系へ射影 (N,3)、列 k = axes[k] 方向
    mn = proj.min(axis=0)
    mx = proj.max(axis=0)
    extents = mx - mn
    mid = (mx + mn) / 2.0
    center = c0 + mid @ axes                   # 世界座標の箱中心

    signs = np.array([[sx, sy, sz]
                      for sx in (-1.0, 1.0)
                      for sy in (-1.0, 1.0)
                      for sz in (-1.0, 1.0)])   # (8,3) の ±1 組合せ
    corners = center + (signs * (extents / 2.0)) @ axes

    return {
        "center": center.astype(np.float64),
        "axes": axes.astype(np.float64),
        "extents": extents.astype(np.float64),
        "corners": corners.astype(np.float64),
    }


# ═══════════════════════════════════════════════════════════════════════════
# 3. aabb: 軸整列バウンディングボックス
# ═══════════════════════════════════════════════════════════════════════════
def aabb(points) -> Dict[str, np.ndarray]:
    """点群 (N,3) → 軸整列バウンディングボックス(AABB)。

    各座標軸に沿った最小・最大を取るだけの最速の外接箱。物体が座標軸に対して傾いていると
    過大になる(OBB との差 = 向き適合の効き)。

    Parameters
    ----------
    points : array_like (N,3)
        入力点群(>= 1 点)。

    Returns
    -------
    dict
        - ``min``: (3,) float64 — 各軸の最小座標。
        - ``max``: (3,) float64 — 各軸の最大座標。

    Raises
    ------
    ValueError
        形状不正・非有限・点数 0 のとき(fail-closed)。
    """
    P = _as_points(points, min_n=1)
    return {
        "min": P.min(axis=0).astype(np.float64),
        "max": P.max(axis=0).astype(np.float64),
    }


# ═══════════════════════════════════════════════════════════════════════════
# 4. min_enclosing_sphere: 全点を含む(近似)最小包含球(Ritter 法)
# ═══════════════════════════════════════════════════════════════════════════
def min_enclosing_sphere(points, refine_iters: int = 1000) -> Dict[str, object]:
    """点群 (N,3) → 全点を含む(近似)最小包含球 {center(3), radius}。

    2 段構成で「全点内包」を厳守しつつ半径を詰める:

    1. **Ritter (1990) 初期化** — 最遠の点対を粗く取り初期球にし、各点を走査して球外の点が
       あれば「その点と既存球の両方を含む」最小の球へ 1 回膨らませる(膨張式
       ``new_r=(r+d)/2`` / 中心を点方向へ ``(d-r)/(2d)`` 進める)。新球が旧球を完全に含むため、
       1 パスで全点内包を保証する。
    2. **Bădoiu–Clarkson (2003) core-set 反復による精緻化** — 反復 ``i`` で最遠点 ``q`` へ
       中心を ``1/(i+2)`` だけ寄せる。真の最小包含球へ単調収束する(半径過大な Ritter の
       ドリフトを詰める)。最後に半径を「中心からの最大距離」で確定するので、精緻化後も
       **必ず全点を内包**(近似ゆえ半径が過小になり点が漏れることはない、安全側)。

    精緻化した中心が Ritter より外接半径を縮められたときのみ採用する(常に Ritter 以下)。
    真の最小球(NP ではないが厳密解は Welzl)ではなく高速な (1+ε) 近似。

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
        raise ValueError("refine_iters は非負である必要があります")
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
