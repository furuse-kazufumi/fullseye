# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""はんだフィレットの外観検査(AOI)—— 3 リング照明は傾斜の 3 段量子化器で、高さの 7 割は暗部にある。

基板に実装したチップ部品(1608)のはんだフィレットを、仰角の違う 3 つのリング
照明(低 = 赤、中 = 緑、天頂 = 青)で撮り、面の傾きを色に写して 良品 / はんだ不足 /
ブリッジ / 浮き(tombstone)を判定する仕事です。鏡面に近いはんだは「リング c の
仰角の窓に入る傾き」でだけリング c の色を返すので、**色の並び = 傾きの並び**になる。
その並びからフィレットの高さを推定し、IPC-A-610 風の受け入れ基準
(フィレット高さ ≥ 電極高さの 25 %)で締める。

EXTEND: 実機に差し替えるなら :func:`render` の代わりに撮影画像を、
:func:`fillet_shape` の代わりに X 線 CT や断面研磨で測ったフィレット断面を
真値に置く。**リングごとの仰角の窓と、はんだの接触角 θ は装置・工程の定数**として
先に測っておくこと(この PoC の推定器 E2 はその 2 つを既知として使う)。
:func:`ring_lut` は GGX(``fullseye.brdf_microfacet``)で計算しているが、
実機では鏡面球(既知の傾き)を撮って同じ表(傾き → 3 色)を作る。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. ★★**フィレット高さの 71 % は、どのリングにも照らされない暗部にある**。
   接触角 θ = 18° の凹円弧は壁で 72° まで立つが、いちばん低いリング(仰角 10°)
   でも鏡面反射で見えるのは傾き 40° まで。幾何の予測は「見える高さ = 28.8 %」、
   色帯の傾きを素朴に積分する推定器 E1 の実測は真値の 0.276 倍(相関 0.9926)。
   **色を積分してもフィレットの高さは出ない** —— 出るのは見えている裾の高さだけ。
2. ★**色そのものではなく、色が変わる位置がフィレットを決める**。円弧なら傾き α の
   点は x = x_c − R sin α に並ぶので、青→緑(θ)/緑→赤(30°)/赤→暗(40°)の
   境界位置 2〜3 点から R と中心が決まり、壁まで外挿できる(推定器 E2)。
   自由な円弧の範囲で相対誤差の中央値 -0.6 %(ばらつき 6.2 %)、真値との
   相関 0.9973。境界の位置精度 ±0.5 px が R の誤差にそのまま乗るので、
   IPC 境界(h/H = 0.25、緑帯 5.6 px)では ±9 % の予測に対し実測 6.2 %。
3. ★**はんだ量が増えて爪先(toe)がパッド端に固定されると E2 は下に外れる**。
   自由円弧が成り立つのは V ≤ 0.0243 mm³ まで(予測)。固定後は爪先の傾きが θ
   より立つので、青→緑境界を「傾き θ」と読む E2 は R を小さく見積もる
   (V = 0.030 mm³ で -19.5 %)。ただしそこは h/H ≥ 0.67 なので合否は変わらない。
4. **合否の崖は IPC 境界の両側 ±0.023(h/H)**。境界付近を一様に 200 点振ると、
   |h/H − 0.25| < 0.023 の帯の中で誤判定 22.9 %、外では 0.5 %。
   はんだ量の推定誤差(6 %)と合否の誤り率(帯の幅)は別の量で、後者は
   「境界からどれだけ離れた個体が多いか」という工程の分布次第。
5. ★**部品の位置ずれ 0.16 mm で良品が「不足」に化ける**(はんだ量は同じ)。
   ずれた側の爪先の余地は 0.3 − Δx。余地がフィレット高さ 0.172 mm を切ると
   爪先が固定されて面が立ち、爪先の傾きが 40° を超えた瞬間に
   **フィレット全体が暗部に落ちて色帯が消える**。幾何の予測は Δx = 0.16 mm、
   実測の反転も 0.16 mm。真値の高さはむしろ**上がっている**(0.172 → 0.207 mm)
   ので、見えなくなった瞬間の誤判定はすべて「良品を不足と言う」向き。
   真値が本当に不足に落ちるのは Δx = 0.28 mm で、その間 0.12 mm が誤判定の窓。
6. ★**表面粗さは「色帯が消える」より前に「暗部が明るくなる」で効く**。GGX の
   粗さを 0.1 → 0.8 に振ると、赤帯が緑に負けて消えるのは表(LUT)の予測で
   0.60、実測の赤帯消失も 0.60。しかし E2 の誤差はもっと早く 0.40 で +12 % を
   超える —— ローブが広がって 40° より立った面にも光が漏れ、暗→色の境界が壁側へ
   動く(E2 はそれを 40° と読む)。**リングの分離が壊れる前に、暗部の定義が壊れる**。
7. **照明むらは鏡面ほど効かない**。赤リングだけ +u % 明るくしても、粗さ 0.15 では
   緑→赤の境界は u = 20 % まで 0 px しか動かない(境界がほぼ階段だから)。
   粗さ 0.40 では u = 20 % で 1.0 px(予測 1.4 px)。
8. ★**ゼロ点(パッド平均色の距離)は「不良である」までしか言えない**。
   良品 / 不足 / ブリッジ / 浮きの 4 種で、ゼロ点は良品 100 % / 不足 100 % /
   ブリッジ 0 % / 浮き 100 % を NG にした —— ブリッジはパッドの外で起きるので
   パッド平均色には出ない。E2 系の判定は 4 種の混同行列で正答 良品 98 % /
   不足 98 % / ブリッジ 100 % / 浮き 86 %。浮きの取りこぼしは全て**持ち上がり角
   15° 未満**で、電極上面がまだ青(天頂リングの窓の中)にいる個体 —— 判定は「不足」
   に落ちる。持ち上がり角の小さい浮きと不足は、この照明では原理的に区別できない。

【グラウンドトゥルース】
パッド・電極・部品の幾何は 1608 の推奨ランド(閉形式の矩形)。フィレット断面は
**接触角 θ と断面積 A で決まる円弧**(重力を無視した定曲率面): 自由な円弧
(壁・パッドとも接触角 θ)→ 爪先がパッド端で固定 → 壁の上端で固定、の 3 段を
面積で単調に繋ぐ(面積は 400 点の多角形求積、誤差 1e-6 未満)。傾き α の
リング応答は ``fullseye.brdf_microfacet``(GGX + Smith + Schlick)を各リングの
仰角の窓と全方位で数値積分した 1-D の表。ブリッジは隣接パッドを跨ぐ円弧断面の
畝、浮きは片端を軸に角 ψ だけ回した剛体。位置ずれ・粗さ・照明むら・雑音は
それぞれ独立に振れる。

来歴(公開文献のみ): IPC-A-610 *Acceptability of Electronic Assemblies*(チップ
部品の端部フィレット高さ F ≥ 25 % H)/ Trowbridge & Reitz, *JOSA* 65 (1975) 531
(GGX 分布)/ Walter et al., *EGSR* (2007)(マイクロファセット BRDF)/
Capella, *Proc. NEPCON* (1990) —— 多段リング照明による三色 AOI の原理。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 場面の諸元(単位 mm) ----------------------------------------------------- #
PX_MM = 0.006               # 1 画素 = 6 µm
FOV_X = (-1.35, 1.35)       # 視野 [mm]
FOV_Y = (-0.65, 1.05)
PAD_X = (0.3, 1.1)          # パッドの x 範囲(右。左は符号反転)
PAD_HY = 0.5                # パッドの y 半幅
NEIGHBOR_Y = (0.8, 1.8)     # 隣の部品のパッド(ブリッジ相手)
BODY_L = 1.6                # 部品の長さ
BODY_HY = 0.4               # 部品・電極の y 半幅
H = 0.45                    # 部品(= 電極)の高さ
ELEC_L = 0.3                # 電極の長さ(上面)
TOE = PAD_X[1] - BODY_L / 2  # 爪先の余地 = 0.3 mm(ずれ無しのとき)
THETA = 18.0                # はんだの接触角 [deg]
IPC_MIN = 0.25              # 受け入れ: フィレット高さ ≥ 25 % H
BRIDGE_X = (0.55, 0.85)     # ブリッジの首の x 範囲
BRIDGE_Y = (0.42, 0.88)     # ブリッジの弦(パッドに 0.08 ずつ乗る)

#: リングの仰角の窓 [deg](水平から)。鏡面なら傾き α の面は仰角 90-2α の光を返す。
RINGS = {"R": (10.0, 30.0), "G": (30.0, 60.0), "B": (60.0, 90.0)}
TILT_MAX = 40.0             # いちばん低いリングでも見える最大の傾き = (90-10)/2
ROUGH_REF = 0.15            # 基準の粗さ(GGX)
NOISE = 0.012               # 撮像雑音 σ
V_DARK = 0.4                # これ未満の明るさは「暗部」
SEED = 7

ALBEDO = {"board": (0.07, 0.22, 0.10), "body": (0.05, 0.05, 0.05),
          "solder": (0.05, 0.05, 0.05)}
MAT_BOARD, MAT_SOLDER, MAT_BODY = 0, 1, 2

_LAB = fs.ledger


# --------------------------------------------------------------------------- #
# フィレット断面 —— 接触角と面積で決まる円弧                                     #
# --------------------------------------------------------------------------- #
def _arc_area(h: float, L: float, cx: float, cz: float, R: float, n: int = 400) -> float:
    """壁 (0,0)-(0,h)、パッド (0,0)-(L,0)、円弧 W→P で囲む面積(多角形求積)。"""
    aw = np.arctan2(h - cz, 0.0 - cx)
    ap = np.arctan2(0.0 - cz, L - cx)
    d = (aw - ap + np.pi) % (2 * np.pi) - np.pi          # 短いほうの弧
    ang = ap + d * np.linspace(0.0, 1.0, n)
    px = np.r_[0.0, L, cx + R * np.cos(ang), 0.0]
    pz = np.r_[0.0, 0.0, cz + R * np.sin(ang), h]
    return float(0.5 * abs(np.dot(px, np.roll(pz, -1)) - np.dot(pz, np.roll(px, -1))))


def _circle_wall_tangent(h: float, L: float, th: float):
    """壁 (0,h) で接触角 th、パッド上の点 (L,0) を通る円。"""
    R = (L * L + h * h) / (2.0 * (L * np.cos(th) - h * np.sin(th)))
    return R * np.cos(th), h + R * np.sin(th), R


def _circle_pad_tangent(h: float, L: float, th: float):
    """パッド (L,0) で接触角 th、壁上の点 (0,h) を通る円(上と x↔z 対称)。"""
    R = (L * L + h * h) / (2.0 * (h * np.cos(th) - L * np.sin(th)))
    return L + R * np.sin(th), R * np.cos(th), R


def _circle_bisector(h: float, L: float, t: float):
    """弦 W-P の垂直二等分線上、中点から空気側へ t の位置に中心を置く円。"""
    c = float(np.hypot(L, h))
    cx = L / 2.0 + t * h / c
    cz = h / 2.0 + t * L / c
    return cx, cz, float(np.sqrt(c * c / 4.0 + t * t))


def _bisect(fn, lo: float, hi: float, target: float, it: int = 60) -> float:
    """fn が単調増加のとき fn(x) = target を二分法で解く。"""
    flo, fhi = fn(lo), fn(hi)
    inc = fhi > flo
    for _ in range(it):
        mid = 0.5 * (lo + hi)
        if (fn(mid) < target) == inc:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def fillet_shape(area: float, toe_max: float, theta: float = THETA,
                 h_max: float = H) -> dict:
    """断面積 ``area`` のフィレットの円弧(局所座標: 壁 x=0、パッド z=0)。

    3 段: 自由(壁もパッドも接触角 θ)→ 短いほうが固定(爪先 or 壁上端)→
    両端固定(壁の接触角が θ → 0 に減る)。面積はどの段でも単調なので二分法。
    それでも入らない量は ``clamped`` として最大形状で止める(実物なら側面や
    部品の下へ回る)。
    """
    th = np.deg2rad(theta)
    if toe_max <= 1e-4 or h_max <= 1e-4 or area <= 0.0:
        # 余地が無い(電極がパッド端に乗っている): 端部フィレットは作れない
        return _pack(0.0, 0.0, 0.0, 0.0, 1.0, "clamped", th)
    k = np.cos(th) - np.sin(th)
    g = np.cos(th) * k - (np.pi / 4.0 - th)
    R_free = float(np.sqrt(area / g))
    h_free = R_free * k
    lim = min(toe_max, h_max)
    if h_free <= lim:
        cx = cz = R_free * np.cos(th)
        return _pack(h_free, h_free, cx, cz, R_free, "free", th)

    toe_first = toe_max <= h_max
    if toe_first:                                   # 爪先固定、h が伸びる
        L = toe_max
        h_hi = min(h_max, 0.999 * L / np.tan(th))

        def area_h(h):
            return _arc_area(h, L, *_circle_wall_tangent(h, L, th))
        if area_h(h_hi) >= area:
            h = _bisect(area_h, L, h_hi, area)
            return _pack(h, L, *_circle_wall_tangent(h, L, th), "toe_pinned", th)
        h = h_hi
    else:                                           # 壁上端固定、L が伸びる
        h = h_max
        L_hi = min(toe_max, 0.999 * h / np.tan(th))

        def area_L(L):
            return _arc_area(h, L, *_circle_pad_tangent(h, L, th))
        if area_L(L_hi) >= area:
            L = _bisect(area_L, h, L_hi, area)
            return _pack(h, L, *_circle_pad_tangent(h, L, th), "wall_pinned", th)
        L = L_hi

    # 両端固定: 接触角を減らして(中心を弦へ寄せて)面積を増やす
    c = float(np.hypot(L, h))
    cx0, cz0, _ = (_circle_wall_tangent(h, L, th) if toe_first
                   else _circle_pad_tangent(h, L, th))
    n = np.array([h, L]) / c
    t_theta = float(np.dot(np.array([cx0 - L / 2.0, cz0 - h / 2.0]), n))
    t_min = max(h * c / (2.0 * L), L * c / (2.0 * h))   # 壁またはパッドで接線が接する

    def area_t(t):
        return _arc_area(h, L, *_circle_bisector(h, L, t))
    if area_t(t_min) >= area:
        t = _bisect(area_t, t_min, t_theta, area)
        return _pack(h, L, *_circle_bisector(h, L, t), "both_pinned", th)
    return _pack(h, L, *_circle_bisector(h, L, t_min), "clamped", th)


def _pack(h, L, cx, cz, R, regime, th) -> dict:
    tilt_toe = float(np.rad2deg(np.arcsin(np.clip((cx - L) / R, -1.0, 1.0))))
    tilt_wall = float(np.rad2deg(np.arcsin(np.clip(cx / R, -1.0, 1.0))))
    return {"h": float(h), "L": float(L), "cx": float(cx), "cz": float(cz),
            "R": float(R), "regime": regime, "area": _arc_area(h, L, cx, cz, R),
            "tilt_toe": tilt_toe, "tilt_wall": tilt_wall}


def area_for_height(h_target: float, theta: float = THETA) -> float:
    """自由円弧で高さ h になる断面積(閉形式の逆)。"""
    th = np.deg2rad(theta)
    k = np.cos(th) - np.sin(th)
    g = np.cos(th) * k - (np.pi / 4.0 - th)
    R = h_target / k
    return float(g * R * R)


ELEC_W = 2 * BODY_HY        # 電極幅 = フィレットの奥行き


def volume_to_area(v_mm3: float) -> float:
    return v_mm3 / ELEC_W


# --------------------------------------------------------------------------- #
# リング照明の応答表 —— 傾き α → 3 色(fullseye.brdf_microfacet を数値積分)     #
# --------------------------------------------------------------------------- #
LUT_ALPHA = np.linspace(0.0, 89.5, 180)
_LUT_CACHE: dict = {}
_GAIN: dict = {}


def ring_lut(roughness: float) -> dict:
    """傾き α(方位 0)の鏡面が、各リングから返す放射輝度(相対)。

    リングは仰角の窓 × 全方位の連続光源。方位は対数間隔(0.05°〜180°)、仰角は
    0.2° 刻みで台形求積。**カメラは天頂**なので、方位 φ の光と方位 0 の法線の組は
    方位 -φ の法線と方位 0 の光の組と同じ(z 軸回りの対称性)—— 法線側を
    (α, φ) の 2-D 格子にして brdf を 1 回で引く。
    """
    key = round(float(roughness), 6)
    if key in _LUT_CACHE:
        return _LUT_CACHE[key]
    p = np.geomspace(0.05, 180.0, 70)
    phi = np.concatenate([-p[::-1], [0.0], p])
    w_phi = np.gradient(np.deg2rad(phi))
    a = np.deg2rad(LUT_ALPHA)[:, None]
    f = np.deg2rad(phi)[None, :]
    normals = np.stack([np.sin(a) * np.cos(-f), np.sin(a) * np.sin(-f),
                        np.cos(a) * np.ones_like(f)], axis=-1)
    out = {"alpha": LUT_ALPHA.copy()}
    de = np.deg2rad(0.2)
    for name, (e1, e2) in RINGS.items():
        acc = np.zeros(normals.shape[:2])
        for e in np.deg2rad(np.arange(e1 + 0.1, e2, 0.2)):
            light = (float(np.cos(e)), 0.0, float(np.sin(e)))
            ndotl = np.clip(normals @ np.asarray(light), 0.0, None)
            fsv = np.asarray(fs.brdf_microfacet(normals, light=light, view=(0.0, 0.0, 1.0),
                                                roughness=roughness, f0=0.9))
            acc += np.nan_to_num(fsv) * ndotl * np.cos(e) * de
        out[name] = (acc * w_phi[None, :]).sum(axis=1)
    _LUT_CACHE[key] = out
    return out


def ring_gain() -> dict:
    """基準の粗さでリングごとのピークが 0.95 になるカメラ利得(固定)。"""
    if not _GAIN:
        ref = ring_lut(ROUGH_REF)
        for name in RINGS:
            _GAIN[name] = 0.95 / float(ref[name].max())
    return _GAIN


def lut_response(roughness: float) -> dict:
    """利得込みの応答(表示・予測用)。"""
    lut = ring_lut(roughness)
    g = ring_gain()
    return {"alpha": lut["alpha"], **{n: np.clip(lut[n] * g[n], 0.0, 1.0) for n in RINGS}}


# --------------------------------------------------------------------------- #
# 場面を作る                                                                    #
# --------------------------------------------------------------------------- #
NX = int(round((FOV_X[1] - FOV_X[0]) / PX_MM))
NY = int(round((FOV_Y[1] - FOV_Y[0]) / PX_MM))
_XX, _YY = np.meshgrid(FOV_X[0] + (np.arange(NX) + 0.5) * PX_MM,
                       FOV_Y[0] + (np.arange(NY) + 0.5) * PX_MM)


def _rect(x0, x1, y0, y1):
    return (_XX >= x0) & (_XX < x1) & (_YY >= y0) & (_YY < y1)


def make_scene(volume: float, shift: float = 0.0, lift_deg: float = 0.0,
               bridge_h: float = 0.0, theta: float = THETA) -> dict:
    """材質図 + 傾き図 + 真値。``volume`` は片側フィレットの体積 [mm³]。"""
    mat = np.full((NY, NX), MAT_BOARD, np.int8)
    tilt = np.zeros((NY, NX))
    for sx in (-1, 1):
        lo, hi = sorted((sx * PAD_X[0], sx * PAD_X[1]))
        mat[_rect(lo, hi, -PAD_HY, PAD_HY)] = MAT_SOLDER
        mat[_rect(lo, hi, NEIGHBOR_Y[0], NEIGHBOR_Y[1])] = MAT_SOLDER

    area = volume_to_area(volume)
    xl = -BODY_L / 2 + shift                 # 左端面(浮きの軸)
    xr = BODY_L / 2 + shift                  # 右端面
    fil = {}
    # 左フィレット(常に有る)。局所 x = xl - X
    fil["L"] = fillet_shape(area, PAD_X[1] + xl, theta)
    m = _rect(xl - fil["L"]["L"], xl, -BODY_HY, BODY_HY)
    tilt[m] = np.rad2deg(np.arcsin(np.clip((fil["L"]["cx"] - (xl - _XX[m])) / fil["L"]["R"], -1, 1)))
    # 右フィレット(浮きなら無い)
    if lift_deg <= 0.0:
        fil["R"] = fillet_shape(area, PAD_X[1] - xr, theta)
        m = _rect(xr, xr + fil["R"]["L"], -BODY_HY, BODY_HY)
        tilt[m] = np.rad2deg(np.arcsin(np.clip((fil["R"]["cx"] - (_XX[m] - xr)) / fil["R"]["R"], -1, 1)))
    # 部品(左端を軸に ψ だけ持ち上がる)
    psi = np.deg2rad(lift_deg)
    c = float(np.cos(psi))
    body = _rect(xl, xl + BODY_L * c, -BODY_HY, BODY_HY)
    mat[body] = MAT_BODY
    for x0, x1 in ((xl, xl + ELEC_L * c), (xl + (BODY_L - ELEC_L) * c, xl + BODY_L * c)):
        m = _rect(x0, x1, -BODY_HY, BODY_HY)
        mat[m] = MAT_SOLDER
        tilt[m] = lift_deg
    if lift_deg > 0.0:                       # 持ち上がった端面が見える
        m = _rect(xl + BODY_L * c, xl + BODY_L * c + H * np.sin(psi), -BODY_HY, BODY_HY)
        mat[m] = MAT_SOLDER
        tilt[m] = 90.0 - lift_deg
    # ブリッジ(右パッドと隣のパッドを跨ぐ畝)
    if bridge_h > 0.0:
        chord = BRIDGE_Y[1] - BRIDGE_Y[0]
        Rb = (chord * chord / 4.0 + bridge_h * bridge_h) / (2.0 * bridge_h)
        yc = 0.5 * (BRIDGE_Y[0] + BRIDGE_Y[1])
        m = _rect(BRIDGE_X[0], BRIDGE_X[1], BRIDGE_Y[0], BRIDGE_Y[1])
        mat[m] = MAT_SOLDER
        tilt[m] = np.rad2deg(np.arcsin(np.clip(np.abs(_YY[m] - yc) / Rb, -1, 1)))
    tilt = np.clip(tilt, 0.0, 89.5)
    h_l = fil["L"]["h"]
    h_r = fil["R"]["h"] if "R" in fil else 0.0
    if bridge_h > 0.0:
        kind = "bridge"
    elif lift_deg > 0.0:
        kind = "tombstone"
    elif min(h_l, h_r) < IPC_MIN * H:
        kind = "insufficient"
    else:
        kind = "good"
    return {"mat": mat, "tilt": tilt, "fillet": fil, "h": (h_l, h_r), "kind": kind,
            "volume": volume, "shift": shift, "lift": lift_deg, "bridge": bridge_h}


def render(scene: dict, roughness: float = ROUGH_REF, gains=(1.0, 1.0, 1.0),
           noise: float = NOISE, seed: int = 0) -> np.ndarray:
    """材質 + 傾き → RGB。鏡面材は応答表、他は拡散のみ。``gains`` はリングごとの照明むら。"""
    lut = ring_lut(roughness)
    g = ring_gain()
    img = np.zeros((NY, NX, 3))
    cosa = np.cos(np.deg2rad(scene["tilt"]))
    shade = 0.4 + 0.6 * cosa
    for mat_id, key in ((MAT_BOARD, "board"), (MAT_SOLDER, "solder"), (MAT_BODY, "body")):
        m = scene["mat"] == mat_id
        for ch in range(3):
            img[..., ch][m] = ALBEDO[key][ch] * shade[m]
    spec = scene["mat"] == MAT_SOLDER
    for ch, name in enumerate("RGB"):
        img[..., ch][spec] += gains[ch] * g[name] * np.interp(scene["tilt"][spec], lut["alpha"], lut[name])
    rng = np.random.default_rng(seed)
    img += noise * rng.standard_normal(img.shape)
    return np.clip(img, 0.0, 1.0)


# --------------------------------------------------------------------------- #
# 検査 —— fullseye の色 op と領域 op で色帯の位置を読む                           #
# --------------------------------------------------------------------------- #
def _col(x: float) -> int:
    return int(round((x - FOV_X[0]) / PX_MM))


def _row(y: float) -> int:
    return int(round((y - FOV_Y[0]) / PX_MM))


CLASS_TILT = {1: 35.0, 2: 22.5}        # E1 が使うリングごとの代表傾き(窓の中央)


def class_map(img: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """画素ごとに 0 = 暗部 / 1 = 赤 / 2 = 緑 / 3 = 青(支配チャネル)。"""
    chans = [np.asarray(fs.apply(img, "access_channel", a=a)) for a in (0.0, 0.4, 0.8)]
    hsv = np.asarray(fs.apply(img, "trans_from_rgb", a=0.0))      # OpenCV HSV(8bit 経由)
    v = hsv[..., 2]
    cls = np.argmax(np.stack(chans), axis=0).astype(np.int8) + 1
    cls[v < V_DARK] = 0
    return cls, v


def _mode_columns(sub: np.ndarray) -> np.ndarray:
    counts = np.stack([(sub == k).sum(axis=0) for k in range(4)])
    return np.argmax(counts, axis=0)


def _parse_profile(seq: np.ndarray, x_of: np.ndarray, theta: float, xw: float) -> dict:
    """壁 ``xw`` から外へ向かう class 列 → 色境界の位置 → 円弧 → 高さ(E2)と傾き積分(E1)。

    爪先 = 色帯(赤/緑)の外側の端。その先は平らなパッド(青)か、パッド端を越えて
    基板(暗)かのどちらかなので、「赤/緑でなくなる最初の画素」で取る。
    """
    colored = np.nonzero((seq == 1) | (seq == 2))[0]
    if colored.size == 0:
        return {"h2": 0.0, "h1": 0.0, "n_pts": 0, "bands": (0, 0), "x40": None, "x30": None,
                "xtoe": None}
    i0 = int(colored[0])
    after = np.nonzero((seq[i0:] != 1) & (seq[i0:] != 2))[0]
    i_toe = int(i0 + after[0]) if after.size else seq.size
    run = seq[i0:i_toe]
    i30 = None
    if run.size and run[0] == 1:
        gg = np.nonzero(run == 2)[0]
        if gg.size:
            i30 = i0 + int(gg[0])
    half = 0.5 * PX_MM * np.sign(x_of[1] - x_of[0]) if x_of.size > 1 else 0.0
    x40 = x_of[i0] - half
    xtoe = (x_of[i_toe] - half) if i_toe < x_of.size else x_of[-1] + half
    pts = [(TILT_MAX, x40), (theta, xtoe)]
    x30 = None
    if i30 is not None:
        x30 = x_of[i30] - half
        pts.insert(1, (30.0, x30))
    s = np.array([np.sin(np.deg2rad(a)) for a, _ in pts])
    x = np.array([xx for _, xx in pts])
    # 外向きの符号を揃える(左側は x が減る向き)。原点は**壁の推定位置**
    # (最初の列の中心にすると 0〜1 px 外へずれ、壁の傾き 72° では h が 5 % 縮む)。
    sgn = np.sign(x_of[-1] - x_of[0]) if x_of.size > 1 else 1.0
    xo = sgn * (x - xw)                     # 壁を 0 とした外向き距離
    A = np.c_[np.ones_like(s), -s]
    sol, *_ = np.linalg.lstsq(A, xo, rcond=None)
    xc, R = float(sol[0]), float(sol[1])
    if R <= 0.0:
        h2 = 0.0
    else:
        sw = np.clip(xc / R, -1.0, 1.0)
        h2 = R * (np.cos(np.deg2rad(theta)) - np.sqrt(1.0 - sw * sw))
        h2 = max(0.0, float(h2))
    h1 = 0.0
    for k in run:
        if k in CLASS_TILT:
            h1 += np.tan(np.deg2rad(CLASS_TILT[k])) * PX_MM
    return {"h2": h2, "h1": float(h1), "n_pts": len(pts), "R": R, "xc": xc,
            "bands": (int((run == 1).sum()), int((run == 2).sum())),
            "x40": float(x40), "x30": (None if x30 is None else float(x30)), "xtoe": float(xtoe)}


def inspect_image(img: np.ndarray, theta: float = THETA) -> dict:
    """1 枚の画像 → 両側のフィレット高さ推定・浮き・ブリッジ・判定。"""
    cls, v = class_map(img)
    r0, r1 = _row(-0.35), _row(0.35)
    c0, c1 = _col(-1.0), _col(1.0)
    # 部品本体(暗い拡散面)の外接箱 → 電極の外端 = 壁の位置
    dark = np.zeros_like(v, bool)
    dark[r0:r1, c0:c1] = v[r0:r1, c0:c1] < 0.15
    lab = _LAB.blob_select_largest(_LAB.blob_label(dark))
    f = _LAB.blob_features(lab)
    if f["n"] == 0:
        return {"verdict": "unreadable", "h2": (0.0, 0.0), "h1": (0.0, 0.0)}
    x_body_l = FOV_X[0] + float(f["bbox_c0"][0]) * PX_MM
    x_body_r = FOV_X[0] + float(f["bbox_c1"][0]) * PX_MM
    xw = {"L": x_body_l - ELEC_L, "R": x_body_r + ELEC_L}

    pr0, pr1 = _row(-0.3), _row(0.3)
    out = {"xw": xw}
    for side in ("L", "R"):
        if side == "R":
            cs = np.arange(_col(xw["R"]), _col(PAD_X[1] + 0.15))
        else:
            cs = np.arange(_col(xw["L"]) - 1, _col(-PAD_X[1] - 0.15), -1)
        cs = cs[(cs >= 0) & (cs < NX)]
        seq = _mode_columns(cls[pr0:pr1, cs])
        x_of = FOV_X[0] + (cs + 0.5) * PX_MM
        out[side] = _parse_profile(seq, x_of, theta, xw[side])
        # 電極上面: 青(傾き < 15°)のはず。浮けば緑/赤/暗に変わる
        ex0, ex1 = ((xw["R"] - 0.27, xw["R"] - 0.03) if side == "R"
                    else (xw["L"] + 0.03, xw["L"] + 0.27))
        blk = cls[pr0:pr1, _col(ex0):_col(ex1)]
        out[side]["elec_blue"] = float((blk == 3).mean()) if blk.size else 0.0
    # ブリッジ: パッド間の隙間に鏡面(明るい)画素の塊が有るか
    gr0, gr1 = _row(0.53), _row(0.77)
    bridge_area = 0.0
    for sx in (-1, 1):
        lo, hi = sorted((sx * PAD_X[0], sx * PAD_X[1]))
        blk = v[gr0:gr1, _col(lo):_col(hi)] > V_DARK
        lab = _LAB.blob_label(blk)
        if lab.max() > 0:
            fb = _LAB.blob_features(lab, spacing=PX_MM)
            bridge_area = max(bridge_area, float(fb["area"].max()))
    out["bridge_area"] = bridge_area
    h2 = (out["L"]["h2"], out["R"]["h2"])
    h1 = (out["L"]["h1"], out["R"]["h1"])
    out["h2"], out["h1"] = h2, h1
    if bridge_area >= 0.01:
        out["verdict"] = "bridge"
    elif min(out["L"]["elec_blue"], out["R"]["elec_blue"]) < 0.5:
        out["verdict"] = "tombstone"
    elif min(h2) < IPC_MIN * H:
        out["verdict"] = "insufficient"
    else:
        out["verdict"] = "good"
    return out


# --------------------------------------------------------------------------- #
# ゼロ点 —— パッド領域の平均色の距離(ΔE)                                        #
# --------------------------------------------------------------------------- #
def pad_mean_lab(img: np.ndarray) -> np.ndarray:
    """左右パッド(設計位置)の平均 RGB → L*a*b*。(2, 3)。"""
    out = []
    for sx in (-1, 1):
        lo, hi = sorted((sx * PAD_X[0], sx * PAD_X[1]))
        roi = img[_row(-PAD_HY):_row(PAD_HY), _col(lo):_col(hi)]
        mean = [float(fs.apply(np.ascontiguousarray(roi[..., ch]), "intensity")) for ch in range(3)]
        out.append(np.asarray(fs.rgb_to_lab(np.asarray(mean).reshape(1, 1, 3)))[0, 0])
    return np.asarray(out)


class ZeroPoint:
    """黄金サンプルの Lab からの距離で OK/NG。しきい値は校正集合で精度最大に置く。"""

    def __init__(self):
        self.golden = None
        self.thr = None

    def calibrate(self, good_imgs, bad_imgs):
        gl = np.asarray([pad_mean_lab(im) for im in good_imgs])
        self.golden = gl.reshape(-1, 3).mean(axis=0)
        dg = np.asarray([self.distance(im) for im in good_imgs])
        db = np.asarray([self.distance(im) for im in bad_imgs])
        cand = np.unique(np.r_[dg, db])
        acc = [(float(((dg <= t).sum() + (db > t).sum()) / (dg.size + db.size)), float(t)) for t in cand]
        best, self.thr = max(acc)
        return best

    def distance(self, img: np.ndarray) -> float:
        lab = pad_mean_lab(img)
        return float(np.max(np.linalg.norm(lab - self.golden, axis=1)))

    def verdict(self, img: np.ndarray) -> str:
        return "ng" if self.distance(img) > self.thr else "ok"


# --------------------------------------------------------------------------- #
# 1. 応答表 —— 暗部の予測                                                        #
# --------------------------------------------------------------------------- #
def section_lut() -> dict:
    print("\n" + "=" * 78)
    print("1) リングの応答表 —— 傾き α のはんだ面が返す 3 色(GGX を窓で積分)")
    print("=" * 78)
    lut = lut_response(ROUGH_REF)
    print("   リング  仰角の窓      鏡面で見える傾き   応答 ≥ 0.5 の傾き(粗さ %.2f)" % ROUGH_REF)
    edges = {}
    for name, (e1, e2) in RINGS.items():
        on = lut["alpha"][lut[name] >= 0.5]
        edges[name] = (float(on.min()), float(on.max()))
        print("   %s      %4.0f-%4.0f°       %4.1f-%4.1f°          %4.1f-%4.1f°"
              % (name, e1, e2, (90 - e2) / 2, (90 - e1) / 2, on.min(), on.max()))
    th = np.deg2rad(THETA)
    vis_frac = (np.cos(th) - np.cos(np.deg2rad(TILT_MAX))) / (np.cos(th) - np.sin(th))
    print("\n  接触角 θ = %.0f° の凹円弧: 爪先の傾き %.0f°、壁の傾き %.0f°。"
          % (THETA, THETA, 90 - THETA))
    print("  ★予測: 見える(傾き ≤ %.0f°)のは高さの (cos θ - cos %.0f°)/(cos θ - sin θ) = %.1f %%。"
          "残り %.1f %% は暗部。" % (TILT_MAX, TILT_MAX, 100 * vis_frac, 100 * (1 - vis_frac)))
    figs.save_plot("ring_lut", [(n, lut["alpha"], lut[n]) for n in RINGS],
                   xlabel="面の傾き α [deg]", ylabel="相対応答", title="3 リングの応答(粗さ %.2f)" % ROUGH_REF,
                   caption="鏡面なら窓の端が階段になる。傾き 40° を超えるとどのリングも届かない。")
    return {"vis_frac": float(vis_frac), "edges": edges}


# --------------------------------------------------------------------------- #
# 2. 場面と 1 個の断面                                                          #
# --------------------------------------------------------------------------- #
def section_scene() -> dict:
    print("\n" + "=" * 78)
    print("2) 場面 —— 良品 / 不足 / ブリッジ / 浮き")
    print("=" * 78)
    v_thr = area_for_height(IPC_MIN * H) * ELEC_W
    v_pin = area_for_height(TOE) * ELEC_W
    print("  片側フィレットの体積: IPC 境界(h = %.4f mm)%.4f mm³ / 爪先が固定される %.4f mm³"
          % (IPC_MIN * H, v_thr, v_pin))
    cases = [("良品", dict(volume=2.5 * v_thr)), ("はんだ不足", dict(volume=0.4 * v_thr)),
             ("ブリッジ", dict(volume=2.5 * v_thr, bridge_h=0.10)),
             ("浮き(ψ=25°)", dict(volume=2.5 * v_thr, lift_deg=25.0))]
    panels, caps = [], []
    for i, (name, kw) in enumerate(cases):
        sc = make_scene(**kw)
        im = render(sc, seed=i)
        r = inspect_image(im)
        print("   %-12s 真値 %-12s h = %.3f/%.3f mm  E2 %.3f/%.3f  判定 %s"
              % (name, sc["kind"], sc["h"][0], sc["h"][1], r["h2"][0], r["h2"][1], r["verdict"]))
        panels.append(im)
        caps.append("%s(判定 %s)" % (name, r["verdict"]))
    figs.save_grid("scene_grid", panels, caps, ncols=2,
                   title="3 リング AOI の見え方(赤 = 30-40°、緑 = 15-30°、青 = 平ら)",
                   caption="フィレットの壁側は暗い。ブリッジは隣のパッドへ渡る畝、浮きは電極上面の色で分かる。")

    sc = make_scene(volume=2.5 * v_thr)
    im = render(sc, seed=0)
    r = inspect_image(im)
    cls, _ = class_map(im)
    fR = sc["fillet"]["R"]
    xs = np.linspace(0.0, fR["L"], 200)
    z_true = fR["cz"] - np.sqrt(np.clip(fR["R"] ** 2 - (fR["cx"] - xs) ** 2, 0, None))
    pr = r["R"]
    th = np.deg2rad(THETA)
    z_est = pr["xc"] * 0 + (pr["R"] * np.cos(th) - np.sqrt(np.clip(pr["R"] ** 2 - (pr["xc"] - xs) ** 2, 0, None)))
    print("  右フィレット: 真値 h %.4f L %.4f R %.4f / E2 の円弧 R %.4f x_c %.4f → h %.4f(%+.1f %%)"
          % (fR["h"], fR["L"], fR["R"], pr["R"], pr["xc"], pr["h2"], 100 * (pr["h2"] / fR["h"] - 1)))
    print("     色帯: 赤 %d px 緑 %d px、境界 x40 %.4f x30 %s xtoe %.4f(壁 %.4f)"
          % (pr["bands"][0], pr["bands"][1], pr["x40"], "%.4f" % pr["x30"] if pr["x30"] else "-",
             pr["xtoe"], r["xw"]["R"]))
    figs.save_grid("tilt_map", [np.clip(sc["tilt"], 0, 90) / 90.0, cls.astype(np.float64) / 3.0],
                   ["真値の傾き(0-90°)", "支配チャネル(暗/赤/緑/青)"], ncols=2,
                   title="傾きの真値と、色から読んだ 4 値")
    figs.save_plot("fillet_profile",
                   [("真値の断面", xs, z_true), ("E2 の円弧(境界 3 点から)", xs, z_est)],
                   xlabel="壁からの距離 [mm]", ylabel="高さ [mm]", title="フィレット断面(右)",
                   caption="見えるのは傾き 40° までの裾。E2 は円弧を壁まで外挿する。")
    return {"v_thr": v_thr, "v_pin": v_pin}


# --------------------------------------------------------------------------- #
# 3. はんだ量を振る —— E1 / E2 と真値                                           #
# --------------------------------------------------------------------------- #
def section_volume(v_thr: float, v_pin: float, vis_frac: float) -> dict:
    print("\n" + "=" * 78)
    print("3) はんだ量を振る —— 色の積分(E1)と境界の位置(E2)")
    print("=" * 78)
    vols = np.geomspace(0.0006, 0.035, 36)
    ht, h1, h2, reg = [], [], [], []
    for i, v in enumerate(vols):
        for s in range(3):
            sc = make_scene(volume=v)
            r = inspect_image(render(sc, seed=100 * i + s))
            ht.append(sc["h"][1])
            h1.append(r["R"]["h1"])
            h2.append(r["R"]["h2"])
            reg.append(sc["fillet"]["R"]["regime"])
    ht, h1, h2 = map(np.asarray, (ht, h1, h2))
    reg = np.asarray(reg)
    free = reg == "free"
    ok = ht > 0.03
    ratio1 = float(np.median(h1[free & ok] / ht[free & ok]))
    c1 = float(np.corrcoef(h1[ok], ht[ok])[0, 1])
    c2 = float(np.corrcoef(h2[ok], ht[ok])[0, 1])
    rel2 = 100 * (h2[free & ok] / ht[free & ok] - 1)
    print("   体積 [mm³]  真値 h   E1 積分   E1/真値   E2 円弧   E2 誤差   段")
    for i in range(0, len(vols), 5):
        j = 3 * i
        print("   %8.5f   %.4f   %.4f    %.3f    %.4f   %+6.1f %%   %s"
              % (vols[i], ht[j], h1[j], h1[j] / ht[j], h2[j], 100 * (h2[j] / ht[j] - 1), reg[j]))
    print("\n  ★E1(色帯の傾きを積分)は真値の %.3f 倍(自由円弧、中央値)。予測 %.3f。"
          "相関 %.4f。" % (ratio1, vis_frac, c1))
    print("  ★E2(境界位置 → 円弧 → 壁へ外挿)は自由円弧で相対誤差 中央値 %+.1f %%、"
          "ばらつき(MAD×1.48)%.1f %%、相関 %.4f。" % (np.median(rel2), 1.48 * np.median(np.abs(rel2 - np.median(rel2))), c2))
    pinned = (reg != "free") & ok
    if pinned.any():
        relp = 100 * (h2[pinned] / ht[pinned] - 1)
        print("  ★爪先が固定される V > %.4f mm³ では E2 は %+.1f %% 〜 %+.1f %%(下に外れる: "
              "爪先の傾きが θ より立つのに θ と読むから)。" % (v_pin, relp.max(), relp.min()))
        jmax = int(np.argmax(vols >= 0.03)) * 3
        print("     V = %.3f mm³ で %+.1f %%(h/H = %.2f、合否は変わらない)"
              % (vols[jmax // 3], 100 * (h2[jmax] / ht[jmax] - 1), ht[jmax] / H))
    figs.save_plot("volume_sweep",
                   [("真値", ht, ht), ("E2 境界位置の円弧", ht, h2), ("E1 色の積分", ht, h1)],
                   xlabel="真値のフィレット高さ [mm]", ylabel="推定 [mm]",
                   title="はんだ量を振る(片側 %.4f〜%.3f mm³)" % (vols[0], vols[-1]),
                   caption="E1 は 0.28 倍の直線に乗る(暗部を見ていない)。E2 は爪先固定から下に外れる。")
    return {"ratio1": ratio1, "c1": c1, "c2": c2, "rel2_med": float(np.median(rel2)),
            "rel2_mad": float(1.48 * np.median(np.abs(rel2 - np.median(rel2)))),
            "relp": (float(relp.min()) if pinned.any() else 0.0),
            "v030": float(100 * (h2[jmax] / ht[jmax] - 1)) if pinned.any() else 0.0}


# --------------------------------------------------------------------------- #
# 4. 合否の崖 —— IPC 境界のまわり                                                #
# --------------------------------------------------------------------------- #
def section_boundary(zp: ZeroPoint) -> dict:
    print("\n" + "=" * 78)
    print("4) 合否の崖 —— IPC 境界(h/H = %.2f)の両側を一様に振る" % IPC_MIN)
    print("=" * 78)
    rng = np.random.default_rng(SEED + 1)
    n = 200
    ratios = rng.uniform(0.15, 0.35, n)
    err, err0, d = [], [], []
    for i, rr in enumerate(ratios):
        v = area_for_height(rr * H) * ELEC_W
        sc = make_scene(volume=v)
        im = render(sc, seed=1000 + i)
        r = inspect_image(im)
        truth = sc["kind"]
        err.append(r["verdict"] != truth)
        err0.append((zp.verdict(im) == "ng") != (truth != "good"))
        d.append(sc["h"][1] / H - IPC_MIN)
    err, err0, d = map(np.asarray, (err, err0, d))
    # 帯の幅: 誤判定が出た |d| の最大値
    band = float(np.abs(d[err]).max()) if err.any() else 0.0
    inside = np.abs(d) < band
    print("   |h/H - 0.25| の帯      個体数   E2 判定の誤り   ゼロ点の誤り")
    for lo, hi in ((0.0, 0.01), (0.01, 0.02), (0.02, 0.03), (0.03, 0.05), (0.05, 0.10)):
        m = (np.abs(d) >= lo) & (np.abs(d) < hi)
        if m.any():
            print("   %.2f - %.2f              %4d      %5.1f %%         %5.1f %%"
                  % (lo, hi, m.sum(), 100 * err[m].mean(), 100 * err0[m].mean()))
    print("\n  ★誤判定が出る帯は |h/H - 0.25| < %.3f。帯の中で %.1f %%、外で %.1f %%。"
          % (band, 100 * err[inside].mean() if inside.any() else 0.0,
             100 * err[~inside].mean() if (~inside).any() else 0.0))
    print("     予測: 境界の位置 ±0.5 px が緑帯 %.1f px に対して ±%.0f %% → 帯 ±%.3f。"
          % (0.191 * (IPC_MIN * H / 0.642) / PX_MM,
             100 * 0.5 / (0.191 * (IPC_MIN * H / 0.642) / PX_MM),
             IPC_MIN * 0.5 / (0.191 * (IPC_MIN * H / 0.642) / PX_MM)))
    print("  ゼロ点(ΔE のしきい値)は同じ帯で %.1f %%、外で %.1f %%。"
          % (100 * err0[inside].mean() if inside.any() else 0.0,
             100 * err0[~inside].mean() if (~inside).any() else 0.0))
    order = np.argsort(d)
    bins = np.linspace(-0.10, 0.10, 11)
    xs, ys, y0 = [], [], []
    for lo, hi in zip(bins[:-1], bins[1:]):
        m = (d >= lo) & (d < hi)
        if m.any():
            xs.append(0.5 * (lo + hi))
            ys.append(100 * err[m].mean())
            y0.append(100 * err0[m].mean())
    figs.save_plot("boundary_error", [("E2 判定", xs, ys), ("ゼロ点 ΔE", xs, y0)],
                   xlabel="h/H - 0.25(真値)", ylabel="誤判定率 [%]",
                   title="IPC 境界のまわりの誤判定(200 個体)",
                   caption="推定誤差 6 % の帯の中だけで誤る。帯の外は 0 に近い。")
    return {"band": band, "in": float(100 * err[inside].mean()) if inside.any() else 0.0,
            "out": float(100 * err[~inside].mean()) if (~inside).any() else 0.0}


# --------------------------------------------------------------------------- #
# 5. 位置ずれ —— 良品が不足に化ける点                                            #
# --------------------------------------------------------------------------- #
def section_shift(v_thr: float) -> dict:
    print("\n" + "=" * 78)
    print("5) 部品の位置ずれ 0 → 0.3 mm —— はんだ量は同じなのに良品が「不足」になる")
    print("=" * 78)
    v = 2.5 * v_thr
    shifts = np.round(np.arange(0.0, 0.301, 0.02), 3)
    print("  片側 V = %.4f mm³(ずれ無しで h = %.3f mm = %.2f H)" % (v, make_scene(volume=v)["h"][1],
                                                                  make_scene(volume=v)["h"][1] / H))
    print("   Δx [mm]  爪先余地  段            真値 h    爪先傾き  予測(見える?)  E2 h    「不足」判定率")
    frac, htrue, hest, pred_vis, truth_ins = [], [], [], [], []
    for dx in shifts:
        sc = make_scene(volume=v, shift=dx)
        fR = sc["fillet"]["R"]
        vis = fR["tilt_toe"] < TILT_MAX and fR["R"] * (np.sin(np.deg2rad(TILT_MAX)) - np.sin(np.deg2rad(fR["tilt_toe"]))) >= PX_MM
        ins = []
        hs = []
        for s in range(4):
            r = inspect_image(render(sc, seed=2000 + s))
            ins.append(r["verdict"] == "insufficient")
            hs.append(r["R"]["h2"])
        frac.append(100 * float(np.mean(ins)))
        htrue.append(fR["h"])
        hest.append(float(np.mean(hs)))
        pred_vis.append(vis)
        truth_ins.append(sc["kind"] == "insufficient")
        print("   %5.2f     %5.2f   %-12s  %.4f    %5.1f°    %-5s         %.4f     %5.0f %%"
              % (dx, TOE - dx, fR["regime"], fR["h"], fR["tilt_toe"], "見える" if vis else "暗い",
                 hest[-1], frac[-1]))
    frac = np.asarray(frac)
    pred_cliff = next((float(s) for s, p in zip(shifts, pred_vis) if not p), None)
    meas_cliff = next((float(s) for s, fr in zip(shifts, frac) if fr >= 50), None)
    truth_cliff = next((float(s) for s, t in zip(shifts, truth_ins) if t), None)
    i_p = int(np.argmax(shifts >= pred_cliff)) if pred_cliff is not None else 0
    print("\n  ★予測の崖(爪先の傾きが %.0f° を超えて色帯が消える)Δx = %.2f mm、"
          "実測の反転(不足判定 ≥ 50 %%)Δx = %s mm。" % (TILT_MAX, pred_cliff, "%.2f" % meas_cliff if meas_cliff is not None else "無し"))
    print("     そこで真値の h は %.3f → %.3f mm と**上がって**いる(面が立つだけ)。"
          % (htrue[0], htrue[i_p]))
    print("     真値が本当に不足になるのは Δx = %s mm。その間は全て「良品を不足と言う」誤判定。"
          % ("%.2f" % truth_cliff if truth_cliff is not None else "範囲内に無し"))
    figs.save_plot("shift_cliff",
                   [("真値 h", shifts, htrue), ("E2 h", shifts, hest),
                    ("IPC 境界", shifts, [IPC_MIN * H] * len(shifts))],
                   xlabel="部品の位置ずれ Δx [mm]", ylabel="右フィレット高さ [mm]",
                   title="ずれると面が立ち、色帯が消える(V 一定)",
                   caption="爪先の余地が減るほど真値は上がるが、傾き 40° を超えた瞬間に推定は 0 になる。")
    figs.save_plot("shift_verdict", [("「不足」判定率", shifts, frac)],
                   xlabel="部品の位置ずれ Δx [mm]", ylabel="不足と判定した割合 [%]",
                   title="良品が不足に化ける点(予測 %.2f mm)" % pred_cliff)
    return {"pred": pred_cliff, "meas": meas_cliff, "truth": truth_cliff,
            "h0": htrue[0], "h_at": htrue[i_p]}


# --------------------------------------------------------------------------- #
# 6. 表面粗さ —— リングの分離が壊れる点                                          #
# --------------------------------------------------------------------------- #
def section_roughness(v_thr: float) -> dict:
    print("\n" + "=" * 78)
    print("6) 表面粗さ(GGX)0.1 → 0.8 —— 赤帯が消える点と、暗部が明るくなる点")
    print("=" * 78)
    roughs = (0.10, 0.15, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80)
    v = 2.0 * v_thr
    sc = make_scene(volume=v)
    fR = sc["fillet"]["R"]
    print("  V = %.4f mm³、真値 h = %.4f mm。表(LUT)から予測 → 実測。" % (v, fR["h"]))
    print("   粗さ   ピーク R/G/B      赤が勝つ傾き   暗部の始まり   予測 E2 h   実測 E2 h   誤差    赤帯 px   合否誤り")
    rows, errs, redpx, pred_h = [], [], [], []
    r_red_gone_pred, r_red_gone_meas, r_err_cliff, r_all_dark = None, None, None, None
    for rgh in roughs:
        lut = lut_response(rgh)
        peaks = [float(lut[n].max()) for n in RINGS]
        dom = (lut["R"] > lut["G"]) & (lut["R"] > lut["B"]) & (lut["R"] >= V_DARK)
        red_rng = (float(lut["alpha"][dom].min()), float(lut["alpha"][dom].max())) if dom.any() else None
        bright = np.max(np.stack([lut[n] for n in RINGS]), axis=0) >= V_DARK
        a_dark = float(lut["alpha"][bright].max()) if bright.any() else 0.0
        if not bright.any() and r_all_dark is None:
            r_all_dark = rgh
        # 予測: 真の円弧上で、表が言う境界の傾きに対応する位置を E2 が固定の傾きで読むと
        pts = [(a_dark, TILT_MAX)]
        gr = (lut["G"] > lut["R"]) & (lut["G"] > lut["B"]) & (lut["G"] >= V_DARK)
        if red_rng is not None and gr.any():
            pts.append((float(lut["alpha"][gr].max()), 30.0))
        pts.append((THETA, THETA))
        if bright.any():
            xs_true = [fR["cx"] - fR["R"] * np.sin(np.deg2rad(a_t)) for a_t, _ in pts]
            s_ass = np.array([np.sin(np.deg2rad(a_a)) for _, a_a in pts])
            sol, *_ = np.linalg.lstsq(np.c_[np.ones_like(s_ass), -s_ass], np.asarray(xs_true), rcond=None)
            xc_p, R_p = sol
            hp = max(0.0, R_p * (np.cos(np.deg2rad(THETA)) - np.sqrt(max(0.0, 1 - min(1.0, xc_p / R_p) ** 2)))) if R_p > 0 else 0.0
        else:
            hp = 0.0
        hs, ins, rp = [], [], []
        for s in range(4):
            r = inspect_image(render(sc, roughness=rgh, seed=3000 + s))
            hs.append(r["R"]["h2"])
            ins.append(r["verdict"] != "good")
            rp.append(r["R"]["bands"][0])
        hm = float(np.mean(hs))
        e = 100 * (hm / fR["h"] - 1)
        errs.append(e)
        redpx.append(float(np.mean(rp)))
        pred_h.append(hp)
        if red_rng is None and r_red_gone_pred is None:
            r_red_gone_pred = rgh
        if np.mean(rp) < 0.5 and r_red_gone_meas is None:
            r_red_gone_meas = rgh
        if abs(e) > 12 and r_err_cliff is None:
            r_err_cliff = rgh
        print("   %.2f   %.2f/%.2f/%.2f   %-13s   %5.1f°        %.4f      %.4f    %+6.1f %%   %4.1f      %4.0f %%"
              % (rgh, peaks[0], peaks[1], peaks[2], "%.0f-%.0f°" % red_rng if red_rng else "無し",
                 a_dark, hp, hm, e, np.mean(rp), 100 * np.mean(ins)))
    print("\n  ★赤帯が消える粗さ: 表の予測 %s、実測 %s。" % (r_red_gone_pred, r_red_gone_meas))
    print("  ★E2 の誤差が 12 %% を超える粗さ %s。全リングの応答が暗部しきい値 %.1f を割って"
          "フィレット全体が暗部になる粗さ %s(利得は基準粗さで固定 = 露光一定)。"
          % (r_err_cliff, V_DARK, r_all_dark))
    print("     いちばん窓の狭い赤(傾き幅 10°)のピークが先に落ちる —— リングの分離より前に"
          "**明るさ**が崩れる。")
    figs.save_plot("roughness", [("実測 E2 誤差", list(roughs), errs),
                                 ("表からの予測", list(roughs), [100 * (p / fR["h"] - 1) for p in pred_h])],
                   xlabel="GGX 粗さ", ylabel="E2 の相対誤差 [%]", title="粗さで暗部の定義が動く",
                   caption="赤帯が消えるより前に、暗→色の境界が壁側へ寄って上に外れる。")
    lo, hi = lut_response(0.15), lut_response(0.5)
    figs.save_plot("ring_lut_rough", [("R 0.15", lo["alpha"], lo["R"]), ("G 0.15", lo["alpha"], lo["G"]),
                                      ("R 0.50", hi["alpha"], hi["R"]), ("G 0.50", hi["alpha"], hi["G"])],
                   xlabel="面の傾き α [deg]", ylabel="相対応答", title="粗さで窓の縁がなまる")
    return {"red_pred": r_red_gone_pred, "red_meas": r_red_gone_meas, "err_cliff": r_err_cliff,
            "all_dark": r_all_dark, "errs": errs}


# --------------------------------------------------------------------------- #
# 7. 照明むら —— 境界はどれだけ動くか                                             #
# --------------------------------------------------------------------------- #
def section_illumination(v_thr: float) -> dict:
    print("\n" + "=" * 78)
    print("7) 照明むら —— 赤リングだけ +u % 明るいと緑→赤の境界は何 px 動くか")
    print("=" * 78)
    v = 2.5 * v_thr
    sc = make_scene(volume=v)
    fR = sc["fillet"]["R"]
    us = (0.0, 0.05, 0.10, 0.20, 0.30)
    res = {}
    for rgh in (ROUGH_REF, 0.40):
        lut = lut_response(rgh)
        a = lut["alpha"]
        # 表の予測: g_R I_R = I_G の交点
        def cross(gain):
            dlt = gain * lut["R"] - lut["G"]
            idx = np.nonzero((dlt[:-1] < 0) & (dlt[1:] >= 0))[0]
            if idx.size == 0:
                return None
            i = idx[-1]
            return float(a[i] + (a[i + 1] - a[i]) * (-dlt[i]) / (dlt[i + 1] - dlt[i]))
        a0 = cross(1.0)
        base = None
        pred_l, meas_l = [], []
        print("  粗さ %.2f  (u = 0 の緑→赤境界 傾き %.1f°)" % (rgh, a0))
        print("     u       予測 Δx30 [px]   実測 Δx30 [px]   E2 h の変化")
        for u in us:
            au = cross(1.0 + u)
            dx_pred = (fR["R"] * (np.sin(np.deg2rad(a0)) - np.sin(np.deg2rad(au))) / PX_MM) if (au is not None and a0 is not None) else float("nan")
            x30s, hs = [], []
            for s in range(3):
                r = inspect_image(render(sc, roughness=rgh, gains=(1.0 + u, 1.0, 1.0), seed=4000 + s))
                x30s.append(r["R"]["x30"] if r["R"]["x30"] is not None else np.nan)
                hs.append(r["R"]["h2"])
            x30 = float(np.nanmean(x30s))
            if base is None:
                base = (x30, float(np.mean(hs)))
            dx_meas = (x30 - base[0]) / PX_MM
            pred_l.append(dx_pred)
            meas_l.append(dx_meas)
            print("    %4.0f %%       %+5.1f            %+5.1f          %+6.1f %%"
                  % (100 * u, dx_pred, dx_meas, 100 * (np.mean(hs) / base[1] - 1)))
        res[rgh] = {"pred": pred_l, "meas": meas_l}
    print("\n  ★鏡面(粗さ %.2f)では境界が階段なので u = %.0f %% でも %.1f px。粗さ 0.40 では"
          " %.1f px(予測 %.1f px)。" % (ROUGH_REF, 100 * us[-2], res[ROUGH_REF]["meas"][3],
                                        res[0.40]["meas"][3], res[0.40]["pred"][3]))
    figs.save_plot("illumination", [("実測 粗さ %.2f" % ROUGH_REF, [100 * u for u in us], res[ROUGH_REF]["meas"]),
                                    ("実測 粗さ 0.40", [100 * u for u in us], res[0.40]["meas"]),
                                    ("予測 粗さ 0.40", [100 * u for u in us], res[0.40]["pred"])],
                   xlabel="赤リングの利得誤差 u [%]", ylabel="緑→赤境界の移動 [px]",
                   title="照明むらは鏡面ほど効かない")
    return res


# --------------------------------------------------------------------------- #
# 8. 混同行列 —— 4 種 × ゼロ点                                                  #
# --------------------------------------------------------------------------- #
KINDS = ("good", "insufficient", "bridge", "tombstone")
KIND_JA = {"good": "良品", "insufficient": "不足", "bridge": "ブリッジ", "tombstone": "浮き"}


def _random_case(kind: str, rng: np.random.Generator, v_thr: float) -> dict:
    kw = {"shift": float(rng.uniform(-0.10, 0.10))}
    if kind == "good":
        kw["volume"] = float(v_thr * rng.uniform(1.4, 6.0))
    elif kind == "insufficient":
        kw["volume"] = float(v_thr * rng.uniform(0.15, 0.75))
    elif kind == "bridge":
        kw["volume"] = float(v_thr * rng.uniform(1.4, 6.0))
        kw["bridge_h"] = float(rng.uniform(0.06, 0.15))
    else:
        kw["volume"] = float(v_thr * rng.uniform(1.4, 6.0))
        kw["lift_deg"] = float(rng.uniform(8.0, 45.0))
    return kw


def section_confusion(v_thr: float, zp: ZeroPoint) -> dict:
    print("\n" + "=" * 78)
    print("8) 混同行列 —— 4 種 × 50 個体(ずれ ±0.1 mm、粗さ 0.10-0.35、照明むら ±5 %)")
    print("=" * 78)
    rng = np.random.default_rng(SEED + 2)
    cm = {k: {k2: 0 for k2 in KINDS} for k in KINDS}
    zp_ng = {k: 0 for k in KINDS}
    miss_lift = []
    n_each = 50
    for kind in KINDS:
        for i in range(n_each):
            kw = _random_case(kind, rng, v_thr)
            sc = make_scene(**kw)
            gains = tuple(1.0 + rng.uniform(-0.05, 0.05, 3))
            im = render(sc, roughness=float(rng.uniform(0.10, 0.35)), gains=gains,
                        seed=5000 + 100 * KINDS.index(kind) + i)
            r = inspect_image(im)
            truth = sc["kind"]
            cm[kind][r["verdict"]] = cm[kind].get(r["verdict"], 0) + 1
            if zp.verdict(im) == "ng":
                zp_ng[kind] += 1
            if kind == "tombstone" and r["verdict"] != "tombstone":
                miss_lift.append((kw["lift_deg"], r["verdict"]))
    header = ["真値 \\ 判定"] + [KIND_JA[k] for k in KINDS] + ["ゼロ点 NG"]
    rows = []
    print("   " + "  ".join("%-10s" % h for h in header))
    for k in KINDS:
        row = [KIND_JA[k]] + ["%d" % cm[k][k2] for k2 in KINDS] + ["%d %%" % (100 * zp_ng[k] // n_each)]
        rows.append(row)
        print("   " + "  ".join("%-10s" % c for c in row))
    acc = {k: 100.0 * cm[k][k] / n_each for k in KINDS}
    print("\n  ★E2 系の判定の正答: " + " / ".join("%s %.0f %%" % (KIND_JA[k], acc[k]) for k in KINDS))
    print("  ★ゼロ点(パッド平均色 ΔE)の NG 率: "
          + " / ".join("%s %.0f %%" % (KIND_JA[k], 100.0 * zp_ng[k] / n_each) for k in KINDS))
    print("     ブリッジはパッドの外で起きるのでパッド平均色には出ない —— ゼロ点は原理的に見えない。")
    if miss_lift:
        angs = [a for a, _ in miss_lift]
        print("  ★浮きの取りこぼし %d 件は持ち上がり角 %.1f°〜%.1f°(全て %.0f° 未満)、判定は %s。"
              % (len(miss_lift), min(angs), max(angs), 15.0,
                 "/".join(sorted(set(KIND_JA.get(v, v) for _, v in miss_lift)))))
        print("     電極上面の傾きが天頂リングの窓(0-15°)に収まっていて青のまま —— "
              "不足と原理的に区別できない。")
    figs.save_table("confusion", header, rows, title="混同行列(各 50 個体)+ ゼロ点の NG 率")
    return {"acc": acc, "zp_ng": {k: 100.0 * zp_ng[k] / n_each for k in KINDS},
            "miss_lift": miss_lift}


# --------------------------------------------------------------------------- #
# 9. 道具の穴                                                                   #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("9) 道具の穴(この PoC で fullseye を引いてみて)")
    print("=" * 78)
    # (a) 3 リング照明(仰角の窓 × 全方位)を BRDF で積分する口が無い
    assert hasattr(fs, "brdf_microfacet") and hasattr(fs, "illumination_design")
    assert not hasattr(fs, "ring_light_response") and not hasattr(fs.ledger, "ring_light_response")
    print("  (a) brdf_microfacet(点光源 1 本)と illumination_design(照明の**選び方**の表)は"
          "在るが、リング光源(仰角の窓 × 全方位)を積分して「傾き → 色」の表を作る口が無い。"
          "この PoC は z 軸対称を使って法線側を格子にし自前で積分した。")
    # (b) 色分類が HSV の 8bit 経由(trans_from_rgb)
    hsv = np.asarray(fs.apply(np.full((2, 2, 3), 0.5), "trans_from_rgb", a=0.0))
    assert hsv.shape == (2, 2, 3)
    print("  (b) trans_from_rgb は OpenCV の 8bit 経由で H が 0-179 を 255 で割った値になる"
          "(青 220° が 0.431)。色相の連続値が要る用途では自前の chromaticity のほうが素直。"
          "ここでは V だけ使い、色は access_channel の支配チャネルで分けた。")
    # (c) 列ごとの最頻値(mode)/ 走査線に沿った区間の解析が無い
    assert not hasattr(fs, "mode_filter_axis") and not hasattr(fs.ledger, "run_lengths")
    print("  (c) 「壁から外へ向かう 1 本の列に沿って、色の並びと境界の位置を読む」"
          "run-length 解析が無い(measure1d 族はエッジ位置は取れるが、多値ラベルの区間は"
          "取れない)。列方向の最頻値も自前。")
    # (d) 2-D の円弧当てはめ(点 → 円)は fit_circle が在る。tangent 拘束つきは無い
    assert hasattr(fs, "fit_circle")
    print("  (d) fit_circle は在る(使えた)。ただし「傾きが既知の点」で円を決める"
          "(sin α に対する線形回帰)形は無いので、E2 は lstsq を直接書いた。")
    # (e) 混同行列 / ROC は PoC 3 本目でも自前
    assert not hasattr(fs, "confusion_matrix")
    print("  (e) 混同行列・ROC は無い(poc_forensics_roc / poc_fabric_defect に続き 3 本目)。")


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.perf_counter()
    print("=" * 78)
    print("はんだフィレットの AOI —— 3 リング照明は傾きの 3 段量子化器")
    print("視野 %d x %d px(%.0f µm/px)/ 1608 チップ / 電極高さ %.2f mm / 接触角 %.0f°"
          % (NX, NY, 1e3 * PX_MM, H, THETA))
    print("=" * 78)

    lut_info = section_lut()
    sc_info = section_scene()
    v_thr, v_pin = sc_info["v_thr"], sc_info["v_pin"]

    # ゼロ点の校正(良品 30 / 不足 30、基準条件)
    rng = np.random.default_rng(SEED + 9)
    goods = [render(make_scene(volume=float(v_thr * rng.uniform(1.4, 6.0))), seed=6000 + i) for i in range(30)]
    bads = [render(make_scene(volume=float(v_thr * rng.uniform(0.15, 0.75))), seed=6100 + i) for i in range(30)]
    zp = ZeroPoint()
    zp_acc = zp.calibrate(goods, bads)
    print("\n  ゼロ点の校正: ΔE のしきい値 %.2f、校正集合(良品 30 / 不足 30)での精度 %.1f %%"
          % (zp.thr, 100 * zp_acc))

    vol = section_volume(v_thr, v_pin, lut_info["vis_frac"])
    bnd = section_boundary(zp)
    sh = section_shift(v_thr)
    rg = section_roughness(v_thr)
    il = section_illumination(v_thr)
    cf = section_confusion(v_thr, zp)
    section_tool_gaps()

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * 見えるのは高さの %.1f %%(予測 %.1f %%)。色を積分しても高さは出ない(E1 = %.3f 倍)。"
          % (100 * vol["ratio1"], 100 * lut_info["vis_frac"], vol["ratio1"]))
    print("  * 境界の位置から円弧を外挿する E2 は誤差 %+.1f %% ± %.1f %%(相関 %.4f)。"
          "爪先固定(V > %.4f mm³)で下に外れる(最大 %+.1f %%)。"
          % (vol["rel2_med"], vol["rel2_mad"], vol["c2"], v_pin, vol["relp"]))
    print("  * 合否の誤りは |h/H - 0.25| < %.3f の帯の中だけ(帯内 %.1f %% / 帯外 %.1f %%)。"
          % (bnd["band"], bnd["in"], bnd["out"]))
    print("  * 位置ずれ %.2f mm で良品が不足に化ける(予測 %.2f mm)。真値が不足になるのは %s mm。"
          % (sh["meas"] if sh["meas"] is not None else float("nan"), sh["pred"],
             "%.2f" % sh["truth"] if sh["truth"] is not None else "-"))
    print("  * 粗さ: 赤帯の消失は予測 %s / 実測 %s。E2 の +12 %% 超えはもっと早く %s。"
          % (rg["red_pred"], rg["red_meas"], rg["err_cliff"]))
    print("  * ゼロ点はブリッジを %.0f %% しか NG にできない。E2 系の浮き取りこぼしは全て小角。"
          % cf["zp_ng"]["bridge"])
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    # 所見を固定する(壊れたら鳴る)
    assert 0.20 < vol["ratio1"] < 0.36, vol["ratio1"]
    assert abs(vol["ratio1"] - lut_info["vis_frac"]) < 0.06, (vol["ratio1"], lut_info["vis_frac"])
    assert vol["c2"] > 0.99, vol["c2"]
    assert abs(vol["rel2_med"]) < 5.0, vol["rel2_med"]
    assert sh["pred"] is not None and sh["meas"] is not None and abs(sh["pred"] - sh["meas"]) <= 0.041, (sh["pred"], sh["meas"])
    assert sh["h_at"] > sh["h0"], (sh["h0"], sh["h_at"])
    assert rg["err_cliff"] is not None and rg["red_meas"] is not None and rg["err_cliff"] <= rg["red_meas"]
    assert cf["zp_ng"]["bridge"] < 20.0, cf["zp_ng"]
    assert cf["acc"]["bridge"] >= 90.0 and cf["acc"]["good"] >= 90.0, cf["acc"]
    assert all(a < 15.0 for a, _ in cf["miss_lift"]), cf["miss_lift"]

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
