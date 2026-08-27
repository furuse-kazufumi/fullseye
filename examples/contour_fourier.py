# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""contour_fourier — 閉輪郭の楕円フーリエ記述子(EFD)で形状を表現・平滑化・照合する。

    py -3.11 examples/contour_fourier.py            # GT検証(数値)だけ
    py -3.11 examples/contour_fourier.py --save out.png  # 図も保存(matplotlib)

【この例が解く問題】
輪郭(部品の外形・細胞・文字など)を少数のフーリエ係数で表したい。用途は
(1) 高調波を打ち切って **平滑化/簡約**、(2) 回転・スケール・始点・平行移動に
**不変** な記述子で **形状照合/検索**。EFD は Kuhl & Giardina (1982) の閉形式。

【グラウンドトゥルース(数値で嘘を弾く)】
1. 円の EFD は第1高調波が支配(長軸≈半径、高次≈0)。
2. 再構成は高調波を増やすほど元輪郭へ収束(最大距離が単調に減少)。
3. 不変性(beat-the-null): 同じ形を回転+拡大+移動+始点シフトしても記述子距離 ≈ 0、
   異なる形とは桁違いに離れる → ギャラリー検索で正解形状を最近傍に選べる。
4. 高調波の打ち切り = 低域通過 = とがりが消える(平滑化)。

輪郭は (N,2) 配列。既存 XLD 輪郭 dict は fourierdesc.from_xld で渡せる。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fourierdesc as F  # noqa: E402


def shp(kind, n=220, R=40, cx=0.0, cy=0.0, phi0=0.0):
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    if kind == "circle":
        x, y = R * np.cos(t), R * np.sin(t)
    elif kind == "square":
        c, s = np.cos(t), np.sin(t)
        m = np.maximum(np.abs(c), np.abs(s))
        x, y = R * c / m, R * s / m
    elif kind == "star":
        rr = R * (0.6 + 0.4 * np.cos(5 * t))
        x, y = rr * np.cos(t), rr * np.sin(t)
    elif kind == "leaf":
        rr = R * (0.5 + 0.5 * np.abs(np.cos(1.5 * t)) ** 0.7)
        x, y = rr * np.cos(t), rr * np.sin(t)
    else:
        raise ValueError(kind)
    return np.column_stack([x * np.cos(phi0) - y * np.sin(phi0) + cx,
                            x * np.sin(phi0) + y * np.cos(phi0) + cy])


def _maxdist(pts, poly):
    P = np.vstack([poly, poly[0]])
    A, B = P[:-1], P[1:]
    AB = B - A
    L2 = (AB ** 2).sum(1) + 1e-12
    return max(np.sqrt(((A + np.clip(((p - A) * AB).sum(1) / L2, 0, 1)[:, None] * AB - p) ** 2).sum(1)).min()
               for p in pts)


def main(save=None):
    # 1) 円 = 第1高調波
    m_c = F.elliptic_fourier(shp("circle", R=50), 8)
    amp = F._amplitudes(m_c["coeffs"])[:, 0]
    print(f"円のEFD  : 第1高調波長軸={amp[0]:.2f}(半径50)、高次最大={amp[1:].max():.3f}(≈0)")
    assert abs(amp[0] - 50) < 1 and amp[1:].max() < 0.05 * amp[0]

    # 2) 再構成の収束
    star = shp("star", R=40)
    errs = [_maxdist(F.reconstruct(F.elliptic_fourier(star, N), 300), star) for N in [1, 3, 6, 12, 24]]
    print(f"再構成収束: 星の最大距離 [1,3,6,12,24高調波] = {[round(e, 2) for e in errs]}")
    assert errs[-1] < 0.2 * errs[0]

    # 3) 不変マッチング + 検索
    gallery = {k: F.elliptic_fourier(shp(k, R=30, cx=10, phi0=1.1), 14)
               for k in ["circle", "square", "star", "leaf"]}
    for truth in ["square", "star", "leaf"]:
        q = F.elliptic_fourier(shp(truth, R=55, cx=-40, cy=20, phi0=2.3), 14)
        d = {k: F.descriptor_distance(q, g, 14) for k, g in gallery.items()}
        best = min(d, key=d.get)
        print(f"検索     : query={truth}(回転+拡大+移動) → 最近傍={best}  "
              f"距離={ {k: round(v, 3) for k, v in d.items()} }")
        assert best == truth and d[truth] < 1e-6

    # 4) 平滑化
    rng = np.random.default_rng(0)
    noisy = shp("circle", R=50, n=256) + rng.normal(0, 3, (256, 2))
    sm = F.fourier_smooth(noisy, keep=3)
    dev0 = np.std(np.hypot(noisy[:, 0], noisy[:, 1]))
    dev1 = np.std(np.hypot(sm[:, 0], sm[:, 1]))
    print(f"平滑化   : ノイズ円 半径ばらつき {dev0:.2f} → 平滑後 {dev1:.2f}")
    assert dev1 < 0.5 * dev0

    print("\nPASS: EFD は円を第1高調波で表し、高調波で元形状へ収束し、"
          "回転/拡大/移動/始点に不変な記述子で形状検索を正しく行い、"
          "高調波打ち切りで輪郭を平滑化できる。")

    if save:
        _save_figure(star, noisy, sm, save)
    return 0


def _save_figure(star, noisy, sm, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 3, figsize=(13, 4.2))
    m = F.elliptic_fourier(star, 24)
    ax[0].plot(*np.vstack([star, star[0]]).T, "k--", lw=1, label="original")
    for N, col in [(1, "C0"), (3, "C1"), (8, "C2")]:
        r = F.reconstruct(m, 300, n_harmonics=N)
        ax[0].plot(*np.vstack([r, r[0]]).T, col, label=f"{N} harm.")
    ax[0].set_title("EFD reconstruction (more harmonics = sharper)")
    ax[0].legend(fontsize=8); ax[0].axis("equal"); ax[0].axis("off")
    ax[1].plot(*np.vstack([noisy, noisy[0]]).T, "0.6", lw=1)
    ax[1].plot(*np.vstack([sm, sm[0]]).T, "C3", lw=2)
    ax[1].set_title("Fourier smoothing (keep=3)"); ax[1].axis("equal"); ax[1].axis("off")
    for k, col in [("circle", "C0"), ("square", "C1"), ("star", "C2"), ("leaf", "C3")]:
        s = shp(k, R=35)
        ax[2].plot(*np.vstack([s, s[0]]).T, col, label=k)
    ax[2].set_title("shape gallery (invariant matching)"); ax[2].legend(fontsize=8)
    ax[2].axis("equal"); ax[2].axis("off")
    plt.tight_layout(); plt.savefig(path, dpi=90, bbox_inches="tight"); plt.close()
    print(f"saved: {path}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--save", default=None)
    args = ap.parse_args()
    raise SystemExit(main(save=args.save))
