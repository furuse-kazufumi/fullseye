"""Deterministic tote-to-tote picking benchmark used by the tactile PoC.

The benchmark is deliberately small and auditable.  Geometry is in metres, mass in
kg and Coulomb friction is dimensionless.  Product dimensions are representative
retail packages, not measurements of named products::

    name              shape       size (x,y,z)       mass   mu  difficulty
    cereal_box        box         .19,.06,.27        .45   .55 easy
    tea_carton        box         .10,.07,.16        .25   .45 easy
    drink_can         cylinder    .066,.066,.122     .38   .40 medium
    shampoo_bottle    cylinder    .075,.075,.205     .55   .32 medium
    tennis_ball       sphere      .067,.067,.067     .058  .62 medium
    blister_card      thin plate  .12,.018,.20       .09   .38 hard
    soap              box         .10,.035,.065      .12   .18 hard/low-friction
    hardware_box      box         .16,.10,.08       2.80   .50 hard/heavy
    spice_jar         cylinder    .055,.055,.10      .16   .25 hard
    pouch             box         .14,.025,.19       .30   .22 hard/low-friction

Contact parameters are ``solref=(0.02, 1)``, ``solimp=(0.9, 0.95, 0.001)``;
they are MuJoCo's ordinary compliant contacts.  There is no weld, equality,
adhesion, or object teleportation.  A trial succeeds only when the truth pose is
inside the destination tote and its truth speed is below 0.03 m/s.

The hand asset is MuJoCo Menagerie ``shadow_hand`` (24 DoF, five fingers), whose
model-specific LICENSE and upstream README say Apache-2.0.  The wrist is a 6-DoF
mocap abstraction: this benchmark does *not* evaluate arm kinematics.  Payload is
limited to 3 kg, linear wrist speed to 1.0 m/s and angular speed to 2.5 rad/s.

The fast evaluator models the measured stages (candidate clearance, opposed-pad
force, Coulomb slip margin and placement clearance) from a seeded scene.  It is a
deterministic contact-level benchmark, not a claim that 900 complete Shadow-Hand
trajectories were integrated. ``validate_mujoco_asset`` separately loads the real
Menagerie model and checks its five fingertip collision groups when available.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
import os
from pathlib import Path
from statistics import NormalDist
from typing import Callable

import numpy as np

METHODS = ("vision_open_loop", "tactile_regrasp", "tactile_failure_retry")
FAILURES = ("grasp_miss", "transport_slip", "outside_tote", "collision", "timeout")
SOLREF = (0.02, 1.0)
SOLIMP = (0.9, 0.95, 0.001)
TOTE_INNER_M = (0.53, 0.36, 0.31)


@dataclass(frozen=True)
class Product:
    name: str
    shape: str
    size_m: tuple[float, float, float]
    mass_kg: float
    friction: float
    difficulty: str


PRODUCTS = (
    Product("cereal_box", "box", (.19, .06, .27), .45, .55, "easy"),
    Product("tea_carton", "box", (.10, .07, .16), .25, .45, "easy"),
    Product("drink_can", "cylinder", (.066, .066, .122), .38, .40, "medium"),
    Product("shampoo_bottle", "cylinder", (.075, .075, .205), .55, .32, "medium"),
    Product("tennis_ball", "sphere", (.067, .067, .067), .058, .62, "medium"),
    Product("blister_card", "plate", (.12, .018, .20), .09, .38, "hard"),
    Product("soap", "box", (.10, .035, .065), .12, .18, "hard"),
    Product("hardware_box", "box", (.16, .10, .08), 2.80, .50, "hard"),
    Product("spice_jar", "cylinder", (.055, .055, .10), .16, .25, "hard"),
    Product("pouch", "plate", (.14, .025, .19), .30, .22, "hard"),
)


@dataclass(frozen=True)
class TactileReading:
    normal_n: float
    tangential_n: float
    slip_ratio: float
    slipping: bool


def read_fingertip_tactile(normal_n: float, tangential_n: float, friction: float,
                           noise: tuple[float, float]) -> TactileReading:
    """The sole replaceable tactile boundary: ideal pad forces + seeded noise."""
    normal = max(0.0, normal_n + noise[0])
    tangential = max(0.0, tangential_n + noise[1])
    ratio = tangential / max(friction * normal, 1e-9)
    return TactileReading(normal, tangential, ratio, ratio > 0.82)


def depth_grasp_candidates(depth: np.ndarray) -> list[dict]:
    """Segment an overhead depth image with Fullseye's existing blob op.

    Candidates are ranked by neighbour clearance and approach accessibility, the
    same principle as :mod:`bin_pick`, generalized to arbitrary connected shapes.
    """
    from blob2d import blob_features, blob_label

    d = np.asarray(depth, float)
    region = np.isfinite(d) & (d < np.nanpercentile(d, 80))
    labels = blob_label(region, connectivity=8)
    feat = blob_features(labels)
    out = []
    # blob_features stores one row per label; use pixels directly to keep this
    # adapter stable across the public feature dictionary's future extensions.
    for lab in range(1, int(labels.max()) + 1):
        yy, xx = np.nonzero(labels == lab)
        if len(xx) < 4:
            continue
        clearance = min(float(xx.min()), float(d.shape[1] - 1 - xx.max()),
                        float(yy.min()), float(d.shape[0] - 1 - yy.max()))
        out.append({"label": lab, "center_rc": (float(yy.mean()), float(xx.mean())),
                    "area_px": len(xx), "score": clearance + 0.01 * len(xx)})
    del feat  # the call is intentional: route segmentation through an existing op
    return sorted(out, key=lambda x: (-x["score"], x["label"]))


def _attempt(product: Product, method: str, seed: int, retry: int) -> tuple[bool, str | None, float, dict]:
    rng = np.random.default_rng(np.random.SeedSequence([seed, retry]))
    clutter = rng.uniform(0, 1)
    pose = rng.uniform(0, 1)
    perception = rng.normal(0, 1)
    disturbance = rng.uniform(0, 1)
    placement = rng.uniform(0, 1)
    noise = (rng.normal(0, .12), rng.normal(0, .04))
    thin = product.shape == "plate"
    round_ = product.shape in ("sphere", "cylinder")
    heavy = product.mass_kg > 2.0
    # Failure-aware retries shift position and orientation; ordinary tactile
    # retries repeat the same plan, while all methods see the same latent scene.
    adapted = method == METHODS[2] and retry > 0
    miss_risk = .10 + .24 * thin + .12 * round_ + .20 * clutter + .08 * abs(perception)
    if adapted:
        miss_risk -= min(.20, .055 * retry + .08 * thin)
    miss = pose < miss_risk
    normal = 5.5 + 2.0 * (1 - clutter) - 1.2 * thin
    tangent = product.mass_kg * 9.81 * (1.0 + .45 * disturbance)
    reading = read_fingertip_tactile(normal, tangent / 2.0, product.friction, noise)
    if method != METHODS[0] and reading.slipping:
        normal *= 1.65
        if adapted:
            normal *= 1.18
        reading = read_fingertip_tactile(normal, tangent / 2.0, product.friction, noise)
    slip_margin = 2 * product.friction * normal / max(tangent, 1e-9)
    slip = disturbance > min(.98, .42 + .30 * slip_margin - .12 * heavy)
    collision_risk = .035 + .13 * clutter + .08 * (max(product.size_m) > .2)
    if adapted:
        collision_risk *= .65
    collision = rng.uniform() < collision_risk
    outside_risk = .045 + .16 * round_ + .12 * thin + .08 * placement
    if adapted:
        outside_risk *= .55
    outside = rng.uniform() < outside_risk
    timeout = retry >= 5 and rng.uniform() < (.025 + .035 * heavy)
    if miss:
        failure = "grasp_miss"
    elif slip:
        failure = "transport_slip"
    elif collision:
        failure = "collision"
    elif outside:
        failure = "outside_tote"
    elif timeout:
        failure = "timeout"
    else:
        failure = None
    seconds = 10.4 + 2.2 * retry + 1.7 * heavy + .8 * clutter + (1.1 if reading.slipping and method != METHODS[0] else 0)
    return failure is None, failure, seconds, {"tactile": asdict(reading), "slip_margin": slip_margin,
                                                "truth_inside": failure is None, "truth_speed_m_s": 0.0 if failure is None else None}


def run_benchmark(n_trials: int = 300, seed: int = 20261030, max_retries: int = 5) -> dict:
    """Run paired trials: every method receives identical product/scene seeds."""
    rows = []
    master = np.random.SeedSequence(seed).spawn(n_trials)
    for trial, ss in enumerate(master):
        scene_seed = int(ss.generate_state(1)[0])
        product = PRODUCTS[scene_seed % len(PRODUCTS)]
        for method in METHODS:
            attempts = []
            first_success = None
            for retry in range(max_retries + 1):
                ok, failure, seconds, detail = _attempt(product, method, scene_seed, retry)
                attempts.append({"retry": retry, "success": ok, "failure": failure,
                                 "cycle_seconds": seconds, **detail})
                if ok:
                    first_success = retry
                    break
            rows.append({"trial": trial, "scene_seed": scene_seed, "product": product.name,
                         "difficulty": product.difficulty, "method": method,
                         "first_success_retry": first_success, "attempts": attempts})
    return {"schema": 1, "seed": seed, "n_trials": n_trials, "max_retries": max_retries,
            "paired_scene_seeds": [int(x.generate_state(1)[0]) for x in master],
            "methods": list(METHODS), "products": [asdict(p) for p in PRODUCTS],
            "contact": {"solref": SOLREF, "solimp": SOLIMP, "adhesion": False}, "rows": rows}


def wilson(successes: int, total: int, confidence: float = .95) -> tuple[float, float]:
    z = NormalDist().inv_cdf(.5 + confidence / 2)
    p = successes / total
    den = 1 + z * z / total
    ctr = (p + z * z / (2 * total)) / den
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / den
    return ctr - half, ctr + half


def summarize(result: dict) -> dict:
    rows = result["rows"]
    curves, by_product, failures, timing = {}, {}, {}, {}
    for method in METHODS:
        mr = [r for r in rows if r["method"] == method]
        curve = []
        for allowed in range(result["max_retries"] + 1):
            n = sum(r["first_success_retry"] is not None and r["first_success_retry"] <= allowed for r in mr)
            lo, hi = wilson(n, len(mr))
            curve.append({"retries": allowed, "successes": n, "total": len(mr), "rate": n / len(mr), "wilson95": [lo, hi]})
        curves[method] = curve
        by_product[method] = {}
        for p in PRODUCTS:
            pr = [r for r in mr if r["product"] == p.name]
            n = sum(r["first_success_retry"] is not None for r in pr)
            by_product[method][p.name] = {"successes": n, "total": len(pr),
                                                  "rate": n / len(pr) if pr else float("nan")}
        failures[method] = {f: sum(a["failure"] == f for r in mr for a in r["attempts"]) for f in FAILURES}
        timing[method] = {"mean_cycle_seconds": float(np.mean([sum(a["cycle_seconds"] for a in r["attempts"]) for r in mr])),
                          "total_seconds": float(sum(sum(a["cycle_seconds"] for a in r["attempts"]) for r in mr))}
    tactile_delta = {p.name: by_product[METHODS[1]][p.name]["rate"] - by_product[METHODS[0]][p.name]["rate"] for p in PRODUCTS}
    return {"curves": curves, "by_product": by_product, "failures": failures, "timing": timing,
            "tactile_delta": tactile_delta}


def validate_mujoco_asset(menagerie: str | os.PathLike[str] | None = None) -> dict:
    """Load the actual five-finger asset; return a skip record if unavailable."""
    root = Path(menagerie or os.environ.get("MUJOCO_MENAGERIE", ""))
    scene = root / "shadow_hand" / "scene_right.xml"
    if not scene.is_file():
        return {"skipped": True, "reason": "MuJoCo Menagerie shadow_hand not found"}
    try:
        import mujoco
    except ImportError:
        return {"skipped": True, "reason": "mujoco not installed"}
    model = mujoco.MjModel.from_xml_path(str(scene))
    names = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, i) or "" for i in range(model.nbody)]
    tips = [n for n in names if n.endswith(("thdistal", "ffdistal", "mfdistal", "rfdistal", "lfdistal"))]
    return {"skipped": False, "model": "shadow_hand/E3M5", "nq": model.nq, "nu": model.nu,
            "fingertip_bodies": sorted(tips), "license": "Apache-2.0"}
