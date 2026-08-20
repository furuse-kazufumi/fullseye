"""Fullseye leverages the GPU-learned evis: render its walk and **perceive** it.

The control policy is learned on the GPU (MJX-PPO, torque-twin humanoid). This module is
the Fullseye side of the bridge: it takes the learned rollout (a qpos trajectory produced
by ``mjx_render.py`` under genuine physics) and runs Fullseye's unified vision on it — an
RGB view, a metric depth view (MuJoCo depth buffer), and a DVS event-camera view (the same
log-intensity-change model as ``event_camera.py``). The point isn't to re-render the walk;
it's that once evis exists as a physics rollout, **Fullseye can see it with any sensor** —
exactly the unified-vision role Fullseye is for.

    import evis_fullseye_bridge as B
    B.perceive_evis_walk("out/evis_v2_walk_qpos.npy",
                         "C:/dev/projects/ms_human_700_jaw/scene_full_mjx.xml")
"""
from __future__ import annotations

import numpy as np


def _colormap(x, lo, hi):
    """Simple teal→amber depth colormap in [lo,hi] → uint8 RGB (no matplotlib dependency)."""
    t = np.clip((x - lo) / max(hi - lo, 1e-6), 0, 1)
    r = (0.10 + 0.85 * t)
    g = (0.72 - 0.30 * t)
    b = (0.65 - 0.55 * t)
    return (np.stack([r, g, b], -1) * 255).astype(np.uint8)


def _dvs(prev_log, cur_log, C=0.18):
    """Per-frame DVS events: red = brightening (ON), blue = darkening (OFF), grey ground."""
    h, w = cur_log.shape
    img = np.full((h, w, 3), 22, np.uint8)
    diff = cur_log - prev_log
    on = diff > C; off = diff < -C
    img[on] = (34, 211, 191)                    # teal ON
    img[off] = (224, 101, 74)                   # amber-red OFF
    return img, int(on.sum() + off.sum())


def perceive_evis_walk(qpos_npy, xml, out_gif="out/evis_fullseye.gif", *, width=360, height=360,
                       max_frames=110, fps=25, body="pelvis", log=print):
    """Render the learned evis rollout and perceive it (RGB | depth | DVS). Returns honest stats
    (frames, forward distance in the rollout, mean event rate, depth span)."""
    import importlib.util
    import os
    if importlib.util.find_spec("mujoco") is None:
        raise RuntimeError("mujoco 未インストール")
    import mujoco
    from PIL import Image

    qpos = np.load(qpos_npy)
    if qpos.ndim != 2:
        raise ValueError(f"qpos npy must be (T, nq); got {qpos.shape}")
    # The training XML bakes WSL-absolute asset paths (/mnt/c/...). On Windows py311 those don't
    # resolve, so rewrite them to their C:/ drive equivalents and load from the patched string.
    with open(xml, encoding="utf-8") as f:
        xml_text = f.read()
    xml_text = xml_text.replace("/mnt/c/", "C:/").replace("/mnt/d/", "D:/")
    m = mujoco.MjModel.from_xml_string(xml_text)
    if qpos.shape[1] != m.nq:
        raise ValueError(f"qpos nq {qpos.shape[1]} != model nq {m.nq} (wrong xml for this rollout)")
    d = mujoco.MjData(m)
    pel = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, body)

    rgb = mujoco.Renderer(m, height=height, width=width)
    dep = mujoco.Renderer(m, height=height, width=width); dep.enable_depth_rendering()
    cam = mujoco.MjvCamera(); cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    cam.distance = 3.2; cam.elevation = -10.0; cam.azimuth = 120.0

    T = len(qpos); stride = max(1, T // max_frames)
    frames = []; prev_log = None; ev_counts = []; dmins = []; dmaxs = []
    fwd0 = None
    for k in range(0, T, stride):
        d.qpos[:] = qpos[k]; mujoco.mj_forward(m, d)
        cx = float(d.xpos[pel][0]) if pel >= 0 else float(d.qpos[0])
        cy = float(d.xpos[pel][1]) if pel >= 0 else 0.0
        if fwd0 is None:
            fwd0 = cx
        cam.lookat[:] = [cx, cy, 0.9]
        rgb.update_scene(d, camera=cam); rimg = rgb.render().copy()
        dep.update_scene(d, camera=cam); dimg = dep.render().copy()
        # depth: clip to a sensible band around the body, colormap
        finite = dimg[np.isfinite(dimg)]
        near, far = (np.percentile(finite, 3), np.percentile(finite, 92)) if finite.size else (0.0, 5.0)
        dmins.append(float(near)); dmaxs.append(float(far))
        dcol = _colormap(np.clip(dimg, near, far), near, far)
        # DVS from RGB luminance (log intensity)
        lum = np.log((0.299 * rimg[..., 0] + 0.587 * rimg[..., 1] + 0.114 * rimg[..., 2]) / 255.0 + 0.02)
        if prev_log is None:
            evimg = np.full_like(rimg, 22); ev = 0
        else:
            evimg, ev = _dvs(prev_log, lum)
        prev_log = lum; ev_counts.append(ev)
        # composite: RGB | depth | events, with a thin separator
        sep = np.full((height, 3, 3), 60, np.uint8)
        panel = np.concatenate([rimg, sep, dcol, sep, evimg], axis=1)
        frames.append(Image.fromarray(panel))

    os.makedirs(os.path.dirname(out_gif) or ".", exist_ok=True)
    frames[0].save(out_gif, save_all=True, append_images=frames[1:],
                   duration=int(1000 / max(1, fps)), loop=0)
    fwd = (float(d.xpos[pel][0]) if pel >= 0 else float(d.qpos[0])) - (fwd0 or 0.0)
    mean_ev = float(np.mean(ev_counts[1:])) if len(ev_counts) > 1 else 0.0
    stats = {"gif": out_gif, "frames": len(frames), "forward_m": fwd,
             "mean_events_per_frame": mean_ev,
             "depth_near_m": float(np.median(dmins)), "depth_far_m": float(np.median(dmaxs))}
    log(f"Fullseye perceives evis: {out_gif} | frames={len(frames)} rollout_fwd={fwd:.2f}m "
        f"DVS~{mean_ev:.0f} ev/frame depth[{stats['depth_near_m']:.2f},{stats['depth_far_m']:.2f}]m "
        f"(panels: RGB | depth | events)")
    return stats


if __name__ == "__main__":
    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "out/evis_v2_walk_qpos.npy"
    x = sys.argv[2] if len(sys.argv) > 2 else "C:/dev/projects/ms_human_700_jaw/scene_full_mjx.xml"
    print(perceive_evis_walk(q, x, log=lambda s: print(s, flush=True)))
