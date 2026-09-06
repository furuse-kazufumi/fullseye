# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""regionprops3d — 3D 連結成分ラベリング + リージョンプロパティ(多物体計測)。

二値ボクセル(bool または 0/1 の 3D numpy 配列)を入力に、連結成分ごとの
体積・重心・バウンディングボックス・主軸・等価半径・真球度などを計測する。
CT / ボリューメトリック検査で「複数の部品を一括計測」する Physical AI 用途を想定。

依存: numpy と scipy.ndimage(label / find_objects)。scipy は fullseye の
3D スイート共通前提なので合わせる。

座標系: 全プロパティは (z, y, x) 軸順(numpy の配列軸順)で報告する。

連結性(connectivity):
    6  = 面接続のみ (generate_binary_structure(3, 1))
    18 = 面 + 辺接続   (generate_binary_structure(3, 2))
    26 = 面 + 辺 + 角接続 (generate_binary_structure(3, 3))

honest な制約(離散化に由来):
    - `volume` はボクセル数そのもの。連続体の体積を離散近似したものなので、
      小さな成分ほど相対誤差が大きい(理論体積比 ±十数 % 程度ずれ得る)。
    - `surface_area` は境界ボクセルの露出面カウント近似(6 近傍の面のみ数える)。
      voxelization の階段状表面のため真の連続表面積より過大評価になりやすく、
      その結果 `sphericity` も真値より小さめに出る(離散球でも厳密に 1 にならない)。
      特に滑らかな凸面では露出面積が真の表面積の約 1.5 倍(3 軸それぞれで投影
      面積の 2 倍が積み上がる ≒ 6πr² vs 真の 4πr²)に漸近するため、球の
      `sphericity` は半径に依らず理論上 ~2/3(実測 ~0.66)が上限となる。
      絶対値ではなく形状間の相対比較(球 ≫ 細長い箱)として使うのが安全。
    - 接触した(連結した)物体は 1 成分に融合するため分離計測できない。必要なら
      前段で morphological erosion / distance-transform watershed 等で切り分ける。
"""
from __future__ import annotations

import numpy as np

try:
    from scipy.ndimage import label as _label
    from scipy.ndimage import find_objects as _find_objects
    from scipy.ndimage import generate_binary_structure as _gen_struct
except ImportError as exc:  # pragma: no cover - scipy は前提だが明示的に失敗させる
    raise ImportError(
        "regionprops3d requires scipy.ndimage "
        "(`from scipy.ndimage import label, find_objects`)."
    ) from exc

__all__ = [
    "label_components",
    "region_props",
    "largest_component",
    "filter_by_volume",
    "inner_box3",
]

# connectivity 値 -> generate_binary_structure(rank=3, connectivity=?) の対応。
_CONNECTIVITY_RANK = {6: 1, 18: 2, 26: 3}


# --------------------------------------------------------------------------- #
# 内部ヘルパ                                                                    #
# --------------------------------------------------------------------------- #
def _as_binary_3d(vol) -> np.ndarray:
    """入力を bool の 3D 配列に正規化する。不正形状は fail-closed で拒否。"""
    arr = np.asarray(vol)
    if arr.ndim != 3:
        raise ValueError(
            f"a 3D voxel array (ndim==3) is required, but got ndim={arr.ndim}."
        )
    return arr.astype(bool, copy=False)


def _structure(connectivity: int) -> np.ndarray:
    """connectivity(6/18/26)に対応する 3x3x3 の構造要素を返す。"""
    try:
        rank = _CONNECTIVITY_RANK[int(connectivity)]
    except (KeyError, ValueError, TypeError):
        raise ValueError(
            f"connectivity must be one of 6 / 18 / 26 "
            f"(got: {connectivity!r})."
        )
    return _gen_struct(3, rank)


def _surface_area(mask: np.ndarray) -> int:
    """境界ボクセルの露出面数(6 近傍近似)。単位はボクセル面 1 枚 = 1。

    ゼロ padding した二値マスクを各軸方向に差分し、前景↔背景の遷移
    (= 露出面)を数える。配列端に接する前景の面も padding により計上される。
    """
    if not mask.any():
        return 0
    m = np.pad(mask.astype(np.int8), 1)
    area = 0
    for axis in range(3):
        area += int(np.count_nonzero(np.diff(m, axis=axis)))
    return area


def _principal_analysis(coords: np.ndarray):
    """座標群 (N,3) の共分散から主軸(固有ベクトル)と主軸長を返す。

    Returns
    -------
    axes : (3,3) ndarray
        固有ベクトルを行として、固有値降順に並べたもの(axes[0] が最長軸方向)。
    lengths : (3,) ndarray
        対応する固有値の平方根(降順)。負の固有値(数値誤差)は 0 にクリップ。
    """
    n = coords.shape[0]
    if n < 2:
        # 単一ボクセル等はばらつきゼロ。恒等基底 + 長さ 0 を返す。
        return np.eye(3), np.zeros(3)
    # bias=True(N で正規化)で N=1 でも nan を出さない母共分散。
    cov = np.cov(coords.T.astype(np.float64), bias=True)
    cov = np.atleast_2d(cov)
    # 対称行列なので eigh。固有値は昇順で返るため降順に並べ替える。
    eigvals, eigvecs = np.linalg.eigh(cov)
    order = np.argsort(eigvals)[::-1]
    eigvals = eigvals[order]
    eigvecs = eigvecs[:, order]
    lengths = np.sqrt(np.clip(eigvals, 0.0, None))
    # 固有ベクトルを「行」に並べ替え(axes[i] が i 番目の主軸方向)。
    axes = eigvecs.T.copy()
    return axes, lengths


# --------------------------------------------------------------------------- #
# 公開 API                                                                      #
# --------------------------------------------------------------------------- #
def label_components(vol, connectivity: int = 26):
    """3D 二値ボリュームを連結成分にラベリングする。

    Parameters
    ----------
    vol : array_like
        bool または 0/1 の 3D 配列。
    connectivity : int
        6(面) / 18(面+辺) / 26(面+辺+角)のいずれか。

    Returns
    -------
    labels : ndarray(int)
        vol と同形状。背景 0、各連結成分に 1..n のラベル。
    n : int
        連結成分数。

    補足:
    - 入力は ``astype(bool)`` で二値化する。0 以外はすべて前景で、float の NaN も True(前景)になる点に注意。
    - 軸順は (z, y, x) = numpy の配列軸順。``labels`` の dtype は ``scipy.ndimage.label`` の返す整数型(通常 int32)。前景が無い/空配列なら int32 のゼロ配列と 0 を返す。
    - ラベル番号の付与順は scipy の走査順で、体積順ではない。
    - Raises ``ValueError``: 3 次元でない入力、``connectivity`` が 6/18/26 以外。
    - 接触している物体は 1 成分に融合する。分離が要るなら前段で ``morph_erode3d`` / ``morph_open3d`` や ``vol_watershed`` で切る。
    - 後段: ``region_props``(計測)、``largest_component`` / ``filter_by_volume``(選別)、``vol_select_labels``(特徴でふるい)、``vol_colorize_labels``(可視化)。
    """
    arr = _as_binary_3d(vol)
    struct = _structure(connectivity)
    if arr.size == 0 or not arr.any():
        return np.zeros(arr.shape, dtype=np.int32), 0
    labels, n = _label(arr, structure=struct)
    return labels, int(n)


def region_props(vol, connectivity: int = 26) -> list[dict]:
    """各連結成分のリージョンプロパティ一覧を返す。

    Parameters
    ----------
    vol : array_like
        bool または 0/1 の 3D 配列。
    connectivity : int
        6 / 18 / 26。

    Returns
    -------
    list[dict]
        成分ごとの dict。キー:
          - ``label``           : ラベル番号 (int)
          - ``volume``          : ボクセル数 (int)
          - ``centroid``        : 重心 (z, y, x) の tuple(float)
          - ``bbox``            : (z0, y0, x0, z1, y1, x1)。z1/y1/x1 は排他的上端(stop)
          - ``extent``          : volume / bbox 体積(充填率、0..1)
          - ``principal_axes``  : (3,3) 主軸ベクトル(行、固有値降順)
          - ``principal_lengths``: (3,) 主軸長 = 座標共分散固有値の平方根(降順)
          - ``equivalent_radius``: 等価球半径 (3V/4π)^(1/3)
          - ``surface_area``    : 露出面カウント近似(ボクセル面単位)
          - ``sphericity``      : 等体積球表面積 / 実表面積(球=1 に近い、離散のため <1)

        前景ボクセルが無い(または空入力)場合は空リスト。

    補足:
    - 全量はボクセル単位(スペーシング補正なし)。実寸が要るなら ``volume`` に voxel 体積、``centroid`` / ``bbox`` / ``principal_lengths`` に各軸のスペーシングを掛ける(非等方だと主軸方向は歪む)。
    - ``principal_lengths`` は座標の母共分散(N で割る)の固有値の平方根で、成分の半径ではなく座標の標準偏差。1 ボクセルの成分は ``principal_axes`` が単位行列、``principal_lengths`` が全 0。
    - ``surface_area`` は配列端に接する面も数える(ゼロ padding)。``sphericity`` は離散化のため球でも約 0.66 が上限(モジュール docstring 参照)。
    - ラベルは 1..n の順(``label_components`` と同じ scipy の走査順)で、体積順ではない。並べ替えは呼び手で行う。
    - 入力は 0 以外を前景として bool 化する(NaN も前景)。Raises ``ValueError``: 3 次元でない入力、``connectivity`` が 6/18/26 以外。
    """
    arr = _as_binary_3d(vol)
    if arr.size == 0 or not arr.any():
        return []

    struct = _structure(connectivity)
    labels, n = _label(arr, structure=struct)
    if n == 0:
        return []

    slices = _find_objects(labels)
    props: list[dict] = []
    for lbl in range(1, n + 1):
        slc = slices[lbl - 1]
        if slc is None:  # ラベルが飛んでいることは通常ないが防御的に
            continue
        sub = labels[slc] == lbl
        volume = int(sub.sum())

        # bbox(排他的 stop)。
        z0, y0, x0 = (s.start for s in slc)
        z1, y1, x1 = (s.stop for s in slc)
        bbox = (int(z0), int(y0), int(x0), int(z1), int(y1), int(x1))
        bbox_vol = (z1 - z0) * (y1 - y0) * (x1 - x0)
        extent = float(volume / bbox_vol) if bbox_vol > 0 else 0.0

        # サブボリューム内座標 -> グローバル座標へオフセット。
        local = np.argwhere(sub)
        offset = np.array([z0, y0, x0], dtype=np.float64)
        coords = local.astype(np.float64) + offset
        centroid = tuple(float(c) for c in coords.mean(axis=0))

        axes, lengths = _principal_analysis(coords)

        equivalent_radius = float((3.0 * volume / (4.0 * np.pi)) ** (1.0 / 3.0))

        surf = _surface_area(sub)
        # 等体積球の表面積 = π^(1/3) (6V)^(2/3)。
        sphere_area = float(np.pi ** (1.0 / 3.0) * (6.0 * volume) ** (2.0 / 3.0))
        sphericity = float(sphere_area / surf) if surf > 0 else 0.0

        props.append(
            {
                "label": int(lbl),
                "volume": volume,
                "centroid": centroid,
                "bbox": bbox,
                "extent": extent,
                "principal_axes": axes,
                "principal_lengths": lengths,
                "equivalent_radius": equivalent_radius,
                "surface_area": int(surf),
                "sphericity": sphericity,
            }
        )
    return props


def largest_component(vol, connectivity: int = 26) -> np.ndarray:
    """最大(最多ボクセル)連結成分の bool マスクを返す。

    前景が無い場合は全 False マスク(vol と同形状)。

    補足:
    - 内部で ``label_components`` を呼び、``bincount`` でラベルごとのボクセル数を数えて最大を選ぶ。**同数のときは番号の小さいラベル**(scipy の走査順で先)が勝つ。
    - 入力は 0 以外を前景として ``bool`` 化する(NaN も前景)。軸順は (z, y, x)。
    - 返り値は入力と同形状の bool。前景が無ければ全 False(例外にはしない)。
    - Raises ``ValueError``: 3 次元でない入力、``connectivity`` が 6/18/26 以外。
    - 典型: 閾値処理で出た二値ボリュームからノイズ塊を捨てて主対象だけ残す。複数を残したいなら ``filter_by_volume``、特徴で選ぶなら ``vol_select_labels``。
    """
    arr = _as_binary_3d(vol)
    labels, n = label_components(arr, connectivity=connectivity)
    if n == 0:
        return np.zeros(arr.shape, dtype=bool)
    # ラベル 1..n の出現数(bincount[0] は背景なので無視)。
    counts = np.bincount(labels.ravel(), minlength=n + 1)
    counts[0] = 0
    winner = int(np.argmax(counts))
    return labels == winner


def filter_by_volume(vol, min_voxels: int, connectivity: int = 26) -> np.ndarray:
    """min_voxels 未満の連結成分を除去した bool マスクを返す。

    Parameters
    ----------
    vol : array_like
        bool または 0/1 の 3D 配列。
    min_voxels : int
        この閾値「未満」(< min_voxels)の成分を落とす。閾値 "以上" は残す。
    connectivity : int
        6 / 18 / 26。

    Returns
    -------
    ndarray(bool)
        条件を満たす成分のみ True。前景無しや全成分除去なら全 False。

    補足:
    - ``min_voxels`` は ``int()`` で丸めてから比較する。1 以下ならすべての成分が残る。
    - 内部で ``label_components`` → ``bincount`` → ``counts >= min_voxels`` のラベルを残す。ラベルの再番号付けは行わず bool マスクだけ返すので、番号が要るなら結果をもう一度 ``label_components`` に通す。
    - 入力は 0 以外を前景として bool 化する(NaN も前景)。軸順 (z, y, x)。
    - Raises ``ValueError``: 3 次元でない入力、``connectivity`` が 6/18/26 以外。
    - ボクセル数はスペーシング未補正なので、実寸で閾値を切るなら voxel 体積で割ってから渡す。
    """
    arr = _as_binary_3d(vol)
    labels, n = label_components(arr, connectivity=connectivity)
    if n == 0:
        return np.zeros(arr.shape, dtype=bool)
    counts = np.bincount(labels.ravel(), minlength=n + 1)
    # 残すラベル(閾値以上)。背景 0 は常に除外。
    keep = np.zeros(n + 1, dtype=bool)
    keep_labels = np.where(counts >= int(min_voxels))[0]
    keep[keep_labels] = True
    keep[0] = False
    return keep[labels]


# --------------------------------------------------------------------------- #
# 最大内接ボックス(inner_rectangle1 の 3-D 版)                                #
# --------------------------------------------------------------------------- #
def _max_all_ones_rect(m: np.ndarray):
    """2-D bool 配列の中で全 True の最大軸平行長方形を返す (top,left,bottom,right)。
    ヒストグラム/スタック法 = 2-D ``inner_rectangle1`` と同じコア(O(H*W))。前景無しは None。"""
    h, w = m.shape
    if not m.any():
        return None
    height = np.zeros(w, dtype=np.int64)
    best = None                                           # (area, top, left, bottom, right)
    for r in range(h):
        height = np.where(m[r], height + 1, 0)
        stack = []                                        # (start_col, bar_height)
        for i in range(w + 1):
            cur = int(height[i]) if i < w else 0
            start = i
            while stack and stack[-1][1] > cur:
                idx, hgt = stack.pop()
                area = hgt * (i - idx)
                if hgt > 0 and (best is None or area > best[0]):
                    best = (area, r - hgt + 1, idx, r, i - 1)
                start = idx
            stack.append((start, cur))
    if best is None:
        return None
    return (best[1], best[2], best[3], best[4])


def inner_box3(vol) -> dict:
    """二値ボクセル領域に完全に内接する最大の軸平行ボックス(2-D ``inner_rectangle1`` の
    3-D 版)。

    厳密解: どの深さ区間 [z0, z1] についても、ボックスはスライス z0..z1 の **論理積**
    (全スライスで前景のボクセル)の内側に無ければならない。その積の中の最大内接 2-D 長方形
    (ヒストグラム法 = ``inner_rectangle1`` と同じコア)× 区間長 が候補ボックスで、全区間に
    ついての最大が厳密な最大内接ボックスになる。O(D^2 * H * W)。

    Returns
    -------
    dict
        (depth,row,col) 軸順で ``min`` / ``max`` 隅、``center`` (+ ``cd/cr/cc``)、
        全幅 ``size``、ボクセル数の ``volume``。

    Raises
    ------
    ValueError
        非 3-D 入力、または前景ゼロの領域(内接ボックス無し)。

    補足:
    - ``min`` / ``max`` は **両端を含む** ボクセル添字(float 配列)。``size = max - min + 1``、``volume = prod(size)``。``center`` は ``(min + max) / 2`` で .5 が付き得る。2-D 側の登録名は ``r2_inner_rectangle1``。
    - 深さ区間ごとに Python ループで最大長方形を探す O(D²·H·W)。積が空になった時点でその z0 の探索は打ち切る。大きなボリュームでは遅い。
    - 同体積の候補が複数あるときは先に見つかったもの(z0 が小さく、その中で z1 が小さい)を返す。
    - 入力は 0 以外を前景として bool 化する(NaN も前景)。軸順は (depth, row, col)。
    - 典型: ``largest_component`` で対象を 1 つに絞ってから呼ぶ(複数成分が混ざると最大成分のボックスとは限らない)。
    """
    m = _as_binary_3d(vol)
    D = m.shape[0]
    if not m.any():
        raise ValueError("region is empty (zero foreground). Inner box is undefined.")
    best = None                                           # (vol, z0, z1, top, left, bottom, right)
    for z0 in range(D):
        acc = m[z0].copy()
        for z1 in range(z0, D):
            if z1 > z0:
                acc &= m[z1]
            rect = _max_all_ones_rect(acc)
            if rect is None:                              # 積が空 → これ以上伸ばしても空
                break
            top, left, bottom, right = rect
            hh, ww, dd = bottom - top + 1, right - left + 1, z1 - z0 + 1
            v = dd * hh * ww
            if best is None or v > best[0]:
                best = (v, z0, z1, top, left, bottom, right)
    v, z0, z1, top, left, bottom, right = best
    mn = np.array([z0, top, left], float)
    mx = np.array([z1, bottom, right], float)
    size = mx - mn + 1.0
    center = 0.5 * (mn + mx)
    return {"min": mn, "max": mx, "center": center,
            "cd": float(center[0]), "cr": float(center[1]), "cc": float(center[2]),
            "size": size, "volume": float(np.prod(size))}
