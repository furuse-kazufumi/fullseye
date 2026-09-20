# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Fly optic-lobe vision pathway — hexagonal sampling, motion, looming (numpy + scipy only).

The insect visual system is a working, measured answer to a hard question this
library keeps meeting from the *design* side (:mod:`optics` / :mod:`visiondesign`)
but never from the *processing* side: given a wide-field, low-resolution eye and a
few neurons, how do you get robust motion, a time-to-collision, and a heading
out of it? This module is that processing pathway written as composable operators,
each one a closed-form textbook model with an exact identity to check it against
rather than a trained network.

Seven families of operator, in the order the light flows through them:

  * **lattice** — :func:`fly_hex_lattice`: the eye's geometry. A hexagonal grid of
    ommatidia (``n = 3*radius*(radius+1)+1`` of them), each an azimuth/elevation
    and a unit viewing direction in body coordinates (x forward, y left, z up).
    Two geometries: a regular hexagon (isotropic inter-ommatidial angle) and a
    ``"boxeye"`` distortion in which the diagonal neighbour is 1.118x farther than
    the axial one — the pixel-grid distortion of the connectome-derived visual
    models (Lappalainen et al., *Nature* 634:1132, 2024).
  * **stimulus** — :func:`fly_sky_1f`: a synthetic equirectangular sky panorama
    with a graded backlight and a 1/f azimuthal texture confined to an elevation
    band, so the sampling and motion operators have a controlled input whose
    spectrum is known.
  * **sample** — :func:`fly_hex_resample`: a pinhole image seen through the eye.
    Each ommatidium integrates the image under a Gaussian acceptance function of
    FWHM ``drho_deg`` weighted by the pixel solid angle, which is a spatial
    low-pass whose modulation transfer is the analytic
    ``exp(-pi^2 drho^2 nu^2 / (4 ln2))`` — measured below and pinned in the tests.
  * **motion** — :func:`fly_emd_response`: the Hassenstein-Reichardt correlator,
    the elementary motion detector. Its steady-state mean response to a drifting
    grating is ``dI^2 * sin(2 pi dphi/lambda) * omega tau/(1+(omega tau)^2)`` — zero
    when the spatial wavelength is twice the sample spacing, and peaked at
    ``f = 1/(2 pi tau)`` regardless of wavelength.
  * **looming** — :func:`fly_lgmd_eta` and :func:`fly_tau_from_expansion`: the two
    ways to read an approach out of an expanding angle. The LGMD/eta model
    ``eta = theta'*exp(-alpha*theta)`` peaks ``alpha*l/|v| - delay`` before
    collision, at an angular size of exactly ``2*atan(1/alpha)`` (24.0 degrees for
    ``alpha=4.7``; Gabbiani, Krapp & Laurent, *J. Neurosci.* 19:1122, 1999). The
    expansion-ratio model returns the time-to-contact directly, and it exists to
    make one silent trap explicit — the disk and sphere formulas differ by 33% at
    a 60-degree subtense, so picking the wrong object model quietly mis-times a
    landing.
  * **integrate** — :func:`fly_hs_readout`: the wide-field opponent readout of the
    horizontal system, summing preferred against anti-preferred motion detectors
    over the upper visual field only, because the ground flow of forward motion
    exceeds the detectors' bandwidth (measured below).
  * **tuning** — :func:`fly_dsi`: the direction-selectivity index and preferred
    direction from a set of responses at known stimulus angles, a vector sum on
    the circle.

Measured — the four closed-form identities the tests are built on
(``tests/test_flyvision.py``):

    quantity                        analytic / measured
    resample MTF, lambda = 15 deg   0.3424   (exp(-pi^2 drho^2/(4 ln2 lambda^2)))
    resample MTF, lambda = 25 deg   0.6799
    resample MTF, lambda = 40 deg   0.8601
    resample MTF, lambda = 80 deg   0.9630
    HR mean response (see test)     matches dI^2 sin(psi) omega tau/(1+(omega tau)^2)
    LGMD peak angle (alpha = 4.7)   24.0 deg  (= 2 atan(1/alpha))
    LGMD peak lead time             alpha*l/|v| - delay
    1/f sky power-spectrum slope    -2 +- 0.4 (log-log azimuth regression)
    boxeye diagonal/axial spacing   1.118

Provenance — textbook and cited public literature only (see ``docs/PROVENANCE.md``):

  * B. Hassenstein & W. Reichardt, "Systemtheoretische Analyse der Zeit-,
    Reihenfolgen- und Vorzeichenauswertung ...", *Z. Naturforsch.* 11b:513, 1956 —
    the correlation-type elementary motion detector.
  * K. Hausen, "Motion sensitive interneurons in the optomotor system of the fly",
    *Biol. Cybern.* 45:143, 1982 — the horizontal-system wide-field integration.
  * F. Gabbiani, H. G. Krapp & G. Laurent, "Computation of object approach by a
    wide-field, motion-sensitive neuron", *J. Neurosci.* 19:1122, 1999 — the
    ``eta = theta'*exp(-alpha*theta)`` model and its ``2 atan(1/alpha)`` peak.
  * D. N. Lee, "A theory of visual control of braking based on information about
    time-to-collision", *Perception* 5:437, 1976 — tau from optical expansion.
  * H. G. Krapp & R. Hengstenberg, "Estimation of self-motion by optic flow
    processing in a single visual interneuron", *Nature* 384:463, 1996 — matched
    filters and why the readout is a directional field over the eye.
  * J. K. Lappalainen et al., "Connectome-constrained networks predict neural
    activity across the fly visual system", *Nature* 634:1132, 2024 — the
    hexagonal photoreceptor lattice and its ``boxeye`` pixel distortion.

Units are in every parameter name — ``_deg`` / ``_s`` / ``_rad`` — because an
angle mixed between degrees and radians, or a time between seconds and
milliseconds, is a plausible-wrong number rather than a crash. ``float("4.63")``
succeeds, so strings, bools and complex numbers are rejected explicitly.

Deliberately **not** here (owned elsewhere — imported and composed, never
re-implemented):

  * **Optical-flow-based ego-motion** is :mod:`sceneflow`. Its
    ``time_to_contact`` / ``looming`` / ``focus_of_expansion`` / ``flow_divergence``
    read the approach and the heading from a **dense flow field** (a per-pixel
    ``(u, v)``); :func:`fly_tau_from_expansion` reads a time-to-contact from a
    **single expanding angle** (``theta(t)``), which is what a wide-field looming
    detector actually has and what a fly does not compute a dense flow to get.
    They are two inputs to the same quantity and this module never recomputes the
    flow-field one.
  * **Generic 1-D filtering / spectra** are :mod:`dsp` and :mod:`funct1d`; an
    ommatidial time series is a plain 1-D float64 array and those ops apply to it
    directly, so they are not re-wrapped. :func:`fly_emd_response` is the one thing
    they are not: an *opponent product of two low-passed channels*, which is a
    motion model, not a filter.
  * **Camera projection and rectification** are :mod:`camera` / :mod:`calib`.
    :func:`fly_hex_resample` uses the vertical-FOV pinhole convention
    (``fov_deg`` is the full vertical field, as in common physics simulators'
    ``fovy``) but does not duplicate their intrinsics/extrinsics machinery — the
    optical axis is simply the lattice centre.

Honest disclosure — what these operators cannot do, measured rather than assumed:

  * **One object per looming trace.** :func:`fly_lgmd_eta` and
    :func:`fly_tau_from_expansion` model a *single* expanding contour. Two objects
    approaching at once produce one ``theta(t)`` that is neither, and nothing here
    separates them — that is a segmentation problem upstream.
  * **The object model is an input, not a measurement.**
    :func:`fly_tau_from_expansion`'s ``shape`` is yours to state, and the disk and
    sphere formulas differ by 33% at a 60-degree subtense with nothing in the
    angle to say which is right. The wrong choice mis-times a landing and the
    operator cannot know.
  * **Resample MTF is a small-footprint approximation.** The
    ``exp(-pi^2 drho^2 nu^2/(4 ln2))`` transfer is the marginal of the 2-D
    Gaussian acceptance and holds where the acceptance footprint is small enough
    that azimuth is locally linear and the sphere locally flat — i.e. near the
    equator and the optical axis. Far off-axis, curvature of the equirectangular
    grid adds error the test does not claim away.
  * **The HR detector reports contrast-weighted motion, not velocity.** Its mean
    scales with ``dI^2``, so a low-contrast fast edge and a high-contrast slow one
    can read the same. That is a property of the correlation model, not a bug, and
    :func:`fly_hs_readout` inherits it.

Fail-closed, like every Fullseye module. A resample onto a lattice that reaches
outside the image, a wide-field readout with no ommatidia above the horizon, a
direction set whose angles do not match the responses, a non-monotone expansion
handed to a time-to-contact, a NaN, an array over the element cap — all raise an
explicit ``ValueError`` naming the problem. The expansion-ratio operator is the
one place a non-finite is a **documented return** rather than a refusal: a
non-expanding angle (``theta' <= 0``) has no time-to-contact, and returning
``NaN`` there is the honest answer (an approaching object that stopped is not
about to hit you), so that operator returns ``NaN`` per sample instead of raising.
"""
from __future__ import annotations

import functools

import numpy as np

__all__ = [
    "fly_hex_lattice", "fly_hex_resample", "fly_hex_quantize",
    "fly_emd_response",
    "fly_lgmd_eta", "fly_tau_from_expansion",
    "fly_hs_readout", "fly_sky_1f", "fly_dsi",
    "FLYVISION", "GEOMETRIES", "LN2", "QUANTIZE_MODES",
    "MAX_LATTICE_RADIUS", "MAX_IMAGE_DIM", "MAX_SIGNAL_POINTS",
    "MAX_RESAMPLE_ELEMENTS",
]

#: The public operators, by name (introspection / facade wiring).
FLYVISION = [
    "fly_hex_lattice", "fly_hex_resample", "fly_hex_quantize",
    "fly_emd_response",
    "fly_lgmd_eta", "fly_tau_from_expansion",
    "fly_hs_readout", "fly_sky_1f", "fly_dsi",
]

#: Lattice geometries accepted by :func:`fly_hex_lattice`.
GEOMETRIES = ("regular", "boxeye")

LN2 = float(np.log(2.0))

#: Largest hexagon radius. radius 60 is already 3*60*61+1 = 10981 ommatidia; the
#: cap only stops a mistyped value from allocating an eye no fly has.
MAX_LATTICE_RADIUS = 60

#: Largest side of a panorama / pinhole image (per axis).
MAX_IMAGE_DIM = 8192

#: Largest number of samples in a 1-D signal handed to a motion / looming op.
MAX_SIGNAL_POINTS = 1 << 22

#: Largest ``n_ommatidia * n_pixels`` for the dense resample weight matrix. The
#: matrix is float64, so 2^24 elements is ~0.13 GB; a lattice of 721 onto a
#: 256x256 image is 47M and over the cap, which is intended — a wide-field eye at
#: full camera resolution wants the sparse route this module does not ship.
#: ★ The cap is on the *product*, not on either factor, because the accident it
#: prevents is the cross term: a modest 900-ommatidium eye and a modest 512x512
#: image are each unremarkable and together are 236M float64 = 1.9 GB.
MAX_RESAMPLE_ELEMENTS = 1 << 24


# --------------------------------------------------------------------------- #
# fail-closed input helpers (same discipline as interferometry / photoncount)  #
# --------------------------------------------------------------------------- #
def _finite_scalar(v, name: str) -> float:
    """A real, finite Python float — or ``ValueError`` naming the problem."""
    if np.ma.is_masked(v):
        raise ValueError("%s is a masked value — fill or drop it explicitly"
                         % (name,))
    if isinstance(v, (complex, np.complexfloating)):
        raise ValueError("%s is complex — an angle / time is a real quantity; "
                         "coercion would silently drop the imaginary part"
                         % (name,))
    if isinstance(v, (bool, np.bool_)):
        raise ValueError("%s is a bool — refusing the silent True==1 promotion "
                         "(True deg is not an angle)" % (name,))
    if isinstance(v, (str, bytes, np.str_, np.bytes_)):
        raise ValueError("%s is a string (%r) — an angle must be a number; "
                         "float('4.63') would silently succeed and hide an "
                         "unparsed configuration value" % (name, v))
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s must be a real scalar, got %r"
                         % (name, type(v).__name__)) from None
    if not np.isfinite(f):
        raise ValueError("%s must be finite, got %r (NaN/Inf would propagate "
                         "through every direction)" % (name, v))
    return f


def _positive(v, name: str) -> float:
    f = _finite_scalar(v, name)
    if f <= 0.0:
        raise ValueError("%s must be > 0, got %g" % (name, f))
    return f


def _nonneg(v, name: str) -> float:
    f = _finite_scalar(v, name)
    if f < 0.0:
        raise ValueError("%s must be >= 0, got %g" % (name, f))
    return f


def _count(v, name: str, lo: int, hi: int) -> int:
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer)):
        raise ValueError("%s must be an int, got %r (a fractional count is an "
                         "input mistake, not something to round)"
                         % (name, type(v).__name__))
    n = int(v)
    if n < lo or n > hi:
        raise ValueError("%s must be in [%d, %d], got %d (the cap stops a "
                         "mistyped value from allocating gigabytes)"
                         % (name, lo, hi, n))
    return n


def _seed(v, name: str = "seed") -> int:
    """A non-negative integer seed. There is no ``None`` — determinism is a
    contract here (the chain fuzzer rejects non-deterministic ops)."""
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer)):
        raise ValueError("%s must be a non-negative int (determinism is a "
                         "contract in this module — there is no seed=None), "
                         "got %r" % (name, type(v).__name__))
    n = int(v)
    if n < 0:
        raise ValueError("%s must be >= 0, got %d" % (name, n))
    return n


def _bool(v, name: str) -> bool:
    if not isinstance(v, (bool, np.bool_)):
        raise ValueError("%s must be a bool, got %r (a truthy string or a 0/1 "
                         "int would hide a mis-wired flag)"
                         % (name, type(v).__name__))
    return bool(v)


def _one_of(v, name: str, choices, op: str) -> str:
    if not isinstance(v, str):
        raise ValueError("%s: %s must be one of %r, got %r"
                         % (op, name, list(choices), type(v).__name__))
    if v not in choices:
        raise ValueError("%s: %s must be one of %r, got %r"
                         % (op, name, list(choices), v))
    return v


def _size_of(a) -> int:
    """Element count of *a* without promoting it to float64 first."""
    shp = getattr(a, "shape", None)
    if shp is None:
        shp = np.shape(a)
    n = 1
    for d in shp:
        n *= int(d)
    return n if shp else 1


def _as_float_array(a, name: str, cap: int, op: str) -> np.ndarray:
    """Coerce to float64 — after the size cap, and refusing the silent-truncation
    traps (masked arrays, complex, non-finite, string/object/bool dtypes)."""
    if np.ma.is_masked(a):
        raise ValueError("%s: %s is a masked array with masked (invalid) entries "
                         "— fill or drop them explicitly" % (op, name))
    if isinstance(a, (str, bytes)):
        raise ValueError("%s: %s is a string — expected an array of numbers"
                         % (op, name))
    n = _size_of(a)
    if n > cap:
        raise ValueError(
            "%s: %s has %d elements (shape %r), over the %d cap — refusing "
            "before the float64 promotion, which would already have allocated "
            "~%d MB" % (op, name, n, tuple(np.shape(a)), cap, n * 8 // (1 << 20)))
    if np.iscomplexobj(a):
        raise ValueError("%s: %s is complex — coercion to float64 would silently "
                         "discard the imaginary part; take .real explicitly if "
                         "that is what you mean" % (op, name))
    kind = getattr(getattr(a, "dtype", None), "kind", None)
    if kind is None and not isinstance(a, (int, float, np.number)):
        kind = np.asarray(a).dtype.kind if not isinstance(a, np.ndarray) else None
    if kind in ("U", "S", "O", "V", "b"):
        raise ValueError(
            "%s: %s has dtype '%s' — numpy would happily parse it into float64, "
            "which is how an unparsed string, an object array of Decimals, or a "
            "bool mask becomes a measurement. Convert it yourself and state what "
            "you meant." % (op, name, np.dtype(kind if kind != "b" else "bool").name
                            if kind != "V" else "void"))
    arr = np.ascontiguousarray(a, dtype=np.float64)
    if not np.isfinite(arr).all():
        bad = int((~np.isfinite(arr)).sum())
        raise ValueError("%s: %s has %d non-finite value(s) (NaN/Inf) — refusing"
                         % (op, name, bad))
    return arr


def _dirs_from_azel(az: np.ndarray, el: np.ndarray) -> np.ndarray:
    """Unit viewing directions in body coordinates (x forward, y left, z up)
    from azimuth (atan2(y, x), left positive) and elevation (asin(z))."""
    ce = np.cos(el)
    return np.stack([ce * np.cos(az), ce * np.sin(az), np.sin(el)], axis=-1)


_LATTICE_KEYS = ("uv", "az_rad", "el_rad", "dirs", "dphi_rad", "geometry")


def _as_lattice(lattice, op: str):
    """Validate a lattice dict (the return of :func:`fly_hex_lattice`).

    Returns ``(dirs (n,3) float64, el_rad (n,) float64, dphi_rad float,
    axis (3,) float64)`` where *axis* is the optical axis = the direction of the
    ``(0, 0)`` ommatidium (the lattice centre)."""
    if not isinstance(lattice, dict):
        raise ValueError("%s: lattice must be the dict returned by "
                         "fly_hex_lattice, got %r" % (op, type(lattice).__name__))
    missing = [k for k in _LATTICE_KEYS if k not in lattice]
    if missing:
        raise ValueError("%s: lattice is missing key(s) %r — it is not a "
                         "fly_hex_lattice result (a csi_design / fly_dsi table "
                         "has different keys and would be read as an eye)"
                         % (op, missing))
    dirs = _as_float_array(lattice["dirs"], "lattice['dirs']",
                           MAX_RESAMPLE_ELEMENTS, op)
    if dirs.ndim != 2 or dirs.shape[1] != 3:
        raise ValueError("%s: lattice['dirs'] must be (n, 3), got shape %r"
                         % (op, dirs.shape))
    el = _as_float_array(lattice["el_rad"], "lattice['el_rad']",
                         MAX_RESAMPLE_ELEMENTS, op)
    if el.shape != (dirs.shape[0],):
        raise ValueError("%s: lattice['el_rad'] has shape %r but 'dirs' has %d "
                         "rows" % (op, el.shape, dirs.shape[0]))
    dphi = _positive(lattice["dphi_rad"], "lattice['dphi_rad']")
    uv = np.asarray(lattice["uv"])
    axis = None
    if uv.ndim == 2 and uv.shape[1] == 2:
        centre = np.where((uv[:, 0] == 0) & (uv[:, 1] == 0))[0]
        if centre.size:
            axis = dirs[int(centre[0])].copy()
    if axis is None:
        axis = dirs[dirs.shape[0] // 2].copy()
    return dirs, el, dphi, axis


# --------------------------------------------------------------------------- #
# 1. lattice — the eye's geometry                                              #
# --------------------------------------------------------------------------- #
def fly_hex_lattice(radius=15, dphi_deg=4.63, az0_deg=0.0, el0_deg=0.0,
                    geometry="regular"):
    """Hexagonal ommatidial lattice: viewing directions of a compound eye.

    A hexagon of ``n = 3*radius*(radius+1)+1`` ommatidia on axial coordinates
    ``(u, v)`` with ``-radius <= u <= radius`` and
    ``max(-radius, -radius-u) <= v <= min(radius, radius-u)`` (u outer, v inner),
    each given an azimuth, an elevation and a unit viewing direction in body
    coordinates (x forward, y left, z up; ``az = atan2(y, x)`` left positive,
    ``el = asin(z)``).

    ``geometry="regular"``:  ``az = az0 + dphi*(v + u/2)``,
    ``el = el0 + dphi*(sqrt(3)/2)*u`` — an isotropic hexagon.
    ``geometry="boxeye"``:   the pixel-grid distortion of the connectome-derived
    models, ``pixel (y, x) = (13*(u + v/2), 13*v)`` with ``13 px = dphi``, so
    ``az = az0 - v*dphi`` and ``el = el0 - (u + v/2)*dphi``; the diagonal neighbour
    is 1.118x the axial spacing.

    radius:    the hexagon radius in ommatidia.
    dphi_deg:  the inter-ommatidial angle in degrees.
    az0_deg / el0_deg: the direction of the lattice centre (the optical axis).
    geometry:  one of :data:`GEOMETRIES`.

    Returns a dict ``{"uv": (n,2) int, "az_rad": (n,), "el_rad": (n,),
    "dirs": (n,3) unit vectors, "dphi_rad": float, "geometry": str}``.

    Ground truth: ``n == 3*radius*(radius+1)+1`` exactly, every ``dirs`` row is a
    unit vector, and for ``"boxeye"`` the ratio of the diagonal to the axial
    nearest-neighbour angular spacing is 1.118 (both pinned in the tests).

    **Raises** ``ValueError``: a *radius* outside ``[1, MAX_LATTICE_RADIUS]``, a
    non-positive *dphi_deg*, a non-real / non-finite / string / bool angle, and an
    unknown *geometry*.
    """
    op = "fly_hex_lattice"
    R = _count(radius, "radius", 1, MAX_LATTICE_RADIUS)
    dphi = _positive(dphi_deg, "dphi_deg")
    az0 = _finite_scalar(az0_deg, "az0_deg")
    el0 = _finite_scalar(el0_deg, "el0_deg")
    geom = _one_of(geometry, "geometry", GEOMETRIES, op)

    us, vs = [], []
    for u in range(-R, R + 1):
        vlo = max(-R, -R - u)
        vhi = min(R, R - u)
        for v in range(vlo, vhi + 1):
            us.append(u)
            vs.append(v)
    u = np.array(us, dtype=np.int64)
    v = np.array(vs, dtype=np.int64)
    dphi_rad = np.deg2rad(dphi)
    az0r = np.deg2rad(az0)
    el0r = np.deg2rad(el0)
    if geom == "regular":
        az = az0r + dphi_rad * (v + 0.5 * u)
        el = el0r + dphi_rad * (np.sqrt(3.0) / 2.0) * u
    else:  # boxeye
        az = az0r - dphi_rad * v
        el = el0r - dphi_rad * (u + 0.5 * v)
    dirs = _dirs_from_azel(az.astype(np.float64), el.astype(np.float64))
    return {
        "uv": np.ascontiguousarray(np.stack([u, v], axis=1)),
        "az_rad": np.ascontiguousarray(az, dtype=np.float64),
        "el_rad": np.ascontiguousarray(el, dtype=np.float64),
        "dirs": np.ascontiguousarray(dirs, dtype=np.float64),
        "dphi_rad": float(dphi_rad),
        "geometry": geom,
    }


# --------------------------------------------------------------------------- #
# 2. stimulus — a controlled sky panorama                                      #
# --------------------------------------------------------------------------- #
def _band_envelope(el_deg: np.ndarray, lo: float, hi: float,
                   edge: float) -> np.ndarray:
    e = np.zeros_like(el_deg)
    inside = (el_deg >= lo) & (el_deg <= hi)
    e[inside] = 1.0
    rise = (el_deg >= lo - edge) & (el_deg < lo)
    e[rise] = 0.5 * (1.0 - np.cos(np.pi * (el_deg[rise] - (lo - edge)) / edge))
    fall = (el_deg > hi) & (el_deg <= hi + edge)
    e[fall] = 0.5 * (1.0 + np.cos(np.pi * (el_deg[fall] - hi) / edge))
    return e


def _one_over_f(w: int, seed: int) -> np.ndarray:
    """A periodic 1-D signal whose power spectrum falls as 1/f^2 (amplitude 1/f),
    std normalised to 1 and clipped to +-2, with frequencies below 2 cycles per
    revolution removed."""
    rng = np.random.default_rng(seed)
    k = np.fft.rfftfreq(w, d=1.0 / w)          # integer cycles per revolution
    amp = np.zeros_like(k)
    keep = k >= 2.0
    amp[keep] = 1.0 / k[keep]
    phase = rng.uniform(0.0, 2.0 * np.pi, size=k.shape)
    spec = amp * np.exp(1j * phase)
    spec[0] = 0.0
    x = np.fft.irfft(spec, n=w)
    s = float(x.std())
    if s > 0.0:
        x = x / s
    return np.clip(x, -2.0, 2.0)


def fly_sky_1f(width=1024, height=512, band_lo_deg=20.0, band_hi_deg=60.0,
               amp=0.12, seed=0, edge_deg=5.0):
    """Synthetic equirectangular sky panorama with a banded 1/f azimuthal texture.

    An equirectangular image (row = elevation +90 deg down to -90 deg, column =
    azimuth 0 to 360 deg). Luminance is a vertical backlight gradient
    (0.62 at the zenith to 0.95 at the nadir) modulated in azimuth by a 1/f
    texture confined to an elevation band with cosine edges::

        L = gradient(el) * (1 + amp * band(el) * noise(az))   clipped to [0, 1]

    where ``noise`` has unit std, is clipped to +-2, and drops azimuthal
    frequencies below 2 cycles per revolution; ``band`` is 1 inside
    ``[band_lo_deg, band_hi_deg]`` with raised-cosine edges of width *edge_deg*.

    width / height: the panorama size in pixels.
    band_lo_deg / band_hi_deg / edge_deg: the textured elevation band.
    amp:  the texture contrast on the backlight.
    seed: integer seed for the azimuth noise (no ``None``).

    Returns a float64 ``(height, width)`` image in ``[0, 1]``.

    Ground truth: the standard deviation across azimuth of a row inside the band
    exceeds that of a row outside it by more than 5x, and the log-log slope of the
    azimuthal power spectrum of an in-band row is ``-2 +- 0.4`` (both pinned in the
    tests).

    **Raises** ``ValueError``: *width* / *height* outside their caps, a non-real /
    string / bool parameter, a negative *amp*, a non-positive *edge_deg*, and a
    band that does not satisfy ``-90 <= band_lo_deg < band_hi_deg <= 90``.
    """
    op = "fly_sky_1f"
    w = _count(width, "width", 8, MAX_IMAGE_DIM)
    h = _count(height, "height", 4, MAX_IMAGE_DIM)
    lo = _finite_scalar(band_lo_deg, "band_lo_deg")
    hi = _finite_scalar(band_hi_deg, "band_hi_deg")
    a = _nonneg(amp, "amp")
    s = _seed(seed)
    edge = _positive(edge_deg, "edge_deg")
    if not (-90.0 <= lo < hi <= 90.0):
        raise ValueError(
            "%s: the band must satisfy -90 <= band_lo_deg (%g) < band_hi_deg (%g) "
            "<= 90; an inverted or out-of-range band would place the texture where "
            "there is no sky." % (op, lo, hi))
    el = 90.0 - 180.0 * (np.arange(h) + 0.5) / h
    grad = 0.62 + (0.95 - 0.62) * ((90.0 - el) / 180.0)
    env = _band_envelope(el, lo, hi, edge)
    noise = _one_over_f(w, s)
    lum = grad[:, None] * (1.0 + a * env[:, None] * noise[None, :])
    return np.ascontiguousarray(np.clip(lum, 0.0, 1.0))


# --------------------------------------------------------------------------- #
# 3. sample — the eye's view of a pinhole image                                #
# --------------------------------------------------------------------------- #
@functools.lru_cache(maxsize=16)
def _resample_weights(h, w, fov_deg, drho_deg, dphi_rad, n, dirs_bytes,
                      axis_bytes):
    dirs = np.frombuffer(dirs_bytes, dtype=np.float64).reshape(n, 3)
    axis = np.frombuffer(axis_bytes, dtype=np.float64).copy()
    f = (h / 2.0) / np.tan(np.deg2rad(fov_deg) / 2.0)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    xc = (xx + 0.5 - w / 2.0) / f
    yc = -(yy + 0.5 - h / 2.0) / f
    el0 = float(np.arcsin(np.clip(axis[2], -1.0, 1.0)))
    az0 = float(np.arctan2(axis[1], axis[0]))
    left = np.array([-np.sin(az0), np.cos(az0), 0.0])
    up = np.array([-np.cos(az0) * np.sin(el0), -np.sin(az0) * np.sin(el0),
                   np.cos(el0)])
    pix = (axis[None, None, :]
           + left[None, None, :] * xc[..., None]
           + up[None, None, :] * yc[..., None])
    norm = np.sqrt(1.0 + xc * xc + yc * yc)
    pix_unit = pix / norm[..., None]
    solid = norm ** (-3.0)
    flat_unit = pix_unit.reshape(-1, 3)
    flat_solid = solid.reshape(-1)
    cosang = np.clip(dirs @ flat_unit.T, -1.0, 1.0)          # (n, P)
    maxcos = cosang.max(axis=1)
    covered = maxcos >= np.cos(dphi_rad / 2.0)
    a_deg = np.degrees(np.arccos(cosang))
    gauss = np.exp(-4.0 * LN2 * a_deg * a_deg / (drho_deg * drho_deg))
    gauss[a_deg > 2.0 * drho_deg] = 0.0
    wmat = gauss * flat_solid[None, :]
    rowsum = wmat.sum(axis=1)
    return wmat, rowsum, covered


def fly_hex_resample(image2d, lattice, drho_deg=8.23, fov_deg=90.0,
                     mode="pinhole"):
    """Resample a pinhole image onto an ommatidial lattice (the eye's view).

    Each ommatidium integrates the image under a Gaussian acceptance function of
    full width at half maximum *drho_deg* weighted by the pixel solid angle::

        signal_i = sum_p w_ip * image_p / sum_p w_ip
        w_ip = exp(-4 ln2 * a_ip^2 / drho_deg^2) * (1 + X_p^2 + Y_p^2)^(-3/2)

    with ``a_ip`` the angular distance between ommatidium *i* and pixel *p*, cut
    off at ``a <= 2*drho_deg``, and ``X, Y`` the pinhole-normalised pixel
    coordinates. The image is a perspective (pinhole) view whose optical axis is
    the lattice centre and whose *fov_deg* is the full **vertical** field of view.

    image2d:  a 2-D ``(H, W)`` pinhole image.
    lattice:  the dict returned by :func:`fly_hex_lattice`.
    drho_deg: the acceptance FWHM in degrees.
    fov_deg:  the full vertical field of view in degrees.
    mode:     ``"pinhole"`` (the only projection implemented).

    Returns a 1-D float64 signal of ``n`` ommatidial intensities.

    Ground truth: an azimuthal sinusoid of angular wavelength ``lambda`` is
    sampled with its amplitude scaled by the analytic modulation transfer
    ``exp(-pi^2 drho_deg^2 nu^2 / (4 ln2))``, ``nu = 1/lambda``, to within 0.05
    over ``lambda`` from 15 to 80 degrees at equatorial ommatidia (pinned in the
    tests).

    **Raises** ``ValueError``: a non-2-D / empty / non-finite *image2d*, an image
    over the element cap, a *lattice* that is not a :func:`fly_hex_lattice` result,
    a non-positive *drho_deg* / *fov_deg*, a *fov_deg* not below 180, an unknown
    *mode*, a ``n_ommatidia * n_pixels`` product over :data:`MAX_RESAMPLE_ELEMENTS`,
    and — this is the field-of-view guard — any ommatidium whose nearest pixel is
    farther than ``dphi_rad/2`` away (the eye is looking outside the image).
    """
    op = "fly_hex_resample"
    img = _as_float_array(image2d, "image2d", MAX_IMAGE_DIM * MAX_IMAGE_DIM, op)
    if img.ndim != 2:
        raise ValueError("%s: image2d must be a 2-D (H, W) pinhole image, got a "
                         "%d-D array of shape %r" % (op, img.ndim, img.shape))
    if img.size == 0:
        raise ValueError("%s: image2d is empty (shape %r)" % (op, img.shape))
    _one_of(mode, "mode", ("pinhole",), op)
    drho = _positive(drho_deg, "drho_deg")
    fov = _positive(fov_deg, "fov_deg")
    if fov >= 180.0:
        raise ValueError("%s: fov_deg = %g must be below 180 (a pinhole cannot "
                         "image a half-space or more)" % (op, fov))
    dirs, _el, dphi_rad, axis = _as_lattice(lattice, op)
    n = dirs.shape[0]
    h, w = img.shape
    if n * h * w > MAX_RESAMPLE_ELEMENTS:
        raise ValueError(
            "%s: the weight matrix would be %d ommatidia x %d pixels = %d "
            "elements, over the %d cap (~%d MB float64). Crop the image or use a "
            "smaller lattice." % (op, n, h * w, n * h * w, MAX_RESAMPLE_ELEMENTS,
                                   MAX_RESAMPLE_ELEMENTS * 8 // (1 << 20)))
    wmat, rowsum, covered = _resample_weights(
        int(h), int(w), float(fov), float(drho), float(dphi_rad), int(n),
        np.ascontiguousarray(dirs).tobytes(), np.ascontiguousarray(axis).tobytes())
    if not covered.all():
        bad = int((~covered).sum())
        raise ValueError(
            "%s: %d of %d ommatidia look outside the image — their nearest pixel "
            "is farther than the half-spacing dphi/2 = %g deg. The eye's field of "
            "view (radius ~%g deg for this lattice) exceeds the image's "
            "(fov_deg = %g deg). Widen fov_deg, enlarge the image, or use a "
            "smaller-radius lattice." % (op, bad, n, np.degrees(dphi_rad) / 2.0,
                                         float(np.degrees(np.max(np.abs(
                                             np.arccos(np.clip(dirs @ axis,
                                                               -1.0, 1.0)))))),
                                         fov))
    zero = rowsum <= 0.0
    if zero.any():
        raise ValueError(
            "%s: %d ommatidia have no pixel within the acceptance cut-off "
            "2*drho_deg = %g deg even though a pixel is within dphi/2 — the "
            "acceptance is narrower than the pixel grid. Increase drho_deg or the "
            "image resolution." % (op, int(zero.sum()), 2.0 * drho))
    out = (wmat @ img.reshape(-1)) / rowsum
    return np.ascontiguousarray(out, dtype=np.float64)


# --------------------------------------------------------------------------- #
# 4. motion — the elementary motion detector                                   #
# --------------------------------------------------------------------------- #
def _lowpass_first_order(x: np.ndarray, tau_s: float, dt_s: float) -> np.ndarray:
    """A first-order low-pass, ``tau y' + y = x``, by exact exponential smoothing
    (``alpha = 1 - exp(-dt/tau)``) along a 1-D signal."""
    alpha = 1.0 - np.exp(-dt_s / tau_s)
    y = np.empty_like(x)
    acc = x[0]
    for i in range(x.size):
        acc = acc + alpha * (x[i] - acc)
        y[i] = acc
    return y


QUANTIZE_MODES = ("log", "linear", "onoff")


def fly_hex_quantize(signal, bits=3, mode="log", contrast=0.2):
    """個眼信号を眼と同じやり方で量子化する: 対数圧縮してから個眼あたり n ビット(``mode="onoff"`` は ON / OFF の 2 チャネル)。

    複眼は生まれつき量子化器で、片眼およそ 800 個眼(間隔 4.6°)、光受容器は強度を対数圧縮して平均に適応し、
    ラミナの L1 / L2 が平均からの偏差を ON と OFF に分ける。この op はその予算を再現し、下流のモデル
    (reservoir・網膜部位対応の検査)に「本当に何ビット要るか」を問えるようにする。

    A compound eye is a quantizer by construction: ~800 ommatidia per eye at 4.6 deg spacing,
    photoreceptors that log-compress intensity and adapt to the mean, and lamina cells (L1/L2)
    that split the deviation into ON and OFF channels. This op reproduces that budget so a
    downstream model (reservoir, retinotopy test) can be asked how many bits it really needs.

    Parameters
    ----------
    signal : (n,) float
        Per-ommatidium intensities >= 0 (``fly_hex_resample`` output).
    bits : int
        1..8 levels = 2**bits (``mode="onoff"`` ignores it: the output is the signed pair below).
    mode : str
        ``"log"``: log1p-compress relative to the mean, shift the darkest ommatidium to 0, then
        uniform levels over the compressed range; ``"linear"``: uniform levels over [0, max]; ``"onoff"``: deviation from the mean
        relative to ``contrast`` clipped to [-1, 1] and returned as ``2 * n`` values ``[ON..., OFF...]``
        (ON = positive part, OFF = negative part), each >= 0.
    contrast : float
        Michelson-style contrast that saturates the ON/OFF channels (``mode="onoff"`` only).

    Returns
    -------
    (n,) float in [0, 1] (levels / (2**bits - 1)); for ``"onoff"`` (2n,) in [0, 1].

    Notes
    -----
    Non-finite or negative inputs are refused. A constant signal quantizes to all-zeros
    (``"log"`` / ``"onoff"``) — there is no contrast to encode.
    """
    op = "fly_hex_quantize"
    x = np.asarray(signal, dtype=np.float64)
    if x.ndim != 1 or x.size == 0:
        raise ValueError(f"{op}: signal must be a non-empty 1-D array (one value per ommatidium), got shape {x.shape}")
    if not np.isfinite(x).all() or (x < 0).any():
        raise ValueError(f"{op}: signal must be finite and >= 0 (intensities)")
    _one_of(mode, "mode", QUANTIZE_MODES, op)
    bits = int(bits)
    if not (1 <= bits <= 8):
        raise ValueError(f"{op}: bits must be in 1..8, got {bits}")
    contrast = float(contrast)
    if not np.isfinite(contrast) or contrast <= 0.0:
        raise ValueError(f"{op}: contrast must be a positive number, got {contrast}")
    levels = float(2 ** bits - 1)
    mean = float(x.mean())
    if mode == "onoff":
        dev = (x - mean) / max(mean * contrast, 1e-12)
        dev = np.clip(dev, -1.0, 1.0)
        return np.concatenate([np.maximum(dev, 0.0), np.maximum(-dev, 0.0)])
    if mode == "linear":
        peak = float(x.max())
        y = x / peak if peak > 0.0 else np.zeros_like(x)
    else:
        y = np.log1p(x / max(mean, 1e-12))
        y = y - float(y.min())                                   # 最も暗い個眼を 0 に(定数 → 全部 0)
        span = float(y.max())
        y = y / span if span > 0.0 else np.zeros_like(y)
    return np.round(y * levels) / levels


def fly_emd_response(signal_a, signal_b, tau_s=0.05, dt_s=0.001):
    """Hassenstein-Reichardt correlator between two adjacent ommatidial signals.

    The opponent elementary motion detector::

        R(t) = LP(a)(t) * b(t) - a(t) * LP(b)(t)

    where ``LP`` is a first-order low-pass of time constant *tau_s*. Delaying one
    channel and multiplying it against the other, then subtracting the mirror
    pair, gives a signal whose sign is the direction of motion and whose
    steady-state mean encodes the temporal frequency.

    signal_a / signal_b: the two 1-D input time series (same length).
    tau_s:  the low-pass time constant, seconds.
    dt_s:   the sample interval, seconds.

    Returns a 1-D float64 array ``R(t)`` of the same length.

    Ground truth: for two sinusoids of temporal frequency ``f`` (``omega = 2 pi f``)
    with a spatial phase ``psi = 2 pi dphi/lambda`` between them, the steady-state
    mean is ``R_bar = dI^2 * sin(psi) * omega tau/(1 + (omega tau)^2)`` (to 5%),
    which is zero at ``lambda = 2 dphi`` (``psi = pi``) and maximal at
    ``f = 1/(2 pi tau)`` independent of ``lambda`` (pinned in the tests).

    **Raises** ``ValueError``: a non-1-D / empty / too-short (< 2) / non-finite
    *signal_a* or *signal_b*, mismatched lengths, a signal over
    :data:`MAX_SIGNAL_POINTS`, and a non-positive *tau_s* / *dt_s*.
    """
    op = "fly_emd_response"
    a = _as_float_array(signal_a, "signal_a", MAX_SIGNAL_POINTS, op)
    b = _as_float_array(signal_b, "signal_b", MAX_SIGNAL_POINTS, op)
    for nm, arr in (("signal_a", a), ("signal_b", b)):
        if arr.ndim != 1:
            raise ValueError("%s: %s must be a 1-D time series, got a %d-D array "
                             "of shape %r" % (op, nm, arr.ndim, arr.shape))
        if arr.size < 2:
            raise ValueError("%s: %s has %d sample(s); a correlator needs at "
                             "least 2" % (op, nm, arr.size))
    if a.shape != b.shape:
        raise ValueError("%s: signal_a has %d samples but signal_b has %d — the "
                         "two channels must be the same length (they are the same "
                         "clip seen by two neighbouring ommatidia)"
                         % (op, a.size, b.size))
    tau = _positive(tau_s, "tau_s")
    dt = _positive(dt_s, "dt_s")
    lpa = _lowpass_first_order(a, tau, dt)
    lpb = _lowpass_first_order(b, tau, dt)
    return np.ascontiguousarray(lpa * b - a * lpb)


# --------------------------------------------------------------------------- #
# 5. looming — reading an approach out of an expanding angle                    #
# --------------------------------------------------------------------------- #
def _shift_delay(x: np.ndarray, dt_s: float, delay_s: float) -> np.ndarray:
    """Shift *x* later in time by *delay_s* (samples held at the leading edge)."""
    k = int(round(delay_s / dt_s))
    if k <= 0:
        return x
    out = np.empty_like(x)
    out[:k] = x[0]
    out[k:] = x[:-k]
    return out


def fly_lgmd_eta(theta_signal, dt_s, alpha=4.7, delay_s=0.0):
    """LGMD/eta looming response from an expanding subtended angle.

    The multiplicative looming model::

        eta(t) = theta'(t - delay) * exp(-alpha * theta(t - delay))

    where *theta_signal* is the object's full subtended angle over time, in
    radians. The product of the angular expansion rate and an exponentially
    decaying gain gives a response that peaks a fixed time before collision.

    theta_signal: the full subtended angle per sample, radians.
    dt_s:  the sample interval, seconds.
    alpha: the gain-decay constant.
    delay_s: a fixed neural delay, seconds.

    Returns a 1-D float64 array ``eta(t)`` of the same length.

    Ground truth: for an object of half-size ``l`` approaching at speed ``|v|``,
    ``eta`` peaks at a time-to-contact of ``alpha*l/|v| - delay_s`` (Gabbiani et
    al. Eq. 5), where the subtended angle is exactly ``2*atan(1/alpha)`` (Eq. 6;
    24.0 degrees for ``alpha = 4.7``) — both pinned in the tests.

    **Raises** ``ValueError``: a non-1-D / empty / too-short (< 3) / non-finite
    *theta_signal*, a signal over :data:`MAX_SIGNAL_POINTS`, a non-positive *dt_s*
    / *alpha*, and a negative *delay_s*.
    """
    op = "fly_lgmd_eta"
    theta = _as_float_array(theta_signal, "theta_signal", MAX_SIGNAL_POINTS, op)
    if theta.ndim != 1:
        raise ValueError("%s: theta_signal must be a 1-D angle series, got a %d-D "
                         "array of shape %r" % (op, theta.ndim, theta.shape))
    if theta.size < 3:
        raise ValueError("%s: theta_signal has %d sample(s); a derivative needs "
                         "at least 3" % (op, theta.size))
    dt = _positive(dt_s, "dt_s")
    a = _positive(alpha, "alpha")
    d = _nonneg(delay_s, "delay_s")
    theta_d = _shift_delay(theta, dt, d)
    dtheta = np.gradient(theta_d, dt)
    return np.ascontiguousarray(dtheta * np.exp(-a * theta_d))


def fly_tau_from_expansion(theta_signal, dt_s, shape="sphere"):
    """Time-to-contact from optical expansion — the tau margin.

    From the subtended angle and its rate::

        shape="disk":   tau = sin(theta) / theta'
        shape="sphere": tau = 2*tan(theta/2) / theta'

    ``theta_signal`` is the full subtended angle over time, radians.

    ★ The two object models differ by 33% at a 60-degree subtense (``sin 60 = 0.866``
    vs ``2 tan 30 = 1.155``); using the wrong one silently mis-times a landing, so
    the model is a required, named choice rather than a default guess.

    theta_signal: the full subtended angle per sample, radians.
    dt_s:  the sample interval, seconds.
    shape: ``"disk"`` (a frontal circular disk) or ``"sphere"``.

    Returns a 1-D float64 array of the time-to-contact per sample, seconds.
    Non-expanding samples (``theta' <= 0``) return ``NaN`` — a documented
    non-finite, because a contracting or static angle has no time-to-contact and
    inventing one would be a plausible-wrong number. (The registry op
    ``tb_fly_tau_from_expansion`` must return a finite signal, so it replaces those
    NaN by the signal fallback without recording a fallback event —
    ``backend_safe.NONFINITE_BY_DESIGN``; call this function directly to keep the NaN.)

    Ground truth: for the model's own object geometry (``theta = 2 asin(l/d)`` for a
    sphere, ``theta = 2 atan(l/d)`` for a disk) approaching at speed ``|v|``, the
    returned tau equals the true distance-over-speed ``d/|v|`` (pinned in the
    tests).

    **Raises** ``ValueError``: a non-1-D / empty / too-short (< 3) / non-finite
    *theta_signal*, a signal over :data:`MAX_SIGNAL_POINTS`, a non-positive *dt_s*,
    and an unknown *shape*. A non-expanding angle is **not** an error — it is the
    documented ``NaN`` return above.
    """
    op = "fly_tau_from_expansion"
    theta = _as_float_array(theta_signal, "theta_signal", MAX_SIGNAL_POINTS, op)
    if theta.ndim != 1:
        raise ValueError("%s: theta_signal must be a 1-D angle series, got a %d-D "
                         "array of shape %r" % (op, theta.ndim, theta.shape))
    if theta.size < 3:
        raise ValueError("%s: theta_signal has %d sample(s); a derivative needs "
                         "at least 3" % (op, theta.size))
    dt = _positive(dt_s, "dt_s")
    sh = _one_of(shape, "shape", ("disk", "sphere"), op)
    dtheta = np.gradient(theta, dt)
    if sh == "disk":
        num = np.sin(theta)
    else:
        num = 2.0 * np.tan(0.5 * theta)
    with np.errstate(divide="ignore", invalid="ignore"):
        tau = np.where(dtheta > 0.0, num / dtheta, np.nan)
    return np.ascontiguousarray(tau, dtype=np.float64)


# --------------------------------------------------------------------------- #
# 6. integrate — the wide-field opponent readout                               #
# --------------------------------------------------------------------------- #
def fly_hs_readout(responses, lattice, n_pref, el_min_deg=0.0, rectify=True):
    """Horizontal-system wide-field readout: opponent sum over the upper field.

    Given a stack of motion-detector responses over the ommatidia — the first
    *n_pref* rows the preferred-direction type, the rest the anti-preferred — the
    opponent readout over the ommatidia above the horizon is::

        (a - b) / (a + b + 1e-6)

    where ``a`` and ``b`` are the (optionally rectified) totals of the preferred
    and anti-preferred responses over the columns with ``el > el_min_deg``.

    Only the upper visual field is used because the ground flow of forward motion
    is ``1/distance`` while the rotational flow it must be separated from is
    distance-independent: an eye 1.2 mm above the floor sees floor flow of
    330-1000 deg/s, above the ~200 deg/s bandwidth of the motion detectors, so the
    lower field carries speed the correlator cannot read and is excluded.

    responses: a ``(k, n)`` matrix of responses, ``n`` matching the lattice.
    lattice:   the dict returned by :func:`fly_hex_lattice`.
    n_pref:    how many leading rows are the preferred-direction type
               (``1 <= n_pref < k``).
    el_min_deg: the horizon; only ommatidia above it contribute.
    rectify:   half-wave rectify (clip negatives to 0) before summing.

    Returns the opponent ratio as a float in ``[-1, 1]``.

    Ground truth: with the preferred rows active only in the upper field and the
    anti-preferred rows silent, the readout is ``+1`` (and the sign and value
    match the hand calculation); an ``el_min_deg`` above every ommatidium raises
    (pinned in the tests).

    **Raises** ``ValueError``: a non-2-D / empty / non-finite *responses*, a
    *responses* over the element cap, a *lattice* that is not a
    :func:`fly_hex_lattice` result, a column count not matching the lattice, a
    *n_pref* outside ``[1, k-1]``, a non-real *el_min_deg*, a non-bool *rectify*,
    and an *el_min_deg* above every ommatidium (no upper field to read).
    """
    op = "fly_hs_readout"
    r = _as_float_array(responses, "responses", MAX_RESAMPLE_ELEMENTS, op)
    if r.ndim != 2:
        raise ValueError("%s: responses must be a 2-D (k, n) matrix, got a %d-D "
                         "array of shape %r" % (op, r.ndim, r.shape))
    if r.size == 0:
        raise ValueError("%s: responses is empty (shape %r)" % (op, r.shape))
    _dirs, el, _dphi, _axis = _as_lattice(lattice, op)
    n = el.shape[0]
    if r.shape[1] != n:
        raise ValueError("%s: responses has %d columns but the lattice has %d "
                         "ommatidia — each column is one ommatidium's response "
                         "and they must correspond" % (op, r.shape[1], n))
    k = r.shape[0]
    npf = _count(n_pref, "n_pref", 1, k - 1)
    el_min = _finite_scalar(el_min_deg, "el_min_deg")
    rect = _bool(rectify, "rectify")
    upper = np.degrees(el) > el_min
    if not upper.any():
        raise ValueError(
            "%s: no ommatidium is above el_min_deg = %g (the lattice reaches to "
            "%g deg) — there is no upper visual field to integrate. Lower "
            "el_min_deg or use a lattice that looks upward."
            % (op, el_min, float(np.degrees(el.max()))))
    pref = r[:npf][:, upper]
    anti = r[npf:][:, upper]
    if rect:
        pref = np.maximum(pref, 0.0)
        anti = np.maximum(anti, 0.0)
    a = float(pref.sum())
    b = float(anti.sum())
    return float((a - b) / (a + b + 1e-6))


# --------------------------------------------------------------------------- #
# 7. tuning — direction selectivity                                            #
# --------------------------------------------------------------------------- #
def fly_dsi(responses, angles_deg):
    """Direction-selectivity index and preferred direction from tuning responses.

    A vector sum on the circle::

        DSI = |sum_k r_k exp(i theta_k)| / (sum_k r_k + 1e-9)
        preferred = angle(sum_k r_k exp(i theta_k))

    where ``r_k >= 0`` is the response to a stimulus moving at angle
    ``theta_k = angles_deg[k]`` (negatives clipped to 0).

    responses:  a 1-D array of responses, one per direction.
    angles_deg: the stimulus directions in degrees, same length.

    Returns a dict ``{"dsi": float, "pref_deg": float}`` with ``pref_deg`` in
    ``[-180, 180]``.

    Ground truth: a response at a single direction gives ``dsi == 1``; an isotropic
    response over directions evenly spanning the circle gives ``dsi == 0`` (pinned
    in the tests).

    **Raises** ``ValueError``: a non-1-D / empty / non-finite *responses* or
    *angles_deg*, mismatched lengths, an array over :data:`MAX_SIGNAL_POINTS`, and
    an all-zero *responses* (no direction tuning to report).
    """
    op = "fly_dsi"
    r = _as_float_array(responses, "responses", MAX_SIGNAL_POINTS, op)
    ang = _as_float_array(angles_deg, "angles_deg", MAX_SIGNAL_POINTS, op)
    for nm, arr in (("responses", r), ("angles_deg", ang)):
        if arr.ndim != 1:
            raise ValueError("%s: %s must be 1-D, got a %d-D array of shape %r"
                             % (op, nm, arr.ndim, arr.shape))
        if arr.size == 0:
            raise ValueError("%s: %s is empty" % (op, nm))
    if r.shape != ang.shape:
        raise ValueError("%s: responses has %d entries but angles_deg has %d — "
                         "each response is measured at one stimulus direction and "
                         "they must correspond" % (op, r.size, ang.size))
    rr = np.maximum(r, 0.0)
    total = float(rr.sum())
    if total <= 0.0:
        raise ValueError(
            "%s: all responses are zero (or negative) after rectification — there "
            "is no tuning to report, and a DSI of 0/0 would be a fabricated "
            "number. This cell did not respond to any direction." % (op,))
    vec = np.sum(rr * np.exp(1j * np.deg2rad(ang)))
    dsi = float(np.abs(vec) / (total + 1e-9))
    pref = float(np.degrees(np.angle(vec)))
    return {"dsi": dsi, "pref_deg": pref}


if __name__ == "__main__":                                # pragma: no cover
    lat = fly_hex_lattice()
    print("flyvision: %d ops" % len(FLYVISION))
    print("  default lattice: %d ommatidia (%s)"
          % (lat["dirs"].shape[0], lat["geometry"]))
