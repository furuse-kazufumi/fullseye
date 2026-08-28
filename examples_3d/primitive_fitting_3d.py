# -*- coding: utf-8 -*-
"""事例: 点群から幾何プリミティブ(直線・平面・球・円・最小包含球)を最小二乗で当てる (metrology).

平たく言うと: スキャンした点群から「これは直線か・平面か・球か・円か」を数式で言い当て、
中心・半径・向き・残差を出すのが計測(メトロロジー)の基本。2-D の
``fit_line`` / ``fit_circle`` に対応する 3-D 版を (depth, row, col) 座標で一括に示す。
``measure3d`` の fit 群 + 最小包含球をまとめて使う。

検証(GT): 既知パラメータの直線・平面・球・円の表面に点を生成し(浮動小数の丸め以外ノイズ無し)、
各 fit が真値を機械精度で復元することを assert する:
    - fit_line3   : 方向ベクトル(符号を除き)+ 残差 ~0
    - fit_plane3  : 法線(符号を除き)+ 残差 ~0
    - fit_sphere3 : 中心・半径 + 残差 ~0
    - fit_circle3 : 中心・半径・法線
    - smallest_sphere3 : 球面上の点なら半径 = 球半径、全点内包

beat-the-null: 各 fit の残差(RMS)が「わざと外した当てはめ」の残差より桁違いに小さいことを
判別的に示す(平面 fit の法線を 90 度ずらした null、球 fit の中心を大きくずらした null)。当てはめが
偶然でなく本当に形状を捉えていることの裏付け。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np
import measure3d as m3


def rot(seed):
    q, _ = np.linalg.qr(np.random.default_rng(seed).standard_normal((3, 3)))
    if np.linalg.det(q) < 0:
        q[:, 0] = -q[:, 0]
    return q


R = rot(1)

# --- 1) 直線: 既知の方向 d0 を通る点列 -------------------------------------
d0 = R[:, 0]
c0 = np.array([12.0, 5.0, -3.0])
Pline = c0 + np.linspace(-4, 4, 50)[:, None] * d0
rl = m3.fit_line3(Pline)
print(f"fit_line3   : 方向誤差 |cosθ|-1 = {abs(abs(rl['direction'] @ d0) - 1):.2e}, rms = {rl['rms']:.2e}")
assert abs(abs(rl["direction"] @ d0) - 1) < 1e-9 and rl["rms"] < 1e-9

# --- 2) 平面: 既知の法線 n0 の面上の点 -------------------------------------
n0 = R[:, 2]
g = np.random.default_rng(2).uniform(-5, 5, (80, 2))
Pplane = np.array([1.0, 2.0, 3.0]) + g[:, 0:1] * R[:, 0] + g[:, 1:2] * R[:, 1]
rp = m3.fit_plane3(Pplane)
# beat-null: 法線を面内方向(90 度ずらし)にした当てはめの残差は桁違いに大きい
null_n = R[:, 0]
null_rms = float(np.sqrt(np.mean(((Pplane - Pplane.mean(0)) @ null_n) ** 2)))
print(f"fit_plane3  : 法線誤差 = {abs(abs(rp['normal'] @ n0) - 1):.2e}, rms = {rp['rms']:.2e}  (null法線 rms = {null_rms:.2f})")
assert abs(abs(rp["normal"] @ n0) - 1) < 1e-9 and rp["rms"] < 1e-6
assert rp["rms"] < 1e-3 * null_rms                         # 判別的に null を下回る

# --- 3) 球: 既知の中心・半径の球面上の点 -----------------------------------
cs, Rr = np.array([3.0, -2.0, 7.0]), 4.3
u = np.random.default_rng(4).standard_normal((200, 3))
u /= np.linalg.norm(u, axis=1, keepdims=True)
Psph = cs + Rr * u
rs = m3.fit_sphere3(Psph)
null_center = cs + np.array([2.0, 0.0, 0.0])                # ずらした中心の null
null_srms = float(np.std(np.linalg.norm(Psph - null_center, axis=1)))
print(f"fit_sphere3 : 中心誤差 = {np.linalg.norm(rs['center'] - cs):.2e}, 半径誤差 = {abs(rs['r'] - Rr):.2e}, rms = {rs['rms']:.2e}  (null中心 rms = {null_srms:.3f})")
assert np.allclose(rs["center"], cs, atol=1e-6) and abs(rs["r"] - Rr) < 1e-6
assert rs["rms"] < 1e-3 * null_srms

# --- 4) 円: 既知の面内の円周上の点 -----------------------------------------
cc0, rc = np.array([0.0, 1.0, -1.0]), 2.7
th = np.linspace(0, 2 * np.pi, 60, endpoint=False)
Pcir = cc0 + rc * (np.cos(th)[:, None] * R[:, 0] + np.sin(th)[:, None] * R[:, 1])
rcir = m3.fit_circle3(Pcir)
print(f"fit_circle3 : 中心誤差 = {np.linalg.norm(rcir['center'] - cc0):.2e}, 半径誤差 = {abs(rcir['r'] - rc):.2e}, 法線誤差 = {abs(abs(rcir['normal'] @ n0) - 1):.2e}")
assert np.allclose(rcir["center"], cc0, atol=1e-6) and abs(rcir["r"] - rc) < 1e-6
assert abs(abs(rcir["normal"] @ n0) - 1) < 1e-6

# --- 5) 最小包含球: 球面上の点なら半径 = 球半径, 全点内包 -------------------
ss = m3.smallest_sphere3(Psph)
aabb_diag = 0.5 * np.linalg.norm(Psph.max(0) - Psph.min(0))   # null: AABB 対角の半分
print(f"smallest_sphere3 : 半径 = {ss['r']:.4f} (真 {Rr}), 全点内包 = {bool(np.all(np.linalg.norm(Psph - ss['center'], axis=1) <= ss['r'] + 1e-7))}  (AABB対角/2 = {aabb_diag:.3f})")
assert abs(ss["r"] - Rr) < 1e-6
assert np.all(np.linalg.norm(Psph - ss["center"], axis=1) <= ss["r"] + 1e-7)

print("PASS: 直線/平面/球/円の 3-D fit が既知プリミティブを機械精度で復元し、"
      "各残差が『わざと外した』null を桁違いに下回る。最小包含球も球半径を厳密復元し全点を内包")
