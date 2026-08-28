# Fullseye Sensor Playbook — センサー種別ごとの推奨 op パイプライン

「手元のセンサーは何か」から入って、その生データを扱うのに **どの op をどの順で** 組めばよいかを引く台帳です(op の全一覧は `OP_CATALOG.md`)。

## この台帳の使い方(assistant 向け)

1. ユーザーの**センサー種別**(下の見出し)を特定する。
2. そのセクションの**パイプライン段**を上から下へ辿る。各段の op はその順で `in → out` のデータ種が繋がるように並んでいる。
3. 3D の各 op は実在レジストリ(`ops3d`)から `in → out`/説明を引いており、`ops3d.get(name)(...)` で呼べる。2D 経路は `OP_CATALOG.md` の該当カテゴリを参照。
4. 各 op の前提・退化条件は fail-closed(捏造せず例外)。GT 例は `examples_3d/` にある。
5. パイプラインは出発点であり、案件に応じて段を足し引きしてよい。

## LiDAR(3D 点群)

- **データ**: 無秩序3D点群(LAS/LAZ=laspy, PCD=pypcd4 で取り込み)。屋外・広域・疎。

### 整形・ノイズ除去
_密度を揃え外れ点を落として後段を安定化_

- `voxel_grid_downsample` (`points → points`) — 辺 voxel_size の格子で点群を間引き、各セルを重心 1 点に集約する(決定論的)。
- `statistical_outlier_removal` (`points → points`) — 各点の k 近傍平均距離が大域的に外れる点を除去する(統計的外れ値除去)。
- `radius_outlier_removal` (`points → points`) — 半径 radius 内の近傍数が min_neighbors 未満の点を除去する(孤立点除去)。

### 距離画像化(任意)
_回転式LiDARを2D距離画像に畳んで高速処理→戻す_

- `project_spherical` (`points → image2d`) — 回転式 LiDAR の球面レンジ画像へ投影 (v_res, h_res)。空セル=0, 近い点優先(最小 range)。
- `unproject_spherical` (`image2d → points`) — 球面レンジ画像 → 3D 点 (M, 3)。range>0 のセルのみをビン中心角で逆投影。
- `project_cylindrical` (`points → image2d`) — 円柱レンジ画像へ投影 (z_bins, h_res)。方位角(列)× z(行)、画素=水平半径 ρ=hypot(x,y)。

### 法線推定
_一貫向きの法線(平面/物体判定・登録の土台)_

- `estimate_oriented_normals` (`points → normals`) — PCA 法線推定 + Hoppe 大域向き付けの合成。→ (N,3) の向き付き単位法線。
- `orient_normals` (`points, normals → normals`) — Hoppe 法で法線を**大域一貫**に向き付け(MST 伝播)。→ (N,3)。

### 地面除去・クラスタリング
_地面を剥がし残りを物体クラスタへ_

- `plane_segmentation` (`points → labels`) — 反復 RANSAC で最大 max_planes 枚の平面を逐次抽出(残差点 -1)。
- `euclidean_cluster` (`points → labels`) — 半径 tol の近接グラフの連結成分で距離クラスタリング(-1=ノイズ)。
- `region_growing` (`points → labels`) — 法線類似で領域成長し連結した平滑領域へ同ラベルを付す(曲率ゲート無し変種)。

### 特徴・キーポイント
_疎な対応付け・登録のための記述子_

- `iss_keypoints` (`points → keypoints`) — ISS(Intrinsic Shape Signatures、3D Harris 相当)キーポイント検出。
- `harris3d_keypoints` (`voxel → keypoints`) — 3D Harris キーポイント検出(2D Harris コーナー検出の 3D 版)。
- `compute_fpfh` (`points, normals → descriptor`) — FPFH 記述子 (N, 3*n_bins) を計算(Rusu 2009)。

### 位置合わせ(粗→精)
_FPFHで粗合わせ→GICP/点対面ICPで精合わせ、品質を定量評価_

- `register_fpfh` (`points, points → pose`) — FPFH 記述子 + RANSAC で **初期推定なし** の剛体位置合わせ (R,t) を推定する。
- `gicp` (`points, points → pose`) — Generalized-ICP(共分散重みマハラノビス ICP)で剛体変換 (R,t) を推定する。
- `icp_point2plane` (`points, points, normals → pose`) — 点-面 ICP(Gauss-Newton, 小角近似)で剛体変換を高精度に精緻化する。
- `inlier_ratio` (`points, points → measurement`) — 対応集合の inlier 率 = ‖T·source[i] − target[i]‖ < thresh の割合。→ [0,1]。
- `registration_recall` (`points, points → measurement`) — 3DMatch 流の per-pair 登録成否 = 1.0(成功)/ 0.0(失敗)。

### バウンディング/計測
_物体の位置・向き・大きさを掴む_

- `aabb` (`points → primitive`) — Axis-aligned bounding box. Returns ``(min (3,), max (3,))``.
- `obb` (`points → primitive`) — Oriented bounding box by PCA.
- `min_enclosing_sphere` (`points → primitive`) — 点群 (N,3) → 全点を含む(近似)最小包含球 {center(3), radius}。
- `convex_hull` (`points → mesh`) — Convex hull of a point set -> ``(V, F)`` with outward-oriented triangles.

### 占有地図・クリアランス
_経路計画用の占有格子と連続距離場_

- `occupancy_grid` (`points → voxel`) — 点群 (N,3) → 3-D 占有ボクセル格子 (res,res,res) bool(点の落ちた voxel を占有)。
- `esdf` (`voxel → sdf`) — 占有格子 → Euclidean 符号付き距離場 (ESDF)(外=+ 最近占有まで, 内=- 最近自由まで)。
- `inflate` (`voxel → voxel`) — 障害物を ``radius``(world 単位)膨張した占有格子 bool(= ESDF<=radius を占有)。
- `query_distance` (`sdf, points → measurement`) — 任意 world 座標 (M,3) での ESDF 値 (M,) を返す(``mode``='trilinear' 補間 or 'nearest')。

### 動体(2時刻)
_シーンフローと剛体運動の分割_

- `nearest_neighbor_flow` (`points, points → flow`) — 各点 pts0 から pts1 の最近傍への 3-D 変位ベクトル場 (N, 3) を返す。
- `rigid_flow` (`points, points → pose`) — pts0 -> pts1 を説明する単一剛体運動を最近傍対応 + Kabsch(ICP 風)で推定。
- `smooth_flow` (`points, points → flow`) — 最近傍フローを近傍平均で局所平滑化した正則化フロー (N, 3) を返す。
- `segment_rigid_motions` (`points, points → labels`) — 2 点群を運動が一致する剛体ごとに分割する(反復 RANSAC による multi-body 分割)。

## 深度カメラ / ToF / RGB-D(整列深度)

- **データ**: 格子状(organized)の深度画像+任意RGB。屋内・近接・密。

### 点群化・法線
_深度→3D点、格子を活かした高速法線_

- `depth_to_organized_points` (`depth → points`) — organized 深度画像 → 格子整列 3D 点 (H,W,3)。
- `depth_to_points` (`depth → points`) — 深度マップ(2.5D)→ point cloud(ピンホール逆投影)。depth 行を全手法へ接続。
- `normals_from_depth` (`depth → normals`) — organized 深度 → 向き付き単位法線 (H,W,3)。隣接画素の 3D 点の外積(格子構造を利用、O(HW))。

### デノイズ・穴埋め
_段差を跨がず平滑化、欠測を補間_

- `bilateral_filter_depth` (`depth → depth`) — 深度画像の bilateral filter(段差保存デノイズ)。→ float64 (H,W)。
- `joint_bilateral` (`depth, image2d → depth`) — joint / cross bilateral: 平滑対象は depth、range 重みは guide の差で作る。→ float64 (H,W)。
- `fill_holes` (`depth → depth`) — 無効画素(穴)を近傍有効画素から調和(ラプラス)緩和で補間。→ float64 (H,W)。

### 遮蔽エッジ
_手前/奥の段差を検出(物体境界)_

- `occlusion_edges` (`depth → image2d`) — 深度の不連続(前景/背景境界 = 遮蔽エッジ)を検出。→ bool HxW。
- `bearing_angle_image` (`depth → image2d`) — bearing-angle 画像: 走査方向に沿った視線と局所面のなす角(range image の古典記述子)。→ HxW(度)。

### 平面・物体分離
_台面除去とビンピッキングの物体分離_

- `plane_segmentation` (`points → labels`) — 反復 RANSAC で最大 max_planes 枚の平面を逐次抽出(残差点 -1)。
- `euclidean_cluster` (`points → labels`) — 半径 tol の近接グラフの連結成分で距離クラスタリング(-1=ノイズ)。

### 多視点融合・表面
_複数深度をTSDFへ融合し表面メッシュを抽出_

- `tsdf_from_depth` (`depth → sdf`) — 深度マップ(2.5D)→ TSDF volume(RGB-D 再構成の標準表現)。depth→TSDF 変換。
- `fuse` (`depth → sdf`) — 深度列を new_volume + integrate で 1 つの TSDF volume に融合。返り値 (tsdf, weight)。
- `integrate` (`sdf, depth → sdf`) — 深度 1 枚を投影的 TSDF で volume に統合(in-place、重み付き移動平均)。
- `extract_surface_points` (`sdf → points`) — TSDF ゼロ交差から表面点 (M,3) を抽出(marching cubes 不要、線形補間)。
- `voxel_to_mesh` (`voxel → mesh`) — voxel → mesh(marching cubes、skimage)。返り値 (verts, faces, normals)。voxel→mesh 変換。

### メッシュ後処理
_非収縮平滑化・軽量化・法線/面積計測_

- `taubin_smooth` (`mesh → mesh`) — Taubin λ|μ フィルタによる **非収縮** 平滑化。→ (verts, faces)。
- `decimate_qem` (`mesh → mesh`) — Quadric-error-metric edge-collapse decimation toward *target_faces*.
- `vertex_normals` (`mesh → normals`) — 三角形メッシュの**頂点法線**(面積重み付きで集約した単位法線)。→ (N,3)。
- `mesh_area` (`mesh → measurement`) — 三角形メッシュの**表面積**(全三角形面積の総和)。→ float。

## ステレオカメラ(2枚→深度)

- **データ**: 既知/未知基線の2画像。対応点から深度・姿勢。

### 相対姿勢
_対応点から基礎/基本行列→相対R,t_

- `fundamental_8point` (`image2d, image2d → matrix`) — 正規化 8 点法で基礎行列 F を推定(rank-2 強制)。→ F (3,3)。8 点以上必要。
- `essential_8point` (`image2d, image2d → matrix`) — 対応点 + K から本質行列 E を直接。→ E (3,3)。
- `recover_pose` (`image2d, image2d → pose`) — 対応点 + K から相対姿勢 (R,t) と 3D 構造を復元(cheirality で一意化)。→ (R, t_unit, points3d)。
- `sampson_distance` (`image2d, image2d → measurement`) — エピポーラ拘束の Sampson 距離(1 次幾何誤差、各対応)。→ (N,)。

### 深度(平面掃引)
_深度平面を掃引しphoto-consistency最小で深度_

- `plane_sweep_depth` (`image2d, image2d → depth`) — plane-sweep stereo で密な深度マップを推定。→ (H,W) depth。
- `warp_by_plane` (`image2d → image2d`) — homography H で img を逆ワープ。→ out[y,x] = img(H·(x,y,1))(bilinear)。

### 三角測量
_対応点+姿勢から3D点を復元_

- `triangulate` (`image2d, image2d → points`) — DLT 三角測量: 2 視点の対応点 + 射影行列 → 3D 点。→ (N,3)。

### 姿勢・精緻化
_PnPで姿勢→再投影誤差最小でバンドル調整_

- `pnp_ransac` (`points, image2d → pose`) — 外れ値に頑健な PnP(RANSAC + 最終 DLT リフィット)。→ (R, t, inlier_mask, info)。
- `dlt_pose` (`points, image2d → pose`) — DLT で 3D-2D 対応からカメラ姿勢を復元(K 既知)。→ (R (3,3), t (3,))。6 点以上必要。
- `reprojection_error` (`points, pose → measurement`) — 再投影誤差(RMS ピクセル)。姿勢の当てはまり評価。→ scalar。
- `bundle_adjust` (`pose, points → pose`) — 再投影誤差最小でカメラ姿勢と 3D 点を同時最適化。→ dict{cameras, points, rmse, cost}。

## 構造化光(縞投影)

- **データ**: 位相シフト/グレイコード縞を投影した複数画像。高精度形状。

### 縞合成(検証/生成)
_既知形状から縞画像を合成しGT検証_

- `synthesize_fringes` (`image2d → images`) — 既知の height map から N-step 位相シフト縞画像列を合成する(テスト/サンプル生成用)。

### 位相復元
_包み位相→アンラップ→絶対位相→高さ_

- `wrapped_phase` (`images → image2d`) — N-step 位相シフト縞画像から wrapped phase (-π, π] を求める。
- `unwrap_phase_2d` (`image2d → image2d`) — wrapped phase を skimage.restoration.unwrap_phase で連続位相に展開する。
- `graycode_decode` (`images → image2d`) — Gray code ビット画像列 → 整数フリンジ次数マップ(絶対次数)。
- `decode_fringe` (`images → depth`) — 位相シフト画像列を一括復号: wrapped → unwrap →(参照減算で)高さ。

### 3D化
_高さ→点群→メッシュ_

- `depth_to_points` (`depth → points`) — 深度マップ(2.5D)→ point cloud(ピンホール逆投影)。depth 行を全手法へ接続。
- `voxel_to_mesh` (`voxel → mesh`) — voxel → mesh(marching cubes、skimage)。返り値 (verts, faces, normals)。voxel→mesh 変換。
- `poisson_lite` (`points → mesh`) — 点群 (N,3) → (vertices(V,3), faces(F,3)) の表面メッシュ(スクリーンド Poisson 軽量近似)。

## フォトメトリックステレオ(多光源)

- **データ**: 同一視点・複数の既知光源方向で撮った輝度画像群。微細凹凸。

### 法線復元
_陰影群から画素ごとの法線_

- `photometric_stereo` (`images → normals`) — Lambertian フォトメトリックステレオ: 既知光源方向の N 枚から法線とアルベドを復元。→ (normals HxWx3, albedo HxW)。
- `surface_normals` (`image2d → normals`) — 高さ場 z(HxW)→ 単位法線 (H,W,3)。n ∝ (-dz/dx, -dz/dy, 1)。深度→法線の順変換。

### 高さ積分
_法線場を積分して高さ場へ_

- `integrate_normals` (`normals → image2d`) — 法線場 → 高さ場 z を Frankot-Chellappa 積分。→ z HxW(定数分の自由度あり・平均0基準)。

### 順方向モデル(検証)
_法線+光源→輝度の順レンダで逆問題を検証_

- `render_lambertian` (`normals → image2d`) — 法線 + アルベド + 光源方向 → Lambertian 画像(検査サンプル生成 / GT 検証 / 逆レンダの順方向)。→ HxW。

## CT / ボリューム(医用・産業X線)

- **データ**: 3Dスカラーボリューム(DICOM/NIfTI/NRRD/TIFF=SimpleITK/tifffile)。断層積層。

### 前処理(モルフォロジ)
_空洞埋め・トゲ除去・境界殻抽出_

- `morph_dilate3d` (`voxel → voxel`) — 3D グレースケール dilation(cube SE 半径 r の局所 max)。明領域を膨張。
- `morph_erode3d` (`voxel → voxel`) — 3D グレースケール erosion(cube SE の局所 min)。明領域を収縮。
- `morph_gradient3d` (`voxel → voxel`) — 3D モルフォロジー勾配 = dilation − erosion。**境界/表面**を抽出(sobel 代替のエッジ源)。
- `morph_tophat3d` (`voxel → voxel`) — 3D white top-hat = vol − opening。SE より小さい **明構造**を抽出(keypoint 前処理)。

### セグメント・計数
_連結成分で分離・計測、接触物体はwatershedで割る_

- `label_components` (`voxel → voxel`) — 3D 二値ボリュームを連結成分にラベリングする。
- `region_props` (`voxel → measurement`) — 各連結成分のリージョンプロパティ一覧を返す。
- `filter_by_volume` (`voxel → voxel`) — min_voxels 未満の連結成分を除去した bool マスクを返す。
- `largest_component` (`voxel → voxel`) — 最大(最多ボクセル)連結成分の bool マスクを返す。
- `vol_watershed` (`voxel → labels`) — Marker-controlled 3-D watershed segmentation (**optional — scikit-image**).

### エッジ・骨格・距離
_境界抽出・距離場・中軸骨格_

- `canny3d` (`voxel → voxel`) — 3D Canny エッジ検出(非最大抑制 + ヒステリシス)。
- `log_zero_crossings` (`voxel → voxel`) — Laplacian-of-Gaussian のゼロ交差エッジ。
- `edge_points` (`voxel → points`) — エッジ mask を (M,3) の座標点群にする(下流の chamfer / Hough 用)。
- `signed_distance_field` (`voxel → sdf`) — occupancy/密度 voxel → 符号付き距離場 SDF(内側<0・外側>0)。edt_jfa を両側に。
- `skeletonize_vol` (`voxel → voxel`) — 3D バイナリ voxel を細線化して 1 voxel 幅の骨格に。skimage の Lee(1994)法ラッパ。
- `medial_axis_points` (`voxel → points`) — medial voxel の座標と局所半径(= その点の EDT 値)を点群化。返り値 (points, radius)。

### 表面抽出・後処理
_marching cubesで表面化→軽量化・平滑化・曲率/面積計測_

- `voxel_to_mesh` (`voxel → mesh`) — voxel → mesh(marching cubes、skimage)。返り値 (verts, faces, normals)。voxel→mesh 変換。
- `decimate_qem` (`mesh → mesh`) — Quadric-error-metric edge-collapse decimation toward *target_faces*.
- `taubin_smooth` (`mesh → mesh`) — Taubin λ|μ フィルタによる **非収縮** 平滑化。→ (verts, faces)。
- `vertex_curvature` (`mesh → curvature`) — 三角形メッシュの各頂点の**平均曲率の大きさ**(mean curvature magnitude)。→ (N,)。
- `mesh_area` (`mesh → measurement`) — 三角形メッシュの**表面積**(全三角形面積の総和)。→ float。

### 形状計測
_不変量・慣性・プリミティブ当てはめで寸法照合_

- `moment_invariants` (`points → descriptor`) — 並進+回転+スケール不変な形状特徴ベクトル(Sadjadi–Hall 流 + 高次半径分布)。
- `principal_moments` (`points → descriptor`) — 慣性テンソルの固有値(主慣性モーメント、降順ソート、回転不変)。
- `inertia_tensor` (`points → matrix`) — 点群の慣性テンソル (3,3)(中心 2 次モーメントから、等質量・総質量 1)。
- `fit_cone` (`points → primitive`) — 点群に無限円錐を当てはめ ``{apex, axis, half_angle, residual}`` を返す。
- `fit_torus` (`points → primitive`) — 点群にトーラスを当てはめ ``{center, axis, R, r, residual}`` を返す。
- `fit_ellipsoid` (`points → primitive`) — 点群に任意姿勢の 3 軸楕円体を代数フィットし ``{center, axes, radii, residual}`` を返す。

## 単眼カメラ / SfM(複数視点→3D)

- **データ**: 1台のカメラで動かし撮った画像列。対応点から構造と運動。

### 2視点初期化
_最初の2枚で姿勢と初期点群_

- `fundamental_8point` (`image2d, image2d → matrix`) — 正規化 8 点法で基礎行列 F を推定(rank-2 強制)。→ F (3,3)。8 点以上必要。
- `essential_8point` (`image2d, image2d → matrix`) — 対応点 + K から本質行列 E を直接。→ E (3,3)。
- `recover_pose` (`image2d, image2d → pose`) — 対応点 + K から相対姿勢 (R,t) と 3D 構造を復元(cheirality で一意化)。→ (R, t_unit, points3d)。
- `triangulate` (`image2d, image2d → points`) — DLT 三角測量: 2 視点の対応点 + 射影行列 → 3D 点。→ (N,3)。

### 姿勢追加(PnP)
_既知3D点に新規画像を PnP で結合_

- `pnp_ransac` (`points, image2d → pose`) — 外れ値に頑健な PnP(RANSAC + 最終 DLT リフィット)。→ (R, t, inlier_mask, info)。
- `reprojection_error` (`points, pose → measurement`) — 再投影誤差(RMS ピクセル)。姿勢の当てはまり評価。→ scalar。

### 大域最適化
_全姿勢+構造をバンドル調整、ループはポーズグラフで_

- `bundle_adjust` (`pose, points → pose`) — 再投影誤差最小でカメラ姿勢と 3D 点を同時最適化。→ dict{cameras, points, rmse, cost}。
- `optimize_pose_graph` (`pose → pose`) — 相対姿勢制約 + ループ閉じから大域姿勢を最適化。→ dict{poses, rmse, cost}。
- `relative_pose` (`pose, pose → pose`) — T_i⁻¹ ∘ T_j = i←j の相対姿勢。pose_* = [rvec|t] (6,)。→ (rvec_ij (3,), t_ij (3,))。

### 2D特徴(対応点の素)
_コーナー/記述子など2D特徴で対応点を作る(詳細=OP_CATALOG.md)_

- 2D: **features(71)** カテゴリ(詳細は OP_CATALOG.md)
- 2D: **edges(57)** カテゴリ(詳細は OP_CATALOG.md)
- 2D: **matching(2)** カテゴリ(詳細は OP_CATALOG.md)

## マルチビュー / シルエット(visual hull・3DGS)

- **データ**: 複数の既知視点画像/シルエット、または3D Gaussian。

### シルエット彫刻
_多視点シルエットからvisual hullを彫る_

- `synthesize_silhouette` (`points → image2d`) — 3-D 点群を (K,R,t) カメラへ射影し占有画素 True のシルエット(H,W bool)を返す。
- `carve` (`images → voxel`) — bounds を res^3 voxel に離散化し、全シルエット内に射影される voxel を残す(空間彫刻)。
- `visual_hull` (`images → voxel`) — 多視点シルエットの visual hull を voxel 占有として返す(:func:`carve` の別名)。

### 平面掃引深度
_既知視点群からの密深度_

- `plane_sweep_depth` (`image2d, image2d → depth`) — plane-sweep stereo で密な深度マップを推定。→ (H,W) depth。

### Gaussian→体積
_3DGSを占有体積化→メッシュ(gsplat 訓練/描画は gsplat_* モジュール)_

- `gaussians_to_voxel` (`gaussians → voxel`) — 3DGS(異方性ガウス)→ 密度 voxel。各ガウスを means に opacity で置き、平均 scale で平滑。
- `voxel_to_mesh` (`voxel → mesh`) — voxel → mesh(marching cubes、skimage)。返り値 (verts, faces, normals)。voxel→mesh 変換。

## エリアカメラ(2D 産業検査)→ 必要なら3D連携

- **データ**: GigE/CoaXPress/Camera Link のエリアスキャン画像(2D)。外観検査の主戦場。

### 2D 前処理・強調
_平滑化・復元・階調/周波数/色変換(詳細=OP_CATALOG.md)_

- 2D: **smoothing(48)** カテゴリ(詳細は OP_CATALOG.md)
- 2D: **filtering** カテゴリ(詳細は OP_CATALOG.md)
- 2D: **restoration(12)** カテゴリ(詳細は OP_CATALOG.md)
- 2D: **gray(41)** カテゴリ(詳細は OP_CATALOG.md)
- 2D: **frequency(19)** カテゴリ(詳細は OP_CATALOG.md)
- 2D: **color(8)** カテゴリ(詳細は OP_CATALOG.md)

### 検出・領域・輪郭
_エッジ/領域/輪郭/形態で欠陥・部品を抽出_

- 2D: **edges(57)** カテゴリ(詳細は OP_CATALOG.md)
- 2D: **segmentation(56)** カテゴリ(詳細は OP_CATALOG.md)
- 2D: **region(76)** カテゴリ(詳細は OP_CATALOG.md)
- 2D: **contour(26)** カテゴリ(詳細は OP_CATALOG.md)
- 2D: **morphology(33)** カテゴリ(詳細は OP_CATALOG.md)

### 特徴・計測・照合
_特徴量・寸法・テクスチャ・テンプレート照合(サブピクセル)_

- 2D: **features(71)** カテゴリ(詳細は OP_CATALOG.md)
- 2D: **measure1d(5)** カテゴリ(詳細は OP_CATALOG.md)
- 2D: **texture(22)** カテゴリ(詳細は OP_CATALOG.md)
- 2D: **matching(2)** カテゴリ(詳細は OP_CATALOG.md)
- 2D: **subpix(6)** カテゴリ(詳細は OP_CATALOG.md)

### 3D幾何連携
_校正済みなら2D計測を3D幾何当てはめへ橋渡し_

- `fit_line_3d` (`points → primitive`) — 点群 → 最小二乗直線(通過点=重心, 方向=最大主軸)。返り値 (point, direction)。
- `fit_plane_3d` (`points → primitive`) — 点群 → 最小二乗平面(通過点=重心, 法線=最小主軸, 残差 RMS)。返り値 (point, normal, resid)。
- `fit_circle_3d` (`points → primitive`) — 点群 → 3D 円(平面フィット → 面内で 2D 円フィット)。返り値 (center, radius, normal)。
- `fit_sphere_3d` (`points → primitive`) — 点群 → 最小二乗球(代数フィット)。返り値 (center, radius)。配管/ボール計測に。

## センサーシミュレーション / レンダリング(学習データ・デジタルツイン)

- **データ**: CAD/SDF/メッシュから合成センサー出力・映える静止画・学習用データを生成。

### ジオメトリ生成
_SDFのCSGで形を作りmarching cubesでメッシュ化_

- `sphere_sdf` (`points → sdf`) — 球の符号付き距離場: ``|p - center| - R``(内側負・外側正)。
- `box_sdf` (`points → sdf`) — 軸平行直方体の**厳密**な符号付き距離場(内側負・外側正)。
- `sdf_smooth_union` (`sdf, sdf → sdf`) — 滑らかに丸めた和集合(polynomial smooth-min)。``k>0`` で継ぎ目を半径 ~k で丸める。
- `sdf_subtract` (`sdf, sdf → sdf`) — 差集合 A\B = max(a, -b)(A の内側 かつ B の外側 = ``-b`` の内側)。
- `voxel_to_mesh` (`voxel → mesh`) — voxel → mesh(marching cubes、skimage)。返り値 (verts, faces, normals)。voxel→mesh 変換。

### 合成センサー出力
_深度/MIP/投影で疑似センサー画像_

- `render_point_depth` (`points → depth`) — 点群 → 深度画像(z-buffer、各画素に最近点の深度)。観測合成/外観検査サンプル。
- `render_volume_projection` (`voxel → image2d`) — voxel を任意視点で 2D 投影(mode=xray=減衰積算 / mip=最大値)。DRR(X線)・世界モデル観測。
- `project_points` (`points → image2d`) — 3D 点群 (N,3) → 画像座標 (u,v) と深度。ピンホール(depth_to_points の順方向)。

### 映える静止3D(hero)
_全品質層を合成した hero 画像(render_beauty 一発、または層を個別に)_

- `render_beauty` (`mesh → image2d`) — メッシュを全品質層合成で「映える静止 3D」1 枚に描く → RGB ``(size, size, 3)`` float [0,1]。
- `ambient_occlusion` (`mesh → image2d`) — メッシュを AO マップ画像 ``(H, W)`` [0,1] にレンダリングして返す。
- `cast_shadow` (`mesh, vector → image2d`) — メッシュのキャスト影 / ソフトシャドウを計算し、可視性マップ (H,W) ∈ [0,1] を返す。
- `phong_shade` (`normals → image2d`) — Phong 反射モデルで法線マップを陰影付け(環境光 + 拡散 + **鏡面**)。→ ``(H, W)``。
- `matcap_shade` (`normals, image2d → image2d`) — MatCap: 視空間法線を lit-sphere テクスチャに写して素材の見えを転写。→ ``(H, W[, C])``。
- `supersample_mesh` (`mesh → image2d`) — メッシュを SSAA でアンチエイリアス描画 -> float 画像 ``(H, W)`` (or ``(H, W, C)``)。
- `tonemap_reinhard` (`image2d → image2d`) — Reinhard トーンマップで HDR を ``[0, 1]`` の LDR へ圧縮。→ float64、入力と同形状。
- `tonemap_aces` (`image2d → image2d`) — ACES filmic 近似(Narkowicz 2015)で HDR を ``[0, 1]`` の LDR へ圧縮。→ float64。

### 学習データ拡張
_点群/ボリュームの拡張で頑健性を上げる_

- `jitter` (`points → points`) — 各点に等方ガウスノイズ ``N(0, sigma)`` を付加(センサ位置ノイズの模倣)。
- `random_rotation` (`points → points`) — ランダム回転を適用し ``(rotated, R)`` を返す(視点変化の模倣)。
- `random_scale` (`points → points`) — 一様スケール ``s ~ U(lo, hi)`` を原点まわりに適用し ``(scaled, s)`` を返す。
- `random_dropout` (`points → points`) — 点の ``ratio`` 割合をランダム除去し ``(kept, kept_idx)`` を返す(欠損の模倣)。
- `elastic_deform` (`points → points`) — 滑らかな乱数変位場で弾性変形(相関距離 ``sigma``, RMS 振幅 ``alpha``)。
- `cutout` (`points → points`) — 空間的な軸平行ボックス領域を除去し ``(kept, kept_idx)`` を返す(局所欠損の模倣)。

## センサーシミュレーション・デモ(走る例スクリプト)

- `bin_pick.py` — ビンピッキング(乱雑箱→把持)
- `stereo_sim.py` — ステレオ撮像シミュレーション
- `focus_stack.py` — 焦点合成(被写界深度合成)
- `polar_cam.py` — 偏光カメラ
- `event_camera.py` — イベントカメラ(DVS)
- `pick_render.py` — ピッキング動作レンダ

