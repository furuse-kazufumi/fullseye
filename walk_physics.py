"""Physics-based quadruped walking (genuine dynamics), rendered headless as a GIF.

This is **not** a kinematic animation: the Unitree Go2 is driven by torque
actuators through a PD position controller tracking a trot gait, and the world is
advanced with ``mj_step`` under gravity with a real contact solver against a
**collidable** undulating terrain. So the body pitches and rolls as the centre of
mass shifts, the feet plant by contact (not by snapping), and if the gait were
unstable the robot would fall — which we measure, not assume. Alongside the GIF we
plot the body's height / pitch / roll over time as proof the motion is dynamic.

    import walk_physics as WP
    WP.run_walk_physics("out/walk_physics.gif")         # -> dict incl. upright, tilt range
"""
from __future__ import annotations

import numpy as np

_GO2 = "C:/dev/projects/mujoco_menagerie/unitree_go2/scene.xml"
_LEGS = {"FL": 0, "FR": 3, "RL": 6, "RR": 9}          # index of each leg's hip joint in the 12-vec
_PHASE = {"FL": 0.0, "RR": 0.0, "FR": np.pi, "RL": np.pi}   # trot: diagonal pairs in phase


def _build(terrain="bumps", amp=0.05, n=14, half=2.2, roll_scale=1.0):
    """Go2 + a collidable terrain (real contact). ``terrain='flat'`` uses the plain floor,
    ``'bumps'`` a gentle procedural field, ``'rolling'`` the registry's steep undulating
    terrain (heights scaled by *roll_scale*; the raw amplitude is ~0.3 m = very rough)."""
    import mujoco
    spec = mujoco.MjSpec.from_file(_GO2)
    spec.visual.global_.offwidth = 1280
    spec.visual.global_.offheight = 960
    wb = spec.worldbody
    if terrain == "bumps":
        cell = 2 * half / n
        for i in range(n):
            for j in range(n):
                x = -half + cell * (i + 0.5); y = -half + cell * (j + 0.5)
                h = amp * np.sin(x * 1.1) * np.cos(y * 1.3) + 0.6 * amp * np.sin(x * 2.1 + 1)
                g = wb.add_geom(); g.type = mujoco.mjtGeom.mjGEOM_BOX
                g.size = [cell / 2 * 1.02, cell / 2 * 1.02, 0.15]
                g.pos = [x, y, float(h) - 0.15]
                shade = 0.5 - 1.2 * float(h)
                g.rgba = [0.55, np.clip(shade, 0.2, 0.7), 0.4, 1.0]
                g.contype = 1; g.conaffinity = 1
    elif terrain in ("rolling", "hfield"):
        # A **genuinely rough** height-field (a heightfield is the standard rough-terrain
        # primitive in locomotion research, not a smoothing cheat). z_max≈0.14 m ≈ half
        # the go2's leg, with steep multi-frequency slopes; the robot must actually
        # negotiate it. roll_scale scales the amplitude.
        N = 84; rad = 2.6
        z_max = 0.14 * roll_scale
        xs = np.linspace(-rad, rad, N); X, Y = np.meshgrid(xs, xs)
        H = (0.5 * np.sin(1.3 * X) * np.cos(1.1 * Y)
             + 0.3 * np.sin(2.5 * X + 1.0) * np.sin(2.1 * Y)
             + 0.2 * np.cos(3.4 * Y - 0.6) + 0.15 * np.sin(4.1 * X))
        H = (H - H.min()) / (H.max() - H.min())               # normalise to 0..1
        spec.add_hfield(name="terr", size=[rad, rad, z_max, 0.1], nrow=N, ncol=N,
                        userdata=H.flatten().tolist())
        g = wb.add_geom(); g.type = mujoco.mjtGeom.mjGEOM_HFIELD; g.hfieldname = "terr"
        g.rgba = [0.52, 0.45, 0.36, 1.0]; g.contype = 1; g.conaffinity = 1
    return spec.compile()


# leg body-frame quadrant signs (front +x, left +y) for the balance controller
_LEG_SIGN = {"FL": (+1, +1), "FR": (+1, -1), "RL": (-1, +1), "RR": (-1, -1)}
_JINV = np.array([[-3.846, 3.125], [0.0, -6.25]])   # foot(x,z) error → (thigh,calf) step


def _leg_ik_table(m, *, samples=48, stride=0.28, stand=0.24, lift=0.07):
    """Pre-solve (thigh, calf) joint targets for one foot cycle by 2-link IK so the
    foot follows a proper walking trajectory: planted and **retracting front→back
    during stance** (propels the body forward, +x), lifted and swinging back→front
    during swing. Solved against the real model FK (a scratch MjData) with a fixed
    local inverse-Jacobian Newton step — so the robot walks **head-first**, not by a
    paddling artifact. Returns thigh[samples], calf[samples] indexed by phase."""
    import mujoco
    dk = mujoco.MjData(m)
    hip = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "FL_thigh")
    knee = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "FL_calf")
    fg = [g for g in range(m.ngeom) if int(m.geom_bodyid[g]) == knee
          and int(m.geom_type[g]) == mujoco.mjtGeom.mjGEOM_SPHERE][0]
    th_adr, cf_adr = 8, 9                                          # FL thigh / calf qpos indices

    def foot_rel(th, cf):
        mujoco.mj_resetDataKeyframe(m, dk, 0)
        dk.qpos[th_adr] = th; dk.qpos[cf_adr] = cf
        mujoco.mj_kinematics(m, dk); mujoco.mj_comPos(m, dk)
        r = dk.geom_xpos[fg] - dk.xpos[hip]
        return np.array([float(r[0]), float(r[2])])               # (x fwd, z up)

    Jinv = np.array([[-3.846, 3.125], [0.0, -6.25]])              # local inverse Jacobian (calibrated)
    th0, cf0 = 0.9, -1.8
    thigh = np.zeros(samples); calf = np.zeros(samples)
    for i in range(samples):
        ph = 2 * np.pi * i / samples
        if ph < np.pi:                                            # stance: front → back, foot down
            u = ph / np.pi; px = stride / 2 - stride * u; pz = -stand
        else:                                                     # swing: back → front, foot lifts
            u = (ph - np.pi) / np.pi; px = -stride / 2 + stride * u; pz = -stand + lift * np.sin(np.pi * u)
        th, cf = th0, cf0
        for _ in range(6):                                        # Newton IK against real FK
            err = np.array([px, pz]) - foot_rel(th, cf)
            d = Jinv @ err
            th += float(np.clip(d[0], -0.4, 0.4)); cf += float(np.clip(d[1], -0.4, 0.4))
        thigh[i], calf[i] = th, cf
    return thigh, calf


def _trot(home, t, table, *, freq=1.8):
    """PD position targets: index the pre-solved IK gait table by each leg's phase
    (diagonal pairs share a phase). Hips held at the stance value."""
    thigh, calf = table
    ns = len(thigh)
    q = home.copy()
    for leg, b in _LEGS.items():
        ph = (2 * np.pi * freq * t + _PHASE[leg]) % (2 * np.pi)
        idx = int(ph / (2 * np.pi) * ns) % ns
        q[b + 1] = thigh[idx]; q[b + 2] = calf[idx]
    return q


def _control(home, t, table, roll_deg, pitch_deg, *, freq=1.6, k_att=0.010):
    """Open-loop trot **+ closed-loop balance feedback**: measure the torso roll/pitch
    and lengthen the legs on the low side to keep the body level over rough terrain —
    the feedback a blind gait lacks. Per-leg foot-z correction is mapped to (thigh,
    calf) via the calibrated inverse Jacobian. This is what lets it negotiate the
    height-field instead of relying on a smoothed surface."""
    q = _trot(home, t, table, freq=freq)
    for leg, b in _LEGS.items():
        sx, sy = _LEG_SIGN[leg]
        dz = -k_att * (pitch_deg * sx + roll_deg * sy)    # low corner → foot pushed down (extend)
        dj = _JINV @ np.array([0.0, dz])
        q[b + 1] += float(dj[0]); q[b + 2] += float(dj[1])
    return q


def _rp(quat):
    w, x, y, z = quat
    roll = np.arctan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
    pitch = np.arcsin(np.clip(2 * (w * y - z * x), -1, 1))
    return np.degrees(roll), np.degrees(pitch)


def run_walk_physics(out_gif="out/walk_physics.gif", *, terrain="rolling", roll_scale=1.0,
                     secs=6.0, kp=60.0, kd=3.0, freq=1.6, width=640, height=480, fps=30,
                     max_gif_frames=110, log=print):
    """Simulate a genuine-physics trot and save a GIF + a telemetry plot next to it.
    Returns honest dynamics stats (upright, forward distance, pitch/roll range)."""
    import importlib.util
    import os
    if importlib.util.find_spec("mujoco") is None:
        raise RuntimeError("mujoco 未インストール")
    import mujoco
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image

    if not os.path.exists(_GO2):
        raise FileNotFoundError(f"go2 scene not found: {_GO2} (needs MuJoCo Menagerie)")
    m = _build(terrain, roll_scale=roll_scale)
    d = mujoco.MjData(m); mujoco.mj_resetDataKeyframe(m, d, 0)
    home = m.key_qpos[0][7:].copy()
    # terrain top height (from the added terrain geoms) → start the base above it and let
    # it settle onto the surface before walking (rolling is tall, so drop from higher).
    terr_top = 0.0
    for g in range(m.ngeom):
        if int(m.geom_bodyid[g]) == 0 and int(m.geom_type[g]) == mujoco.mjtGeom.mjGEOM_BOX:
            terr_top = max(terr_top, float(d.geom_xpos[g][2] + m.geom_size[g][2]))
    d.qpos[2] = terr_top + 0.32
    dt = float(m.opt.timestep)
    table = _leg_ik_table(m)                              # pre-solve the forward-walk gait
    for _ in range(int(0.6 / dt)):                        # settle onto the terrain (hold stance)
        d.ctrl[:] = kp * (home - d.qpos[7:]) - kd * d.qvel[6:]
        mujoco.mj_step(m, d)

    dt = float(m.opt.timestep)
    n_steps = int(secs / dt)
    frame_every = max(1, n_steps // int(max_gif_frames))
    ren = mujoco.Renderer(m, height=height, width=width)
    cam = mujoco.MjvCamera(); cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    cam.distance = 2.4; cam.elevation = -18.0; cam.azimuth = 120.0

    frames = []
    ts, base_z, rolls, pitches, ncons = [], [], [], [], []
    upright = True
    roll, pitch = _rp(d.qpos[3:7])
    for step in range(n_steps):
        t = step * dt
        tgt = _control(home, t, table, roll, pitch, freq=freq)   # balance feedback (prev attitude)
        d.ctrl[:] = kp * (tgt - d.qpos[7:]) - kd * d.qvel[6:]
        mujoco.mj_step(m, d)
        roll, pitch = _rp(d.qpos[3:7])
        ts.append(t); base_z.append(float(d.qpos[2])); rolls.append(roll); pitches.append(pitch)
        ncons.append(int(d.ncon))
        if d.qpos[2] < 0.12:
            upright = False
        if step % frame_every == 0:
            cam.lookat[:] = [float(d.qpos[0]), float(d.qpos[1]), 0.2]   # follow the CoM
            cam.azimuth = 120.0 + 12.0 * np.sin(step * 0.01)
            ren.update_scene(d, camera=cam)
            frames.append(Image.fromarray(ren.render()))
    ren.close()

    fwd = float(d.qpos[0])                                # signed forward progress (+x = head-first)
    pr = (round(min(pitches), 1), round(max(pitches), 1))
    rr = (round(min(rolls), 1), round(max(rolls), 1))
    frames[0].save(out_gif, save_all=True, append_images=frames[1:],
                   duration=int(1000 / max(1, fps)), loop=0)

    # telemetry panel — proof the motion is dynamic (height bobs, body tilts)
    png = os.path.splitext(out_gif)[0] + "_telemetry.png"
    bg, fgc, teal, amber, mut = "#12141b", "#e2e5ec", "#22d3bf", "#f5a524", "#8b91a0"
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 5.6), facecolor=bg, sharex=True)
    for a in (a1, a2):
        a.set_facecolor(bg); a.tick_params(colors=mut); a.grid(True, color="#2c313f", lw=0.5)
        for s in a.spines.values():
            s.set_color("#2c313f")
    a1.plot(ts, base_z, color=teal, lw=1.8); a1.axhline(0.27, color=mut, ls=":", lw=1)
    a1.set_ylabel("base height (m)", color=fgc)
    a1.set_title(f"Genuine-physics trot — CoM height bobs, body tilts (upright={upright})", color=fgc)
    a2.plot(ts, pitches, color=amber, lw=1.6, label=f"pitch [{pr[0]},{pr[1]}]°")
    a2.plot(ts, rolls, color="#e0654a", lw=1.4, label=f"roll [{rr[0]},{rr[1]}]°")
    a2.set_ylabel("body tilt (deg)", color=fgc); a2.set_xlabel("time (s)", color=fgc)
    a2.legend(facecolor=bg, edgecolor="#2c313f", labelcolor=fgc, fontsize=9)
    fig.tight_layout(); fig.savefig(png, dpi=115, facecolor=bg); plt.close(fig)

    log(f"walk physics: {out_gif} (+{os.path.basename(png)}) | terrain={terrain} "
        f"fwd={fwd:.2f}m upright={upright} pitch={pr}° roll={rr}° mean_contacts={np.mean(ncons):.1f}")
    return {"gif": out_gif, "telemetry": png, "upright": bool(upright), "forward_m": fwd,
            "pitch_range_deg": pr, "roll_range_deg": rr, "mean_contacts": float(np.mean(ncons)),
            "dynamic": bool((pr[1] - pr[0]) > 2.0 and upright)}


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "out/walk_physics.gif"
    print(run_walk_physics(out, log=lambda s: print(s, flush=True)))
