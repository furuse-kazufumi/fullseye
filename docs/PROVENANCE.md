# Provenance

Fullseye is an **in-house library reimplemented from published algorithms and
open-source software.** Operators are built from the public literature and from
open-source image-processing libraries, given one typed interface. Nothing here is
derived from a proprietary product; the value is the unified typed registry, the
evolutionary pipeline designer, and the honest holdout gate around them.

## Backend libraries (open source)

Operators wrap or reimplement functionality from: **NumPy**, **SciPy** (ndimage,
signal, fft), **OpenCV**, **scikit-image**, **Pillow**, **PyWavelets**,
**SimpleITK**, **mahotas**, and **kornia/torch** (GPU path). Only NumPy and SciPy
are required; the rest are optional and degrade gracefully.

## Notable algorithm sources

The perception and classic-vision building blocks are reimplemented from standard
public references, e.g.:

| block | source (public) |
|---|---|
| Otsu thresholding | Otsu, *A Threshold Selection Method from Gray-Level Histograms*, IEEE TSMC 1979 |
| Normalized cross-correlation (template match / stereo) | Lewis, *Fast Normalized Cross-Correlation*, 1995 |
| Dense two-frame stereo (block matching) | Scharstein & Szeliski, *A Taxonomy and Evaluation of Dense Two-Frame Stereo*, IJCV 2002 |
| Moment invariants (shape descriptors) | Hu, *Visual Pattern Recognition by Moment Invariants*, IRE 1962 |
| Bilateral filtering | Tomasi & Manduchi, *Bilateral Filtering for Gray and Color Images*, ICCV 1998 |
| CLAHE / histogram equalization | Pizer et al., *Adaptive Histogram Equalization*, CVGIP 1987 |
| Frei–Chen edge operator | Frei & Chen, *Fast Boundary Detection*, IEEE TC 1977 |
| Elevation mapping / traversability | standard robot-centric 2.5-D grid + step/slope analysis |

Each operator records its source in its code comment. When adding an operator,
cite the public paper or library it comes from (see `docs/ADDING_OPS.md`).

## Honesty

Coverage and benchmark numbers are **measured, not asserted**; the held-out split is
never used for selection; limitations are disclosed (see `docs/ACCURACY_BENCH.md`
and the audit notes) rather than hidden.
