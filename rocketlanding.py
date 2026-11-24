# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Two-stage reusable-rocket landing world used by ``poc_rocket_landing``.

The world deliberately separates the simulator truth from the image measurement.
MuJoCo advances two generic stages and supplies the truth state; RGB frames from
two *fixed* calibrated cameras are the only input to :func:`measure_from_rgb`.
The controller is a bounded PID / closed-form braking rule, never a learned
policy.

物理の仮定 / physical assumptions
--------------------------------
* The first-stage and upper-stage dimensions are a generic dimension table,
  not a model of a real vehicle: 6.0 m and 4.0 m long, both 1.5 m diameter.
* The first stage is a rigid body.  It has a dry mass of 12 kg and propellant
  is consumed at ``T/(Isp*g0)``; its MuJoCo body mass and inertia are updated
  each step.  No slosh, plume impingement, structural flex, or ablation is
  modelled.
* Wind is a deterministic horizontal force, not CFD.  It has a seed-fixed
  slowly varying part and a seeded low-frequency perturbation.  The rendered
  flame is a visual proxy for the thrust vector, not combustion radiation.
* The pad is rigid with soft MuJoCo contact.  Aerodynamic drag is deliberately
  omitted so that the controller and its limits can be checked independently.

All public functions fail closed on malformed inputs where applicable.  The
numbers are intentionally small enough for a deterministic CI run; they are
not a claim about the performance of any real launch system.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import numpy as np

import camera
import calib
import measure


G0 = 9.80665
DT = 0.01
DRY_MASS = 12.0
NOMINAL_FUEL = 5.4
ISP_S = 55.0
BODY_LENGTH = 6.0
BODY_RADIUS = 0.75
PAD_RADIUS = 4.0
# The demonstrator's deliberately modest landing envelope.  It is a PoC gate,
# not a certification limit for a real vehicle.
SUCCESS_SPEED_MPS = 4.0
SUCCESS_TILT_DEG = 25.0
SUCCESS_OFFSET_M = 2.5


@dataclass(frozen=True)
class Case:
    """One deterministic launch case / 1 回の固定条件。

    ``kind`` is either ``"nominal"``, ``"fuel_shortage"`` or
    ``"strong_wind"``.  It is deliberately an explicit finite vocabulary so
    a spelling error cannot silently turn a failure case into a nominal one.
    """

    kind: str
    seed: int
    fuel_kg: float
    wind_n: float


def case_spec(kind: str, seed: int) -> Case:
    """Return a seed-fixed case specification / 条件名を固定の物理条件へ写す。

    Raises
    ------
    ValueError
        If ``kind`` is not one of the three documented cases or ``seed`` is
        not an integer.  Failure cases are intentional test stimuli: depleted
        propellant and a wind force beyond the controller's lateral authority.
    """
    if not isinstance(seed, (int, np.integer)):
        raise ValueError("case_spec: seed must be an integer")
    table = {
        "nominal": (NOMINAL_FUEL, 12.0),
        "fuel_shortage": (0.45, 12.0),
        "strong_wind": (NOMINAL_FUEL, 190.0),
    }
    if kind not in table:
        raise ValueError("case_spec: kind must be nominal, fuel_shortage, or strong_wind")
    fuel, wind = table[kind]
    return Case(kind, int(seed), fuel, wind)


def propellant_step(fuel_kg: float, thrust_n: float, dt: float = DT,
                    isp_s: float = ISP_S) -> tuple[float, float]:
    """Consume propellant without going negative / 推力から燃料消費を積分する。

    Returns ``(fuel_after_kg, delivered_thrust_n)``.  The requested thrust is
    clipped by the propellant left in this timestep, so an empty tank returns
    exactly zero rather than a negative mass or a fictitious partial state.
    This is the fuel/mass invariant used by the PoC and unit tests.
    """
    vals = (fuel_kg, thrust_n, dt, isp_s)
    if not all(np.isfinite(v) for v in vals) or fuel_kg < 0 or thrust_n < 0 or dt <= 0 or isp_s <= 0:
        raise ValueError("propellant_step: fuel, thrust, dt, and isp must be finite; fuel/thrust >= 0 and dt/isp > 0")
    if fuel_kg == 0.0 or thrust_n == 0.0:
        return float(fuel_kg), 0.0
    requested = thrust_n / (isp_s * G0) * dt
    used = min(float(fuel_kg), requested)
    delivered = float(thrust_n) * (used / requested)
    return float(fuel_kg - used), delivered


def free_fall_state(z0_m: float, vz0_mps: float, t_s: float) -> tuple[float, float]:
    """Closed-form zero-thrust vertical state / 推力ゼロの自由落下の真値。

    It is intentionally separate from MuJoCo and is the independent invariant:
    ``z=z0+v0*t-g*t²/2`` and ``vz=v0-g*t``.  The actual MuJoCo check is done
    before ground contact, so contact impulses cannot hide an incorrect gate.
    """
    if not all(np.isfinite(v) for v in (z0_m, vz0_mps, t_s)) or t_s < 0:
        raise ValueError("free_fall_state: inputs must be finite and t_s >= 0")
    return float(z0_m + vz0_mps * t_s - 0.5 * G0 * t_s * t_s), float(vz0_mps - G0 * t_s)


def fixed_wind(seed: int, t_s: float, scale_n: float) -> np.ndarray:
    """Seed-fixed horizontal wind force / seed で固定した水平風力[N]。

    A three-coefficient pseudo-random vector is drawn only from ``seed`` and
    evaluated as smooth sines of time.  Repeated calls with the same inputs are
    bit-identical.  It is a force on the simplified body, not an aerodynamic
    coefficient or a weather prediction.
    """
    if not isinstance(seed, (int, np.integer)) or not all(np.isfinite(v) for v in (t_s, scale_n)) or scale_n < 0:
        raise ValueError("fixed_wind: seed must be integer; time finite; scale_n >= 0")
    rng = np.random.default_rng(int(seed))
    phase = rng.uniform(-math.pi, math.pi, 4)
    ax = 0.65 * math.sin(0.37 * t_s + phase[0]) + 0.35 * math.sin(0.91 * t_s + phase[1])
    ay = 0.65 * math.cos(0.31 * t_s + phase[2]) + 0.35 * math.sin(0.73 * t_s + phase[3])
    return float(scale_n) * np.array([ax, ay, 0.0], dtype=float)


def _unit(v: np.ndarray, fallback: np.ndarray | None = None) -> np.ndarray:
    n = float(np.linalg.norm(v))
    if n <= 1e-12:
        if fallback is None:
            raise ValueError("zero direction")
        return np.asarray(fallback, dtype=float).copy()
    return np.asarray(v, dtype=float) / n


def _look_xyaxes(position: np.ndarray, target: np.ndarray) -> np.ndarray:
    """MuJoCo camera x/y axes looking from position to target / 固定カメラの姿勢。"""
    forward = _unit(target - position)
    right = _unit(np.cross(forward, np.array([0.0, 0.0, 1.0])), np.array([1.0, 0.0, 0.0]))
    up = _unit(np.cross(right, forward))
    return np.r_[right, up]


def scene_mjcf() -> str:
    """Build the self-contained generic two-stage MJCF / 一般的な二段機の MJCF。

    Cylinders and dimensioned bands are used for both stages; there are no box
    or sphere stand-ins for the vehicles.  The green pad centre, cyan booster,
    yellow nose band, magenta engine band and red-orange flame are deliberately
    separated RGB cues for the vision measurement.  Those colours are a
    simulator instrument, not a statement about paint or real exhaust.
    """
    gcam_p = np.array([34.0, -72.0, 31.0])
    pcam_p = np.array([-39.0, -58.0, 25.0])
    # A single fixed wide view must include both separation (~60 m) and the
    # pad (0 m); it is not a hidden tracking camera.
    target = np.array([0.0, 0.0, 34.0])
    ga = " ".join(f"{x:.8f}" for x in _look_xyaxes(gcam_p, target))
    pa = " ".join(f"{x:.8f}" for x in _look_xyaxes(pcam_p, target))
    return f"""
<mujoco model="generic_reusable_two_stage">
  <compiler angle="radian" coordinate="local"/>
  <option timestep="{DT}" integrator="implicitfast" gravity="0 0 -9.80665"/>
  <visual><quality shadowsize="2048" offsamples="0"/><map znear="0.05" zfar="180"/><headlight ambient="0.42 0.42 0.42" diffuse="0.72 0.72 0.72" specular="0.10 0.10 0.10"/></visual>
  <default><geom friction="1.2 0.02 0.005" solref="0.018 1" solimp="0.95 0.99 0.002"/></default>
  <worldbody>
    <light name="key" directional="true" dir="-0.35 0.20 -1" diffuse="0.80 0.80 0.80"/>
    <geom name="ground" type="plane" size="120 120 1" rgba="0.07 0.09 0.13 1"/>
    <geom name="landing_pad" type="cylinder" size="{PAD_RADIUS} 0.18" pos="0 0 -0.18" rgba="0.28 0.31 0.35 1"/>
    <geom name="pad_mark" type="cylinder" size="0.52 0.012" pos="0 0 0.012" rgba="0.08 0.90 0.18 1" contype="0" conaffinity="0"/>
    <body name="booster" pos="0 0 54">
      <freejoint name="booster_free"/>
      <inertial pos="0 0 3" mass="17.4" diaginertia="20 20 1.8"/>
      <geom name="booster_tank" type="cylinder" size="0.75 2.65" pos="0 0 2.65" rgba="0.04 0.65 0.94 1"/>
      <geom name="booster_nose_marker" type="cylinder" size="0.77 0.22" pos="0 0 5.55" rgba="0.96 0.78 0.04 1" contype="0" conaffinity="0"/>
      <geom name="booster_engine_marker" type="cylinder" size="0.80 0.18" pos="0 0 0.18" rgba="0.98 0.03 0.03 1" contype="0" conaffinity="0"/>
      <geom name="flame" type="cylinder" size="0.24 0.4" pos="0 0 -0.4" rgba="1 0.42 0.01 0" contype="0" conaffinity="0"/>
    </body>
    <body name="upper_stage" pos="0 0 60.15">
      <freejoint name="upper_free"/>
      <inertial pos="0 0 2" mass="5.4" diaginertia="4 4 0.5"/>
      <geom name="upper_tank" type="cylinder" size="0.56 1.82" pos="0 0 1.82" rgba="0.46 0.16 0.76 1"/>
      <geom name="upper_nose" type="cylinder" size="0.30 0.28" pos="0 0 3.92" rgba="0.72 0.56 0.94 1"/>
    </body>
    <camera name="ground_tracking_camera" pos="{' '.join(map(str, gcam_p))}" xyaxes="{ga}" fovy="56"/>
    <camera name="pad_camera" pos="{' '.join(map(str, pcam_p))}" xyaxes="{pa}" fovy="58"/>
  </worldbody>
</mujoco>
""".strip()


def _quat_from_z(direction: np.ndarray) -> np.ndarray:
    """Quaternion rotating local +Z to direction / 噴射柱の局所姿勢。"""
    z = np.array([0.0, 0.0, 1.0])
    d = _unit(np.asarray(direction, float))
    c = float(np.clip(z @ d, -1.0, 1.0))
    if c > 1.0 - 1e-12:
        return np.array([1.0, 0.0, 0.0, 0.0])
    if c < -1.0 + 1e-12:
        return np.array([0.0, 1.0, 0.0, 0.0])
    a = _unit(np.cross(z, d))
    half = 0.5 * math.acos(c)
    return np.r_[math.cos(half), math.sin(half) * a]


def _camera_calibrations(model: Any, data: Any, width: int, height: int) -> dict[str, dict[str, np.ndarray]]:
    """Read fixed MuJoCo cameras as Fullseye calibrated cameras / 校正値を取り出す。"""
    out = {}
    flip = np.diag([1.0, -1.0, -1.0])
    for name in ("ground_tracking_camera", "pad_camera"):
        cid = int(model.camera(name).id)
        Rwc = np.asarray(data.cam_xmat[cid], float).reshape(3, 3)
        pos = np.asarray(data.cam_xpos[cid], float).copy()
        R = flip @ Rwc.T
        t = -R @ pos
        f = 0.5 * height / math.tan(math.radians(float(model.cam_fovy[cid])) / 2.0)
        K = camera.intrinsic_matrix(f, f, (width - 1) / 2.0, (height - 1) / 2.0)
        out[name] = {"K": K, "R": R, "t": t, "P": camera.projection_matrix(K, R, t)}
    return out


def _mask_rgb(image: np.ndarray, label: str) -> np.ndarray:
    """Segment an instrument colour from RGB / RGB 映像だけから色を閾値分割する。"""
    x = np.asarray(image, np.float32) / 255.0
    r, g, b = x[..., 0], x[..., 1], x[..., 2]
    if label == "booster":
        return (g > 0.26) & (b > 0.34) & (g > 1.28 * r) & (b > 1.35 * r)
    if label == "nose":
        return (r > 0.48) & (g > 0.34) & (r > 1.35 * b) & (g > 1.35 * b)
    if label == "engine":
        return (r > 0.28) & (r > 1.65 * g) & (r > 1.35 * b)
    if label == "flame":
        return (r > 0.42) & (g > 0.08) & (r > 1.20 * g) & (r > 2.2 * b)
    if label == "pad":
        return (g > 0.30) & (g > 1.40 * r) & (g > 1.35 * b)
    raise ValueError("_mask_rgb: unknown label")


def _centroid_uv(mask: np.ndarray, min_pixels: int = 4) -> np.ndarray:
    """Return a mask centroid as (u,v), or NaNs / 領域重心を画素座標へ。"""
    rr, cc = np.nonzero(mask)
    if len(rr) < min_pixels:
        return np.array([np.nan, np.nan])
    return np.array([float(cc.mean()), float(rr.mean())])


def _triangulate_pair(a: np.ndarray, b: np.ndarray, cams: dict[str, dict[str, np.ndarray]]) -> np.ndarray:
    """Triangulate one RGB correspondence using Fullseye / 2視点DLTで3次元化。"""
    if not (np.isfinite(a).all() and np.isfinite(b).all()):
        return np.full(3, np.nan)
    return camera.triangulate(a[None], b[None], cams["ground_tracking_camera"]["P"], cams["pad_camera"]["P"])[0]


def _tilt_deg(axis: np.ndarray) -> float:
    """Return unsigned tilt from vertical / 鉛直からの傾き[deg]。"""
    a = _unit(np.asarray(axis, float))
    return float(math.degrees(math.atan2(float(np.linalg.norm(a[:2])), abs(float(a[2])))))


def _line_angle_error_deg(points: np.ndarray, truth_uv0: np.ndarray, truth_uv1: np.ndarray) -> float:
    """Fit a Fullseye TLS line and compare its undirected image angle / 炎の向き誤差。"""
    if len(points) < 2 or not (np.isfinite(truth_uv0).all() and np.isfinite(truth_uv1).all()):
        return float("nan")
    line = measure.fit_line(points)
    est = float(line["angle_deg"])
    d = truth_uv1 - truth_uv0
    ref = math.degrees(math.atan2(d[1], d[0]))
    return abs(((est - ref + 90.0) % 180.0) - 90.0)


def _annotate_frame(frame: np.ndarray, meas: dict[str, np.ndarray], t_s: float, kind: str) -> np.ndarray:
    """Overlay only measured RGB results / 真値を重ねずに計測結果だけを描く。"""
    import annotate as an

    img = np.asarray(frame, np.float64) / 255.0
    for key, colour in (("booster", "right"), ("nose", "emphasis"), ("engine", "wrong")):
        uv = meas[key]
        if np.isfinite(uv).all():
            img = np.asarray(an.crosshair(img, (float(uv[0]), float(uv[1])), color=colour, width=2, gap=3, extent=10))
    txt = "RGB測定 / RGB measurement   t = %.2f s   case = %s" % (t_s, kind)
    return np.asarray(an.text_box(img, txt, (10, 10), anchor="lt", font_size=18))


def _update_flame_visual(model: Any, flame_gid: int, Rbw: np.ndarray, thrust_dir: np.ndarray,
                         delivered_thrust: float) -> None:
    """Render a thrust-aligned visual plume / 推力の反対向きへ描画炎を置く。"""
    local_down = Rbw.T @ (-_unit(thrust_dir, np.array([0.0, 0.0, 1.0])))
    length = 0.15 + 0.72 * min(1.0, delivered_thrust / 230.0)
    model.geom_pos[flame_gid] = local_down * length
    model.geom_size[flame_gid, 1] = length
    model.geom_quat[flame_gid] = _quat_from_z(local_down)
    model.geom_rgba[flame_gid, 3] = 1.0 if delivered_thrust > 2.0 else 0.0


def _body_state(data: Any, body_id: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Read free-body origin, velocity, orientation and angular velocity / 真値状態を読む。"""
    p = np.asarray(data.xpos[body_id], float).copy()
    R = np.asarray(data.xmat[body_id], float).reshape(3, 3).copy()
    v = np.asarray(data.cvel[body_id, 3:], float).copy()
    w = np.asarray(data.cvel[body_id, :3], float).copy()
    return p, v, R, w


def mujoco_free_fall_check(duration_s: float = 0.40) -> dict[str, float]:
    """Check MuJoCo zero-thrust motion against free fall / MuJoCo の自由落下を閉形式で検算する。

    The body starts high enough that it cannot contact the pad during the check.
    This guards the physical side of the PoC separately from its controller and
    RGB measurement: no force is applied, so both final height and vertical
    speed must agree with :func:`free_fall_state` to integration tolerance.
    """
    if not np.isfinite(duration_s) or duration_s <= 0.0 or duration_s > 1.0:
        raise ValueError("mujoco_free_fall_check: duration_s must be in (0, 1]")
    try:
        import mujoco
    except ImportError as exc:  # pragma: no cover - optional on some CI jobs
        raise RuntimeError("mujoco_free_fall_check: MuJoCo is required") from exc
    model = mujoco.MjModel.from_xml_string(scene_mjcf())
    data = mujoco.MjData(model)
    bid = int(model.body("booster").id)
    jnt = int(model.body_jntadr[bid])
    qadr, dadr = int(model.jnt_qposadr[jnt]), int(model.jnt_dofadr[jnt])
    z0, vz0 = 70.0, -1.75
    data.qpos[qadr:qadr + 3] = [0.0, 0.0, z0]
    data.qpos[qadr + 3:qadr + 7] = [1.0, 0.0, 0.0, 0.0]
    data.qvel[dadr:dadr + 3] = [0.0, 0.0, vz0]
    mujoco.mj_forward(model, data)
    n = int(round(duration_s / DT))
    for _ in range(n):
        data.xfrc_applied[bid] = 0.0
        mujoco.mj_step(model, data)
    t = n * DT
    z_ref, vz_ref = free_fall_state(z0, vz0, t)
    return {"time_s": t, "height_error_m": abs(float(data.qpos[qadr + 2]) - z_ref),
            "velocity_error_mps": abs(float(data.qvel[dadr + 2]) - vz_ref)}


def run_case(case: Case, *, ci: bool = False, keep_frames: bool = True) -> dict[str, Any]:
    """Run MuJoCo, render two RGB videos, and measure them / 物理→映像→計測を一巡する。

    The returned dictionary retains simulator truth separately from measurements.
    ``ci=True`` uses 320×240 and 0.15 s sampling; full mode is 512×384 and
    0.10 s.  The controller reads simulator state because it is the *plant*
    controller, while all reported perception values are reconstructed only
    from the two RGB frame streams and fixed camera calibration.

    Raises
    ------
    RuntimeError
        If MuJoCo is unavailable.  This is intentional for the actual physics
        run; the caller can decide whether an environment without MuJoCo is a
        skip rather than presenting a numerical substitute as this simulation.
    """
    try:
        import mujoco
    except ImportError as exc:  # pragma: no cover - optional on some CI jobs
        raise RuntimeError("run_case: MuJoCo is required for the rocket world") from exc
    if not isinstance(case, Case):
        raise ValueError("run_case: case must be a Case")
    width, height = ((320, 240) if ci else (512, 384))
    sample_every = 15 if ci else 10
    t_end = 10.5
    model = mujoco.MjModel.from_xml_string(scene_mjcf())
    data = mujoco.MjData(model)
    bid = int(model.body("booster").id)
    uid = int(model.body("upper_stage").id)
    flame_gid = int(model.geom("flame").id)
    booster_geom_ids = {int(model.geom(n).id) for n in ("booster_tank", "booster_nose_marker", "booster_engine_marker")}
    ground_geom_ids = {int(model.geom("ground").id), int(model.geom("landing_pad").id)}
    booster_jnt = int(model.body_jntadr[bid])
    upper_jnt = int(model.body_jntadr[uid])
    bq = int(model.jnt_qposadr[booster_jnt]); bv = int(model.jnt_dofadr[booster_jnt])
    uq = int(model.jnt_qposadr[upper_jnt]); uv = int(model.jnt_dofadr[upper_jnt])
    data.qpos[bq:bq + 3] = [0.0, 0.0, 54.0]
    data.qpos[bq + 3:bq + 7] = [1.0, 0.0, 0.0, 0.0]
    data.qvel[bv:bv + 3] = [1.2, -0.6, -10.0]
    data.qpos[uq:uq + 3] = [0.0, 0.0, 60.2]
    data.qpos[uq + 3:uq + 7] = [1.0, 0.0, 0.0, 0.0]
    data.qvel[uv:uv + 3] = [4.8, -1.2, 4.5]
    mujoco.mj_forward(model, data)
    cams = _camera_calibrations(model, data, width, height)
    renderer = mujoco.Renderer(model, width=width, height=height)
    fuel = float(case.fuel_kg)
    nominal_inertia = np.array([20.0, 20.0, 1.8])
    contact: dict[str, float] | None = None
    rows: list[dict[str, Any]] = []
    prev_vz = float(data.qvel[bv + 2])
    try:
        for step in range(int(round(t_end / DT)) + 1):
            t_s = step * DT
            p, v, Rbw, omega = _body_state(data, bid)
            mass = DRY_MASS + fuel
            model.body_mass[bid] = mass
            model.body_inertia[bid] = nominal_inertia * (mass / (DRY_MASS + NOMINAL_FUEL))
            wind = fixed_wind(case.seed, t_s, case.wind_n)
            # Bounded rule controller: stopping-speed target from v²=2 a h,
            # then velocity P feedback.  Lateral authority and gimbal are both
            # intentionally capped, so the strong-wind case has a real failure.
            height_m = max(0.0, float(p[2]))
            vz_target = -max(0.45, min(18.0, math.sqrt(2.0 * 3.0 * height_m)))
            lateral = -0.55 * p[:2] - 0.82 * v[:2] - wind[:2] / max(mass, 1e-9)
            lateral = np.clip(lateral, -3.0, 3.0)
            az = float(np.clip(1.95 * (vz_target - v[2]), -3.4, 12.0))
            requested_thrust = mass * float(np.clip(G0 + az, 0.0, 19.0))
            fuel_next, delivered = propellant_step(fuel, requested_thrust, DT)
            if fuel <= 0.0:
                delivered = 0.0
            desired_dir = _unit(np.r_[lateral, G0 + az], np.array([0.0, 0.0, 1.0]))
            body_z = Rbw[:, 2]
            # A 15 degree gimbal proxy around the actual stage axis.  The outer
            # torque loop must turn the vehicle; force cannot point arbitrarily.
            gimbal = desired_dir - body_z * float(desired_dir @ body_z)
            gimbal = gimbal * min(1.0, math.tan(math.radians(15.0)) / max(float(np.linalg.norm(gimbal)), 1e-12))
            thrust_dir = _unit(body_z + gimbal, body_z)
            attitude_err = np.cross(body_z, desired_dir)
            torque = 65.0 * attitude_err - 9.0 * omega
            data.xfrc_applied[bid, :3] = delivered * thrust_dir + wind
            data.xfrc_applied[bid, 3:] = torque
            # The separated upper stage gets a brief deterministic departure;
            # it is a different trajectory, not a passive duplicate.
            if t_s < 1.8:
                data.xfrc_applied[uid, :3] = np.array([22.0, 2.0, 88.0])
            else:
                data.xfrc_applied[uid, :3] = 0.0
            data.xfrc_applied[uid, 3:] = 0.0
            _update_flame_visual(model, flame_gid, Rbw, thrust_dir, delivered)
            mujoco.mj_step(model, data)
            fuel = fuel_next
            p2, v2, R2, _ = _body_state(data, bid)
            # First contact is simulator truth; it is deliberately not used by
            # the RGB event estimator below.
            if contact is None:
                hit = False
                for ci in range(data.ncon):
                    con = data.contact[ci]
                    pair = {int(con.geom1), int(con.geom2)}
                    if pair & booster_geom_ids and pair & ground_geom_ids:
                        hit = True
                        break
                if hit:
                    contact = {"time_s": t_s + DT, "speed_mps": float(np.linalg.norm(v2)),
                               "vertical_speed_mps": abs(float(v2[2])), "tilt_deg": _tilt_deg(R2[:, 2]),
                               "offset_m": float(np.linalg.norm(p2[:2]))}
            prev_vz = float(v2[2])
            if step % sample_every:
                continue
            cams_now = cams
            imgs = {}
            for name in cams:
                renderer.update_scene(data, camera=name)
                imgs[name] = renderer.render().copy()
            truth_center = p2 + R2[:, 2] * (BODY_LENGTH / 2.0)
            truth_nose = p2 + R2[:, 2] * 5.55
            truth_engine = p2 + R2[:, 2] * 0.18
            truth_flame_end = p2 - R2[:, 2] * (0.15 + 0.72 * min(1.0, delivered / 230.0))
            per_cam = {}
            for name, image in imgs.items():
                per_cam[name] = {label: _centroid_uv(_mask_rgb(image, label))
                                 for label in ("booster", "nose", "engine", "pad")}
                per_cam[name]["flame_points"] = np.argwhere(_mask_rgb(image, "flame"))
                uv0, _ = camera.project_points(np.vstack([truth_engine, truth_flame_end]), cams_now[name]["K"],
                                                cams_now[name]["R"], cams_now[name]["t"])
                per_cam[name]["flame_truth"] = uv0
            rows.append({"t_s": t_s + DT, "truth_center": truth_center, "truth_nose": truth_nose,
                         "truth_engine": truth_engine, "truth_axis": R2[:, 2].copy(), "truth_mass": mass,
                         "fuel_kg": fuel, "thrust_n": delivered, "wind_n": wind.copy(), "images": imgs if keep_frames else {},
                         "per_cam": per_cam})
    finally:
        renderer.close()
    return {"case": case, "rows": rows, "contact_truth": contact, "cameras": cams,
            "width": width, "height": height, "dt_sample": sample_every * DT}


def measure_from_rgb(run: dict[str, Any]) -> dict[str, Any]:
    """Measure trajectory, tilt, contact, flame and pad offset from RGB / 映像計測。

    The function never reads ``truth_*`` fields.  It uses: RGB colour masks;
    existing Fullseye :func:`camera.triangulate` for calibrated 3-D recovery;
    :func:`measure.fit_line` for the flame direction; and existing
    :func:`calib.image_points_to_world_plane` to place the pad centre.  Missing
    masks remain NaN and cause the final judgement to fail closed.
    """
    if not isinstance(run, dict) or not run.get("rows"):
        raise ValueError("measure_from_rgb: run must contain non-empty rows")
    cams = run["cameras"]
    rows = run["rows"]
    # Pad centre: fixed pad camera RGB marker at the first frame, then metric
    # calibration back-projection onto z=0.  It is intentionally not read from
    # the known world coordinate.
    pad_uv = rows[0]["per_cam"]["pad_camera"]["pad"]
    cp = cams["pad_camera"]
    if np.isfinite(pad_uv).all():
        pad_xy = calib.image_points_to_world_plane(cp["K"], np.c_[cp["R"], cp["t"]],
                                                    [[pad_uv[1], pad_uv[0]]])[0]
    else:
        pad_xy = np.array([np.nan, np.nan])
    series = []
    flame_errors = []
    for row in rows:
        g = row["per_cam"]["ground_tracking_camera"]
        p = row["per_cam"]["pad_camera"]
        center = _triangulate_pair(g["booster"], p["booster"], cams)
        nose = _triangulate_pair(g["nose"], p["nose"], cams)
        engine = _triangulate_pair(g["engine"], p["engine"], cams)
        axis = nose - engine if np.isfinite(nose).all() and np.isfinite(engine).all() else np.full(3, np.nan)
        tilt = _tilt_deg(axis) if np.isfinite(axis).all() and np.linalg.norm(axis) > 1e-9 else float("nan")
        ferr = _line_angle_error_deg(g["flame_points"], g["flame_truth"][0], g["flame_truth"][1])
        if np.isfinite(ferr):
            flame_errors.append(ferr)
        series.append({"t_s": row["t_s"], "center": center, "nose": nose, "engine": engine,
                       "axis": axis, "tilt_deg": tilt, "flame_angle_error_deg": ferr,
                       "ground_uv": g, "pad_uv": p})
    times = np.array([x["t_s"] for x in series])
    engines = np.array([x["engine"] for x in series])
    finite = np.all(np.isfinite(engines), axis=1)
    contact_idx = None
    if np.any(finite):
        # The base colour marker is 0.18 m above the contact plane.  A 0.55 m
        # gate covers rendered-pixel and colour-mask discretisation, but it is
        # still entirely an observation-space event.
        candidates = np.flatnonzero(finite & (engines[:, 2] <= 0.28))
        if len(candidates):
            contact_idx = int(candidates[0])
    vision_contact = None
    if contact_idx is not None and 0 < contact_idx < len(series) - 1:
        i = contact_idx
        good = finite[i - 1:i + 2]
        if bool(np.all(good)):
            dt = times[i + 1] - times[i - 1]
            vel = (engines[i + 1] - engines[i - 1]) / dt
            off = float(np.linalg.norm(engines[i][:2] - pad_xy)) if np.isfinite(pad_xy).all() else float("nan")
            vision_contact = {"time_s": float(times[i]), "speed_mps": float(np.linalg.norm(vel)),
                              "tilt_deg": float(series[i]["tilt_deg"]), "offset_m": off, "index": i}
    return {"series": series, "pad_xy": pad_xy, "contact_vision": vision_contact,
            "flame_angle_median_deg": float(np.median(flame_errors)) if flame_errors else float("nan"),
            "n_flame_frames": len(flame_errors)}


def summarise(run: dict[str, Any], measured: dict[str, Any]) -> dict[str, Any]:
    """Compare independent simulator truth and RGB measurements / 真値との誤差表を作る。"""
    rows, series = run["rows"], measured["series"]
    pe, ae = [], []
    for truth, obs in zip(rows, series):
        if np.isfinite(obs["center"]).all():
            pe.append(float(np.linalg.norm(obs["center"] - truth["truth_center"])))
        if np.isfinite(obs["axis"]).all():
            ae.append(abs(_tilt_deg(obs["axis"]) - _tilt_deg(truth["truth_axis"])))
    true = run["contact_truth"]
    vis = measured["contact_vision"]
    if true is None:
        truth_success = False
    else:
        truth_success = bool(true["speed_mps"] <= SUCCESS_SPEED_MPS and true["tilt_deg"] <= SUCCESS_TILT_DEG
                             and true["offset_m"] <= SUCCESS_OFFSET_M)
    if vis is None or not all(np.isfinite(vis[k]) for k in ("speed_mps", "tilt_deg", "offset_m")):
        vision_success = False
    else:
        vision_success = bool(vis["speed_mps"] <= SUCCESS_SPEED_MPS and vis["tilt_deg"] <= SUCCESS_TILT_DEG
                              and vis["offset_m"] <= SUCCESS_OFFSET_M)
    return {
        "position_median_m": float(np.median(pe)) if pe else float("inf"),
        "position_max_m": float(np.max(pe)) if pe else float("inf"),
        "tilt_median_deg": float(np.median(ae)) if ae else float("inf"),
        "tilt_max_deg": float(np.max(ae)) if ae else float("inf"),
        "flame_angle_median_deg": measured["flame_angle_median_deg"],
        "n_position": len(pe), "n_attitude": len(ae), "n_flame": measured["n_flame_frames"],
        "truth_contact": true, "vision_contact": vis,
        "truth_success": truth_success, "vision_success": vision_success,
        "decision_match": truth_success == vision_success,
    }
