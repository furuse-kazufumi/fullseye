# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC ⑱: 世界を広げる —— 閉形式の地形と世界座標の材質、手続きの木と歩行者で、拡大の中心を流れから取り戻す。

15 巡目の教習所は、コースの外 8 m で世界が終わり、路面に模様が無かった。だから光学流は車と街灯にしか無く、
拡大の中心(FoE)は「既知」にするしかなかった(流れから出すと 62 px 外れた)。この PoC は世界を **生成の時に真値を
持たせたまま** 広げる(:mod:`driveterrain`):

  地形 = 乱数位相の正弦の和(fBm のスペクトル合成、Saupe 1988)。高さも勾配も閉形式で、パワースペクトルは f^{−(2H+2)}。
         道の周り 2 m は平らで、そこから 12 m かけて起伏に繋がる(コースへの距離場は点-線分の閉形式、|∇d| = 1)。
         路面には長波長のうねり(振幅 0.8 m、勾配 ≤ 2.3 %)を掛け、自車は坂を上り下りする。
  材質 = 描画した深度から画素の世界座標を戻し、Perlin(2002)の勾配雑音を世界座標で評価する: アスファルトの粒、草むら、
         暗い染み(ラベルは道のまま)、水溜り(空の写り込み、ラベル 11)、摩耗した白線(摩耗率 wear が真値)。
  物体 = 手続きの木(角柱 + 円錐 / 回転楕円体、体積の閉形式)、歩行者(箱 + 回転体)、横断歩道(縞の数と面積の閉形式)、
         道の外への散布(コースから 4 m 以上・互いに 5 m 以上)。標識・街灯は Kenney の CC0 資産。

門(真値の出どころ):
  1. **Perlin の定理**: 格子点で 0、周期 256、解析的な導関数が中心差分と 1e-6 で一致。
  2. **fBm のスペクトル**: 512 × 512 の周期図の log–log 傾き β̂ が 2H + 2(H = 0.8 → 3.6)と 0.25 以内(有限の帯域と窓で +0.1 の偏り)。
  3. **eikonal**: コースへの距離場は道の外で |∇d| = 1(中心差分、中央値 1e-6)、道の内側は 0。
  4. **地形の恒等式**: 勾配の閉形式は中心差分と 1e-6、メッシュの頂点は閉形式そのもの(0)、道の上は うねり だけ。
  5. **描いた世界は式どおり**: 車載カメラの深度から戻した路面の画素の高さが閉形式と一致(中央値 < 1 cm、99 % < 15 cm =
     2 m 升の弦の誤差)、水溜りの画素は全部道の内側、地形の画素は全部道の外側、白線の色 = 白と路面の摩耗率での混色 × 陰影(1e-9)。
  6. **体積の閉形式**: 針葉樹(角柱 + 多角錐)の体積は発散定理のメッシュ体積と 1e-9、広葉樹と頭(回転楕円体・球)は内接で上界の 0.8〜1 倍、
     横断歩道の面積 = 縞の数 × 幅 × 長さ。
  7. **散布の約束**: 木は互いに 5 m 以上、道から 4 m 以上。
  8. **FoE の定理**: 純並進の真の流れは FoE から放射状 —— foe_from_flow(真の流れ)は foe_from_motion と 1e-6 で一致(全コマ、坂の上り下りで
     FoE が像の中を動いても)。
  9. **模様が FoE を取り戻す**: 路面の画素の LK の流れだけから出した FoE は、模様ありで中央値 ≤ 12 px、模様なし(同じ地形・同じ木)は
     その 2 倍以上外れる。
 10. **判りにくい物は本当に判りにくい**: 摩耗した白線と水溜りは明るさのしきい値(向きはどちらでも)では最良でも 1 割以上を間違える(均衡誤り率)——
     真値(ラベル・wear・puddle)は生成時に画素単位で厳密なので、その間違いを数えられる。

正直に書くこと: 木・歩行者は箱と回転体(実物の形ではない)。水溜りの写り込みは空の色を混ぜただけ(鏡面反射の幾何ではない)。
FoE の推定誤差 5〜10 px は LK の偏り込みで、坂の頂点付近で流れが小さい。自車は歩行者に対して制動しない(制動は第 3 回)。

Run: py -3.11 examples/poc_world_terrain.py   (図は FULLSEYE_FIGURE_DIR を設定したときだけ書く)
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import drivecourse as DC  # noqa: E402
import driveworld as DW  # noqa: E402
import driveterrain as DTR  # noqa: E402
import drivettc as TT  # noqa: E402
import flow as FL  # noqa: E402
import annotate as AN  # noqa: E402

T0 = time.time()
LOOP_R, LOOP_S, LOOP_W = 30.0, 80.0, 8.0
Y_EGO = -LOOP_R + 2.0                 # 南の直線の北側の車線(左側通行、東行き)
V_EGO = 6.0
DT_LK = 1.0 / 30.0                    # LK のコマ間隔(路面の流れを十数画素に収める)
DT_OUT = 0.2                          # 記録・GIF のコマ間隔
T_END = 10.0
HURST = 0.8
X_CROSS = 20.0                        # 横断歩道
X_PED, Y_PED0, V_PED, T_PED0 = 18.0, -36.5, 1.5, 0.0     # 自車(x = 20 に t = 10)が着く前に渡り終える(t = 8.7)
CAM_FWD, CAM_H = 1.0, 1.35
OK = []
PAL = np.array([[0.62, 0.75, 0.92], [0.40, 0.41, 0.43], [0.80, 0.80, 0.75], [0.90, 0.20, 0.20], [1.0, 0.55, 0.0],
                [1.0, 1.0, 0.0], [0.90, 0.40, 0.90], [0.55, 0.55, 0.55], [1.0, 0.30, 0.60], [0.35, 0.35, 0.35],
                [1.0, 1.0, 1.0], [0.36, 0.55, 0.25], [0.20, 0.50, 1.0], [1.0, 0.85, 0.30], [0.10, 0.60, 0.20]])


def gate(name, cond, detail=""):
    OK.append(bool(cond))
    print("  [%s] %s %s" % ("PASS" if cond else "FAIL", name, detail))


def _quiver(img, pts, vecs, color=(0.90, 0.62, 0.0), head: float = 3.0):
    """多数の短い矢印を一度に描く(軸 = 線分の標本点、矢じり = 2 本の短い線)。annotate.arrow は 1 本 19 ms なので
    GIF の何万本には使えない。``pts``/``vecs`` は (m, 2) の (col, row)。"""
    H, W = img.shape[:2]
    out = np.array(img, np.float64, copy=True)
    P = np.asarray(pts, np.float64).reshape(-1, 2)
    V = np.asarray(vecs, np.float64).reshape(-1, 2)
    L = np.hypot(V[:, 0], V[:, 1])
    ok = L > 1e-9
    if not ok.any():
        return out
    P, V, L = P[ok], V[ok], L[ok]
    n = int(np.ceil(L.max())) + 2
    t = np.linspace(0.0, 1.0, n)
    shaft = P[:, None, :] + t[None, :, None] * V[:, None, :]
    u = V / L[:, None]
    tip = P + V
    c, s_ = math.cos(math.radians(150.0)), math.sin(math.radians(150.0))
    h1 = np.stack([u[:, 0] * c - u[:, 1] * s_, u[:, 0] * s_ + u[:, 1] * c], 1)
    h2 = np.stack([u[:, 0] * c + u[:, 1] * s_, -u[:, 0] * s_ + u[:, 1] * c], 1)
    th = np.linspace(0.0, 1.0, int(head) + 2)
    heads = np.concatenate([tip[:, None, :] + th[None, :, None] * head * h1[:, None, :],
                            tip[:, None, :] + th[None, :, None] * head * h2[:, None, :]], 1)
    A = np.concatenate([shaft.reshape(-1, 2), heads.reshape(-1, 2)], 0)
    cc = np.rint(A[:, 0]).astype(int)
    rr = np.rint(A[:, 1]).astype(int)
    m = (cc >= 0) & (cc < W) & (rr >= 0) & (rr < H)
    out[rr[m], cc[m]] = color
    return out


def main() -> int:
    """PoC の本体(examples の門: 実行は __main__ の守りの下で)。"""
    # ─────────────────────────────── 1. 雑音と地形の定理 ─────────────────────────────
    print("== 1. Perlin の勾配雑音と fBm のスペクトル合成(閉形式)")
    rng = np.random.default_rng(16)
    x = rng.uniform(-100, 100, 4000)
    y = rng.uniform(-100, 100, 4000)
    e = 1e-5
    n = DTR.perlin2(x, y, 7, 0.7)
    i = np.arange(-12, 12)
    LX, LY = np.meshgrid(i / 0.7, i / 0.7)
    lat = np.abs(DTR.perlin2(LX, LY, 7, 0.7)["value"]).max()
    per = np.abs(DTR.perlin2(x + 256 / 0.7, y - 256 / 0.7, 7, 0.7)["value"] - n["value"]).max()
    fdx = (DTR.perlin2(x + e, y, 7, 0.7)["value"] - DTR.perlin2(x - e, y, 7, 0.7)["value"]) / (2 * e)
    fdy = (DTR.perlin2(x, y + e, 7, 0.7)["value"] - DTR.perlin2(x, y - e, 7, 0.7)["value"]) / (2 * e)
    g_err = max(np.abs(fdx - n["dx"]).max(), np.abs(fdy - n["dy"]).max())
    print("  Perlin: 格子点の |値| 最大 %.1e、周期 256 の誤差 %.1e、値域 [%.3f, %.3f]、導関数の誤差 %.1e" % (
        lat, per, n["value"].min(), n["value"].max(), g_err))
    gate("Perlin の定理: 格子点で 0、周期 256、解析的な導関数 = 中心差分", lat < 1e-12 and per < 1e-10 and g_err < 1e-6
         and np.abs(n["value"]).max() <= 1.0)

    TP = DTR.terrain_params(16, hurst=HURST, amplitude=2.5, f_min=1 / 120.0, f_max=1 / 6.0, n_waves=1024,
                            flat=2.0, blend=12.0, road_amp=0.8, road_len=(160.0, 110.0), road_phase=(1.963, 2.1))   # 峠は x = −10(t = 5 s)
    N = 512
    xs = np.arange(N) * 1.0
    XG, YG = np.meshgrid(xs, xs)
    t_sp = time.time()
    Z = DTR.fbm_height(XG, YG, TP)
    sl = DTR.spectral_slope(Z, 1.0, 1 / 100.0, 1 / 10.0, n_bins=64)
    pg = DTR.radial_periodogram(Z, 1.0, 64)
    beta_th = 2 * HURST + 2
    print("  fBm(H = %.1f、%d 波、f ∈ [1/120, 1/6] 周期/m、RMS %.2f m): 512² の周期図の傾き β̂ = %.3f、定理 2H + 2 = %.1f(%d 帯、%.1f s)" % (
        HURST, len(TP["f"]), Z.std(), sl["beta"], beta_th, sl["n"], time.time() - t_sp))
    gate("fBm のスペクトル: |β̂ − (2H + 2)| < 0.25", abs(sl["beta"] - beta_th) < 0.25, "差 %+.3f" % (sl["beta"] - beta_th))
    hx, hy = DTR.fbm_gradient(x, y, TP)
    fd = (DTR.fbm_height(x + e, y, TP) - DTR.fbm_height(x - e, y, TP)) / (2 * e)
    fbm_g_err = np.abs(fd - hx).max()

    # ─────────────────────────────── 2. 世界 ─────────────────────────────
    print("== 2. 教習所の周回コースを起伏の中に置き、材質・木・標識・横断歩道・歩行者を足す")
    LOOP = DC.course_loop(LOOP_S, LOOP_R, LOOP_W)
    LAYOUT = DC.course_layout(LOOP["elements"], LOOP["placements"])
    q = np.column_stack([rng.uniform(-90, 90, 3000), rng.uniform(-80, 80, 3000)])
    dq = DTR.course_distance(LAYOUT, q)
    ddx = (DTR.course_distance(LAYOUT, q + [e, 0])["d"] - DTR.course_distance(LAYOUT, q - [e, 0])["d"]) / (2 * e)
    ddy = (DTR.course_distance(LAYOUT, q + [0, e])["d"] - DTR.course_distance(LAYOUT, q - [0, e])["d"]) / (2 * e)
    off = dq["d"] > 0.5
    gd = np.hypot(ddx, ddy)[off]
    ins = DC.course_contains(LAYOUT, q)
    print("  コースへの距離場: 道の外 %d 点で |∇d| の中央値 %.8f、99 %% 点 %.6f、道の内側 %d 点は d = %.1e" % (
        off.sum(), np.median(gd), np.percentile(gd, 99), ins.sum(), np.abs(dq["d"][ins]).max()))
    gate("eikonal: 道の外で |∇d| = 1(中央値 1e-6、99 % 点 1e-3)、道の内側で d = 0",
         abs(np.median(gd) - 1) < 1e-6 and abs(np.percentile(gd, 99) - 1) < 1e-3 and np.abs(dq["d"][ins]).max() == 0.0)
    gx, gy = DTR.terrain_gradient(q[:, 0], q[:, 1], TP, LAYOUT)
    fdt = (DTR.terrain_height(q[:, 0] + e, q[:, 1], TP, LAYOUT) - DTR.terrain_height(q[:, 0] - e, q[:, 1], TP, LAYOUT)) / (2 * e)
    tg_err = np.percentile(np.abs(fdt - gx), 99)
    z_in = DTR.terrain_height(q[ins, 0], q[ins, 1], TP, LAYOUT) - DTR._road_wave(q[ins, 0], q[ins, 1], TP)[0]
    WORLD = DW.world_build(LAYOUT, props=[("street_light", -20.0, -25.0, 0.0), ("street_light", 10.0, -25.0, 0.0),
                                          ("sign_stop", 15.0, -25.3, -math.pi / 2), ("sedan", -10.0, LOOP_R + 2.0, math.pi),
                                          ("truck", 30.0, LOOP_R - 2.0, 0.0), ("cone", 36.0, -30.0, 0.0)],
                           ground_margin=40.0, ground_step=2.0)
    n_flat = len(WORLD["V"])
    DTR.world_apply_terrain(WORLD, TP, step=2.0)
    Vg = WORLD["V"][slice(*WORLD["objects"][0]["verts"])]
    mesh_err = np.abs(Vg[:, 2] - DTR.terrain_height(Vg[:, 0], Vg[:, 1], TP, LAYOUT)).max()
    print("  地形: 勾配の閉形式 vs 中心差分 %.1e(fBm 単体 %.1e)、メッシュ %d 頂点の高さ = 閉形式 %.1e、道の上の高さ = うねり(%.1e)、"
          "起伏 [%.2f, %.2f] m" % (tg_err, fbm_g_err, len(Vg), mesh_err, np.abs(z_in).max(), Vg[:, 2].min(), Vg[:, 2].max()))
    gate("地形の恒等式: 勾配 = 中心差分(1e-6)、メッシュの頂点 = 閉形式(0)、道の上 = うねりだけ(0)",
         tg_err < 1e-6 and mesh_err == 0.0 and np.abs(z_in).max() == 0.0)
    trees = DTR.scatter_offroad(LAYOUT, WORLD["bounds"], n=70, r_min=5.0, margin=4.0, seed=16)
    Pt = trees[:, :2]
    Dt = np.hypot(Pt[:, None, 0] - Pt[None, :, 0], Pt[:, None, 1] - Pt[None, :, 1])
    np.fill_diagonal(Dt, np.inf)
    d_road = DTR.course_distance(LAYOUT, Pt)["d"]
    for k, (tx, ty, tyaw) in enumerate(trees):
        kind = "conifer" if k % 3 == 0 else "broadleaf"
        h = float(rng.uniform(4.5, 8.0))
        m = DTR.tree_mesh(h, 0.12 + 0.02 * h, 0.28 * h if kind == "broadleaf" else 0.2 * h, kind)
        z = float(DTR.terrain_height(np.array([tx]), np.array([ty]), TP, LAYOUT)[0])
        DTR.add_mesh_object(WORLD, m, tx, ty, tyaw, name="tree", z=z)
    cw = DTR.crosswalk_mesh((X_CROSS, -LOOP_R - LOOP_W / 2), (X_CROSS, -LOOP_R + LOOP_W / 2), 4.0, 0.45, 0.45)
    Vc = cw["V"].copy()
    Vc[:, 2] += DTR.terrain_height(Vc[:, 0], Vc[:, 1], TP, LAYOUT)
    DW.world_add(WORLD, Vc, cw["F"], cw["label"], cw["color"], name="crosswalk")
    PED_M = DTR.pedestrian_mesh(1.7)
    PED = DTR.add_mesh_object(WORLD, PED_M, X_PED, Y_PED0, math.pi / 2, name="pedestrian",
                              z=float(DTR.terrain_height(np.array([X_PED]), np.array([Y_PED0]), TP, LAYOUT)[0]))
    print("  世界: 三角形 %d(平らな世界 %d 頂点 → %d 頂点)、木 %d 本(互いに %.2f m 以上、道から %.2f m 以上)、横断歩道 %d 縞、歩行者 1 人、"
          "資産 6 個" % (len(WORLD["F"]), n_flat, len(WORLD["V"]), len(trees), Dt.min(), d_road.min(), cw["n_stripes"]))
    gate("散布の約束: 木は互いに 5 m 以上、道から 4 m 以上", Dt.min() >= 5.0 and d_road.min() >= 4.0 and len(trees) == 70)
    tc = DTR.tree_mesh(6.0, 0.15, 1.6, "conifer")
    tb = DTR.tree_mesh(6.0, 0.15, 1.8, "broadleaf")
    v_c = DTR.mesh_signed_volume(tc["V"], tc["F"])
    v_b = DTR.mesh_signed_volume(tb["V"], tb["F"]) - tb["volume"]["trunk"]
    v_p = DTR.mesh_signed_volume(PED_M["V"], PED_M["F"]) - PED_M["volume"]["boxes"]
    print("  体積: 針葉樹 %.6f = 閉形式 %.6f、広葉樹の冠 %.3f ≤ 楕円体 %.3f(%.3f 倍)、頭 %.5f ≤ 球 %.5f(%.3f 倍)、横断歩道 %d 縞 × 0.45 × 4 = %.2f m²" % (
        v_c, tc["volume"]["trunk"] + tc["volume"]["crown"], v_b, tb["volume"]["crown"], v_b / tb["volume"]["crown"],
        v_p, PED_M["volume"]["head_max"], v_p / PED_M["volume"]["head_max"], cw["n_stripes"], cw["area"]))
    gate("体積の閉形式: 針葉樹 1e-9、内接の回転体は上界の 0.8〜1 倍、横断歩道の面積 = 縞 × 幅 × 長さ",
         abs(v_c - tc["volume"]["trunk"] - tc["volume"]["crown"]) < 1e-9 and 0.8 <= v_b / tb["volume"]["crown"] <= 1.0
         and 0.8 <= v_p / PED_M["volume"]["head_max"] <= 1.0 and abs(cw["area"] - cw["n_stripes"] * 0.45 * 4.0) < 1e-12)

    MAT = DTR.material_params(16, grain=0.15, puddle_level=0.42, stain_level=0.4, wear=0.5)
    MAT_PLAIN = DTR.material_params(16, grain=0.0, puddle_level=2.0, stain_level=2.0, wear=0.0, grass_var=0.0)

    def ego_x(t):
        return -40.0 + V_EGO * t

    def eye_of(t):
        xe = ego_x(t) + CAM_FWD
        return (xe, Y_EGO, float(DTR.terrain_height(np.array([xe]), np.array([Y_EGO]), TP, LAYOUT)[0]) + CAM_H)

    def cam_pose(t):
        ex, ey, ez = eye_of(t)
        return DW.camera_pose((ex, ey, ez), (ex + 20.0, ey, ez - 0.45))         # 向きは固定(純並進)、高さは路面に追従

    def ped_y(t):
        return Y_PED0 + V_PED * max(0.0, min(t - T_PED0, (-Y_PED0 - 23.5) / V_PED))

    def set_scene(t):
        yp = ped_y(t)
        zp = float(DTR.terrain_height(np.array([X_PED]), np.array([yp]), TP, LAYOUT)[0])
        DW.world_move(WORLD, PED, X_PED, yp, math.pi / 2, z=zp)

    def render(t, K, w, h, mat):
        set_scene(t)
        P = cam_pose(t)
        v = DW.world_camera(WORLD, P, K, w, h)
        return DTR.world_materials(WORLD, v, P, K, mat), v, P

    # ─────────────────────────────── 3. 描いた世界は式どおりか ─────────────────────────────
    print("== 3. 車載カメラ(60°, 640 × 400)で撮り、深度から戻した世界座標で材質・高さ・ラベルを検算する")
    K = DW.camera_intrinsics(60.0, 640, 400)
    mat3, v3, P3 = render(6.0, K, 640, 400, MAT)
    xyz = mat3["xyz"]
    lab = mat3["label"]
    grd = (lab == 0) | (lab == 10) | (lab == 11)
    zt = DTR.terrain_height(xyz[grd][:, 0], xyz[grd][:, 1], TP, LAYOUT)
    dz = np.abs(xyz[grd][:, 2] - zt)
    in_p = DC.course_contains(LAYOUT, xyz[lab == 11][:, :2])
    in_t = DC.course_contains(LAYOUT, xyz[lab == 10][:, :2])
    lines = (lab == 9) | (lab == 12)
    w_ = mat3["wear"][lines]
    grain = DTR.perlin2(xyz[lines][:, 0], xyz[lines][:, 1], MAT["seed"] + 1, 8.0)["value"]
    road = np.asarray(DTR._ROAD_COLOR) * (1.0 + MAT["grain"] * grain[:, None])
    pred = np.clip((np.asarray(DTR._LINE_COLOR) * (1 - w_)[:, None] + road * w_[:, None]) * v3["shade"][lines][:, None], 0, 1)
    c_err = np.abs(pred - mat3["color"][lines]).max()
    cnt = {DW.LABELS.get(int(k), str(k)): int(c) for k, c in zip(*np.unique(lab, return_counts=True)) if k >= 0}
    print("  路面・地形・水溜りの画素 %d: 高さの誤差 中央値 %.4f m、99 %% 点 %.3f m(2 m 升の弦)。水溜り %d 画素は道の内側 %d、地形 %d 画素は道の外側 %d。"
          "白線 %d 画素の色 = 混色 × 陰影(誤差 %.1e)。ラベル: %s" % (
              grd.sum(), np.median(dz), np.percentile(dz, 99), in_p.size, in_p.sum(), in_t.size, (~in_t).sum(), lines.sum(), c_err, cnt))
    gate("描いた世界は式どおり: 高さ(中央値 < 1 cm、99 % < 15 cm)、水溜りは道の内側、地形は道の外側、白線の色は摩耗率の混色",
         np.median(dz) < 0.01 and np.percentile(dz, 99) < 0.15 and in_p.size > 0 and in_p.all() and (~in_t).all() and c_err < 1e-9)
    # 判りにくい物: 摩耗した白線と水溜りの明るさ
    br = mat3["color"].mean(-1)
    b_line = br[lines]
    b_pud = br[lab == 11]
    ths = np.linspace(0.0, 1.0, 201)
    err_up = np.array([0.5 * (np.mean(b_line < th) + np.mean(b_pud >= th)) for th in ths])     # 「明るい方が白線」
    err_dn = np.array([0.5 * (np.mean(b_line >= th) + np.mean(b_pud < th)) for th in ths])     # 「暗い方が白線」
    err = np.minimum(err_up, err_dn)
    kb = int(np.argmin(err))
    ovl = float(err[kb])
    rule = "明るい方が白線" if err_up[kb] <= err_dn[kb] else "暗い方が白線"
    print("  判りにくい物: 白線 %d 画素(明るさ %.2f〜%.2f、摩耗率で変わる)と水溜り %d 画素(%.2f〜%.2f、路面 %.2f)。明るさのしきい値は向きを選んでも"
          "最良(θ = %.2f、%s)で均衡誤り率 %.0f %%" % (
              b_line.size, b_line.min(), b_line.max(), b_pud.size, b_pud.min(), b_pud.max(), np.median(br[lab == 0]), ths[kb], rule, 100 * ovl))
    gate("判りにくい物: 明るさのしきい値では向きを選んでも最良で 1 割以上を間違える(真値は画素単位で厳密)", ovl >= 0.1 and b_pud.size > 50 and b_line.size > 50)

    # ─────────────────────────────── 4. FoE を流れから ─────────────────────────────
    print("== 4. 0 → %.0f s(%.0f m/s、坂を上り下り)を 30 fps の 2 コマずつ撮り、拡大の中心を流れから出す" % (T_END, V_EGO))
    Kg = DW.camera_intrinsics(60.0, 480, 300)
    t_out = np.round(np.arange(0.0, T_END + 1e-9, DT_OUT), 6)
    R = {k: [] for k in ("t", "grade", "foe_true", "foe_ident_err", "foe_road", "foe_all", "err_road", "err_all", "n_road",
                         "lk_err", "frame", "u", "v", "foe_plain", "err_plain")}
    t_r = time.time()
    for t in t_out:
        m0, v0, P0 = render(t, Kg, 480, 300, MAT)
        m1, v1, P1 = render(t + DT_LK, Kg, 480, 300, MAT)
        T_rel = TT.relative_motion(P0, P1)
        foe = TT.foe_from_motion(Kg, T_rel)
        tru = TT.flow_from_depth_motion(v0["depth"], Kg, T_rel)
        valid = tru["valid"] & (m0["label"] >= 0)
        ident = TT.foe_from_flow(tru["u"], tru["v"], valid)["foe"]
        u, v = FL.optical_flow_lk(m0["color"].mean(-1), m1["color"].mean(-1), window=15, levels=5)
        roadm = valid & (m0["label"] == 0)
        f_road = TT.foe_from_flow(u, v, roadm, max_speed=12.0)
        f_all = TT.foe_from_flow(u, v, valid, max_speed=12.0)
        lk = np.hypot(u - tru["u"], v - tru["v"])[roadm & np.isfinite(u)]
        gr = DTR.terrain_gradient(np.array([ego_x(t)]), np.array([Y_EGO]), TP, LAYOUT)[0][0]
        R["t"].append(t)
        R["grade"].append(gr)
        R["foe_true"].append(foe)
        R["foe_ident_err"].append(np.hypot(*(np.asarray(ident) - foe)))
        R["foe_road"].append(f_road["foe"])
        R["foe_all"].append(f_all["foe"])
        R["err_road"].append(np.hypot(*(np.asarray(f_road["foe"]) - foe)))
        R["err_all"].append(np.hypot(*(np.asarray(f_all["foe"]) - foe)))
        R["n_road"].append(f_road["n"])
        R["lk_err"].append(np.median(lk) if lk.size else np.nan)
        R["frame"].append(m0)
        R["u"].append(u)
        R["v"].append(v)
        if abs(t - round(t)) < 1e-6:                                             # 模様なしは 1 s ごと
            p0, w0, Q0 = render(t, Kg, 480, 300, MAT_PLAIN)
            p1, w1, Q1 = render(t + DT_LK, Kg, 480, 300, MAT_PLAIN)
            up, vp = FL.optical_flow_lk(p0["color"].mean(-1), p1["color"].mean(-1), window=15, levels=5)
            fp = TT.foe_from_flow(up, vp, valid & (p0["label"] == 0), max_speed=12.0)
            R["foe_plain"].append(fp["foe"])
            R["err_plain"].append(np.hypot(*(np.asarray(fp["foe"]) - foe)))
    for k in ("t", "grade", "foe_ident_err", "err_road", "err_all", "n_road", "lk_err", "err_plain"):
        R[k] = np.asarray(R[k], np.float64)
    R["foe_true"] = np.asarray(R["foe_true"])
    sel_int = np.abs(R["t"] - np.round(R["t"])) < 1e-6
    print("  %d コマ(%.1f s)。FoE の真値は坂で像の中を動く: 行 %.1f〜%.1f px(勾配 %+.1f〜%+.1f %%)。真の流れからの FoE の誤差 最大 %.1e px" % (
        len(t_out), time.time() - t_r, R["foe_true"][:, 1].min(), R["foe_true"][:, 1].max(), 100 * R["grade"].min(), 100 * R["grade"].max(),
        R["foe_ident_err"].max()))
    gate("FoE の定理: 真の流れ → foe_from_flow = foe_from_motion(1e-6、全コマ)", R["foe_ident_err"].max() < 1e-6)
    print("  LK(30 fps、路面の画素、流れの誤差の中央値 %.2f px)からの FoE の誤差: 模様あり・路面だけ 中央値 %.1f px(90 %% 点 %.1f)、全画素 中央値 %.1f px、"
          "模様なし・路面だけ(1 s ごと %d コマ)中央値 %.1f px" % (
              np.nanmedian(R["lk_err"]), np.median(R["err_road"]), np.percentile(R["err_road"], 90), np.median(R["err_all"]),
              sel_int.sum(), np.median(R["err_plain"])))
    print("    同じコマで比べる(1 s ごと): 模様あり %s / 模様なし %s" % (
        np.round(R["err_road"][sel_int], 1).tolist(), np.round(R["err_plain"], 1).tolist()))
    gate("模様が FoE を取り戻す: 路面の画素だけで中央値 ≤ 12 px、模様なしは 2 倍以上外れる",
         np.median(R["err_road"]) <= 12.0 and np.median(R["err_plain"]) >= 2.0 * np.median(R["err_road"][sel_int]))

    # ─────────────────────────────── 5. 図 ─────────────────────────────
    if figs.enabled():
        print("== 5. 図")
        set_scene(6.0)
        Kb = DW.camera_intrinsics(55.0, 960, 600)
        top = DW.world_camera(WORLD, DW.camera_pose((-60.0, -150.0, 95.0), (0.0, -10.0, 0.0)), Kb, 960, 600)
        topm = DTR.world_materials(WORLD, top, DW.camera_pose((-60.0, -150.0, 95.0), (0.0, -10.0, 0.0)), Kb, MAT)
        img = np.asarray(AN.text_box(topm["color"], "周回コースを fBm の起伏(H = %.1f)の中に: 道の周り 2 m は平ら、路面はうねる(±0.8 m)、木 %d 本、横断歩道、歩行者" % (
            HURST, len(trees)), (12, 12), anchor="lt", font_size=12))
        figs.save("scene_terrain", img,
                  "世界を南西の上空から(t = 6 s)。fBm のスペクトル合成の起伏(H = %.1f、周期 6〜120 m、RMS 2.5 m)は道の周り 2 m で平らになり、"
                  "12 m かけて繋がる。路面には長波長のうねり(振幅 0.8 m)。木 %d 本は道から 4 m 以上・互いに 5 m 以上に散布。世界はコースの外 40 m まで。" % (HURST, len(trees)))
        lf = np.log10(pg["f"][pg["f"] > 0])
        lp = np.log10(pg["power"][pg["f"] > 0])
        band = (pg["f"] >= 1 / 100.0) & (pg["f"] <= 1 / 10.0)
        fit = sl["intercept"] / math.log(10) - sl["beta"] * lf
        th = (np.log10(pg["power"][band]).mean() + beta_th * np.log10(pg["f"][band]).mean()) - beta_th * lf
        figs.save_plot("terrain_spectrum", [("動径周期図(512 × 512、1 m)", lf, lp), ("当てはめ β̂ = %.2f" % sl["beta"], lf[band], fit[band]),
                                            ("定理 2H + 2 = %.1f" % beta_th, lf[band], th[band])],
                       kinds=["scatter", "line", "line"], xlabel="log10 f [周期/m]", ylabel="log10 パワー",
                       caption="fBm の面(H = %.1f)の動径周期図は log–log で直線: 傾き β̂ = %.2f、定理(Saupe 1988: β = 2H + E、E = 2)は %.1f。"
                               "帯域 [1/100, 1/10] 周期/m の %d 帯で当てはめ。有限の帯域と Hann 窓で +0.1 ほど急に出る。" % (HURST, sl["beta"], beta_th, sl["n"]))
        wear_img = np.stack([mat3["wear"]] * 3, -1)
        truth_img = np.zeros_like(mat3["color"])
        truth_img[..., 0] = mat3["stain"]
        truth_img[..., 2] = mat3["puddle"]
        truth_img[lines, 1] = mat3["wear"][lines]
        figs.save_grid("incar_materials", [mat3["color"], PAL[np.clip(lab + 1, 0, len(PAL) - 1)], wear_img, truth_img],
                       ["色(t = 6 s)", "ラベル(道・地形・縁石・白線・横断歩道・水溜り・木・歩行者)",
                        "白線の摩耗率(真値、0 = 白、1 = 路面)", "真値の場: 赤 = 染み、青 = 水溜り、緑 = 摩耗率"], ncols=2,
                       caption="車載カメラ(60°, 640 × 400)の 1 コマと、その画素ごとの真値。材質は描画した深度から戻した世界座標で評価するので、"
                               "ラベル・摩耗率・水溜り・染みは画素単位で厳密。摩耗した白線と水溜りは明るさのしきい値では最良でも %.0f %% を間違える。" % (100 * ovl))
        k6 = int(np.argmin(np.abs(R["err_road"] - np.median(R["err_road"]))))          # 誤差が中央値に最も近い典型的なコマ
        t6 = float(t_out[k6])
        panels, caps = [], []
        for name_, fr_, uu, vv, fest, ferr in (("模様あり", R["frame"][k6]["color"], R["u"][k6], R["v"][k6], R["foe_road"][k6], R["err_road"][k6]),):
            rr, cc = np.mgrid[0:300, 0:480]
            sel = (R["frame"][k6]["label"] == 0) & (rr % 12 == 0) & (cc % 12 == 0) & np.isfinite(uu) & (np.hypot(uu, vv) > 0.3) & (np.hypot(uu, vv) < 12)
            im = _quiver(fr_, np.column_stack([cc[sel], rr[sel]]), 4 * np.column_stack([uu[sel], vv[sel]]))
            im = np.asarray(AN.crosshair(im, (float(fest[0]), float(fest[1])), color="emphasis", width=1, gap=3, extent=12))
            im = np.asarray(AN.crosshair(im, (float(R["foe_true"][k6][0]), float(R["foe_true"][k6][1])), color="right", width=1, gap=3, extent=12))
            panels.append(im)
            caps.append("%s: 路面の流れ → FoE(橙、誤差 %.1f px)、真値(緑)" % (name_, ferr))
        p0, w0, Q0 = render(t6, Kg, 480, 300, MAT_PLAIN)
        p1, w1, Q1 = render(t6 + DT_LK, Kg, 480, 300, MAT_PLAIN)
        up, vp = FL.optical_flow_lk(p0["color"].mean(-1), p1["color"].mean(-1), window=15, levels=5)
        fp = TT.foe_from_flow(up, vp, (p0["label"] == 0), max_speed=12.0)["foe"]
        rr, cc = np.mgrid[0:300, 0:480]
        sel = (p0["label"] == 0) & (rr % 12 == 0) & (cc % 12 == 0) & np.isfinite(up) & (np.hypot(up, vp) > 0.3) & (np.hypot(up, vp) < 12)
        im = _quiver(p0["color"], np.column_stack([cc[sel], rr[sel]]), 4 * np.column_stack([up[sel], vp[sel]]))
        im = np.asarray(AN.crosshair(im, (float(fp[0]), float(fp[1])), color="emphasis", width=1, gap=3, extent=12))
        im = np.asarray(AN.crosshair(im, (float(R["foe_true"][k6][0]), float(R["foe_true"][k6][1])), color="right", width=1, gap=3, extent=12))
        panels.append(im)
        caps.append("模様なし(同じ地形): FoE は %.1f px 外れる" % np.hypot(*(np.asarray(fp) - R["foe_true"][k6])))
        figs.save_grid("foe_from_flow", panels, caps, ncols=2,
                       caption="t = %.1f s(誤差が中央値に最も近い典型的なコマ)の車載カメラ(480 × 300、30 fps の 2 コマ)。路面の画素の Lucas–Kanade の"
                               "流れ(矢印 ×4)だけから拡大の中心を最小二乗(流線と点の距離、角度の残差で重み)で出す。模様のある路面では真値(緑)に %.1f px、"
                               "無地の路面では %.1f px。" % (t6, R["err_road"][k6], np.hypot(*(np.asarray(fp) - R["foe_true"][k6]))))
        figs.save_plot("foe_error", [("模様あり・路面の画素だけ", R["t"], R["err_road"]), ("模様あり・全画素", R["t"], R["err_all"]),
                                     ("模様なし・路面の画素だけ(1 s ごと)", R["t"][sel_int], R["err_plain"]),
                                     ("路面の勾配 × 100 [%]", R["t"], 100 * R["grade"])],
                       kinds=["line", "line", "scatter", "line"], xlabel="t [s]", ylabel="FoE の誤差 [px] / 勾配 [%]",
                       caption="拡大の中心の推定誤差(真値との距離)。模様のある路面の画素だけで中央値 %.1f px、全画素で %.1f px、無地の路面では %.1f px。"
                               "自車は坂を上り下りする(勾配 %+.1f〜%+.1f %%)ので真の FoE も像の中を動く。" % (
                                   np.median(R["err_road"]), np.median(R["err_all"]), np.median(R["err_plain"]), 100 * R["grade"].min(), 100 * R["grade"].max()))
        gif = []
        for k, t in enumerate(t_out):
            fe = R["foe_all"][k]
            ft = R["foe_true"][k]
            uu, vv = R["u"][k], R["v"][k]
            rr, cc = np.mgrid[0:300, 0:480]
            sel = (R["frame"][k]["label"] >= 0) & (rr % 15 == 0) & (cc % 15 == 0) & np.isfinite(uu) & (np.hypot(uu, vv) > 0.3) & (np.hypot(uu, vv) < 12)
            fr = _quiver(R["frame"][k]["color"], np.column_stack([cc[sel], rr[sel]]), 4 * np.column_stack([uu[sel], vv[sel]]))
            fr = np.asarray(AN.crosshair(fr, (float(fe[0]), float(fe[1])), color="emphasis", width=1, gap=3, extent=10))
            fr = np.asarray(AN.crosshair(fr, (float(ft[0]), float(ft[1])), color="right", width=1, gap=3, extent=10))
            ped_state = "横断中" if T_PED0 <= t <= T_PED0 + (-Y_PED0 - 23.5) / V_PED else ("渡り終えた" if t > T_PED0 else "歩道で待つ")
            fr = np.asarray(AN.text_box(fr, "t = %4.1f s  勾配 %+.1f %%  FoE 誤差 全画素 %.1f / 路面 %.1f px" % (
                t, 100 * R["grade"][k], R["err_all"][k], R["err_road"][k]), (8, 8), anchor="lt", font_size=11))
            fr = np.asarray(AN.text_box(fr, "矢印 = LK ×4  十字 橙 = 推定 / 緑 = 真値  歩行者: %s" % ped_state, (8, 292), anchor="lb", font_size=11))
            gif.append(fr)
        figs.save_gif("drive_gif", gif, fps=5,
                      caption="車載カメラで 0 → %.0f s(%d コマ、%.0f m/s): 起伏の中の周回コースを坂を上り下りしながら走る。矢印は LK の流れ(×4)、"
                              "橙の十字は流れから推定した拡大の中心、緑は真値。横断歩道を歩行者が渡り、路面には水溜りと摩耗した白線。" % (T_END, len(gif), V_EGO))
        if figs.errors():
            print("図の書き出しで失敗:", "; ".join(figs.errors()))

    print("== 結果: %d / %d 門, %.1f s" % (sum(OK), len(OK), time.time() - T0))
    print("PASS" if all(OK) else "FAIL")
    return 0 if all(OK) else 1


if __name__ == "__main__":
    sys.exit(main())
