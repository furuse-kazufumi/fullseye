"""Multispectral / hyperspectral **cube** handling (numpy + scipy only).

A whole new data modality for the library. Where the existing sorts stop at
three channels — ``image`` (H, W), ``color`` (H, W, 3) — a spectral *cube* is
``(H, W, B)`` with **B > 3** narrow bands plus, ideally, the wavelength each band
samples. Remote sensing (Landsat/Sentinel, AVIRIS, EnMAP), agriculture (NDVI and
friends), food/pharma inspection and art conservation all speak in cubes, and a
scan of the HALCON operator corpus returns **zero** spectral operators — HDevelop
colour handling stops at channel access and RGB colour-space transforms. So this
module is both a genuine format expansion and a clear differentiator.

    import specops as sp
    cube, meta = sp.read_envi("scene.hdr")     # (H, W, B) + BandMeta
    ndvi  = sp.spec_index(cube, nir, red)      # normalised difference engine
    ang   = sp.spec_angle_mapper(cube, ref)    # material match, illumination-invariant
    scr, comp, ev = sp.spec_pca(cube, 3)       # decorrelate the spectral axis
    abund = sp.spec_unmix(cube, endmembers)    # per-pixel material fractions

A cube is ``(H, W, B)`` float; a band is an ``image`` ``(H, W)``. **``color``
(H, W, 3) stays a separate thing**: a cube must *never* be silently truncated to
three channels, and — so that a colour image is never silently processed *as* a
cube — an ``(H, W, 3)`` array is refused where a cube is expected (see
:func:`_as_cube`). B = 2 is allowed (an explicit two-band index); B = 3 is the
only channel count that is ambiguous with RGB, and it is the one that is refused.

These are **plain module functions** surfaced through the ``fullseye`` facade
(like :mod:`stereo` / :mod:`pointcloud`); they are deliberately **not** registered
as evolution ops — a cube is not one of the evolvable image sorts.

References (public):
  * ENVI header — the ENVI Image File Format (ASCII ``.hdr`` + a raw binary cube),
    a long-published, dependency-free spec; this module ships a small numpy-native
    reader/writer rather than depend on ``spectral`` / ``rasterio`` / GDAL.
  * Spectral Angle Mapper — Kruse et al., "The Spectral Image Processing System
    (SIPS)", Remote Sensing of Environment 44 (1993).
  * Minimum Noise Fraction — Green, Berman, Switzer & Craig, "A transformation for
    ordering multispectral data in terms of image quality...", IEEE TGRS 26 (1988).
  * Linear mixing / FCLS — Boardman, Kruse & Green, "Mapping target signatures via
    partial unmixing of AVIRIS data" (1995); Heinz & Chang, "Fully constrained
    least squares linear spectral mixture analysis", IEEE TGRS 39 (2001).
  * Pixel Purity Index — Boardman, Kruse & Green (1995).
  * Pansharpening — Tu, Su, Shyu & Huang, "A new look at IHS-like image fusion
    methods", Information Fusion 2 (2001) (fast/generalised IHS); Gillespie, Kahle
    & Walker, "Color enhancement of highly correlated images. II. Channel ratio and
    'chromaticity' transformation techniques", Remote Sensing of Environment 22
    (1987) (the chromaticity transform popularised as **Brovey**); Chavez, Sides &
    Anderson, "Comparison of three different methods to merge multiresolution and
    multispectral data", PE&RS 57 (1991) (the PC1-substitution merge).
  * Decorrelation stretch — Gillespie, Kahle & Walker, "Color enhancement of highly
    correlated images. I. Decorrelation and HSI contrast stretches", Remote Sensing
    of Environment 20 (1986).
  * Pixel-level multi-source fusion — Naidu & Raol, "Pixel-level image fusion using
    wavelets and principal component analysis", Defence Science Journal 58 (2008)
    (PC1 weighting); Burt & Adelson, "The Laplacian pyramid as a compact image
    code", IEEE Trans. Communications 31 (1983) and Li, Manjunath & Mitra,
    "Multisensor image fusion using the wavelet transform", CVGIP: Graphical Models
    and Image Processing 57 (1995) (the *choose-max* activity selection rule).

Honest limitations (nothing here claims more than its unit test proves):
  * Linear unmixing assumes the **linear** mixing model — one bounce, no multiple
    scattering or intimate (non-linear) mixtures; abundances outside the endmember
    simplex are only approximately handled.
  * :func:`spec_angle_mapper` is **illumination-invariant** (it ignores overall
    brightness) but **not material-unique**: two materials with the same spectral
    *shape* at different amplitudes alias to the same angle.
  * :func:`spec_endmembers_ppi` (and endmember extraction generally) is
    **approximate and stochastic** — it is seeded for determinism, but a different
    seed or projection count gives different pixels; it finds spectrally *extreme*
    pixels, which are pure endmembers only when pure pixels exist in the scene.
  * :func:`spec_pca` is **not** MNF. PCA orders by variance; MNF
    (:func:`spec_mnf`) orders by signal-to-noise and therefore needs a noise
    estimate — here a simple spatial-difference estimate, which assumes the noise
    is spatially white and the signal is not.
  * :func:`spec_continuum_removal` assumes positive reflectance-like spectra.
  * :func:`spec_pansharpen` does **no resampling and no co-registration** — the cube
    must already sit on the panchromatic grid (same H x W). Every method here is a
    *component-substitution* scheme, so all of them trade spectral fidelity for
    spatial detail: Brovey assumes non-negative reflectance and forces the pan
    brightness onto the band ratios, IHS injects the same additive detail into every
    band, and PC1 substitution only preserves the spectral information that does not
    live in the first principal component.
  * :func:`spec_decorrelation_stretch` is a **global** (whole-scene) linear
    transform: directions whose variance is numerically zero (a fully correlated
    cube) carry no information and are zeroed rather than divided by ~0, and
    near-degenerate directions legitimately receive a very large gain — that noise
    amplification is inherent to the method, not a bug.
  * :func:`spec_fuse` is **single-scale**: the ``max_abs_detail`` rule is a
    box-high-pass "choose max activity" selector, not a multiresolution pyramid /
    wavelet fusion, so it can switch source mid-structure and leave a seam. It also
    assumes the sources are already co-registered.

Every reader is **fail-closed** on untrusted input: the header magic and required
fields are validated, the declared cube size is checked against the bytes actually
present, the voxel count is capped (:data:`MAX_VOXELS`), and non-finite data is
rejected. A malformed file raises ``ValueError`` naming the file and the problem —
it never returns partially parsed garbage.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

import numpy as np

__all__ = [
    "BandMeta",
    "read_envi", "write_envi",
    "spec_band", "spec_rgb_composite", "spec_nearest_band",
    "spec_band_ratio", "spec_index",
    "spec_angle_mapper",
    "spec_pca", "spec_mnf",
    "spec_unmix", "spec_endmembers_ppi",
    "spec_continuum_removal",
    "spec_pansharpen", "spec_decorrelation_stretch", "spec_fuse",
    "SPECTRALOPS",
    "PANSHARPEN_METHODS", "FUSE_METHODS",
    "MAX_VOXELS", "MAX_FILE_BYTES", "MAX_BANDS",
]

#: Refuse a cube with more voxels (samples*lines*bands) than this.
MAX_VOXELS = 1 << 28                 # ~268 M voxels (~2 GiB as float64)
#: Refuse an ENVI data file larger than this (untrusted input / DoS guard).
MAX_FILE_BYTES = 1 << 31             # 2 GiB
#: Refuse a header declaring more than this many bands (sanity guard).
MAX_BANDS = 100_000
#: Cap the per-pixel constrained-unmix loop (each pixel is an NNLS solve).
MAX_UNMIX_PIXELS = 4_000_000
#: Cap the per-pixel continuum-removal loop (each pixel is a convex hull).
MAX_CONTINUUM_PIXELS = 4_000_000

_EPS = 1e-12

# ENVI "data type" code -> numpy scalar type (real types only; complex is refused).
_ENVI_DTYPES = {
    1: "u1", 2: "i2", 3: "i4", 4: "f4", 5: "f8",
    12: "u2", 13: "u4", 14: "i8", 15: "u8",
}
_NUMPY_TO_ENVI = {np.dtype(v).name: k for k, v in _ENVI_DTYPES.items()}
_INTERLEAVES = ("bsq", "bil", "bip")
#: Data-file extensions tried next to a ``.hdr`` (ENVI leaves this unspecified).
_ENVI_DATA_EXTS = ("", ".img", ".dat", ".raw", ".bin", ".bsq", ".bil", ".bip", ".cube")


# --------------------------------------------------------------------------- #
# Band metadata                                                               #
# --------------------------------------------------------------------------- #
@dataclass
class BandMeta:
    """Per-band metadata for a cube.

    Fields are all optional (``None`` when the source does not carry them):

    * ``wavelengths_nm`` : (B,) float64, centre wavelength of each band in
      **nanometres** (ENVI micrometre headers are converted on read).
    * ``band_names``     : list[str] of length B, human labels for the bands.
    * ``fwhm``           : (B,) float64, full-width-half-maximum of each band
      (its spectral response width) in nm.
    * ``bad_bands``      : (B,) bool, ``True`` where a band is **bad** (should be
      excluded — water-absorption, dead detector, ...). This is the negation of
      ENVI's ``bbl`` convention, where 1 = good and 0 = bad.
    """
    wavelengths_nm: "np.ndarray | None" = None
    band_names: "list | None" = None
    fwhm: "np.ndarray | None" = None
    bad_bands: "np.ndarray | None" = None
    extra: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.wavelengths_nm is not None:
            self.wavelengths_nm = np.asarray(self.wavelengths_nm, np.float64).ravel()
        if self.fwhm is not None:
            self.fwhm = np.asarray(self.fwhm, np.float64).ravel()
        if self.bad_bands is not None:
            self.bad_bands = np.asarray(self.bad_bands, bool).ravel()
        if self.band_names is not None:
            self.band_names = [str(x) for x in self.band_names]

    def nbands(self):
        """Number of bands implied by whichever field is populated, else ``None``."""
        for v in (self.wavelengths_nm, self.fwhm, self.bad_bands, self.band_names):
            if v is not None:
                return len(v)
        return None


def _meta_wavelengths(meta):
    """Pull a (B,) wavelength array from a :class:`BandMeta` or a plain dict."""
    if isinstance(meta, BandMeta):
        wl = meta.wavelengths_nm
    elif isinstance(meta, dict):
        wl = meta.get("wavelengths_nm", meta.get("wavelength"))
    else:
        wl = getattr(meta, "wavelengths_nm", None)
    if wl is None:
        return None
    return np.asarray(wl, np.float64).ravel()


# --------------------------------------------------------------------------- #
# Cube validation (fail-closed)                                               #
# --------------------------------------------------------------------------- #
def _as_cube(cube, name: str = "cube") -> np.ndarray:
    """Coerce to a validated ``(H, W, B)`` float64 cube or raise ``ValueError``.

    Enforces the modality boundary: a 2-D array is an ``image``; an ``(H, W, 3)``
    array is ``color`` (RGB) and is **refused** here, so a colour image is never
    silently consumed as a spectral cube (and a cube is never silently truncated
    to three channels). B = 2 is accepted (an explicit two-band cube / index);
    B = 3 is the sole ambiguous count and is the one rejected.
    """
    a = np.asarray(cube, np.float64)
    if a.ndim != 3:
        raise ValueError(
            "%s must be a 3-D spectral cube (H, W, B); got a %d-D array of shape %r. "
            "A single band is an `image` (H, W); an RGB frame is `color` (H, W, 3)."
            % (name, a.ndim, a.shape))
    B = a.shape[2]
    if B == 3:
        raise ValueError(
            "%s has 3 channels (H, W, 3): that is the `color` (RGB) sort, not a "
            "multispectral cube. A cube carries B>3 narrow bands (B=2 is allowed as "
            "an explicit two-band cube); B=3 is refused so a colour image is never "
            "silently truncated to / mistaken for a spectral cube — use the colour "
            "ops for RGB, or stack a distinguishing extra band if it is truly a cube."
            % name)
    if B < 2:
        raise ValueError("%s must have at least 2 spectral bands, got B=%d" % (name, B))
    if not np.isfinite(a).all():
        raise ValueError("%s contains non-finite values (NaN/Inf) — clean the cube first"
                         % name)
    return a


def _band_index(i: int, B: int, what: str = "band") -> int:
    i = int(i)
    if not -B <= i < B:
        raise ValueError("%s index %d out of range for %d bands" % (what, i, B))
    return i % B


# --------------------------------------------------------------------------- #
# ENVI header parsing                                                          #
# --------------------------------------------------------------------------- #
def _parse_envi_header(text: str, src: str) -> dict:
    """Parse an ASCII ENVI ``.hdr`` into a ``{key: value}`` dict.

    Keys are lower-cased; brace-delimited values (``{...}``) may span several
    lines and are joined. The first non-blank line must be the ``ENVI`` magic.
    """
    lines = text.splitlines()
    first = next((ln.strip() for ln in lines if ln.strip()), "")
    if first.upper() != "ENVI":
        raise ValueError("%s: not an ENVI header — first line is %r, expected 'ENVI'"
                         % (src, first[:40]))
    params, i, n = {}, 0, len(lines)
    while i < n:
        ln = lines[i]
        i += 1
        if "=" not in ln:
            continue
        key, val = ln.split("=", 1)
        key = key.strip().lower()
        val = val.strip()
        if val.startswith("{") and "}" not in val:      # multi-line brace value
            buf = [val]
            while i < n and "}" not in lines[i]:
                buf.append(lines[i].strip())
                i += 1
            if i < n:                                     # the line carrying the closing }
                buf.append(lines[i].strip())
                i += 1
            val = " ".join(buf)
        if key:
            params[key] = val.strip()
    return params


def _brace_items(val: str):
    """``"{a, b, c}"`` -> ``["a", "b", "c"]`` (empty entries dropped)."""
    v = val.strip()
    if v.startswith("{"):
        v = v[1:]
    if v.endswith("}"):
        v = v[:-1]
    return [x.strip() for x in v.split(",") if x.strip() != ""]


def _req_int(params: dict, key: str, src: str) -> int:
    if key not in params:
        raise ValueError("%s: ENVI header is missing required field %r" % (src, key))
    try:
        return int(str(params[key]).strip())
    except (ValueError, TypeError):
        raise ValueError("%s: ENVI %r is not an integer: %r"
                         % (src, key, params[key])) from None


def _floats_or_raise(items, what: str, src: str) -> np.ndarray:
    try:
        return np.array([float(x) for x in items], np.float64)
    except (ValueError, TypeError):
        raise ValueError("%s: malformed ENVI %s — expected numbers, got %r"
                         % (src, what, items[:6])) from None


def _envi_data_path(hdr_path: str, src: str) -> str:
    """Locate the raw binary cube next to the ``.hdr`` (ENVI does not fix the name)."""
    stem = hdr_path[:-4] if hdr_path.lower().endswith(".hdr") else hdr_path
    tried = []
    for ext in _ENVI_DATA_EXTS:
        for cand in (stem + ext, hdr_path + ext if ext else None):
            if cand is None or cand == hdr_path:
                continue
            tried.append(cand)
            if os.path.isfile(cand):
                return cand
    raise ValueError("%s: no ENVI raw data file found next to the header (tried %s)"
                     % (src, ", ".join(os.path.basename(t) for t in tried[:8])))


def _wavelength_scale(params: dict) -> float:
    """Factor converting the header's wavelength units to **nanometres**."""
    units = str(params.get("wavelength units", "")).strip().lower()
    if "micro" in units or units in ("um", "µm", "microns", "micrometer", "micrometre"):
        return 1000.0
    return 1.0                                          # nm / unspecified -> assume nm


# --------------------------------------------------------------------------- #
# ENVI read / write                                                           #
# --------------------------------------------------------------------------- #
def read_envi(hdr_path: str):
    """Read an ENVI cube -> ``(cube, meta)``.

    *cube* is ``(H, W, B)`` in the file's native scalar type (values are exact —
    integer cubes stay integer, float cubes stay float; the spectral ops coerce to
    float64 internally). *meta* is a :class:`BandMeta` with whatever the header
    carried (wavelengths converted to nm).

    The ASCII ``.hdr`` supplies ``samples`` (W), ``lines`` (H), ``bands`` (B),
    ``data type``, ``interleave`` (BSQ / BIL / BIP), ``byte order`` (0 = little,
    1 = big) and ``header offset``; the raw cube is read from the sibling
    ``.img`` / ``.dat`` / ``.bsq`` / ... file and transposed to ``(H, W, B)``.

    Fail-closed: the magic and required fields are validated, the voxel count is
    capped (:data:`MAX_VOXELS`), and the declared size is checked against the
    bytes actually present — a short or oversized file raises ``ValueError``.
    """
    src = str(hdr_path)
    if not os.path.isfile(src):
        raise FileNotFoundError(src)
    with open(src, "r", encoding="utf-8", errors="replace") as f:
        params = _parse_envi_header(f.read(), src)

    W = _req_int(params, "samples", src)
    H = _req_int(params, "lines", src)
    B = _req_int(params, "bands", src)
    dtype_code = _req_int(params, "data type", src)
    if min(W, H, B) < 1:
        raise ValueError("%s: ENVI samples/lines/bands must be positive, got %dx%dx%d"
                         % (src, W, H, B))
    if B > MAX_BANDS:
        raise ValueError("%s: ENVI declares %d bands, over the %d cap (spectral.MAX_BANDS)"
                         % (src, B, MAX_BANDS))
    if dtype_code not in _ENVI_DTYPES:
        raise ValueError("%s: ENVI data type %d is unsupported here (want one of %s; "
                         "complex types are not read)"
                         % (src, dtype_code, sorted(_ENVI_DTYPES)))
    interleave = str(params.get("interleave", "bsq")).strip().lower()
    if interleave not in _INTERLEAVES:
        raise ValueError("%s: ENVI interleave %r is not one of %s"
                         % (src, interleave, _INTERLEAVES))
    byte_order = int(str(params.get("byte order", "0")).strip() or "0")
    if byte_order not in (0, 1):
        raise ValueError("%s: ENVI byte order must be 0 or 1, got %r" % (src, byte_order))
    header_offset = int(str(params.get("header offset", "0")).strip() or "0")
    if header_offset < 0:
        raise ValueError("%s: ENVI header offset must be >= 0, got %d" % (src, header_offset))

    voxels = int(W) * int(H) * int(B)
    if voxels > MAX_VOXELS:
        raise ValueError("%s: ENVI cube is %dx%dx%d = %d voxels, over the %d cap "
                         "(spectral.MAX_VOXELS)" % (src, H, W, B, voxels, MAX_VOXELS))

    data_path = _envi_data_path(src, src)
    file_size = os.path.getsize(data_path)
    if file_size > MAX_FILE_BYTES:
        raise ValueError("%s: ENVI data file %s is %d bytes, over the %d cap "
                         "(spectral.MAX_FILE_BYTES)"
                         % (src, os.path.basename(data_path), file_size, MAX_FILE_BYTES))
    endian = "<" if byte_order == 0 else ">"
    dt = np.dtype(endian + _ENVI_DTYPES[dtype_code])
    need = header_offset + voxels * dt.itemsize
    if file_size < need:
        raise ValueError("%s: ENVI header declares %dx%dx%d %s voxels (%d bytes after a "
                         "%d-byte offset) but the data file holds only %d bytes"
                         % (src, H, W, B, dt.name, voxels * dt.itemsize, header_offset,
                            file_size))
    flat = np.fromfile(data_path, dtype=dt, count=voxels, offset=header_offset)
    if flat.size != voxels:
        raise ValueError("%s: ENVI data file yielded %d of %d expected voxels"
                         % (src, flat.size, voxels))

    if interleave == "bsq":                              # (bands, lines, samples)
        cube = flat.reshape(B, H, W).transpose(1, 2, 0)
    elif interleave == "bil":                            # (lines, bands, samples)
        cube = flat.reshape(H, B, W).transpose(0, 2, 1)
    else:                                                # bip: (lines, samples, bands)
        cube = flat.reshape(H, W, B)
    # Materialise in the native byte order of the same scalar type (values exact).
    cube = np.ascontiguousarray(cube).astype(np.dtype(_ENVI_DTYPES[dtype_code]))

    meta = _meta_from_params(params, B, src)
    return cube, meta


def _meta_from_params(params: dict, B: int, src: str) -> BandMeta:
    wl = names = fwhm = bad = None
    if "wavelength" in params:
        wl = _floats_or_raise(_brace_items(params["wavelength"]), "wavelength", src)
        if wl.size != B:
            raise ValueError("%s: ENVI has %d wavelengths for %d bands" % (src, wl.size, B))
        wl = wl * _wavelength_scale(params)
    if "band names" in params:
        names = _brace_items(params["band names"])
        if len(names) != B:
            raise ValueError("%s: ENVI has %d band names for %d bands" % (src, len(names), B))
    if "fwhm" in params:
        fwhm = _floats_or_raise(_brace_items(params["fwhm"]), "fwhm", src)
        if fwhm.size != B:
            raise ValueError("%s: ENVI has %d fwhm values for %d bands" % (src, fwhm.size, B))
        fwhm = fwhm * _wavelength_scale(params)
    if "bbl" in params:
        bbl = _floats_or_raise(_brace_items(params["bbl"]), "bbl", src)
        if bbl.size != B:
            raise ValueError("%s: ENVI has %d bbl entries for %d bands" % (src, bbl.size, B))
        bad = bbl == 0                                   # ENVI: 1 = good, 0 = bad
    return BandMeta(wavelengths_nm=wl, band_names=names, fwhm=fwhm, bad_bands=bad)


def write_envi(hdr_path: str, cube, meta=None, interleave: str = "bsq",
               byte_order: int = 0, dtype=None) -> None:
    """Write an ENVI cube: an ASCII ``.hdr`` at *hdr_path* and a sibling ``.img``
    raw binary file. The inverse of :func:`read_envi` (used for round-trip tests).

    *cube* is ``(H, W, B)``. *interleave* is BSQ / BIL / BIP; *byte order* is 0
    (little) or 1 (big) — writing a non-native order exercises the reader's
    byte-order handling. By default the on-disk scalar type follows the cube's
    dtype (float64 cubes round-trip exactly); pass *dtype* to force another.
    *meta* (:class:`BandMeta`) is written as ``wavelength`` / ``band names`` /
    ``fwhm`` / ``bbl`` when present.
    """
    src = str(hdr_path)
    interleave = str(interleave).strip().lower()
    if interleave not in _INTERLEAVES:
        raise ValueError("%s: interleave %r is not one of %s" % (src, interleave, _INTERLEAVES))
    if int(byte_order) not in (0, 1):
        raise ValueError("%s: byte order must be 0 or 1, got %r" % (src, byte_order))

    a = np.asarray(cube)
    if a.ndim != 3 or a.shape[2] < 1:
        raise ValueError("%s: cube to write must be (H, W, B), got shape %r" % (src, a.shape))
    if not np.isfinite(np.asarray(a, np.float64)).all():
        raise ValueError("%s: cube to write contains non-finite values" % src)
    H, W, B = a.shape

    np_name = np.dtype(dtype).name if dtype is not None else np.dtype(a.dtype).name
    if np_name not in _NUMPY_TO_ENVI:
        raise ValueError("%s: dtype %r has no ENVI data-type code (supported: %s)"
                         % (src, np_name, sorted(_NUMPY_TO_ENVI)))
    code = _NUMPY_TO_ENVI[np_name]
    endian = "<" if int(byte_order) == 0 else ">"
    np_dt = np.dtype(endian + _ENVI_DTYPES[code])

    if interleave == "bsq":
        disk = np.asarray(a).transpose(2, 0, 1)          # (B, H, W)
    elif interleave == "bil":
        disk = np.asarray(a).transpose(0, 2, 1)          # (H, B, W)
    else:
        disk = np.asarray(a)                             # bip: (H, W, B)
    disk = np.ascontiguousarray(disk).astype(np_dt)

    stem = src[:-4] if src.lower().endswith(".hdr") else src
    data_path = stem + ".img"
    disk.tofile(data_path)

    lines = ["ENVI",
             "description = {fullseye spectral cube}",
             "samples = %d" % W,
             "lines = %d" % H,
             "bands = %d" % B,
             "header offset = 0",
             "file type = ENVI Standard",
             "data type = %d" % code,
             "interleave = %s" % interleave,
             "byte order = %d" % int(byte_order)]
    if meta is not None:
        wl = _meta_wavelengths(meta)
        names = getattr(meta, "band_names", None) if not isinstance(meta, dict) else meta.get("band_names")
        fwhm = getattr(meta, "fwhm", None) if not isinstance(meta, dict) else meta.get("fwhm")
        bad = getattr(meta, "bad_bands", None) if not isinstance(meta, dict) else meta.get("bad_bands")
        if wl is not None:
            if wl.size != B:
                raise ValueError("%s: meta has %d wavelengths for %d bands" % (src, wl.size, B))
            lines.append("wavelength units = Nanometers")
            lines.append("wavelength = {%s}" % ", ".join("%.17g" % x for x in wl))
        if names is not None:
            names = [str(x) for x in names]
            if len(names) != B:
                raise ValueError("%s: meta has %d band names for %d bands" % (src, len(names), B))
            lines.append("band names = {%s}" % ", ".join(names))
        if fwhm is not None:
            fwhm = np.asarray(fwhm, np.float64).ravel()
            if fwhm.size != B:
                raise ValueError("%s: meta has %d fwhm for %d bands" % (src, fwhm.size, B))
            lines.append("fwhm = {%s}" % ", ".join("%.17g" % x for x in fwhm))
        if bad is not None:
            bad = np.asarray(bad, bool).ravel()
            if bad.size != B:
                raise ValueError("%s: meta has %d bad-band flags for %d bands" % (src, bad.size, B))
            lines.append("bbl = {%s}" % ", ".join("0" if b else "1" for b in bad))
    with open(src, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# --------------------------------------------------------------------------- #
# Band access / composites                                                    #
# --------------------------------------------------------------------------- #
def spec_band(cube, i: int) -> np.ndarray:
    """Extract band *i* of the cube as an ``image`` ``(H, W)`` float64 (a copy).
    Negative indices count from the end (numpy convention)."""
    a = _as_cube(cube)
    i = _band_index(i, a.shape[2])
    return a[:, :, i].copy()


def spec_rgb_composite(cube, bands=None, stretch: bool = True) -> np.ndarray:
    """Build a viewable ``color`` ``(H, W, 3)`` image from three chosen bands.

    *bands* is ``(r, g, b)`` band indices; the default spreads three bands across
    the cube. With *stretch* (default) each channel is min-max scaled to [0, 1] so
    the composite is displayable. This is an explicit, band-chosen projection —
    the cube itself is never silently reduced to three channels.
    """
    a = _as_cube(cube)
    B = a.shape[2]
    if bands is None:
        bands = (int(round(0.70 * (B - 1))), int(round(0.50 * (B - 1))),
                 int(round(0.30 * (B - 1))))
    bands = tuple(bands)
    if len(bands) != 3:
        raise ValueError("bands must be 3 indices (r, g, b), got %r" % (bands,))
    chans = []
    for idx in bands:
        c = a[:, :, _band_index(idx, B, "composite band")]
        if stretch:
            lo, hi = float(np.min(c)), float(np.max(c))
            c = (c - lo) / (hi - lo) if hi > lo else np.zeros_like(c)
        chans.append(c)
    return np.clip(np.stack(chans, axis=-1), 0.0, 1.0)


def spec_nearest_band(meta, wavelength_nm: float) -> int:
    """Index of the band whose centre wavelength is nearest *wavelength_nm*.

    *meta* is a :class:`BandMeta` (or a dict with ``wavelengths_nm``). This is how
    you turn "the red band" / "the NIR band" into concrete indices for
    :func:`spec_index`. Raises ``ValueError`` if no wavelengths are known.
    """
    wl = _meta_wavelengths(meta)
    if wl is None or wl.size == 0:
        raise ValueError("meta has no wavelengths_nm — cannot locate a band by wavelength")
    return int(np.argmin(np.abs(wl - float(wavelength_nm))))


# --------------------------------------------------------------------------- #
# Band arithmetic: ratios and normalised-difference indices                   #
# --------------------------------------------------------------------------- #
def spec_band_ratio(cube, i: int, j: int, eps: float = _EPS) -> np.ndarray:
    """Per-pixel band ratio ``band_i / (band_j + eps)`` -> ``image`` ``(H, W)``.

    Simple band ratios (e.g. a clay/iron-oxide ratio in geology) suppress
    illumination/topographic shading, which scales all bands together. *eps*
    guards a zero denominator; the inputs are assumed non-negative (reflectance).
    """
    a = _as_cube(cube)
    B = a.shape[2]
    bi = a[:, :, _band_index(i, B)]
    bj = a[:, :, _band_index(j, B)]
    return bi / (bj + float(eps))


def spec_index(cube, a: int, b: int, eps: float = _EPS) -> np.ndarray:
    """Normalised-difference index ``(band_a - band_b) / (band_a + band_b + eps)``.

    The generic engine behind the whole normalised-difference family — pick the
    band pair and you get the index. For example **NDVI** (vegetation vigour) is
    ``(NIR - Red) / (NIR + Red)``::

        red = spec_nearest_band(meta, 665.0)
        nir = spec_nearest_band(meta, 842.0)
        ndvi = spec_index(cube, nir, red)          # in [-1, 1]

    NDWI (water) is ``(Green - NIR)`` normalised, NDSI (snow) ``(Green - SWIR)``,
    and so on. For non-negative inputs the result lies in ``[-1, 1]``. Returns an
    ``image`` ``(H, W)``.
    """
    ca = _as_cube(cube)
    B = ca.shape[2]
    ba = ca[:, :, _band_index(a, B)]
    bb = ca[:, :, _band_index(b, B)]
    return (ba - bb) / (ba + bb + float(eps))


# --------------------------------------------------------------------------- #
# Spectral Angle Mapper                                                        #
# --------------------------------------------------------------------------- #
def spec_angle_mapper(cube, reference) -> np.ndarray:
    """Per-pixel **spectral angle** (radians) to a *reference* spectrum ``(B,)``.

    SAM (Kruse et al. 1993) treats each pixel's B-band spectrum as a vector and
    measures the angle to the reference: ``arccos( <p, r> / (|p| |r|) )``. Because
    it uses only the *direction* of the spectral vector, it is **illumination-
    invariant** — scaling a pixel by overall brightness (shadow, slope, exposure)
    leaves the angle unchanged. A **small** angle means a good spectral match.

    Returns an ``image`` ``(H, W)`` in ``[0, pi]``. Zero-norm pixels (no signal)
    map to ``pi/2`` (maximally dissimilar). Honest limit: SAM matches spectral
    *shape*, not material identity — two materials with the same shape at different
    amplitudes alias to the same angle (see module docstring).
    """
    a = _as_cube(cube)
    B = a.shape[2]
    ref = np.asarray(reference, np.float64).ravel()
    if ref.shape[0] != B:
        raise ValueError("reference spectrum has %d bands but the cube has %d"
                         % (ref.shape[0], B))
    if not np.isfinite(ref).all():
        raise ValueError("reference spectrum contains non-finite values")
    rn = float(np.linalg.norm(ref))
    if rn <= 0.0:
        raise ValueError("reference spectrum has zero norm — cannot form an angle")
    dots = a @ ref                                       # (H, W)
    pn = np.linalg.norm(a, axis=2)                       # (H, W)
    denom = pn * rn
    with np.errstate(invalid="ignore", divide="ignore"):
        cos = np.where(denom > 0.0, dots / denom, 0.0)
    return np.arccos(np.clip(cos, -1.0, 1.0))


# --------------------------------------------------------------------------- #
# Dimensionality reduction: PCA and MNF                                        #
# --------------------------------------------------------------------------- #
def _flatten(cube):
    a = _as_cube(cube)
    H, W, B = a.shape
    return a, H, W, B, a.reshape(-1, B)


def spec_pca(cube, n_components: int = 3):
    """Principal-component analysis over the **spectral** axis.

    Mean-centres the pixel spectra and eigen-decomposes the ``(B, B)`` band
    covariance; the top *n_components* eigenvectors are the directions of greatest
    spectral variance. Returns ``(scores, components, explained_variance)``:

    * ``scores``  (H, W, n) — each pixel projected onto the components.
    * ``components`` (n, B) — the eigenvectors (unit, sign-arbitrary).
    * ``explained_variance`` (n,) — the **fraction of total spectral variance**
      each returned component captures (like sklearn's
      ``explained_variance_ratio_``).

    PCA decorrelates and compresses hyperspectral bands (which are highly
    redundant). Note this is **not** MNF (:func:`spec_mnf`): PCA orders by variance
    alone and does not model noise.
    """
    a, H, W, B, X = _flatten(cube)
    n = int(n_components)
    if not 1 <= n <= B:
        raise ValueError("n_components must be in 1..%d, got %d" % (B, n))
    mean = X.mean(axis=0)
    Xc = X - mean
    denom = max(X.shape[0] - 1, 1)
    cov = (Xc.T @ Xc) / denom                            # (B, B)
    evals, evecs = np.linalg.eigh(cov)                   # ascending
    order = np.argsort(evals)[::-1]
    evals, evecs = evals[order], evecs[:, order]
    comps = evecs[:, :n].T                               # (n, B)
    scores = (Xc @ comps.T).reshape(H, W, n)
    total = float(evals.sum())
    ratio = (evals[:n] / total) if total > 0 else np.zeros(n)
    return scores, comps, np.asarray(ratio, np.float64)


def spec_mnf(cube, n_components: int = 3):
    """Minimum Noise Fraction transform (Green et al. 1988) — a **documented
    variant** of :func:`spec_pca` that orders components by signal-to-noise rather
    than variance.

    The noise covariance is estimated from the horizontal pixel-to-pixel
    difference (``cube[:, 1:] - cube[:, :-1]``, halved), the data is whitened by it,
    and PCA is run on the whitened data. Returns the same
    ``(scores, components, snr_fraction)`` triple as :func:`spec_pca`, where the
    last array is the per-component share of the summed SNR eigenvalues.

    Honest limit: MNF is only as good as the noise estimate. This spatial-
    difference estimate assumes the noise is spatially white and the signal is
    locally smooth; a real sensor noise model (dark frames / homogeneous regions)
    would be better. Needs W >= 2.
    """
    a, H, W, B, X = _flatten(cube)
    n = int(n_components)
    if not 1 <= n <= B:
        raise ValueError("n_components must be in 1..%d, got %d" % (B, n))
    if W < 2:
        raise ValueError("spec_mnf needs W >= 2 to estimate noise from horizontal differences")
    mean = X.mean(axis=0)
    Xc = X - mean
    data_cov = (Xc.T @ Xc) / max(X.shape[0] - 1, 1)
    diff = (a[:, 1:, :] - a[:, :-1, :]).reshape(-1, B)
    Nc = diff - diff.mean(axis=0)
    noise_cov = (Nc.T @ Nc) / (2.0 * max(Nc.shape[0] - 1, 1))   # var(a-b)=2 var -> halve
    ev_n, U = np.linalg.eigh(noise_cov)
    ev_n = np.clip(ev_n, _EPS, None)
    whiten = U @ np.diag(ev_n ** -0.5)                   # (B, B): decorrelate + unit noise
    Cd = whiten.T @ data_cov @ whiten
    ev_d, V = np.linalg.eigh(Cd)
    order = np.argsort(ev_d)[::-1]
    ev_d, V = ev_d[order], V[:, order]
    transform = whiten @ V                               # MNF vectors in the original space
    comps = transform[:, :n].T                           # (n, B)
    scores = (Xc @ comps.T).reshape(H, W, n)
    total = float(ev_d.sum())
    frac = (ev_d[:n] / total) if total > 0 else np.zeros(n)
    return scores, comps, np.asarray(frac, np.float64)


# --------------------------------------------------------------------------- #
# Linear spectral unmixing                                                     #
# --------------------------------------------------------------------------- #
def spec_unmix(cube, endmembers, constrained: bool = True,
               sum_weight: float = 1e3) -> np.ndarray:
    """Linear spectral unmixing -> per-pixel abundance maps ``(H, W, K)``.

    The linear mixing model says each pixel spectrum is a weighted sum of *K*
    pure-material *endmembers* (rows of ``endmembers``, shape ``(K, B)``): given a
    pixel ``p`` (B,) it solves for abundances ``a`` (K,) with ``p ~ a @ endmembers``.

    * ``constrained=False`` — unconstrained least squares (``p @ pinv(E)``);
      abundances can be negative or exceed 1.
    * ``constrained=True`` (default) — **fully constrained** (FCLS): non-negative
      **and** sum-to-one. Implemented as a per-pixel non-negative least squares
      (``scipy.optimize.nnls``) with the standard sum-to-one augmentation (an extra
      equation of weight *sum_weight* driving the abundances to sum to 1;
      Heinz & Chang 2001).

    Honest limits: this is the **linear** model only — no multiple scattering or
    intimate mixtures; the sum-to-one constraint is enforced softly via
    *sum_weight* (raise it for a tighter sum, at some conditioning cost). The
    constrained solver loops per pixel and is capped at :data:`MAX_UNMIX_PIXELS`.
    """
    a = _as_cube(cube)
    H, W, B = a.shape
    E = np.asarray(endmembers, np.float64)
    if E.ndim != 2 or E.shape[1] != B:
        raise ValueError("endmembers must be (K, B) with B=%d matching the cube, got %r"
                         % (B, (E.shape,)))
    if not np.isfinite(E).all():
        raise ValueError("endmembers contain non-finite values")
    K = E.shape[0]
    if K < 1:
        raise ValueError("need at least one endmember, got %d" % K)
    P = a.reshape(-1, B)
    N = P.shape[0]

    if not constrained:
        A = P @ np.linalg.pinv(E)                        # (N, K), unconstrained LS
        return A.reshape(H, W, K)

    if N > MAX_UNMIX_PIXELS:
        raise ValueError("constrained unmix over %d pixels exceeds the %d cap "
                         "(spectral.MAX_UNMIX_PIXELS) — downsample or use constrained=False"
                         % (N, MAX_UNMIX_PIXELS))
    from scipy.optimize import nnls

    delta = float(sum_weight)
    if delta <= 0.0:
        raise ValueError("sum_weight must be > 0, got %r" % (sum_weight,))
    M = np.vstack([E.T, delta * np.ones((1, K))])        # (B+1, K)
    A = np.zeros((N, K), np.float64)
    y = np.empty(B + 1, np.float64)
    y[B] = delta                                         # the sum-to-one target row
    for idx in range(N):
        y[:B] = P[idx]
        A[idx], _ = nnls(M, y)
    return A.reshape(H, W, K)


def spec_endmembers_ppi(cube, n_endmembers: int, n_projections: int = 1000,
                        seed: int = 0) -> np.ndarray:
    """Approximate endmember extraction by the **Pixel Purity Index** (Boardman
    1995) -> ``endmembers`` ``(K, B)``.

    Pixels are projected onto many random unit "skewers"; the pixel at each
    projection's extreme (min/max) scores a purity point. The *K* pixels with the
    highest scores — the most spectrally extreme — are returned as endmember
    spectra. Deterministic for a given *seed*.

    Honest limits: PPI is **approximate and stochastic** — different seeds /
    projection counts give different pixels, and it finds *extreme* pixels, which
    are pure endmembers only when genuinely pure pixels exist in the scene. Feed
    the result to :func:`spec_unmix` (or refine by hand).
    """
    a = _as_cube(cube)
    H, W, B = a.shape
    K = int(n_endmembers)
    if K < 1:
        raise ValueError("n_endmembers must be >= 1, got %d" % K)
    n_proj = int(n_projections)
    if n_proj < 1:
        raise ValueError("n_projections must be >= 1, got %d" % n_proj)
    P = a.reshape(-1, B)
    N = P.shape[0]
    if K > N:
        raise ValueError("asked for %d endmembers but the cube has only %d pixels" % (K, N))

    rng = np.random.default_rng(int(seed))
    counts = np.zeros(N, np.int64)
    block = max(1, min(n_proj, (1 << 22) // max(N, 1) + 1))   # bound the (N, block) matmul
    done = 0
    while done < n_proj:
        m = min(block, n_proj - done)
        V = rng.standard_normal((B, m))
        V /= np.maximum(np.linalg.norm(V, axis=0, keepdims=True), _EPS)
        proj = P @ V                                     # (N, m)
        np.add.at(counts, proj.argmax(axis=0), 1)
        np.add.at(counts, proj.argmin(axis=0), 1)
        done += m
    chosen = np.argsort(counts)[::-1][:K]
    return P[chosen].copy()


# --------------------------------------------------------------------------- #
# Continuum removal                                                            #
# --------------------------------------------------------------------------- #
def _upper_hull_envelope(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Upper convex-hull envelope of ``y(x)`` sampled back at every *x* (the
    "continuum"). *x* must be strictly increasing."""
    n = len(x)
    hull = []                                            # indices of the upper hull
    for i in range(n):
        while len(hull) >= 2:
            x1, y1 = x[hull[-2]], y[hull[-2]]
            x2, y2 = x[hull[-1]], y[hull[-1]]
            cross = (x2 - x1) * (y[i] - y1) - (y2 - y1) * (x[i] - x1)
            if cross >= 0.0:                             # left/collinear turn -> not upper hull
                hull.pop()
            else:
                break
        hull.append(i)
    return np.interp(x, x[hull], y[hull])


def spec_continuum_removal(cube, wavelengths=None) -> np.ndarray:
    """Continuum removal -> a cube of the same shape with each spectrum divided by
    its upper convex hull (its "continuum").

    This normalises out the broad spectral shape so **absorption features** (the
    dips diagnostic of minerals, vegetation biochemistry, ...) stand out on a
    common ``(0, 1]`` scale, comparable between pixels regardless of overall
    brightness. *wavelengths* gives the spectral x-axis (defaults to band index).

    Honest limits: assumes positive, reflectance-like spectra; it loops per pixel
    (each is a convex hull) and is capped at :data:`MAX_CONTINUUM_PIXELS`.
    """
    a = _as_cube(cube)
    H, W, B = a.shape
    x = (np.arange(B, dtype=np.float64) if wavelengths is None
         else np.asarray(wavelengths, np.float64).ravel())
    if x.shape[0] != B:
        raise ValueError("wavelengths has %d entries but the cube has %d bands"
                         % (x.shape[0], B))
    if np.any(np.diff(x) <= 0):
        raise ValueError("wavelengths must be strictly increasing")
    N = H * W
    if N > MAX_CONTINUUM_PIXELS:
        raise ValueError("continuum removal over %d pixels exceeds the %d cap "
                         "(spectral.MAX_CONTINUUM_PIXELS)" % (N, MAX_CONTINUUM_PIXELS))
    P = a.reshape(N, B)
    out = np.empty_like(P)
    for i in range(N):
        hull = _upper_hull_envelope(x, P[i])
        out[i] = P[i] / np.where(np.abs(hull) > _EPS, hull, _EPS)
    return out.reshape(H, W, B)


# --------------------------------------------------------------------------- #
# Fusion: pansharpening, decorrelation stretch, multi-source image fusion      #
# --------------------------------------------------------------------------- #
#: Component-substitution methods accepted by :func:`spec_pansharpen`.
PANSHARPEN_METHODS = ("brovey", "ihs", "pca")
#: Pixel-level fusion rules accepted by :func:`spec_fuse`.
FUSE_METHODS = ("pca", "average", "max_abs_detail")


def _as_pan(pan, H: int, W: int, name: str = "pan") -> np.ndarray:
    """Coerce the panchromatic band to a validated ``(H, W)`` float64 image.

    Fail-closed: the pan band must be 2-D, exactly the cube's spatial size (this
    module does **not** resample — put both on a common grid first) and finite.
    """
    p = np.asarray(pan, np.float64)
    if p.ndim != 2:
        raise ValueError(
            "%s must be a 2-D panchromatic `image` (H, W); got a %d-D array of shape %r"
            % (name, p.ndim, p.shape))
    if p.shape != (H, W):
        raise ValueError(
            "%s is %r but the cube is %dx%d — resample the pan band and the cube onto a "
            "common grid before fusing (spec_pansharpen does no resampling)"
            % (name, p.shape, H, W))
    if not np.isfinite(p).all():
        raise ValueError("%s contains non-finite values (NaN/Inf)" % name)
    return p


def _finite_or_raise(out: np.ndarray, what: str) -> np.ndarray:
    """Fail-closed output guard: never hand back NaN/Inf (module-wide contract)."""
    if not np.isfinite(out).all():
        raise ValueError(
            "%s produced non-finite values — the input is outside the method's "
            "numerical range (check for zero/negative band means or extreme dynamic "
            "range)" % what)
    return out


def _canonical_signs(V: np.ndarray) -> np.ndarray:
    """Fix the arbitrary sign of each eigenvector **column** deterministically.

    ``numpy.linalg.eigh`` returns eigenvectors up to a sign. Flipping each column so
    that its largest-magnitude entry is positive (ties -> the first such entry) makes
    the basis a pure function of the input, which is what determinism requires.
    """
    out = np.array(V, np.float64, copy=True)
    for k in range(out.shape[1]):
        col = out[:, k]
        if col[int(np.argmax(np.abs(col)))] < 0.0:
            out[:, k] = -col
    return out


def _pca_basis(X: np.ndarray):
    """``(mean, components, eigenvalues)`` of the (N, B) matrix *X*.

    *components* is ``(B, B)`` with the eigenvectors as **columns**, ordered by
    descending eigenvalue and sign-canonicalised (see :func:`_canonical_signs`).
    """
    mean = X.mean(axis=0)
    Xc = X - mean
    cov = (Xc.T @ Xc) / max(X.shape[0] - 1, 1)
    evals, V = np.linalg.eigh(cov)                       # ascending, V columns
    order = np.argsort(evals)[::-1]
    return mean, _canonical_signs(V[:, order]), np.clip(evals[order], 0.0, None)


def _match_ranks_to(src: np.ndarray, ref: np.ndarray) -> np.ndarray:
    """Exact histogram matching by rank: *src* re-quantised onto *ref*'s values.

    Both are 1-D and the same length. The i-th output is the value of ``sort(ref)``
    at the rank *src[i]* holds within *src*, so the result carries **ref's exact
    empirical distribution** with **src's ordering**. Stable sorts make ties (and
    therefore the whole mapping) deterministic; when ``src is ref`` the mapping is
    the identity, including under ties.
    """
    order = np.argsort(src, kind="stable")
    ranks = np.empty(order.size, np.intp)
    ranks[order] = np.arange(order.size, dtype=np.intp)
    return np.sort(ref, kind="stable")[ranks]


def spec_pansharpen(cube, pan, method: str = "brovey", eps: float = _EPS) -> np.ndarray:
    """Fuse a high-resolution **panchromatic** band into a multispectral cube ->
    ``(H, W, B)``, the same shape as *cube*.

    Pansharpening buys the spatial detail of the broad, high-resolution pan channel
    for the spectrally rich but coarse cube. All three methods here are
    *component-substitution* schemes; *cube* must already be resampled onto the pan
    grid (identical ``H x W`` — nothing is resampled here).

    * ``"brovey"`` (default) — the chromaticity / colour-normalised transform
      (Gillespie et al. 1987, popularised as the Brovey transform)::

          fused_i = cube_i * pan / (mean_over_bands(cube) + eps)

      Every band is scaled by the **same** per-pixel factor, so the band *ratios*
      of the input survive exactly (``fused_i / fused_j == cube_i / cube_j``) — that
      is the defining property of the method, and the unit test asserts it.
    * ``"ihs"`` — fast / generalised IHS (Tu et al. 2001): the intensity
      ``I = mean_over_bands(cube)`` is *replaced* by the pan band, which for the
      generalised (additive) form is ``fused_i = cube_i + (pan - I)``. The fused
      cube then has ``mean_over_bands(fused) == pan`` exactly. Classical IHS is
      defined for three bands; the generalised form used here takes the intensity
      over **all** B bands, so it applies to any cube.
    * ``"pca"`` — PC1 substitution (Chavez et al. 1991): the cube is PCA-rotated
      (:func:`spec_pca`'s transform), PC1 is replaced by the pan band **histogram-
      matched to PC1's own distribution** (exact rank matching, so the injected
      component keeps PC1's radiometry), and the inverse rotation is applied.
      Components 2..B pass through untouched.

    *eps* guards the Brovey denominator; the guard is floored at ``1e-12`` times the
    cube's peak magnitude so a near-zero band mean cannot blow up. The output keeps
    the cube's radiometric scale (it is **not** rescaled to [0, 1]) and is verified
    finite. Fail-closed on a shape/finiteness mismatch or an unknown *method*.
    """
    a = _as_cube(cube)
    H, W, B = a.shape
    p = _as_pan(pan, H, W)
    m = str(method).strip().lower()
    if m not in PANSHARPEN_METHODS:
        raise ValueError("method %r is not one of %s" % (method, PANSHARPEN_METHODS))
    if not np.isfinite(eps) or float(eps) < 0.0:
        raise ValueError("eps must be a finite value >= 0, got %r" % (eps,))

    if m == "brovey":
        inten = a.mean(axis=2)                           # (H, W)
        scale = float(np.max(np.abs(a)))
        floor = max(float(eps), _EPS * (scale if scale > 0.0 else 1.0))
        denom = np.where(np.abs(inten) > floor, inten, floor)
        return _finite_or_raise(a * (p / denom)[:, :, None], "spec_pansharpen('brovey')")

    if m == "ihs":
        inten = a.mean(axis=2)                           # generalised IHS intensity
        return _finite_or_raise(a + (p - inten)[:, :, None], "spec_pansharpen('ihs')")

    X = a.reshape(-1, B)
    mean, V, _ = _pca_basis(X)                           # V: (B, B), columns
    scores = (X - mean) @ V                              # (N, B)
    scores[:, 0] = _match_ranks_to(p.reshape(-1), scores[:, 0])
    fused = (scores @ V.T + mean).reshape(H, W, B)
    return _finite_or_raise(fused, "spec_pansharpen('pca')")


def _select_bands(B: int, bands, name: str = "bands") -> np.ndarray:
    """Validate an explicit band selection -> ``(k,)`` intp indices (k >= 2)."""
    if bands is None:
        return np.arange(B, dtype=np.intp)
    idx = [_band_index(int(i), B, "selected band")
           for i in np.asarray(bands).ravel().tolist()]
    if len(idx) < 2:
        raise ValueError("%s must select at least 2 bands, got %d" % (name, len(idx)))
    if len(set(idx)) != len(idx):
        raise ValueError("%s repeats a band index (%r) — the selection must be unique"
                         % (name, idx))
    return np.asarray(idx, np.intp)


def spec_decorrelation_stretch(cube, bands=None, target_std=None) -> np.ndarray:
    """Decorrelation stretch (Gillespie, Kahle & Walker 1986) -> a cube of the
    **same shape**.

    Highly correlated bands (the normal case in remote sensing: everything is
    dominated by overall brightness) produce a cigar-shaped, nearly 1-D cloud in
    band space, so a plain per-band contrast stretch cannot open it up. DCS rotates
    the cloud onto its principal axes, stretches **each axis** to a common target
    standard deviation, and rotates back — colour/spectral differences become
    visible while the axes of the original band space, and each band's mean, are
    preserved.

    Concretely, with the band covariance ``S = V diag(L) V^T`` the transform is the
    symmetric matrix ``T = V diag(g) V^T``, ``g_i = target_std / sqrt(L_i)``, applied
    to the mean-centred spectra and re-centred on the original means. The output
    covariance is then exactly ``target_std**2 * I`` — **all** band-to-band
    correlation is removed — which is what the unit test asserts.

    * *bands* — optional subset of band indices (>= 2, unique) to stretch. The
      remaining bands are copied through **bit-identically**, so the result always
      has the cube's shape. ``None`` (default) stretches every band.
    * *target_std* — the common per-axis standard deviation. ``None`` (default) uses
      the mean of the selected bands' own standard deviations, which keeps the
      output at the input's overall contrast scale rather than at an arbitrary one.

    Degenerate directions (variance <= 1e-12 of the largest, e.g. a cube whose bands
    are identical) carry no information and would be divided by ~0, so their gain is
    set to **0** instead: the result stays finite and NaN-free by construction. The
    output is not clipped to [0, 1]; a display stretch is the caller's business.
    """
    a = _as_cube(cube)
    H, W, B = a.shape
    idx = _select_bands(B, bands)
    k = int(idx.size)
    X = a[:, :, idx].reshape(-1, k)
    mean = X.mean(axis=0)
    Xc = X - mean
    cov = (Xc.T @ Xc) / max(X.shape[0] - 1, 1)           # (k, k), ddof=1
    evals, V = np.linalg.eigh(cov)
    evals = np.clip(evals, 0.0, None)                    # PSD; kill round-off negatives

    if target_std is None:
        s = float(np.mean(np.sqrt(np.clip(np.diag(cov), 0.0, None))))
        if not np.isfinite(s) or s <= 0.0:
            s = 1.0                                      # a constant cube: no scale to keep
    else:
        s = float(target_std)
        if not np.isfinite(s) or s <= 0.0:
            raise ValueError("target_std must be a finite value > 0, got %r" % (target_std,))

    tol = float(np.max(evals)) * 1e-12
    good = evals > tol
    gains = np.where(good, s / np.sqrt(np.where(good, evals, 1.0)), 0.0)
    T = (V * gains) @ V.T                                # V diag(g) V^T, symmetric
    out = a.copy()
    out[:, :, idx] = (Xc @ T + mean).reshape(H, W, k)
    return _finite_or_raise(out, "spec_decorrelation_stretch")


def _as_stack(images, name: str = "images") -> np.ndarray:
    """Coerce a list of ``(H, W)`` images (or an ``(H, W, K)`` array) to ``(H, W, K)``.

    Note the deliberate difference from :func:`_as_cube`: the argument here is a
    *stack of co-registered single-band sources*, not a spectral cube, so an
    ``(H, W, 3)`` array is accepted and read as three sources (fusing the channels of
    an RGB frame is a meaningful request, not a modality error). Pass a **list** of
    2-D images for the unambiguous form.
    """
    if isinstance(images, np.ndarray):
        S = np.asarray(images, np.float64)
        if S.ndim != 3:
            raise ValueError(
                "%s as an array must be (H, W, K) — a stack of K co-registered images; "
                "got a %d-D array of shape %r (pass [img] for a single source)"
                % (name, S.ndim, S.shape))
    else:
        try:
            items = list(images)
        except TypeError:
            raise ValueError("%s must be a sequence of (H, W) images or an (H, W, K) "
                             "array, got %r" % (name, type(images).__name__)) from None
        if not items:
            raise ValueError("%s is empty — need at least one source image" % name)
        arrs = []
        for i, im in enumerate(items):
            b = np.asarray(im, np.float64)
            if b.ndim != 2:
                raise ValueError("%s[%d] must be a 2-D (H, W) image, got shape %r"
                                 % (name, i, b.shape))
            arrs.append(b)
        for i, b in enumerate(arrs):
            if b.shape != arrs[0].shape:
                raise ValueError("%s[%d] has shape %r but %s[0] has %r — the sources must "
                                 "be co-registered onto one grid"
                                 % (name, i, b.shape, name, arrs[0].shape))
        S = np.stack(arrs, axis=-1)
    if min(S.shape[0], S.shape[1]) < 1 or S.shape[2] < 1:
        raise ValueError("%s must hold at least one non-empty (H, W) image, got shape %r"
                         % (name, S.shape))
    if not np.isfinite(S).all():
        raise ValueError("%s contains non-finite values (NaN/Inf)" % name)
    return S


def spec_fuse(images, method: str = "pca", detail_size: int = 3) -> np.ndarray:
    """Fuse a stack of co-registered single-band images into one ``image`` ``(H, W)``.

    *images* is a list of ``(H, W)`` arrays or an ``(H, W, K)`` stack (multi-sensor,
    multi-exposure or multi-focus frames of the same scene). Rules:

    * ``"pca"`` (default) — pixel-level PCA fusion (Naidu & Raol 2008): treat each
      source as a variable and the pixels as observations, take the first principal
      component of the ``(K, K)`` source covariance and use its loadings, normalised
      to sum to one, as the fusion weights. Weighting by PC1 gives the most mutually
      consistent (highest-variance) combination rather than a flat average. The
      sum-normalisation makes the weights independent of the eigenvector's arbitrary
      sign, so identical sources fuse back to exactly that image.
    * ``"average"`` — the plain per-pixel mean, the honest baseline.
    * ``"max_abs_detail"`` — *choose-max activity* multi-focus fusion (the selection
      rule of Burt & Adelson 1983 / Li et al. 1995, here at a single scale): the
      high-pass residual ``|src - boxmean(src, detail_size)|`` measures local
      activity, and each pixel is taken from whichever source is sharpest there
      (ties -> the lowest source index, so the choice is deterministic).

    *detail_size* is the odd box-filter width of the ``max_abs_detail`` high pass.
    Returns float64 ``(H, W)`` on the sources' own radiometric scale (not rescaled
    to [0, 1]), verified finite. Fail-closed on ragged/empty/non-finite input.
    """
    S = _as_stack(images)
    H, W, K = S.shape
    m = str(method).strip().lower()
    if m not in FUSE_METHODS:
        raise ValueError("method %r is not one of %s" % (method, FUSE_METHODS))

    if m == "average":
        return _finite_or_raise(S.mean(axis=2), "spec_fuse('average')")

    if m == "pca":
        X = S.reshape(-1, K)
        Xc = X - X.mean(axis=0)
        cov = (Xc.T @ Xc) / max(X.shape[0] - 1, 1)       # (K, K)
        evals, V = np.linalg.eigh(cov)
        v = V[:, int(np.argmax(evals))]                  # PC1 loadings, sign arbitrary
        total = float(v.sum())
        # w = v / sum(v) is sign-invariant and sums to 1. But when the loadings
        # nearly cancel (near-anti-correlated sources) sum(v) -> 0 and the weights
        # blow up, throwing the fused pixel far outside the source hull. Guard
        # RELATIVELY (not just against exact zero) against that ill-conditioning
        # and fall back to the flat average, which is the documented degenerate rule.
        if abs(total) > 1e-3 * (float(np.abs(v).sum()) + _EPS):
            w = v / total
        else:
            w = np.full(K, 1.0 / K, np.float64)
        return _finite_or_raise((S * w).sum(axis=2), "spec_fuse('pca')")

    n = int(detail_size)
    if n < 3 or n % 2 == 0:
        raise ValueError("detail_size must be an odd integer >= 3, got %r" % (detail_size,))
    from scipy import ndimage

    detail = np.empty_like(S)
    for i in range(K):
        low = ndimage.uniform_filter(S[:, :, i], size=n, mode="nearest")
        detail[:, :, i] = np.abs(S[:, :, i] - low)
    pick = np.argmax(detail, axis=2)                     # ties -> lowest index
    fused = np.take_along_axis(S, pick[:, :, None], axis=2)[:, :, 0]
    return _finite_or_raise(np.ascontiguousarray(fused), "spec_fuse('max_abs_detail')")


#: Introspectable list of the spectral operations this module exposes.
SPECTRALOPS = (
    "read_envi", "write_envi",
    "spec_band", "spec_rgb_composite", "spec_nearest_band",
    "spec_band_ratio", "spec_index",
    "spec_angle_mapper",
    "spec_pca", "spec_mnf",
    "spec_unmix", "spec_endmembers_ppi",
    "spec_continuum_removal",
    "spec_pansharpen", "spec_decorrelation_stretch", "spec_fuse",
)
