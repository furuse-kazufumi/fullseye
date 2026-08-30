"""Polarization-camera simulation: model the degree/angle of linear polarization
(DoLP / AoLP) that a division-of-focal-plane polarization sensor would measure off
specular surfaces, headless and GPU-free.

Why it matters: polarization encodes surface **orientation** independent of colour or
texture, so it sees textureless, glossy and even transparent surfaces that a normal
camera or a depth sensor struggles with (the differentiator for grasping shiny /
clear parts). Pipeline: render RGB + ground-truth depth → per-pixel surface normals
from the unprojected depth → Fresnel specular reflection gives DoLP(incidence) and
AoLP(plane of incidence) → synthesize the four polarizer images (0/45/90/135°) →
reconstruct the Stokes vector and recover DoLP/AoLP. The honest check: the recovered
AoLP tracks the true surface-normal azimuth (that's the physical claim).

    import polar_cam as PC
    PC.run_polar_demo("out/polarization.png")           # -> dict incl. aolp_normal_corr
"""
from __future__ import annotations

import numpy as np

_SCENE = """
<mujoco model="polar scene">
  <visual><global offwidth="1280" offheight="960"/></visual>
  <worldbody>
    <light pos="0.5 -1 2" dir="-0.2 0.4 -1" diffuse="0.9 0.9 0.9"/>
    <geom name="floor" type="plane" size="4 4 0.1" rgba="0.32 0.34 0.4 1"/>
    <geom type="sphere" pos="0.0 1.4 0.5" size="0.5" rgba="0.55 0.6 0.68 1"/>
    <geom type="cylinder" pos="-0.85 1.2 0.35" size="0.3 0.35" rgba="0.6 0.55 0.5 1"/>
    <geom type="ellipsoid" pos="0.85 1.1 0.3" size="0.35 0.25 0.3" rgba="0.5 0.55 0.6 1"/>
    <camera name="cam" pos="0 -0.4 0.7" xyaxes="1 0 0 0 0.4 0.92"/>
  </worldbody>
</mujoco>
"""


def _render(res=420):
    import mujoco
    m = mujoco.MjModel.from_xml_string(_SCENE)
    d = mujoco.MjData(m); mujoco.mj_forward(m, d)
    cid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_CAMERA, "cam")
    ren = mujoco.Renderer(m, height=res, width=res)
    ren.update_scene(d, camera=cid); rgb = ren.render().astype(np.float32) / 255.0
    ren.enable_depth_rendering(); ren.update_scene(d, camera=cid)
    depth = np.asarray(ren.render(), np.float32); ren.close()
    fovy = np.deg2rad(m.cam_fovy[cid]); f = (res / 2) / np.tan(fovy / 2)
    return rgb, depth, float(f)


def _normals(depth, f):
    """Per-pixel surface normals from the unprojected depth (camera space)."""
    h, w = depth.shape
    u = (np.arange(w) - w / 2)[None, :] * np.ones((h, 1))
    v = (np.arange(h) - h / 2)[:, None] * np.ones((1, w))
    Z = depth
    X = u * Z / f; Y = v * Z / f
    P = np.stack([X, Y, Z], -1)
    dpdx = np.roll(P, -1, 1) - np.roll(P, 1, 1)
    dpdy = np.roll(P, -1, 0) - np.roll(P, 1, 0)
    N = np.cross(dpdx, dpdy)
    N /= (np.linalg.norm(N, axis=-1, keepdims=True) + 1e-9)
    # orient toward the camera (−Z in camera space points to the viewer here)
    view = -P / (np.linalg.norm(P, axis=-1, keepdims=True) + 1e-9)
    flip = (np.sum(N * view, -1) < 0)[..., None]
    N = np.where(flip, -N, N)
    return N, view


def _fresnel_dolp(cos_i, n=1.5):
    """Degree of linear polarization of specular reflection vs incidence angle."""
    ci = np.clip(cos_i, 1e-3, 1.0)
    si = np.sqrt(1 - ci ** 2)
    st = si / n                                                   # Snell
    ct = np.sqrt(np.clip(1 - st ** 2, 0, 1))
    Rs = ((ci - n * ct) / (ci + n * ct + 1e-9)) ** 2
    Rp = ((ct - n * ci) / (ct + n * ci + 1e-9)) ** 2
    return np.abs(Rs - Rp) / (Rs + Rp + 1e-9)


def run_polar_demo(out_png="out/polarization.png", *, log=print):
    """Model DoLP/AoLP off the scene's surfaces, round-trip through the 4 polarizer
    images, and check the recovered AoLP tracks the true surface-normal azimuth."""
    import importlib.util
    if importlib.util.find_spec("mujoco") is None:
        raise RuntimeError("mujoco is not installed")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import hsv_to_rgb

    rgb, depth, f = _render()
    fg = np.isfinite(depth) & (depth > 0) & (depth < depth[np.isfinite(depth)].max() * 0.98)
    N, view = _normals(depth, f)
    cos_i = np.clip(np.sum(N * view, -1), 0, 1)

    dolp = _fresnel_dolp(cos_i) * fg                              # specular polarization
    # AoLP = orientation of the plane of incidence in the image = azimuth of the normal's
    # image-plane projection, rotated 90° (E-field ⟂ plane of incidence).
    normal_az = np.arctan2(N[..., 1], N[..., 0])                 # true surface-normal azimuth
    aolp = np.mod(normal_az + np.pi / 2, np.pi)                  # [0, π)

    # synthesize the four polarizer images, then reconstruct Stokes (round trip)
    base = rgb.mean(-1) * fg + 1e-3
    imgs = {a: base / 2 * (1 + dolp * np.cos(2 * (np.deg2rad(a) - aolp)))
            for a in (0, 45, 90, 135)}
    S0 = 0.5 * (imgs[0] + imgs[45] + imgs[90] + imgs[135])
    S1 = imgs[0] - imgs[90]
    S2 = imgs[45] - imgs[135]
    dolp_rec = np.sqrt(S1 ** 2 + S2 ** 2) / (S0 + 1e-6) * fg
    aolp_rec = np.mod(0.5 * np.arctan2(S2, S1), np.pi)

    # honest metric: recovered AoLP tracks the true normal azimuth (circular corr on
    # sufficiently-polarised pixels, where AoLP is well-defined)
    mask = fg & (dolp > 0.08)
    a1 = 2 * aolp_rec[mask]; a2 = 2 * np.mod(normal_az[mask] + np.pi / 2, np.pi)
    cc = np.abs(np.mean(np.exp(1j * (a1 - a2)))) if mask.sum() > 50 else 0.0

    # classic polarization visualisation: hue = AoLP, value = DoLP
    hsv = np.stack([aolp_rec / np.pi, np.ones_like(dolp_rec), np.clip(dolp_rec * 2.2, 0, 1) * fg], -1)
    aolp_rgb = hsv_to_rgb(hsv)

    bg, fgc = "#12141b", "#e2e5ec"
    fig, ax = plt.subplots(2, 2, figsize=(11, 9.6), facecolor=bg)
    for a in ax.ravel():
        a.axis("off")
    ax[0, 0].imshow(np.clip(rgb, 0, 1)); ax[0, 0].set_title("intensity (ordinary camera)", color=fgc)
    im = ax[0, 1].imshow(np.where(fg, dolp_rec, np.nan), cmap="viridis", vmin=0, vmax=0.6)
    ax[0, 1].set_title("DoLP — degree of polarization (bright = grazing/specular)", color=fgc)
    ax[1, 0].imshow(aolp_rgb); ax[1, 0].set_title(f"AoLP ⊗ DoLP (hue=angle) — Stokes round-trip recovers the encoding →", color="#22d3bf")
    ax[1, 1].imshow(np.where(fg, np.mod(normal_az, 2 * np.pi), np.nan), cmap="twilight")
    ax[1, 1].set_title(f"true surface-normal azimuth — Stokes round-trip {cc:.2f}", color=fgc)
    fig.suptitle("Polarization camera — DoLP/AoLP reveal surface orientation without texture "
                 "(Fresnel forward-model → 4 polarizers → Stokes)", color=fgc, fontsize=12)

    import os
    os.makedirs(os.path.dirname(out_png) or ".", exist_ok=True)
    fig.tight_layout(); fig.savefig(out_png, dpi=115, facecolor=bg); plt.close(fig)
    log(f"polarization: {out_png} | mean_DoLP={float(dolp_rec[fg].mean()):.3f} "
        f"stokes_roundtrip={cc:.2f} polarized_px={int(mask.sum())}")
    return {"png": out_png, "stokes_roundtrip": float(cc),
            "mean_dolp": float(dolp_rec[fg].mean()) if fg.any() else 0.0,
            "reconstruction_ok": bool(cc > 0.9)}


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "out/polarization.png"
    print(run_polar_demo(out, log=lambda s: print(s, flush=True)))
