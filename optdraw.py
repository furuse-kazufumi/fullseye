# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""optdraw — 光学系の図面(レンズ断面図・撮像系の設置図・単レンズの製作図)を SVG / DXF で書き出す。

動機(2026-10-15、ユーザーの言葉「光学系の図面とかも出力する機能があればいいのにね」): ``raytrace`` は処方
(``lens_system`` の table)を実光線で評価し、``optscene.vision_layout`` はセンサー・レンズ・照明を束ねて
光学バジェットを返すが、**どちらも数と dict しか返さず、図を 1 枚も描かなかった**。外観検査・計測の現場では、
レンズの断面図と装置の設置図(作動距離・視野・照明の角度)が打ち合わせの共通言語で、製作を頼むには単レンズの
製作図(ISO 10110 の表記)が要る。ここはその 3 種を、**計算した値そのものから**描く層。

内容(8 op、opsoptics のカテゴリ ``drawing``):
  図を組む   `lens_section_drawing`(処方 → 子午断面。面は円錐 + 非球面の sag、コバ・絞り・像面、視野ごとに色を
             分けた**実光線**(絞りを狙って追跡)、EFL・BFL・全長・像高の寸法線、処方表)
             `vision_setup_drawing`(``vision_layout`` → 側面図と上面図。作動距離・視野の錐・被写界深度の帯・
             照明 5 種(ring / dome / bar / coaxial / backlight)の位置と角度・カメラ・寸法)
             `lens_element_drawing`(単レンズの製作図。ISO 10110 の 3 分割の表: 面ごとの R・有効径・3/ 4/ 5/、
             中央に材料の n_d・ν_d と 0/ 1/ 2/。公差は ``tolerance_analysis`` の公差の辞書から写し、EFL の
             Monte-Carlo の幅を注記に入れる)
  書き出す   `drawing_svg`(stdlib だけの SVG。座標は mm、紙の大きさ = 図の大きさ × 縮尺なので**等倍で印刷できる**)
             `drawing_dxf`(stdlib だけの DXF R12(AC1009)の ASCII。HEADER・TABLES(LTYPE・LAYER・STYLE)・ENTITIES)
             `drawing_raster`(matplotlib があれば RGB の画像に。任意依存)
  読み戻す   `svg_entities` / `dxf_entities`(書いた図から座標と文字を読み戻す。門はここから採点する)

図のモデル(``kind == "optdraw"`` の dict): ``entities`` は ``line`` / ``polyline`` / ``circle`` / ``arc`` /
``text`` の列で、座標は**実寸の mm**(y が上、CAD の向き)。各要素は ``layer`` を持ち、層が線の種類(ISO 128 /
JIS Z 8114 の太い実線・細い実線・細い一点鎖線・細い破線)と太さと色を決める。``dimensions`` は寸法線ごとの名前・
値・端点、``values`` は図に書いた数の正本(門が読み戻した文字と突き合わせる相手)。

規約: 長さは mm、角度は度。レンズ断面図の横軸は光軸 z(光は左から右)、縦軸は子午面の高さ y。設置図の側面図は
(y, z)、上面図は (y, x) で、第三角法の並び(上面図を側面図の上に置き、横軸 y を共有する)。**寸法の数字に単位は
書かない**(製図の慣行。mm)。文字は DXF R12 に載るよう ASCII と ⌀ ° ± だけを使い、DXF では ``%%c`` ``%%d``
``%%p`` に置き換える(それ以外の非 ASCII は fail-closed で拒否)。

★2026-10-15 から描けるようになったもの: 鏡・傾き・偏心・座標の切り替え・折り返しミラー・半透鏡を持つ系は
``noncoaxial_drawing``(``raytrace3d`` の系の大域の配置を子午面へ投影した断面図・設置図。``lens_section_drawing`` に
鏡や傾きのある処方を渡すとここへ回す)、接合レンズ群の製作図(``lens_element_drawing`` が接合の群を 1 枚の組図に
する)、非球面の製作図(ISO 10110-12 の sag の表)。描けないもの(fail-closed で ValueError): 縁の厚さが負になる
処方(作れない)、投影面から大きく外れる配置(``view`` で面を選ぶ)。

真値(外部): 球面の sag ``z = R − sign(R)·√(R² − y²)``、円錐の sag(``raytrace`` の docstring の式)、
厚肉レンズの公式(lensmaker)、教科書の Cooke triplet の処方と公表 EFL、ISO 10110 の表記の公開解説、
DXF R12 の公開仕様(グループコード)。門は図を**書いた文字列から読み戻して**採点し、描画に使った関数を
もう一度呼んで比べることはしない(両辺に同じ入力を食わせる門は入力の誤りを通すため)。

来歴: ISO 10110-1/-5/-6/-7(光学素子の製図。有料規格なので公開の解説で表記を確かめた)/ ISO 128・JIS Z 8114
(線の種類と太さ)/ ISO 129-1・JIS Z 8317-1(寸法の記入)/ Smith, *Modern Lens Design*、Kingslake, *Lens Design
Fundamentals*(Cooke triplet)/ DXF Reference R12(グループコード)。
"""
from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET

import numpy as np

import raytrace as RT

__all__ = [
    "lens_section_drawing", "vision_setup_drawing", "lens_element_drawing", "noncoaxial_drawing",
    "drawing_svg", "drawing_dxf", "drawing_raster", "svg_entities", "dxf_entities",
]

#: 層 → (線の太さ [紙の mm], DXF の色番号 ACI, 線種, SVG の色)。太い線 : 細い線 = 2 : 1(ISO 128 / JIS Z 8114)。
LAYERS = {
    "OUTLINE": (0.5, 7, "CONTINUOUS", "#111111"),
    "STOP": (0.5, 7, "CONTINUOUS", "#111111"),
    "IMAGE": (0.5, 7, "CONTINUOUS", "#111111"),
    "AXIS": (0.25, 8, "CENTER", "#555555"),
    "HIDDEN": (0.25, 8, "DASHED", "#555555"),
    "DIM": (0.25, 7, "CONTINUOUS", "#111111"),
    "TEXT": (0.25, 7, "CONTINUOUS", "#111111"),
    "FRAME": (0.5, 7, "CONTINUOUS", "#111111"),
    "THIN": (0.25, 7, "CONTINUOUS", "#111111"),
    "RAY_F1": (0.18, 5, "CONTINUOUS", "#1f4fd8"),
    "RAY_F2": (0.18, 3, "CONTINUOUS", "#1a8f3a"),
    "RAY_F3": (0.18, 1, "CONTINUOUS", "#d62728"),
    "RAY_F4": (0.18, 6, "CONTINUOUS", "#9a3fbf"),
    "RAY_F5": (0.18, 30, "CONTINUOUS", "#e07b00"),
    "RAY_F6": (0.18, 4, "CONTINUOUS", "#138a8a"),
    "PART": (0.5, 7, "CONTINUOUS", "#111111"),
    "CAMERA": (0.5, 7, "CONTINUOUS", "#111111"),
    "FOV": (0.18, 5, "CONTINUOUS", "#1f4fd8"),
    "DOF": (0.18, 3, "CONTINUOUS", "#1a8f3a"),
    "LIGHT": (0.35, 1, "CONTINUOUS", "#c0392b"),
    "LIGHTRAY": (0.18, 1, "CONTINUOUS", "#c0392b"),
}
#: DXF の線種の定義(名前 → (説明, 要素の長さ [紙の mm]、負は空白、0 は点))。ISO 128 の一点長鎖線と破線。
LTYPES = {
    "CONTINUOUS": ("Solid line", ()),
    "CENTER": ("Long dash dot ____ _ ____", (12.0, -3.0, 0.0, -3.0)),
    "DASHED": ("Dashed __ __ __", (6.0, -2.0)),
}
_MAX_FIELDS = 6
_MAX_RAYS = 41
_MAX_PROFILE = 2001
_MAX_ENTITIES = 200000
_MAX_TEXT_BYTES = 50 * 1024 * 1024
#: 紙の上の文字の高さ・矢印の長さ・寸法補助線の延長と隙間 [紙の mm]。ISO 3098(文字 3.5 / 2.5)・ISO 129-1。
TEXT_H = 3.5
TEXT_SMALL = 2.5
ARROW_L = 3.0
ARROW_HALF_DEG = 15.0
EXT_OVER = 2.0
EXT_GAP = 1.0
#: 文字の高さ(DXF の TEXT と同じく大文字の高さ)に対する、等幅の文字 1 字の送り(0.6 em ÷ 0.72)。
CHAR_W = 0.6 / 0.72
#: 大文字の高さ ÷ 文字の大きさ(em)。SVG の font-size と matplotlib の fontsize は em で指定する。
CAP_EM = 0.72
#: 縮尺の候補(紙の mm / 実物の mm)。JIS Z 8314 / ISO 5455 の推奨尺度。
_SCALES = (10.0, 5.0, 2.0, 1.0, 0.5, 0.2, 0.1, 0.05, 0.02)
#: ISO 10110-5 の干渉縞の既定の波長 [µm](水銀の e 線)。1 本の縞 = 面の高さで λ/2。
FRINGE_WL_UM = 0.54607
#: DXF の文字に許す記号(→ AutoCAD の制御コード)。ほかの非 ASCII は書けない。
_DXF_SPECIAL = {"⌀": "%%c", "°": "%%d", "±": "%%p", "∞": "INF"}
_DXF_BACK = {"%%c": "⌀", "%%C": "⌀", "%%d": "°", "%%D": "°", "%%p": "±", "%%P": "±"}


# --------------------------------------------------------------------------- #
# 検証
# --------------------------------------------------------------------------- #
def _num(v, name, op, positive=False, nonneg=False):
    if isinstance(v, (bool, np.bool_, str, bytes)) or v is None:
        raise ValueError("%s: %s must be a real number, got %r" % (op, name, v))
    try:
        x = float(v)
    except (TypeError, ValueError) as exc:
        raise ValueError("%s: %s must be a real number, got %r" % (op, name, v)) from exc
    if not math.isfinite(x):
        raise ValueError("%s: %s must be finite, got %r" % (op, name, v))
    if positive and x <= 0.0:
        raise ValueError("%s: %s must be > 0, got %r" % (op, name, v))
    if nonneg and x < 0.0:
        raise ValueError("%s: %s must be >= 0, got %r" % (op, name, v))
    return x


def _int(v, name, op, lo, hi):
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer)):
        raise ValueError("%s: %s must be an integer, got %r" % (op, name, v))
    i = int(v)
    if not lo <= i <= hi:
        raise ValueError("%s: %s must lie in [%d, %d], got %d" % (op, name, lo, hi, i))
    return i


def _system(system, op):
    if not isinstance(system, dict) or "surfaces" not in system or "stop" not in system:
        raise ValueError("%s: expected the table returned by raytrace.lens_system(), got %r"
                         % (op, type(system).__name__))
    for i, s in enumerate(system["surfaces"]):
        if s.get("mirror"):
            raise ValueError("%s: surface %d is a mirror — folded systems are not drawn (the 2-D meridional "
                             "section would overlap itself)" % (op, i))
        if tuple(s.get("tilt", (0.0, 0.0))) != (0.0, 0.0) or tuple(s.get("decenter", (0.0, 0.0))) != (0.0, 0.0):
            raise ValueError("%s: surface %d is tilted or decentred — only rotationally symmetric, centred "
                             "systems have a meridional section" % (op, i))
    return system


def _drawing(d, op):
    if not isinstance(d, dict) or d.get("kind") != "optdraw" or not isinstance(d.get("entities"), list):
        raise ValueError("%s: expected a drawing (the dict returned by lens_section_drawing / "
                         "vision_setup_drawing / lens_element_drawing), got %r" % (op, type(d).__name__))
    if len(d["entities"]) > _MAX_ENTITIES:
        raise ValueError("%s: %d entities exceed the limit %d" % (op, len(d["entities"]), _MAX_ENTITIES))
    for e in d["entities"]:
        if not isinstance(e, dict) or e.get("type") not in ("line", "polyline", "circle", "arc", "text"):
            raise ValueError("%s: entity %r is not one of line / polyline / circle / arc / text" % (op, e))
        if e.get("layer") not in LAYERS:
            raise ValueError("%s: entity on unknown layer %r (layers: %s)" % (op, e.get("layer"), sorted(LAYERS)))
    return d


# --------------------------------------------------------------------------- #
# 図の部品(実寸の mm で座標を積む)
# --------------------------------------------------------------------------- #
class _Sheet:
    """要素と寸法を積む入れ物。``s`` は縮尺(紙の mm / 実物の mm)で、文字と矢印の大きさを実物の mm に直すのに使う。"""

    def __init__(self, scale):
        self.s = float(scale)
        self.ents = []
        self.dims = []

    def p(self, v):
        """紙の mm → 実物の mm。"""
        return v / self.s

    def line(self, a, b, layer, tag=""):
        self.ents.append({"type": "line", "layer": layer, "points": [[float(a[0]), float(a[1])],
                                                                      [float(b[0]), float(b[1])]], "tag": tag})

    def poly(self, pts, layer, closed=False, fill=False, tag=""):
        pts = [[float(x), float(y)] for x, y in pts]
        self.ents.append({"type": "polyline", "layer": layer, "points": pts, "closed": bool(closed),
                          "fill": bool(fill), "tag": tag})

    def circle(self, c, r, layer, tag=""):
        self.ents.append({"type": "circle", "layer": layer, "center": [float(c[0]), float(c[1])],
                          "r": float(r), "tag": tag})

    def arc(self, c, r, a0, a1, layer, tag=""):
        """反時計回りに a0 → a1 [度](DXF の ARC と同じ向き)。"""
        self.ents.append({"type": "arc", "layer": layer, "center": [float(c[0]), float(c[1])], "r": float(r),
                          "start_deg": float(a0) % 360.0, "end_deg": float(a1) % 360.0, "tag": tag})

    def text(self, at, s, height=None, layer="TEXT", align="left", angle=0.0, tag=""):
        h = self.p(TEXT_H) if height is None else height
        self.ents.append({"type": "text", "layer": layer, "at": [float(at[0]), float(at[1])], "text": str(s),
                          "height": float(h), "align": align, "angle": float(angle), "tag": tag})

    def arrow(self, tip, direction, layer="DIM"):
        """塗りつぶしの矢印(開き角 30°、長さ 3 mm)。*direction* は矢の向き(先端へ)。"""
        u = np.asarray(direction, float)
        u = u / np.linalg.norm(u)
        n = np.array([-u[1], u[0]])
        L = self.p(ARROW_L)
        w = L * math.tan(math.radians(ARROW_HALF_DEG))
        t = np.asarray(tip, float)
        b = t - L * u
        self.poly([t, b + w * n, b - w * n], layer, closed=True, fill=True, tag="arrow")

    def dim(self, p1, p2, offset, text, name, value, layer="DIM"):
        """平行寸法(ISO 129-1): 寸法線は p1→p2 に平行で、法線の向きに *offset* [実物の mm] ずらす。

        寸法補助線は形体から ``EXT_GAP`` 離して始め、寸法線を ``EXT_OVER`` 越えて止める。矢印は内側に
        入らなければ外側から当てる。数字は寸法線の上(左回りの法線の側)に、線に平行に置く。
        """
        a = np.asarray(p1, float)
        b = np.asarray(p2, float)
        d = b - a
        L = float(np.linalg.norm(d))
        if not (math.isfinite(L) and L > 0.0):
            raise ValueError("dimension %s has zero or non-finite length" % name)
        u = d / L
        n = np.array([-u[1], u[0]])
        if offset < 0:
            n = -n
            offset = -offset
        a2 = a + offset * n
        b2 = b + offset * n
        g, o = self.p(EXT_GAP), self.p(EXT_OVER)
        if offset > g:
            self.line(a + g * n, a2 + o * n, layer, tag="ext:" + name)
            self.line(b + g * n, b2 + o * n, layer, tag="ext:" + name)
        al = self.p(ARROW_L)
        th = self.p(TEXT_H)
        tw = CHAR_W * th * len(text)
        if L >= 2.4 * al:
            self.line(a2, b2, layer, tag="dim:" + name)
            self.arrow(a2, -u, layer)
            self.arrow(b2, u, layer)
        else:                                            # 短い寸法: 矢印を外から当てる
            self.line(a2 - 2.0 * al * u, b2 + 2.0 * al * u, layer, tag="dim:" + name)
            self.arrow(a2, u, layer)
            self.arrow(b2, -u, layer)
        ang = math.degrees(math.atan2(u[1], u[0]))
        # 文字は下または右から読める向き(ISO 129-1 の方法 1)
        if ang > 90.0 + 1e-9 or ang <= -90.0 + 1e-9:
            ang += 180.0
            ang = (ang + 180.0) % 360.0 - 180.0
        tu = np.array([math.cos(math.radians(ang)), math.sin(math.radians(ang))])
        tn = np.array([-tu[1], tu[0]])
        mid = 0.5 * (a2 + b2)
        align = "center"
        if tw + 2.4 * al > L:                            # 数字が収まらなければ外へ出す
            if abs(u[1]) > abs(u[0]):
                # 縦に近い寸法: 線の延長に長い文字を立てると寸法線から離れて浮くので、寸法線の真横に
                # 水平に置く(外側 = 形体から遠い側)
                ang = 0.0
                side = 1.0 if n[0] >= 0 else -1.0
                top = a2 if a2[1] >= b2[1] else b2          # 上の矢印の脇(下の端は作業面などと重なりやすい)
                pos = top + side * self.p(1.5) * np.array([1.0, 0.0]) + np.array([0.0, self.p(1.0)])
                align = "left" if side > 0 else "right"
            else:
                far = b2 if float(np.dot(b2 - a2, tu)) >= 0 else a2
                pos = far + (2.2 * al + 0.5 * tw) * tu + self.p(1.0) * tn
        else:
            pos = mid + self.p(1.0) * tn
        self.text(pos, text, layer=layer, align=align, angle=ang, tag="dim:" + name)
        self.dims.append({"name": name, "value": float(value), "text": text,
                          "p1": [float(a[0]), float(a[1])], "p2": [float(b[0]), float(b[1])],
                          "offset": float(offset)})

    def axes(self, origin, labels, layer="THIN"):
        """図の座標軸の向き(矢印 2 本と軸の名前): 横向きの矢印に labels[0]、上向きに labels[1]。"""
        o = np.asarray(origin, float)
        L = self.p(12.0)
        for d, lab in ((np.array([1.0, 0.0]), labels[0]), (np.array([0.0, 1.0]), labels[1])):
            tip = o + L * d
            self.line(o, tip, layer, tag="axes")
            self.arrow(tip, d, layer)
            self.text(tip + self.p(2.0) * d - (np.array([0.0, 0.35]) * self.p(TEXT_SMALL) if d[0] else 0.0),
                      lab, height=self.p(TEXT_SMALL), layer="TEXT", align="left" if d[0] else "center",
                      tag="axes:" + lab)

    def angle_dim(self, c, r, a0, a1, text, name, value, layer="DIM"):
        """角度の寸法: 中心 *c*・半径 *r* の円弧(a0 → a1 度、反時計回り)と両端の矢印と数字。"""
        self.arc(c, r, a0, a1, layer, tag="dim:" + name)
        for a, sgn in ((a0, -1.0), (a1, 1.0)):
            t = math.radians(a)
            tip = (c[0] + r * math.cos(t), c[1] + r * math.sin(t))
            tang = (-math.sin(t) * sgn, math.cos(t) * sgn)
            self.arrow(tip, tang, layer)
        am = math.radians(0.5 * (a0 + a1))
        rr = r + self.p(2.0)
        self.text((c[0] + rr * math.cos(am), c[1] + rr * math.sin(am)), text, layer=layer, align="left",
                  tag="dim:" + name)
        self.dims.append({"name": name, "value": float(value), "text": text, "center": [float(c[0]), float(c[1])],
                          "radius": float(r), "start_deg": float(a0), "end_deg": float(a1)})


def _bbox(ents):
    xs, ys = [], []
    for e in ents:
        if e["type"] in ("line", "polyline"):
            for x, y in e["points"]:
                xs.append(x); ys.append(y)
        elif e["type"] in ("circle", "arc"):
            cx, cy = e["center"]
            r = e["r"]
            xs += [cx - r, cx + r]; ys += [cy - r, cy + r]
        else:
            x, y = e["at"]
            w = CHAR_W * e["height"] * len(e["text"])
            if abs(e.get("angle", 0.0)) > 45.0:
                xs += [x - e["height"], x + e["height"]]; ys += [y - w, y + w]
            else:
                lo = {"left": 0.0, "center": -0.5 * w, "right": -w}[e.get("align", "left")]
                xs += [x + lo, x + lo + w]; ys += [y, y + e["height"]]
    return [min(xs), min(ys), max(xs), max(ys)]


def _auto_scale(extent_mm, paper_mm):
    """ISO 5455 の推奨尺度のうち、図が *paper_mm* に収まる最大のもの。"""
    for s in _SCALES:
        if extent_mm * s <= paper_mm:
            return s
    return _SCALES[-1]


def _scale_label(s):
    if s >= 1.0:
        return "%g:1" % s
    return "1:%g" % (1.0 / s)


def _finish(sheet, name, values, meta, title_lines=()):
    """枠と表題を足して図の dict にする。"""
    ents = sheet.ents
    x0, y0, x1, y1 = _bbox(ents)
    m = sheet.p(8.0)
    th = sheet.p(TEXT_SMALL)
    yb = y0 - m - th * (1.6 * len(title_lines) + 1.6)
    yy = y0 - m
    for i, ln in enumerate(title_lines):
        sheet.text((x0, yy - 1.6 * th * (i + 1)), ln, height=th, layer="TEXT", tag="title")
    fx0, fy0, fx1, fy1 = x0 - m, yb - m * 0.5, x1 + m, y1 + m
    sheet.poly([(fx0, fy0), (fx1, fy0), (fx1, fy1), (fx0, fy1)], "FRAME", closed=True, tag="frame")
    return {"kind": "optdraw", "name": name, "scale": sheet.s, "units": "mm", "entities": ents,
            "dimensions": sheet.dims, "values": values, "meta": meta,
            "frame": [fx0, fy0, fx1, fy1]}


# --------------------------------------------------------------------------- #
# 1. レンズの断面図
# --------------------------------------------------------------------------- #
def _vertices(system):
    z = [0.0]
    for s in system["surfaces"][:-1]:
        z.append(z[-1] + float(s["t"]))
    return z


def _curv(s):
    return 0.0 if s["R"] == RT.INF else 1.0 / s["R"]


def _sag_profile(s, y):
    """面 *s* の sag(``raytrace`` の円錐 + 偶数次の非球面の式)。図の面の形はここだけで決まる。"""
    return RT._sag(np.asarray(y, float) ** 2, _curv(s), s["k"], s["asph"], RT._xtra(s))


def _is_glass(s):
    return float(s["n_value"]) > 1.0 + 1e-9


def _stop_hit(system, P, D):
    tr = RT.trace_rays(system, P, D, image_mm=0.0)
    return tr, tr["points"][:, system["stop"] + 1, 1]


def _aim(system, field, q):
    """絞りの上の高さ ``q·ap``(子午面、x = 0)を通る実光線を割線法で探す(``q`` は配列)。

    入射瞳を経由しないので、入射瞳が無限遠の物体側テレセンでも、近軸の瞳と実の瞳がずれる広角でも同じ式で動く。
    無限遠の物体は光線の高さを、有限の物体は物点から出る傾きを未知数にする。返り値は (P, D, ok)。
    ★狙うあいだは**どの面の口径も外す**(口径の外に出た試し打ちが NaN になると割線法が戻れない —— 物体側
    テレセンの小さな絞りで初期値が全部外れた)。蹴られるかどうかは、狙った光線を本来の処方で追い直して決める。
    """
    q = np.asarray(q, float)
    free = dict(system)
    free["surfaces"] = [dict(sf, ap=None) for sf in system["surfaces"]]
    stop = system["stop"]
    target = q * system["surfaces"][stop]["ap"] * (1.0 - 1e-9)
    zv = _vertices(system)
    z_stop = zv[stop]
    obj = system["object_mm"]
    n = len(q)
    if obj == RT.INF:
        th = math.radians(field)
        dvec = np.array([0.0, math.sin(th), math.cos(th)])
        z0 = -1.0 - max(abs(float(_sag_profile(system["surfaces"][0], [system["surfaces"][0]["ap"] or 0.0])[0]))
                        if system["surfaces"][0]["ap"] else 0.0, 0.0)

        def make(u):
            P = np.stack([np.zeros(n), u, np.full(n, z0)], 1)
            return P, np.tile(dvec, (n, 1))
        # 直線で絞りの面まで進んだときに target を通る高さ(屈折を無視した初期値)
        u0 = target - (z_stop - z0) * math.tan(th)
        u1 = u0 + 0.01 * (1.0 + np.abs(u0))
    else:
        h = float(field)

        def make(u):
            D = np.stack([np.zeros(n), u, np.ones(n)], 1)
            D = D / np.linalg.norm(D, axis=1, keepdims=True)
            return np.tile([0.0, h, -obj], (n, 1)), D
        u0 = (target - h) / (obj + z_stop)
        u1 = u0 * 1.01 + 1e-4
    _, f0 = _stop_hit(free, *make(u0))
    f0 = f0 - target
    _, f1 = _stop_hit(free, *make(u1))
    f1 = f1 - target
    for _ in range(60):
        with np.errstate(invalid="ignore", divide="ignore"):
            u2 = u1 - f1 * (u1 - u0) / (f1 - f0)
        u2 = np.where(np.isfinite(u2), u2, u1)
        _, f2 = _stop_hit(free, *make(u2))
        f2 = f2 - target
        u0, f0, u1, f1 = u1, f1, u2, f2
        good = np.isfinite(f1)
        if np.all(np.abs(f1[good]) < 1e-11) if np.any(good) else True:
            break
    P, D = make(u1)
    ok = np.isfinite(f1) & (np.abs(np.nan_to_num(f1, nan=1.0)) < 1e-8)
    return P, D, ok


def _fmt(v, nd=2):
    return ("%." + str(nd) + "f") % v


def lens_section_drawing(system, fields=None, rays=3, lead_mm=None, edge_margin_pct=5.0, scale=None,
                         profile_points=121, title=None):
    """レンズの子午断面図(``table``、図の dict)—— 処方の面・コバ・絞り・像面と、視野ごとに色を分けた実光線と寸法。

    *system* は ``raytrace.lens_system`` の処方。*fields* は視野の列(物体が無限遠なら度、有限なら物体の高さ mm、
    既定は処方の ``field`` を F として ``(0, 0.7F, F)``、F = 0 なら軸上だけ)、*rays* は視野ごとに描く光線の本数
    (絞りの上で等間隔、両端は口径の縁、1 なら主光線だけ)。光線は**絞りを狙って**実光線で追跡する(割線法で絞りの
    上の高さを合わせる)ので、入射瞳が無限遠の物体側テレセンでも描ける。面の形は ``raytrace`` の sag の式(円錐 +
    偶数次の非球面)、面の有効半径は面の ``ap``、無ければ全視野の子午面の実光線(視野あたり 21 本)の最大の高さ。
    コバ(レンズの外周)は有効半径の最大に *edge_margin_pct* % を足した半径で、有効半径の外は平らな座で描く
    (光学設計ソフトの断面図と同じ作法)。

    寸法線: BFL(最終面 → 後側焦点 F′)・EFL(後側主点 H′ → F′)・全長(第 1 面 → 像面)・像高(最大視野の主光線)。
    処方表(面ごとの R・間隔・n_d・ν_d)と諸元(EFL・BFL・F 値・全長・視野・波長)を文字で書く。*scale* は
    紙の mm / 実物の mm(既定は ISO 5455 の推奨尺度から幅 250 mm に収まる最大)。

    返り値: ``{"kind": "optdraw", "entities", "dimensions", "values", "meta", "scale", "frame"}``。``values`` は
    図に書いた数の正本(``efl`` / ``bfl`` / ``total_track`` / ``image_height`` / ``fno`` / 面ごとの
    ``vertex_z`` ``semi_diameter`` / 光線ごとの面上の交点 ``rays``)。``drawing_svg`` / ``drawing_dxf`` で書き出す。
    平面の ``R`` は ``lens_system`` の規約どおり ``inf``、無焦点の系(両側テレセン)の ``efl`` / ``bfl`` も ``inf``
    (非有限は契約。図には描かず、描かなかった寸法の名前を ``dimensions_skipped`` に残す)。
    鏡・傾き・偏心のある処方(と ``raytrace3d.noncoaxial_system`` の系)は ``noncoaxial_drawing`` に回す(折り返した系の
    断面図)。★縁の厚さが負になる処方は ValueError。
    """
    op = "lens_section_drawing"
    if isinstance(system, dict) and system.get("kind") == "noncoaxial_system":
        return noncoaxial_drawing(system, fields=fields, rays=rays, scale=scale, title=title)
    if isinstance(system, dict) and "surfaces" in system and any(
            s.get("mirror") or tuple(s.get("tilt", (0.0, 0.0))) != (0.0, 0.0)
            or tuple(s.get("decenter", (0.0, 0.0))) != (0.0, 0.0) for s in system["surfaces"]):
        import raytrace3d as R3
        return noncoaxial_drawing(R3.noncoaxial_system(system), fields=fields, rays=rays, scale=scale, title=title)
    _system(system, op)
    nr = _int(rays, "rays", op, 1, _MAX_RAYS)
    npf = _int(profile_points, "profile_points", op, 11, _MAX_PROFILE)
    margin = _num(edge_margin_pct, "edge_margin_pct", op, nonneg=True) / 100.0
    surf = system["surfaces"]
    F = float(system["field"])
    if fields is None:
        fields = (0.0,) if F == 0.0 else (0.0, 0.7 * F, F)
    if isinstance(fields, (int, float, np.integer, np.floating)) and not isinstance(fields, bool):
        fields = (fields,)
    fields = [_num(f, "fields[%d]" % i, op) for i, f in enumerate(list(fields))]
    if not 1 <= len(fields) <= _MAX_FIELDS:
        raise ValueError("%s: give 1..%d fields, got %d" % (op, _MAX_FIELDS, len(fields)))
    para = RT.paraxial_trace(system)
    zv = _vertices(system)
    # --- 光線: 有効半径を決める密な束と、描く束 ---
    q_dense = np.linspace(-1.0, 1.0, 21)
    q_draw = np.array([0.0]) if nr == 1 else np.linspace(-1.0, 1.0, nr)
    sd_ray = np.zeros(len(surf))
    traced = []
    z_img = None
    for j, f in enumerate(fields):
        P, D, ok = _aim(system, f, q_dense)
        tr = RT.trace_rays(system, P, D)
        v = tr["valid"] & ok
        if not np.any(v):
            raise ValueError("%s: no real ray of field %g reaches the image (vignetted or aimed outside)" % (op, f))
        ys = np.abs(tr["points"][v][:, 1:len(surf) + 1, 1])
        sd_ray = np.maximum(sd_ray, ys.max(0))
        P, D, ok = _aim(system, f, q_draw)
        tr = RT.trace_rays(system, P, D)
        z_img = tr["z_image_global"]
        traced.append((f, q_draw, tr, tr["valid"] & ok))
    sd = np.array([s["ap"] if s["ap"] is not None else sd_ray[i] for i, s in enumerate(surf)], float)
    if np.any(sd <= 0.0):
        raise ValueError("%s: a surface has zero clear aperture (give it an 'ap')" % op)
    for i, s in enumerate(surf):
        if s["R"] != RT.INF and s["k"] > -1.0 and (1.0 + s["k"]) * (sd[i] / s["R"]) ** 2 >= 1.0:
            raise ValueError("%s: surface %d semi-diameter %.4g exceeds the conic's extent" % (op, i, sd[i]))
    # --- 要素(ガラスの連続) ---
    groups = []
    i = 0
    while i < len(surf):
        if _is_glass(surf[i]):
            j = i
            while j < len(surf) and _is_glass(surf[j]):
                j += 1
            if j >= len(surf):
                raise ValueError("%s: the medium after the last surface is glass — the image lies inside glass" % op)
            groups.append(list(range(i, j + 1)))
            i = j + 1
        else:
            i += 1
    r_out = np.array(sd, float)
    edge_t = []
    for g in groups:
        R = float(max(sd[g])) * (1.0 + margin)
        for k in g:
            r_out[k] = R
        for a, b in zip(g[:-1], g[1:]):
            za = zv[a] + float(_sag_profile(surf[a], [sd[a]])[0])
            zb = zv[b] + float(_sag_profile(surf[b], [sd[b]])[0])
            if zb - za < 0.0:
                raise ValueError("%s: surfaces %d-%d: the edge thickness %.4g mm is negative — the element cannot be "
                                 "made (thicken it or reduce the aperture)" % (op, a, b, zb - za))
            edge_t.append({"surfaces": [a, b], "edge_thickness_mm": zb - za})
    # --- 縮尺 ---
    span_z = max(z_img, zv[-1]) - min(0.0, float(min(_sag_profile(surf[0], [sd[0]])[0], 0.0)))
    lead = (0.25 * span_z if lead_mm is None else _num(lead_mm, "lead_mm", op, positive=True))
    ymax = float(max(r_out.max(), max(abs(float(np.nanmax(np.abs(t[2]["points"][:, :, 1][t[3]])))) if np.any(t[3])
                                          else 0.0 for t in traced)))
    if scale is None:
        s = _auto_scale(span_z + lead + 0.1 * span_z, 250.0)
    else:
        s = _num(scale, "scale", op, positive=True)
    sh = _Sheet(s)
    z_first = -lead
    # 光軸
    sh.line((z_first - sh.p(4.0), 0.0), (max(z_img, zv[-1]) + sh.p(6.0), 0.0), "AXIS", tag="axis")
    # 面
    surf_rec = []
    for i, srf in enumerate(surf):
        y = np.linspace(-sd[i], sd[i], npf)
        z = zv[i] + _sag_profile(srf, y)
        if not np.all(np.isfinite(z)):
            raise ValueError("%s: surface %d sag is not finite inside its semi-diameter" % (op, i))
        in_group = any(i in g for g in groups)
        ideal = srf.get("f") is not None
        is_stop_only = (i == system["stop"]) and not in_group and srf["R"] == RT.INF and not ideal
        if in_group:
            sh.poly(np.stack([z, y], 1), "OUTLINE", tag="surface:%d" % i)
            ze = zv[i] + float(_sag_profile(srf, [sd[i]])[0])
            if r_out[i] > sd[i]:
                sh.line((ze, sd[i]), (ze, r_out[i]), "OUTLINE", tag="flat:%d" % i)
                sh.line((ze, -sd[i]), (ze, -r_out[i]), "OUTLINE", tag="flat:%d" % i)
        elif not is_stop_only:
            sh.poly(np.stack([z, y], 1), "THIN", tag="surface:%d" % i)       # 空気の中の面(ダミー面)
        if ideal:                                  # 理想レンズ: 細い線 + 両端の矢じり(収束 = 外向き、発散 = 内向き)
            outward = srf["f"] > 0.0
            for sg in (1.0, -1.0):
                yt = sd[i] if outward else sd[i] - sh.p(ARROW_L)
                sh.arrow((zv[i], sg * yt), (0.0, sg if outward else -sg), layer="THIN")
        surf_rec.append({"index": i, "vertex_z": zv[i], "semi_diameter": float(sd[i]), "outer_radius": float(r_out[i]),
                         "R": srf["R"], "k": srf["k"], "asph": list(srf["asph"]),
                         "f": srf.get("f")})
        lab_y = r_out[i] + sh.p(3.0)
        if surf_rec[:-1] and abs(zv[i] - surf_rec[-2]["vertex_z"]) < sh.p(CHAR_W * TEXT_SMALL * 3.0):
            lab_y = max(lab_y, surf_rec[-2]["label_y"] + sh.p(1.8 * TEXT_SMALL))   # 近い面の番号は段をずらす
        surf_rec[-1]["label_y"] = lab_y
        sh.text((zv[i], lab_y), "S%d" % (i + 1), height=sh.p(TEXT_SMALL), align="center", tag="label:surface")
    for g in groups:
        for a, b in zip(g[:-1], g[1:]):
            za = zv[a] + float(_sag_profile(surf[a], [sd[a]])[0])
            zb = zv[b] + float(_sag_profile(surf[b], [sd[b]])[0])
            for sg in (1.0, -1.0):
                sh.line((za, sg * r_out[a]), (zb, sg * r_out[b]), "OUTLINE", tag="edge")
    # 絞り
    st = system["stop"]
    ap = surf[st]["ap"]
    zs = zv[st] + float(_sag_profile(surf[st], [ap])[0])
    mark = max(sh.p(4.0), 0.12 * ymax)
    for sg in (1.0, -1.0):
        sh.line((zs, sg * ap), (zs, sg * (ap + mark)), "STOP", tag="stop")
    sh.text((zs, -(ap + mark) - sh.p(4.0)), "STO", height=sh.p(TEXT_SMALL), align="center", tag="label:stop")
    # 光線
    rays_rec = []
    n_vig = 0
    for j, (f, qs, tr, valid) in enumerate(traced):
        layer = "RAY_F%d" % (j + 1)
        for r in range(len(qs)):
            if not valid[r]:
                n_vig += 1
                continue
            pts = tr["points"][r]
            p0, d0 = pts[0], tr["dirs"][r, 0]
            if system["object_mm"] == RT.INF or system["object_mm"] > 3.0 * span_z:
                t0 = (z_first - p0[2]) / d0[2]
                start = p0 + t0 * d0
            else:
                start = p0
            seq = [start] + [pts[k] for k in range(1, len(surf) + 2)]
            sh.poly([(p[2], p[1]) for p in seq], layer, tag="ray:%d:%d" % (j, r))
            rays_rec.append({"field_index": j, "field": f, "pupil": float(qs[r]),
                             "points_zy": [[float(p[2]), float(p[1])] for p in seq[1:]]})
    # 像面
    y_img = max([abs(rr["points_zy"][-1][1]) for rr in rays_rec] + [0.0])
    h_img = max(1.15 * y_img, 0.3 * ymax)
    sh.line((z_img, -h_img), (z_img, h_img), "IMAGE", tag="image")
    sh.text((z_img, h_img + sh.p(3.0)), "IMA", height=sh.p(TEXT_SMALL), align="center", tag="label:image")
    # 物体(有限で、近ければ)
    if system["object_mm"] != RT.INF and system["object_mm"] <= 3.0 * span_z:
        zo = -system["object_mm"]
        hmax = max(abs(f) for f in fields)
        sh.line((zo, -max(hmax, 0.3 * ymax)), (zo, max(hmax, 0.3 * ymax)), "THIN", tag="object")
        sh.text((zo, max(hmax, 0.3 * ymax) + sh.p(3.0)), "OBJ", height=sh.p(TEXT_SMALL), align="center",
                tag="label:object")
    # 主点と焦点
    z_last = zv[-1]
    efl, bfl = para["efl"], para["bfl"]
    zF = z_last + bfl
    zH = z_last + para["pp_rear"]
    tick = sh.p(3.0)
    afocal = not (math.isfinite(efl) and math.isfinite(bfl))      # 両側テレセン(無焦点)は F′ も H′ も無い
    if not afocal:
        sh.line((zH, -0.6 * ymax), (zH, 0.6 * ymax), "HIDDEN", tag="H'")
        sh.text((zH, 0.6 * ymax + sh.p(1.5)), "H'", height=sh.p(TEXT_SMALL), align="center", tag="label:H'")
        sh.line((zF, -tick), (zF, tick), "THIN", tag="F'")
        sh.text((zF + sh.p(1.0), tick), "F'", height=sh.p(TEXT_SMALL), align="left", tag="label:F'")
    # 寸法
    ybase = -max(ymax, h_img)
    step = sh.p(9.0)
    # 寸法補助線は図の下端から引き出す(レンズと光線を横切らない)。長さ 0 の寸法(最終面が後側焦点に
    # ある物体側テレセンの BFL など)は描けないので、描かなかった名前を values に残す。
    skipped = []
    for k, (za, zb, nm, val) in enumerate(((z_last, zF, "BFL", bfl), (zH, zF, "EFL", efl), (0.0, z_img, "OAL", z_img))):
        if not (math.isfinite(za) and math.isfinite(zb)) or abs(zb - za) < 1e-9:
            skipped.append(nm)
            continue
        sh.dim((za, ybase), (zb, ybase), -(k + 1) * step, nm + " " + _fmt(val), nm, val)
    # 像高(最大視野の主光線)
    chief = [rr for rr in rays_rec if rr["pupil"] == 0.0 and rr["field_index"] == len(fields) - 1]
    img_h = None
    if chief and abs(chief[0]["points_zy"][-1][1]) > 1e-9:
        img_h = chief[0]["points_zy"][-1][1]
        sh.dim((z_img, 0.0), (z_img, img_h), -sh.p(10.0) if img_h > 0 else sh.p(10.0),
               "IMH " + _fmt(abs(img_h)), "IMH", abs(img_h))
    # 処方表と諸元
    th = sh.p(TEXT_SMALL)
    x_tab = z_first
    y_tab = ybase - 3 * step - sh.p(10.0)
    fu = "deg" if system["object_mm"] == RT.INF else "mm"
    # ★入射瞳が無限遠(物体側テレセン)では近軸の F 値 = EFL / 入射瞳径 が 0 になる —— 意味の無い「F/0.00」を書かない
    fno_s = _fmt(para["fno"]) if (math.isfinite(para["fno"]) and para["fno"] > 0.0) else "-"
    spec = [("AFOCAL   m %.4f   OAL %s" % (para["magnification"], _fmt(z_img))) if afocal else
            "EFL %s   BFL %s   F/%s   OAL %s" % (_fmt(efl), _fmt(bfl), fno_s, _fmt(z_img)),
            "FIELD %s %s   WL %.1f nm   STOP S%d" % (" / ".join(_fmt(f, 1) for f in fields), fu,
                                                    1000.0 * system["wavelength_um"], st + 1)]
    for k, ln in enumerate(spec):
        sh.text((x_tab, y_tab - 1.7 * th * k), ln, height=th, tag="spec:%d" % k)
    y_tab -= 1.7 * th * (len(spec) - 1)
    rows = ["SURF        R           T        n_d       v_d      SD"]
    for i, srf in enumerate(surf):
        nd, vd = _nd_vd(srf["n"])
        rs = "INF" if srf["R"] == RT.INF else "%.4f" % srf["R"]
        ts = "-" if srf["t"] is None else "%.4f" % srf["t"]
        if i == len(surf) - 1:
            ts = "%.4f" % (z_img - zv[-1])
        nds = "%.5f" % nd if nd > 1.0 + 1e-9 else "air"
        vds = ("%.2f" % vd) if (nd > 1.0 + 1e-9 and math.isfinite(vd)) else "-"
        rows.append("S%-3d %12s %10s %9s %9s %7.3f%s" % (i + 1, rs, ts, nds, vds, sd[i],
                                                          "  STO" if i == st else ""))
    for k, row in enumerate(rows):
        sh.text((x_tab, y_tab - 1.7 * th * (k + 1)), row, height=th, tag="prescription:%d" % (k - 1))
    values = {"efl": efl, "bfl": bfl, "fno": para["fno"], "total_track": z_img, "image_height": img_h,
              "pp_rear": para["pp_rear"], "image_z": z_img, "fields": fields, "surfaces": surf_rec,
              "edge_thickness": edge_t, "rays": rays_rec, "rays_vignetted": n_vig,
              "field_unit": fu, "scale": s, "dimensions_skipped": skipped}
    meta = {"source": "raytrace.lens_system", "groups": groups, "stop": st,
            "conventions": "x = optical axis z (light left to right), y = meridional height; mm"}
    title_lines = [title or "LENS LAYOUT (MERIDIONAL SECTION)", "UNITS mm   SCALE " + _scale_label(s)]
    return _finish(sh, title or "lens_section", values, meta, title_lines)


def _nd_vd(medium):
    """媒質の n_d と ν_d = (n_d − 1)/(n_F − n_C)。分散の無い媒質は ν_d = inf。"""
    nd = RT.refractive_index(medium, RT.WL_D)
    nF = RT.refractive_index(medium, RT.WL_F)
    nC = RT.refractive_index(medium, RT.WL_C)
    vd = (nd - 1.0) / (nF - nC) if nF - nC > 0.0 else math.inf
    return float(nd), float(vd)


# --------------------------------------------------------------------------- #
# 2. 撮像系の設置図
# --------------------------------------------------------------------------- #
def _box_edges(center, axes, half):
    """中心・3 本の軸(単位ベクトル)・半分の大きさの直方体の 12 辺(3-D の線分の列)。"""
    c = np.asarray(center, float)
    corners = {}
    for i in (-1, 1):
        for j in (-1, 1):
            for k in (-1, 1):
                corners[(i, j, k)] = c + i * half[0] * axes[0] + j * half[1] * axes[1] + k * half[2] * axes[2]
    edges = []
    for (i, j, k), p in corners.items():
        for d in range(3):
            key = [i, j, k]
            if key[d] == -1:
                key[d] = 1
                edges.append((p, corners[tuple(key)]))
    return edges


def vision_setup_drawing(layout, view="both", barrel_diameter_mm=30.0, body_mm=40.0, scale=None, title=None):
    """撮像系の設置図(``table``、図の dict)—— ``optscene.vision_layout`` から側面図と上面図を描く。

    描くもの: 作業面(z = 0)と部品(``scene`` があれば箱・円筒・球・板を投影、くり抜きは破線)、カメラ(鏡筒・
    本体・センサー面。鏡筒の先端 = 主点 = ``optscene`` のピンホール)、光軸(一点鎖線)、視野の錐(センサーの 4 隅の
    画素の縁から逆投影した 4 本の光線と、作業面の上の視野の四角)、被写界深度の帯(光軸に沿って ±DOF/2)、照明 5 種
    (ring = 円環と仰角、dome = 半球と天頂の穴、bar = 棒と仰角、coaxial = ハーフミラーと横の光源、backlight = 部品の
    下の面光源)と光の向きの矢印。寸法: 作動距離 WD・視野の幅(側面図は縦 = センサーの高さ方向、上面図は両方)・
    DOF・照明の高さと半径・仰角。諸元の表(倍率・作動 F 値・回折限界・物体側の画素・DOF・律速)を文字で書く。

    *view* は ``"side"`` / ``"top"`` / ``"both"``。側面図は (y, z)、上面図は (y, x) で、第三角法の並び(上面図を
    側面図の上に置き、横軸 y を共有する)。センサーの像の横(``camera`` の right)は世界の x、縦は y。
    ★鏡筒の大きさ(*barrel_diameter_mm*)とカメラ本体(*body_mm*)は ``lens_spec`` に無いので図のための仮の寸法。
    作動距離は ``optscene`` の薄肉の模型どおり**物体から主点まで**(実機のカタログの WD は前玉の先端から)。

    返り値の ``values``: ``working_distance`` / ``fov_mm``(横, 縦)/ ``dof_mm`` / ``magnification`` /
    ``fov_corners``(作業面の上の 4 隅、3-D)/ ``lights``(照明ごとの種類・高さ・半径・仰角)。
    """
    op = "vision_setup_drawing"
    if not isinstance(layout, dict) or layout.get("kind") != "layout":
        raise ValueError("%s: expected the dict returned by optscene.vision_layout(), got %r"
                         % (op, type(layout).__name__))
    if view not in ("side", "top", "both"):
        raise ValueError("%s: view must be 'side', 'top' or 'both', got %r" % (op, view))
    bd = _num(barrel_diameter_mm, "barrel_diameter_mm", op, positive=True)
    body = _num(body_mm, "body_mm", op, positive=True)
    cam, lens, sensor, budget = layout["camera"], layout["lens"], layout["sensor"], layout["budget"]
    lights = layout["lights"]
    K = np.asarray(cam["K"], float)
    Rm = np.asarray(cam["R"], float)
    eye = np.asarray(cam["eye"], float)
    fwd = np.asarray(cam["forward"], float)
    right, down = Rm[0], Rm[1]
    w, h = int(cam["width"]), int(cam["height"])
    f = float(cam["focal_mm"])
    wd = float(cam["working_distance_mm"])
    look = eye + wd * fwd
    if abs(fwd[2]) < 1e-9:
        raise ValueError("%s: the camera looks parallel to the work plane" % op)
    # 視野の 4 隅: 画素の縁(-0.5 と w-0.5)を逆投影して作業面(look の高さ)と交わらせる
    Kinv = np.linalg.inv(K)
    corners = []
    for u, v in ((-0.5, -0.5), (w - 0.5, -0.5), (w - 0.5, h - 0.5), (-0.5, h - 0.5)):
        dc = Kinv @ np.array([u, v, 1.0])
        dw = Rm.T @ dc
        t = (look[2] - eye[2]) / dw[2]
        corners.append(eye + t * dw)
    corners = np.array(corners)
    dof = float(budget["dof_um"]) / 1000.0
    v_img = f * wd / (wd - f)                           # 薄肉レンズの像距離(主点 → センサー)
    sensor_w, sensor_h = w * cam["pixel_mm"], h * cam["pixel_mm"]
    # --- 3-D の部品を線分の列に ---
    segs = []                                           # (p, q, layer, tag)
    axes_cam = (right, down, fwd)
    barrel_c = eye - fwd * (0.5 * v_img)
    for p, q in _box_edges(barrel_c, axes_cam, (0.5 * bd, 0.5 * bd, 0.5 * v_img)):
        segs.append((p, q, "CAMERA", "barrel"))
    body_c = eye - fwd * (v_img + 0.5 * body)
    for p, q in _box_edges(body_c, axes_cam, (0.5 * body, 0.5 * body, 0.5 * body)):
        segs.append((p, q, "CAMERA", "body"))
    sc = eye - fwd * v_img
    sq = [sc + a * 0.5 * sensor_w * right + b * 0.5 * sensor_h * down for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    for k in range(4):
        segs.append((sq[k], sq[(k + 1) % 4], "OUTLINE", "sensor"))
    segs.append((eye - fwd * (v_img + body + 10.0), look, "AXIS", "axis"))
    for c in corners:
        segs.append((eye, c, "FOV", "fov_ray"))
    for k in range(4):
        segs.append((corners[k], corners[(k + 1) % 4], "FOV", "fov"))
    band = []
    for sgn in (-1.0, 1.0):
        cc = look + sgn * 0.5 * dof * fwd
        band.append([cc + a * 0.5 * (corners[:, 0].max() - corners[:, 0].min()) * right
                     + b * 0.5 * (corners[:, 1].max() - corners[:, 1].min()) * down
                     for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
    for q4 in band:
        for k in range(4):
            segs.append((q4[k], q4[(k + 1) % 4], "DOF", "dof"))
    for k in range(4):
        segs.append((band[0][k], band[1][k], "DOF", "dof"))
    # 部品
    scene = layout.get("scene") or []
    for obj in scene:
        _scene_segments(obj, segs, "PART")
    # 照明
    light_rec = []
    for li, L in enumerate(lights):
        light_rec.append(_light_segments(L, li, segs))
    extent = np.array([[p[0], p[1], p[2]] for s in segs for p in (s[0], s[1])])
    span_y = extent[:, 1].max() - extent[:, 1].min()
    span_x = extent[:, 0].max() - extent[:, 0].min()
    span_z = extent[:, 2].max() - extent[:, 2].min()
    tall = span_z + (span_x if view == "both" else 0.0) if view != "top" else span_x
    if scale is None:
        s = min(_auto_scale(span_y + 60.0, 260.0), _auto_scale(tall + 80.0, 360.0))
    else:
        s = _num(scale, "scale", op, positive=True)
    sh = _Sheet(s)
    z_lo = min(extent[:, 2].min(), -5.0)
    top_off = extent[:, 2].max() + sh.p(40.0) - extent[:, 0].min()   # 上面図の縦の位置(第三角法: 側面図の上)

    def side(p):
        return (p[1], p[2])

    def top(p):
        return (p[1], p[0] + top_off)
    views = []
    if view in ("side", "both"):
        views.append(("SIDE", side))
    if view in ("top", "both"):
        views.append(("TOP", top))
    for vname, proj in views:
        for p, q, layer, tag in segs:
            if tag.startswith("light_top:") and vname != "TOP":
                continue
            if tag.startswith("light_side:") and vname != "SIDE":
                continue
            a, b = proj(p), proj(q)
            if math.hypot(a[0] - b[0], a[1] - b[1]) < 1e-9:
                continue                                    # 視線方向の辺は点に潰れる
            sh.line(a, b, layer, tag=vname.lower() + ":" + tag)
        # 円(照明の円環・ドームの上面図)
        for L, rec in zip(lights, light_rec):
            for circ in rec["circles"]:
                if circ["view"] == vname:
                    c = proj(circ["center"])
                    sh.circle(c, circ["r"], circ["layer"], tag=vname.lower() + ":" + circ["tag"])
            for arc in rec["arcs"]:
                if arc["view"] == vname:
                    c = proj(arc["center"])
                    sh.arc(c, arc["r"], arc["a0"], arc["a1"], arc["layer"], tag=vname.lower() + ":" + arc["tag"])
    # 作業面の線(側面図)と視野の寸法
    ymin_all = extent[:, 1].min() - 10.0
    ymax_all = extent[:, 1].max() + 10.0
    if view in ("side", "both"):
        sh.line((ymin_all, 0.0), (ymax_all, 0.0), "PART", tag="side:work_plane")
        for k in range(8):                               # 作業面の下のハッチ(切断面ではなく地の表示)
            x = ymin_all + (k + 0.5) * (ymax_all - ymin_all) / 8.0
            sh.line((x, 0.0), (x - sh.p(3.0), -sh.p(3.0)), "THIN", tag="side:ground")
        yv = sorted(side(c)[0] for c in corners)
        fov_side = yv[-1] - yv[0]
        sh.dim((yv[0], look[2]), (yv[-1], look[2]), z_lo - look[2] - sh.p(22.0), "FOV " + _fmt(fov_side), "FOV_side",
               fov_side)
        # 作動距離: 物体の点 → 主点(光軸に平行な寸法、右側のいちばん外)
        sh.dim(tuple(side(look)), tuple(side(eye)), -(ymax_all - side(look)[0] + sh.p(12.0)), "WD " + _fmt(wd), "WD",
               wd)
        # DOF の帯の厚さ(光軸に沿う、視野の左 —— 右は WD と棒照明に空ける)
        p1, p2 = side(look - 0.5 * dof * fwd), side(look + 0.5 * dof * fwd)
        off = 0.5 * (corners[:, 1].max() - corners[:, 1].min()) + sh.p(8.0)
        sh.dim(p1, p2, -off, "DOF " + _fmt(dof, 3), "DOF", dof)
        sh.text((ymin_all, z_lo - sh.p(34.0)), "SIDE VIEW (Y-Z)", height=sh.p(TEXT_SMALL), tag="side:label")
        sh.axes((ymin_all - sh.p(20.0), z_lo - sh.p(30.0)), ("+Y", "+Z"))
        bc = side(body_c)
        sh.text((bc[0] + 0.5 * body + sh.p(2.0), bc[1]), "CAMERA", height=sh.p(TEXT_SMALL), tag="side:label:camera")
        lc = side(eye - fwd * (0.5 * v_img))
        sh.text((lc[0] + 0.5 * bd + sh.p(2.0), lc[1]), "LENS f %s F/%s" % (_fmt(f, 1), _fmt(lens["f_number"], 1)),
                height=sh.p(TEXT_SMALL), tag="side:label:lens")
        for li, rec in enumerate(light_rec):
            _light_dims(sh, rec, li, ymin_all)
    if view in ("top", "both"):
        xs = corners[:, 0]
        ys = corners[:, 1]
        fov_w = xs.max() - xs.min()
        fov_h = ys.max() - ys.min()
        sh.dim((ys.min(), xs.min() + top_off), (ys.max(), xs.min() + top_off), -(sh.p(10.0) + (xs.min()
                                                                                              - extent[:, 0].min())),
               "FOV " + _fmt(fov_h), "FOV_top_y", fov_h)
        sh.dim((ys.max(), xs.min() + top_off), (ys.max(), xs.max() + top_off), -(sh.p(10.0) + extent[:, 1].max()
                                                                               - ys.max()),
               "FOV " + _fmt(fov_w), "FOV_top_x", fov_w)
        sh.text((ymin_all, extent[:, 0].min() + top_off - sh.p(24.0)), "TOP VIEW (Y-X)", height=sh.p(TEXT_SMALL),
                tag="top:label")
        # ★上面図は第三角法で側面図と横軸 y を共有するので、センサーの長辺(像の横 = 世界の x)は縦に描かれる。
        #   向きを取り違えないよう、軸の矢印と名前を描く(+X が上)。
        sh.axes((ymin_all - sh.p(20.0), extent[:, 0].min() + top_off - sh.p(20.0)), ("+Y", "+X"))
    # 諸元
    th = sh.p(TEXT_SMALL)
    yy = z_lo - sh.p(44.0)
    lines = ["CAMERA  f %s  F/%s  WD %s  SENSOR %dx%d  PIXEL %.2f um" % (_fmt(f), _fmt(lens["f_number"]), _fmt(wd), w, h,
                                                                       1000.0 * cam["pixel_mm"]),
             "m %.4f  N_w %s  AIRY(obj) %.1f um  PIXEL(obj) %.1f um  LIMIT %.1f um (%s)  DOF %s"
             % (budget["magnification"], _fmt(budget["f_number_working"]), budget["airy_object_um"],
                budget["pixel_object_um"], budget["limit_um"], budget["limited_by"], _fmt(dof, 3))]
    for rec in light_rec:
        lines.append("LIGHT %d  %s  R %s  H %s%s" % (rec["index"] + 1, rec["kind"].upper(), _fmt(rec["radius_mm"]),
                                                     _fmt(rec["height_mm"]),
                                                     ("  ELEV %.1f° FROM WORK PLANE" % rec["elevation_deg"])
                                                     if rec.get("elevation_deg") is not None else ""))
    for k, ln in enumerate(lines):
        sh.text((ymin_all, yy - 1.7 * th * k), ln, height=th, tag="spec:%d" % k)
    values = {"working_distance": wd, "fov_mm": [float(np.ptp(corners[:, 0])), float(np.ptp(corners[:, 1]))],
              "dof_mm": dof, "magnification": budget["magnification"], "image_distance_mm": v_img,
              "fov_corners": corners.tolist(), "eye": eye.tolist(), "look_at": look.tolist(),
              "lights": [{k: v for k, v in r.items() if k not in ("circles", "arcs")} for r in light_rec],
              "top_view_offset": top_off, "scale": s}
    meta = {"source": "optscene.vision_layout", "side_view": "(y, z)", "top_view": "(y, x + top_view_offset)",
            "projection": "third angle: TOP above SIDE, sharing the Y axis"}
    title_lines = [title or "VISION SETUP", "UNITS mm   SCALE " + _scale_label(s) + "   THIRD ANGLE PROJECTION"]
    return _finish(sh, title or "vision_setup", values, meta, title_lines)


def _scene_segments(obj, segs, layer):
    k = obj.get("kind")
    if k == "box":
        c = np.asarray(obj["c"], float)
        hh = np.asarray(obj["h"], float)
        for p, q in _box_edges(c, (np.eye(3)[0], np.eye(3)[1], np.eye(3)[2]), hh):
            segs.append((p, q, layer, "part"))
    elif k == "cylinder":
        c = np.asarray(obj["c"], float)
        r, hz = float(obj["r"]), float(obj["hz"])
        n = 48
        for zz in (c[2] - hz, c[2] + hz):
            for i in range(n):
                a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
                segs.append((np.array([c[0] + r * math.cos(a0), c[1] + r * math.sin(a0), zz]),
                             np.array([c[0] + r * math.cos(a1), c[1] + r * math.sin(a1), zz]), layer, "part"))
        for sx, sy in ((r, 0.0), (-r, 0.0), (0.0, r), (0.0, -r)):
            segs.append((np.array([c[0] + sx, c[1] + sy, c[2] - hz]), np.array([c[0] + sx, c[1] + sy, c[2] + hz]),
                         layer, "part"))
    elif k == "sphere":
        c = np.asarray(obj["c"], float)
        r = float(obj["r"])
        n = 64
        for plane in range(3):
            for i in range(n):
                a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
                p = np.zeros(3); q = np.zeros(3)
                ax = [(0, 1), (0, 2), (1, 2)][plane]
                p[ax[0]], p[ax[1]] = r * math.cos(a0), r * math.sin(a0)
                q[ax[0]], q[ax[1]] = r * math.cos(a1), r * math.sin(a1)
                segs.append((c + p, c + q, layer, "part"))
    elif k == "plane":
        hh = obj.get("half")
        if hh is not None:
            hh = np.atleast_1d(np.asarray(hh, float))
            hx, hy = (float(hh[0]), float(hh[-1]))
            z = float(obj["z"])
            q4 = [np.array([a * hx, b * hy, z]) for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
            for i in range(4):
                segs.append((q4[i], q4[(i + 1) % 4], layer, "part"))
    elif k == "difference":
        _scene_segments(obj["solid"], segs, layer)
        _scene_segments(obj["cavity"], segs, "HIDDEN")


def _light_segments(L, index, segs):
    """照明 1 つを 3-D の線分(両方の図に出す物)と、図ごとの円・円弧に。"""
    kind = L.get("kind")
    E = np.asarray(L["emitters"], float)
    Dd = np.asarray(L["directions"], float)
    R = float(L.get("radius_mm", 0.0))
    H = float(L.get("height_mm", 0.0))
    size = float(L.get("size_mm", 0.25 * R if R else 10.0))
    rec = {"index": index, "kind": kind, "radius_mm": R, "height_mm": H, "circles": [], "arcs": [],
           "elevation_deg": None, "size_mm": size}
    tag = "light%d" % index
    if kind == "ring":
        rec["elevation_deg"] = math.degrees(math.atan2(H, R))
        tw = 0.5 * size
        for sg in (1.0, -1.0):                          # 側面図: 断面の 2 つの四角
            c = np.array([0.0, sg * R, H])
            q4 = [c + np.array([0.0, a * tw, b * 0.5 * tw]) for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
            for i in range(4):
                segs.append((q4[i], q4[(i + 1) % 4], "LIGHT", "light_side:" + tag))
            tip = c + 0.8 * (np.array([0.0, 0.0, 0.0]) - c)
            segs.append((c, tip, "LIGHTRAY", "light_side:ray:" + tag))
        for rr in (R - 0.5 * tw, R + 0.5 * tw):
            rec["circles"].append({"view": "TOP", "center": np.array([0.0, 0.0, H]), "r": rr, "layer": "LIGHT",
                                   "tag": tag})
    elif kind == "dome":
        rec["elevation_deg"] = None
        rec["circles"].append({"view": "TOP", "center": np.array([0.0, 0.0, 0.0]), "r": R, "layer": "LIGHT",
                               "tag": tag})
        rec["circles"].append({"view": "TOP", "center": np.array([0.0, 0.0, 0.0]), "r": R * math.sin(math.radians(20.0)),
                               "layer": "LIGHT", "tag": tag + ":aperture"})
        # 側面図: 半球の断面(天頂 20°〜85° = 仰角 5°〜70°、左右)
        rec["arcs"].append({"view": "SIDE", "center": np.array([0.0, 0.0, 0.0]), "r": R, "a0": 5.0, "a1": 70.0,
                            "layer": "LIGHT", "tag": tag})
        rec["arcs"].append({"view": "SIDE", "center": np.array([0.0, 0.0, 0.0]), "r": R, "a0": 110.0, "a1": 175.0,
                            "layer": "LIGHT", "tag": tag})
        for el in (20.0, 45.0, 135.0, 160.0):
            c = np.array([0.0, R * math.cos(math.radians(el)), R * math.sin(math.radians(el))])
            segs.append((c, 0.3 * c, "LIGHTRAY", "light_side:ray:" + tag))
        rec["height_mm"] = R
    elif kind == "bar":
        rec["elevation_deg"] = math.degrees(math.atan2(H, R))
        x0, x1 = float(E[:, 0].min()), float(E[:, 0].max())
        rec["length_mm"] = x1 - x0
        tw = 0.5 * size
        q4 = [np.array([x, R + a * 0.5 * tw, H + b * 0.5 * tw]) for (x, a, b) in
              ((x0, -1, -1), (x1, -1, -1), (x1, 1, -1), (x0, 1, -1))]
        q4t = [np.array([x, R + a * 0.5 * tw, H]) for (x, a) in ((x0, -1), (x1, -1), (x1, 1), (x0, 1))]
        for i in range(4):
            segs.append((q4t[i], q4t[(i + 1) % 4], "LIGHT", "light_top:" + tag))
        c = np.array([0.0, R, H])
        qs = [c + np.array([0.0, a * 0.5 * tw, b * 0.5 * tw]) for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        for i in range(4):
            segs.append((qs[i], qs[(i + 1) % 4], "LIGHT", "light_side:" + tag))
        segs.append((c, 0.2 * c, "LIGHTRAY", "light_side:ray:" + tag))
        del q4
    elif kind == "coaxial":
        # 等価な面光源(円板)は破線、器具はハーフミラーの箱 + 横の光源
        segs.append((np.array([0.0, -R, H]), np.array([0.0, R, H]), "HIDDEN", "light_side:" + tag + ":disc"))
        rec["circles"].append({"view": "TOP", "center": np.array([0.0, 0.0, H]), "r": R, "layer": "HIDDEN",
                               "tag": tag + ":disc"})
        b = 0.5 * size
        c = np.array([0.0, 0.0, H])
        q4 = [c + np.array([0.0, a * b, d * b]) for a, d in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        for i in range(4):
            segs.append((q4[i], q4[(i + 1) % 4], "LIGHT", "light_side:" + tag + ":splitter"))
        segs.append((c + np.array([0.0, -b, -b]), c + np.array([0.0, b, b]), "LIGHT", "light_side:" + tag + ":mirror"))
        lamp = c + np.array([0.0, 2.2 * b, 0.0])
        l4 = [lamp + np.array([0.0, a * 0.4 * b, d * 0.8 * b]) for a, d in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        for i in range(4):
            segs.append((l4[i], l4[(i + 1) % 4], "LIGHT", "light_side:" + tag + ":lamp"))
        segs.append((lamp - np.array([0.0, 0.4 * b, 0.0]), c, "LIGHTRAY", "light_side:ray:" + tag))
        segs.append((c, c - np.array([0.0, 0.0, 0.8 * H]), "LIGHTRAY", "light_side:ray:" + tag))
        t4 = [c + np.array([a * b, d * b, 0.0]) for a, d in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        for i in range(4):
            segs.append((t4[i], t4[(i + 1) % 4], "LIGHT", "light_top:" + tag + ":splitter"))
    elif kind == "backlight":
        zz = -H
        q4 = [np.array([0.0, a * R, zz + d * 2.5]) for a, d in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        for i in range(4):
            segs.append((q4[i], q4[(i + 1) % 4], "LIGHT", "light_side:" + tag))
        for yy in np.linspace(-0.6 * R, 0.6 * R, 3):
            segs.append((np.array([0.0, yy, zz + 2.5]), np.array([0.0, yy, 0.7 * zz]), "LIGHTRAY",
                         "light_side:ray:" + tag))
        t4 = [np.array([a * R, d * R, zz]) for a, d in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        for i in range(4):
            segs.append((t4[i], t4[(i + 1) % 4], "HIDDEN", "light_top:" + tag))
    else:
        for e, d in zip(E[:: max(1, len(E) // 8)], Dd[:: max(1, len(E) // 8)]):
            segs.append((e, e + 10.0 * d, "LIGHTRAY", "light_side:ray:" + tag))
    return rec


def _light_dims(sh, rec, li, y_left):
    """照明の高さ・半径・仰角の寸法(側面図)。左側(y < 0)に照明ごとに段をずらして置き、右側は WD と DOF に空ける。

    仰角は**作業面から測った**角(atan(H/R))。暗視野/明視野の境の数字は資料によって基準(面からか光軸からか)が
    違うので、図には角の基準も書く(諸元の行)。
    """
    kind = rec["kind"]
    R, H = rec["radius_mm"], rec["height_mm"]
    name = "L%d" % (li + 1)
    step = sh.p(9.0) * li
    if kind == "ring":
        sh.dim((-R, 0.0), (-R, H), (R - y_left) + sh.p(4.0) + step, "H " + _fmt(H), name + "_H", H)
        sh.dim((-R, H), (0.0, H), sh.p(10.0) + step, "%s RING R %s" % (name, _fmt(R)), name + "_R", R)
        el = rec["elevation_deg"]
        sh.angle_dim((0.0, 0.0), 0.8 * math.hypot(R, H), 180.0 - el, 180.0, "%.1f°" % el, name + "_ELEV", el)
    elif kind == "bar":
        tw = 0.25 * rec.get("size_mm", 0.0)
        sh.dim((R + tw, 0.0), (R + tw, H), -(sh.p(6.0) + step), "H " + _fmt(H), name + "_H", H)
        sh.dim((0.0, H), (R, H), sh.p(10.0) + step, "%s BAR R %s" % (name, _fmt(R)), name + "_R", R)
        el = rec["elevation_deg"]
        sh.angle_dim((0.0, 0.0), 0.8 * math.hypot(R, H), 0.0, el, "%.1f°" % el, name + "_ELEV", el)
    elif kind == "dome":
        a = math.radians(150.0)
        sh.dim((0.0, 0.0), (R * math.cos(a), R * math.sin(a)), -sh.p(6.0), "%s DOME R %s" % (name, _fmt(R)),
               name + "_R", R)
    elif kind == "coaxial":
        sh.dim((-R, H), (R, H), sh.p(10.0), "%s COAXIAL ⌀%s" % (name, _fmt(2.0 * R)), name + "_D", 2.0 * R)
        sh.dim((-R, 0.0), (-R, H), (R - y_left) + sh.p(4.0) + step, "H " + _fmt(H), name + "_H", H)
    elif kind == "backlight":
        sh.dim((-R, -H - 2.5), (R, -H - 2.5), -sh.p(8.0), "%s BACKLIGHT W %s" % (name, _fmt(2.0 * R)), name + "_W",
               2.0 * R)
        sh.dim((-R, -H), (-R, 0.0), (R - y_left) + sh.p(4.0) + step, "H " + _fmt(H), name + "_H", H)


# --------------------------------------------------------------------------- #
# 3. 単レンズの製作図(ISO 10110)
# --------------------------------------------------------------------------- #
def _element(system, element, op):
    surf = system["surfaces"]
    groups = []
    i = 0
    while i < len(surf):
        if _is_glass(surf[i]):
            j = i
            while j < len(surf) and _is_glass(surf[j]):
                j += 1
            groups.append(list(range(i, j + 1)))
            i = j + 1
        else:
            i += 1
    if not groups:
        raise ValueError("%s: the prescription has no glass element" % op)
    e = _int(element, "element", op, 0, len(groups) - 1)
    return groups[e]


def _sag_exact(R, y):
    return 0.0 if R == RT.INF else R - math.copysign(math.sqrt(R * R - y * y), R)


def lens_element_drawing(system, element=0, tolerances=None, outer_diameter_mm=None, clear_aperture_mm=None,
                         chamfer_mm=0.2, irregularity_fringes=None, surface_imperfections=None,
                         stress_birefringence=20.0, bubbles="1/3x0.16", inhomogeneity="2/1;1",
                         trials=200, seed=0, radius_tolerance="radius", plane_power_fringes=2.0, scale=None,
                         title=None):
    """単レンズの製作図(``table``、図の dict)—— ISO 10110 の表記で、断面図と 3 分割のデータ欄と表題欄。

    *system* の *element* 番目のガラス(前から 0, 1, …)を描く。データ欄は左が第 1 面、右が第 2 面、中央が材料:

    * 面: ``R``(曲率半径、凸は CX・凹は CC、平面は ∞)と公差、``⌀e``(有効径)、``3/A(B)``(面形状の公差:
      A = 曲率の誤差による sag の誤差、B = 不規則性、どちらも λ = 546.07 nm の干渉縞の本数。R の公差を寸法で
      書くときは A を ``-`` にする —— ISO 10110-5 の慣行)、``4/σ``(面の傾き = 偏心の公差、分)、``5/N×A``
      (表面のきず)。
    * 材料: ``n_d`` と ``ν_d``(式で評価した値。社名の硝材名は書かない)と公差、``0/``(応力複屈折 nm/cm)、
      ``1/``(泡と異物)、``2/``(不均質と脈理)。
    * 図: 中心厚と公差、外径と公差、面取り(保護面取り)、光軸。

    公差は ``raytrace.tolerance_analysis`` の公差の辞書(*tolerances*、既定は同じ既定値 ``radius_pct`` 0.5 /
    ``thickness_mm`` 0.05 / ``index`` 0.001 / ``tilt_deg`` 0.05)から写す: 中心厚 ±``thickness_mm``、``n_d``
    ±``index``、``4/`` = ``tilt_deg`` × 60 分、曲率の公差 ``radius_pct`` は R の ± と、有効径の縁での sag の差
    ``|sag(R(1 ± p)) − sag(R)|`` を縞の本数(1 本 = λ/2)にする。*radius_tolerance* = ``"radius"``(既定)は
    R の欄に ±ΔR を書いて ``3/-(B)`` とし、縞の換算は注記に残す。``"fringes"`` は R を公称値だけにして
    ``3/A(B)`` の A に縞の本数を書く。B(不規則性、*irregularity_fringes*)の既定は ``"radius"`` で 1、
    ``"fringes"`` で A/4(最低 0.5)。平面は曲率の公差が無いので、A は *plane_power_fringes*(既定 2 本)。同じ公差で ``tolerance_analysis`` を回した EFL の 5〜95 % の幅を注記に入れる(*trials* 回、
    *seed*)—— 図の公差が光学系の何を動かすかを製作図に残すため。

    返り値の ``values``: ``R1`` / ``R2`` / ``center_thickness`` / ``outer_diameter`` / ``clear_aperture`` /
    ``nd`` / ``vd`` / ``fringes_power`` / ``tilt_arcmin`` / ``efl`` / ``efl_p5`` / ``efl_p95``。平面の ``R`` と、分散の
    無い媒質の ``vd`` は ``inf``(非有限は契約、``lens_system`` の規約どおり)。
    接合レンズ群(面が 3 つ以上のガラスの連続)は 1 枚の組図にする: 断面に各レンズと接合面、データ欄は面ごとの R・
    有効径と、レンズごとの材料(n_d・ν_d)と中心厚(``values`` の ``R`` / ``center_thickness`` / ``nd`` / ``vd`` は
    列)。非球面・円錐面は ISO 10110-12 の sag の表(高さ h と sag z(h)、式と係数)を図に足し、``values`` の
    ``sag_tables`` に同じ数を残す(門は図から読み戻して ``raytrace`` の sag の式と突き合わせる)。
    """
    op = "lens_element_drawing"
    _system(system, op)
    grp = _element(system, element, op)
    if len(grp) > 2:
        return _cemented_drawing(system, grp, element, tolerances, outer_diameter_mm, clear_aperture_mm,
                                 chamfer_mm, scale, title, op)
    a, b = grp
    surf = system["surfaces"]
    s1, s2 = surf[a], surf[b]
    tol = {"radius_pct": 0.5, "thickness_mm": 0.05, "index": 0.001, "decenter_mm": 0.0, "tilt_deg": 0.05}
    if tolerances is not None:
        if not isinstance(tolerances, dict):
            raise ValueError("%s: tolerances must be a dict like tolerance_analysis takes" % op)
        for k, v in tolerances.items():
            if k not in tol:
                raise ValueError("%s: unknown tolerance %r (choose from %s)" % (op, k, sorted(tol)))
            tol[k] = _num(v, k, op, nonneg=True)
    ch = _num(chamfer_mm, "chamfer_mm", op, nonneg=True)
    trials = _int(trials, "trials", op, 1, 100000)
    ct = float(s1["t"])
    # 有効径と外径
    if clear_aperture_mm is None:
        aps = [s["ap"] for s in (s1, s2) if s["ap"] is not None]
        if not aps:
            sec = lens_section_drawing(system, rays=3)
            ce = 2.0 * max(sec["values"]["surfaces"][a]["semi_diameter"], sec["values"]["surfaces"][b]["semi_diameter"])
        else:
            ce = 2.0 * max(aps)
    else:
        ce = _num(clear_aperture_mm, "clear_aperture_mm", op, positive=True)
    D = 1.1 * ce if outer_diameter_mm is None else _num(outer_diameter_mm, "outer_diameter_mm", op, positive=True)
    if D < ce:
        raise ValueError("%s: outer diameter %.4g is smaller than the clear aperture %.4g" % (op, D, ce))
    for s in (s1, s2):
        _check_extent(s, 0.5 * D, op)
    sag1 = _zs(s1, 0.5 * D)
    sag2 = _zs(s2, 0.5 * D)
    edge = ct + sag2 - sag1
    if edge <= 0.0:
        raise ValueError("%s: the edge thickness %.4g mm is not positive at the outer diameter %.4g" % (op, edge, D))
    nd, vd = _nd_vd(s1["n"])
    # 3/ の A: 曲率の公差 → 有効径の縁での sag の差 → 縞(1 本 = λ/2)
    lam_mm = FRINGE_WL_UM * 1e-3

    ppf = _num(plane_power_fringes, "plane_power_fringes", op, nonneg=True)

    def fringes(R):
        if R == RT.INF:
            return ppf
        if tol["radius_pct"] == 0.0:
            return 0.0
        y = 0.5 * ce
        d = max(abs(_sag_exact(R * (1 + tol["radius_pct"] / 100.0), y) - _sag_exact(R, y)),
                abs(_sag_exact(R * (1 - tol["radius_pct"] / 100.0), y) - _sag_exact(R, y)))
        return d / (0.5 * lam_mm)
    fr = [fringes(s1["R"]), fringes(s2["R"])]
    if radius_tolerance not in ("radius", "fringes"):
        raise ValueError("%s: radius_tolerance must be 'radius' or 'fringes', got %r" % (op, radius_tolerance))
    if irregularity_fringes is None:
        irr = ([1.0, 1.0] if radius_tolerance == "radius"
               else [max(0.5, round(0.25 * f * 2) / 2) for f in fr])
    else:
        irr = [_num(irregularity_fringes, "irregularity_fringes", op, nonneg=True)] * 2
    tilt_min = tol["tilt_deg"] * 60.0
    si = "5/3x0.16" if surface_imperfections is None else str(surface_imperfections)
    sb = _num(stress_birefringence, "stress_birefringence", op, nonneg=True)
    for lab, val in (("bubbles", bubbles), ("inhomogeneity", inhomogeneity), ("surface_imperfections", si)):
        if not isinstance(val, str) or not re.fullmatch(r"[0-9/x;.,() ]{1,40}", val):
            raise ValueError("%s: %s must be an ISO 10110 code like '1/3x0.16', got %r" % (op, lab, val))
    # 同じ公差の Monte-Carlo(単レンズだけを空気中で)
    single = RT.lens_system([{"R": s1["R"], "t": ct, "n": s1["n"], "ap": 0.5 * ce},
                             {"R": s2["R"], "t": None, "n": 1.0}], stop=0,
                            wavelength_um=system["wavelength_um"])
    mc = RT.tolerance_analysis(single, tolerances={k: v for k, v in tol.items()}, trials=trials, seed=seed)
    efl = RT.paraxial_trace(single)["efl"]
    # --- 図 ---
    span = max(D, ct + abs(sag1) + abs(sag2))
    s = _auto_scale(span, 110.0) if scale is None else _num(scale, "scale", op, positive=True)
    sh = _Sheet(s)
    y = np.linspace(-0.5 * D + ch, 0.5 * D - ch, 161)
    z1 = np.array([_zs(s1, v) for v in y])
    z2 = ct + np.array([_zs(s2, v) for v in y])
    sh.poly(np.stack([z1, y], 1), "OUTLINE", tag="surface:1")
    sh.poly(np.stack([z2, y], 1), "OUTLINE", tag="surface:2")
    # 面取りと外周
    for sg in (1.0, -1.0):
        e1 = (_zs(s1, 0.5 * D - ch), sg * (0.5 * D - ch))
        e2 = (ct + _zs(s2, 0.5 * D - ch), sg * (0.5 * D - ch))
        c1 = (sag1 + ch, sg * 0.5 * D)
        c2 = (ct + sag2 - ch, sg * 0.5 * D)
        sh.line(e1, c1, "OUTLINE", tag="chamfer")
        sh.line(e2, c2, "OUTLINE", tag="chamfer")
        sh.line(c1, c2, "OUTLINE", tag="edge")
    zmin, zmax = min(0.0, sag1) - sh.p(8.0), max(ct, ct + sag2) + sh.p(8.0)
    sh.line((zmin, 0.0), (zmax, 0.0), "AXIS", tag="axis")
    sh.dim((0.0, 0.0), (ct, 0.0), -(0.5 * D + sh.p(10.0)), "%s±%s" % (_fmt(ct), _fmt(tol["thickness_mm"])), "CT", ct)
    sh.dim((zmax + sh.p(4.0), -0.5 * D), (zmax + sh.p(4.0), 0.5 * D), -sh.p(4.0),
           "⌀%s" % _fmt(D), "D", D)
    for sg, (zz, lab) in zip((1.0, -1.0), ((sag1, "1"), (ct + sag2, "2"))):
        pass
    sh.text(((sag1) - sh.p(6.0), 0.5 * D + sh.p(4.0)), "1", height=sh.p(TEXT_H), align="center", tag="label:surface")
    sh.text(((ct + sag2) + sh.p(6.0), 0.5 * D + sh.p(4.0)), "2", height=sh.p(TEXT_H), align="center",
            tag="label:surface")
    # --- データ欄(紙の座標で組み、実物の mm に直す) ---
    th = sh.p(TEXT_SMALL)
    y0 = -0.5 * D - sh.p(26.0)
    col = sh.p(62.0)
    x0 = min(0.0, sag1) - sh.p(55.0)

    def rspec(R, side):
        sf = s1 if side == 1 else s2
        if _is_asph(sf):
            return "R %.3f %s  ASPH (12/)" % (abs(R), "CX" if ((R > 0) if side == 1 else (R < 0)) else "CC")
        if R == RT.INF:
            return "R ∞"
        convex = (R > 0) if side == 1 else (R < 0)
        if radius_tolerance == "fringes":
            return "R %.3f %s" % (abs(R), "CX" if convex else "CC")
        return "R %.3f %s  ±%.3f" % (abs(R), "CX" if convex else "CC", abs(R) * tol["radius_pct"] / 100.0)

    def form(k, R):
        a = "-" if (radius_tolerance == "radius" and R != RT.INF) else _fringe(fr[k])
        return "3/%s(%s)" % (a, _fringe(irr[k]))
    left = ["LEFT SURFACE", rspec(s1["R"], 1), "⌀e %s" % _fmt(ce), form(0, s1["R"]),
            "4/%s'" % _fringe(tilt_min), si, "6/ -"]
    right = ["RIGHT SURFACE", rspec(s2["R"], 2), "⌀e %s" % _fmt(ce), form(1, s2["R"]),
             "4/%s'" % _fringe(tilt_min), si, "6/ -"]
    vds = ("%.2f" % vd) if math.isfinite(vd) else "-"
    mid = ["MATERIAL SPECIFICATION", "n_d %.5f ±%.4f" % (nd, tol["index"]), "v_d %s ±0.8%%" % vds,
           "0/%g" % sb, bubbles, inhomogeneity]
    rows = max(len(left), len(mid), len(right))
    hrow = 1.8 * th
    for ci, colv in enumerate((left, mid, right)):
        cx = x0 + ci * col
        sh.poly([(cx, y0 + hrow), (cx + col, y0 + hrow), (cx + col, y0 - hrow * (rows - 0.4)),
                 (cx, y0 - hrow * (rows - 0.4))], "THIN", closed=True, tag="table")
        for k, txt in enumerate(colv):
            sh.text((cx + sh.p(2.0), y0 - hrow * k), txt, height=th,
                    tag="iso:%s:%d" % (("left", "material", "right")[ci], k))
    # 注記と表題欄
    ny = y0 - hrow * (rows + 1.0)
    notes = ["NOTES", "1. PROTECTIVE CHAMFER %s x 45° MAX" % _fmt(ch),
             "2. EDGE THICKNESS %s (REFERENCE)" % _fmt(edge),
             "3. EFL %s (d-line, paraxial)  MC %d trials: p5 %s / p95 %s" % (_fmt(efl, 3), trials,
                                                                            _fmt(mc["efl"]["p5"], 3),
                                                                            _fmt(mc["efl"]["p95"], 3)),
             "4. TOLERANCES FROM tolerance_analysis: R ±%g %%, CT ±%g, n ±%g, TILT ±%g°"
             % (tol["radius_pct"], tol["thickness_mm"], tol["index"], tol["tilt_deg"]),
             "5. 3/ IN FRINGES AT 546.07 nm" + "".join(
                 "; R%d ±%g %% = %s FRINGES OF SAGITTA OVER ⌀e" % (k + 1, tol["radius_pct"], _fringe(fr[k]))
                 for k, ss in enumerate((s1, s2)) if ss["R"] != RT.INF)]
    for k, txt in enumerate(notes):
        sh.text((x0, ny - hrow * k), txt, height=th, tag="note:%d" % k)
    tb = ny - hrow * (len(notes) + 1.0)
    sag_tables = {}
    for side, sf in ((1, s1), (2, s2)):
        if not _is_asph(sf):
            continue
        tab = _sag_table(sf, 0.5 * ce)
        sag_tables[side] = tab
        tb = _draw_sag_table(sh, x0, tb, side, sf, tab, hrow, th)
    sh.poly([(x0, tb), (x0 + 3 * col, tb), (x0 + 3 * col, tb - 3.2 * hrow), (x0, tb - 3.2 * hrow)], "FRAME",
            closed=True, tag="titleblock")
    sh.text((x0 + sh.p(2.0), tb - hrow), title or "LENS ELEMENT %d" % (element + 1), height=sh.p(TEXT_H),
            tag="titleblock:name")
    sh.text((x0 + sh.p(2.0), tb - 2.4 * hrow), "ISO 10110   UNITS mm   SCALE %s   SHEET 1/1" % _scale_label(s),
            height=th, tag="titleblock:info")
    values = {"R1": s1["R"], "R2": s2["R"], "center_thickness": ct, "outer_diameter": D, "clear_aperture": ce,
              "nd": nd, "vd": vd, "fringes_power": fr, "irregularity": irr, "tilt_arcmin": tilt_min,
              "edge_thickness": edge, "efl": efl, "efl_p5": mc["efl"]["p5"], "efl_p95": mc["efl"]["p95"],
              "tolerances": tol, "chamfer": ch, "scale": s, "surfaces": [a, b], "radius_tolerance": radius_tolerance,
              "sag_tables": sag_tables}
    meta = {"standard": "ISO 10110 (notation from public explanations; the standard text is not reproduced)",
            "fringe_wavelength_um": FRINGE_WL_UM}
    return _finish(sh, title or "lens_element", values, meta, [])


#: ISO 10110-12 の sag の表の行数(高さ 0 から有効半径まで等間隔、両端を含む)。
SAG_TABLE_ROWS = 11


def _is_asph(sf):
    return sf["R"] != RT.INF and (sf["k"] != 0.0 or bool(sf["asph"])) or (sf["R"] == RT.INF and bool(sf["asph"]))


def _zs(sf, y):
    """面の sag(球面は閉形式 R − sign(R)√(R² − y²)、円錐・非球面は raytrace の式)。"""
    if _is_asph(sf):
        return float(_sag_profile(sf, [y])[0])
    return _sag_exact(sf["R"], y)


def _check_extent(sf, h, op):
    if sf["R"] == RT.INF:
        return
    if not _is_asph(sf) and abs(sf["R"]) < h:
        raise ValueError("%s: |R| = %.4g is smaller than the half diameter %.4g" % (op, abs(sf["R"]), h))
    if _is_asph(sf) and sf["k"] > -1.0 and (1.0 + sf["k"]) * (h / sf["R"]) ** 2 >= 1.0:
        raise ValueError("%s: the conic (R %.4g, k %.4g) does not reach the half diameter %.4g"
                         % (op, sf["R"], sf["k"], h))


def _sag_table(sf, h_max, rows=None):
    """ISO 10110-12 の sag の表: 高さ h(0 → 有効半径、等間隔)と sag z(h) [mm]。"""
    n = SAG_TABLE_ROWS if rows is None else rows
    hs = np.linspace(0.0, h_max, n)
    return [[float(h), float(_sag_profile(sf, [h])[0])] for h in hs]


def _draw_sag_table(sh, x0, top, side, sf, tab, hrow, th):
    """sag の表を図に書き、次の欄の上端を返す。式と係数(ASCII)を表の上に書く。"""
    coef = "  ".join("A%d %.6e" % (4 + 2 * i, a) for i, a in enumerate(sf["asph"])) or "A4.. 0"
    lines = ["12/ SURFACE %d ASPHERIC SAG TABLE (ISO 10110-12)" % side,
             "z = c h^2/(1+SQRT(1-(1+k) c^2 h^2)) + A4 h^4 + A6 h^6 + ...",
             "R %.6f  k %.6f  %s" % (sf["R"], sf["k"], coef),
             "     h [mm]       z [mm]"]
    y = top - hrow
    for k, txt in enumerate(lines):
        sh.text((x0, y - hrow * k), txt, height=th, tag="sagtab:%d:head:%d" % (side, k))
    y -= hrow * len(lines)
    for k, (h, z) in enumerate(tab):
        sh.text((x0, y - hrow * k), "%11.4f %12.6f" % (h, z), height=th, tag="sagtab:%d:%d" % (side, k))
    return y - hrow * (len(tab) + 1.0)


def _cemented_drawing(system, grp, element, tolerances, outer_diameter_mm, clear_aperture_mm, chamfer_mm,
                      scale, title, op):
    """接合レンズ群の組図(断面・接合面・面ごとの R と有効径・レンズごとの材料と中心厚・sag の表)。"""
    surf = system["surfaces"]
    tol = {"radius_pct": 0.5, "thickness_mm": 0.05, "index": 0.001, "decenter_mm": 0.0, "tilt_deg": 0.05}
    if tolerances is not None:
        if not isinstance(tolerances, dict):
            raise ValueError("%s: tolerances must be a dict like tolerance_analysis takes" % op)
        for k, v in tolerances.items():
            if k not in tol:
                raise ValueError("%s: unknown tolerance %r (choose from %s)" % (op, k, sorted(tol)))
            tol[k] = _num(v, k, op, nonneg=True)
    ch = _num(chamfer_mm, "chamfer_mm", op, nonneg=True)
    if clear_aperture_mm is None:
        aps = [surf[i]["ap"] for i in grp if surf[i]["ap"] is not None]
        if aps:
            ce = 2.0 * max(aps)
        else:
            sec = lens_section_drawing(system, rays=3)
            ce = 2.0 * max(sec["values"]["surfaces"][i]["semi_diameter"] for i in grp)
    else:
        ce = _num(clear_aperture_mm, "clear_aperture_mm", op, positive=True)
    D = 1.1 * ce if outer_diameter_mm is None else _num(outer_diameter_mm, "outer_diameter_mm", op, positive=True)
    if D < ce:
        raise ValueError("%s: outer diameter %.4g is smaller than the clear aperture %.4g" % (op, D, ce))
    for i in grp:
        _check_extent(surf[i], 0.5 * D, op)
    zv = [0.0]
    for i in grp[:-1]:
        zv.append(zv[-1] + float(surf[i]["t"]))
    cts = [float(surf[i]["t"]) for i in grp[:-1]]
    edges = []
    for k in range(len(grp) - 1):
        e = (zv[k + 1] + _zs(surf[grp[k + 1]], 0.5 * D)) - (zv[k] + _zs(surf[grp[k]], 0.5 * D))
        if e <= 0.0:
            raise ValueError("%s: lens %d of the group has a non-positive edge thickness %.4g mm at the outer "
                             "diameter %.4g" % (op, k + 1, e, D))
        edges.append(e)
    span = max(D, zv[-1] + abs(_zs(surf[grp[0]], 0.5 * D)) + abs(_zs(surf[grp[-1]], 0.5 * D)))
    s = _auto_scale(span, 110.0) if scale is None else _num(scale, "scale", op, positive=True)
    sh = _Sheet(s)
    y = np.linspace(-0.5 * D + ch, 0.5 * D - ch, 161)
    for k, i in enumerate(grp):
        z = zv[k] + np.array([_zs(surf[i], v) for v in y])
        sh.poly(np.stack([z, y], 1), "OUTLINE", tag="surface:%d" % (k + 1))
        if 0 < k < len(grp) - 1:                       # 接合面は外径まで(面取りしない)
            for sg in (1.0, -1.0):
                sh.line((z[-1 if sg > 0 else 0], sg * (0.5 * D - ch)),
                        (zv[k] + _zs(surf[i], 0.5 * D), sg * 0.5 * D), "OUTLINE", tag="cement")
    for k in range(len(grp) - 1):
        a, b = grp[k], grp[k + 1]
        for sg in (1.0, -1.0):
            za = zv[k] + _zs(surf[a], 0.5 * D - (ch if k == 0 else 0.0))
            zb = zv[k + 1] + _zs(surf[b], 0.5 * D - (ch if k + 1 == len(grp) - 1 else 0.0))
            ca = zv[k] + _zs(surf[a], 0.5 * D) + (ch if k == 0 else 0.0)
            cb = zv[k + 1] + _zs(surf[b], 0.5 * D) - (ch if k + 1 == len(grp) - 1 else 0.0)
            if k == 0:
                sh.line((za, sg * (0.5 * D - ch)), (ca, sg * 0.5 * D), "OUTLINE", tag="chamfer")
            if k + 1 == len(grp) - 1:
                sh.line((zb, sg * (0.5 * D - ch)), (cb, sg * 0.5 * D), "OUTLINE", tag="chamfer")
            sh.line((ca, sg * 0.5 * D), (cb, sg * 0.5 * D), "OUTLINE", tag="edge")
    zmin = min(0.0, _zs(surf[grp[0]], 0.5 * D)) - sh.p(8.0)
    zmax = max(zv[-1], zv[-1] + _zs(surf[grp[-1]], 0.5 * D)) + sh.p(8.0)
    sh.line((zmin, 0.0), (zmax, 0.0), "AXIS", tag="axis")
    for k, ct in enumerate(cts):
        sh.dim((zv[k], 0.0), (zv[k + 1], 0.0), -(0.5 * D + sh.p(10.0 + 9.0 * (k % 2))),
               "%s±%s" % (_fmt(ct), _fmt(tol["thickness_mm"])), "CT%d" % (k + 1), ct)
    sh.dim((zmax + sh.p(4.0), -0.5 * D), (zmax + sh.p(4.0), 0.5 * D), -sh.p(4.0), "⌀%s" % _fmt(D), "D", D)
    for k in range(len(grp)):
        sh.text((zv[k], 0.5 * D + sh.p(4.0)), "%d" % (k + 1), height=sh.p(TEXT_H), align="center",
                tag="label:surface")
    th = sh.p(TEXT_SMALL)
    hrow = 1.8 * th
    x0 = zmin - sh.p(40.0)
    y0 = -0.5 * D - sh.p(32.0)
    rows = ["CEMENTED GROUP (ISO 10110 ASSEMBLY)", "SURF        R            ⌀e"]
    Rs, nds, vds = [], [], []
    for k, i in enumerate(grp):
        R = surf[i]["R"]
        Rs.append(R)
        rows.append("%-4d %12s %10s%s" % (k + 1, "INF" if R == RT.INF else "%.4f" % R, _fmt(ce),
                                          "  ASPH (12/)" if _is_asph(surf[i]) else ""))
    rows.append("LENS     n_d        v_d       CT")
    for k, i in enumerate(grp[:-1]):
        nd, vd = _nd_vd(surf[i]["n"])
        nds.append(nd)
        vds.append(vd)
        rows.append("%-4d %10.5f %9s %9s" % (k + 1, nd, ("%.2f" % vd) if math.isfinite(vd) else "-",
                                             _fmt(cts[k])))
    for k, txt in enumerate(rows):
        sh.text((x0, y0 - hrow * k), txt, height=th, tag="cemented:%d" % k)
    sub = RT.lens_system([{"R": surf[i]["R"], "t": surf[i]["t"], "n": surf[i]["n"], "k": surf[i]["k"],
                           "asph": surf[i]["asph"], "ap": 0.5 * ce if k == 0 else None}
                          for k, i in enumerate(grp[:-1])] +
                         [{"R": surf[grp[-1]]["R"], "t": None, "n": 1.0, "k": surf[grp[-1]]["k"],
                           "asph": surf[grp[-1]]["asph"]}], stop=0, wavelength_um=system["wavelength_um"])
    efl = RT.paraxial_trace(sub)["efl"]
    ny = y0 - hrow * (len(rows) + 1.0)
    notes = ["NOTES", "1. CEMENT LAYER THICKNESS NEGLECTED (OPTICALLY THIN)",
             "2. EDGE THICKNESS " + " / ".join(_fmt(e) for e in edges) + " (REFERENCE)",
             "3. GROUP EFL %s (d-line, paraxial)" % _fmt(efl, 3),
             "4. TOLERANCES: CT ±%g, n ±%g, R ±%g %%" % (tol["thickness_mm"], tol["index"], tol["radius_pct"])]
    for k, txt in enumerate(notes):
        sh.text((x0, ny - hrow * k), txt, height=th, tag="note:%d" % k)
    tb = ny - hrow * (len(notes) + 1.0)
    sag_tables = {}
    for k, i in enumerate(grp):
        if _is_asph(surf[i]):
            tab = _sag_table(surf[i], 0.5 * ce)
            sag_tables[k + 1] = tab
            tb = _draw_sag_table(sh, x0, tb, k + 1, surf[i], tab, hrow, th)
    sh.poly([(x0, tb), (x0 + sh.p(186.0), tb), (x0 + sh.p(186.0), tb - 3.2 * hrow), (x0, tb - 3.2 * hrow)],
            "FRAME", closed=True, tag="titleblock")
    sh.text((x0 + sh.p(2.0), tb - hrow), title or "CEMENTED GROUP %d" % (element + 1), height=sh.p(TEXT_H),
            tag="titleblock:name")
    sh.text((x0 + sh.p(2.0), tb - 2.4 * hrow), "ISO 10110   UNITS mm   SCALE %s   SHEET 1/1" % _scale_label(s),
            height=th, tag="titleblock:info")
    values = {"R": Rs, "center_thickness": cts, "nd": nds, "vd": vds, "outer_diameter": D, "clear_aperture": ce,
              "edge_thickness": edges, "efl": efl, "surfaces": list(grp), "cemented": True, "scale": s,
              "tolerances": tol, "sag_tables": sag_tables}
    meta = {"standard": "ISO 10110 (assembly of a cemented group; notation from public explanations)"}
    return _finish(sh, title or "cemented_group", values, meta, [])


def _ascii_label(txt, fallback):
    return txt if txt and all(32 <= ord(ch) < 127 for ch in txt) else fallback


def noncoaxial_drawing(system, fields=None, rays=3, view="yz", scale=None, title=None, profile_points=61,
                     rotate_deg=0, overlays=None):
    """折り返した系の断面図・設置図(``table``、図の dict)—— ``raytrace3d`` の系の面・鏡・半透鏡・像面・光線を、
    大域の座標で子午面に投影して描く。

    *system* は ``raytrace3d.noncoaxial_system`` の系(``raytrace.lens_system`` の処方も受ける)。*view* は投影面:
    ``"yz"``(横軸 = 大域の z、縦軸 = y。x 軸まわりの折り返しはこの面に載る)/ ``"zx"``(横軸 z、縦軸 x)。
    面は局所の子午面の sag 曲線(``raytrace`` の円錐 + 非球面の式)を大域へ写して投影し、ガラスの群はコバの線で
    閉じ、鏡は裏に斜線、半透鏡は ``BS`` の印。光軸は座標系の原点の折れ線(細い一点鎖線)、絞りは口径の外の刻み、
    像面は像の座標系の線分(``image_tilt`` で傾く)、有限の物体は物面の線分(``object_tilt`` で傾く)。光線は視野
    ごとに色を分け、絞りの上で等間隔に**絞りを狙った**実光線(``raytrace3d`` の Newton 法)。

    *rotate_deg*(0 / 90 / 180 / 270)は紙の上で図を回す(同軸落射のように光が下から上へ進む装置を立てて描く)。
    *overlays* は別の系(例: 照明の枝 = 半透鏡で反射する系)の列で、その光線を照明の光線の層に重ねて描く
    (面は細線)。

    寸法: 装置の占有の幅 ``W`` と高さ ``H``(面・像面・光線の外接矩形)。注記: 光路長(第 1 面 → 像面の軸の長さ)、
    折り返しの角度。``values``: ``path_length`` / ``footprint`` / ``fold_angles_deg`` / 面ごとの大域の頂点
    ``surfaces`` / 光線の大域の折れ線 ``rays`` / ``image_center``。
    """
    op = "noncoaxial_drawing"
    import raytrace3d as R3
    sysd = R3._check(system, op)
    nr = _int(rays, "rays", op, 1, _MAX_RAYS)
    npf = _int(profile_points, "profile_points", op, 11, _MAX_PROFILE)
    if view not in ("yz", "zx"):
        raise ValueError("%s: view must be 'yz' or 'zx', got %r" % (op, view))
    if isinstance(rotate_deg, bool) or rotate_deg not in (0, 90, 180, 270):
        raise ValueError("%s: rotate_deg must be 0, 90, 180 or 270, got %r" % (op, rotate_deg))
    cr = {0: (1.0, 0.0), 90: (0.0, 1.0), 180: (-1.0, 0.0), 270: (0.0, -1.0)}[int(rotate_deg)]
    ovs = [] if overlays is None else [R3._check(o_, op) for o_ in overlays]
    if len(ovs) > 4:
        raise ValueError("%s: at most 4 overlays" % op)
    vi = 1 if view == "yz" else 0
    recs = sysd["records"]
    F0 = tuple(sysd["field"])
    if fields is None:
        fields = [(0.0, 0.0)] if F0 == (0.0, 0.0) else [(0.0, 0.0), (0.7 * F0[0], 0.7 * F0[1]), F0]
    if isinstance(fields, (int, float, np.integer, np.floating)) and not isinstance(fields, bool):
        fields = [fields]
    flds = []
    for i, f in enumerate(list(fields)):
        if isinstance(f, (int, float, np.integer, np.floating)) and not isinstance(f, bool):
            flds.append((0.0, _num(f, "fields[%d]" % i, op)))
        else:
            if not hasattr(f, "__len__") or len(f) != 2:
                raise ValueError("%s: a field is a number (fy) or a pair (fx, fy), got %r" % (op, f))
            flds.append((_num(f[0], "fields[%d][0]" % i, op), _num(f[1], "fields[%d][1]" % i, op)))
    if not 1 <= len(flds) <= _MAX_FIELDS:
        raise ValueError("%s: give 1..%d fields, got %d" % (op, _MAX_FIELDS, len(flds)))
    lay = R3._layout(sysd)
    path = R3._nominal_path(sysd)
    pos = {k: j for j, (k, _, _) in enumerate(path)}
    stop = sysd["stop"]
    ap_stop = recs[stop]["ap"]
    # --- 光線(描く束と、有効半径を決める密な束) ---
    q_draw = np.array([0.0]) if nr == 1 else np.linspace(-1.0, 1.0, nr)
    q_dense = np.linspace(-1.0, 1.0, 21)
    sd_ray = {k: 0.0 for k in pos}
    traced = []
    for f in flds:
        for qs, keep in ((q_dense, False), (q_draw, True)):
            tg = np.zeros((len(qs), 2))
            tg[:, 1 if view == "yz" else 0] = qs * ap_stop
            P, D, _, ok = R3._aim(sysd, tg, f, layout=lay)
            tr = R3._trace(sysd, P, D, layout=lay)
            v = tr["valid"] & ok
            if not keep:
                if not np.any(v):
                    raise ValueError("%s: no real ray of field %s reaches the image" % (op, f))
                for k, j in pos.items():
                    Rm, o = lay["poses"][k]
                    loc = (tr["points"][v, j + 1, :] - o) @ Rm
                    sd_ray[k] = max(sd_ray[k], float(np.max(np.hypot(loc[:, 0], loc[:, 1]))))
            else:
                traced.append((f, qs, tr, v))
    sd = {k: (recs[k]["ap"] if recs[k]["ap"] is not None else max(sd_ray[k], 1e-3)) for k in pos}
    before, after = R3._media(sysd)
    glass = {k: (not recs[k]["reflect"]) and after[k] > 1.0 + 1e-9 for k in pos}
    # 群(媒質がガラスの連続): 群の外径は最大の有効半径 × 1.05
    groups, cur = [], []
    for k, _, _ in path:
        cur.append(k)
        if not glass[k]:
            if len(cur) >= 2:
                groups.append(cur)
            cur = []
    r_out = dict(sd)
    for g in groups:
        R = 1.05 * max(sd[k] for k in g)
        for k in g:
            r_out[k] = R

    def to2(P):
        P = np.asarray(P, float)
        h, v = P[..., 2], P[..., vi]
        return np.stack([cr[0] * h - cr[1] * v, cr[1] * h + cr[0] * v], -1)

    def prof(k, rmax):
        r = recs[k]
        yy = np.linspace(-rmax, rmax, npf)
        c = 0.0 if r["R"] == RT.INF else 1.0 / r["R"]
        zz = RT._sag(yy * yy, c, r["k"], r["asph"])
        if not np.all(np.isfinite(zz)):
            raise ValueError("%s: record %d sag is not finite inside its semi-diameter" % (op, k))
        loc = np.zeros((npf, 3))
        loc[:, 1 if view == "yz" else 0] = yy
        loc[:, 2] = zz
        Rm, o = lay["poses"][k]
        return loc @ Rm.T + o

    # --- 尺度は描く前に外接矩形から決める ---
    pts_all = []
    for k in pos:
        pts_all.append(prof(k, r_out[k]))
    for (_, _, tr, v) in traced:
        if np.any(v):
            pts_all.append(tr["points"][v, 1:, :].reshape(-1, 3))
    Fi, oi = lay["image"]
    pts_all.append(oi[None, :])
    allp = to2(np.concatenate(pts_all, 0))
    span = float(max(np.ptp(allp[:, 0]), np.ptp(allp[:, 1]), 1e-6))
    s = _auto_scale(1.3 * span, 250.0) if scale is None else _num(scale, "scale", op, positive=True)
    sh = _Sheet(s)
    lead = 0.15 * span
    # 光軸 = 視野 0 の主光線(絞りの中心を狙った実光線)の折れ線。座標系の原点の折れ線は平板の切り替えで
    #   ジグザグになるので使わない。光路長はその第 1 面 → 像面の長さ、折り返しの角度は反射の前後の向きの角。
    Pc, Dc, _, okc = R3._aim(sysd, np.zeros((1, 2)), (0.0, 0.0), layout=lay)
    trc = R3._trace(sysd, Pc, Dc, layout=lay)
    if not (okc[0] and trc["valid"][0]):
        raise ValueError("%s: the axis ray (field 0, stop centre) does not reach the image" % op)
    axis = [trc["points"][0, i] for i in range(1, trc["points"].shape[1])]
    first = to2(axis[0])
    d0 = to2(trc["dirs"][0, 0])
    nd0 = float(np.hypot(*d0))
    pre = first - lead * d0 / nd0 if nd0 > 1e-9 else first
    sh.poly([pre] + [to2(p_) for p_ in axis], "AXIS", tag="axis")
    path_len = float(sum(np.linalg.norm(axis[i + 1] - axis[i]) for i in range(len(axis) - 1)))
    # 面
    surf_rec = []
    placed = []
    ingroup = {k for g in groups for k in g}
    for k, j in pos.items():
        r = recs[k]
        pp = to2(prof(k, r_out[k] if k in ingroup else sd[k]))
        layer = "OUTLINE" if (k in ingroup or r["reflect"] or r["beamsplitter"]) else "THIN"
        is_dummy = (not r["reflect"]) and r["beamsplitter"] is None and k not in ingroup and r["R"] == RT.INF
        if not (is_dummy and k == stop):
            sh.poly(pp, layer, tag="surface:%d" % k)
        Rm, o = lay["poses"][k]
        if r["mirror"]:                                  # 鏡の裏の斜線(光の来ない側 = 局所の +z)
            back = to2(Rm[:, 2])
            nb = float(np.hypot(*back))
            if nb > 1e-6:
                bdir = back / nb
                tang = pp[-1] - pp[0]
                tang = tang / max(float(np.hypot(*tang)), 1e-12)
                L = sh.p(2.5)
                for t in np.linspace(0.0, 1.0, 9):
                    a = pp[0] + t * (pp[-1] - pp[0])
                    sh.line(a, a + L * (0.7 * bdir + 0.7 * tang), "THIN", tag="mirror-back:%d" % k)
        lab = _ascii_label(r["label"], "S%d" % (j + 1))
        if r["beamsplitter"] is not None and "BS" not in lab:
            lab += " BS"
        top = pp[np.argmax(pp[:, 1])].copy()
        top[1] += sh.p(3.0)
        wlab = CHAR_W * sh.p(TEXT_SMALL) * len(lab)
        for (lx, ly, lw) in placed:
            if abs(top[0] - lx) < 0.5 * (wlab + lw) + sh.p(1.0) and abs(top[1] - ly) < sh.p(1.8 * TEXT_SMALL):
                top[1] = ly + sh.p(1.8 * TEXT_SMALL)
        placed.append((top[0], top[1], wlab))
        surf_rec.append({"record": k, "label": lab, "vertex": o.tolist(), "semi_diameter": float(sd[k]),
                         "outer_radius": float(r_out[k]), "R": r["R"], "k": r["k"], "mirror": r["mirror"],
                         "beamsplitter": r["beamsplitter"], "normal": Rm[:, 2].tolist()})
        sh.text((top[0], top[1]), lab, height=sh.p(TEXT_SMALL), align="center", tag="label:surface")
    for g in groups:
        for a, b in zip(g[:-1], g[1:]):
            for sg in (1.0, -1.0):
                pa = to2(prof(a, r_out[a])[0 if sg < 0 else -1])
                pb = to2(prof(b, r_out[b])[0 if sg < 0 else -1])
                sh.line(pa, pb, "OUTLINE", tag="edge")
    # 絞り
    Rm, o = lay["poses"][stop]
    mark = max(sh.p(4.0), 0.12 * ap_stop)
    for sg in (1.0, -1.0):
        e = np.zeros(3)
        e[1 if view == "yz" else 0] = sg
        a = to2(o + Rm @ (e * ap_stop))
        b = to2(o + Rm @ (e * (ap_stop + mark)))
        sh.line(a, b, "STOP", tag="stop")
    # 光線
    rays_rec = []
    n_vig = 0
    for jf, (f, qs, tr, v) in enumerate(traced):
        layer = "RAY_F%d" % (jf + 1)
        for r_ in range(len(qs)):
            if not v[r_]:
                n_vig += 1
                continue
            pts = tr["points"][r_]
            p0, dd = pts[0], tr["dirs"][r_, 0]
            if sysd["object_mm"] == RT.INF or sysd["object_mm"] > 3.0 * span:
                start = pts[1] - lead * dd
            else:
                start = p0
            seq = [start] + [pts[i] for i in range(1, pts.shape[0])]
            sh.poly(to2(np.array(seq)), layer, tag="ray:%d:%d" % (jf, r_))
            rays_rec.append({"field_index": jf, "field": list(f), "pupil": float(qs[r_]),
                             "points": [list(map(float, p)) for p in seq[1:]]})
    # 重ねる系(照明の枝など): 面は細線、光線は照明の光線の層
    ov_rec = []
    for io, ov in enumerate(ovs):
        lo = R3._layout(ov)
        apo = ov["records"][ov["stop"]]["ap"]
        tg = np.zeros((max(nr, 2), 2))
        tg[:, 1 if view == "yz" else 0] = np.linspace(-1.0, 1.0, max(nr, 2)) * apo
        Po, Do, _, oko = R3._aim(ov, tg, tuple(ov["field"]), layout=lo)
        tro = R3._trace(ov, Po, Do, layout=lo)
        for r_ in range(len(tg)):
            if not (oko[r_] and tro["valid"][r_]):
                continue
            seq = [tro["points"][r_, i] for i in range(tro["points"].shape[1])]
            sh.poly(to2(np.array(seq)), "LIGHTRAY", tag="overlay:%d:%d" % (io, r_))
            ov_rec.append({"overlay": io, "points": [list(map(float, p_)) for p_ in seq]})
        src = to2(tro["points"][0, 0]) if oko[0] else None
        if src is not None:
            sh.circle(src, sh.p(1.5), "LIGHT", tag="overlay-source:%d" % io)
            sh.text((src[0], src[1] + sh.p(3.0)), "LIGHT", height=sh.p(TEXT_SMALL), align="center",
                    tag="label:light")
    # 像面
    ih = max([abs(float(((np.array(rr["points"][-1]) - oi) @ Fi)[vi])) for rr in rays_rec] + [0.0])
    hh = max(1.2 * ih, 0.25 * max(sd.values()))
    tx, ty = sysd["image_tilt"]
    slope = math.tan(math.radians(tx if view == "yz" else ty))
    e = np.zeros(3)
    e[vi] = 1.0
    e[2] = slope
    a, b = to2(oi - hh * (Fi @ e)), to2(oi + hh * (Fi @ e))
    sh.line(a, b, "IMAGE", tag="image")
    sh.text((b[0], b[1] + sh.p(3.0)), "IMA", height=sh.p(TEXT_SMALL), align="center", tag="label:image")
    # 物面(有限で近ければ)
    if sysd["object_mm"] != RT.INF and sysd["object_mm"] <= 3.0 * span:
        hmax = max([abs(f[1 if view == "yz" else 0]) for f in flds] + [0.25 * max(sd.values())])
        tx, ty = sysd["object_tilt"]
        sl = math.tan(math.radians(tx if view == "yz" else ty))
        e = np.zeros(3)
        e[vi] = 1.0
        e[2] = sl
        po = np.array([0.0, 0.0, -sysd["object_mm"]])
        a, b = to2(po - 1.2 * hmax * e), to2(po + 1.2 * hmax * e)
        sh.line(a, b, "THIN", tag="object")
        sh.text((b[0], b[1] + sh.p(3.0)), "OBJ", height=sh.p(TEXT_SMALL), align="center", tag="label:object")
    # 折り返しの角度(反射の前後の主光線の向き)
    folds = []
    for j, (k, act, _) in enumerate(path):
        if act == "reflect":
            d1, d2 = trc["dirs"][0, j], trc["dirs"][0, j + 1]
            folds.append(math.degrees(math.acos(max(-1.0, min(1.0, float(d1 @ d2))))))
    # 寸法: 占有の幅と高さ
    x0, y0, x1, y1 = _bbox([en for en in sh.ents if en["layer"] in ("OUTLINE", "THIN", "IMAGE", "STOP", "LIGHTRAY", "LIGHT")
                            or en["layer"].startswith("RAY_F")])
    W, H = x1 - x0, y1 - y0
    step = sh.p(9.0)
    sh.dim((x0, y0), (x1, y0), -step, "W " + _fmt(W), "W", W)
    sh.dim((x1, y0), (x1, y1), -step, "H " + _fmt(H), "H", H)
    th = sh.p(TEXT_SMALL)
    ytab = y0 - 2.5 * step
    notes = ["PATH %s   FOLDS %s   VIEW %s (horizontal z, vertical %s)"
             % (_fmt(path_len), " / ".join(_fmt(a_, 1) for a_ in folds) or "-", view, "y" if vi == 1 else "x"),
             "FIELD %s   WL %.1f nm   STOP %s" % (" / ".join("(%s,%s)" % (_fmt(f[0], 1), _fmt(f[1], 1)) for f in flds),
                                                  1000.0 * sysd["wavelength_um"],
                                                  _ascii_label(recs[stop]["label"], "S%d" % (pos[stop] + 1)))]
    for k, ln in enumerate(notes):
        sh.text((x0, ytab - 1.7 * th * k), ln, height=th, tag="spec:%d" % k)
    values = {"path_length": path_len, "footprint": [W, H], "fold_angles_deg": folds, "surfaces": surf_rec,
              "rays": rays_rec, "rays_vignetted": n_vig, "image_center": oi.tolist(), "fields": [list(f) for f in flds],
              "view": view, "scale": s, "horizontal": "z", "rotate_deg": int(rotate_deg), "overlays": ov_rec}
    meta = {"source": "raytrace3d.noncoaxial_system", "groups": groups, "stop": stop,
            "conventions": "horizontal = global z, vertical = global %s; mm" % ("y" if vi == 1 else "x")}
    title_lines = [title or "OPTICAL LAYOUT (FOLDED SYSTEM, VIEW %s)" % view.upper(),
                   "UNITS mm   SCALE " + _scale_label(s)]
    return _finish(sh, title or "noncoaxial_layout", values, meta, title_lines)


def _fringe(v):
    """縞の本数の書き方: 0.5 刻みに丸め、整数なら整数で。"""
    r = round(v * 2.0) / 2.0
    if r == 0.0 and v > 0.0:
        r = 0.5
    return ("%d" % r) if r == int(r) else ("%.1f" % r)


# --------------------------------------------------------------------------- #
# 4. 書き出し
# --------------------------------------------------------------------------- #
def _f(v):
    """座標の書き方(1e-6 mm まで、-0 を出さない)。"""
    s = "%.6f" % v
    if s.startswith("-") and float(s) == 0.0:
        s = s[1:]
    return s


def _esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def drawing_svg(drawing):
    """図を SVG の文字列にする(``text``)—— stdlib だけ、座標は実物の mm、紙の大きさ = 図 × 縮尺。

    ``viewBox`` は実物の mm、``width`` / ``height`` は紙の mm なので、ブラウザで 100 % 表示・印刷すると縮尺どおり
    (縮尺 1:1 なら等倍)。y は上向き(図のモデル)を SVG の下向きに直すため、**y の符号だけを反転して**書く
    (変換行列は使わない —— 読み戻しが座標をそのまま拾えるように)。層は ``<g data-layer>``、線の太さは
    ISO 128 の太線 0.5 / 細線 0.25 mm(紙の上)、一点鎖線と破線は ``stroke-dasharray``。矢印は塗りつぶしの
    多角形、円弧は ``<path d="M … A …">``。各要素の意味の印は ``data-tag``。
    """
    op = "drawing_svg"
    _drawing(drawing, op)
    s = float(drawing["scale"])
    x0, y0, x1, y1 = drawing["frame"]
    W, H = (x1 - x0), (y1 - y0)
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<svg xmlns="http://www.w3.org/2000/svg" width="%smm" height="%smm" viewBox="%s %s %s %s" '
           'data-scale="%s" data-units="mm">' % (_f(W * s), _f(H * s), _f(x0), _f(-y1), _f(W), _f(H), _f(s)),
           "<title>%s</title>" % _esc(str(drawing.get("name", "drawing"))),
           '<rect x="%s" y="%s" width="%s" height="%s" fill="#ffffff"/>' % (_f(x0), _f(-y1), _f(W), _f(H))]
    by_layer = {}
    for e in drawing["entities"]:
        by_layer.setdefault(e["layer"], []).append(e)
    for layer in LAYERS:
        if layer not in by_layer:
            continue
        lw, _, lt, color = LAYERS[layer]
        dash = ""
        if LTYPES[lt][1]:
            pat = [max(abs(v), 0.5) / s for v in LTYPES[lt][1]]
            dash = ' stroke-dasharray="%s"' % " ".join(_f(v) for v in pat)
        out.append('<g data-layer="%s" stroke="%s" stroke-width="%s" fill="none" stroke-linecap="round" '
                   'stroke-linejoin="round"%s>' % (layer, color, _f(lw / s), dash))
        for e in by_layer[layer]:
            tag = ' data-tag="%s"' % _esc(e.get("tag", "")) if e.get("tag") else ""
            t = e["type"]
            if t == "line":
                (ax, ay), (bx, by) = e["points"]
                out.append('<line x1="%s" y1="%s" x2="%s" y2="%s"%s/>' % (_f(ax), _f(-ay), _f(bx), _f(-by), tag))
            elif t == "polyline":
                pts = " ".join("%s,%s" % (_f(x), _f(-y)) for x, y in e["points"])
                if e.get("closed"):
                    fill = ' fill="%s" stroke-dasharray="none"' % color if e.get("fill") else ""
                    out.append('<polygon points="%s"%s%s/>' % (pts, fill, tag))
                else:
                    out.append('<polyline points="%s"%s/>' % (pts, tag))
            elif t == "circle":
                cx, cy = e["center"]
                out.append('<circle cx="%s" cy="%s" r="%s"%s/>' % (_f(cx), _f(-cy), _f(e["r"]), tag))
            elif t == "arc":
                cx, cy = e["center"]
                r = e["r"]
                a0, a1 = math.radians(e["start_deg"]), math.radians(e["end_deg"])
                sweep = (e["end_deg"] - e["start_deg"]) % 360.0
                large = 1 if sweep > 180.0 else 0
                p0 = (cx + r * math.cos(a0), -(cy + r * math.sin(a0)))
                p1 = (cx + r * math.cos(a1), -(cy + r * math.sin(a1)))
                # 反時計回り(y 上向き)は SVG(y 下向き)では sweep-flag = 0
                out.append('<path d="M %s %s A %s %s 0 %d 0 %s %s"%s/>' % (_f(p0[0]), _f(p0[1]), _f(r), _f(r), large,
                                                                          _f(p1[0]), _f(p1[1]), tag))
            else:
                x, y = e["at"]
                anchor = {"left": "start", "center": "middle", "right": "end"}[e.get("align", "left")]
                rot = ""
                if e.get("angle", 0.0):
                    rot = ' transform="rotate(%s %s %s)"' % (_f(-e["angle"]), _f(x), _f(-y))
                out.append('<text x="%s" y="%s" font-size="%s" font-family="DejaVu Sans Mono, Consolas, monospace" '
                           'text-anchor="%s" fill="%s" stroke="none" xml:space="preserve" style="white-space:pre"%s%s>%s</text>'
                           % (_f(x), _f(-y), _f(e["height"] / CAP_EM), anchor, color, rot, tag, _esc(e["text"])))
        out.append("</g>")
    out.append("</svg>")
    return "\n".join(out) + "\n"


def _dxf_text(s):
    out = []
    for ch in s:
        if ch in _DXF_SPECIAL:
            out.append(_DXF_SPECIAL[ch])
        elif 32 <= ord(ch) < 127:
            out.append(ch)
        else:
            raise ValueError("drawing_dxf: the character %r cannot be written to DXF R12 text (ASCII, ⌀, °, ± only)"
                             % ch)
    return "".join(out)


def drawing_dxf(drawing):
    """図を DXF R12(AC1009)の ASCII にする(``text``)—— CAD に持ち込める最小の完全な構成を stdlib だけで書く。

    構成: ``HEADER``(``$ACADVER`` = AC1009、``$INSBASE``、``$EXTMIN`` / ``$EXTMAX``)、``TABLES``(``LTYPE`` に
    CONTINUOUS / CENTER(一点長鎖線)/ DASHED、``LAYER`` に図の層と色・線種、``STYLE`` に STANDARD)、``ENTITIES``
    (``LINE`` / ``POLYLINE`` + ``VERTEX`` + ``SEQEND`` / ``CIRCLE`` / ``ARC`` / ``TEXT`` / 矢印は ``SOLID``)、
    ``EOF``。座標は実物の mm(縮尺 1:1 のモデル空間)。文字は ASCII と ⌀ ° ±(→ ``%%c`` ``%%d`` ``%%p``)だけで、
    ほかの非 ASCII は ValueError(R12 の文字はコードページ依存で、黙って化けるより止める)。行末は CRLF。
    """
    op = "drawing_dxf"
    _drawing(drawing, op)
    L = []

    def g(code, val):
        L.append("%3d" % code)
        L.append(val if isinstance(val, str) else (_f(val) if isinstance(val, float) else str(val)))
    x0, y0, x1, y1 = drawing["frame"]
    g(0, "SECTION"); g(2, "HEADER")
    g(9, "$ACADVER"); g(1, "AC1009")
    g(9, "$INSBASE"); g(10, 0.0); g(20, 0.0); g(30, 0.0)
    g(9, "$EXTMIN"); g(10, float(x0)); g(20, float(y0)); g(30, 0.0)
    g(9, "$EXTMAX"); g(10, float(x1)); g(20, float(y1)); g(30, 0.0)
    g(9, "$LUNITS"); g(70, 2)
    g(9, "$LUPREC"); g(70, 4)
    g(0, "ENDSEC")
    g(0, "SECTION"); g(2, "TABLES")
    g(0, "TABLE"); g(2, "LTYPE"); g(70, len(LTYPES))
    for name, (desc, pat) in LTYPES.items():
        g(0, "LTYPE"); g(2, name); g(70, 0); g(3, desc); g(72, 65); g(73, len(pat))
        g(40, float(sum(abs(v) for v in pat)))
        for v in pat:
            g(49, float(v))
    g(0, "ENDTAB")
    used = [k for k in LAYERS if any(e["layer"] == k for e in drawing["entities"])]
    g(0, "TABLE"); g(2, "LAYER"); g(70, len(used) + 1)
    g(0, "LAYER"); g(2, "0"); g(70, 0); g(62, 7); g(6, "CONTINUOUS")
    for k in used:
        g(0, "LAYER"); g(2, k); g(70, 0); g(62, LAYERS[k][1]); g(6, LAYERS[k][2])
    g(0, "ENDTAB")
    g(0, "TABLE"); g(2, "STYLE"); g(70, 1)
    g(0, "STYLE"); g(2, "STANDARD"); g(70, 0); g(40, 0.0); g(41, 1.0); g(50, 0.0); g(71, 0); g(42, 2.5)
    g(3, "txt"); g(4, "")
    g(0, "ENDTAB")
    g(0, "ENDSEC")
    g(0, "SECTION"); g(2, "ENTITIES")
    for e in drawing["entities"]:
        t, lay = e["type"], e["layer"]
        if t == "line":
            (ax, ay), (bx, by) = e["points"]
            g(0, "LINE"); g(8, lay); g(10, ax); g(20, ay); g(30, 0.0); g(11, bx); g(21, by); g(31, 0.0)
        elif t == "polyline":
            pts = e["points"]
            if e.get("fill") and e.get("closed") and len(pts) in (3, 4):
                q = list(pts) + ([pts[-1]] if len(pts) == 3 else [])
                # SOLID の頂点の順は 1-2-4-3(Z 字)。3 角形は 3 点目と 4 点目を同じにする
                order = [q[0], q[1], q[3], q[2]] if len(pts) == 4 else [q[0], q[1], q[2], q[2]]
                g(0, "SOLID"); g(8, lay)
                for k, (x, y) in enumerate(order):
                    g(10 + k, float(x)); g(20 + k, float(y)); g(30 + k, 0.0)
                continue
            g(0, "POLYLINE"); g(8, lay); g(66, 1); g(10, 0.0); g(20, 0.0); g(30, 0.0); g(70, 1 if e.get("closed") else 0)
            for x, y in pts:
                g(0, "VERTEX"); g(8, lay); g(10, float(x)); g(20, float(y)); g(30, 0.0)
            g(0, "SEQEND"); g(8, lay)
        elif t == "circle":
            g(0, "CIRCLE"); g(8, lay); g(10, float(e["center"][0])); g(20, float(e["center"][1])); g(30, 0.0)
            g(40, float(e["r"]))
        elif t == "arc":
            g(0, "ARC"); g(8, lay); g(10, float(e["center"][0])); g(20, float(e["center"][1])); g(30, 0.0)
            g(40, float(e["r"])); g(50, float(e["start_deg"])); g(51, float(e["end_deg"]))
        else:
            x, y = e["at"]
            al = {"left": 0, "center": 1, "right": 2}[e.get("align", "left")]
            g(0, "TEXT"); g(8, lay); g(10, float(x)); g(20, float(y)); g(30, 0.0); g(40, float(e["height"]))
            g(1, _dxf_text(e["text"]))
            if e.get("angle", 0.0):
                g(50, float(e["angle"]))
            if al:
                g(72, al); g(11, float(x)); g(21, float(y)); g(31, 0.0)
    g(0, "ENDSEC")
    g(0, "EOF")
    return "\r\n".join(L) + "\r\n"


# --------------------------------------------------------------------------- #
# 5. 読み戻し
# --------------------------------------------------------------------------- #
def _check_text(text, op):
    if isinstance(text, bytes):
        try:
            text = text.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("%s: the input is not UTF-8 text" % op) from exc
    if not isinstance(text, str):
        raise ValueError("%s: expected the text of a file, got %r" % (op, type(text).__name__))
    if len(text) > _MAX_TEXT_BYTES:
        raise ValueError("%s: input of %d characters exceeds the limit %d" % (op, len(text), _MAX_TEXT_BYTES))
    return text


def dxf_entities(text):
    """DXF(R12 の ASCII、R2000 以降の ``LWPOLYLINE`` も可)の ENTITIES を図の要素に読み戻す(``table``)。

    返り値: ``{"version", "layers", "entities"}``。``entities`` は ``drawing_dxf`` が書く要素と同じ形
    (``line`` / ``polyline`` / ``circle`` / ``arc`` / ``text``、``SOLID`` は塗りの閉じた ``polyline``)。文字の
    ``%%c`` ``%%d`` ``%%p`` は ⌀ ° ± に戻す。グループコードと値の対になっていない・数値が読めない・ENTITIES が
    閉じていない入力は ValueError(黙って途中まで返さない)。ブロック参照(INSERT)は展開しない(数だけ ``skipped`` に)。
    """
    op = "dxf_entities"
    text = _check_text(text, op)
    lines = text.splitlines()
    if len(lines) % 2:
        lines = lines[:-1] if lines and not lines[-1].strip() else lines
    if len(lines) % 2:
        raise ValueError("%s: the group codes and values are not paired (odd number of lines)" % op)
    pairs = []
    for i in range(0, len(lines), 2):
        try:
            code = int(lines[i].strip())
        except ValueError as exc:
            raise ValueError("%s: line %d: %r is not a group code" % (op, i + 1, lines[i])) from exc
        pairs.append((code, lines[i + 1].strip() if code != 1 else lines[i + 1]))
    version = None
    layers = {}
    ents = []
    skipped = {}
    i = 0
    n = len(pairs)
    section = None

    def num(v, code):
        try:
            x = float(v)
        except ValueError as exc:
            raise ValueError("%s: group %d value %r is not a number" % (op, code, v)) from exc
        if not math.isfinite(x):
            raise ValueError("%s: group %d value %r is not finite" % (op, code, v))
        return x

    def read_entity(j):
        """pairs[j] が 0/<型> のとき、次の 0 までの属性を dict に(同じ符号は列に)。"""
        attrs = {}
        k = j + 1
        while k < n and pairs[k][0] != 0:
            attrs.setdefault(pairs[k][0], []).append(pairs[k][1])
            k += 1
        return attrs, k
    closed = False
    while i < n:
        code, val = pairs[i]
        if code == 0 and val == "SECTION":
            section = pairs[i + 1][1] if i + 1 < n else None
            i += 2
            continue
        if code == 0 and val == "ENDSEC":
            if section == "ENTITIES":
                closed = True
            section = None
            i += 1
            continue
        if code == 0 and val == "EOF":
            break
        if section == "HEADER" and code == 9 and val == "$ACADVER":
            version = pairs[i + 1][1]
            i += 2
            continue
        if section == "TABLES" and code == 0 and val == "LAYER":
            attrs, i = read_entity(i)
            if 2 in attrs:
                layers[attrs[2][0]] = {"color": int(num(attrs.get(62, ["7"])[0], 62)),
                                       "linetype": attrs.get(6, ["CONTINUOUS"])[0]}
            continue
        if section == "ENTITIES" and code == 0:
            typ = val
            attrs, k = read_entity(i)
            lay = attrs.get(8, ["0"])[0]
            if typ == "LINE":
                ents.append({"type": "line", "layer": lay,
                             "points": [[num(attrs[10][0], 10), num(attrs[20][0], 20)],
                                        [num(attrs[11][0], 11), num(attrs[21][0], 21)]]})
                i = k
            elif typ == "POLYLINE":
                flags = int(num(attrs.get(70, ["0"])[0], 70))
                pts = []
                i = k
                while i < n and pairs[i] == (0, "VERTEX"):
                    va, i = read_entity(i)
                    pts.append([num(va[10][0], 10), num(va[20][0], 20)])
                if i >= n or pairs[i] != (0, "SEQEND"):
                    raise ValueError("%s: POLYLINE without SEQEND" % op)
                _, i = read_entity(i)
                ents.append({"type": "polyline", "layer": lay, "points": pts, "closed": bool(flags & 1),
                             "fill": False})
            elif typ == "LWPOLYLINE":
                xs = [num(v, 10) for v in attrs.get(10, [])]
                ys = [num(v, 20) for v in attrs.get(20, [])]
                if len(xs) != len(ys):
                    raise ValueError("%s: LWPOLYLINE has unpaired coordinates" % op)
                flags = int(num(attrs.get(70, ["0"])[0], 70))
                ents.append({"type": "polyline", "layer": lay, "points": [list(p) for p in zip(xs, ys)],
                             "closed": bool(flags & 1), "fill": False})
                i = k
            elif typ == "SOLID":
                q = [[num(attrs[10 + m][0], 10 + m), num(attrs[20 + m][0], 20 + m)] for m in range(4)]
                pts = [q[0], q[1], q[3], q[2]]
                if pts[2] == pts[3]:
                    pts = pts[:3]
                ded = []
                for p in pts:
                    if not ded or p != ded[-1]:
                        ded.append(p)
                ents.append({"type": "polyline", "layer": lay, "points": ded, "closed": True, "fill": True})
                i = k
            elif typ == "CIRCLE":
                ents.append({"type": "circle", "layer": lay, "center": [num(attrs[10][0], 10), num(attrs[20][0], 20)],
                             "r": num(attrs[40][0], 40)})
                i = k
            elif typ == "ARC":
                ents.append({"type": "arc", "layer": lay, "center": [num(attrs[10][0], 10), num(attrs[20][0], 20)],
                             "r": num(attrs[40][0], 40), "start_deg": num(attrs[50][0], 50),
                             "end_deg": num(attrs[51][0], 51)})
                i = k
            elif typ == "TEXT":
                s = attrs.get(1, [""])[0]
                for a, b in _DXF_BACK.items():
                    s = s.replace(a, b)
                al = int(num(attrs.get(72, ["0"])[0], 72))
                if al and 11 in attrs:
                    at = [num(attrs[11][0], 11), num(attrs[21][0], 21)]
                else:
                    at = [num(attrs[10][0], 10), num(attrs[20][0], 20)]
                ents.append({"type": "text", "layer": lay, "at": at, "text": s, "height": num(attrs[40][0], 40),
                             "angle": num(attrs.get(50, ["0"])[0], 50),
                             "align": {0: "left", 1: "center", 2: "right"}.get(al, "left")})
                i = k
            else:
                skipped[typ] = skipped.get(typ, 0) + 1
                i = k
            if len(ents) > _MAX_ENTITIES:
                raise ValueError("%s: more than %d entities" % (op, _MAX_ENTITIES))
            continue
        i += 1
    if not closed:
        raise ValueError("%s: no complete ENTITIES section (missing ENDSEC)" % op)
    return {"version": version, "layers": layers, "entities": ents, "skipped": skipped}


_NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"


def _svg_arc_center(x0, y0, rx, large, sweep, x1, y1):
    """SVG の円弧(端点表記、rx = ry)の中心(SVG 座標)。SVG 1.1 の付録 F.6.5 の式。"""
    dx2, dy2 = (x0 - x1) / 2.0, (y0 - y1) / 2.0
    r = rx
    d2 = dx2 * dx2 + dy2 * dy2
    if d2 > r * r:
        r = math.sqrt(d2)
    co = math.sqrt(max(r * r - d2, 0.0) / d2) if d2 > 0 else 0.0
    if large == sweep:
        co = -co
    cxp, cyp = co * dy2, -co * dx2
    return cxp + (x0 + x1) / 2.0, cyp + (y0 + y1) / 2.0, r


def svg_entities(text):
    """SVG(``drawing_svg`` が書く形: ``line`` / ``polyline`` / ``polygon`` / ``circle`` / ``path`` の M…A… と M…L…
    / ``text``)を図の要素に読み戻す(``table``)。y の符号を戻して図のモデルの向き(y 上)にする。

    返り値: ``{"entities", "scale", "view_box"}``。層は祖先の ``<g data-layer>``、意味の印は ``data-tag``。
    ★DOCTYPE・実体参照の宣言を含む入力は ValueError(XML の実体展開の攻撃を入口で止める)。``transform`` は
    文字の ``rotate`` だけを解釈し、ほかの変換を持つ要素は ValueError(座標を黙って取り違えない)。
    """
    op = "svg_entities"
    text = _check_text(text, op)
    if re.search(r"<!DOCTYPE|<!ENTITY", text, re.I):
        raise ValueError("%s: DOCTYPE / ENTITY declarations are refused" % op)
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise ValueError("%s: not well-formed XML (%s)" % (op, exc)) from exc
    ns = "{http://www.w3.org/2000/svg}"
    if root.tag not in (ns + "svg", "svg"):
        raise ValueError("%s: the root element is not <svg>" % op)
    ents = []

    def f(el, k):
        v = el.get(k)
        if v is None:
            raise ValueError("%s: <%s> lacks %s" % (op, el.tag.replace(ns, ""), k))
        x = float(v)
        if not math.isfinite(x):
            raise ValueError("%s: non-finite %s" % (op, k))
        return x

    def walk(el, layer):
        lay = el.get("data-layer", layer)
        tag = el.tag.replace(ns, "")
        tr = el.get("transform")
        if tr and tag != "text":
            raise ValueError("%s: <%s transform=%r> is not supported (coordinates would be misread)" % (op, tag, tr))
        dtag = el.get("data-tag", "")
        if tag == "line":
            ents.append({"type": "line", "layer": lay, "tag": dtag,
                         "points": [[f(el, "x1"), -f(el, "y1")], [f(el, "x2"), -f(el, "y2")]]})
        elif tag in ("polyline", "polygon"):
            nums = [float(v) for v in re.findall(_NUM, el.get("points", ""))]
            if len(nums) % 2:
                raise ValueError("%s: <%s> has an odd number of coordinates" % (op, tag))
            pts = [[nums[k], -nums[k + 1]] for k in range(0, len(nums), 2)]
            ents.append({"type": "polyline", "layer": lay, "tag": dtag, "points": pts, "closed": tag == "polygon",
                         "fill": tag == "polygon" and el.get("fill", "none") != "none"})
        elif tag == "circle":
            ents.append({"type": "circle", "layer": lay, "tag": dtag, "center": [f(el, "cx"), -f(el, "cy")],
                         "r": f(el, "r")})
        elif tag == "path":
            d = el.get("d", "")
            m = re.fullmatch(r"\s*M\s*(%s)[ ,]+(%s)\s*A\s*(%s)[ ,]+(%s)[ ,]+(%s)[ ,]+([01])[ ,]+([01])[ ,]+(%s)[ ,]+(%s)\s*"
                             % ((_NUM,) * 5 + (_NUM, _NUM)), d)
            if m:
                x0, y0, rx, _ry, _rot = (float(m.group(k)) for k in range(1, 6))
                large, sweep = int(m.group(6)), int(m.group(7))
                x1, y1 = float(m.group(8)), float(m.group(9))
                cx, cy, r = _svg_arc_center(x0, y0, rx, large, sweep, x1, y1)
                a0 = math.degrees(math.atan2(-(y0 - cy), x0 - cx)) % 360.0
                a1 = math.degrees(math.atan2(-(y1 - cy), x1 - cx)) % 360.0
                if sweep == 1:                          # 時計回り(y 上向きで)なら向きを入れ替える
                    a0, a1 = a1, a0
                ents.append({"type": "arc", "layer": lay, "tag": dtag, "center": [cx, -cy], "r": r,
                             "start_deg": a0, "end_deg": a1})
            else:
                toks = re.findall(r"[MLZ]|%s" % _NUM, d)
                pts, closed, k = [], False, 0
                while k < len(toks):
                    if toks[k] in ("M", "L"):
                        k += 1
                        continue
                    if toks[k] == "Z":
                        closed = True
                        k += 1
                        continue
                    pts.append([float(toks[k]), -float(toks[k + 1])])
                    k += 2
                if len(pts) < 2:
                    raise ValueError("%s: unsupported path %r" % (op, d[:60]))
                ents.append({"type": "polyline", "layer": lay, "tag": dtag, "points": pts, "closed": closed,
                             "fill": False})
        elif tag == "text":
            ang = 0.0
            if tr:
                mm = re.fullmatch(r"\s*rotate\(\s*(%s)(?:[ ,]+%s[ ,]+%s)?\s*\)\s*" % (_NUM, _NUM, _NUM), tr)
                if not mm:
                    raise ValueError("%s: text transform %r is not a rotate()" % (op, tr))
                ang = -float(mm.group(1))
            anchor = el.get("text-anchor", "start")
            ents.append({"type": "text", "layer": lay, "tag": dtag, "at": [f(el, "x"), -f(el, "y")],
                         "text": "".join(el.itertext()), "height": float(el.get("font-size", "0")), "angle": ang,
                         "align": {"start": "left", "middle": "center", "end": "right"}.get(anchor, "left")})
        if len(ents) > _MAX_ENTITIES:
            raise ValueError("%s: more than %d entities" % (op, _MAX_ENTITIES))
        for ch in el:
            walk(ch, lay)
    walk(root, None)
    vb = [float(v) for v in re.findall(_NUM, root.get("viewBox", ""))]
    sc = root.get("data-scale")
    return {"entities": ents, "scale": float(sc) if sc else None, "view_box": vb}


# --------------------------------------------------------------------------- #
# 6. 画像(任意依存 matplotlib)
# --------------------------------------------------------------------------- #
def drawing_raster(drawing, dpi=150):
    """図を RGB の画像(uint8、(H, W, 3))にする(``rgbimage``)—— matplotlib(任意依存)で、紙の大きさ × *dpi*。

    縮尺どおりの紙の大きさ(``frame`` × ``scale``)で描くので、*dpi* = 25.4 なら 1 画素 = 紙の 1 mm。線の太さは
    層の紙の mm、一点鎖線と破線も層どおり。PNG に保存するなら ``imgio`` か PIL で書く。matplotlib が無ければ
    ImportError(``pip install matplotlib``)。
    """
    op = "drawing_raster"
    _drawing(drawing, op)
    dpi = _num(dpi, "dpi", op, positive=True)
    if dpi > 1200:
        raise ValueError("%s: dpi %g exceeds 1200" % (op, dpi))
    try:
        import matplotlib
        matplotlib.use("Agg", force=False)
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from matplotlib.patches import Arc, Circle, Polygon
    except ImportError as exc:                                # pragma: no cover - 任意依存
        raise ImportError("%s needs matplotlib (pip install matplotlib)" % op) from exc
    s = float(drawing["scale"])
    x0, y0, x1, y1 = drawing["frame"]
    wi, hi = (x1 - x0) * s / 25.4, (y1 - y0) * s / 25.4
    if wi * dpi * hi * dpi > 1.0e8:
        raise ValueError("%s: the raster would have %.3g pixels (limit 1e8) — lower dpi" % (op, wi * dpi * hi * dpi))
    fig = Figure(figsize=(wi, hi), dpi=dpi)
    canvas = FigureCanvasAgg(fig)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal")
    ax.axis("off")
    pt_per_mm = 72.0 / 25.4
    for e in drawing["entities"]:
        lw, _, lt, color = LAYERS[e["layer"]]
        ls = "-"
        if LTYPES[lt][1]:
            pat = tuple(max(abs(v), 0.5) / lw for v in LTYPES[lt][1])
            ls = (0, pat)
        lwp = lw * pt_per_mm
        t = e["type"]
        if t == "line":
            (ax_, ay), (bx, by) = e["points"]
            ax.plot([ax_, bx], [ay, by], color=color, lw=lwp, ls=ls, solid_capstyle="round")
        elif t == "polyline":
            p = np.asarray(e["points"])
            if e.get("closed"):
                ax.add_patch(Polygon(p, closed=True, fill=bool(e.get("fill")), facecolor=color, edgecolor=color,
                                     lw=lwp, ls="-" if e.get("fill") else ls))
            else:
                ax.plot(p[:, 0], p[:, 1], color=color, lw=lwp, ls=ls)
        elif t == "circle":
            ax.add_patch(Circle(e["center"], e["r"], fill=False, edgecolor=color, lw=lwp, ls=ls))
        elif t == "arc":
            a0, a1 = e["start_deg"], e["end_deg"]
            if a1 <= a0:
                a1 += 360.0
            ax.add_patch(Arc(e["center"], 2 * e["r"], 2 * e["r"], theta1=a0, theta2=a1, edgecolor=color, lw=lwp,
                             ls=ls))
        else:
            ha = {"left": "left", "center": "center", "right": "right"}[e.get("align", "left")]
            ax.text(e["at"][0], e["at"][1], e["text"], fontsize=e["height"] * s * pt_per_mm / CAP_EM,
                    ha=ha, va="baseline", rotation=e.get("angle", 0.0), rotation_mode="anchor", color=color,
                    family="DejaVu Sans Mono")
    canvas.draw()
    img = np.asarray(canvas.buffer_rgba())[:, :, :3].copy()
    return img
