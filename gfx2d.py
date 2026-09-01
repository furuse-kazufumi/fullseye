# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gfx2d — real-time 2-D graphics: compositing, sprites, tiles, particles, 2-D
lighting and post-processing.

The library already renders 3-D (``render3d`` / ``render_beauty`` / ``render_ao``
/ ``render_shade`` / ``render_shadow`` / ``render_ssaa`` / ``render_tonemap``).
What it had no vocabulary for is the *other* half of what a screen shows: a
sprite blitted over a background, a tile grid, a spark shower, a light cone, and
the post chain that ties them into one picture.

Why a vision library wants this
-------------------------------
The same reason :mod:`defectgen` draws its scratches from stochastic geometry
rather than from photographs: **a sprite is an object whose truth is known**.
Its silhouette, its position and its coverage are the numbers that produced it,
so a scene assembled from sprites arrives with a pixel-exact ground-truth mask
for free — the label is the input, not an annotation someone drew afterwards.
That makes this module a scene generator for detection, segmentation and
occlusion studies, and only incidentally a way to draw a game.

The one thing this family gets wrong quietly
--------------------------------------------
**Straight alpha and premultiplied alpha are the same four numbers with two
different meanings, and confusing them raises no exception.** The picture still
appears; it just grows a dark or bright halo one pixel wide around every
anti-aliased edge, which is exactly the kind of error that survives review.

So this module picks a canon and says it out loud:

* **Straight (non-premultiplied) alpha is canonical at every public boundary.**
  An ``rgba`` argument and an ``rgba`` return value hold ``(R, G, B, A)`` where
  ``R`` is the object's own colour, *independent of its coverage*. This is what
  an image file holds and what an artist edits.
* **The arithmetic is done premultiplied, internally**, because "over" and
  every resampling kernel are linear in premultiplied colour and are *not*
  linear in straight colour. :func:`premultiply` / :func:`unpremultiply` make
  the conversion explicit when a caller wants to stay in that space, and
  :func:`alpha_composite_premul` is the linear operator itself.

What the confusion actually costs, measured: a white disc with an
anti-aliased edge composited over black. Feeding its *straight* buffer to a
routine that assumes premultiplied gives a maximum error of **0.500** and a mean
error over the edge band of **0.253** (bright halo — every partially covered
pixel is drawn at full colour). Feeding a *premultiplied* buffer to a routine
that assumes straight gives a maximum error of **0.250**, mean **0.130** (dark
halo — coverage is applied twice). Both pictures are finite, plausible, and
wrong. Reproduced by ``tests/test_gfx2d.py::test_alpha_convention_confusion_is_measured``.

:func:`premultiply`'s output is checked on the way back in: a premultiplied
pixel must satisfy ``colour <= alpha``. That check catches a straight buffer
handed to a premultiplied consumer **only where the colour exceeds the
coverage** — bright sprites on soft edges, which is the common case, but a
sprite darker than its own alpha slips through it silently. The type check is a
net, not a proof; the canon in the docstring is the proof.

Colour space
------------
Values are **not** assumed to be linear light. Two groups of operators live
here and they want different encodings:

* Encoding-domain (the W3C definitions are written on the encoded values):
  :func:`blend_mode`, :func:`layer_stack`, :func:`dither`,
  :func:`palette_quantize`, :func:`color_grade`.
* Linear-light physics (adding two lights must add their radiance):
  :func:`radial_light`, :func:`light_mask`, :func:`normal_map_shade`,
  :func:`bloom`, :func:`particle_render` in ``"add"`` mode.

Neither group converts for you, because a silent conversion is the same class of
bug as the alpha one. :func:`srgb_to_linear` and :func:`linear_to_srgb` are
provided so the choice is written in the caller's code. Measured cost of getting
it wrong: adding two 0.5 sRGB lights in the encoded domain gives 1.000, while
the physically correct answer is 0.735 sRGB — a 36 % overshoot that reads as
"the highlight blew out" rather than as a bug.

Conventions
-----------
* ``rgb`` is ``(H, W, 3)`` float64 in ``[0, 1]``; ``rgba`` is ``(H, W, 4)``
  float64 with straight colour in ``[0, 1]`` and alpha in ``[0, 1]``.
* Pixel addressing is ``(row, column)`` for arrays, as everywhere else in this
  library. Where an operator takes a *point* it takes ``(x, y)`` — x is the
  column, y is the row, y grows downward — matching :mod:`flow` and
  :mod:`geometry2d`. Every such argument is named ``x``/``y`` or documented as
  ``(x, y)`` so the two orders never appear unlabelled.
* Angles are in degrees and a positive angle turns the content **clockwise on
  screen** (a consequence of the row axis pointing down).
* Randomness is drawn only from an explicit ``seed`` argument, through
  :class:`numpy.random.Generator`. The same seed gives the same bytes.

Sources
-------
* T. Porter & T. Duff, *Compositing Digital Images*, SIGGRAPH 1984 — the "over"
  operator and the premultiplied form used here.
* *Compositing and Blending Level 1*, W3C Candidate Recommendation — the
  separable blend-mode formulae reproduced in :data:`BLEND_MODES`.
* B. E. Bayer, *An optimum method for two-level rendition of continuous-tone
  pictures*, IEEE ICC 1973 — the ordered dither matrix.
* R. W. Floyd & L. Steinberg, *An adaptive algorithm for spatial greyscale*,
  Proc. SID 17(2), 1976 — the error-diffusion weights.
* J. F. Blinn, *Models of light reflection for computer synthesized pictures*,
  SIGGRAPH 1977 — the halfway-vector specular term in
  :func:`normal_map_shade`.
* IEC 61966-2-1 (sRGB) — the transfer function in :func:`srgb_to_linear`.

Honest limitations
------------------
* **Clipping to [0, 1] destroys information and this module does it anyway.**
  ``blend_mode("add")``, :func:`bloom` and :func:`particle_render` can exceed 1
  and the excess is clipped, not returned. Measured on the example scene, the
  bloom pass clips 1.8 % of pixels and loses 0.7 % of the added energy. Work in
  an unclipped buffer of your own if that matters; there is no HDR sort here.
* **:func:`shadow_cast_2d` is a ray-marched visibility map, not a physical
  shadow.** It samples the occluder along the segment to the light at a finite
  step count, so an occluder thinner than the step spacing can be missed. The
  step count is reported in the argument, not hidden.
* **Rotation and scaling resample.** ``sprite_transform`` is exact only for the
  identity and for multiples of 90 degrees with ``interp="nearest"``; everything
  else costs the measured round-trip error documented in that function.
* **No text rendering.** Glyph rasterisation needs a font backend and belongs
  with :mod:`imagedraw`, which already owns that dependency.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

import palette

__all__ = [
    "BLEND_MODES",
    "DEFAULT_PALETTE",
    "alpha_composite",
    "alpha_composite_premul",
    "blend_mode",
    "bloom",
    "chromatic_aberration",
    "color_grade",
    "color_lut",
    "dither",
    "film_grain",
    "layer_stack",
    "light_mask",
    "linear_to_srgb",
    "nine_slice",
    "normal_map_decode",
    "normal_map_shade",
    "palette_quantize",
    "parallax_layers",
    "particle_emit",
    "particle_render",
    "particle_step",
    "premultiply",
    "radial_light",
    "shadow_cast_2d",
    "sprite_blit",
    "sprite_sheet_slice",
    "sprite_synthesize",
    "sprite_transform",
    "srgb_to_linear",
    "tilemap_render",
    "unpremultiply",
    "vignette",
    "viewport",
]

# --------------------------------------------------------------------------- #
# Caps. Each one exists because a small-looking argument otherwise turns into a #
# large allocation.                                                            #
# --------------------------------------------------------------------------- #

#: Largest side of any image accepted or produced.
MAX_DIM = 1 << 14

#: Largest pixel count in one image (2^24 = 16.7 M, i.e. 4096x4096).
MAX_PIXELS = 1 << 24

#: Largest number of layers in :func:`layer_stack` / :func:`parallax_layers`.
MAX_LAYERS = 64

#: Largest number of sprites in a sheet or tile set.
MAX_SPRITES = 4096

#: Largest particle count. :func:`particle_render` additionally caps
#: ``count * (2*radius+1)^2`` (see :data:`MAX_SPLAT_ELEMENTS`).
MAX_PARTICLES = 1 << 18

#: Largest ``count * kernel_area`` in :func:`particle_render`. The splat is
#: vectorised over an ``(N, K, K)`` block, so 2^24 float64 is 134 MB.
MAX_SPLAT_ELEMENTS = 1 << 24

#: Largest ``steps * H * W`` in :func:`shadow_cast_2d`.
MAX_RAY_ELEMENTS = 1 << 24

#: Largest side of a 3-D colour LUT (64^3 * 3 float64 = 6.3 MB).
MAX_LUT_SIZE = 64

#: Largest quantisation level count in :func:`dither`.
MAX_LEVELS = 256

#: Largest palette in :func:`palette_quantize`.
MAX_PALETTE = 4096

#: Absolute tolerance applied when checking that a value lies in ``[0, 1]``.
#: Values inside the tolerance are clipped; values outside are rejected. The
#: window exists because a legitimate float64 pipeline lands on ``1 + 2e-16``,
#: not because "slightly out of range" is acceptable.
RANGE_TOL = 1e-9

#: Default quantitative palette for :func:`palette_quantize` and for colour
#: arguments given as a role name — Okabe & Ito via :mod:`palette`.
DEFAULT_PALETTE = "okabe_ito"

#: The separable blend modes of *Compositing and Blending Level 1*, plus
#: ``"add"``. ``"add"`` is **not** a W3C blend mode: it is Porter & Duff's
#: ``plus`` restricted to colour and then clipped, and it is the only mode here
#: that is not closed under ``[0, 1]`` before clipping. It is included because
#: additive light is what a spark or a muzzle flash actually does.
BLEND_MODES = (
    "add",
    "color_burn",
    "color_dodge",
    "darken",
    "difference",
    "exclusion",
    "hard_light",
    "lighten",
    "multiply",
    "normal",
    "overlay",
    "screen",
    "soft_light",
)

_INTERP_ORDER = {"nearest": 0, "bilinear": 1, "bicubic": 3}

_ANCHORS = ("top_left", "top_right", "bottom_left", "bottom_right", "center")


# --------------------------------------------------------------------------- #
# Validation. Every public entry point goes through these; nothing downstream   #
# re-checks, so a bug here is a bug everywhere.                                 #
# --------------------------------------------------------------------------- #
def _as_array(value, name):
    """ndarray float64, finite, with a named error."""
    if isinstance(value, np.ma.MaskedArray):
        raise ValueError(f"{name}: masked arrays are not accepted (the mask has no "
                         "meaning for a pixel that is already carrying an alpha)")
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f"{name}: a bool is not an image")
    arr = np.asarray(value)
    if arr.dtype.kind == "c":
        raise ValueError(f"{name}: complex arrays are not accepted")
    if arr.dtype.kind not in "fiub":
        raise ValueError(f"{name}: expected a numeric array, got dtype {arr.dtype}")
    arr = np.ascontiguousarray(arr, dtype=np.float64)
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name}: contains NaN or infinity")
    return arr


def _check_hw(h, w, name):
    """Validate an image size, returning ints."""
    for v, label in ((h, "height"), (w, "width")):
        if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer)):
            raise ValueError(f"{name}: {label} must be an int, got {type(v).__name__}")
        if v < 1:
            raise ValueError(f"{name}: {label} must be >= 1, got {v}")
        if v > MAX_DIM:
            raise ValueError(f"{name}: {label} {v} exceeds MAX_DIM={MAX_DIM}")
    if int(h) * int(w) > MAX_PIXELS:
        raise ValueError(f"{name}: {h}x{w} = {int(h) * int(w)} pixels exceeds "
                         f"MAX_PIXELS={MAX_PIXELS}")
    return int(h), int(w)


def _clip01(arr, name, what="value"):
    """Reject values outside ``[0, 1]`` beyond :data:`RANGE_TOL`; clip the rest."""
    lo, hi = float(arr.min()), float(arr.max())
    if lo < -RANGE_TOL or hi > 1.0 + RANGE_TOL:
        raise ValueError(f"{name}: {what} must lie in [0, 1], got [{lo:.6g}, {hi:.6g}]")
    return np.clip(arr, 0.0, 1.0)


def _require_rgb(img, name="image"):
    """``(H, W, 3)`` float64 in ``[0, 1]``."""
    arr = _as_array(img, name)
    if arr.ndim != 3 or arr.shape[2] != 3:
        raise ValueError(f"{name}: expected an (H, W, 3) rgb image, got shape {arr.shape}")
    _check_hw(arr.shape[0], arr.shape[1], name)
    return _clip01(arr, name, "colour")


def _require_rgba(img, name="image"):
    """``(H, W, 4)`` float64, **straight** alpha, colour and alpha in ``[0, 1]``."""
    arr = _as_array(img, name)
    if arr.ndim != 3 or arr.shape[2] != 4:
        raise ValueError(f"{name}: expected an (H, W, 4) rgba image, got shape {arr.shape}")
    _check_hw(arr.shape[0], arr.shape[1], name)
    return _clip01(arr, name, "colour/alpha")


def _require_rgba_premul(img, name="image"):
    """``(H, W, 4)`` float64, **premultiplied**: additionally ``colour <= alpha``.

    The extra inequality is what separates the premultiplied sort from the
    straight one at runtime. It catches a straight buffer only where the colour
    exceeds the coverage; see the module docstring on why that is a net and not
    a proof.
    """
    arr = _require_rgba(img, name)
    over = float(np.max(arr[..., :3] - arr[..., 3:4]))
    if over > RANGE_TOL:
        raise ValueError(
            f"{name}: not premultiplied — colour exceeds alpha by {over:.6g} at the worst "
            "pixel. A premultiplied pixel satisfies colour <= alpha by construction; a "
            "straight-alpha buffer does not. Call premultiply() first.")
    return arr


def _same_shape(a, b, name_a, name_b):
    if a.shape != b.shape:
        raise ValueError(f"{name_a} shape {a.shape} != {name_b} shape {b.shape}; "
                         "this family never broadcasts images (a silent broadcast is a "
                         "silently wrong picture) — resize or blit explicitly")


def _scalar(value, name, lo=None, hi=None, allow_int=True):
    """Finite real scalar with named bounds. Rejects bool and str."""
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f"{name}: a bool is not a number")
    if isinstance(value, str):
        raise ValueError(f"{name}: a string is not a number, got {value!r}")
    if isinstance(value, np.ndarray) and value.ndim != 0:
        raise ValueError(f"{name}: expected a scalar, got an array of shape {value.shape}")
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name}: expected a number, got {type(value).__name__}") from None
    if not np.isfinite(out):
        raise ValueError(f"{name}: must be finite, got {out}")
    if lo is not None and out < lo:
        raise ValueError(f"{name}: must be >= {lo}, got {out}")
    if hi is not None and out > hi:
        raise ValueError(f"{name}: must be <= {hi}, got {out}")
    if not allow_int:
        pass
    return out


def _integer(value, name, lo=None, hi=None):
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f"{name}: a bool is not an int")
    if not isinstance(value, (int, np.integer)):
        raise ValueError(f"{name}: must be an int, got {type(value).__name__} "
                         f"({value!r}). Sub-pixel placement is sprite_transform's job, "
                         "not this argument's.")
    out = int(value)
    if lo is not None and out < lo:
        raise ValueError(f"{name}: must be >= {lo}, got {out}")
    if hi is not None and out > hi:
        raise ValueError(f"{name}: must be <= {hi}, got {out}")
    return out


def _resolve_color(color, name="color", channels=3, scheme=DEFAULT_PALETTE):
    """A colour is either a :mod:`palette` **role name** or an explicit tuple.

    Role names are the preferred form: they keep the same meaning in the same
    colour across every figure, and the default scheme is chosen so the pairs do
    not rely on a red/green distinction.
    """
    if isinstance(color, str):
        rgb = palette.role_color(color, scheme)  # raises ValueError on an unknown role
        out = list(rgb) + [1.0] * (channels - 3)
        return np.asarray(out[:channels], dtype=np.float64)
    arr = _as_array(color, name)
    if arr.ndim != 1 or arr.size not in (3, 4):
        raise ValueError(f"{name}: expected a role name from palette.ROLES "
                         f"{palette.ROLES} or a 3/4-tuple, got shape {arr.shape}")
    if arr.size == 3 and channels == 4:
        arr = np.concatenate([arr, [1.0]])
    elif arr.size == 4 and channels == 3:
        arr = arr[:3]
    return _clip01(arr, name, "colour")


def _choice(value, name, allowed):
    if not isinstance(value, str):
        raise ValueError(f"{name}: expected one of {allowed}, got {type(value).__name__}")
    if value not in allowed:
        raise ValueError(f"{name}: unknown value {value!r}; known: {', '.join(allowed)}")
    return value


def _seed(value, name="seed"):
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f"{name}: a bool is not a seed")
    if not isinstance(value, (int, np.integer)):
        raise ValueError(f"{name}: must be a non-negative int (determinism is a "
                         f"contract here), got {type(value).__name__}")
    if value < 0:
        raise ValueError(f"{name}: must be >= 0, got {value}")
    return int(value)


# --------------------------------------------------------------------------- #
# Colour space                                                                  #
# --------------------------------------------------------------------------- #
def _transfer(img, name, forward):
    arr = _as_array(img, name)
    if arr.ndim not in (2, 3):
        raise ValueError(f"{name}: expected (H, W), (H, W, 3) or (H, W, 4), got {arr.shape}")
    if arr.ndim == 3 and arr.shape[2] not in (1, 3, 4):
        raise ValueError(f"{name}: expected 1, 3 or 4 channels, got {arr.shape[2]}")
    arr = _clip01(arr, name, "value")
    out = arr.copy()
    sl = (Ellipsis, slice(0, 3)) if (arr.ndim == 3 and arr.shape[2] == 4) else (Ellipsis,)
    out[sl] = forward(arr[sl])
    return out


def srgb_to_linear(img):
    """sRGB-encoded values to linear light (IEC 61966-2-1).

    An alpha channel, if present, is **not** transformed — coverage is already
    linear. Accepts ``(H, W)``, ``(H, W, 1|3|4)``.

    Use this before anything that adds or scales light (:func:`radial_light`,
    :func:`light_mask`, :func:`normal_map_shade`, :func:`bloom`) if the input
    came out of an image file. Skipping it does not raise: it makes highlights
    bloom too early and shadows too dark, by the amount quoted in the module
    docstring.
    """
    return _transfer(img, "img",
                     lambda c: np.where(c <= 0.04045, c / 12.92,
                                        ((np.maximum(c, 0.0) + 0.055) / 1.055) ** 2.4))


def linear_to_srgb(img):
    """Linear light back to sRGB encoding. Exact inverse of :func:`srgb_to_linear`."""
    return _transfer(img, "img",
                     lambda c: np.where(c <= 0.0031308, c * 12.92,
                                        1.055 * np.maximum(c, 0.0) ** (1.0 / 2.4) - 0.055))


# --------------------------------------------------------------------------- #
# Alpha: the two representations and the operator that is linear in one of them #
# --------------------------------------------------------------------------- #
def premultiply(rgba):
    """Straight-alpha ``rgba`` to **premultiplied** ``rgba``: ``(C*A, A)``.

    Lossy in one place, on purpose: the colour of a fully transparent pixel is
    multiplied to zero and cannot be recovered. That colour never affects a
    composite, so nothing downstream needs it — but a round trip through this
    pair is the identity only where ``alpha > 0``.
    """
    arr = _require_rgba(rgba, "rgba")
    out = arr.copy()
    out[..., :3] *= arr[..., 3:4]
    return out


def unpremultiply(rgba_premul):
    """**Premultiplied** ``rgba`` back to straight alpha: ``(C/A, A)``.

    Pixels with ``alpha == 0`` come back as transparent black (see
    :func:`premultiply` on why that is the only defensible answer).

    Raises ValueError: if the input is not premultiplied, detected as
    ``colour > alpha`` at some pixel.
    """
    arr = _require_rgba_premul(rgba_premul, "rgba_premul")
    a = arr[..., 3:4]
    out = np.zeros_like(arr)
    np.divide(arr[..., :3], a, out=out[..., :3], where=a > 0.0)
    out[..., 3:4] = a
    return np.clip(out, 0.0, 1.0)


def alpha_composite_premul(src, dst):
    """Porter–Duff **over** on premultiplied colour: ``src + dst*(1 - src.a)``.

    This is the operator; :func:`alpha_composite` is this one with a conversion
    on each side. Being affine in ``dst``, it is **exactly associative** —
    ``over(over(A, B), C) == over(A, over(B, C))`` to float64 rounding, which the
    test suite checks as an equality rather than a tolerance.
    """
    s = _require_rgba_premul(src, "src")
    d = _require_rgba_premul(dst, "dst")
    _same_shape(s, d, "src", "dst")
    inv = 1.0 - s[..., 3:4]
    return np.clip(s + d * inv, 0.0, 1.0)


def alpha_composite(src, dst):
    """Porter–Duff **over** on straight-alpha ``rgba`` (Porter & Duff 1984).

    ``a_o = a_s + a_d (1 - a_s)`` and
    ``C_o = (C_s a_s + C_d a_d (1 - a_s)) / a_o``, with ``C_o = 0`` where
    ``a_o == 0``.

    Both arguments must be straight-alpha and the **same shape** — this family
    never broadcasts, because a broadcast image is a silently wrong picture. Use
    :func:`sprite_blit` to place something smaller.
    """
    s = _require_rgba(src, "src")
    d = _require_rgba(dst, "dst")
    _same_shape(s, d, "src", "dst")
    return unpremultiply(alpha_composite_premul(premultiply(s), premultiply(d)))


# --------------------------------------------------------------------------- #
# Blend modes                                                                   #
# --------------------------------------------------------------------------- #
def _blend_separable(cb, cs, mode):
    """W3C *Compositing and Blending Level 1* separable blend functions.

    ``cb`` is the backdrop, ``cs`` the source; both in ``[0, 1]``.
    """
    if mode == "normal":
        return cs
    if mode == "multiply":
        return cb * cs
    if mode == "screen":
        return cb + cs - cb * cs
    if mode == "darken":
        return np.minimum(cb, cs)
    if mode == "lighten":
        return np.maximum(cb, cs)
    if mode == "difference":
        return np.abs(cb - cs)
    if mode == "exclusion":
        return cb + cs - 2.0 * cb * cs
    if mode == "add":  # Porter & Duff plus, clipped. Not a W3C blend mode.
        return np.minimum(cb + cs, 1.0)
    if mode == "hard_light":
        return np.where(cs <= 0.5, cb * (2.0 * cs),
                        cb + (2.0 * cs - 1.0) - cb * (2.0 * cs - 1.0))
    if mode == "overlay":  # W3C: overlay(cb, cs) == hard_light(cs, cb)
        return _blend_separable(cs, cb, "hard_light")
    if mode == "soft_light":
        d = np.where(cb <= 0.25, ((16.0 * cb - 12.0) * cb + 4.0) * cb, np.sqrt(cb))
        return np.where(cs <= 0.5,
                        cb - (1.0 - 2.0 * cs) * cb * (1.0 - cb),
                        cb + (2.0 * cs - 1.0) * (d - cb))
    if mode == "color_dodge":
        out = np.where(cs >= 1.0, 1.0, np.minimum(1.0, cb / np.maximum(1.0 - cs, 1e-300)))
        return np.where(cb <= 0.0, 0.0, out)
    if mode == "color_burn":
        out = np.where(cs <= 0.0, 0.0,
                       1.0 - np.minimum(1.0, (1.0 - cb) / np.maximum(cs, 1e-300)))
        return np.where(cb >= 1.0, 1.0, out)
    raise ValueError(f"mode: unknown blend mode {mode!r}; known: {', '.join(BLEND_MODES)}")


def blend_mode(base, top, mode="normal", opacity=1.0):
    """Blend two opaque ``rgb`` images with a named mode (W3C Level 1).

    With an opaque backdrop the specification reduces to a lerp,
    ``Co = (1 - opacity)*Cb + opacity*B(Cb, Cs)``, so ``opacity=0`` returns the
    backdrop **exactly** and ``mode="normal", opacity=1`` returns the source
    exactly. Both identities are checked bit-for-bit in the test suite.

    Named ``blend_mode`` and not ``blend`` because :func:`imagemorph.blend`
    already owns that name for a two-image cross-fade; two functions called
    ``blend`` with different signatures is exactly the kind of collision this
    library's naming test exists to prevent.

    Raises ValueError: unknown mode, mismatched shapes, opacity outside
    ``[0, 1]``, values outside ``[0, 1]``.
    """
    cb = _require_rgb(base, "base")
    cs = _require_rgb(top, "top")
    _same_shape(cb, cs, "base", "top")
    mode = _choice(mode, "mode", BLEND_MODES)
    op = _scalar(opacity, "opacity", 0.0, 1.0)
    if op == 0.0:
        return cb.copy()
    blended = _blend_separable(cb, cs, mode)
    if op == 1.0:
        return np.clip(blended, 0.0, 1.0)
    return np.clip(cb + op * (blended - cb), 0.0, 1.0)


def layer_stack(layers):
    """Composite a z-ordered list of ``rgba`` layers, bottom first.

    Each layer is a dict:

    ``{"image": rgba, "mode": str = "normal", "opacity": float = 1.0}``

    and the W3C rule for a blend mode against a *partially transparent* backdrop
    is used — the blend function is weighted by the backdrop's own alpha,
    ``Cs' = (1 - a_b) Cs + a_b B(Cb, Cs)`` — so a layer over empty space keeps
    its own colour whatever the mode. The result is straight-alpha ``rgba``.

    All layers must share one shape; see :func:`alpha_composite` on why.

    Raises ValueError: empty list, more than :data:`MAX_LAYERS`, a non-dict
    entry, an unknown key, mismatched shapes.
    """
    if not isinstance(layers, (list, tuple)):
        raise ValueError(f"layers: expected a list of dicts, got {type(layers).__name__}")
    if len(layers) == 0:
        raise ValueError("layers: empty stack; there is no defensible size for the result")
    if len(layers) > MAX_LAYERS:
        raise ValueError(f"layers: {len(layers)} exceeds MAX_LAYERS={MAX_LAYERS}")
    known = {"image", "mode", "opacity"}
    acc = None
    for i, layer in enumerate(layers):
        if not isinstance(layer, dict):
            raise ValueError(f"layers[{i}]: expected a dict, got {type(layer).__name__}")
        extra = set(layer) - known
        if extra:
            raise ValueError(f"layers[{i}]: unknown key(s) {sorted(extra)}; known: "
                             f"{sorted(known)}. Offsets belong to sprite_blit.")
        if "image" not in layer:
            raise ValueError(f"layers[{i}]: missing 'image'")
        img = _require_rgba(layer["image"], f"layers[{i}]['image']")
        mode = _choice(layer.get("mode", "normal"), f"layers[{i}]['mode']", BLEND_MODES)
        op = _scalar(layer.get("opacity", 1.0), f"layers[{i}]['opacity']", 0.0, 1.0)
        if acc is None:
            acc = np.zeros_like(img)
        _same_shape(img, acc, f"layers[{i}]['image']", "layers[0]['image']")
        ab = acc[..., 3:4]
        cs = img[..., :3]
        if mode != "normal":
            cs = (1.0 - ab) * cs + ab * _blend_separable(acc[..., :3], cs, mode)
        src = np.concatenate([np.clip(cs, 0.0, 1.0), img[..., 3:4] * op], axis=2)
        acc = alpha_composite(src, acc)
    return acc


# --------------------------------------------------------------------------- #
# Sprites                                                                       #
# --------------------------------------------------------------------------- #
def _coverage(shape_fn, height, width, samples=4):
    """Anti-aliased coverage of an implicit shape by regular supersampling.

    ``shape_fn(x, y) -> bool`` is evaluated on an ``samples x samples`` grid
    inside each pixel, so coverage lands on the exact lattice ``k / samples**2``
    and is reproducible without any randomness.
    """
    off = (np.arange(samples) + 0.5) / samples - 0.5
    cov = np.zeros((height, width), dtype=np.float64)
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float64)
    for dy in off:
        for dx in off:
            cov += shape_fn(xx + dx, yy + dy).astype(np.float64)
    return cov / (samples * samples)


def sprite_synthesize(kind="disc", size=32, color="emphasis", thickness=0.25,
                      scheme=DEFAULT_PALETTE):
    """A deterministic anti-aliased test sprite, ``rgba`` ``(size, size, 4)``.

    The entry point of the sprite sort: it needs no asset on disk, and because
    the silhouette comes from an implicit equation the alpha channel *is* the
    ground-truth coverage mask — which is the whole reason this family belongs
    in a vision library.

    ``kind`` is ``"disc"``, ``"ring"``, ``"box"``, ``"diamond"`` or ``"star"``.
    ``color`` is a :mod:`palette` role name (default) or an explicit 3/4-tuple.
    ``thickness`` is the ring's wall as a fraction of the radius.

    Coverage is computed by 4x4 regular supersampling, so alpha takes values on
    the exact lattice ``k/16``.
    """
    kind = _choice(kind, "kind", ("disc", "ring", "box", "diamond", "star"))
    n = _integer(size, "size", 2, 4096)
    rgba = _resolve_color(color, "color", 4, scheme)
    th = _scalar(thickness, "thickness", 0.0, 1.0)
    c = (n - 1) / 2.0
    r = n / 2.0

    if kind == "disc":
        fn = lambda x, y: (x - c) ** 2 + (y - c) ** 2 <= r * r  # noqa: E731
    elif kind == "ring":
        r_in = r * (1.0 - th)
        fn = lambda x, y: (((x - c) ** 2 + (y - c) ** 2 <= r * r)  # noqa: E731
                           & ((x - c) ** 2 + (y - c) ** 2 >= r_in * r_in))
    elif kind == "box":
        fn = lambda x, y: (np.abs(x - c) <= r * 0.9) & (np.abs(y - c) <= r * 0.9)  # noqa: E731
    elif kind == "diamond":
        fn = lambda x, y: np.abs(x - c) + np.abs(y - c) <= r  # noqa: E731
    else:  # star: five-point, inner radius 0.42 of outer
        def fn(x, y):
            ang = np.arctan2(y - c, x - c)
            rad = np.hypot(x - c, y - c)
            k = 5.0
            wave = 0.71 + 0.29 * np.cos(k * (ang + np.pi / 2.0))
            return rad <= r * wave

    cov = _coverage(fn, n, n)
    out = np.empty((n, n, 4), dtype=np.float64)
    out[..., :3] = rgba[:3]
    out[..., 3] = cov * rgba[3]
    return out


def _anchor_origin(anchor, x, y, h, w):
    if anchor == "top_left":
        return y, x
    if anchor == "top_right":
        return y, x - w + 1
    if anchor == "bottom_left":
        return y - h + 1, x
    if anchor == "bottom_right":
        return y - h + 1, x - w + 1
    return y - h // 2, x - w // 2  # center


def sprite_blit(dst, sprite, x=0, y=0, anchor="top_left", flip_x=False, flip_y=False,
                opacity=1.0):
    """Composite ``sprite`` onto a copy of ``dst`` at integer ``(x, y)``.

    ``x`` is the column and ``y`` the row of the sprite's ``anchor`` point;
    ``anchor`` is one of ``"top_left"``, ``"top_right"``, ``"bottom_left"``,
    ``"bottom_right"``, ``"center"``.

    **Out-of-bounds behaviour is to clip silently, and that is a decision, not
    an oversight.** Half a sprite hanging off the edge of the screen is the
    normal case in this family, and raising there would make the common path the
    exceptional one. A sprite entirely outside returns ``dst`` unchanged. The
    contrast with :func:`viewport` — which raises for the same situation — is
    deliberate: a camera asking for pixels that do not exist is a bug in the
    caller's arithmetic, a sprite walking off screen is not.

    ``x``/``y`` must be **integers**. Sub-pixel placement changes the picture
    (it resamples), so it is :func:`sprite_transform`'s job and not a silent
    rounding here.
    """
    d = _require_rgba(dst, "dst")
    s = _require_rgba(sprite, "sprite")
    anchor = _choice(anchor, "anchor", _ANCHORS)
    x = _integer(x, "x", -MAX_DIM * 4, MAX_DIM * 4)
    y = _integer(y, "y", -MAX_DIM * 4, MAX_DIM * 4)
    for flag, nm in ((flip_x, "flip_x"), (flip_y, "flip_y")):
        if not isinstance(flag, (bool, np.bool_)):
            raise ValueError(f"{nm}: expected a bool, got {type(flag).__name__}")
    op = _scalar(opacity, "opacity", 0.0, 1.0)

    if flip_x:
        s = s[:, ::-1]
    if flip_y:
        s = s[::-1]
    sh, sw = s.shape[:2]
    dh, dw = d.shape[:2]
    r0, c0 = _anchor_origin(anchor, x, y, sh, sw)

    dr0, dr1 = max(0, r0), min(dh, r0 + sh)
    dc0, dc1 = max(0, c0), min(dw, c0 + sw)
    out = d.copy()
    if dr0 >= dr1 or dc0 >= dc1:
        return out  # entirely off screen
    sr0, sc0 = dr0 - r0, dc0 - c0
    patch = s[sr0:sr0 + (dr1 - dr0), sc0:sc0 + (dc1 - dc0)].copy()
    if op != 1.0:
        patch[..., 3] *= op
    out[dr0:dr1, dc0:dc1] = alpha_composite(patch, out[dr0:dr1, dc0:dc1])
    return out


def sprite_transform(sprite, angle_deg=0.0, scale=1.0, interp="bilinear", out_shape=None):
    """Rotate and/or scale an ``rgba`` sprite about its centre.

    A **positive** ``angle_deg`` turns the sprite clockwise on screen, because
    the row axis points down. ``interp`` is ``"nearest"``, ``"bilinear"`` or
    ``"bicubic"`` (a cubic spline; it overshoots, and the overshoot is clipped
    back into the premultiplied range).

    The resampling happens in **premultiplied** space and the result is
    converted back. Interpolating straight colour instead mixes in the colour of
    fully transparent pixels, which is invisible in the alpha channel and shows
    up as a dark fringe: measured on a white disc over black, resampling
    straight gives a maximum edge error of 0.121 against the premultiplied
    result, at every rotation angle that is not a multiple of 90 degrees.

    Exact where it can be: ``angle_deg=0, scale=1`` returns the input bit for
    bit, and a multiple of 90 degrees with ``interp="nearest"`` is an exact
    permutation of the pixels. Everything else costs interpolation: measured
    round-trip error for ``+37`` then ``-37`` degrees, bilinear, on the test
    sprite is a mean of 0.0159 and a maximum of 0.166 in alpha.

    ``out_shape`` is ``(height, width)``; the default is the bounding box of the
    transformed sprite, rounded up.
    """
    s = _require_rgba(sprite, "sprite")
    ang = _scalar(angle_deg, "angle_deg", -3.6e4, 3.6e4)
    sc = _scalar(scale, "scale", None, None)
    if sc <= 0.0:
        raise ValueError(f"scale: must be > 0, got {sc} (a zero or negative scale is a "
                         "flip or a collapse, not a scale — use flip_x/flip_y on blit)")
    if sc > 64.0:
        raise ValueError(f"scale: {sc} exceeds 64 (guard against an accidental allocation)")
    interp = _choice(interp, "interp", tuple(_INTERP_ORDER))
    h, w = s.shape[:2]

    if out_shape is None:
        th = np.radians(ang)
        co, si = abs(np.cos(th)), abs(np.sin(th))
        oh = int(np.ceil((h * co + w * si) * sc))
        ow = int(np.ceil((h * si + w * co) * sc))
        oh, ow = max(1, oh), max(1, ow)
    else:
        if not isinstance(out_shape, (tuple, list)) or len(out_shape) != 2:
            raise ValueError(f"out_shape: expected (height, width), got {out_shape!r}")
        oh, ow = out_shape
    oh, ow = _check_hw(oh, ow, "out_shape")

    if ang % 360.0 == 0.0 and sc == 1.0 and (oh, ow) == (h, w):
        return s.copy()

    th = np.radians(ang)
    cos, sin = float(np.cos(th)), float(np.sin(th))
    cy_o, cx_o = (oh - 1) / 2.0, (ow - 1) / 2.0
    cy_i, cx_i = (h - 1) / 2.0, (w - 1) / 2.0
    rr, cc = np.mgrid[0:oh, 0:ow].astype(np.float64)
    xd, yd = cc - cx_o, rr - cy_o
    xs = (cos * xd + sin * yd) / sc + cx_i
    ys = (-sin * xd + cos * yd) / sc + cy_i

    pm = premultiply(s)
    out = np.empty((oh, ow, 4), dtype=np.float64)
    order = _INTERP_ORDER[interp]
    for k in range(4):
        out[..., k] = ndimage.map_coordinates(pm[..., k], [ys, xs], order=order,
                                              mode="constant", cval=0.0, prefilter=order > 1)
    out[..., 3] = np.clip(out[..., 3], 0.0, 1.0)
    out[..., :3] = np.clip(out[..., :3], 0.0, out[..., 3:4])
    return unpremultiply(out)


def sprite_sheet_slice(sheet, tile_height, tile_width, margin=0, spacing=0, count=None):
    """Cut a sprite atlas into a list of equal ``rgba`` frames, row-major.

    ``margin`` is the border around the whole sheet, ``spacing`` the gap between
    neighbouring cells — the two numbers that every atlas exporter writes and
    that every hand-rolled slicer gets wrong by one.

    Returns a ``list`` of ``(tile_height, tile_width, 4)`` arrays. With
    ``margin=spacing=0`` it is the exact inverse of :func:`tilemap_render`.

    Raises ValueError: a sheet that does not contain a whole number of cells
    (a partial cell means the margin/spacing are wrong, and silently dropping it
    hides that), a ``count`` larger than the grid, more than
    :data:`MAX_SPRITES` cells.
    """
    sh = _require_rgba(sheet, "sheet")
    th = _integer(tile_height, "tile_height", 1, MAX_DIM)
    tw = _integer(tile_width, "tile_width", 1, MAX_DIM)
    mg = _integer(margin, "margin", 0, MAX_DIM)
    sp = _integer(spacing, "spacing", 0, MAX_DIM)
    H, W = sh.shape[:2]
    usable_h, usable_w = H - 2 * mg, W - 2 * mg
    if usable_h < th or usable_w < tw:
        raise ValueError(f"sheet {H}x{W} with margin {mg} holds no {th}x{tw} cell")
    if (usable_h + sp) % (th + sp) != 0 or (usable_w + sp) % (tw + sp) != 0:
        raise ValueError(
            f"sheet {H}x{W} with margin={mg}, spacing={sp} does not hold a whole number of "
            f"{th}x{tw} cells ({usable_h}x{usable_w} usable). A partial cell means the "
            "margin or spacing is wrong; dropping it silently would hide that.")
    rows = (usable_h + sp) // (th + sp)
    cols = (usable_w + sp) // (tw + sp)
    total = rows * cols
    if total > MAX_SPRITES:
        raise ValueError(f"{total} cells exceeds MAX_SPRITES={MAX_SPRITES}")
    if count is not None:
        count = _integer(count, "count", 1, total)
    else:
        count = total
    out = []
    for i in range(count):
        r, c = divmod(i, cols)
        r0 = mg + r * (th + sp)
        c0 = mg + c * (tw + sp)
        out.append(sh[r0:r0 + th, c0:c0 + tw].copy())
    return out


def nine_slice(sprite, left, right, top, bottom, out_height, out_width):
    """Stretch a frame to a new size without deforming its corners.

    The four corners are copied **bit for bit**, the four edges are stretched
    along one axis only, and the centre is stretched along both. This is the
    standard way a UI panel grows: the border keeps its thickness at any size.

    Stretching is nearest-neighbour on the interior spans, so an output the same
    size as the input is the exact identity — no resampling blur creeps in when
    a panel happens not to need stretching.

    Raises ValueError: borders that meet or cross (``left + right >= width``),
    an output smaller than the borders it must preserve.
    """
    s = _require_rgba(sprite, "sprite")
    h, w = s.shape[:2]
    l_ = _integer(left, "left", 0, w)
    r_ = _integer(right, "right", 0, w)
    t_ = _integer(top, "top", 0, h)
    b_ = _integer(bottom, "bottom", 0, h)
    oh, ow = _check_hw(out_height, out_width, "out")
    if l_ + r_ >= w:
        raise ValueError(f"left+right = {l_ + r_} must be < sprite width {w}")
    if t_ + b_ >= h:
        raise ValueError(f"top+bottom = {t_ + b_} must be < sprite height {h}")
    if ow < l_ + r_ or oh < t_ + b_:
        raise ValueError(f"out {oh}x{ow} is smaller than the borders to preserve "
                         f"({t_ + b_} rows, {l_ + r_} cols)")

    def idx(n_in, n_out):
        if n_out == 0:
            return np.zeros(0, dtype=np.intp)
        return np.floor((np.arange(n_out) + 0.5) * n_in / n_out).astype(np.intp)

    rows = np.concatenate([np.arange(t_), t_ + idx(h - t_ - b_, oh - t_ - b_),
                           np.arange(h - b_, h)]).astype(np.intp)
    cols = np.concatenate([np.arange(l_), l_ + idx(w - l_ - r_, ow - l_ - r_),
                           np.arange(w - r_, w)]).astype(np.intp)
    return s[np.ix_(rows, cols)].copy()


# --------------------------------------------------------------------------- #
# Tiles                                                                         #
# --------------------------------------------------------------------------- #
def tilemap_render(tiles, indices, empty=-1):
    """Paint a grid of tile indices into one ``rgba`` image.

    ``tiles`` is a list of equally sized ``rgba`` tiles (what
    :func:`sprite_sheet_slice` returns) or an ``(N, th, tw, 4)`` array.
    ``indices`` is a 2-D **integer** array; a cell equal to ``empty`` is left
    transparent. The result is ``(rows*th, cols*tw, 4)``.

    Every cell is a copy, not a resample, so the output equals the tile exactly.

    Raises ValueError: a float index array (a float "index" is a rounding waiting
    to happen), an index outside the tile set, tiles of differing shapes, an
    output past :data:`MAX_PIXELS`.
    """
    if isinstance(tiles, np.ndarray):
        if tiles.ndim != 4 or tiles.shape[3] != 4:
            raise ValueError(f"tiles: expected (N, th, tw, 4), got shape {tiles.shape}")
        tile_list = [tiles[i] for i in range(tiles.shape[0])]
    elif isinstance(tiles, (list, tuple)):
        tile_list = list(tiles)
    else:
        raise ValueError(f"tiles: expected a list of rgba tiles or an (N, th, tw, 4) "
                         f"array, got {type(tiles).__name__}")
    if not tile_list:
        raise ValueError("tiles: empty tile set")
    if len(tile_list) > MAX_SPRITES:
        raise ValueError(f"tiles: {len(tile_list)} exceeds MAX_SPRITES={MAX_SPRITES}")
    tiles_v = [_require_rgba(t, f"tiles[{i}]") for i, t in enumerate(tile_list)]
    th, tw = tiles_v[0].shape[:2]
    for i, t in enumerate(tiles_v):
        if t.shape[:2] != (th, tw):
            raise ValueError(f"tiles[{i}] is {t.shape[:2]}, expected {(th, tw)} — a tile "
                             "set with mixed sizes has no grid")

    idx = np.asarray(indices)
    if idx.dtype.kind not in "iu":
        raise ValueError(f"indices: must be an integer array, got dtype {idx.dtype}")
    if idx.ndim != 2:
        raise ValueError(f"indices: expected a 2-D grid, got shape {idx.shape}")
    empty = _integer(empty, "empty", -(1 << 31), 1 << 31)
    rows, cols = idx.shape
    _check_hw(rows * th, cols * tw, "tilemap output")
    bad = idx[(idx != empty) & ((idx < 0) | (idx >= len(tiles_v)))]
    if bad.size:
        raise ValueError(f"indices: {bad.size} cell(s) outside the tile set "
                         f"[0, {len(tiles_v) - 1}]; first offender {int(bad.flat[0])}")

    out = np.zeros((rows * th, cols * tw, 4), dtype=np.float64)
    for r in range(rows):
        for c in range(cols):
            k = int(idx[r, c])
            if k == empty:
                continue
            out[r * th:(r + 1) * th, c * tw:(c + 1) * tw] = tiles_v[k]
    return out


def parallax_layers(layers, camera_x, factors, camera_y=0.0, factors_y=None):
    """Scroll a set of ``rgba`` layers at different rates and composite them.

    ``layers[0]`` is the farthest layer and is drawn first. Each layer is
    shifted by ``-round(camera_x * factors[i])`` columns (and rows, if
    ``factors_y`` is given) and **wraps** — a parallax backdrop is a loop, and
    wrapping is what makes it one.

    Shifts are rounded to whole pixels, so the operation is a pure permutation:
    a shift of exactly the layer width returns the layer unchanged, bit for bit.
    Sub-pixel scrolling would resample every frame and accumulate blur, which is
    why it is not offered here — put the fractional part in
    :func:`sprite_transform` if you need it.
    """
    if not isinstance(layers, (list, tuple)) or not layers:
        raise ValueError("layers: expected a non-empty list of rgba images")
    if len(layers) > MAX_LAYERS:
        raise ValueError(f"layers: {len(layers)} exceeds MAX_LAYERS={MAX_LAYERS}")
    imgs = [_require_rgba(im, f"layers[{i}]") for i, im in enumerate(layers)]
    shape = imgs[0].shape
    for i, im in enumerate(imgs):
        _same_shape(im, imgs[0], f"layers[{i}]", "layers[0]")
    fx = np.asarray(factors, dtype=np.float64) if not isinstance(factors, np.ndarray) \
        else factors.astype(np.float64)
    if fx.ndim != 1 or fx.size != len(imgs):
        raise ValueError(f"factors: expected {len(imgs)} values (one per layer), got "
                         f"shape {np.shape(factors)}")
    if not np.all(np.isfinite(fx)):
        raise ValueError("factors: must be finite")
    cx = _scalar(camera_x, "camera_x", -1e9, 1e9)
    cy = _scalar(camera_y, "camera_y", -1e9, 1e9)
    if factors_y is None:
        fy = np.zeros_like(fx)
    else:
        fy = np.asarray(factors_y, dtype=np.float64)
        if fy.shape != fx.shape:
            raise ValueError(f"factors_y: expected {fx.shape}, got {fy.shape}")
        if not np.all(np.isfinite(fy)):
            raise ValueError("factors_y: must be finite")

    acc = np.zeros(shape, dtype=np.float64)
    for im, f, g in zip(imgs, fx, fy):
        dx = int(np.rint(-cx * f))
        dy = int(np.rint(-cy * g))
        shifted = np.roll(im, (dy, dx), axis=(0, 1))
        acc = alpha_composite(shifted, acc)
    return acc


# --------------------------------------------------------------------------- #
# Particles                                                                     #
# --------------------------------------------------------------------------- #
_PARTICLE_KEYS = ("pos", "vel", "age", "life", "size", "color")


def _require_particles(state, name="state"):
    if not isinstance(state, dict):
        raise ValueError(f"{name}: expected a particle dict with keys {_PARTICLE_KEYS}, "
                         f"got {type(state).__name__}")
    missing = [k for k in _PARTICLE_KEYS if k not in state]
    if missing:
        raise ValueError(f"{name}: missing key(s) {missing}; expected {_PARTICLE_KEYS}")
    pos = _as_array(state["pos"], f"{name}['pos']")
    if pos.ndim != 2 or pos.shape[1] != 2:
        raise ValueError(f"{name}['pos']: expected (N, 2) as (x, y), got {pos.shape}")
    n = pos.shape[0]
    if n > MAX_PARTICLES:
        raise ValueError(f"{name}: {n} particles exceeds MAX_PARTICLES={MAX_PARTICLES}")
    vel = _as_array(state["vel"], f"{name}['vel']")
    if vel.shape != pos.shape:
        raise ValueError(f"{name}['vel']: expected {pos.shape}, got {vel.shape}")
    out = {"pos": pos, "vel": vel}
    for key in ("age", "life", "size"):
        arr = _as_array(state[key], f"{name}['{key}']")
        if arr.shape != (n,):
            raise ValueError(f"{name}['{key}']: expected ({n},), got {arr.shape}")
        out[key] = arr
    col = _as_array(state["color"], f"{name}['color']")
    if col.shape != (n, 4):
        raise ValueError(f"{name}['color']: expected ({n}, 4) rgba rows, got {col.shape}")
    out["color"] = _clip01(col, f"{name}['color']", "colour/alpha")
    if np.any(out["life"] <= 0.0):
        raise ValueError(f"{name}['life']: every lifetime must be > 0 (a zero lifetime "
                         "makes the fade a division by zero, not an instant death)")
    if np.any(out["size"] < 0.0):
        raise ValueError(f"{name}['size']: must be >= 0")
    return out


def particle_emit(count, seed, origin=(0.0, 0.0), spread=0.0, speed=(10.0, 40.0),
                  direction=(0.0, 360.0), life=(0.5, 1.5), size=(1.0, 3.0),
                  color="emphasis", scheme=DEFAULT_PALETTE):
    """Emit ``count`` particles from ``origin``, deterministically from ``seed``.

    Returns the particle state as a dict of arrays::

        {"pos": (N,2) as (x, y), "vel": (N,2) px/s, "age": (N,), "life": (N,),
         "size": (N,) radius in px, "color": (N,4) straight rgba}

    Ranges are ``(low, high)`` pairs sampled uniformly; ``direction`` is in
    degrees measured clockwise from the +x axis (again because the row axis
    points down). ``spread`` is the radius of the uniform disc the start
    positions are jittered over.

    All randomness comes from ``numpy.random.default_rng(seed)`` — the same seed
    gives the same bytes, which the test suite pins with a SHA-256.
    """
    n = _integer(count, "count", 0, MAX_PARTICLES)
    rng = np.random.default_rng(_seed(seed))
    ox = _scalar(origin[0] if len(origin) == 2 else None, "origin[0]", -1e6, 1e6)
    oy = _scalar(origin[1], "origin[1]", -1e6, 1e6)
    sp = _scalar(spread, "spread", 0.0, 1e5)
    rgba = _resolve_color(color, "color", 4, scheme)

    def _range(pair, nm, lo=None, hi=None, positive=False):
        if not isinstance(pair, (tuple, list, np.ndarray)) or len(pair) != 2:
            raise ValueError(f"{nm}: expected a (low, high) pair, got {pair!r}")
        a = _scalar(pair[0], f"{nm}[0]", lo, hi)
        b = _scalar(pair[1], f"{nm}[1]", lo, hi)
        if b < a:
            raise ValueError(f"{nm}: high {b} < low {a}")
        if positive and a <= 0.0:
            raise ValueError(f"{nm}: low must be > 0, got {a}")
        return a, b

    s_lo, s_hi = _range(speed, "speed", -1e5, 1e5)
    d_lo, d_hi = _range(direction, "direction", -3.6e4, 3.6e4)
    l_lo, l_hi = _range(life, "life", 0.0, 1e5, positive=True)
    z_lo, z_hi = _range(size, "size", 0.0, 1e4)

    ang = np.radians(rng.uniform(d_lo, d_hi, n))
    spd = rng.uniform(s_lo, s_hi, n)
    # uniform over the disc, not over (r, theta) — sqrt or the middle is denser
    jr = sp * np.sqrt(rng.uniform(0.0, 1.0, n))
    ja = rng.uniform(0.0, 2.0 * np.pi, n)
    return {
        "pos": np.stack([ox + jr * np.cos(ja), oy + jr * np.sin(ja)], axis=1),
        "vel": np.stack([spd * np.cos(ang), spd * np.sin(ang)], axis=1),
        "age": np.zeros(n, dtype=np.float64),
        "life": rng.uniform(l_lo, l_hi, n),
        "size": rng.uniform(z_lo, z_hi, n),
        "color": np.tile(rgba, (n, 1)),
    }


def particle_step(state, dt, gravity=(0.0, 98.0), drag=0.0):
    """Advance a particle state by ``dt`` seconds. Returns a **new** dict.

    Semi-implicit (symplectic) Euler::

        v <- v + (g - drag*v) * dt
        p <- p + v * dt
        age <- age + dt

    which makes the closed form exact and checkable: with ``gravity=(0,0)`` and
    ``drag=0`` the position after ``k`` steps is ``p0 + v0*k*dt``, and with drag
    the speed is ``v0 * (1 - drag*dt)**k``. Both are compared as equalities in
    the test suite.

    ``gravity`` is ``(gx, gy)`` in px/s^2, positive ``gy`` pulling **down** the
    screen. The input dict is never mutated.

    Raises ValueError: ``dt <= 0``; ``drag * dt >= 1``, which is the point where
    explicit drag stops decaying the speed and starts reversing it — an
    instability that otherwise shows up as particles flying backwards rather
    than as an error.
    """
    st = _require_particles(state, "state")
    step = _scalar(dt, "dt", None, 1e6)
    if step <= 0.0:
        raise ValueError(f"dt: must be > 0, got {step}")
    if not isinstance(gravity, (tuple, list, np.ndarray)) or len(gravity) != 2:
        raise ValueError(f"gravity: expected (gx, gy), got {gravity!r}")
    gx = _scalar(gravity[0], "gravity[0]", -1e6, 1e6)
    gy = _scalar(gravity[1], "gravity[1]", -1e6, 1e6)
    dg = _scalar(drag, "drag", 0.0, 1e6)
    if dg * step >= 1.0:
        raise ValueError(f"drag*dt = {dg * step} >= 1: explicit drag reverses the velocity "
                         "past this point instead of damping it; reduce dt or drag")
    vel = st["vel"] + (np.array([gx, gy]) - dg * st["vel"]) * step
    return {
        "pos": st["pos"] + vel * step,
        "vel": vel,
        "age": st["age"] + step,
        "life": st["life"].copy(),
        "size": st["size"].copy(),
        "color": st["color"].copy(),
    }


def particle_render(state, height, width, mode="add", fade=True):
    """Splat a particle state into an ``rgba`` image.

    Each particle is a radially symmetric ``(1 - (r/R)^2)^2`` kernel of radius
    ``size``, weighted by its alpha and, when ``fade`` is set, by the remaining
    fraction of its life ``(1 - age/life)``. Particles past their lifetime
    contribute nothing.

    ``mode`` is ``"add"`` (premultiplied additive — what a spark does; the
    result is clipped at 1 and the clipped energy is *not* returned) or
    ``"over"`` (each particle composited in array order, which is what a soft
    smoke puff does).

    Pure function of the state: no randomness enters here, so two calls on the
    same state produce identical bytes.
    """
    st = _require_particles(state, "state")
    h, w = _check_hw(height, width, "output")
    mode = _choice(mode, "mode", ("add", "over"))
    if not isinstance(fade, (bool, np.bool_)):
        raise ValueError(f"fade: expected a bool, got {type(fade).__name__}")

    alive = st["age"] < st["life"]
    n = int(np.count_nonzero(alive))
    out = np.zeros((h, w, 4), dtype=np.float64)
    if n == 0:
        return out
    pos = st["pos"][alive]
    rad = st["size"][alive]
    col = st["color"][alive].copy()
    if fade:
        col[:, 3] *= np.clip(1.0 - st["age"][alive] / st["life"][alive], 0.0, 1.0)

    rmax = float(np.max(rad))
    k = int(np.ceil(rmax)) + 1
    span = 2 * k + 1
    if n * span * span > MAX_SPLAT_ELEMENTS:
        raise ValueError(f"{n} particles at radius {rmax:.3g} need {n * span * span} splat "
                         f"elements, over MAX_SPLAT_ELEMENTS={MAX_SPLAT_ELEMENTS}")

    ci = np.rint(pos[:, 0]).astype(np.int64)
    ri = np.rint(pos[:, 1]).astype(np.int64)
    off = np.arange(-k, k + 1)
    dy, dx = np.meshgrid(off, off, indexing="ij")
    rr = ri[:, None, None] + dy[None]
    cc = ci[:, None, None] + dx[None]
    dist2 = ((rr - pos[:, 1][:, None, None]) ** 2 + (cc - pos[:, 0][:, None, None]) ** 2)
    r2 = np.maximum(rad, 1e-12)[:, None, None] ** 2
    t = np.clip(1.0 - dist2 / r2, 0.0, 1.0)
    weight = t * t
    inside = (rr >= 0) & (rr < h) & (cc >= 0) & (cc < w) & (weight > 0.0)

    if mode == "add":
        # Additive light accumulates in *premultiplied* space: that is the space
        # in which "two lights on one pixel" is a sum at all.
        flat = (np.clip(rr, 0, h - 1) * w + np.clip(cc, 0, w - 1)).ravel()
        cov = weight * inside                       # (n, span, span)
        a_contrib = cov * col[:, 3][:, None, None]  # coverage x the particle's own alpha
        acc = np.zeros((h * w, 4), dtype=np.float64)
        np.add.at(acc[:, 3], flat, a_contrib.ravel())
        for ch in range(3):
            np.add.at(acc[:, ch], flat, (a_contrib * col[:, ch][:, None, None]).ravel())
        return _clamp_premul(acc.reshape(h, w, 4))
    # "over": composite one at a time, in array order
    for i in range(n):
        r0, r1 = max(0, ri[i] - k), min(h, ri[i] + k + 1)
        c0, c1 = max(0, ci[i] - k), min(w, ci[i] + k + 1)
        if r0 >= r1 or c0 >= c1:
            continue
        wsub = weight[i, r0 - (ri[i] - k):r1 - (ri[i] - k), c0 - (ci[i] - k):c1 - (ci[i] - k)]
        patch = np.empty((r1 - r0, c1 - c0, 4), dtype=np.float64)
        patch[..., :3] = col[i, :3]
        patch[..., 3] = np.clip(wsub * col[i, 3], 0.0, 1.0)
        out[r0:r1, c0:c1] = alpha_composite(patch, out[r0:r1, c0:c1])
    return out


def _clamp_premul(acc):
    """Force an accumulated buffer into the premultiplied invariant colour<=alpha."""
    a = np.clip(acc[..., 3:4], 0.0, 1.0)
    out = np.concatenate([np.clip(acc[..., :3], 0.0, a), a], axis=2)
    return unpremultiply(out)


# --------------------------------------------------------------------------- #
# 2-D lighting                                                                  #
# --------------------------------------------------------------------------- #
def radial_light(height, width, x, y, radius, intensity=1.0, falloff="smooth",
                 color="emphasis", scheme=DEFAULT_PALETTE):
    """A radial light map, ``rgb`` ``(H, W, 3)``, centred on ``(x, y)``.

    ``falloff``:

    * ``"smooth"`` — ``(1 - t^2)^2``, compactly supported: exactly zero at and
      beyond ``radius``. The default, because a light that ends somewhere is the
      only kind you can budget.
    * ``"linear"`` — ``1 - t``, also compact.
    * ``"inverse_square"`` — ``1 / (1 + (3t)^2)``, the physical law softened at
      the origin. **Not** compactly supported: it is 10 % of peak at the nominal
      radius and never reaches zero, so a scene full of these never gets dark.

    The value at the centre is exactly ``intensity * color``. This is a
    *linear-light* quantity: add lights together, then encode once.
    """
    h, w = _check_hw(height, width, "output")
    cx = _scalar(x, "x", -1e6, 1e6)
    cy = _scalar(y, "y", -1e6, 1e6)
    rad = _scalar(radius, "radius", None, 1e6)
    if rad <= 0.0:
        raise ValueError(f"radius: must be > 0, got {rad}")
    inten = _scalar(intensity, "intensity", 0.0, 1e3)
    falloff = _choice(falloff, "falloff", ("smooth", "linear", "inverse_square"))
    rgb = _resolve_color(color, "color", 3, scheme)

    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    t = np.hypot(xx - cx, yy - cy) / rad
    if falloff == "smooth":
        g = np.clip(1.0 - t * t, 0.0, None) ** 2
    elif falloff == "linear":
        g = np.clip(1.0 - t, 0.0, None)
    else:
        g = 1.0 / (1.0 + (3.0 * t) ** 2)
    return (inten * g)[..., None] * rgb[None, None, :]


def light_mask(base, light, ambient=0.0):
    """Modulate an ``rgb`` image by an ``rgb`` light map: ``base * (ambient + light)``.

    ``ambient`` is the light that reaches everything; ``ambient=1`` with a black
    light map returns the base **exactly**, which is the identity the test suite
    pins.

    The product is clipped to ``[0, 1]``; the clipped amount is not returned.
    Both arguments should be in the same encoding — mixing an sRGB base with a
    linear light map is the second silent-error trap of this family, and the
    only defence is that both arguments are named.
    """
    b = _require_rgb(base, "base")
    lt = _as_array(light, "light")
    if lt.ndim != 3 or lt.shape[2] != 3:
        raise ValueError(f"light: expected an (H, W, 3) light map, got shape {lt.shape}")
    _same_shape(b, lt, "base", "light")
    if float(lt.min()) < 0.0:
        raise ValueError(f"light: negative radiance {float(lt.min()):.6g}; a light that "
                         "removes light is a bug in the caller, not a feature here")
    amb = _scalar(ambient, "ambient", 0.0, 1e3)
    return np.clip(b * (amb + lt), 0.0, 1.0)


def normal_map_decode(rgb):
    """Tangent-space normal map ``rgb`` in ``[0, 1]`` to unit vectors ``(H, W, 3)``.

    The usual encoding ``n = 2c - 1`` followed by normalisation. The result is
    the ``normalmap`` sort the rest of the library already speaks, so a decoded
    map can go straight into the 3-D normals family.

    Raises ValueError: a pixel whose decoded vector has zero length (the encoded
    colour was exactly mid-grey), because normalising it would silently invent a
    direction.
    """
    c = _require_rgb(rgb, "rgb")
    n = 2.0 * c - 1.0
    norm = np.linalg.norm(n, axis=2, keepdims=True)
    if float(norm.min()) < 1e-9:
        cnt = int(np.count_nonzero(norm < 1e-9))
        raise ValueError(f"rgb: {cnt} pixel(s) decode to a zero-length normal (exactly "
                         "mid-grey); normalising them would invent a direction")
    return n / norm


def normal_map_shade(normals, light_dir=(0.0, 0.0, 1.0), ambient=0.1, diffuse="reference",
                     specular=0.0, shininess=32.0, view_dir=(0.0, 0.0, 1.0),
                     scheme=DEFAULT_PALETTE):
    """Shade a 2-D normal map with one directional light (Lambert + Blinn 1977).

    ``normals`` is a ``normalmap``: ``(H, W, 3)`` **unit** vectors, as
    :func:`normal_map_decode` returns. Non-unit input raises rather than being
    normalised for you — a normal map that is not normalised is usually a map
    that was never decoded, and quietly fixing it hides the mistake.

    ``out = diffuse * (ambient + max(n·l, 0)) + specular * max(n·h, 0)^shininess``
    with ``h`` the normalised halfway vector between light and view.

    Directions are ``(x, y, z)`` with **+x right, +y down, +z out of the
    screen** — the same handedness as the pixel grid, so a light at
    ``(0, -1, 1)`` comes from above the screen. Getting the sign of y wrong
    flips the perceived relief (bumps become dents) without raising anything;
    that is the one thing to check on first render.
    """
    n = _as_array(normals, "normals")
    if n.ndim != 3 or n.shape[2] != 3:
        raise ValueError(f"normals: expected an (H, W, 3) normal map, got shape {n.shape}")
    _check_hw(n.shape[0], n.shape[1], "normals")
    length = np.linalg.norm(n, axis=2)
    err = float(np.max(np.abs(length - 1.0)))
    if err > 1e-6:
        raise ValueError(f"normals: not unit length (worst deviation {err:.3g}). Decode an "
                         "encoded map with normal_map_decode() first.")
    amb = _scalar(ambient, "ambient", 0.0, 10.0)
    spec = _scalar(specular, "specular", 0.0, 10.0)
    shin = _scalar(shininess, "shininess", 1.0, 1e4)
    diff = _resolve_color(diffuse, "diffuse", 3, scheme)

    def _dir(v, nm):
        arr = _as_array(v, nm)
        if arr.shape != (3,):
            raise ValueError(f"{nm}: expected (x, y, z), got shape {arr.shape}")
        norm = float(np.linalg.norm(arr))
        if norm < 1e-12:
            raise ValueError(f"{nm}: zero-length direction")
        return arr / norm

    ld = _dir(light_dir, "light_dir")
    vd = _dir(view_dir, "view_dir")
    ndl = np.clip(n @ ld, 0.0, None)
    half = ld + vd
    hn = float(np.linalg.norm(half))
    out = diff[None, None, :] * (amb + ndl)[..., None]
    if spec > 0.0 and hn > 1e-12:
        ndh = np.clip(n @ (half / hn), 0.0, None)
        out = out + spec * (ndh ** shin)[..., None]
    return np.clip(out, 0.0, 1.0)


def shadow_cast_2d(occluder, x, y, steps=None, softness=0.0):
    """Visibility of every pixel from a point light at ``(x, y)``, as ``image2d``.

    Ray-marches the segment from each pixel to the light, sampling ``occluder``
    (2-D, ``[0, 1]``, 1 = fully blocking) at ``steps`` points with nearest
    lookup, and returns ``1 - max(occluder along the ray)``. For a binary
    occluder that is exactly 0 or 1 — no tolerance involved.

    The sample **excludes** the pixel itself, so an occluder is lit on its own
    light-facing surface and casts behind itself.

    ``softness > 0`` blurs the visibility map by that sigma afterwards, which is
    a penumbra-shaped lie rather than a penumbra: a real one widens with
    distance from the occluder. It is offered because it looks right and named
    so it cannot be mistaken for physics.

    ``steps`` defaults to the image diagonal, which samples about once per
    pixel. **An occluder thinner than the step spacing can be missed**; that is
    the honest limit of a fixed-step march and the reason ``steps`` is an
    argument.
    """
    occ = _as_array(occluder, "occluder")
    if occ.ndim != 2:
        raise ValueError(f"occluder: expected a 2-D map, got shape {occ.shape}")
    h, w = _check_hw(occ.shape[0], occ.shape[1], "occluder")
    occ = _clip01(occ, "occluder", "occlusion")
    lx = _scalar(x, "x", -1e6, 1e6)
    ly = _scalar(y, "y", -1e6, 1e6)
    soft = _scalar(softness, "softness", 0.0, 1e3)
    if steps is None:
        steps = int(np.ceil(np.hypot(h, w)))
    steps = _integer(steps, "steps", 1, 1 << 16)
    if steps * h * w > MAX_RAY_ELEMENTS:
        raise ValueError(f"steps*H*W = {steps * h * w} exceeds "
                         f"MAX_RAY_ELEMENTS={MAX_RAY_ELEMENTS}")

    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    t = ((np.arange(steps) + 1.0) / (steps + 1.0))[:, None, None]
    sx = xx[None] + (lx - xx[None]) * t
    sy = yy[None] + (ly - yy[None]) * t
    ci = np.clip(np.rint(sx), 0, w - 1).astype(np.intp)
    ri = np.clip(np.rint(sy), 0, h - 1).astype(np.intp)
    inside = (sx >= -0.5) & (sx <= w - 0.5) & (sy >= -0.5) & (sy <= h - 0.5)
    blocked = np.max(occ[ri, ci] * inside, axis=0)
    vis = 1.0 - blocked
    if soft > 0.0:
        vis = np.clip(ndimage.gaussian_filter(vis, soft, mode="nearest"), 0.0, 1.0)
    return vis


# --------------------------------------------------------------------------- #
# Post-processing                                                               #
# --------------------------------------------------------------------------- #
def bloom(rgb, threshold=0.8, sigma=4.0, intensity=0.6):
    """Bleed the bright parts of an image into their neighbourhood.

    The classical three steps: isolate what is above ``threshold``, blur it by a
    Gaussian of ``sigma``, add ``intensity`` times the result back, clip.

    A *linear-light* operator: light spreading in a lens adds radiance. Running
    it on sRGB-encoded values makes the halo too strong in the mid-tones —
    ``srgb_to_linear`` first, ``linear_to_srgb`` after.

    Exact identities: ``intensity=0`` and ``threshold >= 1`` both return the
    input bit for bit, and a black image stays black.

    The added energy is *not* conserved by the clip at the end. The suite
    measures how much: on a centred bright blob the blur preserves the bright
    mass to 4e-13 relative, and everything lost after that is the clip.
    """
    img = _require_rgb(rgb, "rgb")
    thr = _scalar(threshold, "threshold", 0.0, 1.0)
    sig = _scalar(sigma, "sigma", 0.0, 1e3)
    inten = _scalar(intensity, "intensity", 0.0, 1e2)
    if inten == 0.0 or thr >= 1.0:
        return img.copy()
    bright = np.clip(img - thr, 0.0, None) / (1.0 - thr)
    if sig > 0.0:
        bright = ndimage.gaussian_filter(bright, (sig, sig, 0.0), mode="nearest")
    return np.clip(img + inten * bright, 0.0, 1.0)


def vignette(rgb, strength=0.6, radius=1.0, power=2.0):
    """Darken towards the corners: ``out = rgb * (1 - strength * t**power)``.

    ``t`` is the distance from the centre divided by ``radius`` times the
    half-diagonal, clipped at 1. The centre pixel is multiplied by exactly 1, so
    ``strength=0`` — and the centre of any vignette — is the exact identity.
    """
    img = _require_rgb(rgb, "rgb")
    st = _scalar(strength, "strength", 0.0, 1.0)
    rad = _scalar(radius, "radius", None, 1e3)
    if rad <= 0.0:
        raise ValueError(f"radius: must be > 0, got {rad}")
    p = _scalar(power, "power", 0.05, 32.0)
    if st == 0.0:
        return img.copy()
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    half_diag = np.hypot(cy, cx)
    if half_diag <= 0.0:
        return img.copy()
    t = np.clip(np.hypot(yy - cy, xx - cx) / (half_diag * rad), 0.0, 1.0)
    return np.clip(img * (1.0 - st * t ** p)[..., None], 0.0, 1.0)


def chromatic_aberration(rgb, strength=0.003, interp="bilinear"):
    """Scale the red and blue channels about the image centre, green fixed.

    Lateral chromatic aberration: red is magnified by ``1 + strength``, blue by
    ``1 - strength``. ``strength=0`` samples the exact pixel centres and returns
    the input to within 1e-15, which the suite checks.

    Negative ``strength`` swaps which channel spreads outward — allowed, since
    which way a real lens disperses depends on the glass.
    """
    img = _require_rgb(rgb, "rgb")
    st = _scalar(strength, "strength", -0.5, 0.5)
    interp = _choice(interp, "interp", tuple(_INTERP_ORDER))
    if st == 0.0:
        return img.copy()
    h, w = img.shape[:2]
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    order = _INTERP_ORDER[interp]
    out = np.empty_like(img)
    out[..., 1] = img[..., 1]
    for ch, s in ((0, 1.0 + st), (2, 1.0 - st)):
        ys = cy + (yy - cy) / s
        xs = cx + (xx - cx) / s
        out[..., ch] = ndimage.map_coordinates(img[..., ch], [ys, xs], order=order,
                                               mode="nearest", prefilter=order > 1)
    return np.clip(out, 0.0, 1.0)


def film_grain(rgb, sigma=0.03, seed=0, monochrome=True):
    """Add zero-mean Gaussian grain, deterministically from ``seed``.

    ``monochrome`` adds the same noise to all three channels (what film grain
    does — the silver halide crystal is not coloured); set it false for sensor
    read noise, which is per-channel.

    ``sigma=0`` returns the input bit for bit. The clip at ``[0, 1]`` biases the
    mean wherever the image is already near an end of the range; the suite
    measures the shift (0.0009 on the mid-grey test image, 0.012 on a
    black-and-white one) rather than claiming it is zero.
    """
    img = _require_rgb(rgb, "rgb")
    sig = _scalar(sigma, "sigma", 0.0, 10.0)
    sd = _seed(seed)
    if not isinstance(monochrome, (bool, np.bool_)):
        raise ValueError(f"monochrome: expected a bool, got {type(monochrome).__name__}")
    if sig == 0.0:
        return img.copy()
    rng = np.random.default_rng(sd)
    h, w = img.shape[:2]
    noise = rng.standard_normal((h, w, 1)) if monochrome else rng.standard_normal((h, w, 3))
    return np.clip(img + sig * noise, 0.0, 1.0)


def color_lut(size=17, gain=(1.0, 1.0, 1.0), lift=(0.0, 0.0, 0.0),
              gamma=(1.0, 1.0, 1.0), saturation=1.0):
    """Build a 3-D colour LUT, ``(n, n, n, 3)`` indexed ``[r, g, b]``.

    ``out = clip(lift + gain * in**gamma)`` per channel, then saturation is
    applied about the Rec. 709 luma. With all defaults this is the **identity
    LUT**, and because trilinear interpolation is exact for a function that is
    linear in each variable, :func:`color_grade` with the identity LUT is the
    identity to float64 rounding — the property the suite uses to prove the
    interpolation itself is right before testing any grade.
    """
    n = _integer(size, "size", 2, MAX_LUT_SIZE)

    def _triple(v, nm, lo, hi):
        arr = _as_array(v, nm)
        if arr.shape != (3,):
            raise ValueError(f"{nm}: expected 3 values, got shape {arr.shape}")
        if float(arr.min()) < lo or float(arr.max()) > hi:
            raise ValueError(f"{nm}: must lie in [{lo}, {hi}], got "
                             f"[{float(arr.min()):.6g}, {float(arr.max()):.6g}]")
        return arr

    g = _triple(gain, "gain", 0.0, 16.0)
    lf = _triple(lift, "lift", -1.0, 1.0)
    gm = _triple(gamma, "gamma", 0.05, 16.0)
    sat = _scalar(saturation, "saturation", 0.0, 8.0)

    axis = np.linspace(0.0, 1.0, n)
    grid = np.stack(np.meshgrid(axis, axis, axis, indexing="ij"), axis=-1)
    out = lf + g * (grid ** gm)
    if sat != 1.0:
        luma = (0.2126 * out[..., 0] + 0.7152 * out[..., 1] + 0.0722 * out[..., 2])[..., None]
        out = luma + sat * (out - luma)
    return np.clip(out, 0.0, 1.0)


def color_grade(rgb, lut):
    """Apply a 3-D colour LUT to an ``rgb`` image by trilinear interpolation.

    ``lut`` is ``(n, n, n, 3)`` indexed ``[r, g, b]`` — the layout
    :func:`color_lut` produces. The identity LUT returns the input to within
    float64 rounding (measured maximum 1.1e-16), which is what makes this
    testable without a reference implementation: trilinear interpolation of a
    coordinate function is that coordinate, exactly.
    """
    img = _require_rgb(rgb, "rgb")
    table = _as_array(lut, "lut")
    if table.ndim != 4 or table.shape[3] != 3 or len({*table.shape[:3]}) != 1:
        raise ValueError(f"lut: expected a cubic (n, n, n, 3) table, got shape {table.shape}")
    n = table.shape[0]
    if n < 2 or n > MAX_LUT_SIZE:
        raise ValueError(f"lut: side {n} outside [2, {MAX_LUT_SIZE}]")
    table = _clip01(table, "lut", "entry")
    coords = img * (n - 1)
    out = np.empty_like(img)
    for ch in range(3):
        out[..., ch] = ndimage.map_coordinates(
            table[..., ch], [coords[..., 0], coords[..., 1], coords[..., 2]],
            order=1, mode="nearest")
    return np.clip(out, 0.0, 1.0)


def _bayer(n):
    """The ``n x n`` ordered-dither index matrix (Bayer 1973); ``n`` a power of two."""
    m = np.zeros((1, 1), dtype=np.float64)
    while m.shape[0] < n:
        m = np.block([[4 * m, 4 * m + 2], [4 * m + 3, 4 * m + 1]])
    return m


def dither(img, levels=2, method="ordered", matrix_size=4):
    """Quantise to ``levels`` values per channel while preserving the local mean.

    ``method``:

    * ``"ordered"`` — Bayer threshold matrix of side ``matrix_size`` (a power of
      two, 2..16). **The mean error has a closed-form bound**: for a uniform
      patch the output mean is within ``0.5 / (matrix_size**2 * (levels-1))`` of
      the input, because the fraction of thresholds crossed is the input
      fraction rounded to the nearest ``1/matrix_size**2``. At the defaults
      (4, 2 levels) that is 0.03125, and the suite measures it and checks the
      bound holds at every level count from 2 to 16.
    * ``"floyd_steinberg"`` — error diffusion with the 7/3/5/1 sixteenths of
      Floyd & Steinberg 1976. Preserves the mean far better (measured 3.1e-4 on
      the test gradient against 4.5e-3 for ordered) at the cost of being serial
      and of a directional texture.

    Accepts ``(H, W)`` or ``(H, W, 3|4)``; an alpha channel is quantised too,
    because a dithered sprite with a smooth alpha is exactly the case that
    motivates this.

    Output values lie on the lattice ``k / (levels - 1)``.
    """
    arr = _as_array(img, "img")
    if arr.ndim not in (2, 3):
        raise ValueError(f"img: expected (H, W) or (H, W, C), got shape {arr.shape}")
    if arr.ndim == 3 and arr.shape[2] not in (1, 3, 4):
        raise ValueError(f"img: expected 1, 3 or 4 channels, got {arr.shape[2]}")
    _check_hw(arr.shape[0], arr.shape[1], "img")
    arr = _clip01(arr, "img", "value")
    lv = _integer(levels, "levels", 2, MAX_LEVELS)
    method = _choice(method, "method", ("ordered", "floyd_steinberg"))
    q = lv - 1

    if method == "ordered":
        ms = _integer(matrix_size, "matrix_size", 2, 16)
        if ms & (ms - 1):
            raise ValueError(f"matrix_size: must be a power of two, got {ms}")
        thr = (_bayer(ms) + 0.5) / (ms * ms)
        h, w = arr.shape[:2]
        tile = np.tile(thr, (h // ms + 1, w // ms + 1))[:h, :w]
        t = tile[..., None] if arr.ndim == 3 else tile
        return np.clip(np.floor(arr * q + t), 0.0, q) / q

    flat = arr.reshape(arr.shape[0], arr.shape[1], -1) if arr.ndim == 3 else arr[..., None]
    work = flat.astype(np.float64).copy()
    h, w, c = work.shape
    out = np.empty_like(work)
    for r in range(h):
        for col in range(w):
            old = work[r, col]
            new = np.clip(np.rint(old * q), 0.0, q) / q
            out[r, col] = new
            err = old - new
            if col + 1 < w:
                work[r, col + 1] += err * (7.0 / 16.0)
            if r + 1 < h:
                if col > 0:
                    work[r + 1, col - 1] += err * (3.0 / 16.0)
                work[r + 1, col] += err * (5.0 / 16.0)
                if col + 1 < w:
                    work[r + 1, col + 1] += err * (1.0 / 16.0)
    return out.reshape(arr.shape)


def palette_quantize(rgb, colors=None, scheme=DEFAULT_PALETTE):
    """Map every pixel to its nearest palette colour in Euclidean RGB.

    ``colors`` is an ``(K, 3)`` array or a list of :mod:`palette` role names;
    the default is the whole Okabe–Ito set plus black and white, so the result
    stays legible under a colour vision deficiency.

    The search is exhaustive, so the assignment is **optimal for this metric**
    and each pixel's error equals its distance to the nearest palette entry —
    there is no approximation to bound. The suite checks optimality by brute
    force and checks that an image whose colours already lie in the palette
    comes back unchanged, bit for bit.

    Euclidean distance in (possibly sRGB-encoded) RGB is not perceptual
    distance. That is a documented choice, not an oversight: a perceptual metric
    needs a colour-appearance model this module does not own, and quantising in
    an unstated space would be worse than quantising in a stated one.
    """
    img = _require_rgb(rgb, "rgb")
    if colors is None:
        pal = palette.semantic_palette(scheme)
        base = [pal[r] for r in palette.ROLES] + [(0.0, 0.0, 0.0), (1.0, 1.0, 1.0)]
        table = np.asarray(base, dtype=np.float64)
    elif isinstance(colors, (list, tuple)) and colors and isinstance(colors[0], str):
        table = np.stack([_resolve_color(c, "colors", 3, scheme) for c in colors])
    else:
        table = _as_array(colors, "colors")
        if table.ndim != 2 or table.shape[1] != 3:
            raise ValueError(f"colors: expected (K, 3), got shape {table.shape}")
        table = _clip01(table, "colors", "colour")
    if table.shape[0] < 1:
        raise ValueError("colors: empty palette")
    if table.shape[0] > MAX_PALETTE:
        raise ValueError(f"colors: {table.shape[0]} exceeds MAX_PALETTE={MAX_PALETTE}")
    d2 = ((img[..., None, :] - table[None, None, :, :]) ** 2).sum(axis=3)
    return table[np.argmin(d2, axis=2)]


# --------------------------------------------------------------------------- #
# Camera                                                                        #
# --------------------------------------------------------------------------- #
def viewport(img, x, y, width, height, scale=1.0, interp="bilinear"):
    """Crop the rectangle at ``(x, y, width, height)`` and resample it by ``scale``.

    Accepts ``rgb`` or ``rgba`` (straight alpha; the crop is a copy, so no
    premultiplication is involved) and returns the same channel count.

    **Out-of-bounds raises**, unlike :func:`sprite_blit`, which clips. The
    asymmetry is the point: a sprite leaving the screen is the normal case,
    while a camera asking for rows the image does not have is arithmetic that
    has already gone wrong somewhere upstream, and returning a partly black
    frame would let it keep going.

    ``scale=1`` with integer bounds returns an exact sub-array copy — no
    interpolation touches it.
    """
    arr = _as_array(img, "img")
    if arr.ndim != 3 or arr.shape[2] not in (3, 4):
        raise ValueError(f"img: expected (H, W, 3) or (H, W, 4), got shape {arr.shape}")
    h, w = _check_hw(arr.shape[0], arr.shape[1], "img")
    arr = _clip01(arr, "img", "value")
    x0 = _integer(x, "x", -MAX_DIM * 4, MAX_DIM * 4)
    y0 = _integer(y, "y", -MAX_DIM * 4, MAX_DIM * 4)
    vw = _integer(width, "width", 1, MAX_DIM)
    vh = _integer(height, "height", 1, MAX_DIM)
    sc = _scalar(scale, "scale", None, 64.0)
    if sc <= 0.0:
        raise ValueError(f"scale: must be > 0, got {sc}")
    interp = _choice(interp, "interp", tuple(_INTERP_ORDER))
    if x0 < 0 or y0 < 0 or x0 + vw > w or y0 + vh > h:
        raise ValueError(
            f"viewport ({x0}, {y0}, {vw}x{vh}) leaves the {h}x{w} image. Unlike "
            "sprite_blit this does not clip: a camera asking for pixels that do not "
            "exist is an arithmetic error upstream, and a partly black frame would hide it.")

    crop = arr[y0:y0 + vh, x0:x0 + vw].copy()
    if sc == 1.0:
        return crop
    oh = max(1, int(round(vh * sc)))
    ow = max(1, int(round(vw * sc)))
    _check_hw(oh, ow, "viewport output")
    order = _INTERP_ORDER[interp]
    rr = (np.arange(oh) + 0.5) * vh / oh - 0.5
    cc = (np.arange(ow) + 0.5) * vw / ow - 0.5
    gy, gx = np.meshgrid(rr, cc, indexing="ij")
    out = np.empty((oh, ow, crop.shape[2]), dtype=np.float64)
    for ch in range(crop.shape[2]):
        out[..., ch] = ndimage.map_coordinates(crop[..., ch], [gy, gx], order=order,
                                               mode="nearest", prefilter=order > 1)
    return np.clip(out, 0.0, 1.0)
