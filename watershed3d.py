# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""watershed3d — 接触した物体の分離(3D watershed / distance-transform シード分水嶺)。

連結成分ラベリング(``regionprops3d.label_components``)は「背景で分断された塊」しか
分けられない。CT や粉体・細胞・封入物では**物体どうしが接触(または僅かに重なる)**ため、
連結成分では複数物体が 1 個に融合してしまい、個数も個々の重心・体積も測れない。

本モジュールは距離変換ベースの分水嶺(watershed)でこの融合を割る:

1. 前景の**距離変換**(``distance_transform_edt``)を取る。凸物体では各物体の中心付近が
   極大になる(背景から最も遠い=芯)。
2. 距離場の**局所極大**を、最小間隔 ``min_distance`` の非最大抑制(NMS)で 1 物体 1 個に
   間引いてシード(マーカ)にする。
3. **反転した距離場 −dist の上で** マーカから分水嶺を流し、前景マスク内を各マーカの
   集水域(catchment basin)に割り当てる。接触面(距離の谷=尾根線)が自然な切断面になる。

バックエンドは 2 系統(``method``):
  - ``"skimage"`` … ``skimage.segmentation.watershed(-dist, markers, mask)``(尾根線を辿る
    正統な分水嶺。マスク境界と物体内部のくびれを尊重する)。
  - ``"scipy"``   … skimage 不在時の**純 scipy フォールバック**。マーカ集合への
    ``distance_transform_edt(return_indices=True)`` で各前景ボクセルを**最近傍マーカ**へ
    割り当てる(前景に制限した一般化ボロノイ分割)。凸物体の接触分離では skimage と
    ほぼ同一の切断面を与える。honest な限界: マスク内のくびれや障壁を辿らない(純幾何の
    最近傍)ため、強い非凸・L 字・環状が接触した病的形状では skimage 版より切断がずれ得る。
  - ``"auto"``    … skimage があれば使い、無ければ scipy にフォールバック。

依存: numpy と scipy.ndimage(前提)。skimage は optional(``method="scipy"`` なら不要)。
座標系: 全て numpy 配列軸順 (z, y, x)。

honest な制約:
  - 距離変換の極大がシードなので、**中心が 1 つに見える形状**(球・楕円体・凸塊)に最適。
    細長い/湾曲した物体は芯が伸びて複数極大に割れ得る(``min_distance`` を大きくして抑制)。
  - ``min_distance`` は物体間隔より小さく、物体内のノイズ極大の間隔より大きく取る。小さすぎる
    と過分割(1 物体が複数ラベル)、大きすぎると過統合(2 物体が 1 ラベル)になる。
  - ボクセル体積・重心は離散近似(``regionprops3d`` と同じ離散化誤差)。僅かに重なった
    2 物体では重なり領域が分水嶺線で 2 分されるため、各ラベル体積は単体からその折半分だけ
    目減りする(重なりが薄いほど誤差は小さい)。
"""
from __future__ import annotations

from typing import Optional

import numpy as np

try:
    from scipy.ndimage import distance_transform_edt as _edt
    from scipy.ndimage import maximum_filter as _max_filter
    from scipy.ndimage import label as _label
    from scipy.ndimage import maximum_position as _max_pos
    from scipy.ndimage import maximum as _nd_max
    from scipy.ndimage import generate_binary_structure as _gen_struct
except ImportError as exc:  # pragma: no cover - scipy は前提だが明示的に失敗させる
    raise ImportError(
        "watershed3d は scipy.ndimage を必要とします "
        "(`from scipy.ndimage import distance_transform_edt, maximum_filter, label`)。"
    ) from exc

__all__ = [
    "watershed_vol",
    "separate_touching",
    "distance_peaks",
]


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
    if not np.all(np.isfinite(arr)):
        raise ValueError("入力ボリュームに NaN/Inf が含まれています(退化入力)。")
    return arr.astype(bool, copy=False)


def _as_marker_3d(markers, shape: tuple[int, int, int]) -> np.ndarray:
    """外部指定マーカを int の 3D ラベル配列へ検証(0=シード無し, >0=シードラベル)。"""
    m = np.asarray(markers)
    if m.shape != shape:
        raise ValueError(
            f"markers はボリュームと同形状 {shape} が必要ですが {m.shape} を受け取りました。"
        )
    if not np.all(np.isfinite(m)):
        raise ValueError("markers に NaN/Inf が含まれています。")
    m = m.astype(np.int64, copy=False)
    if m.min() < 0:
        raise ValueError("markers に負のラベルが含まれています(0=背景, 1..n=シード)。")
    return m


def _peak_markers(dist: np.ndarray, min_distance: float) -> tuple[np.ndarray, list]:
    """距離場の局所極大を最小間隔 ``min_distance`` の NMS で間引き、int マーカ配列を作る。

    手順: (1) 3x3x3 の strict 局所極大(平坦域は連結してまとめる)を候補にする。
    (2) 26 連結で候補をラベリングし、各成分の「距離最大位置」を代表点にする。
    (3) 代表点を距離値の降順に走査し、既採用点から ``min_distance`` 未満のものを捨てる
    (peak_local_max と同じ非最大抑制)。

    Returns:
        (markers, positions): markers は (Z,Y,X) int(0=無し, 1..k=シード)。
        positions は採用したシードの (z,y,x) 座標リスト(検証・描画用)。
    """
    if float(min_distance) < 0:
        raise ValueError(f"min_distance は非負が必要です(受領: {min_distance})。")
    mx = _max_filter(dist, size=3, mode="constant", cval=0.0)
    peaks = (dist == mx) & (dist > 0.0)
    markers = np.zeros(dist.shape, dtype=np.int32)
    if not peaks.any():
        return markers, []
    struct = _gen_struct(3, 3)                       # 26 連結で平坦な極大域をまとめる
    lab, n = _label(peaks, structure=struct)
    idx = list(range(1, n + 1))
    positions = _max_pos(dist, lab, index=idx)       # 各成分の距離最大位置
    if n == 1:
        positions = [positions]                      # scipy は単一時にタプルを返す
    vals = _nd_max(dist, lab, index=idx)
    vals = np.atleast_1d(np.asarray(vals, dtype=np.float64))
    order = np.argsort(vals)[::-1]                    # 芯の太い(=確からしい)順
    accepted: list[tuple[int, int, int]] = []
    md = float(min_distance)
    for i in order:
        p = np.asarray(positions[i], dtype=np.float64)
        if all(np.linalg.norm(p - np.asarray(a)) >= md for a in accepted):
            accepted.append(tuple(int(round(v)) for v in positions[i]))
    for k, (z, y, x) in enumerate(accepted, start=1):
        markers[z, y, x] = k
    return markers, accepted


def _nearest_marker_labels(markers: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """純 scipy フォールバック: 前景を最近傍マーカへ割り当てる(一般化ボロノイ分割)。

    マーカ以外のボクセルからマーカ集合への EDT を ``return_indices=True`` で取り、各ボクセルの
    最近傍マーカ座標→そのラベルを引く。前景マスク内だけ残す。凸物体の接触分離では分水嶺
    (−dist)の切断面とほぼ一致する(いずれも接触面の中線で割る)。
    """
    if not (markers > 0).any():
        return np.zeros(mask.shape, dtype=np.int32)
    non_marker = markers == 0
    _, inds = _edt(non_marker, return_indices=True)
    nearest = markers[tuple(inds)]
    return np.where(mask, nearest, 0).astype(np.int32)


def _skimage_watershed(dist: np.ndarray, markers: np.ndarray,
                       mask: np.ndarray, connectivity: int) -> np.ndarray:
    """skimage 版: 反転距離場 −dist 上でマーカから分水嶺を流す。skimage 不在なら ImportError。"""
    from skimage.segmentation import watershed as _ws  # optional 依存
    lab = _ws(-dist, markers=markers, mask=mask, connectivity=connectivity)
    return lab.astype(np.int32)


# --------------------------------------------------------------------------- #
# 公開 op                                                                       #
# --------------------------------------------------------------------------- #
def distance_peaks(binary, min_distance: float = 1.0) -> np.ndarray:
    """前景の距離変換の局所極大を ``min_distance`` の NMS で間引いた int マーカ配列を返す。

    ``watershed_vol`` が内部で使うシード生成を単体で公開したもの(可視化・検証用)。

    Parameters
    ----------
    binary : array_like
        bool または 0/1 の 3D 前景ボリューム。
    min_distance : float
        採用シード間の最小ユークリッド距離(voxel)。物体間隔より小さく、物体内ノイズ極大の
        間隔より大きく取る。

    Returns
    -------
    markers : ndarray(int32)
        binary と同形状。0=シード無し、1..k=各シードラベル。
    """
    mask = _as_binary_3d(binary)
    if not mask.any():
        return np.zeros(mask.shape, dtype=np.int32)
    dist = _edt(mask)
    markers, _ = _peak_markers(dist, min_distance)
    return markers


def watershed_vol(binary, markers: Optional[np.ndarray] = None,
                  min_distance: float = 1.0, connectivity: int = 1,
                  method: str = "auto") -> np.ndarray:
    """距離変換シードの分水嶺で 3D 前景を物体ごとのラベルに分割する。

    連結成分では 1 個に融合する**接触/僅かな重なり**を割るのが目的。``markers`` を省略すると
    距離変換の局所極大(``min_distance`` NMS)を自動シードにする。

    Parameters
    ----------
    binary : array_like
        bool または 0/1 の 3D 前景ボリューム。
    markers : ndarray or None
        シードを外部指定する場合の int ラベル配列(binary と同形状、0=無し, 1..n=シード)。
        None なら距離変換の極大から自動生成する。
    min_distance : float
        ``markers=None`` のときのシード最小間隔(voxel)。
    connectivity : int
        skimage 分水嶺の連結性(1=面, 3=面+辺+角)。scipy フォールバックでは未使用。
    method : {"auto", "skimage", "scipy"}
        バックエンド選択。"skimage" 指定で不在なら fail-closed(ImportError)。

    Returns
    -------
    labels : ndarray(int32)
        binary と同形状。背景 0、各物体に 1..k のラベル(前景を過不足なく被覆)。

    Raises
    ------
    ValueError
        形状不正・退化入力・不正 method のとき(fail-closed)。
    """
    if method not in ("auto", "skimage", "scipy"):
        raise ValueError(
            f"method は 'auto'/'skimage'/'scipy' のいずれか(受領: {method!r})。"
        )
    mask = _as_binary_3d(binary)
    if not mask.any():
        return np.zeros(mask.shape, dtype=np.int32)

    dist = _edt(mask)
    if markers is None:
        markers, _ = _peak_markers(dist, min_distance)
    else:
        markers = _as_marker_3d(markers, mask.shape).astype(np.int32)
        markers = np.where(mask, markers, 0).astype(np.int32)  # 前景外シードは無効化

    if not (markers > 0).any():
        # シードが 1 つも立たない(前景はあるが極大が抽出できない)→ 全体を単一ラベルに。
        return mask.astype(np.int32)

    if method == "skimage":
        return _skimage_watershed(dist, markers, mask, connectivity)
    if method == "scipy":
        return _nearest_marker_labels(markers, mask)
    # auto: skimage を試し、不在時は scipy フォールバック
    try:
        return _skimage_watershed(dist, markers, mask, connectivity)
    except ImportError:
        return _nearest_marker_labels(markers, mask)


def separate_touching(binary, min_distance: float = 5.0,
                      connectivity: int = 1, method: str = "auto") -> np.ndarray:
    """接触した物体を距離変換シードの分水嶺で自動分離する(``watershed_vol`` の常用ラッパ)。

    「複数物体が接触して 1 連結成分に融合している」典型ケースを 1 呼び出しで割る。距離変換の
    極大を ``min_distance`` の NMS でシード化し、分水嶺で各物体へ分割する。

    Parameters
    ----------
    binary : array_like
        bool または 0/1 の 3D 前景ボリューム。
    min_distance : float
        分離シードの最小間隔(voxel)。想定物体半径程度が目安。
    connectivity : int
        skimage 分水嶺の連結性(1=面, 3=面+辺+角)。
    method : {"auto", "skimage", "scipy"}
        バックエンド選択。

    Returns
    -------
    labels : ndarray(int32)
        binary と同形状。背景 0、分離された各物体に 1..k のラベル。
    """
    return watershed_vol(
        binary, markers=None, min_distance=min_distance,
        connectivity=connectivity, method=method,
    )
