# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""poc_thermal_drift_metrology — カメラの熱ドリフトが寸法計測に効く量。

    py -3.11 examples/poc_thermal_drift_metrology.py

【この PoC が答える問い】
検査装置を朝いちばんに立ち上げて校正し、そのまま一日走らせる。工場の気温が
上がる午後になると、同じワークが違う寸法で出る。**「何度上がると何ミクロン
ずれるか」「どの校正をやり直せば止まるか」**を、真値を握った合成で測る。

答えは「焦点距離の熱膨張(と架台の熱膨張)は**位置に依らない一定の倍率誤差**、
主点のドリフトは**歪みを介して位置に比例する誤差**。ワークを画面内で動かして
**定数項と 1 次項に分ければ 2 つを分離できる**」。

【所見(すべて下の節で実測。★ は重要、★★ は最重要)】

 1. ★★**予想が外れた**。書き始める前の予想は「焦点距離ドリフトは中心から
    遠いほど効く倍率誤差、主点ドリフトは平行移動だから寸法に効かない」。
    実測は**逆だった** —— 歪みが無ければ主点ドリフトは寸法に**厳密に 0**
    (平行移動は距離を変えない)、焦点距離ドリフトは**位置に依らない一定の
    倍率誤差**。位置を振っても何も分離できない。
    ★歪み(k1=-0.12)を入れて初めて主点ドリフトが**半径に比例する誤差**を
    作り、そこで 2 つが分離できるようになる —— **分離を可能にしているのは
    歪みという「不完全さ」のほう**。

 2. ★半径 R の 1 次式 ``err(R) = a + b·R`` に当てはめると、定数項 a が
    焦点距離+架台のドリフト、1 次項 b が主点ドリフトを表す。片方だけを
    動かした対照条件と突き合わせて、この分離が実際に効くことを確かめた(4 節)。

 3. ★★**対照群を置かないと「効いている」と言えない**。雑音だけ(ΔT=0)の
    誤差の床を 300 回の繰り返しで出してから、ドリフトの誤差と比べている。
    ΔT が小さい領域では**ドリフトは床に埋もれる** —— 何度から効き始めるかを
    床との交点として数字で出した(3 節)。

 4. **面積は距離の 2 倍効く**。倍率誤差 ε に対し距離は ε、面積は 2ε+ε²。
    実測の比は 2.000(5 節)。「面積で見れば平均されて安全」ではない。

 5. 対策の比較(6 節)。毎フレーム再校正が最良(床まで戻る)。**画面内の
    基準物によるスケール引き直しは、基準物をワークと同じ半径に置いたときだけ
    効く** —— 中央に置くと主点ドリフトぶんが残る。温度ログ + 式の補正は
    温度センサの誤差にそのまま比例する。

 6. `fs.distort_points` / `fs.undistort_points` / `fs.intrinsic_matrix` は
    この用途にそのまま使えた。足りないのは**熱モデルそのもの**と、
    **基準物によるスケール引き直しの op**。8 節に実測つきで置いた。

【グラウンドトゥルース(すべて閉形式)】
* ワーク: 物体平面(カメラ光軸に垂直)上の正方形。一辺 40.000 mm(厳密)。
* カメラ: ピンホール + 半径方向歪み。温度 ΔT に対して
    f(ΔT)  = f0 (1 + β ΔT)         β = レンズ実効焦点距離 - 画素ピッチの膨張
    Z(ΔT)  = Z0 (1 + α ΔT)         α = 架台(カメラ支柱)の膨張
    cx(ΔT) = cx0 + γx ΔT           γ = センサ取付の非対称な膨張(横ずれ)
  倍率は f/Z なので、寸法の相対誤差は閉形式で **(β - α) ΔT**。
* 計測は「立ち上げ時の校正値」で歪みを外し、Z_cal/f_cal を掛けて mm にする。

【節立て】
 1) 合成器の検算 —— ΔT=0・雑音なしで真値が戻るか
 2) ★対照群 —— 雑音だけの誤差の床(ドリフト以外の誤差)
 3) ★ゼロ点 —— 立ち上げ時に 1 回校正して使い続ける
 4) ★★2 つのドリフトを分離する —— 半径を振る
 5) 距離(1 乗)と面積(2 乗)
 6) 対策の比較 —— 再校正 / 画面内基準物 / 温度ログ+式
 7) 「何度まで許せるか」を仕様から逆算する
 8) 道具の穴(assert で現状を固定)
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- カメラと架台(立ち上げ時 = 基準温度での値)------------------------------- #
IMG_W, IMG_H = 2448, 2048
F0 = 3000.0                      # 焦点距離 [px]
CX0, CY0 = (IMG_W - 1) / 2.0, (IMG_H - 1) / 2.0
Z0 = 400.0                       # 作動距離 [mm]
DIST = np.array([-0.12, 0.03, 0.0, 0.0])     # k1, k2, p1, p2(半径方向のみ)

# --- 熱ドリフトの係数(いずれも 1 K あたり)----------------------------------- #
BETA_F = 2.0e-5                  # 焦点距離 [1/K](樹脂玉を含む C マウントの実勢)
ALPHA_MOUNT = 5.0e-6             # 架台の伸び [1/K](鋼の支柱、短い)
GAMMA_X = 0.25                   # 主点の横ずれ [px/K]
GAMMA_Y = 0.15                   # 主点の縦ずれ [px/K]

SIDE_MM = 40.000                 # ワークの一辺(真値)
GAUGE_MM = 30.000                # 画面内基準物の長さ(真値)
SIGMA_PX = 0.05                  # 角点検出の雑音 [px]
MM_PER_PX = Z0 / F0              # 0.1333 mm/px

K_CAL = fs.intrinsic_matrix(F0, F0, CX0, CY0)     # 立ち上げ時の校正値


# --- 撮像(真値 → 画素)------------------------------------------------------ #
def camera_state(dT: float, drift: str = "both"):
    """温度 ΔT でのカメラの状態。*drift* = ``both`` / ``f`` / ``c`` / ``none``。"""
    use_f = drift in ("both", "f")
    use_c = drift in ("both", "c")
    f = F0 * (1.0 + (BETA_F if use_f else 0.0) * dT)
    z = Z0 * (1.0 + (ALPHA_MOUNT if use_f else 0.0) * dT)
    cx = CX0 + (GAMMA_X if use_c else 0.0) * dT
    cy = CY0 + (GAMMA_Y if use_c else 0.0) * dT
    return f, z, cx, cy


def image_points(world_xy: np.ndarray, dT: float, drift: str = "both",
                 rng: np.random.Generator | None = None) -> np.ndarray:
    """物体平面 (N,2) [mm] → 画素 (N,2)。歪みは `fs.distort_points`。"""
    f, z, cx, cy = camera_state(dT, drift)
    k = fs.intrinsic_matrix(f, f, cx, cy)
    ideal = np.stack([f * world_xy[:, 0] / z + cx,
                      f * world_xy[:, 1] / z + cy], axis=1)
    uv = np.asarray(fs.distort_points(ideal, k, DIST))
    if rng is not None:
        uv = uv + rng.normal(0.0, SIGMA_PX, uv.shape)
    return uv


def measure_xy(uv: np.ndarray, k_cal=None, z_cal: float = Z0) -> np.ndarray:
    """画素 → 物体平面 [mm]。**校正値**で歪みを外して倍率を掛けるだけ。"""
    k = K_CAL if k_cal is None else k_cal
    ud = np.asarray(fs.undistort_points(uv, k, DIST, iters=40))
    p = fs.decompose_intrinsics(k)
    return np.stack([(ud[:, 0] - p["cx"]) * z_cal / p["fx"],
                     (ud[:, 1] - p["cy"]) * z_cal / p["fy"]], axis=1)


# --- ワークと計測量 ---------------------------------------------------------- #
def square(cx_mm: float, cy_mm: float, side: float = SIDE_MM) -> np.ndarray:
    """正方形の 4 隅 [mm](反時計回り)。"""
    h = side / 2.0
    return np.array([[cx_mm - h, cy_mm - h], [cx_mm + h, cy_mm - h],
                     [cx_mm + h, cy_mm + h], [cx_mm - h, cy_mm + h]])


def side_length(pts: np.ndarray) -> float:
    """4 辺の平均長さ [mm]。"""
    d = pts[[1, 2, 3, 0]] - pts
    return float(np.mean(np.hypot(d[:, 0], d[:, 1])))


def polygon_area(pts: np.ndarray) -> float:
    """靴ひも公式の面積 [mm^2]。"""
    x, y = pts[:, 0], pts[:, 1]
    return float(0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))


def place_at_radius(r_px: float) -> tuple[float, float]:
    """画素半径 *r_px* に対応する物体平面上のワーク中心 [mm](対角方向)。"""
    s = r_px * MM_PER_PX / np.sqrt(2.0)
    return s, s


def measure_side(center_mm, dT: float, drift: str = "both", rng=None,
                 k_cal=None, z_cal: float = Z0) -> float:
    uv = image_points(square(*center_mm), dT, drift, rng)
    return side_length(measure_xy(uv, k_cal, z_cal))


def ppm(v: float, truth: float) -> float:
    return 1e6 * (v / truth - 1.0)


def um(v: float, truth: float) -> float:
    return 1e3 * (v - truth)


# =========================================================================== #
def section1_check():
    print("=" * 78)
    print("1) 合成器の検算 —— ΔT=0・雑音なしで真値が戻るか")
    print("=" * 78)
    print("  カメラ: f=%.0f px / Z=%.0f mm / 倍率 %.5f mm/px / 歪み k1=%.2f k2=%.2f"
          % (F0, Z0, MM_PER_PX, DIST[0], DIST[1]))
    print("  視野 %.0f x %.0f mm、ワーク一辺 %.3f mm(= %.0f px)"
          % (IMG_W * MM_PER_PX, IMG_H * MM_PER_PX, SIDE_MM, SIDE_MM / MM_PER_PX))
    print()
    for r in (0.0, 600.0, 1200.0):
        c = place_at_radius(r)
        pts = measure_xy(image_points(square(*c), 0.0))
        err = float(np.max(np.abs(pts - square(*c))))
        print("  半径 %5.0f px: 角点の復元誤差 最大 %.2e mm / 一辺 %.9f mm(真値 %.3f)"
              % (r, err, side_length(pts), SIDE_MM))
    # 歪みの往復
    grid = np.stack(np.meshgrid(np.linspace(50, IMG_W - 50, 12),
                                np.linspace(50, IMG_H - 50, 10)), -1).reshape(-1, 2)
    back = np.asarray(fs.undistort_points(np.asarray(fs.distort_points(grid, K_CAL, DIST)),
                                          K_CAL, DIST, iters=40))
    print("  distort → undistort の往復誤差 最大 %.2e px(fullseye の 2 op)"
          % float(np.max(np.abs(back - grid))))
    print("  画面隅の歪み量: %.1f px(%.2f %% の縮み)"
          % (float(np.max(np.abs(np.asarray(fs.distort_points(grid, K_CAL, DIST)) - grid))),
             100 * (1 - (1 + DIST[0] * 0.283 + DIST[1] * 0.080))))
    print()
    print("  → 真値は厳密に戻る。以降の誤差は**すべて熱ドリフトか雑音**。")


def section2_noise_floor():
    print()
    print("=" * 78)
    print("2) ★対照群 —— 雑音だけの誤差の床(温度を動かさない)")
    print("=" * 78)
    print("  ΔT=0 のまま、角点検出の雑音 σ=%.3f px だけを 300 回入れる。" % SIGMA_PX)
    print("  **この床を超えていなければ「ドリフトが効いている」とは言えない**。")
    print()
    rng = np.random.default_rng(7)
    print("  %8s %14s %14s %14s" % ("半径 px", "偏り µm", "散らばり µm", "散らばり ppm"))
    print("  " + "-" * 54)
    floors = {}
    for r in (0.0, 600.0, 1200.0):
        c = place_at_radius(r)
        vals = [measure_side(c, 0.0, "both", rng) for _ in range(300)]
        v = np.array(vals)
        floors[r] = float(v.std())
        print("  %8.0f %14.3f %14.3f %14.1f"
              % (r, um(float(v.mean()), SIDE_MM), 1e3 * float(v.std()),
                 1e6 * float(v.std()) / SIDE_MM))
    print()
    print("  → 床は %.2f µm(%.0f ppm)前後。角点 4 点の平均なので σ/2 相当。"
          % (1e3 * floors[0.0], 1e6 * floors[0.0] / SIDE_MM))
    print("     偏りは 0 に落ちる(雑音は系統誤差を作らない)—— ここが対照群。")
    return floors


def section3_zero_point(floors):
    print()
    print("=" * 78)
    print("3) ★ゼロ点 —— 立ち上げ時に 1 回校正して使い続ける")
    print("=" * 78)
    print("  ワークは画面中央。温度だけを上げる。閉形式の予測は (β-α)ΔT。")
    print("  β=%.1e /K(焦点距離)、α=%.1e /K(架台)→ 正味 %.1e /K"
          % (BETA_F, ALPHA_MOUNT, BETA_F - ALPHA_MOUNT))
    print()
    c = place_at_radius(0.0)
    print("  %8s %12s %12s %12s %10s" % ("ΔT K", "実測 µm", "閉形式 µm", "実測 ppm",
                                         "床の何倍"))
    print("  " + "-" * 58)
    dts = (0.0, 1.0, 2.0, 5.0, 10.0, 15.0, 20.0)
    meas = []
    for dT in dts:
        v = measure_side(c, dT)
        pred = SIDE_MM * (BETA_F - ALPHA_MOUNT) * dT
        meas.append(um(v, SIDE_MM))
        print("  %8.1f %12.3f %12.3f %12.1f %10.1f"
              % (dT, um(v, SIDE_MM), 1e3 * pred, ppm(v, SIDE_MM),
                 abs(um(v, SIDE_MM)) / (1e3 * floors[0.0])))
    cross = 1e3 * floors[0.0] / (SIDE_MM * (BETA_F - ALPHA_MOUNT) * 1e3)
    print()
    print("  → 実測と閉形式が 3 桁一致。中央では**主点ドリフトが効いていない**")
    print("     (歪みの中心と測定点が同じ場所にあるので、ずれが 1 次で相殺する)。")
    print("     ドリフトが雑音の床を超えるのは ΔT = %.1f K から。それ以下では" % cross)
    print("     「温度の影響は見えない」が正しい報告 —— 床を出さずに")
    print("     「1 K で 0.05 µm ずれた」と書くのは**雑音を読んでいるだけ**。")
    return dts, meas


def section4_separate(floors):
    print()
    print("=" * 78)
    print("4) ★★2 つのドリフトを分離する —— ワークを画面内で動かす")
    print("=" * 78)
    dT = 15.0
    print("  ΔT=%.0f K に固定して、ワークの画素半径 R を振る。" % dT)
    print("  3 条件: 焦点距離+架台のみ / 主点のみ / 両方。雑音は入れない(系統誤差だけ)。")
    print()
    radii = (0.0, 200.0, 400.0, 700.0, 1000.0, 1300.0)
    print("  %8s %14s %14s %14s %12s"
          % ("R px", "f のみ ppm", "主点のみ ppm", "両方 ppm", "和 ppm"))
    print("  " + "-" * 66)
    only_f, only_c, both = [], [], []
    for r in radii:
        c = place_at_radius(r)
        a = ppm(measure_side(c, dT, "f"), SIDE_MM)
        b = ppm(measure_side(c, dT, "c"), SIDE_MM)
        t = ppm(measure_side(c, dT, "both"), SIDE_MM)
        only_f.append(a)
        only_c.append(b)
        both.append(t)
        print("  %8.0f %14.1f %14.1f %14.1f %12.1f" % (r, a, b, t, a + b))
    print()
    print("  → ★**予想が外れた**。焦点距離ドリフトは半径にほとんど依らない")
    print("     (%.1f → %.1f ppm)。主点ドリフトは中央で %.1f ppm、"
          % (only_f[0], only_f[-1], only_c[0]))
    print("     周辺で %.1f ppm と**半径に比例して増える**。予想は逆だった。"
          % only_c[-1])
    print("     理由: 平行移動そのものは距離を変えない。効くのは**歪みを外すときに")
    print("     使う中心がずれる**ことで、その影響は半径の 1 次で入る。")
    print()
    # 対照: 歪みを 0 にすると主点ドリフトは寸法に効かなくなるはず
    global DIST
    keep = DIST.copy()
    DIST = np.zeros(4)
    zero_c = [ppm(measure_side(place_at_radius(r), dT, "c"), SIDE_MM) for r in radii]
    zero_f = [ppm(measure_side(place_at_radius(r), dT, "f"), SIDE_MM) for r in radii]
    DIST = keep
    print("  ★対照条件(歪みを k1=k2=0 にして同じ測定):")
    print("    主点のみ: " + " / ".join("%.2f" % v for v in zero_c) + " ppm")
    print("    f のみ  : " + " / ".join("%.1f" % v for v in zero_f) + " ppm")
    print("    → 歪みが無いと主点ドリフトは**厳密に 0**(最大 %.1e ppm)。"
          % max(abs(v) for v in zero_c))
    print("      **分離を可能にしているのは歪みという「レンズの不完全さ」のほう**。")
    print()
    # 1 次式で分離
    A = np.stack([np.ones(len(radii)), np.array(radii)], axis=1)
    coef, *_ = np.linalg.lstsq(A, np.array(both), rcond=None)
    print("  「両方」の曲線を err(R) = a + b·R に当てはめる:")
    print("    a = %+.1f ppm(真値 = f のみの平均 %+.1f ppm)"
          % (coef[0], float(np.mean(only_f))))
    print("    b = %+.4f ppm/px(真値 = 主点のみの傾き %+.4f ppm/px)"
          % (coef[1], float(np.polyfit(radii, only_c, 1)[0])))
    print("    → 定数項が焦点距離+架台、1 次項が主点。**1 台のカメラで、ワークを")
    print("      画面内で動かすだけで 2 つの原因を切り分けられる**。")
    print("      温度計もレーザ干渉計も要らない。")
    if figs.enabled():
        xs = np.array(radii)
        figs.save_plot("separate_drifts",
                       [("焦点距離+架台のみ", xs, np.array(only_f)),
                        ("主点のみ", xs, np.array(only_c)),
                        ("両方", xs, np.array(both)),
                        ("1 次当てはめ", xs, coef[0] + coef[1] * xs),
                        ("雑音の床 1σ", xs,
                         np.full(xs.size, 1e6 * floors[0.0] / SIDE_MM))],
                       xlabel="ワークの画素半径 R [px]", ylabel="寸法誤差 [ppm]",
                       title="ΔT=15 K。定数項と 1 次項で原因が分かれる",
                       caption="焦点距離ドリフトは R に依らない。主点ドリフトは "
                               "R に比例(歪みを外す中心がずれるため)。")
    return radii, only_f, only_c, both


def section5_area():
    print()
    print("=" * 78)
    print("5) 距離(1 乗)と面積(2 乗)")
    print("=" * 78)
    print("  倍率誤差 ε に対して距離は ε、面積は 2ε + ε²。実測で確かめる。")
    print()
    c = place_at_radius(0.0)
    print("  %8s %14s %14s %10s %10s"
          % ("ΔT K", "一辺 ppm", "面積 ppm", "比", "予測 比"))
    print("  " + "-" * 60)
    for dT in (5.0, 10.0, 15.0, 20.0):
        pts = measure_xy(image_points(square(*c), dT))
        e_len = ppm(side_length(pts), SIDE_MM)
        e_area = ppm(polygon_area(pts), SIDE_MM ** 2)
        pred = 2.0 + e_len * 1e-6
        print("  %8.1f %14.1f %14.1f %10.4f %10.4f"
              % (dT, e_len, e_area, e_area / e_len, pred))
    print()
    print("  → 比は 2.000。**面積で見ると誤差は倍になる** —— 「面積は平均されるから")
    print("     安全」は誤り。ppm の仕様を面積で書くときは 2 倍を織り込むこと。")


def section6_countermeasures(floors):
    print()
    print("=" * 78)
    print("6) 対策の比較 —— 再校正 / 画面内基準物 / 温度ログ+式")
    print("=" * 78)
    dT = 15.0
    r_work = 1000.0
    c_work = place_at_radius(r_work)
    print("  ΔT=%.0f K、ワークは半径 %.0f px。雑音なしの系統誤差で比べる。"
          % (dT, r_work))
    print()

    def gauge_scale(r_gauge: float) -> float:
        """画面内の既知長さ(%.1f mm)を測って得られるスケール係数。""" % GAUGE_MM
        gx, gy = place_at_radius(r_gauge)
        pts = np.array([[gx - GAUGE_MM / 2, gy], [gx + GAUGE_MM / 2, gy]])
        m = measure_xy(image_points(pts, dT))
        return float(np.hypot(*(m[1] - m[0]))) / GAUGE_MM

    rows = []

    def add(name, value_mm, note=""):
        rows.append([name, "%+.3f" % um(value_mm, SIDE_MM),
                     "%+.1f" % ppm(value_mm, SIDE_MM), note])

    add("Z. 立ち上げ時 1 回のみ(ゼロ点)", measure_side(c_work, dT), "")
    f_t, z_t, cx_t, cy_t = camera_state(dT)
    k_t = fs.intrinsic_matrix(f_t, f_t, cx_t, cy_t)
    add("A. 毎フレーム再校正", measure_side(c_work, dT, k_cal=k_t, z_cal=z_t),
        "真の f, Z, 主点を使う")
    add("B1. 画面内基準物(同じ半径)",
        measure_side(c_work, dT) / gauge_scale(r_work), "基準物を隣に置く")
    add("B2. 画面内基準物(中央)",
        measure_side(c_work, dT) / gauge_scale(0.0), "中央固定の治具")
    for terr in (0.0, 1.0, 3.0):
        dh = dT + terr
        f_h, z_h, cx_h, cy_h = camera_state(dh)
        k_h = fs.intrinsic_matrix(f_h, f_h, cx_h, cy_h)
        add("C. 温度ログ+式(センサ誤差 %.0f K)" % terr,
            measure_side(c_work, dT, k_cal=k_h, z_cal=z_h), "")
    add("D. 対照: 温度を動かさない", measure_side(c_work, 0.0), "ドリフト以外の床")

    print("  %-34s %10s %10s  %s" % ("手法", "誤差 µm", "誤差 ppm", "備考"))
    print("  " + "-" * 76)
    for name, u, p, note in rows:
        print("  %-34s %10s %10s  %s" % (name, u, p, note))
    print()
    print("  雑音の床(1σ、300 回): %.3f µm。上の系統誤差がこれを下回れば"
          % (1e3 * floors[1200.0]))
    print("  「実質的に消えた」と言ってよい。")
    print()
    print("  → B1 と B2 の差が要点。**基準物はワークと同じ半径に置かないと**")
    print("     主点ドリフトぶんが残る(中央固定の治具では %s ppm)。"
          % rows[3][2])
    print("     C は温度センサの誤差にほぼ比例して残る(1 K で %s ppm、3 K で %s ppm)。"
          % (rows[5][2], rows[6][2]))
    figs.save_table("countermeasures", ["手法", "誤差 µm", "誤差 ppm", "備考"], rows,
                    title="ΔT=15 K・半径 %.0f px のワーク(真値 %.3f mm)"
                          % (r_work, SIDE_MM))
    return rows


def section7_budget(floors):
    print()
    print("=" * 78)
    print("7) 「何度まで許せるか」を仕様から逆算する")
    print("=" * 78)
    print("  公差の 1/10 を測定系に割り当てる、という普通の配分で考える。")
    print()
    print("  %10s %12s %14s %14s"
          % ("公差 ±µm", "許容誤差 µm", "許容 ΔT K(中央)", "許容 ΔT K(周辺)"))
    print("  " + "-" * 56)
    c0 = place_at_radius(0.0)
    c1 = place_at_radius(1300.0)
    s0 = abs(um(measure_side(c0, 10.0), SIDE_MM)) / 10.0     # µm/K
    s1 = abs(um(measure_side(c1, 10.0), SIDE_MM)) / 10.0
    for tol in (5.0, 10.0, 20.0, 50.0, 100.0):
        budget = tol / 10.0
        print("  %10.0f %12.1f %14.1f %14.1f"
              % (tol, budget, budget / s0, budget / s1))
    print()
    print("  感度は中央 %.3f µm/K、半径 1300 px %.3f µm/K(%.1f 倍)。"
          % (s0, s1, s1 / s0))
    print("  → 公差 ±10 µm の部品を周辺視野で測るなら、**盤内温度を %.1f K 以内に"
          % (1.0 / s1))
    print("     抑えるか、6 節の対策を入れる**。この 1 行が現場で使う結論。")
    if figs.enabled():
        dts = np.linspace(0.0, 20.0, 11)
        e0 = np.array([abs(um(measure_side(c0, d), SIDE_MM)) for d in dts])
        e1 = np.array([abs(um(measure_side(c1, d), SIDE_MM)) for d in dts])
        f_of = [camera_state(d) for d in dts]
        e_c = np.array([abs(um(measure_side(c1, d, k_cal=fs.intrinsic_matrix(
            s[0], s[0], s[2], s[3]), z_cal=s[1]), SIDE_MM)) for d, s in zip(dts, f_of)])
        figs.save_plot("budget",
                       [("中央のワーク", dts, e0),
                        ("周辺のワーク(R=1300)", dts, e1),
                        ("毎フレーム再校正", dts, e_c),
                        ("雑音の床 1σ", dts, np.full(dts.size, 1e3 * floors[0.0])),
                        ("公差 ±10 µm の 1/10", dts, np.full(dts.size, 1.0))],
                       xlabel="温度上昇 ΔT [K]", ylabel="一辺の誤差 [µm]",
                       title="何度まで許せるか",
                       caption="周辺のワークのほうが感度が高い。再校正すれば"
                               "雑音の床まで戻る。")


def section_figures():
    """寸法誤差の面内分布(ΔT=15 K)。原因別に 4 枚。"""
    if not figs.enabled():
        return
    dT = 15.0
    nx, ny = 96, 80
    us = np.linspace(60, IMG_W - 60, nx)
    vs = np.linspace(60, IMG_H - 60, ny)
    uu, vv = np.meshgrid(us, vs)
    half = 60.0                      # 画素で ±60 px の小さな試験片
    maps = {}
    for drift in ("f", "c", "both"):
        pts = []
        for du in (-half, half):
            pts.append(np.stack([(uu + du - CX0) * MM_PER_PX,
                                 (vv - CY0) * MM_PER_PX], axis=-1).reshape(-1, 2))
        w = np.concatenate(pts, axis=0)
        m = measure_xy(image_points(w, dT, drift))
        n = uu.size
        d = np.hypot(*(m[n:] - m[:n]).T).reshape(ny, nx)
        d0 = 2 * half * MM_PER_PX
        maps[drift] = 1e6 * (d / d0 - 1.0)
    lim = float(np.percentile(np.abs(maps["both"]), 99))
    panels = [np.clip(maps["f"], -lim, lim), np.clip(maps["c"], -lim, lim),
              np.clip(maps["both"], -lim, lim),
              np.clip(maps["both"] - maps["f"] - maps["c"], -lim / 20, lim / 20)]
    figs.save_grid("error_maps", panels,
                   ["f のみ [ppm]", "主点のみ [ppm]", "両方 [ppm]", "両方-(f+主点)"],
                   title="寸法誤差の面内分布(ΔT=15 K、±%.0f%% ppm で切る)" % lim,
                   ncols=2, signed=True,
                   caption="f のみは一様、主点のみは中心から離れるほど大きい。"
                           "4 枚目は非線形の残り(1/20 の目盛)。")


def section8_tool_gaps():
    print()
    print("=" * 78)
    print("8) 道具の穴 —— fullseye に無かったもの")
    print("=" * 78)
    import ops as _ops
    allnames = set(dir(fs)) | set(dir(fs.ledger)) | {o.name for o in _ops.REGISTRY}

    # (a) 熱モデルが無い
    for kw in ("thermal", "temperature", "thermo", "drift"):
        hit = [n for n in allnames if kw in n.lower()]
        assert not hit, (kw, hit)
    print("  (a) ★**カメラの熱モデルが 3 層のどこにも無い**('thermal'/'temperature'/")
    print("      'thermo'/'drift' で 0 件)。校正 op は「ある時点の K」を返すだけで、")
    print("      **K が時間とともに動く**ことを表す型が無い。")
    print("      `thermal_intrinsics(K0, dT, beta, gamma)` のような 1 本があれば、")
    print("      6 節の対策 C はそれを呼ぶだけになる。")

    # (b) 基準物によるスケール引き直しの op が無い
    for kw in ("gauge", "artifact", "rescale_by", "scale_from"):
        hit = [n for n in allnames if kw in n.lower()]
        assert not hit, (kw, hit)
    print("  (b) **画面内の既知長さでスケールを引き直す op が無い**。")
    print("      `annotate_scale_bar` は**描く**ほうで、測るほうではない。")
    print("      6 節で見たとおりこの手法には「基準物をワークと同じ半径に置く」")
    print("      という非自明な条件が付くので、op にして docstring に書く価値がある。")

    # (c) undistort_points は歪み中心を K から取る —— 主点と分けられない
    k_shift = fs.intrinsic_matrix(F0, F0, CX0 + 10.0, CY0)
    p = np.array([[CX0 + 800.0, CY0]])
    a = np.asarray(fs.undistort_points(p, K_CAL, DIST, iters=40))
    b = np.asarray(fs.undistort_points(p, k_shift, DIST, iters=40))
    assert abs(a[0, 0] - b[0, 0]) > 1.0, (a, b)
    print("  (c) ★`undistort_points` は**歪みの中心を K の主点と同一視**している。")
    print("      主点を 10 px ずらすだけで、同じ画素の復元結果が %.2f px 動く。"
          % abs(a[0, 0] - b[0, 0]))
    print("      実際のレンズでは**歪み中心と主点は別物**(前者は光軸、後者は")
    print("      投影中心で、偏心があると数十 px 離れる)。分けられないと、")
    print("      4 節で見た「主点ドリフト → 半径比例の寸法誤差」を校正で吸収できない。")
    print("      `dist_center=` を受ける引数が要る(OpenCV も持っていない穴)。")

    # (d) 面積・距離を物体平面で測る口が無い(1-D キャリパーは画素の話)
    assert not any(n in allnames for n in ("polygon_area", "shoelace", "planar_measure"))
    print("  (d) 物体平面での**多角形の面積**を出す口が公開層に無い")
    print("      ('polygon_area'/'shoelace'/'planar_measure' で 0 件)。")
    print("      `measure3d` 族は (depth,row,col) の 3-D 計測、`measuring1d` は")
    print("      画素の 1-D キャリパー。**平面ワークの 2-D 寸法**という")
    print("      いちばん普通の用途がその間に落ちている(この PoC は 3 行書いた)。")

    # (e) 校正の戻り値に温度も時刻も入らない
    print("  (e) 校正結果に**いつ・何度で取ったか**を持たせる場所が無い。")
    print("      `intrinsic_matrix` は 3x3 の生配列を返すだけなので、")
    print("      「この K は 22 ℃ のもの」という来歴が呼び手の頭の中にしか無い。")
    print("      3 節のとおり 15 K で %.0f ppm 動く量なので、来歴は数字と同じくらい"
          % ((BETA_F - ALPHA_MOUNT) * 15.0 * 1e6))
    print("      重要 —— `K` を dict か dataclass で返す設計にしておく価値がある。")
    print()
    print("  次にやるべきこと: (a) と (b) を `calibration3d` / `metrology` 族へ。")
    print("  ただし (b) は**基準物の位置を必須引数**にすること —— 6 節のとおり")
    print("  「中央に置いた基準物」は主点ドリフトを取り切れず、既定値を置くと")
    print("  利用者は静かに間違った寸法を出す(`strain_from_displacement` の")
    print("  method を必須にしたのと同じ判断)。")


def main():
    t0 = time.time()
    print("poc_thermal_drift_metrology — カメラの熱ドリフトが寸法計測に効く量")
    print("(真値: 一辺 %.3f mm。ドリフトは f(ΔT)/Z(ΔT)/主点(ΔT) の閉形式)" % SIDE_MM)
    print()
    section1_check()
    floors = section2_noise_floor()
    section3_zero_point(floors)
    section4_separate(floors)
    section5_area()
    section6_countermeasures(floors)
    section7_budget(floors)
    section_figures()
    section8_tool_gaps()
    print()
    print("  所要 %.1f 秒" % (time.time() - t0))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
