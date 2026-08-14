# Physical-AI perception pipeline (fullseye / imgevolve, v18.3, 2026-08-15)

The perception substrate for physical-AI projects (onocollo / evis / hillco):
turn images and depth into the 3-D quantities a robot acts on. Two end-to-end
chains, both numpy/scipy-native, classical (no learned model), ground-truth tested:

```
MANIPULATION:  image ─▶ (stereo) depth ─▶ point cloud ─▶ segment objects ─▶
               6-DoF object pose ─▶ grasp
LOCOMOTION:    depth ─▶ cloud + normals ─▶ elevation map ─▶ slope / foothold ─▶
               support polygon + static-stability margin
NAVIGATION:    optical flow ─▶ heading (FoE) + time-to-contact + 3-D scene flow
ODOMETRY:      RGB-D pair ─▶ frame-to-frame camera motion ─▶ integrated trajectory
PLANNING:      cloud ─▶ 2-D occupancy grid ─▶ inflate + clearance ─▶ line-of-sight / frontier
```

Runnable template: [`examples/physical_ai_perception.py`](../examples/physical_ai_perception.py)
(manipulation + locomotion + ego-motion, each a composition smoke test).

Everything below is under the `fullseye` facade (`import fullseye as fs`). Frames are
numpy `float64`. Provenance is public literature only — in public articles present
these as an in-house library, never a commercial product name.

## Modules & references

| module | role | key functions | reference |
|---|---|---|---|
| `camera` | 2-D↔3-D backbone | `intrinsic_matrix` `project_points` `backproject` `depth_to_points` `normals_from_depth` `triangulate` `solve_pnp` `fundamental_matrix` `essential_matrix` `recover_pose` `undistort_points` `stereo_rectify` `rodrigues` | Hartley & Zisserman 2004; Brown 1971; Fusiello 2000 |
| `stereo` | dense/robust depth | `disparity_census` `disparity_sgm` `disparity_confidence` `speckle_filter` `fill_disparity` `census_transform` (+ v14 `disparity_map`/`_subpixel`/`lr_consistency`/`depth_from_disparity`) | Zabih & Woodfill 1994; Hirschmüller 2005/2008; Scharstein & Szeliski 2002 |
| `pcseg` | point-cloud carving | `fit_plane/sphere/cylinder_ransac` `remove_ground` `euclidean_clusters` `region_growing` `obb` `aabb` `crop_box/sphere` `farthest_point_sampling` `curvature` `height_above_plane` `principal_axes` | Fischler & Bolles 1981; Rusu 2009; Rabbani 2006; Pauly 2002; Eldar 1994 |
| `ppf` | 6-DoF object pose | `ppf_model` `surface_match` `find_surface_pose` | Drost et al. 2010 |
| `registration` | rigid alignment (ICP) | `kabsch` `icp` `point_to_plane_icp` `pca_align` `register` `feature_register` | Besl & McKay 1992; Low 2004; Rusu 2009 (FPFH) |
| `terrain` | 2.5-D heightmap | `elevation_map` `fuse_elevation` `traversability` `slope_map` `roughness_map` `surface_normals` `step_edges` `foothold_score` `foothold_candidates` `ground_plane` `detect_obstacles` | standard robot-centric elevation mapping |
| `locomotion` | balance / gait | `contact_points` `support_polygon` `com_support_margin` `com_from_silhouette` `gait_phase` | McGhee & Frank 1968; Alexander 1984 |
| `sceneflow` | ego-motion / 3-D motion | `flow_divergence` `flow_curl` `focus_of_expansion` `time_to_contact` `looming` `ego_translation_from_flow` `scene_flow` | Longuet-Higgins & Prazdny 1980; Lee 1976; Vedula 1999 |
| `features` | sparse keypoint matching | `harris_corners` `fast_corners` `describe_patches` `match_descriptors` `match_keypoints` | Harris & Stephens 1988; Rosten & Drummond 2006; Lowe 2004 |
| `odometry` | self-localization | `rgbd_odometry` `pnp_odometry` `integrate_trajectory` `umeyama_align` `trajectory_error` | Arun 1987; Umeyama 1991; Fischler & Bolles 1981 |
| `occupancy` | navigation grid | `occupancy_grid_2d` `inflate_obstacles` `clearance_map` `line_of_sight` `frontier_cells` | Elfes 1989; Lozano-Pérez 1979; Yamauchi 1997 |
| `pose` | silhouette posture | `pose_descriptor` `skeleton_nodes` `principal_axis` | — |
| `pointcloud` | cloud primitives | `estimate_normals` `voxel_downsample` `remove_statistical_outliers` `remove_radius_outliers` `fpfh` | Hoppe 1992; Rusu 2009 |
| `grasp` | antipodal grasp | `grasps_from_mesh` `force_closure` `ferrari_canny_quality` `rank_grasps` | Nguyen 1988; Ferrari & Canny 1992 |

## Conventions

- **Camera frame** (`camera`): +z forward, +u right, +v down (OpenCV). `X_cam = R @ X_world + t`; `P = K @ [R|t]`.
- **World/ground frame** (`terrain` / `locomotion`): x, y span the ground, z is up.
- **Optical flow** (`flow` / `sceneflow`): a feature at `(x, y)` moves to `(x+u, y+v)`; `u`, `v` are `(H, W)` arrays.
- **Pose** `(R, t)` from `solve_pnp` / `ppf`: maps the model/object into the camera/scene frame.

## Where each project plugs in

- **evis** stereo vision → `stereo_rectify` (if uncalibrated pair) → `disparity_sgm` →
  `depth_to_points` + `normals_from_depth` → `pcseg.remove_ground`/`euclidean_clusters`
  → `ppf.find_surface_pose` (object 6-DoF) → grasp.
- **hillco / onocollo** walking → depth → `terrain.elevation_map`/`fuse_elevation` →
  `slope_map` / `step_edges` / `foothold_candidates` → `locomotion.support_polygon` +
  `com_support_margin` (is the COM over the feet?) + `gait_phase`.
- **onocollo** physics videos → `flow.optical_flow_lk` → `sceneflow.time_to_contact` /
  `looming` / `scene_flow` (did it approach, and how fast in 3-D?).

## Honest limits

- Classical methods only — no learned detector/segmenter (feature-based recognition
  via `detect`/`ppf`, not deep learning; that stays a future capability).
- `disparity_*` assume a **rectified** pair; use `camera.stereo_rectify` first for a
  calibrated-but-unrectified rig.
- `ppf` needs surface **normal variation** to be discriminative (a flat/rotationally
  symmetric object has an ambiguous pose); it hands off to ICP for the fine fit.
- `sceneflow` heading/TTC assume dominant **translation** (rotation not decoupled).
- These are `fullseye` **facade modules**, not evolvable REGISTRY operators — they do
  not participate in the pipeline-evolution engine (by design; they are measurement
  code, not single image→image ops).
