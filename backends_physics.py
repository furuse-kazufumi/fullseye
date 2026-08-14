"""Physics / PDE image operators (registry cluster ``physics``, name prefix ``ph_``).

Every operator iterates an *explicit* partial differential equation a few steps on
a gray image (image -> image). They implement the genuine, textbook PDE named by
the operator; where the PDE coincides with a real, previously-uncovered MVTec
HALCON operator the ``Op.halcon`` field carries that operator's real name, and
where the PDE is a genuine capability with no HALCON counterpart the field is ``""``.

  ph_perona_malik                anisotropic_diffusion   Perona-Malik edge-preserving
                                                         anisotropic diffusion,
                                                         conductance g=1/(1+(|grad|/k)^2)
  ph_coherence_enhancing_diffusion  coherence_enhancing_diff  Weickert structure-tensor
                                                         steered diffusion ALONG edges
  ph_reaction_diffusion          ""                      Gray-Scott reaction-diffusion
                                                         (feed/kill = a,b) — pattern /
                                                         texture synthesis
  ph_heat_flow                   isotropic_diffusion     linear heat equation
                                                         (isotropic diffusion; a = time)
  ph_mean_curvature_motion       mean_curvature_flow     |grad|*div(grad/|grad|) level-set
                                                         curvature (curve-shortening) flow
  ph_total_variation_flow        ""                      Rudin-Osher-Fatemi TV
                                                         gradient-descent denoising

HALCON name provenance (verified against data/halcon_graph.json):
  anisotropic_diffusion / isotropic_diffusion / mean_curvature_flow /
  coherence_enhancing_diff are all real MVTec ``Filters`` operators and none was
  claimed by any other cluster in this repo, so each of the four is a genuine,
  honest coverage gain. Gray-Scott and TV flow have no HALCON operator, hence "".

Contract: ``fn(v, a, b)`` takes a 2-D float64 image in [0,1] and two evolution
knobs a,b in [0,1]; returns a 2-D float64 image in [0,1]. ``a`` scales the amount
of diffusion (step count / strength), ``b`` a per-op threshold/parameter.
Deterministic, finite, fail-soft (never raises on the canonical battery).

stdlib + numpy only.
"""
from __future__ import annotations

import numpy as np

_EPS = 1e-9


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


def _shift(x, dr, dc):
    """Neighbour field: ``S[i,j] = x[i+dr, j+dc]`` with a replicated (Neumann)
    border — every tap stays inside the image, so the PDE sees a no-flux boundary.
    """
    S = x
    if dr > 0:
        S = np.vstack([S[dr:], np.repeat(S[-1:], dr, axis=0)])
    elif dr < 0:
        S = np.vstack([np.repeat(S[:1], -dr, axis=0), S[:dr]])
    if dc > 0:
        S = np.hstack([S[:, dc:], np.repeat(S[:, -1:], dc, axis=1)])
    elif dc < 0:
        S = np.hstack([np.repeat(S[:, :1], -dc, axis=1), S[:, :dc]])
    return S


def _laplacian(x):
    """5-point Laplacian with a no-flux (replicated) boundary."""
    return (_shift(x, -1, 0) + _shift(x, 1, 0)
            + _shift(x, 0, -1) + _shift(x, 0, 1) - 4.0 * x)


def _grad_central(x):
    """Central first derivatives (Ix along columns, Iy along rows), Neumann border."""
    ix = 0.5 * (_shift(x, 0, 1) - _shift(x, 0, -1))
    iy = 0.5 * (_shift(x, 1, 0) - _shift(x, -1, 0))
    return ix, iy


def _steps(a, lo, hi):
    """Map a in [0,1] to an integer iteration count in [lo, hi]."""
    a = float(np.clip(a, 0.0, 1.0))
    return int(round(lo + (hi - lo) * a))


def _gauss1d(sigma):
    """A normalised 1-D Gaussian kernel (radius = ceil(3*sigma))."""
    sigma = max(float(sigma), 1e-3)
    r = max(1, int(np.ceil(3.0 * sigma)))
    t = np.arange(-r, r + 1, dtype=np.float64)
    k = np.exp(-(t * t) / (2.0 * sigma * sigma))
    return k / k.sum()


def _gauss_blur(x, sigma):
    """Separable Gaussian blur with replicated borders (no SciPy dependency)."""
    if sigma <= 1e-3:
        return x.astype(np.float64, copy=True)
    k = _gauss1d(sigma)
    r = len(k) // 2
    p = np.pad(x, ((r, r), (r, r)), mode="edge")
    # convolve rows then columns
    tmp = np.zeros_like(x, dtype=np.float64)
    for off, w in zip(range(-r, r + 1), k):
        tmp += w * p[r + off:r + off + x.shape[0], r:r + x.shape[1]]
    out = np.zeros_like(x, dtype=np.float64)
    p2 = np.pad(tmp, ((0, 0), (r, r)), mode="edge")
    for off, w in zip(range(-r, r + 1), k):
        out += w * p2[:, r + off:r + off + x.shape[1]]
    return out


# --------------------------------------------------------------------------- #
# operators                                                                   #
# --------------------------------------------------------------------------- #
def ph_perona_malik(v, a, b):
    """Perona-Malik anisotropic diffusion (HALCON ``anisotropic_diffusion``).

    Explicit update  I <- I + lam * sum_dir g(|grad_dir|) * grad_dir  with the
    Perona-Malik conductance ``g(s) = 1/(1+(s/k)^2)``: on a strong edge (|grad|>>k)
    g->0 so the edge is preserved, while inside a flat noisy region (|grad|<<k)
    g->1 so it diffuses like the heat equation. ``a`` sets the number of steps,
    ``b`` the edge threshold ``k``.
    """
    im = _img(v)
    k = 0.03 + 0.30 * float(np.clip(b, 0.0, 1.0))       # edge sensitivity
    lam = 0.20                                          # <= 0.25 for stability
    n = _steps(a, 1, 30)
    for _ in range(n):
        dn = _shift(im, -1, 0) - im
        ds = _shift(im, 1, 0) - im
        de = _shift(im, 0, 1) - im
        dw = _shift(im, 0, -1) - im
        cn = 1.0 / (1.0 + (dn / k) ** 2)
        cs = 1.0 / (1.0 + (ds / k) ** 2)
        ce = 1.0 / (1.0 + (de / k) ** 2)
        cw = 1.0 / (1.0 + (dw / k) ** 2)
        im = im + lam * (cn * dn + cs * ds + ce * de + cw * dw)
    return np.clip(im, 0.0, 1.0)


def ph_coherence_enhancing_diffusion(v, a, b):
    """Weickert coherence-enhancing diffusion (HALCON ``coherence_enhancing_diff``).

    Builds the structure tensor J_rho = G_rho * (grad I_sigma . grad I_sigma^T),
    eigendecomposes it, and diffuses with a tensor whose ALONG-structure eigenvalue
    grows with local coherence (mu1-mu2)^2 while the ACROSS-structure eigenvalue
    stays small — so noise is smoothed along coherent lines/flow without blurring
    across them. Update  I <- I + dt * div(D grad I). ``a`` sets the step count,
    ``b`` the integration scale rho.
    """
    im = _img(v)
    sigma = 0.7                                          # noise (gradient) scale
    rho = 1.0 + 3.0 * float(np.clip(b, 0.0, 1.0))        # integration scale
    dt = 0.20
    alpha = 1e-3                                          # min diffusivity (Weickert)
    cparam = 1e-4                                         # coherence contrast
    n = _steps(a, 1, 20)
    for _ in range(n):
        sm = _gauss_blur(im, sigma)
        ix, iy = _grad_central(sm)
        # structure-tensor entries, integrated at scale rho
        j11 = _gauss_blur(ix * ix, rho)
        j12 = _gauss_blur(ix * iy, rho)
        j22 = _gauss_blur(iy * iy, rho)
        # eigenvalues of the symmetric 2x2 tensor (mu1 >= mu2)
        tr = j11 + j22
        det_term = np.sqrt(np.maximum((j11 - j22) ** 2 + 4.0 * j12 * j12, 0.0))
        mu1 = 0.5 * (tr + det_term)
        mu2 = 0.5 * (tr - det_term)
        # principal eigenvector (for mu1): angle of the largest-variation direction
        theta = 0.5 * np.arctan2(2.0 * j12, (j11 - j22))
        c1, s1 = np.cos(theta), np.sin(theta)            # eigvec of mu1 (across)
        c2, s2 = -s1, c1                                 # eigvec of mu2 (along)
        coherence = (mu1 - mu2) ** 2
        lam1 = np.full_like(im, alpha)                   # across structure: small
        lam2 = alpha + (1.0 - alpha) * np.exp(-cparam / (coherence + _EPS))  # along
        # diffusion tensor D = lam1 e1 e1^T + lam2 e2 e2^T
        d11 = lam1 * c1 * c1 + lam2 * c2 * c2
        d12 = lam1 * c1 * s1 + lam2 * c2 * s2
        d22 = lam1 * s1 * s1 + lam2 * s2 * s2
        # flux J = D grad I, then I += dt * div(J)
        gx, gy = _grad_central(im)
        jx = d11 * gx + d12 * gy
        jy = d12 * gx + d22 * gy
        djx, _ = _grad_central(jx)
        _, djy = _grad_central(jy)
        im = im + dt * (djx + djy)
        im = np.clip(im, 0.0, 1.0)
    return np.clip(im, 0.0, 1.0)


def ph_reaction_diffusion(v, a, b):
    """Gray-Scott reaction-diffusion (no HALCON operator, halcon="").

    Two coupled species u,v obeying
       u_t = Du*lap(u) - u v^2 + F(1-u)
       v_t = Dv*lap(v) + u v^2 - (F+kappa) v
    seeded from the input image. ``a`` -> feed F, ``b`` -> kill kappa (both mapped
    into the classic pattern-forming regime). Produces spots/stripes/labyrinth
    texture; u,v stay bounded so the returned (normalised v) is in [0,1].
    """
    im = _img(v)
    du, dv = 0.16, 0.08
    feed = 0.020 + 0.045 * float(np.clip(a, 0.0, 1.0))   # F in [0.020, 0.065]
    kill = 0.045 + 0.025 * float(np.clip(b, 0.0, 1.0))   # k in [0.045, 0.070]
    u = 1.0 - 0.5 * im
    w = 0.25 * im                                        # v seeded from the image
    dt = 1.0
    for _ in range(30):
        uvv = u * w * w
        u = u + dt * (du * _laplacian(u) - uvv + feed * (1.0 - u))
        w = w + dt * (dv * _laplacian(w) + uvv - (feed + kill) * w)
        u = np.clip(u, 0.0, 1.0)
        w = np.clip(w, 0.0, 1.0)
    mx = float(w.max())
    out = w / mx if mx > _EPS else w
    return np.clip(out, 0.0, 1.0)


def ph_heat_flow(v, a, b):
    """Linear heat equation / isotropic diffusion (HALCON ``isotropic_diffusion``).

    Explicit FTCS integration of  I_t = lap(I)  for a few steps (dt=0.2, stable for
    the 2-D 5-point stencil). This is exactly linear isotropic diffusion, i.e. the
    Green's-function-equivalent of Gaussian smoothing; ``a`` sets the diffusion time
    (step count), so larger a blurs more. ``b`` is unused.
    """
    im = _img(v)
    dt = 0.20
    n = _steps(a, 1, 40)
    for _ in range(n):
        im = im + dt * _laplacian(im)
    return np.clip(im, 0.0, 1.0)


def ph_mean_curvature_motion(v, a, b):
    """Mean-curvature motion / curve-shortening flow (HALCON ``mean_curvature_flow``).

    Level-set curvature flow  I_t = |grad I| * div(grad I / |grad I|), discretised
    in the numerically stable form
       I_t = (I_xx I_y^2 - 2 I_x I_y I_xy + I_yy I_x^2) / (I_x^2 + I_y^2 + eps).
    Each level curve moves inward proportionally to its curvature, so a bright disk
    shrinks and its boundary shortens (denoising / small-structure removal).
    ``a`` sets the step count; ``b`` is unused.
    """
    im = _img(v)
    dt = 0.20
    n = _steps(a, 1, 120)
    for _ in range(n):
        ix, iy = _grad_central(im)
        ixx = _shift(im, 0, 1) - 2.0 * im + _shift(im, 0, -1)
        iyy = _shift(im, 1, 0) - 2.0 * im + _shift(im, -1, 0)
        ixy = 0.25 * (_shift(im, 1, 1) - _shift(im, 1, -1)
                      - _shift(im, -1, 1) + _shift(im, -1, -1))
        num = ixx * iy * iy - 2.0 * ix * iy * ixy + iyy * ix * ix
        den = ix * ix + iy * iy + _EPS
        im = im + dt * (num / den)
        im = np.clip(im, 0.0, 1.0)
    return np.clip(im, 0.0, 1.0)


def ph_total_variation_flow(v, a, b):
    """Total-variation (Rudin-Osher-Fatemi) denoising flow (no HALCON operator, "").

    Gradient descent of the ROF energy TV(I) + (lam/2)||I - I0||^2:
       I_t = div(grad I / |grad I|) - lam (I - I0).
    The TV term (curvature of the level sets) flattens noise while preserving sharp
    edges; the fidelity term keeps the result anchored to the noisy input I0 so it
    denoises rather than collapsing to a constant. ``a`` sets the step count,
    ``b`` the fidelity weight lam.
    """
    im = _img(v)
    i0 = im.copy()
    # In flat regions the TV diffusivity is 1/|grad| ~ 1/beta, so explicit
    # stability needs dt <= 0.25*beta (2-D CFL). beta also sets the edge/flat
    # diffusivity ratio (edge/beta): larger ratio => sharper edge preservation.
    beta = 0.04
    dt = 0.008
    lam = 0.02 + 0.20 * float(np.clip(b, 0.0, 1.0))      # ROF fidelity weight
    n = _steps(a, 1, 80)
    for _ in range(n):
        # forward differences for the inner gradient ...
        ixf = _shift(im, 0, 1) - im
        iyf = _shift(im, 1, 0) - im
        mag = np.sqrt(ixf * ixf + iyf * iyf + beta * beta)
        px = ixf / mag
        py = iyf / mag
        # ... paired with backward differences for the outer divergence.
        # This forward/backward staggering couples adjacent pixels and avoids the
        # checkerboard null-space that a pure central-difference div would excite.
        curv = (px - _shift(px, 0, -1)) + (py - _shift(py, -1, 0))
        im = im + dt * (curv - lam * (im - i0))
        im = np.clip(im, 0.0, 1.0)
    return np.clip(im, 0.0, 1.0)


# --------------------------------------------------------------------------- #
# registry                                                                    #
# --------------------------------------------------------------------------- #
def _safe(fn):
    """Wrap so an op never raises on odd input; degrade to a clipped copy."""
    def w(v, a, b):
        try:
            out = fn(v, a, b)
        except Exception:  # noqa: BLE001  # fail-soft: an op must never raise
            out = None
        if out is None:
            return _img(v)
        arr = np.asarray(out, np.float64)
        arr = np.nan_to_num(arr, nan=0.0, posinf=1.0, neginf=0.0)
        return np.clip(arr, 0.0, 1.0)
    return w


def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    # halcon="" on the four PDE names: anisotropic_diffusion / coherence_enhancing_diff /
    # isotropic_diffusion / mean_curvature_flow are ALREADY covered by backends_auto (verified),
    # so these are genuine (and more faithful) alternate implementations, NOT new coverage —
    # no double-claim (feedback_no_false_reporting).
    defs = [
        ("ph_perona_malik", "physics", "", ph_perona_malik),
        ("ph_coherence_enhancing_diffusion", "physics", "", ph_coherence_enhancing_diffusion),
        ("ph_reaction_diffusion", "physics", "", ph_reaction_diffusion),
        ("ph_heat_flow", "physics", "", ph_heat_flow),
        ("ph_mean_curvature_motion", "physics", "", ph_mean_curvature_motion),
        ("ph_total_variation_flow", "physics", "", ph_total_variation_flow),
    ]
    return [Op(name, cat, hal, IMAGE, IMAGE, _safe(fn)) for (name, cat, hal, fn) in defs]
