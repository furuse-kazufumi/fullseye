<!-- i18n-source-sha: 673abba3a20e -->
# evis Vision Components — OSS/ROS2 Gap Analysis (2026-08-17)

[日本語](./EVIS_VISION_OSS_GAP.md) · **English**

Purpose: In building the **vision function components** for evis (the MS-Human-700 musculoskeletal humanoid),
a sorting exercise to strictly hold the line of "don't reinvent what OSS/ROS2 already covers." Each perception module is
weighed against the **standard stack actually used in ROS2 robotics** to decide between
`reinvents` (a numpy re-implementation of existing OSS = little value in building) and `genuine gap` (absent from OSS = worth building ourselves).
The ROS2 ecosystem was confirmed by hands-on investigation (see Sources at the end).

## evis Vision Pipeline (from the existing design PERCEPTION_PHYSICAL_AI.md)

```
Grasping (eating with chopsticks): stereo_rectify → disparity_sgm → depth_to_points + normals_from_depth
                  → pcseg.remove_ground/euclidean_clusters → ppf.find_surface_pose(6-DoF) → grasp
Locomotion (hillco):     depth → terrain.elevation_map → slope/step_edges/foothold_candidates
                  → locomotion.support_polygon + com_support_margin
```

## Gap Table (module → ROS2/OSS standard → verdict)

| module (ops) | Role | ROS2/OSS standard (in real use) | Verdict |
|---|---|---|---|
| `camera` (21) | projection/backproject/PnP/essential/rectify | `image_geometry` (PinholeCameraModel) + OpenCV (`solvePnP`/`findEssentialMat`/`stereoRectify`/`Rodrigues`) | **reinvents** OpenCV |
| `stereo` (11) | census/SGM disparity, depth | `image_pipeline`/`stereo_image_proc` (SGBM), `depth_image_proc`, NVIDIA Isaac ROS (deep stereo) | **reinvents** image_pipeline |
| `pcseg` (17) | RANSAC plane/sphere/cylinder, clustering, OBB, curvature | **PCL** (`SACSegmentation`/`EuclideanClusterExtraction`/`MomentOfInertiaEstimation`) via `perception_pcl` | **reinvents** PCL |
| `pointcloud` | normals, voxel, outlier, FPFH | **PCL** (`NormalEstimation`/`VoxelGrid`/`StatisticalOutlierRemoval`/`FPFHEstimation`) | **reinvents** PCL |
| `registration` | ICP, Kabsch, FPFH register | **PCL** (`IterativeClosestPoint`/`SampleConsensusPrerejective`) / Open3D | **reinvents** PCL/Open3D |
| `ppf` | Drost PPF 6-DoF | OpenCV `surface_matching` (`ppf_match_3d`); frontier = deep (FoundationPose/GraspNet) | **reinvents** OpenCV (frontier is deep) |
| `terrain` (13) | elevation/foothold/traversability/slope/step_edges | **ANYbotics `grid_map` + `elevation_mapping` + leggedrobotics `traversability_estimation`** (ANYmal = the legged-robot standard; holds elevation/foothold quality/traversability as layers) | **reinvents** grid_map (core of legged robots) |
| `locomotion` (5) | support polygon, COM margin, gait phase | **No** standard ROS2 perception pkg. Scattered across legged-robot control (OCS2/TOWR/WBC) | **partial gap** (control-side) |
| `odometry` (5) | RGBD/PnP odometry, umeyama, trajectory | `rtabmap_ros` / ORB-SLAM3 / `robot_localization` | **reinvents** rtabmap |
| `sceneflow` (7) | FoE, TTC, looming, scene flow | OpenCV optical flow (sparse/dense). scene-flow/TTC are research-leaning, thin ROS standards | **partial gap** (niche) |
| `features` (5) | Harris/FAST, descriptors, match | OpenCV (`goodFeaturesToTrack`/`FAST`/`ORB`/`BFMatcher`) | **reinvents** OpenCV |
| `pose` (3) | silhouette posture descriptors | (simple silhouette-derived descriptors; thin direct OSS coverage) | **partial gap** (simple) |
| `occupancy` | grid, inflate, clearance | `nav2` `costmap_2d` | **reinvents** nav2 |

## Manipulation/Planning/Execution Layer (reflecting the MoveIt2 point — perception alone is only half the job)

The complete loop where evis "uses" vision is **perceive → plan → execute**. The second half is where the important components lie, and here ROS2 has a thick standard.

```
Perception (stereo/PCL) → 6D grasp pose (GPD/AnyGrasp) → MoveIt2 MTC (grasp pose → IK → collision-free trajectory
→ move-to-pick/grasp/lift/place) → ros2_control (position/velocity/effort I/F) → robot
```

| Component | Role | ROS2/OSS standard (in real use) | Verdict |
|---|---|---|---|
| Motion planning/IK/collision avoidance | grasp pose → collision-free trajectory | **MoveIt2** (OMPL/STOMP/Pilz, 150+ robots in production) + **MoveIt Task Constructor** (staged pick&place) | **use OSS** (not worth self-building) |
| grasp generation | cloud/RGB-D → 6-DoF grasp candidates + scores | **GPD** / **AnyGrasp** / SuctionNet (MoveIt integration), frontier = deep (GraspNet) | **use OSS** |
| Hardware abstraction/low-level control | position/velocity/effort I/F | **ros2_control** (the foundation of MoveIt2/Nav2; a humanoid's ROS2 exposure is almost entirely through here) | **use OSS** |
| Navigation | mapping/pathing/obstacle avoidance | **Nav2** (costmap_2d/BT) | **use OSS** (evis doesn't need it for now) |
| grasp force/force-closure | antipodal grasp quality | GraspIt!/`grasp` (Ferrari-Canny) | partial (the existing grasp op suffices) |

### ★ The true core gap = the muscle-driven evis bridge (absent from OSS)

MoveIt2/ros2_control assume **URDF position/torque joints + a standard gripper**. **evis is driven by MuJoCo's 700 muscles (Hill type)**,
and handles chopsticks (a tool, not a gripper) with an articulated hand. → **No OSS layer exists that realizes the joint trajectory MoveIt2 emits with the activation of 700 muscles.**
This "joint plan → muscle activation" step = **QP / static optimization / WBC** (the QP+osqp you already have in `reference_wbc_qp_control`) is precisely the
evis-specific component that OSS/ROS2 cannot fill. The final step of vision (6D pose) → MoveIt2 (trajectory) → **muscle realization (QP)** is the real gap.

## Visualization Layer (reflecting the RViz2 point — Studio fidelity reference)

The tables so far leaned heavily on algorithms (PCL/OpenCV/grid_map/MoveIt2) and were missing the **"see and confirm" layer**.
HDevelop is strong at displaying 2D images/BLOBs, but Physical AI vision requires **3D display** (point clouds, depth, 6D pose axes, TF trees,
grasp markers, elevation maps) as a must. The ROS2 standard here is **RViz2**. This is a **visualization fidelity/feature reference** so that Fullseye Studio (an HDevelop-style IDE)
can be used to understand, test, and put things into practice; it is not an algorithm, so it is not a re-implementation target but rather serves as the
**requirements map for Studio exposure (F6)**.

| Subject | What to see | ROS2/OSS standard (in real use) | Handling in fullseye |
|---|---|---|---|
| point cloud | PointCloud2 color/intensity/normals | **RViz2** PointCloud2 display / Open3D viewer | Reference for Studio's 3D viewer requirements (F6). No re-implementation; integrate with an existing viewer or thin rendering |
| depth/image | depth colormap, camera image | RViz2 Image/DepthCloud, `image_view` | Place Studio's 2D panel (HDevelop equivalent) alongside 3D |
| 6D pose/grasp | pose axes, grasp posture markers | RViz2 Pose/PoseArray/**InteractiveMarker**, `moveit_visual_tools` | Render ppf/grasp op outputs as axes in Studio (core of evis debugging) |
| coordinate frames | TF tree, link-relative poses | RViz2 TF display | Confirm the camera↔hand↔object pose chain |
| terrain | elevation/traversability layer | RViz2 + **grid_map_rviz_plugin** | Visualize footholds from the terrain op (hillco locomotion) |

★ Implication: **Studio = a fusion of HDevelop (2D image-processing IDE) + RViz2 (3D perception visualization)** is the right shape. evis vision debugging
(is the 6D pose correct? / is the point-cloud segment reasonable? / is the foothold sitting on the terrain?) cannot be judged honestly without 3D visualization.
Each op of the unified I/F should carry **in its meta (F3) "how it draws in Studio"** (2D image / point cloud / pose / grid_map layer),
so that Studio can automatically select RViz2-equivalent rendering.

## Fullseye's Purpose (confirmed with the user 2026-08-17 — the premise of this analysis)

Fullseye = **a comprehensive library that holds every image-processing/vision algorithm as a "skill," ready to use instantly** (a dedicated HALCON).
**HALCON-grade coverage is the goal.** Fullseye Studio (HDevelop-style) = an IDE to understand, test, and use these functions in real work.
→ The ROS2 investigation in this doc is **not "don't build it," but a fidelity/priority reference for building it correctly, comprehensively, and faithfully to real-world vocabulary.**

## Honest Conclusion (corrected to fit the purpose)

- The value of the ROS2 investigation = **a fidelity reference for the correct semantics, real-world vocabulary, and "what is the standard" of each algorithm**, plus **a map of which ops to prioritize for coverage.**
  It is not "don't build it because PCL/grid_map/OpenCV have it" — the purpose is to **hold it all ourselves comprehensively (self-contained numpy) and turn it into skills.**
- **The exception where a thin wrapper suffices** = pure heavyweight dependencies that add neither understanding nor instant usability (e.g., GPU-accelerated SGM, deep 6D pose). Call OSS there.
- **The truly "weird direction" to stop = general CS (algo-c: sort/CRC/palindrome)**. It is not image-processing/vision knowledge, so it is outside fullseye's coverage scope.
- **Perception primitives (camera/stereo/pcseg/terrain/features…) are fullseye's core.** Use the feature sets of ROS2's PCL/grid_map/image_pipeline
  **as a coverage-goal map**, fill in missing ops with honest gates, and **expose them in Studio** (understand, test, use in practice).
There is educational and self-contained value, but for the purpose of "making" evis vision run, rewriting these by hand is
exactly "reinventing what OSS already covers." In particular, **grid_map for legged-robot terrain/foothold, and PCL for the grasp cloud→segment→pose**
are the front-runners actually used on real robots.

## Where evis is worth building ourselves = absent from OSS/ROS2 (genuine gap, in priority order)

1. **★ Muscle-drive bridge (joint plan → 700-muscle activation)**: the layer that realizes the outputs of MoveIt2/GPD (grasp pose, joint trajectory)
   with evis's 700 muscles. QP/static optimization/WBC (`reference_wbc_qp_control`). **The most important component absent from OSS/ROS2.**
2. **sim-source vision bridge (MuJoCo / Gazebo / Isaac Sim — user's point 2026-08-18)**: evis's binocular RGB/depth/
   segmentation is **free as ground-truth inside a sim** (outside the ROS2 stack, which assumes real sensors). Originally written as MuJoCo-only, but
   it should be **generalized into an adapter for sim sources in general.** Place `sim.MuJoCo` / `sim.Gazebo` / `sim.IsaacSim` behind the unified I/F with **the same verbs**
   (`.frames()` / `.depth()` / `.intrinsics()` / `.ground_truth()`), so that vision ops can be composed regardless of the input source.
   The difference in their roles =
   - **MuJoCo/MJX**: evis/hillco's **physics engine proper** (700 muscles, chopsticks, and locomotion actually run). Core of the app; don't change it.
   - **Gazebo (Ignition)**: **the ROS2 standard sim.** Directly connects to ros2_control / RViz2 / sensor plugins (camera/depth/lidar → `sensor_msgs`)
     = the entry point where the unified I/F can be validated with **real ROS2 wiring.**
   - **Isaac Sim (NVIDIA Omniverse)**: GPU, photoreal, **synthetic data generation + domain randomization** (where the RTX 5090 pays off).
     GPU deep perception is **Isaac ROS** (deep stereo/DNN pose) = the aforementioned "heavyweight wrapper" bucket. Especially well matched to the honest evaluation of gap #3.
   The **adapter contract** (F4) of the sim bridge that closes "evis's eyes → perception → planning → muscle realization" is app-specific, but make it an I/F common to all 3 sims.
3. **Honest evaluation of vision-driven behavior**: measure honestly whether "the chopsticks actually picked it up / the locomotion is real (no slipping/diving) / the 6D pose matches ground truth"
   by cross-checking against **sim ground-truth** (#2's `sim.*.ground_truth()`: true 6D pose, segmentation, contact) —
   an evaluator (along the lines of CONSUMER_APPLICATIONS.md). Isaac Sim's synthetic data + randomization is the proper source of evaluation data. App-specific.
4. **Balance perception for locomotion** (support polygon/COM margin/gait) is a partial gap but control-leaning (OCS2/TOWR etc. exist).

## Implications (recommendation, needs user approval)

★ **Unified interface principle (user-confirmed 2026-08-17)**: whether the internals are self-built numpy or an OSS wrapper, **the caller can invoke it through
fullseye's identical I/F** (facade op naming, signature conventions, Studio exposure, honest gate/meta). Even where OSS is used, don't hit raw PCL/OpenCV directly;
tuck it away as a **thin adapter behind fullseye's unified I/F** (= the same as how HALCON offers diverse internal implementations under a single operator vocabulary).
The substance of "instantly usable as a skill" is this consistent I/F.

To fit fullseye's purpose (comprehensive, instantly usable, skill-ified, unified I/F, Studio practicality), run two lines in parallel:

- **(A) Advance library coverage** = use the feature sets of PCL/grid_map/image_pipeline/OpenCV as a **coverage map**,
  fill the gaps in fullseye's perception ops with honest gates, and **expose them in Studio** (in a form ready to understand, test, and use at work).
  Self-contained numpy by default; a thin wrapper only for heavyweights (GPU SGM/deep pose). Same line as **growing the 13.3% in HALCON_COVERAGE.md.**
- **(B) evis-specific genuine gaps** (where OSS has nothing) = in the priority order above, especially **#1 the muscle-drive bridge** (vision→MoveIt2/GPD planning
  references OSS; only the final "realize with 700 muscles" is evis-specific), **#2 the MuJoCo sim vision bridge**, and **#3 honest evaluation.**

To confirm: should tonight's autonomous work go to **(A) coverage of perception ops + Studio exposure**, or **(B) the evis muscle-drive bridge / sim vision**?
Do not fall back to general CS (algo-c).

## Sources (hands-on ROS2 investigation)

- perception_pcl / PCL (the ROS2 point-cloud standard): <https://github.com/ros-perception/perception_pcl> · <https://index.ros.org/p/pcl_ros/>
- ANYbotics grid_map (legged-robot elevation/foothold/traversability): <https://github.com/ANYbotics/grid_map> · traversability: <https://github.com/leggedrobotics/traversability_estimation>
- image_pipeline / stereo_image_proc / depth_image_proc: <https://docs.ros.org/en/rolling/p/image_pipeline/>
- 6-DoF pose / grasp (GPD + MoveIt, frontier=deep): <https://arxiv.org/pdf/2312.03345>
- Visualization: RViz2 <https://github.com/ros2/rviz> · grid_map_rviz_plugin (bundled with ANYbotics grid_map) · moveit_visual_tools
- sim sources: Gazebo/Ignition (ROS2 standard sim, ros_gz bridge) <https://gazebosim.org/> · NVIDIA Isaac Sim/Isaac ROS (GPU synthetic data, deep perception) <https://developer.nvidia.com/isaac/sim> · MuJoCo/MJX (evis/hillco physics proper)
