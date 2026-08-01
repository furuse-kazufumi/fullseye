"""Research provenance — ground operators in their seminal papers.

Every classical image-processing operator has a paper behind it; a serious catalog
should carry that provenance (honest-provenance discipline). This maps operator
families to their seminal references and points at the RAD image-processing corpus
as the mining source for *new* operators (modern denoisers, learned edge/segment,
diffusion priors). Generates docs/REFERENCES.md.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import ops

# family key -> (member ops, seminal paper). Members match on prefix/substring.
PAPERS = [
    (["otsu", "cv_otsu", "sk_otsu"], "Otsu, N. (1979). A threshold selection method from gray-level histograms. IEEE TSMC."),
    (["threshold", "adaptive", "dyn_threshold", "sk_sauvola"], "Sauvola & Pietikäinen (2000). Adaptive document image binarization. Pattern Recognition."),
    (["sk_niblack"], "Niblack, W. (1986). An Introduction to Digital Image Processing."),
    (["sk_li"], "Li & Lee (1993). Minimum cross entropy thresholding. Pattern Recognition."),
    (["sk_yen"], "Yen, Chang & Chang (1995). A new criterion for automatic multilevel thresholding. IEEE TIP."),
    (["canny", "cv_canny", "sk_canny"], "Canny, J. (1986). A computational approach to edge detection. IEEE TPAMI."),
    (["sobel"], "Sobel & Feldman (1968). A 3x3 isotropic gradient operator for image processing."),
    (["prewitt"], "Prewitt, J. (1970). Object enhancement and extraction. Picture Processing and Psychopictorics."),
    (["laplace", "log", "dog", "sk_dog"], "Marr & Hildreth (1980). Theory of edge detection. Proc. R. Soc. Lond. B."),
    (["bilateral", "cv_bilateral"], "Tomasi & Manduchi (1998). Bilateral filtering for gray and color images. ICCV."),
    (["sk_tv"], "Rudin, Osher & Fatemi (1992). Nonlinear total variation based noise removal (ROF). Physica D."),
    (["sk_wavelet"], "Donoho & Johnstone (1994). Ideal spatial adaptation by wavelet shrinkage. Biometrika."),
    (["clahe", "cv_clahe", "sk_adapthist"], "Zuiderveld, K. (1994). Contrast Limited Adaptive Histogram Equalization. Graphics Gems IV."),
    (["gabor", "sk_gabor"], "Daugman, J. (1985). Uncertainty relation for resolution... 2D visual cortical filters. JOSA A."),
    (["sk_frangi"], "Frangi et al. (1998). Multiscale vessel enhancement filtering. MICCAI."),
    (["sk_meijering"], "Meijering et al. (2004). Design and validation of a tool for neurite tracing. Cytometry A."),
    (["corner_response"], "Harris & Stephens (1988). A combined corner and edge detector. Alvey Vision Conf."),
    (["median", "cv_median", "sk_median"], "Tukey, J. (1977). Exploratory Data Analysis (running median smoothing)."),
    (["gerode", "gdilate", "gopen", "gclose", "tophat", "bothat", "reg_", "cv_open", "cv_close"],
     "Serra, J. (1982). Image Analysis and Mathematical Morphology. (Matheron 1975)."),
    (["sk_skeleton", "thin"], "Zhang & Suen (1984). A fast parallel algorithm for thinning digital patterns. CACM."),
    (["sk_medial", "sk_convex"], "Blum, H. (1967). A transformation for extracting new descriptors of shape."),
    (["dist_transform"], "Rosenfeld & Pfaltz (1966). Sequential operations in digital picture processing. JACM."),
    (["blob_count", "select_largest", "remove_small", "area_frac", "sk_euler"],
     "Rosenfeld & Pfaltz (1966). Connected components labeling. JACM."),
    (["edges_sub_pix", "contours", "fit_line", "sk_find_contours", "total_length"],
     "Steger, C. (1998). An unbiased detector of curvilinear structures (subpixel edges). IEEE TPAMI."),
    (["ncc_locate"], "Lewis, J.P. (1995). Fast normalized cross-correlation. Vision Interface."),
    (["shape_locate"], "Steger, C. (2002). Occlusion-, clutter-, and illumination-invariant object recognition (shape-based matching)."),
    (["lowpass", "highpass", "sk_butterworth"], "Gonzalez & Woods, Digital Image Processing — frequency-domain filtering (Butterworth 1930)."),
    (["rotate_img", "rescale_img", "affine_warp"], "Wolberg, G. (1990). Digital Image Warping. IEEE CS Press."),
    (["classify_shape"], "Danielsson, P.-E. (1978). A new shape factor (circularity). Computer Graphics and Image Processing."),
    (["decode_barcode"], "Wang & Srihari (1988). Object recognition in structured / barcode reading. (1D symbology)."),
    (["equalize", "sigmoid", "gamma", "scale_clip", "invert"], "Gonzalez & Woods, Digital Image Processing — intensity transformations."),
]


def _paper_for(name: str) -> str:
    for keys, ref in PAPERS:
        if any(k in name for k in keys):
            return ref
    return "-"


def build_md() -> str:
    rows = ["# imgevolve — operator research provenance", "",
            f"Seminal references for the {ops.N_OPS} operators (families collapse many variants). "
            "The point: a designed pipeline is traceable to the literature, and the RAD image corpus "
            "is the mining source for *new* operators.", "",
            "| op | category | seminal reference |", "|---|---|---|"]
    for op in ops.REGISTRY:
        rows.append(f"| `{op.name}` | {op.category} | {_paper_for(op.name)} |")
    covered = sum(1 for op in ops.REGISTRY if _paper_for(op.name) != "-")
    rows += ["", f"**Provenance coverage: {covered}/{ops.N_OPS} operators cite a seminal paper.**", "",
             "## Mining new operators from research (RAD)",
             "- RAD image / diffusion / deep_learning corpora (thousands of papers) = the source for "
             "operators beyond the classics: modern denoisers (BM3D, DnCNN), learned edges (HED), "
             "superpixels (SLIC), diffusion priors, foundation segmenters (SAM).",
             "- Workflow: mine a paper -> add a typed Op (fn + sort + analogs + this reference) -> "
             "evolution/codegen/catalog pick it up automatically.", ""]
    return "\n".join(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="docs/REFERENCES.md")
    a = ap.parse_args()
    p = Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(build_md(), encoding="utf-8")
    covered = sum(1 for op in ops.REGISTRY if _paper_for(op.name) != "-")
    print(f"[references] {covered}/{ops.N_OPS} ops cite a paper -> {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
