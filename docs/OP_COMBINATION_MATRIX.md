# fullseye 3D op × op 組み合わせマトリクス(実現性 × 差別化で優先度化)

**核心**: 82 個の 3D op(`ops3d.py` レジストリ)は、出力種別 = 別 op の入力種別が合えば連結できる。
型整合な op→op 連結は **721 通り(2 段)**、3 段以上で **指数的**に増える。この空間から
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
