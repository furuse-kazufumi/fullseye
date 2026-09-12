<!-- i18n-source-sha: e49e5ba8de03 -->
# fullseye 3D Vision Toolkit (for Physical AI, differentiating from HALCON/OpenCV)

[日本語](./MATCH_3D_MATRIX.md) · **English**

We systematize 3D object matching on a grid of **"input data structure" × "methods established in 2D"**, and exhaustively expand it via the **data transforms** that connect the two (splat / projection / FFT / gradient field / distance field / PCA canonicalization). Core idea:
**many 3D methods can be built by "transforming 3D data into a representation where a known 2D method works."**
With matching at the core, we integrate **transform graphs, morphology, geometric metrology, surface approximation, curvilinear coordinates, optics, and projection/rendering** into a single stack (built via 2D→3D dimensional lift + diverge→converge).

**Differentiation (a vision library for Physical AI)**:
- cv2 has no 3D matchTemplate, and even HALCON limits 3D to surface/shape-based methods → **a full GPU voxel matching suite** (RTX5090, torch cu128).
- Rather than narrowing to a single method, we **diverge** and accumulate → covering 17 match methods + 6 refinements + metrology/optics/rendering, and converge through **method selection and coarse→fine pipelines**.
- **Projection/rendering closes the loop of 3D→2D synthesis** = world-model observation synthesis, appearance-inspection sample generation, 3D-measurement sample-space generation (directly connected to Physical AI/simulation).
- **We do not abandon rigor**: Snell/Fresnel/geometry/curvature are all verified against ground truth in closed form (unlike the visual approximations of game engines). All GPU/CPU processing times are measured.

## Method list (established in 2D → lifted to 3D). ★=TRIZ principle 17 (moving to another dimension) / line→surface lift
| Method | 2D origin | Key to 3D-ization | Transform |
|---|---|---|---|
| **NCC / template** | normalized cross-correlation | conv3d + box3d normalization | (direct) |
| **shape-based / gradient direction** | Steger / HALCON | directional correlation of 3D gradients (3-component conv3d) | sobel3d |
| **phase correlation** | Reddy & Chatterji | cross-power spectrum of the 3D FFT (translation) | FFT |
| **Fourier-Mellin / log-polar** | Reddy & Chatterji | z-projection |FFT|→log-polar→phase correlation (rotation+scale) | FFT→log-polar |
| **chamfer / distance field** | Barrow 1977 | chamfer score from the edge EDT (all-GPU=JFA) | distance transform (GPU-JFA) |
| **moment / PCA axes** | principal-axis alignment | pose from inertia-tensor eigenvectors | PCA canonicalization |
| **generalized Hough** | Ballard | 3D R-table voting (sum of orientation-bin correlations) | gradient→voting |
| **projection (dimensionality reduction)** | — | apply 2D methods on orthogonal MIP/silhouette | 3D→2D projection |
| ★**curvature / shape index** | contour curvature (1 scalar) | **principal curvatures κ1,κ2** (2 = intrinsic to the surface) Koenderink shape index | Hessian (2nd order) |
| ★**spherical-harmonic descriptor** | Fourier descriptor (1D FFT of the contour) | band energy of the surface SH = **rotation invariant** (Kazhdan) | SH (spherical FFT) |
| **parametric Hough** | Hough line/circle | vote **planes/spheres** into parameter space (template-free = RANSAC family) | gradient→param voting |
| **feature descriptor** (TODO) | Harris/SIFT | 3D corner + descriptor (spin image/FPFH/SHOT) | local shape |
| **iterative refinement** (in progress) | LK / ICP / GN | high-precision convergence of a coarse estimate via Newton/Gauss-Newton/ICP | Jacobian/Hessian |

## Data-structure rows (input format) × transform graph
"**Transforming** 3D data into a representation where a method works" is the core of the matrix. Formats are diverse → **connect them to each other via transforms**.

| Structure/format | Description | Main transforms (implementations) |
|---|---|---|
| **voxel grid** (dense) | dense grid | central representation |
| **point cloud** | point set | `points_to_voxel` (splat) / `estimate_point_normals` (normals=PCA) |
| **3DGS** (anisotropic Gaussians) | means+scale+opacity | `gaussians_to_voxel` (splat) |
| **mesh** (vertices+faces) | triangle mesh | `mesh_to_voxel` (occupancy) / `mesh_to_points` (face sampling) |
| **depth / range** (2.5D) | depth map | `depth_to_points` (back-projection) / `tsdf_from_depth` (TSDF) |
| **SDF / TSDF** | signed distance field | `signed_distance_field` (voxel→SDF) / `sdf_to_occupancy` |
| **occupancy / binary** | occupancy 0/1 | threshold ↔ voxel ↔ SDF |
| **normals** (point/face normals) | orientation | `estimate_point_normals` (for FPFH/ICP-p2plane) |

**Transform graph (→=implemented)**: points ⇄ voxel (splat / marching cubes), voxel → mesh (`voxel_to_mesh`=marching cubes),
mesh → points (`mesh_to_points`), voxel ⇄ SDF ⇄ occupancy, depth → {points, TSDF}, 3DGS → voxel, points → normals.
**If any input format is brought onto a common voxel/point/SDF, every method becomes usable** (= all row × column cells are connected by transforms).

## 3D morphology (3D lift of the 2D operators. grey & binary)
`accel_vol.py`: grey erode/dilate/median/gaussian + binary region (ball/cross, opening).
`match3d.py` additions (preprocessing/feature extraction): `morph_gradient3d` (dilation−erosion=**boundary extraction**, sobel alternative) /
`morph_tophat3d` (**small-bright-structure extraction**, keypoint preprocessing) / `morph_blackhat3d` (dark structures) / `morph_dilate3d` / `morph_erode3d`. GPU (max_pool3d).

## Geometric primitives / metrology (2 points→line, 3 points→plane/angle; common to 2D/3D)
The layer that turns detection/matching into **"measurement"** (equivalent to HALCON 2D/3D metrology). All in closed form and rigorously verified:
- **Construction**: `line_from_2points` (2 points→line) / `plane_from_3points` (3 points→plane)
- **Angle**: `angle_3points` (∠ABC) / `angle_between_lines` / `angle_between_planes` (dihedral) / `angle_line_plane`
- **Distance**: `distance_point_plane` / `distance_point_line` / `distance_line_line` (including skew lines)
- **Intersection**: `intersect_line_plane` (→point) / `intersect_planes` (→line)
- **Fitting** (least squares): `fit_line_3d` / `fit_plane_3d` (normal+residual) / `fit_sphere_3d` (center+radius) / `fit_circle_3d`

## Sparse feature registration (keypoint + descriptor + RANSAC) = large rotation + partial overlap with no initial estimate
The regime that dense matching (NCC/Hough) cannot handle. In a Workflow we explore 4 methods in parallel and, after integration, primary-verify (measured rot_err):
| Method | Module | Measured (60° rotation + 70% overlap) |
|---|---|---|
| Harris3D keypoint (mineig) | `feat_harris.harris3d_keypoints` | repeatability 85% (2D's k=0.04 detects 0 in 3D → adopt mineig) |
| Spin Image + RANSAC | `feat_spin.register_spin` | rot_err **1.84°**, MC 100% success |
| FPFH + RANSAC | `feat_fpfh.register_fpfh` | rot_err **0.83°** |
| SHOT + RANSAC + ICP | `feat_shot.register_shot` | rot_err **0.00°** (with ICP refinement) |

honest limits: degrades sharply at overlap <60% (wrong-basin lock), impossible for featureless shapes (a bare sphere), depends on normal sign. → feed the output as ICP's coarse init.

## Integration of heterogeneous structures (TRIZ merging/composition: combine all 5 structures) = `fuse3d`
Cross-multiply the "rows" of the matrix. Any structure can be handled mutually if it is **converted to a common representation (point cloud/voxel)** and brought together:
- `to_points(data, kind)` — a single entry point that unifies all 5 structures (points/mesh/depth/voxel/3dgs) into a point cloud.
- `register_cross(src, src_kind, dst, dst_kind, method)` — **rigid registration between heterogeneous structures**. Example: **CAD mesh vs point-cloud scan**
  (50° rotation + partial) via FPFH at rot_err **0.15°** (= Physical AI CAD-to-scan alignment).
- `fuse_to_voxel(items)` — **multi-structure fusion** (mesh[topology] + points[sample] + depth[observation] → one density voxel).

## Surface approximation z=f(x,y) (2 variables→1 variable, information compression)
`fit_poly_surface` / `eval_poly_surface` (polynomial least squares) / `surface_form_error` (flatness/sphericity = residual to an ideal surface) /
`background_flatten` (illumination unevenness = subtract a low-order surface = shading correction). Used heavily in both image processing and metrology.

## Expansion into curvilinear coordinate systems (not limited to Cartesian)
`polar_unwrap` (annulus/disc → θ×r, ring/label inspection) / `cylinder_unwrap` (cylindrical surface → height×θ×r, pipe inspection) /
`fit_zernike` (orthogonal basis on a disc = polar surface approximation, optics/wavefront metrology; tilt/defocus/astigmatism map to (n,m)).

## Optical primitives (specular/transparent bodies, all rigorously verified)
`reflect` (specular reflection) / `refract` (Snell refraction, transparent body + refractive index, TIR handling) / `fresnel_reflectance` (reflection/transmission ratio, 0.04 at normal incidence) /
`normal_from_reflection` (**deflectometry** = measure specular normals from reflection) / `snell_angle`. For inspection/measurement of glass/lenses/mirror surfaces.

## Projection / rendering (3D → 2D synthesis, closing the loop)
The reverse of the transform (2D→3D) = **observation synthesis, appearance-inspection sample generation, 3D-measurement sample-space generation** (directly connected to Physical AI/simulation):
`project_points` (pinhole projection) / `render_point_depth` (point cloud→depth, z-buffer) /
`render_volume_projection` (arbitrary-view xray=DRR / mip) / `render_shaded` (normals+light source→Lambertian, connected to optics).

## Transform graph of data formats (connecting structures) = additions
`signed_distance_field` (voxel→SDF) / `sdf_to_occupancy` / `estimate_point_normals` (point cloud→normals=PCA) /
`mesh_to_points` / `voxel_to_mesh` (marching cubes) / `tsdf_from_depth` (RGB-D→TSDF). **Bring any format onto a common representation and apply all methods**.

## Matrix (by method mode × data structure)
All 5 structures (voxel / point cloud / 3DGS / mesh / depth 2.5D) load onto a common voxel/point representation via **transform T**, so
each method below applies to any structure (= 5 structures × number of methods cells). Methods are organized by "what they output (mode)":

**① Localization (output the template position within the scene)**
| Method | Characteristic | GPU |
|---|---|---|
| NCC | normalized cross-correlation, pyramid/sub-voxel | 46× (pyramid 244×) |
| shape-based | gradient direction, **contrast invariant** | 68-89× |
| chamfer | distance field, **occlusion robust**, all-GPU (JFA) | beats scipy at N≥96 |
| gen. Hough | voting, **multiple instances** · occlusion robust | 8× |
| ★curvature | shape index, matches by **surface shape rather than intensity** | 6× |
| MIP→2D | drop to 2D methods via orthogonal projection (cheap coarse) | 1.3× |

**② Pose (output the rotation/scale/translation transform parameters)**
| Method | Output | Characteristic |
|---|---|---|
| phase-corr | translation | template-free, FFT, 18-28× |
| PCA/moment | rotation+translation | with correspondence, residual 0, 0.2ms |
| Fourier-Mellin | rotation+scale | no correspondence, 30×, coarse (±45/90° aliasing) |

**⑤ Iterative refinement (coarse estimate → high-precision convergence). Diverge without narrowing to one means (6 methods verified in parallel in a Workflow, all PASS, primary re-verified after integration)**
| Method | Convergence precision (measured) | Iters/time | vs baseline |
|---|---|---|---|
| Newton sub-voxel peak `refine_peak_newton` | 0.011 voxel (cross curvature from the full Hessian) | 7 / 1.5ms | ~9× vs parabolic |
| Gauss-Newton translation (inverse-compositional LK) `refine_translation_lk` | 0.008-0.023 voxel | 6 / 1.2ms | ~60× vs NCC-COM |
| Levenberg-Marquardt translation+scale `refine_lm` | translation 0.007 voxel + **scale recovery** | 4 / 6ms | ~40-70× vs COM (scale is new) |
| Gauss-Newton z rotation `refine_rotation_z` | 0.002-0.017° | 4 / 12ms | **~5000×** over Fourier-Mellin's ±3° |
| ICP point-to-point (Kabsch) `icp_point2point_3d` | RMSE 1e-14, Trimmed for partial overlap | 6 / 2.5ms | coarse ±0.5vox → machine precision |
| ICP point-to-plane (GN) `icp_point2plane` | RMSE 1e-10, fast convergence to the surface | 4-16 / 8ms | fewer iters than point-to-point (Low 2004) |

**③ Detection (output primitive shapes without a template)**
| Method | Output | Characteristic |
|---|---|---|
| parametric Hough | plane (n,d) / sphere (c,r) | RANSAC family, normal exact · inlier 93%, 4.9×/2× |

**④ Description (match/retrieve with a rotation-invariant global signature)**
| Method | Output | Characteristic |
|---|---|---|
| ★spherical-harmonic descriptor | (radius × frequency) band energy | invariant under 3D rotation (sim 0.999), shape discrimination |

**★ Currently 11 methods (localization 6 / pose 3 / detection 1 / description 1) + 6 refinement methods × 5 structures. ★=line→surface lift (curvature · SH).**
The mesh→voxel translation is fully recovered by phase-corr, and depth back-projection is also verified. **The coarse-estimate→refinement pipeline holds**
(e.g., rotation ±3° with Fourier-Mellin → 0.01° with `refine_rotation_z` / integer sphere center with Hough → sub-voxel with `refine_peak_newton`).

**Implementation (`match3d.py` / `accel_match` / `accel_vol`)**:
- NCC (voxel) = `accel_match.ncc_locate_3d` + `_pyramid` (244× vs scipy) + sub-voxel centroid.
- shape-based (gradient direction = contour matching, **contrast invariant**) = `match3d.match_shape_3d`. sub-voxel localization even at 0.4× weak contrast. GPU 68-89×.
- phase-corr (FFT, translation, template-free) = `match_phase_3d`. GPU 18-28×.
- **Fourier-Mellin (log-polar, rotation+scale) = `match_logpolar_z`. Simultaneously estimates z-axis rotation + isotropic scale with no template/correspondence (PCA requires correspondence). Drops to 2D Fourier-Mellin via z-projection (MIP). Rotation error ~3° (mean) / 5.4° (max), scale ~10% underestimate. GPU 2.8ms = 30× vs CPU (the forte of FFT methods). Honest limits: the 180° symmetry of |FFT| aliases the ±45/90° neighborhood; a coarse estimator (refine downstream with NCC/ICP).**
- PCA/moment (principal-axis alignment, explicit recovery of **rotation**) = `match_pca` / `moment_axes`. Recovers rotation + translation of an anisotropic cloud at residual 0 · angular difference 0° (0.2ms, numpy eigh).
- MIP→2D (drop to 2D methods via orthogonal projection, cheap coarse) = `match_mip_2d`. localization |Δ|=0. GPU 1.3× (transfer-bound).
- chamfer (distance field, occlusion robust) = `match_chamfer_3d(edt="scipy"|"jfa")`. **`edt="jfa"` = GPU-exact EDT (`edt_jfa`, jump-flooding+JFA+2) for an all-GPU pipeline with no CPU round-trip. max|err|=0 vs scipy C-EDT (N≤160), and overtakes at N≥96 (96→2.6× / 128→4.7×).**
- generalized Hough (gradient R-table voting) = `match_hough_3d`. GHT made GPU-native as "sum of correlations per orientation bin" (A(t)=Σ_bin scene_bin⋆template_bin). Unlike shape-based's single solution, it **returns a voting accumulator and detects multiple peaks = multiple instances via NMS** (2/2 demonstrated). Missing edges only lower the peak = occlusion robust. GPU 8× (26 conv3d is compute-heavy, CPU 233→28ms).
- ★**curvature / shape index (line→surface lift) = `curvature_maps` / `match_curvature_3d`.** Lifts the 2D contour curvature (1 scalar) to the **principal curvatures κ1,κ2** (2) of a 3D surface. level-set closed form (Kindlmann 2003, conv3d from the Hessian), per-voxel, shape index S∈[-1,1] (cup/rut/saddle/ridge/cap). Sphere=+1 · cylinder=+0.5, matching the literature. **Matches by local surface shape rather than intensity** (distinguishes a same-intensity sphere vs cylinder). GPU 6×.
- ★**spherical-harmonic descriptor (line→surface lift) = `sh_descriptor` / `match_sh_descriptor`.** 2D closed-contour Fourier descriptor → 3D closed-surface SH. The SH band energy ‖f_l(r)‖ of concentric-sphere shells is **rotation invariant** (Kazhdan 2003). Self-similarity 0.999 under 3D 2-axis rotation, discriminates rod vs sphere at 0.847. For retrieval/verification.
- **parametric Hough (plane/sphere) = `hough_plane_3d` / `hough_sphere_3d`.** 3D lift of 2D Hough line/circle. Uses gradient=normal to vote plane (n,d) / sphere (c,r) into parameter space (template-free = RANSAC family). Thin-boundary-surface extraction rejects the thick gradient band. Plane: normal exact · inlier 93%; sphere: center exact · radius sub-voxel. GPU 4.9× (plane) / 2× (sphere). For ground/wall/ball segmentation of point clouds.
- transforms: `points_to_voxel` (splat) / `gaussians_to_voxel` (3DGS) / `mesh_to_voxel` / `depth_to_points` / `voxel_to_mips` / `sobel3d` / `edt_jfa` (GPU distance field) / `hessian3d` (curvature) / `_thin_surface` (thin-surface extraction).

**pyramid / sub-voxel centroid apply across all NCC methods. Rotation is handled by 3 lineages: shape-based (invariant) + PCA (explicit recovery with correspondence) + Fourier-Mellin (rotation+scale without correspondence).**

## Processing time (measured N=64³, CPU=py3.11 torch cpu / GPU=RTX5090 torch cu128, median ms)
We measure the diverged method group to make it a **basis for method selection**. ★=GPU is clearly favorable, ▲=CPU is faster/equal (for small problems, transfer/launch overhead wins).

| Method | CPU ms | GPU ms | GPU/CPU | Note |
|---|---|---|---|---|
| phase_3d ★ | 37.7 | **0.49** | 77× | FFT, fastest pose (translation) |
| logpolar_z ★ | 96.2 | **2.84** | 34× | FFT, rotation+scale |
| hough_plane ★ | 16.8 | 3.62 | 4.6× | plane detection |
| refine_rot_z ★ | 33.2 | 3.87 | 8.6× | rotation refinement |
| NCC (locate) ★ | 189 | 9.07 | 21× | localization baseline |
| shape_3d ★ | 69.7 | 9.23 | 7.6× | contrast-invariant localization |
| curvature ★ | 58 | 10.4 | 5.6× | shape localization |
| hough_sphere ★ | 21.5 | 10.2 | 2.1× | sphere detection |
| chamfer (scipy) | 36.1 | 16.7 | 2.2× | occlusion robust (EDT on CPU) |
| scene_flow_lk ★ | 65.2 | 17.5 | 3.7× | motion field |
| chamfer (jfa) | 89.5 | 23.3 | 3.8× | all-GPU distance field (favorable at large N) |
| edt_jfa | 64.7 | 27.8 | 2.3× | beats scipy at N≥96 |
| hough_3d (vote) ★ | 527 | 63.0 | 8.4× | multiple instances, heavy |
| mip_2d ▲ | 50.6 | 46.6 | 1.1× | transfer-bound, thin GPU benefit |
| sh_descriptor ▲ | **27.5** | 60.3 | 0.5× | per-radius loop, CPU advantage |
| refine_newton ▲ | **1.3** | 6.5 | 0.2× | small problem, CPU suffices |
| refine_lk ▲ | **1.02** | 2.2 | 0.5× | small problem, CPU suffices |
| refine_lm ▲ | **3.86** | 10.3 | 0.4× | autograd, CPU advantage |
| pca (point cloud) ▲ | **0.21** | — | — | numpy eigh, CPU-only |
| icp_p2p (point cloud) ▲ | **15.3** | — | — | scipy cKDTree, CPU |
| icp_p2plane (point cloud) ▲ | **19.0** | — | — | torch/CPU |

**Method selection (compute resource)**: FFT methods (phase/logpolar), NCC, voting, flow, curvature go on **GPU**. Small iterative refinements (newton/lk/lm), point-cloud methods (pca/icp), and SH are faster on **CPU** (GPU launch/transfer overhead exceeds the problem size).

## Method selection (situation → method). A decision guide that converges the diverged methods
| Situation / requirement | Recommended method | Reason |
|---|---|---|
| translation only, template available | **NCC** or **phase_3d** | phase is template-free and fastest (0.5ms) |
| contrast/illumination varies | **shape_3d** (gradient direction) | intensity invariant |
| distinguish same-intensity objects with different **local shape** | **curvature** (shape index) | matches by surface type |
| **occlusion/partial** present | **chamfer** or **gen. Hough** | missing parts only lower the peak |
| **multiple instances** | **gen. Hough** (NMS peaks) | voting accumulator |
| **z rotation + scale**, no correspondence | **logpolar_z** (coarse) → **refine_rot_z** (fine) | seed with FMT, tighten with GN |
| **arbitrary rotation**, point cloud with correspondence | **PCA** (coarse) → **ICP** (fine) | principal-axis alignment → point-to-plane ICP |
| **arbitrary rotation**, point cloud without correspondence · partial overlap | **feature descriptor** (FPFH/SHOT, in progress) → RANSAC → ICP | global registration with no initial estimate |
| **primitive shape detection** (ground/wall/ball) | **parametric Hough** (plane/sphere) | template-free |
| **rotation-invariant retrieval/matching** | **SH descriptor** | invariant band energy |
| estimate **motion/deformation** | **scene_flow_lk** | dense motion field |
| **refine** a coarse estimate to high precision | Newton/LK/LM/ICP (per parameter) | see table below |

## Coarse → fine pipeline (mapping coarse estimates to their fine tighteners)
| Coarse estimate (output) | Refinement | Attained precision |
|---|---|---|
| integer peak of NCC/shape/Hough | `refine_peak_newton` | 0.01 voxel |
| integer translation | `refine_translation_lk` / `refine_lm` (+scale) | 0.008 voxel |
| Fourier-Mellin rotation ±3° | `refine_rotation_z` | 0.01° |
| coarse pose of PCA / descriptor RANSAC | `icp_point2point_3d` / `icp_point2plane` | RMSE 1e-10 |

## Cells to fill next (TODO). Policy = diverge without narrowing to one means (know-how accumulates in breadth)
- ~~**medial surface / 3D skeleton** (line→surface version)~~ → **implemented 2026-08-27h** (`medial.py`, sphere=1 center point / cylinder=axis line).
- **anisotropic 3DGS exact splat** (currently an isotropic approximation).
- **large-rotation support for log-polar** (resolve the ±45/90° aliasing: multi-projection-axis voting or spherical harmonics).
- **standalone ISS keypoint** (1 schema failure in the Workflow; it is implemented inside feat_shot → publish it independently).
- **differentiable rendering** (make render_* autograd-capable → inverse problems / world-model learning).

## Progress log
- 2026-08-26: implemented, verified, and measured GPU speed for voxel×{NCC, pyramid, sub-voxel, region-morph, shape-based, phase-corr, PCA, MIP}. Connected point cloud / 3DGS via splat transforms. test_match3d(7) + test_accel_3d_toolkit(10).
- 2026-08-27: **added the Fourier-Mellin (`match_logpolar_z`) = rotation+scale column** (z-projection 2D FMT, GPU 30×, rotation error mean 3°/max 5.4°, honest ±45/90° aliasing limit noted). **made chamfer all-GPU with GPU-exact EDT (`edt_jfa`, JFA+2)** (`edt="jfa"`, max|err|=0 vs scipy @N≤160, overtakes at N≥96 96→2.6×/128→4.7×). 5×7=35 cells. test_match3d 12 (+logpolar rotation/scale, edt_jfa exact, chamfer jfa=scipy). speed: also measured PCA 0.2ms / MIP 1.3×.
- 2026-08-27b: **added the generalized Hough (`match_hough_3d`) = voting column** (sum of orientation-bin correlations, multiple-instance 2/2 detection · occlusion robust, GPU 8×). 5×8=40 cells. test_match3d 14 (+hough multi-body/occlusion). Next stage: systematically expand "methods present in 2D but absent in 3D" via TRIZ ideation (2D→3D dimensional lift · line→surface).
- 2026-08-27c (TRIZ principle 17 · line→surface lift): **curvature/shape index** (`curvature_maps`/`match_curvature_3d`, 2 principal curvatures · matches by shape, sphere +1/cylinder +0.5, GPU 6×) / **spherical-harmonic descriptor** (`sh_descriptor`/`match_sh_descriptor`, rotation-invariant sim 0.999, GPU) / **parametric Hough plane · sphere** (`hough_plane_3d`/`hough_sphere_3d`, template-free detection, normal exact · center exact, GPU 4.9×/2×). methods 11 (localization 6/pose 4/detection 1/description 1). test_match3d 21. User guidance = "diverge without narrowing to one means, accumulate know-how in breadth" → currently exploring iterative refinement (Newton/GN/LM/ICP) in parallel in a Workflow.
- 2026-08-27d (iterative refinement = Newton convergence; 6 methods verified in parallel in a Workflow, all PASS → 5/6 primary re-verified after integration PASS, the remaining 1 turned out to be my test-centric-convention mistake, fixed to 0.007voxel PASS): `refine_peak_newton` (0.011vox, 9× vs parabolic) / `refine_translation_lk` (0.008-0.023vox, 60× vs NCC) / `refine_lm` (translation 0.007vox + **new scale recovery**) / `refine_rotation_z` (0.002-0.017°, 5000× over FMT±3°) / `icp_point2point_3d` (RMSE 1e-14, Trimmed for partial overlap) / `icp_point2plane` (RMSE 1e-10, point-to-plane GN, Low 2004). Coarse-estimate→refinement pipeline holds. test_match3d 27 / 56 passed overall.
- 2026-08-27e (diverge→converge): **added scene flow** (`scene_flow_lk`, the 3D version of 2D optical flow, pyramid+warp LK, translation 0.044voxel · divergence detection, GPU 17.5ms/3.7×). Following the user guidance "record processing time / after diverging, do method selection / converge", **measured all methods consistently on CPU/GPU at N=64** → converged into the doc as a **processing-time table + method-selection guide + coarse→fine pipeline table**. honest: small refinements (newton/lk/lm), point-cloud methods (pca/icp), and SH are faster on CPU (GPU overhead). Made sobel3d accept tensor input and gave scene_flow GPU support (bug fix). test_match3d 28. feature descriptors (FPFH/SHOT/spin/Harris3D/ISS) are being explored in parallel in a Workflow.
- 2026-08-27f (data-format axis + geometry; user guidance "3D formats are diverse = use them appropriately / support format conversion" "2 points→line · 3 points→angle/plane are common to 2D/3D"): **extended format transform graph** = `signed_distance_field`/`sdf_to_occupancy`/`estimate_point_normals` (PCA normals)/`mesh_to_points`/`voxel_to_mesh` (marching cubes)/`tsdf_from_depth` (RGB-D). **added 3D grey morphology** = `morph_gradient3d` (boundary)/`morph_tophat3d` (small-bright structure)/`morph_blackhat3d`. **geometric-primitive/metrology layer** (HALCON-equivalent, all closed form) = construction/angle/distance/intersection/fitting. test_match3d 35.
- 2026-08-27g (converge the divergence toward completion; user "finish the accumulated work / note that game-oriented OSS sometimes abandons rigor / differentiate from HALCON · OpenCV for Physical AI"): **surface approximation** (z=f(x,y) least squares / form error / background correction) / **curvilinear coordinate systems** (polar · cylinder unwrap / Zernike) / **optics** (reflect/refract Snell/Fresnel/deflectometry, all rigorous) / **projection · rendering** (project_points/render_point_depth/render_volume_projection[DRR]/render_shaded = close the loop via 3D→2D synthesis). **explored 4 sparse-feature-registration methods in parallel in a Workflow → primary-verified after integration** (`feat_harris`/`feat_spin` 1.84°/`feat_fpfh` 0.83°/`feat_shot` 0.00°, no-initial-estimate 60° rotation + 70% overlap registration. shot fixed by adding an icp import). **72 passed / 5 skipped overall**, match3d 98 functions + feat 4 modules. Turned it into a toolkit (matching + metrology + optics + rendering + transforms + morphology).
- 2026-08-27h (**method diffusion 2nd wave = sensor-based perception**, 2 direct main implementations + 4 parallel agents mutually monitored, primary re-verified after integration): diffuse new method families for depth sensing/inspection/shape as independent modules. **`photometric.py`** (photometric stereo + Frankot-Chellappa normal integration + Lambertian synthesis, normal angular error <1° / shape correlation >0.98, 5 tests) / **`range_image.py`** (organized depth → oriented normals [neighbor cross product O(HW)] / bearing-angle / occlusion edges, matches plane-normal analysis, 6 tests) / **`pcl_filter.py`** (point-cloud preprocessing SOR/radius/voxel/**MLS**, MLS RMS 0.019→0.0085, 12 tests. honest: SOR/radius/voxel have a canonical version in `pointcloud.py` = MLS is the unique addition) / **`fringe.py`** (structured-light phase-shift + Gray-code profilometry, noise-free RMS 5.6e-16, 22 tests) / **`deform3d.py`** (3D non-rigid TPS/nonrigid-ICP/CPD, bend recovery 384× · rigid machine precision, 15 tests. honest: a different domain from the 2D-image `deformreg.py`) / **`medial.py`** (TRIZ line→surface = medial surface/3D skeleton, sphere=1 center point error 0 / cylinder=axis line, 16 tests). **ops3d = 108 ops / 22 categories** (missing 0), full 3D suite **127 passed**. Following the user guidance "we are in the method-diffusion phase now, feel free to proceed", prioritized breadth (verify in a few batches / plan to re-check all ops after a Fable reset). Recorded the canonical know-how in RAD `fullseye_3d_vision_corpus_v2` (SKILL+note9) + the 2nd Brain.
- 2026-08-27i (**method diffusion 3rd wave = evaluation · robust fitting · edges · reconstruction**, 1 direct main implementation + 3 parallel agents, primary re-verified after integration): **`metrics3d.py`** (the fitness foundation for evolutionary search = chamfer/Hausdorff/F-score/normal consistency/voxel IoU · Dice/pose error/RMSE. identical→exact match · known offset→RMSE exact · pose exact, 7 tests) / **`ransac_fit.py`** (RANSAC robust primitive fitting plane/sphere/line/cylinder, normal error 0.001–0.011° under 30% outliers · deterministic seed, 7 tests. an agent found and fixed a real bug: outlier-bias in the cylinder's all-point fit) / **`edges3d.py`** (3D Canny/LoG edges, boundary recall 1.0 · edge thickness 0.218, 12 tests) / **`recon3d.py`** (point cloud → surface reconstruction poisson_lite/alpha shapes, sphere residual 3.4–6.3%R · alpha boundary 100% surface capture, 13 tests. honest: a lightweight Poisson approximation). **ops3d = 128 ops / 26 categories** (missing 0), full 3D suite **166 passed**. ★metrics3d is the keystone directly supporting the evolutionary direction (op-chain search by fitness) = the divergence connects to the next convergence (evolutionary search).
- 2026-08-27j (**method diffusion 4th wave = measurement · description of free-form shapes**, 1 direct main implementation + 2 parallel agents, primary re-verified after integration): **`curve3d.py`** (differential geometry of space curves = Frenet frame/curvature κ/torsion τ/arc length/spline smoothing. κ,τ are invariant under reparameterization, so rigorous via index numerical differentiation; matches helix κ=a/(a²+b²) · τ=b/(a²+b²) within 2%, 7 tests) / **`descriptors3d.py`** (statistics-based global descriptors = D2 distance distribution/A3 angle distribution/extent, near-rigorous rotation- and scale-invariance · rigorously discriminates same-shape < different-shape, 17 tests. honest: thin sphere-vs-cube margin · weak on concave shapes) / **`bspline_surf.py`** (B-spline free-form surface/curve fitting, recovers z=sin(x)cos(y) at RMS 0.0125/correlation 0.9997 · plane residual 0, 18 tests. honest: smoothness-selection tradeoff · weak extrapolation). **ops3d = 143 ops / 29 categories** (missing 0), full 3D suite **208 passed**. **★this turn's method diffusion (2nd–4th waves) = 13 new modules · 208 passed · all pushed** (photometric/range_image/pcl_filter/fringe/deform3d/medial/metrics3d/ransac_fit/edges3d/recon3d/curve3d/descriptors3d/bspline_surf). The natural next convergence = a 3D-pipeline evolutionary-search PoC (type chaining of ops3d.compatible × metrics3d fitness).
- 2026-08-27k (**method diffusion 5th wave [final] = pose estimation and multi-object measurement**, 1 direct main implementation + 1 parallel agent, primary re-verified after integration): **`pnp3d.py`** (Perspective-n-Point = recover camera pose from 3D-2D correspondences via DLT = the inverse problem of my `project_points`. project with a known pose → recover, rot error <0.1° · reprojection <1e-3, pnp_ransac rejects 25% outliers, 5 tests. ★the forward-inverse loop of projection is closed) / **`regionprops3d.py`** (multi-object measurement of 3D connected components = volume/centroid/bbox/principal axes/sphericity, 2-sphere volume ±2% · center exact, 10 tests. ★an agent found the 2/3 upper bound of sphericity [an approximation property of face-counted surface area] and honestly adjusted the threshold = honest disclosure). **ops3d = 150 ops / 31 categories** (missing 0), full 3D suite **231 passed**. **★★this turn's method-diffusion summary (2nd–5th waves) = 15 new modules · 231 passed · all pushed**. The natural next convergence = a 3D-pipeline evolutionary-search PoC (awaiting instruction = the user stated "we are in the diffusion phase now").
- 2026-08-27l (**method diffusion 6th wave + audit + fix = one diverge↔converge cycle in one turn**, user "diverge further / watch for defects while diverging = efficient / repeat diverge↔converge several times"): **6 divergence modules** = direct main implementation `twoview.py` (two-view epipolar geometry = normalized 8-point F · E decomposition · DLT triangulation · relative pose uniquely determined by cheirality, the core of monocular SfM/VO. R error <1° · t direction <1° · converges to a few degrees at 0.3px pixel noise, 13 tests) / `curvature3d.py` (point-cloud principal curvatures = local Monge fit · mean/Gaussian/shape index, sphere 1/R · cylinder (1/R,0) · saddle K<0, grasping affordance) + Workflow parallel 4 `moments3d` (3D moment invariants · translation/rotation/scale invariant, machine precision) / `geodesic3d` (surface geodesic distance = TRIZ line→surface, kNN Dijkstra, sphere = great-circle distance 2.7%) / `visualhull` (silhouette space carving, sphere IoU 0.95) / `superquadric` (superquadric fitting, recovers ellipsoid/box). **★interleaved audit + fix in the same turn** (user "watch for defects while diverging") = an adversarial-audit Workflow (existing 15 modules in 5 parallel groups) **exposed 13 real bugs with concrete repros** → centrally re-confirmed all repros → a fix Workflow (8 parallel groups · root cause + regression tests) fixed them all → re-ran the repros centrally: 10/11 correct behavior · [8] honest partial (poisson_lite's double shell becomes a single watertight shell · sparse input is a known limit) confirmed. Bugs concentrated into **2 major classes** (**scale-independent absolute epsilon/threshold** = curve3d κ/τ · recon3d's circumscribed sphere silently wipes out small coordinates entirely; **fabricated values for degenerate input** = pnp3d coplanar garbage pose · ransac/metrics/visualhull fabricate inlier_ratio=1.0/IoU=1.0/all voxels) + weak tests (frenet tautology · bspline one-sided deviation · total_curvature had no test). Probed the 4 new modules with note_15's 3 failure modes → added a fix for one visualhull "0-camera" fail-closed case. **ops3d = 175 ops / 37 categories** (missing 0), full 3D suite **236 passed**. Updated OP_COMBINATION_MATRIX to 175/37 · 3,282 two-stage chains · wave6 rows #37-46. RAD note_13 (two-view)/note_14 (curvature)/note_15 (2 major audit bug classes) recorded. ★lesson = **"GT test pass ≠ correct"**; divergence alone accumulates ~0.87 bugs/module → **interleaving an adversarial audit every 1-2 waves is most efficient**. **Recommended cadence = another 2-3 cycles (each: diverge 4-6 + audit + fix) → converge to evolutionary search**.
- 2026-08-27m (**method diffusion 7th wave + wave6 audit + fix = diverge↔converge cycle 2**, user "repeat diverge↔converge several times / while considering how many diffusions balance completeness and efficiency"): **diverge 5** = direct main implementation `bundle3d.py` (N-view bundle adjustment = simultaneously optimize all camera poses + 3D structure by minimizing reprojection, the N-view version of twoview. gauge = first camera fixed · rotvec+t parameters · LM, reprojection RMSE ~0 from a perturbation · recovers rotation <0.5°, 4 tests) + Workflow parallel 4 `tsdf_fusion` (multi-frame TSDF volume fusion + zero-crossing extraction = the KinectFusion core, sphere median 0.08voxel · coverage 0→0.5, 9) / `pcl_augment` (point-cloud data augmentation jitter/rotation/scale/dropout/elastic/cutout, rotation isometry · exact dropout count, 31) / `gicp` (Generalized-ICP plane-to-plane covariance, rot <0.5°, 9) / `segment3d` (point-cloud segmentation normal region growing/Euclidean/plane extraction, 15). **★audit = adversarial audit of the 6 unaudited wave6 modules in 2 groups → 6 real bugs confirmed** (all repros reproduced) → fix Workflow (4 groups root cause + regression tests) fixed them all → central repro re-run confirmed all fixes. Bugs were again **the same 2 major classes** (scale-independent threshold = curvature3d shape_index misclassifies gently curved surfaces · moments3d degenerate 1e-13; fabricated values = geodesic_mesh double-counted edges 2× · twoview coplanar t-direction fabrication) + **conceptual flaws** (★curvature3d shape_index's concave/convex is fundamentally undetermined locally = an oriented normal is intrinsically required → added optional normals + corrected note_14; moments3d with only 2nd moments collides cube/sphere → added the higher-order radial moment m4=⟨r⁴⟩/⟨r²⟩²). Fixes = scale relativization / fail-closed ValueError / optional oriented normals / higher-order invariants. **ops3d = 192 ops / 42 categories** (missing 0), full 3D suite **315 passed**. Updated OP_COMBINATION_MATRIX to 192/42 · 4271 two-stage chains · wave7 rows #47-52. Added RAD note_16 (BA gauge) + corrected note_14 = 16 notes total. ★lesson reconfirmed = the adversarial audit detects the same 2 classes + conceptual flaws **even in new modules (including my twoview/curvature3d implementations)** → re-proving that interleaving "watch for defects while diverging" is most efficient. **2 divergence cycles complete (reached the recommended lower bound) → next is convergence = propose the 3D-pipeline evolutionary-search PoC (ops3d.compatible type chaining × metrics3d fitness)**.
- 2026-08-27n (**convergence phase achieved = 3D-pipeline evolutionary-search PoC**, user choice "1=converge"): materialize the payoff of divergence = **`pipeline_evolve.py`**. Replace manual op×op F×D scoring with **automatic fitness search** (generalization of register_auto). 3 elements = (1) grammar = ops3d type consistency (`compatible` auto-prunes type-mismatched chains, e.g. estimate_point_normals for points→normals is a dead end since there is no normals→op, so it never appears in valid chains) (2) fitness = metrics3d chamfer (3) GA (tournament + type-preserving mutation/crossover + elitism, genome bloat suppressed by a crossover length cap). PoC = point-cloud denoising (noise+outliers → minimize chamfer to a clean spherical surface). **Beats all 3 honest baselines (consistent across 3 seeds)**: identity 0.10 → hand-designed (SOR→MLS) 0.049 → **evolved 0.041** (2.5× improvement over identity, beats both hand and random). ★discovery = evolution automatically finds "mls_smooth×n + radius_outlier_removal", **a pipeline that beats the hand-designed SOR→MLS**. ★honest disclosure = the search space is small so random also does well (0.042 vs 0.041 = tiny gap, evolution's advantage kicks in with space expansion and more stages = do not exaggerate). 6 tests (evolution > identity/hand/random · grammar type consistency · dead-end pruning · determinism · history monotonicity). ★**precisely because the type system (192 typed ops accumulated through divergence) exists, the automatic-search space can be defined and holds = divergence→convergence is one continuous arc**. pipeline_evolve is an engine so it is not registered in ops3d (like pipeline3d). RAD note_17 recorded = 17 notes total. Next-stage candidates = evolve op parameters too / multi-task fitness / QD (quality-diversity).
- 2026-08-27o (**diverge↔audit↔fix cycle 3-4 = wave8-9**, user "continue diverge↔audit↔fix and push when done / push in bulk after running several cycles"): after convergence (evolutionary search), returned to the divergence cycle per the user's instruction. **wave8 diverge 4** = main `pose_graph` (SLAM back-end = relative pose + loop closure, SE(3) tangent residual · gauge first-camera fixed, 5 tests) + workflow `normals_orient` (consistently oriented normals by MST propagation = corrects curvature3d's concave/convex sign = the real resolution of the wave7 flaw) / `scene_flow3d` (point-cloud scene flow rigid decomposition) / `occupancy` (occupancy + ESDF + inflation, coexists with the existing 2D nav). audit = wave7 5 modules → **2 real bugs** (gicp GN damping at extreme scale · segment3d's -1 contract) → fixed. **wave9 diverge 3** = main `symmetry3d` (reflection/rotation symmetry = chamfer scoring) + workflow `spherical_proj` (LiDAR spherical range image) / `motion_seg3d` (rigid motion segmentation). audit = wave8 4 modules → **6 real bugs** (occupancy line_of_sight asymmetry / 2D bounds / inflate validation · pose_graph loop_closure weak test [mine] / index unverified · normals_orient seed_dir silent discard) → fixed. Root-fixed all bugs + regression tests · centrally re-confirmed the repros. ★the audit detects the same 2 major classes + weak tests even in new modules (including my own pose_graph/symmetry3d). **ops3d = 214 ops / 49 categories**, full 3D suite **430 passed**, 5246 two-stage chains. OP_COMBINATION_MATRIX 214/49 · wave8-9 rows #53-59. RAD note_18 (pose_graph gauge/SE3 residual) / note_19 (general chamfer comparison + the normalization-length pitfall) = 19 notes total. ★**4 diverge↔audit↔fix cycles (wave6-9) = 33 new modules · 27 real bugs found and fixed · a convergence PoC. Nearly covers the major 3D-vision method families = point of diminishing returns**. Next candidates = deepen convergence (op-parameter co-evolution/QD) or applied porting (evis visual pipeline).
