# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""規格寸法の教習所コース(2-D 多角形、numpy のみ): 屈折・曲線・方向変換・坂道・交差点・縦列駐車・踏切。

## 何を作るか

自動車教習所のコース要素を **「走れる領域」の多角形** として厳密に持つ。各要素は
``{"kind", "polygon" (K, 2) 反時計回り・穴なし, "centerline" (L, 2), "entry" (x, y, yaw), "exit" (x, y, yaw),
"width", "params", "area_closed_form", "bounds"}`` の dict。すみ切り(角の丸め)は円弧を ``arc_pts`` 本の
折線にし、``arc_pts`` を増やすと靴紐面積が閉形式に **単調に** 収束する(門)。複数要素は ``course_layout``
で剛体配置し、``course_contains`` / ``course_occupancy`` は要素ごとの多角形の和で内外を判定する。

## 規格の値(普通免許)と出典

道路交通法施行規則 別表第三(第三十二条関係)「二 コースの形状及び構造に関する基準」(e-Gov 法令 ID
335M50000002060)。記号 A〜E は別表の図の記号。

* 屈折コース(クランク): 幅 A = 3.5 m、曲角間の長さ B = 12 m、出入口部 C ≥ 4 m、すみ切り半径 D = 1 m(曲角部の内側)
* 曲線コース(S 字): 幅 A = 3.5 m、半径 B = 7.5 m(外側の弧、内側は 7.5 − 3.5 = 4.0 m)、弧の長さ C = 円周の
  3/8(= 135°)、逆向きの 2 つの弧を共通接線点で繋ぐ
* 方向変換コース: 幅 A = 3.5 m(進入路)、車庫の幅 B = 3.5 m、奥行 C = 5 m、出入口部 D ≥ 5 m、すみ切り E = 1 m
* 坂道コース: 幅 ≥ 7 m、起点から頂上までの高さ ≥ 1.5 m、緩坂路 6.5〜9.0 %、急坂路 10.0〜12.5 %、頂上平坦部 ≥ 4 m
* 幹線コース(交差点): 幅 ≥ 7 m、十字に交差。交差点のすみ切り半径 ≥ 3 m は 警視庁 審査基準(幹線コースのすみ切り 3 m)
* 踏切: 軌間 1.1 m(レール内側)、レール外側 0.75 m(レール外縁から踏切面の端まで)
* 縦列駐車: **法令に数値なし(通達の別添は図)**。車室の長さ = 車長 + 3.0 m を既定にする

## 閉形式の面積(導出。テストは靴紐公式と突き合わせる)

すみ切り(半径 r)は **走れる領域の凹頂点(障害物ブロックの角)を円弧で削る** ので面積は **増える**。
直角の凹頂点 1 つに付き、頂点と 2 つの接点で囲む正方形 r² から四分円 πr²/4 を引いた
**r²(1 − π/4)** が加わる(頂点 V、接点 A = V − r·d_in、B = V + r·d_out、中心 O = A + r·n_right)。

* **屈折(クランク)**: 中心線は折線 (0,0)→(C+w/2,0)→(C+w/2,B)→(2C+w,B)、長さ L = 2C + w + B(図の C は帯の
  壁から出入口までなので中心線では C + w/2、B は外壁から向かいの内壁まで = 中心線の曲角間距離)。中心線を ±w/2 に太らせ、
  外側の角を正方形のまま残した L 字の面積は、長さ a, b の 2 帯の和 (a + w/2)w + (b + w/2)w から重なる
  正方形 w² を引いて **ちょうど w(a + b)**(外角を正方形にする分 w²/4 と内角の欠け w²/4 が打ち消す)。
  よって面積 = w·L + 2·r²(1 − π/4)。
* **曲線(S 字)**: 環状扇形 2 つ(中心角 θ = 2π·f、外径 R_o、内径 R_i = R_o − w)+ 出入口の直線 2 本。
  面積 = 2·(θ/2)(R_o² − R_i²) + 2·E·w = 2πf(R_o² − R_i²) + 2Ew(f = 3/8 で 2·(3/8)π(7.5² − 4.0²) + 2Ew)。
* **方向変換(T 字)**: 道路 (2E + bay_width) × w(車庫口の両側に出入口部 E)と車庫 depth × bay_width の和に、
  車庫口の凹頂点 2 つのすみ切りを足す。面積 = (2E + bay_width)·w + depth·bay_width + 2·r²(1 − π/4)。
* **坂道**: 長さ L = height/g_gentle + top + height/g_steep の矩形。面積 = w·L。
* **交差点(十字)**: 腕の長さ arm の道路 2 本(長さ 2arm + w、幅 w)の和は 2(2arm + w)w − w²。凹頂点 4 つの
  すみ切りで + 4·r²(1 − π/4)。
* **縦列駐車**: 道路 (2·approach + car_length + extra) × road_width + 車室 (car_length + extra) × car_width。
* **踏切**: 幅 w、長さ 2(rail_outer + gauge/2) + 2·approach の矩形。

## フレーム規約

x = 前/東、y = 左/北、単位 m、角度 rad。各要素は **entry が原点、進入方向 +x**。日本の左側通行に合わせ、
縦列駐車の車室は既定で左側(+y)、交差点の信号機は各流入路の左側手前に置く。占有格子は ``occupancy.py`` と同じ
``[row = y, col = x]``、``extent = (xmin, xmax, ymin, ymax)``、**row 0 = ymin**、cell 中心で判定、
**走れる領域の外 = True**。

## 内外判定(第 2 実装)

``_contains_even_odd``(交差数の偶奇)と ``_contains_winding``(回転数)を両方 numpy でベクトル化して持ち、
テストで凸でない多角形(クランク・S 字)の乱数点 5,000 で全点一致を要求する。境界上の点は未定義。

## 限界(self_reported)

* 多角形は穴なし・自己交差なしを前提にする(S 字は arc_fraction が大きく半径が小さいと要素同士が重なりうる。
  重なりは和として扱うので内外判定は壊れないが、閉形式の面積は重なりを 2 度数える)。
* 別表の図は縮尺なしの模式図。屈折・曲線・方向変換の形と記号の測り方は図(3JH00000217782/83/84)で確認したが、
  出入口部 C・D は「以上」なので既定は下限値。
* 停止線・信号機の位置は法令の数値ではなく、すみ切りの終わりから ``stop_setback`` 手前という慣行的な置き方。

## 参考文献

* 道路交通法施行規則 別表第三(第三十二条関係)二 コースの形状及び構造に関する基準(e-Gov 335M50000002060)
* 警視庁「指定自動車教習所の指定に係る審査基準」(幹線コースのすみ切り 3 m)
* Shimrat, "Algorithm 112: Position of point relative to polygon", CACM 1962(偶奇規則)
* Sunday, "Inclusion of a point in a polygon"(回転数の符号付き交差、2001)
"""
from __future__ import annotations

import math

import numpy as np

__all__ = [
    "course_crank", "course_s_curve", "course_turnaround", "course_slope", "course_intersection",
    "course_parallel_parking", "course_crossing", "course_road", "course_loop_bend", "course_loop", "course_layout",
    "course_occupancy", "course_contains", "polygon_area", "slope_height",
]

_TWO_PI = 2.0 * math.pi
_CHUNK = 32768          # 内外判定で一度に扱う点の数(点 × 頂点の bool 行列を抑える)
_POINT_KEYS = ("polygon", "centerline", "rails", "stop_lines", "corners", "arc_centers")   # 剛体変換で (…, 2) 点として動かす
_POSE_KEYS = ("entry", "exit", "signal_poses")                      # (…, 3) 姿勢として動かす(yaw も回す)


# ---- 引数検査(fail-closed) ------------------------------------------------------------------------
def _positive(v, name: str, op: str) -> float:
    v = float(v)
    if not (np.isfinite(v) and v > 0):
        raise ValueError("%s: %s must be a positive finite number, got %r" % (op, name, v))
    return v


def _nonneg(v, name: str, op: str) -> float:
    v = float(v)
    if not (np.isfinite(v) and v >= 0):
        raise ValueError("%s: %s must be a non-negative finite number, got %r" % (op, name, v))
    return v


def _arc_count(v, op: str) -> int:
    try:
        n = int(v)
    except (TypeError, ValueError):
        raise ValueError("%s: arc_pts must be an integer >= 1, got %r" % (op, v))
    if n < 1 or n != v:
        raise ValueError("%s: arc_pts must be an integer >= 1, got %r" % (op, v))
    return n


def _check_polygon(poly, op: str) -> np.ndarray:
    P = np.asarray(poly, np.float64)
    if P.ndim != 2 or P.shape[1] != 2 or P.shape[0] < 3:
        raise ValueError("%s: polygon must be (K >= 3, 2), got shape %s" % (op, getattr(P, "shape", None)))
    if not np.all(np.isfinite(P)):
        raise ValueError("%s: polygon must be finite" % op)
    return P


def _check_points(xy, op: str) -> tuple[np.ndarray, bool]:
    """(N, 2) float64 と「入力が 1 点 (2,) だったか」。"""
    P = np.asarray(xy, np.float64)
    single = P.ndim == 1
    if single:
        P = P[None, :]
    if P.ndim != 2 or P.shape[1] != 2:
        raise ValueError("%s: xy must be (N, 2) or (2,), got shape %s" % (op, P.shape))
    if not np.all(np.isfinite(P)):
        raise ValueError("%s: xy must be finite" % op)
    return P, single


# ---- 幾何の部品 --------------------------------------------------------------------------------------
def polygon_area(poly) -> float:
    """靴紐公式の **符号付き** 面積(反時計回りで正)。閉形式の面積と突き合わせる門に使う。

    **Raises** ``ValueError``: (K ≥ 3, 2) でない・非有限。"""
    P = _check_polygon(poly, "polygon_area")
    x, y = P[:, 0], P[:, 1]
    return float(0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def _finish_polygon(pts, op: str) -> np.ndarray:
    """連続する重複点を落とし、反時計回りに揃え、退化していないことを確かめる。"""
    P = np.asarray(pts, np.float64)
    keep = np.ones(len(P), bool)
    keep[1:] = np.any(np.abs(P[1:] - P[:-1]) > 1e-12, axis=1)
    if np.all(np.abs(P[0] - P[-1]) <= 1e-12):
        keep[-1] = False
    P = P[keep]
    a = polygon_area(P)
    if abs(a) < 1e-12:
        raise ValueError("%s: degenerate polygon (area ~ 0)" % op)
    return P[::-1].copy() if a < 0 else P


def _fillet_reflex(v, d_in, d_out, r: float, n: int) -> list:
    """反時計回りに辿る境界の **凹頂点**(右に 90° 折れる)を半径 r の円弧で削った点列(接点 A … B を含む)。

    A = V − r·d_in、B = V + r·d_out、中心 O = A + r·n_right(d_in)、弧は A から時計回りに 90°。r = 0 なら [V]。"""
    v = np.asarray(v, np.float64)
    d_in = np.asarray(d_in, np.float64)
    d_out = np.asarray(d_out, np.float64)
    if abs(float(d_in @ d_out)) > 1e-12 or float(d_in[0] * d_out[1] - d_in[1] * d_out[0]) >= 0:
        raise ValueError("_fillet_reflex: expects a right-angle right turn (reflex vertex of a CCW polygon)")
    if r <= 0:
        return [tuple(v)]
    a = v - r * d_in
    o = a + r * np.array([d_in[1], -d_in[0]])
    a0 = math.atan2(a[1] - o[1], a[0] - o[0])
    ang = a0 - (math.pi / 2) * np.arange(n + 1) / n
    pts = np.stack([o[0] + r * np.cos(ang), o[1] + r * np.sin(ang)], axis=1)
    pts[0] = a
    pts[-1] = v + r * d_out
    return [tuple(p) for p in pts]


def _fillet_area(r: float) -> float:
    """直角の凹頂点 1 つのすみ切りで **増える** 面積 r²(1 − π/4)。"""
    return r * r * (1.0 - math.pi / 4.0)


def _rect(x0: float, x1: float, y0: float, y1: float) -> np.ndarray:
    return np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], np.float64)


def _bounds(P: np.ndarray) -> tuple:
    return (float(P[:, 0].min()), float(P[:, 0].max()), float(P[:, 1].min()), float(P[:, 1].max()))


def _resample_polyline(pts, step: float) -> np.ndarray:
    """折線を弧長 step ごとに標本化(頂点を含む)。テストの「中心線が内側」「幅の門」に使う。"""
    P = np.asarray(pts, np.float64)
    out = [P[0]]
    for a, b in zip(P[:-1], P[1:]):
        L = float(np.hypot(*(b - a)))
        n = max(1, int(math.ceil(L / step - 1e-9)))
        for i in range(1, n + 1):
            out.append(a + (b - a) * (i / n))
    return np.asarray(out, np.float64)


def _element(kind: str, polygon, centerline, entry, exit_, width: float, params: dict,
             area: float, op: str, **extra) -> dict:
    P = _finish_polygon(polygon, op)
    d = {
        "kind": kind,
        "polygon": P,
        "centerline": np.asarray(centerline, np.float64),
        "entry": (float(entry[0]), float(entry[1]), float(entry[2])),
        "exit": (float(exit_[0]), float(exit_[1]), float(exit_[2])),
        "width": float(width),
        "params": params,
        "area_closed_form": float(area),
        "bounds": _bounds(P),
    }
    d.update(extra)
    return d


# ---- 内外判定(2 実装) ---------------------------------------------------------------------------------
def _contains_even_odd(poly, pts) -> np.ndarray:
    """偶奇規則(Shimrat 1962): 点から +x へ伸ばした半直線が辺と交わる回数の偶奇。numpy ベクトル化、
    点は ``_CHUNK`` ずつ処理する。境界上の点は未定義。"""
    P = np.asarray(poly, np.float64)
    Q = np.asarray(pts, np.float64).reshape(-1, 2)
    x0, y0 = P[:, 0], P[:, 1]
    x1, y1 = np.roll(x0, -1), np.roll(y0, -1)
    dy = y1 - y0
    safe = np.where(dy == 0, 1.0, dy)
    slope = (x1 - x0) / safe
    out = np.zeros(len(Q), bool)
    for s in range(0, len(Q), _CHUNK):
        px = Q[s:s + _CHUNK, 0][:, None]
        py = Q[s:s + _CHUNK, 1][:, None]
        crosses = (y0 > py) != (y1 > py)
        xi = x0 + (py - y0) * slope
        hit = crosses & (px < xi)
        out[s:s + _CHUNK] = (np.count_nonzero(hit, axis=1) & 1).astype(bool)
    return out


def _contains_winding(poly, pts) -> np.ndarray:
    """回転数(Sunday 2001): 上向きに横切る辺で点が左なら +1、下向きで右なら −1。非零なら内側。"""
    P = np.asarray(poly, np.float64)
    Q = np.asarray(pts, np.float64).reshape(-1, 2)
    x0, y0 = P[:, 0], P[:, 1]
    x1, y1 = np.roll(x0, -1), np.roll(y0, -1)
    out = np.zeros(len(Q), bool)
    for s in range(0, len(Q), _CHUNK):
        px = Q[s:s + _CHUNK, 0][:, None]
        py = Q[s:s + _CHUNK, 1][:, None]
        left = (x1 - x0) * (py - y0) - (px - x0) * (y1 - y0)
        up = (y0 <= py) & (y1 > py) & (left > 0)
        down = (y0 > py) & (y1 <= py) & (left < 0)
        wn = np.count_nonzero(up, axis=1) - np.count_nonzero(down, axis=1)
        out[s:s + _CHUNK] = wn != 0
    return out


def _iter_polygons(course, op: str):
    """要素なら [polygon]、配置なら各要素の polygon(bounds つき)。"""
    if not isinstance(course, dict):
        raise ValueError("%s: course must be a dict from course_* / course_layout" % op)
    if course.get("kind") == "layout":
        els = course.get("elements")
        if not isinstance(els, list) or not els:
            raise ValueError("%s: layout has no elements" % op)
        return [(_check_polygon(e["polygon"], op), e["bounds"]) for e in els]
    if course.get("polygon") is None:
        raise ValueError("%s: course has no polygon" % op)
    P = _check_polygon(course["polygon"], op)
    return [(P, _bounds(P))]


def course_contains(course, xy):
    """点が **走れる領域**(要素の多角形、配置なら要素の和)の内側かを偶奇規則で判定した bool 配列。

    ``xy`` は ``(N, 2)``(``(2,)`` なら bool スカラ)。境界上の点は未定義。要素ごとに bounds で先に篩う。

    **Raises** ``ValueError``: course が dict でない・polygon が無い・xy の形が悪い・非有限。"""
    op = "course_contains"
    Q, single = _check_points(xy, op)
    inside = np.zeros(len(Q), bool)
    for P, (bx0, bx1, by0, by1) in _iter_polygons(course, op):
        cand = ~inside & (Q[:, 0] >= bx0) & (Q[:, 0] <= bx1) & (Q[:, 1] >= by0) & (Q[:, 1] <= by1)
        if np.any(cand):
            inside[cand] = _contains_even_odd(P, Q[cand])
    return inside[0] if single else inside


def course_occupancy(course, cell: float = 0.25, margin: float = 2.0):
    """コース(要素または配置)を占有格子 ``(occ bool [row = y, col = x], extent)`` に落とす。

    **走れる領域の外 = True(障害物)**。格子は bounds を ``margin`` だけ広げた範囲を ``cell`` で覆い、
    各 cell の中心で偶奇判定する。``extent = (xmin, xmax, ymin, ymax)`` は格子がちょうど覆う範囲
    (xmax = xmin + nx·cell)、row 0 = ymin。占有率は cell → 0 で 1 − 面積/格子面積 に収束する(門)。

    **Raises** ``ValueError``: cell ≤ 0、margin < 0、course の形が悪い。"""
    op = "course_occupancy"
    cell = _positive(cell, "cell", op)
    margin = _nonneg(margin, "margin", op)
    polys = _iter_polygons(course, op)
    bx0 = min(b[0] for _, b in polys) - margin
    bx1 = max(b[1] for _, b in polys) + margin
    by0 = min(b[2] for _, b in polys) - margin
    by1 = max(b[3] for _, b in polys) + margin
    nx = max(1, int(math.ceil((bx1 - bx0) / cell - 1e-9)))
    ny = max(1, int(math.ceil((by1 - by0) / cell - 1e-9)))
    xs = bx0 + (np.arange(nx) + 0.5) * cell
    ys = by0 + (np.arange(ny) + 0.5) * cell
    X, Y = np.meshgrid(xs, ys)                      # (ny, nx): row = y
    pts = np.stack([X.ravel(), Y.ravel()], axis=1)
    free = course_contains(course, pts).reshape(ny, nx)
    return ~free, (bx0, bx0 + nx * cell, by0, by0 + ny * cell)


# ---- 要素 ---------------------------------------------------------------------------------------------
def course_crank(width=3.5, between=12.0, entry=4.0, corner_radius=1.0, arc_pts=16):
    """屈折コース(クランク、Z 形): 進入 → 左 90° → B → 右 90° → 退出。

    別表第三の図(3JH00000217782)の測り方に合わせる: 幅 A = w、曲角間の長さ B は一方の道の外壁から
    向かいの道の内壁まで(= 中心線の曲角間距離)、出入口部 C は横断する帯の壁から出入口まで(中心線では
    C + w/2)、すみ切り D は曲角部の **内側** の角(外側の角は正方形のまま)。中心線は
    (0,0)→(C+w/2, 0)→(C+w/2, B)→(2C+w, B)、長さ L = 2C + w + B。面積 = w·L + 2r²(1 − π/4)
    (導出はモジュール docstring)。規格(普通免許): A = 3.5, B = 12, C ≥ 4, D = 1 → ``params["regulation"]``。

    **Raises** ``ValueError``: 幅・B・C が正でない、r < 0、C < r(すみ切りが出入口にはみ出る)、
    B < w + r(2 つの角が重なる)、arc_pts が 1 以上の整数でない。"""
    op = "course_crank"
    w = _positive(width, "width", op)
    B = _positive(between, "between", op)
    C = _positive(entry, "entry", op)
    r = _nonneg(corner_radius, "corner_radius", op)
    n = _arc_count(arc_pts, op)
    h = 0.5 * w
    if C < r:
        raise ValueError("%s: entry (%g) must be >= corner_radius (%g)" % (op, C, r))
    if B < w + r:
        raise ValueError("%s: between (%g) must be >= width + corner_radius (%g)" % (op, B, w + r))
    xc = C + h                       # 曲角の中心線 x
    xe = 2 * C + w                   # 退出口の x
    pts = [(0.0, -h), (xc + h, -h)]
    pts += _fillet_reflex((xc + h, B - h), (0.0, 1.0), (1.0, 0.0), r, n)     # 角 2 の内側
    pts += [(xe, B - h), (xe, B + h), (xc - h, B + h)]
    pts += _fillet_reflex((xc - h, h), (0.0, -1.0), (-1.0, 0.0), r, n)       # 角 1 の内側
    pts += [(0.0, h)]
    center = [(0.0, 0.0), (xc, 0.0), (xc, B), (xe, B)]
    L = 2 * xc + B
    area = w * L + 2 * _fillet_area(r)
    params = {"width": w, "between": B, "entry": C, "corner_radius": r, "arc_pts": n,
              "entry_centerline": xc, "regulation": {"A": w, "B": B, "C": C, "D": r}}
    return _element("crank", pts, center, (0.0, 0.0, 0.0), (xe, B, 0.0), w, params, area, op,
                    corners=np.array([[xc, 0.0], [xc, B]]), centerline_length=L)


def course_s_curve(width=3.5, radius_outer=7.5, arc_fraction=3.0 / 8.0, entry=4.0, arc_pts=48):
    """曲線コース(S 字): 直線 E → 左弧(中心角 2π·f)→ 右弧(同じ)→ 直線 E。

    外径 R_o = ``radius_outer``、内径 R_i = R_o − w、中心線の半径 R_c = (R_o + R_i)/2。2 つの弧は共通接線点で
    曲率の向きが反転する。多角形は中心線の標本点を法線方向に ±w/2 ずらして作る(弧の標本点は外円・内円の
    上に厳密に乗る)。面積 = 2πf(R_o² − R_i²) + 2Ew。規格: A = 3.5, B = 7.5, C = 3/8 → ``params["regulation"]``。

    **Raises** ``ValueError``: 幅・外径が正でない、R_o ≤ w(内径が 0 以下)、arc_fraction ∉ (0, 1)、E < 0、
    arc_pts が 1 以上の整数でない。"""
    op = "course_s_curve"
    w = _positive(width, "width", op)
    Ro = _positive(radius_outer, "radius_outer", op)
    f = float(arc_fraction)
    if not (np.isfinite(f) and 0.0 < f < 1.0):
        raise ValueError("%s: arc_fraction must be in the open interval (0, 1), got %r" % (op, arc_fraction))
    E = _nonneg(entry, "entry", op)
    n = _arc_count(arc_pts, op)
    if Ro <= w:
        raise ValueError("%s: radius_outer (%g) must exceed width (%g) so the inner radius is positive" % (op, Ro, w))
    Ri = Ro - w
    Rc = 0.5 * (Ro + Ri)
    theta = _TWO_PI * f
    h = 0.5 * w
    samples = [(0.0, 0.0, 0.0), (E, 0.0, 0.0)]
    c1 = np.array([E, Rc])
    phi = -math.pi / 2 + theta * np.arange(n + 1) / n
    for a in phi:
        samples.append((c1[0] + Rc * math.cos(a), c1[1] + Rc * math.sin(a), a + math.pi / 2))
    px, py, _ = samples[-1]
    c2 = np.array([px + Rc * math.sin(theta), py - Rc * math.cos(theta)])
    psi = theta + math.pi / 2 - theta * np.arange(n + 1) / n
    for a in psi:
        samples.append((c2[0] + Rc * math.cos(a), c2[1] + Rc * math.sin(a), a - math.pi / 2))
    ex, ey, _ = samples[-1]
    samples.append((ex + E, ey, 0.0))
    S = np.asarray(samples, np.float64)
    nrm = np.stack([-np.sin(S[:, 2]), np.cos(S[:, 2])], axis=1)      # 左法線
    right = S[:, :2] - h * nrm
    left = S[:, :2] + h * nrm
    poly = np.vstack([right, left[::-1]])
    area = theta * (Ro * Ro - Ri * Ri) + 2 * E * w
    params = {"width": w, "radius_outer": Ro, "radius_inner": Ri, "radius_center": Rc, "arc_fraction": f,
              "arc_angle": theta, "entry": E, "arc_pts": n, "regulation": {"A": w, "B": Ro, "C": f}}
    return _element("s_curve", poly, S[:, :2], (0.0, 0.0, 0.0), (ex + E, ey, 0.0), w, params, area, op,
                    arc_centers=np.stack([c1, c2]), centerline_length=2 * E + 2 * Rc * theta)


def course_turnaround(width=3.5, bay_width=3.5, depth=5.0, entry=5.0, corner_radius=1.0, arc_pts=16,
                      side="left"):
    """方向変換コース(T 字): 幅 w の道路(x ∈ [0, 2E + bay_width])の側方中央に車庫(道路沿いの幅 bay_width、
    奥行 depth)、車庫口の両側に出入口部 E ずつ。

    別表第三の図(3JH00000217784)そのもの: 道路(幅 A)の途中に車庫(幅 B × 奥行 C)が直角に付き、車庫口の両側の
    道路が出入口部 D、車庫口の凹頂点 2 つがすみ切り E。図は上向きの道路の右側に車庫があるが、ここでは
    ``side="left"``(+y)を既定にし ``"right"`` で鏡映する。車は道路を進み、後退で車庫に入れ、来た方向へ出る
    (exit = (0, 0, π); 反対側へ出るときは配置側で向きを選ぶ)。centerline は道路の軸 → 車庫の軸。
    面積 = (2E + bay_width)·w + depth·bay_width + 2r²(1 − π/4)。
    規格: A = 3.5, B = 3.5, C = 5, D ≥ 5, E = 1 → ``params["regulation"]``。

    **Raises** ``ValueError``: 幅・車庫幅・奥行・E が正でない、r < 0、E < r または depth < r(すみ切りが辺に
    収まらない)、arc_pts が 1 以上の整数でない、side が left/right でない。"""
    op = "course_turnaround"
    w = _positive(width, "width", op)
    bw = _positive(bay_width, "bay_width", op)
    dp = _positive(depth, "depth", op)
    E = _positive(entry, "entry", op)
    r = _nonneg(corner_radius, "corner_radius", op)
    n = _arc_count(arc_pts, op)
    if side not in ("left", "right"):
        raise ValueError("%s: side must be 'left' or 'right', got %r" % (op, side))
    if E < r:
        raise ValueError("%s: entry (%g) must be >= corner_radius (%g)" % (op, E, r))
    if dp < r:
        raise ValueError("%s: depth (%g) must be >= corner_radius (%g)" % (op, dp, r))
    h = 0.5 * w
    L = 2 * E + bw
    xb0, xb1 = E, E + bw
    pts = [(0.0, -h), (L, -h), (L, h)]
    pts += _fillet_reflex((xb1, h), (-1.0, 0.0), (0.0, 1.0), r, n)
    pts += [(xb1, h + dp), (xb0, h + dp)]
    pts += _fillet_reflex((xb0, h), (0.0, -1.0), (-1.0, 0.0), r, n)
    pts += [(0.0, h)]
    sgn = 1.0 if side == "left" else -1.0
    pts = np.asarray(pts, np.float64)
    pts[:, 1] *= sgn
    xc = 0.5 * L
    center = [(0.0, 0.0), (xc, 0.0), (xc, sgn * (h + dp))]
    area = L * w + dp * bw + 2 * _fillet_area(r)
    params = {"width": w, "bay_width": bw, "depth": dp, "entry": E, "corner_radius": r, "arc_pts": n,
              "road_length": L, "side": side, "regulation": {"A": w, "B": bw, "C": dp, "D": E, "E": r}}
    return _element("turnaround", pts, center, (0.0, 0.0, 0.0), (0.0, 0.0, math.pi), w, params, area, op,
                    bay=(xb0, xb1, sgn * h, sgn * (h + dp)), centerline_length=xc + h + dp)


def course_slope(width=7.0, height=1.5, grade_gentle=0.08, grade_steep=0.11, top=4.0):
    """坂道コース: 緩坂で高さ ``height`` まで上り、頂上平坦部 ``top``、急坂で下りる矩形の道(x 軸沿い)。

    多角形は幅 w × 長さ L = height/g_gentle + top + height/g_steep の矩形。``profile`` = (s, z) の折線
    [(0,0), (s1,h), (s1+top,h), (L,0)]、z は ``slope_height`` で補間(driveworld が路面を持ち上げる)。
    規格: 幅 ≥ 7、高さ ≥ 1.5、緩 6.5〜9.0 %、急 10.0〜12.5 %、平坦部 ≥ 4 → ``params["regulation"]``。
    面積 = w·L。

    **Raises** ``ValueError``: 幅・高さ・勾配・平坦部が正でない、勾配 ≥ 1(45° 超は道ではない)。"""
    op = "course_slope"
    w = _positive(width, "width", op)
    hgt = _positive(height, "height", op)
    g1 = _positive(grade_gentle, "grade_gentle", op)
    g2 = _positive(grade_steep, "grade_steep", op)
    tp = _positive(top, "top", op)
    if g1 >= 1.0 or g2 >= 1.0:
        raise ValueError("%s: grades must be < 1 (rise/run), got %g / %g" % (op, g1, g2))
    s1 = hgt / g1
    s2 = s1 + tp
    L = s2 + hgt / g2
    h = 0.5 * w
    profile = np.array([[0.0, 0.0], [s1, hgt], [s2, hgt], [L, 0.0]], np.float64)
    params = {"width": w, "height": hgt, "grade_gentle": g1, "grade_steep": g2, "top": tp, "length": L,
              "regulation": {"width_min": 7.0, "height_min": 1.5, "gentle_range": (0.065, 0.09),
                             "steep_range": (0.10, 0.125), "top_min": 4.0}}
    return _element("slope", _rect(0.0, L, -h, h), [(0.0, 0.0), (L, 0.0)], (0.0, 0.0, 0.0), (L, 0.0, 0.0),
                    w, params, w * L, op, profile=profile, centerline_length=L)


def slope_height(course, s):
    """坂道要素の路面高 z を弧長 s(要素の局所座標、entry からの距離)で線形補間。プロファイル外は端の値。

    **Raises** ``ValueError``: kind が "slope" でない、s が非有限。"""
    if not isinstance(course, dict) or course.get("kind") != "slope" or "profile" not in course:
        raise ValueError("slope_height: course must be a course_slope element")
    s = np.asarray(s, np.float64)
    if not np.all(np.isfinite(s)):
        raise ValueError("slope_height: s must be finite")
    pr = course["profile"]
    return np.interp(s, pr[:, 0], pr[:, 1])


def course_intersection(width=7.0, arm=20.0, corner_radius=3.0, arc_pts=16, stop_setback=2.0, crosswalk=4.0):
    """幹線コースの十字交差点: 幅 w の道路 2 本が原点で直交、各腕の長さ ``arm``(交差部の縁から)、
    凹頂点 4 つを半径 ``corner_radius`` で削る。

    面積 = 2(2·arm + w)w − w² + 4r²(1 − π/4)。左側通行に合わせ、各腕に **横断歩道 1 本**(``crosswalks`` (4, 2, 2): すみ切りの
    終わりから幅 ``crosswalk`` (既定 4 m)で道路を横切る帯の中心線)、各流入路(東行 → 北行 → 西行 → 南行の順、流入方向 yaw = 0, π/2, π, 3π/2)に
    **停止線 1 本**(``stop_lines`` (4, 2, 2): 流入車線 = 進行方向左半分を横切る線分、横断歩道の ``stop_setback``(既定 2 m)手前)と
    **信号機 1 基**(``signal_poses`` (4, 3): 交差点の**向こう側**、出口側の横断歩道の外の左の角(左側 0.5 m 外)、yaw = 流入車に向く向き
    = 流入方向 + π)。centerline は東西の道路軸。

    規格・基準(2026-09-30、ユーザー「日本の規格やルールに合わせて」): 幅 ≥ 7、すみ切り ≥ 3(警視庁 審査基準)→ ``params["regulation"]``。
    信号機のある交差点には横断歩道と停止線を設ける(運転免許技能試験実施基準 令和 4 年 警察庁丙運発第 12 号 別添 場内コースの設定 (4))、
    停止線は横断歩道の 2 m 手前が標準(信号機設置の指針の解説)、車両用灯器は交差点の向こう側(出口側)に置く(同)、横断歩道の幅は 4 m 以上が一般
    (道路標示 201)。

    **Raises** ``ValueError``: 幅・腕が正でない、r < 0、crosswalk < 0、arm < r + crosswalk + stop_setback、arc_pts が不正。"""
    op = "course_intersection"
    w = _positive(width, "width", op)
    arm_ = _positive(arm, "arm", op)
    r = _nonneg(corner_radius, "corner_radius", op)
    sb = _nonneg(stop_setback, "stop_setback", op)
    cw = _nonneg(crosswalk, "crosswalk", op)
    n = _arc_count(arc_pts, op)
    if arm_ < r + cw + sb:
        raise ValueError("%s: arm (%g) must be >= corner_radius + crosswalk + stop_setback (%g)" % (op, arm_, r + cw + sb))
    h = 0.5 * w
    L = arm_ + h
    pts = [(L, -h), (L, h)]
    pts += _fillet_reflex((h, h), (-1.0, 0.0), (0.0, 1.0), r, n)
    pts += [(h, L), (-h, L)]
    pts += _fillet_reflex((-h, h), (0.0, -1.0), (-1.0, 0.0), r, n)
    pts += [(-L, h), (-L, -h)]
    pts += _fillet_reflex((-h, -h), (1.0, 0.0), (0.0, -1.0), r, n)
    pts += [(-h, -L), (h, -L)]
    pts += _fillet_reflex((h, -h), (0.0, 1.0), (1.0, 0.0), r, n)
    # 東行の流入路(x < 0, 進行 +x)のひな形を 4 方向に回す。横断歩道はすみ切りの終わり(h + r)から幅 cw、停止線はその sb 手前
    d_cross = h + r + 0.5 * cw                                 # 横断歩道の帯の中心
    d_stop = h + r + cw + sb
    cross0 = np.array([[-d_cross, -h], [-d_cross, h]])         # 道路の全幅を横切る帯の中心線(幅 cw は world 側で描く)
    stop0 = np.array([[-d_stop, 0.0], [-d_stop, h]])          # 左半分(y ∈ [0, h])を横切る
    # 信号は流入路から見て交差点の**向こう側**(出口側の横断歩道の外)の左の角、流入路の方(西)を向く(日本の対面信号)。停止線の真横に
    # 立てると車載カメラは 40° 見上げないと灯火が入らない(2026-09-30、閉ループ化で発覚)。
    sig0 = np.array([h + r + cw + 0.5, h + 0.5, math.pi])
    stop_lines, signals, crosswalks = [], [], []
    for k in range(4):
        yaw = k * math.pi / 2
        c, s = math.cos(yaw), math.sin(yaw)
        R = np.array([[c, -s], [s, c]])
        stop_lines.append(stop0 @ R.T)
        crosswalks.append(cross0 @ R.T)
        signals.append([c * sig0[0] - s * sig0[1], s * sig0[0] + c * sig0[1], _wrap(sig0[2] + yaw)])
    area = 2 * (2 * arm_ + w) * w - w * w + 4 * _fillet_area(r)
    params = {"width": w, "arm": arm_, "corner_radius": r, "arc_pts": n, "stop_setback": sb, "crosswalk": cw,
              "regulation": {"width_min": 7.0, "corner_radius_min": 3.0, "stop_setback_std": 2.0, "crosswalk_min": 4.0}}
    return _element("intersection", pts, [(-L, 0.0), (L, 0.0)], (-L, 0.0, 0.0), (L, 0.0, 0.0), w, params,
                    area, op, stop_lines=np.asarray(stop_lines, np.float64), crosswalks=np.asarray(crosswalks, np.float64),
                    crosswalk_width=cw, signal_poses=np.asarray(signals, np.float64), centerline_length=2 * L)


def course_parallel_parking(car_length=4.5, car_width=1.8, extra=3.0, road_width=7.0, approach=5.0,
                            side="left"):
    """縦列駐車: 幅 ``road_width`` の道路(x ∈ [0, 2·approach + bay_length])の路側に、長さ car_length + extra
    (既定 7.5 m)× 幅 car_width の車室。**法令に数値なし(通達の別添は図)** —— 既定は慣行値。

    左側通行に合わせ ``side="left"``(+y)が既定、``"right"`` で鏡映。``bay`` = (x0, x1, y0, y1)。
    面積 = 道路 + 車室(すみ切りなし)。

    **Raises** ``ValueError``: 寸法が正でない、extra < 0、side が left/right でない。"""
    op = "course_parallel_parking"
    cl = _positive(car_length, "car_length", op)
    cw = _positive(car_width, "car_width", op)
    ex = _nonneg(extra, "extra", op)
    rw = _positive(road_width, "road_width", op)
    ap = _positive(approach, "approach", op)
    if side not in ("left", "right"):
        raise ValueError("%s: side must be 'left' or 'right', got %r" % (op, side))
    bl = cl + ex
    L = 2 * ap + bl
    h = 0.5 * rw
    sgn = 1.0 if side == "left" else -1.0
    pts = np.array([(0.0, -h), (L, -h), (L, h), (ap + bl, h), (ap + bl, h + cw), (ap, h + cw), (ap, h), (0.0, h)])
    pts[:, 1] *= sgn
    params = {"car_length": cl, "car_width": cw, "extra": ex, "road_width": rw, "approach": ap, "side": side,
              "bay_length": bl, "regulation": {"note": "法令に数値なし(通達の別添は図)", "bay_length": bl}}
    return _element("parallel_parking", pts, [(0.0, 0.0), (L, 0.0)], (0.0, 0.0, 0.0), (L, 0.0, 0.0), rw,
                    params, L * rw + bl * cw, op, bay=(ap, ap + bl, sgn * h, sgn * (h + cw)),
                    centerline_length=L)


def course_crossing(width=7.0, gauge=1.1, rail_outer=0.75, approach=6.0, stop_setback=0.5):
    """踏切: 幅 w の道路(x 軸沿い)を線路が直角に横切る。踏切面(軌間 + レール外側 2 つ = 2.6 m)の両側に
    ``approach`` の直線。``rails`` (2, 2, 2) はレール 2 本の線分(x = L/2 ± gauge/2、道路幅いっぱい)、
    ``crossing_zone`` = (x0, x1) 踏切面、``stop_lines`` (1, 2, 2) は踏切面の ``stop_setback`` 手前の左車線。
    多角形は矩形(レールはメタデータ)。規格: 軌間 1.1、レール外側 0.75 → ``params["regulation"]``。
    面積 = w·(2(rail_outer + gauge/2) + 2·approach)。

    **Raises** ``ValueError``: 幅・軌間・approach が正でない、rail_outer < 0、stop_setback < 0。"""
    op = "course_crossing"
    w = _positive(width, "width", op)
    g = _positive(gauge, "gauge", op)
    ro = _nonneg(rail_outer, "rail_outer", op)
    ap = _positive(approach, "approach", op)
    sb = _nonneg(stop_setback, "stop_setback", op)
    zone = 2 * (ro + 0.5 * g)
    L = zone + 2 * ap
    h = 0.5 * w
    xc = 0.5 * L
    rails = np.array([[[xc - 0.5 * g, -h], [xc - 0.5 * g, h]], [[xc + 0.5 * g, -h], [xc + 0.5 * g, h]]])
    stop = np.array([[[xc - 0.5 * zone - sb, 0.0], [xc - 0.5 * zone - sb, h]]])
    params = {"width": w, "gauge": g, "rail_outer": ro, "approach": ap, "stop_setback": sb, "length": L,
              "regulation": {"gauge": g, "rail_outer": ro}}
    return _element("crossing", _rect(0.0, L, -h, h), [(0.0, 0.0), (L, 0.0)], (0.0, 0.0, 0.0), (L, 0.0, 0.0),
                    w, params, w * L, op, rails=rails, crossing_zone=(xc - 0.5 * zone, xc + 0.5 * zone),
                    stop_lines=stop, centerline_length=L)


def course_road(length=20.0, width=7.0):
    """連絡路(幹線の一部): 幅 w・長さ L の直線。課題コースの出口を周回コースへ戻す・幹線を延ばすための要素。
    規格(幹線コース): 幅 7 m 以上、周回コースと連絡すること。面積 = w·L。

    **Raises** ``ValueError``: 長さ・幅が正でない。"""
    op = "course_road"
    L = _positive(length, "length", op)
    w = _positive(width, "width", op)
    h = 0.5 * w
    params = {"length": L, "width": w, "regulation": {"width_min": 7.0}}
    return _element("road", _rect(0.0, L, -h, h), [(0.0, 0.0), (L, 0.0)], (0.0, 0.0, 0.0), (L, 0.0, 0.0),
                    w, params, w * L, op, centerline_length=L)


def course_loop_bend(radius=30.0, width=8.0, arc_pts=64):
    """周回コースの端の半円(左へ 180° 回る): 進入 (0, 0, 0) → 中心 (0, R) の周りを回って退出 (0, 2R, π)。
    多角形は外側の弧(半径 R + w/2)と内側の弧(R − w/2)で囲む環の半分。面積 = π R w(閉形式)、弧を
    折線にした分だけ小さく、arc_pts を増やすと収束する。規格(周回コース): 幅 8 m 以上、おおむね長円形。

    **Raises** ``ValueError``: R ≤ w/2(内側の弧が潰れる)、幅・半径が正でない、arc_pts が不正。"""
    op = "course_loop_bend"
    R = _positive(radius, "radius", op)
    w = _positive(width, "width", op)
    n = _arc_count(arc_pts, op)
    h = 0.5 * w
    if R <= h:
        raise ValueError("%s: radius (%g) must exceed width/2 (%g)" % (op, R, h))
    th = np.linspace(-0.5 * math.pi, 0.5 * math.pi, n + 1)
    outer = np.column_stack([(R + h) * np.cos(th), R + (R + h) * np.sin(th)])
    inner = np.column_stack([(R - h) * np.cos(th[::-1]), R + (R - h) * np.sin(th[::-1])])
    pts = np.vstack([outer, inner])
    center = np.column_stack([R * np.cos(th), R + R * np.sin(th)])
    params = {"radius": R, "width": w, "arc_pts": n, "regulation": {"width_min": 8.0}}
    return _element("loop_bend", pts, center, (0.0, 0.0, 0.0), (0.0, 2 * R, math.pi), w, params, math.pi * R * w, op,
                    arc_centers=np.array([[0.0, R]]), centerline_length=math.pi * R)


def course_loop(straight=80.0, radius=30.0, width=8.0, arc_pts=64, overlap=0.05):
    """周回コース(長円形): 直線 2 本 + 半円 2 つを原点中心に置いた ``{"elements": [...], "placements": [...]}``
    を返す(そのまま :func:`course_layout` に渡す)。反時計回りに、南の直線(東行き, y = −R)→ 東の半円 → 北の直線
    (西行き, y = +R)→ 西の半円。直線は両端を ``overlap`` だけ半円に食い込ませる(3-D 化で継ぎ目に縁石が
    立たないための重なり; 面積の和はその分だけ二重に数える)。規格(普通免許): 80 m 以上の直線走行部分、幅 8 m 以上。

    **Raises** ``ValueError``: 直線が正でない、半円の条件(course_loop_bend)。"""
    op = "course_loop"
    S = _positive(straight, "straight", op)
    ov = float(overlap)
    bend = course_loop_bend(radius, width, arc_pts)
    road = course_road(S + 2 * ov, width)            # 両端を ov ずつ半円に食い込ませる(継ぎ目に縁石が立たないように)
    R = float(radius)
    elements = [road, bend, road, bend]
    placements = [(-0.5 * S - ov, -R, 0.0), (0.5 * S, -R, 0.0), (0.5 * S + ov, R, math.pi), (-0.5 * S, R, math.pi)]
    return {"kind": "loop", "elements": elements, "placements": placements,
            "params": {"straight": S, "radius": R, "width": float(width), "overlap": ov,
                       "regulation": {"straight_min": 80.0, "width_min": 8.0}}}


# ---- 配置 ----------------------------------------------------------------------------------------------
def _wrap(x: float) -> float:
    """(−π, π] に折る(丸めで −π に落ちた値は +π に戻す)。"""
    y = x - _TWO_PI * math.floor((x + math.pi) / _TWO_PI)
    return y + _TWO_PI if y <= -math.pi else y


def _rigid_points(P, x: float, y: float, yaw: float) -> np.ndarray:
    P = np.asarray(P, np.float64)
    c, s = math.cos(yaw), math.sin(yaw)
    flat = P.reshape(-1, 2)
    out = np.empty_like(flat)
    out[:, 0] = c * flat[:, 0] - s * flat[:, 1] + x
    out[:, 1] = s * flat[:, 0] + c * flat[:, 1] + y
    return out.reshape(P.shape)


def _rigid_poses(Q, x: float, y: float, yaw: float):
    Q = np.asarray(Q, np.float64)
    flat = Q.reshape(-1, 3)
    xy = _rigid_points(flat[:, :2], x, y, yaw)
    out = np.column_stack([xy, [_wrap(t + yaw) for t in flat[:, 2]]])
    return out.reshape(Q.shape)


def course_layout(elements, placements):
    """複数の要素を剛体運動 ``(x, y, yaw)`` で配置して 1 つの dict にする。

    各要素の polygon / centerline / rails / stop_lines は点として、entry / exit / signal_poses は姿勢として
    (yaw も回す)変換する。``profile``(坂道の (s, z))は要素の局所弧長なのでそのまま。返り値は
    ``{"kind": "layout", "elements": [変換済み要素(各々 "placement" を持つ)], "polygon": None,
    "bounds": (xmin, xmax, ymin, ymax), "placements": [...]}``。内外判定は要素の和(``course_contains`` /
    ``course_occupancy``)。要素の重なりは和として扱う。

    **Raises** ``ValueError``: 要素が空・要素と配置の数が違う・要素が dict でない・配置が 3 要素で有限でない。"""
    op = "course_layout"
    if not isinstance(elements, (list, tuple)) or len(elements) == 0:
        raise ValueError("%s: elements must be a non-empty list of course dicts" % op)
    if not isinstance(placements, (list, tuple)) or len(placements) != len(elements):
        raise ValueError("%s: placements must have one (x, y, yaw) per element (%d elements, %s placements)"
                         % (op, len(elements), len(placements) if isinstance(placements, (list, tuple)) else "?"))
    out, plc = [], []
    for e, p in zip(elements, placements):
        if not isinstance(e, dict) or e.get("polygon") is None or e.get("kind") == "layout":
            raise ValueError("%s: each element must be a single course dict with a polygon (nested layouts are not supported)" % op)
        pv = np.asarray(p, np.float64)
        if pv.shape != (3,) or not np.all(np.isfinite(pv)):
            raise ValueError("%s: placement must be a finite (x, y, yaw), got %r" % (op, p))
        x, y, yaw = (float(v) for v in pv)
        d = dict(e)
        for k in _POINT_KEYS:
            if k in d and d[k] is not None:
                d[k] = _rigid_points(d[k], x, y, yaw)
        for k in _POSE_KEYS:
            if k in d and d[k] is not None:
                q = _rigid_poses(d[k], x, y, yaw)
                d[k] = tuple(float(v) for v in q) if q.ndim == 1 else q
        if "bay" in d:
            b = d["bay"]
            d["bay_polygon"] = _rigid_points(_rect(b[0], b[1], min(b[2], b[3]), max(b[2], b[3])), x, y, yaw)
        d["polygon"] = _check_polygon(d["polygon"], op)
        d["bounds"] = _bounds(d["polygon"])
        d["placement"] = (x, y, yaw)
        out.append(d)
        plc.append((x, y, yaw))
    bx = [e["bounds"] for e in out]
    return {
        "kind": "layout",
        "elements": out,
        "polygon": None,
        "bounds": (min(b[0] for b in bx), max(b[1] for b in bx), min(b[2] for b in bx), max(b[3] for b in bx)),
        "placements": plc,
        "area_closed_form_sum": float(sum(e["area_closed_form"] for e in out)),
    }
