# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""itokawa_curvature — 小惑星表面の曲率解析(尾根・クレーターの検出)。

【この例が解く現実問題】
小惑星の表面は一様ではない。鋭い尾根・ボルダー(巨礫)の縁・クレーターの縁は曲率が大きく、
平坦な地形や大きな滑らかな面は曲率が小さい。各点の **主曲率(k1,k2)/曲率強度(curvedness)** を
点群から局所二次曲面フィットで求めれば、着陸地点の選定(平坦=安全)、地質構造の抽出、
形状異常の検出に使える。曲率分布が「自明でない(平坦一色でない)」ことこそ実在天体の証拠である。

【方法とグラウンドトゥルース】
curvature3d は各点で局所 Monge パッチ w=f(u,v) を最小二乗フィットし、基本形式から主曲率を出す。
半径 R の球なら k1=k2=1/R、curvedness=1/R になる。まずこの GT を合成球で確認してから、
イトカワ実データへ適用し、曲率分布が実質的にばらつく(std>0)こと、高曲率(尾根/縁)と
低曲率(平坦)の点が両方存在することを assert する。

対象データ: studio_assets/sample_3d/itokawa_points.npy(実測イトカワ点群, ~3000 点)。
使う op: curvature3d.principal_curvatures / curvedness / shape_index。
"""
import sys
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import curvature3d  # principal_curvatures / curvedness / shape_index(局所二次曲面フィット)

DATA = _REPO / "studio_assets" / "sample_3d" / "itokawa_points.npy"


def main():
    rng = np.random.default_rng(0)

    # --- グラウンドトゥルース: 半径 R の球は curvedness = 1/R ---
    R = 100.0
    u = rng.normal(size=(3000, 3))
    u /= np.linalg.norm(u, axis=1, keepdims=True)
    sphere = u * R
    cv_sphere = curvature3d.curvedness(sphere, k=25)
    gt = 1.0 / R
    med_sphere = float(np.median(cv_sphere))
    print("=== グラウンドトゥルース(半径 100 m の球) ===")
    print(f"理論 curvedness 1/R = {gt:.5f}")
    print(f"実測 curvedness 中央値 = {med_sphere:.5f}(相対誤差 "
          f"{abs(med_sphere - gt) / gt * 100:.1f}%)")
    assert abs(med_sphere - gt) / gt < 0.15, \
        f"球の曲率が理論値と合わない: {med_sphere:.5f} vs {gt:.5f}"

    # --- イトカワ実データの曲率 ---
    pts = np.load(DATA).astype(np.float64)
    pts = pts - pts.mean(axis=0)
    k1, k2 = curvature3d.principal_curvatures(pts, k=20)
    cv = curvature3d.curvedness(pts, k=20)          # 曲がりの強さ(符号不問)
    si = curvature3d.shape_index(pts, k=20)         # 形状の種類(-1 凹球 .. +1 凸球)

    cv_mean = float(np.mean(cv))
    cv_std = float(np.std(cv))
    cv_med = float(np.median(cv))
    print("\n=== イトカワ表面の曲率分布 ===")
    print(f"curvedness  平均 {cv_mean:.5f} / 標準偏差 {cv_std:.5f} / 中央値 {cv_med:.5f}")
    print(f"主曲率 k1   範囲 [{k1.min():.5f}, {k1.max():.5f}]")
    print(f"主曲率 k2   範囲 [{k2.min():.5f}, {k2.max():.5f}]")
    print(f"shape_index 範囲 [{si.min():.3f}, {si.max():.3f}] / 標準偏差 {np.std(si):.3f}")

    # 高曲率(尾根・縁)と低曲率(平坦)の割合
    high_frac = float(np.mean(cv > 1.5 * cv_med))   # 中央値の 1.5 倍超 = 尾根/クレーター縁
    low_frac = float(np.mean(cv < 0.5 * cv_med))    # 中央値の半分未満 = 滑らかな地形
    print(f"高曲率(>1.5x中央値)の割合 = {high_frac * 100:.1f}%(尾根/巨礫縁/クレーター縁)")
    print(f"低曲率(<0.5x中央値)の割合 = {low_frac * 100:.1f}%(滑らかな地形)")

    # --- 検証: 曲率分布が自明でない ---
    assert cv_std > 0.0, "曲率が一定(平坦一色)= 実在天体らしくない"
    assert cv_std > 0.2 * cv_mean, \
        f"曲率のばらつきが小さすぎる: std/mean = {cv_std / cv_mean:.2f}"
    assert high_frac > 0.0 and low_frac > 0.0, \
        f"高曲率/低曲率のどちらかが存在しない: high={high_frac}, low={low_frac}"

    # shape_index に凸(尾根/丘)も凹(窪み)も現れる(非自明な地形)
    convex_frac = float(np.mean(si > 0.3))
    concave_frac = float(np.mean(si < -0.1))
    print(f"凸地形(shape_index>0.3)= {convex_frac * 100:.1f}% / "
          f"凹地形(shape_index<-0.1)= {concave_frac * 100:.1f}%")
    assert convex_frac > 0.0, "凸地形が検出されない"

    # --- 検証の核心: 曲率が「実在表面の幾何」であることの判別(乱数を弾く) ---
    # 実在天体の表面では、近い点どうしの曲率は相関する(曲率は面上で滑らかに変化する)。
    # もし曲率値が実体のないランダム値なら、この近傍相関はほぼ 0 になる。
    # 「ばらつきがある/高低が両方ある」だけの検査は乱数でも満たせてしまうため、
    # ここで空間的一貫性を要求して本物の地形であることを担保する。
    from scipy.spatial import cKDTree
    tree = cKDTree(pts)
    _, idx = tree.query(pts, k=6)                     # 自身 + 近傍 5 点
    neigh_mean = cv[idx[:, 1:]].mean(axis=1)          # 近傍の曲率度の平均
    coh = float(np.corrcoef(cv, neigh_mean)[0, 1])    # 点の曲率 vs 近傍平均の相関
    print(f"曲率の空間的一貫性(近傍相関)= {coh:.3f} "
          f"(実在表面なら高い / ランダム値なら ~0)")
    assert coh > 0.3, \
        f"曲率が空間的に一貫していない(実体のないランダム値の疑い): r={coh:.3f}"

    print("\nPASS: イトカワ表面の曲率は近傍で空間的に一貫し(相関 "
          f"{coh:.2f})、高曲率(尾根/縁)と低曲率(平坦)が共存する実在の地形分布を持つ。"
          "曲率法自体は球の GT(1/R)で検証済み。")


if __name__ == "__main__":
    main()
