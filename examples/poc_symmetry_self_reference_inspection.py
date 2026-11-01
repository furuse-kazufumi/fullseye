# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""2-D 対称性による自己参照検査 ―― 正解画像なしで欠陥だけを残す。

合成部品へ対称な模様、線形照明むら、非対称欠陥を別々の式で植え、次の独立な量を
検査する。(a) 鏡映差分の欠陥領域 / 模様領域の残差比、(b) 欠けた円板でのエッジ対中心
と面積重心の真値誤差、(c) n=2,3,4,6 の回転次数を雑音・ぼけで振った正答率、(d) 欠陥
振幅に対する対称性スコアの単調性。絵がもっともらしいことは合否に使わない。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import examplefig as figs
import fullseye as fs


def _centroid(region):
    yy, xx = np.indices(region.shape)
    mass = float(np.sum(region))
    return np.array([np.sum(region * yy) / mass, np.sum(region * xx) / mass])


def inspection_scene(amplitude=0.30):
    n = 161
    yy, xx = np.indices((n, n))
    c = 80.0
    part = (yy - c) ** 2 + (xx - c) ** 2 < 55.0 ** 2
    pattern = 0.50 + 0.12 * np.cos((xx - c) * 0.45) + 0.10 * np.cos((yy - c) * 0.31)
    illumination = 0.18 * (xx / (n - 1) - 0.5) + 0.08 * (yy / (n - 1) - 0.5)
    base = np.where(part, pattern + illumination, 0.0)
    defect = (yy - 62.0) ** 2 + (xx - 111.0) ** 2 < 5.0 ** 2
    twin = (yy - 62.0) ** 2 + (xx - 49.0) ** 2 < 7.0 ** 2
    image = base.copy()
    image[defect] += amplitude
    model = {"kind": "reflection", "angle_deg": 90.0, "offset_px": 0.0}
    return base, image, part, defect, twin, model


def rotor(order, noise, blur, seed):
    n = 161
    yy, xx = np.indices((n, n))
    center = np.array([80.2, 79.7])
    dy, dx = yy - center[0], xx - center[1]
    radius, theta = np.hypot(dy, dx), np.arctan2(dy, dx)
    boundary = 42.0 * (1.0 + 0.17 * np.cos(order * theta))
    image = gaussian_filter((radius <= boundary).astype(float), blur)
    image = np.clip(image + np.random.default_rng(seed).normal(0.0, noise, image.shape), 0.0, 1.0)
    return image


def main():
    print("=== A. 自己参照差分: 模様 + 照明むら + 欠陥 ===")
    base, image, part, defect, twin, model = inspection_scene()
    diff = fs.symmetry_difference_map(image, model, detrend=True)
    defect_mean = float(np.mean(diff[defect | twin]))
    pattern_mean = float(np.mean(diff[part & ~(defect | twin)]))
    residual_ratio = defect_mean / max(pattern_mean, 1e-15)
    print(f"欠陥と鏡像位置の平均残差 : {defect_mean:.12f}")
    print(f"模様・照明領域の平均残差 : {pattern_mean:.3e}")
    print(f"欠陥 / 模様・照明の残差比: {residual_ratio:.3e}")
    figs.save_grid(
        "self_reference_defect",
        [base, image, diff],
        ["対称模様 + 線形照明", "非対称欠陥を追加", "鏡映差分(一次面除去)"],
        title="正解画像を使わず、部品自身の鏡像との差を取る",
        ncols=3, gray=[True, True, False], colorbar=[False, False, True],
        caption=(f"欠陥領域の平均残差 {defect_mean:.3f}、模様・照明領域 {pattern_mean:.1e}。"
                 f"比 {residual_ratio:.1e} で欠陥だけが残る。"),
    )

    print("\n=== B. 中心: 欠けに強いエッジ対 vs 欠け無しに強い重心 ===")
    n = 161
    yy, xx = np.indices((n, n))
    truth = np.array([80.23, 79.20])
    clean = (np.hypot(yy - truth[0], xx - truth[1]) <= 48.0).astype(float)
    bite = (yy - truth[0]) ** 2 + (xx - (truth[1] + 42.0)) ** 2 < 16.0 ** 2
    bitten = clean.copy()
    bitten[bite] = 0.0
    edge_clean = np.asarray(fs.center_from_symmetric_edges(clean)["center"])
    edge_bite = np.asarray(fs.center_from_symmetric_edges(bitten)["center"])
    center_rows = []
    center_values = {}
    for condition, region, edge in (("欠け無し", clean, edge_clean), ("片側を欠く", bitten, edge_bite)):
        e_edge = float(np.linalg.norm(edge - truth))
        e_cent = float(np.linalg.norm(_centroid(region) - truth))
        center_values[condition] = (e_edge, e_cent)
        center_rows.append([condition, f"{e_edge:.3f}", f"{e_cent:.3f}"])
        print(f"{condition:8s}  エッジ対 {e_edge:.3f} px / 面積重心 {e_cent:.3f} px")
    figs.save_table(
        "center_tradeoff", ["条件", "エッジ対中心 [px]", "面積重心 [px]"], center_rows,
        title="中心の真値誤差: 頑健さと無擾乱精度の交換",
        caption=("片側欠けではエッジ対中心 0.231 px、面積重心 3.171 px。"
                 "欠け無しでは重心 0.041 px がエッジ対 0.305 px より精密。"),
    )

    print("\n=== C. 回転次数: 雑音・ぼけを振る ===")
    orders = (2, 3, 4, 6)
    conditions = ((0.0, 0.7), (0.01, 1.4), (0.025, 2.0))
    series = [("真値", orders, orders)]
    correct = 0
    estimates = []
    for noise, blur in conditions:
        got = []
        for order in orders:
            out = fs.rotational_symmetry(rotor(order, noise, blur, order + int(100 * noise)),
                                         max_order=8, score_threshold=0.18)
            got.append(out["order"])
            correct += int(out["order"] == order)
        estimates.append(got)
        label = f"noise={noise:.3f}, blur={blur:.1f}"
        series.append((label, orders, got))
        print(f"{label:24s}: 真値 {orders} -> 推定 {tuple(got)}")
    accuracy = correct / (len(orders) * len(conditions))
    print(f"正答率: {correct}/{len(orders) * len(conditions)} = {accuracy:.1%}")
    figs.save_plot(
        "rotational_order_noise", series, xlabel="真の回転次数 n", ylabel="推定次数",
        title="極座標自己相関の次数推定", xlim=(1.5, 6.5), ylim=(1.5, 6.5),
        styles=["dashed", None, None, None], colors=["reference", "emphasis", "right", "neutral"],
        caption=f"n=2,3,4,6 × 3 条件の正答率 {correct}/{len(orders) * len(conditions)}。",
    )

    print("\n=== D. 対称性スコアの単調性 ===")
    amplitudes = np.array([0.0, 0.1, 0.2, 0.3, 0.4])
    scores = []
    for amplitude in amplitudes:
        _, disturbed, _, _, _, model = inspection_scene(float(amplitude))
        scores.append(fs.symmetry_score(disturbed, model, detrend=True))
    scores = np.asarray(scores)
    print("欠陥振幅:", " ".join(f"{x:.1f}" for x in amplitudes))
    print("score   :", " ".join(f"{x:.9f}" for x in scores))
    print("隣接差  :", " ".join(f"{x:.9f}" for x in np.diff(scores)))
    figs.save_plot(
        "symmetry_score_monotone", [("対称からの距離", amplitudes, scores)],
        xlabel="欠陥振幅", ylabel="symmetry_score", title="乱れを増すとスコアは単調増加",
        colors=["emphasis"], caption="5 段階すべてで隣接差が正。軸モデルは固定して比較した。",
    )

    # Pictures are illustrative; these independent quantities decide PASS.
    assert defect_mean > 0.18 and pattern_mean < 1e-10 and residual_ratio > 1e8
    assert 0.1 <= center_values["片側を欠く"][0] <= 0.3
    assert 3.0 <= center_values["片側を欠く"][1] <= 3.4
    assert center_values["欠け無し"][1] < center_values["欠け無し"][0]
    assert accuracy == 1.0
    assert np.all(np.diff(scores) > 0.0)
    if figs.errors():
        raise RuntimeError("図の書き出しに失敗: " + "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
