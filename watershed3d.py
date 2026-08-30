# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""watershed3d — 接触した物体の分離(距離変換シードの分水嶺・skimage 不要フォールバック付き)。

連結成分ラベリング(``regionprops3d.label_components`` / ``volops.vol_label``)は「背景で
分断された塊」しか分けられない。CT や粉体・細胞・封入物では**物体どうしが接触(または
僅かに重なる)**ため、連結成分では複数物体が 1 個に融合してしまい、個数も個々の重心・
体積も測れない。距離変換ベースの分水嶺(watershed)はこの融合を割る:

1. 前景の**距離変換**で各物体の芯(背景から最も遠い点)を作る。
2. 距離場の**局所極大**を最小間隔 ``min_distance`` の非最大抑制(NMS)で 1 物体 1 個に
   間引いてシード(マーカ)にする。
3. **反転した距離場 −dist の上で** マーカから分水嶺を流し、前景内を各マーカの集水域
   (catchment basin)に割り当てる。接触面(距離の谷=尾根線)が自然な切断面になる。

────────────────────────────────────────────────────────────────────────────
本モジュールの立ち位置(genuinely-new の正直な開示)
────────────────────────────────────────────────────────────────────────────
上記 3 ステップの**部品は fullseye 公開 API(``volops`` / ``api``)に既に存在する**:

  - ステップ 1 = :func:`volops.vol_distance_transform`
  - ステップ 2 = :func:`volops.vol_local_maxima`(min_distance 半径の極大検出)
  - ステップ 3 = :func:`volops.vol_watershed`(``skimage.segmentation.watershed`` 委譲。
    その docstring 自身が「the negated distance transform for splitting touching blobs」と
    まさにこの用途を明記している)

したがって「距離変換シードで接触物体を割る」機能そのものは公開 API と**実質重複**であり、
本モジュールはそれをゼロから再実装するものではない。``distance_peaks`` / ``watershed_vol``
は上記 3 op の**薄い合成**として実装している(EDT・極大検出・分水嶺の本体は公開 op を呼ぶ)。

本モジュールが公開 API に対して**真に新規**に足しているのは次の 2 点のみ(=増分):

  (A) **skimage 不要の純 scipy フォールバック**(``_nearest_marker_labels``)。公開の
      :func:`volops.vol_watershed` は skimage 不在で ``ImportError`` を送出し**フォールバック
      を持たない**。本モジュールは ``distance_transform_edt(return_indices=True)`` による
      前景限定の一般化ボロノイ分割(各前景ボクセルを最近傍マーカへ)を用意し、numpy+scipy
      だけで接触分離を完遂できる(``method="scipy"`` / ``method="auto"`` の skimage 不在時)。
  (B) **1 呼び出しの自動シード分離**(``separate_touching``)。距離変換→極大 NMS シード化→
      分水嶺という定型パイプラインを 1 関数に畳んだ薄いラッパ。公開 API では 3 op を手で
      繋ぐ必要があるところを、常用ケース向けに 1 コールで提供する。

薄い合成グルーとして残るのは「極大**座標**(``vol_local_maxima`` の (N,3) 出力)を int の
**マーカラベル配列**へ変換し、平坦域/近接重複を ``min_distance`` の NMS で 1 物体 1 シードに
畳む」処理のみ。これは公開 op が返さない形式変換であり、EDT/極大/分水嶺の再実装ではない。

バックエンド(``method``):
  - ``"skimage"`` … :func:`volops.vol_watershed`(尾根線を辿る正統な分水嶺)。
  - ``"scipy"``   … 上記 (A) の純 scipy フォールバック。凸物体の接触分離では skimage と
    ほぼ同一の切断面を与える。honest な限界: マスク内のくびれや障壁を辿らない(純幾何の
    最近傍)ため、強い非凸・L 字・環状が接触した病的形状では skimage 版より切断がずれ得る。
  - ``"auto"``    … skimage があれば使い、無ければ scipy にフォールバック。

依存: numpy と scipy.ndimage(前提、``volops`` 経由)。skimage は optional
(``method="scipy"`` なら不要)。座標系: 全て numpy 配列軸順 (z, y, x)。

honest な制約:
  - 距離変換の極大がシードなので、**中心が 1 つに見える形状**(球・楕円体・凸塊)に最適。
    細長い/湾曲した物体は芯が伸びて複数極大に割れ得る(``min_distance`` を大きくして抑制)。
  - ``min_distance`` は物体間隔より小さく、物体内のノイズ極大の間隔より大きく取る。小さすぎる
    と過分割(1 物体が複数ラベル)、大きすぎると過統合(2 物体が 1 ラベル)になる。
  - ボクセル体積・重心は離散近似(``regionprops3d`` / ``volops.vol_region_props`` と同じ
    離散化誤差)。僅かに重なった 2 物体では重なり領域が分水嶺線で 2 分されるため、各ラベル
    体積は単体からその折半分だけ目減りする(重なりが薄いほど誤差は小さい)。
"""
from __future__ import annotations

from typing import Optional

import numpy as np

try:
    # 純 scipy ボロノイ・フォールバック (A) だけが return_indices 付き EDT を直接必要とする。
    # EDT / 極大検出 / 分水嶺の本体は volops 公開 op に委譲する(下の import 参照)。
    from scipy.ndimage import distance_transform_edt as _edt_indices
except ImportError as exc:  # pragma: no cover - scipy は前提だが明示的に失敗させる
    raise ImportError(
        "watershed3d requires scipy.ndimage "
        "(`from scipy.ndimage import distance_transform_edt`)."
    ) from exc

# 距離変換・局所極大・分水嶺の本体は fullseye 公開 API を再利用する(ゼロから再実装しない)。
from volops import (  # noqa: E402
    vol_distance_transform as _vol_distance_transform,
    vol_local_maxima as _vol_local_maxima,
    vol_watershed as _vol_watershed,
)

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
            f"a 3D voxel array (ndim==3) is required but got ndim={arr.ndim}."
        )
    if not np.all(np.isfinite(arr)):
        raise ValueError("input volume contains NaN/Inf (degenerate input).")
    return arr.astype(bool, copy=False)


def _as_marker_3d(markers, shape: tuple[int, int, int]) -> np.ndarray:
    """外部指定マーカを int の 3D ラベル配列へ検証(0=シード無し, >0=シードラベル)。"""
    m = np.asarray(markers)
    if m.shape != shape:
        raise ValueError(
            f"markers must have the same shape as the volume {shape} but got {m.shape}."
        )
    if not np.all(np.isfinite(m)):
        raise ValueError("markers contains NaN/Inf.")
    m = m.astype(np.int64, copy=False)
    if m.min() < 0:
        raise ValueError("markers contains negative labels (0=background, 1..n=seeds).")
    return m


def _markers_from_peaks(dist: np.ndarray, min_distance: float) -> tuple[np.ndarray, list]:
    """距離場の局所極大シード(int マーカ配列)を **公開 op の薄い合成**で作る。

    極大検出そのものは :func:`volops.vol_local_maxima`(min_distance 半径のキューブ NMS)へ
    委譲する。本関数が足すのは公開 op が返さない後処理だけ:

      1. ``vol_local_maxima`` の返す (N,3) 座標のうち距離 > 0 のものを残す。
      2. 距離値の降順(芯の太い=確からしい順)に走査し、既採用点から ``min_distance`` 未満の
         ものを捨てる貪欲 NMS(平坦域で並ぶ複数極大を 1 物体 1 シードに畳む)。
      3. 採用シードを int ラベル配列 (0=無し, 1..k) に焼き込む。

    Returns:
        (markers, positions): markers は (Z,Y,X) int32。positions は採用シードの
        (z,y,x) 座標リスト(検証・描画用)。
    """
    md = float(min_distance)
    if md < 0:
        raise ValueError(f"min_distance must be non-negative (received: {min_distance}).")
    markers = np.zeros(dist.shape, dtype=np.int32)
    # vol_local_maxima は正整数の半径を要求する。min_distance をシード最小間隔として渡す
    # (0/端数は最小の 1 に丸めて strict 近傍 3x3x3 相当にする)。
    radius = max(1, int(round(md)))
    coords = _vol_local_maxima(dist, min_distance=radius)
    if len(coords) == 0:
        return markers, []
    vals = dist[coords[:, 0], coords[:, 1], coords[:, 2]]
    keep = vals > 0.0
    coords = coords[keep]
    vals = vals[keep]
    if len(coords) == 0:
        return markers, []
    order = np.argsort(vals)[::-1]                    # 芯の太い(=確からしい)順
    accepted: list[tuple[int, int, int]] = []
    for i in order:
        p = coords[i].astype(np.float64)
        if all(np.linalg.norm(p - np.asarray(a, dtype=np.float64)) >= md for a in accepted):
            accepted.append(tuple(int(v) for v in coords[i]))
    for k, (z, y, x) in enumerate(accepted, start=1):
        markers[z, y, x] = k
    return markers, accepted


def _nearest_marker_labels(markers: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """genuinely-new (A): skimage 不要の純 scipy フォールバック(一般化ボロノイ分割)。

    公開の :func:`volops.vol_watershed` は skimage 不在で ImportError になりフォールバックを
    持たない。本関数はマーカ以外のボクセルからマーカ集合への EDT を ``return_indices=True`` で
    取り、各ボクセルの最近傍マーカ座標→そのラベルを引く。前景マスク内だけ残す。凸物体の
    接触分離では分水嶺(−dist)の切断面とほぼ一致する(いずれも接触面の中線で割る)。
    """
    if not (markers > 0).any():
        return np.zeros(mask.shape, dtype=np.int32)
    non_marker = markers == 0
    _, inds = _edt_indices(non_marker, return_indices=True)
    nearest = markers[tuple(inds)]
    return np.where(mask, nearest, 0).astype(np.int32)


def _skimage_watershed(dist: np.ndarray, markers: np.ndarray,
                       mask: np.ndarray) -> np.ndarray:
    """skimage 版は公開 op :func:`volops.vol_watershed` に委譲する(反転距離場 −dist 上で
    マーカから分水嶺を流す)。skimage 不在なら vol_watershed が ImportError を送出する。"""
    return _vol_watershed(-dist, markers=markers, mask=mask).astype(np.int32)


# --------------------------------------------------------------------------- #
# 公開 op(いずれも volops 公開 op の薄い合成)                                   #
# --------------------------------------------------------------------------- #
def distance_peaks(binary, min_distance: float = 1.0) -> np.ndarray:
    """前景距離変換の局所極大を ``min_distance`` NMS で間引いた int マーカ配列を返す。

    :func:`volops.vol_distance_transform` + :func:`volops.vol_local_maxima` の薄い合成に、
    「極大座標→ラベル配列(1 物体 1 シード)」の後処理を足したもの(``watershed_vol`` が
    内部で使うシード生成を単体で公開=可視化・検証用)。

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
    dist = _vol_distance_transform(mask)             # 公開 op に委譲
    markers, _ = _markers_from_peaks(dist, min_distance)
    return markers


def watershed_vol(binary, markers: Optional[np.ndarray] = None,
                  min_distance: float = 1.0, method: str = "auto") -> np.ndarray:
    """距離変換シードの分水嶺で 3D 前景を物体ごとのラベルに分割する(公開 op の薄い合成)。

    連結成分では 1 個に融合する**接触/僅かな重なり**を割るのが目的。EDT は
    :func:`volops.vol_distance_transform`、skimage 分水嶺は :func:`volops.vol_watershed` に
    委譲し、本モジュールは (A) skimage 不在時の純 scipy フォールバックと、シード自動生成の
    グルーだけを足す。``markers`` を省略すると距離変換の局所極大(``min_distance`` NMS)を
    自動シードにする。

    Parameters
    ----------
    binary : array_like
        bool または 0/1 の 3D 前景ボリューム。
    markers : ndarray or None
        シードを外部指定する場合の int ラベル配列(binary と同形状、0=無し, 1..n=シード)。
        None なら距離変換の極大から自動生成する。
    min_distance : float
        ``markers=None`` のときのシード最小間隔(voxel)。
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
            f"method must be one of 'auto'/'skimage'/'scipy' (received: {method!r})."
        )
    mask = _as_binary_3d(binary)
    if not mask.any():
        return np.zeros(mask.shape, dtype=np.int32)

    dist = _vol_distance_transform(mask)             # 公開 op に委譲
    if markers is None:
        markers, _ = _markers_from_peaks(dist, min_distance)
    else:
        markers = _as_marker_3d(markers, mask.shape).astype(np.int32)
        markers = np.where(mask, markers, 0).astype(np.int32)  # 前景外シードは無効化

    if not (markers > 0).any():
        # シードが 1 つも立たない(前景はあるが極大が抽出できない)→ 全体を単一ラベルに。
        return mask.astype(np.int32)

    if method == "skimage":
        return _skimage_watershed(dist, markers, mask)
    if method == "scipy":
        return _nearest_marker_labels(markers, mask)
    # auto: skimage を試し、不在時は scipy フォールバック
    try:
        return _skimage_watershed(dist, markers, mask)
    except ImportError:
        return _nearest_marker_labels(markers, mask)


def separate_touching(binary, min_distance: float = 5.0,
                      method: str = "auto") -> np.ndarray:
    """genuinely-new (B): 接触物体を 1 呼び出しで自動分離する常用ラッパ。

    「複数物体が接触して 1 連結成分に融合している」典型ケースを、距離変換→極大 NMS シード化→
    分水嶺という定型パイプラインを畳んで 1 コールで割る(公開 API では 3 op を手で繋ぐ必要が
    あるところを常用ケース向けに 1 関数化)。中身は ``watershed_vol(..., markers=None)``。

    Parameters
    ----------
    binary : array_like
        bool または 0/1 の 3D 前景ボリューム。
    min_distance : float
        分離シードの最小間隔(voxel)。想定物体半径程度が目安。
    method : {"auto", "skimage", "scipy"}
        バックエンド選択。

    Returns
    -------
    labels : ndarray(int32)
        binary と同形状。背景 0、分離された各物体に 1..k のラベル。
    """
    return watershed_vol(
        binary, markers=None, min_distance=min_distance, method=method,
    )
