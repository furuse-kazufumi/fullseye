# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""電池セルの劣化を CT で測る —— 膨れは外から見えるが、その何割かは中に隠れる。

角形リチウムイオンセルの劣化診断です。現場でいちばん手軽な指標は**外形**
(厚みをノギスで測る、治具に入るか見る)ですが、劣化の実体は缶の中の積層電極
—— 電極の膨れ、層間に溜まったガス、電極のずれ —— にあります。この PoC は
積層電極とアルミ缶を真値つきで作り、**実際に順投影 → ビームハードニング →
FBP 再構成**した CT ボリュームから、外形指標と内部指標を並べて測ります。

EXTEND: 実機 CT に差し替えるなら :func:`build_cell` が返す ``mu``(線減弱係数の
ボリューム)を実測の再構成ボリュームに置き換えます。``truth`` 辞書(層厚・層中心・
空隙体積・ずれ量)は**実データでは手に入りません** —— そこが差し替えの限界で、
実機では破壊検査(断面研磨)か、既知の膨れを与えた較正セルが要ります。缶の外形は
非破壊で測れるので、**外形だけは実測と突き合わせられます**。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **ゼロ点(外形だけを測る)を先に置く**。電極が 10 % 膨れると積層は
   0.340 mm 伸びようとするが、缶の中には初期クリアランスが 0.240 mm あり、
   はみ出した分しか外へ出ない。★**外形に出るのは膨れの 29.4 %**
   (幾何からの予測 29.4 %)。残りはクリアランスと、缶に押し返された
   積層の弾性圧縮(最小 0.984 倍)が飲む。
2. ★**その「見える割合」は劣化の大きさではなく、セルの初期クリアランスで
   決まる設計量**。同じ 0.340 mm の膨れでも、クリアランス 0.10 mm のセルでは
   70.6 % が見え、0.30 mm のセルでは 11.8 %、0.40 mm なら**何も見えない**。
   外形指標の感度はセル設計ごとに別物で、機種をまたいで比べられない。
3. ★**ノギスは真ん中を挟むので 4 倍に読む**。端板は周辺で固定された板なので
   中央だけがふくらむ(たわみ形状 cos^2 の面平均は 1/4)。CT から測ると
   中央 +0.235 mm に対して面平均は +0.066 mm —— 実測の比 **3.6 倍**
   (幾何からの予測 4.0 倍、真値は +0.249 / +0.062 mm)。「厚みが 0.24 mm
   増えた」は、体積では 0.07 mm ぶんしか増えていない。
4. ★★**対照群: 外形が同じで中身が違う 3 つ**。一様膨れ / 局所膨れ /
   層間ガス空隙を、缶のふくらみが揃うように作った(面平均のはみ出し
   0.0622 mm)。外形は 3 つとも中央 6.313 mm・面平均 6.144 mm で
   **ばらつき 0.000 mm** —— 外形指標では原理的に分けられない。内部指標は
   分ける: 層厚 0.190 / 0.187 / 0.173 mm、空隙率 0.00 / 0.00 / **5.20 %**、
   平面度(残差 RMS)0.0156 / 0.0428 / 0.0784 mm。一様膨れと局所膨れは
   **層厚では分かれず、平面度が分ける**。
5. ★**同じ外形を作るのに要る内部の膨張体積は等しくない**(一様 0.6715 /
   局所 0.3951 / ガス 0.3880 mm3)。集中した膨れは、一様な膨れの**半分ほどの
   体積**で同じ外形変化を作る —— 外形の変化量から中の劣化量は逆算できない。
6. ★**層厚は系統的に 12.5 % 過小に出る**(健全セル: 真値 0.200 -> 測定
   0.175 mm)。ぼけると縞は正弦波に近づき、微分のピーク間隔が**半周期
   0.160 mm** へ引き寄せられる(真値と半周期のあいだの 62 % の位置)。
   同じプロファイルから出す**層間隔は 0.321 mm で真値 0.320 mm を保つ** ——
   周期は当たり、厚みは外れる。層厚は条件どうしの比較にしか使えない。
7. ★**層を数えるだけでは足りないどころか、膨れると 1 枚減る**(健全 17 枚 ->
   一様膨れ 16 枚)。積層が缶に密着すると、端の層の立ち上がりが缶の内面の
   立ち下がりと融合する(健全セルは端板まで 0.18 mm 空いていて落ちない)。
8. **空隙は位置は当たるが体積は痩せる**。真値 3 個・0.4769 mm3 に対し
   3 個・0.4266 mm3(**-10.5 %**)。厚みの最大値は 0.600 mm で真値どおり ——
   落ちているのは**レンズ形の薄い縁**だけ(部分体積効果)。
9. **電極ずれは内部でしか測れない**。1 層 0.0200 mm のずれを 0.0190 mm/層
   (-5.1 %)で回収(健全セルの零点は -0.0001 mm/層)。同じセルの外形は
   +0.0006 mm しか動かない —— ずれは体積を変えないので**原理的に**出ない。
10. ★★**崖は電極の厚みではなく層間の隙間が決めた**。測る前に予測を 2 つ
    書いた: A 標本化定理(周期 0.320 mm)なら voxel/層厚 = 0.80、B 隙間
    0.120 mm を 2 標本で跨ぐ必要があるなら 0.30。**実測は 0.30 で B が当たり**
    (0.30 で 17 -> 15 枚、0.40 で 2 枚に全滅)。狭いほうの特徴が崖を決める。
11. ★**数え上げと周期の測定は別の崖を持つ**。層の数え上げが死んだ後も、
    プロファイルの卓越周期は voxel/層厚 0.40 まで 0.320 mm(FFT 実測
    0.327 mm)を保つ。空隙体積には崖が無く、最初から単調に痩せる
    (0.20 で -10.5 %、0.40 で -19.8 %、0.80 で -49.8 %、1.21 で -100 %)——
    **崖を持つ指標と、持たずにずるずる嘘になる指標がある**。
12. ★**雑音とビームハードニングでは壊れ方が違う**。フォトン数を 3e6 -> 3e3 と
    1000 分の 1 にしても層数は 17 -> 16 枚、層厚は 0.173 mm のまま。壊れるのは
    空隙率で 5.21 -> 4.37 %。ビームハードニング(硬さ比 1.0 -> 0.40)も
    **外形は動かさず**(中央 6.310 -> 6.320 mm)、層厚も動かさず(-12.9 % で
    一定)、空隙だけを痩せさせる(-9.1 % -> -14.7 %)—— コントラストが
    0.535 -> 0.326 に落ちてレンズの縁がしきい値を割るため。
13. **SoH も寿命もこの PoC では測れない**。示したのは「外形指標が内部の違いに
    盲目であること」と「どの分解能・雑音まで内部指標が生き残るか」まで。
    容量劣化との対応づけには充放電の実測が要る(画像だけでは原理的に出ない)。

★3-D の落とし穴を 2 つ踏んだ: (a) 点の op は ``(N,3)=(x,y,z)``、ボリュームの op は
``(D,H,W)=(z,y,x)``。組み立ては格子順で通し、最後に 1 回だけ転置する。
(b) **異方 voxel の粗い軸で補間してはいけない** —— スライス間隔 0.12 mm は面内
0.04 mm の 3 倍粗く、隣のスライスで層の位相がずれていると、その間を補間した
プローブは縞を打ち消す(実測でコントラストが 0.45 -> 0.25 に落ち、17 枚のうち
4 枚しか数えられなかった)。プローブは**スライスの中心**に置く。

【グラウンドトゥルース】積層電極(17 層・ピッチ 0.320 mm・電極厚 0.200 mm)と
アルミ缶(肉厚 0.200 mm)を解析的な場と ``box_sdf`` / ``plane_sdf`` の CSG で構成。
劣化は既知の場として与える —— 一様膨れ(全層が一定率で厚くなる)/ 局所膨れ
(ガウス分布)/ 層間ガス空隙(レンズ形)/ 電極ずれ(層ごとに一定量の面内シフト)。
缶の端板は「はみ出した体積を平板のたわみ形状 cos^2 で受ける」保存則で膨らませる。

来歴(公開文献のみ): Kok et al., *J. Phys. Energy* 1 (2019) 032003 —— X 線 CT による
電池内部の非破壊観察 / Bond et al., *J. Electrochem. Soc.* 169 (2022) 080531 ——
セル膨れと内部劣化の対応 / Barrett & Keat, *Radiographics* 24 (2004) 1679 ——
CT のアーティファクト(ビームハードニング・金属)/ Kak & Slaney,
*Principles of Computerized Tomographic Imaging* (IEEE, 1988) —— FBP と標本化。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

L = fs.ledger

# --- 格子の諸元(ボリュームは (深さ z, 行 y, 列 x) = (D, H, W)) ---------------- #
SZ, SY, SX = 0.12, 0.04, 0.04     # voxel [mm]。スライス間隔は面内より粗い(実機どおり)
ND, NH, NW = 16, 176, 96          # 格子の大きさ [voxel] -> 1.92 x 7.04 x 3.84 mm
SPACING = (SZ, SY, SX)

# --- セルの諸元 [mm] --------------------------------------------------------- #
CAN_X = (0.30, 3.54)              # 缶の外形(x)
CAN_Y = (0.40, 6.48)              # 缶の外形(y = 積層方向)
CAN_Z = (0.12, 1.80)              # 缶の外形(z)
WALL = 0.20                       # 缶の肉厚
CAV_X = (CAN_X[0] + WALL, CAN_X[1] - WALL)
CAV_Y = (CAN_Y[0] + WALL, CAN_Y[1] - WALL)
CAV_Z = (CAN_Z[0] + WALL, CAN_Z[1] - WALL)
CAV_LEN = CAV_Y[1] - CAV_Y[0]     # 空洞の積層方向の長さ = 5.68 mm

N_LAYER = 17                      # 電極層の数
T_ELEC = 0.20                     # 電極の厚み
GAP = 0.12                        # 層間(セパレータ + 電解液)
PITCH = T_ELEC + GAP              # 層のピッチ = 0.32 mm
H_BASE = N_LAYER * PITCH          # 健全時の積層高さ = 5.44 mm(クリアランス 0.24 mm)

ELEC_X = (0.80, 3.04)             # 電極の面内の広がり(x)
ELEC_Z = (0.52, 1.40)             # 電極の面内の広がり(z)

MU_CAN, MU_ELEC, MU_LIQ, MU_GAS = 2.2, 1.0, 0.35, 0.02   # 線減弱(コントラスト単位)

# --- 撮像の諸元 -------------------------------------------------------------- #
N_ANGLE = 120                     # 投影数
# サイノグラムは **voxel 添字** 単位の線積分なので、光子統計とビームハードニングに
# 渡す前に物理的な光学的厚み [-] へ直す: 1 コントラスト単位 = 0.35 /mm、1 step = SY mm。
ATT = 0.35 * SY                   # コントラスト単位・voxel -> 光学的厚み
N0_NOMINAL = 1.0e5                # 公称のフォトン数
BH_NOMINAL = 0.70                 # ビームハードニングの硬さ比(1.0 = 単色)
RING_NOMINAL = 0.006              # 検出器ゲイン誤差(リング/ストリークの元)
SEED = 20260907

# --- 劣化の量 ---------------------------------------------------------------- #
ALPHA_UNIFORM = 0.10              # 一様膨れ: 全層が 10 % 厚くなる
MISALIGN = 0.020                  # 電極ずれ: 1 層あたり x に 0.020 mm

_GRID = None


# --------------------------------------------------------------------------- #
# 格子 —— grid_coords は (nx, ny, nz, 3) を (x, y, z) 順で返す。ボリューム op は
# (D, H, W) = (z, y, x) なので、**組み立ては格子順・最後に一度だけ転置**する。
# 途中で混ぜると静かに間違う(3-D でいちばん多い事故)。
# --------------------------------------------------------------------------- #
def grid():
    """CSG 用の座標格子(``(nx, ny, nz, 3)``、成分は ``(x, y, z)``)。"""
    global _GRID
    if _GRID is None:
        _GRID = np.asarray(L.grid_coords(
            ((0.0, NW * SX), (0.0, NH * SY), (0.0, ND * SZ)), (NW, NH, ND)))
    return _GRID


def to_volume(a):
    """格子順 ``(nx, ny, nz)`` -> ボリューム順 ``(D, H, W) = (z, y, x)``。"""
    return np.ascontiguousarray(np.asarray(a).transpose(2, 1, 0))


def _up(a, ky=2, kx=2):
    """図のパネルを整数倍に拡大する(パネルが細いと題が入らない)。"""
    return np.repeat(np.repeat(np.asarray(a, float), ky, axis=0), kx, axis=1)


def _xz_field(f):
    """``(nx, nz)`` の面内の場を格子順に放送できる ``(nx, 1, nz)`` にする。"""
    return np.asarray(f)[:, None, :]


# --------------------------------------------------------------------------- #
# 1. 劣化の場 —— 積層高さ h(x, z) を先に決め、そこから缶のふくらみを保存則で出す
# --------------------------------------------------------------------------- #
def _panel_grids():
    """端板の面内座標 ``(x, z)`` と、板の内側かどうか。"""
    x = (np.arange(NW) + 0.5) * SX
    z = (np.arange(ND) + 0.5) * SZ
    xx, zz = np.meshgrid(x, z, indexing="ij")
    inside = ((xx >= CAV_X[0]) & (xx <= CAV_X[1])
              & (zz >= CAV_Z[0]) & (zz <= CAV_Z[1]))
    return xx, zz, inside


def _elec_footprint(xx, zz):
    return ((xx >= ELEC_X[0]) & (xx <= ELEC_X[1])
            & (zz >= ELEC_Z[0]) & (zz <= ELEC_Z[1]))


def _plate_shape(xx, zz):
    """周辺固定の平板のたわみ形状 ``cos^2 * cos^2``(中央 1、縁 0、面平均 1/4)。"""
    u = (xx - 0.5 * (CAV_X[0] + CAV_X[1])) / (CAV_X[1] - CAV_X[0])
    v = (zz - 0.5 * (CAV_Z[0] + CAV_Z[1])) / (CAV_Z[1] - CAV_Z[0])
    phi = np.cos(np.pi * np.clip(u, -0.5, 0.5)) ** 2 * np.cos(np.pi * np.clip(v, -0.5, 0.5)) ** 2
    _, _, inside = _panel_grids()
    return np.where(inside, phi, 0.0)


def degradation_fields(kind: str, scale: float = 1.0):
    """劣化の場を返す。

    戻り値は ``alpha``(層の増厚率の場、``(nx, nz)``)と ``voids``(層間ガス空隙の
    リスト ``[(gap_index, height_field), ...]``)と ``shift``(層あたりの x シフト)。
    """
    xx, zz, _ = _panel_grids()
    foot = _elec_footprint(xx, zz)
    alpha = np.zeros((NW, ND))
    voids: list[tuple[int, np.ndarray]] = []
    shift = 0.0

    if kind == "healthy":
        pass
    elif kind == "uniform":
        alpha = np.where(foot, ALPHA_UNIFORM, 0.0)
    elif kind == "local":
        # 局所膨れ: 面内のガウス分布で全層が厚くなる(電極の一部だけが劣化する)
        g = np.exp(-(((xx - 2.30) / 0.55) ** 2 + ((zz - 0.96) / 0.34) ** 2))
        alpha = np.where(foot, scale * g, 0.0)
    elif kind == "gas":
        # 層間ガス空隙: レンズ形(扁平楕円体)を 3 つの層間に置く
        for k, (xc, zc, ax, az) in enumerate(((1.28, 0.82, 0.42, 0.32),
                                              (2.00, 1.06, 0.40, 0.30),
                                              (2.68, 0.84, 0.42, 0.32))):
            gap_index = 4 + 4 * k
            r2 = ((xx - xc) / ax) ** 2 + ((zz - zc) / az) ** 2
            hv = 2.0 * scale * np.sqrt(np.clip(1.0 - r2, 0.0, None))
            voids.append((gap_index, np.where(foot, hv, 0.0)))
    elif kind == "misalign":
        shift = MISALIGN
    else:
        raise ValueError("未知の劣化: %r" % (kind,))
    return {"alpha": alpha, "voids": voids, "shift": shift}


def stack_height(fields) -> np.ndarray:
    """積層高さの場 ``h(x, z)`` [mm]。

    ★**電極の footprint の外でも ``H_BASE`` を返す**。ここを 0 にすると、層の
    y 位置を決める積み上げ(``y_bot = 中心 - h/2``)が footprint の外で崩れ、
    電極ずれで面内にはみ出した部分が消える(最初そう書いて、ずれの傾きが
    真値の半分になった)。はみ出し量の計算だけ footprint で切る。
    """
    h = np.full((NW, ND), H_BASE)
    h = h + N_LAYER * T_ELEC * fields["alpha"]
    for _, hv in fields["voids"]:
        h = h + hv
    return h


def bulge(fields) -> dict:
    """積層のはみ出しを缶の端板のたわみに変換する(体積保存)。

    はみ出し ``excess(x, z) = max(0, h - CAV_LEN)`` を、端板 2 枚が
    ``w(x, z) = w_max * phi(x, z)`` の形で受ける。``phi`` の面平均は 1/4 なので
    ``2 * w_max * (1/4) = <excess>`` -> ``w_max = 2 <excess>``。
    **中央のノギスは ``2 w_max`` を読む = 体積等価な平均の 4 倍**になる。
    """
    xx, zz, inside = _panel_grids()
    h = stack_height(fields)
    # はみ出すのは電極が実際に在るところだけ
    excess = np.where(_elec_footprint(xx, zz), np.maximum(0.0, h - CAV_LEN), 0.0)
    area_cell = SX * SZ
    mean_excess = float(excess[inside].sum() / max(1, int(inside.sum())))
    w_max = 2.0 * mean_excess
    w = w_max * _plate_shape(xx, zz)
    return {"h": h, "excess": excess, "w": w, "w_max": w_max,
            "mean_excess": mean_excess,
            "dv_ext": float(excess[inside].sum() * area_cell),
            "dv_int": float(np.where(_elec_footprint(xx, zz), h - H_BASE, 0.0).sum()
                            * area_cell),
            "panel_area": float(inside.sum() * area_cell)}


def match_to_bulge(kind: str, target_mean_excess: float) -> float:
    """外形のふくらみが ``target_mean_excess`` に一致する劣化の大きさを二分法で探す。

    **対照群の作り方そのもの** —— 外側から見て同じセルを、中身の違う 2 通りで作る。
    """
    lo, hi = 0.0, 4.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        me = bulge(degradation_fields(kind, mid))["mean_excess"]
        if me < target_mean_excess:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# --------------------------------------------------------------------------- #
# 2. セルを組む —— 缶は SDF の CSG、積層は解析的な場
# --------------------------------------------------------------------------- #
def _box(g, xr, yr, zr):
    c = (0.5 * (xr[0] + xr[1]), 0.5 * (yr[0] + yr[1]), 0.5 * (zr[0] + zr[1]))
    hx = (0.5 * (xr[1] - xr[0]), 0.5 * (yr[1] - yr[0]), 0.5 * (zr[1] - zr[0]))
    return np.asarray(L.box_sdf(g, c, hx))


def build_cell(kind: str, scale: float = 1.0) -> dict:
    """線減弱ボリューム ``mu`` (D, H, W) と真値の辞書を作る。"""
    g = grid()
    fields = degradation_fields(kind, scale)
    bl = bulge(fields)
    w = _xz_field(bl["w"])                      # 端板のたわみ (nx, 1, nz)

    # --- 缶: 側壁(SDF の差集合)+ たわんだ端板 2 枚(場でずらした格子で評価)---
    # ★``sdf_offset`` は**スカラのみ**なので、場でずらすには格子を歪めて評価する。
    g_lo = g.copy(); g_lo[..., 1] += w          # 下の端板を -y へ w だけ動かす
    g_hi = g.copy(); g_hi[..., 1] -= w          # 上の端板を +y へ
    side = L.sdf_subtract(_box(g, CAN_X, CAN_Y, CAN_Z),
                          _box(g, CAV_X, (-50.0, 50.0), CAV_Z))
    plate_lo = _box(g_lo, CAN_X, (CAN_Y[0], CAV_Y[0]), CAN_Z)
    plate_hi = _box(g_hi, CAN_X, (CAV_Y[1], CAN_Y[1]), CAN_Z)
    can_sdf = L.sdf_union(L.sdf_union(side, plate_lo), plate_hi)
    can = np.asarray(L.sdf_to_occupancy(can_sdf)) > 0.5

    # --- 空洞(電解液で満たされる): 側壁の内側 x たわんだ端板のあいだ ---
    inner_xz = _box(g, CAV_X, (-50.0, 50.0), CAV_Z)
    lo_face = np.asarray(L.plane_sdf(g_lo, (0.0, CAV_Y[0], 0.0), (0.0, -1.0, 0.0)))
    hi_face = np.asarray(L.plane_sdf(g_hi, (0.0, CAV_Y[1], 0.0), (0.0, 1.0, 0.0)))
    cav = np.asarray(L.sdf_to_occupancy(
        L.sdf_intersect(L.sdf_intersect(inner_xz, lo_face), hi_face))) > 0.5

    # --- 積層電極: 面内の場から層ごとの y 区間を積み上げる ---
    # ★積層が缶を突き抜けないように、たわんだ端板が許す高さまで**局所的に圧縮**する
    #   (実セルでも電極は加圧されて縮む)。これをしないと、背の高いガス空隙のところで
    #   端の層が缶に食われ、層数の比較が壊れる(最初そうなった)。
    X, Y, Z = g[..., 0], g[..., 1], g[..., 2]
    xx, zz, _ = _panel_grids()
    foot_base = _elec_footprint(xx, zz)
    h_demand = bl["h"]
    allow = CAV_LEN + 2.0 * bl["w"]
    squeeze = np.where(h_demand > 1e-9, np.minimum(1.0, allow / np.maximum(h_demand, 1e-9)), 1.0)
    h_fit = h_demand * squeeze
    h = _xz_field(h_fit)
    y_bot = 0.5 * (CAV_Y[0] + CAV_Y[1]) - 0.5 * h        # 積層は空洞の中央に座る
    t_i = _xz_field(T_ELEC * (1.0 + fields["alpha"]) * squeeze)
    void_by_gap = {k: _xz_field(hv * squeeze) for k, hv in fields["voids"]}

    gap_i = _xz_field(GAP * squeeze)
    elec = np.zeros(X.shape, bool)
    voids = np.zeros(X.shape, bool)
    cursor = y_bot + 0.5 * gap_i
    layer_lo, layer_hi, layer_dx = [], [], []
    for i in range(N_LAYER):
        dx = fields["shift"] * (i - 0.5 * (N_LAYER - 1))
        foot = _xz_field(((xx - dx >= ELEC_X[0]) & (xx - dx <= ELEC_X[1])
                          & (zz >= ELEC_Z[0]) & (zz <= ELEC_Z[1])))
        elec |= (Y >= cursor) & (Y < cursor + t_i) & foot
        layer_lo.append(cursor.copy())
        layer_hi.append((cursor + t_i).copy())
        layer_dx.append(dx)
        cursor = cursor + t_i
        hv = void_by_gap.get(i)
        gap_h = gap_i + (hv if hv is not None else 0.0)
        if hv is not None:
            mid = cursor + 0.5 * gap_h
            voids |= (Y >= mid - 0.5 * hv) & (Y < mid + 0.5 * hv) & (hv > 1e-9) \
                & _xz_field(foot_base)
        cursor = cursor + gap_h

    mu = np.zeros(X.shape)
    mu[cav] = MU_LIQ
    mu[elec] = MU_ELEC
    mu[voids] = MU_GAS
    # 缶は最後に、**部分体積で**塗る(食い込みは缶を優先)。二値で塗ると端板の
    # たわみが voxel に量子化されて階段になり、外形の測定がそのぶん粗くなる。
    frac = np.clip(0.5 - np.asarray(can_sdf) / SY, 0.0, 1.0)
    mu = mu * (1.0 - frac) + MU_CAN * frac

    area_cell = SX * SZ
    t_field = T_ELEC * (1.0 + fields["alpha"]) * squeeze
    truth = {
        "kind": kind, "scale": scale,
        "n_layer": N_LAYER, "t_elec": T_ELEC, "pitch": PITCH,
        "t_mean": float(t_field[foot_base].mean()),
        "h_mean": float(h_fit[foot_base].mean()),
        "dh_mean": float(h_fit[foot_base].mean() - H_BASE),
        "dv_int": float((h_fit[foot_base] - H_BASE).sum() * area_cell),
        "dh_demand": float(h_demand[foot_base].mean() - H_BASE),
        "dv_demand": bl["dv_int"], "dv_ext": bl["dv_ext"],
        "mean_excess": bl["mean_excess"], "w_max": bl["w_max"],
        "caliper_gain": 2.0 * bl["w_max"],
        "squeeze_min": float(squeeze[foot_base].min()),
        "void_volume": float(sum(np.sum(hv * squeeze) for _, hv in fields["voids"])
                             * area_cell),
        "void_peak": float(max((np.max(hv * squeeze) for _, hv in fields["voids"]),
                               default=0.0)),
        "void_voxels": int(voids.sum()),
        "shift": fields["shift"],
        "layer_center_mm": [float((0.5 * (lo + hi))[:, 0, :][foot_base].mean())
                            for lo, hi in zip(layer_lo, layer_hi)],
    }
    return {"mu": to_volume(mu), "can": to_volume(can), "elec": to_volume(elec),
            "void": to_volume(voids), "cav": to_volume(cav),
            "truth": truth, "bulge": bl}


# --------------------------------------------------------------------------- #
# 3. 撮像 —— 順投影 -> ビームハードニング -> リング -> フォトン雑音 -> FBP
# --------------------------------------------------------------------------- #
ANGLES = None


def angles():
    global ANGLES
    if ANGLES is None:
        ANGLES = np.asarray(fs.projection_angles(N_ANGLE, 180.0))
    return ANGLES


def forward(mu: np.ndarray) -> np.ndarray:
    """順投影(平行ビーム、回転軸 = z)。**これが実行時間の大半**。"""
    return np.asarray(fs.radon_volume(mu, angles()))


def acquire(sino: np.ndarray, n0=N0_NOMINAL, bh=BH_NOMINAL, ring=RING_NOMINAL,
            seed=SEED) -> np.ndarray:
    """サイノグラムに撮像の劣化を入れて再構成する。

    順序は物理どおり: 光学的厚みへ換算 -> 多色化(ビームハードニング)->
    検出器ゲイン誤差(リング/ストリーク)-> 光子計数 -> 対数 -> FBP。
    """
    p = np.asarray(sino, float) * ATT
    if bh < 1.0:
        p = np.stack([np.asarray(fs.beam_hardening_apply(p[k], 0.5, bh))
                      for k in range(p.shape[0])])
    if ring > 0.0:
        p = np.stack([np.asarray(fs.ring_artifact_apply(p[k], ring, seed))
                      for k in range(p.shape[0])])
    if n0 is not None and np.isfinite(n0):
        rng = np.random.default_rng(seed)
        inten = np.exp(-np.clip(p, 0.0, 30.0))
        counts = rng.poisson(np.clip(n0 * inten, 1e-9, None)).astype(float)
        p = -np.log(np.maximum(counts, 0.5) / n0)
    rec = np.asarray(fs.fbp_volume(p / ATT, angles(), size=NH))
    c0 = (rec.shape[2] - NW) // 2
    return np.ascontiguousarray(rec[:, :, c0:c0 + NW])


# --------------------------------------------------------------------------- #
# 4. 測る —— 外形(ゼロ点)と内部指標
# --------------------------------------------------------------------------- #
def _vidx(z_mm, y_mm, x_mm, spacing=SPACING):
    """物理座標 [mm] -> ボリュームの (z, y, x) 添字(中心アライン)。

    ★掃引で voxel を変えるとき、ここに ``SPACING`` を焼き込んでいると静かに
    ずれる(最初そう書いて、粗い格子で probe が範囲外に飛んだ)。
    """
    return (z_mm / spacing[0] - 0.5, y_mm / spacing[1] - 0.5, x_mm / spacing[2] - 0.5)


def outer_metrics(vol: np.ndarray) -> dict:
    """**ゼロ点** —— 缶の外形だけから劣化を測る(非破壊で誰でもできる方法)。

    外(空気)から内へ向かって最初に缶を横切る位置を、列ごとに**サブボクセルで**
    出す。しきい値は缶の水準の半分(空気 0 と缶の中間 = 縁の半値)にとる ——
    絶対値にするとビームハードニングで缶の水準が下がったときに破綻する。
    電極が誤って明るく出ても、それは 2 つの交差の**あいだ**なので影響しない。

    ``caliper`` は中央 3x3 の平均(ノギスで真ん中を挟む)、``mean`` は端板の面平均
    (体積等価)。**「外形が囲む高さ」を出す op は公開経路に無いので自前**。
    """
    v = np.asarray(vol, float)
    v_can = float(np.median(v[v > np.percentile(v, 98.0)]))
    thr = 0.5 * v_can
    above = v > thr
    ok = above.any(axis=1)
    first = np.argmax(above, axis=1)
    last = NH - 1 - np.argmax(above[:, ::-1, :], axis=1)

    def _sub(idx, back):
        """しきい値交差のサブボクセル位置 [voxel]。``back`` なら 1 つ後ろ側と補間。"""
        j = np.clip(idx + (1 if back else -1), 0, NH - 1)
        a = np.take_along_axis(v, j[:, None, :], axis=1)[:, 0, :]
        b = np.take_along_axis(v, idx[:, None, :], axis=1)[:, 0, :]
        d = np.where(np.abs(b - a) < 1e-9, np.nan, b - a)
        f = np.clip((thr - a) / d, 0.0, 1.0)
        return j + f * (idx - j)

    y_lo, y_hi = _sub(first, False), _sub(last, True)
    heights = np.where(ok, (y_hi - y_lo) * SY, np.nan)
    _, _, inside = _panel_grids()
    panel = inside.T & np.isfinite(heights)
    cz, cx = ND // 2, NW // 2
    core = heights[cz - 1:cz + 2, cx - 1:cx + 2]
    return {"height": heights, "panel": panel, "thr": thr,
            "caliper": float(np.nanmean(core)),
            "mean": float(heights[panel].mean()),
            "bbox": tuple(int(b) for b in np.asarray(L.vol_bounding_box(above)))}


def _probe_points():
    """内部を突くプローブの ``(z, x)`` [mm]。電極の内側だけを使う。

    ★``z`` は**スライスの中心**に置く。スライス間隔 0.12 mm は面内 0.04 mm の
    3 倍粗く、隣り合うスライスで層の位相がずれていると、その間を補間した
    プローブは縞を打ち消してしまう(実測: 空隙のあるセルでコントラストが
    0.45 -> 0.25 に落ち、17 枚の層のうち 4 枚しか数えられなかった)。
    """
    zs = [(k + 0.5) * SZ for k in range(int(ELEC_Z[0] / SZ) + 1,
                                        int(ELEC_Z[1] / SZ))]
    xs = np.linspace(ELEC_X[0] + 0.25, ELEC_X[1] - 0.25, 7)
    return [(float(z), float(x)) for z in zs for x in xs]


def cavity_span(vol, spacing, zc, xc):
    """缶の**内側の面**を列ごとにデータから見つける(真値を使わない)。

    プロファイルは 空気 -> 缶 -> 空洞 -> 缶 -> 空気 と進むので、缶の水準の半値で
    2 値化した最初の塊の終わりと最後の塊の始まりが内面。★これをやらずに設計上の
    空洞 ``CAV_Y`` で突くと、**膨れて端板が動いた分だけ端の層を数え落とす**
    (最初そう書いて、一様膨れのセルだけ層が 17 -> 15 枚になった)。
    """
    y0 = 0.5 * spacing[1]
    y1 = (vol.shape[1] - 0.5) * spacing[1]
    pr = np.asarray(L.vol_profile_line(vol, _vidx(zc, y0, xc, spacing),
                                       _vidx(zc, y1, xc, spacing), spacing=spacing))
    t, v = pr[:, 0], pr[:, 1]
    above = v > 0.55 * float(v.max())
    idx = np.nonzero(above)[0]
    if idx.size < 2:
        return None
    br = np.nonzero(np.diff(idx) > 1)[0]
    if br.size == 0:
        return None
    lo = y0 + float(t[idx[br[0]]]) + 0.02
    hi = y0 + float(t[idx[br[-1] + 1]]) - 0.02
    return (lo, hi) if hi - lo > 1.0 else None


def _edge_threshold(vol, spacing, zc, xc, span):
    """観測されたコントラストから微分しきい値を決める(voxel に依らない規約)。

    「2 voxel のあいだにコントラストの 30 % を振る縁だけを縁と認める」。
    固定値にすると崖の位置がしきい値の選び方で動いてしまう。
    """
    pr = np.asarray(L.vol_profile_line(vol, _vidx(zc, span[0], xc, spacing),
                                       _vidx(zc, span[1], xc, spacing),
                                       spacing=spacing))
    v = pr[:, 1]
    # p5 ではなく p25 を下端にとる —— 空隙(気体)は電解液よりずっと暗いので、
    # p5 だと空隙のあるプローブだけコントラストが水増しされ、しきい値が上がって
    # 層を数え落とす(実測でそうなった)。
    c = float(np.percentile(v, 90) - np.percentile(v, 25))
    return max(1e-6, 0.30 * c / (2.0 * spacing[1])), c, pr


def _stack_probes(vol, spacing):
    """各プローブの ``(zc, xc, span, thr, profile)``。空洞が見つからない列は捨てる。"""
    out = []
    for zc, xc in _probe_points():
        span = cavity_span(vol, spacing, zc, xc)
        if span is None:
            continue
        thr, contrast, pr = _edge_threshold(vol, spacing, zc, xc, span)
        out.append((zc, xc, span, thr, contrast, pr))
    return out


def detect_voids(vol, spacing, liq_level):
    """層間ガス空隙の検出 —— 電解液の水準の半分より暗い連結成分。

    しきい値を絶対値にすると、ビームハードニングで水準が下がったときに空隙が
    まるごと消える。だから ``liq_level``(プローブが見た電解液の水準)に対する
    比で切る。ROI は電極の内側だけ(缶の外の空気を空隙と数えないため)。
    """
    roi = np.zeros(vol.shape, bool)
    z0, z1 = int(ELEC_Z[0] / spacing[0]) + 1, int(ELEC_Z[1] / spacing[0])
    y0, y1 = int((CAN_Y[0] + 0.30) / spacing[1]), int((CAN_Y[1] - 0.30) / spacing[1])
    x0, x1 = int(ELEC_X[0] / spacing[2]) + 2, int(ELEC_X[1] / spacing[2]) - 2
    roi[z0:z1, y0:y1, x0:x1] = True
    dark = (np.asarray(vol) < 0.5 * liq_level) & roi
    lab = np.asarray(L.vol_label(dark, connectivity=26))
    props = L.vol_region_props(lab, spacing=spacing)
    cell_vol = float(spacing[0] * spacing[1] * spacing[2])
    big = sorted([p for p in props if p["volume"] > max(0.004, 4.0 * cell_vol)],
                 key=lambda p: -p["volume"])
    return dark, lab, big, roi


def liquid_level(vol, spacing=SPACING) -> float:
    """プローブが見た電解液の水準(空隙のしきい値の基準)。"""
    lows = [float(np.percentile(p[5][:, 1], 10)) for p in _stack_probes(vol, spacing)]
    return float(np.median(lows)) if lows else MU_LIQ


def internal_metrics(vol: np.ndarray, spacing=SPACING) -> dict:
    """内部指標 —— 層数・層厚・層間隔の散らばり・空隙率。"""
    counts, thicks, pitches, contrasts = [], [], [], []
    fft_pitch, lows = [], []
    for zc, xc, span, thr, contrast, pr in _stack_probes(vol, spacing):
        contrasts.append(contrast)
        lows.append(float(np.percentile(pr[:, 1], 10)))
        p0 = _vidx(zc, span[0], xc, spacing)
        p1 = _vidx(zc, span[1], xc, spacing)
        th = list(L.vol_wall_thickness(vol, p0, p1, sigma=1.2, threshold=thr,
                                       spacing=spacing))
        thicks.extend(th)
        ed = L.vol_edge_probe(vol, p0, p1, sigma=1.2, threshold=thr,
                              spacing=spacing, polarity="positive")
        # ★層は「立ち上がりの縁の数」で数える。``vol_wall_thickness`` の対
        #   (立ち上がり -> 立ち下がり)で数えると、缶の内面のすぐ内側に余分な
        #   立ち下がりが 1 本入るだけで対がずれ、健全なセルでも 17 -> 16 に落ちる。
        counts.append(len(ed))
        t = np.asarray([e["t_mm"] for e in ed])
        if t.size >= 2:
            pitches.extend(np.diff(t).tolist())
        fft_pitch.append(_fft_pitch(pr[:, 0], pr[:, 1]))

    liq = float(np.median(lows)) if lows else MU_LIQ
    dark, lab, big, roi = detect_voids(vol, spacing, liq)
    cell_vol = float(spacing[0] * spacing[1] * spacing[2])
    void_vol = float(sum(p["volume"] for p in big))
    roi_vol = float(roi.sum() * cell_vol)

    return {"n_layer": int(np.median(counts)) if counts else 0,
            "n_layer_min": int(np.min(counts)) if counts else 0,
            "n_layer_max": int(np.max(counts)) if counts else 0,
            "t_mean": float(np.mean(thicks)) if thicks else float("nan"),
            "t_sd": float(np.std(thicks)) if thicks else float("nan"),
            "pitch_mean": float(np.mean(pitches)) if pitches else float("nan"),
            "pitch_sd": float(np.std(pitches)) if pitches else float("nan"),
            "fft_pitch": float(np.median(fft_pitch)),
            "contrast": float(np.mean(contrasts)),
            "void_volume": void_vol, "n_void": len(big),
            "void_fraction": 100.0 * void_vol / roi_vol,
            "roi_volume": roi_vol}


def _fft_pitch(t_mm, values) -> float:
    """プロファイルの卓越周期 [mm]。**数えるのではなく周期を測る**別経路。

    ★1-D の周期性(自己相関・卓越周期)を出す op が公開経路に無いので自前。
    """
    v = np.asarray(values, float)
    v = v - v.mean()
    if v.size < 8:
        return float("nan")
    dt = float(t_mm[1] - t_mm[0])
    sp = np.abs(np.fft.rfft(v * np.hanning(v.size)))
    freq = np.fft.rfftfreq(v.size, d=dt)
    lo = (freq > 1.0 / 1.2) & (freq < 1.0 / 0.12)      # 0.12 .. 1.2 mm の周期だけ
    if not lo.any():
        return float("nan")
    k = np.nonzero(lo)[0][np.argmax(sp[lo])]
    return float(1.0 / freq[k])


def flatness(vol: np.ndarray, y_target: float, spacing=SPACING) -> dict:
    """層の平面度 —— 1 枚の界面を面で測り、``fit_plane_3d`` の残差 RMS を返す。"""
    pts = []
    for zc, xc, span, thr, _c, _pr in _stack_probes(vol, spacing):
        p0 = _vidx(zc, span[0], xc, spacing)
        p1 = _vidx(zc, span[1], xc, spacing)
        ed = L.vol_edge_probe(vol, p0, p1, sigma=1.2, threshold=thr,
                              spacing=spacing, polarity="positive")
        if not ed:
            continue
        y = np.asarray([span[0] + e["t_mm"] for e in ed])
        j = int(np.argmin(np.abs(y - y_target)))
        if abs(y[j] - y_target) < 0.5 * PITCH:
            pts.append((xc, float(y[j]), zc))          # 点の op は (x, y, z)
    if len(pts) < 6:
        return {"resid": float("nan"), "n": len(pts), "points": np.zeros((0, 3))}
    p = np.asarray(pts)
    point, normal, resid = L.fit_plane_3d.raw(p)
    return {"resid": float(resid), "n": len(pts), "points": p,
            "normal": np.asarray(normal)}


def misalign_slope(vol: np.ndarray, truth, spacing=SPACING) -> dict:
    """電極端のずれ —— 層ごとに x 方向の縁を測り、層番号に対する傾きを出す。"""
    zc = 0.5 * (ELEC_Z[0] + ELEC_Z[1])
    xs, idx = [], []
    contrast = float(np.median([p[4] for p in _stack_probes(vol, spacing)] or [0.4]))
    for i, yc in enumerate(truth["layer_center_mm"]):
        p0 = _vidx(zc, yc, CAV_X[0] + 0.02, spacing)
        p1 = _vidx(zc, yc, CAV_X[1] - 0.02, spacing)
        thr = 0.30 * contrast / (2.0 * spacing[2])
        ed = L.vol_edge_probe(vol, p0, p1, sigma=1.2, threshold=thr,
                              spacing=spacing, polarity="positive")
        if ed:
            xs.append(CAV_X[0] + 0.02 + ed[0]["t_mm"])
            idx.append(i)
    if len(xs) < 5:
        return {"slope": float("nan"), "n": len(xs), "idx": idx, "x": xs}
    a, b = np.polyfit(np.asarray(idx, float), np.asarray(xs), 1)
    return {"slope": float(a), "intercept": float(b), "n": len(xs),
            "idx": idx, "x": xs}


# --------------------------------------------------------------------------- #
# 節 1 —— 場面と、外形指標がどれだけ見落とすか
# --------------------------------------------------------------------------- #
def section_scene(cells, recs) -> dict:
    print("\n" + "=" * 78)
    print("1) 場面 —— 積層 %d 層 / ピッチ %.3f mm / 缶の肉厚 %.2f mm" % (
        N_LAYER, PITCH, WALL))
    print("=" * 78)
    hz = cells["healthy"]
    print("  格子 %s voxel、voxel %.2f x %.2f x %.2f mm、投影 %d 本" % (
        (ND, NH, NW), SZ, SY, SX, N_ANGLE))
    print("  空洞の長さ %.3f mm / 健全な積層高さ %.3f mm -> クリアランス %.3f mm"
          % (CAV_LEN, H_BASE, CAV_LEN - H_BASE))
    o = outer_metrics(recs["healthy"])
    print("  健全セルの外形高さ: 中央 %.3f mm / 平均 %.3f mm(真値 %.3f mm)"
          % (o["caliper"], o["mean"], CAN_Y[1] - CAN_Y[0]))

    if figs.enabled():
        # X 線投影(DRR)—— 実機で最初に撮る絵。**積層は見えるが、どの層が
        # 厚いのかは重なって消える**。断層に落とさないと内部指標は出ない。
        panels, caps = [], []
        for key, name in (("healthy", "健全"), ("gas", "ガス空隙")):
            for az in (0.0, 22.0):
                panels.append(_up(L.render_volume_projection(
                    cells[key]["mu"], az, 0.0, mode="xray")))
                caps.append("%s %.0f 度" % (name, az))
        figs.save_grid("xray_projection", panels, caps,
                       title="X 線投影(減衰の積算)—— 姿勢が変わると縞が消える",
                       ncols=4,
                       caption="真正面(0 度)なら空隙の影までは見える。ただし"
                               "奥行きに積算されているので厚みも深さも出ない。"
                               "22 度傾けると層の縞そのものが重なって消える —— "
                               "投影では姿勢が結果を決めてしまう。だから断層に落とす。")

    mid = ND // 2
    figs.save_grid("scene", [_up(cells["healthy"]["mu"][mid]), _up(recs["healthy"][mid]),
                             _up(recs["uniform"][mid]), _up(recs["gas"][mid])],
                   ["真値 μ 健全", "CT 健全", "CT 一様膨れ", "CT ガス空隙"],
                   title="角形セルの断面(z 中央、縦 = 積層方向 y)",
                   ncols=4,
                   caption="缶(明)・電極(中)・電解液(暗)・ガス(最暗)。"
                           "順投影 → ビームハードニング → リング → フォトン雑音 → FBP。")
    return {"outer_healthy": o}


def section_outer_blindness(cells, recs) -> dict:
    print("\n" + "=" * 78)
    print("2) ゼロ点 —— 外形だけで測ると、膨れの何割が見えるか")
    print("=" * 78)

    t = cells["uniform"]["truth"]
    frac = 100.0 * t["dv_ext"] / t["dv_demand"]
    pred = 100.0 * (t["dh_demand"] - (CAV_LEN - H_BASE)) / t["dh_demand"]
    print("  一様膨れ %.0f %%: 積層は %.3f mm 伸びようとする(体積 %.4f mm3)。" % (
        100 * ALPHA_UNIFORM, t["dh_demand"], t["dv_demand"]))
    print("    クリアランス %.3f mm を食い潰した残りだけが缶を押す"
          " -> 外形の体積増 %.4f mm3" % (CAV_LEN - H_BASE, t["dv_ext"]))
    print("    ★外から見える割合 = %.1f %%(幾何からの予測 %.1f %%)" % (frac, pred))
    print("    残りの行き先は 2 つ: クリアランス(隙間)と、缶に押し返された"
          "積層の弾性圧縮(最小 %.3f 倍)。" % t["squeeze_min"])

    o0 = outer_metrics(recs["healthy"])
    o1 = outer_metrics(recs["uniform"])
    d_cal = o1["caliper"] - o0["caliper"]
    d_mean = o1["mean"] - o0["mean"]
    print("\n  CT から測った外形の増分: 中央のノギス %+.3f mm / 面平均 %+.3f mm"
          % (d_cal, d_mean))
    print("    真値: 中央 %+.3f mm / 面平均 %+.3f mm" % (
        t["caliper_gain"], t["mean_excess"]))
    print("    ★中央のノギスは平均の %.1f 倍を読む(平板のたわみ形状 cos^2 の"
          "面平均が 1/4 なので、幾何からの予測は 4.0 倍)。" % (d_cal / max(1e-9, d_mean)))
    print("    「厚みが %.2f mm 増えた」と書くと、体積では %.2f mm しか"
          "増えていない。" % (d_cal, d_mean))

    # クリアランスを振ると「見える割合」は設計値で決まる
    clr, seen = [], []
    for c in np.linspace(0.0, 0.50, 11):
        dh = t["dh_demand"]
        clr.append(c)
        seen.append(100.0 * max(0.0, dh - c) / dh)
    print("\n  ★「見える割合」は劣化の大きさではなく**セルの初期クリアランス**で"
          "決まる設計量:")
    for c, s in zip(clr[::2], seen[::2]):
        print("     クリアランス %.2f mm -> 外から見えるのは %5.1f %%" % (c, s))

    x_mm = (np.arange(NW) + 0.5) * SX

    def _hprof(o):
        """端板の面内だけ(側壁の列は缶が丸ごと写るので外す)。"""
        h = o["height"][ND // 2]
        k = np.isfinite(h) & o["panel"][ND // 2]
        return x_mm[k], h[k]

    figs.save_plot("outer_profile",
                   [("健全",) + _hprof(o0), ("一様膨れ",) + _hprof(o1),
                    ("ガス空隙(外形は同じ)",) + _hprof(outer_metrics(recs["gas"]))],
                   xlabel="x [mm]", ylabel="缶の外形高さ [mm]",
                   title="外形はふくらむが、真ん中しかふくらまない",
                   caption="端板は周辺で固定なので中央だけが出る。ノギスは中央を"
                           "読むので体積等価な平均の 4 倍を報告する。")
    figs.save_plot("visible_fraction",
                   [("外から見える割合", clr, seen)],
                   xlabel="初期クリアランス [mm]", ylabel="外形に出る割合 [%]",
                   title="外形指標が拾う割合はセルの設計で決まる",
                   caption="同じ劣化でもクリアランスが厚いセルでは外形に何も出ない。")
    return {"frac": frac, "pred": pred, "d_cal": d_cal, "d_mean": d_mean,
            "ratio": d_cal / max(1e-9, d_mean), "clearance": clr, "seen": seen}


# --------------------------------------------------------------------------- #
# 節 3 —— 対照群: 外形が同じで中身が違う 3 つ
# --------------------------------------------------------------------------- #
def section_control(cells, recs) -> dict:
    print("\n" + "=" * 78)
    print("3) 対照群 —— 外形のふくらみを揃えた 3 つのセル")
    print("=" * 78)

    rows, res = [], {}
    for key, name in (("healthy", "健全"), ("uniform", "一様膨れ"),
                      ("local", "局所膨れ"), ("gas", "層間ガス空隙")):
        o = outer_metrics(recs[key])
        m = internal_metrics(recs[key])
        t = cells[key]["truth"]
        res[key] = {"outer": o, "inner": m, "truth": t}
        rows.append([name,
                     "%.3f" % o["caliper"], "%.3f" % o["mean"],
                     "%d" % m["n_layer"], "%.3f" % m["t_mean"],
                     "%.3f" % m["pitch_sd"], "%.2f" % m["void_fraction"],
                     "%.4f" % t["dv_int"]])
        print("  %-10s 外形: 中央 %.3f mm 平均 %.3f mm | 内部: 層 %2d 枚 "
              "層厚 %.3f mm 層間隔σ %.3f mm 空隙率 %.2f %% | 真の膨張体積 %.4f mm3"
              % (name, o["caliper"], o["mean"], m["n_layer"], m["t_mean"],
                 m["pitch_sd"], m["void_fraction"], t["dv_int"]))

    base = res["healthy"]
    print("\n  ★外形は 3 つとも同じ(中央 %.3f / %.3f / %.3f mm、ばらつき %.3f mm)。"
          % (res["uniform"]["outer"]["caliper"], res["local"]["outer"]["caliper"],
             res["gas"]["outer"]["caliper"],
             float(np.std([res[k]["outer"]["caliper"]
                           for k in ("uniform", "local", "gas")]))))
    print("     内部は違う: 層厚 %.3f / %.3f / %.3f mm、空隙率 %.2f / %.2f / %.2f %%"
          % (res["uniform"]["inner"]["t_mean"], res["local"]["inner"]["t_mean"],
             res["gas"]["inner"]["t_mean"],
             res["uniform"]["inner"]["void_fraction"],
             res["local"]["inner"]["void_fraction"],
             res["gas"]["inner"]["void_fraction"]))
    print("     ★同じ外形を作るのに必要な**内部の膨張体積**は "
          "一様 %.4f / 局所 %.4f / ガス %.4f mm3 —— 集中した膨れは"
          "少ない体積で同じ外形変化を作る。"
          % (res["uniform"]["truth"]["dv_int"], res["local"]["truth"]["dv_int"],
             res["gas"]["truth"]["dv_int"]))

    # 層厚の系統誤差 —— ぼけると縁の間隔は半周期へ引き寄せられる
    th = res["healthy"]["inner"]["t_mean"]
    tr = res["healthy"]["truth"]["t_mean"]
    print("\n  ★層を**数えるだけ**では劣化の種類は分からない —— それどころか、"
          "膨れたセルでは %d 枚に減る(健全 %d 枚)。積層が缶に密着すると、"
          "端の層の立ち上がりが**缶の内面の立ち下がりと融合**して 1 枚落ちる"
          "(健全セルでは端板まで %.2f mm 空いているので落ちない)。"
          % (res["uniform"]["inner"]["n_layer"], res["healthy"]["inner"]["n_layer"],
             0.5 * (CAV_LEN - H_BASE) + 0.5 * GAP))

    print("\n  ★層厚は**系統的に過小**に出る(健全セル: 真値 %.3f -> 測定 %.3f mm、"
          "%+.1f %%)。" % (tr, th, 100 * (th - tr) / tr))
    print("     理由: ぼけると縞は正弦波に近づき、微分のピーク間隔は"
          "**半周期 %.3f mm** へ引き寄せられる(真値 %.3f と半周期のあいだの %.0f %% の"
          "ところに落ちた)。**層間隔(ピッチ)は %.3f mm で真値 %.3f を保つ** ——"
          "同じプロファイルから出しても、周期は当たり厚みは外れる。"
          % (0.5 * PITCH, tr, 100 * (tr - th) / (tr - 0.5 * PITCH),
             res["healthy"]["inner"]["pitch_mean"], PITCH))
    print("     だから層厚は**条件どうしの比較にだけ**使える(絶対値の合否判定には"
          "使えない)。")

    # 層の平面度 —— **端に近い層**で測る。膨れは積層の中央について対称なので、
    # 真ん中の層はどの劣化でも平らなまま(ここを測ると差が出ない)。
    flat = {}
    for key in ("healthy", "uniform", "local", "gas"):
        y_t = float(cells[key]["truth"]["layer_center_mm"][N_LAYER - 2])
        flat[key] = flatness(recs[key], y_t)
        print("     平面度(端から 2 枚目の層、%s): 残差 RMS %.4f mm(%d 点)"
              % (key, flat[key]["resid"], flat[key]["n"]))

    print("\n  ★どの指標がどれを分けるか: 一様膨れと局所膨れは**層厚では分かれない**"
          "(%.3f / %.3f mm)が、**平面度**が分ける(%.4f / %.4f mm)。"
          "ガス空隙は**空隙率と層間隔の散らばり**が分ける(%.2f %% / %.3f mm)。"
          % (res["uniform"]["inner"]["t_mean"], res["local"]["inner"]["t_mean"],
             flat["uniform"]["resid"], flat["local"]["resid"],
             res["gas"]["inner"]["void_fraction"], res["gas"]["inner"]["pitch_sd"]))

    for r, key in zip(rows, ("healthy", "uniform", "local", "gas")):
        r.append("%.4f" % flat[key]["resid"])

    if figs.enabled():
        # 積層方向のプロファイル(同じ (z, x) で 4 条件)
        zc, xc = (int(ELEC_Z[0] / SZ) + 3 + 0.5) * SZ, 1.28
        series = []
        for key, name in (("healthy", "健全"), ("uniform", "一様膨れ"),
                          ("local", "局所膨れ"), ("gas", "層間ガス空隙")):
            sp = cavity_span(recs[key], SPACING, zc, xc)
            pr = np.asarray(L.vol_profile_line(
                recs[key], _vidx(zc, sp[0], xc), _vidx(zc, sp[1], xc),
                spacing=SPACING))
            series.append((name, sp[0] + pr[:, 0], pr[:, 1]))
        figs.save_plot("profile_layers", series,
                       xlabel="積層方向 y [mm]", ylabel="CT 値(線減弱、任意単位)",
                       title="積層を貫くプロファイル(同じ (z, x) で 4 条件)",
                       caption="17 本の山が電極。ガス空隙のセルだけ谷が 1 つ深く"
                               "落ち、そこから先の山が押し上げられている。")
        # 端から 2 枚目の層の界面(平面度の中身)
        fs_series = []
        z_show = (int(ELEC_Z[0] / SZ) + 3 + 0.5) * SZ      # 1 枚のスライスだけ描く
        for key, name in (("healthy", "健全"), ("uniform", "一様膨れ"),
                          ("local", "局所膨れ"), ("gas", "層間ガス空隙")):
            p = flat[key]["points"]
            if p.size:
                k = np.abs(p[:, 2] - z_show) < 0.5 * SZ    # 点は (x, y, z)
                if k.sum() >= 2:
                    o = np.argsort(p[k, 0])
                    fs_series.append((name, p[k][o, 0], p[k][o, 1]))
        figs.save_plot("flatness", fs_series,
                       xlabel="x [mm]", ylabel="界面の y 位置 [mm]",
                       title="端から 2 枚目の層の界面(z = %.2f mm の 1 断面)" % z_show,
                       caption="一様膨れは平らなまま上がる。局所膨れとガス空隙は"
                               "うねる(残差 RMS で数字になる)。")

    figs.save_table("control_group",
                    ["セル", "外形 中央 mm", "外形 平均 mm", "層数", "層厚 mm",
                     "層間隔σ mm", "空隙率 %", "真の膨張体積 mm3", "平面度 RMS mm"],
                    rows,
                    title="健全 + 外形を揃えた 3 つ ―― 内部指標だけが分ける",
                    caption="外形の 2 列はほぼ同じ。層厚・空隙率・膨張体積は違う。")

    mid = ND // 2
    figs.save_grid("map_control",
                   [_up(recs["healthy"][mid]), _up(recs["uniform"][mid]),
                    _up(recs["local"][mid]), _up(recs["gas"][mid])],
                   ["健全", "一様膨れ", "局所膨れ", "ガス空隙"],
                   title="外形のふくらみを揃えた 4 つの断面(同じ窓)", ncols=4,
                   caption="缶の外形はほぼ同じ。違いは中の層にしか出ない。")
    return {"res": res, "flat": flat, "base": base}


# --------------------------------------------------------------------------- #
# 節 4 —— 空隙の 3-D 地図
# --------------------------------------------------------------------------- #
def section_voidmap(cells, recs) -> dict:
    print("\n" + "=" * 78)
    print("4) 空隙を 3-D で拾う —— 位置と体積を真値と突き合わせる")
    print("=" * 78)

    vol = recs["gas"]
    t = cells["gas"]["truth"]
    dark, lab, big, roi = detect_voids(vol, SPACING, liquid_level(vol))
    est = float(sum(p["volume"] for p in big))
    print("  真値: 空隙 3 個 / 合計体積 %.4f mm3" % t["void_volume"])
    print("  推定: %d 個 / 合計体積 %.4f mm3 (%+.1f %%)"
          % (len(big), est, 100.0 * (est - t["void_volume"]) / t["void_volume"]))
    for p in big[:4]:
        cz, cy, cx = p["centroid"]
        print("     重心 (z %.2f, y %.2f, x %.2f) mm  体積 %.4f mm3"
              % (cz * SZ, cy * SY, cx * SX, p["volume"]))
    print("  ★体積が過小に出るのは、レンズ形の空隙の**縁が薄い**から ——"
          " しきい値は厚い中央しか拾えない(部分体積効果)。")

    # 疑似カラーの空隙地図: ラベルを y 方向へ最大値投影(z-x 平面の地図)
    # 疑似カラーの空隙**厚み**地図 [mm](y 方向に積算。z は等方に伸ばす)
    est_map = _up(dark.sum(axis=1) * SY, ky=6, kx=2)
    truth_map = _up(cells["gas"]["void"].sum(axis=1) * SY, ky=6, kx=2)
    print("     空隙の厚みの最大: 真値 %.3f mm / 推定 %.3f mm"
          % (truth_map.max(), est_map.max()))
    figs.save_grid("void_map", [truth_map, est_map],
                   ["真値の厚み mm", "CT の厚み mm"],
                   title="空隙の厚み地図(y 方向に積算、z は等方表示)", ncols=2,
                   caption="位置は当たる。縁が薄いところは落ちるので体積は過小。")
    figs.save_grid("void_slices",
                   [_up(recs["gas"][ND // 2]), _up(dark[ND // 2])],
                   ["CT 断面", "拾った空隙"],
                   title="空隙のしきい値検出(z 中央の断面)", ncols=2)
    return {"est": est, "true": t["void_volume"], "n": len(big)}


# --------------------------------------------------------------------------- #
# 節 5 —— 電極ずれ
# --------------------------------------------------------------------------- #
def section_misalign(cells, recs) -> dict:
    print("\n" + "=" * 78)
    print("5) 電極ずれ —— 層ごとの端の位置から 1 層あたりのずれを出す")
    print("=" * 78)
    t = cells["misalign"]["truth"]
    m = misalign_slope(recs["misalign"], t)
    m0 = misalign_slope(recs["healthy"], cells["healthy"]["truth"])
    print("  真値 %.4f mm/層 -> 推定 %.4f mm/層 (%+.1f %%、%d 層で回帰)"
          % (t["shift"], m["slope"], 100.0 * (m["slope"] - t["shift"]) / t["shift"],
             m["n"]))
    print("  対照(健全、ずれ 0): 推定 %.4f mm/層 —— これが測定系の零点"
          % m0["slope"])
    o = outer_metrics(recs["misalign"])
    o0 = outer_metrics(recs["healthy"])
    print("  ★外形はまったく動かない(中央 %.3f -> %.3f mm、差 %+.4f mm)。"
          " ずれは体積を変えないので、外形指標には**原理的に**出ない。"
          % (o0["caliper"], o["caliper"], o["caliper"] - o0["caliper"]))

    idx = np.asarray(m["idx"], float)
    figs.save_plot("misalign",
                   [("測定した電極端 x", idx, np.asarray(m["x"])),
                    ("真値の直線", idx,
                     m["intercept"] + t["shift"] * idx),
                    ("健全セル", np.asarray(m0["idx"], float), np.asarray(m0["x"]))],
                   xlabel="層番号", ylabel="電極端の x 位置 [mm]",
                   title="電極ずれは層番号に対する直線として出る",
                   caption="外形指標はこの劣化に完全に盲目(体積が変わらない)。")
    return {"slope": m["slope"], "true": t["shift"], "zero": m0["slope"],
            "d_outer": o["caliper"] - o0["caliper"]}


# --------------------------------------------------------------------------- #
# 節 6 —— 崖(1): 分解能。標本化定理の側から先に予測して突き合わせる
# --------------------------------------------------------------------------- #
def section_resolution(cells, sinos) -> dict:
    print("\n" + "=" * 78)
    print("6) 崖(1) 分解能 —— ボクセルが層厚の何倍で層は融合するか")
    print("=" * 78)
    v_nyq = 0.5 * PITCH
    v_gap = 0.5 * GAP
    print("  ★先に予測を 2 つ立てる(測る前に書く):")
    print("   予測 A(標本化定理): 層は周期 %.3f mm の縞なので voxel < %.3f mm。"
          " 電極厚 %.3f mm との比では **voxel/層厚 = %.2f が崖**。"
          % (PITCH, v_nyq, T_ELEC, v_nyq / T_ELEC))
    print("   予測 B(狭いほうの特徴): 層を 1 枚ずつ分けるには**隙間 %.3f mm** の"
          "ほうを 2 標本で跨ぐ必要がある -> voxel < %.3f mm、**比では %.2f**。"
          % (GAP, v_gap, v_gap / T_ELEC))
    print("     A は縞が「見える」限界、B は縞を「分ける」限界。**電極厚ではなく"
          "隙間が効く**なら B が先に来るはず。")

    rec = acquire(sinos["gas"])
    truth = cells["gas"]["truth"]
    rows, ratios, n_err, t_err, v_err, mod, fftp = [], [], [], [], [], [], []
    for v in (0.04, 0.06, 0.08, 0.10, 0.12, 0.16, 0.20, 0.24):
        if v > SY + 1e-9:
            sigma = 0.6 * v
            cutoff = 1.0 / (2.0 * np.pi * sigma)          # cycles/mm
            blur = np.asarray(L.vol_fft_lowpass(rec, cutoff, SPACING))
            shape = (ND, max(8, int(round(NH * SY / v))), max(8, int(round(NW * SX / v))))
            small = np.asarray(L.vol_resize(blur, shape=shape, order=1))
            sp = (SZ, NH * SY / shape[1], NW * SX / shape[2])
        else:
            small, sp, sigma = rec, SPACING, 0.6 * SY
        m = internal_metrics(small, sp)
        ratio = sp[1] / T_ELEC
        theo = float(np.exp(-2.0 * np.pi ** 2 * sigma ** 2 / PITCH ** 2))
        ratios.append(ratio)
        n_err.append(m["n_layer"] - truth["n_layer"])
        t_err.append(100.0 * (m["t_mean"] - truth["t_mean"]) / truth["t_mean"]
                     if np.isfinite(m["t_mean"]) else np.nan)
        v_err.append(100.0 * (m["void_volume"] - truth["void_volume"])
                     / truth["void_volume"])
        mod.append(100.0 * theo)
        fftp.append(m["fft_pitch"])
        rows.append(["%.3f" % sp[1], "%.2f" % ratio, "%d" % m["n_layer"],
                     "%d..%d" % (m["n_layer_min"], m["n_layer_max"]),
                     "%.3f" % m["t_mean"], "%.3f" % m["pitch_mean"],
                     "%.3f" % m["fft_pitch"],
                     "%+.1f" % v_err[-1], "%.0f" % (100 * theo)])
        print("   voxel %.3f mm (層厚比 %.2f)  層数 %2d (%2d..%2d)  層厚 %.3f mm  "
              "層間隔 %.3f mm  FFT 周期 %.3f mm  空隙体積 %+6.1f %%  予測振幅 %3.0f %%"
              % (sp[1], ratio, m["n_layer"], m["n_layer_min"], m["n_layer_max"],
                 m["t_mean"], m["pitch_mean"], m["fft_pitch"],
                 v_err[-1], 100 * theo))

    bad = [r for r, e in zip(ratios, n_err) if abs(e) > 1]
    cliff = min(bad) if bad else float("nan")
    print("\n  ★実測の崖: 層数が 1 枚を超えて狂うのは voxel/層厚 = %.2f。"
          "予測 A(標本化)は %.2f、予測 B(隙間)は %.2f -> **B が当たり**。"
          % (cliff, v_nyq / T_ELEC, v_gap / T_ELEC))
    print("     効いているのは電極の厚み(%.3f mm)ではなく**層間の隙間**"
          "(%.3f mm)—— 狭いほうの特徴が崖を決める。" % (T_ELEC, GAP))
    ok_fft = [r for r, p in zip(ratios, fftp) if abs(p - PITCH) < 0.03 * PITCH]
    print("     **数えるのと周期を測るのは別の崖**: 周期(FFT)は"
          " voxel/層厚 %.2f まで %.3f mm を保つ(数え上げが死んだ後も 1 段生き残る)。"
          % (max(ok_fft), PITCH))

    counted = [e + truth["n_layer"] for e in n_err]
    figs.save_plot("sweep_resolution",
                   [("数えた層の数 [枚]", ratios, counted),
                    ("真値 17 枚", ratios, [truth["n_layer"]] * len(ratios)),
                    ("予測 A(標本化)", [v_nyq / T_ELEC] * 2, [0, truth["n_layer"]]),
                    ("予測 B(隙間)", [v_gap / T_ELEC] * 2, [0, truth["n_layer"]])],
                   xlabel="voxel / 電極厚", ylabel="数えた層の数 [枚]",
                   title="分解能の崖 —— 当たったのは隙間からの予測 B",
                   caption="標本化定理(A)はまだ余裕があると言うが、実際は層間の"
                           "隙間 0.120 mm を分けられなくなった時点で全滅する。")
    figs.save_plot("sweep_resolution_err",
                   [("層厚の誤差 [%](±100 で切る)", ratios,
                     [float(np.clip(e, -100, 100)) for e in t_err]),
                    ("空隙体積の誤差 [%]", ratios, v_err),
                    ("縞の予測振幅 [%]", ratios, mod)],
                   xlabel="voxel / 電極厚", ylabel="誤差 [%]",
                   title="崖の手前から壊れているもの",
                   caption="空隙体積は崖の手前から単調に痩せる(部分体積効果)。"
                           "層厚は崖を越えると意味を失う。")
    figs.save_table("sweep_resolution_table",
                    ["voxel mm", "voxel/層厚", "層数", "層数の幅", "層厚 mm",
                     "層間隔 mm", "FFT 周期 mm", "空隙体積 誤差 %", "予測 振幅 %"], rows,
                    title="分解能を振る(真値: 層 %d 枚 / 層厚 %.3f mm / 周期 %.3f mm)"
                          % (truth["n_layer"], truth["t_mean"], PITCH))
    return {"ratios": ratios, "n_err": n_err, "cliff": cliff,
            "pred_a": v_nyq / T_ELEC, "pred_b": v_gap / T_ELEC,
            "fft_ok": max(ok_fft)}


# --------------------------------------------------------------------------- #
# 節 7 —— 崖(2): 雑音とビームハードニング
# --------------------------------------------------------------------------- #
def section_noise_streak(cells, sinos) -> dict:
    print("\n" + "=" * 78)
    print("7) 崖(2) 雑音とビームハードニング —— 壊れ方を種類ごとに数える")
    print("=" * 78)
    truth = cells["gas"]["truth"]

    print("  フォトン数を振る(ビームハードニングは公称のまま):")
    n0s, n_err, v_err, sd = [], [], [], []
    for n0 in (3.0e6, 3.0e5, 1.0e5, 3.0e4, 1.0e4, 3.0e3):
        rec = acquire(sinos["gas"], n0=n0)
        m = internal_metrics(rec)
        n0s.append(np.log10(n0))
        n_err.append(m["n_layer"] - truth["n_layer"])
        v_err.append(100.0 * (m["void_volume"] - truth["void_volume"])
                     / truth["void_volume"])
        sd.append(m["pitch_sd"])
        print("   N0 = %8.0f  層数 %2d (%2d..%2d)  層厚 %.3f mm  "
              "空隙率 %.2f %% (真 %.2f %%)  層間隔σ %.3f mm"
              % (n0, m["n_layer"], m["n_layer_min"], m["n_layer_max"],
                 m["t_mean"], m["void_fraction"],
                 100.0 * truth["void_volume"] / m["roi_volume"], m["pitch_sd"]))

    print("\n  ビームハードニングを振る(硬さ比 1.0 = 単色 = むら無し):")
    bhs, bh_terr, bh_verr, bh_cal, bh_contrast = [], [], [], [], []
    for bh in (1.0, 0.85, 0.70, 0.55, 0.40):
        rec = acquire(sinos["gas"], bh=bh)
        m = internal_metrics(rec)
        o = outer_metrics(rec)
        bh_contrast.append(m["contrast"])
        bhs.append(bh)
        bh_terr.append(100.0 * (m["t_mean"] - truth["t_mean"]) / truth["t_mean"])
        bh_verr.append(100.0 * (m["void_volume"] - truth["void_volume"])
                       / truth["void_volume"])
        bh_cal.append(o["caliper"])
        print("   硬さ比 %.2f  層厚 %.3f mm (%+.1f %%)  空隙率 %.2f %% (%+.1f %%)  "
              "外形 中央 %.3f mm  コントラスト %.3f"
              % (bh, m["t_mean"], bh_terr[-1], m["void_fraction"], bh_verr[-1],
                 o["caliper"], m["contrast"]))
    print("  ★ビームハードニングは**外形指標をほとんど動かさない**"
          "(中央 %.3f -> %.3f mm、%+.3f mm)。缶と空気の縁は最も強い縁なので"
          "生き残る。" % (bh_cal[0], bh_cal[-1], bh_cal[-1] - bh_cal[0]))
    print("     層厚も動かない(%+.1f -> %+.1f %%)。壊れるのは**空隙**だけ"
          "(%+.1f %% -> %+.1f %%)—— コントラストが %.3f -> %.3f に落ちると、"
          "レンズ形の縁がしきい値を割る。"
          % (bh_terr[0], bh_terr[-1], bh_verr[0], bh_verr[-1],
             bh_contrast[0], bh_contrast[-1]))

    figs.save_plot("sweep_noise",
                   [("層数の誤差 [枚]", n0s, n_err),
                    ("空隙体積の誤差 [%]", n0s, v_err),
                    ("層間隔の散らばり x100 [mm]", n0s, [100 * s for s in sd])],
                   xlabel="log10(フォトン数 N0)", ylabel="誤差",
                   title="雑音の崖 —— 空隙が先に壊れ、層数は後から壊れる")
    figs.save_plot("sweep_beamhardening",
                   [("層厚の誤差 [%]", bhs, bh_terr),
                    ("空隙体積の誤差 [%]", bhs, bh_verr),
                    ("外形 中央 [mm] x10", bhs, [10 * c for c in bh_cal])],
                   xlabel="ビームハードニングの硬さ比(1.0 = 単色)",
                   ylabel="誤差 [%] / 外形 x10 [mm]",
                   title="低周波むらは外形を動かさず、内部指標だけを曲げる")
    return {"n0": n0s, "n_err": n_err, "v_err": v_err,
            "bh": bhs, "bh_terr": bh_terr, "bh_verr": bh_verr, "bh_cal": bh_cal}


# --------------------------------------------------------------------------- #
# 節 8 —— 測れないもの / 道具の穴
# --------------------------------------------------------------------------- #
def section_limits() -> None:
    print("\n" + "=" * 78)
    print("8) 測れないもの、と道具の穴")
    print("=" * 78)
    print("  * この PoC は **SoH(健全度)も寿命も測っていない**。測ったのは"
          "「外形指標が内部の違いに盲目であること」と「どの分解能・雑音まで"
          "内部指標が生き残るか」だけ。容量劣化との対応づけには"
          "**充放電の実測**が要る(画像だけでは原理的に出ない)。")
    print("  * 空隙率は「ガスの体積 / ROI の体積」であって、電気化学的な"
          "ガス発生量ではない(溶解した分は写らない)。")
    print("  * 3-D の落とし穴: 座標の順が 2 系統ある —— **点の op は (N,3)=(x,y,z)、"
          "ボリュームの op は (D,H,W)=(z,y,x)**。この PoC は組み立てを格子順で"
          "通し、最後に 1 回だけ転置している(`to_volume`)。")
    print("  * `fit_plane_3d` の法線は**符号が任意**。平面度(残差)は符号に"
          "依らないので使えるが、傾きの向きを言うときは基準が要る。")

    print("\n  公開経路に無かった処理(自前で書いた):")
    assert not hasattr(fs, "sdf_offset_field") and not hasattr(L, "sdf_offset_field")
    print("   (a) `sdf_offset` は**スカラのみ**。場でゼロ等値面を動かす口が無い"
          "(缶のたわみは格子を歪めて評価した)。")
    assert not hasattr(fs, "vol_convolve") and not hasattr(L, "vol_convolve")
    print("   (b) `vol_gaussian_psf` で PSF は作れるのに、それで**畳み込む** op が"
          "無い(`vol_richardson_lucy` は逆問題側だけ)。ぼけは"
          " `vol_fft_lowpass` の伝達関数 exp(-f²/2c²) を σ=1/(2πc) と読み替えて使った。")
    assert not any(hasattr(o, n) for o in (fs, L) for n in ("profile_period",
                                                            "autocorrelation_1d"))
    print("   (c) 1-D プロファイルの**卓越周期・自己相関**を出す op が無い"
          "(積層のような周期構造では層を数えるより頑健なのに)。")
    print("   (d) 二値ボリュームの**外形が囲む高さ/体積**(穴を埋めた包絡)を出す口が"
          "無い。缶の外形高さは列ごとに自前で数えた。")
    assert hasattr(L, "grid_coords") and not hasattr(fs, "grid_coords")
    print("   (e) `grid_coords` / `plane_sdf` / `box_sdf` / `sdf_*` / `esdf` /"
          " `render_volume_projection` / `fit_plane_3d` は `fullseye.ledger` 経由のみ"
          "(1 行ファサードには出ていない)。")


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.perf_counter()
    print("=" * 78)
    print("電池セルの劣化を CT で測る —— 膨れは外から見え、原因は中にある")
    print("=" * 78)

    # --- 4 通りのセルを作る。局所膨れとガス空隙は**外形のふくらみを揃える** ---
    cells = {"healthy": build_cell("healthy"), "uniform": build_cell("uniform")}
    target = cells["uniform"]["truth"]["mean_excess"]
    s_local = match_to_bulge("local", target)
    s_gas = match_to_bulge("gas", target)
    cells["local"] = build_cell("local", s_local)
    cells["gas"] = build_cell("gas", s_gas)
    cells["misalign"] = build_cell("misalign")
    print("  外形のふくらみを揃える(面平均のはみ出し %.4f mm):"
          " 局所膨れの倍率 %.4f / ガス空隙の倍率 %.4f" % (target, s_local, s_gas))

    sinos = {k: forward(c["mu"]) for k, c in cells.items()}
    print("  順投影 %d 条件 x %d 角 (%.1f 秒経過)" % (
        len(sinos), N_ANGLE, time.perf_counter() - t0))
    recs = {k: acquire(s) for k, s in sinos.items()}

    scene = section_scene(cells, recs)
    outer = section_outer_blindness(cells, recs)
    ctrl = section_control(cells, recs)
    void = section_voidmap(cells, recs)
    mis = section_misalign(cells, recs)
    resn = section_resolution(cells, sinos)
    noise = section_noise_streak(cells, sinos)
    section_limits()

    # --- 所見を固定する(壊れたら鳴る)---
    assert 25.0 < outer["frac"] < 35.0, outer["frac"]
    assert abs(outer["frac"] - outer["pred"]) < 2.0, (outer["frac"], outer["pred"])
    assert 3.0 < outer["ratio"] < 5.5, outer["ratio"]
    assert ctrl["res"]["uniform"]["inner"]["t_mean"] > \
        ctrl["res"]["gas"]["inner"]["t_mean"] + 0.005
    assert ctrl["res"]["gas"]["inner"]["void_fraction"] > \
        5.0 * ctrl["res"]["uniform"]["inner"]["void_fraction"] + 0.1
    assert abs(mis["slope"] - mis["true"]) < 0.25 * mis["true"]
    assert abs(mis["d_outer"]) < 0.02
    assert np.isfinite(resn["cliff"])

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * 一様膨れ %.0f %% のうち外形に出るのは %.1f %%。残りは"
          "クリアランスが飲む。" % (100 * ALPHA_UNIFORM, outer["frac"]))
    print("  * 中央のノギスは体積等価な平均の %.1f 倍を読む。" % outer["ratio"])
    print("  * 外形を揃えた 3 つのセルは、層厚・空隙率・平面度で分かれる。")
    print("  * 分解能の崖は voxel/層厚 = %.2f。標本化定理からの予測 %.2f では"
          "なく、**隙間から**の予測 %.2f が当たった。周期の測定は %.2f まで持つ。"
          % (resn["cliff"], resn["pred_a"], resn["pred_b"], resn["fft_ok"]))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
