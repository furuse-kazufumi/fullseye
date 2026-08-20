"""Robot pick-and-place, rendered **headless** as a GIF (genuine physics).

A Franka Panda arm reaches for a cube, closes its gripper, lifts it by real
contact + friction (nothing is glued — if the grip were too weak the cube would
slip, and we *measure* the lift height afterwards), swings aside and releases.

The scene is MuJoCo Menagerie's ``franka_emika_panda/mjx_single_cube.xml`` (a
panda + a free-floating cube). The arm is steered with **differential inverse
kinematics** (a damped-least-squares Jacobian step on the 7 arm joints drives the
hand to Cartesian way-points), the gripper by its one position actuator, and the
world is advanced with ``mj_step`` — so the grasp is earned by contact, not
scripted onto the object's pose. Rendering uses MuJoCo's offscreen renderer
(works headless on Windows).

    import pick_render as PR
    PR.render_pick_gif("out/panda_pick.gif")            # -> dict incl. measured lift
"""
from __future__ import annotations
import os

import numpy as np

_MENAGERIE = "C:/dev/projects/mujoco_menagerie"
_PANDA_CUBE = f"{_MENAGERIE}/franka_emika_panda/mjx_single_cube.xml"

_HOME_ARM = np.array([0.0, 0.3, 0.0, -1.57079, 0.0, 2.0, -0.7853])
_GRIP_OPEN, _GRIP_SHUT = 0.04, 0.0
# Hand-body height above the cube centre at which the fingers straddle the cube.
_GRASP_H = 0.105


def _cube_z(d, a):
    return float(d.qpos[a + 2])


def _tcp(d, ids):
    """World position of the grasp point = midpoint of the two finger bodies."""
    return np.mean([d.xpos[i] for i in ids], axis=0)


def _ik_solve(mujoco, m, dk, hand_id, goal_hand, quat_target, seed, *,
              iters=120, damp=0.12, step_clamp=0.10, tol=1e-3):
    """**Kinematic** 6-DOF IK: solve for the 7 arm-joint angles that put the hand
    body at *goal_hand* with orientation *quat_target* (gripper pointing down). Runs
    on a scratch ``MjData`` with damped-least-squares Newton steps (no dynamics), so
    it converges cleanly; the physics loop then just servos to the answer. Returns
    the 7 target angles (falls back to the last iterate if it doesn't fully converge)."""
    dk.qpos[:7] = seed
    q = np.array(seed, dtype=float)
    for _ in range(iters):
        dk.qpos[:7] = q
        mujoco.mj_kinematics(m, dk); mujoco.mj_comPos(m, dk)
        perr = np.asarray(goal_hand) - dk.xpos[hand_id]
        oerr = np.zeros(3)
        mujoco.mju_subQuat(oerr, np.asarray(quat_target), dk.xquat[hand_id])
        if np.linalg.norm(perr) < tol and np.linalg.norm(oerr) < 10 * tol:
            break
        jacp = np.zeros((3, m.nv)); jacr = np.zeros((3, m.nv))
        mujoco.mj_jacBody(m, dk, jacp, jacr, hand_id)
        J = np.vstack([jacp[:, :7], jacr[:, :7]])
        err = np.concatenate([perr, oerr])
        dq = J.T @ np.linalg.solve(J @ J.T + damp * np.eye(6), err)
        q = q + np.clip(dq, -step_clamp, step_clamp)
        lo, hi = m.jnt_range[:7, 0], m.jnt_range[:7, 1]
        q = np.clip(q, lo, hi)                                    # respect joint limits
    return q


def render_pick_gif(out_gif, *, width=640, height=480, fps=30, max_gif_frames=120,
                    azimuth=135.0, elevation=-20.0, distance=1.6, lookat=(0.4, -0.05, 0.25),
                    place_offset=(-0.22, -0.28), log=print):
    """Run a genuine-physics pick-and-place and save it as a GIF. The lift height
    is measured from the simulation, so success is reported from data."""
    import mujoco
    from PIL import Image

    if not os.path.exists(_PANDA_CUBE):
        raise FileNotFoundError(f"panda cube scene not found: {_PANDA_CUBE} "
                                "(needs the MuJoCo Menagerie checkout)")
    m = mujoco.MjModel.from_xml_path(_PANDA_CUBE)
    d = mujoco.MjData(m)
    mujoco.mj_resetDataKeyframe(m, d, 0)                           # 'home' arm pose

    box_qadr = None
    for j in range(m.njnt):
        if int(m.jnt_type[j]) == int(mujoco.mjtJoint.mjJNT_FREE):
            box_qadr = int(m.jnt_qposadr[j]); break
    if box_qadr is None:
        raise RuntimeError("no free joint (cube) found in the scene")
    d.qpos[box_qadr:box_qadr + 7] = [0.5, 0.0, 0.03, 1.0, 0.0, 0.0, 0.0]
    d.qvel[:] = 0.0
    d.ctrl[:7] = _HOME_ARM; d.ctrl[7] = _GRIP_OPEN
    mujoco.mj_forward(m, d)
    hand_id = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "hand")
    lf = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "left_finger")
    rf = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "right_finger")
    ids = [lf, rf]
    rest_z = _cube_z(d, box_qadr)
    bx, by = float(d.qpos[box_qadr]), float(d.qpos[box_qadr + 1])
    # Lock the gripper to its home orientation (fingers pointing down). The grasp
    # point (finger midpoint) sits at a fixed offset below the hand frame in that
    # orientation, so hand_goal = grasp_goal − offset reaches the cube cleanly.
    quat_target = d.xquat[hand_id].copy()
    offset = _tcp(d, ids) - d.xpos[hand_id]

    def hg(gx, gy, gz):
        return np.array([gx, gy, gz]) - offset                    # grasp-point goal → hand-body goal

    dt = float(m.opt.timestep)
    lift_top = 0.38
    grasp_z = rest_z + 0.005                                       # finger midpoint at cube centre
    # (grasp-point goal, gripper, seconds).
    phases = [
        (hg(bx, by, 0.16), _GRIP_OPEN, 1.3),                      # move above cube
        (hg(bx, by, grasp_z), _GRIP_OPEN, 1.4),                   # descend around it
        (hg(bx, by, grasp_z), _GRIP_OPEN, 0.3),                   # settle
        (hg(bx, by, grasp_z), _GRIP_SHUT, 0.9),                   # close (grasp)
        (hg(bx, by, lift_top), _GRIP_SHUT, 1.4),                  # lift straight up
        (hg(bx + place_offset[0], by + place_offset[1], lift_top), _GRIP_SHUT, 1.5),  # carry aside
        (hg(bx + place_offset[0], by + place_offset[1], lift_top), _GRIP_SHUT, 0.3),  # steady
        (hg(bx + place_offset[0], by + place_offset[1], lift_top), _GRIP_OPEN, 0.7),  # release
    ]
    n_steps = int(round(sum(p[2] for p in phases) / dt))
    frame_every = max(1, n_steps // int(max_gif_frames))

    ren = mujoco.Renderer(m, height=height, width=width)
    cam = mujoco.MjvCamera(); cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    cam.lookat[:] = list(lookat); cam.distance = float(distance)
    cam.elevation = float(elevation)

    frames = []
    peak_z = rest_z
    step_i = 0
    for goal, grip, secs in phases:
        seg_steps = max(1, int(round(secs / dt)))
        for _ in range(seg_steps):
            d.ctrl[:7] = _ik_step(mujoco, m, d, hand_id, goal, quat_target)
            d.ctrl[7] = grip
            mujoco.mj_step(m, d)
            peak_z = max(peak_z, _cube_z(d, box_qadr))
            if step_i % frame_every == 0:
                cam.azimuth = azimuth + 40.0 * (step_i / max(1, n_steps))
                ren.update_scene(d, camera=cam)
                frames.append(Image.fromarray(ren.render()))
            step_i += 1
    ren.close()

    final_z = _cube_z(d, box_qadr)
    lift = peak_z - rest_z
    frames[0].save(out_gif, save_all=True, append_images=frames[1:],
                   duration=int(1000 / max(1, fps)), loop=0)
    grasped = lift > 0.06
    log(f"pick GIF: {len(frames)} frames -> {out_gif} | "
        f"lift={lift*100:.1f}cm peak_z={peak_z:.3f} final_z={final_z:.3f} "
        f"grasped={'yes' if grasped else 'no'}")
    return {"gif": out_gif, "frames": len(frames), "lift_m": lift, "peak_z": peak_z,
            "final_z": final_z, "rest_z": rest_z, "grasped": bool(grasped)}


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "out/panda_pick.gif"
    r = render_pick_gif(out, log=lambda s: print(s, flush=True))
    print(r)
