# fullseye 3D マッチング・マトリクス(データ構造 × 2D 手法 × データ変換)

3D の対象マッチングを **「入力データ構造」×「2D で確立した手法」** の格子で体系化し、両者を繋ぐ
**データ変換**(splat / 投影 / FFT / 勾配場 / 距離場 / PCA 正準化)で網羅的に増やす。核心思想:
**多くの 3D 手法は「3D データを、既知の 2D 手法が効く表現へ変換する」ことで作れる。**

差別化根拠: cv2 に 3D matchTemplate は無く、HALCON も 3D は表面/形状ベースに限られる。**GPU voxel マッチング一式**はツールとして空いている(RTX5090、torch cu128)。

## 手法列(2D で確立 → 3D へ持ち上げる)
| 手法 | 2D の出自 | 3D 化の要点 | 変換 |
|---|---|---|---|
| **NCC / template** | 正規化相互相関 | conv3d + box3d 正規化 | (直接) |
| **shape-based / 勾配方向** | Steger / HALCON | 3D 勾配の方向相関(3 成分 conv3d) | sobel3d |
| **phase correlation** | Reddy & Chatterji | 3D FFT の相互パワースペクトル(平行移動) | FFT |
| **Fourier-Mellin / log-polar** | Reddy & Chatterji | z 投影の |FFT|→log-polar→位相相関(回転+スケール) | FFT→log-polar |
| **chamfer / 距離場** | Barrow 1977 | エッジの EDT で chamfer スコア(全 GPU=JFA) | 距離変換(GPU-JFA) |
| **moment / PCA 軸** | 主軸整列 | 慣性テンソル固有ベクトルで姿勢 | PCA 正準化 |
| **generalized Hough** | Ballard | 3D R-table 投票 | 勾配→投票 |
| **projection(次元削減)** | — | 直交 MIP/シルエットで 2D 手法を適用 | 3D→2D 投影 |
| **feature descriptor** | Harris/SIFT | 3D corner + 記述子(spin image/FPFH) | 局所形状 |

## データ構造行(入力) × 共通表現への変換
| 構造 | → 共通表現 | 変換 |
|---|---|---|
| **voxel grid**(dense) | そのまま | — |
| **point cloud** | 密度 voxel | splat(scatter_add、任意で平滑) |
| **3DGS**(異方性ガウス) | 密度 voxel | Gaussian splat(means+scale+opacity) |
| **mesh**(頂点+面) | 占有 voxel / SDF | voxelize |
| **depth / range**(2.5D) | point cloud → voxel | 逆投影 |
| **binary voxel** | 距離場(SDF) | EDT |

## マトリクス(セル = 実現済 / TODO)
行 = データ構造、列 = 手法。**T** = 変換で接続。GPU 速度(vs CPU)を併記。

| ↓構造 \ 手法→ | NCC | shape-based | phase-corr | Fourier-Mellin | PCA/moment | MIP→2D | chamfer |
|---|---|---|---|---|---|---|---|
| voxel grid | ✅ 46× | ✅ 68-89× | ✅ 18-28× | ✅ 回転+スケール **30×** | ✅ | ✅ | ✅ 遮蔽頑健・全GPU |
| point cloud | ✅ T:splat | ✅ T | ✅ T | ✅ T | ✅ 回転復元 | ✅ T | ✅ T |
| 3DGS | ✅ T:splat | ✅ T | ✅ T | ✅ T | ✅ T | ✅ T | ✅ T |
| mesh | ✅ T:voxelize | ✅ T | ✅ T | ✅ T | ✅ T | ✅ T | ✅ T |
| depth 2.5D | ✅ T:逆投影 | ✅ T | ✅ T | ✅ T | ✅ T | ✅ T | ✅ T |

**★ 5 構造 × 7 手法 = 35 セルが変換で接続済**(T の行は共通 voxel/point 表現へ変換 → 列の手法を適用)。
mesh→voxel の平行移動を phase-corr で完全復元、depth 逆投影も検証済。

**実装(`match3d.py` / `accel_match` / `accel_vol`)**:
- NCC(voxel) = `accel_match.ncc_locate_3d` + `_pyramid`(244× vs scipy)+ sub-voxel 重心。
- shape-based(勾配方向 = 輪郭マッチング、**コントラスト不変**)= `match3d.match_shape_3d`。0.4× 弱コントラストでも sub-voxel 定位。GPU 68-89×。
- phase-corr(FFT、平行移動、テンプレ不要)= `match_phase_3d`。GPU 18-28×。
- **Fourier-Mellin(log-polar、回転+スケール)= `match_logpolar_z`。z 軸回転+等方スケールをテンプレ/対応なしで同時推定(PCA は対応が要る)。z 投影(MIP)で 2D Fourier-Mellin に落とす。回転誤差 ~3°(mean)/ 5.4°(max)、スケール ~10% 過小。GPU 2.8ms=CPU 比 30×(FFT 系の本領)。honest な限界: |FFT| の 180° 対称で ±45/90° 近傍は別名化、coarse 推定器(下流で NCC/ICP 精緻化)。**
- PCA/moment(主軸整列、**回転**の明示復元)= `match_pca` / `moment_axes`。異方性雲の回転+並進を残差 0・角度差 0° で復元(0.2ms、numpy eigh)。
- MIP→2D(直交投影で 2D 手法に落とす、安い coarse)= `match_mip_2d`。定位 |Δ|=0。GPU 1.3×(transfer-bound)。
- chamfer(距離場、遮蔽頑健)= `match_chamfer_3d(edt="scipy"|"jfa")`。**`edt="jfa"` = GPU 厳密 EDT(`edt_jfa`、jump-flooding+JFA+2)で CPU 往復なしの全 GPU パイプライン。scipy C-EDT と max|err|=0(N≤160)、N≥96 で追い抜く(96→2.6× / 128→4.7×)。**
- 変換: `points_to_voxel`(splat)/ `gaussians_to_voxel`(3DGS)/ `mesh_to_voxel` / `depth_to_points` / `voxel_to_mips` / `sobel3d` / `edt_jfa`(GPU 距離場)。

**pyramid / sub-voxel 重心は全 NCC 系に横断適用。回転は shape-based(不変)+ PCA(対応あり明示復元)+ Fourier-Mellin(対応なし回転+スケール)の 3 系統で対応。**

## 次に埋めるセル(TODO)
- **generalized Hough 3D**(勾配→R-table 投票): 部分形状・複数インスタンスに強い。回転は R-table を回して対応。
- **feature descriptor**(spin image / FPFH + RANSAC): 疎な keypoint 対応で大回転・部分重なりに。
- **anisotropic 3DGS 厳密 splat**(現状は等方近似)+ **ICP 精緻化**(Fourier-Mellin / PCA の coarse 解を仕上げる）。
- **log-polar の大回転対応**(±45/90° 別名の解消: 複数投影軸の投票 or 球面調和)。

## 進捗ログ
- 2026-08-26: voxel×{NCC, pyramid, sub-voxel, region-morph, shape-based, phase-corr, PCA, MIP} 実装・検証・GPU 速度実測。point cloud / 3DGS を splat 変換で接続。test_match3d(7)+ test_accel_3d_toolkit(10)。
- 2026-08-27: **Fourier-Mellin(`match_logpolar_z`)= 回転+スケール列を追加**(z 投影 2D FMT、GPU 30×、回転誤差 mean 3°/max 5.4°、honest な ±45/90° 別名限界を明記)。**GPU 厳密 EDT(`edt_jfa`、JFA+2)で chamfer を全 GPU 化**(`edt="jfa"`、scipy と max|err|=0 @N≤160、N≥96 で追い抜き 96→2.6×/128→4.7×)。5×7=35 セル。test_match3d 12(+logpolar 回転/スケール, edt_jfa 厳密, chamfer jfa=scipy)。速度: PCA 0.2ms / MIP 1.3× も実測。
