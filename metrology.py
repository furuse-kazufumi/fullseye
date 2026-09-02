"""2D 計測(HALCON "2D Metrology" chapter の genuine core, numpy).

計測モデル(dict handle)に幾何オブジェクト(線/円/矩形/楕円)を登録し、apply で
**参照形状の法線方向**に短い測定線を張ってサブピクセルのエッジ位置を測り、
得られたエッジ点に形状を再フィット(``measure.fit_line`` / ``fit_circle`` /
``fit_ellipse`` / ``fit_rectangle2``)して幾何パラメータと RMS 残差を返す。

画像は 2D float64(グレー値の単位は任意。振幅 ``score`` はその単位のエッジ両側の
グレー差)、点は (row, col)。

角度規約(``gen_ellipse_contour_xld`` / ``gen_rectangle2_contour_xld`` と同じ):
``phi`` は col 軸(x)から row 軸(y, 画像下向き)へ測ったラジアン。楕円の ``ra`` は
``phi`` 方向の半径、``rb`` はその直交方向。矩形の ``l1`` は ``phi`` 方向の半辺長、
``l2`` は直交方向の半辺長。

2026-09-02 以前は楕円・矩形が「半径 max(axis) の円」として測られ再フィットも
無かった(40×15 の楕円が ra=36 rb=33 と出る)。現在は各形状の法線に沿って測る。
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter1d, map_coordinates


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
    """矩形計測オブジェクトを追加(add_metrology_object_rectangle2_measure)。
    ``phi`` = ``l1`` 辺の向き(col 軸から、ラジアン)、``l1``/``l2`` = 半辺長。"""
    model["objects"].append({"type": "rect", "p": (row, col, phi, l1, l2), "n": n})
    return len(model["objects"]) - 1


def add_metrology_object_ellipse_measure(model, row, col, phi, ra, rb, n: int = 40) -> int:
    """楕円計測オブジェクトを追加(add_metrology_object_ellipse_measure)。
    ``phi`` = ``ra`` 軸の向き(col 軸から、ラジアン)。"""
    model["objects"].append({"type": "ellipse", "p": (row, col, phi, ra, rb), "n": n})
    return len(model["objects"]) - 1


def add_metrology_object_generic(model, otype, params, n: int = 40) -> int:
    """汎用計測オブジェクトを追加(add_metrology_object_generic)。"""
    model["objects"].append({"type": otype, "p": tuple(params), "n": n})
    return len(model["objects"]) - 1


# ── 参照形状のサンプル点と法線 ──────────────────────────────────────────────── #
def _samples_line(p, n):
    r1, c1, r2, c2 = p
    ln = np.hypot(r2 - r1, c2 - c1)
    if ln < 1e-9:
        return np.zeros((0, 2)), np.zeros((0, 2))
    nr, nc = -(c2 - c1) / ln, (r2 - r1) / ln                 # 法線(単位)
    s = np.linspace(0.0, 1.0, int(n))
    pts = np.column_stack([r1 + s * (r2 - r1), c1 + s * (c2 - c1)])
    nrm = np.tile([nr, nc], (len(s), 1))
    return pts, nrm


def _samples_circle(p, n):
    row, col, rad = p
    a = np.linspace(0.0, 2 * np.pi, int(n), endpoint=False)
    nrm = np.column_stack([np.sin(a), np.cos(a)])
    return np.column_stack([row + rad * nrm[:, 0], col + rad * nrm[:, 1]]), nrm


def _samples_ellipse(p, n):
    row, col, phi, ra, rb = p
    t = np.linspace(0.0, 2 * np.pi, int(n), endpoint=False)
    x, y = ra * np.cos(t), rb * np.sin(t)                    # 局所 (x, y)
    ca, sa = np.cos(phi), np.sin(phi)
    pts = np.column_stack([row + x * sa + y * ca, col + x * ca - y * sa])
    nx, ny = np.cos(t) / ra, np.sin(t) / rb                  # 楕円の外向き法線 ∝ ∇F
    nrm = np.column_stack([nx * sa + ny * ca, nx * ca - ny * sa])
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-12
    return pts, nrm


def _samples_rect(p, n):
    row, col, phi, l1, l2 = p
    ca, sa = np.cos(phi), np.sin(phi)
    u = np.array([sa, ca])                                   # l1 軸 (row, col)
    v = np.array([ca, -sa])                                  # l2 軸 (row, col)
    c = np.array([row, col], float)
    per = max(2, int(n) // 4)
    pts, nrm = [], []
    # 長辺(±l2 オフセット、法線 ±v)と短辺(±l1 オフセット、法線 ±u)。角は避ける。
    s1 = np.linspace(-l1, l1, per + 2)[1:-1]
    s2 = np.linspace(-l2, l2, per + 2)[1:-1]
    for sign in (+1.0, -1.0):
        for s in s1:
            pts.append(c + u * s + v * (sign * l2)); nrm.append(v * sign)
        for s in s2:
            pts.append(c + u * (sign * l1) + v * s); nrm.append(u * sign)
    return np.asarray(pts), np.asarray(nrm)


_SAMPLERS = {"line": _samples_line, "circle": _samples_circle,
             "ellipse": _samples_ellipse, "rect": _samples_rect}


# ── 法線方向の 1D エッジ測定(サブピクセル) ─────────────────────────────────── #
def _edge_on_profile(img, r0, c0, dr, dc, half=6.0, sigma=1.0):
    """(r0,c0) を中心に法線 (dr,dc) 方向へ ±half [px] のプロファイルを取り、
    最強の勾配極大をパラボラ補間したサブピクセル位置と、エッジ両側のグレー差
    (符号つき、法線方向に増加なら正)を返す。エッジが無ければ None。"""
    k = int(np.ceil(half))
    ts = np.arange(-k, k + 1, dtype=float)
    prof = map_coordinates(img, [r0 + ts * dr, c0 + ts * dc], order=1, mode="nearest")
    sm = gaussian_filter1d(prof, sigma, mode="nearest") if sigma > 0 else prof
    g = np.gradient(sm)
    ag = np.abs(g)
    i = int(np.argmax(ag))
    if i == 0 or i == len(ag) - 1 or ag[i] < 1e-12:
        return None
    den = ag[i - 1] - 2.0 * ag[i] + ag[i + 1]
    delta = 0.5 * (ag[i - 1] - ag[i + 1]) / den if abs(den) > 1e-12 else 0.0
    delta = float(np.clip(delta, -1.0, 1.0))
    t = ts[i] + delta
    # 振幅 = 勾配ローブの両端でのグレー差(スムージング済プロファイル)
    lo = i
    while lo > 0 and ag[lo - 1] < ag[lo] and ag[lo - 1] > 0.01 * ag[i]:
        lo -= 1
    hi = i
    while hi < len(ag) - 1 and ag[hi + 1] < ag[hi] and ag[hi + 1] > 0.01 * ag[i]:
        hi += 1
    amp = float(sm[hi] - sm[lo]) if hi > lo else float(g[i])
    return r0 + t * dr, c0 + t * dc, amp


def _fit(t, pts):
    """エッジ点に参照形状をフィットし (params dict, rms) を返す。失敗は ValueError。"""
    import measure as me
    if t == "line":
        f = me.fit_line(pts)
        d = np.array([f["dy"], f["dx"]])
        rel = (pts - np.array([f["cy"], f["cx"]])) @ d
        p0 = np.array([f["cy"], f["cx"]]) + d * rel.min()
        p1 = np.array([f["cy"], f["cx"]]) + d * rel.max()
        return {"row1": float(p0[0]), "col1": float(p0[1]), "row2": float(p1[0]),
                "col2": float(p1[1]), "angle_deg": f["angle_deg"]}, f["rms"]
    if t == "circle":
        f = me.fit_circle(pts)
        return {"row": f["cy"], "col": f["cx"], "radius": f["r"]}, f["rms"]
    if t == "ellipse":
        f = me.fit_ellipse(pts)
        phi = float(np.radians(f["angle_deg"]))
        # 幾何 RMS(代数残差でなく、楕円中心からの半径方向距離)
        ca, sa = np.cos(phi), np.sin(phi)
        d = pts - np.array([f["cy"], f["cx"]])
        x = d[:, 1] * ca + d[:, 0] * sa
        y = -d[:, 1] * sa + d[:, 0] * ca
        ang = np.arctan2(y / f["rb"], x / f["ra"])
        ex, ey = f["ra"] * np.cos(ang), f["rb"] * np.sin(ang)
        rms = float(np.sqrt(np.mean((x - ex) ** 2 + (y - ey) ** 2)))
        return {"row": f["cy"], "col": f["cx"], "phi": phi, "ra": f["ra"], "rb": f["rb"]}, rms
    if t == "rect":
        f = me.fit_rectangle2(pts)
        return {"row": f["cy"], "col": f["cx"], "phi": float(np.radians(f["angle_deg"])),
                "l1": f["l1"], "l2": f["l2"]}, f["rms"]
    raise ValueError(f"unknown metrology object type {t!r}")


def apply_metrology_model(model, image, measure_length=6.0, sigma=1.0, threshold=0.05) -> list:
    """各計測オブジェクトの参照形状の法線に沿ってサブピクセルエッジを測り、形状を
    再フィットして結果を返す(apply_metrology_model)。

    ``measure_length`` = 法線方向の探索半幅 [px]、``sigma`` = プロファイル平滑化、
    ``threshold`` = 採用するエッジの最小グレー差(画像のグレー単位)。
    各結果 dict: ``type`` / ``edge_points`` (M,2) / ``amplitudes`` (M,) 符号つきグレー差 /
    ``score`` = 平均 |振幅| / ``centroid`` / ``params``(再フィット形状; 直線は
    row1,col1,row2,col2,angle_deg / 円は row,col,radius / 楕円は row,col,phi,ra>=rb /
    矩形は row,col,phi,l1>=l2)/ ``rms`` = フィット残差 [px]。エッジ点が足りず
    フィットできない場合は ``params=None``, ``rms=inf``, ``error`` に理由を入れる
    (他オブジェクトの計測は続行)。楕円・矩形の ``phi`` は長軸(ra / l1)の向き。
    """
    img = np.asarray(image, dtype=np.float64)
    if img.ndim != 2:
        raise ValueError(f"image must be 2-D, got shape {img.shape}")
    results = []
    for obj in model["objects"]:
        t, p, n = obj["type"], obj["p"], obj["n"]
        if t not in _SAMPLERS:
            raise ValueError(f"unknown metrology object type {t!r}")
        ref, nrm = _SAMPLERS[t](p, n)
        pts, amps = [], []
        for (r0, c0), (dr, dc) in zip(ref, nrm):
            e = _edge_on_profile(img, r0, c0, dr, dc, half=measure_length, sigma=sigma)
            if e is None or abs(e[2]) < threshold:
                continue
            pts.append((e[0], e[1])); amps.append(e[2])
        pts = np.asarray(pts, float).reshape(-1, 2)
        amps = np.asarray(amps, float)
        res = {"type": t, "edge_points": pts, "amplitudes": amps,
               "score": float(np.mean(np.abs(amps))) if len(amps) else 0.0,
               "centroid": pts.mean(0) if len(pts) else np.zeros(2),
               "params": None, "rms": float("inf")}
        try:
            res["params"], res["rms"] = _fit(t, pts)
        except ValueError as ex:
            res["error"] = str(ex)
        results.append(res)
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
