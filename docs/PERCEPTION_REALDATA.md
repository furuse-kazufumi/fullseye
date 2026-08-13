# v15 — perception stack on real footage (video I/O + honest field measurements)

The v14 perception blocks (optical flow, motion energy/events, dominant/residual
motion, moving-region segmentation, sparse point tracking) were validated against
*synthetic* pairs with known ground truth. v15 adds the missing piece to run them
on **actual rendered clips** — a video reader — and reports **measured** results
on real FullSense footage, where there is no ground-truth flow.

## `video.py` — clips as numpy frames

`fullseye.read_frames(path, gray=True, step=1, start=0, max_frames=None)` decodes
an mp4/gif into `(T, H, W)` gray or `(T, H, W, 3)` RGB float64 `[0, 1]`;
`iter_frames` streams them; `frame_pairs` yields the consecutive `(prev, nxt)`
pairs the flow functions consume; `write_video` encodes results back; `probe`
reads fps/size. Backends: imageio (mp4 via the bundled imageio-ffmpeg, gif
natively) with an OpenCV fallback — both optional, so the numpy core never
hard-depends on a video library. All re-exported through the `fullseye` facade.

Round-trip is dimension-preserving: gif is exact; mp4 uses `macro_block_size=1`
+ one-pixel even-padding so the writer does **not** silently resize the frame up
to a multiple of 16 (a bug the round-trip test caught).

## The honesty metric: photometric reconstruction gain

Real footage has no ground-truth flow, so `examples/perception_on_video.py`
judges the flow by *self-consistency*: warp `prev` by the estimated flow and
measure how much closer it gets to `nxt` than the raw frame difference —

```
recon_gain = 1 − mean|nxt − warp(prev, u, v)| / mean|nxt − prev|
```

`recon_gain > 0` means the flow reconstructs `nxt` better than the no-motion
(identity) baseline — a **necessary** condition for useful flow, not a proof of
per-pixel correctness; `≈ 0` means it found no motion; `< 0` means the "flow" is
noise that, when warped, corrupts an already-good match.

## Measured results (real FullSense render clips)

Local assets (onocollo / hillco physics renders — not vendored). Reproduce with
`py -3.11 examples/perception_on_video.py <clip> --save out [--max-frames N] [--step K]`.

| clip | size · fps | frames | energy max (px) | recon_gain | events | dominant transl. (px) | movers | track disp (px) |
|---|---|---|---|---|---|---|---|---|
| `rocket_arc.mp4` | 380×460 · 50 | 60 | 5.67 | **+0.69** | 1 @ 51 | (0.08, **−1.00**) | 1 (area 7882) | 14.8 (35/36) |
| `box_grasp.mp4` (chopstick) | 440×320 · 25 | 41 | 4.57 | **+0.43** | 0 | (0.01, 0.00) | 3 (area 5201) | 16.4 (35/36) |
| `undulator_1min.mp4` (swimmer) | 360×270 · 20 | 60 (step 2) | 5.44 | **+0.28** | 3 @ 0,19,46 | (0.00, −0.01) | 2 (area 3886) | 4.9 (36/36) |
| `mujoco_control.gif` (car) | 240×319 | 60 | 0.54 | **−0.28** | 3 | (0.00, 0.00) | 3 | 0.5 (36/36) |

Readings that match what the clips actually show:
- **rocket_arc**: strongest gain (0.69); dominant motion is almost pure vertical
  (v = −1.0 px/frame = the world moving down as the rocket climbs); one motion
  event at frame-pair 51 (the burn/launch); one large mover (the rocket).
- **box_grasp**: the chopstick descent/grasp is the largest track displacement
  (16.4 px) with near-zero global motion — a static camera, one articulated hand.
- **undulator**: continuous swimming motion, three energy peaks over the clip.

## The negative case is honest, not a failure

`mujoco_control.gif` reads a **negative** recon_gain at step 1 — and that is
correct behaviour. Its peak inter-frame motion is 0.54 px (sub-pixel), and it is
a 256-colour GIF, so `|nxt − prev|` is dominated by palette-dither noise, not
motion. Dense LK rightly reports ~0 flow; warping by ~0 flow cannot remove dither,
so the gain is slightly negative. Sampling wider frames confirms the mechanism:

| sampling | peak motion (px) | recon_gain |
|---|---|---|
| step 1 | 0.54 | −0.28 |
| step 3 | 1.04 | **+0.45** |
| step 5 | 1.47 | **+0.54** |

**Practical guidance for consumers** (onocollo / evis / hillco): sample frames at
a step that yields ≳ 1 px inter-frame displacement; below that the photometric
residual is rendering/dither noise and dense flow has nothing to lock onto.

## Wiring & tests

- `video.py` re-exported via `api.py` and the `fullseye` facade
  (`read_frames`/`iter_frames`/`frame_pairs`/`write_video`, plus `fullseye.video.probe`).
- `tests/test_video.py` — 17 round-trip + coercion tests (gif/mp4, gray/color,
  step/start/max, odd-dim padding, dtype, error paths). mp4/gif backends ship
  with the environment, so no external assets are needed.
- `tests/test_examples.py` — synthetic self-test of `perception_on_video`
  (asserts recon_gain > 0.3, one event, ~8 px burst pan) plus a real-clip test
  that runs on `rocket_arc.mp4`/`box_grasp.mp4` when present and is skipped
  otherwise (keeps the suite portable).

## honest limits

- `recon_gain` is a *self-consistency* proxy against the no-motion baseline, not
  accuracy against true flow (none exists for real footage); it is a necessary,
  not sufficient, indicator — it rewards explaining brightness change, so large
  illumination shifts or occlusion boundaries can depress it even when the
  visible motion is tracked well.
- `n_moving_segments` / `largest_segment_area` come from `motion_segments` on the
  residual field; on real footage they can include residual-warp artefacts near
  the frame border, so treat the mover *count* as indicative, not exact.
- `mean_track_disp_px` is net start→end displacement over the window, not arc
  length, and mixes any surviving background points with the moving ones.
- GIF sources are palette-quantised; prefer mp4 for photometric work.
- These remain 2-D/2.5-D building blocks; no learned motion model is involved.
