"""1D 測定(エッジ抽出)(HALCON "1D Measuring" chapter genuine, numpy).

測定線/測定弧に沿ってグレープロファイルを取り、微分でエッジ・エッジ対を抽出。
キャリパー計測の中核。image = 2D float(グレー値の単位は入力のまま: [0,1] でも
0..255 でもよく、``amplitude``/``threshold`` はその単位)。measure = プロファイル取得の
設定 dict(``gen_measure_rectangle2`` / ``gen_measure_arc`` が作る)。

規約(2026-09-02 改訂):
  * プロファイルのサンプル間隔は **1 px**(矩形は厳密に 1、弧は弧長を整数分割した
    ≈1 px、``measure["spacing"]``)。``pos`` はサンプル index(= 測定開始点からの
    距離 / spacing)、``dist`` = 開始点からの距離 [px]、``row``/``col`` = 画像座標。
  * ``amplitude`` は **エッジ両側のグレー差**(符号つき: 測定方向に明るくなる
    立ち上がりが正)。HALCON の Amplitude と同じ意味で、平滑化 ``sigma`` に依存
    しない(以前は平滑化勾配のピーク値=グレー差の ~0.3 倍・sigma 依存だった)。
    ``threshold`` はこの |グレー差| に対する下限。
  * 測定矩形の端にかかるエッジも落とさない(内部で測定線を両端に延長して
    サンプルし、矩形内 [-0.5, n-0.5] のエッジだけ返す)。
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import map_coordinates, gaussian_filter1d


def gen_measure_rectangle2(row, col, phi, length1, length2, shape):
    """回転測定矩形(長軸 ``phi`` 方向に 1 px 間隔でプロファイルを取る)を定義
    (gen_measure_rectangle2)。サンプル数 n = round(2*length1)+1、始点は
    中心から -(n-1)/2 px の位置。``length2`` は幅方向の平均化幅 [px]。"""
    n = max(2, int(round(2.0 * float(length1))) + 1)
    t = np.arange(n, dtype=float) - (n - 1) / 2.0
    ca, sa = np.cos(phi), np.sin(phi)
    rows = row + t * sa
    cols = col + t * ca
    return {"type": "rect", "rows": rows, "cols": cols, "width": length2,
            "phi": phi, "shape": shape, "spacing": 1.0,
            "origin": (float(row), float(col)), "dir": (float(sa), float(ca)), "t": t}


def gen_measure_arc(center_row, center_col, radius, angle_start, angle_extent, width, shape):
    """測定弧(円周方向に ≈1 px 間隔でプロファイルを取る)を定義(gen_measure_arc)。
    サンプル数 n = round(|angle_extent|*radius)+1、``spacing`` = 弧長/(n-1)。"""
    arclen = abs(float(angle_extent)) * float(radius)
    n = max(2, int(round(arclen)) + 1)
    ang = angle_start + np.linspace(0.0, angle_extent, n)
    rows = center_row + radius * np.sin(ang)
    cols = center_col + radius * np.cos(ang)
    return {"type": "arc", "rows": rows, "cols": cols, "width": width, "shape": shape,
            "spacing": arclen / (n - 1), "center": (float(center_row), float(center_col)),
            "radius": float(radius), "angles": ang}


def _extended_coords(measure, k):
    """測定線を両端に k サンプル延長した (rows, cols)。矩形/弧は幾何定義から、
    それ以外は端点の接線で線形外挿。"""
    rows = np.asarray(measure["rows"], float); cols = np.asarray(measure["cols"], float)
    if k <= 0:
        return rows, cols
    if measure.get("type") == "rect" and "origin" in measure:
        t = np.asarray(measure["t"], float)
        te = np.concatenate([t[0] - np.arange(k, 0, -1), t, t[-1] + np.arange(1, k + 1)])
        r0, c0 = measure["origin"]; sa, ca = measure["dir"]
        return r0 + te * sa, c0 + te * ca
    if measure.get("type") == "arc" and "center" in measure:
        ang = np.asarray(measure["angles"], float)
        d = ang[1] - ang[0]
        ae = np.concatenate([ang[0] - d * np.arange(k, 0, -1), ang, ang[-1] + d * np.arange(1, k + 1)])
        r0, c0 = measure["center"]; rad = measure["radius"]
        return r0 + rad * np.sin(ae), c0 + rad * np.cos(ae)
    d0 = np.array([rows[1] - rows[0], cols[1] - cols[0]])
    d1 = np.array([rows[-1] - rows[-2], cols[-1] - cols[-2]])
    pre = np.array([[rows[0], cols[0]] - d0 * j for j in range(k, 0, -1)])
    post = np.array([[rows[-1], cols[-1]] + d1 * j for j in range(1, k + 1)])
    ext = np.vstack([pre, np.column_stack([rows, cols]), post])
    return ext[:, 0], ext[:, 1]


def _profile(image, measure, pad=0):
    """測定線(両端を ``pad`` サンプル延長)に沿った幅方向平均つきグレープロファイル。"""
    im = np.asarray(image, float)
    if im.ndim != 2:
        raise ValueError(f"image must be 2-D, got shape {im.shape}")
    rows, cols = _extended_coords(measure, int(pad))
    w = int(measure.get("width", 1))
    if w <= 1:
        return map_coordinates(im, [rows, cols], order=1, mode="nearest")
    # 幅方向(測定線の法線)に w サンプル平均
    dr = np.gradient(rows); dc = np.gradient(cols)
    norm = np.hypot(dr, dc) + 1e-12
    nr = -dc / norm; nc = dr / norm
    acc = np.zeros(len(rows))
    offs = np.linspace(-w / 2, w / 2, max(2, w))
    for o in offs:
        acc += map_coordinates(im, [rows + nr * o, cols + nc * o], order=1, mode="nearest")
    return acc / len(offs)


def _lobe_amplitude(sm, ag, i):
    """勾配ローブ(ピーク i から両側へ 1 % まで単調減少する範囲)の両端のグレー差。"""
    lo = i
    while lo > 0 and ag[lo - 1] < ag[lo] and ag[lo - 1] > 0.01 * ag[i]:
        lo -= 1
    hi = i
    while hi < len(ag) - 1 and ag[hi + 1] < ag[hi] and ag[hi + 1] > 0.01 * ag[i]:
        hi += 1
    return float(sm[hi] - sm[lo])


def measure_pos(image, measure, sigma=1.0, threshold=0.1, transition="all"):
    """測定線上のエッジ位置(サブピクセル)と振幅を抽出(measure_pos)。

    各エッジ: ``pos``(サンプル index、矩形は始点からの px)/ ``dist``(始点からの
    距離 [px])/ ``row``, ``col`` / ``amplitude``(符号つきグレー差)/ ``polarity``
    ("positive" = 測定方向に明るくなる)。``threshold`` は |amplitude| の下限、
    ``transition`` は "all" / "positive" / "negative"。"""
    n = len(measure["rows"])
    spacing = float(measure.get("spacing", 1.0))
    k = int(np.ceil(3.0 * max(float(sigma), 0.0))) + 2
    prof = _profile(image, measure, pad=k)
    sm = gaussian_filter1d(prof, sigma, mode="nearest") if sigma > 0 else prof
    g = np.gradient(sm, spacing)
    ag = np.abs(g)
    rows_e, cols_e = _extended_coords(measure, k)
    idx_e = np.arange(len(rows_e), dtype=float)
    edges = []
    for i in range(1, len(ag) - 1):
        if not (ag[i] >= ag[i - 1] and ag[i] > ag[i + 1] and ag[i] > 1e-12):
            continue
        amp = _lobe_amplitude(sm, ag, i)
        if abs(amp) < threshold:
            continue
        pol = "positive" if g[i] > 0 else "negative"
        if transition != "all" and transition != pol:
            continue
        den = ag[i - 1] - 2.0 * ag[i] + ag[i + 1]
        delta = 0.5 * (ag[i - 1] - ag[i + 1]) / den if abs(den) > 1e-12 else 0.0
        delta = float(np.clip(delta, -1.0, 1.0))
        pe = i + delta                                  # 延長プロファイル上の index
        pos = pe - k
        if pos < -0.5 or pos > n - 0.5:                 # 測定範囲の外
            continue
        row = float(np.interp(pe, idx_e, rows_e)); col = float(np.interp(pe, idx_e, cols_e))
        edges.append({"pos": float(pos), "dist": float(pos * spacing), "row": row, "col": col,
                      "amplitude": amp, "polarity": pol})
    return edges


def measure_pairs(image, measure, sigma=1.0, threshold=0.1):
    """立ち上がり/立ち下がりエッジのペア(構造の幅)を抽出(measure_pairs)。
    ``first``/``second`` = 各エッジの ``pos``、``width`` = 幅 [px]、
    ``first_point``/``second_point`` = (row, col)。"""
    edges = measure_pos(image, measure, sigma, threshold)
    spacing = float(measure.get("spacing", 1.0))
    pairs = []
    i = 0
    while i < len(edges) - 1:
        a = edges[i]; b = edges[i + 1]
        if a["polarity"] != b["polarity"]:
            pairs.append({"first": a["pos"], "second": b["pos"],
                          "width": (b["pos"] - a["pos"]) * spacing,
                          "first_point": (a["row"], a["col"]), "second_point": (b["row"], b["col"]),
                          "first_amplitude": a["amplitude"], "second_amplitude": b["amplitude"]})
            i += 2
        else:
            i += 1
    return pairs


def fuzzy_measure_pairing(image, measure, sigma=1.0, threshold=0.1, pair_size=None):
    """ファジィ基準(想定幅 pair_size)に最も合うエッジ対を選ぶ(fuzzy_measure_pairing)。"""
    pairs = measure_pairs(image, measure, sigma, threshold)
    if pair_size is None or not pairs:
        return pairs
    for p in pairs:
        p["fuzzy_score"] = float(np.exp(-((p["width"] - pair_size) / (0.5 * pair_size + 1e-9)) ** 2))
    pairs.sort(key=lambda p: -p["fuzzy_score"])
    return pairs


def translate_measure(measure, drow, dcol):
    """測定オブジェクトを平行移動(translate_measure)。"""
    m = dict(measure)
    m["rows"] = np.asarray(measure["rows"], float) + drow
    m["cols"] = np.asarray(measure["cols"], float) + dcol
    if "origin" in m:
        m["origin"] = (m["origin"][0] + drow, m["origin"][1] + dcol)
    if "center" in m:
        m["center"] = (m["center"][0] + drow, m["center"][1] + dcol)
    return m
