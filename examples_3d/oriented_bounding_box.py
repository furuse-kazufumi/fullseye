# -*- coding: utf-8 -*-
"""事例: 傾いた直方体部品の「本当の寸法」を最小体積の有向境界箱で測る (metrology).

平たく言うと: 部品をスキャンした点群から寸法(縦×横×高さ)を出したいとき、軸に平行な
境界箱(AABB=smallest_rectangle1 の 3-D 版)は、部品が斜めを向いていると回転ぶんだけ
膨らんで**実寸より大きく**出てしまう。正しくは、点群にいちばんぴったり沿う向きを探して
体積が最小になる箱を当てる — これが**最小体積の有向境界箱(OBB)**、2-D の
``smallest_rectangle2`` の 3-D 版。座標は (depth, row, col)。

``measure3d.smallest_box3`` は凸包の各面法線を箱の1軸の候補にして、それに直交する面内で
2-D 最小面積長方形(回転キャリパー)を解き、体積が最小になる向きを選ぶ(最適箱は凸包の面と
必ず一面が接する、という定理を 3-D に持ち込んだもの)。PCA で軸を取るだけの箱
(``fit_box3`` / ``pcseg.obb``)は非対称形状で最小にならないので、そこも上回る。

検証(GT): 半径 (l1,l2,l3)=(5,2,1) の直方体表面を密サンプルし、既知の回転 R と並進 t を掛ける。
smallest_box3 が半径 (5,2,1)・中心 t・体積 8·5·2·1=80 を機械精度で復元するか照合。

beat-the-null: 同じ点群に対し AABB(軸平行)の体積は回転で大きく膨らむ(この配置で真値の ~1.8 倍)。
OBB がその null を大きく下回り、かつ真値 80 に一致することを assert。さらに非対称な正四面体で
OBB 体積 ≤ PCA 箱体積(最小箱は PCA 箱より小さくなり得る)も確かめる。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np
import measure3d as m3


def rot(seed):
    """行列式 +1 の直交行列(純回転)を1つ返す。"""
    q, _ = np.linalg.qr(np.random.default_rng(seed).standard_normal((3, 3)))
    if np.linalg.det(q) < 0:
        q[:, 0] = -q[:, 0]
    return q


def box_surface(half, R, t, n=9):
    """半径 half の直方体の6面を (depth,row,col) 格子で密サンプルし、R,t を掛ける。"""
    g = np.linspace(-1, 1, n)
    pts = []
    for a in (-1, 1):
        for i in g:
            for j in g:
                pts.append([a, i, j]); pts.append([i, a, j]); pts.append([i, j, a])
    return (np.array(pts, float) * half) @ R.T + t


# --- 1) 既知の傾いた直方体部品(点群) --------------------------------------
half = np.array([5.0, 2.0, 1.0])          # 真の半径(縦・横・高さの半分)
R, t = rot(7), np.array([10.0, -4.0, 6.0])
P = box_surface(half, R, t)
true_vol = float(np.prod(2 * half))       # = 80

# --- 2) 実 op: AABB(null)/ PCA 箱 / 最小体積 OBB --------------------------
aabb = m3.smallest_box3_axis(P)           # 軸平行(回転で膨らむ null)
pca = m3.fit_box3(P)                       # PCA 箱(向きは取れるが最小ではない)
obb = m3.smallest_box3(P)                  # 最小体積 OBB(本命)

obb_half = np.array([obb["l1"], obb["l2"], obb["l3"]])

# --- 3) GT: OBB が真の半径・中心・体積を復元 -------------------------------
print(f"真の半径 (l1,l2,l3)      : {half.tolist()}  → 真の体積 {true_vol:.3f}")
print(f"OBB 半径                 : ({obb['l1']:.4f}, {obb['l2']:.4f}, {obb['l3']:.4f})")
print(f"OBB 中心 (depth,row,col) : {obb['center'].round(4).tolist()}  (真値 {t.tolist()})")
print(f"OBB 体積                 : {obb['volume']:.4f}")
print(f"AABB 体積 (null)         : {aabb['volume']:.4f}   (回転で膨らむ)")
print(f"PCA 箱 体積              : {pca['volume']:.4f}")

assert np.allclose(np.sort(obb_half), np.sort(half), atol=1e-6), \
    f"OBB が真の半径を復元できていない: {obb_half}"
assert np.allclose(obb["center"], t, atol=1e-6), f"OBB 中心が真値とずれる: {obb['center']}"
assert abs(obb["volume"] - true_vol) < 1e-4, f"OBB 体積が真値とずれる: {obb['volume']}"

# beat-the-null: 軸平行 AABB は真値より大きく膨らむ。OBB はそれを大きく下回り真値に一致。
assert aabb["volume"] > true_vol * 1.5, \
    f"この配置で AABB が膨らんでいない(例の前提が崩れる): {aabb['volume']:.3f}"
assert obb["volume"] < aabb["volume"] - 1e-3, \
    f"OBB が AABB(null)を下回れていない: {obb['volume']:.3f} vs {aabb['volume']:.3f}"

# 非対称形状(正四面体)では最小箱は PCA 箱より小さくなり得る
tet = np.array([[1, 1, 1], [1, -1, -1], [-1, 1, -1], [-1, -1, 1]], float) * 3.0
tet = tet @ rot(8).T + np.array([2.0, 2.0, 2.0])
obb_t, pca_t = m3.smallest_box3(tet), m3.fit_box3(tet)
assert obb_t["volume"] <= pca_t["volume"] + 1e-9, \
    f"最小 OBB が PCA 箱を上回ってしまった: {obb_t['volume']:.3f} vs {pca_t['volume']:.3f}"
print(f"正四面体: OBB 体積 {obb_t['volume']:.3f} ≤ PCA 箱 {pca_t['volume']:.3f}  "
      f"(最小箱は PCA 箱より小さい)")

ratio = aabb["volume"] / obb["volume"]
print(f"PASS: 最小体積 OBB が傾いた直方体の実寸 (5,2,1)・体積 {true_vol:.1f} を機械精度で復元。"
      f"軸平行 AABB(体積 {aabb['volume']:.1f} = {ratio:.1f}倍に膨張)を判別的に下回り、"
      f"非対称形状では PCA 箱も上回る")
