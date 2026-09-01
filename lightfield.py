# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Light-field (plenoptic) operators — one shot, 2-D image *and* per-pixel depth.

A plenoptic camera puts a microlens array (MLA) in front of the sensor. Each
microlens images the main lens' exit pupil onto its own little block of pixels,
so one exposure records not just *how much* light arrived at a point but *from
which direction* — the 4-D light field ``L(v, u, y, x)``. Re-sorting those
pixels gives a grid of slightly-displaced views of the same scene, and from that
grid you get, from a single sensor and a single shot: a 2-D image, a refocusable
focal stack, a synthetic aperture you can stop down (or shoot *through* an
occluder with), and a dense depth map. That is the capability behind industrial
plenoptic cameras, and until now fullseye had no operator for any of it —
``light_field`` / ``plenoptic`` / ``refocus`` / ``sub_aperture`` / ``epi``
returned zero hits across the whole op catalogue.

Five families:

  * **synthesis** — :func:`lf_synthesize` builds a light field of fronto-parallel
    textured layers at *known* slopes, with optional occlusion. It exists so
    every other operator here can be checked against a closed-form answer rather
    than a golden file.
  * **decode** — :func:`lf_from_mla` / :func:`lf_to_mla` are the raw-sensor
    re-sort and its exact inverse (the round trip is bit-identical);
    :func:`lf_stats` reports the shape, the angular centre and the largest slope
    the array can actually carry.
  * **views** — :func:`lf_subaperture` / :func:`lf_center_view` / :func:`lf_views`
    / :func:`lf_epi`: one viewpoint, the centre viewpoint (the "2-D image" a
    plenoptic camera also gives you for free), the whole grid as a list of plain
    2-D images (so the ~1200 existing image operators apply unchanged), and the
    epipolar-plane image whose *line slope is the disparity*.
  * **refocus** — :func:`lf_refocus` (shift-and-add), :func:`lf_focal_stack`,
    :func:`lf_aperture_mask` and :func:`lf_synthetic_aperture` (aperture
    weighting + a median reduction that sees through foreground clutter).
  * **depth** — :func:`lf_depth_from_focus` (sharpness peak across the focal
    stack), :func:`lf_epi_slope` (structure-tensor slope of the EPI lines),
    :func:`lf_disparity_to_depth` (slope -> metric distance) and
    :func:`lf_all_in_focus` (per-pixel selection from the stack).
    :func:`lf_plenoptic_design` sizes the camera itself.

Deliberately **not** here (owned elsewhere — imported and composed, never
re-implemented):

  * **Lens, aperture and depth-of-field arithmetic** is :mod:`optics`.
    :func:`lf_plenoptic_design` *calls* ``optics.thin_lens`` and
    ``optics.depth_of_field`` — the refocusable range of a plenoptic camera is
    literally the depth of field computed with the *microlens pitch* as the
    circle of confusion instead of the pixel pitch, and that is how it is
    computed here.
  * **Two-view stereo** is :mod:`stereo` (``disparity_map``,
    ``disparity_census``, ``disparity_sgm``, ``depth_from_disparity``,
    ``lr_consistency``). A light field is not two rectified cameras: every op
    here uses the *whole* angular grid at once, which is what buys the
    occlusion robustness and the sub-pixel disparity. If you only have two
    views, use :mod:`stereo`; it is better at that job than a 2-view light
    field would be.
  * **Focus stacking of an ordinary camera** is :mod:`focus_stack` — a real
    camera physically re-focused N times. :func:`lf_focal_stack` produces the
    same *kind* of object computationally from one exposure, and hands back a
    plain list of 2-D images so ``focus_stack``'s fusion machinery still applies.
  * **Point clouds, reprojection and 3-D fitting** are :mod:`match3d` /
    :mod:`pointcloud` / :mod:`ransac_fit`. :func:`lf_disparity_to_depth` stops
    at a metric depth map; turning that into points is ``depth_to_points``.
  * **Generic image sharpness / Laplacian / variance filters** are :mod:`ops`
    and :mod:`filters_freq`. The focus measure inside
    :func:`lf_depth_from_focus` is deliberately a *private* helper, not a new
    public sharpness op.

Conventions, stated once (these are the traps):

  * **Layout** is ``L[v, u, y, x]`` with shape ``(V, U, H, W)``: angular axes
    first (``v`` vertical, ``u`` horizontal), spatial axes last. ``L[v, u]`` is
    therefore a plain 2-D image — a sub-aperture view — and every fullseye
    image op applies to it without a reshape.
  * **Angular centre** is ``u_c = (U - 1) / 2``, ``v_c = (V - 1) / 2``. For an
    even ``U`` that is a half-integer and **no single view is the centre view**;
    :func:`lf_center_view` says what it does about that instead of silently
    picking a neighbour.
  * **Slope** (the single parameter every depth op speaks) is
    ``s = dx/du = dy/dv`` — the displacement in **pixels of image shift per one
    step of the angular index**. A scene point sits at
    ``x = x_c + s * (u - u_c)``, ``y = y_c + s * (v - v_c)``. Refocusing onto
    that point therefore shifts view ``(v, u)`` by ``(-s*(v - v_c),
    -s*(u - u_c))`` before averaging — the **minus** is the whole game, and
    getting it backwards produces a picture that is sharp at ``-s`` and looks
    perfectly plausible. ``s = 0`` is the plane the array is already focused on;
    the sign of ``s`` says which side of it a point is on, and *which* sign
    means "near" depends on how the angular axis was oriented during decode, so
    :func:`lf_disparity_to_depth` works from ``|s|`` and asks you for the
    orientation rather than guessing.
  * **Shifts** move content toward larger indices: ``shift(img, +1, 0)`` puts
    ``img[0, 0]`` at ``[1, 0]`` (this is ``scipy.ndimage.shift``'s convention,
    used unchanged). ``edge="nearest"`` clamps at the border like a real camera
    that ran out of sensor; ``edge="wrap"`` makes the scene periodic, which is
    what makes an integer-slope round trip **bit-exact** and is why the tests
    use it.

Honest disclosure (what these ops cannot do):

  * **:func:`lf_epi_slope` is biased for large slopes, and the bias is real.**
    It is an ordinary least-squares fit of ``E_u + s*E_x = 0`` on
    finite-difference gradients, so it needs the EPI line to move less than
    about one texture correlation length per view. Measured 2026-09-01 on a
    5x5x64x64 synthetic field of Gaussian-smoothed noise (``seed=0``,
    ``occlusion=False``, ``edge="wrap"``), median estimate over the interior
    against the true slope: at texture ``sigma = 1.5`` px, true
    ``+1.00 -> +1.0004``, ``+0.50 -> +0.5285``, ``+1.50 -> +1.3018``,
    ``+2.00 -> +1.4614``; at ``sigma = 5.0`` px the same slopes give ``+1.0003``,
    ``+0.5029``, ``+1.4827``, ``+1.9482``. It is fast and dense, not accurate at
    ``|s| > 1``. :func:`lf_depth_from_focus` has no such bias — over those same
    18 combinations (6 slopes x 3 texture scales) its argmax landed **exactly**
    on the true slope 18 times out of 18 — but it only resolves what you put in
    ``slopes``.
  * **No sub-pixel MLA calibration.** :func:`lf_from_mla` re-sorts on an
    *integer* pixel grid with an integer ``offset``. Real plenoptic decoding
    starts by fitting the microlens centres to sub-pixel accuracy from a white
    image, because the MLA is never an exact integer multiple of the pixel
    pitch and is never perfectly aligned. That calibration is out of scope here;
    feed this module an already-rectified raw frame.
  * **No vignetting, no microlens diffraction, no hexagonal MLA.** The decode
    assumes a rectangular, non-overlapping, uniformly-illuminated grid. Real
    sensors show strong per-microlens vignetting toward the pupil edge (which is
    exactly why :func:`lf_aperture_mask` exists) and many commercial MLAs are
    hexagonal.
  * **Refocus is shift-and-add, i.e. the Lambertian, fronto-parallel model.**
    Specular highlights move with the viewpoint and will *not* fuse; slanted
    surfaces are only piecewise correct. :func:`lf_synthetic_aperture` with
    ``reduce="median"`` is the one concession to non-Lambertian reality, and it
    trades resolution for that robustness.
  * **The angular resolution is bought with spatial resolution.** A ``U*V``
    angular grid costs a factor ``U*V`` of pixels; :func:`lf_plenoptic_design`
    prints that trade instead of hiding it.
  * **Bilinear resampling blurs.** Every fractional-slope shift costs contrast.
    Integer slopes are exact (a 25-view integer-slope refocus reproduces the
    source texture to 5.6e-16, and the raw <-> light-field re-sort is
    bit-identical); fractional
    ones are not, and stacking many of them in :func:`lf_all_in_focus` is
    visible. Pass ``interp="cubic"`` when that matters.

Fail-closed on untrusted input, like every Fullseye module: shapes are exact,
NaN/Inf are rejected on the way in, a non-4-D array, an angular axis of length
0, a raw frame whose size is not a whole multiple of the microlens pitch, an
opaque aperture mask, a zero-texture pixel and a slope that would shift the
whole image off the sensor all raise an explicit ``ValueError`` naming the
problem — never a silent NaN, a silent crop, or a silent zero-division. The
element counts are capped (:data:`MAX_LF_ELEMENTS`, :data:`MAX_ANGULAR`,
:data:`MAX_STACK_SLICES`, :data:`MAX_STACK_ELEMENTS`) because ``V*U*H*W`` is a
product of four numbers that each look small: ``(64, 64, 512, 512)`` reads
innocently and is 8.6 GB.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as _ndi

import optics as _optics

__all__ = [
    "lf_synthesize",
    "lf_from_mla", "lf_to_mla", "lf_stats",
    "lf_subaperture", "lf_center_view", "lf_views", "lf_epi",
    "lf_refocus", "lf_focal_stack", "lf_aperture_mask", "lf_synthetic_aperture",
    "lf_depth_from_focus", "lf_epi_slope", "lf_disparity_to_depth",
    "lf_all_in_focus", "lf_plenoptic_design",
    "LIGHTFIELD", "MAX_LF_ELEMENTS", "MAX_ANGULAR", "MAX_SPATIAL",
    "MAX_STACK_SLICES", "MAX_STACK_ELEMENTS", "MAX_LAYERS", "MAX_ABS_SLOPE",
    "INTERP_ORDERS", "EDGE_MODES", "APERTURE_SHAPES", "FOCUS_MEASURES",
    "REDUCERS",
]

#: The public light-field operators, by name (introspection / facade wiring).
LIGHTFIELD = [
    "lf_synthesize",
    "lf_from_mla", "lf_to_mla", "lf_stats",
    "lf_subaperture", "lf_center_view", "lf_views", "lf_epi",
    "lf_refocus", "lf_focal_stack", "lf_aperture_mask", "lf_synthetic_aperture",
    "lf_depth_from_focus", "lf_epi_slope", "lf_disparity_to_depth",
    "lf_all_in_focus", "lf_plenoptic_design",
]

#: Largest element count for a light field, ``V*U*H*W``. 2^24 elements =
#: 134 MB as float64, which still admits 9x9 views of 480x480. The cap exists
#: because the size is a product of *four* separately-innocent numbers:
#: ``(64, 64, 512, 512)`` is 1.07e9 elements = 8.6 GB.
MAX_LF_ELEMENTS = 1 << 24

#: Largest length of one angular axis (``U`` or ``V``). Commercial plenoptic
#: cameras are in the 7..15 range; 64 is already far past useful.
MAX_ANGULAR = 64

#: Largest length of one spatial axis (``H`` or ``W``) of a sub-aperture view.
MAX_SPATIAL = 4096

#: Largest number of slices in a focal stack / slope sweep.
MAX_STACK_SLICES = 256

#: Largest element count for a focal stack, ``len(slopes)*H*W``.
MAX_STACK_ELEMENTS = 1 << 24

#: Largest number of layers :func:`lf_synthesize` will composite.
MAX_LAYERS = 64

#: Largest ``|slope|`` (pixels of image shift per angular step) any operator
#: accepts. Beyond this the extreme view is displaced by more than
#: ``MAX_ABS_SLOPE * (U-1)/2`` pixels, i.e. the whole frame has left the sensor
#: and the "refocused" image is pure edge-extension artefact.
MAX_ABS_SLOPE = 1024.0

#: Resampling kernels, mapped to ``scipy.ndimage`` spline orders. ``nearest``
#: is exact but quantises the slope to whole pixels; ``linear`` is the standard
#: choice; ``cubic`` costs ~3x and preserves contrast through many shifts.
INTERP_ORDERS = {"nearest": 0, "linear": 1, "cubic": 3}

#: Border handling. ``nearest`` clamps (a real camera that ran out of sensor);
#: ``wrap`` makes the scene periodic, which is what makes an integer-slope round
#: trip bit-exact.
EDGE_MODES = {"nearest": "nearest", "wrap": "grid-wrap"}

#: Aperture shapes understood by :func:`lf_aperture_mask`.
APERTURE_SHAPES = ("circle", "square", "gaussian", "annulus")

#: Focus measures understood by :func:`lf_depth_from_focus`.
FOCUS_MEASURES = ("laplacian", "variance", "gradient")

#: Reductions across the angular grid understood by
#: :func:`lf_synthetic_aperture`. ``median`` is the occlusion-robust one.
REDUCERS = ("mean", "median", "max", "min")


# --------------------------------------------------------------------------- #
# fail-closed input helpers (same discipline as optics.py)                     #
# --------------------------------------------------------------------------- #
def _finite_scalar(v, name: str) -> float:
    """A real, finite Python float — or ``ValueError`` naming the problem."""
    if np.ma.is_masked(v):
        raise ValueError("%s is a masked value — fill or drop it explicitly" % (name,))
    if isinstance(v, (complex, np.complexfloating)):
        raise ValueError("%s is complex — a slope/length is a real quantity; "
                         "coercion would silently drop the imaginary part" % (name,))
    if isinstance(v, (bool, np.bool_)):
        raise ValueError("%s is a bool — refusing the silent True==1 promotion"
                         % (name,))
    if isinstance(v, (str, bytes, np.str_, np.bytes_)):
        raise ValueError("%s is a string (%r) — a slope/length must be a number; "
                         "float('1.5') would silently succeed and hide an "
                         "unparsed configuration value" % (name, v))
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s must be a real scalar, got %r"
                         % (name, type(v).__name__)) from None
    if not np.isfinite(f):
        raise ValueError("%s must be finite, got %r (NaN/Inf would propagate "
                         "through every result)" % (name, v))
    return f


def _positive(v, name: str) -> float:
    f = _finite_scalar(v, name)
    if f <= 0.0:
        raise ValueError("%s must be > 0, got %g" % (name, f))
    return f


def _count(v, name: str, lo: int, hi: int) -> int:
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer)):
        raise ValueError("%s must be an int, got %r" % (name, type(v).__name__))
    n = int(v)
    if n < lo or n > hi:
        raise ValueError("%s must be in [%d, %d], got %d (the cap is there so a "
                         "mistyped exponent fails instead of allocating "
                         "gigabytes)" % (name, lo, hi, n))
    return n


def _slope(v, name: str) -> float:
    f = _finite_scalar(v, name)
    if abs(f) > MAX_ABS_SLOPE:
        raise ValueError("%s = %g exceeds the |slope| cap %g px/view — at that "
                         "slope the extreme view is displaced clear off the "
                         "frame and the result is pure edge artefact"
                         % (name, f, MAX_ABS_SLOPE))
    return f


def _as_float_array(a, name: str) -> np.ndarray:
    """Coerce to float64, refusing the two silent-truncation traps."""
    if np.ma.is_masked(a):
        raise ValueError("%s is a masked array with masked (invalid) entries — "
                         "coercion would strip the mask and use the raw values "
                         "underneath; fill or drop them explicitly" % (name,))
    if np.iscomplexobj(a):
        raise ValueError("%s is complex — coercion to float64 would silently "
                         "discard the imaginary part; take .real/.imag/abs() "
                         "explicitly" % (name,))
    arr = np.ascontiguousarray(a, dtype=np.float64)
    if arr.size and not np.isfinite(arr).all():
        n = int((~np.isfinite(arr)).sum())
        raise ValueError("%s has %d non-finite value(s) (NaN/Inf) — refusing"
                         % (name, n))
    return arr


def _require_lf(a, op: str, name: str = "lf") -> np.ndarray:
    """A strictly 4-D ``(V, U, H, W)`` finite, size-capped light field."""
    arr = _as_float_array(a, name)
    if arr.ndim != 4:
        raise ValueError("%s: %s must be a 4-D light field (V, U, H, W), got a "
                         "%d-D array of shape %r — nothing is reshaped silently; "
                         "use lf_from_mla() to decode a raw sensor frame"
                         % (op, name, arr.ndim, tuple(np.shape(a))))
    v, u, h, w = arr.shape
    if min(v, u, h, w) < 1:
        raise ValueError("%s: %s has an empty axis (shape %r) — a light field "
                         "needs at least one view and one pixel"
                         % (op, name, arr.shape))
    if v > MAX_ANGULAR or u > MAX_ANGULAR:
        raise ValueError("%s: %s angular shape (%d, %d) exceeds the %d cap "
                         "(lightfield.MAX_ANGULAR)" % (op, name, v, u, MAX_ANGULAR))
    if h > MAX_SPATIAL or w > MAX_SPATIAL:
        raise ValueError("%s: %s spatial shape (%d, %d) exceeds the %d cap "
                         "(lightfield.MAX_SPATIAL)" % (op, name, h, w, MAX_SPATIAL))
    if arr.size > MAX_LF_ELEMENTS:
        raise ValueError("%s: %s has %d elements (shape %r), over the %d cap "
                         "(lightfield.MAX_LF_ELEMENTS)"
                         % (op, name, arr.size, arr.shape, MAX_LF_ELEMENTS))
    return arr


def _require_image(a, op: str, name: str) -> np.ndarray:
    arr = _as_float_array(a, name)
    if arr.ndim != 2:
        raise ValueError("%s: %s must be a 2-D array, got a %d-D array of shape %r"
                         % (op, name, arr.ndim, tuple(np.shape(a))))
    if arr.shape[0] < 1 or arr.shape[1] < 1:
        raise ValueError("%s: %s is empty (shape %r)" % (op, name, arr.shape))
    return arr


def _choice(v, name: str, allowed, op: str) -> str:
    if not isinstance(v, str):
        raise ValueError("%s: %s must be a string, got %r"
                         % (op, name, type(v).__name__))
    k = v.strip().lower()
    if k not in allowed:
        raise ValueError("%s: unknown %s %r — expected one of %s"
                         % (op, name, v, "/".join(sorted(allowed))))
    return k


def _odd_window(v, name: str, op: str) -> int:
    n = _count(v, name, 1, 4095)
    if n % 2 == 0:
        raise ValueError("%s: %s must be odd so the window has a centre pixel, "
                         "got %d (an even window shifts every estimate by half a "
                         "pixel, which is exactly the size of the effect being "
                         "measured)" % (op, name, n))
    return n


def _shift2(img: np.ndarray, dy: float, dx: float, order: int,
            mode: str) -> np.ndarray:
    """Shift a 2-D image so content moves toward larger indices by ``(dy, dx)``.

    Integer shifts in ``wrap`` mode are exactly ``np.roll`` (verified to 0.0);
    integer shifts in ``nearest`` mode are exact in the interior and clamp at
    the border.
    """
    if dy == 0.0 and dx == 0.0:
        return img.copy()
    return _ndi.shift(img, (dy, dx), order=order, mode=mode, prefilter=order > 1)


def _angular_centers(v: int, u: int) -> tuple:
    return (v - 1) / 2.0, (u - 1) / 2.0


# --------------------------------------------------------------------------- #
# synthesis                                                                    #
# --------------------------------------------------------------------------- #
def _band_limited_texture(shape, sigma, rng) -> np.ndarray:
    """Gaussian-smoothed white noise, rescaled to [0, 1]. Periodic (wrap)."""
    t = _ndi.gaussian_filter(rng.standard_normal(shape), sigma, mode="wrap")
    lo, hi = float(t.min()), float(t.max())
    if hi - lo < 1e-12:
        # Degenerate only if sigma is so large the field is constant; a constant
        # texture carries no parallax, so say so rather than divide by ~0.
        raise ValueError("lf_synthesize: texture_sigma is so large that the "
                         "generated texture is constant (range %g) — a "
                         "featureless field has no measurable disparity"
                         % (hi - lo,))
    return (t - lo) / (hi - lo)


def lf_synthesize(slopes=(0.0,), angular=(5, 5), shape=(64, 64), *,
                  occlusion=True, coverage=0.55, texture_sigma=2.0,
                  interp="linear", edge="wrap", seed=0):
    """Build a light field of textured layers at **known** slopes (the test bed).

    Each entry of *slopes* is one fronto-parallel layer, given as its slope
    ``s = dx/du`` in **pixels of image shift per angular step**; the layer's
    texture is band-limited noise (Gaussian-smoothed, ``texture_sigma`` px) and
    view ``(v, u)`` sees it displaced by ``(s*(v - v_c), s*(u - u_c))``. Because
    the displacement is exactly linear in the angular index, every downstream
    answer is closed-form: the refocus sharpness peaks at ``s``, the EPI lines
    have slope ``s``, and the disparity between the extreme views is
    ``s * (U - 1)``.

    *angular* is ``(V, U)`` and *shape* is ``(H, W)``.

    With ``occlusion=True`` (default) the layers are composited front-to-back by
    ``|slope|`` (largest ``|s|`` = nearest = drawn last) through random binary
    masks covering roughly *coverage* of the frame, and the **last** entry of
    *slopes* is forced opaque as the background. That is what makes a
    see-through synthetic-aperture test meaningful. With ``occlusion=False`` the
    layers are averaged instead — a transparent superposition, which is the
    cleanest possible input for refocusing because each layer survives the
    average untouched.

    Returns ``(light_field, slope_map)``: the ``(V, U, H, W)`` array and the
    ``(H, W)`` map of the front-most layer's slope at each pixel — the ground
    truth for :func:`lf_depth_from_focus` and :func:`lf_epi_slope`. The map is
    in **centre-view** coordinates (the masks are stated unshifted, and the
    centre view is the one view whose shift is zero), which is also the frame a
    refocused image lands in. With
    ``occlusion=False`` the light field also contains the *other* layers at
    every pixel, so a depth estimator will legitimately disagree with the map
    wherever layers overlap; the single-layer case is unambiguous and is what
    the exactness tests use.

    ``edge="wrap"`` (default) makes the scene periodic so an integer slope is a
    pure ``np.roll`` and the whole pipeline is bit-exact end to end (measured
    round-trip error 5.6e-16); ``edge="nearest"`` reproduces a real camera's
    border clamping.

    **Raises** ``ValueError``: an empty or over-long *slopes* list
    (:data:`MAX_LAYERS`), a non-finite or over-large slope
    (:data:`MAX_ABS_SLOPE`), an angular or spatial shape outside
    ``[1, MAX_ANGULAR]`` / ``[1, MAX_SPATIAL]``, a total size over
    :data:`MAX_LF_ELEMENTS`, *coverage* outside ``(0, 1]``, a *texture_sigma*
    so large the texture comes out constant, and an unknown *interp* / *edge*.
    """
    op = "lf_synthesize"
    if isinstance(slopes, (str, bytes)) or np.isscalar(slopes):
        raise ValueError("%s: slopes must be a sequence of layer slopes, got %r "
                         "— pass (s,) for a single layer" % (op, type(slopes).__name__))
    sl = [_slope(s, "%s: slopes[%d]" % (op, i)) for i, s in enumerate(slopes)]
    if not sl:
        raise ValueError("%s: slopes is empty — a scene needs at least one layer"
                         % (op,))
    if len(sl) > MAX_LAYERS:
        raise ValueError("%s: %d layers exceeds the %d cap (lightfield.MAX_LAYERS)"
                         % (op, len(sl), MAX_LAYERS))
    if len(angular) != 2 or len(shape) != 2:
        raise ValueError("%s: angular must be (V, U) and shape must be (H, W)"
                         % (op,))
    V = _count(angular[0], op + ": angular[0] (V)", 1, MAX_ANGULAR)
    U = _count(angular[1], op + ": angular[1] (U)", 1, MAX_ANGULAR)
    H = _count(shape[0], op + ": shape[0] (H)", 2, MAX_SPATIAL)
    W = _count(shape[1], op + ": shape[1] (W)", 2, MAX_SPATIAL)
    if V * U * H * W > MAX_LF_ELEMENTS:
        raise ValueError("%s: (V, U, H, W) = (%d, %d, %d, %d) is %d elements, "
                         "over the %d cap (lightfield.MAX_LF_ELEMENTS) — the "
                         "size is a product of four separately-small numbers"
                         % (op, V, U, H, W, V * U * H * W, MAX_LF_ELEMENTS))
    cov = _finite_scalar(coverage, op + ": coverage")
    if not (0.0 < cov <= 1.0):
        raise ValueError("%s: coverage must be in (0, 1], got %g" % (op, cov))
    sigma = _positive(texture_sigma, op + ": texture_sigma")
    order = INTERP_ORDERS[_choice(interp, "interp", INTERP_ORDERS, op)]
    mode = EDGE_MODES[_choice(edge, "edge", EDGE_MODES, op)]
    seed_i = _count(seed, op + ": seed", 0, 2 ** 31 - 1)
    rng = np.random.default_rng(seed_i)

    # front-to-back = nearest last, so the painter's algorithm draws near over far
    order_idx = sorted(range(len(sl)), key=lambda i: abs(sl[i]))
    textures = [_band_limited_texture((H, W), sigma, rng) for _ in sl]
    alphas = []
    for k, i in enumerate(order_idx):
        if k == 0 or not occlusion:
            alphas.append(np.ones((H, W)))          # farthest layer is the backdrop
        else:
            m = _ndi.gaussian_filter(rng.standard_normal((H, W)),
                                     max(sigma, 2.0), mode="wrap")
            alphas.append((m >= np.quantile(m, 1.0 - cov)).astype(np.float64))

    vc, uc = _angular_centers(V, U)
    lf = np.zeros((V, U, H, W), dtype=np.float64)
    for v in range(V):
        for u in range(U):
            acc = np.zeros((H, W))
            for k, i in enumerate(order_idx):
                dy, dx = sl[i] * (v - vc), sl[i] * (u - uc)
                tex = _shift2(textures[i], dy, dx, order, mode)
                if occlusion:
                    a = _shift2(alphas[k], dy, dx, order, mode)
                    np.clip(a, 0.0, 1.0, out=a)
                    acc = acc * (1.0 - a) + tex * a
                else:
                    acc += tex / len(sl)
            lf[v, u] = acc

    slope_map = np.full((H, W), sl[order_idx[0]], dtype=np.float64)
    for k, i in enumerate(order_idx):
        if k == 0:
            continue
        slope_map = np.where(alphas[k] > 0.5, sl[i], slope_map)
    return lf, slope_map


# --------------------------------------------------------------------------- #
# decode: raw sensor <-> light field                                           #
# --------------------------------------------------------------------------- #
def lf_from_mla(raw, angular=(5, 5), *, offset=(0, 0), crop=False):
    """Decode a microlens-array raw frame into a ``(V, U, H, W)`` light field.

    The plenoptic sensor stores, for microlens ``(t, s)``, a ``V x U`` block of
    pixels — one per direction through the main lens' exit pupil. So raw pixel
    ``(offset_y + t*V + v, offset_x + s*U + u)`` is exactly ``L[v, u, t, s]``:
    the decode is a pure re-sort, no interpolation, no data invented.
    :func:`lf_to_mla` inverts it **bit-exactly**.

    *offset* is the integer position of the first whole microlens; a real MLA is
    never aligned to pixel ``(0, 0)``. Sub-pixel MLA calibration is out of scope
    (see the module docstring) — this operator works on an already-rectified
    frame.

    By default a raw frame whose usable size is not a whole multiple of the
    microlens pitch is a ``ValueError``, because the alternative — quietly
    dropping the last partial row of microlenses — shifts every subsequent
    microlens centre and produces a light field that looks right and is wrong.
    Pass ``crop=True`` to opt in to that crop explicitly.

    **Raises** ``ValueError``: *raw* not 2-D or non-finite, *angular* outside
    ``[1, MAX_ANGULAR]``, a negative *offset*, an *offset* that leaves fewer
    than one whole microlens, a size that is not a multiple of the pitch (unless
    ``crop=True``), a decoded sub-aperture image over :data:`MAX_SPATIAL` on a
    side, and a decoded size over :data:`MAX_LF_ELEMENTS`.
    """
    op = "lf_from_mla"
    img = _require_image(raw, op, "raw")
    if len(angular) != 2:
        raise ValueError("%s: angular must be (V, U)" % (op,))
    V = _count(angular[0], op + ": angular[0] (V)", 1, MAX_ANGULAR)
    U = _count(angular[1], op + ": angular[1] (U)", 1, MAX_ANGULAR)
    if len(offset) != 2:
        raise ValueError("%s: offset must be (offset_y, offset_x)" % (op,))
    oy = _count(offset[0], op + ": offset[0]", 0, MAX_SPATIAL * MAX_ANGULAR)
    ox = _count(offset[1], op + ": offset[1]", 0, MAX_SPATIAL * MAX_ANGULAR)
    Hr, Wr = img.shape
    if oy >= Hr or ox >= Wr:
        raise ValueError("%s: offset (%d, %d) is outside the %dx%d raw frame"
                         % (op, oy, ox, Hr, Wr))
    avail_h, avail_w = Hr - oy, Wr - ox
    if avail_h < V or avail_w < U:
        raise ValueError("%s: after offset (%d, %d) only %dx%d pixels remain, "
                         "less than one whole %dx%d microlens block"
                         % (op, oy, ox, avail_h, avail_w, V, U))
    rh, rw = avail_h % V, avail_w % U
    if (rh or rw) and not crop:
        raise ValueError("%s: the usable frame is %dx%d after offset, which is "
                         "not a whole multiple of the %dx%d microlens pitch "
                         "(%d row(s) and %d column(s) left over). Silently "
                         "dropping them would move every microlens centre; pass "
                         "crop=True to accept the crop explicitly, or fix the "
                         "offset/pitch." % (op, avail_h, avail_w, V, U, rh, rw))
    Hs, Ws = avail_h // V, avail_w // U
    if Hs > MAX_SPATIAL or Ws > MAX_SPATIAL:
        raise ValueError("%s: the decoded sub-aperture images would be %dx%d, "
                         "over the %d cap (lightfield.MAX_SPATIAL) — the raw "
                         "frame is %dx%d and _require_image does not bound it, "
                         "so the bound lives here"
                         % (op, Hs, Ws, MAX_SPATIAL, Hr, Wr))
    if V * U * Hs * Ws > MAX_LF_ELEMENTS:
        raise ValueError("%s: decoded light field would be %d elements "
                         "((%d, %d, %d, %d)), over the %d cap "
                         "(lightfield.MAX_LF_ELEMENTS)"
                         % (op, V * U * Hs * Ws, V, U, Hs, Ws, MAX_LF_ELEMENTS))
    block = img[oy:oy + Hs * V, ox:ox + Ws * U]
    return np.ascontiguousarray(
        block.reshape(Hs, V, Ws, U).transpose(1, 3, 0, 2))


def lf_to_mla(lf):
    """Re-interleave a light field into a microlens-array raw frame (exact inverse).

    Inverse of :func:`lf_from_mla` with ``offset=(0, 0)``: the returned frame has
    shape ``(H*V, W*U)`` and puts ``L[v, u, t, s]`` back at raw pixel
    ``(t*V + v, s*U + u)``. ``lf_from_mla(lf_to_mla(L), (V, U))`` returns ``L``
    bit-for-bit (verified with ``np.array_equal``), which is the cheapest
    possible check that the decode's index arithmetic has no off-by-one.

    **Raises** ``ValueError``: *lf* not 4-D / non-finite / over the shape and
    element caps (see :func:`lf_from_mla`), and a raw frame whose side would
    exceed ``MAX_SPATIAL * MAX_ANGULAR``.
    """
    op = "lf_to_mla"
    arr = _require_lf(lf, op)
    V, U, H, W = arr.shape
    if H * V > MAX_SPATIAL * MAX_ANGULAR or W * U > MAX_SPATIAL * MAX_ANGULAR:
        raise ValueError("%s: the raw frame would be %dx%d, over the "
                         "MAX_SPATIAL*MAX_ANGULAR = %d cap"
                         % (op, H * V, W * U, MAX_SPATIAL * MAX_ANGULAR))
    return np.ascontiguousarray(
        arr.transpose(2, 0, 3, 1).reshape(H * V, W * U))


def lf_stats(lf):
    """Describe a light field: shape, angular centre, and the slope range it can carry.

    Returns a dict — ``angular_v`` / ``angular_u`` · ``height`` / ``width`` ·
    ``n_views = V*U`` · ``center_v`` / ``center_u`` (``(N-1)/2``, a half-integer
    when the axis is even, so ``center_is_a_view`` says whether a single view
    actually sits at the centre) · ``min`` / ``max`` / ``mean`` of the samples ·
    ``max_slope_px``, the largest ``|s|`` for which the extreme view is still
    displaced by less than half the frame, i.e. the honest limit of what this
    array can measure (``min(H, W) / max(V-1, U-1, 1)``; reported as
    ``float(min(H, W))`` when the array has a single view in both directions,
    since then no shift happens at all) · ``baseline_views``, the angular span
    ``(V-1, U-1)`` that any disparity is measured over.

    **Raises** ``ValueError``: *lf* is not a finite 4-D array within the shape
    and element caps.
    """
    op = "lf_stats"
    arr = _require_lf(lf, op)
    V, U, H, W = arr.shape
    vc, uc = _angular_centers(V, U)
    span = max(V - 1, U - 1)
    return {
        "angular_v": int(V), "angular_u": int(U),
        "height": int(H), "width": int(W),
        "n_views": int(V * U),
        "center_v": float(vc), "center_u": float(uc),
        "center_is_a_view": bool(V % 2 == 1 and U % 2 == 1),
        "min": float(arr.min()), "max": float(arr.max()),
        "mean": float(arr.mean()),
        "max_slope_px": float(min(H, W)) if span == 0
                        else float(min(H, W)) / float(span),
        "baseline_views": (int(V - 1), int(U - 1)),
    }


# --------------------------------------------------------------------------- #
# views                                                                        #
# --------------------------------------------------------------------------- #
def lf_subaperture(lf, v=0, u=0):
    """One sub-aperture view — the image seen through one point of the pupil.

    Returns a copy of ``L[v, u]`` as a plain ``(H, W)`` 2-D image, so every
    other fullseye image operator applies to it unchanged. Indices are
    **not** wrapped: a negative or out-of-range index is a ``ValueError``, not a
    silent Python wrap-around to the opposite corner of the pupil (which is the
    single easiest way to get a mirrored disparity sign downstream).

    **Raises** ``ValueError``: *lf* not a valid light field, and *v* / *u* not
    an int in ``[0, V)`` / ``[0, U)``.
    """
    op = "lf_subaperture"
    arr = _require_lf(lf, op)
    V, U = arr.shape[0], arr.shape[1]
    iv = _count(v, op + ": v", 0, V - 1)
    iu = _count(u, op + ": u", 0, U - 1)
    return arr[iv, iu].copy()


def lf_center_view(lf, mode="average"):
    """The centre viewpoint — the ordinary 2-D image a plenoptic camera also gives.

    For odd ``V`` and ``U`` the centre is a single view and both modes return it
    exactly. For an **even** axis the centre falls *between* two views, and this
    operator does not pretend otherwise:

      * ``mode="average"`` (default) returns the mean of the 2 (or 4) views
        straddling the centre — the correctly-centred estimate for a Lambertian
        scene, at the cost of a slight blur proportional to the disparity.
      * ``mode="nearest"`` returns the single view at ``floor((N-1)/2)``, which
        is sharp but sits half an angular step off centre; every disparity
        measured against it carries that half-step bias.

    Returns a ``(H, W)`` 2-D image.

    **Raises** ``ValueError``: *lf* not a valid light field, unknown *mode*.
    """
    op = "lf_center_view"
    arr = _require_lf(lf, op)
    m = _choice(mode, "mode", ("average", "nearest"), op)
    V, U = arr.shape[0], arr.shape[1]
    if m == "nearest" or (V % 2 == 1 and U % 2 == 1):
        return arr[(V - 1) // 2, (U - 1) // 2].copy()
    vs = [(V - 1) // 2] if V % 2 == 1 else [V // 2 - 1, V // 2]
    us = [(U - 1) // 2] if U % 2 == 1 else [U // 2 - 1, U // 2]
    acc = np.zeros(arr.shape[2:], dtype=np.float64)
    for iv in vs:
        for iu in us:
            acc += arr[iv, iu]
    return acc / float(len(vs) * len(us))


def lf_views(lf):
    """The whole angular grid as a plain list of 2-D images (row-major over ``(v, u)``).

    The bridge to the rest of fullseye: the returned ``list`` of ``V*U``
    ``(H, W)`` arrays is the ``images`` type, so multi-image operators
    (registration, fusion, statistics, :mod:`focus_stack`'s machinery) consume a
    light field with no adapter. Ordering is ``v`` outer, ``u`` inner, i.e.
    ``views[v*U + u] == lf[v, u]``; each entry is a copy, so mutating one does
    not corrupt the field.

    **Raises** ``ValueError``: *lf* is not a valid light field.
    """
    op = "lf_views"
    arr = _require_lf(lf, op)
    V, U = arr.shape[0], arr.shape[1]
    return [arr[v, u].copy() for v in range(V) for u in range(U)]


def lf_epi(lf, axis="u", index=0, view=None):
    """Epipolar-plane image — the slice whose **line slope is the disparity**.

    An EPI is what makes a light field different from a pile of photographs: fix
    one image row and one angular row, and every scene point traces a *straight
    line* whose gradient ``dx/du`` is exactly its slope ``s``. Occlusion becomes
    one line crossing in front of another, which is why EPI methods handle it
    better than window matching.

      * ``axis="u"`` (horizontal): fix ``v = view`` (default: the centre row,
        ``(V-1)//2``) and image row ``y = index``; returns ``E[u, x]`` of shape
        ``(U, W)``.
      * ``axis="v"`` (vertical): fix ``u = view`` and image column ``x = index``;
        returns ``E[v, y]`` of shape ``(V, H)``.

    **Raises** ``ValueError``: *lf* not a valid light field, unknown *axis*,
    *index* outside the spatial extent, *view* outside the angular extent.
    """
    op = "lf_epi"
    arr = _require_lf(lf, op)
    V, U, H, W = arr.shape
    ax = _choice(axis, "axis", ("u", "v", "horizontal", "vertical"), op)
    ax = "u" if ax in ("u", "horizontal") else "v"
    if ax == "u":
        vi = (V - 1) // 2 if view is None else _count(view, op + ": view", 0, V - 1)
        yi = _count(index, op + ": index (image row y)", 0, H - 1)
        return np.ascontiguousarray(arr[vi, :, yi, :])
    ui = (U - 1) // 2 if view is None else _count(view, op + ": view", 0, U - 1)
    xi = _count(index, op + ": index (image column x)", 0, W - 1)
    return np.ascontiguousarray(arr[:, ui, :, xi])


# --------------------------------------------------------------------------- #
# refocus / synthetic aperture                                                 #
# --------------------------------------------------------------------------- #
def _shifted_views(arr, slope, order, mode):
    """Yield every view shifted so the plane at *slope* lands on the same pixels."""
    V, U = arr.shape[0], arr.shape[1]
    vc, uc = _angular_centers(V, U)
    for v in range(V):
        for u in range(U):
            yield v, u, _shift2(arr[v, u], -slope * (v - vc), -slope * (u - uc),
                                order, mode)


def lf_refocus(lf, slope=0.0, *, interp="linear", edge="nearest"):
    """Shift-and-add refocus: the synthetic-aperture image focused at *slope*.

    Every view ``(v, u)`` is shifted by ``(-s*(v - v_c), -s*(u - u_c))`` — the
    **minus** undoes the parallax of a point at slope ``s`` — and the shifted
    views are averaged. Points at that slope add coherently and stay sharp;
    everything else is smeared by an amount proportional to its slope
    difference times the angular baseline. ``slope=0`` is the plane the array
    was already focused on and returns the plain average of the views.

    Ground truth it reproduces exactly (pinned in ``tests/test_lightfield.py``):
    a single-layer field synthesised at slope ``s0`` and refocused at ``s0``
    with ``edge="wrap"`` and an integer ``s0`` returns the original texture to
    5.6e-16; sweeping the slope, the variance of the result peaks at ``s0``
    (measured exactly on the sweep grid in all 18 texture/slope combinations
    listed in the module docstring), and refocusing at ``-s0`` does *not* —
    which is the check that catches a flipped shift sign.

    Returns a ``(H, W)`` 2-D image.

    **Raises** ``ValueError``: *lf* not a valid light field, a non-finite or
    over-large *slope* (:data:`MAX_ABS_SLOPE`), unknown *interp* / *edge*.
    """
    op = "lf_refocus"
    arr = _require_lf(lf, op)
    s = _slope(slope, op + ": slope")
    order = INTERP_ORDERS[_choice(interp, "interp", INTERP_ORDERS, op)]
    mode = EDGE_MODES[_choice(edge, "edge", EDGE_MODES, op)]
    acc = np.zeros(arr.shape[2:], dtype=np.float64)
    n = 0
    for _, _, img in _shifted_views(arr, s, order, mode):
        acc += img
        n += 1
    return acc / float(n)


def lf_focal_stack(lf, slopes=(-2.0, -1.0, 0.0, 1.0, 2.0), *,
                   interp="linear", edge="nearest"):
    """Refocus at every slope in *slopes* — a focal stack from one exposure.

    Returns a ``list`` of ``(H, W)`` images (the ``images`` type), in the order
    given, so :mod:`focus_stack`'s fusion and any multi-image operator applies
    unchanged. The physical camera equivalent is racking the focus N times; here
    it costs one exposure and ``len(slopes) * V * U`` image shifts.

    **Raises** ``ValueError``: *lf* not a valid light field, *slopes* empty or
    longer than :data:`MAX_STACK_SLICES`, any slope non-finite or over
    :data:`MAX_ABS_SLOPE`, a stack larger than :data:`MAX_STACK_ELEMENTS`,
    unknown *interp* / *edge*.
    """
    op = "lf_focal_stack"
    arr = _require_lf(lf, op)
    sl = _check_slopes(slopes, arr.shape[2] * arr.shape[3], op)
    order = INTERP_ORDERS[_choice(interp, "interp", INTERP_ORDERS, op)]
    mode = EDGE_MODES[_choice(edge, "edge", EDGE_MODES, op)]
    out = []
    for s in sl:
        acc = np.zeros(arr.shape[2:], dtype=np.float64)
        n = 0
        for _, _, img in _shifted_views(arr, s, order, mode):
            acc += img
            n += 1
        out.append(acc / float(n))
    return out


def _check_slopes(slopes, plane_elems, op):
    if isinstance(slopes, (str, bytes)) or np.isscalar(slopes):
        raise ValueError("%s: slopes must be a sequence, got %r — pass (s,) for "
                         "a single slice" % (op, type(slopes).__name__))
    sl = [_slope(s, "%s: slopes[%d]" % (op, i)) for i, s in enumerate(slopes)]
    if not sl:
        raise ValueError("%s: slopes is empty — nothing to compute" % (op,))
    if len(sl) > MAX_STACK_SLICES:
        raise ValueError("%s: %d slices exceeds the %d cap "
                         "(lightfield.MAX_STACK_SLICES)"
                         % (op, len(sl), MAX_STACK_SLICES))
    if len(sl) * plane_elems > MAX_STACK_ELEMENTS:
        raise ValueError("%s: a %d-slice stack of %d-pixel images is %d "
                         "elements, over the %d cap "
                         "(lightfield.MAX_STACK_ELEMENTS)"
                         % (op, len(sl), plane_elems, len(sl) * plane_elems,
                            MAX_STACK_ELEMENTS))
    return sl


def lf_aperture_mask(angular=(5, 5), shape="circle", *, radius=None,
                     inner=0.0, sigma=None, normalize=True):
    """Angular weighting mask — the synthetic aperture you stop down or shape.

    Returns a ``(V, U)`` 2-D array of per-view weights, indexed the same way as
    the light field's angular axes, for :func:`lf_synthetic_aperture`. The
    radius is measured in **angular steps** from the centre ``((V-1)/2,
    (U-1)/2)``, so ``radius=0`` selects the single centre view (an infinitely
    small aperture: everything in focus, no light) and the default
    ``radius = max(V-1, U-1)/2`` is the largest circle that fits.

      * ``circle``   — hard-edged disc, the physical iris.
      * ``square``   — Chebyshev disc; separable, the cheapest to reason about.
      * ``gaussian`` — apodised pupil (``sigma`` in angular steps, default
        ``radius/2``); no ringing in the defocus PSF.
      * ``annulus``  — ring between *inner* and *radius*; a coded aperture whose
        defocus PSF has more high-frequency content, which is what makes
        depth-from-defocus work better.

    With ``normalize=True`` (default) the weights sum to exactly 1, so a masked
    reduction is a weighted **mean** and its result is directly comparable with
    :func:`lf_refocus`. Set it to ``False`` to keep 0/1 selection weights.

    **Raises** ``ValueError``: an angular shape outside ``[1, MAX_ANGULAR]``, a
    negative *radius* / *inner* / *sigma*, ``inner >= radius``, an unknown
    *shape*, and — explicitly rather than returning a field of zeros — a mask
    that selects **no** view at all (an opaque aperture), which would make every
    downstream weighted mean a 0/0.
    """
    op = "lf_aperture_mask"
    if len(angular) != 2:
        raise ValueError("%s: angular must be (V, U)" % (op,))
    V = _count(angular[0], op + ": angular[0] (V)", 1, MAX_ANGULAR)
    U = _count(angular[1], op + ": angular[1] (U)", 1, MAX_ANGULAR)
    kind = _choice(shape, "shape", APERTURE_SHAPES, op)
    vc, uc = _angular_centers(V, U)
    r_max = max(V - 1, U - 1) / 2.0
    r = r_max if radius is None else _finite_scalar(radius, op + ": radius")
    if r < 0.0:
        raise ValueError("%s: radius must be >= 0, got %g (radius 0 selects the "
                         "single centre view)" % (op, r))
    ri = _finite_scalar(inner, op + ": inner")
    if ri < 0.0:
        raise ValueError("%s: inner must be >= 0, got %g" % (op, ri))
    if kind == "annulus" and ri >= r:
        raise ValueError("%s: annulus needs inner (%g) < radius (%g); otherwise "
                         "the ring is empty" % (op, ri, r))
    gv = np.arange(V, dtype=np.float64)[:, None] - vc
    gu = np.arange(U, dtype=np.float64)[None, :] - uc
    if kind == "square":
        d = np.maximum(np.abs(gv), np.abs(gu))
    else:
        d = np.hypot(gv, gu)
    if kind == "circle" or kind == "square":
        mask = (d <= r + 1e-12).astype(np.float64)
    elif kind == "annulus":
        mask = ((d <= r + 1e-12) & (d >= ri - 1e-12)).astype(np.float64)
    else:                                                    # gaussian
        sg = (r / 2.0) if sigma is None else _finite_scalar(sigma, op + ": sigma")
        if sg <= 0.0:
            raise ValueError("%s: sigma must be > 0 for a gaussian aperture, got "
                             "%g (use shape='circle' with radius=0 for a single "
                             "view)" % (op, sg))
        mask = np.exp(-0.5 * (d / sg) ** 2)
        mask[d > r + 1e-12] = 0.0
    total = float(mask.sum())
    if total <= 0.0:
        raise ValueError("%s: the %s aperture with radius %g selects no view at "
                         "all on a %dx%d angular grid (the nearest view is %g "
                         "steps from the centre) — an opaque aperture would make "
                         "every downstream weighted mean a 0/0"
                         % (op, kind, r, V, U, float(d.min())))
    return mask / total if normalize else mask


def lf_synthetic_aperture(lf, slope=0.0, mask=None, *, reduce="mean",
                          interp="linear", edge="nearest"):
    """Refocus through a shaped aperture — and, with ``reduce="median"``, through occluders.

    Same shift-and-add geometry as :func:`lf_refocus`, with two additions:

      * *mask* — a ``(V, U)`` weight array from :func:`lf_aperture_mask` (or your
        own). A small mask is a stopped-down aperture: less defocus blur, less
        light. ``None`` weights every view equally.
      * *reduce* — how the aligned views are combined. ``mean`` is the classical
        (and linear) synthetic aperture. ``median`` is the interesting one: when
        a foreground occluder covers a *minority* of the views at a pixel, the
        median rejects it and the background behind it is reconstructed —
        looking through a fence, or through a rack of parts. ``max`` / ``min``
        are the order-statistic extremes, useful for specular / shadow work.
        ``median``, ``max`` and ``min`` use the mask only to *select* views
        (weight > 0), because an order statistic has no meaningful weighting;
        that is stated here rather than silently ignoring the weights.

    Returns a ``(H, W)`` 2-D image.

    **Raises** ``ValueError``: *lf* not a valid light field, a *mask* whose
    shape is not ``(V, U)`` or which is non-finite / negative / selects no view,
    a non-finite or over-large *slope*, unknown *reduce* / *interp* / *edge*.
    """
    op = "lf_synthetic_aperture"
    arr = _require_lf(lf, op)
    V, U, H, W = arr.shape
    s = _slope(slope, op + ": slope")
    red = _choice(reduce, "reduce", REDUCERS, op)
    order = INTERP_ORDERS[_choice(interp, "interp", INTERP_ORDERS, op)]
    mode = EDGE_MODES[_choice(edge, "edge", EDGE_MODES, op)]
    if mask is None:
        wts = np.ones((V, U), dtype=np.float64)
    else:
        wts = _require_image(mask, op, "mask")
        if wts.shape != (V, U):
            raise ValueError("%s: mask shape %r does not match the light field's "
                             "angular shape (%d, %d)" % (op, wts.shape, V, U))
        if (wts < 0.0).any():
            raise ValueError("%s: mask has %d negative weight(s) — a pupil cannot "
                             "transmit a negative amount of light"
                             % (op, int((wts < 0.0).sum())))
    total = float(wts.sum())
    if total <= 0.0:
        raise ValueError("%s: mask selects no view (total weight %g) — an opaque "
                         "aperture; refusing the 0/0" % (op, total))
    if red == "mean":
        acc = np.zeros((H, W), dtype=np.float64)
        for v, u, img in _shifted_views(arr, s, order, mode):
            w = wts[v, u]
            if w != 0.0:
                acc += w * img
        return acc / total
    sel = [img for v, u, img in _shifted_views(arr, s, order, mode)
           if wts[v, u] > 0.0]
    stack = np.stack(sel, axis=0)
    if red == "median":
        return np.median(stack, axis=0)
    return stack.max(axis=0) if red == "max" else stack.min(axis=0)


# --------------------------------------------------------------------------- #
# depth                                                                        #
# --------------------------------------------------------------------------- #
def _focus_measure(img, measure, window):
    """Local sharpness of *img* — larger is sharper. Never negative."""
    if measure == "variance":
        m1 = _ndi.uniform_filter(img, window, mode="nearest")
        m2 = _ndi.uniform_filter(img * img, window, mode="nearest")
        return np.maximum(m2 - m1 * m1, 0.0)      # float noise only, not a clamp
    if measure == "gradient":
        gy, gx = np.gradient(img)
        return _ndi.uniform_filter(gy * gy + gx * gx, window, mode="nearest")
    lap_y = _ndi.correlate1d(img, [1.0, -2.0, 1.0], axis=0, mode="nearest")
    lap_x = _ndi.correlate1d(img, [1.0, -2.0, 1.0], axis=1, mode="nearest")
    return _ndi.uniform_filter(np.abs(lap_y) + np.abs(lap_x), window,
                               mode="nearest")


def lf_depth_from_focus(lf, slopes=(-2.0, -1.0, 0.0, 1.0, 2.0), *,
                        window=9, measure="laplacian", subpixel=True,
                        interp="linear", edge="nearest"):
    """Per-pixel slope from the **sharpness peak** across the refocus sweep.

    Refocus at every slope in *slopes*, measure local sharpness (*measure*:
    ``laplacian`` = summed modified Laplacian, the classical depth-from-focus
    operator; ``variance`` = local variance; ``gradient`` = local gradient
    energy) in a ``window x window`` neighbourhood, and take the slope at which
    each pixel is sharpest. With ``subpixel=True`` (default) the peak is refined
    by fitting a parabola through the winning sample and its two neighbours on a
    **uniformly** spaced sweep — on a non-uniform sweep the refinement is
    skipped rather than applied with the wrong spacing.

    Unbiased where :func:`lf_epi_slope` is not: measured 2026-09-01 on a
    5x5x64x64 synthetic field over a 121-point sweep from -3 to +3, the argmax
    landed **exactly** on the true slope in 18 of 18 combinations (true slopes
    0.0, +0.5, +1.0, +1.5, +2.0, -1.0 crossed with texture sigma 1.5 / 3.0 /
    5.0 px), and the sub-pixel refinement left every one of them unmoved. Its
    resolution, though, is whatever you put in *slopes* — it cannot see a plane
    you never refocused on.

    Returns ``(slope_map, sharpness)``: the ``(H, W)`` map of estimated slopes
    (in px per angular step) and the ``(H, W)`` peak focus-measure value, which
    is the honest confidence — a textureless pixel has no sharpness peak, gets
    an essentially arbitrary slope, and its ``sharpness`` is ~0. Threshold on it
    rather than trusting the map everywhere.

    **Raises** ``ValueError``: *lf* not a valid light field, *slopes* empty /
    over :data:`MAX_STACK_SLICES` / over :data:`MAX_STACK_ELEMENTS` / containing
    a non-finite or over-large value, an even or non-positive *window*, unknown
    *measure* / *interp* / *edge*.
    """
    op = "lf_depth_from_focus"
    arr = _require_lf(lf, op)
    H, W = arr.shape[2], arr.shape[3]
    sl = _check_slopes(slopes, H * W, op)
    win = _odd_window(window, "window", op)
    meas = _choice(measure, "measure", FOCUS_MEASURES, op)
    stack = lf_focal_stack(arr, sl, interp=interp, edge=edge)
    fm = np.stack([_focus_measure(img, meas, win) for img in stack], axis=0)
    idx = np.argmax(fm, axis=0)
    slopes_arr = np.asarray(sl, dtype=np.float64)
    best = slopes_arr[idx]
    peak = np.take_along_axis(fm, idx[None], axis=0)[0]
    if subpixel and len(sl) >= 3:
        step = np.diff(slopes_arr)
        if np.allclose(step, step[0], rtol=1e-9, atol=1e-12) and step[0] != 0.0:
            interior = (idx > 0) & (idx < len(sl) - 1)
            i0 = np.clip(idx, 1, len(sl) - 2)
            y0 = np.take_along_axis(fm, (i0 - 1)[None], axis=0)[0]
            y1 = np.take_along_axis(fm, i0[None], axis=0)[0]
            y2 = np.take_along_axis(fm, (i0 + 1)[None], axis=0)[0]
            den = y0 - 2.0 * y1 + y2
            # den == 0 means a flat (or perfectly linear) triple: no parabola
            # vertex exists, so leave those pixels on the sampled grid value.
            ok = interior & (den < 0.0)                  # a real maximum only
            delta = np.zeros_like(den)
            np.divide(0.5 * (y0 - y2), den, out=delta, where=ok)
            np.clip(delta, -0.5, 0.5, out=delta)         # vertex inside the cell
            best = np.where(ok, slopes_arr[i0] + delta * step[0], best)
    return best, peak


def lf_epi_slope(lf, *, window=9, min_energy=1e-10):
    """Per-pixel slope from the **EPI line orientation** (structure tensor, one pass).

    A scene point traces a straight line in the epipolar-plane image
    (:func:`lf_epi`), so along that line the intensity is constant:
    ``E_u + s * E_x = 0``. Accumulating that constraint over the whole angular
    grid and a ``window x window`` spatial neighbourhood gives the closed-form
    least-squares slope ``s = -(J_ux + J_vy) / (J_xx + J_yy)`` with
    ``J_ab = sum(E_a * E_b)`` — one pass over the light field, no sweep, both
    the horizontal and vertical EPI directions pooled.

    **This estimator is biased, and the bias is the reason to also run**
    :func:`lf_depth_from_focus`. It is ordinary (not total) least squares on
    finite differences, so it needs the EPI line to advance less than roughly
    one texture correlation length per view. Measured 2026-09-01 on
    5x5x64x64 synthetic fields, median over the interior: with texture
    ``sigma = 1.5`` px, true ``+1.00 -> +1.0004``, ``+0.50 -> +0.5285``,
    ``+1.50 -> +1.3018``, ``+2.00 -> +1.4614``; with ``sigma = 5.0`` px the same
    slopes give ``+1.0003``, ``+0.5029``, ``+1.4827``, ``+1.9482``. Integer
    slopes on a wrapped field come back within 4e-4 and ``s = 0`` is exact;
    ``|s| > 1`` is under-estimated, by 27% at ``s = 2`` on the roughest texture.
    Use it as a fast dense initialiser, not as the final word.

    Returns ``(slope_map, energy)``: the ``(H, W)`` slope map and the ``(H, W)``
    gradient energy ``J_xx + J_yy`` that was the denominator. Pixels whose
    energy is below *min_energy* have **no** measurable parallax (a flat patch
    of sky); their slope is set to 0 and their energy reported as-is, so you
    threshold on ``energy`` instead of being handed a plausible-looking number
    divided by ~0.

    **Raises** ``ValueError``: *lf* not a valid light field, an angular/spatial
    shape where *neither* EPI direction carries information (the horizontal EPI
    needs ``U >= 2`` **and** ``W >= 2``, the vertical needs ``V >= 2`` and
    ``H >= 2``), an even or non-positive *window*, a non-positive *min_energy*.
    """
    op = "lf_epi_slope"
    arr = _require_lf(lf, op)
    V, U, H, W = arr.shape
    # Both a second view *and* a second pixel are needed along a direction: the
    # constraint is E_u + s*E_x = 0, so a single-column field (W == 1) has no
    # E_x and the horizontal EPI carries no slope information at all. The 2026
    # -09-01 adversarial pass hit this as a raw numpy "Shape of array too small
    # to calculate a numerical gradient" leaking out of np.gradient.
    use_h = U >= 2 and W >= 2
    use_v = V >= 2 and H >= 2
    if not (use_h or use_v):
        raise ValueError("%s: no direction carries slope information — the "
                         "horizontal EPI needs U >= 2 and W >= 2 (got %d, %d) "
                         "and the vertical EPI needs V >= 2 and H >= 2 (got %d, "
                         "%d). A single view, or a single-pixel-wide image, has "
                         "no parallax to measure." % (op, U, W, V, H))
    win = _odd_window(window, "window", op)
    eps = _positive(min_energy, op + ": min_energy")
    num = np.zeros(arr.shape[2:], dtype=np.float64)
    den = np.zeros(arr.shape[2:], dtype=np.float64)
    if use_h:
        e_u = np.gradient(arr, axis=1)
        e_x = np.gradient(arr, axis=3)
        num += (e_u * e_x).sum(axis=(0, 1))
        den += (e_x * e_x).sum(axis=(0, 1))
    if use_v:
        e_v = np.gradient(arr, axis=0)
        e_y = np.gradient(arr, axis=2)
        num += (e_v * e_y).sum(axis=(0, 1))
        den += (e_y * e_y).sum(axis=(0, 1))
    num = _ndi.uniform_filter(num, win, mode="nearest")
    den = _ndi.uniform_filter(den, win, mode="nearest")
    slope = np.zeros_like(den)
    ok = den > eps
    np.divide(-num, den, out=slope, where=ok)
    slope[~ok] = 0.0
    return slope, den


def lf_disparity_to_depth(slope, focal_px=1000.0, baseline=1.0, *,
                          far_depth=None, min_slope=1e-6):
    """Slope (px per angular step) -> metric depth, the camera-array model.

    For a rectified array of viewpoints spaced *baseline* apart with focal
    length *focal_px* expressed **in pixels of the sub-aperture image**, a point
    at distance ``Z`` shifts by ``|s| = focal_px * baseline / Z`` pixels per
    step. Inverting: ``Z = focal_px * baseline / |s|``, returned in whatever
    length unit *baseline* was given in (mm in, mm out).

    Only ``|s|`` enters, deliberately. The *sign* of the slope says which side of
    the focal plane a point is on, and which sign means "nearer" depends on how
    the angular axis was oriented when the field was decoded — a convention this
    module cannot know and refuses to guess. If your decode puts near objects at
    negative slope, negate before calling.

    *far_depth* is the fail-closed switch for the ``s -> 0`` pole (a point at
    infinity has zero parallax). ``None`` (default) makes any ``|s| < min_slope``
    a ``ValueError`` naming how many pixels were affected — mask them, or pass an
    explicit saturation distance as *far_depth* and get that value there. There
    is no silent ``inf`` and no silent clamp.

    Accepts a scalar or any array; returns the same shape (a scalar in gives a
    0-d array out, so downstream code has one type to handle).

    **Raises** ``ValueError``: non-finite *slope* / *focal_px* / *baseline*, a
    non-positive *focal_px* / *baseline* / *min_slope*, a negative *far_depth*,
    and ``|slope| < min_slope`` anywhere when *far_depth* is ``None``.
    """
    op = "lf_disparity_to_depth"
    s = _as_float_array(slope, op + ": slope")
    f = _positive(focal_px, op + ": focal_px")
    b = _positive(baseline, op + ": baseline")
    ms = _positive(min_slope, op + ": min_slope")
    mag = np.abs(s)
    small = mag < ms
    if small.any():
        if far_depth is None:
            raise ValueError("%s: %d of %d slope value(s) are below min_slope=%g "
                             "(|s| min = %g) — those points have no measurable "
                             "parallax and are at (or beyond) infinity. Mask "
                             "them, or pass far_depth=<distance> to saturate "
                             "there explicitly; refusing to return a silent inf"
                             % (op, int(small.sum()), int(mag.size), ms,
                                float(mag.min())))
        fd = _finite_scalar(far_depth, op + ": far_depth")
        if fd < 0.0:
            raise ValueError("%s: far_depth must be >= 0, got %g" % (op, fd))
    else:
        fd = 0.0
    safe = np.where(small, 1.0, mag)
    depth = f * b / safe
    out = np.where(small, fd, depth)
    # float64 overflow: focal_px * baseline can be finite while the quotient is
    # not (2026-09-01 adversarial pass: focal_px = baseline = 1e300 with
    # min_slope = 1e-300 returned a whole array of silent +inf). Non-finite
    # output is never a contract in this module, so it is refused here.
    if out.size and not np.isfinite(out).all():
        raise ValueError("%s: focal_px * baseline / |slope| overflowed float64 "
                         "for %d value(s) (focal_px=%g, baseline=%g, "
                         "|s| min=%g) — the units are inconsistent by many "
                         "orders of magnitude; refusing to return a silent inf"
                         % (op, int((~np.isfinite(out)).sum()), f, b,
                            float(mag.min())))
    return out


def lf_all_in_focus(lf, slope_map, levels=None, *, n_levels=16,
                    interp="linear", edge="nearest"):
    """Composite one everywhere-sharp image by refocusing each pixel at its own slope.

    Builds a focal stack at *levels* and, for every pixel, takes the slice whose
    level is closest to ``slope_map`` there. This is the "2-D image" half of what
    a plenoptic camera delivers, at the full depth range rather than the depth of
    field of one focus setting.

    *levels* controls which refocus planes are actually rendered, and the
    ``None`` default has two documented branches — a continuous slope map has
    one distinct value per pixel, and rendering a refocus plane for each of
    those would be tens of thousands of full-frame shifts:

      * if *slope_map* holds at most *n_levels* distinct values (the case when
        it came from :func:`lf_depth_from_focus` with ``subpixel=False``), those
        exact values are used and the composite is exact;
      * otherwise the map's range is quantised to *n_levels* evenly spaced
        planes (default 16), which is a real approximation: a pixel whose true
        slope falls between two planes is refocused at the nearer one. Pass
        *levels* explicitly — e.g. the sweep you handed
        :func:`lf_depth_from_focus` — when that matters.

    Returns a ``(H, W)`` 2-D image.

    **Raises** ``ValueError``: *lf* not a valid light field, a *slope_map* that
    is not 2-D / not ``(H, W)`` / non-finite, *levels* empty or over the stack
    caps, *n_levels* outside ``[1, MAX_STACK_SLICES]``, unknown *interp* /
    *edge*.
    """
    op = "lf_all_in_focus"
    arr = _require_lf(lf, op)
    H, W = arr.shape[2], arr.shape[3]
    sm = _require_image(slope_map, op, "slope_map")
    if sm.shape != (H, W):
        raise ValueError("%s: slope_map shape %r does not match the light "
                         "field's spatial shape (%d, %d)" % (op, sm.shape, H, W))
    if levels is None:
        nl = _count(n_levels, op + ": n_levels", 1, MAX_STACK_SLICES)
        uniq = np.unique(sm)
        if uniq.size <= nl:
            want = tuple(float(x) for x in uniq)
        else:
            want = tuple(float(x) for x in
                         np.linspace(float(sm.min()), float(sm.max()), nl))
        lv = _check_slopes(want, H * W, op)
    else:
        lv = _check_slopes(levels, H * W, op)
    stack = np.stack(lf_focal_stack(arr, lv, interp=interp, edge=edge), axis=0)
    lv_arr = np.asarray(lv, dtype=np.float64)
    pick = np.abs(sm[None, :, :] - lv_arr[:, None, None]).argmin(axis=0)
    return np.take_along_axis(stack, pick[None], axis=0)[0]


# --------------------------------------------------------------------------- #
# design                                                                       #
# --------------------------------------------------------------------------- #
def lf_plenoptic_design(focal_mm=50.0, f_number=8.0, object_mm=300.0,
                        pixel_um=3.45, mla_pitch_um=27.6,
                        sensor_px=(2048, 2448), *, subpixel_px=0.1):
    """Size a plenoptic camera: what angular/spatial resolution and depth range you buy.

    The plenoptic trade in one table. A microlens spanning ``mla_pitch_um /
    pixel_um`` pixels turns that many pixels into that many *directions*, so the
    sensor's pixel count is unchanged but the image is ``U*V`` times smaller and
    carries ``U*V`` viewpoints. This operator composes :mod:`optics` rather than
    re-deriving it: ``optics.thin_lens`` places the image, and
    ``optics.depth_of_field`` is called **twice** — once with the pixel pitch as
    the circle of confusion (the depth of field of a single refocused slice) and
    once with the *microlens* pitch (the range over which refocusing can still
    recover a sharp image). Their ratio is the refocusing gain, and it comes out
    near the angular resolution, which is the textbook result.

    Returns a dict — ``angular_u`` / ``angular_v`` (whole pixels per microlens,
    from ``floor``) · ``angular_exact`` (the unrounded ratio) and
    ``pitch_is_integer`` (whether the MLA pitch is a whole number of pixels; it
    usually is not, which is why real decoding needs sub-pixel calibration) ·
    ``spatial_w`` / ``spatial_h`` (microlenses = sub-aperture image size) ·
    ``n_views`` · ``resolution_loss`` (``U*V``) · ``image_mm`` /
    ``magnification`` / ``working_distance_mm`` from the thin lens ·
    ``aperture_mm`` (``f/N``) · ``baseline_mm`` (viewpoint spacing across the
    pupil, ``aperture / (U - 1)``) · ``focal_px_subaperture`` (focal length in
    units of the *microlens* pitch, the pixel of a sub-aperture image) ·
    ``dof_pixel_mm`` / ``dof_refocus_mm`` and ``refocus_gain`` · and
    ``depth_precision_mm``, the object-side distance change that moves the
    disparity by *subpixel_px* pixels (``Z^2 * dp / (focal_px * baseline)``) —
    the honest depth resolution at *object_mm*.

    **Raises** ``ValueError``: any non-positive or non-finite length, an
    ``mla_pitch_um`` smaller than two *pixel_um* (fewer than 2 directions is not
    a light field), a sensor smaller than one microlens, a non-positive
    *subpixel_px*, ``object_mm == focal_mm`` (propagated from
    ``optics.thin_lens``: the object images at infinity), and an angular
    resolution of 1 in either axis, where the baseline would be a 0/0.
    """
    op = "lf_plenoptic_design"
    f = _positive(focal_mm, op + ": focal_mm")
    N = _positive(f_number, op + ": f_number")
    s_o = _positive(object_mm, op + ": object_mm")
    p_um = _positive(pixel_um, op + ": pixel_um")
    m_um = _positive(mla_pitch_um, op + ": mla_pitch_um")
    dp = _positive(subpixel_px, op + ": subpixel_px")
    if len(sensor_px) != 2:
        raise ValueError("%s: sensor_px must be (height_px, width_px)" % (op,))
    sh = _count(sensor_px[0], op + ": sensor_px[0]", 1, 1 << 20)
    sw = _count(sensor_px[1], op + ": sensor_px[1]", 1, 1 << 20)
    ratio = m_um / p_um
    if ratio < 2.0:
        raise ValueError("%s: mla_pitch_um / pixel_um = %g < 2 — a microlens "
                         "covering fewer than 2 pixels records fewer than 2 "
                         "directions, which is not a light field" % (op, ratio))
    ang = int(np.floor(ratio + 1e-9))
    if ang < 2:
        raise ValueError("%s: angular resolution floors to %d" % (op, ang))
    spatial_h, spatial_w = sh // ang, sw // ang
    if spatial_h < 1 or spatial_w < 1:
        raise ValueError("%s: a %dx%d sensor holds no whole %dx%d microlens "
                         "block" % (op, sh, sw, ang, ang))
    lens = _optics.thin_lens(f, s_o)
    aperture_mm = f / N
    baseline_mm = aperture_mm / float(ang - 1)
    focal_px_sub = f / (m_um * 1e-3)          # focal length in microlens pitches
    dof_px = _optics.depth_of_field(f, N, s_o, p_um * 1e-3)
    dof_ml = _optics.depth_of_field(f, N, s_o, m_um * 1e-3)
    gain = (dof_ml["depth_mm"] / dof_px["depth_mm"]
            if np.isfinite(dof_ml["depth_mm"]) and np.isfinite(dof_px["depth_mm"])
            and dof_px["depth_mm"] > 0.0 else float("nan"))
    if not np.isfinite(gain):
        # Past the hyperfocal distance the far limit is infinite by contract in
        # optics.depth_of_field; a ratio of infinities is not a number, and this
        # module does not return silent NaN.
        raise ValueError("%s: at object_mm = %g the depth of field is already "
                         "unbounded (hyperfocal %g mm for the microlens circle "
                         "of confusion), so the refocusing gain is a ratio of "
                         "infinities. Move the object closer or open the "
                         "aperture." % (op, s_o, dof_ml["hyperfocal_mm"]))
    precision = (s_o ** 2) * dp / (focal_px_sub * baseline_mm)
    return {
        "angular_u": int(ang), "angular_v": int(ang),
        "angular_exact": float(ratio),
        "pitch_is_integer": bool(abs(ratio - round(ratio)) < 1e-9),
        "spatial_w": int(spatial_w), "spatial_h": int(spatial_h),
        "n_views": int(ang * ang), "resolution_loss": int(ang * ang),
        "image_mm": float(lens["image_mm"]),
        "magnification": float(lens["magnification"]),
        "working_distance_mm": float(lens["working_distance_mm"]),
        "aperture_mm": float(aperture_mm),
        "baseline_mm": float(baseline_mm),
        "focal_px_subaperture": float(focal_px_sub),
        "dof_pixel_mm": float(dof_px["depth_mm"]),
        "dof_refocus_mm": float(dof_ml["depth_mm"]),
        "refocus_gain": float(gain),
        "depth_precision_mm": float(precision),
    }
