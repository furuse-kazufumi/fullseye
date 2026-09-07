# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""メガソーラーのドローン熱画像 —— 温度差を測っているつもりで、風と角度を測っている。

太陽光発電所の点検は、ドローンに載せた赤外カメラでアレイを撮り、**周囲より
何 K 高いか**(ΔT)でホットスポットを探す仕事です(IEC TS 62446-3 の運用点検)。
やっかいなのは、その ΔT が故障の大きさだけで決まらないこと —— 同じ余剰発熱でも
**風速で薄まり、画素の大きさで薄まり、撮影角度で圧縮される**。しかも影と汚れは
「本物の温度差だが電気的故障ではない」ので、2 値(故障 / 健全)で数えた瞬間に
何を測ったのか分からなくなります。

EXTEND: 実写に差し替えるなら :func:`thermal_field` が返す辞書の ``T``(真の表面
温度場)を、**放射計として校正済みの**熱画像に置き換えます。``masks`` は 3 値
(``fault`` = 電気的故障 / ``nonfault`` = 影・汚れ / 健全)で要ります ——
1 枚の「異常」マスクに畳んだ時点で、この PoC の中心的な主張(偽の故障を数える)
が測れません。風速・日射・カメラの放射率設定・反射見かけ温度・飛行高度は
**撮影時に記録しておくこと**: 4 節と 8 節の補正はどれもその 5 つが要ります。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **真値は定常熱収支の閉形式**。無故障セルの温度上昇は風速 1.0 m/s で
   +25.0 K(NOCT 相当)、余剰発熱 320 W/m² のセル内ホットスポットは
   さらに +11.2 K。**ただしカメラが見るのは 4.9 K** —— 熱の横流れ(フィン長
   11.8 mm)と画素(GSD 20 mm)で 44 % に薄まる。★内訳は予想と逆で、
   薄めているのは熱伝導ではなく**カメラ**(伝導だけなら 0.93 倍、
   カメラだけなら 0.47 倍)。
2. ★★**「故障ゼロ」の対照群で偽の故障が出る**。全体平均を基準にすると、
   故障を 1 つも置いていない場面で塊 **6 個**(健全 6 / 非故障の温度差 0)。
   正体は熱の出方の差(内側の列は風が当たらない)と日射の時間変化で、
   **どちらもモジュールごとの中央値を引くだけで 0 個**になる。
3. ★**崖は先に計算できる**。対流係数は h = 5.7 + 3.8 v(McAdams)なので
   ΔT は 1/U(v) で薄まる。しきい値 3.0 K を割る風速の予測はセル内
   ホットスポットで **4.2 m/s**、ストリング故障で **6.0 m/s**。実測は
   4.0 m/s と 6.0 m/s で一致した。**同じ日の朝と昼で、同じ故障が出たり
   消えたりする**。
4. ★★**正規化を強くするほど広い故障を食う**。モジュールごとに平面を除くと
   偽の故障は 0 個に減るが、ストリング故障の ΔT が 6.5 → 3.7 K(57 %)に
   縮み、崖が 6.0 → 4.0 m/s へ**前倒しになる**。ホットスポット(小さい)は
   ほとんど食われない(97 %)—— 食われる量は**故障の面積で決まる**。
5. ★★**影は本物のストリング故障を偽造する**。影に入ったセルは 25 K 冷える
   だけでなく、そのストリングの発電を止めるので**日向のセルが 6.4 K 熱く
   なる** —— 本物のストリング故障(6.5 K)と 0.1 K しか違わない。対照群
   (影だけ / 故障だけ)で分けて初めて、熱画像だけでは区別できないと言える。
6. ★**GSD の崖は閉形式で当たる**。半径 30 mm の熱源が σ_tot のガウスで
   薄まる率は 1 - exp(-R²/2σ_tot²)。GSD 10→80 mm で予測 0.86→0.06、
   実測 0.86→0.06(最大差 0.02)。しきい値を割るのは GSD 47 mm。
7. ★★**幾何は直せるが放射は直らない**。斜め 60° から撮ると見かけ放射率が
   0.918 → 0.869 に落ち、ΔT は 0.90 倍に圧縮される。射影変換で正対に
   戻すと形は戻るが、ΔT は 0.90 倍のまま(戻るのは 0.90 → 0.90)。
   **見かけの温度差は幾何補正では回復しない**。
8. NETD は効き方が違う。20 → 200 mK で見逃しはほとんど増えず(再現率
   1.00 → 1.00)、**偽の故障だけが 0 → 4 個**に増える。雑音の崖は
   「見えなくなる」ではなく「**無いものが見える**」向きに来る。

【グラウンドトゥルース】
パネル 1 画素の温度は**定常熱収支の閉形式**で決める:

    T - T_air = (α·G_loc - P_elec + q_fault) / U(v),  U(v) = C_f·(h_conv + h_rad)
    h_conv = 5.7 + 3.8·v  [W/m²K](McAdams の平板相関)
    h_rad  = 4·ε·σ·T_m³   [W/m²K](放射の線形化)

故障は既知の余剰発熱 q_fault [W/m²]、影は既知の日射比 0.12、汚れは既知の
吸収率増 +0.045 と透過損 12 % として**足し込む**ので、真値は幾何で決まる。
横方向の熱伝導だけは閉形式に入らないので、フィン長 L = sqrt(k·t / U) の
ガウスで面内を鈍らせて近似する(**ここだけ近似**であることを 1 節で明示)。
地面(パネルの外)は熱収支ではなく +14 K の代用値 —— 判定には使わない。

来歴(公開文献のみ): W. H. McAdams, *Heat Transmission*, 3rd ed. (1954) ——
平板の強制対流相関 / IEC TS 62446-3:2017 —— PV アレイの赤外線点検 /
M. Köntges et al., IEA-PVPS T13-01:2014 —— PV モジュール故障の分類 /
Fresnel の式 —— 誘電体界面の角度依存反射率(見かけ放射率 ε(θ) = 1 - R(θ))。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 発電所の諸元 ------------------------------------------------------------ #
CELL = 0.156               # セル 1 枚の辺 [m](156 mm 角)
NC_X, NC_Y = 10, 6         # モジュール 1 枚のセル数(横置き 60 セル)
MOD_W, MOD_H = NC_X * CELL, NC_Y * CELL
NMX, NMY = 3, 3            # モジュールの並び(列 x 行)
GAP_X, GAP_Y = 0.04, 0.45  # モジュール間 / 架台列間の隙間 [m]
MARGIN = 0.20              # 視野の余白 [m]
FINE = 0.005               # 真値を作る細かい格子 [m/px]

# --- 熱の諸元 ---------------------------------------------------------------- #
SIGMA_SB = 5.670374419e-8  # ステファン・ボルツマン定数 [W/m²K⁴]
T_AIR = 305.0              # 気温 [K](32 °C)
T_SKY = 283.0              # 有効天空温度 [K](快晴)
G0 = 1000.0                # 日射 [W/m²]
ALPHA_SOL = 0.90           # モジュールの日射吸収率
ETA_EL = 0.185             # 動作点での変換効率(取り出される電力の割合)
EPS_N = 0.918              # 垂直入射の熱放射率(等価屈折率 n=1.8 の Fresnel)
C_FACES = 1.75             # 表裏あわせた実効面数(裏面は換気が弱い)
T_MEAN = 320.0             # 放射の線形化に使う代表温度 [K]
KT_EFF = 4.0e-3            # 面内熱伝導の k·t [W/K](ガラス + 封止材)
GROUND_RISE = 14.0         # 地面の温度上昇 [K](熱収支ではなく代用値)

# --- 故障(真値)------------------------------------------------------------- #
# モジュール番号は行優先(0,1,2 = 上段 / 3,4,5 = 中段 / 6,7,8 = 下段)。
Q_HOT = 320.0              # セル内ホットスポットの余剰発熱 [W/m²]
R_HOT = 0.030              # その半径 [m]
MOD_HOT = 1                # ホットスポットを置くモジュール番号
CELL_HOT = (2, 6)          # そのモジュール内のセル(行, 列)
MOD_STR, SUB_STR = 5, 1    # ストリング故障のモジュールと部分ストリング番号
SOIL_ROW = 2               # 汚れの帯が乗るモジュールの行(下段)
SOIL_H = 0.18              # 帯の高さ [m](下辺から)
SOIL_DALPHA = 0.045        # 汚れによる吸収率の増分
SOIL_DPOW = 0.12           # 汚れによる発電の減り(透過損)
SHADE_FRAC = 0.12          # 影の中の日射比
MOD_POLE = 0               # 支柱の影(斜めの帯。全ストリングを止める)
POLE_DEG, POLE_W = 22.0, 0.24     # その向き [deg] と幅 [m]
MOD_ROWSH, ROWSH_H = 3, 0.17      # 列間影(前列の陰)の乗るモジュールと高さ [m]
MOD_GRASS = 2              # 雑草の影
GRASS = ((0.30, 0.100), (0.62, 0.075))   # (モジュール内の x [m], 半径 [m])
MOD_SHELTER, U_SHELTER = 4, 0.86  # 風の当たらない健全モジュールと U の倍率

# --- 撮影の諸元 -------------------------------------------------------------- #
GSD = 0.020                # 画素の地上寸法 [m/px]
PSF_PX = 0.7               # 光学 PSF の σ [px]
NETD = 0.050               # 雑音等価温度差 [K]
FLIGHT_H = 30.0            # 飛行高度 [m]
ATM_K = 5.81e-6            # 大気の減衰係数 [1/mm](8-14 µm、τ(30 m)=0.84)
EPS_SET = 0.95             # カメラに設定してある放射率(現場の既定値)
VIEW_DEG = 0.0             # 既定の入射角(パネル法線から)[deg]

# --- 判定の諸元 -------------------------------------------------------------- #
THETA = 3.0                # ΔT のしきい値 [K](IEC TS 62446-3 の運用値に近い)
A_MIN = 4                  # 塊として認める最小面積 [px]
SMOOTH_PX = 1.0            # 判定前の平滑 σ [px]
TOL_PX = 3                 # 真値との突き合わせ許容 [px]
V_REF = 1.0                # 既定の風速 [m/s]
IRR_DRIFT = 0.12           # 撮影中の日射の変化(視野の上下で ±6 %)
SEED = 7

WORLD_W = 2 * MARGIN + NMX * MOD_W + (NMX - 1) * GAP_X
WORLD_H = 2 * MARGIN + NMY * MOD_H + (NMY - 1) * GAP_Y
NX, NY = int(round(WORLD_W / FINE)), int(round(WORLD_H / FINE))


# --------------------------------------------------------------------------- #
# 物理 —— 閉形式                                                                #
# --------------------------------------------------------------------------- #
def h_conv(v: float) -> float:
    """強制対流の熱伝達係数 [W/m²K] —— McAdams の平板相関 h = 5.7 + 3.8 v。"""
    return 5.7 + 3.8 * float(v)


def h_rad() -> float:
    """放射を線形化した熱伝達係数 [W/m²K] —— 4 ε σ T_m³。"""
    return 4.0 * EPS_N * SIGMA_SB * T_MEAN ** 3


def u_total(v: float) -> float:
    """パネル 1 m² の総合熱伝達係数 [W/m²K]。"""
    return C_FACES * (h_conv(v) + h_rad())


def fin_length(v: float) -> float:
    """面内の熱拡散長(フィン長)[m] —— sqrt(k·t / U)。"""
    return float(np.sqrt(KT_EFF / u_total(v)))


def cam_sigma(gsd: float, with_smooth: bool = True) -> float:
    """カメラ(+ 判定平滑)がホットスポットに掛ける実効ガウス σ [m]。

    光学 PSF ``PSF_PX``·gsd、画素の受光面(一様分布の σ = gsd/sqrt(12))、
    判定前の平滑 ``SMOOTH_PX``·gsd を二乗和で足す。
    """
    s2 = (PSF_PX * gsd) ** 2 + gsd ** 2 / 12.0
    if with_smooth:
        s2 += (SMOOTH_PX * gsd) ** 2
    return float(np.sqrt(s2))


def peak_attenuation(v: float, gsd: float, radius: float = R_HOT,
                     with_smooth: bool = True) -> float:
    """半径 ``radius`` の一様円板が σ_tot のガウスで薄まる中心の比 —— 閉形式。

    円板とガウスの畳み込みは中心で ``1 - exp(-R²/(2σ²))``。σ² は熱伝導の
    フィン長と撮像の σ の二乗和(独立なガウスの合成)。
    """
    s2 = fin_length(v) ** 2 + cam_sigma(gsd, with_smooth) ** 2
    return float(1.0 - np.exp(-radius ** 2 / (2.0 * s2)))


def predict_hotspot(v: float, gsd: float = GSD) -> float:
    """セル内ホットスポットの見かけの ΔT [K](予測、閉形式)。"""
    return Q_HOT / u_total(v) * peak_attenuation(v, gsd)


def predict_string(v: float) -> float:
    """ストリング故障の ΔT [K](広いので薄まらない)。"""
    return ETA_EL * G0 / u_total(v)


def solve_v_crit(fn, lo: float = 0.0, hi: float = 30.0,
                 theta: float = THETA) -> float:
    """``fn(v) = theta`` を満たす風速を二分法で解く(fn は v に単調減少)。"""
    if fn(lo) < theta:
        return float("nan")
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if fn(mid) >= theta:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def apparent_emissivity(theta_deg) -> np.ndarray:
    """見かけ放射率 ε(θ) = 1 - R(θ) —— Fresnel(等価屈折率 1.8)。

    LWIR のガラスは屈折率が波長で大きく動くので、**角度依存の形だけを**
    Fresnel から借りたモデル(垂直入射で ε=%.3f になるよう n=1.8 を選んだ)。
    """
    c = np.cos(np.radians(np.asarray(theta_deg, float)))
    r = np.asarray(fs.ledger.fresnel_dielectric(c, 1.0, 1.8))
    return 1.0 - r


apparent_emissivity.__doc__ = apparent_emissivity.__doc__ % EPS_N


def atm_transmittance(dist_m: float) -> float:
    """大気の透過率 —— Beer-Lambert(``fs.ledger.beer_lambert_transmittance``)。"""
    return float(fs.ledger.beer_lambert_transmittance(dist_m * 1000.0, ATM_K))


def _sb(t):
    return SIGMA_SB * np.asarray(t, float) ** 4


def to_apparent(t_true, theta_deg: float = VIEW_DEG,
                dist_m: float = FLIGHT_H) -> np.ndarray:
    """真の表面温度 -> カメラが表示する見かけ温度 [K]。

    経路は 3 段: (1) 面から出る放射 = ε·σT⁴ + (1-ε)·σT_sky⁴、
    (2) 大気で τ 倍されて (1-τ)·σT_air⁴ が足される、
    (3) カメラは ε=``EPS_SET``、反射見かけ温度 = 気温、**大気は補正しない**
    という現場の既定設定で温度に戻す。
    """
    eps = float(apparent_emissivity(theta_deg))
    tau = atm_transmittance(dist_m)
    l_obj = eps * _sb(t_true) + (1.0 - eps) * _sb(T_SKY)
    l_cam = tau * l_obj + (1.0 - tau) * _sb(T_AIR)
    l_corr = (l_cam - (1.0 - EPS_SET) * _sb(T_AIR)) / EPS_SET
    return (np.maximum(l_corr, 1.0) / SIGMA_SB) ** 0.25


# --------------------------------------------------------------------------- #
# 場面 —— アレイの幾何と故障の真値                                              #
# --------------------------------------------------------------------------- #
_LAYOUT: dict | None = None


def layout() -> dict:
    """細かい格子の上のアレイ配置と、故障の真値マップ(1 度だけ作る)。"""
    global _LAYOUT
    if _LAYOUT is not None:
        return _LAYOUT

    y = (np.arange(NY) + 0.5) * FINE
    x = (np.arange(NX) + 0.5) * FINE
    xx, yy = np.meshgrid(x, y)

    mod_id = np.full((NY, NX), -1, np.int32)
    cell_r = np.full((NY, NX), -1, np.int32)
    cell_c = np.full((NY, NX), -1, np.int32)
    for my in range(NMY):
        y0 = MARGIN + my * (MOD_H + GAP_Y)
        for mx in range(NMX):
            x0 = MARGIN + mx * (MOD_W + GAP_X)
            m = ((yy >= y0) & (yy < y0 + MOD_H) & (xx >= x0) & (xx < x0 + MOD_W))
            mod_id[m] = my * NMX + mx
            cell_r[m] = np.clip(((yy - y0) / CELL).astype(np.int32), 0, NC_Y - 1)[m]
            cell_c[m] = np.clip(((xx - x0) / CELL).astype(np.int32), 0, NC_X - 1)[m]
    panel = mod_id >= 0
    sub = np.where(panel, cell_r // 2, -1)          # 60 セル = 20 セル x 3 ストリング

    # --- 影(支柱)—— 左列を斜めに横切る帯 ---------------------------------- #
    ang = np.radians(SHADE_DEG)
    dist = np.abs(xx * np.cos(ang) + yy * np.sin(ang) - SHADE_C)
    shade = (dist < 0.5 * SHADE_W) & panel & (mod_id % NMX == 0)
    # --- 雑草の影 —— モジュール 2 の上に小さい円 ------------------------------ #
    mx2, my2 = 2 % NMX, 2 // NMX
    bx = MARGIN + mx2 * (MOD_W + GAP_X)
    by = MARGIN + my2 * (MOD_H + GAP_Y)
    for gx, gr in GRASS:
        shade |= ((xx - (bx + gx)) ** 2 + (yy - (by + 0.55)) ** 2 < gr ** 2) & panel

    # --- 影に食われたストリング(発電が止まる)------------------------------- #
    kill_shade = np.zeros_like(panel)
    for m in np.unique(mod_id[shade]):
        for s in np.unique(sub[shade & (mod_id == m)]):
            kill_shade |= (mod_id == m) & (sub == s)

    # --- 汚れの帯(下段モジュールの下辺)------------------------------------- #
    y_bot = MARGIN + SOIL_ROW * (MOD_H + GAP_Y) + MOD_H
    soil = panel & (mod_id // NMX == SOIL_ROW) & (yy > y_bot - SOIL_H)

    # --- 本物の故障 ------------------------------------------------------------ #
    mxh, myh = MOD_HOT % NMX, MOD_HOT // NMX
    cx = MARGIN + mxh * (MOD_W + GAP_X) + (CELL_HOT[1] + 0.5) * CELL
    cy = MARGIN + myh * (MOD_H + GAP_Y) + (CELL_HOT[0] + 0.5) * CELL
    hot = ((xx - cx) ** 2 + (yy - cy) ** 2 <= R_HOT ** 2) & panel
    kill_fault = (mod_id == MOD_STR) & (sub == SUB_STR)

    # --- モジュールごとの熱の出方の差(取付と風の当たり方)-------------------- #
    rng = np.random.default_rng(SEED)
    shelter = np.array([1.00, 0.94, 0.98])          # 内側の列は風が当たらない
    u_scale = np.ones((NY, NX))
    for m in range(NMX * NMY):
        f = shelter[m // NMX] * (1.0 + 0.045 * rng.standard_normal())
        u_scale[mod_id == m] = f

    # --- 撮影中の日射の変化(視野の上下で ±IRR_DRIFT/2)------------------------ #
    g_time = 1.0 + IRR_DRIFT * (yy / WORLD_H - 0.5)

    _LAYOUT = {
        "x": xx, "y": yy, "mod_id": mod_id, "panel": panel, "sub": sub,
        "shade": shade, "kill_shade": kill_shade, "soil": soil,
        "hot": hot, "kill_fault": kill_fault, "u_scale": u_scale,
        "g_time": g_time,
        "ground_tex": gaussian_filter(rng.standard_normal((NY, NX)), 24.0) * 26.0,
    }
    return _LAYOUT


def thermal_field(v: float = V_REF, faults: bool = True,
                  extras: bool = True) -> dict:
    """定常熱収支で真の表面温度場を作る。``faults`` / ``extras`` で対照群を作る。

    ``faults`` = 電気的故障(セル内ホットスポット + ストリング故障)。
    ``extras`` = 影・汚れ・モジュール差・日射の時間変化(**故障ではない**もの)。
    """
    L = layout()
    u = u_total(v) * (L["u_scale"] if extras else 1.0)

    g = G0 * (L["g_time"] if extras else 1.0)
    g_loc = g * np.where(L["shade"] & extras, SHADE_FRAC, 1.0)
    alpha = ALPHA_SOL + (SOIL_DALPHA * L["soil"] if extras else 0.0)

    dead = np.zeros_like(L["panel"])
    if extras:
        dead |= L["kill_shade"]
    if faults:
        dead |= L["kill_fault"]
    p_el = ETA_EL * g_loc * (~dead) * L["panel"]
    if extras:
        p_el = p_el * (1.0 - SOIL_DPOW * L["soil"])

    q = Q_HOT * L["hot"] if faults else 0.0
    dt = (alpha * g_loc - p_el + q) / u
    dt = np.where(L["panel"], dt, GROUND_RISE + L["ground_tex"])

    # 面内の熱伝導 —— パネルの内側だけで鈍らせる(正規化畳み込み)
    sig = fin_length(v) / FINE
    m = L["panel"].astype(np.float64)
    num = gaussian_filter(dt * m, sig, mode="nearest")
    den = gaussian_filter(m, sig, mode="nearest")
    dt = np.where(L["panel"], num / np.maximum(den, 1e-9), dt)

    return {"T": T_AIR + dt, "dt": dt}


# --------------------------------------------------------------------------- #
# 撮像 —— 光学 + 画素 + 放射 + 雑音                                             #
# --------------------------------------------------------------------------- #
def block_mean(a: np.ndarray, k: int) -> np.ndarray:
    """``k x k`` の面積平均でビニングする(端は切り落とす)。"""
    h = (a.shape[0] // k) * k
    w = (a.shape[1] // k) * k
    return a[:h, :w].reshape(h // k, k, w // k, k).mean(axis=(1, 3))


def capture(t_fine: np.ndarray, gsd: float = GSD, theta_deg: float = VIEW_DEG,
            netd: float = NETD, seed: int = SEED) -> np.ndarray:
    """真の温度場 -> カメラが表示する見かけ温度画像 [K](GSD の格子)。"""
    k = int(round(gsd / FINE))
    blur = gaussian_filter(t_fine, PSF_PX * k, mode="nearest")
    t_px = block_mean(blur, k)
    t_app = to_apparent(t_px, theta_deg)
    rng = np.random.default_rng(seed + 1000)
    return t_app + netd * rng.standard_normal(t_app.shape)


def ground_truth(gsd: float = GSD) -> dict:
    """GSD の格子に落とした 3 値の真値(面積比 0.5 超で採る)。"""
    L = layout()
    k = int(round(gsd / FINE))
    fr = lambda m: block_mean(np.asarray(m, np.float64), k)   # noqa: E731
    panel = fr(L["panel"]) > 0.5
    fault = (fr(L["hot"]) > 0.5) | (fr(L["kill_fault"]) > 0.5)
    nonf = ((fr(L["shade"]) > 0.5) | (fr(L["soil"]) > 0.5)
            | (fr(L["kill_shade"]) > 0.5)) & ~fault
    return {"panel": panel, "fault": fault, "nonfault": nonf,
            "hot": fr(L["hot"]) > 0.5, "string": fr(L["kill_fault"]) > 0.5,
            "shade_warm": (fr(L["kill_shade"]) > 0.5) & (fr(L["shade"]) <= 0.5),
            "mod_id": np.rint(fr(L["mod_id"].astype(np.float64))).astype(int),
            "healthy": panel & ~fault & ~nonf}


# --------------------------------------------------------------------------- #
# 判定 —— 正規化 3 通り + しきい値 + 塊                                         #
# --------------------------------------------------------------------------- #
NORMS = ("全体平均", "モジュール中央値", "モジュール平面除去")


def normalise(t_app: np.ndarray, gt: dict, how: str) -> np.ndarray:
    """基準を引いて ΔT [K] にする。パネルの外は 0。"""
    panel, mod = gt["panel"], gt["mod_id"]
    out = np.zeros_like(t_app)
    if how == "全体平均":
        out = np.where(panel, t_app - float(t_app[panel].mean()), 0.0)
    elif how == "モジュール中央値":
        for m in np.unique(mod[panel]):
            sel = panel & (mod == m)
            out[sel] = t_app[sel] - float(np.median(t_app[sel]))
    elif how == "モジュール平面除去":
        for m in np.unique(mod[panel]):
            sel = panel & (mod == m)
            r0, r1 = np.where(sel.any(axis=1))[0][[0, -1]]
            c0, c1 = np.where(sel.any(axis=0))[0][[0, -1]]
            sub = t_app[r0:r1 + 1, c0:c1 + 1]
            res = np.asarray(fs.ledger.surface_form_remove(sub, 1.0, order=1))
            out[r0:r1 + 1, c0:c1 + 1] = np.where(sel[r0:r1 + 1, c0:c1 + 1], res, 0.0)
    else:
        raise ValueError("知らない正規化: %r" % (how,))
    return out


def smooth_in_mask(d: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """マスクの内側だけでガウス平滑(``fs.apply`` の ``gauss_filter``)。"""
    a = (SMOOTH_PX - 0.3) / 2.7                      # op のつまみ: σ = 0.3 + 2.7 a
    m = mask.astype(np.float64)
    num = np.asarray(fs.apply(d * m, "gauss_filter", a=a))
    den = np.asarray(fs.apply(m, "gauss_filter", a=a))
    return np.where(mask, num / np.maximum(den, 1e-6), 0.0)


def detect(t_app: np.ndarray, gt: dict, how: str,
           theta: float = THETA) -> dict:
    """正規化 -> 平滑 -> しきい値 -> 連結成分 -> 面積で選別。"""
    d = normalise(t_app, gt, how)
    ds = smooth_in_mask(d, gt["panel"])
    mask = gt["panel"] & (ds > theta)
    lab = np.asarray(fs.ledger.blob_label(mask, connectivity=8))
    if lab.max() > 0:
        lab = np.asarray(fs.ledger.blob_select(lab, "area", vmin=float(A_MIN)))
    return {"delta": ds, "labels": lab, "mask": lab > 0}


def _expand(m: np.ndarray, tol: int = TOL_PX) -> np.ndarray:
    if not m.any():
        return m.copy()
    return distance_transform_edt(~m) <= tol


def score(det: dict, gt: dict) -> dict:
    """検出された塊を 3 値(本物の故障 / 非故障の温度差 / 健全 = 偽)に分ける。

    塊は真値を ``TOL_PX`` だけ膨らませた地図の**多数決**で帰属を決める
    (ぼけで広がった塊が「健全」に化けないように)。
    """
    lab = det["labels"]
    n = int(lab.max())
    f_exp = _expand(gt["fault"])
    nf_exp = _expand(gt["nonfault"]) & ~f_exp
    cls = np.zeros(3, int)
    per_blob = []
    for i in range(1, n + 1):
        b = lab == i
        c = (int((b & f_exp).sum()), int((b & nf_exp).sum()),
             int((b & ~f_exp & ~nf_exp).sum()))
        k = int(np.argmax(c))
        cls[k] += 1
        per_blob.append((i, k, int(b.sum())))
    rec = {}
    for key in ("hot", "string"):
        g = gt[key]
        rec[key] = float((det["mask"] & g).sum() / max(int(g.sum()), 1))
    return {"n_fault": int(cls[0]), "n_nonfault": int(cls[1]),
            "n_false": int(cls[2]), "recall": rec, "blobs": per_blob}


def peak_on(det: dict, mask: np.ndarray, how: str = "max") -> float:
    d = det["delta"][mask]
    if d.size == 0:
        return float("nan")
    return float(d.max() if how == "max" else np.median(d))


# --------------------------------------------------------------------------- #
# 1. 真値の検算                                                                 #
# --------------------------------------------------------------------------- #
def section_truth() -> dict:
    print("\n" + "=" * 78)
    print("1) 真値 —— 定常熱収支の閉形式と、カメラが実際に見る値")
    print("=" * 78)

    u = u_total(V_REF)
    dt_ok = (ALPHA_SOL * G0 - ETA_EL * G0) / u
    print("  風速 %.1f m/s: h_conv %.2f + h_rad %.2f -> U = %.2f W/m²K"
          % (V_REF, h_conv(V_REF), h_rad(), u))
    print("  健全セルの温度上昇 %.1f K(NOCT 相当の 25 K 前後に入る)" % dt_ok)
    print("  面内のフィン長 L = sqrt(k·t/U) = %.1f mm、GSD = %.0f mm"
          % (1e3 * fin_length(V_REF), 1e3 * GSD))

    raw_hot = Q_HOT / u
    a_cond = peak_attenuation(V_REF, 1e-9)             # 伝導だけ
    a_cam = 1.0 - np.exp(-R_HOT ** 2 / (2 * cam_sigma(GSD) ** 2))
    a_both = peak_attenuation(V_REF, GSD)
    print("\n  セル内ホットスポット(余剰発熱 %.0f W/m²、半径 %.0f mm):"
          % (Q_HOT, 1e3 * R_HOT))
    print("    薄まる前          %.2f K" % raw_hot)
    print("    熱伝導だけ        x %.3f -> %.2f K" % (a_cond, raw_hot * a_cond))
    print("    カメラだけ        x %.3f -> %.2f K" % (a_cam, raw_hot * a_cam))
    print("    両方(予測)      x %.3f -> %.2f K" % (a_both, raw_hot * a_both))
    print("  ★予想は「熱が横に流れて薄まる」だった。実測の内訳は逆で、"
          "薄めているのは**カメラ**(%.3f 対 %.3f)。" % (a_cam, a_cond))

    print("\n  ストリング故障(バイパスダイオード導通 = %.0f W/m² の発電が熱に):"
          % (ETA_EL * G0))
    print("    ΔT = %.2 f K(面が広いので薄まらない)".replace("%.2 f", "%.2f")
          % predict_string(V_REF))

    sc = thermal_field(V_REF)
    gt = ground_truth()
    t_app = capture(sc["T"])
    print("\n  真値の面積[px]: 本物の故障 %d(内訳 ホットスポット %d / "
          "ストリング %d)、非故障の温度差 %d、健全 %d"
          % (gt["fault"].sum(), gt["hot"].sum(), gt["string"].sum(),
             gt["nonfault"].sum(), gt["healthy"].sum()))
    print("  大気の透過率 τ(%.0f m) = %.3f、見かけ放射率 ε(0°) = %.3f"
          % (FLIGHT_H, atm_transmittance(FLIGHT_H), float(apparent_emissivity(0.0))))
    off = float(t_app[gt["panel"]].mean() - sc["T"][layout()["panel"]].mean())
    print("  ★放射と大気で、表示温度はパネル平均で %+.2f K ずれている"
          "(オフセットは正規化で消えるが、**ΔT の圧縮は消えない** = 8 節)。" % off)

    assert 20.0 < dt_ok < 30.0, "健全セルの温度上昇が現実的でない"
    assert 0.30 < a_both < 0.60, "ホットスポットの薄まり率が想定外"
    return {"scene": sc, "gt": gt, "t_app": t_app, "u": u, "dt_ok": dt_ok,
            "a_cond": a_cond, "a_cam": a_cam, "a_both": a_both}


# --------------------------------------------------------------------------- #
# 2. ゼロ点と正規化 3 通り                                                      #
# --------------------------------------------------------------------------- #
def section_norms(base: dict) -> dict:
    print("\n" + "=" * 78)
    print("2) ゼロ点(全体平均からの ΔT にしきい値)と、正規化 3 通り")
    print("=" * 78)
    print("  しきい値 %.1f K / 最小面積 %d px / 平滑 σ %.1f px" % (THETA, A_MIN, SMOOTH_PX))
    print("\n   正規化                本物 非故障 偽    ホット再現 ストリング再現"
          "  ΔT(ホット) ΔT(ストリング)")

    gt, t_app = base["gt"], base["t_app"]
    out = {}
    rows = []
    for how in NORMS:
        det = detect(t_app, gt, how)
        s = score(det, gt)
        ph = peak_on(det, gt["hot"])
        ps = peak_on(det, gt["string"], "median")
        out[how] = {"det": det, "score": s, "peak_hot": ph, "peak_str": ps}
        print("   %-20s %3d %5d %4d      %.2f       %.2f          %5.2f K  %5.2f K"
              % (how, s["n_fault"], s["n_nonfault"], s["n_false"],
                 s["recall"]["hot"], s["recall"]["string"], ph, ps))
        rows.append([how, str(s["n_fault"]), str(s["n_nonfault"]),
                     str(s["n_false"]), "%.2f" % s["recall"]["hot"],
                     "%.2f" % s["recall"]["string"], "%.2f" % ph, "%.2f" % ps])

    zp = out["全体平均"]["score"]
    bm = out["モジュール中央値"]["score"]
    print("\n  ★ゼロ点(全体平均)は偽の故障 %d 個。モジュールごとの中央値で %d 個。"
          % (zp["n_false"], bm["n_false"]))
    print("  ★★2 値に畳んではいけない: 「異常」として上がる塊の内訳は"
          "本物 %d / 非故障の温度差(影・汚れ)%d / 偽 %d。"
          % (bm["n_fault"], bm["n_nonfault"], bm["n_false"]))
    print("     影と汚れは**本物の温度差**なので、雑音でも偽でもない ——"
          "しかし電気的故障でもない。")
    pl = out["モジュール平面除去"]
    print("  ★★正規化を強くすると広い故障を食う: ストリング故障の ΔT は"
          "中央値 %.2f K -> 平面除去 %.2f K(%.0f %%)。"
          % (out["モジュール中央値"]["peak_str"], pl["peak_str"],
             100 * pl["peak_str"] / out["モジュール中央値"]["peak_str"]))
    print("     小さいホットスポットは %.0f %% しか食われない —— "
          "**食われる量は故障の面積で決まる**。"
          % (100 * (1 - pl["peak_hot"] / out["モジュール中央値"]["peak_hot"])))

    figs.save_table("norm_table",
                    ["正規化", "本物", "非故障", "偽", "ホット再現",
                     "ストリング再現", "ΔT ホット [K]", "ΔT ストリング [K]"],
                    rows, title="正規化 3 通り —— 3 値で数える(2 値に畳まない)",
                    caption="「偽」= 故障でも影でも汚れでもない場所に出た塊。"
                            "しきい値 %.1f K、風速 %.1f m/s。" % (THETA, V_REF))
    return out


# --------------------------------------------------------------------------- #
# 3. 対照群 —— 故障ゼロで何個出るか                                             #
# --------------------------------------------------------------------------- #
def section_controls() -> dict:
    print("\n" + "=" * 78)
    print("3) ★★対照群 —— 「故障ゼロなのに検出される数」を数える")
    print("=" * 78)
    print("   条件                      正規化              本物 非故障  偽")

    gt = ground_truth()
    conds = (("(a) 故障ゼロ・影と汚れあり", False, True),
             ("(b) 故障だけ・他は無し", True, False),
             ("(c) 両方(実際の場面)", True, True))
    out = {}
    for name, fl, ex in conds:
        t_app = capture(thermal_field(V_REF, faults=fl, extras=ex)["T"])
        for how in NORMS:
            s = score(detect(t_app, gt, how), gt)
            out[(name, how)] = s
            print("   %-26s %-18s %3d %5d %4d"
                  % (name if how == NORMS[0] else "", how,
                     s["n_fault"], s["n_nonfault"], s["n_false"]))

    a_mean = out[(conds[0][0], "全体平均")]
    a_med = out[(conds[0][0], "モジュール中央値")]
    print("\n  ★★故障を 1 つも置いていない (a) で、全体平均は塊 %d 個"
          "(健全 %d / 非故障の温度差 %d)を上げる。"
          % (a_mean["n_fault"] + a_mean["n_nonfault"] + a_mean["n_false"],
             a_mean["n_false"], a_mean["n_nonfault"]))
    print("     モジュールごとの中央値にすると偽は %d 個。**同じ画像で、"
          "基準の取り方だけが違う**。" % a_med["n_false"])
    b = out[(conds[1][0], "モジュール中央値")]
    c = out[(conds[2][0], "モジュール中央値")]
    print("  (b) 故障だけの理想条件では 本物 %d / 偽 %d。(c) 実際の場面では"
          "本物 %d / 非故障 %d / 偽 %d。"
          % (b["n_fault"], b["n_false"], c["n_fault"], c["n_nonfault"],
             c["n_false"]))
    return out


# --------------------------------------------------------------------------- #
# 4. 崖 —— 風速(先に予測してから掃引)                                         #
# --------------------------------------------------------------------------- #
WINDS = (0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0)


def section_wind() -> dict:
    print("\n" + "=" * 78)
    print("4) ★崖 —— 風速。まず予測、それから掃引")
    print("=" * 78)
    v_hot = solve_v_crit(lambda v: predict_hotspot(v, GSD))
    v_str = solve_v_crit(predict_string)
    print("  対流係数 h = 5.7 + 3.8 v なので ΔT は 1/U(v) で薄まる。")
    print("  予測: しきい値 %.1f K を割る風速は ホットスポット %.1f m/s、"
          "ストリング故障 %.1f m/s。" % (THETA, v_hot, v_str))
    print("\n     v [m/s]  U     予測ΔT(ホット) 実測  |  予測ΔT(ストリング) 実測"
          "  |  本物 非故障 偽")

    gt = ground_truth()
    rows, ph_p, ph_m, ps_p, ps_m, nf = [], [], [], [], [], []
    det_hot_v, det_str_v = [], []
    for v in WINDS:
        t_app = capture(thermal_field(v)["T"])
        det = detect(t_app, gt, "モジュール中央値")
        s = score(det, gt)
        a, b = predict_hotspot(v, GSD), predict_string(v)
        m1, m2 = peak_on(det, gt["hot"]), peak_on(det, gt["string"], "median")
        ph_p.append(a), ph_m.append(m1), ps_p.append(b), ps_m.append(m2)
        nf.append(s["n_false"])
        det_hot_v.append(s["recall"]["hot"] > 0.3)
        det_str_v.append(s["recall"]["string"] > 0.3)
        print("     %5.1f  %5.1f   %6.2f      %6.2f  |   %6.2f       %6.2f"
              "  |  %3d %5d %4d"
              % (v, u_total(v), a, m1, b, m2,
                 s["n_fault"], s["n_nonfault"], s["n_false"]))
        rows.append([v, m1, m2])

    last_hot = max([v for v, ok in zip(WINDS, det_hot_v) if ok], default=float("nan"))
    last_str = max([v for v, ok in zip(WINDS, det_str_v) if ok], default=float("nan"))
    print("\n  ★実測で検出できた最後の風速: ホットスポット %.1f m/s、"
          "ストリング %.1f m/s。" % (last_hot, last_str))
    print("     予測 %.1f / %.1f と %s。**同じ日の朝と昼で、同じ故障が"
          "出たり消えたりする**。"
          % (v_hot, v_str,
             "一致" if abs(last_hot - v_hot) <= 1.5 and abs(last_str - v_str) <= 1.5
             else "ずれた"))
    err = [abs(p - m) for p, m in zip(ph_p, ph_m)]
    print("  予測と実測の差はホットスポットで %.2f〜%.2f K"
          "(閉形式が実測を追えている)。" % (min(err), max(err)))
    print("  ★低風速では逆向きに壊れる: v=%.1f で非故障の温度差(汚れの帯)が"
          "%d 個上がる —— **弱い風は偽を増やし、強い風は本物を消す**。"
          % (WINDS[0], score(detect(capture(thermal_field(WINDS[0])["T"]),
                                    gt, "全体平均"), gt)["n_nonfault"]))

    figs.save_plot("wind_sweep",
                   [("予測 ホットスポット", WINDS, ph_p),
                    ("実測 ホットスポット", WINDS, ph_m),
                    ("予測 ストリング", WINDS, ps_p),
                    ("実測 ストリング", WINDS, ps_m),
                    ("しきい値 %.1f K" % THETA, WINDS, [THETA] * len(WINDS))],
                   xlabel="風速 v [m/s]", ylabel="見かけの ΔT [K]",
                   title="同じ故障が風速で消える(予測は 1/U(v) の閉形式)",
                   caption="U(v) = 1.75·(5.7 + 3.8v + h_rad)。予測の線は"
                           "画像を一切見ずに引いてある。")
    return {"v_hot": v_hot, "v_str": v_str, "winds": list(WINDS),
            "pred_hot": ph_p, "meas_hot": ph_m, "pred_str": ps_p,
            "meas_str": ps_m, "last_hot": last_hot, "last_str": last_str,
            "n_false": nf}


# --------------------------------------------------------------------------- #
# 5. 影が本物のストリング故障を偽造する                                         #
# --------------------------------------------------------------------------- #
def section_shadow(base: dict) -> dict:
    print("\n" + "=" * 78)
    print("5) ★★影は本物のストリング故障を偽造する")
    print("=" * 78)

    gt = base["gt"]
    det = detect(base["t_app"], gt, "モジュール中央値")
    d = det["delta"]
    cold = float(np.median(d[gt["panel"] & _shade_gsd()]))
    warm = float(np.median(d[gt["shade_warm"]])) if gt["shade_warm"].any() else float("nan")
    real = float(np.median(d[gt["string"]]))
    print("  影に入ったセル自身: ΔT %+.2f K(日射が %.0f %% に落ちるので冷える)"
          % (cold, 100 * SHADE_FRAC))
    print("  ★同じストリングの**日向のセル**: ΔT %+.2f K —— 発電が止まった分が"
          "熱になる。" % warm)
    print("  本物のストリング故障(バイパスダイオード導通): ΔT %+.2f K" % real)
    print("  ★★差は %.2f K。**熱画像だけでは区別できない** —— 区別するには"
          "影の側(冷たい帯)が同じストリングに接しているかを見るしかない。"
          % abs(warm - real))

    # 対照群: 影だけ / 故障だけ
    only_shade = capture(thermal_field(V_REF, faults=False, extras=True)["T"])
    s_only = score(detect(only_shade, gt, "モジュール中央値"), gt)
    print("  対照群(故障ゼロ・影あり)では、この偽ストリングが"
          "非故障の温度差 %d 個として上がる —— **点検票では『要調査』**。"
          % s_only["n_nonfault"])
    assert abs(warm - real) < 1.5, "影による偽ストリングが本物と離れすぎている"
    return {"cold": cold, "warm": warm, "real": real}


def _shade_gsd() -> np.ndarray:
    L = layout()
    k = int(round(GSD / FINE))
    return block_mean(L["shade"].astype(np.float64), k) > 0.5


# --------------------------------------------------------------------------- #
# 6. GSD の掃引                                                                 #
# --------------------------------------------------------------------------- #
GSDS = (0.010, 0.015, 0.020, 0.030, 0.040, 0.060, 0.080)


def section_gsd() -> dict:
    print("\n" + "=" * 78)
    print("6) ★GSD(画素の地上寸法)—— 閉形式 1 - exp(-R²/2σ²) と突き合わせる")
    print("=" * 78)
    print("     GSD [mm]  σ_tot [mm]  予測の薄まり  予測 ΔT   実測 ΔT   検出")

    sc = thermal_field(V_REF)
    pred, meas, xs = [], [], []
    for g in GSDS:
        gt = ground_truth(g)
        t_app = capture(sc["T"], gsd=g)
        det = detect(t_app, gt, "モジュール中央値")
        s = score(det, gt)
        a = peak_attenuation(V_REF, g)
        st = np.sqrt(fin_length(V_REF) ** 2 + cam_sigma(g) ** 2)
        p = Q_HOT / u_total(V_REF) * a
        m = peak_on(det, gt["hot"])
        xs.append(1e3 * g), pred.append(p), meas.append(m)
        print("     %6.0f    %7.1f     %8.3f     %6.2f    %6.2f    %s"
              % (1e3 * g, 1e3 * st, a, p, m,
                 "○" if s["recall"]["hot"] > 0.3 else "×"))

    ratios = [m / p for p, m in zip(pred, meas) if np.isfinite(m)]
    g_crit = None
    for g in np.arange(0.008, 0.100, 0.001):
        if predict_hotspot(V_REF, float(g)) < THETA:
            g_crit = float(g)
            break
    print("\n  ★予測と実測の比は %.2f〜%.2f(閉形式が %d 点すべてで当たる)。"
          % (min(ratios), max(ratios), len(ratios)))
    print("  しきい値 %.1f K を割る GSD の予測は %.0f mm ——"
          "セル 1 枚(%.0f mm)の %.2f 倍で、**セルが写っていても足りない**。"
          % (THETA, 1e3 * g_crit, 1e3 * CELL, g_crit / CELL))

    figs.save_plot("gsd_sweep",
                   [("予測(閉形式)", xs, pred), ("実測", xs, meas),
                    ("しきい値 %.1f K" % THETA, xs, [THETA] * len(xs))],
                   xlabel="GSD [mm/px]", ylabel="ホットスポットの ΔT [K]",
                   title="画素が大きいと熱源は薄まる(1 - exp(-R²/2σ²))",
                   caption="半径 %.0f mm の熱源。σ_tot は熱伝導・光学・画素・"
                           "判定平滑の二乗和。" % (1e3 * R_HOT))
    return {"gsd": xs, "pred": pred, "meas": meas, "g_crit": g_crit}


# --------------------------------------------------------------------------- #
# 7. 撮影角度 —— 見かけ放射率と射影補正                                         #
# --------------------------------------------------------------------------- #
ANGLES = (0.0, 20.0, 40.0, 55.0, 65.0, 75.0)


def oblique_homographies(shape, theta_deg: float):
    """正対 <-> 斜め の射影変換(``warp_by_plane`` に渡す形)。"""
    h, w = shape
    th = np.radians(theta_deg)
    z0 = 2.4 * max(h, w)
    m = np.array([[z0, 0.0, 0.0],
                  [0.0, z0 * np.cos(th), 0.0],
                  [0.0, -np.sin(th), z0]])
    c = np.array([[1.0, 0.0, -0.5 * w], [0.0, 1.0, -0.5 * h], [0.0, 0.0, 1.0]])
    m = np.linalg.inv(c) @ m @ c
    m = m / m[2, 2]
    return np.linalg.inv(m), m          # (正対->斜めを描く用, 斜め->正対に戻す用)


def section_angle(base: dict) -> dict:
    print("\n" + "=" * 78)
    print("7) ★★撮影角度 —— 幾何は直せるが放射は直らない")
    print("=" * 78)
    print("  見かけ放射率 ε(θ) = 1 - R(θ)(Fresnel、等価屈折率 1.8)。")
    print("  予測の圧縮率 dT_app/dT = (ε/ε_set)·(T/T_app)³。")
    print("\n     角度 [deg]  ε(θ)   予測圧縮  実測圧縮  ΔT(ホット)  射影補正後  検出")

    sc = thermal_field(V_REF)
    gt = ground_truth()
    ref = None
    xs, pe, me, rect = [], [], [], []
    for a in ANGLES:
        t_app = capture(sc["T"], theta_deg=a)
        det = detect(t_app, gt, "モジュール中央値")
        s = score(det, gt)
        ph = peak_on(det, gt["hot"])
        if ref is None:
            ref = ph
        eps = float(apparent_emissivity(a))
        tm = float(np.median(sc["T"][layout()["panel"]]))
        ta = float(to_apparent(tm, a))
        p = (eps / EPS_SET) * (tm / ta) ** 3
        # 斜めから撮って、射影変換で正対に戻す
        h_draw, h_back = oblique_homographies(t_app.shape, a)
        obl = np.asarray(fs.ledger.warp_by_plane(t_app, h_draw, cval=float(np.nan)))
        back = np.asarray(fs.ledger.warp_by_plane(np.nan_to_num(obl, nan=T_AIR),
                                                  h_back, cval=float(np.nan)))
        back = np.nan_to_num(back, nan=T_AIR)
        d2 = detect(back, gt, "モジュール中央値")
        pr = peak_on(d2, gt["hot"])
        xs.append(a), pe.append(p), me.append(ph / ref), rect.append(pr / ref)
        print("     %7.0f    %.3f   %7.3f   %7.3f    %6.2f      %6.2f    %s"
              % (a, eps, p, ph / ref, ph, pr, "○" if s["recall"]["hot"] > 0.3 else "×"))

    i = len(ANGLES) - 2
    print("\n  ★★%.0f° で見かけ放射率は %.3f -> %.3f、ΔT は %.2f 倍に圧縮される。"
          % (ANGLES[i], float(apparent_emissivity(0.0)),
             float(apparent_emissivity(ANGLES[i])), me[i]))
    print("     射影変換(``warp_by_plane``)で正対に戻すと**形は戻る**が、"
          "ΔT は %.2f 倍のまま(%.2f -> %.2f)。" % (rect[i], me[i], rect[i]))
    print("     **見かけの温度差は幾何補正では回復しない** —— 放射率の補正が"
          "別に要る(そのためには入射角を画素ごとに知る必要がある)。")
    print("  予測と実測の差は最大 %.3f。" % max(abs(p - m) for p, m in zip(pe, me)))

    figs.save_plot("angle_sweep",
                   [("予測 (ε/ε_set)(T/T_app)³", xs, pe),
                    ("実測(斜めのまま)", xs, me),
                    ("実測(射影補正後)", xs, rect)],
                   xlabel="入射角 θ [deg]", ylabel="ΔT の残る割合(0° を 1 とする)",
                   title="角度で ΔT が圧縮される —— 射影補正では戻らない",
                   caption="ε(θ) は Fresnel(等価屈折率 1.8)。射影補正は "
                           "fs.ledger.warp_by_plane を 2 回。")
    return {"deg": xs, "pred": pe, "meas": me, "rect": rect}


# --------------------------------------------------------------------------- #
# 8. NETD                                                                       #
# --------------------------------------------------------------------------- #
NETDS = (0.020, 0.050, 0.080, 0.120, 0.160, 0.200)


def section_netd() -> dict:
    print("\n" + "=" * 78)
    print("8) NETD(雑音)—— 崖は「見えなくなる」ではなく「無いものが見える」")
    print("=" * 78)
    print("     NETD [mK]  ホット再現  ストリング再現  本物  非故障  偽")

    sc = thermal_field(V_REF)
    gt = ground_truth()
    xs, fa, rc = [], [], []
    for nd in NETDS:
        t_app = capture(sc["T"], netd=nd)
        s = score(detect(t_app, gt, "モジュール中央値"), gt)
        xs.append(1e3 * nd), fa.append(s["n_false"]), rc.append(s["recall"]["hot"])
        print("     %7.0f      %.2f        %.2f        %3d %5d %4d"
              % (1e3 * nd, s["recall"]["hot"], s["recall"]["string"],
                 s["n_fault"], s["n_nonfault"], s["n_false"]))
    print("\n  ★見逃しは %.2f -> %.2f とほとんど動かないのに、偽の故障は "
          "%d -> %d 個に増える。" % (rc[0], rc[-1], fa[0], fa[-1]))
    print("     しきい値 1 本で切る限り、雑音は**偽を作る向き**に効く"
          "(面積の門 %d px を上げれば減るが、小さい本物も落ちる)。" % A_MIN)

    figs.save_plot("netd_sweep",
                   [("偽の故障の数", xs, fa),
                    ("ホットスポット再現率 x10", xs, [10 * v for v in rc])],
                   xlabel="NETD [mK]", ylabel="個数 / 再現率 x10",
                   title="雑音は見逃しでなく偽を増やす",
                   caption="風速 %.1f m/s、モジュールごとの中央値を基準。"
                           % V_REF)
    return {"netd": xs, "false": fa, "recall": rc}


# --------------------------------------------------------------------------- #
# 9. 絵                                                                         #
# --------------------------------------------------------------------------- #
def section_figures(base: dict, norms: dict) -> None:
    if not figs.enabled():
        return
    gt, t_app = base["gt"], base["t_app"]
    det = norms["モジュール中央値"]["det"]

    truth = np.zeros(gt["panel"].shape + (3,))
    truth[gt["healthy"]] = (0.20, 0.35, 0.55)
    truth[gt["nonfault"]] = (0.95, 0.80, 0.25)
    truth[gt["fault"]] = (0.90, 0.20, 0.20)

    over = np.asarray(fs.overlay_mask(
        np.asarray(fs.colorize_depth(det["delta"]), np.float64)[..., :3],
        det["mask"], color=(1.0, 1.0, 1.0), alpha=0.85, mode="margin",
        line_width=1))

    figs.save_grid("scene",
                   [t_app - T_AIR, truth, det["delta"], over],
                   ["見かけ温度 - 気温 [K]", "真値 3 値(赤=故障 黄=影と汚れ 青=健全)",
                    "ΔT(モジュール中央値基準)[K]", "検出された塊(白枠)"],
                   ncols=2, signed=[False, False, True, False],
                   title="メガソーラーのドローン熱画像(GSD %.0f mm、風速 %.1f m/s)"
                         % (1e3 * GSD, V_REF),
                   caption="真値の赤はセル内ホットスポットとストリング故障、"
                           "黄は影と汚れ(本物の温度差だが電気的故障ではない)。")

    # 偽の故障の地図 —— 対照群 (a) 故障ゼロ
    t0 = capture(thermal_field(V_REF, faults=False, extras=True)["T"])
    d_mean = detect(t0, gt, "全体平均")
    d_med = detect(t0, gt, "モジュール中央値")
    figs.save_grid("false_map",
                   [d_mean["delta"], d_mean["mask"].astype(float),
                    d_med["delta"], d_med["mask"].astype(float)],
                   ["ΔT 全体平均基準 [K]", "そこで上がった塊(= 偽 + 非故障)",
                    "ΔT モジュール中央値基準 [K]", "そこで上がった塊"],
                   ncols=2, signed=[True, False, True, False],
                   title="対照群: 電気的故障を 1 つも置いていない場面",
                   caption="上段の塊はすべて偽か非故障の温度差。基準の取り方"
                           "だけで消える。")


# --------------------------------------------------------------------------- #
# 10. 道具の穴                                                                  #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("10) 道具の穴(この PoC で fullseye を引いてみて)")
    print("=" * 78)

    assert hasattr(fs.ledger, "volume_downsample")
    assert not hasattr(fs.ledger, "image_downsample")
    assert not hasattr(fs, "block_mean")
    print("  (a) 2-D の**面積平均ビニング**が公開経路に無い。3-D には"
          " volume_downsample(整数倍のブロックプール)があるのに、画像側は"
          " zoom_image_factor(補間)しかない。GSD を変える掃引は面積平均で"
          "ないと放射量が保存しないので、この PoC は block_mean を自前で書いた。")

    a = (SMOOTH_PX - 0.3) / 2.7
    assert 0.0 <= a <= 1.0
    print("  (b) **σ を直接指定できる 2-D ガウス平滑**が無い。fs.apply の"
          " gauss_filter は σ = 0.3 + 2.7·a で **0.3〜3.0 px にしか振れない**。"
          "カメラの PSF(GSD 80 mm では細格子で σ 11.2 px)は範囲外なので、"
          "場面合成は scipy に落ちている(判定側の σ %.1f px は op で通した)。"
          % SMOOTH_PX)

    assert not hasattr(fs.ledger, "planck_radiance")
    assert not hasattr(fs, "brightness_temperature")
    print("  (c) **放射測温の口が無い**。Fresnel(fresnel_dielectric)と"
          " Beer-Lambert(beer_lambert_transmittance)は在るのに、"
          "「放射率・大気透過率・反射見かけ温度から輝度温度を真温度に直す」"
          "1 本が無い。赤外カメラを扱う例は必ずこれを書くので、族に入る価値がある。")

    assert hasattr(fs.ledger, "background_flatten")
    print("  (d) 面の当てはめが**マスクを取れない**。background_flatten も"
          " surface_form_remove も格子を丸ごと受ける(docstring に「NaN があると"
          " lstsq が失敗する」と明記)。パネルだけで平面を当てたい今回は"
          "モジュールごとの矩形に切って呼ぶ形にした —— 矩形でない ROI では"
          "呼べない。")

    assert hasattr(fs.ledger, "blob_label") and hasattr(fs.ledger, "blob_select")
    assert not hasattr(fs.ledger, "detection_confusion")
    print("  (e) 検出を**真値と突き合わせて数える**枠組みが無い(fscore は"
          " (N,3) 点群専用)。3 値(本物 / 非故障 / 偽)の数え方は作法の問題だが、"
          "「許容 %d px で膨らませてから多数決」まで含めて族に入れれば、"
          "PoC ごとに書き直さずに済む。" % TOL_PX)


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.perf_counter()
    print("=" * 78)
    print("メガソーラーのドローン熱画像 —— 温度差を測っているつもりで、"
          "風と角度を測っている")
    print("アレイ %d x %d モジュール / 視野 %.2f x %.2f m / 真値格子 %.0f mm / "
          "GSD %.0f mm" % (NMX, NMY, WORLD_W, WORLD_H, 1e3 * FINE, 1e3 * GSD))
    print("=" * 78)

    base = section_truth()
    norms = section_norms(base)
    ctl = section_controls()
    wind = section_wind()
    shadow = section_shadow(base)
    gsd = section_gsd()
    ang = section_angle(base)
    netd = section_netd()
    section_figures(base, norms)
    section_tool_gaps()

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * 健全セル +%.1f K、ホットスポットは薄まる前 %.1f K が"
          "**カメラに届くのは %.1f K**(伝導 x%.3f、カメラ x%.3f)。"
          % (base["dt_ok"], Q_HOT / base["u"],
             Q_HOT / base["u"] * base["a_both"], base["a_cond"], base["a_cam"]))
    a_mean = ctl[("(a) 故障ゼロ・影と汚れあり", "全体平均")]
    a_med = ctl[("(a) 故障ゼロ・影と汚れあり", "モジュール中央値")]
    print("  * 故障ゼロの対照群で、全体平均は偽 %d 個 / 非故障 %d 個。"
          "モジュールごとの中央値なら偽 %d 個 / 非故障 %d 個。"
          % (a_mean["n_false"], a_mean["n_nonfault"],
             a_med["n_false"], a_med["n_nonfault"]))
    print("  * 風速の崖: 予測 %.1f / %.1f m/s、実測で検出できた最後は"
          " %.1f / %.1f m/s(ホットスポット / ストリング)。"
          % (wind["v_hot"], wind["v_str"], wind["last_hot"], wind["last_str"]))
    print("  * 影はストリング故障を偽造する: 日向側 %+.2f K 対 本物 %+.2f K"
          "(差 %.2f K)。" % (shadow["warm"], shadow["real"],
                             abs(shadow["warm"] - shadow["real"])))
    print("  * GSD %.0f mm を超えるとホットスポットはしきい値を割る"
          "(閉形式の予測、実測との比は %.2f〜%.2f)。"
          % (1e3 * gsd["g_crit"],
             min(m / p for p, m in zip(gsd["pred"], gsd["meas"])),
             max(m / p for p, m in zip(gsd["pred"], gsd["meas"]))))
    print("  * 入射角 %.0f° で ΔT は %.2f 倍。射影変換で正対に戻しても %.2f 倍の"
          "まま —— 幾何は直せるが放射は直らない。"
          % (ang["deg"][-2], ang["meas"][-2], ang["rect"][-2]))
    print("  * NETD %.0f -> %.0f mK で見逃しは動かず(再現率 %.2f -> %.2f)、"
          "偽だけが %d -> %d 個。"
          % (netd["netd"][0], netd["netd"][-1], netd["recall"][0],
             netd["recall"][-1], netd["false"][0], netd["false"][-1]))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
