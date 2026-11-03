"""Coverage recipes for the non-image families: driving / robot simulators and rule-based planners
(``drive``), mathematics (``math``), 1-D signals (``oned``), statistical process control and
inspection statistics (``spc``), connectome graphs (``conngraph``), weighted graphs and paths
(``graph``), design of experiments and multivariate analysis (``multivar``), segmentation
proof-reading (``emproof``), streaming video (``videostream``), simulation calibration
(``simcal``), transformer attention kernels (``llmcore``) and convergence verification
(``converge``).

Every sample is synthetic with a closed-form answer (a time to collision Z / v, the RSS formula,
an OU process with known θ, a sine of known frequency, the Cpk of a known normal process, the
algebraic connectivity of a ring, a known shortest path, the Sobol' indices of a linear model ...).
Sample names carry the ``mx_`` prefix.
"""
from __future__ import annotations

import math

import numpy as np

from fullseye.recipebook.common import rng, sine_signal


# =================================================================================================
# samples
# =================================================================================================
def _translation(t):
    T = np.eye(4)
    T[:3, 3] = t
    return T


_K_CAM = np.array([[50.0, 0.0, 16.0], [0.0, 50.0, 16.0], [0.0, 0.0, 1.0]])


def mx_wall_approach(variant: int):
    """A tilted wall seen by a camera that drives toward it (render3d convention: −Z forward).

    Depth Z(col) = Z0 + 0.1·col m, the camera advances v·dt along its optical axis (points move
    +v·dt in camera Z) with a small lateral drift. Truth: per-pixel τ = Z / v (median over the
    image = median depth / v) and the focus of expansion = projection of the translation direction.
    """
    v = 10.0 + 4.0 * variant                     # closing speed, m/s
    z0 = 20.0 + 10.0 * variant                   # wall distance at the left edge, m
    dt = 0.1
    depth = z0 + 0.1 * np.tile(np.arange(32.0), (32, 1))
    tx, ty = 0.05 + 0.05 * variant, -0.03
    t = np.array([tx, ty, v * dt])                # point displacement in camera coordinates
    pose1 = _translation(t)
    fx, fy, cx, cy = _K_CAM[0, 0], _K_CAM[1, 1], _K_CAM[0, 2], _K_CAM[1, 2]
    foe_col = cx + fx * t[0] / (-t[2])
    foe_row = cy - fy * t[1] / (-t[2])
    return {"value": depth, "aux": {"K": _K_CAM.copy(), "pose0": np.eye(4), "pose1": pose1, "dt": dt},
            "truth": {"tau_median": float(np.median(depth)) / v, "closing_speed": v,
                      "foe_col": float(foe_col), "foe_row": float(foe_row)}}


def mx_rss_follow(variant: int):
    """Two cars in one lane (rear v_r, front v_f, gap d); truth = RSS Lemma 2 minimum safe distance
    with the ad-rss-lib defaults ρ = 1 s, a_accel = 3.5, b_min = 4, b_max = 8 m/s²."""
    v_r, v_f, d = (20.0, 15.0, 50.0) if variant == 0 else (25.0, 10.0, 40.0)
    rho, a, bmin, bmax = 1.0, 3.5, 4.0, 8.0
    safe = max(v_r * rho + 0.5 * a * rho ** 2 + (v_r + a * rho) ** 2 / (2 * bmin) - v_f ** 2 / (2 * bmax), 0.0)
    return {"value": None, "aux": {"v_rear": v_r, "v_front": v_f, "d": d},
            "truth": {"safe_distance": safe, "margin": d - safe}}


def mx_ou_wobble(variant: int):
    """Parameters of a driver's lateral wobble modelled as an OU process (θ, σ known)."""
    theta, sigma = (1.0, 0.3) if variant == 0 else (2.0, 0.5)
    return {"value": None, "aux": {"theta": theta, "sigma": sigma, "seed": 11 + variant},
            "truth": {"theta": theta, "sigma": sigma, "sd": sigma / math.sqrt(2 * theta)}}


def mx_peg_hole(variant: int):
    """Peg radius r and hole radius R (m); truth = Whitney's clearance ratio c = (R − r)/R and the
    jamming-free tilt arccos(r/R)."""
    r, R = (5.0e-3, 5.2e-3) if variant == 0 else (4.0e-3, 4.1e-3)
    return {"value": None, "aux": {"r": r, "R": R},
            "truth": {"c": (R - r) / R, "theta_m_exact": math.acos(r / R), "c_r": R - r}}


def mx_doa_angles(variant: int):
    """Two uncorrelated far-field sources at known bearings (deg) on an 8-element λ/2 array."""
    ang = np.array([-10.0, 20.0]) if variant == 0 else np.array([5.0, 35.0])
    return {"value": ang, "aux": {}, "truth": {"doa0": float(ang[0]), "doa1": float(ang[1])}}


def mx_poly_roots(variant: int):
    """A polynomial with roots 0.3, −0.5+0.2i, 1.5, 2.5i and a circle of radius 1 (variant 0) or 2
    (variant 1) about the origin; truth = number of roots inside (2 or 3)."""
    roots = np.array([0.3, -0.5 + 0.2j, 1.5, 2.5j])
    radius = 1.0 + 1.0 * variant
    inside = int(np.sum(np.abs(roots) < radius))
    return {"value": None, "aux": {"radius": radius, "coeffs": np.poly(roots).astype(complex)},
            "truth": {"n_inside": inside}}


def mx_aniso_samples(variant: int):
    """(500, 3) samples whose sample covariance is exactly R·diag(σ²)·Rᵀ (whitened, scaled, rotated);
    truth = condition number σ_max² / σ_min²."""
    g = rng(variant, 21)
    sig = np.array([2.0, 1.0, 0.5]) if variant == 0 else np.array([3.0, 1.0, 1.0])
    X = g.standard_normal((500, 3))
    X -= X.mean(axis=0)
    L = np.linalg.cholesky(X.T @ X / (X.shape[0] - 1))
    W = X @ np.linalg.inv(L).T                         # sample covariance exactly I
    Q, _ = np.linalg.qr(g.standard_normal((3, 3)))
    Y = (W * sig) @ Q.T + np.array([1.0, -2.0, 0.5])
    ev = np.sort(sig ** 2)[::-1]
    return {"value": Y, "aux": {}, "truth": {"cond": float(ev[0] / ev[-1]), "ev0": float(ev[0]),
                                             "ratio0": float(ev[0] / ev.sum()),
                                             "ev_min": float(ev[-1])}}


def mx_process_sample(variant: int):
    """2,000 individual measurements of a normal process N(μ, σ) and its spec limits 9.7 .. 10.3;
    truth = population Cp, Cpk."""
    mu, sd = (10.0, 0.1) if variant == 0 else (10.05, 0.06)
    lsl, usl = 9.7, 10.3
    n = 2000
    x = mu + sd * rng(variant, 22).standard_normal(n)
    cp, cpk = (usl - lsl) / (6 * sd), min(usl - mu, mu - lsl) / (3 * sd)
    se_cpk = math.sqrt(1.0 / (9 * n) + cpk ** 2 / (2 * (n - 1)))      # Bissell 1990
    se_cp = cp / math.sqrt(2 * (n - 1))
    return {"value": x, "aux": {"lsl": lsl, "usl": usl},
            "truth": {"cp": cp, "cpk": cpk, "mean": mu, "cpk_lo": cpk - 3 * se_cpk, "cpk_hi": cpk + 3 * se_cpk,
                      "cp_lo": cp - 3 * se_cp, "cp_hi": cp + 3 * se_cp}}


def mx_subgroups(variant: int):
    """25 subgroups of 5 parts from N(μ, σ); truth = grand mean μ and mean range d2·σ (d2 = 2.326)."""
    mu, sd = (50.0, 1.0) if variant == 0 else (52.0, 2.0)
    m, n = 25, 5
    x = mu + sd * rng(variant, 23).standard_normal((m, n))
    se_mean = sd / math.sqrt(m * n)
    se_rbar = 0.864 * sd / math.sqrt(m)                            # d3 = 0.864 for n = 5
    return {"value": x, "aux": {}, "truth": {"mean": mu, "rbar": 2.326 * sd, "sd": sd,
                                             "mean_lo": mu - 3 * se_mean, "mean_hi": mu + 3 * se_mean,
                                             "rbar_lo": 2.326 * sd - 3 * se_rbar, "rbar_hi": 2.326 * sd + 3 * se_rbar}}


def _part_pattern(n=48):
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    img = 0.3 + 0.3 * xx / n
    img[((yy - 20) ** 2 + (xx - 26) ** 2) < 100] = 0.75
    img[34:40, 6:42] = 0.15
    return img


def mx_sine_crossings(variant: int):
    """The shared ``sine_signal`` (f = 50 + 25·variant Hz, 1,024 samples at 1 kHz) with the number of zero
    crossings it must show: 2·f·N/fs (102.4 or 153.6)."""
    s = sine_signal(variant)
    n, fs = s["value"].size, s["aux"]["fs"]
    s["truth"] = dict(s["truth"], crossings=2.0 * s["truth"]["freq"] * n / fs)
    return s


def mx_varmodel_stack(variant: int):
    """12 good images of a printed part (structure + 0.02 noise) and one test image with a bright
    square defect of side 4 + 2·variant px; truth = defect area in px."""
    g = rng(variant, 24)
    base = _part_pattern()
    stack = np.stack([base + 0.02 * g.standard_normal(base.shape) for _ in range(12)])
    side = 4 + 2 * int(variant)
    test = base + 0.02 * g.standard_normal(base.shape)
    test[8:8 + side, 8:8 + side] += 0.3
    return {"value": stack, "aux": {"test": test}, "truth": {"area": float(side * side)}}


def mx_pod_ahat(variant: int):
    """â-vs-a NDT data: â = β0 + β1·a + N(0, 0.2²) for 60 flaw sizes 0.5 .. 5 mm; decision â > 3;
    truth = a50 = (3 − β0)/β1."""
    b0, b1 = (0.1, 2.0) if variant == 0 else (0.2, 1.5)
    a = np.linspace(0.5, 5.0, 60)
    ahat = b0 + b1 * a + 0.2 * rng(variant, 25).standard_normal(a.size)
    return {"value": {"a": a, "ahat": ahat}, "aux": {"a_dec": 3.0}, "truth": {"a50": (3.0 - b0) / b1}}


def mx_ring_synapses(variant: int):
    """Synapse table of a directed ring of n = 8 + 4·variant neurons; truth = Laplacian λ2 = 2 − 2cos(2π/n)
    and λmax = 4 (n even)."""
    n = 8 + 4 * int(variant)
    syn = np.array([[i, (i + 1) % n, 1.0 + (i % 3)] for i in range(n)], dtype=float)
    return {"value": syn, "aux": {}, "truth": {"lambda2": 2 - 2 * math.cos(2 * math.pi / n), "lambda_max": 4.0}}


def mx_cluster_synapses(variant: int):
    """k = 3 + variant groups of 4 neurons wired by strong synapses (count ≥ 2), plus weak spurious
    synapses (count 0.3) between groups; truth = k clusters once the weak ones are pruned."""
    k = 3 + int(variant)
    rows = []
    for gi in range(k):
        b = 4 * gi
        rows += [[b, b + 1, 3.0], [b + 1, b + 2, 2.0], [b + 2, b + 3, 4.0], [b + 3, b, 2.0]]
        if gi + 1 < k:
            rows.append([b + 3, b + 4, 0.3])
    return {"value": np.array(rows, dtype=float), "aux": {}, "truth": {"max_label": k - 1}}


def mx_tube_graph(variant: int):
    """Symmetric tube-length graph with a unique shortest 0 → 5 path: 0-1-5 (2.0) beats 0-2-3-5 (2.1) and
    0-4-5 (3.2); variant 1 lengthens 1-5 to 1.5 so 0-2-3-5 (2.1) wins."""
    L = np.zeros((6, 6))
    for (i, j, w) in [(0, 1, 1.0), (1, 5, 1.0 + 0.5 * variant), (0, 2, 0.7), (2, 3, 0.7), (3, 5, 0.7),
                      (0, 4, 3.0), (4, 5, 0.2)]:
        L[i, j] = L[j, i] = w
    return {"value": L, "aux": {}, "truth": {"path_length": 2.0 if variant == 0 else 2.1}}


def mx_triangles(variant: int):
    """Directed graph of k = 2 + variant disjoint directed 3-cycles plus a few acyclic edges; truth = k."""
    k = 2 + int(variant)
    n = 3 * k + 2
    A = np.zeros((n, n))
    for c in range(k):
        a, b, d = 3 * c, 3 * c + 1, 3 * c + 2
        A[a, b] = A[b, d] = A[d, a] = 1.0
        A[a, n - 1] = 1.0                             # into a sink: no new cycle
    A[n - 2, 0] = 1.0                                  # from a source
    return {"value": A, "aux": {}, "truth": {"cycles3": k}}


def mx_ccd_response(variant: int):
    """Central composite design (2 factors, 3 centre runs) and y = 10 − (x1 − a)² − 2(x2 − b)² (coded);
    truth = stationary point (a, b), a maximum."""
    import doe
    a, b = (0.3, -0.2) if variant == 0 else (-0.4, 0.5)
    des = doe.doe_central_composite(2, center=3)
    c = des["coded"]
    y = 10 - (c[:, 0] - a) ** 2 - 2 * (c[:, 1] - b) ** 2
    return {"value": None, "aux": {"y": y}, "truth": {"xs0": a, "xs1": b, "ymax": 10.0}}


def mx_sobol_linear(variant: int):
    """Saltelli design (n = 512, 3 factors uniform on [0, 1]) and the linear model y = Σ a_i x_i;
    truth = first-order Sobol' indices a_i² / Σ a_j² (no interactions)."""
    import sensitivity
    a = np.array([1.0, 2.0, 3.0]) if variant == 0 else np.array([3.0, 1.0, 0.5])
    des = sensitivity.doe_saltelli(512, [("x1", 0.0, 1.0), ("x2", 0.0, 1.0), ("x3", 0.0, 1.0)], seed=0)
    y = des["natural"] @ a
    s1 = a ** 2 / np.sum(a ** 2)
    return {"value": None, "aux": {"y": y, "factors": [("x1", 0.0, 1.0), ("x2", 0.0, 1.0), ("x3", 0.0, 1.0)]},
            "truth": {"s1_0": float(s1[0]), "s1_1": float(s1[1]), "s1_2": float(s1[2])}}


def mx_seg_labels(variant: int):
    """64×64 label image: one large cell (40×32 px, or 32×32 in variant 1) and two small ones on a
    background; truth = the VI split term after cutting the large cell in equal halves = A / N bits."""
    L = np.zeros((64, 64), dtype=np.int64)
    h = 40 if variant == 0 else 32
    L[8:8 + h, 4:36] = 1
    L[50:60, 40:60] = 2
    L[4:20, 44:60] = 3
    return {"value": L, "aux": {}, "truth": {"split_bits": h * 32 / 4096.0}}


def mx_scene_cut_clip(variant: int):
    """12 noisy frames: scene A (dark gradient) then scene B (bright disk) from frame c = 5 + 3·variant;
    truth = cut frame index."""
    g = rng(variant, 26)
    c = 5 + 3 * int(variant)
    yy, xx = np.mgrid[0:32, 0:32].astype(float)
    a = 0.2 + 0.2 * xx / 32
    b = 0.5 + 0.4 * (((yy - 16) ** 2 + (xx - 16) ** 2) < 100)
    frames = np.stack([(a if t < c else b) + 0.02 * g.standard_normal(a.shape) for t in range(12)])
    return {"value": np.clip(frames, 0, 1), "aux": {}, "truth": {"cut": c}}


def mx_flicker_clip(variant: int):
    """10 frames of a static textured scene under ±6 % lamp flicker, with a bright 6×6 (or 8×8) square
    entering from frame 1; truth = moving-object area in the last frame (px). Without deflicker the same
    background model flags 251 / 264 px in the last frame (measured), so the first stage is load-bearing."""
    g = rng(variant, 27)
    side = 6 + 2 * int(variant)
    yy, xx = np.mgrid[0:40, 0:40].astype(float)
    bg = 0.3 + 0.1 * np.sin(xx / 4.0) * np.cos(yy / 5.0)
    frames = []
    for t in range(10):
        f = bg.copy()
        if t > 0:                                      # frame 0 is the empty scene that seeds the model
            r0, c0 = 5 + 2 * t, 4 + 3 * t
            f[r0:r0 + side, c0:c0 + side] = 0.9
        f = f * (1.0 + 0.06 * (-1) ** t) + 0.005 * g.standard_normal(f.shape)
        frames.append(f)
    return {"value": np.stack(frames), "aux": {}, "truth": {"area": float(side * side)}}


_SIMCAL_NOISE = {"kind": "emva", "K": 0.5, "sigma_d": 6.0, "dark": 64.0}


def _chart(n=24):
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    img = np.full((n, n), 0.55)
    img[:, : n // 3] = 0.25 + 0.75 * ((xx[:, : n // 3] // 2) % 2)
    img[np.hypot(xx - 0.68 * n, yy - 0.5 * n) < n / 5.0] = 1.0
    return img


def mx_simcal_gain(variant: int):
    """A camera (EMVA linear model, 0.5 DN/e⁻, 6 e⁻ read noise, black 64 DN) photographs a test chart;
    the captured image is synthesized by Poisson electrons + read noise + rounding. Truth = the
    camera gain (600 or 900 DN) that the calibration must recover."""
    import simcal
    gain = 600.0 if variant == 0 else 900.0
    chain = [{"op": "stage:gain_offset", "args": {"offset": 64.0}}]
    knobs = [{"name": "gain", "step": 0, "arg": "gain", "lo": 100.0, "hi": 3000.0, "scale": "log", "unit": "DN"}]
    scene = _chart()
    model = simcal.simcal_model(chain=chain, knobs=knobs, scene=scene, noise=_SIMCAL_NOISE)
    g = rng(variant, 28)
    imgs = []
    for mu in simcal.simcal_simulate(model, {"gain": gain}):
        e = g.poisson(np.maximum(mu - 64.0, 0.0) / 0.5)
        imgs.append(np.round(0.5 * (e + 6.0 * g.standard_normal(mu.shape)) + 64.0))
    return {"value": None, "aux": {"chain": chain, "knobs": knobs, "scene": scene, "noise": _SIMCAL_NOISE,
                                   "images": imgs}, "truth": {"gain": gain}}


def mx_attention_lookup(variant: int):
    """6 one-hot queries, matching one-hot keys and random values: a sharp attention must copy value
    row i to output row i (a key-value lookup). Truth = value[2, 1] and value[4, 3]."""
    g = rng(variant, 29)
    q = 3.0 * np.eye(6, 8)
    k = np.eye(6, 8)
    v = g.standard_normal((6, 4))
    return {"value": q, "aux": {"key": k, "value": v}, "truth": {"v21": float(v[2, 1]), "v43": float(v[4, 3])}}


def mx_grid_study(variant: int):
    """Three solutions φ_i = 1 + 0.5·h_i^p on h = 0.1, 0.2, 0.4 (refinement ratio 2); truth = p."""
    p = 2.0 if variant == 0 else 1.5
    h = (0.1, 0.2, 0.4)
    phi = tuple(1.0 + 0.5 * hh ** p for hh in h)
    return {"value": None, "aux": {"phi": phi, "h": h}, "truth": {"p": p, "phi_ext": 1.0}}


def mx_babylonian(variant: int):
    """Heron's iteration x = (x + c/x)/2 whose fixed point is √c (c = 2 or 5)."""
    c = 2.0 if variant == 0 else 5.0
    return {"value": None, "aux": {"g": lambda x, c=c: 0.5 * (x + c / x), "x0": 1.0},
            "truth": {"root": math.sqrt(c)}}


SAMPLES = {
    "mx_wall_approach": mx_wall_approach, "mx_rss_follow": mx_rss_follow, "mx_ou_wobble": mx_ou_wobble,
    "mx_peg_hole": mx_peg_hole, "mx_doa_angles": mx_doa_angles, "mx_poly_roots": mx_poly_roots,
    "mx_aniso_samples": mx_aniso_samples, "mx_process_sample": mx_process_sample, "mx_subgroups": mx_subgroups,
    "mx_varmodel_stack": mx_varmodel_stack, "mx_pod_ahat": mx_pod_ahat, "mx_ring_synapses": mx_ring_synapses,
    "mx_cluster_synapses": mx_cluster_synapses, "mx_tube_graph": mx_tube_graph, "mx_triangles": mx_triangles,
    "mx_ccd_response": mx_ccd_response, "mx_sobol_linear": mx_sobol_linear, "mx_seg_labels": mx_seg_labels,
    "mx_scene_cut_clip": mx_scene_cut_clip, "mx_flicker_clip": mx_flicker_clip, "mx_simcal_gain": mx_simcal_gain,
    "mx_attention_lookup": mx_attention_lookup, "mx_grid_study": mx_grid_study, "mx_babylonian": mx_babylonian,
    "mx_sine_crossings": mx_sine_crossings,
}


# =================================================================================================
# recipes
# =================================================================================================
RECIPES = [
    # ---------------------------------------------------------------- drive
    {"name": "Sense — time to collision with a wall from depth and ego motion", "family": "drive",
     "task": "measure", "task_class": "sensing", "halcon": None, "input_sort": "image",
     "sample": "mx_wall_approach",
     "stages": [{"op": "relative_motion", "args": ["$aux.pose0", "$aux.pose1"]},
                {"op": "ttc_truth", "args": ["$in", "$aux.K", "$s1"], "kw": {"dt": "$aux.dt"}}],
     "expect": [{"get": ["tau", "@median"], "approx": "tau_median", "rtol": 1e-6},
                {"get": ["closing_speed", "@median"], "approx": "closing_speed", "rtol": 1e-6}],
     "note": "time-to-collision (TTC, τ) map in seconds for an approaching obstacle: the camera's two poses "
             "(world→camera 4×4) give the relative rigid motion, then each depth pixel (m) is moved and τ = Z·Δt/(Z0−Z1) "
             "(Lee 1976). Exact for constant speed — the ground truth to score a vision TTC estimator (forward "
             "collision warning, AEB). Sample: tilted wall 20–33 m, closing 10/14 m/s."},
    {"name": "Sense — focus of expansion of the ego motion (heading point in the image)", "family": "drive",
     "task": "measure", "task_class": "sensing", "halcon": None, "input_sort": "image",
     "sample": "mx_wall_approach",
     "stages": [{"op": "relative_motion", "args": ["$aux.pose0", "$aux.pose1"]},
                {"op": "foe_from_motion", "args": ["$aux.K", "$s1"]}],
     "expect": [{"get": [0], "approx": "foe_col", "atol": 1e-9}, {"get": [1], "approx": "foe_row", "atol": 1e-9}],
     "note": "focus of expansion (FoE, px col/row) = where the vehicle is heading in the image: the projection of the "
             "translation between two camera poses (pure translation required). Used to centre optical-flow TTC, to "
             "check camera mounting / yaw drift; truth = pinhole projection of the translation direction."},
    {"name": "Measure — RSS minimum safe following distance (responsibility-sensitive safety)",
     "family": "drive", "task": "measure", "task_class": "analysis", "halcon": None, "input_sort": None,
     "sample": "mx_rss_follow",
     "stages": [{"op": "rss_params"},
                {"op": "rss_longitudinal_check", "args": ["$prev"],
                 "kw": {"d": "$aux.d", "v_rear": "$aux.v_rear", "v_front": "$aux.v_front"}}],
     "expect": [{"get": ["safe_distance"], "approx": "safe_distance", "rtol": 1e-9},
                {"get": ["margin"], "approx": "margin", "atol": 1e-9}],
     "note": "Mobileye RSS longitudinal rule (Shalev-Shwartz 2017, Lemma 2) with the ad-rss-lib conservative "
             "parameters (ρ 1 s, accel 3.5, brake_min 4, brake_max 8 m/s²): minimum gap in m a following car must keep, "
             "and whether the current gap is dangerous. Speeds in m/s. The parameter table rides the first slot (the "
             "ledger door takes the table first, as declared; the speeds and the gap are keywords)."},
    {"name": "Measure — RSS minimum safe gap behind a braking lead car (rss_params -> rss_longitudinal_same)",
     "family": "drive", "task": "measure", "task_class": "analysis", "halcon": None, "input_sort": None,
     "sample": "mx_rss_follow",
     "stages": [{"op": "rss_params"},
                {"op": "rss_longitudinal_same", "args": ["$prev"],
                 "kw": {"v_rear": "$aux.v_rear", "v_front": "$aux.v_front"}}],
     "expect": [{"get": [], "approx": "safe_distance", "rtol": 1e-9}],
     "note": "the RSS same-direction distance alone (Shalev-Shwartz 2017, Lemma 2): the gap in m a rear car at "
             "v_r must keep so it can still stop if the front car at v_f brakes at b_max — rear reacts for ρ "
             "while accelerating, then brakes at b_min. ad-rss-lib conservative parameters; truth = the closed "
             "form d = [v_r ρ + ½aρ² + (v_r + aρ)²/(2 b_min) − v_f²/(2 b_max)]_+."},
    {"name": "Analyze — driver lateral wobble (Ornstein-Uhlenbeck mean reversion and noise)", "family": "drive",
     "task": "estimate", "task_class": "analysis", "halcon": None, "input_sort": None, "sample": "mx_ou_wobble",
     "stages": [{"op": "lateral_wobble",
                 "kw": {"n": 4096, "dt": 0.2, "theta": "$aux.theta", "sigma": "$aux.sigma", "seed": "$aux.seed"}},
                {"op": "ou_estimate", "kw": {"dt": 0.2}}],
     "expect": [{"get": ["theta"], "approx": "theta", "rtol": 0.2}, {"get": ["sigma"], "approx": "sigma", "rtol": 0.1}],
     "note": "simulate a lane-keeping driver's lateral offset as an OU process (exact discretisation, dt 0.2 s), then "
             "estimate its reversion rate θ (1/s) and noise σ (m/√s) by conditional maximum likelihood — the driver "
             "style / traffic model calibration loop. Tolerances ~4 standard errors for 4,096 samples."},
    {"name": "Inspect — peg-in-hole clearance ratio and jamming-free tilt (robot assembly)", "family": "drive",
     "task": "measure", "task_class": "analysis", "halcon": None, "input_sort": None, "sample": "mx_peg_hole",
     "stages": [{"op": "peg_params", "kw": {"r": "$aux.r", "R": "$aux.R"}}, {"op": "whitney_clearance"}],
     "expect": [{"get": ["c"], "approx": "c", "rtol": 1e-9},
                {"get": ["theta_m_exact"], "approx": "theta_m_exact", "rtol": 1e-9}],
     "note": "Whitney's quasi-static peg-in-hole analysis for a robot insertion: dimensionless clearance "
             "c = (R − r)/R, radial clearance (m), the tilt angle (rad) below which the peg cannot jam, the chamfer "
             "catch range and the wedging angle c/μ. Inputs are peg / hole radii in metres."},
    # ---------------------------------------------------------------- math
    {"name": "Sense — direction of arrival of two sources with an antenna array (MUSIC)", "family": "math",
     "task": "estimate", "task_class": "sensing", "halcon": None, "input_sort": "signal", "sample": "mx_doa_angles",
     "stages": [{"op": "ula_snapshots", "kw": {"n_elements": 8, "n_snapshots": 200, "snr_db": 20.0, "seed": 3}},
                {"op": "music_doa", "kw": {"n_sources": 2}}],
     "expect": [{"get": ["doa_deg", 0], "approx": "doa0", "atol": 0.3},
                {"get": ["doa_deg", 1], "approx": "doa1", "atol": 0.3}],
     "note": "radar / sonar / microphone-array bearing estimation: synthesize complex snapshots of an 8-element "
             "half-wavelength uniform linear array (20 dB SNR) for sources at known angles (deg), then MUSIC "
             "(Schmidt 1986) on the noise subspace returns the bearings; grid 0.05°."},
    {"name": "Analyze — count polynomial roots inside a circle (argument principle)", "family": "math",
     "task": "count", "task_class": "analysis", "halcon": None, "input_sort": None, "sample": "mx_poly_roots",
     "stages": [{"op": "cplx_contour_circle", "kw": {"radius": "$aux.radius", "n": 512}},
                {"op": "cplx_poly_eval", "args": ["$aux.coeffs", "$prev"]},
                {"op": "cplx_argument_principle", "args": ["$s1", "$s2"]}],
     "expect": [{"get": [], "equals": "n_inside"}],
     "note": "how many zeros of a (complex) polynomial lie inside a contour — stability checks (poles inside the "
             "unit circle), root isolation before Newton. Sample the circle, evaluate the polynomial on it, count the "
             "winding of the image curve: an exact integer without root finding."},
    {"name": "Measure — condition number of a measured covariance (anisotropy / ill-conditioning)",
     "family": "math", "task": "measure", "task_class": "analysis", "halcon": None, "input_sort": "matrix",
     "sample": "mx_aniso_samples",
     "stages": [{"op": "stat_covariance"}, {"op": "mat_cond"}],
     "expect": [{"get": [], "approx": "cond", "rtol": 1e-9}],
     "note": "sample covariance of N×D observations (rows = samples), then its 2-norm condition number "
             "λmax/λmin: how elongated the scatter is and how many digits a least-squares / Mahalanobis solve on it "
             "loses. Sample built so its covariance is exactly diag(4, 1, 0.25) rotated (cond 16) or (9, 1, 1)."},
    {"name": "Measure — principal axes of a scatter (covariance eigen-decomposition)", "family": "math",
     "task": "measure", "task_class": "measurement", "halcon": None, "input_sort": "matrix",
     "sample": "mx_aniso_samples",
     "stages": [{"op": "stat_covariance"}, {"op": "mat_eigh"}],
     "expect": [{"get": ["w", -1], "approx": "ev0", "rtol": 1e-9}, {"get": ["w", 0], "approx": "ev_min", "rtol": 1e-9}],
     "note": "covariance of N×D samples, then its symmetric eigen-decomposition: eigenvalues (ascending, variance "
             "along each principal axis, units²) and orthonormal axes V — the covariance-ellipse / orientation / "
             "flatness measurement of a point scatter or a set of features. Exact on the constructed sample."},
    # ---------------------------------------------------------------- oned
    {"name": "Sense — dominant vibration frequency after band-pass filtering", "family": "oned", "task": "measure",
     "task_class": "sensing", "halcon": None, "input_sort": "signal", "sample": "sine_signal",
     "stages": [{"op": "bandpass", "kw": {"rate": 1000.0, "low": 30.0, "high": 150.0}},
                {"op": "signal_features", "kw": {"rate": 1000.0}}],
     "expect": [{"get": ["peak_freq"], "approx": "freq", "atol": 1.0}],
     "note": "condition-monitoring feature vector of a vibration / acoustic signal sampled at 1 kHz: a 4th-order "
             "Butterworth band-pass 30–150 Hz removes drift and hiss, then RMS, peak, crest factor, ZCR, spectral "
             "centroid and the peak frequency (Hz, ±1 bin of 0.98 Hz)."},
    {"name": "Measure — count zero crossings of a smoothed profile (1-D function)", "family": "oned",
     "task": "count", "task_class": "measurement", "halcon": "1D Measuring", "input_sort": "signal",
     "sample": "mx_sine_crossings",
     "stages": [{"op": "smooth_funct_1d_gauss", "kw": {"sigma": 2.0}}, {"op": "zero_crossings_funct_1d"}],
     "expect": [{"get": ["@len"], "approx": "crossings", "atol": 1.5}],
     "note": "HALCON funct_1d style: Gaussian-smooth a sampled profile (σ in samples) so noise cannot add "
             "spurious sign changes, then the integer indices of its zero crossings — pulse / tooth / period "
             "counting. A sine of f Hz over 1.024 s crosses zero ≈ 2·f·1.024 times (102 or 153)."},
    {"name": "Measure — amplitude of a vibration via its Hilbert envelope", "family": "oned", "task": "measure",
     "task_class": "measurement", "halcon": None, "input_sort": "signal", "sample": "sine_signal",
     "stages": [{"op": "envelope"}, {"op": "rms"}],
     "expect": [{"get": [], "approx": "amp", "rtol": 0.03}],
     "note": "analytic-signal (Hilbert) envelope of a tone or burst, then its RMS level: for a steady sine the "
             "envelope is the amplitude itself (units of the signal), so knock / impact / acoustic-emission levels "
             "are read without peak picking."},
    # ---------------------------------------------------------------- spc
    {"name": "Inspect — process capability Cp / Cpk against spec limits", "family": "spc", "task": "measure",
     "task_class": "inspection", "halcon": None, "input_sort": "signal", "sample": "mx_process_sample",
     "stages": [{"op": "spc_capability", "kw": {"lsl": "$aux.lsl", "usl": "$aux.usl"}}],
     "expect": [{"get": ["cpk"], "between": ["cpk_lo", "cpk_hi"]}, {"get": ["cp"], "between": ["cp_lo", "cp_hi"]}],
     "note": "single stage on purpose: capability is computed straight from the individual measurements (no "
             "preprocessing belongs in front). Cp = (USL−LSL)/6σ, Cpk = min(USL−μ, μ−LSL)/3σ for 2,000 parts of a "
             "normal process; the gate is ± 3 sampling standard errors (Bissell 1990)."},
    {"name": "Inspect — X-bar / R control chart of subgrouped parts", "family": "spc", "task": "monitor",
     "task_class": "inspection", "halcon": None, "input_sort": "matrix", "sample": "mx_subgroups",
     "stages": [{"op": "spc_xbar_r"}],
     "expect": [{"get": ["xbar_cl"], "between": ["mean_lo", "mean_hi"]},
                {"get": ["r_cl"], "between": ["rbar_lo", "rbar_hi"]}],
     "note": "single stage on purpose: the Shewhart chart consumes the raw subgroup matrix (25 subgroups × 5 parts). "
             "Centre lines and ISO 8258 limits (A2, D3, D4); the mean range of N(μ, σ) subgroups of 5 is d2·σ = "
             "2.326σ; gates are ± 3 standard errors of the grand mean and of R̄ (d3 = 0.864)."},
    {"name": "Inspect — variation-model defect detection against good samples", "family": "spc", "task": "inspect",
     "task_class": "inspection", "halcon": "Inspection", "input_sort": "seq<image>", "sample": "mx_varmodel_stack",
     "stages": [{"op": "varmodel_fit", "kw": {"spread": "pooled"}},
                {"op": "varmodel_score", "args": ["$aux.test", "$prev"]}],
     "expect": [{"get": ["regions", 0, "area"], "approx": "area", "atol": 0.0}],
     "note": "HALCON-style variation model (train_variation_model / compare_variation_model): learn per-pixel centre "
             "and spread from 12 good images, then z-score a test image and group out-of-band pixels into defect "
             "regions (area px, peak z, polarity, bbox). The bright square defect is recovered exactly."},
    {"name": "Inspect — probability of detection a50 of an NDT method (â vs a)", "family": "spc",
     "task": "measure", "task_class": "inspection", "halcon": None, "input_sort": "table", "sample": "mx_pod_ahat",
     "stages": [{"op": "pod_ahat_fit"}, {"op": "pod_from_ahat", "kw": {"a_dec": "$aux.a_dec"}}],
     "expect": [{"get": ["a50"], "approx": "a50", "atol": 0.06}],
     "note": "MIL-HDBK-1823A signal-response POD: regress the inspection signal â on flaw size a (mm), then with "
             "the decision threshold â > 3 read the POD curve, a50, a90 and a90/95 — how small a crack the method "
             "finds reliably. Truth a50 = (3 − β0)/β1 of the simulated line (gate ≈ 3 standard errors, 60 flaws)."},
    # ---------------------------------------------------------------- conngraph
    {"name": "Analyze — algebraic connectivity of a neuron ring (Laplacian spectrum)", "family": "conngraph",
     "task": "measure", "task_class": "analysis", "halcon": None, "input_sort": "synapse_table",
     "sample": "mx_ring_synapses",
     "stages": [{"op": "graph_from_synapses"}, {"op": "graph_laplacian_spectrum"}],
     "expect": [{"get": [1], "approx": "lambda2", "atol": 1e-9}, {"get": [-1], "approx": "lambda_max", "atol": 1e-9}],
     "note": "turn a connectome synapse table (pre, post, count) into a weighted adjacency matrix, then the "
             "Laplacian eigenvalues of the undirected binary graph: zeros = components, λ2 = how well connected "
             "(Fiedler). Ring of n: 2 − 2cos(2πk/n)."},
    {"name": "Analyze — clusters of a connectome after pruning weak synapses", "family": "conngraph",
     "task": "count", "task_class": "analysis", "halcon": None, "input_sort": "synapse_table",
     "sample": "mx_cluster_synapses",
     "stages": [{"op": "graph_from_synapses"}, {"op": "graph_binarize", "kw": {"thresh": 1.0}},
                {"op": "graph_components"}],
     "expect": [{"get": ["@max"], "equals": "max_label"}],
     "note": "build the weighted graph, keep only synapses with count > 1 (drop spurious weak contacts), then "
             "label weakly connected components: the number of separate circuits (labels 0..k−1)."},
    # ---------------------------------------------------------------- graph
    {"name": "Measure — shortest route on a weighted network (slime-mould transport)", "family": "graph",
     "task": "plan", "task_class": "analysis", "halcon": None, "input_sort": "matrix", "sample": "mx_tube_graph",
     "stages": [{"op": "graph_physarum_path", "kw": {"source": 0, "sink": 5}}],
     "expect": [{"get": ["path_length"], "approx": "path_length", "atol": 1e-9}],
     "note": "single stage: the op takes the length matrix directly and returns the route. Physarum tube dynamics "
             "(Tero 2010) converge to the unique shortest path (Bonifaci 2012): node sequence, its length, the flow "
             "— a self-organising router / AGV path check on a symmetric length matrix."},
    {"name": "Analyze — count directed feedback triangles in a network", "family": "graph", "task": "count",
     "task_class": "analysis", "halcon": None, "input_sort": "matrix", "sample": "mx_triangles",
     "stages": [{"op": "graph_cycle3"}],
     "expect": [{"get": ["cycles3"], "equals": "cycles3"}],
     "note": "single stage: number of directed 3-cycles i→j→k→i = tr(B³)/3 of the binary adjacency — feedback "
             "loops in a dependency / signalling / wiring graph (deadlock rings in a resource graph)."},
    # ---------------------------------------------------------------- multivar
    {"name": "Analyze — response-surface optimum of a central composite experiment", "family": "multivar",
     "task": "optimize", "task_class": "analysis", "halcon": None, "input_sort": None, "sample": "mx_ccd_response",
     "stages": [{"op": "doe_central_composite", "kw": {"factors": 2, "center": 3}},
                {"op": "rsm_fit", "args": ["$prev", "$aux.y"]}],
     "expect": [{"get": ["stationary", "coded", 0], "approx": "xs0", "atol": 1e-6},
                {"get": ["stationary", "coded", 1], "approx": "xs1", "atol": 1e-6}],
     "note": "plan a rotatable central composite design (2 factors, 3 centre runs), run it (responses supplied), "
             "fit the quadratic response surface (ANOVA, lack of fit, R²) and read the stationary point in coded "
             "units — the process-optimisation loop of DOE / RSM."},
    {"name": "Analyze — global sensitivity (Sobol' indices) of a model", "family": "multivar", "task": "rank",
     "task_class": "analysis", "halcon": None, "input_sort": None, "sample": "mx_sobol_linear",
     "stages": [{"op": "doe_saltelli", "kw": {"n": 512, "factors": "$aux.factors", "seed": 0}},
                {"op": "sens_sobol", "args": ["$prev", "$aux.y"], "kw": {"n_boot": 50}}],
     "expect": [{"get": ["S1", 0], "approx": "s1_0", "atol": 0.03}, {"get": ["S1", 2], "approx": "s1_2", "atol": 0.03}],
     "note": "variance-based sensitivity: Saltelli sample matrices (Sobol' sequence, n = 512, 3 factors), the "
             "model output on them, then first-order and total Sobol' indices with bootstrap intervals — which "
             "input tolerances drive the output variance. Linear model: S1_i = a_i²/Σa²."},
    {"name": "Analyze — principal components and explained variance of multivariate data", "family": "multivar",
     "task": "reduce", "task_class": "analysis", "halcon": None, "input_sort": "matrix", "sample": "mx_aniso_samples",
     "stages": [{"op": "mv_pca", "kw": {"standardize": False, "n_parallel": 50, "seed": 0}}],
     "expect": [{"get": ["eigenvalues", 0], "approx": "ev0", "rtol": 1e-9},
                {"get": ["explained_ratio", 0], "approx": "ratio0", "rtol": 1e-9}],
     "note": "single stage: PCA consumes the samples × variables table directly. SVD of the centred data → scores, "
             "loadings, eigenvalues (covariance), explained-variance ratio and three answers to 'how many "
             "components' (cumulative, Horn parallel analysis, MDL). Sample covariance is exactly R·diag(σ²)·Rᵀ."},
    # ---------------------------------------------------------------- emproof
    {"name": "Inspect — score a segmentation split error (variation of information)", "family": "emproof",
     "task": "evaluate", "task_class": "inspection", "halcon": None, "input_sort": "labels2d",
     "sample": "mx_seg_labels",
     "stages": [{"op": "seg_inject_split", "kw": {"n": 1, "min_area": 1000, "axis": "row"}},
                {"op": "seg_variation_of_information", "args": ["$in", "$prev"]}],
     "expect": [{"get": ["split"], "approx": "split_bits", "atol": 1e-9}, {"get": ["merge"], "approx": 0.0, "atol": 1e-9}],
     "note": "proof-reading benchmark for cell / neuron segmentation (EM): inject a known split of the largest cell "
             "at its median row, then the variation of information between truth and candidate in bits — the split "
             "term H(b|a) equals the cut cell's area fraction (equal halves = 1 bit each pixel), merge stays 0."},
    # ---------------------------------------------------------------- videostream
    {"name": "Inspect — detect a scene cut in a noisy video stream", "family": "videostream", "task": "detect",
     "task_class": "inspection", "halcon": None, "input_sort": "seq<image>", "sample": "mx_scene_cut_clip",
     "stages": [{"op": "temporal_bilateral", "kw": {"window": 3, "sigma_t": 2.0, "sigma_r": 0.1}},
                {"op": "scene_cut_detection", "kw": {"bins": 32, "threshold": 0.3}}],
     "expect": [{"get": ["distance", "@argmax"], "equals": "cut"}],
     "note": "causal temporal bilateral denoising (edge-preserving in time, no ghosting across the cut) then the "
             "chi-square histogram distance between consecutive frames: the shot boundary / camera switch / "
             "occluded-lens frame index in a monitoring stream."},
    {"name": "Inspect — moving object mask in a flickering video (deflicker + background model)",
     "family": "videostream", "task": "segment", "task_class": "inspection", "halcon": None,
     "input_sort": "seq<image>", "sample": "mx_flicker_clip",
     "stages": [{"op": "deflicker"}, {"op": "running_gaussian_foreground", "kw": {"alpha": 0.05, "k": 4.0, "var_init": 1e-4}}],
     "expect": [{"get": [-1, "@sum"], "approx": "area", "atol": 2.0}],
     "note": "mains-lamp flicker (±6 % global gain per frame) makes a background model fire everywhere; deflicker "
             "normalises frame brightness first, then the per-pixel running Gaussian (Wren Pfinder) marks only the "
             "moving part. Output: 0/1 masks per frame; last-frame area in px."},
    # ---------------------------------------------------------------- simcal
    {"name": "Calibrate — camera gain from a captured test chart (simulation calibration)", "family": "simcal",
     "task": "calibrate", "task_class": "simulation", "halcon": "Calibration", "input_sort": None,
     "sample": "mx_simcal_gain",
     "stages": [{"op": "simcal_model", "kw": {"chain": "$aux.chain", "knobs": "$aux.knobs", "scene": "$aux.scene",
                                               "noise": "$aux.noise"}},
                {"op": "simcal_observe", "args": ["$prev", "$aux.images"]},
                {"op": "simcal_fit"}, {"op": "simcal_report"}],
     "expect": [{"get": ["$s3", "theta_hat", "gain"], "approx": "gain", "rtol": 0.01}],
     "note": "fit a forward simulation (chart → gain/offset, EMVA 1288 noise model) to a real-looking capture: build "
             "the model with its knob (gain, DN, log range), attach the observed image, weighted least squares with "
             "identifiability gates, then the report table (value, interval, class, gates)."},
    # ---------------------------------------------------------------- llmcore
    {"name": "Analyze — attention as a key-value lookup (RMSNorm → scores → softmax → mix)", "family": "llmcore",
     "task": "compute", "task_class": "analysis", "halcon": None, "input_sort": "tokens",
     "sample": "mx_attention_lookup",
     "stages": [{"op": "rms_norm"}, {"op": "attention_scores", "args": ["$prev", "$aux.key"], "kw": {"scale": 4.0}},
                {"op": "attention_weights"}, {"op": "attention_apply", "args": ["$prev", "$aux.value"]}],
     "expect": [{"get": [2, 1], "approx": "v21", "atol": 1e-3}, {"get": [4, 3], "approx": "v43", "atol": 1e-3}],
     "note": "the transformer attention kernel written out stage by stage: RMS-normalise the query tokens (T, d), "
             "scaled dot-product scores against the keys, row softmax, convex mix of the values. With one-hot "
             "queries/keys a sharp softmax must copy value row i — the retrieval sanity check."},
    # ---------------------------------------------------------------- converge
    {"name": "Measure — observed order of convergence of a grid study (GCI)", "family": "converge",
     "task": "verify", "task_class": "simulation", "halcon": None, "input_sort": None, "sample": "mx_grid_study",
     "stages": [{"op": "conv_observed_order", "kw": {"phi": "$aux.phi", "h": "$aux.h"}}],
     "expect": [{"get": ["p"], "approx": "p", "rtol": 1e-6}],
     "note": "single stage: the op takes the three grid solutions directly. Celik et al. 2008 (ASME V&V) apparent "
             "order p from solutions on fine/medium/coarse grids (cell size h) — verifies a simulation converges at "
             "its design order before results are trusted."},
    {"name": "Measure — fixed point of an iteration with convergence proof (Anderson)", "family": "converge",
     "task": "solve", "task_class": "simulation", "halcon": None, "input_sort": None, "sample": "mx_babylonian",
     "stages": [{"op": "iterate_fixed_point", "kw": {"g": "$aux.g", "x0": "$aux.x0", "method": "anderson"}}],
     "expect": [{"get": ["x"], "approx": "root", "atol": 1e-8}],
     "note": "single stage: the iteration map is the input. Solve x = g(x) with Anderson acceleration, refusing "
             "divergence / stagnation, and report the residual history and an a-posteriori error bound — any "
             "self-consistent loop (interreflection, coupled sensors). Heron's map converges to √c."},
]

MISSING_OPS = [
    {"family": "oned", "need": "spectrum peak picker: pairs (freqs, magnitude) -> measurement (peak frequency in Hz, "
                               "sub-bin interpolated)",
     "why": "spectrum returns the typed pairs (freqs, |rfft|) but every peak op (find_peaks, peak_subbin) takes a "
            "signal; the FFT-peak chain spectrum -> peak cannot be typed, so the recipe reads peak_freq from "
            "signal_features instead (bin-quantised, no sub-bin refinement)."},
    {"family": "drive", "need": "table field selector (table -> image / signal / scalar, by key)",
     "why": "dict-returning drive ops cannot feed their natural consumers: flow_from_depth_motion -> {u, v} cannot "
            "reach ttc_from_flow(u: image, v: image) or foe_from_flow; label_extent -> {width} cannot reach "
            "ttc_from_scale(w0, w1). A generic typed 'get field' op would close all of these."},
]

FAILED_ATTEMPTS = [
    {"family": "drive", "recipe": "Sense — TTC from optical flow (flow_from_depth_motion -> ttc_from_flow)",
     "op": "ttc_from_flow", "error": "flow_from_depth_motion outputs table {u, v, valid, depth1}; ttc_from_flow "
                                     "inputs ['image', 'image'] — no op selects a table field as an image. Via the ledger too: "
                                     "fs.ledger.ttc_from_flow(flow_table, dt=0.1) -> TypeError: missing 1 required "
                                     "positional argument: 'v'",
     "cause": "type_gap"},
    {"family": "drive", "recipe": "Sense — TTC from apparent size growth (label_extent -> ttc_from_scale)",
     "op": "ttc_from_scale", "error": "label_extent outputs table {width, height, ...}; ttc_from_scale is declared a "
                                      "generator (inputs []) taking w0, w1 as scalar keywords. Via the ledger: "
                                      "fs.ledger.ttc_from_scale(extent_table, dt=0.1) -> TypeError: missing 1 "
                                      "required positional argument: 'w1'",
     "cause": "type_gap"},
    {"family": "oned", "recipe": "Sense — FFT peak frequency (spectrum -> find_peaks -> peak_subbin)",
     "op": "find_peaks", "error": "spectrum outputs pairs (freqs, magnitude); find_peaks / peak_subbin input "
                                  "'signal' — type cut at stage 2. Via the ledger: fs.ledger.find_peaks(spectrum(...)) -> "
                                  "ValueError: expected a 1-D signal ..., got shape (129, 2)",
     "cause": "type_gap"},
]


#: 本ごとの日本語ノート(この本で足したレシピ。notes_ja.py の表と合わせて引く)。
NOTES_JA = {
    "Measure — RSS minimum safe gap behind a braking lead car (rss_params -> rss_longitudinal_same)":
        "RSS の同方向の最小安全距離 — 前の車が最大の制動で止まっても、後ろの車が反応時間 ρ のあいだ加速してから"
        "制動して止まれる車間 [m](Shalev-Shwartz 2017 の Lemma 2、ad-rss-lib の保守的な定数)。"
        "パラメータの表を第 1 引数に、速さを名前つきで渡す。真値は閉形式。",
}
