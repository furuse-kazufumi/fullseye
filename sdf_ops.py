# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""sdf_ops — 符号付き距離場(SDF)の CSG 合成(union/intersect/subtract/smooth-blend/offset)。

3D 形状を **符号付き距離場**(signed distance field, 各点で最近表面までの距離。**内側が負・
外側が正**、esdf と同符号)で表すと、集合演算がそのまま **min/max の代数**になる: 2 形状の
和 A∪B は各点の SDF の最小、積 A∩B は最大、差 A\\B は ``max(a,-b)``。これで **CSG(構成的
立体幾何)** — 球・箱などのプリミティブを組み合わせて複雑形状を作る木 — を密なグリッド上で
機械的に構築できる。

固有価値(既存モジュールとの差別化):
  * ``occupancy.esdf`` は **占有ボクセル(bool)→ EDT** で符号付き距離を作る(観測由来・離散)。
    本モジュールは **解析プリミティブ**(``sphere_sdf`` / ``box_sdf``)を **閉形式**で評価し、
    それらを CSG 合成する(設計・生成由来・連続)。両者は同じ符号規約なので相互運用できる。
  * ``recon3d`` / ``tsdf_fusion`` はデータから等値面場を作る。本モジュールが吐く SDF は
    marching cubes(recon3d)や ``occupancy`` のゼロ交差抽出にそのまま渡せる CSG 側の入口。

代数(``a``,``b`` は同一グリッド上で評価した SDF、shape はブロードキャスト整合すればよい):
    union     A∪B  = min(a, b)          — 内側(負)がどちらかにあれば内側
    intersect A∩B  = max(a, b)          — 両方の内側でのみ内側
    subtract  A\\B = max(a, -b)         — A の内側かつ B の外側
    smooth_union      = polynomial smin  — k で丸めた union(k→0 で min に一致)
    offset(sdf, r)    = sdf - r          — ゼロ等値面を r だけ外へ(r>0 で膨張, r<0 で収縮)

min/max による合成はゼロ等値面(=形状境界)を厳密に与え、**外側では厳密な SDF**、内側は保守的
下界(近傍の重なり領域で真の距離をやや過小評価しうる)になる — CSG では標準的な性質。

契約: ``±inf`` を含む SDF(``esdf`` は「全自由なら +inf」を明示契約)も正しく合成する —
min/max 代数は inf を厳密に伝播し(``min(a,+inf)=a`` 等)、``sdf_smooth_union`` は inf 要素で
厳密に ``min`` へ退化する。したがって出力の inf は入力契約の伝播であり異常値ではない。

cv2/skimage は使わない。numpy + 標準ライブラリのみ。
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "sdf_union", "sdf_intersect", "sdf_subtract", "sdf_smooth_union", "sdf_offset",
    "sphere_sdf", "box_sdf", "grid_coords",
]


# --------------------------------------------------------------------------- #
# CSG boolean composition (min/max algebra on signed distance fields)         #
# --------------------------------------------------------------------------- #
def sdf_union(a, b):
    """2 SDF の和集合 A∪B = 要素ごとの min(a, b)(内側=負がどちらかにあれば内側)。

    ゼロ等値面は両形状の境界の和集合に厳密一致。外側では厳密な SDF(最近表面までの距離)、
    内側は保守的下界。``a``/``b`` はブロードキャスト整合すればよい。"""
    a = np.asarray(a, np.float64)
    b = np.asarray(b, np.float64)
    return np.minimum(a, b)


def sdf_intersect(a, b):
    """2 SDF の積集合 A∩B = 要素ごとの max(a, b)(両方の内側でのみ内側)。

    ゼロ等値面は両境界の共通部分。外側で厳密 SDF、内側は保守的下界。"""
    a = np.asarray(a, np.float64)
    b = np.asarray(b, np.float64)
    return np.maximum(a, b)


def sdf_subtract(a, b):
    """差集合 A\\B = max(a, -b)(A の内側 かつ B の外側 = ``-b`` の内側)。

    ``b`` の符号反転は「B の外を内、B の内を外」に反転する(相補集合)ので、A との積が
    A から B をくり抜いた形になる。非可換: ``sdf_subtract(a,b) != sdf_subtract(b,a)``。"""
    a = np.asarray(a, np.float64)
    b = np.asarray(b, np.float64)
    return np.maximum(a, -b)


def sdf_smooth_union(a, b, k):
    """滑らかに丸めた和集合(polynomial smooth-min)。``k>0`` で継ぎ目を半径 ~k で丸める。

    Inigo Quilez の二次多項式 smin:
        ``h = clip(0.5 + 0.5*(b-a)/k, 0, 1)``,  ``smin = mix(b,a,h) - k*h*(1-h)``。
    性質: (1) 対称 ``smin(a,b)=smin(b,a)``、(2) ``smin <= min(a,b)``(継ぎ目でくぼむ)、
    (3) **k→0 で min(a,b) に一致**(= 硬い ``sdf_union``)、(4) 1 次同次
    ``smin(s*a,s*b,s*k)=s*smin(a,b,k)``(スケール整合)。

    ``k`` は距離次元の丸め半径。硬い min が欲しければ ``sdf_union`` を使う。
    ``±inf`` を含む入力(``esdf`` の「全自由なら +inf」契約との相互運用)では、
    ブレンド帯 ``|a-b|<k`` が退化するため厳密に ``min(a,b)`` を返す。
    Raises ValueError for k<=0(0 除算を避けるため fail-closed)。"""
    a = np.asarray(a, np.float64)
    b = np.asarray(b, np.float64)
    k = float(k)
    if not (k > 0.0):                           # fail-closed: k=0 は sdf_union、k<0 は無意味
        raise ValueError("k must be positive; use sdf_union for the hard (k->0) min")
    # inf を含む要素は smooth 式が inf-inf / inf*0 = NaN に化ける(連鎖ファザー
    # wave-5 派生の実測)。数学的には |a-b|>=k でブレンド項は 0 なので min が厳密解。
    with np.errstate(invalid="ignore"):
        h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
        mix = b * (1.0 - h) + a * h             # mix(b, a, h) = lerp from b to a
        out = mix - k * h * (1.0 - h)
    inf_in = np.isinf(a) | np.isinf(b)
    if np.any(inf_in):
        out = np.where(inf_in, np.minimum(a, b), out)
    return out


def sdf_offset(sdf, r):
    """SDF のゼロ等値面を距離 ``r`` だけ法線方向へ動かす = ``sdf - r``(r>0 膨張, r<0 収縮)。

    新しいゼロ集合は旧 ``sdf == r`` の等値面。全点で距離が一様に ``r`` シフトするので、距離場
    としての性質(勾配ノルム 1)は保たれる。プリミティブの厚み付け(丸めた殻)や配管の
    クリアランス確保に使う。"""
    sdf = np.asarray(sdf, np.float64)
    return sdf - float(r)


# --------------------------------------------------------------------------- #
# Analytic primitives (closed-form SDFs evaluated on a coordinate grid)       #
# --------------------------------------------------------------------------- #
def _as_coords(grid) -> np.ndarray:
    """座標グリッドを (..., 3) float64 に検証・変換(最終軸 = xyz)。"""
    g = np.asarray(grid, np.float64)
    if g.ndim < 1 or g.shape[-1] != 3:
        raise ValueError("grid must have last axis of size 3 (x, y, z coordinates)")
    return g


def sphere_sdf(grid, center, R):
    """球の符号付き距離場: ``|p - center| - R``(内側負・外側正)。

    ``grid`` は最終軸が 3 の座標配列 (..., 3)(``grid_coords`` の出力や (N,3) 点群)。
    ``center`` は長さ3、``R>=0`` は半径。返り値の shape は ``grid.shape[:-1]``。厳密な SDF
    (勾配ノルム 1)。``sdf_offset(sphere_sdf(g,c,R), r) == sphere_sdf(g,c,R+r)``。

    Raises ValueError for R<0 or malformed grid/center。"""
    g = _as_coords(grid)
    c = np.asarray(center, np.float64).reshape(3)
    R = float(R)
    if R < 0:                                   # fail-closed: 負半径は無意味
        raise ValueError("R must be non-negative")
    return np.linalg.norm(g - c, axis=-1) - R


def box_sdf(grid, center, half_extents):
    """軸平行直方体の**厳密**な符号付き距離場(内側負・外側正)。

    Inigo Quilez の box SDF: ``q = |p-center| - half_extents`` とし、
        ``outside = |max(q,0)|`` (角/辺/面の外はユークリッド距離),
        ``inside  = min(max(q_x,q_y,q_z), 0)`` (内側は最近面までの負値),
        ``sdf = outside + inside``。
    ``half_extents`` は各軸の**半辺長**(中心から面まで)。外側は厳密距離(角では対角、面前は
    垂直距離)、内側も最近面までの厳密負距離を与える。

    Raises ValueError for any half_extent<0 or malformed grid/center/half_extents。"""
    g = _as_coords(grid)
    c = np.asarray(center, np.float64).reshape(3)
    he = np.asarray(half_extents, np.float64).reshape(3)
    if np.any(he < 0):                          # fail-closed: 負の半辺は無意味
        raise ValueError("half_extents must be non-negative")
    q = np.abs(g - c) - he                      # (..., 3)
    outside = np.linalg.norm(np.maximum(q, 0.0), axis=-1)
    inside = np.minimum(np.max(q, axis=-1), 0.0)
    return outside + inside


def grid_coords(bounds, res):
    """CSG 評価用のボクセル中心座標グリッドを作る(occupancy と同じ格子規約)。

    ``bounds=((xmin,xmax),(ymin,ymax),(zmin,zmax))``、``res`` は各軸のボクセル数(スカラ=立方
    or 長さ3)。voxel ``i`` の中心は world ``lo + (i+0.5)/res * span``(``occupancy.query_distance``
    の ``c=(q-lo)/span*res-0.5`` と整合 = 中心アライン)。返り値は
    ``coords`` shape ``(nx,ny,nz,3)`` と ``extent=(xmin,xmax,ymin,ymax,zmin,zmax)``。

    こうして作った座標に ``sphere_sdf``/``box_sdf`` を評価し CSG 合成すれば、``recon3d`` の
    marching cubes や ``occupancy`` のゼロ交差抽出へそのまま渡せる。

    Raises ValueError for degenerate bounds or res<=0。"""
    b = np.asarray(bounds, np.float64)
    if b.shape != (3, 2):
        raise ValueError("bounds must be ((xmin,xmax),(ymin,ymax),(zmin,zmax))")
    lo, hi = b[:, 0], b[:, 1]
    span = hi - lo
    if not np.all(span > 0):                    # fail-closed: 退化 bounds
        raise ValueError("degenerate bounds: max must exceed min on every axis")
    r = np.atleast_1d(np.asarray(res, np.int64))
    if r.size == 1:
        r = np.repeat(r, 3)
    if r.size != 3 or np.any(r <= 0):           # fail-closed
        raise ValueError("res must be a positive int or length-3 sequence of positive ints")
    axes = [lo[d] + (np.arange(r[d]) + 0.5) / r[d] * span[d] for d in range(3)]
    X, Y, Z = np.meshgrid(axes[0], axes[1], axes[2], indexing="ij")
    coords = np.stack([X, Y, Z], axis=-1)       # (nx, ny, nz, 3)
    extent = (float(lo[0]), float(hi[0]), float(lo[1]), float(hi[1]),
              float(lo[2]), float(hi[2]))
    return coords, extent
