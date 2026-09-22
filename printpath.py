# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""printpath —— 3D プリンタのデータ(G-code / 3MF / スライス / 層画像の検査)を扱う op 族。numpy + 標準ライブラリのみ。

「形 → 層 → 経路 → 画像」の往復が全部 Fullseye の既存語彙で閉じる:

* **G-code**(RepRap / Marlin 系): ``gcode_read`` が G0/G1 の移動を**線分の表**(``table``: x0 y0 z0 x1 y1 z1 e f layer)
  に読む(G90/G91 の絶対・相対、M82/M83 の E の絶対・相対、G92 のリセット、G20/G21 の単位、``;`` コメント、
  ``;LAYER:`` の層番号か Z の増加で層を切る)。``gcode_write`` は表を G1 に書き戻す。``gcode_extrusion_volume`` は
  E [mm] × フィラメント断面積、``gcode_time_estimate`` は距離 / 送り(加速度を無視した下限)。
* **スライス**: ``mesh_slice_contours`` は三角形メッシュ(``mesh`` = (V, F))を平面 z で切って輪郭(``table``: ring x y)、
  ``mesh_slice_stack`` は層ごとの塗りつぶしマスクを ``voxel`` に、``contours_to_gcode`` は輪郭を周回する経路の表に
  (押し出し量は線幅 × 層厚 / 断面積)。
* **3MF**: ``read_3mf`` / ``write_3mf``(zip + XML の最小構成、依存なし)。
* **検査**: ``gcode_layer_image`` が経路を層のラスタ(``image2d``、線幅つき)に描き、``print_layer_defect_map`` が
  観測した層画像と期待の層画像を比べて「無いはずの所にある / あるはずの所に無い」を符号つきの図にする。

真値は自分で仕込める(輪郭 → 経路 → 画像 → 欠陥注入)ので、検出率を数字で言える(``examples/poc_print_layer_inspection.py``)。
入力は fail-closed(方言や欠けた座標は黙って補わず ValueError)。
"""
from __future__ import annotations

import io
import math
import os
import re
import zipfile
from typing import Any
from xml.etree import ElementTree as ET

import numpy as np
from scipy import ndimage as ndi

__all__ = [
    "MAX_GCODE_SEGMENTS", "MAX_LAYER_PIXELS",
    "gcode_read", "gcode_write", "gcode_extrusion_volume", "gcode_time_estimate", "gcode_layer_image",
    "mesh_slice_contours", "mesh_slice_stack", "contours_to_gcode",
    "read_3mf", "write_3mf",
    "print_layer_defect_map",
    "stipple_points_from_image",
    "stipple_energy",
    "stroke_tour_closed",
    "mst_length",
    "stroke_resample_closed",
    "stroke_tone_error",
]

#: 読む線分の上限(1 行 1 線分、これを超えたら ValueError —— 黙って間引かない)。
MAX_GCODE_SEGMENTS = 5_000_000
#: 層ラスタの上限画素数。
MAX_LAYER_PIXELS = 2 ** 26
_SEG_COLS = ("x0", "y0", "z0", "x1", "y1", "z1", "e", "f", "layer")
_WORD = re.compile(r"([A-Za-z])\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)")
_LAYER_TAG = re.compile(r";\s*LAYER\s*[:=]?\s*(\d+)", re.IGNORECASE)


# --------------------------------------------------------------------------- #
# 検査                                                                          #
# --------------------------------------------------------------------------- #
def _finite(x: Any, op: str, name: str, lo=None, hi=None) -> float:
    if isinstance(x, (bool, np.bool_, str)) or x is None:
        raise ValueError(f"{op}: {name} must be a number, got {x!r}")
    v = float(x)
    if not np.isfinite(v):
        raise ValueError(f"{op}: {name} must be finite, got {v}")
    if lo is not None and v < lo:
        raise ValueError(f"{op}: {name} must be >= {lo}, got {v}")
    if hi is not None and v > hi:
        raise ValueError(f"{op}: {name} must be <= {hi}, got {v}")
    return v


def _count(x: Any, op: str, name: str, lo: int, hi: int | None = None) -> int:
    if isinstance(x, (bool, np.bool_)) or not isinstance(x, (int, np.integer)):
        raise ValueError(f"{op}: {name} must be an integer, got {x!r}")
    v = int(x)
    if v < lo or (hi is not None and v > hi):
        raise ValueError(f"{op}: {name} must be in [{lo}, {hi if hi is not None else 'inf'}], got {v}")
    return v


def _path(p: Any, op: str, must_exist: bool) -> str:
    if not isinstance(p, str) or not p:
        raise ValueError(f"{op}: path must be a non-empty string, got {p!r}")
    if must_exist and not os.path.isfile(p):
        raise ValueError(f"{op}: file not found: {p}")
    return p


def _segments(table: Any, op: str) -> dict[str, np.ndarray]:
    """``gcode_read`` の表として受ける(列 x0 y0 z0 x1 y1 z1 e f layer、同じ長さ、有限)。"""
    if not isinstance(table, dict):
        raise ValueError(f"{op}: expected the segment table from gcode_read (a dict of columns), got {type(table).__name__}")
    missing = [c for c in _SEG_COLS if c not in table]
    if missing:
        raise ValueError(f"{op}: segment table lacks columns {missing}")
    out = {}
    n = None
    for c in _SEG_COLS:
        a = np.asarray(table[c], dtype=np.float64 if c != "layer" else np.int64).reshape(-1)
        if n is None:
            n = a.shape[0]
        elif a.shape[0] != n:
            raise ValueError(f"{op}: column {c} has {a.shape[0]} rows, expected {n}")
        if c != "layer" and not np.isfinite(a).all():
            raise ValueError(f"{op}: column {c} must be finite")
        out[c] = a
    if n == 0:
        raise ValueError(f"{op}: the segment table is empty")
    return out


def _mesh(mesh: Any, op: str) -> tuple[np.ndarray, np.ndarray]:
    if not isinstance(mesh, (tuple, list)) or len(mesh) != 2:
        raise ValueError(f"{op}: mesh must be a (V, F) pair, got {type(mesh).__name__}")
    V = np.asarray(mesh[0], dtype=np.float64)
    F = np.asarray(mesh[1])
    if V.ndim != 2 or V.shape[1] != 3 or V.shape[0] < 3 or not np.isfinite(V).all():
        raise ValueError(f"{op}: V must be finite (nv, 3) with nv >= 3, got shape {V.shape}")
    if F.ndim != 2 or F.shape[1] != 3 or F.shape[0] < 1 or not np.issubdtype(F.dtype, np.integer):
        raise ValueError(f"{op}: F must be integer (nf, 3) with nf >= 1, got shape {F.shape} dtype {F.dtype}")
    if F.min() < 0 or F.max() >= V.shape[0]:
        raise ValueError(f"{op}: F indexes vertices outside 0..{V.shape[0] - 1}")
    return V, F.astype(np.int64)


def _contours(table: Any, op: str) -> dict[str, np.ndarray]:
    if not isinstance(table, dict) or any(c not in table for c in ("ring", "x", "y")):
        raise ValueError(f"{op}: expected a contour table with columns ring / x / y (from mesh_slice_contours)")
    ring = np.asarray(table["ring"], dtype=np.int64).reshape(-1)
    x = np.asarray(table["x"], dtype=np.float64).reshape(-1)
    y = np.asarray(table["y"], dtype=np.float64).reshape(-1)
    if not (ring.shape == x.shape == y.shape) or ring.shape[0] == 0:
        raise ValueError(f"{op}: contour columns must be non-empty and the same length")
    if not (np.isfinite(x).all() and np.isfinite(y).all()):
        raise ValueError(f"{op}: contour coordinates must be finite")
    return {"ring": ring, "x": x, "y": y}


# --------------------------------------------------------------------------- #
# G-code                                                                        #
# --------------------------------------------------------------------------- #
def gcode_read(path: str, layer_from: str = "auto") -> dict[str, np.ndarray]:
    """G-code(RepRap / Marlin 系)を**線分の表** ``table`` に読む: 列 ``x0 y0 z0 x1 y1 z1``(mm)、``e``(その線分で
    押し出したフィラメント長 mm、移動だけなら 0)、``f``(送り mm/min)、``layer``(層番号)。

    解釈するのは G0 / G1(直線移動)、G90 / G91(座標の絶対 / 相対)、M82 / M83(E の絶対 / 相対)、G92(座標の
    リセット)、G20 / G21(インチ / mm)、``;`` コメント。円弧 G2 / G3 は**扱わない**(黙って直線にせず ValueError ——
    スライサで直線に展開して出力すること)。層は ``layer_from="tag"`` なら ``;LAYER:n`` のコメント、``"z"`` なら押し出し
    を伴う Z の増加で切る。``"auto"`` はタグがあればタグ、無ければ Z。座標が一度も与えられないまま押し出す行は
    ValueError(方言の穴を黙って 0 で埋めない)。

    >>> t = gcode_read("part.gcode")
    >>> t["e"].sum()                                       # 押し出したフィラメントの総長 [mm]
    """
    op = "gcode_read"
    p = _path(path, op, must_exist=True)
    if layer_from not in ("auto", "tag", "z"):
        raise ValueError(f"{op}: layer_from must be 'auto', 'tag' or 'z', got {layer_from!r}")
    with io.open(p, "r", encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    cols = {c: [] for c in _SEG_COLS}
    pos = {"X": None, "Y": None, "Z": None, "E": 0.0}
    absolute, e_absolute, scale = True, True, 1.0
    feed = None
    tag_layer = None
    have_tag = any(_LAYER_TAG.search(ln) for ln in lines[:5000]) or any(_LAYER_TAG.search(ln) for ln in lines)
    use_tag = layer_from == "tag" or (layer_from == "auto" and have_tag)
    z_layer, last_z_extrude = -1, None
    for ln_no, raw in enumerate(lines, 1):
        m = _LAYER_TAG.search(raw)
        if m:
            tag_layer = int(m.group(1))
        code = raw.split(";", 1)[0].strip()
        if not code:
            continue
        words = _WORD.findall(code)
        if not words:
            continue
        letter, num = words[0][0].upper(), words[0][1]
        cmd = "%s%d" % (letter, int(float(num)))
        params = {k.upper(): float(v) for k, v in words[1:]}
        if cmd in ("G20", "G21"):
            scale = 25.4 if cmd == "G20" else 1.0
        elif cmd in ("G90", "G91"):
            absolute = cmd == "G90"
        elif cmd in ("M82", "M83"):
            e_absolute = cmd == "M82"
        elif cmd == "G92":
            for k in ("X", "Y", "Z", "E"):
                if k in params:
                    pos[k] = params[k] * (scale if k != "E" else 1.0)
        elif cmd in ("G2", "G3"):
            raise ValueError(f"{op}: line {ln_no}: arc moves (G2/G3) are not supported — export with arcs expanded to lines")
        elif cmd in ("G0", "G1"):
            if "F" in params:
                feed = params["F"] * scale
            new = dict(pos)
            for k in ("X", "Y", "Z"):
                if k in params:
                    v = params[k] * scale
                    new[k] = v if (absolute or pos[k] is None) else pos[k] + v
            de = 0.0
            if "E" in params:
                ev = params["E"]
                de = (ev - pos["E"]) if e_absolute else ev
                new["E"] = ev if e_absolute else pos["E"] + ev
            moved = any(new[k] != pos[k] for k in ("X", "Y", "Z"))
            if moved or de != 0.0:
                if any(new[k] is None for k in ("X", "Y", "Z")):
                    missing = [k for k in ("X", "Y", "Z") if new[k] is None]
                    raise ValueError(f"{op}: line {ln_no}: a move before {missing} were ever set (dialect gap; not filled with 0)")
                if any(pos[k] is None for k in ("X", "Y", "Z")):
                    # 始点が未定義(最初の位置決め): 線分にはならない。押し出していたら方言の穴
                    if de > 0.0:
                        raise ValueError(f"{op}: line {ln_no}: extrusion before the start position was ever set")
                    pos = new
                    continue
                if de < 0.0:
                    de = 0.0                                              # リトラクトは押し出しに数えない
                if use_tag:
                    layer = tag_layer if tag_layer is not None else 0
                else:
                    if de > 0.0 and (last_z_extrude is None or new["Z"] > last_z_extrude + 1e-9):
                        z_layer += 1
                        last_z_extrude = new["Z"]
                    layer = max(z_layer, 0)
                if feed is None and moved:
                    raise ValueError(f"{op}: line {ln_no}: a move before any feed rate (F) was set")
                x0 = pos["X"] if pos["X"] is not None else new["X"]
                y0 = pos["Y"] if pos["Y"] is not None else new["Y"]
                z0 = pos["Z"] if pos["Z"] is not None else new["Z"]
                for c, v in zip(_SEG_COLS, (x0, y0, z0, new["X"], new["Y"], new["Z"], de, feed or 0.0, layer)):
                    cols[c].append(v)
                if len(cols["e"]) > MAX_GCODE_SEGMENTS:
                    raise ValueError(f"{op}: more than MAX_GCODE_SEGMENTS={MAX_GCODE_SEGMENTS} moves")
            pos = new
    if not cols["e"]:
        raise ValueError(f"{op}: no moves found in {p}")
    out = {c: np.asarray(cols[c], dtype=np.float64) for c in _SEG_COLS if c != "layer"}
    out["layer"] = np.asarray(cols["layer"], dtype=np.int64)
    return out


def gcode_write(table: Any, path: str, layer_tags: bool = True) -> str:
    """線分の表を G-code(G21 / G90 / M82、G1 の絶対座標と絶対 E)に書く。返りは書いたパス(``text``)。

    ``gcode_read`` と往復できる(層は ``;LAYER:n`` で書く)。移動だけの線分は E を進めない。
    """
    op = "gcode_write"
    seg = _segments(table, op)
    p = _path(path, op, must_exist=False)
    if not isinstance(layer_tags, (bool, np.bool_)):
        raise ValueError(f"{op}: layer_tags must be a bool")
    lines = ["; written by fullseye.printpath.gcode_write", "G21 ; mm", "G90 ; absolute coordinates", "M82 ; absolute E", "G92 E0"]
    e_abs = 0.0
    cur_layer = None
    first = True
    for i in range(seg["e"].shape[0]):
        if layer_tags and int(seg["layer"][i]) != cur_layer:
            cur_layer = int(seg["layer"][i])
            lines.append(";LAYER:%d" % cur_layer)
        if first or (seg["x0"][i], seg["y0"][i], seg["z0"][i]) != (seg["x1"][i - 1], seg["y1"][i - 1], seg["z1"][i - 1]):
            lines.append("G0 X%.5f Y%.5f Z%.5f F%.0f" % (seg["x0"][i], seg["y0"][i], seg["z0"][i], max(seg["f"][i], 1.0)))
            first = False
        e_abs += float(seg["e"][i])
        lines.append("G1 X%.5f Y%.5f Z%.5f E%.7f F%.0f" % (seg["x1"][i], seg["y1"][i], seg["z1"][i], e_abs, max(seg["f"][i], 1.0)))
    with io.open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    return p


def gcode_extrusion_volume(table: Any, filament_mm: float = 1.75) -> float:
    """押し出したフィラメントの体積 [mm³] = Σe × π (d / 2)²(``measurement``)。重さは密度 × 体積(PLA ≈ 1.24 g/cm³)。"""
    op = "gcode_extrusion_volume"
    seg = _segments(table, op)
    d = _finite(filament_mm, op, "filament_mm", lo=1e-6)
    return float(seg["e"].sum() * math.pi * (d / 2.0) ** 2)


def gcode_time_estimate(table: Any) -> float:
    """所要時間の下限 [s] = Σ(線分の長さ / 送り)(加速度・ジャークを無視、``measurement``)。送り 0 の線分は数えない。"""
    op = "gcode_time_estimate"
    seg = _segments(table, op)
    L = np.sqrt((seg["x1"] - seg["x0"]) ** 2 + (seg["y1"] - seg["y0"]) ** 2 + (seg["z1"] - seg["z0"]) ** 2)
    f = seg["f"]
    ok = f > 0.0
    return float((L[ok] / (f[ok] / 60.0)).sum())


def _raster_geometry(op, seg_or_pts_x, seg_or_pts_y, px_per_mm, bounds):
    if bounds is None:
        xmin, xmax = float(np.min(seg_or_pts_x)), float(np.max(seg_or_pts_x))
        ymin, ymax = float(np.min(seg_or_pts_y)), float(np.max(seg_or_pts_y))
        pad = 2.0
        xmin, xmax, ymin, ymax = xmin - pad, xmax + pad, ymin - pad, ymax + pad
    else:
        try:
            xmin, ymin, xmax, ymax = (float(v) for v in bounds)
        except (TypeError, ValueError):
            raise ValueError(f"{op}: bounds must be (xmin, ymin, xmax, ymax) in mm, got {bounds!r}") from None
        if not (xmax > xmin and ymax > ymin):
            raise ValueError(f"{op}: bounds must have xmax > xmin and ymax > ymin, got {bounds!r}")
    W = int(math.ceil((xmax - xmin) * px_per_mm))
    H = int(math.ceil((ymax - ymin) * px_per_mm))
    if W < 1 or H < 1 or W * H > MAX_LAYER_PIXELS:
        raise ValueError(f"{op}: raster of {H} x {W} px is empty or exceeds MAX_LAYER_PIXELS={MAX_LAYER_PIXELS}")
    return xmin, ymin, W, H


def gcode_layer_image(table: Any, layer: int, px_per_mm: float = 10.0, line_width_mm: float = 0.4,
                      bounds=None, travel: bool = False) -> np.ndarray:
    """1 層の経路を**線幅つきのラスタ** ``image2d``(0 / 1、y 下向き = 行)に描く。

    押し出しのある線分だけを ``line_width_mm`` の太さで塗る(``travel=True`` なら移動も細線で)。画素は ``px_per_mm``、
    範囲は ``bounds=(xmin, ymin, xmax, ymax)`` mm(無ければ表全体 + 2 mm の余白 —— 層をまたいで同じ範囲にしたければ
    渡す)。これが「この層はこう見えるはず」の期待像で、カメラの層画像と ``print_layer_defect_map`` で比べる。
    """
    op = "gcode_layer_image"
    seg = _segments(table, op)
    ly = _count(layer, op, "layer", 0)
    ppm = _finite(px_per_mm, op, "px_per_mm", lo=1e-6)
    lw = _finite(line_width_mm, op, "line_width_mm", lo=0.0)
    if not isinstance(travel, (bool, np.bool_)):
        raise ValueError(f"{op}: travel must be a bool")
    xmin, ymin, W, H = _raster_geometry(op, np.concatenate([seg["x0"], seg["x1"]]), np.concatenate([seg["y0"], seg["y1"]]), ppm, bounds)
    sel = seg["layer"] == ly
    if not sel.any():
        raise ValueError(f"{op}: layer {ly} has no moves (layers present: {np.unique(seg['layer']).tolist()[:10]}...)")
    img = np.zeros((H, W), dtype=np.float64)
    ext = sel & (seg["e"] > 0.0)
    _paint_segments(img, seg["x0"][ext], seg["y0"][ext], seg["x1"][ext], seg["y1"][ext], xmin, ymin, ppm, lw)
    if travel:
        trv = sel & (seg["e"] <= 0.0)
        _paint_segments(img, seg["x0"][trv], seg["y0"][trv], seg["x1"][trv], seg["y1"][trv], xmin, ymin, ppm, 0.0, value=0.5)
    return img


def _paint_segments(img, x0, y0, x1, y1, xmin, ymin, ppm, width_mm, value=1.0):
    """線分を画素へ(中心線を刻んで点を落とし、幅は距離変換で膨らませる)。"""
    if x0.shape[0] == 0:
        return
    H, W = img.shape
    core = np.zeros((H, W), dtype=bool)
    for a, b, c, d in zip(x0, y0, x1, y1):
        n = int(math.ceil(math.hypot(c - a, d - b) * ppm)) + 1
        t = np.linspace(0.0, 1.0, n)
        xs = np.clip(np.rint((a + (c - a) * t - xmin) * ppm).astype(int), 0, W - 1)
        ys = np.clip(np.rint((b + (d - b) * t - ymin) * ppm).astype(int), 0, H - 1)
        core[ys, xs] = True
    if width_mm > 0.0:
        r = width_mm * ppm / 2.0
        dist = ndi.distance_transform_edt(~core)
        img[dist <= r] = np.maximum(img[dist <= r], value)
    else:
        img[core] = np.maximum(img[core], value)


# --------------------------------------------------------------------------- #
# スライス                                                                      #
# --------------------------------------------------------------------------- #
def mesh_slice_contours(mesh: Any, z: float, tol: float = 1e-6) -> dict[str, np.ndarray]:
    """三角形メッシュを平面 ``z`` で切った**輪郭の表** ``table``: 列 ``ring``(輪の番号)、``x``、``y``(mm)。

    各三角形と平面の交差を線分にし、三角形の法線で向きを付けて(外輪郭は反時計回り、穴は時計回り)、端点を
    突き合わせて閉じた輪(閉じなければ開いた鎖)に繋ぐ(古典のスライサ)。輪の符号つき面積で中身と穴が分かる。
    頂点がちょうど平面に乗るときは ``tol`` だけ持ち上げて退化を避ける。平面が形に触れなければ ValueError
    (空の層は「無い」と言う)。
    """
    op = "mesh_slice_contours"
    V, F = _mesh(mesh, op)
    zc = _finite(z, op, "z")
    tl = _finite(tol, op, "tol", lo=0.0)
    zs = V[:, 2].copy()
    zs[np.abs(zs - zc) <= tl] += 2.0 * tl + 1e-12
    segs = []
    for tri in F:
        p = V[tri]
        h = zs[tri] - zc
        above = h > 0
        if above.all() or (~above).all():
            continue
        pts = []
        for i in range(3):
            j = (i + 1) % 3
            if above[i] != above[j]:
                t = h[i] / (h[i] - h[j])
                pts.append(p[i, :2] + t * (p[j, :2] - p[i, :2]))
        if len(pts) == 2:
            # 向き: 三角形の法線 n(頂点順の右手系)に対し n × ez の向きへ進む —— 外向き法線の立体は
            # 上から見て外輪郭が反時計回り、穴(内向き法線)は時計回りになる(符号つき面積で区別できる)
            nrm = np.cross(p[1] - p[0], p[2] - p[0])
            d = pts[1] - pts[0]
            if nrm[0] * d[1] - nrm[1] * d[0] < 0.0:                       # dot(d, ez × n) = d·(−ny, nx)
                pts = [pts[1], pts[0]]
            segs.append((pts[0], pts[1]))
    if not segs:
        raise ValueError(f"{op}: the plane z={zc} does not intersect the mesh (z range {V[:, 2].min():.4g}..{V[:, 2].max():.4g})")
    return _link_segments(np.asarray(segs, dtype=np.float64))


def _link_segments(S: np.ndarray, snap: float = 1e-6) -> dict[str, np.ndarray]:
    """有向の線分 (n, 2, 2) を「終点 → 次の始点」で繋いで輪にする(向きは保つ)。"""
    n = S.shape[0]
    key = np.round(S.reshape(-1, 2) / snap).astype(np.int64)
    _uniq, inv = np.unique(key, axis=0, return_inverse=True)
    inv = inv.reshape(n, 2)
    adj: dict[int, list[int]] = {}
    for s in range(n):
        adj.setdefault(int(inv[s, 0]), []).append(s)
    used = np.zeros(n, dtype=bool)
    rings, xs, ys = [], [], []
    ring_id = 0
    for start in range(n):
        if used[start]:
            continue
        used[start] = True
        chain = [S[start, 0], S[start, 1]]
        node = int(inv[start, 1])
        while True:
            nxt = None
            for s in adj.get(node, []):
                if not used[s]:
                    nxt = s
                    break
            if nxt is None:
                break
            used[nxt] = True
            chain.append(S[nxt, 1])
            node = int(inv[nxt, 1])
            if node == int(inv[start, 0]):
                break
        pts = np.asarray(chain)
        if len(pts) >= 2 and np.allclose(pts[0], pts[-1], atol=snap * 10):
            pts = pts[:-1]
        rings.append(np.full(len(pts), ring_id, dtype=np.int64))
        xs.append(pts[:, 0])
        ys.append(pts[:, 1])
        ring_id += 1
    return {"ring": np.concatenate(rings), "x": np.concatenate(xs), "y": np.concatenate(ys)}


def _fill_rings(ring, x, y, xmin, ymin, W, H, ppm) -> np.ndarray:
    """輪郭の内側を **nonzero winding** で塗る(走査線): 反時計回りの輪は +1、時計回りの輪(穴)は −1 を
    積み、正の所が中身。向きは ``mesh_slice_contours`` が三角形の法線から付ける。"""
    acc = np.zeros((H, W), dtype=np.int32)
    for rid in np.unique(ring):
        px = (x[ring == rid] - xmin) * ppm
        py = (y[ring == rid] - ymin) * ppm
        if len(px) < 3:
            continue
        area = 0.5 * float(np.sum(px * np.roll(py, -1) - np.roll(px, -1) * py))
        sign = 1 if area > 0.0 else -1
        for row in range(int(max(0, math.floor(py.min()))), int(min(H - 1, math.ceil(py.max()))) + 1):
            yc = row + 0.5
            xs = []
            for i in range(len(px)):
                j = (i + 1) % len(px)
                y0, y1 = py[i], py[j]
                if (y0 <= yc) != (y1 <= yc):
                    xs.append(px[i] + (yc - y0) / (y1 - y0) * (px[j] - px[i]))
            xs.sort()
            for a, b in zip(xs[0::2], xs[1::2]):
                lo, hi = int(math.ceil(a - 0.5)), int(math.floor(b - 0.5))
                if hi >= lo:
                    acc[row, max(lo, 0):min(hi, W - 1) + 1] += sign
    return acc > 0


def mesh_slice_stack(mesh: Any, layer_mm: float = 0.2, px_per_mm: float = 10.0, bounds=None) -> np.ndarray:
    """メッシュを ``layer_mm`` 刻みで切った**層マスクの積み** ``voxel`` (Z, Y, X)(0 / 1、Z は下から)。

    各層は ``mesh_slice_contours`` の輪郭を **nonzero winding** で塗る(外向き法線の輪は中身、内向き法線 = 穴の輪は
    引く。穴だけが残る層は空)。メッシュの面の向きが揃っていることが前提(STL / 3MF の規約)。``bounds`` は x–y の
    範囲(mm)、無ければメッシュ全体 + 2 mm。形に触れない層(上下の端)は 0 のまま。
    """
    op = "mesh_slice_stack"
    V, F = _mesh(mesh, op)
    dz = _finite(layer_mm, op, "layer_mm", lo=1e-6)
    ppm = _finite(px_per_mm, op, "px_per_mm", lo=1e-6)
    xmin, ymin, W, H = _raster_geometry(op, V[:, 0], V[:, 1], ppm, bounds)
    z0, z1 = float(V[:, 2].min()), float(V[:, 2].max())
    nz = int(math.ceil((z1 - z0) / dz))
    if nz < 1 or nz * H * W > MAX_LAYER_PIXELS * 4:
        raise ValueError(f"{op}: {nz} layers of {H} x {W} px is empty or too large")
    out = np.zeros((nz, H, W), dtype=np.float64)
    for k in range(nz):
        zc = z0 + (k + 0.5) * dz
        try:
            c = mesh_slice_contours((V, F), zc)
        except ValueError:
            continue
        out[k] = _fill_rings(c["ring"], c["x"], c["y"], xmin, ymin, W, H, ppm)
    return out


def contours_to_gcode(contours: Any, z: float, layer: int = 0, layer_mm: float = 0.2, line_width_mm: float = 0.4,
                      filament_mm: float = 1.75, feed_mm_min: float = 1800.0) -> dict[str, np.ndarray]:
    """輪郭(``mesh_slice_contours`` の表)を**周回する経路の表**に(``gcode_read`` と同じ列)。

    最小のスライサ: 各輪を順に一周し、押し出し量は ``線分長 × 線幅 × 層厚 / フィラメント断面積``。輪と輪の間は
    移動(e = 0)。真値つきの合成 G-code を作るための道具で、インフィルやリトラクトは持たない。
    """
    op = "contours_to_gcode"
    c = _contours(contours, op)
    zc = _finite(z, op, "z")
    ly = _count(layer, op, "layer", 0)
    h = _finite(layer_mm, op, "layer_mm", lo=1e-6)
    w = _finite(line_width_mm, op, "line_width_mm", lo=1e-6)
    d = _finite(filament_mm, op, "filament_mm", lo=1e-6)
    f = _finite(feed_mm_min, op, "feed_mm_min", lo=1e-6)
    area = math.pi * (d / 2.0) ** 2
    cols = {k: [] for k in _SEG_COLS}
    prev = None
    for rid in np.unique(c["ring"]):
        px, py = c["x"][c["ring"] == rid], c["y"][c["ring"] == rid]
        if len(px) < 2:
            continue
        pts = np.column_stack([px, py])
        pts = np.vstack([pts, pts[:1]])                                 # 閉じる
        if prev is not None:
            for k, v in zip(_SEG_COLS, (prev[0], prev[1], zc, pts[0, 0], pts[0, 1], zc, 0.0, f, ly)):
                cols[k].append(v)
        for i in range(len(pts) - 1):
            L = float(np.hypot(pts[i + 1, 0] - pts[i, 0], pts[i + 1, 1] - pts[i, 1]))
            for k, v in zip(_SEG_COLS, (pts[i, 0], pts[i, 1], zc, pts[i + 1, 0], pts[i + 1, 1], zc, L * w * h / area, f, ly)):
                cols[k].append(v)
        prev = pts[-1]
    if not cols["e"]:
        raise ValueError(f"{op}: no ring with 2 or more points")
    out = {k: np.asarray(cols[k], dtype=np.float64) for k in _SEG_COLS if k != "layer"}
    out["layer"] = np.asarray(cols["layer"], dtype=np.int64)
    return out


# --------------------------------------------------------------------------- #
# 3MF                                                                          #
# --------------------------------------------------------------------------- #
_NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"


def read_3mf(path: str) -> tuple[np.ndarray, np.ndarray]:
    """3MF(zip の中の ``3D/3dmodel.model``、3MF Core Specification)を三角形メッシュ ``mesh`` = (V, F) に読む。

    複数の ``<object>`` は頂点を連結して 1 つのメッシュに(``<build>`` の変換行列は 3×4 の ``transform`` を適用)。
    単位は ``<model unit>``(既定 millimeter、inch / centimeter / meter / micron は mm に換算)。
    """
    op = "read_3mf"
    p = _path(path, op, must_exist=True)
    try:
        with zipfile.ZipFile(p) as zf:
            names = zf.namelist()
            model = next((n for n in names if n.lower().endswith(".model")), None)
            if model is None:
                raise ValueError(f"{op}: no .model part in {p}")
            root = ET.fromstring(zf.read(model))
    except zipfile.BadZipFile:
        raise ValueError(f"{op}: not a zip container: {p}") from None
    except ET.ParseError as e:
        raise ValueError(f"{op}: malformed XML in the model part: {e}") from None
    unit = {"millimeter": 1.0, "inch": 25.4, "centimeter": 10.0, "meter": 1000.0, "micron": 1e-3, "foot": 304.8}
    scale = unit.get(root.get("unit", "millimeter"))
    if scale is None:
        raise ValueError(f"{op}: unknown unit {root.get('unit')!r}")
    ns = {"m": _NS}
    objs = {}
    for obj in root.findall(".//m:resources/m:object", ns):
        mesh_el = obj.find("m:mesh", ns)
        if mesh_el is None:
            continue
        V = np.array([[float(v.get("x")), float(v.get("y")), float(v.get("z"))] for v in mesh_el.findall("m:vertices/m:vertex", ns)], dtype=np.float64)
        F = np.array([[int(t.get("v1")), int(t.get("v2")), int(t.get("v3"))] for t in mesh_el.findall("m:triangles/m:triangle", ns)], dtype=np.int64)
        if V.size and F.size:
            objs[obj.get("id")] = (V.reshape(-1, 3), F.reshape(-1, 3))
    if not objs:
        raise ValueError(f"{op}: no mesh object in {p}")
    Vs, Fs, off = [], [], 0
    items = root.findall(".//m:build/m:item", ns) or [None]
    for it in items:
        if it is None:
            chosen = list(objs.values())
            T = None
        else:
            if it.get("objectid") not in objs:
                continue
            chosen = [objs[it.get("objectid")]]
            T = it.get("transform")
        for V, F in chosen:
            V = V * scale
            if T:
                m = np.array([float(v) for v in T.split()], dtype=np.float64)
                if m.shape[0] != 12:
                    raise ValueError(f"{op}: transform must have 12 numbers, got {m.shape[0]}")
                M = m.reshape(4, 3)
                V = V @ M[:3] + M[3]
            Vs.append(V)
            Fs.append(F + off)
            off += V.shape[0]
    if not Vs:
        raise ValueError(f"{op}: build items reference no mesh object")
    return np.vstack(Vs), np.vstack(Fs)


def write_3mf(path: str, mesh: Any) -> str:
    """三角形メッシュを 3MF(最小構成: ``[Content_Types].xml`` / ``_rels/.rels`` / ``3D/3dmodel.model``、単位 mm)に書く。返りはパス(``text``)。"""
    op = "write_3mf"
    p = _path(path, op, must_exist=False)
    V, F = _mesh(mesh, op)
    verts = "".join('<vertex x="%.6g" y="%.6g" z="%.6g"/>' % tuple(v) for v in V)
    tris = "".join('<triangle v1="%d" v2="%d" v3="%d"/>' % tuple(t) for t in F)
    model = ('<?xml version="1.0" encoding="UTF-8"?>'
             '<model unit="millimeter" xml:lang="en-US" xmlns="%s">'
             '<resources><object id="1" type="model"><mesh><vertices>%s</vertices><triangles>%s</triangles></mesh></object></resources>'
             '<build><item objectid="1"/></build></model>' % (_NS, verts, tris))
    ctypes = ('<?xml version="1.0" encoding="UTF-8"?>'
              '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
              '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
              '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", ctypes)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("3D/3dmodel.model", model)
    return p


# --------------------------------------------------------------------------- #
# 検査                                                                          #
# --------------------------------------------------------------------------- #
def print_layer_defect_map(observed: Any, expected: Any, tolerance_px: int = 2, threshold: float = 0.5) -> np.ndarray:
    """観測した層画像と期待の層画像(``gcode_layer_image``)を比べた**符号つきの欠陥図** ``image2d``:
    +1 = あるはずの所に無い(欠け・詰まり)、−1 = 無いはずの所にある(糸引き・はみ出し・spaghetti)、0 = 一致。

    両方を ``threshold`` で二値化し、``tolerance_px`` だけ膨らませた相手に含まれない画素だけを欠陥にする(位置ずれと
    線幅の揺れを許す)。位置合わせはしない —— カメラ像は先に ``gcode_layer_image`` と同じ画素格子へ写しておく。
    """
    op = "print_layer_defect_map"
    A = np.asarray(observed, dtype=np.float64)
    B = np.asarray(expected, dtype=np.float64)
    if A.ndim != 2 or A.shape != B.shape or A.size == 0:
        raise ValueError(f"{op}: observed and expected must be the same non-empty 2-D shape, got {A.shape} vs {B.shape}")
    if not (np.isfinite(A).all() and np.isfinite(B).all()):
        raise ValueError(f"{op}: images must be finite")
    tp = _count(tolerance_px, op, "tolerance_px", 0, 1000)
    th = _finite(threshold, op, "threshold")
    a, b = A >= th, B >= th
    if tp > 0:
        da = ndi.binary_dilation(a, iterations=tp)
        db = ndi.binary_dilation(b, iterations=tp)
    else:
        da, db = a, b
    out = np.zeros(A.shape, dtype=np.float64)
    out[b & ~da] = 1.0
    out[a & ~db] = -1.0
    return out


# --------------------------------------------------------------------------- #
# 濃淡 → 1 本の閉じた線(2026-09-22)—— TSP art をこの族に置く理由               #
#   ★ペンプロッタの経路と 3D プリンタの経路は**同じ対象**(順に回る線分の列)で、 #
#   出口も同じ(contours_to_gcode → gcode_write / gcode_time_estimate)。        #
#   だから族を新しく立てず、ここに stroke カテゴリとして足す。                   #
#   参考: Kaplan & Bosch, "TSP Art", Computational Aesthetics 2005。           #
# --------------------------------------------------------------------------- #
#: 点描の距離。"euclidean" 以外は将来。
STIPPLE_METRICS: tuple[str, ...] = ("euclidean",)

#: 巡回路の初期解の作り方。
TOUR_STARTS: tuple[str, ...] = ("nearest", "sorted", "given")


def _stroke_gray(img, op):
    a = np.asarray(img, dtype=np.float64)
    if a.ndim == 3 and a.shape[2] in (3, 4):
        a = a[..., :3] @ np.array([0.299, 0.587, 0.114])
    if a.ndim != 2:
        raise ValueError("%s: image must be 2-D grey or (H, W, 3/4) colour "
                         "(received: %s)" % (op, (a.shape,)))
    if a.shape[0] < 4 or a.shape[1] < 4:
        raise ValueError("%s: image is %dx%d; at least 4x4 is needed to place "
                         "points by density" % (op, a.shape[0], a.shape[1]))
    if not np.all(np.isfinite(a)):
        raise ValueError("%s: image contains non-finite values" % op)
    return a


def _stroke_points(points, op, name="points"):
    p = np.asarray(points, dtype=np.float64)
    if p.ndim != 2 or p.shape[1] != 2:
        raise ValueError("%s: %s must be (N, 2) (received: %s)" % (op, name, (p.shape,)))
    if p.shape[0] < 3:
        raise ValueError("%s: %s needs at least 3 points (received: %d)"
                         % (op, name, p.shape[0]))
    if not np.all(np.isfinite(p)):
        raise ValueError("%s: %s contains non-finite values" % (op, name))
    return p


def stipple_points_from_image(image, n_points, iterations=30, gamma=1.0,
                              floor=0.02, seed=0, metric="euclidean"):
    """濃淡を**点の密度**に写す(重みつき Lloyd = 重心ボロノイ)。→ ``pairs``

    暗いところに点が密に集まる。返るのは ``(n_points, 2)`` の **(row, col)**。

    引数:
        image: 明るさ ``[0, 1]`` の 2-D(または色。輝度に落とす)。
        n_points: 点の数。
        iterations: Lloyd の反復回数。
        gamma: 重みを ``darkness ** gamma`` にする(1 = 暗さそのまま)。
        floor: 重みの下限。**0 にしない** —— 真っ白な領域の重みが厳密に 0 だと
            そこへ入った点が動けず(重心が 0/0)、位置が入力に依らなくなる。
        seed: 初期配置の乱数。
        metric: いまは ``"euclidean"`` のみ。

    返り値のほかに、収束の様子は :func:`stipple_points_from_image` を
    ``iterations`` を変えて呼び比べれば測れる(Lloyd のエネルギーは単調減少する)。

    ★**真っ白な画像でも点は等間隔に散る**(密度が一定なら重心ボロノイは均等)。
    そこが「濃淡を読めている」ことの対照群になる。
    """
    op = "stipple_points_from_image"
    if metric not in STIPPLE_METRICS:
        raise ValueError("%s: metric must be one of %s (received: %r)"
                         % (op, STIPPLE_METRICS, metric))
    a = _stroke_gray(image, op)
    if isinstance(n_points, bool) or not isinstance(n_points, (int, np.integer)):
        raise ValueError("%s: n_points must be an int (received: %r)" % (op, n_points))
    n = int(n_points)
    if n < 3:
        raise ValueError("%s: n_points must be at least 3 (received: %d)" % (op, n))
    if a.size < n:
        raise ValueError("%s: the image has %d pixels but %d points were asked for — "
                         "more points than pixels cannot represent a density"
                         % (op, a.size, n))
    if not (0.0 < float(floor) <= 1.0):
        raise ValueError("%s: floor must lie in (0, 1] (received: %r) — a floor of 0 "
                         "leaves points in white regions with a 0/0 centroid, so their "
                         "position stops depending on the input" % (op, floor))
    if float(gamma) <= 0.0:
        raise ValueError("%s: gamma must be positive (received: %r)" % (op, gamma))
    if isinstance(iterations, bool) or not isinstance(iterations, (int, np.integer)) \
            or int(iterations) < 0:
        raise ValueError("%s: iterations must be a non-negative int (received: %r)"
                         % (op, iterations))

    h, w = a.shape
    lo, hi = float(a.min()), float(a.max())
    dark = (hi - a) / (hi - lo) if hi > lo else np.zeros_like(a)
    weight = np.maximum(dark ** float(gamma), float(floor))

    rng = np.random.default_rng(int(seed))
    flat = weight.ravel() / weight.sum()
    idx = rng.choice(flat.size, size=n, replace=True, p=flat)
    pts = np.stack([(idx // w).astype(np.float64) + rng.random(n),
                    (idx % w).astype(np.float64) + rng.random(n)], axis=1)

    rr, cc = np.mgrid[0:h, 0:w]
    rr = rr.astype(np.float64).ravel()
    cc = cc.astype(np.float64).ravel()
    wf = weight.ravel()
    for _ in range(int(iterations)):
        d = ((rr[:, None] - pts[None, :, 0]) ** 2
             + (cc[:, None] - pts[None, :, 1]) ** 2)
        owner = np.argmin(d, axis=1)
        num_r = np.bincount(owner, weights=wf * rr, minlength=n)
        num_c = np.bincount(owner, weights=wf * cc, minlength=n)
        den = np.bincount(owner, weights=wf, minlength=n)
        move = den > 0.0
        pts[move, 0] = num_r[move] / den[move]
        pts[move, 1] = num_c[move] / den[move]
    return np.ascontiguousarray(pts)


def stipple_energy(image, points, gamma=1.0, floor=0.02):
    """重みつき Lloyd のエネルギー ``Σ w(x) |x - c(x)|^2``(単調減少の検査用)。"""
    op = "stipple_energy"
    a = _stroke_gray(image, op)
    p = _stroke_points(points, op)
    h, w = a.shape
    lo, hi = float(a.min()), float(a.max())
    dark = (hi - a) / (hi - lo) if hi > lo else np.zeros_like(a)
    weight = np.maximum(dark ** float(gamma), float(floor)).ravel()
    rr, cc = np.mgrid[0:h, 0:w]
    d = ((rr.astype(np.float64).ravel()[:, None] - p[None, :, 0]) ** 2
         + (cc.astype(np.float64).ravel()[:, None] - p[None, :, 1]) ** 2)
    return float((weight * d.min(axis=1)).sum())


def _stroke_tour_len(p, order):
    q = p[order]
    d = np.hypot(np.diff(q[:, 0], append=q[0, 0]), np.diff(q[:, 1], append=q[0, 1]))
    return float(d.sum())


def _stroke_nn_order(p):
    n = p.shape[0]
    unseen = np.ones(n, dtype=bool)
    order = np.empty(n, dtype=np.int64)
    cur = 0
    order[0] = cur
    unseen[cur] = False
    for k in range(1, n):
        d = (p[:, 0] - p[cur, 0]) ** 2 + (p[:, 1] - p[cur, 1]) ** 2
        d[~unseen] = np.inf
        cur = int(np.argmin(d))
        order[k] = cur
        unseen[cur] = False
    return order


def _stroke_two_opt(p, order, rounds):
    """2-opt。長さが**減るときだけ**辺を張り替えるので、長さは単調非増加。"""
    n = order.size
    best = order.copy()
    for _ in range(int(rounds)):
        improved = False
        q = p[best]
        for i in range(n - 1):
            a1, a2 = q[i], q[(i + 1) % n]
            d_a = np.hypot(a1[0] - a2[0], a1[1] - a2[1])
            j0 = i + 2
            if j0 >= n:
                break
            b1 = q[j0:n]
            b2 = q[(np.arange(j0, n) + 1) % n]
            d_b = np.hypot(b1[:, 0] - b2[:, 0], b1[:, 1] - b2[:, 1])
            n_a = np.hypot(a1[0] - b1[:, 0], a1[1] - b1[:, 1])
            n_b = np.hypot(a2[0] - b2[:, 0], a2[1] - b2[:, 1])
            gain = (d_a + d_b) - (n_a + n_b)
            k = int(np.argmax(gain))
            if gain[k] > 1e-12:
                j = j0 + k
                best[i + 1:j + 1] = best[i + 1:j + 1][::-1]
                q = p[best]
                improved = True
        if not improved:
            break
    return best


def mst_length(points):
    """最小全域木の長さ(Prim)。**閉じた巡回路はこれより短くなれない**(下界)。"""
    p = _stroke_points(points, "mst_length")
    n = p.shape[0]
    inside = np.zeros(n, dtype=bool)
    inside[0] = True
    best = np.hypot(p[:, 0] - p[0, 0], p[:, 1] - p[0, 1])
    best[0] = np.inf
    total = 0.0
    for _ in range(n - 1):
        j = int(np.argmin(np.where(inside, np.inf, best)))
        total += float(best[j])
        inside[j] = True
        d = np.hypot(p[:, 0] - p[j, 0], p[:, 1] - p[j, 1])
        best = np.minimum(best, d)
    return total


def stroke_tour_closed(points, start="nearest", two_opt_rounds=8, order=None):
    """点を 1 回ずつ通って戻る**閉じた巡回路**に並べ替える。→ ``pairs``

    返るのは入力と同じ点を並べ替えた ``(N, 2)``。**最後の点から最初の点へ戻る**
    ことで閉じる(末尾に先頭を重複させない)。

    ★これは最適な巡回路ではない(TSP は NP 困難)。**下界と比べて質を言う**:
    閉じた巡回路は最小全域木より短くなれないので ``length / mst_length`` が
    1 に近いほど良い。一様な点なら Beardwood–Halton–Hammersley の
    ``0.7124 √(n A)`` も目安になる。**黄金ファイルは使わない。**
    """
    op = "stroke_tour_closed"
    if start not in TOUR_STARTS:
        raise ValueError("%s: start must be one of %s (received: %r)"
                         % (op, TOUR_STARTS, start))
    p = _stroke_points(points, op)
    n = p.shape[0]
    if start == "given":
        if order is None:
            raise ValueError("%s: start='given' needs an explicit order" % op)
        o = np.asarray(order, dtype=np.int64).ravel()
        if o.size != n or sorted(o.tolist()) != list(range(n)):
            raise ValueError("%s: order must be a permutation of 0..%d" % (op, n - 1))
    elif start == "sorted":
        o = np.lexsort((p[:, 1], p[:, 0]))
    else:
        o = _stroke_nn_order(p)
    if isinstance(two_opt_rounds, bool) or not isinstance(two_opt_rounds, (int, np.integer)) \
            or int(two_opt_rounds) < 0:
        raise ValueError("%s: two_opt_rounds must be a non-negative int (received: %r)"
                         % (op, two_opt_rounds))
    o = _stroke_two_opt(p, o, two_opt_rounds)
    return np.ascontiguousarray(p[o])


def stroke_resample_closed(points, n_points, allow_shortening=False):
    """閉じた線を**等弧長**に打ち直す。→ ``pairs``

    フーリエへ渡す前段。★媒介変数の取り方で係数が変わる(実測で最大 47 倍)ので、
    ここは**弧長で等間隔**と明示する。弧長の間隔は機械精度で一定(実測 cv 1e-14)。

    ★**ただし打ち直すと線は短くなる**: 標本と標本を結ぶのは弦なので、折れ点で角を
    切る。実測(300 頂点の巡回路): 標本 4000 で長さ 99.1 %、1024 で 96.9 %、
    300(頂点と同数)で 89.3 %、100 で 72.8 %、50 で **57.7 %**。長さが変われば
    濃淡の再現も壊れるので、**入力の頂点数より少ない標本は既定で拒否する**
    (意図してならば ``allow_shortening=True``)。
    """
    op = "stroke_resample_closed"
    p = _stroke_points(points, op)
    if isinstance(n_points, bool) or not isinstance(n_points, (int, np.integer)) \
            or int(n_points) < 3:
        raise ValueError("%s: n_points must be an int >= 3 (received: %r)" % (op, n_points))
    if int(n_points) < p.shape[0] and not allow_shortening:
        raise ValueError(
            "%s: n_points=%d is fewer than the %d input vertices — resampling at "
            "equal arc length joins the samples with chords, so the stroke gets "
            "shorter by cutting corners (measured: 89%% of the length at one sample "
            "per vertex, 58%% at one sixth). A shorter stroke no longer reproduces "
            "the tone it was built for, so this is refused rather than done quietly; "
            "pass allow_shortening=True if that is what you want."
            % (op, int(n_points), p.shape[0]))
    q = np.vstack([p, p[0]])
    seg = np.hypot(np.diff(q[:, 0]), np.diff(q[:, 1]))
    t = np.concatenate([[0.0], np.cumsum(seg)])
    total = float(t[-1])
    if total <= 0.0:
        raise ValueError("%s: the stroke has zero length (all points coincide)" % op)
    want = np.linspace(0.0, total, int(n_points), endpoint=False)
    return np.ascontiguousarray(np.stack([np.interp(want, t, q[:, 0]),
                                          np.interp(want, t, q[:, 1])], axis=1))


def stroke_tone_error(image, points, pen_width=1.0, blur_sigma=3.0, gamma=1.0):
    """線を引いた結果の**濃淡**が目標とどれだけ違うか。→ ``table``

    ★これが一筆書きの**本当の目的関数**。「絵として似ている」を人の目に任せず、
    ペン幅で描いて目の尺度にぼかし、目標の暗さと比べて数で返す。

    返り値: dict
        "rms" / "max_abs" / "bias" —— 暗さの差(``[0, 1]`` の尺度)
        "corr" —— 目標の暗さと描いた暗さの相関(1 に近いほど濃淡を追えている)
        "ink_fraction" —— 紙に乗ったインクの面積率
        "target_darkness" —— 目標の平均暗さ(インク率と釣り合うべき量)
        "length_px" —— 線の長さ[px]

    ★**ペン幅は連続なノブ**(被覆率で塗る)。線が重ならない範囲では
    ``インク率 ≈ 線長 × ペン幅 / 画像の面積`` が成り立つので、目標の濃さに合う
    ペン幅を **閉形式で解いてから**確かめられる:
    ``pen_width ≈ target_darkness × area / length_px``。
    """
    op = "stroke_tone_error"
    a = _stroke_gray(image, op)
    p = _stroke_points(points, op)
    if float(pen_width) <= 0.0:
        raise ValueError("%s: pen_width must be positive (received: %r)" % (op, pen_width))
    if float(blur_sigma) <= 0.0:
        raise ValueError("%s: blur_sigma must be positive (received: %r) — the tone of a "
                         "line drawing only exists at a scale coarser than the line"
                         % (op, blur_sigma))
    h, w = a.shape
    ink = np.zeros((h, w), dtype=np.float64)
    q = np.vstack([p, p[0]])
    seg = np.hypot(np.diff(q[:, 0]), np.diff(q[:, 1]))
    length = float(seg.sum())
    steps = max(int(np.ceil(length * 2.0)), q.shape[0])
    t = np.concatenate([[0.0], np.cumsum(seg)])
    want = np.linspace(0.0, t[-1], steps, endpoint=False)
    rr = np.interp(want, t, q[:, 0])
    cc = np.interp(want, t, q[:, 1])
    # ★被覆率で塗る。整数画素の円板で塗っていたときはペン幅が**階段**になり
    #   (0.5 / 1.0 / 1.5 px がインク率 0.1900 で一致し、2.0 で 0.4853 へ跳ねた)、
    #   「目標の濃さに合うペン幅」を解くことができなかった。画素中心から標本までの
    #   距離で被覆率を出すと、ペン幅が連続なノブになる。
    rad = float(pen_width) * 0.5
    k = int(np.ceil(rad + 0.5))
    br = np.floor(rr).astype(int)
    bc = np.floor(cc).astype(int)
    for dr in range(-k, k + 2):
        for dc in range(-k, k + 2):
            ri = br + dr
            ci = bc + dc
            ok = (ri >= 0) & (ri < h) & (ci >= 0) & (ci < w)
            if not ok.any():
                continue
            dist = np.hypot(ri[ok] - rr[ok], ci[ok] - cc[ok])
            cov = np.clip(rad - dist + 0.5, 0.0, 1.0)
            np.maximum.at(ink, (ri[ok], ci[ok]), cov)

    lo, hi = float(a.min()), float(a.max())
    target = (hi - a) / (hi - lo) if hi > lo else np.zeros_like(a)
    target = target ** float(gamma)
    drawn = _stroke_gauss(ink, float(blur_sigma))
    tgt = _stroke_gauss(target, float(blur_sigma))
    d = drawn - tgt
    sd, st = drawn - drawn.mean(), tgt - tgt.mean()
    denom = float(np.sqrt((sd ** 2).sum() * (st ** 2).sum()))
    return {"rms": float(np.sqrt((d ** 2).mean())),
            "max_abs": float(np.abs(d).max()),
            "bias": float(d.mean()),
            "corr": (float((sd * st).sum() / denom) if denom > 0.0 else float("nan")),
            "ink_fraction": float(ink.mean()),
            "target_darkness": float(target.mean()),
            "length_px": length}


def _stroke_gauss(a, sigma):
    """分離可能なガウスぼかし(端は反射)。scipy を呼ばない。"""
    r = int(np.ceil(3.0 * sigma))
    x = np.arange(-r, r + 1, dtype=np.float64)
    k = np.exp(-0.5 * (x / sigma) ** 2)
    k /= k.sum()
    out = np.apply_along_axis(lambda v: np.convolve(
        np.concatenate([v[r:0:-1], v, v[-2:-r - 2:-1]]), k, mode="valid"), 0, a)
    out = np.apply_along_axis(lambda v: np.convolve(
        np.concatenate([v[r:0:-1], v, v[-2:-r - 2:-1]]), k, mode="valid"), 1, out)
    return out
