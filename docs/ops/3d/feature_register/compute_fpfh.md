---
op: compute_fpfh
dim: 3d
category: feature_register
in: points × normals
out: descriptor
examples: [fpfh_correspondence]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# compute_fpfh — 3D `feature_register` op

- **データ種**: `points × normals` → `descriptor`
- **呼び出し**: `import fullseye as fs; fs.ledger.compute_fpfh(points, normals, k=60, n_bins=11)` (実装を直接呼ぶなら `import feat_fpfh; feat_fpfh.compute_fpfh(points, normals, k=60, n_bins=11)`、台帳から引くなら `ops3d.get("compute_fpfh")`)

## 使い方

FPFH 記述子 (N, 3*n_bins) を計算(Rusu 2009)。

1) SPFH: 各点 p と近傍 k 点の対に (α,φ,θ) を求め、各特徴を n_bins ビンでヒストグラム化。
2) FPFH(p) = SPFH(p) + (1/k)Σ_j (1/d_pj) SPFH(j): 近傍 SPFH を距離重みで合成。
3 サブヒストグラムを各々 L1 正規化して連結(既定 33 次元)。角特徴は剛体不変。

引数: points (N,3), normals (N,3), k(FPFH 近傍数), n_bins(1特徴あたりのビン数)。
返り値: (N, 3*n_bins) の記述子行列。
Raises ValueError: points/normals が (N,3) でない・行数不一致・非有限・N<4
(k-NN が k>=3 を要求するため)。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blas_threads_and_memory](../../math/guides/blas_threads_and_memory.md) — 行列分解が遅い理由の知識 — BLAS スレッド・キャッシュ・メモリ配置

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [fpfh_correspondence](../../../../examples_3d/fpfh_correspondence.py) — `py -3.11 examples_3d/fpfh_correspondence.py`

## 型が繋がる次の op(`descriptor` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [shape_distance](../shape_descriptor/shape_distance.md)

## 同カテゴリ(`feature_register`)

[harris3d_keypoints](harris3d_keypoints.md) · [iss_keypoints](iss_keypoints.md) · [shot_descriptor](shot_descriptor.md) · [register_spin](register_spin.md) · [register_fpfh](register_fpfh.md) · [register_shot](register_shot.md)

---
*Provenance: feat_fpfh.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
