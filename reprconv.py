# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""reprconv — 表現どうしを繋ぐ変換 op(袋小路の型に、正直な出口を作る)。

## なぜこのモジュールがあるか

この repo で直近に見つかった実バグは**全部が変換 op** だった —— ``voxel_to_mesh``
が宣言 ``mesh`` に対し 3-tuple を返していた / ``render_beauty`` が宣言
``image2d`` に対し RGB を返していた(**一度も実行されていなかったので誰も
気づけなかった**)/ ``project_points`` が宣言 ``image2d`` に対しタプルを返して
いた / ``alpha_shape_boundary`` が宣言 ``points`` に対し添字を返していた。

理由は単純で、**変換は「入口の型」と「出口の型」の両方を主張するので、嘘を
つく面が 2 つある**。だから変換を増やすことは、機能を増やすことであると同時に
**検査面を増やすこと**でもある。

## 何を埋めたか(実測した穴)

``tools/chain_fuzz.py`` の台帳 515 op を「単入力かつ in 型 ≠ out 型 = 変換」で
機械集計すると、**他型へ一歩も出られない型**が並んでいた(2026-09-02 実測):

    型            他型へ出る  他型から来る
    pairs              0           5
    indices            0           3
    curvature          0           3
    descriptor         0           3
    keypoints          0           2
    normals            0           2
    position           0           2
    flow               0           0     ← 単入力の産む op も食う op も無い
    gaussians          0           0     ← 産む op が 1 つも無い
    score              0           0     ← 産む op が 1 つも無い
    cscalar / countrate / angle / shift / rot_scale / deformation   0   0-1

産む op はあるのに食う op が無い型 = **死んだ語彙**。進化探索でも連鎖ファザー
でも、そこから先へ一歩も進めない。本モジュールはその出口を作る。

## 中心的な規律 —— 往復(round-trip)

**変換の嘘は往復で露見する。** よって全 op を次の 3 群に分けて宣言し、
``tests/test_reprconv.py`` が機械検証する:

* **可逆(exact)** —— 往復して ε 以下。誤差は数字で出す。
  ``normals_to_angles`` ⇄ ``angles_to_normals`` /
  ``curvature_to_shape_index`` ⇄ ``shape_index_to_curvature`` /
  ``descriptor_to_matrix`` ⇄ ``matrix_to_descriptor`` /
  ``keypoints_uv_to_points`` ⇄ ``points_zyx_to_keypoints_uv``(z を渡す向き)/
  ``indices_to_labels`` ⇄ ``labels_to_indices`` /
  ``angle_to_matrix`` ⇄ ``matrix_to_angle`` /
  ``rot_scale_to_matrix`` ⇄ ``matrix_to_rot_scale`` /
  ``shift_to_vector`` ⇄ ``vector_to_shift`` /
  ``cscalar_to_polar`` ⇄ ``polar_to_cscalar`` /
  ``countrate_to_counts`` ⇄ ``counts_to_countrate`` /
  ``points_to_gaussians`` → ``gaussians_to_points``(中心は bit 一致)。
* **不可逆(quantified)** —— 「戻らない」で終わらせず**何がどれだけ落ちるか**を
  測る。``keypoints_to_image2d`` → ``keypoints_from_image2d``(画素格子への
  量子化 RMS)/ ``points_to_position``(重心 = 分散を捨てる)/
  ``normals_to_egi``(方向の binning)/ ``gaussians_to_voxel``(質量保存率)。
* **一方向(片道が定義されない)** —— ``curvature_to_table`` /
  ``descriptor_to_table`` / ``pairs_to_table`` / ``flow_magnitude`` /
  ``score_to_image2d``。統計や射影は情報を捨てるのが仕事なので逆を作らない
  (作れば「戻せるふり」という別種の嘘になる)。

## 軸と単位 —— ここが一番嘘をつく

この repo には**同じ型名のもとに 2 つの座標系が同居している**(実測):

* ``points`` は ``fuse3d.to_points(voxel)`` が **(z, y, x)** で返す
  (``volregion.vol_rle_centroid`` の ``position`` も (z, y, x))。
* ``keypoints`` は ``match3d.project_points`` が **(u, v) = (col, row)** で
  返す(カメラの画像座標。列が先)。

つまり ``keypoints`` を素直に ``points`` の先頭 2 列だと思って繋ぐと、
**例外も NaN も出ないまま行と列が入れ替わる**。そこで本モジュールは軸の約束を
**op 名に書く**: ``keypoints_uv_to_points`` / ``points_zyx_to_keypoints_uv``。
名前で殴っておかないと、6 か月後の自分が必ず間違える。

角度は**すべて度**(``normals_to_angles`` / ``angle_to_matrix`` /
``matrix_to_rot_scale``)。ラジアンを返す op は本モジュールに 1 つも無い。
``countrate_to_counts`` は **[Hz] × [s] = [counts]** で、gate 時間を
明示引数にしてある(既定 1 ms)。

## 依存

numpy + scipy(``scipy.ndimage`` / ``scipy.spatial``)まで。torch は使わない。

## 使い方

    import reprconv
    az_el = reprconv.normals_to_angles(n)          # (N,3) -> (N,2) 度
    n2 = reprconv.angles_to_normals(az_el)          # 往復 max|Δ| ~ 1e-16
    reprconv.selftest()                             # 往復誤差表を印字
"""
from __future__ import annotations

import numpy as np


def _fssystem():
    """``fssystem`` を遅延解決する(import 時の循環と起動コストを避ける)。"""
    import fssystem
    return fssystem

__all__ = [
    # 方向(normals / pairs)
    "normals_to_angles", "angles_to_normals", "normals_to_egi",
    # 曲率(curvature)
    "curvature_to_shape_index", "shape_index_to_curvature", "curvature_to_table",
    # 記述子(descriptor)
    "descriptor_to_matrix", "matrix_to_descriptor", "descriptor_to_table",
    # キーポイント / 位置
    "keypoints_uv_to_points", "points_zyx_to_keypoints_uv",
    "keypoints_to_image2d", "keypoints_from_image2d",
    "position_to_points", "points_to_position",
    # 添字 / ラベル
    "indices_to_labels", "labels_to_indices", "select_points",
    # 対(pairs)
    "pairs_to_signal", "pairs_to_image2d", "pairs_to_table",
    # フロー
    "flow_magnitude", "flow_to_rgbimage", "flow_speed", "flow_apply",
    # ガウシアン
    "points_to_gaussians", "gaussians_to_points", "gaussians_to_voxel",
    # スコア volume
    "correlation_score", "score_to_position", "score_to_image2d",
    # 小さな代数(軸・単位の規律を検査する面)
    "angle_to_matrix", "matrix_to_angle",
    "rot_scale_to_matrix", "matrix_to_rot_scale",
    "shift_to_vector", "vector_to_shift",
    "cscalar_to_polar", "polar_to_cscalar",
    "countrate_to_counts", "counts_to_countrate",
    "deformation_to_points",
    # 型のつながりを閉じる変換(2026-11-03)
    "gradient_magnitude",
    "gradient_coherence",
    "hessian_determinant",
    "hessian_vesselness",
    "frame_axis",
    "knn_graph_to_conn_graph",
    "pointmap_to_points",
    "match_component",
    "indices_to_positions",
    "synapse_table_from_table",
    "jones_state",
    "tokens_to_matrix",
    "table_field_image2d",
    "table_field_signal",
    "table_field_matrix",
    "table_field_measurement",
    "pairs_peak_x",
    "keypoints_rowcol_to_uv",
    "keypoints_uv_to_rowcol",
    "pose_to_matrix",
    "selftest",
]

#: 1 つの産物として許す最大要素数。**小さい入力から内部割当だけ巨大になる**
#: 形を止めるための上限で、``keypoints_to_image2d(kp, shape=(40000, 40000))`` の
#: ように引数だけで 12 GB を要求できてしまう op が実際にある。
MAX_ELEMENTS = 64_000_000


# --------------------------------------------------------------------------- #
# fail-closed の共通部品                                                        #
# --------------------------------------------------------------------------- #
def _arr(value, what, *, dtype=float):
    """ndarray へ寄せ、**非有限を黙って通さない**。

    非有限を通すと下流で NaN が「暗い画素」や「小さい誤差」に化けて、誰も
    気づけない形で結果を汚す。入口で止めるのが唯一の実効策。
    """
    # ★ 整数 dtype への変換は **キャストの前に** 生の値を検査する。
    # 敵対的検査で見つけた穴(2026-09-02): ``np.asarray(nan, dtype=int64)`` は
    # 例外を出さず INT_MIN を返し、キャスト後は ``dtype.kind == 'i'`` なので
    # 下の非有限検査を素通りする。3.7 のような非整数も黙って 3 に切り詰まる ——
    # **添字が 1 ずれた結果が、例外もなく返る**。まさに変換 op の嘘そのもの。
    if np.dtype(dtype).kind in "iu":
        raw = np.asarray(value)
        if raw.dtype.kind in "fc":
            if raw.size and not np.all(np.isfinite(raw)):
                n_bad = int(np.count_nonzero(~np.isfinite(raw)))
                raise ValueError(f"{what}: contains {n_bad} non-finite value(s) (NaN/Inf) "
                                 f"— casting these to an integer index would silently "
                                 f"produce INT_MIN, not an error")
            if raw.size and not np.all(raw == np.rint(raw)):
                bad = float(raw[raw != np.rint(raw)].ravel()[0])
                raise ValueError(f"{what}: must hold whole numbers to be used as indices; "
                                 f"got {bad} (casting would silently truncate)")
    try:
        a = np.asarray(value, dtype=dtype)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{what}: cannot be read as a numeric array ({exc})") from exc
    if a.size == 0:
        raise ValueError(f"{what}: empty array is not a valid representation")
    if a.dtype.kind in "fc" and not np.all(np.isfinite(a)):
        n_bad = int(np.count_nonzero(~np.isfinite(a)))
        raise ValueError(f"{what}: contains {n_bad} non-finite value(s) (NaN/Inf)")
    return a


def _n3(value, what):
    """(N, 3) の実配列を要求する。"""
    a = _arr(value, what)
    if a.ndim != 2 or a.shape[1] != 3:
        raise ValueError(f"{what}: must be (N, 3); got {a.shape}")
    return a


def _n2(value, what):
    """(N, 2) の実配列を要求する。``pairs`` の正典形。

    ``pairs`` は台帳上 16 op が産むが、実測では **(n,2) 配列** と
    **2 本の 1-D 配列のタプル** が混在していた(``spectrum`` /
    ``stat_histogram`` / ``curvature_torsion``)。しかも
    ``TYPE_CHECKS["pairs"]`` は ``lambda v: True`` なので**何も検査していない**。
    ここでは 2-tuple を (n,2) へ束ねる橋渡しだけ行い、長さが違えば拒否する
    (``stat_histogram`` の (10,) と (11,) は「対」ではないので通さない)。
    """
    if isinstance(value, tuple) and len(value) == 2 and not isinstance(value[0], (int, float)):
        a0 = _arr(value[0], f"{what}[0]")
        a1 = _arr(value[1], f"{what}[1]")
        if a0.shape != a1.shape or a0.ndim != 1:
            raise ValueError(
                f"{what}: 2-tuple must hold two 1-D arrays of equal length; "
                f"got {a0.shape} and {a1.shape}")
        return np.stack([a0, a1], axis=1)
    a = _arr(value, what)
    if a.ndim != 2 or a.shape[1] != 2:
        raise ValueError(f"{what}: must be (N, 2) or a 2-tuple of equal-length 1-D arrays; "
                         f"got {a.shape}")
    return a


def _shape2(shape, what):
    """(H, W) を検証し、要素数の上限も見る。"""
    try:
        h, w = (int(shape[0]), int(shape[1]))
    except (TypeError, ValueError, IndexError) as exc:
        raise ValueError(f"{what}: shape must be a 2-sequence (H, W); got {shape!r}") from exc
    if h < 1 or w < 1:
        raise ValueError(f"{what}: shape must be positive; got ({h}, {w})")
    if h * w > MAX_ELEMENTS:
        raise ValueError(f"{what}: shape ({h}, {w}) = {h * w} elements exceeds "
                         f"MAX_ELEMENTS={MAX_ELEMENTS}")
    return h, w


def _shape3(shape, what):
    """(D, H, W) を検証し、要素数の上限も見る。"""
    try:
        d, h, w = (int(shape[0]), int(shape[1]), int(shape[2]))
    except (TypeError, ValueError, IndexError) as exc:
        raise ValueError(f"{what}: shape must be a 3-sequence (D, H, W); got {shape!r}") from exc
    if d < 1 or h < 1 or w < 1:
        raise ValueError(f"{what}: shape must be positive; got ({d}, {h}, {w})")
    if d * h * w > MAX_ELEMENTS:
        raise ValueError(f"{what}: shape ({d}, {h}, {w}) = {d * h * w} elements exceeds "
                         f"MAX_ELEMENTS={MAX_ELEMENTS}")
    return d, h, w


# --------------------------------------------------------------------------- #
# normals / pairs —— 方向の極座標エンコード(可逆)                              #
# --------------------------------------------------------------------------- #
def normals_to_angles(normals):
    """法線 ``(N,3)`` → 方位・仰角の対 ``(N,2)`` **[度]**。``normals`` の出口。

    ``az = atan2(c1, c0)`` を軸0-軸1 平面内の方位、``el = asin(c2/|v|)`` を
    軸2 からの仰角とする。**x/y/z でなく「軸0/1/2」で定義する**のは、この repo に
    (z,y,x) 順の点群と (x,y,z) 順の点群が両方いるため —— 名前で書くと、渡された
    配列がどちらの流儀かに依存して意味が変わってしまう。

    可逆: :func:`angles_to_normals` と往復して **方向は厳密に戻る**(実測
    max|Δ| = 6.1e-16、``selftest`` が毎回測る)。**戻らないのは長さだけ** ——
    法線は向きなので、非単位ベクトルを渡すと往復で単位ベクトルになる。

    Args:
        normals: (N, 3) 実配列。零ベクトルは拒否(方位が定義できない)。
    Returns:
        (N, 2) float64。列 0 = 方位 (-180, 180]、列 1 = 仰角 [-90, 90]。
    Raises:
        ValueError: 形状が (N,3) でない / 非有限 / 長さ 0 のベクトルを含む。
    """
    v = _n3(normals, "normals")
    r = np.linalg.norm(v, axis=1)
    if np.any(r <= 0.0):
        n_zero = int(np.count_nonzero(r <= 0.0))
        raise ValueError(f"normals: {n_zero} zero-length vector(s) have no direction")
    az = np.degrees(np.arctan2(v[:, 1], v[:, 0]))
    el = np.degrees(np.arcsin(np.clip(v[:, 2] / r, -1.0, 1.0)))
    return np.stack([az, el], axis=1)


def angles_to_normals(pairs):
    """方位・仰角の対 ``(N,2)`` **[度]** → 単位法線 ``(N,3)``。``pairs`` の出口。

    :func:`normals_to_angles` の厳密な逆(単位長に正規化した意味で)。
    仰角は [-90, 90] の外を拒否する —— 100 度の仰角は「反対側の 80 度」に
    折り返して**もっともらしく間違う**ので、黙って受けない。

    Args:
        pairs: (N, 2) [方位度, 仰角度]、または 2 本の等長 1-D のタプル。
    Returns:
        (N, 3) float64、行ごとに単位長。
    Raises:
        ValueError: 形状不正 / 非有限 / 仰角が [-90, 90] 外。
    """
    p = _n2(pairs, "pairs")
    az = np.radians(p[:, 0])
    el = p[:, 1]
    if np.any(np.abs(el) > 90.0):
        bad = float(np.max(np.abs(el)))
        raise ValueError(f"pairs: elevation must be within [-90, 90] degrees; got |el| max {bad}")
    el = np.radians(el)
    c = np.cos(el)
    return np.stack([c * np.cos(az), c * np.sin(az), np.sin(el)], axis=1)


def normals_to_egi(normals, n_az=36, n_el=18):
    """法線 ``(N,3)`` → 拡張ガウス像 ``(n_el, n_az)`` の ``image2d``。

    方向の 2-D ヒストグラム(Horn, *Extended Gaussian Images*, Proc. IEEE 72(12)
    1984)。「どの向きの面がどれだけあるか」の地図で、平面が支配的な物体では
    1 つの bin に山が立つ。**不可逆** —— bin 幅ぶんの方向解像度を捨てる。
    捨てた量は測れる: 最頻 bin の中心方向と入力の平均方向の角度差が量子化誤差で、
    既定 (36, 18) では bin 幅 10 度に対し実測 3.7 度(``selftest`` が出す)。

    仰角の bin は ``sin(el)`` で等分する(等立体角)。度で等分すると極が過剰に
    細かくなり、「北極に面が集中している」という嘘の山が立つ。

    ★**位置の点群を渡しても例外は出ない**。``backends_typed.TYPE_TO_SORT`` が
    ``normals`` を ``points`` に畳んでいるので、進化器も台帳も両者を区別しない。
    この op は方向しか見ない(長さは捨てる)ので、``(N,3)`` の座標を渡すと
    「原点から各点を見た向き」のヒストグラムが**もっともらしく**返る。実測
    (2026-09-08、200 点の曲線 vs 全部真上の法線): 非零 bin が 1 → 12、
    最大 bin が 200 → 44 に変わるだけで、**総和はどちらも 200**。
    「総和が点数と合うから正しい」では区別がつかない。
    ``fullseye.set_system("extra_checks", "on")`` にすると、単位長から外れた
    ベクトルを**拒否**する(下の Raises)。

    Args:
        normals: (N, 3)。
        n_az: 方位の bin 数(既定 36 = 10 度刻み)。
        n_el: 仰角の bin 数(既定 18)。
    Returns:
        (n_el, n_az) float64 の計数マップ(行 = 仰角、列 = 方位)。
    Raises:
        ValueError: bin 数が 1 未満 / 上限超 / 入力不正。
        ValueError: ``extra_checks='on'`` で、長さが 1 から 1e-6 を超えて外れる
            ベクトルを含むとき(位置の点群を法線として渡した事故を捕まえる)。
    """
    n_el_i, n_az_i = _shape2((n_el, n_az), "egi bins")
    if _fssystem().get_system("extra_checks") == "on":
        v = np.asarray(normals, np.float64)
        if v.ndim == 2 and v.shape[1] == 3 and v.size:
            r = np.linalg.norm(v, axis=1)
            off = np.abs(r - 1.0)
            if off.max() > 1e-6:
                raise ValueError(
                    "normals_to_egi: %d of %d vectors are not unit length "
                    "(max |len-1| = %.4g). A point cloud passed as normals produces a "
                    "plausible histogram with no error, so extra_checks='on' refuses it; "
                    "normalise first, or drop that system setting to opt back in"
                    % (int((off > 1e-6).sum()), len(v), float(off.max())))
    a = normals_to_angles(normals)
    az_i = np.clip(((a[:, 0] + 180.0) / 360.0 * n_az_i).astype(np.int64), 0, n_az_i - 1)
    el_i = np.clip(((np.sin(np.radians(a[:, 1])) + 1.0) / 2.0 * n_el_i).astype(np.int64),
                   0, n_el_i - 1)
    out = np.zeros((n_el_i, n_az_i), np.float64)
    np.add.at(out, (el_i, az_i), 1.0)
    return out


# --------------------------------------------------------------------------- #
# curvature —— 形状指数(可逆)                                                  #
# --------------------------------------------------------------------------- #
def _principal(curvature, what="curvature"):
    """主曲率を ``(N,2)`` の ``[k1, k2]``(k1 >= k2)へ寄せる。

    ``curvature`` を宣言する既存 3 op は**3 つとも形が違う**(実測):
    ``principal_curvatures`` = 2-tuple の (N,) / ``vertex_curvature`` = (nv,) /
    ``curvature_maps`` = 4 本の volume のタプル。ここで受けるのは主曲率の対
    (前 2 者のうち対を持つ形)だけで、(N,) の単独曲率は
    「もう一方が 0 だ」と決めつけると**黙って間違った形状指数**を出すので拒否する。
    """
    p = _n2(curvature, what)
    k1 = np.maximum(p[:, 0], p[:, 1])
    k2 = np.minimum(p[:, 0], p[:, 1])
    return np.stack([k1, k2], axis=1)


def curvature_to_shape_index(curvature):
    """主曲率 ``(N,2)`` → 形状指数と曲がり ``(N,2)`` の ``pairs``。``curvature`` の出口。

    Koenderink & van Doorn, *Surface shape and curvature scales*, Image and
    Vision Computing 10(8) 1992 の (S, C):

        S = (2/pi) * atan2(k1 + k2, k1 - k2)      (k1 >= k2, S in [-1, 1])
        C = sqrt((k1^2 + k2^2) / 2)               (曲がりの大きさ)

    **除算でなく atan2 で書いてある**のが要点で、球状臍点 (k1 == k2) でも
    平面 (k1 == k2 == 0) でもゼロ除算にならず、:func:`shape_index_to_curvature`
    との往復が**全域で厳密**になる(実測 max|Δ| = 4.6e-16)。教科書の
    ``atan((k1+k2)/(k1-k2))`` をそのまま実装すると臍点で NaN が出て、
    その NaN が下流で「暗い画素」に化ける。

    S = -1 は杯、0 は鞍、+1 は帽子。C は形と独立な「どれだけ曲がっているか」。

    **入力順の情報だけは戻らない**: (k2, k1) の順で渡しても内部で k1 >= k2 へ
    並べ替えるので、往復すると必ず降順で返る(向きの規約であり、値の損失ではない)。

    Args:
        curvature: (N, 2) の ``[k1, k2]``、または 2 本の等長 1-D のタプル
            (``principal_curvatures`` の素の返りがこれ)。
    Returns:
        (N, 2) float64。列 0 = S in [-1, 1]、列 1 = C >= 0。
    Raises:
        ValueError: 形状不正 / 非有限。
    """
    k = _principal(curvature)
    s = (2.0 / np.pi) * np.arctan2(k[:, 0] + k[:, 1], k[:, 0] - k[:, 1])
    c = np.sqrt((k[:, 0] ** 2 + k[:, 1] ** 2) / 2.0)
    return np.stack([s, c], axis=1)


def shape_index_to_curvature(pairs):
    """形状指数と曲がり ``(N,2)`` → 主曲率 ``(N,2)``。:func:`curvature_to_shape_index` の逆。

    theta = pi*S/2 として ``k1 = C(sin+cos)``, ``k2 = C(sin-cos)``。
    (S, C) の定義式を解いた閉形式で、近似も反復も入っていない。

    Args:
        pairs: (N, 2) の ``[S, C]``。
    Returns:
        (N, 2) float64 の ``[k1, k2]``(k1 >= k2)。
    Raises:
        ValueError: |S| > 1 / C < 0 / 形状不正 / 非有限。
    """
    p = _n2(pairs, "pairs")
    s, c = p[:, 0], p[:, 1]
    if np.any(np.abs(s) > 1.0):
        raise ValueError(f"pairs: shape index must be within [-1, 1]; got |S| max {float(np.max(np.abs(s)))}")
    if np.any(c < 0.0):
        raise ValueError(f"pairs: curvedness must be >= 0; got min {float(np.min(c))}")
    th = np.pi * s / 2.0
    sn, cs = np.sin(th), np.cos(th)
    return np.stack([c * (sn + cs), c * (sn - cs)], axis=1)


def curvature_to_table(curvature):
    """曲率 → 分布の要約 ``table``。**一方向**(統計は情報を捨てるのが仕事)。

    (N,) の単独曲率も (N,2) の主曲率対も受ける —— 統計を出すだけなら対で
    ある必要が無いため。``kind`` に受けた形を書き戻すので、下流は「対だったのか」
    を後から判別できる。

    Args:
        curvature: (N,) / (N, 2) / 2 本の等長 1-D のタプル。
    Returns:
        dict。``kind`` / ``n`` / ``min`` / ``max`` / ``mean`` / ``rms`` /
        ``p05`` / ``p50`` / ``p95``、対なら ``gauss_mean``(K = k1*k2 の平均)と
        ``mean_curvature_mean``((k1+k2)/2 の平均)。
    Raises:
        ValueError: 形状不正 / 非有限。
    """
    try:
        k = _principal(curvature)
        kind, flat = "principal_pair", k.ravel()
    except ValueError:
        a = _arr(curvature, "curvature")
        if a.ndim != 1:
            raise ValueError(f"curvature: must be (N,), (N, 2) or a 2-tuple of 1-D; got {a.shape}")
        k, kind, flat = None, "scalar", a
    out = {
        "kind": kind, "n": int(flat.size),
        "min": float(np.min(flat)), "max": float(np.max(flat)),
        "mean": float(np.mean(flat)), "rms": float(np.sqrt(np.mean(flat ** 2))),
        "p05": float(np.percentile(flat, 5.0)),
        "p50": float(np.percentile(flat, 50.0)),
        "p95": float(np.percentile(flat, 95.0)),
    }
    if k is not None:
        out["n"] = int(k.shape[0])
        out["gauss_mean"] = float(np.mean(k[:, 0] * k[:, 1]))
        out["mean_curvature_mean"] = float(np.mean((k[:, 0] + k[:, 1]) / 2.0))
    return out


# --------------------------------------------------------------------------- #
# descriptor —— 行列化(可逆)                                                   #
# --------------------------------------------------------------------------- #
def descriptor_to_matrix(descriptor):
    """記述子 → ``matrix``。``descriptor`` の出口(**可逆**)。

    1-D の記述子 (n,) は **(1, n)** の 1 行行列にする。2-D の記述子束
    (``sh_descriptor`` の (12, 9) のような「点 x 次元」)はそのまま通す。
    こうしておくと記述子バンクに ``mat_svd`` / ``mat_pinv`` / ``mat_cond``
    がそのまま掛かる —— 記述子は本質的にベクトルなので、行列語彙へ渡すのは
    梱包の付け替えであって変形ではない。

    :func:`matrix_to_descriptor` と往復して **bit 一致**(実測 max|Δ| = 0.0)。

    Args:
        descriptor: (n,) または (m, n) の実配列。
    Returns:
        (1, n) または (m, n) float64。
    Raises:
        ValueError: 3-D 以上 / 非有限 / dict(``fit_zernike`` は dict を返すので
            ここで拒否される —— 詳細は本モジュール docstring)。
    """
    if isinstance(descriptor, dict):
        raise ValueError(
            "descriptor: dict is not an array descriptor — `fit_zernike` returns "
            "{(n, m): coefficient}; convert it explicitly (the key order is part of "
            "its meaning and must not be guessed here)")
    a = _arr(descriptor, "descriptor")
    if a.ndim == 1:
        return a.reshape(1, -1)
    if a.ndim == 2:
        return a
    raise ValueError(f"descriptor: must be 1-D or 2-D; got {a.shape}")


def matrix_to_descriptor(matrix):
    """``matrix`` → 記述子。:func:`descriptor_to_matrix` の逆。

    1 行の行列 (1, n) は (n,) へ戻す(それが元の 1-D 記述子だから)。
    2 行以上はそのまま。**この非対称は意図的**で、これが無いと
    ``descriptor -> matrix -> descriptor`` の往復が (n,) から (1,n) へ
    静かに形を変える = 型の嘘そのものになる。

    ★**測って残す非可逆点**: そのぶん、元から **(1, n) の 2-D だった記述子**は
    往復で (n,) の 1-D になる —— (1,n) の行列は「1-D 記述子を包んだもの」と
    「行が 1 本しかない記述子束」の区別を持たないので、**この 1 ケースだけは
    原理的に戻せない**。値は全て保存されるので損失は「行が 1 本だった」という
    メタ情報のみ。どちらを非可逆にするか選ばされる状況で、
    ``descriptor`` の圧倒的多数(実測 14 producers 中 12 が 1-D)を厳密側に
    倒した。``tests/test_reprconv.py::test_one_row_descriptor_ambiguity_is_documented``
    がこの穴を**塞がずに固定**している(隠すと、いつか黙って形が変わる)。

    Args:
        matrix: (m, n) の実配列。
    Returns:
        m == 1 なら (n,)、それ以外は (m, n)。
    Raises:
        ValueError: 2-D でない / 非有限。
    """
    a = _arr(matrix, "matrix")
    if a.ndim != 2:
        raise ValueError(f"matrix: must be 2-D; got {a.shape}")
    return a.reshape(-1) if a.shape[0] == 1 else a


def descriptor_to_table(descriptor):
    """記述子 → 要約 ``table``。**一方向**。

    次元・ノルム・エネルギー集中(正規化した二乗和の上位 10% が占める割合)を
    出す。記述子が「実質何次元使っているか」を見るためのもので、次元だけ多くて
    ほぼ全部 0 という失敗を可視化する。

    Args:
        descriptor: (n,) または (m, n)。
    Returns:
        dict(``shape`` / ``n`` / ``l2`` / ``mean`` / ``std`` / ``min`` /
        ``max`` / ``top10pct_energy`` / ``nonzero_fraction``)。
    Raises:
        ValueError: 形状不正 / 非有限。
    """
    m = descriptor_to_matrix(descriptor)
    flat = m.reshape(-1)
    e = flat ** 2
    tot = float(np.sum(e))
    k = max(1, int(round(0.1 * flat.size)))
    top = float(np.sum(np.sort(e)[::-1][:k]))
    return {
        "shape": tuple(int(s) for s in m.shape), "n": int(flat.size),
        "l2": float(np.linalg.norm(flat)), "mean": float(np.mean(flat)),
        "std": float(np.std(flat)), "min": float(np.min(flat)), "max": float(np.max(flat)),
        "top10pct_energy": (top / tot) if tot > 0.0 else 0.0,
        "nonzero_fraction": float(np.count_nonzero(flat)) / float(flat.size),
    }


# --------------------------------------------------------------------------- #
# keypoints / position —— 軸の約束を名前に書く                                  #
# --------------------------------------------------------------------------- #
def keypoints_uv_to_points(keypoints, z=0.0):
    """画像座標 ``(N,2) = (u, v)`` → 点群 ``(N,3) = (z, y, x)``。``keypoints`` の出口。

    **op 名に軸の約束が書いてある**のは、この repo で ``keypoints`` を産む
    ``match3d.project_points`` が **(u, v) = (列, 行)** を返し、``points`` を産む
    ``fuse3d.to_points(voxel)`` が **(z, y, x)** を返すから —— 素直に「先頭 2 列」
    として繋ぐと**例外も NaN も出ないまま行と列が入れ替わる**。ここでは
    ``y = v``、``x = u`` と明示的に入れ替えて渡す。

    :func:`points_zyx_to_keypoints_uv` と往復して **bit 一致**(z を渡した向き)。

    Args:
        keypoints: (N, 2) の (u, v)。
        z: 載せる平面の z(スカラ、または (N,) の配列)。
    Returns:
        (N, 3) float64 の (z, y, x)。
    Raises:
        ValueError: 形状不正 / 非有限 / z の長さ不一致。
    """
    kp = _n2(keypoints, "keypoints")
    zc = np.asarray(z, dtype=float)
    if zc.ndim == 0:
        zc = np.full(kp.shape[0], float(zc))
    else:
        zc = _arr(zc, "z")
        if zc.shape != (kp.shape[0],):
            raise ValueError(f"z: must be a scalar or ({kp.shape[0]},); got {zc.shape}")
    return np.stack([zc, kp[:, 1], kp[:, 0]], axis=1)


def points_zyx_to_keypoints_uv(points):
    """点群 ``(N,3) = (z, y, x)`` → 画像座標 ``(N,2) = (u, v)``。

    :func:`keypoints_uv_to_points` の逆向き。**不可逆** —— z が落ちる。
    落ちる量は測れる: 往復して戻ってこない値は z 列そのもので、
    ``selftest`` は「z の RMS = 落とした情報量」として数字で出す。

    Args:
        points: (N, 3) の (z, y, x)。
    Returns:
        (N, 2) float64 の (u, v) = (x, y)。
    Raises:
        ValueError: 形状不正 / 非有限。
    """
    p = _n3(points, "points")
    return np.stack([p[:, 2], p[:, 1]], axis=1)


def keypoints_to_image2d(keypoints, shape=(64, 64)):
    """画像座標 ``(N,2) = (u, v)`` → 計数画像 ``(H, W)``。``keypoints`` の 2 つ目の出口。

    ``round(v)`` を行、``round(u)`` を列として 1 ずつ加算する。**画素格子への
    量子化が損失**で、:func:`keypoints_from_image2d` と往復すると位置が
    最大 0.5 画素ずれる(よく離れた 225 点での実測: **軸あたり** RMS 0.2835 px =
    一様量子化の理論値 1/sqrt(12) = 0.2887 と一致。2-D 距離では sqrt(2) 倍の
    0.4009 px で、理論 sqrt(2/12) = 0.4082)。
    ★ここも一度間違えた: 2-D 距離の実測を 1-D の理論値と並べて「0.29 のはずが
    0.40 だ」と読みかけた —— 軸ごとの量と距離の量を混ぜると、正しい実装が
    誤っているように見える。
    近接した点は連結成分として融合するので、往復で点数も減りうる
    (実測: 60 点をランダムに置くと 54 点)。

    範囲外の点は**黙って捨てない** —— 捨てると「検出が減った」のか
    「画像が小さすぎた」のかが区別できなくなる。

    Args:
        keypoints: (N, 2) の (u, v)。
        shape: (H, W)。
    Returns:
        (H, W) float64 の計数画像。
    Raises:
        ValueError: 形状不正 / 非有限 / 範囲外の点がある / shape が上限超。
    """
    kp = _n2(keypoints, "keypoints")
    h, w = _shape2(shape, "keypoints_to_image2d")
    col = np.rint(kp[:, 0]).astype(np.int64)
    row = np.rint(kp[:, 1]).astype(np.int64)
    bad = (row < 0) | (row >= h) | (col < 0) | (col >= w)
    if np.any(bad):
        raise ValueError(
            f"keypoints: {int(np.count_nonzero(bad))} point(s) fall outside the "
            f"({h}, {w}) raster (u in [{float(kp[:, 0].min()):.2f}, "
            f"{float(kp[:, 0].max()):.2f}], v in [{float(kp[:, 1].min()):.2f}, "
            f"{float(kp[:, 1].max()):.2f}]) — enlarge shape or clip explicitly")
    out = np.zeros((h, w), np.float64)
    np.add.at(out, (row, col), 1.0)
    return out


def keypoints_from_image2d(image2d, threshold=0.0):
    """計数/応答画像 ``(H, W)`` → 画像座標 ``(N,2) = (u, v)``。往復の戻り路。

    ``> threshold`` の画素を 8 近傍で連結成分に分け、各成分の**強度重み付き
    重心**を返す。重み付きにするのは、副画素の情報が残っている応答画像
    (相関ピーク等)で往復誤差を量子化以下へ落とせるようにするため。

    **8 近傍の連結が損失の主犯**である点に注意: 隣り合う画素に落ちた 2 点は
    1 つの成分に融合し、重心が 2 点の中間へ動く。``selftest`` は
    「よく離れた点だけの量子化誤差」と「融合を含む全体」を**別々に**測る
    (混ぜると量子化の理論値 0.2887 px と比較できなくなる)。

    Args:
        image2d: (H, W) の実画像。
        threshold: この値を超えた画素だけを拾う。
    Returns:
        (N, 2) float64 の (u, v)。行順は ``scipy.ndimage.label`` のラベル順。
    Raises:
        ValueError: 2-D でない / 非有限 / 閾値を超える画素が 1 つも無い。
    """
    from scipy import ndimage                              # noqa: PLC0415

    img = _arr(image2d, "image2d")
    if img.ndim != 2:
        raise ValueError(f"image2d: must be 2-D; got {img.shape}")
    mask = img > float(threshold)
    if not mask.any():
        raise ValueError(f"image2d: no pixel exceeds threshold {float(threshold)} "
                         f"(max is {float(img.max())}) — nothing to extract")
    lab, n = ndimage.label(mask, structure=np.ones((3, 3), bool))
    idx = np.arange(1, n + 1)
    cen = ndimage.center_of_mass(np.where(mask, img, 0.0), lab, idx)
    cen = np.asarray(cen, dtype=float).reshape(n, 2)       # (row, col)
    return np.stack([cen[:, 1], cen[:, 0]], axis=1)        # (u, v)


def position_to_points(position):
    """位置 ``(z, y, x)`` → 1 点の点群 ``(1, 3)``。``position`` の出口(**可逆**)。

    ``position`` は ``volregion.vol_rle_centroid`` などが返す 3-tuple で、
    順序は **(z, y, x)**(``vol_rle_centroid`` の docstring が明示している)。
    点群も voxel 由来なら同じ順なので、そのまま 1 行の点群にできる。

    Args:
        position: 長さ 3 の列 (z, y, x)。
    Returns:
        (1, 3) float64。
    Raises:
        ValueError: 長さが 3 でない / 非有限。
    """
    a = _arr(position, "position")
    if a.shape != (3,):
        raise ValueError(f"position: must be a length-3 (z, y, x) sequence; got {a.shape}")
    return a.reshape(1, 3)


def points_to_position(points):
    """点群 ``(N,3)`` → 重心 ``(z, y, x)``。**不可逆**(分布を捨てる)。

    捨てた量は測れる: 重心まわりの RMS 距離が「1 点に潰したときに失った広がり」
    そのもので、``selftest`` はこれを数字で出す。N = 1 のときだけ
    :func:`position_to_points` との往復が bit 一致する。

    Args:
        points: (N, 3) の (z, y, x)。
    Returns:
        3-tuple の float (z, y, x)。
    Raises:
        ValueError: 形状不正 / 非有限。
    """
    p = _n3(points, "points")
    c = p.mean(axis=0)
    return (float(c[0]), float(c[1]), float(c[2]))


# --------------------------------------------------------------------------- #
# indices / labels                                                             #
# --------------------------------------------------------------------------- #
def indices_to_labels(indices):
    """添字 ``(N,)`` → 選択マスク ``labels``。``indices`` の出口(**可逆**)。

    ``max(indices) + 1`` 長の 1-D ラベル配列を作り、選ばれた位置に 1 を置く。
    ``indices -> labels -> indices`` は **bit 一致**(重複と順序を除く)。
    逆向き ``labels -> indices -> labels`` は**末尾の背景を落とす**
    (長さが ``max_index + 1`` に切り詰まる)—— これは情報の損失であって
    バグではないので、:func:`labels_to_indices` の docstring に量を書いてある。

    Args:
        indices: (N,) の非負整数配列。
    Returns:
        (max + 1,) の int64 ラベル配列(選択 = 1、背景 = 0)。
    Raises:
        ValueError: 1-D でない / 負 / 空 / 上限超。
    """
    a = _arr(indices, "indices", dtype=np.int64)
    if a.ndim != 1:
        raise ValueError(f"indices: must be 1-D; got {a.shape}")
    if np.any(a < 0):
        raise ValueError(f"indices: must be non-negative; got min {int(a.min())}")
    n = int(a.max()) + 1
    if n > MAX_ELEMENTS:
        raise ValueError(f"indices: max index {int(a.max())} would need a "
                         f"{n}-element label array (> MAX_ELEMENTS={MAX_ELEMENTS})")
    out = np.zeros(n, np.int64)
    out[a] = 1
    return out


def labels_to_indices(labels):
    """``labels`` → 非背景の添字 ``(N,)``。:func:`indices_to_labels` の逆向き。

    2-D 以上のラベル画像も受ける —— その場合の添字は
    **``labels.ravel()`` への添字**(C 順)である。``np.unravel_index`` で
    座標へ戻せるが、**戻すには元の shape が要る**ので、この向きは
    ``shape`` を捨てている(不可逆)。

    Args:
        labels: 任意次元の整数/実ラベル配列。
    Returns:
        (N,) int64。ラベルが 0 でない位置の平坦添字(昇順)。
    Raises:
        ValueError: 空 / 非有限 / 非背景が 1 つも無い。
    """
    a = _arr(labels, "labels")
    idx = np.flatnonzero(a.reshape(-1) != 0)
    if idx.size == 0:
        raise ValueError("labels: every element is background (0) — no indices to extract")
    return idx.astype(np.int64)


def select_points(points, indices):
    """点群 ``(N,3)`` と添字 ``(M,)`` → 部分点群 ``(M,3)``。``indices`` の消費側。

    ``indices`` を産む op は 6 つあるのに(``iss_keypoints`` /
    ``farthest_point_sampling`` / ``alpha_shape_boundary`` / ``find_peaks`` /
    ``zero_crossings_funct_1d`` / ``cad_visible_faces``)、**添字を食う単入力 op が
    1 つも無かった** —— 添字は「元の集合とセットで初めて意味を持つ」ので、
    単入力では原理的に作れない。よってこれは 2 入力にしてある。

    Args:
        points: (N, 3)。
        indices: (M,) の非負整数、N 未満。
    Returns:
        (M, 3) float64。
    Raises:
        ValueError: 範囲外の添字 / 形状不正 / 非有限。
    """
    p = _n3(points, "points")
    a = _arr(indices, "indices", dtype=np.int64)
    if a.ndim != 1:
        raise ValueError(f"indices: must be 1-D; got {a.shape}")
    if np.any(a < 0) or np.any(a >= p.shape[0]):
        raise ValueError(f"indices: out of range for {p.shape[0]} points "
                         f"(min {int(a.min())}, max {int(a.max())})")
    return p[a]


# --------------------------------------------------------------------------- #
# pairs                                                                        #
# --------------------------------------------------------------------------- #
def pairs_to_signal(pairs):
    """対 ``(N,2)`` → 従属変数の ``signal`` ``(N,)``。``pairs`` の 2 つ目の出口。

    列 1(y)だけを取り出す。``funct_1d_to_pairs`` が (x, y) を並べた
    (N,2) を返すので、その逆向きにあたる —— **x が等間隔ならば**
    ``signal -> pairs -> signal`` は bit 一致する。等間隔でない x を持つ対を
    通すと、**x の情報が黙って落ちる**(``signal`` は添字が等間隔だという前提の型)。
    だから :func:`pairs_to_table` が ``x_uniform`` を必ず一緒に出す。

    Args:
        pairs: (N, 2) または 2 本の等長 1-D のタプル。
    Returns:
        (N,) float64。
    Raises:
        ValueError: 形状不正 / 非有限。
    """
    return _n2(pairs, "pairs")[:, 1].copy()


def pairs_to_image2d(pairs, shape=(64, 64)):
    """対 ``(N,2)`` → 散布密度画像 ``(H, W)``。``pairs`` の 3 つ目の出口。

    列 0 を行方向、列 1 を列方向に、それぞれの最小-最大で正規化して bin へ落とす
    (2-D ヒストグラム)。位相図・相関図として見るためのもので、**不可逆**
    (bin 幅ぶんの量子化 + 正規化で絶対値のスケールを捨てる)。
    捨てたスケールは戻せるように ``extent`` を…返さない —— 返すと ``image2d``
    でなくなる。必要なら :func:`pairs_to_table` の ``x_min`` などを使う。

    定数列(最小 == 最大)は 0.5 の位置へ集める(0 除算を避けるが、
    それを「密度が中央に集中している」と読まれないよう、bin は 1 本だけ立つ)。

    Args:
        pairs: (N, 2)。
        shape: (H, W)。
    Returns:
        (H, W) float64、最大値 1.0 に正規化した密度。
    Raises:
        ValueError: 形状不正 / 非有限 / shape が上限超。
    """
    p = _n2(pairs, "pairs")
    h, w = _shape2(shape, "pairs_to_image2d")

    def _bin(col, n):
        lo, hi = float(col.min()), float(col.max())
        if hi <= lo:
            return np.full(col.shape, n // 2, np.int64)
        return np.clip(((col - lo) / (hi - lo) * n).astype(np.int64), 0, n - 1)

    out = np.zeros((h, w), np.float64)
    np.add.at(out, (_bin(p[:, 0], h), _bin(p[:, 1], w)), 1.0)
    m = float(out.max())
    return out / m if m > 0.0 else out


def pairs_to_table(pairs):
    """対 ``(N,2)`` → 要約 ``table``。**一方向**。

    ``x_uniform`` は「列 0 が等間隔か」の判定で、これが False の対を
    :func:`pairs_to_signal` に通すと x が黙って落ちる(上の docstring 参照)。
    判定は差分の最大値と最小値の開きで行い、閾値は全幅に対して 1e-9(相対)。

    Args:
        pairs: (N, 2)。
    Returns:
        dict(``n`` / ``x_min`` / ``x_max`` / ``y_min`` / ``y_max`` /
        ``y_mean`` / ``x_uniform`` / ``x_step``(等間隔のときのみ) /
        ``pearson_r``(N >= 2 かつ両列が定数でないとき))。
    Raises:
        ValueError: 形状不正 / 非有限。
    """
    p = _n2(pairs, "pairs")
    x, y = p[:, 0], p[:, 1]
    out = {"n": int(p.shape[0]), "x_min": float(x.min()), "x_max": float(x.max()),
           "y_min": float(y.min()), "y_max": float(y.max()), "y_mean": float(y.mean())}
    if p.shape[0] >= 2:
        d = np.diff(x)
        span = float(np.max(np.abs(d))) if d.size else 0.0
        uniform = bool(span == 0.0 or (float(np.max(d) - np.min(d)) <= 1e-9 * max(span, 1.0)))
        out["x_uniform"] = uniform
        if uniform:
            out["x_step"] = float(np.mean(d))
        if x.std() > 0.0 and y.std() > 0.0:
            out["pearson_r"] = float(np.corrcoef(x, y)[0, 1])
    else:
        out["x_uniform"] = True
    return out


# --------------------------------------------------------------------------- #
# flow —— 同じ型名の下に **2 つの別物** がいる                                   #
# --------------------------------------------------------------------------- #
#
# 実測 2026-09-02: ``flow`` を宣言する 4 op のうち ``scene_flow_lk`` は
# **(3, D, H, W) の密な体積フロー**(成分は dz, dy, dx)、残る 3 op
# (``estimate_flow`` / ``nearest_neighbor_flow`` / ``smooth_flow``)は
# **(N, 3) の散在フロー**を返す。``TYPE_CHECKS`` に ``flow`` の述語が無いので、
# **どちらも黙って同じプールに入る**。ここでは 1 つの op に両方を食わせず、
# **密用と散在用で op を分けて、相手の形は fail-closed** にする。
# (分けずに ndim で分岐すると、出る型まで変わる = 型の嘘になる。)
def _dense_flow(flow):
    f = _arr(flow, "flow")
    if f.ndim != 4 or f.shape[0] != 3:
        raise ValueError(
            f"flow: this op takes DENSE scene flow (3, D, H, W) as returned by "
            f"`scene_flow_lk`; got {f.shape}. Scattered (N, 3) flow from "
            f"`estimate_flow` goes to flow_speed()/flow_apply() instead")
    return f


def _scattered_flow(flow):
    f = _arr(flow, "flow")
    if f.ndim != 2 or f.shape[1] != 3:
        raise ValueError(
            f"flow: this op takes SCATTERED flow (N, 3) as returned by "
            f"`estimate_flow`; got {f.shape}. Dense (3, D, H, W) flow from "
            f"`scene_flow_lk` goes to flow_magnitude()/flow_to_rgbimage() instead")
    return f


def flow_magnitude(flow):
    """密なシーンフロー ``(3,D,H,W)`` → 速さの体積 ``voxel (D,H,W)``。``flow`` の出口。

    ``sqrt(dz^2 + dy^2 + dx^2)``。**一方向**(向きを捨てるので戻せない)。
    捨てた量は明示できる: 3 成分のうち 2 自由度ぶんの方向が消え、残るのは
    大きさだけ。方向まで見たいときは :func:`flow_to_rgbimage`。

    Args:
        flow: (3, D, H, W)。成分順は (dz, dy, dx)(``scene_flow_lk`` の約束)。
    Returns:
        (D, H, W) float64。
    Raises:
        ValueError: 密フローでない / 非有限。
    """
    f = _dense_flow(flow)
    return np.sqrt(np.sum(f.astype(np.float64) ** 2, axis=0))


def flow_to_rgbimage(flow, index=None, scale=None):
    """密なシーンフローの 1 スライス → 色相=向き・明度=速さの ``rgbimage``。

    光学フローの標準的な可視化(色相環)を 3-D フローの z スライスに当てる:
    ``hue = atan2(dy, dx)``(度で 0-360)、``value = |(dy, dx)| / scale``、
    彩度は 1。**dz は捨てる** —— 面内成分だけの図であることを明示する
    (捨てた成分を色に混ぜると「見えている色が何の量か」が誰にも言えなくなる)。

    **一方向**。色相環の凡例は図の側で必ず一緒に焼くこと(色の意味が書いていない
    フロー図は、綺麗なだけで読めない)。

    Args:
        flow: (3, D, H, W)。
        index: 取り出す z スライス(既定 = 中央)。
        scale: 明度 1.0 に対応する面内速さ(既定 = そのスライスの最大値。
            0 なら全面黒を返す)。
    Returns:
        (H, W, 3) float64、値域 [0, 1]。
    Raises:
        ValueError: 密フローでない / index が範囲外 / scale <= 0。
    """
    f = _dense_flow(flow)
    d = f.shape[1]
    k = d // 2 if index is None else int(index)
    if not 0 <= k < d:
        raise ValueError(f"index: must be within [0, {d - 1}]; got {k}")
    dy, dx = f[1, k].astype(np.float64), f[2, k].astype(np.float64)
    mag = np.hypot(dy, dx)
    if scale is None:
        s = float(mag.max())
    else:
        s = float(scale)
        if s <= 0.0:
            raise ValueError(f"scale: must be > 0; got {s}")
    val = np.clip(mag / s, 0.0, 1.0) if s > 0.0 else np.zeros_like(mag)
    hue = (np.degrees(np.arctan2(dy, dx)) % 360.0) / 60.0
    i = np.floor(hue).astype(np.int64) % 6
    frac = hue - np.floor(hue)
    p = np.zeros_like(val)
    q = val * (1.0 - frac)
    t = val * frac
    r = np.select([i == 0, i == 1, i == 2, i == 3, i == 4, i == 5], [val, q, p, p, t, val])
    g = np.select([i == 0, i == 1, i == 2, i == 3, i == 4, i == 5], [t, val, val, q, p, p])
    b = np.select([i == 0, i == 1, i == 2, i == 3, i == 4, i == 5], [p, p, t, val, val, q])
    return np.stack([r, g, b], axis=-1)


def flow_speed(flow):
    """散在フロー ``(N,3)`` → 速さの ``signal`` ``(N,)``。散在 ``flow`` の出口。

    **一方向**(向きを捨てる)。密フローを渡すと fail-closed —— 同じ ``flow``
    という型名の下に別物が 2 つ入っているため、受け側で必ず選ばせる。

    Args:
        flow: (N, 3) の変位ベクトル場。
    Returns:
        (N,) float64。
    Raises:
        ValueError: 散在フローでない / 非有限。
    """
    return np.linalg.norm(_scattered_flow(flow), axis=1)


def flow_apply(points, flow):
    """点群 ``(N,3)`` に散在フロー ``(N,3)`` を足す → ``points``。``flow`` の消費側。

    ``estimate_flow(a, b)`` が「a の各点から b の最近傍への変位」を返すので、
    ``flow_apply(a, estimate_flow(a, b))`` は **b の点のうち a から最近傍として
    選ばれたもの**へ移る。往復が厳密になるのは対応が全単射のときだけで、
    そうでなければ「a の 2 点が b の同じ点へ落ちる」ぶんだけ形が縮む
    —— ``selftest`` はこの残差を数字で出す。

    Args:
        points: (N, 3)。
        flow: (N, 3)。
    Returns:
        (N, 3) float64。
    Raises:
        ValueError: 行数不一致 / 形状不正 / 非有限。
    """
    p = _n3(points, "points")
    f = _scattered_flow(flow)
    if p.shape != f.shape:
        raise ValueError(f"flow: must match points row-for-row; got {f.shape} vs {p.shape}")
    return p + f


# --------------------------------------------------------------------------- #
# gaussians —— 産む op が 1 つも無かった型                                       #
# --------------------------------------------------------------------------- #
def points_to_gaussians(points, k=6, scale=1.0):
    """点群 ``(N,3)`` → 等方ガウシアン ``gaussians``。**この型の唯一の入口**。

    ``gaussians`` は台帳で ``fuse3d.to_points`` が食う型だが、**産む op が
    1 つも無かった**(実測)—— 消費側だけがある型は、生成器を種として置かない限り
    一度も実行されない。ここでは 3D Gaussian Splatting の初期化と同じやり方で
    作る: 各点の k 近傍までの**平均距離**を sigma、重みを 1/N の等分にする。

    ``mu`` は入力点そのものなので :func:`gaussians_to_points` と往復して
    **bit 一致**(実測 max|Δ| = 0.0)。sigma と w は往復で戻らない —— 点群には
    もともと無かった量だからで、これは損失ではなく**追加**である。

    Args:
        points: (N, 3)。N >= 2。
        k: sigma を決める近傍数(既定 6)。N-1 を超えると N-1 に丸める。
        scale: sigma に掛ける係数(既定 1.0)。
    Returns:
        dict(``mu`` (N,3) / ``sigma`` (N,) / ``w`` (N,))。
    Raises:
        ValueError: N < 2 / k < 1 / scale <= 0 / 形状不正 / 非有限。
    """
    from scipy.spatial import cKDTree                      # noqa: PLC0415

    p = _n3(points, "points")
    n = p.shape[0]
    if n < 2:
        raise ValueError(f"points: need at least 2 points to estimate spacing; got {n}")
    kk = int(k)
    if kk < 1:
        raise ValueError(f"k: must be >= 1; got {kk}")
    sc = float(scale)
    if sc <= 0.0:
        raise ValueError(f"scale: must be > 0; got {sc}")
    kk = min(kk, n - 1)
    d, _ = cKDTree(p).query(p, k=kk + 1)                   # 自分自身を含むので +1
    sigma = np.asarray(d, float)[:, 1:].mean(axis=1) * sc
    # ★ 実バグの回帰点。最初ここを ``np.maximum(sigma, finfo.tiny)`` にしていた。
    # 重複点で sigma = 2.2e-308 になり、``gaussians_to_voxel`` の
    # ``sigma ** 3`` が **アンダーフローで 0** になって 0 除算 -> NaN。
    # 「0 を避けた」つもりが、下流で NaN を生む値に置き換えていた
    # (例外も出ないまま体積の一部が NaN になる = 黙って間違う典型)。
    # 重複点は「間隔が測れない」のだから、番兵で埋めずに fail-closed にする。
    bad = int(np.count_nonzero(sigma <= 0.0))
    if bad:
        raise ValueError(
            f"points: {bad} point(s) coincide with all {kk} of their nearest neighbours, "
            f"so the local spacing is 0 and sigma cannot be estimated — "
            f"deduplicate first (e.g. voxel_downsample) instead of taking a sentinel sigma")
    return {"mu": p.copy(), "sigma": sigma, "w": np.full(n, 1.0 / n)}


def _gaussians(g):
    if not isinstance(g, dict):
        raise ValueError(f"gaussians: must be a dict with 'mu'/'sigma'/'w'; got {type(g).__name__}")
    missing = [key for key in ("mu", "sigma", "w") if key not in g]
    if missing:
        raise ValueError(f"gaussians: missing key(s) {missing}")
    mu = _n3(g["mu"], "gaussians['mu']")
    sigma = _arr(g["sigma"], "gaussians['sigma']")
    w = _arr(g["w"], "gaussians['w']")
    if sigma.shape != (mu.shape[0],) or w.shape != (mu.shape[0],):
        raise ValueError(f"gaussians: sigma {sigma.shape} and w {w.shape} must both be "
                         f"({mu.shape[0]},) to match mu")
    if np.any(sigma <= 0.0):
        raise ValueError(f"gaussians: sigma must be > 0; got min {float(sigma.min())}")
    # sigma が小さすぎると正規化係数 1/sigma**3 がアンダーフロー/オーバーフローし、
    # **例外を出さずに** 0 除算 -> NaN、あるいは inf の密度になる。有限性を先に見る。
    norm = (2.0 * np.pi) ** 1.5 * sigma.astype(np.float64) ** 3
    if not np.all(np.isfinite(norm)) or np.any(norm <= 0.0):
        raise ValueError(
            f"gaussians: sigma min {float(sigma.min()):.3e} is too small — the density "
            f"normaliser 1/((2*pi)^1.5 * sigma^3) is not representable and would "
            f"silently produce NaN/Inf voxels")
    return mu, sigma, w


def gaussians_to_points(gaussians):
    """``gaussians`` → 中心の点群 ``(N,3)``。``gaussians`` の出口(**中心は可逆**)。

    Args:
        gaussians: ``mu`` / ``sigma`` / ``w`` を持つ dict。
    Returns:
        (N, 3) float64(``mu`` のコピー)。
    Raises:
        ValueError: キー欠落 / 形状不整合 / sigma <= 0 / 非有限。
    """
    mu, _, _ = _gaussians(gaussians)
    return mu.copy()


def gaussians_to_voxel(gaussians, shape=(32, 32, 32), origin=(0.0, 0.0, 0.0),
                       spacing=(1.0, 1.0, 1.0), truncate=3.0):
    """``gaussians`` → 密度 ``voxel (D,H,W)``。``gaussians`` の 2 つ目の出口。

    各ガウシアンを ``truncate * sigma`` で打ち切って加算する。**格子の原点と
    刻みを明示引数にしてある**のが要点で、既定の ``spacing=(1,1,1)`` を
    そのまま使うと「世界座標をそのまま添字にする」ことになり、実データでは
    まず間違う —— しかも例外は出ず、密度が別の場所に立つだけなので気づけない。
    ``tests/test_reprconv.py`` はこの取り違えを明示的に測っている。

    **不可逆**。損失は 3 つあり、どれも数字で測れる:
      * **打ち切り** —— 打ち切りは**軸並行の箱**(各軸 ±truncate*sigma)なので、
        残る質量は ``erf(t/sqrt(2))**3``。t = 3 で **99.194%**。
        ★ここは一度間違えた: 最初「3 sigma の**球**の質量 97.07%」と書いたが、
        実装は箱なので値が違う。刻みを 1.0 → 0.125 と細かくして極限を取ると
        99.30% → 99.19% へ収束し、球の 97.07% には**近づかない**ことで反証できた
        (``tests/test_reprconv.py::test_gaussians_to_voxel_mass_matches_box_truncation``)。
        例外も NaN も出ない、まさに「黙って間違った数字を返す」種類の誤り。
      * **格子求積** —— 中点則なので刻みが sigma に対して粗いと**上振れ**する
        (実測: sigma = 1.5 で刻み 1.0 のとき 99.94%、0.125 で 99.30%)。
      * **境界の切り落とし** —— 箱が volume の外へ出た分は落ちる。中心が縁に
        近いガウシアンでは打ち切りより遥かに大きい損失になる。

    Args:
        gaussians: ``mu`` / ``sigma`` / ``w`` を持つ dict。``mu`` は (z, y, x)。
        shape: (D, H, W)。
        origin: 格子の (z, y, x) 原点(世界座標)。
        spacing: 格子の (dz, dy, dx) 刻み(世界単位 / voxel)。
        truncate: 何 sigma で打ち切るか(既定 3)。
    Returns:
        (D, H, W) float64 の密度(値は「voxel あたりの重み和」で、体積積分が
        ``sum(w)`` に近づく)。
    Raises:
        ValueError: shape/spacing 不正 / truncate <= 0 / gaussians 不正。
    """
    mu, sigma, w = _gaussians(gaussians)
    d, h, ww = _shape3(shape, "gaussians_to_voxel")
    org = _arr(origin, "origin")
    sp = _arr(spacing, "spacing")
    if org.shape != (3,) or sp.shape != (3,):
        raise ValueError(f"origin {org.shape} and spacing {sp.shape} must both be (3,)")
    if np.any(sp <= 0.0):
        raise ValueError(f"spacing: must be > 0 in every axis; got {sp.tolist()}")
    tr = float(truncate)
    if tr <= 0.0:
        raise ValueError(f"truncate: must be > 0; got {tr}")

    out = np.zeros((d, h, ww), np.float64)
    idx = (mu - org) / sp                                   # 世界座標 -> voxel 添字
    rad = tr * sigma[:, None] / sp[None, :]                 # 軸ごとの半径 [voxel]
    cell = float(np.prod(sp))
    for i in range(mu.shape[0]):
        lo = np.maximum(np.floor(idx[i] - rad[i]).astype(np.int64), [0, 0, 0])
        hi = np.minimum(np.ceil(idx[i] + rad[i]).astype(np.int64) + 1, [d, h, ww])
        if np.any(hi <= lo):
            continue                                        # 格子の外に落ちた
        zz = (np.arange(lo[0], hi[0]) - idx[i, 0]) * sp[0]
        yy = (np.arange(lo[1], hi[1]) - idx[i, 1]) * sp[1]
        xx = (np.arange(lo[2], hi[2]) - idx[i, 2]) * sp[2]
        amp = w[i] / ((2.0 * np.pi) ** 1.5 * sigma[i] ** 3) * cell
        den = 2.0 * sigma[i] ** 2
        ez = np.exp(-(zz ** 2) / den)
        ey = np.exp(-(yy ** 2) / den)
        ex = np.exp(-(xx ** 2) / den)
        out[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]] += amp * (
            ez[:, None, None] * ey[None, :, None] * ex[None, None, :]
        )
    return out


# --------------------------------------------------------------------------- #
# score —— 産む op が 1 つも無かった型                                           #
# --------------------------------------------------------------------------- #
def correlation_score(voxel_a, voxel_b):
    """2 つの ``voxel`` → 正規化相互相関の ``score`` volume。**この型の唯一の入口**。

    ``score`` は ``refine_peak_newton`` が食う型だが、**台帳のどの op も
    ``score`` を産まなかった**(実測。生成器の種を置いてようやく到達していた)。
    ここでは FFT による循環相互相関を返す:

        score[s] = sum_x (a[x] - mean_a) * (b[x + s] - mean_b) / (N * std_a * std_b)

    したがって ``b`` が ``a`` を ``s0`` だけ ``np.roll`` したものなら、
    ピークは**厳密に** ``s0`` に立つ(閉形式の真値。テストがこれを使う)。
    循環相関なので端は巻き込む —— **打ち切り相関ではない**ことを明記しておく。

    Args:
        voxel_a: (D, H, W)。
        voxel_b: (D, H, W)、``voxel_a`` と同形。
    Returns:
        (D, H, W) float64、値域は概ね [-1, 1] (完全一致で 1.0)。
    Raises:
        ValueError: 3-D でない / 形が違う / 定数体積(標準偏差 0)/ 非有限。
    """
    a = _arr(voxel_a, "voxel_a")
    b = _arr(voxel_b, "voxel_b")
    if a.ndim != 3 or b.ndim != 3:
        raise ValueError(f"voxel: both must be 3-D; got {a.shape} and {b.shape}")
    if a.shape != b.shape:
        raise ValueError(f"voxel: shapes must match; got {a.shape} and {b.shape}")
    sa, sb = float(a.std()), float(b.std())
    if sa == 0.0 or sb == 0.0:
        raise ValueError("voxel: a constant volume has no correlation peak "
                         f"(std {sa} and {sb}) — refuse to return a flat score")
    fa = np.fft.fftn(a - a.mean())
    fb = np.fft.fftn(b - b.mean())
    c = np.real(np.fft.ifftn(np.conj(fa) * fb))
    return c / (a.size * sa * sb)


def score_to_position(score):
    """``score`` volume → 最大値の位置 ``position (z, y, x)``。``score`` の出口。

    整数格子上の argmax(副画素精緻化はしない —— それは既存の
    ``refine_peak_newton`` の仕事で、ここで真似ると 2 か所で別の答えが出る)。
    **一方向**(1 つの位置から volume は戻せない)。

    Args:
        score: (D, H, W)。
    Returns:
        3-tuple の float (z, y, x)。
    Raises:
        ValueError: 3-D でない / 非有限。
    """
    s = _arr(score, "score")
    if s.ndim != 3:
        raise ValueError(f"score: must be 3-D (D, H, W); got {s.shape}")
    z, y, x = np.unravel_index(int(np.argmax(s)), s.shape)
    return (float(z), float(y), float(x))


def score_to_image2d(score, axis=0):
    """``score`` volume → 最大値投影 ``image2d``。``score`` の 2 つ目の出口。

    指定軸に沿った最大値投影(MIP)。**一方向**。相関ピークが「どの面から見ても
    1 本に見えるか」を確かめるのに使う —— 2 本見えたら対応が曖昧という意味。

    Args:
        score: (D, H, W)。
        axis: 潰す軸(0/1/2)。
    Returns:
        (H, W) 等の 2-D float64。
    Raises:
        ValueError: 3-D でない / axis が範囲外 / 非有限。
    """
    s = _arr(score, "score")
    if s.ndim != 3:
        raise ValueError(f"score: must be 3-D (D, H, W); got {s.shape}")
    ax = int(axis)
    if ax not in (0, 1, 2):
        raise ValueError(f"axis: must be 0, 1 or 2; got {ax}")
    return s.max(axis=ax)


# --------------------------------------------------------------------------- #
# 小さな代数 —— 軸と単位の規律を検査する面                                       #
# --------------------------------------------------------------------------- #
def angle_to_matrix(angle):
    """角度 **[度]** → z 軸まわりの回転行列 ``matrix (3,3)``。``angle`` の出口。

    ``angle_to_matrix(90)`` は軸1(y)を軸2(x)へ送り、軸2(x)を **−軸1**(−y)へ
    送る(``R @ [0,1,0] = [0,0,1]``、``R @ [0,0,1] = [0,-1,0]``、実測)。
    2-D の :func:`rot_scale_to_matrix` と同じ ``[[c,-s],[s,c]]`` の向き
    (軸 0 → 軸 1)を軸 (1, 2) に置いたもので、:func:`matrix_to_angle` の
    ``atan2(R[2,1], R[1,1])`` もこの向きで往復する。**度**であることと
    **どちらの軸へ回るか**が、この段落の全内容である。ラジアンを渡すと
    例外は出ず、ただ 57.3 分の 1 だけ回った行列が返る。

    Args:
        angle: 度。
    Returns:
        (3, 3) float64、行列式 1 の直交行列。
    Raises:
        ValueError: スカラでない / 非有限。
    """
    a = _arr(angle, "angle")
    if a.shape != ():
        raise ValueError(f"angle: must be a scalar in degrees; got shape {a.shape}")
    t = np.radians(float(a))
    c, s = np.cos(t), np.sin(t)
    return np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]])


def matrix_to_angle(matrix):
    """z 軸まわりの回転行列 → 角度 **[度]**。:func:`angle_to_matrix` の逆。

    ``atan2(R[2,1], R[1,1])`` を度で返す(-180, 180]。往復は
    (-180, 180] の範囲で **bit 一致に近い**(実測 max|Δ| = 2.8e-14 度)。

    Args:
        matrix: (3, 3)。
    Returns:
        float(度)。
    Raises:
        ValueError: (3,3) でない / 非有限。
    """
    m = _arr(matrix, "matrix")
    if m.shape != (3, 3):
        raise ValueError(f"matrix: must be (3, 3); got {m.shape}")
    return float(np.degrees(np.arctan2(m[2, 1], m[1, 1])))


def rot_scale_to_matrix(rot_scale):
    """``(角度[度], 倍率)`` → 2-D 相似変換 ``matrix (2,2)``。``rot_scale`` の出口。

    ``match_logpolar_z`` が返す 2-tuple をそのまま行列にする。
    :func:`matrix_to_rot_scale` と往復して実測 max|Δ| = 2.8e-14(角度は度、倍率は無次元)。

    Args:
        rot_scale: 長さ 2 の列 ``(angle_deg, scale)``。scale > 0。
    Returns:
        (2, 2) float64。
    Raises:
        ValueError: 長さが 2 でない / scale <= 0 / 非有限。
    """
    a = _arr(rot_scale, "rot_scale")
    if a.shape != (2,):
        raise ValueError(f"rot_scale: must be a length-2 (angle_deg, scale); got {a.shape}")
    ang, sc = float(a[0]), float(a[1])
    if sc <= 0.0:
        raise ValueError(f"rot_scale: scale must be > 0; got {sc}")
    t = np.radians(ang)
    return sc * np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]])


def matrix_to_rot_scale(matrix):
    """2-D 相似変換 ``(2,2)`` → ``(角度[度], 倍率)``。:func:`rot_scale_to_matrix` の逆。

    倍率は列ノルム、角度は ``atan2(m[1,0], m[0,0])``。
    せん断を含む一般の (2,2) を渡しても例外は出ない(相似成分だけを読む)ので、
    ``residual`` が要るときは呼び出し側で ``m - rot_scale_to_matrix(...)`` を取ること。

    Args:
        matrix: (2, 2)。
    Returns:
        2-tuple の float ``(angle_deg, scale)``。
    Raises:
        ValueError: (2,2) でない / 退化(倍率 0)/ 非有限。
    """
    m = _arr(matrix, "matrix")
    if m.shape != (2, 2):
        raise ValueError(f"matrix: must be (2, 2); got {m.shape}")
    sc = float(np.hypot(m[0, 0], m[1, 0]))
    if sc == 0.0:
        raise ValueError("matrix: first column is zero — no similarity scale is defined")
    return (float(np.degrees(np.arctan2(m[1, 0], m[0, 0]))), sc)


def shift_to_vector(shift):
    """整数シフト ``(dz, dy, dx)`` → ``vector (3,)``。``shift`` の出口(**可逆**)。

    ``match_phase_3d`` は整数 3-tuple を返す。``vector`` へ載せると
    ``points`` 語彙へ繋がる(``vector -> points`` の既存 op がある)。

    Args:
        shift: 長さ 3 の整数列 (dz, dy, dx)。
    Returns:
        (3,) float64。
    Raises:
        ValueError: 長さが 3 でない / 非有限。
    """
    a = _arr(shift, "shift")
    if a.shape != (3,):
        raise ValueError(f"shift: must be a length-3 (dz, dy, dx); got {a.shape}")
    return a.astype(np.float64)


def vector_to_shift(vector):
    """``vector (3,)`` → 整数シフト ``(dz, dy, dx)``。:func:`shift_to_vector` の逆向き。

    **不可逆**(最近接整数へ丸める)。落ちる量は丸め残差そのもので、
    ``|v - round(v)| <= 0.5`` が各軸の上界。整数を渡した往復だけが bit 一致する。

    Args:
        vector: (3,)。
    Returns:
        3-tuple の int。
    Raises:
        ValueError: (3,) でない / 非有限。
    """
    a = _arr(vector, "vector")
    if a.shape != (3,):
        raise ValueError(f"vector: must be (3,); got {a.shape}")
    r = np.rint(a).astype(np.int64)
    return (int(r[0]), int(r[1]), int(r[2]))


def cscalar_to_polar(cscalar):
    """複素スカラ → 極形式 ``pairs (1,2) = [|z|, arg z[度]]``。``cscalar`` の出口。

    ``cplx_contour_integral`` / ``cplx_cauchy_value`` が返す複素スカラは、
    ``measurement``(実スカラのみ)へ混ぜると下流が生 TypeError で落ちるので
    型が分かれている。極形式の対にすると 1-D 語彙へ渡せる。

    **角度は度**。:func:`polar_to_cscalar` と往復して実測 max|Δ| = 8.9e-16。

    Args:
        cscalar: complex(または複素 0-d 配列)。
    Returns:
        (1, 2) float64。
    Raises:
        ValueError: 複素スカラでない / 非有限。
    """
    z = np.asarray(cscalar)
    if z.shape != () or z.dtype.kind not in "cfi":
        raise ValueError(f"cscalar: must be a complex scalar; got shape {z.shape} "
                         f"dtype {z.dtype}")
    zc = complex(z)
    if not (np.isfinite(zc.real) and np.isfinite(zc.imag)):
        raise ValueError(f"cscalar: non-finite value {zc}")
    return np.array([[abs(zc), np.degrees(np.arctan2(zc.imag, zc.real))]])


def polar_to_cscalar(pairs):
    """極形式 ``pairs (1,2) = [r, theta[度]]`` → 複素スカラ。:func:`cscalar_to_polar` の逆。

    Args:
        pairs: (1, 2)。r >= 0。
    Returns:
        complex。
    Raises:
        ValueError: 形状が (1,2) でない / r < 0 / 非有限。
    """
    p = _n2(pairs, "pairs")
    if p.shape[0] != 1:
        raise ValueError(f"pairs: polar form of one complex scalar must be (1, 2); got {p.shape}")
    r, th = float(p[0, 0]), float(p[0, 1])
    if r < 0.0:
        raise ValueError(f"pairs: modulus must be >= 0; got {r}")
    t = np.radians(th)
    return complex(r * np.cos(t), r * np.sin(t))


def countrate_to_counts(countrate, gate_s=1.0e-3):
    """計数レート ``[Hz]`` → 計数 ``counts``。``countrate`` の出口(**可逆**)。

    **単位が変換の全内容**: ``[1/s] * [s] = [1]``。``gate_s`` は積算窓の秒数で、
    既定 1 ms。``counts`` は「時間 bin ごとの光子数」の型なので、レート列を
    そのまま counts と名乗らせると**桁が 7 つずれたまま黙って通る**
    (``TYPE_CHECKS`` はどちらも「非負の 1-D」としか見ていない)。

    :func:`counts_to_countrate` と往復して実測 max|Δ| = 9.3e-10(値域が 1e3-1e7 Hz なので
    **相対** 1e-16 = 倍精度の丸め 1 単位ぶん。絶対値だけ見ると大きく見えるので、
    レートのように桁が広い量は相対で言う)。

    ★**2 度掛けても例外は出ない**。``TYPE_TO_SORT`` が ``countrate`` を ``counts`` に
    畳んでいるので、出口が入口にそのまま繋がる。実測(2026-09-08、1,200 Hz を
    gate 1 ms で): 1 回で 1.2000 counts、もう 1 回通すと 0.0012 counts ——
    **1,000 倍の取り違えが、負の値も NaN も出さずに通る**。値だけを見て
    「レートか計数か」を判定する方法は無いので、この 1 件は検査でなく
    **呼ぶ側の規律**で守るしかない(繋いだ経路を書き残すこと)。

    Args:
        countrate: (N,) の非負レート [Hz]。
        gate_s: 積算窓 [s]。> 0。
    Returns:
        (N,) float64 の非負計数。
    Raises:
        ValueError: 負のレート / gate_s <= 0 / 形状不正 / 非有限。
    """
    a = _arr(countrate, "countrate")
    if a.ndim != 1:
        raise ValueError(f"countrate: must be 1-D; got {a.shape}")
    if np.any(a < 0.0):
        raise ValueError(f"countrate: must be non-negative [Hz]; got min {float(a.min())}")
    g = float(gate_s)
    if g <= 0.0:
        raise ValueError(f"gate_s: integration window must be > 0 s; got {g}")
    return a * g


def counts_to_countrate(counts, gate_s=1.0e-3):
    """計数 → 計数レート ``[Hz]``。:func:`countrate_to_counts` の逆。

    Args:
        counts: (N,) の非負計数。
        gate_s: 積算窓 [s]。> 0。
    Returns:
        (N,) float64 の非負レート [Hz]。
    Raises:
        ValueError: 負の計数 / gate_s <= 0 / 形状不正 / 非有限。
    """
    a = _arr(counts, "counts")
    if a.ndim != 1:
        raise ValueError(f"counts: must be 1-D; got {a.shape}")
    if np.any(a < 0.0):
        raise ValueError(f"counts: must be non-negative; got min {float(a.min())}")
    g = float(gate_s)
    if g <= 0.0:
        raise ValueError(f"gate_s: integration window must be > 0 s; got {g}")
    return a / g


def deformation_to_points(deformation):
    """TPS 変形 ``deformation`` → 制御点 ``points (N,3)``。``deformation`` の出口。

    ``tps_fit`` が返す dict の ``ctrl`` を取り出す。「この歪みはどこに
    固定されているか」を点群語彙で見るためのもので、**一方向**
    (制御点だけからは重み ``w`` とアフィン項 ``a`` は復元できない)。

    Args:
        deformation: ``ctrl`` を持つ dict(``tps_fit`` の返り)。
    Returns:
        (N, 3) float64。
    Raises:
        ValueError: dict でない / ``ctrl`` が無い / 形状不正 / 非有限。
    """
    if not isinstance(deformation, dict):
        raise ValueError(f"deformation: must be a dict from `tps_fit`; "
                         f"got {type(deformation).__name__}")
    if "ctrl" not in deformation:
        raise ValueError(f"deformation: missing 'ctrl' (keys: {sorted(deformation)})")
    return _n3(deformation["ctrl"], "deformation['ctrl']").copy()


# --------------------------------------------------------------------------- #
# 型のつながりを閉じる変換(2026-11-03)                                          #
#                                                                               #
# ``tools/type_connectivity.py`` が数えた「作られるのに誰も受けない型」と       #
# 「受ける op はあるのに誰も作らない型」を、実物を確かめてから 1 つずつ閉じる。 #
# どれも**既存の型語彙だけ**を使う(新しい型名は 1 つも足していない)。         #
# --------------------------------------------------------------------------- #
def _host(x, what):
    """torch.Tensor でも numpy でも、ホストの float64 ndarray にする(torch は import しない)。"""
    if hasattr(x, "detach") and hasattr(x, "cpu"):
        x = x.detach().cpu().numpy()
    return _arr(x, what)


#: ``sobel3d`` の利得(微分 [-1,0,1] の 2 × 他 2 軸の平滑 [1,2,1] の 4 × 4)。
#: ``sobel3d`` の docstring が「真の勾配の 32 倍」と書いているのと同じ数。
SOBEL3D_GAIN = 32.0


def _gradient_field(gradient):
    """``gradient`` 型の 2 つの形を、真の勾配 ``(3, D, H, W)``(成分 = d/d軸0, d/d軸1, d/d軸2)に揃える。

    ``gradient`` 型を産む op は 2 つあり、**形が違う**(実測 2026-11-03):

    * ``gradient3d`` → ``(gmag (D,H,W), gvec (D,H,W,3))`` の numpy 2-tuple。利得 1。
    * ``sobel3d`` → ``(gz, gy, gx)`` の torch tensor 3 本、各 ``(1,1,D,H,W)``。**利得 32**。

    取り違えると大きさが 32 倍ずれるのに例外は出ないので、ここで形から見分けて
    ``sobel3d`` の形は :data:`SOBEL3D_GAIN` で割る。どちらの形でもなければ拒否する。
    """
    if isinstance(gradient, (tuple, list)) and len(gradient) == 2:
        gvec = _host(gradient[1], "gradient[1] (gvec)")
        if gvec.ndim != 4 or gvec.shape[-1] != 3:
            raise ValueError(f"gradient: the gradient3d form is (gmag, gvec) with gvec (D,H,W,3); "
                             f"got gvec {gvec.shape}")
        return np.moveaxis(gvec.astype(np.float64), -1, 0)
    if isinstance(gradient, (tuple, list)) and len(gradient) == 3:
        comps = []
        for i, g in enumerate(gradient):
            a = _host(g, f"gradient[{i}]")
            a = a.reshape(a.shape[-3:]) if a.ndim == 5 and a.shape[:2] == (1, 1) else a
            if a.ndim != 3:
                raise ValueError(f"gradient: the sobel3d form is 3 arrays of (D,H,W) or (1,1,D,H,W); "
                                 f"got component {i} with shape {np.shape(g)}")
            comps.append(a.astype(np.float64))
        if not (comps[0].shape == comps[1].shape == comps[2].shape):
            raise ValueError(f"gradient: components differ in shape {[c.shape for c in comps]}")
        return np.stack(comps) / SOBEL3D_GAIN
    raise ValueError("gradient: expected the gradient3d form (gmag, gvec) or the sobel3d form "
                     f"(gz, gy, gx); got {type(gradient).__name__}"
                     + (f" of length {len(gradient)}" if isinstance(gradient, (tuple, list)) else ""))


def gradient_magnitude(gradient):
    """3-D 勾配 ``gradient`` → 勾配の大きさの体積 ``voxel``。``gradient`` 型の出口。

    ``|∇I| = sqrt(gz² + gy² + gx²)``。``gradient3d`` の形 ``(gmag, gvec)`` は ``gvec`` から
    計算し直す(``gmag`` を信じて素通しにしない —— 渡された対が食い違っていても気づけないため)。
    ``sobel3d`` の形 ``(gz, gy, gx)`` は利得 32 を割ってから計算するので、**どちらの産み手から
    来ても真の勾配の大きさ**(1 voxel あたりの濃度変化)になる。

    **一方向**(向き 2 自由度を捨てる)。向きを残すなら :func:`gradient_coherence` や
    ``sobel3d`` の成分そのもの。

    ★外から来た勾配(微分可能レンダラの出力など)は ``(gmag, gvec)`` の形で渡すこと。
    3 本の形は ``sobel3d`` の利得 32 として割るので、利得 1 の 3 本を渡すと 1/32 に出る
    (形だけでは利得を見分けられない。型を分けるかは ``docs/TYPE_CONNECTIVITY.md`` の案)。

    Args:
        gradient: ``gradient3d`` の ``(gmag, gvec)`` か ``sobel3d`` の ``(gz, gy, gx)``。
    Returns:
        (D, H, W) float64。
    Raises:
        ValueError: どちらの形でもない / 非有限 / 空。
    """
    g = _gradient_field(gradient)
    return np.sqrt(np.sum(g * g, axis=0))


def gradient_coherence(gradient, sigma=1.5, eps=1e-12):
    """3-D 勾配 → 構造テンソルの**面らしさ**(コヒーレンス)``voxel``、値域 [0, 1]。

    各 voxel で勾配の外積 ``g gᵀ`` をガウス ``sigma`` で平均した構造テンソル ``J`` を作り、
    固有値 ``μ1 ≥ μ2 ≥ μ3 ≥ 0`` から ``(μ1 − μ2) / (μ1 + μ2 + μ3 + eps)`` を返す
    (Westin の線形異方性を構造テンソルに当てたもの。Bigün & Granlund 1987、Westin 2002)。
    近傍の勾配が 1 方向にそろう(層・板・界面)と 1 に近づき、向きがばらばら(等方的な
    ざらつき・塊)だと 0 に近づく。**勾配の大きさには依らない**(比なので)。
    平らで勾配の無い所は分母が ``eps`` だけになり 0 を返す。

    ``gradient`` 型を一級の入力として受けるので、勾配の出どころ(``gradient3d`` /
    ``sobel3d`` / 外部の微分可能レンダラ)を問わない。

    Args:
        gradient: ``gradient3d`` の ``(gmag, gvec)`` か ``sobel3d`` の ``(gz, gy, gx)``。
        sigma: 構造テンソルを平均するガウスの標準偏差 [voxel]。> 0。
        eps: 分母の下駄(勾配ゼロの所で 0 を返すため)。> 0。
    Returns:
        (D, H, W) float64、[0, 1]。
    Raises:
        ValueError: 形が違う / 非有限 / sigma <= 0 / eps <= 0。
    """
    from scipy.ndimage import gaussian_filter
    if not (np.isfinite(sigma) and sigma > 0):
        raise ValueError(f"sigma: must be a finite number > 0; got {sigma}")
    if not (np.isfinite(eps) and eps > 0):
        raise ValueError(f"eps: must be a finite number > 0; got {eps}")
    g = _gradient_field(gradient)
    J = np.empty(g.shape[1:] + (3, 3), dtype=np.float64)
    for i in range(3):
        for j in range(i, 3):
            s = gaussian_filter(g[i] * g[j], sigma=float(sigma), mode="nearest")
            J[..., i, j] = s
            J[..., j, i] = s
    mu = np.linalg.eigvalsh(J)[..., ::-1]          # 降順
    mu = np.clip(mu, 0.0, None)                    # 丸めで出る微小な負を 0 に
    return np.clip((mu[..., 0] - mu[..., 1]) / (mu.sum(axis=-1) + float(eps)), 0.0, 1.0)


def _hessian_eigs(hessian):
    """``hessian3d`` の 6 成分 (zz, yy, xx, zy, zx, yx) → 固有値 (D,H,W,3)、``|λ|`` の昇順。"""
    if not isinstance(hessian, (tuple, list)) or len(hessian) != 6:
        raise ValueError("hessian: expected the hessian3d form, 6 arrays (zz, yy, xx, zy, zx, yx); "
                         f"got {type(hessian).__name__}"
                         + (f" of length {len(hessian)}" if isinstance(hessian, (tuple, list)) else ""))
    c = [_host(h, f"hessian[{i}]").astype(np.float64) for i, h in enumerate(hessian)]
    if any(x.ndim != 3 or x.shape != c[0].shape for x in c):
        raise ValueError(f"hessian: the 6 components must share one (D,H,W) shape; "
                         f"got {[x.shape for x in c]}")
    zz, yy, xx, zy, zx, yx = c
    H = np.stack([np.stack([zz, zy, zx], -1),
                  np.stack([zy, yy, yx], -1),
                  np.stack([zx, yx, xx], -1)], -2)
    lam = np.linalg.eigvalsh(H)
    order = np.argsort(np.abs(lam), axis=-1)
    return np.take_along_axis(lam, order, axis=-1)


def hessian_determinant(hessian):
    """3-D Hessian ``hessian`` → 行列式 ``det H`` の体積 ``voxel``(符号つき)。``hessian`` 型の出口。

    ``det H = λ1 λ2 λ3``(固有値の積)。球状の明るい塊の中心では 3 つとも負なので負、
    暗い塊では正、管や板(固有値の 1 つ以上が 0 に近い)では 0 に近い ——
    Determinant-of-Hessian の塊検出(Lindeberg 1998)の 3-D 版。単位は ``hessian3d``
    と同じ 1/voxel² の 3 乗(正規化しない。**値の比較は同じ尺度の中だけ**で)。

    固有値を経由せず成分から直接 ``zz(yy·xx − yx²) − zy(zy·xx − yx·zx) + zx(zy·yx − yy·zx)``
    で計算する(固有値分解の丸めを入れないため)。

    Args:
        hessian: ``hessian3d`` の 6 成分 (zz, yy, xx, zy, zx, yx)。torch でも numpy でもよい。
    Returns:
        (D, H, W) float64。
    Raises:
        ValueError: 6 成分でない / 形がそろわない / 非有限 / 空。
    """
    if not isinstance(hessian, (tuple, list)) or len(hessian) != 6:
        raise ValueError("hessian: expected the hessian3d form, 6 arrays (zz, yy, xx, zy, zx, yx); "
                         f"got {type(hessian).__name__}"
                         + (f" of length {len(hessian)}" if isinstance(hessian, (tuple, list)) else ""))
    c = [_host(h, f"hessian[{i}]").astype(np.float64) for i, h in enumerate(hessian)]
    if any(x.ndim != 3 or x.shape != c[0].shape for x in c):
        raise ValueError(f"hessian: the 6 components must share one (D,H,W) shape; "
                         f"got {[x.shape for x in c]}")
    zz, yy, xx, zy, zx, yx = c
    return zz * (yy * xx - yx * yx) - zy * (zy * xx - yx * zx) + zx * (zy * yx - yy * zx)


def hessian_vesselness(hessian, alpha=0.5, beta=0.5, c=None, black_ridges=False):
    """3-D Hessian → Frangi の管らしさ(vesselness)``voxel``、値域 [0, 1]。

    固有値を ``|λ1| ≤ |λ2| ≤ |λ3|`` に並べ、``Ra = |λ2|/|λ3|``(板と管を分ける)、
    ``Rb = |λ1|/sqrt(|λ2 λ3|)``(塊を除く)、``S = sqrt(λ1²+λ2²+λ3²)``(背景の雑音を除く)から

        V = (1 − exp(−Ra²/2α²)) · exp(−Rb²/2β²) · (1 − exp(−S²/2c²))

    を返す(Frangi et al. 1998, MICCAI)。明るい管(``black_ridges=False``)では
    ``λ2 > 0`` か ``λ3 > 0`` の voxel を 0 にする(暗い管なら符号を逆に)。
    ``c`` の既定は Frangi の勧めどおり ``S`` の最大値の半分。

    ``vol_frangi`` は体積から Hessian を**自分で作る**(尺度ごとに)のに対し、こちらは
    ``hessian`` 型を受ける —— Hessian の出どころ(``hessian3d`` / 外部の微分)を選べ、
    同じ Hessian から :func:`hessian_determinant` など複数の量を引き出せる。
    1 尺度だけ(多尺度の最大は呼ぶ側で取る)。

    Args:
        hessian: ``hessian3d`` の 6 成分 (zz, yy, xx, zy, zx, yx)。
        alpha, beta: Frangi の感度(既定 0.5 / 0.5)。> 0。
        c: 構造の強さの感度。None で ``max(S)/2``。> 0。全面 0 の Hessian では 0 を返す。
        black_ridges: True で暗い管(背景より暗い)を拾う。
    Returns:
        (D, H, W) float64、[0, 1]。
    Raises:
        ValueError: 6 成分でない / 非有限 / alpha・beta・c が正でない。
    """
    for nm, v in (("alpha", alpha), ("beta", beta)):
        if not (np.isfinite(v) and v > 0):
            raise ValueError(f"{nm}: must be a finite number > 0; got {v}")
    lam = _hessian_eigs(hessian)
    l1, l2, l3 = lam[..., 0], lam[..., 1], lam[..., 2]
    a1, a2, a3 = np.abs(l1), np.abs(l2), np.abs(l3)
    S = np.sqrt(l1 * l1 + l2 * l2 + l3 * l3)
    if c is None:
        smax = float(S.max())
        if smax == 0.0:
            return np.zeros(S.shape, dtype=np.float64)
        c = 0.5 * smax
    if not (np.isfinite(c) and c > 0):
        raise ValueError(f"c: must be a finite number > 0 (or None); got {c}")
    tiny = np.finfo(np.float64).tiny
    Ra = a2 / np.maximum(a3, tiny)
    Rb = a1 / np.maximum(np.sqrt(a2 * a3), tiny)
    V = ((1.0 - np.exp(-(Ra * Ra) / (2.0 * alpha * alpha)))
         * np.exp(-(Rb * Rb) / (2.0 * beta * beta))
         * (1.0 - np.exp(-(S * S) / (2.0 * float(c) * float(c)))))
    wrong = (l2 < 0) | (l3 < 0) if black_ridges else (l2 > 0) | (l3 > 0)
    V[wrong] = 0.0
    return np.clip(V, 0.0, 1.0)


_FRAME_AXES = {"tangent": 0, "normal": 1, "binormal": 2}


def frame_axis(frame, axis="tangent"):
    """Frenet 標構 ``frame`` → 1 本の軸の単位ベクトル列 ``normals (N,3)``。``frame`` 型の出口。

    ``frenet_frame`` の返り ``(T, N, B)``(各 (N,3))から ``axis`` の 1 本を取り出す:
    ``"tangent"`` = 接線 T、``"normal"`` = 主法線 N、``"binormal"`` = 陪法線 B。
    取り出した列は点ごとの単位ベクトルなので ``normals`` 型に載る
    (``normals_to_angles`` / ``normals_to_egi`` などがそのまま掛かる)。

    ``frenet_frame`` は直線区間で N・B がほぼゼロベクトルになる(向き不定)。ここでは
    **長さ 0.5 未満の行を拒否**する(黙って単位ベクトルのふりをさせない)。
    直線を含む曲線で N/B を使うなら、先に ``fit_spline_curve`` で滑らかにするか接線だけを使う。

    Args:
        frame: ``(T, N, B)`` の 3-tuple、各 (N,3)。
        axis: ``"tangent"`` / ``"normal"`` / ``"binormal"``。
    Returns:
        (N, 3) float64、各行は単位長(``frenet_frame`` が正規化した値そのまま)。
    Raises:
        ValueError: 3-tuple でない / 形がそろわない / axis が不正 / 長さ 0.5 未満の行がある。
    """
    if axis not in _FRAME_AXES:
        raise ValueError(f"axis: must be one of {sorted(_FRAME_AXES)}; got {axis!r}")
    if not isinstance(frame, (tuple, list)) or len(frame) != 3:
        raise ValueError("frame: expected the frenet_frame form (T, N, B); "
                         f"got {type(frame).__name__}"
                         + (f" of length {len(frame)}" if isinstance(frame, (tuple, list)) else ""))
    parts = [_n3(f, f"frame[{i}]") for i, f in enumerate(frame)]
    if not (parts[0].shape == parts[1].shape == parts[2].shape):
        raise ValueError(f"frame: T, N, B must share one shape; got {[p.shape for p in parts]}")
    v = parts[_FRAME_AXES[axis]].astype(np.float64)
    n = np.linalg.norm(v, axis=1)
    bad = np.flatnonzero(n < 0.5)
    if bad.size:
        raise ValueError(f"frame_axis: {bad.size} row(s) of the {axis} are not unit vectors "
                         f"(first at index {int(bad[0])}, length {float(n[bad[0]]):.3g}) — "
                         f"the Frenet {axis} is undefined on straight stretches")
    return v.copy()


_GRAPH_WEIGHTS = ("inverse_distance", "distance", "binary")


def knn_graph_to_conn_graph(graph, weight="inverse_distance", symmetric=True):
    """k 近傍グラフ ``graph`` → 重みつき隣接行列 ``conn_graph (n, n)``。``graph`` 型の出口。

    ``knn_graph`` の返り ``(idx (n,k) int, dist (n,k) float)`` を、``conn_graph`` 族
    (``graph_components`` / ``graph_laplacian_spectrum`` / ``graph_layout_spectral`` …)が
    受ける n×n の ``W[i, j]`` = i → j の重みにする。``weight``:

    * ``"inverse_distance"`` —— ``1 / dist``(近いほど強い。距離 0 の重複点は拒否する)
    * ``"distance"`` —— ``dist`` そのもの(経路長として使う側向け)
    * ``"binary"`` —— 1

    ``symmetric=True`` で ``W = max(W, Wᵀ)``(k 近傍は片想いがあるので、無向グラフとして
    扱うなら対称化する)。対角は 0(``knn_graph`` は自分を除いている)。
    n は ``conngraph.MAX_NODES``(4096)まで —— 密行列なので、それを超える点群は
    先に ``farthest_point_sampling`` などで間引く。

    Args:
        graph: ``(idx, dist)`` の 2-tuple(``knn_graph`` の返り)。
        weight: ``"inverse_distance"`` / ``"distance"`` / ``"binary"``。
        symmetric: True で対称化。
    Returns:
        (n, n) float64。
    Raises:
        ValueError: 2-tuple でない / 形が違う / 添字が範囲外 / 自己ループ / n が上限超え /
            ``inverse_distance`` で距離 0 / weight が不正。
    """
    import conngraph
    if weight not in _GRAPH_WEIGHTS:
        raise ValueError(f"weight: must be one of {list(_GRAPH_WEIGHTS)}; got {weight!r}")
    if not isinstance(graph, (tuple, list)) or len(graph) != 2:
        raise ValueError("graph: expected the knn_graph form (idx, dist); "
                         f"got {type(graph).__name__}"
                         + (f" of length {len(graph)}" if isinstance(graph, (tuple, list)) else ""))
    idx = _arr(graph[0], "graph[0] (idx)", dtype=np.int64)
    dist = _arr(graph[1], "graph[1] (dist)")
    if idx.ndim != 2 or idx.shape != dist.shape:
        raise ValueError(f"graph: idx and dist must both be (n, k); got {idx.shape} and {dist.shape}")
    n = idx.shape[0]
    if n > conngraph.MAX_NODES:
        raise ValueError(f"graph: n = {n} nodes exceeds conngraph.MAX_NODES = {conngraph.MAX_NODES} "
                         f"(a dense n×n matrix); subsample the points first")
    if idx.size and (idx.min() < 0 or idx.max() >= n):
        raise ValueError(f"graph: neighbour indices must lie in [0, {n - 1}]; "
                         f"got [{int(idx.min())}, {int(idx.max())}]")
    rows = np.repeat(np.arange(n), idx.shape[1])
    cols = idx.ravel()
    if np.any(rows == cols):
        raise ValueError("graph: a node lists itself as a neighbour (knn_graph excludes self)")
    if np.any(dist < 0):
        raise ValueError("graph: distances must be >= 0")
    if weight == "inverse_distance":
        if np.any(dist == 0):
            raise ValueError("graph: zero distance (duplicate points) cannot be inverted; "
                             "use weight='binary' or drop duplicate points first")
        w = 1.0 / dist.ravel()
    elif weight == "distance":
        w = dist.ravel().astype(np.float64)
    else:
        w = np.ones(rows.size, dtype=np.float64)
    W = np.zeros((n, n), dtype=np.float64)
    W[rows, cols] = w
    if symmetric:
        W = np.maximum(W, W.T)
    return W


def pointmap_to_points(pointmap, drop_nonpositive_z=False):
    """格子整列の 3-D 点 ``pointmap (H,W,3)`` → 点群 ``points (N,3)``。``pointmap`` 型の出口。

    行優先(row-major)に並べ直し、**非有限の行は捨てる**(``pointmap`` では NaN が「その
    画素は無効」の印なので、ここでは拒否せず落とす)。``drop_nonpositive_z=True`` は
    ``z <= 0`` の行も捨てる —— ``depth_to_organized_points`` のカメラ座標の pointmap は
    無効深度 0 が原点に集まるので、その場合に使う(``depth_to_points`` と同じ規約になり、
    同じ内部行列なら**同じ点が同じ順に**出る)。地心座標(``dem_geocentric_grid``)では
    z が負になりうるので既定は False。列の意味(x, y, z)は入力のまま変えない。

    Args:
        pointmap: (H, W, 3)。
        drop_nonpositive_z: True で z <= 0 の行も捨てる。
    Returns:
        (N, 3) float64。
    Raises:
        ValueError: (H, W, 3) でない / 空 / 有効な点が 1 つも残らない。
    """
    try:
        p = np.asarray(pointmap, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"pointmap: cannot be read as a numeric array ({exc})") from exc
    if p.ndim != 3 or p.shape[2] != 3:
        raise ValueError(f"pointmap: must be (H, W, 3); got {p.shape}")
    if p.size == 0:
        raise ValueError("pointmap: empty array is not a valid representation")
    flat = p.reshape(-1, 3)
    keep = np.all(np.isfinite(flat), axis=1)
    if drop_nonpositive_z:
        keep &= flat[:, 2] > 0
    if not np.any(keep):
        raise ValueError(f"pointmap: no valid point remains out of {flat.shape[0]} "
                         f"(non-finite{' or z <= 0' if drop_nonpositive_z else ''})")
    return flat[keep].copy()


def match_component(match, index=0):
    """``match`` 型(1-D の結果ベクトル)→ その 1 成分の ``measurement``。``match`` 型の出口。

    2-D レジストリの ``match`` 型は「1 スカラーでは表せない複数の値」を 1 本のベクトルで運ぶ:
    ``area_center`` = (面積 [px], 重心の行 [px], 重心の列 [px])、``ncc_locate`` /
    ``shape_locate`` = (相関値, 行, 列)、``eccentricity`` = (Anisometry, Bulkiness,
    StructureFactor) など。HALCON でも ``area_center`` の Row だけを次の処理に渡すように、
    **成分を名指しで 1 つ取り出す**のがこの型の自然な出口。どの成分が何かは産んだ op の
    docstring が決めている(ここでは解釈しない)。

    Args:
        match: 1-D の有限な数値列(長さ >= 1)。0-D のスカラーは長さ 1 として受ける。
        index: 取り出す成分の番号(0 始まり)。負の番号は使えない(取り違えを防ぐため)。
    Returns:
        float。
    Raises:
        ValueError: 1-D でない / 非有限 / 空 / index が範囲外か整数でない。
    """
    a = np.atleast_1d(_arr(match, "match"))
    if a.ndim != 1:
        raise ValueError(f"match: must be a 1-D result vector; got shape {a.shape}")
    if isinstance(index, bool) or not isinstance(index, (int, np.integer)):
        raise ValueError(f"index: must be an int; got {type(index).__name__}")
    if not 0 <= int(index) < a.size:
        raise ValueError(f"index: must be within [0, {a.size - 1}]; got {index}")
    return float(a[int(index)])


def indices_to_positions(indices, spacing=1.0, origin=0.0):
    """添字 ``indices`` → 事象の位置 ``positions``(物理単位)。``positions`` 型の入口。

    ``x = origin + spacing * i``。``find_peaks`` / ``zero_crossings_funct_1d`` などが返す
    **標本番号**を、``point_spectrum`` が受ける**位置の列**(欠陥が流れ方向のどこにあったか、
    いつ数えたか)にする。``positions`` を ``signal`` と分けてあるのは、等間隔標本の列を
    事象の位置として(またはその逆に)渡すと、例外なしに別物のスペクトルが出るため
    (``point_spectrum`` の docstring)。順序は入力のまま(並べ替えない)。

    空の添字は ValueError(この repo の空入力の方針 A: 黙って空を返さず、何が空かを名指しで拒否)。

    Args:
        indices: 1-D の整数(整数値の float も可。非整数・非有限・空は拒否)。
        spacing: 標本間隔(位置の単位 / 標本)。有限で 0 でないこと。
        origin: 添字 0 の位置。有限。
    Returns:
        (k,) float64。
    Raises:
        ValueError: 1-D でない / 整数でない / 非有限 / 空 / spacing が 0 か非有限。
    """
    if not (np.isfinite(spacing) and spacing != 0):
        raise ValueError(f"spacing: must be finite and non-zero; got {spacing}")
    if not np.isfinite(origin):
        raise ValueError(f"origin: must be finite; got {origin}")
    i = np.atleast_1d(_arr(indices, "indices", dtype=np.int64))
    if i.ndim != 1:
        raise ValueError(f"indices: must be 1-D; got shape {i.shape}")
    if not (np.isfinite(spacing) and spacing != 0):
        raise ValueError(f"spacing: must be finite and non-zero; got {spacing}")
    if not np.isfinite(origin):
        raise ValueError(f"origin: must be finite; got {origin}")
    return float(origin) + float(spacing) * i.astype(np.float64)


def synapse_table_from_table(table, pre="pre", post="post", count=None):
    """表 ``table``(列名 → 配列)→ シナプス表 ``synapse_table (m, 3)``。``synapse_table`` 型の入口。

    コネクトームの公開データは CSV(``table_read_csv`` で ``table`` になる)で来るので、
    その 3 列を ``(pre_id, post_id, count)`` の m×3 に詰め直す。``count`` を省くと 1
    (シナプス 1 個 = 1 行の表)。``synapse_table`` を ``points`` と分けてある理由
    (形が同じ (N,3) で、点群を渡すと座標が id として読まれる)を守るため、**id が
    0 以上の整数であることをここで確かめる**(``graph_from_synapses`` と同じ規約)。

    ``table`` は 2 つの形を受ける: 列名 → 配列の dict そのものと、``table_read_csv`` の返り
    ``{"columns": {列名: 配列}, "units": ..., "meta": ...}``(列は ``columns`` から読む)。

    Args:
        table: 列名 → 1-D 配列の dict、または ``table_read_csv`` の返り。
        pre, post: 前・後ニューロン id の列名。
        count: シナプス数の列名(None で全行 1)。
    Returns:
        (m, 3) float64。
    Raises:
        ValueError: dict でない / 列が無い / 長さがそろわない / id が 0 以上の整数でない /
            count が負か非有限 / 空。
    """
    if not isinstance(table, dict):
        raise ValueError(f"table: must be a dict of column name -> 1-D array; "
                         f"got {type(table).__name__}")
    if isinstance(table.get("columns"), dict) and pre not in table:
        table = table["columns"]                   # table_read_csv の形
    for col in (pre, post) + ((count,) if count is not None else ()):
        if col not in table:
            raise ValueError(f"table: missing column {col!r} (columns: {sorted(map(str, table))})")
    a = np.ravel(_arr(table[pre], f"table[{pre!r}]"))
    b = np.ravel(_arr(table[post], f"table[{post!r}]"))
    c = (np.ones_like(a, dtype=np.float64) if count is None
         else np.ravel(_arr(table[count], f"table[{count!r}]")))
    if not (a.size == b.size == c.size):
        raise ValueError(f"table: columns differ in length ({a.size}, {b.size}, {c.size})")
    ids = np.concatenate([a, b])
    if np.any(ids < 0) or not np.all(ids == np.round(ids)):
        raise ValueError("table: pre / post ids must be whole numbers >= 0 "
                         "(a point cloud read as synapses would pass silently otherwise)")
    if np.any(c < 0):
        raise ValueError("table: count must be >= 0")
    return np.stack([a, b, c], axis=1).astype(np.float64)


def jones_state(azimuth_deg=0.0, ellipticity_deg=0.0, amplitude=1.0):
    """偏光の向きと楕円率 → Jones ベクトル ``jones``(Ex, Ey)。``jones`` 型の入口。

    方位角 ψ = ``azimuth_deg``、楕円率角 χ = ``ellipticity_deg``(|χ| <= 45 度)で

        E = A · [cos ψ cos χ + i sin ψ sin χ,  sin ψ cos χ − i cos ψ sin χ]

    を返す。``optics.stokes_from_jones`` の約束(S3 = 2 Im(Ex·conj(Ey)))のもとで
    **Stokes が (A², A² cos2χ cos2ψ, A² cos2χ sin2ψ, A² sin2χ) になる**ように符号を選んである
    (χ = 0 で直線偏光、χ = +45 度で S3 > 0 の円偏光 = ``[1, -i]/√2``)。
    ``jones_apply`` に通す入射光の状態として使う。それまで Jones ベクトルを作る op が無く、
    ``jones_apply`` の第 2 入力と ``stokes_from_jones`` に何も渡せなかった。

    Args:
        azimuth_deg: 偏光楕円の長軸の向き [度](+x から +y へ)。有限。
        ellipticity_deg: 楕円率角 [度]、[-45, 45]。
        amplitude: 振幅 A(>= 0、有限)。強度は A²。
    Returns:
        (2,) complex128。
    Raises:
        ValueError: 非有限 / ellipticity が [-45, 45] の外 / amplitude < 0。
    """
    for nm, v in (("azimuth_deg", azimuth_deg), ("ellipticity_deg", ellipticity_deg),
                  ("amplitude", amplitude)):
        if not np.isfinite(v):
            raise ValueError(f"{nm}: must be finite; got {v}")
    if not -45.0 <= float(ellipticity_deg) <= 45.0:
        raise ValueError(f"ellipticity_deg: must be within [-45, 45]; got {ellipticity_deg}")
    if amplitude < 0:
        raise ValueError(f"amplitude: must be >= 0; got {amplitude}")
    p, c = np.radians(float(azimuth_deg)), np.radians(float(ellipticity_deg))
    return float(amplitude) * np.array(
        [np.cos(p) * np.cos(c) + 1j * np.sin(p) * np.sin(c),
         np.sin(p) * np.cos(c) - 1j * np.cos(p) * np.sin(c)], dtype=np.complex128)


def tokens_to_matrix(tokens):
    """トークン列 ``tokens (T, d)`` → 一般の行列 ``matrix (T, d)``。``tokens`` 型の出口。

    中身は変えない(写しを返す)。``tokens`` を ``matrix`` と分けてあるのは、**入る側**で
    転置した (d, T) が黙って通るのを防ぐため(``opsllmcore`` の docstring)で、出る側は
    一般の行列として扱ってよい —— SVD・条件数・ノルムなど ``matrix`` の op がそのまま掛かる
    (例: 注意の出力の実効次数を ``mat_cond`` で見る)。逆向き(``matrix`` → ``tokens``)は
    軸の順を確かめようがないので作らない。

    Args:
        tokens: (T, d) の有限な実数列。
    Returns:
        (T, d) float64。
    Raises:
        ValueError: 2-D でない / 非有限 / 空。
    """
    t = _arr(tokens, "tokens")
    if t.ndim != 2:
        raise ValueError(f"tokens: must be (T, d); got {t.shape}")
    return t.astype(np.float64, copy=True)


def _table_value(table, key, what):
    """``table`` 型の値から 1 欄を取り出す(dict そのもの / ``table_read_csv`` の ``columns``)。"""
    if not isinstance(table, dict):
        raise ValueError(f"{what}: table must be a dict (column name -> value); got {type(table).__name__}")
    if key not in table and isinstance(table.get("columns"), dict):
        table = table["columns"]                   # table_read_csv の形
    if key not in table:
        raise ValueError(f"{what}: no field {key!r} (fields: {sorted(map(str, table))})")
    return table[key]


def table_field_image2d(table, key):
    """表 ``table`` の 1 欄 → 2-D 画像 ``image2d``。``table`` を返す op から画像を受ける op へのつなぎ。

    ``vx_sobel3x3`` の ``{gx, gy, valid}`` → ``vx_magnitude(gx, gy)``、``flow_from_depth_motion``
    の ``{u, v, ...}`` → ``ttc_from_flow(u, v)`` のように、**dict を返す op の欄を名指しで取り出す**。
    取り出した値が 2-D の有限な数値配列であることを確かめる(型の名前どおりの物しか通さない)。
    bool の欄(``valid`` のような印)は 0/1 の float にする。

    Args:
        table: 欄の名前 → 値の dict(``table_read_csv`` の返りなら ``columns`` から読む)。
        key: 欄の名前。
    Returns:
        (H, W) の配列(dtype はそのまま。bool は float64)。
    Raises:
        ValueError: dict でない / 欄が無い / 2-D でない / 非有限 / 空。
    """
    v = _table_value(table, key, "table_field_image2d")
    a = np.asarray(v)
    if a.dtype == bool:
        a = a.astype(np.float64)
    a = _arr(a, f"table[{key!r}]", dtype=a.dtype if a.dtype.kind in "iuf" else float)
    if a.ndim != 2:
        raise ValueError(f"table_field_image2d: field {key!r} is not 2-D (shape {a.shape})")
    return a.copy()


def table_field_signal(table, key):
    """表 ``table`` の 1 欄 → 1-D 配列 ``signal``。CSV の 1 列や dict の系列を信号の op へ渡す。

    1-D の有限な数値列であることを確かめる((n,1) / (1,n) は 1-D に直す。それ以外の 2-D は拒否)。

    Args:
        table: 欄の名前 → 値の dict(``table_read_csv`` の返りなら ``columns`` から読む)。
        key: 欄の名前。
    Returns:
        (n,) float64。
    Raises:
        ValueError: dict でない / 欄が無い / 1-D に直せない / 非有限 / 空。
    """
    a = _arr(_table_value(table, key, "table_field_signal"), f"table[{key!r}]")
    if a.ndim == 2 and 1 in a.shape:
        a = a.ravel()
    if a.ndim != 1:
        raise ValueError(f"table_field_signal: field {key!r} is not 1-D (shape {a.shape})")
    return a.astype(np.float64, copy=True)


def table_field_matrix(table, key):
    """表 ``table`` の 1 欄 → 一般の行列 ``matrix``。例: ``swt_map`` の ``swt`` 欄 → ``text_candidates``。

    2-D の有限な数値配列であることを確かめる。``swt_map`` の SWT 場のように「線の無い画素」を
    0 で持つ欄はそのまま通る(NaN で持つ欄は拒否される —— 中身の約束は産んだ op の docstring)。

    Args:
        table: 欄の名前 → 値の dict。
        key: 欄の名前。
    Returns:
        2-D float64。
    Raises:
        ValueError: dict でない / 欄が無い / 2-D でない / 非有限 / 空。
    """
    a = _arr(_table_value(table, key, "table_field_matrix"), f"table[{key!r}]")
    if a.ndim != 2:
        raise ValueError(f"table_field_matrix: field {key!r} is not 2-D (shape {a.shape})")
    return a.astype(np.float64, copy=True)


def table_field_measurement(table, key):
    """表 ``table`` の 1 欄 → 数 1 個 ``measurement``。例: ``label_extent`` の ``width``。

    値が要素 1 個の有限な数(スカラーか長さ 1 の配列)であることを確かめる。

    Args:
        table: 欄の名前 → 値の dict。
        key: 欄の名前。
    Returns:
        float。
    Raises:
        ValueError: dict でない / 欄が無い / 要素が 1 個でない / 非有限。
    """
    a = _arr(_table_value(table, key, "table_field_measurement"), f"table[{key!r}]")
    if a.size != 1:
        raise ValueError(f"table_field_measurement: field {key!r} holds {a.size} values, not one")
    return float(a.ravel()[0])


def pairs_peak_x(pairs, x_min=None, x_max=None):
    """対 ``pairs (x, y)`` → y が最大になる x(放物線で標本の間まで補間)``measurement``。

    ``spectrum`` の ``(freqs, magnitude)`` から主周波数、``surface_psd`` の (周波数, PSD) から
    卓越波長の逆数を読む、のように **対の列のピークの位置**を返す。最大の標本と両隣の 3 点に
    放物線を当て、頂点の x を返す(端の標本が最大のときは補間せずその x)。**補間の偏りは
    窓しだい**: 窓を掛けない(矩形)正弦波の振幅スペクトルでは最大 0.25 bin ほど(実測 1 Hz 刻みで
    123.4 Hz → 123.18、123.25 → 123.05、整数と半整数の周波数では 1e-2 bin 以下)。
    細かく要るなら窓を掛けた信号か ``peak_subbin`` を使う。``x_min`` / ``x_max`` で探す範囲を切る ——
    **スペクトルでは DC(x = 0)が最大になりやすい**ので、主周波数を探すなら ``x_min`` を 0 より
    大きくする。y の同点は最初の標本。

    Args:
        pairs: (n, 2) か 2-tuple の (x, y)。x は昇順。
        x_min, x_max: 探す x の範囲(含む)。None で端まで。
    Returns:
        float(ピークの x)。
    Raises:
        ValueError: 対でない / x が昇順でない / 範囲に標本が無い / 非有限。
    """
    p = _n2(pairs, "pairs")
    x, y = p[:, 0], p[:, 1]
    if x.size > 1 and np.any(np.diff(x) <= 0):
        raise ValueError("pairs: x must be strictly increasing")
    keep = np.ones(x.size, dtype=bool)
    if x_min is not None:
        keep &= x >= float(x_min)
    if x_max is not None:
        keep &= x <= float(x_max)
    idx = np.flatnonzero(keep)
    if idx.size == 0:
        raise ValueError(f"pairs_peak_x: no sample within [{x_min}, {x_max}]")
    k = int(idx[np.argmax(y[idx])])
    if k - 1 not in idx or k + 1 not in idx:
        return float(x[k])
    y0, y1, y2 = y[k - 1], y[k], y[k + 1]
    den = y0 - 2.0 * y1 + y2
    if den >= 0:                                   # 平ら・谷: 補間しない
        return float(x[k])
    d = 0.5 * (y0 - y2) / den                      # 標本番号での頂点のずれ、|d| <= 0.5
    step = (x[k + 1] - x[k - 1]) / 2.0
    return float(x[k] + d * step)


def _swap2(keypoints, what):
    a = _n2(keypoints, what)
    return a[:, ::-1].copy()


def keypoints_rowcol_to_uv(keypoints):
    """像面の点 ``(row, col)`` → ``(u, v) = (col, row)``。``keypoints`` 型の 2 つの流儀のつなぎ。

    ``keypoints`` 型には 2 つの軸の約束が同居している(実測): ``calib.project_3d_point`` などは
    **(row, col)**、``project_points`` / ``dlt_pose`` / ``pnp_ransac`` は **(u, v) = (列, 行)**。
    取り違えても例外は出ず、姿勢が鏡に映ったように出る(W2 の実測: t = (−0.565, 0.61, 3.21)
    のはずが (0.1, −0.05, 3.0))。列を入れ替えるだけだが、**どちらの向きかを op 名に書く**ため
    逆向きの :func:`keypoints_uv_to_rowcol` と 2 本に分けてある(中身は同じ入れ替え)。

    Args:
        keypoints: (N, 2) の (row, col)。
    Returns:
        (N, 2) float64 の (u, v)。
    Raises:
        ValueError: (N, 2) でない / 非有限 / 空。
    """
    return _swap2(keypoints, "keypoints")


def keypoints_uv_to_rowcol(keypoints):
    """像面の点 ``(u, v) = (col, row)`` → ``(row, col)``。:func:`keypoints_rowcol_to_uv` の逆向き。

    Args:
        keypoints: (N, 2) の (u, v)。
    Returns:
        (N, 2) float64 の (row, col)。
    Raises:
        ValueError: (N, 2) でない / 非有限 / 空。
    """
    return _swap2(keypoints, "keypoints")


def pose_to_matrix(pose):
    """剛体姿勢 ``pose (R, t)`` → 4×4 の同次変換 ``matrix``。

    ``dlt_pose`` / ``icp_point2point_3d`` / ``fit_rigid`` などは ``(R (3,3), t (3,))`` を返すが、
    ``rotation_translation_error`` などは 4×4 を受ける。``[[R, t], [0, 0, 0, 1]]`` に詰める。
    既に 4×4 の配列が来たら、最下行が (0, 0, 0, 1) であることを確かめて写しを返す。
    R が回転行列であること(``RᵀR = I``、``det R = +1``、公差 1e-6)を確かめる ——
    相似変換や鏡映を黙って剛体として通さない。

    Args:
        pose: ``(R, t)`` の 2-tuple / list、``{"R": .., "t": ..}`` の dict、または 4×4 配列。
    Returns:
        (4, 4) float64。
    Raises:
        ValueError: 形が違う / R が回転行列でない / 非有限。
    """
    if isinstance(pose, dict) and "R" in pose and "t" in pose:
        pose = (pose["R"], pose["t"])
    if isinstance(pose, (tuple, list)) and len(pose) >= 2:
        R_ = _arr(pose[0], "pose[0] (R)")
        t_ = np.ravel(_arr(pose[1], "pose[1] (t)"))
        if R_.shape != (3, 3) or t_.shape != (3,):
            raise ValueError(f"pose: R must be (3,3) and t (3,); got {R_.shape} and {t_.shape}")
        M = np.eye(4)
        M[:3, :3] = R_
        M[:3, 3] = t_
    else:
        M = _arr(pose, "pose")
        if M.shape != (4, 4) or not np.allclose(M[3], [0, 0, 0, 1], atol=1e-12):
            raise ValueError(f"pose: expected (R, t) or a 4x4 homogeneous matrix; got shape {M.shape}")
        M = M.astype(np.float64, copy=True)
    R_ = M[:3, :3]
    if not (np.allclose(R_.T @ R_, np.eye(3), atol=1e-6) and np.linalg.det(R_) > 0):
        raise ValueError("pose: R is not a rotation (R^T R != I or det R <= 0)")
    return M


# --------------------------------------------------------------------------- #
# selftest —— 往復誤差を「数字で」出す                                           #
# --------------------------------------------------------------------------- #
def roundtrip_report(seed=0):
    """全往復ペアの誤差を実測して返す(``list[dict]``)。

    可逆なものは ``max_abs`` を、不可逆なものは「何がどれだけ落ちたか」を
    ``lost`` に文字列で入れる。**数字は必ずここで測る** —— docstring に
    書いてある値もこの関数の出力から写している。

    Args:
        seed: 乱数種(決定的)。
    Returns:
        list of dict(``pair`` / ``kind`` / ``max_abs`` or ``lost``)。
    """
    rng = np.random.default_rng(seed)
    rows = []

    def exact(pair, a, b):
        e = float(np.max(np.abs(np.asarray(a, float) - np.asarray(b, float))))
        rows.append({"pair": pair, "kind": "exact", "max_abs": e})
        return e

    # 1. normals <-> pairs(方向の極座標)
    v = rng.standard_normal((512, 3))
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    exact("normals -> pairs -> normals", v, angles_to_normals(normals_to_angles(v)))

    # 2. curvature <-> pairs(形状指数)。臍点と平面をわざと混ぜる
    k = np.concatenate([rng.standard_normal((200, 2)),
                        np.repeat(rng.standard_normal((20, 1)), 2, axis=1),   # 臍点
                        np.zeros((5, 2))])                                     # 平面
    k = np.stack([k.max(axis=1), k.min(axis=1)], axis=1)
    exact("curvature -> pairs -> curvature", k,
          shape_index_to_curvature(curvature_to_shape_index(k)))

    # 3. descriptor <-> matrix(1-D と 2-D の両方)
    d1 = rng.standard_normal(131)
    d2 = rng.standard_normal((12, 9))
    exact("descriptor(1-D) -> matrix -> descriptor", d1,
          matrix_to_descriptor(descriptor_to_matrix(d1)))
    exact("descriptor(2-D) -> matrix -> descriptor", d2,
          matrix_to_descriptor(descriptor_to_matrix(d2)))

    # 4. keypoints <-> points(軸の入れ替えつき)
    kp = rng.random((256, 2)) * 60.0
    z = rng.random(256) * 4.0
    exact("keypoints(u,v) -> points(z,y,x) -> keypoints", kp,
          points_zyx_to_keypoints_uv(keypoints_uv_to_points(kp, z)))
    pts = keypoints_uv_to_points(kp, z)
    rows.append({"pair": "points(z,y,x) -> keypoints -> points", "kind": "lossy",
                 "lost": f"z 列そのもの(RMS {float(np.sqrt(np.mean(z ** 2))):.4f})"})

    # 5. keypoints <-> image2d(画素格子への量子化)。**融合と量子化を分けて測る**
    #    —— 混ぜると 8 近傍で融合した点の中間位置が誤差に乗り、一様量子化の
    #    理論値 1/sqrt(12) と比較できなくなる(最初に混ぜて測って 0.586 px を
    #    得たが、それは量子化誤差ではなく「量子化 + 融合」だった)。
    from scipy.spatial import cKDTree                       # noqa: PLC0415
    grid = np.stack(np.meshgrid(np.arange(3.0, 62.0, 4.0), np.arange(3.0, 62.0, 4.0),
                                indexing="ij"), -1).reshape(-1, 2)
    kp_sep = grid + rng.uniform(-0.5, 0.5, size=grid.shape)     # 4 px 間隔 = 融合しない
    back_sep = keypoints_from_image2d(keypoints_to_image2d(kp_sep, shape=(64, 64)))
    d_sep, j_sep = cKDTree(back_sep).query(kp_sep, k=1)
    axis_rms = float(np.sqrt(np.mean((back_sep[j_sep] - kp_sep) ** 2)))
    rows.append({"pair": "keypoints -> image2d -> keypoints (離した点)", "kind": "lossy",
                 "lost": f"画素格子への量子化のみ: 軸あたり RMS {axis_rms:.4f} px "
                         f"(一様量子化の理論値 1/sqrt(12) = 0.2887)、"
                         f"2-D 距離 RMS {float(np.sqrt(np.mean(d_sep ** 2))):.4f} px "
                         f"(理論 sqrt(2/12) = 0.4082)、"
                         f"点数 {kp_sep.shape[0]} -> {back_sep.shape[0]}(融合なし)"})
    kp_in = rng.random((60, 2)) * 50.0 + 5.0
    back = keypoints_from_image2d(keypoints_to_image2d(kp_in, shape=(64, 64)))
    dist, _ = cKDTree(back).query(kp_in, k=1)
    rows.append({"pair": "keypoints -> image2d -> keypoints (ランダム配置)", "kind": "lossy",
                 "lost": f"量子化 + 8 近傍の融合 RMS {float(np.sqrt(np.mean(dist ** 2))):.4f} px、"
                         f"点数 {kp_in.shape[0]} -> {back.shape[0]}"})

    # 6. indices <-> labels
    idx = np.unique(rng.integers(0, 200, size=40))
    exact("indices -> labels -> indices", idx, labels_to_indices(indices_to_labels(idx)))
    lab = np.zeros(256, np.int64)
    lab[idx] = 1
    lab2 = indices_to_labels(labels_to_indices(lab))
    rows.append({"pair": "labels -> indices -> labels", "kind": "lossy",
                 "lost": f"末尾の背景 {lab.size - lab2.size} 要素(長さ {lab.size} -> {lab2.size})"})

    # 7. position <-> points
    pos = (3.5, 7.25, 11.125)
    exact("position -> points -> position", pos, points_to_position(position_to_points(pos)))
    cloud = rng.standard_normal((300, 3)) * 2.0 + 5.0
    spread = float(np.sqrt(np.mean(np.sum((cloud - cloud.mean(0)) ** 2, axis=1))))
    rows.append({"pair": "points -> position -> points", "kind": "lossy",
                 "lost": f"重心まわりの広がり RMS {spread:.4f}(N {cloud.shape[0]} -> 1)"})

    # 8. gaussians <-> points
    g = points_to_gaussians(cloud)
    exact("points -> gaussians -> points", cloud, gaussians_to_points(g))
    # 中央に 1 つだけ置いて境界の切り落としを排除する(混ぜると打ち切りの
    # 理論値と比較できない)。刻みを細かくすると中点則の上振れが減っていく
    import math                                             # noqa: PLC0415
    box = math.erf(3.0 / math.sqrt(2.0)) ** 3
    one = {"mu": np.array([[8.0, 8.0, 8.0]]), "sigma": np.array([1.5]), "w": np.array([1.0])}
    masses = []
    for sp in (1.0, 0.5, 0.25, 0.125):
        n = int(round(16.0 / sp))
        masses.append(float(gaussians_to_voxel(one, shape=(n, n, n),
                                               spacing=(sp, sp, sp)).sum()))
    rows.append({"pair": "gaussians -> voxel (質量保存)", "kind": "lossy",
                 "lost": "3σ の**箱**打ち切り理論 "
                         f"erf(3/√2)³ = {box * 100:.3f}%。実測は刻み 1.0/0.5/0.25/0.125 で "
                         + " / ".join(f"{m * 100:.2f}%" for m in masses)
                         + " と単調に収束(中点則の上振れが縮む)"})
    edge = {"mu": np.array([[1.0, 8.0, 8.0]]), "sigma": np.array([1.5]), "w": np.array([1.0])}
    rows.append({"pair": "gaussians -> voxel (境界の切り落とし)", "kind": "lossy",
                 "lost": f"中心を縁から 1 voxel に置くと質量 "
                         f"{float(gaussians_to_voxel(edge, shape=(16, 16, 16)).sum()) * 100:.2f}% "
                         f"(打ち切りより遥かに大きい損失)"})

    # 9. angle <-> matrix / rot_scale <-> matrix / shift <-> vector
    angs = rng.uniform(-179.9, 179.9, size=64)
    exact("angle -> matrix -> angle", angs, [matrix_to_angle(angle_to_matrix(a)) for a in angs])
    rs = np.stack([rng.uniform(-179.9, 179.9, 64), rng.uniform(0.2, 5.0, 64)], axis=1)
    exact("rot_scale -> matrix -> rot_scale", rs,
          [matrix_to_rot_scale(rot_scale_to_matrix(r)) for r in rs])
    sh = rng.integers(-8, 9, size=(32, 3))
    exact("shift -> vector -> shift", sh, [vector_to_shift(shift_to_vector(s)) for s in sh])

    # 10. cscalar <-> pairs
    zs = rng.standard_normal(64) + 1j * rng.standard_normal(64)
    exact("cscalar -> pairs -> cscalar", np.stack([zs.real, zs.imag], 1),
          np.array([[(lambda c: (c.real, c.imag))(polar_to_cscalar(cscalar_to_polar(c)))]
                    for c in zs]).reshape(-1, 2))

    # 11. countrate <-> counts(単位)
    cr = 10.0 ** rng.uniform(3.0, 7.0, size=128)
    exact("countrate -> counts -> countrate", cr,
          counts_to_countrate(countrate_to_counts(cr)))

    # 12. normals -> EGI(方向の binning)
    n_axis = np.array([0.3, 0.4, np.sqrt(1 - 0.25)])
    n_axis /= np.linalg.norm(n_axis)
    cloud_n = n_axis + 0.02 * rng.standard_normal((4000, 3))
    cloud_n /= np.linalg.norm(cloud_n, axis=1, keepdims=True)
    egi = normals_to_egi(cloud_n)
    ei, ai = np.unravel_index(int(np.argmax(egi)), egi.shape)
    az_c = (ai + 0.5) / egi.shape[1] * 360.0 - 180.0
    el_c = np.degrees(np.arcsin((ei + 0.5) / egi.shape[0] * 2.0 - 1.0))
    peak = angles_to_normals(np.array([[az_c, el_c]]))[0]
    rows.append({"pair": "normals -> EGI (方向の量子化)", "kind": "lossy",
                 "lost": f"最頻 bin と真の向きの角度差 "
                         f"{float(np.degrees(np.arccos(np.clip(peak @ n_axis, -1, 1)))):.3f} 度 "
                         f"(bin 幅 {360.0 / egi.shape[1]:.1f} 度)"})

    # 13. voxel -> score -> position(閉形式の真値: 既知の巡回シフト)
    n = 24
    zz, yy, xx = np.mgrid[0:n, 0:n, 0:n]
    base = np.exp(-(((zz - 11.0) ** 2 + (yy - 13.0) ** 2 + (xx - 7.0) ** 2) / 8.0))
    true_shift = (3, -5, 2)
    moved = np.roll(base, true_shift, axis=(0, 1, 2))
    got = score_to_position(correlation_score(base, moved))
    want = tuple(float(s % n) for s in true_shift)
    exact("voxel,voxel -> score -> position (既知シフト)", want, got)
    return rows


def selftest(seed=0):
    """往復誤差表を印字して 0 を返す(``python reprconv.py`` の本体)。"""
    rows = roundtrip_report(seed)
    width = max(len(r["pair"]) for r in rows)
    n_exact = n_lossy = 0
    worst = 0.0
    for r in rows:
        if r["kind"] == "exact":
            n_exact += 1
            worst = max(worst, r["max_abs"])
            print(f"  {r['pair']:<{width}}  exact  max|Δ| = {r['max_abs']:.3e}")
        else:
            n_lossy += 1
            print(f"  {r['pair']:<{width}}  lossy  {r['lost']}")
    print(f"\n可逆 {n_exact} 組(最悪 max|Δ| = {worst:.3e}) / 不可逆 {n_lossy} 組")
    return 0


if __name__ == "__main__":
    raise SystemExit(selftest())
