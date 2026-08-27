# 真球度/丸さ検査 — pipeline3d.inspect_roundness
# 実問題: 工業計測で「ボール/球状部品がどれだけ真球に近いか」を点群から数値評価する。
# 完全な球ほど半径のばらつき(真球度偏差)は小さく、へこみ(打痕)があると偏差が増える。
import numpy as np
import pipeline3d as P


def fibonacci_sphere(n, center, radius):
    """乱数を使わず球面をほぼ一様に覆う点群(Fibonacci 格子)。再現性のため決定論的。"""
    i = np.arange(n) + 0.5
    phi = np.arccos(1.0 - 2.0 * i / n)          # 極角(z 方向): 面積一様
    theta = np.pi * (1.0 + 5.0 ** 0.5) * i      # 黄金角で方位を回す
    dirs = np.stack([np.sin(phi) * np.cos(theta),
                     np.sin(phi) * np.sin(theta),
                     np.cos(phi)], axis=1)       # 単位方向ベクトル (n,3)
    return np.asarray(center) + radius * dirs, dirs


CENTER = np.array([2.0, 3.0, 4.0])
R = 5.0
N = 1200

# ケースA: ほぼ完全な球(理想部品)
pts_perfect, dirs = fibonacci_sphere(N, CENTER, R)

# ケースB: 同じ球に「既知のへこみ」を入れる(打痕のある部品)。
# +x 方向のパッチ(方向ベクトルが x 軸と近い点)を中心へ向けて DENT だけ押し込む。
DENT = 0.30                                       # へこみ深さ(既知の GT)
pts_dented = pts_perfect.copy()
mask = dirs[:, 0] > 0.85                          # +x 極付近のパッチだけ選ぶ
pts_dented[mask] = CENTER + (R - DENT) * dirs[mask]
n_dent = int(mask.sum())

# --- 検査を実行 ---
res_perfect = P.inspect_roundness(pts_perfect)
res_dented = P.inspect_roundness(pts_dented)

print(f"[perfect] radius={res_perfect['radius']:.6f} "
      f"roundness_pv={res_perfect['roundness_pv']:.6e} rms={res_perfect['rms']:.6e}")
print(f"[dented ] radius={res_dented['radius']:.6f} "
      f"roundness_pv={res_dented['roundness_pv']:.6e} rms={res_dented['rms']:.6e}  "
      f"(dent depth={DENT}, {n_dent} pts)")

# --- GT 検証(視覚でなく数値) ---
# 1) フィット半径は真値 5.0 を高精度で復元(代数フィットは完全球で厳密)
assert abs(res_perfect['radius'] - R) < 1e-6, res_perfect['radius']
# 2) 完全な球ほど偏差が小さい: 完全球の真球度偏差 ≈ 0(浮動小数点誤差レベル)
assert res_perfect['roundness_pv'] < 1e-6, res_perfect['roundness_pv']
assert res_perfect['rms'] < 1e-6, res_perfect['rms']
# 3) へこみがあると偏差は明確に増大し、PV は概ねへこみ深さのオーダー
assert res_dented['roundness_pv'] > res_perfect['roundness_pv'], "dent must raise PV"
assert res_dented['rms'] > res_perfect['rms'], "dent must raise RMS"
# 4) PV はへこみ深さ DENT に近い(0.7*DENT < PV < 1.3*DENT。多数点が R 上なのでフィット半径は
#    僅かに縮むだけ = PV はへこみ深さ ± 数% に収まる)
assert 0.7 * DENT < res_dented['roundness_pv'] < 1.3 * DENT, res_dented['roundness_pv']

# sphericity(真球度): 半径に対する PV 偏差の比。0 に近いほど真球。
sph_perfect = res_perfect['roundness_pv'] / res_perfect['radius']
sph_dented = res_dented['roundness_pv'] / res_dented['radius']
print(f"sphericity(pv/R): perfect={sph_perfect:.3e}  dented={sph_dented:.3e}")
assert sph_perfect < sph_dented
print("OK: 完全な球ほど真球度偏差が小さい (perfect < dented) を数値で確認")