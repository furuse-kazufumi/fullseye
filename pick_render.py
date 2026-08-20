"""Robot pick-and-place, rendered **headless** as a GIF (genuine physics).

A Franka Panda arm reaches for a cube, closes its gripper, lifts it by real
contact + friction (nothing is glued — if the grip were too weak the cube would
slip, and we *measure* the lift height afterwards), swings aside and releases.

The scene is MuJoCo Menagerie's ``franka_emika_panda/mjx_single_cube.xml`` (a
panda + a free-floating cube + tuned ``home``/``pickup`` keyframes). We drive the
8 position actuators (7 arm joints + 1 gripper) through waypoints and step the
physics, so the grasp is earned, not scripted onto the object's pose. Rendering
uses MuJoCo's offscreen renderer (works headless on Windows).

    import pick_render as PR
    PR.render_pick_gif("out/panda_pick.gif")            # -> dict incl. lift height
"""
from __future__ import annotations
import os

import numpy as np

_MENAGERIE = "C:/dev/projects/mujoco_menagerie"
_PANDA_CUBE = f"{_MENAGERIE}/franka_emika_panda/mjx_single_cube.xml"

# 8-dim ctrl (actuator1..7 = arm, actuator8 = gripper; 0.04 open, 0.0 closed).
_HOME = np.array([0.0, 0.3, 0.0, -1.57079, 0.0, 2.0, -0.7853, 0.04])
_PICK = np.array([0.2897, 0.423, -0.144392, -2.13105, -0.0291743, 2.52586, -0.492492, 0.04])


def _segments():
    """(target_ctrl, seconds) waypoints for reach → grasp → lift → place → release."""
    arm_home, arm_pick = _HOME[:7], _PICK[:7]
    lift = np.concatenate([arm_home, [0.0]])                       # raise, gripper closed
    place = np.concatenate([[-0.7], arm_home[1:], [0.0]])          # swing base aside, still closed
    place_open = np.concatenate([[-0.7], arm_home[1:], [0.04]])    # release over the drop spot
    return [
        (_PICK.copy(), 1.6),                                       # reach down to the cube (open)
        (_PICK.copy(), 0.3),                                       # settle
        (np.concatenate([_PICK[:7], [0.0]]), 0.9),                 # close gripper (grasp)
        (lift, 1.4),                                               # lift straight up
        (place, 1.3),                                              # carry aside
        (place, 0.4),                                              # steady
        (place_open, 0.7),                                         # release
    ]


def _cube_z(d, box_qadr):
    return float(d.qpos[box_qadr + 2])


def render_pick_gif(out_gif, *, width=640, height=480, fps=30, max_gif_frames=110,
                    azimuth=135.0, elevation=-20.0, distance=1.6, lookat=(0.45, 0.0, 0.25),
                    log=print):
    """Run a genuine-physics pick-and-place and save it as a GIF. Returns a dict
    with the measured lift height so success is reported from data, not asserted."""
    import mujoco
    from PIL import Image

    if not os.path.exists(_PANDA_CUBE):
        raise FileNotFoundError(f"panda cube scene not found: {_PANDA_CUBE} "
                                "(needs the MuJoCo Menagerie checkout)")
    m = mujoco.MjModel.from_xml_path(_PANDA_CUBE)
    d = mujoco.MjData(m)
    mujoco.mj_resetDataKeyframe(m, d, 0)                           # 'home' arm pose

    # Locate the free joint's qpos address robustly (jnt_type FREE == 0).
    box_qadr = None
    for j in range(m.njnt):
        if int(m.jnt_type[j]) == int(mujoco.mjtJoint.mjJNT_FREE):
            box_qadr = int(m.jnt_qposadr[j]); break
    if box_qadr is None:
        raise RuntimeError("no free joint (cube) found in the scene")
    # The 'home' keyframe parks the cube at x=0.7, but the 'pickup' pose reaches to
    # x≈0.5 — put the cube where the gripper actually descends, or it grasps thin air.
    d.qpos[box_qadr:box_qadr + 7] = [0.5, 0.0, 0.03, 1.0, 0.0, 0.0, 0.0]
    d.qvel[:] = 0.0
    mujoco.mj_forward(m, d)
    z0 = _cube_z(d, box_qadr)
    z_rest = z0                                                    # table-rest height

    dt = float(m.opt.timestep)
    segs = _segments()
    total_s = sum(s for _, s in segs)
    n_steps = int(round(total_s / dt))
    frame_every = max(1, n_steps // int(max_gif_frames))

    ren = mujoco.Renderer(m, height=height, width=width)
    cam = mujoco.MjvCamera(); cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    cam.lookat[:] = list(lookat); cam.distance = float(distance)
    cam.azimuth = float(azimuth); cam.elevation = float(elevation)

    ctrl0 = _HOME.copy()
    d.ctrl[:] = ctrl0
    frames = []
    z_grasp_peak = z_rest
    step_i = 0
    seg_start_ctrl = ctrl0.copy()
    for target, secs in segs:
        seg_steps = max(1, int(round(secs / dt)))
        for k in range(seg_steps):
            frac = (k + 1) / seg_steps
            d.ctrl[:] = seg_start_ctrl + (target - seg_start_ctrl) * frac
            mujoco.mj_step(m, d)
            if step_i % frame_every == 0:
                cam.azimuth = azimuth + 30.0 * (step_i / max(1, n_steps))   # gentle orbit
                ren.update_scene(d, camera=cam)
                frames.append(Image.fromarray(ren.render()))
            z_grasp_peak = max(z_grasp_peak, _cube_z(d, box_qadr))
            step_i += 1
        seg_start_ctrl = target.copy()
    ren.close()

    z_final = _cube_z(d, box_qadr)
    lift = z_grasp_peak - z_rest
    frames[0].save(out_gif, save_all=True, append_images=frames[1:],
                   duration=int(1000 / max(1, fps)), loop=0)
    grasped = lift > 0.06                                          # cube clearly left the table
    log(f"pick GIF: {len(frames)} frames -> {out_gif} | "
        f"lift={lift*100:.1f}cm peak_z={z_grasp_peak:.3f} final_z={z_final:.3f} "
        f"grasped={'yes' if grasped else 'no'}")
    return {"gif": out_gif, "frames": len(frames), "lift_m": lift, "peak_z": z_grasp_peak,
            "final_z": z_final, "rest_z": z_rest, "grasped": bool(grasped)}


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "out/panda_pick.gif"
    r = render_pick_gif(out, log=lambda s: print(s, flush=True))
    print(r)
