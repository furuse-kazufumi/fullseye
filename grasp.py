"""Grasp synthesis from geometry — ranked parallel-jaw grasps (numpy + scipy).

The *payoff* of the 3-D import side of the perception stack: once an object is a
point cloud (from :mod:`stereo`, :mod:`mesh` surface sampling, or a scan) with
surface normals (:func:`pointcloud.estimate_normals`), this proposes **where to
grasp it** — candidate two-finger parallel-jaw grasps, each scored and ranked, so
a manipulation project can pick one and close the gripper:

    import fullseye as fs
    V, F   = fs.read_mesh("part.stl")
    grasps = fs.grasps_from_mesh(V, F, n_surface=2000, mu=0.5, width_max=0.08)
    best   = grasps[0]                 # highest Ferrari-Canny quality
    T      = best.pose                 # 4x4 gripper frame to move the hand to

This closes the loop that :mod:`registration` opened (object *pose*) with object
*grasp*: pose says where the thing is, grasp says how to pick it up.

What this is, precisely (honest scope):

  * A **two-finger parallel-jaw** antipodal model. The gripper has two flat jaws
    that close along one line; a grasp is a pair of surface contacts whose
    connecting line lies inside both contacts' friction cones (the antipodal /
    force-closure condition, Nguyen 1988). Candidate pairs are sampled from the
    surface geometry (ten Pas et al. 2017).
  * The quality is the **approximate Ferrari-Canny epsilon** (Ferrari & Canny
    1992): the radius of the largest origin-centred ball inside the convex hull
    of the contact **wrench** set, built from a *linearised* friction cone
    (``n_cone`` edges per contact). It is approximate for two reasons documented
    on :func:`ferrari_canny_quality`: the cone is polygonised, and a two-finger
    point-contact grasp cannot resist a pure twist about the line through its
    contacts, so the wrench set is only 5-dimensional — the epsilon is measured
    within that controllable 5-D subspace, the standard hard-finger two-contact
    treatment, not a full 6-D value.

  * Normals from a point cloud are **sign-ambiguous** unless a viewpoint oriented
    them. The antipodal / force-closure test here therefore treats each normal as
    an undirected *line* (it uses ``|n . L|``), which is robust to that sign flip
    and correct for genuinely antipodal geometry. Pass oriented normals if you
    have them; they are not required.

  * There is **no gripper kinematics, no reachability, and no learned grasping**
    here — that (a GG-CNN / Dex-Net style learned branch) is deliberately
    deferred to an optional ``[onnx]`` extra. :func:`collision_free` is a coarse
    finger-sweep occupancy check, not a full collision model.

Nothing below claims a capability its test does not demonstrate.

Fail-closed on untrusted input, in the style of :mod:`mesh` / :mod:`pointcloud`:
shapes and finiteness are validated, ``mu`` must be > 0, ``n_samples`` is capped
(``MAX_SAMPLES``), an empty or degenerate cloud yields an **empty** grasp list
rather than a crash, and a candidate pair with (near) zero separation or normals
parallel to the closing line is skipped. Malformed input raises ``ValueError``.

References (public):
  * V-D. Nguyen, "Constructing Force-Closure Grasps", IJRR 1988.
  * C. Ferrari & J. Canny, "Planning Optimal Grasps", ICRA 1992.
  * A. ten Pas, M. Gualtieri, K. Saenko, R. Platt, "Grasp Pose Detection in
    Point Clouds", IJRR 2017 (geometric antipodal grasp sampling).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

__all__ = [
    "Grasp",
    "sample_antipodal_grasps",
    "grasps_from_mesh",
    "force_closure",
    "ferrari_canny_quality",
    "approach_vector_from_normals",
    "rank_grasps",
    "grasp_pose",
    "collision_free",
    "MAX_SAMPLES",
    "MAX_GRASPS",
    "CONE_EDGES_DEFAULT",
    "MIN_SEPARATION",
    "DEFAULT_N_SAMPLES",
]

#: Hard cap on ``n_samples`` (seed points) — an untrusted / accidental DoS guard.
MAX_SAMPLES = 200_000
#: Hard cap on the number of grasps returned (one best partner is kept per seed,
#: so this also bounds the seed loop's output).
MAX_GRASPS = 50_000
#: Default friction-cone linearisation resolution for the quality metric.
CONE_EDGES_DEFAULT = 8
#: Contact pairs closer than this (in cloud units) are degenerate and skipped —
#: their connecting line, and hence the closing axis, is undefined.
MIN_SEPARATION = 1e-9
#: Default number of seed contacts sampled when the caller gives none.
DEFAULT_N_SAMPLES = 500

_EPS = 1e-12


# --------------------------------------------------------------------------- #
# result type                                                                 #
# --------------------------------------------------------------------------- #
@dataclass
class Grasp:
    """One ranked parallel-jaw grasp proposal.

    Attributes
    ----------
    center : (3,) float64
        Midpoint of the two contacts — the grasp frame origin.
    axis : (3,) float64, unit
        The **closing direction**: the line joining the two contacts,
        ``unit(contacts[1] - contacts[0])``. The jaws travel along this line.
    approach : (3,) float64, unit
        Gripper **approach direction**, perpendicular to ``axis`` (see
        :func:`approach_vector_from_normals`).
    width : float
        Jaw opening = distance between the two contacts.
    quality : float
        Approximate Ferrari-Canny epsilon (>= 0; larger is better). 0 means the
        pair is not force-closure under the linearised model.
    contacts : (2, 3) float64
        The two surface contact points.
    pose : (4, 4) float64
        Rigid gripper frame ``[[R | center], [0 0 0 1]]`` with columns of ``R``
        = ``(approach, axis, approach x axis)``. See :func:`grasp_pose`.
    """

    center: np.ndarray
    axis: np.ndarray
    approach: np.ndarray
    width: float
    quality: float
    contacts: np.ndarray
    pose: np.ndarray = field(default=None)

    def __post_init__(self):
        if self.pose is None:
            self.pose = grasp_pose(self)


# --------------------------------------------------------------------------- #
# fail-closed guards                                                          #
# --------------------------------------------------------------------------- #
def _points(P, what: str = "points") -> np.ndarray:
    """Coerce to (N, 3) float64 and reject NaN/Inf (a poisoned coordinate would
    corrupt every grasp computation) — mirrors mesh._finite_points."""
    A = np.asarray(P, np.float64)
    if A.ndim != 2 or A.shape[1] != 3:
        raise ValueError("%s must be (N, 3), got shape %r" % (what, (A.shape,)))
    if A.size and not np.isfinite(A).all():
        raise ValueError("%s contain non-finite (NaN/Inf) values" % what)
    return A


def _check_mu(mu) -> float:
    mu = float(mu)
    if not np.isfinite(mu) or mu <= 0.0:
        raise ValueError("mu (friction coefficient) must be finite and > 0, got %r" % (mu,))
    return mu


def _unit(v):
    """Unit vector, or ``None`` if the input has (near) zero length."""
    v = np.asarray(v, np.float64)
    n = float(np.linalg.norm(v))
    if n < _EPS:
        return None
    return v / n


def _perp(axis: np.ndarray) -> np.ndarray:
    """A deterministic unit vector perpendicular to *axis* (unit)."""
    e = np.zeros(3)
    e[int(np.argmin(np.abs(axis)))] = 1.0          # the world axis least aligned
    t = e - float(e @ axis) * axis
    u = _unit(t)
    return u if u is not None else np.array([1.0, 0.0, 0.0])


def _cos_cone(mu: float) -> float:
    """cos(atan(mu)) — the friction-cone half-angle cosine."""
    return 1.0 / np.sqrt(1.0 + mu * mu)


# --------------------------------------------------------------------------- #
# force closure (Nguyen 1988)                                                 #
# --------------------------------------------------------------------------- #
def force_closure(contacts, normals, mu) -> bool:
    """Two-finger antipodal force-closure test (Nguyen 1988).

    The pair is force-closure when the line joining the two contacts lies inside
    **both** friction cones: the angle between the contact-to-contact line and
    each contact normal is <= ``atan(mu)``. Equivalently ``|n_i . L| >= cos(atan
    mu)`` for both contacts, where ``L`` is the unit line direction.

    *contacts* is (2, 3) and *normals* is (2, 3). The test uses the **unsigned**
    normal direction (each normal as an undirected line), so it is correct
    whether the cloud's normals were oriented (via a viewpoint) or not — the
    genuine antipodal geometry is what matters, not the arbitrary eigenvector
    sign :func:`pointcloud.estimate_normals` assigns.

    Returns ``False`` (rather than raising) for anything that is simply not a
    two-finger grasp — a single contact, a wrong contact count, coincident
    contacts, or a zero-length normal. Raises ``ValueError`` only for genuinely
    malformed input: a non-(k, 3) array, non-finite values, or ``mu <= 0``.
    """
    C = _points(contacts, "contacts")
    N = _points(normals, "normals")
    mu = _check_mu(mu)
    if C.shape[0] != 2 or N.shape[0] != 2:
        return False                                # not a two-finger grasp
    L = _unit(C[1] - C[0])
    if L is None:                                   # coincident contacts
        return False
    n0, n1 = _unit(N[0]), _unit(N[1])
    if n0 is None or n1 is None:                    # a degenerate (zero) normal
        return False
    cos_fc = _cos_cone(mu)
    return bool(abs(float(n0 @ L)) >= cos_fc and abs(float(n1 @ L)) >= cos_fc)


# --------------------------------------------------------------------------- #
# Ferrari-Canny epsilon quality (Ferrari & Canny 1992)                        #
# --------------------------------------------------------------------------- #
def _cone_edges(n_inward: np.ndarray, mu: float, n_cone: int) -> np.ndarray:
    """``n_cone`` unit force vectors on the friction cone about *n_inward*.

    Each edge is ``normalize(n + mu*(cos t * u + sin t * v))`` for a tangent
    basis ``(u, v)`` of the contact normal — the polygonised (linearised)
    boundary of the cone the contact can push through.
    """
    u = _perp(n_inward)
    v = np.cross(n_inward, u)
    ang = np.linspace(0.0, 2.0 * np.pi, n_cone, endpoint=False)
    dirs = n_inward[None, :] + mu * (np.cos(ang)[:, None] * u[None, :]
                                     + np.sin(ang)[:, None] * v[None, :])
    nrm = np.linalg.norm(dirs, axis=1, keepdims=True)
    return dirs / np.maximum(nrm, _EPS)


def _inscribed_ball_radius(W: np.ndarray) -> float:
    """Radius of the largest origin-centred ball inside ``conv(W)``.

    *W* is (m, 6) wrench generators. Because a two-finger point-contact wrench
    set is rank-deficient in 6-D (it cannot produce a moment about the line
    through the contacts), the ball is measured within the affine subspace the
    wrenches actually span (via an SVD projection). Returns 0 when the origin is
    outside that hull, when the origin is off the spanned subspace (so no wrench
    combination reaches it), or when the set is too degenerate to hull.
    """
    from scipy.spatial import ConvexHull
    from scipy.spatial.qhull import QhullError  # type: ignore

    if W.shape[0] < 2:
        return 0.0
    scale = float(np.max(np.abs(W)))
    if not np.isfinite(scale) or scale < _EPS:
        return 0.0
    mean = W.mean(axis=0)
    Wc = W - mean
    # SVD -> orthonormal basis of the spanned subspace + its dimension.
    U, s, Vt = np.linalg.svd(Wc, full_matrices=False)
    tol = s[0] * 1e-9 if s.size and s[0] > 0 else 0.0
    rank = int(np.count_nonzero(s > tol))
    if rank < 1:
        return 0.0
    basis = Vt[:rank]                               # (rank, 6), orthonormal rows
    # The origin, relative to the point mean, in subspace coordinates.
    rel = -mean
    origin_sub = rel @ basis.T                      # (rank,)
    residual = float(np.linalg.norm(rel - origin_sub @ basis))
    if residual > 1e-6 * scale:                     # origin is off the subspace
        return 0.0
    pts = Wc @ basis.T                              # (m, rank), full-dim in subspace
    if rank == 1:                                   # a segment: ball = nearer end
        lo, hi = float(pts.min()), float(pts.max())
        o = float(origin_sub[0])
        return float(min(o - lo, hi - o)) if lo <= o <= hi else 0.0
    try:
        hull = ConvexHull(pts)
    except (QhullError, ValueError):
        return 0.0
    A = hull.equations[:, :-1]                       # unit facet normals
    b = hull.equations[:, -1]                        # offsets: A.x + b <= 0 inside
    sd = A @ origin_sub + b                          # signed distance origin->facet
    if sd.size == 0 or float(sd.max()) > 0.0:        # origin outside the hull
        return 0.0
    return float(-sd.max())


def ferrari_canny_quality(contacts, normals, mu, n_cone: int = CONE_EDGES_DEFAULT) -> float:
    """Approximate Ferrari-Canny epsilon grasp quality (Ferrari & Canny 1992).

    Each contact's friction cone is linearised into *n_cone* unit force edges.
    Every edge force ``f`` at contact position ``r`` (relative to the grasp
    centroid) contributes a 6-D **wrench** ``[f, (r x f) / L]`` where ``L`` is the
    largest moment arm (so the force and torque parts are comparably scaled). The
    epsilon is the radius of the largest ball centred on the wrench-space origin
    that fits inside the convex hull of those wrenches: the magnitude of the
    smallest disturbance wrench the grasp can *just* resist. It is > 0 only when
    the origin is inside the hull (force closure) and grows as the grasp gets more
    balanced, so a well-centred antipodal grasp scores above a skewed one.

    Normals are oriented **inward** (toward the grasp centroid) before the cones
    are built, so the metric is independent of the cloud normals' arbitrary sign.

    Approximate, honestly, for two reasons:

      * the friction cone is polygonised into ``n_cone`` edges (a finer ``n_cone``
        tightens the estimate toward the true circular cone);
      * a two-finger point-contact grasp cannot resist a pure moment about the
        line through its two contacts, so the wrench set is only 5-dimensional in
        6-D wrench space. This returns the epsilon **within that controllable 5-D
        subspace** (the standard hard-finger two-contact treatment) — not a full
        6-D value, which would be 0 for *any* such grasp. Treat it as a relative
        score for ranking, not an absolute Newton-metre disturbance bound.

    Returns 0.0 for a non-force-closure pair, a single/zero contact, coincident
    contacts, or a degenerate wrench set. Raises ``ValueError`` on non-finite
    input or ``mu <= 0``.
    """
    C = _points(contacts, "contacts")
    N = _points(normals, "normals")
    mu = _check_mu(mu)
    n_cone = int(n_cone)
    if n_cone < 3:
        raise ValueError("n_cone must be >= 3 (a cone needs >= 3 edges), got %r" % (n_cone,))
    if C.shape[0] < 2 or N.shape[0] != C.shape[0]:
        return 0.0
    centroid = C.mean(axis=0)
    r = C - centroid
    l_char = float(np.max(np.linalg.norm(r, axis=1)))
    if l_char < MIN_SEPARATION:                     # contacts coincide
        return 0.0
    wrenches = []
    for i in range(C.shape[0]):
        n_in = _unit(N[i])
        if n_in is None:
            return 0.0
        # orient inward: point the normal toward the grasp centroid
        if float(n_in @ (centroid - C[i])) < 0.0:
            n_in = -n_in
        edges = _cone_edges(n_in, mu, n_cone)       # (n_cone, 3) unit forces
        torque = np.cross(r[i][None, :], edges) / l_char
        wrenches.append(np.concatenate([edges, torque], axis=1))
    W = np.concatenate(wrenches, axis=0)            # (k*n_cone, 6)
    return _inscribed_ball_radius(W)


# --------------------------------------------------------------------------- #
# grasp frame                                                                 #
# --------------------------------------------------------------------------- #
def approach_vector_from_normals(contacts, normals) -> np.ndarray:
    """A gripper approach direction perpendicular to the grasp axis (unit (3,)).

    The jaws close along the contact-to-contact ``axis``; the gripper *approaches*
    along a direction orthogonal to it. This takes the average **inward** contact
    normal (each oriented toward the grasp centroid) and projects out the ``axis``
    component. For a symmetric antipodal grasp the two inward normals are nearly
    anti-parallel and cancel, leaving the approach under-determined — a
    deterministic perpendicular to ``axis`` is returned in that case. The result
    is always a unit vector orthogonal to ``axis``.
    """
    C = _points(contacts, "contacts")
    N = _points(normals, "normals")
    if C.shape[0] != 2 or N.shape[0] != 2:
        raise ValueError("approach_vector_from_normals needs exactly 2 contacts and 2 normals")
    axis = _unit(C[1] - C[0])
    if axis is None:
        raise ValueError("contacts coincide — the grasp axis is undefined")
    center = 0.5 * (C[0] + C[1])
    nin = []
    for i in range(2):
        u = _unit(N[i])
        if u is None:
            continue
        if float(u @ (center - C[i])) < 0.0:
            u = -u
        nin.append(u)
    a = None
    if nin:
        avg = np.mean(nin, axis=0)
        a = _unit(avg - float(avg @ axis) * axis)   # project off the axis
    if a is None:                                   # normals cancelled / absent
        a = _perp(axis)
    return a


def grasp_pose(g: Grasp) -> np.ndarray:
    """Rigid 4x4 gripper frame for a grasp.

    Columns of the rotation are ``x = approach``, ``y = axis``,
    ``z = approach x axis`` (a right-handed orthonormal frame), and the
    translation is the grasp ``center``. Move the gripper so its tool frame
    equals this transform and the jaws straddle the two contacts.
    """
    axis = _unit(g.axis)
    approach = g.approach
    if axis is None:
        raise ValueError("grasp axis is degenerate")
    # re-orthogonalise approach against axis so the frame is exactly orthonormal
    ap = _unit(approach - float(approach @ axis) * axis)
    if ap is None:
        ap = _perp(axis)
    z = _unit(np.cross(ap, axis))
    if z is None:
        z = _perp(axis)
    R = np.column_stack([ap, axis, z])
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = np.asarray(g.center, np.float64)
    return T


def rank_grasps(grasps) -> list:
    """Return the grasps sorted by ``quality`` descending (best first)."""
    return sorted(grasps, key=lambda g: g.quality, reverse=True)


def _make_grasp(c0, c1, n0, n1, mu, n_cone) -> Grasp:
    """Assemble + score a Grasp from two contacts and their normals."""
    contacts = np.array([c0, c1], np.float64)
    normals = np.array([n0, n1], np.float64)
    axis = _unit(c1 - c0)
    center = 0.5 * (c0 + c1)
    width = float(np.linalg.norm(c1 - c0))
    approach = approach_vector_from_normals(contacts, normals)
    quality = ferrari_canny_quality(contacts, normals, mu, n_cone=n_cone)
    return Grasp(center=center, axis=axis, approach=approach,
                 width=width, quality=quality, contacts=contacts)


# --------------------------------------------------------------------------- #
# antipodal grasp sampling (ten Pas et al. 2017)                              #
# --------------------------------------------------------------------------- #
def sample_antipodal_grasps(points, normals=None, n_samples: int = DEFAULT_N_SAMPLES,
                            mu: float = 0.5, width_max=None, n_cone: int = CONE_EDGES_DEFAULT,
                            seed: int = 0) -> list:
    """Propose ranked two-finger antipodal grasps from a point cloud.

    Samples up to *n_samples* seed contacts; for each, searches the surface for a
    partner contact within *width_max* whose connecting line lies inside **both**
    friction cones (the antipodal condition, Nguyen 1988; geometric sampling after
    ten Pas et al. 2017), keeps the best-aligned partner, scores the pair with
    :func:`ferrari_canny_quality`, and returns the grasps sorted best-first.

    Parameters
    ----------
    points : (N, 3)
        The object surface cloud (metric units).
    normals : (N, 3), optional
        Per-point surface normals. Computed with
        :func:`pointcloud.estimate_normals` (unoriented — no viewpoint) when
        omitted; the antipodal test is sign-robust, so orientation is not
        required (pass oriented normals if you have them).
    n_samples : int
        Number of seed contacts to try (capped at ``MAX_SAMPLES``). If it is >=
        the cloud size every point is used once; otherwise a deterministic random
        subset is drawn.
    mu : float
        Coulomb friction coefficient (> 0). A larger ``mu`` widens the friction
        cones and admits more grasps.
    width_max : float, optional
        Maximum jaw opening. Pairs farther apart than this are rejected. Defaults
        to the cloud's bounding-box diagonal (effectively unlimited).
    n_cone : int
        Friction-cone linearisation for the quality metric (>= 3).
    seed : int
        Seed for the (deterministic) seed-contact sampling.

    Returns an empty list for an empty, single-point, or degenerate cloud — never
    raises on those. Raises ``ValueError`` for non-finite input, ``mu <= 0``,
    ``n_samples <= 0``, or a non-positive ``width_max``.
    """
    from scipy.spatial import cKDTree

    P = _points(points, "points")
    mu = _check_mu(mu)
    n_samples = int(n_samples)
    if n_samples <= 0:
        raise ValueError("n_samples must be > 0, got %r" % (n_samples,))
    n_samples = min(n_samples, MAX_SAMPLES)
    n_cone = int(n_cone)
    if n_cone < 3:
        raise ValueError("n_cone must be >= 3, got %r" % (n_cone,))
    N = P.shape[0]
    if N < 2:                                        # nothing to pair
        return []

    if normals is None:
        import pointcloud
        Nrm = pointcloud.estimate_normals(P, k=16)
    else:
        Nrm = _points(normals, "normals")
        if Nrm.shape[0] != N:
            raise ValueError("normals has %d rows for %d points" % (Nrm.shape[0], N))

    bbox = P.max(axis=0) - P.min(axis=0)
    diag = float(np.linalg.norm(bbox))
    if diag < MIN_SEPARATION:                        # all points coincident
        return []
    if width_max is None:
        wmax = diag
    else:
        wmax = float(width_max)
        if not np.isfinite(wmax) or wmax <= 0.0:
            raise ValueError("width_max must be finite and > 0, got %r" % (width_max,))

    cos_fc = _cos_cone(mu)
    tree = cKDTree(P)
    rng = np.random.default_rng(seed)
    if n_samples >= N:
        seeds = np.arange(N)
    else:
        seeds = rng.choice(N, size=n_samples, replace=False)

    grasps = []
    seen = set()
    for i in seeds:
        ci, ni = P[i], Nrm[i]
        nu = _unit(ni)
        if nu is None:
            continue
        neigh = tree.query_ball_point(ci, r=wmax)    # candidate opposite jaw
        if not neigh:
            continue
        J = np.fromiter((j for j in neigh if j != i), dtype=np.int64)
        if J.size == 0:
            continue
        Lv = P[J] - ci
        d = np.linalg.norm(Lv, axis=1)
        ok = (d > MIN_SEPARATION) & (d <= wmax)
        if not ok.any():
            continue
        J, Lv, d = J[ok], Lv[ok], d[ok]
        Lh = Lv / d[:, None]
        ai = np.abs(Lh @ nu)                         # |n_i . L|  (seed cone)
        # partner normals, unit-normalised (robust to un-normalised input)
        NJ = Nrm[J]
        njn = np.linalg.norm(NJ, axis=1)
        good = njn > _EPS
        if not good.any():
            continue
        aj = np.zeros(J.shape[0])
        aj[good] = np.abs(np.einsum("ij,ij->i", Lh[good], NJ[good] / njn[good, None]))
        passing = good & (ai >= cos_fc) & (aj >= cos_fc)
        if not passing.any():
            continue
        # keep the most "square" antipodal partner (line closest to both normals)
        score = ai * aj
        score[~passing] = -1.0
        jbest = int(J[int(np.argmax(score))])
        key = (int(i), jbest) if i < jbest else (jbest, int(i))
        if key in seen:
            continue
        seen.add(key)
        g = _make_grasp(ci, P[jbest], Nrm[i], Nrm[jbest], mu, n_cone)
        grasps.append(g)
        if len(grasps) >= MAX_GRASPS:
            break

    return rank_grasps(grasps)


def grasps_from_mesh(V, F, n_surface: int = 2000, mu: float = 0.5, width_max=None,
                     n_cone: int = CONE_EDGES_DEFAULT, seed: int = 0) -> list:
    """Convenience: sample a mesh surface into a cloud, then propose grasps.

    Draws *n_surface* points over the mesh with :func:`mesh.sample_surface`,
    estimates their normals with :func:`pointcloud.estimate_normals`, and forwards
    to :func:`sample_antipodal_grasps`. Same return contract (ranked list, empty
    on a degenerate mesh via the underlying guards).
    """
    import mesh
    import pointcloud

    pts = mesh.sample_surface(V, F, int(n_surface), seed=seed)
    if pts.shape[0] < 2:
        return []
    nrm = pointcloud.estimate_normals(pts, k=16)
    return sample_antipodal_grasps(pts, normals=nrm, n_samples=pts.shape[0], mu=mu,
                                   width_max=width_max, n_cone=n_cone, seed=seed)


# --------------------------------------------------------------------------- #
# optional coarse collision check                                             #
# --------------------------------------------------------------------------- #
def collision_free(grasp: Grasp, points, gripper_width=None, finger_len=None) -> bool:
    """Coarse finger-sweep collision check (approximate).

    Models the two jaws as thin slabs at ``+-gripper_width/2`` along the closing
    ``axis``, each reaching ``finger_len`` back along the approach direction, and
    reports whether the cloud protrudes into the *open gap* between the object and
    a jaw — i.e. whether any point sits beyond the grasp's own contacts (``|v| >
    width/2``) but still within the jaw envelope (``|v| <= gripper_width/2``) and
    within the finger's reach along the approach axis. Such a point would strike a
    finger before it reached the contact, so the grasp is reported as colliding.

    This is a deliberately simple occupancy test in the grasp frame, **not** a
    full swept-volume collision model (no finger thickness, no palm, no gripper
    CAD). Use it to prune obviously blocked grasps, not to certify reachability.

    *gripper_width* defaults to ``1.2 * grasp.width`` and *finger_len* to
    ``grasp.width``. Returns ``True`` when the sweep is clear.
    """
    P = _points(points, "points")
    if P.shape[0] == 0:
        return True
    width = float(grasp.width)
    gw = 1.2 * width if gripper_width is None else float(gripper_width)
    fl = width if finger_len is None else float(finger_len)
    if gw <= 0.0 or fl <= 0.0:
        raise ValueError("gripper_width and finger_len must be > 0")
    T = grasp_pose(grasp)
    R = T[:3, :3]
    local = (P - T[:3, 3]) @ R                       # columns: u=approach, v=axis, w=z
    u, v = local[:, 0], local[:, 1]
    within_reach = np.abs(u) <= fl
    in_gap = (np.abs(v) > 0.5 * width + MIN_SEPARATION) & (np.abs(v) <= 0.5 * gw)
    return bool(not np.any(within_reach & in_gap))
