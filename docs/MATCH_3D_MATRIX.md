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

## データ構造行(入力) × 共通表現への変換
| 構造 | → 共通表現 | 変換 |
|---|---|---|
| **voxel grid**(dense) | そのまま | — |
| **point cloud** | 密度 voxel | splat(scatter_add、任意で平滑) |
| **3DGS**(異方性ガウス) | 密度 voxel | Gaussian splat(means+scale+opacity) |
| **mesh**(頂点+面) | 占有 voxel / SDF | voxelize |
| **depth / range**(2.5D) | point cloud → voxel | 逆投影 |
| **binary voxel** | 距離場(SDF) | EDT |

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
| 反復精緻化(進行中) | 高精度収束 | Newton/GN/ICP で粗推定を仕上げ |

**③ 検出(テンプレ不要で原始形状を出す)**
| 手法 | 出力 | 特徴 |
|---|---|---|
| パラメトリック Hough | 平面 (n,d) / 球 (c,r) | RANSAC 系、法線exact・inlier93%、4.9×/2× |

**④ 記述(回転不変な大域シグネチャで照合/検索)**
| 手法 | 出力 | 特徴 |
|---|---|---|
| ★球面調和記述子 | (半径×周波数)帯域エネルギー | 3D 回転で不変(sim 0.999)、形状識別 |

**★ 現在 11 手法(定位6 / 姿勢4 / 検出1 / 記述1)× 5 構造。★=線→面リフト(曲率・SH)。**
mesh→voxel の平行移動を phase-corr で完全復元、depth 逆投影も検証済。

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

## 次に埋めるセル(TODO)。方針=手段を1つに絞らず発散(ノウハウは幅に蓄積)
- **反復精緻化(進行中、Workflow で複数並行)**: Newton サブボクセルピーク / Gauss-Newton(Lucas-Kanade)並進 / Levenberg-Marquardt 並進+スケール / ICP point-to-point / ICP point-to-plane / GN 回転角精緻化。粗推定(FMT ±3°/Hough ±0.5vox/NCC整数)を高精度へ収束。
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
