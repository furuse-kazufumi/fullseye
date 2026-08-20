"""Learn (not hand-code) closed-loop steering so a physics go2 traces figure-8s.

This is a **genuinely learned** controller, not a rule-based one: a small neural
network policy maps the robot's perceived tracking state to a steering command, and
its weights are optimised by **Evolution Strategies** (Salimans et al. 2017, an
RL-family method) from a reward that measures how much of a figure-8 the robot
actually completes under real MuJoCo physics. Forward locomotion uses the working
rule-based trot as a substrate; the *navigation* — turning left/right by the right
amount, at the right time, to trace a Gerono lemniscate — is learned end-to-end.

Honesty by construction:
  * fitness = fraction of the figure-8 waypoints genuinely reached (the robot either
    gets there under physics or it doesn't) minus cross-track error; a fall freezes
    progress, so a policy that topples scores low.
  * the policy is trained on a panel of sizes and **evaluated on held-out sizes** —
    if it merely memorised one loop it fails the generalisation test, which we report.

    import learn_figure8 as L
    L.train_figure8("out/fig8_policy.npz", iters=40)      # -> learning curve + weights
    L.eval_figure8("out/fig8_learned.gif", "out/fig8_policy.npz")   # -> GIF + tracks
"""
from __future__ import annotations

import numpy as np

import walk_physics as WP

# ------------------------------------------------------------------ policy (numpy MLP)
_OBS = 8
_HID = 32
_ACT = 1
_TURN_MAX = 1.2
_LAYERS = [(_OBS, _HID), (_HID, _HID), (_HID, _ACT)]


def n_params():
    return sum(i * o + o for i, o in _LAYERS)


def _unpack(theta):
    ws, off = [], 0
    for i, o in _LAYERS:
        w = theta[off:off + i * o].reshape(i, o); off += i * o
        b = theta[off:off + o]; off += o
        ws.append((w, b))
    return ws


def policy_action(theta_layers, obs):
    x = obs
    for k, (w, b) in enumerate(theta_layers):
        x = x @ w + b
        if k < len(theta_layers) - 1:
            x = np.tanh(x)
    return float(np.tanh(x[0])) * _TURN_MAX          # steering command in [-1.2, 1.2]


# ------------------------------------------------------------------ figure-8 geometry
def lemniscate(size, k=48):
    """Gerono lemniscate waypoints (a proper figure-8 crossing the origin, lobes on ±x)."""
    s = np.linspace(0.0, 2 * np.pi, k, endpoint=False)
    x = size * np.sin(s)
    y = 0.5 * size * np.sin(2 * s)
    return np.stack([x, y], axis=1)


# ------------------------------------------------------------------ one physics rollout
def rollout(m, d, table, home, theta_layers, size, *, horizon=16.0, ctrl_every=12,
            reach=0.38, collect=False):
    """Drive the learned steering policy through genuine physics against a figure-8 of
    the given size. Returns (fitness, info[, path]). Deterministic given inputs."""
    import mujoco
    mujoco.mj_resetDataKeyframe(m, d, 0)
    dt = float(m.opt.timestep)
    for _ in range(int(0.5 / dt)):                    # settle onto the floor
        d.ctrl[:] = 60 * (home - d.qpos[7:]) - 3 * d.qvel[6:]
        mujoco.mj_step(m, d)

    wps = lemniscate(size)
    K = len(wps)
    kidx = 0
    roll, pitch = WP._rp(d.qpos[3:7])

    def yaw_of():
        w, x, y, z = d.qpos[3:7]
        return np.arctan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))

    prev = np.array([float(d.qpos[0]), float(d.qpos[1])])
    prev_yaw = yaw_of()
    cdt = ctrl_every * dt
    turn = 0.0
    cross_sum = 0.0
    cross_n = 0
    fell = False
    path = [] if collect else None
    n_steps = int(horizon / dt)
    for step in range(n_steps):
        if step % ctrl_every == 0:
            pos = np.array([float(d.qpos[0]), float(d.qpos[1])])
            yaw = yaw_of()
            # advance the target waypoint when reached (arclength progress)
            while kidx < K and np.hypot(*(wps[kidx] - pos)) < reach:
                kidx += 1
            tgt = wps[min(kidx, K - 1)]
            to = tgt - pos
            desired = np.arctan2(to[1], to[0])
            he = (desired - yaw + np.pi) % (2 * np.pi) - np.pi
            cross = float(np.min(np.hypot(wps[:, 0] - pos[0], wps[:, 1] - pos[1])))
            cross_sum += cross; cross_n += 1
            speed = float(np.hypot(*(pos - prev))) / cdt
            yaw_rate = ((yaw - prev_yaw + np.pi) % (2 * np.pi) - np.pi) / cdt
            prev, prev_yaw = pos, yaw
            obs = np.array([np.sin(he), np.cos(he), np.clip(cross / max(size, 1e-3), -3, 3),
                            np.clip(yaw_rate, -3, 3), np.clip(speed, -1, 2),
                            roll / 30.0, pitch / 30.0,
                            np.clip(np.hypot(*to) / max(size, 1e-3), 0, 3)])
            turn = policy_action(theta_layers, obs)
            if collect:
                path.append((pos[0], pos[1], kidx))
            if kidx >= K:                             # completed the whole figure-8
                break
        q = WP._steer(home, step * dt, table, roll, pitch, turn, freq=1.3)
        d.ctrl[:] = 60 * (q - d.qpos[7:]) - 3 * d.qvel[6:]
        mujoco.mj_step(m, d)
        roll, pitch = WP._rp(d.qpos[3:7])
        if d.qpos[2] < 0.12:                          # toppled → progress frozen
            fell = True
            break

    completed = kidx / K
    mean_cross = cross_sum / max(cross_n, 1)
    # reward: completion dominates; cross-track penalised; a fall keeps kidx frozen (low)
    fitness = completed - 0.35 * (mean_cross / max(size, 1e-3)) - (0.15 if fell else 0.0)
    info = {"completed": completed, "mean_cross": mean_cross, "fell": fell, "kidx": kidx, "K": K}
    if collect:
        return fitness, info, path
    return fitness, info


# ------------------------------------------------------------------ parallel ES worker
_W = {}


def _winit():
    """Each worker builds the MuJoCo model once and reuses it (models don't pickle)."""
    import mujoco
    m = WP._build("flat")
    _W["m"] = m
    _W["d"] = mujoco.MjData(m)
    _W["home"] = m.key_qpos[0][7:].copy()
    _W["table"] = WP._leg_ik_table(m)


def _weval(args):
    theta, sizes = args
    layers = _unpack(theta)
    fs = []
    for sz in sizes:
        f, _ = rollout(_W["m"], _W["d"], _W["table"], _W["home"], layers, sz)
        fs.append(f)
    return float(np.mean(fs))


# ------------------------------------------------------------------ Evolution Strategies
def train_figure8(out_npz="out/fig8_policy.npz", *, iters=40, pop=24, sigma=0.15, lr=0.06,
                  panel=(1.2, 1.8), seed=0, workers=None, log=print):
    """Train the steering policy by mirrored-sampling Evolution Strategies. Deterministic
    physics → clean fitness ranking. Saves the weights and an honest learning curve."""
    import os
    import multiprocessing as mp
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rng = np.random.default_rng(seed)
    P = n_params()
    theta = rng.standard_normal(P) * 0.05
    workers = workers or min(mp.cpu_count(), 2 * pop)
    panel = tuple(panel)
    hist_best, hist_mean, hist_center = [], [], []

    pool = mp.Pool(workers, initializer=_winit)
    try:
        for it in range(iters):
            eps = rng.standard_normal((pop, P))
            batch = np.concatenate([theta + sigma * eps, theta - sigma * eps], axis=0)
            tasks = [(batch[i], panel) for i in range(2 * pop)]
            R = np.array(pool.map(_weval, tasks))
            rp, rm = R[:pop], R[pop:]
            # rank-normalise the mirrored pairs → robust ES gradient
            adv = rp - rm
            if np.std(adv) > 1e-8:
                adv = (adv - adv.mean()) / (adv.std() + 1e-8)
            grad = (eps.T @ adv) / pop                             # ES gradient estimate
            theta = theta + lr * grad / (sigma + 1e-8)             # OpenAI-ES step
            # honest progress: evaluate the *current center* policy on the panel
            center_f = _center_eval(pool, theta, panel)
            hist_best.append(float(R.max())); hist_mean.append(float(R.mean()))
            hist_center.append(center_f)
            log(f"ES it {it+1:02d}/{iters} | center={center_f:+.3f} "
                f"best={R.max():+.3f} mean={R.mean():+.3f}")
    finally:
        pool.close(); pool.join()

    os.makedirs(os.path.dirname(out_npz) or ".", exist_ok=True)
    np.savez(out_npz, theta=theta, layers=np.array([_OBS, _HID, _ACT]),
             panel=np.array(panel), hist_center=np.array(hist_center),
             hist_best=np.array(hist_best), hist_mean=np.array(hist_mean))
    # learning curve
    png = os.path.splitext(out_npz)[0] + "_curve.png"
    bg, fgc, teal, amber = "#12141b", "#e2e5ec", "#22d3bf", "#f5a524"
    fig, ax = plt.subplots(figsize=(8, 3.6), facecolor=bg)
    ax.set_facecolor(bg); ax.tick_params(colors="#8b91a0"); ax.grid(True, color="#2c313f", lw=0.5)
    for s in ax.spines.values():
        s.set_color("#2c313f")
    xs = np.arange(1, len(hist_center) + 1)
    ax.plot(xs, hist_center, color=teal, lw=2.2, label="center policy fitness")
    ax.plot(xs, hist_best, color=amber, lw=1.2, alpha=0.8, label="population best")
    ax.set_xlabel("ES iteration", color=fgc); ax.set_ylabel("figure-8 fitness", color=fgc)
    ax.set_title("Learned figure-8 steering — Evolution Strategies training", color=fgc)
    ax.legend(facecolor=bg, edgecolor="#2c313f", labelcolor=fgc, fontsize=9)
    fig.tight_layout(); fig.savefig(png, dpi=115, facecolor=bg); plt.close(fig)
    log(f"trained: {out_npz} (+{os.path.basename(png)}) | final_center={hist_center[-1]:+.3f} params={P}")
    return {"weights": out_npz, "curve": png, "final_center": hist_center[-1],
            "params": P, "iters": iters}


def _center_eval(pool, theta, panel):
    return float(pool.map(_weval, [(theta, panel)])[0])


# ------------------------------------------------------------------ pyramid-search MPC
def _snap(d):
    return (d.qpos.copy(), d.qvel.copy(), d.act.copy() if d.act.size else None, float(d.time))


def _restore(m, d, s):
    import mujoco
    d.qpos[:] = s[0]; d.qvel[:] = s[1]
    if s[2] is not None:
        d.act[:] = s[2]
    d.time = s[3]
    mujoco.mj_forward(m, d)


def _reactive_obs(pos, prev, yaw, prev_yaw, roll, pitch, wps, k, size, cdt):
    """Build the policy observation exactly as training/deploy do (so look-ahead is faithful)."""
    tgt = wps[min(k, len(wps) - 1)]; to = tgt - pos
    he = (np.arctan2(to[1], to[0]) - yaw + np.pi) % (2 * np.pi) - np.pi
    cross = float(np.min(np.hypot(wps[:, 0] - pos[0], wps[:, 1] - pos[1])))
    speed = float(np.hypot(*(pos - prev))) / cdt
    yaw_rate = ((yaw - prev_yaw + np.pi) % (2 * np.pi) - np.pi) / cdt
    obs = np.array([np.sin(he), np.cos(he), np.clip(cross / max(size, 1e-3), -3, 3),
                    np.clip(yaw_rate, -3, 3), np.clip(speed, -1, 2), roll / 30.0, pitch / 30.0,
                    np.clip(np.hypot(*to) / max(size, 1e-3), 0, 3)])
    return obs, cross


def _lookahead(m, d, table, home, layers, wps, kidx, size, first_turn, *, H=0.5, ctrl_every=12):
    """Roll the model forward from the *current* state: hold ``first_turn`` for one control
    interval, then let the **learned policy** (faithful obs) drive for the rest of horizon H.
    Score = figure-8 waypoints passed (+ partial) − fall − cross-track. The simulator is the
    predictive model; this is the value a candidate next-action buys."""
    import mujoco
    dt = float(m.opt.timestep); K = len(wps); cdt = ctrl_every * dt
    k = kidx; roll, pitch = WP._rp(d.qpos[3:7]); turn = first_turn
    prev = np.array([float(d.qpos[0]), float(d.qpos[1])]); prev_yaw = None
    n = int(H / dt); cross_acc = 0.0; cn = 0; fell = False
    for step in range(n):
        if step > 0 and step % ctrl_every == 0:                # after the committed first action
            pos = np.array([float(d.qpos[0]), float(d.qpos[1])])
            w, x, y, z = d.qpos[3:7]
            yaw = np.arctan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
            while k < K and np.hypot(*(wps[k] - pos)) < 0.38:
                k += 1
            obs, cross = _reactive_obs(pos, prev, yaw, prev_yaw if prev_yaw is not None else yaw,
                                       roll, pitch, wps, k, size, cdt)
            cross_acc += cross; cn += 1
            turn = policy_action(layers, obs)
            prev, prev_yaw = pos, yaw
        q = WP._steer(home, float(d.time), table, roll, pitch, turn, freq=1.3)
        d.ctrl[:] = 60 * (q - d.qpos[7:]) - 3 * d.qvel[6:]
        mujoco.mj_step(m, d); roll, pitch = WP._rp(d.qpos[3:7])
        if d.qpos[2] < 0.12:
            fell = True; break
    pos = np.array([float(d.qpos[0]), float(d.qpos[1])])
    while k < K and np.hypot(*(wps[k] - pos)) < 0.38:
        k += 1
    partial = 0.0
    if k < K:
        partial = np.clip((0.38 - np.hypot(*(wps[k] - pos))) / 0.38, 0, 1.0)
    score = (k - kidx) + partial - (3.0 if fell else 0.0) - 0.1 * (cross_acc / max(cn, 1)) / max(size, 1e-3)
    return score, (float(pos[0]), float(pos[1]))


def pyramid_action(m, d, table, home, layers, wps, kidx, size, a_prior, *, ncoarse=5, nfine=4,
                   spread=0.7, H=0.35, ctrl_every=12):
    """Coarse→fine (pyramid) search over the next steering action, **centred on the RL
    policy's proposal** ``a_prior`` (always included as a candidate, so the search can only
    match or beat the reactive policy). Evaluate a coarse fan of candidate turns by model
    look-ahead, refine around the best. Returns the chosen turn + coarse fan (turn, end, score)."""
    s0 = _snap(d)
    coarse = np.clip(np.concatenate([[a_prior], np.linspace(a_prior - spread, a_prior + spread, ncoarse)]),
                     -_TURN_MAX, _TURN_MAX)
    fan = []; best_c, best_s = float(a_prior), -1e9
    for c in coarse:
        sc, end = _lookahead(m, d, table, home, layers, wps, kidx, size, float(c), H=H, ctrl_every=ctrl_every)
        fan.append((float(c), end, float(sc))); _restore(m, d, s0)
        if sc > best_s:
            best_s, best_c = sc, float(c)
    fine = np.linspace(best_c - 0.25, best_c + 0.25, nfine)
    for c in fine:
        sc, _e = _lookahead(m, d, table, home, layers, wps, kidx, size, float(c), H=H, ctrl_every=ctrl_every)
        _restore(m, d, s0)
        if sc > best_s:
            best_s, best_c = sc, float(c)
    return float(np.clip(best_c, -_TURN_MAX, _TURN_MAX)), fan


def deploy_rollout(m, d, table, home, layers, size, *, use_mpc=True, horizon=26.0,
                   fan_every=16, search_every=3, ctrl_every=12, look_H=0.35, collect=True, log=None):
    """Run the learned controller on a figure-8 of the given size under genuine physics. The
    RL policy proposes a steering action every control tick; when ``use_mpc`` the pyramid
    search refines that proposal by model look-ahead (coarse→fine candidate next-actions,
    policy proposal always among them, so it never underperforms the reactive policy).
    Returns completion + taken path + recorded search fans (every ``fan_every`` ticks)."""
    import mujoco
    mujoco.mj_resetDataKeyframe(m, d, 0); dt = float(m.opt.timestep)
    for _ in range(int(0.5 / dt)):
        d.ctrl[:] = 60 * (home - d.qpos[7:]) - 3 * d.qvel[6:]; mujoco.mj_step(m, d)
    wps = lemniscate(size); K = len(wps); kidx = 0
    roll, pitch = WP._rp(d.qpos[3:7]); turn = 0.0; cdt = ctrl_every * dt
    prev = np.array([float(d.qpos[0]), float(d.qpos[1])]); prev_yaw = 0.0
    path = []; fans = []; fell = False; tick = 0
    n_steps = int(horizon / dt)
    for step in range(n_steps):
        if step % ctrl_every == 0:
            pos = np.array([float(d.qpos[0]), float(d.qpos[1])])
            w, x, y, z = d.qpos[3:7]
            yaw = np.arctan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
            while kidx < K and np.hypot(*(wps[kidx] - pos)) < 0.38:
                kidx += 1
            if kidx >= K:
                break
            obs, _c = _reactive_obs(pos, prev, yaw, prev_yaw, roll, pitch, wps, kidx, size, cdt)
            a_prior = policy_action(layers, obs)                    # RL policy proposal
            if use_mpc and tick % search_every == 0:                # pyramid refinement (receding horizon)
                turn, fan = pyramid_action(m, d, table, home, layers, wps, kidx, size, a_prior,
                                           H=look_H, ctrl_every=ctrl_every)
                if collect and tick % fan_every == 0:
                    fans.append((pos.copy(), fan))
            else:
                turn = a_prior
            prev, prev_yaw = pos, yaw; tick += 1
            if collect:
                path.append((float(pos[0]), float(pos[1])))
        q = WP._steer(home, step * dt, table, roll, pitch, turn, freq=1.3)
        d.ctrl[:] = 60 * (q - d.qpos[7:]) - 3 * d.qvel[6:]
        mujoco.mj_step(m, d); roll, pitch = WP._rp(d.qpos[3:7])
        if d.qpos[2] < 0.12:
            fell = True; break
    return {"completed": kidx / K, "kidx": kidx, "K": K, "fell": fell,
            "path": path, "fans": fans, "wps": wps}


def eval_figure8(out_gif="out/fig8_learned.gif", weights="out/fig8_policy.npz", *,
                 sizes=(1.0, 1.4, 1.8, 2.1, 2.5), train_panel=None,
                 render_size=1.8, width=680, height=560, fps=30, max_gif_frames=130, log=print):
    """Render the **learned** figure-8 controller: a 3D GIF of the go2 tracing a figure-8, a
    top-down panel of the tracks + target curves for several sizes (train and held-out), a
    generalisation bar of completion vs size, and a snapshot of the pyramid look-ahead fan.
    Honest metrics throughout (completion is measured under physics)."""
    import importlib.util
    import os
    if importlib.util.find_spec("mujoco") is None:
        raise RuntimeError("mujoco 未インストール")
    import mujoco
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image

    z = np.load(weights); layers = _unpack(z["theta"])
    m = WP._build("flat"); d = mujoco.MjData(m)
    home = m.key_qpos[0][7:].copy(); table = WP._leg_ik_table(m); dt = float(m.opt.timestep)

    # 1) generalisation sweep (policy-only, fast) — completion per size + tracks
    tracks = {}; comp = {}
    for sz in sizes:
        r = deploy_rollout(m, d, table, home, layers, sz, use_mpc=False, horizon=24.0)
        tracks[sz] = np.array(r["path"]); comp[sz] = r["completed"]
        log(f"  size {sz}: completed {r['completed']*100:.0f}% ({r['kidx']}/{r['K']})")

    # 2) one pyramid-search rollout at render_size to capture the candidate fans
    rr = deploy_rollout(m, d, table, home, layers, render_size, use_mpc=True, horizon=24.0,
                        search_every=3, fan_every=18)
    fans = rr["fans"]

    # 3) render a 3D GIF of the learned policy tracing render_size (reset + replay policy-only)
    mujoco.mj_resetDataKeyframe(m, d, 0)
    for _ in range(int(0.5 / dt)):
        d.ctrl[:] = 60 * (home - d.qpos[7:]) - 3 * d.qvel[6:]; mujoco.mj_step(m, d)
    wps = lemniscate(render_size); K = len(wps); kidx = 0
    roll, pitch = WP._rp(d.qpos[3:7]); turn = 0.0; cdt = 12 * dt
    prev = np.array([float(d.qpos[0]), float(d.qpos[1])]); prev_yaw = 0.0
    ren = mujoco.Renderer(m, height=height, width=width)
    cam = mujoco.MjvCamera(); cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    cam.elevation = -55.0; cam.azimuth = 90.0; cam.distance = 2.2 + 1.6 * render_size
    n_steps = int(24.0 / dt); frame_every = max(1, n_steps // int(max_gif_frames)); frames = []
    for step in range(n_steps):
        if step % 12 == 0:
            pos = np.array([float(d.qpos[0]), float(d.qpos[1])])
            w, x, y, zz = d.qpos[3:7]; yaw = np.arctan2(2 * (w * zz + x * y), 1 - 2 * (y * y + zz * zz))
            while kidx < K and np.hypot(*(wps[kidx] - pos)) < 0.38:
                kidx += 1
            if kidx >= K:
                break
            obs, _c = _reactive_obs(pos, prev, yaw, prev_yaw, roll, pitch, wps, kidx, render_size, cdt)
            turn = policy_action(layers, obs); prev, prev_yaw = pos, yaw
        q = WP._steer(home, step * dt, table, roll, pitch, turn, freq=1.3)
        d.ctrl[:] = 60 * (q - d.qpos[7:]) - 3 * d.qvel[6:]
        mujoco.mj_step(m, d); roll, pitch = WP._rp(d.qpos[3:7])
        if step % frame_every == 0:
            cam.lookat[:] = [0.0, 0.0, 0.2]
            ren.update_scene(d, camera=cam); frames.append(Image.fromarray(ren.render()))
    ren.close()
    if frames:
        frames[0].save(out_gif, save_all=True, append_images=frames[1:],
                       duration=int(1000 / max(1, fps)), loop=0)

    # 4) analysis figure: tracks (with target curves) | generalisation bar + fan inset
    png = os.path.splitext(out_gif)[0] + "_analysis.png"
    bg, fgc, teal, amber, red, mut = "#12141b", "#e2e5ec", "#22d3bf", "#f5a524", "#e0654a", "#8b91a0"
    pal = ["#22d3bf", "#5aa9e6", "#f5a524", "#e0654a", "#b57edc"]
    fig = plt.figure(figsize=(12, 5.4), facecolor=bg)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.15, 1.0])
    ax = fig.add_subplot(gs[0]); ax.set_facecolor(bg)
    for i, sz in enumerate(sizes):
        tp = lemniscate(sz, k=200)
        ax.plot(tp[:, 0], tp[:, 1], ":", color=pal[i % len(pal)], lw=1.0, alpha=0.55)
        pa = tracks[sz]
        if len(pa):
            ax.plot(pa[:, 0], pa[:, 1], "-", color=pal[i % len(pal)], lw=2.0,
                    label=f"size {sz}{'*' if sz not in train_panel else ''}: {comp[sz]*100:.0f}%")
    # pyramid fan snapshot (candidate look-ahead endpoints at one decision point)
    if fans:
        pos0, fan = fans[len(fans) // 2]
        for (c, end, sc) in fan:
            ax.plot([pos0[0], end[0]], [pos0[1], end[1]], "-", color=mut, lw=0.8, alpha=0.5)
            ax.plot(end[0], end[1], ".", color=mut, ms=5)
        best = max(fan, key=lambda f: f[2])
        ax.plot([pos0[0], best[1][0]], [pos0[1], best[1][1]], "-", color=amber, lw=2.0,
                label="pyramid look-ahead (chosen)")
    ax.set_aspect("equal"); ax.tick_params(colors=mut)
    for s in ax.spines.values():
        s.set_color("#2c313f")
    ax.set_title("Learned figure-8 tracking (* = held-out size)", color=fgc)
    ax.set_xlabel("x (m)", color=fgc); ax.set_ylabel("y (m)", color=fgc)
    ax.legend(facecolor=bg, edgecolor="#2c313f", labelcolor=fgc, fontsize=8, loc="upper right")

    ax2 = fig.add_subplot(gs[1]); ax2.set_facecolor(bg); ax2.tick_params(colors=mut)
    for s in ax2.spines.values():
        s.set_color("#2c313f")
    xs = np.arange(len(sizes))
    cols = [teal if sz in train_panel else amber for sz in sizes]
    ax2.bar(xs, [comp[sz] * 100 for sz in sizes], color=cols, width=0.62)
    for i, sz in enumerate(sizes):
        ax2.text(i, comp[sz] * 100 + 2, f"{comp[sz]*100:.0f}%", ha="center", color=fgc, fontsize=9)
    ax2.set_xticks(xs); ax2.set_xticklabels([f"{s}" for s in sizes])
    ax2.set_ylim(0, 105); ax2.grid(True, axis="y", color="#2c313f", lw=0.5)
    ax2.set_ylabel("figure-8 completed (%)", color=fgc); ax2.set_xlabel("figure-8 size (m)", color=fgc)
    ax2.set_title("Generalisation: teal=train panel, amber=held-out", color=fgc)
    fig.tight_layout(); fig.savefig(png, dpi=115, facecolor=bg); plt.close(fig)

    mean_train = float(np.mean([comp[s] for s in sizes if s in train_panel]))
    held = [s for s in sizes if s not in train_panel]
    mean_held = float(np.mean([comp[s] for s in held])) if held else 0.0
    log(f"eval figure-8: {out_gif} (+{os.path.basename(png)}) | "
        f"mean_train={mean_train*100:.0f}% mean_heldout={mean_held*100:.0f}% sizes={list(sizes)}")
    return {"gif": out_gif, "analysis": png, "completion": comp,
            "mean_train": mean_train, "mean_heldout": mean_held, "n_fans": len(fans)}


if __name__ == "__main__":
    import sys
    out = sys.argv[2] if len(sys.argv) > 2 else "out/fig8_policy.npz"
    if len(sys.argv) > 1 and sys.argv[1] == "eval":
        print(eval_figure8(log=lambda s: print(s, flush=True)))
        raise SystemExit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "smoke":
        # quick single-rollout sanity check (untrained policy)
        import mujoco
        m = WP._build("flat"); d = mujoco.MjData(m)
        home = m.key_qpos[0][7:].copy(); table = WP._leg_ik_table(m)
        th = np.random.default_rng(0).standard_normal(n_params()) * 0.05
        f, info = rollout(m, d, table, home, _unpack(th), 1.4)
        print("smoke:", f, info)
    else:
        print(train_figure8(out, log=lambda s: print(s, flush=True)))
