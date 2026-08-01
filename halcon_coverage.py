"""HALCON coverage tracker — honest map of what we cover vs HALCON's taxonomy.

I do NOT have all ~2100 HALCON operators memorised. This encodes HALCON's Operator
Reference CHAPTER STRUCTURE (accurate) with per-chapter APPROXIMATE counts (my
estimates) and a CURATED list of operators I'm confident exist (not exhaustive).
It then maps our registry's `halcon` analog names onto those chapters to report
coverage. Treat counts as estimates; the authoritative list is the MVTec HALCON
Operator Reference — ingest it (docs/RAD) to drive exhaustive coverage.

Generates docs/HALCON_COVERAGE.md.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import ops

# chapter -> (approx operator count [estimate], curated known operators [not exhaustive])
CHAPTERS = [
    ("Filters", 150, ["gauss_filter", "mean_image", "median_image", "binomial_filter", "smooth_image",
                      "anisotropic_diffusion", "bilateral_filter", "sobel_amp", "sobel_dir", "laplace",
                      "laplace_of_gauss", "derivate_gauss", "edges_image", "diff_of_gauss", "dyn_threshold",
                      "emphasize", "sharpen", "rank_image", "gray_range_rect", "fft_image", "gen_gabor",
                      "convol_image", "mean_sp", "lowpass", "highpass", "butterworth"]),
    ("Morphology", 90, ["dilation1", "erosion1", "opening", "closing", "opening_circle", "closing_circle",
                        "gray_erosion", "gray_dilation", "gray_opening", "gray_closing", "gray_tophat",
                        "gray_bothat", "boundary", "connection", "fill_up", "skeleton", "gray_range_rect"]),
    ("Regions", 140, ["threshold", "binary_threshold", "var_threshold", "dyn_threshold", "regiongrowing",
                      "connection", "select_shape", "area_center", "shape_trans", "fill_up", "complement",
                      "difference", "intersection", "union1", "erosion_circle", "dilation_circle",
                      "select_shape_largest", "select_shape_area", "clear_border"]),
    ("XLD / Contours", 180, ["edges_sub_pix", "threshold_sub_pix", "gen_contour_polygon_xld",
                             "fit_line_contour_xld", "fit_circle_contour_xld", "fit_ellipse_contour_xld",
                             "segment_contours_xld", "select_contours_xld", "smooth_contours_xld", "length_xld",
                             "area_center_xld", "gen_region_contour_xld", "union_collinear_contours_xld",
                             "find_contours"]),
    ("Matching", 120, ["create_shape_model", "find_shape_model", "create_ncc_model", "find_ncc_model",
                       "create_scaled_shape_model", "create_aniso_shape_model", "best_match", "create_template"]),
    ("Measuring", 60, ["gen_measure_rectangle2", "measure_pos", "measure_pairs", "fuzzy_measure_pos"]),
    ("Identification (Bar/Data code, OCR)", 120, ["create_bar_code_model", "find_bar_code", "decode_bar_code",
                                                  "create_data_code_2d_model", "find_data_code_2d",
                                                  "read_ocr_class_mlp", "do_ocr_single_class", "create_ocr_class_cnn"]),
    ("Calibration", 90, ["calibrate_cameras", "find_calib_object", "gen_caltab", "camera_calibration"]),
    ("3D (object model / reconstruction / metrology / matching)", 330,
     ["read_object_model_3d", "prepare_object_model_3d", "binocular_stereo", "disparity_image_to_xyz",
      "reconstruct_surface_stereo", "create_surface_model", "find_surface_model", "xyz_to_object_model_3d"]),
    ("Classification", 120, ["create_class_mlp", "create_class_svm", "create_class_gmm", "create_class_knn",
                             "classify_image_class_mlp", "select_shape_circularity"]),
    ("Deep Learning", 150, ["read_dl_model", "apply_dl_model", "train_dl_model", "gen_dl_samples"]),
    ("Image (channels / access / generation)", 120, ["gen_image_const", "decompose3", "compose3",
                                                     "get_grayval", "scale_image", "invert_image", "pow_image",
                                                     "equ_histo_image", "zoom_image_size", "rotate_image",
                                                     "affine_trans_image"]),
    ("Graphics / Visualization", 200, ["disp_image", "dev_display", "set_color"]),
    ("Tuple / System / File / Tools", 460, ["tuple_add", "read_image", "write_image", "count_obj"]),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="docs/HALCON_COVERAGE.md")
    a = ap.parse_args()
    ours = {op.halcon for op in ops.REGISTRY}
    total_est = sum(c for _, c, _ in CHAPTERS)

    rows = ["# imgevolve — HALCON coverage (honest, partial)", "",
            "I don't have all ~2100 HALCON operators memorised. Below is HALCON's chapter "
            "structure with **estimated** counts and a **curated** (non-exhaustive) operator list, "
            "mapped against our registry's `halcon` analog names. The authoritative list is the "
            "**MVTec HALCON Operator Reference** — ingesting it (RAD) is how we drive exhaustive coverage.", "",
            f"Our registry currently exposes **{ops.N_OPS} operators**; HALCON is estimated at "
            f"**~{total_est}** (of which a large share is non-algorithmic infrastructure — "
            "graphics/tuple/system/file).", "",
            "| chapter | est. count | curated known | ours (matched) |", "|---|---|---|---|"]
    algo_est = matched_total = 0
    for name, count, known in CHAPTERS:
        matched = sorted(k for k in known if k in ours)
        rows.append(f"| {name} | ~{count} | {len(known)} | {len(matched)}: {', '.join(matched) or '—'} |")
        if not name.startswith(("Graphics", "Tuple")):
            algo_est += count
        matched_total += len(matched)
    rows += ["",
             f"**Matched {matched_total} curated HALCON operators** across chapters "
             f"(the imgevolve registry has {ops.N_OPS} ops incl. OpenCV/skimage/torch analogs).",
             "",
             "## Honest reading",
             f"- Algorithmic chapters ~{algo_est} operators; ~660 are infrastructure (graphics/tuple/system/file) "
             "that an algorithm-design engine does not target.",
             "- Many HALCON operators are parametric variants of a family (collapse to fewer).",
             "- **Gap to full coverage**: 3D/DL/OCR/calibration/matching need heavy deps (Open3D/torch/models) "
             "or the official reference for exact signatures. Next: fetch the MVTec Operator Reference into RAD, "
             "then generate typed stubs per operator so coverage is tracked against the real 2100, not memory.", ""]
    p = Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(rows), encoding="utf-8")
    print(f"[halcon_coverage] matched {matched_total} curated ops across {len(CHAPTERS)} chapters -> {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
