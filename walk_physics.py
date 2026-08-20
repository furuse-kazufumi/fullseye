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
    elif terrain == "rolling":
        import re
        import scene_registry as R
        xml = R.resolve("rolling")["xml"]
        body = open(xml, encoding="utf-8").read().split("<worldbody>", 1)[1].rsplit("</worldbody>", 1)[0]
        for tag in re.findall(r"<geom[^>]*/>", body):
            def at(nm, d=None):
                mm = re.search(rf'{nm}="([^"]*)"', tag)
                return mm.group(1) if mm else d
            if (at("type") or "box") != "box":
                continue
            sz = [float(v) for v in at("size", "0.05 0.05 0.05").split()]
            po = [float(v) for v in at("pos", "0 0 0").split()]
            rg = [float(v) for v in at("rgba", "0.4 0.4 0.4 1").split()]
            g = wb.add_geom(); g.type = mujoco.mjtGeom.mjGEOM_BOX
            g.size = [sz[0], sz[1], max(0.01, sz[2] * roll_scale)]
            g.pos = [po[0], po[1], po[2] * roll_scale]        # scale height (keep footprint)
            g.rgba = rg; g.contype = 1; g.conaffinity = 1     # collidable (real contact)
    return spec.compile()


def _trot(home, t, *, freq=1.8, a_th=0.35, a_cf=0.5, lift=0.3):
    """PD position targets for a trot gait around the standing pose *home* (12-vec).

    The thigh's fore-aft swing sign is negated so the robot walks **head-first (+x**,
    where FL/FR are) rather than rump-first."""
    q = home.copy()
    for leg, b in _LEGS.items():
        ph = 2 * np.pi * freq * t + _PHASE[leg]
        s = np.sin(ph); sw = max(0.0, s)                  # swing during the positive half
        q[b + 1] = home[b + 1] - a_th * s + lift * sw     # thigh: swing (fwd) + lift on swing
        q[b + 2] = home[b + 2] - a_cf * sw                # calf: tuck on swing
    return q


def _rp(quat):
    w, x, y, z = quat
    roll = np.arctan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
    pitch = np.arcsin(np.clip(2 * (w * y - z * x), -1, 1))
    return np.degrees(roll), np.degrees(pitch)


def run_walk_physics(out_gif="out/walk_physics.gif", *, terrain="bumps", roll_scale=1.0,
                     secs=6.0, kp=40.0, kd=2.0, freq=1.8, width=640, height=480, fps=30,
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
    for step in range(n_steps):
        t = step * dt
        d.ctrl[:] = kp * (_trot(home, t, freq=freq) - d.qpos[7:]) - kd * d.qvel[6:]
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
