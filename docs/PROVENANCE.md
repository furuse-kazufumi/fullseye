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

## Industry events as a *topic* signal — and the line that must not be crossed

Trade fairs and industry awards (VISION in Stuttgart, and similar) are a useful
signal for **which problem areas the market currently values**. Reading a
shortlist can legitimately tell us "3-D from a single shot matters", or "photon-
limited sensing is arriving". That is a topic hint, and topic hints are free.

The line is between **what to work on** and **how it works**:

| allowed | not allowed |
|---|---|
| Noting that an area (light-field capture, photon counting, virtual system design) is commercially active | Reading a company's product and reproducing *its* method |
| Implementing that area from textbook first principles and cited public literature | Naming a module, operator, or API after a company or product |
| Using the standard technical vocabulary of the field | Implying endorsement, partnership, or that we are compatible with a named product |

**Naming rule.** Company and product names never appear in module names, operator
names, API surface, docstrings, or documentation. Only the field's own
established terminology is used — *photometric stereo*, *light field* /
*plenoptic*, *SPAD*, *TCSPC*, *depth of field*, *MTF*. Those are textbook terms,
not anyone's mark, and using them is what makes the operators findable. A
commit message that says a module is "derived from" a commercial product is
wrong even when the code is independent, because provenance is judged on what we
wrote down, not on what we meant.

**What this means concretely for the 2026 additions.** `visiondesign` computes
field of view from the Gaussian conjugate equation, the sampling limit from
Nyquist, the diffraction limit from the Airy criterion, depth of field from the
circle of confusion, and falloff from the cos⁴ law. Every one of those predates
any current product by decades and is in any optics textbook; the module is an
arrangement of them, and it deliberately produces *limits* rather than rendered
images (there is no light-transport simulation here — see the module docstring's
honest-limitations paragraph). `defectgen` models defects as stochastic geometry
— random walks, point processes, branching paths, band-limited noise — which is
classical applied probability, and the pixel-perfect mask falls out of drawing
from geometry rather than from any annotation technique.

If a future addition cannot be traced to public literature this way, it does not
go in.

## Honesty

Coverage and benchmark numbers are **measured, not asserted**; the held-out split is
never used for selection; limitations are disclosed (see `docs/ACCURACY_BENCH.md`
and the audit notes) rather than hidden.
