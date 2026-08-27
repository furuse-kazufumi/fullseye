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
        "regionprops3d は scipy.ndimage を必要とします "
        "(`from scipy.ndimage import label, find_objects`)。"
    ) from exc

__all__ = [
    "label_components",
    "region_props",
    "largest_component",
    "filter_by_volume",
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
            f"3D ボクセル配列 (ndim==3) が必要ですが ndim={arr.ndim} を受け取りました。"
        )
    return arr.astype(bool, copy=False)


def _structure(connectivity: int) -> np.ndarray:
    """connectivity(6/18/26)に対応する 3x3x3 の構造要素を返す。"""
    try:
        rank = _CONNECTIVITY_RANK[int(connectivity)]
    except (KeyError, ValueError, TypeError):
        raise ValueError(
            f"connectivity は 6 / 18 / 26 のいずれかである必要があります "
            f"(受け取った値: {connectivity!r})。"
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
