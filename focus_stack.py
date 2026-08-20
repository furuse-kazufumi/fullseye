"""Focus stacking (焦点合成): build a focal stack by simulating depth-of-field from a
MuJoCo RGB + **ground-truth depth** render, then fuse the sharpest region of each
frame into one all-in-focus image — and recover a depth-from-focus map for free.

The scene has objects at a range of distances, so no single focus setting is sharp
everywhere (that's the whole point of focus stacking). For each focus distance we
blur every pixel by its circle-of-confusion ∝ |depth − focus| (a genuine thin-lens
model driven by the true depth), giving one stack frame. Fusion picks, per pixel,
the frame with the highest local sharpness (Laplacian energy). We report an honest
metric: the fused image's sharpness beats every single stack frame, and the
depth-from-focus map correlates with the true depth.

    import focus_stack as FS
    FS.run_focus_stack_demo("out/focus_stack.png")      # -> dict incl. sharpness gain
"""
from __future__ import annotations

import numpy as np

_SCENE = """
<mujoco model="focus scene">
  <visual><global offwidth="1280" offheight="960"/></visual>
  <worldbody>
    <light pos="0.5 -1 2" dir="-0.2 0.5 -1" diffuse="0.9 0.9 0.9"/>
    <light pos="-1 0 1.5" dir="0.5 0 -1" diffuse="0.4 0.4 0.4"/>
    <geom name="floor" type="plane" size="6 6 0.1" rgba="0.32 0.34 0.4 1"/>
    <geom type="box" pos="0.35 0.0 0.06" size="0.06 0.06 0.06" rgba="0.90 0.35 0.30 1"/>
    <geom type="box" pos="0.75 0.10 0.09" size="0.09 0.09 0.09" rgba="0.30 0.72 0.45 1"/>
    <geom type="box" pos="1.25 -0.10 0.12" size="0.12 0.12 0.12" rgba="0.30 0.55 0.90 1"/>
    <geom type="box" pos="1.9 0.12 0.16" size="0.16 0.16 0.16" rgba="0.92 0.76 0.25 1"/>
    <geom type="sphere" pos="2.7 -0.15 0.2" size="0.2" rgba="0.70 0.42 0.85 1"/>
  </worldbody>
</mujoco>
"""


def _render_rgb_depth(res=480):
    import mujoco
    m = mujoco.MjModel.from_xml_string(_SCENE)
    d = mujoco.MjData(m); mujoco.mj_forward(m, d)
    cam = mujoco.MjvCamera(); cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    cam.lookat[:] = [1.2, 0.0, 0.12]; cam.distance = 1.9; cam.azimuth = 12; cam.elevation = -14
    ren = mujoco.Renderer(m, height=res, width=res)
    ren.update_scene(d, camera=cam); rgb = ren.render().astype(np.float32) / 255.0
    ren.enable_depth_rendering(); ren.update_scene(d, camera=cam)
    depth = np.asarray(ren.render(), np.float32); ren.close()
    return rgb, depth


def _gauss(img, sigma):
    """Separable Gaussian blur (stdlib/numpy only — no scipy dependency)."""
    if sigma < 0.4:
        return img.copy()
    rad = max(1, int(3 * sigma))
    x = np.arange(-rad, rad + 1)
    k = np.exp(-(x ** 2) / (2 * sigma ** 2)); k /= k.sum()
    out = img
    for ax in (0, 1):
        out = np.apply_along_axis(lambda mm: np.convolve(mm, k, mode="same"), ax, out)
    return out


def _dof_frame(rgb, levels, sigmas, coc):
    """Compose a depth-of-field frame: each pixel takes the pre-blurred level whose
    sigma is closest to its circle-of-confusion. Vectorised over the discrete levels."""
    idx = np.abs(sigmas[:, None, None] - coc[None]).argmin(axis=0)      # (H,W) nearest level
    out = np.zeros_like(rgb)
    for li in range(len(levels)):
        mask = (idx == li)
        out[mask] = levels[li][mask]
    return out


def _sharpness(gray):
    """Local Laplacian energy — the focus measure used for fusion."""
    lap = (-4 * gray
           + np.roll(gray, 1, 0) + np.roll(gray, -1, 0)
           + np.roll(gray, 1, 1) + np.roll(gray, -1, 1))
    return lap ** 2


def run_focus_stack_demo(out_png="out/focus_stack.png", *, n_focus=7, coc_gain=7.0, log=print):
    """Simulate a focal stack, fuse it all-in-focus, and score it honestly."""
    import importlib.util
    if importlib.util.find_spec("mujoco") is None:
        raise RuntimeError("mujoco 未インストール")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rgb, depth = _render_rgb_depth()
    fg = (depth > 0) & (depth < depth.max() * 0.98)                     # ignore the far sky/back
    dmin, dmax = np.percentile(depth[fg], 2), np.percentile(depth[fg], 98)

    sigmas = np.array([0.0, 1.0, 2.0, 3.5, 5.0, 7.0])
    levels = [_gauss(rgb, s) for s in sigmas]                           # pre-blurred pyramid
    focus_dists = np.linspace(dmin, dmax, n_focus)
    stack = []
    for f in focus_dists:
        coc = np.clip(coc_gain * np.abs(depth - f), 0, sigmas[-1])
        stack.append(_dof_frame(rgb, levels, sigmas, coc))

    grays = [s.mean(axis=2) for s in stack]
    sharp = np.stack([_gauss(_sharpness(g), 2.0) for g in grays])       # smoothed focus measure
    best = sharp.argmax(axis=0)                                         # per-pixel sharpest frame
    fused = np.zeros_like(rgb)
    for fi in range(len(stack)):
        m_ = (best == fi); fused[m_] = stack[fi][m_]

    def sh(img):
        return float(_sharpness(img.mean(axis=2))[fg].mean())
    stack_sh = [sh(s) for s in stack]
    fused_sh = sh(fused)
    gain = fused_sh / max(1e-9, max(stack_sh))
    # depth-from-focus: map each pixel's sharpest-frame index to its focus distance
    dff = focus_dists[best]
    corr = float(np.corrcoef(dff[fg].ravel(), depth[fg].ravel())[0, 1])

    bg, fgc, muted = "#12141b", "#e2e5ec", "#8b91a0"
    fig, ax = plt.subplots(2, 3, figsize=(13, 8.4), facecolor=bg)
    for a in ax.ravel():
        a.axis("off")
    ax[0, 0].imshow(np.clip(stack[0], 0, 1)); ax[0, 0].set_title(f"stack: focus @ near ({focus_dists[0]:.2f}m)", color=fgc)
    ax[0, 1].imshow(np.clip(stack[n_focus // 2], 0, 1)); ax[0, 1].set_title(f"stack: focus @ mid ({focus_dists[n_focus//2]:.2f}m)", color=fgc)
    ax[0, 2].imshow(np.clip(stack[-1], 0, 1)); ax[0, 2].set_title(f"stack: focus @ far ({focus_dists[-1]:.2f}m)", color=fgc)
    ax[1, 0].imshow(np.clip(fused, 0, 1)); ax[1, 0].set_title(f"FUSED all-in-focus (sharpness ×{gain:.1f})", color="#22d3bf")
    im = ax[1, 1].imshow(dff, cmap="turbo"); ax[1, 1].set_title(f"depth-from-focus (corr {corr:.2f})", color=fgc)
    ax[1, 2].imshow(depth, cmap="turbo"); ax[1, 2].set_title("true depth (MuJoCo)", color=fgc)
    fig.suptitle("Focus stacking — fuse the sharp region of each focus setting", color=fgc, fontsize=14)

    import os
    os.makedirs(os.path.dirname(out_png) or ".", exist_ok=True)
    fig.tight_layout(); fig.savefig(out_png, dpi=115, facecolor=bg); plt.close(fig)
    log(f"focus stack: {out_png} | n_focus={n_focus} fused_sharpness×{gain:.2f} "
        f"depth-from-focus_corr={corr:.2f}")
    return {"png": out_png, "sharpness_gain": gain, "depth_focus_corr": corr,
            "n_focus": n_focus,
            # weak metric by construction (argmax fusion nearly always beats any single
            # frame) — depth_focus_corr is the substantive validation, this is auxiliary
            "beats_all_frames": bool(gain > 1.0)}


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "out/focus_stack.png"
    print(run_focus_stack_demo(out, log=lambda s: print(s, flush=True)))
