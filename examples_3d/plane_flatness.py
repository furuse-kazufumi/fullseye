# -*- coding: utf-8 -*-
"""事例: 平面度メトロロジー(基準面からの偏差)。

実問題: 加工した金属プレートや定盤が「どれだけ平らか」を検査したい。
点群を測って最小二乗の基準平面を当て、そこからの各点のはみ出し量を測る。
平面度(flatness)は基準面からの残差の広がり(peak-to-valley = 最大 - 最小、
および RMS)で表す。ここでは既知の高さ h の膨らみ(bump)をわざと作り込み、
measure_plane が返す平面度がその既知の高さと整合することを数値で確かめる。
"""
import numpy as np
import pipeline3d as P

rng = np.random.default_rng(0)

# --- 合成データ: ほぼ平面 + 既知高さの膨らみ --------------------------------
N = 4000
BUMP_H = 0.50                     # 既知の膨らみの高さ(GT)
# 基準面は水平(z=0)。微小な測定ノイズ(sigma=2mm 相当)を全点に付加。
xy = rng.uniform(0.0, 10.0, size=(N, 2))
z = np.zeros(N) + rng.normal(0.0, 0.002, size=N)

# 中央に局所的なガウス状の膨らみ(sigma=0.5 の小さく鋭いふくらみ)。局所的なので
# 基準面(重心)の持ち上げは小さく、ピークの基準面からの距離 ≈ 膨らみ高さになる。
cx, cy = 5.0, 5.0
r2 = (xy[:, 0] - cx) ** 2 + (xy[:, 1] - cy) ** 2
bump = BUMP_H * np.exp(-r2 / (2 * 0.5 ** 2))
z = z + bump
pts = np.column_stack([xy, z])
# 頂点を確実に標本化するため、膨らみの中心にちょうど高さ BUMP_H の点を 1 点足す。
pts = np.vstack([pts, [cx, cy, BUMP_H]])
N = len(pts)

# 膨らみが実際に付いていること(この点群の生の高さ範囲)を確認
print("点数:", N)
print("既知の膨らみ高さ BUMP_H:", BUMP_H)
print("生の z 範囲            :", f"{z.min():.4f} .. {z.max():.4f}")

# --- 平面度計測 --------------------------------------------------------------
# measure_plane: 最小二乗の基準平面(法線・通過点)を当て、
# 各点の基準面からの距離の RMS と PV(peak-to-valley)を返す。
mp = P.measure_plane(pts)
print("\n--- measure_plane の結果 ---")
print("基準面 法線 :", np.round(mp["normal"], 4))
print("flatness_rms:", f"{mp['flatness_rms']:.4f}")
print("pv (P-V)    :", f"{mp['pv']:.4f}")

# --- GT 検証(数値 assert)---------------------------------------------------
# 局所的な膨らみが少数のとき、基準面は元の平面(z=0)にほぼ一致し、
# ピーク点の基準面からの距離 ≈ 膨らみ高さ。よって PV は既知 BUMP_H に近い。
# 中心の膨らみが centroid を h*(膨らみ寄与/N) だけ持ち上げるので厳密一致はしないが、
# 局所ゆえその持ち上げは小さく、PV は BUMP_H の許容範囲に収まる。
print("\n--- GT 整合チェック ---")
print(f"|pv - BUMP_H| = {abs(mp['pv'] - BUMP_H):.4f}  (許容 0.03)")
assert abs(mp["pv"] - BUMP_H) < 0.03, (mp["pv"], BUMP_H)

# 基準面の法線はほぼ +z 方向(水平な定盤)
assert abs(abs(mp["normal"][2]) - 1.0) < 1e-3, mp["normal"]

# 膨らみが無い対照点群では平面度がほぼ 0(ノイズのみ)= 欠陥検出の識別性
flat_only = np.column_stack([xy, rng.normal(0.0, 0.002, size=len(xy))])
mp0 = P.measure_plane(flat_only)
print(f"対照(膨らみ無し)の pv = {mp0['pv']:.4f}  (膨らみありの {mp['pv']:.4f} より十分小)")
assert mp0["pv"] < 0.05 and mp["pv"] > 5 * mp0["pv"], (mp0["pv"], mp["pv"])

print("\nOK: 測った平面度 PV が既知の膨らみ高さ BUMP_H と整合し、欠陥を検出できた")
