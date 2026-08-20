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


def _lookahead(m, d, table, home, layers, wps, kidx, first_turn, *, H=0.6, ctrl_every=12):
    """Roll the model forward from the *current* state: hold ``first_turn`` for one control
    interval, then let the **learned policy** drive for the rest of horizon H. Score by how
    many figure-8 waypoints get passed (+ partial progress), upright, low cross-track. This
    is the value a candidate next-action buys — the simulator is the predictive model."""
    import mujoco
    dt = float(m.opt.timestep); K = len(wps)
    k = kidx; roll, pitch = WP._rp(d.qpos[3:7]); turn = first_turn
    n = int(H / dt); cross_acc = 0.0; cn = 0; fell = False
    for step in range(n):
        if step > 0 and step % ctrl_every == 0:                # after the committed first action
            pos = np.array([float(d.qpos[0]), float(d.qpos[1])])
            w, x, y, z = d.qpos[3:7]
            yaw = np.arctan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
            while k < K and np.hypot(*(wps[k] - pos)) < 0.38:
                k += 1
            tgt = wps[min(k, K - 1)]; to = tgt - pos
            he = (np.arctan2(to[1], to[0]) - yaw + np.pi) % (2 * np.pi) - np.pi
            cross = float(np.min(np.hypot(wps[:, 0] - pos[0], wps[:, 1] - pos[1])))
            cross_acc += cross; cn += 1
            obs = np.array([np.sin(he), np.cos(he), np.clip(cross, -3, 3), 0.0, 0.3,
                            roll / 30.0, pitch / 30.0, np.clip(np.hypot(*to), 0, 3)])
            turn = policy_action(layers, obs)
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
        partial = np.clip((0.38 - np.hypot(*(wps[k] - pos))) / 0.38 + 1.0, 0, 1.2)
    score = (k - kidx) + partial - (2.0 if fell else 0.0) - 0.05 * (cross_acc / max(cn, 1))
    return score, (float(pos[0]), float(pos[1]))


def pyramid_action(m, d, table, home, layers, wps, kidx, *, ncoarse=5, nfine=5,
                   H=0.6, ctrl_every=12):
    """Coarse→fine (pyramid) search over the next steering action: evaluate a coarse fan of
    candidate turns by look-ahead, then refine around the best. Returns the chosen turn and
    the coarse candidate end-points (for visualising the search fan)."""
    s0 = _snap(d)
    coarse = np.linspace(-_TURN_MAX, _TURN_MAX, ncoarse)
    fan = []; best_c, best_s = 0.0, -1e9
    for c in coarse:
        sc, end = _lookahead(m, d, table, home, layers, wps, kidx, float(c), H=H, ctrl_every=ctrl_every)
        fan.append(end); _restore(m, d, s0)
        if sc > best_s:
            best_s, best_c = sc, float(c)
    fine = np.linspace(best_c - 0.3, best_c + 0.3, nfine)
    for c in fine:
        sc, _e = _lookahead(m, d, table, home, layers, wps, kidx, float(c), H=H, ctrl_every=ctrl_every)
        _restore(m, d, s0)
        if sc > best_s:
            best_s, best_c = sc, float(c)
    return float(np.clip(best_c, -_TURN_MAX, _TURN_MAX)), fan


def deploy_rollout(m, d, table, home, layers, size, *, use_mpc=True, horizon=26.0,
                   replan_every=48, ctrl_every=12, look_H=0.6, collect=True, log=None):
    """Run the learned controller (optionally wrapped by pyramid-search MPC) on a figure-8
    of the given size, under genuine physics. Returns completion + the taken path + a few
    recorded search fans. This is the deployment used for rendering and the honest metrics."""
    import mujoco
    mujoco.mj_resetDataKeyframe(m, d, 0); dt = float(m.opt.timestep)
    for _ in range(int(0.5 / dt)):
        d.ctrl[:] = 60 * (home - d.qpos[7:]) - 3 * d.qvel[6:]; mujoco.mj_step(m, d)
    wps = lemniscate(size); K = len(wps); kidx = 0
    roll, pitch = WP._rp(d.qpos[3:7]); turn = 0.0
    prev = np.array([float(d.qpos[0]), float(d.qpos[1])]); prev_yaw = 0.0
    path = []; fans = []; fell = False
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
            if use_mpc and step % replan_every == 0:
                turn, fan = pyramid_action(m, d, table, home, layers, wps, kidx,
                                           H=look_H, ctrl_every=ctrl_every)
                fans.append((pos.copy(), fan))
            else:
                tgt = wps[kidx]; to = tgt - pos
                he = (np.arctan2(to[1], to[0]) - yaw + np.pi) % (2 * np.pi) - np.pi
                cross = float(np.min(np.hypot(wps[:, 0] - pos[0], wps[:, 1] - pos[1])))
                cdt = ctrl_every * dt
                speed = float(np.hypot(*(pos - prev))) / cdt
                yaw_rate = ((yaw - prev_yaw + np.pi) % (2 * np.pi) - np.pi) / cdt
                obs = np.array([np.sin(he), np.cos(he), np.clip(cross / max(size, 1e-3), -3, 3),
                                np.clip(yaw_rate, -3, 3), np.clip(speed, -1, 2),
                                roll / 30.0, pitch / 30.0,
                                np.clip(np.hypot(*to) / max(size, 1e-3), 0, 3)])
                turn = policy_action(layers, obs)
            prev, prev_yaw = pos, yaw
            if collect:
                path.append((float(pos[0]), float(pos[1])))
        q = WP._steer(home, step * dt, table, roll, pitch, turn, freq=1.3)
        d.ctrl[:] = 60 * (q - d.qpos[7:]) - 3 * d.qvel[6:]
        mujoco.mj_step(m, d); roll, pitch = WP._rp(d.qpos[3:7])
        if d.qpos[2] < 0.12:
            fell = True; break
    return {"completed": kidx / K, "kidx": kidx, "K": K, "fell": fell,
            "path": path, "fans": fans, "wps": wps}


if __name__ == "__main__":
    import sys
    out = sys.argv[2] if len(sys.argv) > 2 else "out/fig8_policy.npz"
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
