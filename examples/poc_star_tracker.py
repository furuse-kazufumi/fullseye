# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""poc_star_tracker — 合成星像から対応付けと Kabsch で衛星姿勢を推定する。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools import build_startrk_anim3d as demo


def main():
    result = demo.compute()
    gate = demo.gates(result)
    print("stars=%d mismatches=%d centroid_median=%.4f px" %
          (gate["n_stars"], gate["mismatch_count"], gate["centroid_median_px"]))
    print("attitude_error=%.4f deg pixel_angle=%.4f deg kabsch_vs_svd=%s" %
          (gate["attitude_error_deg"], gate["angular_pixel_deg"],
           demo._e(gate["kabsch_svd_max_difference"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
