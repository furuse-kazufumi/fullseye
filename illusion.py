# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""illusion —— 錯視図形の生成と、**その図が否定している厳密な不変量**。

動機(2026-09-23)は著者の要望「錯視画像とかぱっと作れるような op も用意して
みて」。ただしこの族が本当にこの repo に属するのは、装飾だからではない ——
**錯視は「見た目は確かめの役に立たない」の反例ではなく、その最も純粋な実例**
だからである。カフェウォールの目地は**厳密に平行**で、ミュラー・リヤーの軸は
**厳密に等長**で、チェッカーシャドウの 2 マスは**厳密に同じ画素値**を持つ。
見えているものが違う、というだけ。

だからこの族の採用基準(「定理が門になるか、既存の別実装が真値になるか」)は
自然に満たされる。**各生成器は、自分が守っている不変量を数として返せる**
(:func:`illusion_ground_truth`)。図と真値が同じ op から出るので、

    1. 生成器が不変量を本当に守っているか(画像を測って確かめる)
    2. 測る側(既存の計測 op)がその不変量を回復できるか

の 2 つを門にできる。**「きれいに見えるから確かめない」を、機械が確かめる。**

★設計の中心: 返すのは ``rgb``(H,W,3、[0,1] の float)だけで、新しい型語は
足さない。錯視は「特別な画像」ではなく**ただの画像**であり、既存の 2,147 op が
そのまま掛かることに意味がある(測る側が錯視を知らないまま測れる、が芯)。

★反エイリアスは**陰関数の被覆率**で入れる(``gfx2d.sprite_synthesize`` と同じ
物差し)。ただし**平坦な領域の値は一切触らない** —— チェッカーシャドウや
同時対比の門は「2 つのパッチが厳密に同値」なので、そこへ縁の混色が混ざると
**門が甘くなるのではなく、門が嘘になる**。パッチの中心から測る、ではなく、
**パッチを平坦に作る**ことで守る。

使い方::

    import illusion
    img = illusion.illusion_cafe_wall()            # (H,W,3)
    gt = illusion.illusion_ground_truth("cafe_wall")
    gt["quantity"], gt["value"]                    # 目が否定している量と、その真値
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "illusion_cafe_wall",
    "illusion_muller_lyer",
    "illusion_ebbinghaus",
    "illusion_checker_shadow",
    "illusion_hermann_grid",
    "illusion_scintillating_grid",
    "illusion_kanizsa",
    "illusion_zollner",
    "illusion_fraser_spiral",
    "illusion_poggendorff",
    "illusion_ponzo",
    "illusion_simultaneous_contrast",
    "illusion_ground_truth",
    "ILLUSIONS",
    "CHECKER_PATCHES",
]


# --------------------------------------------------------------------------- #
# 下請け —— 陰関数の被覆率で描く(線も円も「符号つき距離 < 0」の面積)             #
# --------------------------------------------------------------------------- #
def _grid(h, w):
    """画素**中心**の座標 (y, x)。左上画素の中心が (0.5, 0.5)。"""
    y = np.arange(h, dtype=np.float64)[:, None] + 0.5
    x = np.arange(w, dtype=np.float64)[None, :] + 0.5
    return y, x


def _coverage(sdf, aa=1.0):
    """符号つき距離 → 被覆率 [0,1]。``aa=0`` で**反エイリアスなし**(硬い縁)。

    ★平坦であることが門になっている図(チェッカーシャドウ・同時対比)では
    ``aa=0`` を使う。縁の混色は「2 マスが厳密に同値」という主張を壊す。
    """
    if aa <= 0.0:
        return (sdf < 0.0).astype(np.float64)
    return np.clip(0.5 - sdf / aa, 0.0, 1.0)


def _sdf_disc(y, x, cy, cx, r):
    return np.hypot(y - cy, x - cx) - r


def _sdf_segment(y, x, y0, x0, y1, x1, half):
    """太さ ``2*half`` の線分の符号つき距離。"""
    dy, dx = y1 - y0, x1 - x0
    L2 = dy * dy + dx * dx
    if L2 < 1e-12:
        return np.hypot(y - y0, x - x0) - half
    t = np.clip(((y - y0) * dy + (x - x0) * dx) / L2, 0.0, 1.0)
    return np.hypot(y - (y0 + t * dy), x - (x0 + t * dx)) - half


def _paint(img, cov, colour):
    """被覆率で色を載せる(ストレート α の合成、下地を壊さない)。"""
    c = np.asarray(colour, dtype=np.float64).reshape(1, 1, 3)
    a = cov[..., None]
    return img * (1.0 - a) + c * a


def _canvas(h, w, value):
    return np.full((h, w, 3), float(value), dtype=np.float64)


def _bbox(shape, lo_y, hi_y, lo_x, hi_x):
    """描く図形の**外接箱**だけを返す(全画面の距離場を作らない)。

    ★これは速度のためだけの工夫ではない: 1 枚の錯視図は線分を数百本使うので、
    素朴に全画面の距離場を毎回作ると 520x520 で 1 枚 1.5 秒かかる。PoC の
    所要時間は CI の合否そのものなので、ここは配管の問題ではなく門の問題。
    """
    h, w = shape[:2]
    return (max(int(lo_y), 0), min(int(hi_y) + 1, h),
            max(int(lo_x), 0), min(int(hi_x) + 1, w))


def _local(shape, box):
    y0, y1, x0, x1 = box
    y = np.arange(y0, y1, dtype=np.float64)[:, None] + 0.5
    x = np.arange(x0, x1, dtype=np.float64)[None, :] + 0.5
    return y, x


def _blend(img, box, cov, colour):
    y0, y1, x0, x1 = box
    if y0 >= y1 or x0 >= x1:
        return img
    a = cov[..., None]
    c = np.asarray(colour, np.float64).reshape(1, 1, 3)
    img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1.0 - a) + c * a
    return img


def _seg(img, y0, x0, y1, x1, half, colour, aa=1.0):
    box = _bbox(img.shape, min(y0, y1) - half - 2, max(y0, y1) + half + 2,
                min(x0, x1) - half - 2, max(x0, x1) + half + 2)
    y, x = _local(img.shape, box)
    return _blend(img, box, _coverage(_sdf_segment(y, x, y0, x0, y1, x1, half), aa),
                  colour)


def _disc(img, cy, cx, r, colour, aa=1.0):
    box = _bbox(img.shape, cy - r - 2, cy + r + 2, cx - r - 2, cx + r + 2)
    y, x = _local(img.shape, box)
    return _blend(img, box, _coverage(_sdf_disc(y, x, cy, cx, r), aa), colour)


# --------------------------------------------------------------------------- #
# 幾何の錯視 —— 「厳密に平行 / 等長 / 共線 / 同心」を目が否定する                  #
# --------------------------------------------------------------------------- #
def illusion_cafe_wall(size: int = 40, rows: int = 8, cols: int = 10,
                       mortar: float = 2.0, shift: float = 0.5) -> np.ndarray:
    """カフェウォール錯視。**目地は厳密な水平線**なのに、傾いて見える。

    ``shift`` は 1 行ごとの市松のずれ(``size`` 比)。ずれが 0 または 0.5 では
    錯視は消える —— **0.25 前後が最も強い**というのが古典的な観察で、この op は
    そのままずらし量を振れるようにしてある(``shift=0.25`` が既定ではないのは、
    生成器の既定値で「効果が最大」を主張したくないため)。

    不変量: 目地の中心 y は ``k * size``(k = 1..rows-1)**ちょうど**。
    """
    h, w = rows * size, cols * size
    img = _canvas(h, w, 0.5)
    for r in range(rows):
        off = (r * shift * size) % (2 * size)
        for c in range(-1, cols + 1):
            x0 = c * 2 * size + off
            img[r * size:(r + 1) * size,
                max(int(round(x0)), 0):max(int(round(x0 + size)), 0)] = 0.0
            img[r * size:(r + 1) * size,
                max(int(round(x0 + size)), 0):max(int(round(x0 + 2 * size)), 0)] = 1.0
    if mortar > 0.0:
        half = 0.5 * mortar
        for k in range(1, rows):
            y0 = max(int(round(k * size - half)), 0)
            y1 = min(int(round(k * size + half)), h)
            img[y0:y1, :] = 0.5
    return img


def illusion_muller_lyer(length: float = 220.0, head: float = 34.0,
                         angle_deg: float = 35.0) -> np.ndarray:
    """ミュラー・リヤー錯視。**2 本の軸は厳密に等長**。

    不変量: どちらの軸も長さ ``length``(浮動小数の同一値)。
    """
    h, w = 260, int(length + 4 * head + 60)
    img = _canvas(h, w, 1.0)
    cx = w * 0.5
    a = np.deg2rad(angle_deg)
    for i, outward in enumerate((True, False)):
        cy = 80.0 + i * 100.0
        x0, x1 = cx - 0.5 * length, cx + 0.5 * length
        img = _seg(img, cy, x0, cy, x1, 1.6, (0.1, 0.1, 0.12))
        s = 1.0 if outward else -1.0
        for xe, d in ((x0, +1.0), (x1, -1.0)):
            for sgn in (+1.0, -1.0):
                img = _seg(img, cy, xe,
                           cy + sgn * head * np.sin(a),
                           xe + s * d * head * np.cos(a), 1.6, (0.1, 0.1, 0.12))
    return img


def illusion_ponzo(bar: float = 150.0) -> np.ndarray:
    """ポンゾ錯視。**2 本の横棒は厳密に等長**(遠近の手がかりが長さを変える)。

    不変量: 上下の棒はどちらも長さ ``bar``。
    """
    h, w = 300, 360
    img = _canvas(h, w, 1.0)
    img = _seg(img, 20.0, w * 0.5 - 30.0, h - 20.0, 20.0, 1.4, (0.25, 0.25, 0.3))
    img = _seg(img, 20.0, w * 0.5 + 30.0, h - 20.0, w - 20.0, 1.4, (0.25, 0.25, 0.3))
    for cy in (90.0, 210.0):
        img = _seg(img, cy, w * 0.5 - 0.5 * bar, cy, w * 0.5 + 0.5 * bar,
                   2.4, (0.85, 0.25, 0.2))
    return img


def illusion_zollner(lines: int = 7, gap: float = 56.0,
                     hatch_deg: float = 38.0) -> np.ndarray:
    """ツェルナー錯視。**長い線は厳密に平行**なのに、収束して見える。

    不変量: 長い線はすべて傾き 0(水平)。
    """
    h, w = int(gap * (lines + 1)), 520
    img = _canvas(h, w, 1.0)
    a = np.deg2rad(hatch_deg)
    for i in range(1, lines + 1):
        cy = i * gap
        s = 1.0 if i % 2 else -1.0
        for x in np.arange(18.0, w - 18.0, 26.0):
            img = _seg(img, cy - s * 13.0 * np.sin(a), x - 13.0 * np.cos(a),
                       cy + s * 13.0 * np.sin(a), x + 13.0 * np.cos(a),
                       1.3, (0.35, 0.45, 0.65))
        img = _seg(img, cy, 10.0, cy, w - 10.0, 2.0, (0.1, 0.1, 0.12))
    return img


def illusion_poggendorff(angle_deg: float = 30.0, bar: float = 90.0) -> np.ndarray:
    """ポッゲンドルフ錯視。**斜線は厳密に 1 本の直線**(帯で隠れているだけ)。

    不変量: 左右に見えている 2 本の線分は共線(同じ傾き・同じ切片)。
    """
    h, w = 300, 420
    img = _canvas(h, w, 1.0)
    cy, cx = h * 0.5, w * 0.5
    m = np.tan(np.deg2rad(angle_deg))
    x0, x1 = 30.0, w - 30.0
    for xa, xb in ((x0, cx - 0.5 * bar), (cx + 0.5 * bar, x1)):
        img = _seg(img, cy + m * (xa - cx), xa, cy + m * (xb - cx), xb,
                   2.0, (0.1, 0.1, 0.12))
    img[:, int(cx - 0.5 * bar):int(cx + 0.5 * bar)] = 0.82
    for xv in (cx - 0.5 * bar, cx + 0.5 * bar):
        img = _seg(img, 20.0, xv, h - 20.0, xv, 1.4, (0.3, 0.3, 0.35))
    return img


def illusion_fraser_spiral(rings: int = 7, tilt_deg: float = 22.0,
                           size: int = 520) -> np.ndarray:
    """フレーザー錯視。**渦に見えるが、実体は同心円**。

    不変量: どの環も半径が一定(渦なら半径は角度とともに増える)。
    """
    img = _canvas(size, size, 0.5)
    cy = cx = size * 0.5
    a = np.deg2rad(tilt_deg)
    for k in range(1, rings + 1):
        r = size * 0.5 * k / (rings + 1)
        n = max(int(2 * np.pi * r / 13.0), 12)
        for j in range(n):
            th = 2 * np.pi * j / n
            uy, ux = np.sin(th), np.cos(th)          # 半径方向
            ty, tx = np.cos(th), -np.sin(th)         # 接線方向
            dy = 7.0 * (np.cos(a) * ty + np.sin(a) * uy)
            dx = 7.0 * (np.cos(a) * tx + np.sin(a) * ux)
            col = (1.0, 1.0, 1.0) if j % 2 else (0.0, 0.0, 0.0)
            img = _seg(img, cy + r * uy - dy, cx + r * ux - dx,
                       cy + r * uy + dy, cx + r * ux + dx, 2.6, col)
    return img


def illusion_ebbinghaus(radius: float = 30.0) -> np.ndarray:
    """エビングハウス錯視。**中央の 2 円は厳密に同じ半径**。

    不変量: 中央の 2 円はどちらも半径 ``radius``(= 面積も同じ)。
    """
    h, w = 340, 620
    img = _canvas(h, w, 1.0)
    # ★周りの円は**互いに重ならない**ように置く。n 個を半径 rs の環に並べるとき、
    #   隣どうしの中心間距離は 2*rs*sin(pi/n) なので rs > rr / sin(pi/n) が要る。
    #   最初これを守らずに (rs=62, rr=46, n=6) と置いたら、周りの円が融合して
    #   **花のような 1 つの塊**になった —— エビングハウス錯視になっていない。
    for i, (cx, rs, n, rr) in enumerate(((168.0, 108.0, 6, 46.0),
                                         (452.0, 54.0, 8, 15.0))):
        assert rs > rr / np.sin(np.pi / n) * 1.02, "周りの円が重なる"
        cy = h * 0.5
        for j in range(n):
            th = 2 * np.pi * j / n
            img = _disc(img, cy + rs * np.sin(th), cx + rs * np.cos(th), rr,
                        (0.72, 0.74, 0.78))
        img = _disc(img, cy, cx, radius, (0.85, 0.35, 0.25))
    return img


def illusion_kanizsa(radius: float = 54.0, size: int = 420) -> np.ndarray:
    """カニッツァの三角形。**輪郭は 1 本も描かれていない**のに三角形が見える。

    不変量: 錯覚輪郭の上では画像は**背景の定数**(勾配が厳密に 0)。
    """
    img = _canvas(size, size, 0.97)
    c = size * 0.5
    R = size * 0.30
    pts = [(c - R, c), (c + R * 0.5, c - R * np.sqrt(3) / 2),
           (c + R * 0.5, c + R * np.sqrt(3) / 2)]
    for (py, px) in pts:
        img = _disc(img, py, px, radius, (0.12, 0.12, 0.16))
    # 楔を背景色で抜く = パックマン。三角形の辺は**一度も描かない**。
    y, x = _grid(size, size)
    for i, (py, px) in enumerate(pts):
        oy, ox = c - py, c - px
        n = np.hypot(oy, ox)
        oy, ox = oy / n, ox / n
        perp_y, perp_x = -ox, oy
        d1 = (y - py) * oy + (x - px) * ox
        d2 = np.abs((y - py) * perp_y + (x - px) * perp_x)
        wedge = ((d1 > 0) & (d2 < d1 * np.tan(np.deg2rad(32.0)))).astype(np.float64)
        img = _paint(img, wedge * (np.hypot(y - py, x - px) < radius + 1.0), (0.97, 0.97, 0.97))
    return img


# --------------------------------------------------------------------------- #
# 明るさの錯視 —— 「厳密に同じ画素値」を目が否定する                               #
# --------------------------------------------------------------------------- #
#: チェッカーシャドウで「厳密に同値」になる 2 マス (row, col)。
#: 影の外の**暗**マスと、影の中の**明**マス。
CHECKER_PATCHES = ((2, 3), (5, 5))


def illusion_checker_shadow(size: int = 46, n: int = 8,
                            light: float = 0.62, dark: float = 0.31) -> np.ndarray:
    """チェッカーシャドウ。**印を付けた 2 マスは厳密に同じ画素値**。

    影の係数を ``dark / light`` に取ると、影の中の明マスは影の外の暗マスと
    **数として同じ**になる。★この図は ``aa=0``(反エイリアスなし)で描く ——
    縁の混色が入ると「厳密に同値」という主張のほうが嘘になるため。

    不変量: :data:`CHECKER_PATCHES` の 2 マス —— **影の外の暗マス** (2,3) と
    **影の中の明マス** (5,5) —— の画素値が完全に一致(差が厳密に 0)。

    ★ここは一度間違えた。対にすべきは「暗マス × 影なし」と「明マス × 影あり」で、
    同じ明暗のマスを 2 つ選んでも当然ながら一致しない(実測 0.31 の差が出た)。
    絵は「それらしく」見えてしまうので、**数で確かめるまで気づけない** ——
    この族が守ろうとしているのと同じ型の事故。
    """
    h = w = n * size
    img = np.zeros((h, w, 3), dtype=np.float64)
    base = np.empty((n, n), dtype=np.float64)
    for r in range(n):
        for c in range(n):
            base[r, c] = light if (r + c) % 2 == 0 else dark
    s = dark / light                                   # 影の係数(厳密)
    shade = np.ones((n, n), dtype=np.float64)
    for r in range(n):
        for c in range(n):
            if c >= 3 and r >= 3:                      # 影の四角い領域
                shade[r, c] = s
    val = base * shade
    for r in range(n):
        for c in range(n):
            img[r * size:(r + 1) * size, c * size:(c + 1) * size, :] = val[r, c]
    return img


def illusion_simultaneous_contrast(patch: int = 90, size: int = 320) -> np.ndarray:
    """同時対比。**2 つの灰色パッチは厳密に同じ値**(周りだけが違う)。

    不変量: 左右のパッチの画素値が完全に一致。
    """
    h, w = size, size * 2
    img = np.zeros((h, w, 3), dtype=np.float64)
    img[:, :w // 2, :] = 0.16
    img[:, w // 2:, :] = 0.84
    g = 0.5
    y0, y1 = (h - patch) // 2, (h - patch) // 2 + patch
    for cx in (w // 4, 3 * w // 4):
        img[y0:y1, cx - patch // 2:cx + patch // 2, :] = g
    return img


def illusion_hermann_grid(size: int = 44, n: int = 8,
                          bar: float = 12.0) -> np.ndarray:
    """ヘルマン格子。**交点は他の場所と厳密に同じ白**(黒い点は目が作る)。

    不変量: すべての交点の画素値が一致し、かつ帯の値と一致する。
    """
    h = w = (n + 1) * size
    img = _canvas(h, w, 0.0)
    for k in range(n + 1):
        c = k * size + size * 0.5
        img[:, int(c - bar * 0.5):int(c + bar * 0.5), :] = 1.0
        img[int(c - bar * 0.5):int(c + bar * 0.5), :, :] = 1.0
    return img


def illusion_scintillating_grid(size: int = 44, n: int = 8, bar: float = 12.0,
                                dot: float = 6.0) -> np.ndarray:
    """きらめき格子。ヘルマン格子の交点に白丸を置いたもの。

    不変量: すべての白丸が同一(半径も値も)。
    """
    img = illusion_hermann_grid(size=size, n=n, bar=bar)
    img *= 0.62                                        # 帯を灰色に落とす
    for r in range(n + 1):
        for c in range(n + 1):
            img = _disc(img, r * size + size * 0.5, c * size + size * 0.5,
                        dot, (1.0, 1.0, 1.0))
    return img


# --------------------------------------------------------------------------- #
# 真値 —— 各錯視が守っている不変量を、数として返す                                 #
# --------------------------------------------------------------------------- #
#: 錯視名 → (生成器, 目が否定している量, その真値の説明)
ILLUSIONS = {
    "cafe_wall": ("illusion_cafe_wall", "mortar_slope",
                  "目地の傾き(厳密に 0 —— 目地は水平線)"),
    "muller_lyer": ("illusion_muller_lyer", "shaft_length_difference",
                    "2 本の軸の長さの差(厳密に 0)"),
    "ponzo": ("illusion_ponzo", "bar_length_difference",
              "2 本の横棒の長さの差(厳密に 0)"),
    "zollner": ("illusion_zollner", "line_slope_spread",
                "長い線の傾きのばらつき(厳密に 0 —— すべて水平)"),
    "poggendorff": ("illusion_poggendorff", "collinearity_offset",
                    "左右の線分の食い違い(厳密に 0 —— 共線)"),
    "fraser_spiral": ("illusion_fraser_spiral", "ring_radius_variation",
                      "各環の半径の変動(厳密に 0 —— 同心円であって渦ではない)"),
    "ebbinghaus": ("illusion_ebbinghaus", "centre_radius_difference",
                   "中央 2 円の半径の差(厳密に 0)"),
    "kanizsa": ("illusion_kanizsa", "illusory_edge_gradient",
                "錯覚輪郭上の勾配(厳密に 0 —— 辺は描かれていない)"),
    "checker_shadow": ("illusion_checker_shadow", "patch_value_difference",
                       "影の外の暗マスと影の中の明マスの画素値の差(厳密に 0)"),
    "simultaneous_contrast": ("illusion_simultaneous_contrast",
                              "patch_value_difference",
                              "左右のパッチの画素値の差(厳密に 0)"),
    "hermann_grid": ("illusion_hermann_grid", "intersection_value_spread",
                     "交点の画素値のばらつき(厳密に 0)"),
    "scintillating_grid": ("illusion_scintillating_grid",
                           "intersection_value_spread",
                           "白丸の画素値のばらつき(厳密に 0)"),
}


def illusion_ground_truth(name: str = "") -> dict:
    """錯視が守っている**厳密な不変量**を表で返す(``name`` 空で全件)。

    ★これがこの族の芯。図だけを配ると「きれいだね」で終わるが、**図と一緒に
    真値が出てくる**と、測る側を採点できる。返り値の ``value`` はすべて
    「あるべき値」であって、測った値ではない(測るのは呼んだ側の仕事)。
    """
    keys = sorted(ILLUSIONS) if not name else [name]
    for k in keys:
        if k not in ILLUSIONS:
            raise ValueError("unknown illusion %r (known: %s)"
                             % (k, ", ".join(sorted(ILLUSIONS))))
    return {
        "name": np.array(keys, dtype=object),
        "generator": np.array([ILLUSIONS[k][0] for k in keys], dtype=object),
        "quantity": np.array([ILLUSIONS[k][1] for k in keys], dtype=object),
        "value": np.zeros(len(keys), dtype=np.float64),      # すべて「厳密に 0」
        "note": np.array([ILLUSIONS[k][2] for k in keys], dtype=object),
    }
