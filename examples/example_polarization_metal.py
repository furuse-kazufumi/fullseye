# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""偏光 4 方向の鏡面除去は、誘電体で効いて金属では効かない —— 残る量を閉形式で示す。

    py -3.11 examples/example_polarization_metal.py

【この例が解く問題】
`polarization_separate` は偏光板 4 方向の掃引を「無偏光 2·I_min」と「直線偏光
I_max − I_min」に**厳密に**分ける。それを拡散 / 鏡面と呼べるのは「鏡面反射が
完全直線偏光」のときだけで、それは誘電体の Brewster 角近傍の話。金属の鏡面は
部分偏光(偏光度 p < 1)なので、(1 − p)·S が **diffuse 側に残る**。この例は
その残りを Fresnel の閉形式から予測し、op の出力と一致させる = 限界を見せる例。

【グラウンドトゥルース】
鏡面の偏光度 p は s / p 偏光の反射率から p = (R_s − R_p) / (R_s + R_p)。
誘電体(n=1.5)は `fresnel_dielectric`、金属(アルミ相当 n=1.2, k=7.3、代表値)は
`fresnel_conductor` で出す。部分偏光の掃引 I(t) = 0.5·D + S·[(1−p)/2 + p·cos²(t−φ)]
は、代数的に polarization_render(D + (1−p)·S, p·S) と同じなので、op で描ける。
分離結果の diffuse は閉形式 D + (1−p)·S に一致するはず。

【この例が示すこと(数字は実行時の実測)】
1. 誘電体 @ Brewster 角: p = 1、残り 0(丸め誤差)。
2. 誘電体 @ 30°: p < 1 で、鏡面の一部が diffuse に残る(角度依存)。
3. 金属 @ 同じ角: p が 0.1 未満 —— 鏡面の 9 割以上が diffuse に残り「除けていない」。
4. DoLP 地図は p·S/(D+S) に一致 —— 偏光板を付ける価値の判定はここで先に分かる。
5. どの場合も op の出力は閉形式と 1e-12 以内で一致する = 道具は正しい、仮定が違う。

EXTEND: 実機なら `fresnel_conductor` の n, k を材料の値(波長依存)に、
角度は照明とカメラの幾何から。p が 0.5 を切る材料では色の経路
(`specular_diffuse_split`)を併用する。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fullseye as fs  # noqa: E402

ANGLES = (0.0, 45.0, 90.0, 135.0)
AZIMUTH = 30.0
H, W = 48, 64


def scene():
    """拡散 D(テクスチャ)と鏡面 S(中央のハイライト)。"""
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    d = 0.25 + 0.15 * np.sin(xx / 6.0) * np.cos(yy / 5.0) + 0.15
    s = 0.6 * np.exp(-((yy - H / 2) ** 2 + (xx - W / 2) ** 2) / (2 * 6.0 ** 2))
    return d, s


def dop(rs: float, rp: float) -> float:
    return (rs - rp) / (rs + rp)


def main() -> None:
    d, s = scene()
    n_glass = 1.5
    brewster = fs.ledger.brewster_angle_deg(1.0, n_glass)
    cases = []
    for label, theta in (("誘電体 n=1.5 @ Brewster", brewster), ("誘電体 n=1.5 @ 30°", 30.0),
                         ("金属 Al(n=1.2, k=7.3) @ Brewster(誘電体の)", brewster), ("金属 Al @ 30°", 30.0)):
        ci = float(np.cos(np.deg2rad(theta)))
        if label.startswith("誘電体"):
            rs = float(fs.ledger.fresnel_dielectric(ci, 1.0, n_glass, "s"))
            rp = float(fs.ledger.fresnel_dielectric(ci, 1.0, n_glass, "p"))
        else:
            rs = float(fs.ledger.fresnel_conductor(ci, 1.2, 7.3, "s"))
            rp = float(fs.ledger.fresnel_conductor(ci, 1.2, 7.3, "p"))
        p = dop(rs, rp)
        # 部分偏光の掃引 = polarization_render(D + (1-p) S, p S)(代数的に同じ)
        frames = fs.ledger.polarization_render(d + (1 - p) * s, p * s, ANGLES, azimuth_deg=AZIMUTH)
        diffuse, specular = fs.ledger.polarization_separate.raw(frames, ANGLES)
        leak = diffuse - d                                  # 「拡散」に残った鏡面
        leak_closed = (1 - p) * s
        dolp = np.asarray(fs.ledger.polarization_dolp_map(frames, ANGLES))
        dolp_closed = p * s / (d + s)
        cases.append((label, theta, rs, rp, p, float(np.abs(leak - leak_closed).max()),
                      float(leak.max() / s.max()), float(np.abs(dolp - dolp_closed).max())))

    print("=== 偏光 4 方向の鏡面除去: 残る鏡面 (1-p)·S を閉形式と突き合わせる")
    print("| 場面 | θ [deg] | R_s | R_p | 偏光度 p | 残り/鏡面 (1-p) | op − 閉形式 (max) | DoLP − 閉形式 |")
    print("|---|---|---|---|---|---|---|---|")
    for label, theta, rs, rp, p, err, frac, derr in cases:
        print(f"| {label} | {theta:.1f} | {rs:.4f} | {rp:.4f} | {p:.4f} | {frac:.3f} | {err:.1e} | {derr:.1e} |")

    # 主張を固定する
    diel_b, diel_30, met_b, met_30 = cases
    assert abs(diel_b[4] - 1.0) < 1e-12 and diel_b[6] < 1e-12, diel_b       # Brewster: p=1、残り 0
    assert 0.3 < diel_30[4] < 1.0, diel_30                                   # 30°: 一部残る
    assert met_b[4] < 0.1 and met_30[4] < 0.1, (met_b[4], met_30[4])          # 金属: p < 0.1
    assert met_b[6] > 0.9, met_b                                              # 9 割以上が残る
    assert all(c[5] < 1e-12 and c[7] < 1e-12 for c in cases), cases           # op = 閉形式
    print()
    print(f"Brewster 角(n=1.5)= {brewster:.2f} deg。金属では鏡面の {met_b[6] * 100:.1f} % が「拡散」に残る —— "
          "道具は厳密で、外れているのは『鏡面 = 完全偏光』の仮定。金属は色の経路(specular_diffuse_split)を併用。")
    print("PASS")


if __name__ == "__main__":
    main()
