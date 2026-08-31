"""3-D volume geometric transforms (numpy + scipy.ndimage — no other dependency).

The 2-D operator set carries a full *geometry* sort (28 ops: resize / rotate /
affine / polar / mirror ...), but until now the voxel world had only *format*
conversions — no way to resample a ``(D, H, W)`` volume at all. This module
closes that confirmed gap (``docs/NEXT_OPS_PLAN_2026-08-31.md`` §D) with the
three primitives every registration / metrology pipeline needs right after a
pose estimate: :func:`vol_resize` (zoom), :func:`vol_rotate` (in-plane rotation
about a pair of axes) and :func:`vol_affine` (a general 3x3-or-4x4 resampler).
All three are thin, *convention-pinned* wrappers over ``scipy.ndimage``
(``zoom`` / ``rotate`` / ``affine_transform``).

Frame convention (shared with :mod:`volio` / :mod:`volops`): a volume is a
``(D, H, W)`` float64 array indexed ``[z, y, x]``; ``spacing`` is
``(sz, sy, sx)`` millimetres per voxel, lined up with those axes (a
:class:`volio.VolumeMeta` may be passed wherever ``spacing`` is accepted).

Pinned conventions (each is machine-verified in ``tests/test_volxform.py``):

  * **Resize samples cells, not endpoints** — :func:`vol_resize` uses
    ``scipy.ndimage.zoom(..., grid_mode=True)``: a voxel is a *cell* of physical
    size ``spacing``, so upscaling by an integer factor ``f`` maps input voxel
    ``i`` exactly onto the output block ``[f*i, f*(i+1))`` (order=0), and the
    physical extent ``size * spacing`` of the volume is preserved exactly by the
    recomputed spacing.
  * **Rotation direction** — a positive *angle_deg* rotates **from the first
    axis of** *axes* **toward the second**, exactly the ``np.rot90`` convention:
    ``vol_rotate(v, 90, axes=a, reshape=False)`` equals ``np.rot90(v, 1, axes=a)``
    bit-for-bit at order=0 (square in-plane shape).
  * **Affine is pull (output -> input)** — scipy's resampling convention:
    output voxel ``o`` reads the input at ``matrix @ o + offset``. A matrix of
    ``2*I`` therefore makes the object appear *half* size (each output step
    strides two input voxels). To *push* an object by a transform ``T``, pass
    the **inverse** of ``T``.

Honest limitations (nothing here claims more than the tests prove):

  * **Interpolation does not band-limit.** ``zoom`` / ``rotate`` /
    ``affine_transform`` interpolate the existing samples; *shrinking* a volume
    this way aliases (high-frequency detail folds into the result). For a large
    reduction, run :func:`volops.volume_downsample` (mean-pool = a real
    pre-filter) first and use :func:`vol_resize` only for the residual factor.
  * **order > 1 overshoots.** Spline interpolation (order 2..5) is not
    monotone: values can slightly exceed the input range (a ``[0, 1]`` volume
    may come back with voxels a little below 0 or above 1 near sharp edges).
    Clamp downstream if the range is a contract, or use order 1.
  * **order 0 is exact but blocky** — nearest-neighbour preserves label /
    binary volumes (no invented intermediate values) and is what the
    ground-truth tests use; it is the right choice for masks, the wrong one
    for grey CT.
  * **A 90-degree rotation with ``reshape=False`` is lossless only for a
    square in-plane shape**; on a rectangle the corners that leave the frame
    are filled with *cval* and the ones that enter are lost.
  * **Boundary values are invented.** Every voxel whose source coordinate
    falls outside the input is filled per *mode*/*cval* (default constant 0);
    a rotation or affine always has such voxels unless the content is well
    inside the frame.

Fail-closed on untrusted input: every entry point requires a 3-D ``(D, H, W)``
array, coerces to float64, rejects NaN / Inf, caps the voxel count at
``MAX_VOXELS`` (1 << 27) — **including the output size** (a huge zoom factor or
``output_shape`` is refused *before* any allocation, so a hostile parameter
cannot balloon memory) — and accepts *order* only as an exact integer in 0..5.
A malformed input raises ``ValueError`` naming the problem.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

__all__ = [
    "vol_resize", "vol_rotate", "vol_affine",
    "VOLXFORM_OPS", "MAX_VOXELS",
]

#: The public 3-D geometric-transform operators, by name (facade wiring).
VOLXFORM_OPS = ["vol_resize", "vol_rotate", "vol_affine"]

#: Refuse an input *or output* volume larger than this (~134 M voxels = 1 GiB
#: as float64) — the same cap as :mod:`volops` / :mod:`volregion`. The output
#: check is the important half here: a resampler is the one place a small
#: input can be blown up into an arbitrarily large allocation.
MAX_VOXELS = 1 << 27

_VALID_ROTATE_AXES = ((0, 1), (0, 2), (1, 2))


# --------------------------------------------------------------------------- #
# fail-closed input helpers                                                    #
# --------------------------------------------------------------------------- #
def _require_volume(vol, name: str = "vol") -> np.ndarray:
    """Coerce to a contiguous ``(D, H, W)`` float64 array or raise ``ValueError``.

    Rejects anything that is not exactly 3-D and any NaN / Inf — interpolation
    would smear a single poisoned voxel over a whole neighbourhood."""
    v = np.ascontiguousarray(vol, dtype=np.float64)
    if v.ndim != 3:
        raise ValueError("%s must be a 3-D (D, H, W) volume, got a %d-D array of shape %r"
                         % (name, v.ndim, tuple(np.shape(vol))))
    if not np.isfinite(v).all():
        n = int((~np.isfinite(v)).sum())
        raise ValueError("%s has %d non-finite voxel(s) (NaN/Inf) — refusing "
                         "(interpolation would smear them)" % (name, n))
    if v.size > MAX_VOXELS:
        raise ValueError("%s: a %d-voxel volume (shape %r) exceeds the %d cap "
                         "(volxform.MAX_VOXELS) — crop to an ROI or downsample first"
                         % (name, v.size, v.shape, MAX_VOXELS))
    return v


def _check_output_voxels(shape, op: str) -> None:
    """Cap the *output* allocation (plain-int product — no int64 overflow)."""
    n = 1
    for s in shape:
        n *= int(s)
    if n > MAX_VOXELS:
        raise ValueError("%s: the requested output shape %r has %d voxels, "
                         "exceeding the %d cap (volxform.MAX_VOXELS) — refusing "
                         "before allocation" % (op, tuple(shape), n, MAX_VOXELS))


def _check_order(order) -> int:
    """*order* as an exact integer in 0..5 (a 1.5 is rejected, never truncated)."""
    try:
        f = float(order)
    except (TypeError, ValueError):
        raise ValueError("order must be an integer in 0..5, got %r" % (order,)) from None
    if not np.isfinite(f) or f != int(f) or not (0 <= int(f) <= 5):
        raise ValueError("order must be an integer in 0..5 (spline degree), got %r"
                         % (order,))
    return int(f)


def _check_cval(cval) -> float:
    try:
        c = float(cval)
    except (TypeError, ValueError):
        raise ValueError("cval must be a finite real number, got %r" % (cval,)) from None
    if not np.isfinite(c):
        raise ValueError("cval must be finite, got %r — a NaN/Inf fill would poison "
                         "the output (every volop rejects non-finite voxels)" % (cval,))
    return c


def _spacing_tuple(spacing, name: str = "spacing"):
    """Normalise a spacing argument to ``(sz, sy, sx)`` floats, or ``None``.
    Accepts a 3-tuple *or* a :class:`volio.VolumeMeta` (same as :mod:`volops`)."""
    if spacing is None:
        return None
    if hasattr(spacing, "spacing_mm"):
        spacing = spacing.spacing_mm
    try:
        sp = tuple(float(s) for s in spacing)
    except (TypeError, ValueError):
        raise ValueError("%s must be a length-3 (sz, sy, sx) sequence or a "
                         "VolumeMeta, got %r" % (name, spacing)) from None
    if len(sp) != 3 or any(not np.isfinite(s) or s <= 0.0 for s in sp):
        raise ValueError("%s must be 3 positive finite values (sz, sy, sx), got %r"
                         % (name, sp))
    return sp


# --------------------------------------------------------------------------- #
# vol_resize — zoom with cell semantics and spacing recomputation              #
# --------------------------------------------------------------------------- #
def vol_resize(vol, factor=None, shape=None, order=1, spacing=None):
    """Resample a volume to a new grid (``scipy.ndimage.zoom``, cell semantics).

    Exactly **one** of *factor* / *shape* selects the target grid:

    * ``factor`` — a positive scalar or ``(fz, fy, fx)``; the output shape is
      ``round(dim * f)`` per axis (scipy's rule, each ``>= 1``).
    * ``shape`` — the exact output ``(D', H', W')`` (positive integers).

    Sampling uses ``grid_mode=True`` (cell semantics): a voxel is a *cell*, so
    an integer upscale ``f`` maps input voxel ``i`` exactly onto the output
    block ``[f*i, f*(i+1))`` (exact at ``order=0``), and the volume's physical
    extent is preserved by the recomputed spacing — not the endpoint-aligned
    convention of scipy's ``grid_mode=False`` default.

    **The return shape depends on** *spacing*:

    * ``spacing=None`` (default) — returns the resampled ``(D', H', W')``
      float64 volume alone.
    * *spacing* given (``(sz, sy, sx)`` or a ``VolumeMeta``) — returns a
      **2-tuple** ``(out, new_spacing)`` where
      ``new_spacing = (sz * D/D', sy * H/H', sx * W/W')``, so
      ``out.shape * new_spacing == vol.shape * spacing`` per axis: the physical
      size in millimetres is invariant. Keep the new spacing — every
      spacing-aware operator downstream needs it.

    *order* is the spline degree (exact integer 0..5; 0 = nearest — the choice
    for masks / labels, 1 = trilinear — the grey-value default; >1 can
    overshoot, see the module notes). Shrinking aliases (no band-limiting) —
    mean-pool with :func:`volops.volume_downsample` first for large reductions.

    Raises ``ValueError`` when both or neither of *factor* / *shape* are given,
    or when the **output** would exceed ``MAX_VOXELS`` (checked before any
    allocation — a huge factor cannot balloon memory).
    """
    v = _require_volume(vol)
    order = _check_order(order)
    sp = _spacing_tuple(spacing)
    if (factor is None) == (shape is None):
        raise ValueError("vol_resize needs exactly one of factor= or shape= "
                         "(got factor=%r, shape=%r)" % (factor, shape))

    if factor is not None:
        f = np.atleast_1d(np.asarray(factor, dtype=np.float64))
        if f.size == 1:
            f = np.repeat(f, 3)
        if f.size != 3 or not np.isfinite(f).all() or (f <= 0.0).any():
            raise ValueError("factor must be a positive scalar or a length-3 "
                             "(fz, fy, fx) of positive finite values, got %r"
                             % (factor,))
        out_shape = tuple(int(round(d * float(fi))) for d, fi in zip(v.shape, f))
        if min(out_shape) < 1:
            raise ValueError("factor %r collapses the %r volume to shape %r — "
                             "every output axis must have >= 1 voxel"
                             % (factor, v.shape, out_shape))
    else:
        try:
            dims = tuple(float(s) for s in shape)
        except (TypeError, ValueError):
            raise ValueError("shape must be a length-3 (D, H, W) of positive "
                             "integers, got %r" % (shape,)) from None
        if (len(dims) != 3
                or any(not np.isfinite(s) or s != int(s) or int(s) < 1 for s in dims)):
            raise ValueError("shape must be a length-3 (D, H, W) of positive "
                             "integers, got %r" % (shape,))
        out_shape = tuple(int(s) for s in dims)

    _check_output_voxels(out_shape, "vol_resize")
    zoom = [t / s for t, s in zip(out_shape, v.shape)]
    out = ndimage.zoom(v, zoom, order=order, grid_mode=True, mode="grid-constant")
    if out.shape != out_shape:                      # defensive: scipy's rounding drifted
        raise ValueError("vol_resize: scipy.ndimage.zoom produced shape %r instead "
                         "of the requested %r" % (out.shape, out_shape))
    out = np.ascontiguousarray(out, dtype=np.float64)
    if sp is None:
        return out
    new_spacing = tuple(s * d / o for s, d, o in zip(sp, v.shape, out_shape))
    return out, new_spacing


# --------------------------------------------------------------------------- #
# vol_rotate — in-plane rotation about an axis pair                            #
# --------------------------------------------------------------------------- #
def vol_rotate(vol, angle_deg, axes=(1, 2), order=1, reshape=False,
               mode="constant", cval=0.0):
    """Rotate a volume in the plane of an axis pair (``scipy.ndimage.rotate``).

    *axes* names the rotation plane and must be exactly one of ``(0, 1)``
    (z-y plane, turning about the x-axis), ``(0, 2)`` (z-x, about y) or
    ``(1, 2)`` (y-x, about z — the axial-slice rotation; the default). Any
    other pair — including a reversed one like ``(2, 1)`` — raises
    ``ValueError``, so the direction convention below is never silently
    flipped.

    **Direction (pinned)**: a positive *angle_deg* rotates **from the first
    axis of** *axes* **toward the second** — the same convention as
    ``np.rot90``. Concretely, ``vol_rotate(v, 90, axes=a, reshape=False,
    order=0)`` equals ``np.rot90(v, 1, axes=a)`` bit-for-bit when the in-plane
    shape is square (the test pins this).

    ``reshape=False`` (default) keeps the input shape (in-plane corners that
    leave the frame are lost, entering ones are filled with *cval* per *mode*);
    ``reshape=True`` grows the in-plane shape to contain the whole rotated
    frame — the grown output is cap-checked against ``MAX_VOXELS`` *before*
    the call. *order* is the spline degree (exact integer 0..5; >1 overshoots
    — module notes).

    Returns a ``(D, H, W)`` float64 volume (same shape unless *reshape*).
    """
    v = _require_volume(vol)
    order = _check_order(order)
    cval = _check_cval(cval)
    try:
        a = float(angle_deg)
    except (TypeError, ValueError):
        raise ValueError("angle_deg must be a finite angle in degrees, got %r"
                         % (angle_deg,)) from None
    if not np.isfinite(a):
        raise ValueError("angle_deg must be finite, got %r" % (angle_deg,))
    try:
        ax = tuple(int(x) for x in axes)
    except (TypeError, ValueError):
        raise ValueError("axes must be one of (0, 1), (0, 2) or (1, 2), got %r"
                         % (axes,)) from None
    if ax not in _VALID_ROTATE_AXES:
        raise ValueError("axes must be exactly one of (0, 1), (0, 2) or (1, 2) "
                         "(a reversed or repeated pair would silently change the "
                         "rotation direction), got %r" % (axes,))

    if reshape:
        # conservative pre-check of the grown output (>= scipy's actual shape)
        h, w = v.shape[ax[0]], v.shape[ax[1]]
        c, s = abs(np.cos(np.deg2rad(a))), abs(np.sin(np.deg2rad(a)))
        grown = list(v.shape)
        grown[ax[0]] = int(np.ceil(h * c + w * s)) + 1
        grown[ax[1]] = int(np.ceil(h * s + w * c)) + 1
        _check_output_voxels(grown, "vol_rotate (reshape=True)")

    out = ndimage.rotate(v, a, axes=ax, reshape=bool(reshape), order=order,
                         mode=mode, cval=cval)
    return np.ascontiguousarray(out, dtype=np.float64)


# --------------------------------------------------------------------------- #
# vol_affine — the general resampler (pull convention)                         #
# --------------------------------------------------------------------------- #
def vol_affine(vol, matrix, offset=(0, 0, 0), order=1, output_shape=None,
               mode="constant", cval=0.0):
    """General affine resampling (``scipy.ndimage.affine_transform``).

    **Convention (pinned — read this before writing a matrix)**: this is
    scipy's **pull** (output -> input) resampler. For every output voxel at
    integer coordinate ``o = (z, y, x)`` the result is the input interpolated
    at ``matrix @ o + offset``::

        out[o] = vol[ matrix @ o + offset ]        # (z, y, x) order, voxels

    Consequences: ``matrix = 2*I`` makes the object appear **half** size (each
    output step strides two input voxels); ``offset = (1, 2, 3)`` moves the
    object by ``(-1, -2, -3)``. To *push* content through a forward transform
    ``T`` (the pose from a registration), pass the **inverse** of ``T``. The
    test suite machine-pins this direction.

    *matrix* is either a ``(3, 3)`` linear part (with *offset* a separate
    length-3 translation) or a ``(4, 4)`` homogeneous matrix
    ``[[A, t], [0, 0, 0, 1]]`` — then ``A`` / ``t`` are taken from the matrix,
    the bottom row must be exactly ``(0, 0, 0, 1)``, and *offset* must stay at
    its zero default (a second translation would be ambiguous). Any other
    shape raises ``ValueError``.

    *output_shape* defaults to the input shape; an explicit one is cap-checked
    against ``MAX_VOXELS`` before allocation. *order* is the spline degree
    (exact integer 0..5). Voxels whose source coordinate falls outside the
    input are filled per *mode*/*cval*.

    Returns a float64 volume of *output_shape*.
    """
    v = _require_volume(vol)
    order = _check_order(order)
    cval = _check_cval(cval)
    M = np.asarray(matrix, dtype=np.float64)
    if M.shape not in ((3, 3), (4, 4)):
        raise ValueError("matrix must be (3, 3) or a (4, 4) homogeneous matrix, "
                         "got shape %r" % (M.shape,))
    if not np.isfinite(M).all():
        raise ValueError("matrix has non-finite entries — refusing")

    if M.shape == (4, 4):
        if not np.array_equal(M[3], [0.0, 0.0, 0.0, 1.0]):
            raise ValueError("a (4, 4) matrix must be affine-homogeneous: its "
                             "bottom row must be exactly (0, 0, 0, 1), got %r"
                             % (M[3].tolist(),))
        off_arg = np.asarray(offset, dtype=np.float64).ravel()
        if off_arg.size != 3 or off_arg.any():
            raise ValueError("with a (4, 4) homogeneous matrix the translation "
                             "comes from the matrix itself — offset must stay "
                             "(0, 0, 0), got %r (two translations would be "
                             "ambiguous)" % (offset,))
        A, t = M[:3, :3], M[:3, 3]
    else:
        try:
            t = np.asarray(tuple(float(o) for o in offset), dtype=np.float64)
        except (TypeError, ValueError):
            raise ValueError("offset must be a length-3 (oz, oy, ox), got %r"
                             % (offset,)) from None
        if t.size != 3 or not np.isfinite(t).all():
            raise ValueError("offset must be 3 finite values (oz, oy, ox), got %r"
                             % (offset,))
        A = M

    if output_shape is None:
        shp = v.shape
    else:
        try:
            dims = tuple(float(s) for s in output_shape)
        except (TypeError, ValueError):
            raise ValueError("output_shape must be a length-3 (D, H, W) of "
                             "positive integers, got %r" % (output_shape,)) from None
        if (len(dims) != 3
                or any(not np.isfinite(s) or s != int(s) or int(s) < 1 for s in dims)):
            raise ValueError("output_shape must be a length-3 (D, H, W) of "
                             "positive integers, got %r" % (output_shape,))
        shp = tuple(int(s) for s in dims)
    _check_output_voxels(shp, "vol_affine")

    out = ndimage.affine_transform(v, A, offset=t, output_shape=shp, order=order,
                                   mode=mode, cval=cval)
    return np.ascontiguousarray(out, dtype=np.float64)
