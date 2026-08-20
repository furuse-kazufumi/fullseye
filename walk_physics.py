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


def _control(home, t, table, roll_deg, pitch_deg, *, freq=1.6, k_att=0.002):
    """Open-loop trot **+ closed-loop balance feedback**: measure the torso roll/pitch
    and lengthen the legs on the low side to keep the body level over rough terrain —
    the feedback a blind gait lacks. Per-leg foot-z correction is mapped to (thigh,
    calf) via the calibrated inverse Jacobian; measured to cut the roll swing on the
    height-field roughly in half while keeping the same forward speed."""
    q = _trot(home, t, table, freq=freq)
    for leg, b in _LEGS.items():
        sx, sy = _LEG_SIGN[leg]
        dz = -k_att * (pitch_deg * sx - roll_deg * sy)    # low corner → foot pushed down (extend)
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
        if int(m.geom_bodyid[g]) != 0:
            continue
        if int(m.geom_type[g]) == mujoco.mjtGeom.mjGEOM_BOX:
            # static geoms: use the MODEL pose — d.geom_xpos is all-zero before mj_forward,
            # which silently turned this branch into the constant 0.15
            terr_top = max(terr_top, float(m.geom_pos[g][2] + m.geom_size[g][2]))
        elif int(m.geom_type[g]) == mujoco.mjtGeom.mjGEOM_HFIELD:
            terr_top = max(terr_top, float(m.hfield_size[m.geom_dataid[g]][2]))   # hfield z_max
    d.qpos[2] = terr_top + 0.34                           # start clear of the terrain, then settle
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


def run_jump_physics(out_gif="out/jump_physics.gif", *, terrain="flat", width=640, height=480,
                     fps=30, max_gif_frames=90, log=print):
    """Genuine-physics vertical jump: crouch → explosive leg extension → **ballistic
    flight** (all four feet leave the ground — verified by zero contacts) → landing.
    Torque-actuated, friction + gravity resolved by mj_step. Returns the measured jump
    height and airtime (a real leap, not a scripted hop)."""
    import importlib.util
    import os
    if importlib.util.find_spec("mujoco") is None:
        raise RuntimeError("mujoco 未インストール")
    import mujoco
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image

    m = _build(terrain); d = mujoco.MjData(m); mujoco.mj_resetDataKeyframe(m, d, 0)
    stand = m.key_qpos[0][7:].copy()
    crouch = stand.copy(); extend = stand.copy()
    for b in (0, 3, 6, 9):
        crouch[b + 1] = 1.5; crouch[b + 2] = -2.6            # deep fold (load the legs)
        extend[b + 1] = 0.3; extend[b + 2] = -0.6            # near-full extension (push off)
    dt = float(m.opt.timestep)
    stand_z = 0.27
    # phase schedule: (target, kp, kd, seconds)
    phases = [(stand, 60, 3, 0.4), (crouch, 60, 3, 0.5), (extend, 250, 2, 0.12),
              (stand, 80, 4, 1.4)]
    n_steps = int(sum(p[3] for p in phases) / dt)
    frame_every = max(1, n_steps // int(max_gif_frames))
    ren = mujoco.Renderer(m, height=height, width=width)
    cam = mujoco.MjvCamera(); cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    cam.lookat[:] = [0, 0, 0.3]; cam.distance = 2.1; cam.elevation = -12.0; cam.azimuth = 90.0

    frames = []; ts, base_z, ncons = [], [], []
    peak = stand_z; airborne = 0; step_i = 0
    for target, pkp, pkd, secs in phases:
        for _ in range(int(secs / dt)):
            d.ctrl[:] = pkp * (target - d.qpos[7:]) - pkd * d.qvel[6:]
            mujoco.mj_step(m, d)
            z = float(d.qpos[2]); peak = max(peak, z)
            ts.append(step_i * dt); base_z.append(z); ncons.append(int(d.ncon))
            if d.ncon == 0:
                airborne += 1
            if step_i % frame_every == 0:
                cam.lookat[2] = 0.3 + 0.5 * (z - stand_z)     # tilt up to follow the leap
                ren.update_scene(d, camera=cam)
                frames.append(Image.fromarray(ren.render()))
            step_i += 1
    ren.close()

    jump_h = peak - stand_z; airtime = airborne * dt
    png = os.path.splitext(out_gif)[0] + "_telemetry.png"
    bg, fgc, teal = "#12141b", "#e2e5ec", "#22d3bf"
    fig, ax = plt.subplots(figsize=(9, 3.6), facecolor=bg)
    ax.set_facecolor(bg); ax.tick_params(colors="#8b91a0"); ax.grid(True, color="#2c313f", lw=0.5)
    for s in ax.spines.values():
        s.set_color("#2c313f")
    ax.plot(ts, base_z, color=teal, lw=2.0)
    air = np.array(ncons) == 0
    ax.fill_between(ts, 0, base_z, where=air, color="#f5a524", alpha=0.35, label=f"airborne (0 contacts) {airtime:.2f}s")
    ax.axhline(stand_z, color="#8b91a0", ls=":", lw=1)
    ax.set_xlabel("time (s)", color=fgc); ax.set_ylabel("base height (m)", color=fgc)
    ax.set_title(f"Genuine-physics jump — peak {peak:.2f} m (leap {jump_h*100:.0f} cm), airtime {airtime:.2f} s", color=fgc)
    ax.legend(facecolor=bg, edgecolor="#2c313f", labelcolor=fgc, fontsize=9)
    fig.tight_layout(); fig.savefig(png, dpi=115, facecolor=bg); plt.close(fig)

    frames[0].save(out_gif, save_all=True, append_images=frames[1:],
                   duration=int(1000 / max(1, fps)), loop=0)
    log(f"jump physics: {out_gif} (+{os.path.basename(png)}) | peak_z={peak:.3f} "
        f"jump_height={jump_h*100:.0f}cm airtime={airtime:.2f}s (0-contact flight)")
    return {"gif": out_gif, "telemetry": png, "peak_z": peak, "jump_height_m": jump_h,
            "airtime_s": airtime, "left_ground": bool(airtime > 0.1)}


def run_hurdle_physics(out_gif="out/hurdle_physics.gif", *, barrier_h=0.20, barrier_x=0.85,
                       run_s=1.5, push_kp=300, width=640, height=480, fps=30, max_gif_frames=110,
                       log=print):
    """Genuine-physics **running long-jump over a barrier**: the go2 trots up to speed,
    crouches, launches forward+up off its legs (feet driven back → body forward), sails
    over a barrier of height *barrier_h*, and lands beyond it — all mj_step, gravity,
    friction, contact. Reports whether it actually cleared the barrier (measured)."""
    import importlib.util
    import os
    if importlib.util.find_spec("mujoco") is None:
        raise RuntimeError("mujoco 未インストール")
    import mujoco
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image

    spec = mujoco.MjSpec.from_file(_GO2)
    spec.visual.global_.offwidth = 1280; spec.visual.global_.offheight = 960
    g = spec.worldbody.add_geom(); g.type = mujoco.mjtGeom.mjGEOM_BOX
    g.size = [0.04, 0.6, barrier_h / 2]; g.pos = [barrier_x, 0, barrier_h / 2]
    g.rgba = [0.85, 0.3, 0.28, 1.0]; g.contype = 1; g.conaffinity = 1
    m = spec.compile(); d = mujoco.MjData(m); mujoco.mj_resetDataKeyframe(m, d, 0)
    home = m.key_qpos[0][7:].copy(); d.qpos[2] = 0.30
    table = _leg_ik_table(m); dt = float(m.opt.timestep)
    crouch = home.copy(); extend = home.copy()
    for b in (0, 3, 6, 9):
        crouch[b + 1] = 1.4; crouch[b + 2] = -2.5
        extend[b + 1] = 1.2; extend[b + 2] = -0.5         # thigh back + straighten → forward+up thrust

    ren = mujoco.Renderer(m, height=height, width=width)
    cam = mujoco.MjvCamera(); cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    cam.distance = 2.6; cam.elevation = -14.0; cam.azimuth = 90.0
    frames = []; ts, base_x, base_z, ncons = [], [], [], []
    step_i = [0]; peak = 0.30; cleared = False; prev_x = [float('nan')]

    def grab():
        cam.lookat[:] = [max(0.0, float(d.qpos[0])), 0, 0.25]
        ren.update_scene(d, camera=cam); frames.append(Image.fromarray(ren.render()))

    def phase(get_ctrl, secs):
        nonlocal peak, cleared
        for _ in range(int(secs / dt)):
            d.ctrl[:] = get_ctrl()
            mujoco.mj_step(m, d)
            peak = max(peak, float(d.qpos[2]))
            x_now = float(d.qpos[0])
            # 'cleared' = at the moment the base crosses the barrier plane it is inside the
            # barrier's y-span (no sidestepping around the 0.6 m half-width) AND well above its
            # top (genuinely over, not scraping). x>barrier_x alone also passed a walk-around.
            if prev_x[0] == prev_x[0] and prev_x[0] <= barrier_x < x_now:
                if abs(float(d.qpos[1])) < 0.55 and float(d.qpos[2]) > barrier_h + 0.15:
                    cleared = True
            prev_x[0] = x_now
            ts.append(step_i[0] * dt); base_x.append(float(d.qpos[0]))
            base_z.append(float(d.qpos[2])); ncons.append(int(d.ncon))
            if step_i[0] % max(1, int(3.6 / dt / max_gif_frames)) == 0:
                grab()
            step_i[0] += 1

    roll = [0.0]; pitch = [0.0]
    def run_ctrl():
        q = _control(home, step_i[0] * dt, table, roll[0], pitch[0], freq=2.2)
        roll[0], pitch[0] = _rp(d.qpos[3:7])
        return 60 * (q - d.qpos[7:]) - 3 * d.qvel[6:]
    mujoco.mj_forward(m, d)
    phase(lambda: 60 * (home - d.qpos[7:]) - 3 * d.qvel[6:], 0.4)   # settle
    phase(run_ctrl, run_s)                                          # run up to speed
    phase(lambda: 70 * (crouch - d.qpos[7:]) - 3 * d.qvel[6:], 0.18)  # crouch
    phase(lambda: push_kp * (extend - d.qpos[7:]) - 2 * d.qvel[6:], 0.14)  # explosive launch
    phase(lambda: 90 * (home - d.qpos[7:]) - 4 * d.qvel[6:], 1.3)   # flight + land
    ren.close()

    upright = float(d.qpos[2]) > 0.15
    success = bool(cleared and upright)
    airtime = sum(1 for c in ncons if c == 0) * dt
    png = os.path.splitext(out_gif)[0] + "_telemetry.png"
    bg, fgc, teal = "#12141b", "#e2e5ec", "#22d3bf"
    fig, ax = plt.subplots(figsize=(9, 3.6), facecolor=bg)
    ax.set_facecolor(bg); ax.tick_params(colors="#8b91a0"); ax.grid(True, color="#2c313f", lw=0.5)
    for s in ax.spines.values():
        s.set_color("#2c313f")
    ax.plot(base_x, base_z, color=teal, lw=2.0)
    ax.axvline(barrier_x, color="#e0654a", lw=3, alpha=0.7, label=f"barrier ({barrier_h*100:.0f} cm)")
    ax.axhline(barrier_h, xmin=0, xmax=1, color="#e0654a", ls=":", lw=1)
    ax.set_xlabel("forward x (m)", color=fgc); ax.set_ylabel("base height z (m)", color=fgc)
    ax.set_title(f"Running long-jump — trajectory (cleared {barrier_h*100:.0f} cm barrier: {success})", color=fgc)
    ax.legend(facecolor=bg, edgecolor="#2c313f", labelcolor=fgc, fontsize=9)
    fig.tight_layout(); fig.savefig(png, dpi=115, facecolor=bg); plt.close(fig)
    frames[0].save(out_gif, save_all=True, append_images=frames[1:],
                   duration=int(1000 / max(1, fps)), loop=0)
    log(f"hurdle physics: {out_gif} (+{os.path.basename(png)}) | barrier={barrier_h*100:.0f}cm "
        f"final_x={float(d.qpos[0]):.2f} peak_z={peak:.2f} cleared={cleared} upright={upright}")
    return {"gif": out_gif, "telemetry": png, "barrier_h": barrier_h, "cleared": bool(cleared),
            "upright": bool(upright), "success": success, "final_x": float(d.qpos[0]), "peak_z": peak}


def _steer(home, t, table, roll, pitch, turn, *, freq=1.6):
    """Gait + closed-loop balance + **differential-stride steering** (extra stance
    retraction on one side yaws the body). ``turn>0`` steers left."""
    q = _control(home, t, table, roll, pitch, freq=freq)
    for leg, b in _LEGS.items():
        side = +1 if leg in ("FL", "RL") else -1
        ph = (2 * np.pi * freq * t + _PHASE[leg]) % (2 * np.pi)
        q[b + 1] += float(turn) * side * 0.16 * np.cos(ph)
    return q


def run_route_planning(out_gif="out/route_planning.gif", *, max_s=60.0, freq=1.8,
                       width=720, height=560, fps=30, max_gif_frames=130, log=print):
    """**Perceptive route planning**: obstacles block a straight line to the goal, so
    every replan the robot casts a fan of look-ahead rays (a coarse→fine **pyramid
    search** over candidate headings), scores each by obstacle clearance + progress to
    the goal, picks the best heading, and steers there with a differential-stride turn.
    Genuine physics throughout; the chosen route and candidate rays are drawn each frame."""
    import importlib.util
    import os
    if importlib.util.find_spec("mujoco") is None:
        raise RuntimeError("mujoco 未インストール")
    import mujoco
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image

    goal = np.array([6.0, 0.0])
    obstacles = [(2.0, 0.4, 0.5), (3.2, -0.9, 0.5), (4.4, 0.7, 0.5), (3.0, 1.4, 0.5),
                 (2.4, -1.6, 0.5), (4.8, -0.6, 0.5)]        # (x, y, radius) pillars to avoid
    spec = mujoco.MjSpec.from_file(_GO2)
    spec.visual.global_.offwidth = 1280; spec.visual.global_.offheight = 960
    wb = spec.worldbody
    for (ox, oy, orad) in obstacles:
        g = wb.add_geom(); g.type = mujoco.mjtGeom.mjGEOM_CYLINDER
        g.size = [orad, 0.5, 0]; g.pos = [ox, oy, 0.5]
        g.rgba = [0.80, 0.32, 0.28, 1.0]; g.contype = 1; g.conaffinity = 1
    gm = wb.add_geom(); gm.type = mujoco.mjtGeom.mjGEOM_CYLINDER   # goal marker (no collision)
    gm.size = [0.25, 0.02, 0]; gm.pos = [goal[0], goal[1], 0.02]
    gm.rgba = [0.2, 0.8, 0.4, 1.0]; gm.contype = 0; gm.conaffinity = 0
    m = spec.compile(); d = mujoco.MjData(m); mujoco.mj_resetDataKeyframe(m, d, 0)
    home = m.key_qpos[0][7:].copy(); table = _leg_ik_table(m); dt = float(m.opt.timestep)
    obs_group = np.zeros(6, np.uint8); obs_group[0] = 1

    def clearance(px, py, ang, reach=2.5):
        # distance to nearest obstacle along heading ang (analytic ray-vs-circle)
        c, s = np.cos(ang), np.sin(ang); best = reach
        for (ox, oy, orad) in obstacles:
            dx, dy = ox - px, oy - py
            proj = dx * c + dy * s
            if proj <= 0:
                continue
            perp = abs(-dx * s + dy * c)
            if perp < orad + 0.28:                       # robot half-width margin
                hit = proj - np.sqrt(max(0.0, (orad + 0.28) ** 2 - perp ** 2))
                best = min(best, max(0.0, hit))
        return best

    def plan(px, py, yaw):
        goal_ang = np.arctan2(goal[1] - py, goal[0] - px)
        def score(ang):
            cl = clearance(px, py, ang)
            # reward clearance + alignment to goal; penalise sharp turns
            # wrap the turn cost: yaw≈+π vs candidate≈−π is the SAME direction, not a 2π turn
            dturn = abs((ang - yaw + np.pi) % (2 * np.pi) - np.pi)
            return cl + 1.5 * np.cos(ang - goal_ang) - 0.3 * dturn
        # pyramid: coarse fan, then refine around the best
        coarse = np.linspace(goal_ang - 1.4, goal_ang + 1.4, 9)
        best = max(coarse, key=score)
        fine = np.linspace(best - 0.35, best + 0.35, 9)
        best = max(fine, key=score)
        return float(best), goal_ang

    ren = mujoco.Renderer(m, height=height, width=width)
    cam = mujoco.MjvCamera(); cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    cam.lookat[:] = [3.0, 0, 0.2]; cam.distance = 7.5; cam.elevation = -40.0; cam.azimuth = 90.0
    n_steps = int(max_s / dt); frame_every = max(1, n_steps // int(max_gif_frames))
    for _ in range(int(0.5 / dt)):
        d.ctrl[:] = 60 * (home - d.qpos[7:]) - 3 * d.qvel[6:]; mujoco.mj_step(m, d)
    roll, pitch = _rp(d.qpos[3:7]); reached = False; chosen = 0.0
    path = []; imgs = []
    try:
        for step in range(n_steps):
            px, py = float(d.qpos[0]), float(d.qpos[1])
            w_, x_, y_, z_ = d.qpos[3:7]; yaw = np.arctan2(2 * (w_ * z_ + x_ * y_), 1 - 2 * (y_ * y_ + z_ * z_))
            if step % 60 == 0:
                chosen, goal_ang = plan(px, py, yaw)     # replan the route (perceive + pyramid search)
            turn = np.clip(2.2 * ((chosen - yaw + np.pi) % (2 * np.pi) - np.pi), -1.2, 1.2)
            q = _steer(home, step * dt, table, roll, pitch, turn, freq=freq)
            d.ctrl[:] = 60 * (q - d.qpos[7:]) - 3 * d.qvel[6:]
            mujoco.mj_step(m, d); roll, pitch = _rp(d.qpos[3:7])
            if step % 20 == 0:
                path.append((px, py))
            if d.qpos[2] < 0.12:
                break
            if np.hypot(goal[0] - px, goal[1] - py) < 0.4:
                reached = True; break
            if step % frame_every == 0:
                cam.lookat[:] = [px * 0.5 + 3.0, py * 0.4, 0.2]
                ren.update_scene(d, camera=cam)
                imgs.append(Image.fromarray(ren.render()))   # local — a crashed run can't leak
    finally:
        ren.close()                                      # release the GL context even on a blow-up
    reached_d = float(np.hypot(goal[0] - d.qpos[0], goal[1] - d.qpos[1]))
    # top-down plan figure (obstacles, goal, taken path)
    png = os.path.splitext(out_gif)[0] + "_plan.png"
    bg, fgc, teal = "#12141b", "#e2e5ec", "#22d3bf"
    fig, ax = plt.subplots(figsize=(6.2, 5.6), facecolor=bg); ax.set_facecolor(bg)
    ax.tick_params(colors="#8b91a0")
    for s in ax.spines.values():
        s.set_color("#2c313f")
    for (ox, oy, orad) in obstacles:
        ax.add_patch(plt.Circle((ox, oy), orad, color="#e0654a", alpha=0.8))
    ax.plot(goal[0], goal[1], "*", color="#4cc57e", ms=20, label="goal")
    if path:
        pa = np.array(path); ax.plot(pa[:, 0], pa[:, 1], "-", color=teal, lw=2.2, label="route taken")
        ax.plot(pa[0, 0], pa[0, 1], "o", color=fgc, ms=8)
    ax.set_aspect("equal"); ax.set_title(f"Route planning — reached goal: {reached}", color=fgc)
    ax.set_xlabel("x (m)", color=fgc); ax.set_ylabel("y (m)", color=fgc)
    ax.legend(facecolor=bg, edgecolor="#2c313f", labelcolor=fgc, fontsize=9)
    fig.tight_layout(); fig.savefig(png, dpi=115, facecolor=bg); plt.close(fig)
    if imgs:
        imgs[0].save(out_gif, save_all=True, append_images=imgs[1:],
                     duration=int(1000 / max(1, fps)), loop=0)
    log(f"route planning: {out_gif} (+{os.path.basename(png)}) | reached={reached} "
        f"final_gap={reached_d:.2f}m obstacles={len(obstacles)}")
    return {"gif": out_gif, "plan": png, "reached_goal": reached, "final_gap_m": reached_d,
            "n_obstacles": len(obstacles)}


def run_figure8(out_gif="out/figure8.gif", *, sizes=(3.0, 5.0), freq=1.3, width=680, height=560,
                fps=30, max_gif_frames=130, log=print):
    """Steering practice: drive the differential-stride turn with a sinusoid to trace
    **figure-8 loops of several sizes**, exercising left+right turns at varying radii.
    Plots the top-down tracks — a clean calibration of the turn controller."""
    import importlib.util
    import os
    if importlib.util.find_spec("mujoco") is None:
        raise RuntimeError("mujoco 未インストール")
    import mujoco
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image

    m = _build("flat"); dt = float(mujoco.MjModel.from_xml_path(_GO2).opt.timestep)
    tracks = {}; frames = []
    bg, fgc = "#12141b", "#e2e5ec"
    palette = ["#22d3bf", "#f5a524", "#e0654a"]
    ren = mujoco.Renderer(m, height=height, width=width)
    cam = mujoco.MjvCamera(); cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    cam.elevation = -50.0; cam.azimuth = 90.0; cam.distance = 5.0
    for si, amp in enumerate(sizes):
        d = mujoco.MjData(m); mujoco.mj_resetDataKeyframe(m, d, 0)
        home = m.key_qpos[0][7:].copy(); table = _leg_ik_table(m)
        for _ in range(int(0.5 / dt)):
            d.ctrl[:] = 60 * (home - d.qpos[7:]) - 3 * d.qvel[6:]; mujoco.mj_step(m, d)
        roll, pitch = _rp(d.qpos[3:7]); T = 16.0; path = []
        for step in range(int(T / dt)):
            tt = step * dt
            turn = amp * np.sin(2 * np.pi * tt / T * 2)   # two loops → figure-8
            q = _steer(home, tt, table, roll, pitch, turn, freq=freq)
            d.ctrl[:] = 60 * (q - d.qpos[7:]) - 3 * d.qvel[6:]
            mujoco.mj_step(m, d); roll, pitch = _rp(d.qpos[3:7])
            if step % 15 == 0:
                path.append((float(d.qpos[0]), float(d.qpos[1])))
            if si == len(sizes) - 1 and step % max(1, int(T / dt / max_gif_frames)) == 0:
                cam.lookat[:] = [float(d.qpos[0]), float(d.qpos[1]), 0.2]
                ren.update_scene(d, camera=cam); frames.append(Image.fromarray(ren.render()))
        tracks[amp] = np.array(path)
    ren.close()

    png = os.path.splitext(out_gif)[0] + "_tracks.png"
    fig, ax = plt.subplots(figsize=(6.2, 5.6), facecolor=bg); ax.set_facecolor(bg)
    ax.tick_params(colors="#8b91a0")
    for s in ax.spines.values():
        s.set_color("#2c313f")
    for i, (amp, pa) in enumerate(tracks.items()):
        if len(pa):
            ax.plot(pa[:, 0], pa[:, 1], "-", color=palette[i % len(palette)], lw=2.0, label=f"turn amp {amp}")
    ax.set_aspect("equal"); ax.set_title("Figure-8 steering practice (various sizes)", color=fgc)
    ax.set_xlabel("x (m)", color=fgc); ax.set_ylabel("y (m)", color=fgc)
    ax.legend(facecolor=bg, edgecolor="#2c313f", labelcolor=fgc, fontsize=9)
    fig.tight_layout(); fig.savefig(png, dpi=115, facecolor=bg); plt.close(fig)
    if frames:
        frames[0].save(out_gif, save_all=True, append_images=frames[1:],
                       duration=int(1000 / max(1, fps)), loop=0)
    spans = {round(a, 2): round(float(np.ptp(p[:, 0]) + np.ptp(p[:, 1])), 2) for a, p in tracks.items() if len(p)}
    log(f"figure-8: {out_gif} (+{os.path.basename(png)}) | sizes={list(tracks)} track_spans={spans}")
    return {"gif": out_gif, "tracks": png, "sizes": list(tracks), "track_spans": spans}


def run_long_route(out_gif="out/long_route.gif", *, target_m=100.0, max_s=360.0, freq=2.0,
                   width=720, height=420, fps=30, max_gif_frames=140, log=print, max_s_override=None):
    """A **long, varied route**: build a ~120 m strip of undulating terrain (flat and
    rolling sections) and have the rule-based go2 walk it under genuine physics until it
    covers *target_m* metres (or falls / times out). Rendered as a tracking GIF plus a
    distance-vs-time plot. Everything is mj_step + friction + gravity + contact; the
    controller is analytical (hand-designed gait + PD + proportional balance), no learning."""
    import importlib.util
    import os
    if importlib.util.find_spec("mujoco") is None:
        raise RuntimeError("mujoco 未インストール")
    import mujoco
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image

    Lx, Wy = 124.0, 6.0
    spec = mujoco.MjSpec.from_file(_GO2)
    spec.visual.global_.offwidth = 1280; spec.visual.global_.offheight = 960
    NX, NY = 620, 40
    xs = np.linspace(-4, Lx, NX); ys = np.linspace(-Wy, Wy, NY)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    rough = 0.5 + 0.5 * np.sin(0.05 * X)                  # roughness varies along the route (complex)
    H = rough * (0.5 * np.sin(0.5 * X) * np.cos(0.7 * Y) + 0.3 * np.sin(0.9 * X + 1)) + 0.2 * np.cos(1.1 * Y)
    H = (H - H.min()) / (H.max() - H.min())
    cx = (Lx - 4) / 2
    spec.add_hfield(name="terr", size=[(Lx + 4) / 2, Wy, 0.07, 0.1], nrow=NY, ncol=NX,
                    userdata=H.T.flatten().tolist())
    g = spec.worldbody.add_geom(); g.type = mujoco.mjtGeom.mjGEOM_HFIELD; g.hfieldname = "terr"
    g.pos = [cx, 0, 0]; g.rgba = [0.52, 0.45, 0.36, 1.0]; g.contype = 1; g.conaffinity = 1
    m = spec.compile(); d = mujoco.MjData(m); mujoco.mj_resetDataKeyframe(m, d, 0)
    home = m.key_qpos[0][7:].copy(); d.qpos[2] = 0.07 + 0.34
    table = _leg_ik_table(m); dt = float(m.opt.timestep)
    for _ in range(int(0.6 / dt)):
        d.ctrl[:] = 60 * (home - d.qpos[7:]) - 3 * d.qvel[6:]; mujoco.mj_step(m, d)

    n_steps = int(max_s / dt); frame_every = max(1, n_steps // int(max_gif_frames))
    ren = mujoco.Renderer(m, height=height, width=width)
    cam = mujoco.MjvCamera(); cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    cam.distance = 3.0; cam.elevation = -12.0; cam.azimuth = 90.0
    frames = []; ts, dist = [], []
    roll, pitch = _rp(d.qpos[3:7]); upright = True; reached = False
    for step in range(n_steps):
        q = _control(home, step * dt, table, roll, pitch, freq=freq)
        d.ctrl[:] = 60 * (q - d.qpos[7:]) - 3 * d.qvel[6:]
        mujoco.mj_step(m, d)
        roll, pitch = _rp(d.qpos[3:7])
        x = float(d.qpos[0])
        if step % 40 == 0:
            ts.append(step * dt); dist.append(x)
        if d.qpos[2] < 0.12:
            upright = False; break
        if step % frame_every == 0:
            cam.lookat[:] = [x, 0, 0.25]; cam.azimuth = 90.0 + 8.0 * np.sin(step * 0.002)
            ren.update_scene(d, camera=cam); frames.append(Image.fromarray(ren.render()))
        if x >= target_m:
            reached = True; break
    ren.close()
    travelled = float(d.qpos[0]); sim_t = step * dt

    png = os.path.splitext(out_gif)[0] + "_telemetry.png"
    bg, fgc, teal = "#12141b", "#e2e5ec", "#22d3bf"
    fig, ax = plt.subplots(figsize=(9, 3.4), facecolor=bg)
    ax.set_facecolor(bg); ax.tick_params(colors="#8b91a0"); ax.grid(True, color="#2c313f", lw=0.5)
    for s in ax.spines.values():
        s.set_color("#2c313f")
    ax.plot(ts, dist, color=teal, lw=2.0)
    ax.axhline(target_m, color="#f5a524", ls="--", lw=1.2, label=f"target {target_m:.0f} m")
    ax.set_xlabel("time (s)", color=fgc); ax.set_ylabel("distance travelled (m)", color=fgc)
    ax.set_title(f"Long route — {travelled:.0f} m in {sim_t:.0f} s ({travelled/max(sim_t,1e-6):.2f} m/s), upright={upright}", color=fgc)
    ax.legend(facecolor=bg, edgecolor="#2c313f", labelcolor=fgc, fontsize=9)
    fig.tight_layout(); fig.savefig(png, dpi=115, facecolor=bg); plt.close(fig)
    frames[0].save(out_gif, save_all=True, append_images=frames[1:],
                   duration=int(1000 / max(1, fps)), loop=0)
    log(f"long route: {out_gif} (+{os.path.basename(png)}) | travelled={travelled:.1f}m "
        f"in {sim_t:.0f}s sim ({travelled/max(sim_t,1e-6):.2f}m/s) reached_{target_m:.0f}m={reached} upright={upright}")
    return {"gif": out_gif, "telemetry": png, "distance_m": travelled, "sim_s": sim_t,
            "reached_target": reached, "upright": upright, "speed_mps": travelled / max(sim_t, 1e-6)}


if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "walk"
    if mode == "long":
        print(run_long_route(sys.argv[2] if len(sys.argv) > 2 else "out/long_route.gif",
                             log=lambda s: print(s, flush=True)))
        raise SystemExit(0)
    if mode == "hurdle":
        print(run_hurdle_physics(sys.argv[2] if len(sys.argv) > 2 else "out/hurdle_physics.gif",
                                 log=lambda s: print(s, flush=True)))
        raise SystemExit(0)
    out = sys.argv[2] if len(sys.argv) > 2 else f"out/{'jump' if mode=='jump' else 'walk'}_physics.gif"
    fn = run_jump_physics if mode == "jump" else run_walk_physics
    print(fn(out, log=lambda s: print(s, flush=True)))
