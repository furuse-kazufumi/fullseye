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
    """Per-frame DVS events: teal = brightening (ON), amber-red = darkening (OFF), dark ground."""
    h, w = cur_log.shape
    img = np.full((h, w, 3), 22, np.uint8)
    diff = cur_log - prev_log
    on = diff > C; off = diff < -C
    img[on] = (34, 211, 191)                    # teal ON
    img[off] = (224, 101, 74)                   # amber-red OFF
    return img, int(on.sum() + off.sum())


def perceive_evis_walk(qpos_npy, xml, out_gif="out/evis_fullseye.gif", *, width=360, height=360,
                       max_frames=110, fps=25, body="pelvis", ego_body=None, ego_h=0.35,
                       ego_dist=2.5, log=print):
    """Render the learned evis rollout and perceive it (RGB | depth | DVS). Returns honest stats
    (frames, forward distance in the rollout, mean event rate, depth span).

    With ``ego_body`` set (e.g. ``"torso_link"`` for the G1), the sensors are MOUNTED ON THE
    ROBOT: a first-person camera rides ``ego_h`` above that body, faces the body's yaw heading,
    and the depth + DVS panels are computed from THAT view — the panel layout becomes
    third-person RGB | robot's-eye RGB | robot's-eye depth | robot's-eye DVS."""
    import importlib.util
    import os
    if importlib.util.find_spec("mujoco") is None:
        raise RuntimeError("mujoco 未インストール")
    import mujoco
    from PIL import Image

    qpos = np.load(qpos_npy)
    if qpos.ndim != 2:
        raise ValueError(f"qpos npy must be (T, nq); got {qpos.shape}")
    if len(qpos) == 0:
        raise ValueError(f"empty rollout: {qpos_npy} has 0 frames (nothing to perceive)")
    # Two loading regimes, chosen by inspecting the file (measured, both real):
    #  * evis scene_full_mjx.xml bakes WSL-absolute asset paths (/mnt/c/...) that Windows
    #    py311 can't resolve -> rewrite to drive letters and load from the patched STRING;
    #  * menagerie scenes (G1 etc.) are <include>-based with relative assets, which
    #    from_xml_string can NEVER resolve -> load by PATH.
    with open(xml, encoding="utf-8") as f:
        xml_text = f.read()
    if "/mnt/" in xml_text:
        xml_text = xml_text.replace("/mnt/c/", "C:/").replace("/mnt/d/", "D:/")
        m = mujoco.MjModel.from_xml_string(xml_text)
    else:
        m = mujoco.MjModel.from_xml_path(xml)
    if qpos.shape[1] != m.nq:
        raise ValueError(f"qpos nq {qpos.shape[1]} != model nq {m.nq} (wrong xml for this rollout)")
    d = mujoco.MjData(m)
    pel = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, body)

    rgb = mujoco.Renderer(m, height=height, width=width)
    dep = mujoco.Renderer(m, height=height, width=width); dep.enable_depth_rendering()
    cam = mujoco.MjvCamera(); cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    cam.distance = 3.2; cam.elevation = -10.0; cam.azimuth = 120.0
    ego = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, ego_body) if ego_body else -1
    if ego_body and ego < 0:
        raise ValueError(f"ego_body {ego_body!r} not found in model")
    ecam = mujoco.MjvCamera(); ecam.type = mujoco.mjtCamera.mjCAMERA_FREE

    def _ego_cam(dd):
        """Place the free camera AT the robot's head, looking along its yaw heading.
        MuJoCo's free camera sits at lookat - distance*dir(azimuth, elevation), so putting
        lookat one distance AHEAD of the eye along that direction puts the camera on the eye."""
        import math
        qw, qx, qy, qz = dd.qpos[3:7]
        yaw = math.atan2(2.0 * (qw * qz + qx * qy), 1.0 - 2.0 * (qy * qy + qz * qz))
        el = math.radians(-5.0)                       # look slightly down, like a walking human
        dv = np.array([math.cos(el) * math.cos(yaw), math.cos(el) * math.sin(yaw), math.sin(el)])
        eye = dd.xpos[ego].copy(); eye[2] += ego_h    # head-mounted: ride above the torso body
        ecam.lookat[:] = eye + dv * ego_dist
        ecam.distance = ego_dist
        ecam.azimuth = math.degrees(yaw)
        ecam.elevation = -5.0

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
        if ego >= 0:
            # robot's-eye sensors: RGB + depth + DVS all from the head-mounted camera
            _ego_cam(d)
            rgb.update_scene(d, camera=ecam); eimg = rgb.render().copy()
            dep.update_scene(d, camera=ecam); dimg = dep.render().copy()
            sens = eimg
        else:
            dep.update_scene(d, camera=cam); dimg = dep.render().copy()
            sens = rimg
        # depth: clip to a sensible band around the body, colormap
        finite = dimg[np.isfinite(dimg)]
        near, far = (np.percentile(finite, 3), np.percentile(finite, 92)) if finite.size else (0.0, 5.0)
        dmins.append(float(near)); dmaxs.append(float(far))
        dcol = _colormap(np.clip(dimg, near, far), near, far)
        # DVS from the sensor view's luminance (log intensity)
        lum = np.log((0.299 * sens[..., 0] + 0.587 * sens[..., 1] + 0.114 * sens[..., 2]) / 255.0 + 0.02)
        if prev_log is None:
            evimg = np.full_like(sens, 22); ev = 0
        else:
            evimg, ev = _dvs(prev_log, lum)
        prev_log = lum; ev_counts.append(ev)
        # composite with thin separators: 3rd-person | (ego) | depth | events
        sep = np.full((height, 3, 3), 60, np.uint8)
        panels = [rimg] + ([eimg] if ego >= 0 else []) + [dcol, evimg]
        panel = panels[0]
        for pnl in panels[1:]:
            panel = np.concatenate([panel, sep, pnl], axis=1)
        frames.append(Image.fromarray(panel))

    os.makedirs(os.path.dirname(out_gif) or ".", exist_ok=True)
    frames[0].save(out_gif, save_all=True, append_images=frames[1:],
                   duration=int(1000 / max(1, fps)), loop=0)
    fwd = (float(d.xpos[pel][0]) if pel >= 0 else float(d.qpos[0])) - (fwd0 or 0.0)
    mean_ev = float(np.mean(ev_counts[1:])) if len(ev_counts) > 1 else 0.0
    stats = {"gif": out_gif, "frames": len(frames), "forward_m": fwd,
             "mean_events_per_frame": mean_ev,
             "depth_near_m": float(np.median(dmins)), "depth_far_m": float(np.median(dmaxs))}
    layout = "3rd-person RGB | robot's-eye RGB | robot's-eye depth | robot's-eye DVS" \
        if ego >= 0 else "RGB | depth | events"
    log(f"Fullseye perceives evis: {out_gif} | frames={len(frames)} rollout_fwd={fwd:.2f}m "
        f"DVS~{mean_ev:.0f} ev/frame depth[{stats['depth_near_m']:.2f},{stats['depth_far_m']:.2f}]m "
        f"(panels: {layout})")
    return stats


_G1_OBSTACLES = """
    <geom name="fs_p1" type="cylinder" pos="3.0 1.5 0.6" size="0.15 0.6" rgba="0.85 0.5 0.3 1"/>
    <geom name="fs_p2" type="cylinder" pos="2.0 -1.8 0.5" size="0.18 0.5" rgba="0.4 0.7 0.5 1"/>
    <geom name="fs_b1" type="box" pos="-2.5 1.6 0.4" size="0.3 0.3 0.4" rgba="0.4 0.55 0.9 1"/>
    <geom name="fs_b2" type="box" pos="4.0 -0.6 0.5" size="0.25 0.25 0.5" rgba="0.8 0.75 0.3 1"/>
    <geom name="fs_s1" type="sphere" pos="-1.0 -2.4 0.35" size="0.35" rgba="0.75 0.4 0.8 1"/>
    <geom name="fs_wall" type="box" pos="5.5 0 1.0" size="0.1 4.0 1.0" rgba="0.5 0.52 0.6 1"/>
    <geom name="fs_p3" type="cylinder" pos="-4.0 -1.5 0.9" size="0.2 0.9" rgba="0.6 0.6 0.65 1"/>
"""


def perceive_g1_real(qpos_npy, xml, out_gif="out/g1_real_sensors.gif", *, height=300,
                     max_frames=110, fps=25, obstacles=False, log=print):
    """Perceive a G1 rollout through the robot's REAL head-sensor suite, spec-matched:

    * **Livox Mid-360 LiDAR** (head top): 360° azimuth, vertical FOV −7°..+52°, 15 m clip
      here (spec 40 m) — sampled as a 16×180 ray grid via ``mj_multiRay`` (the real unit's
      non-repetitive pattern integrates to similar coverage). Rendered as a heading-up
      bird's-eye point cloud, height-colored, rings every 4 m.
    * **RealSense D435i depth camera** (face, forward): 87°×58° FOV, depth band 0.3–6 m
      (the sensor's practical range), plus its RGB view.
    * No DVS panel — the real G1 carries no event camera.

    Mounts are MEASURED from the model at the stand keyframe (head is rigid on torso_link):
    Mid-360 at torso+(0.004, 0, 0.496) → z≈1.33 m; D435i at torso+(0.080, 0, 0.326) →
    z≈1.16 m, facing the torso x axis. Both ride the torso's full yaw+pitch.
    Panels: third-person RGB | D435i RGB | D435i depth | Mid-360 bird's-eye."""
    import importlib.util
    import math
    import os
    if importlib.util.find_spec("mujoco") is None:
        raise RuntimeError("mujoco 未インストール")
    import mujoco
    from PIL import Image

    qpos = np.load(qpos_npy)
    if qpos.ndim != 2 or len(qpos) == 0:
        raise ValueError(f"bad rollout {qpos_npy}: shape {qpos.shape}")
    m = mujoco.MjModel.from_xml_path(xml)
    if qpos.shape[1] != m.nq:
        raise ValueError(f"qpos nq {qpos.shape[1]} != model nq {m.nq}")
    me = mujoco.MjModel.from_xml_path(xml)      # second model: D435i optics (58° vertical FOV)
    me.vis.global_.fovy = 58.0
    d = mujoco.MjData(m)
    de = mujoco.MjData(me)
    tid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "torso_link")
    if tid < 0:
        raise ValueError("torso_link not found — is this a G1 scene?")
    OFF_LIDAR = np.array([0.004, 0.0, 0.496])   # torso-frame head-top mount (measured)
    OFF_CAM = np.array([0.080, 0.0, 0.326])     # torso-frame face mount (measured)
    D_NEAR, D_FAR, L_MAX, BEV_HALF = 0.3, 6.0, 15.0, 12.0

    # Mid-360 ray grid (world-frame directions rebuilt per frame from torso yaw is unnecessary:
    # the scan is 360° so a fixed world-frame grid IS the sensor's coverage; only the BEV
    # display rotates into the robot's heading)
    elv = np.deg2rad(np.linspace(-7.0, 52.0, 16))
    azs = np.linspace(0.0, 2.0 * np.pi, 180, endpoint=False)
    VEC = np.stack([np.outer(np.cos(elv), np.cos(azs)).ravel(),
                    np.outer(np.cos(elv), np.sin(azs)).ravel(),
                    np.repeat(np.sin(elv), len(azs))], axis=1)
    NRAY = len(VEC)

    w_cam = int(round(height * math.tan(math.radians(87 / 2)) / math.tan(math.radians(58 / 2))))
    rgb3 = mujoco.Renderer(m, height=height, width=height)
    rgbe = mujoco.Renderer(me, height=height, width=w_cam)
    depe = mujoco.Renderer(me, height=height, width=w_cam); depe.enable_depth_rendering()
    cam3 = mujoco.MjvCamera(); cam3.type = mujoco.mjtCamera.mjCAMERA_FREE
    cam3.distance = 3.2; cam3.elevation = -10.0; cam3.azimuth = 120.0
    came = mujoco.MjvCamera(); came.type = mujoco.mjtCamera.mjCAMERA_FREE

    # BEV static layer: range rings every 4 m + center marker
    yy, xx = np.mgrid[0:height, 0:height]
    rr = np.hypot(xx - height / 2, yy - height / 2) * (2 * BEV_HALF / height)
    ring_mask = (np.abs(rr - 4.0) < 0.10) | (np.abs(rr - 8.0) < 0.10) | (np.abs(rr - 12.0) < 0.12)

    T = len(qpos); stride = max(1, T // max_frames)
    frames = []; hit_counts = []
    for k in range(0, T, stride):
        d.qpos[:] = qpos[k]; mujoco.mj_forward(m, d)
        de.qpos[:] = qpos[k]; mujoco.mj_forward(me, de)
        tp = d.xpos[tid]; R = d.xmat[tid].reshape(3, 3)
        fwd = R @ np.array([1.0, 0.0, 0.0])
        yaw = math.atan2(fwd[1], fwd[0])
        el = math.asin(float(np.clip(fwd[2], -1.0, 1.0)))
        # third person follows the pelvis
        cam3.lookat[:] = [float(d.qpos[0]), float(d.qpos[1]), 0.9]
        rgb3.update_scene(d, camera=cam3); img3 = rgb3.render().copy()
        # D435i: free camera seated ON the face mount, along the torso's yaw+pitch
        eye = tp + R @ OFF_CAM
        dv = np.array([math.cos(el) * math.cos(yaw), math.cos(el) * math.sin(yaw), math.sin(el)])
        came.lookat[:] = eye + dv * 2.0; came.distance = 2.0
        came.azimuth = math.degrees(yaw); came.elevation = math.degrees(el)
        rgbe.update_scene(de, camera=came); imge = rgbe.render().copy()
        depe.update_scene(de, camera=came); dimg = depe.render().copy()
        dcol = _colormap(np.clip(dimg, D_NEAR, D_FAR), D_NEAR, D_FAR)
        # Mid-360: real ray-cast scan from the head top
        origin = (tp + R @ OFF_LIDAR).astype(np.float64)
        geomid = np.full(NRAY, -1, np.int32); dist = np.zeros(NRAY)
        mujoco.mj_multiRay(m, d, origin, VEC.ravel(), None, 1, -1, geomid, dist, None, NRAY, L_MAX)
        hit = (geomid >= 0) & (dist > 0) & (dist <= L_MAX)
        pts = origin[None, :] + dist[hit, None] * VEC[hit]
        keep = np.hypot(pts[:, 0] - origin[0], pts[:, 1] - origin[1]) > 0.45   # self-return filter
        pts = pts[keep]; hit_counts.append(int(len(pts)))
        bev = np.full((height, height, 3), 16, np.uint8)
        bev[ring_mask] = 45
        if len(pts):
            relp = pts - origin
            c_, s_ = math.cos(-yaw), math.sin(-yaw)
            bx = c_ * relp[:, 0] - s_ * relp[:, 1]
            by = s_ * relp[:, 0] + c_ * relp[:, 1]
            scale = height / (2 * BEV_HALF)
            row = (height / 2 - bx * scale).astype(int)
            col = (height / 2 - by * scale).astype(int)
            ok = (row >= 0) & (row < height - 1) & (col >= 0) & (col < height - 1)
            colors = _colormap(pts[:, 2], 0.0, 1.5)
            for dr in (0, 1):                      # 2x2 dots so points survive GIF quantization
                for dc in (0, 1):
                    bev[row[ok] + dr, col[ok] + dc] = colors[ok]
        bev[height // 2 - 2:height // 2 + 3, height // 2 - 2:height // 2 + 3] = (240, 240, 240)
        sep = np.full((height, 3, 3), 60, np.uint8)
        panel = img3
        for pnl in (imge, dcol, bev):
            panel = np.concatenate([panel, sep, pnl], axis=1)
        frames.append(Image.fromarray(panel))

    os.makedirs(os.path.dirname(out_gif) or ".", exist_ok=True)
    frames[0].save(out_gif, save_all=True, append_images=frames[1:],
                   duration=int(1000 / max(1, fps)), loop=0)
    stats = {"gif": out_gif, "frames": len(frames),
             "mid360_mean_returns": float(np.mean(hit_counts)),
             "mid360_rays_per_frame": NRAY,
             "d435i_band_m": [D_NEAR, D_FAR]}
    log(f"G1 real-sensor perception: {out_gif} | frames={len(frames)} "
        f"Mid-360 returns/frame={stats['mid360_mean_returns']:.0f}/{NRAY} "
        f"D435i band {D_NEAR}-{D_FAR}m (panels: 3rd | D435i RGB | D435i depth | Mid-360 BEV)")
    return stats


if __name__ == "__main__":
    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "out/evis_v2_walk_qpos.npy"
    x = sys.argv[2] if len(sys.argv) > 2 else "C:/dev/projects/ms_human_700_jaw/scene_full_mjx.xml"
    print(perceive_evis_walk(q, x, log=lambda s: print(s, flush=True)))
