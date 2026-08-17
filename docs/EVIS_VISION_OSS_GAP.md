# evis の視覚部品 — OSS/ROS2 ギャップ分析 (2026-08-17)

目的: evis(MS-Human-700 筋骨格ヒューマノイド)の**視覚機能部品**を作るにあたり、
「OSS/ROS2 で足りるものは再発明しない」を厳守するための仕分け。各知覚モジュールを
**実際に ROS2 ロボティクスで使われている標準スタック**に照らし、
`reinvents`(既存 OSS の numpy 再実装=作る価値薄い)/ `genuine gap`(OSS に無い=自作の価値)
を判定する。ROS2 エコシステムは実地調査で確認(末尾 Sources)。

## evis の視覚パイプライン(既存設計 PERCEPTION_PHYSICAL_AI.md より)

```
把持(箸で食べる): stereo_rectify → disparity_sgm → depth_to_points + normals_from_depth
                  → pcseg.remove_ground/euclidean_clusters → ppf.find_surface_pose(6-DoF) → grasp
歩行(hillco):     depth → terrain.elevation_map → slope/step_edges/foothold_candidates
                  → locomotion.support_polygon + com_support_margin
```

## ギャップ表(module → ROS2/OSS 標準 → 判定)

| module (ops) | 役割 | ROS2/OSS 標準(実使用) | 判定 |
|---|---|---|---|
| `camera` (21) | 投影/backproject/PnP/essential/rectify | `image_geometry`(PinholeCameraModel)+ OpenCV(`solvePnP`/`findEssentialMat`/`stereoRectify`/`Rodrigues`) | **reinvents** OpenCV |
| `stereo` (11) | census/SGM disparity, depth | `image_pipeline`/`stereo_image_proc`(SGBM)、`depth_image_proc`、NVIDIA Isaac ROS(deep stereo) | **reinvents** image_pipeline |
| `pcseg` (17) | RANSAC 平面/球/円柱, clustering, OBB, curvature | **PCL**(`SACSegmentation`/`EuclideanClusterExtraction`/`MomentOfInertiaEstimation`)via `perception_pcl` | **reinvents** PCL |
| `pointcloud` | normals, voxel, outlier, FPFH | **PCL**(`NormalEstimation`/`VoxelGrid`/`StatisticalOutlierRemoval`/`FPFHEstimation`) | **reinvents** PCL |
| `registration` | ICP, Kabsch, FPFH register | **PCL**(`IterativeClosestPoint`/`SampleConsensusPrerejective`)/ Open3D | **reinvents** PCL/Open3D |
| `ppf` | Drost PPF 6-DoF | OpenCV `surface_matching`(`ppf_match_3d`); frontier = deep(FoundationPose/GraspNet) | **reinvents** OpenCV(frontier は deep) |
| `terrain` (13) | elevation/foothold/traversability/slope/step_edges | **ANYbotics `grid_map` + `elevation_mapping` + leggedrobotics `traversability_estimation`**(ANYmal=脚ロボ標準。elevation/foothold quality/traversability を layer で保持) | **reinvents** grid_map(脚ロボ核心) |
| `locomotion` (5) | support polygon, COM margin, gait phase | ROS2 標準の知覚 pkg **なし**。脚ロボ制御(OCS2/TOWR/WBC)側に散在 | **partial gap**(制御寄り) |
| `odometry` (5) | RGBD/PnP odometry, umeyama, trajectory | `rtabmap_ros` / ORB-SLAM3 / `robot_localization` | **reinvents** rtabmap |
| `sceneflow` (7) | FoE, TTC, looming, scene flow | OpenCV optical flow(疎/密)。scene-flow/TTC は研究寄りで ROS 標準薄い | **partial gap**(niche) |
| `features` (5) | Harris/FAST, descriptors, match | OpenCV(`goodFeaturesToTrack`/`FAST`/`ORB`/`BFMatcher`) | **reinvents** OpenCV |
| `pose` (3) | silhouette 姿勢記述 | (シルエット由来の簡易記述子。直接の OSS 対応薄い) | **partial gap**(簡易) |
| `occupancy` | grid, inflate, clearance | `nav2` `costmap_2d` | **reinvents** nav2 |

## マニピュレーション/計画/実行 層(MoveIt2 指摘を反映 — 知覚だけでは片手落ち)

evis が視覚を「使う」完全ループは **perceive → plan → execute**。後半こそ重要部品で、ここは ROS2 に厚い標準がある。

```
知覚(stereo/PCL)→ 6D grasp pose(GPD/AnyGrasp)→ MoveIt2 MTC(grasp pose→IK→衝突回避軌道
→ move-to-pick/grasp/lift/place)→ ros2_control(position/velocity/effort I/F)→ ロボット
```

| 部品 | 役割 | ROS2/OSS 標準(実使用) | 判定 |
|---|---|---|---|
| 動作計画/IK/衝突回避 | grasp pose → 衝突なし軌道 | **MoveIt2**(OMPL/STOMP/Pilz、150+ ロボ実績)+ **MoveIt Task Constructor**(pick&place ステージ化) | **use OSS**(自作不可) |
| grasp 生成 | cloud/RGB-D → 6-DoF grasp 候補+スコア | **GPD** / **AnyGrasp** / SuctionNet(MoveIt 連携)、frontier=deep(GraspNet) | **use OSS** |
| ハード抽象/低レベル制御 | position/velocity/effort I/F | **ros2_control**(MoveIt2/Nav2 の土台。humanoid の ROS2 露出はほぼここ経由) | **use OSS** |
| ナビゲーション | 地図/経路/障害回避 | **Nav2**(costmap_2d/BT) | **use OSS**(evis は当面不要) |
| 把持力/force-closure | antipodal grasp 品質 | GraspIt!/`grasp`(Ferrari-Canny) | partial(既存 grasp op で足りる) |

### ★真の核心ギャップ = 筋駆動 evis のブリッジ(OSS に無い)

MoveIt2/ros2_control は **URDF の位置/トルク関節+標準グリッパ**前提。**evis は MuJoCo の 700 筋(Hill 型)駆動**で、
箸(グリッパでない道具)を articulated hand で扱う。→ **MoveIt2 が出す関節軌道を 700 筋の活性で実現する層が OSS に存在しない**。
この「関節計画 → 筋活性実現」= **QP / static optimization / WBC**(あなたが既に持つ `reference_wbc_qp_control` の QP+osqp)こそ、
OSS/ROS2 では埋まらない evis 固有部品。視覚(6D pose)→ MoveIt2(軌道)→ **筋実現(QP)** の最後の一段が本当のギャップ。

## 正直な結論

**知覚 op の約 8〜9 割は、成熟した ROS2/OSS(PCL・grid_map・image_pipeline・OpenCV・rtabmap・nav2)の numpy 再実装**。
**マニピュレーション/実行層(MoveIt2/MTC/GPD/ros2_control)も自作対象ではなく OSS を使う所**。
教育・自己完結の価値はあるが、evis の視覚を「動かす」目的では、これらを手で書き直すのは
まさに「OSS で足りるものの再発明」。特に **脚ロボの terrain/foothold は grid_map、
把持の cloud→segment→pose は PCL** が実robotで使われる本命。

## OSS/ROS2 に無い = evis 視覚で自作の価値がある所(genuine gap)

1. **MuJoCo ネイティブの sim 視覚**: evis は MuJoCo 内に居る。両眼視点の RGB/depth/segmentation は
   **シミュ内なら ground-truth で無料**に取れる(実センサ前提の ROS2 スタックの外)。
   「evis の目からのレンダリング → 知覚 → 制御ループ」の bridge は OSS に無い app 固有部品。
2. **視覚駆動行動の honest 評価**: 「箸で摘めたか/歩行が本物か(滑り/ダイブでないか)」を
   sim ground-truth と突き合わせて正直に測る評価器(CONSUMER_APPLICATIONS.md の線)。app 固有。
3. **locomotion のバランス知覚**(support polygon/COM margin/gait)は部分的にギャップだが制御寄り
   (OCS2/TOWR 等の枠組みが既にある)。

## 含意(推奨・要ユーザー承認)

- 知覚プリミティブの新規手実装は**止める**(PCL/grid_map/OpenCV の再発明)。
- evis 視覚の本命 = **MuJoCo sim 視覚 bridge + honest 評価**(OSS に無い app 層)。
  既存の numpy 知覚 op は、必要なら PCL/grid_map/OpenCV の**薄い wrapper**に置換 or それらを直接使う。
- ここから先の実装対象は、この gap 表の `genuine gap` 行にのみ投資する。

## Sources(ROS2 実地調査)

- perception_pcl / PCL(ROS2 point cloud 標準): <https://github.com/ros-perception/perception_pcl> ・ <https://index.ros.org/p/pcl_ros/>
- ANYbotics grid_map(脚ロボ elevation/foothold/traversability): <https://github.com/ANYbotics/grid_map> ・ traversability: <https://github.com/leggedrobotics/traversability_estimation>
- image_pipeline / stereo_image_proc / depth_image_proc: <https://docs.ros.org/en/rolling/p/image_pipeline/>
- 6-DoF pose / grasp(GPD + MoveIt、frontier=deep): <https://arxiv.org/pdf/2312.03345>
