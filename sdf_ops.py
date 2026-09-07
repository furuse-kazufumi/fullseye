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
    "plane_sdf", "cylinder_sdf", "torus_sdf", "capsule_sdf",
]


# --------------------------------------------------------------------------- #
# CSG boolean composition (min/max algebra on signed distance fields)         #
# --------------------------------------------------------------------------- #
def sdf_union(a, b):
    """2 SDF の和集合 A∪B = 要素ごとの min(a, b)(内側=負がどちらかにあれば内側)。

    ゼロ等値面は両形状の境界の和集合に厳密一致。外側では厳密な SDF(最近表面までの距離)、
    内側は保守的下界。``a``/``b`` はブロードキャスト整合すればよい。

    計算: ``np.minimum(np.asarray(a, float64), np.asarray(b, float64))``。それ以外の
    検査はしない — shape がブロードキャストできなければ numpy の ``ValueError``、
    NaN は要素ごとに伝播する(``np.minimum`` は NaN を返す)。``±inf`` は厳密に伝播
    (``min(a, +inf) = a``:``esdf`` の「全自由なら +inf」契約と相互運用できる)。

    入力: 同一グリッド上で評価した 2 つの SDF(``sphere_sdf`` / ``box_sdf`` /
    ``esdf`` の出力など、内側負・外側正)。形は ``grid_coords`` の
    ``(nx, ny, nz)`` でも ``(N,)`` の点列でもよい。距離の単位は入力と同じ。

    返り値: ブロードキャスト後の shape の float64。ゼロ交差(``<= 0``)が A∪B の
    占有。

    注意: 内側の値は「どちらか近い方の表面までの距離」の下界であり、重なり領域では
    真の距離より小さめ(絶対値が大きめ)に出る。CSG の標準的性質で、等値面抽出
    (marching cubes)や ``sdf_offset`` の膨張には影響しない。継ぎ目を丸めたい場合は
    ``sdf_smooth_union``。"""
    a = np.asarray(a, np.float64)
    b = np.asarray(b, np.float64)
    return np.minimum(a, b)


def sdf_intersect(a, b):
    """2 SDF の積集合 A∩B = 要素ごとの max(a, b)(両方の内側でのみ内側)。

    ゼロ等値面は両境界の共通部分。外側で厳密 SDF、内側は保守的下界。

    計算: ``np.maximum(np.asarray(a, float64), np.asarray(b, float64))``。要素ごとの
    max なので、ある点が A∩B の内側(負)になるのは ``a < 0`` かつ ``b < 0`` のときだけ。
    shape はブロードキャスト整合していればよく(不整合なら numpy の ``ValueError``)、
    それ以外の検査はしない。NaN は伝播、``±inf`` は厳密に伝播(``max(a, -inf) = a``)。

    入力: 同一グリッド上で評価した 2 つの SDF(``sphere_sdf`` / ``box_sdf`` /
    ``esdf`` の出力など、内側負・外側正)。距離の単位は入力と同じ。

    返り値: ブロードキャスト後の shape の float64。``<= 0`` が A∩B の占有。

    注意:
    - **外側の値は真の距離より小さく出うる**: 交差の外側で、点が A の外かつ B の外の
      とき ``max(a, b)`` は「遠い方の表面まで」の距離で、A∩B の表面はそれより遠い
      ことがある(下界)。ゼロ等値面は厳密。
    - 共通部分が無ければ全要素が正(占有 0)になり、エラーにはならない。
    - 箱で球を切る・2 つの箱で角柱を作る、といった CSG の「切り出し」に使う。
      A から B を抜くのは ``sdf_subtract``。"""
    a = np.asarray(a, np.float64)
    b = np.asarray(b, np.float64)
    return np.maximum(a, b)


def sdf_subtract(a, b):
    """差集合 A\\B = max(a, -b)(A の内側 かつ B の外側 = ``-b`` の内側)。

    ``b`` の符号反転は「B の外を内、B の内を外」に反転する(相補集合)ので、A との積が
    A から B をくり抜いた形になる。非可換: ``sdf_subtract(a,b) != sdf_subtract(b,a)``。

    計算: ``np.maximum(np.asarray(a, float64), -np.asarray(b, float64))``。
    ``sdf_intersect(a, -b)`` と同じ。shape はブロードキャスト整合が必要(不整合なら
    numpy の ``ValueError``)で、それ以外の検査はしない。NaN は伝播、``±inf`` も
    厳密に伝播する(``b = +inf`` の点は ``-b = -inf`` なので ``a`` がそのまま残る =
    「B が無限に遠い」点は A のまま)。

    入力: 同一グリッド上の 2 つの SDF(内側負・外側正)。``a`` が残す形、``b`` が
    くり抜く形。距離の単位は入力と同じ。

    返り値: ブロードキャスト後の shape の float64。``<= 0`` が A\B の占有。

    注意:
    - B の内側で値は ``-b > 0``(B の表面までの距離)になるので、くり抜いた穴の内壁
      までの距離は外側では厳密、A の内側では下界(CSG の標準的性質)。
    - B が A を完全に含むと全要素が正(空集合)。エラーにはならない。
    - 穴あけ・ポケット加工・殻(``a`` と ``sdf_offset(a, -t)`` の差で厚さ ``t`` の
      殻)に使う。"""
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
    クリアランス確保に使う。

    計算: ``np.asarray(sdf, float64) - float(r)``。``r`` はスカラのみ(配列を渡すと
    ``float()`` で ``TypeError``)。単位は ``sdf`` の距離単位と同じ。``r = 0`` は恒等。
    shape・NaN・inf の検査はしない(``inf - r = inf`` で契約どおり伝播)。

    幾何的意味: 厳密な SDF に対しては Minkowski 和(``r > 0`` で半径 ``r`` の球で
    膨張、``r < 0`` で収縮)に一致する。``sphere_sdf(g, c, R)`` に ``r`` を掛けると
    ``sphere_sdf(g, c, R + r)`` と厳密に等しい。``box_sdf`` の膨張では角が丸くなる
    (ユークリッド膨張なので、箱が大きくなるのではなく角 R = r の丸箱になる)。

    注意:
    - 収縮(``r < 0``)で ``|r|`` が最小内接半径を超えると形は消える(全要素が正)。
      エラーにはならない。
    - ``sdf_union`` / ``sdf_intersect`` の**内側**は真の距離の下界なので、合成後に
      ``r < 0`` で収縮すると、重なり領域で実際より多く削れることがある。
    - 厚さ ``t`` の殻: ``sdf_subtract(sdf, sdf_offset(sdf, -t))``。"""
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

    Raises ValueError for R<0 or malformed grid/center。

    計算: ``np.linalg.norm(grid - center, axis=-1) - R``。座標の単位はそのまま距離の
    単位になる(``grid_coords`` の world 座標を渡せば world 単位)。座標の成分順は
    ``grid`` の最終軸の順(``grid_coords`` なら ``(x, y, z)``)で、``center`` も同じ順。

    引数と検証(``ValueError``):
    - ``grid``: 最終軸が 3 の float 配列 ``(..., 3)``(1-D の ``(3,)`` も可。0-D や
      最終軸が 3 以外は拒否)。
    - ``center``: 要素数 3(``reshape(3)`` できなければ numpy の ``ValueError``)。
    - ``R``: ``float()`` できるスカラ。回転行列などを渡した場合も ``ValueError``
      (この引数は半径であって姿勢ではない)。``R < 0`` は拒否、``R = 0`` は
      中心からの距離場そのもの。

    返り値: ``grid.shape[:-1]`` の float64(``grid_coords`` の出力なら
    ``(nx, ny, nz)``)。中心で ``-R``、表面で 0、外側で正。

    使いどころ: ``grid_coords`` で格子 → ``sphere_sdf`` / ``box_sdf`` → ``sdf_union`` /
    ``sdf_subtract`` で CSG → ``<= 0`` を占有として marching cubes(``voxel_to_mesh``
    に ``-sdf`` を渡し ``iso=0`` 相当で等値面)。"""
    g = _as_coords(grid)
    c = np.asarray(center, np.float64).reshape(3)
    try:                                        # R は**半径のスカラ**(回転行列ではない)
        R = float(R)
    except (TypeError, ValueError) as exc:      # fail-closed: 生の TypeError を漏らさない
        raise ValueError(
            "sphere_sdf: R must be a scalar radius, not %r — note this argument is a "
            "radius, not a rotation matrix" % (type(R).__name__,)) from exc
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


# --------------------------------------------------------------------------- #
# 追加のプリミティブ(2026-09-07)                                              #
#                                                                             #
# ★足した理由は実測: `poc_dfm_thickness_overhang` と `poc_cad_scan_deviation` が    #
# 「機械部品は円筒穴・面取り・フィレットでできているのに、プリミティブが球と       #
# 直方体しか無いので CSG で組めない」と報告し、両方とも面ごとの解析式を自前で       #
# 書いていた。ここにある 4 つは**すべて閉形式で厳密**(外側は最近表面までの        #
# ユークリッド距離、内側は最近面までの負値)なので、真値を持つ合成部品を           #
# CSG だけで組めるようになる。                                                  #
# --------------------------------------------------------------------------- #
def _axis_frame(axis):
    """軸ベクトルを正規化して返す(退化は fail-closed)。"""
    a = np.asarray(axis, np.float64).reshape(3)
    n = np.linalg.norm(a)
    if not np.isfinite(n) or n <= 0:            # fail-closed: 零ベクトル/NaN の軸
        raise ValueError("axis must be a non-zero finite 3-vector")
    return a / n


def _split_axial_radial(g, center, axis):
    """点を軸方向成分 ``t`` と軸からの半径 ``r`` に分ける(``(..., )`` の 2 つ)。"""
    a = _axis_frame(axis)
    c = np.asarray(center, np.float64).reshape(3)
    d = g - c                                   # (..., 3)
    t = d @ a                                   # 軸方向の符号つき距離
    perp = d - t[..., None] * a                 # 軸に直交する成分
    return t, np.linalg.norm(perp, axis=-1)


def plane_sdf(grid, point, normal):
    """半空間(平面で切った側)の**厳密**な符号付き距離場(内側負・外側正)。

    ``sdf(p) = (p - point) · n̂``。法線 ``n̂`` の**指す側が外側(正)**で、反対側が内側。
    面取り(chamfer)・切断・「基板から上だけ」のような**片側だけを残す**演算に使う。
    ``sdf_intersect`` を重ねれば任意の凸多面体が作れる(6 枚で直方体 = ``box_sdf`` と一致)。

    厳密性: 平面は全空間で勾配ノルム 1 なので、この値は**どこでも真の符号付き距離**
    (``box_sdf`` のように角で切り替わる場合分けが要らない)。

    引数と検証(``ValueError``):
    - ``grid``: 最終軸が 3 の float 配列 ``(..., 3)``(``grid_coords`` の出力または点列)。
    - ``point``: 平面上の 1 点(要素数 3)。
    - ``normal``: 平面の法線(要素数 3、**零ベクトル・NaN は拒否**)。長さは自動で 1 に
      正規化するので、大きさは結果に影響しない(向きだけが意味を持つ)。

    返り値: ``grid.shape[:-1]`` の float64。法線側で正、反対側で負、平面上で 0。

    使いどころ: ``sdf_subtract(part, plane_sdf(g, p, n))`` で「その平面より法線側を削る」。
    向きを逆にしたいときは ``normal`` の符号を反転する(``-sdf`` でも同じ)。"""
    g = _as_coords(grid)
    p0 = np.asarray(point, np.float64).reshape(3)
    n = _axis_frame(normal)
    return (g - p0) @ n


def cylinder_sdf(grid, center, axis, radius, height):
    """有限長の円柱(両端が平らな蓋)の**厳密**な符号付き距離場(内側負・外側正)。

    軸方向の距離 ``t`` と軸からの半径 ``r`` に分け、``q = (r - radius, |t| - height/2)``
    として ``outside = ‖max(q, 0)‖``、``inside = min(max(q), 0)``、``sdf = outside + inside``。
    これは ``box_sdf`` と同じ Quilez 流の構成を「(半径, 軸)の 2-D 断面」に適用したもので、
    側面・蓋・角(縁)のいずれに対しても真のユークリッド距離になる。

    引数と検証(``ValueError``):
    - ``grid``: 最終軸が 3 の float 配列 ``(..., 3)``。
    - ``center``: 円柱の**中心**(端面ではなく重心。要素数 3)。
    - ``axis``: 軸の向き(要素数 3、零ベクトル・NaN は拒否。長さは自動正規化)。
    - ``radius``: 半径 > 0 相当のスカラ(``0`` は軸線そのもの、負は拒否)。
    - ``height``: 全長のスカラ(``center`` から ±height/2。負は拒否)。

    返り値: ``grid.shape[:-1]`` の float64。

    使いどころ: **貫通穴は ``sdf_subtract(part, cylinder_sdf(...))``**(``height`` を部品より
    長くして端面の縁を残さない)。ボス・ピン・シャフトは ``sdf_union``。無限長の円柱が
    要るなら ``height`` を十分大きく取る(端面が評価域の外に出れば側面だけが効く)。"""
    g = _as_coords(grid)
    R = float(radius)
    H = float(height)
    if R < 0 or H < 0:                          # fail-closed: 負の寸法は無意味
        raise ValueError("radius and height must be non-negative")
    t, r = _split_axial_radial(g, center, axis)
    qr = r - R
    qt = np.abs(t) - 0.5 * H
    outside = np.sqrt(np.maximum(qr, 0.0) ** 2 + np.maximum(qt, 0.0) ** 2)
    inside = np.minimum(np.maximum(qr, qt), 0.0)
    return outside + inside


def torus_sdf(grid, center, axis, major_radius, minor_radius):
    """トーラス(ドーナツ)の**厳密**な符号付き距離場(内側負・外側正)。

    ``sdf(p) = ‖(r - major_radius, t)‖ - minor_radius``(``r`` は軸からの半径、``t`` は
    軸方向の距離)。芯線が半径 ``major_radius`` の円で、その周りに半径 ``minor_radius``
    の管が付いた形なので、**フィレット(隅の丸み)の解析形**としてそのまま使える。

    引数と検証(``ValueError``):
    - ``grid`` / ``center`` / ``axis``: :func:`cylinder_sdf` と同じ(軸はドーナツの穴の向き)。
    - ``major_radius``: 芯線の半径(負は拒否)。
    - ``minor_radius``: 管の半径(負は拒否)。``minor_radius >= major_radius`` だと穴が
      潰れた形になるが、距離場としては正しいので**拒否しない**。

    返り値: ``grid.shape[:-1]`` の float64。

    使いどころ: ``sdf_subtract`` で内隅にフィレットを削り出す / ``sdf_union`` で O リング溝の
    形を作る。角を丸めるだけなら ``sdf_smooth_union`` のほうが手軽だが、あちらは丸みの
    半径が形状に依存する —— **半径を設計値として持ちたいときはこちら**。"""
    g = _as_coords(grid)
    Rm = float(major_radius)
    rm = float(minor_radius)
    if Rm < 0 or rm < 0:                        # fail-closed
        raise ValueError("major_radius and minor_radius must be non-negative")
    t, r = _split_axial_radial(g, center, axis)
    return np.sqrt((r - Rm) ** 2 + t ** 2) - rm


def capsule_sdf(grid, a, b, radius):
    """線分 ``a``–``b`` を半径 ``radius`` で太らせたカプセルの**厳密**な符号付き距離場。

    ``sdf(p) = ‖p - (a + clamp(((p-a)·(b-a))/‖b-a‖², 0, 1)·(b-a))‖ - radius``。
    線分への最短距離そのものなので**全空間で勾配ノルム 1**(円柱と違い端が丸いぶん、
    角が無く厳密)。リブ・配管・骨・ワイヤ・工具の掃引体積の近似に向く。

    引数と検証(``ValueError``):
    - ``grid``: 最終軸が 3 の float 配列 ``(..., 3)``。
    - ``a`` / ``b``: 芯線の端点(要素数 3)。``a == b`` なら球(``sphere_sdf`` と一致)。
    - ``radius``: 太さ(負は拒否)。

    返り値: ``grid.shape[:-1]`` の float64。

    使いどころ: 工具の到達性を「工具の掃引体積が部品と交わらないか」で見るとき、工具を
    カプセルで置いて ``sdf_intersect`` の最小値が正かを見る。骨梁・血管・繊維の合成にも。"""
    g = _as_coords(grid)
    pa = np.asarray(a, np.float64).reshape(3)
    pb = np.asarray(b, np.float64).reshape(3)
    rr = float(radius)
    if rr < 0:                                  # fail-closed
        raise ValueError("radius must be non-negative")
    ab = pb - pa
    denom = float(ab @ ab)
    d = g - pa                                  # (..., 3)
    if denom <= 0:                              # a == b: 球に退化(厳密に正しい)
        return np.linalg.norm(d, axis=-1) - rr
    h = np.clip((d @ ab) / denom, 0.0, 1.0)
    return np.linalg.norm(d - h[..., None] * ab, axis=-1) - rr
