"""2D 計測(HALCON "2D Metrology" chapter の genuine core, numpy).

計測モデル(dict handle)に幾何オブジェクト(線/円/矩形/楕円)を登録し、apply で画像の
エッジ(勾配極大)を参照形状の近傍で測定して形状を再フィットする。古典的な subpixel なしの
genuine 計測。画像は [0,1] の 2D float64、点は (row, col)。
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage


def create_metrology_model() -> dict:
    """空の計測モデルを作る(create_metrology_model)。"""
    return {"objects": []}


def add_metrology_object_line_measure(model, row1, col1, row2, col2, n: int = 25) -> int:
    """直線計測オブジェクトを追加(add_metrology_object_line_measure)。index を返す。"""
    model["objects"].append({"type": "line", "p": (row1, col1, row2, col2), "n": n})
    return len(model["objects"]) - 1


def add_metrology_object_circle_measure(model, row, col, radius, n: int = 40) -> int:
    """円計測オブジェクトを追加(add_metrology_object_circle_measure)。"""
    model["objects"].append({"type": "circle", "p": (row, col, radius), "n": n})
    return len(model["objects"]) - 1


def add_metrology_object_rectangle2_measure(model, row, col, phi, l1, l2, n: int = 40) -> int:
    """矩形計測オブジェクトを追加(add_metrology_object_rectangle2_measure)。"""
    model["objects"].append({"type": "rect", "p": (row, col, phi, l1, l2), "n": n})
    return len(model["objects"]) - 1


def add_metrology_object_ellipse_measure(model, row, col, phi, ra, rb, n: int = 40) -> int:
    """楕円計測オブジェクトを追加(add_metrology_object_ellipse_measure)。"""
    model["objects"].append({"type": "ellipse", "p": (row, col, phi, ra, rb), "n": n})
    return len(model["objects"]) - 1


def add_metrology_object_generic(model, otype, params, n: int = 40) -> int:
    """汎用計測オブジェクトを追加(add_metrology_object_generic)。"""
    model["objects"].append({"type": otype, "p": tuple(params), "n": n})
    return len(model["objects"]) - 1


def _edge_on_profile(mag, r0, c0, dr, dc, half=6):
    """(r0,c0) を中心に (dr,dc) 方向へ ±half 探索し勾配極大の位置を返す。"""
    ts = np.arange(-half, half + 1)
    rs = np.clip((r0 + ts * dr).round().astype(int), 0, mag.shape[0] - 1)
    cs = np.clip((c0 + ts * dc).round().astype(int), 0, mag.shape[1] - 1)
    vals = mag[rs, cs]
    k = int(np.argmax(vals))
    return rs[k], cs[k], float(vals[k])


def apply_metrology_model(model, image) -> list:
    """各計測オブジェクトの近傍でエッジを測定し、形状を再フィットして結果を返す(apply_metrology_model)。"""
    img = np.asarray(image, dtype=np.float64)
    mag = np.hypot(ndimage.sobel(img, axis=1), ndimage.sobel(img, axis=0))
    results = []
    for obj in model["objects"]:
        t, p, n = obj["type"], obj["p"], obj["n"]
        pts, strengths = [], []
        if t == "line":
            r1, c1, r2, c2 = p
            ln = np.hypot(r2 - r1, c2 - c1) + 1e-9
            nr, nc = -(c2 - c1) / ln, (r2 - r1) / ln       # 法線
            for s in np.linspace(0, 1, n):
                r0, c0 = r1 + s * (r2 - r1), c1 + s * (c2 - c1)
                er, ec, st = _edge_on_profile(mag, r0, c0, nr, nc)
                pts.append((er, ec)); strengths.append(st)
        else:
            row, col = p[0], p[1]
            rad = p[2] if t == "circle" else max(p[3], p[4])
            for a in np.linspace(0, 2 * np.pi, n, endpoint=False):
                dr, dc = np.sin(a), np.cos(a)
                r0, c0 = row + rad * dr, col + rad * dc
                er, ec, st = _edge_on_profile(mag, r0, c0, dr, dc)
                pts.append((er, ec)); strengths.append(st)
        pts = np.array(pts, float)
        results.append({"type": t, "edge_points": pts,
                        "score": float(np.mean(strengths)) if strengths else 0.0,
                        "centroid": pts.mean(0) if len(pts) else np.zeros(2)})
    return results


def align_metrology_model(model, drow=0.0, dcol=0.0) -> dict:
    """計測モデルの全オブジェクトを平行移動して整列(align_metrology_model)。"""
    out = {"objects": []}
    for obj in model["objects"]:
        p = list(obj["p"])
        p[0] += drow
        p[1] += dcol
        out["objects"].append({**obj, "p": tuple(p)})
    return out
