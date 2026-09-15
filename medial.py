# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""medial — 3D medial surface / 3D 骨格(TRIZ 原理 #17「多次元化(線→面)」)。

2D の形状照合は「輪郭(1D 境界)→ 2D スケルトン(中心線)」で位相を捉える。これを 1 次元
上げると「曲面(2D 境界)→ **medial surface(中心面)/ 3D 骨格**」になる。太い塊は面状の
medial surface に、細い管は線状の骨格に潰れる——同じ抽出器が形状の局所次元に応じて自然に
面/線を出し分ける。これが位相不変な形状照合の土台になる。

原理:
    距離変換(EDT)の **リッジ(尾根 = 勾配方向の極大)** が medial(中心)である。各 voxel から
    最近傍の背景までの距離を測ると、物体の「芯」ほど値が大きく、そこが局所的な峰になる。峰の
    次元(点/線/面)が物体の局所的な太さ次元に対応する。

公開 API:
    distance_ridge(vol)      -> (ridge_mask, edt)   EDT のリッジを medial として抽出
    skeletonize_vol(vol)     -> skeleton(bool 3D)   skimage Lee(1994)3D 細線化ラッパ
    medial_axis_points(vol)  -> (points, radius)    medial voxel 座標 + 局所半径(=EDT)
    topology_signature(skel) -> dict                26 近傍次数による位相記述子
    medial_match(a, b)       -> float               位相 + 半径分布による粗照合スコア

入力はバイナリ voxel(bool / 0-1 の 3D numpy 配列)。距離は voxel 単位(等方サンプリング前提)。
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import convolve, distance_transform_edt, maximum_filter

__all__ = [
    "distance_ridge",
    "skeletonize_vol",
    "medial_axis_points",
    "topology_signature",
    "medial_match",
    "skeleton_junctions3d",
    "skeleton_endpoints3d",
    "skeleton_prune3d",
    "skeleton_branches3d",
    "skeleton_graph3d",
]


def _as_binary_volume(vol, name="vol"):
    """入力を bool の 3D 配列に正規化(信頼境界での再検証: 型/次元/中身を必ず確認)。

    bool / 0-1 / 任意の数値配列を受け、非ゼロを前景とみなす。3D 以外・空配列・NaN/Inf 混入は
    fail-closed で ValueError。返り値は連続な bool 配列(以降のシフト/畳み込みが安全)。
    """
    arr = np.asarray(vol)
    if arr.ndim != 3:
        raise ValueError(f"{name} must be a 3D voxel array (got ndim={arr.ndim}, shape={arr.shape})")
    if arr.size == 0:
        raise ValueError(f"{name} is empty (shape={arr.shape})")
    if np.issubdtype(arr.dtype, np.floating) and not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} contains NaN/Inf (pass a binary voxel array)")
    return np.ascontiguousarray(arr).astype(bool)


def distance_ridge(vol, min_radius=0.0):
    """EDT のリッジ(距離場の局所極大)を medial として抽出。返り値 (ridge_mask, edt)。

    各前景 voxel の EDT を計算し、**26 近傍の局所極大**(自分の EDT が周囲 26 voxel の最大以上)を
    medial とみなす。この基準は物体の局所次元に応じて自然に次元を出し分ける:
        塊(球)  -> EDT が単峰 -> 点状の medial(中心 1 点)。
        管(円柱)-> 軸方向に平坦・半径方向に単峰 -> 線状の medial(軸線)。
        板(スラブ)-> 面内で平坦・厚み方向に単峰 -> 面状の medial(中心面)。
    境界 voxel は内側の隣が必ず大きいため極大にならず、外殻は自然に除かれる。平坦な尾根
    (軸/面)は同値の隣接を許容(>=)することで連続した線/面として残る。

    Args:
        vol: バイナリ voxel(bool / 0-1 の 3D)。
        min_radius: この EDT 値以下の弱い尾根を捨てる閾値(既定 0 = 捨てない)。ノイズ抑制用。

    Returns:
        ridge_mask (bool 3D): medial voxel。
        edt (float64 3D): 各 voxel の背景までのユークリッド距離(= 局所半径)。
    """
    mask = _as_binary_volume(vol)
    if float(min_radius) < 0.0:
        raise ValueError(f"min_radius must be non-negative (got: {min_radius})")
    edt = distance_transform_edt(mask).astype(np.float64)
    # 3x3x3 の最大値フィルタ(外側 = 背景 = 0)。自分自身を含むので edt >= local_max は
    # 「26 近傍で最大(タイ許容)」= 局所極大を意味する。
    local_max = maximum_filter(edt, size=3, mode="constant", cval=0.0)
    ridge_mask = mask & (edt >= local_max) & (edt > float(min_radius))
    return ridge_mask, edt


def skeletonize_vol(vol):
    """3D バイナリ voxel を細線化して 1 voxel 幅の骨格に。skimage の Lee(1994)法ラッパ。

    method='lee' は 3D 対応の位相保存細線化。塊も含めて線状の骨格へ潰す(medial *surface* が
    欲しい場合は distance_ridge を使う)。返り値は入力と同形の bool 配列。

    Args:
        vol: バイナリ voxel(bool / 0-1 の 3D)。

    Returns:
        skeleton (bool 3D): 骨格 voxel。

    入力の扱い: ``_as_binary_volume`` が 3-D 配列を bool に正規化する(非ゼロ = 前景)。
    3-D でない・空配列・float で NaN/Inf を含む場合は ``ValueError``。軸順は
    ``(z, y, x)``、距離・太さは voxel 単位で、等方サンプリングを仮定する(異方
    voxel のままだと細線化の結果が軸ごとに偏る。先に ``vol_resize`` で等方化する)。

    挙動:
    - 前景が無ければ全 False の同形配列を返す(skimage は呼ばない)。
    - ``skimage.morphology.skeletonize(mask, method="lee")`` は遅延 import。
      scikit-image が無い環境ではここで ``ImportError`` になる。
    - Lee 法は位相を保つ(連結成分数・穴・空洞を変えない)が、太い塊は複数の枝に
      潰れ、表面の凹凸に応じたヒゲ(短い枝)が出る。ヒゲは ``skeleton_prune3d`` で
      刈る。

    使いどころ: ``topology_signature``(端点・分岐の数)、``skeleton_junctions3d`` /
    ``skeleton_endpoints3d`` / ``skeleton_branches3d`` の入力。骨格 voxel の局所
    半径が要るなら ``distance_ridge`` の ``edt`` を骨格位置で引く。
    """
    mask = _as_binary_volume(vol)
    if not mask.any():
        return np.zeros_like(mask)
    from skimage.morphology import skeletonize

    skel = skeletonize(mask, method="lee")
    return np.ascontiguousarray(skel).astype(bool)


def medial_axis_points(vol, min_radius=0.0):
    """medial voxel の座標と局所半径(= その点の EDT 値)を点群化。返り値 (points, radius)。

    太い部分は面状、細い部分は線状に分布する medial 点を (M,3) の座標(z,y,x)と、それぞれの
    局所半径 (M,) として返す。半径最大の点は形状の最も「内側」= 中心を指す。

    Args:
        vol: バイナリ voxel(bool / 0-1 の 3D)。
        min_radius: この半径以下の点を除外(ノイズ抑制)。

    Returns:
        points (float64, (M,3)): medial voxel 座標(z, y, x)。
        radius (float64, (M,)): 各点の EDT 値(= 局所内接半径)。

    手順: ``distance_ridge(vol, min_radius)`` で得た ``ridge_mask`` の ``np.argwhere``
    (配列 index、行は z-major の辞書順で決定的)と、その位置の ``edt`` 値を返す。
    座標は voxel index で spacing は掛けない(物理座標が要るなら呼び手で
    ``points * (sz, sy, sx)``、半径も同様に等方 spacing を掛ける)。

    引数と検証: ``vol`` は 3-D(非ゼロ = 前景)。3-D でない・空・NaN/Inf は
    ``ValueError``、``min_radius < 0`` も ``ValueError``。``radius`` は
    ``> min_radius`` の点だけ(境界 voxel は EDT が 1 以下なので ``min_radius=1`` で
    外殻ノイズをほぼ落とせる)。

    端の挙動: 前景が無い、または全点が ``min_radius`` 以下なら ``points`` は ``(0, 3)``、
    ``radius`` は ``(0,)`` の空配列(エラーにしない)。

    使いどころ: ``medial_match`` の半径分布、点群 op(``smallest_sphere3`` /
    ``fit_line3`` 等)への橋渡し、``np.argmax(radius)`` で最大内接球の中心を取る。
    """
    ridge_mask, edt = distance_ridge(vol, min_radius=min_radius)
    points = np.argwhere(ridge_mask).astype(np.float64)          # (M,3) in (z,y,x)
    radius = edt[ridge_mask].astype(np.float64)                   # (M,)
    return points, radius


def _skeleton_degree(skel):
    """各骨格 voxel の 26 近傍次数(骨格 voxel の数)。"""
    kernel = np.ones((3, 3, 3), dtype=np.int32)
    kernel[1, 1, 1] = 0
    return convolve(skel.astype(np.int32), kernel, mode="constant", cval=0)


def _ensure_skeleton(vol, name="vol"):
    """入力が骨格でなければ skeletonize_vol で細線化してから返す。

    「骨格である」判定 = 6 近傍(面隣接)がすべて前景の interior voxel が無いこと。
    """
    mask = _as_binary_volume(vol, name=name)
    if not mask.any():
        return mask
    from scipy.ndimage import binary_erosion, generate_binary_structure
    interior = binary_erosion(mask, structure=generate_binary_structure(3, 1),
                              border_value=0)
    return skeletonize_vol(mask) if interior.any() else mask


def skeleton_junctions3d(vol):
    """3D 骨格の分岐点(joint、26 近傍に骨格 voxel が 3 個以上)を voxel マスクで返す。

    骨格でない入力(interior を持つ塊)は skeletonize_vol で細線化してから測る。
    2D の `junctions_skeleton` の 3D 版。血管・多孔質・ネットワーク状構造の
    グラフ化(node 抽出)に使う。分岐次数の集計だけ欲しい場合は
    topology_signature が dict で返す。

    注意(honest): 26 近傍次数は分岐近傍の対角隣接で過大に出うる(離散骨格の
    既知の性質)。分岐 *個数* を数えるときはこのマスクを連結成分でまとめること。

    手順: ``_ensure_skeleton`` — 入力を bool 化し、6 近傍(面隣接)がすべて前景の
    interior voxel が 1 つでもあれば「骨格ではない」とみなして ``skeletonize_vol``
    (skimage Lee 法)を先に掛ける。その後、3x3x3 の全 1 カーネル(中心 0)の畳み込み
    (``mode="constant"``、外側は 0)で各 voxel の 26 近傍にある骨格 voxel 数(次数)を
    数え、``skel & (次数 >= 3)`` を返す。

    返り値: 入力と同形の bool 配列。前景が無ければ全 False。骨格 voxel 以外は
    必ず False。座標は ``np.argwhere`` で ``(z, y, x)`` 順に取れる。

    検証(``ValueError``): 3-D でない・空配列・float で NaN/Inf を含む入力。
    scikit-image が無い環境で細線化が必要になると ``ImportError``。

    注意: 既に骨格の入力でも interior 判定は毎回走る(細い骨格なら細線化は
    skip される)。個数を数えるなら ``vol_label(mask, 26)`` の成分数を使う。
    枝に分けるのは ``skeleton_branches3d``、端点は ``skeleton_endpoints3d``。
    """
    skel = _ensure_skeleton(vol)
    if not skel.any():
        return np.zeros_like(skel)
    return skel & (_skeleton_degree(skel) >= 3)


def skeleton_endpoints3d(vol):
    """3D 骨格の端点(26 近傍に骨格 voxel が 1 個以下)を voxel マスクで返す。

    孤立 voxel(次数 0)も端点に数える。2D の `r2_endpoints_skeleton` の 3D 版。

    手順: ``_ensure_skeleton`` で入力を bool 化し、6 近傍がすべて前景の interior voxel
    があれば ``skeletonize_vol`` で細線化してから、3x3x3 全 1 カーネル(中心 0、
    ``mode="constant"`` で外側 0)の畳み込みで各 voxel の 26 近傍にある骨格 voxel 数
    (次数)を数え、``skel & (次数 <= 1)`` を返す。volume の縁にある骨格 voxel は、
    外側が 0 扱いなので枝がそこで途切れていれば端点になる。

    返り値: 入力と同形の bool 配列(端点 = True)。前景が無ければ全 False。
    ``np.argwhere`` で ``(z, y, x)`` 座標に、``.sum()`` で端点数になる。

    検証(``ValueError``): 3-D でない・空配列・float で NaN/Inf を含む入力。
    細線化が必要で scikit-image が無い環境では ``ImportError``。

    注意:
    - 端点は各枝の末端で厳密だが、ヒゲ(細線化が作る短い枝)の先端も端点に数える。
      構造の端だけ欲しければ先に ``skeleton_prune3d`` で刈る。
    - 閉ループだけの骨格(輪)は端点 0 個。
    - 数だけ欲しいなら ``topology_signature`` が ``endpoints`` / ``isolated`` を
      分けて返す。
    """
    skel = _ensure_skeleton(vol)
    if not skel.any():
        return np.zeros_like(skel)
    return skel & (_skeleton_degree(skel) <= 1)


def skeleton_prune3d(vol, length=1):
    """3D 骨格のヒゲ(短い枝)を刈る。端点除去を length 回反復 = 枝長 <=length を除去。

    2D の `pruning` の 3D 版。孤立 voxel は端点扱いで消える。

    手順: ``_ensure_skeleton`` で bool 化(interior voxel があれば ``skeletonize_vol``
    で細線化)し、次を ``length`` 回繰り返す — 26 近傍次数 ``<= 1`` の voxel(端点と
    孤立点)をすべて同時に取り除く。骨格が空になるか端点が無くなれば(閉ループ
    だけになれば)途中で止まる。

    引数: ``length`` は ``int(length)`` にして負なら 0 に丸める(0 なら細線化した
    骨格をそのまま返す)。1 回の反復で各枝の先端 1 voxel が消えるので、
    長さ ``<= length`` voxel の枝(ヒゲ)は根元まで消える。

    返り値: 入力と同形の bool 配列。

    注意(挙動として知っておくこと):
    - **長い枝も先端から ``length`` voxel 短くなる**(ヒゲだけを選んで消す処理では
      ない)。主枝の端点位置が要るなら、刈った後の端点は元より ``length`` 内側に
      ある。
    - 2 分岐の間の短い枝は両端が分岐点(次数 >= 3)なので消えない。
    - 孤立 voxel は 1 回目で消える。
    - 反復のたびに次数を数え直すので、コストは ``length`` に比例する。

    検証(``ValueError``): 3-D でない・空配列・NaN/Inf を含む入力。細線化が必要で
    scikit-image が無ければ ``ImportError``。後段は ``skeleton_endpoints3d`` /
    ``skeleton_junctions3d`` / ``skeleton_branches3d`` / ``topology_signature``。
    """
    skel = _ensure_skeleton(vol)
    n = max(0, int(length))
    for _ in range(n):
        if not skel.any():
            break
        ends = skel & (_skeleton_degree(skel) <= 1)
        if not ends.any():
            break
        skel = skel & ~ends
    return skel


def skeleton_branches3d(vol, min_length=0):
    """3D 骨格を分岐点で切って枝(線分)に分割する。2D の `r2_split_skeleton_lines` の 3D 版。

    分岐点 voxel を除いた残りが枝。min_length > 0 なら、26 連結成分の voxel 数が
    それ未満の断片を除去する。

    手順: ``_ensure_skeleton`` で bool 化(interior voxel があれば ``skeletonize_vol``
    で細線化)→ 26 近傍次数 ``>= 3`` の voxel(分岐点)を取り除く → ``min_length > 0``
    なら ``scipy.ndimage.label``(3x3x3 全 1 構造 = 26 連結)で成分に分け、voxel 数が
    ``min_length`` 未満の成分を落とす。

    返り値: 入力と同形の bool 配列(枝 voxel = True)。**枝ごとのラベルは返さない**
    — 枝を個別に扱うには返り値を ``vol_label(branches, 26)`` に通す(成分数 = 枝数)。
    分岐点 voxel そのものは結果に含まれないので、枝の両端は分岐点の 1 voxel 手前で
    終わる。

    引数と検証: ``min_length`` は voxel 数(``int()`` で切り捨て。0 なら除去しない)。
    入力が 3-D でない・空・NaN/Inf は ``ValueError``。細線化が必要で
    scikit-image が無ければ ``ImportError``。前景が無ければ全 False。

    注意: 26 近傍次数は分岐の対角隣接で 3 以上になりやすく、分岐点が数 voxel の
    塊として除かれるため、枝が実際より短く出ることがある。閉ループだけの骨格は
    分岐点が無く、全体が 1 本の枝として残る。
    """
    skel = _ensure_skeleton(vol)
    if not skel.any():
        return np.zeros_like(skel)
    branches = skel & ~(skel & (_skeleton_degree(skel) >= 3))
    if min_length > 0 and branches.any():
        from scipy.ndimage import label
        lab, n = label(branches, structure=np.ones((3, 3, 3), dtype=np.int32))
        if n:
            sizes = np.bincount(lab.ravel())
            keep = np.zeros_like(sizes, dtype=bool)
            keep[1:] = sizes[1:] >= int(min_length)
            branches = keep[lab]
    return branches


def _strict_binary_volume(vol, name="skeleton"):
    """骨格入力を **厳密な二値**として bool 3-D に正規化(fail-closed)。

    ``_as_binary_volume`` は「非ゼロ = 前景」と緩く受けるが、**骨格を食う op に
    中間値は意味を持たない** —— 0.37 という voxel は「細いのか、確率なのか、
    スケールし忘れたのか」が区別できず、黙って前景に丸めると**グラフの位相が
    入力の素性に依って変わる**。だから bool か ``{0, 1}`` だけを受け、それ以外は
    何が入っていたかを名指しして ``ValueError``(先に閾値処理か
    ``skeletonize_vol`` を通すのは呼び手の仕事)。
    """
    arr = np.asarray(vol)
    if arr.ndim != 3:
        raise ValueError(f"{name} must be a 3D voxel array (got ndim={arr.ndim}, shape={arr.shape})")
    if arr.size == 0:
        raise ValueError(f"{name} is empty (shape={arr.shape})")
    if arr.dtype == bool:
        return np.ascontiguousarray(arr)
    if (not np.issubdtype(arr.dtype, np.number)
            or np.issubdtype(arr.dtype, np.complexfloating)):
        raise ValueError(f"{name} must be a bool or real numeric volume, got dtype {arr.dtype!r}")
    if np.issubdtype(arr.dtype, np.floating) and not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} contains NaN/Inf (pass a binary voxel array)")
    off = (arr != 0) & (arr != 1)
    if off.any():
        bad = arr[off]
        raise ValueError(
            f"{name} must be binary (bool, or values in {{0, 1}}); "
            f"{int(off.sum())} voxel(s) are neither 0 nor 1 (e.g. {float(bad.flat[0])!r}). "
            "Threshold it first, or pass the output of skeletonize_vol.")
    return np.ascontiguousarray(arr != 0)


def _spacing3(spacing, name="spacing"):
    """``(sz, sy, sx)`` の正の有限値 3 つに正規化(``volio.VolumeMeta`` も受ける)。

    ``volops._spacing_tuple`` と同じ規約。``None`` は等方 ``(1, 1, 1)``。
    """
    if spacing is None:
        return (1.0, 1.0, 1.0)
    if hasattr(spacing, "spacing_mm"):
        spacing = spacing.spacing_mm
    try:
        sp = tuple(float(s) for s in spacing)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a length-3 (sz, sy, sx) sequence or a "
                         f"VolumeMeta, got {spacing!r}") from None
    if len(sp) != 3 or any((not np.isfinite(s)) or s <= 0.0 for s in sp):
        raise ValueError(f"{name} must be 3 positive finite values (sz, sy, sx), got {sp!r}")
    return sp


def _graph_neighbourhood(spacing):
    """26 近傍のオフセットと、**spacing を掛けた実距離**の歩幅。"""
    sz, sy, sx = spacing
    offs, steps = [], []
    for dz in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dz or dy or dx:
                    offs.append((dz, dy, dx))
                    steps.append(float(np.sqrt((dz * sz) ** 2 + (dy * sy) ** 2
                                               + (dx * sx) ** 2)))
    return offs, steps


def _edge_row(u, v, length, path, dist, component):
    """枝 1 本の行。半径は経路上(両端のノード voxel を含む)の値から。"""
    row = {"u": int(min(u, v)), "v": int(max(u, v)),
           "length": float(length), "n_points": int(len(path)),
           "component": int(component)}
    if dist is None:
        row["radius_mean"] = None
        row["radius_min"] = None
    else:
        vals = np.array([dist[p] for p in path], dtype=np.float64)
        row["radius_mean"] = float(vals.mean())
        row["radius_min"] = float(vals.min())
    return row


def _graph_degrees(edges, ids):
    """ノード id → 接続する枝の本数(自己ループは 2 と数える)。"""
    deg = {int(i): 0 for i in ids}
    for e in edges:
        deg[e["u"]] += 1
        deg[e["v"]] += 1                 # u == v(自己ループ)なら自動的に +2
    return deg


def skeleton_graph3d(vol, distance=None, spacing=(1.0, 1.0, 1.0), min_branch_len=0.0):
    """3D 骨格を **ノード(接合点・端点)と枝(長さ・半径)のグラフ**に組み立てる。

    ``skeleton_junctions3d`` / ``skeleton_endpoints3d`` / ``skeleton_branches3d`` は
    「どの voxel がノードか/枝か」を **マスク**で返すだけで、**どの枝がどのノードと
    どのノードを繋ぐか**は返さない。回路にするにはその接続が要る —— 神経形態の
    ケーブル理論では、区画の軸方向コンダクタンスが **直径と長さ**で決まり、区画同士の
    **繋がり方**が回路そのものになる。この op はその 1 段を埋める。

    引数:
        vol: 3-D の骨格(bool か ``{0, 1}``。``skeletonize_vol`` の出力)。中身が
            塊(6 近傍がすべて前景の interior voxel がある)なら、族の他の op と
            同じく内部で ``skeletonize_vol`` を先に掛ける。
        distance: 任意。同形の距離変換ボリューム(``vol_distance_transform`` の
            出力)。渡すと各ノード・各枝に半径が付く。**単位は渡した距離場に従う**
            —— 物理単位が要るなら ``vol_distance_transform(mask, spacing)`` を渡す。
        spacing: ``(sz, sy, sx)``。枝の長さを **実距離**で測る(EM の異方ボクセルが
            既定の想定)。``VolumeMeta`` も受ける。
        min_branch_len: これ未満の**末端の枝(ヒゲ)**を刈る(既定 0 = 刈らない)。
            単位は ``spacing`` の実距離。刈るのは「片端が端点(次数 1)で、もう
            片端が次数 2 以上」の枝 —— **両端とも端点**の枝は刈らない。それは
            それ自体が 1 つの連結成分(短い孤立した管)なので、刈ると構造ごと
            消えてしまう。刈ったぶんは ``n_pruned_branches`` に返す。

    返り値: ``dict``(台帳の宣言 out 型 = ``table``)。

        * ``nodes``: ノード表。``id`` / ``z,y,x``(voxel 添字での重心。実座標は
          spacing を掛ける)/ ``kind`` / ``degree`` / ``n_voxels`` / ``radius``
          (``distance`` を渡したとき、そのノードの voxel での最大値 = 内接半径)/
          ``component``。
        * ``edges``: 枝表。``u`` / ``v``(ノード id の対)/ ``length``(骨格に沿った
          実距離、spacing 込み)/ ``radius_mean`` / ``radius_min`` / ``n_points``
          (経路上の voxel 数、両端のノード voxel を含む)/ ``component``。
        * ``n_nodes`` / ``n_edges`` / ``n_components`` / ``n_cycles`` /
          ``n_pruned_branches`` / ``n_skeleton_voxels`` / ``spacing`` / ``has_radius``。

    規約(ここが位相を決める):
        * 26 近傍次数 **2** の voxel は枝の途中であってノードにしない。次数 **1 以下**
          が端点(孤立 voxel を含む)、**3 以上**が接合。
        * 接合 voxel は 1 つとは限らない(離散骨格では分岐が数 voxel の塊になる)。
          26 連結で塊にまとめて **1 ノード**として数え、座標はその重心。
        * **連結成分が複数なら黙って繋がない。** ``n_components`` に本数を返し、
          各ノード・各枝に ``component`` を付ける。
        * 閉ループだけの成分(ノードになる voxel が 1 つも無い輪)は、その成分の
          先頭 voxel を 1 つだけ種のノードに立てて自己ループの枝 1 本にする。
          こうすると **オイラーの関係 ``n_cycles = n_edges - n_nodes +
          n_components``** が輪でも成り立つ(木だと仮定していない)。
        * ``kind`` は**刈った後の**次数で決まる: 0 = ``isolated`` / 1 = ``endpoint`` /
          2 = ``chain``(輪の種ノード、または刈った結果そうなったノード)/
          3 以上 = ``junction``。刈ると接合が次数 2 に落ちることがあり、その
          ノードは残る(区画の境界としては正しいが、「次数 2 はノードにしない」
          という上の規約は**刈る前**の話であることに注意)。
        * 接合の塊どうしが直接隣接している(間に次数 2 の道が無い)場合は、その
          対に対して **1 本**の枝を作る(長さ = 隣接する voxel 対の最短)。

    検証(すべて ``ValueError`` で fail-closed): 3-D でない/空配列/NaN・Inf/
    bool でも ``{0,1}`` でもない値(中間値の「たぶん前景」を黙って丸めない)/
    前景がゼロ/``distance`` の形が違う・負・非有限/``spacing`` が 3 つの正の
    有限値でない/``min_branch_len`` が負。細線化が要る入力で scikit-image が
    無ければ ``ImportError``。

    注意(honest、いずれも実測):

    * 長さは **26 近傍の折れ線**の和なので、曲がった枝は連続曲線より長く出る。
      半径 14 voxel の閉じた管(真の周長 87.96)で **94.7 = +7.7 %**。
    * **太い入力は端が縮む。** 自由端の細線化は端の蓋の手前で止まる。長さ 35 の
      直円柱で実測すると 半径 1・2 は **35.00(縮みゼロ)**、半径 3 は 33、
      半径 4 は 31 —— 半径が 3 以上になると片端あたり 1〜2 voxel 内側に寄る。
      長さを真値と比べるなら、**細線化を通らない 1 voxel 幅の骨格**を渡すこと
      (そのときは厳密に一致する: 31 voxel の直線で 30.0)。
    * 分岐では、接合の塊(次数 3 以上が 26 連結でまとまったもの)に呑まれたぶん
      だけ枝が短くなる。**接合より短いヒゲは枝にならず、ノードの ``n_voxels``
      に含まれて消える**(``min_branch_len`` で刈る対象にすらならない)。
    * 半径は ``distance`` の値そのもの。端点は端の蓋までの距離で決まるので
      **管の半径より小さく出る**(半径 3 の円柱で端点 2.0、枝の平均 3.07)。
      枝の太さを見るなら ``radius_mean`` / ``radius_min`` を使う。
    * **90 度回転**: 1 voxel 幅の骨格を入れた場合、グラフは同型で長さも厳密に
      一致する(9 通り実測)。太い塊を渡した場合はノード数・枝数は一致するが、
      長さは最大 1.41(= 対角 1 歩)ずれる —— ずれているのはこの op ではなく
      **細線化ヘルパ(skimage Lee)が回転で厳密には同じ骨格を作らない**ため。
    """
    from scipy.ndimage import binary_erosion, generate_binary_structure, label

    skel = _strict_binary_volume(vol, "skeleton")
    if not skel.any():
        raise ValueError("skeleton has no foreground voxel (all zero) — "
                         "there is no graph to build (pass a skeleton or a solid shape)")
    interior = binary_erosion(skel, structure=generate_binary_structure(3, 1),
                              border_value=0)
    if interior.any():
        skel = skeletonize_vol(skel)
        if not skel.any():
            raise ValueError("skeletonize_vol produced an empty skeleton from this volume")

    sp = _spacing3(spacing)
    mbl = float(min_branch_len)
    if not np.isfinite(mbl) or mbl < 0.0:
        raise ValueError(f"min_branch_len must be a finite value >= 0, got {min_branch_len!r}")

    dist = None
    if distance is not None:
        dist = np.asarray(distance)
        if dist.shape != skel.shape:
            raise ValueError(f"distance must have the same shape as the skeleton "
                             f"{skel.shape!r}, got {dist.shape!r}")
        if (not np.issubdtype(dist.dtype, np.number)
                or np.issubdtype(dist.dtype, np.complexfloating)):
            raise ValueError(f"distance must be a real numeric volume, got dtype {dist.dtype!r}")
        dist = dist.astype(np.float64)
        if not np.all(np.isfinite(dist)):
            raise ValueError("distance contains NaN/Inf")
        if float(dist.min()) < 0.0:
            raise ValueError(f"distance must be non-negative (it is a distance "
                             f"transform), got min {float(dist.min()):.6g}")

    st26 = np.ones((3, 3, 3), dtype=np.int32)
    deg_vox = _skeleton_degree(skel)
    node_mask = skel & (deg_vox != 2)
    node_of, n_node = label(node_mask, structure=st26)
    node_of = node_of.astype(np.int64)
    comp_of, n_comp = label(skel, structure=st26)

    # 閉ループだけの成分にはノードになる voxel が 1 つも無い。種を 1 つ立てて
    # 自己ループの枝にする(立てないと、その成分は**出力から黙って消える**)。
    if n_comp:
        has_node = np.zeros(n_comp + 1, dtype=bool)
        if node_mask.any():
            has_node[np.unique(comp_of[node_mask])] = True
        nid = int(n_node)
        for c in range(1, n_comp + 1):
            if has_node[c]:
                continue
            zz, yy, xx = np.nonzero(comp_of == c)
            nid += 1
            node_of[zz[0], yy[0], xx[0]] = nid
        n_node = nid

    node_vox = {}
    for z, y, x in np.argwhere(node_of > 0):
        node_vox.setdefault(int(node_of[z, y, x]), []).append((int(z), int(y), int(x)))

    offs, steps = _graph_neighbourhood(sp)
    d0, d1, d2 = skel.shape
    consumed = np.zeros(skel.shape, dtype=bool)
    edges = []
    direct = {}

    for nid in sorted(node_vox):
        for (z, y, x) in node_vox[nid]:
            for (dz, dy, dx), slen in zip(offs, steps):
                z1, y1, x1 = z + dz, y + dy, x + dx
                if not (0 <= z1 < d0 and 0 <= y1 < d1 and 0 <= x1 < d2):
                    continue
                if not skel[z1, y1, x1]:
                    continue
                other = int(node_of[z1, y1, x1])
                if other:
                    if other == nid:
                        continue
                    key = (min(nid, other), max(nid, other))
                    if key not in direct or slen < direct[key][0]:
                        direct[key] = (slen, [(z, y, x), (z1, y1, x1)])
                    continue
                if consumed[z1, y1, x1]:
                    continue                       # 反対側から既に辿った枝
                consumed[z1, y1, x1] = True
                path = [(z, y, x), (z1, y1, x1)]
                length = slen
                pz, py, px = z, y, x
                cz, cy, cx = z1, y1, x1
                while True:
                    step = None
                    for (ez, ey, ex), elen in zip(offs, steps):
                        z2, y2, x2 = cz + ez, cy + ey, cx + ex
                        if not (0 <= z2 < d0 and 0 <= y2 < d1 and 0 <= x2 < d2):
                            continue
                        if not skel[z2, y2, x2] or (z2, y2, x2) == (pz, py, px):
                            continue
                        step = (z2, y2, x2, elen)
                        break                      # 次数 2 なので候補はこの 1 つだけ
                    if step is None:
                        raise ValueError(
                            "internal: degree-2 skeleton voxel %r has no continuation "
                            "(the 26-neighbour degree and the walk disagree)"
                            % ((cz, cy, cx),))
                    z2, y2, x2, elen = step
                    length += elen
                    path.append((z2, y2, x2))
                    if node_of[z2, y2, x2]:
                        edges.append(_edge_row(nid, int(node_of[z2, y2, x2]), length,
                                               path, dist, comp_of[z, y, x]))
                        break
                    consumed[z2, y2, x2] = True
                    pz, py, px = cz, cy, cx
                    cz, cy, cx = z2, y2, x2

    for (a, b), (slen, path) in sorted(direct.items()):
        edges.append(_edge_row(a, b, slen, path, dist, comp_of[path[0]]))

    alive = set(node_vox)
    pruned = 0
    if mbl > 0.0 and edges:
        while True:
            dg = _graph_degrees(edges, alive)
            drop = None
            for i, e in enumerate(edges):
                if e["u"] == e["v"] or e["length"] >= mbl:
                    continue
                # 末端(次数 1)の枝を刈る。ただし**両端とも端点**の枝は刈らない
                # —— それは「短い孤立した管」そのものなので、刈ると構造ごと消える。
                # ★ここを「もう片端が次数 3 以上」と書いていた最初の版は、実測で
                #   一度も発火しなかった: ヒゲの根元が枝の端点クラスタと 26 近傍で
                #   融合して次数 2 になる配置が普通にあり、その場合に素通りしていた
                #   (「刈った」と報告しながら 0 本という、いちばん静かな失敗)。
                if dg[e["u"]] == 1 and dg[e["v"]] >= 2:
                    drop = (i, e["u"])
                    break
                if dg[e["v"]] == 1 and dg[e["u"]] >= 2:
                    drop = (i, e["v"])
                    break
            if drop is None:
                break
            i, leaf = drop
            edges.pop(i)
            alive.discard(leaf)
            pruned += 1

    order = sorted(alive)
    remap = {old: new for new, old in enumerate(order)}
    for e in edges:
        e["u"], e["v"] = remap[e["u"]], remap[e["v"]]
        if e["u"] > e["v"]:
            e["u"], e["v"] = e["v"], e["u"]
    edges.sort(key=lambda e: (e["u"], e["v"], e["length"]))
    dg = _graph_degrees(edges, remap.values())

    nodes = []
    for old in order:
        vox = np.array(node_vox[old], dtype=np.float64)
        d = int(dg[remap[old]])
        kind = ("isolated" if d == 0 else "endpoint" if d == 1
                else "chain" if d == 2 else "junction")
        nodes.append({
            "id": int(remap[old]),
            "z": float(vox[:, 0].mean()), "y": float(vox[:, 1].mean()),
            "x": float(vox[:, 2].mean()),
            "kind": kind, "degree": d, "n_voxels": int(len(vox)),
            "radius": (None if dist is None
                       else float(max(dist[p] for p in node_vox[old]))),
            "component": int(comp_of[node_vox[old][0]]),
        })

    return {
        "nodes": nodes,
        "edges": edges,
        "n_nodes": len(nodes),
        "n_edges": len(edges),
        "n_components": int(n_comp),
        "n_cycles": int(len(edges) - len(nodes) + int(n_comp)),
        "n_pruned_branches": int(pruned),
        "n_skeleton_voxels": int(skel.sum()),
        "spacing": (float(sp[0]), float(sp[1]), float(sp[2])),
        "has_radius": dist is not None,
    }


def topology_signature(skeleton):
    """骨格の 26 近傍次数から位相記述子を作る。端点/分岐点/通常点/孤立点の個数を返す。

    各骨格 voxel について 26 近傍にある骨格 voxel 数(次数)を数え、
        次数 1  = 端点(endpoint)
        次数 2  = 通常点(骨格の途中)
        次数>=3 = 分岐点(branch)
        次数 0  = 孤立点(isolated)
    に分類する。個数は平行移動・回転(90 度)不変で、形状の位相を粗く要約する記述子になる。

    注意(honest): 26 近傍の次数は、分岐近傍で対角隣接により過大に数えられることがある(離散
    骨格の既知の性質)。端点数は各枝の末端で厳密だが、分岐点数はやや過大側に振れうる。

    Args:
        skeleton: 骨格 voxel(bool / 0-1 の 3D)。

    Returns:
        dict: endpoints, branches, normal, isolated, total(骨格 voxel 総数),
              degree_hist(次数 -> 個数)。
    """
    skel = _as_binary_volume(skeleton, name="skeleton")
    kernel = np.ones((3, 3, 3), dtype=np.int32)
    kernel[1, 1, 1] = 0
    degree = convolve(skel.astype(np.int32), kernel, mode="constant", cval=0)
    deg = degree[skel]                                            # 骨格 voxel の次数のみ
    if deg.size == 0:
        return {"endpoints": 0, "branches": 0, "normal": 0, "isolated": 0,
                "total": 0, "degree_hist": {}}
    endpoints = int(np.count_nonzero(deg == 1))
    branches = int(np.count_nonzero(deg >= 3))
    normal = int(np.count_nonzero(deg == 2))
    isolated = int(np.count_nonzero(deg == 0))
    vals, counts = np.unique(deg, return_counts=True)
    degree_hist = {int(v): int(c) for v, c in zip(vals, counts)}
    return {
        "endpoints": endpoints,
        "branches": branches,
        "normal": normal,
        "isolated": isolated,
        "total": int(deg.size),
        "degree_hist": degree_hist,
    }


def _topology_vector(sig):
    """位相記述子を、総数で正規化した [端点, 分岐, 通常, 孤立] の割合ベクトルに。"""
    total = max(sig["total"], 1)
    return np.array(
        [sig["endpoints"], sig["branches"], sig["normal"], sig["isolated"]],
        dtype=np.float64,
    ) / total


def _radius_histogram(radius, edges):
    """半径配列を共通 bin 端 edges で正規化ヒストグラム(合計 1)に。空なら一様 0。"""
    if radius.size == 0:
        return np.zeros(len(edges) - 1, dtype=np.float64)
    hist, _ = np.histogram(radius, bins=edges)
    s = hist.sum()
    if s == 0:
        return np.zeros(len(edges) - 1, dtype=np.float64)
    return hist.astype(np.float64) / s


def medial_match(vol_a, vol_b, w_topology=0.6, w_radius=0.4, n_bins=12):
    """2 つの voxel 形状の medial(位相 + 半径分布)による粗照合スコア。返り値 [0,1]。

    骨格の位相記述子(端点/分岐/通常/孤立の割合)の距離と、medial 半径分布(内接半径の
    ヒストグラム)の距離を重み付き合成し、類似度 = 1 - 距離 として返す。1 に近いほど似ている。
    平行移動・回転(90 度)に対して概ね不変で、位相ベースの初期照合(粗いふるい)に使う。

    Args:
        vol_a, vol_b: バイナリ voxel(bool / 0-1 の 3D)。
        w_topology: 位相距離の重み(既定 0.6)。
        w_radius: 半径分布距離の重み(既定 0.4)。
        n_bins: 半径ヒストグラムの bin 数。

    Returns:
        float: 類似スコア [0,1](大きいほど類似)。
    """
    if w_topology < 0 or w_radius < 0 or (w_topology + w_radius) <= 0:
        raise ValueError("weights must be non-negative and sum to > 0")

    # 位相距離: 骨格の次数割合ベクトルの L1 距離を半分にして [0,1] に収める。
    sig_a = topology_signature(skeletonize_vol(vol_a))
    sig_b = topology_signature(skeletonize_vol(vol_b))
    tv_a, tv_b = _topology_vector(sig_a), _topology_vector(sig_b)
    topo_dist = 0.5 * float(np.abs(tv_a - tv_b).sum())           # [0,1]

    # 半径分布距離: 共通 bin での全変動距離(TV = 0.5 * L1)、[0,1]。
    _, ra = medial_axis_points(vol_a)
    _, rb = medial_axis_points(vol_b)
    rmax = max(float(ra.max()) if ra.size else 0.0,
               float(rb.max()) if rb.size else 0.0)
    if rmax <= 0.0:
        radius_dist = 0.0 if (ra.size == 0 and rb.size == 0) else 1.0
    else:
        edges = np.linspace(0.0, rmax + 1e-9, n_bins + 1)
        ha = _radius_histogram(ra, edges)
        hb = _radius_histogram(rb, edges)
        radius_dist = 0.5 * float(np.abs(ha - hb).sum())         # [0,1]

    dist = (w_topology * topo_dist + w_radius * radius_dist) / (w_topology + w_radius)
    return float(1.0 - min(max(dist, 0.0), 1.0))


if __name__ == "__main__":
    # 手早い自己確認(中実球 / 中実円柱)。
    def _ball(size, r):
        zz, yy, xx = np.mgrid[0:size, 0:size, 0:size]
        c = (size - 1) / 2.0
        return ((zz - c) ** 2 + (yy - c) ** 2 + (xx - c) ** 2) <= r * r

    v = _ball(41, 12)
    pts, rad = medial_axis_points(v)
    i = int(np.argmax(rad))
    print(f"ball: medial pts={len(pts)}  max_radius={rad[i]:.2f} @ {pts[i]}  (center=20)")
    print("self-match:", round(medial_match(v, v), 3))
