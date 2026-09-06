# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""blob2d — 2-D の**連結成分**と、**物体ごと**の形の特徴量。

## なぜ要るか(2026-09-06)

`examples/poc_cell_counting.py` が「2 次元の連結成分ラベリングと per-object の
region props が facade に無い」と書いた。3 層すべてを引いて確かめた結果、
**本当に無かった**(この repo は同じ形で一度間違えているので、今度は先に引いた):

* ``fullseye.ledger.label_components`` / ``region_props`` は **3-D 専用**。
  2-D を渡すと ``ValueError: a 3D voxel array (ndim==3) is required`` で拒否
  される(fail-closed なので嘘は出ないが、2-D では使えない)。
* ``circularity`` / ``eccentricity`` / ``area_center`` / ``select_shape`` /
  ``blob_count`` / ``select_largest`` は**進化 op のレジストリ**
  (``fullseye.op.*``)にしかなく、いずれも画像 1 枚 → スカラ 1 個か画像 1 枚。
  「2 番目の物体の面積」は取り出せない。
* ラベリング自体は ``ndimage.label`` として **op の実装の中**には 20 か所以上
  ある。だがどれも結果を画像かスカラに畳んでから返すので、利用者には出て
  こない。**実装があることと、公開経路があることは別**。

つまり閾値処理のあとの定番の連鎖 —— 領域を物体に切り、物体ごとに測り、
条件で選ぶ —— が、この道具では書けなかった。

## 内容(7 op)

    切る     `blob_label`          … 二値領域 → ラベル画像(4/8 連結)
    測る     `blob_features`       … 物体ごとの 19 項目(面積・重心・慣性主軸…)
    選ぶ     `blob_select`         … 特徴量の範囲で残す(番号は振り直す)
             `blob_select_largest` … 面積の大きい順に n 個
    取り出す `blob_region`         … 1 個を二値領域として抜く
             `blob_boundaries`     … 物体の輪郭(1 画素幅)
    見る     `blob_overlay`        … 元画像の上に色分けして重ねる

## 規約

* 画像は ``img[i, j]``、``i`` = 行 = y(下向き)、``j`` = 列 = x(右向き)。
* **入力の領域は「0 より大きい画素が前景」**。bool でも実数でもよい。
  NaN は前景にしない(``> 0`` が False になる)。
* ラベルは ``int32``、**背景 = 0、物体 = 1..n の連番**。歯抜けにしない
  (``blob_select`` は残った物体を振り直す)—— 歯抜けを許すと
  ``features["area"][k]`` の ``k`` が何の番号なのか呼び手が追えなくなる。
* ``spacing`` は**画素 1 個の大きさ**[任意単位/px]。長さはこれを、面積は
  その 2 乗を掛けて返す。**bbox と重心の行列番号だけは画素のまま** ——
  あれは長さではなく添字だから。返り値の ``"units"`` に全項目の単位を
  入れてあるので、読み違えたら表で気づける。
* ``angle`` は**行列座標系**での傾き:「+列(右)方向から +行(下)方向へ」正。
  画面上では時計回りが正になる —— 数学の慣習と符号が逆なので、
  ``blob_features`` の返り値の ``units["angle"]`` にもそう書いてある。

## 測って決めたこと

いずれも本ファイルの実装で 2026-09-06 に実測(``tests/test_blob2d.py`` が固定):

* **周長は素朴に数えると 4 割ずれる。** 半径 40 px の円板(真値 251.33 px)を
  境界画素の数で数えると 356 px。Crofton 型の重みづけ(直線 1 / 斜め √2 /
  角 (1+√2)/2、:func:`_perimeter`)なら 250 px 台に収まる。円形度 4πA/P² が
  1 を超えるかどうかがここで決まるので、素朴な数え方は採らなかった。
* **4 連結と 8 連結は「斜めに触れる 2 つ」で割れる。** 市松に並べた 2 個は
  8 連結で 1 個、4 連結で 2 個。既定は 8 —— HALCON の ``connection`` と
  ``ndimage.label`` の既定に合わせる(``poc_cell_counting`` の実測では
  4 連結にすると細胞が過剰計数された)。
* **``solidity`` の分母は凸包を塗り直して数える。** 多角形として面積を出すと
  「画素を点と見るか正方形と見るか」でどちらかへ必ずずれ、**凸な物体の
  solidity が 1 にならない**(半径 40 px の円板で 0.977 か 1.025)。分子が
  画素の数なら分母も画素の数で揃える —— 塗り直すと 1.000 になる。
* **2 次モーメントに 1/12 を足す。** 画素を点ではなく 1 辺 1 の正方形として
  扱う補正で、これが無いと 1 画素幅の線で ``minor`` が 0 になり
  ``eccentricity`` が 1 に張り付く。

来歴(公開文献のみ): Serra, *Image Analysis and Mathematical Morphology*
(Academic Press, 1982)—— Crofton の公式による周長推定 / Hu, *IRE Trans.
Inf. Theory* 8 (1962) 179 —— 2 次モーメントと慣性主軸 / Rosenfeld & Pfaltz,
*J. ACM* 13 (1966) 471 —— 連結成分ラベリング。
"""
from __future__ import annotations

import math
from typing import Any, Optional

import numpy as np
from scipy import ndimage

__all__ = [
    "blob_label", "blob_features", "blob_select", "blob_select_largest",
    "blob_region", "blob_boundaries", "blob_overlay",
    "FEATURE_KEYS", "CONNECTIVITIES",
]

#: 受け付ける連結の定義。既定は 8(``ndimage.label`` と HALCON の既定)。
CONNECTIVITIES: tuple[int, int] = (4, 8)

#: :func:`blob_features` が返す物体ごとの項目(``blob_select`` が選べる鍵)。
FEATURE_KEYS: tuple[str, ...] = (
    "label", "area", "row", "col", "bbox_r0", "bbox_c0", "bbox_r1", "bbox_c1",
    "perimeter", "equiv_diameter", "major", "minor", "angle", "eccentricity",
    "circularity", "extent", "solidity", "holes", "touches_border",
)

#: Crofton の公式(4 方向)で周長を数えるための 2x2 近傍の符号化。
_PERIM_KERNEL = np.array([[0, 0, 0],
                          [0, 1, 4],
                          [0, 2, 8]], dtype=np.int32)

#: 符号 0..15 に配る長さ。4 方向(0°/45°/90°/135°)の投影の重みつき平均。
_PERIM_COEF = np.array([
    0.0,
    math.pi / 4 * (1 + 1 / math.sqrt(2)),
    math.pi / (4 * math.sqrt(2)),
    math.pi / (2 * math.sqrt(2)),
    0.0,
    math.pi / 4 * (1 + 1 / math.sqrt(2)),
    0.0,
    math.pi / (4 * math.sqrt(2)),
    math.pi / 4,
    math.pi / 2,
    math.pi / (4 * math.sqrt(2)),
    math.pi / (4 * math.sqrt(2)),
    math.pi / 4,
    math.pi / 2,
    0.0,
    0.0,
], dtype=np.float64)


# --------------------------------------------------------------------------- #
# 入力検証 — fail closed                                                       #
# --------------------------------------------------------------------------- #
def _as_binary(region: Any, op: str, name: str = "region") -> np.ndarray:
    """2-D の前景マスクとして受ける(``> 0`` が前景。NaN は背景)。"""
    a = np.asarray(region)
    if a.ndim != 2:
        raise ValueError(
            f"{op}: {name} must be a 2-D region, got ndim={a.ndim}. "
            "3-D volumes have their own family (label_components / region_props)")
    if a.size == 0:
        raise ValueError(f"{op}: {name} is empty")
    if a.dtype == bool:
        return a
    f = np.asarray(a, np.float64)
    return np.nan_to_num(f, nan=0.0, posinf=0.0, neginf=0.0) > 0.0


def _as_labels(labels: Any, op: str, name: str = "labels") -> np.ndarray:
    """ラベル画像として受ける。**bool と実数のラベルは拒否する**。

    ``blob_label`` の出力は ``int32`` で、番号は 1..n の連番。実数配列を
    許すと ``0.999`` のような値がどの物体なのか決められず、丸め方の違いで
    静かに別の答えが出る —— なので整数だけを通す。
    """
    a = np.asarray(labels)
    if a.ndim != 2:
        raise ValueError(f"{op}: {name} must be a 2-D label image, got ndim={a.ndim}")
    if a.size == 0:
        raise ValueError(f"{op}: {name} is empty")
    if a.dtype == bool:
        # 二値をそのまま渡されたら「物体 1 個」ではなく **ラベリングし直す**
        # のが正しいので、ここでは受けずに直し方を出す。
        raise ValueError(
            f"{op}: {name} is a boolean mask, not a label image. "
            "Call blob_label(mask) first - a mask holding several separate "
            "objects would otherwise be measured as one blob and return "
            "plausible nonsense (one centroid between two cells)")
    if not np.issubdtype(a.dtype, np.integer):
        raise ValueError(
            f"{op}: {name} must have an integer dtype, got {a.dtype}. "
            "blob_label returns int32; a float label image cannot be indexed "
            "without a rounding rule")
    if int(a.min()) < 0:
        raise ValueError(f"{op}: {name} has negative labels (min={int(a.min())})")
    return np.asarray(a, np.int32)


def _positive_float(value: Any, op: str, name: str) -> float:
    v = float(value)
    if not math.isfinite(v) or v <= 0.0:
        raise ValueError(f"{op}: {name} must be finite and > 0, got {value!r}")
    return v


# --------------------------------------------------------------------------- #
# 1. 切る                                                                      #
# --------------------------------------------------------------------------- #
def blob_label(region: Any, connectivity: int = 8) -> np.ndarray:
    """二値領域を連結成分に分け、``int32`` のラベル画像(背景 0、物体 1..n)を返す。

    Parameters
    ----------
    region : array_like
        2-D。``> 0`` が前景(bool でも実数でもよい。NaN は背景)。
    connectivity : {4, 8}
        斜めに触れる 2 画素をつなぐか。既定 8 は ``ndimage.label`` と
        HALCON ``connection`` の既定に一致する。**4 にすると斜めに接した塊が
        別々に数えられる**。

    Returns
    -------
    numpy.ndarray
        ``(H, W)`` の ``int32``。番号は 1 から連番で歯抜けが無い。

    Examples
    --------
    >>> import numpy as np
    >>> m = np.zeros((6, 9), bool); m[1:4, 1:4] = True; m[1:4, 5:8] = True
    >>> int(blob_label(m).max())
    2
    """
    if connectivity not in CONNECTIVITIES:
        raise ValueError(
            f"blob_label: connectivity must be 4 or 8, got {connectivity!r}")
    m = _as_binary(region, "blob_label")
    st = (np.ones((3, 3), bool) if connectivity == 8
          else ndimage.generate_binary_structure(2, 1))
    lab, _ = ndimage.label(m, structure=st)
    return np.asarray(lab, np.int32)


# --------------------------------------------------------------------------- #
# 2. 測る                                                                      #
# --------------------------------------------------------------------------- #
def _perimeter(mask: np.ndarray) -> float:
    """Crofton の公式(4 方向)による周長[px]。

    **数え方を 3 つ測ってから選んだ**(2026-09-06 実測、半径 r の円板):

        r     真値      境界画素を数える     Serra の重み     Crofton 4 方向
        10    62.83     76 (+21.0 %)         65.94 (+4.95 %)  65.20 (+3.77 %)
        20   125.66    156 (+24.1 %)        131.88 (+4.95 %) 127.71 (+1.63 %)
        40   251.33    316 (+25.7 %)        263.76 (+4.95 %) 252.75 (+0.56 %)

    素朴に境界画素を数えると 2 割超の過大。Serra の重み(1 / √2 / (1+√2)/2)は
    **大きさを変えても +4.95 % のまま**で、円板の円形度が 0.908 で頭打ちになる
    —— 「円らしさ 0.9 以上」で切る使い方が成り立たない。Crofton は大きさとともに
    真値へ寄り、r=40 で円形度 0.988。

    **正直に書いておく偏り**: 軸に平行な多角形は逆に小さく出る。20x20 の正方形
    (真値 80)で 74.73(**-6.6 %**)、円形度は π/4 = 0.785 のところ 0.900。
    角ばった物体の円形度を絶対値で語らないこと(相対比較なら向きは保たれる)。
    """
    img = np.pad(mask, 1).astype(np.uint8)
    if not img.any():
        return 0.0
    code = ndimage.convolve(img, _PERIM_KERNEL, mode="constant", cval=0)
    hist = np.bincount(code.ravel(), minlength=16)
    return float(_PERIM_COEF @ hist[:16])


def _convex_area(mask: np.ndarray) -> float:
    """凸包を**塗り直して**数えた面積[px^2](``solidity`` の分母)。

    多角形としての凸包面積ではなく、**凸包の中に中心が入る画素の数**を返す。
    理由は測って決めた(2026-09-06、半径 40 px の円板 = 凸なので真値は 1.0):

        画素の角で多角形の面積 …… 5140 px^2 → solidity 0.977(凸なのに 1 未満)
        画素の中心で多角形面積 …… 4900 px^2 → solidity 1.025(1 を超える)
        凸包を塗り直して数える …… 5025 px^2 → **solidity 1.000**

    多角形の面積は「画素を点と見るか正方形と見るか」でどちらかへ必ずずれ、
    凸な物体の solidity が 1 にならない。分子(面積)が画素の数である以上、
    分母も画素の数で揃えるのが筋が通る。

    退化(1 画素、1 画素幅の線)では凸包が作れないので、そのときは
    **面積そのもの**を返す = solidity 1.0。線分も 1 点も凸なので正しい。
    """
    rows = np.nonzero(mask.any(axis=1))[0]
    if rows.size == 0:
        return 0.0
    # 凸包の頂点は「その行のいちばん左かいちばん右」にしかない(それ以外は
    # 2 点を結ぶ線分の内側)。行ごとの両端だけ渡せば包は変わらず、点数が
    # 物体の周長ではなく**高さ**に比例する。
    first = np.argmax(mask, axis=1)
    last = mask.shape[1] - 1 - np.argmax(mask[:, ::-1], axis=1)
    pts = np.concatenate([np.stack([rows, first[rows]], 1),
                          np.stack([rows, last[rows]], 1)]).astype(np.float64)
    hull = _monotone_chain(pts)
    if hull.shape[0] < 3:                # 1 点・共線 —— どちらも凸なので 1.0
        return float(mask.sum())
    gr, gc = np.mgrid[0:mask.shape[0], 0:mask.shape[1]]
    grid = np.stack([gr.ravel(), gc.ravel()], 1).astype(np.float64)
    a = hull
    b = np.roll(hull, -1, axis=0)
    e = b - a                            # 各辺のベクトル
    # ★符号に注意: 頂点は (row, col) の順で並んでいるので、``_monotone_chain``
    #   が返す向きは (row を x と見た) 反時計回り = 画面では時計回り。内側は
    #   外積が**非負**の側になる(``<= 0`` と書いて全物体 solidity 0 を出した)。
    cross = (e[None, :, 0] * (grid[:, None, 1] - a[None, :, 1])
             - e[None, :, 1] * (grid[:, None, 0] - a[None, :, 0]))
    return float(np.all(cross >= -1e-9, axis=1).sum())


def _monotone_chain(pts: np.ndarray) -> np.ndarray:
    """Andrew の monotone chain による凸包(頂点を反時計回りで返す)。

    Qhull を呼ばないのは速さのため —— 512x512 に 153 物体を撒いて
    ``_convex_area`` 全体を測ると ``ConvexHull`` 版 74.1 ms に対して
    19.4 ms(**3.8 倍**、2026-09-06 実測)。小さな点集合を何千回も包む
    用途では Qhull の起動費が支配的になる。``blob_features`` 全体では
    100.4 ms → 33.6 ms。
    """
    p = np.unique(pts, axis=0)           # 辞書順に整列もされる
    if p.shape[0] < 3:
        return p

    def _half(seq):
        out: list = []
        for q in seq:
            while len(out) >= 2:
                o, t = out[-2], out[-1]
                if (t[0] - o[0]) * (q[1] - o[1]) - (t[1] - o[1]) * (q[0] - o[0]) <= 0:
                    out.pop()
                else:
                    break
            out.append(q)
        return out

    lower = _half(p)
    upper = _half(p[::-1])
    return np.asarray(lower[:-1] + upper[:-1], np.float64)


def blob_features(labels: Any, spacing: float = 1.0) -> dict:
    """物体ごとの形の特徴量を、**鍵ごとに 1 本の配列**で返す。

    Parameters
    ----------
    labels : array_like
        :func:`blob_label` の出力(整数、背景 0)。
    spacing : float
        画素 1 個の大きさ[単位/px]。長さにこれを、面積にその 2 乗を掛ける。
        **既定 1.0 = 画素のまま**。

    Returns
    -------
    dict
        ``n``(物体数)、``spacing``、``units``(項目 → 単位の対応)と、
        長さ ``n`` の配列 19 本(:data:`FEATURE_KEYS`)。物体が 0 個でも
        鍵は全部揃えて空配列で返す(呼び手が分岐しなくて済む)。

    Notes
    -----
    * ``angle`` は**行列座標系**の傾き(+列 → +行 が正 = 画面では時計回り)。
    * ``major`` / ``minor`` は**同じ 2 次モーメントを持つ楕円**の軸長
      (``4 sqrt(lambda)``)。画素の並びの外接ではないので、正方形に対しては
      辺長より少し長く出る —— これは定義どおりで、誤差ではない。
    * ``circularity`` は ``4 pi A / P^2``。**HALCON の ``circularity`` は
      「面積 / 最遠点を半径とする円の面積」で別物**なので、値を突き合わせる
      ときは定義を確かめること。
    * ``touches_border`` が True の物体は、面積も周長も**切れた分だけ小さい**。
      数える前に捨てるか、真値の側も同じ規約で数えること。

    Examples
    --------
    >>> import numpy as np
    >>> m = np.zeros((20, 20), bool); m[4:14, 4:9] = True
    >>> f = blob_features(blob_label(m))
    >>> int(f["n"]), float(f["area"][0])
    (1, 50.0)
    """
    lab = _as_labels(labels, "blob_features")
    sp = _positive_float(spacing, "blob_features", "spacing")
    n = int(lab.max())

    units = {
        "label": "-", "area": "unit^2", "row": "px", "col": "px",
        "bbox_r0": "px index", "bbox_c0": "px index",
        "bbox_r1": "px index (exclusive)", "bbox_c1": "px index (exclusive)",
        "perimeter": "unit", "equiv_diameter": "unit", "major": "unit",
        "minor": "unit", "angle": "rad (+col -> +row, clockwise on screen)",
        "eccentricity": "-", "circularity": "-", "extent": "-",
        "solidity": "-", "holes": "count", "touches_border": "bool",
    }
    out: dict = {"n": n, "spacing": sp, "units": units}
    if n == 0:
        for k in FEATURE_KEYS:
            out[k] = np.zeros(0, np.float64)
        out["label"] = np.zeros(0, np.int32)
        out["holes"] = np.zeros(0, np.int32)
        for k in ("bbox_r0", "bbox_c0", "bbox_r1", "bbox_c1"):
            out[k] = np.zeros(0, np.int32)
        out["touches_border"] = np.zeros(0, bool)
        return out

    objs = ndimage.find_objects(lab)
    h, w = lab.shape
    cols: dict = {k: [] for k in FEATURE_KEYS}
    for idx, sl in enumerate(objs, start=1):
        if sl is None:                                # 歯抜けのラベル(通常来ない)
            continue
        sub = lab[sl] == idx
        r0, r1 = int(sl[0].start), int(sl[0].stop)
        c0, c1 = int(sl[1].start), int(sl[1].stop)
        area_px = float(sub.sum())

        rr, cc = np.nonzero(sub)
        rr = rr + r0
        cc = cc + c0
        row = float(rr.mean())
        col = float(cc.mean())

        # 2 次中心モーメント。1/12 は画素を点でなく 1 辺 1 の正方形として扱う補正。
        mu20 = float(((cc - col) ** 2).mean()) + 1.0 / 12.0
        mu02 = float(((rr - row) ** 2).mean()) + 1.0 / 12.0
        mu11 = float(((cc - col) * (rr - row)).mean())
        common = math.sqrt(max((mu20 - mu02) ** 2 + 4.0 * mu11 * mu11, 0.0))
        lam1 = 0.5 * (mu20 + mu02 + common)           # 長軸側
        lam2 = max(0.5 * (mu20 + mu02 - common), 0.0)
        major = 4.0 * math.sqrt(lam1)
        minor = 4.0 * math.sqrt(lam2)
        angle = 0.5 * math.atan2(2.0 * mu11, mu20 - mu02)
        ecc = math.sqrt(max(1.0 - lam2 / lam1, 0.0)) if lam1 > 0 else 0.0

        perim_px = _perimeter(sub)
        conv_px = _convex_area(sub)
        # 穴の数 = 1 画素ぶん広げた背景の連結成分 - 1(外側)。穴の連結は
        # 4 連結で数える(物体を 8 連結で取ったので、背景は 4 連結が対)。
        pad = np.pad(sub, 1)
        _, nbg = ndimage.label(~pad, structure=ndimage.generate_binary_structure(2, 1))

        cols["label"].append(idx)
        cols["area"].append(area_px * sp * sp)
        cols["row"].append(row)
        cols["col"].append(col)
        cols["bbox_r0"].append(r0)
        cols["bbox_c0"].append(c0)
        cols["bbox_r1"].append(r1)
        cols["bbox_c1"].append(c1)
        cols["perimeter"].append(perim_px * sp)
        cols["equiv_diameter"].append(2.0 * math.sqrt(area_px / math.pi) * sp)
        cols["major"].append(major * sp)
        cols["minor"].append(minor * sp)
        cols["angle"].append(angle)
        cols["eccentricity"].append(ecc)
        cols["circularity"].append(
            4.0 * math.pi * area_px / (perim_px * perim_px) if perim_px > 0 else 0.0)
        cols["extent"].append(area_px / float((r1 - r0) * (c1 - c0)))
        cols["solidity"].append(area_px / conv_px if conv_px > 0 else 0.0)
        cols["holes"].append(int(nbg) - 1)
        cols["touches_border"].append(
            bool(r0 == 0 or c0 == 0 or r1 == h or c1 == w))

    for k in FEATURE_KEYS:
        if k == "touches_border":
            out[k] = np.asarray(cols[k], bool)
        elif k == "label" or k == "holes" or k.startswith("bbox_"):
            out[k] = np.asarray(cols[k], np.int32)
        else:
            out[k] = np.asarray(cols[k], np.float64)
    return out


# --------------------------------------------------------------------------- #
# 3. 選ぶ                                                                      #
# --------------------------------------------------------------------------- #
def _renumber(lab: np.ndarray, keep) -> np.ndarray:
    """``keep``(1 起点のラベル番号の並び)だけ残し、その順に 1..k を振り直す。"""
    keep = np.asarray(keep, np.int64)
    lut = np.zeros(int(lab.max()) + 1, np.int32)
    lut[keep] = np.arange(1, len(keep) + 1, dtype=np.int32)
    return lut[lab]


def blob_select(labels: Any, feature: str, vmin: Optional[float] = None,
                vmax: Optional[float] = None, spacing: float = 1.0) -> np.ndarray:
    """特徴量が ``[vmin, vmax]`` に入る物体だけ残す(**番号は 1 から振り直す**)。

    Parameters
    ----------
    labels : array_like
        :func:`blob_label` の出力。
    feature : str
        :data:`FEATURE_KEYS` のどれか。知らない鍵は**候補を並べて拒否する**。
    vmin, vmax : float or None
        両端(含む)。``None`` は片側を開ける。両方 ``None`` は
        「何も選んでいない」ので拒否する —— 全部通す意図なら呼ばなければよい。
    spacing : float
        :func:`blob_features` と同じ意味。``area`` や ``perimeter`` を
        物理単位で切るときに要る。

    Returns
    -------
    numpy.ndarray
        ``int32`` のラベル画像。**残った物体は 1..k の連番**になる
        (元の番号は残さない)。元の番号が要るなら
        ``blob_features(labels)["label"]`` を先に取っておくこと。
    """
    if feature not in FEATURE_KEYS:
        raise ValueError(
            "blob_select: unknown feature %r. Available: %s"
            % (feature, ", ".join(FEATURE_KEYS)))
    if vmin is None and vmax is None:
        raise ValueError(
            "blob_select: give at least one of vmin / vmax - selecting with "
            "neither bound would silently return the input unchanged")
    lab = _as_labels(labels, "blob_select")
    f = blob_features(lab, spacing)
    if f["n"] == 0:
        return np.zeros_like(lab)
    v = np.asarray(f[feature], np.float64)
    ok = np.ones(v.shape, bool)
    if vmin is not None:
        ok &= v >= float(vmin)
    if vmax is not None:
        ok &= v <= float(vmax)
    return _renumber(lab, f["label"][ok])


def blob_select_largest(labels: Any, count: int = 1) -> np.ndarray:
    """面積の大きい順に ``count`` 個だけ残す(**番号は面積の降順に振り直す**)。

    同じ面積が並んだときは元の番号が小さいほうを先にする(実行ごとに順序が
    変わらないよう ``argsort`` を安定ソートで固定してある)。``count`` が
    物体数より多くても**あるだけ**返す(足りないことを例外にはしない ——
    「上位 3 個」を頼んで 2 個しか無いのは異常ではない)。
    """
    c = int(count)
    if c < 1:
        raise ValueError(f"blob_select_largest: count must be >= 1, got {count!r}")
    lab = _as_labels(labels, "blob_select_largest")
    f = blob_features(lab)
    if f["n"] == 0:
        return np.zeros_like(lab)
    order = np.argsort(-np.asarray(f["area"], np.float64), kind="stable")
    return _renumber(lab, f["label"][order[:c]])


# --------------------------------------------------------------------------- #
# 4. 取り出す                                                                  #
# --------------------------------------------------------------------------- #
def blob_region(labels: Any, index: int) -> np.ndarray:
    """物体 1 個を二値領域(bool)として抜く。``index`` は **1 起点**。"""
    lab = _as_labels(labels, "blob_region")
    i = int(index)
    n = int(lab.max())
    if i < 1 or i > n:
        raise ValueError(
            f"blob_region: index must be in 1..{n} (1-origin, 0 is background), "
            f"got {index!r}")
    return lab == i


def blob_boundaries(labels: Any) -> np.ndarray:
    """物体の輪郭(1 画素幅、bool)。**隣り合う物体の境目も残る**。

    内側の縁を取る(自分と違うラベルに隣接する前景画素)ので、輪郭は必ず
    物体の内部にある —— 外側を取ると隣の物体の画素を輪郭だと言うことになる。
    """
    lab = _as_labels(labels, "blob_boundaries")
    fg = lab > 0
    same = ndimage.grey_erosion(lab, footprint=np.ones((3, 3), bool)) == lab
    return fg & ~same


# --------------------------------------------------------------------------- #
# 5. 見る                                                                      #
# --------------------------------------------------------------------------- #
def blob_overlay(image: Any, labels: Any, alpha: float = 0.5,
                 seed: int = 0) -> np.ndarray:
    """元画像の上に物体を色分けして重ね、``(H, W, 3)`` の float RGB を返す。

    この族の**出口**。作れて測れるが見られない型にしないために置く。
    色は :func:`fullseye.colorize_labels` と同じ規則で、背景は元画像のまま。
    """
    import imgio

    lab = _as_labels(labels, "blob_overlay")
    a = float(alpha)
    if not (0.0 <= a <= 1.0):
        raise ValueError(f"blob_overlay: alpha must be in [0, 1], got {alpha!r}")
    img = np.asarray(image, np.float64)
    if img.ndim == 2:
        if img.shape != lab.shape:
            raise ValueError(
                f"blob_overlay: image {img.shape} and labels {lab.shape} differ")
        lo, hi = float(np.nanmin(img)), float(np.nanmax(img))
        g = (img - lo) / (hi - lo) if hi - lo > 1e-12 else np.zeros_like(img)
        base = np.repeat(np.nan_to_num(g)[:, :, None], 3, axis=2)
    elif img.ndim == 3 and img.shape[2] in (3, 4):
        if img.shape[:2] != lab.shape:
            raise ValueError(
                f"blob_overlay: image {img.shape[:2]} and labels {lab.shape} differ")
        base = np.clip(img[:, :, :3], 0.0, 1.0)
    else:
        raise ValueError(
            f"blob_overlay: image must be (H,W) or (H,W,3|4), got {img.shape}")

    colour = np.asarray(imgio.colorize_labels(lab, seed=seed), np.float64)[:, :, :3]
    m = (lab > 0)[:, :, None]
    return np.where(m, (1.0 - a) * base + a * colour, base)
