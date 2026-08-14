# Fullseye perception stack — one-page reference

The physical-AI perception substrate (v13–v14): hand another project's numpy frames
and get measured results back. Everything is numpy-native, contract-tested, and
reached through `import fullseye`. Pipeline shape:

    frames ──▶ flow/motion (time)      objects (detect) ──▶ pose
       │                                   │
       └▶ stereo (space) ─▶ depth ─▶ point cloud ─▶ terrain (heightmap/obstacles)
                                              │
                                              └▶ pointcloud (normals/clean) ─▶ registration ─▶ 6-DoF pose (grasp)

Install: `pip install -e C:\dev\projects\imgevolve` (or add the dir to `sys.path`).
Frames are float64 grayscale in `[0,1]` (H×W), or H×W×3 for colour ops.

## Operators (521)
`fullseye.apply(img, name, a, b)` / `run_pipeline(img, [(name,a,b), …])`. Discover
with `list_ops(sort=…)`, `op_names()`, the CLI `imgevolve.py ops --search …`, or
`docs/OP_INDEX.json`. Sorts: image · color · region · feature · contour · volume.

## Motion (time axis) — `flow`, `motion`
```python
u, v  = fs.optical_flow_lk(prev, nxt, levels=3)   # pyramidal Lucas-Kanade; also optical_flow_hs
rgb   = fs.colorize_flow(u, v)                     # Middlebury wheel (dir=hue, speed=bright)
mag   = fs.flow_magnitude(u, v); ang = fs.flow_angle(u, v)
rec   = fs.warp_by_flow(prev, u, v)                # reconstruct nxt (flow check)
trk,ok= fs.track_points(prev, nxt, pts_xy)         # follow specific points (markers/objects)
e     = fs.frame_motion_energy(u, v)               # RMS speed (event signal)
M     = fs.dominant_motion(u, v)                    # robust global/camera affine motion
ru,rv = fs.residual_motion(u, v)                    # independent (object) motion
mask,segs = fs.motion_segments(u, v, threshold=2.0)# label moving regions
series = fs.motion_energy_series(frames); ev = fs.detect_events(series)  # event frames in a clip
```

## Video / higher-dimensional (T,H,W) — `videops`
A video is a first-class `(T, H, W)` float array (a stack of frames). Genuine
spatiotemporal ops — denoise a sequence over time, model + subtract a background,
find where motion happened, filter in 3-D across (t, y, x).
```python
bg  = fs.temporal_median(video)                 # static-camera background (also temporal_mean/std/max/min)
fg  = fs.background_subtraction(video, threshold=0.1)   # per-frame foreground mask
me  = fs.motion_energy(video)                   # sum |d/dt| = where motion happened
d   = fs.frame_difference(video); g = fs.temporal_gradient(video)   # inter-frame change
sm  = fs.spatiotemporal_gaussian(video, sigma_t=1, sigma_s=1)       # 3-D smooth; spatiotemporal_sobel = 3-D edges
mv  = fs.moving_average(video, window=3); fl = fs.flicker_reduce(video)
out = fs.per_frame(video, lambda f: fs.apply(f, "gauss_filter"))    # apply any 2-D op per frame
of  = fs.optical_flow_sequence(video)           # consecutive-frame flow magnitude volume
```
Fail-closed (non-3-D / non-finite / T<1 raise `ValueError`); numpy+scipy only.

## Depth (space axis) — `stereo`
```python
disp  = fs.disparity_map(left, right, method="sad")     # sad|ssd|ncc; disparity_subpixel for sub-px
dR    = fs.disparity_map(left, right, reference="right"); ok = fs.lr_consistency(disp, dR)  # drop occlusions
Z     = fs.depth_from_disparity(disp, focal=f, baseline=B)      # Z = f*B/d (inf = unmatched)
pts   = fs.reproject_to_points(Z, fx=f, fy=f)                   # (N,3) camera-frame cloud
```

## Terrain (locomotion) — `terrain`
```python
grid, extent = fs.elevation_map(world_pts, cell=0.05)          # 2.5-D heightmap (z-up world frame)
ok    = fs.traversability(grid, cell=0.05, max_step=0.1, max_slope=0.6)
score = fs.foothold_score(grid, cell=0.05)                     # flatness in [0,1]
mask, obs = fs.detect_obstacles(grid, cell=0.05, clearance=0.12, extent=extent)  # ground='plane'(default)|'opening'
```

## Objects & posture — `detect`, `pose`
```python
objs  = fs.segment_objects(frame, threshold="otsu", min_area=20)   # area/centroid/bbox/hu/mask + perimeter/circularity/eccentricity
lab,_ = fs.nearest_prototype(fs.object_descriptor(objs[0]), prototypes)   # feature-based id (ML/DL = gap)
desc  = fs.pose_descriptor(mask)                    # [orient, elong, #ends, #joints, fill, aspect] from a silhouette
```

## 3-D registration & grasp — `pointcloud`, `registration`
```python
cloud = fs.remove_statistical_outliers(cloud)[0]; cloud = fs.voxel_downsample(cloud, 0.01)  # clean/thin
nrm   = fs.estimate_normals(cloud, k=16, viewpoint=(0,0,0))    # grasp approach directions
R,t,aln,rmse = fs.register(cloud, model)            # PCA start + trimmed ICP (large rotations, outliers)
R,t,aln,rmse = fs.point_to_plane_icp(cloud, model)  # tighter on surfaces (Low 2004)
R,t,aln,rmse = fs.feature_register(cloud, model)    # FPFH + RANSAC + ICP (ambiguous global axes)
```

## Metrology — `measure` (sub-pixel primitive fitting)
The measurement side HALCON does with `fit_*_contour_xld`: fit a geometric
primitive to a set of `(row, col)` points (e.g. an XLD edge contour) by classical
least squares and read back the parameters + an honest RMS residual.
```python
prof = fs.line_profile(img, (r0, c0), (r1, c1))     # bilinear intensity profile
c = fs.fit_circle(points)      # Kåsa/Coope algebraic fit -> {cy, cx, r, rms}
e = fs.fit_ellipse(points)     # Halir-Flusser 1998 direct fit -> {cy, cx, ra, rb, angle_deg, rms}
l = fs.fit_line(points)        # total-least-squares -> {cy, cx, dy, dx, angle_deg, rms}
r = fs.fit_rectangle2(points)  # min-area oriented box (rotating calipers) -> {cy, cx, l1, l2, angle_deg, rms}
```
Exact on noise-free points; robust under moderate noise; fail-closed (collinear /
< min points / non-finite raise `ValueError` rather than return a meaningless fit).

## Visualise / export — `imgio` (no matplotlib)
`colorize_depth` · `colorize_disparity` · `colorize_labels` · `colorize_flow` ·
`colorize_height` · `shaded_relief` · `apply_cmap(x, name)` (16 maps) ·
`overlay_mask` · `save`/`load` (cv2/Pillow) · `save_ply`.

## Interactive — Fullseye Studio
`py -3.11 studio.py` (or `fullseye-studio`): op pipeline + step exec + zoom/pan +
pseudo-colour/3-D surface + Inspector + **Perception (v14) panel** (frame B →
optical flow / motion overlay / stereo depth / stereo terrain).

## Templates
`examples/perception_pipeline.py` (stereo→depth→terrain) · `segment_and_classify.py` ·
`motion_analysis.py` (flow→motion) · `grasp_pose.py` (cloud→normals→register→6-DoF).

## Honest limits
Flow assumes brightness constancy (illumination change / occlusion show as error, not
a mask). `ground_plane` assumes planar ground; `ground='opening'` for rough terrain has
a ramp-border artefact. `pca_align` needs an anisotropic cloud; `feature_register`'s
FPFH is only approximately rotation-invariant (normal signs) and symmetric shapes stay
ambiguous. Object *identification* and *where-to-grasp* are feature/geometry only —
learned models are out of scope. Verified across three independent AI reviews (Claude
adversarial + Codex + Copilot); full test suite green. See `docs/V14.md` for details.
