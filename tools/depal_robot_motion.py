# -*- coding: utf-8 -*-
"""混載デパレタイズのロボット動作: UR10e(MuJoCo Menagerie)の逆運動学と、時刻ごとの部品の世界姿勢。

Robot motion for mixed-case depalletizing.  The arm is the MuJoCo Menagerie UR10e
(``universal_robots_ur10e/ur10e.xml``, BSD-3-Clause, (c) 2018 ROS Industrial Consortium);
this module only *reads* that directory.

What it produces
----------------
``plan_motion(picks, fps, base)`` returns a dict (and ``__main__`` writes it to JSON) with, per
frame, the 6 joint angles + the rail position, and for every visual mesh of the arm a transform
``[x, y, z, qw, qx, qy, qz]`` that maps the **raw OBJ vertex coordinates** to world coordinates
(MuJoCo re-centres meshes on their centre of mass when it loads them; the transform here undoes
that, and the module asserts the OBJ <-> MuJoCo vertex mismatch is below 0.1 mm).

World frame (fixed, shared with ``depal_scene.py``): floor z = 0, pallet (1.1 x 1.1 m, top
z = 0.144) centred on the origin, x right, y away, z up [m]; overhead camera at (0, 0, 2.70).

Cell layout decided here (see ``DEFAULT_BASE`` / ``DEFAULT_CONVEYOR`` and the report):
* The suggested mount (0.85, 0, 0.50) cannot reach the far half of the pallet with a vertical
  tool (far corners at x = -0.45 are 1.30-1.38 m away; with a rail the far *low* points are
  reached only with the elbow almost straight, the far *high* approach points not at all).  The
  arm is moved to x = 0.72 (5 cm gap between the 0.24 m pedestal and the pallet edge), raised to
  z = 0.75 (shoulder level with the wrist for far picks), and put on a **linear rail along y**
  (7th axis, ±1.0 m).  For each pick the rail position is chosen (straight in front, or offset
  sideways so near-side picks are not cramped) by the shortest estimated cycle.  ``check_reach``
  in ``__main__`` prints the evidence.
* The conveyor runs along y beside the pallet's +y edge (belt x 0.05..0.55, y 0.65..1.95, top
  0.75, flow +y), outside the camera's pyramid onto the pallet.  Behind the robot (x = 1.55)
  would need a 180° base swing twice per cycle: at the UR10e's 120 °/s that alone is > 5 s.

Blender note: import the OBJ files **without axis conversion** (forward = Y, up = Z); the
transforms assume the OBJ's own axes.
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import numpy as np

try:
    import mujoco
except ImportError as exc:  # pragma: no cover - environment guard
    raise SystemExit("mujoco is required: py -3.11 -m pip install mujoco") from exc

# --------------------------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------------------------

#: Menagerie の UR10e(``MUJOCO_MENAGERIE`` で上書き。既定は作業場の projects/mujoco_menagerie)。
MENAGERIE_UR10E = Path(os.environ.get("MUJOCO_MENAGERIE",
                                      str(Path(__file__).resolve().parents[2] / "mujoco_menagerie"))) / "universal_robots_ur10e"
UR10E_XML = MENAGERIE_UR10E / "ur10e.xml"
UR10E_ASSETS = MENAGERIE_UR10E / "assets"

ARM_JOINTS = (
    "shoulder_pan_joint", "shoulder_lift_joint", "elbow_joint",
    "wrist_1_joint", "wrist_2_joint", "wrist_3_joint",
)
#: UR10e e-Series published maximum joint speeds [rad/s]: base & shoulder 120 °/s, others 180 °/s.
UR10E_VMAX = np.radians([120.0, 120.0, 180.0, 180.0, 180.0, 180.0])
#: UR10e published joint working range is ±360° on every joint.  The Menagerie model limits the
#: elbow to ±180° (physically the elbow cannot fold through itself) — we use the model ranges.
UR10E_PAYLOAD_KG = 12.5

#: The linear axis (7th axis).  Speed/acceleration typical of a heavy-duty belt/rack robot rail.
RAIL_VMAX = 1.5      # m/s
RAIL_AMAX = 4.0      # m/s^2

PALLET_HALF = 0.55
PALLET_TOP = 0.144
CAM_POS = np.array([0.0, 0.0, 2.70])
#: The camera sees the pallet through the pyramid camera -> pallet top rectangle (+ margin).
CAM_VIEW_MARGIN = 0.03

TOOL_LENGTH = 0.22          # flange -> suction pad face [m]
TOOL_SHAFT_RADIUS = 0.035
PAD_SIZE = (0.160, 0.080)   # long x short [m]
PAD_THICK = 0.030           # pad block thickness (part of the 0.22 m)
PRESS_DEPTH = 0.005         # pad pushed 5 mm into the box top on contact

#: Default cell (decided by the reach study, see module docstring).
DEFAULT_BASE: dict[str, Any] = {
    "x": 0.72, "y": 0.0, "z": 0.75,      # robot base flange (bottom of the UR base) in world
    "facing": [-1.0, 0.0, 0.0],          # arm points toward the pallet at pan = 0
    "rail": {"axis": [0.0, 1.0, 0.0], "min": -1.00, "max": 1.00, "home": 0.40},
    "pedestal_size": [0.24, 0.24],       # carriage + column footprint [m] (x, y)
}
DEFAULT_CONVEYOR: dict[str, Any] = {
    "center": [0.30, 1.30, 0.75],        # top surface centre [m] (belt spans y 0.65 .. 1.95)
    "length": 1.30, "width": 0.50, "flow": [0.0, 1.0, 0.0],
    "drop_point": [0.30, 0.95],          # where the box centre is put down (x, y)
}

SAFE_Z = 1.05               # pad must be at least this high while carrying over the pallet
LIFT_CLEAR = 0.08           # carried box bottom clears every remaining box top by this much
APPROACH_HEIGHT = 0.25      # above the grasp point before the vertical descent

# Segment durations [s] (joint-space moves get stretched if a speed limit would be exceeded).
T_CAPTURE = 0.10
T_DESCEND = 0.30            # minimum durations; Cartesian moves are stretched to the speed limits
T_VACUUM = 0.10
T_LIFT = 0.30
T_PLACE = 0.30
T_RELEASE = 0.08
T_ASCEND = 0.25
T_JOINT_MIN = 0.50
#: Peak pad speed on the straight vertical moves [m/s] (UR quotes 1 m/s as a typical TCP speed;
#: the safety tool-speed limit is configurable well above this).
V_CART_PEAK = 1.5
IDLE_ABOVE_CONVEYOR = 0.50  # idle / capture pose: pad this high above the conveyor top
#: Rail offsets tried at the pick (relative to the grasp y): straight in front first, sideways
#: offsets keep the arm from folding up for near-side picks.
RAIL_PICK_OFFSETS = (0.0, 0.10, -0.10, 0.20, -0.20, 0.30, -0.30, 0.40, -0.40, 0.50, -0.50,
                     0.60, -0.60)
BLEND_FRAC = 0.30           # corner blends: overlap = this fraction of the shorter segment
LIFT_BLEND_DIST = 0.03      # horizontal motion may start only in the last 3 cm of the lift
ELBOW_MARGIN_MIN = 10.0     # deg away from stretched (singular) and fully folded
SPEED_USE = 0.92            # plan joint moves to at most 92 % of the published speeds

QUINTIC_PEAK_V = 1.875      # peak of d/dtau (10t^3-15t^4+6t^5)
QUINTIC_PEAK_A = 5.7735     # peak of d2/dtau2


# --------------------------------------------------------------------------------------------
# Small rotation helpers (quaternions are [w, x, y, z])
# --------------------------------------------------------------------------------------------

def mat2quat(R: np.ndarray) -> np.ndarray:
    q = np.zeros(4)
    mujoco.mju_mat2Quat(q, np.ascontiguousarray(R, dtype=float).reshape(9))
    if q[0] < 0:
        q = -q
    return q


def quat2mat(q: np.ndarray) -> np.ndarray:
    R = np.zeros(9)
    mujoco.mju_quat2Mat(R, np.asarray(q, dtype=float))
    return R.reshape(3, 3)


def rot_z(a: float) -> np.ndarray:
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def tool_down_rotation(yaw: float, normal: np.ndarray | None = None) -> np.ndarray:
    """Pad frame for a grasp: z = into the surface (-normal), x = pad long side at ``yaw``."""
    n = np.array([0.0, 0.0, 1.0]) if normal is None else np.asarray(normal, float)
    n = n / np.linalg.norm(n)
    z = -n
    x0 = np.array([math.cos(yaw), math.sin(yaw), 0.0])
    x = x0 - z * float(x0 @ z)
    if np.linalg.norm(x) < 1e-6:  # normal horizontal along yaw: degenerate, pick anything
        x = np.cross(z, [0.0, 1.0, 0.0])
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    return np.column_stack([x, y, z])


def rot_err(R_cur: np.ndarray, R_tgt: np.ndarray) -> np.ndarray:
    """Rotation vector (world frame) that takes R_cur to R_tgt."""
    Rd = R_tgt @ R_cur.T
    q = mat2quat(Rd)
    v = q[1:]
    s = np.linalg.norm(v)
    if s < 1e-12:
        return np.zeros(3)
    ang = 2.0 * math.atan2(s, q[0])
    return v / s * ang


def angle_between(R1: np.ndarray, R2: np.ndarray) -> float:
    return float(np.linalg.norm(rot_err(R1, R2)))


def quintic(tau: float) -> float:
    tau = min(max(tau, 0.0), 1.0)
    return tau ** 3 * (10.0 - 15.0 * tau + 6.0 * tau * tau)


def _quintic_inverse(s: float) -> float:
    """tau in [0, 1] with quintic(tau) = s (bisection; quintic is monotone)."""
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if quintic(mid) < s:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def obb_overlap(c1, R1, h1, c2, R2, h2, tol: float = 0.0) -> float:
    """Separating-axis test for two oriented boxes.  Returns penetration depth (>0 = overlap)
    along the best separating axis (negative = separation distance lower bound)."""
    c1, c2 = np.asarray(c1, float), np.asarray(c2, float)
    axes = [R1[:, i] for i in range(3)] + [R2[:, i] for i in range(3)]
    for i in range(3):
        for j in range(3):
            a = np.cross(R1[:, i], R2[:, j])
            if np.linalg.norm(a) > 1e-9:
                axes.append(a / np.linalg.norm(a))
    best = math.inf
    d = c2 - c1
    for a in axes:
        r1 = sum(h1[i] * abs(a @ R1[:, i]) for i in range(3))
        r2 = sum(h2[i] * abs(a @ R2[:, i]) for i in range(3))
        pen = r1 + r2 - abs(d @ a)
        best = min(best, pen)
    return best - tol


# --------------------------------------------------------------------------------------------
# Model construction
# --------------------------------------------------------------------------------------------

def _fmt(v) -> str:
    return " ".join(f"{float(x):.6g}" for x in v)


def _lookat_camera(name: str, pos, target) -> str:
    f = np.asarray(target, float) - np.asarray(pos, float)
    f /= np.linalg.norm(f)
    x = np.cross(f, [0.0, 0.0, 1.0])
    x /= np.linalg.norm(x)
    y = np.cross(x, f)
    return f'<camera name="{name}" pos="{_fmt(pos)}" xyaxes="{_fmt(x)} {_fmt(y)}" fovy="50"/>'


def build_model_xml(base: dict, conveyor: dict, boxes: list[dict] | None = None) -> str:
    """UR10e on a y-rail + tool + (for debug renders) floor, pallet, conveyor and mocap boxes."""
    text = UR10E_XML.read_text(encoding="utf-8")
    text = text.replace("<option ", '<visual><global offwidth="1600" offheight="1200"/></visual>'
                                    "<option ", 1)
    text = text.replace('meshdir="assets"', f'meshdir="{UR10E_ASSETS.as_posix()}"')
    text = re.sub(r"<keyframe>.*?</keyframe>", "", text, flags=re.S)
    facing = np.asarray(base["facing"], float)
    # Menagerie (base quat "0 0 0 -1"): measured that the all-zero pose stretches the arm along
    # world -x, so a mount yaw of atan2(fy, fx) - pi makes it stretch along `facing`.
    yaw = math.atan2(facing[1], facing[0]) - math.pi
    rail = base["rail"]
    head = (
        f'<body name="rail_carriage" pos="{base["x"]:.6g} {base["y"]:.6g} {base["z"]:.6g}">'
        f'<joint name="rail" type="slide" axis="{_fmt(rail["axis"])}" '
        f'range="{rail["min"]:.6g} {rail["max"]:.6g}" damping="100"/>'
        f'<inertial pos="0 0 0" mass="30" diaginertia="1 1 1"/>'
        f'<geom name="carriage_plate" type="box" size="{base["pedestal_size"][0] / 2:.4g} '
        f'{base["pedestal_size"][1] / 2:.4g} 0.01" pos="0 0 -0.01" rgba="0.3 0.3 0.32 1" '
        f'contype="0" conaffinity="0"/>'
        f'<body name="mount" euler="0 0 {yaw:.9g}">'
    )
    text = text.replace('<body name="base" quat="0 0 0 -1" childclass="ur10e">',
                        head + '<body name="base" quat="0 0 0 -1" childclass="ur10e">', 1)
    tool = (
        '<body name="tool" pos="0 0.1 0" quat="-1 1 0 0">'
        f'<geom name="tool_shaft" type="cylinder" size="{TOOL_SHAFT_RADIUS} '
        f'{(TOOL_LENGTH - PAD_THICK) / 2:.6g}" pos="0 0 {(TOOL_LENGTH - PAD_THICK) / 2:.6g}" '
        'rgba="0.6 0.6 0.62 1" contype="0" conaffinity="0" group="2"/>'
        f'<geom name="tool_pad" type="box" size="{PAD_SIZE[0] / 2} {PAD_SIZE[1] / 2} '
        f'{PAD_THICK / 2}" pos="0 0 {TOOL_LENGTH - PAD_THICK / 2:.6g}" rgba="0.15 0.15 0.15 1" '
        'contype="0" conaffinity="0" group="2"/>'
        f'<site name="flange" pos="0 0 0"/>'
        f'<site name="pad" pos="0 0 {TOOL_LENGTH}"/>'
        '</body>'
    )
    text = text.replace('<site name="attachment_site" pos="0 0.1 0" quat="-1 1 0 0"/>',
                        '<site name="attachment_site" pos="0 0.1 0" quat="-1 1 0 0"/>' + tool, 1)
    cz = conveyor["center"][2]
    world = [
        "</body></body>",  # close mount + rail_carriage
        '<geom name="floor" type="plane" size="4 4 0.1" rgba="0.55 0.55 0.52 1" '
        'contype="0" conaffinity="0"/>',
        f'<geom name="pallet" type="box" size="{PALLET_HALF} {PALLET_HALF} {PALLET_TOP / 2}" '
        f'pos="0 0 {PALLET_TOP / 2}" rgba="0.65 0.5 0.32 1" contype="0" conaffinity="0"/>',
        f'<geom name="conveyor" type="box" size="{conveyor["width"] / 2} '
        f'{conveyor["length"] / 2} {cz / 2}" pos="{conveyor["center"][0]} '
        f'{conveyor["center"][1]} {cz / 2}" rgba="0.25 0.27 0.3 1" contype="0" conaffinity="0"/>',
        f'<geom name="rail_beam" type="box" size="0.08 {(base["rail"]["max"] - base["rail"]["min"]) / 2 + 0.15:.4g} '
        f'{(base["z"] - 0.02) / 2:.4g}" pos="{base["x"]} {(base["rail"]["max"] + base["rail"]["min"]) / 2:.4g} '
        f'{(base["z"] - 0.02) / 2:.4g}" rgba="0.4 0.4 0.42 1" contype="0" conaffinity="0"/>',
        _lookat_camera("overview", (-1.5, -2.3, 2.3), (0.25, 0.25, 0.7)),
        _lookat_camera("side", (0.2, -3.0, 1.2), (0.2, 0.3, 0.8)),
        f'<camera name="ceiling" pos="{_fmt(CAM_POS)}" xyaxes="1 0 0 0 1 0" fovy="27"/>',
        '<light pos="0 0 4" dir="0 0 -1" directional="true"/>',
    ]
    for i, b in enumerate(boxes or []):
        L, W, H = b["box_size"]
        world.append(
            f'<body name="box_{i}" mocap="true" pos="0 0 -5">'
            f'<geom type="box" size="{L / 2} {W / 2} {H / 2}" rgba="0.72 0.55 0.35 1" '
            'contype="0" conaffinity="0"/></body>')
    text = text.replace("</worldbody>", "".join(world) + "</worldbody>", 1)
    return text


@dataclass
class Robot:
    """Thin wrapper: model, data, index bookkeeping, IK and per-geom OBJ transforms."""

    base: dict
    conveyor: dict
    boxes: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.model = mujoco.MjModel.from_xml_string(build_model_xml(self.base, self.conveyor,
                                                                    self.boxes))
        self.data = mujoco.MjData(self.model)
        m = self.model
        self.rail_qadr = m.jnt_qposadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, "rail")]
        self.arm_qadr = np.array([m.jnt_qposadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, j)]
                                  for j in ARM_JOINTS])
        self.arm_dadr = np.array([m.jnt_dofadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, j)]
                                  for j in ARM_JOINTS])
        self.qlo = np.array([m.jnt_range[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, j)][0]
                             for j in ARM_JOINTS])
        self.qhi = np.array([m.jnt_range[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, j)][1]
                             for j in ARM_JOINTS])
        self.pad_sid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_SITE, "pad")
        self.flange_sid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_SITE, "flange")
        # visual mesh geoms of the arm = the parts Blender reads
        self.parts: list[dict] = []
        for g in range(m.ngeom):
            if m.geom_type[g] != mujoco.mjtGeom.mjGEOM_MESH:
                continue
            mid = m.geom_dataid[g]
            mname = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_MESH, mid)
            matid = m.geom_matid[g]
            mat = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_MATERIAL, matid) if matid >= 0 else None
            rgba = (m.mat_rgba[matid] if matid >= 0 else m.geom_rgba[g]).tolist()
            body = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, m.geom_bodyid[g])
            va, vn = m.mesh_vertadr[mid], m.mesh_vertnum[mid]
            verts = m.mesh_vert[va:va + vn].astype(float)
            self.parts.append({
                "geom": g, "name": mname, "body": body, "material": mat, "rgba": rgba,
                "obj": str(UR10E_ASSETS / f"{mname}.obj"),
                "mesh_pos": m.mesh_pos[mid].astype(float).copy(),
                "mesh_quat": m.mesh_quat[mid].astype(float).copy(),
                "verts": verts, "hull": _hull_points(verts),
            })

    # ---- kinematics ------------------------------------------------------------------------
    def set_q(self, q7: np.ndarray) -> None:
        d = self.data
        d.qpos[:] = 0.0
        d.qpos[self.arm_qadr] = q7[:6]
        d.qpos[self.rail_qadr] = q7[6]
        mujoco.mj_kinematics(self.model, d)
        mujoco.mj_comPos(self.model, d)

    def site_pose(self, sid: int) -> tuple[np.ndarray, np.ndarray]:
        return self.data.site_xpos[sid].copy(), self.data.site_xmat[sid].reshape(3, 3).copy()

    def pad_pose(self, q7: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        self.set_q(q7)
        return self.site_pose(self.pad_sid)

    def ik(self, p_tgt: np.ndarray, R_tgt: np.ndarray, rail: float, seed: np.ndarray,
           iters: int = 300, tol_p: float = 2e-6, tol_r: float = 2e-6) -> tuple[np.ndarray, float, float]:
        """Damped least squares IK of the 6 arm joints (rail held fixed).  Returns q7, pos err [m],
        rot err [rad]."""
        m, d = self.model, self.data
        q = np.concatenate([np.asarray(seed[:6], float), [rail]])
        jacp = np.zeros((3, m.nv))
        jacr = np.zeros((3, m.nv))
        lam = 1e-3
        ep = er = math.inf
        for it in range(iters):
            self.set_q(q)
            p, R = self.site_pose(self.pad_sid)
            e = np.concatenate([p_tgt - p, rot_err(R, R_tgt)])
            ep, er = float(np.linalg.norm(e[:3])), float(np.linalg.norm(e[3:]))
            if ep < tol_p and er < tol_r:
                break
            if it == 80 and (ep > 0.02 or er > 0.05):   # not converging from this seed
                break
            mujoco.mj_jacSite(m, d, jacp, jacr, self.pad_sid)
            J = np.vstack([jacp[:, self.arm_dadr], jacr[:, self.arm_dadr]])
            dq = J.T @ np.linalg.solve(J @ J.T + (lam ** 2) * np.eye(6), e)
            n = np.linalg.norm(dq)
            if n > 0.3:
                dq *= 0.3 / n
            q[:6] = np.clip(q[:6] + dq, self.qlo, self.qhi)
        return q, ep, er

    def ik_best(self, p_tgt, R_tgt, rail, seeds: list[np.ndarray], ref: np.ndarray,
                yaw_flip_ok: bool = True) -> tuple[np.ndarray, float, float]:
        """Try several seeds (and the 180°-equivalent pad yaw), keep the converged solution that is
        elbow-up and closest to ``ref`` (weighted joint distance)."""
        targets = [R_tgt]
        if yaw_flip_ok:
            targets.append(R_tgt @ rot_z(math.pi))
        best = None
        w = np.array([2.0, 2.0, 1.5, 1.0, 1.0, 0.6])
        # stage 1: the caller's own seeds (continuity); stage 2: the generic seeds, only if
        # stage 1 found nothing or only a far-away solution
        n_local = min(2, len(seeds))
        for stage_seeds in (seeds[:n_local], seeds[n_local:]):
            for Rt in targets:
                for s in stage_seeds:
                    q, ep, er = self.ik(p_tgt, Rt, rail, s)
                    if ep > 1e-4 or er > 1e-4:
                        continue
                    q[:6] = self._unwrap(q[:6], ref[:6])
                    if not self._elbow_up(q):
                        continue
                    cost = float(np.sum(w * np.abs(q[:6] - ref[:6])))
                    if best is None or cost < best[0]:
                        best = (cost, q, ep, er)
            if best is not None and best[0] < 4.0:
                break
        if best is None:
            raise RuntimeError(f"IK failed for target {np.round(p_tgt, 4)} (rail {rail:.3f})")
        return best[1], best[2], best[3]

    def _unwrap(self, q6: np.ndarray, ref6: np.ndarray) -> np.ndarray:
        q6 = q6.copy()
        for i in range(6):
            for k in (-1, 1):
                alt = q6[i] + k * 2 * math.pi
                if self.qlo[i] <= alt <= self.qhi[i] and abs(alt - ref6[i]) < abs(q6[i] - ref6[i]):
                    q6[i] = alt
        return q6

    def _elbow_up(self, q7: np.ndarray) -> bool:
        """Elbow above the line shoulder -> wrist (keeps the forearm away from the boxes)."""
        self.set_q(q7)
        m, d = self.model, self.data
        sh = d.xpos[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "upper_arm_link")]
        el = d.xpos[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "forearm_link")]
        wr = d.xpos[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "wrist_1_link")]
        t = np.clip(((el - sh) @ (wr - sh)) / max((wr - sh) @ (wr - sh), 1e-9), 0, 1)
        return bool(el[2] >= (sh + t * (wr - sh))[2] - 1e-6)

    # ---- OBJ <-> world -----------------------------------------------------------------------
    def part_obj_transforms(self) -> dict[str, np.ndarray]:
        """For the current data: name -> [x,y,z,qw,qx,qy,qz] mapping raw OBJ vertices to world.

        MuJoCo stores mesh vertices as v_mj = R(mesh_quat)^T (v_obj - mesh_pos) [verified by
        ``verify_obj_alignment``], so world = xpos + xmat v_mj = xpos + xmat R^T (v_obj - pos).
        """
        out = {}
        for p in self.parts:
            g = p["geom"]
            Rg = self.data.geom_xmat[g].reshape(3, 3)
            Rm = quat2mat(p["mesh_quat"])
            R = Rg @ Rm.T
            t = self.data.geom_xpos[g] - R @ p["mesh_pos"]
            out[p["name"]] = np.concatenate([t, mat2quat(R)])
        return out

    def world_hulls(self) -> list[np.ndarray]:
        res = []
        for p in self.parts:
            g = p["geom"]
            res.append(self.data.geom_xpos[g] + p["hull"] @ self.data.geom_xmat[g].reshape(3, 3).T)
        return res


def _hull_points(v: np.ndarray) -> np.ndarray:
    try:
        from scipy.spatial import ConvexHull
        return v[ConvexHull(v).vertices]
    except Exception:  # scipy missing or degenerate: fall back to all vertices
        return v


def read_obj_vertices(path: str | Path) -> np.ndarray:
    vs = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("v "):
                vs.append([float(x) for x in line.split()[1:4]])
    return np.asarray(vs, float)


def verify_obj_alignment(robot: Robot, q7: np.ndarray) -> float:
    """Max distance [m] between OBJ vertices mapped by our transform and MuJoCo's world mesh
    vertices (both directions, nearest neighbour).  Asserts <= 0.1 mm."""
    from scipy.spatial import cKDTree
    robot.set_q(q7)
    T = robot.part_obj_transforms()
    worst = 0.0
    for p in robot.parts:
        g = p["geom"]
        mj_world = robot.data.geom_xpos[g] + p["verts"] @ robot.data.geom_xmat[g].reshape(3, 3).T
        obj = np.unique(read_obj_vertices(p["obj"]), axis=0)
        t = T[p["name"]]
        ours = t[:3] + obj @ quat2mat(t[3:]).T
        d1 = cKDTree(mj_world).query(ours)[0].max()
        d2 = cKDTree(ours).query(mj_world)[0].max()
        worst = max(worst, float(d1), float(d2))
    assert worst <= 1e-4, f"OBJ <-> MuJoCo vertex mismatch {worst * 1e3:.4f} mm > 0.1 mm"
    return worst


# --------------------------------------------------------------------------------------------
# Trajectory
# --------------------------------------------------------------------------------------------

@dataclass
class Segment:
    kind: str                 # "hold" | "joint" | "cart"
    phase: str
    t0: float
    T: float
    q0: np.ndarray
    q1: np.ndarray
    p0: np.ndarray | None = None
    p1: np.ndarray | None = None
    R: np.ndarray | None = None
    attached: int | None = None
    cycle: int = -1
    q_grid: np.ndarray | None = None   # Cartesian segments: IK along the line, s = 0..1

    def prepare(self, robot: "Robot", n: int = 400) -> None:
        """Solve the straight line once (sequential IK) so q(s) can be interpolated."""
        if self.kind != "cart":
            return
        grid = [self.q0.copy()]
        q = self.q0.copy()
        for k in range(1, n + 1):
            p = self.p0 + (self.p1 - self.p0) * k / n
            q_new, ep, er = robot.ik(p, self.R, self.q0[6], q)
            if ep > 1e-5 or er > 1e-5:
                raise RuntimeError(f"Cartesian IK failed on {self.phase} (cycle {self.cycle})")
            if np.max(np.abs(q_new[:6] - q[:6])) > 0.1:
                raise RuntimeError(f"IK branch jump on {self.phase} (cycle {self.cycle})")
            q = q_new
            grid.append(q.copy())
        if np.max(np.abs(grid[-1][:6] - self.q1[:6])) > 1e-3:
            raise RuntimeError(f"{self.phase} (cycle {self.cycle}) ends on another IK branch")
        grid[-1] = self.q1.copy()
        self.q_grid = np.array(grid)

    def q_at(self, tau: float) -> np.ndarray:
        s = quintic(tau)
        if self.kind == "hold":
            return self.q0.copy()
        if self.kind == "joint":
            return self.q0 + s * (self.q1 - self.q0)
        x = s * (len(self.q_grid) - 1)
        i = min(int(x), len(self.q_grid) - 2)
        f = x - i
        return self.q_grid[i] * (1.0 - f) + self.q_grid[i + 1] * f


def joint_move_time(q0: np.ndarray, q1: np.ndarray, t_min: float) -> float:
    dq = np.abs(q1 - q0)
    t_v = QUINTIC_PEAK_V * dq[:6] / (SPEED_USE * UR10E_VMAX)
    t_rail_v = QUINTIC_PEAK_V * dq[6] / (SPEED_USE * RAIL_VMAX)
    t_rail_a = math.sqrt(QUINTIC_PEAK_A * dq[6] / (SPEED_USE * RAIL_AMAX))
    return float(max(t_min, t_v.max(), t_rail_v, t_rail_a))


def cart_move_time(robot: "Robot", p0: np.ndarray, p1: np.ndarray, R: np.ndarray,
                   q0: np.ndarray, t_min: float, n: int = 24) -> float:
    """Duration of a straight-line quintic move: limited by the peak pad speed and by every
    joint's published speed (dq/ds measured along the IK path)."""
    q_prev = q0.copy()
    dqds = np.zeros(6)
    for k in range(1, n + 1):
        p = p0 + (p1 - p0) * k / n
        q, ep, er = robot.ik(p, R, q0[6], q_prev)
        if ep > 1e-4 or er > 1e-4:
            raise RuntimeError(f"Cartesian path not reachable near {np.round(p, 3)}")
        dqds = np.maximum(dqds, np.abs(q[:6] - q_prev[:6]) * n)
        q_prev = q
    t_joint = QUINTIC_PEAK_V * float(np.max(dqds / (SPEED_USE * UR10E_VMAX)))
    t_cart = QUINTIC_PEAK_V * float(np.linalg.norm(p1 - p0)) / V_CART_PEAK
    return max(t_min, t_joint, t_cart)


def _camera_margin(robot: "Robot", q7: np.ndarray) -> float:
    """Smallest signed distance [m] of arm + tool outside the camera -> pallet pyramid."""
    robot.set_q(q7)
    pts = np.vstack(robot.world_hulls())
    pad_p, pad_R = robot.site_pose(robot.pad_sid)
    tc, tR, th = _tool_obb(pad_p, pad_R)
    corners = tc + (np.array([[sx, sy, sz] for sx in (-1, 1) for sy in (-1, 1)
                              for sz in (-1, 1)]) * th) @ tR.T
    return float(min(np.min(_in_camera_view(pts)), np.min(_in_camera_view(corners))))


def plan_motion(picks: list[dict], fps: int = 30, base: dict | None = None,
                conveyor: dict | None = None) -> dict:
    """Plan the pick-and-place motion for ``picks`` (in pick order) and sample it at ``fps``.

    Parameters
    ----------
    picks : list of dict
        ``{"box_id", "grasp": [x, y, z, yaw], "normal": [nx, ny, nz] (optional),
        "box_size": [L, W, H], "box_top_center": [x, y, z], "box_yaw": float}``.
        ``grasp`` z is the top-surface height the pad touches.  L is along ``box_yaw``.
    fps : int
        Output frame rate.
    base : dict, optional
        Robot mount (see ``DEFAULT_BASE``); keys missing from it fall back to the defaults.
    conveyor : dict, optional
        Conveyor geometry (see ``DEFAULT_CONVEYOR``).

    Returns
    -------
    dict
        JSON-serialisable plan: ``fps, base, conveyor, tool, meshes, boxes, frames, checks``.
    """
    if not picks:
        raise ValueError("picks is empty")
    base = {**DEFAULT_BASE, **(base or {})}
    base["rail"] = {**DEFAULT_BASE["rail"], **base.get("rail", {})}
    conveyor = {**DEFAULT_CONVEYOR, **(conveyor or {})}
    for pk in picks:
        _validate_pick(pk)

    robot = Robot(base, conveyor, list(picks))
    rail_lo, rail_hi = base["rail"]["min"], base["rail"]["max"]

    # --- idle pose: above the drop point (out of the camera's view of the pallet) --------------
    drop_xy = np.array(conveyor["drop_point"], float)
    conv_top = float(conveyor["center"][2])
    rail_home = float(base["rail"]["home"])
    seed_generic = _seeds(robot)
    p_idle = np.array([drop_xy[0], drop_xy[1], conv_top + IDLE_ABOVE_CONVEYOR])
    q_idle, _, _ = robot.ik_best(p_idle, tool_down_rotation(math.pi / 2), rail_home, seed_generic,
                                 ref=seed_generic[0])

    segs: list[Segment] = []
    t = 0.0
    q_cur = q_idle.copy()
    contact_checks = []
    box_events = []
    remaining = list(range(len(picks)))
    flow_yaw = math.atan2(conveyor["flow"][1], conveyor["flow"][0])

    for ci, pk in enumerate(picks):
        gx, gy, gz, gyaw = (float(v) for v in pk["grasp"])
        n = np.asarray(pk.get("normal") or [0.0, 0.0, 1.0], float)
        n /= np.linalg.norm(n)
        L, W, H = (float(v) for v in pk["box_size"])
        remaining.remove(ci)
        R_g = tool_down_rotation(gyaw, n)
        p_contact = np.array([gx, gy, gz]) - n * PRESS_DEPTH
        p_above = np.array([gx, gy, gz]) + n * APPROACH_HEIGHT

        top_rem = max([float(picks[j]["box_top_center"][2]) for j in remaining] + [PALLET_TOP])
        z_lift = max(SAFE_Z, top_rem + LIFT_CLEAR + (H - PRESS_DEPTH))
        p_lift = np.array([gx, gy, z_lift])
        p_place_above = np.array([drop_xy[0], drop_xy[1], max(z_lift, conv_top + H + 0.15)])
        p_release = np.array([drop_xy[0], drop_xy[1], conv_top + H - PRESS_DEPTH])
        geo = dict(R_g=R_g, p_above=p_above, p_contact=p_contact, p_lift=p_lift,
                   p_place_above=p_place_above, p_release=p_release, p_idle=p_idle,
                   box_yaw=float(pk["box_yaw"]), flow_yaw=flow_yaw)
        # choose the rail positions (at the pick and at the drop) by the shortest cycle
        best = None
        for off in RAIL_PICK_OFFSETS:
            rail = gy + off
            if not (rail_lo <= rail <= rail_hi):
                continue
            plan = _plan_cycle(robot, geo, rail, q_cur, seed_generic, q_idle, rail_lo, rail_hi)
            if plan is not None and (best is None or plan["T_total"] < best["T_total"]):
                best = plan
        if best is None:
            raise RuntimeError(f"box {pk['box_id']}: no rail position reaches the grasp "
                               f"{np.round(p_contact, 3)} and the drop point")
        rail, rail_drop = best["rail"], best["rail_drop"]
        q_above, q_contact, q_lift = best["q_above"], best["q_contact"], best["q_lift"]
        q_pabove, q_release, q_idle_c = best["q_pabove"], best["q_release"], best["q_idle"]
        R_g_used, R_place = best["R_g"], best["R_place"]
        Tm = best["T"]

        def add(kind, phase, T, q0, q1, p0=None, p1=None, R=None, att=None, lead=0.0):
            """Append a segment; ``lead`` > 0 starts it that long before the previous one ends
            (blended corner)."""
            nonlocal t
            t0 = t - lead
            segs.append(Segment(kind, phase, t0, T, q0.copy(), q1.copy(), p0, p1, R, att, ci))
            t = t0 + T

        # blends: approach -> descent (lateral motion dies out while the pad is still >= ~20 cm
        # above the box), lift -> transfer (horizontal motion starts only in the last
        # LIFT_BLEND_DIST of the lift), transfer -> place (both over the conveyor)
        lift_d = float(np.linalg.norm(p_lift - p_contact))
        tau_l = _quintic_inverse(max(0.0, 1.0 - LIFT_BLEND_DIST / max(lift_d, 1e-9)))
        lead_desc = BLEND_FRAC * min(Tm["approach"], Tm["descend"])
        lead_tr = min((1.0 - tau_l) * Tm["lift"], BLEND_FRAC * Tm["transfer"])
        lead_pl = BLEND_FRAC * min(Tm["transfer"], Tm["place"])

        bid = int(pk["box_id"])
        t_cycle0 = t
        add("hold", "idle", T_CAPTURE, q_cur, q_cur)
        add("joint", "approach", Tm["approach"], q_cur, q_above)
        add("cart", "grasp", Tm["descend"], q_above, q_contact, p_above, p_contact, R_g_used,
            lead=lead_desc)
        t_contact = t
        add("hold", "grasp", T_VACUUM, q_contact, q_contact, att=bid)
        add("cart", "lift", Tm["lift"], q_contact, q_lift, p_contact, p_lift, R_g_used, att=bid)
        add("joint", "transfer", Tm["transfer"], q_lift, q_pabove, att=bid, lead=lead_tr)
        add("cart", "place", Tm["place"], q_pabove, q_release, p_place_above, p_release, R_place,
            att=bid, lead=lead_pl)
        t_release = t
        add("hold", "place", T_RELEASE, q_release, q_release)
        add("cart", "return", Tm["ascend"], q_release, q_idle_c, p_release, p_idle, R_place)
        q_cur = q_idle_c

        # contact accuracy (IK convergence) at the contact instant
        pc, Rc = robot.pad_pose(q_contact)
        contact_checks.append({
            "box_id": bid, "cycle": ci, "t_contact": round(t_contact, 4),
            "pos_err_mm": float(np.linalg.norm(pc - p_contact) * 1e3),
            "rot_err_deg": math.degrees(angle_between(Rc, R_g_used)),
            "normal_err_deg": math.degrees(math.acos(np.clip(-Rc[:, 2] @ n, -1, 1))),
            "pad_yaw_deg": math.degrees(math.atan2(Rc[1, 0], Rc[0, 0])),
            "rail": rail, "rail_drop": rail_drop, "lift_z": z_lift,
        })
        box_events.append({"box_id": bid, "cycle": ci, "t_cycle_start": round(t_cycle0, 4),
                           "t_capture": t_cycle0, "t_contact": round(t_contact, 4),
                           "t_release": round(t_release, 4), "t_cycle_end": round(t, 4),
                           "cycle_s": round(t - t_cycle0, 4)})

    # --- evaluate the trajectory --------------------------------------------------------------
    t_end = t
    fine_dt = 1.0 / 240.0
    t_frames = np.arange(0.0, t_end + 1e-9, 1.0 / fps)
    t_fine = np.arange(0.0, t_end + 1e-9, fine_dt)
    t_capt = np.array([e["t_capture"] for e in box_events])
    times = np.unique(np.round(np.concatenate([t_frames, t_fine, t_capt, [t_end]]), 9))
    evaluator = _TrajEvaluator(robot, segs)
    samples = [evaluator(ti) for ti in times]
    # contact accuracy measured on the *evaluated* trajectory (blends included), not on the IK
    # waypoint alone
    for c in contact_checks:
        seg = next(s for s in segs if s.cycle == c["cycle"] and s.phase == "grasp"
                   and s.kind == "cart")
        q_eval, _ = evaluator(seg.t0 + seg.T)
        pc, Rc = robot.pad_pose(q_eval)
        c["pos_err_mm"] = float(np.linalg.norm(pc - seg.p1) * 1e3)
        c["rot_err_deg"] = math.degrees(angle_between(Rc, seg.R))
        n_c = np.asarray(picks[c["cycle"]].get("normal") or [0.0, 0.0, 1.0], float)
        c["normal_err_deg"] = math.degrees(math.acos(np.clip(-Rc[:, 2] @ (n_c / np.linalg.norm(n_c)),
                                                             -1.0, 1.0)))

    # box attach bookkeeping: relative pose at the contact instant
    rel_pose: dict[int, tuple[np.ndarray, np.ndarray]] = {}
    pick_by_id = {int(pk["box_id"]): pk for pk in picks}
    for pk in picks:
        bid = int(pk["box_id"])
        c = next(c for c in contact_checks if c["box_id"] == bid)
        seg = next(s for s in segs if s.attached == bid)
        pc, Rc = robot.pad_pose(seg.q0)
        bc, bR = box_world_pose(pk)
        rel_pose[bid] = (Rc.T @ (bc - pc), Rc.T @ bR)

    frame_idx = set(np.round(t_frames, 9).tolist())
    frames, check_rows = [], []
    picked_before: dict[int, float] = {e["box_id"]: e["t_contact"] for e in box_events}
    capture_ts = {round(e["t_capture"], 9) for e in box_events}
    for ti, (q7, seg) in zip(times, samples):
        robot.set_q(q7)
        pad_p, pad_R = robot.site_pose(robot.pad_sid)
        fl_p, fl_R = robot.site_pose(robot.flange_sid)
        bpose = None
        if seg.attached is not None:
            rp, rR = rel_pose[seg.attached]
            bpose = (pad_p + pad_R @ rp, pad_R @ rR)
        row = {"t": float(ti), "q": q7.copy(), "seg": seg, "pad": (pad_p, pad_R), "box": bpose,
               "hulls": robot.world_hulls(), "capture": round(float(ti), 9) in capture_ts}
        check_rows.append(row)
        if round(float(ti), 9) in frame_idx:
            parts = {k: _r(v) for k, v in robot.part_obj_transforms().items()}
            frames.append({
                "t": round(float(ti), 6),
                "q": _r(q7),
                "rail_y": round(float(q7[6]), 6),
                "base_pose": _r(np.concatenate([[base["x"], base["y"] + q7[6], base["z"]],
                                                mat2quat(robot.data.xmat[mujoco.mj_name2id(
                                                    robot.model, mujoco.mjtObj.mjOBJ_BODY,
                                                    "mount")].reshape(3, 3))])),
                "parts": parts,
                "flange_pose": _r(np.concatenate([fl_p, mat2quat(fl_R)])),
                "tool_pose": _r(np.concatenate([pad_p, mat2quat(pad_R)])),
                "attached": seg.attached,
                "box_pose": None if bpose is None else _r(np.concatenate([bpose[0],
                                                                          mat2quat(bpose[1])])),
                "phase": seg.phase,
                "cycle": seg.cycle,
            })

    checks = _run_checks(robot, picks, check_rows, contact_checks, box_events, picked_before,
                         fine_dt)
    checks["obj_vs_mujoco_max_mm"] = verify_obj_alignment(
        robot, np.array([0.3, -1.1, 1.2, -1.6, -1.4, 0.7, 0.21])) * 1e3

    boxes_out = []
    for e in box_events:
        pk = pick_by_id[e["box_id"]]
        bc, bR = box_world_pose(pk)
        rp, rR = rel_pose[e["box_id"]]
        seg = next(s for s in segs if s.cycle == e["cycle"] and s.phase == "place"
                   and s.kind == "cart")
        pr, Rr = robot.pad_pose(seg.q1)
        placed_c, placed_R = pr + Rr @ rp, Rr @ rR
        boxes_out.append({**e, "initial_pose": _r(np.concatenate([bc, mat2quat(bR)])),
                          "placed_pose": _r(np.concatenate([placed_c, mat2quat(placed_R)])),
                          "box_size": pk["box_size"]})

    return {
        "fps": fps,
        "duration_s": round(t_end, 4),
        "world": {"floor_z": 0.0, "pallet": {"center": [0, 0], "size": [1.1, 1.1],
                                             "top_z": PALLET_TOP},
                  "camera": CAM_POS.tolist()},
        "base": {**base, "rail_y_series": "frames[*].rail_y",
                 "note": "robot base (bottom of UR base) at (x, y + rail_y, z); arm faces -x at "
                         "pan = 0; rail runs along +y"},
        "conveyor": conveyor,
        "tool": {"length": TOOL_LENGTH, "shaft": {"shape": "cylinder", "radius": TOOL_SHAFT_RADIUS,
                                                  "length": TOOL_LENGTH - PAD_THICK},
                 "pad": {"shape": "box", "size": [PAD_SIZE[0], PAD_SIZE[1], PAD_THICK],
                         "long_side": "tool local +x"},
                 "frame": "flange_pose: origin at flange, +z along the tool; tool_pose = pad face "
                          "centre (flange + 0.22 m along +z), +x = pad long side",
                 "press_depth": PRESS_DEPTH},
        "meshes": [{"name": p["name"], "obj": p["obj"], "material": p["material"],
                    "rgba": [round(c, 4) for c in p["rgba"]], "link": p["body"]} for p in robot.parts],
        "obj_import": "Blender: import OBJ with forward_axis='Y', up_axis='Z' (no conversion); "
                      "apply parts[name] = [x,y,z,qw,qx,qy,qz] as the object's world transform",
        "joint_order": list(ARM_JOINTS) + ["rail (m, along +y)"],
        "boxes": boxes_out,
        "frames": frames,
        "checks": checks,
        "license": {"ur10e_model": "MuJoCo Menagerie universal_robots_ur10e, BSD-3-Clause, "
                                   "Copyright 2018 ROS Industrial Consortium"},
    }


def _validate_pick(pk: dict) -> None:
    for k in ("box_id", "grasp", "box_size", "box_top_center", "box_yaw"):
        if k not in pk:
            raise ValueError(f"pick missing key {k!r}: {pk}")
    if len(pk["grasp"]) != 4 or len(pk["box_size"]) != 3 or len(pk["box_top_center"]) != 3:
        raise ValueError(f"bad pick shape: {pk}")
    if not all(math.isfinite(float(v)) for v in list(pk["grasp"]) + list(pk["box_size"])):
        raise ValueError(f"non-finite values in pick: {pk}")


def box_world_pose(pk: dict) -> tuple[np.ndarray, np.ndarray]:
    """Box centre and rotation from top centre / yaw / (optional) normal."""
    n = np.asarray(pk.get("normal") or [0.0, 0.0, 1.0], float)
    n /= np.linalg.norm(n)
    R = tool_down_rotation(float(pk["box_yaw"]), -n)  # z = +n
    # tool_down_rotation(yaw, -n) gives z = n, x along yaw: a right-handed box frame
    H = float(pk["box_size"][2])
    c = np.asarray(pk["box_top_center"], float) - n * H / 2
    return c, R


def _elbow_margin_deg(q7: np.ndarray) -> float:
    """Distance of the elbow from stretched (0°, singular) and folded (180°, limit)."""
    e = abs(math.degrees(q7[2]))
    return min(e, 180.0 - e)


def _plan_cycle(robot: Robot, geo: dict, rail: float, q_cur: np.ndarray,
                seed_generic: list[np.ndarray], q_idle: np.ndarray,
                rail_lo: float, rail_hi: float) -> dict | None:
    """Solve every waypoint of one cycle for a given rail position at the pick, pick the best
    rail position at the drop, and time every segment.  None if something is unreachable or the
    elbow comes closer than ``ELBOW_MARGIN_MIN`` to stretched / folded."""
    try:
        q_above, _, _ = robot.ik_best(geo["p_above"], geo["R_g"], rail, [q_cur] + seed_generic,
                                      ref=q_cur)
        R_g = robot.pad_pose(q_above)[1]                 # may be the 180°-flipped pad yaw
        q_contact, _, _ = robot.ik_best(geo["p_contact"], R_g, rail, [q_above], ref=q_above,
                                        yaw_flip_ok=False)
        q_lift, _, _ = robot.ik_best(geo["p_lift"], R_g, rail, [q_contact], ref=q_contact,
                                     yaw_flip_ok=False)
        if min(_elbow_margin_deg(q) for q in (q_above, q_contact, q_lift)) < ELBOW_MARGIN_MIN:
            return None
        T = {
            "approach": joint_move_time(q_cur, q_above, T_JOINT_MIN),
            "descend": cart_move_time(robot, geo["p_above"], geo["p_contact"], R_g, q_above,
                                      T_DESCEND),
            "lift": cart_move_time(robot, geo["p_contact"], geo["p_lift"], R_g, q_contact, T_LIFT),
        }
    except RuntimeError:
        return None
    # place: box long side along the flow, box/pad relative yaw kept from the contact instant
    pad_yaw = math.atan2(R_g[1, 0], R_g[0, 0])
    R_place0 = tool_down_rotation(geo["flow_yaw"] - (geo["box_yaw"] - pad_yaw))
    best = None
    y_drop = float(geo["p_release"][1])
    for rd in np.arange(rail_lo, rail_hi + 1e-9, 0.10):
        rd = float(rd)
        if not (y_drop - 1.2 <= rd <= y_drop + 0.4):   # the drop is out of reach beyond this
            continue
        try:
            qa, _, _ = robot.ik_best(geo["p_place_above"], R_place0, rd,
                                     [q_lift, q_idle] + seed_generic, ref=q_lift)
            Rp = robot.pad_pose(qa)[1]
            qr, _, _ = robot.ik_best(geo["p_release"], Rp, rd, [qa], ref=qa, yaw_flip_ok=False)
            qi, _, _ = robot.ik_best(geo["p_idle"], Rp, rd, [qr], ref=qr, yaw_flip_ok=False)
        except RuntimeError:
            continue
        if min(_elbow_margin_deg(q) for q in (qa, qr, qi)) < ELBOW_MARGIN_MIN:
            continue
        if _camera_margin(robot, qi) <= 0.0:        # idle = capture pose: view must be clear
            continue
        t_tr = joint_move_time(q_lift, qa, T_JOINT_MIN)
        # half of the next approach, estimated as going back to this pick's lift pose
        cost = t_tr + 0.5 * joint_move_time(qi, q_lift, T_JOINT_MIN)
        if best is None or cost < best[0]:
            best = (cost, t_tr, qa, qr, qi, Rp, rd)
    if best is None:
        return None
    cost, t_tr, qa, qr, qi, Rp, rd = best
    try:
        T["transfer"] = t_tr
        T["place"] = cart_move_time(robot, geo["p_place_above"], geo["p_release"], Rp, qa, T_PLACE)
        T["ascend"] = cart_move_time(robot, geo["p_release"], geo["p_idle"], Rp, qr, T_ASCEND)
    except RuntimeError:
        return None
    T_total = sum(T.values()) + T_CAPTURE + T_VACUUM + T_RELEASE + (cost - t_tr)
    return {"rail": rail, "rail_drop": rd, "q_above": q_above, "q_contact": q_contact,
            "q_lift": q_lift, "q_pabove": qa, "q_release": qr, "q_idle": qi, "R_g": R_g,
            "R_place": Rp, "T": T, "T_total": T_total}


def _seeds(robot: Robot) -> list[np.ndarray]:
    """Elbow-up, tool-down seeds covering both pan directions."""
    seeds = []
    for pan in (0.0, 0.8, -0.8, 1.57, -1.57):
        for lift, elbow in ((-1.2, 1.6), (-0.6, 0.9), (-1.6, 2.2)):
            w1 = -math.pi / 2 - (lift + elbow)
            seeds.append(np.array([pan, lift, elbow, w1, -math.pi / 2, 0.0, 0.0]))
    return seeds


class _TrajEvaluator:
    """q(t) by superposition: q(t) = q_start + sum_i (q_i(tau_i) - q_i(0)) over the segments
    that have started.  Without overlaps this is exactly the active segment; where a segment
    starts ``lead`` seconds before its predecessor ends, the two motions blend (velocity stays
    continuous, both endpoints are still reached exactly)."""

    def __init__(self, robot: Robot, segs: list[Segment]):
        self.robot, self.segs = robot, segs
        for s in segs:
            s.prepare(robot)
        self.q_start = segs[0].q0.copy()

    def __call__(self, t: float) -> tuple[np.ndarray, Segment]:
        q = self.q_start.copy()
        active = self.segs[0]
        for s in self.segs:
            if t < s.t0 - 1e-12:
                break
            tau = (t - s.t0) / s.T if s.T > 0 else 1.0
            if s.kind != "hold":
                q += s.q_at(min(tau, 1.0)) - s.q0
            active = s
        return q, active


def _r(v) -> list[float]:
    return [round(float(x), 6) for x in np.asarray(v).ravel()]


# --------------------------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------------------------

def _in_camera_view(pts: np.ndarray) -> np.ndarray:
    """Signed margin per point: > 0 means outside the camera -> pallet-top pyramid."""
    z = pts[:, 2]
    h = (PALLET_HALF + CAM_VIEW_MARGIN) * (CAM_POS[2] - z) / (CAM_POS[2] - PALLET_TOP)
    inside_z = (z > PALLET_TOP) & (z < CAM_POS[2])
    m = np.maximum(np.abs(pts[:, 0]) - h, np.abs(pts[:, 1]) - h)
    return np.where(inside_z, m, np.inf)


def _tool_obb(pad_p, pad_R) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    c = pad_p - pad_R[:, 2] * (TOOL_LENGTH / 2)
    return c, pad_R, np.array([PAD_SIZE[0] / 2, PAD_SIZE[1] / 2, TOOL_LENGTH / 2])


def _run_checks(robot, picks, rows, contact_checks, box_events, t_contact_by_id, dt) -> dict:
    q = np.array([r["q"] for r in rows])
    ts = np.array([r["t"] for r in rows])
    # joint limit usage: fraction of the half-range used from the centre
    centre = (robot.qlo + robot.qhi) / 2
    half = (robot.qhi - robot.qlo) / 2
    lim_use = np.max(np.abs(q[:, :6] - centre) / half, axis=0)
    rail_use = max(abs(q[:, 6].min() - (robot.base["rail"]["min"] + robot.base["rail"]["max"]) / 2),
                   abs(q[:, 6].max() - (robot.base["rail"]["min"] + robot.base["rail"]["max"]) / 2)) \
        / ((robot.base["rail"]["max"] - robot.base["rail"]["min"]) / 2)
    dtv = np.diff(ts)
    good = dtv > 1e-6
    v = np.diff(q, axis=0)[good] / dtv[good, None]
    v_use = np.max(np.abs(v[:, :6]), axis=0) / UR10E_VMAX
    rail_v = float(np.max(np.abs(v[:, 6])))
    # acceleration on a uniform resampling (the sample times are not exactly uniform)
    tu = np.arange(ts[0], ts[-1], dt)
    ru = np.interp(tu, ts, q[:, 6])
    a_rail = float(np.max(np.abs(np.diff(ru, 2)))) / dt ** 2 if len(tu) > 3 else 0.0

    pick_by_id = {int(p["box_id"]): p for p in picks}
    floor_min = math.inf
    pallet_pen = -math.inf
    box_hits = []
    link_box_min_clear = math.inf
    carried_box_hits = []
    tool_box_hits = []
    cam_rows = []
    for r in rows:
        pts = np.vstack(r["hulls"])
        floor_min = min(floor_min, float(pts[:, 2].min()))
        inside = (np.abs(pts[:, 0]) <= PALLET_HALF) & (np.abs(pts[:, 1]) <= PALLET_HALF)
        if inside.any():
            pallet_pen = max(pallet_pen, float((PALLET_TOP - pts[inside, 2]).max()))
        # boxes still on the pallet at time t
        present = [b for b, tc in t_contact_by_id.items() if r["t"] < tc - 1e-9]
        att = r["seg"].attached
        for b in present:
            bc, bR = box_world_pose(pick_by_id[b])
            hb = np.array(pick_by_id[b]["box_size"], float) / 2
            loc = (pts - bc) @ bR
            out = np.max(np.abs(loc) - hb, axis=1)
            mo = float(out.min())
            link_box_min_clear = min(link_box_min_clear, mo)
            if mo < 0:
                box_hits.append({"t": round(r["t"], 4), "box": b, "depth_mm": -mo * 1e3})
            # tool vs remaining boxes (the box being picked is touched on purpose)
            tc, tR, th = _tool_obb(*r["pad"])
            pen = obb_overlap(tc, tR, th, bc, bR, hb)
            target = int(picks[r["seg"].cycle]["box_id"]) == b   # pressed 5 mm on purpose
            if pen > (PRESS_DEPTH + 1e-4 if target else 1e-3):
                tool_box_hits.append({"t": round(r["t"], 4), "box": b, "pen_mm": pen * 1e3})
            if r["box"] is not None and att is not None:
                cpen = obb_overlap(r["box"][0], r["box"][1],
                                   np.array(pick_by_id[att]["box_size"], float) / 2, bc, bR, hb)
                # touching neighbours at the very start of the lift is allowed (1 mm)
                if cpen > 1e-3:
                    carried_box_hits.append({"t": round(r["t"], 4), "carried": att, "box": b,
                                             "pen_mm": cpen * 1e3})
        if r["capture"]:
            m_cam = float(np.min(_in_camera_view(pts)))
            tc, tR, th = _tool_obb(*r["pad"])
            corners = tc + (np.array([[sx, sy, sz] for sx in (-1, 1) for sy in (-1, 1)
                                      for sz in (-1, 1)]) * th) @ tR.T
            m_cam = min(m_cam, float(np.min(_in_camera_view(corners))))
            cam_rows.append({"t": round(r["t"], 4), "margin_m": m_cam, "clear": m_cam > 0})

    def _summ(hits, key):
        if not hits:
            return {"count": 0, "max_mm": 0.0}
        return {"count": len(hits), "max_mm": max(h[key] for h in hits), "first": hits[0]}

    return {
        "contact": contact_checks,
        "joint_limit_use_max": {j: float(u) for j, u in zip(ARM_JOINTS, lim_use)},
        "rail_range_use_max": float(rail_use),
        "joint_speed_use_max": {j: float(u) for j, u in zip(ARM_JOINTS, v_use)},
        "rail_speed_max_mps": rail_v, "rail_speed_use_max": rail_v / RAIL_VMAX,
        "rail_accel_max_mps2": a_rail,
        "robot_min_z_m": floor_min,
        "floor_ok": floor_min > 0.0,
        "pallet_column_penetration_mm": max(pallet_pen, 0.0) * 1e3 if pallet_pen > -math.inf else 0.0,
        "pallet_column_ok": pallet_pen <= 0.0,
        "links_vs_remaining_boxes": _summ(box_hits, "depth_mm"),
        "links_vs_remaining_boxes_min_clear_mm": link_box_min_clear * 1e3,
        "tool_vs_remaining_boxes": _summ(tool_box_hits, "pen_mm"),
        "carried_box_vs_remaining_boxes": _summ(carried_box_hits, "pen_mm"),
        "camera_view_at_capture": cam_rows,
        "camera_view_ok": all(c["clear"] for c in cam_rows),
        "cycle_s": [e["cycle_s"] for e in box_events],
    }


# --------------------------------------------------------------------------------------------
# Example / self-check
# --------------------------------------------------------------------------------------------

def example_picks() -> list[dict]:
    """Two layers: four lower boxes (top z = 0.394) and four upper boxes (top 0.574-0.694).
    Pick order: upper first.  Includes far corners (x = -0.45), centre, high, low, yaw ±40°."""
    lower_top = PALLET_TOP + 0.25
    A = (0.44, 0.30, 0.25)
    boxes = [
        # id, size, centre xy, yaw(deg), grasp xy offset (world), grasp yaw (deg), layer bottom
        (1, (0.40, 0.36, 0.30), (0.00, 0.00), 40, (0.0, 0.0), 40, lower_top),   # high, centre
        (2, (0.34, 0.24, 0.25), (0.30, 0.31), 0, (0.0, 0.0), 0, lower_top),
        (3, (0.36, 0.26, 0.20), (0.33, -0.33), -40, (0.0, 0.0), -40, lower_top),
        (4, (0.30, 0.22, 0.18), (-0.36, -0.33), 0, (0.0, 0.0), 0, lower_top),
        (5, A, (-0.32, 0.31), 90, (-0.10, 0.14), 90, PALLET_TOP),                # far corner +y
        (6, A, (-0.32, -0.32), 0, (-0.13, -0.08), 0, PALLET_TOP),                # far corner -y
        (7, A, (0.28, 0.28), 40, (0.0, 0.0), 40, PALLET_TOP),
        (8, A, (0.28, -0.28), -40, (0.0, 0.0), -40, PALLET_TOP),
    ]
    picks = []
    for bid, size, cxy, yaw, goff, gyaw, bottom in boxes:
        top = bottom + size[2]
        picks.append({
            "box_id": bid, "box_size": list(size),
            "box_top_center": [cxy[0], cxy[1], round(top, 4)],
            "box_yaw": math.radians(yaw),
            "grasp": [cxy[0] + goff[0], cxy[1] + goff[1], round(top, 4), math.radians(gyaw)],
            "normal": [0.0, 0.0, 1.0],
        })
    return picks


def _check_example_layout(picks: list[dict]) -> None:
    """Example boxes must not overlap each other and the pad must lie on its box top."""
    for i in range(len(picks)):
        ci, Ri = box_world_pose(picks[i])
        hi = np.array(picks[i]["box_size"]) / 2
        for j in range(i + 1, len(picks)):
            cj, Rj = box_world_pose(picks[j])
            hj = np.array(picks[j]["box_size"]) / 2
            pen = obb_overlap(ci, Ri, hi - 1e-4, cj, Rj, hj - 1e-4)
            assert pen <= 0, f"example boxes {picks[i]['box_id']} and {picks[j]['box_id']} overlap " \
                             f"by {pen * 1e3:.1f} mm"
        gx, gy, gz, gyaw = picks[i]["grasp"]
        R = rot_z(gyaw)
        for sx in (-1, 1):
            for sy in (-1, 1):
                c = np.array([gx, gy, 0]) + R @ np.array([sx * PAD_SIZE[0] / 2, sy * PAD_SIZE[1] / 2, 0])
                loc = (c - ci) @ Ri
                assert abs(loc[0]) <= hi[0] + 1e-6 and abs(loc[1]) <= hi[1] + 1e-6, \
                    f"pad corner off box {picks[i]['box_id']}"
        assert max(abs(gx), abs(gy)) <= 0.45 + 1e-9


def check_reach(base_xyz: tuple[float, float, float], targets: list[tuple[float, float, float]],
                use_rail: bool) -> list[tuple[tuple, bool, float]]:
    """Reach study: can the pad reach each target (tool straight down) with the base at
    ``base_xyz`` (rail aligned to the target y if ``use_rail``)?  Returns (target, ok, elbow_deg)
    where elbow_deg is |elbow angle| (0 = stretched, i.e. singular)."""
    b = {**DEFAULT_BASE, "x": base_xyz[0], "y": 0.0, "z": base_xyz[2],
         "rail": {**DEFAULT_BASE["rail"], "min": -1.0, "max": 1.0, "home": 0.0}}
    rob = Robot(b, DEFAULT_CONVEYOR)
    out = []
    for tg in targets:
        rail = (tg[1] - base_xyz[1]) if use_rail else base_xyz[1]
        try:
            q, _, _ = rob.ik_best(np.array(tg), tool_down_rotation(0.0), rail, _seeds(rob),
                                  ref=_seeds(rob)[0])
            out.append((tg, True, math.degrees(abs(q[2]))))
        except RuntimeError:
            out.append((tg, False, float("nan")))
    return out


def render_debug(plan: dict, picks: list[dict], out_dir: Path, times: list[tuple[str, float]]) -> list[str]:
    base = {k: v for k, v in plan["base"].items() if k in DEFAULT_BASE}
    robot = Robot(base, plan["conveyor"], picks)
    m, d = robot.model, robot.data
    try:
        renderer = mujoco.Renderer(m, 600, 800)
    except Exception as exc:  # no GL context
        print(f"[render] skipped: {exc}")
        return []
    frames = plan["frames"]
    written = []
    pick_by_id = {int(p["box_id"]): p for p in picks}
    ev = {b["box_id"]: b for b in plan["boxes"]}
    for label, tq in times:
        fr = min(frames, key=lambda f: abs(f["t"] - tq))
        q7 = np.array(fr["q"])
        d.qpos[robot.arm_qadr] = q7[:6]
        d.qpos[robot.rail_qadr] = q7[6]
        for i, pk in enumerate(picks):
            bid = int(pk["box_id"])
            e = ev[bid]
            if fr["attached"] == bid and fr["box_pose"] is not None:
                pose = fr["box_pose"]
            elif fr["t"] < e["t_contact"]:
                pose = e["initial_pose"]
            elif fr["t"] < e["t_release"] + 0.6:
                pose = e["placed_pose"]
            else:
                pose = [0, 0, -5, 1, 0, 0, 0]
            d.mocap_pos[i] = pose[:3]
            d.mocap_quat[i] = pose[3:]
        mujoco.mj_forward(m, d)
        for cam in ("overview", "side", "ceiling"):
            renderer.update_scene(d, camera=cam)
            img = renderer.render()
            path = out_dir / f"{label}_{cam}.png"
            _save_png(path, img)
            written.append(str(path))
    renderer.close()
    return written


def _save_png(path: Path, img: np.ndarray) -> None:
    try:
        from PIL import Image
        Image.fromarray(img).save(path)
    except ImportError:
        import imageio.v2 as iio
        iio.imwrite(path, img)


def main() -> int:
    out_dir = Path(os.environ.get("DEPAL_ROBOT_DEBUG", "")) if os.environ.get("DEPAL_ROBOT_DEBUG") else Path(__import__("tempfile").gettempdir()) / "depal_robot_debug"
    out_dir.mkdir(parents=True, exist_ok=True)
    picks = example_picks()
    _check_example_layout(picks)

    far = [(-0.45, 0.45, 0.394 + 0.25 + 0.0), (-0.45, -0.45, 0.394), (-0.45, 0.0, 0.70 + 0.25),
           (0.45, 0.45, 0.394), (0.45, 0.0, 0.70 + 0.25)]
    print("== reach study (tool straight down) ==")
    for label, bxyz, rail in (("suggested (0.85,0,0.50) fixed", (0.85, 0.0, 0.50), False),
                              ("(0.85,0,0.50) + y-rail", (0.85, 0.0, 0.50), True),
                              ("chosen (0.72,0,0.75) + y-rail", (DEFAULT_BASE["x"], 0.0,
                                                                 DEFAULT_BASE["z"]), True)):
        res = check_reach(bxyz, far, rail)
        print(f"  {label:34s} " + "  ".join(
            f"{tg[0]:+.2f},{tg[1]:+.2f},{tg[2]:.2f}:{'ok' if ok else 'NO'}"
            + (f"(elbow {el:.0f}°)" if ok else "") for tg, ok, el in res))

    plan = plan_motion(picks, fps=30)
    js = out_dir / "motion_example.json"
    js.write_text(json.dumps(plan, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"\nwrote {js}  ({js.stat().st_size / 1e6:.1f} MB, {len(plan['frames'])} frames, "
          f"{plan['duration_s']:.2f} s)")

    c = plan["checks"]
    print("\n== contact (IK convergence at the contact instant) ==")
    print(" box  cycle  t_contact  pos_err[mm]  rot_err[deg]  normal_err[deg]  rail_pick  rail_drop"
          "  lift_z  cycle[s]")
    for row, cyc in zip(c["contact"], c["cycle_s"]):
        print(f" {row['box_id']:3d}  {row['cycle']:5d}  {row['t_contact']:9.3f}  "
              f"{row['pos_err_mm']:11.6f}  {row['rot_err_deg']:12.6f}  {row['normal_err_deg']:15.6f}"
              f"  {row['rail']:+9.3f}  {row['rail_drop']:+9.3f}  {row['lift_z']:6.3f}  {cyc:7.3f}")
    print(f" cycle time: mean {np.mean(c['cycle_s']):.2f} s, min {min(c['cycle_s']):.2f}, "
          f"max {max(c['cycle_s']):.2f}")
    print("\n== joint usage (max over all frames) ==")
    print(" joint                 limit_use  speed_use")
    for j in ARM_JOINTS:
        print(f" {j:20s}  {c['joint_limit_use_max'][j]:9.3f}  {c['joint_speed_use_max'][j]:9.3f}")
    print(f" rail                  {c['rail_range_use_max']:9.3f}  {c['rail_speed_use_max']:9.3f}"
          f"   (v_max {c['rail_speed_max_mps']:.2f} m/s, a_max {c['rail_accel_max_mps2']:.2f} m/s²)")
    print("\n== collisions / view ==")
    print(f" robot lowest vertex z         : {c['robot_min_z_m']:.3f} m  floor_ok={c['floor_ok']}")
    print(f" pallet column penetration     : {c['pallet_column_penetration_mm']:.2f} mm  "
          f"ok={c['pallet_column_ok']}")
    print(f" links vs remaining boxes      : {c['links_vs_remaining_boxes']}  "
          f"(min clearance {c['links_vs_remaining_boxes_min_clear_mm']:.1f} mm)")
    print(f" tool vs remaining boxes       : {c['tool_vs_remaining_boxes']}")
    print(f" carried box vs remaining boxes: {c['carried_box_vs_remaining_boxes']}")
    print(" camera view at capture        : " + ", ".join(
        f"t={r['t']:.2f}:{'clear' if r['clear'] else 'BLOCKED'}({r['margin_m'] * 100:+.0f}cm)"
        for r in c["camera_view_at_capture"]))
    print(f" OBJ <-> MuJoCo vertices max   : {c['obj_vs_mujoco_max_mm']:.6f} mm")

    # debug renders: first frame, a contact, its lift, over the conveyor
    b0 = plan["boxes"][4]
    tl = next(f["t"] for f in plan["frames"] if f["cycle"] == b0["cycle"] and f["phase"] == "transfer")
    tr = next(f["t"] for f in plan["frames"] if f["cycle"] == b0["cycle"] and f["phase"] == "place")
    pngs = render_debug(plan, picks, out_dir, [
        ("f0_capture", 0.0), ("f1_contact", b0["t_contact"]), ("f2_lift", tl),
        ("f3_conveyor", tr + 0.2)])
    for p in pngs:
        print("png:", p)
    ok = (c["floor_ok"] and c["pallet_column_ok"] and c["camera_view_ok"]
          and max(c["joint_speed_use_max"].values()) <= 1.0 and c["rail_speed_use_max"] <= 1.0
          and c["links_vs_remaining_boxes"]["count"] == 0
          and c["carried_box_vs_remaining_boxes"]["count"] == 0
          and c["tool_vs_remaining_boxes"]["count"] == 0
          and max(r["pos_err_mm"] for r in c["contact"]) < 0.1
          and max(r["rot_err_deg"] for r in c["contact"]) < 0.01)
    print("\nALL CHECKS", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
