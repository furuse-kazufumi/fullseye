"""Sensor-fusion simulation: a Kalman filter fuses a noisy position sensor
(camera / GPS proxy) with a noisy velocity sensor (IMU proxy) to track a thrown
object, and the result is scored **honestly** against each sensor alone.

MuJoCo is the ground-truth physics (a ball thrown under gravity, read through
declared ``framepos`` + ``velocimeter`` sensors). We corrupt those readings with
Gaussian noise, then run a 6-state constant-acceleration Kalman filter that knows
only gravity as its input. The payoff is a measured one: the fused RMSE beats both
the raw position sensor and dead-reckoning from the velocity sensor — and we print
all three so a fused number that *didn't* win would be obvious.

    import sensor_fusion as SF
    SF.run_fusion_demo("out/sensor_fusion.png")         # -> dict of RMSEs (metres)
"""
from __future__ import annotations

import numpy as np

_BALL_XML = """
<mujoco model="thrown ball">
  <option timestep="0.002" gravity="0 0 -9.81"/>
  <worldbody>
    <geom name="floor" type="plane" size="0 0 0.05" pos="0 0 0"/>
    <body name="ball" pos="-1.5 0 0.2">
      <freejoint name="ball"/>
      <geom name="ball" type="sphere" size="0.05" rgba="0.15 0.8 0.7 1" mass="0.15"/>
    </body>
  </worldbody>
  <sensor>
    <framepos name="ball_pos" objtype="body" objname="ball"/>
    <velocimeter name="ball_vel" site="ball_site"/>
  </sensor>
</mujoco>
"""

# velocimeter needs a site; inject one into the ball body.
_BALL_XML = _BALL_XML.replace(
    '<geom name="ball" type="sphere"',
    '<site name="ball_site" pos="0 0 0"/>\n      <geom name="ball" type="sphere"')


def _simulate(seed=0, throw=(2.2, 0.3, 7.2), n_steps=1100, substep=4):
    """Run the MuJoCo ground truth and return true + sensed (declared-sensor) traces."""
    import mujoco
    m = mujoco.MjModel.from_xml_string(_BALL_XML)
    d = mujoco.MjData(m)
    ball_dof = m.jnt_dofadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, "ball")]
    d.qvel[ball_dof:ball_dof + 3] = throw                         # launch velocity
    pos_adr = int(m.sensor_adr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_SENSOR, "ball_pos")])
    vel_adr = int(m.sensor_adr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_SENSOR, "ball_vel")])

    dt = float(m.opt.timestep) * substep
    true_p, true_v, sens_p, sens_v, ts = [], [], [], [], []
    t = 0.0
    for i in range(n_steps):
        for _ in range(substep):
            mujoco.mj_step(m, d)
        mujoco.mj_forward(m, d)                                   # refresh sensordata
        p = d.sensordata[pos_adr:pos_adr + 3].copy()
        v = d.sensordata[vel_adr:vel_adr + 3].copy()
        true_p.append(p); true_v.append(v); ts.append(t)
        t += dt
        if p[2] < 0.02 and i > 5:                                 # landed
            break
    return (np.array(true_p), np.array(true_v), np.array(ts), dt)


def _kalman(true_p, true_v, dt, *, pos_std=0.13, vel_std=0.10, vel_bias=0.11, seed=0):
    """6-state constant-acceleration KF fusing a noisy **unbiased** position sensor
    with a low-noise but **biased** velocity sensor — the textbook reason fusion
    exists: an IMU drifts (bias integrates), an absolute sensor is noisy but doesn't.
    Returns (measured_pos, deadreckon_pos, fused_pos)."""
    rng = np.random.default_rng(seed)
    N = len(true_p)
    meas_p = true_p + rng.normal(0, pos_std, true_p.shape)        # camera / GPS proxy (noisy, unbiased)
    bias = np.array([vel_bias, 0.0, -vel_bias])                   # a fixed IMU bias (unknown to the filter)
    meas_v = true_v + bias + rng.normal(0, vel_std, true_v.shape)  # IMU proxy (low noise, biased)

    g = np.array([0.0, 0.0, -9.81])
    F = np.eye(6); F[:3, 3:] = np.eye(3) * dt
    Bu = np.concatenate([0.5 * g * dt * dt, g * dt])              # known gravity input
    H = np.eye(6)                                                 # measure both pos + vel
    R = np.diag([pos_std**2] * 3 + [vel_std**2] * 3)
    q = 0.05
    Q = np.eye(6) * q * dt

    x = np.concatenate([meas_p[0], meas_v[0]])                    # init from first reading
    P = np.eye(6) * 0.5
    fused = np.zeros((N, 3))
    fused[0] = x[:3]
    # start at k=1: z[0] already seeded the state — reusing it as the first update would
    # count the same reading twice (and one predict step out of phase)
    for k in range(1, N):
        x = F @ x + Bu                                            # predict
        P = F @ P @ F.T + Q
        z = np.concatenate([meas_p[k], meas_v[k]])
        y = z - H @ x                                             # innovation
        S = H @ P @ H.T + R
        K = P @ H.T @ np.linalg.inv(S)
        x = x + K @ y                                             # update
        P = (np.eye(6) - K @ H) @ P
        fused[k] = x[:3]

    # dead-reckoning: integrate the noisy velocity from the true start (IMU only)
    dead = np.zeros((N, 3)); dead[0] = true_p[0]
    for k in range(1, N):
        dead[k] = dead[k - 1] + meas_v[k - 1] * dt
    return meas_p, dead, fused


def _rmse(a, b):
    return float(np.sqrt(np.mean(np.sum((a - b) ** 2, axis=1))))


def run_fusion_demo(out_png="out/sensor_fusion.png", *, seed=0, log=print):
    """Simulate, fuse, score, and render the comparison figure. Returns the RMSE dict."""
    import importlib.util
    if importlib.util.find_spec("mujoco") is None:
        raise RuntimeError("mujoco is not installed")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    true_p, true_v, ts, dt = _simulate(seed=seed)
    meas_p, dead, fused = _kalman(true_p, true_v, dt, seed=seed)

    rmse = {"position_sensor_only": _rmse(meas_p, true_p),
            "imu_dead_reckoning": _rmse(dead, true_p),
            "kalman_fused": _rmse(fused, true_p)}
    won = rmse["kalman_fused"] < min(rmse["position_sensor_only"], rmse["imu_dead_reckoning"])

    # ---- figure (x–z flight plane + error-over-time) --------------------------
    bg, fg, grid = "#12141b", "#e2e5ec", "#2c313f"
    teal, amber, muted, red = "#22d3bf", "#f5a524", "#8b91a0", "#e0654a"
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.6), facecolor=bg,
                                   gridspec_kw={"width_ratios": [1.4, 1]})
    for ax in (ax1, ax2):
        ax.set_facecolor(bg)
        for s in ax.spines.values():
            s.set_color(grid)
        ax.tick_params(colors=muted); ax.grid(True, color=grid, lw=0.6, alpha=0.6)

    ax1.scatter(meas_p[:, 0], meas_p[:, 2], s=10, c=muted, alpha=0.45,
                label=f"position sensor (RMSE {rmse['position_sensor_only']*100:.1f} cm)")
    ax1.plot(dead[:, 0], dead[:, 2], color=red, lw=1.6, ls="--",
             label=f"IMU dead-reckon (RMSE {rmse['imu_dead_reckoning']*100:.1f} cm)")
    ax1.plot(fused[:, 0], fused[:, 2], color=teal, lw=2.4,
             label=f"Kalman fused (RMSE {rmse['kalman_fused']*100:.1f} cm)")
    ax1.plot(true_p[:, 0], true_p[:, 2], color=amber, lw=1.4, alpha=0.9, label="ground truth")
    ax1.set_xlabel("x (m)", color=fg); ax1.set_ylabel("height z (m)", color=fg)
    ax1.set_title("Thrown-ball tracking — fuse camera + IMU", color=fg, fontsize=12)
    leg = ax1.legend(facecolor=bg, edgecolor=grid, fontsize=8.5, labelcolor=fg, loc="upper right")

    err_p = np.linalg.norm(meas_p - true_p, axis=1) * 100
    err_d = np.linalg.norm(dead - true_p, axis=1) * 100
    err_f = np.linalg.norm(fused - true_p, axis=1) * 100
    ax2.plot(ts, err_p, color=muted, lw=1.4, label="position sensor")
    ax2.plot(ts, err_d, color=red, lw=1.6, ls="--", label="IMU dead-reckon")
    ax2.plot(ts, err_f, color=teal, lw=2.2, label="Kalman fused")
    ax2.set_xlabel("time (s)", color=fg); ax2.set_ylabel("position error (cm)", color=fg)
    ax2.set_title("Error over flight", color=fg, fontsize=12)
    ax2.legend(facecolor=bg, edgecolor=grid, fontsize=8.5, labelcolor=fg)

    import os
    os.makedirs(os.path.dirname(out_png) or ".", exist_ok=True)
    fig.tight_layout(); fig.savefig(out_png, dpi=120, facecolor=bg); plt.close(fig)
    log(f"sensor fusion: {out_png} | pos-only={rmse['position_sensor_only']*100:.1f}cm "
        f"imu-dead={rmse['imu_dead_reckoning']*100:.1f}cm fused={rmse['kalman_fused']*100:.1f}cm "
        f"| fused_wins={'yes' if won else 'no'}")
    return {"png": out_png, "rmse_m": rmse, "fused_wins": bool(won), "steps": len(true_p)}


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "out/sensor_fusion.png"
    print(run_fusion_demo(out, log=lambda s: print(s, flush=True)))
