# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""cadmap — 画像上の観測を CAD 面上の座標へ落とす**逆写像**(numpy のみ)。

動機(2026-09-02)は fullseye 自身の空白の実測(`docs/INDUSTRY_SIGNALS.md` §3 の
行 6)。既存の 3-D スタックは **姿勢までは出せる**(`pipeline3d.align_cad_to_scan`
= FPFH で mesh↔点群、ICP 3 種、`ppf` 一式)が、**そこで終わっている**。
「2-D 画像上で見つけた欠陥が CAD 面上のどの座標か」に落とす経路が 1 つも無い。
本モジュールはその出口で、**画素 → 光線 → 三角形交差 → 重心座標**という
完全な閉形式だけで組んである(学習なし・レンダラなし・torch なし)。

来歴は公開文献のみ(`docs/PROVENANCE.md` の naming rule に従い、特定の製品・
企業を動機にも名前にも使わない):

  * Möller & Trumbore, "Fast, Minimum Storage Ray/Triangle Intersection",
    *Journal of Graphics Tools* 1997 — 光線×三角形の交差と重心座標。
  * Hartley & Zisserman, *Multiple View Geometry* 2nd ed. 2004 §6.1 — ピンホール
    投影と逆投影(光線の生成)。
  * Catmull 1974 の z-buffer と同じ**最近傍のみ可視**という遮蔽規約。ただし
    ここではラスタライズではなく光線ごとの最小 t で決める。
  * 面積要素 dA = Z^2 cosα / (fx fy |cosθ|) は透視投影のヤコビアン(標準的な
    立体角 dΩ = cos^3α/(fx fy) と dA = ρ^2 dΩ / |cosθ|、ρ = Z/cosα の合成)。

--------------------------------------------------------------------------
座標規約 — **`camera.py` に合わせてある**(合わせたことをここに明記する)
--------------------------------------------------------------------------
本モジュールは :mod:`camera` の OpenCV 系規約をそのまま使う。**`render3d` の
規約とは違う**ので、両者を混ぜてはならない:

  * カメラは **+Z** を向く(``render3d`` は -Z)。可視点は ``Z > 0``。
  * ``X_cam = R @ X_world + t``(``camera.project_points`` と同じ引数)。
  * ``u = fx*X/Z + cx``(**列**), ``v = fy*Y/Z + cy``(**行**)。``v`` は下向きに
    増える。``render3d`` は ``sv = cy - fy*(Y/depth)`` で符号が逆。
  * **画素の中心は整数座標**。画素 ``(row=i, col=j)`` の中心は ``(u, v) = (j, i)``
    で、``camera.depth_to_points`` の ``v, u = np.mgrid[0:H, 0:W]`` と一致する。
    ``render3d`` の ``arange + 0.5`` とは半画素ずれるので、片方の depth 画像を
    もう片方の規約で読むと**黙って半画素ずれる**。
  * ``depth`` はカメラ座標の Z(視線方向の距離ではない)。

mesh は本 repo の ``mesh`` sort、すなわち **``(V, F)`` タプル**をそのまま 1 引数
で受ける(``meshrepair.convex_hull`` の返りと同じ形)。``V`` は (nv, 3) float、
``F`` は (nf, 3) int。面の巻き方は **外から見て反時計回り**(外向き法線
``(B-A) x (C-A)``)を仮定する — STL / ``convex_hull`` / 多くの CAD 出力の規約で、
``cull_backfaces=True`` の既定はこの仮定に依存する。巻きが混在した mesh では
裏面判定が意味を失うので、その場合は ``cull_backfaces=False`` にすること。

**内向きに巻かれた閉メッシュは黙って受け取らない**(2026-09-02 の実バグ、
:func:`_orient_for_culling` を参照)。``cull_backfaces=True`` のとき、閉じて
いる(全ての無向辺がちょうど 2 面で共有される)のに符号つき体積が負なら、
既定では**巻きを直したうえでその事実を返り値の ``winding_fixed`` に載せる**。
``strict=True`` を渡すと直さずに ``ValueError`` で拒否する。

--------------------------------------------------------------------------
黙って間違えないための設計(fail-closed)
--------------------------------------------------------------------------
  * **当たらない画素には最寄りの面を返さない**。``face_id = -1``、``bary`` /
    ``point`` / ``depth`` は ``NaN``、``hit = False``。最近傍探索は一切しない。
  * **裏面は当たりにしない**(既定)。Möller-Trumbore の ``det > 0`` が
    「法線がカメラを向いている」と同値なので、判定は交差計算そのものの中で
    終わる(後段の別判定を足していないので、両者がずれることが起きない)。
  * **内向き巻きの閉メッシュを黙って通さない**。裏面カリングは巻き方向の符号に
    依存するので、内向きのまま通すと「自分自身の手前の壁」がカリングされ、
    光線が部品を突き抜けて**裏側の点まで可視**になる。実測(1400 面の部品・
    同一カメラ): 内向きだと ``cad_surface_to_pixel`` の可視率 0.861 に対し
    「面法線がカメラを向く面積比」は 0.517 ―― 遮蔽は可視を**減らす**ことしか
    できないので、この 2 つの大小が逆転した時点で物理的にあり得ない。外向きに
    直すと 0.412 / 0.483 で整合する。判定は 1 箇所(:func:`_orient_for_culling`)
    で行い、``cull_backfaces`` を使う 4 つの op すべてが共有する。
  * **遮蔽は返り値で区別できる**。``cad_surface_to_pixel`` は投影した画素を
    返すと同時に ``occluded`` / ``occluder_face`` / ``in_front`` / ``in_image``
    を返し、``visible`` はその論理積。隠れている点の画素座標を「見えている」
    かのように返すことはない。
  * **str / bool / complex を明示的に拒否**する。``float("50")`` は成功して
    しまうので、``np.asarray(x, np.float64)`` に落とす前に **dtype.kind を
    ``"iuf"`` に限定**する。スカラ引数も ``isinstance`` で bool / str / complex を
    先に弾く(``bool`` は ``int`` の派生なので順序が重要)。
  * **画素数 × 面数の総当たりに上限**(``MAX_RAY_FACE_TESTS``)。上限判定は
    **float64 への昇格より前**、配列の形だけから行う(昇格後に置くと、上限で
    守ったつもりの割り当てが既に済んでいる)。実際の計算も
    ``RAY_CHUNK_TESTS`` 要素ごとに分割するので、上限内でもピークメモリは一定。
  * ``R`` は直交性を検査する(``||R R^T - I||_inf > 1e-6`` で拒否)。非直交な
    ``R`` を渡すとカメラ中心 ``C = -R^T t`` が黙って別の場所になる。
  * 面数 0 の mesh、非有限の頂点、特異な ``K`` はすべて ``ValueError``。

使い方::

    import cadmap
    rec = cadmap.cad_pixel_to_surface((V, F), uv, K=K, R=R, t=t)
    rec["face_id"], rec["bary"], rec["point"]
    tbl = cadmap.cad_defect_to_cad((V, F), labels, K=K, R=R, t=t)
"""
from __future__ import annotations

import numpy as np

import camera
import render3d

__all__ = [
    "cad_pixel_to_surface", "cad_surface_to_pixel", "cad_defect_to_cad",
    "cad_visible_faces",
    "MAX_RAY_FACE_TESTS", "RAY_CHUNK_TESTS", "DEFAULT_IMAGE_SIZE",
]

#: 1 回の呼び出しで許す「光線 × 面」の総当たり回数の上限。超えたら
#: ``ValueError``。**形だけから float 演算で判定**するので、int の桁あふれも
#: 巨大配列の確保も起きない。
MAX_RAY_FACE_TESTS = 1 << 28          # 268,435,456 テスト

#: 交差計算 1 チャンクあたりの中間要素数。ピークメモリはおよそ
#: ``RAY_CHUNK_TESTS * 8 byte * (作業配列の本数)`` で頭打ちになる。
RAY_CHUNK_TESTS = 1 << 19             # 524,288 要素/チャンク

#: ``image_size`` を省略し、かつ画素から推定もできないときの既定の画像サイズ。
DEFAULT_IMAGE_SIZE = (256, 256)       # (width, height)

#: 重心座標の許容(辺・頂点をどちらの面にも属さなくしないための緩め)。
#: 重心座標は無次元 [0, 1] なので絶対値で持ってよい。``render3d._BARY_EPS`` と
#: 同じ値にしてある(両者で同じ点の内外判定が割れないように)。
_BARY_EPS = 1e-9
#: 「光線と平行 / 面積 0 の三角形」を弾く行列式のしきい値。**相対**で持つ:
#: ``det = e1 . (d x e2)`` は ``|e1| |e2| |d| sin(...)`` の次元なので、絶対値で
#: 持つと mesh の単位に依存する。実測で見つけた実バグ ―― 1e-12 の絶対値だと
#: **1 辺 1 um の mesh(``|e1||e2| ~ 1e-12``)で全画素が例外なく miss** になり、
#: 「CAD の外に欠陥がある」という嘘の表を返していた(m 単位では正しく動くので
#: 単体試験では見えない)。相対にすれば 1e-6 倍でも 1e+6 倍でも同じ結果になる。
_DET_EPS_REL = 1e-12
#: 光線パラメータ(= カメラ座標 Z)の下限を作る**相対**係数。絶対値で持つと
#: mesh の単位(m か mm か um か)に依存して、小さな部品で全画素が miss する。
#: 実効しきい値は ``_T_EPS_REL * bbox 対角``(1.0 で下限を切らない — 切ると 1um の部品で全画素が miss する)。
_T_EPS_REL = 1e-12


# --------------------------------------------------------------------------- #
# 型と単位の門番(str / bool / complex を「たまたま通る」前に落とす)          #
# --------------------------------------------------------------------------- #
def _real_array(a, name: str) -> np.ndarray:
    """実数値の ndarray へ。``float("50")`` が通ってしまう経路を塞ぐ。

    ``np.asarray(x, np.float64)`` は ``["1", "2"]`` を黙って 1.0, 2.0 にするので、
    **dtype を見てから**変換する。許すのは整数 / 符号なし整数 / 浮動小数のみ
    (``bool`` は ``kind == "b"`` なのでここで落ちる)。"""
    arr = np.asarray(a)
    if arr.dtype.kind not in "iuf":
        raise ValueError(
            "%s must be a real numeric array (int/float); got dtype %r — "
            "strings, bools, complex and object arrays are refused because "
            "float(\"50\") would silently succeed" % (name, str(arr.dtype)))
    out = arr.astype(np.float64)
    if out.size and not np.isfinite(out).all():
        raise ValueError("%s contains non-finite values (NaN/Inf)" % name)
    return out


def _int_array(a, name: str, allow_bool: bool = False) -> np.ndarray:
    """整数値の ndarray へ(面インデックス・ラベル画像)。

    浮動小数は**値が整数のときだけ**受け入れる — 連結成分ラベルを float で
    持つ op が実在するため。小数を持つ配列は拒否(ラベルとして意味がない)。
    ``allow_bool`` は**ラベル画像にだけ**立てる: 真偽マスクは「欠陥領域 1 つ」と
    いう曖昧さのない意味を持ち、``float("50")`` のような黙った変換も起きない。
    座標や面インデックスでは立てない(``True`` が 1 番の頂点になるのは事故)。"""
    arr = np.asarray(a)
    if allow_bool and arr.dtype.kind == "b":
        return arr.astype(np.int64)
    if arr.dtype.kind in "iu":
        return arr.astype(np.int64)
    if arr.dtype.kind == "f":
        if arr.size and not np.isfinite(arr).all():
            raise ValueError("%s contains non-finite values (NaN/Inf)" % name)
        if arr.size and not np.array_equal(arr, np.round(arr)):
            raise ValueError(
                "%s is a float array with non-integral values; a label image "
                "must be integral" % name)
        return arr.astype(np.int64)
    raise ValueError(
        "%s must be an integer (or integral float) array; got dtype %r — "
        "strings, bools, complex and object arrays are refused" % (name, str(arr.dtype)))


def _num(x, name: str) -> float:
    """実スカラへ。bool / str / bytes / complex を**明示的に**拒否する。

    ``bool`` は ``int`` の派生なので ``isinstance(x, int)`` より先に見る必要が
    あり、``float("50")`` が成功するので ``str`` も明示的に落とす。"""
    if isinstance(x, (bool, np.bool_)):
        raise ValueError("%s must be a real number, got a bool" % name)
    if isinstance(x, (str, bytes, np.str_, np.bytes_)):
        raise ValueError("%s must be a real number, got a string "
                         "(float(\"50\") would silently succeed)" % name)
    if isinstance(x, (complex, np.complexfloating)):
        raise ValueError("%s must be a real number, got a complex value" % name)
    try:
        v = float(x)
    except (TypeError, ValueError):
        raise ValueError("%s must be a real number, got %r" % (name, type(x).__name__))
    if not np.isfinite(v):
        raise ValueError("%s must be finite, got %r" % (name, v))
    return v


def _size(x, name: str) -> int:
    """正の整数へ(画像の幅・高さ・画素数)。小数は拒否(黙って切り捨てない)。"""
    v = _num(x, name)
    if v != int(v):
        raise ValueError("%s must be a whole number, got %r" % (name, v))
    n = int(v)
    if n <= 0:
        raise ValueError("%s must be positive, got %d" % (name, n))
    return n


# --------------------------------------------------------------------------- #
# mesh / カメラの検証                                                         #
# --------------------------------------------------------------------------- #
def _mesh(m):
    """``mesh`` sort = ``(V, F)`` タプル → 検証済み ``(V float64, F int64)``。

    形とインデックス範囲の検査は :func:`render3d._mesh_arrays` を**再実装せず
    そのまま使う**(あちらが正典で、二重実装すると片方だけ直る事故になる)。
    ただしその前に dtype を自前で締める — ``mesh._finite_points`` は
    ``np.asarray(x, np.float64)`` なので、文字列の頂点を黙って数に変える。"""
    if isinstance(m, dict):
        if "vertices" not in m or "faces" not in m:
            raise ValueError("mesh dict must have 'vertices' and 'faces' keys")
        V, F = m["vertices"], m["faces"]
    elif isinstance(m, (tuple, list)) and len(m) == 2:
        V, F = m
    else:
        raise ValueError(
            "mesh must be the (vertices, faces) pair this library's `mesh` sort "
            "uses (e.g. the return of meshrepair.convex_hull), got %r"
            % (type(m).__name__,))
    Vv = _real_array(V, "mesh vertices")
    Ff = _int_array(F, "mesh faces")
    Vv, Ff = render3d._mesh_arrays(Vv, Ff, allow_empty_faces=False)
    return Vv, Ff


# --------------------------------------------------------------------------- #
# 巻き方向の門番(裏面カリングを使う全 op が共有する 1 箇所)                   #
# --------------------------------------------------------------------------- #
#: 「閉じているのに符号つき体積が負」を内向きと判定するときの**相対**しきい値。
#: 符号つき体積は長さの 3 乗なので、絶対値で持つと mesh の単位に依存する
#: (1 辺 1 um の部品は真の体積が 1e-18 で、絶対しきい値では常に「判定不能」に
#: 落ちる ―― ``_DET_EPS_REL`` で踏んだのと同じ罠)。実効しきい値は
#: ``_WINDING_VOL_EPS_REL * (bbox 対角)^3``。
_WINDING_VOL_EPS_REL = 1e-9


def _signed_volume(V: np.ndarray, F: np.ndarray) -> float:
    """閉メッシュの符号つき体積(発散定理 ``V = Σ A·(B×C) / 6``)。

    外向き巻きなら正、内向き巻きなら負。**閉じていない mesh では意味を持たない**
    ので、必ず :func:`_is_closed_surface` を通してから呼ぶ。

    積む前に **bbox 中心を原点へ寄せる**。閉曲面の符号つき体積は原点の取り方に
    依らない(発散定理の帰結)が、原点から遠い mesh をそのまま積むと大きな正負の
    打ち消しで有効桁が落ちる ―― 寄せておけば符号だけは確実に読める。"""
    c = 0.5 * (V.min(axis=0) + V.max(axis=0))
    tri = V[F] - c
    return float(np.einsum("ij,ij->i", tri[:, 0],
                           np.cross(tri[:, 1], tri[:, 2])).sum() / 6.0)


def _is_closed_surface(F: np.ndarray, n_vertices: int) -> bool:
    """**全ての無向辺がちょうど 2 面で共有される**か(= watertight)。

    符号つき体積が「内向き」を意味するのは閉曲面のときだけなので、巻き方向を
    見る前にここを通す。開いた mesh(1 枚の板、片側だけのスキャン)は符号つき
    体積が幾何と無関係な値になるため、**判定せず素通しする**のが正しい。

    ``meshrepair.is_watertight`` と同じ判定だが、あちらを import しない:
    ``meshrepair`` は scipy を要求し、本モジュールは **numpy だけで動く**という
    約束を持っている。この 6 行を二重に持つほうが、import 依存を 1 つ増やすより
    安い(``_mesh`` が ``render3d._mesh_arrays`` を再利用しているのは、あちらが
    既に numpy だけの依存にあるから)。

    辺は ``(lo, hi)`` を 1 つの int64 キーへ畳んでから ``np.unique`` する。
    ``np.unique(..., axis=0)`` は行ごとの比較になって面数が大きいと極端に遅く、
    ここは ``cull_backfaces=True`` の呼び出し全部で必ず通る経路だから。"""
    if F.shape[0] == 0:
        return False
    e = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]], axis=0)
    lo = np.minimum(e[:, 0], e[:, 1]).astype(np.int64)
    hi = np.maximum(e[:, 0], e[:, 1]).astype(np.int64)
    nv = int(n_vertices)
    if 0 < nv < 3037000499:                 # nv*nv が int64 に収まる範囲でだけ畳む
        counts = np.unique(lo * nv + hi, return_counts=True)[1]
    else:                                   # 桁あふれの恐れがあるときだけ遅い経路
        counts = np.unique(np.stack([lo, hi], axis=1), axis=0,
                           return_counts=True)[1]
    return bool(np.all(counts == 2))


def _orient_for_culling(V: np.ndarray, F: np.ndarray, cull_backfaces,
                        strict, op_name: str, reports: bool):
    """裏面カリングを掛ける前に巻き方向を検める **1 箇所**。→ ``(F, winding_fixed)``

    ``cull_backfaces`` を使う 4 つの op がすべてここを通る(同じ判定を 4 箇所に
    書くと、片方だけ直る事故になる)。

    判定は 3 段で、**手前の段で決まったら後ろは見ない**:

      1. ``cull_backfaces=False`` — 裏面判定そのものをしないので巻き方向は結果に
         **一切効かない**。検査もせず素通しし、``winding_fixed`` は常に ``False``。
         (内向きの mesh でも法線 ``normal`` の符号は入力の巻きどおりに返る。
         符号を外向きに揃えたいなら ``cull_backfaces=True`` で呼ぶこと。)
      2. **閉じているか**(全無向辺がちょうど 2 面)。閉じていなければ符号つき
         体積は意味を持たないので、やはり素通しする。開いた板を「内向き」と
         誤検出して壊さないための順序で、ここを飛ばしてはならない。
      3. 符号つき体積が負(``< -_WINDING_VOL_EPS_REL * 対角^3``)なら内向き。
         ``strict`` なら ``ValueError``、そうでなければ ``F[:, ::-1]`` で巻きを
         裏返して ``winding_fixed=True`` を返す。面の**行番号は変えない**ので
         ``face_id`` の意味は保たれ、``normal`` は外向きになる。

    限界を正直に書いておく: これは**全体の符号**しか見ないので、閉じたまま巻きが
    **混在**している mesh(半分だけ裏返っている)は捕まらない ―― 符号つき体積が
    たまたま正になりうるし、全部裏返しても直らない。その場合は
    ``cull_backfaces=False`` にするしかない(``meshrepair.orient_consistent``
    で直してから渡すのが本筋)。"""
    if not isinstance(cull_backfaces, (bool, np.bool_)):
        raise ValueError("cull_backfaces must be a bool")
    if not isinstance(strict, (bool, np.bool_)):
        raise ValueError("strict must be a bool")
    if not cull_backfaces:
        return F, False
    if not _is_closed_surface(F, V.shape[0]):
        return F, False
    vol = _signed_volume(V, F)
    diag = float(np.linalg.norm(V.max(axis=0) - V.min(axis=0)))
    if vol >= -(_WINDING_VOL_EPS_REL * diag ** 3):
        return F, False                      # 外向き、または符号を読めない退化形
    if strict:
        raise ValueError(
            "mesh is closed (watertight) but its signed volume is negative "
            "(%.6g): the faces are wound inward. cull_backfaces=True then culls "
            "the walls that are actually in front, rays pass straight through "
            "the part, and %s reports points on the far side as visible "
            "(measured on a 1400-face part: visible fraction 0.861 while only "
            "0.517 of the area even faces the camera - occlusion can only "
            "remove visibility, never add it). Fix the winding (F[:, ::-1], or "
            "meshrepair.orient_consistent), or pass cull_backfaces=False if the "
            "winding is genuinely mixed%s."
            % (vol, op_name,
               ", or strict=False to have this call flip it "
               "(the result then carries winding_fixed=True)" if reports else
               ", or strict=False to have this call flip it (note: this op "
               "returns a bare index array, so the fix cannot be reported in "
               "the return value - that is why it refuses by default)"))
    return np.ascontiguousarray(F[:, ::-1]), True


def _check_R(R) -> np.ndarray:
    R = _real_array(R, "R")
    if R.shape != (3, 3):
        raise ValueError("R must be 3x3, got %r" % (R.shape,))
    if np.abs(R @ R.T - np.eye(3)).max() > 1e-6:
        raise ValueError(
            "R is not a rotation (||R R^T - I||_inf = %.3g > 1e-6); the camera "
            "centre C = -R^T t would silently be somewhere else"
            % float(np.abs(R @ R.T - np.eye(3)).max()))
    return R


def _check_K(K) -> np.ndarray:
    K = _real_array(K, "K")
    K = render3d._check_intrinsics(K)          # 3x3 / 有限 / fx,fy != 0
    if abs(float(np.linalg.det(K))) < 1e-12:
        raise ValueError("K is singular (det = %.3g); pixels cannot be "
                         "back-projected to rays" % float(np.linalg.det(K)))
    # camera.project_points は uv = (X K^T)[:2] / **Z** と書いてあり、最終行が
    # [0,0,1] であることを暗黙に前提にしている。ここで検査しないと、最終行の
    # 違う K を渡したときに「順方向の投影」と「逆方向の光線」が別のカメラ
    # モデルになり、往復が黙ってずれる(例外は出ない)。
    if not np.allclose(K[2], [0.0, 0.0, 1.0], atol=1e-12):
        raise ValueError(
            "K's last row must be [0, 0, 1] (got %r); camera.project_points "
            "divides by the camera-frame Z, so any other last row makes the "
            "forward projection and this back-projection different cameras"
            % (K[2].tolist(),))
    return K


def _auto_camera(V: np.ndarray, width: int, height: int, fov_deg: float = 45.0):
    """mesh を画像へ収める既定カメラ ``(K, R, t)``(**camera.py 規約**)。

    ``R = I`` のまま、カメラを重心の ``-Z`` 側へ引き、``+Z`` 方向に見る。
    :func:`render3d.auto_view` と同じ「外接球を短辺に収める」計算だが、あちらは
    OpenGL 規約 (-Z 向き) の 4x4 を返すので**そのまま使うと符号が反転する**。
    ここは K の生成だけ :func:`render3d.intrinsics_from_fov` を再利用する。"""
    lo, hi = V.min(axis=0), V.max(axis=0)
    center = 0.5 * (lo + hi)
    radius = float(np.linalg.norm(V - center, axis=1).max())
    if not np.isfinite(radius) or radius <= 0.0:
        radius = 1.0
    K = render3d.intrinsics_from_fov(fov_deg, width, height)
    f = float(K[1, 1])
    dist = 1.2 * f * radius / max(0.5 * min(width, height), 1e-9)
    dist = max(dist, radius * 1e-3 + 1e-6)
    R = np.eye(3)
    t = -center + np.array([0.0, 0.0, dist])      # eye = center - [0,0,dist]
    return K, R, t


def _resolve_camera(V, K, R, t, width, height):
    """``K``/``R``/``t`` の欠けを :func:`_auto_camera` で補い、検証して返す。

    **一部だけ与えられた場合も残りを自動で埋める**が、そのとき実際に使われた
    カメラは返り値の ``camera`` に必ず入れる(既定に落ちたことを利用者が後から
    確かめられないと、数値の意味が分からなくなる)。"""
    aK, aR, at = _auto_camera(V, width, height)
    K = aK if K is None else _check_K(K)
    R = aR if R is None else _check_R(R)
    t = at if t is None else _real_array(t, "t").reshape(-1)
    if t.size != 3:
        raise ValueError("t must have 3 elements, got %d" % t.size)
    return K, R, t.astype(np.float64)


# --------------------------------------------------------------------------- #
# 光線生成と交差(Möller-Trumbore)                                            #
# --------------------------------------------------------------------------- #
def _rays_from_pixels(uv: np.ndarray, K: np.ndarray, R: np.ndarray, t: np.ndarray):
    """画素 (N,2) → ``(origin (3,), dir_world (N,3), inv_cos_alpha (N,))``。

    方向は **正規化しない**: ``Kinv @ [u, v, 1]`` の第 3 成分が 1 なので、交差の
    光線パラメータ ``t`` がそのまま**カメラ座標の Z(= depth)**になる。
    ``inv_cos_alpha`` = ``|d_cam|`` = 1/cosα(光軸からの傾き)で、面積要素に要る。"""
    Kinv = np.linalg.inv(K)
    hom = np.concatenate([uv, np.ones((uv.shape[0], 1))], axis=1)
    d_cam = hom @ Kinv.T                     # (N,3), 第 3 成分は 1(K の最終行が [0,0,1])
    d_cam = d_cam / d_cam[:, 2:3]            # 数値誤差で 1 からずれた分を正規化
    d_world = d_cam @ R                      # R^T @ d_cam を行ベクトルで書いたもの
    origin = -R.T @ t                        # カメラ中心(世界座標)
    inv_cos_alpha = np.linalg.norm(d_cam, axis=1)
    return origin, d_world, inv_cos_alpha


def _check_budget(n_rays: int, n_faces: int) -> None:
    """光線 × 面の総当たり回数を**float64 昇格の前**に上限で切る。

    形だけから float で計算するので、ここに来る時点では (N, M) の中間配列は
    まだ 1 つも確保されていない。"""
    tests = float(n_rays) * float(n_faces)
    if tests > float(MAX_RAY_FACE_TESTS):
        raise ValueError(
            "%d rays x %d faces = %.3g ray-triangle tests exceeds the "
            "%d cap (cadmap.MAX_RAY_FACE_TESTS); reduce the pixel count or "
            "decimate the mesh (mesh_decimate.decimate_qem)"
            % (n_rays, n_faces, tests, MAX_RAY_FACE_TESTS))


def _intersect(origin: np.ndarray, dirs: np.ndarray, A: np.ndarray,
               e1: np.ndarray, e2: np.ndarray, cull: bool, t_eps: float):
    """Möller-Trumbore(1997)を光線 × 面で総当たりし、**最も手前の当たり**を返す。

    → ``(face_id (N,) int64, tpar (N,), bary (N,3))``。当たりが無い光線は
    ``face_id = -1`` / ``tpar = inf`` / ``bary = NaN``。最寄りの面へ丸めることは
    しない。同じ ``t`` に複数の面が当たる(共有辺・共有頂点)場合は
    ``np.argmin`` の規約どおり**面インデックスが小さいほう**を決定論的に返す。"""
    n_rays = dirs.shape[0]
    n_faces = A.shape[0]
    face_id = np.full(n_rays, -1, np.int64)
    tbest = np.full(n_rays, np.inf, np.float64)
    bary = np.full((n_rays, 3), np.nan, np.float64)
    if n_rays == 0 or n_faces == 0:
        return face_id, tbest, bary

    tvec = origin[None, :] - A                                # (M,3) 光線に依らない
    qvec = np.cross(tvec, e1)                                 # (M,3) 同上
    tnum = np.einsum("mk,mk->m", e2, qvec)[None, :]           # 同上
    # det のしきい値は |e1||e2||d| に比例させる(絶対値で持つと単位依存になる)
    face_scale = (np.linalg.norm(e1, axis=1) * np.linalg.norm(e2, axis=1))[None, :]
    step = max(1, int(RAY_CHUNK_TESTS // max(n_faces, 1)))
    for s in range(0, n_rays, step):
        d = dirs[s:s + step]                                  # (n,3)
        pvec = np.cross(d[:, None, :], e2[None, :, :])        # (n,M,3)
        det = np.einsum("mk,nmk->nm", e1, pvec)               # (n,M)
        eps = _DET_EPS_REL * face_scale * np.linalg.norm(d, axis=1)[:, None]
        if cull:
            # det > 0  <=>  d . ((B-A)x(C-A)) < 0  <=>  外向き法線がカメラを向く
            ok = det > eps
        else:
            ok = np.abs(det) > eps
        inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
        u = np.einsum("mk,nmk->nm", tvec, pvec) * inv
        ok &= (u >= -_BARY_EPS) & (u <= 1.0 + _BARY_EPS)
        v = np.einsum("nk,mk->nm", d, qvec) * inv
        ok &= (v >= -_BARY_EPS) & (u + v <= 1.0 + _BARY_EPS)
        tt = tnum * inv
        ok &= tt > t_eps
        tt = np.where(ok, tt, np.inf)
        idx = np.argmin(tt, axis=1)                           # 同点は最小 face index
        rows = np.arange(tt.shape[0])
        tmin = tt[rows, idx]
        hit = np.isfinite(tmin)
        gid = s + rows
        face_id[gid[hit]] = idx[hit]
        tbest[gid[hit]] = tmin[hit]
        uu = u[rows, idx][hit]
        vv = v[rows, idx][hit]
        bary[gid[hit]] = np.stack([1.0 - uu - vv, uu, vv], axis=1)
    return face_id, tbest, bary


def _t_eps(V: np.ndarray) -> float:
    """光線パラメータの下限(mesh のスケールに比例)。単位非依存にするため。"""
    diag = float(np.linalg.norm(V.max(axis=0) - V.min(axis=0))) if V.size else 1.0
    return _T_EPS_REL * max(diag, 1e-300)


def _face_geometry(V: np.ndarray, F: np.ndarray):
    """``(A, e1, e2, unit_normal)`` — 面ごとの交差用の前計算。"""
    A = V[F[:, 0]]
    e1 = V[F[:, 1]] - A
    e2 = V[F[:, 2]] - A
    n = np.cross(e1, e2)
    ln = np.linalg.norm(n, axis=1, keepdims=True)
    unit = np.divide(n, ln, out=np.zeros_like(n), where=ln > 0.0)
    return A, e1, e2, unit


#: ``image_size`` を画素から推定するときの上限(既定カメラの正気度のため)。
#: これは割り当てではなく ``cx``/``cy`` と画角を決める数なので、上限を超えたら
#: 例外ではなく頭打ちにする — 「画枠の外を指す画素」は正当な問い合わせで、
#: 答えは miss だから。
_MAX_IMPLIED_SIZE = 1 << 16


def _implied_size(uv: np.ndarray):
    """画素の外接箱から画像サイズを推定する(既定カメラを合わせるためだけ)。"""
    if uv.shape[0] == 0:
        return DEFAULT_IMAGE_SIZE
    w = int(np.ceil(max(float(uv[:, 0].max()), 0.0))) + 1
    h = int(np.ceil(max(float(uv[:, 1].max()), 0.0))) + 1
    return (min(max(w, 2), _MAX_IMPLIED_SIZE), min(max(h, 2), _MAX_IMPLIED_SIZE))


def _cam_dict(K, R, t, width, height):
    return {"K": K, "R": R, "t": t, "width": int(width), "height": int(height)}


# --------------------------------------------------------------------------- #
# op 1 — 画素 → 面上の点                                                       #
# --------------------------------------------------------------------------- #
def cad_pixel_to_surface(mesh, pixels, K=None, R=None, t=None,
                         cull_backfaces=True, image_size=None, strict=False):
    """画素 (N,2) → CAD 面上の ``(face_id, 重心座標, 3-D 点)``(閉形式)。

    画素ごとに視線を作り(``camera.py`` 規約: 中心は整数座標、``u`` = 列、
    ``v`` = 行)、Möller-Trumbore で全三角形と交差させ、**最も手前の当たり**を
    採る。当たらない画素には ``face_id = -1`` を返し、**最寄りの面へは絶対に
    丸めない**(検査で「欠陥が背景に載っていた」を「面 17 の欠陥」に化けさせない
    ため)。``cull_backfaces=True``(既定)では法線がカメラを向いていない面は
    当たりにしない。

    返りは dict:

      * ``face_id``  (N,) int64 — 当たった三角形の行番号。miss は ``-1``。
      * ``bary``     (N,3) — 重心座標 ``(w0, w1, w2)``、``F[face_id]`` の 3 頂点の
        順。``point = w0*V[i0] + w1*V[i1] + w2*V[i2]`` が厳密に成り立つ。
        miss は ``NaN``。辺・頂点上では 1 成分が ``0``(許容 ``1e-9``)。
      * ``point``    (N,3) — 世界座標の交点。miss は ``NaN``。
      * ``depth``    (N,) — カメラ座標の Z(視線距離ではない)。miss は ``NaN``。
      * ``normal``   (N,3) — 当たった面の単位法線(世界座標、巻き方どおり)。
        miss は ``NaN``(``bary``/``point``/``depth`` と同じ規約)。
      * ``hit``      (N,) bool。
      * ``camera``   実際に使われた ``K``/``R``/``t``/``width``/``height``。
        既定に落ちた場合もここを見れば分かる。
      * ``winding_fixed`` bool — 内向きに巻かれた閉メッシュを検出して**この
        呼び出しの中で巻きを直した**かどうか。常に入る(``False`` でも入る)。

    ``cull_backfaces=True``(既定)で mesh が閉じていて符号つき体積が負なら、
    既定では巻きを直して ``winding_fixed=True`` を返す。``strict=True`` にすると
    直さず ``ValueError`` で拒否する。``cull_backfaces=False`` のときは裏面判定を
    しないので巻き方向は結果に効かず、検査もせず ``winding_fixed`` は常に
    ``False``(``normal`` は入力の巻きどおりの符号で返る)。詳細は
    :func:`_orient_for_culling`。

    ``K``/``R``/``t`` を省くと mesh を画像に収める既定カメラを作る
    (``R = I``、カメラは重心の -Z 側)。``image_size`` を省くと**与えた画素の
    外接箱**から画像サイズを決める — 既定カメラが画素のある場所を見るように
    するためで、``K`` を明示したときは ``in_image`` 判定にしか効かない。"""
    V, F = _mesh(mesh)
    uv = _real_array(pixels, "pixels")
    if uv.ndim != 2 or uv.shape[1] != 2:
        raise ValueError("pixels must be (N, 2) [u=column, v=row], got %r"
                         % (uv.shape,))
    _check_budget(uv.shape[0], F.shape[0])      # ★ 大きい中間配列を作る前に
    if image_size is None:
        width, height = _implied_size(uv)
    else:
        if len(image_size) != 2:
            raise ValueError("image_size must be (width, height)")
        width, height = _size(image_size[0], "width"), _size(image_size[1], "height")
    F, winding_fixed = _orient_for_culling(V, F, cull_backfaces, strict,
                                           "cad_pixel_to_surface", reports=True)
    K, R, t = _resolve_camera(V, K, R, t, width, height)

    origin, dirs, _ = _rays_from_pixels(uv, K, R, t)
    A, e1, e2, unit = _face_geometry(V, F)
    face_id, tpar, bary = _intersect(origin, dirs, A, e1, e2, bool(cull_backfaces), _t_eps(V))
    hit = face_id >= 0

    n = uv.shape[0]
    point = np.full((n, 3), np.nan)
    depth = np.full(n, np.nan)
    normal = np.full((n, 3), np.nan)
    if hit.any():
        # 交点は重心座標から直接組む(origin + t*d と数値的に等価だが、重心座標
        # との整合が定義上厳密になる = 往復可逆性の検証が意味を持つ)
        tri = V[F[face_id[hit]]]                       # (m,3,3)
        point[hit] = np.einsum("mkj,mk->mj", tri, bary[hit])
        depth[hit] = tpar[hit]
        normal[hit] = unit[face_id[hit]]
    return {"face_id": face_id, "bary": bary, "point": point, "depth": depth,
            "normal": normal, "hit": hit,
            "camera": _cam_dict(K, R, t, width, height),
            "winding_fixed": bool(winding_fixed)}


# --------------------------------------------------------------------------- #
# op 2 — 面上の点 → 画素(遮蔽を隠さない順方向)                                #
# --------------------------------------------------------------------------- #
def cad_surface_to_pixel(mesh, points, K=None, R=None, t=None, image_size=None,
                         cull_backfaces=True, depth_tol=1e-6, strict=False):
    """3-D 点 (N,3) → 画素 + **可視性**(遮蔽・背面・画枠外を区別して返す)。

    ``camera.project_points`` で投影したうえで、**同じ画素へ光線を撃ち直して**
    手前に別の面が無いかを確かめる。これをやらないと、隠れている点の画素座標を
    「そこに見えている」かのように返してしまう。返りは dict:

      * ``uv``            (N,2) — 画素 ``(u=列, v=行)``。``depth <= 0`` の点でも
        投影値は返るが ``in_front = False`` が立つ。
      * ``depth``         (N,) — カメラ座標 Z。
      * ``in_front``      (N,) bool — ``depth > 0``。
      * ``in_image``      (N,) bool — 画枠内(``0 <= u <= width-1`` かつ
        ``0 <= v <= height-1``)。
      * ``occluded``      (N,) bool — 同じ視線上で、その点より手前に面がある。
      * ``occluder_face`` (N,) int64 — 遮っている面。無ければ ``-1``。
      * ``visible``       (N,) bool — ``in_front & in_image & ~occluded``。
      * ``camera``        実際に使われたカメラ。
      * ``winding_fixed`` bool — 内向きに巻かれた閉メッシュを検出して直したか。

    ``depth_tol`` は「自分自身の面に遮られた」と誤判定しないための相対許容で、
    遮蔽と判定するのは ``z_hit < depth * (1 - depth_tol) - depth_tol`` のとき。
    閉じた mesh の**裏側**にある点は、手前の壁に遮られて ``occluded = True`` に
    なる — これは仕様であって取りこぼしではない。

    **遮蔽判定は巻き方向に依存する**(手前の壁が裏面としてカリングされると、
    裏側の点まで ``visible`` になる)。そのため ``cull_backfaces=True`` では
    内向きに巻かれた閉メッシュを検出し、既定では巻きを直して
    ``winding_fixed=True`` を返す。``strict=True`` で ``ValueError``、
    ``cull_backfaces=False`` では検査そのものをしない
    (詳細は :func:`_orient_for_culling`)。"""
    V, F = _mesh(mesh)
    P = _real_array(points, "points")
    if P.ndim != 2 or P.shape[1] != 3:
        raise ValueError("points must be (N, 3), got %r" % (P.shape,))
    _check_budget(P.shape[0], F.shape[0])
    if image_size is None:
        width, height = DEFAULT_IMAGE_SIZE
    else:
        if len(image_size) != 2:
            raise ValueError("image_size must be (width, height)")
        width, height = _size(image_size[0], "width"), _size(image_size[1], "height")
    tol = _num(depth_tol, "depth_tol")
    if tol < 0.0:
        raise ValueError("depth_tol must be >= 0")
    F, winding_fixed = _orient_for_culling(V, F, cull_backfaces, strict,
                                           "cad_surface_to_pixel", reports=True)
    K, R, t = _resolve_camera(V, K, R, t, width, height)

    uv, depth = camera.project_points(P, K, R, t)
    in_front = depth > 0.0
    in_image = ((uv[:, 0] >= 0.0) & (uv[:, 0] <= width - 1.0)
                & (uv[:, 1] >= 0.0) & (uv[:, 1] <= height - 1.0))

    origin, dirs, _ = _rays_from_pixels(uv, K, R, t)
    A, e1, e2, _ = _face_geometry(V, F)
    face_id, tpar, _ = _intersect(origin, dirs, A, e1, e2, bool(cull_backfaces), _t_eps(V))
    blocked = (face_id >= 0) & (tpar < depth * (1.0 - tol) - tol)
    occluder = np.where(blocked, face_id, -1).astype(np.int64)
    visible = in_front & in_image & ~blocked
    return {"uv": uv, "depth": depth, "in_front": in_front, "in_image": in_image,
            "occluded": blocked, "occluder_face": occluder, "visible": visible,
            "camera": _cam_dict(K, R, t, width, height),
            "winding_fixed": bool(winding_fixed)}


# --------------------------------------------------------------------------- #
# op 3 — 2-D 欠陥領域 → CAD 上の表                                             #
# --------------------------------------------------------------------------- #
def cad_defect_to_cad(mesh, labels, K=None, R=None, t=None, cull_backfaces=True,
                      min_pixels=1, background=0):
    """2-D の欠陥ラベル画像 → **CAD 面上の表**(面 ID / 面上の面積 / 3-D 重心)。

    ``labels`` は (H, W) の整数ラベル画像(``background`` は無視、bool マスクも
    可)。ラベルごとに全画素の視線を撃ち、当たった面と、その画素が**面の上で
    占める実面積**を積む。面積は画素数ではなく

        dA = Z^2 * cosα / (fx * fy * |cosθ|)

    で、``cosα`` は光軸からの傾き、``cosθ`` は視線と面法線のなす角。**斜めから
    見た面ほど 1 画素が広い面積を覆う**という透視投影のヤコビアンそのもので、
    ここを ``Z^2/(fx*fy)`` のままにすると傾いた面の欠陥が小さく出る(60 度で
    ちょうど半分になる)。

    返りはラベルごとの dict の list(``table`` sort):

      * ``label``        ラベル値。
      * ``n_pixels``     そのラベルの画素数。
      * ``n_hit``        CAD に当たった画素数。``hit_fraction`` = その比。
      * ``area``         面上の実面積(mesh の長さ単位の 2 乗)。当たった画素分
        だけの和で、当たらなかった画素は**足さない**。
      * ``area_naive``   ``Z^2/(fx*fy)`` だけの和(= 傾きを無視した値)。両方
        返すのは、傾き補正が効いているかを利用者が自分で確かめられるようにする
        ため。
      * ``face_ids``     当たった面の昇順一意リスト(int64 配列)。
      * ``face_areas``   ``face_ids`` と同じ並びの面ごとの面積。
      * ``centroid``     面積重みの 3-D 重心(世界座標)。当たり 0 なら ``NaN``。
      * ``depth_mean``   当たった画素の平均 Z。当たり 0 なら ``NaN``。

    ``min_pixels`` 未満の領域は落とす。当たり 0 の領域は**消さずに** ``area =
    0.0``, ``hit_fraction = 0.0`` で残す — 消すと「CAD の外にあった欠陥」が
    表から静かに消えるため。"""
    V, F = _mesh(mesh)
    lab = _int_array(labels, "labels", allow_bool=True)
    if lab.ndim != 2:
        raise ValueError("labels must be a 2-D (H, W) label image, got %r"
                         % (lab.shape,))
    H, W = lab.shape
    if H < 1 or W < 1:
        raise ValueError("labels must be non-empty")
    bg = int(_num(background, "background"))
    minpx = _size(min_pixels, "min_pixels")
    if not isinstance(cull_backfaces, (bool, np.bool_)):
        raise ValueError("cull_backfaces must be a bool")

    fg = lab != bg
    _check_budget(int(fg.sum()), F.shape[0])     # ★ float64 昇格の前に
    K, R, t = _resolve_camera(V, K, R, t, W, H)
    fx, fy = float(K[0, 0]), float(K[1, 1])

    rows, cols = np.nonzero(fg)
    uv = np.stack([cols.astype(np.float64), rows.astype(np.float64)], axis=1)
    origin, dirs, inv_cos_alpha = _rays_from_pixels(uv, K, R, t)
    A, e1, e2, unit = _face_geometry(V, F)
    face_id, tpar, bary = _intersect(origin, dirs, A, e1, e2, bool(cull_backfaces), _t_eps(V))
    hit = face_id >= 0

    # 面積要素(当たった画素のみ)
    area_px = np.zeros(uv.shape[0])
    area_naive = np.zeros(uv.shape[0])
    pts = np.full((uv.shape[0], 3), np.nan)
    if hit.any():
        Z = tpar[hit]
        cos_alpha = 1.0 / inv_cos_alpha[hit]
        rhat = dirs[hit] / np.linalg.norm(dirs[hit], axis=1, keepdims=True)
        cos_theta = np.abs(np.einsum("nk,nk->n", rhat, unit[face_id[hit]]))
        base = Z * Z / (fx * fy)
        area_naive[hit] = base
        # cosθ = 0 は視線が面と平行 = 交差しないので、当たった画素では起きない。
        # それでも 0 除算で inf を吐くより、明示的に無効化するほうが安全。
        good = cos_theta > 1e-12
        idx = np.nonzero(hit)[0][good]
        area_px[idx] = (base * cos_alpha / cos_theta)[good]
        tri = V[F[face_id[hit]]]
        pts[hit] = np.einsum("mkj,mk->mj", tri, bary[hit])

    # ラベルごとの画素をまとめる。**ラベル値ごとに全画素を舐め直さない** ―
    # ``for val in unique: sel = flat == val`` と書くと O(ラベル数 x 画素数) で、
    # 実測で 256x256 の「1 画素 1 ラベル」画像(= 65536 ラベル、たった 256 KB の
    # 入力)が 24.97 秒かかった。1 度の argsort で線形にする。
    flat = lab[rows, cols]
    order = np.argsort(flat, kind="stable")
    values, starts = np.unique(flat[order], return_index=True)
    ends = np.append(starts[1:], flat.size)

    out = []
    for val, s0, s1 in zip(values, starts, ends):
        idx = order[s0:s1]                       # そのラベルの画素の**添字**
        npx = int(idx.size)
        if npx < minpx:
            continue
        h = idx[hit[idx]]                        # 当たった画素だけの添字
        nh = int(h.size)
        rec = {"label": int(val), "n_pixels": npx, "n_hit": nh,
               "hit_fraction": float(nh) / float(npx),
               "area": float(area_px[h].sum()),
               "area_naive": float(area_naive[h].sum())}
        if nh:
            fids, inv = np.unique(face_id[h], return_inverse=True)
            fareas = np.bincount(inv, weights=area_px[h], minlength=fids.size)
            wsum = float(area_px[h].sum())
            wts = area_px[h] if wsum > 0.0 else np.ones(nh)
            rec["face_ids"] = fids.astype(np.int64)
            rec["face_areas"] = fareas.astype(np.float64)
            rec["centroid"] = (pts[h] * wts[:, None]).sum(0) / wts.sum()
            rec["depth_mean"] = float(tpar[h].mean())
        else:
            rec["face_ids"] = np.zeros(0, np.int64)
            rec["face_areas"] = np.zeros(0, np.float64)
            rec["centroid"] = np.full(3, np.nan)
            rec["depth_mean"] = float("nan")
        rec["camera"] = _cam_dict(K, R, t, W, H)
        out.append(rec)
    return out


# --------------------------------------------------------------------------- #
# op 4 — 実際に見えている面(検査カバレッジ)                                   #
# --------------------------------------------------------------------------- #
def cad_visible_faces(mesh, K=None, R=None, t=None, width=64, height=64,
                      cull_backfaces=True):
    """このカメラから**実際に見えている**面の ID(昇順、``indices`` sort)。

    画像格子(``width`` x ``height``、画素中心は整数座標)へ光線を撃ち、最も
    手前に来た面を集める。裏面(法線がカメラを向いていない)と、手前の面に
    完全に隠れた面は入らない。検査カバレッジ — 「この視点で CAD のどの面を
    見たことになるか」— をそのまま返す量で、``mesh_area`` と組み合わせれば
    「未検査の面積」が出る。

    格子の分解能より小さく写る面は取りこぼす(標本化なので当然)。**取りこぼし
    を「隠れている」と言い換えない**ために、返るのは「見えた面」であって
    「見えない面の補集合」ではない。"""
    V, F = _mesh(mesh)
    w = _size(width, "width")
    h = _size(height, "height")
    if float(w) * float(h) > float(render3d.MAX_PIXELS):
        raise ValueError("%dx%d = %.3g pixels exceeds render3d.MAX_PIXELS (%d)"
                         % (w, h, float(w) * float(h), render3d.MAX_PIXELS))
    _check_budget(w * h, F.shape[0])            # ★ float64 昇格の前に
    K, R, t = _resolve_camera(V, K, R, t, w, h)
    vv, uu = np.mgrid[0:h, 0:w]                 # camera.depth_to_points と同じ規約
    uv = np.stack([uu.ravel().astype(np.float64), vv.ravel().astype(np.float64)], 1)
    origin, dirs, _ = _rays_from_pixels(uv, K, R, t)
    A, e1, e2, _ = _face_geometry(V, F)
    face_id, _, _ = _intersect(origin, dirs, A, e1, e2, bool(cull_backfaces), _t_eps(V))
    seen = face_id[face_id >= 0]
    return np.unique(seen).astype(np.int64)
