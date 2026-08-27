# fullseye 3D op × op 組み合わせマトリクス(実現性 × 差別化で優先度化)

**核心**: 150 個の 3D op(`ops3d.py` レジストリ、31 カテゴリ)は、出力種別 = 別 op の入力種別が合えば連結できる。
型整合な op→op 連結は **2,843 通り(2 段、`ops3d.compatible()` 実測)**、3 段以上で **指数的**に増える
(第2〜5波で photometric/range_image/preprocess/structured_light/deform/medial/metrics/robust_fit/edges/
reconstruct/curve/shape_descriptor/freeform/pose_estimation/regionprops の 15 モジュール・68 op を追加し、
82 op/16 カテゴリ→150 op/31 カテゴリへほぼ倍増)。この空間から
**実現しやすさ(F: 1–5)× 差別化(D: 1–5)= 優先度スコア** で手を付ける順を決める。

スコア規準:
- **F(実現性)**: 5=既存 op を連結するだけ / 4=薄い接着コード / 3=中規模の新 op 1 つ / 2=重い新規実装 / 1=研究要素。
- **D(差別化)**: 5=HALCON/OpenCV に無い(特に GPU 3D・Physical AI・合成ループ)/ 3=あるが 3D/GPU で優位 / 1=既存で十分。
- **状態**: ✅=検証済パイプライン既存 / ○=接着すれば即 / △=新 op 要。

## 優先度上位(F×D 降順)

| # | op チェーン | 何ができる | F | D | 優先 | 状態 |
|---|---|---|---|---|---|---|
| 1 | `mesh_to_points → register_fpfh → icp_point2plane` | **CAD mesh vs 点群スキャン整合**(Physical AI の基盤) | 5 | 5 | 25 | ✅ fuse3d |
| 2 | `estimate_point_normals → compute_fpfh → register_fpfh → icp` | 初期推定なし点群大域登録(no-init 60°) | 4 | 5 | 20 | ✅ feat_fpfh |
| 3 | `signed_distance_field → match_shape_3d` | **SDF ベース照合**(滑らか・遮蔽頑健、cv2/HALCON 手薄) | 5 | 4 | 20 | ○ |
| 4 | `hough_plane_3d → distance_point_plane / surface_form_error` | **平面度/形状誤差メトロロジー**(検出→計測) | 5 | 4 | 20 | ○ |
| 5 | `scene_flow_lk → 変形/歪み measurement` | **非剛体・変形トラッキング**(3D flow は競合少) | 4 | 5 | 20 | ○ |
| 6 | `render_volume_projection / render_shaded → 既知 GT` | **合成サンプル生成**(検査学習・3D 計測サンプル空間) | 5 | 4 | 20 | ✅ render |
| 7 | `render_volume_projection(xray=DRR) → match_shape_3d(2D)` | **X 線/CT 検査マッチング**(産業 CT) | 4 | 4 | 16 | ○ |
| 8 | `curvature_maps → harris3d_keypoints` | **曲率顕著 keypoint**(形状で頑健な特徴点) | 4 | 4 | 16 | ○ |
| 9 | `reflect + render_shaded → 検査画像` | **鏡面/スペキュラの外観サンプル合成** | 4 | 4 | 16 | ○ |
| 10 | `fit_zernike → descriptor 照合` | **波面/レンズ収差の分類**(光学検査) | 4 | 4 | 16 | ○ |
| 11 | `match_hough_3d(topk) → 各体を refine_peak_newton` | **複数インスタンス検出→個別サブボクセル** | 4 | 4 | 16 | ○ |
| 12 | `fuse_to_voxel(depth×N 多視点) → register/match` | **多視点フュージョン → 統合照合** | 4 | 4 | 16 | ✅ fuse3d |
| 13 | `tsdf_from_depth → voxel_to_mesh` | **RGB-D 再構成**(KinectFusion 系) | 5 | 3 | 15 | ○ |
| 14 | `polar_unwrap → match_shape_3d(2D)` | **回転体/リング検査**(θ 展開で直線化) | 5 | 3 | 15 | ○ |
| 15 | `hough_sphere_3d → fit_sphere_3d → 残差` | **真球度/球状部品計測** | 5 | 3 | 15 | ○ |
| 16 | `refract → render` | **透明体(ガラス/レンズ)の像歪み合成** | 3 | 5 | 15 | ○ |
| 17 | `morph_tophat3d → harris3d / hough_3d` | **微小欠陥・突起の検出**(前処理で顕在化) | 4 | 3 | 12 | ○ |
| 18 | `voxel_to_mesh → mesh_to_points → register_fpfh` | **voxel↔mesh 異種登録** | 5 | 3 | 15 | ✅ fuse3d |
| 19 | `match_logpolar_z → refine_rotation_z` | 回転粗→精(±3°→0.01°) | 5 | 3 | 15 | ✅ 粗精 |
| 20 | `edt_jfa → medial surface → 位相照合` | **骨格/medial 照合**(位相不変) | 2 | 4 | 8 | △ TODO |
| 21 | `render_* + autograd → 逆問題` | **微分可能レンダ**(姿勢/形状の逆推定・世界モデル学習) | 2 | 5 | 10 | △ TODO |

### 第2〜5波(15 モジュール追加)で開く新チェーン

| # | op チェーン | 何ができる | F | D | 優先 | 状態 |
|---|---|---|---|---|---|---|
| 22 | `photometric_stereo → integrate_normals → surface_form_error` | **既知光源の複数画像→法線→高さ場→形状誤差**(鏡面/微細凹凸検査、Frankot-Chellappa 積分まで閉形式) | 5 | 4 | 20 | ○(前半 2 hop は✅ test_photometric) |
| 23 | `depth_to_organized_points ⊕ normals_from_depth → compute_fpfh → register_fpfh` | **RGB-D ネイティブな疎点群大域登録**(視点符号確定の organized 法線 + FPFH、depth カメラ直結) | 4 | 4 | 16 | ○ |
| 24 | `ransac_plane → distance_point_plane` | **外れ値頑健な平面度計測**(RANSAC で外れ値を捨ててから測る、match3d の最小二乗当てはめより頑健) | 5 | 4 | 20 | ○ |
| 25 | `edge_points(edges3d) → [順序付け] → curvature_torsion(curve3d)` | **3D エッジ→曲線微分幾何**(voxel Canny で抽出したシーム/エッジ点列を並べ直し曲率・捩率でシーム計測) | 3 | 5 | 15 | △ 要順序付けグルー |
| 26 | `poisson_lite(recon3d) → mesh_to_points(transform) → chamfer_distance(metrics3d)` | **再構成品質を GT 点群比較で数値化**(点群→近似再構成メッシュ→chamfer、進化探索の評価にも転用可) | 5 | 4 | 20 | ○ |
| 27 | `decode_fringe(structured_light) → depth_to_organized_points → fit_plane_3d → distance_point_plane` | **縞投影(fringe projection)profilometry の全経路**(位相復号→高さ→organized 点群→平面適合→平面度、産業3Dスキャン検査を閉ループ化) | 4 | 5 | 20 | ○ |
| 28 | `register_nonrigid(deform3d) → rmse_correspondence(metrics3d)` | **非剛体位置合わせの残差を定量評価**(TPS 非剛体 ICP の変形追跡精度を GT 点群 RMSE で保証) | 5 | 5 | 25 | ○ |
| 29 | `pnp_ransac(pnp3d) → reprojection_error(pnp3d)` | **PnP-RANSAC 姿勢推定の再投影誤差評価**(pnp_ransac は inlier 集合で内部計算済、任意対応集合への外部適用や合成 GT 検証にも) | 5 | 2 | 10 | ✅ pnp3d(内部で既に連結・計算済) |
| 30 | `label_components(regionprops3d) → region_props(regionprops3d)` | **多物体を一括連結成分計測**(体積/重心/主軸/真球度、CT・検査で複数部品を同時計測) | 5 | 3 | 15 | ✅ regionprops3d |
| 31 | `medial_axis_points(medial) → icp_point2point_3d(match3d)` | **骨格点まで削減してから ICP 粗合わせ**(密な voxel を疎な medial 点に圧縮、位相不変な軽量プリアライン) | 4 | 5 | 20 | ○ |
| 32 | `chamfer_distance / fscore / medial_match → op-chain 探索の fitness` | **進化探索の fitness 土台**(閉形式・GT 検証済のメトリクスをそのまま fitness にし、op-chain 空間を imgevolve の進化ループで自動探索する収束ステップの基盤) | 3 | 5 | 15 | ○(evolve.py への 3D 版接続が要件) |
| 33 | `statistical_outlier_removal → voxel_grid_downsample → mls_smooth(pcl_filter) → poisson_lite(recon3d)` | **点群クリーンアップ→再構成の実務パイプライン**(外れ値除去→間引き→MLS 平滑→Poisson 近似で生スキャンから即使えるメッシュへ) | 5 | 3 | 15 | ○ |
| 34 | `dlt_pose / pnp_ransac(pnp3d) → pose_error(metrics3d)`(既知姿勢の合成 GT ループ) | **姿勢推定精度を合成 GT で検証**(既知姿勢→投影→PnP 復元→pose_error、AR/hand-eye 較正のテスト基盤) | 4 | 4 | 16 | ○ |
| 35 | `describe(descriptors3d) → shape_distance(descriptors3d)` | **統計的形状記述子で検索/分類**(回転・スケール不変、メッシュ化・法線推定不要で疎/欠損点群にも頑健) | 5 | 3 | 15 | ✅ descriptors3d(test_rotation_invariance_describe で連結検証済) |
| 36 | `fit_bspline_surface(bspline_surf) → surface_residual(bspline_surf)` | **多項式を超えた自由曲面の逸脱量計測**(B スプライン当てはめ→残差、平面度/球面度を超えた自由形状検査) | 5 | 4 | 20 | ✅ bspline_surf |

## カテゴリ間連結(どの出力→どの入力が多いか、型整合上位)
`geometry→geometry`(55, 計測の連鎖)/ `transform→*`(構造変換が全 op の入口)/ `morphology→match_localize`(前処理→照合)/
`transform→feature_register`(点群化→疎登録)。→ **transform(変換グラフ)が全連結のハブ**、geometry が計測の終端。

## 運用(今後の進め方)
1. `ops3d.compatible(name)` で後続候補を機械列挙 → 上表の規準で F/D 採点 → 優先度順に着手。
2. **○(接着で即)を先に刈り取る**(F5×D4 群 = #3,4,6 等)。△(新 op 要)は差別化が高いもの(#21)を選抜。
3. op を足すたびに `ops3d._CATALOG` に登録 → 組み合わせ空間が自動で広がる(指数的候補が増える)。
4. コードレビュー/検証は数回に分割(Fable リセット後に全 op 再確認予定)。

## 現状の op 在庫(`ops3d.py`、82 op / 16 カテゴリ)
transform 12 / geometry 15 / feature_register 7 / match_localize 6 / refine 6 / optics 5 / morphology 5 /
render 4 / surface_fit 4 / feature 4 / match_pose 4 / curvilinear 3 / detect 2 / describe 2 / fusion 2 / motion 1。
