"""Cross-library operator catalog.

Maps each registry op to its analog in other image-processing libraries (OpenCV,
scikit-image, MATLAB Image Processing Toolbox) alongside its HALCON name. The point
is a *single typed op-DSL that speaks many libraries' APIs* — so a designed pipeline
can be read/emitted against whichever library a user targets, and coverage across
libraries is measurable. Generates docs/OPERATORS.md.

This is a mapping of the CURRENT registry (42 ops). Growing it toward full coverage
of OpenCV/skimage/HALCON is the ongoing catalog effort — adding an op with its
analogs extends coverage automatically.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import ops

# op.name -> {library: api name}. "-" = no direct single-call analog.
ANALOGS: dict[str, dict[str, str]] = {
    "identity": {"opencv": "copyTo", "skimage": "-", "matlab": "-"},
    "gaussian": {"opencv": "GaussianBlur", "skimage": "filters.gaussian", "matlab": "imgaussfilt"},
    "mean_box": {"opencv": "blur/boxFilter", "skimage": "filters.rank.mean", "matlab": "imboxfilt"},
    "bilateral": {"opencv": "bilateralFilter", "skimage": "restoration.denoise_bilateral", "matlab": "imbilatfilt"},
    "unsharp": {"opencv": "addWeighted", "skimage": "filters.unsharp_mask", "matlab": "imsharpen"},
    "median": {"opencv": "medianBlur", "skimage": "filters.median", "matlab": "medfilt2"},
    "min_filter": {"opencv": "erode", "skimage": "filters.rank.minimum", "matlab": "ordfilt2"},
    "max_filter": {"opencv": "dilate", "skimage": "filters.rank.maximum", "matlab": "ordfilt2"},
    "percentile": {"opencv": "-", "skimage": "filters.rank.percentile", "matlab": "ordfilt2"},
    "gerode": {"opencv": "erode", "skimage": "morphology.erosion", "matlab": "imerode"},
    "gdilate": {"opencv": "dilate", "skimage": "morphology.dilation", "matlab": "imdilate"},
    "gopen": {"opencv": "morphologyEx(OPEN)", "skimage": "morphology.opening", "matlab": "imopen"},
    "gclose": {"opencv": "morphologyEx(CLOSE)", "skimage": "morphology.closing", "matlab": "imclose"},
    "tophat": {"opencv": "morphologyEx(TOPHAT)", "skimage": "morphology.white_tophat", "matlab": "imtophat"},
    "bothat": {"opencv": "morphologyEx(BLACKHAT)", "skimage": "morphology.black_tophat", "matlab": "imbothat"},
    "morph_grad": {"opencv": "morphologyEx(GRADIENT)", "skimage": "-", "matlab": "-"},
    "sobel_mag": {"opencv": "Sobel", "skimage": "filters.sobel", "matlab": "edge(...,'sobel')"},
    "laplace": {"opencv": "Laplacian", "skimage": "filters.laplace", "matlab": "fspecial('laplacian')"},
    "prewitt_mag": {"opencv": "-", "skimage": "filters.prewitt", "matlab": "edge(...,'prewitt')"},
    "roberts_mag": {"opencv": "-", "skimage": "filters.roberts", "matlab": "edge(...,'roberts')"},
    "dog": {"opencv": "-", "skimage": "filters.difference_of_gaussians", "matlab": "-"},
    "gamma": {"opencv": "LUT", "skimage": "exposure.adjust_gamma", "matlab": "imadjust"},
    "invert": {"opencv": "bitwise_not", "skimage": "util.invert", "matlab": "imcomplement"},
    "scale_clip": {"opencv": "convertScaleAbs", "skimage": "exposure.rescale_intensity", "matlab": "imadjust"},
    "equalize": {"opencv": "equalizeHist", "skimage": "exposure.equalize_hist", "matlab": "histeq"},
    "sigmoid": {"opencv": "-", "skimage": "exposure.adjust_sigmoid", "matlab": "-"},
    "lowpass": {"opencv": "dft+mask", "skimage": "fft+mask", "matlab": "fft2+mask"},
    "highpass": {"opencv": "dft+mask", "skimage": "fft+mask", "matlab": "fft2+mask"},
    "std_filter": {"opencv": "-", "skimage": "filters.rank (std)", "matlab": "stdfilt"},
    "threshold": {"opencv": "threshold", "skimage": "img>t", "matlab": "imbinarize"},
    "otsu": {"opencv": "threshold(OTSU)", "skimage": "filters.threshold_otsu", "matlab": "otsuthresh/graythresh"},
    "dyn_threshold": {"opencv": "adaptiveThreshold", "skimage": "filters.threshold_local", "matlab": "adaptthresh"},
    "reg_erode": {"opencv": "erode", "skimage": "morphology.binary_erosion", "matlab": "imerode"},
    "reg_dilate": {"opencv": "dilate", "skimage": "morphology.binary_dilation", "matlab": "imdilate"},
    "reg_open": {"opencv": "morphologyEx(OPEN)", "skimage": "morphology.binary_opening", "matlab": "imopen"},
    "reg_close": {"opencv": "morphologyEx(CLOSE)", "skimage": "morphology.binary_closing", "matlab": "imclose"},
    "fill_holes": {"opencv": "floodFill", "skimage": "ndi.binary_fill_holes", "matlab": "imfill('holes')"},
    "select_largest": {"opencv": "connectedComponents+max", "skimage": "measure.label+regionprops", "matlab": "bwareafilt"},
    "remove_small": {"opencv": "-", "skimage": "morphology.remove_small_objects", "matlab": "bwareaopen"},
    "invert_region": {"opencv": "bitwise_not", "skimage": "util.invert", "matlab": "imcomplement"},
    "blob_count": {"opencv": "connectedComponents", "skimage": "measure.label", "matlab": "bwconncomp"},
    "area_frac": {"opencv": "countNonZero", "skimage": "regionprops(area)", "matlab": "bwarea"},
    "grad_dir": {"opencv": "phase", "skimage": "-", "matlab": "imgradient"},
    "log": {"opencv": "-", "skimage": "filters.laplace(gaussian)", "matlab": "fspecial('log')"},
    "canny": {"opencv": "Canny", "skimage": "feature.canny", "matlab": "edge(...,'canny')"},
    "local_max": {"opencv": "-", "skimage": "feature.peak_local_max", "matlab": "imregionalmax"},
    "dist_transform": {"opencv": "distanceTransform", "skimage": "ndi.distance_transform_edt", "matlab": "bwdist"},
    "region_boundary": {"opencv": "findContours", "skimage": "segmentation.find_boundaries", "matlab": "bwperim"},
    "convex_fill": {"opencv": "convexHull", "skimage": "morphology.convex_hull_image", "matlab": "bwconvhull"},
    "edges_sub_pix": {"opencv": "-", "skimage": "measure.find_contours", "matlab": "-"},
    "select_contours": {"opencv": "(filter contours)", "skimage": "-", "matlab": "-"},
    "smooth_contours": {"opencv": "approxPolyDP", "skimage": "-", "matlab": "-"},
    "fit_line_contours": {"opencv": "fitLine", "skimage": "measure.LineModelND", "matlab": "polyfit"},
    "contours_to_region": {"opencv": "drawContours/fillPoly", "skimage": "draw.polygon", "matlab": "poly2mask"},
    "count_contours": {"opencv": "len(findContours)", "skimage": "len(find_contours)", "matlab": "-"},
    "total_length": {"opencv": "arcLength", "skimage": "-", "matlab": "-"},
    "ncc_locate": {"opencv": "matchTemplate", "skimage": "feature.match_template", "matlab": "normxcorr2"},
    "rotate_img": {"opencv": "warpAffine(rot)", "skimage": "transform.rotate", "matlab": "imrotate"},
    "rescale_img": {"opencv": "resize", "skimage": "transform.rescale", "matlab": "imresize"},
    "affine_warp": {"opencv": "warpAffine", "skimage": "transform.warp(Affine)", "matlab": "imwarp"},
    "gabor": {"opencv": "getGaborKernel+filter2D", "skimage": "filters.gabor", "matlab": "imgaborfilt"},
    "clahe": {"opencv": "createCLAHE", "skimage": "exposure.equalize_adapthist", "matlab": "adapthisteq"},
    "corner_response": {"opencv": "cornerHarris", "skimage": "feature.corner_harris", "matlab": "detectHarrisFeatures"},
    "adaptive_gauss_thresh": {"opencv": "adaptiveThreshold(GAUSSIAN)", "skimage": "filters.threshold_local", "matlab": "adaptthresh"},
    "shape_locate": {"opencv": "matchTemplate+rotations", "skimage": "-", "matlab": "-"},
    "classify_shape": {"opencv": "-", "skimage": "regionprops(circularity)", "matlab": "regionprops('Circularity')"},
    "decode_barcode": {"opencv": "barcode.BarcodeDetector", "skimage": "-", "matlab": "readBarcode"},
}

LIBS = ("halcon", "opencv", "skimage", "matlab")


def _analogs(name: str) -> dict:
    """Analogs for an op — explicit map, or derived for wrapped backend ops."""
    if name in ANALOGS:
        return ANALOGS[name]
    if name.startswith("sk_"):
        return {"skimage": "skimage." + name[3:], "opencv": "-", "matlab": "-"}
    if name.startswith("cv_"):
        return {"opencv": "cv2." + name[3:], "skimage": "-", "matlab": "-"}
    if name.startswith("dl_"):
        return {"opencv": "-", "skimage": "-", "matlab": "-"}  # custom torch op
    if name.startswith("vol_"):
        return {"opencv": "-", "skimage": "scipy.ndimage (N-D)", "matlab": "-"}  # 3D volume op
    return {}


def build_md() -> str:
    rows = ["# imgevolve — cross-library operator catalog", "",
            f"{ops.N_OPS} operators across {len(ops.categories())} categories, "
            f"typed by sort (image/region/feature). Each maps to the nearest single-call API "
            "in HALCON / OpenCV / scikit-image / MATLAB. `-` = no direct one-call analog.", "",
            "| op | sort | category | halcon | opencv | skimage | matlab |",
            "|---|---|---|---|---|---|---|"]
    for op in ops.REGISTRY:
        an = _analogs(op.name)
        sort = op.in_sort if op.in_sort == op.out_sort else f"{op.in_sort}->{op.out_sort}"
        rows.append(f"| `{op.name}` | {sort} | {op.category} | {op.halcon} | "
                    f"{an.get('opencv', '-')} | {an.get('skimage', '-')} | {an.get('matlab', '-')} |")
    # coverage summary
    rows += ["", "## Coverage (ops with a direct analog)"]
    for lib in ("opencv", "skimage", "matlab"):
        have = sum(1 for op in ops.REGISTRY if _analogs(op.name).get(lib, "-") != "-")
        rows.append(f"- {lib}: {have}/{ops.N_OPS}")
    rows += ["", "## Roadmap toward full coverage",
             "- HALCON ~2100 operators: add regions/XLD-contours/matching/OCR/calibration sorts.",
             "- OpenCV ~2500 functions, scikit-image ~300: extend registry per family; analogs auto-tracked here.",
             "- Adding an op with its ANALOGS row extends the catalog + search + codegen automatically.", ""]
    return "\n".join(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="docs/OPERATORS.md")
    a = ap.parse_args()
    p = Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(build_md(), encoding="utf-8")
    miss = [op.name for op in ops.REGISTRY if not _analogs(op.name)]
    print(f"[catalog] {ops.N_OPS} ops -> {p}" + (f" | MISSING analogs: {miss}" if miss else " | all mapped"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
