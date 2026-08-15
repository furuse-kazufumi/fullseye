"""Ground-truth + contract tests for backends_deform.py (registry cluster deform_).

Does NOT import ops.py. It drives ``build()`` through a tiny ``_Op`` stub and
calls each module-level operator directly, asserting that it really implements
the published deformation model its name promises. Every algorithmic assertion
is anchored on an **independent reference computation** written in this file
from the papers' own equations (loop-based, different formulation from the
vectorised module code), not on "it ran without raising":

  * ``deform_tps`` -- the Bookstein (1989) linear system is re-assembled here
    with the literal U(r) = r^2 log r (the module uses the algebraically equal
    but different 0.5*r^2*log(r^2)), solved by lstsq, and both the coefficients
    and the dense warp must agree; the interpolation property f(p_i) = q_i, the
    side conditions sum(w_i) = 0 / sum(w_i p_i) = 0, and exact affine
    reproduction with zero bending are all checked.
  * ``deform_ffd`` -- the tensor cubic B-spline sum (Rueckert 1999) is recomputed
    pixel-by-pixel with the four textbook basis polynomials; the compact support
    of one control point (exactly 4 spans) is verified to be *exactly* zero
    outside its footprint.
  * ``deform_mls`` -- the per-pixel weighted least-squares affine (Schaefer et
    al. 2006) is re-solved here with an explicit 2x2 ``np.linalg.solve``; the
    defining exactness property (affine data is reproduced everywhere) and the
    control-point interpolation are checked.

For all three the op-level warp is validated against the reference field by
warping a linear ramp (bilinear resampling is exact on a linear function, so
out[y,x] must equal the ramp evaluated at the independently computed source
coordinate).
"""
from __future__ import annotations

import numpy as np

import backends_deform as D
from conftest import KNOBS, image_bank


# --------------------------------------------------------------------------- #
# stub registry (mirrors ops.Op's positional construction)                    #
# --------------------------------------------------------------------------- #
class _Op:
    def __init__(self, *a):
        self.name = a[0]
        self.category = a[1]
        self.halcon = a[2]
        self.in_sort = a[3]
        self.out_sort = a[4]
        self.fn = a[5]


def _norm(x):
    m = float(np.max(np.abs(x)))
    return x / m if m > 1e-8 else x


def _binm(v):
    return (np.asarray(v) > 0.5).astype(np.float64)


OPS = D.build(_Op, "image", "region", "feature", "contour", _norm, _binm)

EXPECTED = ["deform_tps", "deform_ffd", "deform_mls"]


# --------------------------------------------------------------------------- #
# independent references (written from the papers, loop-based on purpose)     #
# --------------------------------------------------------------------------- #
def _ref_tps_solve(src, dst):
    """Bookstein 1989 TPS system, assembled entry by entry with U(r)=r^2 log r."""
    src = np.asarray(src, float)
    n = len(src)
    lmat = np.zeros((n + 3, n + 3))
    for i in range(n):
        for j in range(n):
            r = float(np.hypot(src[i, 0] - src[j, 0], src[i, 1] - src[j, 1]))
            lmat[i, j] = r * r * np.log(r) if r > 0.0 else 0.0
        lmat[i, n] = 1.0
        lmat[i, n + 1] = src[i, 0]
        lmat[i, n + 2] = src[i, 1]
        lmat[n, i] = 1.0
        lmat[n + 1, i] = src[i, 0]
        lmat[n + 2, i] = src[i, 1]
    rhs = np.zeros((n + 3, 2))
    rhs[:n] = np.asarray(dst, float)
    return np.linalg.lstsq(lmat, rhs, rcond=None)[0]


def _ref_tps_eval(src, sol, pts):
    src = np.asarray(src, float)
    n = len(src)
    out = np.zeros((len(pts), 2))
    for k, v in enumerate(np.asarray(pts, float)):
        acc = sol[n] + sol[n + 1] * v[0] + sol[n + 2] * v[1]
        for i in range(n):
            r = float(np.hypot(v[0] - src[i, 0], v[1] - src[i, 1]))
            u = r * r * np.log(r) if r > 0.0 else 0.0
            acc = acc + u * sol[i]
        out[k] = acc
    return out


def _ref_b(l, u):
    """The four uniform cubic B-spline basis polynomials, written out."""
    if l == 0:
        return (1.0 - u) ** 3 / 6.0
    if l == 1:
        return (3.0 * u ** 3 - 6.0 * u ** 2 + 4.0) / 6.0
    if l == 2:
        return (-3.0 * u ** 3 + 3.0 * u ** 2 + 3.0 * u + 1.0) / 6.0
    return u ** 3 / 6.0


def _ref_ffd_field(h, w, phi, ny, nx):
    """Rueckert 1999 tensor cubic B-spline FFD, recomputed pixel by pixel."""
    sy = (h - 1) / ny
    sx = (w - 1) / nx
    out = np.zeros((h, w, 2))
    for y in range(h):
        ty = y / sy
        i0 = min(max(int(np.floor(ty)), 0), ny - 1)
        u = ty - i0
        for x in range(w):
            tx = x / sx
            j0 = min(max(int(np.floor(tx)), 0), nx - 1)
            uu = tx - j0
            acc = np.zeros(2)
            for l in range(4):
                for m in range(4):
                    acc = acc + _ref_b(l, u) * _ref_b(m, uu) * phi[i0 + l, j0 + m]
            out[y, x] = acc
    return out


def _ref_mls_affine(p, q, pts, alpha, eps=1e-8):
    """Schaefer et al. 2006 MLS-affine, re-solved per point with a 2x2 solve."""
    p = np.asarray(p, float)
    q = np.asarray(q, float)
    out = np.zeros((len(pts), 2))
    for k, v in enumerate(np.asarray(pts, float)):
        wts = np.array([1.0 / (float(np.sum((v - pi) ** 2)) + eps) ** alpha for pi in p])
        pstar = (wts[:, None] * p).sum(0) / wts.sum()
        qstar = (wts[:, None] * q).sum(0) / wts.sum()
        hp = p - pstar
        hq = q - qstar
        app = (wts[:, None, None] * hp[:, :, None] * hp[:, None, :]).sum(0)
        apq = (wts[:, None, None] * hp[:, :, None] * hq[:, None, :]).sum(0)
        mat = np.linalg.solve(app, apq)
        out[k] = (v - pstar) @ mat + qstar
    return out


def _ramp(h, w):
    """A horizontal linear ramp: bilinear resampling reproduces it exactly."""
    return (np.mgrid[0:h, 0:w][1] / float(w - 1)).astype(np.float64)


def _ramp_expected(src_yx, h, w, margin=1.0):
    """Expected warped ramp + a mask of pixels whose source is safely interior."""
    sy = src_yx[:, 0].reshape(h, w)
    sx = src_yx[:, 1].reshape(h, w)
    inside = ((sy > margin) & (sy < h - 1 - margin)
              & (sx > margin) & (sx < w - 1 - margin))
    return sx / float(w - 1), inside


# --------------------------------------------------------------------------- #
# structural / provenance                                                     #
# --------------------------------------------------------------------------- #
def test_registry_shape_names_and_sorts():
    names = [o.name for o in OPS]
    assert names == EXPECTED
    assert len(set(names)) == len(names)
    for op in OPS:
        assert op.name.startswith("deform_")
        assert op.in_sort == "image" and op.out_sort == "image"
        assert op.category == "deformation"


def test_every_op_makes_no_halcon_claim():
    # HALCON has no thin-plate-spline / free-form-deformation /
    # moving-least-squares operator; its warp operators only APPLY a supplied
    # vector field and its deformable-model family is matching, not synthesis.
    assert all(op.halcon == "" for op in OPS)


def test_no_overlap_with_the_existing_closed_form_warps():
    # Honesty: sk_swirl (backends.py) and aug_barrel (backends_aug.py) already
    # cover the global analytic warps. This cluster must neither reuse their
    # names nor merely reproduce their output.
    import backends_aug as AUG

    aug_names = {o.name for o in AUG.build(_Op, "image", "region", "feature",
                                           "contour", _norm, _binm)}
    assert aug_names.isdisjoint({o.name for o in OPS})
    img = image_bank()["normal"]
    barrel = AUG.aug_barrel(img, 0.8, 0.0)
    for fn in (D.deform_tps, D.deform_ffd, D.deform_mls):
        assert np.abs(fn(img, 0.8, 0.3) - barrel).max() > 1e-3


def test_contract_finite_deterministic_shape_and_range():
    for op in OPS:
        for iname, iv in image_bank().items():
            for a, b in KNOBS:
                out = op.fn(np.array(iv, copy=True), a, b)
                assert isinstance(out, np.ndarray) and out.ndim == 2, (op.name, iname)
                assert out.shape == iv.shape, (op.name, iname)
                assert np.isfinite(out).all(), (op.name, iname, a, b)
                assert out.min() >= -1e-9 and out.max() <= 1 + 1e-9, (op.name, iname)
                again = op.fn(np.array(iv, copy=True), a, b)
                assert np.array_equal(out, again), (op.name, iname, a, b)


def test_wrapper_is_fail_soft():
    # A garbage input must not raise: _safe -> sanitize returns a valid image.
    for op in OPS:
        out = op.fn("not an image", 0.5, 0.5)
        assert out is not None


def test_module_uses_no_random_number_generator():
    with open(D.__file__, encoding="utf-8") as fh:
        src = fh.read()
    for banned in ("np.random", "numpy.random", "default_rng", "RandomState",
                   "import random", "random.random", "np.seed"):
        assert banned not in src, banned


def test_knobs_outside_the_unit_interval_are_clamped():
    img = image_bank()["normal"]
    for fn in (D.deform_tps, D.deform_ffd, D.deform_mls):
        assert np.array_equal(fn(img, -3.0, 0.4), fn(img, 0.0, 0.4))
        assert np.array_equal(fn(img, 7.0, 0.4), fn(img, 1.0, 0.4))
        assert np.isfinite(fn(img, np.nan, np.inf)).all()


def test_every_op_really_deforms_at_full_amplitude():
    img = image_bank()["normal"]
    for fn in (D.deform_tps, D.deform_ffd, D.deform_mls):
        assert np.abs(fn(img, 1.0, 0.5) - img).max() > 1e-2, fn.__name__


def test_warping_a_constant_image_leaves_it_constant():
    # any resampling of a constant field must return that constant, whatever
    # the deformation does -- a cheap but exact end-to-end sanity anchor
    const = np.full((32, 32), 0.42)
    for fn in (D.deform_tps, D.deform_ffd, D.deform_mls):
        for a, b in KNOBS:
            out = fn(const, a, b)
            assert np.abs(out - 0.42).max() < 1e-12, (fn.__name__, a, b)


# --------------------------------------------------------------------------- #
# 1. thin-plate spline (Bookstein 1989)                                       #
# --------------------------------------------------------------------------- #
def _small_tps_problem():
    src = D._grid_points(24, 24, 4)
    dst = src.copy()
    # a known, small, deterministic displacement of the interior points
    dst[5] += np.array([1.5, -0.75])
    dst[6] += np.array([-0.5, 2.0])
    dst[9] += np.array([0.25, 0.5])
    dst[10] += np.array([-1.25, -1.0])
    return src, dst


def test_tps_kernel_is_r_squared_log_r():
    r = np.array([0.0, 0.25, 1.0, 2.0, 7.5])
    ref = np.where(r > 0, r * r * np.log(np.where(r > 0, r, 1.0)), 0.0)
    assert np.allclose(D._tps_kernel(r * r), ref, atol=1e-12)


def test_tps_interpolates_every_control_point():
    # THE defining property: the solved map must send each p_i exactly to q_i.
    src, dst = _small_tps_problem()
    weights, affine = D._tps_fit(src, dst)
    mapped = D._tps_eval(src, weights, affine, src)
    assert np.abs(mapped - dst).max() < 1e-6


def test_tps_side_conditions_of_the_bookstein_system_hold():
    # sum w_i = 0 and sum w_i p_i = 0 (zero force / zero moment): what makes the
    # interpolant the minimum-bending-energy one and affine at infinity.
    src, dst = _small_tps_problem()
    weights, _affine = D._tps_fit(src, dst)
    assert np.abs(weights.sum(axis=0)).max() < 1e-8
    assert np.abs(src.T @ weights).max() < 1e-7


def test_tps_coefficients_match_an_independent_solve_of_the_system():
    src, dst = _small_tps_problem()
    weights, affine = D._tps_fit(src, dst)
    ref = _ref_tps_solve(src, dst)
    n = len(src)
    assert np.abs(weights - ref[:n]).max() < 1e-8
    assert np.abs(affine - ref[n:]).max() < 1e-7


def test_tps_evaluation_matches_the_independent_evaluator():
    src, dst = _small_tps_problem()
    weights, affine = D._tps_fit(src, dst)
    pts = np.array([[0.0, 0.0], [3.5, 11.25], [12.0, 12.0], [23.0, 4.0], [7.7, 19.9]])
    got = D._tps_eval(src, weights, affine, pts)
    ref = _ref_tps_eval(src, _ref_tps_solve(src, dst), pts)
    assert np.abs(got - ref).max() < 1e-7


def test_tps_reproduces_an_exact_affine_with_zero_bending():
    # affine control data has no bending energy: all radial weights vanish and
    # the affine block IS the transform (Bookstein's decomposition).
    src = D._grid_points(24, 24, 4)
    mat = np.array([[1.1, 0.2], [-0.15, 0.9]])
    off = np.array([2.0, -1.5])
    dst = src @ mat + off
    weights, affine = D._tps_fit(src, dst)
    assert np.abs(weights).max() < 1e-7
    assert np.abs(affine[0] - off).max() < 1e-6
    assert np.abs(affine[1:] - mat).max() < 1e-8
    pts = np.array([[0.0, 0.0], [5.5, 17.25], [23.0, 23.0]])
    assert np.abs(D._tps_eval(src, weights, affine, pts) - (pts @ mat + off)).max() < 1e-6


def test_tps_identity_when_the_amplitude_knob_is_zero():
    # a = 0 -> control points do not move -> the SOLVED map is the identity
    # (there is no short circuit in the op; the linear solve produces it).
    for iname, iv in image_bank().items():
        out = D.deform_tps(iv, 0.0, 0.7)
        assert np.abs(out - iv).max() < 1e-6, iname


def test_tps_warp_matches_an_independent_reference_field_on_a_ramp():
    h = w = 20
    a, b = 0.6, 0.4
    img = _ramp(h, w)
    out = D.deform_tps(img, a, b)
    # rebuild the documented control displacement, then solve+evaluate with the
    # loop-based reference implementation
    src = D._grid_points(h, w, 5)
    amp = 0.15 * a * min(h, w)
    freq = 0.5 + 1.5 * b
    gy = src[:, 0] / (h - 1.0)
    gx = src[:, 1] / (w - 1.0)
    disp = np.stack([amp * np.sin(2 * np.pi * freq * gx),
                     amp * np.cos(2 * np.pi * freq * gy)], axis=1)
    interior = (gy > 1e-9) & (gy < 1 - 1e-9) & (gx > 1e-9) & (gx < 1 - 1e-9)
    disp[~interior] = 0.0
    dst = src + disp
    ref_map = _ref_tps_eval(dst, _ref_tps_solve(dst, src), D._pixel_points(h, w))
    expected, inside = _ramp_expected(ref_map, h, w)
    assert inside.sum() > 0.5 * h * w                      # the check is not vacuous
    assert np.abs(out[inside] - expected[inside]).max() < 1e-6


def test_tps_pins_the_border_control_points():
    # the 16 border control points carry zero displacement, so the four image
    # corners are fixed by the interpolation property
    h = w = 32
    src = D._grid_points(h, w, 5)
    a, b = 0.9, 0.2
    amp = 0.15 * a * min(h, w)
    freq = 0.5 + 1.5 * b
    gy = src[:, 0] / (h - 1.0)
    gx = src[:, 1] / (w - 1.0)
    disp = np.stack([amp * np.sin(2 * np.pi * freq * gx),
                     amp * np.cos(2 * np.pi * freq * gy)], axis=1)
    interior = (gy > 1e-9) & (gy < 1 - 1e-9) & (gx > 1e-9) & (gx < 1 - 1e-9)
    disp[~interior] = 0.0
    assert interior.sum() == 9 and (~interior).sum() == 16
    dst = src + disp
    weights, affine = D._tps_fit(dst, src)
    border = D._tps_eval(dst, weights, affine, src[~interior])
    assert np.abs(border - src[~interior]).max() < 1e-6


def test_tps_knobs_change_the_warp_and_stay_deterministic():
    img = image_bank()["normal"]
    lo = D.deform_tps(img, 0.3, 0.2)
    hi = D.deform_tps(img, 0.9, 0.2)
    other_f = D.deform_tps(img, 0.9, 0.9)
    assert np.abs(lo - hi).max() > 1e-3
    assert np.abs(hi - other_f).max() > 1e-3
    assert np.array_equal(hi, D.deform_tps(img, 0.9, 0.2))


# --------------------------------------------------------------------------- #
# 2. cubic B-spline free-form deformation (Rueckert 1999)                     #
# --------------------------------------------------------------------------- #
def test_bspline_basis_matches_the_textbook_polynomials():
    u = np.linspace(0.0, 1.0, 11)
    got = D._bspline3(u)
    for l in range(4):
        assert np.abs(got[l] - np.array([_ref_b(l, float(t)) for t in u])).max() < 1e-14
    assert np.abs(got.sum(axis=0) - 1.0).max() < 1e-14      # partition of unity
    assert got.min() >= 0.0                                 # non-negative


def test_ffd_zero_lattice_gives_a_zero_field_everywhere():
    field = D._ffd_field((33, 41), np.zeros((7, 7, 2)), 4, 4)
    assert np.abs(field).max() == 0.0


def test_ffd_single_control_point_has_exactly_four_spans_of_support():
    # compact support: control array index k (lattice index k-1) may only move
    # the spans i0 in [k-3, k]; everything else must be EXACTLY zero.
    ny = nx = 8
    h = w = 65                                   # span = 8 px
    span = (h - 1) / ny
    k = 4
    phi = np.zeros((ny + 3, nx + 3, 2))
    phi[k, k] = np.array([1.0, -2.0])
    field = D._ffd_field((h, w), phi, ny, nx)
    yy, xx = np.mgrid[0:h, 0:w]
    i0 = np.clip(np.floor(yy / span).astype(int), 0, ny - 1)
    j0 = np.clip(np.floor(xx / span).astype(int), 0, nx - 1)
    support = ((i0 >= k - 3) & (i0 <= k) & (j0 >= k - 3) & (j0 <= k))
    assert np.abs(field[~support]).max() == 0.0             # local, not global
    assert np.abs(field[support]).max() > 0.1               # and it really bumps
    # the bump lives in a (4 span) x (4 span) box around the control point
    nz = np.abs(field).sum(-1) > 0
    rows = np.where(nz.any(axis=1))[0]
    cols = np.where(nz.any(axis=0))[0]
    assert rows.min() >= (k - 3) * span and rows.max() < (k + 1) * span
    assert cols.min() >= (k - 3) * span and cols.max() < (k + 1) * span
    assert (rows.max() - rows.min()) <= 4 * span


def test_ffd_field_matches_the_independent_tensor_product_reference():
    ny, nx = 4, 5
    h, w = 21, 26
    ii = (np.arange(ny + 3) - 1.0) / ny
    jj = (np.arange(nx + 3) - 1.0) / nx
    phi = np.zeros((ny + 3, nx + 3, 2))
    phi[:, :, 0] = 1.7 * np.sin(2 * np.pi * jj)[None, :]
    phi[:, :, 1] = -0.9 * np.cos(2 * np.pi * ii)[:, None]
    got = D._ffd_field((h, w), phi, ny, nx)
    ref = _ref_ffd_field(h, w, phi, ny, nx)
    assert np.abs(got - ref).max() < 1e-12


def test_ffd_identity_when_the_amplitude_knob_is_zero():
    for iname, iv in image_bank().items():
        out = D.deform_ffd(iv, 0.0, 0.85)
        assert np.abs(out - iv).max() < 1e-12, iname


def test_ffd_warp_matches_the_reference_field_on_a_ramp():
    h = w = 33
    a, b = 0.8, 0.5
    img = _ramp(h, w)
    out = D.deform_ffd(img, a, b)
    ny = nx = 2 + int(b * 6)
    sy = (h - 1.0) / ny
    sx = (w - 1.0) / nx
    amp = 0.45 * a * min(sy, sx)
    ii = (np.arange(ny + 3) - 1.0) / ny
    jj = (np.arange(nx + 3) - 1.0) / nx
    phi = np.zeros((ny + 3, nx + 3, 2))
    phi[:, :, 0] = amp * np.sin(2 * np.pi * jj)[None, :]
    phi[:, :, 1] = amp * np.cos(2 * np.pi * ii)[:, None]
    ref = _ref_ffd_field(h, w, phi, ny, nx)
    yy, xx = np.mgrid[0:h, 0:w]
    ref_map = np.stack([(yy + ref[:, :, 0]).ravel(), (xx + ref[:, :, 1]).ravel()], 1)
    expected, inside = _ramp_expected(ref_map, h, w)
    assert inside.sum() > 0.5 * h * w
    assert np.abs(out[inside] - expected[inside]).max() < 1e-9


def test_ffd_amplitude_respects_the_injectivity_bound():
    # Choi & Lee (2000): |phi| < 0.48 * spacing keeps a uniform cubic B-spline
    # FFD fold-free. Each displacement component is varied ALONG ITS OWN lattice
    # axis so the monotonicity (fold) check is non-vacuous: the Jacobian diagonal
    # d(coord+disp)/dcoord then actually depends on the amplitude, and a fold shows
    # up as a non-positive diagonal. The counter-case below (amplitude far over the
    # bound) is required to fold, which proves the assertion can fail.
    h = w = 49
    for b in (0.0, 0.5, 1.0):
        ny = nx = 2 + int(b * 6)
        sy = (h - 1.0) / ny
        sx = (w - 1.0) / nx
        ii = (np.arange(ny + 3) - 1.0) / ny
        jj = (np.arange(nx + 3) - 1.0) / nx
        yy, xx = np.mgrid[0:h, 0:w]

        def field_for(amp):
            phi = np.zeros((ny + 3, nx + 3, 2))
            phi[:, :, 0] = amp * np.sin(2 * np.pi * ii)[:, None]   # y-disp varies along y
            phi[:, :, 1] = amp * np.sin(2 * np.pi * jj)[None, :]   # x-disp varies along x
            return D._ffd_field((h, w), phi, ny, nx)

        # within the injectivity bound -> strictly monotone (fold-free) both ways
        amp_ok = 0.45 * min(sy, sx)
        assert amp_ok < 0.48 * min(sy, sx)
        f = field_for(amp_ok)
        assert np.diff(yy + f[:, :, 0], axis=0).min() > 0.0
        assert np.diff(xx + f[:, :, 1], axis=1).min() > 0.0

        # far over the bound the map MUST fold somewhere -> the check is non-vacuous
        f_bad = field_for(3.0 * min(sy, sx))
        assert (np.diff(yy + f_bad[:, :, 0], axis=0).min() <= 0.0
                or np.diff(xx + f_bad[:, :, 1], axis=1).min() <= 0.0)


def test_ffd_lattice_resolution_knob_changes_the_deformation():
    img = image_bank()["normal"]
    coarse = D.deform_ffd(img, 0.9, 0.0)         # 2 spans
    fine = D.deform_ffd(img, 0.9, 1.0)           # 8 spans
    assert np.abs(coarse - fine).max() > 1e-3
    assert np.array_equal(fine, D.deform_ffd(img, 0.9, 1.0))


# --------------------------------------------------------------------------- #
# 3. moving least squares, affine variant (Schaefer et al. 2006)              #
# --------------------------------------------------------------------------- #
def _mls_control_set(h=48, w=48):
    return D._grid_points(h, w, 5)


def test_mls_reproduces_an_exact_affine_everywhere():
    # THE defining exactness property of MLS-affine: if the targets are an exact
    # affine image of the sources, the deformation IS that affine at every point
    # (for any weight function / any alpha).
    p = _mls_control_set()
    theta = 0.23
    rot = np.array([[np.cos(theta), -np.sin(theta)],
                    [np.sin(theta), np.cos(theta)]])
    off = np.array([3.0, -2.0])
    q = p @ rot + off
    pts = D._pixel_points(48, 48)
    truth = pts @ rot + off
    for alpha in (0.5, 1.0, 1.5, 2.0):
        got = D._mls_affine(p, q, pts, alpha)
        assert np.abs(got - truth).max() < 1e-8, alpha


def test_mls_reproduces_a_general_affine_including_shear_and_scale():
    p = _mls_control_set(32, 40)
    mat = np.array([[1.15, -0.25], [0.35, 0.85]])
    off = np.array([-4.0, 6.5])
    q = p @ mat + off
    pts = np.array([[0.0, 0.0], [31.0, 39.0], [7.5, 21.25], [16.0, 16.0]])
    got = D._mls_affine(p, q, pts, 1.0)
    assert np.abs(got - (pts @ mat + off)).max() < 1e-8


def test_mls_interpolates_its_control_points():
    p = _mls_control_set()
    q = p.copy()
    q[12] += np.array([4.0, -3.0])
    q[7] += np.array([-1.0, 2.5])
    got = D._mls_affine(p, q, p, 1.0)
    assert np.abs(got - q).max() < 1e-4


def test_mls_matches_the_independent_per_point_reference():
    p = _mls_control_set(30, 30)
    q = p.copy()
    q[12] += np.array([2.0, -1.5])
    q[13] += np.array([-1.0, 1.0])
    pts = np.array([[0.0, 0.0], [4.5, 22.25], [15.0, 15.0], [29.0, 3.0], [11.1, 8.8]])
    for alpha in (0.5, 1.0, 2.0):
        got = D._mls_affine(p, q, pts, alpha)
        ref = _ref_mls_affine(p, q, pts, alpha)
        assert np.abs(got - ref).max() < 1e-8, alpha


def test_mls_alpha_knob_localises_the_influence():
    # w_i = 1/|p_i - v|^(2 alpha): a larger alpha confines the influence of a
    # displaced control point to its own neighbourhood.
    p = _mls_control_set()
    q = p.copy()
    q[12] += np.array([4.0, -3.0])               # centre control point only
    far = np.array([[5.0, 5.0], [6.0, 42.0], [41.0, 6.0]])
    mags = [float(np.abs(D._mls_affine(p, q, far, al) - far).max())
            for al in (0.5, 1.0, 1.5, 2.0)]
    assert mags[0] > mags[1] > mags[2] > mags[3]
    near = np.array([[23.5, 23.5]])              # the displaced control point
    for al in (0.5, 1.0, 2.0):
        moved = np.abs(D._mls_affine(p, q, near, al) - near).max()
        assert moved > 3.5                       # still interpolated locally


def test_mls_identity_when_the_amplitude_knob_is_zero():
    for iname, iv in image_bank().items():
        out = D.deform_mls(iv, 0.0, 0.6)
        assert np.abs(out - iv).max() < 1e-6, iname


def test_mls_warp_matches_the_independent_reference_on_a_ramp():
    h = w = 24
    a, b = 0.7, 0.4
    img = _ramp(h, w)
    out = D.deform_mls(img, a, b)
    p = D._grid_points(h, w, 5)
    amp = 0.12 * a * min(h, w)
    gy = p[:, 0] / (h - 1.0)
    gx = p[:, 1] / (w - 1.0)
    q = p + np.stack([amp * np.sin(2 * np.pi * gx),
                      amp * np.cos(2 * np.pi * gy)], axis=1)
    ref_map = _ref_mls_affine(q, p, D._pixel_points(h, w), 0.5 + 1.5 * b)
    expected, inside = _ramp_expected(ref_map, h, w)
    assert inside.sum() > 0.4 * h * w
    assert np.abs(out[inside] - expected[inside]).max() < 1e-8


def test_mls_knobs_change_the_warp_and_stay_deterministic():
    img = image_bank()["normal"]
    lo = D.deform_mls(img, 0.3, 0.5)
    hi = D.deform_mls(img, 0.9, 0.5)
    other = D.deform_mls(img, 0.9, 0.0)
    assert np.abs(lo - hi).max() > 1e-3
    assert np.abs(hi - other).max() > 1e-3
    assert np.array_equal(hi, D.deform_mls(img, 0.9, 0.5))
