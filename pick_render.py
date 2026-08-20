"""Robot pick-and-place, rendered **headless** as a GIF (genuine physics).

A Franka Panda arm reaches for a cube, closes its gripper, lifts it by real
contact + friction (nothing is glued to the hand — the cube is a free body held
only by the fingers, and we *measure* its height afterwards), swings it aside and
releases. The scene is MuJoCo Menagerie's ``franka_emika_panda/mjx_single_cube.xml``.

The trajectory is a small set of joint-space way-points derived from the scene's
own tuned ``home``/``pickup`` keyframes (the authors calibrated the pickup pose so
the fingers straddle the cube). We interpolate the 7 arm-joint targets and the
gripper actuator between way-points and advance the world with ``mj_step`` — so
the grasp is earned by the contact solver, not scripted onto the object's pose.
Rendering uses MuJoCo's offscreen renderer (works headless on Windows).

    import pick_render as PR
    PR.render_pick_gif("out/panda_pick.gif")            # -> dict incl. measured lift
"""
from __future__ import annotations
import os

import numpy as np

_MENAGERIE = "C:/dev/projects/mujoco_menagerie"
_PANDA_CUBE = f"{_MENAGERIE}/franka_emika_panda/mjx_single_cube.xml"

_GRIP_OPEN, _GRIP_SHUT = 0.04, 0.0


def _cube_z(d, a):
    return float(d.qpos[a + 2])


def render_pick_gif(out_gif, *, width=640, height=480, fps=30, max_gif_frames=120,
                    azimuth=138.0, elevation=-18.0, distance=1.55, lookat=(0.42, 0.02, 0.22),
                    carry_yaw=-0.75, log=print):
    """Run a genuine-physics pick-and-place and save it as a GIF. The lift height
    is measured from the simulation, so success is reported from data, not asserted.

    Returns a dict with ``lift_m`` (peak cube rise), ``grasped`` (cleared the table),
    and ``placed_z`` (final cube height after release)."""
    import mujoco
    from PIL import Image

    if not os.path.exists(_PANDA_CUBE):
        raise FileNotFoundError(f"panda cube scene not found: {_PANDA_CUBE} "
                                "(needs the MuJoCo Menagerie checkout)")
    m = mujoco.MjModel.from_xml_path(_PANDA_CUBE)
    d = mujoco.MjData(m)

    box_qadr = None
    for j in range(m.njnt):
        if int(m.jnt_type[j]) == int(mujoco.mjtJoint.mjJNT_FREE):
            box_qadr = int(m.jnt_qposadr[j]); break
    if box_qadr is None:
        raise RuntimeError("no free joint (cube) found in the scene")

    # Way-points come from the scene's own keyframes: 'home' (arm up) and 'pickup'
    # (fingers straddling the cube). The cube starts where the pickup pose reaches.
    home_arm = m.key_qpos[0, :7].copy()
    pick_arm = m.key_qpos[1, :7].copy()
    pick_box = m.key_qpos[1, -7:].copy()

    mujoco.mj_resetDataKeyframe(m, d, 0)                           # home arm pose
    d.qpos[box_qadr:box_qadr + 7] = pick_box                      # cube under the grasp
    d.qvel[:] = 0.0
    d.ctrl[:7] = home_arm; d.ctrl[7] = _GRIP_OPEN
    mujoco.mj_forward(m, d)
    rest_z = _cube_z(d, box_qadr)

    carry_arm = home_arm.copy(); carry_arm[0] += float(carry_yaw)  # swing the base aside
    # (arm_from, arm_to, gripper, seconds)
    phases = [
        (home_arm, pick_arm, _GRIP_OPEN, 1.5),                    # reach down to the cube
        (pick_arm, pick_arm, _GRIP_OPEN, 0.3),                    # settle
        (pick_arm, pick_arm, _GRIP_SHUT, 0.8),                    # close the gripper (grasp)
        (pick_arm, home_arm, _GRIP_SHUT, 1.5),                    # lift straight up
        (home_arm, carry_arm, _GRIP_SHUT, 1.4),                   # carry it aside
        (carry_arm, carry_arm, _GRIP_SHUT, 0.3),                  # steady
        (carry_arm, carry_arm, _GRIP_OPEN, 0.8),                  # release
    ]
    dt = float(m.opt.timestep)
    n_steps = int(round(sum(p[3] for p in phases) / dt))
    frame_every = max(1, n_steps // int(max_gif_frames))

    ren = mujoco.Renderer(m, height=height, width=width)
    cam = mujoco.MjvCamera(); cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    cam.lookat[:] = list(lookat); cam.distance = float(distance); cam.elevation = float(elevation)

    frames = []
    peak_z = rest_z
    step_i = 0
    for a_from, a_to, grip, secs in phases:
        seg = max(1, int(round(secs / dt)))
        for k in range(seg):
            frac = (k + 1) / seg
            d.ctrl[:7] = a_from + (a_to - a_from) * frac
            d.ctrl[7] = grip
            mujoco.mj_step(m, d)
            peak_z = max(peak_z, _cube_z(d, box_qadr))
            if step_i % frame_every == 0:
                cam.azimuth = azimuth + 42.0 * (step_i / max(1, n_steps))
                ren.update_scene(d, camera=cam)
                frames.append(Image.fromarray(ren.render()))
            step_i += 1
    ren.close()

    placed_z = _cube_z(d, box_qadr)
    lift = peak_z - rest_z
    grasped = lift > 0.10                                          # cube clearly cleared the table
    frames[0].save(out_gif, save_all=True, append_images=frames[1:],
                   duration=int(1000 / max(1, fps)), loop=0)
    log(f"pick GIF: {len(frames)} frames -> {out_gif} | "
        f"lift={lift*100:.1f}cm peak_z={peak_z:.3f} placed_z={placed_z:.3f} "
        f"grasped={'yes' if grasped else 'no'}")
    return {"gif": out_gif, "frames": len(frames), "lift_m": lift, "peak_z": peak_z,
            "placed_z": placed_z, "rest_z": rest_z, "grasped": bool(grasped)}


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "out/panda_pick.gif"
    r = render_pick_gif(out, log=lambda s: print(s, flush=True))
    print(r)
