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

## 可視化層(RViz2 指摘を反映 — Studio の忠実性参照)

これまでの表はアルゴリズム(PCL/OpenCV/grid_map/MoveIt2)偏重で、**「見て確かめる」層**が抜けていた。
HDevelop は 2D 画像/BLOB の表示に強いが、Physical AI の視覚は **3D 表示**(点群・depth・6D pose 軸・TF 木・
grasp マーカー・elevation map)が必須。ここの ROS2 標準が **RViz2**。Fullseye Studio(HDevelop 風 IDE)が
把握・試験・実用に使えるための **可視化の忠実性/機能参照**であり、アルゴリズムではないので再実装対象ではなく
**Studio 露出(F6)の要件地図**として使う。

| 対象 | 何を見る | ROS2/OSS 標準(実使用) | fullseye での扱い |
|---|---|---|---|
| 点群 | PointCloud2 の色/強度/法線 | **RViz2** PointCloud2 display / Open3D viewer | Studio の 3D viewer 要件参照(F6)。再実装せず既存 viewer 連携 or 薄い描画 |
| depth/画像 | depth colormap, camera image | RViz2 Image/DepthCloud、`image_view` | Studio の 2D パネル(HDevelop 相当)を 3D と併置 |
| 6D pose/grasp | pose 軸・grasp 姿勢マーカー | RViz2 Pose/PoseArray/**InteractiveMarker**、`moveit_visual_tools` | ppf/grasp op の出力を Studio で軸表示(evis デバッグ核心) |
| 座標系 | TF 木・リンク相対姿勢 | RViz2 TF display | camera↔hand↔object の姿勢連鎖確認 |
| 地形 | elevation/traversability layer | RViz2 + **grid_map_rviz_plugin** | terrain op(hillco 歩行)の foothold 可視化 |

★含意: **Studio = HDevelop(2D 画像処理 IDE)+ RViz2(3D 知覚可視化)の融合**が正しい姿。evis の視覚デバッグ
(6D pose が合っているか/点群セグメントが妥当か/foothold が地形に載っているか)は 3D 可視化なしに honest に
判定できない。統一 I/F の各 op は **メタ(F3)に「Studio でどう描くか」(2D image / point cloud / pose / grid_map layer)**
を持たせ、Studio が RViz2 相当の描画を自動選択できる構造にする。

## Fullseye の目的(2026-08-17 ユーザー確認 — この分析の前提)

Fullseye = **あらゆる画像処理/視覚アルゴリズムを「スキル」として保持し即使える包括的ライブラリ**(専用 HALCON)。
**HALCON 級網羅が目標**。Fullseye Studio(HDevelop 風)= 機能を把握・試験・仕事で使う IDE。
→ この doc の ROS2 調査は **「作るな」ではなく「正しく・網羅的に・実用語彙に忠実に作る」ための忠実性/優先度の参照**。

## 正直な結論(目的に沿って訂正)

- ROS2 調査の価値 = **各アルゴリズムの正しい意味論・実用語彙・"何が標準か" の忠実性参照**、および **どの op を優先網羅すべきかの地図**。
  「PCL/grid_map/OpenCV にあるから作らない」ではない — **包括的に自作保持(自己完結 numpy)してスキル化**が目的。
- **薄い wrapper で済ます例外** = 理解も即使用性も増えない純粋な重量級依存(例: GPU 加速 SGM、deep 6D pose)。ここは OSS を呼ぶ。
- **真に止める"変な方向" = 汎用 CS(algo-c: sort/CRC/回文)**。画像処理/視覚の知見でないので fullseye の網羅対象外。
- **知覚プリミティブ(camera/stereo/pcseg/terrain/features…)は fullseye の中核**。ROS2 の PCL/grid_map/image_pipeline の
  機能セットを**網羅目標の地図として使い**、抜けている op を honest gate 付きで補完し **Studio に露出(把握・試験・実用)**。
教育・自己完結の価値はあるが、evis の視覚を「動かす」目的では、これらを手で書き直すのは
まさに「OSS で足りるものの再発明」。特に **脚ロボの terrain/foothold は grid_map、
把持の cloud→segment→pose は PCL** が実robotで使われる本命。

## OSS/ROS2 に無い = evis で自作の価値がある所(genuine gap、優先順)

1. **★筋駆動ブリッジ(関節計画 → 700 筋活性)**: MoveIt2/GPD の出力(grasp pose・関節軌道)を
   evis の 700 筋で実現する層。QP/static optimization/WBC(`reference_wbc_qp_control`)。**OSS/ROS2 に無い最重要部品**。
2. **sim ソース視覚 bridge(MuJoCo / Gazebo / Isaac Sim — ユーザー指摘 2026-08-18)**: evis の両眼視点 RGB/depth/
   segmentation は **sim 内なら ground-truth で無料**(実センサ前提の ROS2 スタックの外)。当初 MuJoCo 限定で書いたが、
   **sim ソース全般のアダプタに一般化**すべき。統一 I/F に `sim.MuJoCo` / `sim.Gazebo` / `sim.IsaacSim` を**同じ動詞**
   (`.frames()` / `.depth()` / `.intrinsics()` / `.ground_truth()`)で置き、視覚 op が入力元を問わず組めるようにする。
   役割の違い =
   - **MuJoCo/MJX**: evis/hillco の**物理エンジン本体**(700 筋・箸・歩行が実走)。app の中核・変えない。
   - **Gazebo(Ignition)**: **ROS2 標準シム**。ros2_control / RViz2 / センサープラグイン(camera/depth/lidar→`sensor_msgs`)
     と直結 = 統一 I/F を **ROS2 実配線**で検証できる入口。
   - **Isaac Sim(NVIDIA Omniverse)**: GPU・フォトリアル・**合成データ生成 + ドメインランダム化**(RTX 5090 が活きる)。
     GPU 深層知覚は **Isaac ROS**(deep stereo/DNN pose)= 既出「重量級 wrapper」枠。gap #3 の honest 評価と特に相性。
   「evis の目 → 知覚 → 計画 → 筋実現」を閉じる sim bridge の**アダプタ契約**(F4)は app 固有だが、3 シム共通の I/F にする。
3. **視覚駆動行動の honest 評価**: 「箸で摘めたか/歩行が本物か(滑り/ダイブでないか)/6D pose が真値と合うか」を
   **sim ground-truth**(#2 の `sim.*.ground_truth()`: 真の 6D pose・segmentation・接触)と突き合わせて正直に測る
   評価器(CONSUMER_APPLICATIONS.md の線)。Isaac Sim の合成データ+ランダム化が評価データ源として本職。app 固有。
4. **locomotion のバランス知覚**(support polygon/COM margin/gait)は部分ギャップだが制御寄り(OCS2/TOWR 等あり)。

## 含意(推奨・要ユーザー承認)

★**統一インターフェース原則(ユーザー確定 2026-08-17)**: 中身が自作 numpy でも OSS ラッパでも、**使う側は
fullseye の同一 I/F(facade の op 命名・シグネチャ規約・Studio 露出・honest gate/メタ)で呼べる**こと。
OSS を使う所も素の PCL/OpenCV を直接叩かず、**fullseye 統一 I/F の裏に薄いアダプタ**として収める(= HALCON が
多様な内部実装を単一 operator 語彙で提供するのと同じ)。「スキルとして即使える」の実体はこの一貫 I/F。

fullseye の目的(包括的・即使用・スキル化・統一 I/F・Studio 実用)に沿うと、2 つの線を並行:

- **(A) ライブラリ網羅を進める** = PCL/grid_map/image_pipeline/OpenCV の機能セットを**カバレッジ地図**として使い、
  fullseye の知覚 op の抜けを honest gate 付きで補完し **Studio に露出**(把握・試験・仕事で使える形に)。
  自己完結 numpy を基本、重量級(GPU SGM/deep pose)のみ薄い wrapper。**HALCON_COVERAGE.md の 13.3% を伸ばす**のと同線。
- **(B) evis 固有の genuine gap**(OSS に無い所)= 上の優先順で、特に **#1 筋駆動ブリッジ**(視覚→MoveIt2/GPD 計画は
  OSS 参照、最後の「700 筋で実現」だけが evis 固有)、**#2 MuJoCo sim 視覚 bridge**、**#3 honest 評価**。

要確認: 今夜の自律作業を **(A) 知覚 op の網羅+Studio 露出** に充てるか、**(B) evis 筋駆動ブリッジ/sim 視覚** に充てるか。
汎用 CS(algo-c)には戻さない。

## Sources(ROS2 実地調査)

- perception_pcl / PCL(ROS2 point cloud 標準): <https://github.com/ros-perception/perception_pcl> ・ <https://index.ros.org/p/pcl_ros/>
- ANYbotics grid_map(脚ロボ elevation/foothold/traversability): <https://github.com/ANYbotics/grid_map> ・ traversability: <https://github.com/leggedrobotics/traversability_estimation>
- image_pipeline / stereo_image_proc / depth_image_proc: <https://docs.ros.org/en/rolling/p/image_pipeline/>
- 6-DoF pose / grasp(GPD + MoveIt、frontier=deep): <https://arxiv.org/pdf/2312.03345>
