# -*- coding: utf-8 -*-
"""事例: 点群から直線/平面/球/円を当てはめ、角度・距離・交線を計測する (metrology).

平たく言うと: 3-D スキャンした部品を「計測(メトロロジー)」するとは、生の点から
直線・平面・球・円といった理想形状を数式で当てはめ、それらの**間の関係**(2 面のなす角、
点と面の隙間、2 稜線の距離、面 ∩ 面の稜線、線 ∩ 面の当たり点)を数値で言い当てること。
本例は 1 つの機械加工ブロック(2 面が稜線で交わり、面上に球と円穴が乗る)を舞台に、
当てはめ op(fit_*/ransac_line)の出力を計測 op(angle_*/distance_*/intersect_*)へ
そのまま渡して**連結**し、各値が既知の設計真値(GT)に機械精度で一致するかを検証する。

検証(GT): 直交フレーム R と設計角(二面角 β=35°, 稜角 γ=40°, 線-面角 δ=25°)から
解析的な真値を作り、以下を assert する。
    - 当てはめ: fit_plane_3d/fit_line_3d/fit_sphere_3d/fit_circle_3d が法線・方向・中心・
      半径を機械精度で復元し、平面フィット残差 ~0。
    - 基本要素: line_from_2points/plane_from_3points が 2 点/3 点から方向・法線を厳密に復元。
    - 角度: angle_3points=γ, angle_between_lines=γ, angle_between_planes=β, angle_line_plane=δ。
    - 距離: distance_point_plane/point_line/line_line が既知の隙間・垂線長を厳密復元。
    - 交差: intersect_planes の稜線が面上に載り方向=稜線方向、intersect_line_plane の
      当たり点が面上(平行線では None)。
    - 面形状: surface_form_error は理想曲面の次数が合えば残差 ~0(2 次部品を deg1 では
      平らにできない)。background_flatten は 2 次照明ムラを厳密に引き去る。

beat-the-null: (1) ransac_line は外れ値混じりでも稜線方向を復元し、素の fit_line_3d(全点)
が外れ値に引かれてできる方向誤差を桁違いに下回る。(2) background_flatten は照明に埋もれた
高周波信号を復元し、生画像と信号の相関(照明優勢でほぼ無相関)を判別的に上回る。
(3) surface_form_error は次数一致の残差(~0)が次数不足の残差(有意)を桁違いに下回る。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np
import match3d as m3          # 幾何プリミティブ / メトロロジー op 群
import ransac_fit as rf       # 外れ値に頑健な当てはめ(ransac_line)


def frame(seed):
    """右手系の直交フレーム(列 = 単位基底 e0,e1,e2)。"""
    q, _ = np.linalg.qr(np.random.default_rng(seed).standard_normal((3, 3)))
    if np.linalg.det(q) < 0:
        q[:, 0] = -q[:, 0]
    return q


def ang_deg(u, v):
    """2 単位ベクトルのなす角(度, 符号無視)。"""
    u = u / np.linalg.norm(u); v = v / np.linalg.norm(v)
    return float(np.degrees(np.arccos(np.clip(abs(u @ v), -1, 1))))


R = frame(7)
e0, e1, e2 = R[:, 0], R[:, 1], R[:, 2]
c0 = np.array([10.0, -4.0, 6.0])                 # 2 面が交わる稜線上の一点(共通頂点)

BETA, GAMMA, DELTA = 35.0, 40.0, 25.0            # 設計: 二面角 / 稜角 / 線-面角(度)
bR, gR, dR = np.radians([BETA, GAMMA, DELTA])

# ── 面の設計法線(解析 GT) ────────────────────────────────────────────────
n1 = e2                                           # 面1(基準面)法線
n2 = np.cos(bR) * e2 + np.sin(bR) * e0            # 面2 法線: n1 と角 BETA をなす
w2 = m3._u(np.cross(n2, e1))                       # 面2 の面内方向(e1 と共に面2 を張る)

# ══════════════════════════════════════════════════════════════════════════
# 1) 基本要素: 2 点 → 直線 / 3 点 → 平面(閉形式・厳密)
# ══════════════════════════════════════════════════════════════════════════
lp, ld = m3.line_from_2points(c0, c0 + 3.0 * e1)   # 稜線を 2 点で定義
assert ang_deg(ld, e1) < 1e-9                      # 方向 = 稜線方向 e1(符号除き)
assert np.allclose(lp, c0)

pp, pn = m3.plane_from_3points(c0, c0 + e0, c0 + e1)  # 面1 を 3 点で定義
assert ang_deg(pn, n1) < 1e-9                      # 法線 = e2(符号除き)
print(f"line_from_2points  : 方向誤差 = {ang_deg(ld, e1):.2e} deg")
print(f"plane_from_3points : 法線誤差 = {ang_deg(pn, n1):.2e} deg")

# ══════════════════════════════════════════════════════════════════════════
# 2) 面の当てはめ: 面上点群(実測ノイズ付)→ fit_plane_3d(法線・残差)→ 二面角 / 稜線を連結
#    ノイズを入れるのは、fit_plane_3d の残差が「計測ノイズ床」を復元することを GT に使うため
#    (完全平面だと最小固有値が丸めで負に転び sqrt が nan になる = op の実挙動)。
# ══════════════════════════════════════════════════════════════════════════
SIGMA_P = 5e-4                                      # 面計測ノイズ(mm 相当)の標準偏差
g1 = np.random.default_rng(11).uniform(-5, 5, (120, 2))
P1 = (c0 + g1[:, 0:1] * e0 + g1[:, 1:2] * e1        # 面1 上の点群
      + np.random.default_rng(101).normal(0, SIGMA_P, (120, 3)))
g2 = np.random.default_rng(12).uniform(-5, 5, (120, 2))
P2 = (c0 + g2[:, 0:1] * e1 + g2[:, 1:2] * w2        # 面2 上の点群
      + np.random.default_rng(102).normal(0, SIGMA_P, (120, 3)))

c1, fn1, r1 = m3.fit_plane_3d(P1)
c2, fn2, r2 = m3.fit_plane_3d(P2)
assert ang_deg(fn1, n1) < 1e-2 and ang_deg(fn2, n2) < 1e-2          # 法線をノイズ限界で復元
assert 0.5 * SIGMA_P < r1 < 1.5 * SIGMA_P and 0.5 * SIGMA_P < r2 < 1.5 * SIGMA_P  # 残差=ノイズ床

# 連結: フィット法線 → 二面角。設計 BETA に一致(ノイズ限界)。
beta_meas = m3.angle_between_planes(fn1, fn2)
assert abs(beta_meas - BETA) < 0.05
print(f"fit_plane_3d       : 法線誤差 {ang_deg(fn1, n1):.2e}/{ang_deg(fn2, n2):.2e} deg, 残差 {r1:.2e}/{r2:.2e} (ノイズ {SIGMA_P})")
print(f"angle_between_planes: 実測 {beta_meas:.6f} deg (設計 {BETA})")

# 連結: 2 フィット面の交線 = 稜線。方向 = e1、点は両フィット面上(距離 ~0)。
ip, idr = m3.intersect_planes(c1, fn1, c2, fn2)
assert ang_deg(idr, e1) < 0.1
assert m3.distance_point_plane(ip, c1, fn1) < 1e-6
assert m3.distance_point_plane(ip, c2, fn2) < 1e-6
print(f"intersect_planes   : 稜線方向誤差 = {ang_deg(idr, e1):.2e} deg, 交点は両面上")

# ══════════════════════════════════════════════════════════════════════════
# 3) 稜線の当てはめ: 稜線点群 → fit_line_3d、素の 2 点線と平行(角 ~0)を連結確認
# ══════════════════════════════════════════════════════════════════════════
u = np.linspace(-6, 6, 40)
edge = c0 + u[:, None] * e1                          # 稜線上の点
flc, fld = m3.fit_line_3d(edge)
assert ang_deg(fld, e1) < 1e-9
# 連結: フィット稜線 ∥ 面 ∩ 面 稜線 → なす角 ~0
assert m3.angle_between_lines(fld, idr) < 1e-6
print(f"fit_line_3d        : 方向誤差 = {ang_deg(fld, e1):.2e} deg")
print(f"angle_between_lines: 稜線 vs 面∩面 = {m3.angle_between_lines(fld, idr):.2e} deg (平行)")

# ══════════════════════════════════════════════════════════════════════════
# 4) 頑健当てはめ: 外れ値混じり稜線 → ransac_line。素の fit_line_3d(null)を凌駕
# ══════════════════════════════════════════════════════════════════════════
rng = np.random.default_rng(21)
out = c0 + rng.uniform(-6, 6, (16, 1)) * e1 + rng.uniform(2, 6, (16, 1)) * (
    e0 * rng.choice([-1, 1], (16, 1)))              # 稜線から離れた外れ値
contaminated = np.vstack([edge, out])
params, mask, _ = rf.ransac_line(contaminated, thresh=0.1, iters=300, seed=0)
rl_err = ang_deg(params["direction"], e1)           # RANSAC 方向誤差
naive_dir = m3.fit_line_3d(contaminated)[1]         # null: 全点を素直に最小二乗
nv_err = ang_deg(naive_dir, e1)                     # null 方向誤差(外れ値に引かれる)
assert rl_err < 1.0                                 # RANSAC は稜線を復元
assert nv_err > 3.0                                 # 素フィットは外れ値で傾く
assert rl_err < 0.1 * nv_err                        # 判別的に null を下回る
assert int(mask.sum()) == len(edge)                 # inlier = 稜線点のみ
print(f"ransac_line        : 方向誤差 {rl_err:.3f} deg vs 素フィットnull {nv_err:.2f} deg / inlier {int(mask.sum())}/{len(edge)}")

# ══════════════════════════════════════════════════════════════════════════
# 5) 角度メトロロジー: angle_3points / angle_line_plane
# ══════════════════════════════════════════════════════════════════════════
A = c0 + e0                                          # 稜角 GAMMA: 頂点 c0、腕 e0 と (cosγ e0+sinγ e1)
B = c0
Cpt = c0 + np.cos(gR) * e0 + np.sin(gR) * e1
assert abs(m3.angle_3points(A, B, Cpt) - GAMMA) < 1e-7
assert abs(m3.angle_between_lines(e0, np.cos(gR) * e0 + np.sin(gR) * e1) - GAMMA) < 1e-7

probe_dir = np.cos(dR) * e0 + np.sin(dR) * e2        # 面1 に角 DELTA で差し込むプローブ線
assert abs(m3.angle_line_plane(probe_dir, n1) - DELTA) < 1e-7
print(f"angle_3points      : {m3.angle_3points(A, B, Cpt):.6f} deg (設計 {GAMMA})")
print(f"angle_line_plane   : {m3.angle_line_plane(probe_dir, n1):.6f} deg (設計 {DELTA})")

# ══════════════════════════════════════════════════════════════════════════
# 6) 距離メトロロジー: point-plane / point-line / line-line
# ══════════════════════════════════════════════════════════════════════════
H_STANDOFF = 3.5
p_above = c0 + H_STANDOFF * e2 + 2.0 * e0            # 面1 から H_STANDOFF 浮いた点
assert abs(m3.distance_point_plane(p_above, c0, n1) - H_STANDOFF) < 1e-9

T_OFF = 2.0
q_off = c0 + 4.0 * e1 + T_OFF * e0                   # 稜線(c0,e1)から T_OFF ずれた点
assert abs(m3.distance_point_line(q_off, c0, e1) - T_OFF) < 1e-9

H_SKEW = 5.0                                          # ねじれ 2 直線の共通垂線長
assert abs(m3.distance_line_line(c0, e0, c0 + H_SKEW * e2, e1) - H_SKEW) < 1e-9
print(f"distance_point_plane: {m3.distance_point_plane(p_above, c0, n1):.6f} (設計 {H_STANDOFF})")
print(f"distance_point_line : {m3.distance_point_line(q_off, c0, e1):.6f} (設計 {T_OFF})")
print(f"distance_line_line  : {m3.distance_line_line(c0, e0, c0 + H_SKEW * e2, e1):.6f} (設計 {H_SKEW}, skew)")

# ══════════════════════════════════════════════════════════════════════════
# 7) 線 ∩ 面: intersect_line_plane(当たり点は面上、平行線は None)
# ══════════════════════════════════════════════════════════════════════════
line_pt = c0 + 5.0 * e2 + 1.0 * e0                   # 面1 の 5 上方からプローブを下ろす
hit = m3.intersect_line_plane(line_pt, probe_dir, c0, n1)
assert hit is not None and m3.distance_point_plane(hit, c0, n1) < 1e-9   # 当たり点は面上
assert m3.intersect_line_plane(c0 + e2, e0, c0, n1) is None              # 面に平行 → None
print(f"intersect_line_plane: 当たり点の面外れ = {m3.distance_point_plane(hit, c0, n1):.2e} (平行線は None)")

# ══════════════════════════════════════════════════════════════════════════
# 8) 球の当てはめ: fit_sphere_3d。中心の面からの高さを連結計測(球+面フィット)
# ══════════════════════════════════════════════════════════════════════════
BALL_H, BALL_R = 4.0, 2.6
cs = c0 + BALL_H * e2 + 1.0 * e0                     # 面1 の上 BALL_H に座す球の中心
sph_u = np.random.default_rng(31).standard_normal((220, 3))
sph_u /= np.linalg.norm(sph_u, axis=1, keepdims=True)
Psph = cs + BALL_R * sph_u
sc, sr = m3.fit_sphere_3d(Psph)
assert np.allclose(sc, cs, atol=1e-6) and abs(sr - BALL_R) < 1e-6
# 連結: フィット球中心 → フィット面1 までの距離 = ボール座面高さ
standoff = m3.distance_point_plane(sc, c1, fn1)
assert abs(standoff - BALL_H) < 1e-6
print(f"fit_sphere_3d      : 中心誤差 {np.linalg.norm(sc - cs):.2e}, 半径誤差 {abs(sr - BALL_R):.2e}, 座面高 {standoff:.6f} (設計 {BALL_H})")

# ══════════════════════════════════════════════════════════════════════════
# 9) 円の当てはめ: fit_circle_3d(面1 上の円穴)。軸 ∥ 面法線・中心は面上を連結確認
# ══════════════════════════════════════════════════════════════════════════
BORE_R = 1.7
cc = c0 + 1.0 * e0                                   # 面1 上の円穴中心
th = np.linspace(0, 2 * np.pi, 72, endpoint=False)
Pcir = cc + BORE_R * (np.cos(th)[:, None] * e0 + np.sin(th)[:, None] * e1)
ccenter, cr, cnorm = m3.fit_circle_3d(Pcir)
assert np.allclose(ccenter, cc, atol=1e-6) and abs(cr - BORE_R) < 1e-6
assert ang_deg(cnorm, n1) < 1e-6                    # 円軸 ∥ 面1 法線(円は面内)
assert m3.distance_point_plane(ccenter, c1, fn1) < 1e-6   # 円中心は面1 上
print(f"fit_circle_3d      : 中心誤差 {np.linalg.norm(ccenter - cc):.2e}, 半径誤差 {abs(cr - BORE_R):.2e}, 軸-面法線 {ang_deg(cnorm, n1):.2e} deg")

# ══════════════════════════════════════════════════════════════════════════
# 10) 面形状誤差: surface_form_error(理想曲面の次数が合えば残差 ~0)
# ══════════════════════════════════════════════════════════════════════════
yy, xx = np.mgrid[0:48, 0:48]
Z2 = (2.0 + 0.30 * xx - 0.20 * yy + 0.010 * xx**2      # 厳密な 2 次曲面(球面度部品)
      - 0.008 * yy**2 + 0.005 * xx * yy)
_, rms2, pv2 = m3.surface_form_error(Z2, degree=2)     # 次数一致 → 残差 ~0
_, rms1, pv1 = m3.surface_form_error(Z2, degree=1)     # 次数不足 → 平らにできない
assert rms2 < 1e-6 and pv2 < 1e-6                      # 2 次部品を 2 次で除けば形状誤差 ~0
assert rms1 > 0.1                                      # 平面近似では有意な残差
assert rms2 < 1e-4 * rms1                              # 判別的に次数不足 null を下回る
Z1 = 3.0 + 0.40 * xx - 0.25 * yy                       # 厳密な平面(平面度部品)
_, rms1p, _ = m3.surface_form_error(Z1, degree=1)
assert rms1p < 1e-6                                     # 平面を deg1 で除けば ~0
print(f"surface_form_error : 2次残差rms {rms2:.2e} << 1次残差rms {rms1:.4f} / 平面のdeg1残差 {rms1p:.2e}")

# ══════════════════════════════════════════════════════════════════════════
# 11) 背景平坦化: background_flatten(2 次照明ムラを引き去り高周波信号を回収)
# ══════════════════════════════════════════════════════════════════════════
Yy, Xx = np.mgrid[0:64, 0:64]
illum = (5.0 + 0.10 * Xx - 0.05 * Yy + 0.0020 * Xx**2    # 厳密な 2 次照明ムラ
         + 0.0010 * Yy**2 - 0.0015 * Xx * Yy)
flat_bg = m3.background_flatten(illum, degree=2)         # 純ムラ → ほぼゼロ
assert np.abs(flat_bg).max() < 1e-6
signal = 0.5 * np.sin(2 * np.pi * 6 * Xx / 64) * np.sin(2 * np.pi * 5 * Yy / 64)
img = illum + signal
flat = m3.background_flatten(img, degree=2)              # ムラを引き信号を回収
corr_flat = float(np.corrcoef(flat.ravel(), signal.ravel())[0, 1])
corr_raw = float(np.corrcoef(img.ravel(), signal.ravel())[0, 1])   # null: 生画像(照明優勢)
assert corr_flat > 0.99                                  # 信号を高精度に回収
assert corr_flat > corr_raw + 0.5                        # 判別的に生画像 null を凌駕
print(f"background_flatten : 純ムラ残差max {np.abs(flat_bg).max():.2e} / 信号相関 平坦後 {corr_flat:.4f} vs 生 {corr_raw:.4f}")

print("PASS: 1 部品の幾何メトロロジー — 面/線/球/円の当てはめが法線・方向・中心・半径を"
      "機械精度で復元し、その出力を角度(β=35/γ=40/δ=25)・距離(隙間/垂線/skew)・"
      "交差(面∩面稜線, 線∩面当たり点)へ連結した計測がすべて設計真値に一致。"
      "ransac_line は外れ値下で素フィットnullを桁違いに凌ぎ、surface_form_error/"
      "background_flatten も次数一致残差~0・照明ムラ除去で各 null を判別的に上回った")
