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
| **phase correlation** | Reddy & Chatterji | 3D FFT の相互パワースペクトル | FFT |
| **chamfer / 距離場** | Barrow 1977 | エッジの EDT で chamfer スコア | 距離変換 |
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
行 = データ構造、列 = 手法。**T** = 変換で接続。

| ↓構造 \ 手法→ | NCC | shape-based | phase-corr | chamfer | PCA/moment | MIP→2D |
|---|---|---|---|---|---|---|
| voxel grid | ✅ | ✅ | ✅ | TODO | TODO | ✅ |
| point cloud | ✅(T:splat) | ✅(T) | ✅(T) | TODO | TODO | TODO |
| 3DGS | ✅(T:splat) | T | T | — | T | — |
| mesh | T:voxelize | T | T | — | T | — |
| depth 2.5D | T | T | T | — | T | — |

- **pyramid**(coarse-to-fine)と **sub-voxel 重心**は全 NCC 系に横断適用(既存)。
- **rotation 対応**: shape-based(勾配方向)/ PCA 正準化 / log-polar(将来)で扱う。

## 進捗ログ
- 2026-08-26: voxel×{NCC, pyramid, sub-voxel, region-morph} 実装済(`accel_match`/`accel_vol`)。
