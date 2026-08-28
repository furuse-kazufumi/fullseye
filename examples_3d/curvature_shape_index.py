# -*- coding: utf-8 -*-
"""事例: ガウス曲率の符号で表面を「ドーム」と「鞍点」に分ける (shape_analysis).

平たく言うと: 物体表面の各点が、お椀を伏せたような凸(楕円点=ドーム)なのか、峠の
鞍のように一方向へ反り返る鞍点(双曲点)なのかは、把持点選びや欠陥判定で効く。これを
分けられるのは**ガウス曲率 K=k1·k2 の符号**であって、平均曲率 H=(k1+k2)/2 では分けられない
(H は片側だけ強い凸でも大きくなる)。トーラス(ドーナツ)はこの違いの教科書例:
外周は楕円(K>0)、内周(穴側)は鞍点(K<0)。

``curvature3d.gaussian_curvature`` を密なトーラス点群に当て、外周/内周を符号で正しく
分類できるかを、解析的な真値(トーラスの K=cos v /(r(R+r cos v)))と照合する。

検証(GT): 生成時に各点のチューブ角 v を知っているので真の領域が分かる。外周帯(cos v>0.5)は
K>0、内周帯(cos v<-0.5)は K<0 が真値。ガウス曲率の符号分類がこの真値に高精度で一致するか。

beat-the-null: このトーラス(R=1.0, r=0.35)は外周も内周も**平均曲率 H が正**なので、H の符号で
楕円/双曲を分けようとすると外周と内周を同じ型に貼ってしまい分離できない(≈偶然)。ガウス曲率の
符号分類がこの H 符号 null を判別的に上回ることを assert する。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np
import curvature3d as C

R, r = 1.0, 0.35            # 主半径 / 管半径


def torus_points(n_u=140, n_v=90, seed=0):
    """トーラス表面を (u,v) 格子で密サンプル。各点のチューブ角 v も返す(GT用)。"""
    u = np.linspace(0, 2 * np.pi, n_u, endpoint=False)
    v = np.linspace(0, 2 * np.pi, n_v, endpoint=False)
    uu, vv = np.meshgrid(u, v, indexing="ij")
    uu, vv = uu.ravel(), vv.ravel()
    x = (R + r * np.cos(vv)) * np.cos(uu)
    y = (R + r * np.cos(vv)) * np.sin(uu)
    z = r * np.sin(vv)
    P = np.stack([x, y, z], axis=1)
    return P, vv


# --- 1) トーラス点群 + 真のチューブ角 v ------------------------------------
P, v = torus_points()
cosv = np.cos(v)
outer = cosv > 0.5                       # 外周帯: 真値 K>0(楕円/ドーム)
inner = cosv < -0.5                      # 内周帯: 真値 K<0(双曲/鞍点)

# 解析的な真のガウス曲率(符号の裏取り): K = cos v / (r (R + r cos v))
K_true = cosv / (r * (R + r * cosv))
assert np.all(K_true[outer] > 0) and np.all(K_true[inner] < 0), "解析真値の前提が不成立"

# --- 2) 実 op: 点群からガウス曲率と平均曲率を推定 --------------------------
K = C.gaussian_curvature(P, k=25)        # 楕円/双曲を分けられる量
H = C.mean_curvature(P, k=25)            # 分けられない量(null 用)

# --- 3) GT: ガウス曲率の符号が外周(+)/内周(-)を正しく分類するか ----------
acc_outer = float(np.mean(K[outer] > 0))
acc_inner = float(np.mean(K[inner] < 0))
gauss_sep = 0.5 * (acc_outer + acc_inner)          # 楕円/双曲の分離精度

# --- 4) beat-null: 平均曲率の符号では分けられない --------------------------
# H の符号で「楕円 vs 双曲」を当てようとする最良の割り当てを許しても分離できないことを示す。
h_out_pos = float(np.mean(H[outer] > 0))
h_in_neg = float(np.mean(H[inner] < 0))
mean_sep_a = 0.5 * (h_out_pos + h_in_neg)          # 割り当て: 楕円=H>0, 双曲=H<0
mean_sep_b = 0.5 * ((1 - h_out_pos) + (1 - h_in_neg))  # 反転割り当て
mean_sep = max(mean_sep_a, mean_sep_b)             # H に有利な最良割り当て

print(f"外周(真K>0)でK>0の割合   : {acc_outer:.3f}")
print(f"内周(真K<0)でK<0の割合   : {acc_inner:.3f}")
print(f"ガウス曲率の分離精度       : {gauss_sep:.3f}")
print(f"平均曲率H: 外周でH>0 {h_out_pos:.3f} / 内周でH>0 {float(np.mean(H[inner] > 0)):.3f}")
print(f"平均曲率の最良分離(null)   : {mean_sep:.3f}  (このR,rでは外周も内周もH>0=分けられない)")

# GT: ガウス曲率は外周/内周を高精度で分離(>=0.9)。平均曲率の符号は分離できず(<=0.6)、
# ガウス曲率が明確に(>=0.3 差で)上回る = 楕円/双曲の判別にはガウス曲率が必要。
assert acc_outer > 0.9, f"外周を楕円(K>0)と分類できていない: {acc_outer:.3f}"
assert acc_inner > 0.9, f"内周を双曲(K<0)と分類できていない: {acc_inner:.3f}"
assert mean_sep < 0.6, f"平均曲率で分けられてしまっている(この例の主張が崩れる): {mean_sep:.3f}"
assert gauss_sep > mean_sep + 0.3, \
    f"ガウス曲率が平均曲率nullを判別的に上回れていない: {gauss_sep:.3f} vs {mean_sep:.3f}"
print(f"PASS: ガウス曲率の符号が外周(楕円)/内周(鞍点)を分離精度 {gauss_sep:.3f} で分類。"
      f"平均曲率null {mean_sep:.3f}(このトーラスはH>0一色で分離不能)を判別的に上回る")
