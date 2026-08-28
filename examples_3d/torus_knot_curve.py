# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: 結び目のある非平面 3D 空間曲線(トーラス結び目)の微分幾何量を計測する (shape_analysis).

ケーブルの取り回し・溶接シーム・工具軌跡のように、3D 空間をよじれながら閉じる曲線は、
円や螺旋のような素直な形では近似できない。ここでは (p,q)=(2,3) トーラス結び目(三葉結び目)を
閉形式パラメータ表示から密なポリラインとして生成し、curve3d の空間曲線 op
(arc_length / curvature_torsion / frenet_frame)だけで弧長・曲率・捩率・Frenet 標構を求め、
すべて解析解または独立計算と突き合わせて検証する。合成データのみ・ネット不要・決定的。

検証(GT): 結び目の「よじれ」は捩率 τ に現れ、平面曲線と判別的に分かれる。
  (a) 弧長: curve3d.arc_length(密ポリライン N=4000)が、解析速度 |r'(t)|=√(r²q²+p²(R+r cos qt)²)
      の超細分台形積分(真値)と相対 1e-5 未満で一致(粗い N=40 は 1e-2 台で桁違いに外す)。
  (b) 捩率: 結び目は非平面なので |τ| が実質的に非ゼロ。二方式(閉形式 op と Frenet–Serret
      τ=-(dB/ds)·N)が中央値相対 1e-3 未満で一致=真の幾何量であることの独立確認。
  beat-null: 同じ長さの「平面」円は捩率が構造的にゼロ(傾けた平面でも丸め誤差 ~5e-10 のみ)。
  結び目の中央 |τ|≈0.28 は円の ~5e8 倍(桁違い)で、平面/非平面を判別的に切り分ける。
  一方、弧長と曲率(円は中央 κ=1/r に 1e-6 未満で一致)はどちらも正確=op 自体は正しい。
"""
import numpy as np
import curve3d  # arc_length / curvature_torsion / frenet_frame(空間曲線 op)

# 決定的: 乱数は一切使わない(閉形式パラメータ表示のみ)。念のため seed を固定。
np.random.seed(0)

# numpy 2.x は trapezoid、旧版は trapz。どちらでも真値(細分台形積分)を計算できるように。
_trapz = getattr(np, "trapezoid", None) or np.trapz


def torus_knot(p, q, R, r, n):
    """(p,q) トーラス結び目を n 点の順序付きポリラインで生成(閉形式パラメータ表示)。

    半径 R(主)・r(管)のトーラス上を、主軸まわりに p 周・管まわりに q 周する曲線:
      x=(R+r cos qt) cos pt,  y=(R+r cos qt) sin pt,  z=r sin qt,  t∈[0,2π)。
    gcd(p,q)=1 なので (2,3) は三葉結び目(trefoil)。endpoint=False で重複点を避け、
    閉ループの弧長を測るときだけ先頭点を末尾に付けて閉じる。
    """
    t = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    A = R + r * np.cos(q * t)
    return np.stack([A * np.cos(p * t), A * np.sin(p * t), r * np.sin(q * t)], axis=1)


def rot_matrix(axis, ang):
    """Rodrigues の回転行列(平面円を軸非依存な一般平面へ傾けて null を作る)。"""
    ax = np.asarray(axis, float)
    ax = ax / np.linalg.norm(ax)
    c, s = np.cos(ang), np.sin(ang)
    x, y, z = ax
    return np.array([[c + x * x * (1 - c), x * y * (1 - c) - z * s, x * z * (1 - c) + y * s],
                     [y * x * (1 - c) + z * s, c + y * y * (1 - c), y * z * (1 - c) - x * s],
                     [z * x * (1 - c) - y * s, z * y * (1 - c) + x * s, c + z * z * (1 - c)]])


def closed(poly):
    """先頭点を末尾に付けて閉ループにする(弧長に閉じ区間を含めるため)。"""
    return np.vstack([poly, poly[:1]])


P, Q, R, RT = 2, 3, 2.0, 0.8   # (p,q)=(2,3) 三葉結び目、トーラス半径 R=2.0 / r=0.8
N = 4000                        # ポリライン点数(密)

# --- 0) 弧長の真値(GT): 解析速度 |r'(t)| の超細分台形積分 ---------------------
# speed(t)² = r²q² + p²(R + r cos qt)²(下記で導出、閉形式)。周期・滑らかなので
# 台形積分は M を大きくすれば指数的に真値へ収束する。これを弧長の真値 L_gt とする。
M = 400_000
tg = np.linspace(0.0, 2.0 * np.pi, M + 1)
speed = np.sqrt(RT * RT * Q * Q + P * P * (R + RT * np.cos(Q * tg)) ** 2)
L_gt = float(_trapz(speed, tg))

# --- 1) 結び目の生成と弧長 ---------------------------------------------------
knot = torus_knot(P, Q, R, RT, N)
_, L_knot = curve3d.arc_length(closed(knot))
err_knot = abs(L_knot - L_gt) / L_gt

# 粗い N=40 のポリラインは弦近似の誤差が桁違いに大きい(密の正確さが意味を持つことの対照)
knot_coarse = torus_knot(P, Q, R, RT, 40)
_, L_coarse = curve3d.arc_length(closed(knot_coarse))
err_coarse = abs(L_coarse - L_gt) / L_gt

# --- 2) 結び目の捩率・曲率(非平面の指標)------------------------------------
kappa_k, tau_k = curve3d.curvature_torsion(knot)
med_tau_knot = float(np.median(np.abs(tau_k)))
z_extent = float(knot[:, 2].max() - knot[:, 2].min())   # 非平面(z 方向の広がり)

# --- 3) Frenet 標構: 直交正規性 + Frenet–Serret による捩率の独立確認 ----------
T, Nn, B = curve3d.frenet_frame(knot)
unit_err = max(np.abs(np.linalg.norm(T, axis=1) - 1).max(),
               np.abs(np.linalg.norm(Nn, axis=1) - 1).max(),
               np.abs(np.linalg.norm(B, axis=1) - 1).max())
ortho_err = max(np.abs(np.sum(T * Nn, axis=1)).max(),
                np.abs(np.sum(T * B, axis=1)).max(),
                np.abs(np.sum(Nn * B, axis=1)).max())
bxn_err = float(np.abs(B - np.cross(T, Nn)).max())       # B == T×N か
# Frenet–Serret: dB/ds = -τ N  ⇒  τ = -(dB/ds)·N(弧長微分)。閉形式 op と独立な第2経路。
cum, _ = curve3d.arc_length(knot)
ds = np.gradient(cum)
dB = np.gradient(B, axis=0) / ds[:, None]
tau_fs = -np.sum(dB * Nn, axis=1)
interior = slice(5, -5)                                  # seam 端点(片側差分)を除く
sig = np.abs(tau_k[interior]) > 0.05                     # 有意な捩率の点で相対誤差を測る
tau_agree = float(np.median(np.abs(tau_k[interior][sig] - tau_fs[interior][sig])
                            / np.abs(tau_k[interior][sig])))

# --- 4) beat-null: 同じ長さの「平面」円(傾けた一般平面) ----------------------
# 半径 = L_gt/2π で円周が結び目と同じ長さ。軸非依存を示すため一般平面へ傾ける。
rad = L_gt / (2.0 * np.pi)
u = np.linspace(0.0, 2.0 * np.pi, N, endpoint=False)
circ = np.stack([rad * np.cos(u), rad * np.sin(u), np.zeros_like(u)], axis=1)
circ = circ @ rot_matrix([0.3, 0.7, 0.5], 0.9).T        # 一般平面へ回転(弧長不変)
_, L_circ = curve3d.arc_length(closed(circ))
err_circ = abs(L_circ - L_gt) / L_gt
kappa_c, tau_c = curve3d.curvature_torsion(circ)
med_tau_circ = float(np.median(np.abs(tau_c)))          # 平面 ⇒ 構造的にゼロ(丸め誤差のみ)
kappa_err_circ = abs(float(np.median(kappa_c)) - 1.0 / rad) / (1.0 / rad)  # κ=1/r か
# 桁違い比(0 割り防止に機械ゼロ floor。circ の中央値はそれより桁上なので floor は保険)
tau_ratio = med_tau_knot / max(med_tau_circ, 1e-15)

print(f"弧長 真値 L_gt(解析速度 台形積分 M={M})   : {L_gt:.9f}")
print(f"(a) 結び目 arc_length(N={N}) rel err       : {err_knot:.3e}  (粗 N=40 は {err_coarse:.3e})")
print(f"(a) 円     arc_length rel err               : {err_circ:.3e}")
print(f"(b) 結び目 中央|τ|                          : {med_tau_knot:.4f}  z 広がり {z_extent:.3f}(非平面)")
print(f"(b) 捩率 二方式一致(op vs Frenet–Serret)   : 中央相対 {tau_agree:.3e}")
print(f"    Frenet 標構: 単位性 {unit_err:.1e} / 直交 {ortho_err:.1e} / B=T×N {bxn_err:.1e}")
print(f"null 平面円: 中央|τ| {med_tau_circ:.2e}  κ=1/r 誤差 {kappa_err_circ:.1e}")
print(f"beat-null: 結び目/円 の中央|τ| 比          : {tau_ratio:.2e}  (桁違い)")

# ═══ GT 検証(解析真値・独立計算との tight tolerance。緩い assert は禁止)═══
# (a) 弧長: 密ポリラインは真値に相対 1e-5 未満で一致し、粗ポリラインは桁違いに外す
assert err_knot < 1e-5, f"結び目の弧長が真値と不一致: {err_knot:.3e}"
assert err_circ < 1e-5, f"円の弧長が真値と不一致: {err_circ:.3e}"
assert err_coarse > 100 * err_knot, f"粗ポリラインが密と同精度になってしまった: {err_coarse:.3e}"
# (b) 捩率: 結び目は非平面 ⇒ |τ| が実質的に非ゼロ、かつ二方式が独立に一致(真の幾何量)
assert med_tau_knot > 0.05, f"結び目の捩率が非平面と言えるほど大きくない: {med_tau_knot:.4f}"
assert z_extent > 1.0, f"結び目が平面的すぎる(z 広がり不足): {z_extent:.3f}"
assert tau_agree < 1e-3, f"捩率が op と Frenet–Serret で不一致(幾何量として疑わしい): {tau_agree:.3e}"
# Frenet 標構が直交正規で B=T×N(標構 op が正しい)
assert unit_err < 1e-5, f"Frenet 標構が単位ベクトルでない: {unit_err:.1e}"
assert ortho_err < 1e-5, f"Frenet 標構が直交でない: {ortho_err:.1e}"
assert bxn_err < 1e-9, f"B が T×N になっていない: {bxn_err:.1e}"
# beat-null: 平面円は捩率が機械ゼロ、しかし弧長と曲率は正確(op 自体は正しい)
assert med_tau_circ < 1e-6, f"平面円の捩率がゼロでない(null が壊れた): {med_tau_circ:.2e}"
assert kappa_err_circ < 1e-6, f"円の曲率が 1/r と不一致(op が壊れた): {kappa_err_circ:.1e}"
assert tau_ratio > 1e6, f"結び目の捩率が平面円を桁違いに上回らない: {tau_ratio:.2e}"

print(f"PASS: (2,3)トーラス結び目 弧長 rel {err_knot:.1e}(真値 {L_gt:.4f}, 粗 N=40 は {err_coarse:.1e})"
      f"・中央|τ| {med_tau_knot:.3f}(op↔Frenet–Serret 一致 {tau_agree:.1e})は平面円の {tau_ratio:.1e} 倍"
      f"(円は捩率 {med_tau_circ:.0e} だが κ=1/r 誤差 {kappa_err_circ:.0e}・弧長 rel {err_circ:.0e}で正確)")
