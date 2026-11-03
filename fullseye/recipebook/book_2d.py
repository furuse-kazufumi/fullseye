"""2-D image recipes (registry ops; every one runs unchanged through MCP ``fullseye_pipeline``).

Organised by HALCON chapter: Filters, Segmentation, Regions / Morphology, Features, 1D Measuring,
XLD / Contours, Matching, Inspection, Texture, Color, Transformations, Restoration, Frequency,
Identification, OCR.

Every stage is a 2-D registry op written as ``{"op", "a", "b"}`` (the knobs are normalised to [0, 1];
each op note in ``docs/ops/2d/<category>/<op>.md`` documents how a knob maps to a physical value —
the mapping used is repeated in each recipe's note). The samples below are small (96 x 96) synthetic
scenes with a closed-form answer (pixel area of a disk, number of parts, edge column, angle, period...).

Angle conventions seen while writing this book (measured, see FAILED_ATTEMPTS): ``orientation_region``
returns the HALCON angle (counter-clockwise from the column axis with rows pointing down) divided by
180 deg; ``xg_orientation`` and ``structure_tensor_orientation`` return the angle measured the other way
round, i.e. (180 - theta) / 180 for a line turned theta counter-clockwise.
"""
from __future__ import annotations

import numpy as np

N = 96   # side of every synthetic scene in this book (px)


def _R(op, a=0.5, b=0.5):
    """A registry stage (the MCP-runnable form)."""
    return {"op": op, "a": a, "b": b}


RECIPES = [
    # ---------------------------------------------------------------- Regions (the 2 originals)
    {"name": "Measure — diameter of a bright round part", "family": "2d", "task": "measure",
     "task_class": "measurement", "halcon": "Regions", "input_sort": "image", "sample": "disk_image",
     "stages": [{"op": "gaussian", "a": 0.3, "b": 0.5}, {"op": "otsu", "a": 0.5, "b": 0.5},
                {"op": "fill_up", "a": 0.5, "b": 0.5}, {"op": "diameter_region", "a": 0.5, "b": 0.5}],
     "expect": [{"get": [], "approx": "diameter", "atol": 3.0}],
     "note": "smooth, Otsu, fill holes, then the region's maximal diameter in pixels "
             "(the disk's diameter 2r; the sample's disk has r = 18 + 6·variant)"},
    {"name": "Inspect — roundness of a punched disk (circularity)", "family": "2d", "task": "inspect",
     "task_class": "inspection", "halcon": "Regions", "input_sort": "image", "sample": "disk_image",
     "stages": [{"op": "otsu", "a": 0.5, "b": 0.5}, {"op": "fill_up", "a": 0.5, "b": 0.5},
                {"op": "circularity", "a": 0.5, "b": 0.5}],
     "expect": [{"get": [], "between": [0.9, 1.0]}],
     "note": "binarize, fill, circularity 4πA/P²-style score: near 1 for a good round part, lower when it is "
             "dented or oval"},

    # ---------------------------------------------------------------- Filters
    {"name": "Preprocess — remove salt-and-pepper impulses before measuring part area", "family": "2d",
     "task": "denoise", "task_class": "preprocess", "halcon": "Filters", "input_sort": "image",
     "sample": "d2_saltpepper_disk",
     "stages": [_R("median", 0.3), _R("otsu"), _R("area_center")],
     "expect": [{"get": [0], "approx": "area", "rtol": 0.03}, {"get": [1], "approx": "row", "atol": 0.5}],
     "note": "Impulse (salt-and-pepper) noise from a faulty sensor or dust inflates a binarized area: Otsu on the "
             "raw image counts the white impulses as part pixels (+22 % here). A 3x3 median (a=0.3 -> window 3) "
             "removes isolated impulses while keeping the edge, then Otsu + area_center give the part area in "
             "px² (truth πr², r = 16 + 6·variant) and its centroid row (px)."},
    {"name": "Preprocess — denoise a flat field and verify the residual noise level", "family": "2d",
     "task": "denoise", "task_class": "preprocess", "halcon": "Filters", "input_sort": "image",
     "sample": "d2_flat_noise",
     "stages": [_R("median", 0.6), _R("estimate_noise")],
     "expect": [{"get": [], "between": [0.0, "sigma_half"]}],
     "note": "Flat grey frame with white Gaussian sensor noise (sigma 0.02 / 0.05). A 7x7 median (a=0.6) "
             "smooths it and estimate_noise (robust Laplacian-MAD sigma, grey units 0..1) checks that the "
             "residual noise dropped below half of the input sigma — a quick denoise acceptance test."},

    # ---------------------------------------------------------------- Segmentation
    {"name": "Inspect — count parts under strongly uneven illumination (local threshold)", "family": "2d",
     "task": "count", "task_class": "inspection", "halcon": "Segmentation", "input_sort": "image",
     "sample": "d2_shaded_blobs",
     "stages": [_R("local_threshold", 0.5, 0.6), _R("opening_circle", 0.2), _R("count_obj")],
     "expect": [{"get": [], "equals": "count"}],
     "note": "Small bright parts on a left-to-right illumination ramp: one global Otsu threshold cuts the ramp "
             "and returns ~20 fragments. local_threshold compares each pixel with its Gaussian local mean "
             "(a=0.5 -> sigma 2.5 px, b=0.6 -> offset +0.03), a radius-1 opening (a=0.2) removes single-pixel "
             "noise, count_obj counts 8-connected parts (truth 4 / 6)."},
    {"name": "Preprocess — flatten an illumination gradient with a plane fit, then count parts", "family": "2d",
     "task": "count", "task_class": "preprocess", "halcon": "Segmentation", "input_sort": "image",
     "sample": "d2_shaded_blobs",
     "stages": [_R("hx_plane_deviation"), _R("otsu"), _R("count_obj")],
     "expect": [{"get": [], "equals": "count"}],
     "note": "Shading correction by background subtraction: fit a first-order plane to the grey values and "
             "keep |image - plane| (removes a linear illumination ramp / tilt), then a global Otsu threshold "
             "works again and count_obj gives the number of parts (truth 4 / 6)."},
    {"name": "Inspect — split touching round parts and count them (distance-transform peaks)", "family": "2d",
     "task": "count", "task_class": "inspection", "halcon": "Segmentation", "input_sort": "image",
     "sample": "d2_touching_disks",
     "stages": [_R("otsu"), _R("dist_transform"), _R("xsk2_h_maxima", 0.3), _R("count_obj")],
     "expect": [{"get": [], "equals": "count"}],
     "note": "Pairs of overlapping pellets / cells: a plain connected-component count sees one blob per pair. "
             "The Euclidean distance transform of the mask peaks at each disk centre; h-maxima (a=0.3 -> "
             "h = 0.14 of the normalised distance) keeps one marker per disk, so count_obj returns the number of "
             "individual parts (truth 4 / 6) — the marker step of a watershed split."},
    {"name": "Measure — part area with a k-means intensity segmentation", "family": "2d",
     "task": "segment", "task_class": "measurement", "halcon": "Segmentation", "input_sort": "image",
     "sample": "disk_image",
     "stages": [_R("sg_kmeans_intensity", 0.0), _R("area_center")],
     "expect": [{"get": [0], "approx": "area", "rtol": 0.02}, {"get": [2], "approx": "col", "atol": 0.5}],
     "note": "Clustering the grey values into k = 2 classes (a=0) and keeping the brightest class is a "
             "threshold-free alternative to Otsu; area_center returns (area px², centroid row, col). Truth: "
             "disk of radius 18 + 6·variant."},
    {"name": "Measure — part area with hysteresis thresholding", "family": "2d", "task": "segment",
     "task_class": "measurement", "halcon": "Segmentation", "input_sort": "image", "sample": "disk_image",
     "stages": [_R("gaussian", 0.1), _R("hysteresis_threshold", 0.8, 0.2), _R("area_center")],
     "expect": [{"get": [0], "approx": "area", "rtol": 0.02}],
     "note": "Hysteresis keeps pixels above a low threshold (a=0.8 -> 0.44) only when connected to pixels above "
             "a high one (b=0.2 -> 0.56): robust against noise speckles that cross a single threshold. A light "
             "Gaussian (sigma 0.57 px) first; area in px² (truth πr²)."},

    # ---------------------------------------------------------------- Regions
    {"name": "Measure — hole area fraction of a washer", "family": "2d", "task": "measure",
     "task_class": "measurement", "halcon": "Regions", "input_sort": "image", "sample": "d2_washer",
     "stages": [_R("otsu"), _R("area_holes")],
     "expect": [{"get": [], "approx": "hole_frac", "atol": 0.005}],
     "note": "Washer / ring gasket: Otsu, then area_holes = (filled area - area) / filled area, i.e. the hole's "
             "share of the outer disk = (r_in / r_out)² (r_out 34, r_in 10 / 16 px)."},
    {"name": "Inspect — count punched holes in a plate (Euler number)", "family": "2d", "task": "count",
     "task_class": "inspection", "halcon": "Regions", "input_sort": "image", "sample": "d2_plate_holes",
     "stages": [_R("otsu"), _R("euler_number")],
     "expect": [{"get": [], "equals": "euler"}],
     "note": "A single plate with k round holes has Euler number 1 - k (components minus holes): a missing or "
             "extra punched hole changes it. Truth k = 2 / 3."},
    {"name": "Measure — orientation angle of an elongated part", "family": "2d", "task": "measure",
     "task_class": "measurement", "halcon": "Regions", "input_sort": "image", "sample": "d2_bar",
     "stages": [_R("otsu"), _R("orientation_region")],
     "expect": [{"get": [], "approx": "orient01", "atol": 0.006}],
     "note": "Principal-axis angle of a bar (pin, screw, rod) for pick-and-place alignment. orientation_region "
             "returns the HALCON angle (counter-clockwise from the column axis, rows down) scaled by 1/180 deg: "
             "multiply by 180 for degrees. Truth 20 / 45 deg; tolerance ~1 deg."},
    {"name": "Measure — equivalent-ellipse semi-axes of an oval part", "family": "2d", "task": "measure",
     "task_class": "measurement", "halcon": "Regions", "input_sort": "image", "sample": "d2_ellipse",
     "stages": [_R("otsu"), _R("elliptic_axis")],
     "expect": [{"get": [0], "approx": "ra", "atol": 1.0}, {"get": [1], "approx": "rb", "atol": 1.0}],
     "note": "Equivalent ellipse (same second moments) of a binarized oval: (Ra, Rb, Phi), Ra / Rb in px. "
             "Truth Ra = 32, Rb = 12 / 18 px. (Phi is not gated: its sign is opposite to orientation_region's, "
             "see FAILED_ATTEMPTS.)"},
    {"name": "Measure — anisometry (aspect ratio) of an oval part", "family": "2d", "task": "measure",
     "task_class": "measurement", "halcon": "Regions", "input_sort": "image", "sample": "d2_ellipse",
     "stages": [_R("gaussian", 0.1), _R("otsu"), _R("eccentricity")],
     "expect": [{"get": [0], "approx": "anisometry", "rtol": 0.03}],
     "note": "HALCON eccentricity returns (anisometry Ra/Rb, bulkiness, structure factor); anisometry flags "
             "oval / squashed parts. Truth 32/12 and 32/18."},
    {"name": "Measure — area and position of the largest part in a cluttered scene", "family": "2d",
     "task": "measure", "task_class": "measurement", "halcon": "Regions", "input_sort": "image",
     "sample": "d2_sizes",
     "stages": [_R("otsu"), _R("select_largest"), _R("area_center")],
     "expect": [{"get": [0], "approx": "area", "rtol": 0.01}, {"get": [1], "approx": "row", "atol": 0.5},
                {"get": [2], "approx": "col", "atol": 0.5}],
     "note": "Several parts of different size: keep only the largest connected region (select_shape_std "
             "'max_area'), then its area (px²) and centroid (row, col px). Truth: disk r = 12 / 17 at (30, 30)."},
    {"name": "Measure — convex-hull area of a C-shaped part", "family": "2d", "task": "measure",
     "task_class": "measurement", "halcon": "Regions", "input_sort": "image", "sample": "d2_cshape",
     "stages": [_R("otsu"), _R("get_region_convex"), _R("area_center")],
     "expect": [{"get": [0], "approx": "hull_area", "rtol": 0.03}],
     "note": "Open ring (C-clip) with a gap of 60 / 100 deg: the convex hull closes the gap with a chord, area "
             "= πR² - R²/2·(g - sin g) for R = 30 px (closed form). Used for packing / gripper envelope."},
    {"name": "Inspect — convexity of a C-shaped clip (gap detection)", "family": "2d", "task": "inspect",
     "task_class": "inspection", "halcon": "Regions", "input_sort": "image", "sample": "d2_cshape",
     "stages": [_R("otsu"), _R("convexity")],
     "expect": [{"get": [], "approx": "convexity", "atol": 0.02}],
     "note": "Convexity = area / convex-hull area: 1 for convex parts, lower for open or dented ones. Truth from "
             "the pixel area of the clip over the closed-form hull area."},
    {"name": "Measure — length of a thin wire or scratch", "family": "2d", "task": "measure",
     "task_class": "measurement", "halcon": "Regions", "input_sort": "image", "sample": "d2_thin_line",
     "stages": [_R("otsu"), _R("diameter_region")],
     "expect": [{"get": [], "approx": "length", "atol": 1.5}],
     "note": "Maximal diameter (largest point-to-point distance, px) of a 3 px wide straight line = its length "
             "(50 / 70 px; pixel centres give L - 1)."},
    {"name": "Measure — wall thickness of a bar-shaped part", "family": "2d", "task": "measure",
     "task_class": "measurement", "halcon": "Regions", "input_sort": "image", "sample": "d2_bar",
     "stages": [_R("otsu"), _R("get_region_thickness")],
     "expect": [{"get": [], "approx": "width", "atol": 1.2}],
     "note": "Thickness of a rotated bar (width 10 / 14 px) from the region's thickness profile along its main "
             "axis (px). Use for rib / web / weld-seam width checks."},
    {"name": "Inspect — count the arms of a branched part (skeleton end points)", "family": "2d",
     "task": "count", "task_class": "inspection", "halcon": "Regions", "input_sort": "image", "sample": "d2_star",
     "stages": [_R("otsu"), _R("opening_circle", 0.1), _R("skeleton"), _R("r2_endpoints_skeleton"),
                _R("count_obj")],
     "expect": [{"get": [], "equals": "arms"}],
     "note": "Star bracket / connector with m arms: binarize, a radius-1 opening (a=0.1) removes edge pixel "
             "noise that would grow skeleton spurs, skeletonize, keep the skeleton end points and count them "
             "(= number of arms, 3 / 4). A broken-off arm lowers the count."},

    # ---------------------------------------------------------------- Morphology
    {"name": "Preprocess — remove dust specks, then count the real parts", "family": "2d", "task": "count",
     "task_class": "preprocess", "halcon": "Morphology", "input_sort": "image", "sample": "d2_specks",
     "stages": [_R("otsu"), _R("remove_small", 0.0), _R("count_obj")],
     "expect": [{"get": [], "equals": "count"}],
     "note": "Binarized image with 1-4 px dust specks next to the real parts: remove_small drops components "
             "below 1 % of the image (a=0 -> 92 px), so count_obj counts only the parts (2 / 3; raw count "
             "11-15)."},
    {"name": "Inspect — dark pits on a bright surface (black top-hat)", "family": "2d", "task": "inspect",
     "task_class": "inspection", "halcon": "Morphology", "input_sort": "image", "sample": "d2_dark_pits",
     "stages": [_R("bothat", 0.6), _R("threshold", 0.5), _R("count_obj")],
     "expect": [{"get": [], "equals": "count"}],
     "note": "Black top-hat (closing - image, a=0.6 -> 7x7 element) isolates dark defects smaller than the "
             "element and ignores the slow brightness ramp; threshold 0.5 of the normalised response and "
             "count (pits 2 / 4)."},
    {"name": "Inspect — bright spots on a vignetted background (white top-hat)", "family": "2d",
     "task": "inspect", "task_class": "inspection", "halcon": "Morphology", "input_sort": "image",
     "sample": "d2_spots_on_shading",
     "stages": [_R("gray_tophat", 0.6), _R("otsu"), _R("count_obj")],
     "expect": [{"get": [], "equals": "count"}],
     "note": "White top-hat (image - opening, a=0.6 -> 7x7 element) removes the smooth vignetting / shading "
             "and keeps small bright spots (particles, solder balls); Otsu on the residue and count (3 / 5). "
             "Global Otsu on the raw image finds 8 regions on both variants."},

    # ---------------------------------------------------------------- Features / edges
    {"name": "Inspect — count bright round blobs (Laplacian-of-Gaussian detector)", "family": "2d",
     "task": "count", "task_class": "inspection", "halcon": None, "input_sort": "image", "sample": "blobs_image",
     "stages": [_R("gaussian", 0.2), _R("xsk_blob_log", 0.2, 0.5)],
     "expect": [{"get": [], "equals": "count"}],
     "note": "Scale-space blob detection (LoG, a=0.2 -> max_sigma 9, b=0.5 -> threshold 0.095) counts spots / "
             "cells / pellets without a binarization step. Truth 3 / 4 disks of radius 6-8 px."},
    {"name": "Inspect — count circular holes with the Hough circle transform", "family": "2d", "task": "count",
     "task_class": "inspection", "halcon": "Features", "input_sort": "image", "sample": "blobs_image",
     "stages": [_R("gaussian", 0.5), _R("cv_hough_circles", 0.5, 0.0)],
     "expect": [{"get": [], "equals": "count"}],
     "note": "Hough gradient circle voting (radii 3-20 px fixed; a=0.5 -> min centre distance 20, b=0 -> vote "
             "threshold 20). The Gaussian (sigma 1.65 px) is required: on the raw noisy image the detector "
             "finds 0 circles (same with cv2.HoughCircles directly). Truth 3 / 4."},
    {"name": "Inspect — count corners of rectangular parts", "family": "2d", "task": "count",
     "task_class": "inspection", "halcon": "Features", "input_sort": "image", "sample": "d2_squares",
     "stages": [_R("gaussian", 0.1), _R("cv_good_features", 0.9, 0.5)],
     "expect": [{"get": [], "equals": "corners"}],
     "note": "Shi-Tomasi corner detection (a=0.9 -> up to 46 corners, b=0.5 -> quality 0.06, min distance 5 px) "
             "on squares: 4 corners per intact part (8 / 12) — a chipped corner changes the count."},
    {"name": "Measure — edge column from the gradient projection profile", "family": "2d", "task": "measure",
     "task_class": "measurement", "halcon": "Filters", "input_sort": "image", "sample": "step_edge_image",
     "stages": [_R("gaussian", 0.3), _R("sobel_amp"), _R("img_to_projection_profile", 0.0, 0.2)],
     "expect": [{"get": ["@argmax"], "approx": "edge_col", "atol": 1.0}],
     "note": "Smooth (sigma 1.1 px), Sobel gradient magnitude, then average the columns into a 1-D profile "
             "(b<0.5 -> length W); the profile's maximum is the column of a vertical edge (px). Truth 23.5 / "
             "31.5."},
    {"name": "Measure — edge position on a 1-D grey profile (derivative peak)", "family": "2d",
     "task": "measure", "task_class": "measurement", "halcon": "1D Measuring", "input_sort": "image",
     "sample": "step_edge_image",
     "stages": [_R("img_to_signal", 0.5, 0.2), _R("tb_smooth_funct_1d_gauss"), _R("tb_derivate_funct_1d")],
     "expect": [{"get": ["@argmax"], "approx": "edge_col", "atol": 1.0}],
     "note": "Read the centre row as a 1-D function (a=0.5, b<0.5 -> row), Gaussian-smooth it and take the "
             "derivative: the maximum of the derivative is the rising edge's column (px). The funct_1d path "
             "of HALCON."},

    # ---------------------------------------------------------------- 1D Measuring
    {"name": "Measure — sub-pixel edge position along a caliper line", "family": "2d", "task": "measure",
     "task_class": "measurement", "halcon": "1D Measuring", "input_sort": "image", "sample": "step_edge_image",
     "stages": [_R("gaussian", 0.2), _R("m1_measure_pos", 0.0, 0.3)],
     "expect": [{"get": ["cs", 0, 0, 1], "approx": "edge_col", "atol": 0.15}],
     "note": "measure_pos: a horizontal caliper through the image centre (a=0 -> theta 0), edges where the "
             "smoothed profile derivative peaks above 30 % of the strongest (b=0.3), refined to sub-pixel by a "
             "3-point parabola. Output contour points (row, col) in px; the step sits at col 23.5 / 31.5."},
    {"name": "Inspect — count bright bars crossed by a caliper (edge pairs)", "family": "2d", "task": "count",
     "task_class": "inspection", "halcon": "1D Measuring", "input_sort": "image", "sample": "d2_bars",
     "stages": [_R("gaussian", 0.1), _R("m1_measure_pairs", 0.0, 0.3)],
     "expect": [{"get": [], "equals": "count"}],
     "note": "measure_pairs: rising -> falling edge pairs along a horizontal caliper (a=0) = number of bright "
             "objects crossed (pins of a connector, leads of an IC, bars). Truth 3 / 4."},
    {"name": "Measure — count all edges along a caliper line", "family": "2d", "task": "count",
     "task_class": "measurement", "halcon": "1D Measuring", "input_sort": "image", "sample": "d2_bars",
     "stages": [_R("m1_measure_pos", 0.0, 0.3), _R("count_contours")],
     "expect": [{"get": [], "equals": "edges"}],
     "note": "Sub-pixel edge points along the caliper (one contour per edge) counted: 2 edges per bar (6 / 8). "
             "The edge positions themselves are in stage 1's contour (row, col px)."},

    # ---------------------------------------------------------------- XLD
    {"name": "Measure — sub-pixel area of a round part from its iso-contour", "family": "2d", "task": "measure",
     "task_class": "measurement", "halcon": "XLD", "input_sort": "image", "sample": "disk_image",
     "stages": [_R("threshold_sub_pix", 0.5), _R("area_center_xld")],
     "expect": [{"get": [0], "approx": "area", "rtol": 0.01}, {"get": [1], "approx": "row", "atol": 0.3},
                {"get": [2], "approx": "col", "atol": 0.3}],
     "note": "threshold_sub_pix extracts the grey-level 0.45 iso-line (a=0.5) with sub-pixel accuracy (marching "
             "squares); area_center_xld gives the enclosed polygon area (shoelace, px²) and its centroid: "
             "within 1 % of πr², better than pixel counting."},
    {"name": "Measure — maximal diameter of a part from its sub-pixel contour", "family": "2d", "task": "measure",
     "task_class": "measurement", "halcon": "XLD", "input_sort": "image", "sample": "disk_image",
     "stages": [_R("threshold_sub_pix", 0.5), _R("diameter_xld")],
     "expect": [{"get": [], "approx": "diameter", "atol": 1.5}],
     "note": "Largest distance between two contour points (px) of the sub-pixel iso-contour: the disk's "
             "diameter 36 / 48 px (measured +1.1 px)."},
    {"name": "Measure — radius of a round part by an ellipse fit to its sub-pixel edge", "family": "2d",
     "task": "measure", "task_class": "measurement", "halcon": "XLD", "input_sort": "image",
     "sample": "disk_image",
     "stages": [_R("threshold_sub_pix", 0.5), _R("elliptic_axis_xld")],
     "expect": [{"get": [0], "approx": "radius", "rtol": 0.01}, {"get": [1], "approx": "radius", "rtol": 0.01}],
     "note": "Least-squares ellipse fit (cv2.fitEllipse) to the iso-contour; for a round part both semi-axes "
             "are the radius in px (18 / 24), their difference is an ovality measure. There is no circle-fit op "
             "that returns the radius (see MISSING_OPS)."},
    {"name": "Measure — angle of a straight edge by a sub-pixel line fit", "family": "2d", "task": "measure",
     "task_class": "measurement", "halcon": "XLD", "input_sort": "image", "sample": "d2_tilted_edge",
     "stages": [_R("gaussian", 0.2), _R("edges_sub_pix", 0.3), _R("fit_line_contours"), _R("xg_orientation")],
     "expect": [{"get": [], "approx": "orient01_rowdown", "atol": 0.005}],
     "note": "Sub-pixel edge points (gradient threshold 0.3 -> 0.30), total-least-squares line fit, then the "
             "line's orientation scaled to [0,1) (x 180 = degrees, measured in (row, col) coordinates, i.e. "
             "(180 - theta) for an edge turned theta counter-clockwise on screen). Truth 15 / 35 deg."},
    {"name": "Measure — orientation of a bar from its sub-pixel outline", "family": "2d", "task": "measure",
     "task_class": "measurement", "halcon": "XLD", "input_sort": "image", "sample": "d2_bar",
     "stages": [_R("threshold_sub_pix", 0.5), _R("xg_orientation")],
     "expect": [{"get": [], "approx": "orient01_rowdown", "atol": 0.006}],
     "note": "Principal axis of the bar's iso-contour points (PCA), folded to [0,1) (x 180 = degrees, row-down "
             "convention: 180 - 20 and 180 - 45 deg). orientation_xld was dropped (see FAILED_ATTEMPTS)."},

    # ---------------------------------------------------------------- Subpix
    {"name": "Measure — sub-pixel centre of a laser spot / fiducial dot", "family": "2d", "task": "measure",
     "task_class": "measurement", "halcon": "Filters", "input_sort": "image", "sample": "d2_subpix_spot",
     "stages": [_R("xsp_savgol", 0.3), _R("sp_local_max_sub_pix", 0.2)],
     "expect": [{"get": ["cs", 0, 0, 0], "approx": "row", "atol": 0.02},
                {"get": ["cs", 0, 0, 1], "approx": "col", "atol": 0.02}],
     "note": "Savitzky-Golay smoothing (a=0.3 -> window 7, order 2, keeps the peak shape) then a 2-D quadratic "
             "fit around each local maximum deeper than 0.07 (a=0.2) gives the spot centre (row, col) to "
             "<0.01 px. Truth (40.3, 52.7) / (49.7, 41.5)."},

    # ---------------------------------------------------------------- Matching
    {"name": "Locate — find a fiducial mark by normalized cross-correlation", "family": "2d", "task": "locate",
     "task_class": "inspection", "halcon": "Matching", "input_sort": "image", "sample": "d2_fiducial_shift",
     "stages": [_R("gaussian", 0.1), _R("ncc_locate")],
     "expect": [{"get": [1], "approx": "row", "atol": 0.5}, {"get": [2], "approx": "col", "atol": 0.5},
                {"get": [0], "between": [0.9, 1.0]}],
     "note": "NCC template matching (find_ncc_model): returns [score, row, col] of the template centre (px). The "
             "template is registered on this thread by the sample (ops.set_match_template), as the matching "
             "ops require. Gaussian (sigma 0.57 px) against sensor noise sigma 0.05."},
    {"name": "Locate — find a rotated part and its angle (shape-based matching)", "family": "2d",
     "task": "locate", "task_class": "inspection", "halcon": "Matching", "input_sort": "image",
     "sample": "d2_fiducial_scene",
     "stages": [_R("gaussian", 0.1), _R("shape_locate")],
     "expect": [{"get": [1], "approx": "row", "atol": 0.5}, {"get": [2], "approx": "col", "atol": 0.5},
                {"get": [3], "approx": "angle", "atol": 1.0}],
     "note": "Rotation-searching matching (find_shape_model-like): the template is tried at 0..330 deg in 30 "
             "deg steps; returns [score, row, col, angle deg]. Truth: the mark at 0 deg / turned 90 deg. Angle "
             "resolution is the 30 deg step — coarse orientation only."},

    # ---------------------------------------------------------------- Color
    {"name": "Inspect — segment a coloured part by saturation (HSV)", "family": "2d", "task": "segment",
     "task_class": "inspection", "halcon": "Color", "input_sort": "color", "sample": "d2_color_parts",
     "stages": [_R("trans_from_rgb", 0.0), _R("access_channel", 0.4), _R("threshold", 0.3), _R("area_center")],
     "expect": [{"get": [0], "approx": "area", "rtol": 0.01}, {"get": [1], "approx": "row", "atol": 0.5}],
     "note": "RGB -> HSV (a=0), take the saturation channel (a=0.4 -> channel 1) and threshold it at 0.3: the "
             "blue part is kept, the grey tray and a grey decoy of the same luminance are rejected (on the "
             "luminance image a grey threshold cannot separate them). Area px² and centroid row."},
    {"name": "Inspect — pick a blue part by its colour channel", "family": "2d", "task": "segment",
     "task_class": "inspection", "halcon": "Color", "input_sort": "color", "sample": "d2_color_parts",
     "stages": [_R("access_channel", 0.9), _R("threshold", 0.6), _R("area_center")],
     "expect": [{"get": [0], "approx": "area", "rtol": 0.01}],
     "note": "Channel selection: the blue channel (a=0.9 -> channel 2) thresholded at 0.6 keeps only the blue "
             "part (B = 0.8, grey 0.45 / 0.29). Area in px²."},

    # ---------------------------------------------------------------- Transformations
    {"name": "Preprocess — rotate an image by a known angle and check the part angle", "family": "2d",
     "task": "transform", "task_class": "preprocess", "halcon": "Transformations", "input_sort": "image",
     "sample": "d2_bar",
     "stages": [_R("rotate_img", 0.5 + 15.0 / 90.0), _R("otsu"), _R("orientation_region")],
     "expect": [{"get": [], "approx": "orient01_rot15", "atol": 0.006}],
     "note": "rotate_img turns the image about its centre by -45 + 90·a deg (a = 0.667 -> +15 deg, "
             "counter-clockwise on screen); the bar's measured orientation must move by the same 15 deg "
             "(truth (theta + 15) / 180). A check of an alignment / deskew step."},
    {"name": "Preprocess — zoom about the centre and verify the area scale", "family": "2d", "task": "transform",
     "task_class": "preprocess", "halcon": "Transformations", "input_sort": "image", "sample": "d2_part_disk",
     "stages": [_R("zoom_image_factor", 0.75, 0.75), _R("otsu"), _R("area_center")],
     "expect": [{"get": [0], "approx": "area_zoom", "rtol": 0.02}],
     "note": "zoom_image_factor scales rows by 0.7 + 0.6·a and columns by 0.7 + 0.6·b about the centre (a = b = "
             "0.75 -> 1.15 x); the part area must grow by 1.15² (canvas unchanged)."},
    {"name": "Preprocess — mirror an image upside down (row flip)", "family": "2d", "task": "transform",
     "task_class": "preprocess", "halcon": "Transformations", "input_sort": "image", "sample": "d2_part_disk",
     "stages": [_R("mirror_image", 0.1), _R("otsu"), _R("area_center")],
     "expect": [{"get": [1], "approx": "row_flip", "atol": 0.5}, {"get": [2], "approx": "col", "atol": 0.5}],
     "note": "mirror_image with a=0.1 flips the rows (row -> H-1-row; a=0.9 transposes instead, measured), the "
             "column stays. For camera mounted upside down / mirror optics."},
    {"name": "Measure — ring radius by polar unwrapping", "family": "2d", "task": "measure",
     "task_class": "measurement", "halcon": "Transformations", "input_sort": "image", "sample": "d2_ring",
     "stages": [_R("polar_trans_image"), _R("img_to_projection_profile", 0.0, 0.2)],
     "expect": [{"get": ["@argmax"], "approx": "polar_col", "atol": 2.0}],
     "note": "polar_trans_image unwraps about the image centre (columns = radius 0..min(H,W)/2 over W "
             "columns, i.e. 2 columns per px here); averaging over the angle rows gives a radial profile whose "
             "peak column is 2·R (ring radius 20 / 30 px) — O-ring, bore, seal inspection."},

    # ---------------------------------------------------------------- Restoration
    {"name": "Preprocess — inpaint scratch lines before measuring part area", "family": "2d", "task": "restore",
     "task_class": "preprocess", "halcon": "Restoration", "input_sort": "image", "sample": "d2_damaged_disk",
     "stages": [_R("xcv_inpaint"), _R("otsu"), _R("area_center")],
     "expect": [{"get": [0], "approx": "area", "rtol": 0.03}],
     "note": "Saturated white scratch lines (dead columns / reflections) add +45 % to an Otsu area. Telea "
             "inpainting fills the saturated (>235/255) pixels from their surroundings, then the part area "
             "(px²) is back within 3 % of πr²."},
    {"name": "Preprocess — Richardson-Lucy deblur of a defocused part, then measure", "family": "2d",
     "task": "restore", "task_class": "preprocess", "halcon": "Restoration", "input_sort": "image",
     "sample": "d2_blurred_disk",
     "stages": [_R("iv_richardson_lucy", 0.6), _R("otsu"), _R("area_center")],
     "expect": [{"get": [0], "approx": "area", "rtol": 0.03}],
     "note": "Richardson-Lucy deconvolution with a small Gaussian PSF (a=0.6 -> 9 iterations) sharpens a "
             "defocused image (Gaussian blur sigma 2 px); the deblurred part still binarizes to its true area "
             "(px², πr²)."},

    # ---------------------------------------------------------------- Frequency
    {"name": "Preprocess — suppress periodic interference stripes with an FFT low-pass", "family": "2d",
     "task": "filter", "task_class": "preprocess", "halcon": "Frequency", "input_sort": "image",
     "sample": "d2_striped_disk",
     "stages": [_R("lowpass", 0.3), _R("otsu"), _R("area_center")],
     "expect": [{"get": [0], "approx": "area", "rtol": 0.03}],
     "note": "Strong diagonal stripes (period 4 px: moire / mains interference) make Otsu return 3x the part "
             "area. An ideal FFT low-pass (a=0.3 -> cutoff 0.17 cycles/px) removes the stripe frequency "
             "(0.35 cycles/px) and keeps the part, whose area (px²) is then within 3 %."},

    # ---------------------------------------------------------------- Texture
    {"name": "Measure — period of a stripe texture by zero crossings", "family": "2d", "task": "measure",
     "task_class": "measurement", "halcon": "Texture", "input_sort": "image", "sample": "d2_stripes",
     "stages": [_R("img_to_projection_profile", 0.0, 0.2), _R("tb_stat_zscore"), _R("tb_zero_crossings_funct_1d"),
                _R("tb_num_points_funct_1d")],
     "expect": [{"get": [], "approx": "crossings", "atol": 1.5}],
     "note": "Grating / fabric / knurl pitch: column-average projection profile, z-score it, find the sign "
             "changes and count them. 2·W / period crossings (24 / 16 for period 8 / 12 px over 96 px); the "
             "period is 2·W / count."},
    {"name": "Measure — direction of a grating or brushed texture (structure tensor)", "family": "2d",
     "task": "measure", "task_class": "measurement", "halcon": "Texture", "input_sort": "image",
     "sample": "d2_tilted_stripes",
     "stages": [_R("gaussian", 0.05), _R("structure_tensor_orientation", 0.3, 0.5)],
     "expect": [{"get": ["@median"], "approx": "orient01_rowdown", "atol": 0.015}],
     "note": "Structure tensor (a=0.3 -> derivative sigma 1.25 px, b=0.5 -> integration rho 4.5 px) gives the "
             "local stripe direction in [0,1] (0 and 1 horizontal, 0.5 vertical; x 180 = degrees, measured in "
             "row-down coordinates: 180 - theta). Median over the image; truth 30 / 60 deg (fibre / polishing "
             "direction)."},

    # ---------------------------------------------------------------- Inspection
    {"name": "Inspect — length of a dark scratch on brushed metal", "family": "2d", "task": "inspect",
     "task_class": "inspection", "halcon": "Inspection", "input_sort": "image", "sample": "d2_scratch_on_texture",
     "stages": [_R("bothat", 0.5), _R("threshold", 0.5), _R("select_largest"), _R("diameter_region")],
     "expect": [{"get": [], "approx": "length", "atol": 1.5}],
     "note": "Black top-hat (a=0.5 -> 7x7) lifts a 2 px dark scratch above the fine surface noise, threshold 0.5 "
             "of the normalised response, keep the largest defect and report its length (max diameter, px; "
             "truth 40 / 60). A median filter before the top-hat erases the scratch (measured)."},
    {"name": "Inspect — dark contamination spots on a woven fabric", "family": "2d", "task": "inspect",
     "task_class": "inspection", "halcon": "Inspection", "input_sort": "image", "sample": "d2_spot_on_fabric",
     "stages": [_R("lowpass", 0.1), _R("bothat", 0.9), _R("threshold", 0.5), _R("count_obj")],
     "expect": [{"get": [], "equals": "count"}],
     "note": "Periodic weave (period 6 px) hides small spots from any global threshold. An FFT low-pass "
             "(a=0.1 -> cutoff 0.09 cycles/px) removes the weave frequency (0.17), a 9x9 black top-hat (a=0.9) "
             "isolates the dark spots, threshold and count (1 / 3)."},

    # ---------------------------------------------------------------- Identification / OCR
    {"name": "Identify — count the bars of a 1-D barcode", "family": "2d", "task": "identify",
     "task_class": "inspection", "halcon": "Identification", "input_sort": "image", "sample": "d2_barcode",
     "stages": [_R("bilateral", 0.2, 0.3), _R("decode_barcode", 0.5)],
     "expect": [{"get": [], "equals": "bars"}],
     "note": "Edge-preserving bilateral smoothing (sigma_s 1.6 px, sigma_r 0.17) keeps the 2 px bars while "
             "flattening print noise (a median erases them, measured); decode_barcode counts dark bars on the "
             "centre scan line (a=0.5 -> dark below 0.5). It does NOT decode symbols (see MISSING_OPS)."},
    {"name": "Preprocess — segment dark characters on shaded paper for OCR", "family": "2d", "task": "segment",
     "task_class": "preprocess", "halcon": "OCR", "input_sort": "image", "sample": "d2_text_line",
     "stages": [_R("hx_char_threshold", 0.5), _R("count_obj")],
     "expect": [{"get": [], "equals": "glyphs"}],
     "note": "char_threshold-style global threshold mean - k·std (a=0.5 -> k = 1.1) selects dark glyphs that are "
             "a minority on bright paper even with a 0.25 shading ramp; count_obj gives the number of "
             "character blobs (5 / 7) — the segmentation step before OCR classification."},
    # ---------------------------------------------------------------- two-input (n-ary) stages
    # These carry "args" (a second input from the sample's aux), so they run through the python
    # runner (api.apply([x0, x1], op, a, b)); MCP's single-input pipeline cannot chain them.
    {"name": "Inspect — defects by golden-template difference against a good part", "family": "2d",
     "task": "inspect", "task_class": "inspection", "halcon": "Inspection", "input_sort": "image",
     "sample": "d2_golden_pair",
     "stages": [{"op": "abs_diff_image", "args": ["$prev", "$aux.golden"], "a": 1.0 / 3.0, "b": 0.5},
                _R("threshold", 0.2), _R("opening_circle", 0.1), _R("count_obj")],
     "expect": [{"get": [], "equals": "defects"}],
     "note": "Golden-template (reference image) comparison: |test - golden| with gain 0.5 + 1.5·a = 1.0 "
             "(a = 1/3), threshold at 0.2 grey (above the sensor noise of both images, below the 0.35 defect "
             "contrast), a radius-1 opening removes isolated noise pixels, count the defects (pits / missing "
             "print, 2 / 3). The part itself is textured (checker print), so a global threshold of the test image "
             "returns one region (the whole part)."},
    {"name": "Preprocess — flat-field correction by dividing by a white reference", "family": "2d",
     "task": "correct", "task_class": "preprocess", "halcon": "Filters", "input_sort": "image",
     "sample": "d2_flatfield_pair",
     "stages": [{"op": "div_image", "args": ["$prev", "$aux.flat"], "a": 0.5, "b": 0.5},
                _R("otsu"), _R("area_center")],
     "expect": [{"get": [0], "approx": "area", "rtol": 0.02}],
     "note": "Shading / vignetting correction with a flat-field frame (image of a uniform white target): "
             "test / flat x (0.1 + 0.9·a) = 0.55 restores the reflectance, then a global Otsu threshold gives "
             "the total part area in px² (5 / 7 disks of r 6 = 565 / 791 px²). On the raw image Otsu cuts the "
             "bright centre background instead (3207 / 2325 px², measured)."},
    {"name": "Preprocess — subtract a background frame, then measure the part area", "family": "2d",
     "task": "correct", "task_class": "preprocess", "halcon": "Filters", "input_sort": "image",
     "sample": "d2_background_pair",
     "stages": [{"op": "sub_image", "args": ["$prev", "$aux.background"], "a": 0.5, "b": 0.0},
                _R("threshold", 0.2), _R("area_center")],
     "expect": [{"get": [0], "approx": "area", "rtol": 0.02}, {"get": [1], "approx": "row", "atol": 0.5}],
     "note": "Background subtraction: the empty-scene frame (fixture, shadows, stray-light pattern) is "
             "subtracted, (test - background) x (0.5 + a) + b with a = 0.5, b = 0, so only the added part "
             "remains; threshold 0.2 and area_center (px², centroid row). Truth: disk r 14 / 20 px."},
    {"name": "Inspect — missing material against the nominal shape (region difference)", "family": "2d",
     "task": "inspect", "task_class": "inspection", "halcon": "Regions", "input_sort": "image",
     "sample": "d2_chipped_part",
     "stages": [_R("otsu"), {"op": "difference", "args": ["$aux.nominal", "$prev"], "a": 0.5, "b": 0.5},
                _R("area_center")],
     "expect": [{"get": [0], "approx": "missing_area", "rtol": 0.05}],
     "note": "Compare a part with its nominal (CAD / taught) region: nominal minus the segmented part leaves "
             "the missing material (chip, broken edge); its area in px² (truth = pixels of the bite, 51 / 116). "
             "Order matters: difference(nominal, part)."},
]


# ---- samples (synthetic scenes with a closed-form truth) --------------------------------------------
def _rng(variant, salt):
    return np.random.default_rng(2000 + 31 * int(variant) + int(salt))


def _grid(n=N):
    return np.mgrid[0:n, 0:n].astype(float)


def _disk(yy, xx, cy, cx, r):
    return ((yy - cy) ** 2 + (xx - cx) ** 2) <= r * r


def _scene(mask, variant, salt, lo=0.1, hi=0.9, noise=0.01):
    img = lo + (hi - lo) * mask + noise * _rng(variant, salt).standard_normal(mask.shape)
    return np.clip(img, 0, 1)


def d2_saltpepper_disk(variant):
    """Bright disk (r = 16 + 6·variant) hit by 5 % salt-and-pepper impulses."""
    r = 16.0 + 6.0 * variant
    yy, xx = _grid()
    img = 0.2 + 0.6 * _disk(yy, xx, 48, 48, r)
    m = _rng(variant, 1).random(img.shape)
    img = np.where(m < 0.025, 0.0, np.where(m > 0.975, 1.0, img))
    return {"value": img, "aux": {}, "truth": {"area": float(np.pi * r * r), "radius": r, "row": 48.0}}


def d2_flat_noise(variant):
    """Flat grey 0.5 with white Gaussian noise of sigma = 0.02 + 0.03·variant."""
    s = 0.02 + 0.03 * variant
    img = 0.5 + s * _rng(variant, 2).standard_normal((N, N))
    return {"value": img, "aux": {}, "truth": {"sigma": s, "sigma_half": 0.5 * s}}


def d2_shaded_blobs(variant):
    """k = 4 + 2·variant small bright disks (r 5) on a strong left-to-right illumination ramp."""
    k = 4 + 2 * int(variant)
    yy, xx = _grid()
    img = 0.1 + 0.6 * xx / (N - 1)
    for i in range(k):
        cy, cx = 16 + 32 * (i % 3), 12 + 18 * (i // 3) + (i % 3) * 4
        img = img + 0.25 * _disk(yy, xx, cy, cx, 5)
    img = img + 0.01 * _rng(variant, 3).standard_normal(img.shape)
    return {"value": np.clip(img, 0, 1), "aux": {}, "truth": {"count": k}}


def d2_touching_disks(variant):
    """Pairs of overlapping disks (r = 10, centre spacing 16); 2 + variant pairs -> 2·pairs disks."""
    p = 2 + int(variant)
    yy, xx = _grid()
    m = np.zeros((N, N), bool)
    for i in range(p):
        cy = 18 + 30 * i if p < 3 else 16 + 30 * i
        m |= _disk(yy, xx, cy, 30, 10) | _disk(yy, xx, cy, 46, 10)
    return {"value": _scene(m, variant, 4, 0.15, 0.85), "aux": {}, "truth": {"count": 2 * p, "pairs": p}}


def d2_washer(variant):
    """Washer: disk r_out = 34 with a concentric hole r_in = 10 + 6·variant."""
    ro, ri = 34.0, 10.0 + 6.0 * variant
    yy, xx = _grid()
    m = _disk(yy, xx, 48, 48, ro) & ~_disk(yy, xx, 48, 48, ri)
    return {"value": _scene(m, variant, 5), "aux": {},
            "truth": {"hole_area": float(np.pi * ri * ri), "hole_frac": (ri / ro) ** 2, "r_in": ri, "r_out": ro}}


def d2_plate_holes(variant):
    """Rectangular plate with k = 2 + variant punched round holes (r = 6); Euler number 1 - k."""
    k = 2 + int(variant)
    yy, xx = _grid()
    m = (yy >= 16) & (yy < 80) & (xx >= 10) & (xx < 86)
    for i in range(k):
        m &= ~_disk(yy, xx, 48, 24 + 22 * i, 6)
    return {"value": _scene(m, variant, 6), "aux": {}, "truth": {"holes": k, "euler": 1 - k}}


def _bar_mask(theta_deg, length, width, cy=48.0, cx=48.0):
    """Rectangle turned theta counter-clockwise on screen (rows point down)."""
    yy, xx = _grid()
    t = np.radians(theta_deg)
    u = (xx - cx) * np.cos(t) - (yy - cy) * np.sin(t)
    v = (xx - cx) * np.sin(t) + (yy - cy) * np.cos(t)
    return (np.abs(u) <= length / 2) & (np.abs(v) <= width / 2)


def d2_bar(variant):
    """Bright bar 64 x (10 + 4·variant) px turned theta = 20 + 25·variant deg counter-clockwise."""
    th, w = 20.0 + 25.0 * variant, 10.0 + 4.0 * variant
    m = _bar_mask(th, 64.0, w)
    return {"value": _scene(m, variant, 7), "aux": {},
            "truth": {"theta_deg": th, "orient01": th / 180.0, "orient01_rot15": (th + 15.0) / 180.0,
                      "orient01_rowdown": (180.0 - th) / 180.0, "length": 64.0, "width": w}}


def d2_ellipse(variant):
    """Axis-aligned ellipse with semi-axes Ra = 32, Rb = 12 + 6·variant."""
    ra, rb = 32.0, 12.0 + 6.0 * variant
    yy, xx = _grid()
    m = ((xx - 48) / ra) ** 2 + ((yy - 48) / rb) ** 2 <= 1
    return {"value": _scene(m, variant, 8), "aux": {}, "truth": {"ra": ra, "rb": rb, "anisometry": ra / rb}}


def d2_sizes(variant):
    """Five disks of different sizes; the largest (r = 12 + 5·variant) sits at (30, 30)."""
    yy, xx = _grid()
    big = _disk(yy, xx, 30, 30, 12.0 + 5.0 * variant)
    m = big.copy()
    for (cy, cx, r) in ((20, 75, 6), (75, 20, 7), (75, 75, 8), (50, 70, 4)):
        m |= _disk(yy, xx, cy, cx, r)
    return {"value": _scene(m, variant, 9), "aux": {}, "truth": {"area": float(big.sum()), "row": 30.0, "col": 30.0}}


def d2_specks(variant):
    """k = 2 + variant real parts (r = 10) plus up to 40 one-to-two-pixel dust specks."""
    k = 2 + int(variant)
    yy, xx = _grid()
    m = np.zeros((N, N), bool)
    for i in range(k):
        m |= _disk(yy, xx, 24 + 24 * (i % 3), 24 + 48 * (i // 3), 10)
    g = _rng(variant, 10)
    for _ in range(40):
        y, x = g.integers(2, N - 3, 2)
        if not m[max(0, y - 13):y + 13, max(0, x - 13):x + 13].any():
            m[y:y + g.integers(1, 3), x:x + g.integers(1, 3)] = True
    img = 0.1 + 0.8 * m + 0.01 * g.standard_normal(m.shape)
    return {"value": np.clip(img, 0, 1), "aux": {}, "truth": {"count": k}}


def d2_cshape(variant):
    """C-clip: ring r 18..30 with an open gap of g = 60 + 40·variant deg; hull = πR² - R²/2 (g - sin g)."""
    yy, xx = _grid()
    gap = np.radians(60.0 + 40.0 * variant)
    ang = np.arctan2(yy - 48, xx - 48)
    m = _disk(yy, xx, 48, 48, 30) & ~_disk(yy, xx, 48, 48, 18) & (np.abs(ang) > gap / 2)
    hull = float(np.pi * 900 - 900 / 2 * (gap - np.sin(gap)))
    return {"value": _scene(m, variant, 11), "aux": {},
            "truth": {"part_area": float(m.sum()), "hull_area": hull, "convexity": float(m.sum()) / hull}}


def d2_thin_line(variant):
    """Bright horizontal line 3 px wide, length 50 + 20·variant px."""
    L = 50 + 20 * int(variant)
    m = np.zeros((N, N), bool)
    c0 = (N - L) // 2
    m[47:50, c0:c0 + L] = True
    return {"value": _scene(m, variant, 12, 0.15, 0.85), "aux": {}, "truth": {"length": float(L)}}


def d2_star(variant):
    """Star-shaped bracket: m = 3 + variant straight arms (6 px wide, 34 px long) from one hub."""
    m_arms = 3 + int(variant)
    yy, xx = _grid()
    msk = _disk(yy, xx, 48, 48, 5)
    for i in range(m_arms):
        t = 2 * np.pi * i / m_arms + 0.3
        u = (xx - 48) * np.cos(t) + (yy - 48) * np.sin(t)
        w = -(xx - 48) * np.sin(t) + (yy - 48) * np.cos(t)
        msk |= (u >= 0) & (u <= 34) & (np.abs(w) <= 3)
    return {"value": _scene(msk, variant, 27), "aux": {}, "truth": {"arms": m_arms}}


def d2_spots_on_shading(variant):
    """k = 3 + 2·variant small bright spots (3x3 px) on a smooth uneven (vignetted) background."""
    k = 3 + 2 * int(variant)
    yy, xx = _grid()
    img = 0.3 + 0.35 * np.exp(-((yy - 30) ** 2 + (xx - 60) ** 2) / (2 * 35.0 ** 2))
    for i in range(k):
        y, x = 12 + 17 * i, 14 + (i * 29) % 68
        img[y - 1:y + 2, x - 1:x + 2] += 0.25
    img = img + 0.005 * _rng(variant, 13).standard_normal(img.shape)
    return {"value": np.clip(img, 0, 1), "aux": {}, "truth": {"count": k}}


def d2_dark_pits(variant):
    """k = 2 + 2·variant dark pits (5x5 px) on a bright, slightly ramped surface."""
    k = 2 + 2 * int(variant)
    yy, xx = _grid()
    img = 0.7 + 0.15 * yy / (N - 1)
    for i in range(k):
        y, x = 14 + 22 * (i % 4), 20 + 40 * (i // 4) + 8 * (i % 2)
        img[y - 2:y + 3, x - 2:x + 3] -= 0.35
    img = img + 0.005 * _rng(variant, 14).standard_normal(img.shape)
    return {"value": np.clip(img, 0, 1), "aux": {}, "truth": {"count": k}}


def d2_squares(variant):
    """k = 2 + variant bright axis-aligned squares (14 px); 4 corners each."""
    k = 2 + int(variant)
    m = np.zeros((N, N), bool)
    for i in range(k):
        y, x = 12 + 40 * (i % 2), 10 + 30 * (i // 2) + 10 * (i % 2)
        m[y:y + 14, x:x + 14] = True
    return {"value": _scene(m, variant, 28, 0.15, 0.85), "aux": {}, "truth": {"corners": 4 * k, "count": k}}


def d2_bars(variant):
    """k = 3 + variant bright vertical bars (6 px wide) on a dark background."""
    k = 3 + int(variant)
    m = np.zeros((N, N), bool)
    pitch = N // (k + 1)
    for i in range(1, k + 1):
        m[:, i * pitch - 3:i * pitch + 3] = True
    return {"value": _scene(m, variant, 15, 0.15, 0.85), "aux": {}, "truth": {"count": k, "edges": 2 * k}}


def d2_tilted_edge(variant):
    """Straight dark/bright edge through the centre, turned theta = 15 + 20·variant deg counter-clockwise."""
    th = np.radians(15.0 + 20.0 * variant)
    yy, xx = _grid()
    side = (xx - 48) * np.sin(th) + (yy - 48) * np.cos(th)
    deg = float(np.degrees(th))
    return {"value": _scene(side > 0, variant, 30, 0.2, 0.8), "aux": {},
            "truth": {"theta_deg": deg, "orient01_rowdown": (180.0 - deg) / 180.0}}


def d2_subpix_spot(variant):
    """Gaussian spot (sigma 2.5 px) at the sub-pixel centre (40.3 + 9.4v, 52.7 - 11.2v)."""
    cy, cx = 40.3 + 9.4 * variant, 52.7 - 11.2 * variant
    yy, xx = _grid()
    img = 0.1 + 0.8 * np.exp(-((yy - cy) ** 2 + (xx - cx) ** 2) / (2 * 2.5 ** 2))
    return {"value": img, "aux": {}, "truth": {"row": cy, "col": cx}}


def _mark(n=17):
    """Asymmetric fiducial (T-like bars + a grey corner square) so every 90 deg turn differs."""
    t = np.zeros((n, n))
    t[n // 2 - 2:n // 2 + 3, 2:n - 2] = 1.0
    t[2:n - 2, n // 2 - 4:n // 2 - 1] = 1.0
    t[2:6, 2:6] = 0.6
    return 0.1 + 0.8 * t


def d2_fiducial_shift(variant):
    """Search image with the 17x17 fiducial (never rotated) centred at (24 + 34v, 30 + 30v), noise 0.05.

    The matching ops read their model from a thread-local context, so the sample registers the
    template here (``ops.set_match_template``), on the thread that then runs the recipe."""
    import ops as _ops
    T = _mark()
    img = 0.1 + 0.05 * _rng(variant, 20).standard_normal((N, N))
    y0, x0 = 16 + 34 * variant, 22 + 30 * variant
    img[y0:y0 + 17, x0:x0 + 17] += T - 0.1
    _ops.set_match_template(T)
    return {"value": img, "aux": {"template": T}, "truth": {"row": float(y0 + 8), "col": float(x0 + 8)}}


def d2_fiducial_scene(variant):
    """The fiducial centred at (28 + 30v, 38 + 25v); variant 1 turns it by 90 deg (np.rot90)."""
    import ops as _ops
    T = _mark()
    img = 0.1 + 0.02 * _rng(variant, 19).standard_normal((N, N))
    y0, x0 = 20 + 30 * variant, 30 + 25 * variant
    img[y0:y0 + 17, x0:x0 + 17] = np.rot90(T, k=int(variant))
    _ops.set_match_template(T)
    return {"value": img, "aux": {"template": T},
            "truth": {"row": float(y0 + 8), "col": float(x0 + 8), "angle": 90.0 * variant}}


def d2_color_parts(variant):
    """Grey tray (0.45) with a blue part (r = 12 + 5·variant) and a same-luminance grey decoy disk."""
    yy, xx = _grid()
    img = np.full((N, N, 3), 0.45)
    blue = _disk(yy, xx, 32, 34, 12.0 + 5.0 * variant)
    img[blue] = (0.1, 0.3, 0.8)
    img[_disk(yy, xx, 72, 70, 12)] = (0.29, 0.29, 0.29)
    img = np.clip(img + 0.01 * _rng(variant, 18).standard_normal(img.shape), 0, 1)
    return {"value": img, "aux": {}, "truth": {"area": float(blue.sum()), "row": 32.0, "col": 34.0}}


def d2_part_disk(variant):
    """Off-centre disk r = 14 + 4·variant at (40 + 6v, 36 + 8v); truths for zoom (1.15 x) and row flip."""
    r, cy, cx = 14.0 + 4.0 * variant, 40.0 + 6.0 * variant, 36.0 + 8.0 * variant
    yy, xx = _grid()
    m = _disk(yy, xx, cy, cx, r)
    area = float(m.sum())
    return {"value": _scene(m, variant, 31), "aux": {},
            "truth": {"area": area, "area_zoom": area * 1.15 ** 2, "row": cy, "col": cx,
                      "row_flip": (N - 1) - cy}}


def d2_ring(variant):
    """Thin bright ring (2 px wide) of radius 20 + 10·variant about the image centre."""
    R = 20.0 + 10.0 * variant
    yy, xx = _grid()
    m = np.abs(np.hypot(yy - N / 2, xx - N / 2) - R) <= 1.0
    return {"value": _scene(m, variant, 16), "aux": {}, "truth": {"radius": R, "polar_col": 2.0 * R}}


def d2_damaged_disk(variant):
    """Disk r = 18 + 6·variant (0.6 on 0.3) crossed by three saturated white scratch columns."""
    r = 18.0 + 6.0 * variant
    yy, xx = _grid()
    img = 0.3 + 0.3 * _disk(yy, xx, 48, 48, r)
    for c in (30, 47, 64):
        img[:, c:c + 2] = 1.0
    img = img + 0.005 * _rng(variant, 22).standard_normal(img.shape)
    return {"value": np.clip(img, 0, 1), "aux": {}, "truth": {"area": float(np.pi * r * r)}}


def d2_blurred_disk(variant):
    """Disk r = 16 + 6·variant blurred by a Gaussian PSF sigma 2 px (defocus) plus mild noise."""
    from scipy.ndimage import gaussian_filter
    r = 16.0 + 6.0 * variant
    yy, xx = _grid()
    img = gaussian_filter(0.15 + 0.7 * _disk(yy, xx, 48, 48, r).astype(float), 2.0)
    img = img + 0.005 * _rng(variant, 21).standard_normal(img.shape)
    return {"value": np.clip(img, 0, 1), "aux": {}, "truth": {"area": float(np.pi * r * r)}}


def d2_striped_disk(variant):
    """Disk r = 16 + 6·variant under strong diagonal interference stripes (period 4 px along x and y)."""
    r = 16.0 + 6.0 * variant
    yy, xx = _grid()
    img = 0.3 + 0.35 * _disk(yy, xx, 48, 48, r) + 0.18 * np.sin(2 * np.pi * (xx + yy) / 4.0)
    return {"value": np.clip(img, 0, 1), "aux": {}, "truth": {"area": float(np.pi * r * r)}}


def d2_stripes(variant):
    """Vertical sinusoidal stripes of period 8 + 4·variant px (grating / fabric / knurl)."""
    p = 8.0 + 4.0 * variant
    yy, xx = _grid()
    img = 0.5 + 0.35 * np.sin(2 * np.pi * (xx + 0.3) / p) + 0.01 * _rng(variant, 17).standard_normal((N, N))
    return {"value": img, "aux": {}, "truth": {"period": p, "crossings": 2 * N / p}}


def d2_tilted_stripes(variant):
    """Grating (period 8 px) whose stripes run at theta = 30 + 30·variant deg counter-clockwise."""
    th = np.radians(30.0 + 30.0 * variant)
    yy, xx = _grid()
    phase = (xx - 48) * np.sin(th) + (yy - 48) * np.cos(th)
    img = 0.5 + 0.35 * np.sin(2 * np.pi * phase / 8.0) + 0.01 * _rng(variant, 29).standard_normal((N, N))
    deg = float(np.degrees(th))
    return {"value": img, "aux": {}, "truth": {"theta_deg": deg, "orient01_rowdown": (180.0 - deg) / 180.0}}


def d2_scratch_on_texture(variant):
    """Brushed-metal-like fine noise (sigma 0.03) with one dark 2 px scratch, length 40 + 20·variant px."""
    L = 40 + 20 * int(variant)
    img = 0.6 + 0.03 * _rng(variant, 25).standard_normal((N, N))
    r0, c0 = 30 + 10 * variant, (N - L) // 2
    img[r0:r0 + 2, c0:c0 + L] -= 0.3
    return {"value": np.clip(img, 0, 1), "aux": {}, "truth": {"length": float(L)}}


def d2_spot_on_fabric(variant):
    """Woven texture (period 6 px in x and y) with k = 1 + 2·variant dark contamination spots (r = 3)."""
    k = 1 + 2 * int(variant)
    yy, xx = _grid()
    img = 0.5 + 0.2 * np.sin(2 * np.pi * xx / 6.0) * np.sin(2 * np.pi * yy / 6.0)
    for i in range(k):
        img[_disk(yy, xx, 20 + 25 * i, 24 + 22 * i, 3)] = 0.05
    img = img + 0.01 * _rng(variant, 26).standard_normal(img.shape)
    return {"value": np.clip(img, 0, 1), "aux": {}, "truth": {"count": k}}


def d2_barcode(variant):
    """1-D barcode: k = 9 + 4·variant dark bars of width 2 or 4 px on white, with print noise 0.04."""
    k = 9 + 4 * int(variant)
    img = np.full((N, N), 0.9)
    g = _rng(variant, 23)
    c = 8
    for _ in range(k):
        w = 2 if g.random() < 0.5 else 4
        img[20:76, c:c + w] = 0.1
        c += w + (2 if g.random() < 0.5 else 3)
    img = img + 0.04 * g.standard_normal(img.shape)
    return {"value": np.clip(img, 0, 1), "aux": {}, "truth": {"bars": k}}


def d2_text_line(variant):
    """OCR line: k = 5 + 2·variant dark glyph blocks (7x11 px, each with a counter hole) on shaded paper."""
    k = 5 + 2 * int(variant)
    yy, xx = _grid()
    img = 0.85 - 0.25 * xx / (N - 1)
    for i in range(k):
        x0 = 6 + 12 * i
        img[40:51, x0:x0 + 7] = 0.12
        img[43:47, x0 + 2:x0 + 5] = img[43, 0]
    img = img + 0.01 * _rng(variant, 24).standard_normal(img.shape)
    return {"value": np.clip(img, 0, 1), "aux": {}, "truth": {"glyphs": k}}


def _textured_part():
    """A printed part with fine structure (pattern of bright / dark squares) on a dark tray."""
    yy, xx = _grid()
    img = np.full((N, N), 0.15)
    inside = (yy >= 16) & (yy < 80) & (xx >= 16) & (xx < 80)
    img[inside] = 0.55 + 0.25 * (((yy[inside] // 4) + (xx[inside] // 4)) % 2)
    return img


def d2_golden_pair(variant):
    """Test image = golden (defect-free) part + k = 2 + variant dark pits (5x5, -0.35); fresh noise each."""
    k = 2 + int(variant)
    base = _textured_part()
    golden = np.clip(base + 0.01 * _rng(variant, 40).standard_normal(base.shape), 0, 1)
    test = base.copy()
    for i in range(k):
        y, x = 24 + 20 * i, 28 + 14 * i
        test[y:y + 5, x:x + 5] -= 0.35
    test = np.clip(test + 0.01 * _rng(variant, 41).standard_normal(base.shape), 0, 1)
    return {"value": test, "aux": {"golden": golden}, "truth": {"defects": k}}


def d2_flatfield_pair(variant):
    """Parts (k = 5 + 2·variant disks, reflectance 0.75 on 0.35) seen through strong vignetting; aux flat
    = the same optics imaging a uniform white target (gain map 0.2..1)."""
    k = 5 + 2 * int(variant)
    yy, xx = _grid()
    gain = 0.2 + 0.8 * np.exp(-((yy - 48) ** 2 + (xx - 48) ** 2) / (2 * 24.0 ** 2))
    refl = np.full((N, N), 0.35)
    for i in range(k):
        cy, cx = 14 + 22 * (i % 4), 14 + 34 * (i // 4) + 6 * (i % 2)
        refl[_disk(yy, xx, cy, cx, 6)] = 0.75
    parts = refl > 0.5
    test = np.clip(refl * gain + 0.005 * _rng(variant, 42).standard_normal(refl.shape), 0, 1)
    flat = np.clip(gain + 0.005 * _rng(variant, 43).standard_normal(refl.shape), 0, 1)
    return {"value": test, "aux": {"flat": flat}, "truth": {"count": k, "area": float(parts.sum())}}


def d2_background_pair(variant):
    """Empty-scene frame (fixture bars + a stray-light blob) and the same scene with a disk part added."""
    r = 14.0 + 6.0 * variant
    yy, xx = _grid()
    bg = 0.2 + 0.3 * ((xx % 24) < 6) + 0.25 * np.exp(-((yy - 70) ** 2 + (xx - 30) ** 2) / (2 * 12.0 ** 2))
    part = _disk(yy, xx, 44, 50, r)
    test = np.clip(bg + 0.4 * part + 0.01 * _rng(variant, 44).standard_normal(bg.shape), 0, 1)
    bgf = np.clip(bg + 0.01 * _rng(variant, 45).standard_normal(bg.shape), 0, 1)
    return {"value": test, "aux": {"background": bgf}, "truth": {"area": float(part.sum()), "row": 44.0}}


def d2_chipped_part(variant):
    """Disk part r = 26 with a chipped-off circular bite (r 6 / 9 px at the rim); aux nominal = the
    intact disk as a region (0/1 float). Truth = number of chipped pixels."""
    yy, xx = _grid()
    nominal = _disk(yy, xx, 48, 48, 26)
    bite = _disk(yy, xx, 48 - 26, 48, 6.0 + 3.0 * variant)
    part = nominal & ~bite
    return {"value": _scene(part, variant, 46), "aux": {"nominal": nominal.astype(np.float64)},
            "truth": {"missing_area": float((nominal & bite).sum())}}


SAMPLES: dict = {name: fn for name, fn in dict(globals()).items()
                 if name.startswith("d2_") and callable(fn)}

MISSING_OPS: list = [
    {"family": "2d", "need": "circle fit to an XLD contour that returns (row, col, radius) — HALCON fit_circle_contour_xld",
     "why": "hx_fit_circle_contour returns only the RMS residual and hx_smallest_circle_xld a centroid-centred "
            "enclosing radius divided by max(H, W); the radius of a round part had to be read from "
            "elliptic_axis_xld (Ra = Rb) instead"},
    {"family": "2d", "need": "watershed that returns the basins (one region / label per object) — HALCON watersheds 'Basins'",
     "why": "watersheds, pouring, xcv_watershed_markers and sg_watershed_gradient return only the dam lines; counting "
            "their components gives 1-4 for 4 / 6 touching disks, so splitting touching parts stops at the marker "
            "step (distance transform + h-maxima) and the split parts cannot be measured one by one"},
    {"family": "2d", "need": "dominant spatial frequency / period of an image as a feature (strongest non-DC FFT peak: cycles/px and angle)",
     "why": "fft_image / power_real / power_ln return spectrum images; the max-projection profile's argmax lands on "
            "the DC column and tb_find_peaks returns ~30 noise peaks, so no chain reads the grating period from the "
            "spectrum (the texture period recipe goes through zero crossings of a profile instead)"},
    {"family": "2d", "need": "bar-code / 2-D code decoding (symbology + data string) — HALCON find_bar_code / find_data_code_2d",
     "why": "decode_barcode only counts dark bars on the centre scan line; no op returns the encoded data"},
    {"family": "2d", "need": "OCR character classification (HALCON do_ocr_single_class_mlp / read text)",
     "why": "the 2-D family can segment glyphs (hx_char_threshold, sk_sauvola) but nothing classifies them"},
    {"family": "2d", "need": "polar unwrap about a given centre and radius range — HALCON polar_trans_image_ext with Row/Column/Radius",
     "why": "polar_trans_image(_ext) always use the image centre and min(H, W)/2; an off-centre ring / bore cannot "
            "be unwrapped after locating it with area_center (the ring recipe needs the ring at the image centre)"},
]

FAILED_ATTEMPTS: list = [
    {"family": "2d", "recipe": "Measure — orientation of a bar from its sub-pixel outline (orientation_xld)",
     "op": "orientation_xld",
     "error": "returns 0.389 (70.0 deg) for a bar that orientation_region measures at 19.9 deg on the same scene "
              "(0.250 = 45 deg agrees only because 45 = 90 - 45)",
     "cause": "doc_mismatch"},
    {"family": "2d", "recipe": "Measure — equivalent-ellipse angle Phi of a bar (elliptic_axis)",
     "op": "elliptic_axis",
     "error": "Phi = -0.348 rad for a bar turned +20 deg counter-clockwise on screen, while orientation_region on "
              "the same region gives +19.9 deg; the note says Phi is counter-clockwise from the column axis "
              "(elliptic_axis_xld shows the same sign: -0.3505)",
     "cause": "doc_mismatch"},
    {"family": "2d", "recipe": "Inspect — count circular holes with the Hough circle transform (no pre-smoothing)",
     "op": "cv_hough_circles",
     "error": "returns 0.0 on blobs_image (3 disks r 6-8) and on disk_image (r 18) with noise sigma 0.02; "
              "cv2.HoughCircles called directly also returns None; after gaussian a=0.5 it counts 3 / 4 correctly",
     "cause": "doc_mismatch"},
    {"family": "2d", "recipe": "Inspect — split touching parts with a marker-controlled watershed",
     "op": "xcv_watershed_markers",
     "error": "count_obj of its output = 3 / 4 for 4 / 6 touching disks (it returns the dam lines, not basins)",
     "cause": "type_gap"},
    {"family": "2d", "recipe": "Measure — perimeter of a round part from sub-pixel edges",
     "op": "edges_sub_pix",
     "error": "gaussian -> edges_sub_pix -> length_xld = 2508 px for a disk of circumference 113 px (4237 vs 151): "
              "the edge points of one contour are not ordered along the curve, so length_xld / circularity_xld "
              "sum raster jumps; threshold_sub_pix (ordered marching squares) gives 121 px",
     "cause": "doc_mismatch"},
    {"family": "2d", "recipe": "Inspect — length of a scratch from its line contour (lines_gauss)",
     "op": "lines_gauss",
     "error": "lines_gauss -> length_xld = 117 / 177 px for 40 / 60 px scratches (one contour of the thresholded "
              "ridge band's pixels, not a centre line)",
     "cause": "doc_mismatch"},
]
