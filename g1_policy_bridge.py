"""Run the GPU-trained G1 walking policy inside Fullseye — no JAX/GPU/WSL needed at runtime.

The policy is trained on the GPU (MJX + brax PPO, ``mjx_humanoid_walk.py`` in WSL). This
module is the Fullseye side: it loads the brax checkpoint, re-implements the tiny policy
MLP in pure numpy (4x32 swish -> tanh head, observation normalizer), and re-creates the
training environment's observation/control pipeline on NATIVE MuJoCo so a trained
checkpoint can be rolled out, watched and measured from Studio on Windows.

Faithfulness notes (each one is a measured lesson from the training side):
  * The obs layout must match the training env EXACTLY (gyro, projected gravity, cmd,
    joint pos/vel, last action, clip phase, steering [y-offset, yaw], and for the vision
    env the pseudo-LiDAR rays + their x20 temporal change). One wrong slot and the policy
    is garbage — parity is verified against brax inference in the test suite.
  * Control is RESIDUAL around the mocap reference: ctrl = clip(ref[i, 7:] + res * a).
  * The training model reduced collisions to feet+floor and capped solver iterations at 6;
    the same edits are applied here so the native dynamics stay close to the MJX ones.
    (The cylinder->capsule swap is NOT needed: those shoulder geoms end up non-collidable
    after the feet-only reduction, and native MuJoCo handles cylinders fine.)

JAX is imported ONLY inside load_policy() to unpickle the checkpoint's jax.Array leaves
(CPU jax is enough); everything after that is numpy + mujoco.

    import g1_policy_bridge as G
    out = G.g1_walk_policy("out/humanoid/mjx_g1_walk12b_params.pkl",
                           "out/humanoid/g1_walk_cycle_straight.npy", secs=8)
"""
from __future__ import annotations

import os

import numpy as np

G1_XML = "C:/dev/projects/mujoco_menagerie/unitree_g1/scene.xml"
_REF_DEFAULT = "C:/dev/projects/onocollo-complete/out/humanoid/g1_walk_cycle_straight.npy"


# ------------------------------------------------------------------ policy (numpy)
class _Stub:
    """Duck-typed stand-in for brax/flax container classes referenced by the checkpoint
    pickle — only the attribute payload matters (jax.Array leaves + dicts), so brax does
    NOT need to be installed on the Fullseye side."""

    def __init__(self, *a, **k):
        self.__dict__.update(k)

    def __setstate__(self, state):
        if isinstance(state, dict):
            self.__dict__.update(state)
        elif isinstance(state, tuple):
            for s in state:
                if isinstance(s, dict):
                    self.__dict__.update(s)


class _CkptUnpickler:
    def __new__(cls, f):
        import pickle

        class U(pickle.Unpickler):
            def find_class(self, module, name):
                try:
                    return super().find_class(module, name)
                except (ImportError, AttributeError):
                    return type(name, (_Stub,), {})
        return U(f)


def load_policy(pkl_path):
    """brax PPO checkpoint -> plain numpy dict {mean, std, layers=[(W,b),...], act_size}.

    The pickle holds (normalizer_state, policy_params[, value_params]); its jax.Array
    leaves need CPU jax to deserialize, and missing brax/flax classes are stubbed —
    after this call nothing touches jax again.
    """
    with open(pkl_path, "rb") as f:
        params = _CkptUnpickler(f).load()
    norm, pol = params[0], params[1]
    mean = np.asarray(norm.mean, dtype=np.float64)
    std = np.asarray(norm.std, dtype=np.float64)
    tree = pol["params"] if "params" in pol else pol
    names = sorted(tree.keys(), key=lambda s: int(s.split("_")[-1]))
    layers = [(np.asarray(tree[n]["kernel"], np.float64),
               np.asarray(tree[n]["bias"], np.float64)) for n in names]
    act_size = layers[-1][1].shape[0] // 2          # head emits (loc, raw_scale)
    return {"mean": mean, "std": std, "layers": layers,
            "obs_size": mean.shape[0], "act_size": act_size}


def policy_action(pol, obs):
    """Deterministic brax-PPO action for one observation: normalize -> MLP(swish) -> tanh(loc)."""
    h = (np.asarray(obs, np.float64) - pol["mean"]) / pol["std"]
    n = len(pol["layers"])
    for k, (W, b) in enumerate(pol["layers"]):
        h = h @ W + b
        if k < n - 1:
            # swish(x) = x * sigmoid(x), overflow-safe on both tails
            h = h * np.where(h >= 0, 1.0 / (1.0 + np.exp(-np.abs(h))),
                             np.exp(-np.abs(h)) / (1.0 + np.exp(-np.abs(h))))
    loc = h[: pol["act_size"]]
    return np.tanh(loc)


# ------------------------------------------------------------------ env (native MuJoCo)
def _rot_inv(quat, v):
    """Rotate world vector v into the body frame (quat is wxyz) — same math as training."""
    w, x, y, z = quat
    c = np.array([-x, -y, -z])
    t = 2.0 * np.cross(c, v)
    return v + w * t + np.cross(c, t)


def _yaw(quat):
    w, x, y, z = quat
    return np.arctan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))


class G1PolicySession:
    """Staged API: load the checkpoint and the mocap reference once, then step/run/render
    piecewise — the same layered pattern as ``PerceptionSession`` (1-line facade below).

    Faithful numpy twin of the training envs G1Mimic (proprioception + steering) and
    G1VisionWalk (+ pseudo-LiDAR over random obstacle cylinders).
    """

    def __init__(self, params_pkl, ref_npy=_REF_DEFAULT, xml=G1_XML, *,
                 vision=False, ref_fps=30.0, ref_start=0, ref_len=0, res_scale=0.4,
                 corridor=2.5, n_frames=10,
                 n_obst=8, obst_r=0.30, rays=16, ray_fov=180.0, ray_max=4.0,
                 obst_x=(2.5, 16.0), obst_y=1.2, hit_dist=0.45, seed=0):
        import mujoco
        self._mujoco = mujoco
        self.pol = load_policy(params_pkl)
        self.vision = bool(vision)

        m = mujoco.MjModel.from_xml_path(xml)
        # dynamics parity with the trainer: solver caps + feet-only collision set
        m.opt.iterations = 6
        m.opt.ls_iterations = 6
        feet = set()
        for nm in ("left_ankle_roll_link", "right_ankle_roll_link"):
            bid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, nm)
            if bid >= 0:
                feet.add(bid)
        for g in range(m.ngeom):
            is_plane = int(m.geom_type[g]) == int(mujoco.mjtGeom.mjGEOM_PLANE)
            if not (is_plane or int(m.geom_bodyid[g]) in feet):
                m.geom_contype[g] = 0
                m.geom_conaffinity[g] = 0
        self.m, self.d = m, mujoco.MjData(m)
        self.xml = xml
        self._n_frames = int(n_frames)
        self.dt = float(m.opt.timestep) * self._n_frames
        self._default = m.key_qpos[0][7:].copy()
        self._lo = m.actuator_ctrlrange[:, 0].copy()
        self._hi = m.actuator_ctrlrange[:, 1].copy()
        self._nu = m.nu
        self._res = float(res_scale)
        self._corridor = float(corridor)
        self._term_z, self._term_tilt, self._dev_z = 0.45, 0.5, 0.3

        # ---- reference clip: resample to control dt, renormalize quats, root velocity
        # with the wrap-spike filter — byte-for-byte the same recipe as G1Mimic.__init__
        ref = np.load(ref_npy)
        ref = ref[ref_start: ref_start + ref_len if ref_len else None]
        t_src = np.arange(len(ref)) / float(ref_fps)
        t_dst = np.arange(0.0, t_src[-1], self.dt)
        R = np.stack([np.interp(t_dst, t_src, ref[:, i]) for i in range(ref.shape[1])], 1)
        R[:, 3:7] /= np.maximum(np.linalg.norm(R[:, 3:7], axis=1, keepdims=True), 1e-8)
        rv = np.zeros((len(R), 2))
        rv[1:] = (R[1:, :2] - R[:-1, :2]) / self.dt
        rv[0] = rv[1]
        sp = np.linalg.norm(rv, axis=1)
        bad = sp > 3.0 * float(np.median(sp)) + 0.5
        if bad.any() and (~bad).any():
            rv[bad] = rv[~bad].mean(axis=0)
        self.ref, self.ref_rootv, self.ref_n = R, rv, len(R)

        # ---- vision channel (identical geometry to G1VisionWalk / pseudo_lidar_rays)
        self._nray = int(rays)
        self._ray_ang = np.linspace(-ray_fov / 2, ray_fov / 2, int(rays)) * np.pi / 180.0
        self._ray_max = float(ray_max)
        self._hit = float(hit_dist)
        rng = np.random.default_rng(seed)
        self.obst = np.stack([rng.uniform(obst_x[0], obst_x[1], n_obst),
                              rng.uniform(-obst_y, obst_y, n_obst),
                              np.full(n_obst, obst_r)], axis=1) if vision else None

        want = 98 + 2 + (2 * self._nray if vision else 0)
        if self.pol["obs_size"] != want:
            raise ValueError(f"checkpoint expects obs={self.pol['obs_size']}, env builds {want} "
                             f"(vision={vision}) — wrong ckpt/env combination")
        self._i = 0
        self._last_action = np.zeros(self._nu)
        self._prev_rays = None
        self.qpos_hist: list[np.ndarray] = []

    # ---------------- observation (must mirror G1Walk._obs + G1Mimic steer + vision)
    def _rays(self):
        p, yaw = self.d.qpos[:2], _yaw(self.d.qpos[3:7])
        ang = self._ray_ang + yaw
        dvec = np.stack([np.cos(ang), np.sin(ang)], axis=1)
        rel = self.obst[:, :2] - p[None, :]
        t_c = rel @ dvec.T
        per2 = np.sum(rel * rel, axis=1)[:, None] - np.square(t_c)
        r2 = np.square(self.obst[:, 2])[:, None]
        hit = (per2 <= r2) & (t_c > 0.0)
        t_hit = np.where(hit, t_c - np.sqrt(np.maximum(r2 - per2, 0.0)), self._ray_max)
        return np.clip(t_hit.min(axis=0), 0.0, self._ray_max) / self._ray_max

    def _obs(self):
        q, v = self.d.qpos, self.d.qvel
        i = self._i
        gyro = v[3:6].copy()                                  # free-joint angvel is body-frame
        gvec = _rot_inv(q[3:7], np.array([0.0, 0.0, -1.0]))
        cmd = np.array([self.ref_rootv[i, 0], self.ref_rootv[i, 1], 0.0])
        phase = i / self.ref_n
        ph = np.array([np.sin(2 * np.pi * phase), np.cos(2 * np.pi * phase)])
        steer = np.array([q[1] - self.ref[i, 1], _yaw(q[3:7])])
        parts = [gyro, gvec, cmd, q[7:] - self._default, v[6:] * 0.05,
                 self._last_action, ph, steer]
        if self.vision:
            rays = self._rays()
            prev = rays if self._prev_rays is None else self._prev_rays
            parts += [rays, 20.0 * (rays - prev)]
            self._prev_rays = rays
        return np.nan_to_num(np.concatenate(parts), nan=0.0, posinf=0.0, neginf=0.0)

    # ---------------- staged calls
    def reset(self, start_frame=0):
        """Deterministic Reference-State-Init at ``start_frame`` (no training noise)."""
        mujoco = self._mujoco
        i = int(start_frame) % self.ref_n
        self._i = i
        self.d.qpos[:] = self.ref[i]
        self.d.qvel[:] = 0.0
        self.d.qvel[:2] = self.ref_rootv[i]
        self.d.qvel[6:] = (self.ref[(i + 1) % self.ref_n, 7:] - self.ref[i, 7:]) / self.dt
        mujoco.mj_forward(self.m, self.d)
        self._last_action = np.zeros(self._nu)
        self._prev_rays = None
        self.qpos_hist = [self.d.qpos.copy()]
        return self._obs()

    def step(self, obs):
        """One control step: policy -> residual ctrl -> n_frames physics substeps.
        Returns (obs, done, info) with the same termination tests as training."""
        mujoco = self._mujoco
        a = np.clip(policy_action(self.pol, obs), -1.0, 1.0)
        self._i = (self._i + 1) % self.ref_n
        ref = self.ref[self._i]
        self.d.ctrl[:] = np.clip(ref[7:] + self._res * a, self._lo, self._hi)
        for _ in range(self._n_frames):
            mujoco.mj_step(self.m, self.d)
        self._last_action = a
        self.qpos_hist.append(self.d.qpos.copy())

        q = self.d.qpos
        gvec = _rot_inv(q[3:7], np.array([0.0, 0.0, -1.0]))
        fallen = (q[2] < self._term_z) or (-gvec[2] < self._term_tilt)
        deviated = abs(q[2] - ref[2]) > self._dev_z
        offline = abs(q[1] - ref[1]) > self._corridor
        crashed = False
        if self.vision:
            dmin = float(np.min(np.linalg.norm(self.obst[:, :2] - q[None, :2], axis=1)
                                - self.obst[:, 2]))
            crashed = dmin < self._hit
        done = fallen or deviated or offline or crashed
        return self._obs(), done, {"fallen": fallen, "deviated": deviated,
                                   "offline": offline, "crashed": crashed}

    def run(self, secs=8.0, start_frame=0, stop_on_done=True):
        """Roll the policy for ``secs`` and return honest measurements (no reward talk —
        distance, survival and lateral error are things a ruler could check)."""
        obs = self.reset(start_frame)
        n = int(secs / self.dt)
        done_info = {}
        for _ in range(n):
            obs, done, done_info = self.step(obs)
            if done and stop_on_done:
                break
        qp = np.stack(self.qpos_hist)
        yerr = qp[:, 1] - self.ref[(np.arange(int(start_frame), int(start_frame) + len(qp))
                                    % self.ref_n), 1]
        return {"steps": len(qp) - 1, "secs": round((len(qp) - 1) * self.dt, 2),
                "distance_m": round(float(qp[-1, 0] - qp[0, 0]), 2),
                "mean_speed": round(float((qp[-1, 0] - qp[0, 0]) / max((len(qp) - 1) * self.dt, 1e-9)), 2),
                "lateral_rms_m": round(float(np.sqrt(np.mean(yerr ** 2))), 3),
                "fell": bool(done_info.get("fallen", False) or done_info.get("deviated", False)),
                "offline": bool(done_info.get("offline", False)),
                "crashed": bool(done_info.get("crashed", False)),
                "survived_horizon": len(qp) - 1 >= n}

    def save_qpos(self, path):
        """Persist the rollout trajectory — the handoff artifact every Fullseye perception
        op (robot_pov / g1_real_sensors / evis_perceive) accepts as input."""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        qp = np.stack(self.qpos_hist)
        np.save(path, qp)
        if self.vision:
            np.save(os.path.splitext(path)[0] + "_obst.npy", self.obst)
        return path

    def render(self, out_path="out/g1_policy_walk.mp4", width=640, height=480, max_frames=240):
        """Follow-camera video of the recorded rollout. With vision=True the episode's
        obstacle cylinders are injected into a temp scene so the video shows exactly
        what the policy's rays saw (same trick as the perception bridge)."""
        mujoco = self._mujoco
        xml = self.xml
        if self.vision:
            geoms = "".join(
                f'<geom name="fs_ob{k}" type="cylinder" pos="{o[0]:.3f} {o[1]:.3f} 0.5" '
                f'size="{o[2]:.3f} 0.5" rgba="0.85 0.5 0.3 1" contype="0" conaffinity="0"/>'
                for k, o in enumerate(self.obst))
            txt = open(self.xml, encoding="utf-8").read().replace(
                "<worldbody>", "<worldbody>" + geoms, 1)
            xml = os.path.join(os.path.dirname(self.xml), "._fs_policy_obst.xml")
            with open(xml, "w", encoding="utf-8") as f:
                f.write(txt)
        m = mujoco.MjModel.from_xml_path(xml)
        if xml != self.xml:
            os.unlink(xml)
        d = mujoco.MjData(m)
        r = mujoco.Renderer(m, height=height, width=width)
        cam = mujoco.MjvCamera()
        cam.type = mujoco.mjtCamera.mjCAMERA_FREE
        cam.distance, cam.elevation, cam.azimuth = 3.0, -12.0, 120.0
        qp = np.stack(self.qpos_hist)
        stride = max(1, len(qp) // max_frames)
        frames = []
        for k in range(0, len(qp), stride):
            d.qpos[:] = qp[k]
            mujoco.mj_forward(m, d)
            cam.lookat[:] = [float(d.qpos[0]), float(d.qpos[1]), 0.6]
            r.update_scene(d, camera=cam)
            frames.append(r.render())
        r.close()
        import imageio
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        imageio.mimwrite(out_path, frames, fps=max(1, int(1 / self.dt / stride)))
        return out_path


# ------------------------------------------------------------------ 1-line facade
def g1_walk_policy(params_pkl, ref_npy=_REF_DEFAULT, *, secs=8.0, vision=False,
                   out_video="out/g1_policy_walk.mp4", out_qpos="", seed=0, **kw):
    """One call: checkpoint in -> measured rollout + follow-camera video out.

    Returns the honest metrics dict from ``G1PolicySession.run`` plus artifact paths.
    ``vision=True`` rolls the pseudo-LiDAR obstacle policy (checkpoint must match).
    """
    s = G1PolicySession(params_pkl, ref_npy, vision=vision, seed=seed, **kw)
    out = s.run(secs=secs)
    if out_qpos:
        out["qpos_npy"] = s.save_qpos(out_qpos)
    if out_video:
        out["video"] = s.render(out_video)
    return out


# ------------------------------------------------------------------ training curves
def training_curves(log_path):
    """Parse a trainer log (the ``[tag] step ... key=val`` progress lines) into arrays —
    Studio can plot reward / ep_len / perr / crash over steps without touching the GPU box."""
    import re
    rows = []
    pat = re.compile(r"step\s+(\d+)\s+\((\d+)/s\)\s+(.*)")
    with open(log_path, encoding="utf-8", errors="replace") as f:
        for line in f:
            mt = pat.search(line)
            if not mt:
                continue
            row = {"step": float(mt.group(1)), "sps": float(mt.group(2))}
            for k, v in re.findall(r"(\w+)=([+-]?[\d.]+)", mt.group(3)):
                try:
                    row[k] = float(v)
                except ValueError:
                    pass
            rows.append(row)
    if not rows:
        return {"step": np.zeros(0)}
    keys = sorted({k for r in rows for k in r})
    return {k: np.array([r.get(k, np.nan) for r in rows]) for k in keys}
