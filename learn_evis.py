"""Learn (not hand-code) a torque policy so the biped *evis*-family humanoid walks — the
same RL recipe used for the go2 figure-8, transferred to the torque twin.

Runs in the loco_mujoco venv (``C:/dev/venvs/loco``), which provides the ``HumanoidTorque``
environment: a 13-torque, 19-DoF biped on a floor, with **reference-state initialisation**
(``random_start`` seeds each episode from a mocap walk frame) and a TargetVelocity reward
that pays for moving forward at a target speed while staying upright. A small neural policy
(obs 36 → torques 13) is trained by **Evolution Strategies** to maximise the episode return
— i.e. to keep the biped walking under genuine MuJoCo physics.

Honesty by construction: the reward terminates on a fall (absorbing state), so a policy that
topples scores low; the metric we report is the measured number of upright steps and metres
walked by the *learned* policy versus the passive/random baseline — no kinematic replay.

Method caveat (review 2026-08-21): ``random_start`` re-seeds every episode from a different
mocap frame, so the mirrored pairs R(θ+σε) / R(θ−σε) are evaluated on DIFFERENT initial
states — the antithetic variance reduction is diluted by start noise (the go2 figure-8
trainer resets deterministically, where the trick is sound). The negative result reported
from this file (CPU-ES never beat the passive baseline with any of 3 reward designs) stands
on the shared-fate of all three runs plus the passive-collapse analysis, but a future retry
should share the episode seed within each ± pair (common random numbers).

    # in the loco venv:
    py learn_evis.py train   out/evis_policy.npz --iters 60
    py learn_evis.py render  out/evis_walk.gif out/evis_policy.npz
"""
from __future__ import annotations

import numpy as np

TASK = "HumanoidTorque.walk.perfect"
DIMS = None          # set after env introspection: [obs, 64, 64, act]


def make_env():
    from loco_mujoco import LocoEnv
    return LocoEnv.make(TASK)


# ----------------------------------------------------------------- policy (numpy MLP + obs norm)
def unpack(theta, dims):
    ws, off = [], 0
    for i, o in zip(dims[:-1], dims[1:]):
        w = theta[off:off + i * o].reshape(i, o); off += i * o
        b = theta[off:off + o]; off += o
        ws.append((w, b))
    return ws


def n_params(dims):
    return sum(i * o + o for i, o in zip(dims[:-1], dims[1:]))


def act(layers, obs, mean, std, lo, hi):
    x = (obs - mean) / std
    for k, (w, b) in enumerate(layers):
        x = x @ w + b
        if k < len(layers) - 1:
            x = np.tanh(x)
    a = np.tanh(x)
    return lo + (a + 1.0) * 0.5 * (hi - lo)


def _obs_of(r):
    return np.asarray(r[0] if isinstance(r, tuple) else r, dtype=float)


def rollout(env, theta, dims, mean, std, lo, hi, *, horizon=500):
    """One genuine-physics episode from an RSI walk frame; return (episode return, steps, dx)."""
    layers = unpack(theta, dims)
    obs = _obs_of(env.reset())
    tot = 0.0; x0 = float(env._data.qpos[0]); steps = 0
    for t in range(horizon):
        a = act(layers, obs, mean, std, lo, hi)
        r = env.step(a); obs = _obs_of(r)
        tot += float(r[1]); steps = t + 1
        if r[2]:                                             # absorbing (fell) → episode ends
            break
    dx = float(env._data.qpos[0]) - x0
    return tot, steps, dx


# ----------------------------------------------------------------- obs statistics (normalisation)
def collect_obs_stats(env, dims, n=6, horizon=300, seed=0):
    rng = np.random.default_rng(seed)
    P = n_params(dims); buf = []
    lo = env.info.action_space.low; hi = env.info.action_space.high
    for _ in range(n):
        obs = _obs_of(env.reset()); buf.append(obs)
        for _t in range(horizon):
            a = lo + rng.random(len(lo)) * (hi - lo)
            r = env.step(a); buf.append(_obs_of(r))
            if r[2]:
                break
    B = np.array(buf)
    mean = B.mean(0); std = B.std(0); std[std < 1e-3] = 1.0
    return mean, std


# ----------------------------------------------------------------- parallel ES workers
_W = {}


def _winit(dims, mean, std):
    env = make_env()
    _W["env"] = env; _W["dims"] = dims; _W["mean"] = mean; _W["std"] = std
    _W["lo"] = env.info.action_space.low; _W["hi"] = env.info.action_space.high


def _weval(theta):
    return rollout(_W["env"], theta, _W["dims"], _W["mean"], _W["std"], _W["lo"], _W["hi"])[0]


# ----------------------------------------------------------------- Evolution Strategies trainer
def train(out_npz="out/evis_policy.npz", *, iters=60, pop=32, sigma=0.04, lr=0.03,
          hidden=64, horizon=500, seed=0, workers=None, log=print):
    import os
    import multiprocessing as mp
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    env = make_env()
    odim = env.info.observation_space.shape[0]; adim = env.info.action_space.shape[0]
    dims = [odim, hidden, hidden, adim]
    lo = env.info.action_space.low; hi = env.info.action_space.high
    log(f"env {TASK}: obs={odim} act={adim} params={n_params(dims)}")
    mean, std = collect_obs_stats(env, dims, seed=seed)
    rng = np.random.default_rng(seed); P = n_params(dims)
    theta = rng.standard_normal(P) * 0.02
    base = rollout(env, theta * 0, dims, mean, std, lo, hi, horizon=horizon)
    log(f"passive baseline: return={base[0]:.1f} steps={base[1]} dx={base[2]:.2f}")

    workers = workers or min(mp.cpu_count(), 2 * pop)
    hist_c, hist_b, hist_steps = [], [], []
    pool = mp.Pool(workers, initializer=_winit, initargs=(dims, mean, std))
    try:
        for it in range(iters):
            eps = rng.standard_normal((pop, P))
            batch = np.concatenate([theta + sigma * eps, theta - sigma * eps], 0)
            R = np.array(pool.map(_weval, list(batch)))
            adv = R[:pop] - R[pop:]
            if adv.std() > 1e-8:
                adv = (adv - adv.mean()) / (adv.std() + 1e-8)
            theta = theta + lr * (eps.T @ adv) / pop / sigma
            cret, csteps, cdx = rollout(env, theta, dims, mean, std, lo, hi, horizon=horizon)
            hist_c.append(cret); hist_b.append(float(R.max())); hist_steps.append(csteps)
            log(f"ES it {it+1:02d}/{iters} | center_ret={cret:.1f} steps={csteps} dx={cdx:+.2f} "
                f"pop_best={R.max():.1f}")
    finally:
        pool.close(); pool.join()

    os.makedirs(os.path.dirname(out_npz) or ".", exist_ok=True)
    np.savez(out_npz, theta=theta, dims=np.array(dims), mean=mean, std=std,
             lo=lo, hi=hi, hist_c=np.array(hist_c), hist_b=np.array(hist_b),
             hist_steps=np.array(hist_steps))
    png = os.path.splitext(out_npz)[0] + "_curve.png"
    bg, fgc, teal, amber = "#12141b", "#e2e5ec", "#22d3bf", "#f5a524"
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 5.2), facecolor=bg, sharex=True)
    for a in (a1, a2):
        a.set_facecolor(bg); a.tick_params(colors="#8b91a0"); a.grid(True, color="#2c313f", lw=0.5)
        for s in a.spines.values():
            s.set_color("#2c313f")
    xs = np.arange(1, len(hist_c) + 1)
    a1.plot(xs, hist_c, color=teal, lw=2.0, label="center policy return")
    a1.plot(xs, hist_b, color=amber, lw=1.0, alpha=0.7, label="population best")
    a1.axhline(base[0], color="#8b91a0", ls=":", lw=1, label=f"passive baseline ({base[0]:.0f})")
    a1.set_ylabel("episode return", color=fgc); a1.legend(facecolor=bg, edgecolor="#2c313f",
                                                          labelcolor=fgc, fontsize=8)
    a1.set_title("Learned torque-biped walking — Evolution Strategies", color=fgc)
    a2.plot(xs, hist_steps, color=teal, lw=2.0)
    a2.axhline(base[1], color="#8b91a0", ls=":", lw=1)
    a2.set_ylabel("upright steps", color=fgc); a2.set_xlabel("ES iteration", color=fgc)
    fig.tight_layout(); fig.savefig(png, dpi=115, facecolor=bg); plt.close(fig)
    log(f"trained: {out_npz} (+{os.path.basename(png)}) | final_ret={hist_c[-1]:.1f} "
        f"final_steps={hist_steps[-1]} (baseline {base[1]})")
    return {"weights": out_npz, "curve": png, "final_return": hist_c[-1],
            "final_steps": hist_steps[-1], "baseline_steps": base[1]}


# ----------------------------------------------------------------- render the learned policy
def render(out_gif="out/evis_walk.gif", weights="out/evis_policy.npz", *, horizon=500,
          width=640, height=480, fps=30, max_gif_frames=120, log=print):
    import os
    import mujoco
    from PIL import Image
    z = np.load(weights)
    dims = list(z["dims"]); mean = z["mean"]; std = z["std"]; lo = z["lo"]; hi = z["hi"]
    layers = unpack(z["theta"], dims)
    env = make_env()
    obs = _obs_of(env.reset())
    m = env._model; d = env._data
    ren = mujoco.Renderer(m, height=height, width=width)
    cam = mujoco.MjvCamera(); cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    cam.distance = 3.4; cam.elevation = -12.0; cam.azimuth = 120.0
    frames = []; x0 = float(d.qpos[0]); steps = 0
    frame_every = max(1, horizon // int(max_gif_frames))
    for t in range(horizon):
        a = act(layers, obs, mean, std, lo, hi)
        r = env.step(a); obs = _obs_of(r); steps = t + 1
        if t % frame_every == 0:
            cam.lookat[:] = [float(d.qpos[0]), float(d.qpos[1]), 0.6]
            ren.update_scene(d, camera=cam); frames.append(Image.fromarray(ren.render()))
        if r[2]:
            break
    ren.close()
    dx = float(d.qpos[0]) - x0
    if frames:
        frames[0].save(out_gif, save_all=True, append_images=frames[1:],
                       duration=int(1000 / max(1, fps)), loop=0)
    log(f"render: {out_gif} | learned policy walked {steps} steps dx={dx:.2f} m before "
        f"{'falling' if steps < horizon else 'horizon'}")
    return {"gif": out_gif, "steps": steps, "dx": dx}


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "train"
    if cmd == "train":
        out = sys.argv[2] if len(sys.argv) > 2 else "out/evis_policy.npz"
        it = int(sys.argv[sys.argv.index("--iters") + 1]) if "--iters" in sys.argv else 60
        print(train(out, iters=it, log=lambda s: print(s, flush=True)))
    elif cmd == "render":
        out = sys.argv[2] if len(sys.argv) > 2 else "out/evis_walk.gif"
        w = sys.argv[3] if len(sys.argv) > 3 else "out/evis_policy.npz"
        print(render(out, w, log=lambda s: print(s, flush=True)))
