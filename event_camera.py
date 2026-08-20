"""Event camera (DVS) simulation: turn a rendered image sequence into an
asynchronous **event stream** with the standard log-intensity model, headless.

A dynamic-vision sensor fires a per-pixel event whenever the log brightness changes
by a threshold C since that pixel last fired — ON if it brightened, OFF if it dimmed.
We pan a MuJoCo camera across a scene, take the log-intensity difference between
consecutive frames, threshold it, and accumulate the ON/OFF events into an event
image. The honest check: events concentrate on moving **edges**, so event density
correlates with the reference frame's spatial-gradient magnitude.

    import event_camera as EC
    EC.run_event_demo("out/event_camera.png")           # -> dict incl. edge correlation
"""
from __future__ import annotations

import numpy as np

_SCENE = """
<mujoco model="event scene">
  <visual><global offwidth="1280" offheight="960"/></visual>
  <worldbody>
    <light pos="0 0 3" dir="0 0 -1" directional="true"/>
    <geom name="floor" type="plane" size="4 4 0.1" rgba="0.30 0.33 0.4 1"/>
    <geom type="box" pos="0.6 0.3 0.25" size="0.2 0.2 0.25" rgba="0.88 0.4 0.3 1"/>
    <geom type="sphere" pos="-0.7 0.5 0.3" size="0.3" rgba="0.3 0.55 0.9 1"/>
    <geom type="cylinder" pos="0.2 -0.8 0.35" size="0.18 0.35" rgba="0.92 0.76 0.25 1"/>
    <geom type="box" pos="-0.9 -0.6 0.2" size="0.18 0.18 0.2" rgba="0.3 0.72 0.45 1"/>
    <geom type="capsule" pos="1.2 -0.3 0.25" size="0.13 0.3" rgba="0.7 0.42 0.85 1"/>
  </worldbody>
</mujoco>
"""


def _render_pan(n_frames=24, res=360, az0=110, az1=170):
    import mujoco
    m = mujoco.MjModel.from_xml_string(_SCENE)
    d = mujoco.MjData(m); mujoco.mj_forward(m, d)
    ren = mujoco.Renderer(m, height=res, width=res)
    cam = mujoco.MjvCamera(); cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    cam.lookat[:] = [0, 0, 0.25]; cam.distance = 3.4; cam.elevation = -24
    frames = []
    for a in np.linspace(az0, az1, n_frames):
        cam.azimuth = float(a)
        ren.update_scene(d, camera=cam)
        frames.append(ren.render().astype(np.float32) / 255.0)
    ren.close()
    return frames


def _events(frames, C=0.15):
    """Standard DVS: threshold the per-pixel log-intensity change each step. Returns
    accumulated (on_count, off_count) images and the total event count."""
    logs = [np.log(f.mean(axis=2) + 0.02) for f in frames]
    on = np.zeros_like(logs[0]); off = np.zeros_like(logs[0])
    ref = logs[0]                                                      # last-fired reference
    total = 0
    for k in range(1, len(logs)):
        diff = logs[k] - ref
        pos = diff > C; neg = diff < -C
        on += pos; off += neg
        total += int(pos.sum() + neg.sum())
        ref = np.where(pos | neg, logs[k], ref)                       # reset fired pixels
    return on, off, total


def _grad_mag(gray):
    gx = np.roll(gray, -1, 1) - np.roll(gray, 1, 1)
    gy = np.roll(gray, -1, 0) - np.roll(gray, 1, 0)
    return np.hypot(gx, gy)


def run_event_demo(out_png="out/event_camera.png", *, n_frames=24, C=0.15, log=print):
    """Render a pan, emit DVS events, and score that they land on edges."""
    import importlib.util
    if importlib.util.find_spec("mujoco") is None:
        raise RuntimeError("mujoco 未インストール")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    frames = _render_pan(n_frames=n_frames)
    on, off, total = _events(frames, C=C)

    # event image: ON = teal, OFF = magenta, on a dark ground
    ev = np.zeros((*on.shape, 3), np.float32)
    ev[..., 1] += np.clip(on / max(1, on.max()), 0, 1)               # ON -> green/teal
    ev[..., 2] += np.clip(on / max(1, on.max()), 0, 1)
    ev[..., 0] += np.clip(off / max(1, off.max()), 0, 1)             # OFF -> magenta
    ev[..., 2] += np.clip(off / max(1, off.max()), 0, 1)
    ev = np.clip(ev, 0, 1)

    edges = _grad_mag(frames[n_frames // 2].mean(axis=2))
    dens = (on + off)
    corr = float(np.corrcoef(dens.ravel(), edges.ravel())[0, 1])
    ev_per_frame = total / max(1, n_frames - 1)

    bg, fgc = "#0c0e13", "#e2e5ec"
    fig, ax = plt.subplots(1, 3, figsize=(13.5, 4.8), facecolor=bg)
    for a in ax:
        a.axis("off")
    ax[0].imshow(np.clip(frames[n_frames // 2], 0, 1)); ax[0].set_title("reference frame (panning)", color=fgc)
    ax[1].imshow(ev); ax[1].set_title(f"DVS events — ON=teal / OFF=magenta ({total:,} events)", color=fgc)
    ax[2].imshow(edges, cmap="magma"); ax[2].set_title(f"spatial edges — event↔edge corr {corr:.2f}", color=fgc)
    fig.suptitle("Event camera (DVS) — log-intensity change fires per-pixel events on motion", color=fgc, fontsize=13)

    import os
    os.makedirs(os.path.dirname(out_png) or ".", exist_ok=True)
    fig.tight_layout(); fig.savefig(out_png, dpi=120, facecolor=bg); plt.close(fig)
    log(f"event camera: {out_png} | frames={n_frames} events={total} "
        f"events/frame={ev_per_frame:.0f} edge_corr={corr:.2f}")
    return {"png": out_png, "n_events": int(total), "events_per_frame": ev_per_frame,
            "edge_corr": corr, "fires_on_edges": bool(corr > 0.3)}


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "out/event_camera.png"
    print(run_event_demo(out, log=lambda s: print(s, flush=True)))
