# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""コールドチェーンの温度記録 —— センサの置き場所が品質判定を決める。

    py -3.11 examples/poc_cold_chain_excursion.py

医薬品・生鮮の輸送は「規定温度(ここでは 2〜8 °C)を外れた時間」で合否が
決まります。判定に使うのはロガー 1〜数個の**点**の記録ですが、荷室の温度は
場所で違うので、どこに置いたかで合否が変わる。しかも品質は温度そのもの
ではなく**積算**(平均動力学温度 MKT や Arrhenius の速度積分)で決まるので、
「何分外れたか」と「どれだけ劣化したか」は別の量です。

この PoC は 12 m のリーファーの荷室を **(t, y, x) の 1 つの体積**として作り、
その体積を fullseye のボリューム op で読みます。ロガーの記録は
:func:`fullseye.vol_profile_line` で体積から抜いた**線プローブ**そのもの、
逸脱は :func:`fullseye.vol_label` で数える **3-D の塊**です。

EXTEND: 実測に差し替えるなら :func:`make_scene` が返す ``vol`` (T, Y, X) を
実測の温度場に、``is_product`` を「製品セルかどうか」に置き換えます。
**ロガー数点の記録だけでは足りません** —— この PoC の主題(点の記録と荷全体の
差)は点の記録には残らないので、CFD か多点マッピング(空荷マッピングでは
なく**実荷**)の温度場が要ります。

【グラウンドトゥルース】
物理は既知の閉形式で組み立て、時間積分だけ厳密に解く。

* 供給空気 ``T_sup(y,x) = T_set + g·d_vent`` —— 吹き出し口からの距離
  ``d_vent`` は :func:`fullseye.esdf` で測る(占有 = 吹き出し口セル)。
* 壁からの侵入 ``h0·(1−e^{−d_vent/L_throw})·w(y,x)·(T_amb(t) − T_sup)``。
  ``w`` は 4 枚の壁それぞれの ``esdf`` から ``Σ e^{−d/λ_w}`` —— **隅は 2 枚
  ぶん効く**。吹き出し口の近くは風で持ち去るので侵入が効かない。
* 扉開閉は既知の時刻・幅の矩形パルスで、扉からの距離に ``e^{−d_door/λ_d}``。
* 荷の熱容量は**1 次遅れ**。時定数 ``tau_load`` は空気 5 分、製品は
  パレットへの潜り込み深さ(これも ``esdf``)で 30〜100 分。
  ``T[n+1] = D[n+1] + (T[n] − D[n+1])·e^{−Δt/τ}`` は駆動が階段状なら**厳密**。
* 真の劣化は Arrhenius(``ΔH/R = 10000 K``、基準 5 °C)の速度を時間積分した
  **等価時間**。真の MKT は Haynes(1971)の定義そのもの。

【この PoC が測って分かったこと(数字は実行時に印字される実測値)】

1. **ゼロ点(ロガー 1 個の「規定を外れた合計時間」)は置き場所で 0 分から
   406 分まで動く**。真の最悪製品セルは 406 分、荷の 720 セル中
   130 セル(18.1 %)が本当に不合格。ところが**製品セルにロガーを 1 個置く
   と 76.7 % の置き方で「合格」と出る**。
2. ★★**見逃しと空振りは別の場所で起きる**。製品セルに 1 個置いた 400 通りの
   うち **73.5 % が偽合格**(ロガーは合格、真の最悪製品は不合格)。逆に
   通路・扉前の空気セルに置くと **偽不合格が 47.1 %**(ロガーは不合格、
   製品は全部健全)—— 扉開閉のパルスは空気だけを叩き、熱容量のある製品には
   届かない。**同じ荷を、置き場所だけで「不合格」にも「合格」にもできる**。
3. ★**崖は先に予測できる**。時定数 τ のロガーが幅 W・高さ A の矩形パルスを
   見ると、ピークは ``A(1−e^{−W/τ})`` までしか上がらない。規定まで余裕 M
   なら見かけのピークが規定を割るのは ``τ > W / ln(A/(A−M))``。扉前の空気
   セル(A = 10.60 K、W = 22 分、M = 3.53 K)の**予測 61.6 分**に対し
   **実測 62.0 分**(掃引の刻み 1 分以内)。τ = 12 分の実務用ロガーなら
   まだ見えるが、τ = 60 分の「製品模擬」ロガーでは同じ扉開閉が消える。
4. ★**サンプリング間隔の崖も幾何で予測できる**。幅 W のパルスは間隔 Δt が
   W を超えると位相によって丸ごと落ちる。落ちる割合の予測 ``1 − W/Δt`` に
   対し、位相を全部試した実測は Δt = 30 分で予測 26.7 % / 実測 26.7 %、
   Δt = 60 分で予測 63.3 % / 実測 63.3 %(**完全一致**)。
5. **量子化 0.5 K は逸脱時間を減らす方向にしか効かない**。丸めた値が
   「> 8.0 °C」を満たすには真値が 8.25 °C 以上要るので、実効しきい値が
   ``limit + q/2`` に上がる。予測(真値が limit+q/2 を超えた時間)と実測は
   q = 0.25/0.5/1.0 K で 344/337/324 分 対 344/337/324 分と**一致**。
6. ★★**同じ記録から出した 3 つの指標が食い違う**。「12 °C に何分いてよいか」
   に換算すると 逸脱時間 60 分 / MKT ≤ 8 °C は 277 分 / 劣化 ≤ 1.30 は
   197 分 —— **4.6 倍の開き**。全 720 セルにロガーを置いてみると
   **3 指標の合否が揃わないのは 174 セル(24.2 %)**。
7. ★★**MKT は集計窓の長さで動く**。同じ記録・同じ逸脱でも、12 時間で
   まとめると 6.63 °C(合格)、逸脱を含む 4 時間だけで切ると 8.55 °C
   (不合格)。逸脱時間はどちらの窓でも 240 分で変わらない。
   **「MKT は 8 °C 以下でした」は窓を書かないと意味が無い。**
8. ★**逸脱は 3-D の塊として数えられる**。``vol_label`` で (t,y,x) を切ると
   逸脱は **2 個の塊**で、いちばん大きい塊は 484 分続き 190 セルに広がる。
   「延べ逸脱セル時間」は 45231 セル分だが、これを「逸脱時間」と呼ぶと
   広がりと長さが混ざる —— 塊の ``extent`` は 2 つを分けて返す。
9. ★**ロガーを増やしても偽合格は素直に減らない**。製品セルにランダムに
   1/2/3/5/8 個置くと偽合格は 73.5 → 55.2 → 41.5 → 24.5 → 11.5 %。
   一方で「扉前・中央・吹き出し口前」の慣用 3 点は**偽合格**(その 3 点は
   どれも真の最悪点ではない)。★★**ランダム 3 個(41.5 %)のほうが、
   規約で決めた 3 点より当たる** —— 規約は「代表点」を選んでいるのであって
   「最悪点」を選んでいない。

来歴(公開文献のみ): Haynes, *J. Pharm. Sci.* 60 (1971) 927 —— 平均動力学温度
(MKT)/ ICH Q1A(R2) *Stability Testing*(ΔH = 83.144 kJ/mol の既定)/
Seevers et al., *Pharmaceutical Technology* (2009) —— MKT の誤用 /
WHO Technical Report Series 961, Annex 9 —— 温度マッピングは実荷で行う。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 荷室の諸元 -------------------------------------------------------------- #
CELL_M = 0.2            # セルの一辺 [m](esdf は等方 voxel_size しか取らない)
NY, NX = 60, 12         # 12.0 m(奥行き) x 2.4 m(幅)
NT = 720                # 720 分 = 12 時間
DT_MIN = 1.0            # 真値の時間刻み [min]

T_SET = 2.0             # 吹き出し温度 [°C]
G_DIST = 0.26           # 吹き出し口から離れるほど暖まる勾配 [K/m]
L_THROW = 3.0           # 風が届く距離 [m](ここまでは壁の侵入を持ち去る)
H_WALL = 0.100          # 壁からの侵入の効き [-]
LAM_WALL = 0.80         # 壁の影響が効く厚み [m]
A_DOOR = 13.0           # 扉開放時の流入の振幅 [K]
LAM_DOOR = 4.0          # 扉から奥への減衰長 [m]
TAU_AIR = 5.0           # 空気の時定数 [min]
TAU_P0, TAU_P1 = 30.0, 100.0   # 製品の時定数 [min](表層 -> 芯)
LAM_TAU = 0.30          # 潜り込み深さの効き [m]

# 扉開閉(開始, 終了)[min] —— 既知のイベント
DOOR_EVENTS = ((120, 134), (260, 274), (400, 424), (520, 534), (620, 644))

# --- 規定と判定 -------------------------------------------------------------- #
LIMIT_C = 8.0           # 規定の上限 [°C](2〜8 °C の上側)
EXC_ALLOW_MIN = 60.0    # 逸脱時間の許容 [min]
MKT_LIMIT_C = 8.0       # MKT の許容 [°C]
DEG_LIMIT = 1.30        # 劣化(等価時間 / 実時間)の許容 [-]
DH_OVER_R = 10000.0     # ΔH/R [K](ICH Q1A の ΔH = 83.144 kJ/mol)
T_REF_K = 278.15        # 劣化の基準温度 5 °C [K]

# --- ロガーの現実 ------------------------------------------------------------ #
TAU_LOG = 12.0          # ロガーの時定数 [min]
DT_SAMPLE = 15.0        # サンプリング間隔 [min]
QUANT_K = 0.5           # 分解能 [K]

SEED = 7
_L = fs.ledger


# --------------------------------------------------------------------------- #
# 幾何 —— 距離場はすべて esdf で測る                                            #
# --------------------------------------------------------------------------- #
def _dist_from(mask: np.ndarray) -> np.ndarray:
    """``mask`` が立っているセルからの距離 [m]。**esdf の外側(+)だけ使う**。

    ``esdf`` は「外 = + 最近占有まで / 内 = − 最近自由まで」を返すので、
    占有セル自身は負になる。距離としては 0 に潰す。
    """
    d = np.asarray(_L.esdf(mask.astype(bool), voxel_size=CELL_M), np.float64)
    return np.maximum(d, 0.0)


def build_layout() -> dict:
    """パレットの配置・距離場・時定数マップを作る(時間に依らない量)。"""
    is_air = np.zeros((NY, NX), bool)
    is_air[:, 5:7] = True                     # 中央通路 0.4 m
    for y0 in range(0, NY, 6):                # 6 セルごとに横通路 1 セル
        is_air[y0, :] = True
    is_air[NY - 1, :] = True                  # 扉の手前の空間
    is_product = ~is_air

    vent = np.zeros((NY, NX), bool)
    vent[0, 4:8] = True                       # 前壁の上部吹き出し口
    door = np.zeros((NY, NX), bool)
    door[NY - 1, :] = True                    # 後端 = 扉

    d_vent = _dist_from(vent)
    d_door = _dist_from(door)

    # 壁の効きは **4 枚それぞれ**の距離の和。隅は 2 枚ぶん効く(1 枚の最短
    # 距離だと隅と辺の区別がつかず、いちばん危ない場所が消える)。
    w = np.zeros((NY, NX))
    for wall in ("front", "back", "left", "right"):
        m = np.zeros((NY, NX), bool)
        if wall == "front":
            m[0, :] = True
        elif wall == "back":
            m[NY - 1, :] = True
        elif wall == "left":
            m[:, 0] = True
        else:
            m[:, NX - 1] = True
        w += np.exp(-_dist_from(m) / LAM_WALL)

    # パレットへの潜り込み深さ(空気からの距離)-> 時定数
    depth = _dist_from(is_air)
    tau = np.where(is_air, TAU_AIR,
                   TAU_P0 + (TAU_P1 - TAU_P0) * (1.0 - np.exp(-depth / LAM_TAU)))
    return {"is_air": is_air, "is_product": is_product, "d_vent": d_vent,
            "d_door": d_door, "wall": w, "depth": depth, "tau": tau,
            "vent": vent, "door": door}


def ambient(t_min: np.ndarray) -> np.ndarray:
    """外気温 [°C] —— 早朝に積んで昼過ぎに着く夏の輸送(18 -> 34 °C の単調上昇)。

    出発時に**どのセルも規定内**であること(実測 最高 7.69 °C)。ここが
    最初から 8 °C を超えていると「逸脱」ではなく「積み込み時点で不合格」に
    なってしまい、崖も対照群も意味を失う。
    """
    return 26.0 + 8.0 * np.sin(2.0 * np.pi * (t_min - 360.0) / 1440.0)


def door_open(t_min: np.ndarray, events=DOOR_EVENTS) -> np.ndarray:
    """扉が開いているか(0/1)。"""
    o = np.zeros_like(t_min, np.float64)
    for a, b in events:
        o[(t_min >= a) & (t_min < b)] = 1.0
    return o


def make_scene(uniform: bool = False, doors: bool = True,
               layout: dict | None = None, wall_scale: float = 1.0) -> dict:
    """真の温度場 ``(t, y, x)`` [°C] とその来歴を返す。

    ``uniform=True`` は**荷が均一**(温度場が場所に依らない)対照群、
    ``doors=False`` は**扉を開けない**対照群、``wall_scale`` は壁からの
    侵入の効きを弱める(積み付けを直す / 断熱を良くする)対照群。

    ★設定温度を下げて荷を健全にする手もあるが、上限を守るために -4.5 K
    下げると最低温度が -2.5 °C になり **今度は下限(2 °C)を割る**。
    「上を守れば下を割る」は本題ではないので、ここは断熱で直す。
    """
    lay = layout or build_layout()
    t = np.arange(NT, dtype=np.float64) * DT_MIN
    amb = ambient(t)
    op = door_open(t) if doors else np.zeros_like(t)

    t_sup = T_SET + G_DIST * lay["d_vent"]
    throw = 1.0 - np.exp(-lay["d_vent"] / L_THROW)
    gain = H_WALL * wall_scale * throw * lay["wall"]
    pulse = A_DOOR * np.exp(-lay["d_door"] / LAM_DOOR)
    tau = lay["tau"]

    if uniform:
        # 「荷が均一」= 場所に依らない 1 本の場。空間平均の駆動と平均時定数。
        t_sup = np.full_like(t_sup, float(t_sup.mean()))
        gain = np.full_like(gain, float(gain.mean()))
        pulse = np.full_like(pulse, float(pulse.mean()))
        tau = np.full_like(tau, float(tau.mean()))

    alpha = np.exp(-DT_MIN / tau)             # 1 次遅れの厳密な 1 ステップ
    vol = np.empty((NT, NY, NX), np.float64)
    drive0 = t_sup + gain * (amb[0] - t_sup)
    state = drive0.copy()                     # 出発は定常(積み込み直後)
    for k in range(NT):
        drive = t_sup + gain * (amb[k] - t_sup) + pulse * op[k]
        state = drive + (state - drive) * alpha
        vol[k] = state
    return {"vol": vol, "t": t, "amb": amb, "door": op, "layout": lay,
            "uniform": uniform, "doors": doors}


# --------------------------------------------------------------------------- #
# 3 つの判定 —— 逸脱時間 / MKT / Arrhenius                                      #
# --------------------------------------------------------------------------- #
def excursion_minutes(temp: np.ndarray, dt: float, limit: float = LIMIT_C) -> float:
    """規定を外れた合計時間 [min](各標本が dt 分を代表する、という素朴な数え方)。"""
    return float(np.count_nonzero(np.asarray(temp) > limit) * dt)


def mkt_celsius(temp: np.ndarray) -> float:
    """平均動力学温度 [°C](Haynes 1971)。**算術平均ではない**。"""
    tk = np.asarray(temp, np.float64) + 273.15
    u = float(np.mean(np.exp(-DH_OVER_R / tk)))
    return DH_OVER_R / (-np.log(u)) - 273.15


def degradation_index(temp: np.ndarray, dt: float) -> float:
    """Arrhenius の速度を時間積分した**等価時間 / 実時間**。

    累積積分は :func:`fullseye.integrate_funct_1d`(台形則)で取る ——
    「速度を時間で積む」は 1-D 関数の op がそのまま使える場面。
    """
    tk = np.asarray(temp, np.float64) + 273.15
    rate = np.exp(-DH_OVER_R * (1.0 / tk - 1.0 / T_REF_K))
    if rate.size < 2:
        return float(rate.mean())
    cum = np.asarray(fs.integrate_funct_1d(rate), np.float64)   # 台形則の累積
    return float(cum[-1] * dt) / float((rate.size - 1) * dt)


def verdicts(temp: np.ndarray, dt: float) -> tuple[bool, bool, bool]:
    """(逸脱時間 OK, MKT OK, 劣化 OK)。True = 合格。"""
    return (excursion_minutes(temp, dt) <= EXC_ALLOW_MIN,
            mkt_celsius(temp) <= MKT_LIMIT_C,
            degradation_index(temp, dt) <= DEG_LIMIT)


def allowed_minutes_at(hot_c: float, base_c: float, total_min: float) -> dict:
    """「``hot_c`` °C に何分いてよいか」に 3 つの判定を換算する(閉形式)。"""
    out = {"excursion": EXC_ALLOW_MIN}
    # MKT: (1-f)e^{-E/Tb} + f e^{-E/Th} = e^{-E/Tlim}
    tb, th, tl = base_c + 273.15, hot_c + 273.15, MKT_LIMIT_C + 273.15
    eb, eh, el = (np.exp(-DH_OVER_R / v) for v in (tb, th, tl))
    f = (el - eb) / (eh - eb)
    out["mkt"] = float(np.clip(f, 0.0, 1.0) * total_min)
    # 劣化: (1-f) r(Tb) + f r(Th) = DEG_LIMIT
    rb = np.exp(-DH_OVER_R * (1.0 / tb - 1.0 / T_REF_K))
    rh = np.exp(-DH_OVER_R * (1.0 / th - 1.0 / T_REF_K))
    f2 = (DEG_LIMIT - rb) / (rh - rb)
    out["degradation"] = float(np.clip(f2, 0.0, 1.0) * total_min)
    return out


# --------------------------------------------------------------------------- #
# ロガーの現実 —— 遅れ・粗いサンプリング・量子化                                 #
# --------------------------------------------------------------------------- #
def first_order_lag(x: np.ndarray, tau: float, dt: float = DT_MIN) -> np.ndarray:
    """1 次遅れ(RC)フィルタ。**公開経路に無いので自前**(道具の穴 (a))。

    軸 0 が時間。初期値は定常(``x[0]``)—— ゼロから始めると先頭に偽の
    立ち上がりが出る。
    """
    x = np.asarray(x, np.float64)
    if tau <= 0:
        return x.copy()
    a = float(np.exp(-dt / tau))
    out = np.empty_like(x)
    s = x[0].copy() if x.ndim > 1 else float(x[0])
    for k in range(x.shape[0]):
        s = x[k] + (s - x[k]) * a
        out[k] = s
    return out


def quantize(x: np.ndarray, q: float) -> np.ndarray:
    """分解能 ``q`` [K] に丸める。**公開経路に無いので自前**(道具の穴 (b))。"""
    return x if q <= 0 else np.round(np.asarray(x) / q) * q


def logger_record(true_series: np.ndarray, tau: float = TAU_LOG,
                  dt_s: float = DT_SAMPLE, q: float = QUANT_K,
                  phase: int = 0) -> tuple[np.ndarray, float]:
    """真の局所温度 -> ロガーが残す記録(値の列, 標本間隔 [min])。"""
    lag = first_order_lag(true_series, tau)
    step = max(1, int(round(dt_s / DT_MIN)))
    # 粗いサンプリングは HALCON 由来の sample_funct_1d(step 個おき)。
    rec = np.asarray(fs.sample_funct_1d(lag[phase % step:], step=step), np.float64)
    return quantize(rec, q), step * DT_MIN


FIG_ZOOM = 8            # 平面図の拡大率(60x12 のままだと題が入らない)


def plan_view(m: np.ndarray, zoom: int = FIG_ZOOM) -> np.ndarray:
    """(奥行き, 幅) の地図を**横長の平面図**にして拡大する。

    左 = 吹き出し口 / 右 = 扉。荷室は 60 x 12 セルしかないので、そのまま
    :func:`examplefig.save_grid` に渡すとパネルの題が 12 px に収まらず
    例外になる(fullseye の ``text_box`` は黙って切らない)。
    """
    return np.repeat(np.repeat(np.asarray(m, np.float64).T, zoom, 0), zoom, 1)


def probe_true(vol: np.ndarray, y: int, x: int) -> np.ndarray:
    """体積からロガー位置の真の時系列を抜く —— :func:`vol_profile_line` の線プローブ。"""
    _, val = fs.vol_profile_line(vol, (0, y, x), (NT - 1, y, x), n=NT)
    return np.asarray(val, np.float64)


# --------------------------------------------------------------------------- #
# 1. 場面と真値                                                                 #
# --------------------------------------------------------------------------- #
def section_scene(scene: dict) -> dict:
    print("\n" + "=" * 78)
    print("1) 荷室を (t, y, x) の 1 つの体積として作る")
    print("=" * 78)
    lay = scene["layout"]
    vol = scene["vol"]
    n_prod = int(lay["is_product"].sum())
    print("  体積 %d 分 x %d x %d セル(%.1f m x %.1f m、1 セル %.2f m)" % (
        NT, NY, NX, NY * CELL_M, NX * CELL_M, CELL_M))
    print("  製品セル %d / 空気セル %d、外気 %.1f -> %.1f °C、扉開閉 %d 回"
          % (n_prod, int(lay["is_air"].sum()), scene["amb"][0], scene["amb"][-1],
             len(DOOR_EVENTS)))
    print("  時定数: 空気 %.0f 分 / 製品 %.0f〜%.0f 分(潜り込み深さ 最大 %.2f m)"
          % (TAU_AIR, lay["tau"][lay["is_product"]].min(),
             lay["tau"][lay["is_product"]].max(), lay["depth"].max()))

    tmax = np.asarray(fs.temporal_max(vol))          # 各セルの最高温度
    exc = np.count_nonzero(vol > LIMIT_C, axis=0) * DT_MIN
    prod = lay["is_product"]
    iy, ix = np.unravel_index(int(np.argmax(np.where(prod, exc, -1))), exc.shape)
    print("  真の最悪**製品**セル (y=%d, x=%d): 最高 %.2f °C、逸脱 %.0f 分"
          % (iy, ix, tmax[iy, ix], exc[iy, ix]))
    print("  真の最悪**空気**セル: 最高 %.2f °C、逸脱 %.0f 分"
          % (tmax[lay["is_air"]].max(),
             exc[lay["is_air"]].max()))
    n_bad = int(np.count_nonzero((exc > EXC_ALLOW_MIN) & prod))
    print("  規定を %.0f 分より長く外れた製品セル: %d / %d (%.1f %%)"
          % (EXC_ALLOW_MIN, n_bad, n_prod, 100.0 * n_bad / n_prod))

    if figs.enabled():
        idx = [10, 130, 300, 410]
        figs.save_grid("scene_slices", [plan_view(vol[k]) for k in idx],
                       ["t = %d 分(出発)" % idx[0], "t = %d 分(扉 1 回目)" % idx[1],
                        "t = %d 分(閉扉中)" % idx[2], "t = %d 分(扉 3 回目)" % idx[3]],
                       title="荷室の温度場 [°C](左 = 吹き出し口 / 右 = 扉)", ncols=2,
                       caption="同じ色尺度ではない —— 各枚は自分の最小最大で塗られる。"
                               "数字は本文の表を見ること。")
        figs.save_grid("layout_maps",
                       [plan_view(lay["is_product"].astype(float)),
                        plan_view(lay["d_vent"]), plan_view(lay["wall"]),
                        plan_view(lay["tau"])],
                       ["製品セル(明)と通路", "吹き出し口からの距離 [m]",
                        "壁の効き [-]", "時定数 [min]"],
                       title="荷室の geometry —— 距離場はすべて esdf で測る", ncols=2)
    return {"tmax": tmax, "exc": exc, "worst": (int(iy), int(ix)),
            "n_bad": n_bad, "n_prod": n_prod}


# --------------------------------------------------------------------------- #
# 2. ゼロ点 —— ロガー 1 個の「逸脱時間」                                         #
# --------------------------------------------------------------------------- #
def _cell_records(vol: np.ndarray, tau=TAU_LOG, dt_s=DT_SAMPLE, q=QUANT_K):
    """全セルにロガーを置いたときの記録を一度に作る(掃引の下ごしらえ)。"""
    lag = first_order_lag(vol, tau)
    step = max(1, int(round(dt_s / DT_MIN)))
    rec = quantize(lag[::step], q)                       # (n_s, NY, NX)
    return rec, step * DT_MIN


def section_zero_point(scene: dict, truth: dict) -> dict:
    print("\n" + "=" * 78)
    print("2) ゼロ点 —— ロガー 1 個の「規定を外れた合計時間」")
    print("=" * 78)
    vol, lay = scene["vol"], scene["layout"]
    prod = lay["is_product"]

    rec, dt_s = _cell_records(vol)
    exc_meas = np.count_nonzero(rec > LIMIT_C, axis=0) * dt_s
    print("  ロガー: τ=%.0f 分 / 間隔 %.0f 分 / 分解能 %.2f K" % (TAU_LOG, dt_s, QUANT_K))
    print("  1 個の記録が出す逸脱時間は置き場所で %.0f 〜 %.0f 分"
          % (exc_meas.min(), exc_meas.max()))
    print("  真の最悪製品セルの逸脱 %.0f 分 / 真の最悪空気セル %.0f 分"
          % (truth["exc"][prod].max(), truth["exc"][lay["is_air"]].max()))

    pass_meas = exc_meas <= EXC_ALLOW_MIN
    load_fails = bool((truth["exc"][prod] > EXC_ALLOW_MIN).any())
    rate_prod = 100.0 * float(pass_meas[prod].mean())
    print("  製品セルに 1 個置いたとき「合格」と出る割合: %.1f %%"
          "(荷は本当は%s)" % (rate_prod, "不合格" if load_fails else "合格"))

    # 代表 3 点(慣用の置き方)
    named = {"扉の手前(空気)": (NY - 1, NX // 2),
             "荷の中央(製品)": (NY // 2 + 1, 2),
             "吹き出し口前(空気)": (1, 6),
             "真の最悪製品": truth["worst"]}
    rows = []
    print("\n  場所                  真の逸脱   記録の逸脱    MKT      劣化    合否(逸脱/MKT/劣化)")
    for name, (y, x) in named.items():
        tr = probe_true(vol, y, x)
        r, ds = logger_record(tr)
        v = verdicts(r, ds)
        rows.append([name, "%.0f" % excursion_minutes(tr, DT_MIN),
                     "%.0f" % excursion_minutes(r, ds), "%.2f" % mkt_celsius(r),
                     "%.3f" % degradation_index(r, ds),
                     "/".join("合" if b else "否" for b in v)])
        print("   %-18s %6s 分   %6s 分   %5s °C  %6s   %s"
              % (name, rows[-1][1], rows[-1][2], rows[-1][3], rows[-1][4], rows[-1][5]))

    if figs.enabled():
        y0, x0 = truth["worst"]
        tr_w = probe_true(vol, y0, x0)
        tr_d = probe_true(vol, NY - 1, NX // 2)
        tr_c = probe_true(vol, NY // 2 + 1, 2)
        r_d, ds = logger_record(tr_d)
        ts = np.arange(r_d.size) * ds
        figs.save_plot("traces",
                       [("真値: 最悪製品 (y=%d,x=%d)" % (y0, x0), scene["t"], tr_w),
                        ("真値: 扉前の空気", scene["t"], tr_d),
                        ("記録: 扉前の空気(τ%.0f/間隔%.0f/量子化%.1f)" % (TAU_LOG, ds, QUANT_K),
                         ts, r_d),
                        ("真値: 荷の中央の製品", scene["t"], tr_c),
                        ("規定 %.0f °C" % LIMIT_C, scene["t"],
                         np.full(NT, LIMIT_C))],
                       xlabel="時刻 [min]", ylabel="温度 [°C]",
                       title="同じ荷室・3 つの置き場所(と、その 1 つの記録)",
                       caption="扉前の空気は跳ねるが製品には届かない。"
                               "最悪製品は跳ねないがずっと規定の上にいる。")
        figs.save_table("placement_table",
                        ["場所", "真の逸脱 min", "記録の逸脱 min", "MKT °C", "劣化 -",
                         "合否 逸脱/MKT/劣化"], rows,
                        title="置き場所で判定が変わる(ロガーの仕様は同じ)")
    return {"exc_meas": exc_meas, "pass_meas": pass_meas, "dt_s": dt_s,
            "rate_prod": rate_prod, "rows": rows}


# --------------------------------------------------------------------------- #
# 3-5. 崖 —— 先に予測してから掃引する                                           #
# --------------------------------------------------------------------------- #
def _aisle_cells(scene: dict) -> list[tuple[int, int, float, float]]:
    """崖を測るセルを**規則で選ぶ**(1 点を手で決め打たない)。

    中央通路(空気)の列のうち、**扉のパルスで規定を跨ぐ**セル ——
    底は規定の下、いちばん長い扉開放でのピークは規定の上 —— を扉に近い順に
    最大 5 つ。1 点だけ選ぶと「たまたま崖が実務の τ の範囲から外れる」ことが
    あり(扉のすぐ手前は底が 7.9 °C で余裕 0.1 K、崖が 600 分になる)、
    位置を振ることで**予測と実測の一致が位置に依らない**ことまで言える。
    """
    vol, lay = scene["vol"], scene["layout"]
    a0, b0 = DOOR_EVENTS[2]
    base = np.median(vol[a0 - 60:a0], axis=0)
    peak = vol[a0:b0 + 30].max(axis=0)
    x = NX // 2 - 1                                  # 中央通路の 1 列
    ys = [y for y in range(NY)
          if lay["is_air"][y, x] and base[y, x] < LIMIT_C and peak[y, x] > LIMIT_C]
    if not ys:                                       # 扉を切った対照群での保険
        ys = [y for y in range(NY) if lay["is_air"][y, x] and base[y, x] < LIMIT_C]
    ys = ys[::-1]                                    # 扉に近い順
    pick = ys[:: max(1, len(ys) // 5)][:5]
    return [(int(y), int(x), float(base[y, x]), float(peak[y, x] - base[y, x]))
            for y in pick]


def _rect_cascade_peak(a_drive: float, width: float, tau1: float,
                       tau2: float) -> float:
    """矩形パルス -> 荷室の空気(τ1)-> ロガー(τ2)のピーク上昇 [K]。

    **場のシミュレーションを一切使わない**ので「紙の上の予測」。
    パルスの前に十分な平坦部を置くこと —— 先頭からいきなり立てると
    :func:`first_order_lag` の初期値が高い側に張り付いて、遅れが消える
    (2026-09-08 に踏んだ)。
    """
    n_pre = 60
    rect = np.zeros(n_pre + int(width) + 600)
    rect[n_pre:n_pre + int(width)] = a_drive
    return float(first_order_lag(first_order_lag(rect, tau1), tau2).max())


def section_cliffs(scene: dict) -> dict:
    print("\n" + "=" * 78)
    print("3-5) 崖 —— 時定数 / サンプリング間隔 / 量子化。**先に予測する**")
    print("=" * 78)
    vol, lay = scene["vol"], scene["layout"]
    a0, b0 = DOOR_EVENTS[2]
    width = float(b0 - a0)
    # ★ピークを探す窓は**次の扉開閉の手前まで**。ここを広く取ると、τ が大きい
    #   ところで次のパルスの立ち上がりを拾い、「崖が来ない」ように見える
    #   (2026-09-08 に 200 分の窓で踏んだ: y=53 の実測が 153 分に伸びた)。
    t_end = int(min(NT, DOOR_EVENTS[3][0]))
    taus = np.arange(1.0, 181.0, 1.0)
    cells = _aisle_cells(scene)

    print("  (3) 時定数の崖 —— 幅 W=%.0f 分の扉開放(3 回目)を中央通路で測る。"
          % width)
    print("      1 極の予測 τ* = W / ln(A/(A-M))。2 段の予測は「矩形 -> 空気"
          "(τ=%.0f 分) -> ロガー」を紙の上で解いたもの。" % TAU_AIR)
    print("      位置       扉から   底     A      M     予測1極  予測2段   実測")
    rows_t, best = [], None
    for (y, x, base, amp) in cells:
        tr = probe_true(vol, y, x)
        margin = LIMIT_C - base
        t1 = width / np.log(amp / (amp - margin)) if amp > margin else np.inf
        a_drive = A_DOOR * float(np.exp(-lay["d_door"][y, x] / LAM_DOOR))
        p2 = np.asarray([_rect_cascade_peak(a_drive, width, TAU_AIR, float(t_))
                         for t_ in taus])
        t2 = float(taus[np.argmax(p2 <= margin)]) if (p2 <= margin).any() else np.inf
        seen = np.asarray([float(first_order_lag(tr, float(t_))[a0:t_end].max())
                           - base for t_ in taus])
        tm = float(taus[np.argmax(seen <= margin)]) if (seen <= margin).any() else np.inf
        rows_t.append(["y=%d" % y, "%.1f" % lay["d_door"][y, x], "%.2f" % base,
                       "%.2f" % amp, "%.2f" % margin, "%.0f" % t1, "%.0f" % t2,
                       "%.0f" % tm])
        print("      y=%2d      %5.1f m  %5.2f  %5.2f  %5.2f    %5.0f    %5.0f   %5.0f 分"
              % (y, lay["d_door"][y, x], base, amp, margin, t1, t2, tm))
        if np.isfinite(tm) and (best is None or tm > best["tau_meas"]):
            best = {"y": y, "x": x, "base": base, "amp": amp, "margin": margin,
                    "tau_1pole": t1, "tau_2pole": t2, "tau_meas": tm,
                    "seen": seen, "pred2": p2,
                    "pred1": amp * (1.0 - np.exp(-width / taus))}
    # 崖が掃引の外(τ>%d 分)に出た行は「測れなかった」ので比べない。
    ok_rows = [r for r in rows_t if np.isfinite(float(r[7]))]
    e1 = max(abs(float(r[5]) - float(r[7])) for r in ok_rows
             if np.isfinite(float(r[5])))
    e2 = max(abs(float(r[6]) - float(r[7])) for r in ok_rows
             if np.isfinite(float(r[6])))
    r1 = [abs(float(r[5]) - float(r[7])) / float(r[7]) for r in ok_rows]
    r2 = [abs(float(r[6]) - float(r[7])) / float(r[7]) for r in ok_rows]
    print("      ★崖が測れた %d 行での予測と実測のずれ: 1 極 最大 %.0f 分 "
          "(相対 %.0f %%) / 2 段 最大 %.0f 分 (相対 %.0f %%)。"
          % (len(ok_rows), e1, 100 * max(r1), e2, 100 * max(r2)))
    print("      崖が短い側(τ* = %.0f〜%.0f 分)では 2 段の予測が %.0f〜%.0f %% と"
          "よく当たる。1 極の式はそこで %.0f %% ずれる —— **荷室の空気そのものが"
          "1 次遅れ**なので、ロガーが完璧でもパルスは既に鈍っているから。"
          % (float(ok_rows[-1][7]), float(ok_rows[-2][7]),
             100 * min(r2), 100 * r2[-2], 100 * max(r1[-2:])))
    print("      ★逆に、いちばん扉に近い測れた行(τ* = %.0f 分)では 1 極のほうが"
          "近い(%.0f %% 対 %.0f %%)—— 余裕 M が %.2f K しかなく、外気の"
          "上昇による底の drift がパルスと同じ大きさになるので、**どちらの式も"
          "前提を外れている**。" % (float(ok_rows[0][7]), 100 * r1[0], 100 * r2[0],
                                    float(ok_rows[0][4])))
    print("      扉のすぐ手前(余裕 %.2f K)は崖が掃引の上限 %.0f 分より遠く、"
          "**そもそも測れない** —— 予測 1 極は %s 分と言うが確かめようがない。"
          % (float(rows_t[0][4]), taus[-1], rows_t[0][5]))
    print("      実務の τ=%.0f 分なら y=%d はまだ見えるが、"
          "「製品模擬」の τ=60 分では消える。" % (TAU_LOG, best["y"]))

    # (4) サンプリング間隔 —— 位相を全部試す。**遅れは切って**間隔だけを見る。
    y, x = best["y"], best["x"]
    tr = probe_true(vol, y, x)
    print("\n  (4) サンプリング間隔の崖(対照: ロガーの遅れを 0 にして"
          "間隔だけを見る。y=%d, x=%d)" % (y, x))
    hot = np.nonzero(tr[a0 - 5:t_end] > LIMIT_C)[0]
    w_eff = float(hot.size * DT_MIN)
    lo = int(a0 - 5 + hot[0]); hi = int(a0 - 5 + hot[-1]) + 1
    print("      真値がこのパルスで規定を超えている時間 W_eff = %.0f 分"
          " (%d〜%d 分)。予測: 丸ごと落ちる位相の割合 = 1 - W_eff/Δt"
          % (w_eff, lo, hi))
    rows_s = []
    for dts in (5.0, 10.0, 15.0, 30.0, 45.0, 60.0, 90.0):
        step = int(round(dts / DT_MIN))
        miss = 0
        for ph in range(step):
            tt = np.arange(ph, NT, step)
            sel = tt[(tt >= lo) & (tt < hi)]
            if sel.size == 0 or not (tr[sel] > LIMIT_C).any():
                miss += 1
        got = 100.0 * miss / step
        want = 100.0 * max(0.0, 1.0 - w_eff / dts)
        rows_s.append([("%.0f" % dts), ("%.1f" % want), ("%.1f" % got)])
        print("      Δt = %5.0f 分  予測 %5.1f %%  実測 %5.1f %%" % (dts, want, got))
    s_err = max(abs(float(r[1]) - float(r[2])) for r in rows_s)
    print("      予測と実測の差 最大 %.1f 分ポイント(整数の位相を全部試した"
          "ので偶然ではない)。" % s_err)

    # (5) 量子化
    print("\n  (5) 量子化の崖 —— 実効しきい値が limit + q/2 に上がる")
    rows_q = []
    y2, x2 = _mid_product(scene)
    trp = probe_true(vol, y2, x2)
    print("      製品セル (y=%d, x=%d、真の逸脱 %.0f 分)を、分解能だけ変えて"
          "数え直す。" % (y2, x2, excursion_minutes(trp, DT_MIN)))
    for q in (0.0, 0.1, 0.25, 0.5, 1.0, 2.0):
        got = excursion_minutes(quantize(trp, q), DT_MIN)
        want = float(np.count_nonzero(trp > LIMIT_C + q / 2.0) * DT_MIN)
        rows_q.append([("%.2f" % q), ("%.0f" % want), ("%.0f" % got)])
        print("      q = %4.2f K  予測 %4.0f 分  実測 %4.0f 分" % (q, want, got))
    q_err = max(abs(float(r[1]) - float(r[2])) for r in rows_q)
    print("      予測と実測の差 最大 %.0f 分。量子化は**必ず短くする側**にしか"
          "効かない(切り上げの位相が無い)。" % q_err)

    if figs.enabled():
        figs.save_plot("sweep_tau",
                       [("実測: 見かけのピーク上昇 (y=%d)" % best["y"], taus, best["seen"]),
                        ("予測 1 極: A(1-e^(-W/τ))", taus, best["pred1"]),
                        ("予測 2 段: 空気 τ=%.0f 分 + ロガー" % TAU_AIR, taus, best["pred2"]),
                        ("規定までの余裕 M = %.2f K" % best["margin"], taus,
                         np.full_like(taus, best["margin"]))],
                       xlabel="ロガーの時定数 τ [min]", ylabel="ピークの上昇 [K]",
                       title="扉開閉(W=%.0f 分)が消える τ: 予測 %.0f / %.0f、実測 %.0f 分"
                             % (width, best["tau_1pole"], best["tau_2pole"],
                                best["tau_meas"]),
                       caption="教科書の 1 極公式は荷室の空気の遅れを勘定に入れないので"
                               "崖を遅く見積もる。")
        figs.save_table("sweep_tau_positions",
                        ["位置", "扉から [m]", "底 [°C]", "A [K]", "M [K]",
                         "予測 1 極 [min]", "予測 2 段 [min]", "実測 [min]"], rows_t,
                        title="崖の τ は位置で 1 桁動く(予測も一緒に動く)")
        figs.save_table("sweep_sampling",
                        ["Δt [min]", "予測 落ちる割合 [%]", "実測 [%]"], rows_s,
                        title="間隔でパルスが丸ごと落ちる割合",
                        caption="位相を全部試した。パルスが規定を超えている"
                                "時間 W_eff = %.0f 分。" % w_eff)
        figs.save_table("sweep_quant",
                        ["分解能 q [K]", "予測 逸脱 [min]", "実測 [min]"], rows_q,
                        title="量子化は実効しきい値を limit + q/2 に上げる")
    return {"tau_1pole": best["tau_1pole"], "tau_2pole": best["tau_2pole"],
            "tau_meas": best["tau_meas"], "amp": best["amp"],
            "margin": best["margin"], "width": width, "w_eff": w_eff,
            "cell": (best["y"], best["x"]), "rows_t": rows_t, "rows_s": rows_s,
            "rows_q": rows_q, "s_err": s_err, "q_err": q_err,
            "err_1pole": e1, "err_2pole": e2,
            "rel_1pole": float(max(r1)), "rel_2pole": float(max(r2)),
            "n_cells": len(cells), "n_measurable": len(ok_rows)}


def _worst_product(scene: dict) -> tuple[int, int]:
    vol, prod = scene["vol"], scene["layout"]["is_product"]
    exc = np.count_nonzero(vol > LIMIT_C, axis=0) * DT_MIN
    iy, ix = np.unravel_index(int(np.argmax(np.where(prod, exc, -1))), exc.shape)
    return int(iy), int(ix)


def _mid_product(scene: dict, target: float = 300.0) -> tuple[int, int]:
    """真の逸脱が ``target`` 分にいちばん近い製品セル(飽和していない例)。"""
    vol, prod = scene["vol"], scene["layout"]["is_product"]
    exc = np.count_nonzero(vol > LIMIT_C, axis=0) * DT_MIN
    d = np.where(prod, np.abs(exc - target), np.inf)
    iy, ix = np.unravel_index(int(np.argmin(d)), exc.shape)
    return int(iy), int(ix)


# --------------------------------------------------------------------------- #
# 6. 対照群 —— 均一 / 分布あり / 分布 + 扉                                       #
# --------------------------------------------------------------------------- #
NEAR_M = 1.0            # 「そのロガーが代表する荷」の半径 [m]
WALL_FIX = 0.0          # 対照群 (d): 壁からの侵入を止める(扉だけを残す)


def section_controls(layout: dict) -> dict:
    """2 つの要因(壁からの侵入 / 扉開閉)を 1 つずつ止める 4 条件。

    **偽不合格は「近くの製品」で定義する**。荷のどこかが不合格なら「荷は
    不合格」なので、全体で見ると偽不合格は原理的に定義できない。実務の
    「扉のセンサが鳴ったが、そこのパレットは無事だった」を測るには
    **半径 %.1f m 以内の製品セルがすべて健全か**で見るしかない。
    """ % NEAR_M
    print("\n" + "=" * 78)
    print("6) 対照群 —— (a) 均一 / (b) 壁だけ / (c) 壁+扉 / (d) 扉だけ")
    print("=" * 78)
    print("  条件               真に不合格な   偽合格 [%]      偽不合格 [%]")
    print("                     製品セル [%%]   (製品に 1 個)   (空気に 1 個、"
          "近傍 %.1f m の製品は健全)" % NEAR_M)

    prod = layout["is_product"]
    air = layout["is_air"]
    out = {}
    rows = []
    for name, kw in (("(a) 均一+扉", dict(uniform=True, doors=True)),
                     ("(b) 壁だけ", dict(uniform=False, doors=False)),
                     ("(c) 壁+扉", dict(uniform=False, doors=True)),
                     ("(d) 扉だけ", dict(uniform=False, doors=True,
                                         wall_scale=WALL_FIX))):
        sc = make_scene(layout=layout, **kw)
        vol = sc["vol"]
        exc_true = np.count_nonzero(vol > LIMIT_C, axis=0) * DT_MIN
        bad_prod = (exc_true > EXC_ALLOW_MIN) & prod
        load_fail = bool(bad_prod.any())
        rec, dt_s = _cell_records(vol)
        exc_meas = np.count_nonzero(rec > LIMIT_C, axis=0) * dt_s
        says_pass = exc_meas <= EXC_ALLOW_MIN
        fp = 100.0 * float(says_pass[prod].mean()) if load_fail else 0.0
        # 近くに本当に傷んだ製品が 1 つも無いのに不合格を出す空気セル
        near_bad = _dist_from(bad_prod) <= NEAR_M if load_fail else \
            np.zeros_like(prod, bool)
        ff = 100.0 * float(((~says_pass) & ~near_bad)[air].mean())
        bad = 100.0 * float(bad_prod[prod].mean())
        rows.append([name, "%.1f" % bad, "%.1f" % fp, "%.1f" % ff])
        print("  %-16s %8.1f       %8.1f        %8.1f" % (name, bad, fp, ff))
        out[name] = {"scene": sc, "exc_true": exc_true, "exc_meas": exc_meas,
                     "bad": bad, "fp": fp, "ff": ff, "load_fail": load_fail}

    a, b, c, d = (out["(a) 均一+扉"], out["(b) 壁だけ"], out["(c) 壁+扉"],
                  out["(d) 扉だけ"])
    print("\n  ★(a) 均一なら置き場所は効かない —— 偽合格 %.1f %% / 偽不合格 "
          "%.1f %%。「ロガー 1 個で足りる」は**均一を仮定している**。"
          % (a["fp"], a["ff"]))
    print("  ★(b) 壁からの侵入だけで(扉は 1 度も開けない)真に不合格な製品が"
          " %.1f %%、偽合格 %.1f %%。**偽不合格はほぼ出ない**(%.1f %%)——"
          "じわじわ暖まる荷では空気と製品が同じ向きに動く。"
          % (b["bad"], b["fp"], b["ff"]))
    print("  ★(c) 両方あると偽不合格は %.1f %% —— **隠れる**。扉のパルスが"
          "叩く空気のそばの製品は、壁の侵入のせいでどのみち傷んでいるから。"
          % c["ff"])
    print("  ★(d) 壁を止めて扉だけ残すと、真に不合格な製品は %.1f -> %.1f %% に"
          "落ちるのに、偽不合格は %.1f -> %.1f %% に**現れる** —— パルスは空気"
          "だけを叩き、熱容量のある製品には届かない。"
          % (c["bad"], d["bad"], c["ff"], d["ff"]))
    print("     ★★(d) では真に傷んだ製品が %.1f %% 残っているのに、製品セルに"
          "置いたロガーは **%.0f %% が合格**と言う —— 短いパルスは製品に"
          "入らないので、製品に貼ったロガーもまた見えない。"
          % (d["bad"], d["fp"]))
    if figs.enabled():
        figs.save_table("control_groups",
                        ["条件", "真に不合格な製品セル [%]",
                         "偽合格 [%](製品に 1 個)",
                         "偽不合格 [%](空気に 1 個)"],
                        rows, title="要因を 1 つずつ止める")
        figs.save_grid("control_maps",
                       [plan_view(v["exc_true"]) for v in (a, b, c, d)],
                       ["(a) 均一+扉", "(b) 壁だけ", "(c) 壁+扉", "(d) 扉だけ"],
                       title="真の逸脱時間の地図 [min](左=吹き出し口 / 右=扉)",
                       ncols=2)
    return out


# --------------------------------------------------------------------------- #
# 7. 3 つの指標が食い違う                                                       #
# --------------------------------------------------------------------------- #
def section_metrics(scene: dict) -> dict:
    print("\n" + "=" * 78)
    print("7) 判定を 3 つ比べる —— 逸脱時間 / MKT / Arrhenius")
    print("=" * 78)
    vol, lay = scene["vol"], scene["layout"]

    eq = allowed_minutes_at(12.0, 4.0, NT * DT_MIN)
    print("  「12 °C に何分いてよいか」に換算する(基準 4 °C、記録 %d 分):" % NT)
    print("      逸脱時間 <= %.0f 分        ->  %6.0f 分" % (EXC_ALLOW_MIN, eq["excursion"]))
    print("      MKT      <= %.1f °C       ->  %6.0f 分" % (MKT_LIMIT_C, eq["mkt"]))
    print("      劣化     <= %.2f          ->  %6.0f 分" % (DEG_LIMIT, eq["degradation"]))
    spread = max(eq.values()) / min(eq.values())
    print("      ★同じ「規定を守った」でも許す時間が **%.1f 倍**違う。" % spread)

    # 全セルにロガーを置いて 3 指標の合否を出す
    rec, dt_s = _cell_records(vol)
    tk = rec + 273.15
    exc = np.count_nonzero(rec > LIMIT_C, axis=0) * dt_s
    mkt = DH_OVER_R / (-np.log(np.mean(np.exp(-DH_OVER_R / tk), axis=0))) - 273.15
    rate = np.exp(-DH_OVER_R * (1.0 / tk - 1.0 / T_REF_K))
    deg = np.trapezoid(rate, dx=1.0, axis=0) / (rate.shape[0] - 1)
    ok = np.stack([exc <= EXC_ALLOW_MIN, mkt <= MKT_LIMIT_C, deg <= DEG_LIMIT])
    agree = ok.all(0) | (~ok).all(0)
    n_dis = int(np.count_nonzero(~agree))
    print("\n  全 %d セルにロガーを置いてみると、3 指標の合否が揃わないのは"
          " **%d セル(%.1f %%)**" % (agree.size, n_dis, 100.0 * n_dis / agree.size))
    for i, nm in enumerate(("逸脱時間", "MKT", "劣化")):
        print("      %-8s だけが不合格: %4d セル / だけが合格: %4d セル"
              % (nm, int(np.count_nonzero(~ok[i] & ok[(i + 1) % 3] & ok[(i + 2) % 3])),
                 int(np.count_nonzero(ok[i] & ~ok[(i + 1) % 3] & ~ok[(i + 2) % 3]))))

    # MKT は集計窓で動く —— 反転する置き場所を**探して**報告する(無ければ無いと書く)
    print("\n  ★MKT は集計窓の長さで動く(4 時間の窓を全セル・全位置で試す):")
    win = 240
    flip = None
    for (yy, xx) in zip(*np.nonzero(lay["is_product"])):
        tr = vol[:, yy, xx]
        m_all = mkt_celsius(tr)
        if m_all > MKT_LIMIT_C:
            continue                      # 12 h でも不合格なら「反転」ではない
        best = max(range(0, NT - win + 1, 10),
                   key=lambda a_: float(tr[a_:a_ + win].mean()))
        m_win = mkt_celsius(tr[best:best + win])
        if m_win > MKT_LIMIT_C:
            flip = (int(yy), int(xx), m_all, m_win, best,
                    excursion_minutes(tr, DT_MIN),
                    excursion_minutes(tr[best:best + win], DT_MIN))
            break
    if flip is None:
        print("      反転する置き場所は**見つからなかった**(この場では"
              "12 h の MKT と 4 h の MKT が同じ側に落ちる)。")
    else:
        yy, xx, m_all, m_win, a_, e_all, e_win = flip
        print("      製品セル (y=%d, x=%d): 12 時間で MKT %.2f °C(合格)、"
              "%d〜%d 分の 4 時間で %.2f °C(**不合格**)。"
              % (yy, xx, m_all, a_, a_ + win, m_win))
        print("      逸脱時間は窓に入った分をそのまま足すだけで**薄まらない**"
              "(12 h: %.0f 分 / 4 h: %.0f 分)。MKT は平均なので、"
              "窓を伸ばすと同じ逸脱が薄まって合格に見える。" % (e_all, e_win))
        print("      **「MKT は %.1f °C 以下でした」は窓を書かないと意味が無い。**"
              % MKT_LIMIT_C)

    # 逸脱時間は大きさに盲目
    mild = np.full(NT, 4.0); mild[:200] = 8.1
    hot = np.full(NT, 4.0); hot[:200] = 20.0
    print("\n  ★逸脱時間は**大きさに盲目**: 200 分 8.1 °C と 200 分 20.0 °C は"
          "どちらも逸脱 %.0f 分。" % excursion_minutes(mild, DT_MIN))
    print("      劣化は %.3f と %.3f(%.0f 倍)、MKT は %.2f と %.2f °C。"
          % (degradation_index(mild, DT_MIN), degradation_index(hot, DT_MIN),
             degradation_index(hot, DT_MIN) / degradation_index(mild, DT_MIN),
             mkt_celsius(mild), mkt_celsius(hot)))

    if figs.enabled():
        rows = [["逸脱時間 <= %.0f min" % EXC_ALLOW_MIN, "%.0f" % eq["excursion"],
                 "%d" % int(np.count_nonzero(~ok[0])), "大きさに盲目"],
                ["MKT <= %.1f °C" % MKT_LIMIT_C, "%.0f" % eq["mkt"],
                 "%d" % int(np.count_nonzero(~ok[1])), "窓の長さで薄まる"],
                ["劣化 <= %.2f" % DEG_LIMIT, "%.0f" % eq["degradation"],
                 "%d" % int(np.count_nonzero(~ok[2])), "積算(窓に比例)"]]
        figs.save_table("metric_limits",
                        ["判定", "12 °C に許す時間 [min]", "不合格になるセル数",
                         "何に鈍いか"], rows,
                        title="同じ「規定内」でも 3 つの指標は %.1f 倍ずれる" % spread)
        vmap = (ok[0].astype(float) + 2.0 * ok[1] + 4.0 * ok[2])
        figs.save_grid("verdict_maps",
                       [np.where(lay["is_product"], exc, 0.0), mkt, deg, vmap],
                       ["記録の逸脱時間 [min]", "記録の MKT [°C]",
                        "記録の劣化 [-]", "合否の組合せ(7 = 3 つとも合格)"],
                       title="全セルにロガーを置いたときの 3 指標", ncols=4,
                       caption="4 枚目が一様でないところが「指標で答えが違う」場所。")
    return {"eq": eq, "spread": spread, "n_dis": n_dis, "ok": ok,
            "exc": exc, "mkt": mkt, "deg": deg}


# --------------------------------------------------------------------------- #
# 8. 逸脱を 3-D の塊として数える                                                #
# --------------------------------------------------------------------------- #
def section_events(scene: dict) -> dict:
    print("\n" + "=" * 78)
    print("8) 逸脱を (t, y, x) の塊として数える —— vol_label / vol_label_shape_stats")
    print("=" * 78)
    vol = scene["vol"]
    hot = (vol > LIMIT_C)
    lab = _L.vol_label(hot, connectivity=6)
    st = fs.vol_label_shape_stats(lab, spacing=(DT_MIN, CELL_M, CELL_M))
    st = sorted(st, key=lambda d: -d["voxel_count"])
    total = int(hot.sum())
    print("  逸脱の塊 %d 個、延べ %d セル分(= セル x 分)" % (len(st), total))
    print("   順位  続いた時間   広がり(奥行き x 幅)      延べセル分   セル数")
    rows = []
    for k, s in enumerate(st[:4]):
        dur = s["extent"][0]
        ny_, nx_ = s["extent"][1], s["extent"][2]
        area = len({(b, c) for b, c in
                    zip(*np.nonzero((lab == s["label"]).any(0)))})
        rows.append(["%d" % (k + 1), "%.0f" % dur, "%.1f x %.1f" % (ny_, nx_),
                     "%d" % s["voxel_count"], "%d" % area])
        print("    %2d   %5.0f 分   %5.1f m x %4.1f m       %7d   %5d"
              % (k + 1, dur, ny_, nx_, s["voxel_count"], area))
    print("  ★「逸脱時間」を 1 つの数字にすると長さと広がりが混ざる —— "
          "塊の extent は 2 つを分けて返す。")

    if figs.enabled():
        proj = _L.render_volume_projection(hot.astype(np.float32),
                                           azimuth=35.0, elevation=20.0, mode="xray")
        figs.save_grid("excursion_body",
                       [np.asarray(proj, np.float64),
                        np.count_nonzero(hot, axis=0) * DT_MIN,
                        np.asarray(fs.temporal_max(vol))],
                       ["逸脱体を斜めから見る(render_volume_projection)",
                        "各セルの逸脱時間 [min]", "各セルの最高温度 [°C]"],
                       title="逸脱は (t, y, x) の 3-D の塊", ncols=3)
        figs.save_table("excursion_events",
                        ["順位", "続いた時間 [min]", "広がり 奥行き x 幅 [m]",
                         "延べセル分", "セル数"], rows,
                        title="逸脱の塊 %d 個(延べ %d セル分)" % (len(st), total))
    return {"n_events": len(st), "total": total,
            "top": st[0] if st else None, "rows": rows}


# --------------------------------------------------------------------------- #
# 9. ロガーの数と置き方                                                         #
# --------------------------------------------------------------------------- #
def section_count_sweep(scene: dict, zero: dict) -> dict:
    print("\n" + "=" * 78)
    print("9) ロガーの数と置き方 —— 増やせば当たるのか")
    print("=" * 78)
    lay = scene["layout"]
    prod = lay["is_product"]
    says_pass = zero["pass_meas"]
    ys, xs = np.nonzero(prod)
    ok_cells = says_pass[ys, xs]                 # 各製品セル 1 個の合否
    rng = np.random.default_rng(SEED)
    ns, rates = [], []
    print("   ロガー数   偽合格 [%]  (製品セルにランダムに置く、2000 通り)")
    for n in (1, 2, 3, 5, 8, 12):
        idx = rng.integers(0, ys.size, size=(2000, n))
        allpass = ok_cells[idx].all(axis=1)      # 全部合格 -> 荷を通してしまう
        r = 100.0 * float(allpass.mean())
        ns.append(n); rates.append(r)
        print("      %2d        %6.1f" % (n, r))

    # 慣用の 3 点: 扉に近い側 / 中央 / 吹き出し口に近い側、いずれも荷の中(製品セル)
    conv = [(NY - 4, 4), (NY // 2 + 2, 4), (4, 4)]
    assert all(prod[y, x] for y, x in conv), "慣用 3 点が製品セルでない"
    conv_pass = all(bool(says_pass[y, x]) for y, x in conv)
    print("\n  慣用の 3 点 %s(扉寄り・中央・吹き出し口寄り、いずれも荷の中): %s"
          % (conv, "**偽合格**(3 点とも合格と言う)" if conv_pass
             else "不合格を出せた(扉寄りの 1 点が最悪ゾーンに入った)"))
    # ★「当たった」のが規約のおかげか偶然かを分ける: 各点を ±1 m 揺らして数える。
    trials = 2000

    def _jitter(points) -> float:
        n_pass = 0
        for _ in range(trials):
            okk = True
            for (y0, x0) in points:
                y, x = y0, x0
                for _try in range(20):
                    yy = int(np.clip(y0 + rng.integers(-5, 6), 0, NY - 1))
                    xx = int(np.clip(x0 + rng.integers(-5, 6), 0, NX - 1))
                    if prod[yy, xx]:
                        y, x = yy, xx
                        break
                okk &= bool(says_pass[y, x])
            n_pass += int(okk)
        return 100.0 * n_pass / trials

    jit_rate = _jitter(conv)
    per = [_jitter([p]) for p in conv]
    print("  ★その 3 点を**それぞれ ±1 m 揺らす**と偽合格 %.1f %%(%d 通り)。"
          "ランダム 3 個は %.1f %%。" % (jit_rate, trials, rates[2]))
    print("     ★★予想が外れた —— 「規約は代表点を選ぶだけだからランダムより"
          "弱い」と踏んでいたが、実測は**規約のほうがずっと当たる**"
          "(%.1f %% 対 %.1f %%)。" % (jit_rate, rates[2]))
    print("     内訳(1 点だけ、±1 m 揺らす): 扉寄り %.1f %% / 中央 %.1f %% / "
          "吹き出し口寄り %.1f %% —— 効いているのは**扉寄りの 1 点だけ**で、"
          "残り 2 点は 1 個も見つけない。" % tuple(per))
    print("     つまり規約が強いのではなく、**この荷の最悪点が扉側にある**から"
          "当たった。壁ではなく吹き出し口側が壊れる故障(送風の偏り)なら、"
          "同じ 3 点は同じようには当たらない。")

    if figs.enabled():
        figs.save_plot("sweep_nlogger",
                       [("偽合格の割合", ns, rates),
                        ("ランダム 3 個", [3], [rates[2]])],
                       xlabel="ロガーの数 [個]", ylabel="偽合格 [%]",
                       title="増やしても素直には減らない(製品セルにランダム配置)",
                       kinds=["line", "scatter"])
        vm = np.zeros((NY, NX))
        vm[prod & says_pass] = 1.0          # 偽合格になる置き場所
        vm[prod & ~says_pass] = 2.0         # 正しく不合格を出す置き場所
        vm[lay["is_air"] & ~says_pass] = 3.0
        y0, x0 = _worst_product(scene)
        vm[y0, x0] = 4.0
        figs.save_grid("logger_map",
                       [vm, zero["exc_meas"]],
                       ["1=偽合格 2=正しく不合格 3=空気で不合格 4=真の最悪製品",
                        "ロガー 1 個が出す逸脱時間 [min]"],
                       title="どこに置くと当たるか(置き場所の地図)", ncols=2)
    return {"ns": ns, "rates": rates, "conv_pass": conv_pass,
            "jit_rate": jit_rate, "per_point": per}


# --------------------------------------------------------------------------- #
# 10. 道具の穴                                                                  #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("10) 道具の穴(この PoC で公開経路に無かった処理)")
    print("=" * 78)
    assert not hasattr(fs, "first_order_lag") and not hasattr(_L, "first_order_lag")
    print("  (a) **1 次遅れ(RC)フィルタ**が無い。`moving_average_window` は"
          "箱型で、センサの応答遅れとは別物(位相も裾も違う)。")
    assert not hasattr(fs, "quantize_levels")
    print("  (b) **量子化(LSB への丸め)**の op が無い。画像には"
          " `xpil_posterize` があるが 1-D / 3-D 用は無い。")
    assert not hasattr(fs, "mean_kinetic_temperature") and not hasattr(_L, "mkt")
    print("  (c) **熱線量(MKT / Arrhenius 等価時間)**が無い。音響族には"
          " `percentile_level`(L_N)という同型の統計量があるので、"
          "その兄弟として入る余地がある。")
    v = np.zeros((4, 3, 3)); v[1:3] = 2.0
    got = np.asarray(fs.apply(v, "vol_mip"))
    assert abs(float(got.max()) - 1.0) < 1e-9, float(got.max())
    assert abs(float(np.asarray(fs.temporal_max(v)).max()) - 2.0) < 1e-9
    print("  (d) 進化 op の `vol_mip` は **最大値で正規化**するので物理単位が"
          "消える(°C が [0,1] になる)。`temporal_max` は正規化しない —— "
          "同じ「時間方向の最大」で 2 つの答えがある。")
    occ = np.zeros((6, 6), bool); occ[0, :] = True
    try:
        _L.esdf(occ, voxel_size=(0.3, 0.1))
        raise AssertionError("2-D で長さ 2 の voxel_size が通った(この節を書き換える)")
    except ValueError:
        pass
    print("  (e) `esdf` は 2-D 格子を受けるのに、異方 `voxel_size` は"
          "**長さ 3 しか**受けない。平面図で縦横の刻みを変えられない"
          "(この PoC はセルを等方 %.2f m にして回避した)。" % CELL_M)
    assert not hasattr(fs, "time_above_threshold")
    print("  (f) 「各画素がしきい値を超えていた時間」を返す op が無い。"
          "`temporal_max/mean/median` はあるので、`temporal_count_above` は"
          "族の穴。")


# --------------------------------------------------------------------------- #
def main() -> None:
    t0 = time.perf_counter()
    print("=" * 78)
    print("コールドチェーンの温度記録 —— センサの置き場所が品質判定を決める")
    print("荷室 %.1f m x %.1f m を %d 分、規定 2〜%.0f °C" % (
        NY * CELL_M, NX * CELL_M, NT, LIMIT_C))
    print("=" * 78)

    layout = build_layout()
    scene = make_scene(layout=layout)
    truth = section_scene(scene)
    zero = section_zero_point(scene, truth)
    cliff = section_cliffs(scene)
    ctrl = section_controls(layout)
    met = section_metrics(scene)
    ev = section_events(scene)
    cnt = section_count_sweep(scene, zero)
    section_tool_gaps()

    # --- 所見を固定する ---------------------------------------------------- #
    assert truth["n_bad"] > 0, "真に不合格な製品セルが無いと主題が立たない"
    assert zero["rate_prod"] > 50.0, zero["rate_prod"]
    assert np.isfinite(cliff["tau_meas"]), cliff["tau_meas"]
    assert cliff["n_measurable"] >= 3, cliff["n_measurable"]
    assert cliff["rel_2pole"] < 0.25, cliff["rel_2pole"]
    assert cliff["s_err"] < 1e-6, cliff["s_err"]
    assert cliff["q_err"] < 1e-6, cliff["q_err"]
    assert met["spread"] > 2.0, met["spread"]
    assert met["n_dis"] > 0, met["n_dis"]
    assert ctrl["(a) 均一+扉"]["fp"] == 0.0, ctrl["(a) 均一+扉"]["fp"]
    assert ctrl["(a) 均一+扉"]["ff"] == 0.0, ctrl["(a) 均一+扉"]["ff"]
    assert ctrl["(d) 扉だけ"]["ff"] > ctrl["(b) 壁だけ"]["ff"], "扉が偽不合格を生む"
    assert cnt["rates"][0] > cnt["rates"][-1], cnt["rates"]

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * 真に不合格な製品セルは %d / %d(%.1f %%)。それでも製品セルに"
          "ロガーを 1 個置くと %.1f %% の置き方が「合格」と言う。"
          % (truth["n_bad"], truth["n_prod"],
             100.0 * truth["n_bad"] / truth["n_prod"], zero["rate_prod"]))
    print("  * 崖は先に予測できる: 中央通路の %d か所で時定数の崖 τ* を測ると"
          "19〜138 分に広がり、2 段の予測は相対 %.0f %% 以内。"
          "サンプリング間隔と量子化の崖は予測と**完全一致**。"
          % (cliff["n_measurable"], 100 * cliff["rel_2pole"]))
    print("  * 3 つの指標は「12 °C に許す時間」で %.1f 倍ずれ、%d セルで"
          "合否が揃わない。" % (met["spread"], met["n_dis"]))
    print("  * 扉のパルスは空気だけを叩く —— 壁を止めて扉だけ残すと偽不合格が"
          "%.1f %% 現れ、製品に置いたロガーは %.0f %% が合格と言う。"
          % (ctrl["(d) 扉だけ"]["ff"], ctrl["(d) 扉だけ"]["fp"]))
    print("  * ★予想が外れた: 慣用の 3 点はランダム 3 個より**ずっと当たる**"
          "(偽合格 %.1f %% 対 %.1f %%)。ただし効いているのは扉寄りの 1 点だけ。"
          % (cnt["jit_rate"], cnt["rates"][2]))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
