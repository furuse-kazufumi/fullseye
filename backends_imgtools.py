"""Image domain / format / crop / bit-plane operators (registry cluster ``imgtools``).

Every operator here implements the GENUINE algorithm named by its HALCON operator
(the ``Op.halcon`` field is the real, previously-uncovered MVTec operator name,
each verified present in ``data/halcon_graph.json`` with ``covered == False``):

  it_add_image_border   add_image_border   add a reflected border (width from a),
                                            fitted back into the HxW frame
  it_crop_part          crop_part          central a-fraction crop resampled back
                                            to HxW (a zoom-in)
  it_crop_rectangle1    crop_rectangle1    the [a .. 1-a] centred rectangle crop
                                            resampled back to HxW
  it_bit_lshift         bit_lshift         8-bit left shift by round(a*7), masked
                                            to 8 bits (wrap), back to [0,1]
  it_bit_rshift         bit_rshift         8-bit right shift by round(a*7)
  it_bit_mask           bit_mask           logical AND with the 8-bit constant
                                            mask round(a*255)
  it_convert_image_type convert_image_type quantise to round(2 + a*254) levels
                                            (bit-depth / precision reduction)
  it_change_format      change_format      change the matrix size to a square of
                                            the max dimension (crop/pad, no
                                            resampling) -- identity for a square
  it_region_to_bin      region_to_bin      threshold at a to a region, then render
                                            it as a two-gray-level binary image
  it_full_domain        full_domain        expand the domain to the full rectangle
                                            -- identity for a plain full-domain array
  it_crop_domain        crop_domain        restrict the domain to the central a
                                            window, zeroing everything outside

Contract: ``fn(v, a, b)`` takes a 2-D float64 image in [0,1] plus two evolution
knobs a,b in [0,1] and returns a 2-D float64 image in [0,1]. Deterministic,
finite, and fail-soft (never raises on the canonical battery). Multichannel
operators (decompose2..7, interleave_channels) are intentionally NOT included:
this cluster is single-gray-image only.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage


def _safe(fn, out_sort=None):
    from backend_safe import sanitize

    def w(v, a, b):
        try:
            out = fn(v, a, b)
        except Exception:  # noqa: BLE001 - fail-soft per op contract
            out = None
        return sanitize(out, v, out_sort)

    return w


# --------------------------------------------------------------------------- #
# small helpers                                                               #
# --------------------------------------------------------------------------- #
def _img(v):
    """Coerce input to a finite 2-D float64 image in [0,1] (fail-soft)."""
    x = np.asarray(v, np.float64)
    if x.ndim == 3:                       # accidental colour -> luma
        x = x.mean(axis=-1)
    elif x.ndim != 2:
        x = np.atleast_2d(x).astype(np.float64)
    x = np.nan_to_num(x, nan=0.0, posinf=1.0, neginf=0.0)
    return np.clip(x, 0.0, 1.0)


def _resize(x, H, W):
    """Deterministic bilinear resample of a 2-D image to exactly (H, W)."""
    x = np.asarray(x, np.float64)
    h, w = x.shape[:2]
    if h < 1 or w < 1:
        return np.zeros((H, W), np.float64)
    if (h, w) == (H, W):
        return x.copy()
    rr = np.linspace(0.0, h - 1, H)
    cc = np.linspace(0.0, w - 1, W)
    R, C = np.meshgrid(rr, cc, indexing="ij")
    out = ndimage.map_coordinates(
        x, np.vstack([R.ravel(), C.ravel()]), order=1, mode="nearest",
    )
    return out.reshape(H, W)


def _q8(x):
    """Quantise a [0,1] image to an 8-bit (uint16-held) integer image 0..255."""
    return np.clip(np.round(_img(x) * 255.0), 0, 255).astype(np.uint16)


# --------------------------------------------------------------------------- #
# operators (module-level so tests can call them directly)                    #
# --------------------------------------------------------------------------- #
def it_add_image_border(v, a, b):
    """add_image_border: pad a reflected border of width ``w`` around the image
    and fit the bordered canvas back into the original HxW frame. ``a`` sets the
    border width w = 1 + round(a*6); ``b`` is ignored."""
    x = _img(v)
    H, W = x.shape[:2]
    if H < 2 or W < 2:
        return x
    w = 1 + int(round(float(np.clip(a, 0.0, 1.0)) * 6))
    w = max(0, min(w, min(H, W) - 1))
    if w == 0:
        return x
    padded = np.pad(x, w, mode="reflect")
    return np.clip(_resize(padded, H, W), 0.0, 1.0)


def it_crop_part(v, a, b):
    """crop_part: cut out the central a-fraction of the image and resample it
    back to HxW -- a genuine zoom-in on the centre. ``b`` is ignored."""
    x = _img(v)
    H, W = x.shape[:2]
    frac = float(np.clip(a, 0.05, 0.95))
    ch = max(1, int(round(H * frac)))
    cw = max(1, int(round(W * frac)))
    r0 = (H - ch) // 2
    c0 = (W - cw) // 2
    crop = x[r0:r0 + ch, c0:c0 + cw]
    return np.clip(_resize(crop, H, W), 0.0, 1.0)


def it_crop_rectangle1(v, a, b):
    """crop_rectangle1: cut out the centred rectangle spanning rows/cols
    [a .. 1-a] and resample it back to HxW. a=0 is (near) identity; larger a
    zooms further in. ``b`` is ignored."""
    x = _img(v)
    H, W = x.shape[:2]
    m = float(np.clip(a, 0.0, 0.45))
    r1 = int(round(H * m))
    c1 = int(round(W * m))
    r2 = max(r1 + 1, H - r1)
    c2 = max(c1 + 1, W - c1)
    crop = x[r1:r2, c1:c2]
    return np.clip(_resize(crop, H, W), 0.0, 1.0)


def it_bit_lshift(v, a, b):
    """bit_lshift: 8-bit quantise, left-shift every pixel by round(a*7), mask to
    8 bits (wrap-around, as HALCON does), and map back to [0,1]. ``b`` ignored."""
    q = _q8(v)
    shift = int(round(float(np.clip(a, 0.0, 1.0)) * 7))
    out = np.left_shift(q, shift) & 0xFF
    return out.astype(np.float64) / 255.0


def it_bit_rshift(v, a, b):
    """bit_rshift: 8-bit quantise then right-shift every pixel by round(a*7)
    (an integer divide by 2**shift -> a coarser, darker image). ``b`` ignored."""
    q = _q8(v)
    shift = int(round(float(np.clip(a, 0.0, 1.0)) * 7))
    out = np.right_shift(q, shift)
    return out.astype(np.float64) / 255.0


def it_bit_mask(v, a, b):
    """bit_mask: logical AND of the 8-bit image with the constant bit mask
    round(a*255). ``b`` is ignored."""
    q = _q8(v)
    mask = int(round(float(np.clip(a, 0.0, 1.0)) * 255)) & 0xFF
    out = np.bitwise_and(q, mask)
    return out.astype(np.float64) / 255.0


def it_convert_image_type(v, a, b):
    """convert_image_type: model a conversion to a lower-precision pixel type by
    quantising to L = round(2 + a*254) evenly spaced levels (bit-depth
    reduction). ``b`` is ignored."""
    x = _img(v)
    levels = int(round(2 + float(np.clip(a, 0.0, 1.0)) * 254))
    levels = max(2, min(256, levels))
    q = np.round(x * (levels - 1)) / (levels - 1)
    return np.clip(q, 0.0, 1.0)


def it_change_format(v, a, b):
    """change_format: change the image matrix size to a square of the maximum
    dimension by cropping/padding at the origin (NO resampling, exactly as
    HALCON change_format does). A square image is returned unchanged; a
    non-square image is zero-expanded to the square. ``a``/``b`` are ignored."""
    x = _img(v)
    H, W = x.shape[:2]
    if H == W:
        return x
    s = max(H, W)
    out = np.zeros((s, s), np.float64)
    out[:min(H, s), :min(W, s)] = x[:min(H, s), :min(W, s)]
    return np.clip(out, 0.0, 1.0)


def it_region_to_bin(v, a, b):
    """region_to_bin: threshold the image at ``a`` to obtain a region, then render
    that region as a two-gray-level binary image -- foreground pixels get the
    high gray value, background pixels the low one. ``b`` sets the two levels:
    lo = 0.5 - 0.5*b, hi = 0.5 + 0.5*b."""
    x = _img(v)
    bb = float(np.clip(b, 0.0, 1.0))
    lo = 0.5 - 0.5 * bb
    hi = 0.5 + 0.5 * bb
    mask = x > float(np.clip(a, 0.0, 1.0))
    return np.where(mask, hi, lo).astype(np.float64)


def it_full_domain(v, a, b):
    """full_domain: expand the domain of the image to the full rectangle. A plain
    numpy array already carries a full domain, so this is the identity -- the
    genuine, correct behaviour of full_domain for such images. ``a``/``b``
    ignored."""
    return _img(v)


def it_crop_domain(v, a, b):
    """crop_domain: restrict the image domain to the central ``a`` window,
    zeroing every pixel outside it (pixels outside the domain are undefined ->
    0). ``a`` sets the kept window fraction; ``b`` is ignored."""
    x = _img(v)
    H, W = x.shape[:2]
    frac = float(np.clip(a, 0.0, 1.0))
    wh = int(round(H * frac))
    ww = int(round(W * frac))
    out = np.zeros_like(x)
    if wh >= 1 and ww >= 1:
        r0 = (H - wh) // 2
        c0 = (W - ww) // 2
        out[r0:r0 + wh, c0:c0 + ww] = x[r0:r0 + wh, c0:c0 + ww]
    return np.clip(out, 0.0, 1.0)


# --------------------------------------------------------------------------- #
# registry                                                                    #
# --------------------------------------------------------------------------- #
def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    defs = [
        ("it_add_image_border", "geometry", "add_image_border", it_add_image_border),
        ("it_crop_part", "geometry", "crop_part", it_crop_part),
        ("it_crop_rectangle1", "geometry", "crop_rectangle1", it_crop_rectangle1),
        ("it_bit_lshift", "gray", "bit_lshift", it_bit_lshift),
        ("it_bit_rshift", "gray", "bit_rshift", it_bit_rshift),
        ("it_bit_mask", "gray", "bit_mask", it_bit_mask),
        ("it_convert_image_type", "gray", "convert_image_type", it_convert_image_type),
        ("it_change_format", "geometry", "change_format", it_change_format),
        ("it_region_to_bin", "segmentation", "region_to_bin", it_region_to_bin),
        # halcon="" — on a plain full-domain numpy array full_domain is a pure identity
        # (imgevolve has no restricted-domain concept), so it adds no observable algorithm;
        # kept as a harmless op but makes no coverage claim.
        ("it_full_domain", "domain", "", it_full_domain),
        ("it_crop_domain", "domain", "crop_domain", it_crop_domain),
    ]
    return [Op(n, c, h, IMAGE, IMAGE, _safe(f, IMAGE)) for (n, c, h, f) in defs]
