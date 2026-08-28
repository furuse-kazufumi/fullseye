# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: 3D点群の鏡映対称面(ミラー平面)を自動復元する (shape_analysis).

工業検査・形状補完・姿勢正準化では「この形はどの平面で左右対称か」を知りたい。左右差は
欠陥のサインになり、対称面が分かれば欠損側を鏡映で埋められる。ここでは **既知の平面** で
厳密に鏡映対称な点群(ランダムな半分を作り、平面で鏡映してもう半分を生成)を合成し、
symmetry3d.detect_reflection_symmetry(重心を通る PCA 主軸を候補法線に採点)で
その平面を初期推定なしに復元する。数学的裏付け: 鏡映対称な集合の共分散は鏡映行列と
可換になるため、真の法線は必ず共分散の固有ベクトル(=PCA 主軸)になる。

【指標の向き — 誤解しないよう明記】symmetry3d の生スコアは「鏡映残差 =
chamfer(鏡映, 元)/中央値点間隔」で、**小さいほど対称**(0=完全対称)。よって「対称ほど
高スコア」ではなく「対称ほど低スコア」である点に注意。

検証(GT): (1) 復元した法線と真の法線の角度差 < 1度(符号の反転を許容)。真の法線は
共分散の固有ベクトルなので厳密に一致するはず。(2) 対称点群の残差は ~0(< 0.01 点間隔)。
(3) beat-null: 非対称点群(乱数 + 片側のこぶ)は検出器が 3 主軸から最良を選んでも残差が桁違いに
大きい。さらに、対称点群でも法線を乱数(でたらめな平面)にすると残差が跳ね上がる — つまり
復元した平面だけが特別に低残差であることを示し、緩い assert では通らない判別性を担保する。
"""
import sys
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import symmetry3d  # detect_reflection_symmetry / reflection_symmetry_score / reflect_points


def plane_basis(n):
    """法線 n に直交する平面内の正規直交基底 (u, v) を返す。"""
    n = np.asarray(n, float)
    n = n / np.linalg.norm(n)
    seed = np.array([1.0, 0.0, 0.0]) if abs(n[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    u = seed - (seed @ n) * n
    u /= np.linalg.norm(u)
    v = np.cross(n, u)
    return u, v


def normal_angle_deg(a, b):
    """2つの法線の角度差(度)。鏡映面の法線は向き(符号)が不定なので絶対値で畳む。"""
    a = np.asarray(a, float) / np.linalg.norm(a)
    b = np.asarray(b, float) / np.linalg.norm(b)
    return float(np.degrees(np.arccos(np.clip(abs(a @ b), 0.0, 1.0))))


def make_mirror_symmetric(n_true, n_half=1500, seed=7):
    """既知の平面(原点通過・法線 n_true)で厳密に鏡映対称な点群を作る。

    平面内で異方的(3方向でスケールを変える)に半分を作り、reflect_points で鏡映コピーを
    足す。異方性を持たせるのは共分散の3固有値を明確に分離するためで、これにより真の法線が
    PCA 主軸として一意に取り出せる(等方だと固有値が縮退し主軸が定まらない)。
    """
    u, v = plane_basis(n_true)
    n = np.asarray(n_true, float) / np.linalg.norm(n_true)
    rng = np.random.default_rng(seed)
    a = np.abs(rng.normal(0.0, 1.0, n_half))    # 法線方向は正側のみ(=平面の片側)
    b = rng.normal(0.0, 3.0, n_half)            # 面内 u: 大きなスケール
    c = rng.normal(0.0, 2.0, n_half)            # 面内 v: 中スケール(3方向すべて異なる)
    half = a[:, None] * n + b[:, None] * u + c[:, None] * v
    mirror = symmetry3d.reflect_points(half, np.zeros(3), n)   # 実 op で鏡映してもう半分
    return np.vstack([half, mirror])


def make_asymmetric(n_pts=1500, seed=13):
    """明確に非対称な点群(異方ガウス + 片側のこぶ)。どの平面でも左右が揃わない null。"""
    rng = np.random.default_rng(seed)
    blob = rng.normal(0.0, 1.0, (n_pts, 3)) * np.array([3.0, 2.0, 1.0])
    lump = rng.normal(np.array([6.0, 0.0, 0.0]), 0.5, (n_pts // 4, 3))  # +x だけに塊
    return np.vstack([blob, lump])


# --- 1) 既知の平面で対称点群を合成し、平面を復元 -----------------------------
n_true = np.array([0.4, -0.7, 0.6])
n_true = n_true / np.linalg.norm(n_true)                  # 真の対称面法線(軸非整列)
sym = make_mirror_symmetric(n_true)

res = symmetry3d.detect_reflection_symmetry(sym)
n_rec = res["plane_normal"]
sym_score = res["score"]                                   # 鏡映残差(小さいほど対称)
angle = normal_angle_deg(n_rec, n_true)

print(f"真の法線                  : [{n_true[0]:.3f} {n_true[1]:.3f} {n_true[2]:.3f}]")
print(f"復元法線                  : [{n_rec[0]:.3f} {n_rec[1]:.3f} {n_rec[2]:.3f}]")
print(f"法線の角度差 (度)         : {angle:.4f}")
print(f"対称点群の残差 (best)     : {sym_score:.3e}  (3主軸: "
      f"{[f'{s:.2e}' for s in res['all_scores']]})")

# --- 2) null-A: 非対称点群は検出器が最良を選んでも残差が桁違いに大きい --------
asym = make_asymmetric()
res_asym = symmetry3d.detect_reflection_symmetry(asym)
asym_score = res_asym["score"]
print(f"非対称点群の残差 (best)   : {asym_score:.3e}  (3主軸: "
      f"{[f'{s:.2e}' for s in res_asym['all_scores']]})")

# --- 3) null-B: 対称点群でも法線を乱数にすると残差が跳ね上がる(平面の特別さ)--
rng = np.random.default_rng(99)
c_sym = sym.mean(axis=0)
rand_scores = []
for _ in range(8):
    g = rng.normal(size=3)
    rand_scores.append(symmetry3d.reflection_symmetry_score(sym, c_sym, g))
rand_min = float(min(rand_scores))            # でたらめ平面の中でも最良の残差
print(f"でたらめ平面の残差 (最良) : {rand_min:.3e}  (乱数法線8本の min)")

# --- 4) GT検証 ---------------------------------------------------------------
# (1) 真の法線は共分散の固有ベクトルなので、復元法線はほぼ厳密に一致する。
assert angle < 1.0, f"復元した対称面法線が真の法線とずれている: {angle:.4f} 度"
# (2) 厳密対称なら鏡映残差はほぼ 0(点間隔の 1% 未満)。
assert sym_score < 1e-2, f"対称点群の残差が大きすぎる(対称面が復元できていない): {sym_score:.3e}"
# (3) beat-null-A: 非対称点群は対称点群より桁違いに残差が大きい。
assert asym_score > 100.0 * max(sym_score, 1e-9), \
    f"非対称点群の残差が対称点群と識別できない: 非対称={asym_score:.3e} 対称={sym_score:.3e}"
assert asym_score > 0.3, f"非対称 null の残差が絶対値でも小さすぎる: {asym_score:.3e}"
# (4) beat-null-B: 復元した平面はでたらめ平面より桁違いに低残差。
assert rand_min > 100.0 * max(sym_score, 1e-9), \
    f"でたらめ平面と復元平面が識別できない: でたらめ最良={rand_min:.3e} 復元={sym_score:.3e}"

ratio = asym_score / max(sym_score, 1e-12)
print(f"PASS: 鏡映対称面を法線誤差 {angle:.4f}度・残差 {sym_score:.2e} で復元。"
      f"非対称 null 残差 {asym_score:.2e} は {ratio:.1e} 倍大きく、"
      f"でたらめ平面(最良 {rand_min:.2e})も桁違い — 対称面の復元は判別的。")
