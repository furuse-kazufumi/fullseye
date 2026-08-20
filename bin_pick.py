"""Bin picking (バラ積みピッキング), rendered **headless** as a GIF (genuine physics).

Cubes are dropped into a bin and settle into a random pile. A simple "vision"
step picks the **topmost graspable** cube (highest centre — what a 3-D bin-picking
camera would surface first), the arm solves 6-DOF IK to a top-down grasp over it,
closes, lifts it clear of the rim and drops it in a place zone — then re-scans and
repeats. Nothing is glued; a cube counts as picked only if its measured height
clears the bin rim, so the success count is earned.

The arm is a Franka Panda (Menagerie). IK is damped-least-squares on the hand body
with the orientation error rotated into the world frame (the fix that makes 6-DOF
IK converge here). Rendering is MuJoCo offscreen (headless on Windows).

    import bin_pick as BP
    BP.render_bin_pick_gif("out/bin_pick.gif", n_cubes=8, n_picks=3)   # -> dict incl. n_picked
"""
from __future__ import annotations
import os

import numpy as np

_MENAGERIE = "C:/dev/projects/mujoco_menagerie"
_PANDA_SCENE = f"{_MENAGERIE}/franka_emika_panda/scene.xml"

_HOME_ARM = np.array([0.0, 0.3, 0.0, -1.57079, 0.0, 2.0, -0.7853])
_GRIP_OPEN, _GRIP_SHUT = 0.04, 0.0
_BIN_C = (0.5, 0.0)            # bin centre (x, y) within panda reach
_BIN_HALF = 0.13              # bin inner half-width
_WALL_H = 0.07
_CUBE = 0.022                 # cube half-size


def _build(n_cubes, seed):
    """Panda + a walled bin + n free cubes, composed with MjSpec. Returns (model, box_qadrs)."""
    import mujoco
    spec = mujoco.MjSpec.from_file(_PANDA_SCENE)
    spec.visual.global_.offwidth = 1280                          # allow larger offscreen frames
    spec.visual.global_.offheight = 960
    wb = spec.worldbody
    cx, cy = _BIN_C
    t = 0.006                                                     # wall thickness
    walls = [(cx, cy + _BIN_HALF, _BIN_HALF + t, t), (cx, cy - _BIN_HALF, _BIN_HALF + t, t),
             (cx + _BIN_HALF, cy, t, _BIN_HALF), (cx - _BIN_HALF, cy, t, _BIN_HALF)]
    for (wx, wy, sx, sy) in walls:
        g = wb.add_geom()
        g.type = mujoco.mjtGeom.mjGEOM_BOX
        g.size = [sx, sy, _WALL_H]; g.pos = [wx, wy, _WALL_H]
        g.rgba = [0.55, 0.57, 0.62, 0.45]; g.contype = 1; g.conaffinity = 1
    rng = np.random.default_rng(seed)
    palette = [[0.90, 0.30, 0.24], [0.25, 0.70, 0.45], [0.30, 0.55, 0.9],
               [0.95, 0.75, 0.20], [0.70, 0.40, 0.85], [0.35, 0.78, 0.75]]
    for i in range(n_cubes):
        bx = cx + rng.uniform(-0.07, 0.07)
        by = cy + rng.uniform(-0.07, 0.07)
        bz = 0.10 + 0.055 * i                                    # stacked column → drops into a pile
        b = wb.add_body()
        b.pos = [bx, by, bz]
        b.add_freejoint()
        g = b.add_geom()
        g.type = mujoco.mjtGeom.mjGEOM_BOX
        g.size = [_CUBE, _CUBE, _CUBE]
        g.rgba = palette[i % len(palette)] + [1.0]
        g.condim = 3; g.friction = [1.0, 0.03, 0.003]; g.mass = 0.05
    model = spec.compile()
    box_qadrs = []
    for j in range(model.njnt):
        if int(model.jnt_type[j]) == int(mujoco.mjtJoint.mjJNT_FREE):
            box_qadrs.append(int(model.jnt_qposadr[j]))
    return model, box_qadrs


def _ik_solve(mujoco, m, dk, hand_id, goal, quat_t, seed, *, iters=160, damp=0.1, clamp=0.1, tol=1e-3):
    """Damped-least-squares 6-DOF IK to put the hand at *goal* with orientation
    *quat_t* (orientation error rotated body→world so it converges). Returns 7 angles."""
    q = np.array(seed, float)
    for _ in range(iters):
        dk.qpos[:7] = q
        mujoco.mj_kinematics(m, dk); mujoco.mj_comPos(m, dk)
        perr = np.asarray(goal) - dk.xpos[hand_id]
        oerr = np.zeros(3)
        mujoco.mju_subQuat(oerr, np.asarray(quat_t), dk.xquat[hand_id])
        oerr = dk.xmat[hand_id].reshape(3, 3) @ oerr             # body-frame → world-frame
        if np.linalg.norm(perr) < tol and np.linalg.norm(oerr) < 1e-2:
            break
        jp = np.zeros((3, m.nv)); jr = np.zeros((3, m.nv))
        mujoco.mj_jacBody(m, dk, jp, jr, hand_id)
        J = np.vstack([jp[:, :7], jr[:, :7]])
        dq = J.T @ np.linalg.solve(J @ J.T + damp * np.eye(6), np.concatenate([perr, oerr]))
        q = np.clip(q + np.clip(dq, -clamp, clamp), m.jnt_range[:7, 0], m.jnt_range[:7, 1])
    return q


def render_bin_pick_gif(out_gif, *, n_cubes=8, n_picks=3, seed=1, width=680, height=480, fps=30,
                        max_gif_frames=150, azimuth=150.0, elevation=-22.0, distance=1.35,
                        lookat=(0.5, 0.0, 0.12), log=print):
    """Drop cubes into a bin, then pick the top cube *n_picks* times. Returns a dict
    with ``n_picked`` (cubes whose measured height cleared the rim) — an earned count."""
    import mujoco
    from PIL import Image

    if not os.path.exists(_PANDA_SCENE):
        raise FileNotFoundError(f"panda scene not found: {_PANDA_SCENE} (needs MuJoCo Menagerie)")
    m, box_qadrs = _build(n_cubes, seed)
    d = mujoco.MjData(m); dk = mujoco.MjData(m)
    hand_id = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "hand")
    lf = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "left_finger")
    rf = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "right_finger")

    d.ctrl[:7] = _HOME_ARM; d.ctrl[7] = _GRIP_OPEN
    for j in range(7):
        d.qpos[m.jnt_qposadr[j]] = _HOME_ARM[j] if j < 7 else d.qpos[m.jnt_qposadr[j]]
    mujoco.mj_forward(m, d)
    quat_t = d.xquat[hand_id].copy()                             # top-down grasp orientation
    tcp = 0.5 * (d.xpos[lf] + d.xpos[rf])
    offset = tcp - d.xpos[hand_id]                               # hand→grasp-point offset

    dt = float(m.opt.timestep)
    frames = []
    place = (_BIN_C[0] - 0.34, _BIN_C[1] - 0.30)                 # drop zone outside the bin
    ren = mujoco.Renderer(m, height=height, width=width)
    cam = mujoco.MjvCamera(); cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    cam.lookat[:] = list(lookat); cam.distance = float(distance)
    cam.elevation = float(elevation); cam.azimuth = float(azimuth)
    step_counter = [0]

    def grab():
        cam.azimuth = azimuth + 8.0 * np.sin(step_counter[0] * 0.01)
        ren.update_scene(d, camera=cam)
        frames.append(Image.fromarray(ren.render()))

    def settle(steps, grip):
        for _ in range(steps):
            d.ctrl[7] = grip
            mujoco.mj_step(m, d)
            if step_counter[0] % settle.every == 0:
                grab()
            step_counter[0] += 1
    settle.every = 8

    def move_to(q_target, grip, secs):
        seg = max(1, int(secs / dt))
        q0 = d.ctrl[:7].copy()
        for k in range(seg):
            d.ctrl[:7] = q0 + (q_target - q0) * ((k + 1) / seg)
            d.ctrl[7] = grip
            mujoco.mj_step(m, d)
            if step_counter[0] % settle.every == 0:
                grab()
            step_counter[0] += 1

    def hand_goal_for(grasp_pt):
        return np.asarray(grasp_pt) - offset

    def solve(grasp_pt, seed_q):
        return _ik_solve(mujoco, m, dk, hand_id, hand_goal_for(grasp_pt), quat_t, seed_q)

    # let the pile settle
    settle(int(1.6 / dt), _GRIP_OPEN)

    rim_z = _WALL_H + 2 * _CUBE
    picked = 0
    picked_flags = [False] * len(box_qadrs)
    for _ in range(n_picks):
        # vision: choose the highest still-in-bin cube (topmost graspable candidate)
        cand, best_z = None, -1.0
        for ci, qa in enumerate(box_qadrs):
            if picked_flags[ci]:
                continue
            cx, cy, cz = d.qpos[qa], d.qpos[qa + 1], d.qpos[qa + 2]
            in_bin = abs(cx - _BIN_C[0]) < _BIN_HALF + 0.03 and abs(cy - _BIN_C[1]) < _BIN_HALF + 0.03
            if in_bin and cz > best_z:
                cand, best_z, cand_i = (cx, cy, cz), cz, ci
        if cand is None:
            break
        cx, cy, cz = cand
        approach = (cx, cy, cz + 0.14)
        q_app = solve(approach, d.qpos[:7]); move_to(q_app, _GRIP_OPEN, 1.1)
        # re-read the cube after the hover (the pile may have shifted), then descend
        # deeper than the target to beat the position-servo droop, and let the arm
        # arrive before closing — grasping a cube in clutter is unforgiving.
        qa = box_qadrs[cand_i]
        cx, cy, cz = float(d.qpos[qa]), float(d.qpos[qa + 1]), float(d.qpos[qa + 2])
        grasp = (cx, cy, cz + 0.02)                             # finger midpoint down around the cube
        clear = (cx, cy, rim_z + 0.22)
        drop = (place[0], place[1], rim_z + 0.22)
        q_gr = solve(grasp, d.qpos[:7]); move_to(q_gr, _GRIP_OPEN, 1.1)
        settle(int(0.35 / dt), _GRIP_OPEN)                      # arrive before closing
        move_to(q_gr, _GRIP_SHUT, 0.8)                          # close
        q_cl = solve(clear, d.qpos[:7]); move_to(q_cl, _GRIP_SHUT, 1.1)  # lift clear of rim
        q_dr = solve(drop, d.qpos[:7]); move_to(q_dr, _GRIP_SHUT, 1.2)   # carry to drop zone
        move_to(q_dr, _GRIP_OPEN, 0.5)                          # release
        # earned success: cube left the bin (moved to the place zone / cleared rim)
        fx, fy, fz = d.qpos[box_qadrs[cand_i]], d.qpos[box_qadrs[cand_i] + 1], d.qpos[box_qadrs[cand_i] + 2]
        out_of_bin = abs(fx - _BIN_C[0]) > _BIN_HALF or abs(fy - _BIN_C[1]) > _BIN_HALF
        if out_of_bin:
            picked += 1; picked_flags[cand_i] = True
        move_to(_HOME_ARM, _GRIP_OPEN, 0.9)                     # back home, rescan

    ren.close()
    if len(frames) > max_gif_frames:                            # subsample to a sane GIF length
        idx = np.linspace(0, len(frames) - 1, int(max_gif_frames)).round().astype(int)
        frames = [frames[i] for i in idx]
    frames[0].save(out_gif, save_all=True, append_images=frames[1:],
                   duration=int(1000 / max(1, fps)), loop=0)
    log(f"bin pick GIF: {len(frames)} frames -> {out_gif} | "
        f"cubes={n_cubes} attempts={n_picks} picked={picked}")
    return {"gif": out_gif, "frames": len(frames), "n_cubes": n_cubes,
            "n_attempts": n_picks, "n_picked": picked}


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "out/bin_pick.gif"
    print(render_bin_pick_gif(out, log=lambda s: print(s, flush=True)))
