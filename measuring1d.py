"""1D 測定(エッジ抽出)(HALCON "1D Measuring" chapter genuine, numpy).

測定線/測定弧に沿ってグレープロファイルを取り、微分でエッジ・エッジ対を抽出。
キャリパー計測の中核。image = 2D float64。measure = プロファイル取得の設定 dict。
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import map_coordinates, gaussian_filter1d


def gen_measure_rectangle2(row, col, phi, length1, length2, shape):
    """回転測定矩形(長軸に沿ってプロファイルを取る)を定義(gen_measure_rectangle2)。"""
    n = int(2 * length1 + 1)
    t = np.linspace(-length1, length1, n)
    ca, sa = np.cos(phi), np.sin(phi)
    rows = row + t * sa
    cols = col + t * ca
    return {"type": "rect", "rows": rows, "cols": cols, "width": length2,
            "phi": phi, "shape": shape}


def gen_measure_arc(center_row, center_col, radius, angle_start, angle_extent, width, shape):
    """測定弧(円周方向にプロファイルを取る)を定義(gen_measure_arc)。"""
    n = int(abs(angle_extent) * radius) + 1
    ang = angle_start + np.linspace(0, angle_extent, n)
    rows = center_row + radius * np.sin(ang)
    cols = center_col + radius * np.cos(ang)
    return {"type": "arc", "rows": rows, "cols": cols, "width": width, "shape": shape}


def _profile(image, measure):
    """測定線に沿った(幅方向平均つき)グレープロファイル。"""
    im = np.asarray(image, float)
    rows = measure["rows"]; cols = measure["cols"]
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


def measure_pos(image, measure, sigma=1.0, threshold=0.1, transition="all"):
    """測定線上のエッジ位置(サブピクセル)と振幅を抽出(measure_pos)。"""
    prof = gaussian_filter1d(_profile(image, measure), sigma)
    d = np.gradient(prof)
    edges = []
    for i in range(1, len(d) - 1):
        if abs(d[i]) < threshold:
            continue
        if abs(d[i]) >= abs(d[i - 1]) and abs(d[i]) > abs(d[i + 1]):
            pol = "positive" if d[i] > 0 else "negative"
            if transition != "all" and transition != pol:
                continue
            denom = (d[i - 1] - 2 * d[i] + d[i + 1])
            sub = i - 0.5 * (d[i + 1] - d[i - 1]) / denom if abs(denom) > 1e-9 else i
            edges.append({"pos": float(sub), "amplitude": float(d[i]), "polarity": pol})
    return edges


def measure_pairs(image, measure, sigma=1.0, threshold=0.1):
    """立ち上がり/立ち下がりエッジのペア(構造の幅)を抽出(measure_pairs)。"""
    edges = measure_pos(image, measure, sigma, threshold)
    pairs = []
    i = 0
    while i < len(edges) - 1:
        a = edges[i]; b = edges[i + 1]
        if a["polarity"] != b["polarity"]:
            pairs.append({"first": a["pos"], "second": b["pos"],
                          "width": b["pos"] - a["pos"]})
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
    m["rows"] = measure["rows"] + drow
    m["cols"] = measure["cols"] + dcol
    return m
