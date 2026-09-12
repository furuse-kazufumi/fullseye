<!-- i18n-source-sha: e1b504a1e060 -->
# fullseye 3D op × op Combination Matrix (prioritized by feasibility × differentiation)

[日本語](./OP_COMBINATION_MATRIX.md) · **English**

**Core idea**: The 214 3D ops (the `ops3d.py` registry, 49 categories) can be chained whenever one op's output type matches another op's input type.
Type-consistent op→op chains number **5,246 (2-stage, measured via `ops3d.compatible()`)**, and grow **exponentially** at 3+ stages
(waves 2–5 added the 15 modules and 68 ops photometric/range_image/preprocess/structured_light/deform/medial/metrics/robust_fit/edges/
reconstruct/curve/shape_descriptor/freeform/pose_estimation/regionprops, nearly doubling from
82 ops/16 categories to 150 ops/31 categories). From this space we decide the order to tackle things by
**feasibility (F: 1–5) × differentiation (D: 1–5) = priority score**.

Scoring criteria:
- **F (feasibility)**: 5 = just chain existing ops / 4 = thin glue code / 3 = one medium-sized new op / 2 = heavy new implementation / 1 = research element.
- **D (differentiation)**: 5 = not in HALCON/OpenCV (especially GPU 3D · Physical AI · synthesis loops) / 3 = exists but we have a 3D/GPU edge / 1 = existing solutions suffice.
- **Status**: ✅ = verified pipeline already exists / ○ = ready as soon as glued / △ = new op required.

## Top priorities (descending F×D)

| # | op chain | What it does | F | D | Priority | Status |
|---|---|---|---|---|---|---|
| 1 | `mesh_to_points → register_fpfh → icp_point2plane` | **CAD mesh vs point-cloud scan alignment** (foundation of Physical AI) | 5 | 5 | 25 | ✅ fuse3d |
| 2 | `estimate_point_normals → compute_fpfh → register_fpfh → icp` | global registration of point clouds without an initial estimate (no-init 60°) | 4 | 5 | 20 | ✅ feat_fpfh |
| 3 | `signed_distance_field → match_shape_3d` | **SDF-based matching** (smooth, occlusion-robust; thin in cv2/HALCON) | 5 | 4 | 20 | ○ |
| 4 | `hough_plane_3d → distance_point_plane / surface_form_error` | **flatness/form-error metrology** (detect → measure) | 5 | 4 | 20 | ○ |
| 5 | `scene_flow_lk → deformation/distortion measurement` | **non-rigid / deformation tracking** (3D flow has few competitors) | 4 | 5 | 20 | ○ |
| 6 | `render_volume_projection / render_shaded → known GT` | **synthetic sample generation** (inspection training · 3D measurement sample space) | 5 | 4 | 20 | ✅ render |
| 7 | `render_volume_projection(xray=DRR) → match_shape_3d(2D)` | **X-ray/CT inspection matching** (industrial CT) | 4 | 4 | 16 | ○ |
| 8 | `curvature_maps → harris3d_keypoints` | **curvature-salient keypoints** (feature points robust to shape) | 4 | 4 | 16 | ○ |
| 9 | `reflect + render_shaded → inspection image` | **appearance-sample synthesis of mirror/specular surfaces** | 4 | 4 | 16 | ○ |
| 10 | `fit_zernike → descriptor matching` | **classification of wavefront/lens aberrations** (optical inspection) | 4 | 4 | 16 | ○ |
| 11 | `match_hough_3d(topk) → refine_peak_newton per instance` | **multi-instance detection → per-instance sub-voxel** | 4 | 4 | 16 | ○ |
| 12 | `fuse_to_voxel(depth×N multi-view) → register/match` | **multi-view fusion → integrated matching** | 4 | 4 | 16 | ✅ fuse3d |
| 13 | `tsdf_from_depth → voxel_to_mesh` | **RGB-D reconstruction** (KinectFusion family) | 5 | 3 | 15 | ○ |
| 14 | `polar_unwrap → match_shape_3d(2D)` | **rotationally symmetric body / ring inspection** (θ-unwrap to straighten) | 5 | 3 | 15 | ○ |
| 15 | `hough_sphere_3d → fit_sphere_3d → residual` | **sphericity / spherical-part measurement** | 5 | 3 | 15 | ○ |
| 16 | `refract → render` | **image-distortion synthesis of transparent bodies (glass/lens)** | 3 | 5 | 15 | ○ |
| 17 | `morph_tophat3d → harris3d / hough_3d` | **detection of tiny defects/protrusions** (surfaced by preprocessing) | 4 | 3 | 12 | ○ |
| 18 | `voxel_to_mesh → mesh_to_points → register_fpfh` | **voxel↔mesh heterogeneous registration** | 5 | 3 | 15 | ✅ fuse3d |
| 19 | `match_logpolar_z → refine_rotation_z` | rotation coarse→fine (±3°→0.01°) | 5 | 3 | 15 | ✅ coarse-fine |
| 20 | `edt_jfa → medial surface → topological matching` | **skeleton/medial matching** (topology-invariant) | 2 | 4 | 8 | △ TODO |
| 21 | `render_* + autograd → inverse problem` | **differentiable rendering** (inverse estimation of pose/shape · world-model learning) | 2 | 5 | 10 | △ TODO |

### New chains opened by waves 2–5 (15 modules added)

| # | op chain | What it does | F | D | Priority | Status |
|---|---|---|---|---|---|---|
| 22 | `photometric_stereo → integrate_normals → surface_form_error` | **multiple images under known illumination → normals → height field → form error** (specular/fine-relief inspection; closed-form through Frankot-Chellappa integration) | 5 | 4 | 20 | ○ (first 2 hops are ✅ test_photometric) |
| 23 | `depth_to_organized_points ⊕ normals_from_depth → compute_fpfh → register_fpfh` | **RGB-D-native sparse point-cloud global registration** (organized normals with a determined viewpoint sign + FPFH, directly connected to a depth camera) | 4 | 4 | 16 | ○ |
| 24 | `ransac_plane → distance_point_plane` | **outlier-robust flatness measurement** (discard outliers with RANSAC before measuring; more robust than match3d's least-squares fit) | 5 | 4 | 20 | ○ |
| 25 | `edge_points(edges3d) → [ordering] → curvature_torsion(curve3d)` | **3D edges → differential geometry of a curve** (reorder the seam/edge point sequence extracted by voxel Canny and measure the seam via curvature and torsion) | 3 | 5 | 15 | △ needs ordering glue |
| 26 | `poisson_lite(recon3d) → mesh_to_points(transform) → chamfer_distance(metrics3d)` | **quantify reconstruction quality by GT point-cloud comparison** (point cloud → approximate reconstruction mesh → chamfer; also reusable as the evaluation of evolutionary search) | 5 | 4 | 20 | ○ |
| 27 | `decode_fringe(structured_light) → depth_to_organized_points → fit_plane_3d → distance_point_plane` | **the full path of fringe-projection profilometry** (phase decoding → height → organized point cloud → plane fit → flatness; closes the loop for industrial 3D scan inspection) | 4 | 5 | 20 | ○ |
| 28 | `register_nonrigid(deform3d) → rmse_correspondence(metrics3d)` | **quantitatively evaluate the residual of non-rigid registration** (guarantee the deformation-tracking accuracy of TPS non-rigid ICP via GT point-cloud RMSE) | 5 | 5 | 25 | ○ |
| 29 | `pnp_ransac(pnp3d) → reprojection_error(pnp3d)` | **reprojection-error evaluation of PnP-RANSAC pose estimation** (pnp_ransac already computes this internally over its inlier set; also for external application to an arbitrary correspondence set or synthetic-GT validation) | 5 | 2 | 10 | ✅ pnp3d (already chained and computed internally) |
| 30 | `label_components(regionprops3d) → region_props(regionprops3d)` | **batch connected-component measurement of many objects** (volume/centroid/principal axes/sphericity; measure multiple parts simultaneously in CT/inspection) | 5 | 3 | 15 | ✅ regionprops3d |
| 31 | `medial_axis_points(medial) → icp_point2point_3d(match3d)` | **reduce to skeleton points, then coarse-align with ICP** (compress a dense voxel to sparse medial points; a topology-invariant lightweight pre-alignment) | 4 | 5 | 20 | ○ |
| 32 | `chamfer_distance / fscore / medial_match → fitness of op-chain search` | **the fitness foundation of evolutionary search** (use closed-form, GT-verified metrics directly as fitness; the basis of a convergence step that automatically explores the op-chain space with imgevolve's evolutionary loop) | 3 | 5 | 15 | ○ (requires wiring a 3D version into evolve.py) |
| 33 | `statistical_outlier_removal → voxel_grid_downsample → mls_smooth(pcl_filter) → poisson_lite(recon3d)` | **the practical point-cloud cleanup → reconstruction pipeline** (outlier removal → downsampling → MLS smoothing → Poisson approximation, turning a raw scan into an immediately usable mesh) | 5 | 3 | 15 | ○ |
| 34 | `dlt_pose / pnp_ransac(pnp3d) → pose_error(metrics3d)` (a known-pose synthetic-GT loop) | **validate pose-estimation accuracy with synthetic GT** (known pose → projection → PnP recovery → pose_error; a test basis for AR / hand-eye calibration) | 4 | 4 | 16 | ○ |
| 35 | `describe(descriptors3d) → shape_distance(descriptors3d)` | **retrieval/classification with statistical shape descriptors** (rotation- and scale-invariant; needs no meshing or normal estimation and is robust to sparse/incomplete point clouds) | 5 | 3 | 15 | ✅ descriptors3d (chain verified in test_rotation_invariance_describe) |
| 36 | `fit_bspline_surface(bspline_surf) → surface_residual(bspline_surf)` | **measure the deviation of free-form surfaces beyond polynomials** (B-spline fit → residual; free-form inspection beyond flatness/sphericity) | 5 | 4 | 20 | ✅ bspline_surf |

### New chains opened by wave 6 (6 modules added)

| # | op chain | What it does | F | D | Priority | Status |
|---|---|---|---|---|---|---|
| 37 | `recover_pose(twoview) → triangulate → poisson_lite(recon3d)` | **minimal monocular SfM pipeline** (2-view correspondences → relative pose + sparse point cloud → surface reconstruction) | 4 | 4 | 16 | ○ |
| 38 | `recover_pose(twoview) → pose_error(metrics3d)` | **validate relative-pose accuracy with synthetic GT** (a basis for VO/AR/hand-eye, disambiguated by cheirality) | 5 | 3 | 15 | ○ |
| 39 | `principal_curvatures / shape_index(curvature3d) → grasp-affordance classification by convex/concave/saddle` | **grasp-point selection by curvature** (shape index is +1 for a sphere, +0.5 for a cylinder, 0 for a saddle; Physical AI grasp) | 5 | 5 | 25 | △ needs grasp-point classification |
| 40 | `gaussian_curvature(curvature3d) → curvature-anomaly threshold → surface-defect detection` | **curvature-based defect inspection** (surface dents/protrusions via anomalies of local K/H) | 4 | 4 | 16 | △ needs threshold |
| 41 | `moment_invariants(moments3d) → shape_distance(descriptors3d)` | **rotation/scale-invariant shape retrieval** (needs no meshing or normal estimation; robust to sparse/missing) | 5 | 3 | 15 | ○ |
| 42 | `geodesic_distances(geodesic3d) → along-surface distance measurement` | **on-surface metrology** (distance along the surface rather than straight-line; not in HALCON/OpenCV) | 5 | 5 | 25 | ○ |
| 43 | `farthest_point_sampling(geodesic3d) → shot_descriptor / compute_fpfh` | **make descriptor computation efficient via geodesically uniform sampling** (dense cloud → representative points) | 4 | 4 | 16 | ○ |
| 44 | `synthesize_silhouette(visualhull)×N → carve → voxel_to_mesh(transform)` | **multi-view silhouettes → visual hull → mesh** (silhouette reconstruction that also works on textureless/transparent bodies) | 4 | 4 | 16 | ○ |
| 45 | `carve(visualhull) → voxel_iou / chamfer_distance(metrics3d)` | **quantify visual-hull reconstruction quality** (also for evaluating the coverage of camera placement) | 5 | 3 | 15 | ○ |
| 46 | `fit_superquadric(superquadric) → single-primitive grasp planning` | **approximate an object with a single superquadric → grasp** (continuously represents box–sphere–cylinder via ε; Physical AI grasp affordance) | 5 | 5 | 25 | △ needs grasp planning |

### New chains opened by wave 7 (5 modules added)

| # | op chain | What it does | F | D | Priority | Status |
|---|---|---|---|---|---|---|
| 47 | `recover_pose(twoview) → bundle_adjust(bundle3d)` | **N-view SfM** (initialize with 2 views → N-view bundle adjustment to minimize reprojection over all poses + structure) | 4 | 4 | 16 | ○ |
| 48 | `fuse(tsdf_fusion) → extract_surface_points → chamfer_distance(metrics3d)` | **RGB-D multi-frame fusion → surface → quality evaluation** (closes the KinectFusion path into a loop) | 4 | 4 | 16 | ○ |
| 49 | `depth_to_organized_points → estimate_covariances → gicp` | **plane-to-plane precise alignment of RGB-D point clouds** (superior to ICP on planar/noisy clouds) | 4 | 4 | 16 | ○ |
| 50 | `augment(pcl_augment) → point-cloud training-data augmentation` | **preprocessing for Physical AI point-cloud learning** (generalization via rotation/dropout/elastic/cutout, deterministic seed) | 5 | 4 | 20 | ○ |
| 51 | `plane_segmentation / region_growing(segment3d) → region_props(regionprops3d)` | **scene segmentation → per-segment measurement** (separate ground/wall/object and measure each individually) | 5 | 4 | 20 | ○ |
| 52 | `euclidean_cluster(segment3d) → fit_superquadric(superquadric) per cluster` | **multi-object scene → approximate each object with a superquadric** (extract grasp primitives) | 4 | 5 | 20 | △ needs cluster→fit connection |

### New chains opened by waves 8–9 (7 modules added) (SLAM/perception/symmetry/LiDAR/dynamic)

| # | op chain | What it does | F | D | Priority | Status |
|---|---|---|---|---|---|---|
| 53 | `recover_pose(twoview)×N → optimize_pose_graph(pose_graph)` | **SLAM trajectory optimization** (loop-close and correct 2-view relative poses with a pose graph, front-end → back-end) | 4 | 4 | 16 | ○ |
| 54 | `estimate_oriented_normals(normals_orient) → shape_index(curvature3d)` | **oriented normals → correct concave/convex judgment** (resolves the conceptual defect of curvature3d found in the wave7 audit) | 5 | 5 | 25 | ○ |
| 55 | `project_spherical(spherical_proj) → 2D inspection/CNN` | **turn a LiDAR point cloud into a spherical range image** (omnidirectional; bridges established 2D methods to 3D LiDAR) | 5 | 4 | 20 | ○ |
| 56 | `segment_rigid_motions(motion_seg3d) → fit_superquadric(superquadric) per rigid body` | **dynamic scene → rigid-body separation → object approximation** (turn each moving object into a grasp primitive) | 4 | 5 | 20 | △ needs connection |
| 57 | `occupancy_grid → esdf → inflate(occupancy)` | **point cloud → ESDF → path planning with a safety margin** (the distance-field foundation of robot navigation) | 5 | 4 | 20 | ○ |
| 58 | `detect_reflection_symmetry(symmetry3d) → fill missing side via reflect_points` | **mirror-complete a one-sided defect via symmetry** (fill the hidden face of a scan using symmetry) | 4 | 5 | 20 | △ needs connection |
| 59 | `fuse(tsdf_fusion) → occupancy_grid → esdf(occupancy)` | **multi-frame fusion → occupancy → distance field** (closes the loop of SLAM map + planning) | 4 | 4 | 16 | ○ |

## Inter-category linkage (which output → which input is common; top type-consistent pairs)
`geometry→geometry` (55, the chain of measurement) / `transform→*` (structural transformation is the entry point of every op) / `morphology→match_localize` (preprocessing → matching) /
`transform→feature_register` (point-cloud conversion → sparse registration). → **transform (the transformation graph) is the hub of all linkage**, geometry is the terminal of measurement.

**Linkage patterns added by waves 2–5 (15 modules)**: **metrics is a new evaluation terminal** (it receives points/voxel/normals/pose,
converges to measurement, and chamfer/fscore/medial_match can be reused directly as the fitness of evolutionary search).
**reconstruct/photometric/structured_light are new entry points to depth/points** (point-cloud-only reconstruction,
photometric stereo from multiple lights under one view, and the 3 paths of fringe-projection profilometry each independently
merge into the transform hub, increasing the sources of depth/points/mesh).

## Operations (how to proceed going forward)
1. Machine-enumerate successor candidates with `ops3d.compatible(name)` → score F/D by the criteria of the table above → tackle in priority order.
2. **Harvest the ○ (ready as soon as glued) items first** (the F5×D4 group = #3, 4, 6, etc.). For △ (new op required), select those with high differentiation (#21).
3. Each time you add an op, register it in `ops3d._CATALOG` → the combination space widens automatically (exponential candidates grow).
4. Split code review/validation into several passes (a full re-check of all ops is planned after a Fable reset).

## Current op inventory (`ops3d.py`, 214 ops / 49 categories, measured via `py -3.11 ops3d.py`)
geometry 15 / transform 12 / feature_register 7 / metrics 7 / augment 6 / match_localize 6 / refine 6 /
morphology 5 / optics 5 / structured_light 5 / medial 5 / edges 5 / curve 5 / shape_descriptor 5 / freeform 5 /
two_view 5 / curvature 5 /
feature 4 / match_pose 4 / render 4 / surface_fit 4 / photometric 4 / range_image 4 / preprocess 4 /
deform 4 / robust_fit 4 / reconstruct 4 / regionprops 4 / moment_invariant 4 / geodesic 4 / superquadric 4 /
occupancy 4 / symmetry 4 /
curvilinear 3 / pose_estimation 3 / space_carving 3 / bundle_adjust 3 / tsdf_fusion 3 / segment 3 /
pose_graph 3 / scene_flow3d 3 / lidar_projection 3 / motion_segment 3 /
detect 2 / describe 2 / fusion 2 / gicp 2 / normals_orient 2 / motion 1.

**The 15 new categories · 68 ops of waves 2–5**: photometric (photometric stereo · normal integration) / range_image (organized
depth image) / preprocess (point-cloud filters) / structured_light (fringe-projection profilometry) / deform (3D non-rigid registration) /
medial (medial surface · 3D skeleton) / metrics (evaluation metrics for reconstruction/registration, the foundation of evolutionary-search fitness) / robust_fit (RANSAC
robust primitive fitting) / edges (3D edge extraction) / reconstruct (direct surface reconstruction from point clouds) / curve (differential geometry of space curves) /
shape_descriptor (statistics-based global shape descriptors) / freeform (B-spline free-form surfaces · curves) / pose_estimation (PnP) /
regionprops (3D connected components · multi-object measurement).
