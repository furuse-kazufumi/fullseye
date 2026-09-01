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
    max|Δ| = 2.2e-16、``selftest`` が毎回測る)。**戻らないのは長さだけ** ——
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
    既定 (36, 18) では bin 幅 10 度に対し実測 3 度前後(``selftest`` が出す)。

    仰角の bin は ``sin(el)`` で等分する(等立体角)。度で等分すると極が過剰に
    細かくなり、「北極に面が集中している」という嘘の山が立つ。

    Args:
        normals: (N, 3)。
        n_az: 方位の bin 数(既定 36 = 10 度刻み)。
        n_el: 仰角の bin 数(既定 18)。
    Returns:
        (n_el, n_az) float64 の計数マップ(行 = 仰角、列 = 方位)。
    Raises:
        ValueError: bin 数が 1 未満 / 上限超 / 入力不正。
    """
    n_el_i, n_az_i = _shape2((n_el, n_az), "egi bins")
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
    との往復が**全域で厳密**になる(実測 max|Δ| = 8.9e-16)。教科書の
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
    最大 0.5 画素ずれる(よく離れた点での実測 RMS 0.2880 px = 一様量子化の
    理論値 1/sqrt(12) = 0.2887 と一致)。近接した点は連結成分として融合するので、
    往復で点数も減りうる(実測: 60 点をランダムに置くと 52 点)。

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
    判定は最大差分と最小差分の比で行い、閾値は 1e-9(相対)。

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
    sigma = np.maximum(sigma, np.finfo(float).tiny)        # 重複点で 0 にしない
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
        r2 = (zz[:, None, None] ** 2 + yy[None, :, None] ** 2 + xx[None, None, :] ** 2)
        amp = w[i] / ((2.0 * np.pi) ** 1.5 * sigma[i] ** 3) * cell
        out[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]] += amp * np.exp(-r2 / (2.0 * sigma[i] ** 2))
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
        (D, H, W) float64、値域は概ね [-1, 1](完全一致で 1.0)。
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

    ``angle_to_matrix(90)`` は軸2(x)を軸1(y)へ送る —— **度**であることと
    **どちらの軸へ回るか**が、この 2 行の全内容である。ラジアンを渡すと
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
    :func:`matrix_to_rot_scale` と往復して **max|Δ| = 0**(実測)。

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

    **角度は度**。:func:`polar_to_cscalar` と往復して実測 max|Δ| = 2.5e-16。

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

    :func:`counts_to_countrate` と往復して実測 max|Δ| = 0.0(同じ gate なら
    乗除が厳密に打ち消す値域)。

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
    d_sep, _ = cKDTree(back_sep).query(kp_sep, k=1)
    rows.append({"pair": "keypoints -> image2d -> keypoints (離した点)", "kind": "lossy",
                 "lost": f"画素格子への量子化のみ RMS {float(np.sqrt(np.mean(d_sep ** 2))):.4f} px "
                         f"(一様量子化の理論値 1/sqrt(12) = 0.2887)、"
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
