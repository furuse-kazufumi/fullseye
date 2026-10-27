# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""poc_star_tracker — 合成星像から対応付けと Kabsch で衛星姿勢を推定する。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import examplefig as figs
from tools import build_startrk_anim3d as demo


def main():
    result = demo.compute()
    gate = demo.gates(result)
    print("stars=%d mismatches=%d centroid_median=%.4f px" %
          (gate["n_stars"], gate["mismatch_count"], gate["centroid_median_px"]))
    print("attitude_error=%.4f deg pixel_angle=%.4f deg kabsch_vs_svd=%s" %
          (gate["attitude_error_deg"], gate["angular_pixel_deg"],
           demo._e(gate["kabsch_svd_max_difference"])))
    print("catalogue=%d detections=%d genuine=%d false_rejected=%d/%d" %
          (gate["catalogue_size"], gate["n_detections"], gate["n_stars"],
           gate["false_rejected"], gate["n_false"]))

    # examplefig is a no-op when FULLSEYE_FIGURES=off, so the numerical CI path
    # does not pay for plotting or file I/O.  With FULLSEYE_FIGURE_DIR it gives
    # Studio a camera image, the detected points, and a copyable gate table.
    figs.save("star_tracker_camera_image", result["image"],
              "PSF・光子雑音・読み出し雑音を含む合成像。真の星16個に、星表に無いホットピクセル2個を加えた。",
              gray=True)
    figs.save_plot("star_tracker_detections",
                   [("18 detections", result["detected"][:, 1], result["detected"][:, 0]),
                    ("16 catalogue matches", result["detected"][result["match"] >= 0, 1],
                     result["detected"][result["match"] >= 0, 0])],
                   xlabel="column [px]", ylabel="row [px]",
                   title="Detected points and catalogue inliers",
                   caption="三角形の角距離で全196星表を探索し、ホットピクセル2個を外れ値として棄却した。",
                   kinds=["scatter", "scatter"], colors=["wrong", "reference"])
    figs.save_table("star_tracker_gates", ["gate", "result", "criterion"], [
        ["catalogue matching", "%d mismatch" % gate["mismatch_count"], "0"],
        ["false-point rejection", "%d/%d" % (gate["false_rejected"], gate["n_false"]), "all"],
        ["attitude angle", "%.4f deg" % gate["attitude_error_deg"],
         "< %.4f deg" % gate["angular_pixel_deg"]],
        ["kabsch vs direct SVD", demo._e(gate["kabsch_svd_max_difference"]), "< 1e-12"],
    ], title="Star-tracker gates",
       caption="推定値は合成像の検出点から計算し、真値は採点だけに使った。")

    ok = (gate["mismatch_count"] == 0 and gate["false_kept"] == 0
          and gate["false_rejected"] == gate["n_false"] == 2
          and gate["attitude_error_deg"] < gate["angular_pixel_deg"]
          and gate["kabsch_svd_max_difference"] < 1e-12)
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
        ok = False
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
