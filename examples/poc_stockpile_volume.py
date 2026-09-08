# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""堆積物の在庫量を 3-D スキャンで出す —— 在庫は「誰も測っていない面」で決まる。

骨材ヤード・鉱山のズリ山・バイオマス燃料のチップ山・港湾の石炭ヤード。どれも
在庫は **1 個の体積の数字**で報告され、その数字で決済も生産計画も動きます。
スキャナは山の**表面**を測ります。ところが体積は表面と**底面**の差です。
底面は山の下に埋まっていて、**誰も測っていません**。この PoC は、山と地面を
別々の式で置いてから、(a) 底面の仮定と (b) 片側からのスキャンの遮蔽が、
在庫量の何 % を動かすかを分けて測ります。

EXTEND: 実スキャンに差し替えるなら :func:`surface_of` の戻り値(``(H, W)`` の
標高格子 [m])を、地上型 LiDAR / UAV 写真測量の点群から作った DSM に置き換え、
:func:`visible_from` の戻り値(1 = その格子点に測点がある)を、実際に点が
落ちた格子のマスクに置き換えます。走査位置は機器のログにあります。
**この PoC の中心である「真の底面と比べる」は、実データではできません** ——
山の下の地面の真値は、**山を退かした日に測量する**以外に手に入らないからです
(現場ではその一度きりの測量を「基準面」として何年も使い回します)。
実データでできるのは §3 の Δh 感度(底面を上下させて在庫がどれだけ動くかを
示す)と、§5 の走査位置を増やす掃引だけで、**絶対誤差は出せません**。
逆に言えば、業者が示す「精度 ±1 %」が底面込みの数字なのかどうかは、
その基準面がいつどう測られたかを聞かないと判定できません。

この PoC が示すこと(数字はすべて最終実行の実測値):

1. **底面を 5 cm 動かすと在庫が 1.269 % 動く**。閉形式 ΔV = A・Δh(A = 山の
   底面積)を測る前に印字して突き合わせました —— A = 906.48 m^2、Δh = 0.05 m
   の予測 -45.32 m^3 に対し実測 -45.32 m^3(7 通りで差は最大 0.0000 m^3)。
   かさ密度 1.6 t/m^3 なら **72.5 t**。
   ★予測と実測が合うのは当たり前(同じ領域 S で積分している)ですが、
   **重要なのは大きさのほう**です。底面積が 900 m^2 あるので、5 cm という
   「測量では誤差とも呼ばない量」がトラック 3 台分になります。
2. **傾いた地面は素朴な水平底面で勝手に打ち消える。うねりは打ち消えない**。
   全周スキャン(遮蔽ゼロ)+「外周の高さの平均を水平底面とみなす」現場の手で、
   **平らな地面なら誤差 +0.01 %**(= 格子の離散化のみ)、**傾き 1.8 % / -1.1 %
   とうねり ±0.22 m を入れると +1.79 %**。傾きは footprint が概ね対称なら
   外周平均と内部平均が同じ値になるので消えます。残る +1.79 % は**うねり**
   —— 外周は山の下のうねりを知らないからです。
3. ★**傾いた平面を外周に当てはめても直らない。むしろ悪くなる**(+1.79 % →
   +1.91 %)。当てはめる形(平面)が真の形(うねり)と違うので、自由度を
   増やしても偏りは減りません。
4. ★**遮蔽の広さは幾何で厳密に予測できる**。円錐は**線織面**なので、母線ごとに
   接平面の向きだけで可視/不可視が決まり、可視率 = arccos((H-h_s)/(D tanφ))/π。
   H=12 m・安息角 37 度・目線 2.0 m の山を D=60 m から見ると予測 0.5710、
   実測 0.5539(差 -0.0171)。★差は模型の誤りではなく**格子の離散化**で、
   セルを 1.2 → 0.6 → 0.4 m と細かくすると差は 0.0339 → 0.0171 → 0.0116 と
   **1 次で縮みます**。
5. **走査位置 1 → 2 → 3 で遮蔽は 66.0 % → 31.5 % → 1.4 %**。3 か所 120 度
   置きなら可視弧(半幅 72.8 度)が一周を覆う、という予測どおりです。
6. ★★**予測を 1 つ外しました**。遮蔽部を線形補間で埋めると体積は**過小**に
   出ると予測していました(円錐面は凹なので弦は下を通る)。実測は **+17.20 %
   の過大**。理由は、裏側は法尻まで丸ごと見えないので、三角形分割の相手が
   **山の上ではなく山の外の地面**になり、稜線から 30 m 先の地面へ張った弦は
   勾配 0.37 m/m —— 真の斜面 0.75 m/m の**上**を通るからです。
   「凹だから過小」は、両端が山の上にあるときの話でした。
7. ★★**素朴な水平底面が「良く見える」のは、間違いが 2 つ打ち消しているから**。
   同じ 1 か所スキャンで、真の地面を底面にすると +17.20 %、外周平均の水平
   底面だと **+0.51 %**。良くなったのではなく、**外周の高さも同じ補間で
   +0.728 m 持ち上がっている**からです。証拠に、外周のうち**実際に見えた点
   だけ**で水平底面を決めると **+12.05 %** に戻ります。**汚染された物差しで
   汚染された対象を測ると、誤差が消えたように見えます**。
8. **物差しを変えると勝者が入れ替わる**。体積では水平底面(+1.79 %)が平面
   当てはめ(+1.91 %)よりわずかに良く、**重心位置では平面当てはめ(0.07 m)
   が水平底面(0.42 m)の 6 分の 1**。積込計画に効くのは重心、決済に効くのは
   体積なので、**どちらか一方だけを見て「この手が良い」とは言えません**。
9. ★**外れ値に強い当てはめが、数字を悪くすることがある**。法尻に残土の土手
   (外周の 12 % を +0.45 m)を混ぜると、TLS 平面は +0.61 %、RANSAC 平面は
   +2.48 %。**RANSAC のほうが正しい仕事をしています** —— 土手を捨てて、
   土手が無いときの平面当てはめ(+1.91 %)へ戻っただけです。TLS が良く見えるのは
   **土手の持ち上げがうねりの偏りをたまたま打ち消した**ため。§7 と同じ形の罠です。
10. ★**道具の穴を 1 つ見つけました**。:func:`fullseye.ledger.dem_viewshed` は、
    **観測者の目線より高いセルを軒並み「見えない」と返します**。平地に置いた
    円錐の**頂点**が、開けた平地の観測者から見えないと出ます(実測 0.0)。
    原因は実装の刻み: 視線を ``ceil(hypot(H,W))`` 等分した最後の標本が
    ``np.rint`` で**目標セル自身**に丸まり、``(z-eye)/(d*t) > (z-eye)/d``
    (t<1、z>eye で必ず真)で自己遮蔽します。この PoC の遮蔽は
    :func:`visible_from`(目標の 1 セル手前で打ち切る自前の視線判定)で測り、
    §4 の閉形式で妥当性を確かめました。

【グラウンドトゥルース】山は**安息角 37 度の円錐 3 個の和**
(:data:`CONES`、高さ 12.0 / 5.5 / 3.5 m)で置きました。和にしたのは、
``max`` と違って**体積が解析的に閉じる**からです —— ∫Σmax(0, H-tanφ・r) dA
= Σ(π/3)R_k^2 H_k = **3572.6089 m^3**(セル 0.025 m の数値積分 3572.6089 と
一致)。重なった所は斜面が安息角より急になりますが、体積の真値は厳密です。
地面は別の式で置き(:func:`ground_of`、傾き 1.8 % / -1.1 % + 波長 47/38 m・
振幅 0.22 m のうねり)、**山の形とは独立**です。対照群は (a) うねりゼロの
平らな地面、(b) 全周から測った完全な点群。

【来歴】安息角 37 度は破砕骨材でよく使う値です(ISO 4324 は粉体の安息角の
測定法を定めますが、材料ごとの値は現場で測るもの)。かさ密度 1.6 t/m^3 も
砕石の代表値として置いた仮定で、出典のある定数ではありません。可視判定の
「線織面の母線は接平面の向きだけで可視/不可視が決まる」は円錐が線織面である
ことからの初等幾何で、文献は引きません。
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

#: セル寸法 [m] と格子の一辺。120 m 四方のヤードを 0.6 m で刻む。
CELL, N = 0.6, 201

#: 安息角 [度]。破砕骨材でよく使う値(材料ごとに現場で測るもの)。
REPOSE_DEG = 37.0
TANP = math.tan(math.radians(REPOSE_DEG))

#: 山 = 円錐 3 個の**和**。``(高さ H [m], 中心 x [m], 中心 y [m])``。
#: 和にすると ∫ が Σ(π/3)R^2 H に閉じる(``max`` だと重なりの積分が要る)。
CONES = ((12.0, 60.0, 60.0), (5.5, 74.0, 66.0), (3.5, 49.0, 50.0))

#: かさ密度 [t/m^3]。砕石の代表値として置いた仮定(出典のある定数ではない)。
BULK_DENSITY = 1.6

#: 走査位置を置く半径 [m](山の中心から)。
SCAN_RADIUS = 45.0

#: スキャナの目線高さ [m](三脚 + 機器)。
EYE_HEIGHT = 2.0

#: 法尻の帯の幅 [m]。ここの点で底面を決める(現場の「トゥライン」)。
TOE_BAND = 2.5


# --------------------------------------------------------------------------- #
# グラウンドトゥルース —— 山と地面を別々の式で置く                              #
# --------------------------------------------------------------------------- #
def pile_of(x, y):
    """山の高さ [m](地面からの厚み)。円錐 3 個の和。"""
    h = np.zeros(np.shape(x), np.float64)
    for peak, cx, cy in CONES:
        h += np.maximum(0.0, peak - TANP * np.hypot(x - cx, y - cy))
    return h


def ground_of(x, y, flat=False):
    """地面の標高 [m]。**山とは独立の式**。``flat=True`` が対照群。"""
    if flat:
        return np.full(np.shape(x), 1.0)
    return (1.0 + 0.018 * (x - 60.0) - 0.011 * (y - 60.0)
            + 0.22 * np.sin(2 * np.pi * (x - 60.0) / 47.0 + 1.1)
                   * np.cos(2 * np.pi * (y - 60.0) / 38.0 + 0.4))


def surface_of(x, y, flat=False):
    """スキャナが見る面 = 地面 + 山。"""
    return ground_of(x, y, flat) + pile_of(x, y)


def exact_volume():
    """真の体積 [m^3]。円錐の和なので項ごとに閉じる: Σ (π/3) R^2 H。"""
    return sum(math.pi / 3.0 * (peak / TANP) ** 2 * peak for peak, _, _ in CONES)


def exact_centroid():
    """真の重心の水平位置 [m]。各円錐は軸対称なので体積で重み付けた平均。"""
    vols = [math.pi / 3.0 * (peak / TANP) ** 2 * peak for peak, _, _ in CONES]
    tot = sum(vols)
    return (sum(v * c[1] for v, c in zip(vols, CONES)) / tot,
            sum(v * c[2] for v, c in zip(vols, CONES)) / tot)


def fine_volume(step):
    """細格子の数値積分 [m^3]。解析値の検算用。"""
    g = np.arange(30.0, 95.0, step)
    gx, gy = np.meshgrid(g, g)
    return float((pile_of(gx, gy) * step * step).sum())


def fine_area(step):
    """底面積(山の厚みが正の領域)[m^2] を細格子で。"""
    g = np.arange(30.0, 95.0, step)
    gx, gy = np.meshgrid(g, g)
    return float((pile_of(gx, gy) > 0).sum() * step * step)


# --------------------------------------------------------------------------- #
# 視線判定 —— なぜ dem_viewshed を直接使わないか                                #
# --------------------------------------------------------------------------- #
def visible_from(surf, cell, obs_rc, eye_h, step=1.0, margin=1.0):
    """観測点 ``obs_rc`` から各セルが見えるか(1/0)。``dem_viewshed`` の代役。

    ``fullseye.ledger.dem_viewshed`` は視線を格子全体の対角長で等分し、途中の
    標本を ``np.rint`` で最近傍セルに丸めます。**最後の標本が目標セル自身に
    丸まる**幾何がふつうに起き、そのとき ``(z-eye)/(d*t) > (z-eye)/d``
    (t<1)は ``z>eye`` なら必ず真になるので、**目線より高いセルが軒並み
    自己遮蔽**します。§9 でその症状を数字で示します。

    ここでは同じ考え方のまま (1) 距離を**セル単位で等間隔**に刻み、
    (2) 目標の ``margin`` セル手前で打ち切り、(3) 双一次で標本します。
    ``margin`` を残す分だけ遮蔽をわずかに少なく見積もりますが、§4 の
    閉形式と格子収束で偏りの大きさを押さえてあります。
    """
    h, w = surf.shape
    r0, c0 = obs_rc
    eye = float(surf[r0, c0]) + float(eye_h)
    rr, cc = np.mgrid[0:h, 0:w].astype(np.float64)
    dy, dx = rr - r0, cc - c0
    dcell = np.hypot(dy, dx)
    safe = np.where(dcell > 0, dcell, 1.0)
    uy, ux = dy / safe, dx / safe
    need = (surf - eye) / (safe * cell)              # 目標の仰角
    blocked = np.zeros(surf.shape, bool)
    n_steps = int(math.ceil((float(dcell.max()) - margin) / step))
    for k in range(1, n_steps + 1):
        s = k * step                                  # 観測点からの距離 [セル]
        act = dcell > s + margin                      # まだ目標の手前か
        if not act.any():
            break
        py, px = r0 + uy * s, c0 + ux * s
        iy = np.clip(np.floor(py), 0, h - 2).astype(np.int64)
        ix = np.clip(np.floor(px), 0, w - 2).astype(np.int64)
        fy = np.clip(py - iy, 0.0, 1.0)
        fx = np.clip(px - ix, 0.0, 1.0)
        z = ((1 - fy) * (1 - fx) * surf[iy, ix] + (1 - fy) * fx * surf[iy, ix + 1]
             + fy * (1 - fx) * surf[iy + 1, ix] + fy * fx * surf[iy + 1, ix + 1])
        blocked |= act & ((z - eye) / (s * cell) > need)
    vis = ~blocked
    vis[r0, c0] = True
    return vis


def occluded_fraction_closed_form(peak, eye_h, dist):
    """円錐 1 個の底面のうち**見えない**割合(閉形式)。

    円錐は線織面で、母線 θ に沿った接平面の法線は ``(tanφ cosθ, tanφ sinθ, 1)``。
    観測点 S がその平面の外側にあるときだけ母線が見えるので、可視条件は
    ``cos(θ-θ_S) > (H-h_s)/(D tanφ)``。可視弧の半幅 α = arccos(c*) より
    **可視率 = α/π**。``c* >= 1``(観測者が円錐面より下)は定義できない。
    """
    c_star = (peak - eye_h) / (dist * TANP)
    if c_star >= 1.0:
        return float("nan")
    return 1.0 - math.acos(c_star) / math.pi


# --------------------------------------------------------------------------- #
# 測る側 —— 底面の仮定と、遮蔽を埋める補間                                      #
# --------------------------------------------------------------------------- #
class Yard:
    """1 つのヤード(格子・真値・法尻の帯)をまとめて持つ。"""

    def __init__(self, flat=False):
        self.flat = flat
        xs = np.arange(N) * CELL
        self.x, self.y = np.meshgrid(xs, xs)
        self.ground = ground_of(self.x, self.y, flat)
        self.pile = pile_of(self.x, self.y)
        self.surf = self.ground + self.pile
        self.foot = self.pile > 0                     # 底面(トゥラインの内側)
        # 底面の外側までの距離 = 各円錐の (r - R) の最小値(解析的に出る)
        d_out = np.min(np.stack([np.hypot(self.x - cx, self.y - cy) - peak / TANP
                                 for peak, cx, cy in CONES]), axis=0)
        self.toe = (d_out > 0) & (d_out <= TOE_BAND)
        self.area = float(self.foot.sum()) * CELL * CELL

    def scan(self, n_pos):
        """走査位置 ``n_pos`` か所(等間隔)。0 = 全周から測った完全な点群。"""
        if n_pos == 0:
            return np.ones(self.surf.shape, bool), []
        pos = [(60.0 + SCAN_RADIUS * math.cos(math.radians(a)),
                60.0 + SCAN_RADIUS * math.sin(math.radians(a)))
               for a in np.linspace(0.0, 360.0, n_pos, endpoint=False)]
        vis = np.zeros(self.surf.shape, bool)
        for px, py in pos:
            vis |= visible_from(self.surf, CELL,
                                (int(round(py / CELL)), int(round(px / CELL))),
                                EYE_HEIGHT)
        return vis, pos

    def fill(self, vis):
        """見えなかった所を線形補間で埋めた DSM。``fullseye.interp_scattered``。"""
        if vis.all():
            return self.surf.copy(), 0.0
        samples = np.column_stack([self.x[vis], self.y[vis]])
        query = np.column_stack([self.x.ravel(), self.y.ravel()])
        got = fs.interp_scattered(samples, self.surf[vis], query, method="linear",
                                  fill_value=np.nan)
        return (np.asarray(got["value"]).reshape(self.surf.shape),
                float(got["outside_fraction"]))

    # -- 底面の決め方 3 通り -------------------------------------------------
    def base_level(self, dsm, mask=None):
        """外周の高さの平均を水平な底面とみなす(現場で実際に使われる手)。"""
        m = self.toe if mask is None else (self.toe & mask)
        return np.full(dsm.shape, float(dsm[m].mean()))

    def base_plane(self, dsm, robust=False, contaminate=None):
        """外周に平面を当てはめる。``robust`` で RANSAC(外れ値に強い当てはめ)。"""
        z = dsm if contaminate is None else contaminate
        pts = np.column_stack([self.x[self.toe], self.y[self.toe], z[self.toe]])
        if robust:
            plane, inliers = fs.fit_plane_ransac(pts, thresh=0.12, iters=400, seed=3)
            plane = np.asarray(plane, np.float64)
        else:
            plane, inliers = np.asarray(fs.fit_plane(pts), np.float64), None
        zb = -(plane[0] * self.x + plane[1] * self.y + plane[3]) / plane[2]
        return zb, plane, pts, inliers

    # -- 物差し ---------------------------------------------------------------
    def measure(self, dsm, base):
        """在庫量 [m^3]・重心の水平位置 [m]・最高点の高さ [m]。"""
        d = dsm - base
        vol = float(d[self.foot].sum()) * CELL * CELL
        w = np.clip(d[self.foot], 0.0, None)
        pts = np.column_stack([self.x[self.foot], self.y[self.foot],
                               np.zeros(int(self.foot.sum()))])
        cen = np.asarray(fs.ledger.moment_axes(pts, w)[0], np.float64)
        return {"vol": vol, "cx": float(cen[0]), "cy": float(cen[1]),
                "peak": float(np.nanmax(d[self.foot]))}


def _pct(v, truth):
    return 100.0 * (v - truth) / truth


# --------------------------------------------------------------------------- #
def section_truth():
    print("=== 1. グラウンドトゥルース —— 山と地面を別々の式で置く ===")
    v_exact = exact_volume()
    yard = Yard()
    v_grid = float(yard.pile.sum()) * CELL * CELL
    print(f"  解析(Σ(π/3)R^2 H)      {v_exact:12.4f} m^3")
    for step in (0.10, 0.05, 0.025):
        print(f"  数値積分(セル {step:5.3f} m)  {fine_volume(step):12.4f} m^3")
    print(f"  作業格子(セル {CELL} m)     {v_grid:12.4f} m^3"
          f"  ({_pct(v_grid, v_exact):+.4f} %)")
    area_fine = fine_area(0.025)
    print(f"  底面積 A = {area_fine:.2f} m^2(細格子)/ {yard.area:.2f} m^2(作業格子)")
    tcx, tcy = exact_centroid()
    print(f"  真の重心 ({tcx:.3f}, {tcy:.3f}) m —— 円錐の体積で重み付けた平均")
    r_main = np.hypot(yard.x - 60.0, yard.y - 60.0)
    az = np.degrees(np.arctan2(yard.y - 60.0, yard.x - 60.0))
    # 主円錐だけの法面を取る。副円錐は方位 23 度と -138 度にあるので、
    # 95〜145 度の扇形はどちらからも 18 m 以上離れていて混ざらない。
    flank = (r_main > 4.0) & (r_main < 12.0) & (az > 95.0) & (az < 145.0)
    flat_yard = Yard(flat=True)
    s_flat = float(fs.ledger.dem_slope(flat_yard.surf, CELL)[flank].mean())
    s_real = float(fs.ledger.dem_slope(yard.surf, CELL)[flank].mean())
    print(f"  主円錐の法面の傾斜 {s_flat:.3f} 度(仕込んだ安息角 {REPOSE_DEG} 度、"
          f"平らな地面の上で dem_slope 確認)")
    print(f"  同じ法面を傾いた地面の上で測ると {s_real:.3f} 度 —— **地面の勾配が"
          f"安息角に足し算される**。安息角を現場で読むときの罠。")
    print("  → 円錐の**和**にしたので体積が解析的に閉じる。重なった所は斜面が")
    print("     安息角より急になるが、体積の真値は厳密。")
    return {"exact": v_exact, "grid": v_grid, "fine": fine_volume(0.025),
            "area": area_fine, "cx": tcx, "cy": tcy,
            "flank": s_flat, "flank_tilted": s_real}


def section_base_offset(truth):
    print("\n=== 2. 崖(a) 底面の仮定 —— 閉形式を先に印字してから測る ===")
    yard = Yard()
    v_grid = truth["grid"]
    print(f"  予測: 底面を Δh だけ動かすと ΔV = -A・Δh、A = {yard.area:.2f} m^2。")
    print(f"       Δh = 0.05 m なら {-yard.area * 0.05:+.2f} m^3 = "
          f"{-100 * yard.area * 0.05 / truth['exact']:+.3f} %")
    print(f"  {'Δh [m]':>8}{'予測 ΔV':>12}{'実測 ΔV':>12}{'在庫比':>10}"
          f"{'かさ 1.6 t/m^3':>16}")
    rows, worst = [], 0.0
    for dh in (-0.20, -0.10, -0.05, 0.0, 0.05, 0.10, 0.20):
        got = yard.measure(yard.surf, yard.ground + dh)
        pred, meas = -yard.area * dh, got["vol"] - v_grid
        worst = max(worst, abs(pred - meas))
        rows.append((f"{dh:+.2f}", f"{pred:+.2f}", f"{meas:+.2f}",
                     f"{100 * meas / truth['exact']:+.3f} %",
                     f"{meas * BULK_DENSITY:+.1f} t"))
        print(f"  {dh:>8.2f}{pred:>12.2f}{meas:>12.2f}"
              f"{100 * meas / truth['exact']:>9.3f}%{meas * BULK_DENSITY:>15.1f} t")
    print(f"  → 予測と実測の差は最大 {worst:.4f} m^3。**驚きは一致ではなく大きさ**:")
    print("     測量では誤差とも呼ばない 5 cm が、トラック 3 台分になる。")
    figs.save_table("base_offset", ["Δh [m]", "予測 ΔV [m^3]", "実測 ΔV [m^3]",
                                    "在庫比", "重量"], rows,
                    title="底面を Δh 動かすと在庫は A・Δh 動く",
                    caption=f"A = {yard.area:.1f} m^2。閉形式は測る前に印字してある。")
    if figs.enabled():
        dhs = np.linspace(-0.25, 0.25, 21)
        meas = np.array([yard.measure(yard.surf, yard.ground + d)["vol"] - v_grid
                         for d in dhs])
        figs.save_plot("base_offset_line",
                       [("閉形式 -A・Δh", dhs, -yard.area * dhs),
                        ("実測", dhs, meas)],
                       xlabel="底面の仮定のずれ Δh [m]", ylabel="在庫量の変化 [m^3]",
                       title="底面の仮定が在庫量を決める",
                       caption="2 本は重なる。傾き = 底面積。"
                               "底面積が大きいほど、同じ 1 cm が重い。")
    return {"area": yard.area, "worst": worst}


def section_null_baseline(truth):
    print("\n=== 3. ゼロ点 —— 外周平均の水平底面(全周スキャン = 遮蔽ゼロ)===")
    print(f"  {'地面':>14}{'水平底面':>14}{'平面当てはめ':>16}"
          f"{'重心誤差(水平)':>18}{'重心誤差(平面)':>18}")
    out = {}
    for label, flat in (("平ら(対照群)", True), ("傾き+うねり", False)):
        yard = Yard(flat)
        lv = yard.measure(yard.surf, yard.base_level(yard.surf))
        pl = yard.measure(yard.surf, yard.base_plane(yard.surf)[0])
        cl = math.hypot(lv["cx"] - truth["cx"], lv["cy"] - truth["cy"])
        cp = math.hypot(pl["cx"] - truth["cx"], pl["cy"] - truth["cy"])
        print(f"  {label:>14}{_pct(lv['vol'], truth['exact']):>13.2f}%"
              f"{_pct(pl['vol'], truth['exact']):>15.2f}%"
              f"{cl:>16.2f} m{cp:>16.2f} m")
        out[label] = {"level": lv, "plane": pl, "cl": cl, "cp": cp}
    print("  → 平らな地面なら +0.01 %(格子の離散化だけ)。**対照群が効いている**。")
    print("     傾きは footprint が概ね対称なら外周平均と内部平均が一致して消え、")
    print("     残るのは**うねり** —— 外周は山の下のうねりを知らない。")
    print("  → ★平面を当てはめると**悪くなる**(+1.79 % → +1.91 %)。当てはめる形が")
    print("     真の形(うねり)と違うので、自由度を増やしても偏りは減らない。")
    print("  → ★物差しを変えると勝者が入れ替わる: 体積は水平底面がわずかに良く、")
    print("     **重心は平面当てはめが 6 分の 1**。積込計画に効くのは重心のほう。")
    return out


def section_occlusion_closed_form():
    print("\n=== 4. 崖(b) 遮蔽 —— 幾何で予測してから測る ===")
    print("  円錐は線織面。母線 θ の接平面法線 (tanφcosθ, tanφsinθ, 1) の外側に")
    print("  観測点があるときだけ見えるので、可視率 = arccos((H-h_s)/(D tanφ))/π。")
    print(f"  {'D [m]':>8}{'目線 [m]':>10}{'予測 遮蔽率':>14}{'実測':>10}{'差':>10}")
    peak = CONES[0][0]
    rows, worst = [], 0.0
    for dist, eye in ((60.0, 2.0), (45.0, 2.0), (30.0, 2.0), (20.0, 2.0),
                      (45.0, 4.0), (30.0, 5.0)):
        xs = np.arange(N) * CELL
        gx, gy = np.meshgrid(xs, xs)
        r = np.hypot(gx - 60.0, gy - 60.0)
        surf = np.maximum(0.0, peak - TANP * r) + 1.0          # 単一円錐・平地
        foot = r < peak / TANP
        row = int(round((60.0 + dist) / CELL))
        vis = visible_from(surf, CELL, (row, int(round(60.0 / CELL))), eye)
        meas = 1.0 - float(vis[foot].mean())
        pred = occluded_fraction_closed_form(peak, eye, dist)
        worst = max(worst, abs(meas - pred))
        rows.append((f"{dist:.0f}", f"{eye:.1f}", f"{pred:.4f}", f"{meas:.4f}",
                     f"{meas - pred:+.4f}"))
        print(f"  {dist:>8.0f}{eye:>10.1f}{pred:>14.4f}{meas:>10.4f}{meas - pred:>10.4f}")
    print(f"  → 予測と実測の差は最大 {worst:.4f}。符号は一貫して負 = 遮蔽をやや")
    print("     少なく見積もっている。**模型の誤りか、格子の離散化か**を分ける:")
    conv = []
    for cell in (1.2, 0.6, 0.4):
        n = int(round(120.0 / cell)) + 1
        xs = np.arange(n) * cell
        gx, gy = np.meshgrid(xs, xs)
        r = np.hypot(gx - 60.0, gy - 60.0)
        surf = np.maximum(0.0, peak - TANP * r) + 1.0
        foot = r < peak / TANP
        vis = visible_from(surf, cell, (int(round(120.0 / cell)),
                                        int(round(60.0 / cell))), 2.0)
        meas = 1.0 - float(vis[foot].mean())
        pred = occluded_fraction_closed_form(peak, 2.0, 60.0)
        conv.append((cell, abs(meas - pred)))
        print(f"     セル {cell:4.2f} m ({n}x{n}): 実測 {meas:.4f}  差 {meas - pred:+.4f}")
    print("  → セルを半分にすると差も約半分 = **1 次収束** = 離散化。境界は母線 1 本")
    print("     (直線)なので、そこに並ぶセルの幅がそのまま面積の誤差になる。")
    figs.save_table("occlusion_closed_form",
                    ["距離 D [m]", "目線 [m]", "予測 遮蔽率", "実測", "差"], rows,
                    title="遮蔽の広さは測る前に幾何で出る",
                    caption="可視率 = arccos((H-h_s)/(D tanφ))/π。"
                            "単一円錐・平らな地面の対照群。")
    return {"worst": worst, "conv": conv}


def section_scan_sweep(truth):
    print("\n=== 5. 走査位置を 1 → 2 → 3 → 4 と増やす ===")
    print(f"  {'地面':>12}{'走査':>6}{'遮蔽率':>10}{'hull 外':>10}"
          f"{'真の底面':>12}{'水平底面':>12}{'重心誤差':>12}")
    out = {}
    for label, flat in (("平ら", True), ("うねり", False)):
        yard = Yard(flat)
        for n_pos in (0, 1, 2, 3, 4):
            vis, _ = yard.scan(n_pos)
            dsm, outside = yard.fill(vis)
            occ = 1.0 - float(vis[yard.foot].mean())
            gt = yard.measure(dsm, yard.ground)
            lv = yard.measure(dsm, yard.base_level(dsm))
            cerr = math.hypot(lv["cx"] - truth["cx"], lv["cy"] - truth["cy"])
            print(f"  {label:>12}{n_pos:>6}{occ:>10.3f}{outside:>10.3f}"
                  f"{_pct(gt['vol'], truth['exact']):>11.2f}%"
                  f"{_pct(lv['vol'], truth['exact']):>11.2f}%{cerr:>10.2f} m")
            out[(label, n_pos)] = {"occ": occ, "gt": gt, "lv": lv, "cerr": cerr,
                                   "outside": outside}
    alpha = math.degrees(math.acos((CONES[0][0] - EYE_HEIGHT)
                                   / (SCAN_RADIUS * TANP)))
    print(f"  → 予測: D={SCAN_RADIUS:.0f} m の可視弧は半幅 {alpha:.1f} 度なので、")
    print(f"     1 か所で {1 - alpha / 180:.3f}、2 か所(180 度)で "
          f"{max(0.0, 1 - 2 * alpha / 180):.3f}、3 か所(120 度)で 0。")
    print("     実測 0.660 / 0.315 / 0.014 —— 3 か所で塞がるのは予測どおり。")
    print("  → ★1 か所・真の底面で **+17.20 %**。補間は**過大**に出た。")
    print("     予測を外した: 円錐面は凹なので弦は下を通る = 過小、と思っていた。")
    print("     実際は裏側が法尻まで丸ごと見えないので、三角形の相手が山の上ではなく")
    print("     **山の外の地面**になり、稜線から 30 m 先へ張った弦は勾配 0.37 m/m。")
    print("     真の斜面 0.75 m/m の**上**を通る。「凹だから過小」は両端が山の上の話。")
    if figs.enabled():
        xs = np.array([1, 2, 3, 4], float)
        figs.save_plot(
            "scan_sweep",
            [("うねり・真の底面", xs, np.array([abs(_pct(out[("うねり", k)]["gt"]["vol"],
                                                         truth["exact"])) for k in (1, 2, 3, 4)])),
             ("平ら・真の底面", xs, np.array([abs(_pct(out[("平ら", k)]["gt"]["vol"],
                                                       truth["exact"])) for k in (1, 2, 3, 4)])),
             ("うねり・水平底面", xs, np.array([abs(_pct(out[("うねり", k)]["lv"]["vol"],
                                                         truth["exact"])) for k in (1, 2, 3, 4)]))],
            xlabel="走査位置の数", ylabel="在庫量の誤差の絶対値 [%]",
            title="走査位置を増やすと遮蔽の誤差は落ちる —— 底面の誤差は残る",
            caption="3 か所で遮蔽は 1.4 % まで落ちるが、うねり由来の +1.8 % は"
                    "何か所測っても消えない(底面は誰も測っていない)。")
    return out


def section_cancellation(truth):
    print("\n=== 6. なぜ素朴な水平底面が「良く見える」のか(1 か所スキャン)===")
    yard = Yard()
    vis, _ = yard.scan(1)
    dsm, _ = yard.fill(vis)
    ring_true = float(yard.surf[yard.toe].mean())
    ring_fill = float(dsm[yard.toe].mean())
    seen = yard.toe & vis
    print(f"  外周の高さ: 真 {ring_true:.3f} m / 補間後 {ring_fill:.3f} m"
          f"(**{ring_fill - ring_true:+.3f} m 持ち上がった**)")
    print(f"  外周で実際に見えた点 {int(seen.sum())} / {int(yard.toe.sum())}")
    print(f"  {'底面の決め方':>26}{'在庫量':>12}{'誤差':>10}{'重心誤差':>12}{'最高点':>10}")
    out = {}
    for name, base in (("真の地面(反実仮想)", yard.ground),
                       ("外周平均(見えた点だけ)", yard.base_level(dsm, vis)),
                       ("外周平均(補間込み・現場の手)", yard.base_level(dsm))):
        got = yard.measure(dsm, base)
        cerr = math.hypot(got["cx"] - truth["cx"], got["cy"] - truth["cy"])
        print(f"  {name:>26}{got['vol']:>12.1f}"
              f"{_pct(got['vol'], truth['exact']):>9.2f}%{cerr:>10.2f} m"
              f"{got['peak']:>10.2f}")
        out[name] = {"got": got, "cerr": cerr}
    print("  → **良くなったのではない**。山を持ち上げた補間が外周も同じだけ持ち上げ、")
    print("     引き算で消えているだけ。見えた点だけで底面を決めると +12.05 % に戻る。")
    print("     ★汚染された物差しで汚染された対象を測ると、誤差は消えたように見える。")
    out["ring"] = {"true": ring_true, "fill": ring_fill, "seen": int(seen.sum()),
                   "total": int(yard.toe.sum())}
    if figs.enabled():
        shade = np.asarray(fs.ledger.dem_hillshade(yard.surf, CELL, azimuth_deg=135.0,
                                                   altitude_deg=45.0))
        lift = dsm - yard.surf
        figs.save_grid("scene",
                       [shade, vis.astype(float), lift,
                        np.where(yard.foot, dsm - yard.ground, 0.0)],
                       ["表面(陰影・南東の光)", "見えた所(明)/ 遮蔽(暗)",
                        "補間のずれ [m](0 が暗)", "測った厚み [m]"],
                       ncols=2, signed=[False, False, True, False],
                       title="1 か所スキャン —— 見えない裏側は測定でなく補間",
                       caption=f"補間のずれは {lift.min():+.2f} 〜 {lift.max():+.2f} m"
                               f"(0 の所が暗い = 触っていない)。外周の高さも"
                               f" {ring_fill - ring_true:+.3f} m 持ち上がる —— "
                               "山も底も同じ向きにずれるので、引き算で見えなくなる。")
    return out


def section_toe_contamination(truth):
    print("\n=== 7. 法尻に残土の土手が混じると(全周スキャン)===")
    yard = Yard()
    rng = np.random.default_rng(7)
    dirty = yard.surf.copy()
    berm = yard.toe & (rng.random(yard.toe.shape) < 0.12)
    dirty[berm] += 0.45
    clean_plane = yard.measure(yard.surf, yard.base_plane(yard.surf)[0])
    print(f"  土手なしの平面当てはめ: {clean_plane['vol']:.1f} m^3 "
          f"({_pct(clean_plane['vol'], truth['exact']):+.2f} %)  ← 比較の基準")
    print(f"  土手: 外周 {int(yard.toe.sum())} 点のうち {int(berm.sum())} 点を +0.45 m")
    print(f"  {'当てはめ':>10}{'在庫量':>12}{'誤差':>10}{'基準との差':>14}"
          f"{'底面の偏り':>14}")
    out = {"clean": clean_plane}
    for name, robust in (("TLS", False), ("RANSAC", True)):
        zb, plane, pts, inliers = yard.base_plane(yard.surf, robust=robust,
                                                  contaminate=dirty)
        got = yard.measure(yard.surf, zb)
        bias = float((zb - yard.ground)[yard.foot].mean())
        print(f"  {name:>10}{got['vol']:>12.1f}"
              f"{_pct(got['vol'], truth['exact']):>9.2f}%"
              f"{got['vol'] - clean_plane['vol']:>13.1f} m^3{bias:>13.3f} m")
        out[name] = {"got": got, "bias": bias,
                     "inliers": None if inliers is None else int(np.sum(inliers)),
                     "plane": plane, "pts": pts}
    res = np.asarray(fs.height_above_plane(out["RANSAC"]["pts"], out["RANSAC"]["plane"]))
    print(f"  RANSAC の内点 {out['RANSAC']['inliers']} / {int(yard.toe.sum())}、"
          f"外周の残差 rms {float(np.sqrt(np.mean(res ** 2))):.3f} m / "
          f"最大 {float(np.max(np.abs(res))):.3f} m")
    print("  → ★**外れ値に強いほうが数字は悪い**。RANSAC は土手を正しく捨てて、")
    print("     土手が無いときの答え(+1.91 %)へ戻っただけ。TLS が良く見えるのは")
    print("     **土手の持ち上げがうねりの偏りをたまたま打ち消した**から —— §6 と同じ罠。")
    out["res_rms"] = float(np.sqrt(np.mean(res ** 2)))
    return out


def section_op_hole():
    print("\n=== 8. 道具の穴 —— dem_viewshed は目線より高いセルを見えないと言う ===")
    peak = CONES[0][0]
    xs = np.arange(N) * CELL
    gx, gy = np.meshgrid(xs, xs)
    r = np.hypot(gx - 60.0, gy - 60.0)
    surf = np.maximum(0.0, peak - TANP * r) + 1.0
    foot = r < peak / TANP
    obs = (int(round(120.0 / CELL)), int(round(60.0 / CELL)))
    op_vis = np.asarray(fs.ledger.dem_viewshed(surf, CELL, obs, observer_height_m=2.0))
    own = visible_from(surf, CELL, obs, 2.0)
    apex = (int(round(60.0 / CELL)), int(round(60.0 / CELL)))
    pred = occluded_fraction_closed_form(peak, 2.0, 60.0)
    print(f"  平地に置いた円錐 1 個、観測者は 60 m 先の開けた平地(目線 2.0 m)。")
    print(f"  **円錐の頂点**の可視: dem_viewshed {op_vis[apex]:.1f} / "
          f"自前 {float(own[apex]):.1f} / 幾何 1.0(凸な立体の最高点は外から必ず見える)")
    print(f"  底面の遮蔽率: dem_viewshed {1 - op_vis[foot].mean():.4f} / "
          f"自前 {1 - own[foot].mean():.4f} / 閉形式 {pred:.4f}")
    above = surf > (surf[obs] + 2.0)
    print(f"  目線(標高 {surf[obs] + 2.0:.1f} m)より高いセル {int(above.sum())} 個のうち、"
          f"dem_viewshed が可視と言うのは {int(op_vis[above].sum())} 個")
    print("  → 原因: 視線を ceil(hypot(H,W)) 等分した最後の標本が np.rint で")
    print("     **目標セル自身**に丸まり、(z-eye)/(d*t) > (z-eye)/d(t<1)が")
    print("     z>eye なら必ず真になる。目標は「途中の地形」ではないので、")
    print("     打ち切りを 1 セル手前にすれば直る(この PoC は他ファイルを触らない)。")
    return {"apex_op": float(op_vis[apex]), "apex_own": float(own[apex]),
            "occ_op": float(1 - op_vis[foot].mean()),
            "occ_own": float(1 - own[foot].mean()), "pred": pred,
            "above": int(above.sum()), "above_vis": int(op_vis[above].sum())}


def main():
    t0 = time.perf_counter()
    truth = section_truth()
    off = section_base_offset(truth)
    null = section_null_baseline(truth)
    occ = section_occlusion_closed_form()
    sweep = section_scan_sweep(truth)
    canc = section_cancellation(truth)
    toe = section_toe_contamination(truth)
    hole = section_op_hole()

    print("\n=== 9. まとめ —— 何がどれだけ効いたか ===")
    rows = [
        ("底面の仮定だけ(全周・平ら)", f"{_pct(null['平ら(対照群)']['level']['vol'], truth['exact']):+.2f} %"),
        ("底面の仮定だけ(全周・うねり)", f"{_pct(null['傾き+うねり']['level']['vol'], truth['exact']):+.2f} %"),
        ("遮蔽だけ(1 か所・平ら・真の底面)", f"{_pct(sweep[('平ら', 1)]['gt']['vol'], truth['exact']):+.2f} %"),
        ("遮蔽だけ(3 か所・平ら・真の底面)", f"{_pct(sweep[('平ら', 3)]['gt']['vol'], truth['exact']):+.2f} %"),
        ("両方(1 か所・うねり・水平底面)", f"{_pct(sweep[('うねり', 1)]['lv']['vol'], truth['exact']):+.2f} %"),
        ("両方(3 か所・うねり・水平底面)", f"{_pct(sweep[('うねり', 3)]['lv']['vol'], truth['exact']):+.2f} %"),
    ]
    for name, val in rows:
        print(f"  {name:<34}{val:>10}")
    add = (_pct(null['傾き+うねり']['level']['vol'], truth['exact'])
           + _pct(sweep[('平ら', 1)]['lv']['vol'], truth['exact']))
    print(f"  → 2 つを足すと {add:+.2f} %、実際に両方入れると "
          f"{_pct(sweep[('うねり', 1)]['lv']['vol'], truth['exact']):+.2f} %。"
          f"**足し算にならない**")
    print("     —— 遮蔽の補間が外周(= 底面の決め手)まで動かすので、2 つは絡む。")
    figs.save_table("summary", ["条件", "在庫量の誤差"], rows,
                    title="底面の仮定と遮蔽 —— どちらがどれだけ効くか",
                    caption="対照群(平ら/全周)で 2 つを切り分けてから、両方入れる。")

    # ---- 自己検査(所見を固定する。穴が塞がったら鳴る)-----------------------
    assert abs(truth["exact"] - truth["fine"]) < 1e-3, (truth["exact"], truth["fine"])
    assert abs(_pct(truth["grid"], truth["exact"])) < 0.02
    assert abs(truth["flank"] - REPOSE_DEG) < 0.1, truth["flank"]
    # (a) 底面の閉形式 ΔV = A・Δh
    assert off["worst"] < 0.05, off["worst"]
    # 対照群: 平ら + 全周なら、素朴な水平底面でも離散化しか残らない
    assert abs(_pct(null["平ら(対照群)"]["level"]["vol"], truth["exact"])) < 0.05
    # うねりを入れると 1 % 台の偏りが立つ(平らでは立たない)
    assert _pct(null["傾き+うねり"]["level"]["vol"], truth["exact"]) > 1.0
    # ★物差しで勝者が入れ替わる: 体積は水平底面、重心は平面当てはめ
    nb = null["傾き+うねり"]
    assert abs(_pct(nb["level"]["vol"], truth["exact"])) \
        < abs(_pct(nb["plane"]["vol"], truth["exact"])), "体積の勝者が入れ替わった"
    assert nb["cp"] < 0.5 * nb["cl"], (nb["cp"], nb["cl"])
    # (b) 遮蔽の閉形式と、その差が離散化であること(1 次収束)
    assert occ["worst"] < 0.03, occ["worst"]
    cells = [c for c, _ in occ["conv"]]
    errs = [e for _, e in occ["conv"]]
    assert errs[0] > errs[1] > errs[2], occ["conv"]
    assert 1.5 < errs[0] / errs[1] < 2.5, occ["conv"]
    assert cells == [1.2, 0.6, 0.4]
    # 走査位置を増やすと遮蔽は落ちる。3 か所で塞がる
    assert sweep[("うねり", 1)]["occ"] > 0.5
    assert sweep[("うねり", 3)]["occ"] < 0.03, sweep[("うねり", 3)]["occ"]
    assert all(sweep[("うねり", k)]["outside"] == 0.0 for k in (1, 2, 3, 4))
    # ★外した予測: 補間は過小ではなく**過大**
    assert _pct(sweep[("うねり", 1)]["gt"]["vol"], truth["exact"]) > 10.0
    assert _pct(sweep[("平ら", 1)]["gt"]["vol"], truth["exact"]) > 10.0
    # ★相殺: 補間込みの外周だと誤差が小さく見え、見えた点だけだと戻る
    assert canc["ring"]["fill"] - canc["ring"]["true"] > 0.5
    small = abs(_pct(canc["外周平均(補間込み・現場の手)"]["got"]["vol"], truth["exact"]))
    honest = abs(_pct(canc["外周平均(見えた点だけ)"]["got"]["vol"], truth["exact"]))
    assert small < 1.0 < 10.0 < honest, (small, honest)
    # 土手: RANSAC は土手を捨てて「土手なし」へ戻る。TLS は逆向きにずれる
    assert abs(toe["RANSAC"]["got"]["vol"] - toe["clean"]["vol"]) \
        < abs(toe["TLS"]["got"]["vol"] - toe["clean"]["vol"]), toe
    assert toe["TLS"]["got"]["vol"] < toe["clean"]["vol"] < toe["RANSAC"]["got"]["vol"]
    # ★道具の穴。dem_viewshed が直ったらここが鳴る(それが目的)
    assert hole["apex_own"] == 1.0
    assert hole["apex_op"] == 0.0, "dem_viewshed が直った —— §8 の記述を更新すること"
    assert hole["occ_op"] > hole["occ_own"] + 0.25, (hole["occ_op"], hole["occ_own"])
    assert abs(hole["occ_own"] - hole["pred"]) < 0.03
    assert hole["above_vis"] == 0, hole["above_vis"]

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print(f"\n所要 {time.perf_counter() - t0:.1f} s")
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
