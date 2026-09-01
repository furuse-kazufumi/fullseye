# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""volcolor — 3-D ラベルボリュームの**色分け**(colour-coded voxel labelling)。

:mod:`volops` は ``vol_label`` で 3-D 連結成分を、``vol_region_props`` で成分ごとの
定量値を出せるようになった。ところが**色を付ける手段は 2-D しか無かった** ――
:func:`imgio.colorize_labels` は ``(H, W)`` のラベル画像を前提にしており、
ボリュームを見るには「1 枚ずつ切って、切った後で色を付ける」しかない。

その順序が実は致命的である。**切ってから色を付けると、スライスごとにラベル番号が
振り直されるので、同じ部品が層ごとに別の色になる**(ちらつく)。
先にボリュームで色を付けて後から切れば、同じ部品は最後まで同じ色のままになる。
本モジュールはその「先に色、後で切る」を 1 級の操作として持つ。

  * :func:`vol_label_color_flicker` はこの差を**数える** op である。左右に並べて
    「安定しています」と言うのではなく、色が変わった (成分, スライス) の組と、
    変化を含むスライスの本数を返す。この族の存在理由がそのまま測定量になっている。

パレット規約(**2-D と完全一致**):

  :func:`vol_label_palette` は :func:`imgio.colorize_labels` の内部と**同じ乱数列**を
  使う ―― ``np.random.default_rng(seed).random((n + 1, 3))`` の行 ``k`` が
  ラベル ``k`` の色で、行 0 は背景。PCG64 の列は逐次生成なので **``n`` が違っても
  先頭 ``k`` 行は同一**(実測で確認、``tests/test_volcolor.py::test_palette_prefix_is_stable``)。
  したがって「同じラベル番号・同じ seed なら 2-D でも 3-D でも同じ色」が成立し、
  ``tests/test_volcolor.py::test_matches_imgio_colorize_labels_exactly`` が
  ``np.array_equal`` で固定している。**この一致が崩れたらテストが落ちる**ので、
  片側だけ配色を変える改変は通らない。

フレーム規約(:mod:`volops` / :mod:`volio` と共有):

  ボリュームは ``(D, H, W)`` で ``[z, y, x]``、``spacing`` は ``(sz, sy, sx)`` mm。
  色付きボリュームは ``(D, H, W, 3)`` の float64、値域 ``[0, 1]``。
  **メッシュだけは (x, y, z) 順**で返る(``vol_labels_to_meshes`` の ``axes``
  既定 ``"xyz"``)―― :mod:`render3d` / :mod:`mesh` の頂点はその順だからで、
  黙って (z, y, x) を渡すと**例外なく上下と前後が入れ替わった絵**になる。
  引数で切り替えられるようにし、テストで両方の重心を突き合わせてある。

正直な限界(すべて ``tests/test_volcolor.py`` が測っている範囲):

  * **色は衝突しうる**。パレットは一様乱数なので、ラベル数が増えると近い色の対が
    必ず出る。実測(seed=0、RGB ユークリッド距離・取りうる最大は sqrt(3)=1.732):
    最近接色対の距離は 16 色で 0.1439、64 色で 0.0385、256 色で 0.0274。
    **色は識別子ではなく目印**であり、どの色がどの成分かは
    :func:`vol_label_legend` が返す表で読む。色だけの図を作らないこと。
  * **チャネルごとの最大値合成(MIP)は提供しない**。RGB ラベルボリュームを
    チャネル別に max すると、赤成分は部品 A・緑成分は部品 B から来た「どの部品にも
    属さない色」が出る。実測(3 成分が z 方向に重なる ``(16, 16, 16)``、seed=0):
    投影 ``(16, 16)`` の前景 168 画素のうち **90 画素**がパレットのどの行とも
    一致しない色になった。``mode="max"`` は :class:`ValueError` で拒否する
    (黙って混ぜない)。
  * **等方でない spacing を渡し忘れると体積も形状指標も狂う**。``spacing=None`` は
    「1 ボクセル = 1 単位」であって「mm」ではない。実測は
    :func:`vol_label_shape_stats` の docstring に。
  * **``labels.max()`` は成分数ではない**。番号に欠番があると max は成分数より大きい。
    本モジュールは常に ``np.bincount`` の非ゼロから**実在するラベル**を取る。
  * 表面積・Wadell 球形度は :func:`volops.vol_region_props` の担当で、ここでは
    再実装しない(``surface="auto"`` の marching cubes が要るため)。本モジュールの
    :func:`vol_label_shape_stats` は**線形時間で出せる量だけ**を返す。

fail-closed(untrusted 入力):3-D でない / 浮動小数のラベル / 負のラベル /
非有限 / ラベル最大値が :data:`MAX_LABELS` 超 / ボクセル数が上限超 / 範囲外の
``alpha`` ``index`` ``axis`` ``background`` ―― すべて**文書化された**
:class:`ValueError` を送出する。黙って clip も wrap もしない(2-D の
``colorize_labels`` は負ラベルを 0 に clip するが、3-D 側はそれを**継承しない**:
負ラベルは「ラベル付けの上流が壊れている」印なので、色を付けて隠さない)。

依存は numpy + scipy のみ。:func:`vol_labels_to_meshes` だけが marching cubes
(scikit-image、:mod:`render3d` 経由)を必要とし、不在なら明示的な
:class:`ImportError` を出す。

来歴(公開文献・公開実装のみ):

  * 連結成分ラベリング = ``scipy.ndimage.label``(Rosenfeld & Pfaltz, JACM 1966 の
    2 パス法の N 次元版)。本モジュールはラベリング自体は行わず :mod:`volops` に委ねる。
  * 主成分による形状指標(linearity / planarity / isotropy)= J. Demantké,
    C. Mallet, N. David, B. Vallet, "Dimensionality based scale selection in 3D
    LiDAR point clouds", ISPRS Workshop Laser Scanning 2011 の 3 次元特徴。
    共分散固有値 ``l1 >= l2 >= l3`` から ``(l1-l2)/l1`` ``(l2-l3)/l1`` ``l3/l1``。
  * 等価直径 = ``(6V/pi)**(1/3)``(球の直径、教科書式)。
  * front-to-back の α 合成 = T. Porter & T. Duff, "Compositing Digital Images",
    SIGGRAPH 1984 の ``over`` 演算子。
  * marching cubes = W. E. Lorensen & H. E. Cline, SIGGRAPH 1987(:mod:`render3d` 経由)。
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

import volops

__all__ = [
    "vol_label_palette", "vol_colorize_labels",
    "vol_label_slice_rgb", "vol_label_mpr_rgb",
    "vol_label_shape_stats", "vol_select_labels",
    "vol_label_overlay", "vol_label_legend",
    "vol_labels_to_meshes", "vol_label_volume_render",
    "vol_label_color_flicker",
    "VOLCOLOR", "MAX_LABELS", "MAX_COLOR_VOXELS", "MAX_MESHES",
]

#: 公開 op(introspection / facade 配線用)。
VOLCOLOR = [
    "vol_label_palette", "vol_colorize_labels",
    "vol_label_slice_rgb", "vol_label_mpr_rgb",
    "vol_label_shape_stats", "vol_select_labels",
    "vol_label_overlay", "vol_label_legend",
    "vol_labels_to_meshes", "vol_label_volume_render",
    "vol_label_color_flicker",
]

#: ラベル最大値の上限。パレットは ``(n+1, 3)`` float64 = **1 ラベル 24 バイト**を
#: 確保するので、``labels`` に 1 個でも巨大な値が混ざっていると(たとえ実在する
#: 成分が 2 つでも)確保だけで GB 級になる。``2**20`` で 25 MB。
#: **成分数ではなく最大値で切る**のが要点 —— 上流が壊れているのはまさに
#: 「実在は 2 個なのに番号が 10**9」という形で来る。
MAX_LABELS = 1 << 20

#: 色付きボリューム ``(D, H, W, 3)`` float64 = **1 ボクセル 24 バイト**を作る op
#: (:func:`vol_colorize_labels` / :func:`vol_label_overlay`)と、O(N) の座標
#: 一時配列を数本使う :func:`vol_label_shape_stats` の上限。``2**23`` ボクセル
#: (= 202**3 相当)で色ボリューム 201 MB。これを超えるものは ROI へ切るか
#: ``volops.volume_downsample`` で間引く(:mod:`volops` と同じ作法)。
MAX_COLOR_VOXELS = 1 << 23

#: :func:`vol_labels_to_meshes` が一度に返すメッシュ数の上限。1 成分ごとに
#: marching cubes を回すので、1 ボクセル 1 ラベルのような病的入力に対して
#: 素通しにすると時間もメモリも成分数に比例して膨らむ。
MAX_MESHES = 4096

_AXIS_ALIASES = {
    "z": 0, "axial": 0, "0": 0, 0: 0,
    "y": 1, "coronal": 1, "1": 1, 1: 1,
    "x": 2, "sagittal": 2, "2": 2, 2: 2,
}


# --------------------------------------------------------------------------- #
# fail-closed 入力ヘルパ                                                        #
# --------------------------------------------------------------------------- #
def _as_labels(labels, name: str = "labels", cap: int = None) -> np.ndarray:
    """``(D, H, W)`` の**整数**ラベルボリュームを int64 で返す、さもなくば ValueError。

    浮動小数のラベルは拒否する。``astype(int)`` で黙って丸めると ``2.7`` が
    ラベル 2 になり、「ラベル付けの出力ではない何か」を色分けした図が出来上がる。
    負のラベルも拒否する(2-D の ``colorize_labels`` は 0 に clip するが、
    それは壊れた上流を背景に見せる = 隠す動作である)。
    """
    L = np.asarray(labels)
    if L.ndim != 3:
        raise ValueError("%s must be a 3-D (D, H, W) label volume, got a %d-D array "
                         "of shape %r" % (name, L.ndim, tuple(L.shape)))
    if L.dtype.kind == "b":
        L = L.astype(np.int64)
    elif L.dtype.kind in "fc":
        raise ValueError("%s has a %s dtype — labels must be integers. A float label "
                         "volume is almost always an un-thresholded image; round or "
                         "threshold it explicitly (e.g. volops.vol_label(vol > 0.5))"
                         % (name, L.dtype))
    elif L.dtype.kind not in "iu":
        raise ValueError("%s must be an integer array, got dtype %s" % (name, L.dtype))
    L = np.ascontiguousarray(L, dtype=np.int64)
    if L.size == 0:
        raise ValueError("%s is empty (shape %r) — nothing to colour" % (name, L.shape))
    lo = int(L.min())
    if lo < 0:
        raise ValueError("%s has %d negative voxel(s) (minimum %d) — refusing. A "
                         "negative label means the upstream labelling is broken; "
                         "colouring it would hide that as background"
                         % (name, int((L < 0).sum()), lo))
    hi = int(L.max())
    if hi > MAX_LABELS:
        raise ValueError("%s: the largest label is %d, over the %d cap "
                         "(volcolor.MAX_LABELS) — the palette alone would need "
                         "%.1f MB. Note the cap is on the label *value*, not the "
                         "component count: a volume with 2 components numbered 1 and "
                         "10**9 hits it too (relabel with volops.vol_label first)"
                         % (name, hi, MAX_LABELS, (hi + 1) * 24 / 1e6))
    if cap is not None and L.size > cap:
        raise ValueError("%s: a %d-voxel volume (shape %r) exceeds the %d cap "
                         "(volcolor.MAX_COLOR_VOXELS) — crop to an ROI or "
                         "downsample first (volops.volume_downsample)"
                         % (name, L.size, L.shape, cap))
    return L


def _check_seed(seed) -> int:
    try:
        s = int(seed)
    except (TypeError, ValueError):
        raise ValueError("seed must be a non-negative integer, got %r" % (seed,)) from None
    if s != seed or s < 0:
        raise ValueError("seed must be a non-negative integer, got %r" % (seed,))
    return s


def _check_rgb(colour, name: str = "background") -> np.ndarray:
    c = np.asarray(colour, dtype=np.float64).reshape(-1)
    if c.size != 3:
        raise ValueError("%s must be 3 RGB components in [0, 1], got %r" % (name, colour))
    if not np.isfinite(c).all() or c.min() < 0.0 or c.max() > 1.0:
        raise ValueError("%s must be 3 finite RGB components in [0, 1], got %r"
                         % (name, colour))
    return c


def _check_axis(axis) -> int:
    key = axis.lower() if isinstance(axis, str) else axis
    if key not in _AXIS_ALIASES:
        raise ValueError("axis must be one of 'z'/'axial'/0, 'y'/'coronal'/1, "
                         "'x'/'sagittal'/2, got %r" % (axis,))
    return _AXIS_ALIASES[key]


def _check_unit(value, name: str) -> float:
    v = float(value)
    if not np.isfinite(v) or v < 0.0 or v > 1.0:
        raise ValueError("%s must be a finite number in [0, 1], got %r" % (name, value))
    return v


def _as_rgb_volume(rgbvol, name: str = "rgbvol") -> np.ndarray:
    """``(D, H, W, 3)`` float64・値域 ``[0, 1]`` の色ボリュームを検証して返す。

    値域を検査するのは、``[0, 255]`` のまま渡された配列を後段が uint8 へ落とすと
    **飽和して真っ白**になり、それが「明るい図」として通ってしまうからである。
    """
    A = np.asarray(rgbvol, dtype=np.float64)
    if A.ndim != 4 or A.shape[3] != 3:
        raise ValueError("%s must be a (D, H, W, 3) RGB volume, got shape %r"
                         % (name, tuple(A.shape)))
    if not np.isfinite(A).all():
        raise ValueError("%s has %d non-finite entry(ies) — refusing (they would "
                         "render as black and look like real dark structure)"
                         % (name, int((~np.isfinite(A)).sum())))
    if A.min() < 0.0 or A.max() > 1.0:
        raise ValueError("%s must lie in [0, 1] (got [%g, %g]) — a 0..255 volume "
                         "saturates to white when written as uint8, which reads as "
                         "a valid bright image" % (name, A.min(), A.max()))
    return np.ascontiguousarray(A)


def _present_labels(L: np.ndarray, n: int) -> tuple:
    """``(実在するラベル id (昇順), そのボクセル数)``。**max ではなく bincount** で
    数えるので、番号に欠番があっても成分数を取り違えない。"""
    counts = np.bincount(L.ravel(), minlength=n + 1)
    ids = np.nonzero(counts)[0]
    ids = ids[ids > 0]
    return ids.astype(np.int64), counts[ids].astype(np.int64)


# --------------------------------------------------------------------------- #
# パレット / 色付け                                                             #
# --------------------------------------------------------------------------- #
def vol_label_palette(n_labels, seed: int = 0, background=(0.0, 0.0, 0.0)):
    """ラベル ``0..n_labels`` の RGB パレット ``(n_labels + 1, 3)`` float64。

    :func:`imgio.colorize_labels` と**同じ乱数列**である ――
    ``np.random.default_rng(seed).random((n + 1, 3))`` の行 ``k`` がラベル ``k`` の
    色、行 0 は *background*(既定は黒 = 2-D 側と同一)。PCG64 の標本列は逐次
    生成なので ``n`` を増やしても先頭行は変わらず、**同じラベル番号・同じ seed なら
    2-D の 1 枚でも 3-D のボリュームでも色が一致する**。この一致は
    ``tests/test_volcolor.py`` が ``np.array_equal`` で固定している。

    実測(seed=0、RGB ユークリッド距離、取りうる最大は sqrt(3)=1.732):最近接の
    色対の距離は 16 色で 0.1439、64 色で 0.0385、256 色で 0.0274。**色は識別子では
    なく目印**であり、区別が要る図には :func:`vol_label_legend` の表を添える。

    Raises ``ValueError`` for a negative / non-integer *n_labels*, an *n_labels*
    over :data:`MAX_LABELS`, a negative *seed*, or a *background* outside [0, 1].
    """
    try:
        n = int(n_labels)
    except (TypeError, ValueError):
        raise ValueError("n_labels must be a non-negative integer, got %r"
                         % (n_labels,)) from None
    if n != n_labels or n < 0:
        raise ValueError("n_labels must be a non-negative integer, got %r" % (n_labels,))
    if n > MAX_LABELS:
        raise ValueError("n_labels=%d exceeds the %d cap (volcolor.MAX_LABELS) — the "
                         "palette alone would need %.1f MB"
                         % (n, MAX_LABELS, (n + 1) * 24 / 1e6))
    s = _check_seed(seed)
    bg = _check_rgb(background)
    rng = np.random.default_rng(s)
    cols = rng.random((n + 1, 3))
    cols[0] = bg
    return cols


def vol_colorize_labels(labels, seed: int = 0, background=(0.0, 0.0, 0.0)):
    """3-D ラベルボリューム -> ``(D, H, W, 3)`` float64 の RGB ボリューム。

    「切ってから色を付ける」のではなく「**色を付けてから切る**」ための入口。
    ラベル ``k`` の色は :func:`vol_label_palette` の行 ``k`` そのもので、
    ``imgio.colorize_labels(labels, seed)`` を同じ配列に対して呼んだ結果と
    **バイト単位で一致する**(``tests/test_volcolor.py`` が固定)。

    切る順序が効くこと自体は :func:`vol_label_color_flicker` が数える。実測
    (16 球・``(24, 48, 48)`` の参照ファントム、``connectivity=26``、seed=0):
    スライスごとに色を付け直すと **24 スライス中 20 スライス**で少なくとも
    1 成分の色が変わり、(成分, スライス) の変化は 108 組中 **62 件**、
    **16 成分すべて**が一度は色を変える。ボリュームで色を付けてから切ると
    3 つとも 0。

    Raises ``ValueError`` on a non-3-D, float, or negative label volume, on a label
    over :data:`MAX_LABELS`, or on more than :data:`MAX_COLOR_VOXELS` voxels.
    """
    L = _as_labels(labels, cap=MAX_COLOR_VOXELS)
    n = int(L.max())
    pal = vol_label_palette(n, seed=seed, background=background)
    return np.ascontiguousarray(pal[L])


# --------------------------------------------------------------------------- #
# 断面                                                                          #
# --------------------------------------------------------------------------- #
def vol_label_slice_rgb(rgbvol, index: int, axis="z"):
    """色付きボリュームから 1 枚の断面 RGB を取り出す(axial / coronal / sagittal)。

    *axis* は ``"z"``/``"axial"``/0(``(H, W, 3)`` が返る)、``"y"``/``"coronal"``/1
    (``(D, W, 3)``)、``"x"``/``"sagittal"``/2(``(D, H, 3)``)。**返る 2 軸が
    軸ごとに違う**のは ``(D, H, W)`` から 1 軸抜くのだから当然だが、``(H, W)`` を
    期待して受けると縦横が入れ替わった絵が例外なしに出る。3 通りの形は
    ``tests/test_volcolor.py::test_slice_axes_shapes_and_content`` が固定している。

    *index* は**非負**でなければならない。``-1`` を「最後の断面」として黙って
    受けると、範囲外の指定が最後の断面として通ってしまう(切り出す位置が
    1 箇所ずれた図は、機械にも目にも「壊れている」と見えない)。

    Returns a contiguous float64 ``(..., 3)`` copy. Raises ``ValueError`` for a bad
    volume, an unknown *axis*, or an out-of-range / negative *index*.
    """
    A = _as_rgb_volume(rgbvol)
    ax = _check_axis(axis)
    try:
        i = int(index)
    except (TypeError, ValueError):
        raise ValueError("index must be an integer, got %r" % (index,)) from None
    if i != index:
        raise ValueError("index must be an integer, got %r" % (index,))
    n = A.shape[ax]
    if i < 0 or i >= n:
        raise ValueError("index %d is out of range for axis %r (0 <= index < %d). "
                         "Negative indices are refused on purpose — wrapping would "
                         "turn an out-of-range request into a plausible slice"
                         % (i, axis, n))
    if ax == 0:
        sl = A[i, :, :, :]
    elif ax == 1:
        sl = A[:, i, :, :]
    else:
        sl = A[:, :, i, :]
    return np.ascontiguousarray(sl)


def vol_label_mpr_rgb(rgbvol, center=None, gap: int = 4,
                      background=(0.05, 0.05, 0.07)):
    """色付きボリュームの直交 3 断面を **1 枚の RGB** に並べた図を返す。

    左から axial ``(H, W)`` / coronal ``(D, W)`` / sagittal ``(D, H)``。*center* は
    ``(z, y, x)`` の交点(既定は各軸の中央)。パネルの高さは最大値へ *background*
    で下詰めパディングし、間に *gap* 画素の隙間を空ける。

    ラベル色が**ボリューム由来**であることがこの図の意味である ―― 3 面で同じ部品が
    同じ色に見えることが、3 断面が同じラベリングから来ている証拠になる
    (断面ごとに色を付け直した図では 3 面の色は一致しない)。

    Returns float64 ``(H_out, W_out, 3)``. Raises ``ValueError`` for a bad volume,
    a *center* outside the volume, or a negative *gap*.
    """
    A = _as_rgb_volume(rgbvol)
    D, H, W = A.shape[:3]
    if center is None:
        c = (D // 2, H // 2, W // 2)
    else:
        c = tuple(int(v) for v in np.asarray(center).reshape(-1))
        if len(c) != 3:
            raise ValueError("center must be (z, y, x), got %r" % (center,))
        for v, n, nm in zip(c, (D, H, W), "zyx"):
            if v < 0 or v >= n:
                raise ValueError("center %s=%d is outside the volume (0 <= %s < %d)"
                                 % (nm, v, nm, n))
    g = int(gap)
    if g < 0:
        raise ValueError("gap must be >= 0, got %r" % (gap,))
    bg = _check_rgb(background)

    panels = [vol_label_slice_rgb(A, c[0], "z"),
              vol_label_slice_rgb(A, c[1], "y"),
              vol_label_slice_rgb(A, c[2], "x")]
    ph = max(p.shape[0] for p in panels)
    pw = sum(p.shape[1] for p in panels) + g * (len(panels) - 1)
    out = np.tile(bg, (ph, pw, 1))
    x = 0
    for p in panels:
        out[:p.shape[0], x:x + p.shape[1], :] = p
        x += p.shape[1] + g
    return np.ascontiguousarray(out)


# --------------------------------------------------------------------------- #
# 形状統計 / 選別                                                               #
# --------------------------------------------------------------------------- #
def vol_label_shape_stats(labels, spacing=None, shape: bool = True):
    """成分ごとの**線形時間で出せる**定量値(体積・重心・箱・主成分形状指標)。

    :func:`volops.vol_region_props` の姉妹だが、**目的が違う**:

      * あちらは ``surface_area`` と Wadell ``sphericity`` を出す。そのために
        成分ごとに marching cubes を回すので、**成分数に比例して Python ループが
        回る**(1 ボクセル 1 ラベルの病的入力で急速に重くなる)。
      * こちらは ``np.bincount`` の重み付き総和だけで済む量に限る。ラベル配列 1 本
        あたり 9 回の ``bincount`` = **O(N + n)**。実測(``connectivity=26``、
        1 ボクセル 1 ラベルの市松模様):8**3=256 成分 0.0016 s / 16**3=2048 成分
        0.0032 s / 32**3=16384 成分 0.0125 s / 64**3=131072 成分 0.0923 s ――
        ボクセル数 512 倍に対して 57 倍(二次なら 26 万倍)。

    ``label`` ``voxel_count`` ``volume`` ``centroid`` ``bbox`` の 5 つは
    :func:`volops.vol_region_props` と**同一の定義・同一の値**である
    (``tests/test_volcolor.py::test_stats_agree_with_vol_region_props`` が
    厳密一致で固定)。``bbox`` は ``(z0, z1, y0, y1, x0, x1)`` で上限は排他的。

    加えて返すもの:

      ``centroid_mm`` ``(z, y, x)`` 物理座標(spacing 無しなら voxel と同値)·
      ``extent`` bbox の物理寸法 ``(dz, dy, dx)`` · ``equivalent_diameter``
      ``(6V/pi)**(1/3)`` · ``touches_border`` bbox がボリューム端に接するか ·
      ``principal_extent`` 共分散固有値の平方根 ``(s1 >= s2 >= s3)``(物理単位) ·
      ``linearity`` ``(l1-l2)/l1`` · ``planarity`` ``(l2-l3)/l1`` · ``isotropy``
      ``l3/l1`` · ``elongation`` ``sqrt(l1/l2)``。

    **``elongation`` は無限になりうる**(契約):``l1 > 0`` かつ ``l2 == 0``、
    すなわち厚み 1 ボクセルの完全な直線の成分では ``inf`` を返す。0 で割った事故
    ではなく「第 2 軸方向に広がりが無い」という事実であり、丸めると細長さの順位が
    黙って入れ替わる。単一ボクセル(``l1 == 0``)は等方な点なので ``1.0``。

    **spacing を渡し忘れると狂う**。実測(半径 6 ボクセルの球を ``spacing =
    (3.0, 1.0, 1.0)`` の異方格子に置いた場合):体積は 925 voxel 対 2775.0 mm**3
    で 3.000 倍、``isotropy`` は 0.9913(等方と読める)対 0.1088(扁平と読める)。
    数字も結論も変わる。

    *shape* を ``False`` にすると共分散(9 本のうち 6 本の bincount)を省き、
    ``principal_extent`` 以下の 5 項目を返さない ―― 体積フィルタしか要らない
    ときに O(N) の一時配列を 1 本に減らせる。

    Returns ``list[dict]`` in ascending label order (**実在するラベルのみ** ――
    番号に欠番があっても、``labels.max()`` ぶんの空 dict は返さない)。
    """
    L = _as_labels(labels, cap=MAX_COLOR_VOXELS)
    sp = volops._spacing_tuple(spacing)
    sz, sy, sx = (1.0, 1.0, 1.0) if sp is None else sp
    voxvol = float(sz * sy * sx)
    D, H, W = L.shape
    n = int(L.max())
    ids, counts = _present_labels(L, n)
    if ids.size == 0:
        return []

    flat = L.ravel()
    cnt = np.bincount(flat, minlength=n + 1).astype(np.float64)
    cnt_safe = np.where(cnt > 0, cnt, 1.0)

    # 座標(voxel index)を O(N) の重み配列にして bincount へ。broadcast_to().ravel()
    # は 1 度だけコピーする(ufunc.at のような要素ごとの Python 往復は無い)。
    zc = np.broadcast_to(np.arange(D, dtype=np.float64)[:, None, None], L.shape).ravel()
    yc = np.broadcast_to(np.arange(H, dtype=np.float64)[None, :, None], L.shape).ravel()
    xc = np.broadcast_to(np.arange(W, dtype=np.float64)[None, None, :], L.shape).ravel()
    s_z = np.bincount(flat, weights=zc, minlength=n + 1)
    s_y = np.bincount(flat, weights=yc, minlength=n + 1)
    s_x = np.bincount(flat, weights=xc, minlength=n + 1)
    mz, my, mx = s_z / cnt_safe, s_y / cnt_safe, s_x / cnt_safe

    if shape:
        # 物理単位の中心化座標で 2 次モーメント。spacing はここで効く。
        s_zz = np.bincount(flat, weights=zc * zc, minlength=n + 1)
        s_yy = np.bincount(flat, weights=yc * yc, minlength=n + 1)
        s_xx = np.bincount(flat, weights=xc * xc, minlength=n + 1)
        s_zy = np.bincount(flat, weights=zc * yc, minlength=n + 1)
        s_zx = np.bincount(flat, weights=zc * xc, minlength=n + 1)
        s_yx = np.bincount(flat, weights=yc * xc, minlength=n + 1)
        c_zz = (s_zz / cnt_safe - mz * mz) * (sz * sz)
        c_yy = (s_yy / cnt_safe - my * my) * (sy * sy)
        c_xx = (s_xx / cnt_safe - mx * mx) * (sx * sx)
        c_zy = (s_zy / cnt_safe - mz * my) * (sz * sy)
        c_zx = (s_zx / cnt_safe - mz * mx) * (sz * sx)
        c_yx = (s_yx / cnt_safe - my * mx) * (sy * sx)
    del zc, yc, xc, flat

    # bbox は find_objects(C 実装・1 パス)で。volops.vol_region_props と同じ定義。
    slices = ndimage.find_objects(L)

    out = []
    for lab in ids:
        i = int(lab)
        sl = slices[i - 1] if i - 1 < len(slices) else None
        if sl is None:                                  # 起きないはずだが黙らせない
            raise ValueError("label %d is present in the volume but find_objects "
                             "returned no bounding box — the label array changed "
                             "underneath us" % i)
        bbox = (int(sl[0].start), int(sl[0].stop), int(sl[1].start), int(sl[1].stop),
                int(sl[2].start), int(sl[2].stop))
        vol_phys = float(cnt[i] * voxvol)
        rec = {
            "label": i,
            "voxel_count": int(cnt[i]),
            "volume": vol_phys,
            "centroid": (float(mz[i]), float(my[i]), float(mx[i])),
            "centroid_mm": (float(mz[i] * sz), float(my[i] * sy), float(mx[i] * sx)),
            "bbox": bbox,
            "extent": (float((bbox[1] - bbox[0]) * sz), float((bbox[3] - bbox[2]) * sy),
                       float((bbox[5] - bbox[4]) * sx)),
            "equivalent_diameter": float((6.0 * vol_phys / np.pi) ** (1.0 / 3.0)),
            "touches_border": bool(bbox[0] == 0 or bbox[1] == D or bbox[2] == 0
                                   or bbox[3] == H or bbox[4] == 0 or bbox[5] == W),
        }
        if shape:
            C = np.array([[c_zz[i], c_zy[i], c_zx[i]],
                          [c_zy[i], c_yy[i], c_yx[i]],
                          [c_zx[i], c_yx[i], c_xx[i]]], np.float64)
            ev = np.linalg.eigvalsh(C)[::-1]            # l1 >= l2 >= l3
            ev = np.maximum(ev, 0.0)                    # 数値誤差の負値を潰す
            l1, l2, l3 = (float(v) for v in ev)
            if l1 <= 0.0:                               # 単一ボクセル = 等方な点
                lin, pla, iso, elo = 0.0, 0.0, 1.0, 1.0
            else:
                lin = (l1 - l2) / l1
                pla = (l2 - l3) / l1
                iso = l3 / l1
                elo = float(np.sqrt(l1 / l2)) if l2 > 0.0 else float("inf")
            rec.update({
                "principal_extent": (float(np.sqrt(l1)), float(np.sqrt(l2)),
                                     float(np.sqrt(l3))),
                "linearity": float(lin), "planarity": float(pla),
                "isotropy": float(iso), "elongation": float(elo),
            })
        out.append(rec)
    return out


#: :func:`vol_select_labels` の条件名 -> (必要な props キー, 比較, 説明)。
_CRITERIA = {
    "min_volume": ("volume", "ge", "physical (or voxel) volume"),
    "max_volume": ("volume", "le", "physical (or voxel) volume"),
    "min_voxels": ("voxel_count", "ge", "voxel count"),
    "max_voxels": ("voxel_count", "le", "voxel count"),
    "min_sphericity": ("sphericity", "ge", "Wadell sphericity (volops.vol_region_props)"),
    "max_sphericity": ("sphericity", "le", "Wadell sphericity (volops.vol_region_props)"),
    "min_elongation": ("elongation", "ge", "sqrt(l1/l2) (vol_label_shape_stats)"),
    "max_elongation": ("elongation", "le", "sqrt(l1/l2) (vol_label_shape_stats)"),
    "min_isotropy": ("isotropy", "ge", "l3/l1 (vol_label_shape_stats)"),
    "max_isotropy": ("isotropy", "le", "l3/l1 (vol_label_shape_stats)"),
    "min_equivalent_diameter": ("equivalent_diameter", "ge", "(6V/pi)**(1/3)"),
    "max_equivalent_diameter": ("equivalent_diameter", "le", "(6V/pi)**(1/3)"),
}


def vol_select_labels(labels, props=None, spacing=None, relabel: bool = False,
                      exclude_border: bool = False, keep=None, **criteria):
    """3-D の特徴で成分をふるいにかける(2-D のブロブ選別の 3-D 版)。

    ``(labels_out, kept_ids)`` を返す。落ちた成分のボクセルは 0(背景)になる。

    *props* は :func:`vol_label_shape_stats` か :func:`volops.vol_region_props` の
    返り値。``None`` なら :func:`vol_label_shape_stats` をその場で呼ぶ。

    条件(すべて省略可・与えたものは AND):``min_volume`` ``max_volume``
    ``min_voxels`` ``max_voxels`` ``min_sphericity`` ``max_sphericity``
    ``min_elongation`` ``max_elongation`` ``min_isotropy`` ``max_isotropy``
    ``min_equivalent_diameter`` ``max_equivalent_diameter``。加えて
    ``exclude_border=True`` で**ボリューム端に接する成分を落とす**(CT の視野で
    切れている粒子を計測から外す標準手順)、``keep=[...]`` で残す id を直接指定。

    **必要なキーが props に無ければ ValueError**。たとえば ``min_sphericity`` を
    :func:`vol_label_shape_stats` の結果に対して指定すると、``sphericity`` は
    そちらが出さない量なので拒否する ―― 欠けたキーを既定値で埋めると「条件を
    書いたのに一件も落ちない」フィルタが黙って出来上がる。

    ``relabel``:

      * ``False``(既定)―― **元の id をそのまま残す**。ゆえに
        :func:`vol_colorize_labels` を前後で呼んでも**残った成分の色は変わらない**。
        「ふるいにかけて色が残っていく」図が成立するのはこの既定のおかげである。
      * ``True`` ―― 残った成分を ``1..k`` へ振り直す。**色は総取り替えになる**
        (ラベル番号がパレットの行番号だから)。下流が連番を要求する場合だけ使う。
        この 1 引数がこの族の売りを壊せる唯一の場所なので、明示的にした。

    Returns ``(labels_out int32 (D, H, W), kept_ids np.ndarray int64)``.
    Raises ``ValueError`` for an unknown criterion, a criterion whose key is absent
    from *props*, a *props* that does not cover the labels present, or a *keep*
    containing a label that is not in the volume.
    """
    L = _as_labels(labels, cap=MAX_COLOR_VOXELS)
    n = int(L.max())
    ids, _counts = _present_labels(L, n)

    unknown = [k for k in criteria if k not in _CRITERIA]
    if unknown:
        raise ValueError("unknown selection criterion(s) %r — known: %s"
                         % (sorted(unknown), ", ".join(sorted(_CRITERIA))))
    active = {k: v for k, v in criteria.items() if v is not None}

    if props is None:
        props = vol_label_shape_stats(L, spacing=spacing, shape=True)
    if not isinstance(props, (list, tuple)):
        raise ValueError("props must be a list of per-label dicts (from "
                         "vol_label_shape_stats or volops.vol_region_props), got %r"
                         % (type(props).__name__,))
    by_id = {}
    for rec in props:
        if not isinstance(rec, dict) or "label" not in rec:
            raise ValueError("every props entry must be a dict with a 'label' key, "
                             "got %r" % (rec,))
        by_id[int(rec["label"])] = rec
    missing = [int(i) for i in ids if int(i) not in by_id]
    if missing:
        raise ValueError("props does not cover label(s) %r that are present in the "
                         "volume — it was probably computed from a different label "
                         "array" % (missing[:8],))

    for k in active:
        key = _CRITERIA[k][0]
        absent = [i for i in by_id if key not in by_id[i]]
        if absent:
            raise ValueError("criterion %r needs the %r key (%s) but props does not "
                             "carry it. Use volops.vol_region_props(..., surface=...) "
                             "for 'sphericity'/'surface_area', or "
                             "vol_label_shape_stats(..., shape=True) for "
                             "'elongation'/'isotropy'"
                             % (k, key, _CRITERIA[k][2]))

    if keep is not None:
        want = set(int(v) for v in np.asarray(keep, np.int64).reshape(-1))
        bad = sorted(want - set(int(i) for i in ids))
        if bad:
            raise ValueError("keep names label(s) %r that are not present in the "
                             "volume" % (bad[:8],))
    else:
        want = None

    kept = []
    for i in ids:
        i = int(i)
        rec = by_id[i]
        ok = True
        for k, v in active.items():
            key, cmp_, _desc = _CRITERIA[k]
            val = float(rec[key])
            thr = float(v)
            if cmp_ == "ge" and not (val >= thr):
                ok = False
            elif cmp_ == "le" and not (val <= thr):
                ok = False
            if not ok:
                break
        if ok and exclude_border:
            if "touches_border" in rec:
                ok = not bool(rec["touches_border"])
            else:
                b = rec.get("bbox")
                if b is None:
                    raise ValueError("exclude_border needs 'touches_border' or 'bbox' "
                                     "in props; got keys %r" % (sorted(rec),))
                ok = not (b[0] == 0 or b[1] == L.shape[0] or b[2] == 0
                          or b[3] == L.shape[1] or b[4] == 0 or b[5] == L.shape[2])
        if ok and want is not None:
            ok = i in want
        if ok:
            kept.append(i)

    kept_ids = np.asarray(kept, np.int64)
    lut = np.zeros(n + 1, np.int32)
    if relabel:
        for new, i in enumerate(kept, start=1):
            lut[i] = new
        kept_out = np.arange(1, len(kept) + 1, dtype=np.int64)
    else:
        lut[kept_ids] = kept_ids.astype(np.int32) if kept_ids.size else 0
        kept_out = kept_ids
    return np.ascontiguousarray(lut[L]), kept_out


# --------------------------------------------------------------------------- #
# 重ね合わせ / 凡例                                                             #
# --------------------------------------------------------------------------- #
def _label_boundary_mask(L: np.ndarray) -> np.ndarray:
    """前景ボクセルのうち、6 近傍に**違うラベル**(背景を含む)を持つものだけ True。

    成分ごとに erosion を回さないので、成分数に関係なく O(N)。境界は「隣が別の
    ラベル」で定義するので、接している 2 成分の間にも線が入る。"""
    m = L > 0
    b = np.zeros_like(m)
    for ax in (0, 1, 2):
        for shift in (1, -1):
            nb = np.roll(L, shift, axis=ax)
            # ボリューム外周は roll で巻き込むので、端の面は常に境界として扱う
            idx = [slice(None)] * 3
            idx[ax] = 0 if shift == 1 else -1
            diff = nb != L
            diff[tuple(idx)] = True
            b |= m & diff
    return b


def vol_label_overlay(vol, labels, seed: int = 0, alpha: float = 0.5,
                      vmin=None, vmax=None, mode: str = "fill",
                      background=(0.0, 0.0, 0.0)):
    """元のグレーボリュームに色ラベルを重ねた ``(D, H, W, 3)`` を返す。

    医用 CT / 産業 CT で実際に使う形 ―― 「セグメンテーションだけの絵」は
    どこを切り出したのかが分からず、「元画像だけの絵」は何を測ったのかが分からない。

    *vol* は ``(D, H, W)``。表示窓は ``vmin`` / ``vmax`` で**明示**する
    (``None`` なら ``vol`` の最小 / 最大)。窓を暗黙に決めないのは、窓が違えば
    同じ組織が別の明るさで出るからで、CT の window/level と同じ理由である。

    *alpha* は ``0``(元画像のまま)から ``1``(色で塗り潰す)。*mode* は
    ``"fill"``(成分全体を塗る)か ``"boundary"``(6 近傍で隣が別ラベルの
    ボクセルだけを塗る = 輪郭表示、下の構造が完全に見える)。

    実測(``(24, 48, 48)``・16 成分・ノイズ入りグレー体、``mode="fill"``):
    前景ボクセルにおける元画像との平均絶対差は alpha=0.00 で 0.000、
    0.25 で 0.106、0.50 で 0.212、0.75 で 0.318、1.00 で 0.424。
    背景ボクセルは alpha に依らず 0.000(色は前景にしか乗らない)。

    Raises ``ValueError`` when *vol* and *labels* differ in shape, on a non-finite
    *vol*, on ``vmin >= vmax``, on an *alpha* outside [0, 1], or on an unknown *mode*.
    """
    L = _as_labels(labels, cap=MAX_COLOR_VOXELS)
    V = volops._require_volume(vol, "vol")
    if V.shape != L.shape:
        raise ValueError("vol %r and labels %r must have the same shape"
                         % (V.shape, L.shape))
    a = _check_unit(alpha, "alpha")
    if mode not in ("fill", "boundary"):
        raise ValueError("mode must be 'fill' or 'boundary', got %r" % (mode,))
    lo = float(V.min()) if vmin is None else float(vmin)
    hi = float(V.max()) if vmax is None else float(vmax)
    if not (np.isfinite(lo) and np.isfinite(hi)):
        raise ValueError("vmin / vmax must be finite, got (%r, %r)" % (vmin, vmax))
    if hi <= lo:
        if vmin is None and vmax is None:
            hi = lo + 1.0                       # 定数ボリューム: 一様な灰色にする
        else:
            raise ValueError("vmax (%g) must be greater than vmin (%g)" % (hi, lo))
    grey = np.clip((V - lo) / (hi - lo), 0.0, 1.0)
    out = np.repeat(grey[..., None], 3, axis=3)

    pal = vol_label_palette(int(L.max()), seed=seed, background=background)
    mask = (L > 0) if mode == "fill" else _label_boundary_mask(L)
    if mask.any():
        out[mask] = (1.0 - a) * out[mask] + a * pal[L[mask]]
    return np.ascontiguousarray(np.clip(out, 0.0, 1.0))


def vol_label_legend(labels, props=None, seed: int = 0, spacing=None,
                     measure: str = "volume", top=None,
                     background=(0.0, 0.0, 0.0)):
    """「どの色がどの成分で、その計測値は幾つか」の凡例表を返す。

    色だけを出して意味の読めない図を作らないための op。返りは ``list[dict]``:

      ``label`` · ``rgb`` ``(r, g, b)`` float ``[0, 1]`` · ``hex`` ``"#rrggbb"`` ·
      ``voxel_count`` · ``volume`` · ``measure`` 並べ替えに使った量の名前 ·
      ``value`` その値 · ``rank`` 1 始まりの順位 · ``share`` 全成分の
      *measure* 合計に対する割合。

    *measure* は props に載っている数値キーなら何でもよい(``"volume"``
    ``"voxel_count"`` ``"equivalent_diameter"``、``volops.vol_region_props`` を
    渡したなら ``"sphericity"`` も)。降順に並べ、同点はラベル番号の昇順で割る
    (**決定的**)。*top* を与えると上位 N 件だけ返す。

    実在するラベルは ``np.bincount`` の非ゼロから取る。``labels.max()`` を成分数と
    見なさないので、番号に欠番があっても件数も順位も狂わない
    (``tests/test_volcolor.py::test_legend_ignores_gaps_in_numbering``)。

    Raises ``ValueError`` when *measure* is not a numeric key of *props*, when
    *props* does not cover the labels present, or on a bad *top*.
    """
    L = _as_labels(labels, cap=MAX_COLOR_VOXELS)
    n = int(L.max())
    ids, counts = _present_labels(L, n)
    if props is None:
        props = vol_label_shape_stats(L, spacing=spacing)
    by_id = {int(r["label"]): r for r in props}
    missing = [int(i) for i in ids if int(i) not in by_id]
    if missing:
        raise ValueError("props does not cover label(s) %r present in the volume"
                         % (missing[:8],))
    if ids.size and measure not in by_id[int(ids[0])]:
        raise ValueError("measure %r is not a key of props; available: %s"
                         % (measure, ", ".join(sorted(by_id[int(ids[0])]))))
    if top is not None:
        t = int(top)
        if t != top or t <= 0:
            raise ValueError("top must be a positive integer or None, got %r" % (top,))
    pal = vol_label_palette(n, seed=seed, background=background)

    rows = []
    for i, c in zip(ids, counts):
        i = int(i)
        rec = by_id[i]
        val = float(rec[measure])
        if not np.isfinite(val):
            raise ValueError("measure %r is %r for label %d — a non-finite sort key "
                             "would order the legend arbitrarily" % (measure, val, i))
        rows.append((val, i, c, rec))
    total = sum(r[0] for r in rows)
    rows.sort(key=lambda r: (-r[0], r[1]))

    out = []
    for rank, (val, i, c, rec) in enumerate(rows, start=1):
        rgb = pal[i]
        out.append({
            "label": i,
            "rgb": (float(rgb[0]), float(rgb[1]), float(rgb[2])),
            "hex": "#%02x%02x%02x" % tuple(int(round(v * 255.0)) for v in rgb),
            "voxel_count": int(c),
            "volume": float(rec.get("volume", c)),
            "measure": measure,
            "value": val,
            "rank": rank,
            "share": float(val / total) if total > 0 else 0.0,
        })
    return out[:top] if top is not None else out


# --------------------------------------------------------------------------- #
# 3-D 表示 / 投影                                                               #
# --------------------------------------------------------------------------- #
def vol_labels_to_meshes(labels, ids=None, spacing=None, seed: int = 0,
                         level: float = 0.5, axes: str = "xyz",
                         background=(0.0, 0.0, 0.0)):
    """成分ごとに marching cubes をかけ、**色付きメッシュの集合**にする。

    返りは ``list[dict]``、各要素が ``{"label", "vertices" (nv, 3) float64,
    "faces" (nf, 3) int64, "color" (r, g, b)}``。色は
    :func:`vol_colorize_labels` と同じパレットなので、**断面図と 3-D 表示で同じ
    部品が同じ色**になる。

    成分ごとに **bbox を 1 ボクセル分パディングした部分体**だけを切り出して
    marching cubes を回す(全ボリュームを成分数だけ舐めない)。パディングは
    ボリューム端に接する成分の面を閉じるためで、これをしないと端の成分だけ
    穴の開いたメッシュになる。

    ``axes``:

      * ``"xyz"``(既定)―― 頂点を ``(x, y, z)`` で返す。:mod:`render3d` /
        :mod:`mesh` の頂点順がこれで、``render3d.render_mesh`` へ直接渡せる。
      * ``"zyx"`` ―― ボリュームの添字順のまま返す。:func:`vol_label_shape_stats`
        の ``centroid`` と同じ並びになる。

      **黙って取り違えると例外は出ない** ―― 出るのは上下と前後が入れ替わった、
      それらしい絵である。``tests/test_volcolor.py::test_mesh_axes_order`` が
      両方の重心を stats の重心と突き合わせて固定している。

    *spacing* を渡すと頂点は物理座標(mm)になる。*ids* で成分を絞れる
    (``None`` なら実在する全ラベル、ただし :data:`MAX_MESHES` 件まで)。

    Raises ``ImportError`` (with the ``pip install scikit-image`` message) when
    marching cubes is unavailable, and ``ValueError`` for a bad *axes*, a *level*
    outside ``(0, 1)``, an *ids* naming an absent label, or more than
    :data:`MAX_MESHES` components.
    """
    import render3d                                     # lazy: skimage は optional

    L = _as_labels(labels, cap=MAX_COLOR_VOXELS)
    if axes not in ("xyz", "zyx"):
        raise ValueError("axes must be 'xyz' (render3d / mesh order) or 'zyx' "
                         "(volume index order), got %r" % (axes,))
    lv = float(level)
    if not np.isfinite(lv) or lv <= 0.0 or lv >= 1.0:
        raise ValueError("level must lie strictly inside (0, 1) for a binary "
                         "component mask, got %r" % (level,))
    sp = volops._spacing_tuple(spacing)
    sz, sy, sx = (1.0, 1.0, 1.0) if sp is None else sp
    n = int(L.max())
    present, _counts = _present_labels(L, n)
    if ids is None:
        want = present
    else:
        want = np.asarray(ids, np.int64).reshape(-1)
        bad = sorted(set(int(v) for v in want) - set(int(v) for v in present))
        if bad:
            raise ValueError("ids name label(s) %r that are not present in the volume"
                             % (bad[:8],))
    if want.size > MAX_MESHES:
        raise ValueError("%d components exceed the %d cap (volcolor.MAX_MESHES) — "
                         "select components first (vol_select_labels) or pass ids"
                         % (want.size, MAX_MESHES))
    pal = vol_label_palette(n, seed=seed, background=background)
    slices = ndimage.find_objects(L)

    out = []
    for lab in want:
        i = int(lab)
        sl = slices[i - 1]
        z0, z1 = max(0, sl[0].start - 1), min(L.shape[0], sl[0].stop + 1)
        y0, y1 = max(0, sl[1].start - 1), min(L.shape[1], sl[1].stop + 1)
        x0, x1 = max(0, sl[2].start - 1), min(L.shape[2], sl[2].stop + 1)
        sub = (L[z0:z1, y0:y1, x0:x1] == i).astype(np.float64)
        sub = np.pad(sub, 1)                            # 端に接する成分の面を閉じる
        V, F = render3d.marching_cubes(sub, lv)
        V = V + np.array([z0 - 1.0, y0 - 1.0, x0 - 1.0])     # 部分体 -> 全体の添字
        V = V * np.array([sz, sy, sx])                       # 添字 -> 物理
        if axes == "xyz":
            V = V[:, ::-1]
        out.append({"label": i, "vertices": np.ascontiguousarray(V, np.float64),
                    "faces": np.ascontiguousarray(F, np.int64),
                    "color": (float(pal[i][0]), float(pal[i][1]), float(pal[i][2]))})
    return out


def vol_label_volume_render(labels, axis="z", mode: str = "front", seed: int = 0,
                            alpha: float = 0.35, background=(0.0, 0.0, 0.0)):
    """色付きラベルの**合成投影** ``(H, W, 3)`` を numpy だけで作る。

    *mode*:

      * ``"front"`` ―― 視線方向で最初に当たる非背景ボクセルの色(不透明表示)。
      * ``"back"``  ―― 最後に当たるもの(裏側から見た形)。
      * ``"alpha"`` ―― front-to-back の ``over`` 合成(Porter & Duff 1984)。
        非背景ボクセルが不透明度 *alpha* を持つとして手前から積む。
        奥行きの重なりが出る一方、手前の色は必ず後ろより濃く出る。

    **``mode="max"`` は拒否する**(``ValueError``)。RGB をチャネルごとに max
    すると、赤成分が部品 A・緑成分が部品 B から来た**どの部品の色でもない色**が
    出るからである。実測(3 成分・``(16, 16, 16)``、seed=0、axis="z"):
    チャネル別 max の結果はパレットに存在しない色を **1226 / 1500 前景画素**で
    作り、そのうち 0 画素も「どれか 1 つの成分の色」に一致しなかった。
    ``"front"`` は同じ入力で 100 % がパレットの色である
    (``tests/test_volcolor.py::test_channelwise_max_would_invent_colours``)。

    *axis* は ``"z"``/0(``(H, W, 3)`` が返る)、``"y"``/1(``(D, W, 3)``)、
    ``"x"``/2(``(D, H, 3)``)。

    Raises ``ValueError`` for an unknown *mode* / *axis*, an *alpha* outside
    [0, 1], or a bad label volume.
    """
    if mode in ("max", "mip", "maximum"):
        raise ValueError(
            "mode=%r is refused on purpose. A channel-wise maximum over an RGB "
            "label volume mixes the red of one component with the green of "
            "another and produces a colour that belongs to no component "
            "(measured: 1226 of 1500 foreground pixels on the reference volume). "
            "Use mode='front' (nearest opaque component), 'back', or 'alpha' "
            "(front-to-back over-compositing)." % (mode,))
    if mode not in ("front", "back", "alpha"):
        raise ValueError("mode must be 'front', 'back' or 'alpha', got %r" % (mode,))
    L = _as_labels(labels, cap=MAX_COLOR_VOXELS)
    ax = _check_axis(axis)
    a = _check_unit(alpha, "alpha")
    bg = _check_rgb(background)
    n = int(L.max())
    pal = vol_label_palette(n, seed=seed, background=background)

    M = np.moveaxis(L, ax, 0)                           # (K, R, C) 視線 = 軸 0
    K = M.shape[0]
    nz = M > 0
    if mode in ("front", "back"):
        order = M if mode == "front" else M[::-1]
        hits = order > 0
        first = np.argmax(hits, axis=0)
        has = hits.any(axis=0)
        rr, cc = np.indices(first.shape)
        picked = np.where(has, order[first, rr, cc], 0)
        img = pal[picked]
        img[~has] = bg
        return np.ascontiguousarray(img)

    # front-to-back over: C_out += (1 - A_acc) * a * C_i ; A_acc += (1 - A_acc) * a
    img = np.zeros(M.shape[1:] + (3,), np.float64)
    acc = np.zeros(M.shape[1:], np.float64)
    for k in range(K):
        m = nz[k]
        if not m.any():
            continue
        w = (1.0 - acc[m]) * a
        img[m] += w[:, None] * pal[M[k][m]]
        acc[m] += w
    img += (1.0 - acc)[..., None] * bg
    return np.ascontiguousarray(np.clip(img, 0.0, 1.0))


# --------------------------------------------------------------------------- #
# 色の安定性(この族の存在理由の測定)                                          #
# --------------------------------------------------------------------------- #
def vol_label_color_flicker(vol_binary, axis="z", seed: int = 0,
                            connectivity: int = 26, connectivity_2d: int = 8):
    """「切ってから色を付ける」と「色を付けてから切る」の差を**数える**。

    同じ 2 値ボリュームに対して 2 通りの手順を踏む:

      A. **スライスごと** ―― 各断面を 2-D で連結成分ラベリングし、
         :func:`imgio.colorize_labels` と同じパレットで色を付ける。
         断面ごとに番号が振り直されるので、同じ部品でも層が変われば色が変わりうる。
      B. **ボリュームで** ―― :func:`volops.vol_label` でラベリングしてから
         :func:`vol_colorize_labels` で色を付け、あとで切る。

    返りは dict:

      ``n_components`` 3-D 成分数 · ``n_slices`` 断面の数 ·
      ``slices_with_change`` **A で 1 つ以上の成分の色が変わった断面の本数** ·
      ``changed_pairs`` A で色が変わった (成分, 断面) の組の数 ·
      ``changed_components`` A で一度でも色が変わった成分の数 ·
      ``volume_slices_with_change`` / ``volume_changed_pairs`` /
      ``volume_changed_components`` B の同じ量(**構造上 0**) ·
      ``pairs_checked`` 比較した (成分, 断面) の総数 ·
      ``flicker_rate`` ``changed_pairs / pairs_checked``。

    比較の定義:各 3-D 成分 ``c`` について、``c`` が現れる最初の断面での色を
    基準とし、以降の断面で ``c`` の画素の**最頻色**が基準と違えば 1 件と数える
    (1 つの 3-D 成分が 1 断面で複数の 2-D 片に割れることがあるため、代表は
    最頻色。同数の場合は RGB の辞書順で小さい方 = 決定的)。

    実測(``(24, 48, 48)``・16 成分の参照体、seed=0、axis="z"):
    ``slices_with_change=21 / 24``、``changed_pairs=96``、
    ``changed_components=15 / 16``、B 側はすべて 0。

    Raises ``ValueError`` for a bad volume, an unknown *axis*, or a *connectivity*
    that is not 6 / 18 / 26 (2-D: 4 / 8).
    """
    m = volops._as_binary(vol_binary)
    if m.size > MAX_COLOR_VOXELS:
        raise ValueError("vol_label_color_flicker: a %d-voxel volume exceeds the %d "
                         "cap (volcolor.MAX_COLOR_VOXELS)" % (m.size, MAX_COLOR_VOXELS))
    ax = _check_axis(axis)
    s = _check_seed(seed)
    if int(connectivity_2d) not in (4, 8):
        raise ValueError("connectivity_2d must be 4 or 8, got %r" % (connectivity_2d,))
    labels3d, n3 = volops.vol_label(m, connectivity=connectivity)

    struct2d = ndimage.generate_binary_structure(2, 1 if int(connectivity_2d) == 4 else 2)
    M = np.moveaxis(labels3d, ax, 0)
    K = M.shape[0]

    def _scan(colour_of_slice):
        """colour_of_slice(k) -> (H, W, 3)。成分ごとに基準色からの変化を数える。"""
        first_colour = {}
        changed_pairs = 0
        changed_slices = set()
        changed_comps = set()
        pairs = 0
        for k in range(K):
            sl = M[k]
            ids = np.unique(sl)
            ids = ids[ids > 0]
            if ids.size == 0:
                continue
            rgb = colour_of_slice(k)
            for i in ids:
                i = int(i)
                px = rgb[sl == i]
                # 最頻色(同数はタプルの昇順 = 決定的)
                uniq, cnt = np.unique(px, axis=0, return_counts=True)
                dom = tuple(uniq[np.lexsort((np.arange(len(uniq)), -cnt))[0]])
                pairs += 1
                if i not in first_colour:
                    first_colour[i] = dom
                elif dom != first_colour[i]:
                    changed_pairs += 1
                    changed_slices.add(k)
                    changed_comps.add(i)
        return pairs, changed_pairs, len(changed_slices), len(changed_comps)

    def _per_slice(k):
        lab2d, _ = ndimage.label(M[k] > 0, structure=struct2d)
        nn = int(lab2d.max())
        pal = vol_label_palette(nn, seed=s)
        return pal[lab2d]

    rgbvol = vol_colorize_labels(labels3d, seed=s)
    RGB = np.moveaxis(rgbvol, ax, 0)

    def _from_volume(k):
        return RGB[k]

    pairs, cp, cs, cc = _scan(_per_slice)
    _p2, vcp, vcs, vcc = _scan(_from_volume)
    return {
        "n_components": int(n3),
        "n_slices": int(K),
        "pairs_checked": int(pairs),
        "slices_with_change": int(cs),
        "changed_pairs": int(cp),
        "changed_components": int(cc),
        "volume_slices_with_change": int(vcs),
        "volume_changed_pairs": int(vcp),
        "volume_changed_components": int(vcc),
        "flicker_rate": float(cp / pairs) if pairs else 0.0,
    }


if __name__ == "__main__":                              # pragma: no cover - 手動確認
    print("volcolor: %d ops" % len(VOLCOLOR))
    for name in VOLCOLOR:
        fn = globals()[name]
        print("  %-26s %s" % (name, (fn.__doc__ or "").strip().splitlines()[0]))
