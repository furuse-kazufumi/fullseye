"""LIDAR simulation: a spinning-LIDAR range scan cast by **real ray-tracing** against
a MuJoCo scene (``mj_ray``), rendered headless as a point cloud (GPU-free).

A ring-style LIDAR (N elevation channels × M azimuth steps, like a Velodyne) sits
above a small scene of primitives. Each beam is an actual ray traced against the
scene geometry; the hit distance gives a 3-D point. We render the reference camera
view beside the returned point cloud (coloured by height) and report honest scan
stats (points returned / rays cast, mean range). Nothing is faked — a beam that
misses everything returns no point.

    import lidar_sim as LS
    LS.run_lidar_demo("out/lidar.png")                  # -> dict incl. hit_ratio, n_points
"""
from __future__ import annotations

import numpy as np

_SCENE = """
<mujoco model="lidar scene">
  <visual><global offwidth="1280" offheight="960"/></visual>
  <worldbody>
    <light pos="0 0 3" dir="0 0 -1" directional="true"/>
    <geom name="floor" type="plane" size="4 4 0.1" rgba="0.3 0.33 0.4 1"/>
    <geom type="box" pos="0.8 0.2 0.25" size="0.2 0.2 0.25" rgba="0.85 0.4 0.3 1"/>
    <geom type="box" pos="-0.6 -0.7 0.15" size="0.15 0.3 0.15" rgba="0.3 0.7 0.45 1"/>
    <geom type="sphere" pos="-0.9 0.6 0.3" size="0.3" rgba="0.3 0.55 0.9 1"/>
    <geom type="cylinder" pos="0.3 -0.9 0.35" size="0.18 0.35" rgba="0.9 0.75 0.25 1"/>
    <geom type="box" pos="1.4 -0.5 0.4" size="0.12 0.5 0.4" rgba="0.7 0.4 0.85 1"/>
    <geom type="capsule" pos="-1.5 -0.2 0.2" size="0.12 0.25" rgba="0.35 0.78 0.75 1"/>
  </worldbody>
</mujoco>
"""


def _scan(m, d, origin, *, channels=32, az_steps=360, fov_deg=(-18.0, 12.0), max_range=8.0):
    """Cast a ring LIDAR from *origin*; return hit points (K,3) and hit-ratio."""
    import mujoco
    el = np.deg2rad(np.linspace(fov_deg[0], fov_deg[1], channels))
    az = np.linspace(0, 2 * np.pi, az_steps, endpoint=False)
    pnt = np.asarray(origin, float)
    gid = np.array([-1], np.int32)
    pts, hits, total = [], 0, 0
    for e in el:
        ce, se = np.cos(e), np.sin(e)
        for a in az:
            vec = np.array([ce * np.cos(a), ce * np.sin(a), se])
            dist = mujoco.mj_ray(m, d, pnt, vec, None, 1, -1, gid)
            total += 1
            if 0 <= dist <= max_range:
                pts.append(pnt + dist * vec); hits += 1
    return (np.array(pts) if pts else np.zeros((0, 3))), hits / max(1, total)


def run_lidar_demo(out_png="out/lidar.png", *, channels=32, az_steps=360,
                   sensor_h=0.9, log=print):
    """Render the reference view + the LIDAR point cloud and report scan stats."""
    import importlib.util
    if importlib.util.find_spec("mujoco") is None:
        raise RuntimeError("mujoco 未インストール")
    import mujoco
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image

    m = mujoco.MjModel.from_xml_string(_SCENE)
    d = mujoco.MjData(m); mujoco.mj_forward(m, d)
    origin = (0.0, 0.0, sensor_h)
    pts, hit_ratio = _scan(m, d, origin, channels=channels, az_steps=az_steps)

    # reference camera view
    ren = mujoco.Renderer(m, height=480, width=640)
    cam = mujoco.MjvCamera(); cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    cam.lookat[:] = [0, 0, 0.25]; cam.distance = 4.6; cam.azimuth = 130; cam.elevation = -28
    ren.update_scene(d, camera=cam)
    ref = Image.fromarray(ren.render()); ren.close()

    bg, fg, muted = "#12141b", "#e2e5ec", "#8b91a0"
    fig = plt.figure(figsize=(12, 5.2), facecolor=bg)
    ax0 = fig.add_subplot(1, 2, 1); ax0.imshow(np.asarray(ref)); ax0.axis("off")
    ax0.set_title("reference scene (MuJoCo)", color=fg, fontsize=12)
    ax1 = fig.add_subplot(1, 2, 2, projection="3d", facecolor=bg)
    if len(pts):
        sctr = ax1.scatter(pts[:, 0], pts[:, 1], pts[:, 2], c=pts[:, 2], cmap="turbo",
                           s=3, depthshade=False)
        cb = fig.colorbar(sctr, ax=ax1, shrink=0.6, pad=0.08); cb.set_label("height z (m)", color=fg)
        cb.ax.yaxis.set_tick_params(color=muted); plt.setp(cb.ax.get_yticklabels(), color=muted)
    ax1.scatter([origin[0]], [origin[1]], [origin[2]], c="red", s=40, marker="^")
    ax1.set_title(f"LIDAR point cloud — {len(pts)} points ({channels}ch)", color=fg, fontsize=12)
    for pane in (ax1.xaxis, ax1.yaxis, ax1.zaxis):
        pane.set_pane_color((0.07, 0.08, 0.11, 1.0)); pane.label.set_color(muted)
    ax1.tick_params(colors=muted); ax1.set_xlabel("x"); ax1.set_ylabel("y"); ax1.set_zlabel("z")
    ax1.view_init(elev=32, azim=-60)

    import os
    os.makedirs(os.path.dirname(out_png) or ".", exist_ok=True)
    fig.tight_layout(); fig.savefig(out_png, dpi=120, facecolor=bg); plt.close(fig)
    rng = float(np.linalg.norm(pts - np.array(origin), axis=1).mean()) if len(pts) else 0.0
    log(f"lidar: {out_png} | {channels}ch×{az_steps}az rays={channels*az_steps} "
        f"points={len(pts)} hit_ratio={hit_ratio*100:.0f}% mean_range={rng:.2f}m")
    return {"png": out_png, "n_points": int(len(pts)), "hit_ratio": float(hit_ratio),
            "mean_range_m": rng, "channels": channels}


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "out/lidar.png"
    print(run_lidar_demo(out, log=lambda s: print(s, flush=True)))
