# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""変化検出は位置合わせ誤差でどう壊れるか —— 偽陽性はエッジの帯、しかも「しきい値の崖」つき。

2 時期の衛星・航空画像を引き算して「何が変わったか」を出す仕事です(森林伐採、
建物の新設、水域の拡大)。素朴な差分は**位置合わせが完璧なら**よく効きますが、
実際の画像対は必ずサブピクセルのずれと微小な回転、照明差を持っています。
そのとき壊れるのは「変化を見落とす」ほうではなく、**変化していないエッジが
全部「変化」として出る**ほうです。この PoC はその壊れ方を幾何で先に予測して
から測ります。

EXTEND: 実写に差し替えるなら :func:`render` の 2 枚(``t=1`` と ``t=2``)を
2 時期の正射画像に、:func:`truth_masks` を判読者の変化ポリゴン(**種類別**)に
置き換えます。位置合わせの「残留ずれ」は真値が要るので、実写では GCP
(地上基準点)を別に測っておくこと —— 5 節のグラフの横軸はそれです。
エッジ台帳 :func:`edge_inventory` は実写では作れないので、代わりに 2 節 (c) の
**勾配ヒストグラム法**(基準画像 1 枚から偽陽性面積を予測する)を使う。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. ★★**偽陽性は 0.35 px までは 1 画素も出ない、そこから崖**。ずれ 0.1〜0.3 px
   の偽陽性面積は **0 / 0 / 0 px**、0.5 px で 118 px、3 px で 4232 px。
   予想はエッジ総長(投影 1284 px)× ずれ量の比例則で、**そのままでは 3 px で
   実測の 0.9 倍**だが、崖の位置が説明できない。原因は PSF: 幅 σ の
   ぼけたエッジをずらした差分の高さは C·δ/(σ√2π) で、これがしきい値 τ を
   超える δ* = τσ√2π/C = **0.35 px**(最も強いエッジ C=0.50 で)—— 予測と
   実測(最初に偽陽性が出たのは 0.5 px、0.3 px ではゼロ)が一致した。
   PSF 込みの予測は 0.5〜3 px で実測の **0.67〜0.96 倍**。
2. ★**予測から漏れるのは樹冠テクスチャ**。森林の内側は「エッジ」を持たないが、
   樹冠の勾配 |∇I| が τ/δ を超える画素は差分に出る。ずれ 1.5 px での偽陽性
   の内訳: 人工物のエッジ帯 1187 px / 森林内部 758 px / その他 3 px。
   森林の分は基準画像の勾配ヒストグラムから予測できて(予測 1175 px)、
   足すと全体の予測は実測の 0.97 倍まで寄る。**エッジ総長だけでは
   テクスチャ地物の偽陽性は数えられない**。
3. ★**回転は中央が無傷で端だけ壊れる**。1 度の回転で偽陽性は中心から 32 px 以内
   0.4 % / 96 px 以遠 2.8 %。局所のずれは r·θ なので、崖の半径は r* = δ*/θ:
   0.5 度なら 40 px、1 度なら 20 px —— 実測の内側ビンは 0.5 度で 0.5 %、
   1 度で 0.4 %(まだゼロに近い)。**画像の隅で偽陽性が出る画像対は、
   平行移動ではなく回転を疑う**。
4. ★★**変化の種類ごとに壊れ方が違う**。ずれ+回転(1.3/−0.8 px、0.4 度)で
   検出率は 新設 0.88 / 伐採 0.44 / 水域 0.67。伐採は位置合わせが**完璧でも**
   0.49 —— 樹冠が消えた跡の平均輝度差は小さく、差分に出るのは樹冠 1 本ずつ
   の斑点で、面積では半分しか拾えない。水域は幅 4 px の環なので、ずれ 1 px
   で環の 1/4 が消える。**まとめた 1 つの IoU(0.20)にはこの内訳が無い**。
5. **位置合わせは 3 経路とも同じずれ(1.3/−0.8 px、0.4 度)を残留 0.05 px 以下
   まで戻す**(PIV 相互相関→剛体当てはめ 0.010 px、特徴点→RANSAC→Procrustes
   0.051 px、密な LK フロー→頑健当てはめ 0.010 px)。ただし★**唯一の位相相関
   経路は 3-D 用しかなく整数精度**で、残留 0.38 px、回転は戻せない。
   ★★残留ずれと偽陽性面積は**位置合わせ後も同じ崖の上に乗る**(5 節の図):
   残留 0.38 px は「ずれだけ」の掃引の 0.35〜0.5 px の間に落ちる。
6. ★**照明差は位置合わせでは直らない**。照明差だけ(利得 1.15、オフセット
   0.03)でずれ無しでも偽陽性は 1010 px(明るい屋根・道路が全部「変化」に
   なる)。線形の相対放射補正(利得・オフセットを当てはめる)で 0 px、
   ``histogram_match``(順位で分布を合わせる)でも 0 px。一方ずれだけ
   (照明差なし)は 1948 px —— **同じ「偽陽性」でも原因は対照群でしか分けられない**。
7. **変化の大きさの崖**。ずれ δ(対角)で一辺 s の新設物の検出率は
   (1 − δ/(s√2))² —— δ=1 px で s=2 は 0.09、s=4 は 0.67。予測との差は
   ±0.05 以内。オープニング(半径 1)で偽陽性の帯を消すと、**一辺 2 px 以下の
   変化は δ=0 でも消える**(検出率 0)。

【グラウンドトゥルース】
場面は**連続座標で評価できる閉形式**(矩形・線分・円は erf でぼかした
指示関数、樹冠はガウス、土壌は低周波の正弦)。時期 2 の画像は場面関数を
**回転・平行移動した座標で評価**して作るので、補間は一切入らず、ずれの真値は
機械精度。変化(新設・伐採・水域拡大)は時期 2 の場面関数の中だけで起き、
真値マスクは基準座標での硬い指示関数(画素中心が内側)。エッジ台帳は場面を
組んだ幾何そのもの(辺の長さ・法線・コントラスト)。

来歴(公開文献のみ): Singh, *Int. J. Remote Sensing* 13 (1992) 989 ——
変化検出手法の総説 / Dai & Khorram, *IEEE TGRS* 36 (1998) 1566 ——
位置合わせ誤差が変化検出に与える影響(0.2 px 以下を推奨) / Townshend et al.,
*IEEE TGRS* 30 (1992) 1054 —— 位置合わせ誤差と NDVI 差分 /
Westerweel & Scarano, *Exp. Fluids* 39 (2005) 1096 —— PIV の正規化中央値検定 /
Fischler & Bolles, *Comm. ACM* 24 (1981) 381 —— RANSAC / Hall et al.,
*Remote Sens. Environ.* 35 (1991) 11 —— 相対放射補正。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import affine_transform, binary_dilation
from scipy.special import erf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 場面の諸元 -------------------------------------------------------------- #
N = 256                    # 視野 [px]
PSF = 0.7                  # 光学系のぼけ σ [px](エッジは erf でぼける)
NOISE = 0.010              # 撮像雑音 σ(各時期に独立)
TAU = 0.10                 # 差分のしきい値(雑音差 σ√2 = 0.014 の 7 倍)
SOIL = 0.35                # 土壌の反射率
BORDER = 6                 # 評価から外す縁 [px](ワープの端を全条件で同じに扱う)
SEED = 7
CENTER = ((N - 1) / 2.0, (N - 1) / 2.0)

#: 地物(基準座標、行 y・列 x、半開でなく**閉区間の実数境界**)。
FIELDS = {                 # 畑: (y0, y1, x0, x1, 反射率)
    "F1": (15.0, 75.0, 10.0, 88.0, 0.55),
    "F2": (128.0, 165.0, 10.0, 70.0, 0.28),      # C=0.07 < τ: 見えない辺
    "F3": (175.0, 240.0, 30.0, 110.0, 0.48),
    "F5": (200.0, 240.0, 100.0, 140.0, 0.50),
}
FIELD_ROT = {"cy": 195.0, "cx": 195.0, "h": 45.0, "w": 70.0, "deg": 25.0, "alb": 0.60}
FOREST = (15.0, 105.0, 150.0, 245.0, 0.22)      # 樹冠が乗る地
N_CROWNS = 220
LAKE = {"cy": 62.0, "cx": 118.0, "r1": 22.0, "r2": 26.0, "alb": 0.08}
ROADS = {                  # 線分 (y0, x0, y1, x1)、幅 3 px、反射率 0.75
    "R1": (111.0, 0.0, 116.0, 255.0),
    "R2": (0.0, 145.0, 255.0, 150.0),
}
ROAD_W, ROAD_ALB = 3.0, 0.75
BUILD_ALB = 0.85
BUILDINGS = {              # 時期 1 から在る建物
    "B1": (130.0, 138.0, 104.0, 116.0), "B2": (142.0, 150.0, 122.0, 134.0),
    "B3": (156.0, 166.0, 104.0, 112.0), "B4": (160.0, 168.0, 126.0, 140.0),
    "B6": (86.0, 94.0, 12.0, 24.0), "B7": (96.0, 104.0, 40.0, 52.0),
    "B8": (88.0, 98.0, 70.0, 82.0),
}
#: 時期 2 の変化(種類別)。面積は真値マスクから数えて印字する。
NEW_BUILDINGS = {"NB1": (172.0, 182.0, 104.0, 118.0), "NB2": (99.0, 107.0, 14.0, 26.0),
                 "NB3": (180.0, 190.0, 122.0, 134.0)}
CLEARCUT = (45.0, 68.0, 175.0, 200.0)
CHANGE_TYPES = ("新設(建物)", "消失(伐採)", "水域拡大")

#: 変化の大きさの掃引(別場面): 一辺 s px の正方形を土壌の上に新設する。
SIZE_SIDES = (1, 2, 3, 4, 5, 6, 8, 10, 14)


# --------------------------------------------------------------------------- #
# 幾何(連続座標で評価する指示関数)                                           #
# --------------------------------------------------------------------------- #
def _step(x, sigma):
    """立ち上がり。``sigma`` None なら硬い指示関数、else erf でぼかす。"""
    if sigma is None:
        return (x >= 0).astype(np.float64)
    return 0.5 * (1.0 + erf(x / (sigma * np.sqrt(2.0))))


def rect(Y, X, y0, y1, x0, x1, sigma=PSF):
    """軸に沿った矩形(ガウス PSF との畳み込みは erf の積で閉形式)。"""
    return ((_step(Y - y0, sigma) - _step(Y - y1, sigma))
            * (_step(X - x0, sigma) - _step(X - x1, sigma)))


def rect_px(Y, X, y0, y1, x0, x1, sigma=PSF):
    """画素単位の矩形: 行 ``y0..y1-1``・列 ``x0..x1-1`` が内側(境界は画素の縁 = 半整数)。

    ★境界を整数に置くと、縁の画素は硬い真値では「内側」なのに描画では
    半分しか塗られない —— 一辺 1 px の変化が真値にあるのに画像には 0.09 の
    コントラストでしか写らず、4 節の崖が**幾何でなく標本化の位相**で決まって
    しまう(最初の実装で踏んだ)。
    """
    return rect(Y, X, y0 - 0.5, y1 - 0.5, x0 - 0.5, x1 - 0.5, sigma)


def rot_rect(Y, X, cy, cx, h, w, deg, sigma=PSF):
    """回転した矩形(座標を逆回転してから軸沿い矩形)。"""
    t = np.deg2rad(deg)
    yy, xx = Y - cy, X - cx
    yr = np.cos(t) * yy - np.sin(t) * xx
    xr = np.sin(t) * yy + np.cos(t) * xx
    return rect(yr, xr, -h / 2, h / 2, -w / 2, w / 2, sigma)


def segment(Y, X, y0, x0, y1, x1, width, sigma=PSF):
    """線分(幅 width の帯)。線に沿う座標系で矩形にする。"""
    L = float(np.hypot(y1 - y0, x1 - x0))
    ty, tx = (y1 - y0) / L, (x1 - x0) / L
    yy, xx = Y - y0, X - x0
    along = yy * ty + xx * tx
    across = -yy * tx + xx * ty
    return rect(along, across, 0.0, L, -width / 2, width / 2, sigma)


def disk(Y, X, cy, cx, r, sigma=PSF):
    """円盤(半径方向の erf。r ≫ σ なら PSF 畳み込みの良い近似)。"""
    return _step(r - np.hypot(Y - cy, X - cx), sigma)


def _crowns(rng):
    """樹冠(ガウス)の位置・σ・振幅。森林の内側に一様に撒く。"""
    y0, y1, x0, x1, _ = FOREST
    n = N_CROWNS
    return {"y": rng.uniform(y0 + 3, y1 - 3, n), "x": rng.uniform(x0 + 3, x1 - 3, n),
            "s": rng.uniform(1.3, 2.2, n), "a": rng.uniform(0.10, 0.25, n)}


CROWNS = _crowns(np.random.default_rng(SEED))


def scene(Y, X, t: int, sigma=PSF, sizes: bool = False) -> np.ndarray:
    """場面関数 S_t(y, x)。``t`` = 1 / 2。``sizes`` は大きさ掃引の別場面。"""
    S = SOIL + 0.03 * np.sin(2 * np.pi * Y / 180.0) * np.cos(2 * np.pi * X / 150.0)
    if sizes:
        if t == 2:
            for (ys, xs, s) in size_squares():
                S = S + (BUILD_ALB - S) * rect_px(Y, X, ys, ys + s, xs, xs + s, sigma)
        return S

    def paint(S, W, alb):
        return S + (alb - S) * W

    for (y0, y1, x0, x1, alb) in FIELDS.values():
        S = paint(S, rect_px(Y, X, y0, y1, x0, x1, sigma), alb)
    fr = FIELD_ROT
    S = paint(S, rot_rect(Y, X, fr["cy"], fr["cx"], fr["h"], fr["w"], fr["deg"], sigma), fr["alb"])
    # 森林: 地 + 樹冠。伐採(t=2)は樹冠ごと土壌に戻す。
    fy0, fy1, fx0, fx1, falb = FOREST
    Wf = rect_px(Y, X, fy0, fy1, fx0, fx1, sigma)
    F = np.full_like(S, falb)
    c = CROWNS
    for cy, cx, cs, ca in zip(c["y"], c["x"], c["s"], c["a"]):
        F = F + ca * np.exp(-((Y - cy) ** 2 + (X - cx) ** 2) / (2 * cs ** 2))
    if t == 2:
        Wc = rect_px(Y, X, *CLEARCUT, sigma)
        F = F + (SOIL - F) * Wc
    S = S + (F - S) * Wf
    lk = LAKE
    S = paint(S, disk(Y, X, lk["cy"], lk["cx"], lk["r1"] if t == 1 else lk["r2"], sigma), lk["alb"])
    for (y0, x0, y1, x1) in ROADS.values():
        S = paint(S, segment(Y, X, y0, x0, y1, x1, ROAD_W, sigma), ROAD_ALB)
    for (y0, y1, x0, x1) in BUILDINGS.values():
        S = paint(S, rect_px(Y, X, y0, y1, x0, x1, sigma), BUILD_ALB)
    if t == 2:
        for (y0, y1, x0, x1) in NEW_BUILDINGS.values():
            S = paint(S, rect_px(Y, X, y0, y1, x0, x1, sigma), BUILD_ALB)
    return S


def size_squares():
    """大きさ掃引の正方形 (y, x, s)。互いに 6 px 以上離す。"""
    out, y, x = [], 40.0, 30.0
    for s in SIZE_SIDES:
        out.append((y, x, s))
        x += s + 18
        if x > 200:
            y, x = y + 50, 30.0
    return out


# --------------------------------------------------------------------------- #
# 剛体変換(基準座標 q → 時期 2 の画像座標 p = c + R(q − c) + d)                #
# --------------------------------------------------------------------------- #
def rigid_yx(theta_deg: float, dy: float, dx: float):
    """(A, b): p = A q + b、(y, x) 順。"""
    t = np.deg2rad(theta_deg)
    A = np.array([[np.cos(t), np.sin(t)], [-np.sin(t), np.cos(t)]])
    c = np.asarray(CENTER)
    b = c + np.array([dy, dx]) - A @ c
    return A, b


def grid():
    Y, X = np.mgrid[0:N, 0:N].astype(np.float64)
    return Y, X


def render(t: int, theta_deg=0.0, dy=0.0, dx=0.0, gain=1.0, offset=0.0,
           noise=NOISE, seed=SEED, sizes=False) -> np.ndarray:
    """時期 ``t`` の観測画像。場面を**逆変換した座標で評価**する(補間なし)。"""
    Y, X = grid()
    A, b = rigid_yx(theta_deg, dy, dx)
    Ainv = np.linalg.inv(A)
    P = np.stack([Y.ravel(), X.ravel()])
    Q = Ainv @ (P - b[:, None])
    S = scene(Q[0].reshape(N, N), Q[1].reshape(N, N), t, sizes=sizes)
    rng = np.random.default_rng(seed + 100 * t)
    return gain * S + offset + noise * rng.standard_normal((N, N))


def truth_masks(sizes=False) -> dict:
    """基準座標の硬い真値マスク(種類別)。"""
    Y, X = grid()
    if sizes:
        return {("s=%d" % s): rect_px(Y, X, y, y + s, x, x + s, None) > 0.5
                for (y, x, s) in size_squares()}
    m = {}
    nb = np.zeros((N, N), bool)
    for (y0, y1, x0, x1) in NEW_BUILDINGS.values():
        nb |= rect_px(Y, X, y0, y1, x0, x1, None) > 0.5
    m[CHANGE_TYPES[0]] = nb
    m[CHANGE_TYPES[1]] = rect_px(Y, X, *CLEARCUT, None) > 0.5
    lk = LAKE
    m[CHANGE_TYPES[2]] = ((disk(Y, X, lk["cy"], lk["cx"], lk["r2"], None) > 0.5)
                          & ~(disk(Y, X, lk["cy"], lk["cx"], lk["r1"], None) > 0.5))
    return m


def valid_mask() -> np.ndarray:
    v = np.zeros((N, N), bool)
    v[BORDER:N - BORDER, BORDER:N - BORDER] = True
    return v


def region_classes() -> dict:
    """偽陽性を分けて数えるための領域: 人工物のエッジ帯 / 森林内部 / その他。"""
    Y, X = grid()
    hard = []
    for (y0, y1, x0, x1, _) in FIELDS.values():
        hard.append(rect_px(Y, X, y0, y1, x0, x1, None) > 0.5)
    fr = FIELD_ROT
    hard.append(rot_rect(Y, X, fr["cy"], fr["cx"], fr["h"], fr["w"], fr["deg"], None) > 0.5)
    for (y0, x0, y1, x1) in ROADS.values():
        hard.append(segment(Y, X, y0, x0, y1, x1, ROAD_W, None) > 0.5)
    for (y0, y1, x0, x1) in BUILDINGS.values():
        hard.append(rect_px(Y, X, y0, y1, x0, x1, None) > 0.5)
    lk = LAKE
    hard.append(disk(Y, X, lk["cy"], lk["cx"], lk["r1"], None) > 0.5)
    forest = rect_px(Y, X, *FOREST[:4], None) > 0.5
    hard.append(forest)
    edge = np.zeros((N, N), bool)
    for h in hard:
        edge |= h & binary_dilation(~h, iterations=1)       # 内側 1 px
        edge |= ~h & binary_dilation(h, iterations=1)       # 外側 1 px
    edge = binary_dilation(edge, iterations=3)
    return {"人工物のエッジ帯": edge, "森林内部": forest & ~edge,
            "その他": ~edge & ~forest}


# --------------------------------------------------------------------------- #
# エッジ台帳(予測はこれで立てる)                                             #
# --------------------------------------------------------------------------- #
def edge_inventory(seg_len: float = 4.0) -> list:
    """直線エッジの一覧 ``(my, mx, L, ny, nx, C)``: 中点・長さ・法線・コントラスト。

    長い辺は ``seg_len`` に刻む(回転の予測では場所ごとに変位が違うため)。
    円(湖)は 64 分割の折れ線として入れる。★見えないコントラスト(C < τ)の辺も
    台帳には入れる —— 予測の側でそれを落とすのが筋で、台帳で隠すと
    「なぜ効かないか」が消える。
    """
    out = []

    def add_side(p0, p1, C):
        p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
        L = float(np.linalg.norm(p1 - p0))
        k = max(1, int(np.ceil(L / seg_len)))
        t = (p1 - p0) / L
        n = np.array([-t[1], t[0]])
        for i in range(k):
            a, b = p0 + t * (L * i / k), p0 + t * (L * (i + 1) / k)
            m = 0.5 * (a + b)
            if BORDER <= m[0] <= N - 1 - BORDER and BORDER <= m[1] <= N - 1 - BORDER:
                out.append((m[0], m[1], L / k, n[0], n[1], C))

    def add_rect(corners, C):
        for i in range(4):
            add_side(corners[i], corners[(i + 1) % 4], C)

    def px_corners(y0, y1, x0, x1):
        """画素矩形(rect_px)の縁 = 半整数。"""
        y0, y1, x0, x1 = y0 - 0.5, y1 - 0.5, x0 - 0.5, x1 - 0.5
        return [(y0, x0), (y0, x1), (y1, x1), (y1, x0)]

    for (y0, y1, x0, x1, alb) in FIELDS.values():
        add_rect(px_corners(y0, y1, x0, x1), abs(alb - SOIL))
    fr = FIELD_ROT
    t = np.deg2rad(fr["deg"])
    R = np.array([[np.cos(t), np.sin(t)], [-np.sin(t), np.cos(t)]])
    loc = np.array([(-fr["h"] / 2, -fr["w"] / 2), (-fr["h"] / 2, fr["w"] / 2),
                    (fr["h"] / 2, fr["w"] / 2), (fr["h"] / 2, -fr["w"] / 2)])
    add_rect([np.array([fr["cy"], fr["cx"]]) + R @ p for p in loc], abs(fr["alb"] - SOIL))
    fy0, fy1, fx0, fx1, falb = FOREST
    add_rect(px_corners(fy0, fy1, fx0, fx1), abs(falb - SOIL))
    for (y0, x0, y1, x1) in ROADS.values():
        p0, p1 = np.array([y0, x0]), np.array([y1, x1])
        tt = (p1 - p0) / np.linalg.norm(p1 - p0)
        nn = np.array([-tt[1], tt[0]]) * ROAD_W / 2
        add_side(p0 + nn, p1 + nn, abs(ROAD_ALB - SOIL))
        add_side(p0 - nn, p1 - nn, abs(ROAD_ALB - SOIL))
    for (y0, y1, x0, x1) in BUILDINGS.values():
        add_rect(px_corners(y0, y1, x0, x1), abs(BUILD_ALB - SOIL))
    lk = LAKE
    ang = np.linspace(0, 2 * np.pi, 65)
    pts = [(lk["cy"] + lk["r1"] * np.sin(a), lk["cx"] + lk["r1"] * np.cos(a)) for a in ang]
    for i in range(64):
        add_side(pts[i], pts[i + 1], abs(lk["alb"] - SOIL))
    return out


def band_width(C: float, d: float, tau: float = TAU, sigma: float = PSF,
               noise: float = NOISE) -> float:
    """ぼけたエッジ(高さ C)を法線方向に d ずらした差分が τ を超える**期待**幅 [px]。

    差分には両時期の雑音 σ√2 が乗るので、各位置で超える確率 Q((τ−f)/σ_d) を
    積分する(``noise=0`` なら硬い幅 = f > τ の測度)。
    """
    if d <= 0 or C <= 0:
        return 0.0
    x = np.arange(-12.0, 12.0, 0.01)
    f = C * np.abs(_step(x + d, sigma) - _step(x, sigma))
    if noise <= 0:
        return float(0.01 * np.count_nonzero(f > tau))
    sd = noise * np.sqrt(2.0)
    q = 1.0 - _step(tau - f, sd) + 1.0 - _step(tau + f, sd)
    return float(0.01 * q.sum())


def onset_shift(C: float, tau: float = TAU, sigma: float = PSF) -> float:
    """差分のピーク C·δ/(σ√2π) が τ に届く最小のずれ δ* [px]。"""
    return tau * sigma * np.sqrt(2 * np.pi) / C


def predict_fp(edges, disp_fn, linear: bool = False) -> float:
    """台帳の各辺で法線方向の変位を出し、帯の幅 × 長さを足す。

    ``linear=True`` は「エッジ総長 × ずれ」の比例則(C > τ の辺だけ)。
    """
    tot = 0.0
    for (my, mx, L, ny, nx, C) in edges:
        dy, dx = disp_fn(my, mx)
        dn = abs(ny * dy + nx * dx)
        tot += L * (dn if (linear and C > TAU) else band_width(C, dn))
    return tot


def coverage_rule(s: int, a: float, tau: float = TAU, C: float = BUILD_ALB - SOIL) -> float:
    """一辺 s の正方形を各軸 a だけずらしたとき、真値画素のうち被覆率 > τ/C の割合。

    行と列は独立なので被覆率は ``cov_y(i)·cov_x(j)``、``cov(i) = |[i,i+1) ∩ [a,a+s)|``。
    """
    i = np.arange(s)
    cov = np.clip(np.minimum(i + 1, a + s) - np.maximum(i, a), 0.0, 1.0)
    return float(np.mean(np.outer(cov, cov) > tau / C))


def predict_fp_texture(I_clean: np.ndarray, region: np.ndarray, dy: float, dx: float) -> float:
    """テクスチャ領域の偽陽性を 1 次近似 |∇I·d| > τ で予測(基準画像 1 枚から)。"""
    gy, gx = np.gradient(I_clean)
    return float(np.count_nonzero((np.abs(gy * dy + gx * dx) > TAU) & region))


# --------------------------------------------------------------------------- #
# 検出(ゼロ点)と評価                                                          #
# --------------------------------------------------------------------------- #
def detect(I1, I2, tau: float = TAU, opening: bool = False) -> np.ndarray:
    """|I2 − I1| をしきい値 τ で切る(fullseye の threshold op)。"""
    d = np.abs(np.asarray(I2, float) - np.asarray(I1, float))
    m = np.asarray(fs.apply(d, "threshold", a=tau)) > 0.5
    if opening:
        m = np.asarray(fs.apply(m.astype(np.float64), "opening_circle", a=0.0)) > 0.5
    return m


def fp_mask(det: np.ndarray, masks: dict, valid: np.ndarray) -> np.ndarray:
    """偽陽性の画素。真値の**外側 1 px は不問**(PSF のにじみ。判読ポリゴンの
    縁の曖昧さと同じ扱いで、変化検出の評価では慣行の buffer)。"""
    truth = np.logical_or.reduce(list(masks.values()))
    return det & valid & ~binary_dilation(truth, iterations=1)


def evaluate(det: np.ndarray, masks: dict, valid: np.ndarray) -> dict:
    """IoU(まとめ)/ 偽陽性面積 / 種類別検出率。"""
    truth = np.zeros_like(det)
    for m in masks.values():
        truth |= m
    d, tr = det & valid, truth & valid
    iou = float(fs.ledger.voxel_iou(d.astype(np.float64), tr.astype(np.float64)))
    fp = int(np.count_nonzero(fp_mask(det, masks, valid)))
    rec = {k: float(np.count_nonzero(d & m & valid) / max(1, np.count_nonzero(m & valid)))
           for k, m in masks.items()}
    return {"iou": iou, "fp": fp, "recall": rec, "det": d}


def radiometric_linear(I2, I1, valid):
    """相対放射補正: I2 ≈ g·I1 + o を頑健に当てはめ、I2 を I1 の尺度に戻す。"""
    a, b = I1[valid].ravel(), I2[valid].ravel()
    keep = np.ones(a.size, bool)
    g, o = 1.0, 0.0
    for _ in range(3):
        g, o = np.polyfit(a[keep], b[keep], 1)
        r = b - (g * a + o)
        mad = np.median(np.abs(r[keep] - np.median(r[keep]))) * 1.4826 + 1e-9
        keep = np.abs(r) < 3.0 * mad
    return (I2 - o) / g, float(g), float(o)


# --------------------------------------------------------------------------- #
# 位置合わせ(公開経路の 4 本)                                                 #
# --------------------------------------------------------------------------- #
def fit_rigid_xy(q_xy, p_xy, w=None):
    """対応 q→p(x,y)から (θ[deg], dy, dx)。中心 CENTER まわりの回転 + 並進を LS で。"""
    cx, cy = CENTER[1], CENTER[0]
    X, Y = q_xy[:, 0] - cx, q_xy[:, 1] - cy
    xp, yp = p_xy[:, 0] - cx, p_xy[:, 1] - cy
    n = X.size
    A = np.zeros((2 * n, 4))
    A[0::2, 0], A[0::2, 1], A[0::2, 2] = X, -Y, 1.0
    A[1::2, 0], A[1::2, 1], A[1::2, 3] = Y, X, 1.0
    rhs = np.empty(2 * n)
    rhs[0::2], rhs[1::2] = xp, yp
    if w is not None:
        sw = np.sqrt(np.repeat(w, 2))
        A, rhs = A * sw[:, None], rhs * sw
    a, b, tx, ty = np.linalg.lstsq(A, rhs, rcond=None)[0]
    return float(np.rad2deg(np.arctan2(b, a))), float(ty), float(tx)


def _rigid_from_two(q, p):
    """2 対応から回転 + 並進(閉形式)。"""
    v0, v1 = q[1] - q[0], p[1] - p[0]
    th = np.arctan2(v1[1], v1[0]) - np.arctan2(v0[1], v0[0])
    R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    c = np.array([CENTER[1], CENTER[0]])
    d = p[0] - (c + R @ (q[0] - c))
    return R, d


def ransac_rigid(q_xy, p_xy, thresh=1.0, iters=300, rng=None):
    """2 点 RANSAC → 内点で LS。fullseye に 2-D の頑健当てはめが無いので自前。"""
    rng = rng or np.random.default_rng(0)
    c = np.array([CENTER[1], CENTER[0]])
    best, best_in = None, 0
    n = len(q_xy)
    for _ in range(iters):
        i, j = rng.choice(n, 2, replace=False)
        if np.linalg.norm(q_xy[i] - q_xy[j]) < 8:
            continue
        R, d = _rigid_from_two(q_xy[[i, j]], p_xy[[i, j]])
        pred = (q_xy - c) @ R.T + c + d
        inl = np.linalg.norm(pred - p_xy, axis=1) < thresh
        if inl.sum() > best_in:
            best, best_in = inl, int(inl.sum())
    return best


def reg_phase(I1, I2):
    """位相相関 —— 公開経路には 3-D 用(match_phase_3d)しか無いので (1,H,W) を通す。整数精度。"""
    s = fs.ledger.match_phase_3d(I1[None], I2[None])       # b を戻すロール量
    return 0.0, -float(s[1]), -float(s[2]), {"n": 1}


def _trimmed_rigid(q, p, keep, rounds=4):
    """残差で刈る LS(中央値 + 3·MAD の外を落として繰り返す)。"""
    th = dy = dx = 0.0
    for _ in range(rounds):
        th, dy, dx = fit_rigid_xy(q[keep], p[keep])
        A, b = rigid_yx(th, dy, dx)
        pred = (A @ np.c_[q[:, 1], q[:, 0]].T + b[:, None]).T
        r = np.hypot(pred[:, 0] - p[:, 1], pred[:, 1] - p[:, 0])
        r[~np.isfinite(r)] = np.inf
        med = np.median(r[keep])
        mad = np.median(np.abs(r[keep] - med)) * 1.4826 + 1e-6
        keep = keep & (r < med + 3 * mad)
    return th, dy, dx, keep


def reg_piv(I1, I2, window=48):
    """PIV 相互相関(窓ごと)→ 平坦な窓を捨てる → 正規化中央値検定 → 残差で刈る剛体 LS。

    ★最初は「正規化中央値検定だけ」で組んだ(残留 0.87 px)。窓の半分は平坦な
    土壌か直線エッジ 1 本(開口問題)で、**近傍も同じように間違う**ので近傍検定
    では落ちない。残差で刈る LS を 4 回回して初めて 0.05 px 以下になる。
    """
    fl = np.asarray(fs.ledger.piv_cross_correlate(I1, I2, window=window, overlap=0.5))
    bad = np.asarray(fs.ledger.piv_outlier_mask(np.nan_to_num(fl), threshold=2.0))
    h, w = fl.shape[1:]
    step = window // 2
    ys = window / 2 + step * np.arange(h)
    xs = window / 2 + step * np.arange(w)
    std = np.array([[I1[int(y - window / 2):int(y + window / 2),
                        int(x - window / 2):int(x + window / 2)].std() for x in xs] for y in ys])
    YY, XX = np.meshgrid(ys, xs, indexing="ij")
    q = np.c_[XX.ravel(), YY.ravel()]
    p = q + np.c_[fl[1].ravel(), fl[0].ravel()]
    keep = ~bad.ravel() & np.isfinite(p).all(axis=1) & (std.ravel() > 0.03)
    th0, dy0, dx0 = fit_rigid_xy(q[keep], p[keep])
    th, dy, dx, keep = _trimmed_rigid(q, p, keep)
    return th, dy, dx, {"n": int(keep.sum()), "first_pass": (th0, dy0, dx0)}


def reg_keypoints(I1, I2):
    """特徴点(match_keypoints: Harris + パッチ記述子 + 比検定)→ RANSAC → Procrustes(z=0)。"""
    p1, p2 = fs.match_keypoints(I1, I2, detector="harris", patch=11)
    p1, p2 = np.asarray(p1, float), np.asarray(p2, float)
    inl = ransac_rigid(p1, p2, rng=np.random.default_rng(SEED))
    if inl is None or inl.sum() < 3:
        return 0.0, 0.0, 0.0, {"n": 0}
    src = np.c_[p1[inl], np.zeros(int(inl.sum()))]
    dst = np.c_[p2[inl], np.zeros(int(inl.sum()))]
    M = np.asarray(fs.ledger.procrustes_fit(src, dst, scaling=False))
    th = float(np.rad2deg(np.arctan2(M[1, 0], M[0, 0])))
    # procrustes は原点まわり。中心まわりの並進に直す。
    c = np.array([CENTER[1], CENTER[0]])
    d = M[:2, :2] @ c + M[:2, 3] - c
    return th, float(d[1]), float(d[0]), {"n": int(inl.sum()), "matched": int(len(p1))}


def reg_lk(I1, I2):
    """密な Lucas-Kanade フロー → 残差で刈る頑健 LS(変化画素を外れ値として落とす)。"""
    u, v = fs.optical_flow_lk(I1, I2, window=15, levels=3, iters=4)
    Y, X = grid()
    gy, gx = np.gradient(I1)
    wgt = np.hypot(gy, gx)
    sel = (wgt > 0.02) & valid_mask()
    q = np.c_[X[sel], Y[sel]]
    p = q + np.c_[np.asarray(u)[sel], np.asarray(v)[sel]]
    th, dy, dx, keep = _trimmed_rigid(q, p, np.ones(len(q), bool), rounds=3)
    return th, dy, dx, {"n": int(keep.sum())}


METHODS = {
    "位相相関(3-D 経路、整数)": reg_phase,
    "PIV 相互相関→剛体": reg_piv,
    "特徴点→RANSAC→Procrustes": reg_keypoints,
    "密な LK フロー→頑健 LS": reg_lk,
}


def residual_px(est, true, valid) -> float:
    """推定変換と真の変換の差を、画像全体の平均変位 [px] で。"""
    Y, X = grid()
    Ae, be = rigid_yx(*est)
    At, bt = rigid_yx(*true)
    P = np.stack([Y[valid], X[valid]])
    diff = (Ae - At) @ P + (be - bt)[:, None]
    return float(np.mean(np.hypot(diff[0], diff[1])))


def warp_back(I2, est):
    """I2 を基準座標へ戻す(3 次スプライン)。fullseye の affine_trans_image は
    任意の並進を受けないので scipy を使う(穴として報告)。"""
    A, b = rigid_yx(*est)
    return affine_transform(I2, A, offset=b, order=3, mode="nearest")


# --------------------------------------------------------------------------- #
# 1. 場面と真値、ゼロ点                                                        #
# --------------------------------------------------------------------------- #
def section_scene() -> dict:
    print("\n" + "=" * 78)
    print("1) 場面と真値 —— ずれ無しならゼロ点は効く")
    print("=" * 78)
    I1 = render(1)
    I2 = render(2)
    masks = truth_masks()
    valid = valid_mask()
    areas = {k: int(m.sum()) for k, m in masks.items()}
    print("  変化の真値面積 [px]: " + " / ".join("%s %d" % (k, v) for k, v in areas.items())
          + "(合計 %d、視野の %.2f %%)" % (sum(areas.values()), 100 * sum(areas.values()) / N / N))
    ev = evaluate(detect(I1, I2), masks, valid)
    print("  ずれ無し・照明差無しのゼロ点: IoU %.3f / 偽陽性 %d px / 検出率 "
          % (ev["iou"], ev["fp"]) + " / ".join("%s %.2f" % (k, v) for k, v in ev["recall"].items()))
    print("  ★伐採は位置合わせが完璧でも %.2f —— 樹冠が消えた跡の**平均**輝度差は小さく、"
          "差分に出るのは樹冠 1 本ずつの斑点。" % ev["recall"][CHANGE_TYPES[1]])
    return {"I1": I1, "I2": I2, "masks": masks, "valid": valid, "ev0": ev, "areas": areas}


# --------------------------------------------------------------------------- #
# 2. 崖(a): 平行移動                                                           #
# --------------------------------------------------------------------------- #
def section_shift(sc: dict) -> dict:
    print("\n" + "=" * 78)
    print("2) 崖 (a): サブピクセルのずれ —— 幾何で先に予測してから測る")
    print("=" * 78)
    edges = edge_inventory()
    u = np.array([1.0, 1.0]) / np.sqrt(2.0)                     # ずらす向き(対角)
    Lproj = sum(L * abs(ny * u[0] + nx * u[1]) for (_, _, L, ny, nx, C) in edges if C > TAU)
    Lall = sum(L for (_, _, L, *_) in edges)
    Cmax = max(C for (*_, C) in edges)
    print("  エッジ台帳: %d 本、総長 %.0f px、しきい値を超えるコントラストの辺の投影長 %.0f px"
          % (len(edges), Lall, Lproj))
    print("  予想 A(比例則): 偽陽性 = 投影長 × ずれ = %.0f px × δ" % Lproj)
    print("  予想 B(PSF 込み): 差分のピーク C·δ/(σ√2π) が τ=%.2f を超える δ* = τσ√2π/C"
          " —— C=%.2f で δ* = %.3f px、C=%.2f(湖)で %.3f px"
          % (TAU, Cmax, onset_shift(Cmax), abs(LAKE["alb"] - SOIL), onset_shift(abs(LAKE["alb"] - SOIL))))

    I1, masks, valid = sc["I1"], sc["masks"], sc["valid"]
    I1_clean = render(1, noise=0.0)
    classes = region_classes()
    deltas = (0.0, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0)
    print("\n   ずれ δ   偽陽性 実測   比例則   PSF 込み   +テクスチャ   IoU     内訳: エッジ帯 / 森林内 / その他")
    rows, fp_l, predA, predB, predC, iou_l, split_l = [], [], [], [], [], [], []
    for d in deltas:
        dy, dx = d * u[0], d * u[1]
        I2 = render(2, dy=dy, dx=dx)
        ev = evaluate(detect(I1, I2), masks, valid)
        fpm = fp_mask(ev["det"], masks, valid)
        split = [int(np.count_nonzero(fpm & classes[k])) for k in classes]
        pa = predict_fp(edges, lambda my, mx: (dy, dx), linear=True)
        pb = predict_fp(edges, lambda my, mx: (dy, dx))
        pc = pb + predict_fp_texture(I1_clean, classes["森林内部"], dy, dx)
        fp_l.append(ev["fp"]); predA.append(pa); predB.append(pb); predC.append(pc)
        iou_l.append(ev["iou"]); split_l.append(split)
        rows.append(["%.2f" % d, "%d" % ev["fp"], "%.0f" % pa, "%.0f" % pb, "%.0f" % pc,
                     "%.3f" % ev["iou"]] + ["%d" % s for s in split])
        print("   %5.2f    %7d     %6.0f    %6.0f     %6.0f     %.3f      %5d / %5d / %5d"
              % (d, ev["fp"], pa, pb, pc, ev["iou"], *split))
    quiet = 20                                                  # 雑音の床(視野の 0.03 %)
    first = next((d for d, f in zip(deltas, fp_l) if f > quiet), None)
    last_zero = max(d for d, f in zip(deltas, fp_l) if f <= quiet)
    print("\n  ★偽陽性が最初に出た(> %d px)のは δ=%.2f px(δ=%.2f までは %d px 以下 = 雑音の床)。"
          "予想 B の崖 δ*=%.3f px と整合。" % (quiet, first, last_zero, quiet, onset_shift(Cmax)))
    i3 = deltas.index(3.0)
    print("  ★比例則は 3 px で実測の %.2f 倍 —— 大きなずれでは合うが、崖の位置を説明しない。"
          % (predA[i3] / fp_l[i3]))
    idx = [i for i, d_ in enumerate(deltas) if d_ >= first]
    rB = [predB[i] / fp_l[i] for i in idx]
    rC = [predC[i] / fp_l[i] for i in idx]
    print("  PSF+雑音込みの台帳予測は δ=%.1f〜%.0f px で実測の %.2f〜%.2f 倍。足りない分は"
          "**森林内部**(台帳に無い樹冠テクスチャ)。" % (first, deltas[-1], min(rB), max(rB)))
    i15, i3 = deltas.index(1.5), deltas.index(3.0)
    print("  ずれ 1.5 px の内訳: エッジ帯 %d / 森林内部 %d / その他 %d px。森林分の勾配予測 %.0f px、"
          "足した予測は実測の %.2f 倍。" % (*split_l[i15], predC[i15] - predB[i15], rC[idx.index(i15)]))
    print("  ★ただし勾配則は 1 次近似なので δ が樹冠の σ(1.3〜2.2 px)に近づくと過大: 3 px では森林の"
          "予測 %.0f px に対し実測 %d px、全体で %.2f 倍。台帳予測はエッジ帯だけなら 3 px で %.2f 倍。"
          % (predC[i3] - predB[i3], split_l[i3][1], rC[idx.index(i3)], predB[i3] / split_l[i3][0]))
    print("  IoU は δ=0 の %.3f から 3 px で %.3f へ —— 変化そのものは残っているのに、"
          "偽陽性が和集合を膨らませる。" % (iou_l[0], iou_l[-1]))

    figs.save_plot("plot_fp_vs_shift",
                   [("実測", deltas, fp_l), ("比例則(エッジ総長×δ)", deltas, predA),
                    ("PSF 込み予測", deltas, predB), ("+森林テクスチャ", deltas, predC)],
                   xlabel="ずれ δ [px](対角方向)", ylabel="偽陽性面積 [px]",
                   title="サブピクセルのずれと偽陽性 —— 崖は δ*=τσ√2π/C",
                   caption="0.35 px までゼロ、そこから立ち上がる。比例則は崖を説明しない。")
    figs.save_table("table_fp_shift", ["δ [px]", "偽陽性", "比例則", "PSF 込み", "+テクスチャ",
                                       "IoU", "エッジ帯", "森林内", "その他"], rows,
                    title="ずれの掃引(偽陽性の内訳つき)")
    # 図: ずれ 0.25 / 1 / 3 px の偽陽性地図
    panels, caps = [], []
    for d in (0.0, 0.5, 1.5, 3.0):
        I2 = render(2, dy=d * u[0], dx=d * u[1])
        det = detect(I1, I2) & valid
        truth = np.logical_or.reduce(list(masks.values()))
        rgb = np.stack([I1, I1, I1], -1) * 0.6 + 0.2
        rgb[det & ~truth] = (1.0, 0.55, 0.0)
        rgb[det & truth] = (0.2, 0.4, 1.0)
        panels.append(np.clip(rgb, 0, 1))
        caps.append("δ=%.1f px" % d)
    figs.save_grid("map_fp_shift", panels, caps, ncols=4,
                   title="偽陽性地図(橙=偽陽性、青=真の変化)—— ずれが帯になる",
                   caption="ずれ 0 では変化だけ。0.5 px から強いエッジ(屋根・道路)が帯として出る。")
    return {"deltas": deltas, "fp": fp_l, "predA": predA, "predB": predB, "predC": predC,
            "iou": iou_l, "first": first, "Lproj": Lproj, "edges": edges, "onset": onset_shift(Cmax)}


# --------------------------------------------------------------------------- #
# 3. 崖(b): 微小回転                                                           #
# --------------------------------------------------------------------------- #
def section_rotation(sc: dict, sh: dict) -> dict:
    print("\n" + "=" * 78)
    print("3) 崖 (b): 微小回転 —— 中央は無傷、端だけ壊れる")
    print("=" * 78)
    I1, masks, valid = sc["I1"], sc["masks"], sc["valid"]
    Y, X = grid()
    r = np.hypot(Y - CENTER[0], X - CENTER[1])
    bins = ((0, 32), (32, 64), (64, 96), (96, 128), (128, 200))
    truth = np.logical_or.reduce(list(masks.values()))
    edges = sh["edges"]
    thetas = (0.0, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0)
    print("  局所のずれは r·θ。崖の半径 r* = δ*/θ(δ*=%.3f px): " % sh["onset"]
          + " / ".join("%.2f°→%.0f px" % (t, sh["onset"] / np.deg2rad(t)) for t in thetas[1:]))
    print("\n   θ [deg]   偽陽性 [px]   予測    偽陽性率 [%] r<32 / 32-64 / 64-96 / 96-128 / >128")
    fp_l, pred_l, dens = [], [], []
    for th in thetas:
        I2 = render(2, theta_deg=th)
        det = detect(I1, I2) & valid
        fpm = fp_mask(det, masks, valid)
        t = np.deg2rad(th)
        # 回転の変位場: (dy, dx) = θ × (-(x−cx)... ) → p = c + R(q−c): dq = R q − q ≈ θ·(x−cx, −(y−cy))
        A, b = rigid_yx(th, 0.0, 0.0)
        pred = predict_fp(edges, lambda my, mx: tuple((A @ np.array([my, mx]) + b) - np.array([my, mx])))
        row = []
        for (r0, r1) in bins:
            sel = (r >= r0) & (r < r1) & valid & ~truth
            row.append(100.0 * np.count_nonzero(fpm & sel) / max(1, np.count_nonzero(sel)))
        fp_l.append(int(fpm.sum())); pred_l.append(pred); dens.append(row)
        print("   %5.2f      %7d     %6.0f      " % (th, fpm.sum(), pred)
              + " / ".join("%5.2f" % v for v in row))
    i1, i05 = thetas.index(1.0), thetas.index(0.5)
    print("\n  ★1 度の回転で中心 32 px 以内は %.1f %%、96 px 以遠は %.1f %%。"
          % (dens[i1][0], (dens[i1][3] + dens[i1][4]) / 2))
    print("  0.5 度では r*=%.0f px なので内側ビン(<32)は無傷のはず —— 実測 %.2f %%。"
          % (sh["onset"] / np.deg2rad(0.5), dens[i05][0]))
    print("  台帳による予測は 1 度で実測の %.2f 倍(樹冠テクスチャの分が足りないのは 2 節と同じ)。"
          % (pred_l[i1] / max(1, fp_l[i1])))
    figs.save_plot("plot_rotation_radial",
                   [("θ=%.2f°" % thetas[i], [0.5 * (a + b) for (a, b) in bins], dens[i])
                    for i in (2, 4, 5, 6)],
                   xlabel="中心からの距離 r [px]", ylabel="偽陽性率 [%]",
                   title="回転は中心から r*=δ*/θ の外だけ壊す",
                   caption="局所のずれ r·θ が崖 δ* を超える半径から偽陽性が立ち上がる。")
    I2 = render(2, theta_deg=1.0)
    det = detect(I1, I2) & valid
    rgb = np.stack([I1, I1, I1], -1) * 0.6 + 0.2
    rgb[det & ~truth] = (1.0, 0.55, 0.0)
    rgb[det & truth] = (0.2, 0.4, 1.0)
    figs.save("map_rotation_1deg", np.clip(rgb, 0, 1),
              "回転 1 度の偽陽性地図(橙)。中央付近のエッジは無傷で、端ほど帯が太い。")
    return {"thetas": thetas, "fp": fp_l, "dens": dens, "pred": pred_l}


# --------------------------------------------------------------------------- #
# 4. 崖(c): 変化の大きさ                                                       #
# --------------------------------------------------------------------------- #
def section_size() -> dict:
    print("\n" + "=" * 78)
    print("4) 崖 (c): 変化の大きさ —— 小さい変化から消える(ずれでも、後処理でも)")
    print("=" * 78)
    I1 = render(1, sizes=True)
    masks = truth_masks(sizes=True)
    valid = valid_mask()
    u = np.array([1.0, 1.0]) / np.sqrt(2.0)
    deltas = (0.0, 0.5, 1.0, 2.0)
    print("  予想(最初の案): ずれ δ(対角)で一辺 s の検出率 = 面積の重なり (1 − δ/(s√2))²。")
    print("  ★これは外れた(最初の実行で s≥3 の最大差 0.31)。検出は面積でなく**画素**で決まる: 真値画素は"
          "ずれた足跡に被覆率 > τ/C = %.2f だけ掛かれば拾われる。\n  予想(画素被覆則): 各真値画素の被覆率"
          "(行 × 列)が %.2f を超える割合。1 px 未満のずれでは画素は 1 つも失われず、"
          "(1 − τ/C)√2 = %.2f px を超えると行と列を 1 本ずつ失う。" % (TAU / (BUILD_ALB - SOIL),
                                                                TAU / (BUILD_ALB - SOIL),
                                                                (1 - TAU / (BUILD_ALB - SOIL)) * np.sqrt(2)))
    hdr = "   一辺 s  面積 " + "".join("  δ=%.1f 実/予" % d for d in deltas) + "   δ=0+開 / δ=1+開"
    print(hdr)
    rows, series = [], {d: [] for d in deltas}
    open_series = {0.0: [], 1.0: []}
    pred_series = {d: [] for d in deltas}
    worst = 0.0
    for (y, x, s) in size_squares():
        key = "s=%d" % s
        line = ["%d" % s, "%d" % int(masks[key].sum())]
        for d in deltas:
            I2 = render(2, dy=d * u[0], dx=d * u[1], sizes=True)
            det = detect(I1, I2) & valid
            rec = float(np.count_nonzero(det & masks[key]) / masks[key].sum())
            pr = coverage_rule(s, d / np.sqrt(2.0))
            series[d].append(rec); pred_series[d].append(pr)
            worst = max(worst, abs(rec - pr))
            line.append("%.2f/%.2f" % (rec, pr))
        for d in (0.0, 1.0):
            I2 = render(2, dy=d * u[0], dx=d * u[1], sizes=True)
            det = detect(I1, I2, opening=True) & valid
            open_series[d].append(float(np.count_nonzero(det & masks[key]) / masks[key].sum()))
        line.append("%.2f / %.2f" % (open_series[0.0][-1], open_series[1.0][-1]))
        rows.append(line)
        print("   %5d  %5s " % (s, line[1]) + "".join("   %s" % c for c in line[2:2 + len(deltas)])
              + "     " + line[-1])
    sides = list(SIZE_SIDES)
    print("\n  ★画素被覆則と実測の差は全 36 点で最大 %.3f(PSF は τ/C=0.2 の被覆判定をほとんど動かさない)。"
          % worst)
    print("  ★オープニング(半径 1)を掛けると δ=0 でも一辺 %s px は検出率 0、一辺 2 px は %.2f —— 偽陽性の"
          "帯を消す後処理は、同じ幅の本物の変化も消す(2 px が残るのは PSF で検出マスクが膨らむため)。"
          % ("・".join(str(s) for s, v in zip(sides, open_series[0.0]) if v == 0.0),
             open_series[0.0][sides.index(2)]))
    figs.save_plot("plot_size_cliff",
                   [("δ=0", sides, series[0.0]), ("δ=1 px", sides, series[1.0]),
                    ("δ=1 px 被覆則", sides, pred_series[1.0]), ("δ=2 px", sides, series[2.0]),
                    ("δ=0 + オープニング", sides, open_series[0.0])],
                   xlabel="変化の一辺 s [px]", ylabel="検出率",
                   title="変化の大きさの崖 —— 画素被覆率 > τ/C で決まる",
                   caption="ずれ 1 px では角の画素だけ、2 px では行と列を 1 本ずつ失う。"
                           "オープニングは 1 px を根こそぎ消す。")
    figs.save_table("table_size_cliff", ["一辺 s", "面積"] + ["δ=%.1f 実/予" % d for d in deltas]
                    + ["δ=0+開 / δ=1+開"], rows, title="変化の大きさ × ずれ × 後処理")
    return {"sides": sides, "series": series, "open": open_series, "worst": worst}


# --------------------------------------------------------------------------- #
# 5. 位置合わせ(公開経路)と残留ずれ                                            #
# --------------------------------------------------------------------------- #
CONDITIONS = {
    "ずれ+回転": dict(theta_deg=0.4, dy=1.3, dx=-0.8),
    "ずれ+回転+照明差": dict(theta_deg=0.4, dy=1.3, dx=-0.8, gain=1.15, offset=0.03),
    "ずれ+回転+強い雑音": dict(theta_deg=0.4, dy=1.3, dx=-0.8, noise=0.03),
}


def section_registration(sc: dict, sh: dict) -> dict:
    print("\n" + "=" * 78)
    print("5) 位置合わせ(fullseye の公開経路 4 本)—— 残留ずれと偽陽性は同じ崖に乗る")
    print("=" * 78)
    I1, masks, valid = sc["I1"], sc["masks"], sc["valid"]
    truth = np.logical_or.reduce(list(masks.values()))
    out, rows = [], []
    for cname, kw in CONDITIONS.items():
        true = (kw["theta_deg"], kw["dy"], kw["dx"])
        noise = kw.get("noise", NOISE)
        I2 = render(2, **kw)
        I1c = I1 if noise == NOISE else render(1, noise=noise)
        print("\n  [%s] 真値 θ=%.2f° dy=%+.2f dx=%+.2f px%s" % (
            cname, *true, "、利得 %.2f オフセット %.2f" % (kw["gain"], kw["offset"]) if "gain" in kw else ""))
        print("   方法                          θ [deg]   dy      dx     残留 [px]  偽陽性  IoU    "
              + " / ".join(CHANGE_TYPES) + "   時間")
        # ゼロ点(位置合わせ無し)
        I2n, g, o = radiometric_linear(I2, I1c, valid & ~truth)
        ev = evaluate(detect(I1c, I2n), masks, valid)
        res0 = residual_px((0.0, 0.0, 0.0), true, valid)
        print("   %-28s %7s  %6s  %6s   %7.3f   %6d  %.3f   " % ("ゼロ点(位置合わせ無し)", "-", "-", "-", res0, ev["fp"], ev["iou"])
              + " / ".join("%.2f" % ev["recall"][k] for k in CHANGE_TYPES))
        out.append((cname, "ゼロ点", res0, ev["fp"], ev["iou"], ev["recall"]))
        rows.append([cname, "ゼロ点", "-", "-", "-", "%.3f" % res0, "%d" % ev["fp"], "%.3f" % ev["iou"]]
                    + ["%.2f" % ev["recall"][k] for k in CHANGE_TYPES])
        for mname, fn in METHODS.items():
            t0 = time.perf_counter()
            th, dy, dx, info = fn(I1c, I2)
            dt = time.perf_counter() - t0
            est = (th, dy, dx)
            res = residual_px(est, true, valid)
            I2w = warp_back(I2, est)
            I2n, g, o = radiometric_linear(I2w, I1c, valid & ~truth)
            ev = evaluate(detect(I1c, I2n), masks, valid)
            print("   %-28s %+7.3f  %+6.3f  %+6.3f   %7.3f   %6d  %.3f   " % (mname, th, dy, dx, res, ev["fp"], ev["iou"])
                  + " / ".join("%.2f" % ev["recall"][k] for k in CHANGE_TYPES) + "   %.2f s" % dt)
            out.append((cname, mname, res, ev["fp"], ev["iou"], ev["recall"]))
            rows.append([cname, mname, "%+.3f" % th, "%+.3f" % dy, "%+.3f" % dx, "%.3f" % res,
                         "%d" % ev["fp"], "%.3f" % ev["iou"]] + ["%.2f" % ev["recall"][k] for k in CHANGE_TYPES])
        if "gain" in kw:
            print("   (相対放射補正の推定: 利得 %.3f オフセット %.3f、真値 %.2f / %.2f)" % (g, o, kw["gain"], kw["offset"]))

    base = [r for r in out if r[0] == "ずれ+回転"]
    good = [r for r in base if r[1] != "ゼロ点" and "位相" not in r[1]]
    ph = next(r for r in base if "位相" in r[1])
    rot_only = residual_px((0.0, 1.3, -0.8), (0.4, 1.3, -0.8), valid)
    print("\n  ★3 経路(PIV / 特徴点 / LK)の残留ずれは %.3f〜%.3f px、偽陽性 %d〜%d px(ゼロ点 %d px)。"
          % (min(r[2] for r in good), max(r[2] for r in good),
             min(r[3] for r in good), max(r[3] for r in good), base[0][3]))
    print("  ★位相相関は公開経路に 3-D 用しか無く、整数精度・並進のみ: 残留 %.3f px(うち回転 0.4° の分が %.3f px)、"
          "偽陽性 %d px。" % (ph[2], rot_only, ph[3]))
    # 同じ崖に乗っているか: 2 節の掃引(ずれだけ)を残留ずれの位置で補間して比べる
    interp = float(np.interp(ph[2], sh["deltas"], sh["fp"]))
    print("     2 節の掃引を残留 %.2f px で読むと %.0f px —— 実測 %d px(%.2f 倍)。"
          "**位置合わせ後も同じ崖の上に乗る**(残留の中身が回転でも)。" % (ph[2], interp, ph[3], ph[3] / interp))
    lk_il = next(r for r in out if r[0] == "ずれ+回転+照明差" and "LK" in r[1])
    kp_il = next(r for r in out if r[0] == "ずれ+回転+照明差" and "特徴点" in r[1])
    print("  ★照明差が入ると LK(輝度不変を仮定)は残留 %.3f px に悪化、特徴点(正規化パッチ)は %.3f px のまま。"
          "強い雑音では逆に特徴点が %.3f px、LK が %.3f px —— **経路ごとに弱点が違う**。"
          % (lk_il[2], kp_il[2],
             next(r for r in out if r[0] == "ずれ+回転+強い雑音" and "特徴点" in r[1])[2],
             next(r for r in out if r[0] == "ずれ+回転+強い雑音" and "LK" in r[1])[2]))
    # ★1 枚のグラフ: 残留ずれ vs 偽陽性(掃引の線 + 登録結果の点)
    xs = [r[2] for r in out]
    ys = [r[3] for r in out]
    figs.save_plot("plot_residual_vs_fp",
                   [("ずれだけの掃引(2 節)", list(sh["deltas"]), list(sh["fp"])),
                    ("PSF+テクスチャ予測", list(sh["deltas"]), list(sh["predC"])),
                    ("位置合わせ後(4 経路 × 3 条件 + ゼロ点)", xs, ys)],
                   kinds=["line", "line", "scatter"],
                   xlabel="残留ずれ [px](画像全体の平均変位、真値との差)", ylabel="偽陽性面積 [px]",
                   title="位置合わせ後の残留ずれと偽陽性 —— 同じ崖に乗る",
                   caption="点は 3 条件 × (ゼロ点 + 4 経路)。残留 0.05 px 以下の 3 経路は原点近く、"
                           "整数精度の位相相関は崖の途中に落ちる。")
    figs.save_table("table_registration",
                    ["条件", "方法", "θ [deg]", "dy [px]", "dx [px]", "残留 [px]", "偽陽性 [px]", "IoU"]
                    + list(CHANGE_TYPES), rows, title="位置合わせの公開経路 4 本 × 3 条件")
    return {"rows": out, "good": good, "phase": ph}


# --------------------------------------------------------------------------- #
# 6. 対照群                                                                    #
# --------------------------------------------------------------------------- #
def section_controls(sc: dict) -> dict:
    print("\n" + "=" * 78)
    print("6) 対照群 —— 偽陽性の原因は要因を 1 つずつ止めて分ける")
    print("=" * 78)
    I1, masks, valid = sc["I1"], sc["masks"], sc["valid"]
    truth = np.logical_or.reduce(list(masks.values()))
    cases = {
        "ずれ無し・照明差無し": dict(),
        "照明差だけ": dict(gain=1.15, offset=0.03),
        "ずれだけ(1.3/−0.8 px)": dict(dy=1.3, dx=-0.8),
        "回転だけ(0.4°)": dict(theta_deg=0.4),
        "ずれ+回転+照明差": dict(theta_deg=0.4, dy=1.3, dx=-0.8, gain=1.15, offset=0.03),
    }
    print("   条件                       補正なし    線形放射補正   histogram_match   [偽陽性 px]"
          "   検出率(補正なし) " + " / ".join(CHANGE_TYPES))
    rows, res = [], {}
    for name, kw in cases.items():
        I2 = render(2, **kw)
        e0 = evaluate(detect(I1, I2), masks, valid)
        I2l, g, o = radiometric_linear(I2, I1, valid & ~truth)
        e1 = evaluate(detect(I1, I2l), masks, valid)
        I2h = np.asarray(fs.ledger.histogram_match(I2, I1))
        e2 = evaluate(detect(I1, I2h), masks, valid)
        res[name] = (e0["fp"], e1["fp"], e2["fp"], e0["recall"], e2["recall"])
        rows.append([name, "%d" % e0["fp"], "%d" % e1["fp"], "%d" % e2["fp"]]
                    + ["%.2f" % e0["recall"][k] for k in CHANGE_TYPES])
        print("   %-26s %8d    %8d       %8d                     "
              % (name, e0["fp"], e1["fp"], e2["fp"])
              + " / ".join("%.2f" % e0["recall"][k] for k in CHANGE_TYPES))
    il, sh_only, none = res["照明差だけ"], res["ずれだけ(1.3/−0.8 px)"], res["ずれ無し・照明差無し"]
    print("\n  ★照明差だけで偽陽性 %d px(利得 1.15 で明るい畑・屋根・森林が丸ごと「変化」)。線形放射補正で %d px。"
          % (il[0], il[1]))
    print("  ★histogram_match は %d px —— ずれも照明差も無い対でも %d px 出る。順位で分布を合わせる写像は"
          "**変化そのもの(水域拡大で暗い画素が増える)を分布差として消しにかかる**ので、変化検出の前処理には"
          "向かない(ずれ無しでも水域の検出率が %.2f → %.2f)。"
          % (il[2], none[2], none[3][CHANGE_TYPES[2]], none[4][CHANGE_TYPES[2]]))
    print("  ★ずれだけは %d px で、放射補正しても %d px —— **同じ偽陽性でも直す道具が違う**。"
          "対照群を置かないと「照明を補正したのに直らない」で止まる。" % (sh_only[0], sh_only[1]))
    figs.save_table("table_controls", ["条件", "補正なし", "線形放射補正", "histogram_match"]
                    + list(CHANGE_TYPES), rows, title="対照群(偽陽性 px と検出率)")
    return res


# --------------------------------------------------------------------------- #
# 7. 絵                                                                        #
# --------------------------------------------------------------------------- #
def section_figure(sc: dict) -> None:
    I1, masks = sc["I1"], sc["masks"]
    I2 = render(2, theta_deg=0.4, dy=1.3, dx=-0.8, gain=1.15, offset=0.03)
    tr = np.zeros((N, N, 3))
    cols = ((0.2, 0.4, 1.0), (1.0, 0.3, 0.3), (0.2, 0.8, 0.9))
    for (k, m), c in zip(masks.items(), cols):
        tr[m] = c
    diff = np.abs(I2 - I1)
    figs.save_grid("scene_pair",
                   [I1, I2, tr, np.clip(diff, 0, 0.5)],
                   ["時期 1(基準)", "時期 2(ずれ 1.3/−0.8 px、回転 0.4°、照明差)",
                    "真値(青=新設、赤=伐採、水色=水域拡大)", "素朴な差分 |I2−I1|"],
                   ncols=2, title="合成地表: 畑・道路・建物・森林・湖、%d×%d px" % (N, N),
                   caption="差分にはエッジが全部出る。変化そのものはその帯の中に埋もれる。")


# --------------------------------------------------------------------------- #
# 8. 道具の穴                                                                   #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("8) 道具の穴(この PoC で fullseye を引いてみて)")
    print("=" * 78)
    # (a) 2-D の位相相関が無い(3-D 用を (1,H,W) で通した。整数精度)。
    assert hasattr(fs.ledger, "match_phase_3d")
    assert not hasattr(fs, "phase_correlate") and not hasattr(fs.ledger, "phase_correlate_2d")
    print("  (a) 2-D の位相相関が無い。3-D 用 match_phase_3d に (1,H,W) を通せば動くが整数精度"
          "(丸めだけで最大 0.71 px の残留)で回転も返さず、サブピクセル(refine_translation_lk)も"
          " 3-D 用。2-D の 1 本(サブピクセル + log-polar で回転)があれば 5 節の整数経路は要らない。")
    # (b) 2-D の剛体/相似当てはめ(+RANSAC)が無い。
    assert not hasattr(fs, "fit_rigid_2d") and not hasattr(fs.ledger, "ransac_rigid_2d")
    print("  (b) 対応点から 2-D の剛体変換を頑健に当てはめる口が無い(procrustes_fit は 3-D、"
          "RANSAC は 3-D の平面/球/PnP 用だけ)。この PoC は 2 点 RANSAC を自前で書いた。"
          "poc_panorama_drift も同じ穴を踏んでいる(2 本目)。")
    # (c) 任意の並進+回転で画像をワープする 2-D op が無い。
    assert "affine_trans_image" in fs.op_names()
    print("  (c) 任意の 2×3 行列で画像をワープする 2-D の口が無い(affine_trans_image は"
          "つまみ 2 個で回転 ±20° とせん断だけ、並進を受けない)。戻しは scipy で書いた。")
    # (d) IoU は 3-D 名。
    print("  (d) 2-D マスクの IoU / 偽陽性 / 検出率をまとめて返す評価器が無い。voxel_iou は"
          "次元を見ないので 2-D でも使えるが、名前で見つからない。")
    # (e) 相対放射補正(線形)が無い。histogram_match は在る。
    assert hasattr(fs, "histogram_match")
    print("  (e) 線形の相対放射補正(利得・オフセットを頑健に当てはめる)が無い。"
          "histogram_match(順位で分布を合わせる)は在るが、変化そのものを分布差として消しにかかる"
          "(6 節)ので代わりにならない。")
    # (f) piv_cross_correlate の ledger 経路は info を返さない(docstring は (flow, info))。
    fl = fs.ledger.piv_cross_correlate(np.zeros((64, 64)) + np.random.default_rng(0).random((64, 64)),
                                        np.random.default_rng(0).random((64, 64)), window=32)
    assert isinstance(fl, np.ndarray) and fl.shape[0] == 2
    print("  (f) piv_cross_correlate の docstring は「(flow, info) を返す」と言うが、ledger 経路は"
          "flow (2,h,w) だけを返す —— 窓の中心座標(info[\"rows\"/\"cols\"])が取れないので"
          "この PoC は窓の格子を自分で計算した(格子の規約が変わると黙ってずれる)。")


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.perf_counter()
    print("=" * 78)
    print("変化検出は位置合わせ誤差でどう壊れるか —— 偽陽性はエッジの帯、しきい値の崖つき")
    print("%d x %d px / PSF σ %.1f px / 雑音 σ %.3f / しきい値 τ %.2f" % (N, N, PSF, NOISE, TAU))
    print("=" * 78)

    sc = section_scene()
    sh = section_shift(sc)
    ro = section_rotation(sc, sh)
    sz = section_size()
    rg = section_registration(sc, sh)
    ct = section_controls(sc)
    section_figure(sc)
    section_tool_gaps()

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    d = sh["deltas"]
    print("  * 偽陽性はずれ %.2f px まで雑音の床(≤20 px)、%.2f px から崖(予測 δ*=%.3f px)。3 px で %d px。"
          % (max(x for x, f in zip(d, sh["fp"]) if f <= 20), sh["first"], sh["onset"], sh["fp"][-1]))
    print("  * 比例則(エッジ総長 %.0f px × δ)は 3 px で実測の %.2f 倍、PSF 込みは %.2f 倍、"
          "森林テクスチャを足すと %.2f 倍。"
          % (sh["Lproj"], sh["predA"][-1] / sh["fp"][-1], sh["predB"][-1] / sh["fp"][-1],
             sh["predC"][-1] / sh["fp"][-1]))
    i1 = ro["thetas"].index(1.0)
    print("  * 回転 1 度: 中心 32 px 以内 %.1f %% / 96 px 以遠 %.1f %%。"
          % (ro["dens"][i1][0], (ro["dens"][i1][3] + ro["dens"][i1][4]) / 2))
    print("  * 位置合わせ 3 経路の残留 %.3f〜%.3f px、位相相関(整数)%.3f px。"
          % (min(r[2] for r in rg["good"]), max(r[2] for r in rg["good"]), rg["phase"][2]))
    il = ct["照明差だけ"]
    print("  * 照明差だけの偽陽性 %d px → 放射補正で %d px。ずれだけ %d px は補正しても %d px。"
          % (il[0], il[1], ct["ずれだけ(1.3/−0.8 px)"][0], ct["ずれだけ(1.3/−0.8 px)"][1]))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    # --- 所見を固定する(壊れたら鳴る) ---------------------------------------- #
    assert sh["fp"][d.index(0.3)] <= 20, "0.3 px で雑音の床を超える偽陽性が出た"
    assert sh["fp"][d.index(0.5)] > 100, "0.5 px で崖が始まらない"
    assert 0.6 < sh["predA"][-1] / sh["fp"][-1] < 1.4, "比例則が 3 px で桁で外れた"
    assert ro["dens"][i1][0] < 1.0 and ro["dens"][i1][4] > 1.5, "回転の中央/端の差が消えた"
    assert sz["worst"] < 0.08, "大きさの崖の予測が外れた"
    assert sz["open"][0.0][0] == 0.0 and sz["open"][0.0][1] == 0.0, "オープニングが 1〜2 px を消さない"
    assert max(r[2] for r in rg["good"]) < 0.1, "位置合わせ 3 経路の残留が 0.1 px を超えた"
    assert rg["phase"][2] > 0.2, "位相相関(整数)の残留が小さすぎる(2-D 経路が増えた?)"
    assert il[0] > 300 and il[1] < 50, "照明差の対照群が崩れた"
    assert sc["ev0"]["recall"][CHANGE_TYPES[1]] < 0.7, "伐採の検出率が上がった(樹冠の設定が変わった?)"

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
