"""First-class complex-image capability (numpy + scipy only).

The data type behind FFT-domain filtering, holography, optical coherence
tomography (OCT), synthetic-aperture radar (SAR) and MRI *k*-space is the
**complex field** — a 2-D ``complex128`` array carrying a magnitude *and* a
phase per pixel. Fullseye's evolvable operator set (``ops.py``) already reaches
the frequency domain (``lowpass`` / ``highpass`` via :func:`numpy.fft.fft2`), but
every one of those ops calls ``np.real(np.fft.ifft2(...))`` immediately, so the
complex field is created and destroyed inside a single expression and **never
escapes** as data an application can inspect, filter, or unwrap. This module
fills that gap: it makes the complex field a *thing you can hold* and surfaces
the operators that only make sense on it — decomposition (magnitude / phase /
real / imag / log-spectrum), recomposition, transfer-function filtering that
preserves the complex result, frequency-domain Wiener deconvolution, and — the
differentiator — **2-D phase unwrapping**.

Why this widens Fullseye beyond HALCON: HALCON ships ``fft_image`` /
``fft_image_inv`` / ``complex_to_real`` / ``real_to_complex`` and can *extract*
wrapped phase (``phase_rad`` / ``phase_deg``), but it has **no phase-unwrapping
operator at all** (verified against the HALCON operator corpus: zero ``unwrap``
operators). Wrapped phase is ambiguous modulo 2*pi; the metric quantity an
interferogram / InSAR / OCT / MRI-field-map measures is the *continuous* phase,
which only unwrapping recovers. :func:`phase_unwrap` implements the Herraez
quality-guided path-following algorithm, which HALCON users must leave the tool
to obtain.

These are **plain module functions** surfaced through the ``fullseye`` facade
(exactly like :mod:`stereo` / :mod:`pointcloud` / :mod:`volops`); they are kept
deliberately *out* of the evolution op registry (:mod:`ops`) — the numpy core
and the evolutionary search stay untouched. :mod:`numpy.fft` is the engine; no
new third-party dependency is introduced.

Conventions
-----------
* An **image** is a real ``(H, W)`` ``float64`` array (the shared Fullseye sort).
  The bridging ops (:func:`cx_magnitude`, :func:`cx_real`, :func:`cx_imag`)
  return an image-shaped real field but do **not** clamp it to ``[0, 1]``: a
  magnitude / real part is a *metric* quantity that routinely exceeds one (the
  DC term of a spectrum is huge). Use :func:`cx_log_magnitude` or
  ``imgio.normalize`` for a displayable view. :func:`cx_phase` is the one
  bridge whose default output *is* a ``[0, 1]`` display image (documented below).
* A **complex field** / **spectrum** is a ``(H, W)`` ``complex128`` array.
  :func:`cx_fft` returns it *centred* (DC at the array centre via
  :func:`numpy.fft.fftshift`), matching how spectra are displayed and how the
  ``H`` transfer functions in this module are laid out; :func:`cx_ifft` un-shifts
  before inverting.
* **Real input to a complex-only op is FFT'd, not rejected** (documented
  convenience): passing a real image to :func:`cx_magnitude` / :func:`cx_phase`
  / :func:`cx_log_magnitude` / :func:`cx_apply_transfer_function` / :func:`cx_ifft`
  interprets it as a spatial image and takes its centred FFT first, so
  ``cx_magnitude(image)`` yields the magnitude spectrum. A genuine complex field
  is used as-is.

Honest limits (see the individual docstrings)
--------------------------------------------
* :func:`phase_unwrap` assumes moderate noise and connected support. It is exact
  (up to a global constant) only where the true phase gradient stays below
  pi/pixel; steeper gradients and dense phase residues still alias — no
  path-following unwrapper can invent information the sampling threw away.
* :func:`cx_wiener_deconvolve` is a *linear* inverse: it needs an estimated
  noise-to-signal ratio and a known / estimated PSF, and it rings at strong
  edges. It does not deblur beyond what the (noisy) measurement supports.

Provenance (public papers)
--------------------------
* **Herraez unwrapping** — M. A. Herraez, D. R. Burton, M. J. Lalor, M. A.
  Gdeisat, "Fast two-dimensional phase-unwrapping algorithm based on sorting by
  reliability following a noncontinuous path", *Applied Optics* 41(35),
  7437-7444 (2002).
* **Goldstein branch-cut unwrapping** (documented alternative) — R. M. Goldstein,
  H. A. Zebker, C. L. Werner, "Satellite radar interferometry: Two-dimensional
  phase unwrapping", *Radio Science* 23(4), 713-720 (1988).
* **Wiener deconvolution** — N. Wiener, *Extrapolation, Interpolation, and
  Smoothing of Stationary Time Series* (1949); frequency-domain form as in
  Gonzalez & Woods, *Digital Image Processing* (parametric Wiener filter).
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "cx_fft", "cx_ifft",
    "cx_magnitude", "cx_phase", "cx_real", "cx_imag", "cx_log_magnitude",
    "cx_from_mag_phase",
    "phase_unwrap",
    "cx_wiener_deconvolve",
    "cx_apply_transfer_function",
    "cx_bandpass",
    "COMPLEXOPS",
]

#: The public complex-image functions, by name (introspection / facade wiring).
#: These are the names to re-export through the ``fullseye`` facade.
COMPLEXOPS = [
    "cx_fft", "cx_ifft",
    "cx_magnitude", "cx_phase", "cx_real", "cx_imag", "cx_log_magnitude",
    "cx_from_mag_phase",
    "phase_unwrap",
    "cx_wiener_deconvolve",
    "cx_apply_transfer_function",
    "cx_bandpass",
]

_TWO_PI = 2.0 * np.pi


# --------------------------------------------------------------------------- #
# fail-closed input helpers                                                    #
# --------------------------------------------------------------------------- #
def _require_image(x, name: str = "image") -> np.ndarray:
    """Coerce to a real ``(H, W)`` float64 array or raise ``ValueError``.

    Rejects non-2-D input, complex input (a complex field belongs to the
    ``cx_*`` field ops, not here), and any NaN / Inf — a poisoned pixel would
    spread across the whole spectrum through the FFT and corrupt every output
    silently."""
    a = np.asarray(x)
    if np.iscomplexobj(a):
        raise ValueError("%s must be a real 2-D image, not a complex array — pass a "
                         "complex field to the cx_* field ops instead" % name)
    a = np.asarray(a, dtype=np.float64)
    if a.ndim != 2:
        raise ValueError("%s must be 2-D (H, W); got a %d-D array of shape %r"
                         % (name, a.ndim, tuple(np.shape(x))))
    if not np.isfinite(a).all():
        n = int((~np.isfinite(a)).sum())
        raise ValueError("%s has %d non-finite value(s) (NaN/Inf) — refusing" % (name, n))
    return a


def _as_field(x, name: str = "cx") -> np.ndarray:
    """Coerce to a ``(H, W)`` complex128 *centred spectrum* or raise ``ValueError``.

    A genuine complex array is validated (2-D, finite in both real and imaginary
    parts) and returned as ``complex128``. A **real** array is interpreted as a
    spatial image and replaced by its centred FFT (:func:`cx_fft`) — the
    documented convenience that lets ``cx_magnitude(image)`` mean *magnitude
    spectrum*. See the module docstring."""
    a = np.asarray(x)
    if a.ndim != 2:
        raise ValueError("%s must be 2-D (H, W); got a %d-D array of shape %r"
                         % (name, a.ndim, tuple(np.shape(x))))
    if np.iscomplexobj(a):
        a = np.asarray(a, dtype=np.complex128)
        if not np.isfinite(a).all():                 # np.isfinite on complex checks both parts
            n = int((~np.isfinite(a)).sum())
            raise ValueError("%s has %d non-finite entry/entries (NaN/Inf in the real or "
                             "imaginary part) — refusing" % (name, n))
        return a
    return cx_fft(a)                                  # real input -> centred spectrum (documented)


def _wrap(x: np.ndarray) -> np.ndarray:
    """Wrap radians into ``(-pi, pi]`` (the gamma operator of Herraez 2002)."""
    return x - _TWO_PI * np.round(x / _TWO_PI)


# --------------------------------------------------------------------------- #
# forward / inverse transform                                                  #
# --------------------------------------------------------------------------- #
def cx_fft(image) -> np.ndarray:
    """Centred 2-D FFT of a real image -> ``(H, W)`` complex128 spectrum.

    ``fftshift(fft2(image))`` — the DC component sits at the array centre, the
    layout used for display and for the ``H`` transfer functions consumed by
    :func:`cx_apply_transfer_function`. Invert with :func:`cx_ifft`."""
    v = _require_image(image)
    return np.fft.fftshift(np.fft.fft2(v))


def cx_ifft(cx, real: bool = True):
    """Inverse of :func:`cx_fft`: ``ifft2(ifftshift(cx))``.

    With ``real=True`` (default) the real part is returned as an image (the
    imaginary part is numerical dust for a spectrum that came from a real image);
    with ``real=False`` the full complex spatial field is returned (holography /
    coherent imaging, where the imaginary part carries signal). A real array is
    FFT'd first (module convenience), making ``cx_ifft`` an involution on it."""
    field = _as_field(cx)
    spatial = np.fft.ifft2(np.fft.ifftshift(field))
    if real:
        return np.real(spatial).astype(np.float64, copy=False)
    return spatial


# --------------------------------------------------------------------------- #
# complex -> image bridges                                                      #
# --------------------------------------------------------------------------- #
def cx_magnitude(cx) -> np.ndarray:
    """Per-pixel magnitude ``|cx|`` -> real ``(H, W)`` float64.

    **Raw / unnormalised** (not clamped to ``[0, 1]``): the magnitude is a metric
    quantity and, for a spectrum, spans many orders of magnitude. Pair it with
    :func:`cx_from_mag_phase` to reconstruct the field exactly, or with
    :func:`cx_log_magnitude` / ``imgio.normalize`` to view it."""
    return np.abs(_as_field(cx))


def cx_phase(cx, display: bool = True) -> np.ndarray:
    """Wrapped phase of ``cx`` -> real ``(H, W)`` float64.

    ``display=True`` (default) maps the wrapped phase ``angle(cx)`` in
    ``(-pi, pi]`` to ``[0, 1]`` for viewing, with **0.5 at zero phase**
    (``(angle + pi) / (2*pi)``: ``-pi -> 0``, ``0 -> 0.5``, ``+pi -> 1``).
    ``display=False`` returns the **raw wrapped radians** in ``(-pi, pi]`` — the
    quantity :func:`cx_from_mag_phase` and :func:`phase_unwrap` consume. Note the
    default output is *wrapped* and *display-scaled*; :func:`phase_unwrap` returns
    raw, continuous, un-scaled radians instead."""
    ph = np.angle(_as_field(cx))
    if display:
        return (ph + np.pi) / _TWO_PI
    return ph


def cx_real(cx) -> np.ndarray:
    """Real part of ``cx`` -> real ``(H, W)`` float64 (raw, not clamped)."""
    return np.real(_as_field(cx)).astype(np.float64, copy=False)


def cx_imag(cx) -> np.ndarray:
    """Imaginary part of ``cx`` -> real ``(H, W)`` float64 (raw, not clamped)."""
    return np.imag(_as_field(cx)).astype(np.float64, copy=False)


def cx_log_magnitude(cx) -> np.ndarray:
    """Log magnitude spectrum for **display** -> real ``(H, W)`` float64 in ``[0, 1]``.

    ``log1p(|cx|)`` (i.e. ``log(1 + |cx|)``, finite at zero) min-max normalised to
    ``[0, 1]``. This is the conventional way to see a spectrum whose linear
    magnitude is dominated by the DC spike. Display only — it is not invertible;
    use :func:`cx_magnitude` for the metric magnitude."""
    m = np.log1p(np.abs(_as_field(cx)))
    mx = float(m.max())
    return m / mx if mx > 0.0 else m


def cx_from_mag_phase(mag, phase) -> np.ndarray:
    """Recompose a complex field from a magnitude and a **radian** phase.

    ``mag * exp(1j * phase)`` -> ``(H, W)`` complex128. Both arguments are real
    ``(H, W)`` arrays of equal shape; *phase* is in radians (as returned by
    ``cx_phase(..., display=False)`` or :func:`phase_unwrap`, **not** the
    ``[0, 1]`` display scaling). This is the exact inverse of the
    :func:`cx_magnitude` / ``cx_phase(display=False)`` decomposition."""
    m = np.asarray(mag, dtype=np.float64)
    p = np.asarray(phase, dtype=np.float64)
    if m.ndim != 2 or p.ndim != 2:
        raise ValueError("mag and phase must both be 2-D (H, W); got %d-D and %d-D"
                         % (m.ndim, p.ndim))
    if m.shape != p.shape:
        raise ValueError("mag %r and phase %r must have the same shape" % (m.shape, p.shape))
    if not (np.isfinite(m).all() and np.isfinite(p).all()):
        raise ValueError("mag/phase contain non-finite values (NaN/Inf) — refusing")
    return m * np.exp(1j * p)


# --------------------------------------------------------------------------- #
# phase unwrapping — the differentiator                                        #
# --------------------------------------------------------------------------- #
def _herraez_reliability(phi: np.ndarray) -> np.ndarray:
    """Per-pixel reliability ``R = 1/D`` of Herraez 2002.

    ``D`` is the RMS of the four wrapped second differences (horizontal,
    vertical, and both diagonals) through each interior pixel; a small ``D``
    (smooth neighbourhood) is highly reliable. Border pixels get ``R = 0`` (least
    reliable) so the path grows from the interior outward."""
    g = _wrap
    R = np.zeros_like(phi)
    c = phi[1:-1, 1:-1]
    H = g(phi[1:-1, :-2] - c) - g(c - phi[1:-1, 2:])
    V = g(phi[:-2, 1:-1] - c) - g(c - phi[2:, 1:-1])
    D1 = g(phi[:-2, :-2] - c) - g(c - phi[2:, 2:])
    D2 = g(phi[:-2, 2:] - c) - g(c - phi[2:, :-2])
    D = np.sqrt(H * H + V * V + D1 * D1 + D2 * D2)
    R[1:-1, 1:-1] = 1.0 / np.maximum(D, 1e-12)        # floor D so a flat region stays finite
    return R


def _find(parent: np.ndarray, offset: np.ndarray, x: int):
    """Weighted union-find root of ``x`` with path compression.

    Returns ``(root, k)`` where ``k`` is the integer number of 2*pi increments
    from ``x`` up to the group root (so the unwrapped phase of ``x`` differs from
    the root's baseline by ``2*pi*k`` plus the wrapped values)."""
    # first pass: locate the root and accumulate the offset x -> root
    root = x
    acc = 0
    while parent[root] != root:
        acc += offset[root]
        root = parent[root]
    # second pass: compress the path, rewriting each offset to point at the root
    node = x
    cum = 0
    while parent[node] != root:
        nxt = parent[node]
        o = offset[node]
        parent[node] = root
        offset[node] = acc - cum
        cum += o
        node = nxt
    return root, acc


def phase_unwrap(wrapped, method: str = "herraez") -> np.ndarray:
    """2-D phase unwrapping: wrapped radians -> continuous (unwrapped) radians.

    Recovers the *continuous* phase surface from a wrapped phase array (values in
    ``(-pi, pi]``, e.g. ``np.angle(field)``). The output is ``float64`` and, by
    design, **not** clamped to ``[0, 1]`` — unwrapped phase is a *metric* quantity
    (an OCT / MRI field map, an InSAR fringe count, an interferometric surface)
    that spans as many radians as the scene demands. The result is defined only up
    to a global additive constant (the absolute fringe order is unobservable).

    Method
    ------
    ``method="herraez"`` (default, the only implemented method) is the
    quality-guided path-following algorithm of Herraez, Burton, Lalor & Gdeisat
    (Applied Optics 2002): rank every edge between neighbouring pixels by the
    combined *reliability* of its endpoints (the inverse of the local wrapped
    second-difference energy), then merge pixels highest-reliability-edge-first
    with a union-find, adding the 2*pi multiple that keeps each merged phase
    difference within ``(-pi, pi]``. Processing reliable (smooth) regions first
    routes the unwrap *around* noisy pixels and phase residues instead of through
    them — this is what makes it robust and deterministic without a smoothness
    model or iteration count.

    ``method="goldstein"`` (Goldstein, Zebker & Werner 1988) is a documented
    alternative — detect the +/-1 phase *residues* (loop integrals of the wrapped
    gradient), join opposite-sign residues with *branch cuts*, then flood-fill the
    phase without crossing a cut. It is **not implemented here** (it needs a
    residue-balancing / cut-placement heuristic that is a project in itself);
    requesting it raises ``ValueError`` rather than silently falling back.

    Honest limits
    -------------
    Unwrapping is only well-posed under the *Itoh condition*: the true phase must
    change by less than pi between adjacent pixels. Where it does, this returns the
    original surface up to a constant to ~1e-12 on a clean signal. Where it does
    **not** — steep gradients (> pi/pixel), or dense phase *residues* from strong
    noise, undersampling, or genuine discontinuities — the sampling has already
    lost the fringe order and *no* unwrapper can recover it: the result will alias
    (be off by a multiple of 2*pi) in and downstream of those regions. This
    implementation assumes moderate noise and connected support; it does not
    claim to unwrap a residue-dense or aliased map correctly.

    Parameters
    ----------
    wrapped : array_like
        A real ``(H, W)`` wrapped phase in radians. Values are wrapped into
        ``(-pi, pi]`` defensively on entry (idempotent for already-wrapped data).
    method : str
        ``"herraez"`` (default). ``"goldstein"`` and any other value raise
        ``ValueError``.

    Returns
    -------
    numpy.ndarray
        The continuous unwrapped phase, ``(H, W)`` float64, in radians (not
        clamped), equal to the input plus the recovered 2*pi field.
    """
    if method != "herraez":
        if method == "goldstein":
            raise ValueError(
                "method='goldstein' (branch-cut unwrapping, Goldstein et al. 1988) is "
                "documented but not implemented; use method='herraez'")
        raise ValueError("unknown method %r; only 'herraez' is implemented" % (method,))

    a = _require_image(wrapped, name="wrapped")
    if a.shape[0] < 1 or a.shape[1] < 1:
        raise ValueError("wrapped must be a non-empty 2-D array")
    phi = _wrap(a)                                     # defensive: guarantee (-pi, pi]
    Hh, Ww = phi.shape
    N = Hh * Ww

    # A 1x1 (or single-row/col) image has no interior and nothing to unwrap.
    if N <= 1 or Hh < 2 or Ww < 2:
        return phi.copy()

    R = _herraez_reliability(phi)
    flat_phi = phi.ravel()
    Rf = R.ravel()

    # Build the edge list: each interior/boundary 4-connected edge, with a
    # reliability = sum of its two endpoint reliabilities (Herraez).
    idx = np.arange(N).reshape(Hh, Ww)
    h_a = idx[:, :-1].ravel()                          # horizontal edges (j)-(j+1)
    h_b = idx[:, 1:].ravel()
    v_a = idx[:-1, :].ravel()                          # vertical edges (i)-(i+1)
    v_b = idx[1:, :].ravel()
    edge_a = np.concatenate([h_a, v_a])
    edge_b = np.concatenate([h_b, v_b])
    edge_rel = Rf[edge_a] + Rf[edge_b]

    order = np.argsort(-edge_rel, kind="stable")       # most reliable edge first
    edge_a = edge_a[order]
    edge_b = edge_b[order]

    parent = np.arange(N, dtype=np.int64)
    offset = np.zeros(N, dtype=np.int64)               # 2*pi increments node -> parent
    size = np.ones(N, dtype=np.int64)

    ea = edge_a.tolist()                               # python ints: fastest for the DSU loop
    eb = edge_b.tolist()
    fp = flat_phi
    inv_two_pi = 1.0 / _TWO_PI
    for a_i, b_i in zip(ea, eb):
        ra, oa = _find(parent, offset, a_i)
        rb, ob = _find(parent, offset, b_i)
        if ra == rb:
            continue
        # enforce inc(a) - inc(b) = M so the merged phase diff lands in (-pi, pi]
        M = int(round((fp[b_i] - fp[a_i]) * inv_two_pi))
        if size[ra] >= size[rb]:
            parent[rb] = ra
            offset[rb] = oa - ob - M
            size[ra] += size[rb]
        else:
            parent[ra] = rb
            offset[ra] = ob - oa + M
            size[rb] += size[ra]

    # Read back each pixel's total 2*pi increment relative to its group root.
    inc = np.empty(N, dtype=np.int64)
    for i in range(N):
        _, k = _find(parent, offset, i)
        inc[i] = k
    return (fp + _TWO_PI * inc.astype(np.float64)).reshape(Hh, Ww)


# --------------------------------------------------------------------------- #
# frequency-domain restoration / filtering                                     #
# --------------------------------------------------------------------------- #
def cx_wiener_deconvolve(image, psf, nsr: float = 0.01) -> np.ndarray:
    """Frequency-domain Wiener deconvolution -> restored image ``(H, W)`` in ``[0, 1]``.

    Given a blurred (and noisy) *image* and the *psf* (point-spread function) that
    blurred it, estimate the original by the parametric Wiener filter

        ``F_hat = conj(H) / (|H|^2 + nsr) * G``

    where ``G = FFT(image)``, ``H = FFT(psf)`` (the PSF normalised to unit sum and
    centred at the origin), and ``nsr`` is the (constant) noise-to-signal power
    ratio (Gonzalez & Woods). The restored image is returned clipped to ``[0, 1]``.

    This is a **linear inverse** and behaves like one: it needs the PSF (known or
    estimated) and a sensible ``nsr`` (too small amplifies noise, too large leaves
    the image blurred), and it produces Gibbs *ringing* near strong edges. It
    cannot recover detail the blur + noise destroyed. The convolution model is
    circular (FFT), so a non-circular blur leaves mild wrap-around error at the
    borders.

    Parameters
    ----------
    image : array_like
        Real ``(H, W)`` blurred image.
    psf : array_like
        Real ``(h, w)`` point-spread function, ``h <= H`` and ``w <= W``, with a
        non-zero sum. It is normalised to sum 1 (unit DC gain) internally.
    nsr : float
        Noise-to-signal power ratio, strictly ``> 0``.
    """
    v = _require_image(image)
    p = np.asarray(psf)
    if np.iscomplexobj(p):
        raise ValueError("psf must be real, not complex")
    p = np.asarray(p, dtype=np.float64)
    if p.ndim != 2:
        raise ValueError("psf must be 2-D (h, w); got a %d-D array of shape %r"
                         % (p.ndim, tuple(np.shape(psf))))
    if not np.isfinite(p).all():
        raise ValueError("psf has non-finite values (NaN/Inf) — refusing")
    if p.shape[0] > v.shape[0] or p.shape[1] > v.shape[1]:
        raise ValueError("psf %r is larger than the image %r" % (p.shape, v.shape))
    s = float(p.sum())
    if abs(s) < 1e-12:
        raise ValueError("psf must have a non-zero sum (it defines the blur's DC gain); "
                         "got sum=%g" % s)
    if not (float(nsr) > 0.0):
        raise ValueError("nsr must be > 0 (the noise-to-signal power ratio); got %r" % (nsr,))
    p = p / s                                          # unit-sum PSF -> DC gain 1

    # Embed the PSF in an image-sized frame and roll its centre to the origin so
    # H = fft2(pad) is a zero-shift blur that matches G's (uncentred) convention.
    pad = np.zeros_like(v)
    ph, pw = p.shape
    pad[:ph, :pw] = p
    pad = np.roll(pad, (-(ph // 2), -(pw // 2)), axis=(0, 1))

    Hf = np.fft.fft2(pad)
    G = np.fft.fft2(v)
    Wf = np.conj(Hf) / (np.abs(Hf) ** 2 + float(nsr))
    out = np.real(np.fft.ifft2(Wf * G))
    return np.clip(out, 0.0, 1.0)


def cx_apply_transfer_function(cx, H) -> np.ndarray:
    """Multiply a **centred** spectrum by a filter ``H`` -> ``(H, W)`` complex128.

    The honest primitive under ``ops.lowpass`` / ``ops.highpass``, but
    **complex-preserving**: the filtered spectrum is returned as a complex field
    (not immediately inverted and real-cast), so it can be chained, inspected, or
    handed to :func:`cx_ifft`. ``H`` is a same-shape transfer function laid out in
    the *centred* convention of :func:`cx_fft` (DC at the centre); it may be real
    (a magnitude mask) or complex (a phase-shifting filter). A real ``cx`` is
    FFT'd first (module convenience)."""
    field = _as_field(cx)
    Hh = np.asarray(H)
    if Hh.ndim != 2:
        raise ValueError("H must be 2-D (H, W); got a %d-D array of shape %r"
                         % (Hh.ndim, tuple(np.shape(H))))
    if Hh.shape != field.shape:
        raise ValueError("H %r must match the spectrum shape %r" % (Hh.shape, field.shape))
    if not np.isfinite(Hh).all():
        raise ValueError("H has non-finite values (NaN/Inf) — refusing")
    return (field * Hh.astype(np.complex128)).astype(np.complex128, copy=False)


def cx_bandpass(image, low: float, high: float) -> np.ndarray:
    """Ideal annulus band-pass in the frequency domain -> image ``(H, W)`` in ``[0, 1]``.

    Convenience wrapper: FFT the image, keep only the centred spectrum ring with
    radial frequency in ``[low, high]`` (an ideal annular mask), invert, and
    min-max normalise the real result to ``[0, 1]`` for display. Frequencies are
    normalised (cycles/pixel, as from :func:`numpy.fft.fftfreq`): ``0`` is DC and
    the reachable maximum is ~``0.707`` (the array corner). ``low`` isolates
    structure coarser than ``1/low`` px; ``high`` drops finer detail / noise.

    Being *ideal* (a hard ring), it exhibits ringing; a Gaussian-edged annulus is
    smoother but this keeps the primitive simple. Built on
    :func:`cx_apply_transfer_function`, so the complex field really is created and
    filtered (unlike the evolvable ``lowpass`` / ``highpass`` ops, which never let
    it escape)."""
    v = _require_image(image)
    lo, hi = float(low), float(high)
    if not (0.0 <= lo < hi):
        raise ValueError("require 0 <= low < high (normalised cycles/pixel); got low=%r high=%r"
                         % (low, high))
    cx = cx_fft(v)
    Hh, Ww = v.shape
    fy = np.fft.fftshift(np.fft.fftfreq(Hh))
    fx = np.fft.fftshift(np.fft.fftfreq(Ww))
    rad = np.sqrt(fy[:, None] ** 2 + fx[None, :] ** 2)
    mask = ((rad >= lo) & (rad <= hi)).astype(np.float64)
    filtered = cx_apply_transfer_function(cx, mask)
    out = cx_ifft(filtered, real=True)
    lo_v, hi_v = float(out.min()), float(out.max())
    if hi_v <= lo_v:
        return np.zeros_like(out)
    return (out - lo_v) / (hi_v - lo_v)
