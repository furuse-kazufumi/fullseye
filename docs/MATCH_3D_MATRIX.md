# fullseye 3D マッチング・マトリクス(データ構造 × 2D 手法 × データ変換)

3D の対象マッチングを **「入力データ構造」×「2D で確立した手法」** の格子で体系化し、両者を繋ぐ
**データ変換**(splat / 投影 / FFT / 勾配場 / 距離場 / PCA 正準化)で網羅的に増やす。核心思想:
**多くの 3D 手法は「3D データを、既知の 2D 手法が効く表現へ変換する」ことで作れる。**

差別化根拠: cv2 に 3D matchTemplate は無く、HALCON も 3D は表面/形状ベースに限られる。**GPU voxel マッチング一式**はツールとして空いている(RTX5090、torch cu128)。

## 手法列(2D で確立 → 3D へ持ち上げる)。★=TRIZ 原理17(多次元化)/ 線→面リフト
| 手法 | 2D の出自 | 3D 化の要点 | 変換 |
|---|---|---|---|
| **NCC / template** | 正規化相互相関 | conv3d + box3d 正規化 | (直接) |
| **shape-based / 勾配方向** | Steger / HALCON | 3D 勾配の方向相関(3 成分 conv3d) | sobel3d |
| **phase correlation** | Reddy & Chatterji | 3D FFT の相互パワースペクトル(平行移動) | FFT |
| **Fourier-Mellin / log-polar** | Reddy & Chatterji | z 投影の |FFT|→log-polar→位相相関(回転+スケール) | FFT→log-polar |
| **chamfer / 距離場** | Barrow 1977 | エッジの EDT で chamfer スコア(全 GPU=JFA) | 距離変換(GPU-JFA) |
| **moment / PCA 軸** | 主軸整列 | 慣性テンソル固有ベクトルで姿勢 | PCA 正準化 |
| **generalized Hough** | Ballard | 3D R-table 投票(向きビン相関の総和) | 勾配→投票 |
| **projection(次元削減)** | — | 直交 MIP/シルエットで 2D 手法を適用 | 3D→2D 投影 |
| ★**曲率 / shape index** | 輪郭の曲率(スカラー1) | **主曲率 κ1,κ2**(2個=曲面固有)Koenderink shape index | Hessian(2次) |
| ★**球面調和記述子** | Fourier 記述子(輪郭の1D FFT) | 曲面 SH の帯域エネルギー=**回転不変**(Kazhdan) | SH(球面 FFT) |
| **パラメトリック Hough** | Hough 直線/円 | **平面/球**を parameter 空間へ投票(テンプレ不要=RANSAC 系) | 勾配→param 投票 |
| **feature descriptor**(TODO) | Harris/SIFT | 3D corner + 記述子(spin image/FPFH/SHOT) | 局所形状 |
| **反復精緻化**(進行中) | LK / ICP / GN | 粗推定を Newton/Gauss-Newton/ICP で高精度収束 | Jacobian/Hessian |

## データ構造行(入力形式)× 変換グラフ
「3D データを手法が効く表現へ**変換**する」がマトリクスの核。形式は多様 → **変換で相互に繋ぐ**。

| 構造/形式 | 説明 | 主な変換(実装) |
|---|---|---|
| **voxel grid**(dense) | 密な格子 | 中心表現 |
| **point cloud** | 点集合 | `points_to_voxel`(splat) / `estimate_point_normals`(法線=PCA) |
| **3DGS**(異方性ガウス) | means+scale+opacity | `gaussians_to_voxel`(splat) |
| **mesh**(頂点+面) | 三角メッシュ | `mesh_to_voxel`(占有) / `mesh_to_points`(面サンプル) |
| **depth / range**(2.5D) | 深度マップ | `depth_to_points`(逆投影) / `tsdf_from_depth`(TSDF) |
| **SDF / TSDF** | 符号付き距離場 | `signed_distance_field`(voxel→SDF) / `sdf_to_occupancy` |
| **occupancy / binary** | 占有 0/1 | 閾値 ↔ voxel ↔ SDF |
| **normals**(点/面法線) | 向き | `estimate_point_normals`(FPFH/ICP-p2plane 用) |

**変換グラフ(→=実装済)**: points ⇄ voxel(splat / marching cubes)、voxel → mesh(`voxel_to_mesh`=marching cubes)、
mesh → points(`mesh_to_points`)、voxel ⇄ SDF ⇄ occupancy、depth → {points, TSDF}、3DGS → voxel、points → normals。
**任意の入力形式を共通 voxel/point/SDF へ寄せれば全手法が使える**(= 行 × 列の全セルが変換で接続)。

## 3D モルフォロジー(2D の 3D リフト。グレー & バイナリ)
`accel_vol.py`: グレー erode/dilate/median/gaussian + バイナリ region(ball/cross、opening)。
`match3d.py` 追加(前処理/特徴抽出):`morph_gradient3d`(dilation−erosion=**境界抽出**、sobel 代替)/
`morph_tophat3d`(**小明構造抽出**、keypoint 前処理)/ `morph_blackhat3d`(暗構造)/ `morph_dilate3d`/`morph_erode3d`。GPU(max_pool3d)。

## 幾何プリミティブ / メトロロジー(2点→線・3点→面/角度、2D/3D 共通)
検出/マッチを**「計測」**に変える層(HALCON 2D/3D metrology 相当)。全て閉形式・厳密検証済:
- **構成**: `line_from_2points`(2点→線)/ `plane_from_3points`(3点→面)
- **角度**: `angle_3points`(∠ABC)/ `angle_between_lines` / `angle_between_planes`(二面角)/ `angle_line_plane`
- **距離**: `distance_point_plane` / `distance_point_line` / `distance_line_line`(ねじれ位置も)
- **交差**: `intersect_line_plane`(→点)/ `intersect_planes`(→線)
- **フィッティング**(最小二乗): `fit_line_3d` / `fit_plane_3d`(法線+残差)/ `fit_sphere_3d`(中心+半径)/ `fit_circle_3d`

## マトリクス(手法モード別 × データ構造)
全 5 構造(voxel / point cloud / 3DGS / mesh / depth 2.5D)は共通 voxel/point 表現へ**変換 T**で載るので、
下の各手法はどの構造にも適用できる(= 5 構造 × 手法数のセル)。手法は「何を出すか(モード)」で整理:

**① 定位(scene 内でテンプレ位置を出す)**
| 手法 | 特徴 | GPU |
|---|---|---|
| NCC | 正規化相互相関、pyramid/sub-voxel | 46×(pyramid 244×) |
| shape-based | 勾配方向、**コントラスト不変** | 68-89× |
| chamfer | 距離場、**遮蔽頑健**、全 GPU(JFA) | N≥96 で scipy 超え |
| gen. Hough | 投票、**複数インスタンス**・遮蔽頑健 | 8× |
| ★曲率 | shape index、**強度でなく曲面形状**で一致 | 6× |
| MIP→2D | 直交投影で 2D 手法に落とす(安 coarse) | 1.3× |

**② 姿勢(回転/スケール/並進の変換パラメータを出す)**
| 手法 | 出力 | 特徴 |
|---|---|---|
| phase-corr | 並進 | テンプレ不要、FFT、18-28× |
| PCA/moment | 回転+並進 | 対応あり、残差0、0.2ms |
| Fourier-Mellin | 回転+スケール | 対応なし、30×、coarse(±45/90°別名) |

**⑤ 反復精緻化(粗推定 → 高精度収束)。手段を1つに絞らず発散(Workflow で6手法を並行検証・全PASS、統合後に一次再検証済)**
| 手法 | 収束精度(実測) | 反復/時間 | baseline 比 |
|---|---|---|---|
| Newton サブボクセルピーク `refine_peak_newton` | 0.011 voxel(全 Hessian で交差曲率) | 7 / 1.5ms | 放物線比 ~9× |
| Gauss-Newton 並進(逆合成 LK)`refine_translation_lk` | 0.008-0.023 voxel | 6 / 1.2ms | NCC-COM 比 ~60× |
| Levenberg-Marquardt 並進+スケール `refine_lm` | 並進 0.007 voxel + **スケール回復** | 4 / 6ms | COM 比 ~40-70×(スケールは新規) |
| Gauss-Newton z 回転 `refine_rotation_z` | 0.002-0.017° | 4 / 12ms | Fourier-Mellin ±3° を **~5000×** |
| ICP 点-点(Kabsch)`icp_point2point_3d` | RMSE 1e-14、Trimmed で部分重なり | 6 / 2.5ms | 粗 ±0.5vox を機械精度へ |
| ICP 点-面(GN)`icp_point2plane` | RMSE 1e-10、表面に高速収束 | 4-16 / 8ms | 点-点より少反復(Low 2004) |

**③ 検出(テンプレ不要で原始形状を出す)**
| 手法 | 出力 | 特徴 |
|---|---|---|
| パラメトリック Hough | 平面 (n,d) / 球 (c,r) | RANSAC 系、法線exact・inlier93%、4.9×/2× |

**④ 記述(回転不変な大域シグネチャで照合/検索)**
| 手法 | 出力 | 特徴 |
|---|---|---|
| ★球面調和記述子 | (半径×周波数)帯域エネルギー | 3D 回転で不変(sim 0.999)、形状識別 |

**★ 現在 11 手法(定位6 / 姿勢3 / 検出1 / 記述1)+ 精緻化6手法 × 5 構造。★=線→面リフト(曲率・SH)。**
mesh→voxel の平行移動を phase-corr で完全復元、depth 逆投影も検証済。**粗推定→精緻化のパイプライン**が成立
(例: Fourier-Mellin で回転 ±3° → `refine_rotation_z` で 0.01° / Hough で球中心整数 → `refine_peak_newton` でサブボクセル)。

**実装(`match3d.py` / `accel_match` / `accel_vol`)**:
- NCC(voxel) = `accel_match.ncc_locate_3d` + `_pyramid`(244× vs scipy)+ sub-voxel 重心。
- shape-based(勾配方向 = 輪郭マッチング、**コントラスト不変**)= `match3d.match_shape_3d`。0.4× 弱コントラストでも sub-voxel 定位。GPU 68-89×。
- phase-corr(FFT、平行移動、テンプレ不要)= `match_phase_3d`。GPU 18-28×。
- **Fourier-Mellin(log-polar、回転+スケール)= `match_logpolar_z`。z 軸回転+等方スケールをテンプレ/対応なしで同時推定(PCA は対応が要る)。z 投影(MIP)で 2D Fourier-Mellin に落とす。回転誤差 ~3°(mean)/ 5.4°(max)、スケール ~10% 過小。GPU 2.8ms=CPU 比 30×(FFT 系の本領)。honest な限界: |FFT| の 180° 対称で ±45/90° 近傍は別名化、coarse 推定器(下流で NCC/ICP 精緻化)。**
- PCA/moment(主軸整列、**回転**の明示復元)= `match_pca` / `moment_axes`。異方性雲の回転+並進を残差 0・角度差 0° で復元(0.2ms、numpy eigh)。
- MIP→2D(直交投影で 2D 手法に落とす、安い coarse)= `match_mip_2d`。定位 |Δ|=0。GPU 1.3×(transfer-bound)。
- chamfer(距離場、遮蔽頑健)= `match_chamfer_3d(edt="scipy"|"jfa")`。**`edt="jfa"` = GPU 厳密 EDT(`edt_jfa`、jump-flooding+JFA+2)で CPU 往復なしの全 GPU パイプライン。scipy C-EDT と max|err|=0(N≤160)、N≥96 で追い抜く(96→2.6× / 128→4.7×)。**
- generalized Hough(勾配 R-table 投票)= `match_hough_3d`。GHT を「向きビンごとの相関の総和」で GPU ネイティブ化(A(t)=Σ_bin scene_bin⋆template_bin)。shape-based の単一解と違い**投票 accumulator を返し、NMS で複数ピーク=複数インスタンスを検出**(2/2 実証)。欠けたエッジはピークを下げるだけ=遮蔽頑健。GPU 8×(26 conv3d が compute-heavy、CPU 233→28ms)。
- ★**曲率 / shape index(線→面リフト)= `curvature_maps` / `match_curvature_3d`。** 2D 輪郭の曲率(スカラー1個)を 3D 曲面の**主曲率 κ1,κ2**(2個)へリフト。level-set 閉形式(Kindlmann 2003、Hessian から conv3d)で per-voxel、shape index S∈[-1,1](cup/rut/saddle/ridge/cap)。球=+1・円柱=+0.5 と文献一致。**強度でなく局所曲面形状**で照合(同強度の球 vs 円柱を区別)。GPU 6×。
- ★**球面調和記述子(線→面リフト)= `sh_descriptor` / `match_sh_descriptor`。** 2D 閉輪郭の Fourier 記述子 → 3D 閉曲面の SH。同心球 shell の SH 帯域エネルギー ‖f_l(r)‖ は**回転不変**(Kazhdan 2003)。3D 2軸回転で自己類似度 0.999、rod vs sphere 0.847 で識別。retrieval/verification 用。
- **パラメトリック Hough(平面/球)= `hough_plane_3d` / `hough_sphere_3d`。** 2D Hough 直線/円の 3D リフト。勾配=法線を使い平面 (n,d) / 球 (c,r) を parameter 空間へ投票(テンプレ不要=RANSAC 系)。薄い境界面抽出で厚い勾配帯を排除。平面 法線exact・inlier93%、球 中心exact・半径 sub-voxel。GPU 4.9×(平面)/2×(球)。点群の地面/壁/ボール分割に。
- 変換: `points_to_voxel`(splat)/ `gaussians_to_voxel`(3DGS)/ `mesh_to_voxel` / `depth_to_points` / `voxel_to_mips` / `sobel3d` / `edt_jfa`(GPU 距離場)/ `hessian3d`(曲率)/ `_thin_surface`(薄面抽出)。

**pyramid / sub-voxel 重心は全 NCC 系に横断適用。回転は shape-based(不変)+ PCA(対応あり明示復元)+ Fourier-Mellin(対応なし回転+スケール)の 3 系統で対応。**

## 処理時間(実測 N=64³、CPU=py3.11 torch cpu / GPU=RTX5090 torch cu128、median ms)
発散した手法群を計測して**使い分けの土台**にする。★=GPU が明確に有利、▲=CPU の方が速い/同等(小問題は転送・起動overhead が勝つ)。

| 手法 | CPU ms | GPU ms | GPU/CPU | 備考 |
|---|---|---|---|---|
| phase_3d ★ | 37.7 | **0.49** | 77× | FFT、最速の姿勢(並進) |
| logpolar_z ★ | 96.2 | **2.84** | 34× | FFT、回転+スケール |
| hough_plane ★ | 16.8 | 3.62 | 4.6× | 平面検出 |
| refine_rot_z ★ | 33.2 | 3.87 | 8.6× | 回転精緻化 |
| NCC(locate) ★ | 189 | 9.07 | 21× | 定位の基準 |
| shape_3d ★ | 69.7 | 9.23 | 7.6× | コントラスト不変定位 |
| curvature ★ | 58 | 10.4 | 5.6× | 形状定位 |
| hough_sphere ★ | 21.5 | 10.2 | 2.1× | 球検出 |
| chamfer(scipy) | 36.1 | 16.7 | 2.2× | 遮蔽頑健(EDT は CPU) |
| scene_flow_lk ★ | 65.2 | 17.5 | 3.7× | 運動場 |
| chamfer(jfa) | 89.5 | 23.3 | 3.8× | 全 GPU 距離場(大 N で有利) |
| edt_jfa | 64.7 | 27.8 | 2.3× | N≥96 で scipy 超え |
| hough_3d(vote) ★ | 527 | 63.0 | 8.4× | 複数インスタンス、重い |
| mip_2d ▲ | 50.6 | 46.6 | 1.1× | 転送律速、GPU 恩恵薄 |
| sh_descriptor ▲ | **27.5** | 60.3 | 0.5× | per-radius ループ、CPU 優位 |
| refine_newton ▲ | **1.3** | 6.5 | 0.2× | 小問題、CPU で十分 |
| refine_lk ▲ | **1.02** | 2.2 | 0.5× | 小問題、CPU で十分 |
| refine_lm ▲ | **3.86** | 10.3 | 0.4× | autograd、CPU 優位 |
| pca(点群) ▲ | **0.21** | — | — | numpy eigh、CPU 完結 |
| icp_p2p(点群) ▲ | **15.3** | — | — | scipy cKDTree、CPU |
| icp_p2plane(点群) ▲ | **19.0** | — | — | torch/CPU |

**使い分け(計算資源)**: FFT系(phase/logpolar)・NCC・voting・flow・curvature は **GPU**。小さな反復精緻化(newton/lk/lm)・点群系(pca/icp)・SH は **CPU** の方が速い(GPU 起動/転送 overhead が問題規模を上回る)。

## 使い分け(状況 → 手法)。発散した手法を収束させる決定ガイド
| 状況・要件 | 推す手法 | 理由 |
|---|---|---|
| 平行移動のみ、テンプレ有 | **NCC** or **phase_3d** | phase はテンプレ不要・最速(0.5ms) |
| コントラスト/照明が変わる | **shape_3d**(勾配方向) | 強度不変 |
| 局所の**形が違う**同強度物体を区別 | **curvature**(shape index) | 曲面型で照合 |
| **遮蔽・部分**が入る | **chamfer** or **gen. Hough** | 欠損はピークを下げるだけ |
| **複数インスタンス** | **gen. Hough**(NMS ピーク) | 投票 accumulator |
| **z 回転+スケール**、対応なし | **logpolar_z**(粗)→ **refine_rot_z**(精) | FMT で当て GN で締める |
| **任意回転**、対応あり点群 | **PCA**(粗)→ **ICP**(精) | 主軸整列 → 点-面 ICP |
| **任意回転**、対応なし点群・部分重なり | **feature descriptor**(FPFH/SHOT、進行中)→ RANSAC → ICP | 初期推定なし大域登録 |
| **原始形状検出**(地面/壁/ボール) | **パラメトリック Hough**(平面/球) | テンプレ不要 |
| **回転不変な検索/照合** | **SH 記述子** | 帯域エネルギー不変 |
| **運動・変形**の推定 | **scene_flow_lk** | 密運動場 |
| 粗推定を**高精度化** | Newton/LK/LM/ICP(パラメータ別) | 下表 |

## 粗 → 精のパイプライン(coarse を fine で締める対応)
| 粗推定(出力) | 精緻化 | 到達精度 |
|---|---|---|
| NCC/shape/Hough の整数ピーク | `refine_peak_newton` | 0.01 voxel |
| 整数並進 | `refine_translation_lk` / `refine_lm`(+スケール) | 0.008 voxel |
| Fourier-Mellin 回転 ±3° | `refine_rotation_z` | 0.01° |
| PCA / 記述子 RANSAC の粗姿勢 | `icp_point2point_3d` / `icp_point2plane` | RMSE 1e-10 |

## 次に埋めるセル(TODO)。方針=手段を1つに絞らず発散(ノウハウは幅に蓄積)
- **feature descriptor**(Harris3D/ISS keypoint + FPFH/SHOT/spin image + RANSAC): 疎対応で大回転・部分重なり。
- **scene flow**(2D optical flow の 3D 版): voxel 運動場、変形/動体。
- **medial surface / 3D skeleton**(2D skeleton=1D medial axis の線→面版): 位相ベース照合。
- **anisotropic 3DGS 厳密 splat**(現状は等方近似)。
- **log-polar の大回転対応**(±45/90° 別名の解消: 複数投影軸の投票 or 球面調和)。

## 進捗ログ
- 2026-08-26: voxel×{NCC, pyramid, sub-voxel, region-morph, shape-based, phase-corr, PCA, MIP} 実装・検証・GPU 速度実測。point cloud / 3DGS を splat 変換で接続。test_match3d(7)+ test_accel_3d_toolkit(10)。
- 2026-08-27: **Fourier-Mellin(`match_logpolar_z`)= 回転+スケール列を追加**(z 投影 2D FMT、GPU 30×、回転誤差 mean 3°/max 5.4°、honest な ±45/90° 別名限界を明記)。**GPU 厳密 EDT(`edt_jfa`、JFA+2)で chamfer を全 GPU 化**(`edt="jfa"`、scipy と max|err|=0 @N≤160、N≥96 で追い抜き 96→2.6×/128→4.7×)。5×7=35 セル。test_match3d 12(+logpolar 回転/スケール, edt_jfa 厳密, chamfer jfa=scipy)。速度: PCA 0.2ms / MIP 1.3× も実測。
- 2026-08-27b: **generalized Hough(`match_hough_3d`)= 投票列を追加**(向きビン相関の総和、複数インスタンス 2/2 検出・遮蔽頑健、GPU 8×)。5×8=40 セル。test_match3d 14(+hough 複数体/遮蔽)。次段は TRIZ 発想(2D→3D 次元リフト・線→面)で「2D にあって 3D に無い手法」を体系的に増やす。
- 2026-08-27c(TRIZ 原理17・線→面リフト): **曲率/shape index**(`curvature_maps`/`match_curvature_3d`、主曲率2個・形状で照合、球+1/円柱+0.5、GPU 6×)/ **球面調和記述子**(`sh_descriptor`/`match_sh_descriptor`、回転不変 sim0.999、GPU)/ **パラメトリック Hough 平面・球**(`hough_plane_3d`/`hough_sphere_3d`、テンプレ不要検出、法線exact・中心exact、GPU 4.9×/2×)。手法 11(定位6/姿勢4/検出1/記述1)。test_match3d 21。ユーザー指針=「手段を1つに絞らず発散、ノウハウは幅に蓄積」→ 反復精緻化(Newton/GN/LM/ICP)を Workflow で複数並行探索中。
- 2026-08-27d(反復精緻化 = Newton 収束、Workflow で6手法並行検証・全PASS→統合後 5/6 一次再検証で PASS、残1は私のテスト中心規約ミスと判明し修正後 0.007voxel PASS): `refine_peak_newton`(0.011vox、放物線比9×)/ `refine_translation_lk`(0.008-0.023vox、NCC比60×)/ `refine_lm`(並進0.007vox+**スケール新規回復**)/ `refine_rotation_z`(0.002-0.017°、FMT±3°を5000×)/ `icp_point2point_3d`(RMSE 1e-14、Trimmed で部分重なり)/ `icp_point2plane`(RMSE 1e-10、点-面 GN、Low 2004)。粗推定→精緻化のパイプライン成立。test_match3d 27 / 全体 56 passed。
- 2026-08-27e(発散→収束): **scene flow**(`scene_flow_lk`、2D optical flow の 3D 版、pyramid+warp LK、並進 0.044voxel・発散検出、GPU 17.5ms/3.7×)追加。ユーザー指針「処理時間を記録/発散の後は使い分け/収束へ」に従い **全手法を N=64 で CPU/GPU 一貫計測** → **処理時間表 + 使い分けガイド + 粗→精パイプライン表**を doc に収束。honest: 小さな精緻化(newton/lk/lm)・点群系(pca/icp)・SH は CPU が速い(GPU overhead)。sobel3d を tensor 入力対応にし scene_flow を GPU 対応(bug fix)。test_match3d 28。feature descriptor(FPFH/SHOT/spin/Harris3D/ISS)は Workflow で並行探索中。
- 2026-08-27f(データ形式軸+幾何、ユーザー指針「3D 形式は多様=適切に使う/形式変換に対応」「2点→線・3点→角度/面は 2D/3D 共通」): **形式変換グラフ拡張** = `signed_distance_field`/`sdf_to_occupancy`/`estimate_point_normals`(PCA 法線)/`mesh_to_points`/`voxel_to_mesh`(marching cubes)/`tsdf_from_depth`(RGB-D)。**3D グレーモルフォロジー**追加 = `morph_gradient3d`(境界)/`morph_tophat3d`(小明構造)/`morph_blackhat3d`(既存 accel_vol の erode/dilate/ball に加え)。**幾何プリミティブ/メトロロジー層**(HALCON 相当、全閉形式)= 構成(line/plane from points)・角度(3点/二面角/線-面)・距離(点-面/点-線/ねじれ線間)・交差(線-面→点/面-面→線)・フィッティング(line/plane/sphere/circle 最小二乗)。test_match3d 35 passed。
