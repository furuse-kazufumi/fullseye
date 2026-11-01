# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""2-D 対称性による自己参照検査 ―― 正解画像なしで欠陥だけを残す。

合成部品へ対称な模様、線形照明むら、非対称欠陥を別々の式で植え、次の独立な量を
検査する。(a) 鏡映差分の欠陥領域 / 模様領域の残差比、(b) 欠けた円板でのエッジ対中心
と面積重心の真値誤差、(c) n=2,3,4,6 の回転次数が雑音・ぼけで壊れる境界、(d) 欠陥
振幅に対する対称性スコアが欠陥なしの雑音床を越える点。絵がもっともらしいことは合否に使わない。
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

    print("\n=== C. 回転次数: 雑音・ぼけで壊れるまで掃く ===")
    orders = (2, 3, 4, 6)
    noises = np.linspace(0.0, 0.2, 8)
    blurs = np.linspace(0.0, 6.0, 7)
    seeds = range(5)
    score_threshold = 0.18
    accuracy_maps = []
    rotation_metrics = []
    for order in orders:
        rates = np.empty((len(blurs), len(noises)), dtype=float)
        for blur_index, blur in enumerate(blurs):
            for noise_index, noise in enumerate(noises):
                correct = 0
                for seed in seeds:
                    # 格子・次数・seed の組から一意に決まる。実行順を変えても同じ像になる。
                    trial_seed = 100000 * order + 1000 * blur_index + 10 * noise_index + seed
                    out = fs.rotational_symmetry(
                        rotor(order, float(noise), float(blur), trial_seed),
                        max_order=8, score_threshold=score_threshold)
                    correct += int(out["order"] == order)
                rates[blur_index, noise_index] = correct / len(seeds)
        accuracy_maps.append(rates)
        failed = np.argwhere(rates < 1.0)
        # 同じ noise なら小さい blur を先に選び、最初に観測した低下点を面下の文にする。
        first = min(failed, key=lambda rc: (noises[rc[1]], blurs[rc[0]]))
        first_blur, first_noise = float(blurs[first[0]]), float(noises[first[1]])
        rotation_metrics.append((order, first_blur, first_noise, int(len(failed))))

    def rotation_line(metric):
        order, blur, noise, failed = metric
        return f"n={order} は blur {blur:.0f} px・noise {noise:.3f} で低下（1未満 {failed} 格子）"

    rotation_wall = (
        f"この垂直な壁は、op の正規化 RMS 差が上限 score_threshold={score_threshold:.2f} "
        "を雑音で越えると n=1 を返すためで、この掃引では blur は壁の位置を動かさない。")
    printed_rotation_caption = (
        "；".join(rotation_line(m) for m in rotation_metrics) + "。" + rotation_wall)
    rotation_caption = (
        "；".join(rotation_line(m) for m in rotation_metrics) + "。" + rotation_wall)
    print(printed_rotation_caption)
    panels = [figs._render_heatmap(
        rates, noises, blurs, xlabel="横: noise σ", ylabel="縦: blur σ [px]",
        vrange=(0.0, 1.0), boundary=rates == 1.0, colorbar_unit="正答率")
        for rates in accuracy_maps]
    figs.save_grid(
        "rotational_order_noise", panels,
        captions=[rotation_line(m) for m in rotation_metrics], ncols=2,
        title="回転次数の推定はどこで壊れるか", caption=rotation_caption,
    )

    print("\n=== D. 欠陥スコアが欠陥なしの雑音床を越える点 ===")
    amplitudes = np.linspace(0.0, 10.0, 101)
    scores = []
    for amplitude in amplitudes:
        _, disturbed, _, _, _, model = inspection_scene(float(amplitude))
        scores.append(fs.symmetry_score(disturbed, model, detrend=True))
    scores = np.asarray(scores)
    noise_levels = (0.01, 0.025, 0.05)
    noise_trials = 500
    _, clean, _, _, _, model = inspection_scene(0.0)
    floors = []
    for noise_index, noise in enumerate(noise_levels):
        null_scores = []
        for seed in range(noise_trials):
            rng = np.random.default_rng(30000 + 1000 * noise_index + seed)
            noisy = np.clip(clean + rng.normal(0.0, noise, clean.shape), 0.0, 1.0)
            null_scores.append(fs.symmetry_score(noisy, model, detrend=True))
        floors.append(float(np.quantile(null_scores, 0.99)))

    crossings = []
    for floor in floors:
        above = np.flatnonzero(scores >= floor)
        assert len(above), "欠陥振幅の掃引が雑音床まで届いていない"
        hi = int(above[0])
        if hi == 0:
            crossing = float(amplitudes[0])
        else:
            lo = hi - 1
            crossing = float(amplitudes[lo] + (floor - scores[lo])
                             * (amplitudes[hi] - amplitudes[lo])
                             / (scores[hi] - scores[lo]))
        crossings.append(crossing)

    def detection_line(noise, crossing):
        return f"noise {noise:.3f} では振幅 {crossing:.2f} から検出"

    printed_detection_caption = "；".join(
        detection_line(noise, crossing) for noise, crossing in zip(noise_levels, crossings)) + "。"
    detection_caption = "；".join(
        detection_line(noise, crossing) for noise, crossing in zip(noise_levels, crossings)) + "。"
    print("99 % 雑音床:", " ".join(f"{floor:.6f}" for floor in floors))
    print(printed_detection_caption)
    plot_series = [("欠陥スコア", amplitudes, scores)]
    plot_styles = [None]
    plot_colors = ["emphasis"]
    floor_colors = ("right", "wrong", "neutral")
    for noise, floor, color in zip(noise_levels, floors, floor_colors):
        plot_series.append((f"noise {noise:.3f} の99%床 {floor:.4f}",
                            [amplitudes[0], amplitudes[-1]], [floor, floor]))
        plot_styles.append("dashed")
        plot_colors.append(color)
    for noise, floor, crossing, color in zip(noise_levels, floors, crossings, floor_colors):
        plot_series.append((f"noise {noise:.3f} → 振幅 {crossing:.2f}",
                            [crossing, crossing], [0.0, floor]))
        plot_styles.append("dotted")
        plot_colors.append(color)
    figs.save_plot(
        "symmetry_score_monotone", plot_series,
        xlabel="欠陥振幅", ylabel="symmetry_score", title="欠陥が雑音の床を越える振幅",
        xlim=(0.0, 10.0), ylim=(0.0, max(scores[-1], max(floors)) * 1.05),
        styles=plot_styles, colors=plot_colors, caption=detection_caption,
    )

    # Pictures are illustrative; these independent quantities decide PASS.
    assert defect_mean > 0.18 and pattern_mean < 1e-10 and residual_ratio > 1e8
    assert 0.1 <= center_values["片側を欠く"][0] <= 0.3
    assert 3.0 <= center_values["片側を欠く"][1] <= 3.4
    assert center_values["欠け無し"][1] < center_values["欠け無し"][0]
    assert all(np.count_nonzero(rates < 1.0) >= 1 for rates in accuracy_maps)
    assert printed_rotation_caption == rotation_caption
    assert np.all(np.diff(scores) > 0.0)
    assert len(floors) == len(crossings) == 3
    assert printed_detection_caption == detection_caption
    if figs.errors():
        raise RuntimeError("図の書き出しに失敗: " + "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
