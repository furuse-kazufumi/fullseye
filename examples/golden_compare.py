# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""golden_compare — 基準画像(ゴールデン)と比べて欠陥を測り、ロット全体を判定する。

    py -3.11 examples/golden_compare.py

【この例が示すこと】
「良品と比べて違うところ」を 1 回の呼び出しで測る ``fs.compare_to_golden`` と、それを
``fs.inspect_batch`` の計測に差し込む ``fs.golden_measure`` / 仕様を組む ``fs.golden_spec``:

1. 同一画像 → 欠陥 0・SSIM 1.0
2. 3 px ずれた良品 → 位相相関で並進を測って合わせれば欠陥 0(合わせなければ縁が欠陥に見える)
3. 異物を足した品 → 欠陥 1 個・面積は足した大きさ(mask の外・min_area 未満は数えない)
4. 6 px もずれた品 → ``max_shift`` を超えるので合わせず ``align_ok=0`` → spec で ng
5. 合成ロット 6 枚(良品 4・異物 1・大ずれ 1)を inspect_batch で回し、その 2 枚だけ ng

を assert で確かめる(絵に描いたふりをしない)。差分の絵は ``out["diff"]`` / ``out["defect_mask"]``。

EXTEND: 照明差がある現場は前処理レシピ(``recipe=["normalize", ...]``)で揃えてから渡す。回転・
スケールを伴うずれは ``frame_align`` / 形状マッチで先に合わせる(ここは整数並進のみ)。
"""
from __future__ import annotations

import os
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fullseye as fs  # noqa: E402


def make_golden() -> np.ndarray:
    rng = np.random.default_rng(0)
    yy, xx = np.mgrid[0:96, 0:96]
    im = 0.35 + 0.25 * np.sin(xx / 9.0) * np.cos(yy / 11.0) + 0.02 * rng.standard_normal((96, 96))
    im[40:56, 40:56] = 0.9
    return np.clip(im, 0, 1)


def shifted(im, dr, dc):
    from scipy.ndimage import shift
    return shift(im, (dr, dc), order=0, mode="nearest")


def main() -> int:
    g = make_golden()

    # 1. 同一
    m = fs.compare_to_golden(g, g)["measurements"]
    assert m["defect_area"] == 0 and abs(m["ssim"] - 1.0) < 1e-9
    print("同一画像: 欠陥 0 / SSIM %.3f" % m["ssim"])

    # 2. ずれた良品
    m = fs.compare_to_golden(shifted(g, 3, -5), g, threshold=0.15)["measurements"]
    raw = fs.compare_to_golden(shifted(g, 3, -5), g, threshold=0.15, align=False)["measurements"]
    print("3px ずれた良品: 並進 (%+.0f, %+.0f) を合わせて欠陥 %d px(合わせないと %d px)"
          % (m["shift_row"], m["shift_col"], m["defect_area"], raw["defect_area"]))
    assert m["defect_area"] == 0 and raw["defect_area"] > 0

    # 3. 異物
    bad = g.copy()
    bad[10:16, 70:78] = 0.95
    out = fs.compare_to_golden(bad, g, threshold=0.2)
    m = out["measurements"]
    print("異物 6x8: 欠陥 %d 個 / 面積 %d px / max_diff %.2f" % (m["defect_count"], m["defect_area"], m["max_diff"]))
    assert m["defect_count"] == 1 and m["defect_area"] == 48
    assert out["defect_mask"][12, 74] and not out["defect_mask"][48, 48]

    # 4. 大ずれは合わせない
    m = fs.compare_to_golden(shifted(g, 6, 0), g, threshold=0.15, max_shift=3)["measurements"]
    v = fs.judge(m, fs.golden_spec(max_shift=3))
    print("6px ずれ: align_ok=%d → %s | %s" % (m["align_ok"], v.status, v.detail[:70]))
    assert m["align_ok"] == 0 and v.status == "ng"

    # 5. ロットを回す
    lot = tempfile.mkdtemp(prefix="fullseye_golden_")
    for i in range(4):
        np.save(os.path.join(lot, "part_%02d.npy" % i), shifted(g, (i % 3) - 1, 1 - (i % 2)))
    np.save(os.path.join(lot, "part_04.npy"), bad)
    np.save(os.path.join(lot, "part_05.npy"), shifted(g, 6, 0))
    res = fs.inspect_batch(lot, None, measure=fs.golden_measure(g, threshold=0.2, max_shift=3),
                           spec=fs.golden_spec(max_shift=3),
                           report_path=os.path.join(lot, "golden_report.md"), title="Golden lot")
    status = [r["verdict"]["status"] for r in res["rows"]]
    print("ロット:", status, res["summary"])
    assert status == ["ok", "ok", "ok", "ok", "ng", "ng"]
    print("report:", res["report_path"])
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
