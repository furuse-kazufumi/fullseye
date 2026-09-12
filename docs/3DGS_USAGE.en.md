<!-- i18n-source-sha: 37bc63784e56 -->
# Fullseye 3DGS — how to use it (one command)

[日本語](./3DGS_USAGE.md) · **English** · [简体中文](./3DGS_USAGE.zh.md) · [繁體中文](./3DGS_USAGE.tw.md) · [한국어](./3DGS_USAGE.ko.md) · [Deutsch](./3DGS_USAGE.de.md)

Turn a MuJoCo sim scene into a **3D Gaussian Splatting** model and produce a GIF you can spin
all the way around plus novel-view images. Camera poses come from the sim's ground truth, so
**no COLMAP is needed**.

## The simplest way

In the imgevolve folder:

```bat
3dgs go2 --open
```

That alone turns go2 (a quadruped robot) into 3DGS and automatically opens the finished
full-turn GIF.

- Change the scene: `3dgs cassie` / `3dgs apollo` / `3dgs anymal` / `3dgs spot`
- Your own MJCF: `3dgs <your local working path>\path\to\scene.xml`
- See the list: `3dgs --list`

## Quality presets

```bat
3dgs go2 --quality fast       :: 128px / 8k Gaussians (a few seconds, for a quick look)
3dgs go2 --quality balanced   :: 256px / 20k Gaussians (default)
3dgs go2 --quality high       :: 384px / 45k Gaussians (the cleanest)
```

## Cleaner still (densify)

```bat
3dgs go2 --quality high --densify --open
```

With `--densify`, training **grows the number of Gaussians automatically to raise detail**
(native gsplat only). On go2 it grows from about 8k to about 50k, and the body and legs come
out smoother. It finishes in a few to a dozen or so seconds.

## The backend is automatic

- If **native gsplat** (tiled CUDA) is available it uses that automatically (fast and detailed,
  hundreds of it/s)
- Otherwise it falls back automatically to **pure PyTorch** (slower, but it works)
- You can also pick explicitly with `--backend torch` / `--backend gsplat`

The launcher sets up the environment (CUDA / compiler) automatically, so you don't have to
worry about vcvars and the like.

## From Studio

Launch `spikes/studio_app.py` → in the "View sim model in 3D / make 3DGS" panel, pick the
scene name (click a chip or type it) and the quality, then "3DGS train 🎇" → when it's done
the full-turn GIF opens.

## Output

Under `out/3dgs_<scene>/` (or wherever `--out` points):
- `turntable.gif` … full-turn preview
- `novelview.png` … left = ground truth / right = novel-view render
- `gaussians.npz` … trained Gaussians (npz)
- `gaussians.ply` … standard 3DGS .ply (with native). **Drag and drop it into a web viewer such
  as SuperSplat** to open it
- `report.json` … metrics such as PSNR

## Requirements

- A GPU-training venv `.venv-gsplat` (torch cu128)
- To use native, `.gsplat-cuda` (CUDA 12.8) plus the C++ tools of VS BuildTools. Details and
  reproduction steps are in `docs/GSPLAT_NATIVE_WINDOWS.md`

> Honest note: how much `--densify` helps is scene-dependent. A solid mass like go2 comes out
> clean, but a thin biped like cassie can overfit to the training views so the hold-out gets a
> little soft. The recommendation is to try without it first and add it if you want more.

## Playing back motion (--motion)

```bat
3dgs go2 --motion --open
```

Instead of a still, this makes a **3DGS of a moving robot**. How it works:
1. Train 3DGS in the canonical pose
2. Determine which MuJoCo body (link) each Gaussian comes from by **segmentation** and rig it
3. Move the joints (default = a sine wave), and for each frame do rigid-body skinning from the
   body poses (the sim's ground truth) → re-render → `motion.gif`

Because a robot is a set of rigid links, it moves naturally without full 4D-GS. Change the
number of frames with `--frames N`.

> Honest: the default motion is a demo sine wave (not an actual walking policy). Since the sim's
> poses are ground truth it never falls apart, but slight noise can appear near the feet (the
> boundary of body assignment for the initialization points).

### Auto-generating a gait

```bat
3dgs go2 --motion --gait trot --open
```

`--gait trot` auto-generates and plays a **quadruped trot gait** (diagonal legs stepping in
phase). It detects the legs automatically from the joint names (FL/FR/RL/RR or LF/RF/LH/RH +
thigh/calf), so it works on go2 and anymal. Models it can't detect fall back to a sine wave. To
use the output of an actual walking policy, use `--motion-file traj.npy` (a qpos trajectory
(F,nq)).
