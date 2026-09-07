# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""mesh_props — 三角形メッシュ(triangle mesh)の**接続情報**から直接測る幾何量。

差別化点(既存 op との棲み分け, honest):
  - ``curvature3d`` / ``normals_orient`` / ``transform.estimate_point_normals`` … いずれも
    **点群 (N,3)** を入力に、近傍探索(kNN)と PCA(共分散の固有ベクトル)で法線・曲率を
    *推定* する。面の接続(どの頂点がどの三角形を作るか)は使わない。ゆえに法線の符号は
    未定(向き付けに別工程が要る)で、曲率も近傍半径に依存する近似。
  - **本モジュール** … 入力は **mesh = (vertices (N,3) float, faces (M,3) int)**。marching cubes
    (``match3d.voxel_to_mesh`` / ``recon3d.poisson_lite`` / ``recon3d.alpha_shape_mesh``)が
    返すそのままの表現を受け、**面の巻き順(winding)から一貫した向き**の法線と、**接続に基づく
    離散微分幾何**(cotangent Laplacian)で曲率を求める。近傍探索も PCA も使わない別系統。

提供 op(すべて mesh in):
  - ``face_normals(mesh)``    → (M,3) 各三角形の単位法線(辺の外積=巻き順で向き決定)。
  - ``vertex_normals(mesh)``  → (N,3) 面積重み付きで集約した頂点法線(向きは面から一貫)。
  - ``mesh_area(mesh)``       → float  全三角形面積の総和(表面積)。
  - ``vertex_curvature(mesh)``→ (N,)  各頂点の平均曲率の大きさ(Meyer 2003 の
    cotangent Laplace-Beltrami 作用素 |K|/2。K = (1/2A_mixed)Σ(cotα+cotβ)(p_i−p_j))。

GT で検証できる理由: 半径 R の球なら 表面積=4πR²、平均曲率=1/R、頂点法線は放射方向 p/|p|
と厳密に一致する(examples_3d/mesh_props.py で数値アサート)。

numpy in / numpy out。scipy 不要(接続演算は np.add.at の散布のみ)。エラー処理は省略せず、
形状不正・範囲外 index・退化(ゼロ面積面・孤立頂点)は fail-closed で ValueError を送出する。

Reference (public): M. Meyer, M. Desbrun, P. Schröder, A. H. Barr,
"Discrete Differential-Geometry Operators for Triangulated 2-Manifolds",
Visualization and Mathematics III, 2003.
"""
from __future__ import annotations

import numpy as np

__all__ = ["face_normals", "vertex_normals", "mesh_area", "vertex_curvature",
           "face_areas", "mesh_volume", "boundary_vertices"]

# ゼロ面積(退化)三角形を「法線が定義できない」と見なすしきい値。外積ノルム(=2·面積)を
# メッシュ全体の代表スケールで正規化した**無次元**量で判定し、座標スケールに依存しない。
_DEGEN_REL = 1e-9


def _as_mesh(mesh) -> tuple[np.ndarray, np.ndarray]:
    """入力を (vertices (N,3) float64, faces (M,3) int64) へ検証・正規化。fail-closed。

    mesh は (vertices, faces) の 2 要素シーケンス。形状不正・非有限・非整数 index・範囲外
    index・空配列はすべて ValueError(退化を捏造して黙って空を返さない)。
    """
    if not (isinstance(mesh, (tuple, list)) and len(mesh) == 2):
        raise ValueError(
            "mesh must be a 2-element tuple (vertices, faces)"
            f" (got: {type(mesh).__name__})")
    V = np.asarray(mesh[0], dtype=np.float64)
    F_raw = np.asarray(mesh[1])
    if V.ndim != 2 or V.shape[1] != 3:
        raise ValueError(f"vertices must be (N,3) (got shape={V.shape})")
    if not np.isfinite(V).all():
        raise ValueError("vertices contain NaN/Inf")
    if F_raw.ndim != 2 or F_raw.shape[1] != 3:
        raise ValueError(f"faces must be (M,3) (got shape={F_raw.shape})")
    if not np.issubdtype(F_raw.dtype, np.integer):
        if not np.all(np.isfinite(F_raw)) or not np.all(np.equal(np.mod(F_raw, 1.0), 0.0)):
            raise ValueError("faces must be integer vertex indices (non-integer values detected)")
    F = F_raw.astype(np.int64)
    if len(V) == 0:
        raise ValueError("vertices is empty")
    if len(F) == 0:
        raise ValueError("faces is empty")
    if F.min() < 0 or F.max() >= len(V):
        raise ValueError(
            f"faces has out-of-range vertex indices (valid range [0,{len(V)}))"
            f": min={int(F.min())}, max={int(F.max())}")
    # 構造検証: 三角形は 3 頂点が相異なる必要がある(index 重複 = 退化した接続)。
    degen_conn = (F[:, 0] == F[:, 1]) | (F[:, 1] == F[:, 2]) | (F[:, 0] == F[:, 2])
    if np.any(degen_conn):
        raise ValueError(
            f"{int(degen_conn.sum())} face(s) reference a duplicate vertex"
            " (a triangle's 3 vertices must be distinct)")
    return V, F


def _face_cross(V: np.ndarray, F: np.ndarray) -> np.ndarray:
    """各三角形の外積ベクトル cross(v1−v0, v2−v0) を返す。→ (M,3)。

    向きは faces の巻き順で決まり、ノルムは 2·(三角形面積)。単位法線は正規化、面積重み付き
    頂点法線はこのベクトルをそのまま散布(重み=2·面積)、面積はノルムの半分で得られる。
    """
    tri = V[F]                              # (M,3,3)
    e1 = tri[:, 1] - tri[:, 0]
    e2 = tri[:, 2] - tri[:, 0]
    return np.cross(e1, e2)


def face_normals(mesh) -> np.ndarray:
    """三角形メッシュの**面法線**(各三角形の単位法線ベクトル)。→ (M,3)。

    法線 = 正規化した cross(v1−v0, v2−v0)。向きは **faces の巻き順(winding)** から一貫して
    決まる(PCA のような符号未定さは無い)。閉じたメッシュを外向き巻きで作れば全法線が外向き。

    Args:
        mesh: (vertices (N,3), faces (M,3)) のタプル。

    Returns:
        (M,3) の単位面法線。

    Raises:
        ValueError: 形状不正・範囲外 index、または退化(ゼロ面積)三角形で法線が定義できないとき。
    """
    V, F = _as_mesh(mesh)
    cr = _face_cross(V, F)
    mag = np.linalg.norm(cr, axis=1)
    scale = float(np.median(mag[mag > 0])) if np.any(mag > 0) else 0.0
    degen = mag <= _DEGEN_REL * scale if scale > 0 else mag <= 0
    if np.any(degen):
        raise ValueError(
            f"{int(degen.sum())} degenerate (zero-area) triangle(s); face normals cannot be defined")
    return cr / mag[:, None]


def vertex_normals(mesh) -> np.ndarray:
    """三角形メッシュの**頂点法線**(面積重み付きで集約した単位法線)。→ (N,3)。

    各三角形の外積ベクトル(=面法線×2·面積)を、その 3 頂点へ散布加算し、頂点ごとに正規化する。
    大きい(重要な)面ほど寄与が大きい面積重み付き平均になり、向きは面の巻き順から一貫する。
    ``normals_orient.estimate_normals``(点群 PCA・符号未定)と違い、追加の向き付け工程は不要。

    Args:
        mesh: (vertices (N,3), faces (M,3)) のタプル。

    Returns:
        (N,3) の単位頂点法線。

    Raises:
        ValueError: 形状不正・範囲外 index、または法線が定義できない頂点(入射面が無い/
            寄与が相殺してゼロ)があるとき。
    """
    V, F = _as_mesh(mesh)
    cr = _face_cross(V, F)                  # (M,3) 面積重み付きベクトル
    vn = np.zeros_like(V)                   # (N,3)
    for c in range(3):                      # 各面を構成する 3 頂点へ散布
        np.add.at(vn, F[:, c], cr)
    mag = np.linalg.norm(vn, axis=1)
    scale = float(np.median(mag[mag > 0])) if np.any(mag > 0) else 0.0
    bad = mag <= _DEGEN_REL * scale if scale > 0 else mag <= 0
    if np.any(bad):
        raise ValueError(
            f"{int(bad.sum())} vertex(es) have no defined normal"
            " (no incident triangles, or face normals cancel out)")
    return vn / mag[:, None]


def mesh_area(mesh) -> float:
    """三角形メッシュの**表面積**(全三角形面積の総和)。→ float。

    面積 = Σ 0.5·|cross(v1−v0, v2−v0)|。頂点数に定数を掛ける素朴な近似ではなく、実際の面の
    大きさを積算するので、メッシュのスケール・形状に正しく追随する。

    Args:
        mesh: (vertices (N,3), faces (M,3)) のタプル。

    Returns:
        表面積(非負の float)。

    Raises:
        ValueError: mesh が (vertices, faces) の 2 要素でない、形状不正、非有限座標、非整数・
        範囲外の index、空、または 3 頂点のどれかが同じ index の三角形があるとき。

    注意: ``face_normals`` と違い、座標がほぼ一直線に並んだ退化三角形(面積 0)は拒否せず 0 として
    加算する。重複面や表裏 2 枚張りの面はそのまま 2 回数えられる。単位は座標の単位の 2 乗。
    """
    V, F = _as_mesh(mesh)
    cr = _face_cross(V, F)
    return float(0.5 * np.linalg.norm(cr, axis=1).sum())


def vertex_curvature(mesh) -> np.ndarray:
    """三角形メッシュの各頂点の**平均曲率の大きさ**(mean curvature magnitude)。→ (N,)。

    Meyer et al. (2003) の離散 Laplace-Beltrami 作用素:

        K(x_i) = (1 / (2·A_mixed_i)) · Σ_{j∈1-ring} (cot α_ij + cot β_ij)·(x_i − x_j)

    は平均曲率法線ベクトル K = 2·H·n に等しい(H=平均曲率, n=単位法線)。ここでは向きに依らない
    **大きさ** H_i = |K(x_i)| / 2 を返す。α_ij, β_ij は辺 (i,j) に相対する 2 つの角、A_mixed は
    Meyer の混合面積(非鈍角三角形は Voronoi 面積、鈍角三角形は面積の 1/2 か 1/4)で、素朴な
    重心面積より曲率推定が正確になる。

    半径 R の球(閉じた多様体)では全頂点で H ≈ 1/R(離散化誤差内)。平面の内部頂点では
    H ≈ 0。**限界(honest)**: cotangent Laplace-Beltrami は閉多様体/内部頂点でのみ妥当で、
    開いたメッシュの**境界頂点**(1-ring が閉じない)では値が発散的に不正確になる。閉じた
    メッシュ、または開メッシュの内部頂点にのみ意味がある。

    Args:
        mesh: (vertices (N,3), faces (M,3)) のタプル。

    Returns:
        (N,) の平均曲率の大きさ(非負)。境界頂点の値は上記の理由で信頼できない。

    Raises:
        ValueError: 形状不正・範囲外 index、または混合面積がゼロの頂点(退化)があるとき。
    """
    V, F = _as_mesh(mesh)
    N = len(V)
    i0, i1, i2 = F[:, 0], F[:, 1], F[:, 2]
    p0, p1, p2 = V[i0], V[i1], V[i2]

    # 各三角形の面積(外積ノルムの半分)。全 3 頂点の角で共通の分母 2·area を作る。
    cr = np.cross(p1 - p0, p2 - p0)
    twice_area = np.linalg.norm(cr, axis=1)         # = 2·area
    area = 0.5 * twice_area
    scale_a = float(np.median(area[area > 0])) if np.any(area > 0) else 0.0
    if np.any(area <= _DEGEN_REL * scale_a if scale_a > 0 else area <= 0):
        raise ValueError("degenerate (zero-area) triangle(s); curvature cannot be defined")

    # 各頂点における角の cotangent = (隣接 2 辺の内積) / (2·area)。
    # cot(∠at v0) は v0 の 2 辺 (p1−p0),(p2−p0) から、他も同様。
    cot0 = np.einsum("ij,ij->i", p1 - p0, p2 - p0) / twice_area
    cot1 = np.einsum("ij,ij->i", p0 - p1, p2 - p1) / twice_area
    cot2 = np.einsum("ij,ij->i", p0 - p2, p1 - p2) / twice_area

    # Laplace-Beltrami の分子 Σ(cotα+cotβ)(x_i − x_j) を 1-ring へ散布。
    # 辺 (1,2) に相対する角は v0 → 重み cot0、辺 (2,0)→v1 の cot1、辺 (0,1)→v2 の cot2。
    K = np.zeros((N, 3), dtype=np.float64)
    np.add.at(K, i1, cot0[:, None] * (p1 - p2))
    np.add.at(K, i2, cot0[:, None] * (p2 - p1))
    np.add.at(K, i2, cot1[:, None] * (p2 - p0))
    np.add.at(K, i0, cot1[:, None] * (p0 - p2))
    np.add.at(K, i0, cot2[:, None] * (p0 - p1))
    np.add.at(K, i1, cot2[:, None] * (p1 - p0))

    # Meyer の混合面積 A_mixed を頂点へ散布。
    #   非鈍角三角形: Voronoi 面積 (1/8)(|edge_a|²·cot(相対角) + |edge_b|²·cot(相対角))
    #   鈍角三角形  : 鈍角の頂点へ area/2、他 2 頂点へ area/4
    l01 = np.einsum("ij,ij->i", p0 - p1, p0 - p1)   # |p0−p1|²
    l12 = np.einsum("ij,ij->i", p1 - p2, p1 - p2)   # |p1−p2|²
    l20 = np.einsum("ij,ij->i", p2 - p0, p2 - p0)   # |p2−p0|²

    # Voronoi 寄与(頂点 v0: 辺 01→相対角 v2 の cot2、辺 20→相対角 v1 の cot1)。
    vor0 = (l01 * cot2 + l20 * cot1) / 8.0
    vor1 = (l01 * cot2 + l12 * cot0) / 8.0
    vor2 = (l20 * cot1 + l12 * cot0) / 8.0

    # 鈍角判定は各頂点の角の cos 符号(= 2 辺の内積符号)で行う。
    d0 = np.einsum("ij,ij->i", p1 - p0, p2 - p0) < 0.0   # v0 が鈍角
    d1 = np.einsum("ij,ij->i", p0 - p1, p2 - p1) < 0.0
    d2 = np.einsum("ij,ij->i", p0 - p2, p1 - p2) < 0.0
    tri_obtuse = d0 | d1 | d2

    a0 = np.where(tri_obtuse, np.where(d0, area / 2.0, area / 4.0), vor0)
    a1 = np.where(tri_obtuse, np.where(d1, area / 2.0, area / 4.0), vor1)
    a2 = np.where(tri_obtuse, np.where(d2, area / 2.0, area / 4.0), vor2)

    A_mixed = np.zeros(N, dtype=np.float64)
    np.add.at(A_mixed, i0, a0)
    np.add.at(A_mixed, i1, a1)
    np.add.at(A_mixed, i2, a2)

    scale_m = float(np.median(A_mixed[A_mixed > 0])) if np.any(A_mixed > 0) else 0.0
    if np.any(A_mixed <= _DEGEN_REL * scale_m if scale_m > 0 else A_mixed <= 0):
        raise ValueError(
            "vertex(es) with zero mixed area; curvature cannot be defined (isolated/degenerate connectivity)")

    Kvec = K / (2.0 * A_mixed[:, None])             # = 2·H·n(平均曲率法線)
    return 0.5 * np.linalg.norm(Kvec, axis=1)       # H = |K|/2(向きに依らない大きさ)


# --------------------------------------------------------------------------- #
# 2026-09-07 追加。DFM の PoC が「面ごとの面積 × 法線の判定」を書くのに、       #
# ``mesh_area`` が総和しか返さないので外積を自前で書いていた(KNOWN_ISSUES     #
# §41.12)。体積と境界も同じ理由で足す —— ``mesh_edge_stats`` は面積の分位数と #
# 境界辺の**本数**は返すが、面ごとの値も境界の**場所**も返さない。            #
# --------------------------------------------------------------------------- #
def face_areas(mesh) -> np.ndarray:
    """三角形メッシュの**面ごとの面積** → ``(M,)``。

    面積 = ``0.5·|cross(v1−v0, v2−v0)|`` を面ごとに返す(``mesh_area`` はこの総和)。
    面積は**重み**として使うためにある —— 「下を向いた面の面積」「公差外の面積」
    「曲率の面積加重平均」はすべて面ごとの面積が要る量で、総和からは作れない。

    Args:
        mesh: ``(vertices (N,3), faces (M,3))`` のタプル。

    Returns:
        ``(M,)`` の float64(非負)。順序は ``faces`` の順で、``face_normals`` と同じ
        並びなので ``areas[normals[:, 2] < 0].sum()`` のように直接組み合わせられる。

    Raises:
        ValueError: ``mesh`` が ``(vertices, faces)`` の 2 要素でない、形状不正、
        非有限座標、非整数・範囲外の index、空のとき。

    注意: ``mesh_area`` と同じく、退化三角形(面積 0)は**拒否せず 0 を返す**
    (``face_normals`` は法線が定義できないので拒否する —— 同じメッシュでも
    こちらは通る)。重複面・表裏 2 枚張りはそれぞれ 1 面として数える。
    単位は座標の単位の 2 乗。"""
    V, F = _as_mesh(mesh)
    return 0.5 * np.linalg.norm(_face_cross(V, F), axis=1)


def mesh_volume(mesh) -> float:
    """閉じた三角形メッシュが囲む**符号付き体積** → float。

    発散定理(divergence theorem)で ``V = (1/6)·Σ v0 · (v1 × v2)``。面の巻き順が外向き
    (右手系)なら正、内向きなら負になる —— **符号は向きの検査そのもの**で、負が
    返ったら法線が裏返っている。

    Args:
        mesh: ``(vertices (N,3), faces (M,3))`` のタプル。

    Returns:
        符号付き体積(float、座標の単位の 3 乗)。

    Raises:
        ValueError: ``mesh`` が ``(vertices, faces)`` の 2 要素でない、形状不正、
        非有限座標、非整数・範囲外の index、空のとき。

    ★**`voxel_to_mesh`(marching cubes)の返りは内向き巻きなので、そのまま渡すと
    負になる**(実測: 1000 voxel の立方体で -985.67)。「負 = 法線が裏返っている」
    のは正しいが、**この組み合わせでは裏返っているのが既定**なので、体積が欲しい
    だけなら ``abs()`` を取るか ``faces[:, ::-1]`` で巻き直すこと。向きの検査に
    使うのは、巻き順を自分で決めた(または向きを揃えた)メッシュに対して。

    **限界(honest)**: 発散定理は**閉じた曲面でのみ**成り立つ。開いたメッシュ
    (穴のあるスキャン)に対しても数値は返るが、それは「穴を原点へ向かって
    塞いだ立体の体積」であって、欲しい量ではない。閉じているかどうかは
    :func:`boundary_vertices` が空か、``mesh_edge_stats`` の ``boundary_edges`` が
    0 かで**先に確かめること**。自己交差があるメッシュでは重なった領域が
    符号つきで二重に数えられる(これも定理どおりの挙動で、検出はしない)。

    Reference (public): 発散定理による多面体体積は標準的な公式。例えば
    C. Zhang & T. Chen, "Efficient feature extraction for 2D/3D objects in mesh
    representation", ICIP 2001。"""
    V, F = _as_mesh(mesh)
    v0, v1, v2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    return float(np.einsum("ij,ij->i", v0, np.cross(v1, v2)).sum() / 6.0)


def boundary_vertices(mesh) -> np.ndarray:
    """開いた縁(境界)に乗っている**頂点の index** → ``(K,)``。

    無向辺のうち**ちょうど 1 つの面にしか使われていない辺**(境界辺)の端点を集めて
    返す。閉じた多様体なら空配列 —— つまり ``len(boundary_vertices(mesh)) == 0`` が
    **水密性(watertight)の判定**になる。穴埋め・体積計算・曲率のどれも、境界の
    有無で意味が変わるので、先にここを見る。

    Args:
        mesh: ``(vertices (N,3), faces (M,3))`` のタプル。

    Returns:
        昇順・重複なしの ``(K,)`` int64。境界が無ければ ``shape == (0,)``。

    Raises:
        ValueError: ``mesh`` が ``(vertices, faces)`` の 2 要素でない、形状不正、
        非有限座標、非整数・範囲外の index、空のとき。

    **限界(honest)**: 返るのは頂点の集合で、**縁のループ(周回順)ではない**。
    穴が複数あっても 1 つの配列にまとまるので、穴ごとに分けたいなら連結成分を
    自分で辿ることになる(ループ抽出の op はまだ無い)。3 つ以上の面が共有する
    非多様体辺はここには出ない(``mesh_edge_stats`` の ``non_manifold_edges``)。"""
    V, F = _as_mesh(mesh)
    e = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]], axis=0)
    e = np.sort(e, axis=1)                      # 無向辺にそろえる
    uniq, counts = np.unique(e, axis=0, return_counts=True)
    return np.unique(uniq[counts == 1]).astype(np.int64)
