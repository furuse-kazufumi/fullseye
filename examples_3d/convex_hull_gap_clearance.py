# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: 2 つの部品の凸包の隙間を、保証つきの上下限で測る(新規 op ``convex_hull_gap``)。

    py -3.11 examples_3d/convex_hull_gap_clearance.py

【この例が示すこと】
1. **閉形式の真値** —— x に d だけ離した箱 2 つの隙間は d、角どうしを斜めに離せば
   √(dx² + dy² + dz²)。上限(実際に作った最も近い点の組の距離)と下限(頂点から直接測った分離の帯の幅)の
   差は 1e-9 以下。独立な線形計画(HiGHS)の t も ``t/√3 ≤ 隙間 ≤ t`` の帯に入る。
2. **頂点の距離では重なりを否定できない** —— 細い棒 2 本の十字は凸包が交わるのに、頂点の間は 1.4 離れていて、
   hausdorff_distance(既存の op)も 1.4 と出す。この op は重なり(``separated = False``)と判定する。
3. **組立の隙間** —— 走査した点群に、隙間の中の飛び点が 6 点まじると、凸包の隙間は飛び点まで詰まって見える。
   既存の ``radius_outlier_removal``(半径 0.06 に近傍 2 点未満を除く)で飛び点を除いてから測ると、面の間の 0.3 に戻る(op の組み合わせ)。
4. **独立な実装との一致** —— 2 点ずつの凸包は線分どうしの距離(``distance_segment_segment``、閉形式)と
   乱数の 200 組で 1e-9 以内。

【グラウンドトゥルース】作った箱・棒・面の座標(閉形式)と、独立な閉形式の op。
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import examplefig as figs     # noqa: E402
import fullseye as fs          # noqa: E402
import hull3d                  # noqa: E402
import match3d                 # noqa: E402
import metrics3d               # noqa: E402
import pcl_filter              # noqa: E402

LG = fs.ledger                 # 台帳(ops3d の bounds)から名前で呼ぶ


def box(lo, hi):
    """軸平行の箱の 8 頂点。"""
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    g = np.array(np.meshgrid([0, 1], [0, 1], [0, 1])).reshape(3, -1).T
    return lo + g * (hi - lo)


def raster_top_view(parts, witness, extent, n=360):
    """真上から見た凸包(x-y への射影)を塗り、最も近い点の組を線で引いた図(numpy だけ)。"""
    from scipy.spatial import ConvexHull
    x0, x1, y0, y1 = extent
    xs = np.linspace(x0, x1, n)
    ys = np.linspace(y1, y0, n)
    X, Y = np.meshgrid(xs, ys)
    img = np.full((n, n, 3), 0.97)
    colors = [(0.25, 0.45, 0.85), (0.9, 0.55, 0.2)]
    for P, col in zip(parts, colors):
        h = ConvexHull(P[:, :2])
        inside = np.ones_like(X, bool)
        for a, b, c in h.equations:
            inside &= a * X + b * Y + c <= 1e-12
        img[inside] = col
    (ax, ay, _), (bx, by, _) = witness
    for u in np.linspace(0.0, 1.0, 400):
        px, py = ax + u * (bx - ax), ay + u * (by - ay)
        j = int(round((px - x0) / (x1 - x0) * (n - 1)))
        i = int(round((y1 - py) / (y1 - y0) * (n - 1)))
        img[max(0, i - 1):i + 2, max(0, j - 1):j + 2] = (0.1, 0.1, 0.1)
    return img


def main() -> int:
    checks = []
    # ---- 1. 閉形式の真値 ---------------------------------------------------------------- #
    a = box([0, 0, 0], [1, 1, 1])
    rows = []
    for d in (0.25, 0.01, 1e-4):
        r = LG.convex_hull_gap(a, box([1 + d, 0.2, -0.3], [2.5 + d, 0.9, 0.4]))
        rows.append(["x に %.4g 離す" % d, "%.12f" % r["gap"], "%.3g" % (r["gap_upper"] - r["gap_lower"]),
                     "%.6f" % r["lp_t"]])
        checks.append(r["separated"] and abs(r["gap"] - d) < 1e-12 and r["gap_upper"] - r["gap_lower"] <= 1e-9)
    dx, dy, dz = 0.3, 0.4, 0.5
    diag = LG.convex_hull_gap(a, box([1 + dx, 1 + dy, 1 + dz], [2 + dx, 2.5 + dy, 1.7 + dz]))
    want = math.sqrt(dx * dx + dy * dy + dz * dz)
    rows.append(["角どうし (0.3, 0.4, 0.5)", "%.12f" % diag["gap"], "%.3g" % (diag["gap_upper"] - diag["gap_lower"]),
                 "%.6f" % diag["lp_t"]])
    print("1. 隙間(真値 d / √(dx²+dy²+dz²) = %.12f):" % want)
    for row in rows:
        print("   %-22s gap %s  上限−下限 %s  線形計画 t %s" % tuple(row))
    checks.append(abs(diag["gap"] - want) < 1e-12 and diag["lp_t"] / math.sqrt(3) <= diag["gap"] <= diag["lp_t"])
    touch = LG.convex_hull_gap(a, box([1, 0.2, 0.1], [2, 1.2, 1.1]))
    over = LG.convex_hull_gap(a, box([0.9, 0.2, 0.1], [2, 1.2, 1.1]))
    print("   接触 separated=%s gap=%s / 食い込み separated=%s gap=%s"
          % (touch["separated"], touch["gap"], over["separated"], over["gap"]))
    checks.append(not touch["separated"] and not over["separated"] and touch["gap"] == over["gap"] == 0.0)

    # ---- 2. 十字の棒(反例の対照) ------------------------------------------------------- #
    rod_a = box([-1, -0.01, -0.01], [1, 0.01, 0.01])
    rod_b = box([-0.01, -1, -0.01], [0.01, 1, 0.01])
    vmin = float(np.min(np.linalg.norm(rod_a[:, None] - rod_b[None], axis=2)))
    hd = float(metrics3d.hausdorff_distance(rod_a, rod_b))
    cr = LG.convex_hull_gap(rod_a, rod_b)
    print("2. 十字の棒: 頂点どうしの最短距離 %.4f、hausdorff_distance %.4f(どちらも「離れている」)、"
          "convex_hull_gap は separated=%s(凸包は交わる)" % (vmin, hd, cr["separated"]))
    checks.append(vmin > 1.4 and hd > 1.4 and not cr["separated"])

    # ---- 3. 組立の隙間(飛び点 → 既存の外れ点除去 → 隙間) ------------------------------- #
    rng = np.random.default_rng(5)
    part_a = np.r_[np.c_[np.ones(400), rng.random((400, 2))], rng.random((1600, 3))]
    part_b = np.r_[np.c_[np.full(400, 1.3), rng.random((400, 2))], rng.random((800, 3)) + [1.3, 0, 0]]
    fly_yz = np.array([[0.2, 0.2], [0.2, 0.8], [0.5, 0.5], [0.8, 0.2], [0.8, 0.8], [0.5, 0.15]])
    fly = np.c_[1.135 + 0.03 * rng.random(6), fly_yz]          # 隙間の真ん中の飛び点(互いに 0.06 より離す)
    raw = LG.convex_hull_gap(np.r_[part_a, fly], part_b)
    clean, keep = pcl_filter.radius_outlier_removal(np.r_[part_a, fly], radius=0.06, min_neighbors=2)
    fixed = LG.convex_hull_gap(clean, part_b)
    print("3. 組立の隙間(作った値 0.3): 飛び点 6 点ありの凸包 %.4f → radius_outlier_removal の後 %.12f"
          "(除いた点 %d、うち飛び点 %d)" % (raw["gap"], fixed["gap"], int((~keep).sum()), int((~keep[-6:]).sum())))
    checks.append(raw["gap"] < 0.2 and abs(fixed["gap"] - 0.3) < 1e-9 and bool((~keep[-6:]).all()))

    # ---- 4. 独立な閉形式の op と一致 ---------------------------------------------------- #
    worst = 0.0
    for _ in range(200):
        p0, p1, q0, q1 = rng.standard_normal((4, 3))
        ref = match3d.distance_segment_segment(p0, p1, q0, q1)[0]
        worst = max(worst, abs(hull3d.convex_hull_gap(np.array([p0, p1]), np.array([q0, q1]))["gap"] - ref))
    print("4. 線分どうしの距離(distance_segment_segment)との差の最大 %.2e(200 組)" % worst)
    checks.append(worst < 1e-9)

    figs.save_table("gaps", ["配置", "gap", "上限−下限", "線形計画 t"], rows,
                    title="convex_hull_gap — 閉形式の真値との突き合わせ",
                    caption="x に d 離した箱は d、角どうしは √(dx²+dy²+dz²)。t は ‖w‖∞ ≤ 1 の線形計画(t/√3 ≤ 隙間 ≤ t)。")
    figs.save("top_view", raster_top_view([np.r_[part_a, fly], part_b], (raw["witness_a"], raw["witness_b"]),
                                          (-0.1, 2.4, -0.1, 1.1)),
              "真上から見た 2 部品の凸包(青 = 飛び点つきの A、橙 = B)と、最も近い点の組(黒線)。"
              "飛び点が A の凸包を隙間の中へ引き伸ばしている。")

    ok_all = all(bool(c) for c in checks)
    print("PASS" if ok_all else "FAIL", "(%d / %d)" % (sum(bool(c) for c in checks), len(checks)))
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
