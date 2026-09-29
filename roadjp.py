# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""roadjp — 日本の車両用信号灯器と道路標識を numpy だけで手続き生成する(driveworld の世界に足す部品)。

外部資産(Kenney = 米国式の縦型信号・八角形 STOP)をやめ、**公表寸法をそのまま頂点に持つメッシュ**にする。
ライセンスの問題が無く、寸法は公表値 = 門(テストが頂点から測る)。

公表値(数値はいずれも「公表値、一次資料で要確認」。docstring に出典名を書く):
  * 車両用灯器: 横型、運転者から見て **左から 青・黄・赤**。レンズ径 **300 mm**(2017 年度から標準 250 mm、どちらも現役)
    — 日本の交通信号機(Wikipedia、信号機設置の指針・交通信号機の品質向上ハンドブックを引く)。
  * 灯器の高さ: 路面から灯器の下端まで **4.5 m 以上**(矢印灯器つきは 5.0 m 以上)— 警察庁系の交通信号機工事仕様書(各県警)。
    横型 3 灯は地盤面から 5.6 m 以上とする仕様書もある。Wikipedia は 5.1 m。→ 既定 ``lamp_bottom=5.0``、4.5 未満は ValueError。
  * 設置位置: 一般の車両用灯器は交差点の **向こう側(出口側)**、手前側は補助灯器(信号機設置の指針の解説)。
    停止線は横断歩道の 2 m 手前が標準。アームで車線の上へ張り出す: アーム長 標準 **2.0 m**、最大 **3.5 m**
    (交通信号機の品質向上ハンドブック経由の Wikipedia 記述)。
  * 歩行者用灯器は高さ 2.5 m 以上(今回は作らない)。
  * 標識(道路標識、区画線及び道路標示に関する命令 別表第二、KICTEC の寸法表): 規制・指示(対車両)は **円形 直径 600 mm**、
    逆三角形(一時停止・徐行)一辺 **600 mm**(一時停止は 800 mm の記述もある → 既定 600、引数 ``side`` で変更可)、
    正方形 900 mm、警戒標識は **菱形 一辺 450 mm**(黄地・黒記号)、補助標識は 2/3。
    路側式の取付高さ 板の下端 **1.8 m**、オーバーヘッド 5.0 m(道路標識設置基準の一般値、要確認)。
    色: 規制 = 赤枠・白地・青記号(一時停止は赤地・白記号)、指示 = 青地・白記号、警戒 = 黄地・黒記号。

フレーム規約(driveworld と同じ z-up・メートル、yaw は +x から反時計回り):
  * 標識の板・灯器の表示面は **yaw 0 で法線 −x**(+x へ進んで来る車に向く)。:func:`add_sign` / :func:`add_signal_jp` の
    ``yaw`` は「その向きへ進んで来る車に面が向く」= 法線 (−cos yaw, −sin yaw)。
  * 灯器のレンズは、その車の運転者から見て左→右 = 青・黄・赤。yaw 0 では運転者の左 = +y なので **青が +y、赤が −y**。
  * 信号の柱は交差点の向こう側・進入車から見て左外の角に立ち、アームは運転者から見て **右**(yaw 0 で −y)へ水平に出る
    (車線は進行方向の左側にあるので、そこへ張り出す)。灯器はアームの先に吊る(灯器の底 = ``lamp_bottom``)。

限界(self_reported):
  * 板は画像を ``cell`` 画素の四角形に量子化した面の集まり。円・三角の縁は階段になり、頂点から測る寸法は 1〜2 区画ぶん内側になる。
  * 文字は PIL でラスタ化する(annotate と同じフォント探索)。フォントに字形が無ければ ValueError(豆腐を黙って出さない)。
  * 記号(人型・踏切など)は単純化した図形。規格の原図ではない。
"""
from __future__ import annotations

import math

import numpy as np

import driveworld as DW

__all__ = [
    "SIGN_KINDS", "SIGN_COLORS", "sign_image", "sign_params", "plate_mesh_from_image", "sign_mesh", "add_sign",
    "signal_jp_mesh", "add_signal_jp", "LENS_DIAMETER", "ARM_MAX", "LAMP_BOTTOM_MIN", "MOUNT_HEIGHT",
]

#: 標識の種類(規制: stop / slow / speed_limit / no_entry / no_parking / one_way、指示: crosswalk、警戒: caution_*)。
SIGN_KINDS = ("stop", "slow", "speed_limit", "no_entry", "no_parking", "one_way", "crosswalk",
              "caution_crossing", "caution_signal", "caution_children")

#: 標識の色(sRGB [0,1])。規格の色票(JIS Z 9101 系)の正確な値ではなく、区別できる代表色。
SIGN_COLORS = {
    "red": (0.84, 0.05, 0.10), "white": (0.97, 0.97, 0.95), "blue": (0.05, 0.28, 0.72),
    "yellow": (0.98, 0.80, 0.05), "black": (0.05, 0.05, 0.05),
}

LENS_DIAMETER = 0.30          #: 公表値: レンズ径 300 mm(Wikipedia 日本の交通信号機、一次資料で要確認)
ARM_MAX = 3.5                 #: 公表値: アーム長 最大 3.5 m(標準 2.0 m、同上)
LAMP_BOTTOM_MIN = 4.5         #: 公表値: 路面から灯器下端まで 4.5 m 以上(交通信号機工事仕様書、各県警。一次資料で要確認)
MOUNT_HEIGHT = 1.8            #: 公表値: 路側式標識の板の下端 1.8 m(道路標識設置基準の一般値、要確認)

_HOUSING = (0.15, 0.15, 0.17)
_POLE = (0.55, 0.56, 0.58)
_SQ3 = math.sqrt(3.0)

# ─────────────────────────────── 標識の形と寸法 ───────────────────────────────

_SIGN_SPEC = {
    # kind: (shape, ground colour, border colour or None, ink colour, width [m], height [m])
    "stop": ("triangle_down", "red", None, "white", 0.6, 0.6 * _SQ3 / 2),
    "slow": ("triangle_down", "white", "red", "blue", 0.6, 0.6 * _SQ3 / 2),
    "speed_limit": ("circle", "white", "red", "blue", 0.6, 0.6),
    "no_entry": ("circle", "red", None, "white", 0.6, 0.6),
    "no_parking": ("circle", "blue", "red", "red", 0.6, 0.6),
    "one_way": ("rect", "blue", None, "white", 0.6, 0.3),
    "crosswalk": ("pentagon", "blue", None, "white", 0.6, 0.6),
    "caution_crossing": ("diamond", "yellow", "black", "black", 0.45 * math.sqrt(2.0), 0.45 * math.sqrt(2.0)),
    "caution_signal": ("diamond", "yellow", "black", "black", 0.45 * math.sqrt(2.0), 0.45 * math.sqrt(2.0)),
    "caution_children": ("diamond", "yellow", "black", "black", 0.45 * math.sqrt(2.0), 0.45 * math.sqrt(2.0)),
}


def _check_kind(kind: str) -> None:
    if kind not in _SIGN_SPEC:
        raise ValueError("未知の標識 kind %r(使えるのは %s)" % (kind, ", ".join(SIGN_KINDS)))


def sign_params(kind: str, *, side: float | None = None) -> dict:
    """標識 ``kind`` の形・寸法・色を返す(公表値、一次資料で要確認)。

    ``{"shape", "width", "height", "mount_height", "ground", "border", "ink", "side"}``。
    shape は circle / triangle_down / diamond / pentagon / rect。width・height は板の外形 [m]:
    円 直径 0.6、逆三角形 一辺 0.6(高さ = 一辺 × √3/2)、菱形 一辺 0.45(対角 = 一辺 × √2)、横長矩形 0.6 × 0.3、
    五角形(横断歩道)0.6 × 0.6 —— 出典: 道路標識、区画線及び道路標示に関する命令 別表第二 / KICTEC 寸法表。
    矩形・五角形の寸法は同表で確かめていない(要確認)。``side`` を渡すと一辺(円は直径、菱形は一辺)を置き換える
    (一時停止 800 mm の記述に合わせるなど)。mount_height = 1.8(路側式、板の下端)。"""
    _check_kind(kind)
    shape, ground, border, ink, w, h = _SIGN_SPEC[kind]
    if side is not None:
        side = float(side)
        if not (side > 0) or not math.isfinite(side):
            raise ValueError("side は正の有限値")
        if shape == "triangle_down":
            w, h = side, side * _SQ3 / 2
        elif shape == "diamond":
            w = h = side * math.sqrt(2.0)
        elif shape in ("circle", "pentagon"):
            w = h = side
        else:
            h = h * side / w
            w = side
    return {"shape": shape, "width": float(w), "height": float(h), "mount_height": MOUNT_HEIGHT,
            "ground": SIGN_COLORS[ground], "border": None if border is None else SIGN_COLORS[border],
            "ink": SIGN_COLORS[ink], "side": float(side) if side is not None else None}


# ─────────────────────────────── 形のマスク(被覆率) ───────────────────────────

def _grid(H: int, W: int, ss: int):
    """画素中心を ss×ss に細分した座標 (u, v)(画像座標、上が v=0)。"""
    u = (np.arange(W * ss) + 0.5) / ss
    v = (np.arange(H * ss) + 0.5) / ss
    return np.meshgrid(u, v)


def _downsample(m: np.ndarray, ss: int) -> np.ndarray:
    H, W = m.shape[0] // ss, m.shape[1] // ss
    return m.reshape(H, ss, W, ss).mean(axis=(1, 3))


def _polygon_inside(uu, vv, poly) -> np.ndarray:
    """凸多角形(反時計回り、画像座標)の内側 = 全辺の左側。"""
    P = np.asarray(poly, np.float64)
    inside = np.ones(uu.shape, bool)
    for k in range(len(P)):
        (x0, y0), (x1, y1) = P[k], P[(k + 1) % len(P)]
        inside &= (x1 - x0) * (vv - y0) - (y1 - y0) * (uu - x0) >= 0
    return inside


def _shape_polygon(shape: str, H: int, W: int, inset: float = 0.0):
    """形の輪郭(画像座標の凸多角形、画像の縁に接する)。``inset`` は縁から内側への距離 [px]。"""
    if shape == "triangle_down":
        # 頂点: 上辺の両端と下の頂点。内接円の中心 = 上辺から H·(1/3)、内接円半径 r = W/(2√3)
        cx, cy = W / 2.0, 2.0 * H / 3.0
        r = W / (2.0 * _SQ3)
        s = max(0.0, (r - inset) / r)
        P = np.array([[0.0, 0.0], [W, 0.0], [W / 2.0, H]])
    elif shape == "diamond":
        cx, cy = W / 2.0, H / 2.0
        r = W * H / (2.0 * math.hypot(W, H))          # 内接円半径(菱形の中心から辺までの距離)
        s = max(0.0, (r - inset) / r)
        P = np.array([[W / 2.0, 0.0], [0.0, H / 2.0], [W / 2.0, H], [W, H / 2.0]])
    elif shape == "pentagon":
        # 家型: 上が屋根(頂点)、下が四角。屋根の高さ = 0.3 H
        cx, cy = W / 2.0, 0.6 * H
        r = W / 2.0
        s = max(0.0, (r - inset) / r)
        P = np.array([[W / 2.0, 0.0], [0.0, 0.3 * H], [0.0, H], [W, H], [W, 0.3 * H]])
    elif shape == "rect":
        cx, cy = W / 2.0, H / 2.0
        r = min(W, H) / 2.0
        s = max(0.0, (r - inset) / r)
        P = np.array([[0.0, 0.0], [0.0, H], [W, H], [W, 0.0]])
    else:
        raise ValueError("多角形でない shape: %r" % shape)
    P = (P - (cx, cy)) * s + (cx, cy)
    # 画像座標(v が下向き)では反時計回りに見える順に並べ直す(符号付き面積が正になるように)
    x, y = P[:, 0], P[:, 1]
    if 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) < 0:
        P = P[::-1]
    return P


def _shape_mask(shape: str, H: int, W: int, inset: float = 0.0, ss: int = 4) -> np.ndarray:
    """形の被覆率 (H, W) ∈ [0,1] (ss×ss の細分で平均)。``inset`` だけ縁から内側へ縮めた形。"""
    uu, vv = _grid(H, W, ss)
    if shape == "circle":
        r = min(W, H) / 2.0 - inset
        m = (uu - W / 2.0) ** 2 + (vv - H / 2.0) ** 2 <= r * r
    else:
        m = _polygon_inside(uu, vv, _shape_polygon(shape, H, W, inset))
    return _downsample(m.astype(np.float64), ss)


def _disk(H: int, W: int, cu: float, cv: float, r: float, ss: int = 4) -> np.ndarray:
    uu, vv = _grid(H, W, ss)
    return _downsample(((uu - cu) ** 2 + (vv - cv) ** 2 <= r * r).astype(np.float64), ss)


def _poly(H: int, W: int, pts, ss: int = 4) -> np.ndarray:
    """凸多角形(画像座標、任意の向き)の被覆率。"""
    P = np.asarray(pts, np.float64)
    x, y = P[:, 0], P[:, 1]
    if 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) < 0:
        P = P[::-1]
    uu, vv = _grid(H, W, ss)
    return _downsample(_polygon_inside(uu, vv, P).astype(np.float64), ss)


def _segment(H: int, W: int, p0, p1, width: float, ss: int = 4) -> np.ndarray:
    """線分を太さ width の帯(四角形)として塗る。"""
    p0, p1 = np.asarray(p0, np.float64), np.asarray(p1, np.float64)
    d = p1 - p0
    n = np.array([-d[1], d[0]]) / max(1e-12, float(np.hypot(*d))) * (width / 2.0)
    return _poly(H, W, [p0 + n, p1 + n, p1 - n, p0 - n], ss)


def _text_mask(H: int, W: int, text: str, cu: float, cv: float, font_size: int, font_path=None) -> np.ndarray:
    """文字を中心 (cu, cv) に置いた [0,1] マスク。フォントに字形が無ければ ValueError(annotate._require_glyphs)。"""
    import annotate
    Image, ImageDraw, _ = annotate._pil()
    font = annotate._font(int(font_size), font_path)
    annotate._require_glyphs(font, text, font_path)
    im = Image.new("L", (W, H), 0)
    ImageDraw.Draw(im).text((float(cu), float(cv)), text, fill=255, font=font, anchor="mm")
    return np.asarray(im, np.float64) / 255.0


def _paint(rgb: np.ndarray, mask: np.ndarray, color) -> None:
    """rgb (H,W,3) の上に色を mask の重みで置く(in place)。"""
    c = np.asarray(color, np.float64)
    rgb[:] = rgb * (1.0 - mask[..., None]) + c * mask[..., None]


def _person(H: int, W: int, cu: float, cv: float, h: float) -> np.ndarray:
    """歩く人の単純な人型(頭 = 円、体 = 台形、脚 = 2 本の線)。高さ h [px]、足元が (cu, cv + h/2)。"""
    top = cv - h / 2.0
    m = _disk(H, W, cu, top + 0.10 * h, 0.09 * h)
    m = np.maximum(m, _poly(H, W, [(cu - 0.10 * h, top + 0.22 * h), (cu + 0.10 * h, top + 0.22 * h),
                                   (cu + 0.15 * h, top + 0.58 * h), (cu - 0.15 * h, top + 0.58 * h)]))
    m = np.maximum(m, _segment(H, W, (cu - 0.03 * h, top + 0.56 * h), (cu - 0.20 * h, top + 0.98 * h), 0.09 * h))
    m = np.maximum(m, _segment(H, W, (cu + 0.03 * h, top + 0.56 * h), (cu + 0.18 * h, top + 0.98 * h), 0.09 * h))
    return m


def sign_image(kind: str, *, size_px: int = 128, value=None, font_path=None, side: float | None = None) -> np.ndarray:
    """標識の絵を RGBA float (H, W, 4) ∈ [0,1] で返す(板の外 = alpha 0)。幅 = ``size_px``、高さは形の比。

    形と色(規格の配色、記号は単純化):
      * stop: 逆三角形・赤地・白の「止まれ」+ 下に小さく「STOP」。 slow: 逆三角形・白地・赤枠・青の「徐行」+「SLOW」。
      * speed_limit: 円・白地・赤枠・青の数字(``value``、既定 40)。 no_entry: 円・赤地・白の横棒。
      * no_parking: 円・青地・赤枠・赤の斜線(左上→右下)。 one_way: 横長の青地に白の矢印(右向き)。
      * crosswalk: 青地の五角形(家型)に白の歩行者と横断歩道の縞。
      * caution_crossing / caution_signal / caution_children: 黄地の菱形・黒縁、黒の記号
        (踏切 = 遮断機の棒 2 本と ×、信号機 = 3 つの円(赤黄青)、学童 = 2 人の人型)。
    文字は PIL でラスタ化する(annotate と同じフォント探索。``font_path`` で固定できる)。**フォントに字形が無ければ
    ValueError**(豆腐を黙って出さない)。``side`` は :func:`sign_params` と同じ(寸法比だけに効く)。"""
    _check_kind(kind)
    size_px = int(size_px)
    if size_px < 16:
        raise ValueError("size_px は 16 以上")
    p = sign_params(kind, side=side)
    W = size_px
    H = max(8, round(size_px * p["height"] / p["width"]))
    shape = p["shape"]
    alpha = _shape_mask(shape, H, W)
    rgb = np.empty((H, W, 3), np.float64)
    rgb[:] = p["ground"]
    if p["border"] is not None:
        bw = 0.09 * W if shape != "diamond" else 0.05 * W
        inner = _shape_mask(shape, H, W, inset=bw)
        _paint(rgb, np.clip(alpha - inner, 0, 1), p["border"])
    ink = p["ink"]
    if kind == "stop":
        _paint(rgb, _text_mask(H, W, "止まれ", W / 2, 0.26 * H, int(0.23 * W), font_path), ink)
        _paint(rgb, _text_mask(H, W, "STOP", W / 2, 0.52 * H, int(0.10 * W), font_path), ink)
    elif kind == "slow":
        _paint(rgb, _text_mask(H, W, "徐行", W / 2, 0.36 * H, int(0.22 * W), font_path), ink)
        _paint(rgb, _text_mask(H, W, "SLOW", W / 2, 0.60 * H, int(0.09 * W), font_path), ink)
    elif kind == "speed_limit":
        v = 40 if value is None else int(value)
        if v <= 0:
            raise ValueError("speed_limit の value は正の整数")
        _paint(rgb, _text_mask(H, W, str(v), W / 2, H / 2, int(0.42 * W), font_path), ink)
    elif kind == "no_entry":
        _paint(rgb, _poly(H, W, [(0.18 * W, 0.42 * H), (0.82 * W, 0.42 * H), (0.82 * W, 0.58 * H), (0.18 * W, 0.58 * H)]), ink)
    elif kind == "no_parking":
        _paint(rgb, _segment(H, W, (0.19 * W, 0.19 * H), (0.81 * W, 0.81 * H), 0.10 * W), ink)
    elif kind == "one_way":
        shaft = _poly(H, W, [(0.12 * W, 0.40 * H), (0.62 * W, 0.40 * H), (0.62 * W, 0.60 * H), (0.12 * W, 0.60 * H)])
        head = _poly(H, W, [(0.60 * W, 0.16 * H), (0.90 * W, 0.50 * H), (0.60 * W, 0.84 * H)])
        _paint(rgb, np.maximum(shaft, head), ink)
    elif kind == "crosswalk":
        stripes = np.zeros((H, W))
        for k in range(5):
            u0 = 0.14 * W + k * 0.16 * W
            stripes = np.maximum(stripes, _poly(H, W, [(u0, 0.80 * H), (u0 + 0.08 * W, 0.80 * H),
                                                       (u0 + 0.08 * W, 0.92 * H), (u0, 0.92 * H)]))
        _paint(rgb, np.maximum(stripes, _person(H, W, 0.50 * W, 0.53 * H, 0.50 * H)), ink)
    elif kind == "caution_crossing":
        m = np.maximum(_segment(H, W, (0.28 * W, 0.62 * H), (0.66 * W, 0.40 * H), 0.05 * W),
                       _segment(H, W, (0.34 * W, 0.72 * H), (0.72 * W, 0.50 * H), 0.05 * W))
        m = np.maximum(m, _segment(H, W, (0.24 * W, 0.62 * H), (0.24 * W, 0.78 * H), 0.05 * W))
        m = np.maximum(m, _segment(H, W, (0.38 * W, 0.28 * H), (0.62 * W, 0.44 * H), 0.05 * W))
        m = np.maximum(m, _segment(H, W, (0.62 * W, 0.28 * H), (0.38 * W, 0.44 * H), 0.05 * W))
        _paint(rgb, m, ink)
    elif kind == "caution_signal":
        _paint(rgb, _poly(H, W, [(0.24 * W, 0.42 * H), (0.76 * W, 0.42 * H), (0.76 * W, 0.58 * H), (0.24 * W, 0.58 * H)]), ink)
        for cu, col in ((0.34, "green"), (0.50, "yellow"), (0.66, "red")):
            _paint(rgb, _disk(H, W, cu * W, 0.50 * H, 0.06 * W), DW._LAMP[col] if col != "yellow" else SIGN_COLORS["yellow"])
    elif kind == "caution_children":
        _paint(rgb, np.maximum(_person(H, W, 0.42 * W, 0.50 * H, 0.42 * H), _person(H, W, 0.60 * W, 0.53 * H, 0.34 * H)), ink)
    out = np.empty((H, W, 4), np.float64)
    out[..., :3] = np.clip(rgb, 0, 1)
    out[..., 3] = np.clip(alpha, 0, 1)
    return out


# ─────────────────────────────── 板メッシュ ───────────────────────────────────

def plate_mesh_from_image(rgba, width: float, height: float, *, cell: int = 4, thickness: float = 0.004,
                          back_color=(0.55, 0.55, 0.55), label: int = 4) -> dict:
    """RGBA 画像を、面の色を持つ薄い板のメッシュにする。

    画像を ``cell × cell`` 画素の区画に切り、alpha の平均が 0.5 以上の区画だけを面にする(2 三角形)。面の色 =
    その区画の alpha で重みづけた平均色 ``Σ(α·rgb) / Σα``。表面の法線 = **−x**(yaw 0 で +x へ進んで来る車に向く)、
    裏面は同じ形で ``back_color``(法線 +x)。原点 = 板の中心、板は y-z 平面(画像の左 = +y、上 = +z)、
    厚さ ``thickness`` を x の ±半分に振る。使われない頂点は残さない(寸法を頂点から測れるように)。

    返り値 ``{"V", "F", "color", "label", "front_faces": (0, n), "back_faces": (n, 2n), "cells": (rows, cols)}``。"""
    A = np.asarray(rgba, np.float64)
    if A.ndim != 3 or A.shape[2] != 4:
        raise ValueError("rgba は (H, W, 4)")
    if not np.all(np.isfinite(A)):
        raise ValueError("rgba に非有限がある")
    width, height, thickness = float(width), float(height), float(thickness)
    cell = int(cell)
    if not (width > 0 and height > 0 and thickness > 0 and cell >= 1):
        raise ValueError("width・height・thickness は正、cell は 1 以上")
    H, W = A.shape[:2]
    rows, cols = -(-H // cell), -(-W // cell)
    sx, sy = width / W, height / H
    Vf, Ff, Cf = [], [], []
    vid = {}

    def vert(r, c, side):
        key = (r, c, side)
        if key not in vid:
            vid[key] = len(Vf)
            y = width / 2.0 - min(c * cell, W) * sx
            z = height / 2.0 - min(r * cell, H) * sy
            Vf.append((side * thickness / 2.0, y, z))
        return vid[key]

    front, back = [], []
    for r in range(rows):
        for c in range(cols):
            blk = A[r * cell:(r + 1) * cell, c * cell:(c + 1) * cell]
            a = blk[..., 3]
            if a.mean() < 0.5:
                continue
            col = (blk[..., :3] * a[..., None]).sum(axis=(0, 1)) / a.sum()
            tl, tr, br, bl = (r, c), (r, c + 1), (r + 1, c + 1), (r + 1, c)
            f = [vert(*tl, -1), vert(*tr, -1), vert(*br, -1), vert(*bl, -1)]
            front.append(([f[0], f[2], f[1]], [f[0], f[3], f[2]], col))
            b = [vert(*tl, 1), vert(*tr, 1), vert(*br, 1), vert(*bl, 1)]
            back.append(([b[0], b[1], b[2]], [b[0], b[2], b[3]]))
    for t0, t1, col in front:
        Ff += [t0, t1]
        Cf += [col, col]
    n_front = len(Ff)
    for t0, t1 in back:
        Ff += [t0, t1]
        Cf += [back_color, back_color]
    V = np.asarray(Vf, np.float64).reshape(-1, 3)
    F = np.asarray(Ff, np.int64).reshape(-1, 3)
    C = np.asarray(Cf, np.float64).reshape(-1, 3)
    return {"V": V, "F": F, "color": C, "label": int(label), "front_faces": (0, n_front),
            "back_faces": (n_front, len(F)), "cells": (rows, cols)}


def sign_mesh(kind: str, *, value=None, cell: int = 4, size_px: int = 128, font_path=None, side: float | None = None) -> dict:
    """:func:`sign_image` + :func:`sign_params` + :func:`plate_mesh_from_image`。返り値に ``width``・``height``・``params`` を足す。"""
    p = sign_params(kind, side=side)
    img = sign_image(kind, size_px=size_px, value=value, font_path=font_path, side=side)
    m = plate_mesh_from_image(img, p["width"], p["height"], cell=cell)
    m.update({"width": p["width"], "height": p["height"], "params": p, "kind": kind})
    return m


def _cylinder(radius: float, z0: float, z1: float, n: int = 16, axis=None) -> tuple:
    """z 軸に沿う円柱(側面 + 両端)。``axis`` を渡すと (原点, 単位方向) の軸に沿わせる。返り値 (V, F)。"""
    ang = np.linspace(0, 2 * np.pi, n, endpoint=False)
    ring = np.stack([radius * np.cos(ang), radius * np.sin(ang)], axis=1)
    V = [(*q, z0) for q in ring] + [(*q, z1) for q in ring] + [(0.0, 0.0, z0), (0.0, 0.0, z1)]
    F = []
    for k in range(n):
        a, b = k, (k + 1) % n
        F += [[a, b, n + b], [a, n + b, n + a]]                 # 側面(外向き)
        F += [[2 * n, b, a], [2 * n + 1, n + a, n + b]]       # 底(−z)・天(+z)
    V, F = np.asarray(V, np.float64), np.asarray(F, np.int64)
    if axis is not None:
        o, d = np.asarray(axis[0], np.float64), np.asarray(axis[1], np.float64)
        d = d / np.linalg.norm(d)
        u = np.cross(d, [0.0, 0.0, 1.0])
        if np.linalg.norm(u) < 1e-9:
            u = np.array([1.0, 0.0, 0.0])
        u /= np.linalg.norm(u)
        w = np.cross(d, u)
        V = V[:, 0:1] * u + V[:, 1:2] * w + V[:, 2:3] * d + o
    return V, F


def _box(x0, x1, y0, y1, z0, z1) -> tuple:
    """軸に沿う箱(8 頂点・12 三角形、法線は外向き)。返り値 (V, F)。"""
    V = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
                  [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]], np.float64)
    F = np.array([[0, 2, 1], [0, 3, 2],        # 底 −z
                  [4, 5, 6], [4, 6, 7],        # 天 +z
                  [0, 1, 5], [0, 5, 4],        # −y
                  [2, 3, 7], [2, 7, 6],        # +y
                  [1, 2, 6], [1, 6, 5],        # +x
                  [3, 0, 4], [3, 4, 7]],       # −x
                 np.int64)
    return V, F


def _merge(parts) -> tuple:
    """[(V, F, color(3,) or (M,3)), ...] を 1 束に。返り値 (V, F, C)。"""
    Vs, Fs, Cs = [], [], []
    off = 0
    for V, F, C in parts:
        C = np.asarray(C, np.float64)
        if C.ndim == 1:
            C = np.broadcast_to(C, (len(F), 3))
        Vs.append(V)
        Fs.append(np.asarray(F, np.int64) + off)
        Cs.append(C)
        off += len(V)
    return np.vstack(Vs), np.vstack(Fs), np.vstack(Cs)


def add_sign(world: dict, kind: str, x: float, y: float, yaw: float, *, value=None, mount_height: float | None = None,
             pole_radius: float = 0.03, cell: int = 4, size_px: int = 128, font_path=None, side: float | None = None) -> int:
    """路側式の標識を立てる: 柱(円柱、灰、ラベル 6)+ 板(下端 = ``mount_height``、既定 1.8 m、ラベル 4)。

    規約: **yaw の向きへ進んで来る車に板の面が向く**(法線 = (−cos yaw, −sin yaw))。実装は :func:`sign_mesh`(法線 −x)を
    :func:`driveworld.place_mesh` で回すだけ。板は柱の手前(車の側)に ``pole_radius + 1 cm`` 離して付ける。
    返り値 = 板の object 索引(``extra = {"kind", "value", "width", "height", "mount_height"}``)。柱は直前の別 object。"""
    _check_kind(kind)
    pole_radius = float(pole_radius)
    if not (pole_radius > 0):
        raise ValueError("pole_radius は正")
    m = sign_mesh(kind, value=value, cell=cell, size_px=size_px, font_path=font_path, side=side)
    mh = MOUNT_HEIGHT if mount_height is None else float(mount_height)
    if not (mh >= 0) or not math.isfinite(mh):
        raise ValueError("mount_height は 0 以上の有限値")
    top = mh + m["height"]
    Vp, Fp = _cylinder(pole_radius, 0.0, top + 0.02, 12)
    world_add = DW.world_add
    world_add(world, DW.place_mesh(Vp, x, y, yaw), Fp, 6, _POLE, name="sign_pole:%s" % kind, pose=(x, y, yaw))
    Vb = m["V"] + np.array([-(pole_radius + 0.01 + 0.002), 0.0, mh + m["height"] / 2.0])
    return world_add(world, DW.place_mesh(Vb, x, y, yaw), m["F"], 4, m["color"], name="sign:%s" % kind, pose=(x, y, yaw),
                     extra={"kind": kind, "value": value, "width": m["width"], "height": m["height"], "mount_height": mh,
                            "front_faces": m["front_faces"]})


# ─────────────────────────────── 信号灯器 ─────────────────────────────────────

_LAMP_NAMES = {3: ("green", "yellow", "red"), 2: ("yellow", "red"), 1: ("yellow",)}


def signal_jp_mesh(*, lens: float = LENS_DIAMETER, n: int = 3, hood: bool = True, state: str = "off") -> dict:
    """横型の車両用灯器(日本式)。原点 = 灯器の底面の中心、表示面は −x を向く。

    箱: 幅 = n·(lens + 0.10) + 0.05(3 灯・300 mm で 1.25 m)、高さ = lens + 0.13(0.43 m)、奥行 0.30 m、濃い灰。
    レンズ = 半径 lens/2 の円盤(24 分割)を前面より 5 mm 外(−x 側)に置く。並びは **−x を向いて見て左から 青・黄・赤**
    = 青が +y、赤が −y(運転者から見て左から青・黄・赤 — Wikipedia 日本の交通信号機、一次資料で要確認)。
    n = 2 なら 黄・赤、n = 1 なら 黄(一灯点滅式)。各レンズの上に庇(薄い箱、長さ 0.25 m、``hood``)。
    レンズ径は 300 mm(2017 年度から標準 250 mm、どちらも現役)。

    返り値 ``{"V", "F", "color", "label": 3, "lamp_faces": {"green": (f0, f1), ...}, "width", "height", "depth", "lens"}``。
    ``lamp_faces`` はこのメッシュ内の面の索引の範囲(世界に足すときは world_add の返す範囲へ平行移動する —
    :func:`driveworld.add_signal` と同じ仕組み)。``state`` の灯だけ driveworld._LAMP の色、他は "off" の色。"""
    lens = float(lens)
    if not (lens > 0) or not math.isfinite(lens):
        raise ValueError("lens(レンズ径 [m])は正の有限値")
    if n not in _LAMP_NAMES:
        raise ValueError("n は 1 / 2 / 3")
    if state not in ("red", "yellow", "green", "off"):
        raise ValueError("state は red / yellow / green / off")
    pitch = lens + 0.10
    width, height, depth = n * pitch + 0.05, lens + 0.13, 0.30
    parts = []
    Vb, Fb = _box(-depth / 2, depth / 2, -width / 2, width / 2, 0.0, height)
    parts.append((Vb, Fb, _HOUSING))
    n_seg = 24
    ang = np.linspace(0, 2 * np.pi, n_seg, endpoint=False)
    r = lens / 2.0
    xf = -depth / 2 - 0.005
    zc = height / 2.0
    lamp_faces = {}
    nf = len(Fb)
    names = _LAMP_NAMES[n]
    for k, name in enumerate(names):
        yc = (n - 1) / 2.0 * pitch - k * pitch
        c = np.array([xf, yc, zc])
        Vd = np.vstack([c, c + np.stack([np.zeros(n_seg), r * np.cos(ang), r * np.sin(ang)], axis=1)])
        Fd = np.array([[0, 1 + (k2 + 1) % n_seg, 1 + k2] for k2 in range(n_seg)], np.int64)   # 法線 −x
        col = DW._LAMP[name] if name == state else DW._LAMP["off"]
        parts.append((Vd, Fd, col))
        lamp_faces[name] = (nf, nf + n_seg)
        nf += n_seg
        if hood:
            Vh, Fh = _box(-depth / 2 - 0.25, -depth / 2, yc - r - 0.02, yc + r + 0.02, zc + r + 0.01, zc + r + 0.02)
            parts.append((Vh, Fh, _HOUSING))
            nf += len(Fh)
    V, F, C = _merge(parts)
    return {"V": V, "F": F, "color": C, "label": 3, "lamp_faces": lamp_faces, "width": width, "height": height,
            "depth": depth, "lens": lens, "state": state}


def add_signal_jp(world: dict, x: float, y: float, yaw: float, *, state: str = "red", arm: float = 2.0,
                  lamp_bottom: float = 5.0, pole_radius: float = 0.08, arm_side: str = "left", lens: float = LENS_DIAMETER,
                  hood: bool = True) -> int:
    """日本式の信号機を立てる: 柱 + 水平アーム + 灯器(横型 3 灯、yaw の向きへ進んで来る車に表示面が向く)。

    配置(信号機設置の指針の解説: 一般の車両用灯器は交差点の向こう側 = 出口側): 柱を (x, y) に立て
    (高さ lamp_bottom + 0.7)、アームを進入車の運転者から見て **右**(車線の上。yaw 0 で −y)へ水平に ``arm`` だけ出し
    (標準 2.0 m、最大 3.5 m 超は ValueError)、灯器の中心をアームの先に吊る(灯器の底 = ``lamp_bottom``、
    既定 5.0 m、4.5 m 未満は ValueError — 交通信号機工事仕様書、一次資料で要確認)。``arm_side="right"`` なら柱が
    運転者の右側にあり、アームは左へ出る。表示面の法線 = (−cos yaw, −sin yaw)、レンズは運転者から見て左から青・黄・赤。

    objects: 柱 + アーム(ラベル 3、name "signal_pole")と灯器(ラベル 3、name "traffic_light"、
    ``extra = {"state", "lamp_faces"(世界の面索引), "arm", "lamp_bottom", "kind": "jp"}``)。返り値 = 灯器の索引
    (:func:`driveworld.set_signal_state` はこれに対して使う)。"""
    if state not in ("red", "yellow", "green", "off"):
        raise ValueError("state は red / yellow / green / off")
    arm, lamp_bottom, pole_radius = float(arm), float(lamp_bottom), float(pole_radius)
    if not (0.0 < arm <= ARM_MAX):
        raise ValueError("arm は 0 < arm <= %.1f m(公表値: 最大 3.5 m)" % ARM_MAX)
    if not (lamp_bottom >= LAMP_BOTTOM_MIN) or not math.isfinite(lamp_bottom):
        raise ValueError("lamp_bottom は %.1f m 以上(公表値: 路面から灯器下端まで 4.5 m 以上)" % LAMP_BOTTOM_MIN)
    if not (pole_radius > 0):
        raise ValueError("pole_radius は正")
    if arm_side not in ("left", "right"):
        raise ValueError("arm_side は left / right")
    head = signal_jp_mesh(lens=lens, n=3, hood=hood, state=state)
    sgn = -1.0 if arm_side == "left" else 1.0              # アームの向き(局所 y): 柱が左 → 右(−y)へ
    z_top = head["height"]
    arm_r = 0.05
    z_arm = lamp_bottom + z_top + 0.05 + arm_r
    pole_top = max(lamp_bottom + 0.7, z_arm + 0.15)
    Vp, Fp = _cylinder(pole_radius, 0.0, pole_top, 16)
    Va, Fa = _cylinder(arm_r, 0.0, arm, 12, axis=((0.0, 0.0, z_arm), (0.0, sgn, 0.0)))
    Vh, Fh = _box(-0.03, 0.03, min(sgn * arm, sgn * (arm - 0.06)), max(sgn * arm, sgn * (arm - 0.06)),
                  lamp_bottom + z_top, z_arm)                                                  # 吊り金具(アームの先の内側)
    V, F, C = _merge([(Vp, Fp, _POLE), (Va, Fa, _POLE), (Vh, Fh, _HOUSING)])
    DW.world_add(world, DW.place_mesh(V, x, y, yaw), F, 3, C, name="signal_pole", pose=(x, y, yaw),
                 extra={"arm": arm, "arm_side": arm_side})
    Vhd = head["V"] + np.array([0.0, sgn * arm, lamp_bottom])
    i = DW.world_add(world, DW.place_mesh(Vhd, x, y, yaw), head["F"], 3, head["color"], name="traffic_light",
                     pose=(x, y, yaw), extra={"state": state, "lamp_faces": {}, "arm": arm, "lamp_bottom": lamp_bottom,
                                             "kind": "jp", "lens": float(lens)})
    f0 = world["objects"][i]["faces"][0]
    world["objects"][i]["lamp_faces"] = {k: (f0 + a, f0 + b) for k, (a, b) in head["lamp_faces"].items()}
    return i
