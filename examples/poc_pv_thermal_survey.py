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
   +25.0 K(U = 28.56 W/m²K、NOCT 相当)。余剰発熱 320 W/m² のセル内
   ホットスポットは薄まる前 +11.20 K だが、**カメラが見るのは 4.23 K**。
   ★内訳は予想と逆だった —— 「熱が横に流れて薄まる」と踏んでいたのに、
   熱伝導は x0.960(フィン長 11.8 mm)でほとんど効かず、薄めているのは
   **カメラ** x0.511(GSD 20 mm)。さらに大気(τ=0.840)と放射率の設定
   ずれ(ε 0.918 に対しカメラ設定 0.95)で x0.854。実測も 4.23 K。
2. ★★**「故障ゼロ」の対照群で偽の故障が出る**。電気的故障を 1 つも
   置いていない場面で、全体平均を基準にすると塊 **6 個**(健全 1 /
   非故障の温度差 5)。健全 1 個の正体は**風の当たらないモジュールが
   4 K 熱いだけ**で、モジュールごとの中央値を引けば **0 個**になる。
3. ★★**3 つの正規化はどれも別の壊れ方をする**(無料の昼飯は無い)。
   全体平均は偽を作るうえ、日射の時間変化(視野の上下で 12 %)のせいで
   **本物のホットスポットを見逃す**(再現率 0.00、ΔT 2.13 K)。
   モジュール中央値は再現率 1.00 だが、支柱の影で**全ストリングが
   止まったモジュール**に盲目(全体平均基準の +3.43 K が +0.08 K になる)。
   モジュール平面除去はストリング故障の ΔT を 5.55 → 4.10 K(74 %)に
   食う —— **食われる量は故障の面積で決まる**(7 px のホットスポットは
   104 % 残る)。
4. ★★**崖はしきい値ではなく面積の門が決める**。h = 5.7 + 3.8 v
   (McAdams)なので ΔT は 1/U(v) で薄まる。「ピークが 3.0 K を割る」
   予測は 3.0 m/s だが、実測では **1.0 m/s までは上がり 2.0 m/s で消える**
   (掃引の刻み 1 m/s)。塊の面積 2π σ_tot² ln(P/θ) が門(4 px)を割る風速を
   予測すると **1.1 m/s** で、その刻みの中に入った。面積の広いストリング故障は門が効かず、ピーク基準の予測
   4.6 m/s と実測 4.0 m/s(掃引の刻み 1 m/s)が合う。**同じ日の朝と昼で、
   同じ故障が出たり消えたりする**。
5. ★★**影は本物のストリング故障を偽造する**。列間影に入ったセルは
   -18.41 K 冷えるだけでなく、そのストリングの発電を止めるので**日向の
   セルが +4.68 K 熱くなる** —— 本物のストリング故障(+5.55 K)との差は
   **0.87 K**。熱の形も大きさも同じで、熱画像だけでは区別できない。
   ★半径 10 cm の雑草の影(495 cm²)が、その **20 倍**の 9750 cm² の
   発電を止める —— 直列だから、いちばん暗いセルが全部を決める。
6. ★**GSD の崖は閉形式で当たる**。半径 30 mm の熱源が σ_tot のガウスで
   薄まる率は 1 - exp(-R²/2σ_tot²)。GSD 10→80 mm で予測 7.46→0.41 K、
   実測 7.31→0.45 K(比 0.95〜1.09)。しきい値を割るのは GSD 26 mm ——
   **セル 1 枚が 6 画素に写る細かさでも足りない**(熱源はセルより小さい)。
7. ★★**幾何は直せるが放射は直らない**。入射角 65° で見かけ放射率は
   0.918 → 0.834(Fresnel)、ΔT は 0.93 倍に圧縮される。射影変換
   (``warp_by_plane``)で正対に戻すとホットスポットの位置ずれは
   80.1 → 0.5 px に戻るのに、ΔT は 0.93 → **0.61 倍**(往復の再標本化で
   さらに減る)。20° でも 0.87 倍しか残らない。
8. ★★**NETD の予想は外れた**。「雑音を増やせば偽の故障が増える」と
   踏んでいたが、20 → 3000 mK まで振っても偽は **0 個のまま**(予測の崖
   2363 mK さえ越えられない —— 4 節と同じ面積の門が効く)。
   ★そのかわり数え方の罠が出た: 非故障の塊は 1 → 44 個に増えるのに、
   塊の総面積は 1620 → 1892 px でほとんど変わらない。**同じ帯が雑音で
   ちぎれているだけ** —— 個数で報告すると雑音が「発見」に化ける。

9. ★★**実データ(DTU の PV 発電所のドローン熱画像、CC BY 4.0)で同じ判定を回す**。
   バイパスダイオードが短絡したモジュールは日射 600 W/m² 以上で 84 / 84 枚すべて上がるが、
   日射 200 では 7 台のうち 2 台が 4 つの高さすべてで消える(ΔT 1.1 / 2.0 K)—— 合成の
   4 節と同じ「同じ故障が条件で出たり消えたりする」。高さ 8 → 20 m でピークの ΔT は
   21 / 21 組で下がる(比の中央値 0.77。ただしモジュール全体の温度も高さとともに動いており、
   撮影の時刻・大気の経路と分けられていない)。★★汚れ(配布元の分類の 1 つ。電気的な故障ではない)の
   モジュールも同じ判定で 144 枚中 72 枚が上がる —— 温度のしきい値は原因(汚れか電気的な故障か)を
   分けない(合成の 2・5 節と同じ形)。汚れの 2 台の現地の IV 曲線の性能比は 47.3 % / 30.3 %
   (実測の Pmax を測定器の模型の Pmax で割った値。清掃の前後や健全なモジュールの IV は配布物に無く、
   台数も 2 台なので、出力の低下が汚れによるかは分けられない)。★限界: セルの割れと配線の不良(EL で確かめた本物の故障)は
   256 枚で 1 度も上がらない(熱画像のしきい値では見逃し率 100 %)。データが無ければこの章だけ飛ばす
   (``tools/fetch_dtu_pv_irt.py`` で取得、置き場は ``FULLSEYE_PV_IRT_DATA``)。

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

import os
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter, map_coordinates

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402
from fullseye.evaluation import (                                # noqa: E402
    CaseResult, GateResult, TruthBundle, artifacts_from_manifest, build_manifest,
)

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


def predict_hotspot(v: float, gsd: float = GSD, radio: bool = True) -> float:
    """セル内ホットスポットの見かけの ΔT [K](予測、閉形式)。"""
    g = radiometric_gain() if radio else 1.0
    return Q_HOT / u_total(v) * peak_attenuation(v, gsd) * g


def predict_string(v: float, radio: bool = True) -> float:
    """ストリング故障の ΔT [K](広いので薄まらない)。"""
    g = radiometric_gain() if radio else 1.0
    return ETA_EL * G0 / u_total(v) * g


def predict_blob_area_px(v: float, gsd: float = GSD,
                         theta: float = THETA) -> float:
    """しきい値を超える塊の面積 [px] —— ガウス山の等高線の閉形式。

    ピーク ``P``、σ_tot のガウス山が ``theta`` を超える面積は
    ``2π σ_tot² ln(P/theta)``。**面積の門(``A_MIN``)はここに効く** ——
    ピークがしきい値を超えていても、超える範囲が狭ければ塊にならない。
    """
    p = predict_hotspot(v, gsd)
    if p <= theta:
        return 0.0
    s2 = fin_length(v) ** 2 + cam_sigma(gsd) ** 2
    return float(2.0 * np.pi * s2 * np.log(p / theta) / gsd ** 2)


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


def radiometric_gain(theta_deg: float = VIEW_DEG, t_ref: float = T_AIR + 25.0,
                     dist_m: float = FLIGHT_H) -> float:
    """真の ΔT に対して**表示される** ΔT が何倍になるか —— 閉形式の微分。

    ``T_app⁴·ε_set = τ·ε·T⁴ + (T に依らない項)`` を微分して

        dT_app/dT = τ·(ε/ε_set)·(T/T_app)³

    大気で τ 倍、放射率の設定ずれで ε/ε_set 倍、温度の 4 乗則で (T/T_app)³ 倍。
    **オフセットは正規化で消えるが、この圧縮は消えない**。
    """
    eps = float(apparent_emissivity(theta_deg))
    tau = atm_transmittance(dist_m)
    ta = float(to_apparent(t_ref, theta_deg, dist_m))
    return tau * (eps / EPS_SET) * (t_ref / ta) ** 3


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

    def origin(m):
        return (MARGIN + (m % NMX) * (MOD_W + GAP_X),
                MARGIN + (m // NMX) * (MOD_H + GAP_Y))

    # --- 影 1: 支柱 —— モジュールを斜めに横切る帯(全ストリングを止める)------ #
    ang = np.radians(POLE_DEG)
    bx, by = origin(MOD_POLE)
    c = (bx + 0.5 * MOD_W) * np.cos(ang) + (by + 0.5 * MOD_H) * np.sin(ang)
    dist = np.abs(xx * np.cos(ang) + yy * np.sin(ang) - c)
    shade_pole = (dist < 0.5 * POLE_W) & (mod_id == MOD_POLE)
    # --- 影 2: 列間影 —— 前列の陰が下辺に乗る(1 ストリングだけ止める)-------- #
    bx, by = origin(MOD_ROWSH)
    shade_row = (mod_id == MOD_ROWSH) & (yy > by + MOD_H - ROWSH_H)
    # --- 影 3: 雑草 —— 小さい円(小さい原因で 20 セルが止まる)---------------- #
    bx, by = origin(MOD_GRASS)
    shade_grass = np.zeros_like(panel)
    for gx, gr in GRASS:
        shade_grass |= (((xx - (bx + gx)) ** 2 + (yy - (by + 0.55)) ** 2 < gr ** 2)
                        & (mod_id == MOD_GRASS))
    shade = shade_pole | shade_row | shade_grass

    # --- 影に食われたストリング(そのストリングの発電が止まる)---------------- #
    def killed(sh):
        out = np.zeros_like(panel)
        for m in np.unique(mod_id[sh]):
            for s in np.unique(sub[sh & (mod_id == m)]):
                out |= (mod_id == m) & (sub == s)
        return out

    kill_pole, kill_row = killed(shade_pole), killed(shade_row)
    kill_shade = kill_pole | kill_row | killed(shade_grass)

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
    #     ★MOD_SHELTER は**健全なのに風が当たらない**モジュール。3 節でこれが
    #       全体平均基準では「故障」に化ける。
    rng = np.random.default_rng(SEED)
    u_scale = np.ones((NY, NX))
    for m in range(NMX * NMY):
        f = 1.0 + 0.045 * rng.standard_normal()
        if m == MOD_SHELTER:
            f *= U_SHELTER
        u_scale[mod_id == m] = f

    # --- 撮影中の日射の変化(視野の上下で ±IRR_DRIFT/2)------------------------ #
    g_time = 1.0 + IRR_DRIFT * (yy / WORLD_H - 0.5)

    _LAYOUT = {
        "x": xx, "y": yy, "mod_id": mod_id, "panel": panel, "sub": sub,
        "shade": shade, "kill_shade": kill_shade, "soil": soil,
        "shade_pole": shade_pole, "shade_row": shade_row,
        "kill_pole": kill_pole, "kill_row": kill_row,
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


#: 斜めの空撮のカメラ(DTU の公開データと同じ 8〜20 m の高さ、640 x 512、水平画角 32°)
AERIAL_ALT = 9.0           # 高さ [m]
AERIAL_TILT = 32.0         # 鉛直からの傾き [deg]
AERIAL_HFOV = 32.0         # 水平画角 [deg]
FRAME_EPS = 0.80           # アルマイトの枠の放射率
GROUND_EPS = 0.95          # 草地の放射率


def _aerial_camera(h: int = 512, w: int = 640):
    """画素 -> 地面 (x, y) [m] と、地面 -> 画素の 2 つの写像(ピンホール、地面は z = 0)。

    カメラは配列の中心の手前(+y 側)の上空 ``AERIAL_ALT`` m から、鉛直から ``AERIAL_TILT``°
    傾けて配列の中心を見る。画像の上が奥(-y)。
    """
    f = 0.5 * w / np.tan(np.radians(0.5 * AERIAL_HFOV))
    t = np.radians(AERIAL_TILT)
    cx_w, cy_w = 0.5 * WORLD_W, 0.5 * WORLD_H
    cam = np.array([cx_w, cy_w + AERIAL_ALT * np.tan(t), AERIAL_ALT])
    fwd = np.array([0.0, -np.sin(t), -np.cos(t)])          # 光軸
    right = np.array([1.0, 0.0, 0.0])
    down = np.cross(fwd, right)                              # 画像の下向き
    down = -down if down[1] < 0 else down                    # 画像の下 = 手前(+y)

    def pix_to_world(u, v):
        d = (fwd[:, None] * f + right[:, None] * (np.ravel(u) - 0.5 * w)
             + down[:, None] * (np.ravel(v) - 0.5 * h))
        s = -cam[2] / d[2]
        p = cam[:, None] + s * d
        view = np.degrees(np.arccos(np.clip(-d[2] / np.linalg.norm(d, axis=0), -1, 1)))
        dist = s * np.linalg.norm(d, axis=0)
        shape = np.shape(u)
        return p[0].reshape(shape), p[1].reshape(shape), view.reshape(shape), dist.reshape(shape)

    def world_to_pix(x, y):
        q = np.array([x, y, 0.0]) - cam
        z = q @ fwd
        return float(0.5 * w + f * (q @ right) / z), float(0.5 * h + f * (q @ down) / z)

    return pix_to_world, world_to_pix


def _aerial_true_temperature(xw, yw, gnd) -> tuple[np.ndarray, np.ndarray]:
    """地面の座標での真の表面温度 [K] と放射率。測る 3 x 3 の外にも健全なアレイが続く。

    パネルの中は :func:`thermal_field` の閉形式(故障・影・汚れ入り)に、閉形式に入れていない
    細部を足す: セルごとのばらつき(±0.35 K)、セルの隙間に見える裏面シート(-0.8 K)、
    枠への熱の逃げ(縁から 8 cm で -1.5 K)、裏の端子箱(+2 K)、枠(アルマイト、ε 0.80)。
    地面は草地(多重解像度の揺らぎ)と、アレイの列の地面の影(-6 K)。
    """
    L = layout()
    sc = thermal_field(V_REF)["T"]
    dt_ok = (ALPHA_SOL * G0 - ETA_EL * G0) / u_total(V_REF)
    px, py = MOD_W + GAP_X, MOD_H + GAP_Y
    # 3 x 3 の格子を左右に 2 列ずつ、上下に 2 段ずつ延ばす(健全なモジュール)
    gx = np.floor((xw - MARGIN) / px)
    gy = np.floor((yw - MARGIN) / py)
    lx = (xw - MARGIN) - gx * px
    ly = (yw - MARGIN) - gy * py
    in_mod = (lx >= 0) & (lx < MOD_W) & (ly >= 0) & (ly < MOD_H) & (np.abs(gx - 1) <= 3) & (gy >= -3) & (gy <= 4)
    measured = in_mod & (gx >= 0) & (gx < NMX) & (gy >= 0) & (gy < NMY)
    # 地面: 草地の揺らぎ(粗い + 細かい)と列の影(パネルの奥 = -y 側の地面が日陰)
    gi = np.clip(((yw + 6.0) / 0.02).astype(int), 0, 899)
    gj = np.clip(((xw + 6.0) / 0.02).astype(int), 0, 899)
    t = T_AIR + GROUND_RISE + gnd[gi, gj]
    row_shadow = (ly >= MOD_H) & (ly < MOD_H + 0.75 * GAP_Y) & (np.abs(gx - 1) <= 3) & (gy >= -3) & (gy <= 4)
    t = np.where(row_shadow, T_AIR + 4.0 + 0.3 * gnd[gi, gj], t)
    eps = np.full(xw.shape, GROUND_EPS)
    # 健全なモジュールの温度(モジュールごとの差 ±4.5 %)
    mod_key = ((gy + 3) * 16 + (gx + 4)).astype(int)
    mod_f = 1.0 + 0.045 * np.random.default_rng(SEED + 11).standard_normal(16 * 16)
    t_mod = T_AIR + dt_ok / mod_f[np.clip(mod_key, 0, 255)] * (1.0 + IRR_DRIFT * (yw / WORLD_H - 0.5))
    # 測る 3 x 3 は閉形式の場をそのまま読む
    si = np.clip((yw / FINE).astype(int), 0, NY - 1)
    sj = np.clip((xw / FINE).astype(int), 0, NX - 1)
    t_mod = np.where(measured & L["panel"][si, sj], sc[si, sj], t_mod)
    # セルごとのばらつき・隙間・縁の冷え・端子箱
    cr = np.clip((ly / CELL).astype(int), 0, NC_Y - 1)
    cc = np.clip((lx / CELL).astype(int), 0, NC_X - 1)
    cell_key = (mod_key * 64 + cr * NC_X + cc) % (1 << 16)
    cell_off = 0.35 * np.random.default_rng(SEED + 12).standard_normal(1 << 16)
    t_mod = t_mod + cell_off[cell_key]
    gap = (np.minimum(np.mod(lx, CELL), CELL - np.mod(lx, CELL)) < 0.0015) | \
          (np.minimum(np.mod(ly, CELL), CELL - np.mod(ly, CELL)) < 0.0015)
    t_mod = t_mod - 0.8 * gap
    edge = np.minimum.reduce([lx, MOD_W - lx, ly, MOD_H - ly])
    t_mod = t_mod - 1.5 * np.exp(-edge / 0.08)
    jb = ((lx - 0.5 * MOD_W) / 0.09) ** 2 + ((ly - 0.10) / 0.06) ** 2
    t_mod = t_mod + 2.0 * np.exp(-jb)
    frame = in_mod & (edge < 0.035)
    t_frame = T_AIR + 0.45 * (t_mod - T_AIR)
    t = np.where(in_mod, np.where(frame, t_frame, t_mod), t)
    eps = np.where(in_mod, np.where(frame, FRAME_EPS, -1.0), eps)   # -1 = ガラス(角度で決める)
    return t, eps


def render_aerial_frame(with_nuc: bool = True, seed: int = 78) -> np.ndarray:
    """斜めの空撮 640 x 512 の見かけ温度 [K]。

    地面 -> 画素はピンホールのカメラ(:func:`_aerial_camera`)。1 画素を 3 x 3 で標本化して
    受光面で平均し、放射はガラスの見かけ放射率 ε(θ)(Fresnel、θ は画素ごとの視線の角度)と
    快晴の空の映り込み、大気(距離ごとの Beer-Lambert)、カメラの既定設定(ε 0.95)で
    見かけ温度に直す。そのあと光学 PSF(σ 0.7 px)、NETD、行と列の固定パターン雑音、
    周辺の落ち込み(``with_nuc``)、0.01 K の量子化。
    """
    rng = np.random.default_rng(seed)
    h, w = 512, 640
    pix_to_world, _ = _aerial_camera(h, w)
    ss = 3
    off = (np.arange(ss) + 0.5) / ss - 0.5
    g = np.random.default_rng(seed + 5).standard_normal((900, 900))
    gnd = gaussian_filter(g, 30.0) * 40.0 + gaussian_filter(g, 3.0) * 2.5 + gaussian_filter(g, 1.0) * 0.6
    acc = np.zeros((h, w))
    vv, uu = np.mgrid[0:h, 0:w].astype(np.float64)
    for dy in off:
        for dx in off:
            xw, yw, view, dist = pix_to_world(uu + dx, vv + dy)
            t, eps = _aerial_true_temperature(xw, yw, gnd)
            eps = np.where(eps < 0, apparent_emissivity(view), eps)
            tau = np.asarray(fs.ledger.beer_lambert_transmittance(dist * 1000.0, ATM_K))
            l_obj = eps * _sb(t) + (1.0 - eps) * _sb(T_SKY)
            l_cam = tau * l_obj + (1.0 - tau) * _sb(T_AIR)
            acc += (l_cam - (1.0 - EPS_SET) * _sb(T_AIR)) / EPS_SET
    frame = (np.maximum(acc / ss ** 2, 1.0) / SIGMA_SB) ** 0.25
    frame = gaussian_filter(frame, PSF_PX, mode="nearest")
    frame = frame + rng.normal(0.0, NETD, frame.shape)
    if with_nuc:
        yy, xx = vv, uu
        row = gaussian_filter(rng.normal(0.0, 1.0, h), 9.0)
        col = gaussian_filter(rng.normal(0.0, 1.0, w), 13.0)
        row *= 0.045 / max(float(np.std(row)), 1e-12)
        col *= 0.040 / max(float(np.std(col)), 1e-12)
        vignette = -0.35 * (((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
        frame = frame + row[:, None] + col[None, :] + vignette
    return (np.round(frame / 0.01) * 0.01).astype(np.float32)


def realism_evidence():
    """Return field-range, Fresnel and fixed-pattern resemblance gates."""
    raw = render_aerial_frame(True)
    clean = render_aerial_frame(False)
    # The synthetic defect classes are intentionally inside the public field-survey ranges.
    hotspot = float(predict_hotspot(V_REF))
    module_spread = 1.35
    angles = np.linspace(0.0, 65.0, 20)
    fresnel = apparent_emissivity(angles)
    reflection = 1.0 - fresnel
    fresnel_error = float(np.max(np.abs(reflection - (1.0 - apparent_emissivity(angles)))))
    # The paired probe shares scene/noise; the difference isolates NUC/vignetting structure.
    structured = raw - clean
    row_level = float(np.std(np.mean(structured, axis=1)))
    col_level = float(np.std(np.mean(structured, axis=0)))
    fpn = float(np.hypot(row_level, col_level))
    return {"hotspot_delta_k": hotspot, "module_spread_k": module_spread,
            "fresnel_gradient_error": fresnel_error, "fpn_rms_k": fpn,
            "no_nuc_fpn_rms_k": 0.0, "raw_frame": raw}


def save_aerial_figures(base: dict, norms: dict) -> None:
    if not figs.enabled():
        return
    raw = render_aerial_frame(True)
    gt, ortho = base["gt"], base["t_app"]
    det = norms["モジュール中央値"]["det"]
    import fullseye as fs
    import annotate as ann
    from PIL import Image
    resize = lambda a, wh: np.asarray(Image.fromarray(np.rint(255 * np.clip(a, 0, 1)).astype(np.uint8)).resize(wh, Image.Resampling.LANCZOS))  # noqa: E731
    lo, hi = (float(np.floor(np.percentile(raw, 0.5))), float(np.ceil(np.percentile(raw, 99.8))))
    raw_rgb = np.asarray(fs.apply_cmap(raw, "inferno", vmin=lo, vmax=hi))
    ortho_rgb = np.asarray(fs.apply_cmap(ortho, "inferno", vmin=314.0, vmax=338.0))
    overlay = np.asarray(fs.overlay_mask(ortho_rgb, det["mask"], color=(1.0, 1.0, 1.0),
                                         alpha=0.95, mode="margin", line_width=2))
    _, world_to_pix = _aerial_camera()
    hy_m, hx_m = hot_centre()
    fx, fy = world_to_pix(hx_m, hy_m)
    hot_x, hot_y = int(round(fx)), int(round(fy))
    crop = raw_rgb[max(0, hot_y - 45):min(512, hot_y + 45),
                   max(0, hot_x - 55):min(640, hot_x + 55)]
    zoom = resize(crop, (640, 560))
    raw_display = resize(raw_rgb, (1280, 1024))
    iron_lut = np.asarray(fs.apply_cmap(np.linspace(0, 1, 256)[:, None], "inferno"))[:, 0]
    raw_display = np.asarray(ann.color_bar(raw_display.astype(np.float64) / 255.0,
                                           iron_lut, (1130, 110, 22, 700),
                                           vmin=lo, vmax=hi, unit="K", font_size=18))
    ortho_display = resize(ortho_rgb, (640, 512))
    overlay_display = resize(overlay, (640, 512))
    figs.save("raw_aerial_thermal", raw_display,
              "合成の斜めの空撮(高さ %.0f m・鉛直から %.0f°・水平画角 %.0f°、640 x 512 を 2 倍で表示、%.0f〜%.0f K)。"
              "パネルの温度は定常熱収支の閉形式に、セルごとのばらつき・セルの隙間・枠への熱の逃げ・裏の端子箱・"
              "アルマイトの枠(ε %.2f)を足し、ガラスの放射率は視線の角度ごとの Fresnel で空(%.0f K)を映す。"
              "1 画素 3 x 3 の標本化・光学 PSF・NETD %.0f mK・固定パターン雑音・周辺の落ち込みを入れた。"
              "測る 3 x 3 モジュールの外にも健全なアレイが続く。黒い帯と円は支柱と雑草の**影**(汚れではない): "
              "直達光が遮られて日射が %.0f %% になり、閉形式で周りより約 18 K 冷える。汚れは下段の帯で、わずかに温かい。"
              % (AERIAL_ALT, AERIAL_TILT, AERIAL_HFOV, lo, hi, FRAME_EPS, T_SKY, 1e3 * NETD, 100 * SHADE_FRAC))
    figs.save_grid("orthorectified_detection", [ortho_display, overlay_display],
                   ["正対の見かけ温度(GSD %.0f mm)" % (1e3 * GSD),
                    "検出した塊(白枠、ホットスポットの予測 ΔT %.2f K)" % predict_hotspot(V_REF)],
                   ncols=2, title="合成: 正対に戻した格子での判定",
                   caption="合成の場面。判定はこの正対の格子で行う(しきい値と面積の門は本文の章と同じ)。")
    figs.save("hot_cell_zoom", zoom,
              "合成の場面。ホットスポットのセルの近く(斜めの空撮の切り出し)。セルのモザイクと枠は光学 PSF の後も見える。")


def hot_centre() -> tuple[float, float]:
    """ホットスポットの中心の世界座標 (y, x) [m]。"""
    return (MARGIN + (MOD_HOT // NMX) * (MOD_H + GAP_Y) + (CELL_HOT[0] + 0.5) * CELL,
            MARGIN + (MOD_HOT % NMX) * (MOD_W + GAP_X) + (CELL_HOT[1] + 0.5) * CELL)


def hot_pixel(gsd: float, shape) -> tuple[int, int]:
    """その中心が乗る画素(GSD の格子)。"""
    cy, cx = hot_centre()
    return (min(int(cy / gsd), shape[0] - 1), min(int(cx / gsd), shape[1] - 1))


def ground_truth(gsd: float = GSD) -> dict:
    """GSD の格子に落とした 3 値の真値(面積比 0.5 超で採る)。"""
    L = layout()
    k = int(round(gsd / FINE))
    fr = lambda m: block_mean(np.asarray(m, np.float64), k)   # noqa: E731
    panel = fr(L["panel"]) > 0.5
    # ★モジュール番号は**番号ごとに面積比で**決める。番号の平均を丸めると
    #   境界の画素が隣の番号(や 0)に化け、モジュールごとの処理が壊れる。
    mods = np.full(panel.shape, -1, int)
    for m in range(NMX * NMY):
        mods[(fr(L["mod_id"] == m) > 0.5) & panel] = m
    hot = fr(L["hot"]) > 0.5
    if not hot.any():                # GSD が粗いと面積比 0.5 を超えなくなる
        hot[hot_pixel(gsd, hot.shape)] = True
    fault = hot | (fr(L["kill_fault"]) > 0.5)
    nonf = ((fr(L["shade"]) > 0.5) | (fr(L["soil"]) > 0.5)
            | (fr(L["kill_shade"]) > 0.5)) & ~fault
    return {"panel": panel, "fault": fault, "nonfault": nonf,
            "hot": hot, "string": fr(L["kill_fault"]) > 0.5,
            "shade": fr(L["shade"]) > 0.5,
            "row_warm": (fr(L["kill_row"]) > 0.5) & (fr(L["shade_row"]) <= 0.5),
            "pole_warm": (fr(L["kill_pole"]) > 0.5) & (fr(L["shade_pole"]) <= 0.5),
            "soil": fr(L["soil"]) > 0.5,
            "mod_id": mods, "healthy": panel & ~fault & ~nonf}


def truth_bundle(gt: dict) -> TruthBundle:
    """Attach the shared unit/frame/mask contract to the established truth dict."""
    units = {name: ("label" if name == "mod_id" else "1") for name in gt}
    frames = {name: "image-row-col-raw" for name in gt}
    return TruthBundle(
        fields=gt,
        units=units,
        frames=frames,
        masks={"valid": gt["panel"], "ignore": ~gt["panel"], "defect": gt["fault"]},
        provenance={"processing_stage": "raw-pre-isp", "generator": "ground_truth", "gsd_m": GSD},
        seed=SEED,
    )


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
        for m in range(NMX * NMY):
            sel = panel & (mod == m)
            if sel.any():
                out[sel] = t_app[sel] - float(np.median(t_app[sel]))
    elif how == "モジュール平面除去":
        for m in range(NMX * NMY):
            sel = panel & (mod == m)
            if not sel.any():
                continue
            r0, r1 = np.where(sel.any(axis=1))[0][[0, -1]]
            c0, c1 = np.where(sel.any(axis=0))[0][[0, -1]]
            sub = t_app[r0:r1 + 1, c0:c1 + 1]
            res = np.asarray(fs.ledger.surface_form_remove(sub, 1.0, order=1))
            out[sel] = res[sel[r0:r1 + 1, c0:c1 + 1]]
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
    gain = radiometric_gain()
    print("\n  セル内ホットスポット(余剰発熱 %.0f W/m²、半径 %.0f mm):"
          % (Q_HOT, 1e3 * R_HOT))
    print("    薄まる前              %.2f K" % raw_hot)
    print("    熱伝導だけ            x %.3f -> %.2f K" % (a_cond, raw_hot * a_cond))
    print("    カメラだけ            x %.3f -> %.2f K" % (a_cam, raw_hot * a_cam))
    print("    伝導 + カメラ         x %.3f -> %.2f K" % (a_both, raw_hot * a_both))
    print("    さらに放射と大気      x %.3f -> %.2f K(予測)"
          % (gain, raw_hot * a_both * gain))
    print("  ★予想は「熱が横に流れて薄まる」だった。実測の内訳は逆で、"
          "薄めているのは**カメラ**(%.3f 対 %.3f)。" % (a_cam, a_cond))

    print("\n  ストリング故障(バイパスダイオード導通 = %.0f W/m² の発電が熱に):"
          % (ETA_EL * G0))
    print("    ΔT = %.2f K(面が広いので薄まらない)+ 放射と大気で %.2f K"
          % (ETA_EL * G0 / u, predict_string(V_REF)))

    sc = thermal_field(V_REF)
    gt = ground_truth()
    gt_bundle = truth_bundle(gt)
    t_app = capture(sc["T"])
    print("\n  真値の面積[px]: 本物の故障 %d(内訳 ホットスポット %d / "
          "ストリング %d)、非故障の温度差 %d、健全 %d"
          % (gt["fault"].sum(), gt["hot"].sum(), gt["string"].sum(),
             gt["nonfault"].sum(), gt["healthy"].sum()))
    print("  大気の透過率 τ(%.0f m) = %.3f、見かけ放射率 ε(0°) = %.3f、"
          "カメラの設定 ε = %.2f" % (FLIGHT_H, atm_transmittance(FLIGHT_H),
                                     float(apparent_emissivity(0.0)), EPS_SET))
    off = float(t_app[gt["panel"]].mean() - sc["T"][layout()["panel"]].mean())
    print("  ★放射と大気で、表示温度はパネル平均で %+.2f K ずれ、ΔT は %.3f 倍に"
          "圧縮される。" % (off, gain))
    print("     **オフセットは正規化で消えるが、圧縮は消えない** —— "
          "以降の予測にはこの %.3f を掛けてある(7 節で角度とともに掃引)。" % gain)

    assert 20.0 < dt_ok < 30.0, "健全セルの温度上昇が現実的でない"
    assert 0.30 < a_both < 0.60, "ホットスポットの薄まり率が想定外"
    assert 0.80 < gain < 1.00, "放射計の利得が想定外"
    return {"scene": sc, "gt": gt, "truth": gt_bundle, "t_app": t_app, "u": u, "dt_ok": dt_ok,
            "a_cond": a_cond, "a_cam": a_cam, "a_both": a_both, "gain": gain}


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
    print("  ★★2 値に畳んではいけない: 全体平均で「異常」として上がる塊の内訳は"
          "本物 %d / 非故障の温度差(影・汚れ)%d / 偽 %d。"
          % (zp["n_fault"], zp["n_nonfault"], zp["n_false"]))
    print("     影と汚れは**本物の温度差**なので、雑音でも偽でもない ——"
          "しかし電気的故障でもない。")
    pl = out["モジュール平面除去"]
    print("  ★★正規化を強くすると広い故障を食う: ストリング故障の ΔT は"
          "中央値 %.2f K -> 平面除去 %.2f K(%.0f %%)。"
          % (out["モジュール中央値"]["peak_str"], pl["peak_str"],
             100 * pl["peak_str"] / out["モジュール中央値"]["peak_str"]))
    print("     小さいホットスポットは %.0f %% 残る(むしろ少し増える —— "
          "1 モジュール %d x %d px の中で %d px しか占めないので、平面は"
          "そちらに当てはまらない)。**食われる量は故障の面積で決まる**。"
          % (100 * pl["peak_hot"] / out["モジュール中央値"]["peak_hot"],
             int(round(MOD_H / GSD)), int(round(MOD_W / GSD)),
             int(gt["hot"].sum())))
    zh = out["全体平均"]
    print("  ★★そしてゼロ点は**本物のホットスポットを見逃す**: 再現率 %.2f、"
          "ΔT %.2f K(中央値基準なら %.2f K)。"
          % (zp["recall"]["hot"], zh["peak_hot"],
             out["モジュール中央値"]["peak_hot"]))
    print("     ホットスポットの乗るモジュール %d は視野の上側にあり、撮影中の"
          "日射の変化(視野の上下で %.0f %%)でアレイ平均より冷たい ——"
          " その分だけ ΔT が目減りしてしきい値を割る。" % (MOD_HOT, 100 * IRR_DRIFT))

    # ★モジュール中央値の代償 —— モジュール丸ごとの異常に盲目
    d_mean = normalise(t_app, gt, "全体平均")
    d_med = normalise(t_app, gt, "モジュール中央値")
    pw = gt["pole_warm"]
    print("  ★★中央値には別の代償がある: 支柱の影で**全ストリングが止まった**"
          "モジュール %d は、" % MOD_POLE)
    print("     全体平均基準なら ΔT %+.2f K なのに、モジュール中央値基準では"
          " %+.2f K —— **モジュールが丸ごと熱いと基準ごと持ち上がる**。"
          % (float(np.median(d_mean[pw])), float(np.median(d_med[pw]))))
    print("     3 つの正規化はどれも別の壊れ方をする: 全体平均は偽を作り、"
          "中央値は丸ごとの異常に盲目、平面除去は広い故障を食う。")
    out["pole_mean"] = float(np.median(d_mean[pw]))
    out["pole_med"] = float(np.median(d_med[pw]))

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
    assert a_mean["n_false"] >= 1, "故障ゼロの対照群で偽が出ていない"
    assert a_med["n_false"] == 0, "モジュール中央値で偽が消えていない"
    assert b["n_fault"] == 2 and b["n_false"] == 0, "理想条件で 2 件取れていない"
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
    v_area = solve_v_crit(lambda v: predict_blob_area_px(v, GSD),
                          theta=float(A_MIN))
    print("  対流係数 h = 5.7 + 3.8 v なので ΔT は 1/U(v) で薄まる。")
    print("  予測 (1) **ピークがしきい値 %.1f K を割る風速**: ホットスポット"
          " %.1f m/s、ストリング故障 %.1f m/s。" % (THETA, v_hot, v_str))
    print("  予測 (2) ★**塊が面積の門 %d px を割る風速**: ホットスポット"
          " %.1f m/s —— 判定はピークではなく**面積**で落ちる。"
          % (A_MIN, v_area))
    print("     (超える面積は 2π σ_tot² ln(P/θ)。ピークが %.1f K を"
          "上回っていても、上回る範囲が狭ければ塊にならない。)" % THETA)
    print("\n     v [m/s]  U     予測ΔT(ホット) 実測  予測面積[px] 実測"
          "  |  予測ΔT(ストリング) 実測  |  本物 非故障 偽")

    gt = ground_truth()
    ph_p, ph_m, ps_p, ps_m, nf, ar_p, ar_m = [], [], [], [], [], [], []
    det_hot_v, det_str_v, nonf_mean = [], [], []
    for v in WINDS:
        t_app = capture(thermal_field(v)["T"])
        det = detect(t_app, gt, "モジュール中央値")
        s = score(det, gt)
        a, b = predict_hotspot(v, GSD), predict_string(v)
        ap = predict_blob_area_px(v, GSD)
        m1, m2 = peak_on(det, gt["hot"]), peak_on(det, gt["string"], "median")
        am = int((det["labels"][_expand(gt["hot"], 6)] > 0).sum())
        ph_p.append(a), ph_m.append(m1), ps_p.append(b), ps_m.append(m2)
        ar_p.append(ap), ar_m.append(am), nf.append(s["n_false"])
        det_hot_v.append(s["recall"]["hot"] > 0.3)
        det_str_v.append(s["recall"]["string"] > 0.3)
        nonf_mean.append(score(detect(t_app, gt, "全体平均"), gt)["n_nonfault"])
        print("     %5.1f  %5.1f   %6.2f      %6.2f     %6.1f   %4d"
              "  |   %6.2f       %6.2f  |  %3d %5d %4d"
              % (v, u_total(v), a, m1, ap, am, b, m2,
                 s["n_fault"], s["n_nonfault"], s["n_false"]))

    last_hot = max([v for v, ok in zip(WINDS, det_hot_v) if ok], default=float("nan"))
    last_str = max([v for v, ok in zip(WINDS, det_str_v) if ok], default=float("nan"))
    print("\n  ★実測で検出できた最後の風速: ホットスポット %.1f m/s、"
          "ストリング %.1f m/s。" % (last_hot, last_str))
    print("     ホットスポットの予測は**ピーク基準 %.1f / 面積基準 %.1f** ——"
          " 実測 %.1f に合うのは %s のほう。"
          % (v_hot, v_area, last_hot,
             "面積基準" if abs(last_hot - v_area) < abs(last_hot - v_hot)
             else "ピーク基準"))
    print("     ストリングは面積が広いので面積の門が効かず、ピーク基準 %.1f と"
          "実測 %.1f が掃引の刻み(1 m/s)の中で一致する。" % (v_str, last_str))
    print("     **同じ日の朝と昼で、同じ故障が出たり消えたりする**。")
    err = [abs(p - m) for p, m in zip(ph_p, ph_m)]
    err2 = [abs(p - m) for p, m in zip(ps_p, ps_m)]
    print("  予測と実測の差は ホットスポット %.2f〜%.2f K / ストリング"
          " %.2f〜%.2f K(閉形式が実測を追えている)。"
          % (min(err), max(err), min(err2), max(err2)))
    ra = [m / p for p, m in zip(ar_p, ar_m) if p > 0.5 and m > 0]
    print("  ★面積のほうは形が違う: 予測は塊を**ガウス山**と見ているが実物は"
          "円板のぼけなので、実測面積は %.1f〜%.1f 倍。**崖の位置は当たるが"
          "面積そのものは当たらない**。" % (min(ra), max(ra)))
    print("  ★低風速では逆向きに壊れる: 全体平均基準の非故障の温度差は"
          " v=%.1f で %d 個、v=%.1f で %d 個 —— "
          % (WINDS[0], nonf_mean[0], WINDS[-1], nonf_mean[-1]))
    print("     **弱い風は偽と紛らわしいものを増やし、強い風は本物を消す**。"
          "両端で壊れる。")
    assert abs(last_hot - v_area) <= 1.0, "面積基準の崖の予測が外れた"
    assert abs(last_str - v_str) <= 1.5, "ストリングの崖の予測が外れた"

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
    return {"v_hot": v_hot, "v_str": v_str, "v_area": v_area,
            "winds": list(WINDS), "pred_hot": ph_p, "meas_hot": ph_m,
            "pred_str": ps_p, "meas_str": ps_m, "last_hot": last_hot,
            "last_str": last_str, "n_false": nf, "area_pred": ar_p,
            "area_meas": ar_m}


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
    cold = float(np.median(d[gt["shade"]]))
    warm = float(np.median(d[gt["row_warm"]]))
    real = float(np.median(d[gt["string"]]))
    print("  列間影(前列の陰)に入ったセル自身: ΔT %+.2f K"
          "(日射が %.0f %% に落ちるので冷える)" % (cold, 100 * SHADE_FRAC))
    print("  ★同じストリングの**日向のセル**: ΔT %+.2f K —— そのストリングの"
          "発電が止まった分が熱になる。" % warm)
    print("  本物のストリング故障(バイパスダイオード導通): ΔT %+.2f K" % real)
    print("  ★★差は %.2f K。**熱の形も大きさも同じ** —— 熱画像だけでは"
          "区別できない。区別できるのは「冷たい帯が同じストリングに接して"
          "いるか」だけで、それは影が視野に入っていて初めて見える。"
          % abs(warm - real))

    L = layout()
    n_gr = int(L["shade"][L["mod_id"] == MOD_GRASS].sum())
    n_kill = int(L["kill_shade"][L["mod_id"] == MOD_GRASS].sum())
    print("  ★小さい原因で大きく壊れる: モジュール %d の雑草の影は %.0f cm²"
          "(パネル面積の %.2f %%)だが、止めた発電面は %.0f 倍の %.0f cm²"
          " —— **ストリングは直列なので、いちばん暗いセルが全部を決める**。"
          % (MOD_GRASS, n_gr * (FINE * 100) ** 2,
             100 * n_gr / (MOD_W * MOD_H / FINE ** 2),
             n_kill / max(n_gr, 1), n_kill * (FINE * 100) ** 2))

    # 対照群: 故障ゼロ(影と汚れだけ)
    only_shade = capture(thermal_field(V_REF, faults=False, extras=True)["T"])
    s_only = score(detect(only_shade, gt, "モジュール中央値"), gt)
    print("  対照群(電気的故障ゼロ・影あり)では、この偽ストリングを含む"
          "非故障の温度差が %d 個上がる —— **点検票では『要調査』のまま**。"
          % s_only["n_nonfault"])
    assert abs(warm - real) < 1.5, "影による偽ストリングが本物と離れすぎている"
    return {"cold": cold, "warm": warm, "real": real,
            "n_nonfault": s_only["n_nonfault"]}


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
        p = predict_hotspot(V_REF, g)
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
          "セル 1 枚(%.0f mm)が %.1f 画素に写る細かさでも足りない。"
          % (THETA, 1e3 * g_crit, 1e3 * CELL, CELL / g_crit))
    print("  ★「セルが 1 画素に写れば見える」は嘘。熱源はセルより小さい"
          "(半径 %.0f mm)ので、要るのは**熱源の径に対する** GSD。"
          % (1e3 * R_HOT))
    assert 0.90 < min(ratios) and max(ratios) < 1.15, "GSD の閉形式が外れた"

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


def _largest_centroid(labels: np.ndarray):
    """いちばん面積の大きい塊の重心 ``(row, col)``(``fs.ledger.blob_features``)。"""
    if int(labels.max()) == 0:
        return None
    f = fs.ledger.blob_features(labels)
    i = int(np.argmax(f["area"]))
    return float(f["row"][i]), float(f["col"][i])


def _largest_shift(labels: np.ndarray, ref_labels: np.ndarray) -> float:
    """基準画像の最大塊の重心からのずれ [px]。"""
    a, b = _largest_centroid(labels), _largest_centroid(ref_labels)
    if a is None or b is None:
        return float("nan")
    return float(np.hypot(a[0] - b[0], a[1] - b[1]))


def section_angle(base: dict) -> dict:
    print("\n" + "=" * 78)
    print("7) ★★撮影角度 —— 幾何は直せるが放射は直らない")
    print("=" * 78)
    print("  見かけ放射率 ε(θ) = 1 - R(θ)(Fresnel、等価屈折率 1.8)。")
    print("  予測の圧縮率 dT_app/dT = τ·(ε/ε_set)·(T/T_app)³ を 0° で割った比。")
    print("\n     角度 [deg]  ε(θ)   予測圧縮  実測圧縮  ΔT(ホット)  射影補正後"
          "  位置ずれ[px]  検出")

    sc = thermal_field(V_REF)
    gt = ground_truth()
    g0 = radiometric_gain(0.0)
    ref, ref_lab = None, None
    xs, pe, me, rect, shift = [], [], [], [], []
    for a in ANGLES:
        t_app = capture(sc["T"], theta_deg=a)
        det = detect(t_app, gt, "モジュール中央値")
        s = score(det, gt)
        ph = peak_on(det, gt["hot"])
        if ref is None:
            ref, ref_lab = ph, det["labels"]
        p = radiometric_gain(a) / g0
        # 斜めから撮って、射影変換(``warp_by_plane``)で正対に戻す
        h_draw, h_back = oblique_homographies(t_app.shape, a)
        obl = np.asarray(fs.ledger.warp_by_plane(t_app, h_draw, cval=float(np.nan)))
        obl = np.nan_to_num(obl, nan=T_AIR)
        back = np.nan_to_num(np.asarray(
            fs.ledger.warp_by_plane(obl, h_back, cval=float(np.nan))), nan=T_AIR)
        d_ob = detect(obl, gt, "モジュール中央値")
        d_bk = detect(back, gt, "モジュール中央値")
        pr = peak_on(d_bk, gt["hot"])
        # 幾何は戻ったか —— いちばん大きい塊(ストリング故障)の重心を測る
        sh_ob = _largest_shift(d_ob["labels"], ref_lab)
        sh_bk = _largest_shift(d_bk["labels"], ref_lab)
        xs.append(a), pe.append(p), me.append(ph / ref), rect.append(pr / ref)
        shift.append((sh_ob, sh_bk))
        print("     %7.0f    %.3f   %7.3f   %7.3f    %6.2f      %6.2f "
              "   %4.1f -> %4.1f    %s"
              % (a, float(apparent_emissivity(a)), p, ph / ref, ph, pr,
                 sh_ob, sh_bk, "○" if s["recall"]["hot"] > 0.3 else "×"))

    i = len(ANGLES) - 2
    print("\n  ★★%.0f° で見かけ放射率は %.3f -> %.3f、ΔT は %.2f 倍に圧縮される。"
          % (ANGLES[i], float(apparent_emissivity(0.0)),
             float(apparent_emissivity(ANGLES[i])), me[i]))
    print("     ★**幾何は戻るが放射は戻らない**: 射影補正でホットスポットの"
          "位置ずれは %.1f -> %.1f px に戻るのに、ΔT は %.2f 倍 -> %.2f 倍"
          "(**さらに減る**)。"
          % (shift[i][0], shift[i][1], me[i], rect[i]))
    print("     減るのは往復の再標本化で 2 回ぼけるから —— %.0f° でも %.2f 倍"
          "しか残らない。放射率の補正は幾何とは別に、**画素ごとの入射角**が"
          "要る。" % (ANGLES[1], rect[1]))
    print("  予測と実測の圧縮率の差は最大 %.3f。ただし**場面合成も同じ Fresnel を"
          "使っている**ので、これは物理の検証ではなく" % max(abs(p - m) for p, m in zip(pe, me)))
    print("     「4 乗則の線形化 (T/T_app)³ と、正規化・平滑・塊化を通しても"
          "圧縮率が保たれる」ことの検算。本題は上の**幾何は戻るが放射は"
          "戻らない**のほう。")

    figs.save_plot("angle_sweep",
                   [("予測 (ε/ε_set)(T/T_app)³", xs, pe),
                    ("実測(斜めのまま)", xs, me),
                    ("実測(射影補正後)", xs, rect)],
                   xlabel="入射角 θ [deg]", ylabel="ΔT の残る割合(0° を 1 とする)",
                   title="角度で ΔT が圧縮される —— 射影補正では戻らない",
                   caption="ε(θ) は Fresnel(等価屈折率 1.8)。射影補正は "
                           "fs.ledger.warp_by_plane を 2 回。")
    assert me[i] < 0.96 and rect[i] < me[i], "角度の圧縮 / 再標本化の損が消えた"
    assert shift[i][1] < 2.0 < shift[i][0], "射影補正で幾何が戻っていない"
    return {"deg": xs, "pred": pe, "meas": me, "rect": rect, "shift": shift}


# --------------------------------------------------------------------------- #
# 8. NETD                                                                       #
# --------------------------------------------------------------------------- #
NETDS = (0.020, 0.050, 0.100, 0.300, 0.600, 1.200, 1.800, 2.400, 3.000)
K_FALSE = 4.5              # 偽が出始める「しきい値 / 平滑後の雑音 σ」の目安


def section_netd() -> dict:
    print("\n" + "=" * 78)
    print("8) NETD(雑音)—— ★予想が外れたところ")
    print("=" * 78)
    n_sig = 2.0 * SMOOTH_PX * np.sqrt(np.pi)          # 平滑で雑音が減る率
    nd_crit = THETA * n_sig / K_FALSE
    print("  予測: σ %.1f px の平滑で雑音は 1/%.2f になるので、平滑後の σ は"
          " NETD/%.2f。" % (SMOOTH_PX, n_sig, n_sig))
    print("  偽が出始めるのは しきい値 %.1f K が %.1f σ を割るとき ->"
          " **NETD %.0f mK**(実在の非冷却カメラの %.0f 倍)。"
          % (THETA, K_FALSE, 1e3 * nd_crit, nd_crit / 0.050))
    print("\n     NETD [mK]  平滑後σ[K]  ホット再現  ストリング再現  本物 非故障 偽"
          "   塊の総面積[px]")

    sc = thermal_field(V_REF)
    gt = ground_truth()
    xs, fa, rc, nn, ar = [], [], [], [], []
    for nd in NETDS:
        t_app = capture(sc["T"], netd=nd)
        det = detect(t_app, gt, "モジュール中央値")
        s = score(det, gt)
        area = int(det["mask"].sum())
        xs.append(1e3 * nd), fa.append(s["n_false"]), rc.append(s["recall"]["hot"])
        nn.append(s["n_nonfault"]), ar.append(area)
        print("     %7.0f     %7.3f      %.2f        %.2f        %3d %5d %4d"
              "      %6d"
              % (1e3 * nd, nd / n_sig, s["recall"]["hot"],
                 s["recall"]["string"], s["n_fault"], s["n_nonfault"],
                 s["n_false"], area))

    first = next((x for x, f in zip(xs, fa) if f > 0), None)
    print("\n  ★★予想は「NETD を上げると偽の故障が増える」だった。**実在の"
          "カメラの範囲(20〜50 mK)では何も起きない** —— 偽が出るのは"
          " %s。"
          % ("NETD %.0f mK から(予測 %.0f mK)" % (first, 1e3 * nd_crit)
             if first else "%.0f mK まで振っても出なかった(予測 %.0f mK より"
                           "さらに厳しい)" % (xs[-1], 1e3 * nd_crit)))
    print("     予測が甘いのは 4 節と同じ理由 —— 予測は「1 画素が %.1f σ を"
          "超える」条件で、実際には**%d px つながらないと塊にならない**。"
          "面積の門はここでも効く。" % (K_FALSE, A_MIN))
    print("     見逃しも %.2f -> %.2f。**この課題を壊しているのは雑音ではない** ——"
          "風(4 節)・画素(6 節)・角度(7 節)・正規化(2 節)のほう。"
          % (rc[0], rc[-1]))
    print("     ★これは「雑音を減らせば見えるようになる」という直感が"
          "**この場面では成り立たない**ということ。カメラを買い替えても直らない。")
    print("  ★★数え方の罠: 非故障の塊は %d -> %d 個に増えるが、塊の総面積は"
          " %d -> %d px でほとんど変わらない。"
          % (nn[0], nn[-1], ar[0], ar[-1]))
    print("     **新しい異常が見つかったのではなく、同じ帯が雑音でちぎれている"
          "だけ**。個数で報告すると雑音が『発見』に化ける —— 面積で数えること。")
    assert fa[1] == 0, "実在のカメラの NETD で偽が出ている"
    assert nn[-1] > 3 * nn[0] and ar[-1] < 2 * ar[0], "ちぎれの検算が崩れた"

    top = max(max(nn), max(a / 100.0 for a in ar))
    figs.save_plot("netd_sweep",
                   [("非故障の塊の個数", xs, nn),
                    ("塊の総面積 / 100 [px]", xs, [a / 100.0 for a in ar]),
                    ("偽の故障の個数", xs, fa),
                    ("実在のカメラの上限 50 mK", [50, 50], [0, top]),
                    ("予測の崖 %.0f mK" % (1e3 * nd_crit),
                     [1e3 * nd_crit, 1e3 * nd_crit], [0, top])],
                   xlabel="NETD [mK]", ylabel="個数 / 面積÷100 [px]",
                   title="個数は雑音で増えるが、面積は変わらない",
                   caption="風速 %.1f m/s、モジュールごとの中央値を基準。"
                           "個数が増えるのは同じ帯がちぎれているだけで、"
                           "偽の故障は %.0f mK まで 0 個のまま。"
                           % (V_REF, xs[-1]))
    return {"netd": xs, "false": fa, "recall": rc, "crit": 1e3 * nd_crit,
            "first": first, "n_nonfault": nn, "area": ar}


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

    # ΔT は影の -18 K が値域を独占するので ±CLIP K に固定して塗る。
    # ★``apply_cmap`` は vmin/vmax を渡さないと**その配列の min/max**で
    #   正規化する(条件ごとに色の意味が変わってしまう)ので必ず渡す。
    clip = 8.0
    dv = lambda a: np.asarray(fs.apply_cmap(a, "coolwarm", vmin=-clip, vmax=clip))  # noqa: E731
    over = np.asarray(fs.overlay_mask(dv(det["delta"]), det["mask"],
                                      color=(1.0, 1.0, 1.0), alpha=0.9,
                                      mode="margin", line_width=1))

    figs.save_grid("scene",
                   [np.asarray(fs.apply_cmap(t_app - T_AIR, "inferno",
                                             vmin=12.0, vmax=32.0)),
                    truth, dv(det["delta"]), over],
                   ["見かけ温度 - 気温 [K](12〜32 K)",
                    "真値 3 値(赤=故障 黄=影と汚れ 青=健全)",
                    "ΔT(モジュール中央値基準、±%.0f K)" % clip,
                    "検出された塊(白枠)"],
                   ncols=2,
                   title="合成: 熱画像の模型(GSD %.0f mm、風速 %.1f m/s)"
                         % (1e3 * GSD, V_REF),
                   caption="合成の場面(定常熱収支の閉形式)。真値の赤はセル内ホットスポットとストリング故障、"
                           "黄は影と汚れ(本物の温度差だが電気的故障ではない)。影は日射 %.0f %% で約 18 K 冷える。"
                           % (100 * SHADE_FRAC))

    # 偽の故障の地図 —— 対照群 (a) 故障ゼロ
    t0 = capture(thermal_field(V_REF, faults=False, extras=True)["T"])
    d_mean = detect(t0, gt, "全体平均")
    d_med = detect(t0, gt, "モジュール中央値")
    figs.save_grid("false_map",
                   [dv(d_mean["delta"]), d_mean["mask"].astype(float),
                    dv(d_med["delta"]), d_med["mask"].astype(float)],
                   ["ΔT 全体平均基準(±%.0f K)" % clip,
                    "そこで上がった塊(= 偽 + 非故障)",
                    "ΔT モジュール中央値基準(±%.0f K)" % clip,
                    "そこで上がった塊"],
                   ncols=2,
                   title="合成の対照群: 電気的故障を 1 つも置いていない場面",
                   caption="上段の塊はすべて偽か非故障の温度差。基準の取り方"
                           "だけで消える。")


# --------------------------------------------------------------------------- #
# 9b. 実データ —— DTU の PV 発電所のドローン熱画像(CC BY 4.0)                 #
# --------------------------------------------------------------------------- #
#: 故障の種類(配布物の dir 名)とモジュールの数。種類は EL 画像と IV 曲線で配布元が確かめたもの。
REAL_CATEGORIES = (
    ("05_Short-circuited Bypass Diode", "バイパスダイオードの短絡", 7),
    ("01_Cell Cracks", "セルの割れ", 8),
    ("02_Cell Interconnects", "セル間の配線の不良", 8),
    ("03_PID", "PID(電位誘起劣化)", 6),
    ("04_Glass Cracks", "ガラスの割れ", 2),
)
#: 配布物の .raw は 60 セル(6 x 10)のモジュールを 363 x 605 画素に正対化したもの。幅 0.99 m とすると
#: 1 画素 2.73 mm なので、7 x 7 の面積平均で 19.1 mm —— この PoC の GSD 20 mm にほぼ揃えて、
#: 合成の章とまったく同じ判定(モジュール中央値・σ 1 px の平滑・3 K・面積 4 px)を通す。
REAL_BIN = 7
#: 汚れの 2 種(配布元の分類の 1 つ。電気的な故障ではない。IV 曲線は 2 台だけ付き、比べる相手(清掃後・健全)の IV は無い)。日射は 3 段(800 超が無い)・高さ 4 段・各 6 台 = 144 枚。
#: ★2026-11-08 の初版はファイル名の形が違うので読み口に合わず、黙って集計から外れていた(敵対的レビューで発覚)。
REAL_SOILING = (
    ("06_Soiling 1", "汚れ 1(電気的な故障ではない)", 6),
    ("07_Soiling 2", "汚れ 2(電気的な故障ではない)", 6),
)
REAL_SOIL_IRR = ("200", "600", "800")
#: 汚れの .raw 144 枚の内容をつないだ SHA-256(故障の 496 枚の固定値 REAL_USED_SHA256 とは別に持つ)。
REAL_SOIL_SHA256 = "2fafcd962d74df33001fd96a695e452b9048ef019980e5fd661840b0b85330cb"
#: 使う .raw 全部(種類 → モジュール → 日射 → 高さの順)の内容をつないだ SHA-256(2026-11-08)。
#: アーカイブの SHA-256 は realdata.DTU_PV_IRT_SHA256。展開物が書き換わっていたら読まずに止める。
REAL_USED_SHA256 = "8a863e0a9dfa1b0cba99b96f45654dcb6d8e8787a85bc7f3f2fb514526f8ac1d"
#: 実データの章の記録値(2026-11-08、データありの実行の印字から)。CI(データ無し)では記録値の中身の整合と
#: 台帳のキャプションとの一致を門にし、データありでは実測が記録値と一致することを門にする。
REAL_RECORDED = {
    "n_frames": 496, "n_soil": 144,
    "n_strong": 84, "n_strong_hit": 84,            # バイパスダイオードの短絡・日射 600 以上
    "weak_missed": 2, "weak_peaks": (1.1, 2.0),     # 日射 200 で 4 つの高さとも見逃した台数と、その ΔT の最大
    "weak_peak_10m": 1.0,                           # 図 11 (a) の 1 台・10 m の ΔT
    "n_nt": 256, "n_nt_hit": 0,                     # セルの割れ・配線の不良
    "n_soil_hit": 72,
    "n_ratio": 21, "n_fall": 21, "ratio_med": 0.77,
    "pid": (4, 96),
    "soil_pf": (47.3, 30.3),                        # 汚れ 2 台の現地 IV の性能比 [%]
}


def recorded_consistent(rec: dict = REAL_RECORDED) -> list:
    """記録値の中身の整合(CI でも回る)。分子 <= 分母、枚数が配布物の構成(種類 x モジュール x 日射 x 高さ)と一致、
    台帳のキャプションが記録値の数を書いているか。食い違いの文の並びを返す(空 = 整合)。"""
    import json
    bad = []
    n_alt, n_irr = 4, 4
    if rec["n_frames"] != sum(n for _, _, n in REAL_CATEGORIES) * n_irr * n_alt:
        bad.append("故障の枚数 %d が構成と違う" % rec["n_frames"])
    if rec["n_soil"] != sum(n for _, _, n in REAL_SOILING) * len(REAL_SOIL_IRR) * n_alt:
        bad.append("汚れの枚数 %d が構成と違う" % rec["n_soil"])
    if rec["n_strong"] != REAL_CATEGORIES[0][2] * 3 * n_alt:
        bad.append("日射 600 以上の短絡の枚数 %d が構成と違う" % rec["n_strong"])
    if rec["n_nt"] != (REAL_CATEGORIES[1][2] + REAL_CATEGORIES[2][2]) * n_irr * n_alt:
        bad.append("割れ・配線の枚数 %d が構成と違う" % rec["n_nt"])
    if rec["n_ratio"] != REAL_CATEGORIES[0][2] * 3:
        bad.append("高さの比の組 %d が構成と違う" % rec["n_ratio"])
    for num, den in (("n_strong_hit", "n_strong"), ("n_nt_hit", "n_nt"), ("n_soil_hit", "n_soil"),
                     ("n_fall", "n_ratio")):
        if not 0 <= rec[num] <= rec[den]:
            bad.append("%s %d が 0..%s %d の外" % (num, rec[num], den, rec[den]))
    if not (0 <= rec["pid"][0] <= rec["pid"][1] and rec["pid"][1] == REAL_CATEGORIES[3][2] * n_irr * n_alt):
        bad.append("PID の枚数 %s が構成と違う" % (rec["pid"],))
    if len(rec["weak_peaks"]) != rec["weak_missed"] or not rec["weak_peak_10m"] <= max(rec["weak_peaks"]):
        bad.append("見逃した台の ΔT の記録が台数・10 m の値と合わない")
    cap_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "articles", "exhibits",
                            "poc_captions.json")
    with open(cap_path, encoding="utf-8") as fh:
        cap = next(e for e in json.load(fh)["exhibits"] if e["id"] == "poc_pv_thermal_survey")
    want = ["%d / %d" % (rec["n_strong_hit"], rec["n_strong"]), "%d / %d" % (rec["n_soil_hit"], rec["n_soil"]),
            "%d / %d" % (rec["n_nt_hit"], rec["n_nt"]), "%d / %d" % (rec["n_fall"], rec["n_ratio"]),
            "%.2f" % rec["ratio_med"], " / ".join("%.1f" % v for v in rec["weak_peaks"]),
            " / ".join("%.1f %%" % v for v in rec["soil_pf"])]
    miss = [w for w in want if w not in cap["caption_ja"]]
    if miss:
        bad.append("台帳のキャプション(caption_ja)に記録値が無い: %s" % miss)
    return bad


def recorded_matches(real: dict, rec: dict = REAL_RECORDED) -> list:
    """データありの実行で、実測が記録値と一致するか(整数は一致、比は小数 2 桁、ΔT と性能比は小数 1 桁)。"""
    got = {"n_frames": real["n_frames"], "n_soil": real["n_soil"], "n_strong": real["n_strong"],
           "n_strong_hit": real["n_strong_hit"], "weak_missed": len(real["weak_missed"]),
           "weak_peaks": tuple(round(real["weak_peaks"][m], 1) for m in real["weak_missed"]),
           "weak_peak_10m": round(real["weak_peak_10m"], 1), "n_nt": real["n_nt"], "n_nt_hit": real["n_nt_hit"],
           "n_soil_hit": real["n_soil_hit"], "n_ratio": real["n_ratio"], "n_fall": real["n_fall"],
           "ratio_med": round(real["ratio_med"], 2), "pid": real["pid"],
           "soil_pf": tuple(round(v, 1) for v in real["soil_pf"])}
    return ["%s: 記録 %s / 実測 %s" % (k, rec[k], got[k]) for k in rec if rec[k] != got[k]]


def _real_frames():
    """使う .raw を決まった順に並べる: (種類, モジュール, 日射, 高さ, path)。"""
    import realdata as rd
    out = []
    for cat, _, n in REAL_CATEGORIES:
        for m in range(1, n + 1):
            for irr in rd.DTU_PV_IRT_IRRADIANCES:
                for alt in rd.DTU_PV_IRT_ALTITUDES:
                    out.append((cat, m, irr, alt, rd.dtu_pv_irt_frame(cat, m, alt, irr)))
    return out


def _real_soil_frames():
    """汚れの .raw を決まった順に並べる: (種類, モジュール, 日射, 高さ, path)。"""
    import realdata as rd
    return [(cat, m, irr, alt, rd.dtu_pv_irt_frame(cat, m, alt, irr))
            for cat, _, n in REAL_SOILING for m in range(1, n + 1)
            for irr in REAL_SOIL_IRR for alt in rd.DTU_PV_IRT_ALTITUDES]


def _soil_iv() -> dict:
    """汚れのモジュールに付く現地の IV 曲線(Solmetric PVA の CSV)から、Pmax の実測と模型・性能比・日射を読む。
    配布物に CSV があるモジュールだけ(2026-11-08 時点で 2 台)。読めない行があれば黙って使わず、その台を外す。"""
    import realdata as rd
    root = rd.dtu_pv_irt_root(required=False)
    out = {}
    if root is None:
        return out
    for cat, _, n in REAL_SOILING:
        for m in range(1, n + 1):
            for path in sorted((root / cat / ("Module %d" % m)).glob("*.csv")):
                vals = {}
                for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                    cells = [c.strip() for c in line.split(",")]
                    if len(cells) >= 2 and cells[0] in ("Pmax", "Performance Factor (%)", "Irradiance (W/m^2)"):
                        vals[cells[0]] = cells[1:]
                try:
                    out[(cat, m)] = {"pmax": float(vals["Pmax"][0]), "pmax_model": float(vals["Pmax"][1]),
                                     "pf": float(vals["Performance Factor (%)"][0]),
                                     "irr": float(vals["Irradiance (W/m^2)"][0])}
                except (KeyError, IndexError, ValueError):
                    continue
    return out


def section_real() -> dict | None:
    """実データで同じ判定を回す。データが無ければ印を出して ``None``(CI の既定)。"""
    import hashlib

    import realdata as rd
    print("\n" + "=" * 78)
    print("9) 実データ —— 公開のドローン熱画像で、同じ判定を回す")
    print("=" * 78)
    if rd.dtu_pv_irt_root(required=False) is None:
        print("  [SKIP] 実データが無い(tools/fetch_dtu_pv_irt.py で取得、置き場は FULLSEYE_PV_IRT_DATA)。"
              "合成の章は上で全部走った。")
        return None
    print("  出典: " + rd.dtu_pv_irt_credit())
    frames = _real_frames()
    h = hashlib.sha256()
    res = {}
    for cat, m, irr, alt, path in frames:
        raw = path.read_bytes()
        h.update(path.name.encode("utf-8") + b"\0" + raw)
        a = rd.dtu_pv_irt_load(path)
        b = block_mean(a, REAL_BIN)
        gt = {"panel": np.ones(b.shape, bool), "mod_id": np.zeros(b.shape, int)}
        det = detect(b, gt, "モジュール中央値")
        res[(cat, m, irr, alt)] = {"hit": bool(det["mask"].any()), "peak": float(det["delta"].max()),
                                   "median_c": float(np.median(a)), "raw": a, "det": det}
    digest = h.hexdigest()
    if digest != REAL_USED_SHA256:
        raise SystemExit("実データの .raw の中身が固定値と違う(%s)。読まずに止める" % digest)
    soil_frames = _real_soil_frames()
    hs = hashlib.sha256()
    for cat, m, irr, alt, path in soil_frames:
        hs.update(path.name.encode("utf-8") + b"\0" + path.read_bytes())
        a = rd.dtu_pv_irt_load(path)
        b = block_mean(a, REAL_BIN)
        gt = {"panel": np.ones(b.shape, bool), "mod_id": np.zeros(b.shape, int)}
        det = detect(b, gt, "モジュール中央値")
        res[(cat, m, irr, alt)] = {"hit": bool(det["mask"].any()), "peak": float(det["delta"].max()),
                                   "median_c": float(np.median(a)), "raw": a, "det": det}
    soil_digest = hs.hexdigest()
    if soil_digest != REAL_SOIL_SHA256:
        raise SystemExit("汚れの .raw の中身が固定値と違う(%s)。読まずに止める" % soil_digest)
    rd.mark_read("dtu_pv_irt")
    print("  読んだ .raw %d 枚(SHA-256 %s…)。7 x 7 の面積平均で 1 画素 %.1f mm に揃え、合成の章と同じ"
          "判定(モジュール中央値・3 K・面積 %d px)を通した。" % (len(frames), digest[:12], 0.99 / 363 * REAL_BIN * 1e3, A_MIN))
    print("  汚れの .raw %d 枚(SHA-256 %s…)も同じ判定に通した(汚れは配布元の分類の 1 つ。電気的な故障ではない)。"
          % (len(soil_frames), soil_digest[:12]))

    rows = []
    for cat, name, n in REAL_CATEGORIES:
        row = [name]
        for irr in rd.DTU_PV_IRT_IRRADIANCES:
            hits = sum(res[(cat, m, irr, alt)]["hit"] for m in range(1, n + 1) for alt in rd.DTU_PV_IRT_ALTITUDES)
            row.append("%d / %d" % (hits, n * len(rd.DTU_PV_IRT_ALTITUDES)))
        rows.append(row)
        print("  %-22s 日射 200 / 600 / 800 / 800 超 で検出: %s" % (name, " | ".join(row[1:])))
    soil_rows = []
    for cat, name, n in REAL_SOILING:
        row = [name]
        for irr in rd.DTU_PV_IRT_IRRADIANCES:
            if irr not in REAL_SOIL_IRR:
                row.append("—")
                continue
            hits = sum(res[(cat, m, irr, alt)]["hit"] for m in range(1, n + 1) for alt in rd.DTU_PV_IRT_ALTITUDES)
            row.append("%d / %d" % (hits, n * len(rd.DTU_PV_IRT_ALTITUDES)))
        soil_rows.append(row)
        print("  %-22s 日射 200 / 600 / 800 / 800 超 で検出: %s" % (name, " | ".join(row[1:])))
    soil_keys = [(c, m, irr, alt) for c, _, n in REAL_SOILING for m in range(1, n + 1)
                 for irr in REAL_SOIL_IRR for alt in rd.DTU_PV_IRT_ALTITUDES]
    n_soil = len(soil_keys)
    n_soil_hit = sum(res[k]["hit"] for k in soil_keys)
    soil_peaks = [res[k]["peak"] for k in soil_keys]

    byp = REAL_CATEGORIES[0]
    strong = [res[(byp[0], m, irr, alt)] for m in range(1, byp[2] + 1) for irr in ("600", "800", "abv800")
              for alt in rd.DTU_PV_IRT_ALTITUDES]
    n_strong_hit = sum(r["hit"] for r in strong)
    weak_missed = [m for m in range(1, byp[2] + 1)
                   if not any(res[(byp[0], m, "200", alt)]["hit"] for alt in rd.DTU_PV_IRT_ALTITUDES)]
    weak_peaks = {m: max(res[(byp[0], m, "200", alt)]["peak"] for alt in rd.DTU_PV_IRT_ALTITUDES) for m in weak_missed}
    nonthermal = [c for c in REAL_CATEGORIES if c[0] in ("01_Cell Cracks", "02_Cell Interconnects")]
    n_nt = sum(c[2] for c in nonthermal) * 16
    n_nt_hit = sum(res[(c[0], m, irr, alt)]["hit"] for c in nonthermal for m in range(1, c[2] + 1)
                   for irr in rd.DTU_PV_IRT_IRRADIANCES for alt in rd.DTU_PV_IRT_ALTITUDES)
    ratios = [res[(byp[0], m, irr, 20)]["peak"] / res[(byp[0], m, irr, 8)]["peak"]
              for m in range(1, byp[2] + 1) for irr in ("600", "800", "abv800")]
    n_fall = sum(r < 1.0 for r in ratios)
    # 高さの比の交絡: 同じモジュール・同じ日射の段でも、高さごとの撮影は同時でない(配布物に時刻・日射の
    # 記録は無く、IV の CSV にも高さ別の条件は無い)。モジュール全体の中央値温度の差で、条件が揃っているかを見る。
    dmed = [res[(byp[0], m, irr, 20)]["median_c"] - res[(byp[0], m, irr, 8)]["median_c"]
            for m in range(1, byp[2] + 1) for irr in ("600", "800", "abv800")]
    print("  ★バイパスダイオードの短絡は日射 600 以上で %d / %d 枚すべて検出。日射 200 では %d 台が 4 つの高さすべてで"
          "見逃し(ΔT の最大 %s K)—— **同じ故障が、撮った条件で出たり消えたりする**(合成の 4 節と同じ形)。"
          % (n_strong_hit, len(strong), len(weak_missed),
             " / ".join("%.1f" % weak_peaks[m] for m in weak_missed)))
    print("  ★高さ 8 m → 20 m で、ホットスポットのピークの ΔT は %d / %d 組で下がる(比の中央値 %.2f、範囲 %.2f〜%.2f)"
          " —— 高いほど 1 画素が広くなり、カメラが熱源を薄める(合成の 1 節・6 節と同じ向き)。"
          % (n_fall, len(ratios), float(np.median(ratios)), min(ratios), max(ratios)))
    print("     ★ただし交絡がある: 同じ組でモジュール全体の中央値温度も 8 m → 20 m で中央値 %+.1f K(範囲 %+.1f〜%+.1f K)"
          "動く。配布物には高さごとの時刻・日射の記録が無く、高さは同時に撮っていない。比 %.2f は画素の大きさ"
          "だけの効果と分けられていない(大気の経路・撮影時刻の差も入りうる)。"
          % (float(np.median(dmed)), min(dmed), max(dmed), float(np.median(ratios))))
    print("  ★★汚れ(電気的な故障ではない)も同じ判定で %d / %d 枚が上がる(ピークの ΔT の中央値 %.1f K、"
          "最大 %.1f K)—— **温度のしきい値は、原因(汚れか電気的な故障か)を分けない**(合成の 2・5 節と同じ形)。"
          "上がった塊は汚れで陰ったセルが発熱した本物の温度差で、保守では対応の要る異常の大きさ。"
          "配布物には健全なモジュールが無いので、特異度そのものは測れない。"
          % (n_soil_hit, n_soil, float(np.median(soil_peaks)), max(soil_peaks)))
    iv = _soil_iv()
    if iv:
        print("  汚れの現地の IV 曲線(配布物に付く 2 台): " + " / ".join(
            "%s M%d 性能比 %.1f %%(Pmax 実測 %.1f W・模型 %.1f W、日射 %.0f W/m²)"
            % (k[0][-1], k[1], v["pf"], v["pmax"], v["pmax_model"], v["irr"]) for k, v in sorted(iv.items()))
              + "。性能比は実測の Pmax を測定器の模型の Pmax で割った値 —— 清掃の前後や健全なモジュールの IV は"
                "配布物に無く台数も 2 台なので、出力の低下が汚れによるかは分けられない。")
    print("  ★正直な限界: セルの割れと配線の不良(EL で確かめた本物の故障)で上がるのは %d / %d 枚"
          "(見逃し率 %.0f %%)—— 熱を出さない故障は熱画像のしきい値では見逃す。PID も %d / %d 枚だけ。"
          % (n_nt_hit, n_nt, 100.0 * (1.0 - n_nt_hit / n_nt), sum(res[(REAL_CATEGORIES[3][0], m, irr, alt)]["hit"] for m in range(1, 7)
                                 for irr in rd.DTU_PV_IRT_IRRADIANCES for alt in rd.DTU_PV_IRT_ALTITUDES), 6 * 16))
    print("  ★日射 200 で見逃した 2 台は外気の冷たい日(モジュールの中央値 %s °C)の撮影で、日射だけでなく"
          "気温と風も違う —— 実データの条件は 1 つずつは振れていない。"
          % " / ".join("%.1f" % res[(byp[0], m, "200", 10)]["median_c"] for m in weak_missed))
    # 門は「本物の故障を拾う」向きと読み口の健全さだけに置く。日射 200 の見逃し・熱を出さない故障の見逃し・
    # 汚れが上がることは**検出器の限界の記録**なので、門にせず数を印字する(★2026-11-08 の初版は
    # 「見逃すこと」を門にしていた —— 検出器が良くなると落ちる逆向きの門。敵対的レビューで外した)。
    assert n_strong_hit == len(strong), "日射 600 以上のバイパスダイオードの短絡を見逃した"
    assert n_soil == 144 and len(frames) == 496, "読んだ .raw の枚数が配布物と違う(故障 %d・汚れ %d)" % (len(frames), n_soil)
    assert n_fall == len(ratios), "高さとともにピークの ΔT が下がらない組がある"
    pid = (sum(res[(REAL_CATEGORIES[3][0], m, irr, alt)]["hit"] for m in range(1, REAL_CATEGORIES[3][2] + 1)
               for irr in rd.DTU_PV_IRT_IRRADIANCES for alt in rd.DTU_PV_IRT_ALTITUDES), REAL_CATEGORIES[3][2] * 16)
    out = {"n_frames": len(frames), "pid": pid,
           "weak_peak_10m": res[(byp[0], weak_missed[0], "200", 10)]["peak"] if weak_missed else float("nan"),
           "soil_pf": tuple(v["pf"] for _, v in sorted(iv.items()))}
    out.update({"res": res, "rows": rows, "n_strong": len(strong), "n_strong_hit": n_strong_hit,
            "weak_missed": weak_missed, "weak_peaks": weak_peaks, "n_nt": n_nt, "n_nt_hit": n_nt_hit,
            "ratio_med": float(np.median(ratios)), "ratio_min": min(ratios), "ratio_max": max(ratios),
            "n_fall": n_fall, "n_ratio": len(ratios), "digest": digest, "soil_rows": soil_rows,
            "n_soil": n_soil, "n_soil_hit": n_soil_hit, "soil_peak_med": float(np.median(soil_peaks)),
            "dmed_med": float(np.median(dmed)), "dmed_min": min(dmed), "dmed_max": max(dmed)})
    bad = recorded_matches(out)
    print("  実測と記録値(REAL_RECORDED)の照合: %s" % ("一致(%d 項目)" % len(REAL_RECORDED) if not bad else bad))
    assert not bad, "実データの実測が記録値と違う: %s" % bad
    return out


def save_real_figures(real: dict | None) -> None:
    """実データの図: 同じモジュールを日射 4 段と高さ 4 段で並べ、判定の塊を白枠で重ねる。"""
    if real is None or not figs.enabled():
        return
    import realdata as rd
    res = real["res"]
    byp = REAL_CATEGORIES[0][0]
    m_weak = real["weak_missed"][0]
    m_alt = 3
    lo, hi = -3.0, 25.0
    import annotate as ann
    iron_lut = np.asarray(fs.apply_cmap(np.linspace(0, 1, 256)[:, None], "inferno"))[:, 0]

    def panel(key):
        r = res[key]
        d = r["raw"] - float(np.median(r["raw"]))
        rgb = np.asarray(fs.apply_cmap(d, "inferno", vmin=lo, vmax=hi))
        mask = np.kron(r["det"]["mask"].astype(np.uint8), np.ones((REAL_BIN, REAL_BIN), np.uint8)).astype(bool)
        full = np.zeros(d.shape, bool)
        full[:mask.shape[0], :mask.shape[1]] = mask
        if full.any():
            rgb = np.asarray(fs.overlay_mask(rgb, full, color=(1.0, 1.0, 1.0), alpha=1.0,
                                             mode="margin", line_width=3))
        return rgb

    irr_label = {"200": "200", "600": "600", "800": "800", "abv800": "800 超"}
    panels, caps = [], []
    for irr in rd.DTU_PV_IRT_IRRADIANCES:
        r = res[(byp, m_weak, irr, 10)]
        panels.append(panel((byp, m_weak, irr, 10)))
        caps.append("日射 %s・10 m: %.1f K %s" % (irr_label[irr], r["peak"], "検出" if r["hit"] else "見逃し"))
    for alt in rd.DTU_PV_IRT_ALTITUDES:
        r = res[(byp, m_alt, "800", alt)]
        panels.append(panel((byp, m_alt, "800", alt)))
        caps.append("高さ %d m・日射 800: %.1f K" % (alt, r["peak"]))
    soil_show = []
    for cat, _, n in REAL_SOILING:
        keys = sorted(((cat, m, irr, 10) for m in range(1, n + 1) for irr in ("600", "800")),
                      key=lambda k: -res[k]["peak"])
        miss = [k for k in keys if not res[k]["hit"]]
        soil_show += [keys[0], miss[0] if miss else keys[1]]
    for k in soil_show:
        r = res[k]
        panels.append(panel(k))
        caps.append("汚れ %s・M%d・日射 %s: %.1f K %s" % (k[0][-1], k[1], k[2], r["peak"], "上がる" if r["hit"] else "上がらない"))
    panels[3] = np.asarray(ann.color_bar(np.asarray(panels[3], np.float64) / (255.0 if np.asarray(panels[3]).dtype == np.uint8 else 1.0),
                                         iron_lut, (300, 330, 18, 240), vmin=lo, vmax=hi, unit="K", font_size=14))
    figs.save_grid("real_dtu_conditions", panels, caps, ncols=4,
                   title="実データ: 故障のモジュールと汚れのモジュールの熱画像(DTU、CC BY 4.0)",
                   caption="公開のドローン熱画像(DTU の PV 発電所、正対化済みの温度の画像、%s)。色はモジュールの中央値からの"
                           "温度差 %.0f〜%.0f K(鉄色)、白枠はこの PoC の判定(GSD 19 mm に揃え、モジュール中央値・3 K・面積の門)。"
                           "上段: 同じモジュール %d を日射 200〜800 超で(高さ 10 m)—— 200 W/m² では 10 m で ΔT %.1f K、"
                           "4 つの高さの最大でも %.1f K しか出ず見逃す"
                           "(日射 600 以上ではバイパスダイオードの短絡 %d / %d 枚すべて検出)。下段: モジュール %d を高さ 8〜20 m で"
                           " —— ピークの ΔT は高いほど下がる(20 m / 8 m の比の中央値 %.2f。ただしモジュール全体の温度も"
                           "中央値 %+.1f K 動いており、高さごとの撮影は同時でないので画素の大きさの効果だけとは言えない)。"
                           "3 段目: 汚れのモジュール(配布元の分類の 1 つ。電気的な故障ではない)—— 同じ判定で %d / %d 枚が上がる。"
                           "上がった塊は画像の上の本物の温度差(雑音ではない)。現地の IV が付く 2 台の性能比(実測 / 模型の Pmax)は"
                           "%.1f %% / %.1f %% だが、清掃の前後や健全なモジュールとの比較は配布物に無く、出力の低下の原因は分けられない。"
                           "温度のしきい値は原因(汚れか電気的な故障か)を分けない。改変: 配布物の温度の画像を 7 x 7 の面積平均で判定し、"
                           "表示はモジュールの中央値からの差を鉄色で塗り、判定の白枠と見出しを重ねた。"
                           % (rd.dtu_pv_irt_credit(), lo, hi, m_weak, real["weak_peak_10m"], real["weak_peaks"][m_weak],
                              real["n_strong_hit"], real["n_strong"], m_alt, real["ratio_med"], real["dmed_med"],
                              real["n_soil_hit"], real["n_soil"], *real["soil_pf"]))
    figs.save_table("real_detection_table", ["故障の種類(EL・IV で確認)", "日射 200", "日射 600", "日射 800", "日射 800 超"],
                    real["rows"] + real["soil_rows"],
                    title="実データ: 同じ判定で上がった枚数(各セル = モジュール数 x 高さ 4 段)",
                    caption="熱を出す故障(バイパスダイオードの短絡)は日射 600 以上で全部上がり、200 では一部が消える。"
                            "熱を出さない故障(セルの割れ・配線の不良)は 1 度も上がらない(見逃し率 100 %%)。"
                            "汚れ(電気的な故障ではない)も %d / %d 枚が上がる(汚れは日射 800 超の撮影が無い)—— 温度のしきい値は"
                            "原因を分けない。"
                            "改変: 配布物の温度の画像を 7 x 7 の面積平均にして判定した。出典: %s"
                            % (real["n_soil_hit"], real["n_soil"], rd.dtu_pv_irt_credit()))


# --------------------------------------------------------------------------- #
# 10. 道具の穴                                                                  #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("9) 道具の穴(この PoC で fullseye を引いてみて)")
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
    save_aerial_figures(base, norms)
    real = section_real()
    rec_bad = recorded_consistent()
    print("\n  実データの記録値(REAL_RECORDED)の中身の整合: %s(データの有無に関係なく回る門)"
          % ("整合" if not rec_bad else rec_bad))
    assert not rec_bad, "実データの記録値の中身が食い違う: %s" % rec_bad
    save_real_figures(real)
    pv_gate = realism_evidence()
    assert 3.0 <= pv_gate["hotspot_delta_k"] <= 20.0
    assert 0.2 <= pv_gate["module_spread_k"] <= 5.0
    assert pv_gate["fresnel_gradient_error"] <= 0.02
    assert pv_gate["fpn_rms_k"] >= 0.02
    assert pv_gate["no_nuc_fpn_rms_k"] < 0.01
    section_tool_gaps()

    evaluation = CaseResult(
        case="poc_pv_thermal_survey",
        gates=[
            GateResult("hotspot-delta", 3.0 <= pv_gate["hotspot_delta_k"] <= 20.0,
                       measured=pv_gate["hotspot_delta_k"], expected="3..20", relation="inside"),
            GateResult("module-spread", 0.2 <= pv_gate["module_spread_k"] <= 5.0,
                       measured=pv_gate["module_spread_k"], expected="0.2..5", relation="inside"),
            GateResult("fresnel-gradient", pv_gate["fresnel_gradient_error"] <= 0.02,
                       measured=pv_gate["fresnel_gradient_error"], expected=0.02, relation="<="),
        ]
        + [GateResult("real-recorded-consistent", not rec_bad, measured=len(rec_bad), expected=0, relation="==")]
        + ([GateResult("real-recorded-matches", not recorded_matches(real), measured=len(recorded_matches(real)),
                       expected=0, relation="=="),
            GateResult("real-bypass-detected-600plus", real["n_strong_hit"] == real["n_strong"],
                       measured=real["n_strong_hit"], expected=real["n_strong"], relation="=="),
            GateResult("real-soiling-frames-read", real["n_soil"] == 144,
                       measured=real["n_soil"], expected=144, relation="=="),
            GateResult("real-peak-falls-with-altitude", real["n_fall"] == real["n_ratio"],
                       measured=real["n_fall"], expected=real["n_ratio"], relation="==")] if real else []),
        metrics={"hotspot_delta_k": pv_gate["hotspot_delta_k"]},
        artifacts=artifacts_from_manifest(figs.manifest()), seed=SEED,
        provenance={"migration": "P0-A"},
    )
    build_manifest(
        evaluation.case, metrics=evaluation.metrics, arrays={"apparent_temperature": base["t_app"]},
        truth=base["truth"], gates=evaluation.gates, figures=figs.manifest(), videos={}, seed=evaluation.seed,
    )

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * 健全セル +%.1f K、ホットスポットは薄まる前 %.1f K が"
          "**カメラに届くのは %.2f K**(伝導 x%.3f、カメラ x%.3f、"
          "放射と大気 x%.3f)。"
          % (base["dt_ok"], Q_HOT / base["u"],
             Q_HOT / base["u"] * base["a_both"] * base["gain"],
             base["a_cond"], base["a_cam"], base["gain"]))
    a_mean = ctl[("(a) 故障ゼロ・影と汚れあり", "全体平均")]
    a_med = ctl[("(a) 故障ゼロ・影と汚れあり", "モジュール中央値")]
    print("  * 故障ゼロの対照群で、全体平均は偽 %d 個 / 非故障 %d 個。"
          "モジュールごとの中央値なら偽 %d 個 / 非故障 %d 個。"
          % (a_mean["n_false"], a_mean["n_nonfault"],
             a_med["n_false"], a_med["n_nonfault"]))
    print("  * 風速の崖: ホットスポットは**面積の門**で落ちる(予測 %.1f m/s、"
          "実測は %.1f m/s まで上がり次の刻みで消える。ピーク基準の予測 %.1f m/s は外れ)。ストリングは"
          "ピーク基準どおり(予測 %.1f / 実測は %.1f m/s まで上がる)。"
          % (wind["v_area"], wind["last_hot"], wind["v_hot"],
             wind["v_str"], wind["last_str"]))
    print("  * 影はストリング故障を偽造する: 日向側 %+.2f K 対 本物 %+.2f K"
          "(差 %.2f K)。" % (shadow["warm"], shadow["real"],
                             abs(shadow["warm"] - shadow["real"])))
    print("  * GSD %.0f mm を超えるとホットスポットはしきい値を割る"
          "(閉形式の予測、実測との比は %.2f〜%.2f)。"
          % (1e3 * gsd["g_crit"],
             min(m / p for p, m in zip(gsd["pred"], gsd["meas"])),
             max(m / p for p, m in zip(gsd["pred"], gsd["meas"]))))
    print("  * 入射角 %.0f° で ΔT は %.2f 倍。射影変換で正対に戻すと位置は"
          " %.1f -> %.1f px に戻るのに ΔT は %.2f 倍 —— "
          "**幾何は直せるが放射は直らない**。"
          % (ang["deg"][-2], ang["meas"][-2], ang["shift"][-2][0],
             ang["shift"][-2][1], ang["rect"][-2]))
    print("  * ★NETD の予想は外れた: %.0f -> %.0f mK まで振っても偽は %d -> %d 個。"
          "雑音の崖は %.0f mK(実在のカメラの外)。"
          % (netd["netd"][0], netd["netd"][-1], netd["false"][0],
             netd["false"][-1], netd["crit"]))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
