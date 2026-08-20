"""Stereo-vision simulation: render a rectified stereo pair from MuJoCo, run the
project's block-matching stereo (``stereo.py``) to estimate depth, and score it
against MuJoCo's **ground-truth depth** — headless, GPU-free.

Two parallel cameras a baseline apart view a textured scene (texture is what block
matching needs). We compute a disparity map, convert it to metric depth with the
pinhole relation ``Z = f·b / disparity``, and compare to the true depth the
simulator hands us. The honest metric: the estimated depth correlates with truth
and its median error is small — reported, not asserted.

    import stereo_sim as SS
    SS.run_stereo_demo("out/stereo.png")                # -> dict incl. depth_corr, median_err
"""
from __future__ import annotations

import numpy as np

# Two parallel cameras offset along world x by the baseline, both looking down -Y.
_BASELINE = 0.12


def _scene_xml():
    # Random-noise texture → unique local features everywhere, so block matching has
    # something to lock onto (a periodic checker aliases and gives wrong disparities).
    return f"""
<mujoco model="stereo scene">
  <visual><global offwidth="1280" offheight="960"/></visual>
  <asset>
    <texture name="noise" type="2d" builtin="flat" mark="random" markrgb="1 1 1"
      random="0.7" rgb1="0.25 0.28 0.35" rgb2="0.55 0.5 0.45" width="512" height="512"/>
    <material name="noise" texture="noise" texrepeat="8 8" reflectance="0.05"/>
    <texture name="noise2" type="2d" builtin="flat" mark="random" markrgb="0.95 0.7 0.5"
      random="0.65" rgb1="0.3 0.35 0.4" rgb2="0.6 0.45 0.4" width="512" height="512"/>
    <material name="noise2" texture="noise2" texrepeat="3 3"/>
  </asset>
  <worldbody>
    <light pos="0 -1 2.5" dir="0 0.3 -1" directional="true"/>
    <geom name="floor" type="plane" size="4 4 0.1" material="noise"/>
    <geom type="box" pos="-0.35 0.9 0.2" size="0.2 0.2 0.2" material="noise2"/>
    <geom type="box" pos="0.35 1.5 0.3" size="0.22 0.22 0.3" material="noise"/>
    <geom type="sphere" pos="-0.1 2.2 0.35" size="0.35" material="noise2"/>
    <geom type="cylinder" pos="0.55 2.9 0.4" size="0.25 0.4" material="noise"/>
    <camera name="left"  pos="{-_BASELINE/2} -0.6 0.6" xyaxes="1 0 0 0 0.35 0.94"/>
    <camera name="right" pos="{ _BASELINE/2} -0.6 0.6" xyaxes="1 0 0 0 0.35 0.94"/>
  </worldbody>
</mujoco>
"""


def _render(res=360):
    import mujoco
    m = mujoco.MjModel.from_xml_string(_scene_xml())
    d = mujoco.MjData(m); mujoco.mj_forward(m, d)
    ren = mujoco.Renderer(m, height=res, width=res)
    def shot(camname, depth=False):
        cid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_CAMERA, camname)
        if depth:
            ren.enable_depth_rendering()
        ren.update_scene(d, camera=cid)
        out = np.asarray(ren.render()).copy()
        if depth:
            ren.disable_depth_rendering()
        return out
    left = shot("left").astype(np.float32) / 255.0
    right = shot("right").astype(np.float32) / 255.0
    depthL = shot("left", depth=True).astype(np.float32)
    # focal length in pixels from the camera's vertical fov
    cid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_CAMERA, "left")
    fovy = np.deg2rad(m.cam_fovy[cid]); f_px = (res / 2) / np.tan(fovy / 2)
    return left, right, depthL, float(f_px)


def run_stereo_demo(out_png="out/stereo.png", *, max_disp=48, block=9, log=print):
    """Render a stereo pair, estimate depth by block matching, score vs truth."""
    import importlib.util
    if importlib.util.find_spec("mujoco") is None:
        raise RuntimeError("mujoco 未インストール")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import stereo

    left, right, depth_gt, f_px = _render()
    gl = left.mean(axis=2); gr = right.mean(axis=2)
    disp = stereo.disparity_subpixel(gl, gr, max_disp=max_disp, block=block)

    valid = disp > 0.5
    depth_est = np.full_like(disp, np.nan)
    depth_est[valid] = f_px * _BASELINE / disp[valid]

    # Correlate in DISPARITY space (bounded 0..max_disp) rather than depth: depth = f·b/d
    # blows up as d→0, and a handful of far-outlier pixels would otherwise crush a
    # depth-space Pearson r even when the disparity map is clearly correct.
    fin = np.isfinite(depth_gt) & (depth_gt > 0)
    true_disp = np.where(fin, f_px * _BASELINE / np.where(fin, depth_gt, 1), 0)
    reliable = valid & fin & (disp > 3) & (true_disp < max_disp)     # skip the 1/d blow-up tail
    corr = float(np.corrcoef(disp[reliable].ravel(), true_disp[reliable].ravel())[0, 1]) if reliable.sum() > 50 else 0.0
    med_err = float(np.median(np.abs(depth_est[reliable] - depth_gt[reliable]))) if reliable.sum() > 50 else float("nan")
    good = valid
    coverage = float(reliable.sum() / max(1, fin.sum()))

    bg, fgc = "#12141b", "#e2e5ec"
    fig, ax = plt.subplots(2, 2, figsize=(11, 9.4), facecolor=bg)
    for a in ax.ravel():
        a.axis("off")
    # anaglyph-ish overlay of the pair to show the baseline shift
    lr = np.zeros_like(left); lr[..., 0] = gl; lr[..., 1] = gr; lr[..., 2] = gr
    ax[0, 0].imshow(np.clip(lr, 0, 1)); ax[0, 0].set_title("stereo pair (L=red, R=cyan)", color=fgc)
    dd = np.where(valid, disp, np.nan)
    im1 = ax[0, 1].imshow(dd, cmap="turbo"); ax[0, 1].set_title(f"disparity (block matching, ≤{max_disp}px)", color=fgc)
    im2 = ax[1, 0].imshow(np.where(good | valid, depth_est, np.nan), cmap="turbo_r")
    ax[1, 0].set_title(f"estimated depth  Z=f·b/d  (corr {corr:.2f})", color="#22d3bf")
    ax[1, 1].imshow(np.where(np.isfinite(depth_gt), depth_gt, np.nan), cmap="turbo_r")
    ax[1, 1].set_title(f"true depth (MuJoCo) — median err {med_err*100:.1f} cm", color=fgc)
    fig.suptitle("Stereo vision — depth from a rectified pair by block matching", color=fgc, fontsize=14)

    import os
    os.makedirs(os.path.dirname(out_png) or ".", exist_ok=True)
    fig.tight_layout(); fig.savefig(out_png, dpi=115, facecolor=bg); plt.close(fig)
    log(f"stereo: {out_png} | corr={corr:.2f} median_err={med_err*100:.1f}cm "
        f"coverage={coverage*100:.0f}% f={f_px:.0f}px baseline={_BASELINE}m")
    return {"png": out_png, "depth_corr": corr, "median_err_m": med_err,
            "coverage": coverage, "matches_truth": bool(med_err < 0.05 and corr > 0.4)}


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "out/stereo.png"
    print(run_stereo_demo(out, log=lambda s: print(s, flush=True)))
